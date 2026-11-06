import altair as alt
import pandas as pd
import streamlit as st

import db

ORDEN_CRITERIOS = ["Precio / calidad", "Sabor y presentación", "Entorno", "Atención", "Limpieza"]


def clp(valor) -> str:
    return "—" if pd.isna(valor) else "$" + f"{valor:,.0f}".replace(",", ".")


st.title("Ficha del restaurante")

modo = st.radio(
    "Calcular con",
    ["historico", "actual"],
    format_func=lambda m: "Histórico acumulado (todas las visitas)" if m == "historico"
    else "Valoración actual (la última de cada uno)",
    horizontal=True,
)

try:
    ranking = pd.DataFrame(db.consulta("v_ranking_restaurante", {"modo": modo}, orden="restaurante"))
    detalle = {r["restaurante_id"]: r for r in db.restaurantes()}
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

if ranking.empty:
    st.info("Todavía no hay restaurantes con valoraciones.")
    st.stop()

opciones = {f"{r.restaurante} · {r.comuna}": int(r.restaurante_id) for r in ranking.itertuples()}
eleccion = st.selectbox("Restaurante", list(opciones))
rid = opciones[eleccion]
fila = ranking[ranking["restaurante_id"] == rid].iloc[0]

try:
    notas = pd.DataFrame(db.consulta("v_valoracion", {"restaurante_id": rid}))
    criterios = pd.DataFrame(
        db.consulta("v_criterio_persona_restaurante", {"restaurante_id": rid, "modo": modo})
    )
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

info = detalle.get(rid, {})
st.subheader(fila["restaurante"])
partes = [fila["tipo"], info.get("direccion_referencia"), fila["comuna"], info.get("ciudad")]
st.caption(" · ".join(str(p) for p in partes if p and not pd.isna(p)))

c = st.columns(5)
c[0].metric("Nota global", f"{fila['nota_global']:.2f} / 5")
c[1].metric("Visitas", int(fila["visitas"]))
c[2].metric("Gasto por persona", clp(fila["gasto_prom_persona"]))
c[3].metric("Precio", fila["rango_precio"] if isinstance(fila["rango_precio"], str) else "—")
c[4].metric("Volverían", f"{fila['pct_volveria']:.0f}%")

personas = notas[["persona", "color_hex"]].drop_duplicates()
escala = alt.Scale(domain=personas["persona"].tolist(), range=personas["color_hex"].tolist())

st.markdown("**Notas por criterio**")
st.altair_chart(
    alt.Chart(criterios)
    .mark_bar()
    .encode(
        x=alt.X("criterio:N", sort=ORDEN_CRITERIOS, title=None),
        xOffset="persona:N",
        y=alt.Y("promedio:Q", scale=alt.Scale(domain=[0, 5]), title="Promedio"),
        color=alt.Color("persona:N", scale=escala, legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["persona", "criterio", alt.Tooltip("promedio:Q", format=".2f")],
    ),
    use_container_width=True,
)

notas["fecha"] = pd.to_datetime(notas["fecha_id"])
if notas["fecha"].nunique() > 1:
    st.markdown("**Evolución de la nota en cada visita**")
    st.altair_chart(
        alt.Chart(notas)
        .mark_line(point=True)
        .encode(
            x=alt.X("fecha:T", title=None),
            y=alt.Y("nota_global:Q", scale=alt.Scale(domain=[1, 5]), title="Nota global"),
            color=alt.Color("persona:N", scale=escala, legend=alt.Legend(title=None, orient="bottom")),
            tooltip=["persona", alt.Tooltip("fecha:T", title="Fecha"),
                     alt.Tooltip("nota_global:Q", format=".2f")],
        ),
        use_container_width=True,
    )

if pd.notna(fila["latitud"]) and pd.notna(fila["longitud"]):
    st.map(pd.DataFrame({"latitude": [fila["latitud"]], "longitude": [fila["longitud"]]}),
           zoom=14, height=220)

st.markdown("**Comentarios y detalle de cada visita**")
for _, v in notas.sort_values(["fecha", "persona"], ascending=[False, True]).iterrows():
    with st.container(border=True):
        voto = "👍 volvería" if v["volveria_recomendaria"] else "👎 no volvería"
        st.markdown(f"**{v['persona']}** · {v['fecha_id']} · ⭐ {v['nota_global']:.1f}/5 · {voto}")
        st.write(v["comentario"] if isinstance(v["comentario"], str) and v["comentario"] else "_Sin comentario_")
        extra = []
        if isinstance(v["ocasion"], str):
            extra.append(v["ocasion"])
        if pd.notna(v["gasto_persona"]):
            extra.append(f"gastó {clp(v['gasto_persona'])}")
        if extra:
            st.caption(" · ".join(extra))

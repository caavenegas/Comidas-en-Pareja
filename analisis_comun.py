"""Pantalla de análisis compartida por los dos módulos (modo 'actual' y 'historico')."""
import altair as alt
import pandas as pd
import streamlit as st

import db

ORDEN_CRITERIOS = ["Precio / calidad", "Sabor y presentación", "Entorno", "Atención", "Limpieza"]

TEXTOS = {
    "actual": (
        "Valoración actual",
        "Cuenta solo la **última valoración de cada uno** por restaurante. "
        "Si vuelven y cambian de opinión, la nota nueva reemplaza a la anterior.",
    ),
    "historico": (
        "Histórico acumulado",
        "**Suma todas las visitas**: cada vez que van y valoran, cuenta una valoración más.",
    ),
}


def clp(valor) -> str:
    return "—" if pd.isna(valor) else "$" + f"{valor:,.0f}".replace(",", ".")


def mostrar(modo: str) -> None:
    titulo, descripcion = TEXTOS[modo]
    st.title(titulo)
    st.caption(descripcion)
    filtro = {"modo": modo}

    def tabla(vista: str, **kw) -> pd.DataFrame:
        return pd.DataFrame(db.consulta(vista, filtro, **kw))

    try:
        resumen = db.consulta("v_resumen", filtro)
        if not resumen:
            st.info("Aún no hay valoraciones. Registra la primera en **Nueva valoración**.")
            st.stop()
        resumen = resumen[0]
        ranking = tabla("v_ranking_restaurante", orden="posicion")
        personas = tabla("v_persona_resumen", orden="persona")
        criterios = tabla("v_criterio_persona")
        coincidencia = db.consulta("v_coincidencia", filtro)
        discrepancia = tabla("v_discrepancia_criterio", orden="discrepancia_prom", desc=True)
        pares = tabla("v_pares", orden="dif_global", desc=True)
    except Exception as e:
        st.error(db.mensaje_error(e))
        st.stop()

    # ---------- resumen ----------
    c = st.columns(5)
    c[0].metric("Salidas", int(resumen["salidas"]))
    c[1].metric("Restaurantes", int(resumen["restaurantes_visitados"]))
    c[2].metric("Nota global", f"{resumen['nota_global']:.2f} / 5")
    c[3].metric("Gasto por persona", clp(resumen["gasto_prom_persona"]))
    c[4].metric("Volverían", f"{resumen['pct_volveria']:.0f}%")

    # ---------- ranking ----------
    st.subheader("Ranking de restaurantes")
    top = ranking.head(10)
    st.altair_chart(
        alt.Chart(top)
        .mark_bar()
        .encode(
            x=alt.X("nota_global:Q", scale=alt.Scale(domain=[0, 5]), title="Nota global"),
            y=alt.Y("restaurante:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("restaurante:N", title="Restaurante"),
                alt.Tooltip("nota_global:Q", title="Nota", format=".2f"),
                alt.Tooltip("visitas:Q", title="Visitas"),
            ],
        )
        .properties(height=max(120, 32 * len(top))),
        use_container_width=True,
    )
    vista_rank = ranking.rename(
        columns={
            "posicion": "#", "restaurante": "Restaurante", "tipo": "Tipo", "visitas": "Visitas",
            "nota_global": "Nota", "gasto_prom_persona": "Gasto prom.", "rango_precio": "Precio",
            "pct_volveria": "% volvería",
        }
    )[["#", "Restaurante", "Tipo", "Visitas", "Nota", "Gasto prom.", "Precio", "% volvería"]]
    st.dataframe(vista_rank, hide_index=True, use_container_width=True)

    # ---------- entre ustedes dos ----------
    st.subheader("Entre ustedes dos")
    escala = alt.Scale(domain=personas["persona"].tolist(), range=personas["color_hex"].tolist())

    cols = st.columns(len(personas))
    for col, (_, p) in zip(cols, personas.iterrows()):
        col.metric(f"Nota promedio de {p['persona']}", f"{p['nota_global']:.2f}")
        col.caption(f"{int(p['valoraciones'])} valoraciones · volvería {p['pct_volveria']:.0f}%")

    st.altair_chart(
        alt.Chart(criterios)
        .mark_bar()
        .encode(
            x=alt.X("criterio:N", sort=ORDEN_CRITERIOS, title=None),
            xOffset="persona:N",
            y=alt.Y("promedio:Q", scale=alt.Scale(domain=[0, 5]), title="Promedio"),
            color=alt.Color("persona:N", scale=escala,
                            legend=alt.Legend(title=None, orient="bottom")),
            tooltip=["persona", "criterio", alt.Tooltip("promedio:Q", format=".2f")],
        ),
        use_container_width=True,
    )

    if coincidencia and coincidencia[0]["salidas_compartidas"]:
        co = coincidencia[0]
        ayuda = (
            "100% = notas idénticas. Compara las valoraciones vigentes de ambos en cada restaurante."
            if modo == "actual"
            else "100% = notas idénticas. Se calcula sobre las salidas que valoraron los dos."
        )
        m = st.columns(3)
        m[0].metric("Coincidencia", f"{co['indice_coincidencia']:.0f}%", help=ayuda)
        m[1].metric("Diferencia promedio", f"{co['dif_global_prom']:.2f} pts")
        m[2].metric("Casos comparados", int(co["salidas_compartidas"]))

        st.markdown("**¿En qué criterio se diferencian más?**")
        st.altair_chart(
            alt.Chart(discrepancia)
            .mark_bar()
            .encode(
                x=alt.X("discrepancia_prom:Q", title="Diferencia promedio (puntos)"),
                y=alt.Y("criterio:N", sort="-x", title=None),
                tooltip=["criterio", alt.Tooltip("discrepancia_prom:Q", format=".2f")],
            )
            .properties(height=180),
            use_container_width=True,
        )

        st.markdown("**Donde más se distanciaron**")
        desacuerdos = pares.head(5).rename(
            columns={"restaurante": "Restaurante", "fecha_id": "Fecha", "dif_global": "Diferencia"}
        )[["Restaurante", "Fecha", "Diferencia"]]
        st.dataframe(desacuerdos, hide_index=True, use_container_width=True)
    else:
        st.info("Cuando los dos valoren un mismo restaurante, aquí verán cuánto coinciden.")

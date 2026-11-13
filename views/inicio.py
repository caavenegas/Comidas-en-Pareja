"""Pantalla de inicio: saludo, resumen personal, salidas por mes, mi top 5 y top 10 global."""
import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

import db
import ui
from analisis_comun import clp

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
# columna en la base -> nombre corto para el filtro
CRITERIOS_CORTOS = {col: etiqueta.split(" (")[0] for col, etiqueta in db.CRITERIOS.items()}

INSTRUCCIONES = """
**1. Arma tu grupo 👥**
Ve a **Grupos** y crea uno (pareja, amigos, familia) o pide que te agreguen. El líder invita a
las personas con su correo. Puedes estar en hasta 5 grupos, y cada grupo admite hasta 5 personas.

**2. Registra dónde fuiste ➕**
En **Nueva valoración**, elige el restaurante, la fecha y la ocasión. Si el restaurante no está
en la lista, puedes agregarlo ahí mismo.
- Pon nota del 1 al 5 a: **precio/calidad, sabor y presentación, entorno, atención y limpieza**.
- Indica si **volverías**, cuánto **gastaste** por persona y deja un comentario si quieres.
- Puedes guardarla en **varios grupos a la vez**. Cuenta como una sola salida.

**3. Mira los resultados 📊**
- **Valoración actual 🎯**: usa solo tu nota más reciente de cada restaurante. Sirve para saber cómo está *hoy*.
- **Histórico acumulado 📈**: suma todas las visitas. Sirve para ver qué lugares han sido buenos de forma *constante*.
- **Ficha del restaurante 🔎**: los gráficos y comentarios de un lugar en particular.
- **Historial 📒**: todas las valoraciones del grupo, de la más nueva a la más antigua.

**4. Catálogo de restaurantes 📍**
Es compartido por todos los usuarios. Cualquiera puede agregar restaurantes, pero solo quien lo
creó puede editarlo. Usa "Buscar coordenadas" para que aparezca en el mapa.

**5. Tu perfil 👤**
Cambia tu foto, apodo y color. Así te reconocen en los gráficos del grupo.

💡 *Tip: si vuelves al mismo restaurante el mismo día y en el mismo grupo, la valoración se
actualiza en vez de duplicarse.*
"""


@st.dialog("📖 Cómo usar la app", width="large")
def dialogo_instrucciones() -> None:
    st.markdown(INSTRUCCIONES)


def hoy() -> dt.date:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Santiago")).date()
    except Exception:
        return dt.date.today()


def nota(df: pd.DataFrame, columnas: list[str]) -> pd.Series:
    """Promedio de los criterios elegidos, fila por fila."""
    return df[columnas].apply(pd.to_numeric, errors="coerce").mean(axis=1)


def tabla_ranking(df: pd.DataFrame, columnas: list[str]) -> None:
    df = df.reset_index(drop=True)
    df.insert(0, "#", range(1, len(df) + 1))
    st.dataframe(
        df[["#"] + columnas], hide_index=True, width="stretch",
        column_config={"Nota": st.column_config.NumberColumn(format="%.2f")},
    )


# ---------- datos ----------
yo = db.persona()
try:
    tiene_grupos = bool(db.mis_grupos())
    mias = pd.DataFrame(db.consulta("v_valoracion", {"persona_id": yo["persona_id"]}))
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

# Una valoración guardada en varios grupos a la vez crea filas con el mismo creado_en:
# se cuentan como una sola salida.
if not mias.empty:
    mias = mias.drop_duplicates(subset=["creado_en", "restaurante_id", "fecha_id"])
usuario_nuevo = mias.empty

# ---------- saludo ----------
nombre = ui.nombre_visible(yo)
c_saludo, c_ayuda = st.columns([4, 1], vertical_alignment="center")
if usuario_nuevo:
    c_saludo.title(f"🍽️ ¡Bienvenido, {nombre}!")
else:
    c_saludo.title(f"🍽️ ¡Bienvenido de vuelta, {nombre}!")
if c_ayuda.button("📖 Instrucciones", width="stretch"):
    dialogo_instrucciones()

if not tiene_grupos:
    st.info("Para empezar, crea un grupo o pide a un líder que te agregue con tu correo.")
    if st.button("👥 Ir a Grupos", type="primary"):
        st.switch_page("views/grupos.py")
elif usuario_nuevo:
    st.subheader("Registra tu primera salida para empezar a armar tu ranking.")
    if st.button("➕ Registrar visita", type="primary"):
        st.switch_page("views/nueva.py")
else:
    st.subheader("¿Dónde fuiste hoy?")
    if st.button("➕ Registrar visita", type="primary"):
        st.switch_page("views/nueva.py")

if usuario_nuevo:
    with st.expander("📖 Cómo usar la app", expanded=True):
        st.markdown(INSTRUCCIONES)

# ---------- resumen personal ----------
if not usuario_nuevo:
    st.divider()
    salidas = len(mias)
    gastos = pd.to_numeric(mias["gasto_persona"], errors="coerce").dropna()
    c = st.columns(3)
    c[0].metric("Salidas", salidas)
    if gastos.empty:
        c[1].metric("Gasto promedio por salida", "Sin gasto registrado")
        c[2].metric("Gasto total", "Sin gasto registrado")
    else:
        c[1].metric("Gasto promedio por salida", clp(gastos.mean()))
        c[2].metric("Gasto total", clp(gastos.sum()))

    # Salidas por mes: últimos 6 meses (incluido el actual), según la fecha de la visita
    mes_actual = pd.Period(hoy(), freq="M")
    meses = pd.period_range(mes_actual - 5, mes_actual, freq="M")
    por_mes = (
        pd.to_datetime(mias["fecha_id"]).dt.to_period("M").value_counts()
        .reindex(meses, fill_value=0)
    )
    grafico = pd.DataFrame({
        "Mes": [f"{MESES[m.month - 1]} {str(m.year)[2:]}" for m in meses],
        "Salidas": por_mes.values,
    })
    st.markdown("**Salidas por mes**")
    st.altair_chart(
        alt.Chart(grafico)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Mes:N", sort=list(grafico["Mes"]), title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Salidas:Q", title=None, axis=alt.Axis(tickMinStep=1)),
            tooltip=["Mes", "Salidas"],
        )
        .properties(height=220),
        width="stretch",
    )

# ---------- filtro de criterios (aplica a Mi top 5 y al Top 10 global) ----------
st.divider()
elegidos = st.pills(
    "Criterios para calcular la nota", list(CRITERIOS_CORTOS),
    format_func=CRITERIOS_CORTOS.get, selection_mode="multi",
    default=list(CRITERIOS_CORTOS), key="inicio_criterios",
)
if not elegidos:
    st.warning("Elige al menos un criterio.")
    st.stop()

# ---------- mi top 5 ----------
if not usuario_nuevo:
    st.subheader("⭐ Mi top 5")
    mias["Nota"] = nota(mias, elegidos)
    mias["Volvería"] = mias["volveria_recomendaria"].map({True: "Sí", False: "No"})
    recientes = mias.sort_values(["fecha_id", "creado_en"], ascending=False)

    tab_acum, tab_ult = st.tabs(["Nota acumulada", "Última nota"])
    with tab_acum:
        acumulado = (
            recientes.groupby("restaurante_id", sort=False)
            .agg(Restaurante=("restaurante", "first"), Comuna=("comuna", "first"),
                 Nota=("Nota", "mean"), Visitas=("Nota", "size"), Volvería=("Volvería", "first"))
            .sort_values(["Nota", "Visitas"], ascending=False).head(5)
        )
        tabla_ranking(acumulado, ["Restaurante", "Comuna", "Nota", "Visitas", "Volvería"])
        st.caption("Promedio de todas tus visitas a cada restaurante, en todos tus grupos. "
                   "Volvería: tu respuesta más reciente.")
    with tab_ult:
        ultima = (
            recientes.drop_duplicates(subset="restaurante_id")
            .rename(columns={"restaurante": "Restaurante", "comuna": "Comuna", "fecha_id": "Fecha"})
            .sort_values(["Nota", "Fecha"], ascending=False).head(5)
        )
        tabla_ranking(ultima, ["Restaurante", "Comuna", "Nota", "Fecha", "Volvería"])
        st.caption("Solo tu valoración más reciente de cada restaurante.")

# ---------- top 10 global ----------
st.subheader("🏆 Top 10 global")
st.caption("Considera las valoraciones de todos los usuarios de la app. "
           "Solo aparecen restaurantes valorados por al menos 2 personas.")
try:
    global_acum = pd.DataFrame(db.consulta("v_global_acumulado"))
    global_act = pd.DataFrame(db.consulta("v_global_actual"))
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

COLUMNAS_GLOBAL = {"restaurante": "Restaurante", "comuna": "Comuna", "tipo": "Tipo",
                   "valoraciones": "Valoraciones", "personas": "Personas"}


def top_global(df: pd.DataFrame, columnas: list[str], pie: str) -> None:
    if df.empty:
        st.info("Aún no hay restaurantes valorados por al menos 2 personas.")
        return
    df = df.assign(Nota=nota(df, elegidos)).rename(columns=COLUMNAS_GLOBAL)
    df = df.sort_values(["Nota", "Valoraciones"], ascending=False).head(10)
    tabla_ranking(df, columnas)
    st.caption(pie)


tab_g_acum, tab_g_act = st.tabs(["Acumulado", "Actual"])
with tab_g_acum:
    top_global(global_acum,
               ["Restaurante", "Comuna", "Tipo", "Nota", "Valoraciones", "Personas"],
               "Promedio de todas las valoraciones históricas de todos los usuarios.")
with tab_g_act:
    top_global(global_act,
               ["Restaurante", "Comuna", "Tipo", "Nota", "Personas"],
               "Solo la última nota de cada usuario en cada restaurante.")

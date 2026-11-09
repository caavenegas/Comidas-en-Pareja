import datetime as dt

import streamlit as st

import db
import ui
import ui_restaurante

st.title("Nueva valoración")

grupo = ui.selector_grupo("¿Para qué grupo es esta valoración?")
ui.encabezado_grupo(grupo)

try:
    restaurantes = db.restaurantes()
    ocasiones = db.ocasiones()
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

s = st.session_state
# Si se acaba de crear un restaurante desde la ventana emergente, queda elegido
if "_rest_nuevo" in s:
    s["nueva_rest"] = s.pop("_rest_nuevo")

nombres_rest = {r["restaurante_id"]: f"{r['nombre']} · {r['comuna']}" for r in restaurantes}
opciones_ocasion = {o["ocasion"]: o["ocasion_id"] for o in ocasiones}

c_rest, c_nuevo = st.columns([5, 3], vertical_alignment="bottom")
rid = c_rest.selectbox(
    "Restaurante", list(nombres_rest), format_func=nombres_rest.get, index=None,
    placeholder="Busca o elige un restaurante", key="nueva_rest",
)
if c_nuevo.button("➕ Nuevo restaurante"):
    ui_restaurante.dialogo_nuevo()

with st.form("valoracion"):
    col1, col2 = st.columns(2)
    fecha = col1.date_input("Fecha", value=dt.date.today(), max_value=dt.date.today())
    ocasion = col2.selectbox("Ocasión", ["—"] + list(opciones_ocasion))
    gasto = st.number_input(
        "Lo que gastaste tú (CLP, 0 si no quieres anotarlo)", min_value=0, step=500, value=0
    )

    st.markdown("**¿Cómo estuvo?** 1 = muy mal · 5 = excelente")
    notas = {col: st.slider(etiqueta, 1, 5, 3) for col, etiqueta in db.CRITERIOS.items()}

    volveria = st.toggle("Volvería y lo recomendaría", value=True)
    comentario = st.text_area("Comentario (opcional)")
    enviar = st.form_submit_button("Guardar", type="primary")

if enviar:
    if rid is None:
        st.error("Elige un restaurante, o crea uno con el botón «Nuevo restaurante».")
    else:
        datos = {
            "grupo_id": grupo["grupo_id"],
            "restaurante_id": rid,
            "fecha_id": fecha.isoformat(),
            "persona_id": db.persona()["persona_id"],
            "ocasion_id": opciones_ocasion.get(ocasion),
            "gasto_persona": int(gasto) or None,
            **notas,
            "volveria_recomendaria": volveria,
            "comentario": comentario.strip() or None,
        }
        try:
            db.guardar_valoracion(datos)
        except Exception as e:
            st.error(db.mensaje_error(e))
        else:
            st.success(
                "¡Guardado! Si ya habías valorado este lugar ese día en este grupo, se actualizó tu nota."
            )

import datetime as dt

import streamlit as st

import db

st.title("Nueva valoración")

try:
    restaurantes = db.restaurantes()
    ocasiones = db.ocasiones()
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

if not restaurantes:
    st.info("Aún no hay restaurantes. Agrega el primero en la sección **Restaurantes**.")
    st.stop()

opciones_rest = {f"{r['nombre']} · {r['comuna']}": r["restaurante_id"] for r in restaurantes}
opciones_ocasion = {o["ocasion"]: o["ocasion_id"] for o in ocasiones}

with st.form("valoracion"):
    rest = st.selectbox("Restaurante", list(opciones_rest))
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
    datos = {
        "restaurante_id": opciones_rest[rest],
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
        st.success("¡Guardado! Si ya habías valorado este lugar ese día, se actualizó tu nota.")

import datetime as dt

import streamlit as st

import db

st.title("Mi perfil")
p = db.persona()

nacimiento = dt.date.fromisoformat(p["fecha_nacimiento"]) if p.get("fecha_nacimiento") else None

with st.form("perfil"):
    apodo = st.text_input("Apodo", value=p.get("apodo") or "")
    genero = st.text_input("Género (opcional)", value=p.get("genero") or "")
    fecha_nac = st.date_input(
        "Fecha de nacimiento",
        value=nacimiento,
        min_value=dt.date(1940, 1, 1),
        max_value=dt.date.today(),
    )
    color = st.color_picker("Tu color en los gráficos", value=p.get("color_hex") or "#4C78A8")
    guardar = st.form_submit_button("Guardar", type="primary")

if guardar:
    try:
        db.actualizar_perfil(
            {
                "apodo": apodo.strip() or None,
                "genero": genero.strip() or None,
                "fecha_nacimiento": fecha_nac.isoformat() if fecha_nac else None,
                "color_hex": color,
            }
        )
    except Exception as e:
        st.error(db.mensaje_error(e))
    else:
        st.success("Perfil actualizado.")

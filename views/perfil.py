import datetime as dt

import streamlit as st

import db
import ui

st.title("Mi perfil")
ui.mostrar_aviso()
p = db.persona()

# ---------- foto ----------
st.subheader("Foto")
c_foto, c_sube = st.columns([1, 3], vertical_alignment="center")
with c_foto:
    ui.avatar(p, 96)
with c_sube:
    n = st.session_state.get("foto_n", 0)
    archivo = st.file_uploader("Sube una foto (JPG, PNG o WebP)", type=["jpg", "jpeg", "png", "webp"],
                               key=f"foto_archivo_{n}")
    if archivo is not None and st.button("Usar esta foto", type="primary"):
        try:
            db.subir_foto(ui.preparar_foto(archivo.getvalue()))
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(db.mensaje_error(e))
        else:
            st.session_state["foto_n"] = n + 1
            ui.aviso("success", "Foto actualizada.")
            st.rerun()
    if p.get("foto_url") and st.button("Quitar foto"):
        try:
            db.quitar_foto()
        except Exception as e:
            st.error(db.mensaje_error(e))
        else:
            ui.aviso("success", "Foto eliminada.")
            st.rerun()

# ---------- datos ----------
st.subheader("Datos")
nacimiento = dt.date.fromisoformat(p["fecha_nacimiento"]) if p.get("fecha_nacimiento") else None

with st.form("perfil"):
    nombre = st.text_input("Nombre", value=p["nombre"], max_chars=60)
    apodo = st.text_input("Apodo", value=p.get("apodo") or "", max_chars=40)
    genero = st.text_input("Género (opcional)", value=p.get("genero") or "")
    fecha_nac = st.date_input(
        "Fecha de nacimiento",
        value=nacimiento,
        min_value=dt.date(1940, 1, 1),
        max_value=dt.date.today(),
    )
    color = st.color_picker("Tu color en los gráficos", value=ui.color_seguro(p.get("color_hex")))
    guardar = st.form_submit_button("Guardar", type="primary")

if guardar:
    if not nombre.strip():
        st.error("El nombre no puede quedar vacío.")
    else:
        try:
            db.actualizar_perfil(
                {
                    "nombre": nombre.strip(),
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

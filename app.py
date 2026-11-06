import streamlit as st

import db

st.set_page_config(page_title="Nosotros · Restaurantes", page_icon="🍽️", layout="centered")


def vista_login() -> None:
    st.title("🍽️ Nuestros restaurantes")
    st.caption("Inicia sesión para continuar.")
    with st.form("login"):
        email = st.text_input("Correo")
        clave = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Entrar", type="primary")
    if enviar:
        try:
            db.login(email.strip(), clave)
        except Exception:
            st.error("No se pudo iniciar sesión. Revisa el correo y la contraseña.")
        else:
            st.rerun()


if not db.esta_logueado():
    vista_login()
    st.stop()

paginas = [
    st.Page("views/nueva.py", title="Nueva valoración", icon="➕", default=True),
    st.Page("views/analisis_actual.py", title="Valoración actual", icon="🎯"),
    st.Page("views/analisis_acumulado.py", title="Histórico acumulado", icon="📈"),
    st.Page("views/ficha.py", title="Ficha del restaurante", icon="🔎"),
    st.Page("views/historial.py", title="Historial", icon="📒"),
    st.Page("views/restaurantes.py", title="Restaurantes", icon="📍"),
    st.Page("views/perfil.py", title="Mi perfil", icon="🙂"),
]
pagina = st.navigation(paginas)

with st.sidebar:
    p = db.persona()
    st.write(f"Hola, **{p.get('apodo') or p['nombre']}**")
    if st.button("Cerrar sesión"):
        db.logout()
        st.rerun()

pagina.run()

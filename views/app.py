import streamlit as st

import db

st.set_page_config(page_title="Nosotros · Restaurantes", page_icon="🍽️", layout="centered")


def vista_login() -> None:
    st.title("🍽️ Nuestros restaurantes")
    entrar, crear = st.tabs(["Entrar", "Crear cuenta"])

    with entrar:
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

    with crear:
        with st.form("registro"):
            nombre = st.text_input("Tu nombre")
            email_nuevo = st.text_input("Correo", key="registro_correo")
            clave1 = st.text_input("Contraseña (mínimo 6 caracteres)", type="password",
                                   key="registro_clave1")
            clave2 = st.text_input("Repite la contraseña", type="password", key="registro_clave2")
            registrar = st.form_submit_button("Crear cuenta", type="primary")
        if registrar:
            if not nombre.strip() or not email_nuevo.strip():
                st.error("Escribe tu nombre y tu correo.")
            elif len(clave1) < 6:
                st.error("La contraseña debe tener al menos 6 caracteres.")
            elif clave1 != clave2:
                st.error("Las contraseñas no coinciden.")
            else:
                try:
                    con_sesion = db.registrar(email_nuevo.strip(), clave1, nombre.strip())
                except Exception as e:
                    st.error(db.mensaje_error(e))
                else:
                    if con_sesion:
                        st.rerun()
                    else:
                        st.success("Cuenta creada. Revisa tu correo para confirmarla y luego entra.")


if not db.esta_logueado():
    vista_login()
    st.stop()

paginas = [
    st.Page("views/inicio.py", title="Inicio", icon="🏠", default=True),
    st.Page("views/nueva.py", title="Nueva valoración", icon="➕"),
    st.Page("views/analisis_actual.py", title="Valoración actual", icon="🎯"),
    st.Page("views/analisis_acumulado.py", title="Histórico acumulado", icon="📈"),
    st.Page("views/ficha.py", title="Ficha del restaurante", icon="🔎"),
    st.Page("views/historial.py", title="Historial", icon="📒"),
    st.Page("views/restaurantes.py", title="Restaurantes", icon="📍"),
    st.Page("views/grupos.py", title="Grupos", icon="👥"),
    st.Page("views/perfil.py", title="Mi perfil", icon="👤"),
]
pagina = st.navigation(paginas)

with st.sidebar:
    import ui

    p = db.persona()
    c_foto, c_texto = st.columns([1, 3], vertical_alignment="center")
    with c_foto:
        ui.avatar(p, 40)
    c_texto.write(f"Hola, **{ui.nombre_visible(p)}**")
    if st.button("Cerrar sesión"):
        db.logout()
        st.rerun()

pagina.run()

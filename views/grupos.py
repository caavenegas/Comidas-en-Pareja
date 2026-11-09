import streamlit as st

import db
import ui

MAX_GRUPOS = 5
MAX_PERSONAS = 5

st.title("Grupos")
st.caption(
    f"Puedes pertenecer a hasta {MAX_GRUPOS} grupos, de hasta {MAX_PERSONAS} personas cada uno. "
    "El líder crea el grupo, agrega a las personas y lo administra."
)
ui.mostrar_aviso()

yo = db.persona()

try:
    grupos = db.mis_grupos()
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()


def ejecutar(accion, *args, exito: str) -> None:
    """Corre una acción; si sale bien recarga la página con un aviso, si no muestra el error."""
    try:
        accion(*args)
    except Exception as e:
        st.error(db.mensaje_error(e))
    else:
        ui.aviso("success", exito)
        st.rerun()


# ---------- crear grupo ----------
with st.expander("➕ Crear un grupo nuevo", expanded=not grupos):
    if len(grupos) >= MAX_GRUPOS:
        st.info(f"Ya perteneces a {MAX_GRUPOS} grupos, que es el máximo.")
    else:
        with st.form("nuevo_grupo", clear_on_submit=True):
            nombre = st.text_input("Nombre del grupo", max_chars=40)
            color = st.color_picker("Color", value=ui.COLOR_DEFECTO)
            crear = st.form_submit_button("Crear grupo", type="primary")
        if crear:
            if not nombre.strip():
                st.error("Escribe un nombre para el grupo.")
            else:
                try:
                    nuevo_id = db.crear_grupo(nombre.strip(), color)
                except Exception as e:
                    st.error(db.mensaje_error(e))
                else:
                    st.session_state["grupo_activo"] = nuevo_id
                    ui.aviso("success", f"Grupo «{nombre.strip()}» creado. Ya eres su líder.")
                    st.rerun()

if not grupos:
    st.stop()

# ---------- mis grupos ----------
for g in grupos:
    gid = g["grupo_id"]
    es_lider = g["lider_persona_id"] == yo["persona_id"]
    try:
        miembros = db.miembros(gid)
    except Exception as e:
        st.error(db.mensaje_error(e))
        continue

    with st.container(border=True):
        ui.encabezado_grupo(g)
        lider = next((m for m in miembros if m["persona_id"] == g["lider_persona_id"]), None)
        rol = "Eres el líder" if es_lider else f"Líder: {ui.nombre_visible(lider) if lider else '—'}"
        st.caption(f"{len(miembros)} de {MAX_PERSONAS} personas · {rol}")

        for m in miembros:
            c_av, c_nom, c_acc = st.columns([1, 5, 2], vertical_alignment="center")
            with c_av:
                ui.avatar(m, 36)
            corona = " 👑" if m["persona_id"] == g["lider_persona_id"] else ""
            c_nom.write(f"{ui.nombre_visible(m)}{corona}")
            if es_lider and m["persona_id"] != yo["persona_id"]:
                if c_acc.button("Quitar", key=f"quitar_{gid}_{m['persona_id']}"):
                    ejecutar(db.quitar_miembro, gid, m["persona_id"],
                             exito=f"{ui.nombre_visible(m)} salió del grupo.")

        if es_lider:
            with st.expander("Administrar grupo"):
                st.markdown("**Nombre y color**")
                with st.form(f"editar_{gid}"):
                    nuevo_nombre = st.text_input("Nombre", value=g["nombre"], max_chars=40)
                    nuevo_color = st.color_picker("Color", value=ui.color_seguro(g["color_hex"]))
                    guardar = st.form_submit_button("Guardar cambios")
                if guardar:
                    if not nuevo_nombre.strip():
                        st.error("El nombre no puede quedar vacío.")
                    else:
                        ejecutar(db.editar_grupo, gid, nuevo_nombre.strip(), nuevo_color,
                                 exito="Grupo actualizado.")

                st.markdown("**Agregar a alguien**")
                if len(miembros) >= MAX_PERSONAS:
                    st.info(f"El grupo ya tiene {MAX_PERSONAS} personas.")
                else:
                    with st.form(f"agregar_{gid}", clear_on_submit=True):
                        correo = st.text_input("Correo de su cuenta")
                        agregar = st.form_submit_button("Agregar al grupo")
                    st.caption("La persona debe haber creado su cuenta antes, desde la pantalla de inicio.")
                    if agregar:
                        if not correo.strip():
                            st.error("Escribe el correo.")
                        else:
                            ejecutar(db.agregar_miembro, gid, correo.strip(),
                                     exito="Persona agregada al grupo.")

                otros = [m for m in miembros if m["persona_id"] != yo["persona_id"]]
                if otros:
                    st.markdown("**Traspasar el liderazgo**")
                    nombres_otros = {m["persona_id"]: ui.nombre_visible(m) for m in otros}
                    nuevo_lider_id = st.selectbox(
                        "Nuevo líder", list(nombres_otros), format_func=nombres_otros.get,
                        key=f"lider_{gid}")
                    if st.button("Traspasar", key=f"traspasar_{gid}"):
                        ejecutar(db.traspasar_liderazgo, gid, nuevo_lider_id,
                                 exito=f"{nombres_otros[nuevo_lider_id]} es ahora el líder.")

                st.markdown("**Eliminar el grupo**")
                st.warning("Se borran el grupo y todas las valoraciones registradas en él. No se puede deshacer.")
                confirmo = st.checkbox("Entiendo que se borrarán las valoraciones del grupo",
                                       key=f"conf_{gid}")
                if st.button("Eliminar grupo", key=f"eliminar_{gid}", disabled=not confirmo):
                    ejecutar(db.eliminar_grupo, gid, exito=f"Grupo «{g['nombre']}» eliminado.")
        else:
            confirmo = st.checkbox("Quiero salir de este grupo", key=f"salir_conf_{gid}")
            if st.button("Salir del grupo", key=f"salir_{gid}", disabled=not confirmo):
                ejecutar(db.salir_del_grupo, gid, exito=f"Saliste de «{g['nombre']}».")

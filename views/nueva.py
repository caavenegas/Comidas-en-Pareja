import datetime as dt

import streamlit as st

import db
import ui
import ui_restaurante

st.title("Nueva valoración")

try:
    grupos = db.mis_grupos()
    restaurantes = db.restaurantes()
    ocasiones = db.ocasiones()
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

if not grupos:
    st.info(
        "Aún no perteneces a ningún grupo. Crea uno en la sección **Grupos**, "
        "o pide a un líder que te agregue con tu correo."
    )
    st.stop()

s = st.session_state

# Grupos donde se guardará la valoración (por defecto, el grupo que estabas viendo)
nombres_grupo = {g["grupo_id"]: g["nombre"] for g in grupos}
if "nueva_grupos" not in s:
    activo = s.get("grupo_activo")
    s["nueva_grupos"] = [activo if activo in nombres_grupo else grupos[0]["grupo_id"]]
s["nueva_grupos"] = [g for g in s["nueva_grupos"] if g in nombres_grupo]   # por si saliste de alguno
grupos_elegidos = st.multiselect(
    "¿En qué grupos quieres guardar esta valoración?",
    list(nombres_grupo), format_func=nombres_grupo.get, key="nueva_grupos",
    help="Se guarda una copia en cada grupo que elijas, y cada grupo la ve en sus análisis.",
)
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
    elif not grupos_elegidos:
        st.error("Elige al menos un grupo donde guardar la valoración.")
    else:
        base = {
            "restaurante_id": rid,
            "fecha_id": fecha.isoformat(),
            "persona_id": db.persona()["persona_id"],
            "ocasion_id": opciones_ocasion.get(ocasion),
            "gasto_persona": int(gasto) or None,
            **notas,
            "volveria_recomendaria": volveria,
            "comentario": comentario.strip() or None,
        }
        filas = [{**base, "grupo_id": g} for g in grupos_elegidos]
        try:
            db.guardar_valoracion(filas)
        except Exception as e:
            st.error(db.mensaje_error(e))
        else:
            lista = ", ".join(f"«{nombres_grupo[g]}»" for g in grupos_elegidos)
            st.success(
                f"¡Guardado en {lista}! Si ya habías valorado este lugar ese día en alguno de "
                "esos grupos, se actualizó tu nota."
            )

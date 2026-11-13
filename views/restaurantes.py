import pandas as pd
import streamlit as st

import db
import ui_restaurante

st.title("Restaurantes")
st.caption(
    "Es un catálogo compartido por todos los grupos. Cualquiera puede agregar restaurantes, "
    "pero solo quien lo creó puede editarlo."
)

s = st.session_state
yo = db.persona()

try:
    tipos = db.tipos()
    restaurantes = db.restaurantes()
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

tipo_ids = {t["tipo"]: t["tipo_id"] for t in tipos}
tab_lista, tab_nuevo, tab_editar, tab_tipos = st.tabs(["Lista y mapa", "Agregar", "Editar", "Tipos"])

# ---------- lista y mapa ----------
with tab_lista:
    if not restaurantes:
        st.info("Todavía no hay restaurantes.")
    else:
        df = pd.DataFrame(
            [
                {
                    "Nombre": r["nombre"],
                    "Tipo": (r.get("dim_tipo_restaurante") or {}).get("tipo"),
                    "Comuna": r["comuna"],
                    "Ciudad": r["ciudad"],
                    "Dirección": r["direccion_referencia"],
                    "Lo creaste tú": "Sí" if r.get("creado_por") == yo["persona_id"] else "",
                    "latitude": r["latitud"],
                    "longitude": r["longitud"],
                }
                for r in restaurantes
            ]
        )
        st.dataframe(df.drop(columns=["latitude", "longitude"]), hide_index=True, width="stretch")
        con_coord = df.dropna(subset=["latitude", "longitude"])
        if not con_coord.empty:
            st.map(con_coord[["latitude", "longitude"]])

# ---------- agregar ----------
with tab_nuevo:
    mensaje = s.pop("nuevo_msg", None)
    if mensaje:
        getattr(st, mensaje[0])(mensaje[1])
    ui_restaurante.campos("nuevo", list(tipo_ids))
    st.button("Guardar restaurante", type="primary", key="btn_guardar_nuevo",
              on_click=ui_restaurante.guardar_nuevo, args=("nuevo", tipo_ids, "nuevo_msg"))

# ---------- editar ----------
with tab_editar:
    if not restaurantes:
        st.info("Todavía no hay restaurantes para editar.")
    else:
        por_id = {r["restaurante_id"]: r for r in restaurantes}
        etiquetas = {i: f"{r['nombre']} · {r['comuna']}" for i, r in por_id.items()}
        rid = st.selectbox("Restaurante a editar", list(etiquetas), format_func=etiquetas.get,
                           index=None, placeholder="Elige un restaurante", key="editar_sel")
        if rid is not None:
            r = por_id[rid]
            if r.get("creado_por") != yo["persona_id"]:
                st.info("Este restaurante lo creó otra persona, así que solo ella puede editarlo.")
            else:
                prefijo = f"ed{rid}"
                mensaje = s.pop("editar_msg", None)
                if mensaje:
                    getattr(st, mensaje[0])(mensaje[1])
                ui_restaurante.campos(prefijo, list(tipo_ids), inicial=r)
                st.button("Guardar cambios", type="primary", key="btn_guardar_edicion",
                          on_click=ui_restaurante.guardar_edicion,
                          args=(prefijo, rid, tipo_ids, "editar_msg"))

# ---------- tipos ----------
with tab_tipos:
    st.write(", ".join(tipo_ids) or "Aún no hay tipos.")
    with st.form("form_agregar_tipo", clear_on_submit=True):
        nuevo = st.text_input("Nuevo tipo")
        if st.form_submit_button("Agregar tipo"):
            if nuevo.strip():
                try:
                    db.crear_tipo(nuevo.strip())
                except Exception as e:
                    st.error(db.mensaje_error(e))
                else:
                    st.rerun()

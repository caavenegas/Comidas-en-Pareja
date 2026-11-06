import pandas as pd
import streamlit as st

import db

REGIONES = [
    "Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo",
    "Valparaíso", "Metropolitana de Santiago", "O'Higgins", "Maule", "Ñuble",
    "Biobío", "La Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes",
    "Otra (fuera de Chile)",
]
CAMPOS_TEXTO = ("r_nombre", "r_dir", "r_comuna", "r_ciudad")


def buscar_coordenadas() -> None:
    from geopy.geocoders import Nominatim

    s = st.session_state
    base = [s.get("r_comuna"), s.get("r_ciudad"), s.get("r_pais")]
    consultas = []
    if (s.get("r_dir") or "").strip():
        consultas.append([s["r_dir"]] + base)
    if (s.get("r_nombre") or "").strip():
        consultas.append([s["r_nombre"]] + base)

    geo = Nominatim(user_agent="restaurantes-pareja-app", timeout=10)
    for partes in consultas:
        try:
            lugar = geo.geocode(", ".join(x for x in partes if x))
        except Exception:
            lugar = None
        if lugar:
            s["r_lat"] = round(lugar.latitude, 6)
            s["r_lon"] = round(lugar.longitude, 6)
            s["r_msg"] = ("success", f"Encontrado: {lugar.address}")
            return
    s["r_msg"] = ("warning", "No se encontró. Revisa la dirección o escribe las coordenadas a mano.")


def guardar_restaurante(tipo_ids: dict) -> None:
    s = st.session_state
    nombre, comuna, ciudad = (s.get(k, "").strip() for k in ("r_nombre", "r_comuna", "r_ciudad"))
    if not (nombre and comuna and ciudad and s.get("r_region")):
        s["r_msg"] = ("error", "Nombre, comuna, ciudad y región son obligatorios.")
        return
    datos = {
        "nombre": nombre,
        "direccion_referencia": s.get("r_dir", "").strip() or None,
        "comuna": comuna,
        "ciudad": ciudad,
        "region": s["r_region"],
        "pais": s.get("r_pais", "").strip() or "Chile",
        "latitud": s.get("r_lat"),
        "longitud": s.get("r_lon"),
        "tipo_id": tipo_ids.get(s.get("r_tipo")),
    }
    try:
        db.crear_restaurante(datos)
    except Exception as e:
        s["r_msg"] = ("error", db.mensaje_error(e))
        return
    for k in CAMPOS_TEXTO:
        s[k] = ""
    s["r_lat"] = s["r_lon"] = None
    s["r_msg"] = ("success", f"Restaurante «{nombre}» guardado.")


st.title("Restaurantes")

try:
    tipos = db.tipos()
    restaurantes = db.restaurantes()
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

tipo_ids = {t["tipo"]: t["tipo_id"] for t in tipos}
tab_lista, tab_nuevo, tab_tipos = st.tabs(["Lista y mapa", "Agregar", "Tipos"])

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
                    "latitude": r["latitud"],
                    "longitude": r["longitud"],
                }
                for r in restaurantes
            ]
        )
        st.dataframe(
            df.drop(columns=["latitude", "longitude"]), hide_index=True, use_container_width=True
        )
        con_coord = df.dropna(subset=["latitude", "longitude"])
        if not con_coord.empty:
            st.map(con_coord[["latitude", "longitude"]])

with tab_nuevo:
    if "r_msg" in st.session_state:
        nivel, texto = st.session_state.pop("r_msg")
        getattr(st, nivel)(texto)

    st.text_input("Nombre", key="r_nombre")
    st.text_input("Dirección o referencia", key="r_dir")
    c1, c2 = st.columns(2)
    c1.text_input("Comuna", key="r_comuna")
    c2.text_input("Ciudad", key="r_ciudad")
    c3, c4 = st.columns(2)
    c3.selectbox("Región", REGIONES, index=None, placeholder="Elige una región", key="r_region")
    c4.text_input("País", value="Chile", key="r_pais")
    st.selectbox("Tipo de restaurante", list(tipo_ids), index=None,
                 placeholder="Sin tipo (puedes crear tipos en la pestaña Tipos)", key="r_tipo")

    st.button("📍 Buscar coordenadas desde la dirección", on_click=buscar_coordenadas)
    c5, c6 = st.columns(2)
    c5.number_input("Latitud", min_value=-90.0, max_value=90.0, value=None,
                    format="%.6f", key="r_lat")
    c6.number_input("Longitud", min_value=-180.0, max_value=180.0, value=None,
                    format="%.6f", key="r_lon")

    st.button("Guardar restaurante", type="primary",
              on_click=guardar_restaurante, args=(tipo_ids,))

with tab_tipos:
    st.write(", ".join(tipo_ids) or "Aún no hay tipos.")
    with st.form("nuevo_tipo", clear_on_submit=True):
        nuevo = st.text_input("Nuevo tipo")
        if st.form_submit_button("Agregar tipo"):
            if nuevo.strip():
                try:
                    db.crear_tipo(nuevo.strip())
                except Exception as e:
                    st.error(db.mensaje_error(e))
                else:
                    st.rerun()

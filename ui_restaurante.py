"""Formulario de restaurante reutilizable: crear (pestaña y ventana emergente) y editar."""
from __future__ import annotations

import streamlit as st

import db

REGIONES = [
    "Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo",
    "Valparaíso", "Metropolitana de Santiago", "O'Higgins", "Maule", "Ñuble",
    "Biobío", "La Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes",
    "Otra (fuera de Chile)",
]


def _k(prefijo: str, campo: str) -> str:
    return f"{prefijo}_{campo}"


def limpiar(prefijo: str) -> None:
    """Borra el estado de un formulario para que vuelva a quedar vacío."""
    s = st.session_state
    for clave in [k for k in s.keys() if k.startswith(prefijo + "_")]:
        del s[clave]


def _sembrar(prefijo: str, inicial: dict | None) -> None:
    """Pone los valores iniciales una sola vez (los widgets leen su valor del estado)."""
    i = inicial or {}
    tipo = (i.get("dim_tipo_restaurante") or {}).get("tipo")
    valores = {
        "nombre": i.get("nombre") or "",
        "dir": i.get("direccion_referencia") or "",
        "comuna": i.get("comuna") or "",
        "ciudad": i.get("ciudad") or "",
        "region": i.get("region"),
        "pais": i.get("pais") or "Chile",
        "tipo": tipo,
        "lat": i.get("latitud"),
        "lon": i.get("longitud"),
    }
    for campo, valor in valores.items():
        st.session_state.setdefault(_k(prefijo, campo), valor)


def _buscar_coordenadas(prefijo: str) -> None:
    from geopy.geocoders import Nominatim

    s = st.session_state
    texto = lambda campo: (s.get(_k(prefijo, campo)) or "").strip()
    base = [texto("comuna"), texto("ciudad"), texto("pais")]
    consultas = []
    if texto("dir"):
        consultas.append([texto("dir")] + base)
    if texto("nombre"):
        consultas.append([texto("nombre")] + base)

    geo = Nominatim(user_agent="restaurantes-pareja-app", timeout=10)
    for partes in consultas:
        try:
            lugar = geo.geocode(", ".join(p for p in partes if p))
        except Exception:
            lugar = None
        if lugar:
            s[_k(prefijo, "lat")] = round(lugar.latitude, 6)
            s[_k(prefijo, "lon")] = round(lugar.longitude, 6)
            s[_k(prefijo, "geo_msg")] = ("success", f"Encontrado: {lugar.address}")
            return
    s[_k(prefijo, "geo_msg")] = (
        "warning", "No se encontró. Revisa la dirección o escribe las coordenadas a mano.")


def campos(prefijo: str, tipo_nombres: list[str], inicial: dict | None = None) -> None:
    """Dibuja los campos. Los valores quedan en st.session_state con claves '<prefijo>_<campo>'."""
    _sembrar(prefijo, inicial)
    s = st.session_state

    st.text_input("Nombre", key=_k(prefijo, "nombre"))
    st.text_input("Dirección o referencia", key=_k(prefijo, "dir"))
    c1, c2 = st.columns(2)
    c1.text_input("Comuna", key=_k(prefijo, "comuna"))
    c2.text_input("Ciudad", key=_k(prefijo, "ciudad"))

    regiones = list(REGIONES)
    region_actual = s.get(_k(prefijo, "region"))
    if region_actual and region_actual not in regiones:
        regiones.insert(0, region_actual)
    c3, c4 = st.columns(2)
    c3.selectbox("Región", regiones, index=None, placeholder="Elige una región",
                 key=_k(prefijo, "region"))
    c4.text_input("País", key=_k(prefijo, "pais"))

    tipos = list(tipo_nombres)
    tipo_actual = s.get(_k(prefijo, "tipo"))
    if tipo_actual and tipo_actual not in tipos:
        tipos.append(tipo_actual)
    st.selectbox("Tipo de restaurante", tipos, index=None,
                 placeholder="Sin tipo (puedes crear tipos en Restaurantes > Tipos)",
                 key=_k(prefijo, "tipo"))

    st.button("📍 Buscar coordenadas desde la dirección", key=_k(prefijo, "btn_geo"),
              on_click=_buscar_coordenadas, args=(prefijo,))
    mensaje = s.pop(_k(prefijo, "geo_msg"), None)
    if mensaje:
        getattr(st, mensaje[0])(mensaje[1])

    c5, c6 = st.columns(2)
    c5.number_input("Latitud", min_value=-90.0, max_value=90.0, value=None,
                    format="%.6f", key=_k(prefijo, "lat"))
    c6.number_input("Longitud", min_value=-180.0, max_value=180.0, value=None,
                    format="%.6f", key=_k(prefijo, "lon"))


def leer(prefijo: str, tipo_ids: dict) -> dict:
    s = st.session_state
    texto = lambda campo: (s.get(_k(prefijo, campo)) or "").strip()
    return {
        "nombre": texto("nombre"),
        "direccion_referencia": texto("dir") or None,
        "comuna": texto("comuna"),
        "ciudad": texto("ciudad"),
        "region": s.get(_k(prefijo, "region")),
        "pais": texto("pais") or "Chile",
        "latitud": s.get(_k(prefijo, "lat")),
        "longitud": s.get(_k(prefijo, "lon")),
        "tipo_id": tipo_ids.get(s.get(_k(prefijo, "tipo"))),
    }


def validar(datos: dict) -> str | None:
    if not (datos["nombre"] and datos["comuna"] and datos["ciudad"] and datos["region"]):
        return "Nombre, comuna, ciudad y región son obligatorios."
    return None


# ---- acciones (se usan como on_click, antes de que se vuelvan a dibujar los campos) ----

def guardar_nuevo(prefijo: str, tipo_ids: dict, clave_msg: str) -> None:
    s = st.session_state
    datos = leer(prefijo, tipo_ids)
    error = validar(datos)
    if error:
        s[clave_msg] = ("error", error)
        return
    try:
        nuevo = db.crear_restaurante(datos)
    except Exception as e:
        s[clave_msg] = ("error", db.mensaje_error(e))
        return
    limpiar(prefijo)
    s["_rest_nuevo"] = nuevo["restaurante_id"]
    s[clave_msg] = ("success", f"Restaurante «{datos['nombre']}» guardado.")


def guardar_edicion(prefijo: str, restaurante_id: int, tipo_ids: dict, clave_msg: str) -> None:
    s = st.session_state
    datos = leer(prefijo, tipo_ids)
    error = validar(datos)
    if error:
        s[clave_msg] = ("error", error)
        return
    try:
        db.actualizar_restaurante(restaurante_id, datos)
    except Exception as e:
        s[clave_msg] = ("error", db.mensaje_error(e))
        return
    s[clave_msg] = ("success", "Cambios guardados.")


@st.dialog("Nuevo restaurante")
def dialogo_nuevo() -> None:
    """Ventana emergente para crear un restaurante sin salir de la pantalla actual."""
    s = st.session_state
    try:
        tipo_ids = {t["tipo"]: t["tipo_id"] for t in db.tipos()}
    except Exception as e:
        st.error(db.mensaje_error(e))
        return
    mensaje = s.pop("dlg_msg", None)
    if mensaje:
        if mensaje[0] == "success":
            st.rerun()          # cierra la ventana y vuelve a la pantalla con el restaurante elegido
        st.error(mensaje[1])
    campos("dlg", list(tipo_ids))
    st.button("Guardar restaurante", type="primary", key="btn_dialogo_guardar",
              on_click=guardar_nuevo, args=("dlg", tipo_ids, "dlg_msg"))

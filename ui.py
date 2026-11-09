"""Piezas de interfaz compartidas: selector de grupo, avatares, mensajes."""
from __future__ import annotations

import html
import io
import re

import streamlit as st

import db

COLOR_DEFECTO = "#4C78A8"
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_FOTO_BYTES = 8 * 1024 * 1024


def color_seguro(color) -> str:
    """Solo deja pasar colores #RRGGBB; evita meter texto raro en el HTML."""
    return color if isinstance(color, str) and _HEX.match(color) else COLOR_DEFECTO


def nombre_visible(p: dict) -> str:
    return p.get("apodo") or p["nombre"]


def encabezado_grupo(grupo: dict, tamano: str = "1.3rem") -> None:
    color = color_seguro(grupo.get("color_hex"))
    nombre = html.escape(grupo["nombre"])
    st.markdown(
        f'<div style="border-left:6px solid {color};padding:2px 0 2px 10px;'
        f'font-size:{tamano};font-weight:600">{nombre}</div>',
        unsafe_allow_html=True,
    )


def avatar(p: dict, tam: int = 44) -> None:
    if p.get("foto_url"):
        st.image(p["foto_url"], width=tam)
        return
    inicial = html.escape(nombre_visible(p)[:1].upper() or "?")
    color = color_seguro(p.get("color_hex"))
    st.markdown(
        f'<div style="width:{tam}px;height:{tam}px;border-radius:50%;background:{color};'
        f'color:#fff;display:flex;align-items:center;justify-content:center;'
        f'font-weight:600;font-size:{int(tam * 0.45)}px">{inicial}</div>',
        unsafe_allow_html=True,
    )


def selector_grupo(etiqueta: str = "Grupo") -> dict:
    """Pide elegir un grupo. Recuerda la elección al cambiar de pantalla. Detiene la página si no hay grupos."""
    try:
        grupos = db.mis_grupos()
    except Exception as e:
        st.error(db.mensaje_error(e))
        st.stop()
    if not grupos:
        st.info(
            "Aún no perteneces a ningún grupo. Crea uno en la sección **Grupos**, "
            "o pide a un líder que te agregue con tu correo."
        )
        st.stop()
    ids = [g["grupo_id"] for g in grupos]
    nombres = {g["grupo_id"]: g["nombre"] for g in grupos}
    actual = st.session_state.get("grupo_activo")
    indice = ids.index(actual) if actual in ids else 0
    elegido = st.selectbox(etiqueta, ids, index=indice, format_func=nombres.get)
    st.session_state["grupo_activo"] = elegido
    return next(g for g in grupos if g["grupo_id"] == elegido)


def aviso(nivel: str, texto: str) -> None:
    """Guarda un mensaje para mostrarlo tras recargar la página."""
    st.session_state["_aviso"] = (nivel, texto)


def mostrar_aviso() -> None:
    mensaje = st.session_state.pop("_aviso", None)
    if mensaje:
        nivel, texto = mensaje
        getattr(st, nivel)(texto)


def preparar_foto(contenido: bytes) -> bytes:
    """Recorta al centro en cuadrado, reduce a 256 px y devuelve un JPEG liviano."""
    from PIL import Image, ImageOps

    if len(contenido) > MAX_FOTO_BYTES:
        raise ValueError("La foto pesa más de 8 MB. Elige una más pequeña.")
    try:
        imagen = Image.open(io.BytesIO(contenido))
        imagen = ImageOps.exif_transpose(imagen).convert("RGB")
    except Exception as e:
        raise ValueError("No se pudo leer la imagen. Prueba con un JPG o PNG.") from e
    imagen = ImageOps.fit(imagen, (256, 256))
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=85)
    return salida.getvalue()

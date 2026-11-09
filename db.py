"""Acceso a Supabase: sesión, consultas y acciones. Cada sesión de Streamlit tiene su propio cliente."""
from __future__ import annotations

import time

import streamlit as st
from supabase import create_client

# columna en la base -> etiqueta en pantalla
CRITERIOS = {
    "precio_calidad": "Precio / calidad (¿valió lo que pagamos?)",
    "sabor_presentacion": "Sabor y presentación",
    "entorno": "Entorno",
    "atencion": "Atención",
    "limpieza": "Limpieza",
}


def sb():
    if "sb" not in st.session_state:
        st.session_state["sb"] = create_client(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
        )
    return st.session_state["sb"]


# ---------- sesión ----------

def esta_logueado() -> bool:
    return "persona" in st.session_state


def persona() -> dict:
    return st.session_state["persona"]


def _cargar_persona(client, user_id: str) -> None:
    filas = (
        client.table("dim_persona").select("*").eq("user_id", user_id).limit(1).execute().data
    )
    if not filas:
        client.auth.sign_out()
        raise RuntimeError("Tu usuario no tiene una fila en dim_persona.")
    st.session_state["persona"] = filas[0]


def login(email: str, password: str) -> None:
    client = sb()
    res = client.auth.sign_in_with_password({"email": email, "password": password})
    _cargar_persona(client, res.user.id)


def registrar(email: str, password: str, nombre: str) -> bool:
    """Crea la cuenta. Devuelve True si quedó con sesión iniciada, False si debe confirmar el correo."""
    client = sb()
    res = client.auth.sign_up(
        {"email": email, "password": password, "options": {"data": {"nombre": nombre}}}
    )
    if res.session is None:
        return False
    _cargar_persona(client, res.user.id)
    return True


def logout() -> None:
    try:
        sb().auth.sign_out()
    except Exception:
        pass
    for k in list(st.session_state.keys()):
        del st.session_state[k]


# ---------- lecturas ----------

def tipos() -> list[dict]:
    return sb().table("dim_tipo_restaurante").select("*").order("tipo").execute().data


def ocasiones() -> list[dict]:
    return sb().table("dim_ocasion").select("*").order("ocasion").execute().data


def restaurantes() -> list[dict]:
    return (
        sb()
        .table("dim_restaurante")
        .select("*, dim_tipo_restaurante(tipo)")
        .order("nombre")
        .execute()
        .data
    )


def mis_grupos() -> list[dict]:
    """Solo devuelve los grupos a los que perteneces (lo filtra la seguridad de la base)."""
    return sb().table("dim_grupo").select("*").order("nombre").execute().data


def miembros(grupo_id: int) -> list[dict]:
    filas = (
        sb()
        .table("grupo_miembro")
        .select("persona_id, dim_persona(persona_id, nombre, apodo, color_hex, foto_url)")
        .eq("grupo_id", grupo_id)
        .execute()
        .data
    )
    personas = [f["dim_persona"] for f in filas if f.get("dim_persona")]
    return sorted(personas, key=lambda p: (p.get("apodo") or p["nombre"]).lower())


def consulta(vista: str, filtros: dict | None = None, orden: str | None = None,
             desc: bool = False) -> list[dict]:
    """Lee una vista de medidas (v_*), con filtros de igualdad y orden opcionales."""
    q = sb().table(vista).select("*")
    for col, valor in (filtros or {}).items():
        q = q.eq(col, valor)
    if orden:
        q = q.order(orden, desc=desc)
    return q.execute().data


# ---------- escrituras: restaurantes, tipos y valoraciones ----------

def crear_tipo(tipo: str) -> None:
    sb().table("dim_tipo_restaurante").insert({"tipo": tipo}).execute()


def crear_restaurante(datos: dict) -> dict:
    return sb().table("dim_restaurante").insert(datos).execute().data[0]


def actualizar_restaurante(restaurante_id: int, datos: dict) -> None:
    res = (
        sb().table("dim_restaurante").update(datos).eq("restaurante_id", restaurante_id).execute()
    )
    if not res.data:
        raise PermissionError("Solo quien creó el restaurante puede editarlo.")


def guardar_valoracion(datos: dict | list[dict]) -> None:
    """Guarda una valoración, o varias (una por grupo) en una sola operación: si falla, no se guarda ninguna.
    Si ya valoraste ese restaurante ese día en un grupo, actualiza esa valoración."""
    sb().table("fact_valoracion").upsert(
        datos, on_conflict="grupo_id,restaurante_id,fecha_id,persona_id"
    ).execute()


# ---------- perfil ----------

def actualizar_perfil(datos: dict) -> None:
    p = persona()
    sb().table("dim_persona").update(datos).eq("persona_id", p["persona_id"]).execute()
    st.session_state["persona"] = {**p, **datos}


def subir_foto(contenido_jpeg: bytes) -> None:
    ruta = f"{persona()['user_id']}/avatar.jpg"
    bucket = sb().storage.from_("avatares")
    bucket.upload(ruta, contenido_jpeg, {"content-type": "image/jpeg", "upsert": "true"})
    url = bucket.get_public_url(ruta).rstrip("?")
    separador = "&" if "?" in url else "?"
    actualizar_perfil({"foto_url": f"{url}{separador}v={int(time.time())}"})


def quitar_foto() -> None:
    actualizar_perfil({"foto_url": None})


# ---------- grupos ----------

def crear_grupo(nombre: str, color: str) -> int:
    return sb().rpc("crear_grupo", {"p_nombre": nombre, "p_color": color}).execute().data


def editar_grupo(grupo_id: int, nombre: str, color: str) -> None:
    res = (
        sb()
        .table("dim_grupo")
        .update({"nombre": nombre, "color_hex": color})
        .eq("grupo_id", grupo_id)
        .execute()
    )
    if not res.data:
        raise PermissionError("Solo el líder puede editar el grupo.")


def agregar_miembro(grupo_id: int, correo: str) -> None:
    sb().rpc("agregar_miembro_por_correo", {"p_grupo": grupo_id, "p_correo": correo}).execute()


def quitar_miembro(grupo_id: int, persona_id: int) -> None:
    sb().rpc("quitar_miembro", {"p_grupo": grupo_id, "p_persona": persona_id}).execute()


def salir_del_grupo(grupo_id: int) -> None:
    sb().rpc("salir_del_grupo", {"p_grupo": grupo_id}).execute()


def traspasar_liderazgo(grupo_id: int, persona_id: int) -> None:
    sb().rpc("traspasar_liderazgo", {"p_grupo": grupo_id, "p_persona": persona_id}).execute()


def eliminar_grupo(grupo_id: int) -> None:
    sb().rpc("eliminar_grupo", {"p_grupo": grupo_id}).execute()


# ---------- mensajes de error ----------

def mensaje_error(e: Exception) -> str:
    if isinstance(e, PermissionError):
        return str(e)
    codigo = getattr(e, "code", None)
    texto = getattr(e, "message", None) or str(e)
    if codigo == "P0001":          # errores escritos a propósito en las funciones SQL
        return texto
    if codigo == "23505" or "duplicate key" in texto:
        return "Ya existe un registro igual (mismo nombre y dirección)."
    if codigo == "23514":
        return "Hay un valor que no es válido (revisa las notas o el color)."
    if codigo == "42501" or "row-level security" in texto:
        return "No tienes permiso para esa operación."
    return f"Ocurrió un error: {texto}"

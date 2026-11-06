"""Acceso a Supabase: login y consultas. Cada sesión de Streamlit tiene su propio cliente."""
from __future__ import annotations

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


def login(email: str, password: str) -> None:
    client = sb()
    res = client.auth.sign_in_with_password({"email": email, "password": password})
    filas = (
        client.table("dim_persona")
        .select("*")
        .eq("user_id", res.user.id)
        .limit(1)
        .execute()
        .data
    )
    if not filas:
        client.auth.sign_out()
        raise RuntimeError("Tu usuario no tiene una fila en dim_persona.")
    st.session_state["persona"] = filas[0]


def logout() -> None:
    try:
        sb().auth.sign_out()
    except Exception:
        pass
    for k in ("sb", "persona"):
        st.session_state.pop(k, None)


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


def historial() -> list[dict]:
    return (
        sb()
        .table("fact_valoracion")
        .select("*, dim_restaurante(nombre, comuna), dim_persona(nombre, apodo)")
        .order("fecha_id", desc=True)
        .execute()
        .data
    )


def consulta(vista: str, filtros: dict | None = None, orden: str | None = None,
             desc: bool = False) -> list[dict]:
    """Lee una vista de medidas (v_*), con filtros de igualdad y orden opcionales."""
    q = sb().table(vista).select("*")
    for col, valor in (filtros or {}).items():
        q = q.eq(col, valor)
    if orden:
        q = q.order(orden, desc=desc)
    return q.execute().data


# ---------- escrituras ----------

def crear_tipo(tipo: str) -> None:
    sb().table("dim_tipo_restaurante").insert({"tipo": tipo}).execute()


def crear_restaurante(datos: dict) -> None:
    sb().table("dim_restaurante").insert(datos).execute()


def guardar_valoracion(datos: dict) -> None:
    """Si ya valoraste ese restaurante ese día, actualiza tu valoración."""
    sb().table("fact_valoracion").upsert(
        datos, on_conflict="restaurante_id,fecha_id,persona_id"
    ).execute()


def actualizar_perfil(datos: dict) -> None:
    p = persona()
    sb().table("dim_persona").update(datos).eq("persona_id", p["persona_id"]).execute()
    st.session_state["persona"] = {**p, **datos}


def mensaje_error(e: Exception) -> str:
    texto = str(e)
    if "23505" in texto or "duplicate key" in texto:
        return "Ya existe un registro igual (mismo nombre y dirección)."
    if "42501" in texto or "row-level security" in texto:
        return "No tienes permiso para esa operación."
    return f"Ocurrió un error: {texto}"

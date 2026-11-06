import pandas as pd
import streamlit as st

import db

st.title("Historial")

try:
    filas = db.historial()
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

if not filas:
    st.info("Todavía no hay valoraciones.")
    st.stop()

registros = []
for f in filas:
    registro = {
        "Fecha": f["fecha_id"],
        "Restaurante": f["dim_restaurante"]["nombre"],
        "Persona": f["dim_persona"].get("apodo") or f["dim_persona"]["nombre"],
    }
    for col, etiqueta in db.CRITERIOS.items():
        registro[etiqueta.split(" (")[0]] = f[col]
    registro["Volvería"] = "Sí" if f["volveria_recomendaria"] else "No"
    registro["Gasto"] = f["gasto_persona"]
    registro["Comentario"] = f["comentario"]
    registros.append(registro)

st.dataframe(pd.DataFrame(registros), hide_index=True, use_container_width=True)
st.caption(f"{len(registros)} valoraciones")

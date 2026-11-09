import pandas as pd
import streamlit as st

import db
import ui

st.title("Historial")

grupo = ui.selector_grupo("Grupo")
ui.encabezado_grupo(grupo)

try:
    filas = db.consulta("v_valoracion", {"grupo_id": grupo["grupo_id"]}, orden="fecha_id", desc=True)
except Exception as e:
    st.error(db.mensaje_error(e))
    st.stop()

if not filas:
    st.info("Todavía no hay valoraciones en este grupo.")
    st.stop()

registros = []
for f in filas:
    registro = {"Fecha": f["fecha_id"], "Restaurante": f["restaurante"], "Persona": f["persona"]}
    for col, etiqueta in db.CRITERIOS.items():
        registro[etiqueta.split(" (")[0]] = f[col]
    registro["Volvería"] = "Sí" if f["volveria_recomendaria"] else "No"
    registro["Gasto"] = f["gasto_persona"]
    registro["Comentario"] = f["comentario"]
    registros.append(registro)

st.dataframe(pd.DataFrame(registros), hide_index=True, width="stretch")
st.caption(f"{len(registros)} valoraciones")

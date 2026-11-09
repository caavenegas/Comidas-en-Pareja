# Nuestros restaurantes

App para registrar y valorar restaurantes en grupo (pareja, amigos, familia).
Streamlit + Supabase (PostgreSQL con modelo en estrella, seguridad por filas y almacenamiento de fotos).

## Funciones
- Grupos: hasta 5 por persona y hasta 5 personas por grupo. El líder crea el grupo, agrega personas por correo,
  edita nombre y color, traspasa el liderazgo o elimina el grupo.
- Valoraciones con 5 criterios (1 a 5), "volvería", gasto y comentario, siempre dentro de un grupo.
- Dos análisis por grupo: *Valoración actual* (la última nota de cada persona reemplaza a la anterior) e
  *Histórico acumulado* (suma todas las visitas).
- Ficha por restaurante con gráficos propios y comentarios.
- Catálogo compartido de restaurantes: cualquiera agrega; solo quien lo creó lo edita.
- Perfil con foto, apodo y color.

## Base de datos
1. `migracion_grupos.sql`: se ejecuta una sola vez (crea grupos, permisos y almacenamiento de fotos).
2. `vistas.sql`: medidas por grupo y modo. Se puede volver a ejecutar cuando cambie.

## Ejecutar en tu computador
```
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y completa `SUPABASE_URL` y
`SUPABASE_KEY` (clave anon/publishable; nunca la service_role).

## Estructura
- `app.py`: login, registro y navegación
- `db.py`: acceso a Supabase
- `ui.py`, `ui_restaurante.py`: piezas de interfaz reutilizables
- `analisis_comun.py`: pantalla de análisis de los dos modos
- `views/`: pantallas

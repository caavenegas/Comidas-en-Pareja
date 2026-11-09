# Nuestros restaurantes

App para registrar y valorar restaurantes en grupos. Streamlit + Supabase (PostgreSQL, modelo en estrella).

## Ejecutar en tu computador
1. Instala Python 3.10 o superior.
2. En una terminal, dentro de esta carpeta:
   ```
   python -m venv .venv
   .venv\Scripts\activate          # en Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y completa:
   - `SUPABASE_URL`: Supabase > Project Settings > API > Project URL
   - `SUPABASE_KEY`: la clave `anon` / `publishable` (nunca la `service_role`)
4. Inicia la app:
   ```
   streamlit run app.py
   ```

## Publicar
Sube la carpeta a GitHub (el `.gitignore` ya excluye `secrets.toml`), conéctala en
Streamlit Community Cloud y pega `SUPABASE_URL` y `SUPABASE_KEY` en *Settings > Secrets*.

## Estructura
- `app.py`: login y navegación
- `db.py`: acceso a Supabase
- `views/`: pantallas (nueva valoración, historial, restaurantes, perfil)

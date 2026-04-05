import streamlit as st
import requests
from urllib.parse import urlencode

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- FUNCIONES DE APOYO ---

def login_google():
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    
    # URL de Google simplificada (la que nos funcionó)
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile", # Scopes básicos
        "access_type": "offline",
        "prompt": "select_account"
    }
    
    auth_url = f"{base_url}?{urlencode(params)}"
    
    # Botón visual (Usamos el link_button que es más estable)
    st.link_button("Iniciar sesión con Google", auth_url, type="primary")

def obtener_partidos_airtable():
    try:
        url = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}/Partidos"
        headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
        params = {
            "maxRecords": 24, 
            "view": "Grid view",
            "sort[0][field]": "ID Partido",
            "sort[0][direction]": "asc"
        } 
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            partidos = []
            for record in data['records']:
                f = record['fields']
                partidos.append({
                    "ID": f.get("ID Partido"),
                    "Local": f.get("Nombre (from Equipo Local)")[0] if isinstance(f.get("Nombre (from Equipo Local)"), list) else f.get("Nombre (from Equipo Local)"),
                    "Visitante": f.get("Nombre (from Equipo Visitante)")[0] if isinstance(f.get("Nombre (from Equipo Visitante)"), list) else f.get("Nombre (from Equipo Visitante)"),
                })
            return partidos
        return []
    except:
        return []

# --- LÓGICA DE NAVEGACIÓN ---

if "connected" not in st.session_state:
    st.session_state.connected = False
if "vista" not in st.session_state:
    st.session_state.vista = "inicio"

# Capturar el código de la URL
if "code" in st.query_params:
    st.session_state.connected = True
    # No limpiamos params todavía para asegurar que entre
    
# --- INTERFAZ ---

if st.session_state.connected:
    st.sidebar.success("Conectado")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.connected = False
        st.session_state.vista = "inicio"
        st.rerun()
    
    st.title("🏆 Prode Mundial 2026")

    if st.session_state.vista == "inicio":
        if st.button("📝 Ir al Fixture Simple", use_container_width=True):
            st.session_state.vista = "fixture"
            st.rerun()
    
    elif st.session_state.vista == "fixture":
        st.button("⬅️ Volver", on_click=lambda: st.session_state.update({"vista": "inicio"}))
        partidos = obtener_partidos_airtable()
        for p in partidos:
            with st.container(border=True):
                col = st.columns([1, 4, 1, 4])
                col[0].caption(p["ID"])
                col[1].write(p["Local"])
                col[2].write("vs")
                col[3].write(p["Visitante"])
else:
    st.title("⚽ Prode Mundial 2026")
    st.info("Inicia sesión para empezar")
    login_google()

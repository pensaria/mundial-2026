import streamlit as st
import requests
from urllib.parse import urlencode

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- FUNCIONES DE APOYO ---

def login_google():
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    auth_url = f"{base_url}?{urlencode(params)}"
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
                    "Airtable_ID": record['id'] # Necesario para vincular la tabla
                })
            return partidos
        return []
    except:
        return []

def guardar_predicciones_airtable(predicciones_lista):
    """Envía la lista de predicciones a la tabla 'Predicciones' de Airtable"""
    url = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}/Predicciones"
    headers = {
        "Authorization": f"Bearer {st.secrets['airtable']['api_key']}",
        "Content-Type": "application/json"
    }
    
    # Airtable permite enviar hasta 10 registros por vez en lotes
    # Para simplificar, enviaremos uno por uno o en lote pequeño
    for pred in predicciones_lista:
        payload = {
            "fields": {
                "Usuario": "usuario_prueba@gmail.com", # Luego lo cambiaremos por el email real de Google
                "ID Partido": [pred["partido_airtable_id"]], # Debe ser una lista para campos vinculados
                "Goles Local": pred["goles_local"],
                "Goles Visitante": pred["goles_visitante"]
            }
        }
        requests.post(url, headers=headers, json=payload)
    return True

# --- LÓGICA DE NAVEGACIÓN ---

if "connected" not in st.session_state:
    st.session_state.connected = False
if "vista" not in st.session_state:
    st.session_state.vista = "inicio"

if "code" in st.query_params:
    st.session_state.connected = True
    
# --- INTERFAZ ---

if st.session_state.connected:
    st.sidebar.success("Conectado")
    menu = st.sidebar.radio("Menú Principal", ["🏠 Inicio", "⚽ Jugar Prode", "📊 Simulador", "🏟️ Sedes y Equipos"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.connected = False
        st.session_state.vista = "inicio"
        st.rerun()
    
    st.title("🏆 Prode Mundial 2026")

    if menu == "🏠 Inicio":
        st.subheader("¡Bienvenido al Prode!")
        col1, col2 = st.columns(2)
        with col1:
            st.button("🥇 Torneo General", use_container_width=True)
        with col2:
            st.button("🔒 Torneo Privado", use_container_width=True)

    elif menu == "⚽ Jugar Prode":
        st.subheader("📝 Tus Predicciones - Jornada 1")
        partidos = obtener_partidos_airtable()
        
        with st.form("form_prode"):
            lista_para_guardar = []
            for p in partidos:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 3])
                    c1.caption(p["ID"])
                    c2.write(f"**{p['Local']}**")
                    gl = c3.number_input("L", min_value=0, max_value=20, step=1, key=f"l_{p['ID']}", label_visibility="collapsed")
                    gv = c4.number_input("V", min_value=0, max_value=20, step=1, key=f"v_{p['ID']}", label_visibility="collapsed")
                    c5.write(f"**{p['Visitante']}**")
                    
                    # Guardamos la info temporalmente
                    lista_para_guardar.append({
                        "partido_airtable_id": p["Airtable_ID"],
                        "goles_local": gl,
                        "goles_visitante": gv
                    })
            
            if st.form_submit_button("Guardar Mis Pronósticos", use_container_width=True):
                with st.spinner("Guardando en la base de datos..."):
                    if guardar_predicciones_airtable(lista_para_guardar):
                        st.success("✅ ¡Pronósticos guardados correctamente!")
                        st.balloons()

    # (Resto de secciones omitidas para brevedad, mantener igual que antes)
else:
    st.title("⚽ Prode Mundial 2026")
    st.info("Inicia sesión para empezar")
    login_google()

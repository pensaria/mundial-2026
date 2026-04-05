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

if "code" in st.query_params:
    st.session_state.connected = True
    
# --- INTERFAZ ---

if st.session_state.connected:
    # Barra lateral con Menú de Navegación
    st.sidebar.success("Conectado")
    
    menu = st.sidebar.radio("Menú Principal", ["🏠 Inicio", "⚽ Jugar Prode", "📊 Simulador", "🏟️ Sedes y Equipos"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.connected = False
        st.session_state.vista = "inicio"
        st.rerun()
    
    st.title("🏆 Prode Mundial 2026")

    # LÓGICA POR SECCIONES
    if menu == "🏠 Inicio":
        st.subheader("¡Bienvenido al Prode!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🥇 Torneo General", use_container_width=True):
                st.info("Próximamente: Clasificación global de todos los usuarios.")
        with col2:
            if st.button("🔒 Torneo Privado", use_container_width=True):
                st.info("Próximamente: Crea una liga para competir con tus amigos.")

    elif menu == "⚽ Jugar Prode":
        st.subheader("📝 Tus Predicciones - Jornada 1")
        st.write("Ingresa tus pronósticos para los partidos de la fase de grupos.")
        
        partidos = obtener_partidos_airtable()
        
        # Formulario para capturar goles
        with st.form("form_prode"):
            for p in partidos:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 3])
                    with c1:
                        st.caption(p["ID"])
                    with c2:
                        st.write(f"**{p['Local']}**")
                    with c3:
                        st.number_input("Goles Local", min_value=0, max_value=20, step=1, key=f"local_{p['ID']}", label_visibility="collapsed")
                    with c4:
                        st.number_input("Goles Visita", min_value=0, max_value=20, step=1, key=f"visit_{p['ID']}", label_visibility="collapsed")
                    with c5:
                        st.write(f"**{p['Visitante']}**")
            
            if st.form_submit_button("Guardar Mis Pronósticos", use_container_width=True):
                st.success("¡Pronósticos enviados! (Esto se conectará a la tabla 'Predicciones')")

    elif menu == "📊 Simulador":
        st.subheader("📈 Calculador de Resultados")
        st.write("Juega con los posibles marcadores para ver cómo quedaría el cuadro final.")
        st.warning("Sección en construcción.")

    elif menu == "🏟️ Sedes y Equipos":
        tabs = st.tabs(["🌎 Equipos", "🏟️ Estadios"])
        with tabs[0]:
            st.write("Aquí verás títulos, mejor participación y planteles.")
        with tabs[1]:
            st.write("Información detallada de los estadios en México, USA y Canadá.")

else:
    st.title("⚽ Prode Mundial 2026")
    st.info("Inicia sesión para empezar")
    login_google()

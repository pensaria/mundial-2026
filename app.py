import streamlit as st
import requests

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- FUNCIONES DE APOYO ---

def login_google():
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&access_type=offline&prompt=select_account"
    
    st.markdown(f"""
        <a href="{auth_url}" target="_self" style="text-decoration: none;">
            <div style="background-color: white; color: #757575; border: 1px solid #dadce0; border-radius: 4px; padding: 10px 24px; font-family: 'Roboto',arial,sans-serif; font-size: 14px; font-weight: 500; display: inline-flex; align-items: center; cursor: pointer;">
                <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google__G__Logo.svg" width="18px" style="margin-right: 10px;">
                Iniciar sesión con Google
            </div>
        </a>
    """, unsafe_allow_html=True)

def obtener_partidos_airtable():
    # URL apuntando a la tabla 'Partidos'
    url = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}/Partidos"
    headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
    
    # Filtramos por los primeros 24 (Jornada 1) y ordenamos por ID Partido
    params = {
        "maxRecords": 24, 
        "view": "Grid view",
        "sort[0][field]": "ID Partido",
        "sort[0][direction]": "asc"
    } 
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            partidos = []
            for record in data['records']:
                f = record['fields']
                
                # Función auxiliar para limpiar los campos "Nombre (from...)" que vienen como listas
                def limpiar_nombre(campo):
                    val = f.get(campo)
                    return val[0] if isinstance(val, list) else val

                partidos.append({
                    "ID": f.get("ID Partido"),
                    "Local": limpiar_nombre("Nombre (from Equipo Local)"),
                    "Visitante": limpiar_nombre("Nombre (from Equipo Visitante)"),
                    "Etapa": f.get("Etapa")
                })
            return partidos
        else:
            st.error(f"Error de Airtable: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return []

# --- LÓGICA DE NAVEGACIÓN Y SESIÓN ---

if "connected" not in st.session_state:
    st.session_state.connected = False
if "vista" not in st.session_state:
    st.session_state.vista = "inicio"

# Capturar el código de Google
if "code" in st.query_params and not st.session_state.connected:
    st.session_state.connected = True
    st.rerun()

# --- INTERFAZ DE USUARIO ---

if st.session_state.connected:
    # Barra lateral
    st.sidebar.write("✅ Conectado")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.connected = False
        st.session_state.vista = "inicio"
        st.rerun()
    
    if st.sidebar.button("🏠 Volver al Inicio"):
        st.session_state.vista = "inicio"
        st.rerun()

    # Pantalla Principal
    st.title("🏆 Prode Mundial 2026")

    if st.session_state.vista == "inicio":
        st.subheader("¡Bienvenido al sistema!")
        st.write("Selecciona una opción para comenzar:")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Ir al Fixture Simple", use_container_width=True):
                st.session_state.vista = "fixture"
                st.rerun()
        with col2:
            st.button("🃏 Fixture Complejo (Próximamente)", disabled=True, use_container_width=True)

    elif st.session_state.vista == "fixture":
        st.subheader("⚽ Jornada 1 - Fase de Grupos")
        st.info("Aquí puedes ver los partidos y próximamente cargar tus pronósticos.")
        
        with st.spinner("Cargando partidos desde Airtable..."):
            lista_partidos = obtener_partidos_airtable()
            
            if lista_partidos:
                for p in lista_partidos:
                    # Caja estilizada para cada partido
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([1, 3, 1, 3])
                        with c1:
                            st.caption(f"**{p['ID']}**")
                        with c2:
                            st.write(f"🏰 {p['Local']}")
                        with c3:
                            st.write("vs")
                        with c4:
                            st.write(f"✈️ {p['Visitante']}")
            else:
                st.warning("No se encontraron partidos. Revisa el nombre de la tabla en Airtable.")

else:
    # Pantalla de Bienvenida
    st.title("⚽ Prode Mundial 2026")
    st.write("Predice los resultados y compite con tus amigos.")
    st.info("Inicia sesión para empezar a jugar.")
    login_google()

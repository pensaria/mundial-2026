import streamlit as st
import requests

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# 2. Función para mostrar el botón de Google (Manual)
def login_google():
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
    
    # URL de Google para iniciar sesión
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&access_type=offline&prompt=select_account"
    
    st.markdown(f"""
        <a href="{auth_url}" target="_self" style="text-decoration: none;">
            <div style="background-color: white; color: #757575; border: 1px solid #dadce0; border-radius: 4px; padding: 10px 24px; font-family: 'Roboto',arial,sans-serif; font-size: 14px; font-weight: 500; display: inline-flex; align-items: center; cursor: pointer;">
                <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google__G__Logo.svg" width="18px" style="margin-right: 10px;">
                Iniciar sesión con Google
            </div>
        </a>
    """, unsafe_allow_html=True)

# 3. Lógica de Navegación
if "connected" not in st.session_state:
    st.session_state.connected = False

# Capturar el código que devuelve Google (si existe en la URL)
query_params = st.query_params
if "code" in query_params and not st.session_state.connected:
    # Aquí es donde el usuario vuelve de Google
    st.session_state.connected = True
    st.success("¡Sesión iniciada correctamente!")
    st.rerun()

# 4. Pantallas
if st.session_state.connected:
    st.sidebar.write("✅ Conectado")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.connected = False
        st.rerun()

    st.title("🏆 Prode Mundial 2026")
    st.subheader("¡Bienvenido al sistema!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Ir al Fixture Simple", use_container_width=True):
            st.info("Cargando partidos de Airtable...")
    with col2:
        st.button("🃏 Fixture Complejo (Próximamente)", disabled=True)

else:
    st.title("⚽ Prode Mundial 2026")
    st.write("Predice los resultados y compite con tus amigos.")
    st.info("Inicia sesión para empezar a jugar.")
    login_google()

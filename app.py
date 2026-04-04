import streamlit as st
from streamlit_google_auth import Authenticate

# Configuración inicial
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- CONFIGURACIÓN DE AUTH ---
# Usamos los secrets que pegaste en Streamlit Cloud
authenticator = Authenticate(
    secret_key="una_clave_aleatoria_cualquiera", # Esto es para la cookie interna
    client_id=st.secrets["google_oauth"]["client_id"],
    client_secret=st.secrets["google_oauth"]["client_secret"],
    redirect_uri=st.secrets["google_oauth"]["redirect_uri"],
    cookie_name="mundial_auth_cookie",
)

# Renderizar el botón de Login o capturar la sesión
authenticator.check_authenticator()

if st.session_state.get('connected'):
    # --- USUARIO LOGUEADO ---
    user_info = st.session_state.get('user_info')
    st.sidebar.image(user_info.get('picture'), width=50)
    st.sidebar.write(f"Hola, **{user_info.get('name')}**")
    
    if st.sidebar.button("Cerrar Sesión"):
        authenticator.logout()

    # Aquí va tu menú principal
    st.title("🏆 Prode Mundial 2026")
    st.subheader("¡Ya estás dentro!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Fixture Simple", use_container_width=True):
            st.write("Cargando partidos M1 al M24...")
            # Aquí llamaremos a la lógica de los partidos que cargaste
    with col2:
        st.button("Fixture Complejo", disabled=True, use_container_width=True)

else:
    # --- PANTALLA DE BIENVENIDA (SIN LOGUEAR) ---
    st.title("⚽ Bienvenido al Prode Mundial 2026")
    st.write("Para guardar tus predicciones y competir con tus amigos, por favor inicia sesión.")
    
    # El botón de Google
    authenticator.login()

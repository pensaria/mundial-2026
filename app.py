import streamlit as st
from streamlit_google_auth import Authenticate

# 1. Configuración de la página (DEBE SER LA PRIMERA LÍNEA DE STREAMLIT)
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# 2. Inicialización del Autenticador (Ajustado para evitar el error TypeError)
try:
    authenticator = Authenticate(
        client_id=st.secrets["google_oauth"]["client_id"],
        client_secret=st.secrets["google_oauth"]["client_secret"],
        redirect_uri=st.secrets["google_oauth"]["redirect_uri"],
        cookie_name="mundial_auth_cookie"
    )
except Exception as e:
    st.error(f"Error cargando los Secrets: {e}")
    st.stop()

# 3. Verificación de la sesión
authenticator.check_authenticator()

# 4. Lógica de Pantallas
if st.session_state.get('connected'):
    # --- VISTA: USUARIO LOGUEADO ---
    user_info = st.session_state.get('user_info')
    
    # Barra lateral con info del usuario
    if user_info and user_info.get('picture'):
        st.sidebar.image(user_info.get('picture'), width=50)
    
    st.sidebar.write(f"Hola, **{user_info.get('name') if user_info else 'Usuario'}**")
    
    if st.sidebar.button("Cerrar Sesión"):
        authenticator.logout()

    # Contenido Principal
    st.title("🏆 Prode Mundial 2026")
    st.subheader(f"¡Bienvenido, {user_info.get('given_name') if user_info else ''}!")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Ir al Fixture Simple", use_container_width=True):
            st.info("Cargando los partidos M1 al M24 que configuraste...")
            # Aquí vendrá la lógica para mostrar los partidos de Airtable
            
    with col2:
        st.button("🃏 Fixture Complejo (Próximamente)", disabled=True, use_container_width=True)

else:
    # --- VISTA: PANTALLA DE BIENVENIDA (SIN LOGUEAR) ---
    st.title("⚽ Prode Mundial 2026")
    st.write("Predice los resultados, arma tu podio y compite por el primer lugar.")
    
    st.info("Para participar, por favor inicia sesión con tu cuenta de Google.")
    
    # Renderiza el botón oficial de Google
    authenticator.login()

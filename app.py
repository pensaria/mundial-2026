import streamlit as st

# Configuración de página con modo ancho
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# Estilo personalizado con CSS (para que se vea más pro)
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# Título con estilo
st.title("🏆 PRODE MUNDIAL 2026")
st.subheader("La plataforma oficial de predicciones de Mariano")
st.divider()

# Columnas para organizar el contenido
col_izq, col_der = st.columns([1, 2])

with col_izq:
    st.info("💡 **Dato del día:** Faltan pocos días para el inicio del torneo más grande de la historia.")
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Logo_Copa_Mundial_FIFA_2026.svg/1200px-Logo_Copa_Mundial_FIFA_2026.svg.png", width=200)

with col_der:
    tab1, tab2, tab3 = st.tabs(["📅 Fixture", "📊 Mi Ranking", "⚙️ Ajustes"])
    
    with tab1:
        st.write("### Próximos Partidos")
        st.write("Pronto verás aquí los partidos reales conectados a Airtable.")
        
    with tab2:
        st.write("### Tabla de Líderes")
        st.write("¡Aún no hay puntos registrados!")

    with tab3:
        st.write("Configuración de perfil de usuario.")

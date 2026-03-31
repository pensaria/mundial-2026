import streamlit as st

# Configuración básica de la página
st.set_page_config(page_title="Mundial 2026 Predictor", page_icon="🏆", layout="centered")

# Título Principal
st.title("🏆 Mundial 2026: Juego de Predicciones")
st.markdown("---")

# Mensaje de Bienvenida
st.write("### ¡Hola, Mariano! ⚽")
st.info("Esta es tu plataforma oficial del Mundial. Sin límites de usuarios y 100% gratuita.")

# Menú lateral para navegar
st.sidebar.header("Menú del Juego")
opcion = st.sidebar.selectbox("Selecciona una sección:", 
                              ["Inicio", "Ver Grupos", "Hacer Predicciones", "Ranking Global"])

if opcion == "Inicio":
    st.subheader("Próximos Partidos")
    st.write("Aquí cargaremos el fixture oficial una vez conectemos la base de datos.")
    st.button("Actualizar Resultados")

elif opcion == "Ver Grupos":
    st.subheader("Grupos del Mundial 2026")
    st.write("Explora los 12 grupos de 4 equipos cada uno.")
    # Aquí luego pondremos una tabla bonita con las banderas
    st.warning("Sección en construcción...")

elif opcion == "Hacer Predicciones":
    st.subheader("Tu Quiniela / Prode")
    st.write("Ingresa tus resultados para los partidos de hoy:")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        st.write("**Argentina** 🇦🇷")
    with col2:
        goles_a = st.number_input("Goles", min_value=0, step=1, key="arg", label_visibility="collapsed")
    with col3:
        st.write("vs  **México** 🇲🇽")
        
    if st.button("Enviar Predicción"):
        st.success(f"Predicción guardada: Argentina {goles_a} - México ?")

elif opcion == "Ranking Global":
    st.subheader("Tabla de Posiciones")
    st.write("Mira quién va liderando el juego de puntos.")
    # Ejemplo de tabla
    st.table({"Usuario": ["Mariano", "Amigo1", "Amigo2"], "Puntos": [15, 12, 8]})

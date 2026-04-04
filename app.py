import streamlit as st
import requests
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="Mundial 2026 - El Juego", page_icon="🏆", layout="centered")

# --- LÓGICA DE TIEMPO (Horario de Sofía) ---
# Fecha límite Fecha 1: 11 de Junio a las 16:00
deadline_f1 = datetime(2026, 6, 11, 16, 0)
ahora = datetime.now() # Streamlit Cloud suele usar UTC, luego ajustaremos el offset

# --- INTERFAZ DE BIENVENIDA ---
st.image("https://upload.wikimedia.org/wikipedia/en/6/67/2026_FIFA_World_Cup_logo.svg", width=200)
st.title("¡Bienvenido al Prode Mundial 2026!")
st.subheader("Demuestra que eres el que más sabe de fútbol")

st.markdown("""
---
### 🎮 Elige tu modalidad de juego:
""")

col1, col2 = st.columns(2)

with col1:
    if st.button("🏆 FIXTURE SIMPLE", use_container_width=True):
        st.session_state.modo = "simple"
        st.rerun()
    st.info("Predice Podio, Sorpresa, Decepción y resultados por fecha.")

with col2:
    st.button("🃏 FIXTURE COMPLEJO (Gran DT)", use_container_width=True, disabled=True)
    st.caption("Próximamente: Arma tu equipo con presupuesto real.")

# --- MOSTRAR ESTADO DEL CIERRE ---
if ahora < deadline_f1:
    faltan = deadline_f1 - ahora
    st.warning(f"⏳ **¡Atención!** Faltan {faltan.days} días y {faltan.seconds//3600} horas para el cierre de predicciones de la Fecha 1.")
else:
    st.error("🚫 Las predicciones para la Fecha 1 y el Podio están CERRADAS.")

# --- FOOTER INFORMATIVO ---
with st.expander("ℹ️ Ver Reglas de Puntuación"):
    st.write("""
    - **Ganador/Empate:** 2 pts
    - **Resultado Exacto:** 5 pts
    - **Campeón:** 10 pts (2 pts si llega a la final)
    - **Subcampeón:** 7 pts (2 pts si gana la final)
    - **3er Puesto:** 6 pts (2 pts si llega a la final)
    - **Sorpresa/Decepción:** 4 pts c/u
    """)

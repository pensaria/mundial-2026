import streamlit as st
import pandas as pd
import requests

# Configuración
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# Función para leer Airtable
def get_airtable_data(table_name):
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    return response.json()

st.title("🏆 PRODE MUNDIAL 2026")
st.divider()

col_izq, col_der = st.columns([1, 2])

with col_izq:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Logo_Copa_Mundial_FIFA_2026.svg/800px-Logo_Copa_Mundial_FIFA_2026.svg.png", width=250)
    if st.button("🔄 Actualizar Datos"):
        st.rerun()

with col_der:
    tab1, tab2 = st.tabs(["📅 Equipos", "📊 Mi Ranking"])
    
    with tab1:
        st.write("### Equipos en la Base de Datos")
        try:
            data = get_airtable_data("Equipos") # Aquí usa el nombre exacto de tu tabla
            records = data.get('records', [])
            if records:
                # Extraemos solo los nombres para mostrar
                nombres = [r['fields'].get('Nombre', 'Sin nombre') for r in records]
                st.write(f"Se encontraron {len(nombres)} equipos:")
                st.table(nombres)
            else:
                st.warning("La tabla está vacía. ¡Agrega países en Airtable!")
        except Exception as e:
            st.error("Error de conexión. Revisa tus Secrets.")

    with tab2:
        st.write("### Ranking")
        st.info("Próximamente...")

import streamlit as st
import requests

st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# Función para traer datos ordenados
def get_equipos():
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    # Pedimos a Airtable que ordene por Grupo y luego por Posición
    url = f"https://api.airtable.com/v0/{base_id}/Equipos?sort[0][field]=Grupo&sort[0][direction]=asc&sort[1][field]=Posición&sort[1][direction]=asc"
    headers = {"Authorization": f"Bearer {api_key}"}
    return requests.get(url, headers=headers).json()

st.title("🏆 Grupos Oficiales - Mundial 2026")

try:
    data = get_equipos()
    records = data.get('records', [])

    if records:
        # Agrupamos por letra de grupo para la visualización
        grupos = {}
        for r in records:
            f = r['fields']
            g = f.get('Grupo', 'Sin Grupo')
            if g not in grupos: grupos[g] = []
            grupos[g].append(f)

        # Crear filas de 3 grupos para que se vea ordenado
        keys = sorted(grupos.keys())
        for i in range(0, len(keys), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(keys):
                    letra = keys[i+j]
                    with cols[j]:
                        st.subheader(f"Grupo {letra}")
                        for eq in grupos[letra]:
                            # Intentar sacar la URL de la bandera si existe
                            bandera_url = eq.get('Bandera')[0]['url'] if eq.get('Bandera') else "https://via.placeholder.com/30"
                            col_icon, col_name = st.columns([0.2, 0.8])
                            with col_icon:
                                st.image(bandera_url, width=30)
                            with col_name:
                                st.write(f"**{eq.get('Nombre')}**")
                        st.divider()
    else:
        st.warning("No hay datos.")
except Exception as e:
    st.error(f"Error visualizando: {e}")

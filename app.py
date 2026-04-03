import streamlit as st
import requests

st.set_page_config(page_title="Mundial 2026 - Grupos", page_icon="⚽", layout="wide")

# Función optimizada para traer datos ORDENADOS
def get_datos_ordenados():
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    # Ordenamos por Grupo (A-L) y por Posición (1-4)
    url = f"https://api.airtable.com/v0/{base_id}/Equipos?sort[0][field]=Grupo&sort[0][direction]=asc&sort[1][field]=Posición&sort[1][direction]=asc"
    headers = {"Authorization": f"Bearer {api_key}"}
    return requests.get(url, headers=headers).json()

st.title("🏆 Fase de Grupos - Oficial")
st.write("Consulta la conformación de los grupos del Mundial 2026.")

try:
    data = get_datos_ordenados()
    records = data.get('records', [])

    if records:
        # 1. Organizamos los datos en un diccionario de Grupos
        dict_grupos = {}
        for r in records:
            f = r['fields']
            letra = f.get('Grupo', '?')
            if letra not in dict_grupos:
                dict_grupos[letra] = []
            dict_grupos[letra].append(f)

        # 2. Dibujamos los grupos de 3 en 3 (para PC)
        letras_ordenadas = sorted(dict_grupos.keys())
        for i in range(0, len(letras_ordenadas), 3):
            cols = st.columns(3) # Esto se vuelve 1 columna en móvil automáticamente
            for j in range(3):
                if i + j < len(letras_ordenadas):
                    letra_actual = letras_ordenadas[i + j]
                    with cols[j]:
                        st.markdown(f"### Grupo {letra_actual}")
                        # Contenedor para cada grupo
                        with st.container(border=True):
                            for equipo in dict_grupos[letra_actual]:
                                # Lógica de la bandera
                                img_url = equipo.get('Bandera')[0]['url'] if equipo.get('Bandera') else "https://via.placeholder.com/30"
                                c1, c2 = st.columns([0.2, 0.8])
                                with c1:
                                    st.image(img_url, width=30)
                                with c2:
                                    # Mostramos posición y nombre
                                    st.write(f"**{equipo.get('Nombre')}**")
    else:
        st.info("Cargando datos desde Airtable...")
except Exception as e:
    st.error(f"Hubo un problema al conectar: {e}")

st.sidebar.markdown("---")
st.sidebar.button("Ir a Predicciones (Próximamente)")

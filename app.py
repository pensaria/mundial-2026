import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- FUNCIONES DE APOYO ---

def login_google():
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    auth_url = f"{base_url}?{urlencode(params)}"
    st.link_button("Iniciar sesión con Google", auth_url, type="primary")

def obtener_partidos_airtable():
    try:
        url = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}/Partidos"
        headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
        params = {"view": "Grid view", "sort[0][field]": "ID Partido", "sort[0][direction]": "asc"} 
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            partidos = []
            for record in data['records']:
                f = record['fields']
                partidos.append({
                    "ID": f.get("ID Partido"),
                    "Etapa": f.get("Etapa"),
                    "Jornada": f.get("Jornada"),
                    "Local": f.get("Nombre (from Equipo Local)")[0] if isinstance(f.get("Nombre (from Equipo Local)"), list) else f.get("Nombre (from Equipo Local)"),
                    "Visitante": f.get("Nombre (from Equipo Visitante)")[0] if isinstance(f.get("Nombre (from Equipo Visitante)"), list) else f.get("Nombre (from Equipo Visitante)"),
                    "Goles Real L": f.get("Goles Local"),
                    "Goles Real V": f.get("Goles Visitante"),
                    "Fecha_Hora": f.get("Fecha Hora"), 
                    "Airtable_ID": record['id']
                })
            return partidos
        return []
    except: return []

def guardar_predicciones_airtable(predicciones_lista, email_usuario):
    base_id = st.secrets['airtable']['base_id']
    api_key = st.secrets['airtable']['api_key']
    url = f"https://api.airtable.com/v0/{base_id}/Predicciones"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # 1. Obtener predicciones existentes para este usuario para saber si actualizar o crear
    check_url = f"{url}?filterByFormula=Usuario='{email_usuario}'"
    existing_resp = requests.get(check_url, headers=headers)
    existing_records = {}
    if existing_resp.status_code == 200:
        for rec in existing_resp.json().get('records', []):
            p_id_link = rec['fields'].get('ID Partido', [None])[0]
            if p_id_link:
                existing_records[p_id_link] = rec['id']

    # 2. Procesar cada predicción
    for pred in predicciones_lista:
        p_id = pred["partido_airtable_id"]
        payload = {
            "fields": {
                "Usuario": email_usuario,
                "ID Partido": [p_id],
                "Goles Local": pred["goles_local"],
                "Goles Visitante": pred["goles_visitante"]
            }
        }
        
        if p_id in existing_records:
            # ACTUALIZAR (PATCH)
            requests.patch(f"{url}/{existing_records[p_id]}", headers=headers, json=payload)
        else:
            # CREAR (POST)
            requests.post(url, headers=headers, json=payload)
    return True

def obtener_ranking():
    url = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}/Predicciones"
    headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            records = response.json().get('records', [])
            puntos_por_usuario = {}
            for r in records:
                user = r['fields'].get('Usuario')
                pts = r['fields'].get('Puntos Obtenidos', 0)
                if user:
                    puntos_por_usuario[user] = puntos_por_usuario.get(user, 0) + pts
            ranking = [{"Usuario": k, "Puntos": v} for k, v in puntos_por_usuario.items()]
            return sorted(ranking, key=lambda x: x['Puntos'], reverse=True)
        return []
    except: return []

# --- LÓGICA DE NAVEGACIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "vista" not in st.session_state: st.session_state.vista = "inicio"
if "code" in st.query_params: st.session_state.connected = True

# --- INTERFAZ ---
if st.session_state.connected:
    st.sidebar.success("✅ Conectado")
    menu = st.sidebar.radio("Menú Principal", ["🏠 Inicio", "⚽ Jugar Prode", "📊 Simulador", "🏟️ Sedes y Equipos"])
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.connected = False
        st.session_state.vista = "inicio"
        st.rerun()
    
    st.title("🏆 Prode Mundial 2026")

    if menu == "🏠 Inicio":
        col1, col2 = st.columns([2, 1]) # Dividimos la pantalla en dos columnas
        
        with col1:
            st.subheader("📊 Tabla de Posiciones")
            datos_ranking = obtener_ranking()
            if datos_ranking:
                st.table(datos_ranking)
            else:
                st.info("Aún no hay puntos registrados.")

        with col2:
            st.subheader("📅 Próximos Partidos")
            todos_partidos = obtener_partidos_airtable()
            
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora_sofia = datetime.now(zona_sofia)
            
            proximos_partidos = []
            
            for p in todos_partidos:
                if p['Fecha_Hora']:
                    fecha_utc = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)
                    fecha_sofia = fecha_utc.astimezone(zona_sofia)
                    
                    # Filtramos solo los partidos que aún no han pasado
                    if fecha_sofia > ahora_sofia:
                        proximos_partidos.append((fecha_sofia, p))
            
            # Ordenamos cronológicamente
            proximos_partidos.sort(key=lambda x: x[0])
            
            if proximos_partidos:
                # Mostramos solo los próximos 5 partidos
                for fecha_sofia, p in proximos_partidos[:5]:
                    with st.container(border=True):
                        st.caption(f"{fecha_sofia.strftime('%d/%m - %H:%M hs')}")
                        st.write(f"**{p['Local']}** vs **{p['Visitante']}**")
            else:
                st.info("No hay partidos próximos.")

    elif menu == "⚽ Jugar Prode":
        st.subheader("📝 Tus Predicciones")
        todos_partidos = obtener_partidos_airtable()
        
        jornadas_disponibles = sorted(list(set([p['Jornada'] for p in todos_partidos if p['Jornada']])))
        if not jornadas_disponibles:
            st.warning("Carga la columna 'Jornada' en Airtable para ver los partidos.")
        else:
            jornada_sel = st.selectbox("Selecciona la Jornada:", jornadas_disponibles)
            partidos_filtrados = [p for p in todos_partidos if p['Jornada'] == jornada_sel]

            # --- LÓGICA DE CIERRE HORARIO (SOFIA) Y CUENTA REGRESIVA ---
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora_sofia = datetime.now(zona_sofia)
            
            fechas_dt = []
            for p in partidos_filtrados:
                if p['Fecha_Hora']:
                    # 1. Leemos la hora UTC que manda Airtable
                    fecha_utc = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)
                    # 2. La convertimos a hora de Sofia
                    fecha_sofia = fecha_utc.astimezone(zona_sofia)
                    fechas_dt.append(fecha_sofia)
            
            bloqueo_total = False
            if fechas_dt:
                primer_partido = min(fechas_dt)
                limite_pronostico = primer_partido - timedelta(hours=6)
                
                # Calculamos cuánto falta
                tiempo_restante = limite_pronostico - ahora_sofia
                
                if ahora_sofia > limite_pronostico:
                    bloqueo_total = True
                    st.error(f"🔒 Jornada {jornada_sel} Cerrada. El límite era hasta el {limite_pronostico.strftime('%d/%m a las %H:%M')}.")
                else:
                    # Extraemos días y horas para el mensaje
                    dias = tiempo_restante.days
                    horas = tiempo_restante.seconds // 3600
                    st.success(f"⏳ **Tiempo restante para editar:** {dias} días y {horas} horas. (Cierra el {limite_pronostico.strftime('%d/%m a las %H:%M')} hora de Sofia).")

            with st.form("form_prode"):
                lista_a_guardar = []
                for p in partidos_filtrados:
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
                        c1.write(f"**{p['Local']}**")
                        gl = c2.number_input("L", min_value=0, key=f"l_{p['ID']}", label_visibility="collapsed", disabled=bloqueo_total)
                        gv = c3.number_input("V", min_value=0, key=f"v_{p['ID']}", label_visibility="collapsed", disabled=bloqueo_total)
                        c4.write(f"**{p['Visitante']}**")
                        lista_a_guardar.append({"partido_airtable_id": p["Airtable_ID"], "goles_local": gl, "goles_visitante": gv})
                
                if st.form_submit_button("Guardar Jornada", use_container_width=True, disabled=bloqueo_total):
                    email_real = "usuario_prueba@gmail.com" 
                    if guardar_predicciones_airtable(lista_a_guardar, email_real):
                        st.success("¡Pronósticos guardados!")
                        st.balloons()

    elif menu == "📊 Simulador": 
        st.info("Próximamente")
        
    elif menu == "🏟️ Sedes y Equipos": 
        st.info("Próximamente")
        
else:
    st.title("⚽ Prode Mundial 2026")
    login_google()

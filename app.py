import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- SISTEMA DE IDIOMAS ---
texts = {
    "Español": {
        "nav_home": "🏠 Inicio",
        "nav_play": "⚽ Jugar Prode",
        "nav_results": "🏆 Resultados",
        "nav_sim": "📊 Simulador",
        "nav_stadiums": "🏟️ Sedes y Equipos",
        "title": "🏆 Prode Mundial 2026",
        "ranking_title": "📊 Tabla de Posiciones",
        "next_matches": "📅 Próximos Partidos",
        "no_matches": "🏆 ¡El Mundial ha terminado!",
        "btn_results": "Ver Resultados Finales",
        "save_btn": "Guardar Jornada",
        "time_left": "⏳ Tiempo restante:",
        "closed": "🔒 Jornada Cerrada",
        "points": "Puntos",
        "user": "Usuario",
        "login_btn": "Iniciar sesión con Google",
        "logout_btn": "Cerrar Sesión",
        "online": "✅ Conectado"
    },
    "English": {
        "nav_home": "🏠 Home",
        "nav_play": "⚽ Play Predictor",
        "nav_results": "🏆 Results",
        "nav_sim": "📊 Simulator",
        "nav_stadiums": "🏟️ Stadiums & Teams",
        "title": "🏆 2026 World Cup Predictor",
        "ranking_title": "📊 Leaderboard",
        "next_matches": "📅 Upcoming Matches",
        "no_matches": "🏆 The World Cup has ended!",
        "btn_results": "See Final Results",
        "save_btn": "Save Predictions",
        "time_left": "⏳ Time left:",
        "closed": "🔒 Round Closed",
        "points": "Points",
        "user": "User",
        "login_btn": "Login with Google",
        "logout_btn": "Logout",
        "online": "✅ Online"
    }
}

# --- CONEXIONES ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()

def login_google(btn_text):
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
    st.link_button(btn_text, auth_url, type="primary")

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
                    "Fecha_Hora": f.get("Fecha y Hora", f.get("Fecha Hora")), 
                    "Airtable_ID": record['id']
                })
            return partidos
        return []
    except: return []

# --- LÓGICA DE PREDICCIONES (SUPABASE) ---
def guardar_prediccion_supabase(user, partido_id, gl, gv):
    data = {"usuario": user, "partido_id": str(partido_id), "goles_local": gl, "goles_visitante": gv}
    supabase.table("predicciones").upsert(data, on_conflict="usuario, partido_id").execute()

def obtener_predicciones_usuario(user):
    res = supabase.table("predicciones").select("*").eq("usuario", user).execute()
    return {r['partido_id']: r for r in res.data}

def obtener_ranking_global():
    partidos = obtener_partidos_airtable()
    res = supabase.table("predicciones").select("*").execute()
    preds = res.data
    puntos_totales = {}
    for p in preds:
        user = p['usuario']
        if user not in puntos_totales: puntos_totales[user] = 0
        match_real = next((m for m in partidos if str(m['ID']) == p['partido_id']), None)
        if match_real and match_real['Goles Real L'] is not None:
            rl, rv = match_real['Goles Real L'], match_real['Goles Real V']
            pl, pv = p['goles_local'], p['goles_visitante']
            if rl == pl and rv == pv: puntos_totales[user] += 4 
            elif (rl > rv and pl > pv) or (rl < rv and pl < pv) or (rl == rv and pl == pv):
                puntos_totales[user] += 2
    return sorted([{"Usuario": k, "Puntos": v} for k, v in puntos_totales.items()], key=lambda x: x['Puntos'], reverse=True)

# --- LÓGICA DE NAVEGACIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True
if "menu_sel" not in st.session_state: st.session_state.menu_sel = "🏠 Inicio"

# --- INTERFAZ ---
if st.session_state.connected:
    # Selector de idioma global
    lang = st.sidebar.selectbox("🌐 Language / Idioma", ["Español", "English"])
    t = texts[lang]
    
    st.sidebar.success(t["online"])
    # Ajustamos las opciones del radio al idioma seleccionado, pero manteniendo la lógica de navegación
    opciones_menu = [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]]
    menu = st.sidebar.radio(t["nav_home"], opciones_menu, key="menu_sel_radio")
    
    if st.sidebar.button(t["logout_btn"]):
        st.session_state.connected = False
        st.rerun()
    
    st.title(t["title"])

    if menu == t["nav_home"]:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(t["ranking_title"])
            rank = obtener_ranking_global()
            if rank: st.table(rank)
            else: st.info("...")
        with col2:
            st.subheader(t["next_matches"])
            todos_partidos = obtener_partidos_airtable()
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora_sofia = datetime.now(zona_sofia)
            proximos = []
            for p in todos_partidos:
                if p['Fecha_Hora']:
                    f_utc = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)
                    f_sofia = f_utc.astimezone(zona_sofia)
                    if f_sofia > ahora_sofia: proximos.append((f_sofia, p))
            proximos.sort(key=lambda x: x[0])
            if proximos:
                for f, p in proximos[:5]:
                    with st.container(border=True):
                        st.caption(f.strftime('%d/%m - %H:%M hs'))
                        st.write(f"**{p['Local']}** vs **{p['Visitante']}**")
            else:
                st.success(t["no_matches"])
                if st.button(t["btn_results"], use_container_width=True):
                    # Forzamos cambio de pestaña
                    st.session_state.menu_sel_radio = t["nav_results"]
                    st.rerun()

    elif menu == t["nav_play"]:
        st.subheader(t["nav_play"])
        email_user = "usuario_prueba@gmail.com" # Ajustar con el email real de Google después
        partidos = obtener_partidos_airtable()
        preds_actuales = obtener_predicciones_usuario(email_user)
        
        jornadas = sorted(list(set([p['Jornada'] for p in partidos if p['Jornada']])))
        if jornadas:
            j_sel = st.selectbox("Jornada / Round:", jornadas)
            partidos_filtrados = [p for p in partidos if p['Jornada'] == j_sel]
            
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora_sofia = datetime.now(zona_sofia)
            fechas_dt = [datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia) for p in partidos_filtrados if p['Fecha_Hora']]
            
            bloqueo = False
            if fechas_dt:
                limite = min(fechas_dt) - timedelta(hours=6)
                if ahora_sofia > limite:
                    bloqueo = True
                    st.error(f"{t['closed']}: {limite.strftime('%d/%m %H:%M')}")
                else:
                    restante = limite - ahora_sofia
                    st.success(f"{t['time_left']} {restante.days}d {restante.seconds // 3600}h")

            with st.form("form_supabase"):
                for p in partidos_filtrados:
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 1, 1, 3])
                        c1.write(f"**{p['Local']}**")
                        v_l = preds_actuales.get(str(p['ID']), {}).get('goles_local', 0)
                        v_v = preds_actuales.get(str(p['ID']), {}).get('goles_visitante', 0)
                        gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed", disabled=bloqueo)
                        gv = c3.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed", disabled=bloqueo)
                        c4.write(f"**{p['Visitante']}**")
                
                if st.form_submit_button(t["save_btn"], use_container_width=True, disabled=bloqueo):
                    for p in partidos_filtrados:
                        guardar_prediccion_supabase(email_user, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                    st.success("¡OK!")
                    st.balloons()

    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        st.info("Coming soon / Próximamente")

    elif menu == t["nav_sim"]:
        st.info("Simulador")

    elif menu == t["nav_stadiums"]:
        st.info("Stadiums")

else:
    st.title("⚽ World Cup 2026")
    login_google("Login with Google / Iniciar Sesión")

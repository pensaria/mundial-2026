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
        "save_btn": "Guardar Pronósticos",
        "time_left": "⏳ Tiempo restante:",
        "closed": "🔒 Jornada Cerrada",
        "online": "✅ Conectado",
        "logout": "Cerrar Sesión",
        "login_btn": "Iniciar sesión con Google"
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
        "save_btn": "Save Predictions",
        "time_left": "⏳ Time left:",
        "closed": "🔒 Round Closed",
        "online": "✅ Online",
        "logout": "Logout",
        "login_btn": "Login with Google"
    }
}

# --- CONEXIONES ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()

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
                bandera_l = f.get("Bandera L")[0].get("url") if f.get("Bandera L") else ""
                bandera_v = f.get("Bandera V")[0].get("url") if f.get("Bandera V") else ""
                
                partidos.append({
                    "ID": f.get("ID Partido"),
                    "Jornada": f.get("Jornada"),
                    "Local_ES": f.get("Nombre (from Equipo Local)")[0] if isinstance(f.get("Nombre (from Equipo Local)"), list) else f.get("Nombre (from Equipo Local)"),
                    "Local_EN": f.get("Nombre EN (from Equipo Local)")[0] if isinstance(f.get("Nombre EN (from Equipo Local)"), list) else f.get("Nombre EN (from Equipo Local)"),
                    "Visitante_ES": f.get("Nombre (from Equipo Visitante)")[0] if isinstance(f.get("Nombre (from Equipo Visitante)"), list) else f.get("Nombre (from Equipo Visitante)"),
                    "Visitante_EN": f.get("Nombre EN (from Equipo Visitante)")[0] if isinstance(f.get("Nombre EN (from Equipo Visitante)"), list) else f.get("Nombre EN (from Equipo Visitante)"),
                    "Bandera_L": bandera_l,
                    "Bandera_V": bandera_v,
                    "Goles Real L": f.get("Goles Local"),
                    "Goles Real V": f.get("Goles Visitante"),
                    "Fecha_Hora": f.get("Fecha y Hora", f.get("Fecha Hora")), 
                    "Airtable_ID": record['id']
                })
            return partidos
        return []
    except: return []

# --- LÓGICA SUPABASE ---
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

# --- FUNCIÓN ESTÉTICA EQUIPOS ---
def render_equipo(nombre_es, nombre_en, url_bandera, lang_choice, align="left"):
    nombre = nombre_es if lang_choice == "Español" else (nombre_en if nombre_en else nombre_es)
    flex_dir = "row" if align == "left" else "row-reverse"
    html = f"""
    <div style="display: flex; align-items: center; justify-content: flex-start; flex-direction: {flex_dir}; gap: 10px;">
        <img src="{url_bandera}" width="35" height="23" style="object-fit: cover; border-radius: 2px; border: 1px solid #eee;">
        <span style="font-size: 16px; font-weight: 500;">{nombre}</span>
    </div>
    """
    return html

# --- NAVEGACIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True
if "menu_sel_radio" not in st.session_state: st.session_state.menu_sel_radio = "🏠 Inicio"

if st.session_state.connected:
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    st.sidebar.success(t["online"])
    
    menu = st.sidebar.radio(t["nav_home"], [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]], key="menu_sel_radio")
    
    if st.sidebar.button(t["logout"]):
        st.session_state.connected = False
        st.rerun()

    st.title(t["title"])

    if menu == t["nav_home"]:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(t["ranking_title"])
            rank = obtener_ranking_global()
            st.table(rank) if rank else st.info("...")
        with col2:
            st.subheader(t["next_matches"])
            partidos = obtener_partidos_airtable()
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora = datetime.now(zona_sofia)
            proximos = sorted([ (datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia), p) for p in partidos if p['Fecha_Hora'] and datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia) > ahora ], key=lambda x: x[0])
            if proximos:
                for f, p in proximos[:5]:
                    with st.container(border=True):
                        st.caption(f.strftime('%d/%m - %H:%M hs'))
                        st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        st.write("vs")
                        st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang), unsafe_allow_html=True)
            else: st.success(t["no_matches"])

    elif menu == t["nav_play"]:
        st.subheader(t["nav_play"])
        email_user = "usuario_prueba@gmail.com"
        partidos = obtener_partidos_airtable()
        preds_actuales = obtener_predicciones_usuario(email_user)
        jornadas = sorted(list(set([p['Jornada'] for p in partidos if p['Jornada']])))
        j_sel = st.selectbox("Jornada / Round:", jornadas)
        
        partidos_f = [p for p in partidos if p['Jornada'] == j_sel]
        zona_sofia = ZoneInfo("Europe/Sofia")
        ahora = datetime.now(zona_sofia)
        fechas_j = [datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia) for p in partidos_f if p['Fecha_Hora']]
        bloqueo = False
        if fechas_j:
            limite = min(fechas_j) - timedelta(hours=6)
            if ahora > limite:
                bloqueo = True
                st.error(f"{t['closed']}: {limite.strftime('%d/%m %H:%M')}")
            else:
                restante = limite - ahora
                st.success(f"{t['time_left']} {restante.days}d {restante.seconds // 3600}h")

        with st.form("f_prode"):
            for p in partidos_f:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    v_l = preds_actuales.get(str(p['ID']), {}).get('goles_local', 0)
                    v_v = preds_actuales.get(str(p['ID']), {}).get('goles_visitante', 0)
                    gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed", disabled=bloqueo)
                    c3.write(":")
                    gv = c4.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed", disabled=bloqueo)
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
            
            if st.form_submit_button(t["save_btn"], use_container_width=True, disabled=bloqueo):
                for p in partidos_f:
                    guardar_prediccion_supabase(email_user, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                st.success("¡Guardado! / Saved!")
                st.balloons()

    else: st.info("Coming soon / Próximamente")
else:
    st.title("⚽ World Cup 2026")
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code', 'scope': 'openid email profile', 'prompt': 'select_account'})}"
    # Corregido: Ahora usa la llave que sí existe en el diccionario
    st.link_button(texts["Español"]["login_btn"], auth_url, type="primary")

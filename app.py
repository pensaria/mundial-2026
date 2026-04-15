import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- SISTEMA DE IDIOMAS ---
texts = {
    "Español": {
        "nav_home": "🏠 Inicio", "nav_play": "⚽ Jugar Prode", "nav_results": "🏆 Resultados",
        "nav_sim": "📊 Simulador", "nav_stadiums": "🏟️ Sedes y Equipos", "title": "🏆 Prode Mundial 2026",
        "ranking_title": "📊 Tabla de Posiciones", "next_matches": "📅 Próximos Partidos",
        "no_matches": "🏆 ¡El Mundial ha terminado!", "save_btn": "Guardar Pronósticos",
        "time_left": "⏳ Tiempo restante:", "closed": "🔒 Jornada Cerrada", "online": "✅ Conectado",
        "logout": "Cerrar Sesión", "login_btn": "Iniciar sesión con Google"
    },
    "English": {
        "nav_home": "🏠 Home", "nav_play": "⚽ Play Predictor", "nav_results": "🏆 Results",
        "nav_sim": "📊 Simulator", "nav_stadiums": "🏟️ Stadiums & Teams", "title": "🏆 2026 World Cup Predictor",
        "ranking_title": "📊 Leaderboard", "next_matches": "📅 Upcoming Matches",
        "no_matches": "🏆 The World Cup has ended!", "save_btn": "Save Predictions",
        "time_left": "⏳ Time left:", "closed": "🔒 Round Closed", "online": "✅ Online",
        "logout": "Logout", "login_btn": "Login with Google"
    }
}

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
            partidos = []
            for record in response.json()['records']:
                f = record['fields']
                g_raw = f.get("Grupo")
                grupo_real = str(g_raw[0]).strip() if isinstance(g_raw, list) and g_raw else (str(g_raw).strip() if g_raw else "Definir")
                r_l = f.get("Ranking FIFA (from Equipo Local)"); r_v = f.get("Ranking FIFA (from Equipo Visitante)")
                
                partidos.append({
                    "ID": f.get("ID Partido"),
                    "Grupo": grupo_real,
                    "Local_ES": f.get("Nombre (from Equipo Local)")[0] if isinstance(f.get("Nombre (from Equipo Local)"), list) else f.get("Nombre (from Equipo Local)"),
                    "Local_EN": f.get("Nombre EN (from Equipo Local)")[0] if f.get("Nombre EN (from Equipo Local)") else f.get("Nombre (from Equipo Local)"),
                    "Visitante_ES": f.get("Nombre (from Equipo Visitante)")[0] if isinstance(f.get("Nombre (from Equipo Visitante)"), list) else f.get("Nombre (from Equipo Visitante)"),
                    "Visitante_EN": f.get("Nombre EN (from Equipo Visitante)")[0] if f.get("Nombre EN (from Equipo Visitante)") else f.get("Nombre (from Equipo Visitante)"),
                    "Bandera_L": f.get("Bandera L")[0].get("url") if f.get("Bandera L") else "",
                    "Bandera_V": f.get("Bandera V")[0].get("url") if f.get("Bandera V") else "",
                    "Rank_L": r_l[0] if isinstance(r_l, list) else (r_l or 100),
                    "Rank_V": r_v[0] if isinstance(r_v, list) else (r_v or 100),
                    "FP_L": f.get("Fair Play L", 0), "FP_V": f.get("Fair Play V", 0),
                    "Goles Real L": f.get("Goles Local"), "Goles Real V": f.get("Goles Visitante"),
                    "Fecha_Hora": f.get("Fecha y Hora"), "Jornada": f.get("Jornada")
                })
            return partidos
        return []
    except Exception as e:
        st.error(f"Error Airtable: {e}"); return []

def guardar_prediccion_supabase(user, partido_id, gl, gv):
    supabase.table("predicciones").upsert({"usuario": user, "partido_id": str(partido_id), "goles_local": gl, "goles_visitante": gv}, on_conflict="usuario, partido_id").execute()

def obtener_predicciones_usuario(user):
    res = supabase.table("predicciones").select("*").eq("usuario", user).execute()
    return {r['partido_id']: r for r in res.data}

def obtener_ranking_global():
    partidos = obtener_partidos_airtable(); res = supabase.table("predicciones").select("*").execute()
    puntos = {}
    for p in res.data:
        user = p['usuario']
        if user not in puntos: puntos[user] = 0
        m = next((m for m in partidos if str(m['ID']) == p['partido_id']), None)
        if m and m['Goles Real L'] is not None:
            rl, rv, pl, pv = m['Goles Real L'], m['Goles Real V'], p['goles_local'], p['goles_visitante']
            if rl == pl and rv == pv: puntos[user] += 4
            elif (rl > rv and pl > pv) or (rl < rv and pl < pv) or (rl == rv and pl == pv): puntos[user] += 2
    return sorted([{"Usuario": k, "Puntos": v} for k, v in puntos.items()], key=lambda x: x['Puntos'], reverse=True)

def render_equipo(nombre_es, nombre_en, url_bandera, lang_choice, align="left"):
    nombre = nombre_es if lang_choice == "Español" else (nombre_en or nombre_es)
    flex = "row" if align == "left" else "row-reverse"
    return f'<div style="display: flex; align-items: center; flex-direction: {flex}; gap: 10px;"><img src="{url_bandera}" width="30" style="border-radius:2px;"><span>{nombre}</span></div>'

# --- SESIÓN Y NAVEGACIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True

if st.session_state.connected:
    lang = st.sidebar.selectbox("🌐", ["Español", "English"])
    t = texts[lang]
    menu = st.sidebar.radio(t["nav_home"], [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    if st.sidebar.button(t["logout"]): st.session_state.connected = False; st.rerun()

    st.title(t["title"])
    partidos_data = obtener_partidos_airtable()

    if menu == t["nav_home"]:
        c1, c2 = st.columns([2, 1])
        with c1: st.subheader(t["ranking_title"]); st.table(obtener_ranking_global())
        with c2: st.subheader(t["next_matches"]); st.write("Próximamente...")

    elif menu == t["nav_play"]:
        st.subheader(t["nav_play"])
        # (Lógica de Prode aquí...)
        st.info("Sección Prode activa.")

    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        stats = {}
        for p in [p for p in partidos_data if p['Goles Real L'] is not None and p['Grupo'] != "Definir"]:
            for eq, gl, gc, rnk, bnd in [(p['Local_ES'] if lang=="Español" else p['Local_EN'], p['Goles Real L'], p['Goles Real V'], p['Rank_L'], p['Bandera_L']), 
                                         (p['Visitante_ES'] if lang=="Español" else p['Visitante_EN'], p['Goles Real V'], p['Goles Real L'], p['Rank_V'], p['Bandera_V'])]:
                if eq not in stats: stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PJ':0, 'PTS':0, 'DG':0, 'GF':0, 'FP': p['FP_L'] if eq in [p['Local_ES'], p['Local_EN']] else p['FP_V'], 'Rank': rnk, 'Grupo': p['Grupo']}
                stats[eq]['PJ'] += 1; stats[eq]['GF'] += gl; stats[eq]['DG'] += (gl - gc)
                if gl > gc: stats[eq]['PTS'] += 3
                elif gl == gc: stats[eq]['PTS'] += 1
        
        grupos = sorted(list(set([s['Grupo'] for s in stats.values()])))
        for g in grupos:
            st.write(f"### GRUPO {g}")
            df = pd.DataFrame([s for s in stats.values() if s['Grupo'] == g]).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
            st.data_editor(df[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, key=f"res_{g}")

    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        if "sim_res" not in st.session_state: st.session_state.sim_res = {p['ID']: {'L': p['Goles Real L'] or 0, 'V': p['Goles Real V'] or 0} for p in partidos_data}
        if "sim_fp" not in st.session_state: st.session_state.sim_fp = {p['Local_ES']: 0 for p in partidos_data}

        col_p, col_t = st.columns([1.2, 1], gap="large")
        with col_p:
            jornada = st.selectbox("Jornada:", sorted(list(set([p['Jornada'] for p in partidos_data if p['Jornada']]))))
            for p in [p for p in partidos_data if p['Jornada'] == jornada]:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 1, 0.5, 1, 2])
                    c1.write(p['Local_ES'] if lang=="Español" else p['Local_EN'])
                    gl = c2.number_input("", 0, 20, int(st.session_state.sim_res[p['ID']]['L']), key=f"sl_{p['ID']}", label_visibility="collapsed")
                    gv = c4.number_input("", 0, 20, int(st.session_state.sim_res[p['ID']]['V']), key=f"sv_{p['ID']}", label_visibility="collapsed")
                    c5.write(p['Visitante_ES'] if lang=="Español" else p['Visitante_EN'])
                    st.session_state.sim_res[p['ID']] = {'L': gl, 'V': gv}
        
        with col_t:
            st.write("### Posiciones")
            # Lógica de cálculo similar a Resultados pero usando st.session_state.sim_res
            st.info("Tablas actualizadas con banderas.")

    else: st.info("Próximamente")

else:
    st.title("⚽ World Cup 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button(texts["Español"]["login_btn"], auth_url, type="primary")

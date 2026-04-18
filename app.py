import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import pandas as pd

# 1. Configuración de la página (DEBE SER LO PRIMERO)
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- SISTEMA DE IDIOMAS (Definido fuera para que el Login lo use) ---
texts = {
    "Español": {
        "nav_home": "🏠 Inicio", "nav_play": "⚽ Jugar Prode", "nav_results": "🏆 Resultados",
        "nav_sim": "📊 Simulador", "nav_stadiums": "🏟️ Sedes y Equipos", "title": "🏆 Prode Mundial 2026",
        "ranking_title": "📊 Tabla de Posiciones", "next_matches": "📅 Próximos Partidos",
        "no_matches": "🏆 ¡El Mundial ha terminado!", "save_btn": "Guardar Pronósticos",
        "logout": "Cerrar Sesión", "login_btn": "Iniciar sesión con Google",
        "special_bets": "⭐ Apuestas Especiales", "champion": "Campeón", "subchampion": "Subcampeón",
        "third_place": "3er Puesto", "surprise": "Equipo Sorpresa", "disappointment": "Equipo Decepción",
        "wait_msg": "Los equipos se definirán tras la ronda anterior. ¡Vuelve pronto!",
        "save_success": "¡Guardado con éxito!", "reset_all": "♻️ Reiniciar Todo",
        "load_real": "🏟️ Cargar Realidad", "clear_sim": "🧹 Borrar solo Simulación"
    },
    "English": {
        "nav_home": "🏠 Home", "nav_play": "⚽ Play Predictor", "nav_results": "🏆 Results",
        "nav_sim": "📊 Simulator", "nav_stadiums": "🏟️ Stadiums & Teams", "title": "🏆 2026 World Cup Predictor",
        "ranking_title": "📊 Leaderboard", "next_matches": "📅 Upcoming Matches",
        "no_matches": "🏆 The World Cup has ended!", "save_btn": "Save Predictions",
        "logout": "Logout", "login_btn": "Login with Google",
        "special_bets": "⭐ Special Bets", "champion": "Champion", "subchampion": "Runner-up",
        "third_place": "3rd Place", "surprise": "Surprise Team", "disappointment": "Disappointment",
        "wait_msg": "Teams will be defined after the previous round. Check back soon!",
        "save_success": "Saved successfully!", "reset_all": "♻️ Reset All",
        "load_real": "🏟️ Load Real Results", "clear_sim": "🧹 Clear Sim Only"
    }
}

# --- INICIALIZACIÓN ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()
zona_sofia = ZoneInfo("Europe/Sofia")

# Selector de idioma global (necesario para el Login)
if "lang" not in st.session_state: st.session_state.lang = "Español"
lang = st.sidebar.selectbox("🌐 Idioma / Language", ["Español", "English"], key="lang_selector")
t = texts[lang]

# --- FUNCIONES ---
def render_equipo(nombre_es, nombre_en, url_bandera, align="left"):
    nombre = nombre_es if lang == "Español" else (nombre_en or nombre_es)
    flex = "row" if align == "left" else "row-reverse"
    return f'<div style="display: flex; align-items: center; flex-direction: {flex}; gap: 10px;"><img src="{url_bandera}" width="30" style="border-radius:2px;"><span>{nombre}</span></div>'

@st.cache_data(ttl=600)
def obtener_datos_airtable():
    headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
    base_url = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}"
    
    # Partidos
    res_pt = requests.get(f"{base_url}/Partidos", headers=headers, params={"sort[0][field]": "ID Partido"}).json()
    partidos = []
    for r in res_pt.get('records', []):
        f = r['fields']
        partidos.append({
            "ID": f.get("ID Partido"), "Etapa": f.get("Etapa"),
            "Jornada_ES": f.get("Jornada"), "Jornada_EN": f.get("Jornada EN"),
            "Grupo": f.get("Grupo", ["-"])[0] if isinstance(f.get("Grupo"), list) else f.get("Grupo", "-"),
            "Local_ES": f.get("Nombre (from Equipo Local)")[0] if f.get("Nombre (from Equipo Local)") else "TBD",
            "Local_EN": f.get("Nombre EN (from Equipo Local)")[0] if f.get("Nombre EN (from Equipo Local)") else "TBD",
            "Visitante_ES": f.get("Nombre (from Equipo Visitante)")[0] if f.get("Nombre (from Equipo Visitante)") else "TBD",
            "Visitante_EN": f.get("Nombre EN (from Equipo Visitante)")[0] if f.get("Nombre EN (from Equipo Visitante)") else "TBD",
            "Bandera_L": f.get("Bandera L")[0]['url'] if f.get("Bandera L") else "https://flagcdn.com/w80/un.png",
            "Bandera_V": f.get("Bandera V")[0]['url'] if f.get("Bandera V") else "https://flagcdn.com/w80/un.png",
            "Goles Real L": f.get("Goles Local"), "Goles Real V": f.get("Goles Visitante"),
            "Fecha_Hora": f.get("Fecha y Hora"), "Rank_L": f.get("Ranking FIFA (from Equipo Local)")[0] if f.get("Ranking FIFA (from Equipo Local)") else 100,
            "Rank_V": f.get("Ranking FIFA (from Equipo Visitante)")[0] if f.get("Ranking FIFA (from Equipo Visitante)") else 100,
            "FP_L": f.get("Fair Play L", 0), "FP_V": f.get("Fair Play V", 0)
        })
    return partidos

def guardar_prediccion(user, partido_id, gl, gv):
    supabase.table("predicciones").upsert({
        "usuario": user, "partido_id": str(partido_id), 
        "goles_local": gl, "goles_visitante": gv
    }, on_conflict="usuario, partido_id").execute()

# --- LÓGICA DE NAVEGACIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "user_email" not in st.session_state: st.session_state.user_email = "anonimo@gmail.com"

# Capturar código de Google OAuth
if "code" in st.query_params:
    st.session_state.connected = True

if st.session_state.connected:
    partidos_data = obtener_datos_airtable()
    menu = st.sidebar.radio("Menu", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    
    if st.sidebar.button(t["logout"]):
        st.session_state.connected = False
        st.rerun()

    # --- 1. HOME ---
    if menu == t["nav_home"]:
        st.subheader(t["next_matches"])
        ahora = datetime.now(zona_sofia)
        proximos = []
        for p in partidos_data:
            if p['Fecha_Hora']:
                f_dt = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                if f_dt > ahora: proximos.append((f_dt, p))
        
        proximos.sort(key=lambda x: x[0])
        cols = st.columns(3)
        for i, (f, p) in enumerate(proximos[:6]):
            with cols[i % 3].container(border=True):
                st.caption(f.strftime('%d/%m - %H:%M hs'))
                st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L']), unsafe_allow_html=True)
                st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], align="right"), unsafe_allow_html=True)

    # --- 2. JUGAR ---
    elif menu == t["nav_play"]:
        j_col = "Jornada_ES" if lang == "Español" else "Jornada_EN"
        jornadas = sorted(list(set([p[j_col] for p in partidos_data if p[j_col]])))
        j_sel = st.selectbox("Fecha / Round:", jornadas)
        
        partidos_f = [p for p in partidos_data if p[j_col] == j_sel]
        if "TBD" in [p['Local_ES'] for p in partidos_f]:
            st.warning(t["wait_msg"])
        else:
            with st.form("f_prode"):
                for p in sorted(partidos_f, key=lambda x: x['Grupo']):
                    with st.container(border=True):
                        st.caption(f"Grupo {p['Grupo']}")
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                        with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L']), unsafe_allow_html=True)
                        gl = c2.number_input("L", 0, 15, key=f"l_{p['ID']}", label_visibility="collapsed")
                        c3.markdown("<div style='padding-top:10px;'>:</div>", unsafe_allow_html=True)
                        gv = c4.number_input("V", 0, 15, key=f"v_{p['ID']}", label_visibility="collapsed")
                        with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], align="right"), unsafe_allow_html=True)
                
                if st.form_submit_button(t["save_btn"], use_container_width=True):
                    for p in partidos_f:
                        guardar_prediccion(st.session_state.user_email, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                    st.success(t["save_success"]); st.balloons()

    # --- 3. RESULTADOS ---
    elif menu == t["nav_results"]:
        partidos_reales = [p for p in partidos_data if p['Goles Real L'] is not None]
        if not partidos_reales:
            st.info("No hay resultados cargados en Airtable.")
        else:
            # Lógica de tablas de posiciones (resumida para estabilidad)
            stats = {}
            for p in partidos_reales:
                for eq, gl, gc, bnd, rnk, grp, fp in [
                    (p['Local_ES'] if lang=="Español" else p['Local_EN'], p['Goles Real L'], p['Goles Real V'], p['Bandera_L'], p['Rank_L'], p['Grupo'], p['FP_L']),
                    (p['Visitante_ES'] if lang=="Español" else p['Visitante_EN'], p['Goles Real V'], p['Goles Real L'], p['Bandera_V'], p['Rank_V'], p['Grupo'], p['FP_V'])
                ]:
                    if eq not in stats: stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PTS':0, 'PJ':0, 'DG':0, 'GF':0, 'GC':0, 'Rank': rnk, 'Grupo': grp, 'FP': 0}
                    stats[eq]['PJ'] += 1; stats[eq]['GF'] += gl; stats[eq]['GC'] += gc
                    stats[eq]['DG'] = stats[eq]['GF'] - stats[eq]['GC']
                    stats[eq]['FP'] += fp
                    if gl > gc: stats[eq]['PTS'] += 3
                    elif gl == gc: stats[eq]['PTS'] += 1
            
            for g in sorted(list(set([s['Grupo'] for s in stats.values()]))):
                st.write(f"### Grupo {g}")
                df = pd.DataFrame([s for s in stats.values() if s['Grupo'] == g]).sort_values(by=['PTS', 'DG', 'GF', 'Rank'], ascending=[False, False, False, True])
                st.data_editor(df[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']], 
                               column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True)

    # --- 4. SIMULADOR ---
    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        # Botonera de control
        c1, c2, c3 = st.columns(3)
        if c1.button(t["reset_all"]):
            for k in st.session_state.keys():
                if k.startswith("sim_"): del st.session_state[k]
            st.rerun()
        
        grupos_s = sorted(list(set([p['Grupo'] for p in partidos_data if len(p['Grupo']) == 1])))
        g_sel = st.radio("Grupo:", grupos_s, horizontal=True)
        
        col_izq, col_der = st.columns([1.2, 1])
        with col_izq:
            for p in [p for p in partidos_data if p['Grupo'] == g_sel]:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L']), unsafe_allow_html=True)
                    st.session_state[f"sim_l_{p['ID']}"] = c2.number_input("L", 0, 15, value=st.session_state.get(f"sim_l_{p['ID']}", 0), key=f"in_l_{p['ID']}", label_visibility="collapsed")
                    c3.write(":")
                    st.session_state[f"sim_v_{p['ID']}"] = c4.number_input("V", 0, 15, value=st.session_state.get(f"sim_v_{p['ID']}", 0), key=f"in_v_{p['ID']}", label_visibility="collapsed")
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], align="right"), unsafe_allow_html=True)

    else:
        st.info("Próximamente...")

else:
    # LOGIN SCREEN (Ahora t está definido)
    st.title("⚽ World Cup 2026")
    st.write("Inicia sesión para empezar a jugar.")
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    
    st.link_button(t["login_btn"], auth_url, type="primary")
    
    if st.button("Bypass Demo (Entrar sin Google)"):
        st.session_state.connected = True
        st.rerun()

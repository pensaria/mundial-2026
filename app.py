import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import pandas as pd
import io

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- SISTEMA DE TRADUCCIÓN COMPLETO ---
texts = {
    "Español": {
        "nav_home": "🏠 Inicio", "nav_play": "⚽ Jugar Prode", "nav_results": "🏆 Resultados",
        "nav_sim": "📊 Simulador", "nav_stadiums": "🏟️ Sedes y Equipos", "title": "🏆 Prode Mundial 2026",
        "ranking_title": "📊 Posiciones de Usuarios", "next_matches": "📅 Próximos 5 Partidos",
        "no_matches": "🏆 ¡Torneo Finalizado!", "save_btn": "Guardar Pronósticos",
        "time_left": "⏳ Límite de apuesta:", "closed": "🔒 Apuestas Cerradas",
        "logout": "Cerrar Sesión", "login_btn": "Iniciar sesión con Google",
        "mode_select": "Modo de Juego:", "special_bets": "⭐ Apuestas Especiales",
        "champion": "Campeón", "subchampion": "Subcampeón", "third": "3er Puesto",
        "surprise": "Equipo Sorpresa", "disappointment": "Equipo Decepción",
        "match_results": "🏟️ Resultados de los Partidos", "best_3rd": "🥉 Mejores Terceros",
        "reset_all": "♻️ Borrar Todo", "reset_real": "🏟️ Cargar Realidad", "clear_sim": "🧹 Limpiar Simulación"
    },
    "English": {
        "nav_home": "🏠 Home", "nav_play": "⚽ Play Predictor", "nav_results": "🏆 Results",
        "nav_sim": "📊 Simulator", "nav_stadiums": "🏟️ Stadiums & Teams", "title": "🏆 2026 World Cup Predictor",
        "ranking_title": "📊 Leaderboard", "next_matches": "📅 Upcoming 5 Matches",
        "no_matches": "🏆 World Cup Ended!", "save_btn": "Save Predictions",
        "time_left": "⏳ Betting deadline:", "closed": "🔒 Betting Closed",
        "logout": "Logout", "login_btn": "Login with Google",
        "mode_select": "Game Mode:", "special_bets": "⭐ Special Bets",
        "champion": "Champion", "subchampion": "Runner-up", "third": "3rd Place",
        "surprise": "Surprise Team", "disappointment": "Disappointment Team",
        "match_results": "🏟️ Match Results", "best_3rd": "🥉 Best Third Places",
        "reset_all": "♻️ Reset Everything", "reset_real": "🏟️ Load Real Data", "clear_sim": "🧹 Clear Sim Only"
    }
}

# --- INICIALIZACIÓN DE SERVICIOS ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()
zona_sofia = ZoneInfo("Europe/Sofia")

if "connected" not in st.session_state: st.session_state.connected = False
if "game_mode" not in st.session_state: st.session_state.game_mode = "Simple"

# Sidebar Global
lang = st.sidebar.selectbox("🌐 Idioma", ["Español", "English"])
t = texts[lang]

# --- FUNCIONES DE RENDERIZADO ---
def render_flag(url):
    # Estandarización de tamaño de banderas para tablas y listas
    return f'<img src="{url}" width="30" height="20" style="border-radius:2px; object-fit: cover; border: 1px solid #eee;">'

def render_equipo_ui(n_es, n_en, url, align="left"):
    nombre = n_es if lang == "Español" else (n_en or n_es)
    flex = "row" if align == "left" else "row-reverse"
    return f'<div style="display: flex; align-items: center; flex-direction: {flex}; gap: 10px;">{render_flag(url)}<span style="font-weight: bold;">{nombre}</span></div>'

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def get_airtable_data():
    headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
    base_id = st.secrets['airtable']['base_id']
    
    # Equipos
    res_eq = requests.get(f"https://api.airtable.com/v0/{base_id}/Equipos", headers=headers).json()
    equipos_dict = {r['id']: r['fields'] for r in res_eq.get('records', [])}
    
    # Partidos con orden FIFA
    res_pa = requests.get(f"https://api.airtable.com/v0/{base_id}/Partidos", headers=headers, 
                          params={"sort[0][field]": "ID Partido", "sort[0][direction]": "asc"}).json()
    
    partidos = []
    for r in res_pa.get('records', []):
        f = r['fields']
        partidos.append({
            "ID": f.get("ID Partido"),
            "Etapa": f.get("Etapa"),
            "Jornada": f.get("Jornada"),
            "Jornada_EN": f.get("Jornada EN"),
            "Grupo": f.get("Grupo", ["-"])[0] if isinstance(f.get("Grupo"), list) else f.get("Grupo", "-"),
            "Local_ES": f.get("Nombre (from Equipo Local)")[0] if f.get("Nombre (from Equipo Local)") else "TBD",
            "Local_EN": f.get("Nombre EN (from Equipo Local)")[0] if f.get("Nombre EN (from Equipo Local)") else "TBD",
            "Visitante_ES": f.get("Nombre (from Equipo Visitante)")[0] if f.get("Nombre (from Equipo Visitante)") else "TBD",
            "Visitante_EN": f.get("Nombre EN (from Equipo Visitante)")[0] if f.get("Nombre EN (from Equipo Visitante)") else "TBD",
            "Band_L": f.get("Bandera L")[0]['url'] if f.get("Bandera L") else "",
            "Band_V": f.get("Bandera V")[0]['url'] if f.get("Bandera V") else "",
            "Real_L": f.get("Goles Local"),
            "Real_V": f.get("Goles Visitante"),
            "Fecha_Hora": f.get("Fecha y Hora"),
            "Rank_L": f.get("Ranking FIFA (from Equipo Local)")[0] if f.get("Ranking FIFA (from Equipo Local)") else 100,
            "Rank_V": f.get("Ranking FIFA (from Equipo Visitante)")[0] if f.get("Ranking FIFA (from Equipo Visitante)") else 100,
            "FP_L": f.get("Fair Play L", 0),
            "FP_V": f.get("Fair Play V", 0)
        })
    return partidos, equipos_dict

# --- LÓGICA DE APLICACIÓN ---
if st.session_state.connected:
    partidos_data, equipos_data = get_airtable_data()
    
    # Selector de Modo
    st.sidebar.divider()
    modo_label = st.sidebar.radio(t["mode_select"], ["Prode Simple", "Magic Mister"])
    st.session_state.game_mode = modo_label
    
    menu = st.sidebar.radio("Menú", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    if st.sidebar.button(t["logout"]):
        st.session_state.connected = False
        st.rerun()

    st.title(t["title"])

    # --- A2: INICIO ---
    if menu == t["nav_home"]:
        c1, c2 = st.columns([1.5, 1])
        with c1:
            st.subheader(t["ranking_title"])
            st.info("Cargando posiciones de usuarios desde Supabase...")
            # Aquí iría la lógica de puntos (Ganador 2pts, Exacto +2, etc.)
            
        with c2:
            st.subheader(t["next_matches"])
            ahora = datetime.now(zona_sofia)
            futuros = []
            for p in partidos_data:
                if p['Fecha_Hora']:
                    dt = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                    if dt > ahora: futuros.append((dt, p))
            
            futuros.sort(key=lambda x: x[0])
            for dt, p in futuros[:5]:
                with st.container(border=True):
                    st.caption(dt.strftime("%d/%m - %H:%M hs"))
                    st.markdown(render_equipo_ui(p['Local_ES'], p['Local_EN'], p['Band_L']), unsafe_allow_html=True)
                    st.markdown(render_equipo_ui(p['Visitante_ES'], p['Visitante_EN'], p['Band_V'], align="right"), unsafe_allow_html=True)

    # --- A3: JUGAR PRODE ---
    elif menu == t["nav_play"]:
        if st.session_state.game_mode == "Magic Mister":
            st.warning("Próximamente: Super Manager - Arma tu equipo de 11 jugadores.")
        else:
            jornada_col = "Jornada" if lang == "Español" else "Jornada_EN"
            jornadas = sorted(list(set([p[jornada_col] for p in partidos_data if p[jornada_col]])))
            j_sel = st.selectbox("Selecciona Jornada / Apuesta:", jornadas)
            
            partidos_f = [p for p in partidos_data if p[jornada_col] == j_sel]
            ahora = datetime.now(zona_sofia)
            
            with st.form("form_prode"):
                # Ordenar por Grupo como en el código original
                for p in sorted(partidos_f, key=lambda x: x['Grupo']):
                    with st.container(border=True):
                        # Lógica de Bloqueo (Timer)
                        dt_p = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                        limite = dt_p - timedelta(hours=6 if "Jornada" in p['Jornada'] else 5)
                        bloqueado = ahora > limite
                        
                        st.caption(f"Grupo {p['Grupo']} | {t['time_left']} {limite.strftime('%d/%m %H:%M')}")
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                        with c1: st.markdown(render_equipo_ui(p['Local_ES'], p['Local_EN'], p['Band_L']), unsafe_allow_html=True)
                        gl = c2.number_input("L", 0, 15, key=f"l_{p['ID']}", disabled=bloqueado, label_visibility="collapsed")
                        c3.markdown("<h3 style='text-align:center; margin:0;'>:</h3>", unsafe_allow_html=True)
                        gv = c4.number_input("V", 0, 15, key=f"v_{p['ID']}", disabled=bloqueado, label_visibility="collapsed")
                        with c5: st.markdown(render_equipo_ui(p['Visitante_ES'], p['Visitante_EN'], p['Band_V'], align="right"), unsafe_allow_html=True)
                        if bloqueado: st.error(t["closed"])

                # A3.b.7 Apuestas Especiales
                st.divider()
                st.subheader(t["special_bets"])
                equipos_nombres = sorted([e['Nombre'] for e in equipos_data.values()])
                col1, col2, col3 = st.columns(3)
                col1.selectbox(t["champion"], equipos_nombres, key="esp_campeon")
                col

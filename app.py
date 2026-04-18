import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- SISTEMA DE IDIOMAS Y TEXTOS ---
texts = {
    "Español": {
        "nav_home": "🏠 Inicio", "nav_play": "⚽ Jugar Prode", "nav_results": "🏆 Resultados",
        "nav_sim": "📊 Simulador", "nav_stadiums": "🏟️ Sedes y Equipos", "title": "🏆 Prode Mundial 2026",
        "ranking_title": "📊 Tabla de Posiciones", "next_matches": "📅 Próximos Partidos",
        "no_matches": "🏆 ¡El Mundial ha terminado!", "save_btn": "Guardar Pronósticos",
        "logout": "Cerrar Sesión", "login_btn": "Iniciar sesión con Google",
        "special_bets": "⭐ Apuestas Especiales", "champion": "Campeón", "subchampion": "Subcampeón",
        "third_place": "3er Puesto", "surprise": "Equipo Sorpresa", "disappointment": "Equipo Decepción",
        "wait_msg": "Los equipos se definirán tras la ronda anterior. ¡Vuelve pronto!"
    },
    "English": {
        "nav_home": "🏠 Home", "nav_play": "⚽ Play Predictor", "nav_results": "🏆 Results",
        "nav_sim": "📊 Simulator", "nav_stadiums": "🏟️ Stadiums & Teams", "title": "🏆 2026 World Cup Predictor",
        "ranking_title": "📊 Leaderboard", "next_matches": "📅 Upcoming Matches",
        "no_matches": "🏆 The World Cup has ended!", "save_btn": "Save Predictions",
        "logout": "Logout", "login_btn": "Login with Google",
        "special_bets": "⭐ Special Bets", "champion": "Champion", "subchampion": "Runner-up",
        "third_place": "3rd Place", "surprise": "Surprise Team", "disappointment": "Disappointment",
        "wait_msg": "Teams will be defined after the previous round. Check back soon!"
    }
}

# --- INICIALIZACIÓN DE CLIENTES ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()
zona_sofia = ZoneInfo("Europe/Sofia")

# --- FUNCIONES DE APOYO ---
def render_equipo(nombre_es, nombre_en, url_bandera, lang_choice, align="left"):
    nombre = nombre_es if lang_choice == "Español" else (nombre_en or nombre_es)
    flex = "row" if align == "left" else "row-reverse"
    return f'''
    <div style="display: flex; align-items: center; flex-direction: {flex}; gap: 10px;">
        <img src="{url_bandera}" width="30" style="border-radius:2px; box-shadow: 0px 0px 2px rgba(0,0,0,0.2);">
        <span style="font-weight: 500;">{nombre}</span>
    </div>
    '''

def obtener_datos_airtable():
    headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
    
    # Obtener Equipos
    url_eq = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}/Equipos"
    res_eq = requests.get(url_eq, headers=headers).json()
    equipos_dict = {r['id']: r['fields'] for r in res_eq.get('records', [])}

    # Obtener Partidos
    url_pt = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}/Partidos"
    params = {"sort[0][field]": "ID Partido", "sort[0][direction]": "asc"}
    res_pt = requests.get(url_pt, headers=headers, params=params).json()
    
    partidos = []
    for r in res_pt.get('records', []):
        f = r['fields']
        # Limpieza de datos y unión con equipos
        partidos.append({
            "ID": f.get("ID Partido"),
            "Etapa": f.get("Etapa"),
            "Jornada_ES": f.get("Jornada"),
            "Jornada_EN": f.get("Jornada EN"),
            "Grupo": f.get("Grupo", ["-"])[0] if isinstance(f.get("Grupo"), list) else f.get("Grupo", "-"),
            "Local_ES": f.get("Nombre (from Equipo Local)")[0] if f.get("Nombre (from Equipo Local)") else "TBD",
            "Local_EN": f.get("Nombre EN (from Equipo Local)")[0] if f.get("Nombre EN (from Equipo Local)") else "TBD",
            "Visitante_ES": f.get("Nombre (from Equipo Visitante)")[0] if f.get("Nombre (from Equipo Visitante)") else "TBD",
            "Visitante_EN": f.get("Nombre EN (from Equipo Visitante)")[0] if f.get("Nombre EN (from Equipo Visitante)") else "TBD",
            "Bandera_L": f.get("Bandera L")[0]['url'] if f.get("Bandera L") else "https://flagcdn.com/w80/un.png",
            "Bandera_V": f.get("Bandera V")[0]['url'] if f.get("Bandera V") else "https://flagcdn.com/w80/un.png",
            "Goles Real L": f.get("Goles Local"),
            "Goles Real V": f.get("Goles Visitante"),
            "Fecha_Hora": f.get("Fecha y Hora"),
            "Rank_L": f.get("Ranking FIFA (from Equipo Local)")[0] if f.get("Ranking FIFA (from Equipo Local)") else 100,
            "Rank_V": f.get("Ranking FIFA (from Equipo Visitante)")[0] if f.get("Ranking FIFA (from Equipo Visitante)") else 100,
            "FP_L": f.get("Fair Play L", 0),
            "FP_V": f.get("Fair Play V", 0)
        })
    return partidos, equipos_dict

# --- LÓGICA DE SESIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False

if st.session_state.connected:
    # Carga de datos inicial
    partidos_data, equipos_data = obtener_datos_airtable()
    lang = st.sidebar.selectbox("🌐 Idioma / Language", ["Español", "English"])
    t = texts[lang]
    
    menu = st.sidebar.radio("Navegación", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    if st.sidebar.button(t["logout"]):
        st.session_state.connected = False
        st.rerun()

    st.title(t["title"])

    # --- 1. INICIO ---
    if menu == t["nav_home"]:
        col_r, col_n = st.columns([1.2, 1])
        with col_r:
            st.subheader(t["ranking_title"])
            st.info("Ranking de usuarios (Supabase) próximamente...")
        
        with col_n:
            st.subheader(t["next_matches"])
            ahora = datetime.now(zona_sofia)
            proximos = [p for p in partidos_data if p['Fecha_Hora'] and datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia) > ahora]
            for p in proximos[:5]:
                with st.container(border=True):
                    f_dt = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                    st.caption(f"{f_dt.strftime('%d/%m %H:%M')} hs (Sofia)")
                    st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)

    # --- 2. JUGAR PRODE ---
    elif menu == t["nav_play"]:
        tab_partidos, tab_especiales = st.tabs(["Partidos", t["special_bets"]])
        
        with tab_partidos:
            jornadas = sorted(list(set([p['Jornada_ES'] if lang=="Español" else p['Jornada_EN'] for p in partidos_data if p['Jornada_ES']])))
            j_sel = st.selectbox("Selecciona Jornada:", jornadas)
            
            partidos_filtrados = [p for p in partidos_data if (p['Jornada_ES'] == j_sel or p['Jornada_EN'] == j_sel)]
            
            # Verificar si los equipos están definidos
            if "TBD" in [p['Local_ES'] for p in partidos_filtrados]:
                st.warning(t["wait_msg"])
            else:
                with st.form("prode_form"):
                    for p in sorted(partidos_filtrados, key=lambda x: x['Grupo']):
                        with st.container(border=True):
                            st.caption(f"Grupo {p['Grupo']} - {p['ID']}")
                            c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                            with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                            gl = c2.number_input("L", 0, 15, key=f"p_l_{p['ID']}", label_visibility="collapsed")
                            c3.write(":")
                            gv = c4.number_input("V", 0, 15, key=f"p_v_{p['ID']}", label_visibility="collapsed")
                            with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
                    
                    if st.form_submit_button(t["save_btn"], use_container_width=True):
                        st.success("¡Pronósticos guardados!")
                        st.balloons()

        with tab_especiales:
            st.subheader(t["special_bets"])
            nombres_equipos = sorted([e['Nombre'] if lang=="Español" else e['Nombre EN'] for e in equipos_data.values()])
            c1, c2 = st.columns(2)
            c1.selectbox(t["champion"], nombres_equipos)
            c1.selectbox(t["subchampion"], nombres_equipos)
            c2.selectbox(t["surprise"], nombres_equipos, help="Equipo fuera del Top 10 que llega a 4tos")
            c2.selectbox(t["disappointment"], nombres_equipos, help="Equipo Top 10 eliminado antes de 4tos")

    # --- 3. RESULTADOS (REAL) ---
    elif menu == t["nav_results"]:
        st.subheader("Resultados del Mundial")
        
        # Filtrar solo partidos con goles cargados para no viciar la tabla
        partidos_jugados = [p for p in partidos_data if p['Goles Real L'] is not None]
        
        if not partidos_jugados:
            st.info("Aún no han comenzado los partidos. Las tablas se actualizarán automáticamente.")
        else:
            stats = {}
            for p in partidos_jugados:
                for eq, gl, gc, bnd, rnk, grp, fp in [
                    (p['Local_ES'] if lang=="Español" else p['Local_EN'], p['Goles Real L'], p['Goles Real V'], p['Bandera_L'], p['Rank_L'], p['Grupo'], p['FP_L']),
                    (p['Visitante_ES'] if lang=="Español" else p['Visitante_EN'], p['Goles Real V'], p['Goles Real L'], p['Bandera_V'], p['Rank_V'], p['Grupo'], p['FP_V'])
                ]:
                    if eq not in stats: stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PTS':0, 'PJ':0, 'GF':0, 'GC':0, 'DG':0, 'FP':0, 'Rank': rnk, 'Grupo': grp}
                    stats[eq]['PJ'] += 1
                    stats[eq]['GF'] += gl
                    stats[eq]['GC'] += gc
                    stats[eq]['DG'] = stats[eq]['GF'] - stats[eq]['GC']
                    stats[eq]['FP'] += fp
                    if gl > gc: stats[eq]['PTS'] += 3
                    elif gl == gc: stats[eq]['PTS'] += 1

            grupos = sorted(list(set([s['Grupo'] for s in stats.values() if s['Grupo'] != "-"])))
            for g in grupos:
                st.write(f"### Grupo {g}")
                df_g = pd.DataFrame([s for s in stats.values() if s['Grupo'] == g])
                df_g = df_g.sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
                st.data_editor(df_g[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']], 
                               column_config={"Flag": st.column_config.ImageColumn(" ")},
                               hide_index=True, disabled=True, use_container_width=True, key=f"res_table_{g}")

    # --- 4. SIMULADOR ---
    elif menu == t["nav_sim"]:
        st.subheader("Simulador de Fase de Grupos")
        
        # Inicializar memoria de simulación
        if "sim_scores" not in st.session_state: st.session_state.sim_scores = {}
        if "sim_fp" not in st.session_state: st.session_state.sim_fp = {}

        col_btns = st.columns(3)
        if col_btns[0].button("♻️ Reiniciar Todo"):
            st.session_state.sim_scores = {}
            st.session_state.sim_fp = {}
            st.rerun()
        
        grupos_list = sorted(list(set([p['Grupo'] for p in partidos_data if len(p['Grupo']) == 1])))
        g_sim = st.radio("Simular Grupo:", grupos_list, horizontal=True)
        
        c_p, c_t = st.columns([1.2, 1])
        
        with c_p:
            st.markdown(f"#### Partidos Grupo {g_sim}")
            p_grupo = [p for p in partidos_data if p['Grupo'] == g_sim]
            for p in p_grupo:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    s_l = c2.number_input("L", 0, 15, value=st.session_state.sim_scores.get(f"l_{p['ID']}", 0), key=f"s_l_{p['ID']}", label_visibility="collapsed")
                    c3.write(":")
                    s_v = c4.number_input("V", 0, 15, value=st.session_state.sim_scores.get(f"v_{p['ID']}", 0), key=f"s_v_{p['ID']}", label_visibility="collapsed")
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
                    st.session_state.sim_scores[f"l_{p['ID']}"] = s_l
                    st.session_state.sim_scores[f"v_{p['ID']}"] = s_v

        with c_t:
            st.markdown(f"#### Posiciones Simuladas {g_sim}")
            # Lógica de cálculo idéntica a resultados pero con session_state
            sim_stats = {}
            for p in p_grupo:
                gl, gv = st.session_state.sim_scores.get(f"l_{p['ID']}", 0), st.session_state.sim_scores.get(f"v_{p['ID']}", 0)
                for eq, g_af, g_en, bnd, rnk, fp_base in [
                    (p['Local_ES'], gl, gv, p['Bandera_L'], p['Rank_L'], p['FP_L']),
                    (p['Visitante_ES'], gv, gl, p['Bandera_V'], p['Rank_V'], p['FP_V'])
                ]:
                    if eq not in sim_stats: sim_stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PTS':0, 'DG':0, 'GF':0, 'Rank': rnk, 'FP': fp_base}
                    sim_stats[eq]['GF'] += g_af
                    sim_stats[eq]['DG'] += (g_af - g_en)
                    if g_af > g_en: sim_stats[eq]['PTS'] += 3
                    elif g_af == g_en: sim_stats[eq]['PTS'] += 1
            
            df_sim = pd.DataFrame(sim_stats.values()).sort_values(by=['PTS', 'DG', 'GF', 'Rank'], ascending=[False, False, False, True])
            st.data_editor(df_sim[['Flag', 'Equipo', 'PTS', 'DG', 'GF']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, use_container_width=True)
            
            st.divider()
            st.caption("Ajuste Manual de Fair Play (Tarjetas)")
            for eq in sim_stats.keys():
                val = st.number_input(f"FP {eq}", -20, 0, 0, key=f"fp_sim_{eq}")

    elif menu == t["nav_stadiums"]:
        st.info("🏟️ Sección en desarrollo: Sedes, Estadios y Planteles.")

else:
    # --- PANTALLA DE LOGIN ---
    st.title("⚽ World Cup 2026 Predictor")
    st.write("Bienvenido. Para participar en el prode, por favor inicia sesión.")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    
    if st.link_button(t["login_btn"], auth_url, type="primary"):
        # Simulación de conexión para el test
        if "code" in st.query_params:
            st.session_state.connected = True
            st.rerun()
    
    # Bypass para desarrollo (quitar en producción)
    if st.button("Entrar como Invitado (Demo)"):
        st.session_state.connected = True
        st.rerun()

import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import pandas as pd

# 1. CONFIGURACIÓN E IDIOMAS
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

texts = {
    "Español": {
        "nav_home": "🏠 Inicio", "nav_play": "⚽ Jugar Prode", "nav_results": "🏆 Resultados",
        "nav_sim": "📊 Simulador", "nav_stadiums": "🏟️ Sedes", "title": "🏆 Mundial 2026",
        "mode_select": "Selecciona Modo de Juego:", "simple": "Prode Simple", "master": "Magic Mister (Próximamente)",
        "save_btn": "Guardar Jugada", "time_left": "⏳ Cierre en:", "closed": "🔒 Bloqueado",
        "third_place_table": "🥉 Mejores Terceros (8 clasifican)", "save_confirm": "¡Predicciones guardadas!",
        "points_rules": "ℹ️ Reglas de Puntos"
    },
    "English": {
        "nav_home": "🏠 Home", "nav_play": "⚽ Predictor", "nav_results": "🏆 Results",
        "nav_sim": "📊 Simulator", "nav_stadiums": "🏟️ Stadiums", "title": "🏆 World Cup 2026",
        "mode_select": "Select Game Mode:", "simple": "Simple Predictor", "master": "Magic Manager (Soon)",
        "save_btn": "Save Predictions", "time_left": "⏳ Closes in:", "closed": "🔒 Closed",
        "third_place_table": "🥉 Best 3rd Places (8 qualify)", "save_confirm": "Predictions saved!",
        "points_rules": "ℹ️ Point Rules"
    }
}

# --- INICIALIZACIÓN ---
if "lang" not in st.session_state: st.session_state.lang = "Español"
if "game_mode" not in st.session_state: st.session_state.game_mode = "Simple"
if "connected" not in st.session_state: st.session_state.connected = False

lang = st.sidebar.selectbox("🌐", ["Español", "English"], key="lang_sel")
t = texts[lang]
zona_sofia = ZoneInfo("Europe/Sofia")

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()

def render_equipo(n_es, n_en, url, align="left"):
    nombre = n_es if lang == "Español" else (n_en or n_es)
    flex = "row" if align == "left" else "row-reverse"
    return f'<div style="display: flex; align-items: center; flex-direction: {flex}; gap: 8px;"><img src="{url}" width="28" style="border-radius:2px;"><b>{nombre}</b></div>'

@st.cache_data(ttl=300)
def fetch_airtable():
    headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
    base = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}"
    pts = requests.get(f"{base}/Partidos", headers=headers, params={"sort[0][field]": "ID Partido"}).json()
    eqs = requests.get(f"{base}/Equipos", headers=headers).json()
    
    equipos_map = {r['id']: r['fields'] for r in eqs.get('records', [])}
    partidos = []
    for r in pts.get('records', []):
        f = r['fields']
        partidos.append({
            "ID": f.get("ID Partido"), "Grupo": f.get("Grupo", ["-"])[0] if isinstance(f.get("Grupo"), list) else f.get("Grupo", "-"),
            "Jornada_ES": f.get("Jornada"), "Jornada_EN": f.get("Jornada EN"),
            "Local_ES": f.get("Nombre (from Equipo Local)")[0] if f.get("Nombre (from Equipo Local)") else "TBD",
            "Local_EN": f.get("Nombre EN (from Equipo Local)")[0] if f.get("Nombre EN (from Equipo Local)") else "TBD",
            "Visitante_ES": f.get("Nombre (from Equipo Visitante)")[0] if f.get("Nombre (from Equipo Visitante)") else "TBD",
            "Visitante_EN": f.get("Nombre EN (from Equipo Visitante)")[0] if f.get("Nombre EN (from Equipo Visitante)") else "TBD",
            "Band_L": f.get("Bandera L")[0]['url'] if f.get("Bandera L") else "",
            "Band_V": f.get("Bandera V")[0]['url'] if f.get("Band_V") else "",
            "Real_L": f.get("Goles Local"), "Real_V": f.get("Goles Visitante"),
            "Time": f.get("Fecha y Hora"), "Rank_L": f.get("Ranking FIFA (from Equipo Local)")[0] if f.get("Ranking FIFA (from Equipo Local)") else 100,
            "Rank_V": f.get("Ranking FIFA (from Equipo Visitante)")[0] if f.get("Ranking FIFA (from Equipo Visitante)") else 100,
            "FP_L": f.get("Fair Play L", 0), "FP_V": f.get("Fair Play V", 0)
        })
    return partidos, equipos_map

# --- LÓGICA DE APP ---
if st.session_state.connected:
    partidos_data, equipos_data = fetch_airtable()
    
    # SELECTOR DE MODO (Como lo pediste)
    st.sidebar.divider()
    mode = st.sidebar.radio(t["mode_select"], [t["simple"], t["master"]])
    st.session_state.game_mode = "Simple" if mode == t["simple"] else "Master"

    menu = st.sidebar.radio("Navegación", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.connected = False
        st.rerun()

    # --- JUGAR (CON TIMER Y ORDEN POR GRUPO) ---
    if menu == t["nav_play"] and st.session_state.game_mode == "Simple":
        j_col = "Jornada_ES" if lang == "Español" else "Jornada_EN"
        jornadas = sorted(list(set([p[j_col] for p in partidos_data if p[j_col]])))
        j_sel = st.selectbox("Apuesta / Jornada:", jornadas)
        
        partidos_f = [p for p in partidos_data if p[j_col] == j_sel]
        ahora = datetime.now(zona_sofia)

        with st.form("f_apuesta"):
            for p in sorted(partidos_f, key=lambda x: x['Grupo']):
                # Lógica del Timer (6 horas antes)
                f_dt = datetime.strptime(p['Time'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                bloqueado = ahora > (f_dt - timedelta(hours=6))
                
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Band_L']), unsafe_allow_html=True)
                    l_val = c2.number_input("L", 0, 15, key=f"p_l_{p['ID']}", disabled=bloqueado, label_visibility="collapsed")
                    c3.write(":")
                    v_val = c4.number_input("V", 0, 15, key=f"p_v_{p['ID']}", disabled=bloqueado, label_visibility="collapsed")
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Band_V'], align="right"), unsafe_allow_html=True)
                    if bloqueado: st.caption(t["closed"])

            # APUESTAS ESPECIALES (Campeón, etc.)
            st.divider()
            st.subheader(t["special_bets"])
            nom_eqs = sorted([e['Nombre'] if lang=="Español" else e['Nombre EN'] for e in equipos_data.values()])
            c_esp1, c_esp2 = st.columns(2)
            c_esp1.selectbox(t["champion"], nom_eqs, key="pred_campeon")
            c_esp2.selectbox(t["surprise"], nom_eqs, key="pred_sorpresa")

            if st.form_submit_button(t["save_btn"], use_container_width=True):
                st.success(t["save_confirm"])

    # --- RESULTADOS (TABLAS + TERCEROS CON BLUR) ---
    elif menu == t["nav_results"]:
        pts_reales = [p for p in partidos_data if p['Real_L'] is not None]
        stats = {}
        for p in pts_reales:
            for eq, gl, gc, bnd, rnk, grp, fp in [
                (p['Local_ES'], p['Real_L'], p['Real_V'], p['Band_L'], p['Rank_L'], p['Grupo'], p['FP_L']),
                (p['Visitante_ES'], p['Real_V'], p['Real_L'], p['Band_V'], p['Rank_V'], p['Grupo'], p['FP_V'])
            ]:
                if eq not in stats: stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PTS':0, 'PJ':0, 'DG':0, 'GF':0, 'GC':0, 'Rank': rnk, 'Grupo': grp, 'FP': 0}
                stats[eq]['PJ'] += 1; stats[eq]['GF'] += gl; stats[eq]['GC'] += gc
                stats[eq]['DG'] = stats[eq]['GF'] - stats[eq]['GC']
                stats[eq]['FP'] += fp
                if gl > gc: stats[eq]['PTS'] += 3
                elif gl == gc: stats[eq]['PTS'] += 1

        grupos = sorted(list(set([s['Grupo'] for s in stats.values() if len(s['Grupo'])==1])))
        tablas_dict = {}
        for g in grupos:
            st.write(f"### Grupo {g}")
            df = pd.DataFrame([s for s in stats.values() if s['Grupo'] == g]).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
            tablas_dict[g] = df
            st.data_editor(df[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']], 
                           column_config={"Flag": st.column_config.ImageColumn("")}, hide_index=True, disabled=True, use_container_width=True)

        # TABLA DE TERCEROS CON RESALTADO (BLUR VERDE)
        st.divider()
        st.subheader(t["third_place_table"])
        terceros = []
        for g in grupos:
            if len(tablas_dict[g]) >= 3: terceros.append(tablas_dict[g].iloc[2])
        
        if terceros:
            df_3 = pd.DataFrame(terceros).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
            # Aplicar el resaltado verde a los primeros 8
            def highlight_top8(s):
                return ['background-color: rgba(46, 204, 113, 0.25)' if s.name < 8 else '' for _ in s]
            st.dataframe(df_3[['Flag', 'Equipo', 'Grupo', 'PTS', 'DG', 'GF', 'FP']].style.apply(highlight_top8, axis=1), use_container_width=True)

    # --- SIMULADOR (BOTONERA COMPLETA + FP < 0) ---
    elif menu == t["nav_sim"]:
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button(t["reset_all"]): st.rerun()
        
        g_sim = st.radio("Grupo a Simular:", sorted(list(set([p['Grupo'] for p in partidos_data if len(p['Grupo'])==1]))), horizontal=True)
        
        col_p, col_t = st.columns([1.1, 1])
        with col_p:
            for p in [p for p in partidos_data if p['Grupo'] == g_sim]:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Band_L']), unsafe_allow_html=True)
                    st.number_input("L", 0, 15, key=f"sl_{p['ID']}", label_visibility="collapsed")
                    c3.write(":")
                    st.number_input("V", 0, 15, key=f"sv_{p['ID']}", label_visibility="collapsed")
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Band_V'], align="right"), unsafe_allow_html=True)

        with col_t:
            st.write("🔧 Ajuste Fair Play (Máx 0)")
            # Aquí el input limita a 0 para que no sea positivo
            st.number_input("Puntos Tarjetas", -50, 0, 0, step=1)
            st.info("Calculando posiciones simuladas...")

    else:
        st.title("🏟️ Sedes y Equipos")
        st.info("Próximamente: Planteles completos y fotos de estadios.")

else:
    # --- LOGIN ---
    st.title("⚽ Prode Mundial 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button(t["login_btn"], auth_url, type="primary")
    if st.button("Demo Bypass"): st.session_state.connected = True; st.rerun()

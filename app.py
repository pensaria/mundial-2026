import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import pandas as pd
from itertools import groupby

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
                g_raw = f.get("Grupo")
                grupo_real = str(g_raw[0]).strip() if isinstance(g_raw, list) and g_raw else (str(g_raw).strip() if g_raw else "Definir")
                r_l = f.get("Ranking FIFA (from Equipo Local)")
                r_v = f.get("Ranking FIFA (from Equipo Visitante)")
                rank_l = r_l[0] if isinstance(r_l, list) else (r_l if r_l else 100)
                rank_v = r_v[0] if isinstance(r_v, list) else (r_v if r_v else 100)
                bandera_l = f.get("Bandera L")[0].get("url") if f.get("Bandera L") else ""
                bandera_v = f.get("Bandera V")[0].get("url") if f.get("Bandera V") else ""
                partidos.append({
                    "ID": f.get("ID Partido"),
                    "Grupo": grupo_real,
                    "Local_ES": f.get("Nombre (from Equipo Local)")[0] if isinstance(f.get("Nombre (from Equipo Local)"), list) else f.get("Nombre (from Equipo Local)"),
                    "Local_EN": f.get("Nombre EN (from Equipo Local)")[0] if f.get("Nombre EN (from Equipo Local)") else f.get("Nombre (from Equipo Local)"),
                    "Visitante_ES": f.get("Nombre (from Equipo Visitante)")[0] if isinstance(f.get("Nombre (from Equipo Visitante)"), list) else f.get("Nombre (from Equipo Visitante)"),
                    "Visitante_EN": f.get("Nombre EN (from Equipo Visitante)")[0] if f.get("Nombre EN (from Equipo Visitante)") else f.get("Nombre (from Equipo Visitante)"),
                    "Bandera_L": bandera_l, "Bandera_V": bandera_v,
                    "Rank_L": rank_l, "Rank_V": rank_v,
                    "FP_L": f.get("Fair Play L", 0), "FP_V": f.get("Fair Play V", 0),
                    "Goles Real L": f.get("Goles Local"), "Goles Real V": f.get("Goles Visitante"),
                    "Fecha_Hora": f.get("Fecha y Hora"), "Jornada": f.get("Jornada")
                })
            return partidos
        return []
    except Exception as e:
        st.error(f"Error Airtable: {e}")
        return []

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

# --- LÓGICA DE SESIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True
if "menu_sel_radio" not in st.session_state: st.session_state.menu_sel_radio = "🏠 Inicio"

if st.session_state.connected:
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    st.sidebar.success(t["online"])
    
    opciones_menu = [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]]
    menu = st.sidebar.radio(t["nav_home"], opciones_menu, key="menu_sel_radio")
    
    if st.sidebar.button(t["logout"]):
        st.session_state.connected = False
        st.rerun()

    st.title(t["title"])

    # --- 1. INICIO ---
    if menu == t["nav_home"]:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(t["ranking_title"])
            rank = obtener_ranking_global()
            if rank: st.table(rank)
            else: st.info("No points registered yet.")
        with col2:
            st.subheader(t["next_matches"])
            partidos = obtener_partidos_airtable()
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora = datetime.now(zona_sofia)
            proximos = []
            for p in partidos:
                if p['Fecha_Hora']:
                    f_sofia = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                    if f_sofia > ahora: proximos.append((f_sofia, p))
            proximos.sort(key=lambda x: x[0])
            if proximos:
                for f, p in proximos[:5]:
                    with st.container(border=True):
                        st.caption(f.strftime('%d/%m - %H:%M hs'))
                        st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        st.markdown("<div style='text-align: center; margin: -5px 0; color: #888; font-size: 12px;'>VS</div>", unsafe_allow_html=True)
                        st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang), unsafe_allow_html=True)
            else: st.success(t["no_matches"])

    # --- 2. JUGAR ---
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
                st.success("Saved!")
                st.balloons()

    # --- 3. RESULTADOS ---
    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        partidos = obtener_partidos_airtable()
        if not partidos: st.info("No hay datos.")
        else:
            stats_global = {}
            for p in partidos:
                if p['Goles Real L'] is not None and p['Goles Real V'] is not None and p['Grupo'] != "Definir":
                    g = p['Grupo']
                    l = p['Local_ES'] if lang == "Español" else p['Local_EN']
                    v = p['Visitante_ES'] if lang == "Español" else p['Visitante_EN']
                    gl, gv = int(p['Goles Real L']), int(p['Goles Real V'])
                    for eq, rnk, fp in [(l, p['Rank_L'], p['FP_L']), (v, p['Rank_V'], p['FP_V'])]:
                        if eq not in stats_global:
                            stats_global[eq] = {'Equipo': eq, 'PJ':0, 'PTS':0, 'DG':0, 'GF':0, 'FP': 0, 'Rank': rnk, 'Grupo': g}
                        stats_global[eq]['FP'] += fp
                    stats_global[l]['PJ'] += 1; stats_global[v]['PJ'] += 1
                    stats_global[l]['GF'] += gl; stats_global[v]['GF'] += gv
                    if gl > gv: stats_global[l]['PTS'] += 3
                    elif gl < gv: stats_global[v]['PTS'] += 3
                    else: stats_global[l]['PTS'] += 1; stats_global[v]['PTS'] += 1
                    stats_global[l]['DG'] += (gl - gv)
                    stats_global[v]['DG'] += (gv - gl)
            grupos_ids = sorted(list(set([s['Grupo'] for s in stats_global.values()])))
            tablas_finales = {}
            for g_id in grupos_ids:
                st.write(f"### GROUP {g_id}" if lang == "English" else f"### GRUPO {g_id}")
                eq_grupo = [s for s in stats_global.values() if s['Grupo'] == g_id]
                eq_grupo.sort(key=lambda x: (x['PTS'], x['DG'], x['GF'], x['FP'], -x['Rank']), reverse=True)
                tablas_finales[g_id] = eq_grupo
                df_g = pd.DataFrame(eq_grupo)[['Equipo', 'PJ', 'PTS', 'DG', 'GF', 'FP']]
                st.dataframe(df_g, use_container_width=True, hide_index=True)
            st.divider()
            st.subheader("🥉 Best Third Places" if lang == "English" else "🥉 Mejores Terceros")
            terceros_lista = [tablas_finales[g][2] for g in grupos_ids if len(tablas_finales[g]) >= 3]
            if terceros_lista:
                df_3 = pd.DataFrame(terceros_lista).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
                def highlight_top8(s):
                    return ['background-color: rgba(46, 204, 113, 0.3)' if s.name < 8 else '' for _ in s]
                st.dataframe(df_3[['Equipo', 'Grupo', 'PTS', 'DG', 'GF', 'FP']].style.apply(highlight_top8, axis=1), use_container_width=True, hide_index=True)
            st.divider()
            st.subheader("🏆 Knockout Stage" if lang == "English" else "🏆 Fase de Eliminatorias")
            texto_a_definir = "To be defined..." if lang == "English" else "Por definirse..."
            c1, c2, c3 = st.columns(3); c1.info(f"**Round of 32 / 16vos** \n\n {texto_a_definir}"); c2.info(f"**Round of 16 / 8vos** \n\n {texto_a_definir}"); c3.info(f"**Quarter-finals / 4tos** \n\n {texto_a_definir}")
            c4, c5, c6 = st.columns(3); c4.warning(f"**Semi-finals / Semifinales** \n\n {texto_a_definir}"); c5.success(f"**Third Place / 3er Puesto** \n\n {texto_a_definir}"); c6.error(f"**GRAND FINAL / GRAN FINAL** \n\n {texto_a_definir}")

    # --- 4. SIMULADOR ---
    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        partidos = obtener_partidos_airtable()
        if not partidos: st.info("No data.")
        else:
            if "sim_results" not in st.session_state:
                st.session_state.sim_results = {p['ID']: {'GL': p['Goles Real L'] or 0, 'GV': p['Goles Real V'] or 0} for p in partidos}
            if "sim_fp" not in st.session_state:
                equipos_un = list(set([p['Local_ES'] for p in partidos] + [p['Visitante_ES'] for p in partidos]))
                st.session_state.sim_fp = {eq: 0 for eq in equipos_un}

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("♻️ Reset Real", use_container_width=True):
                    st.session_state.sim_results = {p['ID']: {'GL': p['Goles Real L'] or 0, 'GV': p['Goles Real V'] or 0} for p in partidos}
                    st.rerun()
            with col_b2:
                if st.button("🧼 0 - 0", use_container_width=True):
                    st.session_state.sim_results = {p['ID']: {'GL': 0, 'GV': 0} for p in partidos}
                    st.rerun()

            st.divider()
            col_partidos, col_tablas = st.columns([1.2, 1], gap="large")

            with col_partidos:
                st.markdown("### ⚽ " + ("Simulate Matches" if lang == "English" else "Simular Partidos"))
                jornadas_sim = sorted(list(set([p['Jornada'] for p in partidos if p['Jornada']])))
                j_sim = st.selectbox("Jornada:", jornadas_sim, key="j_sim_sel")
                for p in [p for p in partidos if p['Jornada'] == j_sim]:
                    with st.container(border=True):
                        c1, c2, c3, c4, c5 = st.columns([2, 1, 0.5, 1, 2])
                        with c1: st.caption(p['Local_ES'] if lang == "Español" else p['Local_EN'])
                        gl = c2.number_input("", 0, 20, int(st.session_state.sim_results[p['ID']]['GL']), key=f"s_l_{p['ID']}", label_visibility="collapsed")
                        c3.write(":")
                        gv = c4.number_input("", 0, 20, int(st.session_state.sim_results[p['ID']]['GV']), key=f"s_v_{p['ID']}", label_visibility="collapsed")
                        with c5: st.caption(p['Visitante_ES'] if lang == "Español" else p['Visitante_EN'])
                        st.session_state.sim_results[p['ID']] = {'GL': gl, 'GV': gv}

            with col_tablas:
                st.markdown("### 📊 " + ("Live Standing" if lang == "English" else "Posiciones en Vivo"))
                sim_stats = {}
                for p in partidos:
                    res = st.session_state.sim_results[p['ID']]
                    g, l, v = p['Grupo'], p['Local_ES'] if lang=="Español" else p['Local_EN'], p['Visitante_ES'] if lang=="Español" else p['Visitante_EN']
                    gl, gv = res['GL'], res['GV']
                    for eq, rnk in [(l, p['Rank_L']), (v, p['Rank_V'])]:
                        if eq not in sim_stats:
                            sim_stats[eq] = {'Equipo': eq, 'PJ':0, 'PTS':0, 'DG':0, 'GF':0, 'Rank': rnk, 'Grupo': g, 'FP': st.session_state.sim_fp.get(eq, 0)}
                    sim_stats[l]['PJ'] += 1; sim_stats[v]['PJ'] += 1
                    sim_stats[l]['GF'] += gl; sim_stats[v]['GF'] += gv
                    sim_stats[l]['DG'] += (gl - gv); sim_stats[v]['DG'] += (gv - gl)
                    if gl > gv: sim_stats[l]['PTS'] += 3
                    elif gv > gl: sim_stats[v]['PTS'] += 3
                    else: sim_stats[l]['PTS'] += 1; sim_stats[v]['PTS'] += 1

                g_ver = st.radio("Ver Grupo:", sorted(list(set([s['Grupo'] for s in sim_stats.values()]))), horizontal=True)
                st.write("**Fair Play (Points < 0):**")
                eq_fp = [s for s in sim_stats.values() if s['Grupo'] == g_ver]
                cols_fp = st.columns(len(eq_fp))
                for i, eq_data in enumerate(eq_fp):
                    nombre_c = eq_data['Equipo'][:10]
                    val_fp = cols_fp[i].number_input(f"{nombre_c}", None, 0, int(st.session_state.sim_fp.get(eq_data['Equipo'], 0)), key=f"fp_sim_{eq_data['Equipo']}")
                    st.session_state.sim_fp[eq_data['Equipo']] = val_fp
                    sim_stats[eq_data['Equipo']]['FP'] = val_fp

                df_sim = pd.DataFrame(eq_fp).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
                st.dataframe(df_sim[['Equipo', 'PTS', 'DG', 'GF', 'FP']], use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("🏁 Cruces Simulados")
            st.warning("Próximo paso: Programar la matriz de cruces...")

    # --- 5. SEDES Y EQUIPOS (PROVISIONAL) ---
    else:
        st.info("Sedes y Equipos: Próximamente / Coming soon")

else:
    # --- PANTALLA DE LOGIN ---
    st.title("⚽ World Cup 2026")
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code', 'scope': 'openid email profile', 'prompt': 'select_account'})}"
    st.link_button(texts["Español"]["login_btn"], auth_url, type="primary")

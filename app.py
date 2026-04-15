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
                    "ID": f.get("ID Partido"), "Grupo": grupo_real,
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

def obtener_predicciones_usuario(user):
    res = supabase.table("predicciones").select("*").eq("usuario", user).execute()
    return {r['partido_id']: r for r in res.data}

def guardar_prediccion_supabase(user, partido_id, gl, gv):
    supabase.table("predicciones").upsert({"usuario": user, "partido_id": str(partido_id), "goles_local": gl, "goles_visitante": gv}, on_conflict="usuario, partido_id").execute()

def obtener_ranking_global(partidos):
    res = supabase.table("predicciones").select("*").execute()
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

# --- SESIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True

if st.session_state.connected:
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    partidos_data = obtener_partidos_airtable()
    menu = st.sidebar.radio("Menu", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    
    if st.sidebar.button(t["logout"]): st.session_state.connected = False; st.rerun()

    st.title(t["title"])

    # --- 1. INICIO ---
    if menu == t["nav_home"]:
        st.subheader(t["ranking_title"])
        ranking = obtener_ranking_global(partidos_data)
        if ranking: st.table(pd.DataFrame(ranking))
        else: st.info("Aún no hay puntos.")

    # --- 2. JUGAR ---
    elif menu == t["nav_play"]:
        st.subheader(t["nav_play"])
        email_user = "usuario_prueba@gmail.com"
        preds = obtener_predicciones_usuario(email_user)
        jornadas = sorted(list(set([p['Jornada'] for p in partidos_data if p['Jornada']])))
        j_sel = st.selectbox("Jornada:", jornadas)
        with st.form("f_prode"):
            for p in [p for p in partidos_data if p['Jornada'] == j_sel]:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    v_l = preds.get(str(p['ID']), {}).get('goles_local', 0)
                    v_v = preds.get(str(p['ID']), {}).get('goles_visitante', 0)
                    gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed")
                    gv = c4.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed")
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
            if st.form_submit_button(t["save_btn"], use_container_width=True):
                for p in [p for p in partidos_data if p['Jornada'] == j_sel]:
                    guardar_prediccion_supabase(email_user, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                st.success("Guardado!"); st.balloons()

    # --- 3. RESULTADOS ---
    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        stats = {}
        for p in [p for p in partidos_data if p['Goles Real L'] is not None and p['Grupo'] != "Definir"]:
            for eq, gl, gc, rnk, bnd, grp, fp in [(p['Local_ES'] if lang=="Español" else p['Local_EN'], p['Goles Real L'], p['Goles Real V'], p['Rank_L'], p['Bandera_L'], p['Grupo'], p['FP_L']), 
                                             (p['Visitante_ES'] if lang=="Español" else p['Visitante_EN'], p['Goles Real V'], p['Goles Real L'], p['Rank_V'], p['Bandera_V'], p['Grupo'], p['FP_V'])]:
                if eq not in stats: stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PJ':0, 'PTS':0, 'DG':0, 'GF':0, 'FP': 0, 'Rank': rnk, 'Grupo': grp}
                stats[eq]['PJ'] += 1; stats[eq]['GF'] += gl; stats[eq]['DG'] += (gl - gc); stats[eq]['FP'] += fp
                if gl > gc: stats[eq]['PTS'] += 3
                elif gl == gc: stats[eq]['PTS'] += 1

        grupos = sorted(list(set([s['Grupo'] for s in stats.values()])))
        tablas_finales = {}
        for g in grupos:
            st.write(f"### GRUPO {g}")
            df_g = pd.DataFrame([s for s in stats.values() if s['Grupo'] == g]).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
            tablas_finales[g] = df_g
            st.data_editor(df_g[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, key=f"res_{g}", use_container_width=True)

        st.divider()
        st.subheader("🥉 Mejores Terceros")
        terceros = []
        for g in grupos:
            if len(tablas_finales[g]) >= 3: terceros.append(tablas_finales[g].iloc[2])
        if terceros:
            df_3 = pd.DataFrame(terceros).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
            def highlight_3(s): return ['background-color: rgba(46, 204, 113, 0.3)' if s.name < 8 else '' for _ in s]
            st.data_editor(df_3[['Flag', 'Equipo', 'Grupo', 'PTS', 'DG', 'GF']].style.apply(highlight_3, axis=1), column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, use_container_width=True)

        # --- SECCIÓN DE CRUCES RESULTADOS ---
        st.divider()
        st.subheader("🏆 Knockout Stage / Fase de Eliminatorias")
        txt_def = "Por definirse..." if lang == "Español" else "To be defined..."
        c1, c2, c3 = st.columns(3); c1.info(f"**Round of 32 / 16vos**\n\n{txt_def}"); c2.info(f"**Round of 16 / 8vos**\n\n{txt_def}"); c3.info(f"**Quarter-finals / 4tos**\n\n{txt_def}")
        c4, c5, c6 = st.columns(3); c4.warning(f"**Semi-finals / Semifinales**\n\n{txt_def}"); c5.success(f"**Third Place / 3er Puesto**\n\n{txt_def}"); c6.error(f"**GRAND FINAL / GRAN FINAL**\n\n{txt_def}")

    # --- 4. SIMULADOR ---
    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        if "sim_fp" not in st.session_state: 
            st.session_state.sim_fp = {p['Local_ES']: 0 for p in partidos_data}

        # --- 1. BOTONERA DE CONTROL (Reseteos Inteligentes) ---
        c_r1, c_r2, c_r3 = st.columns(3)
        with c_r1:
            if st.button("♻️ " + ("Total Reset (0-0)" if lang=="English" else "Borrar Todo (0-0)"), use_container_width=True):
                for p in partidos_data: st.session_state[f"sl_{p['ID']}"] = 0; st.session_state[f"sv_{p['ID']}"] = 0
                st.session_state.sim_fp = {eq: 0 for eq in st.session_state.sim_fp}
                st.rerun()
        with c_r2:
            if st.button("🏟️ " + ("Reset to Real" if lang=="English" else "Restablecer a Realidad"), use_container_width=True):
                for p in partidos_data:
                    st.session_state[f"sl_{p['ID']}"] = p['Goles Real L'] or 0
                    st.session_state[f"sv_{p['ID']}"] = p['Goles Real V'] or 0
                st.rerun()
        with c_r3:
            if st.button("🧹 " + ("Clear Only Sim" if lang=="English" else "Borrar solo Simulación"), use_container_width=True):
                for p in partidos_data:
                    if p['Goles Real L'] is None:
                        st.session_state[f"sl_{p['ID']}"] = 0; st.session_state[f"sv_{p['ID']}"] = 0
                st.rerun()

        st.divider()

        # --- 2. DISEÑO DE DOS COLUMNAS ---
        col_p, col_t = st.columns([1.2, 1], gap="large")

        with col_p:
            st.markdown("### ⚽ " + ("Enter Scores" if lang=="English" else "Ingresar Goles"))
            j_sim = st.selectbox("Jornada:", sorted(list(set([p['Jornada'] for p in partidos_data if p['Jornada']]))))
            for p in [p for p in partidos_data if p['Jornada'] == j_sim]:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 1, 0.5, 1, 2])
                    c1.write(p['Local_ES'] if lang=="Español" else p['Local_EN'])
                    # Actualización directa sin rerun
                    st.session_state[f"sl_{p['ID']}"] = c2.number_input("L", 0, 20, int(st.session_state.get(f"sl_{p['ID']}", p['Goles Real L'] or 0)), key=f"sl_in_{p['ID']}", label_visibility="collapsed")
                    st.session_state[f"sv_{p['ID']}"] = c4.number_input("V", 0, 20, int(st.session_state.get(f"sv_{p['ID']}", p['Goles Real V'] or 0)), key=f"sv_in_{p['ID']}", label_visibility="collapsed")
                    c5.write(p['Visitante_ES'] if lang=="Español" else p['Visitante_EN'])

        with col_t:
            st.markdown("### 📊 " + ("Standings & Fair Play" if lang=="English" else "Posiciones y Fair Play"))
            
            # --- MOTOR DE CÁLCULO FIFA ---
            sim_stats = {}
            for p in partidos_data:
                gl = st.session_state.get(f"sl_{p['ID']}", 0)
                gv = st.session_state.get(f"sv_{p['ID']}", 0)
                l_n, v_n = (p['Local_ES'] if lang=="Español" else p['Local_EN']), (p['Visitante_ES'] if lang=="Español" else p['Visitante_EN'])
                
                for eq, g_f, g_c, rnk, bnd, grp, fp_air in [(l_n, gl, gv, p['Rank_L'], p['Bandera_L'], p['Grupo'], p['FP_L']), (v_n, gv, gl, p['Rank_V'], p['Bandera_V'], p['Grupo'], p['FP_V'])]:
                    if eq not in sim_stats: 
                        sim_stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PTS':0, 'DG':0, 'GF':0, 'Rank': rnk, 'Grupo': grp, 'FP_Airtable': fp_air, 'Partidos': []}
                    sim_stats[eq]['GF'] += g_f
                    sim_stats[eq]['DG'] += (g_f - g_c)
                    if g_f > g_c: sim_stats[eq]['PTS'] += 3
                    elif g_f == g_c: sim_stats[eq]['PTS'] += 1
                    # Guardamos el duelo individual para el criterio de desempate 1
                    sim_stats[eq]['Partidos'].append({'rival': v_n if eq == l_n else l_n, 'gf': g_f, 'gc': g_c, 'pts': 3 if g_f > g_c else (1 if g_f == g_c else 0)})

            lista_g = sorted(list(set([s['Grupo'] for s in sim_stats.values() if len(str(s['Grupo'])) == 1])))
            g_sel = st.radio("Grupo:", lista_g, horizontal=True)

            st.write("🔧 **Ajustar Fair Play:**")
            eq_grupo = [s for s in sim_stats.values() if s['Grupo'] == g_sel]
            for eq_data in eq_grupo:
                col_n, col_i = st.columns([3, 1])
                col_n.write(eq_data['Equipo'])
                st.session_state.sim_fp[eq_data['Equipo']] = col_i.number_input("FP", None, None, int(st.session_state.sim_fp.get(eq_data['Equipo'], 0)), key=f"fp_sim_{eq_data['Equipo']}", label_visibility="collapsed")

            if st.button("🏆 CALCULAR POSICIONES", type="primary", use_container_width=True):
                # Aplicamos la Lógica de Desempate FIFA
                def criterio_fifa(e):
                    empatados = [x for x in eq_grupo if x['PTS'] == e['PTS'] and x['Equipo'] != e['Equipo']]
                    pts_dir, dg_dir, gf_dir = 0, 0, 0
                    if empatados:
                        nombres_emp = [x['Equipo'] for x in empatados]
                        partidos_dir = [p for p in e['Partidos'] if p['rival'] in nombres_emp]
                        pts_dir = sum(p['pts'] for p in partidos_dir)
                        dg_dir = sum(p['gf'] - p['gc'] for p in partidos_dir)
                        gf_dir = sum(p['gf'] for p in partidos_dir)
                    
                    fp_total = e['FP_Airtable'] + st.session_state.sim_fp.get(e['Equipo'], 0)
                    return (-e['PTS'], -pts_dir, -dg_dir, -gf_dir, -e['DG'], -e['GF'], fp_total, e['Rank'])

                df_s = pd.DataFrame(eq_grupo)
                df_s['FP_Tot'] = df_s.apply(lambda x: x['FP_Airtable'] + st.session_state.sim_fp.get(x['Equipo'], 0), axis=1)
                # Ordenar por la función compleja de la FIFA
                eq_finales = sorted(eq_grupo, key=criterio_fifa)
                df_final = pd.DataFrame(eq_finales)
                df_final['FP'] = df_final.apply(lambda x: x['FP_Airtable'] + st.session_state.sim_fp.get(x['Equipo'], 0), axis=1)
                
                st.data_editor(
                    df_final[['Flag', 'Equipo', 'PTS', 'DG', 'GF', 'FP']], 
                    column_config={"Flag": st.column_config.ImageColumn(" ")}, 
                    hide_index=True, disabled=True, use_container_width=True
                )
                st.success("Criterios FIFA aplicados (incluyendo Duelos Directos).")

        # --- CRUCES ---
        st.divider()
        st.subheader("🏁 " + ("Simulated Knockout Stage" if lang == "English" else "Cruces Simulados"))
        txt_sim_def = "Presiona 'Calcular Posiciones' para actualizar."
        sc1, sc2, sc3 = st.columns(3); sc1.info(f"**16vos**\n\n{txt_sim_def}"); sc2.info(f"**8vos**\n\n{txt_sim_def}"); sc3.info(f"**4tos**\n\n{txt_sim_def}")
        sc4, sc5, sc6 = st.columns(3); sc4.warning(f"**Semis**\n\n{txt_sim_def}"); sc5.success(f"**3er Puesto**\n\n{txt_sim_def}"); sc6.error(f"**Final**\n\n{txt_sim_def}")

    else: st.info("Próximamente")

else:
    st.title("⚽ World Cup 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button("Login with Google", auth_url, type="primary")

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
        "logout": "Cerrar Sesión", "login_btn": "Iniciar sesión con Google",
        "mode_simple": "Prode Simple", "mode_complex": "Magic Mister (Próximamente)",
        "special_bets": "🌟 Apuestas Especiales (Torneo)",
        "champion": "Campeón", "runner_up": "Subcampeón", "third_place": "3er Puesto",
        "surprise": "Equipo Sorpresa (Ranking > 10)", "disappointment": "Equipo Decepción (Ranking ≤ 10)",
        "save_special": "Guardar Apuestas Especiales"
    },
    "English": {
        "nav_home": "🏠 Home", "nav_play": "⚽ Play Predictor", "nav_results": "🏆 Results",
        "nav_sim": "📊 Simulator", "nav_stadiums": "🏟️ Stadiums & Teams", "title": "🏆 2026 World Cup Predictor",
        "ranking_title": "📊 Leaderboard", "next_matches": "📅 Upcoming Matches",
        "no_matches": "🏆 The World Cup has ended!", "save_btn": "Save Predictions",
        "time_left": "⏳ Time left:", "closed": "🔒 Round Closed", "online": "✅ Online",
        "logout": "Logout", "login_btn": "Login with Google",
        "mode_simple": "Simple Predictor", "mode_complex": "Magic Mister (Coming soon)",
        "special_bets": "🌟 Special Bets (Tournament)",
        "champion": "Champion", "runner_up": "Runner-up", "third_place": "3rd Place",
        "surprise": "Surprise Team (Rank > 10)", "disappointment": "Disappointment (Rank ≤ 10)",
        "save_special": "Save Special Bets"
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
                    "ID": f.get("ID Partido"), "Grupo": grupo_real, "Etapa": f.get("Etapa"),
                    "Local_ES": f.get("Nombre (from Equipo Local)")[0] if isinstance(f.get("Nombre (from Equipo Local)"), list) else f.get("Nombre (from Equipo Local)"),
                    "Local_EN": f.get("Nombre EN (from Equipo Local)")[0] if f.get("Nombre EN (from Equipo Local)") else f.get("Nombre (from Equipo Local)"),
                    "Visitante_ES": f.get("Nombre (from Equipo Visitante)")[0] if isinstance(f.get("Nombre (from Equipo Visitante)"), list) else f.get("Nombre (from Equipo Visitante)"),
                    "Visitante_EN": f.get("Nombre EN (from Equipo Visitante)")[0] if f.get("Nombre EN (from Equipo Visitante)") else f.get("Nombre (from Equipo Visitante)"),
                    "Bandera_L": f.get("Bandera L")[0].get("url") if f.get("Bandera L") else "",
                    "Bandera_V": f.get("Bandera V")[0].get("url") if f.get("Bandera V") else "",
                    "Rank_L": int(r_l[0]) if isinstance(r_l, list) else int(r_l or 100),
                    "Rank_V": int(r_v[0]) if isinstance(r_v, list) else int(r_v or 100),
                    "FP_L": f.get("Fair Play L", 0), "FP_V": f.get("Fair Play V", 0),
                    "Goles Real L": f.get("Goles Local"), "Goles Real V": f.get("Goles Visitante"),
                    "Fecha_Hora": f.get("Fecha y Hora"), 
                    "Jornada_ES": f.get("Jornada"), "Jornada_EN": f.get("Jornada EN")
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
    if not url_bandera:
        return f'<div style="display: flex; align-items: center; justify-content: {"flex-start" if align=="left" else "flex-end"}; flex-direction: {flex}; gap: 10px;"><span>{nombre}</span></div>'
    return f'<div style="display: flex; align-items: center; justify-content: {"flex-start" if align=="left" else "flex-end"}; flex-direction: {flex}; gap: 10px;"><img src="{url_bandera}" width="30" style="border-radius:2px;"><span>{nombre}</span></div>'

# --- SESIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True

if st.session_state.connected:
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    partidos_data = obtener_partidos_airtable()
    menu = st.sidebar.radio("Menu", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    
    modo_juego = st.sidebar.radio("Modo / Mode", [t["mode_simple"], t["mode_complex"]])
    if st.sidebar.button(t["logout"]): st.session_state.connected = False; st.rerun()

    st.title(t["title"])

    # --- 1. INICIO ---
    if menu == t["nav_home"]:
        col_rank, col_next = st.columns([1.5, 1], gap="large")
        
        with col_rank:
            st.subheader(t["ranking_title"])
            ranking = obtener_ranking_global(partidos_data)
            if ranking: 
                st.table(pd.DataFrame(ranking))
            else: 
                st.info("Aún no hay puntos." if lang == "Español" else "No points yet.")

        with col_next:
            st.subheader(t["next_matches"])
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora = datetime.now(zona_sofia)
            proximos = []
            
            for p in partidos_data:
                if p['Fecha_Hora']:
                    f_dt = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                    if f_dt > ahora:
                        proximos.append((f_dt, p))
            
            proximos.sort(key=lambda x: x[0])
            
            if proximos:
                for f, p in proximos[:5]:
                    with st.container(border=True):
                        st.caption(f.strftime('%d/%m - %H:%M hs'))
                        st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        st.markdown("<div style='text-align:center; font-size:10px; color:gray; margin:2px 0;'>VS</div>", unsafe_allow_html=True)
                        st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang), unsafe_allow_html=True)
            else:
                st.success(t["no_matches"])

    # --- 2. JUGAR ---
    elif menu == t["nav_play"]:
        if modo_juego == t["mode_complex"]:
            st.info("La interfaz de Magic Mister está en desarrollo. / Magic Mister interface is under development.")
        else:
            st.subheader(t["nav_play"])
            email_user = "usuario_prueba@gmail.com" 
            preds = obtener_predicciones_usuario(email_user)
            
            # --- FASE 1: APUESTAS ESPECIALES REPARADAS ---
            with st.expander(t["special_bets"], expanded=False):
                # Extraemos equipos y rankings
                dict_equipos = {}
                for p in partidos_data:
                    if p['Local_ES']: dict_equipos[p['Local_ES'] if lang == "Español" else p['Local_EN']] = p['Rank_L']
                    if p['Visitante_ES']: dict_equipos[p['Visitante_ES'] if lang == "Español" else p['Visitante_EN']] = p['Rank_V']
                
                lista_todos = [""] + sorted(list(dict_equipos.keys()))
                lista_sorpresa = [""] + sorted([eq for eq, rank in dict_equipos.items() if rank > 10])
                lista_decepcion = [""] + sorted([eq for eq, rank in dict_equipos.items() if rank <= 10])
                
                c1, c2, c3 = st.columns(3)
                val_camp = c1.selectbox(t["champion"], lista_todos)
                val_sub = c2.selectbox(t["runner_up"], lista_todos)
                val_ter = c3.selectbox(t["third_place"], lista_todos)
                
                c4, c5 = st.columns(2)
                val_sorp = c4.selectbox(t["surprise"], lista_sorpresa)
                val_dec = c5.selectbox(t["disappointment"], lista_decepcion)
                
                # Validaciones
                top3_seleccionados = [x for x in [val_camp, val_sub, val_ter] if x != ""]
                hay_error_top3 = len(top3_seleccionados) != len(set(top3_seleccionados))
                
                if hay_error_top3:
                    st.error("Error: No puedes repetir el mismo equipo en el Top 3 (Campeón, Subcampeón, 3er Puesto)." if lang == "Español" else "Error: You cannot repeat the same team in the Top 3.")
                
                if val_dec != "" and val_dec in top3_seleccionados:
                    st.warning("Este equipo fue elegido para los primeros 3 puestos, ¿estás seguro de tu elección?" if lang == "Español" else "This team was chosen for the Top 3 spots, are you sure of your choice?")

                if st.button(t["save_special"], disabled=hay_error_top3):
                    st.success("Apuestas especiales guardadas!" if lang == "Español" else "Special bets saved!")

            st.divider()

            # --- FASE 1: JORNADAS COMPLETAS ---
            jornadas_fijas_es = ["Fecha 1", "Fecha 2", "Fecha 3", "16vos de final", "8vos de final", "4tos de final", "Semifinales", "Final y 3er puesto"]
            jornadas_fijas_en = ["Matchday 1", "Matchday 2", "Matchday 3", "Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final & 3rd place"]
            jornadas_list = jornadas_fijas_es if lang == "Español" else jornadas_fijas_en
            
            j_sel = st.selectbox("Jornada / Matchday:", jornadas_list)
            
            mensajes_bloqueo = {
                "16vos de final": "Los equipos se definirán tras la finalización de la Fecha 3. ¡Vuelve el 28/6/2026 a las 8:00 hs!",
                "Round of 32": "Teams will be defined after Matchday 3. Come back on 6/28/2026 at 8:00 AM!",
                "8vos de final": "Los equipos se definirán tras los 16vos. ¡Vuelve el 04/7/2026 a las 8:00 hs!",
                "Round of 16": "Teams will be defined after the Round of 32. Come back on 7/04/2026 at 8:00 AM!",
                "4tos de final": "Los equipos se definirán tras los 8vos. ¡Vuelve el 08/7/2026 a las 2:00 hs!",
                "Quarter-finals": "Teams will be defined after the Round of 16. Come back on 7/08/2026 at 2:00 AM!",
                "Semifinales": "Los equipos se definirán tras los 4tos. ¡Vuelve el 12/7/2026 a las 7:00 hs!",
                "Semi-finals": "Teams will be defined after the Quarter-finals. Come back on 7/12/2026 at 7:00 AM!",
                "Final y 3er puesto": "Los equipos se definirán tras las Semis. ¡Vuelve el 16/7/2026 a las 1:00 hs!",
                "Final & 3rd place": "Teams will be defined after the Semi-finals. Come back on 7/16/2026 at 1:00 AM!"
            }

            if j_sel in mensajes_bloqueo:
                st.info(mensajes_bloqueo[j_sel])
            else:
                with st.form("f_prode"):
                    # Filtramos por jornada pero usamos Airtable key real si existe
                    jornada_key = 'Jornada_ES' if lang == "Español" else 'Jornada_EN'
                    partidos_jornada = [p for p in partidos_data if p.get(jornada_key) == j_sel]
                    partidos_ordenados = sorted(partidos_jornada, key=lambda x: str(x['Grupo']))

                    if not partidos_ordenados:
                        st.info("No hay partidos cargados para esta jornada." if lang == "Español" else "No matches loaded for this matchday.")
                    
                    for p in partidos_ordenados:
                        with st.container(border=True):
                            st.caption(f"Grupo {p['Grupo']}")
                            c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                            
                            with c1: 
                                st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                            
                            v_l = preds.get(str(p['ID']), {}).get('goles_local', 0)
                            v_v = preds.get(str(p['ID']), {}).get('goles_visitante', 0)
                            
                            gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed")
                            c3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                            gv = c4.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed")
                            
                            with c5: 
                                st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
                    
                    if st.form_submit_button(t["save_btn"], use_container_width=True):
                        for p in partidos_jornada:
                            guardar_prediccion_supabase(email_user, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                        st.success("¡Pronósticos guardados correctamente!" if lang == "Español" else "Predictions saved successfully!")
                        st.balloons()

    # --- 3. RESULTADOS ---
    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        stats = {}
        
        for p in partidos_data:
            if p['Grupo'] != "Definir":
                for eq_key, bnd_key, rnk_key in [('Local', 'Bandera_L', 'Rank_L'), ('Visitante', 'Bandera_V', 'Rank_V')]:
                    eq_name = p[f'{eq_key}_ES'] if lang == "Español" else p[f'{eq_key}_EN']
                    if eq_name and eq_name not in stats:
                        stats[eq_name] = {
                            'Flag': p[bnd_key], 'Equipo': eq_name, 'PJ': 0, 'PTS': 0, 
                            'DG': 0, 'GF': 0, 'GC': 0, 'FP': 0, 'Rank': p[rnk_key], 'Grupo': p['Grupo']
                        }

        for p in [p for p in partidos_data if p['Goles Real L'] is not None and p['Grupo'] != "Definir"]:
            eq_l = p['Local_ES'] if lang == "Español" else p['Local_EN']
            eq_v = p['Visitante_ES'] if lang == "Español" else p['Visitante_EN']
            gl, gv = p['Goles Real L'], p['Goles Real V']
            
            stats[eq_l]['PJ'] += 1; stats[eq_l]['GF'] += gl; stats[eq_l]['GC'] += gv; stats[eq_l]['DG'] += (gl - gv); stats[eq_l]['FP'] += p['FP_L']
            stats[eq_v]['PJ'] += 1; stats[eq_v]['GF'] += gv; stats[eq_v]['GC'] += gl; stats[eq_v]['DG'] += (gv - gl); stats[eq_v]['FP'] += p['FP_V']
            
            if gl > gv: stats[eq_l]['PTS'] += 3
            elif gl < gv: stats[eq_v]['PTS'] += 3
            else:
                stats[eq_l]['PTS'] += 1; stats[eq_v]['PTS'] += 1

        grupos = sorted(list(set([s['Grupo'] for s in stats.values()])))
        tablas_finales = {}
        
        for g in grupos:
            st.write(f"### GRUPO {g}")
            df_g = pd.DataFrame([s for s in stats.values() if s['Grupo'] == g]).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
            tablas_finales[g] = df_g
            # FASE 1: Se agregó FP a la vista
            st.data_editor(df_g[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, key=f"res_{g}", use_container_width=True)

        st.divider()
        st.subheader("🥉 Mejores Terceros / Best Third-Placed Teams")
        terceros = []
        for g in grupos:
            if len(tablas_finales[g]) >= 3: terceros.append(tablas_finales[g].iloc[2])
        if terceros:
            df_3 = pd.DataFrame(terceros).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
            def highlight_3(s): return ['background-color: rgba(46, 204, 113, 0.3)' if s.name < 8 else '' for _ in s]
            st.data_editor(df_3[['Flag', 'Equipo', 'Grupo', 'PTS', 'DG', 'GF', 'GC', 'FP']].style.apply(highlight_3, axis=1), column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, use_container_width=True)

        st.divider()
        
        st.subheader("📅 " + ("Resultados por Jornada" if lang == "Español" else "Results by Matchday"))
        jornada_key = 'Jornada_ES' if lang == "Español" else 'Jornada_EN'
        jornadas_res_list = []
        for p in partidos_data:
            j_val = p.get(jornada_key)
            if j_val and j_val not in jornadas_res_list:
                jornadas_res_list.append(j_val)
                
        if jornadas_res_list:
            j_res_sel = st.selectbox("Seleccionar / Select:", jornadas_res_list, key="sel_resultados")
            partidos_res = [p for p in partidos_data if p.get(jornada_key) == j_res_sel]
            
            for p in partidos_res:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    
                    gl_txt = p['Goles Real L'] if p['Goles Real L'] is not None else "-"
                    gv_txt = p['Goles Real V'] if p['Goles Real V'] is not None else "-"
                    
                    c2.markdown(f"<div style='text-align:right; font-size:18px; font-weight:bold;'>{gl_txt}</div>", unsafe_allow_html=True)
                    c3.markdown("<div style='text-align:center; padding-top:2px;'>:</div>", unsafe_allow_html=True)
                    c4.markdown(f"<div style='text-align:left; font-size:18px; font-weight:bold;'>{gv_txt}</div>", unsafe_allow_html=True)
                    
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
        
        # --- FASE 1: DESPLEGABLE Y CUADROS DE ELIMINATORIAS REALES ---
        st.divider()
        st.subheader("🏆 Knockout Stage / Fase de Eliminatorias")
        
        fases_eliminatorias = ["16vos", "8vos", "4tos", "Semifinales", "Final y 3er Puesto"]
        fase_ko_sel = st.selectbox("Ver Fase / View Stage:", fases_eliminatorias)
        
        col_izq, col_der = st.columns(2)
        
        if fase_ko_sel == "16vos":
            with col_izq:
                st.markdown("#### Llave Izquierda")
                cruces_izq = [
                    ("M74", "1E", "3ro (A/B/C/D/F)"), ("M77", "1I", "3ro (C/D/F/G/H)"),
                    ("M73", "2A", "2B"), ("M75", "1F", "2C"),
                    ("M83", "2K", "2L"), ("M84", "1H", "2J"),
                    ("M81", "1D", "3ro (B/E/F/I/J)"), ("M82", "1G", "3ro (A/E/H/I/J)")
                ]
                for match_id, eq1, eq2 in cruces_izq:
                    with st.container(border=True):
                        st.caption(match_id)
                        st.markdown(f"**{eq1}** vs **{eq2}**")

            with col_der:
                st.markdown("#### Llave Derecha")
                cruces_der = [
                    ("M76", "1C", "2F"), ("M78", "2E", "2I"),
                    ("M79", "1A", "3ro (C/E/F/H/I)"), ("M80", "1L", "3ro (E/H/I/J/K)"),
                    ("M86", "1J", "2H"), ("M88", "2D", "2G"),
                    ("M85", "1B", "3ro (E/F/G/I/J)"), ("M87", "1K", "3ro (D/E/I/J/L)")
                ]
                for match_id, eq1, eq2 in cruces_der:
                    with st.container(border=True):
                        st.caption(match_id)
                        st.markdown(f"**{eq1}** vs **{eq2}**")
                        
        elif fase_ko_sel == "8vos":
            with col_izq:
                st.markdown("#### Llave Izquierda")
                for match_id, eq1, eq2 in [("M89", "W74", "W77"), ("M90", "W73", "W75"), ("M93", "W83", "W84"), ("M94", "W81", "W82")]:
                    with st.container(border=True):
                        st.caption(match_id)
                        st.markdown(f"**{eq1}** vs **{eq2}**")
            with col_der:
                st.markdown("#### Llave Derecha")
                for match_id, eq1, eq2 in [("M91", "W76", "W78"), ("M92", "W79", "W80"), ("M95", "W86", "W88"), ("M96", "W85", "W87")]:
                    with st.container(border=True):
                        st.caption(match_id)
                        st.markdown(f"**{eq1}** vs **{eq2}**")

        elif fase_ko_sel == "4tos":
            with col_izq:
                st.markdown("#### Llave Izquierda")
                for match_id, eq1, eq2 in [("M97", "W89", "W90"), ("M98", "W93", "W94")]:
                    with st.container(border=True):
                        st.caption(match_id)
                        st.markdown(f"**{eq1}** vs **{eq2}**")
            with col_der:
                st.markdown("#### Llave Derecha")
                for match_id, eq1, eq2 in [("M99", "W91", "W92"), ("M100", "W95", "W96")]:
                    with st.container(border=True):
                        st.caption(match_id)
                        st.markdown(f"**{eq1}** vs **{eq2}**")

        elif fase_ko_sel == "Semifinales":
            with col_izq:
                st.markdown("#### Llave Izquierda")
                with st.container(border=True):
                    st.caption("M101")
                    st.markdown(f"**W97** vs **W98**")
            with col_der:
                st.markdown("#### Llave Derecha")
                with st.container(border=True):
                    st.caption("M102")
                    st.markdown(f"**W99** vs **W100**")
                    
        elif fase_ko_sel == "Final y 3er Puesto":
            with col_izq:
                st.markdown("#### 🥉 3er Puesto")
                with st.container(border=True):
                    st.caption("M103")
                    st.markdown(f"**RU101** vs **RU102**")
            with col_der:
                st.markdown("#### 🏆 Final")
                with st.container(border=True):
                    st.caption("M104")
                    st.markdown(f"**W101** vs **W102**")

    # --- 4. SIMULADOR ---
    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        if "sim_fp" not in st.session_state: 
            st.session_state.sim_fp = {p['Local_ES']: 0 for p in partidos_data}

        # --- BOTONERA SIMULADOR ---
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

        # --- DISEÑO POR GRUPO SIMULADOR ---
        grupos_disponibles = sorted(list(set([p['Grupo'] for p in partidos_data if len(p['Grupo']) == 1 and p['Grupo'] != "Definir"])))
        if not grupos_disponibles:
            st.warning("No hay grupos definidos.")
        else:
            g_sel = st.radio("Selecciona Grupo para Simular:", grupos_disponibles, horizontal=True)

            col_izq, col_der = st.columns([1.1, 1], gap="medium")

            with col_izq:
                st.markdown(f"### ⚽ Partidos Grupo {g_sel}")
                partidos_grupo = [p for p in partidos_data if p['Grupo'] == g_sel]
                for p in partidos_grupo:
                    with st.container(border=True):
                        st.caption(f"Grupo {p['Grupo']}")
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                        with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        st.session_state[f"sl_{p['ID']}"] = c2.number_input("L", 0, 20, int(st.session_state.get(f"sl_{p['ID']}", 0)), key=f"sim_l_{p['ID']}", label_visibility="collapsed")
                        c3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                        st.session_state[f"sv_{p['ID']}"] = c4.number_input("V", 0, 20, int(st.session_state.get(f"sv_{p['ID']}", 0)), key=f"sim_v_{p['ID']}", label_visibility="collapsed")
                        with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)

            with col_der:
                st.markdown(f"### 📊 Posiciones Grupo {g_sel}")
                
                st.write("🔧 **Ajustar Fair Play (Simular tarjetas)**")
                eq_nombres = sorted(list(set([p['Local_ES'] for p in partidos_grupo] + [p['Visitante_ES'] for p in partidos_grupo])))
                
                for eq_name in eq_nombres:
                    band_url = next((p['Bandera_L'] for p in partidos_data if p['Local_ES'] == eq_name), "")
                    if not band_url: band_url = next((p['Bandera_V'] for p in partidos_data if p['Visitante_ES'] == eq_name), "")

                    with st.container(border=True):
                        cf1, cf2 = st.columns([3, 1])
                        with cf1:
                            if band_url:
                                st.markdown(f"<div style='display:flex; align-items:center; gap:10px;'><img src='{band_url}' width='25'><b>{eq_name}</b></div>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<b>{eq_name}</b>", unsafe_allow_html=True)
                        
                        val_memoria = st.session_state.sim_fp.get(eq_name, 0)
                        val_safe = min(0, int(val_memoria))

                        val_fp = cf2.number_input(
                            "FP", min_value=-100, max_value=0, value=val_safe, 
                            key=f"fp_input_{eq_name}_{g_sel}_{lang}", label_visibility="collapsed"
                        )
                        st.session_state.sim_fp[eq_name] = val_fp
                        
                st.write("")
                if st.button("🏆 CALCULAR POSICIONES", type="primary", use_container_width=True):
                    st.session_state[f"trigger_recalc_{g_sel}"] = True

                if st.session_state.get(f"trigger_recalc_{g_sel}", False):
                    sim_stats = {}
                    for p in [p for p in partidos_data if p['Grupo'] == g_sel]:
                        gl, gv = st.session_state.get(f"sl_{p['ID']}", 0), st.session_state.get(f"sv_{p['ID']}", 0)
                        for eq, gf, gc, rnk, bnd, fp_air in [(p['Local_ES'], gl, gv, p['Rank_L'], p['Bandera_L'], p['FP_L']), (p['Visitante_ES'], gv, gl, p['Rank_V'], p['Bandera_V'], p['FP_V'])]:
                            if eq not in sim_stats:
                                sim_stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PTS':0, 'DG':0, 'GF':0, 'Rank': rnk, 'FP_Base': fp_air, 'Partidos': []}
                            sim_stats[eq]['GF'] += gf
                            sim_stats[eq]['DG'] += (gf - gc)
                            if gf > gc: sim_stats[eq]['PTS'] += 3
                            elif gf == gc: sim_stats[eq]['PTS'] += 1
                            sim_stats[eq]['Partidos'].append({'rival': p['Visitante_ES'] if eq == p['Local_ES'] else p['Local_ES'], 'gf': gf, 'gc': gc, 'pts': 3 if gf > gc else (1 if gf == gc else 0)})

                    def calcular_orden_fifa(e):
                        empatados = [x for x in sim_stats.values() if x['PTS'] == e['PTS'] and x['Equipo'] != e['Equipo']]
                        pts_dir, dg_dir, gf_dir = 0, 0, 0
                        if empatados:
                            nombres_emp = [x['Equipo'] for x in empatados]
                            p_dir = [p for p in e['Partidos'] if p['rival'] in nombres_emp]
                            pts_dir = sum(p['pts'] for p in p_dir)
                            dg_dir = sum(p['gf'] - p['gc'] for p in p_dir)
                            gf_dir = sum(p['gf'] for p in p_dir)
                        fp_total = e['FP_Base'] + st.session_state.sim_fp.get(e['Equipo'], 0)
                        return (-e['PTS'], -pts_dir, -dg_dir, -gf_dir, -e['DG'], -e['GF'], -fp_total, e['Rank'])

                    df_final = pd.DataFrame(sorted(sim_stats.values(), key=calcular_orden_fifa))
                    df_final['FP'] = df_final.apply(lambda x: x['FP_Base'] + st.session_state.sim_fp.get(x['Equipo'], 0), axis=1)

                    st.data_editor(
                        df_final[['Flag', 'Equipo', 'PTS', 'DG', 'GF', 'FP']],
                        column_config={"Flag": st.column_config.ImageColumn(" "), "FP": st.column_config.NumberColumn("FP", format="%d")},
                        hide_index=True, use_container_width=True, disabled=True
                    )
                    
            # --- CRUCES SIMULADOS ---
            st.divider()
            st.subheader("🏁 " + ("Simulated Knockout Stage" if lang == "English" else "Cruces Simulados"))
            txt_sim_def = "Presiona 'Calcular Posiciones' para actualizar." if lang == "Español" else "Press 'Calcular Posiciones' to update."
            sc1, sc2, sc3 = st.columns(3); sc1.info(f"**16vos**\n\n{txt_sim_def}"); sc2.info(f"**8vos**\n\n{txt_sim_def}"); sc3.info(f"**4tos**\n\n{txt_sim_def}")
            sc4, sc5, sc6 = st.columns(3); sc4.warning(f"**Semis**\n\n{txt_sim_def}"); sc5.success(f"**3er Puesto**\n\n{txt_sim_def}"); sc6.error(f"**Final**\n\n{txt_sim_def}")

    # --- 5. SEDES Y EQUIPOS ---
    elif menu == t["nav_stadiums"]:
        st.subheader(t["nav_stadiums"])
        st.info("Próximamente / Coming Soon")

else:
    st.title("⚽ World Cup 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button("Login with Google", auth_url, type="primary")

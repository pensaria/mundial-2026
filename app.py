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
                    "Rank_L": r_l[0] if isinstance(r_l, list) else (r_l or 100),
                    "Rank_V": r_v[0] if isinstance(r_v, list) else (r_v or 100),
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
    # Si no hay bandera, mostrar solo el nombre
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
            email_user = "usuario_prueba@gmail.com" # Hasta que se implemente Auth real
            preds = obtener_predicciones_usuario(email_user)
            
            # Apuestas especiales
            with st.expander(t["special_bets"], expanded=False):
                # Generar lista de equipos únicos
                lista_equipos_es = sorted(list(set([p['Local_ES'] for p in partidos_data if p['Local_ES']])))
                lista_equipos_en = sorted(list(set([p['Local_EN'] for p in partidos_data if p['Local_EN']])))
                lista_eq = lista_equipos_es if lang == "Español" else lista_equipos_en
                lista_eq = [""] + lista_eq
                
                c1, c2, c3 = st.columns(3)
                c1.selectbox(t["champion"], lista_eq)
                c2.selectbox(t["runner_up"], lista_eq)
                c3.selectbox(t["third_place"], lista_eq)
                c4, c5 = st.columns(2)
                c4.selectbox(t["surprise"], lista_eq)
                c5.selectbox(t["disappointment"], lista_eq)
                if st.button(t["save_special"]):
                    st.success("Apuestas especiales guardadas!" if lang == "Español" else "Special bets saved!")

            st.divider()

            # Selector de Jornada
            # Usar la columna correcta según el idioma
            jornada_key = 'Jornada_ES' if lang == "Español" else 'Jornada_EN'
            # Extraer jornadas únicas manteniendo el orden lógico (Airtable debería estar ordenado por ID)
            jornadas_list = []
            for p in partidos_data:
                j_val = p.get(jornada_key)
                if j_val and j_val not in jornadas_list:
                    jornadas_list.append(j_val)
            
            if not jornadas_list:
                st.warning("No hay jornadas definidas.")
            else:
                j_sel = st.selectbox("Jornada / Matchday:", jornadas_list)
                
                # Mensajes de bloqueo para eliminatorias
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
                        partidos_jornada = [p for p in partidos_data if p.get(jornada_key) == j_sel]
                        partidos_ordenados = sorted(partidos_jornada, key=lambda x: str(x['Grupo']))

                        for p in partidos_ordenados:
                            with st.container(border=True):
                                # Nombre del grupo sin bandera roja
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
        st.subheader("🥉 Mejores Terceros / Best Third-Placed Teams")
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

        # --- 1. BOTONERA DE CONTROL (V1 Restaurada) ---
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

        # --- 2. DISEÑO POR GRUPO ---
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
                    
            # --- CRUCES ---
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

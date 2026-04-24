import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io

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
        "save_special": "Guardar Apuestas Especiales",
        "user_welcome": "¡Bienvenido, ", "ask_username": "Elige tu nombre de jugador para empezar:",
        "save_user": "Comenzar a Jugar", "reset_btn": "Reiniciar Jornada 🗑️",
        "lock_msg": "⚠️ Esta jornada está cerrada. Los cambios no se guardarán.",
        "my_ticket": "🎟️ Mi Ticket de Apuestas", "gen_ticket": "Generar Imagen de mi Jugada",
        "download_ticket": "Descargar mi Ticket 📥"
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
        "save_special": "Save Special Bets",
        "user_welcome": "Welcome, ", "ask_username": "Choose your player name to start:",
        "save_user": "Start Playing", "reset_btn": "Reset Matchday 🗑️",
        "lock_msg": "⚠️ This matchday is locked. Changes won't be saved.",
        "my_ticket": "🎟️ My Betting Ticket", "gen_ticket": "Generate My Ticket Image",
        "download_ticket": "Download My Ticket 📥"
    }
}

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()

# --- FUNCIONES DE DB ---

def obtener_perfil(email):
    res = supabase.table("perfiles").select("*").eq("email", email).execute()
    return res.data[0] if res.data else None

def crear_perfil(email, username):
    supabase.table("perfiles").insert({"email": email, "nombre_usuario": username}).execute()

def guardar_apuestas_especiales(email, camp, sub, ter, sorp, decep):
    supabase.table("perfiles").update({
        "equipo_campeon": camp, "equipo_subcampeon": sub, 
        "equipo_tercero": ter, "equipo_sorpresa": sorp, "equipo_decepcion": decep
    }).eq("email", email).execute()

def borrar_predicciones_jornada(user_email, partidos_ids):
    for pid in partidos_ids:
        supabase.table("predicciones").delete().eq("usuario", user_email).eq("partido_id", str(pid)).execute()

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

def asignar_terceros(grupos_terceros):
    permitidos = {
        'R1': ['C', 'E', 'F', 'H', 'I'], 'R2': ['E', 'F', 'G', 'I', 'J'],
        'R3': ['B', 'E', 'F', 'I', 'J'], 'R4': ['A', 'B', 'C', 'D', 'F'],
        'R5': ['A', 'E', 'H', 'I', 'J'], 'R6': ['C', 'D', 'F', 'G', 'H'],
        'R7': ['D', 'E', 'I', 'J', 'L'], 'R8': ['E', 'H', 'I', 'J', 'K']
    }
    def resolver(index, disponibles, asignacion):
        if index == 8: return asignacion
        r_key = f'R{index+1}'
        for g in permitidos[r_key]:
            if g in disponibles:
                disp_copy = disponibles.copy()
                disp_copy.remove(g)
                res = resolver(index + 1, disp_copy, asignacion + [(r_key, g)])
                if res: return res
        return None
    res = resolver(0, grupos_terceros, [])
    return dict(res) if res else None

# --- GENERAR TICKET IMAGEN ---
def generar_ticket_prode(username, camp, sub, ter, sorp, decep):
    img = Image.new('RGB', (600, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # Dibujar bordes decorativos
    d.rectangle([10, 10, 590, 390], outline=(0, 100, 0), width=5)
    
    try:
        fnt_title = ImageFont.load_default() # Idealmente cargar una ttf
        fnt_text = ImageFont.load_default()
    except:
        fnt_title = None
        fnt_text = None

    d.text((200, 30), "TICKET DE APUESTA 2026", fill=(0, 0, 0))
    d.text((50, 80), f"Usuario: {username}", fill=(0, 0, 0))
    d.text((50, 130), f"Campeón: {camp}", fill=(0, 0, 0))
    d.text((50, 160), f"Subcampeón: {sub}", fill=(0, 0, 0))
    d.text((50, 190), f"3er Puesto: {ter}", fill=(0, 0, 0))
    d.text((50, 240), f"Sorpresa: {sorp}", fill=(0, 0, 0))
    d.text((50, 270), f"Decepción: {decep}", fill=(0, 0, 0))
    d.text((150, 350), "¡Suerte en el Mundial!", fill=(0, 100, 0))
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# --- SESIÓN ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True
if "user_email" not in st.session_state: st.session_state.user_email = "usuario_prueba@gmail.com" # Placeholder hasta real auth

if st.session_state.connected:
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    partidos_data = obtener_partidos_airtable()
    
    # --- FLUJO DE USUARIO ---
    perfil_actual = obtener_perfil(st.session_state.user_email)
    
    if not perfil_actual:
        st.warning(t["ask_username"])
        new_nick = st.text_input("Nickname:", max_chars=15)
        if st.button(t["save_user"]):
            if new_nick:
                crear_perfil(st.session_state.user_email, new_nick)
                st.rerun()
        st.stop()
    
    username_display = perfil_actual['nombre_usuario']
    st.sidebar.write(f"⚽ {t['user_welcome']}**{username_display}**!")
    
    menu = st.sidebar.radio("Menu", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    modo_juego = st.sidebar.radio("Modo / Mode", [t["mode_simple"], t["mode_complex"]])
    
    if st.sidebar.button(t["logout"]): st.session_state.connected = False; st.rerun()
    st.title(t["title"])

    # --- 1. INICIO (Mantenido) ---
    if menu == t["nav_home"]:
        col_rank, col_next = st.columns([1.5, 1], gap="large")
        with col_rank:
            st.subheader(t["ranking_title"])
            ranking = obtener_ranking_global(partidos_data)
            if ranking: st.table(pd.DataFrame(ranking))
            else: st.info("Aún no hay puntos.")
        with col_next:
            st.subheader(t["next_matches"])
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora = datetime.now(zona_sofia)
            proximos = []
            for p in partidos_data:
                if p['Fecha_Hora']:
                    f_dt = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                    if f_dt > ahora: proximos.append((f_dt, p))
            proximos.sort(key=lambda x: x[0])
            if proximos:
                for f, p in proximos[:5]:
                    with st.container(border=True):
                        st.caption(f.strftime('%d/%m - %H:%M hs'))
                        st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        st.markdown("<div style='text-align:center; font-size:10px; color:gray; margin:2px 0;'>VS</div>", unsafe_allow_html=True)
                        st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang), unsafe_allow_html=True)
            else: st.success(t["no_matches"])

    # --- 2. JUGAR (CIRUGÍA FASE 2.2) ---
    elif menu == t["nav_play"]:
        if modo_juego == t["mode_complex"]:
            st.info("Magic Mister interface is under development.")
        else:
            st.subheader(t["nav_play"])
            preds = obtener_predicciones_usuario(st.session_state.user_email)
            
            # --- APUESTAS ESPECIALES (REAL) ---
            with st.expander(t["special_bets"], expanded=False):
                dict_eq = {}
                for p in partidos_data:
                    dict_eq[p['Local_ES' if lang=="Español" else 'Local_EN']] = p['Rank_L']
                    dict_eq[p['Visitante_ES' if lang=="Español" else 'Visitante_EN']] = p['Rank_V']
                
                lista_todos = [""] + sorted(list(dict_eq.keys()))
                lista_sorp = [""] + sorted([eq for eq, r in dict_eq.items() if r > 10])
                lista_dece = [""] + sorted([eq for eq, r in dict_eq.items() if r <= 10])
                
                # Valores cargados de DB
                c1, c2, c3 = st.columns(3)
                v_c = c1.selectbox(t["champion"], lista_todos, index=lista_todos.index(perfil_actual['equipo_campeon']) if perfil_actual['equipo_campeon'] in lista_todos else 0)
                v_s = c2.selectbox(t["runner_up"], lista_todos, index=lista_todos.index(perfil_actual['equipo_subcampeon']) if perfil_actual['equipo_subcampeon'] in lista_todos else 0)
                v_t = c3.selectbox(t["third_place"], lista_todos, index=lista_todos.index(perfil_actual['equipo_terceros']) if perfil_actual['equipo_tercero'] in lista_todos else 0)
                
                c4, c5 = st.columns(2)
                v_sor = c4.selectbox(t["surprise"], lista_sorp, index=lista_sorp.index(perfil_actual['equipo_sorpresa']) if perfil_actual['equipo_sorpresa'] in lista_sorp else 0)
                v_dec = c5.selectbox(t["disappointment"], lista_dece, index=lista_dece.index(perfil_actual['equipo_decepcion']) if perfil_actual['equipo_decepcion'] in lista_dece else 0)
                
                top3 = [x for x in [v_c, v_s, v_t] if x != ""]
                error_top3 = len(top3) != len(set(top3))
                if error_top3: st.error("Error: Top 3 repetido.")
                if v_dec != "" and v_dec in top3: st.warning("Elegiste un Top 3 como decepción, ¿seguro?")

                if st.button(t["save_special"], disabled=error_top3):
                    guardar_apuestas_especiales(st.session_state.user_email, v_c, v_s, v_t, v_sor, v_dec)
                    st.success("¡Guardado!")

            st.divider()

            # --- JORNADAS Y TIMER ---
            j_es = ["Fecha 1", "Fecha 2", "Fecha 3", "16vos de final", "8vos de final", "4tos de final", "Semifinales", "Final y 3er puesto"]
            j_en = ["Matchday 1", "Matchday 2", "Matchday 3", "Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final & 3rd place"]
            j_list = j_es if lang == "Español" else j_en
            j_sel = st.selectbox("Jornada:", j_list)
            
            # Cálculo del Bloqueo (5 horas)
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora = datetime.now(zona_sofia)
            partidos_jornada = [p for p in partidos_data if p.get('Jornada_ES' if lang=="Español" else 'Jornada_EN') == j_sel]
            
            bloqueado = False
            if partidos_jornada:
                primer_partido = min([datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia) for p in partidos_jornada if p['Fecha_Hora']])
                if ahora > (primer_partido - timedelta(hours=5)): bloqueado = True

            if bloqueado: st.error(t["lock_msg"])
            
            with st.form("f_play"):
                for p in sorted(partidos_jornada, key=lambda x: str(x['Grupo'])):
                    with st.container(border=True):
                        st.caption(f"Grupo {p['Grupo']}")
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                        with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        v_l = preds.get(str(p['ID']), {}).get('goles_local', 0); v_v = preds.get(str(p['ID']), {}).get('goles_visitante', 0)
                        gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed", disabled=bloqueado)
                        c3.markdown("<div style='padding-top:10px;'>:</div>", unsafe_allow_html=True)
                        gv = c4.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed", disabled=bloqueado)
                        with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
                
                col_b1, col_b2 = st.columns(2)
                if col_b1.form_submit_button(t["save_btn"], use_container_width=True, disabled=bloqueado):
                    for p in partidos_jornada: guardar_prediccion_supabase(st.session_state.user_email, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                    st.success("Guardado!"); st.balloons()
                
                if col_b2.form_submit_button(t["reset_btn"], use_container_width=True, disabled=bloqueado):
                    borrar_predicciones_jornada(st.session_state.user_email, [p['ID'] for p in partidos_jornada])
                    st.rerun()

            # --- MI TICKET (DESCARGA IMAGEN) ---
            st.divider()
            with st.expander(t["my_ticket"]):
                if st.button(t["gen_ticket"]):
                    img_data = generar_ticket_prode(username_display, perfil_actual['equipo_campeon'], perfil_actual['equipo_subcampeon'], perfil_actual['equipo_tercero'], perfil_actual['equipo_sorpresa'], perfil_actual['equipo_decepcion'])
                    st.image(img_data)
                    st.download_button(t["download_ticket"], data=img_data, file_name=f"ticket_{username_display}.png", mime="image/png")

    # --- 3. RESULTADOS (Mantenido 100%) ---
    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        stats = {}
        for p in partidos_data:
            if p['Grupo'] != "Definir":
                for eq_key, bnd_key, rnk_key in [('Local', 'Bandera_L', 'Rank_L'), ('Visitante', 'Bandera_V', 'Rank_V')]:
                    eq_name = p[f'{eq_key}_ES'] if lang == "Español" else p[f'{eq_key}_EN']
                    if eq_name and eq_name not in stats:
                        stats[eq_name] = {'Flag': p[bnd_key], 'Equipo': eq_name, 'PJ': 0, 'PTS': 0, 'DG': 0, 'GF': 0, 'GC': 0, 'FP': 0, 'Rank': p[rnk_key], 'Grupo': p['Grupo']}

        for p in [p for p in partidos_data if p['Goles Real L'] is not None and p['Grupo'] != "Definir"]:
            eq_l = p['Local_ES'] if lang == "Español" else p['Local_EN']; eq_v = p['Visitante_ES'] if lang == "Español" else p['Visitante_EN']
            gl, gv = p['Goles Real L'], p['Goles Real V']
            stats[eq_l]['PJ'] += 1; stats[eq_l]['GF'] += gl; stats[eq_l]['GC'] += gv; stats[eq_l]['DG'] += (gl - gv); stats[eq_l]['FP'] += p['FP_L']
            stats[eq_v]['PJ'] += 1; stats[eq_v]['GF'] += gv; stats[eq_v]['GC'] += gl; stats[eq_v]['DG'] += (gv - gl); stats[eq_v]['FP'] += p['FP_V']
            if gl > gv: stats[eq_l]['PTS'] += 3
            elif gl < gv: stats[eq_v]['PTS'] += 3
            else: stats[eq_l]['PTS'] += 1; stats[eq_v]['PTS'] += 1

        grupos = sorted(list(set([s['Grupo'] for s in stats.values()])))
        tablas_finales = {}
        for g in grupos:
            st.write(f"### GRUPO {g}")
            df_g = pd.DataFrame([s for s in stats.values() if s['Grupo'] == g]).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
            tablas_finales[g] = df_g
            st.data_editor(df_g[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, use_container_width=True)

        st.divider()
        st.subheader("🥉 Mejores Terceros")
        terceros = []
        for g in grupos:
            if len(tablas_finales[g]) >= 3: terceros.append(tablas_finales[g].iloc[2])
        if terceros:
            df_3 = pd.DataFrame(terceros).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
            def highlight_3(s): return ['background-color: rgba(46, 204, 113, 0.3)' if s.name < 8 else '' for _ in s]
            st.data_editor(df_3[['Flag', 'Equipo', 'Grupo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']].style.apply(highlight_3, axis=1), column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, use_container_width=True)

        st.divider()
        st.subheader("🏆 Knockout Stage / Fase de Eliminatorias")
        f_ko_sel = st.selectbox("Ver Fase:", ["16vos", "8vos", "4tos", "Semifinales", "Final y 3er Puesto"])
        col_izq, col_der = st.columns(2)
        if f_ko_sel == "16vos":
            with col_izq:
                for mid, e1, e2 in [("M74", "1E", "3ro"), ("M77", "1I", "3ro"), ("M73", "2A", "2B"), ("M75", "1F", "2C"), ("M83", "2K", "2L"), ("M84", "1H", "2J"), ("M81", "1D", "3ro"), ("M82", "1G", "3ro")]:
                    with st.container(border=True): st.caption(mid); st.markdown(f"**{e1}** vs **{e2}**")
            with col_der:
                for mid, e1, e2 in [("M76", "1C", "2F"), ("M78", "2E", "2I"), ("M79", "1A", "3ro"), ("M80", "1L", "3ro"), ("M86", "1J", "2H"), ("M88", "2D", "2G"), ("M85", "1B", "3ro"), ("M87", "1K", "3ro")]:
                    with st.container(border=True): st.caption(mid); st.markdown(f"**{e1}** vs **{e2}**")

    # --- 4. SIMULADOR (Mantenido 100%) ---
    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        if "sim_goles_dict" not in st.session_state: st.session_state.sim_goles_dict = {}
        if "sim_fp_dict" not in st.session_state: st.session_state.sim_fp_dict = {}

        c_r1, c_r2, _ = st.columns([1, 1, 2])
        with c_r1:
            if st.button("♻️ Borrar Todo"): st.session_state.sim_goles_dict = {}; st.session_state.sim_fp_dict = {}; st.session_state.sim_fp_override = True; st.session_state.generar_cuadro = False; st.rerun()
        with c_r2:
            if st.button("🏟️ Cargar Realidad"):
                for p in partidos_data:
                    if p['Goles Real L'] is not None: st.session_state.sim_goles_dict[f"sl_{p['ID']}"] = p['Goles Real L']; st.session_state.sim_goles_dict[f"sv_{p['ID']}"] = p['Goles Real V']
                st.session_state.sim_fp_override = False; st.rerun()

        st.divider()
        grupos_disponibles = sorted(list(set([p['Grupo'] for p in partidos_data if len(p['Grupo']) == 1 and p['Grupo'] != "Definir"])))
        
        equipos_info = {}
        for p in partidos_data:
            for k, b in [('Local', 'Bandera_L'), ('Visitante', 'Bandera_V')]:
                es = p[f'{k}_ES']; en = p[f'{k}_EN']
                if es: equipos_info[es] = {"flag": p[b]}; equipos_info[en] = {"flag": p[b]}

        s_dict = {}
        for p in partidos_data:
            if p['Grupo'] == "Definir": continue
            for k, b, r, f in [('Local', 'Bandera_L', 'Rank_L', 'FP_L'), ('Visitante', 'Bandera_V', 'Rank_V', 'FP_V')]:
                eq = p[f'{k}_ES' if lang=="Español" else f'{k}_EN']
                if eq and eq not in s_dict: s_dict[eq] = {'Flag': p[b], 'Equipo': eq, 'Grupo': p['Grupo'], 'PJ': 0, 'PTS': 0, 'DG': 0, 'GF': 0, 'GC': 0, 'Rank': p[r], 'FP_Base': p[f], 'H2H_Matches': []}

        for p in partidos_data:
            if p['Grupo'] == "Definir": continue
            eq_l = p['Local_ES' if lang=="Español" else 'Local_EN']; eq_v = p['Visitante_ES' if lang=="Español" else 'Visitante_EN']
            gl = st.session_state.sim_goles_dict.get(f"sl_{p['ID']}"); gv = st.session_state.sim_goles_dict.get(f"sv_{p['ID']}")
            if gl is not None and gv is not None:
                s_dict[eq_l]['PJ'] += 1; s_dict[eq_v]['PJ'] += 1; s_dict[eq_l]['GF'] += gl; s_dict[eq_v]['GF'] += gv; s_dict[eq_l]['GC'] += gv; s_dict[eq_v]['GC'] += gl; s_dict[eq_l]['DG'] += (gl - gv); s_dict[eq_v]['DG'] += (gv - gl)
                pl = 3 if gl > gv else (1 if gl == gv else 0); pv = 3 if gv > gl else (1 if gl == gv else 0)
                s_dict[eq_l]['PTS'] += pl; s_dict[eq_v]['PTS'] += pv; s_dict[eq_l]['H2H_Matches'].append({'rival': eq_v, 'gf': gl, 'gc': gv, 'pts': pl}); s_dict[eq_v]['H2H_Matches'].append({'rival': eq_l, 'gf': gv, 'gc': gl, 'pts': pv})

        for eq in s_dict:
            base_fp = 0 if st.session_state.get('sim_fp_override', False) else s_dict[eq]['FP_Base']
            s_dict[eq]['FP'] = base_fp + st.session_state.sim_fp_dict.get(eq, 0)

        def fifa_sort_key(e):
            emp = [x for x in s_dict.values() if x['Grupo'] == e['Grupo'] and x['PTS'] == e['PTS']]
            h_p, h_d, h_g = 0, 0, 0
            if len(emp) > 1:
                noms = [x['Equipo'] for x in emp]; h_m = [m for m in e['H2H_Matches'] if m['rival'] in noms]
                h_p = sum(m['pts'] for m in h_m); h_d = sum(m['gf']-m['gc'] for m in h_m); h_g = sum(m['gf'] for m in h_m)
            return (-e['PTS'], -h_p, -h_d, -h_g, -e['DG'], -e['GF'], -e['FP'], e['Rank'])

        df_global = pd.DataFrame(sorted(s_dict.values(), key=fifa_sort_key))
        idx_g = grupos_disponibles.index(st.session_state.get("sim_grupo_sel", "A")) if st.session_state.get("sim_grupo_sel") in grupos_disponibles else 0
        g_sel = st.radio("Enfocar Grupo:", grupos_disponibles, horizontal=True, index=idx_g)
        st.session_state.sim_grupo_sel = g_sel

        col_iz, col_de = st.columns([1.1, 1], gap="medium")
        with col_iz:
            st.markdown(f"### ⚽ Partidos Grupo {g_sel}")
            with st.form(f"f_sim_{g_sel}"):
                for p in [p for p in partidos_data if p['Grupo'] == g_sel]:
                    with st.container(border=True):
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                        with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        v_l = st.session_state.sim_goles_dict.get(f"sl_{p['ID']}"); v_v = st.session_state.sim_goles_dict.get(f"sv_{p['ID']}")
                        nl = c2.number_input("L", 0, 20, v_l if v_l is not None else 0, key=f"tmp_l_{p['ID']}", label_visibility="collapsed")
                        c3.write(":"); nv = c4.number_input("V", 0, 20, v_v if v_v is not None else 0, key=f"tmp_v_{p['ID']}", label_visibility="collapsed")
                        with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
                
                st.write("🚩 **Ajuste de Fair Play**")
                eqs_n = sorted(list(set([p['Local_ES' if lang=="Español" else 'Local_EN'] for p in [p for p in partidos_data if p['Grupo']==g_sel]])))
                cols_fp = st.columns(4)
                for i, eq_n in enumerate(eqs_n):
                    with cols_fp[i % 4]:
                        st.markdown(f"<small>{eq_n}</small>", unsafe_allow_html=True)
                        st.number_input("FP", -99, 0, st.session_state.sim_fp_dict.get(eq_n, 0), key=f"tmp_fp_{eq_n}", label_visibility="collapsed")
                
                if st.form_submit_button("⚽ Simular Grupo!", use_container_width=True):
                    for p in [p for p in partidos_data if p['Grupo']==g_sel]:
                        st.session_state.sim_goles_dict[f"sl_{p['ID']}"] = st.session_state[f"tmp_l_{p['ID']}"]; st.session_state.sim_goles_dict[f"sv_{p['ID']}"] = st.session_state[f"tmp_v_{p['ID']}"]
                    for eq_n in eqs_n: st.session_state.sim_fp_dict[eq_n] = st.session_state[f"tmp_fp_{eq_n}"]
                    st.rerun()

        with col_de:
            st.markdown(f"### 📊 Posiciones Grupo {g_sel}")
            st.data_editor(df_global[df_global['Grupo'] == g_sel][['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, use_container_width=True, disabled=True)
            st.markdown("### 🥉 Mejores Terceros")
            ters = []
            for g in grupos_disponibles:
                dg = df_global[df_global['Grupo'] == g]
                if len(dg) >= 3: ters.append(dg.iloc[2])
            if ters:
                df_3s = pd.DataFrame(ters).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
                st.data_editor(df_3s[['Flag', 'Equipo', 'Grupo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']].style.apply(lambda s: ['background-color: rgba(46, 204, 113, 0.3)' if s.name < 8 else '' for _ in s], axis=1), column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, use_container_width=True, disabled=True)

        st.divider()
        if st.button("🏆 Generar Cuadro Final", type="primary", use_container_width=True): st.session_state.generar_cuadro = True; st.rerun()

        if st.session_state.get("generar_cuadro", False):
            r_g = {}
            for g in grupos_disponibles:
                dg = df_global[df_global['Grupo'] == g]
                r_g[f"1{g}"] = dg.iloc[0]['Equipo'] if len(dg) >= 1 else f"1{g}"; r_g[f"2{g}"] = dg.iloc[1]['Equipo'] if len(dg) >= 2 else f"2{g}"
            
            if len(ters) >= 8:
                top8 = df_3s.head(8); asig = asignar_terceros(top8['Grupo'].tolist())
                if asig:
                    td = {g: eq for g, eq in zip(top8['Grupo'].tolist(), top8['Equipo'].tolist())}
                    for r, m in [('R1','M79_3'),('R2','M85_3'),('R3','M81_3'),('R4','M74_3'),('R5','M82_3'),('R6','M77_3'),('R7','M87_3'),('R8','M80_3')]: r_g[m] = td[asig[r]]

            def render_ko(mid, tl, tv):
                with st.container(border=True):
                    st.caption(mid); c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    fl = equipos_info.get(tl, {}).get('flag', ''); fv = equipos_info.get(tv, {}).get('flag', '')
                    with c1: st.markdown(render_equipo(tl, tl, fl, lang), unsafe_allow_html=True)
                    gl = st.session_state.get(f"sk_gl_{mid}"); gv = st.session_state.get(f"sk_gv_{mid}")
                    ngl = c2.number_input("L", 0, 20, gl if gl is not None else 0, key=f"i_gl_{mid}", label_visibility="collapsed")
                    c3.write(":"); ngv = c4.number_input("V", 0, 20, gv if gv is not None else 0, key=f"i_gv_{mid}", label_visibility="collapsed")
                    st.session_state[f"sk_gl_{mid}"], st.session_state[f"sk_gv_{mid}"] = ngl, ngv
                    with c5: st.markdown(render_equipo(tv, tv, fv, lang, align="right"), unsafe_allow_html=True)
                    w, l = f"W{mid[1:]}", f"L{mid[1:]}"
                    if ngl > ngv: w, l = tl, tv
                    elif ngv > ngl: w, l = tv, tl
                    else:
                        st.markdown("<small>Penales</small>", unsafe_allow_html=True); cp1, cp2, cp3, cp4, cp5 = st.columns([3, 1, 0.5, 1, 3])
                        pl = st.session_state.get(f"sk_pl_{mid}"); pv = st.session_state.get(f"sk_pv_{mid}")
                        npl = cp2.number_input("PL", 0, 30, pl if pl is not None else 0, key=f"i_pl_{mid}", label_visibility="collapsed")
                        cp3.write(":"); npv = cp4.number_input("PV", 0, 30, pv if pv is not None else 0, key=f"i_pv_{mid}", label_visibility="collapsed")
                        st.session_state[f"sk_pl_{mid}"], st.session_state[f"sk_pv_{mid}"] = npl, npv
                        if npl > npv: w, l = tl, tv
                        elif npv > npl: w, l = tv, tl
                return w, l

            with st.expander("🏆 Jugar Play-Offs Simulados", expanded=True):
                t1, t2, t3, t4, t5 = st.tabs(["16vos", "8vos", "4tos", "Semis", "Final"])
                kw = {}
                with t1:
                    ci, cd = st.columns(2)
                    with ci: kw["M74"],_ = render_ko("M74", r_g.get("1E","1E"), r_g.get("M74_3","3ro")); kw["M77"],_ = render_ko("M77", r_g.get("1I","1I"), r_g.get("M77_3","3ro")); kw["M73"],_ = render_ko("M73", r_g.get("2A","2A"), r_g.get("2B","2B")); kw["M75"],_ = render_ko("M75", r_g.get("1F","1F"), r_g.get("2C","2C")); kw["M83"],_ = render_ko("M83", r_g.get("2K","2K"), r_g.get("2L","2L")); kw["M84"],_ = render_ko("M84", r_g.get("1H","1H"), r_g.get("2J","2J")); kw["M81"],_ = render_ko("M81", r_g.get("1D","1D"), r_g.get("M81_3","3ro")); kw["M82"],_ = render_ko("M82", r_g.get("1G","1G"), r_g.get("M82_3","3ro"))
                    with cd: kw["M76"],_ = render_ko("M76", r_g.get("1C","1C"), r_g.get("2F","2F")); kw["M78"],_ = render_ko("M78", r_g.get("2E","2E"), r_g.get("2I","2I")); kw["M79"],_ = render_ko("M79", r_g.get("1A","1A"), r_g.get("M79_3","3ro")); kw["M80"],_ = render_ko("M80", r_g.get("1L","1L"), r_g.get("M80_3","3ro")); kw["M86"],_ = render_ko("M86", r_g.get("1J","1J"), r_g.get("2H","2H")); kw["M88"],_ = render_ko("M88", r_g.get("2D","2D"), r_g.get("2G","2G")); kw["M85"],_ = render_ko("M85", r_g.get("1B","1B"), r_g.get("M85_3","3ro")); kw["M87"],_ = render_ko("M87", r_g.get("1K","1K"), r_g.get("M87_3","3ro"))
                with t2:
                    ci, cd = st.columns(2)
                    with ci: kw["M89"],_ = render_ko("M89", kw["M74"], kw["M77"]); kw["M90"],_ = render_ko("M90", kw["M73"], kw["M75"]); kw["M93"],_ = render_ko("M93", kw["M83"], kw["M84"]); kw["M94"],_ = render_ko("M94", kw["M81"], kw["M82"])
                    with cd: kw["M91"],_ = render_ko("M91", kw["M76"], kw["M78"]); kw["M92"],_ = render_ko("M92", kw["M79"], kw["M80"]); kw["M95"],_ = render_ko("M95", kw["M86"], kw["M88"]); kw["M96"],_ = render_ko("M96", kw["M85"], kw["M87"])
                with t3:
                    ci, cd = st.columns(2)
                    with ci: kw["M97"],_ = render_ko("M97", kw["M89"], kw["M90"]); kw["M98"],_ = render_ko("M98", kw["M93"], kw["M94"])
                    with cd: kw["M99"],_ = render_ko("M99", kw["M91"], kw["M92"]); kw["M100"],_ = render_ko("M100", kw["M95"], kw["M96"])
                with t4:
                    ci, cd = st.columns(2)
                    with ci: kw["M101"], l101 = render_ko("M101", kw["M97"], kw["M98"])
                    with cd: kw["M102"], l102 = render_ko("M102", kw["M99"], kw["M100"])
                with t5:
                    ci, cd = st.columns(2)
                    with ci: st.write("#### 🥉 3er Puesto"); render_ko("M103", l101, l102)
                    with cd: st.write("#### 🏆 Final"); render_ko("M104", kw["M101"], kw["M102"])

    # --- 5. SEDES Y EQUIPOS (Próximamente) ---
    elif menu == t["nav_stadiums"]:
        st.subheader(t["nav_stadiums"]); st.info("Próximamente / Coming Soon")

else:
    st.title("⚽ World Cup 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button("Login with Google", auth_url, type="primary")

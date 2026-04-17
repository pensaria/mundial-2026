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

# --- 1. NUEVAS FUNCIONES DE DATOS OPTIMIZADAS ---

@st.cache_data(ttl=600)  # Caché de 10 minutos para no saturar Airtable
def obtener_datos_base():
    """Trae partidos y equipos una sola vez y los organiza en memoria."""
    headers = {"Authorization": f"Bearer {st.secrets['airtable']['api_key']}"}
    base_url = f"https://api.airtable.com/v0/{st.secrets['airtable']['base_id']}"
    
    # Traer Partidos
    r_partidos = requests.get(f"{base_url}/Partidos", headers=headers, params={"sort[0][field]": "ID Partido"}).json()
    
    partidos = []
    for record in r_partidos.get('records', []):
        f = record['fields']
        # Limpieza de datos de Airtable (Manejo de listas de búsqueda)
        def get_val(campo, es_lista=True):
            val = f.get(campo)
            return val[0] if es_lista and isinstance(val, list) and val else (val if val else None)

        partidos.append({
            "ID": f.get("ID Partido"),
            "Grupo": get_val("Grupo"),
            "Local_ES": get_val("Nombre (from Equipo Local)"),
            "Local_EN": get_val("Nombre EN (from Equipo Local)"),
            "Visitante_ES": get_val("Nombre (from Equipo Visitante)"),
            "Visitante_EN": get_val("Nombre EN (from Equipo Visitante)"),
            "Bandera_L": f.get("Bandera L")[0].get("url") if f.get("Bandera L") else "",
            "Bandera_V": f.get("Bandera V")[0].get("url") if f.get("Bandera V") else "",
            "Rank_L": get_val("Ranking FIFA (from Equipo Local)") or 100,
            "Rank_V": get_val("Ranking FIFA (from Equipo Visitante)") or 100,
            "Goles Real L": f.get("Goles Local"),
            "Goles Real V": f.get("Goles Visitante"),
            "FP_L": f.get("Fair Play L", 0),
            "FP_V": f.get("Fair Play V", 0),
            "Fecha_Hora": f.get("Fecha y Hora"),
            "Jornada": f.get("Jornada")
        })
    return partidos

def obtener_predicciones_usuario(user):
    res = supabase.table("predicciones").select("*").eq("usuario", user).execute()
    return {r['partido_id']: r for r in res.data}

def guardar_prediccion_supabase(user, partido_id, gl, gv):
    supabase.table("predicciones").upsert({
        "usuario": user, 
        "partido_id": str(partido_id), 
        "goles_local": gl, 
        "goles_visitante": gv
    }, on_conflict="usuario, partido_id").execute()

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

# --- 2. LÓGICA DE CÁLCULO DEL MUNDIAL (SIMULADOR) ---

def calcular_posiciones(partidos_lista, goles_sim, fp_sim):
    stats = {}
    for p in partidos_lista:
        pid = p['ID']
        gl = goles_sim.get(f"sl_{pid}", 0)
        gv = goles_sim.get(f"sv_{pid}", 0)
        
        # Equipos y sus datos
        for eq, gf, gc, rnk, bnd, grp, fp_base in [
            (p['Local_ES'], gl, gv, p['Rank_L'], p['Bandera_L'], p['Grupo'], p['FP_L']),
            (p['Visitante_ES'], gv, gl, p['Rank_V'], p['Bandera_V'], p['Grupo'], p['FP_V'])
        ]:
            if not eq: continue
            if eq not in stats:
                stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PTS':0, 'DG':0, 'GF':0, 'Rank': rnk, 'Grupo': grp, 'FP': fp_base}
            
            stats[eq]['GF'] += gf
            stats[eq]['DG'] += (gf - gc)
            stats[eq]['FP'] += fp_sim.get(eq, 0)
            if gf > gc: stats[eq]['PTS'] += 3
            elif gf == gc: stats[eq]['PTS'] += 1

    # Ordenar por criterios FIFA: Pts, DG, GF, FP, Rank
    df = pd.DataFrame(stats.values())
    if not df.empty:
        df = df.sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
    return df

# --- INICIO DE LA APP ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True

if st.session_state.connected:
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    
    # Carga de datos optimizada
    partidos_data = obtener_datos_base()
    
    menu = st.sidebar.radio("Menu", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    
    if st.sidebar.button(t["logout"]): st.session_state.connected = False; st.rerun()

    st.title(t["title"])

    # --- 1. INICIO ---
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
            else:
                st.success(t["no_matches"])

    # --- 2. JUGAR ---
    elif menu == t["nav_play"]:
        st.subheader(t["nav_play"])
        email_user = "usuario_prueba@gmail.com"
        preds = obtener_predicciones_usuario(email_user)
        jornadas = sorted(list(set([p['Jornada'] for p in partidos_data if p['Jornada']])))
        j_sel = st.selectbox("Jornada:", jornadas)
        with st.form("f_prode"):
            partidos_jornada = [p for p in partidos_data if p['Jornada'] == j_sel]
            partidos_ordenados = sorted(partidos_jornada, key=lambda x: x['Grupo'] if x['Grupo'] else "")
            for p in partidos_ordenados:
                with st.container(border=True):
                    st.caption(f"Grupo {p['Grupo']}")
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    v_l = preds.get(str(p['ID']), {}).get('goles_local', 0)
                    v_v = preds.get(str(p['ID']), {}).get('goles_visitante', 0)
                    gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed")
                    c3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                    gv = c4.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed")
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
            if st.form_submit_button(t["save_btn"], use_container_width=True):
                for p in partidos_jornada:
                    guardar_prediccion_supabase(email_user, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                st.success("Guardado!"); st.balloons()

    # --- 3. RESULTADOS ---
    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        # Usamos la nueva lógica de cálculo centralizada
        goles_real_dict = {f"sl_{p['ID']}": p['Goles Real L'] if p['Goles Real L'] is not None else 0 for p in partidos_data}
        goles_real_dict.update({f"sv_{p['ID']}": p['Goles Real V'] if p['Goles Real V'] is not None else 0 for p in partidos_data})
        
        df_total = calcular_posiciones(partidos_data, goles_real_dict, {})
        
        grupos = sorted(df_total['Grupo'].unique()) if not df_total.empty else []
        for g in grupos:
            if len(g) > 1: continue # Saltamos fases eliminatorias por ahora
            st.write(f"### GRUPO {g}")
            df_g = df_total[df_total['Grupo'] == g]
            st.data_editor(df_g[['Flag', 'Equipo', 'PTS', 'DG', 'GF']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, disabled=True, key=f"res_{g}", use_container_width=True)

    # --- 4. SIMULADOR (OPTIMIZADO) ---
    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        
        # Inicializar estados de simulación
        if "sim_goles" not in st.session_state: st.session_state.sim_goles = {}
        if "sim_fp" not in st.session_state: st.session_state.sim_fp = {}

        # Botonera
        c_r1, c_r2, c_r3 = st.columns(3)
        with c_r1:
            if st.button("♻️ Borrar Todo", use_container_width=True):
                st.session_state.sim_goles = {}; st.session_state.sim_fp = {}; st.rerun()
        with c_r2:
            if st.button("🏟️ Realidad", use_container_width=True):
                for p in partidos_data:
                    st.session_state.sim_goles[f"sl_{p['ID']}"] = p['Goles Real L'] or 0
                    st.session_state.sim_goles[f"sv_{p['ID']}"] = p['Goles Real V'] or 0
                st.rerun()

        st.divider()
        grupos_sim = sorted(list(set([p['Grupo'] for p in partidos_data if p['Grupo'] and len(p['Grupo'])==1])))
        g_sel = st.radio("Simular Grupo:", grupos_sim, horizontal=True)

        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.write(f"#### Partidos Grupo {g_sel}")
            for p in [p for p in partidos_data if p['Grupo'] == g_sel]:
                with st.container(border=True):
                    c_a, c_b, c_c, c_d, c_e = st.columns([3, 1, 0.5, 1, 3])
                    with c_a: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    
                    # Usamos el diccionario de sesión para evitar lags
                    val_l = st.session_state.sim_goles.get(f"sl_{p['ID']}", 0)
                    val_v = st.session_state.sim_goles.get(f"sv_{p['ID']}", 0)
                    
                    new_l = c_b.number_input("L", 0, 20, val_l, key=f"sim_in_l_{p['ID']}", label_visibility="collapsed")
                    c_c.write(":")
                    new_v = c_d.number_input("V", 0, 20, val_v, key=f"sim_in_v_{p['ID']}", label_visibility="collapsed")
                    
                    st.session_state.sim_goles[f"sl_{p['ID']}"] = new_l
                    st.session_state.sim_goles[f"sv_{p['ID']}"] = new_v
                    
                    with c_e: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)

        with col2:
            st.write(f"#### Posiciones Grupo {g_sel}")
            df_res = calcular_posiciones(partidos_data, st.session_state.sim_goles, st.session_state.sim_fp)
            if not df_res.empty:
                df_g = df_res[df_res['Grupo'] == g_sel]
                st.dataframe(df_g[['Flag', 'Equipo', 'PTS', 'DG', 'GF', 'FP']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, use_container_width=True)
                
                # SECCIÓN MEJORES TERCEROS (AUTOMÁTICA)
                st.write("#### 🥉 Ranking de Terceros")
                terceros = []
                for grp in grupos_sim:
                    df_aux = df_res[df_res['Grupo'] == grp]
                    if len(df_aux) >= 3: terceros.append(df_aux.iloc[2])
                
                if terceros:
                    df_3 = pd.DataFrame(terceros).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
                    # Resaltar los 8 que pasan
                    st.dataframe(df_3[['Flag', 'Equipo', 'Grupo', 'PTS', 'DG']], column_config={"Flag": st.column_config.ImageColumn(" ")}, hide_index=True, use_container_width=True)

    else: st.info("Próximamente")

else:
    st.title("⚽ World Cup 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button("Login with Google", auth_url, type="primary")

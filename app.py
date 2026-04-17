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

    # --- 2. JUGAR (CON TIEMPO LÍMITE Y ORDEN) ---
    elif menu == t["nav_play"]:
        st.subheader(t["nav_play"])
        email_user = "usuario_prueba@gmail.com" # Aquí luego irá el email real de Google
        preds = obtener_predicciones_usuario(email_user)
        
        # Ordenar jornadas (Fase de grupos -> 16vos -> ... -> Final)
        orden_jornadas = ["Jornada 1", "Jornada 2", "Jornada 3", "16vos de final", "8vos de final", "4tos de final", "Semifinal", "3er puesto", "Final"]
        jornadas_existentes = list(set([p['Jornada'] for p in partidos_data if p['Jornada']]))
        jornadas = sorted(jornadas_existentes, key=lambda x: orden_jornadas.index(x) if x in orden_jornadas else 99)
        
        j_sel = st.selectbox("Jornada:", jornadas)
        
        zona_sofia = ZoneInfo("Europe/Sofia")
        ahora = datetime.now(zona_sofia)

        with st.form("f_prode"):
            partidos_jornada = sorted([p for p in partidos_data if p['Jornada'] == j_sel], key=lambda x: x['ID'])
            
            for p in partidos_jornada:
                # Lógica de tiempo límite (6 horas antes)
                f_partido = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                limite = f_partido - timedelta(hours=6)
                bloqueado = ahora > limite

                with st.container(border=True):
                    col_info, col_juego = st.columns([1, 4])
                    col_info.caption(f"ID: {p['ID']} | Grupo {p['Grupo']}")
                    if bloqueado: col_info.error("🔒 Cerrado")
                    else: col_info.info(f"⏳ {limite.strftime('%H:%M')}")

                    c1, c2, c3, c4, c5 = col_juego.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    
                    v_l = preds.get(str(p['ID']), {}).get('goles_local', 0)
                    v_v = preds.get(str(p['ID']), {}).get('goles_visitante', 0)
                    
                    gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed", disabled=bloqueado)
                    c3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                    gv = c4.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed", disabled=bloqueado)
                    
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)

            if st.form_submit_button(t["save_btn"], use_container_width=True):
                for p in partidos_jornada:
                    # Solo guardar si no está bloqueado
                    f_p = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                    if ahora <= (f_p - timedelta(hours=6)):
                        guardar_prediccion_supabase(email_user, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                st.success("Pronósticos actualizados"); st.rerun()

    # --- 4. SIMULADOR (GRUPOS + FP INTEGRADO) ---
    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        if "sim_goles" not in st.session_state: st.session_state.sim_goles = {}
        if "sim_fp" not in st.session_state: st.session_state.sim_fp = {}

        # Controles superiores
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button("♻️ Reiniciar Simulación"): st.session_state.sim_goles = {}; st.session_state.sim_fp = {}; st.rerun()
        with c2:
            if st.button("💾 Guardar Simulación"): 
                # Aquí podrías guardar st.session_state.sim_goles en una nueva tabla de Supabase llamada 'simulaciones'
                st.toast("Simulación guardada localmente")

        grupos_lista = sorted(list(set([p['Grupo'] for p in partidos_data if p['Grupo'] and len(p['Grupo'])==1])))
        g_sel = st.radio("Enfocar Grupo:", grupos_lista, horizontal=True)

        # Cálculo global (necesario para mejores terceros)
        df_global = calcular_posiciones(partidos_data, st.session_state.sim_goles, st.session_state.sim_fp)

        col_input, col_table = st.columns([1.2, 1])

        with col_input:
            st.markdown(f"### ⚽ Partidos & Fair Play - Grupo {g_sel}")
            partidos_g = [p for p in partidos_data if p['Grupo'] == g_sel]
            
            # 1. Inputs de Goles del Grupo
            for p in partidos_g:
                with st.container(border=True):
                    ca, cb, cc, cd, ce = st.columns([3, 1, 0.5, 1, 3])
                    with ca: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    st.session_state.sim_goles[f"sl_{p['ID']}"] = cb.number_input("L", 0, 20, st.session_state.sim_goles.get(f"sl_{p['ID']}", 0), key=f"s_l_{p['ID']}", label_visibility="collapsed")
                    cc.write(":")
                    st.session_state.sim_goles[f"sv_{p['ID']}"] = cd.number_input("V", 0, 20, st.session_state.sim_goles.get(f"sv_{p['ID']}", 0), key=f"s_v_{p['ID']}", label_visibility="collapsed")
                    with ce: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
            
            # 2. Inputs de Fair Play (Integrados abajo de los partidos del grupo)
            st.write("🚩 **Ajuste de Fair Play (Tarjetas)**")
            equipos_g = df_global[df_global['Grupo'] == g_sel]['Equipo'].tolist()
            cols_fp = st.columns(len(equipos_g))
            for i, eq_name in enumerate(equipos_g):
                with cols_fp[i]:
                    band = df_global[df_global['Equipo'] == eq_name]['Flag'].values[0]
                    st.image(band, width=20)
                    st.session_state.sim_fp[eq_name] = st.number_input(f"FP {eq_name}", -20, 0, st.session_state.sim_fp.get(eq_name, 0), key=f"fp_{eq_name}", label_visibility="collapsed")

        with col_table:
            st.markdown(f"### 📊 Posiciones Grupo {g_sel}")
            st.dataframe(df_global[df_global['Grupo'] == g_sel][['Flag', 'Equipo', 'PTS', 'DG', 'GF', 'FP']], 
                         column_config={"Flag": st.column_config.ImageColumn("")}, hide_index=True, use_container_width=True)
            
            st.markdown("### 🥉 Ranking Mejores Terceros")
            terceros = []
            for g in grupos_lista:
                df_g = df_global[df_global['Grupo'] == g]
                if len(df_g) >= 3: terceros.append(df_g.iloc[2])
            
            if terceros:
                df_3 = pd.DataFrame(terceros).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
                # Resaltar en verde los 8 clasificados
                def style_3(s): return ['background-color: #2ecc7133' if s.name < 8 else '' for _ in s]
                st.dataframe(df_3[['Flag', 'Equipo', 'Grupo', 'PTS', 'DG']].style.apply(style_3, axis=1), 
                             column_config={"Flag": st.column_config.ImageColumn("")}, hide_index=True, use_container_width=True)

        # --- SECCIÓN DE CRUCES (A la espera de tu tabla de la FIFA) ---
        st.divider()
        st.subheader("🏁 Cuadro de Eliminatorias Simuladas")
        st.info("Envía la tabla de combinaciones de la FIFA para activar los cruces automáticos de 16vos.")
        
        # Mostrar resumen de otros grupos pequeño abajo
        with st.expander("Ver otros grupos"):
            cols = st.columns(3)
            for i, g in enumerate([grp for grp in grupos_lista if grp != g_sel]):
                with cols[i % 3]:
                    st.caption(f"Grupo {g}")
                    st.dataframe(df_global[df_global['Grupo'] == g][['Equipo', 'PTS']], hide_index=True, use_container_width=True)

    else: st.info("Próximamente")

else:
    st.title("⚽ World Cup 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button("Login with Google", auth_url, type="primary")

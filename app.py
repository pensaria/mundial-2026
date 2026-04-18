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
    if not nombre: nombre = "TBD"
    # Bandera por defecto si no hay url
    if not url_bandera: url_bandera = "https://flagcdn.com/w80/un.png"
    
    flex = "row" if align == "left" else "row-reverse"
    # CSS para forzar tamaño estandarizado 30x20px
    return f'''
    <div style="display: flex; align-items: center; flex-direction: {flex}; gap: 10px; min-width: 150px;">
        <div style="width: 30px; height: 20px; flex-shrink: 0; overflow: hidden; border-radius: 2px; border: 1px solid #eee;">
            <img src="{url_bandera}" style="width: 100%; height: 100%; object-fit: cover;">
        </div>
        <span style="white-space: nowrap; font-weight: 500;">{nombre}</span>
    </div>
    '''
# --- 2. LÓGICA DE CÁLCULO MEJORADA (CRITERIOS FIFA) ---

def calcular_posiciones(partidos_lista, goles_sim, fp_sim):
    stats = {}
    for p in partidos_lista:
        pid = str(p['ID'])
        # Obtenemos goles de la simulación o de la realidad si no hay simulación
        gl = goles_sim.get(f"sl_{pid}", 0)
        gv = goles_sim.get(f"sv_{pid}", 0)
        
        for eq, gf, gc, rnk, bnd, grp, fp_base in [
            (p['Local_ES'], gl, gv, p['Rank_L'], p['Bandera_L'], p['Grupo'], p['FP_L']),
            (p['Visitante_ES'], gv, gl, p['Rank_V'], p['Bandera_V'], p['Grupo'], p['FP_V'])
        ]:
            if not eq: continue
            if eq not in stats:
                # El FP total es: Base de Airtable + Lo que el usuario sume/reste en el simulador
                stats[eq] = {'Flag': bnd, 'Equipo': eq, 'PTS':0, 'DG':0, 'GF':0, 'Rank': rnk, 'Grupo': grp, 'FP_Base': fp_base}
            
            stats[eq]['GF'] += gf
            stats[eq]['DG'] += (gf - gc)
            if gf > gc: stats[eq]['PTS'] += 3
            elif gf == gc: stats[eq]['PTS'] += 1

    # Crear DataFrame y calcular FP Final
    df = pd.DataFrame(stats.values())
    if not df.empty:
        # Sumamos el ajuste manual del simulador al valor base
        df['FP'] = df.apply(lambda x: x['FP_Base'] + fp_sim.get(x['Equipo'], 0), axis=1)
        # ORDEN FIFA: 1. Puntos, 2. DG, 3. Goles Favor, 4. Fair Play, 5. Ranking FIFA
        df = df.sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
    return df

# --- SECCIONES DE LA APP ---
if "connected" not in st.session_state: st.session_state.connected = False
if "code" in st.query_params: st.session_state.connected = True

if st.session_state.connected:
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    partidos_data = obtener_datos_base()
    menu = st.sidebar.radio("Menu", [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    
    if st.sidebar.button(t["logout"]): st.session_state.connected = False; st.rerun()

    st.title(t["title"])

    # --- 1. INICIO ---
    if menu == t["nav_home"]:
        # A2.b.1: Selector de Modo
        modo_juego = st.sidebar.radio("🎮 Modo de Juego", ["Prode Simple", "Magic Mister"])
        
        if modo_juego == "Prode Simple":
            col_rank, col_next = st.columns([1, 1.2], gap="large")
            
            with col_rank:
                st.subheader(t["ranking_title"])
                # A2.b.3: Ranking (Calculado comparando Supabase vs Airtable Real)
                ranking = obtener_ranking_global(partidos_data)
                if ranking:
                    st.table(pd.DataFrame(ranking))
                else:
                    st.info("Aún no hay puntos procesados.")

            with col_next:
                st.subheader(t["next_matches"])
                zona_sofia = ZoneInfo("Europe/Sofia")
                ahora = datetime.now(zona_sofia)
                
                # Filtramos: que tengan fecha, que sean futuros y que ya tengan equipos definidos
                proximos = []
                for p in partidos_data:
                    # Validamos que Local_ES no sea None para evitar partidos TBD de eliminación
                    if p.get('Fecha_Hora') and p.get('Local_ES'): 
                        try:
                            f_dt = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                            if f_dt > ahora:
                                proximos.append((f_dt, p))
                        except:
                            continue
                
                # Ordenamos cronológicamente por la fecha real
                proximos.sort(key=lambda x: x[0])
                
                if proximos:
                    for f_dt, p in proximos[:5]:
                        with st.container(border=True):
                            st.caption(f"🆔 {p['ID']} | 📅 {f_dt.strftime('%d/%m - %H:%M')} hs")
                            c1, c2, c3 = st.columns([2, 0.5, 2])
                            with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                            c2.markdown("<div style='text-align:center; margin-top:10px;'>VS</div>", unsafe_allow_html=True)
                            with c3: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
                else:
                    st.success(t["no_matches"])
        else:
            st.warning("🚀 **Magic Mister** estará disponible próximamente. ¡Prepara tu equipo de 11!")

    # --- 2. JUGAR (CON TIEMPO LÍMITE) ---
    elif menu == t["nav_play"]:
        st.subheader(t["nav_play"])
        email_user = "usuario_prueba@gmail.com" # Aquí luego irá el email real de Google
        
        # 1. Definición de Control de Jornadas (Sofia GMT+3)
        zona_sofia = ZoneInfo("Europe/Sofia")
        ahora = datetime.now(zona_sofia)
        
        controles = {
            "🏆 Apuestas Especiales": {
                "abre": datetime(2024, 1, 1, tzinfo=zona_sofia), # Siempre abierta
                "cierra": datetime(2026, 6, 11, 17, 0, tzinfo=zona_sofia),
                "msg_antes": ""
            },
            "Jornada 1": {
                "abre": datetime(2024, 1, 1, tzinfo=zona_sofia),
                "cierra": datetime(2026, 6, 11, 17, 0, tzinfo=zona_sofia),
                "msg_antes": ""
            },
            "Jornada 2": {
                "abre": datetime(2024, 1, 1, tzinfo=zona_sofia),
                "cierra": datetime(2026, 6, 18, 14, 0, tzinfo=zona_sofia),
                "msg_antes": ""
            },
            "Jornada 3": {
                "abre": datetime(2024, 1, 1, tzinfo=zona_sofia),
                "cierra": datetime(2026, 6, 24, 17, 0, tzinfo=zona_sofia),
                "msg_antes": ""
            },
            "16vos de final": {
                "abre": datetime(2026, 6, 28, 8, 0, tzinfo=zona_sofia),
                "cierra": datetime(2026, 6, 28, 17, 0, tzinfo=zona_sofia),
                "msg_antes": "Los equipos se están definiendo tras la Fecha 3. Vuelve el 28/6/2026 a las 08:00 hs para apostar."
            }
            # ... Agregar las demás según tus horarios
        }

        jornadas_disponibles = ["🏆 Apuestas Especiales"] + sorted(list(set([p['Jornada'] for p in partidos_data if p['Jornada']])), key=lambda x: orden_j.index(x) if x in orden_j else 99)
        j_sel = st.selectbox("Selecciona tu Apuesta:", jornadas_disponibles)
        
        info_j = controles.get(j_sel, {"abre": ahora, "cierra": ahora + timedelta(days=1), "msg_antes": ""})
        
        if ahora < info_j["abre"]:
            st.warning(info_j["msg_antes"])
        else:
            bloqueado = ahora > info_j["cierra"]
            if bloqueado:
                st.error("🔒 El tiempo para esta apuesta ha finalizado.")
            
            # Si es Especiales, mostramos selectores, si no, el formulario de partidos
            if j_sel == "🏆 Apuestas Especiales":
                # Lógica de Campeón, Sorpresa, Decepción aquí...
                pass 
            else:
                # Aquí sigue tu 'with st.form("f_prode")' corregido

        with st.form("f_prode"):
            partidos_j = sorted([p for p in partidos_data if p['Jornada'] == j_sel], key=lambda x: x['ID'])
            for p in partidos_j:
                f_p = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                bloqueado = ahora > (f_p - timedelta(hours=6))
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                    with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    v_l = preds.get(str(p['ID']), {}).get('goles_local', 0)
                    v_v = preds.get(str(p['ID']), {}).get('goles_visitante', 0)
                    gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed", disabled=bloqueado)
                    c3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                    gv = c4.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed", disabled=bloqueado)
                    with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
            if st.form_submit_button(t["save_btn"], use_container_width=True):
                for p in partidos_j:
                    guardar_prediccion_supabase(email_user, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                st.success("Guardado!"); st.rerun()

    # --- 3. RESULTADOS ---
    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        g_real = {f"sl_{p['ID']}": p['Goles Real L'] if p['Goles Real L'] is not None else 0 for p in partidos_data}
        g_real.update({f"sv_{p['ID']}": p['Goles Real V'] if p['Goles Real V'] is not None else 0 for p in partidos_data})
        df_res = calcular_posiciones(partidos_data, g_real, {})
        grupos = sorted([g for g in df_res['Grupo'].unique() if len(g)==1])
        for g in grupos:
            st.write(f"### GRUPO {g}")
            st.dataframe(df_res[df_res['Grupo'] == g][['Flag', 'Equipo', 'PTS', 'DG', 'GF', 'FP']], column_config={"Flag": st.column_config.ImageColumn("")}, hide_index=True, use_container_width=True)

    # --- 4. SIMULADOR (CON CONTROLES DE FP RESTAURADOS) ---
    elif menu == t["nav_sim"]:
        st.subheader(t["nav_sim"])
        
        # Inicialización de estados
        if "sim_goles" not in st.session_state: st.session_state.sim_goles = {}
        if "sim_fp" not in st.session_state: st.session_state.sim_fp = {}

        # Botonera de Control
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("♻️ Reiniciar Todo", use_container_width=True):
                st.session_state.sim_goles = {}
                st.session_state.sim_fp = {}
                # Limpiamos los widgets físicamente
                for key in list(st.session_state.keys()):
                    if key.startswith("fp_in_") or key.startswith("in_l_") or key.startswith("in_v_"):
                        del st.session_state[key]
                st.rerun()
        with c2:
            if st.button("🏟️ Cargar Realidad", use_container_width=True):
                for p in partidos_data:
                    st.session_state.sim_goles[f"sl_{p['ID']}"] = p['Goles Real L'] or 0
                    st.session_state.sim_goles[f"sv_{p['ID']}"] = p['Goles Real V'] or 0
                st.rerun()
        with c3:
            if st.button("🧹 Borrar solo Sim", use_container_width=True):
                for p in partidos_data:
                    if p['Goles Real L'] is None:
                        st.session_state.sim_goles[f"sl_{p['ID']}"] = 0
                        st.session_state.sim_goles[f"sv_{p['ID']}"] = 0
                st.rerun()
        with c4:
            if st.button("💾 Guardar Simulación", use_container_width=True):
                st.success("Guardado localmente")
        
        grupos_lista = sorted(list(set([p['Grupo'] for p in partidos_data if p['Grupo'] and len(p['Grupo'])==1])))
        g_sel = st.radio("Enfocar Grupo:", grupos_lista, horizontal=True)

        # Calculamos posiciones globales
        df_global = calcular_posiciones(partidos_data, st.session_state.sim_goles, st.session_state.sim_fp)
        
        col_input, col_table = st.columns([1.2, 1])

        with col_input:
            st.markdown(f"### ⚽ Partidos Grupo {g_sel}")
            for p in [p for p in partidos_data if p['Grupo'] == g_sel]:
                with st.container(border=True):
                    ca, cb, cc, cd, ce = st.columns([3, 1, 0.5, 1, 3])
                    with ca: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                    
                    # Inputs de goles
                    st.session_state.sim_goles[f"sl_{p['ID']}"] = cb.number_input("L", 0, 20, st.session_state.sim_goles.get(f"sl_{p['ID']}", 0), key=f"in_l_{p['ID']}")
                    cc.write(":")
                    st.session_state.sim_goles[f"sv_{p['ID']}"] = cd.number_input("V", 0, 20, st.session_state.sim_goles.get(f"sv_{p['ID']}", 0), key=f"in_v_{p['ID']}")
                    
                    with ce: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
            
            # --- SECCIÓN DE FAIR PLAY RESTAURADA ---
            st.write("🚩 **Ajuste de Fair Play (Tarjetas)**")
            equipos_fijos = sorted(df_global[df_global['Grupo'] == g_sel]['Equipo'].tolist())
            cols_fp = st.columns(4)
            for i, eq_name in enumerate(equipos_fijos):
                with cols_fp[i % 4]:
                    row = df_global[df_global['Equipo'] == eq_name]
                    if not row.empty:
                        st.image(row['Flag'].values[0], width=20)
                        # Restauramos el input de Fair Play permanente
                        st.session_state.sim_fp[eq_name] = st.number_input(
                            f"{eq_name}", -50, 50, 
                            st.session_state.sim_fp.get(eq_name, 0), 
                            key=f"fp_in_{eq_name}"
                        )

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
                def style_3(s): return ['background-color: #2ecc7133' if s.name < 8 else '' for _ in s]
                st.dataframe(df_3[['Flag', 'Equipo', 'Grupo', 'PTS', 'DG', 'GF', 'FP']].style.apply(style_3, axis=1), 
                             column_config={"Flag": st.column_config.ImageColumn("")}, hide_index=True, use_container_width=True)

        # --- SECCIÓN: VER CUADRO COMPLETO ---
        st.divider()
        with st.expander("🌍 Ver Cuadro Completo (Todos los Grupos)", expanded=False):
            filas_grupos = [grupos_lista[i:i + 4] for i in range(0, len(grupos_lista), 4)]
            for fila in filas_grupos:
                cols = st.columns(4)
                for i, g_id in enumerate(fila):
                    with cols[i]:
                        st.markdown(f"**Grupo {g_id}**")
                        df_mini = df_global[df_global['Grupo'] == g_id][['Flag', 'Equipo', 'PTS', 'DG']]
                        st.dataframe(df_mini, column_config={"Flag": st.column_config.ImageColumn("")}, hide_index=True, use_container_width=True)

        st.divider()
        st.subheader("🏁 Cuadro de Eliminatorias Simuladas")
        
    else: st.info("Próximamente")

else:
    st.title("⚽ World Cup 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button("Login with Google", auth_url, type="primary")

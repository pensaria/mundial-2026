import streamlit as st
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io
import os

# 1. Configuración de la página
st.set_page_config(page_title="Mundial 2026", page_icon="⚽", layout="wide")

# --- SISTEMA DE IDIOMAS ---
texts = {
    "Español": {
        "nav_home": "🏠 Inicio", "nav_play": "⚽ Jugar Prode", "nav_my_preds": "🎯 Mis Pronósticos", "nav_results": "🏆 Resultados",
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
        "lock_msg": "⚠️ El tiempo para esta jornada ha expirado. La edición está bloqueada.",
        "my_ticket": "🎟️ Ticket Apuestas Especiales", "my_ticket_j": "🎟️ Ticket de esta Jornada",
        "gen_ticket": "Generar Imagen", "download_ticket": "Descargar Ticket 📥"
    },
    "English": {
        "nav_home": "🏠 Home", "nav_play": "⚽ Play Predictor", "nav_my_preds": "🎯 My Predictions", "nav_results": "🏆 Results",
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
        "lock_msg": "⚠️ Time's up for this matchday. Editing is locked.",
        "my_ticket": "🎟️ Special Bets Ticket", "my_ticket_j": "🎟️ Matchday Ticket",
        "gen_ticket": "Generate Image", "download_ticket": "Download Ticket 📥"
    }
}

# --- DICCIONARIO HARDCODEADO DE FECHAS LÍMITE ---
FECHAS_LIMITE = {
    "Fecha 1": datetime(2026, 6, 11, 17, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Matchday 1": datetime(2026, 6, 11, 17, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Fecha 2": datetime(2026, 6, 18, 14, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Matchday 2": datetime(2026, 6, 18, 14, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Fecha 3": datetime(2026, 6, 24, 17, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Matchday 3": datetime(2026, 6, 24, 17, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "16vos de final": datetime(2026, 6, 28, 17, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Round of 32": datetime(2026, 6, 28, 17, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "8vos de final": datetime(2026, 7, 4, 15, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Round of 16": datetime(2026, 7, 4, 15, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "4tos de final": datetime(2026, 7, 9, 18, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Quarter-finals": datetime(2026, 7, 9, 18, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Semifinales": datetime(2026, 7, 14, 17, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Semi-finals": datetime(2026, 7, 14, 17, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Final y 3er puesto": datetime(2026, 7, 18, 19, 0, tzinfo=ZoneInfo("Europe/Sofia")),
    "Final & 3rd place": datetime(2026, 7, 18, 19, 0, tzinfo=ZoneInfo("Europe/Sofia")),
}

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()

# --- FUNCIONES DE BASE DE DATOS ---
def obtener_perfil(email):
    res = supabase.table("perfiles").select("*").eq("email", email).execute()
    return res.data[0] if res.data else None

def crear_perfil(email, username):
    supabase.table("perfiles").insert({"email": email, "nombre_usuario": username}).execute()

def verificar_nickname_existente(username):
    res = supabase.table("perfiles").select("nombre_usuario").eq("nombre_usuario", username).execute()
    return len(res.data) > 0

def guardar_apuestas_especiales(email, camp, sub, ter, sorp, decep):
    supabase.table("perfiles").update({
        "equipo_campeon": camp, "equipo_subcampeon": sub, 
        "equipo_tercero": ter, "equipo_sorpresa": sorp, "equipo_decepcion": decep
    }).eq("email", email).execute()

def borrar_predicciones_jornada(user_email, partidos_ids):
    for pid in partidos_ids:
        supabase.table("predicciones").delete().eq("usuario", user_email).eq("partido_id", str(pid)).execute()

# --- DESCARGA DE FUENTE PARA PILLOW ---
@st.cache_resource
def cargar_fuente(size):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
            r = requests.get(url, allow_redirects=True)
            with open(font_path, 'wb') as f: f.write(r.content)
        except: return ImageFont.load_default()
    try: return ImageFont.truetype(font_path, size)
    except: return ImageFont.load_default()

# --- GENERADORES DE TICKETS ---
def generar_ticket_especiales(username, camp, sub, ter, sorp, decep):
    img = Image.new('RGB', (600, 360), color=(240, 245, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 590, 350], outline=(40, 100, 150), width=6)
    
    fnt_title = cargar_fuente(24)
    fnt_text = cargar_fuente(18)

    c, s, t, so, de = [x if x else "No elegido" for x in (camp, sub, ter, sorp, decep)]
    
    d.text((120, 30), "TICKET APUESTAS ESPECIALES 2026", fill=(0, 0, 0), font=fnt_title)
    d.text((40, 80), f"👤 Jugador: {username}", fill=(0, 0, 0), font=fnt_text)
    d.text((40, 130), f"🏆 Campeón (10pts): {c}", fill=(0, 0, 0), font=fnt_text)
    d.text((40, 170), f"🥈 Subcampeón (8pts): {s}", fill=(0, 0, 0), font=fnt_text)
    d.text((40, 210), f"🥉 3er Puesto (6pts): {t}", fill=(0, 0, 0), font=fnt_text)
    d.text((40, 250), f"🚀 Sorpresa (5pts): {so}", fill=(0, 0, 0), font=fnt_text)
    d.text((40, 290), f"📉 Decepción (5pts): {de}", fill=(0, 0, 0), font=fnt_text)
    
    img_byte_arr = io.BytesIO(); img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def generar_ticket_jornada(username, jornada_nombre, predicciones, partidos):
    partidos_j = [p for p in partidos if str(p['ID']) in predicciones]
    altura = max(300, 120 + (len(partidos_j) // 2 + 1) * 40)
    img = Image.new('RGB', (700, altura), color=(245, 245, 245))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 690, altura-10], outline=(0, 150, 100), width=5)
    
    fnt_title = cargar_fuente(22); fnt_text = cargar_fuente(16)
    d.text((20, 30), f"TICKET: {jornada_nombre.upper()}", fill=(0,0,0), font=fnt_title)
    d.text((20, 60), f"👤 Jugador: {username}", fill=(0,0,0), font=fnt_text)
    
    y_base = 100
    for i, p in enumerate(partidos_j):
        pred = predicciones[str(p['ID'])]
        eq_l = p['Local_ES']; eq_v = p['Visitante_ES']
        gl = pred.get('goles_local', '-'); gv = pred.get('goles_visitante', '-')
        texto = f"{eq_l} {gl} - {gv} {eq_v}"
        
        # 2 Columnas
        col_x = 30 if i % 2 == 0 else 360
        row_y = y_base + (i // 2) * 40
        d.text((col_x, row_y), texto, fill=(20, 20, 20), font=fnt_text)
        
    img_byte_arr = io.BytesIO(); img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

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
    # 1. Traemos las predicciones
    res_preds = supabase.table("predicciones").select("*").execute()
    puntos = {}
    for p in res_preds.data:
        user = p['usuario']
        if user not in puntos: puntos[user] = 0
        m = next((m for m in partidos if str(m['ID']) == p['partido_id']), None)
        if m and m['Goles Real L'] is not None:
            rl, rv, pl, pv = m['Goles Real L'], m['Goles Real V'], p['goles_local'], p['goles_visitante']
            if rl == pl and rv == pv: puntos[user] += 4
            elif (rl > rv and pl > pv) or (rl < rv and pl < pv) or (rl == rv and pl == pv): puntos[user] += 2
            
    # 2. Traemos los perfiles para mapear Correo -> Nickname
    res_perfiles = supabase.table("perfiles").select("email, nombre_usuario").execute()
    mapa_nombres = {r['email']: r['nombre_usuario'] for r in res_perfiles.data}
    
    # 3. Construimos el ranking usando el Nickname (o el correo si no tiene)
    lista_ranking = []
    for k, v in puntos.items():
        nombre_visible = mapa_nombres.get(k, k)
        lista_ranking.append({"Usuario": nombre_visible, "Puntos": v})
        
    return sorted(lista_ranking, key=lambda x: x['Puntos'], reverse=True)

def render_equipo(nombre_es, nombre_en, url_bandera, lang_choice, align="left"):
    nombre = nombre_es if lang_choice == "Español" else (nombre_en or nombre_es)
    flex = "row" if align == "left" else "row-reverse"
    # SOLUCIÓN DE BANDERAS: Aplicamos CSS object-fit: cover y un height/width estricto
    if not url_bandera:
        return f'<div style="display: flex; align-items: center; justify-content: {"flex-start" if align=="left" else "flex-end"}; flex-direction: {flex}; gap: 10px;"><span>{nombre}</span></div>'
    return f'<div style="display: flex; align-items: center; justify-content: {"flex-start" if align=="left" else "flex-end"}; flex-direction: {flex}; gap: 10px;"><img src="{url_bandera}" style="width: 30px; height: 20px; object-fit: cover; border-radius: 3px;"><span>{nombre}</span></div>'

# --- FUNCIÓN PARA TABLAS SIN DEFORMAR BANDERAS CORREGIDA ---
def render_html_table(df, styler_func=None):
    df_fmt = df.copy()
    if 'Flag' in df_fmt.columns:
        df_fmt['Flag'] = df_fmt['Flag'].apply(lambda x: f'<img src="{x}" style="width:30px; height:20px; object-fit:cover; border-radius:3px;">' if pd.notna(x) and x else '')
    
    styler = df_fmt.style
    if styler_func:
        styler = styler.apply(styler_func, axis=1)
    
    try:
        styler = styler.hide(axis="index")
    except:
        styler = styler.hide_index()
        
    html = styler.to_html(escape=False)
    html = html.replace('\n', '')
    
    css = "<style>.custom-tbl table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 1rem; } .custom-tbl th { text-align: center !important; padding: 8px; border-bottom: 2px solid #ddd; background-color: rgba(0,0,0,0.02); } .custom-tbl td { text-align: center !important; padding: 8px; border-bottom: 1px solid #ddd; vertical-align: middle; } .custom-tbl tr:hover { background-color: rgba(0,0,0,0.01); }</style>"
    
    st.markdown(f'<div class="custom-tbl">{css}{html}</div>', unsafe_allow_html=True)

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

# --- SESIÓN E INTERCAMBIO OAUTH REAL DE GOOGLE ---
if "connected" not in st.session_state: st.session_state.connected = False
if "user_email" not in st.session_state: st.session_state.user_email = None

if "code" in st.query_params and not st.session_state.connected:
    auth_code = st.query_params["code"]
    try:
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": auth_code,
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "redirect_uri": st.secrets["google_oauth"]["redirect_uri"],
            "grant_type": "authorization_code"
        }
        token_res = requests.post(token_url, data=token_data).json()
        access_token = token_res.get("access_token")
        
        if access_token:
            user_info = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"}).json()
            email_detectado = user_info.get("email")
            if email_detectado:
                st.session_state.user_email = email_detectado
                st.session_state.connected = True
                st.query_params.clear()
                st.rerun()
    except Exception as e:
        st.error(f"Error de autenticación OAuth: {e}")

if st.session_state.connected and st.session_state.user_email:
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    partidos_data = obtener_partidos_airtable()
    
    # --- FLUJO NICKNAME CON VERIFICACIÓN DE DUPLICADOS ---
    perfil_actual = obtener_perfil(st.session_state.user_email)
    if not perfil_actual:
        st.warning(t["ask_username"])
        new_nick = st.text_input("Nickname:", max_chars=15).strip()
        if st.button(t["save_user"]):
            if new_nick:
                if verificar_nickname_existente(new_nick):
                    st.error(f"⚠️ El nickname '{new_nick}' ya está en uso. Por favor, elige otro." if lang == "Español" else f"⚠️ The nickname '{new_nick}' is already taken. Please choose another.")
                else:
                    crear_perfil(st.session_state.user_email, new_nick)
                    st.rerun()
        st.stop()
        
    username_display = perfil_actual['nombre_usuario']
    st.sidebar.write(f"⚽ {t['user_welcome']}**{username_display}**!")

    menu = st.sidebar.radio("Menu", [t["nav_home"], t["nav_play"], t["nav_my_preds"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]])
    
    modo_juego = st.sidebar.radio("Modo / Mode", [t["mode_simple"], t["mode_complex"]])
    if st.sidebar.button(t["logout"]): 
        st.session_state.connected = False
        st.session_state.user_email = None
        st.query_params.clear()
        st.rerun()

    st.title(t["title"])

    # --- 1. INICIO ---
    if menu == t["nav_home"]:
        col_rank, col_next = st.columns([1.5, 1], gap="large")
        
        with col_rank:
            st.subheader(t["ranking_title"])
            ranking = obtener_ranking_global(partidos_data)
            if ranking: 
                df_global_rank = pd.DataFrame(ranking)
                st.table(df_global_rank)
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
                    if f_dt > grandma:
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
            preds = obtener_predicciones_usuario(st.session_state.user_email)
            
            # --- APUESTAS ESPECIALES ---
            with st.expander(t["special_bets"], expanded=False):
                zona_sofia = ZoneInfo("Europe/Sofia")
                ahora = datetime.now(zona_sofia)
                limite_especiales = FECHAS_LIMITE.get("Fecha 1" if lang == "Español" else "Matchday 1")
                bloqueado_especiales = False
                
                if limite_especiales and ahora > limite_especiales:
                    bloqueado_especiales = True
                    st.error("🔒 " + ("El torneo ha comenzado. Las apuestas especiales están bloqueadas." if lang == "Español" else "The tournament has started. Special bets are locked."))

                dict_equipos = {}
                for p in partidos_data:
                    eq_l = p['Local_ES'] if lang == "Español" else p['Local_EN']
                    eq_v = p['Visitante_ES'] if lang == "Español" else p['Visitante_EN']
                    if eq_l and str(eq_l).strip() != "" and str(eq_l) != "None": dict_equipos[eq_l] = p['Rank_L']
                    if eq_v and str(eq_v).strip() != "" and str(eq_v) != "None": dict_equipos[eq_v] = p['Rank_V']
                
                lista_todos = [""] + sorted(list(dict_equipos.keys()))
                lista_sorpresa = [""] + sorted([eq for eq, rank in dict_equipos.items() if rank > 10])
                lista_decepcion = [""] + sorted([eq for eq, rank in dict_equipos.items() if rank <= 10])
                
                st.info("💡 **Puntos:** Campeón (10pts), Subcampeón (8pts), 3er Puesto (6pts). Sorpresa y Decepción (5pts).")

                def get_idx(lst, val): return lst.index(val) if val in lst else 0
                
                c1, c2, c3 = st.columns(3)
                val_camp = c1.selectbox(t["champion"], lista_todos, index=get_idx(lista_todos, perfil_actual['equipo_campeon']), disabled=bloqueado_especiales)
                val_sub = c2.selectbox(t["runner_up"], lista_todos, index=get_idx(lista_todos, perfil_actual['equipo_subcampeon']), disabled=bloqueado_especiales)
                val_ter = c3.selectbox(t["third_place"], lista_todos, index=get_idx(lista_todos, perfil_actual['equipo_tercero']), disabled=bloqueado_especiales)
                
                c4, c5 = st.columns(2)
                val_sorp = c4.selectbox(t["surprise"], lista_sorpresa, index=get_idx(lista_sorpresa, perfil_actual['equipo_sorpresa']), disabled=bloqueado_especiales)
                val_dec = c5.selectbox(t["disappointment"], lista_decepcion, index=get_idx(lista_decepcion, perfil_actual['equipo_decepcion']), disabled=bloqueado_especiales)
                
                top3_seleccionados = [x for x in [val_camp, val_sub, val_ter] if x != ""]
                hay_error_top3 = len(top3_seleccionados) != len(set(top3_seleccionados))
                
                if hay_error_top3:
                    st.error("Error: No puedes repetir el mismo equipo en el Top 3." if lang == "Español" else "Error: You cannot repeat the same team in the Top 3.")
                if val_dec != "" and val_dec in top3_seleccionados:
                    st.warning("Este equipo fue elegido para los primeros 3 puestos, ¿estás seguro de tu elección de decepción?" if lang == "Español" else "This team was chosen for the Top 3 spots, are you sure of your choice?")

                col_a1, col_a2 = st.columns([1, 1])
                if col_a1.button(t["save_special"], disabled=hay_error_top3 or bloqueado_especiales):
                    guardar_apuestas_especiales(st.session_state.user_email, val_camp, val_sub, val_ter, val_sorp, val_dec)
                    st.success("¡Guardado!")
                    st.rerun()
                
                if col_a2.button(t["my_ticket"]):
                    img_data = generar_ticket_especiales(username_display, val_camp, val_sub, val_ter, val_sorp, val_dec)
                    st.download_button(label=t["download_ticket"], data=img_data, file_name=f"ticket_esp_{username_display}.png", mime="image/png", type="primary")

            st.divider()

            # --- JORNADAS Y TIMER DICCIONARIO ---
            jornadas_fijas_es = ["Fecha 1", "Fecha 2", "Fecha 3", "16vos de final", "8vos de final", "4tos de final", "Semifinales", "Final y 3er puesto"]
            jornadas_fijas_en = ["Matchday 1", "Matchday 2", "Matchday 3", "Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final & 3rd place"]
            jornadas_list = jornadas_fijas_es if lang == "Español" else jornadas_fijas_en
            
            c_j1, c_j2 = st.columns([2, 1])
            j_sel = c_j1.selectbox("Jornada / Matchday:", jornadas_list)
            
            # CÁLCULO DEL RELOJ
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora = datetime.now(zona_sofia)
            limite_fecha = FECHAS_LIMITE.get(j_sel)
            
            bloqueado_por_tiempo = False
            if limite_fecha:
                restante = limite_fecha - ahora
                if restante.total_seconds() > 0:
                    dias = restante.days
                    horas, resto = divmod(restante.seconds, 3600)
                    mins, _ = divmod(resto, 60)
                    c_j2.info(f"⏳ **{dias}d {horas}h {mins}m**")
                else:
                    c_j2.error("🔒 Cerrado / Locked")
                    st.error(t["lock_msg"])
                    bloqueado_por_tiempo = True

            jornada_key = 'Jornada_ES' if lang == "Español" else 'Jornada_EN'
            partidos_jornada = [p for p in partidos_data if p.get(jornada_key) == j_sel]
            partidos_ordenados = sorted(partidos_jornada, key=lambda x: str(x['Grupo']))

            if not partidos_ordenados:
                st.info("No hay partidos cargados para esta jornada." if lang == "Español" else "No matches loaded for this matchday.")
            
            with st.form("f_prode"):
                for p in partidos_ordenados:
                    with st.container(border=True):
                        st.caption(f"Grupo {p['Grupo']}")
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                        
                        with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        
                        v_l = preds.get(str(p['ID']), {}).get('goles_local', 0)
                        v_v = preds.get(str(p['ID']), {}).get('goles_visitante', 0)
                        
                        gl = c2.number_input("L", 0, 20, v_l, key=f"l_{p['ID']}", label_visibility="collapsed", disabled=bloqueado_por_tiempo)
                        c3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                        gv = c4.number_input("V", 0, 20, v_v, key=f"v_{p['ID']}", label_visibility="collapsed", disabled=bloqueado_por_tiempo)
                        
                        with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)
                
                col_b1, col_b2 = st.columns(2)
                if col_b1.form_submit_button(t["save_btn"], use_container_width=True, disabled=bloqueado_por_tiempo):
                    for p in partidos_jornada:
                        guardar_prediccion_supabase(st.session_state.user_email, p['ID'], st.session_state[f"l_{p['ID']}"], st.session_state[f"v_{p['ID']}"])
                    st.success("¡Pronósticos guardados correctamente!" if lang == "Español" else "Predictions saved successfully!")
                    st.balloons()
                
                if col_b2.form_submit_button(t["reset_btn"], use_container_width=True, disabled=bloqueado_por_tiempo):
                    borrar_predicciones_jornada(st.session_state.user_email, [p['ID'] for p in partidos_jornada])
                    st.rerun()

            # BOTÓN DESCARGAR TICKET DE JORNADA
            with st.expander(t["my_ticket_j"]):
                if st.button(t["gen_ticket"] + " " + j_sel):
                    img_data = generar_ticket_jornada(username_display, j_sel, preds, partidos_jornada)
                    st.image(img_data)
                    st.download_button(label=t["download_ticket"], data=img_data, file_name=f"ticket_{j_sel}_{username_display}.png", mime="image/png", type="primary")

    # --- 2.5 MIS PRONÓSTICOS (NUEVA SECCIÓN INDEPENDIENTE) ---
    elif menu == t["nav_my_preds"]:
        st.subheader(t["nav_my_preds"])
        
        # --- APUESTAS ESPECIALES VISIBLES ---
        st.markdown(f"#### 🌟 {t['special_bets']}")
        if perfil_actual:
            c_s1, c_s2, c_s3 = st.columns(3)
            c_s1.info(f"🏆 **{t['champion']}**\n\n{perfil_actual.get('equipo_campeon') or '-'}")
            c_s2.info(f"🥈 **{t['runner_up']}**\n\n{perfil_actual.get('equipo_subcampeon') or '-'}")
            c_s3.info(f"🥉 **{t['third_place']}**\n\n{perfil_actual.get('equipo_tercero') or '-'}")
            
            c_s4, c_s5 = st.columns(2)
            c_s4.success(f"🚀 **{t['surprise']}**\n\n{perfil_actual.get('equipo_sorpresa') or '-'}")
            c_s5.error(f"📉 **{t['disappointment']}**\n\n{perfil_actual.get('equipo_decepcion') or '-'}")
            
        st.divider()
        st.markdown(f"#### 📅 " + ("Pronósticos por Jornada" if lang == "Español" else "Predictions by Matchday"))

        preds = obtener_predicciones_usuario(st.session_state.user_email)
        
        jornadas_fijas_es = ["Fecha 1", "Fecha 2", "Fecha 3", "16vos de final", "8vos de final", "4tos de final", "Semifinales", "Final y 3er puesto"]
        jornadas_fijas_en = ["Matchday 1", "Matchday 2", "Matchday 3", "Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final & 3rd place"]
        jornadas_list = jornadas_fijas_es if lang == "Español" else jornadas_fijas_en
        
        txt_todas = "Todas" if lang == "Español" else "All"
        j_filtro = st.selectbox("Filtrar por Jornada / Filter by Matchday:", [txt_todas] + jornadas_list)
        
        puntos_totales_jornada = 0
        partidos_filtrados = partidos_data if j_filtro == txt_todas else [p for p in partidos_data if p.get('Jornada_ES' if lang=="Español" else 'Jornada_EN') == j_filtro]
        
        # Filtramos solo los que el usuario sí predijo
        partidos_con_pred = [p for p in partidos_filtrados if str(p['ID']) in preds]
        
        if not partidos_con_pred:
            st.info("Aún no tienes pronósticos para esta jornada." if lang == "Español" else "You don't have predictions for this matchday yet.")
        else:
            for p in partidos_con_pred:
                pred = preds[str(p['ID'])]
                pl, pv = pred['goles_local'], pred['goles_visitante']
                rl, rv = p['Goles Real L'], p['Goles Real V']
                eq_l, eq_v = p['Local_ES'] if lang=="Español" else p['Local_EN'], p['Visitante_ES'] if lang=="Español" else p['Visitante_EN']
                
                puntos_obtenidos = 0
                bg_color = "rgba(0,0,0,0.02)"
                
                if rl is not None and rv is not None:
                    if rl == pl and rv == pv:
                        puntos_obtenidos = 4
                        bg_color = "rgba(46, 204, 113, 0.15)" # Verde acierto exacto
                    elif (rl > rv and pl > pv) or (rl < rv and pl < pv) or (rl == rv and pl == pv):
                        puntos_obtenidos = 2
                        bg_color = "rgba(241, 196, 15, 0.15)" # Amarillo acierto ganador
                
                puntos_totales_jornada += puntos_obtenidos
                
                flag_l_img = f"<img src='{p['Bandera_L']}' style='width: 24px; height: 16px; object-fit: cover; border-radius: 2px;'>" if p['Bandera_L'] else ""
                flag_v_img = f"<img src='{p['Bandera_V']}' style='width: 24px; height: 16px; object-fit: cover; border-radius: 2px;'>" if p['Bandera_V'] else ""

                html_card = f"<div style='background-color: {bg_color}; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 10px;'>"
                html_card += f"<div style='font-size: 16px; font-weight: bold; display: flex; align-items: center; gap: 8px;'>{flag_l_img} <span>{eq_l} &nbsp;&nbsp;{pl} - {pv}&nbsp;&nbsp; {eq_v}</span> {flag_v_img} <span style='color: gray; font-size:12px; font-weight: normal; margin-left:10px;'>(Tu pronóstico)</span></div>"
                
                if rl is not None and rv is not None:
                    html_card += f"<div style='font-size: 14px; margin-top:8px; display: flex; align-items: center; gap: 8px;'>{flag_l_img} <span>{eq_l} &nbsp;&nbsp;{rl} - {rv}&nbsp;&nbsp; {eq_v}</span> {flag_v_img} <span style='color: gray; font-size:12px; margin-left:10px;'>(Realidad)</span></div>"
                    html_card += f"<div style='margin-top: 8px; font-weight: bold; color: {'#27ae60' if puntos_obtenidos > 0 else '#e74c3c'};'>✅ Puntos Obtenidos: {puntos_obtenidos}</div>"
                else:
                    html_card += f"<div style='font-size: 14px; color: gray; margin-top:5px;'>Partido aún no disputado</div>"
                
                html_card += "</div>"
                st.markdown(html_card, unsafe_allow_html=True)
                
            st.success(f"**Puntos Totales de la Vista: {puntos_totales_jornada}**")

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
        
        filas_grupos_res = [grupos[i:i + 3] for i in range(0, len(grupos), 3)]
        for fila in filas_grupos_res:
            cols_res = st.columns(3)
            for i, g in enumerate(fila):
                with cols_res[i]:
                    st.write(f"### GRUPO {g}")
                    df_g = pd.DataFrame([s for s in stats.values() if s['Grupo'] == g]).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True])
                    tablas_finales[g] = df_g
                    render_html_table(df_g[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']])

        st.divider()
        st.subheader("🥉 Mejores Terceros / Best Third-Placed Teams")
        terceros = []
        for g in grupos:
            if len(tablas_finales[g]) >= 3: terceros.append(tablas_finales[g].iloc[2])
        if terceros:
            df_3 = pd.DataFrame(terceros).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
            def highlight_3(s): return ['background-color: rgba(46, 204, 113, 0.3)' if s.name < 8 else '' for _ in s]
            render_html_table(df_3[['Flag', 'Equipo', 'Grupo', 'PTS', 'DG', 'GF', 'GC', 'FP']], styler_func=highlight_3)

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

        if "sim_goles_dict" not in st.session_state: st.session_state.sim_goles_dict = {}
        if "sim_fp_dict" not in st.session_state: st.session_state.sim_fp_dict = {}

        c_r1, c_r2, _ = st.columns([1, 1, 2])
        with c_r1:
            if st.button("♻️ " + ("Borrar Todo" if lang=="Español" else "Reset All"), use_container_width=True):
                st.session_state.sim_goles_dict = {}
                st.session_state.sim_fp_dict = {}
                st.session_state.sim_fp_override = True  
                st.session_state.generar_cuadro = False
                st.rerun()
        with c_r2:
            if st.button("🏟️ " + ("Restablecer a Realidad" if lang=="Español" else "Reset to Real"), use_container_width=True):
                for p in partidos_data:
                    if p['Goles Real L'] is not None and p['Goles Real V'] is not None:
                        st.session_state.sim_goles_dict[f"sl_{p['ID']}"] = p['Goles Real L']
                        st.session_state.sim_goles_dict[f"sv_{p['ID']}"] = p['Goles Real V']
                st.session_state.sim_fp_override = False 
                st.session_state.generar_cuadro = False
                st.rerun()

        st.divider()

        grupos_disponibles = sorted(list(set([p['Grupo'] for p in partidos_data if len(p['Grupo']) == 1 and p['Grupo'] != "Definir"])))
        if not grupos_disponibles:
            st.warning("No hay grupos definidos.")
        else:
            equipos_info = {}
            for p in partidos_data:
                for eq_key, bnd_key in [('Local', 'Bandera_L'), ('Visitante', 'Bandera_V')]:
                    es = p[f'{eq_key}_ES']
                    en = p[f'{eq_key}_EN']
                    if es:
                        equipos_info[es] = {"flag": p[bnd_key]}
                        equipos_info[en] = {"flag": p[bnd_key]}

            s_dict = {}
            for p in partidos_data:
                if p['Grupo'] == "Definir": continue
                for eq_key, bnd_key, rnk_key, fp_key in [('Local', 'Bandera_L', 'Rank_L', 'FP_L'), ('Visitante', 'Bandera_V', 'Rank_V', 'FP_V')]:
                    eq = p[f'{eq_key}_ES'] if lang == "Español" else p[f'{eq_key}_EN']
                    if eq and eq not in s_dict:
                        s_dict[eq] = {'Flag': p[bnd_key], 'Equipo': eq, 'Grupo': p['Grupo'], 'PJ': 0, 'PTS': 0, 'DG': 0, 'GF': 0, 'GC': 0, 'Rank': p[rnk_key], 'FP_Base': p[fp_key], 'H2H_Matches': []}

            for p in partidos_data:
                if p['Grupo'] == "Definir": continue
                eq_l = p['Local_ES'] if lang == "Español" else p['Local_EN']
                eq_v = p['Visitante_ES'] if lang == "Español" else p['Visitante_EN']

                gl = st.session_state.sim_goles_dict.get(f"sl_{p['ID']}")
                gv = st.session_state.sim_goles_dict.get(f"sv_{p['ID']}")

                if gl is not None and gv is not None and eq_l and eq_v:
                    s_dict[eq_l]['PJ'] += 1; s_dict[eq_v]['PJ'] += 1
                    s_dict[eq_l]['GF'] += gl; s_dict[eq_v]['GF'] += gv
                    s_dict[eq_l]['GC'] += gv; s_dict[eq_v]['GC'] += gl
                    s_dict[eq_l]['DG'] += (gl - gv); s_dict[eq_v]['DG'] += (gv - gl)

                    pts_l = 3 if gl > gv else (1 if gl == gv else 0)
                    pts_v = 3 if gv > gl else (1 if gl == gv else 0)

                    s_dict[eq_l]['PTS'] += pts_l; s_dict[eq_v]['PTS'] += pts_v
                    s_dict[eq_l]['H2H_Matches'].append({'rival': eq_v, 'gf': gl, 'gc': gv, 'pts': pts_l})
                    s_dict[eq_v]['H2H_Matches'].append({'rival': eq_l, 'gf': gv, 'gc': gl, 'pts': pts_v})

            for eq in s_dict:
                base_fp = 0 if st.session_state.get('sim_fp_override', False) else s_dict[eq]['FP_Base']
                s_dict[eq]['FP'] = base_fp + st.session_state.sim_fp_dict.get(eq, 0)

            def fifa_sort_key(e):
                empatados = [x for x in s_dict.values() if x['Grupo'] == e['Grupo'] and x['PTS'] == e['PTS']]
                h2h_pts, h2h_dg, h2h_gf = 0, 0, 0
                if len(empatados) > 1:
                    nombres_emp = [x['Equipo'] for x in empatados]
                    h2h_matches = [m for m in e['H2H_Matches'] if m['rival'] in nombres_emp]
                    h2h_pts = sum(m['pts'] for m in h2h_matches)
                    h2h_dg = sum(m['gf'] - m['gc'] for m in h2h_matches)
                    h2h_gf = sum(m['gf'] for m in h2h_matches)
                return (-e['PTS'], -h2h_pts, -h2h_dg, -h2h_gf, -e['DG'], -e['GF'], -e['FP'], e['Rank'])

            df_global = pd.DataFrame(sorted(s_dict.values(), key=fifa_sort_key))

            idx_grupo = grupos_disponibles.index(st.session_state.sim_grupo_sel) if st.session_state.get("sim_grupo_sel") in grupos_disponibles else 0
            g_sel = st.radio("Enfocar Grupo / Focus Group:", grupos_disponibles, horizontal=True, index=idx_grupo)
            st.session_state.sim_grupo_sel = g_sel

            col_izq, col_der = st.columns([1.1, 1], gap="medium")

            with col_izq:
                st.markdown(f"### ⚽ Partidos Grupo {g_sel}")
                
                with st.form(f"form_sim_{g_sel}"):
                    partidos_grupo = [p for p in partidos_data if p['Grupo'] == g_sel]
                    for p in partidos_grupo:
                        with st.container(border=True):
                            st.caption(f"Grupo {p['Grupo']}")
                            c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                            with c1: st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                            
                            val_l = st.session_state.sim_goles_dict.get(f"sl_{p['ID']}")
                            kwargs_l = {"min_value": 0, "max_value": 20, "key": f"temp_l_{p['ID']}", "label_visibility": "collapsed", "placeholder": "-"}
                            if val_l is not None: kwargs_l["value"] = int(val_l)
                            c2.number_input("L", **kwargs_l)
                            
                            c3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                            
                            val_v = st.session_state.sim_goles_dict.get(f"sv_{p['ID']}")
                            kwargs_v = {"min_value": 0, "max_value": 20, "key": f"temp_v_{p['ID']}", "label_visibility": "collapsed", "placeholder": "-"}
                            if val_v is not None: kwargs_v["value"] = int(val_v)
                            c4.number_input("V", **kwargs_v)
                            
                            with c5: st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang, align="right"), unsafe_allow_html=True)

                    st.write("🚩 **Ajuste de Fair Play (Tarjetas)**")
                    eq_nombres = sorted(list(set([p['Local_ES'] if lang == "Español" else p['Local_EN'] for p in partidos_grupo] + [p['Visitante_ES'] if lang == "Español" else p['Visitante_EN'] for p in partidos_grupo])))
                    eq_nombres = [eq for eq in eq_nombres if eq]

                    for eq_name in eq_nombres:
                        with st.container(border=True):
                            c_fp1, c_fp2 = st.columns([3, 1])
                            row = df_global[df_global['Equipo'] == eq_name]
                            flag_url = row['Flag'].values[0] if not row.empty else ""
                            with c_fp1:
                                st.markdown(f"<div style='display:flex; align-items:center; gap:10px;'><img src='{flag_url}' style='width: 30px; height: 20px; object-fit: cover; border-radius: 3px;'><b>{eq_name}</b></div>", unsafe_allow_html=True)
                            
                            val_fp = st.session_state.sim_fp_dict.get(eq_name, 0)
                            val_seguro = min(0, int(val_fp))
                            
                            with c_fp2:
                                st.number_input("FP", min_value=-99, max_value=0, value=val_seguro, key=f"temp_fp_{eq_name}", label_visibility="collapsed")
                    
                    submit_btn = st.form_submit_button("⚽ Simular Grupo!", type="primary", use_container_width=True)
                    if submit_btn:
                        for p in partidos_grupo:
                            st.session_state.sim_goles_dict[f"sl_{p['ID']}"] = st.session_state[f"temp_l_{p['ID']}"]
                            st.session_state.sim_goles_dict[f"sv_{p['ID']}"] = st.session_state[f"temp_v_{p['ID']}"]
                        for eq_name in eq_nombres:
                            st.session_state.sim_fp_dict[eq_name] = min(0, int(st.session_state[f"temp_fp_{eq_name}"]))
                        st.rerun()

            with col_der:
                st.markdown(f"### 📊 Posiciones Grupo {g_sel}")
                df_g_show = df_global[df_global['Grupo'] == g_sel]
                render_html_table(df_g_show[['Flag', 'Equipo', 'PJ', 'PTS', 'DG', 'GF', 'GC', 'FP']])

                st.markdown("### 🥉 Ranking Mejores Terceros")
                terceros = []
                for g in grupos_disponibles:
                    df_grp = df_global[df_global['Grupo'] == g]
                    if len(df_grp) >= 3: terceros.append(df_grp.iloc[2])

                if terceros:
                    df_3 = pd.DataFrame(terceros).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
                    def style_3(s): return ['background-color: rgba(46, 204, 113, 0.3)' if s.name < 8 else '' for _ in s]
                    render_html_table(df_3[['Flag', 'Equipo', 'Grupo', 'PJ', 'PTS', 'DG', 'GF', 'FP']], styler_func=style_3)

            st.divider()
            with st.expander("🌍 Ver Cuadro Completo (Todos los Grupos)", expanded=False):
                filas_grupos = [grupos_disponibles[i:i + 4] for i in range(0, len(grupos_disponibles), 4)]
                for fila in filas_grupos:
                    cols = st.columns(4)
                    for i, g_id in enumerate(fila):
                        with cols[i]:
                            st.markdown(f"**Grupo {g_id}**")
                            df_mini = df_global[df_global['Grupo'] == g_id][['Flag', 'Equipo', 'PTS', 'DG']]
                            render_html_table(df_mini)

            st.divider()
            if st.button("🏆 Generar Cuadro Final", type="primary", use_container_width=True):
                st.session_state.generar_cuadro = True
                st.rerun()

            if st.session_state.get("generar_cuadro", False):
                r_grp = {}
                for g in grupos_disponibles:
                    df_grp = df_global[df_global['Grupo'] == g]
                    r_grp[f"1{g}"] = df_grp.iloc[0]['Equipo'] if len(df_grp) >= 1 else f"1{g}"
                    r_grp[f"2{g}"] = df_grp.iloc[1]['Equipo'] if len(df_grp) >= 2 else f"2{g}"
                
                if len(terceros) >= 8:
                    top_8 = df_3.head(8)
                    asignacion = asignar_terceros(top_8['Grupo'].tolist())
                    if asignacion:
                        t_dict = {g: eq for g, eq in zip(top_8['Grupo'].tolist(), top_8['Equipo'].tolist())}
                        r_grp["M79_3"] = t_dict[asignacion['R1']]
                        r_grp["M85_3"] = t_dict[asignacion['R2']]
                        r_grp["M81_3"] = t_dict[asignacion['R3']]
                        r_grp["M74_3"] = t_dict[asignacion['R4']]
                        r_grp["M82_3"] = t_dict[asignacion['R5']]
                        r_grp["M77_3"] = t_dict[asignacion['R6']]
                        r_grp["M87_3"] = t_dict[asignacion['R7']]
                        r_grp["M80_3"] = t_dict[asignacion['R8']]

                def render_sim_ko_match(m_id, t_l, t_v):
                    known_l = t_l in equipos_info
                    known_v = t_v in equipos_info
                    
                    if not known_l or not known_v:
                        with st.container(border=True):
                            st.caption(m_id)
                            st.markdown(f"<div style='text-align:center; color:gray;'><b>{t_l}</b> vs <b>{t_v}</b></div>", unsafe_allow_html=True)
                        return f"W{m_id.replace('M','')}", f"L{m_id.replace('M','')}"
                        
                    with st.container(border=True):
                        st.caption(m_id)
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                        
                        flag_l = equipos_info[t_l]['flag']
                        flag_v = equipos_info[t_v]['flag']
                        
                        with c1: st.markdown(render_equipo(t_l, t_l, flag_l, lang), unsafe_allow_html=True)
                        
                        key_gl, key_gv = f"sko_gl_{m_id}", f"sko_gv_{m_id}"
                        gl, gv = st.session_state.get(key_gl), st.session_state.get(key_gv)
                        
                        new_gl = c2.number_input("L", min_value=0, max_value=20, value=gl, key=f"in_{key_gl}", label_visibility="collapsed", placeholder="-")
                        c3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                        new_gv = c4.number_input("V", min_value=0, max_value=20, value=gv, key=f"in_{key_gv}", label_visibility="collapsed", placeholder="-")
                        
                        st.session_state[key_gl], st.session_state[key_gv] = new_gl, new_gv
                        
                        with c5: st.markdown(render_equipo(t_v, t_v, flag_v, lang, align="right"), unsafe_allow_html=True)
                        
                        winner, loser = f"W{m_id.replace('M','')}", f"L{m_id.replace('M','')}"
                        
                        if new_gl is not None and new_gv is not None:
                            if new_gl > new_gv: winner, loser = t_l, t_v
                            elif new_gv > new_gl: winner, loser = t_v, t_l
                            else:
                                st.markdown("<div style='text-align:center; font-size:11px; color:gray; margin-top:-10px; margin-bottom:5px;'>Penales / Penalties</div>", unsafe_allow_html=True)
                                cp1, cp2, cp3, cp4, cp5 = st.columns([3, 1, 0.5, 1, 3])
                                key_pl, key_pv = f"sko_pl_{m_id}", f"sko_pv_{m_id}"
                                pl, pv = st.session_state.get(key_pl), st.session_state.get(key_pv)
                                
                                new_pl = cp2.number_input("PL", min_value=0, max_value=30, value=pl, key=f"in_{key_pl}", label_visibility="collapsed", placeholder="-")
                                cp3.markdown("<div style='text-align:center; padding-top:10px;'>:</div>", unsafe_allow_html=True)
                                new_pv = cp4.number_input("PV", min_value=0, max_value=30, value=pv, key=f"in_{key_pv}", label_visibility="collapsed", placeholder="-")
                                
                                st.session_state[key_pl], st.session_state[key_pv] = new_pl, new_pv
                                
                                if new_pl is not None and new_pv is not None:
                                    if new_pl > new_pv: winner, loser = t_l, t_v
                                    elif new_pv > new_pl: winner, loser = t_v, t_l
                    return winner, loser

                with st.expander("🏆 Jugar Play-Offs Completos", expanded=True):
                    tab_16, tab_8, tab_4, tab_semi, tab_fin = st.tabs(["16vos", "8vos", "4tos", "Semis", "Final & 3er"])
                    ko_win, ko_lose = {}, {}

                    with tab_16:
                        c_i, c_d = st.columns(2)
                        with c_i:
                            ko_win["M74"], _ = render_sim_ko_match("M74", r_grp.get("1E", "1E"), r_grp.get("M74_3", "3ro"))
                            ko_win["M77"], _ = render_sim_ko_match("M77", r_grp.get("1I", "1I"), r_grp.get("M77_3", "3ro"))
                            ko_win["M73"], _ = render_sim_ko_match("M73", r_grp.get("2A", "2A"), r_grp.get("2B", "2B"))
                            ko_win["M75"], _ = render_sim_ko_match("M75", r_grp.get("1F", "1F"), r_grp.get("2C", "2C"))
                            ko_win["M83"], _ = render_sim_ko_match("M83", r_grp.get("2K", "2K"), r_grp.get("2L", "2L"))
                            ko_win["M84"], _ = render_sim_ko_match("M84", r_grp.get("1H", "1H"), r_grp.get("2J", "2J"))
                            ko_win["M81"], _ = render_sim_ko_match("M81", r_grp.get("1D", "1D"), r_grp.get("M81_3", "3ro"))
                            ko_win["M82"], _ = render_sim_ko_match("M82", r_grp.get("1G", "1G"), r_grp.get("M82_3", "3ro"))
                        with c_d:
                            ko_win["M76"], _ = render_sim_ko_match("M76", r_grp.get("1C", "1C"), r_grp.get("2F", "2F"))
                            ko_win["M78"], _ = render_sim_ko_match("M78", r_grp.get("2E", "2E"), r_grp.get("2I", "2I"))
                            ko_win["M79"], _ = render_sim_ko_match("M79", r_grp.get("1A", "1A"), r_grp.get("M79_3", "3ro"))
                            ko_win["M80"], _ = render_sim_ko_match("M80", r_grp.get("1L", "1L"), r_grp.get("M80_3", "3ro"))
                            ko_win["M86"], _ = render_sim_ko_match("M86", r_grp.get("1J", "1J"), r_grp.get("2H", "2H"))
                            ko_win["M88"], _ = render_sim_ko_match("M88", r_grp.get("2D", "2D"), r_grp.get("2G", "2G"))
                            ko_win["M85"], _ = render_sim_ko_match("M85", r_grp.get("1B", "1B"), r_grp.get("M85_3", "3ro"))
                            ko_win["M87"], _ = render_sim_ko_match("M87", r_grp.get("1K", "1K"), r_grp.get("M87_3", "3ro"))

                    with tab_8:
                        c_i, c_d = st.columns(2)
                        with c_i:
                            ko_win["M89"], _ = render_sim_ko_match("M89", ko_win["M74"], ko_win["M77"])
                            ko_win["M90"], _ = render_sim_ko_match("M90", ko_win["M73"], ko_win["M75"])
                            ko_win["M93"], _ = render_sim_ko_match("M93", ko_win["M83"], ko_win["M84"])
                            ko_win["M94"], _ = render_sim_ko_match("M94", ko_win["M81"], ko_win["M82"])
                        with c_d:
                            ko_win["M91"], _ = render_sim_ko_match("M91", ko_win["M76"], ko_win["M78"])
                            ko_win["M92"], _ = render_sim_ko_match("M92", ko_win["M79"], ko_win["M80"])
                            ko_win["M95"], _ = render_sim_ko_match("M95", ko_win["M86"], ko_win["M88"])
                            ko_win["M96"], _ = render_sim_ko_match("M96", ko_win["M85"], ko_win["M87"])

                    with tab_4:
                        c_i, c_d = st.columns(2)
                        with c_i:
                            ko_win["M97"], _ = render_sim_ko_match("M97", ko_win["M89"], ko_win["M90"])
                            ko_win["M98"], _ = render_sim_ko_match("M98", ko_win["M93"], ko_win["M94"])
                        with c_d:
                            ko_win["M99"], _ = render_sim_ko_match("M99", ko_win["M91"], ko_win["M92"])
                            ko_win["M100"], _ = render_sim_ko_match("M100", ko_win["M95"], ko_win["M96"])

                    with tab_semi:
                        c_i, c_d = st.columns(2)
                        with c_i: ko_win["M101"], ko_lose["M101"] = render_sim_ko_match("M101", ko_win["M97"], ko_win["M98"])
                        with c_d: ko_win["M102"], ko_lose["M102"] = render_sim_ko_match("M102", ko_win["M99"], ko_win["M100"])

                    with tab_fin:
                        c_i, c_d = st.columns(2)
                        with c_i: st.markdown("#### 🥉 3er Puesto"); render_sim_ko_match("M103", ko_lose.get("M101", "L101"), ko_lose.get("M102", "L102"))
                        with c_d: st.markdown("#### 🏆 Gran Final"); render_sim_ko_match("M104", ko_win.get("M101", "W101"), ko_win.get("M102", "W102"))

    # --- 5. SEDES Y EQUIPOS ---
    elif menu == t["nav_stadiums"]:
        st.subheader(t["nav_stadiums"])
        st.info("Próximamente / Coming Soon")

else:
    st.title("⚽ World Cup 2026")
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': st.secrets['google_oauth']['client_id'], 'redirect_uri': st.secrets['google_oauth']['redirect_uri'], 'response_type': 'code', 'scope': 'openid email profile'})}"
    st.link_button("Login with Google", auth_url, type="primary")

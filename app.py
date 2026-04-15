if st.session_state.connected:
    # --- SIDEBAR COMÚN ---
    lang = st.sidebar.selectbox("🌐 Language", ["Español", "English"])
    t = texts[lang]
    st.sidebar.success(t["online"])
    
    opciones_menu = [t["nav_home"], t["nav_play"], t["nav_results"], t["nav_sim"], t["nav_stadiums"]]
    menu = st.sidebar.radio(t["nav_home"], opciones_menu, key="menu_sel_radio")
    
    if st.sidebar.button(t["logout"]):
        st.session_state.connected = False
        st.rerun()

    st.title(t["title"])

    # --- 1. PESTAÑA INICIO ---
    if menu == t["nav_home"]:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(t["ranking_title"])
            rank = obtener_ranking_global()
            if rank:
                st.table(rank)
            else:
                st.info("Aún no hay puntos registrados / No points registered yet.")

        with col2:
            st.subheader(t["next_matches"])
            partidos = obtener_partidos_airtable()
            zona_sofia = ZoneInfo("Europe/Sofia")
            ahora = datetime.now(zona_sofia)
            proximos = []
            for p in partidos:
                if p['Fecha_Hora']:
                    f_sofia = datetime.strptime(p['Fecha_Hora'], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(zona_sofia)
                    if f_sofia > ahora:
                        proximos.append((f_sofia, p))
            proximos.sort(key=lambda x: x[0])

            if proximos:
                for f, p in proximos[:5]:
                    with st.container(border=True):
                        st.caption(f.strftime('%d/%m - %H:%M hs'))
                        st.markdown(render_equipo(p['Local_ES'], p['Local_EN'], p['Bandera_L'], lang), unsafe_allow_html=True)
                        st.markdown("<div style='text-align: center; margin: -5px 0; color: #888; font-size: 12px;'>VS</div>", unsafe_allow_html=True)
                        st.markdown(render_equipo(p['Visitante_ES'], p['Visitante_EN'], p['Bandera_V'], lang), unsafe_allow_html=True)
            else:
                st.success(t["no_matches"])

    # --- 2. PESTAÑA JUGAR PRODE ---
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
                st.success("¡Guardado! / Saved!")
                st.balloons()

    # --- 3. PESTAÑA RESULTADOS (Criterio FIFA) ---
    elif menu == t["nav_results"]:
        st.subheader(t["nav_results"])
        partidos = obtener_partidos_airtable()
        if not partidos:
            st.info("No hay datos cargados en Airtable.")
        else:
            stats_global = {}
            for p in partidos:
                if p['Goles Real L'] is not None and p['Goles Real V'] is not None and p['Grupo']:
                    g, l, v = p['Grupo'], p['Local_ES'], p['Visitante_ES']
                    gl, gv = int(p['Goles Real L']), int(p['Goles Real V'])
                    
                    for eq, rnk, fp in [(l, p['Rank_L'], p['FP_L']), (v, p['Rank_V'], p['FP_V'])]:
                        if eq not in stats_global:
                            stats_global[eq] = {'Equipo': eq, 'PJ':0, 'PTS':0, 'GF':0, 'GC':0, 'DG':0, 'Rank': rnk, 'Grupo': g, 'FP': 0}
                        stats_global[eq]['FP'] += fp

                    stats_global[l]['PJ'] += 1; stats_global[v]['PJ'] += 1
                    stats_global[l]['GF'] += gl; stats_global[l]['GC'] += gv
                    stats_global[v]['GF'] += gv; stats_global[v]['GC'] += gl
                    
                    if gl > gv: stats_global[l]['PTS'] += 3
                    elif gl < gv: stats_global[v]['PTS'] += 3
                    else: stats_global[l]['PTS'] += 1; stats_global[v]['PTS'] += 1
                    
                    stats_global[l]['DG'] = stats_global[l]['GF'] - stats_global[l]['GC']
                    stats_global[v]['DG'] = stats_global[v]['GF'] - stats_global[v]['GC']

            grupos_ids = sorted(list(set([s['Grupo'] for s in stats_global.values()])))
            tablas_finales = {}

            for g_id in grupos_ids:
                st.write(f"### GRUPO {g_id}")
                eq_grupo = [s for s in stats_global.values() if s['Grupo'] == g_id]
                eq_grupo.sort(key=lambda x: (x['PTS'], x['DG'], x['GF'], x['FP'], -x['Rank']), reverse=True)
                tablas_finales[g_id] = eq_grupo
                st.table(pd.DataFrame(eq_grupo)[['Equipo', 'PJ', 'PTS', 'DG', 'GF', 'FP']])

            st.divider()
            st.subheader("🥉 Tabla de Terceros Lugares")
            terceros_lista = [tablas_finales[g][2] for g in grupos_ids if len(tablas_finales[g]) >= 3]
            if terceros_lista:
                df_3 = pd.DataFrame(terceros_lista).sort_values(by=['PTS', 'DG', 'GF', 'FP', 'Rank'], ascending=[False, False, False, False, True]).reset_index(drop=True)
                def highlight_top8(s):
                    return ['background-color: rgba(46, 204, 113, 0.3)' if s.name < 8 else '' for _ in s]
                st.dataframe(df_3[['Equipo', 'Grupo', 'PTS', 'DG', 'GF', 'FP']].style.apply(highlight_top8, axis=1))

    # --- 4. OTRAS PESTAÑAS ---
    else:
        st.info("Próximamente / Coming soon")

else:
    # --- PANTALLA DE LOGIN ---
    st.title("⚽ World Cup 2026")
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode({'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code', 'scope': 'openid email profile', 'prompt': 'select_account'})}"
    st.link_button(texts["Español"]["login_btn"], auth_url, type="primary")

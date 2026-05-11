import streamlit as st
from core import load_all, inv, ICONS
from datetime import datetime

def render_admin(*args):
    """Hub Principal do Admin — delega para sub-módulos"""

    st.markdown("""
    <style>
    .stMarkdown,.stText,.stDataFrame,label,div,span,p,h1,h2,h3 { color:#F8FAFC !important; }
    [data-testid="stMetric"] {
        background:linear-gradient(135deg,rgba(59,130,246,0.3),rgba(96,165,250,0.2));
        border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:15px;
    }
    [data-testid="stMetricValue"] { color:#60A5FA !important; }
    [data-testid="stMetricLabel"] { color:#94A3B8 !important; }
    </style>
    """, unsafe_allow_html=True)

    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    # ── Indicadores de conexão e modo offline ─────────────────────────
    from core import render_connection_indicator, render_offline_banner, sync_data_when_online
    render_connection_indicator()
    render_offline_banner()
    sync_data_when_online()

    # ── Header ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E293B,#0F172A);padding:30px;
        border-radius:20px;margin-bottom:30px;border:1px solid rgba(255,255,255,0.2);">
        <h1 style="color:#F8FAFC;margin:0;font-size:2.5rem;">⚡ Painel Administrativo</h1>
        <p style="color:#94A3B8;margin:10px 0 0 0;">
            Utilizador: <strong style="color:#60A5FA">{st.session_state.user}</strong> |
            Tipo: <strong style="color:#60A5FA">{st.session_state.tipo}</strong>
        </p>
        <p style="color:#64748B;margin:5px 0 0 0;font-size:0.9rem;">
            Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Centro de Notificações ────────────────────────────────────────
    from core import get_notificacoes, marcar_notificacao_lida, contar_notificacoes_nao_lidas

    user_atual  = st.session_state.user
    n_nao_lidas = contar_notificacoes_nao_lidas(user_atual)

    col_n1, col_n2 = st.columns([10, 1])
    with col_n2:
        if n_nao_lidas > 0:
            st.markdown(f"""
            <div style="text-align:right;">
                <span style="font-size:1.5rem;">🔔</span>
                <span style="background:#EF4444;color:white;border-radius:50%;
                    padding:2px 8px;font-size:0.8rem;margin-left:-10px;">{n_nao_lidas}</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:right;'><span style='font-size:1.5rem;opacity:0.5;'>🔔</span></div>", unsafe_allow_html=True)

    with st.expander("🔔 Ver Notificações", expanded=n_nao_lidas > 0):
        notifs_df = get_notificacoes(user_atual, apenas_nao_lidas=True, limite=20)
        if not notifs_df.empty:
            for _, notif in notifs_df.iterrows():
                cor = {"info":"#3B82F6","warning":"#F59E0B","error":"#EF4444","success":"#10B981"}.get(notif.get('Tipo','info'),"#6B7280")
                st.markdown(f"""
                <div style="background:{cor}22;border-left:4px solid {cor};
                    padding:15px;border-radius:8px;margin-bottom:10px;">
                    <strong style="color:{cor};">{notif.get('Titulo','')}</strong>
                    <p style="margin:5px 0 0 0;color:#94A3B8;">{notif.get('Mensagem','')}</p>
                    <small style="color:#6B7280;">{notif.get('Data','')} {notif.get('Hora','')}</small>
                </div>""", unsafe_allow_html=True)
            if st.button("✅ Marcar Todas como Lidas", key="marcar_todas_lidas"):
                for _, notif in notifs_df.iterrows():
                    marcar_notificacao_lida(notif['ID'])
                inv()
                st.rerun()
        else:
            st.info("✅ Sem notificações pendentes.")

    st.divider()

    # ── Dashboard Métricas ────────────────────────────────────────────
    st.markdown("### 📊 Visão Geral")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("👷 Técnicos", len(users))
    with c2: st.metric("🏭 Obras Ativas",
        len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0)
    with c3: st.metric("⏳ Validações",
        len(registos_db[registos_db['Status'] == "0"]) if not registos_db.empty else 0)
    with c4: st.metric("📋 Pedidos",
        len(req_fer_db) + len(req_mat_db) + len(req_epi_db))
    with c5: st.metric("⚠️ Incidentes",
        len(incs_db) if not incs_db.empty else 0)
    with c6: st.metric("💰 Faturas",
        len(faturas_db) if not faturas_db.empty else 0)

    st.divider()

    # ── Tabs Principais ───────────────────────────────────────────────
    tabs = st.tabs([
        "✅ Validações",
        "👥 RH",
        "🏗️ Obras",
        "🚗 Frota",
        "🏨 Dormidas",
        "🛒 Compras",
        "💰 Faturação",
        "📊 Orçamentação",
        "💼 Comercial",
        "🎯 Qualidade",
        "📋 Planeamento",
        "💻 IT",
        "🛡️ HSE",
        "📋 Logs Audit",
        "📧 Config Email"
    ])

    # ── TAB 0: VALIDAÇÕES ─────────────────────────────────────────────
    with tabs[0]:
        from mod_admin_validacoes import render_validacoes
        render_validacoes(req_fer_db, req_mat_db, req_epi_db, registos_db, users, obras_db, incs_db)

    # ── TAB 1: RH ─────────────────────────────────────────────────────
    with tabs[1]:
        from mod_admin_rh import render_admin_rh as render_rh
        render_rh(users, avals_db, obras_db, inst_acessos_db)

    # ── TAB 2: OBRAS ──────────────────────────────────────────────────
    with tabs[2]:
        from mod_admin_obras import render_obras
        render_obras(obras_db, frentes_db, users, inst_acessos_db)

    # ── TAB 3: FROTA ──────────────────────────────────────────────────
    with tabs[3]:
        from mod_admin_frota import render_frota
        render_frota()

    # ── TAB 4: DORMIDAS ───────────────────────────────────────────────
    with tabs[4]:
        from mod_admin_dormidas import render_dormidas
        render_dormidas()

    # ── TAB 5: COMPRAS ────────────────────────────────────────────────
    with tabs[5]:
        from mod_admin_compras import render_compras
        render_compras()

    # ── TAB 6: FATURAÇÃO ──────────────────────────────────────────────
    with tabs[6]:
        from mod_admin_faturacao import render_faturacao
        render_faturacao(faturas_db, obras_db)

    # ── TAB 7: ORÇAMENTAÇÃO ───────────────────────────────────────────
    with tabs[7]:
        from mod_admin_orcamentacao import render_orcamentacao
        render_orcamentacao()

    # ── TAB 8: COMERCIAL ──────────────────────────────────────────────
    with tabs[8]:
        from mod_admin_comercial import render_comercial
        render_comercial()

    # ── TAB 9: QUALIDADE ──────────────────────────────────────────────
    with tabs[9]:
        from mod_admin_qualidade import render_qualidade
        render_qualidade()

    # ── TAB 10: PLANEAMENTO ───────────────────────────────────────────
    with tabs[10]:
        from mod_admin_planeamento import render_planeamento
        render_planeamento()

    # ── TAB 11: IT ────────────────────────────────────────────────────
    with tabs[11]:
        from mod_admin_it import render_it
        render_it()

    # ── TAB 12: HSE ───────────────────────────────────────────────────
    with tabs[12]:
        st.markdown("### 🛡️ Segurança e HSE")
        tab_inc, tab_sw = st.tabs(["⚠️ Incidentes", "🚶 Safety Walks"])
        with tab_inc:
            if not incs_db.empty:
                # Filtrar apenas incidentes HSE (excluir avarias)
                hse = incs_db[incs_db.get('Tipo', '') != 'Avaria'] if 'Tipo' in incs_db.columns else incs_db
                cols_show = [c for c in ['ID','Data','Utilizador','Obra','Descricao','Gravidade','Status'] if c in hse.columns]
                st.dataframe(hse[cols_show], use_container_width=True, hide_index=True)
            else:
                st.info("📋 Sem incidentes registados.")
        with tab_sw:
            if not sw_db.empty:
                st.dataframe(sw_db, use_container_width=True, hide_index=True)
            else:
                st.info("📋 Sem safety walks registados.")

    # ── TAB 13: LOGS AUDITORIA ────────────────────────────────────────
    with tabs[13]:
        st.markdown("### 📋 Logs de Auditoria — Compliance SGS/ISO")
        from core import get_audit_logs

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_user = st.selectbox("Filtrar por Utilizador",
                ["Todos"] + users['Nome'].tolist(), key="log_filt_user")
        with col_f2:
            apenas_clientes = st.checkbox("👥 Apenas Clientes", key="log_filt_clientes")
        with col_f3:
            limite = st.number_input("Limite", min_value=10, max_value=1000, value=100, key="log_limite")

        usuario_f = None if filtro_user == "Todos" else filtro_user
        logs_df   = get_audit_logs(filtro_usuario=usuario_f, limite=limite)

        if apenas_clientes and not logs_df.empty:
            logs_df = logs_df[logs_df['Usuario'].str.contains("CLIENTE:", na=False)]

        if not logs_df.empty:
            st.metric("Total Ações", len(logs_df))
            st.divider()
            cols_show = [c for c in ['Data','Hora','Usuario','Acao','Tabela','Registro_ID','Detalhes'] if c in logs_df.columns]
            st.dataframe(logs_df[cols_show], use_container_width=True, hide_index=True)
            csv_logs = logs_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Exportar Logs (CSV)", csv_logs,
                f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv", use_container_width=True
            )
        else:
            st.info("📋 Sem registos de auditoria encontrados.")

    # ── TAB 14: CONFIG EMAIL ──────────────────────────────────────────
    with tabs[14]:
        st.markdown("### 📧 Configuração de Email SMTP")
        st.info("""
        **Para configurar emails:**
        1. Vai ao Google Cloud Console → Secret Manager
        2. Adiciona os secrets: SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME
        3. Reinicia o Cloud Run e volta aqui para testar
        """)

        from core import get_smtp_config, testar_smtp

        config = get_smtp_config()
        if config:
            st.success("✅ SMTP Configurado!")
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.1);border:2px solid #10B981;
                border-radius:10px;padding:20px;">
                <p><strong>Server:</strong> {config['server']}</p>
                <p><strong>Porta:</strong> {config['port']}</p>
                <p><strong>User:</strong> {config['user']}</p>
                <p><strong>From:</strong> {config['from_name']} &lt;{config['from_email']}&gt;</p>
            </div>""", unsafe_allow_html=True)

            st.divider()
            st.markdown("### 🧪 Testar Envio de Email")
            email_teste = st.text_input("Email para teste", placeholder="exemplo@email.com", key="smtp_test_email")
            if st.button("📧 Enviar Email de Teste", use_container_width=True, type="primary"):
                if email_teste:
                    with st.spinner("A enviar..."):
                        if testar_smtp(email_teste):
                            st.success(f"✅ Email de teste enviado para {email_teste}!")
                        else:
                            st.error("❌ Falha ao enviar. Verifica a configuração SMTP.")
                else:
                    st.warning("⚠️ Insere um email para teste.")
        else:
            st.warning("⚠️ SMTP Não Configurado")
            st.markdown("""
            <div style="background:rgba(245,158,11,0.1);border:2px solid #F59E0B;
                border-radius:10px;padding:20px;">
                <p><strong>Passos para configurar:</strong></p>
                <ol style="color:#94A3B8;">
                    <li>Vai ao <a href="https://console.cloud.google.com/security/secret-manager" target="_blank">Google Cloud Secret Manager</a></li>
                    <li>Cria os secrets: SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME</li>
                    <li>Adiciona permissão Secret Accessor ao service account do Cloud Run</li>
                    <li>Reinicia o Cloud Run para carregar os novos secrets</li>
                </ol>
            </div>""", unsafe_allow_html=True)

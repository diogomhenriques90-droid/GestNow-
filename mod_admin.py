import streamlit as st
from core import load_all, inv, ICONS
from datetime import datetime

def render_admin(*args):
    """Hub Principal do Admin - Chama todos os sub-módulos"""
    
    # CSS Global
    st.markdown("""
    <style>
    .stMarkdown, .stText, .stDataFrame, label, div, span, p, h1, h2, h3 { color: #F8FAFC !important; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2));
        border: 2px solid rgba(59,130,246,0.5);
        border-radius: 12px;
        padding: 15px;
    }
    [data-testid="stMetricValue"] { color: #60A5FA !important; }
    [data-testid="stMetricLabel"] { color: #94A3B8 !important; }
    </style>
    """, unsafe_allow_html=True)

    # Desempacotamento das 20 variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    # HEADER
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:30px; border-radius:20px; margin-bottom:30px; border:1px solid rgba(255,255,255,0.2);">
        <h1 style="color:#F8FAFC; margin:0; font-size:2.5rem;">⚡ Painel Administrativo</h1>
        <p style="color:#94A3B8; margin:10px 0 0 0;">Utilizador: <strong style="color:#60A5FA">{st.session_state.user}</strong> | Tipo: <strong style="color:#60A5FA">{st.session_state.tipo}</strong></p>
        <p style="color:#64748B; margin:5px 0 0 0; font-size:0.9rem;">Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)

    # DASHBOARD MÉTRICAS GERAIS
    st.markdown("### 📊 Visão Geral", unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("👷 Técnicos", len(users))
    with c2:
        st.metric("🏭 Obras Ativas", len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0)
    with c3:
        st.metric("⏳ Validações", len(registos_db[registos_db['Status'] == "0"]) if not registos_db.empty else 0)
    with c4:
        st.metric("📋 Pedidos", len(req_fer_db) + len(req_mat_db) + len(req_epi_db))
    with c5:
        st.metric("⚠️ Incidentes", len(incs_db) if not incs_db.empty else 0)
    with c6:
        st.metric("💰 Faturas", len(faturas_db) if not faturas_db.empty else 0)
    
    st.divider()

    # TABS PRINCIPAIS - CADA TAB CHAMA UM SUB-MÓDULO
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
    "📋 Logs Audit"
])

    # ========== TAB 0: VALIDAÇÕES ==========
    with tabs[0]:
        from mod_admin_validacoes import render_validacoes
        render_validacoes(req_fer_db, req_mat_db, req_epi_db, registos_db, users, obras_db)

    # ========== TAB 1: RH ==========
    with tabs[1]:
        from mod_admin_rh import render_rh
        render_rh(users, avals_db, obras_db, inst_acessos_db)

    # ========== TAB 2: OBRAS ==========
    with tabs[2]:
        from mod_admin_obras import render_obras
        render_obras(obras_db, frentes_db, users, inst_acessos_db)

    # ========== TAB 3: FROTA ==========
    with tabs[3]:
        from mod_admin_frota import render_frota
        render_frota()

    # ========== TAB 4: DORMIDAS ==========
    with tabs[4]:
        from mod_admin_dormidas import render_dormidas
        render_dormidas()

    # ========== TAB 5: COMPRAS ==========
    with tabs[5]:
        from mod_admin_compras import render_compras
        render_compras()

    # ========== TAB 6: FATURAÇÃO ==========
    with tabs[6]:
        from mod_admin_faturacao import render_faturacao
        render_faturacao(faturas_db, obras_db)

    # ========== TAB 7: ORÇAMENTAÇÃO ==========
    with tabs[7]:
        from mod_admin_orcamentacao import render_orcamentacao
        render_orcamentacao()

    # ========== TAB 8: COMERCIAL ==========
    with tabs[8]:
        from mod_admin_comercial import render_comercial
        render_comercial()

    # ========== TAB 9: QUALIDADE ==========
    with tabs[9]:
        from mod_admin_qualidade import render_qualidade
        render_qualidade()

    # ========== TAB 10: PLANEAMENTO ==========
    with tabs[10]:
        from mod_admin_planeamento import render_planeamento
        render_planeamento()

    # ========== TAB 11: IT ==========
    with tabs[11]:  # Ou o número correto conforme a ordem
        from mod_admin_it import render_it
        render_it()

    # ========== TAB 12: HSE ==========
    with tabs[12]:
        st.markdown("### 🛡️ Segurança e HSE", unsafe_allow_html=True)
        tab_inc, tab_sw = st.tabs(["⚠️ Incidentes", "🚶 Safety Walks"])
        with tab_inc:
            if not incs_db.empty:
                st.dataframe(incs_db, use_container_width=True)
            else:
                st.info("📋 Sem incidentes registados.")
        with tab_sw:
            if not sw_db.empty:
                st.dataframe(sw_db, use_container_width=True)
            else:
                st.info("📋 Sem safety walks registados.")

    
       # ========== TAB 13: LOGS DE AUDITORIA ==========
    with tabs[13]:
        st.markdown("### 📋 Logs de Auditoria - Compliance SGS/ISO", unsafe_allow_html=True)
        
        from core import get_audit_logs
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_usuario = st.selectbox(
                "Filtrar por Utilizador",
                ["Todos"] + users['Nome'].tolist(),
                key="log_filt_user"
            )
        with col_f2:
            limite = st.number_input("Limite de Registos", min_value=10, max_value=1000, value=100, key="log_limite")
        
        usuario_f = None if filtro_usuario == "Todos" else filtro_usuario
        
        logs_df = get_audit_logs(filtro_usuario=usuario_f, limite=limite)
        
        if not logs_df.empty:
            st.metric("Total Ações", len(logs_df))
            st.divider()
            st.dataframe(logs_df[['Data', 'Hora', 'Usuario', 'Acao', 'Tabela', 'Registro_ID', 'Detalhes']], use_container_width=True, hide_index=True)
            
            csv_logs = logs_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Exportar Logs (CSV)",
                csv_logs,
                f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.info("📋 Sem registos de auditoria encontrados.")

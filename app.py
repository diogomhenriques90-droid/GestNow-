import streamlit as st
from core import init_session, check_timeout, load_all, inject_pwa_meta, inject_global_css, datetime, ICONS
from translations import init_language, t, get_language_options, set_language

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA (PWA + BRANDING INDUSTRIAL)
# =============================================================================
st.set_page_config(
    page_title="GESTNOW v3 - Instrumentação Industrial",
    page_icon=ICONS["app"],
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/seu-org/gestnow-v3',
        'Report a bug': "https://github.com/seu-org/gestnow-v3/issues",
        'About': "# GESTNOW v3\nSistema de Gestão de Instrumentação Industrial"
    }
)

# Injetar PWA meta tags
inject_pwa_meta()

# Injetar CSS global do design system
inject_global_css()

# =============================================================================
# 2. INICIALIZAR SESSÃO E TIMEOUT
# =============================================================================
init_session()
check_timeout()
init_language()

# =============================================================================
# 3. SIDEBAR (APENAS SE LOGADO)
# =============================================================================
if st.session_state.get('user'):
    with st.sidebar:
        # Header com branding
        st.markdown(f"""
        <div style="text-align:center; padding:20px; background:linear-gradient(135deg, #1E293B, #0F172A); border-radius:16px; margin-bottom:20px;">
            <div style="font-size:3rem; margin-bottom:10px;">{ICONS["app"]}</div>
            <div style="font-size:1.2rem; font-weight:700; color:#F8FAFC;">GESTNOW v3</div>
            <div style="font-size:0.8rem; color:#94A3B8;">Instrumentação Industrial</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Perfil do utilizador
        st.markdown(f"""
        <div style="padding:12px; background:rgba(255,255,255,0.05); border-radius:12px; margin-bottom:16px;">
            <div style="font-size:1rem; font-weight:600; color:#F8FAFC;">👤 {st.session_state.user}</div>
            <div style="font-size:0.85rem; color:#94A3B8;">{ICONS["profile"]} {st.session_state.tipo}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Seletor de Idioma
        st.markdown(f"**{ICONS['app']} {t('language')}**")
        lang_opts = get_language_options()
        curr_lang = st.session_state.language
        sel_lang = st.selectbox(
            "🌐", 
            options=list(lang_opts.keys()), 
            format_func=lambda x: lang_opts[x],
            index=list(lang_opts.keys()).index(curr_lang),
            label_visibility="collapsed"
        )
        if sel_lang != curr_lang:
            set_language(sel_lang)
            st.rerun()
        
        st.divider()
        
        # Menu de Navegação (dinâmico por perfil)
        st.markdown(f"**📋 {t('dashboard')}**")
        
        tipo = st.session_state.get('tipo', '')
        
        if tipo == 'Admin':
            menu_item = st.radio(
                "Navegação",
                [f"{ICONS['dashboard']} Dashboard", f"{ICONS['admin']} Admin", f"{ICONS['logout']} Logout"],
                label_visibility="collapsed"
            )
            st.session_state.menu_selected = menu_item
        else:
            # Técnico/Instrumentista
            menu_item = st.radio(
                "Navegação",
                [f"{ICONS['technician']} Obra", f"{ICONS['dashboard']} Dashboard", f"{ICONS['logout']} Logout"],
                label_visibility="collapsed"
            )
            st.session_state.menu_selected = menu_item
        
        st.divider()
        
        # Botão de Logout
        if st.button(f"{ICONS['logout']} {t('logout')}", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()
        
        # Footer
        st.markdown("""
        <div style="position:fixed; bottom:20px; left:20px; right:20px; text-align:center; font-size:0.75rem; color:#64748B;">
            GESTNOW v3.0<br>
            Instrumentação Industrial
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# 4. ROUTING PRINCIPAL
# =============================================================================
if not st.session_state.get('user'):
    # =============================================================================
    # PÁGINA DE LOGIN
    # =============================================================================
    from mod_login import render_login
    
    # Header de login com branding
    st.markdown("""
    <style>
    .login-header {
        text-align:center;
        padding:40px 20px;
        background:linear-gradient(135deg, #1E293B, #0F172A);
        border-radius:20px;
        margin-bottom:30px;
    }
    .login-logo {
        font-size:4rem;
        margin-bottom:10px;
    }
    .login-title {
        font-size:2rem;
        font-weight:800;
        color:#F8FAFC;
        margin-bottom:8px;
    }
    .login-subtitle {
        font-size:1rem;
        color:#94A3B8;
    }
    </style>
    <div class="login-header">
        <div class="login-logo">🎛️</div>
        <div class="login-title">GESTNOW v3</div>
        <div class="login-subtitle">Gestão de Instrumentação Industrial</div>
    </div>
    """, unsafe_allow_html=True)
    
    render_login()
    
else:
    # =============================================================================
    # APLICAÇÃO PRINCIPAL (LOGADO)
    # =============================================================================
    
    # Carregar Dados Globais (20 DataFrames)
    DATA = load_all()
    
    # Desempacotar dados necessários
    (users, obras_db, frentes_db, registos_db, fats, docs, incs, sw, obs, equip,
     diags, diags_u, folhas, comuns, comuns_u, req_fer, req_mat, req_epi, avals, inst_acessos_db) = DATA
    
    tipo = st.session_state.get('tipo', '')
    user_nome = st.session_state.get('user', '')
    
    # Verificar acesso a instrumentação
    tem_inst = False
    if not inst_acessos_db.empty:
        acesso_inst = inst_acessos_db[
            (inst_acessos_db['Utilizador'] == user_nome) & 
            (inst_acessos_db['Ativo'].isin(['Sim', 'Ativo', 'True']))
        ]
        tem_inst = not acesso_inst.empty
    
    # =============================================================================
    # ROUTING POR PERFIL
    # =============================================================================
    
    if tipo == 'Admin':
        # =============================================================================
        # MODO ADMIN
        # =============================================================================
        menu = st.session_state.get('menu_selected', f"{ICONS['dashboard']} Dashboard")
        
        if f"{ICONS['admin']} Admin" in menu:
            st.markdown(f"# {ICONS['admin']} Painel Administrativo")
            from mod_admin import render_admin
            render_admin(*DATA)
        else:
            st.markdown(f"# {ICONS['dashboard']} Dashboard Geral")
            # Dashboard simplificado para admin
            st.info("Dashboard em desenvolvimento...")
    
    else:
        # =============================================================================
        # MODO TÉCNICO / INSTRUMENTISTA
        # =============================================================================
        menu = st.session_state.get('menu_selected', f"{ICONS['technician']} Obra")
        
        if f"{ICONS['technician']} Obra" in menu:
            # Módulo Técnico (Registo de Ponto, HSE, etc.)
            st.markdown(f"# {ICONS['technician']} Área Técnica")
            from mod_tecnico import render_tecnico
            render_tecnico(*DATA)
            
        elif f"{ICONS['dashboard']} Dashboard" in menu:
            # Dashboard com métricas
            st.markdown(f"# {ICONS['dashboard']} Dashboard de Produção")
            
            # Selecionar obra
            if not obras_db.empty:
                obras_list = obras_db[obras_db['Ativa'] == 'Ativa']['Obra'].tolist()
                if obras_list:
                    obra_sel = st.selectbox("🏗️ Selecionar Obra", obras_list)
                    st.session_state.obra_ativa = obra_sel
                    
                    # Métricas simples
                    st.markdown("### 📊 Métricas da Obra")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("⏱️ Horas Totais", "0h")
                    with col2:
                        st.metric("👷 Técnicos", users['Nome'].nunique())
                    with col3:
                        st.metric("️ Obras Ativas", len(obras_list))
                else:
                    st.warning("⚠️ Nenhuma obra ativa encontrada.")
            else:
                st.info("📋 Sem obras registadas.")
        
        else:
            # Logout
            st.session_state.clear()
            st.rerun()

# =============================================================================
# 5. FOOTER GLOBAL
# =============================================================================
st.markdown("""
<style>
.footer {
    position:fixed;
    bottom:0;
    left:0;
    right:0;
    background:linear-gradient(135deg, #1E293B, #0F172A);
    padding:12px 20px;
    text-align:center;
    font-size:0.8rem;
    color:#64748B;
    border-top:1px solid rgba(255,255,255,0.1);
}
</style>
<div class="footer">
    {ICONS["app"]} GESTNOW v3.0 - Sistema de Gestão de Instrumentação Industrial | 
    Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}
</div>
""", unsafe_allow_html=True)

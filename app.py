import streamlit as st
from core import init_session, check_timeout, load_all, inject_pwa_meta, inject_global_css, datetime, ICONS
from translations import init_language, t, get_language_options, set_language

try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# =============================================================================
st.set_page_config(
    page_title="GESTNOW v3 - Instrumentação Industrial",
    page_icon=ICONS["app"],
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help':    'https://github.com/diogomhenriques90-droid/GestNow',
        'Report a bug':"https://github.com/diogomhenriques90-droid/GestNow/issues",
        'About':       "# GESTNOW v3\nSistema de Gestão de Instrumentação Industrial"
    }
)

inject_pwa_meta()
inject_global_css()
init_session()
check_timeout()
init_language()

# =============================================================================
# 2. ROUTING — Páginas Especiais
# =============================================================================
page = st.query_params.get("page", "")

if page == "criar_admin":
    from criar_admin import render_criar_admin
    render_criar_admin()
    st.stop()

# =============================================================================
# 3. SIDEBAR (APENAS SE LOGADO — DESKTOP)
# =============================================================================
if st.session_state.get('user'):
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:20px;
            background:linear-gradient(135deg,#1E293B,#0F172A);
            border-radius:16px;margin-bottom:20px;">
            <div style="font-size:3rem;margin-bottom:10px;">{ICONS["app"]}</div>
            <div style="font-size:1.2rem;font-weight:700;color:#F8FAFC;">GESTNOW v3</div>
            <div style="font-size:0.8rem;color:#94A3B8;">Instrumentação Industrial</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="padding:12px;background:rgba(255,255,255,0.05);border-radius:12px;margin-bottom:16px;">
            <div style="font-size:1rem;font-weight:600;color:#F8FAFC;">👤 {st.session_state.user}</div>
            <div style="font-size:0.85rem;color:#94A3B8;">{st.session_state.tipo} | {st.session_state.cargo}</div>
        </div>
        """, unsafe_allow_html=True)

        # Seletor de Idioma
        st.markdown(f"**{ICONS['app']} {t('language')}**")
        lang_opts  = get_language_options()
        curr_lang  = st.session_state.language
        sel_lang   = st.selectbox(
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
        st.markdown("**📋 Navegação**")

        tipo  = st.session_state.get('tipo', '')
        cargo = st.session_state.get('cargo', '')

        tem_acesso_inst = (tipo in ['Chefe de Equipa','Admin','Gestor'] or
                           cargo in ['Chefe de Equipa','Encarregado','Instrumentista'])
        eh_cliente = (tipo == 'Cliente')

        if eh_cliente:
            menu_item = st.radio("Navegação",
                [f"{ICONS['dashboard']} Portal", f"{ICONS['logout']} Logout"],
                label_visibility="collapsed")
        elif tipo == 'Admin':
            menu_item = st.radio("Navegação",
                [f"{ICONS['dashboard']} Dashboard",
                 f"{ICONS['admin']} Admin",
                 f"{ICONS['instrumentation']} Instrumentação",
                 f"{ICONS['profile']} Perfil",
                 f"{ICONS['logout']} Logout"],
                label_visibility="collapsed")
        elif tem_acesso_inst:
            menu_item = st.radio("Navegação",
                [f"{ICONS['dashboard']} Início",
                 f"{ICONS['technician']} Obra",
                 f"{ICONS['instrumentation']} Instrumentação",
                 f"{ICONS['profile']} Perfil",
                 f"{ICONS['logout']} Logout"],
                label_visibility="collapsed")
        else:
            menu_item = st.radio("Navegação",
                [f"{ICONS['dashboard']} Início",
                 f"{ICONS['technician']} Obra",
                 f"{ICONS['profile']} Perfil",
                 f"{ICONS['logout']} Logout"],
                label_visibility="collapsed")

        st.session_state.menu_selected = menu_item
        st.divider()

        if st.button(f"{ICONS['logout']} {t('logout')}", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()

# =============================================================================
# 4. BOTTOM NAVIGATION BAR (MOBILE-FIRST)
# =============================================================================
if st.session_state.get('user') and HAS_OPTION_MENU:
    tipo  = st.session_state.get('tipo', '')
    cargo = st.session_state.get('cargo', '')
    eh_cliente = (tipo == 'Cliente')

    if eh_cliente:
        nav_options = ["Portal", "Logout"]
        nav_icons   = ["house", "box-arrow-right"]
    elif tipo == 'Admin':
        # ✅ CORRIGIDO: Admin tem Instrumentação na bottom nav
        nav_options = ["Dashboard", "Admin", "Instrumentação", "Perfil", "Logout"]
        nav_icons   = ["graph-up", "gear", "tools", "person", "box-arrow-right"]
    elif tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
        nav_options = ["Início", "Obra", "Instrumentação", "Perfil", "Logout"]
        nav_icons   = ["house", "tools", "wrench", "person", "box-arrow-right"]
    else:
        nav_options = ["Início", "Obra", "Perfil", "Logout"]
        nav_icons   = ["house", "tools", "person", "box-arrow-right"]

    # Determinar índice default
    current_menu = st.session_state.get('menu_selected', '')
    default_index = 0

    if tipo == 'Admin':
        if "Admin" in current_menu:
            default_index = 1
        elif "Instrumentação" in current_menu:
            default_index = 2
        elif "Perfil" in current_menu:
            default_index = 3
        else:
            default_index = 0
    elif tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
        if "Obra" in current_menu:
            default_index = 1
        elif "Instrumentação" in current_menu:
            default_index = 2
        elif "Perfil" in current_menu:
            default_index = 3
        else:
            default_index = 0
    else:
        if "Obra" in current_menu:
            default_index = 1
        elif "Perfil" in current_menu:
            default_index = 2
        else:
            default_index = 0

    selected = option_menu(
        menu_title=None,
        options=nav_options,
        icons=nav_icons,
        menu_icon="cast",
        default_index=default_index,
        orientation="horizontal",
        styles={
            "container":        {"padding":"0!important","background-color":"#1E293B","position":"fixed","bottom":"0","width":"100%","z-index":"999","border-top":"1px solid rgba(255,255,255,0.1)"},
            "icon":             {"color":"#F8FAFC","font-size":"20px"},
            "nav-link":         {"color":"#F8FAFC","font-size":"11px","margin":"0px","text-align":"center","padding":"8px 4px"},
            "nav-link-selected":{"background-color":"#DC2626","color":"#FFFFFF"},
        }
    )

    # ✅ Mapeamento robusto usando chaves fixas
    nav_map = {
        "Início":        f"{ICONS['dashboard']} Início",
        "Portal":        f"{ICONS['dashboard']} Portal",
        "Obra":          f"{ICONS['technician']} Obra",
        "Instrumentação":f"{ICONS['instrumentation']} Instrumentação",
        "Dashboard":     f"{ICONS['dashboard']} Dashboard",
        "Admin":         f"{ICONS['admin']} Admin",
        "Perfil":        f"{ICONS['profile']} Perfil",
        "Logout":        "Logout",
    }

    new_menu = nav_map.get(selected, '')
    if new_menu and new_menu != st.session_state.get('menu_selected', ''):
        st.session_state.menu_selected = new_menu
        if selected == "Logout":
            st.session_state.clear()
        st.rerun()

    st.markdown("<div style='height:70px;'></div>", unsafe_allow_html=True)

# =============================================================================
# 5. ROUTING PRINCIPAL
# =============================================================================
if not st.session_state.get('user'):
    from mod_login import render_login
    render_login()

else:
    DATA = load_all()
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = DATA

    tipo      = st.session_state.get('tipo', '')
    user_nome = st.session_state.get('user', '')
    cargo     = st.session_state.get('cargo', '')

    tem_acesso_inst = (tipo in ['Chefe de Equipa','Admin','Gestor'] or
                       cargo in ['Chefe de Equipa','Encarregado','Instrumentista'])
    eh_cliente = (tipo == 'Cliente')

    menu = st.session_state.get('menu_selected', '')

    # Logout via sidebar
    if "Logout" in menu:
        st.session_state.clear()
        st.rerun()

    # ── MODO CLIENTE ─────────────────────────────────────────────────
    if eh_cliente:
        if "Portal" in menu:
            st.markdown(f"# {ICONS['dashboard']} Portal do Cliente")
            from mod_cliente import render_cliente_portal
            render_cliente_portal()
        else:
            # Default: portal
            st.markdown(f"# {ICONS['dashboard']} Portal do Cliente")
            from mod_cliente import render_cliente_portal
            render_cliente_portal()

    # ── MODO ADMIN ───────────────────────────────────────────────────
    elif tipo == 'Admin':
        if f"{ICONS['admin']} Admin" in menu or "Admin" in menu:
            from mod_admin import render_admin
            render_admin(*DATA)

        elif f"{ICONS['instrumentation']} Instrumentação" in menu or "Instrumentação" in menu:
            st.markdown(f"# {ICONS['instrumentation']} Instrumentação Industrial")
            from mod_instrumentacao import render_instrumentacao
            render_instrumentacao(*DATA)

        elif f"{ICONS['profile']} Perfil" in menu or ("Perfil" in menu and "Admin" not in menu):
            st.markdown(f"# {ICONS['profile']} Perfil do Utilizador")
            from mod_perfil import render_perfil
            render_perfil(*DATA)

        else:
            # Default Admin — Dashboard
            st.markdown(f"# {ICONS['dashboard']} Dashboard Geral")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("👥 Utilizadores", len(users))
            with c2: st.metric("🏭 Obras Ativas",
                len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0)
            with c3: st.metric("📋 Registos", len(registos_db) if not registos_db.empty else 0)
            with c4: st.metric("⚠️ Incidentes", len(incs_db) if not incs_db.empty else 0)

            st.divider()
            from mod_dashboard import render_dashboard
            render_dashboard(*DATA)

    # ── MODO TÉCNICO / CHEFE ─────────────────────────────────────────
    else:
        if f"{ICONS['dashboard']} Início" in menu or "Início" in menu or menu == '':
            from mod_inicio import render_inicio
            render_inicio(*DATA)

        elif f"{ICONS['technician']} Obra" in menu or "Obra" in menu:
            st.markdown(f"# {ICONS['technician']} Área Técnica")
            if tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
                from mod_chefe import render_chefe
                render_chefe(*DATA)
            else:
                from mod_tecnico import render_tecnico
                render_tecnico(*DATA)

        elif f"{ICONS['instrumentation']} Instrumentação" in menu or "Instrumentação" in menu:
            if tem_acesso_inst:
                st.markdown(f"# {ICONS['instrumentation']} Instrumentação Industrial")
                from mod_instrumentacao import render_instrumentacao
                render_instrumentacao(*DATA)
            else:
                st.warning("⚠️ Não tem acesso a este módulo.")

        elif f"{ICONS['profile']} Perfil" in menu or "Perfil" in menu:
            st.markdown(f"# {ICONS['profile']} Perfil do Utilizador")
            from mod_perfil import render_perfil
            render_perfil(*DATA)

        else:
            # Default técnico
            from mod_inicio import render_inicio
            render_inicio(*DATA)

# =============================================================================
# 6. FOOTER GLOBAL
# =============================================================================
st.markdown("""
<style>
.footer {
    position:fixed; bottom:60px; left:0; right:0;
    background:linear-gradient(135deg,#1E293B,#0F172A);
    padding:12px 20px; text-align:center;
    font-size:0.75rem; color:#64748B;
    border-top:1px solid rgba(255,255,255,0.1); z-index:9998;
}
@media (max-width:768px) { .footer { display:none; } }
</style>
<div class="footer">
    🎛️ GESTNOW v3.0 — Sistema de Gestão de Instrumentação Industrial
</div>
""", unsafe_allow_html=True)

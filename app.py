import streamlit as st
from core import init_session, check_timeout, load_all, inject_pwa_meta, datetime
from translations import init_language, t, get_language_options, set_language

# 1. Configuração Única e PWA
st.set_page_config(page_title="GESTNOW v3", page_icon="🏗️", layout="wide")
inject_pwa_meta()

# 2. Inicializar Sessão
init_session()
check_timeout()
init_language()

# 3. Sidebar (Apenas se Logado)
if st.session_state.get('user'):
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.caption(f"Perfil: {st.session_state.tipo}")
        
        # Seletor de Idioma
        lang_opts = get_language_options()
        curr_lang = st.session_state.language
        sel_lang = st.selectbox("🌐", options=list(lang_opts.keys()), 
                                format_func=lambda x: lang_opts[x],
                                index=list(lang_opts.keys()).index(curr_lang))
        if sel_lang != curr_lang:
            set_language(sel_lang)
            st.rerun()
        
        st.divider()
        if st.button(t('logout'), use_container_width=True):
            st.session_state.clear()
            st.rerun()

# 4. Routing
if not st.session_state.get('user'):
    from mod_login import render_login
    render_login()
else:
    # Carregar Dados Globais
    DATA = load_all()
    tipo = st.session_state.get('tipo', '')

    if tipo == "Admin":
        from mod_admin import render_admin
        render_admin(*DATA)
    else:
        # Se Técnico, pode haver opção de trocar de módulo se tiver acesso a Inst.
        inst_acessos_db = DATA[19]
        tem_inst = not inst_acessos_db[(inst_acessos_db['Utilizador'] == st.session_state.user) & (inst_acessos_db['Ativo'] == 'Sim')].empty
        
        if tem_inst:
            mod_sel = st.sidebar.radio("Módulo", ["🏗️ Obra", "🔧 Instrumentação", "📊 Dashboard"])
            if mod_sel == "🔧 Instrumentação":
                from mod_instrumentacao import render_instrumentacao
                render_instrumentacao(*DATA)
            elif mod_sel == "📊 Dashboard":
                from mod_dashboard import render_dashboard_completo
                # Busca obra selecionada no estado
                obra_sel = st.session_state.get('obra_ativa', 'Geral')
                render_dashboard_completo(obra_sel, *DATA)
            else:
                from mod_tecnico import render_tecnico
                render_tecnico(*DATA)
        else:
            from mod_tecnico import render_tecnico
            render_tecnico(*DATA)

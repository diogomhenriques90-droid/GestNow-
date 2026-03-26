"""
GESTNOW v3 — app.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PONTO DE ENTRADA. Este ficheiro não tem lógica de negócio.

Faz apenas 4 coisas:
  1. Importa os módulos
  2. Inicializa a sessão e verifica timeout
  3. Carrega dados (load_all do core.py)
  4. Routing: decide qual módulo renderizar

Para alterar qualquer funcionalidade → editar o módulo correspondente.
Para dados novos → core.py (load_all + save_db).
Para novo ecrã inteiro (ex: fornecedores) → criar mod_fornecedores.py
                                              e adicionar uma linha de routing aqui.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from core import (
    st, datetime, load_all, inv,
    init_session, check_timeout
)
from mod_login import render_login
from mod_admin import render_admin
from mod_tecnico import render_tecnico
from translations import t, init_language, set_language, get_language_options

# Import do módulo de instrumentação (já existente)
try:
    from mod_instrumentacao import render_instrumentacao
except Exception as _e:
    _erro_inst = str(_e)
    def render_instrumentacao(**DB):
        st.error(f"❌ Erro ao carregar módulo de instrumentação: {_erro_inst}")

# Import do novo módulo de dashboard
try:
    from mod_dashboard import render_dashboard_completo
except Exception as _e:
    def render_dashboard_completo(**kwargs):
        st.error(f"❌ Erro ao carregar dashboard: {_e}")

# ── 1. Inicializar sessão ────────────────────────────────────────────────────
init_session()
check_timeout()
init_language()  # Inicializa o idioma para traduções

# ── 2. Sidebar (só quando autenticado) ──────────────────────────────────────
if st.session_state.get('user'):
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.caption(f"Tipo: {st.session_state.tipo}")
        
        # ──────────────────────────────────────────────────────────
        # SELETOR DE IDIOMA (canto superior direito)
        # ──────────────────────────────────────────────────────────
        col_lang1, col_lang2 = st.columns([3, 1])
        with col_lang1:
            st.markdown(f"🌐 {t('language')}")
        with col_lang2:
            current_lang = st.session_state.get("language", "pt")
            lang_options = get_language_options()
            selected_lang = st.selectbox(
                "",
                options=list(lang_options.keys()),
                format_func=lambda x: lang_options[x],
                index=list(lang_options.keys()).index(current_lang),
                key="language_selector",
                label_visibility="collapsed"
            )
            if selected_lang != current_lang:
                set_language(selected_lang)
                st.rerun()
        
        st.divider()
        
        # Botão de reiniciar dados
        if st.button("🔄 Reiniciar dados locais", use_container_width=True,
                     help="Limpa cache e força resincronização"):
            st.session_state['reiniciar_dados'] = True
        if st.session_state.get('reiniciar_dados'):
            st.markdown("<div style='background:white;padding:1rem;border-radius:12px;text-align:center;'>",
                        unsafe_allow_html=True)
            st.warning("⚠️ Limpar dados locais e atualizar?")
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                if st.button("✅ Confirmar", key="reiniciar_sim", use_container_width=True):
                    load_all.clear()
                    for k in list(st.session_state.keys()):
                        if k not in ['user','tipo','cargo','session_token','language']:
                            del st.session_state[k]
                    st.success("✅ Dados reiniciados!")
                    st.rerun()
            with c_r2:
                if st.button("✕ Cancelar", key="reiniciar_nao", use_container_width=True):
                    st.session_state['reiniciar_dados'] = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.divider()
        
        # Botão de terminar sessão
        if st.button("🚪 Terminar Sessão", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        st.divider()
        st.caption(f"Sessão: {st.session_state.get('last_activity', datetime.now()).strftime('%d/%m/%Y %H:%M')}")

# ── 3. Routing ───────────────────────────────────────────────────────────────
if not st.session_state.get('user'):
    # ── Não autenticado → login
    render_login()

else:
    # ── Autenticado → carregar dados
    (users, obras_db, frentes_db, registos_db, faturas_db,
     docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db,
     comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db,
     inst_acessos_db) = load_all()

    DB = dict(
        users=users, obras_db=obras_db, frentes_db=frentes_db,
        registos_db=registos_db, faturas_db=faturas_db,
        docs_db=docs_db, incs_db=incs_db, sw_db=sw_db,
        obs_db=obs_db, equip_db=equip_db,
        diags_db=diags_db, diags_u_db=diags_u_db, folhas_db=folhas_db,
        comuns_db=comuns_db, comuns_u_db=comuns_u_db,
        req_fer_db=req_fer_db, req_mat_db=req_mat_db, req_epi_db=req_epi_db,
        avals_db=avals_db,
        inst_acessos_db=inst_acessos_db,
    )

    # ── Routing por tipo de utilizador
    tipo = st.session_state.get('tipo', '')

    if tipo == "Admin":
        render_admin(**DB)
    else:
        # Verificar se o utilizador tem acesso a obra de instrumentação
        user_atual = st.session_state.get('user','')
        tem_acesso_inst = False
        if not inst_acessos_db.empty:
            acesso = inst_acessos_db[
                (inst_acessos_db['Utilizador'] == user_atual) &
                (inst_acessos_db['Ativo'].isin(['Sim','sim','1','true','True']))
            ]
            tem_acesso_inst = not acesso.empty

        # Selector de módulo se tiver acesso a instrumentação
        if tem_acesso_inst:
            modulo = st.sidebar.radio(
                "📱 Módulo",
                ["🏗️ Gestão de Obra", "🔧 Instrumentação", "📊 Dashboard"],
                key="modulo_sel"
            )
            
            if modulo == "🔧 Instrumentação":
                render_instrumentacao(**DB)
            elif modulo == "📊 Dashboard":
                # Importar função auxiliar do módulo de instrumentação para carregar dados
                from mod_instrumentacao import _load_inst
                
                # Obter obra selecionada (precisa ser definida no módulo de instrumentação)
                obra_sel = st.session_state.get('obra_sel', '')
                if obra_sel:
                    obra_key = obra_sel.replace(' ', '_').replace('/', '_')
                    insts, hookups, bom, packing, itr_a, itr_b, punch = _load_inst(obra_key)
                    
                    # Obter código da obra
                    obra_cod = ""
                    if not obras_db.empty and obra_sel in obras_db['Obra'].values:
                        obra_cod = obras_db[obras_db['Obra']==obra_sel].iloc[0].get('Codigo','')
                    
                    render_dashboard_completo(
                        obra_sel=obra_sel,
                        obra_cod=obra_cod,
                        insts=insts,
                        packing=packing,
                        bom=bom,
                        hookups=hookups,
                        punch=punch,
                        itr_a=itr_a,
                        itr_b=itr_b,
                        user_atual=user_atual,
                        obra_key=obra_key
                    )
                else:
                    st.warning("⚠️ Selecione uma obra no módulo de Instrumentação primeiro.")
                    st.info("Vá ao módulo 'Instrumentação', escolha uma obra e depois volte ao Dashboard.")
            else:
                render_tecnico(**DB)
        else:
            render_tecnico(**DB)

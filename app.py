import streamlit as st
import base64, time
from datetime import datetime
from core import (init_session, check_timeout, load_all, inject_pwa_meta,
                  inject_global_css, hp, save_db, log_audit,
                  criar_notificacao, _gcs_read, inv, tem_permissao,
                  _verificar_alerta_backup, _registar_backup, THEME,
                  # FIX 1 — importar a versão cached de core em vez de redefinir
                  _load_users_cached)
from translations import init_language, t, get_language_options, set_language

st.set_page_config(
    page_title="GestNow — CPS Smart Solutions",
    page_icon="assets/icone_cps_192.png",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help':    'https://github.com/diogomhenriques90-droid/GestNow',
        'Report a bug':"https://github.com/diogomhenriques90-droid/GestNow/issues",
        'About':       "# GESTNOW v3\nSistema de Gestão de Instrumentação Industrial"
    }
)

st.logo("assets/logo_cps_transparente.png",
        icon_image="assets/icone_cps_192.png", size="large")

inject_pwa_meta()
inject_global_css()

st.markdown("""
<style>
.stApp { transition: none !important; }
[data-testid="stAppViewContainer"] { transition: none !important; }
iframe { transition: none !important; }
</style>
""", unsafe_allow_html=True)

init_session()
check_timeout()
init_language()

from streamlit_autorefresh import st_autorefresh

if st.session_state.get('user'):
    st_autorefresh(interval=300000, limit=None, key="auto_refresh")


def _verificar_password_provisoria(user_nome):
    """Password gerada em massa (ou individualmente) pelo RH nasce sempre
    provisória (Password_Provisoria=Sim). Bloqueia tudo — sem forma de
    contornar — até a pessoa definir uma password própria. Corre logo a
    seguir ao login, antes de qualquer outro ecrã ou bloqueio, e para
    qualquer Tipo (incluindo Admin) — simétrico ao
    _verificar_pin_provisorio do cps-ponto."""
    try:
        uc = _load_users_cached()
        if uc.empty: return False
        m = uc[uc['Nome'] == user_nome]
        if m.empty: return False
        r = m.iloc[0]
        if str(r.get('Password_Provisoria', '')).strip() != 'Sim':
            return False
    except Exception:
        return False

    st.markdown(f"""
    <div style="background:{THEME['surface']};border:1px solid {THEME['border']};
        border-radius:{THEME['radius']};padding:25px;margin-bottom:25px;text-align:center;">
        <h2 style="color:{THEME['text']};margin:0 0 8px 0;">Password provisória</h2>
        <p style="color:{THEME['text_secondary']};margin:0;font-size:1rem;">
            Esta password foi-te atribuída pelo RH e é provisória.<br>
            Define uma password só tua para continuar.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_password_provisoria", clear_on_submit=False):
        nova = st.text_input("Nova Password", type="password", key="npp_nova_pwd")
        conf = st.text_input("Confirmar Nova Password", type="password", key="npp_conf_pwd")
        submetido = st.form_submit_button(
            "Definir Password", use_container_width=True, type="primary"
        )

    if submetido:
        if len(nova) < 8:
            st.error("Mínimo 8 caracteres.")
        elif nova != conf:
            st.error("As passwords não coincidem.")
        else:
            up = _load_users_cached().copy()
            mk = up['Nome'] == user_nome
            if mk.any():
                up.loc[mk, 'Password']            = hp(nova)
                up.loc[mk, 'Password_Provisoria'] = ''
                save_db(up, "usuarios.csv")
                inv("usuarios.csv")
            st.success("Password definida. A continuar...")
            st.rerun()
    st.stop()
    return True


# =============================================================================
# SIDEBAR
# =============================================================================
if st.session_state.get('user'):
    with st.sidebar:
        # Logótipo mostrado só via st.logo() (topo da barra lateral,
        # já cobre também o caso da barra colapsada) — o segundo
        # logótipo embutido aqui manualmente foi removido por ser
        # redundante (Identidade Visual, Fase 2).
        st.markdown(f"""
        <div style="padding:12px;background:{THEME['surface']};border:1px solid {THEME['border']};
            border-radius:12px;margin-bottom:16px;">
            <div style="font-size:1rem;font-weight:600;color:{THEME['text']};">
                {st.session_state.user}
            </div>
            <div style="font-size:0.85rem;color:{THEME['text_secondary']};">
                {st.session_state.tipo} | {st.session_state.cargo}
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"**{t('language')}**")
        lang_opts = get_language_options()
        curr_lang = st.session_state.language
        sel_lang  = st.selectbox(
            t('language'), options=list(lang_opts.keys()),
            format_func=lambda x: lang_opts[x],
            index=list(lang_opts.keys()).index(curr_lang),
            label_visibility="collapsed", key="sidebar_language_sel"
        )
        if sel_lang != curr_lang:
            set_language(sel_lang)
            st.rerun()

        st.divider()
        tipo  = st.session_state.get('tipo', '')
        cargo = st.session_state.get('cargo', '')
        tem_acesso_inst = (tipo in ['Chefe de Equipa','Admin','Gestor'] or
                           cargo in ['Chefe de Equipa','Encarregado','Instrumentista'])
        eh_cliente = (tipo == 'Cliente')

        if eh_cliente:
            menu_item = st.radio("Nav",
                [f"Portal", "Logout"],
                label_visibility="collapsed", key="sidebar_nav_cliente")
        elif tipo == 'Admin':
            _opts_admin = [f"Dashboard", f"Admin",
                           f"Instrumentação",
                           f"Perfil"]
            # Dashboard de Obra — mesma condição da barra inferior (super-admin vê sempre)
            if tem_permissao(st.session_state.get('user', ''), 'mod_dashboard_obra'):
                _opts_admin.append(f"Dashboard de Obra")
            _opts_admin.append("Logout")
            menu_item = st.radio("Nav", _opts_admin,
                label_visibility="collapsed", key="sidebar_nav_admin")
        elif tem_acesso_inst:
            menu_item = st.radio("Nav",
                [f"Início", f"Obra",
                 f"Instrumentação",
                 f"Perfil", "Logout"],
                label_visibility="collapsed", key="sidebar_nav_chefe")
        else:
            menu_item = st.radio("Nav",
                [f"Início", f"Obra",
                 f"Perfil", "Logout"],
                label_visibility="collapsed", key="sidebar_nav_tecnico")

        if not st.session_state.get('_menu_locked', False):
            st.session_state.menu_selected = menu_item

        st.divider()
        if st.button("Atualizar Dados", use_container_width=True,
                     type="secondary", key="sidebar_refresh_btn"):
            from core import _cached_load_all
            _cached_load_all.clear()
            inv()
            st.rerun()
        if st.button(f"{t('logout')}", use_container_width=True,
                     type="secondary", key="sidebar_logout_btn"):
            st.session_state.clear()
            st.rerun()

# =============================================================================
# BOTTOM NAVIGATION BAR (MOBILE)
# =============================================================================
if st.session_state.get('user'):
    tipo  = st.session_state.get('tipo', '')
    cargo = st.session_state.get('cargo', '')
    eh_cliente = (tipo == 'Cliente')

    if eh_cliente:
        nav_options = ["Portal", "Logout"]
    elif tipo == 'Admin':
        nav_options = ["Dashboard","Admin","Instrumentação","Perfil","Logout"]
        # Dashboard de Obra — só aparece a Admins com permissão (super-admin vê sempre)
        if tem_permissao(st.session_state.get('user',''), 'mod_dashboard_obra'):
            nav_options.insert(4, "Dashboard de Obra")
    elif tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
        nav_options = ["Início","Obra","Instrumentação","Perfil","Logout"]
    else:
        nav_options = ["Início","Obra","Perfil","Logout"]

    current_menu  = st.session_state.get('menu_selected', '')
    default_opcao = nav_options[0]
    if tipo == 'Admin':
        if   "Admin"             in current_menu: default_opcao = "Admin"
        elif "Instrumentação"    in current_menu: default_opcao = "Instrumentação"
        elif "Perfil"            in current_menu: default_opcao = "Perfil"
        elif "Dashboard de Obra" in current_menu: default_opcao = "Dashboard de Obra"
    elif tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
        if   "Obra"           in current_menu: default_opcao = "Obra"
        elif "Instrumentação" in current_menu: default_opcao = "Instrumentação"
        elif "Perfil"         in current_menu: default_opcao = "Perfil"
    else:
        if   "Obra"   in current_menu: default_opcao = "Obra"
        elif "Perfil" in current_menu: default_opcao = "Perfil"
    if default_opcao not in nav_options:
        default_opcao = nav_options[0]

    # Widget de chave estável, sincronizado manualmente com menu_selected:
    # só reescrevemos o valor do segmented_control quando a navegação mudou
    # por uma via externa a ele (sidebar, etc.) — nunca no próprio ciclo em
    # que o utilizador acabou de lhe tocar, para não perder o clique.
    _NAV_KEY = "bottom_nav_sel"
    if st.session_state.get('_bottom_nav_synced_menu') != current_menu:
        st.session_state[_NAV_KEY] = default_opcao
        st.session_state['_bottom_nav_synced_menu'] = current_menu

    st.markdown(f"""
    <style>
    .st-key-bottom_nav_bar {{
        position: fixed; bottom: 0; left: 0; width: 100%; z-index: 999;
        background-color: {THEME['surface']};
        border-top: 1px solid {THEME['border']};
        padding: 6px 4px;
    }}
    .bottom-nav-spacer {{ height: 70px; }}
    /* Só ecrãs largura mobile: no desktop já existe a barra lateral. */
    @media (min-width: 769px) {{
        .st-key-bottom_nav_bar {{ display: none; }}
        .bottom-nav-spacer {{ display: none; }}
    }}
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="bottom_nav_bar"):
        selected = st.segmented_control(
            "Navegação", nav_options, required=True,
            width="stretch", key=_NAV_KEY,
            label_visibility="collapsed",
        )

    nav_map = {op: op for op in nav_options}

    if st.session_state.get('_menu_locked', False):
        st.session_state['_menu_locked'] = False
    else:
        new_menu = nav_map.get(selected, '')
        if new_menu and new_menu != st.session_state.get('menu_selected', ''):
            st.session_state.menu_selected = new_menu
            st.session_state['_bottom_nav_synced_menu'] = new_menu
            # Protege a mudança contra o próximo rerun: sem isto, a sidebar
            # (radio com o seu próprio valor antigo, nunca tocado por este
            # clique) reescreve menu_selected de volta ao ecrã anterior.
            # Mesmo padrão já usado em mod_chefe.py e mod_inicio.py.
            st.session_state['_menu_locked'] = True
            if selected == "Logout":
                st.session_state.clear()
            st.rerun()

    st.markdown("<div class='bottom-nav-spacer'></div>", unsafe_allow_html=True)

# =============================================================================
# ROUTING PRINCIPAL
# =============================================================================
if not st.session_state.get('user'):
    from mod_login import render_login
    render_login()
else:
    _verificar_password_provisoria(st.session_state.get('user', ''))

    DATA = load_all()
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     diarias_config_db, diarias_faltas_db, diarias_pagamentos_db,
     folhas_ocr_db) = DATA

    tipo      = st.session_state.get('tipo', '')
    user_nome = st.session_state.get('user', '')
    cargo     = st.session_state.get('cargo', '')
    tem_acesso_inst = (tipo in ['Chefe de Equipa','Admin','Gestor'] or
                       cargo in ['Chefe de Equipa','Encarregado','Instrumentista'])
    eh_cliente = (tipo == 'Cliente')
    menu       = st.session_state.get('menu_selected', '')

    if "Logout" in menu:
        st.session_state.clear()
        st.rerun()

    # ── BLOQUEIO CENTRALIZADO — só Técnicos e Chefes ──────────────────
    # O onboarding de 4 passos (Documentos/Preço/Perfil/IBAN) saiu daqui
    # por completo — vive só no cps-ponto (DESENHO_ONBOARDING.md, passo
    # 6).
    if tipo not in ['Admin', 'Cliente']:
        # ── Aviso de contrato pendente de assinatura — PERMANENTE, NÃO
        # BLOQUEANTE (DESENHO_ONBOARDING.md, secção 4: "impedir alguém de
        # trabalhar no primeiro dia por causa de papelada em atraso é
        # pior do que o problema que resolve"). Tinha aqui um st.stop()
        # que bloqueava a app inteira — o mesmo bug já corrigido na
        # versão gémea do cps-ponto (_verificar_contrato); removido.
        try:
            u_ct_check = _load_users_cached()
            if not u_ct_check.empty:
                m_ct = u_ct_check[u_ct_check['Nome'] == user_nome]
                if not m_ct.empty:
                    row_ct = m_ct.iloc[0]
                    ct_enviado  = row_ct.get('Contrato_Enviado','')  == 'Sim'
                    ct_assinado = row_ct.get('Contrato_Assinado','') == 'Sim'
                    ct_validado = row_ct.get('Contrato_Validado_Admin','') == 'Sim'

                    if ct_enviado and not ct_assinado and not ct_validado:
                        st.warning(
                            "Tens um contrato pendente de assinatura. Podes "
                            "continuar a usar a app normalmente — só falta "
                            "este passo."
                        )

                        ct_b64 = row_ct.get('Contrato_b64','')
                        if ct_b64:
                            try:
                                ct_bytes = base64.b64decode(ct_b64)
                                st.download_button(
                                    "Descarregar Contrato para Assinar",
                                    data=ct_bytes,
                                    file_name=f"contrato_{user_nome.replace(' ','_')}.docx",
                                    mime="application/vnd.openxmlformats-officedocument"
                                         ".wordprocessingml.document",
                                    use_container_width=True,
                                    key="blk_dl_ct"
                                )
                            except:
                                st.error("Erro ao processar o contrato.")

                        st.markdown(f"""
                        <div style="background:{THEME['surface']};border:1px solid {THEME['border']};
                            border-radius:10px;padding:14px;margin:16px 0;border-left:3px solid {THEME['accent']};">
                            <p style="color:{THEME['text_secondary']};font-size:0.85rem;margin:0;">
                                <b>Instruções:</b><br>
                                1. Descarrega o contrato acima<br>
                                2. Imprime e assina à mão<br>
                                3. Fotografa ou digitaliza<br>
                                4. Faz upload abaixo
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        ficheiro_assin = st.file_uploader(
                            "Upload do contrato assinado",
                            type=["jpg","jpeg","png","pdf","docx"],
                            key="blk_ct_upload"
                        )
                        if ficheiro_assin:
                            tam_kb = len(ficheiro_assin.getvalue()) / 1024
                            st.success(
                                f"Ficheiro: **{ficheiro_assin.name}** "
                                f"({tam_kb:.0f} KB)"
                            )
                            st.markdown(
                                f"<p style='color:{THEME['warning']};font-size:0.82rem;margin:8px 0;'>"
                                "Confirma que o contrato está assinado antes de submeter.</p>",
                                unsafe_allow_html=True
                            )
                            if st.button("Submeter contrato assinado ao RH",
                                          key="blk_btn_assin",
                                          type="primary",
                                          use_container_width=True):
                                f_b64 = base64.b64encode(ficheiro_assin.getvalue()).decode()
                                u_up  = _load_users_cached().copy()
                                mask  = u_up['Nome'] == user_nome
                                if mask.any():
                                    u_up.loc[mask,'Contrato_Assinado']        = 'Sim'
                                    u_up.loc[mask,'Contrato_Assinatura_b64']  = f_b64
                                    u_up.loc[mask,'Contrato_Assinatura_Data'] = \
                                        datetime.now().strftime("%d/%m/%Y %H:%M")
                                    save_db(u_up, "usuarios.csv")
                                    criar_notificacao(
                                        destinatario="admin",
                                        titulo="Contrato Assinado",
                                        mensagem=f"{user_nome} submeteu o contrato assinado.",
                                        tipo="success", acao_url="/admin?tab=rh"
                                    )
                                    log_audit(usuario=user_nome,
                                              acao="SUBMETER_CONTRATO",
                                              tabela="usuarios.csv",
                                              registro_id=user_nome,
                                              detalhes="Contrato assinado submetido",
                                              ip="")
                                    inv("usuarios.csv")  # FIX 2 — selectivo
                                    st.success("Assinatura submetida! O RH será notificado.")
                                    st.rerun()
                        st.markdown("---")
        except Exception as _e_ct:
            pass

    if eh_cliente:
        st.markdown(f"# Portal do Cliente")
        from mod_cliente import render_cliente_portal
        render_cliente_portal()

    elif tipo == 'Admin':
        # ── ALERTA BACKUP ─────────────────────────────────────────────
        _status_bkp, _ultima_bkp = _verificar_alerta_backup()
        if _status_bkp != 'ok':
            _ultima_str = _ultima_bkp.strftime('%d/%m/%Y %H:%M') \
                          if _ultima_bkp else 'Nunca realizado'
            if _status_bkp in ('critico', 'nunca'):
                st.error(
                    f"**BACKUP CRÍTICO** — Último: **{_ultima_str}** — "
                    f"Dados não protegidos!"
                )
            else:
                st.warning(f"**Backup em atraso** — Último: **{_ultima_str}**")
            _col_b1, _col_b2 = st.columns(2)
            with _col_b1:
                if st.button("Fazer Backup Agora",
                             key="alert_bkp_btn", type="primary",
                             use_container_width=True):
                    st.session_state['menu_selected'] = f"Admin"
                    st.session_state['_menu_locked']  = True
                    st.rerun()
            with _col_b2:
                if st.button("Confirmar backup feito",
                             key="alert_bkp_confirm",
                             use_container_width=True):
                    _registar_backup(user_nome)
                    st.success("Backup confirmado!")
                    st.rerun()

        if f"Admin" in menu:
            from mod_admin import render_admin
            render_admin(*DATA)
        elif f"Instrumentação" in menu:
            st.markdown(f"# Instrumentação Industrial")
            from mod_instrumentacao import render_instrumentacao
            render_instrumentacao(*DATA)
        elif f"Perfil" in menu:
            st.markdown(f"# Perfil do Utilizador")
            from mod_perfil import render_perfil
            render_perfil(*DATA)
        elif f"Dashboard de Obra" in menu and \
                tem_permissao(user_nome, 'mod_dashboard_obra'):
            from mod_dashboard_obra import render_dashboard_obra
            render_dashboard_obra(*DATA)
        elif f"Dashboard" in menu or menu == '':
            st.markdown(f"# Dashboard Geral")
            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("Utilizadores", len(users))
            with c2: st.metric("Obras Ativas",
                len(obras_db[obras_db['Ativa']=='Ativa']) if not obras_db.empty else 0)
            with c3: st.metric("Registos", len(registos_db) if not registos_db.empty else 0)
            with c4: st.metric("Incidentes", len(incs_db) if not incs_db.empty else 0)
            st.divider()
            from mod_dashboard import render_dashboard
            render_dashboard(*DATA)
        else:
            from mod_admin import render_admin
            render_admin(*DATA)

    elif tipo == 'Secretariado':
        from mod_secretariado import render_secretariado
        render_secretariado(*DATA)

    elif tipo == 'Armazém':
        from mod_armazem import render_armazem
        req_fer_db2, req_mat_db2, req_epi_db2 = DATA[15], DATA[16], DATA[17]
        incs_db2 = DATA[6]
        render_armazem(req_fer_db2, req_mat_db2, req_epi_db2, incs_db2)

    else:
        if f"Obra" in menu:
            st.markdown(f"# Área Técnica")
            if tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
                from mod_chefe import render_chefe
                render_chefe(*DATA)
            else:
                from mod_tecnico import render_tecnico
                render_tecnico(*DATA)
        elif f"Instrumentação" in menu:
            if tem_acesso_inst:
                st.markdown(f"# Instrumentação Industrial")
                from mod_instrumentacao import render_instrumentacao
                render_instrumentacao(*DATA)
            else:
                st.warning("Não tem acesso a este módulo.")
        elif f"Perfil" in menu:
            st.markdown(f"# Perfil do Utilizador")
            from mod_perfil import render_perfil
            render_perfil(*DATA)
        else:
            from mod_inicio import render_inicio
            render_inicio(*DATA)

st.markdown(f"""
<style>
.footer {{
    position:fixed; bottom:60px; left:0; right:0;
    background:{THEME['surface']};
    padding:12px 20px; text-align:center;
    font-size:0.75rem; color:{THEME['text_secondary']};
    border-top:1px solid {THEME['border']}; z-index:9998;
}}
@media (max-width:768px) {{ .footer {{ display:none; }} }}
</style>
<div class="footer">GESTNOW v3.0 - Plataforma de Gestão de Empresas/Gestão de Obras e Instrumentação Industrial</div>
""", unsafe_allow_html=True)

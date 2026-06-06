import streamlit as st
import pandas as pd
from core import load_all, inv, ICONS, fh, save_db, tem_permissao, _PERM_COLS, _SUPER_ADMINS
from datetime import datetime

# =============================================================================
# HELPERS — descompactar load_all() de forma uniforme
# =============================================================================
_ALL_COLS = [
    "users","obras_db","frentes_db","registos_db","faturas_db","docs_db",
    "incs_db","sw_db","obs_db","equip_db","diags_db","diags_u_db","folhas_db",
    "comuns_db","comuns_u_db","req_fer_db","req_mat_db","req_epi_db","avals_db",
    "inst_acessos_db","diarias_config_db","diarias_faltas_db",
    "diarias_pagamentos_db","folhas_ocr_db"
]

def _unpack():
    """Chama load_all() (cached) e devolve dict com os DataFrames."""
    vals = load_all()
    return dict(zip(_ALL_COLS, vals))

# =============================================================================
# FRAGMENTOS — cada tab é um @st.fragment independente.
# Um clique dentro do tab RH só rerun o fragmento RH; os outros 9 não correm.
# =============================================================================

def _sem_permissao(modulo_label):
    st.error(f"🚫 Sem permissão para aceder ao módulo **{modulo_label}**.")


@st.fragment
def _tab_armazem():
    if not tem_permissao(st.session_state.get('user',''), 'mod_armazem'):
        _sem_permissao("Armazém"); return
    d = _unpack()
    from mod_armazem import render_armazem
    render_armazem(d["req_fer_db"], d["req_mat_db"],
                   d["req_epi_db"],  d["incs_db"])


@st.fragment
def _tab_rh():
    if not tem_permissao(st.session_state.get('user',''), 'mod_rh'):
        _sem_permissao("RH"); return
    d = _unpack()
    from mod_admin_rh import render_admin_rh
    render_admin_rh(
        d["users"], d["obras_db"], d["frentes_db"], d["registos_db"],
        d["faturas_db"], d["docs_db"], d["incs_db"], d["sw_db"], d["obs_db"],
        d["equip_db"], d["diags_db"], d["diags_u_db"], d["folhas_db"],
        d["comuns_db"], d["comuns_u_db"], d["req_fer_db"], d["req_mat_db"],
        d["req_epi_db"], d["avals_db"], d["inst_acessos_db"]
    )


@st.fragment
def _tab_secretariado():
    if not tem_permissao(st.session_state.get('user',''), 'mod_secretariado'):
        _sem_permissao("Secretariado"); return
    d = _unpack()
    from mod_secretariado import render_secretariado
    render_secretariado(
        d["users"], d["obras_db"], d["frentes_db"], d["registos_db"],
        d["faturas_db"], d["docs_db"], d["incs_db"], d["sw_db"], d["obs_db"],
        d["equip_db"], d["diags_db"], d["diags_u_db"], d["folhas_db"],
        d["comuns_db"], d["comuns_u_db"], d["req_fer_db"], d["req_mat_db"],
        d["req_epi_db"], d["avals_db"], d["inst_acessos_db"],
        d["diarias_config_db"], d["diarias_faltas_db"],
        d["diarias_pagamentos_db"]
    )


@st.fragment
def _subtab_prod_obras():
    d = _unpack()
    from mod_admin_obras import render_obras
    render_obras(d["obras_db"], d["frentes_db"], d["users"], d["inst_acessos_db"])

@st.fragment
def _subtab_prod_frota():
    from mod_admin_frota import render_frota
    render_frota()

@st.fragment
def _subtab_prod_deslocacoes():
    d = _unpack()
    from mod_admin_deslocacoes import render_deslocacoes
    render_deslocacoes(d["obras_db"], d["users"])

@st.fragment
def _subtab_prod_planeamento():
    from mod_admin_planeamento import render_planeamento
    render_planeamento()

@st.fragment
def _subtab_prod_acessos():
    d = _unpack()
    from mod_admin_acessos_obras import render_acessos_obras
    render_acessos_obras(d["users"], d["obras_db"])


@st.fragment
def _tab_producao():
    if not tem_permissao(st.session_state.get('user',''), 'mod_producao'):
        _sem_permissao("Produção"); return
    st.markdown("## 🏭 Produção")
    prod_tabs = st.tabs([
        "🏗️ Obras", "🚗 Frota", "🗺️ Deslocações", "📋 Planeamento", "🔐 Acessos"
    ])
    with prod_tabs[0]: _subtab_prod_obras()
    with prod_tabs[1]: _subtab_prod_frota()
    with prod_tabs[2]: _subtab_prod_deslocacoes()
    with prod_tabs[3]: _subtab_prod_planeamento()
    with prod_tabs[4]: _subtab_prod_acessos()


@st.fragment
def _subtab_fat_dashboard():
    d = _unpack()
    from mod_fat_dashboard import render_fat_dashboard
    render_fat_dashboard(d["obras_db"], d["registos_db"], d["faturas_db"], d["diarias_pagamentos_db"])

@st.fragment
def _subtab_fat_clientes():
    d = _unpack()
    from mod_fat_clientes import render_fat_clientes
    render_fat_clientes(d["obras_db"], d["registos_db"])

@st.fragment
def _subtab_fat_fornecedores():
    d = _unpack()
    from mod_fat_fornecedores import render_fat_fornecedores
    render_fat_fornecedores(d["obras_db"])

@st.fragment
def _subtab_fat_rh():
    d = _unpack()
    from mod_fat_rh import render_fat_rh
    render_fat_rh(d["obras_db"], d["registos_db"])

@st.fragment
def _subtab_fat_frota():
    from mod_fat_frota import render_fat_frota
    render_fat_frota()

@st.fragment
def _subtab_fat_obras():
    d = _unpack()
    from mod_fat_obras import render_fat_obras
    render_fat_obras(d["obras_db"], d["registos_db"], d["faturas_db"], d["diarias_pagamentos_db"])

@st.fragment
def _subtab_fat_tesouraria():
    d = _unpack()
    from mod_fat_tesouraria import render_fat_tesouraria
    render_fat_tesouraria(d["obras_db"], d["registos_db"], d["faturas_db"], d["diarias_pagamentos_db"])

@st.fragment
def _subtab_fat_crise():
    d = _unpack()
    from mod_fat_crise import render_fat_crise
    render_fat_crise(d["obras_db"], d["registos_db"], d["faturas_db"], d["diarias_pagamentos_db"])

@st.fragment
def _subtab_fat_fundos():
    from mod_fat_fundos import render_fat_fundos
    render_fat_fundos()

@st.fragment
def _subtab_fat_imobilizado():
    from mod_fat_imobilizado import render_fat_imobilizado
    render_fat_imobilizado()

@st.fragment
def _subtab_fat_fiscal():
    d = _unpack()
    from mod_fat_fiscal import render_fat_fiscal
    render_fat_fiscal(d["obras_db"], d["registos_db"], d["faturas_db"], d["diarias_pagamentos_db"])

@st.fragment
def _subtab_fat_auditoria():
    d = _unpack()
    from mod_fat_auditoria import render_fat_auditoria
    render_fat_auditoria(d["obras_db"], d["registos_db"], d["faturas_db"], d["diarias_pagamentos_db"])

@st.fragment
def _subtab_fat_reporting():
    d = _unpack()
    from mod_fat_reporting import render_fat_reporting
    render_fat_reporting(d["obras_db"], d["registos_db"], d["faturas_db"], d["diarias_pagamentos_db"])

@st.fragment
def _subtab_fat_custos():
    d = _unpack()
    _render_custos_por_obra(d["obras_db"], d["registos_db"], d["req_mat_db"], d["req_fer_db"], d["req_epi_db"], d["incs_db"])

@st.fragment
def _subtab_fat_diarias():
    d = _unpack()
    from mod_admin_diarias import render_admin_diarias
    render_admin_diarias(
        d["users"], d["obras_db"], d["frentes_db"], d["registos_db"],
        d["faturas_db"], d["docs_db"], d["incs_db"], d["sw_db"],
        d["obs_db"], d["equip_db"], d["diags_db"], d["diags_u_db"],
        d["folhas_db"], d["comuns_db"], d["comuns_u_db"],
        d["req_fer_db"], d["req_mat_db"], d["req_epi_db"], d["avals_db"],
        d["inst_acessos_db"], d["diarias_config_db"],
        d["diarias_faltas_db"], d["diarias_pagamentos_db"]
    )

@st.fragment
def _subtab_fat_folhas():
    d = _unpack()
    _render_folhas_ponto_fat(d["folhas_db"], d["folhas_ocr_db"], d["obras_db"])

@st.fragment
def _subtab_fat_horas():
    d = _unpack()
    _render_horas_faturacao(d["registos_db"])

@st.fragment
def _subtab_fat_emissao():
    d = _unpack()
    _render_emissao_mensal(d["obras_db"], d["registos_db"], d["faturas_db"], d["diarias_pagamentos_db"])

@st.fragment
def _subtab_fat_exportacao():
    from mod_exportacao_contabilidade import render_exportacao_contabilidade
    render_exportacao_contabilidade()


@st.fragment
def _tab_faturacao():
    if not tem_permissao(st.session_state.get('user',''), 'mod_faturacao'):
        _sem_permissao("Faturação"); return
    st.markdown("## 💰 Faturação")
    fat_tabs = st.tabs([
        "📊 Dashboard CFO", "🧾 Clientes & Faturação", "📥 Fornecedores",
        "👥 RH Financeiro", "🚗 Frota & Renting", "📈 Performance Obras",
        "💵 Tesouraria", "🆘 Simulador Crise", "🇪🇺 Fundos Europeus",
        "🏭 Imobilizado", "🧾 Fiscal", "📋 Auditoria Anual", "📊 Reporting",
        "📊 Custos por Obra", "💶 Diárias", "📄 Folhas de Ponto",
        "⏱️ Horas Faturação", "📤 Emissão Mensal", "📤 Export Contabilidade",
    ])
    with fat_tabs[0]:  _subtab_fat_dashboard()
    with fat_tabs[1]:  _subtab_fat_clientes()
    with fat_tabs[2]:  _subtab_fat_fornecedores()
    with fat_tabs[3]:  _subtab_fat_rh()
    with fat_tabs[4]:  _subtab_fat_frota()
    with fat_tabs[5]:  _subtab_fat_obras()
    with fat_tabs[6]:  _subtab_fat_tesouraria()
    with fat_tabs[7]:  _subtab_fat_crise()
    with fat_tabs[8]:  _subtab_fat_fundos()
    with fat_tabs[9]:  _subtab_fat_imobilizado()
    with fat_tabs[10]: _subtab_fat_fiscal()
    with fat_tabs[11]: _subtab_fat_auditoria()
    with fat_tabs[12]: _subtab_fat_reporting()
    with fat_tabs[13]: _subtab_fat_custos()
    with fat_tabs[14]: _subtab_fat_diarias()
    with fat_tabs[15]: _subtab_fat_folhas()
    with fat_tabs[16]: _subtab_fat_horas()
    with fat_tabs[17]: _subtab_fat_emissao()
    with fat_tabs[18]: _subtab_fat_exportacao()


@st.fragment
def _tab_orcamentacao():
    if not tem_permissao(st.session_state.get('user',''), 'mod_orcamentacao'):
        _sem_permissao("Orçamentação"); return
    from mod_admin_orcamentacao import render_orcamentacao
    render_orcamentacao()


@st.fragment
def _tab_comercial():
    if not tem_permissao(st.session_state.get('user',''), 'mod_comercial'):
        _sem_permissao("Comercial"); return
    from mod_admin_comercial import render_comercial
    render_comercial()


@st.fragment
def _tab_contactos_iso():
    if not tem_permissao(st.session_state.get('user',''), 'mod_contactos_iso'):
        _sem_permissao("Contactos ISO"); return
    from mod_contactos_iso import render_contactos_iso
    render_contactos_iso()


@st.fragment
def _tab_qualidade():
    if not tem_permissao(st.session_state.get('user',''), 'mod_qualidade'):
        _sem_permissao("Qualidade"); return
    d = _unpack()
    st.markdown("## 🎯 Qualidade & Auditoria")
    qual_tabs = st.tabs([
        "🎯 Qualidade Operacional", "🏆 ISO 9001:2015", "📋 Logs Audit"
    ])
    with qual_tabs[0]:
        from mod_admin_qualidade import render_qualidade
        render_qualidade()
    with qual_tabs[1]:
        from mod_iso9001 import render_iso9001
        render_iso9001()
    with qual_tabs[2]:
        st.markdown("### 📋 Logs de Auditoria")
        from core import get_audit_logs
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_user = st.selectbox(
                "Utilizador",
                ["Todos"] + d["users"]["Nome"].tolist(),
                key="log_filt_user"
            )
        with col_f2:
            apenas_clientes = st.checkbox(
                "👥 Apenas Clientes", key="log_filt_clientes"
            )
        with col_f3:
            limite = st.number_input(
                "Limite", min_value=10, max_value=1000,
                value=100, key="log_limite"
            )
        usuario_f = None if filtro_user == "Todos" else filtro_user
        logs_df   = get_audit_logs(filtro_usuario=usuario_f, limite=limite)
        if apenas_clientes and not logs_df.empty:
            logs_df = logs_df[
                logs_df["Usuario"].str.contains("CLIENTE:", na=False)
            ]
        if not logs_df.empty:
            st.metric("Total Ações", len(logs_df))
            cols_show = [c for c in [
                "Data","Hora","Usuario","Acao","Tabela","Registro_ID","Detalhes"
            ] if c in logs_df.columns]
            st.dataframe(logs_df[cols_show], use_container_width=True, hide_index=True)
            csv_logs = logs_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Exportar Logs", csv_logs,
                f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv", use_container_width=True
            )
        else:
            st.info("📋 Sem registos de auditoria.")


@st.fragment
def _tab_it():
    if not tem_permissao(st.session_state.get('user',''), 'mod_it'):
        _sem_permissao("IT"); return
    st.markdown("## 💻 IT & Sistemas")
    it_tabs = st.tabs(["💻 IT & Infraestrutura", "📧 Config Email"])
    with it_tabs[0]:
        from mod_admin_it import render_it
        render_it()
    with it_tabs[1]:
        st.markdown("### 📧 Configuração de Email SMTP")
        st.info("""
        **Para configurar emails:**
        1. Vai ao Google Cloud Console → Secret Manager
        2. Adiciona: SMTP_SERVER, SMTP_PORT, SMTP_USER,
           SMTP_PASSWORD, SMTP_FROM_NAME
        3. Reinicia o Cloud Run
        """)
        from core import get_smtp_config, testar_smtp
        config = get_smtp_config()
        if config:
            st.success("✅ SMTP Configurado!")
            st.markdown(
                f"<div style='background:rgba(16,185,129,0.1);"
                f"border:2px solid #10B981;border-radius:10px;padding:20px;'>"
                f"<p><b>Server:</b> {config['server']}</p>"
                f"<p><b>Porta:</b> {config['port']}</p>"
                f"<p><b>User:</b> {config['user']}</p>"
                f"</div>", unsafe_allow_html=True
            )
            st.divider()
            email_teste = st.text_input(
                "Email para teste", placeholder="exemplo@email.com",
                key="smtp_test_email"
            )
            if st.button("📧 Enviar Email de Teste",
                         use_container_width=True, type="primary"):
                if email_teste:
                    with st.spinner("A enviar..."):
                        if testar_smtp(email_teste):
                            st.success(f"✅ Email enviado para {email_teste}!")
                        else:
                            st.error("❌ Falha. Verifica a configuração.")
                else:
                    st.warning("⚠️ Insere um email.")
        else:
            st.warning("⚠️ SMTP não configurado.")


@st.fragment
def _tab_hse():
    if not tem_permissao(st.session_state.get('user',''), 'mod_hse'):
        _sem_permissao("HSE"); return
    d = _unpack()
    st.markdown("### 🛡️ Segurança e HSE")
    tab_inc, tab_sw = st.tabs(["⚠️ Incidentes", "🚶 Safety Walks"])
    with tab_inc:
        incs_db = d["incs_db"]
        if not incs_db.empty:
            hse = (incs_db[incs_db["Tipo"] != "Avaria"]
                   if "Tipo" in incs_db.columns else incs_db)
            cols_hse = [c for c in [
                "ID","Data","Utilizador","Obra","Descricao","Gravidade","Status"
            ] if c in hse.columns]
            st.dataframe(hse[cols_hse], use_container_width=True, hide_index=True)
        else:
            st.info("📋 Sem incidentes.")
    with tab_sw:
        sw_db = d["sw_db"]
        if not sw_db.empty:
            st.dataframe(sw_db, use_container_width=True, hide_index=True)
        else:
            st.info("📋 Sem safety walks.")


# =============================================================================
# TAB PERMISSÕES — apenas visível para super-admins (_SUPER_ADMINS)
# =============================================================================
_MODULOS_LABELS = [
    ("mod_armazem",     "📦 Armazém"),
    ("mod_rh",          "👥 RH"),
    ("mod_secretariado","🗂️ Secretariado"),
    ("mod_producao",    "🏭 Produção"),
    ("mod_faturacao",   "💰 Faturação"),
    ("mod_orcamentacao",   "📊 Orçamentação"),
    ("mod_comercial",      "💼 Comercial"),
    ("mod_contactos_iso",  "🔗 Contactos ISO"),
    ("mod_qualidade",      "🎯 Qualidade"),
    ("mod_it",          "💻 IT"),
    ("mod_hse",         "🛡️ HSE"),
]

@st.fragment
def _tab_permissoes():
    from core import load_db, save_db, inv, _load_users_cached, _PERM_COLS
    st.markdown("## 🔐 Gestão de Permissões de Módulos")
    st.info("Apenas super-admins têm acesso a esta secção. "
            "Configura quais os módulos acessíveis a cada Admin.")

    # Utilizadores Admin (excluindo super-admin)
    users = _load_users_cached()
    admins = []
    if not users.empty and 'Tipo' in users.columns:
        admins = [n for n in users[users['Tipo'] == 'Admin']['Nome'].tolist()
                  if n not in _SUPER_ADMINS]

    if not admins:
        st.warning("⚠️ Sem utilizadores com tipo Admin para gerir.")
        return

    # Permissões actuais
    perm_df = load_db("permissoes_admin.csv", _PERM_COLS, silent=True)
    perm_dict = {}
    if not perm_df.empty:
        for _, row in perm_df.iterrows():
            u = str(row.get('utilizador', ''))
            if u:
                perm_dict[u] = {k: str(row.get(k, 'False')).strip().lower() == 'true'
                                for k, _ in _MODULOS_LABELS}

    st.markdown("---")
    # Cabeçalho da tabela
    hdr = st.columns([3] + [1] * 10)
    hdr[0].markdown("**Utilizador**")
    for i, (_, lbl) in enumerate(_MODULOS_LABELS):
        icon = lbl.split()[0]
        hdr[i + 1].markdown(f"<div style='text-align:center;font-size:0.75rem;'>{icon}</div>",
                             unsafe_allow_html=True)

    novos: dict = {}
    for admin in admins:
        atual = perm_dict.get(admin, {k: False for k, _ in _MODULOS_LABELS})
        cols = st.columns([3] + [1] * 10)
        cols[0].markdown(f"👤 {admin}")
        novos[admin] = {}
        for i, (mod_key, lbl) in enumerate(_MODULOS_LABELS):
            novos[admin][mod_key] = cols[i + 1].checkbox(
                "", value=atual.get(mod_key, False),
                key=f"perm_{admin}_{mod_key}",
                label_visibility="collapsed"
            )

    st.markdown("---")
    if st.button("💾 Guardar Permissões", type="primary",
                 use_container_width=True, key="btn_guardar_perms"):
        rows = [{"utilizador": u, **{k: str(v) for k, v in perms.items()}}
                for u, perms in novos.items()]
        df_novo = pd.DataFrame(rows, columns=_PERM_COLS)
        save_db(df_novo, "permissoes_admin.csv")
        inv("permissoes_admin.csv")
        st.success("✅ Permissões guardadas!")
        st.rerun()


# =============================================================================
# RENDER ADMIN — hub principal (header + métricas + chamada dos fragmentos)
# =============================================================================
@st.fragment
def _fragment_notificacoes():
    from core import (get_notificacoes, marcar_notificacao_lida,
                      contar_notificacoes_nao_lidas)
    user_atual  = st.session_state.user
    n_nao_lidas = contar_notificacoes_nao_lidas(user_atual)
    col_n1, col_n2 = st.columns([10, 1])
    with col_n2:
        if n_nao_lidas > 0:
            st.markdown(
                f"<div style='text-align:right;'>"
                f"<span style='font-size:1.5rem;'>🔔</span>"
                f"<span style='background:#EF4444;color:white;border-radius:50%;"
                f"padding:2px 8px;font-size:0.8rem;margin-left:-10px;'>"
                f"{n_nao_lidas}</span></div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div style='text-align:right;'>"
                "<span style='font-size:1.5rem;opacity:0.5;'>🔔</span></div>",
                unsafe_allow_html=True
            )
    with st.expander("🔔 Ver Notificações", expanded=n_nao_lidas > 0):
        notifs_df = get_notificacoes(user_atual, apenas_nao_lidas=True, limite=20)
        if not notifs_df.empty:
            for _, notif in notifs_df.iterrows():
                cor = {"info":"#3B82F6","warning":"#F59E0B",
                       "error":"#EF4444","success":"#10B981"}.get(
                    notif.get('Tipo','info'),"#6B7280"
                )
                st.markdown(
                    f"<div style='background:{cor}22;border-left:4px solid {cor};"
                    f"padding:15px;border-radius:8px;margin-bottom:10px;'>"
                    f"<strong style='color:{cor};'>{notif.get('Titulo','')}</strong>"
                    f"<p style='margin:5px 0 0 0;color:#94A3B8;'>"
                    f"{notif.get('Mensagem','')}</p>"
                    f"<small style='color:#6B7280;'>"
                    f"{notif.get('Data','')} {notif.get('Hora','')}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            if st.button("✅ Marcar Todas como Lidas",
                          key="marcar_todas_lidas"):
                for _, notif in notifs_df.iterrows():
                    marcar_notificacao_lida(notif['ID'])
                inv("notificacoes.csv")
                st.rerun()
        else:
            st.info("✅ Sem notificações pendentes.")


def render_admin(*args):
    """Hub Principal do Admin — 10 tabs com @st.fragment."""

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
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     diarias_config_db, diarias_faltas_db, diarias_pagamentos_db,
     folhas_ocr_db) = args

    from core import render_connection_indicator, render_offline_banner
    render_connection_indicator()
    render_offline_banner()
    # sync_data_when_online removido — chamada nuclear desnecessária no render

    # ── Header ────────────────────────────────────────────────────
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

    # ── Notificações ──────────────────────────────────────────────
    _fragment_notificacoes()

    st.divider()

    # ── Métricas ──────────────────────────────────────────────────
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

    # ── Tabs — 11 módulos + tab Permissões (só Diogo Henriques) ──────
    _e_super = st.session_state.get('user','') in _SUPER_ADMINS
    _tab_labels = [
        "📦 Armazém", "👥 RH", "🗂️ Secretariado", "🏭 Produção",
        "💰 Faturação", "📊 Orçamentação", "💼 Comercial",
        "🔗 Contactos ISO", "🎯 Qualidade", "💻 IT", "🛡️ HSE",
    ]
    if _e_super:
        _tab_labels.append("🔐 Permissões")
    tabs = st.tabs(_tab_labels)
    with tabs[0]:  _tab_armazem()
    with tabs[1]:  _tab_rh()
    with tabs[2]:  _tab_secretariado()
    with tabs[3]:  _tab_producao()
    with tabs[4]:  _tab_faturacao()
    with tabs[5]:  _tab_orcamentacao()
    with tabs[6]:  _tab_comercial()
    with tabs[7]:  _tab_contactos_iso()
    with tabs[8]:  _tab_qualidade()
    with tabs[9]:  _tab_it()
    with tabs[10]: _tab_hse()
    if _e_super:
        with tabs[11]: _tab_permissoes()


# =============================================================================
# FUNÇÕES AUXILIARES DE FATURAÇÃO
# =============================================================================

def _render_custos_por_obra(
    obras_db, registos_db, req_mat_db,
    req_fer_db, req_epi_db, incs_db
):
    import pandas as pd
    from core import fh, load_db
    st.markdown("### 📊 Custos Totais por Obra")

    if obras_db.empty:
        st.info("📋 Sem obras.")
        return

    obras_ativas = obras_db[obras_db['Ativa'] == 'Ativa']['Obra'].tolist()
    if not obras_ativas:
        st.info("📋 Sem obras ativas.")
        return

    obra_c = st.selectbox("Obra", obras_ativas, key="custos_obra")

    # Horas
    horas_obra = 0
    if not registos_db.empty:
        ro = registos_db[registos_db['Obra'] == obra_c]
        horas_obra = pd.to_numeric(
            ro['Horas_Total'], errors='coerce'
        ).fillna(0).sum()

    # Materiais
    mat_total = 0
    try:
        compras_db = load_db("compras.csv", [
            "Obra","Total"
        ], silent=True)
        if not compras_db.empty:
            mc = compras_db[compras_db['Obra'] == obra_c]
            mat_total = pd.to_numeric(
                mc['Total'], errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    # Dormidas
    dorm_total = 0
    try:
        dormidas_db = load_db("dormidas.csv", [
            "Obra","Total"
        ], silent=True)
        if not dormidas_db.empty:
            dc = dormidas_db[dormidas_db['Obra'] == obra_c]
            dorm_total = pd.to_numeric(
                dc['Total'], errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("⏱️ Horas",     fh(horas_obra))
    with c2: st.metric("📦 Materiais", f"€ {mat_total:.2f}")
    with c3: st.metric("🏨 Dormidas",  f"€ {dorm_total:.2f}")

    total_custos = mat_total + dorm_total
    st.metric("💰 Total Custos (sem horas)", f"€ {total_custos:.2f}")


def _render_folhas_ponto_fat(folhas_db, folhas_ocr_db, obras_db):
    import pandas as pd
    st.markdown("### 📄 Folhas de Ponto por Obra")

    obras_lista = obras_db[
        obras_db['Ativa'] == 'Ativa'
    ]['Obra'].tolist() if not obras_db.empty else []

    if not obras_lista:
        st.info("📋 Sem obras ativas.")
        return

    obra_fp = st.selectbox("Obra", obras_lista, key="fat_fp_obra")

    # Folhas assinadas
    st.markdown("#### ✍️ Folhas Assinadas pelo Chefe")
    if not folhas_db.empty and 'Obra' in folhas_db.columns:
        fp_obra = folhas_db[folhas_db['Obra'] == obra_fp]
        if not fp_obra.empty:
            cols_fp = [c for c in [
                'Periodo','Responsavel','Data_Assinatura','Selo','Status'
            ] if c in fp_obra.columns]
            st.dataframe(
                fp_obra[cols_fp],
                use_container_width=True, hide_index=True
            )
        else:
            st.info(f"📋 Sem folhas assinadas para {obra_fp}.")
    else:
        st.info("📋 Sem folhas.")

    # Folhas OCR (extraídas por IA)
    st.markdown("---")
    st.markdown("#### 🤖 Folhas Extraídas por IA (OCR)")
    if not folhas_ocr_db.empty and 'Obra' in folhas_ocr_db.columns:
        ocr_obra = folhas_ocr_db[folhas_ocr_db['Obra'] == obra_fp]
        if not ocr_obra.empty:
            cols_ocr = [c for c in [
                'Semana_Inicio','Semana_Fim','Tecnico',
                'Horas_Folha','Extraido_Em','Extraido_Por'
            ] if c in ocr_obra.columns]
            st.dataframe(
                ocr_obra[cols_ocr],
                use_container_width=True, hide_index=True
            )

            # Admin pode ver e descarregar
            st.markdown("---")
            st.markdown("#### 👁️ Ver Folha de Ponto (Imagem)")
            periodos_ocr = ocr_obra['Semana_Inicio'].unique().tolist()
            periodo_ver  = st.selectbox(
                "Período", periodos_ocr, key="fat_periodo_ver"
            )
            ocr_periodo = ocr_obra[
                ocr_obra['Semana_Inicio'] == periodo_ver
            ]
            if not ocr_periodo.empty:
                img_b64 = ocr_periodo.iloc[0].get('Imagem_b64','')
                if img_b64 and len(img_b64) > 100:
                    import base64
                    try:
                        st.image(
                            f"data:image/jpeg;base64,{img_b64}",
                            caption=f"Folha de ponto — {periodo_ver}",
                            use_column_width=True
                        )
                        img_bytes = base64.b64decode(img_b64)
                        st.download_button(
                            "📥 Descarregar Imagem",
                            data=img_bytes,
                            file_name=f"folha_{obra_fp}_{periodo_ver.replace('/','')}.jpg",
                            mime="image/jpeg",
                            key="dl_folha_img"
                        )
                    except:
                        st.info("📷 Imagem não disponível para visualização.")
                else:
                    st.info("📷 Imagem não armazenada neste registo.")
        else:
            st.info(f"📋 Sem folhas OCR para {obra_fp}.")
    else:
        st.info("📋 Sem folhas OCR disponíveis.")


def _render_horas_faturacao(registos_db):
    st.markdown("### ⏱️ Horas por Obra (Faturação)")
    if registos_db.empty:
        st.info("📋 Sem registos.")
        return
    regs = registos_db[registos_db['Status'] == '3'].copy()
    if regs.empty:
        st.info("📋 Sem registos com status faturado.")
        return
    regs['Horas_Total'] = pd.to_numeric(regs['Horas_Total'], errors='coerce').fillna(0)
    resumo = regs.groupby('Obra')['Horas_Total'].sum().reset_index()
    resumo.columns = ['Obra', 'Horas Totais']
    resumo['Horas Totais'] = resumo['Horas Totais'].apply(fh)
    st.dataframe(resumo.sort_values('Obra'), use_container_width=True, hide_index=True)


def _render_emissao_mensal(
    obras_db, registos_db, faturas_db, diarias_pagamentos_db
):
    import pandas as pd
    from core import fh, save_db, load_db
    import uuid
    from datetime import datetime

    st.markdown("### 📤 Emissão de Fatura Mensal ao Cliente")
    st.info(
        "Gera o resumo mensal de custos por obra para enviar ao cliente."
    )

    obras_ativas = obras_db[
        obras_db['Ativa'] == 'Ativa'
    ]['Obra'].tolist() if not obras_db.empty else []

    if not obras_ativas:
        st.info("📋 Sem obras ativas.")
        return

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        obra_em = st.selectbox("Obra", obras_ativas, key="emissao_obra")
    with col_e2:
        import calendar
        hoje_em = datetime.now()
        meses   = {
            "Janeiro":1,"Fevereiro":2,"Março":3,"Abril":4,
            "Maio":5,"Junho":6,"Julho":7,"Agosto":8,
            "Setembro":9,"Outubro":10,"Novembro":11,"Dezembro":12
        }
        mes_sel_em = st.selectbox(
            "Mês",
            list(meses.keys()),
            index=hoje_em.month - 1,
            key="emissao_mes"
        )

    mes_num = meses[mes_sel_em]
    ano_em  = hoje_em.year

    # Horas processadas (Status 3)
    horas_fat = 0
    valor_horas = 0
    if not registos_db.empty:
        regs_em = registos_db[
            (registos_db['Obra']   == obra_em) &
            (registos_db['Status'] == '3')
        ].copy()
        regs_em['Data_d'] = pd.to_datetime(
            regs_em['Data'], dayfirst=True, errors='coerce'
        )
        regs_mes = regs_em[
            (regs_em['Data_d'].dt.month == mes_num) &
            (regs_em['Data_d'].dt.year  == ano_em)
        ]
        horas_fat = pd.to_numeric(
            regs_mes['Horas_Total'], errors='coerce'
        ).fillna(0).sum()

    # Diárias do mês
    diarias_mes = 0
    if not diarias_pagamentos_db.empty:
        dp_em = diarias_pagamentos_db[
            diarias_pagamentos_db['Obras'].str.contains(
                obra_em, na=False
            )
        ]
        diarias_mes = pd.to_numeric(
            dp_em['Valor_Total'], errors='coerce'
        ).fillna(0).sum()

    # Materiais
    mat_mes = 0
    try:
        compras_em = load_db("compras.csv",["Obra","Total"], silent=True)
        if not compras_em.empty:
            mat_mes = pd.to_numeric(
                compras_em[compras_em['Obra'] == obra_em]['Total'],
                errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    # Dormidas
    dorm_mes = 0
    try:
        dorm_em = load_db("dormidas.csv",["Obra","Total"], silent=True)
        if not dorm_em.empty:
            dorm_mes = pd.to_numeric(
                dorm_em[dorm_em['Obra'] == obra_em]['Total'],
                errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    st.markdown(f"#### 📊 Resumo — {mes_sel_em} {ano_em} — {obra_em}")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("⏱️ Horas",     fh(horas_fat))
    with c2: st.metric("💶 Diárias",   f"€ {diarias_mes:.2f}")
    with c3: st.metric("📦 Materiais", f"€ {mat_mes:.2f}")
    with c4: st.metric("🏨 Dormidas",  f"€ {dorm_mes:.2f}")

    total_fat = diarias_mes + mat_mes + dorm_mes
    st.metric("💰 Total a Faturar (sem horas)", f"€ {total_fat:.2f}")
    st.info(
        "ℹ️ O valor das horas depende do preço/hora contratado com o cliente."
    )

    if st.button(
        "📄 Gerar Resumo PDF",
        key="btn_gerar_fat_mensal",
        type="primary",
        use_container_width=True
    ):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            )
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            import io

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4,
                                    rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            story  = []

            story.append(Paragraph(
                f"RESUMO DE FATURAÇÃO — {mes_sel_em.upper()} {ano_em}",
                styles['Heading1']
            ))
            story.append(Paragraph(
                f"Obra: {obra_em}", styles['Normal']
            ))
            story.append(Spacer(1, 0.5*cm))

            dados_pdf = [
                ["Descrição", "Valor (€)"],
                ["Horas trabalhadas", f"{fh(horas_fat)}"],
                ["Ajudas de custo (diárias)", f"€ {diarias_mes:.2f}"],
                ["Materiais/Compras", f"€ {mat_mes:.2f}"],
                ["Alojamento (dormidas)", f"€ {dorm_mes:.2f}"],
                ["TOTAL (sem horas)", f"€ {total_fat:.2f}"],
            ]
            t = Table(dados_pdf, colWidths=[12*cm, 5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0),(-1,0),  colors.HexColor('#1E293B')),
                ('TEXTCOLOR',     (0,0),(-1,0),  colors.white),
                ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0,0),(-1,-1), 11),
                ('GRID',          (0,0),(-1,-1), 0.5, colors.grey),
                ('BACKGROUND',    (0,-1),(-1,-1),colors.HexColor('#F1F5F9')),
                ('FONTNAME',      (0,-1),(-1,-1),'Helvetica-Bold'),
                ('TOPPADDING',    (0,0),(-1,-1), 8),
                ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph(
                f"Documento gerado em "
                f"{datetime.now().strftime('%d/%m/%Y %H:%M')} — GESTNOW v3.0",
                styles['Normal']
            ))
            doc.build(story)
            buf.seek(0)

            st.download_button(
                f"📥 Descarregar PDF — {mes_sel_em} {ano_em}",
                data=buf.getvalue(),
                file_name=(
                    f"faturacao_{obra_em.replace(' ','_')}_"
                    f"{mes_num:02d}_{ano_em}.pdf"
                ),
                mime="application/pdf",
                key="dl_fat_mensal_pdf"
            )
        except Exception as e:
            st.error(f"❌ Erro ao gerar PDF: {e}")

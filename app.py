import streamlit as st
import pandas as pd
import json, base64, time
from datetime import datetime
from core import (init_session, check_timeout, load_all, inject_pwa_meta,
                  inject_global_css, ICONS, hp, save_db, log_audit,
                  criar_notificacao, load_db, _gcs_read, inv)
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
# 3. FUNÇÕES DE VALIDAÇÃO OBRIGATÓRIA (CENTRALIZADAS)
# =============================================================================
def _load_users_fresh():
    """Lê usuarios.csv sempre do GCS sem cache com strip completo."""
    for tentativa in range(3):
        try:
            buf = _gcs_read("usuarios.csv")
            if buf:
                df = pd.read_csv(buf, dtype=str, on_bad_lines='skip', encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].str.strip()
                return df.fillna("")
            time.sleep(0.3)
        except:
            if tentativa == 2: return pd.DataFrame()
            time.sleep(0.3)
    return pd.DataFrame()

def _verificar_validacoes_pendentes(user_nome):
    """Verifica se há PDFs por validar ou preço hora por aceitar."""
    try:
        users = _load_users_fresh()
        if users.empty: return False, False
        match = users[users['Nome'] == user_nome]
        if match.empty: return False, False
        row = match.iloc[0]
        pdfs_pendentes  = row.get('PDFs_Validados', 'Não') != 'Sim'
        preco_pendente  = row.get('PrecoHoraStatus', '') == ''
        return pdfs_pendentes, preco_pendente
    except:
        return False, False

def _render_validacao_obrigatoria(user_nome):
    """
    Ecrã de validação obrigatória — bloqueia toda a navegação até
    o utilizador validar os PDFs e aceitar/recusar o preço hora.
    Devolve True se ainda há validações pendentes, False se tudo OK.
    """
    users_live = _load_users_fresh()
    if users_live.empty:
        return False

    match = users_live[users_live['Nome'] == user_nome]
    if match.empty:
        return False

    user_idx  = match.index[0]
    user_data = match.iloc[0]

    pdfs_validados   = user_data.get('PDFs_Validados', 'Não')
    preco_status     = user_data.get('PrecoHoraStatus', '')
    preco_hora_valor = user_data.get('PrecoHora', '15.0')

    # Carregar PDFs obrigatórios
    try:
        pdfs_db = load_db("pdfs_obrigatorios.csv", [
            "ID", "Nome", "Descricao", "Data_Upload", "Upload_Por", "Ficheiro_b64"
        ], silent=True)
    except:
        pdfs_db = pd.DataFrame(columns=["ID","Nome","Descricao","Data_Upload","Upload_Por","Ficheiro_b64"])

    try:
        pdfs_vistos = json.loads(user_data.get('PDFs_Vistos', '[]'))
    except:
        pdfs_vistos = []

    total_pdfs      = len(pdfs_db) if not pdfs_db.empty else 0
    pdf_ids_validos = pdfs_db['ID'].tolist() if not pdfs_db.empty else []
    pdfs_val_count  = len([p for p in pdfs_vistos if p in pdf_ids_validos])

    # Determinar o que está pendente
    tem_pdfs_pendentes = (pdfs_validados != 'Sim') and (total_pdfs > 0)
    tem_preco_pendente = (preco_status == '')

    if not tem_pdfs_pendentes and not tem_preco_pendente:
        return False  # Tudo validado — routing normal

    # ── Estilos do ecrã de validação ─────────────────────────────────
    st.markdown("""
    <style>
    .val-header {
        background: linear-gradient(135deg, #DC2626, #991B1B);
        padding: 25px; border-radius: 20px; margin-bottom: 25px; text-align: center;
    }
    .val-step {
        background: rgba(255,255,255,0.05); border: 2px solid rgba(255,255,255,0.1);
        border-radius: 15px; padding: 20px; margin-bottom: 20px;
    }
    .val-step.done { border-color: #10B981; background: rgba(16,185,129,0.1); }
    .val-step.pending { border-color: #F59E0B; background: rgba(245,158,11,0.1); }
    .pdf-item {
        background: rgba(255,255,255,0.05); border-radius: 10px;
        padding: 15px; margin-bottom: 12px;
    }
    .pdf-item.visto { border-left: 4px solid #10B981; }
    .pdf-item.por-ver { border-left: 4px solid #EF4444; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────
    pendentes_lista = []
    if tem_pdfs_pendentes: pendentes_lista.append("documentos obrigatórios")
    if tem_preco_pendente: pendentes_lista.append("preço hora")

    st.markdown(f"""
    <div class="val-header">
        <div style="font-size:3rem;margin-bottom:15px;">⚠️</div>
        <h2 style="color:white;margin:0 0 10px 0;">AÇÃO OBRIGATÓRIA</h2>
        <p style="color:rgba(255,255,255,0.8);margin:0;">
            Olá <strong>{user_nome}</strong>, tens de completar os seguintes passos
            antes de aceder à aplicação:
        </p>
        <p style="color:rgba(255,255,255,0.6);font-size:0.9rem;margin:10px 0 0 0;">
            {'  ·  '.join([f'✗ Validar {p}' for p in pendentes_lista])}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Barra de Progresso Geral ──────────────────────────────────────
    total_passos      = (1 if tem_pdfs_pendentes else 0) + (1 if tem_preco_pendente else 0)
    passos_completos  = 0
    if not tem_pdfs_pendentes: passos_completos += 1
    if not tem_preco_pendente: passos_completos += 1

    pct_geral = int(passos_completos / max(total_passos + passos_completos, 1) * 100) if total_pdfs > 0 else 0
    pct_pdfs  = int(pdfs_val_count / total_pdfs * 100) if total_pdfs > 0 else 0

    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.1);border-radius:10px;padding:15px;margin-bottom:25px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="color:#94A3B8;font-size:0.9rem;">Progresso geral</span>
            <span style="color:#60A5FA;font-weight:bold;">
                {passos_completos}/{total_passos + passos_completos} passos completos
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # PASSO 1 — DOCUMENTOS OBRIGATÓRIOS
    # ════════════════════════════════════════════════════════════════
    if tem_pdfs_pendentes:
        st.markdown(f"""
        <div class="val-step pending">
            <h3 style="color:#F59E0B;margin:0 0 5px 0;">📄 Passo 1 — Documentos Obrigatórios</h3>
            <p style="color:#94A3B8;margin:0;font-size:0.9rem;">
                Lê e confirma cada documento. <strong>{pdfs_val_count}/{total_pdfs}</strong> validados.
            </p>
            <div style="background:rgba(0,0,0,0.3);border-radius:6px;height:8px;margin:12px 0 0 0;">
                <div style="background:#10B981;width:{pct_pdfs}%;height:8px;border-radius:6px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not pdfs_db.empty:
            for _, pdf in pdfs_db.iterrows():
                pdf_id   = str(pdf.get('ID', '')).strip()
                pdf_nome = pdf.get('Nome', 'Documento')
                pdf_desc = pdf.get('Descricao', '')
                visto    = pdf_id in pdfs_vistos
                classe   = "visto" if visto else "por-ver"

                st.markdown(f"""
                <div class="pdf-item {classe}">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <strong style="color:{'#10B981' if visto else '#EF4444'};">
                                {'✅' if visto else '📄'} {pdf_nome}
                            </strong>
                            <p style="color:#94A3B8;font-size:0.85rem;margin:4px 0 0 0;">{pdf_desc}</p>
                        </div>
                        <div style="color:{'#10B981' if visto else '#F59E0B'};font-size:0.85rem;font-weight:bold;">
                            {'Validado' if visto else 'Por ler'}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_dl, col_ok = st.columns([2, 1])
                with col_dl:
                    if pdf.get('Ficheiro_b64'):
                        try:
                            pdf_data = base64.b64decode(pdf['Ficheiro_b64'])
                            st.download_button(
                                f"📥 Descarregar: {pdf_nome}",
                                data=pdf_data,
                                file_name=f"{pdf_nome}.pdf",
                                mime="application/pdf",
                                key=f"app_dl_pdf_{pdf_id}",
                                use_container_width=True
                            )
                        except:
                            st.error("❌ Erro ao carregar PDF")

                with col_ok:
                    if not visto:
                        if st.button(
                            "✅ Confirmar leitura",
                            key=f"app_val_pdf_{pdf_id}",
                            use_container_width=True,
                            type="primary"
                        ):
                            pdfs_vistos.append(pdf_id)
                            novos_val = len([p for p in pdfs_vistos if p in pdf_ids_validos])
                            users_live.loc[user_idx, 'PDFs_Vistos'] = json.dumps(pdfs_vistos)

                            if novos_val >= total_pdfs:
                                users_live.loc[user_idx, 'PDFs_Validados']      = 'Sim'
                                users_live.loc[user_idx, 'PDFs_Validacao_Data'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                save_db(users_live, "usuarios.csv")
                                inv()
                                log_audit(
                                    usuario=user_nome, acao="VALIDAR_PDFS",
                                    tabela="usuarios.csv", registro_id=user_nome,
                                    detalhes=f"Todos os {novos_val} PDFs validados", ip=""
                                )
                                criar_notificacao(
                                    destinatario="admin",
                                    titulo="✅ PDFs Validados",
                                    mensagem=f"{user_nome} validou todos os documentos obrigatórios.",
                                    tipo="success", acao_url="/admin?tab=rh"
                                )
                                st.success("✅ Todos os documentos validados!")
                                time.sleep(1)
                            else:
                                users_live.loc[user_idx, 'PDFs_Vistos'] = json.dumps(pdfs_vistos)
                                save_db(users_live, "usuarios.csv")
                                inv()
                                st.success(f"✅ '{pdf_nome}' confirmado! ({novos_val}/{total_pdfs})")
                                time.sleep(0.5)
                            st.rerun()
                    else:
                        st.success("✅ Lido")

        if pdfs_val_count < total_pdfs:
            st.warning(f"⚠️ Faltam {total_pdfs - pdfs_val_count} documento(s) por confirmar.")
            st.stop()
        else:
            st.success("✅ Todos os documentos confirmados! Prossegue para o passo seguinte.")

    # ════════════════════════════════════════════════════════════════
    # PASSO 2 — VALIDAÇÃO DO PREÇO HORA
    # ════════════════════════════════════════════════════════════════
    if tem_preco_pendente:
        passo_num = 2 if tem_pdfs_pendentes else 1
        st.markdown(f"""
        <div class="val-step pending">
            <h3 style="color:#F59E0B;margin:0 0 5px 0;">💰 Passo {passo_num} — Validação do Preço Hora</h3>
            <p style="color:#94A3B8;margin:0;font-size:0.9rem;">
                Aceita ou recusa o preço hora proposto pela empresa.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.07);border:2px solid rgba(255,255,255,0.15);
            border-radius:15px;padding:30px;text-align:center;margin-bottom:20px;">
            <p style="color:#94A3B8;font-size:1rem;margin:0 0 10px 0;">Preço Hora Proposto:</p>
            <p style="color:#10B981;font-size:3.5rem;font-weight:900;margin:0 0 15px 0;">
                € {preco_hora_valor}
                <span style="font-size:1.5rem;color:#64748B;">/hora</span>
            </p>
            <p style="color:#64748B;font-size:0.85rem;margin:0;">
                A tua resposta ficará registada e será notificada ao administrador.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_ac, col_rec = st.columns(2)
        with col_ac:
            if st.button(
                "✅ ACEITAR o Preço Hora",
                key="app_aceitar_preco",
                use_container_width=True,
                type="primary"
            ):
                users_live2 = _load_users_fresh()
                if not users_live2.empty:
                    mask = users_live2['Nome'] == user_nome
                    if mask.any():
                        users_live2.loc[mask, 'PrecoHoraStatus'] = 'Aceite'
                        users_live2.loc[mask, 'PrecoHoraData']   = datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(users_live2, "usuarios.csv")
                        inv()
                        log_audit(
                            usuario=user_nome, acao="ACEITAR_PRECO_HORA",
                            tabela="usuarios.csv", registro_id=user_nome,
                            detalhes=f"Aceitou €{preco_hora_valor}/hora", ip=""
                        )
                        criar_notificacao(
                            destinatario="admin",
                            titulo="💰 Preço Hora Aceite",
                            mensagem=f"{user_nome} aceitou o preço de €{preco_hora_valor}/hora.",
                            tipo="success", acao_url="/admin?tab=rh"
                        )
                        st.success("✅ Preço hora aceite com sucesso!")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()

        with col_rec:
            if st.button(
                "❌ RECUSAR o Preço Hora",
                key="app_recusar_preco",
                use_container_width=True,
                type="secondary"
            ):
                users_live2 = _load_users_fresh()
                if not users_live2.empty:
                    mask = users_live2['Nome'] == user_nome
                    if mask.any():
                        users_live2.loc[mask, 'PrecoHoraStatus'] = 'Recusado'
                        users_live2.loc[mask, 'PrecoHoraData']   = datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(users_live2, "usuarios.csv")
                        inv()
                        log_audit(
                            usuario=user_nome, acao="RECUSAR_PRECO_HORA",
                            tabela="usuarios.csv", registro_id=user_nome,
                            detalhes=f"Recusou €{preco_hora_valor}/hora", ip=""
                        )
                        criar_notificacao(
                            destinatario="admin",
                            titulo="💰 Preço Hora RECUSADO",
                            mensagem=f"{user_nome} RECUSOU o preço de €{preco_hora_valor}/hora. Contactar para renegociação.",
                            tipo="error", acao_url="/admin?tab=rh"
                        )
                        st.warning("❌ Preço hora recusado. O admin será notificado para renegociação.")
                        time.sleep(1.5)
                        st.rerun()

        st.stop()

    return False  # Nenhuma validação pendente — routing normal

# =============================================================================
# 4. SIDEBAR (APENAS SE LOGADO)
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
        <div style="padding:12px;background:rgba(255,255,255,0.05);
            border-radius:12px;margin-bottom:16px;">
            <div style="font-size:1rem;font-weight:600;color:#F8FAFC;">
                👤 {st.session_state.user}
            </div>
            <div style="font-size:0.85rem;color:#94A3B8;">
                {st.session_state.tipo} | {st.session_state.cargo}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**{ICONS['app']} {t('language')}**")
        lang_opts = get_language_options()
        curr_lang = st.session_state.language
        sel_lang  = st.selectbox(
            "🌐",
            options=list(lang_opts.keys()),
            format_func=lambda x: lang_opts[x],
            index=list(lang_opts.keys()).index(curr_lang),
            label_visibility="collapsed",
            key="sidebar_language_sel"
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
                label_visibility="collapsed", key="sidebar_nav_cliente")
        elif tipo == 'Admin':
            menu_item = st.radio("Navegação",
                [f"{ICONS['dashboard']} Dashboard", f"{ICONS['admin']} Admin",
                 f"{ICONS['instrumentation']} Instrumentação",
                 f"{ICONS['profile']} Perfil", f"{ICONS['logout']} Logout"],
                label_visibility="collapsed", key="sidebar_nav_admin")
        elif tem_acesso_inst:
            menu_item = st.radio("Navegação",
                [f"{ICONS['dashboard']} Início", f"{ICONS['technician']} Obra",
                 f"{ICONS['instrumentation']} Instrumentação",
                 f"{ICONS['profile']} Perfil", f"{ICONS['logout']} Logout"],
                label_visibility="collapsed", key="sidebar_nav_chefe")
        else:
            menu_item = st.radio("Navegação",
                [f"{ICONS['dashboard']} Início", f"{ICONS['technician']} Obra",
                 f"{ICONS['profile']} Perfil", f"{ICONS['logout']} Logout"],
                label_visibility="collapsed", key="sidebar_nav_tecnico")

        st.session_state.menu_selected = menu_item
        st.divider()

        if st.button(f"{ICONS['logout']} {t('logout')}", use_container_width=True,
                     type="secondary", key="sidebar_logout_btn"):
            st.session_state.clear()
            st.rerun()

# =============================================================================
# 5. BOTTOM NAVIGATION BAR (MOBILE)
# =============================================================================
if st.session_state.get('user') and HAS_OPTION_MENU:
    tipo  = st.session_state.get('tipo', '')
    cargo = st.session_state.get('cargo', '')
    eh_cliente = (tipo == 'Cliente')

    if eh_cliente:
        nav_options = ["Portal", "Logout"]
        nav_icons   = ["house", "box-arrow-right"]
    elif tipo == 'Admin':
        nav_options = ["Dashboard", "Admin", "Instrumentação", "Perfil", "Logout"]
        nav_icons   = ["graph-up", "gear", "tools", "person", "box-arrow-right"]
    elif tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
        nav_options = ["Início", "Obra", "Instrumentação", "Perfil", "Logout"]
        nav_icons   = ["house", "tools", "wrench", "person", "box-arrow-right"]
    else:
        nav_options = ["Início", "Obra", "Perfil", "Logout"]
        nav_icons   = ["house", "tools", "person", "box-arrow-right"]

    current_menu  = st.session_state.get('menu_selected', '')
    default_index = 0
    if tipo == 'Admin':
        if "Admin"          in current_menu: default_index = 1
        elif "Instrumentação" in current_menu: default_index = 2
        elif "Perfil"        in current_menu: default_index = 3
        else:                                default_index = 0
    elif tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
        if "Obra"           in current_menu: default_index = 1
        elif "Instrumentação" in current_menu: default_index = 2
        elif "Perfil"        in current_menu: default_index = 3
        else:                                default_index = 0
    else:
        if "Obra"    in current_menu: default_index = 1
        elif "Perfil" in current_menu: default_index = 2
        else:                         default_index = 0

    selected = option_menu(
        menu_title=None,
        options=nav_options,
        icons=nav_icons,
        menu_icon="cast",
        default_index=default_index,
        orientation="horizontal",
        styles={
            "container":        {"padding":"0!important","background-color":"#1E293B",
                                 "position":"fixed","bottom":"0","width":"100%",
                                 "z-index":"999","border-top":"1px solid rgba(255,255,255,0.1)"},
            "icon":             {"color":"#F8FAFC","font-size":"20px"},
            "nav-link":         {"color":"#F8FAFC","font-size":"11px","margin":"0px",
                                 "text-align":"center","padding":"8px 4px"},
            "nav-link-selected":{"background-color":"#DC2626","color":"#FFFFFF"},
        }
    )

    nav_map = {
        "Início":         f"{ICONS['dashboard']} Início",
        "Portal":         f"{ICONS['dashboard']} Portal",
        "Obra":           f"{ICONS['technician']} Obra",
        "Instrumentação": f"{ICONS['instrumentation']} Instrumentação",
        "Dashboard":      f"{ICONS['dashboard']} Dashboard",
        "Admin":          f"{ICONS['admin']} Admin",
        "Perfil":         f"{ICONS['profile']} Perfil",
        "Logout":         "Logout",
    }

    new_menu = nav_map.get(selected, '')
    if new_menu and new_menu != st.session_state.get('menu_selected', ''):
        st.session_state.menu_selected = new_menu
        if selected == "Logout":
            st.session_state.clear()
        st.rerun()

    st.markdown("<div style='height:70px;'></div>", unsafe_allow_html=True)

# =============================================================================
# 6. ROUTING PRINCIPAL
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

    if "Logout" in menu:
        st.session_state.clear()
        st.rerun()

    # ══════════════════════════════════════════════════════════════════
    # ✅ BLOQUEIO CENTRALIZADO — verificar ANTES de qualquer routing
    # Só aplica a Técnicos e Chefes (não a Admin nem Cliente)
    # ══════════════════════════════════════════════════════════════════
    if tipo not in ['Admin', 'Cliente']:
        pdfs_pend, preco_pend = _verificar_validacoes_pendentes(user_nome)
        if pdfs_pend or preco_pend:
            _render_validacao_obrigatoria(user_nome)
            st.stop()

    # ── MODO CLIENTE ─────────────────────────────────────────────────
    if eh_cliente:
        st.markdown(f"# {ICONS['dashboard']} Portal do Cliente")
        from mod_cliente import render_cliente_portal
        render_cliente_portal()

    # ── MODO ADMIN ───────────────────────────────────────────────────
    elif tipo == 'Admin':
        if f"{ICONS['admin']} Admin" in menu:
            from mod_admin import render_admin
            render_admin(*DATA)
        elif f"{ICONS['instrumentation']} Instrumentação" in menu:
            st.markdown(f"# {ICONS['instrumentation']} Instrumentação Industrial")
            from mod_instrumentacao import render_instrumentacao
            render_instrumentacao(*DATA)
        elif f"{ICONS['profile']} Perfil" in menu:
            st.markdown(f"# {ICONS['profile']} Perfil do Utilizador")
            from mod_perfil import render_perfil
            render_perfil(*DATA)
        elif f"{ICONS['dashboard']} Dashboard" in menu or menu == '':
            st.markdown(f"# {ICONS['dashboard']} Dashboard Geral")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("👥 Utilizadores",  len(users))
            with c2: st.metric("🏭 Obras Ativas",
                len(obras_db[obras_db['Ativa']=='Ativa']) if not obras_db.empty else 0)
            with c3: st.metric("📋 Registos",      len(registos_db) if not registos_db.empty else 0)
            with c4: st.metric("⚠️ Incidentes",    len(incs_db)     if not incs_db.empty else 0)
            st.divider()
            from mod_dashboard import render_dashboard
            render_dashboard(*DATA)
        else:
            from mod_admin import render_admin
            render_admin(*DATA)

    # ── MODO TÉCNICO / CHEFE ─────────────────────────────────────────
    else:
        if f"{ICONS['technician']} Obra" in menu:
            st.markdown(f"# {ICONS['technician']} Área Técnica")
            if tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
                from mod_chefe import render_chefe
                render_chefe(*DATA)
            else:
                from mod_tecnico import render_tecnico
                render_tecnico(*DATA)

        elif f"{ICONS['instrumentation']} Instrumentação" in menu:
            if tem_acesso_inst:
                st.markdown(f"# {ICONS['instrumentation']} Instrumentação Industrial")
                from mod_instrumentacao import render_instrumentacao
                render_instrumentacao(*DATA)
            else:
                st.warning("⚠️ Não tem acesso a este módulo.")

        elif f"{ICONS['profile']} Perfil" in menu:
            st.markdown(f"# {ICONS['profile']} Perfil do Utilizador")
            from mod_perfil import render_perfil
            render_perfil(*DATA)

        else:
            # Default → Início
            from mod_inicio import render_inicio
            render_inicio(*DATA)

# =============================================================================
# 7. FOOTER
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

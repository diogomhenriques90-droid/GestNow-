import streamlit as st
import pandas as pd
import uuid, secrets, base64, io, json
from datetime import datetime, timedelta, date
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import time

from core import (
    save_db, inv, fh, sl, render_metric, load_db, canvas_to_b64,
    ICONS, COLORS, TIPOS_FRENTE, REGRAS_OURO,
    CATEGORIAS_SAFETY_WALK, log_audit, criar_notificacao, process_and_compress_image
)
from translations import t

# Mapeamento de Status para classes CSS
_STATUS_CSS = {
    "0": "pendente", "1": "aprovado", "2": "fechado",
    "-1": "fechado", "3": "fechado", "4": "fechado"
}

def render_tecnico(*args):
    """Renderiza módulo Técnico com perfil completo, PDFs obrigatórios e validação de Preço Hora"""

    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    user_nome  = st.session_state.get('user', 'Usuário')
    cargo_user = st.session_state.get('cargo', 'Técnico')
    user_tipo  = st.session_state.get('tipo', 'Técnico')

    is_chefe = (user_tipo in ['Chefe de Equipa', 'Admin', 'Gestor'] or
                cargo_user in ['Chefe de Equipa', 'Encarregado'])

    # ── Carregar dados frescos do utilizador ─────────────────────────
    try:
        users_fresh = load_db("usuarios.csv", [
            "Nome","Password","Tipo","Cargo","Email","Telefone","Morada","Localidade",
            "Concelho","Codigo_Postal","Naturalidade","Nacionalidade","NIF","NISS","CC",
            "CC_Validade","DataNasc","Estado_Civil","Sexo","Dependentes","Profissao",
            "Categoria_Profissional","Habilitacoes_Literarias","Contacto_Emergencia",
            "Nome_Emergencia","Grau_Parentesco","Banco_IBAN","Observacoes",
            "Tamanho_Camisola","Tamanho_Calca","Tamanho_Botas","Local",
            "PrecoHora","PrecoHoraStatus","PrecoHoraData","PIN","Foto",
            "Campos_Bloqueados","PDFs_Vistos","PDFs_Validados","PDFs_Validacao_Data"
        ])
        user_match = users_fresh[users_fresh['Nome'] == user_nome]
        if not user_match.empty:
            user_data = user_match.iloc[0]
            user_idx  = user_match.index[0]
        else:
            user_data = None
            user_idx  = None
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        user_data = None
        user_idx  = None

    # ── Carregar PDFs obrigatórios ────────────────────────────────────
    try:
        pdfs_db = load_db("pdfs_obrigatorios.csv", [
            "ID","Nome","Descricao","Data_Upload","Upload_Por","Ficheiro_b64"
        ])
    except:
        pdfs_db = pd.DataFrame(columns=["ID","Nome","Descricao","Data_Upload","Upload_Por","Ficheiro_b64"])

    # ── Header ───────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center;padding:30px 20px;
        background:linear-gradient(135deg,#1E293B,#0F172A);
        border-radius:20px;margin-bottom:30px;
        border:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:3rem;margin-bottom:10px;">{ICONS["technician"]}</div>
        <div style="font-size:1.8rem;font-weight:800;color:#F8FAFC;">{user_nome}</div>
        <div style="font-size:1rem;color:#94A3B8;">{cargo_user} | {user_tipo}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── CSS ───────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .rp-card {
        background:rgba(255,255,255,0.05); padding:18px; border-radius:15px;
        border-left:6px solid #3B82F6; margin-bottom:12px;
        box-shadow:0 4px 10px rgba(0,0,0,0.2);
    }
    .rp-card.pendente  { border-left-color:#F59E0B; }
    .rp-card.aprovado  { border-left-color:#10B981; }
    .rp-card.fechado   { border-left-color:#3B82F6; }
    .esign-seal {
        border:2px dashed #10B981; padding:15px; background:rgba(16,185,129,0.1);
        border-radius:10px; color:#10B981; font-family:monospace; font-size:0.85rem; margin-top:15px;
    }
    .pedido-card {
        background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.3);
        border-radius:10px; padding:15px; margin-bottom:10px;
    }
    .pdf-card {
        background:rgba(239,68,68,0.1); border:2px solid #EF4444;
        border-radius:10px; padding:20px; margin-bottom:15px; text-align:center;
    }
    .pdf-card.validado { background:rgba(16,185,129,0.1); border-color:#10B981; }
    .section-title {
        background:linear-gradient(135deg,#3B82F6,#1E40AF); color:white !important;
        padding:15px; border-radius:10px; margin:30px 0 20px 0;
        font-size:1.3rem; font-weight:bold;
    }
    .subsection-title {
        background:rgba(59,130,246,0.1); border-left:4px solid #3B82F6;
        padding:10px 15px; margin:20px 0 15px 0;
        font-size:1.1rem; font-weight:600; color:#F8FAFC !important;
    }
    .progress-container { background:rgba(255,255,255,0.1); padding:15px; border-radius:10px; margin-bottom:20px; }
    .progress-bar { background:linear-gradient(90deg,#10B981,#059669); height:10px; border-radius:5px; margin-top:10px; }
    .date-carousel {
        display:flex; gap:10px; overflow-x:auto; padding:15px;
        background:rgba(255,255,255,0.05); border-radius:15px; margin-bottom:20px;
        scrollbar-width:thin; scrollbar-color:#3B82F6 rgba(255,255,255,0.1);
    }
    .stTabs [data-baseweb="tab"] { color:#F8FAFC !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color:white !important; font-weight:bold; }
    .stTextInput label, .stNumberInput label, .stTextArea label,
    .stSelectbox label, .stDateInput label, .stTimeInput label,
    .stRadio label, .stCheckbox label { color:#F8FAFC !important; font-weight:500; }
    .stTextInput > div > div > input, .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea, .stSelectbox > div > div > div {
        background:#FFFFFF !important; color:#1E293B !important;
    }
    h1,h2,h3,h4,h5,h6 { color:#F8FAFC !important; }
    .stMarkdown p, div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] { color:#F8FAFC !important; }
    .streamlit-expanderHeader { color:#F8FAFC !important; background:rgba(255,255,255,0.05) !important; }
    .stForm label { color:#F8FAFC !important; }
    </style>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════
    # VERIFICAÇÃO DE PDFs OBRIGATÓRIOS
    # ═══════════════════════════════════════════════════════════════════
    if user_data is not None:
        pdfs_validados      = user_data.get('PDFs_Validados', 'Não')
        pdfs_validacao_data = user_data.get('PDFs_Validacao_Data', '')
        hoje_dt             = datetime.now()
        precisa_validar     = False

        if pdfs_validados != 'Sim':
            precisa_validar = True
        elif pdfs_validacao_data:
            try:
                dv = datetime.strptime(pdfs_validacao_data, "%d/%m/%Y %H:%M")
                if hoje_dt.day == 1 and (hoje_dt.month != dv.month or hoje_dt.year != dv.year):
                    precisa_validar = True
            except:
                precisa_validar = True

        if precisa_validar:
            if hoje_dt.day == 1:
                st.markdown("""
                <div style="background:#EF4444;color:white;padding:20px;border-radius:15px;text-align:center;margin-bottom:30px;">
                    <h2 style="margin:0 0 10px 0;">⚠️ VALIDAÇÃO MENSAL OBRIGATÓRIA</h2>
                    <p style="margin:0;">É dia 1! Deves visualizar e validar os documentos obrigatórios.</p>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:#EF4444;color:white;padding:20px;border-radius:15px;text-align:center;margin-bottom:30px;">
                    <h2 style="margin:0 0 10px 0;">⚠️ AÇÃO OBRIGATÓRIA</h2>
                    <p style="margin:0;">Deves visualizar e validar os documentos obrigatórios antes de continuar.</p>
                </div>""", unsafe_allow_html=True)

            st.markdown("### 📋 Documentos Obrigatórios")

            try:
                pdfs_vistos_json = user_data.get('PDFs_Vistos', '[]')
                pdfs_vistos = json.loads(pdfs_vistos_json)
            except:
                pdfs_vistos = []

            total_pdfs       = len(pdfs_db) if not pdfs_db.empty else 0
            pdf_ids_validos  = pdfs_db['ID'].tolist() if not pdfs_db.empty else []
            pdfs_val_count   = len([p for p in pdfs_vistos if p in pdf_ids_validos])

            if total_pdfs > 0:
                pct = int((pdfs_val_count / total_pdfs) * 100)
                st.markdown(f"""
                <div class="progress-container">
                    <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                        <span style="color:#94A3B8;">📊 Progresso</span>
                        <span style="color:#10B981;font-weight:bold;">{pdfs_val_count}/{total_pdfs} PDFs validados</span>
                    </div>
                    <div class="progress-bar" style="width:{pct}%;"></div>
                </div>""", unsafe_allow_html=True)

            if not pdfs_db.empty:
                for _, pdf in pdfs_db.iterrows():
                    pdf_id   = pdf.get('ID', '')
                    pdf_nome = pdf.get('Nome', 'Documento')
                    pdf_desc = pdf.get('Descricao', '')
                    visto    = pdf_id in pdfs_vistos

                    with st.container():
                        if visto:
                            st.markdown(f"""
                            <div class="pdf-card validado">
                                <h4 style="margin:0 0 10px 0;color:#10B981;">✅ {pdf_nome}</h4>
                                <p style="margin:0 0 15px 0;color:#94A3B8;">{pdf_desc}</p>
                                <div style="background:#10B981;color:white;padding:10px;border-radius:8px;font-weight:bold;">
                                    ✅ Documento validado
                                </div>
                            </div>""", unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="pdf-card">
                                <h4 style="margin:0 0 10px 0;color:#EF4444;">📄 {pdf_nome}</h4>
                                <p style="margin:0 0 15px 0;color:#94A3B8;">{pdf_desc}</p>
                            </div>""", unsafe_allow_html=True)

                        if pdf.get('Ficheiro_b64'):
                            try:
                                pdf_data = base64.b64decode(pdf['Ficheiro_b64'])
                                st.download_button(
                                    label="📄 Visualizar/Descarregar PDF",
                                    data=pdf_data,
                                    file_name=f"{pdf_nome}.pdf",
                                    mime="application/pdf",
                                    key=f"view_pdf_{pdf_id}",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"❌ Erro ao carregar PDF: {str(e)}")

                        if not visto:
                            if st.button(f"✅ Confirmar Visualização: {pdf_nome}",
                                         key=f"validar_{pdf_id}", use_container_width=True, type="primary"):
                                if pdf_id not in pdfs_vistos:
                                    pdfs_vistos.append(pdf_id)
                                users_fresh.loc[user_idx, 'PDFs_Vistos'] = json.dumps(pdfs_vistos)
                                novos_val = len([p for p in pdfs_vistos if p in pdf_ids_validos])
                                save_db(users_fresh, "usuarios.csv")
                                st.cache_data.clear()
                                inv()

                                if novos_val >= total_pdfs:
                                    users_fresh.loc[user_idx, 'PDFs_Validados']     = 'Sim'
                                    users_fresh.loc[user_idx, 'PDFs_Validacao_Data']= datetime.now().strftime("%d/%m/%Y %H:%M")
                                    save_db(users_fresh, "usuarios.csv")
                                    st.cache_data.clear()
                                    inv()
                                    log_audit(usuario=user_nome, acao="VALIDAR_PDFS_OBRIGATORIOS",
                                              tabela="usuarios.csv", registro_id=user_nome,
                                              detalhes=f"Validou {novos_val} PDFs", ip="")
                                    criar_notificacao(destinatario="admin",
                                        titulo="✅ Colaborador Validou PDFs",
                                        mensagem=f"{user_nome} validou {novos_val} PDF(s)",
                                        tipo="success", acao_url="/admin?tab=rh")
                                    st.markdown("""
                                    <div style="background:#10B981;color:white;padding:30px;border-radius:15px;text-align:center;margin:30px 0;">
                                        <h2 style="margin:0 0 15px 0;">✅ VALIDAÇÃO DE PDFs CONCLUÍDA!</h2>
                                        <p style="margin:0;">Todos os documentos foram validados.</p>
                                    </div>""", unsafe_allow_html=True)
                                    st.balloons()
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    restantes = total_pdfs - novos_val
                                    st.markdown(f"""
                                    <div style="background:#10B981;color:white;padding:20px;border-radius:10px;margin:20px 0;">
                                        <p style="margin:0;">✅ '{pdf_nome}' validado!</p>
                                        <p style="margin:10px 0 0 0;font-size:0.9rem;">📊 {novos_val}/{total_pdfs} PDFs | Faltam {restantes}</p>
                                    </div>""", unsafe_allow_html=True)
                                    time.sleep(2)
                                    st.rerun()

            if total_pdfs > 0:
                st.warning(f"⚠️ Deves validar TODOS os {total_pdfs} PDFs antes de continuar.")
                st.stop()

    # ═══════════════════════════════════════════════════════════════════
    # VALIDAÇÃO DE PREÇO HORA
    # ═══════════════════════════════════════════════════════════════════
    if user_data is not None:
        preco_status    = user_data.get('PrecoHoraStatus', '')
        preco_hora_valor= user_data.get('PrecoHora', '15.0')

        if preco_status == '':
            st.markdown("""
            <div style="background:#F59E0B;color:white;padding:20px;border-radius:15px;text-align:center;margin-bottom:30px;">
                <h2 style="margin:0 0 10px 0;">⏳ VALIDAÇÃO DE PREÇO HORA</h2>
                <p style="margin:0;">Deves aceitar ou recusar o teu preço hora antes de continuar.</p>
            </div>""", unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.1);padding:30px;border-radius:15px;text-align:center;">
                <p style="font-size:1.2rem;margin:0 0 20px 0;"><strong>Preço Hora Proposto:</strong></p>
                <p style="font-size:3rem;font-weight:bold;color:#10B981;margin:0 0 30px 0;">€ {preco_hora_valor}/hora</p>
            </div>""", unsafe_allow_html=True)

            col_a1, col_a2 = st.columns(2)
            with col_a1:
                if st.button("✅ Aceitar Preço Hora", key="aceitar_preco", use_container_width=True, type="primary"):
                    users_fresh.loc[user_idx, 'PrecoHoraStatus'] = 'Aceite'
                    users_fresh.loc[user_idx, 'PrecoHoraData']   = datetime.now().strftime("%d/%m/%Y %H:%M")
                    save_db(users_fresh, "usuarios.csv")
                    log_audit(usuario=user_nome, acao="ACEITAR_PRECO_HORA",
                              tabela="usuarios.csv", registro_id=user_nome,
                              detalhes=f"Aceitou €{preco_hora_valor}/hora", ip="")
                    criar_notificacao(destinatario="admin", titulo="💰 Preço Hora Aceite",
                        mensagem=f"{user_nome} aceitou €{preco_hora_valor}", tipo="success", acao_url="/admin?tab=rh")
                    inv()
                    st.success("✅ Preço hora aceite!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()

            with col_a2:
                if st.button("❌ Recusar Preço Hora", key="recusar_preco", use_container_width=True, type="secondary"):
                    users_fresh.loc[user_idx, 'PrecoHoraStatus'] = 'Recusado'
                    users_fresh.loc[user_idx, 'PrecoHoraData']   = datetime.now().strftime("%d/%m/%Y %H:%M")
                    save_db(users_fresh, "usuarios.csv")
                    log_audit(usuario=user_nome, acao="RECUSAR_PRECO_HORA",
                              tabela="usuarios.csv", registro_id=user_nome,
                              detalhes=f"Recusou €{preco_hora_valor}/hora", ip="")
                    criar_notificacao(destinatario="admin", titulo="💰 Preço Hora Recusado",
                        mensagem=f"{user_nome} RECUSOU €{preco_hora_valor}", tipo="warning", acao_url="/admin?tab=rh")
                    inv()
                    st.warning("❌ Preço hora recusado. Contacta o admin.")
                    time.sleep(2)
                    st.rerun()

            st.stop()

        elif preco_status == 'Recusado':
            st.warning("⚠️ O teu preço hora foi recusado. Contacta o admin para renegociação.")
            st.stop()

    # ═══════════════════════════════════════════════════════════════════
    # TABS PRINCIPAIS
    # ═══════════════════════════════════════════════════════════════════
    menu = [f"{ICONS['dashboard']} Pontos", f"{ICONS['safety']} Segurança (HSE)",
            f"{ICONS['profile']} Perfil", f"{ICONS['material']} Pedidos"]
    if is_chefe:
        menu.insert(1, f"{ICONS['reports']} Folha de Ponto")

    tabs = st.tabs(menu)

    # ═══ TAB 0: REGISTO DE PONTO ══════════════════════════════════════
    with tabs[0]:
        st.markdown(f"### {ICONS['dashboard']} Registo de Ponto")

        hoje = date.today()
        if 'data_consulta' not in st.session_state:
            st.session_state.data_consulta = hoje

        inicio_sem = hoje - timedelta(days=hoje.weekday())
        dias_sem   = [inicio_sem + timedelta(days=i) for i in range(14)]

        st.markdown('<div class="date-carousel">', unsafe_allow_html=True)
        cols_cal = st.columns(len(dias_sem))
        for i, d in enumerate(dias_sem):
            with cols_cal[i]:
                selecionado = d == st.session_state.data_consulta
                if st.button(
                    f"{d.strftime('%a')[:3]}\n{d.day} {d.strftime('%b')[:3]}",
                    key=f"date_{d.strftime('%Y-%m-%d')}",
                    use_container_width=True,
                    type="primary" if selecionado else "secondary"
                ):
                    st.session_state.data_consulta = d
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander(f"➕ Registar Trabalho em {st.session_state.data_consulta.strftime('%d/%m/%Y')}", expanded=True):
            st.markdown("#### ⏱️ Períodos de Trabalho")
            st.caption("Adiciona todos os períodos trabalhados neste dia")

            if 'periodos_trabalho' not in st.session_state:
                st.session_state.periodos_trabalho = [{"entrada": "08:00", "saida": "12:00"}]

            if st.button("➕ Adicionar Outro Período", use_container_width=True, type="secondary", key="add_periodo"):
                st.session_state.periodos_trabalho.append({"entrada": "13:00", "saida": "17:00"})
                st.rerun()

            st.divider()

            with st.form("ponto_form_elite"):
                obras_list = obras_db['Obra'].unique() if not obras_db.empty else ["Geral"]
                col1, col2 = st.columns(2)
                with col1: obra   = st.selectbox(f"{ICONS['app']} Selecionar Obra", obras_list, key="reg_obra")
                with col2: frente = st.selectbox(f"{ICONS['reports']} Frente de Trabalho", TIPOS_FRENTE, key="reg_frente")

                total_horas_dia = 0
                for idx, periodo in enumerate(st.session_state.periodos_trabalho):
                    st.markdown(f"**Período {idx + 1}**")
                    col_e, col_s = st.columns(2)
                    with col_e:
                        entrada = st.time_input(f"Entrada {idx+1}",
                            value=datetime.strptime(periodo["entrada"], "%H:%M").time(),
                            key=f"period_{idx}_entrada")
                    with col_s:
                        saida = st.time_input(f"Saída {idx+1}",
                            value=datetime.strptime(periodo["saida"], "%H:%M").time(),
                            key=f"period_{idx}_saida")
                    t1 = datetime.combine(date.today(), entrada)
                    t2 = datetime.combine(date.today(), saida)
                    delta_h = round(max((t2 - t1).seconds / 3600, 0), 2)
                    total_horas_dia += delta_h
                    st.markdown("---")

                if total_horas_dia > 0:
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.1);border:2px solid #10B981;
                        border-radius:10px;padding:15px;margin:20px 0;">
                        <p style="margin:0;font-size:1.1rem;color:#10B981;">
                            <strong>⏱️ Total de horas: {total_horas_dia:.2f}h</strong>
                        </p>
                    </div>""", unsafe_allow_html=True)

                relat = st.text_area("📝 Relatório de Atividades",
                    placeholder="Descreve o trabalho realizado neste dia...", key="reg_relatorio")

                if st.form_submit_button(f"{ICONS['save']} Gravar Registo", use_container_width=True, type="primary"):
                    if total_horas_dia <= 0:
                        st.error("⚠️ Deves registar pelo menos um período de trabalho válido.")
                    else:
                        # ✅ CORRIGIDO: ler valores reais dos time_inputs
                        for idx, periodo in enumerate(st.session_state.periodos_trabalho):
                            entrada_v = st.session_state.get(f"period_{idx}_entrada") or \
                                        datetime.strptime(periodo["entrada"], "%H:%M").time()
                            saida_v   = st.session_state.get(f"period_{idx}_saida") or \
                                        datetime.strptime(periodo["saida"], "%H:%M").time()
                            t1 = datetime.combine(date.today(), entrada_v)
                            t2 = datetime.combine(date.today(), saida_v)
                            delta_h = round(max((t2 - t1).seconds / 3600, 0), 2)
                            if delta_h > 0:
                                new_r = pd.DataFrame([{
                                    "ID":         str(uuid.uuid4())[:8].upper(),
                                    "Data":       st.session_state.data_consulta.strftime("%d/%m/%Y"),
                                    "Técnico":    user_nome,
                                    "Obra":       obra,
                                    "Frente":     frente,
                                    "Turnos":     f"{entrada_v.strftime('%H:%M')}-{saida_v.strftime('%H:%M')}",
                                    "Horas_Total":delta_h,
                                    "Relatorio":  relat,
                                    "Status":     "0",
                                    "Periodo":    idx + 1
                                }])
                                updated = pd.concat([registos_db, new_r], ignore_index=True) if not registos_db.empty else new_r
                                save_db(updated, "registos.csv")
                                log_audit(usuario=st.session_state.user, acao="REGISTAR_PONTO",
                                          tabela="registos.csv", registro_id=new_r['ID'].iloc[0],
                                          detalhes=f"{user_nome} registou {delta_h}h em {obra}", ip="")

                        st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"12:00"}]
                        st.success(f"{ICONS['approved']} Ponto registado! ({total_horas_dia:.2f}h totais)")
                        inv()
                        st.rerun()

        # Cards do dia selecionado
        st.markdown(f"### Registos de {st.session_state.data_consulta.strftime('%d/%m/%Y')}")
        if not registos_db.empty:
            meus_regs = registos_db[registos_db['Técnico'] == user_nome]
            regs_dia  = meus_regs[
                pd.to_datetime(meus_regs['Data'], dayfirst=True, errors='coerce').dt.date == st.session_state.data_consulta
            ]
            if regs_dia.empty:
                st.caption("ℹ️ Nenhum registo encontrado para este dia.")
            else:
                total_display = regs_dia['Horas_Total'].astype(float).sum()
                st.markdown(f"**Total: {fh(total_display)}**")
                for _, r in regs_dia.iterrows():
                    status_info  = sl(r.get('Status','0'))
                    cor_status   = status_info[3]
                    texto_status = status_info[0]
                    # ✅ CORRIGIDO: mapeamento correcto para classes CSS
                    classe_card  = _STATUS_CSS.get(str(r.get('Status','0')), 'pendente')
                    periodo_info = f" (Período {r.get('Periodo',1)})" if str(r.get('Periodo',1)) != "1" else ""
                    relatorio_text = str(r.get("Relatorio",""))[:100]

                    st.markdown(
                        f'<div class="rp-card {classe_card}">'
                        f'<b>{r.get("Obra","")}{periodo_info}</b> | {r.get("Turnos","")} '
                        f'(<b>{fh(r.get("Horas_Total",0))}</b>)<br>'
                        f'<small>{r.get("Frente","")}</small><br>'
                        f'<small style="color:#94A3B8;">{relatorio_text}</small><br>'
                        f'<small style="color:{cor_status};">{texto_status}</small>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

    # ═══ TAB FOLHA DE PONTO (só chefe) ════════════════════════════════
    offset = 0
    if is_chefe:
        offset = 1
        with tabs[1]:
            st.markdown(f"### {ICONS['reports']} Folha de Ponto & Assinatura Digital")
            st.caption("Gera e assina digitalmente a folha de ponto semanal da equipa.")

            obra_f = st.selectbox(f"{ICONS['app']} Obra para Validar",
                obras_db['Obra'].unique() if not obras_db.empty else ["Sem Obras"],
                key="esign_obra")

            inicio_sem_d = hoje - timedelta(days=hoje.weekday())
            col_p1, col_p2 = st.columns(2)
            with col_p1: semana_inicio = st.date_input("Início da Semana", value=inicio_sem_d, key="fp_inicio")
            with col_p2: semana_fim    = st.date_input("Fim da Semana", value=inicio_sem_d + timedelta(days=6), key="fp_fim")

            if not registos_db.empty:
                regs_fp = registos_db[
                    (registos_db['Obra'] == obra_f) &
                    (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date >= semana_inicio) &
                    (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date <= semana_fim)
                ]
                if not regs_fp.empty:
                    st.markdown(f"### 📋 Registos de {semana_inicio.strftime('%d/%m')} a {semana_fim.strftime('%d/%m/%Y')}")
                    for tecnico in regs_fp['Técnico'].unique():
                        regs_t = regs_fp[regs_fp['Técnico'] == tecnico]
                        total  = regs_t['Horas_Total'].astype(float).sum()
                        st.markdown(f"""
                        <div class="pedido-card">
                            <b>👤 {tecnico}</b><br>
                            <small>{len(regs_t)} dias registados | <b>{total:.1f}h totais</b></small>
                        </div>""", unsafe_allow_html=True)

                    st.markdown("### ✍️ Assinatura do Responsável")
                    canvas_sig = None
                    try:
                        canvas_sig = st_canvas(
                            fill_color="rgba(255,255,255,0)", stroke_width=2.5,
                            stroke_color="#3B82F6", background_color="#FFFFFF",
                            height=180, width=400, drawing_mode="freedraw",
                            key="canvas_esign_fp"
                        )
                    except Exception:
                        st.info("ℹ️ Canvas de assinatura não disponível neste ambiente.")

                    nome_resp = st.text_input("Nome do Responsável / Cliente",
                        placeholder="Ex: Eng. João Silva", key="fp_resp_nome")

                    if st.button(f"{ICONS['reports']} Gerar Folha com Selo de Segurança",
                                 use_container_width=True, type="primary", key="btn_gerar_folha"):
                        if nome_resp:
                            esign_id  = secrets.token_hex(6).upper()
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            # ✅ CORRIGIDO: converter canvas para base64 antes de guardar
                            sig_b64 = ""
                            if canvas_sig is not None and canvas_sig.image_data is not None:
                                sig_b64 = canvas_to_b64(canvas_sig.image_data) or ""

                            nova_folha = pd.DataFrame([{
                                "ID":             str(uuid.uuid4())[:8].upper(),
                                "Obra":           obra_f,
                                "Periodo":        f"{semana_inicio.strftime('%d/%m')} - {semana_fim.strftime('%d/%m/%Y')}",
                                "Responsavel":    nome_resp,
                                "Data_Assinatura":timestamp,
                                "Assinatura_b64": sig_b64,
                                "Selo":           esign_id,
                                "Status":         "Assinado"
                            }])
                            updated = pd.concat([folhas_db, nova_folha], ignore_index=True) if not folhas_db.empty else nova_folha
                            save_db(updated, "folhas_ponto.csv")
                            log_audit(usuario=st.session_state.user, acao="ASSINAR_FOLHA_PONTO",
                                      tabela="folhas_ponto.csv", registro_id=nova_folha['ID'].iloc[0],
                                      detalhes=f"Folha assinada por {nome_resp} para {obra_f}", ip="")
                            st.markdown(f"""
                            <div class="esign-seal">
                                <b>🔒 SELO GESTNOW #{esign_id}</b><br>
                                ASSINADO POR: {nome_resp}<br>
                                DATA/HORA: {timestamp}<br>
                                PERÍODO: {semana_inicio.strftime('%d/%m')} a {semana_fim.strftime('%d/%m/%Y')}<br>
                                OBRA: {obra_f}
                            </div>""", unsafe_allow_html=True)
                            st.success(f"{ICONS['approved']} Folha #{esign_id} gerada e assinada!")
                            inv()
                            st.rerun()
                        else:
                            st.warning("⚠️ Fornece o nome do responsável.")
                else:
                    st.info(f"📋 Sem registos de ponto para {obra_f} neste período.")
            else:
                st.info("📋 Sem registos de ponto disponíveis.")

    # ═══ TAB HSE ══════════════════════════════════════════════════════
    with tabs[1 + offset]:
        st.markdown(f"### {ICONS['safety']} Regras de Ouro")
        for ic, tit, des in REGRAS_OURO:
            with st.expander(f"{ic} {tit}"):
                st.write(des)

        st.divider()
        st.markdown(f"### {ICONS['safety']} Reportar Incidente HSE")
        with st.form("hse_report"):
            io_hse = st.selectbox(f"{ICONS['app']} Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="hse_obra")
            it_hse = st.selectbox("Gravidade", ["Baixa","Média","Alta (Crítica)"], key="hse_grav")
            id_hse = st.text_area("Descrição da Ocorrência / Condição Insegura", key="hse_desc")

            if st.form_submit_button(f"{ICONS['safety']} Submeter Alerta HSE", use_container_width=True, type="primary"):
                if id_hse:
                    ni = pd.DataFrame([{
                        "ID":       str(uuid.uuid4())[:8].upper(),
                        "Data":     date.today().strftime("%d/%m/%Y"),
                        "Utilizador":user_nome,
                        "Obra":     io_hse,
                        "Status":   "Aberto",
                        "Gravidade":it_hse,
                        "Descricao":id_hse,
                        "Tipo":     "HSE"
                    }])
                    updated = pd.concat([incs_db, ni], ignore_index=True) if not incs_db.empty else ni
                    save_db(updated, "incidentes.csv")
                    log_audit(usuario=st.session_state.user, acao="REPORTAR_INCIDENTE_HSE",
                              tabela="incidentes.csv", registro_id=ni['ID'].iloc[0],
                              detalhes=f"Incidente por {user_nome} em {io_hse}", ip="")
                    inv()
                    st.success(f"{ICONS['approved']} Alerta HSE enviado!")
                    st.rerun()
                else:
                    st.warning("⚠️ Descreve o incidente.")

    # ═══ TAB PERFIL ═══════════════════════════════════════════════════
    # ✅ CORRIGIDO: tab Perfil é sempre tabs[-2] (o penúltimo)
    with tabs[-2]:
        st.markdown(f"### {ICONS['profile']} Perfil do Colaborador")

        if user_data is not None:
            try:
                campos_bloqueados = json.loads(user_data.get('Campos_Bloqueados', '[]'))
            except:
                campos_bloqueados = []

            st.markdown('<div class="section-title">✏️ Editar Perfil</div>', unsafe_allow_html=True)

            with st.form("form_editar_perfil"):
                st.markdown('<div class="subsection-title">📋 Identificação</div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    telefone   = st.text_input("Contacto Telefónico", value=user_data.get('Telefone',''),     disabled='Telefone' in campos_bloqueados,              key="edit_tel")
                    email_v    = st.text_input("Email",               value=user_data.get('Email',''),        disabled='Email' in campos_bloqueados,                 key="edit_email")
                    c_emerg    = st.text_input("Contacto Emergência", value=user_data.get('Contacto_Emergencia',''), disabled='Contacto_Emergencia' in campos_bloqueados, key="edit_emerg")
                with col2:
                    n_emerg    = st.text_input("Nome Emergência",     value=user_data.get('Nome_Emergencia',''),    disabled='Nome_Emergencia' in campos_bloqueados,    key="edit_n_emerg")
                    grau       = st.text_input("Grau Parentesco",     value=user_data.get('Grau_Parentesco',''),    disabled='Grau_Parentesco' in campos_bloqueados,    key="edit_grau")

                st.markdown('<div class="subsection-title">📍 Morada</div>', unsafe_allow_html=True)
                morada = st.text_input("Morada", value=user_data.get('Morada',''), disabled='Morada' in campos_bloqueados, key="edit_morada")
                c3, c4, c5 = st.columns(3)
                with c3: localidade = st.text_input("Localidade",    value=user_data.get('Localidade',''),    disabled='Localidade' in campos_bloqueados,    key="edit_loc")
                with c4: concelho   = st.text_input("Concelho",      value=user_data.get('Concelho',''),      disabled='Concelho' in campos_bloqueados,      key="edit_conc")
                with c5: cod_postal = st.text_input("Código Postal",  value=user_data.get('Codigo_Postal',''), disabled='Codigo_Postal' in campos_bloqueados, key="edit_cp")

                st.markdown('<div class="subsection-title">🌍 Dados Pessoais</div>', unsafe_allow_html=True)
                col6, col7 = st.columns(2)
                with col6:
                    naturalidade = st.text_input("Naturalidade", value=user_data.get('Naturalidade',''), disabled='Naturalidade' in campos_bloqueados, key="edit_nat")
                    ec_opts = ["Solteiro(a)","Casado(a)","Divorciado(a)","Viúvo(a)","União de Facto"]
                    ec_val  = user_data.get('Estado_Civil','Solteiro(a)')
                    estado_civil = st.selectbox("Estado Civil", ec_opts,
                        index=ec_opts.index(ec_val) if ec_val in ec_opts else 0,
                        disabled='Estado_Civil' in campos_bloqueados, key="edit_ec")
                with col7:
                    nacionalidade = st.text_input("Nacionalidade", value=user_data.get('Nacionalidade','Portugal'), disabled='Nacionalidade' in campos_bloqueados, key="edit_nac")
                    sexo_opts = ["Masculino","Feminino"]
                    sexo_val  = user_data.get('Sexo','Masculino')
                    sexo = st.radio("Sexo", sexo_opts,
                        index=sexo_opts.index(sexo_val) if sexo_val in sexo_opts else 0,
                        horizontal=True, disabled='Sexo' in campos_bloqueados, key="edit_sexo")

                st.markdown('<div class="subsection-title">🆔 Documentos</div>', unsafe_allow_html=True)
                col8, col9 = st.columns(2)
                with col8:
                    nif  = st.text_input("NIF",  value=user_data.get('NIF',''),  disabled='NIF' in campos_bloqueados,  key="edit_nif")
                    cc   = st.text_input("CC",   value=user_data.get('CC',''),   disabled='CC' in campos_bloqueados,   key="edit_cc")
                    niss = st.text_input("NISS", value=user_data.get('NISS',''), disabled='NISS' in campos_bloqueados, key="edit_niss")
                with col9:
                    cc_val = st.text_input("Validade CC", value=user_data.get('CC_Validade',''), disabled='CC_Validade' in campos_bloqueados, key="edit_cc_val")
                    dep_raw = user_data.get('Dependentes','0')
                    try: dep_int = int(dep_raw) if dep_raw else 0
                    except: dep_int = 0
                    dependentes = st.number_input("Dependentes", min_value=0, value=dep_int, disabled='Dependentes' in campos_bloqueados, key="edit_dep")

                st.markdown('<div class="subsection-title">💼 Dados Profissionais</div>', unsafe_allow_html=True)
                profissao = st.text_input("Profissão", value=user_data.get('Profissao',''), disabled='Profissao' in campos_bloqueados, key="edit_prof")
                col10, col11 = st.columns(2)
                with col10:
                    categoria = st.text_input("Categoria Profissional", value=user_data.get('Categoria_Profissional',''), disabled='Categoria_Profissional' in campos_bloqueados, key="edit_cat")
                with col11:
                    hab_opts = ["4º Ano","6º Ano","9º Ano","12º Ano","Curso Técnico","Licenciatura","Mestrado","Doutoramento"]
                    hab_val  = user_data.get('Habilitacoes_Literarias','')
                    habilitacoes = st.selectbox("Habilitações", hab_opts,
                        index=hab_opts.index(hab_val) if hab_val in hab_opts else 0,
                        disabled='Habilitacoes_Literarias' in campos_bloqueados, key="edit_hab")

                st.markdown('<div class="subsection-title">👕 Fardamento</div>', unsafe_allow_html=True)
                col12, col13, col14 = st.columns(3)
                cam_opts = ["XS","S","M","L","XL","XXL","XXXL"]
                cal_opts = ["XS (34/36)","S (38)","M (40/42)","L (42/44)","XL (46/48)","XXL (50/52)"]
                bot_opts = ["40","41","42","43","44","45","Outro"]
                with col12:
                    cam_v = user_data.get('Tamanho_Camisola','M')
                    tam_camisola = st.selectbox("Camisola", cam_opts, index=cam_opts.index(cam_v) if cam_v in cam_opts else 2, key="edit_cam")
                with col13:
                    cal_v = user_data.get('Tamanho_Calca','')
                    tam_calca = st.selectbox("Calça", cal_opts, index=cal_opts.index(cal_v) if cal_v in cal_opts else 0, key="edit_calc")
                with col14:
                    bot_v = user_data.get('Tamanho_Botas','')
                    tam_botas = st.selectbox("Botas", bot_opts, index=bot_opts.index(bot_v) if bot_v in bot_opts else 0, key="edit_bot")

                st.markdown('<div class="subsection-title">📝 Observações</div>', unsafe_allow_html=True)
                observacoes = st.text_area("Observações", value=user_data.get('Observacoes',''), disabled='Observacoes' in campos_bloqueados, key="edit_obs")

                st.info("🔒 Nome, Tipo, Cargo e IBAN são geridos pelo Admin.")

                if st.form_submit_button("💾 Guardar Alterações", use_container_width=True, type="primary"):
                    updates = {
                        'Telefone': telefone, 'Email': email_v, 'Morada': morada,
                        'Localidade': localidade, 'Concelho': concelho, 'Codigo_Postal': cod_postal,
                        'Naturalidade': naturalidade, 'Nacionalidade': nacionalidade,
                        'Estado_Civil': estado_civil, 'Sexo': sexo, 'NIF': nif,
                        'CC': cc, 'CC_Validade': cc_val, 'NISS': niss,
                        'Dependentes': str(dependentes), 'Profissao': profissao,
                        'Categoria_Profissional': categoria, 'Habilitacoes_Literarias': habilitacoes,
                        'Contacto_Emergencia': c_emerg, 'Nome_Emergencia': n_emerg,
                        'Grau_Parentesco': grau, 'Tamanho_Camisola': tam_camisola,
                        'Tamanho_Calca': tam_calca, 'Tamanho_Botas': tam_botas, 'Observacoes': observacoes
                    }
                    for campo, valor in updates.items():
                        if campo not in campos_bloqueados:
                            users_fresh.loc[user_idx, campo] = valor
                    save_db(users_fresh, "usuarios.csv")
                    log_audit(usuario=user_nome, acao="EDITAR_PERFIL",
                              tabela="usuarios.csv", registro_id=user_nome,
                              detalhes="Perfil atualizado", ip="")
                    inv()
                    st.success("✅ Perfil atualizado com sucesso!")
                    st.rerun()
        else:
            st.warning("⚠️ Não foi possível carregar os dados do utilizador.")

    # ═══ TAB PEDIDOS ══════════════════════════════════════════════════
    with tabs[-1]:
        st.markdown(f"### {ICONS['material']} Pedidos & Documentos")

        sub_fer, sub_epi, sub_mat, sub_gas, sub_avar, sub_meus = st.tabs([
            "🔧 Ferramentas", "🦺 EPIs", "📦 Materiais", "⛽ Gasóleo", "🔧 Avarias", "📋 Meus Pedidos"
        ])

        with sub_fer:
            st.markdown("#### 🔧 Pedir Ferramentas")
            with st.form("form_pedir_fer"):
                obra_ped  = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_fer_obra")
                desc_fer  = st.text_area("Descrição da ferramenta necessária", key="ped_fer_desc")
                urg_fer   = st.selectbox("Urgência", ["Baixa","Média","Alta"], key="ped_fer_urg")
                foto_fer  = st.file_uploader("Foto da ferramenta (opcional)", type=["png","jpg","jpeg"], key="ped_fer_foto")
                if st.form_submit_button("📤 Enviar Pedido de Ferramenta", use_container_width=True, type="primary"):
                    if desc_fer:
                        foto_b64 = process_and_compress_image(foto_fer) if foto_fer else None
                        novo_ped = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_ped,
                            "Descricao": desc_fer, "Urgencia": urg_fer,
                            "Foto_b64": foto_b64, "Status": "Pendente"
                        }])
                        updated = pd.concat([req_fer_db, novo_ped], ignore_index=True) if not req_fer_db.empty else novo_ped
                        save_db(updated, "req_ferramentas.csv")
                        log_audit(usuario=st.session_state.user, acao="PEDIR_FERRAMENTA",
                                  tabela="req_ferramentas.csv", registro_id=novo_ped['ID'].iloc[0],
                                  detalhes=f"Pedido ferramenta por {user_nome} em {obra_ped}", ip="")
                        criar_notificacao(destinatario="admin", titulo="🔧 Novo Pedido de Ferramenta",
                            mensagem=f"{user_nome} pediu ferramenta em {obra_ped}: {desc_fer[:50]}",
                            tipo="warning", acao_url="/admin?tab=validacoes")
                        inv()
                        st.success("✅ Pedido enviado!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Descreve a ferramenta necessária.")

        with sub_epi:
            st.markdown("#### 🦺 Pedir EPIs")
            with st.form("form_pedir_epi"):
                obra_epi = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_epi_obra")
                item_epi = st.selectbox("Tipo de EPI", ["Capacete","Óculos de Proteção","Luvas","Botas de Segurança","Arnés","Protetor Auditivo","Máscara","Outro"], key="ped_epi_tipo")
                tam_epi  = st.selectbox("Tamanho", ["P","M","G","XG","Único"], key="ped_epi_tam")
                qtd_epi  = st.number_input("Quantidade", min_value=1, value=1, key="ped_epi_qtd")
                desc_epi = st.text_area("Observações (opcional)", key="ped_epi_obs")
                if st.form_submit_button("📤 Enviar Pedido de EPI", use_container_width=True, type="primary"):
                    novo_ped = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8].upper(),
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante": user_nome, "Obra": obra_epi,
                        "Item": item_epi, "Tamanho": tam_epi,
                        "Quantidade": qtd_epi, "Descricao": desc_epi, "Status": "Pendente"
                    }])
                    updated = pd.concat([req_epi_db, novo_ped], ignore_index=True) if not req_epi_db.empty else novo_ped
                    save_db(updated, "req_epis.csv")
                    log_audit(usuario=st.session_state.user, acao="PEDIR_EPI",
                              tabela="req_epis.csv", registro_id=novo_ped['ID'].iloc[0],
                              detalhes=f"EPI por {user_nome}: {item_epi} ({tam_epi})", ip="")
                    criar_notificacao(destinatario="admin", titulo="🦺 Novo Pedido de EPI",
                        mensagem=f"{user_nome} pediu {qtd_epi}x {item_epi} ({tam_epi}) em {obra_epi}",
                        tipo="warning", acao_url="/admin?tab=validacoes")
                    inv()
                    st.success("✅ Pedido de EPI enviado!")
                    st.rerun()

        with sub_mat:
            st.markdown("#### 📦 Pedir Materiais")
            with st.form("form_pedir_mat"):
                obra_mat = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_mat_obra")
                desc_mat = st.text_area("Descrição do material necessário", key="ped_mat_desc")
                qtd_mat  = st.number_input("Quantidade", min_value=1, value=1, key="ped_mat_qtd")
                unid_mat = st.selectbox("Unidade", ["un","m","kg","l","cx","rol"], key="ped_mat_unid")
                urg_mat  = st.selectbox("Urgência", ["Baixa","Média","Alta"], key="ped_mat_urg")
                if st.form_submit_button("📤 Enviar Pedido de Material", use_container_width=True, type="primary"):
                    if desc_mat:
                        novo_ped = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_mat,
                            "Descricao": desc_mat, "Quantidade": qtd_mat,
                            "Unidade": unid_mat, "Urgencia": urg_mat, "Status": "Pendente"
                        }])
                        updated = pd.concat([req_mat_db, novo_ped], ignore_index=True) if not req_mat_db.empty else novo_ped
                        save_db(updated, "req_materiais.csv")
                        log_audit(usuario=st.session_state.user, acao="PEDIR_MATERIAL",
                                  tabela="req_materiais.csv", registro_id=novo_ped['ID'].iloc[0],
                                  detalhes=f"Material por {user_nome}: {qtd_mat}{unid_mat} - {desc_mat[:30]}", ip="")
                        criar_notificacao(destinatario="admin", titulo="📦 Novo Pedido de Material",
                            mensagem=f"{user_nome} pediu {qtd_mat}{unid_mat} de {desc_mat[:30]} em {obra_mat}",
                            tipo="warning", acao_url="/admin?tab=validacoes")
                        inv()
                        st.success("✅ Pedido de material enviado!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Descreve o material necessário.")

        with sub_gas:
            st.markdown("#### ⛽ Registar Abastecimento de Gasóleo")
            with st.form("form_pedir_gas"):
                obra_gas   = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_gas_obra")
                litros_gas = st.number_input("Litros Abastecidos", min_value=0.0, value=0.0, step=0.1, key="ped_gas_litros")
                valor_gas  = st.number_input("Valor Total (€)", min_value=0.0, value=0.0, step=0.01, key="ped_gas_valor")
                data_gas   = st.date_input("Data do Abastecimento", value=date.today(), key="ped_gas_data")
                desc_gas   = st.text_area("Observações (viatura, km, etc.)", key="ped_gas_obs")
                recibo_gas = st.file_uploader("📄 Foto do Recibo (obrigatório)", type=["png","jpg","jpeg","pdf"], key="ped_gas_recibo")
                if st.form_submit_button("📤 Enviar Registo de Gasóleo", use_container_width=True, type="primary"):
                    if recibo_gas and litros_gas > 0:
                        if recibo_gas.type == "application/pdf":
                            recibo_b64 = base64.b64encode(recibo_gas.read()).decode()
                        else:
                            recibo_b64 = process_and_compress_image(recibo_gas)
                        novo_gas = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_gas,
                            "Litros": litros_gas, "Valor": valor_gas,
                            "Data_Abastecimento": data_gas.strftime("%d/%m/%Y"),
                            "Descricao": desc_gas, "Recibo_b64": recibo_b64,
                            "Status": "Pendente", "Tipo": "Gasóleo"
                        }])
                        updated = pd.concat([req_mat_db, novo_gas], ignore_index=True) if not req_mat_db.empty else novo_gas
                        save_db(updated, "req_materiais.csv")
                        log_audit(usuario=st.session_state.user, acao="REGISTAR_GASOLEO",
                                  tabela="req_materiais.csv", registro_id=novo_gas['ID'].iloc[0],
                                  detalhes=f"{user_nome} registou {litros_gas}L de gasóleo em {obra_gas}", ip="")
                        criar_notificacao(destinatario="admin", titulo="⛽ Novo Registo de Gasóleo",
                            mensagem=f"{user_nome} registou {litros_gas}L (€{valor_gas}) em {obra_gas}",
                            tipo="info", acao_url="/admin?tab=validacoes")
                        inv()
                        st.success("✅ Registo de gasóleo enviado com recibo!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Faz upload do recibo e indica os litros.")

        with sub_avar:
            st.markdown("#### 🔧 Reportar Avaria / Reparação")
            with st.form("form_pedir_avar"):
                obra_avar  = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_avar_obra")
                equip_avar = st.text_input("Equipamento / Viatura", placeholder="Ex: Viatura ABC-123", key="ped_avar_equip")
                desc_avar  = st.text_area("Descrição da Avaria", key="ped_avar_desc")
                urg_avar   = st.selectbox("Urgência", ["Baixa","Média","Alta","Crítica - Paragem"], key="ped_avar_urg")
                val_avar   = st.number_input("Valor Estimado (€)", min_value=0.0, value=0.0, step=0.01, key="ped_avar_valor")
                fat_avar   = st.file_uploader("📄 Foto Fatura/Orçamento (obrigatório)", type=["png","jpg","jpeg","pdf"], key="ped_avar_fat")
                if st.form_submit_button("📤 Enviar Reporte de Avaria", use_container_width=True, type="primary"):
                    if fat_avar and desc_avar:
                        if fat_avar.type == "application/pdf":
                            fat_b64 = base64.b64encode(fat_avar.read()).decode()
                        else:
                            fat_b64 = process_and_compress_image(fat_avar)
                        nova_av = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_avar,
                            "Equipamento": equip_avar, "Descricao": desc_avar,
                            "Urgencia": urg_avar, "Valor_Estimado": val_avar,
                            "Fatura_b64": fat_b64, "Status": "Pendente", "Tipo": "Avaria"
                        }])
                        updated = pd.concat([incs_db, nova_av], ignore_index=True) if not incs_db.empty else nova_av
                        save_db(updated, "incidentes.csv")
                        log_audit(usuario=st.session_state.user, acao="REPORTAR_AVARIA",
                                  tabela="incidentes.csv", registro_id=nova_av['ID'].iloc[0],
                                  detalhes=f"Avaria por {user_nome}: {equip_avar} em {obra_avar}", ip="")
                        criar_notificacao(destinatario="admin", titulo="🔧 Nova Avaria Reportada",
                            mensagem=f"{urg_avar}: {equip_avar} em {obra_avar} - {desc_avar[:30]}...",
                            tipo="error" if urg_avar == "Crítica - Paragem" else "warning",
                            acao_url="/admin?tab=validacoes")
                        inv()
                        st.success("✅ Reporte de avaria enviado!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Descreve a avaria e faz upload da fatura/orçamento.")

        with sub_meus:
            st.markdown("#### 📋 Histórico dos Meus Pedidos")

            def _card_pedido(ped, titulo_campo):
                cor = {"Pendente":"#F59E0B","Aprovado":"#10B981","Rejeitado":"#EF4444"}.get(ped.get('Status','Pendente'),"#6B7280")
                return f"""
                <div class="pedido-card" style="border-left-color:{cor};">
                    <b>{ped.get(titulo_campo,'N/A')}</b><br>
                    <small>Data: {ped.get('Data','N/A')} | Urgência: {ped.get('Urgencia','N/A')}<br>
                    Status: <span style="color:{cor};font-weight:bold;">{ped.get('Status','Pendente')}</span></small>
                </div>"""

            sem_pedidos = True

            if not req_fer_db.empty:
                meus = req_fer_db[req_fer_db['Solicitante'] == user_nome]
                if not meus.empty:
                    sem_pedidos = False
                    st.markdown("##### 🔧 Ferramentas")
                    for _, p in meus.iterrows():
                        st.markdown(_card_pedido(p, 'Descricao'), unsafe_allow_html=True)

            if not req_epi_db.empty:
                meus = req_epi_db[req_epi_db['Solicitante'] == user_nome]
                if not meus.empty:
                    sem_pedidos = False
                    st.markdown("##### 🦺 EPIs")
                    for _, p in meus.iterrows():
                        cor = {"Pendente":"#F59E0B","Aprovado":"#10B981","Rejeitado":"#EF4444"}.get(p.get('Status','Pendente'),"#6B7280")
                        st.markdown(f"""
                        <div class="pedido-card" style="border-left-color:{cor};">
                            <b>{p.get('Item','N/A')} ({p.get('Tamanho','N/A')}) x{p.get('Quantidade',1)}</b><br>
                            <small>Data: {p.get('Data','N/A')}<br>
                            Status: <span style="color:{cor};font-weight:bold;">{p.get('Status','Pendente')}</span></small>
                        </div>""", unsafe_allow_html=True)

            if not req_mat_db.empty:
                meus = req_mat_db[req_mat_db['Solicitante'] == user_nome]
                if not meus.empty:
                    sem_pedidos = False
                    st.markdown("##### 📦 Materiais & Outros")
                    for _, p in meus.iterrows():
                        cor = {"Pendente":"#F59E0B","Aprovado":"#10B981","Rejeitado":"#EF4444"}.get(p.get('Status','Pendente'),"#6B7280")
                        st.markdown(f"""
                        <div class="pedido-card" style="border-left-color:{cor};">
                            <b>{p.get('Descricao', p.get('Equipamento','N/A'))}</b><br>
                            <small>Data: {p.get('Data','N/A')} | {p.get('Quantidade','')}{p.get('Unidade','')}<br>
                            Status: <span style="color:{cor};font-weight:bold;">{p.get('Status','Pendente')}</span></small>
                        </div>""", unsafe_allow_html=True)

            if sem_pedidos:
                st.info("📋 Ainda não fizeste nenhum pedido.")

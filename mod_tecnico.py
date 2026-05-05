import streamlit as st
import pandas as pd
import uuid, secrets, base64, io, json
from datetime import datetime, timedelta, date
from streamlit_drawable_canvas import st_canvas
from PIL import Image

from core import (
    save_db, inv, fh, sl, render_metric, load_db,
    ICONS, COLORS, TIPOS_FRENTE, REGRAS_OURO,
    CATEGORIAS_SAFETY_WALK, log_audit, criar_notificacao, process_and_compress_image
)
from translations import t

def render_tecnico(*args):
    """Renderiza módulo Técnico com perfil editável, PDFs obrigatórios e validação de Preço Hora"""
    
    # 1. Desempacotamento das variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    user_nome = st.session_state.get('user', 'Usuário')
    cargo_user = st.session_state.get('cargo', 'Técnico')
    user_tipo = st.session_state.get('tipo', 'Técnico')

    # Lógica de Permissões
    is_chefe = user_tipo in ['Chefe de Equipa', 'Admin', 'Gestor'] or cargo_user in ['Chefe de Equipa', 'Encarregado']
    
    # Carregar dados do utilizador atual
    user_data = None
    user_idx = None
    if not users.empty and 'Nome' in users.columns:
        user_match = users[users['Nome'] == user_nome]
        if not user_match.empty:
            user_data = user_match.iloc[0]
            user_idx = user_match.index[0]
    
    # Carregar PDFs obrigatórios
    try:
        pdfs_db = load_db("pdfs_obrigatorios.csv", [
            "ID", "Nome", "Descricao", "Data_Upload", "Upload_Por", "Ficheiro_b64"
        ])
    except:
        pdfs_db = pd.DataFrame(columns=[
            "ID", "Nome", "Descricao", "Data_Upload", "Upload_Por", "Ficheiro_b64"
        ])
    
    # =============================================================================
    # HEADER COM BRANDING INDUSTRIAL
    # =============================================================================
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:30px 20px;
        background:linear-gradient(135deg, #1E293B, #0F172A);
        border-radius:20px;
        margin-bottom:30px;
        border:1px solid rgba(255,255,255,0.1);
    ">
        <div style="font-size:3rem; margin-bottom:10px;">{ICONS["technician"]}</div>
        <div style="font-size:1.8rem; font-weight:800; color:#F8FAFC;">{user_nome}</div>
        <div style="font-size:1rem; color:#94A3B8;">{cargo_user} | {user_tipo}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # CSS PERSONALIZADO
    # =============================================================================
    st.markdown("""
    <style>
    .rp-card {
        background: rgba(255,255,255,0.05);
        padding: 18px;
        border-radius: 15px;
        border-left: 6px solid #3B82F6;
        margin-bottom: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        backdrop-filter: blur(10px);
    }
    .rp-card.pendente { border-left-color: #F59E0B; }
    .rp-card.aprovado { border-left-color: #10B981; }
    .rp-card.fechado { border-left-color: #3B82F6; }
    .week-bar {
        background: rgba(255,255,255,0.08);
        padding: 15px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 20px;
    }
    .esign-seal {
        border: 2px dashed #10B981;
        padding: 15px;
        background: rgba(16,185,129,0.1);
        border-radius: 10px;
        color: #10B981;
        font-family: monospace;
        font-size: 0.85rem;
        margin-top: 15px;
    }
    .pedido-card {
        background: rgba(59,130,246,0.1);
        border: 1px solid rgba(59,130,246,0.3);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .pdf-card {
        background: rgba(239, 68, 68, 0.1);
        border: 2px solid #EF4444;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        text-align: center;
    }
    .pdf-card.validado {
        background: rgba(16, 185, 129, 0.1);
        border-color: #10B981;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # VERIFICAÇÃO DE PDFs OBRIGATÓRIOS (BLOQUEIO)
    # =============================================================================
    if user_data is not None:
        pdfs_validados = user_data.get('PDFs_Validados', 'Não')
        
        if pdfs_validados != 'Sim':
            st.markdown("""
            <div style="background:#EF4444; color:white; padding:20px; border-radius:15px; text-align:center; margin-bottom:30px;">
                <h2 style="margin:0 0 10px 0;">⚠️ AÇÃO OBRIGATÓRIA</h2>
                <p style="margin:0; font-size:1.1rem;">Deves visualizar e validar os documentos obrigatórios antes de continuar.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 📋 Documentos Obrigatórios", unsafe_allow_html=True)
            
            # Carregar PDFs já vistos
            try:
                pdfs_vistos = json.loads(user_data.get('PDFs_Vistos', '[]'))
            except:
                pdfs_vistos = []
            
            todos_vistos = True
            
            if not pdfs_db.empty:
                for _, pdf in pdfs_db.iterrows():
                    pdf_id = pdf.get('ID', '')
                    pdf_nome = pdf.get('Nome', 'Documento')
                    pdf_desc = pdf.get('Descricao', '')
                    visto = pdf_id in pdfs_vistos
                    
                    with st.container():
                        st.markdown(f"""
                        <div class="pdf-card {'validado' if visto else ''}">
                            <h4 style="margin:0 0 10px 0;">📄 {pdf_nome}</h4>
                            <p style="margin:0 0 15px 0; color:#94A3B8;">{pdf_desc}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Botão para visualizar PDF
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
                            except:
                                st.error("❌ Erro ao carregar PDF")
                        
                        # Botão de validação
                        if not visto:
                            todos_vistos = False
                            if st.button(f"✅ Confirmar Visualização: {pdf_nome}", key=f"validar_{pdf_id}", use_container_width=True):
                                pdfs_vistos.append(pdf_id)
                                users.loc[user_idx, 'PDFs_Vistos'] = json.dumps(pdfs_vistos)
                                
                                # Se todos foram vistos, marcar como validado
                                if len(pdfs_vistos) >= len(pdfs_db):
                                    users.loc[user_idx, 'PDFs_Validados'] = 'Sim'
                                    users.loc[user_idx, 'PDFs_Validacao_Data'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    
                                    # Notificar admin RH
                                    criar_notificacao(
                                        destinatario="admin",
                                        titulo="✅ Colaborador Validou PDFs",
                                        mensagem=f"{user_nome} validou a visualização de {len(pdfs_vistos)} PDF(s) obrigatório(s)",
                                        tipo="success",
                                        acao_url="/admin?tab=rh"
                                    )
                                    
                                    log_audit(usuario=user_nome, acao="VALIDAR_PDFS_OBRIGATORIOS", tabela="usuarios.csv", registro_id=user_nome, detalhes=f"PDFs validados: {pdfs_vistos}", ip="")
                                
                                save_db(users, "usuarios.csv")
                                inv()
                                st.success("✅ Validação registada!")
                                st.rerun()
                        else:
                            st.success("✅ Documento validado")
                        
                        st.divider()
            else:
                st.info("📋 Nenhum PDF obrigatório configurado pelo momento.")
                todos_vistos = True
            
            if not todos_vistos:
                st.warning("⚠️ Deves validar TODOS os PDFs antes de continuar.")
                st.stop()  # Bloqueia o resto da página
            else:
                st.success("✅ Todos os PDFs validados! Podes continuar.")
                st.divider()
    
    # =============================================================================
    # DEFINIÇÃO DE TABS
    # =============================================================================
    menu = [f"{ICONS['dashboard']} Pontos", f"{ICONS['safety']} Segurança (HSE)", f"{ICONS['profile']} Perfil", f"{ICONS['material']} Pedidos"]
    if is_chefe:
        menu.insert(1, f"{ICONS['reports']} Folha de Ponto")
    
    tabs = st.tabs(menu)
    
    # =============================================================================
    # TAB 1: REGISTO DE PONTO
    # =============================================================================
    with tabs[0]:
        st.markdown(f"### {ICONS['dashboard']} Registo de Ponto")
        
        hoje = date.today()
        if 'data_consulta' not in st.session_state:
            st.session_state.data_consulta = hoje
        
        d_sel = st.session_state.data_consulta
        inicio_sem = d_sel - timedelta(days=d_sel.weekday())
        dias_sem = [inicio_sem + timedelta(days=i) for i in range(7)]
        
        st.markdown('<div class="week-bar">', unsafe_allow_html=True)
        cols_cal = st.columns(7)
        for i, d in enumerate(dias_sem):
            with cols_cal[i]:
                status_dia = "⚪"
                if not registos_db.empty:
                    dia_regs = registos_db[
                        (registos_db['Técnico'] == user_nome) &
                        (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date == d)
                    ]
                    if not dia_regs.empty:
                        status_dia = "🟢" if "1" in dia_regs['Status'].values else "🟠"
                
                tipo_btn = "primary" if d == d_sel else "secondary"
                if st.button(f"{status_dia}\n{d.day}", key=f"cal_{d}", use_container_width=True, type=tipo_btn):
                    st.session_state.data_consulta = d
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander(f"➕ Registar Trabalho em {st.session_state.data_consulta.strftime('%d/%m/%Y')}", expanded=(d_sel == hoje)):
            with st.form("ponto_form_elite"):
                obras_list = obras_db['Obra'].unique() if not obras_db.empty else ["Geral"]
                obra = st.selectbox(f"{ICONS['app']} Selecionar Obra", obras_list)
                frente = st.selectbox(f"{ICONS['reports']} Frente de Trabalho", TIPOS_FRENTE)
                
                c1, c2 = st.columns(2)
                h_ini = c1.time_input("Entrada", value=datetime.strptime("08:00", "%H:%M").time())
                h_fim = c2.time_input("Saída", value=datetime.strptime("17:00", "%H:%M").time())
                relat = st.text_area("📝 Relatório de Atividades")
                
                if st.form_submit_button(f"{ICONS['save']} Gravar Registo", use_container_width=True, type="primary"):
                    t1 = datetime.combine(date.today(), h_ini)
                    t2 = datetime.combine(date.today(), h_fim)
                    delta_h = round((t2 - t1).seconds / 3600, 2)
                    
                    if delta_h <= 0:
                        st.error("⚠️ Erro: A hora de saída deve ser posterior à de entrada.")
                    else:
                        new_r = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": st.session_state.data_consulta.strftime("%d/%m/%Y"),
                            "Técnico": user_nome,
                            "Obra": obra,
                            "Frente": frente,
                            "Turnos": f"{h_ini.strftime('%H:%M')}-{h_fim.strftime('%H:%M')}",
                            "Horas_Total": delta_h,
                            "Relatorio": relat,
                            "Status": "0"
                        }])
                        save_db(pd.concat([registos_db, new_r], ignore_index=True) if not registos_db.empty else new_r, "registos.csv")
                        
                        log_audit(usuario=st.session_state.user, acao="REGISTAR_PONTO", tabela="registos.csv", registro_id=new_r['ID'].iloc[0], detalhes=f"{user_nome} registou {delta_h}h em {obra}", ip="")
                        
                        st.success(f"{ICONS['approved']} Ponto registado com sucesso!")
                        inv()
                        st.rerun()
        
        st.markdown(f"### Registos de {st.session_state.data_consulta.strftime('%d/%m/%Y')}")
        if not registos_db.empty:
            meus_regs = registos_db[registos_db['Técnico'] == user_nome]
            regs_dia = meus_regs[pd.to_datetime(meus_regs['Data'], dayfirst=True, errors='coerce').dt.date == st.session_state.data_consulta]
            
            if regs_dia.empty:
                st.caption("ℹ️ Nenhum registo encontrado para este dia.")
            
            for _, r in regs_dia.iterrows():
                _, st_cls = sl(r['Status'])[:2]
                st.markdown(f"""
                <div class="rp-card {st_cls.split('-')[1] if st_cls else 'pendente'}">
                    <b>{r["Obra"]}</b> | {r["Turnos"]} (<b>{fh(r["Horas_Total"])}h</b>)<br>
                    <small>{r["Frente"]}</small><br>
                    <small style="color:#94A3B8;">{r["Relatorio"][:100] if r["Relatorio"] else ""}</small><br>
                    <small style="color:{'#10B981' if r['Status']=='1' else '#F59E0B' if r['Status']=='0' else '#EF4444'};">
                        {'✅ Aprovado' if r['Status']=='1' else '⏳ Pendente' if r['Status']=='0' else '❌ Rejeitado'}
                    </small>
                </div>
                """, unsafe_allow_html=True)
    
    # =============================================================================
    # TAB 2 (CHEFE): FOLHA DE PONTO
    # =============================================================================
    offset = 0
    if is_chefe:
        offset = 1
        with tabs[1]:
            st.markdown(f"### {ICONS['reports']} Folha de Ponto & Assinatura Digital")
            st.caption("Gera e assina digitalmente a folha de ponto semanal da equipa.")
            
            obra_f = st.selectbox(f"{ICONS['app']} Obra para Validar", 
                                  obras_db['Obra'].unique() if not obras_db.empty else ["Sem Obras"], 
                                  key="esign_obra")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                semana_inicio = st.date_input("Início da Semana", value=inicio_sem, key="fp_inicio")
            with col_p2:
                semana_fim = st.date_input("Fim da Semana", value=inicio_sem + timedelta(days=6), key="fp_fim")
            
            if not registos_db.empty:
                regs_periodo = registos_db[
                    (registos_db['Obra'] == obra_f) &
                    (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date >= semana_inicio) &
                    (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date <= semana_fim)
                ]
                
                if not regs_periodo.empty:
                    st.markdown(f"### 📋 Registos de {semana_inicio.strftime('%d/%m')} a {semana_fim.strftime('%d/%m/%Y')}")
                    
                    for tecnico in regs_periodo['Técnico'].unique():
                        regs_tec = regs_periodo[regs_periodo['Técnico'] == tecnico]
                        total_horas = regs_tec['Horas_Total'].astype(float).sum()
                        
                        st.markdown(f"""
                        <div class="pedido-card">
                            <b>👤 {tecnico}</b><br>
                            <small>{len(regs_tec)} dias registados | <b>{total_horas:.1f}h totais</b></small>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("### ✍️ Assinatura do Responsável")
                    canvas_sig = st_canvas(
                        fill_color="rgba(255, 255, 255, 0)",
                        stroke_width=2.5,
                        stroke_color="#3B82F6",
                        background_color="#FFFFFF",
                        height=180,
                        width=400,
                        drawing_mode="freedraw",
                        key="canvas_esign_fp"
                    )
                    
                    nome_responsavel = st.text_input("Nome do Responsável / Cliente", placeholder="Ex: Eng. João Silva")
                    
                    if st.button(f"{ICONS['reports']} Gerar Folha com Selo de Segurança", use_container_width=True, type="primary"):
                        if canvas_sig.image_data is not None and nome_responsavel:
                            esign_id = secrets.token_hex(6).upper()
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            nova_folha = pd.DataFrame([{
                                "ID": str(uuid.uuid4())[:8].upper(),
                                "Obra": obra_f,
                                "Periodo": f"{semana_inicio.strftime('%d/%m')} - {semana_fim.strftime('%d/%m/%Y')}",
                                "Responsavel": nome_responsavel,
                                "Data_Assinatura": timestamp,
                                "Assinatura_b64": canvas_sig.image_data,
                                "Selo": esign_id,
                                "Status": "Assinado"
                            }])
                            
                            if not folhas_db.empty:
                                folhas_db = pd.concat([folhas_db, nova_folha], ignore_index=True)
                            else:
                                folhas_db = nova_folha
                            
                            save_db(folhas_db, "folhas_ponto.csv")
                            
                            log_audit(usuario=st.session_state.user, acao="ASSINAR_FOLHA_PONTO", tabela="folhas_ponto.csv", registro_id=nova_folha['ID'].iloc[0], detalhes=f"Folha assinada por {nome_responsavel} para {obra_f}", ip="")
                            
                            st.markdown(f"""
                            <div class="esign-seal">
                                <b>🔒 SELO DE SEGURANÇA GESTNOW #{esign_id}</b><br>
                                ASSINADO POR: {nome_responsavel}<br>
                                DATA/HORA: {timestamp}<br>
                                PERÍODO: {semana_inicio.strftime('%d/%m')} a {semana_fim.strftime('%d/%m/%Y')}<br>
                                OBRA: {obra_f}
                            </div>
                            """, unsafe_allow_html=True)
                            st.success(f"{ICONS['approved']} Folha de ponto gerada e assinada com sucesso!")
                            inv()
                        else:
                            st.warning("⚠️ Por favor, forneça a assinatura e o nome do responsável.")
                else:
                    st.info(f"📋 Sem registos de ponto para {obra_f} neste período.")
            else:
                st.info("📋 Sem registos de ponto disponíveis.")
    
    # =============================================================================
    # TAB HSE: SEGURANÇA
    # =============================================================================
    with tabs[1 + offset]:
        st.markdown(f"### {ICONS['safety']} Regras de Ouro")
        
        for ic, tit, des in REGRAS_OURO:
            with st.expander(f"{ic} {tit}"):
                st.write(des)
        
        st.divider()
        st.markdown(f"### {ICONS['safety']} Reportar Incidente HSE")
        
        with st.form("hse_report"):
            io = st.selectbox(f"{ICONS['app']} Obra", 
                             obras_db['Obra'].unique() if not obras_db.empty else ["Geral"])
            it = st.selectbox("Gravidade", ["Baixa", "Média", "Alta (Crítica)"])
            id_desc = st.text_area("Descrição da Ocorrência / Condição Insegura")
            
            if st.form_submit_button(f"{ICONS['safety']} Submeter Alerta HSE", use_container_width=True, type="primary"):
                ni = pd.DataFrame([{
                    "ID": str(uuid.uuid4())[:8].upper(),
                    "Data": date.today().strftime("%d/%m/%Y"),
                    "Utilizador": user_nome,
                    "Obra": io,
                    "Status": "Aberto",
                    "Gravidade": it,
                    "Descricao": id_desc
                }])
                save_db(pd.concat([incs_db, ni], ignore_index=True) if not incs_db.empty else ni, "incidentes.csv")
                
                log_audit(usuario=st.session_state.user, acao="REPORTAR_INCIDENTE_HSE", tabela="incidentes.csv", registro_id=ni['ID'].iloc[0], detalhes=f"Incidente reportado por {user_nome} em {io}", ip="")
                
                st.success(f"{ICONS['approved']} Alerta HSE enviado para o departamento de segurança.")
                inv()
                st.rerun()
    
    # =============================================================================
    # TAB PERFIL: EDITÁVEL COM VALIDAÇÕES
    # =============================================================================
    with tabs[-1 if not is_chefe else -2]:
        st.markdown(f"### {ICONS['profile']} Perfil do Colaborador", unsafe_allow_html=True)
        
        if user_data is not None:
            # ========== VALIDAÇÃO DE PREÇO HORA (PRIMEIRO ACESSO) ==========
            preco_status = user_data.get('PrecoHoraStatus', '')
            
            if preco_status == '':
                st.markdown("""
                <div style="background:#3B82F6; color:white; padding:20px; border-radius:15px; text-align:center; margin-bottom:30px;">
                    <h3 style="margin:0 0 10px 0;">💰 Validação de Preço Hora</h3>
                    <p style="margin:0;">Deves aceitar ou recusar o teu preço hora antes de continuar.</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.1); padding:20px; border-radius:15px; text-align:center;">
                    <p style="font-size:1.2rem; margin:0 0 20px 0;"><strong>Preço Hora Proposto:</strong></p>
                    <p style="font-size:2.5rem; font-weight:bold; color:#10B981; margin:0 0 30px 0;">€ {user_data.get('PrecoHora', '15.0')}</p>
                    
                    <div style="display:flex; gap:20px; justify-content:center;">
                        <button onclick="document.getElementById('aceitar_preco').click()" style="background:#10B981; color:white; border:none; padding:15px 40px; border-radius:10px; font-size:1.1rem; cursor:pointer;">
                            ✅ Aceitar
                        </button>
                        <button onclick="document.getElementById('recusar_preco').click()" style="background:#EF4444; color:white; border:none; padding:15px 40px; border-radius:10px; font-size:1.1rem; cursor:pointer;">
                            ❌ Recusar
                        </button>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_acc1, col_acc2 = st.columns(2)
                with col_acc1:
                    if st.button("✅ Aceitar Preço Hora", key="aceitar_preco", use_container_width=True):
                        users.loc[user_idx, 'PrecoHoraStatus'] = 'Aceite'
                        users.loc[user_idx, 'PrecoHoraData'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(users, "usuarios.csv")
                        
                        log_audit(usuario=user_nome, acao="ACEITAR_PRECO_HORA", tabela="usuarios.csv", registro_id=user_nome, detalhes=f"Aceitou €{user_data.get('PrecoHora')}/hora", ip="")
                        
                        criar_notificacao(
                            destinatario="admin",
                            titulo="💰 Preço Hora Aceite",
                            mensagem=f"{user_nome} aceitou o preço hora de €{user_data.get('PrecoHora')}",
                            tipo="success",
                            acao_url="/admin?tab=rh"
                        )
                        
                        inv()
                        st.success("✅ Preço hora aceite! Podes continuar.")
                        st.rerun()
                
                with col_acc2:
                    if st.button("❌ Recusar Preço Hora", key="recusar_preco", use_container_width=True):
                        users.loc[user_idx, 'PrecoHoraStatus'] = 'Recusado'
                        users.loc[user_idx, 'PrecoHoraData'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(users, "usuarios.csv")
                        
                        log_audit(usuario=user_nome, acao="RECUSAR_PRECO_HORA", tabela="usuarios.csv", registro_id=user_nome, detalhes=f"Recusou €{user_data.get('PrecoHora')}/hora", ip="")
                        
                        criar_notificacao(
                            destinatario="admin",
                            titulo="💰 Preço Hora Recusado",
                            mensagem=f"{user_nome} RECUSOU o preço hora de €{user_data.get('PrecoHora')}",
                            tipo="warning",
                            acao_url="/admin?tab=rh"
                        )
                        
                        inv()
                        st.warning("❌ Preço hora recusado. Contacta o admin para renegociação.")
                        st.rerun()
                
                st.stop()  # Bloqueia até validar preço hora
            
            elif preco_status == 'Recusado':
                st.warning("⚠️ O teu preço hora foi recusado. Contacta o admin para renegociação.")
                st.stop()
            
            # ========== FORMULÁRIO DE EDIÇÃO DE PERFIL ==========
            st.markdown("### ✏️ Editar Perfil", unsafe_allow_html=True)
            
            # Carregar campos bloqueados
            try:
                campos_bloqueados = json.loads(user_data.get('Campos_Bloqueados', '[]'))
            except:
                campos_bloqueados = []
            
            with st.form("form_editar_perfil"):
                col1, col2 = st.columns(2)
                
                # Campos editáveis (exceto Preço Hora e bloqueados)
                campos_editaveis = {
                    'Email': user_data.get('Email', ''),
                    'Telefone

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
    """Renderiza módulo Técnico com perfil completo, PDFs obrigatórios e validação de Preço Hora"""
    
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
    .section-title {
        background: linear-gradient(135deg, #3B82F6, #1E40AF);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 30px 0 20px 0;
        font-size: 1.3rem;
        font-weight: bold;
    }
    .subsection-title {
        background: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3B82F6;
        padding: 10px 15px;
        margin: 20px 0 15px 0;
        font-size: 1.1rem;
        font-weight: 600;
    }
    .blur-price {
        filter: blur(5px);
        user-select: none;
        cursor: pointer;
        transition: filter 0.3s ease;
    }
    .blur-price:hover {
        filter: blur(3px);
    }
    .blur-price.revealed {
        filter: blur(0);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # VERIFICAÇÃO DE PDFs OBRIGATÓRIOS (BLOQUEIO)
    # =============================================================================
    if user_data is not None:
        pdfs_validados = user_data.get('PDFs_Validados', 'Não')
        pdfs_validacao_data = user_data.get('PDFs_Validacao_Data', '')
        
        # Verificar se precisa validar (primeira vez OU dia 1 do mês)
        hoje = datetime.now()
        precisa_validar = False
        
        if pdfs_validados != 'Sim':
            precisa_validar = True
        elif pdfs_validacao_
            try:
                data_validacao = datetime.strptime(pdfs_validacao_data, "%d/%m/%Y %H:%M")
                if hoje.day == 1 and (hoje.month != data_validacao.month or hoje.year != data_validacao.year):
                    precisa_validar = True
            except:
                precisa_validar = True
        
        if precisa_validar:
            # Mostrar aviso
            if hoje.day == 1:
                st.markdown("""
                <div style="background:#EF4444; color:white; padding:20px; border-radius:15px; text-align:center; margin-bottom:30px;">
                    <h2 style="margin:0 0 10px 0;">⚠️ VALIDAÇÃO MENSAL OBRIGATÓRIA</h2>
                    <p style="margin:0; font-size:1.1rem;">É dia 1! Deves visualizar e validar os documentos obrigatórios.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
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
            
            total_pdfs = len(pdfs_db) if not pdfs_db.empty else 0
            
            if not pdfs_db.empty:
                st.info(f"📊 Progresso: {len(pdfs_vistos)}/{total_pdfs} PDFs validados")
                
                for _, pdf in pdfs_db.iterrows():
                    pdf_id = pdf.get('ID', '')
                    pdf_nome = pdf.get('Nome', 'Documento')
                    pdf_desc = pdf.get('Descricao', '')
                    visto = pdf_id in pdfs_vistos
                    
                    with st.container():
                        if visto:
                            st.markdown(f"""
                            <div class="pdf-card validado">
                                <h4 style="margin:0 0 10px 0; color:#10B981;">✅ {pdf_nome}</h4>
                                <p style="margin:0 0 15px 0; color:#94A3B8;">{pdf_desc}</p>
                                <div style="background:#10B981; color:white; padding:10px; border-radius:8px; font-weight:bold;">
                                    ✅ Documento validado
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="pdf-card">
                                <h4 style="margin:0 0 10px 0; color:#EF4444;">📄 {pdf_nome}</h4>
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
                            except Exception as e:
                                st.error(f"❌ Erro ao carregar PDF: {str(e)}")
                        
                        # Botão de validação
                        if not visto:
                            if st.button(f"✅ Confirmar Visualização: {pdf_nome}", key=f"validar_{pdf_id}", use_container_width=True):
                                if pdf_id not in pdfs_vistos:
                                    pdfs_vistos.append(pdf_id)
                                
                                users.loc[user_idx, 'PDFs_Vistos'] = json.dumps(pdfs_vistos)
                                
                                # Verificar se TODOS foram validados
                                if len(pdfs_vistos) >= total_pdfs:
                                    # ✅ TODOS VALIDADOS!
                                    users.loc[user_idx, 'PDFs_Validados'] = 'Sim'
                                    users.loc[user_idx, 'PDFs_Validacao_Data'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    save_db(users, "usuarios.csv")
                                    
                                    log_audit(usuario=user_nome, acao="VALIDAR_PDFS_OBRIGATORIOS", tabela="usuarios.csv", registro_id=user_nome, detalhes=f"Validou {len(pdfs_vistos)} PDFs", ip="")
                                    
                                    criar_notificacao(
                                        destinatario="admin",
                                        titulo="✅ Colaborador Validou PDFs",
                                        mensagem=f"{user_nome} validou {len(pdfs_vistos)} PDF(s)",
                                        tipo="success",
                                        acao_url="/admin?tab=rh"
                                    )
                                    
                                    # Mostrar mensagem PERMANENTE
                                    st.markdown("""
                                    <div style="background:#10B981; color:white; padding:30px; border-radius:15px; text-align:center; margin:30px 0;">
                                        <h2 style="margin:0 0 15px 0;">✅ VALIDAÇÃO CONCLUÍDA!</h2>
                                        <p style="margin:0; font-size:1.2rem;">Todos os documentos foram validados.</p>
                                        <p style="margin:15px 0 0 0;">A desbloquear aplicação...</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    st.balloons()
                                    inv()
                                    st.rerun()  # ← RELOAD IMEDIATO!
                                    return  # ← PARAR EXECUÇÃO!
                                else:
                                    # Ainda faltam PDFs
                                    save_db(users, "usuarios.csv")
                                    inv()
                                    restantes = total_pdfs - len(pdfs_vistos)
                                    st.success(f"✅ '{pdf_nome}' validado! Faltam {restantes} PDF(s).")
                                    st.rerun()
                                    return  # ← PARAR EXECUÇÃO!
            
            # Se chegou aqui, é porque ainda não validou todos
            st.warning(f"⚠️ Deves validar TODOS os {total_pdfs} PDFs antes de continuar.")
            st.stop()  # ← BLOQUEAR A APP!
    
    # =============================================================================
    # SE CHEGOU AQUI, É PORQUE OS PDFs ESTÃO VALIDADOS - CONTINUAR COM O RESTO DA APP
    # =============================================================================
    
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
    # TAB PERFIL: EDITÁVEL COM TODOS OS NOVOS CAMPOS
    # =============================================================================
    with tabs[-1 if not is_chefe else -2]:
        st.markdown(f"### {ICONS['profile']} Perfil do Colaborador", unsafe_allow_html=True)
        
        if user_data is not None:
            # ========== VALIDAÇÃO DE PREÇO HORA (PRIMEIRO ACESSO) ==========
            preco_status = user_data.get('PrecoHoraStatus', '')
            preco_hora_valor = user_data.get('PrecoHora', '15.0')
            
            if preco_status == '':
                st.markdown("""
                <div style="background:#3B82F6; color:white; padding:20px; border-radius:15px; text-align:center; margin-bottom:30px;">
                    <h3 style="margin:0 0 10px 0;">💰 Validação de Preço Hora</h3>
                    <p style="margin:0;">Deves aceitar ou recusar o teu preço hora antes de continuar.</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.1); padding:30px; border-radius:15px; text-align:center;">
                    <p style="font-size:1.2rem; margin:0 0 20px 0;"><strong>Preço Hora Proposto:</strong></p>
                    <p style="font-size:3rem; font-weight:bold; color:#10B981; margin:0 0 30px 0;">€ {preco_hora_valor}/hora</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_acc1, col_acc2 = st.columns(2)
                with col_acc1:
                    if st.button("✅ Aceitar Preço Hora", key="aceitar_preco", use_container_width=True, type="primary"):
                        users.loc[user_idx, 'PrecoHoraStatus'] = 'Aceite'
                        users.loc[user_idx, 'PrecoHoraData'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(users, "usuarios.csv")
                        
                        log_audit(usuario=user_nome, acao="ACEITAR_PRECO_HORA", tabela="usuarios.csv", registro_id=user_nome, detalhes=f"Aceitou €{preco_hora_valor}/hora", ip="")
                        
                        criar_notificacao(
                            destinatario="admin",
                            titulo="💰 Preço Hora Aceite",
                            mensagem=f"{user_nome} aceitou o preço hora de €{preco_hora_valor}",
                            tipo="success",
                            acao_url="/admin?tab=rh"
                        )
                        
                        inv()
                        st.success("✅ Preço hora aceite! Podes continuar.")
                        st.rerun()
                
                with col_acc2:
                    if st.button("❌ Recusar Preço Hora", key="recusar_preco", use_container_width=True, type="secondary"):
                        users.loc[user_idx, 'PrecoHoraStatus'] = 'Recusado'
                        users.loc[user_idx, 'PrecoHoraData'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(users, "usuarios.csv")
                        
                        log_audit(usuario=user_nome, acao="RECUSAR_PRECO_HORA", tabela="usuarios.csv", registro_id=user_nome, detalhes=f"Recusou €{preco_hora_valor}/hora", ip="")
                        
                        criar_notificacao(
                            destinatario="admin",
                            titulo="💰 Preço Hora Recusado",
                            mensagem=f"{user_nome} RECUSOU o preço hora de €{preco_hora_valor}",
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
            
            # ========== FORMULÁRIO DE EDIÇÃO DE PERFIL COMPLETO ==========
            st.markdown('<div class="section-title">✏️ Editar Perfil</div>', unsafe_allow_html=True)
            
            # Carregar campos bloqueados
            try:
                campos_bloqueados = json.loads(user_data.get('Campos_Bloqueados', '[]'))
            except:
                campos_bloqueados = []
            
            with st.form("form_editar_perfil"):
                # Secção 1: Identificação
                st.markdown('<div class="subsection-title">📋 Identificação do Colaborador</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    telefone = st.text_input("Contacto Telefónico", value=user_data.get('Telefone', ''), disabled='Telefone' in campos_bloqueados, key="edit_telefone")
                    email = st.text_input("Email", value=user_data.get('Email', ''), disabled='Email' in campos_bloqueados, key="edit_email")
                    contacto_emerg = st.text_input("Contacto Emergência", value=user_data.get('Contacto_Emergencia', ''), disabled='Contacto_Emergencia' in campos_bloqueados, key="edit_emerg_tel")
                with col2:
                    nome_emerg = st.text_input("Nome Emergência", value=user_data.get('Nome_Emergencia', ''), disabled='Nome_Emergencia' in campos_bloqueados, key="edit_emerg_nome")
                    grau_parentesco = st.text_input("Grau Parentesco", value=user_data.get('Grau_Parentesco', ''), disabled='Grau_Parentesco' in campos_bloqueados, key="edit_emerg_grau")
                
                # Secção 2: Morada
                st.markdown('<div class="subsection-title">📍 Morada</div>', unsafe_allow_html=True)
                
                morada = st.text_input("Morada", value=user_data.get('Morada', ''), disabled='Morada' in campos_bloqueados, key="edit_morada")
                col3, col4, col5 = st.columns(3)
                with col3:
                    localidade = st.text_input("Localidade", value=user_data.get('Localidade', ''), disabled='Localidade' in campos_bloqueados, key="edit_localidade")
                with col4:
                    concelho = st.text_input("Concelho", value=user_data.get('Concelho', ''), disabled='Concelho' in campos_bloqueados, key="edit_concelho")
                with col5:
                    cod_postal = st.text_input("Código Postal", value=user_data.get('Codigo_Postal', ''), disabled='Codigo_Postal' in campos_bloqueados, key="edit_cp")
                
                # Secção 3: Dados Pessoais
                st.markdown('<div class="subsection-title">🌍 Dados Pessoais</div>', unsafe_allow_html=True)
                
                col6, col7 = st.columns(2)
                with col6:
                    naturalidade = st.text_input("Naturalidade", value=user_data.get('Naturalidade', ''), disabled='Naturalidade' in campos_bloqueados, key="edit_naturalidade")
                    estado_civil = st.selectbox("Estado Civil", ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União de Facto"], index=["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União de Facto"].index(user_data.get('Estado_Civil', 'Solteiro(a)')) if user_data.get('Estado_Civil', '') in ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União de Facto"] else 0, disabled='Estado_Civil' in campos_bloqueados, key="edit_ec")
                with col7:
                    nacionalidade = st.text_input("Nacionalidade", value=user_data.get('Nacionalidade', 'Portugal'), disabled='Nacionalidade' in campos_bloqueados, key="edit_nacionalidade")
                    sexo = st.radio("Sexo", ["Masculino", "Feminino"], index=["Masculino", "Feminino"].index(user_data.get('Sexo', 'Masculino')) if user_data.get('Sexo', '') in ["Masculino", "Feminino"] else 0, horizontal=True, disabled='Sexo' in campos_bloqueados, key="edit_sexo")
                
                # Secção 4: Documentos
                st.markdown('<div class="subsection-title">🆔 Documentos</div>', unsafe_allow_html=True)
                
                col8, col9 = st.columns(2)
                with col8:
                    nif = st.text_input("Nº Contribuinte (NIF)", value=user_data.get('NIF', ''), disabled=True, key="edit_nif")  # NIF nunca editável
                    cc = st.text_input("Cartão Cidadão", value=user_data.get('CC', ''), disabled='CC' in campos_bloqueados, key="edit_cc")
                    niss = st.text_input("Nº Segurança Social (NISS)", value=user_data.get('NISS', ''), disabled='NISS' in campos_bloqueados, key="edit_niss")
                with col9:
                    cc_validade = st.text_input("Validade CC", value=user_data.get('CC_Validade', ''), disabled='CC_Validade' in campos_bloqueados, key="edit_cc_val")
                    dependentes = st.number_input("Dependentes", min_value=0, value=int(user_data.get('Dependentes', '0')), disabled='Dependentes' in campos_bloqueados, key="edit_dep")
                
                # Secção 5: Dados Profissionais
                st.markdown('<div class="subsection-title">💼 Dados Profissionais</div>', unsafe_allow_html=True)
                
                profissao = st.text_input("Profissão", value=user_data.get('Profissao', ''), disabled='Profissao' in campos_bloqueados, key="edit_prof")
                col10, col11 = st.columns(2)
                with col10:
                    categoria = st.text_input("Categoria Profissional", value=user_data.get('Categoria_Profissional', ''), disabled='Categoria_Profissional' in campos_bloqueados, key="edit_cat")
                with col11:
                    habilitacoes = st.selectbox("Habilitações Literárias", [
                        "4º Ano", "6º Ano", "9º Ano", "12º Ano",
                        "Curso Técnico", "Licenciatura", "Mestrado", "Doutoramento"
                    ], index=0 if user_data.get('Habilitacoes_Literarias', '') not in ["4º Ano", "6º Ano", "9º Ano", "12º Ano", "Curso Técnico", "Licenciatura", "Mestrado", "Doutoramento"] else ["4º Ano", "6º Ano", "9º Ano", "12º Ano", "Curso Técnico", "Licenciatura", "Mestrado", "Doutoramento"].index(user_data.get('Habilitacoes_Literarias', '')), disabled='Habilitacoes_Literarias' in campos_bloqueados, key="edit_hab")
                
                # Secção 6: Dados Bancários
                st.markdown('<div class="subsection-title">💰 Dados Bancários</div>', unsafe_allow_html=True)
                
                iban = st.text_input("IBAN", value=user_data.get('Banco_IBAN', ''), disabled='Banco_IBAN' in campos_bloqueados, key="edit_iban", placeholder="PT50 0000 0000 0000 00000 0000")
                
                # Secção 7: Fardamento
                st.markdown('<div class="subsection-title">👕 Tamanhos de Fardamento</div>', unsafe_allow_html=True)
                
                col12, col13, col14 = st.columns(3)
                with col12:
                    tam_camisola = st.selectbox("Camisola/T-shirt", 
                        ["XS", "S", "M", "L", "XL", "XXL", "XXXL"], 
                        index=["XS", "S", "M", "L", "XL", "XXL", "XXXL"].index(user_data.get('Tamanho_Camisola', 'M')) if user_data.get('Tamanho_Camisola', '') in ["XS", "S", "M", "L", "XL", "XXL", "XXXL"] else 2, 
                        key="edit_tam_cam")
                with col13:
                    tam_calca = st.selectbox("Calça",
                        ["XS (34/36)", "S (38)", "M (40/42)", "L (42/44)", "XL (46/48)", "XXL (50/52)"],
                        index=0 if user_data.get('Tamanho_Calca', '') not in ["XS (34/36)", "S (38)", "M (40/42)", "L (42/44)", "XL (46/48)", "XXL (50/52)"] else ["XS (34/36)", "S (38)", "M (40/42)", "L (42/44)", "XL (46/48)", "XXL (50/52)"].index(user_data.get('Tamanho_Calca', '')),
                        key="edit_tam_calc")
                with col14:
                    tam_botas = st.selectbox("Botas",
                        ["40", "41", "42", "43", "44", "45", "Outro"],
                        index=0 if user_data.get('Tamanho_Botas', '') not in ["40", "41", "42", "43", "44", "45", "Outro"] else ["40", "41", "42", "43", "44", "45", "Outro"].index(user_data.get('Tamanho_Botas', '')),
                        key="edit_tam_bot")
                
                # Secção 8: Observações
                st.markdown('<div class="subsection-title">📝 Observações</div>', unsafe_allow_html=True)
                
                observacoes = st.text_area("Observações", value=user_data.get('Observacoes', ''), disabled='Observacoes' in campos_bloqueados, key="edit_obs")
                
                # Informações de campos não editáveis
                st.info("""
                **🔒 Campos não editáveis:**
                - Nome, Tipo, Cargo, NIF (contacta admin para alterar)
                - Preço Hora (definido pelo admin)
                
                **Campos bloqueados pelo admin:** Serão mostrados como desativados acima.
                """)
                
                if st.form_submit_button("💾 Guardar Alterações", use_container_width=True, type="primary"):
                    # Atualizar campos editáveis
                    campos_para_atualizar = {
                        'Telefone': telefone,
                        'Email': email,
                        'Morada': morada,
                        'Localidade': localidade,
                        'Concelho': concelho,
                        'Codigo_Postal': cod_postal,
                        'Naturalidade': naturalidade,
                        'Nacionalidade': nacionalidade,
                        'Estado_Civil': estado_civil,
                        'Sexo': sexo,
                        'CC': cc,
                        'CC_Validade': cc_validade,
                        'NISS': niss,
                        'Dependentes': str(dependentes),
                        'Profissao': profissao,
                        'Categoria_Profissional': categoria,
                        'Habilitacoes_Literarias': habilitacoes,
                        'Contacto_Emergencia': contacto_emerg,
                        'Nome_Emergencia': nome_emerg,
                        'Grau_Parentesco': grau_parentesco,
                        'Banco_IBAN': iban,
                        'Tamanho_Camisola': tam_camisola,
                        'Tamanho_Calca': tam_calca,
                        'Tamanho_Botas': tam_botas,
                        'Observacoes': observacoes
                    }
                    
                    for campo, valor in campos_para_atualizar.items():
                        if campo not in campos_bloqueados:
                            users.loc[user_idx, campo] = valor
                    
                    save_db(users, "usuarios.csv")
                    
                    log_audit(usuario=user_nome, acao="EDITAR_PERFIL", tabela="usuarios.csv", registro_id=user_nome, detalhes="Perfil atualizado", ip="")
                    
                    inv()
                    st.success("✅ Perfil atualizado com sucesso!")
                    st.rerun()
            
            # Informações de leitura apenas COM PREÇO HORA BLUR + OLHO
            st.divider()
            st.markdown("### 📋 Informações do Perfil", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.metric(f"{ICONS['profile']} Cargo", user_data.get('Cargo', 'N/A'))
                st.metric(f"{ICONS['admin']} Tipo de Acesso", user_tipo)
                
                # Preço Hora com blur e ícone de olho
                st.markdown(f"""
                <div style="margin-top:10px;">
                    <div style="color:#94A3B8; font-size:0.9rem; margin-bottom:5px;">💰 Preço Hora</div>
                    <div id="preco_hora_container" style="display:flex; align-items:center; gap:10px;">
                        <span id="preco_hora_valor" class="blur-price" style="font-size:1.5rem; font-weight:bold; color:#10B981;" onclick="togglePrecoHora()">
                            € {user_data.get('PrecoHora', '15.0')}/hora
                        </span>
                        <span id="preco_hora_olho" style="cursor:pointer; font-size:1.2rem;" onclick="togglePrecoHora()">👁️</span>
                    </div>
                </div>
                <script>
                function togglePrecoHora() {{
                    const valor = document.getElementById('preco_hora_valor');
                    const olho = document.getElementById('preco_hora_olho');
                    if (valor.classList.contains('blur-price')) {{
                        valor.classList.remove('blur-price');
                        valor.classList.add('revealed');
                        olho.textContent = '👁️🗨️';
                    }} else {{
                        valor.classList.remove('revealed');
                        valor.classList.add('blur-price');
                        olho.textContent = '👁️';
                    }}
                }}
                </script>
                """, unsafe_allow_html=True)
                
            with c2:
                st.metric("📧 Email", user_data.get('Email', 'N/A'))
                st.metric("📞 Telefone", user_data.get('Telefone', 'N/A'))
                st.metric("📍 Local", user_data.get('Local', 'Não'))
            
            st.divider()
            if st.button(f"{ICONS['logout']} Sair do Sistema", use_container_width=True, type="secondary"):
                st.session_state.clear()
                st.rerun()
        else:
            st.warning("⚠️ Não foi possível carregar os dados do utilizador.")
    
    # =============================================================================
    # TAB PEDIDOS & DOCUMENTOS
    # =============================================================================
    with tabs[-1]:
        st.markdown(f"### {ICONS['material']} Pedidos & Documentos", unsafe_allow_html=True)
        
        sub_fer, sub_epi, sub_mat, sub_gas, sub_avar, sub_meus = st.tabs([
            "🔧 Ferramentas", "🦺 EPIs", "📦 Materiais", "⛽ Gasóleo", "🔧 Avarias", "📋 Meus Pedidos"
        ])
        
        # --- SUB-TAB: FERRAMENTAS ---
        with sub_fer:
            st.markdown("#### 🔧 Pedir Ferramentas")
            with st.form("form_pedir_fer"):
                obra_ped = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_fer_obra")
                desc_fer = st.text_area("Descrição da ferramenta necessária", key="ped_fer_desc")
                urgencia_fer = st.selectbox("Urgência", ["Baixa", "Média", "Alta"], key="ped_fer_urg")
                foto_fer = st.file_uploader("Foto da ferramenta (opcional)", type=["png", "jpg", "jpeg"], key="ped_fer_foto")
                
                if st.form_submit_button("📤 Enviar Pedido de Ferramenta", use_container_width=True, type="primary"):
                    if desc_fer:
                        foto_b64 = None
                        if foto_fer:
                            foto_b64 = process_and_compress_image(foto_fer)
                        
                        novo_ped = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome,
                            "Obra": obra_ped,
                            "Descricao": desc_fer,
                            "Urgencia": urgencia_fer,
                            "Foto_b64": foto_b64,
                            "Status": "Pendente"
                        }])
                        
                        if not req_fer_db.empty:
                            req_fer_db = pd.concat([req_fer_db, novo_ped], ignore_index=True)
                        else:
                            req_fer_db = novo_ped
                        
                        save_db(req_fer_db, "req_ferramentas.csv")
                        
                        log_audit(usuario=st.session_state.user, acao="PEDIR_FERRAMENTA", tabela="req_ferramentas.csv", registro_id=novo_ped['ID'].iloc[0], detalhes=f"Pedido de ferramenta por {user_nome} em {obra_ped}", ip="")
                        
                        criar_notificacao(destinatario="admin", titulo="🔧 Novo Pedido de Ferramenta", mensagem=f"{user_nome} pediu ferramenta em {obra_ped}: {desc_fer[:50]}...", tipo="warning", acao_url="/admin?tab=validacoes")
                        
                        st.success("✅ Pedido de ferramenta enviado!")
                        inv()
                        st.rerun()
                    else:
                        st.warning("⚠️ Por favor, descreve a ferramenta necessária.")
        
        # --- SUB-TAB: EPIs ---
        with sub_epi:
            st.markdown("#### 🦺 Pedir EPIs")
            with st.form("form_pedir_epi"):
                obra_epi = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_epi_obra")
                item_epi = st.selectbox("Tipo de EPI", ["Capacete", "Óculos de Proteção", "Luvas", "Botas de Segurança", "Arnés", "Protetor Auditivo", "Máscara", "Outro"], key="ped_epi_tipo")
                tamanho_epi = st.selectbox("Tamanho", ["P", "M", "G", "XG", "Único"], key="ped_epi_tam")
                qtd_epi = st.number_input("Quantidade", min_value=1, value=1, key="ped_epi_qtd")
                desc_epi = st.text_area("Observações (opcional)", key="ped_epi_obs")
                
                if st.form_submit_button("📤 Enviar Pedido de EPI", use_container_width=True, type="primary"):
                    novo_ped = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8].upper(),
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante": user_nome,
                        "Obra": obra_epi,
                        "Item": item_epi,
                        "Tamanho": tamanho_epi,
                        "Quantidade": qtd_epi,
                        "Descricao": desc_epi,
                        "Status": "Pendente"
                    }])
                    
                    if not req_epi_db.empty:
                        req_epi_db = pd.concat([req_epi_db, novo_ped], ignore_index=True)
                    else:
                        req_epi_db = novo_ped
                    
                    save_db(req_epi_db, "req_epis.csv")
                    
                    log_audit(usuario=st.session_state.user, acao="PEDIR_EPI", tabela="req_epis.csv", registro_id=novo_ped['ID'].iloc[0], detalhes=f"Pedido de EPI por {user_nome}: {item_epi} ({tamanho_epi})", ip="")
                    
                    criar_notificacao(destinatario="admin", titulo="🦺 Novo Pedido de EPI", mensagem=f"{user_nome} pediu {qtd_epi}x {item_epi} ({tamanho_epi}) em {obra_epi}", tipo="warning", acao_url="/admin?tab=validacoes")
                    
                    st.success("✅ Pedido de EPI enviado!")
                    inv()
                    st.rerun()
        
        # --- SUB-TAB: MATERIAIS ---
        with sub_mat:
            st.markdown("#### 📦 Pedir Materiais")
            with st.form("form_pedir_mat"):
                obra_mat = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_mat_obra")
                desc_mat = st.text_area("Descrição do material necessário", key="ped_mat_desc")
                qtd_mat = st.number_input("Quantidade", min_value=1, value=1, key="ped_mat_qtd")
                unidade_mat = st.selectbox("Unidade", ["un", "m", "kg", "l", "cx", "rol"], key="ped_mat_unid")
                urgencia_mat = st.selectbox("Urgência", ["Baixa", "Média", "Alta"], key="ped_mat_urg")
                
                if st.form_submit_button("📤 Enviar Pedido de Material", use_container_width=True, type="primary"):
                    if desc_mat:
                        novo_ped = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome,
                            "Obra": obra_mat,
                            "Descricao": desc_mat,
                            "Quantidade": qtd_mat,
                            "Unidade": unidade_mat,
                            "Urgencia": urgencia_mat,
                            "Status": "Pendente"
                        }])
                        
                        if not req_mat_db.empty:
                            req_mat_db = pd.concat([req_mat_db, novo_ped], ignore_index=True)
                        else:
                            req_mat_db = novo_ped
                        
                        save_db(req_mat_db, "req_materiais.csv")
                        
                        log_audit(usuario=st.session_state.user, acao="PEDIR_MATERIAL", tabela="req_materiais.csv", registro_id=novo_ped['ID'].iloc[0], detalhes=f"Pedido de material por {user_nome}: {qtd_mat}{unidade_mat} - {desc_mat[:30]}", ip="")
                        
                        criar_notificacao(destinatario="admin", titulo="📦 Novo Pedido de Material", mensagem=f"{user_nome} pediu {qtd_mat}{unidade_mat} de {desc_mat[:30]} em {obra_mat}", tipo="warning", acao_url="/admin?tab=validacoes")
                        
                        st.success("✅ Pedido de material enviado!")
                        inv()
                        st.rerun()
                    else:
                        st.warning("⚠️ Por favor, descreve o material necessário.")
        
        # --- SUB-TAB: GASÓLEO ---
        with sub_gas:
            st.markdown("#### ⛽ Registar Abastecimento de Gasóleo")
            with st.form("form_pedir_gas"):
                obra_gas = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_gas_obra")
                litros_gas = st.number_input("Litros Abastecidos", min_value=0.0, value=0.0, step=0.1, key="ped_gas_litros")
                valor_gas = st.number_input("Valor Total (€)", min_value=0.0, value=0.0, step=0.01, key="ped_gas_valor")
                data_gas = st.date_input("Data do Abastecimento", value=date.today(), key="ped_gas_data")
                desc_gas = st.text_area("Observações (viatura, km, etc.)", key="ped_gas_obs")
                recibo_gas = st.file_uploader("📄 Foto do Recibo (obrigatório)", type=["png", "jpg", "jpeg", "pdf"], key="ped_gas_recibo")
                
                if st.form_submit_button("📤 Enviar Registo de Gasóleo", use_container_width=True, type="primary"):
                    if recibo_gas and litros_gas > 0:
                        recibo_b64 = None
                        if recibo_gas.type == "application/pdf":
                            recibo_b64 = base64.b64encode(recibo_gas.read()).decode()
                        else:
                            recibo_b64 = process_and_compress_image(recibo_gas)
                        
                        novo_gas = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome,
                            "Obra": obra_gas,
                            "Litros": litros_gas,
                            "Valor": valor_gas,
                            "Data_Abastecimento": data_gas.strftime("%d/%m/%Y"),
                            "Descricao": desc_gas,
                            "Recibo_b64": recibo_b64,
                            "Status": "Pendente"
                        }])
                        
                        novo_gas['Tipo'] = "Gasóleo"
                        
                        if not req_mat_db.empty:
                            req_mat_db = pd.concat([req_mat_db, novo_gas], ignore_index=True)
                        else:
                            req_mat_db = novo_gas
                        
                        save_db(req_mat_db, "req_materiais.csv")
                        
                        log_audit(usuario=st.session_state.user, acao="REGISTAR_GASOLEO", tabela="req_materiais.csv", registro_id=novo_gas['ID'].iloc[0], detalhes=f"{user_nome} registou {litros_gas}L de gasóleo em {obra_gas}", ip="")
                        
                        criar_notificacao(destinatario="admin", titulo="⛽ Novo Registo de Gasóleo", mensagem=f"{user_nome} registou {litros_gas}L (€{valor_gas}) em {obra_gas}", tipo="info", acao_url="/admin?tab=validacoes")
                        
                        st.success("✅ Registo de gasóleo enviado com recibo!")
                        inv()
                        st.rerun()
                    else:
                        st.warning("⚠️ Por favor, faz upload do recibo e indica os litros.")
        
        # --- SUB-TAB: AVARIAS ---
        with sub_avar:
            st.markdown("#### 🔧 Reportar Avaria / Reparação")
            with st.form("form_pedir_avar"):
                obra_avar = st.selectbox("Obra", obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_avar_obra")
                equip_avar = st.text_input("Equipamento / Viatura", placeholder="Ex: Viatura ABC-123, Compressor XYZ", key="ped_avar_equip")
                desc_avar = st.text_area("Descrição da Avaria", key="ped_avar_desc")
                urgencia_avar = st.selectbox("Urgência", ["Baixa", "Média", "Alta", "Crítica - Paragem"], key="ped_avar_urg")
                valor_avar = st.number_input("Valor Estimado da Reparação (€)", min_value=0.0, value=0.0, step=0.01, key="ped_avar_valor")
                fatura_avar = st.file_uploader("📄 Foto da Fatura/Orçamento (obrigatório)", type=["png", "jpg", "jpeg", "pdf"], key="ped_avar_fatura")
                
                if st.form_submit_button("📤 Enviar Reporte de Avaria", use_container_width=True, type="primary"):
                    if fatura_avar and desc_avar:
                        fatura_b64 = None
                        if fatura_avar.type == "application/pdf":
                            fatura_b64 = base64.b64encode(fatura_avar.read()).decode()
                        else:
                            fatura_b64 = process_and_compress_image(fatura_avar)
                        
                        nova_avar = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome,
                            "Obra": obra_avar,
                            "Equipamento": equip_avar,
                            "Descricao": desc_avar,
                            "Urgencia": urgencia_avar,
                            "Valor_Estimado": valor_avar,
                            "Fatura_b64": fatura_b64,
                            "Status": "Pendente"
                        }])
                        
                        nova_avar['Tipo'] = "Avaria"
                        
                        if not incs_db.empty:
                            incs_db = pd.concat([incs_db, nova_avar], ignore_index=True)
                        else:
                            incs_db = nova_avar
                        
                        save_db(incs_db, "incidentes.csv")
                        
                        log_audit(usuario=st.session_state.user, acao="REPORTAR_AVARIA", tabela="incidentes.csv", registro_id=nova_avar['ID'].iloc[0], detalhes=f"Avaria reportada por {user_nome}: {equip_avar} em {obra_avar}", ip="")
                        
                        criar_notificacao(destinatario="admin", titulo="🔧 Nova Avaria Reportada", mensagem=f"{urgencia_avar}: {equip_avar} em {obra_avar} - {desc_avar[:30]}...", tipo="error" if urgencia_avar == "Crítica - Paragem" else "warning", acao_url="/admin?tab=validacoes")
                        
                        st.success("✅ Reporte de avaria enviado com fatura!")
                        inv()
                        st.rerun()
                    else:
                        st.warning("⚠️ Por favor, descreve a avaria e faz upload da fatura/orçamento.")
        
        # --- SUB-TAB: MEUS PEDIDOS ---
        with sub_meus:
            st.markdown("#### 📋 Histórico dos Meus Pedidos")
            
            if not req_fer_db.empty:
                meus_fer = req_fer_db[req_fer_db['Solicitante'] == user_nome]
                if not meus_fer.empty:
                    st.markdown("##### 🔧 Ferramentas")
                    for _, ped in meus_fer.iterrows():
                        cor_status = {"Pendente": "#F59E0B", "Aprovado": "#10B981", "Rejeitado": "#EF4444"}.get(ped.get('Status', 'Pendente'), "#6B7280")
                        st.markdown(f"""
                        <div class="pedido-card" style="border-left-color: {cor_status};">
                            <b>{ped.get('Descricao', 'N/A')}</b><br>
                            <small>Data: {ped.get('Data', 'N/A')} | Urgência: {ped.get('Urgencia', 'N/A')}<br>
                            Status: <span style="color:{cor_status}; font-weight:bold;">{ped.get('Status', 'Pendente')}</span></small>
                        </div>
                        """, unsafe_allow_html=True)
            
            if not req_epi_db.empty:
                meus_epi = req_epi_db[req_epi_db['Solicitante'] == user_nome]
                if not meus_epi.empty:
                    st.markdown("##### 🦺 EPIs")
                    for _, ped in meus_epi.iterrows():
                        cor_status = {"Pendente": "#F59E0B", "Aprovado": "#10B981", "Rejeitado": "#EF4444"}.get(ped.get('Status', 'Pendente'), "#6B7280")
                        st.markdown(f"""
                        <div class="pedido-card" style="border-left-color: {cor_status};">
                            <b>{ped.get('Item', 'N/A')} ({ped.get('Tamanho', 'N/A')}) x{ped.get('Quantidade', 1)}</b><br>
                            <small>Data: {ped.get('Data', 'N/A')}<br>
                            Status: <span style="color:{cor_status}; font-weight:bold;">{ped.get('Status', 'Pendente')}</span></small>
                        </div>
                        """, unsafe_allow_html=True)
            
            if not req_mat_db.empty:
                meus_mat = req_mat_db[req_mat_db['Solicitante'] == user_nome]
                if not meus_mat.empty:
                    st.markdown("##### 📦 Materiais & Outros")
                    for _, ped in meus_mat.iterrows():
                        cor_status = {"Pendente": "#F59E0B", "Aprovado": "#10B981", "Rejeitado": "#EF4444"}.get(ped.get('Status', 'Pendente'), "#6B7280")
                        st.markdown(f"""
                        <div class="pedido-card" style="border-left-color: {cor_status};">
                            <b>{ped.get('Descricao', ped.get('Equipamento', 'N/A'))}</b><br>
                            <small>Data: {ped.get('Data', 'N/A')} | {ped.get('Quantidade', '')}{ped.get('Unidade', '')}<br>
                            Status: <span style="color:{cor_status}; font-weight:bold;">{ped.get('Status', 'Pendente')}</span></small>
                        </div>
                        """, unsafe_allow_html=True)
            
            if (req_fer_db.empty or req_fer_db[req_fer_db['Solicitante'] == user_nome].empty) and \
               (req_epi_db.empty or req_epi_db[req_epi_db['Solicitante'] == user_nome].empty) and \
               (req_mat_db.empty or req_mat_db[req_mat_db['Solicitante'] == user_nome].empty):
                st.info("📋 Ainda não fizeste nenhum pedido.")

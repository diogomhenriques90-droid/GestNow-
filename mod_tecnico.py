import streamlit as st
import pandas as pd
import uuid, secrets, base64, io, json
from datetime import datetime, timedelta, date
from streamlit_drawable_canvas import st_canvas
from PIL import Image

from core import (
    save_db, inv, fh, sl, render_metric,
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
            
            pdfs_obrigatorios = [
                {"id": "regulamento", "nome": "📋 Regulamento Interno", "url": "https://exemplo.com/regulamento.pdf"},
                {"id": "hse", "nome": "🛡️ Política de Segurança e HSE", "url": "https://exemplo.com/hse.pdf"},
                {"id": "qualidade", "nome": "📊 Procedimentos de Qualidade", "url": "https://exemplo.com/qualidade.pdf"}
            ]
            
            # Carregar PDFs já vistos
            try:
                pdfs_vistos = json.loads(user_data.get('PDFs_Vistos', '[]'))
            except:
                pdfs_vistos = []
            
            todos_vistos = True
            for pdf in pdfs_obrigatorios:
                visto = pdf['id'] in pdfs_vistos
                
                with st.container():
                    st.markdown(f"""
                    <div class="pdf-card {'validado' if visto else ''}">
                        <h4 style="margin:0 0 10px 0;">{pdf['nome']}</h4>
                        <a href="{pdf['url']}" target="_blank" style="text-decoration:none;">
                            <button style="background:#3B82F6; color:white; border:none; padding:10px 20px; border-radius:8px; cursor:pointer; margin-bottom:10px;">
                                📄 Visualizar PDF
                            </button>
                        </a>
                        <br>
                        <small style="color:{'#10B981' if visto else '#EF4444'};">
                            {'✅ Validado' if visto else '❌ Não validado'}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if not visto:
                        todos_vistos = False
                        if st.button(f"✅ Confirmar Visualização: {pdf['nome']}", key=f"validar_{pdf['id']}"):
                            pdfs_vistos.append(pdf['id'])
                            users.loc[user_idx, 'PDFs_Vistos'] = json.dumps(pdfs_vistos)
                            
                            # Se todos foram vistos, marcar como validado
                            if len(pdfs_vistos) >= len(pdfs_obrigatorios):
                                users.loc[user_idx, 'PDFs_Validados'] = 'Sim'
                                users.loc[user_idx, 'PDFs_Validacao_Data'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                
                                # Notificar admin RH
                                criar_notificacao(
                                    destinatario="admin",
                                    titulo="✅ Colaborador Validou PDFs",
                                    mensagem=f"{user_nome} validou a visualização dos PDFs obrigatórios",
                                    tipo="success",
                                    acao_url="/admin?tab=rh"
                                )
                                
                                log_audit(usuario=user_nome, acao="VALIDAR_PDFS_OBRIGATORIOS", tabela="usuarios.csv", registro_id=user_nome, detalhes=f"PDFs validados: {pdfs_vistos}", ip="")
                            
                            save_db(users, "usuarios.csv")
                            inv()
                            st.success("✅ Validação registada!")
                            st.rerun()
            
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
                        st.warning("❌ Preço hora recusado. Contacta o admin para negociação.")
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
                    'Telefone': user_data.get('Telefone', ''),
                    'Morada': user_data.get('Morada', ''),
                    'NIF': user_data.get('NIF', ''),
                    'NISS': user_data.get('NISS', ''),
                    'CC': user_data.get('CC', ''),
                    'DataNasc': user_data.get('DataNasc', ''),
                    'Nacionalidade': user_data.get('Nacionalidade', 'Portugal'),
                }
                
                # Tamanhos EPI (sempre editáveis)
                tamanhos_epis = {
                    'Tamanho_Capacete': user_data.get('Tamanho_Capacete', ''),
                    'Tamanho_Camisola': user_data.get('Tamanho_Camisola', ''),
                    'Tamanho_Casaco': user_data.get('Tamanho_Casaco', ''),
                    'Tamanho_Calças': user_data.get('Tamanho_Calças', ''),
                    'Tamanho_Botas': user_data.get('Tamanho_Botas', ''),
                    'Tamanho_Luvas': user_data.get('Tamanho_Luvas', ''),
                }
                
                with col1:
                    for campo, valor in campos_editaveis.items():
                        bloqueado = campo in campos_bloqueados
                        if bloqueado:
                            st.text_input(f"🔒 {campo}", value=valor, disabled=True, key=f"edit_{campo}")
                        else:
                            st.text_input(campo, value=valor, key=f"edit_{campo}")
                    
                    st.markdown("#### 👕 Tamanhos EPI")
                    for campo, valor in tamanhos_epis.items():
                        label = campo.replace('Tamanho_', '').replace('_', ' ')
                        st.selectbox(label, ["P", "M", "G", "XG", "Único"], index=["P", "M", "G", "XG", "Único"].index(valor) if valor in ["P", "M", "G", "XG", "Único"] else 1, key=f"edit_{campo}")
                
                with col2:
                    st.info("""
                    **Campos não editáveis:**
                    - 🔒 Preço Hora (definido pelo admin)
                    - 🔒 Nome, Tipo, Cargo (contacta admin para alterar)
                    
                    **Campos bloqueados pelo admin:**
                    """)
                    if campos_bloqueados:
                        for cb in campos_bloqueados:
                            st.write(f"🔒 {cb}")
                    else:
                        st.write("✅ Nenhum campo bloqueado")
                
                if st.form_submit_button("💾 Guardar Alterações", use_container_width=True, type="primary"):
                    # Atualizar campos editáveis
                    for campo in campos_editaveis:
                        if campo not in campos_bloqueados:
                            users.loc[user_idx, campo] = st.session_state[f"edit_{campo}"]
                    
                    # Atualizar tamanhos EPI
                    for campo in tamanhos_epis:
                        users.loc[user_idx, campo] = st.session_state[f"edit_{campo}"]
                    
                    save_db(users, "usuarios.csv")
                    
                    log_audit(usuario=user_nome, acao="EDITAR_PERFIL", tabela="usuarios.csv", registro_id=user_nome, detalhes="Perfil atualizado", ip="")
                    
                    inv()
                    st.success("✅ Perfil atualizado com sucesso!")
                    st.rerun()
            
            # Informações de leitura apenas
            st.divider()
            st.markdown("### 📋 Informações do Perfil", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.metric(f"{ICONS['profile']} Cargo", user_data.get('Cargo', 'N/A'))
                st.metric(f"{ICONS['admin']} Tipo de Acesso", user_tipo)
                st.metric("💰 Preço Hora", f"€ {user_data.get('PrecoHora', '15.0')}")
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

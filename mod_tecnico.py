import streamlit as st
import pandas as pd
import uuid, secrets, base64, io
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
    """Renderiza módulo Técnico com design industrial moderno + Pedidos + Documentos"""
    
    # 1. Desempacotamento das variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    user_nome = st.session_state.get('user', 'Usuário')
    cargo_user = st.session_state.get('cargo', 'Técnico')
    user_tipo = st.session_state.get('tipo', 'Técnico')

    # Lógica de Permissões
    is_chefe = user_tipo in ['Chefe de Equipa', 'Admin', 'Gestor'] or cargo_user in ['Chefe de Equipa', 'Encarregado']
    
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
    </style>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # DEFINIÇÃO DE TABS - ATUALIZADO COM PEDIDOS
    # =============================================================================
    menu = [f"{ICONS['dashboard']} Pontos", f"{ICONS['safety']} Segurança (HSE)", f"{ICONS['profile']} Perfil", f"{ICONS['material']} Pedidos"]
    if is_chefe:
        menu.insert(1, f"{ICONS['reports']} Folha de Ponto")
    
    tabs = st.tabs(menu)
    
    # =============================================================================
    # TAB 1: REGISTO DE PONTO (CALENDÁRIO & CARDS)
    # =============================================================================
    with tabs[0]:
        st.markdown(f"### {ICONS['dashboard']} Registo de Ponto")
        
        # Calendário Semanal Interativo
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
        
        # Formulário de Registo
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
        
        # Visualização dos Cards do Dia Selecionado
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
    # TAB 2 (CHEFE): FOLHA DE PONTO & E-SIGN - CORRIGIDO
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
            
            # Selecionar período
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                semana_inicio = st.date_input("Início da Semana", value=inicio_sem, key="fp_inicio")
            with col_p2:
                semana_fim = st.date_input("Fim da Semana", value=inicio_sem + timedelta(days=6), key="fp_fim")
            
            # Carregar registos do período
            if not registos_db.empty:
                regs_periodo = registos_db[
                    (registos_db['Obra'] == obra_f) &
                    (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date >= semana_inicio) &
                    (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date <= semana_fim)
                ]
                
                if not regs_periodo.empty:
                    st.markdown(f"### 📋 Registos de {semana_inicio.strftime('%d/%m')} a {semana_fim.strftime('%d/%m/%Y')}")
                    
                    # Agrupar por técnico
                    for tecnico in regs_periodo['Técnico'].unique():
                        regs_tec = regs_periodo[regs_periodo['Técnico'] == tecnico]
                        total_horas = regs_tec['Horas_Total'].astype(float).sum()
                        
                        st.markdown(f"""
                        <div class="pedido-card">
                            <b>👤 {tecnico}</b><br>
                            <small>{len(regs_tec)} dias registados | <b>{total_horas:.1f}h totais</b></small>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Canvas para Assinatura
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
                            
                            # Guardar folha de ponto
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
    # TAB PEDIDOS & DOCUMENTOS (NOVA!)
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
        
        # --- SUB-TAB: GASÓLEO (COM UPLOAD DE RECIBO) ---
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
                            # Para PDF, guardar como base64 simples
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
                        
                        # Guardar em req_mat_db ou criar tabela separada
                        # Para simplificar, vamos usar req_mat_db com tipo "Gasóleo"
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
        
        # --- SUB-TAB: AVARIAS (COM UPLOAD DE FATURA) ---
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
                        
                        # Guardar em incs_db ou tabela separada de avarias
                        # Para simplificar, vamos usar incs_db com tipo "Avaria"
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
        
        # --- SUB-TAB: MEUS PEDIDOS (HISTÓRICO) ---
        with sub_meus:
            st.markdown("#### 📋 Histórico dos Meus Pedidos")
            
            # Ferramentas
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
            
            # EPIs
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
            
            # Materiais
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
            
            # Se não houver pedidos
            if (req_fer_db.empty or req_fer_db[req_fer_db['Solicitante'] == user_nome].empty) and \
               (req_epi_db.empty or req_epi_db[req_epi_db['Solicitante'] == user_nome].empty) and \
               (req_mat_db.empty or req_mat_db[req_mat_db['Solicitante'] == user_nome].empty):
                st.info("📋 Ainda não fizeste nenhum pedido.")
    
    # =============================================================================
    # TAB PERFIL: INFORMAÇÕES E LOGOUT
    # =============================================================================
    with tabs[-1 if not is_chefe else -2]:
        st.markdown(f"### {ICONS['profile']} Perfil do Colaborador")
        
        if not users.empty:
            u_data = users[users['Nome'] == user_nome]
            if not u_data.empty:
                u = u_data.iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(f"{ICONS['profile']} Cargo", u.get('Cargo', 'N/A'))
                with c2:
                    st.metric(f"{ICONS['admin']} Tipo de Acesso", st.session_state.get('tipo', 'Técnico'))
                
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; margin-top:15px;">
                    <p><strong>Email:</strong> {u.get('Email', 'N/A')}</p>
                    <p><strong>Telefone:</strong> {u.get('Telefone', 'N/A')}</p>
                    <p><strong>Preço Hora:</strong> € {u.get('PrecoHora', '15.0')}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        if st.button(f"{ICONS['logout']} Sair do Sistema", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()

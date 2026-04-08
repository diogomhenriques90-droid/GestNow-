"""
GESTNOW v3 — mod_cliente.py
Portal do Cliente - Visualização de Projetos e Aprovações
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from core import load_db, save_db, inv, log_audit, criar_notificacao

def render_cliente_portal():
    """Portal do Cliente para visualização e aprovação de projetos"""
    
    # CSS Personalizado
    st.markdown("""
    <style>
    .cliente-header {
        background: linear-gradient(135deg, #1E293B, #0F172A);
        padding: 30px;
        border-radius: 20px;
        margin-bottom: 30px;
        border: 2px solid rgba(59,130,246,0.5);
    }
    .cliente-card {
        background: rgba(59,130,246,0.1);
        border: 2px solid rgba(59,130,246,0.3);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
    <div class="cliente-header">
        <h1 style="color:#F8FAFC; margin:0;">🏢 Portal do Cliente</h1>
        <p style="color:#94A3B8; margin:10px 0 0 0;">Bem-vindo, <strong style="color:#60A5FA">{st.session_state.user}</strong></p>
        <p style="color:#64748B; margin:5px 0 0 0; font-size:0.9rem;">{datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carregar dados
    try:
        obras_db = load_db("obras_lista.csv", ["Obra", "Cliente", "TipoObra", "Ativa"])
        insts_db = pd.DataFrame()
        logs_db = load_db("logs_audit.csv", ["ID", "Data", "Hora", "Usuario", "Acao", "Tabela", "Registro_ID", "Detalhes", "IP"], silent=True)
    except:
        st.error("❌ Erro ao carregar dados.")
        return
    
    # Filtrar obras do cliente
    cliente_nome = st.session_state.user
    obras_cliente = obras_db[(obras_db['Cliente'] == cliente_nome) & (obras_db['Ativa'] == 'Ativa')]
    
    if obras_cliente.empty:
        st.warning("⚠️ Não tem obras ativas no momento.")
        return
    
    # Seleção de Obra
    st.markdown("### 🏗️ Selecione o Projeto", unsafe_allow_html=True)
    obra_sel = st.selectbox("Projeto", obras_cliente['Obra'].tolist(), key="cliente_obra_sel")
    
    if not obra_sel:
        return
    
    o_key = obra_sel.replace(' ', '_').replace('/', '_')
    
    # Carregar instrumentos da obra
    try:
        insts_db = load_db(f"inst_{o_key}_index.csv", ["ID", "Tag", "Tipo", "Descricao", "Status", "GPS_Lat", "GPS_Lng", "Assinatura_Calibracao_b64", "Assinatura_Instalacao_b64"])
    except:
        insts_db = pd.DataFrame()
    
    # Dashboard de Progresso
    st.markdown("### 📊 Progresso da Obra", unsafe_allow_html=True)
    
    total = len(insts_db) if not insts_db.empty else 0
    pendentes = len(insts_db[insts_db['Status'] == '0']) if not insts_db.empty else 0
    material_ok = len(insts_db[insts_db['Status'] == '1']) if not insts_db.empty else 0
    calibrados = len(insts_db[insts_db['Status'] == '2']) if not insts_db.empty else 0
    instalados = len(insts_db[insts_db['Status'].isin(['3', '4'])]) if not insts_db.empty else 0
    
    progresso = (instalados / total * 100) if total > 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Instrumentos", total)
    with col2:
        st.metric("Pendentes", pendentes)
    with col3:
        st.metric("Material OK", material_ok)
    with col4:
        st.metric("Calibrados", calibrados)
    with col5:
        st.metric("Instalados", instalados)
    
    # Barra de progresso
    st.progress(progresso / 100)
    st.write(f"**{progresso:.1f}% Concluído**")
    
    st.divider()
    
    # Tabs
    tab_resumo, tab_instrumentos, tab_aprovar, tab_docs, tab_punch = st.tabs([
        "📋 Resumo", 
        "🔧 Instrumentos", 
        "✅ Aprovações", 
        "📄 Documentação",
        "💬 Punch List"
    ])
    
    # TAB RESUMO
    with tab_resumo:
        st.markdown("### 📋 Resumo do Projeto", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="cliente-card">
            <h3>🏗️ {obra_sel}</h3>
            <p><strong>Cliente:</strong> {cliente_nome}</p>
            <p><strong>Estado:</strong> {'✅ Ativa' if obra_sel in obras_cliente['Obra'].values else '⏸️ Inativa'}</p>
            <p><strong>Progresso:</strong> {progresso:.1f}%</p>
            <p><strong>Instrumentos Instalados:</strong> {instalados} de {total}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Timeline de atividades recentes
        st.markdown("### 🕐 Atividades Recentes", unsafe_allow_html=True)
        
        if not logs_db.empty:
            logs_obra = logs_db[logs_db['Tabela'].str.contains(o_key, na=False)]
            logs_recentes = logs_obra.tail(10) if len(logs_obra) > 10 else logs_obra
            
            if not logs_recentes.empty:
                for _, log in logs_recentes.iterrows():
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; margin-bottom:10px;">
                        <small style="color:#64748B">{log['Data']} {log['Hora']}</small>
                        <p style="margin:5px 0;"><strong>{log['Acao']}</strong>: {log['Detalhes']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📋 Sem atividades recentes.")
        else:
            st.info("📋 Sem logs disponíveis.")
    
    # TAB INSTRUMENTOS
    with tab_instrumentos:
        st.markdown("### 🔧 Lista de Instrumentos", unsafe_allow_html=True)
        
        if not insts_db.empty:
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                filtro_tipo = st.multiselect("Tipo", insts_db['Tipo'].unique() if 'Tipo' in insts_db.columns else [], key="cliente_filt_tipo")
            with col2:
                filtro_status = st.multiselect("Status", insts_db['Status'].unique() if 'Status' in insts_db.columns else [], key="cliente_filt_status")
            
            df_f = insts_db.copy()
            if filtro_tipo:
                df_f = df_f[df_f['Tipo'].isin(filtro_tipo)]
            if filtro_status:
                df_f = df_f[df_f['Status'].isin(filtro_status)]
            
            # Mapear status para texto
            status_map = {
                '0': '⏳ Pendente',
                '1': '📦 Material OK',
                '2': '🔬 Calibrado',
                '3': '📍 Instalado',
                '4': '✅ Concluído'
            }
            
            if 'Status' in df_f.columns:
                df_f['Status_Texto'] = df_f['Status'].map(status_map)
            
            # Colunas a mostrar
            colunas = ['Tag', 'Tipo', 'Descricao', 'Status_Texto'] if 'Status_Texto' in df_f.columns else ['Tag', 'Tipo', 'Descricao']
            
            st.dataframe(df_f[colunas], use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Sem instrumentos registados para esta obra.")
    
    # TAB APROVAR
    with tab_aprovar:
        st.markdown("### ✅ Aprovação de ITRs", unsafe_allow_html=True)
        
        # Instrumentos prontos para aprovação (instalados)
        if not insts_db.empty and 'Status' in insts_db.columns:
            prontos_aprovar = insts_db[insts_db['Status'].isin(['2', '3', '4'])]
            
            if not prontos_aprovar.empty:
                st.write(f"**{len(prontos_aprovar)} instrumento(s) pronto(s) para aprovação**")
                
                tag_aprovar = st.selectbox("Selecione o Instrumento", prontos_aprovar['Tag'].tolist(), key="cliente_aprovar_tag")
                
                if tag_aprovar:
                    inst = prontos_aprovar[prontos_aprovar['Tag'] == tag_aprovar].iloc[0]
                    
                    st.markdown(f"""
                    <div class="cliente-card">
                        <h4>🔧 {tag_aprovar}</h4>
                        <p><strong>Tipo:</strong> {inst.get('Tipo', 'N/A')}</p>
                        <p><strong>Descrição:</strong> {inst.get('Descricao', 'N/A')}</p>
                        <p><strong>Status:</strong> {inst.get('Status', 'N/A')}</p>
                        <p><strong>Calibração:</strong> {'✅ Assinada' if inst.get('Assinatura_Calibracao_b64') else '⏳ Pendente'}</p>
                        <p><strong>Instalação:</strong> {'✅ Assinada' if inst.get('Assinatura_Instalacao_b64') else '⏳ Pendente'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Checkbox de aprovação
                    aprovar = st.checkbox("✅ Confirmo que este instrumento está instalado e funcional", key=f"aprov_{tag_aprovar}")
                    
                    if aprovar:
                        comentario = st.text_area("Comentários (opcional)", key=f"coment_{tag_aprovar}")
                        
                        if st.button("✅ Aprovar Instrumento", use_container_width=True, type="primary", key=f"btn_aprov_{tag_aprovar}"):
                            # Log de aprovação
                            log_audit(
                                usuario=f"CLIENTE: {cliente_nome}",
                                acao="APROVAR_INSTRUMENTO_CLIENTE",
                                tabela=f"inst_{o_key}_index.csv",
                                registro_id=tag_aprovar,
                                detalhes=f"Cliente aprovou {tag_aprovar}. Comentário: {comentario}",
                                ip=""
                            )
                            
                            # Notificar admin
                            criar_notificacao(
                                destinatario="admin",
                                titulo="✅ Cliente Aprovou Instrumento",
                                mensagem=f"{cliente_nome} aprovou {tag_aprovar} em {obra_sel}",
                                tipo="success",
                                acao_url=f"/instrumentacao?obra={o_key}"
                            )
                            
                            st.success(f"✅ {tag_aprovar} aprovado com sucesso!")
                            st.rerun()
            else:
                st.info("ℹ️ Nenhum instrumento pronto para aprovação.")
        else:
            st.info("ℹ️ Sem instrumentos disponíveis.")
    
    # TAB DOCUMENTAÇÃO
    with tab_docs:
        st.markdown("### 📄 Documentação da Obra", unsafe_allow_html=True)
        
        st.info("📋 Documentação em desenvolvimento. Em breve poderá descarregar:\n- Relatórios de Calibração (ITR-A)\n- Relatórios de Instalação (ITR-B)\n- Handover Completo\n- Certificados")
    
    # TAB PUNCH LIST
    with tab_punch:
        st.markdown("### 💬 Punch List / Comentários", unsafe_allow_html=True)
        
        # Carregar punch list existente
        try:
            punch_db = load_db(f"punch_{o_key}.csv", ["ID", "Data", "Autor", "Tag", "Descricao", "Prioridade", "Estado"], silent=True)
        except:
            punch_db = pd.DataFrame(columns=["ID", "Data", "Autor", "Tag", "Descricao", "Prioridade", "Estado"])
        
        # Mostrar punch list existente
        if not punch_db.empty:
            st.markdown("#### 📋 Punch List Existente")
            st.dataframe(punch_db, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Adicionar novo item
        st.markdown("#### ➕ Adicionar Novo Item")
        
        with st.form("form_punch_cliente"):
            col1, col2 = st.columns(2)
            with col1:
                tag_punch = st.text_input("Tag do Instrumento (opcional)", key="punch_tag")
            with col2:
                prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"], key="punch_prior")
            
            descricao = st.text_area("Descrição do Issue/Comentário", key="punch_desc")
            
            if st.form_submit_button("💬 Adicionar à Punch List", use_container_width=True, type="primary"):
                if descricao:
                    import uuid
                    novo_item = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8].upper(),
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Autor": f"CLIENTE: {cliente_nome}",
                        "Tag": tag_punch if tag_punch else "N/A",
                        "Descricao": descricao,
                        "Prioridade": prioridade,
                        "Estado": "Aberto"
                    }])
                    
                    if punch_db.empty:
                        punch_db = novo_item
                    else:
                        punch_db = pd.concat([punch_db, novo_item], ignore_index=True)
                    
                    save_db(punch_db, f"punch_{o_key}.csv")
                    
                    # Log
                    log_audit(
                        usuario=f"CLIENTE: {cliente_nome}",
                        acao="CRIAR_PUNCH_ITEM",
                        tabela=f"punch_{o_key}.csv",
                        registro_id=novo_item['ID'].iloc[0],
                        detalhes=f"Punch item criado: {descricao[:50]}...",
                        ip=""
                    )
                    
                    # Notificar
                    criar_notificacao(
                        destinatario="admin",
                        titulo="💬 Novo Punch Item",
                        mensagem=f"{cliente_nome} adicionou issue em {obra_sel}: {descricao[:50]}...",
                        tipo="warning",
                        acao_url=f"/admin?tab=qualidade"
                    )
                    
                    st.success("✅ Item adicionado à punch list!")
                    st.rerun()
                else:
                    st.warning("⚠️ Por favor, preencha a descrição.")

import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, log_audit, criar_notificacao, notificar_por_email

def render_validacoes(req_fer_db, req_mat_db, req_epi_db, registos_db, users, obras_db, incs_db):
    """Módulo de Validações Completo - Horas, EPIs, Ferramentas, Materiais, Gasóleos, Avarias"""
    
    st.markdown("### ✅ Centro de Validações", unsafe_allow_html=True)
    
    # Tabs principais com sub-tabs de histórico
    tab_horas, tab_epis, tab_ferramentas, tab_materiais, tab_gasoleos, tab_avarias = st.tabs([
        "⏱️ Horas", "🦺 EPIs", "🔧 Ferramentas", "📦 Materiais", "⛽ Gasóleos", "🔧 Avarias"
    ])
    
    # ========== TAB HORAS ==========
    with tab_horas:
        st.markdown("### Validação de Horas", unsafe_allow_html=True)
        
        sub_horas_pend, sub_horas_hist = st.tabs(["🟠 Pendentes", "📋 Histórico"])
        
        with sub_horas_pend:
            col1, col2 = st.columns(2)
            with col1:
                filtro = st.selectbox("Filtrar por", ["Todos", "Técnico", "Obra"], key="val_filtro")
            with col2:
                estado = st.selectbox("Estado", ["Todos", "🟠 Pendente", "🟢 Aprovado", "🔵 Faturação", "⚪ Faturado"], key="val_estado")
            
            if not registos_db.empty:
                pendentes = registos_db[registos_db['Status'] == "0"]
                st.dataframe(pendentes[['Data', 'Técnico', 'Obra', 'Horas_Total']], use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🟢 Validar", use_container_width=True, key="btn_val_horas"):
                        registos_db.loc[registos_db['Status'] == "0", 'Status'] = "1"
                        save_db(registos_db, "registos.csv")
                        
                        for _, reg in pendentes.iterrows():
                            log_audit(usuario=st.session_state.user, acao="APROVAR_HORAS", tabela="registos.csv", registro_id=reg.get('ID', f"{reg['Técnico']}_{reg['Data']}"), detalhes=f"Aprovadas {reg['Horas_Total']}h de {reg['Técnico']} em {reg['Obra']}", ip="")
                            criar_notificacao(destinatario=reg['Técnico'], titulo="✅ Horas Aprovadas", mensagem=f"As suas {reg['Horas_Total']}h em {reg['Obra']} foram aprovadas!", tipo="success", acao_url="/registos")
                        
                        inv()
                        st.success(f"✅ {len(pendentes)} registos validados!")
                        st.rerun()
                        
                with col2:
                    if st.button("🔵 Faturação", use_container_width=True, key="btn_val_fat"):
                        registos_db.loc[registos_db['Status'] == "0", 'Status'] = "2"
                        save_db(registos_db, "registos.csv")
                        
                        for _, reg in pendentes.iterrows():
                            log_audit(usuario=st.session_state.user, acao="PRONTO_FATURACAO", tabela="registos.csv", registro_id=reg.get('ID', f"{reg['Técnico']}_{reg['Data']}"), detalhes=f"Enviado para faturação: {reg['Horas_Total']}h de {reg['Técnico']}", ip="")
                        
                        inv()
                        st.success(f"✅ {len(pendentes)} registos enviados para faturação!")
                        st.rerun()
                        
                with col3:
                    if st.button("❌ Rejeitar", use_container_width=True, key="btn_val_rej"):
                        registos_db.loc[registos_db['Status'] == "0", 'Status'] = "-1"
                        save_db(registos_db, "registos.csv")
                        
                        for _, reg in pendentes.iterrows():
                            log_audit(usuario=st.session_state.user, acao="REJEITAR_HORAS", tabela="registos.csv", registro_id=reg.get('ID', f"{reg['Técnico']}_{reg['Data']}"), detalhes=f"Rejeitado: {reg['Horas_Total']}h de {reg['Técnico']} em {reg['Obra']}", ip="")
                            criar_notificacao(destinatario=reg['Técnico'], titulo="❌ Horas Rejeitadas", mensagem=f"As suas {reg['Horas_Total']}h em {reg['Obra']} foram rejeitadas. Contacte o gestor.", tipo="error", acao_url="/registos")
                        
                        inv()
                        st.error(f"❌ {len(pendentes)} registos rejeitados!")
                        st.rerun()
            else:
                st.info("📋 Sem registos de horas.")
        
        with sub_horas_hist:
            st.markdown("#### 📋 Histórico de Horas Validadas")
            if not registos_db.empty:
                historico = registos_db[registos_db['Status'].isin(["1", "2", "-1"])]
                if not historico.empty:
                    # Mapear status
                    status_map = {"1": "✅ Aprovado", "2": "🔵 Faturação", "-1": "❌ Rejeitado"}
                    historico['Status_Texto'] = historico['Status'].map(status_map)
                    st.dataframe(historico[['Data', 'Técnico', 'Obra', 'Horas_Total', 'Status_Texto']], use_container_width=True)
                else:
                    st.info("📋 Sem histórico de horas.")
            else:
                st.info("📋 Sem registos.")

    # ========== TAB EPIs ==========
    with tab_epis:
        st.markdown("### 🦺 Validação de EPIs", unsafe_allow_html=True)
        
        sub_epi_pend, sub_epi_hist = st.tabs(["🟠 Pendentes", "📋 Histórico"])
        
        with sub_epi_pend:
            if not req_epi_db.empty:
                pendentes_epi = req_epi_db[req_epi_db['Status'] == 'Pendente']
                
                if 'ID' not in pendentes_epi.columns:
                    pendentes_epi = pendentes_epi.copy()
                    pendentes_epi['ID'] = pendentes_epi.index.astype(str)
                
                if not pendentes_epi.empty:
                    st.markdown(f"#### 📋 {len(pendentes_epi)} Pedido(s) Pendente(s)")
                    
                    for idx, ped in pendentes_epi.iterrows():
                        ped_id = ped.get('ID', f"EPI_{idx}")
                        
                        with st.expander(f"🦺 {ped.get('Item', 'EPI')} - {ped.get('Solicitante', 'N/A')} ({ped.get('Obra', 'N/A')})", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante', 'N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra', 'N/A')}</p>
                                <p><strong>Item:</strong> {ped.get('Item', 'N/A')} ({ped.get('Tamanho', 'N/A')})</p>
                                <p><strong>Quantidade:</strong> {ped.get('Quantidade', 1)}</p>
                                <p><strong>Data:</strong> {ped.get('Data', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col_apr, col_rej = st.columns(2)
                            with col_apr:
                                if st.button("✅ Aprovar", key=f"apr_epi_{ped_id}", use_container_width=True):
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Status'] = 'Aprovado'
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Validado_Por'] = st.session_state.user
                                    save_db(req_epi_db, "req_epis.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_EPI", tabela="req_epis.csv", registro_id=ped_id, detalhes=f"EPI aprovado para {ped.get('Solicitante')}: {ped.get('Item')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="✅ EPI Aprovado", mensagem=f"O teu pedido de {ped.get('Item')} foi aprovado!", tipo="success", acao_url="/tecnico")
                                    st.success("✅ Aprovado!")
                                    inv()
                                    st.rerun()
                            with col_rej:
                                if st.button("❌ Rejeitar", key=f"rej_epi_{ped_id}", use_container_width=True, type="secondary"):
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Status'] = 'Rejeitado'
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Validado_Por'] = st.session_state.user
                                    save_db(req_epi_db, "req_epis.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_EPI", tabela="req_epis.csv", registro_id=ped_id, detalhes=f"EPI rejeitado para {ped.get('Solicitante')}: {ped.get('Item')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="❌ EPI Rejeitado", mensagem=f"O teu pedido de {ped.get('Item')} foi rejeitado. Contacta o admin.", tipo="error", acao_url="/tecnico")
                                    st.error("❌ Rejeitado!")
                                    inv()
                                    st.rerun()
                else:
                    st.success("✅ Sem pedidos de EPI pendentes!")
            else:
                st.info("📋 Sem pedidos de EPI.")
        
        with sub_epi_hist:
            st.markdown("#### 📋 Histórico de Pedidos de EPI")
            if not req_epi_db.empty:
                historico = req_epi_db[req_epi_db['Status'].isin(['Aprovado', 'Rejeitado'])]
                if not historico.empty:
                    st.dataframe(historico[['Data', 'Solicitante', 'Obra', 'Item', 'Quantidade', 'Status', 'Data_Validacao', 'Validado_Por']], use_container_width=True)
                else:
                    st.info("📋 Sem histórico de EPIs.")
            else:
                st.info("📋 Sem registos.")

    # ========== TAB FERRAMENTAS ==========
    with tab_ferramentas:
        st.markdown("### 🔧 Validação de Ferramentas", unsafe_allow_html=True)
        
        sub_fer_pend, sub_fer_hist = st.tabs(["🟠 Pendentes", "📋 Histórico"])
        
        with sub_fer_pend:
            if not req_fer_db.empty:
                pendentes_fer = req_fer_db[req_fer_db['Status'] == 'Pendente']
                
                if 'ID' not in pendentes_fer.columns:
                    pendentes_fer = pendentes_fer.copy()
                    pendentes_fer['ID'] = pendentes_fer.index.astype(str)
                
                if not pendentes_fer.empty:
                    st.markdown(f"#### 📋 {len(pendentes_fer)} Pedido(s) Pendente(s)")
                    
                    for idx, ped in pendentes_fer.iterrows():
                        ped_id = ped.get('ID', f"FER_{idx}")
                        
                        with st.expander(f"🔧 {ped.get('Descricao', 'Ferramenta')[:50]} - {ped.get('Solicitante', 'N/A')}", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante', 'N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra', 'N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao', 'N/A')}</p>
                                <p><strong>Urgência:</strong> {ped.get('Urgencia', 'N/A')}</p>
                                <p><strong>Data:</strong> {ped.get('Data', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if ped.get('Foto_b64'):
                                st.image(f"image/png;base64,{ped['Foto_b64']}", caption="Foto da ferramenta", width=200)
                            
                            col_apr, col_rej = st.columns(2)
                            with col_apr:
                                if st.button("✅ Aprovar", key=f"apr_fer_{ped_id}", use_container_width=True):
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Status'] = 'Aprovado'
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Validado_Por'] = st.session_state.user
                                    save_db(req_fer_db, "req_ferramentas.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_FERRAMENTA", tabela="req_ferramentas.csv", registro_id=ped_id, detalhes=f"Ferramenta aprovada para {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="✅ Ferramenta Aprovada", mensagem=f"O teu pedido de ferramenta foi aprovado!", tipo="success", acao_url="/tecnico")
                                    st.success("✅ Aprovado!")
                                    inv()
                                    st.rerun()
                            with col_rej:
                                if st.button("❌ Rejeitar", key=f"rej_fer_{ped_id}", use_container_width=True, type="secondary"):
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Status'] = 'Rejeitado'
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Validado_Por'] = st.session_state.user
                                    save_db(req_fer_db, "req_ferramentas.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_FERRAMENTA", tabela="req_ferramentas.csv", registro_id=ped_id, detalhes=f"Ferramenta rejeitada para {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="❌ Ferramenta Rejeitada", mensagem=f"O teu pedido de ferramenta foi rejeitado.", tipo="error", acao_url="/tecnico")
                                    st.error("❌ Rejeitado!")
                                    inv()
                                    st.rerun()
                else:
                    st.success("✅ Sem pedidos de ferramentas pendentes!")
            else:
                st.info("📋 Sem pedidos de ferramentas.")
        
        with sub_fer_hist:
            st.markdown("#### 📋 Histórico de Pedidos de Ferramentas")
            if not req_fer_db.empty:
                historico = req_fer_db[req_fer_db['Status'].isin(['Aprovado', 'Rejeitado'])]
                if not historico.empty:
                    st.dataframe(historico[['Data', 'Solicitante', 'Obra', 'Descricao', 'Urgencia', 'Status', 'Data_Validacao', 'Validado_Por']], use_container_width=True)
                else:
                    st.info("📋 Sem histórico de ferramentas.")
            else:
                st.info("📋 Sem registos.")

    # ========== TAB MATERIAIS ==========
    with tab_materiais:
        st.markdown("### 📦 Validação de Materiais", unsafe_allow_html=True)
        
        sub_mat_pend, sub_mat_hist = st.tabs(["🟠 Pendentes", "📋 Histórico"])
        
        with sub_mat_pend:
            if not req_mat_db.empty:
                pendentes_mat = req_mat_db[(req_mat_db['Status'] == 'Pendente') & (req_mat_db.get('Tipo', '') != 'Gasóleo')]
                
                if 'ID' not in pendentes_mat.columns:
                    pendentes_mat = pendentes_mat.copy()
                    pendentes_mat['ID'] = pendentes_mat.index.astype(str)
                
                if not pendentes_mat.empty:
                    st.markdown(f"#### 📋 {len(pendentes_mat)} Pedido(s) Pendente(s)")
                    
                    for idx, ped in pendentes_mat.iterrows():
                        ped_id = ped.get('ID', f"MAT_{idx}")
                        
                        with st.expander(f"📦 {ped.get('Descricao', 'Material')[:50]} - {ped.get('Solicitante', 'N/A')}", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante', 'N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra', 'N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao', 'N/A')}</p>
                                <p><strong>Quantidade:</strong> {ped.get('Quantidade', 1)}{ped.get('Unidade', '')}</p>
                                <p><strong>Urgência:</strong> {ped.get('Urgencia', 'N/A')}</p>
                                <p><strong>Data:</strong> {ped.get('Data', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col_apr, col_rej = st.columns(2)
                            with col_apr:
                                if st.button("✅ Aprovar", key=f"apr_mat_{ped_id}", use_container_width=True):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status'] = 'Aprovado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por'] = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_MATERIAL", tabela="req_materiais.csv", registro_id=ped_id, detalhes=f"Material aprovado para {ped.get('Solicitante')}: {ped.get('Descricao', '')[:30]}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="✅ Material Aprovado", mensagem=f"O teu pedido de material foi aprovado!", tipo="success", acao_url="/tecnico")
                                    st.success("✅ Aprovado!")
                                    inv()
                                    st.rerun()
                            with col_rej:
                                if st.button("❌ Rejeitar", key=f"rej_mat_{ped_id}", use_container_width=True, type="secondary"):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status'] = 'Rejeitado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por'] = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_MATERIAL", tabela="req_materiais.csv", registro_id=ped_id, detalhes=f"Material rejeitado para {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="❌ Material Rejeitado", mensagem=f"O teu pedido de material foi rejeitado.", tipo="error", acao_url="/tecnico")
                                    st.error("❌ Rejeitado!")
                                    inv()
                                    st.rerun()
                else:
                    st.success("✅ Sem pedidos de materiais pendentes!")
            else:
                st.info("📋 Sem pedidos de materiais.")
        
        with sub_mat_hist:
            st.markdown("#### 📋 Histórico de Pedidos de Materiais")
            if not req_mat_db.empty:
                historico = req_mat_db[(req_mat_db['Status'].isin(['Aprovado', 'Rejeitado'])) & (req_mat_db.get('Tipo', '') != 'Gasóleo')]
                if not historico.empty:
                    st.dataframe(historico[['Data', 'Solicitante', 'Obra', 'Descricao', 'Quantidade', 'Unidade', 'Status', 'Data_Validacao', 'Validado_Por']], use_container_width=True)
                else:
                    st.info("📋 Sem histórico de materiais.")
            else:
                st.info("📋 Sem registos.")

    # ========== TAB GASÓLEOS ==========
    with tab_gasoleos:
        st.markdown("### ⛽ Validação de Gasóleos", unsafe_allow_html=True)
        
        sub_gas_pend, sub_gas_hist = st.tabs(["🟠 Pendentes", "📋 Histórico"])
        
        with sub_gas_pend:
            if not req_mat_db.empty:
                pendentes_gas = req_mat_db[(req_mat_db['Status'] == 'Pendente') & (req_mat_db.get('Tipo', '') == 'Gasóleo')]
                
                if 'ID' not in pendentes_gas.columns:
                    pendentes_gas = pendentes_gas.copy()
                    pendentes_gas['ID'] = pendentes_gas.index.astype(str)
                
                if not pendentes_gas.empty:
                    st.markdown(f"#### 📋 {len(pendentes_gas)} Registo(s) de Gasóleo Pendente(s)")
                    
                    for idx, ped in pendentes_gas.iterrows():
                        ped_id = ped.get('ID', f"GAS_{idx}")
                        
                        with st.expander(f"⛽ {ped.get('Litros', 0)}L - {ped.get('Solicitante', 'N/A')} ({ped.get('Obra', 'N/A')})", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante', 'N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra', 'N/A')}</p>
                                <p><strong>Litros:</strong> {ped.get('Litros', 0)}L</p>
                                <p><strong>Valor:</strong> €{ped.get('Valor', 0):.2f}</p>
                                <p><strong>Data Abastecimento:</strong> {ped.get('Data_Abastecimento', 'N/A')}</p>
                                <p><strong>Data Registo:</strong> {ped.get('Data', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if ped.get('Recibo_b64'):
                                if str(ped.get('Recibo_b64', '')).startswith('JVBER'):
                                    st.info("📄 Recibo em formato PDF - descarrega para visualizar")
                                else:
                                    st.image(f"image/png;base64,{ped['Recibo_b64']}", caption="Recibo de Gasóleo", width=300)
                            
                            col_apr, col_rej = st.columns(2)
                            with col_apr:
                                if st.button("✅ Validar", key=f"apr_gas_{ped_id}", use_container_width=True):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status'] = 'Aprovado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por'] = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_GASOLEO", tabela="req_materiais.csv", registro_id=ped_id, detalhes=f"Gasóleo validado para {ped.get('Solicitante')}: {ped.get('Litros')}L", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="✅ Gasóleo Validado", mensagem=f"O teu registo de {ped.get('Litros')}L de gasóleo foi validado!", tipo="success", acao_url="/tecnico")
                                    st.success("✅ Validado!")
                                    inv()
                                    st.rerun()
                            with col_rej:
                                if st.button("❌ Rejeitar", key=f"rej_gas_{ped_id}", use_container_width=True, type="secondary"):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status'] = 'Rejeitado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por'] = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_GASOLEO", tabela="req_materiais.csv", registro_id=ped_id, detalhes=f"Gasóleo rejeitado para {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="❌ Gasóleo Rejeitado", mensagem=f"O teu registo de gasóleo foi rejeitado. Contacta o admin.", tipo="error", acao_url="/tecnico")
                                    st.error("❌ Rejeitado!")
                                    inv()
                                    st.rerun()
                else:
                    st.success("✅ Sem registos de gasóleo pendentes!")
            else:
                st.info("📋 Sem registos de gasóleo.")
        
        with sub_gas_hist:
            st.markdown("#### 📋 Histórico de Registos de Gasóleo")
            if not req_mat_db.empty:
                historico = req_mat_db[(req_mat_db['Status'].isin(['Aprovado', 'Rejeitado'])) & (req_mat_db.get('Tipo', '') == 'Gasóleo')]
                if not historico.empty:
                    st.dataframe(historico[['Data', 'Solicitante', 'Obra', 'Litros', 'Valor', 'Status', 'Data_Validacao', 'Validado_Por']], use_container_width=True)
                else:
                    st.info("📋 Sem histórico de gasóleos.")
            else:
                st.info("📋 Sem registos.")

    # ========== TAB AVARIAS ==========
    with tab_avarias:
        st.markdown("### 🔧 Validação de Avarias / Reparações", unsafe_allow_html=True)
        
        sub_avar_pend, sub_avar_hist = st.tabs(["🟠 Pendentes", "📋 Histórico"])
        
        with sub_avar_pend:
            if not incs_db.empty:
                pendentes_avar = incs_db[(incs_db['Status'] == 'Pendente') & (incs_db.get('Tipo', '') == 'Avaria')]
                
                if 'ID' not in pendentes_avar.columns:
                    pendentes_avar = pendentes_avar.copy()
                    pendentes_avar['ID'] = pendentes_avar.index.astype(str)
                
                if not pendentes_avar.empty:
                    st.markdown(f"#### 📋 {len(pendentes_avar)} Avaria(s) Pendente(s)")
                    
                    for idx, ped in pendentes_avar.iterrows():
                        ped_id = ped.get('ID', f"AVAR_{idx}")
                        cor_urg = {"Baixa": "#10B981", "Média": "#F59E0B", "Alta": "#EF4444", "Crítica - Paragem": "#DC2626"}.get(ped.get('Urgencia', 'Média'), "#6B7280")
                        
                        with st.expander(f"🔧 {ped.get('Equipamento', 'Equipamento')[:40]} - {ped.get('Solicitante', 'N/A')}", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; border-left:4px solid {cor_urg};">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante', 'N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra', 'N/A')}</p>
                                <p><strong>Equipamento:</strong> {ped.get('Equipamento', 'N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao', 'N/A')}</p>
                                <p><strong>Urgência:</strong> <span style="color:{cor_urg}; font-weight:bold;">{ped.get('Urgencia', 'N/A')}</span></p>
                                <p><strong>Valor Estimado:</strong> €{ped.get('Valor_Estimado', 0):.2f}</p>
                                <p><strong>Data:</strong> {ped.get('Data', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if ped.get('Fatura_b64'):
                                if str(ped.get('Fatura_b64', '')).startswith('JVBER'):
                                    st.info("📄 Fatura em formato PDF - descarrega para visualizar")
                                else:
                                    st.image(f"image/png;base64,{ped['Fatura_b64']}", caption="Fatura/Orçamento", width=300)
                            
                            col_apr, col_rej = st.columns(2)
                            with col_apr:
                                if st.button("✅ Aprovar Reparação", key=f"apr_avar_{ped_id}", use_container_width=True):
                                    incs_db.loc[incs_db.index == idx, 'Status'] = 'Aprovado'
                                    incs_db.loc[incs_db.index == idx, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    incs_db.loc[incs_db.index == idx, 'Validado_Por'] = st.session_state.user
                                    save_db(incs_db, "incidentes.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_AVARIA", tabela="incidentes.csv", registro_id=ped_id, detalhes=f"Avaria aprovada para {ped.get('Solicitante')}: {ped.get('Equipamento')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="✅ Reparação Aprovada", mensagem=f"A tua reparação de {ped.get('Equipamento')} foi aprovada!", tipo="success", acao_url="/tecnico")
                                    st.success("✅ Aprovado!")
                                    inv()
                                    st.rerun()
                            with col_rej:
                                if st.button("❌ Rejeitar", key=f"rej_avar_{ped_id}", use_container_width=True, type="secondary"):
                                    incs_db.loc[incs_db.index == idx, 'Status'] = 'Rejeitado'
                                    incs_db.loc[incs_db.index == idx, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    incs_db.loc[incs_db.index == idx, 'Validado_Por'] = st.session_state.user
                                    save_db(incs_db, "incidentes.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_AVARIA", tabela="incidentes.csv", registro_id=ped_id, detalhes=f"Avaria rejeitada para {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante', 'N/A'), titulo="❌ Reparação Rejeitada", mensagem=f"A tua reparação foi rejeitada. Contacta o admin.", tipo="error", acao_url="/tecnico")
                                    st.error("❌ Rejeitado!")
                                    inv()
                                    st.rerun()
                else:
                    st.success("✅ Sem avarias pendentes!")
            else:
                st.info("📋 Sem avarias registadas.")
        
        with sub_avar_hist:
            st.markdown("#### 📋 Histórico de Avarias / Reparações")
            if not incs_db.empty:
                historico = incs_db[(incs_db['Status'].isin(['Aprovado', 'Rejeitado'])) & (incs_db.get('Tipo', '') == 'Avaria')]
                if not historico.empty:
                    st.dataframe(historico[['Data', 'Solicitante', 'Obra', 'Equipamento', 'Urgencia', 'Valor_Estimado', 'Status', 'Data_Validacao', 'Validado_Por']], use_container_width=True)
                else:
                    st.info("📋 Sem histórico de avarias.")
            else:
                st.info("📋 Sem registos.")

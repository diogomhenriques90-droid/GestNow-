import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, log_audit, criar_notificacao, notificar_por_email

def render_validacoes(req_fer_db, req_mat_db, req_epi_db, registos_db, users, obras_db):
    """Módulo de Validações Completo - Horas, EPIs, Ferramentas, Materiais, Gasóleos, Avarias"""
    
    st.markdown("### ✅ Centro de Validações", unsafe_allow_html=True)
    
    # Tabs para todas as validações
    tab_horas, tab_epis, tab_ferramentas, tab_materiais, tab_gasoleos, tab_avarias = st.tabs([
        "⏱️ Horas", "🦺 EPIs", "🔧 Ferramentas", "📦 Materiais", "⛽ Gasóleos", "🔧 Avarias"
    ])
    
    # ========== TAB HORAS ==========
    with tab_horas:
        st.markdown("### Validação de Horas", unsafe_allow_html=True)
        
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

    # ========== TAB EPIs - VALIDAÇÃO INDIVIDUAL ==========
    with tab_epis:
        st.markdown("### 🦺 Validação de EPIs", unsafe_allow_html=True)
        
        if not req_epi_db.empty:
            pendentes_epi = req_epi_db[req_epi_db['Status'] == 'Pendente']
            
            if not pendentes_epi.empty:
                st.markdown(f"#### 📋 {len(pendentes_epi)} Pedido(s) Pendente(s)")
                
                for idx, ped in pendentes_epi.iterrows():
                    with st.expander(f"🦺 {ped.get('Item', 'EPI')} - {ped.get('Solicitante', 'N/A')} ({ped.get('Obra', 'N/A')})", expanded=True):
                        st.markdown(f"""
                        <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px;">
                            <p><strong>Solicitante:</strong> {ped.get('Solicitante', 'N/A')}</p>
                            <p><strong>Obra:</strong> {ped.get('Obra', 'N/A')}</p>
                            <p><strong>Item:</strong> {ped.get('Item', 'N/A')} ({ped.get('Tamanho', 'N/A')})</p>
                            <p><strong>Quantidade:</strong> {ped.get('Quantidade', 1)}</p>
                            <p><strong>Data:</strong> {ped.get('Data', 'N/A')}</p>
                            <p><strong>Observações:</strong> {ped.get('Descricao', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_apr, col_rej = st.columns(2)
                        with col_apr:
                            if st.button("✅ Aprovar", key=f"apr_epi_{ped['ID']}", use_container_width=True):
                                req_epi_db.loc[req_epi_db['ID'] == ped['ID'], 'Status'] = 'Aprovado'
                                save_db(req_epi_db, "req_epis.csv")
                                log_audit(usuario=st.session_state.user, acao="APROVAR_EPI", tabela="req_epis.csv", registro_id=ped['ID'], detalhes=f"EPI aprovado para {ped.get('Solicitante')}: {ped.get('Item')}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="✅ EPI Aprovado", mensagem=f"O teu pedido de {ped.get('Item')} foi aprovado!", tipo="success", acao_url="/tecnico")
                                st.success("✅ Aprovado!")
                                inv()
                                st.rerun()
                        with col_rej:
                            if st.button("❌ Rejeitar", key=f"rej_epi_{ped['ID']}", use_container_width=True, type="secondary"):
                                req_epi_db.loc[req_epi_db['ID'] == ped['ID'], 'Status'] = 'Rejeitado'
                                save_db(req_epi_db, "req_epis.csv")
                                log_audit(usuario=st.session_state.user, acao="REJEITAR_EPI", tabela="req_epis.csv", registro_id=ped['ID'], detalhes=f"EPI rejeitado para {ped.get('Solicitante')}: {ped.get('Item')}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="❌ EPI Rejeitado", mensagem=f"O teu pedido de {ped.get('Item')} foi rejeitado. Contacta o admin.", tipo="error", acao_url="/tecnico")
                                st.error("❌ Rejeitado!")
                                inv()
                                st.rerun()
            else:
                st.success("✅ Sem pedidos de EPI pendentes!")
        else:
            st.info("📋 Sem pedidos de EPI.")

    # ========== TAB FERRAMENTAS - VALIDAÇÃO INDIVIDUAL ==========
    with tab_ferramentas:
        st.markdown("### 🔧 Validação de Ferramentas", unsafe_allow_html=True)
        
        if not req_fer_db.empty:
            pendentes_fer = req_fer_db[req_fer_db['Status'] == 'Pendente']
            
            if not pendentes_fer.empty:
                st.markdown(f"#### 📋 {len(pendentes_fer)} Pedido(s) Pendente(s)")
                
                for idx, ped in pendentes_fer.iterrows():
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
                        
                        # Mostrar foto se existir
                        if ped.get('Foto_b64'):
                            st.image(f"data:image/png;base64,{ped['Foto_b64']}", caption="Foto da ferramenta", width=200)
                        
                        col_apr, col_rej = st.columns(2)
                        with col_apr:
                            if st.button("✅ Aprovar", key=f"apr_fer_{ped['ID']}", use_container_width=True):
                                req_fer_db.loc[req_fer_db['ID'] == ped['ID'], 'Status'] = 'Aprovado'
                                save_db(req_fer_db, "req_ferramentas.csv")
                                log_audit(usuario=st.session_state.user, acao="APROVAR_FERRAMENTA", tabela="req_ferramentas.csv", registro_id=ped['ID'], detalhes=f"Ferramenta aprovada para {ped.get('Solicitante')}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="✅ Ferramenta Aprovada", mensagem=f"O teu pedido de ferramenta foi aprovado!", tipo="success", acao_url="/tecnico")
                                st.success("✅ Aprovado!")
                                inv()
                                st.rerun()
                        with col_rej:
                            if st.button("❌ Rejeitar", key=f"rej_fer_{ped['ID']}", use_container_width=True, type="secondary"):
                                req_fer_db.loc[req_fer_db['ID'] == ped['ID'], 'Status'] = 'Rejeitado'
                                save_db(req_fer_db, "req_ferramentas.csv")
                                log_audit(usuario=st.session_state.user, acao="REJEITAR_FERRAMENTA", tabela="req_ferramentas.csv", registro_id=ped['ID'], detalhes=f"Ferramenta rejeitada para {ped.get('Solicitante')}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="❌ Ferramenta Rejeitada", mensagem=f"O teu pedido de ferramenta foi rejeitado.", tipo="error", acao_url="/tecnico")
                                st.error("❌ Rejeitado!")
                                inv()
                                st.rerun()
            else:
                st.success("✅ Sem pedidos de ferramentas pendentes!")
        else:
            st.info("📋 Sem pedidos de ferramentas.")

    # ========== TAB MATERIAIS - VALIDAÇÃO INDIVIDUAL ==========
    with tab_materiais:
        st.markdown("### 📦 Validação de Materiais", unsafe_allow_html=True)
        
        if not req_mat_db.empty:
            # Filtrar apenas materiais (excluir gasóleos que também estão aqui)
            pendentes_mat = req_mat_db[(req_mat_db['Status'] == 'Pendente') & (req_mat_db.get('Tipo', '') != 'Gasóleo')]
            
            if not pendentes_mat.empty:
                st.markdown(f"#### 📋 {len(pendentes_mat)} Pedido(s) Pendente(s)")
                
                for idx, ped in pendentes_mat.iterrows():
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
                            if st.button("✅ Aprovar", key=f"apr_mat_{ped['ID']}", use_container_width=True):
                                req_mat_db.loc[req_mat_db['ID'] == ped['ID'], 'Status'] = 'Aprovado'
                                save_db(req_mat_db, "req_materiais.csv")
                                log_audit(usuario=st.session_state.user, acao="APROVAR_MATERIAL", tabela="req_materiais.csv", registro_id=ped['ID'], detalhes=f"Material aprovado para {ped.get('Solicitante')}: {ped.get('Descricao', '')[:30]}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="✅ Material Aprovado", mensagem=f"O teu pedido de material foi aprovado!", tipo="success", acao_url="/tecnico")
                                st.success("✅ Aprovado!")
                                inv()
                                st.rerun()
                        with col_rej:
                            if st.button("❌ Rejeitar", key=f"rej_mat_{ped['ID']}", use_container_width=True, type="secondary"):
                                req_mat_db.loc[req_mat_db['ID'] == ped['ID'], 'Status'] = 'Rejeitado'
                                save_db(req_mat_db, "req_materiais.csv")
                                log_audit(usuario=st.session_state.user, acao="REJEITAR_MATERIAL", tabela="req_materiais.csv", registro_id=ped['ID'], detalhes=f"Material rejeitado para {ped.get('Solicitante')}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="❌ Material Rejeitado", mensagem=f"O teu pedido de material foi rejeitado.", tipo="error", acao_url="/tecnico")
                                st.error("❌ Rejeitado!")
                                inv()
                                st.rerun()
            else:
                st.success("✅ Sem pedidos de materiais pendentes!")
        else:
            st.info("📋 Sem pedidos de materiais.")

    # ========== TAB GASÓLEOS - COM VISUALIZAÇÃO DE RECIBO ==========
    with tab_gasoleos:
        st.markdown("### ⛽ Validação de Gasóleos", unsafe_allow_html=True)
        
        if not req_mat_db.empty:
            # Filtrar apenas gasóleos
            pendentes_gas = req_mat_db[(req_mat_db['Status'] == 'Pendente') & (req_mat_db.get('Tipo', '') == 'Gasóleo')]
            
            if not pendentes_gas.empty:
                st.markdown(f"#### 📋 {len(pendentes_gas)} Registo(s) de Gasóleo Pendente(s)")
                
                for idx, ped in pendentes_gas.iterrows():
                    with st.expander(f"⛽ {ped.get('Litros', 0)}L - {ped.get('Solicitante', 'N/A')} ({ped.get('Obra', 'N/A')})", expanded=True):
                        st.markdown(f"""
                        <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px;">
                            <p><strong>Solicitante:</strong> {ped.get('Solicitante', 'N/A')}</p>
                            <p><strong>Obra:</strong> {ped.get('Obra', 'N/A')}</p>
                            <p><strong>Litros:</strong> {ped.get('Litros', 0)}L</p>
                            <p><strong>Valor:</strong> €{ped.get('Valor', 0):.2f}</p>
                            <p><strong>Data Abastecimento:</strong> {ped.get('Data_Abastecimento', 'N/A')}</p>
                            <p><strong>Data Registo:</strong> {ped.get('Data', 'N/A')}</p>
                            <p><strong>Observações:</strong> {ped.get('Descricao', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Mostrar recibo se existir
                        if ped.get('Recibo_b64'):
                            if ped.get('Recibo_b64', '').startswith('JVBER'):
                                st.info("📄 Recibo em formato PDF - descarrega para visualizar")
                            else:
                                st.image(f"data:image/png;base64,{ped['Recibo_b64']}", caption="Recibo de Gasóleo", width=300)
                        
                        col_apr, col_rej = st.columns(2)
                        with col_apr:
                            if st.button("✅ Validar", key=f"apr_gas_{ped['ID']}", use_container_width=True):
                                req_mat_db.loc[req_mat_db['ID'] == ped['ID'], 'Status'] = 'Aprovado'
                                save_db(req_mat_db, "req_materiais.csv")
                                log_audit(usuario=st.session_state.user, acao="APROVAR_GASOLEO", tabela="req_materiais.csv", registro_id=ped['ID'], detalhes=f"Gasóleo validado para {ped.get('Solicitante')}: {ped.get('Litros')}L", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="✅ Gasóleo Validado", mensagem=f"O teu registo de {ped.get('Litros')}L de gasóleo foi validado!", tipo="success", acao_url="/tecnico")
                                st.success("✅ Validado!")
                                inv()
                                st.rerun()
                        with col_rej:
                            if st.button("❌ Rejeitar", key=f"rej_gas_{ped['ID']}", use_container_width=True, type="secondary"):
                                req_mat_db.loc[req_mat_db['ID'] == ped['ID'], 'Status'] = 'Rejeitado'
                                save_db(req_mat_db, "req_materiais.csv")
                                log_audit(usuario=st.session_state.user, acao="REJEITAR_GASOLEO", tabela="req_materiais.csv", registro_id=ped['ID'], detalhes=f"Gasóleo rejeitado para {ped.get('Solicitante')}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="❌ Gasóleo Rejeitado", mensagem=f"O teu registo de gasóleo foi rejeitado. Contacta o admin.", tipo="error", acao_url="/tecnico")
                                st.error("❌ Rejeitado!")
                                inv()
                                st.rerun()
            else:
                st.success("✅ Sem registos de gasóleo pendentes!")
        else:
            st.info("📋 Sem registos de gasóleo.")

    # ========== TAB AVARIAS - COM VISUALIZAÇÃO DE FATURA ==========
    with tab_avarias:
        st.markdown("### 🔧 Validação de Avarias / Reparações", unsafe_allow_html=True)
        
        if not incs_db.empty:
            # Filtrar apenas avarias
            pendentes_avar = incs_db[(incs_db['Status'] == 'Pendente') & (incs_db.get('Tipo', '') == 'Avaria')]
            
            if not pendentes_avar.empty:
                st.markdown(f"#### 📋 {len(pendentes_avar)} Avaria(s) Pendente(s)")
                
                for idx, ped in pendentes_avar.iterrows():
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
                        
                        # Mostrar fatura se existir
                        if ped.get('Fatura_b64'):
                            if ped.get('Fatura_b64', '').startswith('JVBER'):
                                st.info("📄 Fatura em formato PDF - descarrega para visualizar")
                            else:
                                st.image(f"data:image/png;base64,{ped['Fatura_b64']}", caption="Fatura/Orçamento", width=300)
                        
                        col_apr, col_rej = st.columns(2)
                        with col_apr:
                            if st.button("✅ Aprovar Reparação", key=f"apr_avar_{ped['ID']}", use_container_width=True):
                                incs_db.loc[incs_db['ID'] == ped['ID'], 'Status'] = 'Aprovado'
                                save_db(incs_db, "incidentes.csv")
                                log_audit(usuario=st.session_state.user, acao="APROVAR_AVARIA", tabela="incidentes.csv", registro_id=ped['ID'], detalhes=f"Avaria aprovada para {ped.get('Solicitante')}: {ped.get('Equipamento')}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="✅ Reparação Aprovada", mensagem=f"A tua reparação de {ped.get('Equipamento')} foi aprovada!", tipo="success", acao_url="/tecnico")
                                st.success("✅ Aprovado!")
                                inv()
                                st.rerun()
                        with col_rej:
                            if st.button("❌ Rejeitar", key=f"rej_avar_{ped['ID']}", use_container_width=True, type="secondary"):
                                incs_db.loc[incs_db['ID'] == ped['ID'], 'Status'] = 'Rejeitado'
                                save_db(incs_db, "incidentes.csv")
                                log_audit(usuario=st.session_state.user, acao="REJEITAR_AVARIA", tabela="incidentes.csv", registro_id=ped['ID'], detalhes=f"Avaria rejeitada para {ped.get('Solicitante')}", ip="")
                                criar_notificacao(destinatario=ped['Solicitante'], titulo="❌ Reparação Rejeitada", mensagem=f"A tua reparação foi rejeitada. Contacta o admin.", tipo="error", acao_url="/tecnico")
                                st.error("❌ Rejeitado!")
                                inv()
                                st.rerun()
            else:
                st.success("✅ Sem avarias pendentes!")
        else:
            st.info("📋 Sem avarias registadas.")

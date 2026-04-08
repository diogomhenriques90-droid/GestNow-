import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, log_audit
from core import log_audit, criar_notificacao

def render_validacoes(req_fer_db, req_mat_db, req_epi_db, registos_db, users, obras_db):
    """Módulo de Validações (EPIs, Ferramentas, Materiais, Horas)"""
    
    st.markdown("### ✅ Centro de Validações", unsafe_allow_html=True)
    
    tab_horas, tab_epis, tab_ferramentas, tab_materiais = st.tabs([
        "⏱️ Horas", "🦺 EPIs", "🔧 Ferramentas", "📦 Materiais"
    ])
    
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
            
            # 🔔 NOTIFICAR TÉCNICO
            criar_notificacao(
                destinatario=reg['Técnico'],
                titulo="✅ Horas Aprovadas",
                mensagem=f"As suas {reg['Horas_Total']}h em {reg['Obra']} foram aprovadas!",
                tipo="success",
                acao_url="/registos"
            )
        
        inv()
        st.success(f"✅ {len(pendentes)} registos validados!")
        st.rerun()
                    
            with col2:
                if st.button("🔵 Faturação", use_container_width=True, key="btn_val_fat"):
                    # Atualiza status para pronto para faturação (2)
                    registos_db.loc[registos_db['Status'] == "0", 'Status'] = "2"
                    save_db(registos_db, "registos.csv")
                    
                    # Log de auditoria
                    for _, reg in pendentes.iterrows():
                        log_audit(
                            usuario=st.session_state.user,
                            acao="PRONTO_FATURACAO",
                            tabela="registos.csv",
                            registro_id=reg.get('ID', f"{reg['Técnico']}_{reg['Data']}"),
                            detalhes=f"Enviado para faturação: {reg['Horas_Total']}h de {reg['Técnico']}",
                            ip=""
                        )
                    
                    inv()
                    st.success(f"✅ {len(pendentes)} registos enviados para faturação!")
                    st.rerun()
                    
            with col3:
             with col3:
    if st.button("❌ Rejeitar", use_container_width=True, key="btn_val_rej"):
        registos_db.loc[registos_db['Status'] == "0", 'Status'] = "-1"
        save_db(registos_db, "registos.csv")
        
        for _, reg in pendentes.iterrows():
            log_audit(usuario=st.session_state.user, acao="REJEITAR_HORAS", tabela="registos.csv", registro_id=reg.get('ID', f"{reg['Técnico']}_{reg['Data']}"), detalhes=f"Rejeitado: {reg['Horas_Total']}h de {reg['Técnico']} em {reg['Obra']}", ip="")
            
            # 🔔 NOTIFICAR TÉCNICO
            criar_notificacao(
                destinatario=reg['Técnico'],
                titulo="❌ Horas Rejeitadas",
                mensagem=f"As suas {reg['Horas_Total']}h em {reg['Obra']} foram rejeitadas. Contacte o gestor.",
                tipo="error",
                acao_url="/registos"
            )
        
        inv()
        st.error(f"❌ {len(pendentes)} registos rejeitados!")
        st.rerun()  

    with tab_epis:
        st.markdown("### 🦺 Validação de EPIs", unsafe_allow_html=True)
        if not req_epi_db.empty:
            st.dataframe(req_epi_db, use_container_width=True)
            if st.button("✅ Validar EPIs", key="btn_val_epi"):
                # Log de auditoria
                for _, req in req_epi_db.iterrows():
                    log_audit(
                        usuario=st.session_state.user,
                        acao="APROVAR_EPI",
                        tabela="req_epi.csv",
                        registro_id=req.get('ID', ''),
                        detalhes=f"EPI aprovado para {req.get('Técnico', 'N/A')}",
                        ip=""
                    )
                st.success("✅ EPIs validados!")
                st.rerun()
        else:
            st.info("📋 Sem pedidos de EPI")

    with tab_ferramentas:
        st.markdown("### 🔧 Validação de Ferramentas", unsafe_allow_html=True)
        if not req_fer_db.empty:
            st.dataframe(req_fer_db, use_container_width=True)
            if st.button("✅ Validar Ferramentas", key="btn_val_fer"):
                # Log de auditoria
                for _, req in req_fer_db.iterrows():
                    log_audit(
                        usuario=st.session_state.user,
                        acao="APROVAR_FERRAMENTA",
                        tabela="req_fer.csv",
                        registro_id=req.get('ID', ''),
                        detalhes=f"Ferramenta aprovada para {req.get('Técnico', 'N/A')}",
                        ip=""
                    )
                st.success("✅ Ferramentas validadas!")
                st.rerun()
        else:
            st.info("📋 Sem pedidos de ferramentas")

    with tab_materiais:
        st.markdown("### 📦 Validação de Materiais", unsafe_allow_html=True)
        if not req_mat_db.empty:
            st.dataframe(req_mat_db, use_container_width=True)
            if st.button("✅ Validar Materiais", key="btn_val_mat"):
                # Log de auditoria
                for _, req in req_mat_db.iterrows():
                    log_audit(
                        usuario=st.session_state.user,
                        acao="APROVAR_MATERIAL",
                        tabela="req_mat.csv",
                        registro_id=req.get('ID', ''),
                        detalhes=f"Material aprovado para {req.get('Técnico', 'N/A')}",
                        ip=""
                    )
                st.success("✅ Materiais validados!")
                st.rerun()
        else:
            st.info("📋 Sem pedidos de materiais")

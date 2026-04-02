import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

def render_qualidade():
    """Módulo de Gestão da Qualidade"""
    
    st.markdown("### 🎯 Gestão da Qualidade", unsafe_allow_html=True)
    
    tab_itrs, tab_nao_conf, tab_auditorias, tab_certificacoes = st.tabs([
        "📋 ITRs", "⚠️ Não Conformidades", "🔍 Auditorias", "📜 Certificações"
    ])
    
    with tab_itrs:
        st.markdown("### ITR - Inspection Test Records", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### ➕ Novo ITR", unsafe_allow_html=True)
            with st.form("form_itr"):
                tipo_itr = st.selectbox("Tipo ITR", ["ITR-A (Calibração)", "ITR-B (Instalação)"], key="itr_tipo")
                obra = st.text_input("Obra", key="itr_obra")
                frente = st.text_input("Frente", key="itr_frente")
                tecnico = st.text_input("Técnico Responsável", key="itr_tec")
                data = st.date_input("Data", key="itr_data")
                
                if st.form_submit_button("💾 Criar ITR", use_container_width=True):
                    st.success(f"✅ {tipo_itr} criado!")
                    st.rerun()
        
        with col2:
            st.markdown("#### 📋 ITRs Existentes", unsafe_allow_html=True)
            st.info("Lista de ITRs por obra...")
        
        st.divider()
        st.markdown("#### ✅ Validação de ITRs", unsafe_allow_html=True)
        st.info("ITRs pendentes de validação pelo cliente...")

    with tab_nao_conf:
        st.markdown("### ⚠️ Não Conformidades", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("#### ➕ Reportar Não Conformidade", unsafe_allow_html=True)
            with st.form("form_nc"):
                obra = st.text_input("Obra", key="nc_obra")
                tipo = st.selectbox("Tipo", ["Produto", "Processo", "Documentação", "Outro"], key="nc_tipo")
                gravidade = st.selectbox("Gravidade", ["Baixa", "Média", "Alta", "Crítica"], key="nc_grav")
                descricao = st.text_area("Descrição", key="nc_desc")
                acao = st.text_area("Ação Corretiva", key="nc_acao")
                
                if st.form_submit_button("💾 Reportar", use_container_width=True):
                    st.success("✅ Não conformidade reportada!")
                    st.rerun()
        
        with col2:
            st.markdown("#### 📋 Não Conformidades Abertas", unsafe_allow_html=True)
            st.info("Lista de NCs por estado...")

    with tab_auditorias:
        st.markdown("### 🔍 Auditorias de Qualidade", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📅 Agendar Auditoria", unsafe_allow_html=True)
            with st.form("form_aud"):
                tipo = st.selectbox("Tipo", ["Interna", "Externa", "Cliente", "Certificadora"], key="aud_tipo")
                data = st.date_input("Data", key="aud_data")
                auditor = st.text_input("Auditor", key="aud_auditor")
                ambito = st.text_area("Âmbito", key="aud_ambito")
                
                if st.form_submit_button("💾 Agendar", use_container_width=True):
                    st.success("✅ Auditoria agendada!")
                    st.rerun()
        
        with col2:
            st.markdown("#### 📋 Auditorias Agendadas", unsafe_allow_html=True)
            st.info("Calendário de auditorias...")

    with tab_certificacoes:
        st.markdown("### 📜 Certificações", unsafe_allow_html=True)
        
        st.info("📋 Gestão de certificações ISO, CE, etc.")
        
        col1, col2, c3 = st.columns(3)
        with col1:
            st.metric("ISO 9001", "✅ Válida")
        with col2:
            st.metric("ISO 14001", "✅ Válida")
        with c3:
            st.metric("ISO 45001", "⚠️ Expira em 6 meses")
        
        st.divider()
        st.markdown("#### 📄 Documentos de Certificação", unsafe_allow_html=True)
        st.info("Upload e gestão de certificados...")

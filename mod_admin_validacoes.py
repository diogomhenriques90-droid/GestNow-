import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

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
                    st.success("✅ Validado!")
            with col2:
                if st.button("🔵 Faturação", use_container_width=True, key="btn_val_fat"):
                    st.success("✅ Pronto para faturação!")
            with col3:
                if st.button("❌ Rejeitar", use_container_width=True, key="btn_val_rej"):
                    st.error("❌ Rejeitado!")

    with tab_epis:
        st.markdown("### 🦺 Validação de EPIs", unsafe_allow_html=True)
        if not req_epi_db.empty:
            st.dataframe(req_epi_db, use_container_width=True)
            if st.button("✅ Validar EPIs", key="btn_val_epi"):
                st.success("✅ EPIs validados!")
        else:
            st.info("📋 Sem pedidos de EPI")

    with tab_ferramentas:
        st.markdown("### 🔧 Validação de Ferramentas", unsafe_allow_html=True)
        if not req_fer_db.empty:
            st.dataframe(req_fer_db, use_container_width=True)
            if st.button("✅ Validar Ferramentas", key="btn_val_fer"):
                st.success("✅ Ferramentas validadas!")
        else:
            st.info("📋 Sem pedidos de ferramentas")

    with tab_materiais:
        st.markdown("### 📦 Validação de Materiais", unsafe_allow_html=True)
        if not req_mat_db.empty:
            st.dataframe(req_mat_db, use_container_width=True)
            if st.button("✅ Validar Materiais", key="btn_val_mat"):
                st.success("✅ Materiais validados!")
        else:
            st.info("📋 Sem pedidos de materiais")

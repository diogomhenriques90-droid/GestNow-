import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

def render_frota():
    """Módulo de Gestão de Frota"""
    
    st.markdown("### 🚗 Gestão de Frota", unsafe_allow_html=True)
    
    tab_viaturas, tab_combustivel, tab_avarias = st.tabs([
        "Viaturas", "Combustível", "Avarias"
    ])
    
    with tab_viaturas:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Nova Viatura", unsafe_allow_html=True)
            with st.form("form_viatura"):
                matricula = st.text_input("Matrícula", key="viat_mat")
                marca = st.text_input("Marca", key="viat_marca")
                modelo = st.text_input("Modelo", key="viat_modelo")
                tipo = st.selectbox("Tipo", ["Própria", "Alugada", "Colaborador"], key="viat_tipo")
                condutor = st.text_input("Condutor", key="viat_cond")
                custo = st.number_input("Custo Mensal (€)", min_value=0.0, value=0.0, key="viat_custo")
                
                if st.form_submit_button("💾 Registar", use_container_width=True):
                    st.success(f"✅ Viatura {matricula} registada!")
                    st.rerun()
        
        with col2:
            st.markdown("### 🚗 Frota Existente", unsafe_allow_html=True)
            st.info("Lista de viaturas...")

    with tab_combustivel:
        st.markdown("### ⛽ Combustível", unsafe_allow_html=True)
        st.info("Registo de abastecimentos...")

    with tab_avarias:
        st.markdown("### ⚠️ Avarias", unsafe_allow_html=True)
        st.info("Registo de avarias e incidentes...")

import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

def render_comercial():
    """Módulo Comercial"""
    
    st.markdown("### 💼 Gestão Comercial", unsafe_allow_html=True)
    
    tab_visitas, tab_clientes, tab_relatorios = st.tabs([
        "Visitas", "Clientes", "Relatórios"
    ])
    
    with tab_visitas:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### 📅 Nova Visita", unsafe_allow_html=True)
            with st.form("form_visita"):
                comercial = st.text_input("Comercial", key="vis_comercial")
                cliente = st.text_input("Cliente", key="vis_cliente")
                tipo = st.selectbox("Tipo", ["Prospeção", "Follow-up", "Técnica"], key="vis_tipo")
                objetivo = st.text_area("Objetivo", key="vis_obj")
                
                if st.form_submit_button("💾 Agendar", use_container_width=True):
                    st.success("✅ Visita agendada!")
                    st.rerun()
        
        with col2:
            st.markdown("### 📋 Próximas Visitas", unsafe_allow_html=True)
            st.info("Calendário de visitas...")

    with tab_clientes:
        st.markdown("### 🏢 Base de Clientes", unsafe_allow_html=True)
        st.info("Gestão de clientes...")

    with tab_relatorios:
        st.markdown("### 📊 Relatórios de Visitas", unsafe_allow_html=True)
        st.info("Relatórios técnicos e comerciais...")

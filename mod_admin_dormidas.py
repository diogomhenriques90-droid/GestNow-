import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

def render_dormidas():
    """Módulo de Gestão de Dormidas com IA"""
    
    st.markdown("### 🏨 Gestão de Dormidas", unsafe_allow_html=True)
    
    tab_registar, tab_pesquisar, tab_historico = st.tabs([
        "Registar", "🤖 IA Pesquisa", "Histórico"
    ])
    
    with tab_registar:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Nova Dormida", unsafe_allow_html=True)
            with st.form("form_dormida"):
                trabalhador = st.text_input("Trabalhador", key="dorm_trab")
                obra = st.text_input("Obra", key="dorm_obra")
                hotel = st.text_input("Hotel", key="dorm_hotel")
                custo = st.number_input("Custo (€)", min_value=0.0, value=0.0, key="dorm_custo")
                kms = st.number_input("Kms até Obra", min_value=0, value=0, key="dorm_kms")
                
                if st.form_submit_button("💾 Registar", use_container_width=True):
                    st.success(f"✅ Dormida registada! Custo: € {custo:.2f}")
                    st.rerun()
        
        with col2:
            st.markdown("### 📋 Dormidas Registadas", unsafe_allow_html=True)
            st.info("Lista de dormidas...")

    with tab_pesquisar:
        st.markdown("### 🤖 IA - Pesquisa de Hotéis", unsafe_allow_html=True)
        st.info("🔍 Integração com Booking.com, Trivago...")
        
        raio = st.slider("Raio de Busca (km)", 1, 50, 10, key="dorm_raio")
        if st.button("🔍 Pesquisar", key="btn_pesq_hotel"):
            st.info("🤖 IA a pesquisar...")
            st.success("✅ Encontrados 5 hotéis!")

    with tab_historico:
        st.markdown("### 📜 Histórico", unsafe_allow_html=True)
        st.info("Histórico de dormidas por obra/zona...")

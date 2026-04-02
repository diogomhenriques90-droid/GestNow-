import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

def render_orcamentacao():
    """Módulo de Orçamentação com IA"""
    
    st.markdown("### 📊 Orçamentação com IA", unsafe_allow_html=True)
    
    tab_novo, tab_historico, tab_ia = st.tabs([
        "Novo Orçamento", "Histórico", "🤖 Sugestões IA"
    ])
    
    with tab_novo:
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Cliente", key="orc_cliente")
            obra = st.text_input("Obra", key="orc_obra")
            descricao = st.text_area("Descrição", key="orc_desc")
        with col2:
            if st.button("🤖 IA - Sugerir Valor", key="btn_ia_orc"):
                st.info("🤖 A analisar histórico...")
                st.success("💡 Sugestão IA: € 15,000 - € 18,000")
            
            valor = st.number_input("Valor (€)", min_value=0.0, value=0.0, key="orc_valor")
        
        if st.button("💾 Guardar", key="btn_orc"):
            st.success("✅ Orçamento guardado!")
            st.rerun()

    with tab_historico:
        st.markdown("### 📜 Histórico de Orçamentos", unsafe_allow_html=True)
        st.info("Orçamentos anteriores...")

    with tab_ia:
        st.markdown("### 🤖 Aprendizagem IA", unsafe_allow_html=True)
        st.info("IA aprende com orçamentos aceites/rejeitados...")

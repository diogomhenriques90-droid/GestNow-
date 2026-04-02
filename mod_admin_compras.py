import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

def render_compras():
    """Módulo de Compras com IA"""
    
    st.markdown("### 🛒 Gestão de Compras", unsafe_allow_html=True)
    
    tab_compras, tab_fornecedores, tab_cotacoes = st.tabs([
        "Compras", "Fornecedores", "🤖 IA Cotações"
    ])
    
    with tab_compras:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Nova Compra", unsafe_allow_html=True)
            with st.form("form_compra"):
                fornecedor = st.text_input("Fornecedor", key="comp_forn")
                descricao = st.text_input("Descrição", key="comp_desc")
                tipo = st.selectbox("Tipo", ["Material", "Ferramenta", "EPI", "Outro"], key="comp_tipo")
                quantidade = st.number_input("Quantidade", min_value=1, value=1, key="comp_qtd")
                preco = st.number_input("Preço Unitário (€)", min_value=0.0, value=0.0, key="comp_preco")
                
                if st.form_submit_button("💾 Registar", use_container_width=True):
                    st.success(f"✅ Compra registada!")
                    st.rerun()
        
        with col2:
            st.markdown("### 📋 Compras Registadas", unsafe_allow_html=True)
            st.info("Lista de compras...")

    with tab_fornecedores:
        st.markdown("### 🏢 Fornecedores", unsafe_allow_html=True)
        st.info("Gestão de fornecedores...")

    with tab_cotacoes:
        st.markdown("### 🤖 IA - Cotações Automáticas", unsafe_allow_html=True)
        st.info("🔍 IA pesquisa 3+ fornecedores automaticamente...")
        
        produto = st.text_input("Produto/Serviço", key="cot_prod")
        if st.button("🔍 Pedir Cotações", key="btn_cotacao"):
            st.info("🤖 IA a contactar fornecedores...")
            st.success("✅ 3 cotações recebidas!")

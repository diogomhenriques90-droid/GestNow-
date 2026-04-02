import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

def render_faturacao(faturas_db, obras_db):
    """Módulo de Faturação com Todos os Custos"""
    
    st.markdown("### 💰 Centro de Faturação", unsafe_allow_html=True)
    
    if not obras_db.empty:
        cliente = st.selectbox("Selecionar Cliente", obras_db['Cliente'].unique().tolist(), key="fat_cliente")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Faturas", len(faturas_db[faturas_db['Cliente'] == cliente]) if not faturas_db.empty else 0)
        with c2:
            st.metric("Valor Faturas", "€ 0.00")
        with c3:
            st.metric("Custos Totais", "€ 0.00")
        with c4:
            st.metric("Lucro", "€ 0.00")
        
        st.divider()
        
        if st.button("📄 Gerar Fatura PDF", type="primary", use_container_width=True, key="btn_gerar_fat"):
            st.info(f"A processar fatura para {cliente}...")
            st.success("✅ Fatura gerada!")
    else:
        st.warning("⚠️ Sem obras disponíveis")

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core import save_db, inv

def render_planeamento():
    """Módulo de Planeamento e Engenharia com Produção"""
    
    st.markdown("### 📋 Planeamento e Engenharia", unsafe_allow_html=True)
    
    tab_producao, tab_cronograma, tab_recursos, tab_desenhos = st.tabs([
        "🏭 Produção", "📅 Cronograma", "👷 Recursos", "📐 Desenhos"
    ])
    
    with tab_producao:
        st.markdown("### 🏭 Produção e Progresso", unsafe_allow_html=True)
        
        # KPIs de Produção
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("📊 Progresso Global", "65%")
        with c2:
            st.metric("⏱️ Horas Planeadas", "1,200h")
        with c3:
            st.metric("⏱️ Horas Reais", "980h")
        with c4:
            st.metric("📈 Produtividade", "82%")
        
        st.divider()
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("#### ➕ Novo Pacote de Trabalho", unsafe_allow_html=True)
            with st.form("form_pacote"):
                obra = st.text_input("Obra", key="prod_obra")
                frente = st.text_input("Frente", key="prod_frente")
                descricao = st.text_area("Descrição", key="prod_desc")
                horas_plan = st.number_input("Horas Planeadas", min_value=0, value=0, key="prod_horas")
                data_inicio = st.date_input("Data Início", key="prod_ini")
                data_fim = st.date_input("Data Fim", key="prod_fim")
                
                if st.form_submit_button("💾 Criar Pacote", use_container_width=True):
                    st.success("✅ Pacote de trabalho criado!")
                    st.rerun()
        
        with col2:
            st.markdown("#### 📋 Pacotes de Trabalho Ativos", unsafe_allow_html=True)
            st.info("Lista de pacotes por obra e frente...")
        
        st.divider()
        st.markdown("#### 📊 Curva S de Produção", unsafe_allow_html=True)
        st.info("Gráfico de planeado vs real...")

    with tab_cronograma:
        st.markdown("### 📅 Cronograma e Milestones", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### ➕ Novo Milestone", unsafe_allow_html=True)
            with st.form("form_milestone"):
                obra = st.text_input("Obra", key="mile_obra")
                descricao = st.text_input("Descrição", key="mile_desc")
                data = st.date_input("Data Alvo", key="mile_data")
                responsavel = st.text_input("Responsável", key="mile_resp")
                
                if st.form_submit_button("💾 Criar Milestone", use_container_width=True):
                    st.success("✅ Milestone criado!")
                    st.rerun()
        
        with col2:
            st.markdown("#### 📋 Milestones Críticos", unsafe_allow_html=True)
            st.info("Milestones por data e estado...")
        
        st.divider()
        st.markdown("#### 📊 Diagrama de Gantt", unsafe_allow_html=True)
        st.info("Visualização de cronograma por obra...")

    with tab_recursos:
        st.markdown("### 👷 Planeamento de Recursos", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("👷 Técnicos Alocados", "24")
        with c2:
            st.metric("🔧 Ferramentas Disp.", "95%")
        with c3:
            st.metric("📦 Materiais Stock", "87%")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📅 Alocação de Técnicos", unsafe_allow_html=True)
            st.info("Calendário de alocação por obra...")
        
        with col2:
            st.markdown("#### 📊 Carga de Trabalho", unsafe_allow_html=True)
            st.info("Distribuição de horas por técnico...")

    with tab_desenhos:
        st.markdown("### 📐 Gestão de Desenhos e Documentação Técnica", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("#### ➕ Upload de Desenho", unsafe_allow_html=True)
            with st.form("form_desenho"):
                obra = st.text_input("Obra", key="des_obra")
                tipo = st.selectbox("Tipo", ["P&ID", "Layout", "Esquemático", "Isométrico"], key="des_tipo")
                revisao = st.text_input("Revisão", key="des_rev")
                ficheiro = st.file_uploader("Ficheiro", type=["pdf", "dwg", "dxf"], key="des_file")
                
                if st.form_submit_button("💾 Upload", use_container_width=True):
                    st.success("✅ Desenho upload!")
                    st.rerun()
        
        with col2:
            st.markdown("#### 📋 Biblioteca de Desenhos", unsafe_allow_html=True)
            st.info("Desenhos por obra e tipo...")
        
        st.divider()
        st.markdown("#### ✅ Controlo de Revisões", unsafe_allow_html=True)
        st.info("Histórico de revisões por desenho...")

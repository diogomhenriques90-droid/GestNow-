import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv

def render_obras(obras_db, frentes_db, users, inst_acessos_db):
    """Módulo de Gestão de Obras"""
    
    st.markdown("### 🏗️ Gestão de Obras", unsafe_allow_html=True)
    
    tab_obras, tab_alocacoes, tab_historico = st.tabs([
        "Obras", "Alocações", "Histórico"
    ])
    
    with tab_obras:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Nova Obra", unsafe_allow_html=True)
            with st.form("form_nova_obra"):
                nome = st.text_input("Nome da Obra", key="obra_nome")
                cliente = st.text_input("Cliente", key="obra_cliente")
                tipo = st.selectbox("Tipo", ["Normal", "Instrumentação", "Manutenção"], key="obra_tipo")
                local = st.text_input("Localização", key="obra_local")
                
                if st.form_submit_button("💾 Criar Obra", use_container_width=True):
                    new_obra = pd.DataFrame([{
                        "Obra": nome, "Cliente": cliente, "TipoObra": tipo,
                        "Local": local, "Ativa": "Ativa",
                        "DataInicio": datetime.now().strftime("%d/%m/%Y")
                    }])
                    obras_db = pd.concat([obras_db, new_obra], ignore_index=True)
                    save_db(obras_db, "obras_lista.csv")
                    inv()
                    st.success(f"✅ Obra '{nome}' criada!")
                    st.rerun()
        
        with col2:
            st.markdown("### 🏭 Obras Existentes", unsafe_allow_html=True)
            if not obras_db.empty:
                st.dataframe(obras_db[['Obra', 'Cliente', 'TipoObra', 'Ativa', 'Local']], use_container_width=True)

    with tab_alocacoes:
        st.markdown("### 👷 Alocação de Pessoal", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            obra = st.selectbox("Obra", obras_db['Obra'].unique().tolist() if not obras_db.empty else [], key="aloc_obra")
            tecnico = st.selectbox("Técnico", users['Nome'].tolist() if not users.empty else [], key="aloc_tec")
        with col2:
            preco_hora = st.number_input("Preço Hora na Obra (€)", min_value=0.0, value=15.0, key="aloc_preco")
        
        if st.button("➕ Alocar", key="btn_alocar"):
            new_aloc = pd.DataFrame([{
                "Obra": obra, "Utilizador": tecnico,
                "Cargo": users[users['Nome'] == tecnico]['Cargo'].values[0] if not users.empty else "",
                "Ativo": "Sim"
            }])
            inst_acessos_db = pd.concat([inst_acessos_db, new_aloc], ignore_index=True)
            save_db(inst_acessos_db, "inst_acessos.csv")
            inv()
            st.success(f"✅ {tecnico} alocado à obra {obra}!")
            st.rerun()

    with tab_historico:
        st.markdown("### 📜 Histórico de Obras", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, hp

def render_rh(users, avals_db, obras_db, inst_acessos_db):
    """Módulo de Recursos Humanos"""
    
    st.markdown("### 👥 Gestão de Recursos Humanos", unsafe_allow_html=True)
    
    tab_pessoal, tab_avaliacoes, tab_historico, tab_acessos = st.tabs([
        "Gestão de Pessoal", "Avaliações", "Histórico", "Acessos"
    ])
    
    with tab_pessoal:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Novo Colaborador", unsafe_allow_html=True)
            with st.form("form_novo_colab"):
                nome = st.text_input("Nome Completo", key="rh_nome")
                email = st.text_input("Email", key="rh_email")
                telefone = st.text_input("Telefone", key="rh_tel")
                tipo = st.selectbox("Tipo", ["Técnico", "Chefe de Equipa", "Admin", "Comercial"], key="rh_tipo")
                cargo = st.selectbox("Cargo", ["Instrumentista", "Técnico de Campo", "Chefe de Equipa", "Engenheiro"], key="rh_cargo")
                nif = st.text_input("NIF", key="rh_nif")
                morada = st.text_input("Morada", key="rh_morada")
                local = st.checkbox("É Local? (Não precisa dormida)", key="rh_local")
                preco_hora = st.number_input("Preço Hora (€)", min_value=0.0, value=15.0, key="rh_preco")
                password = st.text_input("Password", type="password", value="gestnow123", key="rh_pass")
                
                if st.form_submit_button("💾 Criar", use_container_width=True):
                    new_user = pd.DataFrame([{
                        "Nome": nome, "Password": hp(password), "Tipo": tipo, "Cargo": cargo,
                        "Email": email, "Telefone": telefone, "NIF": nif, "Morada": morada,
                        "Local": "Sim" if local else "Não", "PrecoHora": str(preco_hora),
                        "NISS": "", "CC": "", "DataNasc": "", "Nacionalidade": "Portugal",
                        "Foto": "", "PrecoHoraStatus": "", "PrecoHoraData": "", "PIN": "0000"
                    }])
                    users = pd.concat([users, new_user], ignore_index=True)
                    save_db(users, "usuarios.csv")
                    inv()
                    st.success(f"✅ {nome} criado!")
                    st.rerun()
        
        with col2:
            st.markdown("### 👥 Lista de Colaboradores", unsafe_allow_html=True)
            if not users.empty:
                # Verificar quais colunas existem
cols_disponiveis = [col for col in ['Nome', 'Tipo', 'Cargo', 'Email', 'Telefone', 'Local', 'PrecoHora'] if col in users.columns]
st.dataframe(users[cols_disponiveis], use_container_width=True)
    with tab_avaliacoes:
        st.markdown("### 📊 Avaliações de Desempenho", unsafe_allow_html=True)
        if not users.empty:
            trabalhador = st.selectbox("Trabalhador", users['Nome'].tolist(), key="avalia_trab")
            
            col1, col2 = st.columns(2)
            with col1:
                nota_tecnica = st.slider("Competência Técnica", 1, 10, 5, key="nota_tec")
                nota_pontualidade = st.slider("Pontualidade", 1, 10, 5, key="nota_pont")
                nota_equipa = st.slider("Trabalho em Equipa", 1, 10, 5, key="nota_eq")
            with col2:
                nota_proatividade = st.slider("Proatividade", 1, 10, 5, key="nota_proat")
                nota_comunicacao = st.slider("Comunicação", 1, 10, 5, key="nota_com")
                comentarios = st.text_area("Comentários", key="avalia_coment")
            
            if st.button("💾 Guardar Avaliação", key="btn_avalia"):
                media = (nota_tecnica + nota_pontualidade + nota_equipa + nota_proatividade + nota_comunicacao) / 5
                nova_avalia = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"), "Trabalhador": trabalhador,
                    "Nota_Tecnica": nota_tecnica, "Nota_Pontualidade": nota_pontualidade,
                    "Nota_Trabalho_Eq": nota_equipa, "Nota_Proatividade": nota_proatividade,
                    "Nota_Comunicacao": nota_comunicacao, "Media": media, "Comentarios": comentarios
                }])
                avals_db = pd.concat([avals_db, nova_avalia], ignore_index=True)
                save_db(avals_db, "avaliacoes.csv")
                inv()
                st.success("✅ Avaliação guardada!")
                st.rerun()

    with tab_historico:
        st.markdown("### 📜 Histórico", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    with tab_acessos:
        st.markdown("### 🔐 Acessos a Obras", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

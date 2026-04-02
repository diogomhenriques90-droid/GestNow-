import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, hp

def render_rh(users, avals_db, obras_db, inst_acessos_db):
    """Módulo de Recursos Humanos - Versão Corrigida"""
    
    # ✅ CORRIGIR: Adicionar colunas em falta se não existirem
    if 'Local' not in users.columns:
        users['Local'] = "Não"
    if 'PrecoHora' not in users.columns:
        users['PrecoHora'] = "15.0"
    if 'Morada' not in users.columns:
        users['Morada'] = ""
    
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
                morada = st.text_input("Morada Completa", key="rh_morada")
                local = st.checkbox("É Local? (Não precisa dormida)", key="rh_local")
                preco_hora = st.number_input("Preço Hora (€)", min_value=0.0, value=15.0, key="rh_preco")
                password = st.text_input("Password", type="password", value="gestnow123", key="rh_pass")
                
                if st.form_submit_button("💾 Criar Colaborador", use_container_width=True):
                    new_user = pd.DataFrame([{
                        "Nome": nome,
                        "Password": hp(password),
                        "Tipo": tipo,
                        "Cargo": cargo,
                        "Email": email,
                        "Telefone": telefone,
                        "NIF": nif,
                        "Morada": morada,
                        "Local": "Sim" if local else "Não",
                        "PrecoHora": str(preco_hora),
                        "NISS": "",
                        "CC": "",
                        "DataNasc": "",
                        "Nacionalidade": "Portugal",
                        "Foto": "",
                        "PrecoHoraStatus": "",
                        "PrecoHoraData": "",
                        "PIN": "0000"
                    }])
                    users = pd.concat([users, new_user], ignore_index=True)
                    save_db(users, "usuarios.csv")
                    inv()
                    st.success(f"✅ {nome} criado!")
                    st.rerun()
        
        with col2:
            st.markdown("### 👥 Lista de Colaboradores", unsafe_allow_html=True)
            if not users.empty:
                # ✅ CORRIGIR: Mostrar apenas colunas que existem
                cols_para_mostrar = []
                for col in ['Nome', 'Tipo', 'Cargo', 'Email', 'Telefone', 'Local', 'PrecoHora']:
                    if col in users.columns:
                        cols_para_mostrar.append(col)
                
                st.dataframe(users[cols_para_mostrar], use_container_width=True)
                
                st.divider()
                st.markdown("### Gestão de Colaboradores", unsafe_allow_html=True)
                
                for idx, user in users.iterrows():
                    with st.expander(f"👤 {user['Nome']} - {user['Cargo']}", key=f"exp_{idx}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Email:** {user.get('Email', 'N/A')}")
                            st.write(f"**Telefone:** {user.get('Telefone', 'N/A')}")
                            st.write(f"**NIF:** {user.get('NIF', 'N/A')}")
                            st.write(f"**Morada:** {user.get('Morada', 'N/A')}")
                            st.write(f"**Local:** {user.get('Local', 'Não')}")
                        with c2:
                            st.write(f"**Tipo:** {user.get('Tipo', 'N/A')}")
                            st.write(f"**Cargo:** {user.get('Cargo', 'N/A')}")
                            st.write(f"**Preço Hora:** € {user.get('PrecoHora', '15.0')}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✏️ Editar", key=f"edit_{idx}"):
                                st.info("Editar funcionalidade")
                        with col2:
                            if st.button("📊 Avaliar", key=f"eval_{idx}"):
                                st.info("Avaliação funcionalidade")
                        with col3:
                            if st.button("🗑️ Dispensar", key=f"del_{idx}", type="secondary"):
                                if st.session_state.user != user['Nome']:
                                    users = users.drop(idx)
                                    save_db(users, "usuarios.csv")
                                    inv()
                                    st.success("✅ Trabalhador dispensado!")
                                    st.rerun()
                                else:
                                    st.error("❌ Não pode eliminar o seu próprio utilizador!")

    with tab_avaliacoes:
        st.markdown("### 📊 Avaliações de Desempenho", unsafe_allow_html=True)
        
        if not users.empty:
            trabalhador_sel = st.selectbox("Selecionar Trabalhador", users['Nome'].tolist(), key="avalia_trab")
            
            col1, col2 = st.columns(2)
            with col1:
                nota_tecnica = st.slider("Competência Técnica", 1, 10, 5, key="nota_tec")
                nota_pontualidade = st.slider("Pontualidade", 1, 10, 5, key="nota_pont")
                nota_trabalho_eq = st.slider("Trabalho em Equipa", 1, 10, 5, key="nota_eq")
            
            with col2:
                nota_proatividade = st.slider("Proatividade", 1, 10, 5, key="nota_proat")
                nota_comunicacao = st.slider("Comunicação", 1, 10, 5, key="nota_com")
                comentarios = st.text_area("Comentários", key="avalia_coment")
            
            if st.button("💾 Guardar Avaliação", key="btn_avalia"):
                media = (nota_tecnica + nota_pontualidade + nota_trabalho_eq + nota_proatividade + nota_comunicacao) / 5
                nova_avalia = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Trabalhador": trabalhador_sel,
                    "Nota_Tecnica": nota_tecnica,
                    "Nota_Pontualidade": nota_pontualidade,
                    "Nota_Trabalho_Eq": nota_trabalho_eq,
                    "Nota_Proatividade": nota_proatividade,
                    "Nota_Comunicacao": nota_comunicacao,
                    "Media": media,
                    "Comentarios": comentarios
                }])
                avals_db = pd.concat([avals_db, nova_avalia], ignore_index=True)
                save_db(avals_db, "avaliacoes.csv")
                inv()
                st.success("✅ Avaliação guardada!")
                st.rerun()
            
            # Histórico de avaliações
            if not avals_db.empty:
                st.divider()
                st.markdown("### Histórico de Avaliações", unsafe_allow_html=True)
                aval_trab = avals_db[avals_db['Trabalhador'] == trabalhador_sel]
                if not aval_trab.empty:
                    st.dataframe(aval_trab, use_container_width=True)

    with tab_historico:
        st.markdown("### 📜 Histórico de Trabalhadores", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    with tab_acessos:
        st.markdown("### 🔐 Acessos a Obras", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

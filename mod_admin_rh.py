import streamlit as st
import pandas as pd
import json
from datetime import datetime
from core import save_db, inv, hp, cp, log_audit, criar_notificacao

def render_rh(users, avals_db, obras_db, inst_acessos_db):
    """Módulo de Recursos Humanos - Gestão de Colaboradores com campos bloqueáveis e PDFs"""
    
    # Garantir colunas obrigatórias
    cols_obrigatorias = {
        'Local': 'Não',
        'PrecoHora': '15.0',
        'Morada': '',
        'NIF': '',
        'Telefone': '',
        'Email': '',
        'Cargo': 'Técnico',
        'Tipo': 'Técnico',
        'Password': '',
        'NISS': '',
        'CC': '',
        'DataNasc': '',
        'Nacionalidade': 'Portugal',
        'Foto': '',
        'PrecoHoraStatus': '',  # '', 'Aceite', 'Recusado'
        'PrecoHoraData': '',
        'PIN': '0000',
        # Novos campos de tamanhos EPI
        'Tamanho_Capacete': '',
        'Tamanho_Camisola': '',
        'Tamanho_Casaco': '',
        'Tamanho_Calças': '',
        'Tamanho_Botas': '',
        'Tamanho_Luvas': '',
        # Campos bloqueáveis (JSON string)
        'Campos_Bloqueados': '[]',
        # PDFs obrigatórios
        'PDFs_Vistos': '[]',  # JSON: lista de PDFs vistos
        'PDFs_Validados': 'Não',  # 'Sim' ou 'Não'
        'PDFs_Validacao_Data': ''
    }
    
    for col, valor_padrao in cols_obrigatorias.items():
        if col not in users.columns:
            users[col] = valor_padrao
    
    # Garantir avals_db
    if avals_db.empty:
        avals_db = pd.DataFrame(columns=[
            'Data', 'Trabalhador', 'Nota_Tecnica', 'Nota_Pontualidade',
            'Nota_Trabalho_Eq', 'Nota_Proatividade', 'Nota_Comunicacao',
            'Media', 'Comentarios'
        ])
    
    st.markdown("### 👥 Gestão de Recursos Humanos", unsafe_allow_html=True)
    
    tab_pessoal, tab_avaliacoes, tab_historico, tab_config = st.tabs([
        "Gestão de Pessoal", "Avaliações", "Histórico", "⚙️ Configurações"
    ])
    
    with tab_pessoal:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Novo Colaborador", unsafe_allow_html=True)
            with st.form("form_novo_colab"):
                nome = st.text_input("Nome Completo", key="rh_nome")
                email = st.text_input("Email", key="rh_email")
                telefone = st.text_input("Telefone", key="rh_tel")
                tipo = st.selectbox("Tipo", ["Técnico", "Chefe de Equipa", "Admin", "Comercial", "Cliente"], key="rh_tipo")
                cargo = st.selectbox("Cargo", ["Instrumentista", "Técnico de Campo", "Chefe de Equipa", "Engenheiro", "Gestor de Projeto"], key="rh_cargo")
                nif = st.text_input("NIF", key="rh_nif")
                morada = st.text_input("Morada Completa", key="rh_morada")
                local = st.checkbox("É Local? (Não precisa dormida)", key="rh_local")
                preco_hora = st.number_input("Preço Hora (€)", min_value=0.0, value=15.0, key="rh_preco")
                password = st.text_input("Password Inicial", type="password", value="gestnow123", key="rh_pass")
                
                if st.form_submit_button("💾 Criar Colaborador", use_container_width=True):
                    if nome and password:
                        if nome in users['Nome'].values:
                            st.error(f"❌ Já existe um colaborador com o nome '{nome}'!")
                        else:
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
                                "PIN": "0000",
                                "Tamanho_Capacete": "",
                                "Tamanho_Camisola": "",
                                "Tamanho_Casaco": "",
                                "Tamanho_Calças": "",
                                "Tamanho_Botas": "",
                                "Tamanho_Luvas": "",
                                "Campos_Bloqueados": json.dumps([]),
                                "PDFs_Vistos": json.dumps([]),
                                "PDFs_Validados": "Não",
                                "PDFs_Validacao_Data": ""
                            }])
                            users = pd.concat([users, new_user], ignore_index=True)
                            save_db(users, "usuarios.csv")
                            
                            log_audit(usuario=st.session_state.user, acao="CRIAR_COLABORADOR", tabela="usuarios.csv", registro_id=nome, detalhes=f"Novo colaborador criado: {nome} ({tipo}, {cargo})", ip="")
                            
                            inv()
                            st.success(f"✅ {nome} criado com sucesso!")
                            st.info(f"🔑 Password inicial: `{password}` (o utilizador deve alterar no primeiro login)")
                            st.rerun()
                    else:
                        st.error("❌ Nome e password são obrigatórios!")
        
        with col2:
            st.markdown("### 👥 Lista de Colaboradores", unsafe_allow_html=True)
            if not users.empty:
                cols_visiveis = [col for col in ['Nome', 'Tipo', 'Cargo', 'Email', 'Telefone', 'Local', 'PrecoHora'] if col in users.columns]
                st.dataframe(users[cols_visiveis], use_container_width=True)
                
                st.divider()
                st.markdown("### Gestão Individual", unsafe_allow_html=True)
                
                for idx, user in users.iterrows():
                    nome_user = user.get('Nome', f'Utilizador_{idx}')
                    with st.expander(f"👤 {nome_user} - {user.get('Cargo', 'N/A')}", key=f"exp_{idx}"):
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
                        
                        # Status do Preço Hora
                        preco_status = user.get('PrecoHoraStatus', '')
                        if preco_status == 'Aceite':
                            st.success(f"✅ Preço Hora ACEITE em {user.get('PrecoHoraData', 'N/A')}")
                        elif preco_status == 'Recusado':
                            st.error(f"❌ Preço Hora RECUSADO em {user.get('PrecoHoraData', 'N/A')}")
                        else:
                            st.warning(f"⏳ Preço Hora AGUARDANDO validação")
                        
                        # Status dos PDFs
                        pdfs_validados = user.get('PDFs_Validados', 'Não')
                        if pdfs_validados == 'Sim':
                            st.success(f"✅ PDFs validados em {user.get('PDFs_Validacao_Data', 'N/A')}")
                        else:
                            st.warning("⏳ PDFs AGUARDANDO visualização")
                        
                        # Gestão de Password (Admin)
                        if st.session_state.get('tipo') == 'Admin':
                            st.divider()
                            st.markdown("**🔐 Gestão de Password (Admin)**", unsafe_allow_html=True)
                            
                            col_pwd1, col_pwd2 = st.columns(2)
                            with col_pwd1:
                                st.info("⚠️ Por segurança, a password não é visível (está encriptada)")
                            with col_pwd2:
                                nova_password = st.text_input("Nova password", type="password", key=f"new_pwd_{idx}")
                                if st.button("🔄 Resetar Password", key=f"btn_reset_{idx}"):
                                    if nova_password:
                                        users.loc[idx, 'Password'] = hp(nova_password)
                                        save_db(users, "usuarios.csv")
                                        st.success(f"✅ Password de {nome_user} atualizada!")
                                        inv()
                                        st.rerun()
                        
                        # Configuração de campos bloqueáveis (Admin)
                        if st.session_state.get('tipo') == 'Admin':
                            st.divider()
                            st.markdown("**🔒 Campos Bloqueáveis**", unsafe_allow_html=True)
                            st.caption("Desmarca para permitir que o colaborador edite este campo")
                            
                            # Carregar campos bloqueados atuais
                            try:
                                campos_bloqueados = json.loads(user.get('Campos_Bloqueados', '[]'))
                            except:
                                campos_bloqueados = []
                            
                            campos_editaveis = ['Email', 'Telefone', 'Morada', 'NIF', 'NISS', 'CC', 'DataNasc', 'Nacionalidade',
                                              'Tamanho_Capacete', 'Tamanho_Camisola', 'Tamanho_Casaco', 'Tamanho_Calças', 'Tamanho_Botas', 'Tamanho_Luvas']
                            
                            novos_bloqueados = []
                            for campo in campos_editaveis:
                                bloqueado = campo in campos_bloqueados
                                if st.checkbox(f"🔒 {campo}", value=bloqueado, key=f"lock_{idx}_{campo}"):
                                    novos_bloqueados.append(campo)
                            
                            if st.button("💾 Guardar Configuração de Campos", key=f"save_locks_{idx}"):
                                users.loc[idx, 'Campos_Bloqueados'] = json.dumps(novos_bloqueados)
                                save_db(users, "usuarios.csv")
                                st.success(f"✅ Configuração guardada para {nome_user}!")
                                inv()
                                st.rerun()
                        
                        # Ações
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✏️ Editar", key=f"edit_{idx}"):
                                st.info("Funcionalidade em desenvolvimento")
                        with col2:
                            if st.button("📊 Avaliar", key=f"eval_{idx}"):
                                st.session_state['avaliar_user'] = nome_user
                                st.rerun()
                        with col3:
                            if st.button("🗑️ Dispensar", key=f"del_{idx}", type="secondary"):
                                if st.session_state.get('user') != nome_user:
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
            
            aval_trab = avals_db[avals_db['Trabalhador'] == trabalhador_sel] if 'Trabalhador' in avals_db.columns else pd.DataFrame()
            
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
                    "Media": round(media, 2),
                    "Comentarios": comentarios
                }])
                avals_db = pd.concat([avals_db, nova_avalia], ignore_index=True)
                save_db(avals_db, "avaliacoes.csv")
                inv()
                st.success("✅ Avaliação guardada!")
                st.rerun()
            
            if not aval_trab.empty:
                st.divider()
                st.markdown("### Histórico de Avaliações", unsafe_allow_html=True)
                st.dataframe(aval_trab, use_container_width=True)
        
        elif users.empty:
            st.warning("⚠️ Não existem utilizadores para avaliar.")
        else:
            st.info("📋 Sem avaliações registadas.")

    with tab_historico:
        st.markdown("### 📜 Histórico de Trabalhadores", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    with tab_config:
        st.markdown("### ⚙️ Configurações de PDFs Obrigatórios", unsafe_allow_html=True)
        
        st.info("""
        **PDFs que os colaboradores devem visualizar:**
        
        1. 📋 Regulamento Interno
        2. 🛡️ Política de Segurança e HSE
        3. 📊 Procedimentos de Qualidade
        
        Os colaboradores só podem usar a app após validar a visualização de todos os PDFs.
        """)
        
        # Lista de PDFs (URLs ou caminhos)
        pdfs_obrigatorios = [
            {"nome": "Regulamento Interno", "url": "https://exemplo.com/regulamento.pdf"},
            {"nome": "Política de Segurança e HSE", "url": "https://exemplo.com/hse.pdf"},
            {"nome": "Procedimentos de Qualidade", "url": "https://exemplo.com/qualidade.pdf"}
        ]
        
        st.markdown("#### 📋 Lista de PDFs Configurados")
        for i, pdf in enumerate(pdfs_obrigatorios):
            st.markdown(f"**{i+1}. {pdf['nome']}**")
            st.code(pdf['url'], language="text")
        
        st.warning("⚠️ Para alterar os PDFs, edite a lista `pdfs_obrigatorios` no código.")

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from core import save_db, inv, hp, cp, log_audit, criar_notificacao
import base64
import os

def render_rh(users, avals_db, obras_db, inst_acessos_db):
    """Módulo de Recursos Humanos - Gestão de Colaboradores com campos bloqueáveis e PDFs uploadáveis"""
    
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
        'PDFs_Vistos': '[]',  # JSON: lista de IDs de PDFs vistos
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
    
    tab_pessoal, tab_avaliacoes, tab_historico, tab_pdfs = st.tabs([
        "Gestão de Pessoal", "Avaliações", "Histórico", "📄 PDFs Obrigatórios"
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

    # ========== TAB PDFs OBRIGATÓRIOS (NOVA) ==========
    with tab_pdfs:
        st.markdown("### 📄 Gestão de PDFs Obrigatórios", unsafe_allow_html=True)
        
        st.info("""
        **Instruções:**
        1. Faz upload dos PDFs obrigatórios (máximo 3)
        2. Os colaboradores visualizarão estes PDFs no seu perfil
        3. Devem validar a visualização de TODOS os PDFs
        4. Receberás notificação quando validarem
        """)
        
        # Carregar PDFs existentes do GCS ou base de dados
        try:
            # Tentar carregar de CSV primeiro (mais simples)
            pdfs_db = load_db("pdfs_obrigatorios.csv", [
                "ID", "Nome", "Descricao", "Data_Upload", "Upload_Por", "Ficheiro_b64"
            ])
        except:
            pdfs_db = pd.DataFrame(columns=[
                "ID", "Nome", "Descricao", "Data_Upload", "Upload_Por", "Ficheiro_b64"
            ])
        
        st.markdown("#### 📋 PDFs Atuais")
        
        if not pdfs_db.empty and len(pdfs_db) > 0:
            for idx, pdf in pdfs_db.iterrows():
                with st.expander(f"📄 {pdf.get('Nome', 'PDF')} - Carregado em {pdf.get('Data_Upload', 'N/A')}", expanded=True):
                    st.write(f"**Descrição:** {pdf.get('Descricao', 'N/A')}")
                    st.write(f"**Upload por:** {pdf.get('Upload_Por', 'N/A')}")
                    
                    # Botão para visualizar/download
                    if pdf.get('Ficheiro_b64'):
                        try:
                            pdf_data = base64.b64decode(pdf['Ficheiro_b64'])
                            st.download_button(
                                label="📥 Descarregar PDF",
                                data=pdf_data,
                                file_name=f"{pdf.get('Nome', 'documento')}.pdf",
                                mime="application/pdf",
                                key=f"download_pdf_{idx}"
                            )
                        except:
                            st.error("❌ Erro ao descarregar PDF")
                    
                    # Botão para eliminar
                    if st.button("🗑️ Eliminar PDF", key=f"delete_pdf_{idx}", type="secondary"):
                        pdfs_db = pdfs_db.drop(idx)
                        save_db(pdfs_db, "pdfs_obrigatorios.csv")
                        st.success("✅ PDF eliminado!")
                        inv()
                        st.rerun()
        else:
            st.warning("📋 Nenhum PDF obrigatório carregado ainda.")
        
        st.divider()
        
        # Upload de novos PDFs
        st.markdown("#### ➕ Upload de Novo PDF Obrigatório")
        
        if len(pdfs_db) >= 3:
            st.warning("⚠️ Limite máximo de 3 PDFs atingido. Elimina um PDF existente antes de adicionar outro.")
        else:
            with st.form("form_upload_pdf"):
                col1, col2 = st.columns(2)
                with col1:
                    nome_pdf = st.text_input("Nome do Documento", placeholder="Ex: Regulamento Interno")
                    descricao_pdf = st.text_area("Descrição", placeholder="Ex: Regulamento interno da empresa")
                with col2:
                    ficheiro_pdf = st.file_uploader("📄 Ficheiro PDF", type=["pdf"])
                
                if st.form_submit_button("📤 Upload de PDF", use_container_width=True, type="primary"):
                    if nome_pdf and ficheiro_pdf:
                        # Ler ficheiro PDF
                        pdf_bytes = ficheiro_pdf.read()
                        pdf_b64 = base64.b64encode(pdf_bytes).decode()
                        
                        # Criar novo registo
                        import uuid
                        novo_pdf = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Nome": nome_pdf,
                            "Descricao": descricao_pdf,
                            "Data_Upload": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Upload_Por": st.session_state.user,
                            "Ficheiro_b64": pdf_b64
                        }])
                        
                        if not pdfs_db.empty:
                            pdfs_db = pd.concat([pdfs_db, novo_pdf], ignore_index=True)
                        else:
                            pdfs_db = novo_pdf
                        
                        save_db(pdfs_db, "pdfs_obrigatorios.csv")
                        
                        log_audit(usuario=st.session_state.user, acao="UPLOAD_PDF_OBRIGATORIO", tabela="pdfs_obrigatorios.csv", registro_id=novo_pdf['ID'].iloc[0], detalhes=f"PDF carregado: {nome_pdf}", ip="")
                        
                        st.success(f"✅ PDF '{nome_pdf}' carregado com sucesso!")
                        inv()
                        st.rerun()
                    else:
                        st.warning("⚠️ Por favor, preenche o nome e faz upload do PDF.")

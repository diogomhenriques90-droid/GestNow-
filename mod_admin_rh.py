import streamlit as st
import pandas as pd
import json
from datetime import datetime
from core import save_db, inv, hp, cp, log_audit, criar_notificacao, load_db
import base64
import os
import uuid

def render_rh(users, avals_db, obras_db, inst_acessos_db):
    """Módulo de Recursos Humanos - Gestão Completa de Colaboradores"""
    
    # Garantir TODAS as colunas necessárias
    cols_obrigatorias = {
        # Dados básicos
        'Nome': '',
        'Password': '',
        'Tipo': 'Técnico',
        'Cargo': 'Técnico',
        'Email': '',
        'Telefone': '',
        'Morada': '',
        'Localidade': '',
        'Concelho': '',
        'Codigo_Postal': '',
        'Naturalidade': '',
        'Nacionalidade': 'Portugal',
        'NIF': '',
        'NISS': '',
        'CC': '',
        'CC_Validade': '',
        'DataNasc': '',
        'Estado_Civil': '',
        'Sexo': '',
        'Dependentes': '0',
        'Profissao': '',
        'Categoria_Profissional': '',
        'Habilitacoes_Literarias': '',
        'Contacto_Emergencia': '',
        'Nome_Emergencia': '',
        'Grau_Parentesco': '',
        'Banco_IBAN': '',
        'Observacoes': '',
        # Fardamento
        'Tamanho_Camisola': '',
        'Tamanho_Calca': '',
        'Tamanho_Botas': '',
        # Outros
        'Local': 'Não',
        'PrecoHora': '15.0',
        'PrecoHoraStatus': '',
        'PrecoHoraData': '',
        'PIN': '0000',
        'Foto': '',
        'Campos_Bloqueados': '[]',
        'PDFs_Vistos': '[]',
        'PDFs_Validados': 'Não',
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
    
    st.markdown("""
    <style>
    .section-title {
        background: linear-gradient(135deg, #3B82F6, #1E40AF);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 30px 0 20px 0;
        font-size: 1.3rem;
        font-weight: bold;
    }
    .subsection-title {
        background: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3B82F6;
        padding: 10px 15px;
        margin: 20px 0 15px 0;
        font-size: 1.1rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 👥 Gestão de Recursos Humanos", unsafe_allow_html=True)
    
    tab_pessoal, tab_avaliacoes, tab_historico, tab_pdfs = st.tabs([
        "Gestão de Pessoal", "Avaliações", "Histórico", "📄 PDFs Obrigatórios"
    ])
    
    with tab_pessoal:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown('<div class="section-title">➕ Novo Colaborador</div>', unsafe_allow_html=True)
            with st.form("form_novo_colab"):
                st.markdown("#### 📋 Identificação do Colaborador")
                nome = st.text_input("Nome Completo *", key="rh_nome")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    telefone = st.text_input("Contacto Telefónico *", key="rh_tel")
                    email = st.text_input("Email", key="rh_email")
                with col_b:
                    contacto_emerg = st.text_input("Contacto Emergência", key="rh_emerg_tel")
                    nome_emerg = st.text_input("Nome Emergência", key="rh_emerg_nome")
                    grau_parentesco = st.text_input("Grau Parentesco", key="rh_emerg_grau")
                
                st.markdown("#### 📍 Morada")
                morada = st.text_input("Morada", key="rh_morada")
                col_c, col_d, col_e = st.columns(3)
                with col_c:
                    localidade = st.text_input("Localidade", key="rh_localidade")
                with col_d:
                    concelho = st.text_input("Concelho", key="rh_concelho")
                with col_e:
                    cod_postal = st.text_input("Código Postal", key="rh_cp")
                
                st.markdown("#### 🌍 Dados Pessoais")
                col_f, col_g = st.columns(2)
                with col_f:
                    naturalidade = st.text_input("Naturalidade", key="rh_naturalidade")
                    data_nasc = st.date_input("Data de Nascimento", key="rh_datanasc", min_value=datetime(1950,1,1), max_value=datetime.now())
                with col_g:
                    nacionalidade = st.text_input("Nacionalidade", value="Portugal", key="rh_nacionalidade")
                    estado_civil = st.selectbox("Estado Civil", ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União de Facto"], key="rh_ec")
                
                sexo = st.radio("Sexo", ["Masculino", "Feminino"], horizontal=True, key="rh_sexo")
                
                st.markdown("#### 🆔 Documentos")
                col_h, col_i = st.columns(2)
                with col_h:
                    nif = st.text_input("Nº Contribuinte (NIF) *", key="rh_nif")
                    cc = st.text_input("Cartão Cidadão", key="rh_cc")
                    niss = st.text_input("Nº Segurança Social (NISS)", key="rh_niss")
                with col_i:
                    cc_validade = st.date_input("Validade CC", key="rh_cc_val", min_value=datetime.now())
                    dependentes = st.number_input("Dependentes", min_value=0, value=0, key="rh_dep")
                
                st.markdown("#### 💼 Dados Profissionais")
                profissao = st.text_input("Profissão", key="rh_prof")
                categoria = st.text_input("Categoria Profissional", key="rh_cat")
                habilitacoes = st.selectbox("Habilitações Literárias", [
                    "4º Ano", "6º Ano", "9º Ano", "12º Ano",
                    "Curso Técnico", "Licenciatura", "Mestrado", "Doutoramento"
                ], key="rh_hab")
                
                st.markdown("#### 💰 Dados Bancários")
                iban = st.text_input("IBAN", key="rh_iban", placeholder="PT50 0000 0000 0000 00000 0000")
                
                st.markdown("#### 👕 Tamanhos de Fardamento")
                col_j, col_k, col_l = st.columns(3)
                with col_j:
                    tam_camisola = st.selectbox("Camisola/T-shirt", 
                        ["XS", "S", "M", "L", "XL", "XXL", "XXXL"], key="rh_tam_cam")
                with col_k:
                    tam_calca = st.selectbox("Calça",
                        ["XS (34/36)", "S (38)", "M (40/42)", "L (42/44)", "XL (46/48)", "XXL (50/52)"], key="rh_tam_calc")
                with col_l:
                    tam_botas = st.selectbox("Botas",
                        ["40", "41", "42", "43", "44", "45", "Outro"], key="rh_tam_bot")
                
                st.markdown("#### 👤 Dados da Conta")
                tipo = st.selectbox("Tipo", ["Técnico", "Chefe de Equipa", "Admin", "Comercial", "Cliente"], key="rh_tipo")
                cargo = st.selectbox("Cargo", ["Instrumentista", "Técnico de Campo", "Chefe de Equipa", "Engenheiro", "Gestor de Projeto"], key="rh_cargo")
                local = st.checkbox("É Local? (Não precisa dormida)", key="rh_local")
                preco_hora = st.number_input("Preço Hora (€)", min_value=0.0, value=15.0, key="rh_preco")
                password = st.text_input("Password Inicial *", type="password", value="gestnow123", key="rh_pass")
                
                observacoes = st.text_area("Observações", key="rh_obs")
                
                if st.form_submit_button("💾 Criar Colaborador", use_container_width=True):
                    if nome and telefone and nif and password:
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
                                "Morada": morada,
                                "Localidade": localidade,
                                "Concelho": concelho,
                                "Codigo_Postal": cod_postal,
                                "Naturalidade": naturalidade,
                                "Nacionalidade": nacionalidade,
                                "NIF": nif,
                                "NISS": niss,
                                "CC": cc,
                                "CC_Validade": cc_validade.strftime("%d/%m/%Y") if cc_validade else "",
                                "DataNasc": data_nasc.strftime("%d/%m/%Y"),
                                "Estado_Civil": estado_civil,
                                "Sexo": sexo,
                                "Dependentes": str(dependentes),
                                "Profissao": profissao,
                                "Categoria_Profissional": categoria,
                                "Habilitacoes_Literarias": habilitacoes,
                                "Contacto_Emergencia": contacto_emerg,
                                "Nome_Emergencia": nome_emerg,
                                "Grau_Parentesco": grau_parentesco,
                                "Banco_IBAN": iban,
                                "Observacoes": observacoes,
                                "Tamanho_Camisola": tam_camisola,
                                "Tamanho_Calca": tam_calca,
                                "Tamanho_Botas": tam_botas,
                                "Local": "Sim" if local else "Não",
                                "PrecoHora": str(preco_hora),
                                "PrecoHoraStatus": "",
                                "PrecoHoraData": "",
                                "PIN": "0000",
                                "Foto": "",
                                "Campos_Bloqueados": json.dumps([]),
                                "PDFs_Vistos": json.dumps([]),
                                "PDFs_Validados": "Não",
                                "PDFs_Validacao_Data": ""
                            }])
                            users = pd.concat([users, new_user], ignore_index=True)
                            save_db(users, "usuarios.csv")
                            
                            log_audit(usuario=st.session_state.user, acao="CRIAR_COLABORADOR", tabela="usuarios.csv", registro_id=nome, detalhes=f"Novo colaborador criado: {nome}", ip="")
                            
                            inv()
                            st.success(f"✅ {nome} criado com sucesso!")
                            st.info(f"🔑 Password inicial: `{password}`")
                            st.rerun()
                    else:
                        st.error("❌ Nome, Telefone, NIF e password são obrigatórios!")
        
        with col2:
            st.markdown('<div class="section-title">👥 Lista de Colaboradores</div>', unsafe_allow_html=True)
            if not users.empty:
                cols_visiveis = [col for col in ['Nome', 'Tipo', 'Cargo', 'Telefone', 'Email', 'NIF', 'Local', 'PrecoHora'] if col in users.columns]
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
                                st.info("⚠️ Por segurança, a password não é visível")
                            with col_pwd2:
                                nova_password = st.text_input("Nova password", type="password", key=f"new_pwd_{idx}")
                                if st.button("🔄 Resetar Password", key=f"btn_reset_{idx}"):
                                    if nova_password:
                                        users.loc[idx, 'Password'] = hp(nova_password)
                                        save_db(users, "usuarios.csv")
                                        st.success(f"✅ Password de {nome_user} atualizada!")
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

    # ========== TAB PDFs OBRIGATÓRIOS ==========
    with tab_pdfs:
        st.markdown("### 📄 Gestão de PDFs Obrigatórios", unsafe_allow_html=True)
        
        st.info("""
        **Instruções:**
        1. Faz upload dos PDFs obrigatórios (ilimitado)
        2. Os colaboradores visualizarão estes PDFs no seu perfil
        3. Devem validar a visualização de TODOS os PDFs
        4. Receberás notificação quando validarem
        5. **No dia 1 de cada mês, todos devem validar novamente**
        6. **Ao adicionar PDF novo, todos devem validar novamente**
        """)
        
        try:
            pdfs_db = load_db("pdfs_obrigatorios.csv", [
                "ID", "Nome", "Descricao", "Data_Upload", "Upload_Por", "Ficheiro_b64"
            ])
        except:
            pdfs_db = pd.DataFrame(columns=[
                "ID", "Nome", "Descricao", "Data_Upload", "Upload_Por", "Ficheiro_b64"
            ])
        
        st.markdown("#### 📋 PDFs Atuais")
        
        if not pdfs_db.empty and len(pdfs_db) > 0:
            st.success(f"✅ {len(pdfs_db)} PDF(s) obrigatório(s) carregado(s)")
            
            for idx, pdf in pdfs_db.iterrows():
                with st.expander(f"📄 {pdf.get('Nome', 'PDF')} - Carregado em {pdf.get('Data_Upload', 'N/A')}", expanded=True):
                    st.write(f"**Descrição:** {pdf.get('Descricao', 'N/A')}")
                    st.write(f"**Upload por:** {pdf.get('Upload_Por', 'N/A')}")
                    
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
                    
                    if st.button("🗑️ Eliminar PDF", key=f"delete_pdf_{idx}", type="secondary"):
                        pdfs_db = pdfs_db.drop(idx)
                        save_db(pdfs_db, "pdfs_obrigatorios.csv")
                        st.success("✅ PDF eliminado!")
                        inv()
                        st.rerun()
        else:
            st.warning("📋 Nenhum PDF obrigatório carregado ainda.")
        
        st.divider()
        
        st.markdown("#### ➕ Upload de Novo PDF Obrigatório")
        
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
                    
                    # 🔥 RESETAR VALIDAÇÃO DE TODOS OS COLABORADORES
                    st.info("🔄 A atualizar validações de todos os colaboradores...")
                    
                    for idx, user in users.iterrows():
                        users.loc[idx, 'PDFs_Validados'] = 'Não'
                        users.loc[idx, 'PDFs_Vistos'] = json.dumps([])
                        users.loc[idx, 'PDFs_Validacao_Data'] = ''
                    
                    save_db(users, "usuarios.csv")
                    
                    log_audit(usuario=st.session_state.user, acao="UPLOAD_PDF_OBRIGATORIO", tabela="pdfs_obrigatorios.csv", registro_id=novo_pdf['ID'].iloc[0], detalhes=f"PDF carregado: {nome_pdf}. Validação resetada para {len(users)} colaboradores", ip="")
                    
                    # Notificar todos os colaboradores (exceto admins)
                    notificados = 0
                    for idx, user in users.iterrows():
                        if user.get('Tipo', '') != 'Admin':
                            criar_notificacao(
                                destinatario=user.get('Nome', ''),
                                titulo="📄 Novo Documento Obrigatório",
                                mensagem=f"Foi adicionado um novo documento obrigatório: {nome_pdf}. Deves validar todos os documentos no teu perfil.",
                                tipo="warning",
                                acao_url="/tecnico"
                            )
                            notificados += 1
                    
                    st.success(f"✅ PDF '{nome_pdf}' carregado com sucesso!")
                    st.info(f"🔄 Todos os {len(users)} colaboradores deverão validar os PDFs novamente no próximo acesso.")
                    st.info(f"📧 {notificados} colaboradores notificados.")
                    inv()
                    st.rerun()
                else:
                    st.warning("⚠️ Por favor, preenche o nome e faz upload do PDF.")

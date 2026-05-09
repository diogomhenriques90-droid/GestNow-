import streamlit as st
import pandas as pd
import json
from datetime import datetime
from core import save_db, inv, hp, cp, log_audit, criar_notificacao, load_db, _gcs_read
import base64
import uuid


def _load_users_fresh():
    """Lê usuarios.csv SEMPRE do GCS sem cache."""
    try:
        buf = _gcs_read("usuarios.csv")
        if buf:
            df = pd.read_csv(buf, dtype=str, on_bad_lines='skip', encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            return df.fillna("")
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


def render_rh(users, avals_db, obras_db, inst_acessos_db):
    """Módulo de Recursos Humanos — Gestão Completa de Colaboradores"""

    cols_obrigatorias = {
        'Nome': '', 'Password': '', 'Tipo': 'Técnico', 'Cargo': 'Técnico',
        'Email': '', 'Telefone': '', 'Morada': '', 'Localidade': '',
        'Concelho': '', 'Codigo_Postal': '', 'Naturalidade': '',
        'Nacionalidade': 'Portugal', 'NIF': '', 'NISS': '', 'CC': '',
        'CC_Validade': '', 'DataNasc': '', 'Estado_Civil': '', 'Sexo': '',
        'Dependentes': '0', 'Profissao': '', 'Categoria_Profissional': '',
        'Habilitacoes_Literarias': '', 'Contacto_Emergencia': '',
        'Nome_Emergencia': '', 'Grau_Parentesco': '', 'Banco_IBAN': '',
        'Observacoes': '', 'Tamanho_Camisola': '', 'Tamanho_Calca': '',
        'Tamanho_Botas': '', 'Local': 'Não', 'PrecoHora': '15.0',
        'PrecoHoraStatus': '', 'PrecoHoraData': '', 'PIN': '0000',
        'Foto': '', 'Campos_Bloqueados': '[]', 'PDFs_Vistos': '[]',
        'PDFs_Validados': 'Não', 'PDFs_Validacao_Data': ''
    }
    for col, val in cols_obrigatorias.items():
        if col not in users.columns:
            users[col] = val

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
        color: white; padding: 15px; border-radius: 10px;
        margin: 30px 0 20px 0; font-size: 1.3rem; font-weight: bold;
    }
    .subsection-title {
        background: rgba(59,130,246,0.1); border-left: 4px solid #3B82F6;
        padding: 10px 15px; margin: 20px 0 15px 0;
        font-size: 1.1rem; font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 👥 Gestão de Recursos Humanos")

    tab_pessoal, tab_avaliacoes, tab_historico, tab_pdfs = st.tabs([
        "Gestão de Pessoal", "Avaliações", "Histórico", "📄 PDFs Obrigatórios"
    ])

    # ══════════════════════════════════════════════════════════════════
    # TAB PESSOAL
    # ══════════════════════════════════════════════════════════════════
    with tab_pessoal:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown('<div class="section-title">➕ Novo Colaborador</div>',
                        unsafe_allow_html=True)
            with st.form("form_novo_colab"):
                st.markdown("#### 📋 Identificação")
                nome = st.text_input("Nome Completo *", key="rh_nome")

                col_a, col_b = st.columns(2)
                with col_a:
                    telefone       = st.text_input("Contacto *",         key="rh_tel")
                    email          = st.text_input("Email",               key="rh_email")
                with col_b:
                    contacto_emerg = st.text_input("Emergência Tel.",     key="rh_emerg_tel")
                    nome_emerg     = st.text_input("Nome Emergência",     key="rh_emerg_nome")
                    grau_parent    = st.text_input("Grau Parentesco",     key="rh_emerg_grau")

                st.markdown("#### 📍 Morada")
                morada = st.text_input("Morada", key="rh_morada")
                col_c, col_d, col_e = st.columns(3)
                with col_c: localidade = st.text_input("Localidade",   key="rh_localidade")
                with col_d: concelho   = st.text_input("Concelho",     key="rh_concelho")
                with col_e: cod_postal = st.text_input("Cód. Postal",  key="rh_cp")

                st.markdown("#### 🌍 Dados Pessoais")
                col_f, col_g = st.columns(2)
                with col_f:
                    naturalidade  = st.text_input("Naturalidade", key="rh_naturalidade")
                    data_nasc     = st.date_input("Data Nascimento", key="rh_datanasc",
                                                   min_value=datetime(1950, 1, 1),
                                                   max_value=datetime.now())
                with col_g:
                    nacionalidade = st.text_input("Nacionalidade", value="Portugal",
                                                   key="rh_nacionalidade")
                    estado_civil  = st.selectbox("Estado Civil",
                        ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União de Facto"],
                        key="rh_ec")
                sexo = st.radio("Sexo", ["Masculino", "Feminino"], horizontal=True, key="rh_sexo")

                st.markdown("#### 🆔 Documentos")
                col_h, col_i = st.columns(2)
                with col_h:
                    nif  = st.text_input("NIF *",  key="rh_nif")
                    cc   = st.text_input("CC",     key="rh_cc")
                    niss = st.text_input("NISS",   key="rh_niss")
                with col_i:
                    cc_val      = st.date_input("Validade CC", key="rh_cc_val",
                                                 min_value=datetime.now())
                    dependentes = st.number_input("Dependentes", min_value=0,
                                                   value=0, key="rh_dep")

                st.markdown("#### 💼 Profissional")
                profissao    = st.text_input("Profissão",              key="rh_prof")
                categoria    = st.text_input("Categoria Profissional", key="rh_cat")
                habilitacoes = st.selectbox("Habilitações",
                    ["4º Ano","6º Ano","9º Ano","12º Ano",
                     "Curso Técnico","Licenciatura","Mestrado","Doutoramento"],
                    key="rh_hab")

                st.markdown("#### 💰 Bancário")
                iban = st.text_input("IBAN", key="rh_iban",
                                     placeholder="PT50 0000 0000 0000 00000 0000")

                st.markdown("#### 👕 Fardamento")
                col_j, col_k, col_l = st.columns(3)
                with col_j:
                    tam_cam  = st.selectbox("Camisola",
                        ["XS","S","M","L","XL","XXL","XXXL"], key="rh_tam_cam")
                with col_k:
                    tam_calc = st.selectbox("Calça",
                        ["XS (34/36)","S (38)","M (40/42)","L (42/44)","XL (46/48)","XXL (50/52)"],
                        key="rh_tam_calc")
                with col_l:
                    tam_bot  = st.selectbox("Botas",
                        ["40","41","42","43","44","45","Outro"], key="rh_tam_bot")

                st.markdown("#### 👤 Conta")
                tipo_u     = st.selectbox("Tipo",
                    ["Técnico","Chefe de Equipa","Admin","Comercial","Cliente"],
                    key="rh_tipo")
                cargo_u    = st.selectbox("Cargo",
                    ["Instrumentista","Técnico de Campo","Chefe de Equipa",
                     "Engenheiro","Gestor de Projeto"],
                    key="rh_cargo")
                local_u    = st.checkbox("É Local? (não precisa dormida)", key="rh_local")
                preco_hora = st.number_input("Preço Hora (€)", min_value=0.0,
                                              value=15.0, key="rh_preco")
                password   = st.text_input("Password Inicial *", type="password",
                                           value="gestnow123", key="rh_pass")
                observacoes= st.text_area("Observações", key="rh_obs")

                if st.form_submit_button("💾 Criar Colaborador", use_container_width=True):
                    if nome and telefone and nif and password:
                        # ✅ CRÍTICO: ler estado ACTUAL do GCS antes de guardar
                        # Evita sobrescrever utilizadores que existem no GCS
                        # mas que não estão no cache em memória
                        users_live = _load_users_fresh()
                        if users_live.empty:
                            # Fallback para o users em memória se GCS falhar
                            users_live = users.copy()

                        if nome in users_live.get('Nome', pd.Series([])).values:
                            st.error(f"❌ Já existe um colaborador com o nome '{nome}'!")
                        else:
                            new_user = pd.DataFrame([{
                                "Nome": nome,
                                "Password": hp(password),
                                "Tipo": tipo_u,
                                "Cargo": cargo_u,
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
                                "CC_Validade": cc_val.strftime("%d/%m/%Y") if cc_val else "",
                                "DataNasc": data_nasc.strftime("%d/%m/%Y"),
                                "Estado_Civil": estado_civil,
                                "Sexo": sexo,
                                "Dependentes": str(dependentes),
                                "Profissao": profissao,
                                "Categoria_Profissional": categoria,
                                "Habilitacoes_Literarias": habilitacoes,
                                "Contacto_Emergencia": contacto_emerg,
                                "Nome_Emergencia": nome_emerg,
                                "Grau_Parentesco": grau_parent,
                                "Banco_IBAN": iban,
                                "Observacoes": observacoes,
                                "Tamanho_Camisola": tam_cam,
                                "Tamanho_Calca": tam_calc,
                                "Tamanho_Botas": tam_bot,
                                "Local": "Sim" if local_u else "Não",
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

                            # ✅ Concatenar com estado fresco do GCS
                            updated = pd.concat([users_live, new_user], ignore_index=True)
                            resultado = save_db(updated, "usuarios.csv")

                            if resultado:
                                log_audit(
                                    usuario=st.session_state.user,
                                    acao="CRIAR_COLABORADOR",
                                    tabela="usuarios.csv",
                                    registro_id=nome,
                                    detalhes=f"Novo colaborador criado: {nome}",
                                    ip=""
                                )
                                inv()
                                st.success(f"✅ {nome} criado com sucesso!")
                                st.info(f"🔑 Password inicial: `{password}`")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao guardar no GCS. Verifica as credenciais.")
                    else:
                        st.error("❌ Nome, Telefone, NIF e password são obrigatórios!")

        with col2:
            st.markdown('<div class="section-title">👥 Lista de Colaboradores</div>',
                        unsafe_allow_html=True)

            # ✅ Mostrar sempre a lista mais fresca do GCS
            users_display = _load_users_fresh()
            if users_display.empty:
                users_display = users.copy()

            if not users_display.empty:
                cols_vis = [c for c in
                    ['Nome', 'Tipo', 'Cargo', 'Telefone', 'Email', 'NIF', 'Local', 'PrecoHora']
                    if c in users_display.columns]
                st.dataframe(users_display[cols_vis], use_container_width=True)

                st.divider()
                st.markdown("### Gestão Individual")

                for idx, user in users_display.iterrows():
                    nome_user = user.get('Nome', f'Utilizador_{idx}')

                    # ✅ CORRIGIDO: sem key no expander
                    with st.expander(f"👤 {nome_user} — {user.get('Cargo', 'N/A')}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Email:** {user.get('Email','N/A')}")
                            st.write(f"**Telefone:** {user.get('Telefone','N/A')}")
                            st.write(f"**NIF:** {user.get('NIF','N/A')}")
                            st.write(f"**Morada:** {user.get('Morada','N/A')}")
                        with c2:
                            st.write(f"**Tipo:** {user.get('Tipo','N/A')}")
                            st.write(f"**Cargo:** {user.get('Cargo','N/A')}")
                            st.write(f"**Preço Hora:** € {user.get('PrecoHora','15.0')}")

                        preco_status = user.get('PrecoHoraStatus', '')
                        if preco_status == 'Aceite':
                            st.success(f"✅ Preço Hora ACEITE em {user.get('PrecoHoraData','N/A')}")
                        elif preco_status == 'Recusado':
                            st.error(f"❌ Preço Hora RECUSADO em {user.get('PrecoHoraData','N/A')}")
                        else:
                            st.warning("⏳ Preço Hora AGUARDANDO validação")

                        pdfs_val = user.get('PDFs_Validados', 'Não')
                        if pdfs_val == 'Sim':
                            st.success(f"✅ PDFs validados em {user.get('PDFs_Validacao_Data','N/A')}")
                        else:
                            st.warning("⏳ PDFs AGUARDANDO visualização")

                        # ── Reset de Password ─────────────────────────
                        if st.session_state.get('tipo') == 'Admin':
                            st.divider()
                            st.markdown("**🔐 Resetar Password**")
                            col_p1, col_p2 = st.columns(2)
                            with col_p1:
                                st.info("⚠️ Por segurança, a password não é visível")
                            with col_p2:
                                nova_pwd = st.text_input("Nova password", type="password",
                                                          key=f"new_pwd_{idx}")
                                if st.button("🔄 Resetar Password", key=f"btn_reset_{idx}"):
                                    if nova_pwd:
                                        if len(nova_pwd) < 4:
                                            st.error("❌ Mínimo 4 caracteres.")
                                        else:
                                            # ✅ Ler fresco do GCS antes de guardar
                                            users_live = _load_users_fresh()
                                            if not users_live.empty:
                                                mask = users_live['Nome'] == nome_user
                                                if mask.any():
                                                    users_live.loc[mask, 'Password'] = hp(nova_pwd)
                                                    resultado = save_db(users_live, "usuarios.csv")
                                                    if resultado:
                                                        inv()
                                                        log_audit(
                                                            usuario=st.session_state.user,
                                                            acao="RESETAR_PASSWORD_ADMIN",
                                                            tabela="usuarios.csv",
                                                            registro_id=nome_user,
                                                            detalhes=f"Password de {nome_user} resetada pelo admin",
                                                            ip=""
                                                        )
                                                        st.success(f"✅ Password de {nome_user} atualizada!")
                                                        st.rerun()
                                                    else:
                                                        st.error("❌ Erro ao guardar no GCS.")
                                                else:
                                                    st.error(f"❌ {nome_user} não encontrado no GCS.")
                                            else:
                                                st.error("❌ Erro ao aceder à base de dados.")
                                    else:
                                        st.warning("⚠️ Escreve a nova password.")

                        # ── Ações ─────────────────────────────────────
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            if st.button("✏️ Editar", key=f"edit_{idx}"):
                                st.info("Vai ao Perfil do colaborador para edição completa.")
                        with col_b:
                            if st.button("📊 Avaliar", key=f"eval_{idx}"):
                                st.session_state['avaliar_user'] = nome_user
                                st.rerun()
                        with col_c:
                            if st.button("🗑️ Dispensar", key=f"del_{idx}", type="secondary"):
                                if st.session_state.get('user') != nome_user:
                                    # ✅ Ler fresco do GCS antes de guardar
                                    users_live = _load_users_fresh()
                                    if not users_live.empty:
                                        users_live = users_live[users_live['Nome'] != nome_user]
                                        resultado = save_db(users_live, "usuarios.csv")
                                        if resultado:
                                            inv()
                                            log_audit(
                                                usuario=st.session_state.user,
                                                acao="DISPENSAR_COLABORADOR",
                                                tabela="usuarios.csv",
                                                registro_id=nome_user,
                                                detalhes=f"Dispensado: {nome_user}",
                                                ip=""
                                            )
                                            st.success("✅ Colaborador dispensado!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Erro ao guardar no GCS.")
                                else:
                                    st.error("❌ Não pode eliminar o seu próprio utilizador!")
            else:
                st.info("📋 Sem colaboradores registados.")

    # ══════════════════════════════════════════════════════════════════
    # TAB AVALIAÇÕES
    # ══════════════════════════════════════════════════════════════════
    with tab_avaliacoes:
        st.markdown("### 📊 Avaliações de Desempenho")

        # Usar lista fresca de utilizadores
        users_aval = _load_users_fresh()
        if users_aval.empty:
            users_aval = users.copy()

        if not users_aval.empty and 'Nome' in users_aval.columns:
            trabalhador_sel = st.selectbox("Selecionar Trabalhador",
                users_aval['Nome'].tolist(), key="avalia_trab")

            aval_trab = (avals_db[avals_db['Trabalhador'] == trabalhador_sel]
                         if 'Trabalhador' in avals_db.columns else pd.DataFrame())

            col1, col2 = st.columns(2)
            with col1:
                nota_tec   = st.slider("Competência Técnica",  1, 10, 5, key="nota_tec")
                nota_pont  = st.slider("Pontualidade",          1, 10, 5, key="nota_pont")
                nota_eq    = st.slider("Trabalho em Equipa",    1, 10, 5, key="nota_eq")
            with col2:
                nota_proat = st.slider("Proatividade",          1, 10, 5, key="nota_proat")
                nota_com   = st.slider("Comunicação",           1, 10, 5, key="nota_com")
                comentarios= st.text_area("Comentários",        key="avalia_coment")

            if st.button("💾 Guardar Avaliação", key="btn_avalia"):
                media   = (nota_tec + nota_pont + nota_eq + nota_proat + nota_com) / 5
                nova_av = pd.DataFrame([{
                    "Data":             datetime.now().strftime("%d/%m/%Y"),
                    "Trabalhador":      trabalhador_sel,
                    "Nota_Tecnica":     nota_tec,
                    "Nota_Pontualidade":nota_pont,
                    "Nota_Trabalho_Eq": nota_eq,
                    "Nota_Proatividade":nota_proat,
                    "Nota_Comunicacao": nota_com,
                    "Media":            round(media, 2),
                    "Comentarios":      comentarios
                }])
                avals_db = pd.concat([avals_db, nova_av], ignore_index=True)
                save_db(avals_db, "avaliacoes.csv")
                log_audit(
                    usuario=st.session_state.user,
                    acao="AVALIAR_COLABORADOR",
                    tabela="avaliacoes.csv",
                    registro_id=trabalhador_sel,
                    detalhes=f"Avaliação de {trabalhador_sel}: média {round(media,2)}",
                    ip=""
                )
                inv()
                st.success("✅ Avaliação guardada!")
                st.rerun()

            if not aval_trab.empty:
                st.divider()
                st.markdown("### Histórico de Avaliações")
                st.dataframe(aval_trab, use_container_width=True)
        else:
            st.warning("⚠️ Não existem utilizadores para avaliar.")

    # ══════════════════════════════════════════════════════════════════
    # TAB HISTÓRICO
    # ══════════════════════════════════════════════════════════════════
    with tab_historico:
        st.markdown("### 📜 Histórico de Trabalhadores")
        st.info("Funcionalidade em desenvolvimento...")

    # ══════════════════════════════════════════════════════════════════
    # TAB PDFs OBRIGATÓRIOS
    # ══════════════════════════════════════════════════════════════════
    with tab_pdfs:
        st.markdown("### 📄 Gestão de PDFs Obrigatórios")
        st.info("""
        **Instruções:**
        1. Faz upload dos PDFs obrigatórios
        2. Os colaboradores visualizam no perfil
        3. Devem validar TODOS os PDFs
        4. Recebes notificação quando validarem
        5. **Dia 1 de cada mês → todos validam novamente**
        6. **PDF novo → todos validam novamente**
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

        if not pdfs_db.empty:
            st.success(f"✅ {len(pdfs_db)} PDF(s) obrigatório(s) carregado(s)")
            for idx, pdf in pdfs_db.iterrows():
                with st.expander(
                    f"📄 {pdf.get('Nome','PDF')} — {pdf.get('Data_Upload','N/A')}",
                    expanded=True
                ):
                    st.write(f"**Descrição:** {pdf.get('Descricao','N/A')}")
                    st.write(f"**Upload por:** {pdf.get('Upload_Por','N/A')}")
                    if pdf.get('Ficheiro_b64'):
                        try:
                            pdf_data = base64.b64decode(pdf['Ficheiro_b64'])
                            st.download_button(
                                "📥 Descarregar PDF", pdf_data,
                                f"{pdf.get('Nome','documento')}.pdf",
                                "application/pdf",
                                key=f"dl_pdf_{idx}"
                            )
                        except:
                            st.error("❌ Erro ao descarregar PDF")

                    if st.button("🗑️ Eliminar PDF", key=f"del_pdf_{idx}", type="secondary"):
                        pdfs_db = pdfs_db.drop(idx)
                        save_db(pdfs_db, "pdfs_obrigatorios.csv")
                        inv()
                        st.success("✅ PDF eliminado!")
                        st.rerun()
        else:
            st.warning("📋 Nenhum PDF obrigatório carregado ainda.")

        st.divider()
        st.markdown("#### ➕ Upload de Novo PDF")

        with st.form("form_upload_pdf"):
            col1, col2 = st.columns(2)
            with col1:
                nome_pdf = st.text_input("Nome do Documento",
                    placeholder="Ex: Regulamento Interno")
                desc_pdf = st.text_area("Descrição",
                    placeholder="Ex: Regulamento interno da empresa")
            with col2:
                fich_pdf = st.file_uploader("📄 Ficheiro PDF", type=["pdf"])

            if st.form_submit_button("📤 Upload de PDF", use_container_width=True, type="primary"):
                if nome_pdf and fich_pdf:
                    pdf_b64  = base64.b64encode(fich_pdf.read()).decode()
                    novo_pdf = pd.DataFrame([{
                        "ID":          str(uuid.uuid4())[:8].upper(),
                        "Nome":        nome_pdf,
                        "Descricao":   desc_pdf,
                        "Data_Upload": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Upload_Por":  st.session_state.user,
                        "Ficheiro_b64":pdf_b64
                    }])
                    pdfs_db = pd.concat([pdfs_db, novo_pdf], ignore_index=True) if not pdfs_db.empty else novo_pdf
                    save_db(pdfs_db, "pdfs_obrigatorios.csv")

                    # ✅ Resetar validação usando dados frescos do GCS
                    users_live = _load_users_fresh()
                    if not users_live.empty:
                        for idx_u in users_live.index:
                            users_live.loc[idx_u, 'PDFs_Validados']      = 'Não'
                            users_live.loc[idx_u, 'PDFs_Vistos']         = json.dumps([])
                            users_live.loc[idx_u, 'PDFs_Validacao_Data'] = ''
                        save_db(users_live, "usuarios.csv")

                    log_audit(
                        usuario=st.session_state.user,
                        acao="UPLOAD_PDF_OBRIGATORIO",
                        tabela="pdfs_obrigatorios.csv",
                        registro_id=novo_pdf['ID'].iloc[0],
                        detalhes=f"PDF: {nome_pdf}. Reset para todos os colaboradores",
                        ip=""
                    )

                    # Notificar todos os colaboradores
                    notificados = 0
                    users_notif = _load_users_fresh()
                    if not users_notif.empty:
                        for _, u in users_notif.iterrows():
                            if u.get('Tipo', '') != 'Admin':
                                criar_notificacao(
                                    destinatario=u.get('Nome', ''),
                                    titulo="📄 Novo Documento Obrigatório",
                                    mensagem=f"Novo documento: {nome_pdf}. Valida no teu perfil.",
                                    tipo="warning",
                                    acao_url="/tecnico"
                                )
                                notificados += 1

                    inv()
                    st.success(f"✅ PDF '{nome_pdf}' carregado!")
                    st.info(f"🔄 {notificados} colaboradores notificados.")
                    st.rerun()
                else:
                    st.warning("⚠️ Preenche o nome e faz upload do PDF.")

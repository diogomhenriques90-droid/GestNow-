import streamlit as st
import pandas as pd
import uuid, base64, json
from datetime import datetime, date
from io import BytesIO

from core import (
    save_db, inv, load_db, log_audit, criar_notificacao,
    hp, _gcs_read, _gcs_write_binary, _gcs_read_binary,
    _fill_contrato_template, ICONS
)

# ── Tipos e cargos disponíveis ────────────────────────────────────────
TIPOS_USUARIO = ["Técnico","Instrumentista","Engenheiro","Chefe de Equipa","Admin","Cliente"]

CARGOS_POR_TIPO = {
    "Técnico":        ["Técnico Eletricista","Técnico Mecânico","Técnico Automação",
                       "Técnico Instrumentação","Operador Especializado","Serralheiro","Outro"],
    "Instrumentista": ["Instrumentista","Técnico Instrumentista","Instrumentista Sénior"],
    "Engenheiro":     ["Engenheiro Eletrotécnico","Engenheiro Mecânico",
                       "Engenheiro Automação","Engenheiro Instrumentação",
                       "Engenheiro de Projeto"],
    "Chefe de Equipa":["Chefe de Equipa","Encarregado","Supervisor de Obra"],
    "Admin":          ["Administrador","Gestor RH","Gestor IT"],
    "Cliente":        ["Gestor de Projeto","Fiscal de Obra","Responsável Técnico"],
}

# Campos do colaborador para exportação / visualização completa
CAMPOS_PERFIL = [
    ("Identificação",   ["Nome","NIF","NISS","CC","CC_Validade","DataNasc",
                         "Naturalidade","Estado_Civil","Nacionalidade"]),
    ("Contactos",       ["Telefone","Email"]),
    ("Morada",          ["Morada","Localidade","Concelho","Codigo_Postal"]),
    ("Emergência",      ["Nome_Emergencia","Contacto_Emergencia","Grau_Parentesco"]),
    ("Profissional",    ["Tipo","Cargo","PrecoHora","PrecoHoraStatus",
                         "Local_Obra","Cliente_Obra"]),
    ("Fardamento",      ["Tamanho_Camisola","Tamanho_Calca","Tamanho_Botas"]),
    ("Onboarding",      ["PDFs_Validados","PDFs_Validacao_Data",
                         "PrecoHoraData","Perfil_Completo","Perfil_Data",
                         "IBAN_Data_Upload"]),
    ("Contrato",        ["Contrato_Gerado","Contrato_Data","Contrato_Enviado",
                         "Contrato_Enviado_Data","Contrato_Assinado",
                         "Contrato_Assinatura_Data","Contrato_Validado_Admin",
                         "Contrato_Validado_Data"]),
]

def _load_users_fresh():
    import time
    for t in range(3):
        try:
            buf = _gcs_read("usuarios.csv")
            if buf:
                df = pd.read_csv(buf, dtype=str, on_bad_lines='skip',
                                 encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].str.strip()
                return df.fillna("")
            time.sleep(0.3)
        except:
            if t == 2: return pd.DataFrame()
            time.sleep(0.3)
    return pd.DataFrame()


def _exportar_excel_colaborador(user_row: pd.Series) -> bytes:
    """Gera um Excel com todos os dados do colaborador."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        linhas = []
        for secao, campos in CAMPOS_PERFIL:
            linhas.append({"Secção": f"── {secao} ──", "Campo": "", "Valor": ""})
            for campo in campos:
                valor = user_row.get(campo, '')
                # Não exportar dados binários
                if campo.endswith('_b64') or campo.endswith('_b64'):
                    valor = "(ficheiro binário)" if valor else ""
                linhas.append({"Secção": secao, "Campo": campo, "Valor": valor})
        df_export = pd.DataFrame(linhas)
        df_export.to_excel(writer, index=False, sheet_name="Dados Colaborador")

        # Formatar
        ws = writer.sheets["Dados Colaborador"]
        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 28
        ws.column_dimensions['C'].width = 45

    output.seek(0)
    return output.getvalue()


def render_admin_rh(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db,
     inst_acessos_db) = args

    admin_nome = st.session_state.get('user', 'Admin')

    st.markdown("""
    <style>
    [data-baseweb="select"] [role="option"] {
        color: #111827 !important;
        background: #FFFFFF !important;
    }
    [data-baseweb="menu"] {
        background: #FFFFFF !important;
    }
    [data-baseweb="menu"] li {
        color: #111827 !important;
    }
    .stDownloadButton > button {
        color: #111827 !important;
        background: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("# 👥 Recursos Humanos")

    tab_lista, tab_gestao, tab_contrato, tab_template = st.tabs([
        "👥 Colaboradores",
        "📋 Gestão Individual",
        "📄 Contratos",
        "⚙️ Templates & Config",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 — LISTA DE COLABORADORES + CRIAR
    # ════════════════════════════════════════════════════════════════
    with tab_lista:

        col_titulo, col_btn = st.columns([4, 1])
        with col_titulo:
            st.markdown("### 👥 Todos os Colaboradores")
        with col_btn:
            if st.button("➕ Novo", key="btn_novo_colab",
                          type="primary", use_container_width=True):
                st.session_state['show_criar_colab'] = True
                st.rerun()

        users_live = _load_users_fresh()

        # ── Formulário de criação ─────────────────────────────────
        if st.session_state.get('show_criar_colab', False):
            st.markdown("---")
            st.markdown("#### ➕ Criar Novo Colaborador")

            with st.form("form_criar_colab"):
                st.markdown("**Dados obrigatórios**")
                c1, c2 = st.columns(2)
                with c1:
                    novo_nome = st.text_input("Nome Completo *",
                        key="nc_nome", placeholder="Nome completo")
                    novo_tipo = st.selectbox("Tipo de Acesso *",
    TIPOS_USUARIO, key="rh_nc_tipo")
                with c2:
                    novo_tel  = st.text_input("Contacto *",
                        key="nc_tel", placeholder="9XXXXXXXX")
                    novo_pwd  = st.text_input("Password *",
                        key="nc_pwd", type="password",
                        placeholder="Mínimo 4 caracteres")

                # Cargo dinâmico baseado no tipo
                cargos_disp = CARGOS_POR_TIPO.get(novo_tipo, ["Outro"])
                novo_cargo  = st.selectbox("Cargo / Função *",
                    cargos_disp, key="rh_nc_cargo") 

                st.markdown("**Dados da Obra** *(obrigatório para contrato)*")
                c3, c4 = st.columns(2)
                with c3:
                    novo_local  = st.text_input("Local da Obra *",
                        key="nc_local",
                        placeholder="Ex: Refinaria de Sines")
                with c4:
                    novo_cliente = st.text_input("Cliente *",
                        key="nc_cliente",
                        placeholder="Ex: GALP Energia")

                st.markdown("**Dados opcionais**")
                c5, c6 = st.columns(2)
                with c5:
                    novo_nif    = st.text_input("NIF (opcional na criação)",
                        key="nc_nif")
                    novo_preco  = st.number_input("Preço Hora (€)",
                        min_value=0.0, value=15.0, step=0.5,
                        key="nc_preco")
                with c6:
                    novo_email  = st.text_input("Email",
                        key="nc_email",
                        placeholder="colaborador@email.com")

                c_sub, c_can = st.columns(2)
                with c_sub:
                    submitted = st.form_submit_button(
                        "💾 Criar Colaborador",
                        use_container_width=True, type="primary"
                    )
                with c_can:
                    cancelar = st.form_submit_button(
                        "✕ Cancelar", use_container_width=True
                    )

            if cancelar:
                st.session_state['show_criar_colab'] = False
                st.rerun()

            if submitted:
                erros = []
                if not novo_nome.strip():   erros.append("Nome Completo")
                if not novo_tel.strip():    erros.append("Contacto")
                if not novo_pwd.strip() or len(novo_pwd.strip()) < 4:
                    erros.append("Password (mínimo 4 caracteres)")
                if not novo_local.strip():  erros.append("Local da Obra")
                if not novo_cliente.strip():erros.append("Cliente")

                if erros:
                    st.error(f"❌ Campos obrigatórios em falta: {', '.join(erros)}")
                else:
                    # Verificar nome duplicado
                    if not users_live.empty and \
                       novo_nome.strip() in users_live['Nome'].values:
                        st.error(f"❌ Já existe um colaborador com o nome '{novo_nome.strip()}'")
                    else:
                        novo_id  = str(uuid.uuid4())[:8].upper()
                        pwd_hash = hp(novo_pwd.strip())

                        novo_row = {
                            "ID": novo_id,
                            "Nome": novo_nome.strip(),
                            "Tipo": novo_tipo,
                            "Cargo": novo_cargo,
                            "Contacto": novo_tel.strip(),
                            "Telefone": novo_tel.strip(),
                            "Password": pwd_hash,
                            "NIF": novo_nif.strip(),
                            "Email": novo_email.strip(),
                            "PrecoHora": str(novo_preco),
                            "PrecoHoraStatus": "",
                            "Local_Obra": novo_local.strip(),
                            "Cliente_Obra": novo_cliente.strip(),
                            "PDFs_Validados": "Não",
                            "Perfil_Completo": "",
                            "Contrato_Gerado": "",
                            "Data_Criacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        }

                        nova_df = pd.DataFrame([novo_row])
                        updated = pd.concat(
                            [users_live, nova_df], ignore_index=True
                        ) if not users_live.empty else nova_df

                        save_db(updated, "usuarios.csv")
                        inv()
                        log_audit(usuario=admin_nome,
                                  acao="CRIAR_COLABORADOR",
                                  tabela="usuarios.csv",
                                  registro_id=novo_id,
                                  detalhes=f"Criado: {novo_nome.strip()} "
                                           f"({novo_tipo} / {novo_cargo})",
                                  ip="")

                        st.success(f"✅ Colaborador **{novo_nome.strip()}** criado com sucesso!")
                        st.session_state['show_criar_colab'] = False
                        inv()
                        st.rerun()

        # ── Tabela de colaboradores ───────────────────────────────
        if not users_live.empty:
            st.markdown(f"**{len(users_live)} colaborador(es)**")

            # Filtros
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_tipo = st.selectbox("Filtrar por tipo",
                    ["Todos"] + TIPOS_USUARIO, key="rh_filtro_tipo")
            with col_f2:
                filtro_nome = st.text_input("Pesquisar nome",
                    key="rh_filtro_nome", placeholder="Nome...")

            df_show = users_live.copy()
            if filtro_tipo != "Todos":
                df_show = df_show[df_show['Tipo'] == filtro_tipo]
            if filtro_nome:
                df_show = df_show[
                    df_show['Nome'].str.contains(filtro_nome, case=False, na=False)
                ]

            for _, row in df_show.iterrows():
                nome_c    = row.get('Nome','')
                tipo_c    = row.get('Tipo','')
                cargo_c   = row.get('Cargo','')
                estado_pdf = "✅" if row.get('PDFs_Validados','') == 'Sim' else "⏳"
                estado_pfx = "✅" if row.get('Perfil_Completo','') == 'Sim' else "⏳"
                estado_iban= "✅" if row.get('IBAN_Comprovativo_b64','') else "⏳"
                estado_ct  = "✅" if row.get('Contrato_Validado_Admin','') == 'Sim' \
                             else "🔵" if row.get('Contrato_Assinado','') == 'Sim' \
                             else "📄" if row.get('Contrato_Gerado','') == 'Sim' \
                             else "⬜"

                col_info, col_sel = st.columns([5, 1])
                with col_info:
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin-bottom:6px;'>"
                        f"<b style='color:#F1F5F9;'>{nome_c}</b> "
                        f"<span style='color:#64748B;font-size:0.8rem;'>"
                        f"· {tipo_c} · {cargo_c}</span><br>"
                        f"<span style='font-size:0.75rem;color:#94A3B8;'>"
                        f"PDFs {estado_pdf} &nbsp; Perfil {estado_pfx} &nbsp; "
                        f"IBAN {estado_iban} &nbsp; Contrato {estado_ct}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_sel:
                    if st.button("📋", key=f"sel_{nome_c}",
                                  use_container_width=True,
                                  help="Gerir colaborador"):
                        st.session_state['rh_colaborador_sel'] = nome_c
                        st.rerun()
        else:
            st.info("Sem colaboradores registados.")

    # ════════════════════════════════════════════════════════════════
    # TAB 2 — GESTÃO INDIVIDUAL
    # ════════════════════════════════════════════════════════════════
    with tab_gestao:
        users_live2 = _load_users_fresh()

        if users_live2.empty:
            st.info("Sem colaboradores.")
            return

        # Seletor
        nomes = users_live2['Nome'].tolist()
        sel_default = 0
        colab_sel   = st.session_state.get('rh_colaborador_sel', '')
        if colab_sel in nomes:
            sel_default = nomes.index(colab_sel)

        nome_sel = st.selectbox("Selecionar Colaborador",
            nomes, index=sel_default, key="rh_gestao_sel")
        st.session_state['rh_colaborador_sel'] = nome_sel

        match = users_live2[users_live2['Nome'] == nome_sel]
        if match.empty:
            st.warning("Colaborador não encontrado.")
            return
        row = match.iloc[0]

        # ── Cabeçalho do colaborador ──────────────────────────────
        st.markdown(
            f"<div style='background:#1E293B;border-radius:14px;"
            f"padding:16px;margin-bottom:16px;border:1px solid #334155;'>"
            f"<p style='color:#F1F5F9;font-size:1.2rem;font-weight:900;margin:0;'>"
            f"{nome_sel}</p>"
            f"<p style='color:#64748B;font-size:0.85rem;margin:3px 0 0;'>"
            f"{row.get('Tipo','')} · {row.get('Cargo','')} · "
            f"{row.get('Local_Obra','')} → {row.get('Cliente_Obra','')}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        # ── Exportar Excel ────────────────────────────────────────
        excel_bytes = _exportar_excel_colaborador(row)
        st.download_button(
            "📥 Exportar dados em Excel",
            data=excel_bytes,
            file_name=f"colaborador_{nome_sel.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_export_excel"
        )

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        # ── Todos os dados por secções ────────────────────────────
        for secao, campos in CAMPOS_PERFIL:
            tem_dados = any(
                row.get(c,'') and not c.endswith('_b64')
                for c in campos
            )
            with st.expander(f"📂 {secao}", expanded=(secao == "Identificação")):
                c_left, c_right = st.columns(2)
                for i, campo in enumerate(campos):
                    valor = row.get(campo, '')
                    if campo.endswith('_b64'):
                        valor = "✅ Ficheiro presente" if valor else "❌ Não submetido"
                    elif not valor:
                        valor = "—"
                    col_use = c_left if i % 2 == 0 else c_right
                    with col_use:
                        st.markdown(
                            f"<p style='color:#94A3B8;font-size:0.72rem;"
                            f"margin:0;text-transform:uppercase;'>{campo}</p>"
                            f"<p style='color:#F1F5F9;font-size:0.9rem;"
                            f"font-weight:600;margin:0 0 10px;'>{valor}</p>",
                            unsafe_allow_html=True
                        )

        # ── Download Comprovativo IBAN ────────────────────────────
        st.markdown("---")
        st.markdown("#### 🏦 Comprovativo IBAN")
        iban_b64 = row.get('IBAN_Comprovativo_b64', '')
        iban_data = row.get('IBAN_Data_Upload', '')
        if iban_b64:
            st.success(f"✅ Comprovativo submetido em {iban_data}")
            try:
                iban_bytes = base64.b64decode(iban_b64)
                st.download_button(
                    "📥 Descarregar Comprovativo IBAN",
                    data=iban_bytes,
                    file_name=f"iban_{nome_sel.replace(' ','_')}.pdf",
                    mime="application/octet-stream",
                    key="btn_dl_iban"
                )
            except:
                st.error("Erro ao processar o ficheiro IBAN.")
        else:
            st.warning("⏳ Colaborador ainda não submeteu o comprovativo bancário.")

        # ── Bloquear/Desbloquear campos ───────────────────────────
        st.markdown("---")
        st.markdown("#### 🔒 Campos Bloqueados")
        try:
            campos_bl = json.loads(row.get('Campos_Bloqueados', '[]'))
        except:
            campos_bl = []

        todos_bloqueáveis = ["NIF","CC","NISS","Morada","Localidade",
                             "Banco_IBAN","Email","Telefone"]
        novos_bl = st.multiselect(
            "Selecionar campos que o colaborador NÃO pode editar:",
            todos_bloqueáveis, default=campos_bl,
            key="rh_campos_bl"
        )
        if st.button("💾 Guardar Bloqueios",
                      key="btn_guardar_bloqueios"):
            u_fresh = _load_users_fresh()
            mask    = u_fresh['Nome'] == nome_sel
            if mask.any():
                u_fresh.loc[mask, 'Campos_Bloqueados'] = json.dumps(novos_bl)
                save_db(u_fresh, "usuarios.csv")
                inv()
                st.success("✅ Campos bloqueados atualizados.")
                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 3 — CONTRATOS
    # ════════════════════════════════════════════════════════════════
    with tab_contrato:
        users_ct = _load_users_fresh()
        if users_ct.empty:
            st.info("Sem colaboradores.")
            return

        nomes_ct    = users_ct['Nome'].tolist()
        colab_ct    = st.session_state.get('rh_colaborador_sel', nomes_ct[0])
        idx_ct      = nomes_ct.index(colab_ct) if colab_ct in nomes_ct else 0
        nome_ct_sel = st.selectbox("Colaborador",
            nomes_ct, index=idx_ct, key="ct_colab_sel")

        match_ct = users_ct[users_ct['Nome'] == nome_ct_sel]
        if match_ct.empty:
            st.warning("Colaborador não encontrado.")
            return
        row_ct = match_ct.iloc[0]

        # ── Estado do contrato ────────────────────────────────────
        ct_gerado    = row_ct.get('Contrato_Gerado','')    == 'Sim'
        ct_enviado   = row_ct.get('Contrato_Enviado','')   == 'Sim'
        ct_assinado  = row_ct.get('Contrato_Assinado','')  == 'Sim'
        ct_validado  = row_ct.get('Contrato_Validado_Admin','') == 'Sim'

        passos_ct = [
            ("📄 Gerado",    ct_gerado,   row_ct.get('Contrato_Data','')),
            ("📤 Enviado",   ct_enviado,  row_ct.get('Contrato_Enviado_Data','')),
            ("✍️ Assinado",  ct_assinado, row_ct.get('Contrato_Assinatura_Data','')),
            ("✅ Validado",  ct_validado, row_ct.get('Contrato_Validado_Data','')),
        ]

        col_ps = st.columns(4)
        for col_p, (label, feito, data_p) in zip(col_ps, passos_ct):
            with col_p:
                cor_p = "#10B981" if feito else "#334155"
                st.markdown(
                    f"<div style='background:{cor_p}22;border:2px solid {cor_p};"
                    f"border-radius:10px;padding:10px;text-align:center;'>"
                    f"<p style='color:{cor_p};font-weight:700;"
                    f"font-size:0.8rem;margin:0;'>{label}</p>"
                    f"<p style='color:#64748B;font-size:0.68rem;margin:3px 0 0;'>"
                    f"{data_p or '—'}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        # ── Verificar dados completos ─────────────────────────────
        campos_necessarios = ["NIF","NISS","CC","CC_Validade","Morada"]
        dados_em_falta = [c for c in campos_necessarios
                          if not row_ct.get(c,'').strip()]

        if dados_em_falta:
            st.warning(
                f"⚠️ Perfil incompleto para gerar contrato. "
                f"Em falta: **{', '.join(dados_em_falta)}**"
            )

        # ── PASSO 1: Gerar contrato ───────────────────────────────
        if not ct_gerado:
            template_ok = _gcs_read_binary("contrato_template.docx") is not None

            if not template_ok:
                st.error("❌ Template do contrato não encontrado. "
                         "Faz upload do template no separador '⚙️ Templates'.")
            else:
                st.markdown("#### 📄 Gerar Contrato")
                st.info(
                    "Os dados pessoais são preenchidos automaticamente "
                    "a partir do perfil do colaborador."
                )

                with st.form("form_gerar_ct"):
                    c1, c2 = st.columns(2)
                    with c1:
                        ct_local = st.text_input(
                            "Local da obra *",
                            value=row_ct.get('Local_Obra',''),
                            key="ct_local"
                        )
                        ct_data_inicio = st.date_input(
                            "Data de início *",
                            value=date.today(), key="ct_data_ini"
                        )
                    with c2:
                        ct_cliente = st.text_input(
                            "Cliente *",
                            value=row_ct.get('Cliente_Obra',''),
                            key="ct_cliente"
                        )
                        ct_data_doc = st.date_input(
                            "Data do documento",
                            value=date.today(), key="ct_data_doc"
                        )

                    if st.form_submit_button("📄 Gerar Contrato",
                        use_container_width=True, type="primary"):
                        if not ct_local or not ct_cliente:
                            st.error("❌ Local e Cliente são obrigatórios.")
                        else:
                            morada_completa = " ".join(filter(None, [
                                row_ct.get('Morada',''),
                                row_ct.get('Localidade',''),
                                row_ct.get('Codigo_Postal','')
                            ]))

                            subs = {
                                "{{nome}}":                         row_ct.get('Nome',''),
                                "{{morada}}":                       morada_completa,
                                "{{NIF}}":                          row_ct.get('NIF',''),
                                "{{NISS}}":                         row_ct.get('NISS',''),
                                "{{número de cartão de cidadão}}":  row_ct.get('CC',''),
                                "{{validade do cartão de cidadão}}":row_ct.get('CC_Validade',''),
                                "{{categoria profissional}}":       row_ct.get('Cargo',''),
                                "{{local}}":                        ct_local,
                                "{{Cliente}}":                      ct_cliente,
                                "{{data}}":                         ct_data_doc.strftime("%d de %B de %Y"),
                                "4 de Março de 2026":               ct_data_inicio.strftime("%d de %B de %Y"),
                            }

                            docx_bytes = _fill_contrato_template(subs)
                            if docx_bytes:
                                docx_b64 = base64.b64encode(docx_bytes).decode()
                                u_ct = _load_users_fresh()
                                mask = u_ct['Nome'] == nome_ct_sel
                                if mask.any():
                                    u_ct.loc[mask, 'Contrato_Gerado']  = 'Sim'
                                    u_ct.loc[mask, 'Contrato_Data']    = \
                                        datetime.now().strftime("%d/%m/%Y %H:%M")
                                    u_ct.loc[mask, 'Contrato_b64']     = docx_b64
                                    u_ct.loc[mask, 'Contrato_Local_Obra']   = ct_local
                                    u_ct.loc[mask, 'Contrato_Cliente_Obra'] = ct_cliente
                                    save_db(u_ct, "usuarios.csv")
                                    inv()
                                    log_audit(
                                        usuario=admin_nome,
                                        acao="GERAR_CONTRATO",
                                        tabela="usuarios.csv",
                                        registro_id=row_ct.get('ID',''),
                                        detalhes=f"Contrato gerado para {nome_ct_sel}",
                                        ip=""
                                    )
                                    st.success("✅ Contrato gerado com sucesso!")
                                    st.rerun()
                            else:
                                st.error("❌ Erro ao gerar contrato. "
                                         "Verifica o template.")

        # ── PASSO 2: Download + Enviar ao colaborador ─────────────
        if ct_gerado and not ct_enviado:
            st.markdown("#### 📤 Rever e Enviar ao Colaborador")
            ct_b64 = row_ct.get('Contrato_b64','')
            if ct_b64:
                try:
                    ct_bytes = base64.b64decode(ct_b64)
                    st.download_button(
                        "📥 Descarregar contrato para rever",
                        data=ct_bytes,
                        file_name=f"contrato_{nome_ct_sel.replace(' ','_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument"
                             ".wordprocessingml.document",
                        key="btn_dl_contrato_admin"
                    )
                except:
                    st.error("Erro ao processar o contrato.")
                    
             # ── Re-upload do contrato editado ─────────────────
                st.markdown("##### 📤 Substituir contrato (versão editada)")
                ct_novo = st.file_uploader(
                    "Upload do contrato editado (.docx ou .pdf)",
                    type=["docx","pdf"],
                    key="ct_reupload"
                )
                if ct_novo:
                    if st.button("💾 Guardar versão editada",
                                  key="btn_guardar_ct_editado",
                                  use_container_width=True):
                        novo_b64 = base64.b64encode(ct_novo.read()).decode()
                        u_re = _load_users_fresh()
                        mask = u_re['Nome'] == nome_ct_sel
                        if mask.any():
                            u_re.loc[mask, 'Contrato_b64'] = novo_b64
                            save_db(u_re, "usuarios.csv")
                            inv()
                            st.success("✅ Contrato atualizado com a versão editada!")
                            st.rerun()

                st.markdown("---")       

            col_env1, col_env2 = st.columns(2)
            with col_env1:
                if st.button("📤 Marcar como Enviado ao Colaborador",
                              key="btn_enviar_ct", type="primary",
                              use_container_width=True):
                    u_ct2 = _load_users_fresh()
                    mask  = u_ct2['Nome'] == nome_ct_sel
                    if mask.any():
                        u_ct2.loc[mask, 'Contrato_Enviado']      = 'Sim'
                        u_ct2.loc[mask, 'Contrato_Enviado_Data'] = \
                            datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(u_ct2, "usuarios.csv")
                        criar_notificacao(
                            destinatario=nome_ct_sel,
                            titulo="📄 Contrato disponível",
                            mensagem="O teu contrato de trabalho está disponível "
                                     "para assinar. Acede ao teu Perfil para descarregar.",
                            tipo="info",
                            acao_url="/perfil?tab=contrato"
                        )
                        inv()
                        st.success("✅ Colaborador notificado!")
                        st.rerun()
            with col_env2:
                if st.button("🔄 Regenerar Contrato",
                              key="btn_regen_ct",
                              use_container_width=True):
                    u_ct2 = _load_users_fresh()
                    mask  = u_ct2['Nome'] == nome_ct_sel
                    if mask.any():
                        for campo in ['Contrato_Gerado','Contrato_Data',
                                      'Contrato_b64','Contrato_Enviado',
                                      'Contrato_Enviado_Data']:
                            u_ct2.loc[mask, campo] = ''
                        save_db(u_ct2, "usuarios.csv")
                        inv()
                        st.rerun()

        # ── PASSO 3: Aguarda assinatura do colaborador ────────────
        if ct_enviado and not ct_assinado:
            st.info(
                "⏳ **Aguarda assinatura** — O colaborador recebeu o contrato "
                "e deve assinar fisicamente, fotografar e fazer upload na app."
            )

        # ── PASSO 4: Validar assinatura ───────────────────────────
        if ct_assinado and not ct_validado:
            st.markdown("#### ✅ Validar Assinatura do Colaborador")
            assin_b64 = row_ct.get('Contrato_Assinatura_b64','')
            if assin_b64:
                try:
                    assin_bytes = base64.b64decode(assin_b64)
                    st.download_button(
                        "📥 Ver contrato assinado pelo colaborador",
                        data=assin_bytes,
                        file_name=f"contrato_assinado_{nome_ct_sel.replace(' ','_')}.pdf",
                        mime="application/octet-stream",
                        key="btn_dl_assinado"
                    )
                except:
                    st.error("Erro ao processar o ficheiro.")

            col_val1, col_val2 = st.columns(2)
            with col_val1:
                if st.button("✅ Validar e Arquivar",
                              key="btn_validar_ct", type="primary",
                              use_container_width=True):
                    u_ct3 = _load_users_fresh()
                    mask  = u_ct3['Nome'] == nome_ct_sel
                    if mask.any():
                        u_ct3.loc[mask, 'Contrato_Validado_Admin'] = 'Sim'
                        u_ct3.loc[mask, 'Contrato_Validado_Data']  = \
                            datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(u_ct3, "usuarios.csv")
                        inv()
                        criar_notificacao(
                            destinatario=nome_ct_sel,
                            titulo="✅ Contrato Validado",
                            mensagem="O teu contrato foi validado e está arquivado.",
                            tipo="success",
                            acao_url="/perfil?tab=contrato"
                        )
                        log_audit(
                            usuario=admin_nome,
                            acao="VALIDAR_CONTRATO",
                            tabela="usuarios.csv",
                            registro_id=row_ct.get('ID',''),
                            detalhes=f"Contrato validado para {nome_ct_sel}",
                            ip=""
                        )
                        st.success("✅ Contrato arquivado!")
                        st.rerun()
            with col_val2:
                if st.button("❌ Recusar (pedir nova assinatura)",
                              key="btn_recusar_ct",
                              use_container_width=True):
                    u_ct3 = _load_users_fresh()
                    mask  = u_ct3['Nome'] == nome_ct_sel
                    if mask.any():
                        for campo in ['Contrato_Assinado',
                                      'Contrato_Assinatura_b64',
                                      'Contrato_Assinatura_Data']:
                            u_ct3.loc[mask, campo] = ''
                        save_db(u_ct3, "usuarios.csv")
                        criar_notificacao(
                            destinatario=nome_ct_sel,
                            titulo="⚠️ Assinatura Recusada",
                            mensagem="A assinatura do contrato foi recusada. "
                                     "Por favor, assina novamente e faz upload.",
                            tipo="error",
                            acao_url="/perfil?tab=contrato"
                        )
                        inv()
                        st.warning("Colaborador notificado para nova assinatura.")
                        st.rerun()

        # ── PASSO 5: Arquivo final ────────────────────────────────
        if ct_validado:
            st.success("✅ **Contrato arquivado e validado.**")
            ct_b64_f = row_ct.get('Contrato_b64','')
            if ct_b64_f:
                try:
                    ct_bytes_f = base64.b64decode(ct_b64_f)
                    st.download_button(
                        "📥 Descarregar contrato original",
                        data=ct_bytes_f,
                        file_name=f"contrato_final_{nome_ct_sel.replace(' ','_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument"
                             ".wordprocessingml.document",
                        key="btn_dl_ct_final"
                    )
                except:
                    pass

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — TEMPLATES & CONFIG
    # ════════════════════════════════════════════════════════════════
    with tab_template:
        st.markdown("### ⚙️ Template do Contrato")

        template_existe = _gcs_read_binary("contrato_template.docx") is not None
        if template_existe:
            st.success("✅ Template do contrato carregado no sistema.")
        else:
            st.warning("⚠️ Nenhum template carregado. "
                       "Faz upload abaixo para activar a geração automática.")

        st.markdown("#### 📤 Upload do Template")
        st.info(
            "O template deve ser um ficheiro `.docx` com os campos marcados como:\n"
            "`{{nome}}` `{{morada}}` `{{NIF}}` `{{NISS}}` "
            "`{{número de cartão de cidadão}}` `{{validade do cartão de cidadão}}` "
            "`{{categoria profissional}}` `{{local}}` `{{Cliente}}` `{{data}}`"
        )

        template_file = st.file_uploader(
            "Selecionar template .docx",
            type=["docx"],
            key="upload_template_ct"
        )
        if template_file:
            acao_label = "🔄 Substituir Template" if template_existe else "💾 Guardar Template"
            if st.button(acao_label,
                          key="btn_guardar_template",
                          type="primary", use_container_width=True):
                ok = _gcs_write_binary(
                    template_file.read(), "contrato_template.docx"
                )
                if ok:
                    st.success("✅ Template guardado no sistema!")
                    log_audit(
                        usuario=admin_nome,
                        acao="UPLOAD_TEMPLATE_CONTRATO",
                        tabela="GCS",
                        registro_id="contrato_template.docx",
                        detalhes="Template do contrato atualizado",
                        ip=""
                    )
                    st.rerun()
                else:
                    st.error("❌ Erro ao guardar o template.")

        if template_existe:
            st.markdown("---")
            st.markdown("#### 📥 Descarregar Template Atual")
            template_bytes = _gcs_read_binary("contrato_template.docx")
            if template_bytes:
                st.download_button(
                    "📥 Descarregar template atual",
                    data=template_bytes,
                    file_name="contrato_template.docx",
                    mime="application/vnd.openxmlformats-officedocument"
                         ".wordprocessingml.document",
                    key="btn_dl_template"
                )

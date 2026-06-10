import streamlit as st
import pandas as pd
import uuid, base64, json, unicodedata, re
from datetime import datetime, date, timedelta
from io import BytesIO

from core import (
    save_db, inv, load_db, log_audit, criar_notificacao,
    hp, _gcs_read, _gcs_write_binary, _gcs_read_binary,
    _fill_contrato_template, ICONS
)

# ── Tipos e cargos disponíveis ────────────────────────────────────────
TIPOS_USUARIO = ["Técnico","Instrumentista","Engenheiro","Chefe de Equipa",
                 "Secretariado","Armazém","Admin","Cliente"]
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
    "Secretariado": ["Secretária","Administrativo","Faturação","RH"],
    "Armazém":      ["Responsável de Armazém","Técnico de Armazém"],
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

# ── Constantes legais/fiscais para colaboradores_rh.csv ──────────────
ESTADO_CIVIL_OPTS    = ["Solteiro(a)","Casado(a)","União de Facto",
                        "Divorciado(a)","Viúvo(a)","Separado(a)"]
GENERO_OPTS          = ["Masculino","Feminino","Outro","Não especificado"]
MODALIDADE_HORARIO_OPTS = ["Tempo Inteiro","Tempo Parcial","Isenção de Horário",
                            "Trabalho por Turnos","Teletrabalho","Misto"]
TIPO_CONTRATO_OPTS   = ["A Termo Certo","A Termo Incerto","Sem Termo",
                        "Prestação de Serviços","Estágio Profissional","Outro"]
NIVEL_HABILITACOES_OPTS = [
    "Sem escolaridade","1º Ciclo (4ª classe)","2º Ciclo (6º ano)",
    "3º Ciclo (9º ano)","Ensino Secundário (12º ano)","Bacharelato",
    "Licenciatura","Mestrado","Doutoramento","Outro",
]
SITUACAO_PROFISSIONAL_OPTS = [
    "Quadro Permanente","Contrato a Termo Certo","Contrato a Termo Incerto",
    "Prestador de Serviços","Estagiário","Outro",
]
FORMA_PAGAMENTO_OPTS = ["Transferência Bancária","Numerário","Cheque","Outro"]
IRCT_OPTS            = ["IRCT 25989 – CCT Empresas Electrotécnicas",
                        "IRCT 5/2015 – CCT Metalúrgico","Outro","Não aplicável"]

CATEGORIAS_CCT_25989 = {
    "02069": "AJUDANTES DE FOGUEIRO",
    "02070": "ANALISTA DE INFORMÁTICA ASSISTENTE",
    "02996": "ANALISTA DE INFORMÁTICA ESTAGIÁRIO",
    "02071": "ANALISTA DE INFORMÁTICA PRINCIPAL",
    "02072": "ANALISTA DE INFORMÁTICA PROFISSIONAL",
    "11285": "ASSISTENTE ADMINISTRATIVO DE 1.ª",
    "11286": "ASSISTENTE ADMINISTRATIVO DE 2.ª",
    "11287": "ASSISTENTE ADMINISTRATIVO DE 3.ª",
    "43991": "ASSISTENTE ADMINISTRATIVO ESTAGIÁRIO ATÉ 2 ANOS",
    "23130": "ASSISTENTE ADMINISTRATIVO ESTAGIÁRIO DO 2.º ANO",
    "03236": "AUXILIAR DE ENFERMAGEM",
    "00159": "CHEFE DE EQUIPA",
    "00081": "CHEFE DE SECÇÃO",
    "00080": "CHEFE DE SERVIÇOS",
    "00411": "CHEFE DE VENDAS",
    "30112": "CHEFE DE VIGILÂNCIA",
    "01427": "CONTABILISTA",
    "00527": "CONTÍNUO",
    "02176": "COORDENADOR DE OPERADORES ESPECIALIZADOS",
    "00532": "COZINHEIRO",
    "38497": "EMPREGADO DE REFEITÓRIO/CAFETARIA",
    "00412": "EMPREGADO DE SERVIÇOS EXTERNOS",
    "00023": "ENCARREGADO",
    "02097": "ENCARREGADO DE LIMPEZA",
    "02098": "ENCARREGADO DE REFEITÓRIO OU CANTINA",
    "00184": "ENCARREGADO GERAL",
    "00542": "ENFERMEIRO",
    "44140": "ENGENHEIRO I-A / ESPECIALISTA I-A",
    "44141": "ENGENHEIRO I-B / ESPECIALISTA I-B",
    "44142": "ENGENHEIRO II / ESPECIALISTA II",
    "44143": "ENGENHEIRO III / ESPECIALISTA III",
    "44310": "ENGENHEIRO IV / ESPECIALISTA IV",
    "44145": "ENGENHEIRO V / ESPECIALISTA V",
    "44146": "ENGENHEIRO VI / ESPECIALISTA VI",
    "02021": "ESTAGIÁRIO RECEPCIONISTA",
    "02103": "EXPOSITOR DECORADOR",
    "02108": "GUARDA OU VIGILANTE",
    "00328": "INSPECTOR DE VENDAS",
    "00478": "MOTORISTA DE LIGEIROS",
    "00479": "MOTORISTA DE PESADOS",
    "35679": "OPERADOR DE INFORMÁTICA PRINCIPAL",
    "35678": "OPERADOR DE INFORMÁTICA PROFISSIONAL",
    "02150": "OPERADOR ESPECIALIZADO DE 1.ª",
    "02151": "OPERADOR ESPECIALIZADO DE 2.ª",
    "02152": "OPERADOR ESPECIALIZADO DE 3.ª",
    "43990": "OPERADOR ESPECIALIZADO SÉNIOR",
    "38498": "OPERADOR INFORMÁTICO ESTAGIÁRIO",
    "00490": "PORTEIRO",
    "02155": "PROFISSIONAL QUALIFICADO OFICIAL",
    "31323": "PROFISSIONAL QUALIFICADO PRATICANTE ATÉ 2 ANOS",
    "02158": "PROFISSIONAL QUALIFICADO PRÉ-OFICIAL 1.º E 2.º ANOS",
    "03106": "PROGRAMADOR DE INFORMÁTICA ASSISTENTE",
    "35680": "PROGRAMADOR DE INFORMÁTICA PRINCIPAL",
    "03108": "PROGRAMADOR DE INFORMÁTICA PROFISSIONAL",
    "38499": "PROGRAMADOR INFORMÁTICO ESTAGIÁRIO",
    "02163": "PROJECTISTA",
    "00387": "PROMOTOR DE VENDAS",
    "00388": "PROSPECTOR DE VENDAS",
    "02032": "RECEPCIONISTA DE 1.ª",
    "02033": "RECEPCIONISTA DE 2.ª",
    "95989": "RESIDUAL (inclui o ignorado)",
    "25963": "SECRETÁRIO(A)",
    "00044": "SERVENTE",
    "35677": "SUPERVISOR DE LOGÍSTICA",
    "11288": "TÉCNICO ADMINISTRATIVO",
    "02182": "TÉCNICO DE SERVIÇO SOCIAL",
    "43989": "TÉCNICO OPERACIONAL 1 E 2 ANOS",
    "43988": "TÉCNICO OPERACIONAL 3 E 4 ANOS",
    "43987": "TÉCNICO OPERACIONAL 5 E 6 ANOS",
    "43986": "TÉCNICO OPERACIONAL MAIS DE 6 ANOS",
    "43992": "TÉCNICO OPERACIONAL PRATICANTE ATÉ 2 ANOS",
    "40876": "TÉCNICO OPERACIONAL PRINCIPAL",
    "00503": "VENDEDOR",
}

PROFISSOES_CPP_CPS = {
    "74121": "Electricista de instalações",
    "74122": "Electricista de manutenção",
    "74123": "Electricista de redes e subestações",
    "74124": "Electromecânico",
    "74131": "Técnico de instalações eléctricas industriais",
    "74141": "Técnico de instrumentação e controlo",
    "74142": "Técnico de automação industrial",
    "74143": "Técnico de telecomunicações industriais",
    "21411": "Engenheiro Electrotécnico",
    "21412": "Engenheiro de Automação",
    "21413": "Engenheiro de Instrumentação",
    "31211": "Técnico de electrónica",
    "31221": "Técnico de electromecânica",
    "33411": "Técnico Administrativo",
    "43110": "Escriturário",
    "72111": "Serralheiro mecânico",
    "72121": "Soldador",
    "91110": "Indiferenciado / Servente",
}

# Colunas completas do colaboradores_rh.csv
COLS_RH = [
    "ID","Nome","NIF","NISS","Tipo","Cargo",
    "Salario_Base","Data_Inicio","Estado_Civil","N_Dependentes",
    "Banco_IBAN","Contrato","Ativo",
    "Genero","DataNasc","Naturalidade","Nacionalidade","Pais_Residencia",
    "CC","CC_Validade","Passaporte","Passaporte_Validade",
    "IRS_Escalao","IRS_Percentagem","Titular_Unico","Taxa_Retencao_IRS",
    "Isencao_IRS","Artigo_IRS",
    "Tipo_Contrato","Modalidade_Horario","Horas_Semana",
    "Contrato_Inicio","Contrato_Fim","Contrato_Indeterminado",
    "Periodo_Experimental","Periodo_Experimental_Fim",
    "Local_Trabalho","Funcao_Contratual",
    "Subsidio_Alimentacao","Subsidio_Ferias","Subsidio_Natal",
    "Premio_Producao","Outros_Complementos","Forma_Pagamento",
    "IBAN_Validado","SWIFT_BIC",
    "Nivel_Habilitacoes","Situacao_Profissional","Profissao_CPP",
    "Categoria_CCT","IRCT_Aplicavel","Vinculo_Empresa",
    "Reducao_Horario","Data_Ultima_Promocao","Antiguidade_Anos",
    "Nivel_Remuneratorio","Grau_Deficiencia","Deficiencia_Tipo",
    "Seg_Social_Cartao","Cartao_Prof_Num","Cartao_Prof_Validade",
    "Alvara_Num","Alvara_Validade",
]

# Mapeamento Eticadata → COLS_RH (nome coluna Eticadata: nome campo GestNow)
ETICADATA_MAP = {
    "Nome": "Nome",
    "NIF": "NIF",
    "N.º Segurança Social": "NISS",
    "Nº Segurança Social": "NISS",
    "BI/CC": "CC",
    "N.º Cartão Cidadão": "CC",
    "Validade CC": "CC_Validade",
    "Validade BI/CC": "CC_Validade",
    "Data Nascimento": "DataNasc",
    "Data Nasc.": "DataNasc",
    "Sexo": "Genero",
    "Estado Civil": "Estado_Civil",
    "Nº Dependentes": "N_Dependentes",
    "N.º Dependentes": "N_Dependentes",
    "IBAN": "Banco_IBAN",
    "Categoria": "Categoria_CCT",
    "Remuneração Base": "Salario_Base",
    "Salário Base": "Salario_Base",
    "Rem. Base": "Salario_Base",
    "Data Admissão": "Contrato_Inicio",
    "Data Início": "Contrato_Inicio",
    "Data Cessação": "Contrato_Fim",
    "Data Fim": "Contrato_Fim",
    "Tipo Contrato": "Tipo_Contrato",
    "Habilitações": "Nivel_Habilitacoes",
    "Profissão CPP": "Profissao_CPP",
    "CPP": "Profissao_CPP",
    "Local Trabalho": "Local_Trabalho",
    "Função": "Funcao_Contratual",
}

# Mapas de conversão de valores Eticadata → GestNow
_ETICA_GENERO   = {"M": "Masculino", "F": "Feminino",
                   "1": "Masculino", "2": "Feminino"}
_ETICA_EST_CIVIL = {
    "1": "Solteiro(a)", "2": "Casado(a)", "3": "Divorciado(a)",
    "4": "Viúvo(a)",    "5": "União de Facto", "6": "Separado(a)",
}
_ETICA_HABILITACOES = {
    "1": "Sem escolaridade",
    "2": "1º Ciclo (4ª classe)",
    "3": "2º Ciclo (6º ano)",
    "4": "3º Ciclo (9º ano)",
    "5": "Ensino Secundário (12º ano)",
    "6": "Bacharelato",
    "7": "Licenciatura",
    "8": "Mestrado",
    "9": "Doutoramento",
}
_ETICA_TIPO_CONTRATO = {
    "1": "Sem Termo",
    "2": "A Termo Certo",
    "3": "A Termo Incerto",
    "4": "Prestação de Serviços",
    "5": "Estágio Profissional",
}

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


def _load_rh_fresh() -> pd.DataFrame:
    """Lê colaboradores_rh.csv directamente do GCS, sem cache."""
    import time
    for attempt in range(3):
        try:
            buf = _gcs_read("colaboradores_rh.csv")
            if buf:
                df = pd.read_csv(buf, dtype=str, on_bad_lines='skip',
                                 encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].str.strip()
                for c in COLS_RH:
                    if c not in df.columns:
                        df[c] = ""
                return df.fillna("")
            time.sleep(0.3)
        except Exception:
            if attempt == 2:
                return pd.DataFrame(columns=COLS_RH)
            time.sleep(0.3)
    return pd.DataFrame(columns=COLS_RH)


def _sync_rh_csv(nome: str, updates: dict):
    """Aplica `updates` ao registo de `nome` em colaboradores_rh.csv.
    Cria linha nova se o colaborador ainda não existir."""
    rh = _load_rh_fresh()
    mask = (rh['Nome'] == nome) if 'Nome' in rh.columns and not rh.empty else pd.Series([], dtype=bool)
    if mask.any():
        for k, v in updates.items():
            rh.loc[mask, k] = v
    else:
        novo = {c: "" for c in COLS_RH}
        novo['Nome'] = nome
        novo.update(updates)
        rh = pd.concat([rh, pd.DataFrame([novo])], ignore_index=True)
    save_db(rh, "colaboradores_rh.csv")
    inv("colaboradores_rh.csv")


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

    # ── Painel de alertas de validade ─────────────────────────────────
    _today = date.today()
    _rh_alert = _load_rh_fresh()

    _VALIDADE_COLS = [
        ("CC_Validade",          "CC"),
        ("Passaporte_Validade",  "Passaporte"),
        ("Cartao_Prof_Validade", "Carta Prof."),
        ("Alvara_Validade",      "Alvará"),
    ]
    _CAMPOS_OBG = ["NIF","NISS","CC","CC_Validade","Banco_IBAN","Tipo_Contrato"]

    _n_exp, _n_prox, _n_ct, _n_inc = 0, 0, 0, 0
    _det_exp, _det_prox, _det_ct, _det_inc = [], [], [], []

    def _parse_date(s):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return None

    if not _rh_alert.empty:
        for _, _r in _rh_alert.iterrows():
            _nm = _r.get('Nome', '')
            for _col, _lbl in _VALIDADE_COLS:
                _v = _parse_date(_r.get(_col, ''))
                if _v:
                    if _v < _today:
                        _n_exp += 1
                        _det_exp.append(f"{_nm} — {_lbl} expirado em {_r.get(_col,'')}")
                    elif _v <= _today + timedelta(days=60):
                        _n_prox += 1
                        _det_prox.append(f"{_nm} — {_lbl} expira em {_r.get(_col,'')}")
            _fim = _parse_date(_r.get('Contrato_Fim', ''))
            if _fim and _r.get('Contrato_Indeterminado', '') != 'Sim':
                _days = (_fim - _today).days
                if _days <= 90:
                    _n_ct += 1
                    _det_ct.append(f"{_nm} — contrato termina em {_r.get('Contrato_Fim','')} ({_days}d)")
            _falta = [c for c in _CAMPOS_OBG if not _r.get(c, '')]
            if _falta:
                _n_inc += 1
                _det_inc.append(f"{_nm} — em falta: {', '.join(_falta)}")

    if _n_exp + _n_prox + _n_ct + _n_inc > 0:
        _ca1, _ca2, _ca3, _ca4 = st.columns(4)
        _ca1.metric("🔴 Expirados",   _n_exp)
        _ca2.metric("🟡 A expirar",   _n_prox)
        _ca3.metric("🟠 Contratos",   _n_ct)
        _ca4.metric("⚪ Incompletos", _n_inc)
        with st.expander("📋 Ver detalhes dos alertas"):
            if _det_exp:
                st.markdown("**🔴 Documentos Expirados**")
                for _d in _det_exp: st.markdown(f"- {_d}")
            if _det_prox:
                st.markdown("**🟡 A Expirar nos próximos 60 dias**")
                for _d in _det_prox: st.markdown(f"- {_d}")
            if _det_ct:
                st.markdown("**🟠 Contratos a Terminar (≤ 90 dias)**")
                for _d in _det_ct: st.markdown(f"- {_d}")
            if _det_inc:
                st.markdown("**⚪ Fichas Incompletas**")
                for _d in _det_inc: st.markdown(f"- {_d}")
        st.markdown("---")

    (tab_lista, tab_gestao, tab_dados_legais, tab_eticadata,
     tab_contrato, tab_template, tab_formacoes) = st.tabs([
        "👥 Colaboradores",
        "📋 Gestão Individual",
        "📋 Dados Legais",
        "📥 Importar Eticadata",
        "📄 Contratos",
        "⚙️ Templates & Config",
        "🎓 Formações",
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
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        log_audit(usuario=admin_nome,
                                  acao="CRIAR_COLABORADOR",
                                  tabela="usuarios.csv",
                                  registro_id=novo_id,
                                  detalhes=f"Criado: {novo_nome.strip()} "
                                           f"({novo_tipo} / {novo_cargo})",
                                  ip="")

                        st.success(f"✅ Colaborador **{novo_nome.strip()}** criado com sucesso!")
                        st.session_state['show_criar_colab'] = False
                        inv("usuarios.csv")
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
                inv("usuarios.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                st.success("✅ Campos bloqueados atualizados.")
                st.rerun()

        # ── Alterar Função e Password ─────────────────────────────
        st.markdown("---")
        st.markdown("#### ⚙️ Alterar Função / Password")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            tipos_opcoes = ["Técnico", "Chefe de Equipa", "Admin",
                            "Gestor", "Secretariado"]
            tipo_atual   = row.get("Tipo", "Técnico")
            idx_tipo     = tipos_opcoes.index(tipo_atual)                            if tipo_atual in tipos_opcoes else 0
            novo_tipo = st.selectbox("👤 Função (Tipo)",
                tipos_opcoes, index=idx_tipo, key="rh_novo_tipo")

        with col_f2:
            cargos_opcoes = ["Técnico", "Instrumentista", "Eletricista",
                             "Mecânico", "Chefe de Equipa", "Encarregado",
                             "Engenheiro", "QA/QC", "Admin", "Outro"]
            cargo_atual   = row.get("Cargo", "")
            idx_cargo     = cargos_opcoes.index(cargo_atual)                             if cargo_atual in cargos_opcoes else 0
            novo_cargo = st.selectbox("🏷️ Cargo",
                cargos_opcoes, index=idx_cargo, key="rh_novo_cargo")

        if st.button("💾 Guardar Função/Cargo",
                     key="btn_guardar_funcao", type="primary"):
            u_fn = _load_users_fresh()
            mk_fn = u_fn["Nome"] == nome_sel
            if mk_fn.any():
                u_fn.loc[mk_fn, "Tipo"]  = novo_tipo
                u_fn.loc[mk_fn, "Cargo"] = novo_cargo
                save_db(u_fn, "usuarios.csv")
                inv("usuarios.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                log_audit(usuario=st.session_state.get("user","admin"),
                          acao="ALTERAR_FUNCAO",
                          tabela="usuarios.csv",
                          registro_id=nome_sel,
                          detalhes=f"Tipo={novo_tipo}, Cargo={novo_cargo}")
                st.success(f"✅ Função actualizada: {novo_tipo} / {novo_cargo}")
                st.rerun()

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        with st.expander("🔐 Redefinir Password"):
            nova_pwd_admin = st.text_input(
                "Nova Password *", type="password", key="rh_nova_pwd_admin",
                placeholder="Mínimo 4 caracteres")
            conf_pwd_admin = st.text_input(
                "Confirmar Password *", type="password", key="rh_conf_pwd_admin")
            if st.button("🔐 Redefinir Password", key="btn_redef_pwd",
                         type="primary"):
                if not nova_pwd_admin.strip():
                    st.error("⚠️ Introduz uma nova password.")
                elif len(nova_pwd_admin.strip()) < 4:
                    st.error("⚠️ Mínimo 4 caracteres.")
                elif nova_pwd_admin != conf_pwd_admin:
                    st.error("⚠️ As passwords não coincidem.")
                else:
                    u_pw = _load_users_fresh()
                    mk_pw = u_pw["Nome"] == nome_sel
                    if mk_pw.any():
                        u_pw.loc[mk_pw, "Password"] = hp(nova_pwd_admin.strip())
                        save_db(u_pw, "usuarios.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        log_audit(usuario=st.session_state.get("user","admin"),
                                  acao="REDEFINIR_PASSWORD",
                                  tabela="usuarios.csv",
                                  registro_id=nome_sel,
                                  detalhes="Password redefinida pelo Admin")
                        st.success(f"✅ Password de {nome_sel} redefinida.")
                        st.rerun()

        # ── Remover ou Lista Negra ────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🚫 Remover Colaborador")

        st.markdown(
            "<div style='background:rgba(239,68,68,0.08);border-radius:10px;"
            "padding:12px 16px;border-left:3px solid #EF4444;margin-bottom:12px;'>"
            "<p style='color:#FCA5A5;font-size:0.82rem;margin:0;'>"
            "⚠️ <b>Atenção:</b> Estas acções são permanentes ou têm impacto "
            "no acesso do colaborador à plataforma.</p></div>",
            unsafe_allow_html=True
        )

        col_rm1, col_rm2 = st.columns(2)

        with col_rm1:
            st.markdown(
                "<p style='color:#F1F5F9;font-weight:700;margin:0 0 6px;'>"
                "🗑️ Remover Permanentemente</p>"
                "<p style='color:#64748B;font-size:0.78rem;'>"
                "Apaga o colaborador de forma definitiva. "
                "Registos de horas são mantidos.</p>",
                unsafe_allow_html=True)
            confirmar_rm = st.text_input(
                f"Escreve '{nome_sel}' para confirmar",
                key="rh_confirm_rm", placeholder="Nome completo")
            if st.button("🗑️ Remover Definitivamente",
                         key="btn_remover_def"):
                if confirmar_rm.strip() != nome_sel:
                    st.error("⚠️ Nome não coincide. Operação cancelada.")
                else:
                    u_rm = _load_users_fresh()
                    u_rm = u_rm[u_rm["Nome"] != nome_sel]
                    save_db(u_rm, "usuarios.csv")
                    inv("usuarios.csv")
                    from core import _cached_load_all
                    _cached_load_all.clear()
                    log_audit(usuario=st.session_state.get("user","admin"),
                              acao="REMOVER_COLABORADOR",
                              tabela="usuarios.csv",
                              registro_id=nome_sel,
                              detalhes="Removido permanentemente pelo Admin")
                    st.success(f"✅ {nome_sel} removido da plataforma.")
                    st.session_state.pop("rh_colaborador_sel", None)
                    st.rerun()

        with col_rm2:
            st.markdown(
                "<p style='color:#F1F5F9;font-weight:700;margin:0 0 6px;'>"
                "⛔ Adicionar à Lista Negra</p>"
                "<p style='color:#64748B;font-size:0.78rem;'>"
                "Bloqueia o acesso mas mantém o registo. "
                "Fica vísivel na Lista Negra com observações.</p>",
                unsafe_allow_html=True)
            obs_ln = st.text_area(
                "Motivo / Observações *",
                key="rh_obs_ln", height=68,
                placeholder="Ex: Abandono de posto, comportamento inadequado...")
            if st.button("⛔ Enviar para Lista Negra",
                         key="btn_lista_negra"):
                if not obs_ln.strip():
                    st.error("⚠️ Indica o motivo.")
                else:
                    # 1. Bloquear utilizador (Tipo → Bloqueado)
                    u_ln = _load_users_fresh()
                    mk_ln = u_ln["Nome"] == nome_sel
                    if mk_ln.any():
                        u_ln.loc[mk_ln, "Tipo"]          = "Bloqueado"
                        u_ln.loc[mk_ln, "Lista_Negra"]   = "Sim"
                        u_ln.loc[mk_ln, "Lista_Negra_Data"] =                             datetime.now().strftime("%d/%m/%Y %H:%M")
                        u_ln.loc[mk_ln, "Lista_Negra_Obs"] = obs_ln.strip()
                        u_ln.loc[mk_ln, "Lista_Negra_Por"] =                             st.session_state.get("user", "admin")
                        save_db(u_ln, "usuarios.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        log_audit(
                            usuario=st.session_state.get("user","admin"),
                            acao="LISTA_NEGRA",
                            tabela="usuarios.csv",
                            registro_id=nome_sel,
                            detalhes=f"Lista negra: {obs_ln[:100]}")
                        st.success(f"⛔ {nome_sel} adicionado à lista negra.")
                        st.rerun()

        # ── Ver Lista Negra ───────────────────────────────────────
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        u_all_ln = _load_users_fresh()
        ln_users = u_all_ln[
            u_all_ln.get("Lista_Negra", pd.Series(["Não"]*len(u_all_ln))) == "Sim"
        ] if not u_all_ln.empty and "Lista_Negra" in u_all_ln.columns else pd.DataFrame()

        if not ln_users.empty:
            with st.expander(f"📋 Lista Negra ({len(ln_users)} colaborador(es))",
                             expanded=False):
                for _, ln_row in ln_users.iterrows():
                    ln_nome = ln_row.get("Nome","")
                    ln_data = ln_row.get("Lista_Negra_Data","")
                    ln_por  = ln_row.get("Lista_Negra_Por","")
                    ln_obs  = ln_row.get("Lista_Negra_Obs","")
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin-bottom:8px;"
                        f"border-left:4px solid #EF4444;'>"
                        f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:flex-start;'>"
                        f"<div>"
                        f"<p style='color:#F1F5F9;font-weight:700;margin:0;'>"
                        f"⛔ {ln_nome}</p>"
                        f"<p style='color:#64748B;font-size:0.75rem;margin:2px 0;'>"
                        f"Adicionado por {ln_por} em {ln_data}</p>"
                        f"<p style='color:#94A3B8;font-size:0.8rem;margin:4px 0 0;'>"
                        f"{ln_obs}</p>"
                        f"</div></div></div>",
                        unsafe_allow_html=True
                    )
                    # Opção de reactivar
                    if st.button(f"🔓 Reactivar {ln_nome}",
                                 key=f"btn_reactivar_{ln_nome}"):
                        u_ra = _load_users_fresh()
                        mk_ra = u_ra["Nome"] == ln_nome
                        if mk_ra.any():
                            u_ra.loc[mk_ra, "Tipo"]        = "Técnico"
                            u_ra.loc[mk_ra, "Lista_Negra"] = "Não"
                            u_ra.loc[mk_ra, "Lista_Negra_Data"] = ""
                            u_ra.loc[mk_ra, "Lista_Negra_Obs"]  = ""
                            u_ra.loc[mk_ra, "Lista_Negra_Por"]  = ""
                            save_db(u_ra, "usuarios.csv")
                            inv("usuarios.csv")
                            from core import _cached_load_all
                            _cached_load_all.clear()
                            log_audit(
                                usuario=st.session_state.get("user","admin"),
                                acao="REACTIVAR_COLABORADOR",
                                tabela="usuarios.csv",
                                registro_id=ln_nome,
                                detalhes="Reactivado da lista negra")
                            st.success(f"✅ {ln_nome} reactivado.")
                            st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 3 — DADOS LEGAIS
    # ════════════════════════════════════════════════════════════════
    with tab_dados_legais:
        st.markdown("### 📋 Dados Legais e Fiscais")

        _u_dl = _load_users_fresh()
        if _u_dl.empty:
            st.info("Sem colaboradores.")
        else:
            _nomes_dl = _u_dl['Nome'].tolist()
            _sel_dl_def = st.session_state.get('rh_colaborador_sel', _nomes_dl[0])
            _idx_dl = _nomes_dl.index(_sel_dl_def) if _sel_dl_def in _nomes_dl else 0
            _nome_dl = st.selectbox("Colaborador", _nomes_dl,
                                    index=_idx_dl, key="dl_colab_sel")
            st.session_state['rh_colaborador_sel'] = _nome_dl

            _rh_dl = _load_rh_fresh()
            _mask_dl = (_rh_dl['Nome'] == _nome_dl) if not _rh_dl.empty else pd.Series([], dtype=bool)
            _row_dl  = _rh_dl[_mask_dl].iloc[0] if _mask_dl.any() else pd.Series(dtype=str)

            def _v(campo, default=""):
                return _row_dl.get(campo, default) if not _row_dl.empty else default

            def _opt_idx(opts, val):
                return opts.index(val) if val in opts else 0

            # ── 1. Identificação Legal ────────────────────────────
            with st.expander("🪪 Identificação Legal", expanded=True):
                with st.form("dl_form_ident"):
                    _c1, _c2, _c3 = st.columns(3)
                    with _c1:
                        _genero   = st.selectbox("Género", GENERO_OPTS,
                            index=_opt_idx(GENERO_OPTS, _v("Genero")), key="dl_genero")
                        _datanasc = st.text_input("Data Nascimento (DD/MM/AAAA)",
                            value=_v("DataNasc"), key="dl_datanasc")
                        _nat  = st.text_input("Naturalidade", value=_v("Naturalidade"), key="dl_nat")
                    with _c2:
                        _nac  = st.text_input("Nacionalidade", value=_v("Nacionalidade"), key="dl_nac")
                        _pais = st.text_input("País Residência", value=_v("Pais_Residencia"), key="dl_pais")
                        _nif  = st.text_input("NIF", value=_v("NIF"), key="dl_nif")
                    with _c3:
                        _niss = st.text_input("NISS", value=_v("NISS"), key="dl_niss")
                        _cc   = st.text_input("Nº Cartão Cidadão", value=_v("CC"), key="dl_cc")
                        _ccval= st.text_input("Validade CC (DD/MM/AAAA)",
                            value=_v("CC_Validade"), key="dl_ccval")
                    _c4, _c5 = st.columns(2)
                    with _c4:
                        _pass_num = st.text_input("Passaporte", value=_v("Passaporte"), key="dl_pass")
                        _pass_val = st.text_input("Validade Passaporte (DD/MM/AAAA)",
                            value=_v("Passaporte_Validade"), key="dl_passval")
                    with _c5:
                        _est_civil = st.selectbox("Estado Civil", ESTADO_CIVIL_OPTS,
                            index=_opt_idx(ESTADO_CIVIL_OPTS, _v("Estado_Civil")), key="dl_estcivil")
                        _n_dep = st.text_input("Nº Dependentes", value=_v("N_Dependentes"), key="dl_ndep")
                    if st.form_submit_button("💾 Guardar Identificação",
                                             use_container_width=True, type="primary"):
                        _sync_rh_csv(_nome_dl, {
                            "Genero": _genero, "DataNasc": _datanasc,
                            "Naturalidade": _nat, "Nacionalidade": _nac,
                            "Pais_Residencia": _pais, "NIF": _nif, "NISS": _niss,
                            "CC": _cc, "CC_Validade": _ccval,
                            "Passaporte": _pass_num, "Passaporte_Validade": _pass_val,
                            "Estado_Civil": _est_civil, "N_Dependentes": _n_dep,
                        })
                        st.success("✅ Identificação guardada.")
                        st.rerun()

            # ── 2. Dados Fiscais ──────────────────────────────────
            with st.expander("🏦 Dados Fiscais"):
                with st.form("dl_form_fiscal"):
                    _c1, _c2 = st.columns(2)
                    with _c1:
                        _irs_esc  = st.text_input("Escalão IRS", value=_v("IRS_Escalao"), key="dl_irs_esc")
                        _irs_pct  = st.text_input("Taxa IRS (%)", value=_v("IRS_Percentagem"), key="dl_irs_pct")
                        _tit_unico= st.selectbox("Titular Único", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Titular_Unico"))
                                  if _v("Titular_Unico") in ["","Sim","Não"] else 0,
                            key="dl_tit_unico")
                    with _c2:
                        _taxa_ret = st.text_input("Taxa Retenção (%)", value=_v("Taxa_Retencao_IRS"), key="dl_taxa_ret")
                        _isencao  = st.selectbox("Isenção IRS", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Isencao_IRS"))
                                  if _v("Isencao_IRS") in ["","Sim","Não"] else 0,
                            key="dl_isencao")
                        _artigo_irs = st.text_input("Artigo IRS", value=_v("Artigo_IRS"), key="dl_artigo")
                    if st.form_submit_button("💾 Guardar Dados Fiscais",
                                             use_container_width=True, type="primary"):
                        _sync_rh_csv(_nome_dl, {
                            "IRS_Escalao": _irs_esc, "IRS_Percentagem": _irs_pct,
                            "Titular_Unico": _tit_unico, "Taxa_Retencao_IRS": _taxa_ret,
                            "Isencao_IRS": _isencao, "Artigo_IRS": _artigo_irs,
                        })
                        st.success("✅ Dados fiscais guardados.")
                        st.rerun()

            # ── 3. Dados Contratuais ──────────────────────────────
            with st.expander("📄 Dados Contratuais"):
                with st.form("dl_form_contrato"):
                    _c1, _c2, _c3 = st.columns(3)
                    with _c1:
                        _tp_ct = st.selectbox("Tipo Contrato", TIPO_CONTRATO_OPTS,
                            index=_opt_idx(TIPO_CONTRATO_OPTS, _v("Tipo_Contrato")), key="dl_tpct")
                        _mod_hr = st.selectbox("Modalidade Horário", MODALIDADE_HORARIO_OPTS,
                            index=_opt_idx(MODALIDADE_HORARIO_OPTS, _v("Modalidade_Horario")), key="dl_modhr")
                        _hrs_sem = st.text_input("Horas/Semana", value=_v("Horas_Semana"), key="dl_hrsem")
                    with _c2:
                        _ct_ini  = st.text_input("Data Início Contrato (DD/MM/AAAA)",
                            value=_v("Contrato_Inicio"), key="dl_ctini")
                        _ct_fim  = st.text_input("Data Fim Contrato (DD/MM/AAAA)",
                            value=_v("Contrato_Fim"), key="dl_ctfim")
                        _ct_ind  = st.selectbox("Contrato Indeterminado", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Contrato_Indeterminado"))
                                  if _v("Contrato_Indeterminado") in ["","Sim","Não"] else 0,
                            key="dl_ctind")
                    with _c3:
                        _pe      = st.text_input("Período Experimental (meses)",
                            value=_v("Periodo_Experimental"), key="dl_pe")
                        _pe_fim  = st.text_input("Fim Período Exp. (DD/MM/AAAA)",
                            value=_v("Periodo_Experimental_Fim"), key="dl_pefim")
                        _local_t = st.text_input("Local de Trabalho",
                            value=_v("Local_Trabalho"), key="dl_local")
                    _func_ct = st.text_input("Função Contratual",
                        value=_v("Funcao_Contratual"), key="dl_func")
                    if st.form_submit_button("💾 Guardar Dados Contratuais",
                                             use_container_width=True, type="primary"):
                        _sync_rh_csv(_nome_dl, {
                            "Tipo_Contrato": _tp_ct, "Modalidade_Horario": _mod_hr,
                            "Horas_Semana": _hrs_sem, "Contrato_Inicio": _ct_ini,
                            "Contrato_Fim": _ct_fim, "Contrato_Indeterminado": _ct_ind,
                            "Periodo_Experimental": _pe, "Periodo_Experimental_Fim": _pe_fim,
                            "Local_Trabalho": _local_t, "Funcao_Contratual": _func_ct,
                        })
                        st.success("✅ Dados contratuais guardados.")
                        st.rerun()

            # ── 4. Remuneração e Pagamento ────────────────────────
            with st.expander("💰 Remuneração e Pagamento"):
                with st.form("dl_form_rem"):
                    _c1, _c2, _c3 = st.columns(3)
                    with _c1:
                        _sal_b  = st.text_input("Salário Base (€)",
                            value=_v("Salario_Base"), key="dl_salb")
                        _sub_al = st.text_input("Subsídio Alimentação (€)",
                            value=_v("Subsidio_Alimentacao"), key="dl_subal")
                        _sub_fe = st.text_input("Subsídio Férias (€)",
                            value=_v("Subsidio_Ferias"), key="dl_subfe")
                    with _c2:
                        _sub_na = st.text_input("Subsídio Natal (€)",
                            value=_v("Subsidio_Natal"), key="dl_subna")
                        _prem   = st.text_input("Prémio Produção (€)",
                            value=_v("Premio_Producao"), key="dl_prem")
                        _outros = st.text_input("Outros Complementos",
                            value=_v("Outros_Complementos"), key="dl_outros")
                    with _c3:
                        _forma_pag = st.selectbox("Forma Pagamento", FORMA_PAGAMENTO_OPTS,
                            index=_opt_idx(FORMA_PAGAMENTO_OPTS, _v("Forma_Pagamento")), key="dl_fpag")
                        _iban_val  = st.selectbox("IBAN Validado", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("IBAN_Validado"))
                                  if _v("IBAN_Validado") in ["","Sim","Não"] else 0,
                            key="dl_ibanval")
                        _swift = st.text_input("SWIFT/BIC",
                            value=_v("SWIFT_BIC"), key="dl_swift")
                    if st.form_submit_button("💾 Guardar Remuneração",
                                             use_container_width=True, type="primary"):
                        _sync_rh_csv(_nome_dl, {
                            "Salario_Base": _sal_b, "Subsidio_Alimentacao": _sub_al,
                            "Subsidio_Ferias": _sub_fe, "Subsidio_Natal": _sub_na,
                            "Premio_Producao": _prem, "Outros_Complementos": _outros,
                            "Forma_Pagamento": _forma_pag, "IBAN_Validado": _iban_val,
                            "SWIFT_BIC": _swift,
                        })
                        st.success("✅ Remuneração guardada.")
                        st.rerun()

            # ── 5. Profissional / Relatório Único ─────────────────
            with st.expander("📊 Profissional & Relatório Único"):
                with st.form("dl_form_prof"):
                    _c1, _c2 = st.columns(2)
                    with _c1:
                        _nivel_hab = st.selectbox("Nível Habilitações", NIVEL_HABILITACOES_OPTS,
                            index=_opt_idx(NIVEL_HABILITACOES_OPTS, _v("Nivel_Habilitacoes")), key="dl_nhab")
                        _sit_prof  = st.selectbox("Situação Profissional", SITUACAO_PROFISSIONAL_OPTS,
                            index=_opt_idx(SITUACAO_PROFISSIONAL_OPTS, _v("Situacao_Profissional")), key="dl_sitprof")
                        _cpp_opts  = [""] + [f"{k} – {v}" for k,v in PROFISSOES_CPP_CPS.items()]
                        _cpp_val   = _v("Profissao_CPP")
                        _cpp_match = next((o for o in _cpp_opts if o.startswith(_cpp_val)), "")
                        _cpp_idx   = _cpp_opts.index(_cpp_match) if _cpp_match in _cpp_opts else 0
                        _profissao = st.selectbox("Profissão (CPP 2010)", _cpp_opts,
                            index=_cpp_idx, key="dl_cpp")
                        _cct_opts  = [""] + [f"{k} – {v}" for k,v in CATEGORIAS_CCT_25989.items()]
                        _cct_val   = _v("Categoria_CCT")
                        _cct_match = next((o for o in _cct_opts if o.startswith(_cct_val)), "")
                        _cct_idx   = _cct_opts.index(_cct_match) if _cct_match in _cct_opts else 0
                        _cat_cct   = st.selectbox("Categoria CCT", _cct_opts,
                            index=_cct_idx, key="dl_catcct")
                    with _c2:
                        _irct = st.selectbox("IRCT Aplicável", IRCT_OPTS,
                            index=_opt_idx(IRCT_OPTS, _v("IRCT_Aplicavel")), key="dl_irct")
                        _vinculo = st.text_input("Vínculo Empresa",
                            value=_v("Vinculo_Empresa"), key="dl_vinculo")
                        _red_hr  = st.selectbox("Redução Horário", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Reducao_Horario"))
                                  if _v("Reducao_Horario") in ["","Sim","Não"] else 0,
                            key="dl_redhr")
                        _dt_prom = st.text_input("Data Última Promoção (DD/MM/AAAA)",
                            value=_v("Data_Ultima_Promocao"), key="dl_dtprom")
                        _ant_anos= st.text_input("Antiguidade (anos)",
                            value=_v("Antiguidade_Anos"), key="dl_antanos")
                        _n_rem   = st.text_input("Nível Remuneratório",
                            value=_v("Nivel_Remuneratorio"), key="dl_nrem")
                    _c3, _c4 = st.columns(2)
                    with _c3:
                        _grau_def = st.text_input("Grau Deficiência (%)",
                            value=_v("Grau_Deficiencia"), key="dl_graudef")
                        _def_tipo = st.text_input("Tipo Deficiência",
                            value=_v("Deficiencia_Tipo"), key="dl_deftipo")
                    with _c4:
                        _cartao_prof_num = st.text_input("Nº Cartão Profissional",
                            value=_v("Cartao_Prof_Num"), key="dl_cpnum")
                        _cartao_prof_val = st.text_input("Validade Cartão Prof. (DD/MM/AAAA)",
                            value=_v("Cartao_Prof_Validade"), key="dl_cpval")
                    if st.form_submit_button("💾 Guardar Dados Profissionais",
                                             use_container_width=True, type="primary"):
                        _profissao_code = _profissao.split(" – ")[0] if " – " in _profissao else _profissao
                        _cat_cct_code   = _cat_cct.split(" – ")[0]   if " – " in _cat_cct   else _cat_cct
                        _sync_rh_csv(_nome_dl, {
                            "Nivel_Habilitacoes": _nivel_hab, "Situacao_Profissional": _sit_prof,
                            "Profissao_CPP": _profissao_code, "Categoria_CCT": _cat_cct_code,
                            "IRCT_Aplicavel": _irct, "Vinculo_Empresa": _vinculo,
                            "Reducao_Horario": _red_hr, "Data_Ultima_Promocao": _dt_prom,
                            "Antiguidade_Anos": _ant_anos, "Nivel_Remuneratorio": _n_rem,
                            "Grau_Deficiencia": _grau_def, "Deficiencia_Tipo": _def_tipo,
                            "Cartao_Prof_Num": _cartao_prof_num, "Cartao_Prof_Validade": _cartao_prof_val,
                        })
                        st.success("✅ Dados profissionais guardados.")
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — IMPORTAR ETICADATA
    # ════════════════════════════════════════════════════════════════
    with tab_eticadata:
        st.markdown("### 📥 Importar Lista de Trabalhadores (Eticadata)")
        st.info(
            "Exporta do Eticadata o ficheiro **`Lista_Trabalhadores.csv`** "
            "(separador `;`, codificação UTF-8 com BOM) e faz upload aqui. "
            "O match é feito pelo Nome com `usuarios.csv`. "
            "Colaboradores sem match são criados automaticamente."
        )

        # ── Tabelas de conversão de valores Eticadata ─────────────
        _E_SEXO = {"0": "Masculino", "1": "Feminino"}
        _E_EST_CIVIL = {
            "1": "Solteiro(a)", "2": "Casado(a)", "3": "Viúvo(a)",
            "4": "Divorciado(a)", "5": "União de facto",
            "6": "Separado(a) judicialmente",
        }
        _E_NAC = {
            "0": "Português", "2": "Brasileiro",
            "3": "Outro UE/EEE", "4": "Extracomunitário",
        }
        _E_NIVEL_QUAL = {
            "0": "", "1": "Quadro superior", "2": "Quadro médio",
            "3": "Encarregado contramestre mestre e chefe de equipa",
            "4": "Profissional altamente qualificado",
            "5": "Profissional qualificado",
            "6": "Profissional semi-qualificado especializado",
            "7": "Profissional não qualificado indiferenciado",
            "8": "Estagiário praticante e aprendiz",
        }
        _E_DOC_TIPO = {
            "CC": "Cartão de Cidadão", "PASS": "Passaporte",
            "TRT": "Título de Residência Temporária",
            "TRP": "Título de Residência Permanente",
            "CRFCUNET": "Cartão Registo Cidadão UE/EEE",
        }
        _FIXED_RH = {
            # Campos para Dados Legais (nomes canónicos GestNow)
            "IRCT_Aplicavel":             "IRCT 25989 – CCT Empresas Electrotécnicas",
            "Situacao_Profissional":      "Trabalhador por Conta de Outrem",
            "Categoria_CCT":              "02155",
            "Profissao_CPP":              "74124",
            # Campos extra Eticadata (referência)
            "IRCT_Codigo":                "25989",
            "IRCT_Descricao":             "CCT - Empresas Electrotécnicas",
            "IRCT_Aplicabilidade":        "04 - Acto de Gestão",
            "Modo_Remuneracao":           "Mensal",
            "Duracao_Tempo_Trabalho":     "1 - Adaptabilidade por regulamentação colectiva (RU:10)",
            "Tipo_Horario":               "Normal Fixo",
            "Pensionista":                "Não",
            "Regime_Reforma":             "1 - Segurança Social",
            "Organizacao_Tempo_Trabalho": "1 - Trabalho diurno",
            "Categoria_Profissional_Cod": "02155",
            "Categoria_Profissional_Desc":"PROFISSIONAL QUALIFICADO OFICIAL",
            "Profissao_CPP_Cod":          "74124",
            "Profissao_CPP_Desc":         "Electromecânico, electricista e outros instaladores de máquinas e equipamentos eléctricos",
        }

        def _etica_strip_date(s):
            """Remove parte horária — '29/03/2023 00:00' → '29/03/2023'."""
            s = str(s).strip()
            return s.split(" ")[0] if " " in s else s

        def _etica_map_row(er):
            """Converte linha Eticadata em (rh_dict, users_if_empty_dict, users_always_dict, chefe_bool)."""
            rh = {}
            rh["Eticadata_ID"]           = er.get("intCodigo", "")
            rh["Genero"]                 = _E_SEXO.get(er.get("bitSexo", ""), "")
            rh["Estado_Civil"]           = _E_EST_CIVIL.get(er.get("intEstadoCivil", ""), "")
            rh["Salario_Base"]           = er.get("fltVencActual", "")
            rh["Data_Admissao"]          = _etica_strip_date(er.get("dtmAdmissao", ""))
            # Nomes canónicos GestNow (coincidem com Dados Legais)
            rh["Contrato_Inicio"]        = _etica_strip_date(er.get("dtmInicioContr", ""))
            _fim_c                       = _etica_strip_date(er.get("dtmFimContr", ""))
            rh["Contrato_Fim"]           = _fim_c
            rh["Tipo_Contrato"]          = "Sem Termo" if not _fim_c else "A Termo Certo"
            rh["Horas_Semana"]           = er.get("fltHorasSemanais", "")
            rh["Subsidio_Alimentacao"]   = er.get("fltSubAlimentacao", "")
            rh["Banco_Nome"]             = er.get("strAbrevBanco", "")
            rh["Num_Utente"]             = er.get("strNumUtente", "")
            rh["SWIFT_BIC"]              = er.get("strBic", "")
            rh["Servico_Financas"]       = er.get("strCodRepFinancas", "")
            rh["Naturalidade"]           = er.get("strNaturalidade", "")
            rh["Banco_Empresa_Pagamento"]= er.get("strCodContaEmpresa", "")
            rh["Nacionalidade"]          = _E_NAC.get(er.get("intCodNacionalidade", ""), "")
            rh["Nivel_Qualificacao"]     = _E_NIVEL_QUAL.get(er.get("intNivelQualificacao", ""), "")
            _tdoc                        = er.get("strTypDocId", "")
            rh["Tipo_Doc_ID"]            = _E_DOC_TIPO.get(_tdoc, _tdoc)
            # Campos partilhados com usuarios.csv — também gravados aqui para
            # que fiquem visíveis na tab "Dados Legais" (lê de colaboradores_rh.csv)
            rh["CC"]                     = er.get("strNumBI", "")
            rh["CC_Validade"]            = _etica_strip_date(er.get("dtmValidadeBI", ""))
            rh["NISS"]                   = er.get("strNumSegSocial", "")
            rh["Email"]                  = er.get("strEmail", "")
            rh["Morada"]                 = er.get("strMorada1GRH", "")
            rh["Localidade"]             = er.get("strLocalidadeGRH", "")
            rh["Codigo_Postal"]          = er.get("strCodPostalGRH", "")
            rh.update(_FIXED_RH)

            u_if_empty = {
                "Email":        er.get("strEmail", ""),
                "CC":           er.get("strNumBI", ""),
                "CC_Validade":  _etica_strip_date(er.get("dtmValidadeBI", "")),
                "NISS":         er.get("strNumSegSocial", ""),
                "Morada":       er.get("strMorada1GRH", ""),
                "Localidade":   er.get("strLocalidadeGRH", ""),
                "Codigo_Postal":er.get("strCodPostalGRH", ""),
                "Banco_IBAN":   er.get("strIban", ""),
            }
            u_always = {
                "PrecoHora":  er.get("CA_Valor_Hora", ""),
                "Local_Obra": er.get("CA_Obra", ""),
            }
            chefe = er.get("CA_ChefedeEquipa", "").strip() == "1"
            return rh, u_if_empty, u_always, chefe

        # ── Upload → guardar imediatamente em session_state ────────
        _eti_ukey = f"eti_uploader_{st.session_state.get('eti_upload_key', 0)}"
        _eti_file = st.file_uploader(
            "Selecionar CSV do Eticadata (sep=;, UTF-8 BOM)",
            type=["csv"], key=_eti_ukey
        )
        if _eti_file is not None:
            try:
                _eti_raw = pd.read_csv(
                    _eti_file, sep=";", dtype=str,
                    encoding="utf-8-sig", on_bad_lines='skip'
                )
                _eti_raw.columns = _eti_raw.columns.str.strip()
                _eti_raw = _eti_raw.replace("NULL", "").fillna("")
                for _ec in _eti_raw.select_dtypes(include='object').columns:
                    _eti_raw[_ec] = _eti_raw[_ec].str.strip()
                st.session_state['eticadata_df'] = _eti_raw
            except Exception as _e:
                st.error(f"❌ Erro ao ler o ficheiro: {_e}")

        if 'eticadata_result' in st.session_state:
            _res = st.session_state['eticadata_result']
            st.success(
                f"✅ Importação concluída! "
                f"**{_res['n_act']}** actualizados, "
                f"**{_res['n_new']}** novos criados, "
                f"**{_res['n_campos']}** campos preenchidos."
            )
            if _res.get('novos'):
                st.markdown("#### 🆕 Passwords geradas — guardar agora!")
                st.warning(
                    "⚠️ Estas passwords só são mostradas uma vez. "
                    "Comunica-as aos colaboradores antes de fechar."
                )
                for _nc in _res['novos']:
                    st.markdown(f"- **{_nc['Nome']}** → `{_nc['Password']}`")
            if st.button("✓ Já guardei — fechar relatório",
                         key="imp_fechar_relatorio"):
                del st.session_state['eticadata_result']
                st.rerun()
        elif 'eticadata_df' not in st.session_state:
            st.info("Faz upload do CSV para começar.")
        else:
            _eti_df = st.session_state['eticadata_df']

            _ecol_h, _ecol_btn = st.columns([5, 1])
            with _ecol_h:
                st.success(f"✅ Ficheiro carregado: **{len(_eti_df)}** registos, "
                           f"**{len(_eti_df.columns)}** colunas.")
            with _ecol_btn:
                if st.button("🗑️ Limpar", key="imp_limpar"):
                    del st.session_state['eticadata_df']
                    st.session_state['eti_upload_key'] = st.session_state.get('eti_upload_key', 0) + 1
                    st.rerun()

            with st.expander("👁️ CSV original (primeiras 5 linhas)"):
                st.dataframe(_eti_df.head(), use_container_width=True)

            # ── Detectar coluna Nome no CSV ────────────────────────
            _nome_col_eti = None
            for _cn in ("Nome", "strNome", "NomeFuncionario", "nome", "NOME"):
                if _cn in _eti_df.columns:
                    _nome_col_eti = _cn
                    break

            if _nome_col_eti is None:
                st.error(
                    "❌ Coluna 'Nome' não encontrada no CSV. "
                    f"Colunas disponíveis: `{'`, `'.join(_eti_df.columns.tolist())}`"
                )
            else:
                # ── Match por Nome com usuarios.csv ───────────────
                _u_eti = _load_users_fresh()
                _nomes_exact = set(
                    _u_eti['Nome'].dropna().unique()
                ) if not _u_eti.empty and 'Nome' in _u_eti.columns else set()

                def _norm_nome(s):
                    s = str(s).strip().lower()
                    s = unicodedata.normalize('NFD', s)
                    s = s.encode('ascii', 'ignore').decode('ascii')
                    return re.sub(r'\s+', ' ', s)

                _nomes_ci  = {n.strip().lower(): n for n in _nomes_exact}
                _nomes_acc = {_norm_nome(n): n for n in _nomes_exact}

                def _find_match_eti(nome_eti):
                    n = str(nome_eti).strip()
                    if n in _nomes_exact:                  # a. exacto
                        return n
                    ci = _nomes_ci.get(n.lower())
                    if ci:                                 # b. case-insensitive
                        return ci
                    acc = _nomes_acc.get(_norm_nome(n))
                    if acc:                                # c. sem acentos
                        return acc
                    # d. primeiro + último nome normalizados
                    parts = _norm_nome(n).split()
                    if len(parts) >= 2:
                        fl = f"{parts[0]} {parts[-1]}"
                        for gn in _nomes_exact:
                            gp = _norm_nome(gn).split()
                            if len(gp) >= 2 and f"{gp[0]} {gp[-1]}" == fl:
                                return gn
                    return None

                # ── Preview com status de match ────────────────────
                _prev_rows = []
                for _, _er in _eti_df.iterrows():
                    _nem = _er.get(_nome_col_eti, "")
                    _ng  = _find_match_eti(_nem)
                    _rh_p, _, _, _ = _etica_map_row(_er)
                    _prev_rows.append({
                        "Status":         "✅ Match" if _ng else "⚠️ Sem match",
                        "Nome Eticadata": _nem,
                        "Nome GestNow":   _ng or "—",
                        "Salário Base":   _rh_p.get("Salario_Base", ""),
                        "Tipo Contrato":  _rh_p.get("Tipo_Contrato", ""),
                        "Data Admissão":  _rh_p.get("Data_Admissao", ""),
                        "Género":         _rh_p.get("Genero", ""),
                        "Nacionalidade":  _rh_p.get("Nacionalidade", ""),
                    })

                _prev_df   = pd.DataFrame(_prev_rows)
                _n_match   = int((_prev_df["Status"] == "✅ Match").sum())
                _n_nomatch = int((_prev_df["Status"] == "⚠️ Sem match").sum())

                _mc1, _mc2 = st.columns(2)
                _mc1.metric("✅ Com match", _n_match)
                _mc2.metric("⚠️ Sem match", _n_nomatch)

                st.markdown("#### 📋 Pré-visualização — todos os colaboradores")
                st.dataframe(_prev_df, use_container_width=True, height=400)

                if _n_nomatch > 0:
                    with st.expander(f"🆕 {_n_nomatch} sem match — serão criados como novos"):
                        for _sn in _prev_df[
                            _prev_df["Status"] == "⚠️ Sem match"
                        ]["Nome Eticadata"].tolist():
                            st.markdown(f"- `{_sn}`")

                st.markdown("---")

                _btn_label = (
                    f"🚀 Importar: {_n_match} actualiz."
                    + (f" + {_n_nomatch} novos" if _n_nomatch else "")
                )
                if _n_match == 0 and _n_nomatch == 0:
                    st.warning("⚠️ Nenhum registo encontrado no CSV.")
                else:
                    if st.button(
                        _btn_label,
                        key="imp_importar", type="primary",
                        use_container_width=True
                    ):
                        _df_rh    = _load_rh_fresh()
                        _df_users = _load_users_fresh()
                        _n_act    = 0
                        _n_new    = 0
                        _n_campos = 0
                        _novos_criados = []

                        for _, _er in _eti_df.iterrows():
                            _nem   = _er.get(_nome_col_eti, "")
                            _ng    = _find_match_eti(_nem)
                            _rh_v, _u_emp, _u_alw, _chefe = _etica_map_row(_er)

                            if _ng:
                                # Actualizar colaboradores_rh.csv
                                _mrh = (
                                    (_df_rh['Nome'] == _ng)
                                    if 'Nome' in _df_rh.columns and not _df_rh.empty
                                    else pd.Series([], dtype=bool)
                                )
                                if _mrh.any():
                                    for _k, _vv in _rh_v.items():
                                        if _vv != "":
                                            if _k not in _df_rh.columns:
                                                _df_rh[_k] = ""
                                            _df_rh.loc[_mrh, _k] = _vv
                                            _n_campos += 1
                                else:
                                    _novo_rh = {c: "" for c in COLS_RH}
                                    _novo_rh['Nome'] = _ng
                                    _novo_rh.update({k: v for k, v in _rh_v.items() if v})
                                    _df_rh = pd.concat(
                                        [_df_rh, pd.DataFrame([_novo_rh])],
                                        ignore_index=True
                                    )

                                # Actualizar usuarios.csv
                                _mu = (
                                    (_df_users['Nome'] == _ng)
                                    if not _df_users.empty and 'Nome' in _df_users.columns
                                    else pd.Series([], dtype=bool)
                                )
                                if _mu.any():
                                    for _k, _vv in _u_emp.items():
                                        if _vv:
                                            if _k not in _df_users.columns:
                                                _df_users[_k] = ""
                                            if not str(_df_users.loc[_mu, _k].iloc[0]).strip():
                                                _df_users.loc[_mu, _k] = _vv
                                                _n_campos += 1
                                    for _k, _vv in _u_alw.items():
                                        if _vv:
                                            if _k not in _df_users.columns:
                                                _df_users[_k] = ""
                                            _df_users.loc[_mu, _k] = _vv
                                            _n_campos += 1
                                    if _chefe and 'Tipo' in _df_users.columns:
                                        _tipo_cur = str(_df_users.loc[_mu, 'Tipo'].iloc[0]).strip()
                                        if _tipo_cur not in ("Admin","Secretariado","Armazém","Cliente"):
                                            _df_users.loc[_mu, 'Tipo'] = "Chefe de Equipa"
                                _n_act += 1

                            else:
                                # Criar novo colaborador
                                _partes = str(_nem).strip().split()
                                _primeiro = _partes[0].capitalize() if _partes else "User"
                                _pwd_plain = f"{_primeiro}1234"
                                _novo_id   = str(uuid.uuid4())[:8].upper()

                                _novo_u = {
                                    "ID":              _novo_id,
                                    "Nome":            _nem,
                                    "Tipo":            "Chefe de Equipa" if _chefe else "Técnico",
                                    "Cargo":           "Técnico Instrumentação",
                                    "Password":        hp(_pwd_plain),
                                    "PDFs_Validados":  "Não",
                                    "Perfil_Completo": "",
                                    "Data_Criacao":    datetime.now().strftime("%d/%m/%Y %H:%M"),
                                }
                                for _k, _vv in _u_emp.items():
                                    if _vv:
                                        _novo_u[_k] = _vv
                                for _k, _vv in _u_alw.items():
                                    if _vv:
                                        _novo_u[_k] = _vv
                                _df_users = pd.concat(
                                    [_df_users, pd.DataFrame([_novo_u])],
                                    ignore_index=True
                                )

                                _novo_rh = {c: "" for c in COLS_RH}
                                _novo_rh['Nome'] = _nem
                                _novo_rh.update({k: v for k, v in _rh_v.items() if v})
                                _df_rh = pd.concat(
                                    [_df_rh, pd.DataFrame([_novo_rh])],
                                    ignore_index=True
                                )
                                _novos_criados.append({"Nome": _nem, "Password": _pwd_plain})
                                _n_new += 1

                        save_db(_df_rh, "colaboradores_rh.csv")
                        save_db(_df_users, "usuarios.csv")
                        inv("colaboradores_rh.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        log_audit(
                            usuario=admin_nome,
                            acao="IMPORTAR_ETICADATA",
                            tabela="colaboradores_rh.csv+usuarios.csv",
                            registro_id="batch",
                            detalhes=(f"Actualizados: {_n_act}, "
                                      f"Novos: {_n_new}, "
                                      f"Campos: {_n_campos}"),
                            ip=""
                        )
                        st.session_state['eticadata_result'] = {
                            'n_act': _n_act, 'n_new': _n_new,
                            'n_campos': _n_campos, 'novos': _novos_criados,
                        }
                        del st.session_state['eticadata_df']
                        # incrementar chave força o file_uploader a renderizar
                        # sem ficheiro no próximo rerun — evita recriar eticadata_df
                        st.session_state['eti_upload_key'] = st.session_state.get('eti_upload_key', 0) + 1
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 5 — CONTRATOS
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
                                    inv("usuarios.csv")
                                    from core import _cached_load_all
                                    _cached_load_all.clear()
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
                            inv("usuarios.csv")
                            from core import _cached_load_all
                            _cached_load_all.clear()
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
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
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
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
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
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
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
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
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
    # TAB 6 — TEMPLATES & CONFIG
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

        if template_existe:
            st.warning(
                "⚠️ Já existe um template. Fazer upload de um novo **substitui** o atual."
            )

        template_file = st.file_uploader(
            "Selecionar novo template .docx",
            type=["docx"],
            key="upload_template_ct"
        )
        if template_file:
            acao_label = "🔄 Substituir Template Atual" if template_existe \
                         else "💾 Guardar Template"
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

    # ════════════════════════════════════════════════════════════════
    # TAB 7 — FORMAÇÕES
    # ════════════════════════════════════════════════════════════════
    with tab_formacoes:
        from mod_admin_formacoes import render_formacoes
        render_formacoes(users, obras_db)

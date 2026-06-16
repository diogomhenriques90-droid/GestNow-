"""
mod_criar_admin.py — GESTNOW v3
Utilitário para criar o primeiro utilizador Admin ou repor credenciais.
Acesso apenas quando não existe nenhum Admin no sistema,
ou via flag GESTNOW_SETUP=true nas variáveis de ambiente do Cloud Run.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

from core import save_db, load_db, hp, _gcs_read, _gcs_write


# Colunas padrão do usuarios.csv
_COLS_USERS = [
    "Nome", "Password", "PIN", "Tipo", "Cargo", "Email", "Telefone",
    "Morada", "Localidade", "Concelho", "Codigo_Postal",
    "Contacto_Emergencia", "Nome_Emergencia", "Grau_Parentesco",
    "IBAN", "NIF", "Data_Nascimento", "Data_Entrada",
    "PrecoHora", "PrecoHoraStatus", "PrecoHoraData",
    "PDFs_Validados", "PDFs_Validacao_Data",
    "Contrato_Enviado", "Contrato_b64",
    "Contrato_Assinado", "Contrato_Assinatura_b64", "Contrato_Assinatura_Data",
    "Contrato_Validado_Admin",
    "Campos_Bloqueados", "Ativo", "Foto",
    "Criado_Em", "Criado_Por",
]


def _modo_setup_permitido() -> bool:
    """Permite acesso se variável de ambiente GESTNOW_SETUP=true
    OU se não existir nenhum utilizador do tipo Admin no sistema."""
    # Flag de ambiente (definir temporariamente no Cloud Run)
    if os.environ.get("GESTNOW_SETUP", "").lower() == "true":
        return True
    # Sem admins no sistema
    try:
        buf = _gcs_read("usuarios.csv")
        if buf is None:
            return True  # ficheiro não existe ainda
        df = pd.read_csv(buf, dtype=str, on_bad_lines='skip',
                         encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        if df.empty or 'Tipo' not in df.columns:
            return True
        admins = df[df['Tipo'].str.strip() == 'Admin']
        return admins.empty
    except:
        return True  # em caso de erro, permite acesso


def render_criar_admin():
    """Página de setup/criação de Admin — chamada pelo app.py quando necessário."""

    st.markdown("""
    <style>
    .stApp { background:#0F172A !important; }
    .main .block-container { padding-top:2rem !important; max-width:520px; }
    h1,h2,h3 { color:#F1F5F9 !important; }
    p,div,span,label { color:#CBD5E1; }
    .stTextInput>div>div>input {
        background:#1E293B !important; color:#F1F5F9 !important;
        border:1px solid #334155 !important; border-radius:10px !important;
    }
    .stSelectbox>div>div>div {
        background:#1E293B !important; color:#F1F5F9 !important;
        border:1px solid #334155 !important;
    }
    .stButton>button[kind="primary"] {
        background:#DC2626 !important; color:white !important;
        border:none !important; border-radius:12px !important;
        font-weight:700 !important; height:48px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Verificar se o acesso é permitido ─────────────────────────
    if not _modo_setup_permitido():
        st.error("⛔ Acesso negado. Já existe um Admin no sistema.")
        st.info("Para repor credenciais, define a variável de ambiente "
                "`GESTNOW_SETUP=true` no Cloud Run e reinicia o serviço.")
        st.stop()

    # ── Cabeçalho ─────────────────────────────────────────────────
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1E293B,#0F172A);
        padding:28px;border-radius:16px;margin-bottom:24px;
        border:1px solid rgba(220,38,38,0.4);text-align:center;'>
        <p style='font-size:2.5rem;margin:0 0 8px;'>⚡</p>
        <h2 style='color:#F1F5F9;margin:0;font-size:1.4rem;'>
            GESTNOW v3 — Setup Inicial</h2>
        <p style='color:#64748B;margin:8px 0 0;font-size:0.85rem;'>
            Criação do utilizador Administrador</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<div style='background:rgba(245,158,11,0.1);border-left:3px solid "
        "#F59E0B;border-radius:8px;padding:12px 16px;margin-bottom:20px;'>"
        "<p style='color:#FCD34D;font-size:0.82rem;margin:0;'>"
        "⚠️ Este ecrã só está disponível enquanto não existir um Admin "
        "no sistema. Após criar o Admin, este acesso é bloqueado automaticamente."
        "</p></div>",
        unsafe_allow_html=True
    )

    # ── Formulário ────────────────────────────────────────────────
    with st.form("form_criar_admin", clear_on_submit=False):

        st.markdown(
            "<p style='color:#64748B;font-size:0.72rem;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.08em;margin:0 0 12px;'>"
            "👤 Dados do Administrador</p>",
            unsafe_allow_html=True
        )

        nome = st.text_input(
            "Nome completo",
            placeholder="Ex: João Silva",
            key="ca_nome"
        )

        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input(
                "Email",
                placeholder="admin@empresa.pt",
                key="ca_email"
            )
        with col2:
            telefone = st.text_input(
                "Telefone",
                placeholder="912 345 678",
                key="ca_tel"
            )

        st.markdown(
            "<hr style='border:none;border-top:1px solid #1E293B;margin:12px 0;'>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<p style='color:#64748B;font-size:0.72rem;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.08em;margin:0 0 12px;'>"
            "🔐 Credenciais de Acesso</p>",
            unsafe_allow_html=True
        )

        col3, col4 = st.columns(2)
        with col3:
            password  = st.text_input(
                "Password", type="password", key="ca_pw"
            )
        with col4:
            password2 = st.text_input(
                "Confirmar Password", type="password", key="ca_pw2"
            )

        pin = st.text_input(
            "PIN (4 dígitos numéricos)",
            max_chars=4,
            placeholder="0000",
            key="ca_pin"
        )

        st.markdown(
            "<hr style='border:none;border-top:1px solid #1E293B;margin:12px 0;'>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<p style='color:#64748B;font-size:0.72rem;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.08em;margin:0 0 12px;'>"
            "🏢 Perfil</p>",
            unsafe_allow_html=True
        )

        col5, col6 = st.columns(2)
        with col5:
            tipo = st.selectbox(
                "Tipo de Utilizador",
                ["Admin", "Gestor"],
                key="ca_tipo"
            )
        with col6:
            cargo = st.text_input(
                "Cargo",
                value="Administrador",
                key="ca_cargo"
            )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        submeter = st.form_submit_button(
            "🚀 Criar Administrador",
            use_container_width=True,
            type="primary"
        )

    # ── Processamento ─────────────────────────────────────────────
    if submeter:
        erros = []

        if not nome.strip():
            erros.append("Nome é obrigatório.")
        if not password.strip():
            erros.append("Password é obrigatória.")
        elif len(password.strip()) < 4:
            erros.append("Password deve ter pelo menos 4 caracteres.")
        elif password.strip() != password2.strip():
            erros.append("As passwords não coincidem.")
        if pin.strip() and (len(pin.strip()) != 4 or not pin.strip().isdigit()):
            erros.append("PIN deve ter exactamente 4 dígitos numéricos.")

        if erros:
            for e in erros:
                st.error(f"⚠️ {e}")
        else:
            try:
                # Carregar utilizadores existentes
                buf = _gcs_read("usuarios.csv")
                if buf:
                    df_users = pd.read_csv(
                        buf, dtype=str, on_bad_lines='skip',
                        encoding='utf-8-sig'
                    )
                    df_users.columns = df_users.columns.str.strip()
                    df_users = df_users.fillna("")
                else:
                    df_users = pd.DataFrame(columns=_COLS_USERS)

                # Garantir todas as colunas existem
                for col in _COLS_USERS:
                    if col not in df_users.columns:
                        df_users[col] = ""

                # Verificar se nome já existe
                if not df_users.empty and \
                   nome.strip() in df_users['Nome'].values:
                    st.error(
                        f"⚠️ Já existe um utilizador com o nome '{nome.strip()}'."
                    )
                    st.stop()

                # Criar novo registo
                novo = {col: "" for col in _COLS_USERS}
                novo.update({
                    "Nome":           nome.strip(),
                    "Password":       hp(password.strip()),
                    "PIN":            pin.strip() if pin.strip() else "0000",
                    "Tipo":           tipo,
                    "Cargo":          cargo.strip(),
                    "Email":          email.strip(),
                    "Telefone":       telefone.strip(),
                    "Ativo":          "Sim",
                    "Campos_Bloqueados": "[]",
                    "Criado_Em":      datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Criado_Por":     "SETUP",
                    "PrecoHora":      "0.0",
                    "PrecoHoraStatus":"",
                    "PDFs_Validados": "Não",
                    "Contrato_Enviado":"Não",
                    "Contrato_Assinado":"Não",
                    "Contrato_Validado_Admin":"Não",
                })

                df_novo   = pd.DataFrame([novo])
                df_users  = pd.concat([df_users, df_novo], ignore_index=True)

                # Garantir ordem das colunas — preservar colunas extra do
                # ficheiro vivo (ex.: Funcao, Categoria_Operacional, Contrato_*)
                # em vez de as descartar com um reindex à lista fixa.
                for col in _COLS_USERS:
                    if col not in df_users.columns:
                        df_users[col] = ""
                _extra = [c for c in df_users.columns if c not in _COLS_USERS]
                df_users = df_users[_COLS_USERS + _extra]

                save_db(df_users, "usuarios.csv")

                st.success(
                    f"✅ Administrador **{nome.strip()}** criado com sucesso!"
                )
                st.markdown(
                    "<div style='background:rgba(16,185,129,0.1);"
                    "border-left:3px solid #10B981;border-radius:8px;"
                    "padding:14px 16px;margin-top:12px;'>"
                    "<p style='color:#6EE7B7;font-size:0.85rem;margin:0;'>"
                    "✅ Pode agora fazer login com as credenciais criadas.<br>"
                    "🔒 Este ecrã de setup ficará automaticamente bloqueado."
                    "</p></div>",
                    unsafe_allow_html=True
                )
                st.balloons()

            except Exception as e:
                st.error(f"❌ Erro ao criar administrador: {e}")

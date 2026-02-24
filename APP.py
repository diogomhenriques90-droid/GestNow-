import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. Configuração de Página e Estilo
st.set_page_config(page_title="GestNow Admin", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    .stButton>button { border-radius: 12px; font-weight: bold; height: 3.5em; width: 100%; background-color: #1A1A1A; color: white; }
    .login-header { text-align: center; padding: 20px; color: #1A1A1A; }
    </style>
    """, unsafe_allow_html=True)

# 2. Inicialização de Estados
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# 3. ECRÃ DE LOGIN (SIMPLIFICADO AO MÁXIMO)
if not st.session_state.autenticado:
    st.markdown("<h1 class='login-header'>GestNow Login</h1>", unsafe_allow_html=True)
    
    user_input = st.text_input("Utilizador").strip().lower()
    pass_input = st.text_input("Palavra-passe", type="password").strip()
    
    if st.button("ENTRAR"):
        # VERIFICAÇÃO DIRETA SEM DEPENDER DE FICHEIROS
        if user_input == "admin" and pass_input == "DeltaPlus2026":
            st.session_state.autenticado = True
            st.session_state.user = "Admin"
            st.rerun()
        else:
            st.error("Credenciais incorretas. Tenta novamente.")
    st.stop()

# 4. SE CHEGOU AQUI, ESTÁ LOGADO - CARREGAR DADOS
def safe_save(df, f):
    df.to_csv(f, index=False)

def safe_load(f, cols):
    if os.path.exists(f):
        try:
            return pd.read_csv(f, dtype=str)
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

obras_db = safe_load("obras_lista.csv", ["Obra"])
frentes_db = safe_load("frentes_lista.csv", ["Obra", "Frente"])
registos_db = safe_load("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status"])

# 5. PAINEL ADMIN
st.title(f"Bem-vindo, {st.session_state.user}")

tab1, tab2 = st.tabs(["🏗️ Configurar Obras", "📋 Registos"])

with tab1:
    st.subheader("Adicionar Obra/Frente")
    with st.form("form_obra"):
        nova_obra = st.text_input("Nome da Obra")
        nova_frente = st.text_input("Frente de Trabalho")
        if st.form_submit_button("GRAVAR"):
            if nova_obra and nova_frente:
                o_df = pd.concat([obras_db, pd.DataFrame([{"Obra": nova_obra}])]).drop_duplicates()
                f_df = pd.concat([frentes_db, pd.DataFrame([{"Obra": nova_obra, "Frente": nova_frente}])]).drop_duplicates()
                safe_save(o_df, "obras_lista.csv")
                safe_save(f_df, "frentes_lista.csv")
                st.success("Configuração guardada!")
                st.rerun()

with tab2:
    st.subheader("Histórico de Registos")
    st.dataframe(registos_db, use_container_width=True)

if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.rerun()

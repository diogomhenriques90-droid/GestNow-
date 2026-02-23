import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 1. Configuração da Página
st.set_page_config(page_title="GestNow", page_icon="🎯", layout="wide")

# 2. BLOQUEIO DAS FERRAMENTAS STREAMLIT (Interface Limpa)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stStatusWidget"] {visibility: hidden;}
    .main { background-color: #f5f7f9; }
    .stButton>button { 
        border-radius: 5px; 
        height: 3em; 
        background-color: #004b87; 
        color: white; 
        font-weight: bold; 
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def carregar_csv(ficheiro, colunas):
    if os.path.exists(ficheiro):
        return pd.read_csv(ficheiro)
    return pd.DataFrame(columns=colunas)

def guardar_csv(df, ficheiro):
    df.to_csv(ficheiro, index=False)

def calcular_horas(row):
    try:
        fmt = '%H:%M'
        tdelta = datetime.strptime(row['Saída'], fmt) - datetime.strptime(row['Entrada'], fmt)
        return round(tdelta.total_seconds() / 3600, 2)
    except:
        return 0

# --- INICIALIZAÇÃO DE DADOS ---
df_users = carregar_csv("usuarios.csv", ["Nome", "Password", "Tipo"])

# ALTERAÇÃO: Password de Admin definida como DeltaPlus2026
if df_users.empty:
    df_users = pd.DataFrame([{"Nome": "Admin", "Password": "DeltaPlus2026", "Tipo": "Admin"}])
    guardar_csv(df_users, "usuarios.csv")

df_obras = carregar_csv("obras.csv", ["Nome"])
df_registos = carregar_csv("registos_completos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída"])

if not df_registos.empty:
    df_registos['Horas'] = df_registos.apply(calcular_horas, axis=1)

# --- SISTEMA DE LOGIN ---
if 'user' not in st.session_state: st.session_state['user'] = None

if st.session_state['user'] is None:
    st.image("https://images.unsplash.com/photo-1581092334651-ddf26d9a1930?auto=format&fit=crop&q=80&w=1000", use_container_width=True)
    st.title("GestNow")
    with st.form("login"):
        u = st.text_input("Utilizador")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Entrar"):
            user_match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
            if not user_match.empty:
                st.session_state['user'] = u
                st.session_state['tipo'] = user_match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso negado. Verifique os dados.")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.title("GestNow")
if st.sidebar.button("Sair"):
    st.session_state['user'] = None
    st.rerun()

# --- ÁREA COLABORADOR ---
if st.session_state['tipo'] == "Colaborador":
    st.header(f"📍 Ponto: {st.session_state['user']}")
    with st.container(border=True):
        d = st.

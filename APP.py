import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- CONFIGURAÇÃO DE ELITE ---
st.set_page_config(page_title="GestNow | Comando Central", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #00D2FF; }
    .stButton>button { background-color: #00D2FF; color: #0A192F; font-weight: bold; border-radius: 5px; height: 3em; width: 100%; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #112240; border-radius: 5px; color: white; padding: 10px; }
    input, select, textarea { background-color: #112240 !important; color: #00D2FF !important; border: 1px solid #1E3A5F !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE DADOS ---
def engine(f, col):
    try:
        if os.path.exists(f): return pd.read_csv(f)
    except: os.remove(f)
    return pd.DataFrame(columns=col)

def save(df, f): df.to_csv(f, index=False)

# Bases de Dados (Recuperação de Âmbito)
users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Relatorio"])

# --- LOGIN (DIOGO MASTER KEY) ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>GESTNOW</h1>", unsafe_allow_html=True)
    u = st.text_input("Utilizador").lower().strip()
    p = st.text_input("Palavra-Passe", type="password")
    if st.button("AUTENTICAR"):
        if (u == "diogo" or u == "rafael correia") and (p == "rafael2026" or p == "123"):
            st.session_state.user, st.session_state.tipo = u, "Admin"
            st.rerun()
        match = users[(users['Nome'].str.lower() == u) & (users['Password'].astype(str) == p)]
        if not match.empty:
            st.session_state.user, st.session_state.tipo = u, match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado.")
    st.stop()

# --- PAINEL DE COMANDO ---
st.sidebar.title(f"👤 {st.session_state.user.upper()}")

if st.session_state.tipo == "Admin":
    st.title("📊 Painel de Monitorização e Gestão")
    t1, t2, t3, t4 = st.tabs(["👥 Colaboradores", "🏗️ Unidades", "📋 Registos", "📥 Exportar"])

    with t1:
        st.subheader("Gestão de Equipa")
        col1, col2 = st.columns([1, 2])
        with col1:
            nu = st.text_input("Novo Nome")
            np = st.text_input("Nova Senha")
            if st.button("Adicionar Colaborador"):
                users = pd.concat([users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": "Colaborador"}])])
                save(users, "usuarios.csv"); st.success("Adicionado!"); st.rerun()
        with col2:
            st.write("Equipa Ativa")
            st.dataframe(users, use_container_width=True)
            rem_u = st.selectbox("Remover Colaborador", ["-- Selecionar --"] + users['Nome'].tolist())
            if st.button("Eliminar"):
                users = users[users['Nome'] != rem_u]
                save(users, "usuarios.csv"); st.rerun()

    with t2:
        st.subheader("Gestão de Unidades de Instrumentação")
        col3, col4 = st.columns([1, 2])
        with col3:
            no = st.text_input("ID Nova Unidade")
            if st.button("Adicionar Unidade"):
                obras = pd.concat([obras, pd.DataFrame([{"Nome": no}])])
                save(obras, "obras.csv"); st.success("Unidade Gravada!"); st.rerun()
        with col4:
            st.write("Unidades no Terreno")
            st.dataframe(obras, use_container_width=True)
            rem_o = st.selectbox("Remover Unidade", ["-- Selecionar --"] + obras['Nome'].tolist())
            if st.button("Arquivar Unidade"):
                obras = obras[obras['Nome'] != rem_o]
                save(obras, "obras.csv"); st.rerun()

    with t3:
        st.dataframe(registos, use_container_width=True)

    with t4:
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: registos.to_excel(w, index=False)
            st.download_button("📥 DESCARREGAR EXCEL PARA REUNIÃO", buf.getvalue(), "GestNow_Relatorio.xlsx")

else: # MODO TÉCNICO
    st.title("📝 Registo Técnico")
    with st.form("input"):
        un = st.selectbox("Unidade", ["-- Selecionar --"] + obras['Nome'].tolist())
        rel = st.text_area("Notas Técnicas")
        if st.form_submit_button("SUBMETER"):
            novo = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Técnico": st.session_state.user, "Unidade": un, "Relatorio": rel}])
            novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
            st.success("Transmitido com Sucesso!")

if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

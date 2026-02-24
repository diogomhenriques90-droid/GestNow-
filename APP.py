import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- CONFIGURAÇÃO DE ALTA PERFORMANCE ---
st.set_page_config(page_title="GestNow | Comando Central", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #00D2FF; }
    .stButton>button { background-color: #00D2FF; color: #0A192F; font-weight: bold; border-radius: 5px; height: 3em; width: 100%; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #112240; border-radius: 5px; color: white; padding: 10px; }
    input, select, textarea { background-color: #112240 !important; color: #00D2FF !important; border: 1px solid #1E3A5F !important; }
    .stDataFrame { background-color: #112240; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE DE DADOS ROBUSTA (EINSTEIN/PMBOK) ---
def engine(f, col):
    try:
        if os.path.exists(f): 
            df = pd.read_csv(f)
            return df if not df.empty else pd.DataFrame(columns=col)
    except: pass
    return pd.DataFrame(columns=col)

def save(df, f): 
    df.to_csv(f, index=False)

# Inicialização de Bases
users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Relatorio"])

# Criar Admin de Segurança se vazio
if users.empty:
    users = pd.DataFrame([{"Nome": "diogo", "Password": "123", "Tipo": "Admin"}])
    save(users, "usuarios.csv")

# --- SISTEMA DE LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>GESTNOW</h1>", unsafe_allow_html=True)
    u = st.text_input("Utilizador").lower().strip()
    p = st.text_input("Palavra-Passe", type="password")
    if st.button("ENTRAR NO COMANDO"):
        # Chave Mestra Diogo
        if (u == "diogo" or u == "rafael correia") and (p == "rafael2026" or p == "123"):
            st.session_state.user, st.session_state.tipo = u, "Admin"
            st.rerun()
        match = users[(users['Nome'].str.lower() == u) & (users['Password'].astype(str) == p)]
        if not match.empty:
            st.session_state.user, st.session_state.tipo = u, match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado.")
    st.stop()

# --- INTERFACE DE PODER (UPGRADE TOTAL) ---
st.sidebar.title(f"👤 {st.session_state.user.upper()}")

if st.session_state.tipo == "Admin":
    st.title("🛰️ Dashboard de Gestão Estratégica")
    t1, t2, t3, t4 = st.tabs(["👥 Colaboradores", "🏗️ Unidades/Obras", "📋 Registos", "📥 Exportar"])

    with t1:
        st.subheader("Upgrade de Equipa")
        c1, c2 = st.columns([1, 2])
        with c1:
            nu = st.text_input("Nome do Colaborador")
            np = st.text_input("Senha de Acesso")
            nt = st.selectbox("Nível", ["Colaborador", "Admin"])
            if st.button("Adicionar à Equipa"):
                users = pd.concat([users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": nt}])]).drop_duplicates()
                save(users, "usuarios.csv"); st.success("Técnico Ativado!"); st.rerun()
        with c2:
            st.dataframe(users, use_container_width=True)
            u_rem = st.selectbox("Eliminar Colaborador", ["-- Selecionar --"] + users['Nome'].tolist())
            if st.button("Remover da Base de Dados"):
                users = users[users['Nome'] != u_rem]
                save(users, "usuarios.csv"); st.rerun()

    with t2:
        st.subheader("Controlo de Unidades de Instrumentação")
        c3, c4 = st.columns([1, 2])
        with c3:
            no = st.text_input("ID da Nova Unidade")
            if st.button("Criar Unidade"):
                obras = pd.concat([obras, pd.DataFrame([{"Nome": no}])]).drop_duplicates()
                save(obras, "obras.csv"); st.success("Unidade Ativa!"); st.rerun()
        with c4:
            st.dataframe(obras, use_container_width=True)
            o_rem = st.selectbox("Eliminar Unidade", ["-- Selecionar --"] + obras['Nome'].tolist())
            if st.button("Eliminar Obra"):
                obras = obras[obras['Nome'] != o_rem]
                save(obras, "obras.csv"); st.rerun()

    with t3:
        st.subheader("Logs de Operação")
        st.dataframe(registos, use_container_width=True)
        if st.button("Limpar Todos os Registos"):
            save(pd.DataFrame(columns=["Data", "Técnico", "Unidade", "Relatorio"]), "registos.csv")
            st.rerun()

    with t4:
        st.subheader("Relatórios para Chefia")
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: registos.to_excel(w, index=False)
            st.download_button("📥 DESCARREGAR EXCEL DE ELITE", buf.getvalue(), "GestNow_Relatorio.xlsx")

else: # MODO TÉCNICO (REGISTO DIRETO)
    st.title("📝 Terminal Técnico")
    with st.form("input"):
        un = st.selectbox("Unidade / Obra", ["-- Selecionar --"] + obras['Nome'].tolist())
        rel = st.text_area("Relatório de Conformidade Técnica")
        if st.form_submit_button("SUBMETER PARA BASE DE DADOS"):
            if un != "-- Selecionar --":
                novo = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Técnico": st.session_state.user, "Unidade": un, "Relatorio": rel}])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("Dados transmitidos com sucesso!")

if st.sidebar.button("Terminar Sessão"):
    st.session_state.user = None
    st.rerun()

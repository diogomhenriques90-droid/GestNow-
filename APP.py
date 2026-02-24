import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE ELITE ---
st.set_page_config(page_title="GestNow | Precision Control", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #00D2FF; }
    .stButton>button { 
        background-color: #00D2FF; color: #0A192F; font-weight: bold; 
        border-radius: 5px; width: 100%; border: none; height: 3.5em;
    }
    input, select, textarea { background-color: #112240 !important; color: #00D2FF !important; border: 1px solid #1E3A5F !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #112240; border-radius: 5px; color: white; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS ---
def engine(f, colunas):
    try:
        if os.path.exists(f):
            df = pd.read_csv(f)
            return df if not df.empty else pd.DataFrame(columns=colunas)
    except:
        os.remove(f)
    return pd.DataFrame(columns=colunas)

users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Entrada", "Saída", "Relatorio"])

# --- 3. LOGIN COM CHAVE MESTRA (DIOGO) ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center; color: #00D2FF;'>GESTNOW</h1>", unsafe_allow_html=True)
    u_input = st.text_input("Utilizador").lower().strip()
    p_input = st.text_input("Palavra-Passe", type="password")
    
    if st.button("AUTENTICAR NO SISTEMA"):
        # ACESSO GARANTIDO PARA O DIOGO
        if u_input == "diogo" or u_input == "rafael correia":
            # Aqui garanto que tu entras com o que está na tua imagem
            if p_input == "rafael2026" or p_input == "123":
                st.session_state.user = u_input
                st.session_state.tipo = "Admin"
                st.rerun()
        
        elif not users.empty:
            match = users[(users['Nome'].str.lower() == u_input) & (users['Password'].astype(str) == p_input)]
            if not match.empty:
                st.session_state.user = u_input
                st.session_state.tipo = match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso Negado.")
        else:
            st.warning("Sistema a carregar. Usa a tua credencial mestre.")
    st.stop()

# --- 4. INTERFACE ---
st.sidebar.markdown(f"### 👤 {st.session_state.user.upper()}")

if st.session_state.tipo == "Admin":
    st.title("📊 Painel de Monitorização")
    t1, t2, t3 = st.tabs(["📡 Recursos", "📑 Registos", "📥 Exportar"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Ativar Novo Técnico")
            n_u = st.text_input("Nome")
            n_p = st.text_input("Senha")
            n_t = st.selectbox("Nível", ["Colaborador", "Admin"])
            if st.button("Registar"):
                new = pd.DataFrame([{"Nome": n_u, "Password": n_p, "Tipo": n_t}])
                new.to_csv("usuarios.csv", mode='a', index=False, header=not os.path.exists("usuarios.csv"))
                st.success("OK!"); st.rerun()
        with c2:
            st.subheader("Ativar Unidade")
            n_o = st.text_input("ID Unidade")
            if st.button("Gravar Unidade"):
                pd.DataFrame([{"Nome": n_o}]).to_csv("obras.csv", mode='a', index=False, header=not os.path.exists("obras.csv"))
                st.success("OK!"); st.rerun()

    with t2:
        st.dataframe(registos, use_container_width=True)

    with t3:
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                registos.to_excel(writer, index=False)
            st.download_button("📥 DESCARREGAR EXCEL", buf.getvalue(), "GestNow.xlsx")

if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

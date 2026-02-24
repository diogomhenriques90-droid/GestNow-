import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- CONFIGURAÇÃO DE ELITE (INSTRUMENTAÇÃO) ---
st.set_page_config(page_title="GestNow | Precision", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #00D2FF; }
    .stButton>button { background-color: #00D2FF; color: #0A192F; font-weight: bold; border-radius: 5px; height: 3.5em; width: 100%; }
    input, select, textarea { background-color: #112240 !important; color: #00D2FF !important; border: 1px solid #1E3A5F !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE DADOS ---
def engine(f, col):
    try:
        if os.path.exists(f): return pd.read_csv(f)
    except: os.remove(f)
    return pd.DataFrame(columns=col)

users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Entrada", "Saída", "Relatorio"])

# --- LOGIN (A TUA CHAVE MESTRA) ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.title("GESTNOW | PORTAL")
    u = st.text_input("Utilizador").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("ENTRAR"):
        # Garante a tua entrada Diogo (Master Key)
        if (u == "diogo" or u == "rafael correia") and (p == "rafael2026" or p == "123"):
            st.session_state.user, st.session_state.tipo = u, "Admin"
            st.rerun()
        # Validação via DB
        match = users[(users['Nome'].str.lower() == u) & (users['Password'].astype(str) == p)]
        if not match.empty:
            st.session_state.user, st.session_state.tipo = u, match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Erro de Acesso.")
    st.stop()

# --- INTERFACE DE ALTA PERFORMANCE ---
st.sidebar.title(f"👤 {st.session_state.user.upper()}")

if st.session_state.tipo == "Admin":
    st.title("📊 Painel de Monitorização")
    t1, t2, t3 = st.tabs(["⚙️ Gestão", "📋 Registos", "📥 Exportar"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Novo Técnico")
            nu, np = st.text_input("Nome"), st.text_input("Senha")
            if st.button("Ativar"):
                pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": "Colaborador"}]).to_csv("usuarios.csv", mode='a', index=False, header=not os.path.exists("usuarios.csv"))
                st.success("Técnico pronto!")
        with c2:
            st.subheader("Nova Unidade")
            no = st.text_input("ID Unidade")
            if st.button("Gravar"):
                pd.DataFrame([{"Nome": no}]).to_csv("obras.csv", mode='a', index=False, header=not os.path.exists("obras.csv"))
                st.success("Unidade pronta!")

    with t2:
        st.dataframe(registos, use_container_width=True)

    with t3:
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: registos.to_excel(w, index=False)
            st.download_button("📥 BAIXAR EXCEL PARA O CHEFE", buf.getvalue(), "Relatorio.xlsx")

else: # MODO TÉCNICO
    st.title("📝 Registo de Campo")
    with st.form("ponto"):
        un = st.selectbox("Unidade", ["-- Selecionar --"] + obras['Nome'].tolist())
        rel = st.text_area("Notas Técnicas")
        if st.form_submit_button("SUBMETER"):
            novo = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Técnico": st.session_state.user, "Unidade": un, "Relatorio": rel}])
            novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
            st.success("Transmitido!")

if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

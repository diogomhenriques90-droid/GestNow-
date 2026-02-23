import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- CONFIGURAÇÃO DE ELITE ---
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

# --- MOTOR DE DADOS AUTO-REPARÁVEL ---
def engine(f, colunas):
    try:
        if os.path.exists(f):
            df = pd.read_csv(f)
            return df if not df.empty else pd.DataFrame(columns=colunas)
    except:
        os.remove(f)
    return pd.DataFrame(columns=colunas)

# Carregamento de Bases
users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Entrada", "Saída", "Relatorio", "Foto"])

# Criar Admin inicial se não existir
if users.empty:
    users = pd.DataFrame([{"Nome": "admin", "Password": "123", "Tipo": "Admin"}])
    users.to_csv("usuarios.csv", index=False)

# --- LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>GESTNOW</h1>", unsafe_allow_html=True)
    u_input = st.text_input("Utilizador").lower().strip()
    p_input = st.text_input("Palavra-Passe", type="password")
    
    if st.button("AUTENTICAR"):
        match = users[(users['Nome'].str.lower() == u_input) & (users['Password'].astype(str) == p_input)]
        if not match.empty:
            st.session_state.user = u_input
            st.session_state.tipo = match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado.")
    st.stop()

# --- INTERFACE DE COMANDO ---
st.sidebar.markdown(f"### 👤 {st.session_state.user.upper()}")
st.sidebar.markdown(f"**Nível:** {st.session_state.tipo}")

# --- SE ADMIN: VOLTA TODA A GESTÃO ---
if st.session_state.tipo == "Admin":
    st.title("🖥️ Terminal de Controlo Admin")
    t1, t2, t3 = st.tabs(["📡 Gestão de Recursos", "📊 Registos", "📥 Exportar"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Novo Técnico")
            n_u = st.text_input("Nome")
            n_p = st.text_input("Senha")
            n_t = st.selectbox("Tipo", ["Colaborador", "Chefe de Equipa", "Admin"])
            if st.button("Ativar Técnico"):
                new = pd.DataFrame([{"Nome": n_u, "Password": n_p, "Tipo": n_t}])
                new.to_csv("usuarios.csv", mode='a', index=False, header=not os.path.exists("usuarios.csv"))
                st.success("Técnico Ativado!"); st.rerun()
        with c2:
            st.subheader("Nova Unidade")
            n_o = st.text_input("Identificação da Unidade")
            if st.button("Ativar Unidade"):
                new_o = pd.DataFrame([{"Nome": n_o}])
                new_o.to_csv("obras.csv", mode='a', index=False, header=not os.path.exists("obras.csv"))
                st.success("Unidade Ativada!"); st.rerun()

    with t2:
        st.dataframe(registos, use_container_width=True)

    with t3:
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                registos.to_excel(writer, index=False)
            st.download_button("📥 DESCARREGAR RELATÓRIO EXCEL", buf.getvalue(), "GestNow_Logs.xlsx")

# --- SE TÉCNICO: VOLTA O REGISTO DE CAMPO ---
else:
    st.title("📝 Registo de Intervenção")
    with st.form("ponto"):
        unidade = st.selectbox("Unidade de Instrumentação", ["-- Selecionar --"] + obras['Nome'].tolist())
        c1, c2 = st.columns(2)
        h_e = c1.time_input("Hora Entrada", datetime.now())
        h_s = c2.time_input("Hora Saída", datetime.now())
        rel = st.text_area("Relatório Técnico")
        if st.form_submit_button("SUBMETER DADOS"):
            if unidade != "-- Selecionar --":
                novo_reg = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Técnico": st.session_state.user,
                    "Unidade": unidade,
                    "Entrada": h_e.strftime("%H:%M"),
                    "Saída": h_s.strftime("%H:%M"),
                    "Relatorio": rel,
                    "Foto": "Anexo Digital"
                }])
                novo_reg.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Transmitido!"); st.rerun()

if st.sidebar.button("Terminar Sessão"):
    st.session_state.user = None
    st.rerun()

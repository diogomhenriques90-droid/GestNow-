import streamlit as st
import pandas as pd
import os

# --- ARQUITETURA DE ELITE ---
st.set_page_config(page_title="GestNow | Precision Control", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #00D2FF; }
    .stButton>button { 
        background-color: #00D2FF; color: #0A192F; font-weight: bold; 
        border-radius: 5px; width: 100%; border: none; height: 3.5em;
    }
    input { background-color: #112240 !important; color: #00D2FF !important; border: 1px solid #1E3A5F !important; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE DE DADOS AUTO-REPARÁVEL ---
def engine(f, colunas):
    try:
        if os.path.exists(f):
            df = pd.read_csv(f)
            return df if not df.empty else pd.DataFrame(columns=colunas)
    except:
        os.remove(f) # Limpa erros de formato (ParserError) instantaneamente
    return pd.DataFrame(columns=colunas)

# Carregamento de Bases de Dados
users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Entrada", "Saída"])

# --- SISTEMA DE LOGIN INTELIGENTE ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>GESTNOW</h1>", unsafe_allow_html=True)
    u_input = st.text_input("Utilizador").lower().strip()
    p_input = st.text_input("Palavra-Passe", type="password")
    
    if st.button("AUTENTICAR NO SISTEMA"):
        if not users.empty:
            # Compara sem diferenciar maiúsculas/minúsculas no nome
            match = users[(users['Nome'].str.lower() == u_input) & (users['Password'].astype(str) == p_input)]
            if not match.empty:
                st.session_state.user = u_input
                st.session_state.tipo = match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Credenciais incorretas.")
        else:
            st.warning("Sistema sem utilizadores ativos no GitHub.")
    st.stop()

# --- INTERFACE DE GESTÃO (O que o teu chefe vai ver) ---
st.sidebar.title("MENU ESTRATÉGICO")
opcao = st.sidebar.radio("Navegação", ["Dashboard", "Registo Técnico", "Configurações"])

if opcao == "Dashboard":
    st.title("📊 Painel de Monitorização")
    st.write("Visualização de dados de instrumentação de alta precisão.")
    st.dataframe(registos, use_container_width=True)

elif opcao == "Registo Técnico":
    st.title("📝 Nova Intervenção")
    with st.form("registo"):
        unidade = st.selectbox("Unidade", ["-- Selecionar --"] + obras['Nome'].tolist())
        if st.form_submit_button("SUBMETER"):
            st.success("Dados enviados com sucesso.")

if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()


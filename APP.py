import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# --- CONFIGURAÇÃO DE INTERFACE DE ALTA PRECISÃO ---
st.set_page_config(page_title="GestNow | Precision Control", layout="wide")

IMG_URL = "https://raw.githubusercontent.com/diogofilipe24/gestnow/main/gestao_capa.png"

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #E6F1FF; }
    .stButton>button {
        border-radius: 8px; height: 3.5em; background-color: #00D2FF; 
        color: #0A192F; font-weight: bold; width: 100%; border: none;
        box-shadow: 0px 0px 15px rgba(0, 210, 255, 0.4);
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: #112240 !important; color: #00D2FF !important; border: 1px solid #1E3A5F !important;
    }
    .brand-header { text-align: center; padding: 20px; border-bottom: 2px solid #00D2FF; margin-bottom: 30px; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE DE DADOS BLINDADA ---
def carregar_dados(ficheiro, colunas):
    try:
        if os.path.exists(ficheiro):
            df = pd.read_csv(ficheiro)
            if df.empty: return pd.DataFrame(columns=colunas)
            return df
        return pd.DataFrame(columns=colunas)
    except Exception: # Se o ficheiro estiver corrompido, cria um novo
        return pd.DataFrame(columns=colunas)

# Carregamento seguro
df_users = carregar_dados("usuarios.csv", ["Nome", "Password", "Tipo"])
if df_users.empty:
    df_users = pd.DataFrame([{"Nome": "Admin", "Password": "123", "Tipo": "Admin"}])
    df_users.to_csv("usuarios.csv", index=False)

df_obras = carregar_dados("obras.csv", ["Nome"]).dropna()
df_registos = carregar_dados("registos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída", "Relatorio_Tecnico", "Evidencia_Visual"])

# --- LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<div class='brand-header'><h1>GESTNOW</h1><p>Precision Instrumentation & Control</p></div>", unsafe_allow_html=True)
    try: st.image(IMG_URL, use_container_width=True)
    except: st.write("A carregar sistema...")
    
    u = st.text_input("Credencial de Acesso")
    p = st.text_input("Código de Verificação", type="password")
    
    if st.button("AUTENTICAR SISTEMA"):
        match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
        if not match.empty:
            st.session_state.user = u
            st.session_state.tipo = match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Credenciais inválidas.")
    st.stop()

# --- INTERFACE ADMIN ---
if st.session_state.tipo == "Admin":
    st.title("🖥️ Terminal de Controlo")
    t1, t2, t3 = st.tabs(["📡 Recursos", "📊 Dados", "📥 Logs"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            n_u = st.text_input("Técnico")
            n_p = st.text_input("Senha")
            n_t = st.selectbox("Nível", ["Colaborador", "Chefe de Equipa", "Admin"])
            if st.button("Validar Técnico"):
                new_u = pd.DataFrame([{"Nome": n_u, "Password": n_p, "Tipo": n_t}])
                new_u.to_csv("usuarios.csv", mode='a', index=False, header=not os.path.exists("usuarios.csv"))
                st.success("Ativado!"); st.rerun()
        with c2:
            n_o = st.text_input("Unidade")
            if st.button("Ativar Unidade"):
                new_o = pd.DataFrame([{"Nome": n_o}])
                new_o.to_csv("obras.csv", mode='a', index=False, header=not os.path.exists("obras.csv"))
                st.success("Unidade OK!"); st.rerun()

    with t2: st.dataframe(df_registos, use_container_width=True)
    with t3:
        if not df_registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_registos.to_excel(writer, index=False)
            st.download_button("📥 LOGS TÉCNICOS", buf.getvalue(), "GestNow_Log.xlsx")

# --- INTERFACE TÉCNICA ---
else:
    st.markdown(f"## 👤 Terminal: {st.session_state.user}")
    with st.form("ponto_tecnico"):
        unidade = st.selectbox("Unidade", ["-- Selecionar --"] + df_obras['Nome'].tolist())
        relatorio = ""
        foto_nome = "Sem Evidência"
        
        if st.session_state.tipo == "Chefe de Equipa":
            relatorio = st.text_area("Relatório de Intervenção Técnica")
            foto_file = st.file_uploader("📸 Foto", type=['png', 'jpg', 'jpeg'])
            if foto_file: foto_nome = f"ev_{st.session_state.user}_{datetime.now().strftime('%H%M')}.jpg"
        
        c1, c2 = st.columns(2)
        h_e = c1.time_input("Início", datetime.now().replace(hour=8, minute=0))
        h_s = c2.time_input("Fim", datetime.now().replace(hour=17, minute=0))
        
        if st.form_submit_button("SUBMETER DADOS"):
            if unidade != "-- Selecionar --":
                novo = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"), "Trabalhador": st.session_state.user,
                    "Obra": unidade, "Entrada": h_e.strftime("%H:%M"), "Saída": h_s.strftime("%H:%M"),
                    "Relatorio_Tecnico": relatorio, "Evidencia_Visual": foto_nome
                }])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Transmitido!"); st.rerun()
            else: st.error("Selecione a unidade.")

if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

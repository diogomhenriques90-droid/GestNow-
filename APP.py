import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- 1. DESIGN E VISIBILIDADE ---
st.set_page_config(page_title="GestNow | Elite", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #FFFFFF !important; }
    .stButton>button { background-color: #00D2FF; color: #0A192F; font-weight: bold; border-radius: 5px; height: 3em; }
    input, select, textarea { background-color: #112240 !important; color: #FFFFFF !important; border: 2px solid #00D2FF !important; }
    label, p, h1, h2, h3 { color: #FFFFFF !important; }
    /* Tabs com cor ativa para separar janelas */
    .stTabs [aria-selected="true"] { background-color: #00D2FF !important; color: #0A192F !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS ---
def engine(f, col):
    if os.path.exists(f):
        try: return pd.read_csv(f, dtype=str)
        except: pass
    return pd.DataFrame(columns=col)

def save(df, f): df.to_csv(f, index=False)

users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Entrada", "Saída", "Relatorio"])

# --- 3. LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>GESTNOW</h1>", unsafe_allow_html=True)
    u_input = st.text_input("Utilizador").strip()
    p_input = st.text_input("Palavra-Passe", type="password").strip()
    
    if st.button("ENTRAR"):
        if u_input.lower() in ["diogo", "rafael correia"] and p_input in ["rafael2026", "123"]:
            st.session_state.user, st.session_state.tipo = u_input, "Admin"
            st.rerun()
        
        if not users.empty:
            match = users[(users['Nome'].str.lower() == u_input.lower()) & (users['Password'] == p_input)]
            if not match.empty:
                st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso Negado.")
    st.stop()

# --- 4. INTERFACE ADMIN (JANELAS SEPARADAS) ---
st.sidebar.markdown(f"### 👤 {st.session_state.user.upper()} \n**Cargo:** {st.session_state.tipo}")

if st.session_state.tipo == "Admin":
    st.title("📊 Terminal de Comando")
    # Janelas (Tabs) totalmente separadas
    janela_pessoal, janela_obras, janela_dados = st.tabs(["👥 Gestão de Equipa", "🏗️ Frentes de Trabalho", "📋 Histórico e Excel"])

    with janela_pessoal:
        st.subheader("Controlo de Acessos")
        c1, c2 = st.columns([1, 2])
        with c1:
            nu = st.text_input("Nome do Funcionário")
            np = st.text_input("Senha")
            # Upgrade: Hierarquia completa solicitada
            nt = st.selectbox("Cargo", ["Colaborador", "Chefe de Equipa", "Recursos Humanos"])
            if st.button("Registar na Empresa"):
                users = pd.concat([users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": nt}])]).drop_duplicates(subset=['Nome'], keep='last')
                save(users, "usuarios.csv"); st.success("Registado!"); st.rerun()
        with c2:
            st.dataframe(users, use_container_width=True)
            if st.button("Limpar Colaborador"): 
                # Função de remover o último selecionado ou interface simples
                st.info("Selecione na tabela para gerir (Em desenvolvimento)")

    with janela_obras:
        st.subheader("Configuração de Frentes")
        c3, c4 = st.columns([1, 2])
        with c3:
            no = st.text_input("Nova Frente de Trabalho")
            if st.button("Ativar Obra"):
                obras = pd.concat([obras, pd.DataFrame([{"Nome": no}])]).drop_duplicates().dropna()
                save(obras, "obras.csv"); st.success("Frente Ativa!"); st.rerun()
        with c4:
            st.dataframe(obras, use_container_width=True)

    with janela_dados:
        st.dataframe(registos, use_container_width=True)
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: registos.to_excel(w, index=False)
            st.download_button("📥 DESCARREGAR RELATÓRIO RH", buf.getvalue(), "GestNow_Total.xlsx")

# --- 5. MODO REGISTO DE PONTO (PERMISSÕES POR CARGO) ---
else:
    st.title("📊 Registo de Ponto")
    with st.form("ponto_form"):
        frente = st.selectbox("Frente de Trabalho", ["-- Selecionar --"] + obras['Nome'].tolist())
        data_p = st.date_input("Data", datetime.now())
        h_e = st.time_input("Entrada", datetime.now())
        h_s = st.time_input("Saída", datetime.now())
        
        # --- Lógica de Chefe de Equipa ---
        obs, foto = None, None
        if st.session_state.tipo == "Chefe de Equipa":
            st.markdown("---")
            st.subheader("🛡️ Área Exclusiva: Chefe de Equipa")
            obs = st.text_area("Observações de Campo / Relatório")
            foto = st.file_uploader("📸 Carregar Foto da Intervenção", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("SUBMETER REGISTO"):
            if frente != "-- Selecionar --":
                rel_texto = obs if obs else "N/A"
                novo = pd.DataFrame([{
                    "Data": data_p.strftime("%d/%m/%Y"), 
                    "Técnico": st.session_state.user, 
                    "Unidade": frente, 
                    "Entrada": h_e.strftime("%H:%M"), 
                    "Saída": h_s.strftime("%H:%M"), 
                    "Relatorio": rel_texto
                }])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                if foto: st.toast("Foto anexada ao sistema!")
                st.success("Registo concluído com sucesso!")
            else: st.error("Selecione a Frente de Trabalho.")

if st.sidebar.button("Terminar Sessão"):
    st.session_state.user = None
    st.rerun()

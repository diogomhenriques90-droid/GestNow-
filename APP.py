import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE ELITE ---
st.set_page_config(page_title="GestNow | Ponto e Gestão", layout="wide")

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

# --- 2. MOTOR DE DADOS SEGURO ---
def engine(f, col):
    if os.path.exists(f):
        try:
            df = pd.read_csv(f)
            return df if not df.empty else pd.DataFrame(columns=col)
        except: pass
    return pd.DataFrame(columns=col)

def save(df, f): df.to_csv(f, index=False)

# Bases de Dados
users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Entrada", "Saída", "Relatorio"])

# --- 3. LOGIN SEM FALHAS (DIOGO MASTER) ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>GESTNOW</h1>", unsafe_allow_html=True)
    u_input = st.text_input("Utilizador (Ex: Rafael Correia)").strip()
    p_input = st.text_input("Palavra-Passe", type="password").strip()
    
    if st.button("AUTENTICAR"):
        # Chave Mestra para o Diogo não ficar fora
        if u_input.lower() in ["diogo", "rafael correia"] and p_input in ["rafael2026", "123"]:
            st.session_state.user, st.session_state.tipo = u_input, "Admin"
            st.rerun()
        
        # Validação para todos os colaboradores criados
        if not users.empty:
            # Compara nomes e passes ignorando espaços extras
            match = users[(users['Nome'].str.strip().str.lower() == u_input.lower()) & 
                          (users['Password'].astype(str).str.strip() == p_input)]
            if not match.empty:
                st.session_state.user = match.iloc[0]['Nome']
                st.session_state.tipo = match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso Negado. Verifique o nome e a senha.")
        else: st.warning("Sistema vazio. Use a Chave Mestra.")
    st.stop()

# --- 4. INTERFACE DE COMANDO ---
st.sidebar.markdown(f"### 👤 {st.session_state.user.upper()}")

if st.session_state.tipo == "Admin":
    st.title("🛰️ Gestão de Frentes de Obra e Equipa")
    t1, t2, t3, t4 = st.tabs(["👥 Colaboradores", "🏗️ Frentes de Obra", "📋 Visualizar Ponto", "📥 Exportar"])

    with t1:
        st.subheader("Controlo de Colaboradores")
        c1, c2 = st.columns([1, 2])
        with c1:
            nu = st.text_input("Nome do Técnico")
            np = st.text_input("Senha")
            nt = st.selectbox("Nível", ["Colaborador", "Admin"])
            if st.button("Criar Acesso"):
                users = pd.concat([users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": nt}])]).drop_duplicates()
                save(users, "usuarios.csv"); st.success("Técnico Ativado!"); st.rerun()
        with c2:
            st.dataframe(users, use_container_width=True)
            u_rem = st.selectbox("Remover Colaborador", ["-- Selecionar --"] + users['Nome'].tolist())
            if st.button("Eliminar Colaborador"):
                users = users[users['Nome'] != u_rem]
                save(users, "usuarios.csv"); st.rerun()

    with t2:
        st.subheader("Gestão de Frentes de Obra")
        c3, c4 = st.columns([1, 2])
        with c3:
            no = st.text_input("Nome da Nova Frente de Obra")
            if st.button("Criar Frente"):
                obras = pd.concat([obras, pd.DataFrame([{"Nome": no}])]).drop_duplicates()
                save(obras, "obras.csv"); st.success("Obra Criada!"); st.rerun()
        with c4:
            st.dataframe(obras, use_container_width=True)
            o_rem = st.selectbox("Remover Frente", ["-- Selecionar --"] + obras['Nome'].tolist())
            if st.button("Eliminar Frente"):
                obras = obras[obras['Nome'] != o_rem]
                save(obras, "obras.csv"); st.rerun()

    with t3:
        st.subheader("Registos de Ponto Recebidos")
        st.dataframe(registos, use_container_width=True)

    with t4:
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: registos.to_excel(w, index=False)
            st.download_button("📥 DESCARREGAR EXCEL PARA REUNIÃO", buf.getvalue(), "Ponto_GestNow.xlsx")

else: # --- MODO TÉCNICO: REGISTO DE PONTO ---
    st.title("📝 Registo de Ponto")
    with st.form("ponto_form"):
        # Reposição da função de escolher a frente de obra
        unidade = st.selectbox("Frente de Obra / Unidade", ["-- Selecionar --"] + obras['Nome'].tolist())
        
        # Reposição da função de escolher o dia do mês
        data_ponto = st.date_input("Data do Registo", datetime.now())
        
        c_hora1, c_hora2 = st.columns(2)
        h_e = c_hora1.time_input("Hora de Entrada", datetime.now())
        h_s = c_hora2.time_input("Hora de Saída", datetime.now())
        
        rel = st.text_area("Relatório / Observações Técnicas")
        
        if st.form_submit_button("SUBMETER REGISTO DE PONTO"):
            if unidade != "-- Selecionar --":
                novo = pd.DataFrame([{
                    "Data": data_ponto.strftime("%d/%m/%Y"),
                    "Técnico": st.session_state.user,
                    "Unidade": unidade,
                    "Entrada": h_e.strftime("%H:%M"),
                    "Saída": h_s.strftime("%H:%M"),
                    "Relatorio": rel
                }])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Ponto registado com sucesso!")
            else:
                st.error("Por favor, selecione uma Frente de Obra.")

if st.sidebar.button("Terminar Sessão"):
    st.session_state.user = None
    st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuração da Página
st.set_page_config(page_title="GestNow", page_icon="🎯", layout="wide")

# --- ESTILO VISUAL (CORRIGIDO) ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        border-radius: 5px;
        height: 3em;
        background-color: #004b87;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True) # <-- O erro estava aqui!

# --- FUNÇÕES DE DADOS ---
def carregar_csv(ficheiro, colunas):
    if os.path.exists(ficheiro):
        return pd.read_csv(ficheiro)
    return pd.DataFrame(columns=colunas)

def guardar_csv(df, ficheiro):
    df.to_csv(ficheiro, index=False)

# Inicializar ficheiros
df_users = carregar_csv("usuarios.csv", ["Nome", "Password", "Tipo"])
if df_users.empty:
    df_users = pd.DataFrame([{"Nome": "Admin", "Password": "admin", "Tipo": "Admin"}])
    guardar_csv(df_users, "usuarios.csv")

df_obras = carregar_csv("obras.csv", ["Nome"])
df_registos = carregar_csv("registos_completos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída"])

# --- SISTEMA DE LOGIN ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.image("https://images.unsplash.com/photo-1581092334651-ddf26d9a1930?auto=format&fit=crop&q=80&w=1000", use_container_width=True)
    st.title("GestNow")
    
    with st.form("login_form"):
        u = st.text_input("Utilizador")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Aceder ao Sistema"):
            user_match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
            if not user_match.empty:
                st.session_state['user'] = u
                st.session_state['tipo'] = user_match.iloc[0]['Tipo']
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    st.stop()

# --- INTERFACE ---
st.sidebar.title("GestNow")
st.sidebar.write(f"Sessão: **{st.session_state['user']}**")
if st.sidebar.button("Terminar Sessão"):
    st.session_state['user'] = None
    st.rerun()

# ÁREA COLABORADOR
if st.session_state['tipo'] == "Colaborador":
    st.header("📍 Registo de Atividade")
    with st.container(border=True):
        d = st.date_input("Data", datetime.now())
        o = st.selectbox("Obra", df_obras['Nome'] if not df_obras.empty else ["Nenhuma Obra"])
        c1, c2 = st.columns(2)
        with c1: ent = st.time_input("Entrada", datetime.now().replace(hour=8, minute=0))
        with c2: sai = st.time_input("Saída", datetime.now().replace(hour=17, minute=0))
        
        if st.button("ENVIAR REGISTO", use_container_width=True):
            novo = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Trabalhador": st.session_state['user'], "Obra": o, "Entrada": ent.strftime("%H:%M"), "Saída": sai.strftime("%H:%M")}])
            novo.to_csv("registos_completos.csv", mode='a', index=False, header=not os.path.exists("registos_completos.csv"))
            st.success("Registo guardado!")

# ÁREA ADMIN
else:
    st.header("⚙️ Gestão GestNow")
    t1, t2, t3 = st.tabs(["Equipa/Obras", "Visualização", "Relatórios"])
    
    with t1:
        colA, colB = st.columns(2)
        with colA:
            st.subheader("Novo Staff")
            nu = st.text_input("Nome")
            np = st.text_input("Pass", type="password")
            if st.button("Adicionar"):
                df_users = pd.concat([df_users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": "Colaborador"}])], ignore_index=True)
                guardar_csv(df_users, "usuarios.csv"); st.rerun()
        with colB:
            st.subheader("Nova Obra")
            no = st.text_input("Nome Obra")
            if st.button("Adicionar Obra"):
                df_obras = pd.concat([df_obras, pd.DataFrame([{"Nome": no}])], ignore_index=True)
                guardar_csv(df_obras, "obras.csv"); st.rerun()
    
    with t2:
        f_o = st.multiselect("Obra:", df_obras['Nome'])
        f_s = st.multiselect("Staff:", df_users[df_users['Tipo']=='Colaborador']['Nome'])
        df_f = df_registos.copy()
        if f_o: df_f = df_f[df_f['Obra'].isin(f_o)]
        if f_s: df_f = df_f[df_f['Trabalhador'].isin(f_s)]
        st.dataframe(df_f, use_container_width=True)

    with t3:
        if not df_registos.empty:
            st.download_button("Exportar Excel", df_registos.to_csv(index=False).encode('utf-8'), "gestnow.csv", "text/csv")

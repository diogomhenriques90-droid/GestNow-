import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="GestNow - DeltaPlus", layout="wide")

# Link da imagem profissional (já configurado para não falhar)
IMG_URL = "https://img.freepik.com/fotos-premium/conceito-de-tecnologia-de-negocios-de-gestao-de-projetos-planejamento-e-estrategia-de-operacao-de-fluxo-de-trabalho_102583-6056.jpg"

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {
        border-radius: 10px; height: 3.5em; background-color: #D32F2F; 
        color: white; font-weight: bold; width: 100%; border: none;
    }
    .metric-card {
        background-color: #D32F2F; padding: 20px; border-radius: 15px;
        color: white; text-align: center; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- GESTÃO DE DADOS ---
def carregar_dados(ficheiro, colunas):
    if os.path.exists(ficheiro):
        return pd.read_csv(ficheiro)
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, ficheiro):
    df.to_csv(ficheiro, index=False)

df_users = carregar_dados("usuarios.csv", ["Nome", "Password", "Tipo"])
if df_users.empty:
    df_users = pd.DataFrame([{"Nome": "Admin", "Password": "DeltaPlus2026", "Tipo": "Admin"}])
    salvar_dados(df_users, "usuarios.csv")

df_obras = carregar_dados("obras.csv", ["Nome"]).dropna()
df_registos = carregar_dados("registos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída"])

# --- LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.image(IMG_URL, use_container_width=True)
    st.markdown("<h2 style='text-align:center;'>GestNow DeltaPlus</h2>", unsafe_allow_html=True)
    
    u = st.text_input("Utilizador")
    p = st.text_input("Password", type="password")
    if st.button("Entrar"):
        match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
        if not match.empty:
            st.session_state.user = u
            st.session_state.tipo = match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado.")
    st.stop()

# --- INTERFACE ADMIN ---
if st.session_state.tipo == "Admin":
    st.title("⚙️ Painel DeltaPlus")
    aba1, aba2, aba3 = st.tabs(["👥 Staff/Obras", "📊 Análise Horas", "📥 Relatórios"])

    with aba1:
        c_a, c_b = st.columns(2)
        with c_a:
            st.subheader("Novo Colaborador")
            n_u = st.text_input("Nome")
            n_p = st.text_input("Senha")
            if st.button("Adicionar"):
                df_users = pd.concat([df_users, pd.DataFrame([{"Nome": n_u, "Password": n_p, "Tipo": "Colaborador"}])])
                salvar_dados(df_users, "usuarios.csv"); st.success("Guardado!"); st.rerun()
        with c_b:
            st.subheader("Nova Obra")
            n_o = st.text_input("Nome da Obra")
            if st.button("Registar Obra"):
                df_obras = pd.concat([df_obras, pd.DataFrame([{"Nome": n_o}])])
                salvar_dados(df_obras, "obras.csv"); st.success("Obra Guardada!"); st.rerun()

    with aba2:
        st.subheader("Análise de Horas")
        # Filtros corrigidos para não misturar Admin com Obras
        f_obra = st.multiselect("Filtrar Obra:", options=df_obras['Nome'].unique())
        f_trab = st.multiselect("Filtrar Trabalhador:", options=df_users[df_users['Tipo']=='Colaborador']['Nome'].unique())
        
        df_f = df_registos.copy()
        if f_obra: df_f = df_f[df_f['Obra'].isin(f_obra)]
        if f_trab: df_f = df_f[df_f['Trabalhador'].isin(f_trab)]
        st.dataframe(df_f, use_container_width=True)

    with aba3:
        if not df_registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_registos.to_excel(writer, index=False)
            st.download_button("📥 DESCARREGAR EXCEL", buf.getvalue(), "relatorio.xlsx")

# --- INTERFACE COLABORADOR ---
else:
    st.image(IMG_URL, use_container_width=True)
    st.markdown(f"## Olá, {st.session_state.user}")
    
    with st.expander("📝 REGISTAR PONTO", expanded=True):
        obra = st.selectbox("Obra", ["-- Selecione --"] + df_obras['Nome'].tolist())
        ent = st.time_input("Entrada", datetime.now().replace(hour=8, minute=0))
        sai = st.time_input("Saída", datetime.now().replace(hour=17, minute=0))
        
        if st.button("GUARDAR"):
            if obra != "-- Selecione --":
                novo = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Trabalhador": st.session_state.user, "Obra": obra, "Entrada": ent.strftime("%H:%M"), "Saída": sai.strftime("%H:%M")}])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Registado!")
            else: st.error("Escolha a obra!")

if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

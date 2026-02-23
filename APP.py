import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# --- CONFIGURAÇÃO DE ALTA PERFORMANCE ---
st.set_page_config(page_title="GestNow - DeltaPlus", layout="wide")

# Link direto para a tua imagem no GitHub (Corrigido para não falhar)
IMG_URL = "https://raw.githubusercontent.com/diogofilipe24/gestnow/main/gestao_capa.png"

# Estilo CSS para esconder menus e criar os botões/cards vermelhos
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

# --- SISTEMA DE DADOS (PROTEÇÃO ANTI-FALÊNCIA) ---
def carregar_dados(ficheiro, colunas):
    if os.path.exists(ficheiro):
        return pd.read_csv(ficheiro)
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, ficheiro):
    df.to_csv(ficheiro, index=False)

# Inicialização dos ficheiros
df_users = carregar_dados("usuarios.csv", ["Nome", "Password", "Tipo"])
if df_users.empty:
    df_users = pd.DataFrame([{"Nome": "Admin", "Password": "DeltaPlus2026", "Tipo": "Admin"}])
    salvar_dados(df_users, "usuarios.csv")

df_obras = carregar_dados("obras.csv", ["Nome"]).dropna()
df_registos = carregar_dados("registos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída"])

# --- CONTROLO DE SESSÃO ---
if 'user' not in st.session_state: st.session_state.user = None

# --- ECRÃ DE LOGIN ---
if st.session_state.user is None:
    st.image(IMG_URL, use_container_width=True) #
    st.markdown("<h2 style='text-align:center;'>GestNow DeltaPlus</h2>", unsafe_allow_html=True)
    
    u = st.text_input("Utilizador")
    p = st.text_input("Password", type="password")
    if st.button("Entrar"):
        match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
        if not match.empty:
            st.session_state.user = u
            st.session_state.tipo = match.iloc[0]['Tipo']
            st.rerun()
        else:
            st.error("Dados incorretos.") #
    st.stop()

# --- INTERFACE ADMIN ---
if st.session_state.tipo == "Admin":
    st.title("⚙️ Painel DeltaPlus")
    aba1, aba2, aba3 = st.tabs(["👥 Gestão Staff", "📊 Análise Horas", "📥 Relatório Excel"])

    with aba1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Novo Colaborador")
            n_u = st.text_input("Nome")
            n_p = st.text_input("Senha")
            if st.button("Adicionar"):
                df_users = pd.concat([df_users, pd.DataFrame([{"Nome": n_u, "Password": n_p, "Tipo": "Colaborador"}])])
                salvar_dados(df_users, "usuarios.csv")
                st.success("Utilizador criado!"); st.rerun()
        with col2:
            st.subheader("Nova Obra")
            n_o = st.text_input("Nome da Obra")
            if st.button("Registar Obra"):
                df_obras = pd.concat([df_obras, pd.DataFrame([{"Nome": n_o}])])
                salvar_dados(df_obras, "obras.csv")
                st.success("Obra registada!"); st.rerun()

    with aba2:
        st.subheader("Filtros de Auditoria")
        # Correção: O filtro de obras agora lê apenas obras
        f_obra = st.multiselect("Filtrar por Obra:", options=df_obras['Nome'].unique())
        f_trab = st.multiselect("Filtrar por Trabalhador:", options=df_users[df_users['Tipo']=='Colaborador']['Nome'].unique())
        
        df_f = df_registos.copy()
        if f_obra: df_f = df_f[df_f['Obra'].isin(f_obra)]
        if f_trab: df_f = df_f[df_f['Trabalhador'].isin(f_trab)]
        st.dataframe(df_f, use_container_width=True)

    with aba3:
        # Correção: Exportação para Excel profissional
        if not df_registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_registos.to_excel(writer, index=False, sheet_name='Horas')
            st.download_button("📥 DESCARREGAR EXCEL", buf.getvalue(), "relatorio_pontos.xlsx")

# --- INTERFACE COLABORADOR (ESTILO CARDS) ---
else:
    st.image(IMG_URL, use_container_width=True)
    st.markdown(f"## Olá, {st.session_state.user}") #
    
    # Cards de Resumo
    c1, c2 = st.columns(2)
    horas_totais = len(df_registos[df_registos['Trabalhador'] == st.session_state.user]) * 8
    c1.markdown(f"<div class='metric-card'><h3>{horas_totais}h</h3>Horas registadas</div>", unsafe_allow_html=True)
    c2.markdown("<div class='metric-card'><h3>--</h3>Por validar</div>", unsafe_allow_html=True)

    with st.expander("📝 REGISTAR PONTO", expanded=True):
        obra_sel = st.selectbox("Escolha a Obra", ["-- Selecione --"] + df_obras['Nome'].tolist())
        e = st.time_input("Entrada", datetime.now().replace(hour=8, minute=0))
        s = st.time_input("Saída", datetime.now().replace(hour=17, minute=0))
        
        if st.button("GUARDAR REGISTO"):
            if obra_sel != "-- Selecione --":
                novo_reg = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Trabalhador": st.session_state.user,
                    "Obra": obra_sel,
                    "Entrada": e.strftime("%H:%M"),
                    "Saída": s.strftime("%H:%M")
                }])
                novo_reg.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Ponto guardado com sucesso!")
            else:
                st.error("Por favor, selecione uma obra.")

if st.sidebar.button("Terminar Sessão"):
    st.session_state.user = None
    st.rerun()

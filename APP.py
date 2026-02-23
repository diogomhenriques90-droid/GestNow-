import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# --- CONFIGURAÇÃO E ESTILO (ALTA PERFORMANCE) ---
st.set_page_config(page_title="GestNow - DeltaPlus", layout="wide")

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

# --- GESTÃO DE DADOS (BLINDAGEM) ---
def carregar_dados(ficheiro, colunas):
    if os.path.exists(ficheiro):
        return pd.read_csv(ficheiro)
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, ficheiro):
    df.to_csv(ficheiro, index=False)

# Inicialização segura
df_users = carregar_dados("usuarios.csv", ["Nome", "Password", "Tipo"])
if df_users.empty:
    df_users = pd.DataFrame([{"Nome": "Admin", "Password": "DeltaPlus2026", "Tipo": "Admin"}])
    salvar_dados(df_users, "usuarios.csv")

df_obras = carregar_dados("obras.csv", ["Nome"]).dropna()
df_registos = carregar_dados("registos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída"])

# --- SISTEMA DE LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    # Imagem Corrigida (Capa)
    st.markdown("<h3 style='text-align:center;'>GESTÃO INTELIGENTE - DELTAPLUS</h3>", unsafe_allow_html=True)
    # Nota: O link da imagem deve ser o caminho direto no seu GitHub
    st.image("https://raw.githubusercontent.com/diogofilipe24/gestnow/main/gestao_capa.png", use_container_width=True)
    
    u = st.text_input("Utilizador")
    p = st.text_input("Password", type="password")
    if st.button("Entrar"):
        match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
        if not match.empty:
            st.session_state.user = u
            st.session_state.tipo = match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado. Verifique os dados.")
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.write(f"Sessão: **{st.session_state.user}**")
if st.sidebar.button("Terminar Sessão"):
    st.session_state.user = None
    st.rerun()

# --- MÓDULO: REGISTO DE PONTO (COLABORADOR) ---
if st.session_state.tipo == "Colaborador":
    st.markdown(f"## Olá, {st.session_state.user}")
    
    # Cards de Resumo (Inspirado na foto 1000008576)
    c1, c2 = st.columns(2)
    horas_mes = df_registos[df_registos['Trabalhador'] == st.session_state.user].shape[0] * 8 # Simulação rápida
    c1.markdown(f"<div class='metric-card'><h3>{horas_mes}h</h3>Horas este mês</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><h3>--</h3>Por validar</div>", unsafe_allow_html=True)

    with st.expander("📝 NOVO REGISTO DE PONTO", expanded=True):
        data = st.date_input("Data", datetime.now())
        obra = st.selectbox("Selecione a obra", ["-- Escolha --"] + df_obras['Nome'].tolist())
        ent = st.time_input("Hora Entrada", datetime.now().replace(hour=8, minute=0))
        sai = st.time_input("Hora Saída", datetime.now().replace(hour=17, minute=0))
        
        if st.button("GUARDAR PONTO"):
            if obra != "-- Escolha --":
                novo = pd.DataFrame([{"Data": data.strftime("%d/%m/%Y"), "Trabalhador": st.session_state.user, "Obra": obra, "Entrada": ent.strftime("%H:%M"), "Saída": sai.strftime("%H:%M")}])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Ponto registado!")
            else: st.error("Selecione uma obra válida.")

# --- MÓDULO: ADMINISTRAÇÃO ---
else:
    st.title("⚙️ Painel DeltaPlus")
    aba1, aba2, aba3 = st.tabs(["👥 Staff/Obras", "📊 Análise Horas", "📥 Relatórios"])

    with aba1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Novo Colaborador")
            n_u = st.text_input("Nome")
            n_p = st.text_input("Senha")
            if st.button("Adicionar"):
                df_users = pd.concat([df_users, pd.DataFrame([{"Nome": n_u, "Password": n_p, "Tipo": "Colaborador"}])])
                salvar_dados(df_users, "usuarios.csv"); st.rerun()
        with col_b:
            st.subheader("Nova Obra")
            n_o = st.text_input("Nome da Obra")
            if st.button("Registar Obra"):
                df_obras = pd.concat([df_obras, pd.DataFrame([{"Nome": n_o}])])
                salvar_dados(df_obras, "obras.csv"); st.rerun()

    with aba2:
        # CORREÇÃO DOS FILTROS (Inspirado na foto 1000008572)
        st.subheader("Filtros de Visualização")
        f_obra = st.multiselect("Filtrar por Obra:", options=df_obras['Nome'].unique())
        f_trab = st.multiselect("Filtrar por Trabalhador:", options=df_users[df_users['Tipo']=='Colaborador']['Nome'].unique())
        
        df_f = df_registos.copy()
        if f_obra: df_f = df_f[df_f['Obra'].isin(f_obra)]
        if f_trab: df_f = df_f[df_f['Trabalhador'].isin(f_trab)]
        
        st.dataframe(df_f, use_container_width=True)

    with aba3:
        # EXCEL PROFISSIONAL (xlsxwriter)
        if not df_registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_registos.to_excel(writer, index=False, sheet_name='Relatorio')
            st.download_button("📥 DESCARREGAR EXCEL", buf.getvalue(), "relatorio_pontos.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

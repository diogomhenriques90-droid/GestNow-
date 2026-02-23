import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# --- CONFIGURAÇÃO DE INTERFACE DE ALTA PRECISÃO ---
st.set_page_config(page_title="GestNow | Precision Control", layout="wide")

# Imagem de Login (Atualizada para refletir tecnologia/instrumentação)
IMG_URL = "https://raw.githubusercontent.com/diogofilipe24/gestnow/main/gestao_capa.png"

# Estilo CSS Customizado: Dark Mode & Cyan Glow (Azul Elétrico)
st.markdown("""
    <style>
    /* Remover elementos padrão do Streamlit */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Fundo Dark Profundo */
    .stApp {
        background-color: #0A192F;
        color: #E6F1FF;
    }
    
    /* Botões em Azul Elétrico / Ciano */
    .stButton>button {
        border-radius: 8px; 
        height: 3.5em; 
        background-color: #00D2FF; 
        color: #0A192F; 
        font-weight: bold; 
        width: 100%; 
        border: none;
        box-shadow: 0px 0px 15px rgba(0, 210, 255, 0.4);
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #0082A3;
        color: white;
        box-shadow: 0px 0px 25px rgba(0, 210, 255, 0.6);
    }
    
    /* Input Fields Estilizados */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: #112240 !important;
        color: #00D2FF !important;
        border: 1px solid #1E3A5F !important;
    }
    
    /* Container de Mensagem de Login */
    .brand-header {
        text-align: center;
        padding: 20px;
        border-bottom: 2px solid #00D2FF;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE DE DADOS ---
def carregar_dados(ficheiro, colunas):
    if os.path.exists(ficheiro): return pd.read_csv(ficheiro)
    return pd.DataFrame(columns=colunas)

df_users = carregar_dados("usuarios.csv", ["Nome", "Password", "Tipo"])
df_obras = carregar_dados("obras.csv", ["Nome"]).dropna()
df_registos = carregar_dados("registos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída", "Relatorio_Tecnico", "Evidencia_Visual"])

# --- CONTROLO DE ACESSO ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    # Cabeçalho de Marca de Honra
    st.markdown("<div class='brand-header'><h1>GESTNOW</h1><p>Precision Instrumentation & Control</p></div>", unsafe_allow_html=True)
    
    # Imagem de Entrada
    try:
        st.image(IMG_URL, use_container_width=True)
    except:
        st.write("A carregar sistema de segurança...")
    
    u = st.text_input("Credencial de Acesso")
    p = st.text_input("Código de Verificação", type="password")
    
    if st.button("AUTENTICAR SISTEMA"):
        match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
        if not match.empty:
            st.session_state.user = u
            st.session_state.tipo = match.iloc[0]['Tipo']
            st.rerun()
        else:
            st.error("Credenciais inválidas. Tente novamente.")
    st.stop()

# --- INTERFACE DE GESTÃO (ADMIN) ---
if st.session_state.tipo == "Admin":
    st.title("🖥️ Terminal de Controlo Estratégico")
    t1, t2, t3 = st.tabs(["📡 Recursos & Ativos", "📊 Monitorização de Dados", "📥 Exportação de Protocolos"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Configurar Novo Operador")
            n_u = st.text_input("Nome do Técnico")
            n_p = st.text_input("Senha de Acesso")
            n_t = st.selectbox("Nível de Permissão", ["Colaborador", "Chefe de Equipa", "Admin"])
            if st.button("Validar Novo Perfil"):
                new_u = pd.DataFrame([{"Nome": n_u, "Password": n_p, "Tipo": n_t}])
                pd.concat([df_users, new_u]).to_csv("usuarios.csv", index=False)
                st.success("Perfil ativado no sistema!"); st.rerun()
        with c2:
            st.subheader("Configurar Nova Unidade/Obra")
            n_o = st.text_input("Identificação da Unidade")
            if st.button("Ativar Unidade"):
                new_o = pd.DataFrame([{"Nome": n_o}])
                pd.concat([df_obras, new_o]).to_csv("obras.csv", index=False)
                st.success("Unidade registada na rede!"); st.rerun()

    with t2:
        st.subheader("Logs de Intervenção em Tempo Real")
        st.dataframe(df_registos, use_container_width=True)

    with t3:
        if not df_registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_registos.to_excel(writer, index=False)
            st.download_button("📥 DESCARREGAR RELATÓRIO TÉCNICO", buf.getvalue(), "GestNow_DataLog.xlsx")

# --- INTERFACE TÉCNICA (CHEFE E STAFF) ---
else:
    st.markdown(f"## 👤 Terminal: {st.session_state.user}")
    
    with st.container():
        unidade = st.selectbox("Unidade de Intervenção", ["-- Selecionar Unidade --"] + df_obras['Nome'].tolist())
        
        relatorio = ""
        foto_nome = "Sem Evidência"
        
        # Lógica Silenciosa para Chefes de Equipa
        if st.session_state.tipo == "Chefe de Equipa":
            st.markdown("---")
            st.subheader("📑 Relatório de Intervenção Técnica")
            relatorio = st.text_area("Descreva os procedimentos executados e calibrações efetuadas:")
            foto_file = st.file_uploader("📸 Evidência Fotográfica (Sensores/Painéis)", type=['png', 'jpg', 'jpeg'])
            if foto_file:
                foto_nome = f"evidencia_{st.session_state.user}_{datetime.now().strftime('%H%M%S')}.jpg"
        
        c1, c2 = st.columns(2)
        h_e = c1.time_input("Início da Atividade", datetime.now().replace(hour=8, minute=0))
        h_s = c2.time_input("Conclusão da Atividade", datetime.now().replace(hour=17, minute=0))
        
        if st.button("SUBMETER DADOS DE INTERVENÇÃO"):
            if unidade != "-- Selecionar Unidade --":
                novo = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Trabalhador": st.session_state.user,
                    "Obra": unidade,
                    "Entrada": h_e.strftime("%H:%M"),
                    "Saída": h_s.strftime("%H:%M"),
                    "Relatorio_Tecnico": relatorio,
                    "Evidencia_Visual": foto_nome
                }])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Dados transmitidos e guardados com sucesso!")
            else:
                st.error("Erro: Seleção de unidade obrigatória.")

if st.sidebar.button("Encerrar Sessão"):
    st.session_state.user = None
    st.rerun()

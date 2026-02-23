import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# --- CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="GestNow - DeltaPlus", layout="wide")

# Link da imagem de capa (Certifica-te que o ficheiro existe no GitHub)
IMG_URL = "https://raw.githubusercontent.com/diogofilipe24/gestnow/main/gestao_capa.png"

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {
        border-radius: 10px; height: 3.5em; background-color: #D32F2F; 
        color: white; font-weight: bold; width: 100%; border: none;
    }
    .quote-box {
        text-align:center; padding:15px; border-left: 5px solid #D32F2F; 
        background-color: #f1f1f1; font-style: italic; margin-bottom:20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- GESTÃO DE DADOS ---
def carregar_dados(ficheiro, colunas):
    if os.path.exists(ficheiro): return pd.read_csv(ficheiro)
    return pd.DataFrame(columns=colunas)

df_users = carregar_dados("usuarios.csv", ["Nome", "Password", "Tipo"])
if df_users.empty:
    df_users = pd.DataFrame([{"Nome": "Admin", "Password": "123", "Tipo": "Admin"}])
    df_users.to_csv("usuarios.csv", index=False)

df_obras = carregar_dados("obras.csv", ["Nome"]).dropna()
df_registos = carregar_dados("registos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída", "Relatorio_Obra", "Evidencia_Foto"])

# --- SISTEMA DE LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.image(IMG_URL, use_container_width=True)
    st.markdown("<div class='quote-box'>\"Quanto maior a liberdade, maior a responsabilidade.\"</div>", unsafe_allow_html=True)
    u = st.text_input("Utilizador")
    p = st.text_input("Password", type="password")
    if st.button("ENTRAR NA GESTNOW"):
        match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
        if not match.empty:
            st.session_state.user = u
            st.session_state.tipo = match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado.")
    st.stop()

# --- NÍVEL 1: ADMINISTRADOR ---
if st.session_state.tipo == "Admin":
    st.title("⚙️ Painel de Controlo DeltaPlus")
    t1, t2, t3 = st.tabs(["👥 Gestão de Staff", "📊 Auditoria de Obra", "📥 Exportar Dados"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Criar Novo Acesso")
            n_u = st.text_input("Nome")
            n_p = st.text_input("Senha")
            n_t = st.selectbox("Perfil", ["Colaborador", "Chefe de Equipa", "Admin"])
            if st.button("Registar Utilizador"):
                new_u = pd.DataFrame([{"Nome": n_u, "Password": n_p, "Tipo": n_t}])
                pd.concat([df_users, new_u]).to_csv("usuarios.csv", index=False)
                st.success("Criado com sucesso!"); st.rerun()
        with c2:
            st.subheader("Novos Projetos")
            n_o = st.text_input("Nome da Obra")
            if st.button("Ativar Obra"):
                new_o = pd.DataFrame([{"Nome": n_o}])
                pd.concat([df_obras, new_o]).to_csv("obras.csv", index=False)
                st.success("Obra Ativa!"); st.rerun()

    with t2:
        st.subheader("Visualização de Registos Real-Time")
        st.dataframe(df_registos, use_container_width=True)

    with t3:
        if not df_registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_registos.to_excel(writer, index=False, startrow=2)
                wb, ws = writer.book, writer.sheets['Sheet1']
                fmt = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#D32F2F', 'border': 1})
                ws.write('A1', 'RELATÓRIO DE AUDITORIA GESTNOW', wb.add_format({'bold': True, 'font_size': 14}))
                for i, col in enumerate(df_registos.columns): ws.write(2, i, col, fmt)
            st.download_button("📥 DESCARREGAR EXCEL DE GESTÃO", buf.getvalue(), "GestNow_Relatorio.xlsx")

# --- NÍVEL 2 E 3: COLABORADOR E CHEFE DE EQUIPA ---
else:
    st.image(IMG_URL, use_container_width=True)
    st.markdown(f"### 👋 Bem-vindo, {st.session_state.user}")
    st.info(f"Nível de Acesso: **{st.session_state.tipo}**")
    
    with st.form("form_ponto"):
        obra_sel = st.selectbox("Em que obra estás?", ["-- Selecionar Obra --"] + df_obras['Nome'].tolist())
        
        # Campo exclusivo para Chefes
        relatorio = ""
        foto_nome = "Sem Anexo"
        if st.session_state.tipo == "Chefe de Equipa":
            st.markdown("---")
            relatorio = st.text_area("Relatório de Obra (O que foi feito hoje?)")
            foto_file = st.file_uploader("📸 Anexar Evidência Visual", type=['png', 'jpg', 'jpeg'])
            if foto_file:
                foto_nome = f"foto_{st.session_state.user}_{datetime.now().strftime('%d%m_%H%M')}.jpg"
        
        c_e, c_s = st.columns(2)
        h_e = c_e.time_input("Hora de Entrada", datetime.now().replace(hour=8, minute=0))
        h_s = c_s.time_input("Hora de Saída", datetime.now().replace(hour=17, minute=0))
        
        btn_enviar = st.form_submit_button("SUBMETER REGISTO")
        
        if btn_enviar:
            if obra_sel != "-- Selecionar Obra --":
                novo_reg = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Trabalhador": st.session_state.user,
                    "Obra": obra_sel,
                    "Entrada": h_e.strftime("%H:%M"),
                    "Saída": h_s.strftime("%H:%M"),
                    "Relatorio_Obra": relatorio,
                    "Evidencia_Foto": foto_nome
                }])
                novo_reg.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Ponto registado com sucesso!")
            else:
                st.error("Erro: Tens de selecionar a obra.")

if st.sidebar.button("Terminar Sessão"):
    st.session_state.user = None
    st.rerun()

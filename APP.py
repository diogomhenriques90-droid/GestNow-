import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- 1. DESIGN E VISIBILIDADE (BRANCO NO ESCURO) ---
st.set_page_config(page_title="GestNow | Comando Central", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #FFFFFF !important; }
    .stButton>button { background-color: #00D2FF; color: #0A192F; font-weight: bold; border-radius: 5px; height: 3em; }
    input, select, textarea { background-color: #112240 !important; color: #FFFFFF !important; border: 2px solid #00D2FF !important; }
    label, p, h1, h2, h3, span { color: #FFFFFF !important; }
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
obras_db = engine("obras_lista.csv", ["Obra"])
frentes_db = engine("frentes_lista.csv", ["Obra", "Frente"])
registos = engine("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Entrada", "Saída", "Relatorio"])

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
    st.title("📊 Painel de Comando Administrativo")
    j_pessoal, j_obras, j_frentes, j_dados = st.tabs(["👥 Pessoal", "🏗️ Obras", "🚧 Frentes", "📋 Histórico"])

    with j_pessoal:
        st.subheader("Gestão de Equipa")
        c1, c2 = st.columns([1, 2])
        with c1:
            nu, np = st.text_input("Nome"), st.text_input("Senha")
            nt = st.selectbox("Cargo", ["Colaborador", "Chefe de Equipa", "Recursos Humanos"])
            if st.button("Registar"):
                users = pd.concat([users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": nt}])]).drop_duplicates(subset=['Nome'], keep='last')
                save(users, "usuarios.csv"); st.success("OK!"); st.rerun()
        with c2: st.dataframe(users, use_container_width=True)

    with j_obras:
        st.subheader("Criar Nova Obra Principal")
        c3, c4 = st.columns([1, 2])
        with c3:
            nova_o = st.text_input("Nome da Obra (ex: Sonae)")
            if st.button("Gravar Obra"):
                obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra": nova_o}])]).drop_duplicates()
                save(obras_db, "obras_lista.csv"); st.success("Obra Ativa!"); st.rerun()
        with c4: st.dataframe(obras_db, use_container_width=True)

    with j_frentes:
        st.subheader("Criar Frentes de Trabalho")
        c5, c6 = st.columns([1, 2])
        with c5:
            o_selec = st.selectbox("Para qual Obra?", ["-- Selecionar --"] + obras_db['Obra'].tolist())
            nova_f = st.text_input("Nome da Frente (ex: Caldeira 2)")
            if st.button("Ativar Frente"):
                if o_selec != "-- Selecionar --":
                    frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra": o_selec, "Frente": nova_f}])]).drop_duplicates()
                    save(frentes_db, "frentes_lista.csv"); st.success("Frente Criada!"); st.rerun()
        with c6: st.dataframe(frentes_db, use_container_width=True)

    with j_dados:
        st.dataframe(registos, use_container_width=True)
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: registos.to_excel(w, index=False)
            st.download_button("📥 DESCARREGAR EXCEL", buf.getvalue(), "GestNow_Total.xlsx")

# --- 5. REGISTO DE PONTO (DUAS JANELAS DE SELEÇÃO) ---
else:
    st.title("📊 Registo de Ponto")
    with st.form("ponto_form"):
        # Janela 1: Selecionar a Obra
        obra_escolhida = st.selectbox("1. Selecione a Obra", ["-- Selecionar --"] + obras_db['Obra'].tolist())
        
        # Janela 2: Filtrar Frentes baseado na Obra escolhida
        frentes_filtradas = frentes_db[frentes_db['Obra'] == obra_escolhida]['Frente'].tolist() if obra_escolhida != "-- Selecionar --" else []
        frente_escolhida = st.selectbox("2. Selecione a Frente de Trabalho", ["-- Selecionar --"] + frentes_filtradas)
        
        data_p = st.date_input("Data", datetime.now())
        c_h1, c_h2 = st.columns(2)
        h_e = c_h1.time_input("Entrada", datetime.now())
        h_s = c_h2.time_input("Saída", datetime.now())
        
        obs, foto = None, None
        if st.session_state.tipo == "Chefe de Equipa":
            st.markdown("---")
            st.subheader("🛡️ Área do Chefe")
            obs = st.text_area("Observações Técnicas")
            foto = st.file_uploader("📸 Foto da Intervenção", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("SUBMETER PONTO"):
            if obra_escolhida != "-- Selecionar --" and frente_escolhida != "-- Selecionar --":
                novo = pd.DataFrame([{
                    "Data": data_p.strftime("%d/%m/%Y"), "Técnico": st.session_state.user, 
                    "Obra": obra_escolhida, "Frente": frente_escolhida, 
                    "Entrada": h_e.strftime("%H:%M"), "Saída": h_s.strftime("%H:%M"), 
                    "Relatorio": obs if obs else "N/A"
                }])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Registo concluído!")
            else: st.error("Selecione Obra e Frente!")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

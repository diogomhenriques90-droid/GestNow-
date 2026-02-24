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
    .stButton>button { background-color: #00D2FF; color: #0A192F; font-weight: bold; border-radius: 5px; height: 3em; width: 100%; }
    .btn-delete>button { background-color: #FF4B4B !important; color: white !important; }
    input, select, textarea { background-color: #112240 !important; color: #FFFFFF !important; border: 2px solid #00D2FF !important; }
    label, p, h1, h2, h3, span { color: #FFFFFF !important; }
    .stTabs [aria-selected="true"] { background-color: #00D2FF !important; color: #0A192F !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS ---
def engine(f, col):
    if os.path.exists(f):
        try: 
            df = pd.read_csv(f, dtype=str)
            for c in df.columns: df[c] = df[c].str.strip()
            return df
        except: pass
    return pd.DataFrame(columns=col)

def save(df, f): 
    for col in df.columns: df[col] = df[col].astype(str).str.strip()
    df.to_csv(f, index=False)

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
        if u_input.lower() in ["diogo", "admin"] and p_input in ["rafael2026", "123", "DeltaPlus2026"]:
            st.session_state.user, st.session_state.tipo = u_input, "Admin"
            st.rerun()
        if not users.empty:
            match = users[(users['Nome'].str.lower() == u_input.lower()) & (users['Password'] == p_input)]
            if not match.empty:
                st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso Negado.")
    st.stop()

# --- 4. INTERFACE ADMIN (JANELAS COM REMOÇÃO) ---
if st.session_state.tipo == "Admin":
    st.title("📊 Painel de Comando Administrativo")
    j_pessoal, j_obras, j_frentes, j_dados = st.tabs(["👥 Pessoal", "🏗️ Obras", "🚧 Frentes", "📋 Histórico"])

    with j_pessoal:
        st.subheader("Gestão de Equipa")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### Adicionar Novo")
            nu = st.text_input("Nome").strip()
            np = st.text_input("Senha").strip()
            nt = st.selectbox("Cargo", ["Colaborador", "Chefe de Equipa", "Recursos Humanos"])
            if st.button("Registar"):
                if nu and np:
                    users = pd.concat([users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": nt}])]).drop_duplicates(subset=['Nome'], keep='last')
                    save(users, "usuarios.csv"); st.success(f"{nu} registado!"); st.rerun()
            
            st.markdown("---")
            st.markdown("### 🗑️ Eliminar Acesso")
            u_para_eliminar = st.selectbox("Selecionar Colaborador", ["-- Selecionar --"] + users['Nome'].tolist())
            st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
            if st.button("ELIMINAR DEFINITIVAMENTE"):
                if u_para_eliminar != "-- Selecionar --":
                    users = users[users['Nome'] != u_para_eliminar]
                    save(users, "usuarios.csv")
                    st.warning(f"{u_para_eliminar} removido!")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c2: 
            st.write("Lista Ativa")
            st.dataframe(users, use_container_width=True)

    # ... (Restantes janelas de Obras e Frentes mantêm-se iguais para garantir estabilidade)
    with j_obras:
        st.subheader("Criação de Obras")
        c3, c4 = st.columns([1, 2])
        with c3:
            nova_o = st.text_input("Nome da Obra").strip()
            if st.button("Gravar Obra"):
                if nova_o:
                    obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra": nova_o}])]).drop_duplicates()
                    save(obras_db, "obras_lista.csv"); st.success("Obra Ativa!"); st.rerun()
        with c4: st.dataframe(obras_db, use_container_width=True)

    with j_frentes:
        st.subheader("Criação de Frentes")
        c5, c6 = st.columns([1, 2])
        with c5:
            o_selec = st.selectbox("Para qual Obra?", ["-- Selecionar --"] + sorted(obras_db['Obra'].unique().tolist()))
            nova_f = st.text_input("Nome da Frente").strip()
            if st.button("Ativar Frente"):
                if o_selec != "-- Selecionar --" and nova_f:
                    frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra": o_selec, "Frente": nova_f}])]).drop_duplicates()
                    save(frentes_db, "frentes_lista.csv"); st.success("Frente Criada!"); st.rerun()
        with c6: st.dataframe(frentes_db, use_container_width=True)

    with j_dados:
        st.dataframe(registos, use_container_width=True)

# --- 5. REGISTO DE PONTO (SEM ALTERAÇÕES) ---
else:
    st.title("📊 Registo de Ponto")
    with st.form("ponto_form"):
        obra_escolhida = st.selectbox("Selecione a Obra", ["-- Selecionar --"] + sorted(obras_db['Obra'].unique().tolist()))
        frentes_filtradas = frentes_db[frentes_db['Obra'] == obra_escolhida]['Frente'].tolist() if obra_escolhida != "-- Selecionar --" else []
        frente_escolhida = st.selectbox("Selecione a Frente de Trabalho", ["-- Selecionar --"] + sorted(frentes_filtradas))
        
        data_p = st.date_input("Data", datetime.now())
        c_h1, c_h2 = st.columns(2)
        h_e = c_h1.time_input("Entrada", datetime.now())
        h_s = c_h2.time_input("Saída", datetime.now())
        
        if st.form_submit_button("SUBMETER"):
            if obra_escolhida != "-- Selecionar --" and frente_escolhida != "-- Selecionar --":
                novo = pd.DataFrame([{
                    "Data": data_p.strftime("%d/%m/%Y"), "Técnico": st.session_state.user, 
                    "Obra": obra_escolhida, "Frente": frente_escolhida, 
                    "Entrada": h_e.strftime("%H:%M"), "Saída": h_s.strftime("%H:%M"), 
                    "Relatorio": "N/A"
                }])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("✅ Ponto registado!")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

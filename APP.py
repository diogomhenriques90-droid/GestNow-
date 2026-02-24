import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- 1. CONFIGURAÇÃO E DESIGN DE ALTA VISIBILIDADE ---
st.set_page_config(page_title="GestNow | Comando", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    /* Fundo Escuro com Texto Branco para Visibilidade Total */
    .stApp { background-color: #0A192F; color: #FFFFFF !important; }
    
    /* Botões Ciano com Texto Escuro */
    .stButton>button { 
        background-color: #00D2FF; color: #0A192F; font-weight: bold; 
        border-radius: 5px; height: 3em; width: 100%; border: none;
    }
    
    /* Input de Texto com contraste reforçado */
    input, select, textarea { 
        background-color: #112240 !important; color: #FFFFFF !important; 
        border: 2px solid #00D2FF !important; 
    }
    
    /* Labels e Textos auxiliares em Branco */
    label, p, span, h1, h2, h3 { color: #FFFFFF !important; }
    
    /* Tabs com destaque */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #112240; border-radius: 5px; color: #FFFFFF; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00D2FF !important; color: #0A192F !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS COM REPARAÇÃO DE PASSWORDS ---
def engine(f, col):
    if os.path.exists(f):
        try:
            # Leitura forçada como string para não corromper passwords numéricas
            df = pd.read_csv(f, dtype=str)
            return df if not df.empty else pd.DataFrame(columns=col)
        except: pass
    return pd.DataFrame(columns=col)

def save(df, f): 
    df.to_csv(f, index=False)

# Carregamento de Bases
users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras = engine("obras.csv", ["Nome"])
registos = engine("registos.csv", ["Data", "Técnico", "Unidade", "Entrada", "Saída", "Relatorio"])

# --- 3. LOGIN (DIOGO MASTER ACCESS) ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>GESTNOW</h1>", unsafe_allow_html=True)
    u_input = st.text_input("Utilizador").strip()
    p_input = st.text_input("Palavra-Passe", type="password").strip()
    
    if st.button("ENTRAR"):
        # Chave Mestra de Emergência (Garante entrada sempre)
        if u_input.lower() in ["diogo", "rafael correia"] and p_input in ["rafael2026", "123"]:
            st.session_state.user, st.session_state.tipo = u_input, "Admin"
            st.rerun()
        
        # Verificação da Base de Dados (Recuperação de passes antigas)
        if not users.empty:
            match = users[(users['Nome'].str.strip().str.lower() == u_input.lower()) & 
                          (users['Password'].astype(str).str.strip() == p_input)]
            if not match.empty:
                st.session_state.user = match.iloc[0]['Nome']
                st.session_state.tipo = match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso Negado. Verifique as credenciais.")
    st.stop()

# --- 4. INTERFACE DE COMANDO ---
st.sidebar.markdown(f"### 👤 {st.session_state.user.upper()}")

if st.session_state.tipo == "Admin":
    st.title("📊 Painel de Monitorização") # Troca do Lápis pela Imagem de Monitorização
    t1, t2, t3, t4 = st.tabs(["👥 Colaboradores", "🏗️ Frentes de Obra", "📋 Registos", "📥 Exportar"])

    with t1:
        st.subheader("Gestão de Equipa")
        c1, c2 = st.columns([1, 2])
        with c1:
            nu = st.text_input("Nome")
            np = st.text_input("Senha (Nova ou Antiga)")
            if st.button("Gravar Acesso"):
                # Garante que não há duplicados e guarda como string
                new_user = pd.DataFrame([{"Nome": nu, "Password": str(np), "Tipo": "Colaborador"}])
                users = pd.concat([users, new_user]).drop_duplicates(subset=['Nome'], keep='last')
                save(users, "usuarios.csv"); st.success("Guardado!"); st.rerun()
        with c2:
            st.dataframe(users, use_container_width=True)
            u_rem = st.selectbox("Eliminar", ["--"] + users['Nome'].tolist())
            if st.button("Remover"):
                users = users[users['Nome'] != u_rem]
                save(users, "usuarios.csv"); st.rerun()

    with t2:
        st.subheader("Configurar Frentes de Obra")
        c3, c4 = st.columns([1, 2])
        with c3:
            no = st.text_input("ID da Obra / Local")
            if st.button("Confirmar Nova Frente"):
                # Correção do erro de criação de frentes
                new_obra = pd.DataFrame([{"Nome": no}])
                obras = pd.concat([obras, new_obra]).drop_duplicates().dropna()
                save(obras, "obras.csv"); st.success("Frente Ativada!"); st.rerun()
        with c4:
            st.write("Frentes Ativas no Sistema")
            st.dataframe(obras, use_container_width=True)
            o_rem = st.selectbox("Arquivar", ["--"] + obras['Nome'].tolist())
            if st.button("Eliminar Obra"):
                obras = obras[obras['Nome'] != o_rem]
                save(obras, "obras.csv"); st.rerun()

    with t3:
        st.dataframe(registos, use_container_width=True)

    with t4:
        if not registos.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: registos.to_excel(w, index=False)
            st.download_button("📥 EXPORTAR EXCEL", buf.getvalue(), "GestNow_Final.xlsx")

else: # --- MODO REGISTO DE PONTO ---
    st.title("📊 Registo de Ponto") # Troca da imagem do lápis aqui também
    with st.form("ponto_form"):
        frente = st.selectbox("Frente de Obra", ["-- Selecionar --"] + obras['Nome'].tolist())
        data_p = st.date_input("Data", datetime.now())
        h_e = st.time_input("Entrada", datetime.now())
        h_s = st.time_input("Saída", datetime.now())
        obs = st.text_area("Observações")
        if st.form_submit_button("SUBMETER"):
            if frente != "-- Selecionar --":
                novo = pd.DataFrame([{"Data": data_p.strftime("%d/%m/%Y"), "Técnico": st.session_state.user, "Unidade": frente, "Entrada": h_e.strftime("%H:%M"), "Saída": h_s.strftime("%H:%M"), "Relatorio": obs}])
                novo.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.success("Registado!")
            else: st.error("Selecione a Frente de Obra.")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

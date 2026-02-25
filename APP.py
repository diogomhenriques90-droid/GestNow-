import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. DESIGN ELITE (RECUPERADO E ESTÁVEL) ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .header-ponto { 
        background-color: #1A1C23; padding: 30px; border-radius: 20px; 
        text-align: center; border: 1px solid #30363D; margin-bottom: 25px;
    }
    .total-horas { font-size: 50px; font-weight: bold; color: #00FBFF; }
    .turno-card { 
        background: #1C2128; padding: 20px; border-radius: 15px; margin-bottom: 12px; 
        display: flex; justify-content: space-between; align-items: center;
        border-left: 5px solid #30363D;
    }
    .bola { height: 12px; width: 12px; border-radius: 50%; display: inline-block; }
    .bola-0 { background-color: #FF9500; box-shadow: 0 0 10px #FF9500; } 
    .bola-1 { background-color: #00FF41; box-shadow: 0 0 10px #00FF41; } 
    .bola-2 { background-color: #007AFF; box-shadow: 0 0 10px #007AFF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÃO DE CARREGAMENTO "FORÇADO" (LIMPA ERROS) ---
def load_data(file, cols):
    try:
        if os.path.exists(file) and os.stat(file).st_size > 0:
            df = pd.read_csv(file, dtype=str, on_bad_lines='skip')
            # Garante que as colunas existem
            for c in cols:
                if c not in df.columns: df[c] = "0"
            return df[cols]
    except:
        pass
    return pd.DataFrame(columns=cols)

# --- 3. INICIALIZAÇÃO ---
if 'user' not in st.session_state: st.session_state.user = None
if 'step' not in st.session_state: st.session_state.step = "login"

u_db = load_data("usuarios.csv", ["Nome", "Password", "Tipo"])
o_db = load_data("obras_lista.csv", ["Obra"])
r_db = load_data("registos.csv", ["Data", "Técnico", "Obra", "Turnos", "Status"])

# --- 4. LOGIN SEM BLOQUEIOS ---
if st.session_state.user is None:
    st.title("GestNow Login")
    u = st.text_input("Utilizador").strip()
    p = st.text_input("Password", type="password").strip()
    
    if st.button("ENTRAR"):
        # Super-Admin (Sempre funciona)
        if u.lower() == "admin" and p == "DeltaPlus2026":
            st.session_state.user = "Admin"
            st.session_state.tipo = "Admin"
            st.rerun()
        else:
            # Verifica na base de dados
            match = u_db[(u_db['Nome'] == u) & (u_db['Password'] == p)]
            if not match.empty:
                st.session_state.user = match.iloc[0]['Nome']
                st.session_state.tipo = match.iloc[0]['Tipo']
                st.rerun()
            else:
                st.error("Credenciais inválidas ou base de dados vazia.")
    st.stop()

# --- 5. INTERFACE ADMIN ---
if st.session_state.tipo == "Admin":
    st.sidebar.write(f"Sessão: {st.session_state.user}")
    menu = st.sidebar.radio("Menu", ["Aprovações", "Equipa", "Obras"])
    
    if menu == "Aprovações":
        st.subheader("Registos Pendentes")
        pend = r_db[r_db['Status'] == "0"]
        if pend.empty: st.info("Nada para aprovar.")
        for idx, row in pend.iterrows():
            st.write(f"👷 {row['Técnico']} | {row['Obra']}")
            if st.button(f"Aprovar {idx}", key=idx):
                r_db.at[idx, 'Status'] = "1"
                r_db.to_csv("registos.csv", index=False)
                st.rerun()

    elif menu == "Equipa":
        st.subheader("Novos Técnicos")
        nu = st.text_input("Nome")
        np = st.text_input("Senha")
        if st.button("Criar"):
            new_u = pd.DataFrame([{"Nome":nu, "Password":np, "Tipo":"Técnico"}])
            pd.concat([u_db, new_u]).to_csv("usuarios.csv", index=False)
            st.success("Criado!")
            st.rerun()
        st.table(u_db)

    elif menu == "Obras":
        st.subheader("Novas Obras")
        no = st.text_input("Nome da Obra")
        if st.button("Gravar Obra"):
            new_o = pd.DataFrame([{"Obra":no}])
            pd.concat([o_db, new_o]).drop_duplicates().to_csv("obras_lista.csv", index=False)
            st.success("Gravado!")
            st.rerun()
        st.table(o_db)

# --- 6. INTERFACE TÉCNICO (O QUE TU QUERES) ---
else:
    hoje = datetime.now().strftime("%d/%m/%Y")
    
    # Se ainda não escolheu obra, mostra a lista
    if 'obra_sel' not in st.session_state:
        st.subheader("🏢 Selecione a Obra")
        if o_db.empty:
            st.warning("O Admin ainda não criou obras.")
        for obra in o_db['Obra'].unique():
            if st.button(obra, use_container_width=True):
                st.session_state.obra_sel = obra
                st.rerun()
    else:
        # PÁGINA DO PONTO (Cores e Status)
        meu_reg = r_db[(r_db['Técnico'] == st.session_state.user) & (r_db['Data'] == hoje)]
        
        st.markdown(f"""
            <div class="header-ponto">
                <div class="total-horas">00:00</div>
                <div style="font-size:14px; opacity:0.7;">{st.session_state.obra_sel}</div>
                <div style="font-size:12px; opacity:0.5;">{hoje}</div>
            </div>
        """, unsafe_allow_html=True)

        # Mostrar turnos com as bolinhas
        if not meu_reg.empty:
            for t in meu_reg.iloc[0]['Turnos'].split(', '):
                status = meu_reg.iloc[0]['Status']
                st.markdown(f"""
                    <div class="turno-card">
                        <span>{t}</span>
                        <div class="bola bola-{status}"></div>
                    </div>
                """, unsafe_allow_html=True)

        if st.button("➕ Adicionar Horas"):
            # Lógica simplificada para não travar
            new_reg = pd.DataFrame([{"Data":hoje, "Técnico":st.session_state.user, "Obra":st.session_state.obra_sel, "Turnos":"08:00-17:00", "Status":"0"}])
            pd.concat([r_db, new_reg]).to_csv("registos.csv", index=False)
            st.rerun()

        if st.button("⬅️ Trocar Obra"):
            del st.session_state.obra_sel
            st.rerun()

if st.sidebar.button("Terminar Sessão"):
    st.session_state.clear()
    st.rerun()

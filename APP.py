import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO E DESIGN DARK PREMIUM (RECUPERADO) ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    
    /* Cabeçalho com Total Horas Ciano */
    .header-ponto { 
        background-color: #1A1C23; padding: 30px; border-radius: 20px; 
        text-align: center; border: 1px solid #30363D; margin-bottom: 25px;
    }
    .total-horas { font-size: 50px; font-weight: bold; color: #00FBFF; text-shadow: 0 0 15px rgba(0,251,255,0.3); }
    
    /* Cartões de Turno Modernos */
    .turno-card { 
        background: #1C2128; padding: 20px; border-radius: 15px; margin-bottom: 12px; 
        display: flex; justify-content: space-between; align-items: center;
        border: 1px solid #30363D;
    }
    
    /* Bolinhas de Status (Laranja, Verde, Azul) */
    .bola { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-left: 10px; }
    .bola-0 { background-color: #FF9500; box-shadow: 0 0 10px #FF9500; } /* Pendente */
    .bola-1 { background-color: #00FF41; box-shadow: 0 0 10px #00FF41; } /* Validado */
    .bola-2 { background-color: #007AFF; box-shadow: 0 0 10px #007AFF; } /* Finalizado */

    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; transition: 0.3s; }
    .stTextInput>div>div>input { background-color: #21262D; color: white; border: 1px solid #30363D; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTÃO DE DADOS À PROVA DE ERROS ---
def safe_load(file, cols):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, dtype=str, on_bad_lines='skip')
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def safe_save(df, file):
    df.to_csv(file, index=False)

# Inicialização das bases
u_db = safe_load("usuarios.csv", ["Nome", "Password", "Tipo"])
o_db = safe_load("obras_lista.csv", ["Obra"])
f_db = safe_load("frentes_lista.csv", ["Obra", "Frente"])
r_db = safe_load("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Status"])

# --- 3. LOGICA DE LOGIN (CORRIGIDA) ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align:center; color:#00FBFF;'>GestNow</h1>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Utilizador").strip()
        p = st.text_input("Password", type="password").strip()
        if st.button("ENTRAR"):
            if u.lower() == "admin" and p == "DeltaPlus2026":
                st.session_state.user, st.session_state.tipo = "Admin", "Admin"
                st.rerun()
            else:
                match = u_db[(u_db['Nome'] == u) & (u_db['Password'] == p)]
                if not match.empty:
                    st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
                    st.rerun()
                else: st.error("Acesso negado. Verifique os dados.")
    st.stop()

# --- 4. PAINEL ADMIN (GESTÃO DE EQUIPA E OBRAS) ---
if st.session_state.tipo == "Admin":
    st.title(f"Painel de Controlo")
    tab1, tab2, tab3 = st.tabs(["📝 Aprovações", "👥 Equipa", "🏗️ Obras"])

    with tab1:
        pend = r_db[r_db['Status'] == "0"]
        if pend.empty: st.info("Sem registos para validar.")
        for idx, row in pend.iterrows():
            with st.expander(f"👷 {row['Técnico']} - {row['Obra']}"):
                st.write(f"Horas: {row['Turnos']}")
                c1, c2 = st.columns(2)
                if c1.button("🟢 VALIDAR", key=f"v{idx}"):
                    r_db.at[idx, 'Status'] = "1"; safe_save(r_db, "registos.csv"); st.rerun()
                if c2.button("🔵 FINALIZAR", key=f"f{idx}"):
                    r_db.at[idx, 'Status'] = "2"; safe_save(r_db, "registos.csv"); st.rerun()

    with tab2:
        st.subheader("Gerir Técnicos")
        with st.form("add_user"):
            nu, np = st.text_input("Nome"), st.text_input("Senha")
            nt = st.selectbox("Cargo", ["Colaborador", "Chefe de Equipa"])
            if st.form_submit_button("Registar"):
                u_db = pd.concat([u_db, pd.DataFrame([{"Nome":nu, "Password":np, "Tipo":nt}])])
                safe_save(u_db, "usuarios.csv"); st.rerun()
        st.table(u_db[["Nome", "Tipo"]])

    with tab3:
        st.subheader("Gerir Obras")
        with st.form("add_obra"):
            no = st.text_input("Nome da Obra")
            nf = st.text_input("Frente de Trabalho")
            if st.form_submit_button("Gravar"):
                o_db = pd.concat([o_db, pd.DataFrame([{"Obra":no}])]).drop_duplicates()
                f_db = pd.concat([f_db, pd.DataFrame([{"Obra":no, "Frente":nf}])]).drop_duplicates()
                safe_save(o_db, "obras_lista.csv"); safe_save(f_db, "frentes_lista.csv"); st.rerun()
        st.table(f_db)

# --- 5. INTERFACE TÉCNICO (O "REGISTO DE PONTO" ELITE) ---
else:
    if 'obra_sel' not in st.session_state:
        st.subheader("Selecione a Obra")
        for o in o_db['Obra'].unique():
            if st.button(f"🏗️ {o}", key=o): 
                st.session_state.obra_sel = o; st.rerun()
    else:
        hoje = datetime.now().strftime("%d/%m/%Y")
        meu_reg = r_db[(r_db['Técnico'] == st.session_state.user) & (r_db['Data'] == hoje)]
        
        # Cálculo Total
        total_m = 0
        if not meu_reg.empty:
            for t in str(meu_reg.iloc[0]['Turnos']).split(', '):
                try:
                    i, f = t.split('-')
                    t1, t2 = datetime.strptime(i, "%H:%M"), datetime.strptime(f, "%H:%M")
                    total_m += (t2 - t1).total_seconds() / 60
                except: continue
        
        # UI Premium
        st.markdown(f"""
            <div class="header-ponto">
                <div style="text-transform: uppercase; font-size: 12px; opacity: 0.7;">Total de Horas Hoje</div>
                <div class="total-horas">{int(total_m//60):02d}:{int(total_m%60):02d}</div>
                <div style="margin-top: 10px;">{st.session_state.obra_sel} | {hoje}</div>
            </div>
            """, unsafe_allow_html=True)

        # Listagem de Turnos com Bolinhas
        if not meu_reg.empty:
            for t in meu_reg.iloc[0]['Turnos'].split(', '):
                st_id = meu_reg.iloc[0]['Status']
                st.markdown(f"""
                    <div class="turno-card">
                        <div>
                            <div style="font-size: 11px; color: #8E8E93;">TURNO</div>
                            <div style="font-size: 18px; font-weight: bold;">{t}</div>
                        </div>
                        <div class="bola bola-{st_id}"></div>
                    </div>
                """, unsafe_allow_html=True)

        with st.expander("➕ ADICIONAR TURNO"):
            c1, c2 = st.columns(2)
            hi = c1.time_input("Início", datetime.now().replace(hour=8, minute=0))
            hf = c2.time_input("Fim", datetime.now().replace(hour=17, minute=0))
            if st.button("GRAVAR"):
                txt = f"{hi.strftime('%H:%M')}-{hf.strftime('%H:%M')}"
                if meu_reg.empty:
                    new_l = pd.DataFrame([{"Data":hoje, "Técnico":st.session_state.user, "Obra":st.session_state.obra_sel, "Frente":"Geral", "Turnos":txt, "Status":"0"}])
                    r_db = pd.concat([r_db, new_l])
                else:
                    r_db.loc[meu_reg.index[0], 'Turnos'] += f", {txt}"
                safe_save(r_db, "registos.csv"); st.rerun()

        if st.sidebar.button("Voltar / Mudar Obra"):
            del st.session_state.obra_sel; st.rerun()

if st.sidebar.button("Sair"): st.session_state.user = None; st.rerun()


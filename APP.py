import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. DESIGN PREMIUM COM CORES DE STATUS ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    
    /* Cabeçalho das fotos */
    .header-ponto { background-color: #1A1A1A; color: white; padding: 35px 20px; text-align: center; border-radius: 0 0 30px 30px; margin-bottom: 20px; }
    .total-horas { font-size: 55px; font-weight: bold; color: #00D1FF; line-height: 1; }
    .sub-header { font-size: 13px; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }

    /* Cartões com a Bolinha de Status */
    .turno-card { 
        background: white; padding: 18px; border-radius: 15px; margin-bottom: 12px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; 
    }
    .status-bola { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-left: 8px; }
    .bola-0 { background-color: #FF9500; box-shadow: 0 0 8px #FF9500; } /* Laranja: Pendente */
    .bola-1 { background-color: #34C759; box-shadow: 0 0 8px #34C759; } /* Verde: Validado */
    .bola-2 { background-color: #007AFF; box-shadow: 0 0 8px #007AFF; } /* Azul: Finalizado */

    .label-hora { color: #8E8E93; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .valor-hora { color: #1C1C1E; font-size: 18px; font-weight: bold; }
    
    .stButton>button { border-radius: 12px; font-weight: bold; height: 3.5em; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE DADOS ---
def load_db(f, cols):
    if os.path.exists(f):
        try: return pd.read_csv(f, dtype=str)
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_db(df, f):
    df.to_csv(f, index=False)

def calc_total(turnos_str):
    if not turnos_str or pd.isna(turnos_str): return "00:00"
    m = 0
    for t in str(turnos_str).split(', '):
        try:
            i, f = t.split('-')
            t1, t2 = datetime.strptime(i.strip(), "%H:%M"), datetime.strptime(f.strip(), "%H:%M")
            m += (t2 - t1).total_seconds() / 60
        except: continue
    return f"{int(m // 60):02d}:{int(m % 60):02d}"

# Bases
u_db = load_db("usuarios.csv", ["Nome", "Password", "Tipo"])
o_db = load_db("obras_lista.csv", ["Obra"])
f_db = load_data("frentes_lista.csv", ["Obra", "Frente"]) # Mantive para não quebrar
r_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Status"])

# --- 3. LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h2 style='text-align:center; padding-top:20px;'>GestNow</h2>", unsafe_allow_html=True)
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
            else: st.error("Incorreto.")
    st.stop()

# --- 4. PAINEL ADMIN (VALIDAÇÃO COM CORES) ---
if st.session_state.tipo == "Admin":
    st.title("Gestão Central")
    t1, t2, t3 = st.tabs(["🟠 Validar", "👥 Equipa", "🏗️ Obras"])
    
    with t1:
        pend = r_db[r_db['Status'] == "0"]
        if pend.empty: st.success("Sem pendentes!")
        for idx, row in pend.iterrows():
            with st.container():
                st.write(f"👷 **{row['Técnico']}** | {row['Obra']}")
                st.info(f"Horas: {row['Turnos']}")
                c1, c2 = st.columns(2)
                if c1.button(f"🟢 Validar", key=f"v{idx}"):
                    r_db.at[idx, 'Status'] = "1"; save_db(r_db, "registos.csv"); st.rerun()
                if c2.button(f"🔵 Finalizar", key=f"f{idx}"):
                    r_db.at[idx, 'Status'] = "2"; save_db(r_db, "registos.csv"); st.rerun()

    # (Lógica de Equipa e Obras simplificada aqui para focar no visual que pediste)
    with t3:
        with st.form("nova_obra"):
            no = st.text_input("Nova Obra")
            if st.form_submit_button("Gravar"):
                o_db = pd.concat([o_db, pd.DataFrame([{"Obra":no}])]).drop_duplicates()
                save_db(o_db, "obras_lista.csv"); st.rerun()

# --- 5. INTERFACE TÉCNICO (O VISUAL QUE TU QUERES) ---
else:
    if 'step' not in st.session_state: st.session_state.step = "obra"
    
    if st.session_state.step == "obra":
        st.subheader("Selecione a Obra")
        for o in o_db['Obra'].unique():
            if st.button(o): st.session_state.obra_ativa = o; st.session_state.step = "ponto"; st.rerun()
    
    elif st.session_state.step == "ponto":
        hoje = datetime.now().strftime("%d/%m/%Y")
        meu_reg = r_db[(r_db['Técnico'] == st.session_state.user) & (r_db['Data'] == hoje)]
        total = calc_total(meu_reg.iloc[0]['Turnos']) if not meu_reg.empty else "00:00"

        # HEADER BLACK PREMIUM
        st.markdown(f"""
            <div class="header-ponto">
                <div class="sub-header">Total de Horas</div>
                <div class="total-horas">{total}</div>
                <div class="sub-header">{hoje} | {st.session_state.obra_ativa}</div>
            </div>
            """, unsafe_allow_html=True)

        # LISTA COM AS BOLINHAS DE CORES
        if not meu_reg.empty:
            for _, row in meu_reg.iterrows():
                status = row['Status'] # 0, 1 ou 2
                status_nome = ["Pendente", "Validado", "Finalizado"][int(status)]
                for t in row['Turnos'].split(', '):
                    h1, h2 = t.split('-')
                    st.markdown(f"""
                        <div class="turno-card">
                            <div>
                                <div class="label-hora">Entrada / Saída</div>
                                <div class="valor-hora">{h1} — {h2}</div>
                            </div>
                            <div style="display:flex; align-items:center;">
                                <span style="font-size:12px; color:#8E8E93;">{status_nome}</span>
                                <span class="status-bola bola-{status}"></span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

        if st.button("➕ Adicionar Turno"):
            # Aqui abririas o expander ou form para adicionar
            st.info("Clica em 'Mudar Obra' para resetar por agora.")
        
        if st.button("⬅️ Mudar Obra"): st.session_state.step = "obra"; st.rerun()

if st.sidebar.button("Logout"): st.session_state.user = None; st.rerun()

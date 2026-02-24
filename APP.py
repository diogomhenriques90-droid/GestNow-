import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. DESIGN ELITE COM STATUS COLORIDO ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F8F9FA; }
    
    /* Cabeçalho Premium das fotos */
    .header-ponto { 
        background-color: #1A1A1A; color: white; padding: 40px 20px; 
        text-align: center; border-radius: 0 0 35px 35px; margin-bottom: 25px; 
    }
    .total-horas { font-size: 65px; font-weight: 800; color: #00D1FF; line-height: 1; }
    .sub-header { font-size: 13px; opacity: 0.7; text-transform: uppercase; letter-spacing: 2px; margin-top: 10px; }

    /* Cartões de Turno com Indicador de Status */
    .turno-card { 
        background: white; padding: 20px; border-radius: 20px; margin-bottom: 15px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.06); display: flex; justify-content: space-between; align-items: center; 
        border-left: 6px solid #DDD;
    }
    /* Cores das Bordas e Bolinhas por Status */
    .status-0 { border-left-color: #FF9500 !important; } /* Laranja: Pendente */
    .status-1 { border-left-color: #34C759 !important; } /* Verde: Validado */
    .status-2 { border-left-color: #007AFF !important; } /* Azul: Finalizado */

    .bola { height: 14px; width: 14px; border-radius: 50%; display: inline-block; margin-left: 10px; }
    .bola-0 { background-color: #FF9500; box-shadow: 0 0 10px rgba(255,149,0,0.5); }
    .bola-1 { background-color: #34C759; box-shadow: 0 0 10px rgba(52,199,89,0.5); }
    .bola-2 { background-color: #007AFF; box-shadow: 0 0 10px rgba(0,122,255,0.5); }

    .label-h { color: #8E8E93; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .valor-h { color: #1C1C1E; font-size: 20px; font-weight: 700; }
    
    div.stButton > button { border-radius: 15px; font-weight: 700; height: 3.8em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTÃO DE DADOS (CORRIGIDO) ---
def load_db(file, cols):
    if os.path.exists(file) and os.stat(file).st_size > 0:
        try:
            df = pd.read_csv(file, dtype=str)
            return df[cols] if all(c in df.columns for c in cols) else pd.DataFrame(columns=cols)
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_db(df, file):
    df.to_csv(file, index=False)

def calc_total(turnos_str):
    if not turnos_str or pd.isna(turnos_str): return "00:00"
    minutos = 0
    for t in str(turnos_str).split(', '):
        try:
            i, f = t.split('-')
            t1, t2 = datetime.strptime(i.strip(), "%H:%M"), datetime.strptime(f.strip(), "%H:%M")
            minutos += (t2 - t1).total_seconds() / 60
        except: continue
    return f"{int(minutos // 60):02d}:{int(minutos % 60):02d}"

# Bases de Dados
u_db = load_db("usuarios.csv", ["Nome", "Password", "Tipo"])
o_db = load_db("obras_lista.csv", ["Obra"])
f_db = load_db("frentes_lista.csv", ["Obra", "Frente"])
r_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Status"])

# --- 3. LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h2 style='text-align:center; padding-top:30px;'>GestNow Login</h2>", unsafe_allow_html=True)
    u = st.text_input("Utilizador").strip()
    p = st.text_input("Password", type="password").strip()
    
    if st.button("ENTRAR", use_container_width=True):
        if u.lower() == "admin" and p == "DeltaPlus2026":
            st.session_state.user, st.session_state.tipo = "Admin", "Admin"
            st.rerun()
        else:
            match = u_db[(u_db['Nome'] == u) & (u_db['Password'] == p)]
            if not match.empty:
                st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

# --- 4. PAINEL ADMIN (APROVAÇÕES COLORIDAS) ---
if st.session_state.tipo == "Admin":
    st.markdown("### Painel de Controlo")
    tab1, tab2, tab3 = st.tabs(["🟠 Validar", "👥 Equipa", "🏗️ Obras"])

    with tab1:
        pend = r_db[r_db['Status'] == "0"]
        if pend.empty: st.info("Não existem registos para validar.")
        for idx, row in pend.iterrows():
            with st.container():
                st.markdown(f"**{row['Técnico']}** | {row['Obra']} ({row['Data']})")
                st.write(f"Horas: {row['Turnos']}")
                c1, c2 = st.columns(2)
                if c1.button("🟢 Validar", key=f"v{idx}"):
                    r_db.at[idx, 'Status'] = "1"; save_db(r_db, "registos.csv"); st.rerun()
                if c2.button("🔵 Finalizar", key=f"f{idx}"):
                    r_db.at[idx, 'Status'] = "2"; save_db(r_db, "registos.csv"); st.rerun()

    with tab2:
        with st.form("add_tecnico"):
            nu, np = st.text_input("Nome"), st.text_input("Senha")
            if st.form_submit_button("Criar Técnico"):
                u_db = pd.concat([u_db, pd.DataFrame([{"Nome":nu, "Password":np, "Tipo":"Técnico"}])])
                save_db(u_db, "usuarios.csv"); st.rerun()
        st.dataframe(u_db[["Nome", "Tipo"]], use_container_width=True)

    with tab3:
        with st.form("add_obra"):
            no, nf = st.text_input("Obra"), st.text_input("Frente")
            if st.form_submit_button("Gravar"):
                o_db = pd.concat([o_db, pd.DataFrame([{"Obra":no}])]).drop_duplicates()
                f_db = pd.concat([f_db, pd.DataFrame([{"Obra":no, "Frente":nf}])]).drop_duplicates()
                save_db(o_db, "obras_lista.csv"); save_db(f_db, "frentes_lista.csv"); st.rerun()
        st.dataframe(f_db, use_container_width=True)

# --- 5. INTERFACE TÉCNICO (O VISUAL COMPLETO) ---
else:
    if 'step' not in st.session_state: st.session_state.step = "obra"
    
    if st.session_state.step == "obra":
        st.markdown("### Selecione a Obra")
        for o in o_db['Obra'].unique():
            if st.button(f"🏢 {o}", use_container_width=True):
                st.session_state.obra_ok, st.session_state.step = o, "ponto"; st.rerun()
    
    elif st.session_state.step == "ponto":
        hoje = datetime.now().strftime("%d/%m/%Y")
        meu_reg = r_db[(r_db['Técnico'] == st.session_state.user) & (r_db['Data'] == hoje)]
        total = calc_total(meu_reg.iloc[0]['Turnos']) if not meu_reg.empty else "00:00"

        # HEADER PRETO PREMIUM
        st.markdown(f"""
            <div class="header-ponto">
                <div class="total-horas">{total}</div>
                <div class="sub-header">Horas Totais Hoje</div>
                <div style="margin-top:10px; font-size:12px; opacity:0.6;">{hoje} | {st.session_state.obra_ok}</div>
            </div>
            """, unsafe_allow_html=True)

        # LISTA COM STATUS COLORIDO (BOLINHAS)
        if not meu_reg.empty:
            for _, row in meu_reg.iterrows():
                st_id = row['Status']
                st_txt = ["Pendente", "Validado", "Finalizado"][int(st_id)]
                for t in row['Turnos'].split(', '):
                    h1, h2 = t.split('-')
                    st.markdown(f"""
                        <div class="turno-card status-{st_id}">
                            <div>
                                <div class="label-h">Entrada / Saída</div>
                                <div class="valor-h">{h1} — {h2}</div>
                            </div>
                            <div style="display:flex; align-items:center;">
                                <span style="font-size:12px; color:#8E8E93;">{st_txt}</span>
                                <span class="bola bola-{st_id}"></span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

        with st.expander("➕ ADICIONAR REGISTO"):
            c1, c2 = st.columns(2)
            hi = c1.time_input("Início", datetime.now().replace(hour=8, minute=0))
            hf = c2.time_input("Fim", datetime.now().replace(hour=17, minute=0))
            if st.button("GRAVAR HORAS", use_container_width=True):
                novo_t = f"{hi.strftime('%H:%M')}-{hf.strftime('%H:%M')}"
                if meu_reg.empty:
                    nova_l = pd.DataFrame([{"Data":hoje, "Técnico":st.session_state.user, "Obra":st.session_state.obra_ok, "Frente":"Geral", "Turnos":novo_t, "Status":"0"}])
                    r_db = pd.concat([r_db, nova_l])
                else:
                    r_db.loc[meu_reg.index[0], 'Turnos'] += f", {novo_t}"
                save_db(r_db, "registos.csv"); st.rerun()

        if st.button("⬅️ MUDAR OBRA"): st.session_state.step = "obra"; st.rerun()

if st.sidebar.button("Logout"): st.session_state.user = None; st.rerun()

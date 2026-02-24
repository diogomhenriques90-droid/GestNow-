import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. DESIGN PREMIUM (O REGRESSO DO VISUAL DAS FOTOS) ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    /* Cabeçalho igual à foto do calendário */
    .header-ponto { background-color: #1A1A1A; color: white; padding: 30px 20px; text-align: center; border-radius: 0 0 25px 25px; margin-bottom: 20px; }
    .total-horas { font-size: 50px; font-weight: bold; color: #FFFFFF; line-height: 1; }
    .sub-header { font-size: 14px; opacity: 0.7; margin-top: 5px; }
    /* Cartões brancos modernos */
    .turno-card { background: white; padding: 18px; border-radius: 15px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; }
    .turno-info { display: flex; flex-direction: column; }
    .label-hora { color: #8E8E93; font-size: 10px; text-transform: uppercase; font-weight: 700; }
    .valor-hora { color: #1C1C1E; font-size: 18px; font-weight: bold; margin-bottom: 5px; }
    /* Botões redondos */
    .stButton>button { border-radius: 12px; font-weight: bold; height: 3.5em; width: 100%; transition: 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS ---
def safe_load(f, cols):
    if os.path.exists(f):
        try:
            df = pd.read_csv(f, dtype=str, on_bad_lines='skip')
            return df[cols] if all(c in df.columns for c in cols) else pd.DataFrame(columns=cols)
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_db(df, f):
    df.to_csv(f, index=False)

def calc_total_horas(turnos):
    minutos = 0
    for t in turnos:
        try:
            i, f = t.split('-')
            t1, t2 = datetime.strptime(i.strip(), "%H:%M"), datetime.strptime(f.strip(), "%H:%M")
            diff = (t2 - t1).total_seconds() / 60
            if diff > 0: minutos += diff
        except: continue
    return f"{int(minutos // 60):02d}:{int(minutos % 60):02d}"

# Bases de dados
users_db = safe_load("usuarios.csv", ["Nome", "Password", "Tipo"])
obras_db = safe_load("obras_lista.csv", ["Obra"])
frentes_db = safe_load("frentes_lista.csv", ["Obra", "Frente"])
registos_db = safe_load("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status"])

# --- 3. GESTÃO DE ACESSO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'user' not in st.session_state: st.session_state.user = None
if 'tipo' not in st.session_state: st.session_state.tipo = None
if 'step' not in st.session_state: st.session_state.step = "obra"
if 'turnos_temp' not in st.session_state: st.session_state.turnos_temp = []

if not st.session_state.autenticado:
    st.markdown("<h2 style='text-align:center; padding-top:20px;'>GestNow Login</h2>", unsafe_allow_html=True)
    u = st.text_input("Utilizador").strip().lower()
    p = st.text_input("Palavra-passe", type="password").strip()
    
    if st.button("ENTRAR"):
        if u == "admin" and p == "DeltaPlus2026":
            st.session_state.autenticado, st.session_state.user, st.session_state.tipo = True, "Admin", "Admin"
            st.rerun()
        else:
            match = users_db[(users_db['Nome'].str.lower() == u) & (users_db['Password'] == p)]
            if not match.empty:
                st.session_state.autenticado, st.session_state.user, st.session_state.tipo = True, match.iloc[0]['Nome'], match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

# --- 4. PAINEL ADMIN (GESTÃO) ---
if st.session_state.tipo == "Admin":
    st.markdown(f"<h3 style='text-align:center;'>Painel de Controlo: {st.session_state.user}</h3>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["📋 Aprovações", "👥 Equipa", "🏗️ Obras"])

    with t1:
        pend = registos_db[registos_db['Status'] == "0"]
        if pend.empty: st.info("Sem registos pendentes.")
        for idx, row in pend.iterrows():
            st.markdown(f"**{row['Técnico']}** | {row['Data']}")
            st.write(f"Turnos: {row['Turnos']}")
            if st.button(f"Validar {row['Técnico']}", key=idx):
                registos_db.at[idx, 'Status'] = "1"; save_db(registos_db, "registos.csv"); st.rerun()

    with t2:
        with st.form("add_tecnico"):
            nu, np = st.text_input("Nome"), st.text_input("Senha")
            if st.form_submit_button("Criar Técnico"):
                users_db = pd.concat([users_db, pd.DataFrame([{"Nome":nu, "Password":np, "Tipo":"Colaborador"}])])
                save_db(users_db, "usuarios.csv"); st.rerun()
        st.dataframe(users_db)

    with t3:
        with st.form("add_obra"):
            no, nf = st.text_input("Obra"), st.text_input("Frente")
            if st.form_submit_button("Gravar Obra"):
                obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra":no}])]).drop_duplicates()
                frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra":no, "Frente":nf}])]).drop_duplicates()
                save_db(obras_db, "obras_lista.csv"); save_db(frentes_db, "frentes_lista.csv"); st.rerun()
        st.dataframe(frentes_db)

# --- 5. INTERFACE TÉCNICO (O VISUAL DAS FOTOS) ---
else:
    if st.session_state.step == "obra":
        st.markdown("### Selecione a Obra")
        for o in obras_db['Obra'].unique():
            if st.button(f"🏢 {o}"):
                st.session_state.obra_ativa, st.session_state.step = o, "frente"; st.rerun()
    
    elif st.session_state.step == "frente":
        st.markdown(f"**Obra:** {st.session_state.obra_ativa}")
        for f in frentes_db[frentes_db['Obra'] == st.session_state.obra_ativa]['Frente']:
            if st.button(f"🚧 {f}"):
                st.session_state.frente_ativa, st.session_state.step = f, "ponto"; st.rerun()
        if st.button("⬅️ Voltar"): st.session_state.step = "obra"; st.rerun()

    elif st.session_state.step == "ponto":
        data_sel = st.date_input("Data", datetime.now())
        ds = data_sel.strftime("%d/%m/%Y")
        meu_reg = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == ds)]
        
        exibir = st.session_state.turnos_temp if meu_reg.empty else meu_reg.iloc[0]['Turnos'].split(', ')
        total = calc_total_horas(exibir)

        # CABEÇALHO PRETO IGUAL À FOTO
        st.markdown(f"""<div class="header-ponto"><div class="sub-header">Horas Totais</div><div class="total-horas">{total}</div><div class="sub-header">{ds} | {st.session_state.frente_ativa}</div></div>""", unsafe_allow_html=True)

        # EXIBIÇÃO EM CARTÕES (FOTO 2)
        if not meu_reg.empty:
            for t in meu_reg.iloc[0]['Turnos'].split(', '):
                h1, h2 = t.split('-')
                st.markdown(f"""<div class="turno-card"><div class="turno-info"><span class="label-hora">Entrada</span><span class="valor-hora">{h1}</span><span class="label-hora">Saída</span><span class="valor-hora">{h2}</span></div><div style="color:#34C759; font-weight:bold;">● Enviado</div></div>""", unsafe_allow_html=True)
        
        for t in st.session_state.turnos_temp:
            h1, h2 = t.split('-')
            st.markdown(f"""<div class="turno-card" style="border-left: 5px solid #FF9500;"><div class="turno-info"><span class="label-hora">Entrada</span><span class="valor-hora">{h1}</span><span class="label-hora">Saída</span><span class="valor-hora">{h2}</span></div><div style="color:#FF9500;">Pendente</div></div>""", unsafe_allow_html=True)

        with st.expander("➕ Adicionar Bloco"):
            c1, c2 = st.columns(2)
            hi = c1.time_input("Início", datetime.now().replace(hour=8, minute=0))
            hf = c2.time_input("Fim", datetime.now().replace(hour=17, minute=0))
            if st.button("Confirmar Horas"):
                st.session_state.turnos_temp.append(f"{hi.strftime('%H:%M')}-{hf.strftime('%H:%M')}"); st.rerun()

        if st.session_state.turnos_temp:
            if st.button("🚀 SUBMETER RELATÓRIO", use_container_width=True):
                nr = pd.DataFrame([{"Data":ds, "Técnico":st.session_state.user, "Obra":st.session_state.obra_ativa, "Frente":st.session_state.frente_ativa, "Turnos":", ".join(st.session_state.turnos_temp), "Relatorio":"", "Status":"0"}])
                save_db(pd.concat([registos_db, nr]), "registos.csv")
                st.session_state.turnos_temp = []; st.success("Enviado!"); st.rerun()
        
        if st.button("⬅️ Trocar Obra"): st.session_state.step = "obra"; st.rerun()

if st.sidebar.button("Logout"): st.session_state.autenticado = False; st.rerun()

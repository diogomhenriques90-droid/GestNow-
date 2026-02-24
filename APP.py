import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. DESIGN DE ELITE (FOTOS) ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    /* Estilo do Cabeçalho Preto (Foto 2) */
    .header-ponto { 
        background-color: #1A1A1A; color: white; padding: 30px 20px; 
        text-align: center; border-radius: 0 0 25px 25px; margin-bottom: 25px; 
    }
    .total-horas { font-size: 55px; font-weight: bold; color: #FFFFFF; line-height: 1; }
    .sub-header { font-size: 14px; opacity: 0.8; margin-top: 5px; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Cartões de Registos (Foto 1) */
    .turno-card { 
        background: white; padding: 20px; border-radius: 18px; 
        margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        display: flex; justify-content: space-between; align-items: center; 
    }
    .label-hora { color: #8E8E93; font-size: 11px; text-transform: uppercase; font-weight: 700; margin-bottom: 2px; }
    .valor-hora { color: #1C1C1E; font-size: 20px; font-weight: bold; }
    
    /* Botões Arredondados */
    .stButton>button { 
        border-radius: 14px; font-weight: bold; height: 3.8em; 
        transition: all 0.2s ease; border: none;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f0f2f6; border-radius: 10px; padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTÃO DE DADOS ---
def load_db(f, cols):
    if os.path.exists(f):
        try: return pd.read_csv(f, dtype=str)
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_db(df, f):
    df.to_csv(f, index=False)

def calc_total(turnos_str):
    minutos = 0
    if not turnos_str: return "00:00"
    for t in turnos_str.split(', '):
        try:
            i, f = t.split('-')
            t1, t2 = datetime.strptime(i.strip(), "%H:%M"), datetime.strptime(f.strip(), "%H:%M")
            minutos += (t2 - t1).total_seconds() / 60
        except: continue
    return f"{int(minutos // 60):02d}:{int(minutos % 60):02d}"

# Carregar Bases
users_db = load_db("usuarios.csv", ["Nome", "Password", "Tipo"])
obras_db = load_db("obras_lista.csv", ["Obra"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente"])
registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Status"])

# --- 3. LOGIN ROBUSTO ---
if 'user' not in st.session_state: st.session_state.user = None
if 'step' not in st.session_state: st.session_state.step = "obra"

if st.session_state.user is None:
    st.markdown("<h1 style='text-align:center;'>GestNow Login</h1>", unsafe_allow_html=True)
    u = st.text_input("Utilizador").strip()
    p = st.text_input("Palavra-passe", type="password").strip()
    
    if st.button("ENTRAR", use_container_width=True):
        if u.lower() == "admin" and p == "DeltaPlus2026":
            st.session_state.user, st.session_state.tipo = "Admin", "Admin"
            st.rerun()
        else:
            match = users_db[(users_db['Nome'] == u) & (users_db['Password'] == p)]
            if not match.empty:
                st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

# --- 4. ÁREA ADMINISTRATIVA ---
if st.session_state.tipo == "Admin":
    st.markdown(f"## Painel de Controlo")
    t1, t2, t3 = st.tabs(["📋 Aprovações", "👥 Técnicos", "🏗️ Obras"])

    with t1:
        pendentes = registos_db[registos_db['Status'] == "0"]
        if pendentes.empty: st.info("Não há registos pendentes.")
        for idx, row in pendentes.iterrows():
            with st.container():
                st.markdown(f"**Técnico:** {row['Técnico']} | **Obra:** {row['Obra']}")
                st.write(f"Horas: {row['Turnos']} ({row['Data']})")
                if st.button(f"✅ Aprovar {row['Técnico']}", key=f"ap{idx}"):
                    registos_db.at[idx, 'Status'] = "1"
                    save_db(registos_db, "registos.csv"); st.rerun()
            st.divider()

    with t2:
        st.subheader("Gerir Equipa")
        with st.form("add_user"):
            nu, np = st.text_input("Nome do Técnico"), st.text_input("Senha")
            if st.form_submit_button("CRIAR ACESSO"):
                users_db = pd.concat([users_db, pd.DataFrame([{"Nome":nu, "Password":np, "Tipo":"Técnico"}])])
                save_db(users_db, "usuarios.csv"); st.success("Criado!"); st.rerun()
        st.table(users_db[["Nome", "Tipo"]])

    with t3:
        st.subheader("Gerir Obras")
        with st.form("add_obra"):
            no, nf = st.text_input("Nome da Obra"), st.text_input("Frente de Trabalho")
            if st.form_submit_button("GRAVAR OBRA"):
                obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra":no}])]).drop_duplicates()
                frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra":no, "Frente":nf}])]).drop_duplicates()
                save_db(obras_db, "obras_lista.csv"); save_db(frentes_db, "frentes_lista.csv"); st.rerun()
        st.table(frentes_db)

# --- 5. ÁREA DO TÉCNICO (O VISUAL DAS FOTOS) ---
else:
    if st.session_state.step == "obra":
        st.markdown("### Selecione a Obra")
        for o in obras_db['Obra'].unique():
            if st.button(f"🏢 {o}", use_container_width=True):
                st.session_state.obra_ativa = o; st.session_state.step = "frente"; st.rerun()
    
    elif st.session_state.step == "frente":
        st.markdown(f"### Obra: {st.session_state.obra_ativa}")
        f_lista = frentes_db[frentes_db['Obra'] == st.session_state.obra_ativa]['Frente'].tolist()
        for f in f_lista:
            if st.button(f"🚧 {f}", use_container_width=True):
                st.session_state.frente_ativa = f; st.session_state.step = "ponto"; st.rerun()
        if st.button("⬅️ Voltar"): st.session_state.step = "obra"; st.rerun()

    elif st.session_state.step == "ponto":
        hoje = datetime.now().strftime("%d/%m/%Y")
        meu_reg = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == hoje)]
        total = calc_total(meu_reg.iloc[0]['Turnos']) if not meu_reg.empty else "00:00"

        # CABEÇALHO PRETO
        st.markdown(f"""
            <div class="header-ponto">
                <div class="sub-header">Horas Totais Hoje</div>
                <div class="total-horas">{total}</div>
                <div class="sub-header">{st.session_state.frente_ativa}</div>
            </div>
            """, unsafe_allow_html=True)

        # MOSTRAR TURNOS EXISTENTES
        if not meu_reg.empty:
            for t in meu_reg.iloc[0]['Turnos'].split(', '):
                h1, h2 = t.split('-')
                st.markdown(f"""
                    <div class="turno-card">
                        <div class="turno-info">
                            <div class="label-hora">Entrada</div><div class="valor-hora">{h1}</div>
                        </div>
                        <div class="turno-info" style="text-align:right;">
                            <div class="label-hora">Saída</div><div class="valor-hora">{h2}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        with st.expander("➕ Adicionar Período"):
            c1, c2 = st.columns(2)
            hi = c1.time_input("Início", datetime.now().replace(hour=8, minute=0))
            hf = c2.time_input("Fim", datetime.now().replace(hour=17, minute=0))
            if st.button("GRAVAR REGISTO", use_container_width=True):
                novo_turno = f"{hi.strftime('%H:%M')}-{hf.strftime('%H:%M')}"
                if meu_reg.empty:
                    new_line = pd.DataFrame([{"Data":hoje, "Técnico":st.session_state.user, "Obra":st.session_state.obra_ativa, "Frente":st.session_state.frente_ativa, "Turnos":novo_turno, "Status":"0"}])
                    registos_db = pd.concat([registos_db, new_line])
                else:
                    registos_db.loc[meu_reg.index[0], 'Turnos'] += f", {novo_turno}"
                save_db(registos_db, "registos.csv"); st.rerun()

        if st.button("⬅️ Mudar de Obra"): st.session_state.step = "obra"; st.rerun()

if st.sidebar.button("Terminar Sessão"): st.session_state.user = None; st.rerun()

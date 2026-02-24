import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E DESIGN MOBILE (Fiel às fotos) ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    .header-ponto { background-color: #1A1A1A; color: white; padding: 30px 20px; text-align: center; border-radius: 0 0 25px 25px; margin-bottom: 20px; }
    .total-horas { font-size: 50px; font-weight: bold; color: #FFFFFF; line-height: 1; }
    .sub-header { font-size: 14px; opacity: 0.7; margin-top: 5px; }
    .turno-card { background: white; padding: 18px; border-radius: 15px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; }
    .turno-info { display: flex; flex-direction: column; }
    .label-hora { color: #8E8E93; font-size: 10px; text-transform: uppercase; font-weight: 700; }
    .valor-hora { color: #1C1C1E; font-size: 18px; font-weight: bold; margin-bottom: 5px; }
    .status-bola { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-left: 5px; }
    .bola-0 { background-color: #FF9500; } /* Laranja */
    .bola-1 { background-color: #34C759; } /* Verde */
    .bola-2 { background-color: #007AFF; } /* Azul */
    .stButton>button { border-radius: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS ---
def load_db(f, cols):
    if os.path.exists(f):
        return pd.read_csv(f, dtype=str).apply(lambda x: x.str.strip())
    return pd.DataFrame(columns=cols)

def save_db(df, f):
    df.to_csv(f, index=False)

def calc_total(turnos_lista):
    total_min = 0
    for t in turnos_lista:
        try:
            h1, h2 = t.split('-')
            t1 = datetime.strptime(h1.strip(), "%H:%M")
            t2 = datetime.strptime(h2.strip(), "%H:%M")
            total_min += (t2 - t1).seconds / 60
        except: continue
    return f"{int(total_min // 60):02d}:{int(total_min % 60):02d}"

# Carregar bases
users = load_db("usuarios.csv", ["Nome", "Password", "Tipo"])
obras_db = load_db("obras_lista.csv", ["Obra"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente"])
registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status"])

# --- 3. LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'turnos_temp' not in st.session_state: st.session_state.turnos_temp = []
if 'step' not in st.session_state: st.session_state.step = "obra"

if st.session_state.user is None:
    st.markdown("<h2 style='text-align:center;'>GestNow Login</h2>", unsafe_allow_html=True)
    u = st.text_input("Utilizador")
    p = st.text_input("Password", type="password")
    if st.button("Entrar", use_container_width=True):
        if u.lower() in ["diogo", "admin"] and p in ["rafael2026", "123"]:
            st.session_state.user, st.session_state.tipo = u, "Admin"
            st.rerun()
        match = users[(users['Nome'].str.lower() == u.lower()) & (users['Password'] == p)]
        if not match.empty:
            st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado")
    st.stop()

# --- 4. INTERFACE ADMIN ---
if st.session_state.tipo == "Admin":
    st.title("Admin Tower")
    t1, t2, t3, t4 = st.tabs(["🟠 Aprovar", "👥 Pessoal", "🏗️ Obras", "📋 Histórico"])
    
    with t1:
        st.subheader("Validação de Horas")
        pendentes = registos_db[registos_db['Status'] == "0"]
        for i, row in pendentes.iterrows():
            st.info(f"**{row['Técnico']}** | {row['Obra']}\n{row['Turnos']}")
            c1, c2 = st.columns(2)
            if c1.button(f"Validar Verde 🟢", key=f"v_{i}"):
                registos_db.at[i, 'Status'] = "1"; save_db(registos_db, "registos.csv"); st.rerun()
            if c2.button(f"Fechar Azul 🔵", key=f"a_{i}"):
                registos_db.at[i, 'Status'] = "2"; save_db(registos_db, "registos.csv"); st.rerun()

    with t2:
        nu, np = st.text_input("Nome"), st.text_input("Senha")
        if st.button("Criar"):
            users = pd.concat([users, pd.DataFrame([{"Nome":nu, "Password":np, "Tipo":"Colaborador"}])])
            save_db(users, "usuarios.csv"); st.rerun()
        st.dataframe(users)

    with t3:
        no = st.text_input("Obra")
        nf = st.text_input("Frente")
        if st.button("Gravar"):
            obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra":no}])]).drop_duplicates()
            frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra":no, "Frente":nf}])]).drop_duplicates()
            save_db(obras_db, "obras_lista.csv"); save_db(frentes_db, "frentes_lista.csv"); st.rerun()

    with t4:
        st.dataframe(registos_db)

# --- 5. INTERFACE COLABORADOR (Fiel às fotos) ---
else:
    if st.session_state.step == "obra":
        st.markdown("### Selecione uma obra")
        for obra in obras_db['Obra'].unique():
            if st.button(f"🏢 {obra}", use_container_width=True):
                st.session_state.obra_ativa = obra; st.session_state.step = "frente"; st.rerun()

    elif st.session_state.step == "frente":
        st.markdown(f"**Obra:** {st.session_state.obra_ativa}")
        st.markdown("### Selecione uma frente")
        f_list = frentes_db[frentes_db['Obra'] == st.session_state.obra_ativa]['Frente'].tolist()
        if st.button("⬅️ Voltar"): st.session_state.step = "obra"; st.rerun()
        for f in f_list:
            if st.button(f"🚧 {f}", use_container_width=True):
                st.session_state.frente_ativa = f; st.session_state.step = "ponto"; st.rerun()

    elif st.session_state.step == "ponto":
        # Seletor Scroll de Data
        data_sel = st.date_input("Consultar Dia", datetime.now())
        data_str = data_sel.strftime("%d/%m/%Y")
        
        meu_ponto = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == data_str)]
        
        # Somatório (Fiel à Foto 1)
        total_dia = calc_total(st.session_state.turnos_temp)
        if not meu_ponto.empty:
            total_dia = calc_total(meu_ponto.iloc[0]['Turnos'].split(', '))

        st.markdown(f"""
            <div class="header-ponto">
                <div class="sub-header">Registo de ponto</div>
                <div class="total-horas">{total_dia}</div>
                <div class="sub-header">{st.session_state.frente_ativa}</div>
            </div>
            """, unsafe_allow_html=True)

        # Cartões de Período (Fiel à Foto 2)
        if not meu_ponto.empty:
            status = meu_ponto.iloc[0]['Status']
            status_map = {"0": ("Reportado", "bola-0", "#FF9500"), "1": ("Validado", "bola-1", "#34C759"), "2": ("Finalizado", "bola-2", "#007AFF")}
            txt, bola_classe, cor = status_map.get(status, ("Reportado", "bola-0", "#FF9500"))
            
            for t in meu_ponto.iloc[0]['Turnos'].split(', '):
                h_in, h_out = t.split('-')
                st.markdown(f"""
                    <div class="turno-card">
                        <div class="turno-info">
                            <span class="label-hora">Hora de entrada</span><span class="valor-hora">{h_in}</span>
                            <span class="label-hora">Hora de saída</span><span class="valor-hora">{h_out}</span>
                        </div>
                        <div style="text-align:right">
                            <span style="font-size:12px; font-weight:bold; color:{cor}">{txt}</span>
                            <span class="status-bola {bola_classe}"></span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        # Adicionar Novo (Fiel à Foto 3)
        with st.expander("➕ Adicionar Período"):
            c1, c2 = st.columns(2)
            hi = c1.time_input("Entrada", datetime.now().replace(hour=8, minute=0))
            hf = c2.time_input("Saída", datetime.now().replace(hour=12, minute=0))
            if st.button("Gravar Bloco"):
                st.session_state.turnos_temp.append(f"{hi.strftime('%H:%M')}-{hf.strftime('%H:%M')}")
                st.rerun()

        if st.session_state.turnos_temp:
            st.info(f"Pendentes: {st.session_state.turnos_temp}")
            if st.button("🚀 FINALIZAR E ENVIAR TUDO", use_container_width=True):
                novo_r = pd.DataFrame([{"Data":data_str, "Técnico":st.session_state.user, "Obra":st.session_state.obra_ativa, "Frente":st.session_state.frente_ativa, "Turnos":", ".join(st.session_state.turnos_temp), "Relatorio":"", "Status":"0"}])
                save_db(pd.concat([registos_db, novo_r]), "registos.csv")
                st.session_state.turnos_temp = []
                st.success("Enviado!")
                st.rerun()

        if st.button("⬅️ Voltar"): st.session_state.step = "obra"; st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

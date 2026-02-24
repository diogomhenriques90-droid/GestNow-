import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    .header-ponto { background-color: #112240; color: white; padding: 20px; text-align: center; border-radius: 0 0 25px 25px; margin-bottom: 15px; }
    .total-horas { font-size: 40px; font-weight: bold; color: #00D2FF; }
    .status-bola { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
    .status-0 { background-color: #FFA500; } /* Laranja: Reportado */
    .status-1 { background-color: #28A745; } /* Verde: Validado */
    .status-2 { background-color: #007BFF; } /* Azul: Confirmado */
    .turno-card { background: white; padding: 15px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); color: #333; }
    .stButton>button { border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS ---
def load_db(f, cols):
    if os.path.exists(f):
        try:
            return pd.read_csv(f, dtype=str).apply(lambda x: x.str.strip())
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_db(df, f):
    df.to_csv(f, index=False)

users = load_db("usuarios.csv", ["Nome", "Password", "Tipo"])
obras_db = load_db("obras_lista.csv", ["Obra"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente"])
registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status"])

# --- 3. GESTÃO DE SESSÃO ---
if 'user' not in st.session_state: st.session_state.user = None
if 'data_consulta' not in st.session_state: st.session_state.data_consulta = datetime.now().date()
if 'turnos_temp' not in st.session_state: st.session_state.turnos_temp = []

# --- 4. LOGIN ---
if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center; color: #112240;'>GESTNOW</h1>", unsafe_allow_html=True)
    u = st.text_input("Utilizador").strip()
    p = st.text_input("Password", type="password").strip()
    if st.button("ENTRAR"):
        if u.lower() in ["diogo", "admin", "rafael correia"] and p in ["rafael2026", "123"]:
            st.session_state.user, st.session_state.tipo = u, "Admin"
            st.rerun()
        match = users[(users['Nome'].str.lower() == u.lower()) & (users['Password'] == p)]
        if not match.empty:
            st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado")
    st.stop()

# --- 5. INTERFACE ADMIN ---
if st.session_state.tipo == "Admin":
    st.title("Painel de Controlo")
    tab_aprov, tab_pess, tab_obras, tab_frentes, tab_hist = st.tabs(["🟠 Aprovar", "👥 Pessoal", "🏗️ Obras", "🚧 Frentes", "📋 Histórico"])
    
    with tab_aprov:
        st.subheader("Validar Horas Pendentes")
        pendentes = registos_db[registos_db['Status'] == "0"]
        if not pendentes.empty:
            for i, row in pendentes.iterrows():
                with st.container():
                    st.markdown(f"**{row['Técnico']}** - {row['Data']}\n\n*{row['Obra']} ({row['Turnos']})*")
                    col_a, col_b = st.columns(2)
                    if col_a.button(f"Validar Verde 🟢", key=f"v_{i}"):
                        registos_db.at[i, 'Status'] = "1"
                        save_db(registos_db, "registos.csv"); st.rerun()
                    if col_b.button(f"Fechar Azul 🔵", key=f"az_{i}"):
                        registos_db.at[i, 'Status'] = "2"
                        save_db(registos_db, "registos.csv"); st.rerun()
                    st.markdown("---")
        else: st.write("Tudo em dia! Sem pendentes.")

    with tab_pess:
        nu = st.text_input("Novo Nome").strip()
        np = st.text_input("Nova Senha").strip()
        nt = st.selectbox("Cargo", ["Colaborador", "Chefe de Equipa", "Recursos Humanos"])
        if st.button("Criar Utilizador"):
            users = pd.concat([users, pd.DataFrame([{"Nome":nu, "Password":np, "Tipo":nt}])])
            save_db(users, "usuarios.csv"); st.success("Criado!"); st.rerun()
        st.dataframe(users, use_container_width=True)

    with tab_obras:
        no = st.text_input("Nome da Obra Principal").strip()
        if st.button("Gravar Obra"):
            obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra":no}])])
            save_db(obras_db, "obras_lista.csv"); st.rerun()
        st.dataframe(obras_db, use_container_width=True)

    with tab_frentes:
        o_sel = st.selectbox("Para qual obra?", ["--"] + obras_db['Obra'].tolist())
        nf = st.text_input("Nome da Frente").strip()
        if st.button("Gravar Frente"):
            frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra":o_sel, "Frente":nf}])])
            save_db(frentes_db, "frentes_lista.csv"); st.rerun()
        st.dataframe(frentes_db, use_container_width=True)
    
    with tab_hist:
        st.dataframe(registos_db, use_container_width=True)

# --- 6. INTERFACE COLABORADOR ---
else:
    # Calendário
    st.markdown("### O meu Calendário")
    c1, c2, c3 = st.columns([1, 2, 1])
    if c1.button("◀️"): st.session_state.data_consulta -= timedelta(days=1); st.rerun()
    data_str = st.session_state.data_consulta.strftime("%d/%m/%Y")
    c2.markdown(f"<h4 style='text-align:center; color:black;'>{data_str}</h4>", unsafe_allow_html=True)
    if c3.button("▶️"): st.session_state.data_consulta += timedelta(days=1); st.rerun()

    meu_dia = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == data_str)]
    
    total_h = f"{len(meu_dia)*4}:00" if not meu_dia.empty else "00:00"
    st.markdown(f'<div class="header-ponto"><p style="margin:0">Horas Totais</p><div class="total-horas">{total_h}</div></div>', unsafe_allow_html=True)

    if not meu_dia.empty:
        for _, row in meu_dia.iterrows():
            st.markdown(f"""
                <div class="turno-card">
                    <span class="status-bola status-{row['Status']}"></span> <b>{row['Obra']}</b><br>
                    {row['Turnos']}<br><small>{row['Frente']}</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Sem registos neste dia.")

    if st.session_state.data_consulta == datetime.now().date():
        st.markdown("---")
        with st.expander("➕ Adicionar Turno"):
            obra_s = st.selectbox("Obra", ["--"] + obras_db['Obra'].tolist())
            frentes_f = frentes_db[frentes_db['Obra'] == obra_s]['Frente'].tolist() if obra_s != "--" else []
            frente_s = st.selectbox("Frente", ["--"] + frentes_f)
            h_e = st.time_input("Entrada", datetime.now().replace(hour=8, minute=0))
            h_s = st.time_input("Saída", datetime.now().replace(hour=17, minute=0))
            if st.button("Gravar Bloco"):
                st.session_state.turnos_temp.append(f"{h_e.strftime('%H:%M')}-{h_s.strftime('%H:%M')}")
                st.rerun()
        
        if st.session_state.turnos_temp:
            st.write(f"Períodos: {', '.join(st.session_state.turnos_temp)}")
            if st.button("🚀 SUBMETER TUDO (Laranja 🟠)"):
                if obra_s != "--" and frente_s != "--":
                    novo = pd.DataFrame([{"Data":data_str, "Técnico":st.session_state.user, "Obra":obra_s, "Frente":frente_s, "Turnos":", ".join(st.session_state.turnos_temp), "Relatorio":"", "Status":"0"}])
                    registos_db = pd.concat([registos_db, novo])
                    save_db(registos_db, "registos.csv")
                    st.session_state.turnos_temp = []
                    st.success("Enviado!")
                    st.rerun()
                else: st.error("Escolha Obra e Frente!")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

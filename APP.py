datetimeeamlit as st
import pandas as pd
import os
from datetime import dapd# --- 1. DESIGN E ESTILO (FIEL ÀS TUAS FOTOS) ---
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
    .bola-0 { background-color: #FF9500; } 
    .bola-1 { background-color: #34C759; } 
    .bola-2 { background-color: #007AFF; } 
    .stButton>button { border-radius: 12px; font-weight: bold; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS (BLINDADO) ---
def safe_load(f, cols):
    if os.path.exists(f):
        try:
            df = pd.read_csv(f, dtype=str, on_bad_lines='skip', encoding='utf-8')
            if all(c in df.columns for c in cols): 
                return df[cols]
        except: 
            pass
    return pd.DataFrame(columns=cols)

def save_db(df, f):
    df.to_csv(f, index=False, encoding='utf-8')

def calc_total_horas(turnos):
    minutos = 0
    for t in turnos:
        try:
            i, f = t.split('-')
            t1 = datetime.strptime(i.strip(), "%H:%M")
            t2 = datetime.strptime(f.strip(), "%H:%M")
            diff = (t2 - t1).total_seconds() / 60
            if diff > 0: minutos += diff
        except: continue
    return f"{int(minutos // 60):02d}:{int(minutos % 60):02d}"

# Carregamento Inicial
users = safe_load("usuarios.csv", ["Nome", "Password", "Tipo"])
obras_db = safe_load("obras_lista.csv", ["Obra"])
frentes_db = safe_load("frentes_lista.csv", ["Obra", "Frente"])
registos_db = safe_load("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status"])

# --- 3. ESTADOS DA SESSÃO ---
if 'user' not in st.session_state: st.session_state.user = None
if 'turnos_temp' not in st.session_state: st.session_state.turnos_temp = []
if 'step' not in st.session_state: st.session_state.step = "obra"

# --- 4. LOGIN ---
if st.session_state.user is None:
    st.markdown("<h2 style='text-align:center;'>GestNow Login</h2>", unsafe_allow_html=True)
    u = st.text_input("Utilizador").strip()
    p = st.text_input("Password", type="password").strip()
    if st.button("Entrar", use_container_width=True):
        if u.lower() in ["diogo", "admin"] and p in ["rafael2026", "123"]:
            st.session_state.user, st.session_state.tipo = u, "Admin"
            st.rerun()
        match = users[(users['Nome'].str.lower() == u.lower()) & (users['Password'] == p)]
        if not match.empty:
            st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso negado.")
    st.stop()

# --- 5. INTERFACE ADMIN ---
if st.session_state.tipo == "Admin":
    st.title("Painel Admin")
    t1, t2, t3 = st.tabs(["🟠 Aprovar", "👥 Equipa", "🏗️ Config Obras"])
    
    with t1:
        pend = registos_db[registos_db['Status'] == "0"]
        if pend.empty: st.write("Tudo em dia!")
        for idx, row in pend.iterrows():
            st.info(f"**{row['Técnico']}** | {row['Data']}\n{row['Turnos']}")
            c1, c2 = st.columns(2)
            if c1.button("Validar 🟢", key=f"v{idx}"):
                registos_db.at[idx, 'Status'] = "1"
                save_db(registos_db, "registos.csv"); st.rerun()
            if c2.button("Finalizar 🔵", key=f"f{idx}"):
                registos_db.at[idx, 'Status'] = "2"
                save_db(registos_db, "registos.csv"); st.rerun()
    
    with t2:
        nu, np = st.text_input("Nome"), st.text_input("Senha")
        if st.button("Adicionar"):
            users = pd.concat([users, pd.DataFrame([{"Nome":nu, "Password":np, "Tipo":"Colaborador"}])])
            save_db(users, "usuarios.csv"); st.rerun()
        st.dataframe(users)

    with t3:
        no, nf = st.text_input("Obra"), st.text_input("Frente")
        if st.button("Gravar"):
            obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra":no}])]).drop_duplicates()
            frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra":no, "Frente":nf}])]).drop_duplicates()
            save_db(obras_db, "obras_lista.csv"); save_db(frentes_db, "frentes_lista.csv"); st.rerun()

# --- 6. INTERFACE COLABORADOR (FIEL ÀS TUAS FOTOS) ---
else:
    if st.session_state.step == "obra":
        st.markdown("### Selecione a Obra")
        for o in obras_db['Obra'].unique():
            if st.button(f"🏢 {o}", use_container_width=True):
                st.session_state.obra_ativa = o; st.session_state.step = "frente"; st.rerun()
    
    elif st.session_state.step == "frente":
        st.markdown(f"**Obra:** {st.session_state.obra_ativa}")
        f_list = frentes_db[frentes_db['Obra'] == st.session_state.obra_ativa]['Frente'].tolist()
        if st.button("⬅️ Voltar"): st.session_state.step = "obra"; st.rerun()
        for f in f_list:
            if st.button(f"🚧 {f}", use_container_width=True):
                st.session_state.frente_ativa = f; st.session_state.step = "ponto"; st.rerun()

    elif st.session_state.step == "ponto":
        # Navegação por data (Scroll no mobile)
        data_sel = st.date_input("Escolha o Dia", datetime.now())
        ds = data_sel.strftime("%d/%m/%Y")
        
        meu_reg = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == ds)]
        
        # Define o que exibir no cabeçalho e nos cartões
        lista_exibir = st.session_state.turnos_temp if meu_reg.empty else meu_reg.iloc[0]['Turnos'].split(', ')
        total_h = calc_total_horas(lista_exibir)

        st.markdown(f"""
            <div class="header-ponto">
                <div class="sub-header">Registo de ponto</div>
                <div class="total-horas">{total_h}</div>
                <div class="sub-header">{st.session_state.frente_ativa}</div>
            </div>""", unsafe_allow_html=True)

        # Cartões de Período (Igual à Foto 2)
        if not meu_reg.empty:
            stts = meu_reg.iloc[0]['Status']
            s_map = {"0":("Reportado","bola-0","#FF9500"), "1":("Validado","bola-1","#34C759"), "2":("Finalizado","bola-2","#007AFF")}
            txt, bola, cor = s_map.get(stts, ("Reportado","bola-0","#FF9500"))
            for t in meu_reg.iloc[0]['Turnos'].split(', '):
                h1, h2 = t.split('-')
                st.markdown(f"""
                <div class="turno-card">
                    <div class="turno-info">
                        <span class="label-hora">Hora entrada</span><span class="valor-hora">{h1}</span>
                        <span class="label-hora">Hora saída</span><span class="valor-hora">{h2}</span>
                    </div>
                    <div style="text-align:right">
                        <span style="font-size:11px; font-weight:bold; color:{cor}">{txt}</span><span class="status-bola {bola}"></span>
                    </div>
                </div>""", unsafe_allow_html=True)

        # Novos blocos temporários
        for t in st.session_state.turnos_temp:
            h1, h2 = t.split('-')
            st.markdown(f"""
            <div class="turno-card" style="border-left: 5px solid orange;">
                <div class="turno-info">
                    <span class="label-hora">Entrada</span><span class="valor-hora">{h1}</span>
                    <span class="label-hora">Saída</span><span class="valor-hora">{h2}</span>
                </div>
                <div style="text-align:right"><span style="font-size:11px; color:orange;">Novo</span></div>
            </div>""", unsafe_allow_html=True)

        with st.expander("➕ Adicionar Bloco"):
            c1, c2 = st.columns(2)
            hi = c1.time_input("Início", datetime.now().replace(hour=8, minute=0))
            hf = c2.time_input("Fim", datetime.now().replace(hour=17, minute=0))
            if st.button("Inserir"):
                st.session_state.turnos_temp.append(f"{hi.strftime('%H:%M')}-{hf.strftime('%H:%M')}")
                st.rerun()

        if st.session_state.turnos_temp:
            if st.button("🚀 SUBMETER DIA", use_container_width=True):
                nr = pd.DataFrame([{"Data":ds, "Técnico":st.session_state.user, "Obra":st.session_state.obra_ativa, "Frente":st.session_state.frente_ativa, "Turnos":", ".join(st.session_state.turnos_temp), "Relatorio":"", "Status":"0"}])
                save_db(pd.concat([registos_db, nr]), "registos.csv")
                st.session_state.turnos_temp = []
                st.success("Submetido com sucesso!")
                st.rerun()
        
        if st.button("⬅️ Mudar Obra"):
            st.session_state.step = "obra"
            st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

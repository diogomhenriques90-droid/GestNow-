import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO VISUAL ---
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

# --- 2. FUNÇÕES DE DADOS (ANTI-ERRO) ---
def safe_load(file_path, columns):
    """Lê o CSV de forma segura. Se falhar, cria um novo com as colunas certas."""
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, dtype=str, on_bad_lines='skip', encoding='utf-8')
            # Verifica se todas as colunas necessárias existem
            if all(c in df.columns for c in columns):
                return df[columns]
        except:
            pass # Se der erro de parser, ignora e cria novo
    return pd.DataFrame(columns=columns)

def save_db(df, file_path):
    df.to_csv(file_path, index=False, encoding='utf-8')

def calc_total_horas(turnos):
    """Calcula o somatório de strings tipo ['08:00-12:00', '13:00-17:00']"""
    minutos_totais = 0
    for t in turnos:
        try:
            inicio, fim = t.split('-')
            t1 = datetime.strptime(inicio.strip(), "%H:%M")
            t2 = datetime.strptime(fim.strip(), "%H:%M")
            diff = (t2 - t1).total_seconds() / 60
            if diff > 0: minutos_totais += diff
        except: continue
    horas = int(minutos_totais // 60)
    mins = int(minutos_totais % 60)
    return f"{horas:02d}:{mins:02d}"

# Carregar bases com colunas fixas para evitar o erro do Parser
users = safe_load("usuarios.csv", ["Nome", "Password", "Tipo"])
obras_db = safe_load("obras_lista.csv", ["Obra"])
frentes_db = safe_load("frentes_lista.csv", ["Obra", "Frente"])
registos_db = safe_load("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status"])

# --- 3. ESTADOS ---
if 'user' not in st.session_state: st.session_state.user = None
if 'turnos_temp' not in st.session_state: st.session_state.turnos_temp = []
if 'step' not in st.session_state: st.session_state.step = "obra"

# --- 4. LOGIN ---
if st.session_state.user is None:
    st.markdown("<h2 style='text-align:center;'>GestNow Login</h2>", unsafe_allow_html=True)
    u = st.text_input("Utilizador").strip()
    p = st.text_input("Password", type="password").strip()
    if st.button("Entrar", use_container_width=True):
        if (u.lower() in ["diogo", "admin"]) and p in ["rafael2026", "123"]:
            st.session_state.user, st.session_state.tipo = u, "Admin"
            st.rerun()
        match = users[(users['Nome'].str.lower() == u.lower()) & (users['Password'] == p)]
        if not match.empty:
            st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Utilizador ou senha incorretos.")
    st.stop()

# --- 5. LÓGICA DE ADMIN ---
if st.session_state.tipo == "Admin":
    st.title("Painel Admin")
    tab1, tab2, tab3 = st.tabs(["🟠 Aprovações", "👥 Equipa", "🏗️ Config Obras"])
    
    with tab1:
        pendentes = registos_db[registos_db['Status'] == "0"]
        if pendentes.empty: st.write("Não há registos para aprovar.")
        for idx, row in pendentes.iterrows():
            with st.container():
                st.markdown(f"**Técnico:** {row['Técnico']} | **Data:** {row['Data']}")
                st.write(f"Turnos: {row['Turnos']}")
                col1, col2 = st.columns(2)
                if col1.button("Validar (Verde)", key=f"val_{idx}"):
                    registos_db.at[idx, 'Status'] = "1"
                    save_db(registos_db, "registos.csv"); st.rerun()
                if col2.button("Finalizar (Azul)", key=f"fin_{idx}"):
                    registos_db.at[idx, 'Status'] = "2"
                    save_db(registos_db, "registos.csv"); st.rerun()
            st.divider()

    with tab2:
        with st.form("add_user"):
            new_u = st.text_input("Nome do Técnico")
            new_p = st.text_input("Senha")
            if st.form_submit_button("Adicionar"):
                users = pd.concat([users, pd.DataFrame([{"Nome":new_u, "Password":new_p, "Tipo":"Colaborador"}])])
                save_db(users, "usuarios.csv"); st.success("Adicionado!"); st.rerun()
        st.dataframe(users, use_container_width=True)

    with tab3:
        with st.form("add_obra"):
            o_n = st.text_input("Nome da Obra")
            f_n = st.text_input("Frente de Trabalho")
            if st.form_submit_button("Gravar Obra"):
                obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra":o_n}])]).drop_duplicates()
                frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra":o_n, "Frente":f_n}])]).drop_duplicates()
                save_db(obras_db, "obras_lista.csv")
                save_db(frentes_db, "frentes_lista.csv"); st.success("Gravado!"); st.rerun()

# --- 6. LÓGICA DE COLABORADOR (DESIGN DAS FOTOS) ---
else:
    if st.session_state.step == "obra":
        st.markdown("### Selecione a Obra")
        if obras_db.empty: st.info("Aguarde que o Admin configure as obras.")
        for o in obras_db['Obra'].unique():
            if st.button(f"🏢 {o}", use_container_width=True):
                st.session_state.obra_ativa = o; st.session_state.step = "frente"; st.rerun()

    elif st.session_state.step == "frente":
        st.markdown(f"**Obra:** {st.session_state.obra_ativa}")
        f_disp = frentes_db[frentes_db['Obra'] == st.session_state.obra_ativa]['Frente'].tolist()
        if st.button("⬅️ Voltar"): st.session_state.step = "obra"; st.rerun()
        for f in f_disp:
            if st.button(f"🚧 {f}", use_container_width=True):
                st.session_state.frente_ativa = f; st.session_state.step = "ponto"; st.rerun()

    elif st.session_state.step == "ponto":
        data_escolhida = st.date_input("Escolha o dia", datetime.now())
        ds = data_escolhida.strftime("%d/%m/%Y")
        
        # Carregar registo se já existir
        meu_reg = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == ds)]
        
        # Calcular horas totais para o cabeçalho
        lista_p exibir = st.session_state.turnos_temp if meu_reg.empty else meu_reg.iloc[0]['Turnos'].split(', ')
        total_h = calc_total_horas(lista_p exibir)

        st.markdown(f"""
            <div class="header-ponto">
                <div class="sub-header">Registo de ponto</div>
                <div class="total-horas">{total_h}</div>
                <div class="sub-header">{st.session_state.frente_ativa}</div>
            </div>
            """, unsafe_allow_html=True)

        # Mostrar cartões existentes (Fiel à Foto 2)
        if not meu_reg.empty:
            stts = meu_reg.iloc[0]['Status']
            st_map = {"0": ("Reportado", "bola-0", "#FF9500"), "1": ("Validado", "bola-1", "#34C759"), "2": ("Finalizado", "bola-2", "#007AFF")}
            txt, classe, cor = st_map.get(stts, ("Reportado", "bola-0", "#FF9500"))
            
            for t in meu_reg.iloc[0]['Turnos'].split(', '):
                h_in, h_out = t.split('-')
                st.markdown(f"""
                <div class="turno-card">
                    <div class="turno-info">
                        <span class="label-hora">Hora de entrada</span><span class="valor-hora">{h_in}</span>
                        <span class="label-hora">Hora de saída</span><span class="valor-hora">{h_out}</span>
                    </div>
                    <div style="text-align:right">
                        <span style="font-size:11px; font-weight:bold; color:{cor}">{txt}</span><span class="status-bola {classe}"></span>
                    </div>
                </div>""", unsafe_allow_html=True)
        
        # Mostrar o que está a ser adicionado agora
        for t in st.session_state.turnos_temp:
            h_in, h_out = t.split('-')
            st.markdown(f"""
            <div class="turno-card" style="border-left: 5px solid #FF9500;">
                <div class="turno-info">
                    <span class="label-hora">Entrada</span><span class="valor-hora">{h_in}</span>
                    <span class="label-hora">Saída</span><span class="valor-hora">{h_out}</span>
                </div>
                <div style="text-align:right"><span style="font-size:11px; color:#FF9500;">Novo</span></div>
            </div>""", unsafe_allow_html=True)

        with st.expander("➕ Adicionar Bloco de Horas"):
            c1, c2 = st.columns(2)
            hi = c1.time_input("Início", datetime.now().replace(hour=8, minute=0))
            hf = c2.time_input("Fim", datetime.now().replace(hour=12, minute=0))
            if st.button("Adicionar"):
                st.session_state.turnos_temp.append(f"{hi.strftime('%H:%M')}-{hf.strftime('%H:%M')}")
                st.rerun()

        if st.session_state.turnos_temp:
            if st.button("🚀 SUBMETER DIA", use_container_width=True):
                novo_line = pd.DataFrame([{
                    "Data": ds, "Técnico": st.session_state.user, 
                    "Obra": st.session_state.obra_ativa, "Frente": st.session_state.frente_ativa,
                    "Turnos": ", ".join(st.session_state.turnos_temp), "Relatorio": "", "Status": "0"
                }])
                registos_db = pd.concat([registos_db, novo_line])
                save_db(registos_db, "registos.csv")
                st.session_state.turnos_temp = []; st.success("Submetido!"); st.rerun()

        if st.button("⬅️ Voltar"): st.session_state.step = "obra"; st.rerun()

if st.sidebar.button("Logout"): st.session_state.user = None; st.rerun()

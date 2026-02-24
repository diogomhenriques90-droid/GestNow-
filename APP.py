import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E DESIGN MOBILE (Fiel às fotos) ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    
    /* Cabeçalho das Fotos */
    .header-ponto { background-color: #1A1A1A; color: white; padding: 30px 20px; text-align: center; border-radius: 0 0 25px 25px; margin-bottom: 20px; }
    .total-horas { font-size: 50px; font-weight: bold; color: #FFFFFF; line-height: 1; }
    .sub-header { font-size: 14px; opacity: 0.7; margin-top: 5px; }
    
    /* Cartões de Período (Igual à Foto) */
    .turno-card { background: white; padding: 18px; border-radius: 15px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; }
    .turno-info { display: flex; flex-direction: column; }
    .label-hora { color: #8E8E93; font-size: 12px; text-transform: uppercase; font-weight: 600; }
    .valor-hora { color: #1C1C1E; font-size: 18px; font-weight: bold; margin-bottom: 8px; }
    
    /* Status (Bolinhas) */
    .status-area { text-align: right; }
    .status-txt { font-size: 12px; font-weight: 600; }
    .status-bola { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-left: 5px; }
    .bola-0 { background-color: #FF9500; } /* Laranja */
    .bola-1 { background-color: #34C759; } /* Verde */
    .bola-2 { background-color: #007AFF; } /* Azul */
    
    .stButton>button { border-radius: 12px; font-weight: bold; border: none; }
    .btn-add { background-color: #F2F2F7 !important; color: #FF3B30 !important; }
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
            t1 = datetime.strptime(h1, "%H:%M")
            t2 = datetime.strptime(h2, "%H:%M")
            total_min += (t2 - t1).seconds / 60
        except: continue
    return f"{int(total_min // 60):02d}:{int(total_min % 60):02d}"

registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status"])
obras_db = load_db("obras_lista.csv", ["Obra"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente"])

# --- 3. LÓGICA DE NAVEGAÇÃO ---
if 'step' not in st.session_state: st.session_state.step = "obra"
if 'turnos_temp' not in st.session_state: st.session_state.turnos_temp = []

# --- 4. FLUXO MOBILE (BASEADO NAS FOTOS) ---

# PASSO 1: SELECIONAR OBRA
if st.session_state.step == "obra":
    st.markdown("### Selecione uma obra")
    for _, row in obras_db.iterrows():
        if st.button(f"🏢 {row['Obra']}", use_container_width=True):
            st.session_state.obra_ativa = row['Obra']
            st.session_state.step = "frente"
            st.rerun()

# PASSO 2: SELECIONAR FRENTE
elif st.session_state.step == "frente":
    st.markdown(f"**Obra:** {st.session_state.obra_ativa}")
    st.markdown("### Selecione uma frente")
    f_lista = frentes_db[frentes_db['Obra'] == st.session_state.obra_ativa]['Frente'].tolist()
    if st.button("⬅️ Voltar"): st.session_state.step = "obra"; st.rerun()
    for f in f_lista:
        if st.button(f"🚧 {f}", use_container_width=True):
            st.session_state.frente_ativa = f
            st.session_state.step = "ponto"
            st.rerun()

# PASSO 3: FOLHA DE PONTO (A INTERFACE DAS FOTOS)
elif st.session_state.step == "ponto":
    # Seletor de Data (Scroll)
    data_sel = st.date_input("Data", datetime.now())
    data_str = data_sel.strftime("%d/%m/%Y")
    
    # Filtrar o que já existe no DB para este dia
    meu_ponto = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == data_str)]
    
    # Calcular Total (Existente + Novo temporário)
    total_dia = calc_total(st.session_state.turnos_temp) 
    if not meu_ponto.empty:
        total_dia = calc_total(meu_ponto.iloc[0]['Turnos'].split(', '))

    # HEADER ESCURO (FOTO 1)
    st.markdown(f"""
        <div class="header-ponto">
            <div class="sub-header">Registo de ponto</div>
            <div class="total-horas">{total_dia}</div>
            <div class="sub-header">{st.session_state.frente_ativa}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### Pontos")

    # MOSTRAR CARTÕES (FOTO 2)
    # 1. Mostrar o que já está na base de dados
    if not meu_ponto.empty:
        status = meu_ponto.iloc[0]['Status']
        status_map = {"0": ("Reportado", "bola-0"), "1": ("Validado", "bola-1"), "2": ("Finalizado", "bola-2")}
        txt, classe = status_map.get(status, ("Reportado", "bola-0"))
        
        for t in meu_ponto.iloc[0]['Turnos'].split(', '):
            h_in, h_out = t.split('-')
            st.markdown(f"""
                <div class="turno-card">
                    <div class="turno-info">
                        <span class="label-hora">Hora de entrada</span>
                        <span class="valor-hora">{h_in}</span>
                        <span class="label-hora">Hora de saída</span>
                        <span class="valor-hora">{h_out}</span>
                    </div>
                    <div class="status-area">
                        <span class="status-txt" style="color:{'#FF9500' if status=='0' else '#34C759' if status=='1' else '#007AFF'}">{txt}</span>
                        <span class="status-bola {classe}"></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # 2. Mostrar o que está a ser adicionado agora
    for t in st.session_state.turnos_temp:
        h_in, h_out = t.split('-')
        st.markdown(f"""
            <div class="turno-card" style="border-left: 5px solid #FF9500;">
                <div class="turno-info">
                    <span class="label-hora">Entrada</span><span class="valor-hora">{h_in}</span>
                    <span class="label-hora">Saída</span><span class="valor-hora">{h_out}</span>
                </div>
                <div class="status-area"><span class="status-txt">Novo</span></div>
            </div>
            """, unsafe_allow_html=True)

    # BOTÃO "+" ADICIONAR (FOTO 3)
    with st.expander("➕ Adicionar Período"):
        c1, c2 = st.columns(2)
        hi = c1.time_input("Início", datetime.now().replace(hour=8, minute=0))
        hf = c2.time_input("Fim", datetime.now().replace(hour=12, minute=0))
        if st.button("Inserir Período"):
            st.session_state.turnos_temp.append(f"{hi.strftime('%H:%M')}-{hf.strftime('%H:%M')}")
            st.rerun()

    # FINALIZAR DIA
    if st.session_state.turnos_temp:
        if st.button("🚀 FINALIZAR E ENVIAR", use_container_width=True):
            novo = pd.DataFrame([{
                "Data": data_str, "Técnico": st.session_state.user,
                "Obra": st.session_state.obra_ativa, "Frente": st.session_state.frente_ativa,
                "Turnos": ", ".join(st.session_state.turnos_temp), "Relatorio": "", "Status": "0"
            }])
            save_db(pd.concat([registos_db, novo]), "registos.csv")
            st.session_state.turnos_temp = []
            st.success("Enviado com sucesso!")
            st.rerun()

    if st.button("⬅️ Mudar Obra/Frente"):
        st.session_state.step = "obra"
        st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

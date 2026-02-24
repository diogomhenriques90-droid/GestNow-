import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO VISUAL MOBILE ---
st.set_page_config(page_title="GestNow | Calendário", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    .header-ponto { background-color: #112240; color: white; padding: 20px; text-align: center; border-radius: 0 0 25px 25px; }
    .total-horas { font-size: 40px; font-weight: bold; color: #00D2FF; }
    
    /* Estados das Bolinhas */
    .status-bola { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
    .status-0 { background-color: #FFA500; } /* Laranja: Reportado */
    .status-1 { background-color: #28A745; } /* Verde: Validado Gestor */
    .status-2 { background-color: #007BFF; } /* Azul: Confirmado Final */
    
    .turno-card { background: white; padding: 15px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .nav-calendario { display: flex; justify-content: space-between; align-items: center; background: white; padding: 10px; border-radius: 10px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS ---
def load_data(f):
    if os.path.exists(f):
        return pd.read_csv(f, dtype=str).apply(lambda x: x.str.strip())
    return pd.DataFrame(columns=["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status"])

registos_db = load_data("registos.csv")

# --- 3. CONTROLO DE NAVEGAÇÃO ---
if 'data_consulta' not in st.session_state:
    st.session_state.data_consulta = datetime.now().date()
if 'turnos_temp' not in st.session_state:
    st.session_state.turnos_temp = []

# --- 4. INTERFACE DE REGISTO (VISTA DO COLABORADOR) ---

# Cabeçalho de Navegação (O Calendário "para a frente e para trás")
st.markdown("### Consultar Data")
c1, c2, c3 = st.columns([1, 3, 1])

if c1.button("◀️"):
    st.session_state.data_consulta -= timedelta(days=1)
    st.rerun()

data_str = st.session_state.data_consulta.strftime("%d/%m/%Y")
c2.markdown(f"<h4 style='text-align:center; color:black;'>{data_str}</h4>", unsafe_allow_html=True)

if c3.button("▶️"):
    st.session_state.data_consulta += timedelta(days=1)
    st.rerun()

# Filtrar registos desta data para este técnico
meu_registo_dia = registos_db[
    (registos_db['Técnico'] == st.session_state.user) & 
    (registos_db['Data'] == data_str)
]

# Cálculo de horas total do dia consultado
total_dia = "00:00"
if not meu_registo_dia.empty:
    # Lógica simples de exemplo: cada turno contado como blocos (pode ser expandida)
    total_dia = f"{len(meu_registo_dia.iloc[0]['Turnos'].split(',')) * 4}:00"

st.markdown(f"""
    <div class="header-ponto">
        <p style='margin:0; opacity:0.8;'>Horas no dia {data_str}</p>
        <div class="total-horas">{total_dia}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# MOSTRAR ESTADO DAS HORAS (Bolinhas)
if not meu_registo_dia.empty:
    for _, row in meu_registo_dia.iterrows():
        status = row['Status']
        status_label = "Reportado" if status == "0" else ("Validado" if status == "1" else "Confirmado")
        
        st.markdown(f"""
            <div class="turno-card">
                <div style='display:flex; align-items:center; justify-content:space-between;'>
                    <span><span class="status-bola status-{status}"></span><b>{status_label}</b></span>
                    <span style='color:gray; font-size:12px;'>{row['Obra']}</span>
                </div>
                <div style='margin-top:10px; font-size:18px; font-weight:bold;'>{row['Turnos']}</div>
                <div style='color:gray; font-size:14px; margin-top:5px;'>{row['Frente']}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Sem registos para este dia.")

# SÓ PERMITE REGISTAR SE FOR A DATA DE HOJE (Evita fraudes no passado)
if st.session_state.data_consulta == datetime.now().date():
    with st.expander("➕ Adicionar Novo Turno de Hoje"):
        st.write("Registe os blocos de trabalho")
        h_e = st.time_input("Entrada", datetime.now().replace(hour=8, minute=0))
        h_s = st.time_input("Saída", datetime.now().replace(hour=12, minute=0))
        if st.button("Adicionar Bloco"):
            st.session_state.turnos_temp.append(f"{h_e.strftime('%H:%M')}-{h_s.strftime('%H:%M')}")
            st.rerun()
            
    if st.session_state.turnos_temp:
        st.write(f"**Blocos prontos:** {', '.join(st.session_state.turnos_temp)}")
        obs = st.text_area("Notas do dia")
        if st.button("🚀 SUBMETER TUDO (Laranja 🟠)"):
            # Lógica de gravação igual à anterior...
            st.success("Submetido com sucesso!")
            st.session_state.turnos_temp = []
            st.rerun()

if st.button("Voltar ao Menu"):
    st.session_state.step = "selecao_obra"
    st.rerun()

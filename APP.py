import streamlit as st
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="GestNow - Picar", layout="centered")

# --- CSS PERSONALIZADO (Estilo Dark & Néon) ---
st.markdown("""
    <style>
    /* Fundo e cores gerais */
    .stApp { background-color: #0e1117; color: white; }
    
    /* Calendário Horizontal */
    .cal-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #161b22;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-bottom: 2px solid #00f2ff;
    }
    .cal-day {
        text-align: center;
        padding: 5px 10px;
        border-radius: 5px;
        color: #8b949e;
    }
    .cal-active {
        background-color: #00f2ff;
        color: #0e1117 !important;
        font-weight: bold;
    }

    /* Cartão Principal de Horas */
    .main-card {
        background-color: #1c2128;
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    .total-hours {
        color: #00f2ff;
        font-size: 60px;
        font-weight: bold;
        text-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
        margin: 10px 0;
    }

    /* Cartões de Turno */
    .shift-card {
        background-color: #1c2128;
        border-radius: 15px;
        padding: 15px 20px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 5px solid #ffaa00;
    }
    .status-dot {
        height: 12px;
        width: 12px;
        background-color: #ffaa00;
        border-radius: 50%;
        box-shadow: 0 0 8px #ffaa00;
    }

    /* Botão Enviar */
    .stButton>button {
        width: 100%;
        background-color: #00f2ff !important;
        color: #0e1117 !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 15px !important;
        font-size: 18px !important;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CABEÇALHO / CALENDÁRIO ---
st.markdown(f"""
    <div class="cal-container">
        <span>&lt;</span>
        <div class="cal-day">Seg 23</div>
        <div class="cal-day">Ter 24</div>
        <div class="cal-day cal-active">Qua 25</div>
        <div class="cal-day">Qui 26</div>
        <div class="cal-day">Sex 27</div>
        <span>&gt;</span>
    </div>
    """, unsafe_allow_html=True)

# --- CARTÃO PRINCIPAL ---
st.markdown(f"""
    <div class="main-card">
        <p style="color: #8b949e; font-size: 12px; margin-bottom: 0;">TOTAL DE HORAS HOJE</p>
        <div class="total-hours">08:00</div>
        <p style="color: #8b949e; margin-top: 10px;">Basf | 25/02/2026</p>
    </div>
    """, unsafe_allow_html=True)

# --- TURNOS ---
turnos = [
    {"label": "TURNO", "horario": "08:00-12:00"},
    {"label": "TURNO", "horario": "13:00-17:00"}
]

for turno in turnos:
    st.markdown(f"""
        <div class="shift-card">
            <div>
                <small style="color: #8b949e; display: block;">{turno['label']}</small>
                <strong style="font-size: 18px;">{turno['horario']}</strong>
            </div>
            <div class="status-dot"></div>
        </div>
        """, unsafe_allow_html=True)

# --- ADICIONAR TURNO ---
with st.expander("➕ ADICIONAR TURNO"):
    col1, col2 = st.columns(2)
    inicio = col1.time_input("Início", value=datetime.strptime("08:00", "%H:%M"))
    fim = col2.time_input("Fim", value=datetime.strptime("17:00", "%H:%M"))
    if st.button("Gravar Turno"):
        st.success("Turno adicionado!")

st.write("---")

# --- BOTÃO FINAL ---
if st.button("ENVIAR PARA ORÇAMENTAÇÃO"):
    st.balloons()
    st.info("Dados integrados na estrutura PMBOK do projeto Guess.")

# Rodapé
st.markdown("<p style='text-align: center; color: #8b949e; font-size: 12px;'>Gerenciar aplicativo</p>", unsafe_allow_html=True)



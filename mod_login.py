import streamlit as st
from datetime import datetime
from core import load_all, cp

def render_login():
    """Login simples e funcional"""
    
    st.markdown("""
    <style>
    /* ESCONDER UI Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* FUNDO SIMPLES - Gradiente Azul Industrial */
    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
        background-attachment: fixed;
    }
    
    /* CARD CENTRAL */
    div[data-testid="stVerticalBlock"] > div:first-child {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 40px;
        max-width: 450px;
        margin: 80px auto;
        backdrop-filter: blur(10px);
    }
    
    /* TÍTULO */
    h1 {
        color: #60A5FA !important;
        text-align: center;
        font-size: 2.5rem !important;
        margin-bottom: 10px !important;
        font-weight: 900;
    }
    
    .subtitle {
        color: rgba(255, 255, 255, 0.7);
        text-align: center;
        margin-bottom: 40px;
        font-size: 1rem;
    }
    
    /* INPUTS */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.08);
        color: white;
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 10px;
        padding: 12px 16px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
    }
    
    /* BOTÃO */
    .stButton > button {
        background: linear-gradient(135deg, #3B82F6, #60A5FA);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 14px;
        font-weight: 700;
        font-size: 1.05rem;
        width: 100%;
        margin-top: 15px;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
    }
    
    /* CAPTION */
    .stCaption {
        color: rgba(255, 255, 255, 0.6) !important;
        margin-top: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # TÍTULO
    st.markdown("<h1>GESTNOW v3</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Gestão de Empresas e de Obras Industriais</p>", unsafe_allow_html=True)
    
    # TABS
    tab_pwd, tab_pin = st.tabs(["🔑 Password", "🔢 PIN"])
    
    with tab_pwd:
        username = st.text_input("Utilizador", key="u1")
        password = st.text_input("Password", type="password", key="p1")
        
        if st.button("ENTRAR", use_container_width=True, key="b1"):
            if username and password:
                users = load_all()[0]
                for _, user in users.iterrows():
                    if user['Nome'].lower() == username.lower():
                        if cp(password, user['Password']):
                            st.session_state['user'] = username
                            st.session_state['tipo'] = user.get('Tipo', 'Técnico')
                            st.session_state['last_activity'] = datetime.now()
                            st.success("✅ Login!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Password errada")
                        break
                else:
                    st.error("❌ Utilizador não encontrado")
    
    with tab_pin:
        u_pin = st.text_input("Utilizador", key="u2")
        pin = st.text_input("PIN (4-12 caracteres)", type="password", key="p2")
        
        if st.button("ENTRAR COM PIN", use_container_width=True, key="b2"):
            if u_pin and pin and 4 <= len(pin) <= 12:
                users = load_all()[0]
                match = users[(users['Nome'].str.lower() == u_pin.lower()) & (users['PIN'] == pin)]
                if not match.empty:
                    st.session_state['user'] = match.iloc[0]['Nome']
                    st.session_state['tipo'] = match.iloc[0]['Tipo']
                    st.session_state['last_activity'] = datetime.now()
                    st.success("✅ Login!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ PIN errado")

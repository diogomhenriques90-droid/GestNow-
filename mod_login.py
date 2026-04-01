import streamlit as st
import secrets
from datetime import datetime
from core import load_all, cp

def render_login():
    """Login page - Design Industrial Premium"""
    
    # CSS COMPLETO
    st.markdown("""
    <style>
    /* ESCONDER Streamlit UI */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stApp {background: transparent !important;}
    
    /* FUNDO COM IMAGEM INDUSTRIAL */
    .login-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: 
            linear-gradient(135deg, rgba(15,23,42,0.92), rgba(30,41,59,0.88)),
            url('https://images.unsplash.com/photo-1532601224a21-38e4cb705588?w=2560&q=90');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        z-index: -2;
    }
    
    /* CENTRALIZAR */
    .login-center {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 20px;
    }
    
    /* CARD GLASSMORPHISM */
    .login-card {
        background: rgba(255, 255, 255, 0.06);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        padding: 45px 40px;
        max-width: 460px;
        width: 100%;
        box-shadow: 
            0 20px 40px rgba(0,0,0,0.4),
            0 0 80px rgba(59,130,246,0.12);
        animation: slideUp 0.6s ease;
    }
    
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(40px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* TÍTULO */
    .login-title {
        text-align: center;
        margin-bottom: 35px;
    }
    .login-title h1 {
        font-size: 2.6rem;
        font-weight: 900;
        background: linear-gradient(135deg, #60A5FA, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 8px 0;
        letter-spacing: -1.5px;
    }
    .login-title p {
        color: rgba(255,255,255,0.7);
        font-size: 0.95rem;
        margin: 0;
    }
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        margin-bottom: 25px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 12px 20px;
        color: white;
        font-weight: 600;
        border: 1px solid rgba(255,255,255,0.2);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3B82F6, #60A5FA);
        border-color: #3B82F6;
    }
    
    /* INPUTS */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(59,130,246,0.3);
        border-radius: 10px;
        color: white;
        padding: 14px 18px;
        font-size: 1rem;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.25);
        background: rgba(255,255,255,0.12);
    }
    .stTextInput > div > div > input::placeholder {
        color: rgba(255,255,255,0.45);
    }
    
    /* CAPTION */
    .stCaption {
        color: rgba(255,255,255,0.6) !important;
        font-size: 0.82rem !important;
        margin-top: 5px !important;
    }
    
    /* BOTÃO */
    .stButton > button {
        background: linear-gradient(135deg, #3B82F6, #60A5FA);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 14px;
        font-size: 1.05rem;
        font-weight: 700;
        width: 100%;
        margin-top: 15px;
        cursor: pointer;
        transition: all 0.25s ease;
        box-shadow: 0 4px 20px rgba(59,130,246,0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(59,130,246,0.6);
    }
    
    /* FOOTER */
    .login-footer {
        text-align: center;
        margin-top: 30px;
        color: rgba(255,255,255,0.5);
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Background
    st.markdown('<div class="login-bg"></div>', unsafe_allow_html=True)
    
    # Container
    st.markdown('<div class="login-center">', unsafe_allow_html=True)
    
    # Card
    st.markdown("""
    <div class="login-card">
        <div class="login-title">
            <h1>GESTNOW v3</h1>
            <p>Gestão de Empresas e de Obras Industriais</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs
    tab_pwd, tab_pin = st.tabs(["🔑 Password", "🔢 PIN"])
    
    # TAB PASSWORD
    with tab_pwd:
        st.markdown('<div class="login-card" style="margin-top:-45px">', unsafe_allow_html=True)
        
        username = st.text_input("Utilizador", placeholder="Introduza o utilizador", key="lp_u")
        password = st.text_input("Password", type="password", placeholder="Introduza a password", key="lp_p")
        
        if st.button("ENTRAR", use_container_width=True, key="lp_btn"):
            if not username or not password:
                st.error("⚠️ Preencha todos os campos.")
            else:
                try:
                    users = load_all()[0]
                    found = False
                    for _, user in users.iterrows():
                        if user['Nome'].lower() == username.lower():
                            found = True
                            if cp(password, user['Password']):
                                st.session_state['user'] = username
                                st.session_state['tipo'] = user.get('Tipo', 'Técnico')
                                st.session_state['cargo'] = user.get('Cargo', 'Técnico')
                                st.session_state['last_activity'] = datetime.now()
                                st.success(f"✅ Bem-vindo!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Password incorreta.")
                            break
                    if not found:
                        st.error("❌ Utilizador não encontrado.")
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)[:100]}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB PIN
    with tab_pin:
        st.markdown('<div class="login-card" style="margin-top:-45px">', unsafe_allow_html=True)
        
        u_pin = st.text_input("Utilizador", placeholder="Introduza o utilizador", key="li_u")
        st.caption("PIN: 4 a 12 caracteres")
        pin_in = st.text_input("PIN", type="password", placeholder="Introduza o PIN", key="li_p")
        
        if st.button("ENTRAR COM PIN", use_container_width=True, key="li_btn"):
            if not u_pin or not pin_in:
                st.error("⚠️ Preencha todos os campos.")
            elif len(pin_in) < 4:
                st.error("⚠️ Mínimo 4 caracteres.")
            elif len(pin_in) > 12:
                st.error("⚠️ Máximo 12 caracteres.")
            else:
                try:
                    users = load_all()[0]
                    match = users[
                        (users['Nome'].str.lower() == u_pin.lower()) & 
                        (users['PIN'] == pin_in)
                    ]
                    if not match.empty:
                        st.session_state['user'] = match.iloc[0]['Nome']
                        st.session_state['tipo'] = match.iloc[0]['Tipo']
                        st.session_state['cargo'] = match.iloc[0].get('Cargo', 'Técnico')
                        st.session_state['last_activity'] = datetime.now()
                        st.success(f"✅ Bem-vindo!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Utilizador ou PIN incorretos.")
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)[:100]}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="login-footer">
        GESTNOW v3.0 • Instrumentação Industrial<br>
        <span style="opacity:0.6">© 2024 Todos os direitos reservados</span>
    </div>
    """, unsafe_allow_html=True)

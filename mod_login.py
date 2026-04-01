import streamlit as st
import secrets
from core import load_all, cp, hp, ICONS, COLORS
from translations import t

def render_login():
    """Renderiza página de login com design industrial futurista"""
    
    # CSS personalizado com imagem de fundo industrial
    st.markdown("""
    <style>
    /* Remover elementos padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Fundo com imagem industrial nítida */
    .stApp {
        background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.9)),
                    url('https://images.unsplash.com/photo-1532601224a21-38e4cb705588?w=1920&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        min-height: 100vh;
    }
    
    /* Container principal centralizado */
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 20px;
    }
    
    /* Card glassmorphism premium */
    .login-card {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        padding: 50px 40px;
        max-width: 520px;
        width: 100%;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4),
                    0 0 60px rgba(59, 130, 246, 0.2);
        animation: slideIn 0.6s ease-out;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Logo e título */
    .logo-container {
        text-align: center;
        margin-bottom: 40px;
    }
    
    .logo-icon {
        font-size: 4rem;
        margin-bottom: 15px;
        filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.6));
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    .app-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #60A5FA, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 10px 0;
        letter-spacing: -1px;
    }
    
    .app-subtitle {
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.7);
        font-weight: 400;
    }
    
    /* Tabs modernas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px 24px;
        color: white;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3B82F6, #60A5FA);
        border-color: #3B82F6;
    }
    
    /* Inputs modernos */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.1);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        color: white;
        padding: 15px 20px;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3),
                    0 0 20px rgba(59, 130, 246, 0.4);
        background: rgba(255, 255, 255, 0.15);
    }
    
    .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.5);
    }
    
    /* Caption */
    .stCaption {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.85rem;
    }
    
    /* Botão login premium */
    .stButton > button {
        background: linear-gradient(135deg, #3B82F6, #60A5FA);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 16px 32px;
        font-size: 1.1rem;
        font-weight: 700;
        width: 100%;
        margin-top: 20px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.5),
                    0 0 40px rgba(59, 130, 246, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 30px rgba(59, 130, 246, 0.7),
                    0 0 60px rgba(59, 130, 246, 0.5);
        background: linear-gradient(135deg, #60A5FA, #3B82F6);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Elementos decorativos flutuantes */
    .floating-icons {
        position: fixed;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        pointer-events: none;
        z-index: 0;
    }
    
    .float-icon {
        position: absolute;
        font-size: 2rem;
        opacity: 0.15;
        animation: float 6s ease-in-out infinite;
        color: #3B82F6;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-20px) rotate(5deg); }
    }
    
    .icon-1 { top: 15%; left: 10%; animation-delay: 0s; }
    .icon-2 { top: 70%; left: 5%; animation-delay: 1s; }
    .icon-3 { top: 20%; right: 10%; animation-delay: 2s; }
    .icon-4 { top: 75%; right: 8%; animation-delay: 3s; }
    
    /* Footer discreto */
    .login-footer {
        text-align: center;
        margin-top: 30px;
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Elementos decorativos flutuantes
    st.markdown("""
    <div class="floating-icons">
        <div class="float-icon icon-1">️</div>
        <div class="float-icon icon-2">📊</div>
        <div class="float-icon icon-3">🔧</div>
        <div class="float-icon icon-4">⚡</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Container principal
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # Card de login
    st.markdown("""
    <div class="login-card">
        <div class="logo-container">
            <div class="logo-icon">🎛️</div>
            <h1 class="app-title">GESTNOW v3</h1>
            <p class="app-subtitle">Gestão de Empresas e de Obras Industriais</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs para Password e PIN
    tab_password, tab_pin = st.tabs(["🔑 Password", "🔢 PIN"])
    
    # ========== TAB PASSWORD ==========
    with tab_password:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        username = st.text_input("Utilizador", placeholder="Introduza o utilizador", key="pwd_user")
        password = st.text_input("Password", type="password", placeholder="Introduza a password", key="pwd_pass")
        
        if st.button("ENTRAR", use_container_width=True, key="btn_password"):
            if not username or not password:
                st.error("⚠️ Por favor, preencha todos os campos.")
            else:
                try:
                    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, 
                     incs_db, sw_db, obs_db, equip_db, diags_db, diags_u_db, 
                     folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, 
                     req_epi_db, avals_db, inst_acessos_db) = load_all()
                    
                    user_found = False
                    for _, user in users.iterrows():
                        if user['Nome'].lower() == username.lower():
                            user_found = True
                            if cp(password, user['Password']):
                                st.session_state['user'] = username
                                st.session_state['tipo'] = user.get('Tipo', 'Técnico')
                                st.session_state['cargo'] = user.get('Cargo', 'Técnico')
                                st.session_state['last_activity'] = secrets.token_hex(16)
                                
                                st.success(f"✅ Bem-vindo, {username}!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Password incorreta.")
                            break
                    
                    if not user_found:
                        st.error("❌ Utilizador não encontrado.")
                        
                except Exception as e:
                    st.error(f"❌ Erro ao autenticar: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== TAB PIN ==========
    with tab_pin:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        u_pin = st.text_input("Utilizador", placeholder="Introduza o utilizador", key="pin_user")
        st.caption("Introduza o seu PIN (4 a 12 caracteres)")
        pin_in = st.text_input("PIN", type="password", placeholder="Introduza o PIN", key="pin_input")
        
        if st.button("ENTRAR COM PIN", use_container_width=True, key="btn_pin"):
            if not u_pin or not pin_in:
                st.error("⚠️ Por favor, preencha todos os campos.")
            elif len(pin_in) < 4:
                st.error("⚠️ O PIN deve ter pelo menos 4 caracteres.")
            elif len(pin_in) > 12:
                st.error("⚠️ O PIN deve ter no máximo 12 caracteres.")
            else:
                try:
                    users_df = load_all()[0]
                    match = users_df[
                        (users_df['Nome'].str.lower() == u_pin.lower()) & 
                        (users_df['PIN'] == pin_in)
                    ]
                    
                    if not match.empty:
                        st.session_state['user'] = match.iloc[0]['Nome']
                        st.session_state['tipo'] = match.iloc[0]['Tipo']
                        st.session_state['cargo'] = match.iloc[0].get('Cargo', 'Técnico')
                        st.session_state['last_activity'] = secrets.token_hex(16)
                        
                        st.success(f"✅ Bem-vindo, {u_pin}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Utilizador ou PIN incorretos.")
                        
                except Exception as e:
                    st.error(f"❌ Erro ao autenticar: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="login-footer">
        <p>🎛️ GESTNOW v3.0 - Sistema de Gestão de Instrumentação Industrial</p>
        <p style="font-size: 0.75rem; margin-top: 5px;">© 2024 - Todos os direitos reservados</p>
    </div>
    """, unsafe_allow_html=True)

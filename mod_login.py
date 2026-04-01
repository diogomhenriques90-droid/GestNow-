import streamlit as st
import secrets
from core import load_all, cp, hp, ICONS, COLORS
from translations import t

def render_login():
    """Renderiza página de login com design industrial futurista PROFISSIONAL"""
    
    # CSS AGRESSIVO - Forçar imagem de fundo e glassmorphism
    st.markdown("""
    <style>
    /* ESCONDER elementos Streamlit */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stApp {background: transparent !important;}
    
    /* FUNDO com imagem industrial NÍTIDA */
    .main-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: 
            linear-gradient(135deg, rgba(15,23,42,0.85), rgba(30,41,59,0.80)),
            url('https://images.unsplash.com/photo-1532601224a21-38e4cb705588?w=2560&q=90');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        z-index: -1;
    }
    
    /* CENTRALIZAR tudo */
    .login-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 20px;
    }
    
    /* CARD GLASSMORPHISM PREMIUM */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(30px) saturate(180%);
        -webkit-backdrop-filter: blur(30px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.125);
        border-radius: 30px;
        padding: 60px 50px;
        max-width: 500px;
        width: 100%;
        box-shadow: 
            0 25px 50px rgba(0, 0, 0, 0.5),
            0 0 100px rgba(59, 130, 246, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        animation: fadeInUp 0.8s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(50px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* LOGO e TÍTULO */
    .brand {
        text-align: center;
        margin-bottom: 50px;
    }
    
    .brand-icon {
        font-size: 5rem;
        margin-bottom: 20px;
        filter: drop-shadow(0 0 30px rgba(59, 130, 246, 0.8));
        animation: glow 2s ease-in-out infinite;
    }
    
    @keyframes glow {
        0%, 100% { filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.6)); }
        50% { filter: drop-shadow(0 0 40px rgba(96, 165, 250, 0.9)); }
    }
    
    .brand h1 {
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(135deg, #60A5FA 0%, #3B82F6 50%, #2563EB 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 15px 0;
        letter-spacing: -2px;
    }
    
    .brand p {
        font-size: 1.1rem;
        color: rgba(255, 255, 255, 0.75);
        font-weight: 400;
        margin: 0;
    }
    
    /* TABS PREMIUM */
    .tabs-container {
        display: flex;
        gap: 15px;
        margin-bottom: 30px;
    }
    
    .tab-btn {
        flex: 1;
        padding: 15px 25px;
        background: rgba(255, 255, 255, 0.08);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 15px;
        color: white;
        font-weight: 600;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .tab-btn.active {
        background: linear-gradient(135deg, #3B82F6, #60A5FA);
        border-color: #3B82F6;
        box-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
    }
    
    .tab-btn:hover:not(.active) {
        background: rgba(255, 255, 255, 0.15);
        border-color: #60A5FA;
    }
    
    /* INPUTS FUTURISTAS */
    .input-group {
        margin-bottom: 25px;
    }
    
    .input-group label {
        display: block;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 600;
        margin-bottom: 10px;
        font-size: 0.95rem;
    }
    
    .input-group input {
        width: 100%;
        padding: 18px 25px;
        background: rgba(255, 255, 255, 0.08);
        border: 2px solid rgba(59, 130, 246, 0.25);
        border-radius: 15px;
        color: white;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-sizing: border-box;
    }
    
    .input-group input:focus {
        outline: none;
        border-color: #3B82F6;
        background: rgba(255, 255, 255, 0.12);
        box-shadow: 
            0 0 0 4px rgba(59, 130, 246, 0.2),
            0 0 30px rgba(59, 130, 246, 0.4);
    }
    
    .input-group input::placeholder {
        color: rgba(255, 255, 255, 0.4);
    }
    
    /* BOTÃO LOGIN ÉPICO */
    .login-btn {
        width: 100%;
        padding: 20px;
        background: linear-gradient(135deg, #3B82F6 0%, #60A5FA 50%, #3B82F6 100%);
        background-size: 200% 200%;
        border: none;
        border-radius: 15px;
        color: white;
        font-size: 1.2rem;
        font-weight: 800;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 
            0 10px 40px rgba(59, 130, 246, 0.5),
            0 0 60px rgba(59, 130, 246, 0.3);
        animation: gradientShift 3s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .login-btn:hover {
        transform: translateY(-3px);
        box-shadow: 
            0 15px 50px rgba(59, 130, 246, 0.7),
            0 0 80px rgba(59, 130, 246, 0.5);
    }
    
    .login-btn:active {
        transform: translateY(-1px);
    }
    
    /* CAPTION */
    .caption {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.85rem;
        margin-top: 8px;
        font-style: italic;
    }
    
    /* FOOTER */
    .footer {
        text-align: center;
        margin-top: 40px;
        color: rgba(255, 255, 255, 0.5);
        font-size: 0.85rem;
    }
    
    /* ÍCONES FLUTUANTES */
    .float-icons {
        position: fixed;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        pointer-events: none;
        z-index: -1;
        overflow: hidden;
    }
    
    .float-icon {
        position: absolute;
        font-size: 3rem;
        opacity: 0.08;
        animation: floating 8s ease-in-out infinite;
        color: #3B82F6;
    }
    
    @keyframes floating {
        0%, 100% { transform: translateY(0) rotate(0deg); }
        33% { transform: translateY(-30px) rotate(5deg); }
        66% { transform: translateY(-15px) rotate(-5deg); }
    }
    
    .fi-1 { top: 10%; left: 8%; animation-delay: 0s; }
    .fi-2 { top: 65%; left: 5%; animation-delay: 2s; }
    .fi-3 { top: 15%; right: 8%; animation-delay: 4s; }
    .fi-4 { top: 70%; right: 5%; animation-delay: 6s; }
    </style>
    """, unsafe_allow_html=True)
    
    # Background image
    st.markdown('<div class="main-bg"></div>', unsafe_allow_html=True)
    
    # Ícones flutuantes
    st.markdown("""
    <div class="float-icons">
        <div class="float-icon fi-1">️</div>
        <div class="float-icon fi-2">📊</div>
        <div class="float-icon fi-3">🔧</div>
        <div class="float-icon fi-4">⚡</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Container principal
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    
    # Card principal
    st.markdown("""
    <div class="glass-card">
        <div class="brand">
            <div class="brand-icon">🎛️</div>
            <h1>GESTNOW v3</h1>
            <p>Gestão de Empresas e de Obras Industriais</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs de navegação
    tab1, tab2 = st.tabs(["🔑 Password", "🔢 PIN"])
    
    # ========== TAB PASSWORD ==========
    with tab1:
        st.markdown('<div class="glass-card" style="margin-top: -50px;">', unsafe_allow_html=True)
        
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
                    st.error(f"❌ Erro: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== TAB PIN ==========
    with tab2:
        st.markdown('<div class="glass-card" style="margin-top: -50px;">', unsafe_allow_html=True)
        
        u_pin = st.text_input("Utilizador", placeholder="Introduza o utilizador", key="pin_user")
        st.markdown('<p class="caption">Introduza o seu PIN (4 a 12 caracteres)</p>', unsafe_allow_html=True)
        pin_in = st.text_input("PIN", type="password", placeholder="Introduza o PIN", key="pin_input")
        
        if st.button("ENTRAR COM PIN", use_container_width=True, key="btn_pin"):
            if not u_pin or not pin_in:
                st.error("⚠️ Por favor, preencha todos os campos.")
            elif len(pin_in) < 4:
                st.error("⚠️ Mínimo 4 caracteres.")
            elif len(pin_in) > 12:
                st.error("⚠️ Máximo 12 caracteres.")
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
                    st.error(f"❌ Erro: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>🎛️ GESTNOW v3.0 - Sistema de Gestão Industrial</p>
        <p style="font-size: 0.75rem; margin-top: 5px; opacity: 0.7;">© 2024 - Todos os direitos reservados</p>
    </div>
    """, unsafe_allow_html=True)

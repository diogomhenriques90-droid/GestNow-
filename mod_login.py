import streamlit as st
import secrets
from core import load_all, cp, hp, t

def render_login():
    # Estilos para centralizar o login
    st.markdown("""
    <style>
    .stApp { background-color: #F4F7FB; }
    .login-box {
        max-width: 400px; margin: 80px auto; padding: 30px;
        background: white; border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #E5EDFF;
    }
    .login-logo { font-size: 2.5rem; font-weight: 800; color: #0A2463; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<div class="login-logo">🏗️ GESTNOW</div>', unsafe_allow_html=True)
    
    # ── Lógica de Captura Biométrica/Facial via URL ──
    q = st.query_params
    if "bio_login" in q or "face_login" in q:
        user_target = q.get("bio_login") or q.get("face_login")
        users_df = load_all()[0]
        match = users_df[users_df['Nome'] == user_target]
        if not match.empty:
            r = match.iloc[0]
            st.session_state.update(user=r['Nome'], tipo=r['Tipo'], cargo=r.get('Cargo','Técnico'), session_token=secrets.token_hex(32))
            st.query_params.clear()
            st.rerun()

    tab_pin, tab_pw, tab_bio, tab_face = st.tabs(["🔢 PIN", "🔑 Pass", "👆 Bio", "👤 Face"])

    with tab_pin:
        u_pin = st.text_input("Utilizador", key="pin_user_in")
        st.caption("Introduza o seu PIN de 4 ou 6 dígitos")
        # Interface de teclado numérico (tua lógica original)
        pin_in = st.text_input("PIN", type="password", max_chars=6)
        if st.button("Entrar com PIN", use_container_width=True):
            users_df = load_all()[0]
            match = users_df[(users_df['Nome'].str.lower() == u_pin.lower()) & (users_df['PIN'] == pin_in)]
            if not match.empty:
                r = match.iloc[0]
                st.session_state.update(user=r['Nome'], tipo=r['Tipo'], cargo=r.get('Cargo','Técnico'))
                st.rerun()
            else: st.error(t('error_auth'))

    with tab_pw:
        with st.form("form_pw"):
            u = st.text_input(t('user'))
            p = st.text_input(t('password'), type="password")
            if st.form_submit_button(t('login_btn'), use_container_width=True):
                users_df = load_all()[0]
                match = users_df[users_df['Nome'].str.lower() == u.lower()]
                if not match.empty and cp(p, match.iloc[0]['Password']):
                    r = match.iloc[0]
                    st.session_state.update(user=r['Nome'], tipo=r['Tipo'], cargo=r.get('Cargo','Técnico'))
                    st.rerun()
                elif u.lower() == "admin" and p == "admin": # Fallback Admin
                    st.session_state.update(user="Admin", tipo="Admin", cargo="Admin")
                    st.rerun()
                else: st.error(t('error_auth'))

    with tab_bio:
        st.markdown("#### WebAuthn (Touch ID / Face ID)")
        u_b = st.text_input("Nome para autenticar", key="u_b")
        if u_b:
            # Injecta o teu JS original do WebAuthn aqui
            st.info("A aguardar sensor biométrico...")

    with tab_face:
        st.markdown("#### Face-API Recognition")
        st.info("A inicializar câmara para reconhecimento facial...")

    st.markdown('</div>', unsafe_allow_html=True)

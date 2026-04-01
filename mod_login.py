import streamlit as st
from datetime import datetime
from core import load_all, cp

def render_login():
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        background-attachment: fixed;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align:center; color:#60A5FA;'>GESTNOW v3</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:rgba(255,255,255,0.7);'>Gestão de Empresas e de Obras Industriais</p>", unsafe_allow_html=True)
    
    tab_pwd, tab_pin = st.tabs(["🔑 Password", "🔢 PIN"])
    
    with tab_pwd:
        username = st.text_input("Utilizador", key="u1")
        password = st.text_input("Password", type="password", key="p1")
        
        if st.button("ENTRAR", use_container_width=True, key="b1"):
            if username and password:
                # CORREÇÃO: Usar load_all() como antes
                (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, 
                 incs_db, sw_db, obs_db, equip_db, diags_db, diags_u_db, 
                 folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, 
                 req_epi_db, avals_db, inst_acessos_db) = load_all()
                
                # Verificar utilizador
                user_found = False
                for _, user in users.iterrows():
                    if user['Nome'].lower() == username.lower():
                        user_found = True
                        if cp(password, user['Password']):
                            st.session_state['user'] = username
                            st.session_state['tipo'] = user.get('Tipo', 'Técnico')
                            st.session_state['cargo'] = user.get('Cargo', 'Técnico')
                            st.session_state['last_activity'] = datetime.now()
                            st.success("✅ Login!")
                            st.rerun()
                        else:
                            st.error("❌ Password incorreta")
                        break
                
                if not user_found:
                    st.error("❌ Utilizador não encontrado")
    
    with tab_pin:
        u_pin = st.text_input("Utilizador", key="u2")
        pin = st.text_input("PIN", type="password", key="p2")
        
        if st.button("ENTRAR COM PIN", use_container_width=True, key="b2"):
            if u_pin and pin:
                (users, *rest) = load_all()
                match = users[(users['Nome'].str.lower() == u_pin.lower()) & (users['PIN'] == pin)]
                if not match.empty:
                    st.session_state['user'] = match.iloc[0]['Nome']
                    st.session_state['tipo'] = match.iloc[0]['Tipo']
                    st.session_state['last_activity'] = datetime.now()
                    st.success("✅ Login!")
                    st.rerun()
                else:
                    st.error("❌ PIN incorreto")

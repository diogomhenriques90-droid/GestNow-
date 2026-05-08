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
    st.markdown("<p style='text-align:center; color:rgba(255,255,255,0.7); margin-bottom:40px;'>Gestão de Empresas e de Obras Industriais</p>", unsafe_allow_html=True)

    tab_pwd, tab_pin = st.tabs(["🔑 Password", "🔢 PIN"])

    with tab_pwd:
        username = st.text_input("Utilizador", key="u1")
        password = st.text_input("Password", type="password", key="p1")

        if st.button("ENTRAR", use_container_width=True, key="b1", type="primary"):
            if username and password:
                result = load_all()
                users = result[0] if result else None

                if users is None or users.empty:
                    st.error("❌ Base de dados vazia. Cria o utilizador Admin primeiro.")
                    st.markdown("[🔧 Criar Admin](/?page=criar_admin)")
                    st.stop()

                user_found = False
                for _, user in users.iterrows():
                    if str(user.get('Nome', '')).lower() == username.lower():
                        user_found = True
                        if cp(password, str(user.get('Password', ''))):
                            st.session_state['user']          = user['Nome']
                            st.session_state['tipo']          = user.get('Tipo', 'Técnico')
                            st.session_state['cargo']         = user.get('Cargo', 'Técnico')
                            st.session_state['last_activity'] = datetime.now()
                            st.session_state['menu_selected'] = ''
                            st.success("✅ Login bem-sucedido!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Password incorreta.")
                        break

                if not user_found:
                    st.error("❌ Utilizador não encontrado.")
            else:
                st.warning("⚠️ Preenche utilizador e password.")

    with tab_pin:
        u_pin = st.text_input("Utilizador", key="u2")
        pin   = st.text_input("PIN (4 dígitos)", type="password", max_chars=4, key="p2")

        if st.button("ENTRAR COM PIN", use_container_width=True, key="b2", type="primary"):
            if u_pin and pin:
                result = load_all()
                users  = result[0] if result else None

                if users is not None and not users.empty:
                    match = users[
                        (users['Nome'].str.lower() == u_pin.lower()) &
                        (users['PIN'] == pin)
                    ]
                    if not match.empty:
                        st.session_state['user']          = match.iloc[0]['Nome']
                        st.session_state['tipo']          = match.iloc[0].get('Tipo', 'Técnico')
                        st.session_state['cargo']         = match.iloc[0].get('Cargo', 'Técnico')
                        st.session_state['last_activity'] = datetime.now()
                        st.session_state['menu_selected'] = ''
                        st.success("✅ Login com PIN bem-sucedido!")
                        st.rerun()
                    else:
                        st.error("❌ Utilizador ou PIN incorreto.")
                else:
                    st.error("❌ Base de dados vazia.")
            else:
                st.warning("⚠️ Preenche utilizador e PIN.")

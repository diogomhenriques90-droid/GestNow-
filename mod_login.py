import streamlit as st
import pandas as pd
from datetime import datetime
from core import cp, _gcs_read, hp, inv

def _load_users_fresh():
    """Lê usuarios.csv SEMPRE do GCS sem cache — crítico para login."""
    try:
        buf = _gcs_read("usuarios.csv")
        if buf:
            df = pd.read_csv(buf, dtype=str, on_bad_lines='skip', encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            return df.fillna("")
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

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

    st.markdown(
        "<h1 style='text-align:center; color:#60A5FA;'>GESTNOW v3</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center; color:rgba(255,255,255,0.7); margin-bottom:40px;'>"
        "Gestão de Empresas e de Obras Industriais</p>",
        unsafe_allow_html=True
    )

    tab_pwd, tab_pin = st.tabs(["🔑 Password", "🔢 PIN"])

    # ══════════════════════════════════════════════════════════════════
    # TAB PASSWORD
    # ══════════════════════════════════════════════════════════════════
    with tab_pwd:
        username = st.text_input("Utilizador", key="login_u1")
        password = st.text_input("Password", type="password", key="login_p1")

        if st.button("ENTRAR", use_container_width=True, key="login_b1", type="primary"):
            if username and password:
                # ✅ Leitura FRESCA do GCS — sem cache
                users = _load_users_fresh()

                if users.empty:
                    st.error("❌ Base de dados vazia. Cria o utilizador Admin primeiro.")
                    st.markdown("[🔧 Criar Admin](/?page=criar_admin)")
                    st.stop()

                user_found = False
                for _, user in users.iterrows():
                    if str(user.get('Nome', '')).lower() == username.lower():
                        user_found = True
                        pwd_hash = str(user.get('Password', ''))

                        if not pwd_hash:
                            st.error("❌ Este utilizador não tem password definida. Contacta o admin.")
                            break

                        if cp(password, pwd_hash):
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
                st.warning("⚠️ Preenche o utilizador e a password.")

        st.divider()
        st.markdown(
            "<p style='text-align:center; color:#64748B; font-size:0.85rem;'>"
            "Esqueceste a password? Contacta o administrador.</p>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align:center; font-size:0.8rem;'>"
            "<a href='/?page=criar_admin' style='color:#3B82F6;'>🔧 Criar utilizador Admin</a></p>",
            unsafe_allow_html=True
        )

    # ══════════════════════════════════════════════════════════════════
    # TAB PIN
    # ══════════════════════════════════════════════════════════════════
    with tab_pin:
        u_pin = st.text_input("Utilizador", key="login_u2")
        pin   = st.text_input("PIN (4 dígitos)", type="password", max_chars=4, key="login_p2")

        if st.button("ENTRAR COM PIN", use_container_width=True, key="login_b2", type="primary"):
            if u_pin and pin:
                # ✅ Leitura FRESCA do GCS — sem cache
                users = _load_users_fresh()

                if users.empty:
                    st.error("❌ Base de dados vazia.")
                    st.stop()

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
                st.warning("⚠️ Preenche o utilizador e o PIN.")

import streamlit as st
import pandas as pd
import io
from datetime import datetime
from core import cp, _gcs_read, inv

def _load_users_fresh():
    """Lê usuarios.csv SEMPRE do GCS sem cache, com strip de todos os valores."""
    for tentativa in range(3):
        try:
            buf = _gcs_read("usuarios.csv")
            if buf:
                df = pd.read_csv(
                    buf,
                    dtype=str,
                    on_bad_lines='skip',
                    encoding='utf-8-sig'
                )
                # ✅ Strip dos nomes das colunas
                df.columns = df.columns.str.strip()
                # ✅ CRÍTICO: strip de TODOS os valores string nas células
                # Evita falhas por espaços invisíveis no CSV
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].str.strip()
                return df.fillna("")
            # GCS retornou None — esperar e tentar novamente
            import time
            time.sleep(0.3)
        except Exception as e:
            if tentativa == 2:
                return pd.DataFrame()
            import time
            time.sleep(0.3)
    return pd.DataFrame()

def render_login():
    # Limpar estado antigo que possa causar loops
    for key in ['login_error', 'login_tentativas']:
        if key not in st.session_state:
            st.session_state[key] = 0

    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer     {visibility: hidden;}
    header     {visibility: hidden;}
    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        background-attachment: fixed;
    }
    /* Fix para evitar flicker no segundo attempt */
    .stAlert { animation: none !important; }
    </style>
    """, unsafe_allow_html=True)

    _c1, _c2, _c3 = st.columns([1, 2, 1])
    with _c2:
        st.image("assets/logo_cps_tema_escuro.png", width=380)
    st.markdown(
        "<h3 style='text-align:center; color:#60A5FA; margin-top:8px;'>GESTNOW v3</h3>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center; color:rgba(255,255,255,0.7); margin-bottom:40px;'>"
        "Gestão de Empresas e de Obras Industriais</p>",
        unsafe_allow_html=True
    )

    tab_pwd, tab_pin = st.tabs(["🔑 Password", "🔢 PIN"])

    # ═══════════════════════════════════════════════════════════════
    # TAB PASSWORD
    # ═══════════════════════════════════════════════════════════════
    with tab_pwd:
        with st.form("form_login_pwd", clear_on_submit=False):
            username = st.text_input("Utilizador", key="login_u1",
                                     placeholder="Nome completo")
            password = st.text_input("Password", type="password", key="login_p1",
                                     placeholder="••••••••")
            submitted = st.form_submit_button(
                "ENTRAR", use_container_width=True, type="primary"
            )

        if submitted:
            if not username or not password:
                st.warning("⚠️ Preenche o utilizador e a password.")
            else:
                # ✅ Strip do input do utilizador antes de comparar
                username_clean = username.strip()
                password_clean = password.strip()

                with st.spinner("A verificar credenciais..."):
                    users = _load_users_fresh()

                if users.empty:
                    st.error(
                        "❌ Não foi possível aceder à base de dados. "
                        "Tenta novamente em alguns segundos."
                    )
                    st.info("💡 Se o problema persistir, verifica a ligação à internet.")
                else:
                    # ✅ Comparação com strip nos dois lados
                    user_found  = False
                    user_match  = None

                    for _, user in users.iterrows():
                        nome_csv = str(user.get('Nome', '')).strip()
                        if nome_csv.lower() == username_clean.lower():
                            user_found = True
                            user_match = user
                            break

                    if not user_found:
                        st.error(f"❌ Utilizador '{username_clean}' não encontrado.")
                        # Debug: mostrar lista de nomes disponíveis (remover em produção)
                        # with st.expander("🔍 Debug — nomes no sistema"):
                        #     st.write(users['Nome'].tolist())
                    else:
                        pwd_hash = str(user_match.get('Password', '')).strip()

                        if not pwd_hash:
                            st.error(
                                "❌ Este utilizador não tem password definida. "
                                "Contacta o administrador."
                            )
                        elif cp(password_clean, pwd_hash):
                            # ✅ Login bem-sucedido
                            st.session_state['user']          = user_match['Nome'].strip()
                            st.session_state['tipo']          = user_match.get('Tipo', 'Técnico').strip()
                            st.session_state['cargo']         = user_match.get('Cargo', 'Técnico').strip()
                            st.session_state['last_activity'] = datetime.now()
                            st.session_state['menu_selected'] = ''
                            # Limpar contadores de erro
                            st.session_state['login_tentativas'] = 0
                            st.success("✅ Login bem-sucedido!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Password incorreta.")
                            tentativas = st.session_state.get('login_tentativas', 0) + 1
                            st.session_state['login_tentativas'] = tentativas
                            if tentativas >= 3:
                                st.warning(
                                    "⚠️ Várias tentativas falhadas. "
                                    "Contacta o administrador para resetar a tua password."
                                )

        st.divider()
        st.markdown(
            "<p style='text-align:center; color:#64748B; font-size:0.85rem;'>"
            "Esqueceste a password? Contacta o administrador.</p>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align:center; font-size:0.8rem;'>"
            "<a href='/?page=criar_admin' style='color:#3B82F6;'>"
            "🔧 Criar utilizador Admin</a></p>",
            unsafe_allow_html=True
        )

    # ═══════════════════════════════════════════════════════════════
    # TAB PIN
    # ═══════════════════════════════════════════════════════════════
    with tab_pin:
        with st.form("form_login_pin", clear_on_submit=False):
            u_pin = st.text_input("Utilizador", key="login_u2",
                                   placeholder="Nome completo")
            pin   = st.text_input("PIN (4 dígitos)", type="password",
                                   max_chars=4, key="login_p2",
                                   placeholder="0000")
            submitted_pin = st.form_submit_button(
                "ENTRAR COM PIN", use_container_width=True, type="primary"
            )

        if submitted_pin:
            if not u_pin or not pin:
                st.warning("⚠️ Preenche o utilizador e o PIN.")
            elif len(pin.strip()) != 4 or not pin.strip().isdigit():
                st.error("❌ O PIN deve ter exatamente 4 dígitos numéricos.")
            else:
                u_pin_clean = u_pin.strip()
                pin_clean   = pin.strip()

                with st.spinner("A verificar PIN..."):
                    users = _load_users_fresh()

                if users.empty:
                    st.error("❌ Não foi possível aceder à base de dados. Tenta novamente.")
                else:
                    # ✅ Comparação com strip nos dois lados
                    if 'Nome' in users.columns and 'PIN' in users.columns:
                        match = users[
                            (users['Nome'].str.strip().str.lower() == u_pin_clean.lower()) &
                            (users['PIN'].str.strip() == pin_clean)
                        ]
                    else:
                        match = pd.DataFrame()

                    if not match.empty:
                        row = match.iloc[0]
                        st.session_state['user']          = row['Nome'].strip()
                        st.session_state['tipo']          = row.get('Tipo', 'Técnico').strip()
                        st.session_state['cargo']         = row.get('Cargo', 'Técnico').strip()
                        st.session_state['last_activity'] = datetime.now()
                        st.session_state['menu_selected'] = ''
                        st.success("✅ Login com PIN bem-sucedido!")
                        st.rerun()
                    else:
                        # Verificar se o utilizador existe mas o PIN está errado
                        user_existe = users[
                            users['Nome'].str.strip().str.lower() == u_pin_clean.lower()
                        ]
                        if user_existe.empty:
                            st.error(f"❌ Utilizador '{u_pin_clean}' não encontrado.")
                        else:
                            st.error("❌ PIN incorreto.")

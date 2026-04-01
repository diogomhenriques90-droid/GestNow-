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
    
    # ========== DEBUG COMPLETO ==========
    try:
        with st.expander("🔍 DEBUG - Ver estado da BD", expanded=True):
            result = load_all()
            st.write(f"**Total de dataframes:** {len(result)}")
            
            if len(result) >= 1:
                users = result[0]
                st.write(f"**Utilizadores encontrados:** {len(users)}")
                
                if len(users) > 0:
                    st.write("**Lista de utilizadores:**")
                    st.write(users['Nome'].tolist())
                    st.write("**Colunas disponíveis:**")
                    st.write(users.columns.tolist())
                    st.write("**Primeiras linhas:**")
                    st.write(users.head())
                else:
                    st.error("❌ DataFrame de utilizadores está VAZIO!")
                    st.warning("💡 Precisa criar utilizadores no CSV!")
            else:
                st.error("❌ load_all() não retornou dados!")
    except Exception as e:
        st.error(f"❌ ERRO: {e}")
        st.stop()
    
    # ========== LOGIN ==========
    tab_pwd, tab_pin = st.tabs(["🔑 Password", "🔢 PIN"])
    
    with tab_pwd:
        username = st.text_input("Utilizador", key="u1")
        password = st.text_input("Password", type="password", key="p1")
        
        if st.button("ENTRAR", use_container_width=True, key="b1"):
            if username and password:
                # Carregar dados
                result = load_all()
                users = result[0] if len(result) > 0 else None
                
                if users is None or users.empty:
                    st.error("❌ Base de dados de utilizadores vazia!")
                    st.stop()
                
                # Procurar utilizador
                user_found = False
                for idx, user in users.iterrows():
                    user_name = user.get('Nome', '')
                    st.info(f"🔍 A verificar: {user_name}")
                    
                    if user_name.lower() == username.lower():
                        user_found = True
                        st.success(f"✅ Utilizador '{username}' encontrado!")
                        
                        # Verificar password
                        stored_hash = user.get('Password', '')
                        st.info(f"🔐 Hash na BD: {stored_hash[:20]}...")
                        
                        if cp(password, stored_hash):
                            st.success("✅ Password correta!")
                            st.session_state['user'] = username
                            st.session_state['tipo'] = user.get('Tipo', 'Técnico')
                            st.session_state['cargo'] = user.get('Cargo', 'Técnico')
                            st.session_state['last_activity'] = datetime.now()
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Password incorreta")
                            st.info(f"💡 Password inserida: {password}")
                        break
                
                if not user_found:
                    st.error(f"❌ Utilizador '{username}' não encontrado!")
                    st.info(f"💡 Utilizadores disponíveis: {users['Nome'].tolist()}")
    
    with tab_pin:
        u_pin = st.text_input("Utilizador", key="u2")
        pin = st.text_input("PIN", type="password", key="p2")
        
        if st.button("ENTRAR COM PIN", use_container_width=True, key="b2"):
            if u_pin and pin:
                result = load_all()
                users = result[0] if len(result) > 0 else None
                
                if users is not None and not users.empty:
                    match = users[(users['Nome'].str.lower() == u_pin.lower()) & (users['PIN'] == pin)]
                    if not match.empty:
                        st.session_state['user'] = match.iloc[0]['Nome']
                        st.session_state['tipo'] = match.iloc[0]['Tipo']
                        st.session_state['last_activity'] = datetime.now()
                        st.success("✅ Login!")
                        st.rerun()
                    else:
                        st.error("❌ PIN incorreto")

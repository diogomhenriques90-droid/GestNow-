import streamlit as st
import pandas as pd
import io, base64
from datetime import datetime
from core import (
    cp, hp, save_db, _gcs_read, inv, THEME,
    registar_tentativa_login, contar_falhas_recentes,
    limpar_tentativas_login, bloquear_conta_por_numero,
    criar_notificacao,
)

# Tipos que entram por PIN (colaboradores de campo, normalmente ao
# telemóvel) — todos os outros entram por Password. Ver briefing da
# Fase 1: PIN prioriza rapidez em campo, Password prioriza força para
# quem mexe em dados financeiros/pessoais a partir de um computador.
TIPOS_PIN = {"Técnico", "Instrumentista", "Engenheiro", "Chefe de Equipa", "Armazém"}

_LIMITE_TENTATIVAS = 3

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

def _render_forcar_reset_password():
    """Ecrã intermédio: mostrado quando alguém autentica com sucesso
    através de uma Password mais curta que o mínimo atual (8
    caracteres) — legado de antes da Fase 1. A sessão só fica completa
    depois de definir uma password nova."""
    numero = st.session_state.get('_forcar_reset_numero', '')

    st.warning(
        "A tua password é mais curta do que o mínimo atual "
        "(8 caracteres). Define uma password nova para continuar."
    )
    with st.form("form_forcar_reset", clear_on_submit=False):
        nova = st.text_input("Nova Password", type="password",
                              key="reset_nova_pwd")
        conf = st.text_input("Confirmar Nova Password", type="password",
                              key="reset_conf_pwd")
        submitted = st.form_submit_button(
            "Definir Password", use_container_width=True, type="primary"
        )

    if submitted:
        if len(nova) < 8:
            st.error("Mínimo 8 caracteres.")
        elif nova != conf:
            st.error("As passwords não coincidem.")
        else:
            users = _load_users_fresh()
            mask = users['Numero_Colaborador'].astype(str).str.strip() == numero \
                if 'Numero_Colaborador' in users.columns else pd.Series(dtype=bool)
            if mask.any():
                row = users.loc[mask].iloc[0]
                users.loc[mask, 'Password'] = hp(nova)
                save_db(users, "usuarios.csv")
                inv("usuarios.csv")
                del st.session_state['_forcar_reset_numero']
                st.session_state['user']          = row['Nome'].strip()
                st.session_state['tipo']          = row.get('Tipo', 'Técnico').strip()
                st.session_state['cargo']         = row.get('Cargo', 'Técnico').strip()
                st.session_state['last_activity'] = datetime.now()
                st.session_state['menu_selected'] = ''
                st.success("Password atualizada. A entrar...")
                st.rerun()
            else:
                del st.session_state['_forcar_reset_numero']
                st.error("Ocorreu um erro a localizar a conta. Tenta entrar novamente.")
                st.rerun()

def _completar_login_antigo(row):
    """Login bem-sucedido pela via antiga (por Nome). Enquanto durar a
    transição, quem já tiver Número de colaborador atribuído vê-o em
    destaque antes de entrar, para o aprender sem ser preciso
    contactá-lo um a um. Quem ainda não tiver número (ex. duplicado
    por resolver) entra normalmente, sem o passo extra."""
    numero = str(row.get('Numero_Colaborador', '')).strip()
    if numero:
        st.session_state['_pendente_login'] = {
            "nome":   row['Nome'].strip(),
            "tipo":   row.get('Tipo', 'Técnico').strip(),
            "cargo":  row.get('Cargo', 'Técnico').strip(),
            "numero": numero,
        }
        st.rerun()
    else:
        st.session_state['user']          = row['Nome'].strip()
        st.session_state['tipo']          = row.get('Tipo', 'Técnico').strip()
        st.session_state['cargo']         = row.get('Cargo', 'Técnico').strip()
        st.session_state['last_activity'] = datetime.now()
        st.session_state['menu_selected'] = ''
        st.success("Login bem-sucedido!")
        st.balloons()
        st.rerun()

def _render_banner_numero():
    """Ecrã intermédio (rollout Fase 1): mostra o Número de colaborador
    a quem entrou pela via antiga, antes de completar a sessão."""
    pendente = st.session_state.get('_pendente_login', {})
    st.success(f"Login bem-sucedido, {pendente.get('nome','')}!")
    st.markdown(
        f"<div style='background:{THEME['surface']};border:2px solid {THEME['accent']};"
        f"border-radius:{THEME['radius']};padding:24px;text-align:center;margin:16px 0;'>"
        f"<p style='color:{THEME['text_secondary']};font-size:0.85rem;margin:0 0 8px;'>"
        "O teu número de colaborador é</p>"
        f"<p style='color:{THEME['text']};font-size:2.2rem;font-weight:800;"
        f"letter-spacing:0.1em;margin:0 0 8px;'>{pendente.get('numero','')}</p>"
        f"<p style='color:{THEME['text_secondary']};font-size:0.82rem;margin:0;'>"
        "Grava-o — vais precisar dele para entrar quando este acesso por "
        "Nome deixar de existir.</p></div>",
        unsafe_allow_html=True
    )
    if st.button("Continuar", key="btn_continuar_banner_numero",
                 use_container_width=True, type="primary"):
        st.session_state['user']          = pendente.get('nome', '')
        st.session_state['tipo']          = pendente.get('tipo', 'Técnico')
        st.session_state['cargo']         = pendente.get('cargo', 'Técnico')
        st.session_state['last_activity'] = datetime.now()
        st.session_state['menu_selected'] = ''
        del st.session_state['_pendente_login']
        st.rerun()

def render_login():
    if st.session_state.get('_forcar_reset_numero'):
        st.markdown("<div class='login-wrap'><div class='login-card'>",
                    unsafe_allow_html=True)
        _render_forcar_reset_password()
        st.markdown("</div></div>", unsafe_allow_html=True)
        return

    if st.session_state.get('_pendente_login'):
        st.markdown("<div class='login-wrap'><div class='login-card'>",
                    unsafe_allow_html=True)
        _render_banner_numero()
        st.markdown("</div></div>", unsafe_allow_html=True)
        return

    # Limpar estado antigo que possa causar loops
    for key in ['login_error', 'login_tentativas']:
        if key not in st.session_state:
            st.session_state[key] = 0

    st.markdown(f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer     {{visibility: hidden;}}
    header     {{visibility: hidden;}}
    /* Fix para evitar flicker no segundo attempt */
    .stAlert {{ animation: none !important; }}

    .login-wrap .block-container {{
        max-width: 460px; margin: 0 auto; padding-top: 6vh;
    }}
    .login-card {{
        background: {THEME['surface']};
        border: 1px solid {THEME['border']};
        border-radius: {THEME['radius']};
        box-shadow: 0 1px 3px rgba(16,24,40,0.05), 0 8px 24px rgba(16,24,40,0.06);
        padding: 32px 28px 24px;
        margin-top: 8px;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-wrap'>", unsafe_allow_html=True)

    with open("assets/logo_cps_transparente.png", "rb") as _f:
        _logo_b64 = base64.b64encode(_f.read()).decode()
    st.markdown(
        f"<div style='display:flex;justify-content:center;margin:8px 0 4px 0;'>"
        f"<img src='data:image/png;base64,{_logo_b64}' alt='CPS Smart Solutions' "
        f"style='width:min(380px,80vw);height:auto;'/></div>",
        unsafe_allow_html=True
    )

    st.markdown("<div class='login-card'>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════
    # LOGIN POR NÚMERO DE COLABORADOR (via principal)
    # ═══════════════════════════════════════════════════════════════
    with st.form("form_login_numero", clear_on_submit=False):
        numero = st.text_input("Número de colaborador", key="login_numero",
                                max_chars=5, placeholder="00000")
        credencial = st.text_input("Credencial", type="password",
                                    key="login_credencial",
                                    placeholder="••••••••")
        submitted_num = st.form_submit_button(
            "ENTRAR", use_container_width=True, type="primary"
        )

    if submitted_num:
        if not numero or not credencial:
            st.warning("Preenche os dois campos.")
        elif not (numero.strip().isdigit() and len(numero.strip()) == 5):
            st.error("Credenciais inválidas.")
        else:
            numero_clean = numero.strip()

            with st.spinner("A verificar credenciais..."):
                users = _load_users_fresh()

            if users.empty:
                st.error(
                    "Não foi possível aceder à base de dados. "
                    "Tenta novamente em alguns segundos."
                )
            else:
                match = users[
                    users['Numero_Colaborador'].astype(str).str.strip() == numero_clean
                ] if 'Numero_Colaborador' in users.columns else pd.DataFrame()

                row       = None
                bloqueada = False
                sucesso   = False

                if not match.empty:
                    row = match.iloc[0]
                    bloqueada = str(row.get('Bloqueado', '')).strip().lower() == 'sim'
                    if not bloqueada:
                        tipo = str(row.get('Tipo', '')).strip()
                        campo_credencial = 'PIN' if tipo in TIPOS_PIN else 'Password'
                        hash_guardado = str(row.get(campo_credencial, '')).strip()
                        if hash_guardado and cp(credencial, hash_guardado):
                            sucesso = True

                if sucesso:
                    limpar_tentativas_login(numero_clean)
                    if campo_credencial == 'Password' and len(credencial) < 8:
                        # Password anterior ao mínimo de 8 caracteres —
                        # não completa a sessão ainda, força a definição
                        # de uma password nova primeiro.
                        st.session_state['_forcar_reset_numero'] = numero_clean
                        st.rerun()
                    else:
                        st.session_state['user']          = row['Nome'].strip()
                        st.session_state['tipo']          = row.get('Tipo', 'Técnico').strip()
                        st.session_state['cargo']         = row.get('Cargo', 'Técnico').strip()
                        st.session_state['last_activity'] = datetime.now()
                        st.session_state['menu_selected'] = ''
                        st.success("Login bem-sucedido!")
                        st.balloons()
                        st.rerun()
                else:
                    # Regista a tentativa quer o número exista quer não —
                    # a resposta abaixo é sempre a mesma nos dois casos.
                    registar_tentativa_login(numero_clean)
                    if not match.empty and not bloqueada:
                        falhas = contar_falhas_recentes(numero_clean)
                        if falhas >= _LIMITE_TENTATIVAS:
                            ficou_bloqueada = bloquear_conta_por_numero(numero_clean, users)
                            if ficou_bloqueada:
                                criar_notificacao(
                                    destinatario="admin",
                                    titulo="Conta bloqueada",
                                    mensagem=(
                                        f"A conta de {row['Nome'].strip()} "
                                        f"(nº {numero_clean}) foi bloqueada "
                                        "após tentativas de login falhadas."
                                    ),
                                    tipo="warning",
                                )
                    st.error("Credenciais inválidas.")

    st.markdown(
        f"<p style='text-align:center; color:{THEME['text_secondary']}; font-size:0.85rem; margin-top:8px;'>"
        f"Esqueceste a credencial ou a conta está bloqueada? Contacta o administrador.</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='text-align:center; font-size:0.8rem;'>"
        f"<a href='/?page=criar_admin' style='color:{THEME['accent']};'>"
        f"Criar utilizador Admin</a></p>",
        unsafe_allow_html=True
    )

    st.divider()

    # ═══════════════════════════════════════════════════════════════
    # ACESSO ANTIGO (por Nome) — só durante a janela de transição
    # ═══════════════════════════════════════════════════════════════
    with st.expander("Acesso antigo (por Nome)"):
        st.markdown(
            f"<p style='color:{THEME['text_secondary']}; font-size:0.8rem;'>"
            "Disponível apenas durante a transição para o número de "
            "colaborador. Vai deixar de existir em breve.</p>",
            unsafe_allow_html=True
        )
        tab_pwd, tab_pin = st.tabs(["Password", "PIN"])

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
                    st.warning("Preenche o utilizador e a password.")
                else:
                    # ✅ Strip do input do utilizador antes de comparar
                    username_clean = username.strip()
                    password_clean = password.strip()

                    with st.spinner("A verificar credenciais..."):
                        users = _load_users_fresh()

                    if users.empty:
                        st.error(
                            "Não foi possível aceder à base de dados. "
                            "Tenta novamente em alguns segundos."
                        )
                        st.info("Se o problema persistir, verifica a ligação à internet.")
                    else:
                        # ✅ Comparação com strip nos dois lados
                        matches = [
                            user for _, user in users.iterrows()
                            if str(user.get('Nome', '')).strip().lower()
                               == username_clean.lower()
                        ]

                        if len(matches) == 0:
                            st.error(f"Utilizador '{username_clean}' não encontrado.")
                        elif len(matches) > 1:
                            # Mais do que um colaborador com o mesmo Nome —
                            # nunca autenticar o primeiro "por sorte" (já
                            # aconteceu em produção, ver mod_dashboard_obra.py).
                            st.error(
                                "Existe mais do que um utilizador com este nome. "
                                "Contacta o administrador para resolver a ambiguidade."
                            )
                        else:
                            user_match = matches[0]
                            pwd_hash = str(user_match.get('Password', '')).strip()

                            if not pwd_hash:
                                st.error(
                                    "Este utilizador não tem password definida. "
                                    "Contacta o administrador."
                                )
                            elif cp(password_clean, pwd_hash):
                                # Limpar contadores de erro
                                st.session_state['login_tentativas'] = 0
                                _completar_login_antigo(user_match)
                            else:
                                st.error("Password incorreta.")
                                tentativas = st.session_state.get('login_tentativas', 0) + 1
                                st.session_state['login_tentativas'] = tentativas
                                if tentativas >= 3:
                                    st.warning(
                                        "Várias tentativas falhadas. "
                                        "Contacta o administrador para resetar a tua password."
                                    )

        # ═══════════════════════════════════════════════════════════
        # TAB PIN
        # ═══════════════════════════════════════════════════════════
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
                    st.warning("Preenche o utilizador e o PIN.")
                elif len(pin.strip()) != 4 or not pin.strip().isdigit():
                    st.error("O PIN deve ter exatamente 4 dígitos numéricos.")
                else:
                    u_pin_clean = u_pin.strip()
                    pin_clean   = pin.strip()

                    with st.spinner("A verificar PIN..."):
                        users = _load_users_fresh()

                    if users.empty:
                        st.error("Não foi possível aceder à base de dados. Tenta novamente.")
                    else:
                        # ✅ Verificar primeiro se o Nome é único, antes de
                        # sequer olhar para o PIN — nunca autenticar por
                        # coincidência de um PIN igual entre duas pessoas com
                        # o mesmo Nome (já aconteceu em produção, ver
                        # mod_dashboard_obra.py).
                        if 'Nome' in users.columns:
                            nome_matches = users[
                                users['Nome'].str.strip().str.lower() == u_pin_clean.lower()
                            ]
                        else:
                            nome_matches = pd.DataFrame()

                        if nome_matches.empty:
                            st.error(f"Utilizador '{u_pin_clean}' não encontrado.")
                        elif len(nome_matches) > 1:
                            st.error(
                                "Existe mais do que um utilizador com este nome. "
                                "Contacta o administrador para resolver a ambiguidade."
                            )
                        else:
                            row = nome_matches.iloc[0]
                            pin_hash = str(row.get('PIN', '')).strip()
                            if pin_hash and cp(pin_clean, pin_hash):
                                _completar_login_antigo(row)
                            else:
                                st.error("PIN incorreto.")

    st.markdown("</div></div>", unsafe_allow_html=True)

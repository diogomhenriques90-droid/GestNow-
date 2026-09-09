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

def render_login():
    if st.session_state.get('_forcar_reset_numero'):
        st.markdown("<div class='login-wrap'><div class='login-card'>",
                    unsafe_allow_html=True)
        _render_forcar_reset_password()
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
    # LOGIN — NÚMERO DE COLABORADOR + PASSWORD (única via)
    # ═══════════════════════════════════════════════════════════════
    with st.form("form_login_numero", clear_on_submit=False):
        numero = st.text_input("Número de colaborador", key="login_numero",
                                max_chars=5, placeholder="00000")
        credencial = st.text_input("Password", type="password",
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
                        hash_guardado = str(row.get('Password', '')).strip()
                        if hash_guardado and cp(credencial, hash_guardado):
                            sucesso = True

                if sucesso:
                    limpar_tentativas_login(numero_clean)
                    if len(credencial) < 8:
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

    st.markdown("</div></div>", unsafe_allow_html=True)

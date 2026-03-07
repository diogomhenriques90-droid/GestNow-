"""
GESTNOW v3 — app.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PONTO DE ENTRADA. Este ficheiro não tem lógica de negócio.

Faz apenas 4 coisas:
  1. Importa os módulos
  2. Inicializa a sessão e verifica timeout
  3. Carrega dados (load_all do core.py)
  4. Routing: decide qual módulo renderizar

Para alterar qualquer funcionalidade → editar o módulo correspondente.
Para dados novos → core.py (load_all + save_db).
Para novo ecrã inteiro (ex: fornecedores) → criar mod_fornecedores.py
                                              e adicionar uma linha de routing aqui.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from core import (
    st, datetime, load_all, inv,
    init_session, check_timeout
)
from mod_login   import render_login
from mod_admin   import render_admin
from mod_tecnico import render_tecnico

# ── 1. Inicializar sessão ────────────────────────────────────────────────────
init_session()
check_timeout()

# ── 2. Sidebar (só quando autenticado) ──────────────────────────────────────
if st.session_state.get('user'):
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.caption(f"Tipo: {st.session_state.tipo}"); st.divider()
        if st.button("🔄 Reiniciar dados locais", use_container_width=True,
                     help="Limpa cache e força resincronização"):
            st.session_state['reiniciar_dados'] = True
        if st.session_state.get('reiniciar_dados'):
            st.markdown("<div style='background:white;padding:1rem;border-radius:12px;text-align:center;'>",
                        unsafe_allow_html=True)
            st.warning("⚠️ Limpar dados locais e atualizar?")
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                if st.button("✅ Confirmar", key="reiniciar_sim", use_container_width=True):
                    load_all.clear()
                    for k in list(st.session_state.keys()):
                        if k not in ['user','tipo','cargo','session_token']:
                            del st.session_state[k]
                    st.success("✅ Dados reiniciados!"); st.rerun()
            with c_r2:
                if st.button("✕ Cancelar", key="reiniciar_nao", use_container_width=True):
                    st.session_state['reiniciar_dados'] = False; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        st.divider()
        if st.button("🚪 Terminar Sessão", use_container_width=True):
            st.session_state.clear(); st.rerun()
        st.divider()
        st.caption(f"Sessão: {st.session_state.get('last_activity', datetime.now()).strftime('%d/%m/%Y %H:%M')}")

# ── 3. Routing ───────────────────────────────────────────────────────────────
if not st.session_state.get('user'):
    # ── Não autenticado → login
    render_login()

else:
    # ── Autenticado → carregar dados
    (users, obras_db, frentes_db, registos_db, faturas_db,
     docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db,
     comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db) = load_all()

    DB = dict(
        users=users, obras_db=obras_db, frentes_db=frentes_db,
        registos_db=registos_db, faturas_db=faturas_db,
        docs_db=docs_db, incs_db=incs_db, sw_db=sw_db,
        obs_db=obs_db, equip_db=equip_db,
        diags_db=diags_db, diags_u_db=diags_u_db, folhas_db=folhas_db,
        comuns_db=comuns_db, comuns_u_db=comuns_u_db,
        req_fer_db=req_fer_db, req_mat_db=req_mat_db, req_epi_db=req_epi_db,
        avals_db=avals_db,
    )

    # ── Routing por tipo de utilizador
    tipo = st.session_state.get('tipo', '')

    if tipo == "Admin":
        render_admin(**DB)
    else:
        # Técnico, Chefe de Equipa, Encarregado, Supervisor, etc.
        render_tecnico(**DB)

    # ── Para adicionar um novo tipo de utilizador no futuro:
    # elif tipo == "Fornecedor":
    #     from mod_fornecedor import render_fornecedor
    #     render_fornecedor(**DB)

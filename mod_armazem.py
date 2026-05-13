# mod_armazem.py — VERSÃO CORRIGIDA
import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, log_audit, criar_notificacao

def render_armazem(req_fer_db, req_mat_db, req_epi_db, incs_db, *_):

    st.markdown("### 📦 Gestão de Armazém & Validações")

    tab_epis, tab_ferramentas, tab_materiais, tab_compras = st.tabs([
        "🦺 EPIs", "🔧 Ferramentas", "📦 Materiais", "🛒 Compras"
    ])

    # ═══ TAB EPIs ════════════════════════════════════════════════════
    with tab_epis:
        st.markdown("### 🦺 Validação de EPIs")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not req_epi_db.empty:
                if 'Data_Validacao' not in req_epi_db.columns: req_epi_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_epi_db.columns: req_epi_db['Validado_Por']   = ""
                pend = req_epi_db[req_epi_db['Status'] == 'Pendente']
                if not pend.empty:
                    st.markdown(f"**{len(pend)} pedido(s) pendente(s)**")
                    for idx, ped in pend.iterrows():
                        ped_id = ped.get('ID', f"EPI_{idx}")
                        with st.expander(
                            f"🦺 {ped.get('Item','EPI')} — "
                            f"{ped.get('Solicitante','N/A')} ({ped.get('Obra','N/A')})",
                            expanded=True
                        ):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);
                                padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Item:</strong> {ped.get('Item','N/A')} ({ped.get('Tamanho','N/A')})</p>
                                <p><strong>Quantidade:</strong> {ped.get('Quantidade',1)}</p>
                                <p><strong>Data:</strong> {ped.get('Data','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar", key=f"apr_epi_{ped_id}",
                                              use_container_width=True):
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_epi_db, "req_epis.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_EPI",
                                              tabela="req_epis.csv", registro_id=ped_id,
                                              detalhes=f"EPI aprovado: {ped.get('Item')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante',''),
                                        titulo="✅ EPI Aprovado",
                                        mensagem=f"O teu pedido de {ped.get('Item')} foi aprovado!",
                                        tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_epi_{ped_id}",
                                              use_container_width=True, type="secondary"):
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_epi_db, "req_epis.csv")
                                    criar_notificacao(destinatario=ped.get('Solicitante',''),
                                        titulo="❌ EPI Rejeitado",
                                        mensagem=f"O teu pedido de {ped.get('Item')} foi rejeitado.",
                                        tipo="error", acao_url="/tecnico")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem pedidos de EPI pendentes!")
            else:
                st.info("📋 Sem pedidos de EPI.")

        with sub_h:
            if not req_epi_db.empty:
                hist = req_epi_db[req_epi_db['Status'].isin(['Aprovado','Rejeitado'])]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Item',
                                        'Quantidade','Status','Data_Validacao','Validado_Por']
                            if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")

    # ═══ TAB FERRAMENTAS ═════════════════════════════════════════════
    with tab_ferramentas:
        st.markdown("### 🔧 Validação de Ferramentas")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not req_fer_db.empty:
                if 'Data_Validacao' not in req_fer_db.columns: req_fer_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_fer_db.columns: req_fer_db['Validado_Por']   = ""
                pend = req_fer_db[req_fer_db['Status'] == 'Pendente']
                if not pend.empty:
                    st.markdown(f"**{len(pend)} pedido(s) pendente(s)**")
                    for idx, ped in pend.iterrows():
                        ped_id = ped.get('ID', f"FER_{idx}")
                        with st.expander(
                            f"🔧 {str(ped.get('Descricao','Ferramenta'))[:50]} — "
                            f"{ped.get('Solicitante','N/A')}",
                            expanded=True
                        ):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);
                                padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao','N/A')}</p>
                                <p><strong>Urgência:</strong> {ped.get('Urgencia','N/A')}</p>
                                <p><strong>Data:</strong> {ped.get('Data','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            if ped.get('Foto_b64'):
                                try:
                                    st.image(f"data:image/png;base64,{ped['Foto_b64']}",
                                             caption="Foto", width=200)
                                except:
                                    pass
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar", key=f"apr_fer_{ped_id}",
                                              use_container_width=True):
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_fer_db, "req_ferramentas.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_FERRAMENTA",
                                              tabela="req_ferramentas.csv", registro_id=ped_id,
                                              detalhes="Ferramenta aprovada", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante',''),
                                        titulo="✅ Ferramenta Aprovada",
                                        mensagem="O teu pedido de ferramenta foi aprovado!",
                                        tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_fer_{ped_id}",
                                              use_container_width=True, type="secondary"):
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_fer_db, "req_ferramentas.csv")
                                    criar_notificacao(destinatario=ped.get('Solicitante',''),
                                        titulo="❌ Ferramenta Rejeitada",
                                        mensagem="O teu pedido de ferramenta foi rejeitado.",
                                        tipo="error", acao_url="/tecnico")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem pedidos de ferramentas pendentes!")
            else:
                st.info("📋 Sem pedidos de ferramentas.")

        with sub_h:
            if not req_fer_db.empty:
                hist = req_fer_db[req_fer_db['Status'].isin(['Aprovado','Rejeitado'])]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Descricao',
                                        'Urgencia','Status','Data_Validacao','Validado_Por']
                            if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")

    # ═══ TAB MATERIAIS ════════════════════════════════════════════════
    with tab_materiais:
        st.markdown("### 📦 Validação de Materiais")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not req_mat_db.empty:
                if 'Data_Validacao' not in req_mat_db.columns: req_mat_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_mat_db.columns: req_mat_db['Validado_Por']   = ""
                pend = req_mat_db[
                    (req_mat_db['Status'] == 'Pendente') &
                    (req_mat_db.get('Tipo', pd.Series([''] * len(req_mat_db))) != 'Gasóleo')
                ]
                if not pend.empty:
                    st.markdown(f"**{len(pend)} pedido(s) pendente(s)**")
                    for idx, ped in pend.iterrows():
                        ped_id = ped.get('ID', f"MAT_{idx}")
                        with st.expander(
                            f"📦 {str(ped.get('Descricao','Material'))[:50]} — "
                            f"{ped.get('Solicitante','N/A')}",
                            expanded=True
                        ):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);
                                padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao','N/A')}</p>
                                <p><strong>Quantidade:</strong> {ped.get('Quantidade',1)}{ped.get('Unidade','')}</p>
                                <p><strong>Urgência:</strong> {ped.get('Urgencia','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar", key=f"apr_mat_{ped_id}",
                                              use_container_width=True):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    criar_notificacao(destinatario=ped.get('Solicitante',''),
                                        titulo="✅ Material Aprovado",
                                        mensagem="O teu pedido de material foi aprovado!",
                                        tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_mat_{ped_id}",
                                              use_container_width=True, type="secondary"):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    criar_notificacao(destinatario=ped.get('Solicitante',''),
                                        titulo="❌ Material Rejeitado",
                                        mensagem="O teu pedido de material foi rejeitado.",
                                        tipo="error", acao_url="/tecnico")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem pedidos de materiais pendentes!")
            else:
                st.info("📋 Sem pedidos de materiais.")

        with sub_h:
            if not req_mat_db.empty:
                hist = req_mat_db[
                    (req_mat_db['Status'].isin(['Aprovado','Rejeitado'])) &
                    (req_mat_db.get('Tipo', pd.Series([''] * len(req_mat_db))) != 'Gasóleo')
                ]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Descricao',
                                        'Quantidade','Unidade','Status','Data_Validacao','Validado_Por']
                            if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")

    # ═══ TAB COMPRAS ═════════════════════════════════════════════════
    with tab_compras:
        from mod_admin_compras import render_compras
        render_compras()

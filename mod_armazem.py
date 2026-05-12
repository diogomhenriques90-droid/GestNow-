import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, log_audit, criar_notificacao

def render_armazem(req_fer_db, req_mat_db, req_epi_db, incs_db, *_):

    st.markdown("### 📦 Gestão de Armazém & Validações")

    tab_epis, tab_ferramentas, tab_materiais, tab_gasoleos, tab_avarias = st.tabs([
        "🦺 EPIs", "🔧 Ferramentas", "📦 Materiais", "⛽ Gasóleos", "🔧 Avarias"
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
                                              detalhes=f"Ferramenta aprovada", ip="")
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

    # ═══ TAB GASÓLEOS ════════════════════════════════════════════════
    with tab_gasoleos:
        st.markdown("### ⛽ Validação de Gasóleos")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not req_mat_db.empty:
                if 'Data_Validacao' not in req_mat_db.columns: req_mat_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_mat_db.columns: req_mat_db['Validado_Por']   = ""
                pend_gas = req_mat_db[
                    (req_mat_db['Status'] == 'Pendente') &
                    (req_mat_db.get('Tipo', pd.Series([''] * len(req_mat_db))) == 'Gasóleo')
                ]
                if not pend_gas.empty:
                    for idx, ped in pend_gas.iterrows():
                        ped_id = ped.get('ID', f"GAS_{idx}")
                        with st.expander(
                            f"⛽ {ped.get('Litros',0)}L — "
                            f"{ped.get('Solicitante','N/A')} ({ped.get('Obra','N/A')})",
                            expanded=True
                        ):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);
                                padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Litros:</strong> {ped.get('Litros',0)}L</p>
                                <p><strong>Valor:</strong> €{ped.get('Valor',0)}</p>
                                <p><strong>Data:</strong> {ped.get('Data_Abastecimento','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            if ped.get('Recibo_b64'):
                                recibo_str = str(ped.get('Recibo_b64',''))
                                if recibo_str.startswith('JVBER'):
                                    st.info("📄 Recibo PDF — descarrega para visualizar")
                                else:
                                    try:
                                        st.image(f"data:image/png;base64,{recibo_str}",
                                                 caption="Recibo", width=300)
                                    except:
                                        pass
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Validar", key=f"apr_gas_{ped_id}",
                                              use_container_width=True):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    criar_notificacao(destinatario=ped.get('Solicitante',''),
                                        titulo="✅ Gasóleo Validado",
                                        mensagem=f"{ped.get('Litros')}L validados!",
                                        tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_gas_{ped_id}",
                                              use_container_width=True, type="secondary"):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem gasóleos pendentes!")

        with sub_h:
            if not req_mat_db.empty:
                hist = req_mat_db[
                    (req_mat_db['Status'].isin(['Aprovado','Rejeitado'])) &
                    (req_mat_db.get('Tipo', pd.Series([''] * len(req_mat_db))) == 'Gasóleo')
                ]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Litros',
                                        'Valor','Status','Data_Validacao','Validado_Por']
                            if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")

    # ═══ TAB AVARIAS ═════════════════════════════════════════════════
    with tab_avarias:
        st.markdown("### 🔧 Validação de Avarias")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not incs_db.empty:
                if 'Data_Validacao' not in incs_db.columns: incs_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in incs_db.columns: incs_db['Validado_Por']   = ""
                pend_av = incs_db[
                    (incs_db['Status'] == 'Pendente') &
                    (incs_db.get('Tipo', pd.Series([''] * len(incs_db))) == 'Avaria')
                ]
                if not pend_av.empty:
                    for idx, ped in pend_av.iterrows():
                        ped_id = ped.get('ID', f"AVAR_{idx}")
                        cor_u  = {"Baixa":"#10B981","Média":"#F59E0B",
                                  "Alta":"#EF4444","Crítica - Paragem":"#DC2626"}.get(
                                      ped.get('Urgencia','Média'),"#6B7280")
                        with st.expander(
                            f"🔧 {str(ped.get('Equipamento','Equipamento'))[:40]} — "
                            f"{ped.get('Solicitante','N/A')}",
                            expanded=True
                        ):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);
                                padding:15px;border-radius:10px;border-left:4px solid {cor_u};">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Equipamento:</strong> {ped.get('Equipamento','N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao','N/A')}</p>
                                <p><strong>Urgência:</strong>
                                    <span style="color:{cor_u};font-weight:bold;">
                                        {ped.get('Urgencia','N/A')}
                                    </span></p>
                                <p><strong>Valor Estimado:</strong> €{ped.get('Valor_Estimado',0)}</p>
                            </div>""", unsafe_allow_html=True)
                            if ped.get('Fatura_b64'):
                                fat_str = str(ped.get('Fatura_b64',''))
                                if fat_str.startswith('JVBER'):
                                    st.info("📄 Fatura PDF")
                                else:
                                    try:
                                        st.image(f"data:image/png;base64,{fat_str}",
                                                 caption="Fatura", width=300)
                                    except:
                                        pass
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar", key=f"apr_av_{ped_id}",
                                              use_container_width=True):
                                    incs_db.loc[incs_db.index == idx, 'Status']         = 'Aprovado'
                                    incs_db.loc[incs_db.index == idx, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    incs_db.loc[incs_db.index == idx, 'Validado_Por']   = st.session_state.user
                                    save_db(incs_db, "incidentes.csv")
                                    criar_notificacao(destinatario=ped.get('Solicitante',''),
                                        titulo="✅ Reparação Aprovada",
                                        mensagem=f"A tua reparação de {ped.get('Equipamento')} foi aprovada!",
                                        tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_av_{ped_id}",
                                              use_container_width=True, type="secondary"):
                                    incs_db.loc[incs_db.index == idx, 'Status']         = 'Rejeitado'
                                    incs_db.loc[incs_db.index == idx, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    incs_db.loc[incs_db.index == idx, 'Validado_Por']   = st.session_state.user
                                    save_db(incs_db, "incidentes.csv")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem avarias pendentes!")

        with sub_h:
            if not incs_db.empty:
                hist = incs_db[
                    (incs_db['Status'].isin(['Aprovado','Rejeitado'])) &
                    (incs_db.get('Tipo', pd.Series([''] * len(incs_db))) == 'Avaria')
                ]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Equipamento',
                                        'Urgencia','Status','Data_Validacao','Validado_Por']
                            if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")

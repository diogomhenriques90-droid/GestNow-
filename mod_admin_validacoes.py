import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, log_audit, criar_notificacao, notificar_por_email

def render_validacoes(req_fer_db, req_mat_db, req_epi_db, registos_db, users, obras_db, incs_db):

    st.markdown("### ✅ Centro de Validações")

    # CSS — botões do dataframe (download/fullscreen) com texto preto
    st.markdown("""
    <style>
    [data-testid="stDataFrameToolbar"] button {
        background: #1E293B !important;
        color: #F1F5F9 !important;
        border: 1px solid #334155 !important;
    }
    [data-testid="stDataFrameToolbar"] button svg {
        fill: #F1F5F9 !important;
    }
    [data-testid="stElementToolbar"] button {
        background: #1E293B !important;
        color: #F1F5F9 !important;
        border: 1px solid #334155 !important;
    }
    [data-testid="stElementToolbar"] button svg {
        fill: #F1F5F9 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    tab_horas, tab_epis, tab_ferramentas, tab_materiais, tab_gasoleos, tab_avarias = st.tabs([
        "⏱️ Horas", "🦺 EPIs", "🔧 Ferramentas", "📦 Materiais", "⛽ Gasóleos", "🔧 Avarias"
    ])

    # ═══ TAB HORAS ═══════════════════════════════════════════════════
    with tab_horas:
        st.markdown("### Validação de Horas")
        sub_pend, sub_hist = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_pend:
            col1, col2 = st.columns(2)
            with col1:
                filtro = st.selectbox(
                    "Filtrar por", ["Todos","Técnico","Obra"],
                    key="val_filtro"
                )
            with col2:
                estado = st.selectbox(
                    "Estado",
                    ["Todos","🟠 Pendente","🟢 Aprovado","🔵 Faturação","⚪ Faturado"],
                    key="val_estado"
                )

            # Valor do segundo filtro (técnico ou obra específica)
            filtro_valor = None
            if filtro == "Técnico" and not registos_db.empty:
                tecnicos = sorted(registos_db['Técnico'].dropna().unique().tolist())
                filtro_valor = st.selectbox(
                    "Selecionar Técnico",
                    tecnicos,
                    key="val_filtro_tec"
                )
            elif filtro == "Obra" and not registos_db.empty:
                obras = sorted(registos_db['Obra'].dropna().unique().tolist())
                filtro_valor = st.selectbox(
                    "Selecionar Obra",
                    obras,
                    key="val_filtro_obra"
                )

            if not registos_db.empty:
                # ── Fix: formatar Data para string ────────────────
                regs = registos_db.copy()
                if pd.api.types.is_datetime64_any_dtype(regs['Data']):
                    regs['Data'] = regs['Data'].dt.strftime('%d/%m/%Y').fillna('—')
                else:
                    regs['Data'] = regs['Data'].astype(str).replace('NaT', '—').replace('None', '—')

                pendentes = regs[regs['Status'] == "0"].copy()

                # ── Aplicar filtro ────────────────────────────────
                if filtro == "Técnico" and filtro_valor:
                    pendentes = pendentes[pendentes['Técnico'] == filtro_valor]
                elif filtro == "Obra" and filtro_valor:
                    pendentes = pendentes[pendentes['Obra'] == filtro_valor]

                if not pendentes.empty:
                    st.markdown(f"**{len(pendentes)} registo(s) pendente(s)**")
                    cols_show = [c for c in ['Data','Técnico','Obra','Horas_Total'] if c in pendentes.columns]
                    st.dataframe(pendentes[cols_show], use_container_width=True, hide_index=True)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("🟢 Validar Todos", use_container_width=True, key="btn_val_horas"):
                            ids_a_validar = pendentes.index
                            registos_db.loc[ids_a_validar, 'Status'] = "1"
                            save_db(registos_db, "registos.csv")
                            for _, reg in pendentes.iterrows():
                                log_audit(
                                    usuario=st.session_state.user,
                                    acao="APROVAR_HORAS",
                                    tabela="registos.csv",
                                    registro_id=reg.get('ID', f"{reg['Técnico']}_{reg['Data']}"),
                                    detalhes=f"Aprovadas {reg['Horas_Total']}h de {reg['Técnico']} em {reg['Obra']}",
                                    ip=""
                                )
                                criar_notificacao(
                                    destinatario=reg['Técnico'],
                                    titulo="✅ Horas Aprovadas",
                                    mensagem=f"As suas {reg['Horas_Total']}h em {reg['Obra']} foram aprovadas!",
                                    tipo="success", acao_url="/registos"
                                )
                            inv()
                            st.success(f"✅ {len(pendentes)} registos validados!")
                            st.rerun()
                    with col2:
                        if st.button("🔵 Para Faturação", use_container_width=True, key="btn_val_fat"):
                            ids_a_validar = pendentes.index
                            registos_db.loc[ids_a_validar, 'Status'] = "2"
                            save_db(registos_db, "registos.csv")
                            inv()
                            st.success(f"✅ {len(pendentes)} registos enviados para faturação!")
                            st.rerun()
                    with col3:
                        if st.button("❌ Rejeitar Todos", use_container_width=True, key="btn_val_rej"):
                            ids_a_validar = pendentes.index
                            registos_db.loc[ids_a_validar, 'Status'] = "-1"
                            save_db(registos_db, "registos.csv")
                            for _, reg in pendentes.iterrows():
                                criar_notificacao(
                                    destinatario=reg['Técnico'],
                                    titulo="❌ Horas Rejeitadas",
                                    mensagem=f"As suas {reg['Horas_Total']}h em {reg['Obra']} foram rejeitadas.",
                                    tipo="error", acao_url="/registos"
                                )
                            inv()
                            st.error(f"❌ {len(pendentes)} registos rejeitados!")
                            st.rerun()

                    # ── Validação individual por técnico ──────────
                    st.markdown("---")
                    st.markdown("#### ✅ Validar Individualmente")
                    for _, reg in pendentes.iterrows():
                        reg_id = reg.get('ID', f"{reg.get('Técnico','')}_{reg.get('Data','')}")
                        col_i, col_v, col_r = st.columns([4, 1, 1])
                        with col_i:
                            st.markdown(
                                f"<div style='background:#1E293B;border-radius:8px;"
                                f"padding:10px 14px;'>"
                                f"<b style='color:#F1F5F9;'>{reg.get('Técnico','')}</b>"
                                f"<span style='float:right;color:#F59E0B;font-weight:700;'>"
                                f"{reg.get('Horas_Total',0)}h</span><br>"
                                f"<small style='color:#64748B;'>"
                                f"{reg.get('Data','')} · {reg.get('Obra','')} · {reg.get('Frente','')}"
                                f"</small></div>",
                                unsafe_allow_html=True
                            )
                        with col_v:
                            if st.button("✅", key=f"val_ind_{reg_id}",
                                          use_container_width=True,
                                          help="Validar"):
                                registos_db.loc[registos_db['ID'] == reg_id, 'Status'] = "1"
                                save_db(registos_db, "registos.csv")
                                criar_notificacao(
                                    destinatario=reg.get('Técnico',''),
                                    titulo="✅ Horas Aprovadas",
                                    mensagem=f"{reg.get('Horas_Total',0)}h em {reg.get('Obra','')} aprovadas.",
                                    tipo="success", acao_url="/registos"
                                )
                                inv()
                                st.rerun()
                        with col_r:
                            if st.button("❌", key=f"rej_ind_{reg_id}",
                                          use_container_width=True,
                                          help="Rejeitar"):
                                registos_db.loc[registos_db['ID'] == reg_id, 'Status'] = "-1"
                                save_db(registos_db, "registos.csv")
                                criar_notificacao(
                                    destinatario=reg.get('Técnico',''),
                                    titulo="❌ Horas Rejeitadas",
                                    mensagem=f"{reg.get('Horas_Total',0)}h em {reg.get('Obra','')} rejeitadas.",
                                    tipo="error", acao_url="/registos"
                                )
                                inv()
                                st.rerun()
                else:
                    st.success("✅ Sem registos pendentes com este filtro.")
            else:
                st.info("📋 Sem registos de horas.")

        with sub_hist:
            st.markdown("#### 📋 Histórico de Horas")

            # Filtro no histórico
            col_hf1, col_hf2 = st.columns(2)
            with col_hf1:
                hist_filtro_tec = st.selectbox(
                    "Técnico",
                    ["Todos"] + (sorted(registos_db['Técnico'].dropna().unique().tolist())
                                 if not registos_db.empty else []),
                    key="hist_filtro_tec"
                )
            with col_hf2:
                hist_filtro_obra = st.selectbox(
                    "Obra",
                    ["Todas"] + (sorted(registos_db['Obra'].dropna().unique().tolist())
                                 if not registos_db.empty else []),
                    key="hist_filtro_obra"
                )

            if not registos_db.empty:
                regs_h = registos_db.copy()
                # Fix Data
                if pd.api.types.is_datetime64_any_dtype(regs_h['Data']):
                    regs_h['Data'] = regs_h['Data'].dt.strftime('%d/%m/%Y').fillna('—')
                else:
                    regs_h['Data'] = regs_h['Data'].astype(str).replace('NaT','—').replace('None','—')

                hist = regs_h[regs_h['Status'].isin(["1","2","-1"])].copy()

                # Aplicar filtros
                if hist_filtro_tec != "Todos":
                    hist = hist[hist['Técnico'] == hist_filtro_tec]
                if hist_filtro_obra != "Todas":
                    hist = hist[hist['Obra'] == hist_filtro_obra]

                if not hist.empty:
                    hist['Status_Texto'] = hist['Status'].map({
                        "1":"✅ Aprovado",
                        "2":"🔵 Faturação",
                        "-1":"❌ Rejeitado"
                    })
                    cols_show = [c for c in ['Data','Técnico','Obra','Horas_Total','Status_Texto']
                                 if c in hist.columns]
                    st.markdown(f"**{len(hist)} registo(s)**")
                    st.dataframe(hist[cols_show], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico com este filtro.")
            else:
                st.info("📋 Sem registos.")

    # ═══ TAB EPIs ════════════════════════════════════════════════════
    with tab_epis:
        st.markdown("### 🦺 Validação de EPIs")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not req_epi_db.empty:
                if 'Data_Validacao' not in req_epi_db.columns: req_epi_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_epi_db.columns: req_epi_db['Validado_Por']   = ""
                pend = req_epi_db[req_epi_db['Status'] == 'Pendente']
                if 'ID' not in pend.columns:
                    pend = pend.copy(); pend['ID'] = pend.index.astype(str)

                if not pend.empty:
                    st.markdown(f"#### {len(pend)} Pedido(s) Pendente(s)")
                    for idx, ped in pend.iterrows():
                        ped_id = ped.get('ID', f"EPI_{idx}")
                        with st.expander(f"🦺 {ped.get('Item','EPI')} — {ped.get('Solicitante','N/A')} ({ped.get('Obra','N/A')})", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Item:</strong> {ped.get('Item','N/A')} ({ped.get('Tamanho','N/A')})</p>
                                <p><strong>Quantidade:</strong> {ped.get('Quantidade',1)}</p>
                                <p><strong>Data:</strong> {ped.get('Data','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar", key=f"apr_epi_{ped_id}", use_container_width=True):
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_epi_db, "req_epis.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_EPI", tabela="req_epis.csv", registro_id=ped_id, detalhes=f"EPI aprovado: {ped.get('Item')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="✅ EPI Aprovado", mensagem=f"O teu pedido de {ped.get('Item')} foi aprovado!", tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_epi_{ped_id}", use_container_width=True, type="secondary"):
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_epi_db.loc[req_epi_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_epi_db, "req_epis.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_EPI", tabela="req_epis.csv", registro_id=ped_id, detalhes=f"EPI rejeitado: {ped.get('Item')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="❌ EPI Rejeitado", mensagem=f"O teu pedido de {ped.get('Item')} foi rejeitado.", tipo="error", acao_url="/tecnico")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem pedidos de EPI pendentes!")
            else:
                st.info("📋 Sem pedidos de EPI.")

        with sub_h:
            st.markdown("#### 📋 Histórico de EPIs")
            if not req_epi_db.empty:
                if 'Data_Validacao' not in req_epi_db.columns: req_epi_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_epi_db.columns: req_epi_db['Validado_Por']   = ""
                hist = req_epi_db[req_epi_db['Status'].isin(['Aprovado','Rejeitado'])]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Item','Quantidade','Status','Data_Validacao','Validado_Por'] if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")
            else:
                st.info("📋 Sem registos.")

    # ═══ TAB FERRAMENTAS ═════════════════════════════════════════════
    with tab_ferramentas:
        st.markdown("### 🔧 Validação de Ferramentas")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not req_fer_db.empty:
                if 'Data_Validacao' not in req_fer_db.columns: req_fer_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_fer_db.columns: req_fer_db['Validado_Por']   = ""
                pend = req_fer_db[req_fer_db['Status'] == 'Pendente']
                if 'ID' not in pend.columns:
                    pend = pend.copy(); pend['ID'] = pend.index.astype(str)

                if not pend.empty:
                    st.markdown(f"#### {len(pend)} Pedido(s) Pendente(s)")
                    for idx, ped in pend.iterrows():
                        ped_id = ped.get('ID', f"FER_{idx}")
                        with st.expander(f"🔧 {str(ped.get('Descricao','Ferramenta'))[:50]} — {ped.get('Solicitante','N/A')}", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao','N/A')}</p>
                                <p><strong>Urgência:</strong> {ped.get('Urgencia','N/A')}</p>
                                <p><strong>Data:</strong> {ped.get('Data','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            if ped.get('Foto_b64'):
                                try:
                                    st.image(f"data:image/png;base64,{ped['Foto_b64']}", caption="Foto da ferramenta", width=200)
                                except:
                                    st.info("📷 Foto disponível mas não foi possível exibir.")
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar", key=f"apr_fer_{ped_id}", use_container_width=True):
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_fer_db, "req_ferramentas.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_FERRAMENTA", tabela="req_ferramentas.csv", registro_id=ped_id, detalhes=f"Ferramenta aprovada: {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="✅ Ferramenta Aprovada", mensagem="O teu pedido de ferramenta foi aprovado!", tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_fer_{ped_id}", use_container_width=True, type="secondary"):
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_fer_db.loc[req_fer_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_fer_db, "req_ferramentas.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_FERRAMENTA", tabela="req_ferramentas.csv", registro_id=ped_id, detalhes=f"Ferramenta rejeitada: {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="❌ Ferramenta Rejeitada", mensagem="O teu pedido de ferramenta foi rejeitado.", tipo="error", acao_url="/tecnico")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem pedidos de ferramentas pendentes!")
            else:
                st.info("📋 Sem pedidos de ferramentas.")

        with sub_h:
            st.markdown("#### 📋 Histórico de Ferramentas")
            if not req_fer_db.empty:
                if 'Data_Validacao' not in req_fer_db.columns: req_fer_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_fer_db.columns: req_fer_db['Validado_Por']   = ""
                hist = req_fer_db[req_fer_db['Status'].isin(['Aprovado','Rejeitado'])]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Descricao','Urgencia','Status','Data_Validacao','Validado_Por'] if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")
            else:
                st.info("📋 Sem registos.")

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
                if 'ID' not in pend.columns:
                    pend = pend.copy(); pend['ID'] = pend.index.astype(str)

                if not pend.empty:
                    st.markdown(f"#### {len(pend)} Pedido(s) Pendente(s)")
                    for idx, ped in pend.iterrows():
                        ped_id = ped.get('ID', f"MAT_{idx}")
                        with st.expander(f"📦 {str(ped.get('Descricao','Material'))[:50]} — {ped.get('Solicitante','N/A')}", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao','N/A')}</p>
                                <p><strong>Quantidade:</strong> {ped.get('Quantidade',1)}{ped.get('Unidade','')}</p>
                                <p><strong>Urgência:</strong> {ped.get('Urgencia','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar", key=f"apr_mat_{ped_id}", use_container_width=True):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_MATERIAL", tabela="req_materiais.csv", registro_id=ped_id, detalhes=f"Material aprovado: {ped.get('Descricao','')[:30]}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="✅ Material Aprovado", mensagem="O teu pedido de material foi aprovado!", tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_mat_{ped_id}", use_container_width=True, type="secondary"):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_MATERIAL", tabela="req_materiais.csv", registro_id=ped_id, detalhes=f"Material rejeitado: {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="❌ Material Rejeitado", mensagem="O teu pedido de material foi rejeitado.", tipo="error", acao_url="/tecnico")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem pedidos de materiais pendentes!")
            else:
                st.info("📋 Sem pedidos de materiais.")

        with sub_h:
            st.markdown("#### 📋 Histórico de Materiais")
            if not req_mat_db.empty:
                if 'Data_Validacao' not in req_mat_db.columns: req_mat_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_mat_db.columns: req_mat_db['Validado_Por']   = ""
                hist = req_mat_db[
                    (req_mat_db['Status'].isin(['Aprovado','Rejeitado'])) &
                    (req_mat_db.get('Tipo', pd.Series([''] * len(req_mat_db))) != 'Gasóleo')
                ]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Descricao','Quantidade','Unidade','Status','Data_Validacao','Validado_Por'] if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")
            else:
                st.info("📋 Sem registos.")

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
                if 'ID' not in pend_gas.columns:
                    pend_gas = pend_gas.copy(); pend_gas['ID'] = pend_gas.index.astype(str)

                if not pend_gas.empty:
                    st.markdown(f"#### {len(pend_gas)} Registo(s) Pendente(s)")
                    for idx, ped in pend_gas.iterrows():
                        ped_id = ped.get('ID', f"GAS_{idx}")
                        with st.expander(f"⛽ {ped.get('Litros',0)}L — {ped.get('Solicitante','N/A')} ({ped.get('Obra','N/A')})", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Litros:</strong> {ped.get('Litros',0)}L</p>
                                <p><strong>Valor:</strong> €{ped.get('Valor',0)}</p>
                                <p><strong>Data Abastecimento:</strong> {ped.get('Data_Abastecimento','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            if ped.get('Recibo_b64'):
                                recibo_str = str(ped.get('Recibo_b64',''))
                                if recibo_str.startswith('JVBER') or recibo_str.startswith('JVBERi'):
                                    st.info("📄 Recibo em PDF — descarrega para visualizar")
                                else:
                                    try:
                                        st.image(f"data:image/png;base64,{recibo_str}", caption="Recibo", width=300)
                                    except:
                                        st.info("📷 Recibo disponível mas não foi possível exibir.")
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Validar", key=f"apr_gas_{ped_id}", use_container_width=True):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_GASOLEO", tabela="req_materiais.csv", registro_id=ped_id, detalhes=f"Gasóleo validado: {ped.get('Litros')}L de {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="✅ Gasóleo Validado", mensagem=f"O teu registo de {ped.get('Litros')}L foi validado!", tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_gas_{ped_id}", use_container_width=True, type="secondary"):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = st.session_state.user
                                    save_db(req_mat_db, "req_materiais.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_GASOLEO", tabela="req_materiais.csv", registro_id=ped_id, detalhes=f"Gasóleo rejeitado: {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="❌ Gasóleo Rejeitado", mensagem="O teu registo de gasóleo foi rejeitado.", tipo="error", acao_url="/tecnico")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem gasóleos pendentes!")
            else:
                st.info("📋 Sem registos de gasóleo.")

        with sub_h:
            st.markdown("#### 📋 Histórico de Gasóleos")
            if not req_mat_db.empty:
                if 'Data_Validacao' not in req_mat_db.columns: req_mat_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_mat_db.columns: req_mat_db['Validado_Por']   = ""
                hist = req_mat_db[
                    (req_mat_db['Status'].isin(['Aprovado','Rejeitado'])) &
                    (req_mat_db.get('Tipo', pd.Series([''] * len(req_mat_db))) == 'Gasóleo')
                ]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Litros','Valor','Status','Data_Validacao','Validado_Por'] if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")
            else:
                st.info("📋 Sem registos.")

    # ═══ TAB AVARIAS ═════════════════════════════════════════════════
    with tab_avarias:
        st.markdown("### 🔧 Validação de Avarias / Reparações")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not incs_db.empty:
                if 'Data_Validacao' not in incs_db.columns: incs_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in incs_db.columns: incs_db['Validado_Por']   = ""
                pend_av = incs_db[
                    (incs_db['Status'] == 'Pendente') &
                    (incs_db.get('Tipo', pd.Series([''] * len(incs_db))) == 'Avaria')
                ]
                if 'ID' not in pend_av.columns:
                    pend_av = pend_av.copy(); pend_av['ID'] = pend_av.index.astype(str)

                if not pend_av.empty:
                    st.markdown(f"#### {len(pend_av)} Avaria(s) Pendente(s)")
                    for idx, ped in pend_av.iterrows():
                        ped_id = ped.get('ID', f"AVAR_{idx}")
                        cor_u = {"Baixa":"#10B981","Média":"#F59E0B","Alta":"#EF4444","Crítica - Paragem":"#DC2626"}.get(ped.get('Urgencia','Média'),"#6B7280")
                        with st.expander(f"🔧 {str(ped.get('Equipamento','Equipamento'))[:40]} — {ped.get('Solicitante','N/A')}", expanded=True):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;border-left:4px solid {cor_u};">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Equipamento:</strong> {ped.get('Equipamento','N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao','N/A')}</p>
                                <p><strong>Urgência:</strong> <span style="color:{cor_u};font-weight:bold;">{ped.get('Urgencia','N/A')}</span></p>
                                <p><strong>Valor Estimado:</strong> €{ped.get('Valor_Estimado',0)}</p>
                            </div>""", unsafe_allow_html=True)
                            if ped.get('Fatura_b64'):
                                fat_str = str(ped.get('Fatura_b64',''))
                                if fat_str.startswith('JVBER') or fat_str.startswith('JVBERi'):
                                    st.info("📄 Fatura em PDF — descarrega para visualizar")
                                else:
                                    try:
                                        st.image(f"data:image/png;base64,{fat_str}", caption="Fatura/Orçamento", width=300)
                                    except:
                                        st.info("📷 Fatura disponível mas não foi possível exibir.")
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar Reparação", key=f"apr_av_{ped_id}", use_container_width=True):
                                    incs_db.loc[incs_db.index == idx, 'Status']         = 'Aprovado'
                                    incs_db.loc[incs_db.index == idx, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    incs_db.loc[incs_db.index == idx, 'Validado_Por']   = st.session_state.user
                                    save_db(incs_db, "incidentes.csv")
                                    log_audit(usuario=st.session_state.user, acao="APROVAR_AVARIA", tabela="incidentes.csv", registro_id=ped_id, detalhes=f"Avaria aprovada: {ped.get('Equipamento')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="✅ Reparação Aprovada", mensagem=f"A tua reparação de {ped.get('Equipamento')} foi aprovada!", tipo="success", acao_url="/tecnico")
                                    inv(); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"rej_av_{ped_id}", use_container_width=True, type="secondary"):
                                    incs_db.loc[incs_db.index == idx, 'Status']         = 'Rejeitado'
                                    incs_db.loc[incs_db.index == idx, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    incs_db.loc[incs_db.index == idx, 'Validado_Por']   = st.session_state.user
                                    save_db(incs_db, "incidentes.csv")
                                    log_audit(usuario=st.session_state.user, acao="REJEITAR_AVARIA", tabela="incidentes.csv", registro_id=ped_id, detalhes=f"Avaria rejeitada: {ped.get('Solicitante')}", ip="")
                                    criar_notificacao(destinatario=ped.get('Solicitante','N/A'), titulo="❌ Reparação Rejeitada", mensagem="A tua reparação foi rejeitada. Contacta o admin.", tipo="error", acao_url="/tecnico")
                                    inv(); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem avarias pendentes!")
            else:
                st.info("📋 Sem avarias registadas.")

        with sub_h:
            st.markdown("#### 📋 Histórico de Avarias")
            if not incs_db.empty:
                if 'Data_Validacao' not in incs_db.columns: incs_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in incs_db.columns: incs_db['Validado_Por']   = ""
                hist = incs_db[
                    (incs_db['Status'].isin(['Aprovado','Rejeitado'])) &
                    (incs_db.get('Tipo', pd.Series([''] * len(incs_db))) == 'Avaria')
                ]
                if not hist.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Equipamento','Urgencia','Status','Data_Validacao','Validado_Por'] if c in hist.columns]
                    st.dataframe(hist[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico.")
            else:
                st.info("📋 Sem registos.")

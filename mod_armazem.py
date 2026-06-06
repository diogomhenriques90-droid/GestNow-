# mod_armazem.py — fluxo completo + confirmação receção
import streamlit as st
import pandas as pd
from datetime import datetime
from core import save_db, inv, log_audit, criar_notificacao, load_db

# Statuses do fluxo completo:
# Pendente → Aprovado → Enviado → Entregue / Rejeitado

def _load_chefes(users_db=None):
    """Carrega lista de chefes de equipa."""
    try:
        if users_db is not None and not users_db.empty \
           and 'Tipo' in users_db.columns:
            chefes = users_db[
                users_db['Tipo'].isin(['Chefe','Admin','chefe'])
            ]['Nome'].tolist()
            if chefes:
                return chefes
        uf = load_db("usuarios.csv", ["Nome","Tipo"], silent=True)
        if not uf.empty and 'Tipo' in uf.columns:
            return uf[
                uf['Tipo'].isin(['Chefe','Admin','chefe'])
            ]['Nome'].tolist()
    except:
        pass
    return []


def _badge_status(status: str) -> str:
    cores = {
        'Pendente':  ('#F59E0B', '🟠'),
        'Aprovado':  ('#3B82F6', '🔵'),
        'Enviado':   ('#8B5CF6', '🟣'),
        'Entregue':  ('#10B981', '✅'),
        'Rejeitado': ('#EF4444', '❌'),
    }
    cor, ic = cores.get(status, ('#6B7280', '⚪'))
    return (
        f"<span style='background:{cor}22;color:{cor};"
        f"padding:2px 10px;border-radius:12px;"
        f"font-size:0.75rem;font-weight:700;'>"
        f"{ic} {status}</span>"
    )


def render_armazem(req_fer_db, req_mat_db, req_epi_db,
                   incs_db, *extra):
    """Armazém completo: EPIs, Ferramentas, Materiais, Compras,
       Receção (confirmação chefe)."""

    # users_db opcional no extra[0]
    users_db = extra[0] if extra else None

    st.markdown("### 📦 Gestão de Armazém & Validações")

    (tab_epis, tab_ferramentas, tab_materiais,
     tab_rececao, tab_compras) = st.tabs([
        "🦺 EPIs",
        "🔧 Ferramentas",
        "📦 Materiais",
        "📬 Receção / Entrega",
        "🛒 Compras",
    ])

    # ═══ HELPERS COMUNS ══════════════════════════════════════════
    def _aprovar(df, csv, ped_id, tec, item_desc, obra):
        df.loc[df['ID'] == ped_id, 'Status']         = 'Aprovado'
        df.loc[df['ID'] == ped_id, 'Data_Validacao'] = \
            datetime.now().strftime("%d/%m/%Y %H:%M")
        df.loc[df['ID'] == ped_id, 'Validado_Por']   = \
            st.session_state.user
        save_db(df, csv)
        log_audit(
            usuario=st.session_state.user,
            acao=f"APROVAR_{csv.split('.')[0].upper()}",
            tabela=csv, registro_id=ped_id,
            detalhes=f"{item_desc} | {obra}", ip=""
        )
        criar_notificacao(
            destinatario=tec,
            titulo="✅ Pedido Aprovado",
            mensagem=f"O teu pedido de {item_desc} foi aprovado! "
                     f"Será enviado para {obra}.",
            tipo="success", acao_url="/tecnico"
        )
        inv(csv)
        from core import _cached_load_all
        _cached_load_all.clear()
        st.success("✅ Aprovado!"); st.rerun()

    def _rejeitar(df, csv, ped_id, tec, item_desc):
        df.loc[df['ID'] == ped_id, 'Status']         = 'Rejeitado'
        df.loc[df['ID'] == ped_id, 'Data_Validacao'] = \
            datetime.now().strftime("%d/%m/%Y %H:%M")
        df.loc[df['ID'] == ped_id, 'Validado_Por']   = \
            st.session_state.user
        save_db(df, csv)
        criar_notificacao(
            destinatario=tec,
            titulo="❌ Pedido Rejeitado",
            mensagem=f"O teu pedido de {item_desc} foi rejeitado.",
            tipo="error", acao_url="/tecnico"
        )
        inv(csv)
        from core import _cached_load_all
        _cached_load_all.clear()
        st.error("❌ Rejeitado."); st.rerun()

    def _marcar_enviado(df, csv, ped_id, tec, item_desc, obra):
        df.loc[df['ID'] == ped_id, 'Status']        = 'Enviado'
        df.loc[df['ID'] == ped_id, 'Data_Envio']    = \
            datetime.now().strftime("%d/%m/%Y %H:%M")
        df.loc[df['ID'] == ped_id, 'Enviado_Por']   = \
            st.session_state.user
        save_db(df, csv)
        criar_notificacao(
            destinatario=tec,
            titulo="📬 Material Enviado para Obra",
            mensagem=f"{item_desc} enviado para {obra}. "
                     f"Confirma a receção na app.",
            tipo="info", acao_url="/tecnico"
        )
        inv(csv)
        from core import _cached_load_all
        _cached_load_all.clear()
        st.info("📬 Marcado como enviado!"); st.rerun()

    # ═══ TAB EPIs ════════════════════════════════════════════════
    with tab_epis:
        st.markdown("### 🦺 EPIs")
        sub_pend, sub_aprov, sub_hist = st.tabs([
            "🟠 Pendentes", "🔵 Aprovados", "📋 Histórico"
        ])

        with sub_pend:
            if req_epi_db.empty:
                st.info("📋 Sem pedidos."); return
            if 'Data_Validacao' not in req_epi_db.columns:
                req_epi_db['Data_Validacao'] = ""
            if 'Validado_Por' not in req_epi_db.columns:
                req_epi_db['Validado_Por'] = ""

            pend = req_epi_db[req_epi_db['Status'] == 'Pendente']
            if pend.empty:
                st.success("✅ Sem EPIs pendentes!")
            else:
                st.markdown(f"**{len(pend)} pedido(s)**")
                for idx, ped in pend.iterrows():
                    pid = ped.get('ID', f"EPI_{idx}")
                    with st.expander(
                        f"🦺 {ped.get('Item','EPI')} — "
                        f"{ped.get('Solicitante','N/A')} "
                        f"({ped.get('Obra','N/A')})",
                        expanded=True
                    ):
                        st.markdown(
                            f"<div style='background:rgba(255,255,255,0.05);"
                            f"padding:12px;border-radius:8px;'>"
                            f"<p><b>Solicitante:</b> {ped.get('Solicitante','')}</p>"
                            f"<p><b>Obra:</b> {ped.get('Obra','')}</p>"
                            f"<p><b>Item:</b> {ped.get('Item','')} "
                            f"({ped.get('Tamanho','')})</p>"
                            f"<p><b>Qtd:</b> {ped.get('Quantidade',1)}</p>"
                            f"<p><b>Data:</b> {ped.get('Data','')}</p>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        ca, cr = st.columns(2)
                        with ca:
                            if st.button(
                                "✅ Aprovar",
                                key=f"apr_epi_{pid}",
                                use_container_width=True
                            ):
                                _aprovar(
                                    req_epi_db, "req_epis.csv",
                                    pid,
                                    ped.get('Solicitante',''),
                                    ped.get('Item','EPI'),
                                    ped.get('Obra','')
                                )
                        with cr:
                            if st.button(
                                "❌ Rejeitar",
                                key=f"rej_epi_{pid}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                _rejeitar(
                                    req_epi_db, "req_epis.csv",
                                    pid,
                                    ped.get('Solicitante',''),
                                    ped.get('Item','EPI')
                                )

        with sub_aprov:
            aprov = req_epi_db[
                req_epi_db['Status'] == 'Aprovado'
            ] if not req_epi_db.empty else pd.DataFrame()
            if aprov.empty:
                st.info("📋 Sem EPIs aprovados a aguardar envio.")
            else:
                st.info(
                    "📬 Estes EPIs foram aprovados. "
                    "Marca como **Enviado** quando saírem do armazém."
                )
                for _, ped in aprov.iterrows():
                    pid = ped.get('ID','')
                    col_i, col_e = st.columns([5,1])
                    with col_i:
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:10px 14px;"
                            f"margin-bottom:4px;"
                            f"border-left:3px solid #3B82F6;'>"
                            f"<b style='color:#F1F5F9;'>"
                            f"{ped.get('Item','')} × "
                            f"{ped.get('Quantidade',1)}</b>"
                            f"<span style='float:right;color:#64748B;'>"
                            f"{ped.get('Data_Validacao','')}</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"👤 {ped.get('Solicitante','')} · "
                            f"🏗️ {ped.get('Obra','')}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with col_e:
                        if st.button(
                            "📬",
                            key=f"env_epi_{pid}",
                            use_container_width=True,
                            help="Marcar como enviado para obra"
                        ):
                            _marcar_enviado(
                                req_epi_db, "req_epis.csv",
                                pid,
                                ped.get('Solicitante',''),
                                ped.get('Item','EPI'),
                                ped.get('Obra','')
                            )

        with sub_hist:
            if not req_epi_db.empty:
                hist = req_epi_db[
                    req_epi_db['Status'].isin(
                        ['Aprovado','Rejeitado','Enviado','Entregue']
                    )
                ]
                if not hist.empty:
                    cols = [c for c in [
                        'Data','Solicitante','Obra','Item',
                        'Quantidade','Status',
                        'Data_Validacao','Validado_Por'
                    ] if c in hist.columns]
                    st.dataframe(
                        hist[cols],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("📋 Sem histórico.")

    # ═══ TAB FERRAMENTAS ═════════════════════════════════════════
    with tab_ferramentas:
        st.markdown("### 🔧 Ferramentas")
        sub_pf, sub_af, sub_hf = st.tabs([
            "🟠 Pendentes", "🔵 Aprovadas", "📋 Histórico"
        ])

        with sub_pf:
            if req_fer_db.empty:
                st.info("📋 Sem pedidos."); return
            if 'Data_Validacao' not in req_fer_db.columns:
                req_fer_db['Data_Validacao'] = ""
            if 'Validado_Por' not in req_fer_db.columns:
                req_fer_db['Validado_Por'] = ""

            pend_f = req_fer_db[req_fer_db['Status'] == 'Pendente']
            if pend_f.empty:
                st.success("✅ Sem ferramentas pendentes!")
            else:
                st.markdown(f"**{len(pend_f)} pedido(s)**")
                for idx, ped in pend_f.iterrows():
                    pid = ped.get('ID', f"FER_{idx}")
                    with st.expander(
                        f"🔧 {str(ped.get('Descricao',''))[:45]} — "
                        f"{ped.get('Solicitante','N/A')}",
                        expanded=True
                    ):
                        st.markdown(
                            f"<div style='background:rgba(255,255,255,0.05);"
                            f"padding:12px;border-radius:8px;'>"
                            f"<p><b>Solicitante:</b> "
                            f"{ped.get('Solicitante','')}</p>"
                            f"<p><b>Obra:</b> {ped.get('Obra','')}</p>"
                            f"<p><b>Descrição:</b> "
                            f"{ped.get('Descricao','')}</p>"
                            f"<p><b>Urgência:</b> "
                            f"{ped.get('Urgencia','')}</p>"
                            f"<p><b>Data:</b> {ped.get('Data','')}</p>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        if ped.get('Foto_b64'):
                            try:
                                st.image(
                                    f"data:image/png;base64,"
                                    f"{ped['Foto_b64']}",
                                    caption="Foto", width=200
                                )
                            except:
                                pass
                        ca, cr = st.columns(2)
                        with ca:
                            if st.button(
                                "✅ Aprovar",
                                key=f"apr_fer_{pid}",
                                use_container_width=True
                            ):
                                _aprovar(
                                    req_fer_db, "req_ferramentas.csv",
                                    pid,
                                    ped.get('Solicitante',''),
                                    str(ped.get('Descricao',''))[:40],
                                    ped.get('Obra','')
                                )
                        with cr:
                            if st.button(
                                "❌ Rejeitar",
                                key=f"rej_fer_{pid}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                _rejeitar(
                                    req_fer_db, "req_ferramentas.csv",
                                    pid,
                                    ped.get('Solicitante',''),
                                    str(ped.get('Descricao',''))[:40]
                                )

        with sub_af:
            aprov_f = req_fer_db[
                req_fer_db['Status'] == 'Aprovado'
            ] if not req_fer_db.empty else pd.DataFrame()
            if aprov_f.empty:
                st.info("📋 Sem ferramentas aprovadas a aguardar envio.")
            else:
                for _, ped in aprov_f.iterrows():
                    pid = ped.get('ID','')
                    col_i, col_e = st.columns([5,1])
                    with col_i:
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:10px 14px;"
                            f"margin-bottom:4px;"
                            f"border-left:3px solid #3B82F6;'>"
                            f"<b style='color:#F1F5F9;'>"
                            f"{str(ped.get('Descricao',''))[:40]}</b><br>"
                            f"<small style='color:#64748B;'>"
                            f"👤 {ped.get('Solicitante','')} · "
                            f"🏗️ {ped.get('Obra','')}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with col_e:
                        if st.button(
                            "📬",
                            key=f"env_fer_{pid}",
                            use_container_width=True,
                            help="Marcar como enviado"
                        ):
                            _marcar_enviado(
                                req_fer_db, "req_ferramentas.csv",
                                pid,
                                ped.get('Solicitante',''),
                                str(ped.get('Descricao',''))[:40],
                                ped.get('Obra','')
                            )

        with sub_hf:
            if not req_fer_db.empty:
                hist_f = req_fer_db[
                    req_fer_db['Status'].isin(
                        ['Aprovado','Rejeitado','Enviado','Entregue']
                    )
                ]
                if not hist_f.empty:
                    cols_f = [c for c in [
                        'Data','Solicitante','Obra','Descricao',
                        'Urgencia','Status',
                        'Data_Validacao','Validado_Por'
                    ] if c in hist_f.columns]
                    st.dataframe(
                        hist_f[cols_f],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("📋 Sem histórico.")

    # ═══ TAB MATERIAIS ═══════════════════════════════════════════
    with tab_materiais:
        st.markdown("### 📦 Materiais")
        sub_pm, sub_am, sub_hm = st.tabs([
            "🟠 Pendentes", "🔵 Aprovados", "📋 Histórico"
        ])

        with sub_pm:
            if req_mat_db.empty:
                st.info("📋 Sem pedidos."); return
            if 'Data_Validacao' not in req_mat_db.columns:
                req_mat_db['Data_Validacao'] = ""
            if 'Validado_Por' not in req_mat_db.columns:
                req_mat_db['Validado_Por'] = ""

            pend_m = req_mat_db[
                (req_mat_db['Status'] == 'Pendente') &
                (req_mat_db.get(
                    'Tipo',
                    pd.Series([''] * len(req_mat_db))
                ) != 'Gasóleo')
            ]
            if pend_m.empty:
                st.success("✅ Sem materiais pendentes!")
            else:
                st.markdown(f"**{len(pend_m)} pedido(s)**")
                for idx, ped in pend_m.iterrows():
                    pid = ped.get('ID', f"MAT_{idx}")
                    with st.expander(
                        f"📦 {str(ped.get('Descricao',''))[:45]} — "
                        f"{ped.get('Solicitante','N/A')}",
                        expanded=True
                    ):
                        st.markdown(
                            f"<div style='background:rgba(255,255,255,0.05);"
                            f"padding:12px;border-radius:8px;'>"
                            f"<p><b>Solicitante:</b> "
                            f"{ped.get('Solicitante','')}</p>"
                            f"<p><b>Obra:</b> {ped.get('Obra','')}</p>"
                            f"<p><b>Descrição:</b> "
                            f"{ped.get('Descricao','')}</p>"
                            f"<p><b>Quantidade:</b> "
                            f"{ped.get('Quantidade',1)}"
                            f"{ped.get('Unidade','')}</p>"
                            f"<p><b>Urgência:</b> "
                            f"{ped.get('Urgencia','')}</p>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        ca, cr = st.columns(2)
                        with ca:
                            if st.button(
                                "✅ Aprovar",
                                key=f"apr_mat_{pid}",
                                use_container_width=True
                            ):
                                _aprovar(
                                    req_mat_db, "req_materiais.csv",
                                    pid,
                                    ped.get('Solicitante',''),
                                    str(ped.get('Descricao',''))[:40],
                                    ped.get('Obra','')
                                )
                        with cr:
                            if st.button(
                                "❌ Rejeitar",
                                key=f"rej_mat_{pid}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                _rejeitar(
                                    req_mat_db, "req_materiais.csv",
                                    pid,
                                    ped.get('Solicitante',''),
                                    str(ped.get('Descricao',''))[:40]
                                )

        with sub_am:
            aprov_m = req_mat_db[
                (req_mat_db['Status'] == 'Aprovado') &
                (req_mat_db.get(
                    'Tipo',
                    pd.Series([''] * len(req_mat_db))
                ) != 'Gasóleo')
            ] if not req_mat_db.empty else pd.DataFrame()
            if aprov_m.empty:
                st.info("📋 Sem materiais aprovados a aguardar envio.")
            else:
                for _, ped in aprov_m.iterrows():
                    pid = ped.get('ID','')
                    col_i, col_e = st.columns([5,1])
                    with col_i:
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:10px 14px;"
                            f"margin-bottom:4px;"
                            f"border-left:3px solid #3B82F6;'>"
                            f"<b style='color:#F1F5F9;'>"
                            f"{str(ped.get('Descricao',''))[:40]}</b>"
                            f"<span style='float:right;color:#64748B;'>"
                            f"{ped.get('Quantidade','')} "
                            f"{ped.get('Unidade','')}</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"👤 {ped.get('Solicitante','')} · "
                            f"🏗️ {ped.get('Obra','')}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with col_e:
                        if st.button(
                            "📬",
                            key=f"env_mat_{pid}",
                            use_container_width=True,
                            help="Marcar como enviado"
                        ):
                            _marcar_enviado(
                                req_mat_db, "req_materiais.csv",
                                pid,
                                ped.get('Solicitante',''),
                                str(ped.get('Descricao',''))[:40],
                                ped.get('Obra','')
                            )

        with sub_hm:
            if not req_mat_db.empty:
                hist_m = req_mat_db[
                    (req_mat_db['Status'].isin(
                        ['Aprovado','Rejeitado','Enviado','Entregue']
                    )) &
                    (req_mat_db.get(
                        'Tipo',
                        pd.Series([''] * len(req_mat_db))
                    ) != 'Gasóleo')
                ]
                if not hist_m.empty:
                    cols_m = [c for c in [
                        'Data','Solicitante','Obra','Descricao',
                        'Quantidade','Unidade','Status',
                        'Data_Validacao','Validado_Por'
                    ] if c in hist_m.columns]
                    st.dataframe(
                        hist_m[cols_m],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("📋 Sem histórico.")

    # ═══ TAB RECEÇÃO / ENTREGA ════════════════════════════════════
    with tab_rececao:
        st.markdown("### 📬 Receção & Confirmação de Entrega")
        st.info(
            "Aqui o admin regista a confirmação do chefe de equipa "
            "quando o material chega à obra. "
            "O chefe pode também confirmar directamente no seu módulo."
        )

        # Agregar todos os itens com status "Enviado"
        enviados = []

        def _add_enviados(df, tipo):
            if df.empty or 'Status' not in df.columns:
                return
            env = df[df['Status'] == 'Enviado'].copy()
            env['_tipo'] = tipo
            env['_csv']  = {
                'EPI':       'req_epis.csv',
                'Ferramenta':'req_ferramentas.csv',
                'Material':  'req_materiais.csv',
            }.get(tipo,'')
            env['_df_ref'] = tipo  # para referência
            enviados.extend(env.to_dict('records'))

        _add_enviados(req_epi_db,  'EPI')
        _add_enviados(req_fer_db,  'Ferramenta')
        _add_enviados(req_mat_db,  'Material')

        if not enviados:
            st.success(
                "✅ Sem material enviado a aguardar confirmação de receção."
            )
        else:
            st.markdown(
                f"<div style='background:rgba(139,92,246,0.1);"
                f"border:1px solid #8B5CF6;border-radius:8px;"
                f"padding:10px 16px;margin-bottom:12px;'>"
                f"<b style='color:#8B5CF6;'>"
                f"📬 {len(enviados)} item(s) aguardam confirmação "
                f"de receção na obra</b>"
                f"</div>",
                unsafe_allow_html=True
            )

            for item in enviados:
                iid   = item.get('ID','')
                tipo  = item.get('_tipo','')
                csv   = item.get('_csv','')
                desc  = (item.get('Item','') or
                         item.get('Descricao',''))[:40]
                obra  = item.get('Obra','')
                tec   = item.get('Solicitante','')
                qtd   = (str(item.get('Quantidade','')) + ' ' +
                         str(item.get('Unidade','') or
                             item.get('Tamanho',''))).strip()

                with st.expander(
                    f"{tipo}: {desc} → {obra} ({tec})",
                    expanded=True
                ):
                    col_r1, col_r2 = st.columns([3,2])
                    with col_r1:
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:12px;'>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Tipo:</b> {tipo}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Item:</b> {desc}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Quantidade:</b> {qtd}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Obra:</b> {obra}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Solicitante:</b> {tec}</p>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                    with col_r2:
                        # Upload foto de confirmação
                        foto = st.file_uploader(
                            "📸 Foto de confirmação (opcional)",
                            type=["jpg","jpeg","png"],
                            key=f"foto_rec_{iid}",
                            label_visibility="visible"
                        )
                        notas_rec = st.text_input(
                            "Notas",
                            key=f"notas_rec_{iid}",
                            placeholder="Ex: Entregue ao chefe João"
                        )

                        if st.button(
                            "✅ Confirmar Receção",
                            key=f"conf_rec_{iid}",
                            use_container_width=True,
                            type="primary"
                        ):
                            # Atualizar o DF correto
                            foto_b64 = ""
                            if foto:
                                import base64
                                foto_b64 = base64.b64encode(
                                    foto.read()
                                ).decode()

                            for df_ref, csv_ref in [
                                (req_epi_db,  'req_epis.csv'),
                                (req_fer_db,  'req_ferramentas.csv'),
                                (req_mat_db,  'req_materiais.csv'),
                            ]:
                                if not df_ref.empty and \
                                   'ID' in df_ref.columns and \
                                   iid in df_ref['ID'].values:
                                    df_ref.loc[
                                        df_ref['ID']==iid, 'Status'
                                    ] = 'Entregue'
                                    df_ref.loc[
                                        df_ref['ID']==iid,
                                        'Data_Entrega'
                                    ] = datetime.now().strftime(
                                        "%d/%m/%Y %H:%M"
                                    )
                                    df_ref.loc[
                                        df_ref['ID']==iid,
                                        'Entregue_Por'
                                    ] = st.session_state.user
                                    df_ref.loc[
                                        df_ref['ID']==iid,
                                        'Notas_Entrega'
                                    ] = notas_rec
                                    if foto_b64:
                                        df_ref.loc[
                                            df_ref['ID']==iid,
                                            'Foto_Entrega_b64'
                                        ] = foto_b64
                                    save_db(df_ref, csv_ref)
                                    log_audit(
                                        usuario=st.session_state.user,
                                        acao="CONFIRMAR_RECECAO",
                                        tabela=csv_ref,
                                        registro_id=iid,
                                        detalhes=(
                                            f"{desc} | {obra} | "
                                            f"Foto: {'Sim' if foto_b64 else 'Não'}"
                                        ),
                                        ip=""
                                    )
                                    criar_notificacao(
                                        destinatario=tec,
                                        titulo="📦 Material Entregue",
                                        mensagem=(
                                            f"{desc} entregue em "
                                            f"{obra}. "
                                            f"{notas_rec}"
                                        ),
                                        tipo="success",
                                        acao_url="/tecnico"
                                    )
                                    break

                            inv(csv_ref)
                            from core import _cached_load_all
                            _cached_load_all.clear()
                            st.success(
                                f"✅ Receção confirmada: {desc}"
                            )
                            st.rerun()

        # Histórico de entregas
        st.markdown("---")
        st.markdown("#### 📋 Histórico de Entregas")

        entregues = []
        for df_e, tipo_e in [
            (req_epi_db, 'EPI'),
            (req_fer_db, 'Ferramenta'),
            (req_mat_db, 'Material'),
        ]:
            if not df_e.empty and 'Status' in df_e.columns:
                ent = df_e[df_e['Status']=='Entregue'].copy()
                if not ent.empty:
                    ent['_tipo'] = tipo_e
                    entregues.append(ent)

        if entregues:
            df_ent = pd.concat(entregues, ignore_index=True)
            cols_ent = [c for c in [
                '_tipo','Data','Solicitante','Obra',
                'Item','Descricao','Status',
                'Data_Entrega','Entregue_Por'
            ] if c in df_ent.columns]
            df_ent_show = df_ent[cols_ent].rename(
                columns={'_tipo':'Tipo'}
            ).sort_values(
                'Data_Entrega' if 'Data_Entrega' in df_ent.columns
                else 'Data',
                ascending=False
            )
            st.dataframe(
                df_ent_show,
                use_container_width=True,
                hide_index=True
            )

            # Mostrar fotos de confirmação
            fotos_com = [
                r for r in entregues[0].to_dict('records')
                if r.get('Foto_Entrega_b64','')
            ] if entregues else []
            if fotos_com:
                with st.expander("📸 Fotos de Confirmação"):
                    for r in fotos_com[:6]:
                        try:
                            st.image(
                                f"data:image/jpeg;base64,"
                                f"{r['Foto_Entrega_b64']}",
                                caption=(
                                    f"{r.get('Item','') or r.get('Descricao','')} "
                                    f"— {r.get('Obra','')}"
                                ),
                                width=250
                            )
                        except:
                            pass
        else:
            st.info("📋 Sem entregas confirmadas ainda.")

    # ═══ TAB COMPRAS ═════════════════════════════════════════════
    with tab_compras:
        from mod_admin_compras import render_compras
        render_compras()

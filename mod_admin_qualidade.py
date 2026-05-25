# mod_admin_qualidade.py
"""
GESTNOW v3 — mod_admin_qualidade.py
Gestão da Qualidade — não conformidades, ações corretivas,
indicadores, auditorias internas, documentos SGQ
"""
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date, timedelta
from core import save_db, inv, load_db, log_audit, criar_notificacao

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()


def render_qualidade(*_):
    """Módulo de Qualidade."""

    nc_db  = _load("nao_conformidades.csv", [
        "ID","Data","Obra","Reportado_Por","Tipo","Descricao",
        "Gravidade","Status","Causa_Raiz","Acao_Corretiva",
        "Responsavel_AC","Prazo_AC","Data_Fecho","Verificado_Por"
    ])
    docs_sgq = _load("documentos_sgq.csv", [
        "ID","Codigo","Titulo","Revisao","Data_Emissao",
        "Data_Revisao","Tipo","Responsavel","Status","Ficheiro_b64"
    ])
    insp_db = _load("inspecoes_qualidade.csv", [
        "ID","Data","Obra","Tipo_Inspecao","Realizado_Por",
        "Resultado","Obs","Status","Evidencias_b64"
    ])

    obras_db = _load("obras_lista.csv", ["Obra","Ativa"])
    user_nome = st.session_state.get('user','Admin')
    hoje      = date.today()

    st.markdown("### 🎯 Gestão da Qualidade")

    # KPIs
    n_nc_aber = len(nc_db[nc_db['Status'].isin(['Aberta','Em Tratamento'])]) \
                if not nc_db.empty else 0
    n_nc_tot  = len(nc_db) if not nc_db.empty else 0
    n_ac_venc = 0
    if not nc_db.empty and 'Prazo_AC' in nc_db.columns:
        nc2 = nc_db.copy()
        nc2['P_d'] = pd.to_datetime(
            nc2['Prazo_AC'], dayfirst=True, errors='coerce'
        )
        nc_aber = nc2[nc2['Status'].isin(['Aberta','Em Tratamento'])]
        n_ac_venc = len(nc_aber[
            nc_aber['P_d'] < pd.Timestamp(hoje)
        ])
    n_docs = len(docs_sgq) if not docs_sgq.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("🔴 NC Abertas",    n_nc_aber)
    with c2: st.metric("📋 NC Total",      n_nc_tot)
    with c3: st.metric("⚠️ AC Vencidas",   n_ac_venc,
                       delta="🔴 Urgente" if n_ac_venc > 0 else "✅")
    with c4: st.metric("📄 Docs SGQ",      n_docs)

    st.divider()

    tab_nc, tab_nova_nc, tab_insp, tab_docs, tab_kpis = st.tabs([
        "🔴 Não Conformidades",
        "➕ Nova NC",
        "🔍 Inspeções",
        "📄 Docs SGQ",
        "📊 Indicadores",
    ])

    # ════════════════════════════════════════════════════════════════
    # NÃO CONFORMIDADES
    # ════════════════════════════════════════════════════════════════
    with tab_nc:
        st.markdown("#### 🔴 Não Conformidades")

        if nc_db.empty:
            st.success("✅ Sem não conformidades registadas.")
        else:
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                stat_opts = ["Todos","Aberta","Em Tratamento",
                             "Fechada","Verificada"]
                stat_f = st.selectbox("Estado", stat_opts, key="nc_stat_f")
            with col_f2:
                obras_f = ["Todas"] + nc_db['Obra'].dropna().unique().tolist()
                obra_f  = st.selectbox("Obra", obras_f, key="nc_obra_f")
            with col_f3:
                grav_f  = ["Todas","Crítica","Maior","Menor","Observação"]
                grav_sel = st.selectbox("Gravidade", grav_f, key="nc_grav_f")

            df_nc = nc_db.copy()
            if stat_f != "Todos":
                df_nc = df_nc[df_nc['Status'] == stat_f]
            if obra_f != "Todas":
                df_nc = df_nc[df_nc['Obra']   == obra_f]
            if grav_sel != "Todas" and 'Gravidade' in df_nc.columns:
                df_nc = df_nc[df_nc['Gravidade'] == grav_sel]

            for _, nc in df_nc.sort_values('Data',ascending=False).iterrows():
                ncid  = nc.get('ID','')
                grav  = nc.get('Gravidade','')
                stat  = nc.get('Status','')
                cor_g = {
                    'Crítica':    '#DC2626',
                    'Maior':      '#EF4444',
                    'Menor':      '#F59E0B',
                    'Observação': '#3B82F6'
                }.get(grav,'#6B7280')
                cor_s = {
                    'Aberta':        '#EF4444',
                    'Em Tratamento': '#F59E0B',
                    'Fechada':       '#10B981',
                    'Verificada':    '#64748B'
                }.get(stat,'#6B7280')

                # Alerta prazo vencido
                prazo_str = nc.get('Prazo_AC','')
                alerta_pz = ""
                if prazo_str and stat in ['Aberta','Em Tratamento']:
                    try:
                        d_pz = datetime.strptime(prazo_str,"%d/%m/%Y").date()
                        dias = (d_pz - hoje).days
                        if dias < 0:
                            alerta_pz = f" 🔴 AC vencida há {abs(dias)}d!"
                        elif dias <= 5:
                            alerta_pz = f" ⚠️ AC vence em {dias}d"
                    except:
                        pass

                with st.expander(
                    f"[{grav}] {str(nc.get('Descricao',''))[:50]} "
                    f"— {nc.get('Obra','')} | {stat}{alerta_pz}",
                    expanded=(stat == 'Aberta' and grav in ['Crítica','Maior'])
                ):
                    col_nc1, col_nc2 = st.columns([3,1])
                    with col_nc1:

                        causa_txt = ('<p style=color:#F59E0B;margin:2px 0;><b>Causa Raiz:</b> ' + str(nc.get('Causa_Raiz','')) + '</p>') if nc.get('Causa_Raiz') else ''
                        ac_txt    = ('<p style=color:#3B82F6;margin:2px 0;><b>Ação Corretiva:</b> ' + str(nc.get('Acao_Corretiva','')) + '</p>') if nc.get('Acao_Corretiva') else ''
                        prazo_txt = ('<p style=color:#64748B;margin:2px 0;><b>Prazo AC:</b> ' + str(nc.get('Prazo_AC','')) + ' · Resp: ' + str(nc.get('Responsavel_AC','')) + '</p>') if nc.get('Prazo_AC') else ''

                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:12px;"
                            f"border-left:4px solid {cor_g};'>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Data:</b> {nc.get('Data','')} · "
                            f"<b>Obra:</b> {nc.get('Obra','')} · "
                            f"<b>Tipo:</b> {nc.get('Tipo','')}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Reportado por:</b> {nc.get('Reportado_Por','')}</p>"
                            f"<p style='color:#94A388;margin:4px 0;'>"
                            f"{nc.get('Descricao','')}</p>"
                            f"{causa_txt}"
                            f"{ac_txt}"
                            f"{prazo_txt}"
                            f"</div>",
                            unsafe_allow_html=True
                         )   

                    with col_nc2:
                        st.markdown(
                            f"<div style='background:{cor_s}18;"
                            f"border:1px solid {cor_s};"
                            f"border-radius:8px;padding:10px;"
                            f"text-align:center;'>"
                            f"<b style='color:{cor_s};'>{stat}</b><br>"
                            f"<span style='color:{cor_g};"
                            f"font-size:0.8rem;'>{grav}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        # Ação corretiva
                        if stat in ['Aberta','Em Tratamento']:
                            ac_text = st.text_area(
                                "Ação Corretiva",
                                value=nc.get('Acao_Corretiva',''),
                                key=f"nc_ac_{ncid}",
                                height=70
                            )
                            ac_resp = st.text_input(
                                "Responsável AC",
                                value=nc.get('Responsavel_AC',''),
                                key=f"nc_resp_{ncid}"
                            )
                            ac_prazo = st.text_input(
                                "Prazo AC (dd/mm/aaaa)",
                                value=nc.get('Prazo_AC',''),
                                key=f"nc_prazo_{ncid}"
                            )
                            novo_stat_nc = st.selectbox(
                                "Estado",
                                ['Aberta','Em Tratamento',
                                 'Fechada','Verificada'],
                                key=f"nc_st_{ncid}",
                                index=['Aberta','Em Tratamento',
                                       'Fechada','Verificada'].index(stat)
                                      if stat in ['Aberta','Em Tratamento',
                                                  'Fechada','Verificada']
                                      else 0
                            )
                            if st.button(
                                "💾 Guardar",
                                key=f"nc_save_{ncid}",
                                use_container_width=True,
                                type="primary"
                            ):
                                nc_db.loc[nc_db['ID']==ncid,'Acao_Corretiva'] = ac_text
                                nc_db.loc[nc_db['ID']==ncid,'Responsavel_AC'] = ac_resp
                                nc_db.loc[nc_db['ID']==ncid,'Prazo_AC']       = ac_prazo
                                nc_db.loc[nc_db['ID']==ncid,'Status']         = novo_stat_nc
                                if novo_stat_nc == 'Fechada':
                                    nc_db.loc[nc_db['ID']==ncid,'Data_Fecho']    = hoje.strftime("%d/%m/%Y")
                                    nc_db.loc[nc_db['ID']==ncid,'Verificado_Por']= user_nome
                                save_db(nc_db,"nao_conformidades.csv")
                                log_audit(
                                    usuario=user_nome,
                                    acao="ATUALIZAR_NC",
                                    tabela="nao_conformidades.csv",
                                    registro_id=ncid,
                                    detalhes=f"Estado: {novo_stat_nc}",
                                    ip=""
                                )
                                inv("nao_conformidades.csv"); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # NOVA NC
    # ════════════════════════════════════════════════════════════════
    with tab_nova_nc:
        st.markdown("#### ➕ Registar Não Conformidade")

        obras_ativas = obras_db[
            obras_db['Ativa']=='Ativa'
        ]['Obra'].tolist() if not obras_db.empty else []

        with st.form("form_nova_nc"):
            col_nn1, col_nn2 = st.columns(2)
            with col_nn1:
                nn_obra   = st.selectbox(
                    "Obra *",
                    obras_ativas if obras_ativas else ["—"],
                    key="nn_obra"
                )
                nn_tipo   = st.selectbox(
                    "Tipo *",
                    ["Processo","Produto","Segurança","Ambiental",
                     "Documental","Subempreiteiro","Outro"],
                    key="nn_tipo"
                )
                nn_grav   = st.selectbox(
                    "Gravidade *",
                    ["Crítica","Maior","Menor","Observação"],
                    key="nn_grav"
                )
                nn_desc   = st.text_area(
                    "Descrição detalhada *",
                    key="nn_desc",
                    placeholder="Descreve a não conformidade..."
                )
            with col_nn2:
                nn_causa  = st.text_area(
                    "Causa Raiz (se identificada)",
                    key="nn_causa",
                    placeholder="Ex: Procedimento não seguido..."
                )
                nn_ac     = st.text_area(
                    "Ação Corretiva Proposta",
                    key="nn_ac",
                    placeholder="Ex: Rever procedimento..."
                )
                nn_resp_ac= st.text_input(
                    "Responsável AC",
                    key="nn_resp_ac",
                    value=user_nome
                )
                nn_prazo  = st.text_input(
                    "Prazo AC (dd/mm/aaaa)",
                    key="nn_prazo",
                    value=(hoje + timedelta(days=15)).strftime("%d/%m/%Y")
                )

            if st.form_submit_button(
                "💾 Registar NC",
                use_container_width=True,
                type="primary"
            ):
                if not nn_desc.strip():
                    st.error("❌ Descrição obrigatória.")
                else:
                    nova_nc = pd.DataFrame([{
                        "ID":           str(uuid.uuid4())[:8].upper(),
                        "Data":         hoje.strftime("%d/%m/%Y"),
                        "Obra":         nn_obra,
                        "Reportado_Por":user_nome,
                        "Tipo":         nn_tipo,
                        "Descricao":    nn_desc.strip(),
                        "Gravidade":    nn_grav,
                        "Status":       "Aberta",
                        "Causa_Raiz":   nn_causa.strip(),
                        "Acao_Corretiva":nn_ac.strip(),
                        "Responsavel_AC":nn_resp_ac.strip(),
                        "Prazo_AC":     nn_prazo.strip(),
                        "Data_Fecho":   "",
                        "Verificado_Por":""
                    }])
                    upd_nc = pd.concat(
                        [nc_db, nova_nc], ignore_index=True
                    ) if not nc_db.empty else nova_nc
                    save_db(upd_nc,"nao_conformidades.csv")
                    log_audit(
                        usuario=user_nome,
                        acao="CRIAR_NC",
                        tabela="nao_conformidades.csv",
                        registro_id=nova_nc['ID'].iloc[0],
                        detalhes=(
                            f"{nn_grav} | {nn_tipo} | "
                            f"{nn_obra}"
                        ),
                        ip=""
                    )
                    # Notificar responsável AC
                    if nn_resp_ac and nn_resp_ac != user_nome:
                        criar_notificacao(
                            destinatario=nn_resp_ac,
                            titulo=f"🔴 Nova NC [{nn_grav}] — {nn_obra}",
                            mensagem=(
                                f"Foste designado responsável pela "
                                f"ação corretiva. Prazo: {nn_prazo}"
                            ),
                            tipo="error",
                            acao_url="/"
                        )
                    inv("nao_conformidades.csv")
                    st.success("✅ Não conformidade registada!")
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # INSPEÇÕES
    # ════════════════════════════════════════════════════════════════
    with tab_insp:
        st.markdown("#### 🔍 Inspeções de Qualidade")

        col_ic1, col_ic2 = st.columns([1, 2])

        with col_ic1:
            st.markdown("##### ➕ Nova Inspeção")
            obras_ativas2 = obras_db[
                obras_db['Ativa']=='Ativa'
            ]['Obra'].tolist() if not obras_db.empty else []

            with st.form("form_insp"):
                i_obra  = st.selectbox(
                    "Obra *",
                    obras_ativas2 if obras_ativas2 else ["—"],
                    key="i_obra"
                )
                i_tipo  = st.selectbox(
                    "Tipo *",
                    ["Inspeção de Processo","Inspeção de Material",
                     "Inspeção Final","Auditoria Interna",
                     "Verificação de Calibração","Outro"],
                    key="i_tipo"
                )
                i_real  = st.text_input(
                    "Realizado por",
                    value=user_nome, key="i_real"
                )
                i_res   = st.selectbox(
                    "Resultado",
                    ["Conforme","Não Conforme","Condicionado"],
                    key="i_res"
                )
                i_obs   = st.text_area("Observações", key="i_obs")

                if st.form_submit_button(
                    "💾 Registar",
                    use_container_width=True,
                    type="primary"
                ):
                    nova_i = pd.DataFrame([{
                        "ID":           str(uuid.uuid4())[:8].upper(),
                        "Data":         hoje.strftime("%d/%m/%Y"),
                        "Obra":         i_obra,
                        "Tipo_Inspecao":i_tipo,
                        "Realizado_Por":i_real.strip(),
                        "Resultado":    i_res,
                        "Obs":          i_obs.strip(),
                        "Status":       "Fechado",
                        "Evidencias_b64":""
                    }])
                    upd_i = pd.concat(
                        [insp_db, nova_i], ignore_index=True
                    ) if not insp_db.empty else nova_i
                    save_db(upd_i,"inspecoes_qualidade.csv")
                    inv("inspecoes_qualidade.csv")
                    st.success("✅ Inspeção registada!")
                    st.rerun()

        with col_ic2:
            st.markdown("##### 📋 Últimas Inspeções")
            if insp_db.empty:
                st.info("📋 Sem inspeções.")
            else:
                for _, ins in insp_db.sort_values(
                    'Data', ascending=False
                ).head(10).iterrows():
                    res   = ins.get('Resultado','')
                    cor_r = {
                        'Conforme':    '#10B981',
                        'Não Conforme':'#EF4444',
                        'Condicionado':'#F59E0B'
                    }.get(res,'#6B7280')

                    obs_txt = ('<br><small style=color:#94A3B8;>' + str(ins.get('Obs',''))[:60] + '</small>') if ins.get('Obs') else ''
                    
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:8px;padding:10px 14px;"
                        f"margin-bottom:4px;"
                        f"border-left:3px solid {cor_r};'>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:0.85rem;'>"
                        f"{ins.get('Tipo_Inspecao','')[:35]}</b>"
                        f"<span style='float:right;color:{cor_r};"
                        f"font-weight:700;'>{res}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"{ins.get('Data','')} · "
                        f"{ins.get('Obra','')} · "
                        f"{ins.get('Realizado_Por','')}"
                        f"</small>"
                        f"{obs_txt}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

    # ════════════════════════════════════════════════════════════════
    # DOCUMENTOS SGQ
    # ════════════════════════════════════════════════════════════════
    with tab_docs:
        st.markdown("#### 📄 Documentação do SGQ")
        st.info(
            "Registo e controlo dos documentos do Sistema de "
            "Gestão da Qualidade — procedimentos, instruções, "
            "impressos e registos."
        )

        col_dc1, col_dc2 = st.columns([1, 2])

        with col_dc1:
            st.markdown("##### ➕ Novo Documento")
            with st.form("form_doc_sgq"):
                d_cod   = st.text_input(
                    "Código *",
                    key="d_cod",
                    placeholder="Ex: PGQ-001"
                )
                d_tit   = st.text_input("Título *", key="d_tit")
                d_tipo  = st.selectbox(
                    "Tipo",
                    ["Procedimento","Instrução de Trabalho",
                     "Impresso","Registo","Plano","Especificação",
                     "Outro"],
                    key="d_tipo"
                )
                d_rev   = st.text_input(
                    "Revisão", key="d_rev",
                    placeholder="Ex: Rev. A"
                )
                d_resp  = st.text_input(
                    "Responsável",
                    value=user_nome, key="d_resp"
                )
                d_stat  = st.selectbox(
                    "Estado",
                    ["Em vigor","Em revisão","Obsoleto"],
                    key="d_stat"
                )

                if st.form_submit_button(
                    "💾 Guardar",
                    use_container_width=True,
                    type="primary"
                ):
                    if not d_cod.strip() or not d_tit.strip():
                        st.error("❌ Código e título obrigatórios.")
                    else:
                        novo_d = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Codigo":      d_cod.strip(),
                            "Titulo":      d_tit.strip(),
                            "Revisao":     d_rev.strip(),
                            "Data_Emissao":hoje.strftime("%d/%m/%Y"),
                            "Data_Revisao":hoje.strftime("%d/%m/%Y"),
                            "Tipo":        d_tipo,
                            "Responsavel": d_resp.strip(),
                            "Status":      d_stat,
                            "Ficheiro_b64":""
                        }])
                        upd_d = pd.concat(
                            [docs_sgq, novo_d], ignore_index=True
                        ) if not docs_sgq.empty else novo_d
                        save_db(upd_d,"documentos_sgq.csv")
                        inv("documentos_sgq.csv")
                        st.success(
                            f"✅ {d_cod} — {d_tit} adicionado!"
                        )
                        st.rerun()

        with col_dc2:
            st.markdown("##### 📋 Índice de Documentos")
            if docs_sgq.empty:
                st.info("📋 Sem documentos registados.")
            else:
                stat_doc_f = st.selectbox(
                    "Estado",
                    ["Todos","Em vigor","Em revisão","Obsoleto"],
                    key="doc_stat_f"
                )
                tipo_doc_f = st.selectbox(
                    "Tipo",
                    ["Todos","Procedimento","Instrução de Trabalho",
                     "Impresso","Registo","Plano",
                     "Especificação","Outro"],
                    key="doc_tipo_f"
                )
                df_d = docs_sgq.copy()
                if stat_doc_f != "Todos":
                    df_d = df_d[df_d['Status'] == stat_doc_f]
                if tipo_doc_f != "Todos" and 'Tipo' in df_d.columns:
                    df_d = df_d[df_d['Tipo'] == tipo_doc_f]

                cols_d = [c for c in [
                    'Codigo','Titulo','Tipo','Revisao',
                    'Data_Emissao','Responsavel','Status'
                ] if c in df_d.columns]
                st.dataframe(
                    df_d[cols_d],
                    use_container_width=True,
                    hide_index=True
                )

                csv_d = df_d[cols_d].to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    "📥 Exportar Índice",
                    data=csv_d.encode('utf-8-sig'),
                    file_name="indice_sgq.csv",
                    mime="text/csv",
                    key="dl_sgq"
                )

    # ════════════════════════════════════════════════════════════════
    # INDICADORES
    # ════════════════════════════════════════════════════════════════
    with tab_kpis:
        st.markdown("#### 📊 Indicadores de Qualidade")

        import plotly.graph_objects as go

        if nc_db.empty and insp_db.empty:
            st.info("📋 Sem dados suficientes para indicadores.")
        else:
            # NC por gravidade
            if not nc_db.empty and 'Gravidade' in nc_db.columns:
                st.markdown("##### NC por Gravidade")
                grp_g = nc_db.groupby('Gravidade').size().reset_index(
                    name='Count'
                )
                cores_g = {
                    'Crítica':    '#DC2626',
                    'Maior':      '#EF4444',
                    'Menor':      '#F59E0B',
                    'Observação': '#3B82F6'
                }
                fig_g = go.Figure(go.Bar(
                    x=grp_g['Gravidade'],
                    y=grp_g['Count'],
                    marker_color=[
                        cores_g.get(g,'#6B7280')
                        for g in grp_g['Gravidade']
                    ],
                    text=grp_g['Count'],
                    textposition='outside',
                    textfont={'color':'#F1F5F9'}
                ))
                fig_g.update_layout(
                    title={'text':'NCs por Gravidade',
                           'font':{'color':'#F1F5F9'}},
                    height=220,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(30,41,59,0.5)',
                    font={'color':'#F1F5F9'},
                    xaxis={'gridcolor':'#334155',
                           'tickfont':{'color':'#94A3B8'}},
                    yaxis={'gridcolor':'#334155',
                           'tickfont':{'color':'#94A3B8'}},
                    margin=dict(t=40,b=20,l=10,r=10),
                    showlegend=False
                )
                st.plotly_chart(fig_g, use_container_width=True)

            # NC por estado
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                if not nc_db.empty and 'Status' in nc_db.columns:
                    grp_s = nc_db.groupby('Status').size()
                    total_nc = grp_s.sum()
                    for stat_k, cnt_k in grp_s.items():
                        pct_k = round(cnt_k/total_nc*100)
                        cor_k = {
                            'Aberta':        '#EF4444',
                            'Em Tratamento': '#F59E0B',
                            'Fechada':       '#10B981',
                            'Verificada':    '#64748B'
                        }.get(stat_k,'#6B7280')
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:8px 12px;"
                            f"margin-bottom:4px;"
                            f"border-left:3px solid {cor_k};'>"
                            f"<span style='color:{cor_k};"
                            f"font-weight:700;'>{stat_k}</span>"
                            f"<span style='float:right;"
                            f"color:#94A3B8;'>"
                            f"{cnt_k} ({pct_k}%)</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

            with col_k2:
                # Taxa de conformidade nas inspeções
                if not insp_db.empty and 'Resultado' in insp_db.columns:
                    tot_i   = len(insp_db)
                    conf_i  = len(insp_db[
                        insp_db['Resultado'] == 'Conforme'
                    ])
                    taxa_cf = round(conf_i/tot_i*100) if tot_i > 0 else 0
                    cor_cf  = "#10B981" if taxa_cf >= 90 \
                              else "#F59E0B" if taxa_cf >= 70 \
                              else "#EF4444"
                    st.markdown(
                        f"<div style='background:{cor_cf}18;"
                        f"border:2px solid {cor_cf};"
                        f"border-radius:12px;padding:20px;"
                        f"text-align:center;'>"
                        f"<p style='color:#64748B;margin:0 0 4px;'>"
                        f"Taxa de Conformidade</p>"
                        f"<b style='color:{cor_cf};"
                        f"font-size:2.5rem;'>{taxa_cf}%</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"{conf_i}/{tot_i} inspeções conformes"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

                    # NC por obra (top 5)
                    if not nc_db.empty and 'Obra' in nc_db.columns:
                        st.markdown("**NC por Obra (top 5):**")
                        top_o = nc_db.groupby('Obra').size() \
                                     .sort_values(ascending=False) \
                                     .head(5)
                        for obra_k, cnt_o in top_o.items():
                            st.markdown(
                                f"<div style='display:flex;"
                                f"justify-content:space-between;"
                                f"padding:4px 0;"
                                f"border-bottom:1px solid #1E293B;'>"
                                f"<small style='color:#94A3B8;'>"
                                f"{obra_k[:25]}</small>"
                                f"<b style='color:#EF4444;'>"
                                f"{cnt_o}</b></div>",
                                unsafe_allow_html=True
                            )

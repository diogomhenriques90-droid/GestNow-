# mod_admin_compras.py
"""
GESTNOW v3 — mod_admin_compras.py
Gestão de Compras — pedidos, fornecedores, aprovações, histórico
"""
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date
from core import save_db, inv, load_db, log_audit, criar_notificacao

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()


def render_compras(*_):
    """Módulo de Gestão de Compras."""

    # ── Carregar dados ────────────────────────────────────────────
    compras_db = _load("compras.csv", [
        "ID","Data","Solicitante","Obra","Fornecedor","Descricao",
        "Quantidade","Unidade","Valor_Unit","Total","Categoria",
        "Urgencia","Status","Data_Aprovacao","Aprovado_Por",
        "Numero_Fatura","Notas","Fatura_b64"
    ])
    obras_db = _load("obras_lista.csv", ["Obra","Ativa"])

    user_nome = st.session_state.get('user', 'Admin')
    hoje      = date.today()

    st.markdown("### 🛒 Gestão de Compras")

    # ── KPIs ──────────────────────────────────────────────────────
    n_pend  = len(compras_db[compras_db['Status'] == 'Pendente']) \
              if not compras_db.empty else 0
    n_apr   = len(compras_db[compras_db['Status'] == 'Aprovado']) \
              if not compras_db.empty else 0
    val_mes = 0.0
    if not compras_db.empty and 'Data' in compras_db.columns:
        cc = compras_db.copy()
        cc['Data_d'] = pd.to_datetime(cc['Data'], dayfirst=True, errors='coerce')
        cc['Total_N'] = pd.to_numeric(cc.get('Total',0), errors='coerce').fillna(0)
        mask_m = (
            (cc['Data_d'].dt.month == hoje.month) &
            (cc['Data_d'].dt.year  == hoje.year)
        )
        val_mes = cc[mask_m]['Total_N'].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("🟠 Pendentes",    n_pend)
    with c2: st.metric("✅ Aprovadas",     n_apr)
    with c3: st.metric("💰 Valor Mês",    f"€{val_mes:,.2f}")
    with c4: st.metric("📋 Total Registo",len(compras_db) if not compras_db.empty else 0)

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────
    tab_pend, tab_nova, tab_hist, tab_forn = st.tabs([
        "🟠 Pendentes",
        "➕ Nova Compra",
        "📋 Histórico",
        "🏢 Fornecedores",
    ])

    # ════════════════════════════════════════════════════════════════
    # PENDENTES
    # ════════════════════════════════════════════════════════════════
    with tab_pend:
        st.markdown("#### 🟠 Compras Pendentes de Aprovação")

        if compras_db.empty:
            st.info("📋 Sem compras registadas.")
        else:
            pend = compras_db[compras_db['Status'] == 'Pendente'].copy()
            if pend.empty:
                st.success("✅ Sem compras pendentes!")
            else:
                # Filtros
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    obras_pend = ["Todas"] + pend['Obra'].dropna().unique().tolist()
                    obra_filt = st.selectbox("Obra", obras_pend, key="cp_obra_filt")
                with col_f2:
                    cats = ["Todas"] + pend['Categoria'].dropna().unique().tolist() \
                           if 'Categoria' in pend.columns else ["Todas"]
                    cat_filt = st.selectbox("Categoria", cats, key="cp_cat_filt")

                df_p = pend.copy()
                if obra_filt != "Todas":
                    df_p = df_p[df_p['Obra'] == obra_filt]
                if cat_filt != "Todas" and 'Categoria' in df_p.columns:
                    df_p = df_p[df_p['Categoria'] == cat_filt]

                total_pend = pd.to_numeric(
                    df_p.get('Total',0), errors='coerce'
                ).fillna(0).sum()
                st.markdown(
                    f"<div style='background:rgba(245,158,11,0.1);"
                    f"border:1px solid #F59E0B;border-radius:8px;"
                    f"padding:10px 16px;margin-bottom:12px;'>"
                    f"<b style='color:#F59E0B;'>"
                    f"{len(df_p)} compra(s) · Total: €{total_pend:,.2f}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                for _, row in df_p.iterrows():
                    cid    = row.get('ID','')
                    total  = float(row.get('Total',0) or 0)
                    urg    = row.get('Urgencia','Normal')
                    cor_u  = {"Urgente":"#EF4444","Normal":"#F59E0B",
                              "Baixa":"#10B981"}.get(urg,"#6B7280")

                    with st.expander(
                        f"🛒 {str(row.get('Descricao',''))[:45]} — "
                        f"{row.get('Obra','')} · €{total:,.2f}",
                        expanded=(urg == 'Urgente')
                    ):
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            st.markdown(
                                f"<div style='background:#1E293B;"
                                f"border-radius:8px;padding:12px;'>"
                                f"<p style='color:#64748B;font-size:0.75rem;"
                                f"margin:0 0 6px;'>DETALHES</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Solicitante:</b> {row.get('Solicitante','')}</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Obra:</b> {row.get('Obra','')}</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Fornecedor:</b> {row.get('Fornecedor','')}</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Categoria:</b> {row.get('Categoria','')}</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Quantidade:</b> {row.get('Quantidade','')} "
                                f"{row.get('Unidade','')}</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Valor unit.:</b> €{float(row.get('Valor_Unit',0) or 0):,.2f}</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Data:</b> {row.get('Data','')}</p>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with col_d2:
                            st.markdown(
                                f"<div style='background:{cor_u}18;"
                                f"border:1px solid {cor_u};"
                                f"border-radius:8px;padding:12px;"
                                f"text-align:center;'>"
                                f"<p style='color:#64748B;font-size:0.75rem;"
                                f"margin:0 0 4px;'>TOTAL</p>"
                                f"<b style='color:{cor_u};"
                                f"font-size:1.6rem;'>€{total:,.2f}</b><br>"
                                f"<span style='color:{cor_u};"
                                f"font-size:0.8rem;'>Urgência: {urg}</span>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            if row.get('Notas'):
                                st.markdown(
                                    f"<div style='background:#1E293B;"
                                    f"border-radius:6px;padding:8px;"
                                    f"margin-top:8px;'>"
                                    f"<small style='color:#94A3B8;'>"
                                    f"📝 {row.get('Notas','')}</small>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )

                        # Fatura anexada
                        if row.get('Fatura_b64'):
                            fat_str = str(row.get('Fatura_b64',''))
                            if fat_str.startswith('JVBER'):
                                st.info("📄 Fatura PDF anexada")
                            elif len(fat_str) > 100:
                                try:
                                    st.image(
                                        f"data:image/jpeg;base64,{fat_str}",
                                        caption="Fatura", width=250
                                    )
                                except:
                                    pass

                        # Nº fatura para aprovação
                        num_fat_key = f"cp_nfat_{cid}"
                        num_fatura = st.text_input(
                            "Nº Fatura (opcional)",
                            key=num_fat_key,
                            placeholder="Ex: FT 2025/001"
                        )

                        col_a, col_r = st.columns(2)
                        with col_a:
                            if st.button(
                                "✅ Aprovar",
                                key=f"cp_apr_{cid}",
                                use_container_width=True,
                                type="primary"
                            ):
                                compras_db.loc[
                                    compras_db['ID'] == cid, 'Status'
                                ] = 'Aprovado'
                                compras_db.loc[
                                    compras_db['ID'] == cid, 'Data_Aprovacao'
                                ] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                compras_db.loc[
                                    compras_db['ID'] == cid, 'Aprovado_Por'
                                ] = user_nome
                                if num_fatura:
                                    compras_db.loc[
                                        compras_db['ID'] == cid, 'Numero_Fatura'
                                    ] = num_fatura
                                save_db(compras_db, "compras.csv")
                                log_audit(
                                    usuario=user_nome,
                                    acao="APROVAR_COMPRA",
                                    tabela="compras.csv",
                                    registro_id=cid,
                                    detalhes=(
                                        f"{row.get('Descricao','')} | "
                                        f"€{total:,.2f} | "
                                        f"{row.get('Obra','')}"
                                    ),
                                    ip=""
                                )
                                criar_notificacao(
                                    destinatario=row.get('Solicitante',''),
                                    titulo="✅ Compra Aprovada",
                                    mensagem=(
                                        f"A tua compra de "
                                        f"{row.get('Descricao','')} "
                                        f"(€{total:,.2f}) foi aprovada!"
                                    ),
                                    tipo="success",
                                    acao_url="/tecnico"
                                )
                                inv("compras.csv")
                                st.success("✅ Aprovado!")
                                st.rerun()

                        with col_r:
                            motivo_rej = st.text_input(
                                "Motivo rejeição",
                                key=f"cp_motivo_{cid}",
                                placeholder="Opcional",
                                label_visibility="collapsed"
                            )
                            if st.button(
                                "❌ Rejeitar",
                                key=f"cp_rej_{cid}",
                                use_container_width=True
                            ):
                                compras_db.loc[
                                    compras_db['ID'] == cid, 'Status'
                                ] = 'Rejeitado'
                                compras_db.loc[
                                    compras_db['ID'] == cid, 'Data_Aprovacao'
                                ] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                compras_db.loc[
                                    compras_db['ID'] == cid, 'Aprovado_Por'
                                ] = user_nome
                                if motivo_rej:
                                    compras_db.loc[
                                        compras_db['ID'] == cid, 'Notas'
                                    ] = f"Rejeitado: {motivo_rej}"
                                save_db(compras_db, "compras.csv")
                                criar_notificacao(
                                    destinatario=row.get('Solicitante',''),
                                    titulo="❌ Compra Rejeitada",
                                    mensagem=(
                                        f"A tua compra de "
                                        f"{row.get('Descricao','')} "
                                        f"foi rejeitada. "
                                        f"{motivo_rej}"
                                    ),
                                    tipo="error",
                                    acao_url="/tecnico"
                                )
                                inv("compras.csv")
                                st.error("❌ Rejeitado.")
                                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # NOVA COMPRA
    # ════════════════════════════════════════════════════════════════
    with tab_nova:
        st.markdown("#### ➕ Registar Nova Compra")

        obras_ativas = []
        if not obras_db.empty and 'Ativa' in obras_db.columns:
            obras_ativas = obras_db[
                obras_db['Ativa'] == 'Ativa'
            ]['Obra'].tolist()

        with st.form("form_nova_compra"):
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                nc_obra = st.selectbox(
                    "Obra *",
                    obras_ativas if obras_ativas else ["—"],
                    key="nc_obra"
                )
                nc_desc = st.text_area(
                    "Descrição *",
                    key="nc_compra_desc",
                    placeholder="Ex: Cabo XLR 10m × 5 un."
                )
                nc_forn = st.text_input(
                    "Fornecedor",
                    key="nc_forn",
                    placeholder="Ex: Würth, Amazon, etc."
                )
                nc_cat = st.selectbox(
                    "Categoria",
                    ["Materiais","Ferramentas","EPIs","Consumíveis",
                     "Equipamento","Serviços","Outro"],
                    key="nc_cat"
                )
            with col_n2:
                nc_qtd = st.number_input(
                    "Quantidade *",
                    min_value=0.0, value=1.0, step=1.0,
                    key="nc_qtd"
                )
                nc_uni = st.selectbox(
                    "Unidade",
                    ["un","m","kg","L","cx","par","lote"],
                    key="nc_uni"
                )
                nc_vunit = st.number_input(
                    "Valor Unit. (€)",
                    min_value=0.0, step=0.50,
                    key="nc_vunit"
                )
                nc_urg = st.selectbox(
                    "Urgência",
                    ["Normal","Urgente","Baixa"],
                    key="nc_urg"
                )
                nc_notas = st.text_area(
                    "Notas",
                    key="nc_notas",
                    placeholder="Informação adicional..."
                )

            nc_total = round(nc_qtd * nc_vunit, 2)
            if nc_total > 0:
                st.info(f"💰 Total calculado: **€{nc_total:,.2f}**")

            nc_fatura = st.file_uploader(
                "Anexar Fatura/Orçamento (opcional)",
                type=["jpg","jpeg","png","pdf"],
                key="nc_fatura"
            )

            submitted = st.form_submit_button(
                "💾 Registar Compra",
                use_container_width=True,
                type="primary"
            )

            if submitted:
                if not nc_desc.strip() or nc_qtd <= 0:
                    st.error("❌ Descrição e quantidade obrigatórias.")
                else:
                    # Processar fatura
                    fatura_b64 = ""
                    if nc_fatura:
                        import base64
                        fatura_b64 = base64.b64encode(
                            nc_fatura.read()
                        ).decode()

                    nova = pd.DataFrame([{
                        "ID":           str(uuid.uuid4())[:8].upper(),
                        "Data":         hoje.strftime("%d/%m/%Y"),
                        "Solicitante":  user_nome,
                        "Obra":         nc_obra,
                        "Fornecedor":   nc_forn.strip(),
                        "Descricao":    nc_desc.strip(),
                        "Quantidade":   nc_qtd,
                        "Unidade":      nc_uni,
                        "Valor_Unit":   nc_vunit,
                        "Total":        nc_total,
                        "Categoria":    nc_cat,
                        "Urgencia":     nc_urg,
                        "Status":       "Pendente",
                        "Data_Aprovacao":"",
                        "Aprovado_Por": "",
                        "Numero_Fatura":"",
                        "Notas":        nc_notas.strip(),
                        "Fatura_b64":   fatura_b64
                    }])
                    upd = pd.concat(
                        [compras_db, nova], ignore_index=True
                    ) if not compras_db.empty else nova
                    save_db(upd, "compras.csv")
                    log_audit(
                        usuario=user_nome,
                        acao="CRIAR_COMPRA",
                        tabela="compras.csv",
                        registro_id=nova['ID'].iloc[0],
                        detalhes=(
                            f"{nc_desc[:50]} | "
                            f"€{nc_total:,.2f} | {nc_obra}"
                        ),
                        ip=""
                    )
                    inv("compras.csv")
                    st.success(
                        f"✅ Compra registada! "
                        f"Total: €{nc_total:,.2f}"
                    )
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # HISTÓRICO
    # ════════════════════════════════════════════════════════════════
    with tab_hist:
        st.markdown("#### 📋 Histórico de Compras")

        if compras_db.empty:
            st.info("📋 Sem compras registadas.")
        else:
            col_hf1, col_hf2, col_hf3 = st.columns(3)
            with col_hf1:
                obras_h = ["Todas"] + compras_db['Obra'].dropna().unique().tolist()
                obra_h  = st.selectbox("Obra", obras_h, key="ch_obra")
            with col_hf2:
                stats_h = ["Todos","Pendente","Aprovado","Rejeitado"]
                stat_h  = st.selectbox("Estado", stats_h, key="ch_stat")
            with col_hf3:
                cats_h  = ["Todas"] + compras_db['Categoria'].dropna().unique().tolist() \
                          if 'Categoria' in compras_db.columns else ["Todas"]
                cat_h   = st.selectbox("Categoria", cats_h, key="ch_cat")

            df_h = compras_db.copy()
            if obra_h != "Todas":
                df_h = df_h[df_h['Obra'] == obra_h]
            if stat_h != "Todos" and 'Status' in df_h.columns:
                df_h = df_h[df_h['Status'] == stat_h]
            if cat_h != "Todas" and 'Categoria' in df_h.columns:
                df_h = df_h[df_h['Categoria'] == cat_h]

            if not df_h.empty:
                df_h['Total_N'] = pd.to_numeric(
                    df_h.get('Total',0), errors='coerce'
                ).fillna(0)
                total_h = df_h['Total_N'].sum()

                col_km1, col_km2 = st.columns(2)
                with col_km1: st.metric("📋 Compras",  len(df_h))
                with col_km2: st.metric("💰 Total",    f"€{total_h:,.2f}")

                cols_show = [c for c in [
                    'Data','Solicitante','Obra','Fornecedor',
                    'Descricao','Quantidade','Unidade',
                    'Total','Categoria','Status','Aprovado_Por'
                ] if c in df_h.columns]
                st.dataframe(
                    df_h[cols_show].sort_values('Data', ascending=False),
                    use_container_width=True, hide_index=True
                )

                csv_h = df_h[cols_show].to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    "📥 Exportar CSV",
                    data=csv_h.encode('utf-8-sig'),
                    file_name=f"compras_{hoje.strftime('%Y%m')}.csv",
                    mime="text/csv",
                    key="dl_compras_hist"
                )

                # Gráfico por categoria
                if len(df_h) > 1:
                    import plotly.graph_objects as go
                    grp = df_h.groupby('Categoria')['Total_N'].sum().reset_index() \
                          if 'Categoria' in df_h.columns \
                          else pd.DataFrame()
                    if not grp.empty:
                        fig = go.Figure(go.Pie(
                            labels=grp['Categoria'],
                            values=grp['Total_N'],
                            hole=0.4,
                            marker={'colors':['#3B82F6','#10B981','#F59E0B',
                                              '#EF4444','#8B5CF6','#06B6D4','#F97316'],
                                    'line':{'color':'#0F172A','width':2}},
                            textfont={'color':'#F1F5F9','size':11}
                        ))
                        fig.update_layout(
                            title={'text':'Compras por Categoria',
                                   'font':{'color':'#F1F5F9'}},
                            height=260,
                            paper_bgcolor='rgba(0,0,0,0)',
                            font={'color':'#F1F5F9'},
                            legend={'font':{'color':'#94A3B8'}},
                            margin=dict(t=40,b=10,l=10,r=10)
                        )
                        st.plotly_chart(fig)
            else:
                st.info("📋 Sem compras com este filtro.")

    # ════════════════════════════════════════════════════════════════
    # FORNECEDORES
    # ════════════════════════════════════════════════════════════════
    with tab_forn:
        st.markdown("#### 🏢 Fornecedores Habituais")

        forn_db = _load("fornecedores_compras.csv", [
            "ID","Nome","NIF","Email","Telefone",
            "Categoria","Prazo_Entrega","Notas","Ativo"
        ])

        col_fc1, col_fc2 = st.columns([1, 2])

        with col_fc1:
            st.markdown("##### ➕ Novo Fornecedor")
            with st.form("form_forn"):
                f_nome  = st.text_input("Nome *",      key="f_nome")
                f_nif   = st.text_input("NIF",         key="f_nif")
                f_email = st.text_input("Email",       key="f_email")
                f_tel   = st.text_input("Telefone",    key="f_tel")
                f_cat   = st.selectbox(
                    "Categoria",
                    ["Materiais","Ferramentas","EPIs",
                     "Equipamento","Serviços","Geral"],
                    key="f_cat"
                )
                f_prazo = st.text_input(
                    "Prazo Entrega",
                    key="f_prazo",
                    placeholder="Ex: 2-3 dias úteis"
                )
                f_notas = st.text_area("Notas", key="f_notas")

                if st.form_submit_button(
                    "💾 Guardar",
                    use_container_width=True,
                    type="primary"
                ):
                    if not f_nome.strip():
                        st.error("❌ Nome obrigatório.")
                    else:
                        novo_f = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Nome":         f_nome.strip(),
                            "NIF":          f_nif.strip(),
                            "Email":        f_email.strip(),
                            "Telefone":     f_tel.strip(),
                            "Categoria":    f_cat,
                            "Prazo_Entrega":f_prazo.strip(),
                            "Notas":        f_notas.strip(),
                            "Ativo":        "Sim"
                        }])
                        upd_f = pd.concat(
                            [forn_db, novo_f], ignore_index=True
                        ) if not forn_db.empty else novo_f
                        save_db(upd_f, "fornecedores_compras.csv")
                        inv("fornecedores_compras.csv")
                        st.success(f"✅ {f_nome} adicionado!")
                        st.rerun()

        with col_fc2:
            st.markdown("##### 📋 Lista de Fornecedores")
            if forn_db.empty:
                st.info(
                    "📋 Sem fornecedores registados. "
                    "Adiciona os teus fornecedores habituais."
                )
            else:
                cols_f = [c for c in [
                    'Nome','NIF','Email','Telefone',
                    'Categoria','Prazo_Entrega','Ativo'
                ] if c in forn_db.columns]
                st.dataframe(
                    forn_db[cols_f],
                    use_container_width=True,
                    hide_index=True
                )

                # Análise por fornecedor
                if not compras_db.empty and 'Fornecedor' in compras_db.columns:
                    st.markdown("---")
                    st.markdown("##### 📊 Volume por Fornecedor")
                    cc2 = compras_db.copy()
                    cc2['Total_N'] = pd.to_numeric(
                        cc2.get('Total',0), errors='coerce'
                    ).fillna(0)
                    top_forn = cc2.groupby('Fornecedor')['Total_N'].sum() \
                                  .sort_values(ascending=False) \
                                  .head(8)
                    if not top_forn.empty:
                        import plotly.graph_objects as go
                        fig_f = go.Figure(go.Bar(
                            x=top_forn.values,
                            y=top_forn.index.tolist(),
                            orientation='h',
                            marker_color='#3B82F6',
                            text=[f"€{v:,.0f}" for v in top_forn.values],
                            textposition='outside',
                            textfont={'color':'#F1F5F9','size':10}
                        ))
                        fig_f.update_layout(
                            title={'text':'Top Fornecedores',
                                   'font':{'color':'#F1F5F9'}},
                            height=max(200, len(top_forn)*40+80),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(30,41,59,0.5)',
                            font={'color':'#F1F5F9'},
                            xaxis={'gridcolor':'#334155',
                                   'tickfont':{'color':'#94A3B8'},
                                   'tickprefix':'€'},
                            yaxis={'gridcolor':'#334155',
                                   'tickfont':{'color':'#94A3B8'}},
                            margin=dict(t=40,b=20,l=10,r=60),
                            showlegend=False
                        )
                        st.plotly_chart(fig_f)

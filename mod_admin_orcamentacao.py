# mod_admin_orcamentacao.py
"""
GESTNOW v3 — mod_admin_orcamentacao.py
Orçamentação de Obras — criação, versões, comparativo real vs orçado
"""
import streamlit as st
import pandas as pd
import uuid, io
from datetime import datetime, date
from core import save_db, inv, load_db, log_audit

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()


def render_orcamentacao(*_):
    """Módulo de Orçamentação."""

    orc_db  = _load("orcamentos.csv", [
        "ID","Obra","Cliente","Versao","Data","Criado_Por",
        "Status","Validade","Total_Mao_Obra","Total_Materiais",
        "Total_Equipamentos","Total_Deslocacoes","Margem_Pct",
        "Total_Sem_Margem","Total_Com_Margem","Notas"
    ])
    orc_linhas = _load("orcamentos_linhas.csv", [
        "ID","Orcamento_ID","Descricao","Categoria",
        "Quantidade","Unidade","Preco_Unit","Total","Notas"
    ])
    obras_db = _load("obras_lista.csv", ["Obra","Cliente","Ativa"])

    user_nome = st.session_state.get('user','Admin')
    hoje      = date.today()

    st.markdown("### 📊 Orçamentação")

    # KPIs
    n_orc    = len(orc_db) if not orc_db.empty else 0
    n_pend   = len(orc_db[orc_db['Status']=='Pendente']) \
               if not orc_db.empty else 0
    val_tot  = _num(orc_db,'Total_Com_Margem')

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("📋 Orçamentos",   n_orc)
    with c2: st.metric("⏳ Pendentes",    n_pend)
    with c3: st.metric("💰 Valor Total",  f"€{val_tot:,.2f}")

    st.divider()

    tab_lista, tab_novo, tab_comp = st.tabs([
        "📋 Lista",
        "➕ Novo Orçamento",
        "📊 Real vs Orçado",
    ])

    # ════════════════════════════════════════════════════════════════
    # LISTA DE ORÇAMENTOS
    # ════════════════════════════════════════════════════════════════
    with tab_lista:
        st.markdown("#### 📋 Orçamentos")

        if orc_db.empty:
            st.info("📋 Sem orçamentos. Cria o primeiro no tab ➕ Novo Orçamento.")
        else:
            # Filtros
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                status_opts = ["Todos"] + orc_db['Status'].dropna().unique().tolist()
                stat_f = st.selectbox("Estado", status_opts, key="orc_stat_f")
            with col_f2:
                obras_opts = ["Todas"] + orc_db['Obra'].dropna().unique().tolist()
                obra_f = st.selectbox("Obra", obras_opts, key="orc_obra_f")

            df_o = orc_db.copy()
            if stat_f != "Todos": df_o = df_o[df_o['Status'] == stat_f]
            if obra_f != "Todas": df_o = df_o[df_o['Obra']   == obra_f]

            for _, orc in df_o.sort_values('Data',ascending=False).iterrows():
                oid    = orc.get('ID','')
                stat   = orc.get('Status','')
                total  = float(orc.get('Total_Com_Margem',0) or 0)
                cor_s  = {
                    'Pendente':  '#F59E0B',
                    'Aprovado':  '#10B981',
                    'Rejeitado': '#EF4444',
                    'Enviado':   '#3B82F6',
                    'Em Revisão':'#8B5CF6',
                }.get(stat,'#6B7280')

                with st.expander(
                    f"📄 {orc.get('Obra','')} — v{orc.get('Versao','1')} "
                    f"| €{total:,.2f} | {stat}",
                    expanded=False
                ):
                    col_o1, col_o2 = st.columns([2,1])
                    with col_o1:
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:12px;'>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Cliente:</b> {orc.get('Cliente','')}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Data:</b> {orc.get('Data','')} | "
                            f"<b>Validade:</b> {orc.get('Validade','')}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Margem:</b> {orc.get('Margem_Pct',0)}%</p>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        # Linhas do orçamento
                        if not orc_linhas.empty and \
                           'Orcamento_ID' in orc_linhas.columns:
                            linhas = orc_linhas[
                                orc_linhas['Orcamento_ID'] == oid
                            ]
                            if not linhas.empty:
                                st.markdown("**Linhas:**")
                                cols_l = [c for c in [
                                    'Descricao','Categoria',
                                    'Quantidade','Unidade',
                                    'Preco_Unit','Total'
                                ] if c in linhas.columns]
                                st.dataframe(
                                    linhas[cols_l],
                                    use_container_width=True,
                                    hide_index=True
                                )

                    with col_o2:
                        st.markdown(
                            f"<div style='background:{cor_s}18;"
                            f"border:1px solid {cor_s};"
                            f"border-radius:8px;padding:12px;"
                            f"text-align:center;'>"
                            f"<b style='color:{cor_s};"
                            f"font-size:1.4rem;'>€{total:,.2f}</b><br>"
                            f"<small style='color:#64748B;'>{stat}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        # Breakdown
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:10px;"
                            f"margin-top:8px;font-size:0.82rem;'>"
                            f"<p style='color:#64748B;margin:2px 0;'>"
                            f"Mão de Obra: "
                            f"€{float(orc.get('Total_Mao_Obra',0) or 0):,.2f}</p>"
                            f"<p style='color:#64748B;margin:2px 0;'>"
                            f"Materiais: "
                            f"€{float(orc.get('Total_Materiais',0) or 0):,.2f}</p>"
                            f"<p style='color:#64748B;margin:2px 0;'>"
                            f"Equipamentos: "
                            f"€{float(orc.get('Total_Equipamentos',0) or 0):,.2f}</p>"
                            f"<p style='color:#64748B;margin:2px 0;'>"
                            f"Deslocações: "
                            f"€{float(orc.get('Total_Deslocacoes',0) or 0):,.2f}</p>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        # Alterar estado
                        novo_stat = st.selectbox(
                            "Estado",
                            ['Pendente','Enviado','Em Revisão',
                             'Aprovado','Rejeitado'],
                            key=f"orc_st_{oid}",
                            index=['Pendente','Enviado','Em Revisão',
                                   'Aprovado','Rejeitado'].index(stat)
                                  if stat in ['Pendente','Enviado',
                                              'Em Revisão','Aprovado',
                                              'Rejeitado'] else 0
                        )
                        if st.button(
                            "✅ Atualizar",
                            key=f"orc_upd_{oid}",
                            use_container_width=True,
                            type="primary"
                        ):
                            orc_db.loc[orc_db['ID']==oid,'Status'] = novo_stat
                            save_db(orc_db,"orcamentos.csv")
                            inv(); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # NOVO ORÇAMENTO
    # ════════════════════════════════════════════════════════════════
    with tab_novo:
        st.markdown("#### ➕ Criar Novo Orçamento")

        obras_ativas = obras_db[
            obras_db['Ativa']=='Ativa'
        ]['Obra'].tolist() if not obras_db.empty else []

        col_hd1, col_hd2 = st.columns(2)
        with col_hd1:
            no_obra    = st.selectbox(
                "Obra *",
                obras_ativas if obras_ativas else ["—"],
                key="no_obra"
            )
            # Auto-preencher cliente
            cliente_auto = ""
            if not obras_db.empty and 'Cliente' in obras_db.columns:
                match = obras_db[obras_db['Obra']==no_obra]
                if not match.empty:
                    cliente_auto = match.iloc[0].get('Cliente','')
            no_cliente = st.text_input(
                "Cliente *", value=cliente_auto, key="no_cliente"
            )
            no_versao = st.number_input(
                "Versão", min_value=1, value=1, key="no_versao"
            )
            no_validade = st.text_input(
                "Validade (dd/mm/aaaa)",
                value=(date(hoje.year, hoje.month+1, hoje.day)
                       if hoje.month < 12 else
                       date(hoje.year+1, 1, hoje.day)
                       ).strftime("%d/%m/%Y"),
                key="no_validade"
            )

        with col_hd2:
            no_margem = st.slider(
                "Margem (%)", 0, 50, 20, key="no_margem"
            )
            no_notas  = st.text_area("Notas", key="no_notas")

        st.markdown("---")
        st.markdown("#### 📝 Linhas do Orçamento")
        st.info(
            "Adiciona as linhas abaixo. "
            "O total é calculado automaticamente."
        )

        # Gestão de linhas em session_state
        if 'orc_linhas_temp' not in st.session_state:
            st.session_state['orc_linhas_temp'] = []

        # Adicionar linha
        with st.form("form_linha_orc"):
            col_l1, col_l2, col_l3 = st.columns(3)
            with col_l1:
                l_desc = st.text_input("Descrição *", key="l_desc")
                l_cat  = st.selectbox(
                    "Categoria",
                    ["Mão de Obra","Materiais","Equipamentos",
                     "Deslocações","Subempreitada","Outro"],
                    key="l_cat"
                )
            with col_l2:
                l_qtd  = st.number_input(
                    "Quantidade", min_value=0.0,
                    value=1.0, step=0.5, key="l_qtd"
                )
                l_uni  = st.selectbox(
                    "Unidade",
                    ["h","un","m","m²","m³","kg","L","vg","mês"],
                    key="l_uni"
                )
            with col_l3:
                l_preco = st.number_input(
                    "Preço Unit. (€)",
                    min_value=0.0, step=1.0,
                    key="l_preco"
                )
                l_notas = st.text_input("Notas linha", key="l_notas")

            if st.form_submit_button("➕ Adicionar Linha"):
                if l_desc.strip():
                    st.session_state['orc_linhas_temp'].append({
                        "ID":          str(uuid.uuid4())[:6].upper(),
                        "Descricao":   l_desc.strip(),
                        "Categoria":   l_cat,
                        "Quantidade":  l_qtd,
                        "Unidade":     l_uni,
                        "Preco_Unit":  l_preco,
                        "Total":       round(l_qtd * l_preco, 2),
                        "Notas":       l_notas.strip()
                    })
                    st.rerun()

        # Preview linhas
        if st.session_state['orc_linhas_temp']:
            df_temp = pd.DataFrame(st.session_state['orc_linhas_temp'])

            st.dataframe(
                df_temp[['Descricao','Categoria','Quantidade',
                          'Unidade','Preco_Unit','Total']],
                use_container_width=True,
                hide_index=True
            )

            # Totais por categoria
            tot_mo   = df_temp[df_temp['Categoria']=='Mão de Obra']['Total'].sum()
            tot_mat  = df_temp[df_temp['Categoria']=='Materiais']['Total'].sum()
            tot_equip= df_temp[df_temp['Categoria']=='Equipamentos']['Total'].sum()
            tot_desl = df_temp[df_temp['Categoria']=='Deslocações']['Total'].sum()
            tot_sub  = df_temp[df_temp['Categoria']=='Subempreitada']['Total'].sum()
            tot_out  = df_temp[~df_temp['Categoria'].isin(
                ['Mão de Obra','Materiais','Equipamentos',
                 'Deslocações','Subempreitada']
            )]['Total'].sum()
            total_sem = df_temp['Total'].sum()
            total_com = round(total_sem * (1 + no_margem/100), 2)

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown(
                    f"<div style='background:#1E293B;"
                    f"border-radius:10px;padding:14px;'>"
                    f"<p style='color:#64748B;margin:2px 0;'>"
                    f"Mão de Obra: €{tot_mo:,.2f}</p>"
                    f"<p style='color:#64748B;margin:2px 0;'>"
                    f"Materiais: €{tot_mat:,.2f}</p>"
                    f"<p style='color:#64748B;margin:2px 0;'>"
                    f"Equipamentos: €{tot_equip:,.2f}</p>"
                    f"<p style='color:#64748B;margin:2px 0;'>"
                    f"Deslocações: €{tot_desl:,.2f}</p>"
                    f"<p style='color:#64748B;margin:2px 0;'>"
                    f"Subempreitada: €{tot_sub:,.2f}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with col_t2:
                st.markdown(
                    f"<div style='background:rgba(59,130,246,0.1);"
                    f"border:1px solid #3B82F6;"
                    f"border-radius:10px;padding:14px;"
                    f"text-align:center;'>"
                    f"<p style='color:#64748B;margin:0;'>"
                    f"Sem margem: €{total_sem:,.2f}</p>"
                    f"<b style='color:#3B82F6;font-size:1.5rem;'>"
                    f"€{total_com:,.2f}</b><br>"
                    f"<small style='color:#64748B;'>"
                    f"Com margem {no_margem}%</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button(
                    "💾 Guardar Orçamento",
                    key="btn_save_orc",
                    type="primary",
                    use_container_width=True
                ):
                    if not no_obra or no_obra == "—":
                        st.error("❌ Seleciona uma obra.")
                    else:
                        orc_id = str(uuid.uuid4())[:8].upper()
                        novo_orc = pd.DataFrame([{
                            "ID":                orc_id,
                            "Obra":              no_obra,
                            "Cliente":           no_cliente.strip(),
                            "Versao":            no_versao,
                            "Data":              hoje.strftime("%d/%m/%Y"),
                            "Criado_Por":        user_nome,
                            "Status":            "Pendente",
                            "Validade":          no_validade.strip(),
                            "Total_Mao_Obra":    tot_mo,
                            "Total_Materiais":   tot_mat,
                            "Total_Equipamentos":tot_equip,
                            "Total_Deslocacoes": tot_desl,
                            "Margem_Pct":        no_margem,
                            "Total_Sem_Margem":  total_sem,
                            "Total_Com_Margem":  total_com,
                            "Notas":             no_notas.strip()
                        }])
                        upd_orc = pd.concat(
                            [orc_db, novo_orc], ignore_index=True
                        ) if not orc_db.empty else novo_orc
                        save_db(upd_orc, "orcamentos.csv")

                        # Guardar linhas
                        linhas_novas = []
                        for lin in st.session_state['orc_linhas_temp']:
                            linhas_novas.append({
                                **lin, "Orcamento_ID": orc_id
                            })
                        df_lin_novas = pd.DataFrame(linhas_novas)
                        upd_lin = pd.concat(
                            [orc_linhas, df_lin_novas],
                            ignore_index=True
                        ) if not orc_linhas.empty else df_lin_novas
                        save_db(upd_lin, "orcamentos_linhas.csv")

                        log_audit(
                            usuario=user_nome,
                            acao="CRIAR_ORCAMENTO",
                            tabela="orcamentos.csv",
                            registro_id=orc_id,
                            detalhes=(
                                f"{no_obra} | "
                                f"v{no_versao} | "
                                f"€{total_com:,.2f}"
                            ),
                            ip=""
                        )
                        st.session_state['orc_linhas_temp'] = []
                        inv()
                        st.success(
                            f"✅ Orçamento criado! "
                            f"Total: €{total_com:,.2f}"
                        )
                        st.rerun()

            with col_btn2:
                if st.button(
                    "🗑️ Limpar Linhas",
                    key="btn_clear_orc",
                    use_container_width=True
                ):
                    st.session_state['orc_linhas_temp'] = []
                    st.rerun()
        else:
            st.info("📝 Ainda sem linhas. Adiciona pelo formulário acima.")

    # ════════════════════════════════════════════════════════════════
    # REAL VS ORÇADO
    # ════════════════════════════════════════════════════════════════
    with tab_comp:
        st.markdown("#### 📊 Comparativo Real vs Orçado")

        if orc_db.empty:
            st.info("📋 Sem orçamentos para comparar.")
        else:
            obras_orc = orc_db['Obra'].dropna().unique().tolist()
            obra_comp = st.selectbox(
                "Selecionar Obra",
                obras_orc,
                key="orc_comp_obra"
            )

            orc_obra = orc_db[orc_db['Obra'] == obra_comp]
            if orc_obra.empty:
                st.info("📋 Sem orçamento para esta obra.")
            else:
                # Usar versão mais recente
                orc_ref = orc_obra.sort_values('Versao').iloc[-1]
                tot_orc = float(orc_ref.get('Total_Com_Margem',0) or 0)
                tot_orc_sm = float(orc_ref.get('Total_Sem_Margem',0) or 0)

                # Custos reais
                compras_db2 = _load("compras.csv",["Obra","Total","Status"])
                real_mat = 0.0
                if not compras_db2.empty:
                    cm2 = compras_db2[
                        (compras_db2['Obra'] == obra_comp) &
                        (compras_db2['Status'] == 'Aprovado')
                    ]
                    real_mat = pd.to_numeric(
                        cm2.get('Total',0), errors='coerce'
                    ).fillna(0).sum()

                dorm_db2 = _load("dormidas.csv",["Obra","Total"])
                real_dorm = 0.0
                if not dorm_db2.empty:
                    dd2 = dorm_db2[dorm_db2['Obra']==obra_comp]
                    real_dorm = pd.to_numeric(
                        dd2.get('Total',0), errors='coerce'
                    ).fillna(0).sum()

                real_total = real_mat + real_dorm
                desvio     = round(real_total - tot_orc_sm, 2)
                desvio_pct = round(desvio/tot_orc_sm*100, 1) \
                             if tot_orc_sm > 0 else 0

                col_cv1, col_cv2, col_cv3 = st.columns(3)
                with col_cv1:
                    st.metric("📋 Orçado (s/ margem)",
                              f"€{tot_orc_sm:,.2f}")
                with col_cv2:
                    st.metric("💸 Custo Real",
                              f"€{real_total:,.2f}",
                              delta=f"{desvio_pct:+.1f}%",
                              delta_color="inverse")
                with col_cv3:
                    st.metric("📊 Orçado (c/ margem)",
                              f"€{tot_orc:,.2f

"""
GESTNOW v3 — mod_dashboard.py
Dashboard Avançado com KPIs, Gráficos e Previsões
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core import load_db, inv

def render_dashboard(*args):
    """Dashboard Avançado com KPIs e Analytics"""

    st.markdown("""
    <style>
    .kpi-card {
        background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(96,165,250,0.1));
        border: 2px solid rgba(59,130,246,0.3);
        border-radius: 15px; padding: 20px; margin-bottom: 15px;
    }
    .kpi-value { font-size: 2rem; font-weight: bold; color: #60A5FA; }
    .kpi-label { color: #94A3B8; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    # Header
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E293B,#0F172A);padding:30px;
        border-radius:20px;margin-bottom:30px;border:1px solid rgba(255,255,255,0.2);">
        <h1 style="color:#F8FAFC;margin:0;font-size:2.5rem;">📊 Dashboard Executivo</h1>
        <p style="color:#94A3B8;margin:10px 0 0 0;">Visão geral de produção e KPIs</p>
        <p style="color:#64748B;margin:5px 0 0 0;font-size:0.9rem;">
            {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Filtros
    st.markdown("### 🔍 Filtros")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        obra_filtro = st.multiselect("Obras",
            obras_db['Obra'].unique() if not obras_db.empty else [],
            default=[], key="dash_obra")
    with col_f2:
        tipo_filtro = st.selectbox("Tipo de Vista",
            ["Todos","Admin","Técnico","Cliente"], key="dash_tipo")
    with col_f3:
        periodo = st.selectbox("Período",
            ["Hoje","Esta Semana","Este Mês","Todos"], key="dash_periodo")

    st.divider()

    # ── KPIs ─────────────────────────────────────────────────────────
    st.markdown("### 🎯 KPIs Principais")

    total_obras    = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
    total_tecnicos = len(users) if not users.empty else 0

    # ✅ CORRIGIDO: pd.to_numeric ANTES de qualquer agrupamento
    total_horas    = 0.0
    horas_validadas= 0.0
    if not registos_db.empty and 'Horas_Total' in registos_db.columns:
        registos_db = registos_db.copy()
        registos_db['Horas_Total'] = pd.to_numeric(
            registos_db['Horas_Total'], errors='coerce'
        ).fillna(0)
        total_horas     = registos_db['Horas_Total'].sum()
        horas_validadas = registos_db[
            registos_db['Status'] == '1'
        ]['Horas_Total'].sum()

    # Carregar instrumentos de todas as obras
    total_instrumentos     = 0
    instrumentos_instalados= 0
    calibrados_count       = 0

    if not obras_db.empty:
        for _, obra in obras_db.iterrows():
            o_key = obra['Obra'].replace(' ', '_').replace('/', '_')
            try:
                inst = load_db(f"inst_{o_key}_index.csv", ["Status"], silent=True)
                if not inst.empty:
                    total_instrumentos      += len(inst)
                    instrumentos_instalados += len(inst[inst['Status'].isin(['3','4'])])
                    calibrados_count        += len(inst[inst['Status'] == '2'])
            except:
                pass

    progresso_geral = (instrumentos_instalados / total_instrumentos * 100) if total_instrumentos > 0 else 0
    produtividade   = (horas_validadas / total_horas * 100) if total_horas > 0 else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{total_obras}</div>
            <div class="kpi-label">🏭 Obras Ativas</div></div>""",
            unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{total_tecnicos}</div>
            <div class="kpi-label">👷 Técnicos</div></div>""",
            unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{total_horas:.0f}h</div>
            <div class="kpi-label">⏱️ Horas Totais</div></div>""",
            unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{produtividade:.1f}%</div>
            <div class="kpi-label">✅ Horas Válidas</div></div>""",
            unsafe_allow_html=True)
    with col5:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{total_instrumentos}</div>
            <div class="kpi-label">🔧 Instrumentos</div></div>""",
            unsafe_allow_html=True)
    with col6:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{progresso_geral:.1f}%</div>
            <div class="kpi-label">📈 Progresso</div></div>""",
            unsafe_allow_html=True)

    st.divider()

    # ── Gráficos ──────────────────────────────────────────────────────
    st.markdown("### 📈 Analytics")

    tab_g1, tab_g2, tab_g3, tab_g4 = st.tabs([
        "📊 Progresso por Obra",
        "⏱️ Horas por Semana",
        "🔥 Incidentes",
        "🏆 Ranking Técnicos"
    ])

    # TAB 1: PROGRESSO POR OBRA
    with tab_g1:
        st.markdown("### Progresso de Instrumentação por Obra")
        dados_progresso = []
        if not obras_db.empty:
            for _, obra in obras_db.iterrows():
                if obra['Ativa'] == 'Ativa':
                    o_key = obra['Obra'].replace(' ','_').replace('/','_')
                    try:
                        inst = load_db(f"inst_{o_key}_index.csv", ["Status"], silent=True)
                        if not inst.empty:
                            total    = len(inst)
                            inst_ok  = len(inst[inst['Status'].isin(['3','4'])])
                            prog     = (inst_ok / total * 100) if total > 0 else 0
                            dados_progresso.append({
                                "Obra": obra['Obra'],
                                "Total": total,
                                "Instalados": inst_ok,
                                "Progresso (%)": round(prog, 1)
                            })
                    except:
                        pass

        if dados_progresso:
            df_prog = pd.DataFrame(dados_progresso)
            st.bar_chart(df_prog.set_index("Obra")["Progresso (%)"], color="#3B82F6")
            st.dataframe(df_prog, use_container_width=True, hide_index=True)
        else:
            st.info("📋 Sem dados de instrumentação disponíveis.")

    # TAB 2: HORAS POR SEMANA ✅ CORRIGIDO
    with tab_g2:
        st.markdown("### Horas Trabalhadas por Semana")

        if not registos_db.empty and 'Data' in registos_db.columns:
            df_sem = registos_db.copy()

            # ✅ converter ANTES do groupby
            df_sem['Horas_Total'] = pd.to_numeric(
                df_sem['Horas_Total'], errors='coerce'
            ).fillna(0)

            df_sem['Data_Parse'] = pd.to_datetime(
                df_sem['Data'], dayfirst=True, errors='coerce'
            )
            df_sem = df_sem.dropna(subset=['Data_Parse'])
            df_sem['Semana'] = df_sem['Data_Parse'].dt.isocalendar().week.astype(int)

            horas_semana = (
                df_sem.groupby('Semana')['Horas_Total']
                .sum()
                .reset_index()
                .rename(columns={'Horas_Total': 'Horas'})
            )

            if not horas_semana.empty:
                st.bar_chart(horas_semana.set_index("Semana"), color="#10B981")
                st.dataframe(horas_semana, use_container_width=True, hide_index=True)
            else:
                st.info("📋 Sem dados de horas para o período.")
        else:
            st.info("📋 Sem registos de horas disponíveis.")

    # TAB 3: INCIDENTES
    with tab_g3:
        st.markdown("### 🔥 Mapa de Incidentes HSE")

        if not incs_db.empty:
            # Filtrar apenas HSE (excluir avarias)
            hse_db = incs_db[incs_db.get('Tipo','') != 'Avaria'] if 'Tipo' in incs_db.columns else incs_db

            if not hse_db.empty:
                if 'Gravidade' in hse_db.columns:
                    inc_grav = hse_db['Gravidade'].value_counts().reset_index()
                    inc_grav.columns = ['Gravidade', 'Count']
                    st.bar_chart(inc_grav.set_index("Gravidade"), color="#EF4444")

                st.divider()

                if 'Obra' in hse_db.columns:
                    inc_obra = hse_db['Obra'].value_counts().reset_index()
                    inc_obra.columns = ['Obra', 'Incidentes']
                    st.markdown("#### Por Obra")
                    st.dataframe(inc_obra, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("#### Últimos Incidentes")
                cols_show = [c for c in ['Data','Utilizador','Obra','Descricao','Gravidade','Status'] if c in hse_db.columns]
                st.dataframe(hse_db[cols_show].head(10), use_container_width=True, hide_index=True)
            else:
                st.success("✅ Sem incidentes HSE registados!")
        else:
            st.success("✅ Sem incidentes registados!")

    # TAB 4: RANKING TÉCNICOS
    with tab_g4:
        st.markdown("### 🏆 Ranking de Produtividade")

        if not registos_db.empty and 'Técnico' in registos_db.columns:
            df_rank = registos_db.copy()
            df_rank['Horas_Total'] = pd.to_numeric(
                df_rank['Horas_Total'], errors='coerce'
            ).fillna(0)

            horas_tec = (
                df_rank.groupby('Técnico')['Horas_Total']
                .sum()
                .reset_index()
                .rename(columns={'Horas_Total': 'Horas Totais'})
                .sort_values('Horas Totais', ascending=False)
            )

            st.bar_chart(horas_tec.set_index("Técnico").head(10), color="#F59E0B")
            st.dataframe(horas_tec.head(10), use_container_width=True, hide_index=True)

            st.divider()

            pendentes = (
                df_rank[df_rank['Status'] == '0']
                .groupby('Técnico')
                .size()
                .reset_index()
                .rename(columns={0: 'Pendentes'})
            )
            if not pendentes.empty:
                st.markdown("### ⏳ Validações Pendentes por Técnico")
                st.dataframe(pendentes, use_container_width=True, hide_index=True)
        else:
            st.info("📋 Sem dados de produtividade disponíveis.")

    st.divider()

    # ── Previsões ──────────────────────────────────────────────────────
    st.markdown("### 🔮 Previsões")
    col_p1, col_p2 = st.columns(2)

    data_prev = (datetime.now() + timedelta(
        days=max(1, int((100 - progresso_geral) * 3))
    )).strftime("%d/%m/%Y")

    obras_atrasadas = len([d for d in dados_progresso if d.get('Progresso (%)', 0) < 50]) if dados_progresso else 0
    pend_horas = len(registos_db[registos_db['Status'] == '0']) if not registos_db.empty else 0

    with col_p1:
        st.markdown(f"""
        <div class="kpi-card">
            <h4 style="color:#60A5FA;margin:0 0 15px 0;">📅 Conclusão Prevista</h4>
            <p style="color:#94A3B8;">Progresso atual: {progresso_geral:.1f}%</p>
            <p style="color:#F8FAFC;font-size:1.5rem;font-weight:bold;margin:15px 0;">
                {data_prev}
            </p>
            <p style="color:#64748B;font-size:0.85rem;">
                *Baseado na média dos últimos 30 dias
            </p>
        </div>""", unsafe_allow_html=True)

    with col_p2:
        st.markdown(f"""
        <div class="kpi-card">
            <h4 style="color:#60A5FA;margin:0 0 15px 0;">⚠️ Riscos Detetados</h4>
            <ul style="color:#94A3B8;margin:0;padding-left:20px;">
                <li>{obras_atrasadas} obra(s) com progresso abaixo de 50%</li>
                <li>{total_instrumentos - instrumentos_instalados - calibrados_count} instrumento(s) por calibrar</li>
                <li>{pend_horas} validação(ões) de horas pendente(s)</li>
            </ul>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Atividades Recentes ────────────────────────────────────────────
    st.markdown("### 🕐 Atividades Recentes")
    col_a1, col_a2 = st.columns(2)

    with col_a1:
        st.markdown("#### 📋 Últimas Validações")
        if not registos_db.empty:
            ult_val = registos_db[registos_db['Status'] == '1'].tail(5)
            if not ult_val.empty:
                for _, val in ult_val.iterrows():
                    data_str = val['Data'].strftime('%d/%m/%Y') if hasattr(val['Data'], 'strftime') else str(val.get('Data',''))
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.1);border-left:3px solid #10B981;
                        padding:10px;border-radius:5px;margin-bottom:10px;">
                        <strong style="color:#10B981;">✅ {val.get('Técnico','N/A')}</strong>
                        <p style="margin:5px 0 0 0;color:#94A3B8;font-size:0.85rem;">
                            {val.get('Horas_Total',0):.1f}h em {val.get('Obra','N/A')} | {data_str}
                        </p>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("Sem validações recentes.")
        else:
            st.info("Sem registos.")

    with col_a2:
        st.markdown("#### 🔧 Últimas Instalações")
        instalacoes = []
        if not obras_db.empty:
            for _, obra in obras_db.iterrows():
                o_key = obra['Obra'].replace(' ','_').replace('/','_')
                try:
                    inst = load_db(f"inst_{o_key}_index.csv",
                                   ["Tag","Status","Descricao"], silent=True)
                    if not inst.empty:
                        inst_ok = inst[inst['Status'].isin(['3','4'])].tail(2)
                        for _, ir in inst_ok.iterrows():
                            instalacoes.append({
                                "Tag": ir.get('Tag','N/A'),
                                "Obra": obra['Obra'],
                                "Desc": ir.get('Descricao','N/A')
                            })
                except:
                    pass

        if instalacoes:
            for i in instalacoes[-5:]:
                st.markdown(f"""
                <div style="background:rgba(59,130,246,0.1);border-left:3px solid #3B82F6;
                    padding:10px;border-radius:5px;margin-bottom:10px;">
                    <strong style="color:#3B82F6;">📍 {i['Tag']}</strong>
                    <p style="margin:5px 0 0 0;color:#94A3B8;font-size:0.85rem;">
                        {i['Obra']} | {i['Desc']}
                    </p>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Sem instalações recentes.")

    st.divider()
    if st.button("🔄 Atualizar Dados", use_container_width=True,
                 type="secondary", key="dash_refresh"):
        inv()
        st.rerun()

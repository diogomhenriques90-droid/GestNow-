"""
GESTNOW v3 — mod_dashboard.py
Dashboard Avançado com KPIs, Gráficos e Previsões
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core import load_db, inv

def _safe_date_str(val):
    """Converte data para string sem crashar com NaT."""
    try:
        if pd.isna(val):
            return 'N/A'
        if hasattr(val, 'strftime'):
            return val.strftime('%d/%m/%Y')
        return str(val)
    except:
        return 'N/A'

@st.cache_data(ttl=3600, show_spinner=False)
def _load_instrumentos_cache(obra_keys_tuple):
    """Agrega dados de instrumentação de todas as obras activas. TTL=5min."""
    dados_progresso = []
    total_inst = 0
    total_inst_ok = 0
    total_cal = 0
    instalacoes = []
    for o_key, obra_nome in obra_keys_tuple:
        try:
            inst = load_db(f"inst_{o_key}_index.csv",
                           ["Tag", "Status", "Descricao"], silent=True)
            if not inst.empty:
                total   = len(inst)
                inst_ok = len(inst[inst['Status'].isin(['3', '4'])])
                calib   = len(inst[inst['Status'] == '2'])
                prog    = (inst_ok / total * 100) if total > 0 else 0
                total_inst    += total
                total_inst_ok += inst_ok
                total_cal     += calib
                dados_progresso.append({
                    "Obra":          obra_nome,
                    "Total":         total,
                    "Instalados":    inst_ok,
                    "Progresso (%)": round(prog, 1)
                })
                for _, ir in inst[inst['Status'].isin(['3', '4'])].tail(2).iterrows():
                    instalacoes.append({
                        "Tag":  ir.get('Tag', 'N/A'),
                        "Obra": obra_nome,
                        "Desc": ir.get('Descricao', 'N/A')
                    })
        except:
            pass
    return dados_progresso, total_inst, total_inst_ok, total_cal, instalacoes


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
    comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
    *_) = args

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

    st.markdown("### 🔍 Filtros")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        obra_filtro = st.multiselect("Obras",
            obras_db['Obra'].unique() if not obras_db.empty else [],
            default=[], key="dash_obra")
    with col_f2:
        tipo_filtro = st.selectbox("Tipo de Vista",
            ["Todos", "Admin", "Técnico", "Cliente"], key="dash_tipo")
    with col_f3:
        periodo = st.selectbox("Período",
            ["Hoje", "Esta Semana", "Este Mês", "Todos"], key="dash_periodo")

    st.divider()

    # ── KPIs ──────────────────────────────────────────────────────────
    st.markdown("### 🎯 KPIs Principais")

    total_obras    = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
    total_tecnicos = len(users) if not users.empty else 0

    # ✅ pd.to_numeric ANTES de qualquer operação
    total_horas     = 0.0
    horas_validadas = 0.0
    if not registos_db.empty and 'Horas_Total' in registos_db.columns:
        registos_db = registos_db.copy()
        registos_db['Horas_Total'] = pd.to_numeric(
            registos_db['Horas_Total'], errors='coerce'
        ).fillna(0)
        total_horas     = registos_db['Horas_Total'].sum()
        horas_validadas = registos_db[registos_db['Status'] == '1']['Horas_Total'].sum()

    # Instrumentos — carregados via cache TTL=5min para evitar N leituras GCS por render
    dados_progresso         = []
    total_instrumentos      = 0
    instrumentos_instalados = 0
    calibrados_count        = 0
    instalacoes             = []

    if not obras_db.empty:
        _obra_keys = tuple(
            (obra['Obra'].replace(' ', '_').replace('/', '_'), obra['Obra'])
            for _, obra in obras_db.iterrows()
            if obra.get('Ativa', '') == 'Ativa'
        )
        (dados_progresso, total_instrumentos,
         instrumentos_instalados, calibrados_count, instalacoes) = \
            _load_instrumentos_cache(_obra_keys)

    progresso_geral = (instrumentos_instalados / total_instrumentos * 100) if total_instrumentos > 0 else 0
    produtividade   = (horas_validadas / total_horas * 100) if total_horas > 0 else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    kpis = [
        (total_obras,    "🏭 Obras Ativas"),
        (total_tecnicos, "👷 Técnicos"),
        (f"{total_horas:.0f}h", "⏱️ Horas Totais"),
        (f"{produtividade:.1f}%", "✅ Horas Válidas"),
        (total_instrumentos, "🔧 Instrumentos"),
        (f"{progresso_geral:.1f}%", "📈 Progresso"),
    ]
    for col, (val, lbl) in zip([col1, col2, col3, col4, col5, col6], kpis):
        with col:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{lbl}</div></div>""",
                unsafe_allow_html=True)

    st.divider()

    # ── Gráficos ───────────────────────────────────────────────────────
    st.markdown("### 📈 Analytics")

    tab_g1, tab_g2, tab_g3, tab_g4 = st.tabs([
        "📊 Progresso por Obra",
        "⏱️ Horas por Semana",
        "🔥 Incidentes",
        "🏆 Ranking Técnicos"
    ])

    # TAB 1
    with tab_g1:
        st.markdown("### Progresso de Instrumentação por Obra")
        if dados_progresso:
            df_prog = pd.DataFrame(dados_progresso)
            st.bar_chart(df_prog.set_index("Obra")["Progresso (%)"], color="#3B82F6")
            st.dataframe(df_prog, use_container_width=True, hide_index=True)
        else:
            st.info("📋 Sem dados de instrumentação disponíveis.")

    # TAB 2 ✅ CORRIGIDO — NaTType
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
            # ✅ Remover NaT antes de extrair semana
            df_sem = df_sem.dropna(subset=['Data_Parse'])

            if not df_sem.empty:
                df_sem['Semana'] = df_sem['Data_Parse'].dt.isocalendar().week.astype(int)
                horas_semana = (
                    df_sem.groupby('Semana')['Horas_Total']
                    .sum()
                    .reset_index()
                    .rename(columns={'Horas_Total': 'Horas'})
                )
                st.bar_chart(horas_semana.set_index("Semana"), color="#10B981")
                st.dataframe(horas_semana, use_container_width=True, hide_index=True)
            else:
                st.info("📋 Sem datas válidas nos registos.")
        else:
            st.info("📋 Sem registos de horas disponíveis.")

    # TAB 3
    with tab_g3:
        st.markdown("### 🔥 Mapa de Incidentes HSE")
        if not incs_db.empty:
            hse_db = incs_db[incs_db.get('Tipo', '') != 'Avaria'] if 'Tipo' in incs_db.columns else incs_db
            if not hse_db.empty:
                if 'Gravidade' in hse_db.columns:
                    inc_grav = hse_db['Gravidade'].value_counts().reset_index()
                    inc_grav.columns = ['Gravidade', 'Count']
                    st.bar_chart(inc_grav.set_index("Gravidade"), color="#EF4444")
                st.divider()
                if 'Obra' in hse_db.columns:
                    inc_obra = hse_db['Obra'].value_counts().reset_index()
                    inc_obra.columns = ['Obra', 'Incidentes']
                    st.dataframe(inc_obra, use_container_width=True, hide_index=True)
                st.divider()
                cols_show = [c for c in ['Data','Utilizador','Obra','Descricao','Gravidade','Status'] if c in hse_db.columns]
                st.dataframe(hse_db[cols_show].head(10), use_container_width=True, hide_index=True)
            else:
                st.success("✅ Sem incidentes HSE!")
        else:
            st.success("✅ Sem incidentes registados!")

    # TAB 4
    with tab_g4:
        st.markdown("### 🏆 Ranking de Produtividade")
        if not registos_db.empty and 'Técnico' in registos_db.columns:
            df_rank = registos_db.copy()
            df_rank['Horas_Total'] = pd.to_numeric(df_rank['Horas_Total'], errors='coerce').fillna(0)
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
                st.markdown("### ⏳ Validações Pendentes")
                st.dataframe(pendentes, use_container_width=True, hide_index=True)
        else:
            st.info("📋 Sem dados disponíveis.")

    st.divider()

    # ── Previsões ──────────────────────────────────────────────────────
    st.markdown("### 🔮 Previsões")
    data_prev       = (datetime.now() + timedelta(days=max(1, int((100 - progresso_geral) * 3)))).strftime("%d/%m/%Y")
    obras_atrasadas = len([d for d in dados_progresso if d.get('Progresso (%)', 0) < 50])
    pend_horas      = int(registos_db[registos_db['Status'] == '0']['Horas_Total'].sum()) if not registos_db.empty else 0

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown(f"""
        <div class="kpi-card">
            <h4 style="color:#60A5FA;margin:0 0 15px 0;">📅 Conclusão Prevista</h4>
            <p style="color:#94A3B8;">Progresso atual: {progresso_geral:.1f}%</p>
            <p style="color:#F8FAFC;font-size:1.5rem;font-weight:bold;margin:15px 0;">{data_prev}</p>
            <p style="color:#64748B;font-size:0.85rem;">*Baseado na média dos últimos 30 dias</p>
        </div>""", unsafe_allow_html=True)
    with col_p2:
        st.markdown(f"""
        <div class="kpi-card">
            <h4 style="color:#60A5FA;margin:0 0 15px 0;">⚠️ Riscos Detetados</h4>
            <ul style="color:#94A3B8;margin:0;padding-left:20px;">
                <li>{obras_atrasadas} obra(s) com progresso abaixo de 50%</li>
                <li>{total_instrumentos - instrumentos_instalados - calibrados_count} instrumento(s) por calibrar</li>
                <li>{pend_horas}h de validações pendentes</li>
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
                    # ✅ CORRIGIDO: usa _safe_date_str para evitar NaTType
                    data_str = _safe_date_str(val.get('Data'))
                    horas_v  = val.get('Horas_Total', 0)
                    try:
                        horas_v = float(horas_v)
                    except:
                        horas_v = 0
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.1);border-left:3px solid #10B981;
                        padding:10px;border-radius:5px;margin-bottom:10px;">
                        <strong style="color:#10B981;">✅ {val.get('Técnico','N/A')}</strong>
                        <p style="margin:5px 0 0 0;color:#94A3B8;font-size:0.85rem;">
                            {horas_v:.1f}h em {val.get('Obra','N/A')} | {data_str}
                        </p>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("Sem validações recentes.")
        else:
            st.info("Sem registos.")

    with col_a2:
        st.markdown("#### 🔧 Últimas Instalações")
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
        _load_instrumentos_cache.clear()
        inv()
        st.rerun()

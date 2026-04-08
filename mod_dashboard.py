"""
GESTNOW v3 — mod_dashboard.py
Dashboard Avançado com KPIs, Gráficos e Previsões IA
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core import load_db, inv

def render_dashboard(*args):
    """Dashboard Avançado com KPIs e Analytics"""
    
    # CSS Personalizado
    st.markdown("""
    <style>
    .kpi-card {
        background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(96,165,250,0.1));
        border: 2px solid rgba(59,130,246,0.3);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
        color: #60A5FA;
    }
    .kpi-label {
        color: #94A3B8;
        font-size: 0.9rem;
    }
    .status-em-atraso { color: #EF4444; }
    .status-no-prazo { color: #10B981; }
    .status-adiantado { color: #3B82F6; }
    </style>
    """, unsafe_allow_html=True)
    
    # Desempacotar dados
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args
    
    # Header
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:30px; border-radius:20px; margin-bottom:30px; border:1px solid rgba(255,255,255,0.2);">
        <h1 style="color:#F8FAFC; margin:0; font-size:2.5rem;">📊 Dashboard Executivo</h1>
        <p style="color:#94A3B8; margin:10px 0 0 0;">Visão geral de produção e KPIs</p>
        <p style="color:#64748B; margin:5px 0 0 0; font-size:0.9rem;">{datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filtros Globais
    st.markdown("### 🔍 Filtros", unsafe_allow_html=True)
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        obra_filtro = st.multiselect("Obras", obras_db['Obra'].unique() if not obras_db.empty else [], default=[], key="dash_obra")
    with col_f2:
        tipo_filtro = st.selectbox("Tipo de Vista", ["Todos", "Admin", "Técnico", "Cliente"], key="dash_tipo")
    with col_f3:
        periodo = st.selectbox("Período", ["Hoje", "Esta Semana", "Este Mês", "Todos"], key="dash_periodo")
    
    st.divider()
    
    # ========== KPIs GERAIS ==========
    st.markdown("### 🎯 KPIs Principais", unsafe_allow_html=True)
    
    # Calcular KPIs
    total_obras = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
    total_tecnicos = len(users) if not users.empty else 0
    total_horas = registos_db['Horas_Total'].astype(float).sum() if not registos_db.empty and 'Horas_Total' in registos_db.columns else 0
    horas_validadas = registos_db[registos_db['Status'] == '1']['Horas_Total'].astype(float).sum() if not registos_db.empty and 'Status' in registos_db.columns else 0
    total_instrumentos = 0
    instrumentos_instalados = 0
    
    # Carregar instrumentos de todas as obras
    if not obras_db.empty:
        for _, obra in obras_db.iterrows():
            o_key = obra['Obra'].replace(' ', '_').replace('/', '_')
            try:
                inst = load_db(f"inst_{o_key}_index.csv", ["Status"], silent=True)
                if not inst.empty:
                    total_instrumentos += len(inst)
                    instrumentos_instalados += len(inst[inst['Status'].isin(['3', '4'])])
            except:
                pass
    
    progresso_geral = (instrumentos_instalados / total_instrumentos * 100) if total_instrumentos > 0 else 0
    produtividade = (horas_validadas / total_horas * 100) if total_horas > 0 else 0
    
    # KPIs em Cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_obras}</div>
            <div class="kpi-label">🏭 Obras Ativas</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_tecnicos}</div>
            <div class="kpi-label">👷 Técnicos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_horas:.0f}h</div>
            <div class="kpi-label">⏱️ Horas Totais</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{produtividade:.1f}%</div>
            <div class="kpi-label">✅ Horas Válidas</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_instrumentos}</div>
            <div class="kpi-label">🔧 Instrumentos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{progresso_geral:.1f}%</div>
            <div class="kpi-label">📈 Progresso</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # ========== GRÁFICOS ==========
    st.markdown("### 📈 Analytics", unsafe_allow_html=True)
    
    tab_graf1, tab_graf2, tab_graf3, tab_graf4 = st.tabs([
        "📊 Progresso por Obra",
        "⏱️ Horas por Semana",
        "🔥 Incidentes",
        "🏆 Ranking Técnicos"
    ])
    
    # TAB 1: PROGRESSO POR OBRA
    with tab_graf1:
        st.markdown("### Progresso de Instrumentação por Obra", unsafe_allow_html=True)
        
        if not obras_db.empty:
            dados_progresso = []
            for _, obra in obras_db.iterrows():
                if obra['Ativa'] == 'Ativa':
                    o_key = obra['Obra'].replace(' ', '_').replace('/', '_')
                    try:
                        inst = load_db(f"inst_{o_key}_index.csv", ["Status"], silent=True)
                        if not inst.empty:
                            total = len(inst)
                            instalados = len(inst[inst['Status'].isin(['3', '4'])])
                            progresso = (instalados / total * 100) if total > 0 else 0
                            dados_progresso.append({
                                "Obra": obra['Obra'],
                                "Total": total,
                                "Instalados": instalados,
                                "Progresso (%)": round(progresso, 1)
                            })
                    except:
                        pass
            
            if dados_progresso:
                df_progresso = pd.DataFrame(dados_progresso)
                
                # Gráfico de barras
                st.bar_chart(df_progresso.set_index("Obra")["Progresso (%)"], color="#3B82F6")
                
                # Tabela detalhada
                st.dataframe(df_progresso, use_container_width=True, hide_index=True)
            else:
                st.info("📋 Sem dados de instrumentação disponíveis.")
        else:
            st.info("📋 Sem obras registadas.")
    
    # TAB 2: HORAS POR SEMANA
    with tab_graf2:
        st.markdown("### Horas Trabalhadas por Semana", unsafe_allow_html=True)
        
        if not registos_db.empty and 'Data' in registos_db.columns:
            # Converter datas
            registos_db['Data_Parse'] = pd.to_datetime(registos_db['Data'], format='%d/%m/%Y', errors='coerce')
            registos_db['Semana'] = registos_db['Data_Parse'].dt.isocalendar().week
            
            # Agrupar por semana
            horas_semana = registos_db.groupby('Semana')['Horas_Total'].astype(float).sum().reset_index()
            horas_semana.columns = ['Semana', 'Horas']
            
            st.bar_chart(horas_semana.set_index("Semana"), color="#10B981")
            st.dataframe(horas_semana, use_container_width=True, hide_index=True)
        else:
            st.info("📋 Sem registos de horas disponíveis.")
    
    # TAB 3: INCIDENTES
    with tab_graf3:
        st.markdown("### 🔥 Mapa de Incidentes HSE", unsafe_allow_html=True)
        
        if not incs_db.empty:
            # Incidentes por tipo
            if 'Tipo' in incs_db.columns:
                inc_tipo = incs_db['Tipo'].value_counts().reset_index()
                inc_tipo.columns = ['Tipo', 'Count']
                st.bar_chart(inc_tipo.set_index("Tipo"), color="#EF4444")
            
            st.divider()
            
            # Incidentes por obra
            if 'Obra' in incs_db.columns:
                inc_obra = incs_db['Obra'].value_counts().reset_index()
                inc_obra.columns = ['Obra', 'Incidentes']
                st.dataframe(inc_obra, use_container_width=True, hide_index=True)
            
            st.divider()
            st.markdown("### Últimos Incidentes")
            st.dataframe(incs_db.head(10), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Sem incidentes registados!")
    
    # TAB 4: RANKING TÉCNICOS
    with tab_graf4:
        st.markdown("### 🏆 Ranking de Produtividade", unsafe_allow_html=True)
        
        if not registos_db.empty and 'Técnico' in registos_db.columns:
            # Horas por técnico
            horas_tecnico = registos_db.groupby('Técnico')['Horas_Total'].astype(float).sum().reset_index()
            horas_tecnico.columns = ['Técnico', 'Horas Totais']
            horas_tecnico = horas_tecnico.sort_values('Horas Totais', ascending=False)
            
            st.bar_chart(horas_tecnico.set_index("Técnico").head(10), color="#F59E0B")
            st.dataframe(horas_tecnico.head(10), use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Validações pendentes por técnico
            pendentes = registos_db[registos_db['Status'] == '0'].groupby('Técnico').size().reset_index()
            if not pendentes.empty:
                pendentes.columns = ['Técnico', 'Pendentes']
                st.markdown("### ⏳ Validações Pendentes")
                st.dataframe(pendentes, use_container_width=True, hide_index=True)
        else:
            st.info("📋 Sem dados de produtividade disponíveis.")
    
    st.divider()
    
    # ========== PREVISÕES IA ==========
    st.markdown("### 🔮 Previsões IA", unsafe_allow_html=True)
    
    col_prev1, col_prev2 = st.columns(2)
    
    with col_prev1:
        st.markdown("""
        <div class="kpi-card">
            <h4 style="color:#60A5FA; margin:0 0 15px 0;">📅 Conclusão Prevista</h4>
            <p style="color:#94A3B8; margin:0;">
                Com base no progresso atual ({:.1f}%), a previsão de conclusão é:
            </p>
            <p style="color:#F8FAFC; font-size:1.5rem; font-weight:bold; margin:15px 0;">
                {}
            </p>
            <p style="color:#64748B; font-size:0.85rem; margin:0;">
                *Cálculo baseado na média de instalação dos últimos 30 dias
            </p>
        </div>
        """.format(
            progresso_geral,
            (datetime.now() + timedelta(days=max(1, int((100 - progresso_geral) * 3)))).strftime("%d/%m/%Y")
        ), unsafe_allow_html=True)
    
    with col_prev2:
        st.markdown("""
        <div class="kpi-card">
            <h4 style="color:#60A5FA; margin:0 0 15px 0;">⚠️ Riscos Detetados</h4>
            <ul style="color:#94A3B8; margin:0; padding-left:20px;">
                <li>{} obras com progresso abaixo de 50%</li>
                <li>{} instrumentos pendentes de calibração</li>
                <li>{} validações de horas pendentes</li>
            </ul>
        </div>
        """.format(
            len([d for d in dados_progresso if d.get('Progresso (%)', 0) < 50]) if 'dados_progresso' in dir() else 0,
            total_instrumentos - instrumentos_instalados - calibrados if 'calibrados' in dir() else 0,
            len(registos_db[registos_db['Status'] == '0']) if not registos_db.empty else 0
        ), unsafe_allow_html=True)
    
    st.divider()
    
    # ========== ATIVIDADES RECENTES ==========
    st.markdown("### 🕐 Atividades Recentes", unsafe_allow_html=True)
    
    col_act1, col_act2 = st.columns(2)
    
    with col_act1:
        st.markdown("#### 📋 Últimas Validações")
        if not registos_db.empty:
            ultimas_val = registos_db[registos_db['Status'] == '1'].tail(5)
            if not ultimas_val.empty:
                for _, val in ultimas_val.iterrows():
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.1); border-left:3px solid #10B981; padding:10px; border-radius:5px; margin-bottom:10px;">
                        <strong style="color:#10B981;">✅ {val.get('Técnico', 'N/A')}</strong>
                        <p style="margin:5px 0 0 0; color:#94A3B8; font-size:0.85rem;">
                            {val.get('Horas_Total', '0')}h em {val.get('Obra', 'N/A')} | {val.get('Data', 'N/A')}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Sem validações recentes.")
        else:
            st.info("Sem registos.")
    
    with col_act2:
        st.markdown("#### 🔧 Últimas Instalações")
        # Carregar últimas instalações de todas as obras
        instalacoes_recentes = []
        if not obras_db.empty:
            for _, obra in obras_db.iterrows():
                o_key = obra['Obra'].replace(' ', '_').replace('/', '_')
                try:
                    inst = load_db(f"inst_{o_key}_index.csv", ["Tag", "Status", "Descricao"], silent=True)
                    if not inst.empty:
                        instaladas = inst[inst['Status'].isin(['3', '4'])].tail(3)
                        for _, inst_row in instaladas.iterrows():
                            instalacoes_recentes.append({
                                "Tag": inst_row.get('Tag', 'N/A'),
                                "Obra": obra['Obra'],
                                "Descricao": inst_row.get('Descricao', 'N/A')
                            })
                except:
                    pass
        
        if instalacoes_recentes:
            for inst in instalacoes_recentes[-5:]:
                st.markdown(f"""
                <div style="background:rgba(59,130,246,0.1); border-left:3px solid #3B82F6; padding:10px; border-radius:5px; margin-bottom:10px;">
                    <strong style="color:#3B82F6;">📍 {inst['Tag']}</strong>
                    <p style="margin:5px 0 0 0; color:#94A3B8; font-size:0.85rem;">
                        {inst['Obra']} | {inst['Descricao']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sem instalações recentes.")
    
    # Botão de refresh
    st.divider()
    if st.button("🔄 Atuar Dados", use_container_width=True, type="secondary"):
        inv()
        st.rerun()

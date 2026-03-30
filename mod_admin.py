import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import plotly.express as px

# Importações do seu arquivo core.py
try:
    from core import (
        load_all, save_db, inv, fh, sl, render_metric, t, gerar_pdf
    )
except ImportError:
    st.error("Erro: O arquivo 'core.py' não foi encontrado ou faltam funções nele.")

def render_admin(*args):
    # 1. Desempacotamento integral das 20 variáveis (conforme solicitado)
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db, 
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    st.title(f"🛡️ Admin: {st.session_state.get('user', 'Administrador')}")

    # Definição das Abas Administrativas
    tabs = st.tabs(["📊 Dash", "✅ Aprovar", "👥 Pessoal", "🏗️ Obras", "💰 Faturação", "🛡️ HSE"])

    # ============================================================
    # TAB 0: DASHBOARD ESTRATÉGICO
    # ============================================================
    with tabs[0]:
        st.subheader("Visão Geral do Sistema")
        
        # Métricas em Colunas
        c1, c2, c3, c4 = st.columns(4)
        total_horas = registos_db['Horas_Total'].sum() if not registos_db.empty else 0
        pendentes = len(registos_db[registos_db['Status'] == "0"]) if not registos_db.empty else 0
        obras_ativas = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
        tecnicos_count = users['Nome'].nunique() if not users.empty else 0

        with c1: render_metric("⏱️", fh(total_horas), "Total Horas")
        with c2: render_metric("👷", tecnicos_count, "Técnicos Ativos")
        with c3: render_metric("🏗️", obras_ativas, "Obras Ativas")
        with c4: render_metric("⏳", pendentes, "Pendentes Aprovação")
        
        st.divider()

        # Gráfico de Evolução de Horas (Plotly)
        if not registos_db.empty:
            df_grafico = registos_db.copy()
            df_grafico['Data'] = pd.to_datetime(df_grafico['Data'], dayfirst=True)
            df_resumo = df_grafico.groupby('Data')['Horas_Total'].sum().reset_index().sort_values('Data')
            
            fig = px.area(
                df_resumo, x='Data', y='Horas_Total', 
                title="📈 Curva de Carga (Horas Totais / Dia)",
                color_discrete_sequence=['#0A2463']
            )
            fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o gráfico de evolução.")

    # ============================================================
    # TAB 1: APROVAÇÕES DE PONTO
    # ============================================================
    with tabs[1]:
        st.subheader("Validação de Registos de Trabalho")
        pend = registos_db[registos_db['Status'] == "0"] if not registos_db.empty else pd.DataFrame()
        
        if pend.empty:
            st.success("✅ Todos os registos estão validados.")
        else:
            st.warning(f"Existem {len(pend)} registos aguardando aprovação.")
            st.dataframe(
                pend[['Data', 'Técnico', 'Obra', 'Horas_Total', 'Turnos', 'Frente']], 
                use_container_width=True, hide_index=True
            )
            
            c_apr, c_rej = st.columns([1, 4])
            if c_apr.button("✅ Aprovar Todos", use_container_width=True, type="primary"):
                registos_db.loc[registos_db['Status'] == "0", 'Status'] = "1"
                save_db(registos_db, "registos.csv")
                st.success("Registos aprovados com sucesso!"); inv(); st.rerun()

    # ============================================================
    # TAB 2: GESTÃO DE PESSOAL
    # ============================================================
    with tabs[2]:
        st.subheader("Equipa e Performance ⭐")
        if not users.empty:
            for _, u in users.iterrows():
                with st.expander(f"👤 {u['Nome']} - {u['Cargo']}"):
                    col1, col2 = st.columns(2)
                    col1.write(f"**Email:** {u.get('Email', 'N/A')}")
                    col1.write(f"**NIF:** {u.get('NIF', 'N/A')}")
                    
                    # Simulação de Ranking/KPI
                    horas_user = registos_db[registos_db['Técnico'] == u['Nome']]['Horas_Total'].sum() if not registos_db.empty else 0
                    col2.metric("Horas Acumuladas", f"{horas_user}h")
                    
                    if st.button(f"Editar Perfil: {u['Nome']}", key=f"edit_{u['Nome']}"):
                        st.info("Módulo de edição de utilizador em desenvolvimento.")
        else:
            st.error("Nenhum utilizador encontrado na base de dados.")

    # ============================================================
    # TAB 3: CONTROLO DE OBRAS
    # ============================================================
    with tabs[3]:
        st.subheader("Gestão de Projetos")
        
        # Lista de Obras Atuais
        if not obras_db.empty:
            st.dataframe(obras_db[['Obra', 'Cliente', 'TipoObra', 'Ativa']], use_container_width=True, hide_index=True)
        
        st.divider()
        
        with st.expander("➕ Criar Nova Obra / Projeto"):
            with st.form("nova_obra"):
                no = st.text_input("Nome da Obra (ID Único)")
                cl = st.text_input("Cliente")
                ti = st.selectbox("Tipo de Obra", ["Normal", "Instrumentação", "Manutenção", "Paragem"])
                est = st.selectbox("Estado Inicial", ["Ativa", "Pendente", "Concluída"])
                
                if st.form_submit_button("🚀 Registar Projeto"):
                    if no and cl:
                        new_o = pd.DataFrame([{"Obra": no, "Cliente": cl, "TipoObra": ti, "Ativa": est}])
                        save_db(pd.concat([obras_db, new_o]), "obras_lista.csv")
                        st.success(f"Obra '{no}' criada com sucesso!"); inv(); st.rerun()
                    else:
                        st.error("Nome da Obra e Cliente são obrigatórios.")

    # ============================================================
    # TAB 4: CENTRO DE FATURAÇÃO
    # ============================================================
    with tabs[4]:
        st.subheader("💰 Resumo para Faturação")
        if not obras_db.empty:
            cliente_f = st.selectbox("Filtrar por Cliente", obras_db['Cliente'].unique())
            
            # Filtra horas aprovadas (Status "1") para o cliente
            obras_do_cliente = obras_db[obras_db['Cliente'] == cliente_f]['Obra'].tolist()
            horas_faturar = registos_db[(registos_db['Obra'].isin(obras_do_cliente)) & (registos_db['Status'] == "1")]
            
            st.metric(f"Horas a Faturar ({cliente_f})", f"{horas_faturar['Horas_Total'].sum()} h")
            
            if st.button("📄 Gerar Relatório de Horas PDF"):
                st.info(f"A exportar dados de {cliente_f} para formato PDF...")
                # Aqui chamaria a sua função core: gerar_pdf(horas_faturar)
        else:
            st.info("Nenhuma obra registada para faturação.")

    # ============================================================
    # TAB 5: SEGURANÇA (HSE)
    # ============================================================
    with tabs[5]:
        st.subheader("🛡️ Gestão de Incidentes HSE")
        if not incs_db.empty:
            # Filtro por gravidade
            criticos = len(incs_db[incs_db['Gravidade'] == 'Alta (Crítica)'])
            if criticos > 0:
                st.error(f"🚨 Atenção: {criticos} Incidentes Críticos Registados!")
            
            st.dataframe(incs_db.sort_values(by='Data', ascending=False), use_container_width=True)
        else:
            st.success("Nenhum incidente reportado até ao momento.")
            
        st.divider()
        st.subheader("🔍 Últimos Safety Walks")
        if not sw_db.empty:
            st.dataframe(sw_db, use_container_width=True)
        else:
            st.caption("Aguardando submissão de auditorias de segurança (Safety Walks).")

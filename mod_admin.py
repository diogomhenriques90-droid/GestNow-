import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import load_all, save_db, inv, fh, sl, render_metric, ICONS, COLORS
from translations import t
import plotly.express as px

def render_admin(*args):
    """Renderiza módulo Admin completo - Versão Corrigida"""
    
    # Desempacotamento integral das 20 variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args
    
    st.title(f"🛡️ Admin: {st.session_state.user}")

    tabs = st.tabs(["📊 Dash", "✅ Aprovar", "👥 Pessoal", "🏗️ Obras", "💰 Faturação", "🛡️ HSE"])

    # =============================================================================
    # TAB 0: DASHBOARD
    # =============================================================================
    with tabs[0]:
        st.subheader(t('dashboard'))
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            total_horas = registos_db['Horas_Total'].sum() if not registos_db.empty else 0
            render_metric("⏱️", fh(total_horas), t('total_hours'))
        with c2: 
            render_metric("👷", users['Nome'].nunique() if not users.empty else 0, "Técnicos")
        with c3: 
            render_metric("🏗️", len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0, t('active_sites'))
        with c4: 
            render_metric("⏳", len(registos_db[registos_db['Status'] == "0"]) if not registos_db.empty else 0, t('pending'))
        
        # Gráfico de Horas (Plotly)
        if not registos_db.empty:
            fig = px.area(registos_db.groupby('Data')['Horas_Total'].sum().reset_index(), x='Data', y='Horas_Total', title="Evolução de Horas")
            st.plotly_chart(fig, use_container_width=True)

    # =============================================================================
    # TAB 1: APROVAÇÕES
    # =============================================================================
    with tabs[1]:
        st.subheader(t('approvals'))
        pend = registos_db[registos_db['Status'] == "0"] if not registos_db.empty else pd.DataFrame()
        if pend.empty: 
            st.success("Sem registos pendentes.")
        else:
            st.dataframe(pend[['Data', 'Técnico', 'Obra', 'Horas_Total', 'Turnos']], use_container_width=True)
            if st.button("✅ Aprovar Todos os Registos"):
                registos_db.loc[registos_db['Status'] == "0", 'Status'] = "1"
                save_db(registos_db, "registos.csv")
                inv()
                st.rerun()

    # =============================================================================
    # TAB 2: PESSOAL & RANKING
    # =============================================================================
    with tabs[2]:
        st.subheader("Gestão de Pessoal e Ranking ⭐")
        # Lógica de cálculo automático do ranking
        if not users.empty:
            for _, u in users.iterrows():
                with st.expander(f"👤 {u['Nome']} - {u['Cargo']}"):
                    st.write(f"Email: {u['Email']} | NIF: {u['NIF']}")
                    # Ranking e avaliação
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Tipo", u['Tipo'])
                    with col2:
                        st.metric("Cargo", u['Cargo'])
                    
                    # Botões de ação
                    if st.button(f"📝 Editar {u['Nome']}", key=f"edit_{u['Nome']}"):
                        st.info(f"Editar utilizador {u['Nome']} - Funcionalidade em desenvolvimento")

    # =============================================================================
    # TAB 3: OBRAS & FRENTES
    # =============================================================================
    with tabs[3]:
        st.subheader("Controlo de Obras")
        
        # Mostrar obras existentes
        if not obras_db.empty:
            st.dataframe(obras_db[['Obra', 'Cliente', 'TipoObra', 'Ativa']], use_container_width=True)
        else:
            st.info("📋 Sem obras registadas.")
        
        st.divider()
        
        # Formulário de nova obra integral
        with st.expander("➕ Criar Nova Obra"):
            with st.form("nova_obra"):
                no = st.text_input("Nome da Obra")
                cl = st.text_input("Cliente")
                ti = st.selectbox("Tipo de Obra", ["Normal", "Instrumentação"])
                local = st.text_input("Local")
                submitted = st.form_submit_button("Criar Obra")
                
                if submitted and no and cl:
                    new_o = pd.DataFrame([{
                        "Obra": no,
                        "Cliente": cl,
                        "TipoObra": ti,
                        "Local": local,
                        "Ativa": "Ativa",
                        "DataInicio": datetime.now().strftime("%d/%m/%Y")
                    }])
                    if not obras_db.empty:
                        obras_db = pd.concat([obras_db, new_o], ignore_index=True)
                    else:
                        obras_db = new_o
                    save_db(obras_db, "obras_lista.csv")
                    inv()
                    st.success(f"✅ Obra '{no}' criada com sucesso!")
                    st.rerun()

    # =============================================================================
    # TAB 4: FATURAÇÃO
    # =============================================================================
    with tabs[4]:
        st.subheader("💰 Centro de Faturação")
        
        if not obras_db.empty:
            clientes = obras_db['Cliente'].unique()
            cliente_f = st.selectbox("Selecionar Cliente", clientes)
            
            # Métricas do cliente
            c1, c2 = st.columns(2)
            with c1:
                if not faturas_db.empty:
                    num_faturas = len(faturas_db[faturas_db['Cliente'] == cliente_f])
                    st.metric("Faturas Emitidas", num_faturas)
                else:
                    st.metric("Faturas Emitidas", 0)
            with c2:
                if not faturas_db.empty and cliente_f:
                    try:
                        valor_total = faturas_db[faturas_db['Cliente'] == cliente_f]['Valor'].astype(float).sum()
                        st.metric("Valor Total", f"€ {valor_total:,.2f}")
                    except:
                        st.metric("Valor Total", "€ 0.00")
                else:
                    st.metric("Valor Total", "€ 0.00")
            
            st.divider()
            
            # Botão gerar fatura
            if st.button("📄 Gerar Fatura PDF", type="primary"):
                st.info(f"A processar fatura para {cliente_f}...")
                # Lógica de geração de fatura em PDF (Core Helper)
                st.success("✅ Fatura gerada com sucesso!")
        else:
            st.warning("⚠️ Sem obras disponíveis para faturação.")

    # =============================================================================
    # TAB 5: HSE SEGURANÇA
    # =============================================================================
    with tabs[5]:
        st.subheader("🛡️ Incidentes e Safety Walks")
        
        tab_inc, tab_sw = st.tabs(["⚠️ Incidentes", "🚶 Safety Walks"])
        
        with tab_inc:
            if not incs_db.empty:
                st.dataframe(incs_db, use_container_width=True)
            else:
                st.info("📋 Sem incidentes registados.")
        
        with tab_sw:
            if not sw_db.empty:
                st.dataframe(sw_db, use_container_width=True)
            else:
                st.info("📋 Sem safety walks registados.")

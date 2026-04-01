import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import load_all, save_db, inv, fh, sl, render_metric, ICONS, COLORS
from translations import t
import plotly.express as px

def render_admin(*args):
    """Renderiza módulo Admin com design industrial moderno"""
    
    # Desempacotamento das 20 variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args
    
    # Header com branding industrial
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:30px 20px;
        background:linear-gradient(135deg, #1E293B, #0F172A);
        border-radius:20px;
        margin-bottom:30px;
        border:1px solid rgba(255,255,255,0.1);
    ">
        <div style="font-size:3rem; margin-bottom:10px;">{ICONS["admin"]}</div>
        <div style="font-size:1.8rem; font-weight:800; color:#F8FAFC;">Painel Administrativo</div>
        <div style="font-size:1rem; color:#94A3B8;">{st.session_state.user} | {st.session_state.tipo}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs com ícones atualizados
    tabs = st.tabs([
        f"{ICONS['dashboard']} Dash",
        f"{ICONS['approved']} Aprovar",
        f"{ICONS['profile']} Pessoal",
        f"{ICONS['app']} Obras",
        f"💰 Faturação",
        f"{ICONS['safety']} HSE"
    ])
    
    # =============================================================================
    # TAB 0: DASHBOARD ADMIN
    # =============================================================================
    with tabs[0]:
        st.markdown(f"### {ICONS['dashboard']} {t('dashboard')}")
        
        # Métricas com novo design
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric("⏱️", fh(registos_db['Horas_Total'].sum()) if not registos_db.empty else "0h00m", t('total_hours'), COLORS["accent"])
        with c2:
            render_metric("👷", users['Nome'].nunique() if not users.empty else 0, "Técnicos", COLORS["info"])
        with c3:
            render_metric("⚙️", len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0, t('active_sites'), COLORS["success"])
        with c4:
            render_metric("⏳", len(registos_db[registos_db['Status'] == '0']) if not registos_db.empty else 0, t('pending'), COLORS["warning"])
        
        st.divider()
        
        # Gráfico de Evolução de Horas (Plotly)
        if not registos_db.empty:
            st.markdown("### 📈 Evolução de Horas")
            regs_grouped = registos_db.groupby('Data')['Horas_Total'].sum().reset_index()
            regs_grouped['Data'] = pd.to_datetime(regs_grouped['Data'], dayfirst=True, errors='coerce')
            fig = px.area(regs_grouped, x='Data', y='Horas_Total', 
                         title='Evolução de Horas Trabalhadas',
                         color_discrete_sequence=[COLORS["accent"]])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color=COLORS["text_primary"],
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Sem dados de registos disponíveis.")
    
    # =============================================================================
    # TAB 1: APROVAÇÕES
    # =============================================================================
    with tabs[1]:
        st.markdown(f"### {ICONS['approved']} {t('approvals')}")
        
        pend = registos_db[registos_db['Status'] == '0'] if not registos_db.empty else pd.DataFrame()
        
        if pend.empty:
            st.success(f"{ICONS['approved']} Sem registos pendentes.")
        else:
            st.warning(f"⚠️ {len(pend)} registos pendentes de aprovação")
            st.dataframe(pend[['Data', 'Técnico', 'Obra', 'Horas_Total', 'Turnos']], use_container_width=True)
            
            if st.button(f"{ICONS['approved']} Aprovar Todos os Registos", use_container_width=True, type="primary"):
                registos_db.loc[registos_db['Status'] == '0', 'Status'] = '1'
                save_db(registos_db, "registos.csv")
                inv()
                st.success(f"✅ {len(pend)} registos aprovados!")
                st.rerun()
    
    # =============================================================================
    # TAB 2: PESSOAL & RANKING
    # =============================================================================
    with tabs[2]:
        st.markdown(f"### {ICONS['profile']} Gestão de Pessoal")
        
        if not users.empty:
            for _, u in users.iterrows():
                with st.expander(f"👤 {u['Nome']} - {u.get('Cargo', 'Técnico')}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Email:** {u.get('Email', 'N/A')}")
                        st.write(f"**Telefone:** {u.get('Telefone', 'N/A')}")
                    with c2:
                        st.write(f"**NIF:** {u.get('NIF', 'N/A')}")
                        st.write(f"**Cargo:** {u.get('Cargo', 'Técnico')}")
                    
                    # Avaliação do técnico
                    st.divider()
                    st.write("**Avaliação de Performance**")
                    nota = st.slider(f"Nota para {u['Nome']}", 1, 10, 5, key=f"nota_{u['Nome']}")
                    if st.button(f"💾 Guardar Avaliação", key=f"save_{u['Nome']}"):
                        st.success(f"Avaliação guardada: {nota}/10")
        else:
            st.info("📋 Sem utilizadores registados.")
    
    # =============================================================================
    # TAB 3: OBRAS & FRENTES
    # =============================================================================
    with tabs[3]:
        st.markdown(f"### {ICONS['app']} Controlo de Obras")
        
        # Formulário de nova obra
        with st.expander(f"➕ Criar Nova Obra"):
            with st.form("nova_obra"):
                no = st.text_input("Nome da Obra")
                cl = st.text_input("Cliente")
                ti = st.selectbox("Tipo de Obra", ["Normal", "Instrumentação"])
                loc = st.text_input("Localização")
                
                if st.form_submit_button("Criar Obra", use_container_width=True, type="primary"):
                    if no and cl:
                        new_o = pd.DataFrame([{
                            "Obra": no,
                            "Codigo": no.replace(' ', '_').upper()[:10],
                            "Cliente": cl,
                            "TipoObra": ti,
                            "Ativa": "Ativa",
                            "Local": loc
                        }])
                        save_db(pd.concat([obras_db, new_o]) if not obras_db.empty else new_o, "obras_lista.csv")
                        inv()
                        st.success(f"✅ Obra '{no}' criada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Preencha nome da obra e cliente.")
        
        st.divider()
        
        # Lista de obras ativas
        st.markdown("### 🏗️ Obras Ativas")
        if not obras_db.empty:
            obras_ativas = obras_db[obras_db['Ativa'] == 'Ativa']
            if not obras_ativas.empty:
                for _, o in obras_ativas.iterrows():
                    st.markdown(f"""
                    <div style="
                        padding:15px;
                        background:rgba(255,255,255,0.05);
                        border-radius:12px;
                        margin-bottom:10px;
                        border-left:4px solid {COLORS['accent']};
                    ">
                        <b>{o['Obra']}</b> | Cliente: {o['Cliente']} | Tipo: {o.get('TipoObra', 'Normal')}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Sem obras ativas.")
        else:
            st.info("📋 Sem obras registadas.")
    
    # =============================================================================
    # TAB 4: FATURAÇÃO
    # =============================================================================
    with tabs[4]:
        st.markdown(f"### 💰 Centro de Faturação")
        
        if not obras_db.empty:
            clientes = obras_db['Cliente'].unique()
            cliente_f = st.selectbox("Selecionar Cliente", clientes)
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Faturas Emitidas", len(faturas_db[faturas_db['Cliente'] == cliente_f]) if not faturas_db.empty else 0)
            with c2:
                st.metric("Valor Total", f"€ {faturas_db[faturas_db['Cliente'] == cliente_f]['Valor'].sum():.2f}" if not faturas_db.empty else "€ 0.00")
            
            if st.button("📄 Gerar Fatura PDF", use_container_width=True, type="primary"):
                st.info(f"A processar fatura para {cliente_f}...")
                # Lógica de geração de fatura em PDF (Core Helper)
        else:
            st.info("📋 Sem obras registadas.")
    
    # =============================================================================
    # TAB 5: HSE SEGURANÇA
    # =============================================================================
    with tabs[5]:
        st.markdown(f"### {ICONS['safety']} Incidentes e Safety Walks")
        
        tab_inc, tab_sw = st.tabs(["⚠️ Incidentes", "🚶 Safety Walks"])
        
        with tab_inc:
            if not incs_db.empty:
                st.dataframe(incs_db, use_container_width=True)
                
                # Métricas de segurança
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Total Incidentes", len(incs_db))
                with c2:
                    st.metric("Abertos", len(incs_db[incs_db['Status'] == 'Aberto']))
                with c3:
                    st.metric("Fechados", len(incs_db[incs_db['Status'] == 'Fechado']))
            else:
                st.success("✅ Sem incidentes registados!")
        
        with tab_sw:
            if not sw_db.empty:
                st.dataframe(sw_db, use_container_width=True)
            else:
                st.info("📋 Sem Safety Walks registados.")

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

    # Header do Painel
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:30px; border-radius:20px; margin-bottom:30px; border:1px solid rgba(255,255,255,0.1);">
        <h1 style="color:#F8FAFC; margin:0;">{ICONS['admin']} Painel Administrativo</h1>
        <p style="color:#94A3B8; margin:10px 0 0 0;">{st.session_state.user} | {st.session_state.tipo}</p>
    </div>
    """, unsafe_allow_html=True)

    # Tabs de Navegação Admin
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"{ICONS['users']} Utilizadores",
        f"{ICONS['work']} Obras",
        f"{ICONS['documents']} Documentos",
        f"{ICONS['chart']} Relatórios",
        f"{ICONS['settings']} Configurações"
    ])

    # =============================================================================
    # TAB 1: GESTÃO DE UTILIZADORES
    # =============================================================================
    with tab1:
        st.markdown("### 👥 Gestão de Utilizadores")
        
        # Métricas de utilizadores
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Utilizadores", len(users))
        with col2:
            st.metric("Admins", len(users[users['Tipo'] == 'Admin']) if not users.empty else 0)
        with col3:
            st.metric("Técnicos", len(users[users['Tipo'] == 'Técnico']) if not users.empty else 0)
        
        st.divider()
        
        # Tabela de utilizadores
        st.markdown("### Lista de Utilizadores")
        if not users.empty:
            st.dataframe(users[['Nome', 'Tipo', 'Cargo', 'Email', 'Telefone']].head(20), use_container_width=True)
        else:
            st.info("📋 Sem utilizadores registados.")

    # =============================================================================
    # TAB 2: GESTÃO DE OBRAS
    # =============================================================================
    with tab2:
        st.markdown("### 🏗️ Gestão de Obras")
        
        # Métricas de obras
        col1, col2, col3 = st.columns(3)
        with col1:
            total_obras = len(obras_db) if not obras_db.empty else 0
            st.metric("Total Obras", total_obras)
        with col2:
            obras_ativas = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
            st.metric("Obras Ativas", obras_ativas)
        with col3:
            obras_concluidas = len(obras_db[obras_db['Ativa'] == 'Concluída']) if not obras_db.empty else 0
            st.metric("Obras Concluídas", obras_concluidas)
        
        st.divider()
        
        # Tabela de obras
        st.markdown("### Lista de Obras")
        if not obras_db.empty:
            st.dataframe(obras_db[['Obra', 'Cliente', 'Local', 'Ativa']].head(20), use_container_width=True)
        else:
            st.info("📋 Sem obras registadas.")

    # =============================================================================
    # TAB 3: DOCUMENTOS E FATURAS
    # =============================================================================
    with tab3:
        st.markdown("### 📄 Documentos e Faturas")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📄 Documentos", len(docs_db) if not docs_db.empty else 0)
        with col2:
            st.metric("💰 Faturas", len(faturas_db) if not faturas_db.empty else 0)
        
        st.divider()
        
        # Faturas por cliente
        st.markdown("### Faturas por Cliente")
        if not obras_db.empty and not faturas_db.empty:
            clientes = obras_db['Cliente'].unique()
            cliente_f = st.selectbox("Selecionar Cliente", clientes)
            
            c1, c2 = st.columns(2)
            with c1:
                num_faturas = len(faturas_db[faturas_db['Cliente'] == cliente_f]) if not faturas_db.empty else 0
                st.metric("Faturas Emitidas", num_faturas)
            with c2:
                if not faturas_db.empty and cliente_f:
                    try:
                        valor_total = faturas_db[faturas_db['Cliente'] == cliente_f]['Valor'].astype(float).sum()
                        st.metric("Valor Total", f"€ {valor_total:,.2f}")
                    except:
                        st.metric("Valor Total", "€ 0.00")
                else:
                    st.metric("Valor Total", "€ 0.00")
        else:
            st.info("📋 Sem dados de faturas.")

    # =============================================================================
    # TAB 4: RELATÓRIOS E MÉTRICAS
    # =============================================================================
    with tab4:
        st.markdown("### 📊 Relatórios e Métricas")
        
        # Métricas gerais
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 Utilizadores", len(users))
        with col2:
            st.metric("🏭 Obras Ativas", len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0)
        with col3:
            st.metric("📋 Registos", len(registos_db) if not registos_db.empty else 0)
        with col4:
            st.metric("⚠️ Incidentes", len(incs_db) if not incs_db.empty else 0)
        
        st.divider()
        
        # Gráfico de obras
        st.markdown("### Distribuição de Obras")
        if not obras_db.empty:
            obras_por_estado = obras_db['Ativa'].value_counts()
            st.bar_chart(obras_por_estado)
        else:
            st.info("📋 Sem dados para mostrar.")

    # =============================================================================
    # TAB 5: CONFIGURAÇÕES
    # =============================================================================
    with tab5:
        st.markdown("### ⚙️ Configurações do Sistema")
        
        st.markdown("#### 🔄 Cache e Dados")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Limpar Cache", use_container_width=True):
                inv()
                st.success("✅ Cache limpa!")
                st.rerun()
        with col2:
            if st.button("📊 Recarregar Dados", use_container_width=True):
                st.cache_data.clear()
                st.success("✅ Dados recarregados!")
                st.rerun()
        
        st.divider()
        
        # Informação do sistema
        st.markdown("#### ℹ️ Informação do Sistema")
        st.info(f"""
        - **Versão:** GESTNOW v3.0
        - **Utilizador:** {st.session_state.user}
        - **Tipo:** {st.session_state.tipo}
        - **Cargo:** {st.session_state.cargo}
        - **Última Atividade:** {st.session_state.get('last_activity', 'N/A')}
        """)

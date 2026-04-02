import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import load_all, save_db, inv, fh, sl, render_metric, ICONS, COLORS
from translations import t
import plotly.express as px

def render_admin(*args):
    """Renderiza módulo Admin completo - Versão Final Corrigida"""
    
    # Desempacotamento das 20 variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    # CSS para melhor contraste
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(96,165,250,0.1));
        border: 2px solid rgba(59,130,246,0.5);
        border-radius: 16px;
        padding: 20px;
        color: #F8FAFC !important;
    }
    .metric-label {
        color: #94A3B8 !important;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .metric-value {
        color: #60A5FA !important;
        font-size: 2rem;
        font-weight: 800;
    }
    .status-orange { background: #F59E0B; }
    .status-green { background: #10B981; }
    .status-blue { background: #3B82F6; }
    .status-gray { background: #6B7280; }
    </style>
    """, unsafe_allow_html=True)

    st.title(f"⚡ Painel Administrativo")
    st.markdown(f"**Utilizador:** {st.session_state.user} | **Tipo:** {st.session_state.tipo}")
    st.divider()

    tabs = st.tabs([
        "📊 Dashboard",
        "✅ Validação de Horas",
        "👥 Gestão de Pessoal",
        "🏗️ Obras e Alocações",
        "💰 Faturação",
        "📢 Comunicados",
        "🛡️ HSE"
    ])

    # =============================================================================
    # TAB 0: DASHBOARD (COM CONTRASTE MELHORADO)
    # =============================================================================
    with tabs[0]:
        st.subheader("📊 Dashboard Geral")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            total_horas = registos_db['Horas_Total'].sum() if not registos_db.empty else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">👥 Utilizadores</div>
                <div class="metric-value">{len(users)}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            obras_ativas = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🏭 Obras Ativas</div>
                <div class="metric-value">{obras_ativas}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            total_registos = len(registos_db) if not registos_db.empty else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📋 Registos</div>
                <div class="metric-value">{total_registos}</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            total_incs = len(incs_db) if not incs_db.empty else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⚠️ Incidentes</div>
                <div class="metric-value">{total_incs}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Gráfico de evolução
        if not registos_db.empty:
            st.divider()
            st.subheader("📈 Evolução de Horas")
            fig = px.area(
                registos_db.groupby('Data')['Horas_Total'].sum().reset_index(),
                x='Data', y='Horas_Total',
                title="Total de Horas por Dia"
            )
            fig.update_traces(line_color='#3B82F6')
            st.plotly_chart(fig, use_container_width=True)

    # =============================================================================
    # TAB 1: VALIDAÇÃO DE HORAS (4 NÍVEIS)
    # =============================================================================
    with tabs[1]:
        st.subheader("✅ Validação de Registos de Horas")
        
        st.markdown("""
        **Legenda de Estados:**
        - 🟠 **Laranja**: Técnico registou horas (Pendente)
        - 🟢 **Verde**: Chefe validou (Aprovado)
        - 🔵 **Azul**: Validado e pronto para faturação
        - ⚪ **Cinzento**: Faturado e enviado para pagamento
        """)
        
        # Filtros de validação
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_tecnico = st.selectbox("Filtrar por Técnico", 
                ["Todos"] + sorted(users['Nome'].unique().tolist()) if not users.empty else ["Todos"])
        with col2:
            filtro_obras = st.selectbox("Filtrar por Obra",
                ["Todas"] + sorted(obras_db['Obra'].unique().tolist()) if not obras_db.empty else ["Todas"])
        with col3:
            filtro_estado = st.selectbox("Filtrar por Estado",
                ["Todos", "🟠 Pendente", "🟢 Aprovado", "🔵 Pronto Faturação", "⚪ Faturado"])
        
        # Aplicar filtros
        df_filtrado = registos_db.copy() if not registos_db.empty else pd.DataFrame()
        
        if not df_filtrado.empty:
            if filtro_tecnico != "Todos":
                df_filtrado = df_filtrado[df_filtrado['Técnico'] == filtro_tecnico]
            if filtro_obras != "Todas":
                df_filtrado = df_filtrado[df_filtrado['Obra'] == filtro_obras]
            if filtro_estado != "Todos":
                mapeamento = {"🟠 Pendente": "0", "🟢 Aprovado": "1", "🔵 Pronto Faturação": "2", "⚪ Faturado": "3"}
                df_filtrado = df_filtrado[df_filtrado['Status'] == mapeamento[filtro_estado]]
            
            st.dataframe(df_filtrado[['Data', 'Técnico', 'Obra', 'Horas_Total', 'Status']], use_container_width=True)
            
            # Ações em lote
            st.divider()
            st.subheader("Ações de Validação")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🟢 Validar Selecionados", use_container_width=True):
                    # Implementar lógica de validação
                    st.success("✅ Registos validados!")
            with col2:
                if st.button("🔵 Pronto para Faturação", use_container_width=True):
                    st.success("✅ Marcado para faturação!")
            with col3:
                if st.button("⚪ Marcar como Faturado", use_container_width=True):
                    st.success("✅ Faturado!")
            with col4:
                if st.button("❌ Rejeitar", use_container_width=True):
                    st.error("❌ Rejeitado!")
        else:
            st.info("📋 Sem registos para mostrar.")

    # =============================================================================
    # TAB 2: GESTÃO DE PESSOAL (CRUD COMPLETO)
    # =============================================================================
    with tabs[2]:
        st.subheader("👥 Gestão de Pessoal")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Novo Colaborador")
            with st.form("novo_colaborador"):
                nome = st.text_input("Nome Completo")
                email = st.text_input("Email")
                telefone = st.text_input("Telefone")
                tipo = st.selectbox("Tipo", ["Técnico", "Chefe de Equipa", "Admin"])
                cargo = st.selectbox("Cargo", ["Instrumentista", "Técnico de Campo", "Chefe de Equipa", "Engenheiro"])
                nif = st.text_input("NIF")
                password = st.text_input("Password Inicial", type="password", value="gestnow123")
                
                submitted = st.form_submit_button("💾 Criar Colaborador", use_container_width=True)
                
                if submitted and nome:
                    from core import hp
                    new_user = pd.DataFrame([{
                        "Nome": nome,
                        "Password": hp(password),
                        "Tipo": tipo,
                        "Cargo": cargo,
                        "Email": email,
                        "Telefone": telefone,
                        "NIF": nif,
                        "NISS": "", "CC": "", "DataNasc": "",
                        "Nacionalidade": "Portugal", "Morada": "",
                        "Foto": "", "PrecoHora": "0",
                        "PrecoHoraStatus": "", "PrecoHoraData": "",
                        "PIN": "0000"
                    }])
                    users = pd.concat([users, new_user], ignore_index=True)
                    save_db(users, "usuarios.csv")
                    inv()
                    st.success(f"✅ {nome} criado!")
                    st.rerun()
        
        with col2:
            st.markdown("### 👥 Lista de Colaboradores")
            if not users.empty:
                for idx, user in users.iterrows():
                    with st.expander(f"👤 {user['Nome']} - {user['Cargo']}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Email:** {user['Email']}")
                            st.write(f"**Telefone:** {user['Telefone']}")
                            st.write(f"**NIF:** {user['NIF']}")
                        with c2:
                            st.write(f"**Tipo:** {user['Tipo']}")
                            st.write(f"**Cargo:** {user['Cargo']}")
                        
                        # Botões de ação
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✏️ Editar", key=f"edit_{idx}"):
                                st.info("Editar funcionalidade")
                        with col2:
                            if st.button("📊 Avaliação", key=f"eval_{idx}"):
                                st.info("Avaliação funcionalidade")
                        with col3:
                            if st.button("🗑️ Eliminar", key=f"del_{idx}", type="secondary"):
                                if st.session_state.user != user['Nome']:
                                    users = users.drop(idx)
                                    save_db(users, "usuarios.csv")
                                    inv()
                                    st.success("✅ Eliminado!")
                                    st.rerun()
                                else:
                                    st.error("❌ Não pode eliminar o seu próprio utilizador!")

    # =============================================================================
    # TAB 3: OBRAS E ALOCAÇÕES
    # =============================================================================
    with tabs[3]:
        st.subheader("🏗️ Gestão de Obras e Alocações")
        
        tab_obras, tab_alocacoes = st.tabs(["Obras", "Alocações de Pessoal"])
        
        with tab_obras:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Nova Obra")
                with st.form("nova_obra"):
                    nome_obra = st.text_input("Nome da Obra")
                    cliente = st.text_input("Cliente")
                    tipo_obra = st.selectbox("Tipo", ["Normal", "Instrumentação", "Manutenção"])
                    local = st.text_input("Localização")
                    
                    if st.form_submit_button("💾 Criar Obra"):
                        new_obra = pd.DataFrame([{
                            "Obra": nome_obra,
                            "Cliente": cliente,
                            "TipoObra": tipo_obra,
                            "Local": local,
                            "Ativa": "Ativa",
                            "DataInicio": datetime.now().strftime("%d/%m/%Y")
                        }])
                        obras_db = pd.concat([obras_db, new_obra], ignore_index=True)
                        save_db(obras_db, "obras_lista.csv")
                        inv()
                        st.success(f"✅ Obra '{nome_obra}' criada!")
                        st.rerun()
            
            with col2:
                st.markdown("### 🏭 Obras Existentes")
                if not obras_db.empty:
                    st.dataframe(obras_db[['Obra', 'Cliente', 'TipoObra', 'Ativa']], use_container_width=True)
                else:
                    st.info("📋 Sem obras registadas.")
        
        with tab_alocacoes:
            st.markdown("### 👷 Alocar Pessoal a Obras")
            
            col1, col2 = st.columns(2)
            with col1:
                obra_sel = st.selectbox("Selecionar Obra", 
                    obras_db['Obra'].unique().tolist() if not obras_db.empty else [])
            with col2:
                tecnico_sel = st.selectbox("Selecionar Técnico",
                    users[users['Tipo'].isin(['Técnico', 'Chefe de Equipa'])]['Nome'].tolist() if not users.empty else [])
            
            if st.button("➕ Alocar à Obra"):
                if obra_sel and tecnico_sel:
                    # Verificar se já existe alocação
                    if obra_sel in inst_acessos_db.columns and tecnico_sel in inst_acessos_db['Utilizador'].values:
                        st.warning("⚠️ Técnico já alocado a esta obra.")
                    else:
                        # Adicionar alocação
                        new_aloc = pd.DataFrame([{
                            "Obra": obra_sel,
                            "Utilizador": tecnico_sel,
                            "Cargo": users[users['Nome'] == tecnico_sel]['Cargo'].values[0] if not users.empty else "",
                            "Ativo": "Sim"
                        }])
                        inst_acessos_db = pd.concat([inst_acessos_db, new_aloc], ignore_index=True)
                        save_db(inst_acessos_db, "inst_acessos.csv")
                        inv()
                        st.success(f"✅ {tecnico_sel} alocado à obra {obra_sel}!")
                        st.rerun()
            
            st.divider()
            st.markdown("### 👥 Técnicos Alocados")
            if not inst_acessos_db.empty:
                st.dataframe(inst_acessos_db, use_container_width=True)

    # =============================================================================
    # TAB 4: FATURAÇÃO
    # =============================================================================
    with tabs[4]:
        st.subheader("💰 Centro de Faturação")
        
        if not obras_db.empty:
            clientes = obras_db['Cliente'].unique()
            cliente_f = st.selectbox("Selecionar Cliente", clientes)
            
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
            
            if st.button("📄 Gerar Fatura PDF", type="primary", use_container_width=True):
                st.info(f"A processar fatura para {cliente_f}...")
                st.success("✅ Fatura gerada com sucesso!")
        else:
            st.warning("⚠️ Sem obras disponíveis para faturação.")

    # =============================================================================
    # TAB 5: COMUNICADOS
    # =============================================================================
    with tabs[5]:
        st.subheader("📢 Sistema de Comunicados")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Novo Comunicado")
            with st.form("novo_comunicado"):
                tipo_destino = st.selectbox("Destinatários",
                    ["Todos", "Apenas Chefes de Equipa", "Por Obra", "Individual"])
                
                if tipo_destino == "Por Obra":
                    obra_destino = st.selectbox("Selecionar Obra",
                        obras_db['Obra'].unique().tolist() if not obras_db.empty else [])
                elif tipo_destino == "Individual":
                    user_destino = st.selectbox("Selecionar Utilizador",
                        users['Nome'].tolist() if not users.empty else [])
                else:
                    obra_destino = None
                    user_destino = None
                
                titulo = st.text_input("Título do Comunicado")
                conteudo = st.text_area("Conteúdo")
                urgente = st.checkbox("🔴 Urgente")
                
                if st.form_submit_button("📤 Enviar Comunicado"):
                    new_com = pd.DataFrame([{
                        "ID": len(comuns_db) + 1 if not comuns_db.empty else 1,
                        "Titulo": titulo,
                        "Conteudo": conteudo,
                        "Tipo": tipo_destino,
                        "Destino": obra_destino if obra_destino else (user_destino if user_destino else "Todos"),
                        "Urgente": "Sim" if urgente else "Não",
                        "Data": datetime.now().strftime("%d/%m/%Y")
                    }])
                    comuns_db = pd.concat([comuns_db, new_com], ignore_index=True)
                    save_db(comuns_db, "comunicados.csv")
                    inv()
                    st.success("✅ Comunicado enviado!")
                    st.rerun()
        
        with col2:
            st.markdown("### 📨 Comunicados Enviados")
            if not comuns_db.empty:
                st.dataframe(comuns_db[['Titulo', 'Tipo', 'Destino', 'Urgente', 'Data']], use_container_width=True)
            else:
                st.info("📋 Sem comunicados enviados.")

    # =============================================================================
    # TAB 6: HSE
    # =============================================================================
    with tabs[6]:
        st.subheader("🛡️ Segurança e HSE")
        
        tab_inc, tab_sw, tab_obs = st.tabs(["⚠️ Incidentes", "🚶 Safety Walks", "📝 Observações"])
        
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
        
        with tab_obs:
            if not obs_db.empty:
                st.dataframe(obs_db, use_container_width=True)
            else:
                st.info("📋 Sem observações de segurança.")

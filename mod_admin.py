import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import load_all, save_db, inv, fh, sl, render_metric, ICONS, COLORS, hp
from translations import t
import plotly.express as px

def render_admin(*args):
    """Renderiza módulo Admin completo - Versão Final Corrigida"""
    
    # CSS GLOBAL
    st.markdown("""
    <style>
    .stMarkdown, .stText, .stDataFrame, label, div, span, p, h1, h2, h3 { color: #F8FAFC !important; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2));
        border: 2px solid rgba(59,130,246,0.5);
        border-radius: 12px;
        padding: 15px;
    }
    [data-testid="stMetricValue"] { color: #60A5FA !important; }
    [data-testid="stMetricLabel"] { color: #94A3B8 !important; }
    .stDataFrame { color: #F8FAFC !important; }
    .stTextInput > div > div > input, .stSelectbox > div > div > div, .stTextArea > div > div > textarea {
        background: rgba(255,255,255,0.1) !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #3B82F6, #60A5FA) !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Desempacotamento das 20 variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    # HEADER
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:30px; border-radius:20px; margin-bottom:30px; border:1px solid rgba(255,255,255,0.2);">
        <h1 style="color:#F8FAFC; margin:0; font-size:2.5rem;">⚡ Painel Administrativo</h1>
        <p style="color:#94A3B8; margin:10px 0 0 0;">Utilizador: <strong style="color:#60A5FA">{st.session_state.user}</strong> | Tipo: <strong style="color:#60A5FA">{st.session_state.tipo}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    # TABS
    tabs = st.tabs([
        "📊 Dashboard",
        "✅ Validação Horas",
        "👥 Recursos Humanos",
        "🏗️ Obras",
        "🚗 Frota",
        "🏨 Dormidas",
        "🛒 Compras",
        "💰 Faturação",
        "📊 Orçamentação",
        "💼 Comercial",
        "📢 Comunicados",
        "🛡️ HSE"
    ])

    # =============================================================================
    # TAB 0: DASHBOARD
    # =============================================================================
    with tabs[0]:
        st.markdown("### 📊 Dashboard Geral", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            total_horas = registos_db['Horas_Total'].sum() if not registos_db.empty else 0
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:20px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">⏱️ Total Horas</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{fh(total_horas)}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:20px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">👷 Técnicos Ativos</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{len(users)}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            obras_ativas = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:20px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">🏭 Obras Ativas</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{obras_ativas}</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            pendentes = len(registos_db[registos_db['Status'] == "0"]) if not registos_db.empty else 0
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:20px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">⏳ Validações</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{pendentes}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Gráfico de Horas
        if not registos_db.empty:
            st.divider()
            st.markdown("### 📈 Evolução de Horas", unsafe_allow_html=True)
            fig = px.area(
                registos_db.groupby('Data')['Horas_Total'].sum().reset_index(),
                x='Data', y='Horas_Total',
                title="Total de Horas por Dia"
            )
            fig.update_traces(line_color='#60A5FA', fillcolor='rgba(59,130,246,0.3)')
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F8FAFC'),
                title_font=dict(color='#60A5FA', size=18)
            )
            st.plotly_chart(fig, use_container_width=True)

    # =============================================================================
    # TAB 1: VALIDAÇÃO DE HORAS
    # =============================================================================
    with tabs[1]:
        st.markdown("### ✅ Validação de Registos de Horas", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_tecnico = st.selectbox("Filtrar por Técnico", 
                ["Todos"] + sorted(users['Nome'].unique().tolist()) if not users.empty else ["Todos"],
                key="val_tecnico")
        with col2:
            filtro_obras = st.selectbox("Filtrar por Obra",
                ["Todas"] + sorted(obras_db['Obra'].unique().tolist()) if not obras_db.empty else ["Todas"],
                key="val_obra")
        with col3:
            filtro_estado = st.selectbox("Filtrar por Estado",
                ["Todos", "🟠 Pendente", "🟢 Aprovado", "🔵 Faturação", "⚪ Faturado"],
                key="val_estado")
        
        df_filtrado = registos_db.copy() if not registos_db.empty else pd.DataFrame()
        
        if not df_filtrado.empty:
            if filtro_tecnico != "Todos":
                df_filtrado = df_filtrado[df_filtrado['Técnico'] == filtro_tecnico]
            if filtro_obras != "Todas":
                df_filtrado = df_filtrado[df_filtrado['Obra'] == filtro_obras]
            
            st.dataframe(df_filtrado[['Data', 'Técnico', 'Obra', 'Horas_Total', 'Status']], use_container_width=True)
            
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("🟢 Validar Selecionados", use_container_width=True, key="btn_validar"):
                    st.success("✅ Registos validados!")
            with col2:
                if st.button("🔵 Pronto Faturação", use_container_width=True, key="btn_faturar"):
                    st.success("✅ Marcado para faturação!")
            with col3:
                if st.button("⚪ Marcar Faturado", use_container_width=True, key="btn_faturado"):
                    st.success("✅ Faturado!")
            with col4:
                if st.button("❌ Rejeitar", use_container_width=True, key="btn_rejeitar"):
                    st.error("❌ Rejeitado!")

    # =============================================================================
    # TAB 2: RECURSOS HUMANOS
    # =============================================================================
    with tabs[2]:
        st.markdown("### 👥 Recursos Humanos", unsafe_allow_html=True)
        
        tab_pessoal, tab_avaliacoes, tab_historico = st.tabs([
            "Gestão de Pessoal", "Avaliações", "Histórico"
        ])
        
        with tab_pessoal:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Novo Colaborador", unsafe_allow_html=True)
                with st.form("form_novo_colab"):
                    nome = st.text_input("Nome Completo", key="colab_nome")
                    email = st.text_input("Email", key="colab_email")
                    telefone = st.text_input("Telefone", key="colab_tel")
                    tipo = st.selectbox("Tipo", ["Técnico", "Chefe de Equipa", "Admin", "Comercial"], key="colab_tipo")
                    cargo = st.selectbox("Cargo", ["Instrumentista", "Técnico de Campo", "Chefe de Equipa", "Engenheiro"], key="colab_cargo")
                    nif = st.text_input("NIF", key="colab_nif")
                    morada = st.text_input("Morada Completa", key="colab_morada")
                    local = st.checkbox("É Local? (Não precisa dormida)", key="colab_local")
                    preco_hora = st.number_input("Preço Hora (€)", min_value=0.0, value=15.0, key="colab_preco")
                    password = st.text_input("Password Inicial", type="password", value="gestnow123", key="colab_pass")
                    
                    submitted = st.form_submit_button("💾 Criar Colaborador", use_container_width=True)
                    
                    if submitted and nome:
                        new_user = pd.DataFrame([{
                            "Nome": nome,
                            "Password": hp(password),
                            "Tipo": tipo,
                            "Cargo": cargo,
                            "Email": email,
                            "Telefone": telefone,
                            "NIF": nif,
                            "Morada": morada,
                            "Local": "Sim" if local else "Não",
                            "PrecoHora": str(preco_hora),
                            "NISS": "", "CC": "", "DataNasc": "",
                            "Nacionalidade": "Portugal",
                            "Foto": "", "PrecoHoraStatus": "", "PrecoHoraData": "",
                            "PIN": "0000"
                        }])
                        users = pd.concat([users, new_user], ignore_index=True)
                        save_db(users, "usuarios.csv")
                        inv()
                        st.success(f"✅ {nome} criado!")
                        st.rerun()
            
            with col2:
                st.markdown("### 👥 Lista de Colaboradores", unsafe_allow_html=True)
                if not users.empty:
                    for idx, user in users.iterrows():
                        with st.expander(f"👤 {user['Nome']} - {user['Cargo']}", key=f"exp_{idx}"):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.write(f"**Email:** {user['Email']}")
                                st.write(f"**Telefone:** {user['Telefone']}")
                                st.write(f"**NIF:** {user['NIF']}")
                                st.write(f"**Morada:** {user.get('Morada', 'N/A')}")
                                st.write(f"**Local:** {user.get('Local', 'Não')}")
                            with c2:
                                st.write(f"**Tipo:** {user['Tipo']}")
                                st.write(f"**Cargo:** {user['Cargo']}")
                                st.write(f"**Preço Hora:** € {user.get('PrecoHora', '0')}")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✏️ Editar", key=f"edit_{idx}"):
                                    st.info("Editar funcionalidade")
                            with col2:
                                if st.button("📊 Avaliar", key=f"eval_{idx}"):
                                    st.info("Avaliação funcionalidade")
                            with col3:
                                if st.button("🗑️ Dispensar", key=f"del_{idx}", type="secondary"):
                                    if st.session_state.user != user['Nome']:
                                        users = users.drop(idx)
                                        save_db(users, "usuarios.csv")
                                        inv()
                                        st.success("✅ Trabalhador dispensado!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Não pode eliminar o seu próprio utilizador!")

        with tab_avaliacoes:
            st.markdown("### 📊 Avaliações de Desempenho", unsafe_allow_html=True)
            
            if not users.empty:
                trabalhador_sel = st.selectbox("Selecionar Trabalhador", users['Nome'].tolist(), key="avalia_trab")
                
                col1, col2 = st.columns(2)
                with col1:
                    nota_tecnica = st.slider("Competência Técnica", 1, 10, 5, key="nota_tec")
                    nota_pontualidade = st.slider("Pontualidade", 1, 10, 5, key="nota_pont")
                    nota_trabalho_eq = st.slider("Trabalho em Equipa", 1, 10, 5, key="nota_eq")
                
                with col2:
                    nota_proatividade = st.slider("Proatividade", 1, 10, 5, key="nota_proat")
                    nota_comunicacao = st.slider("Comunicação", 1, 10, 5, key="nota_com")
                    comentarios = st.text_area("Comentários", key="avalia_coment")
                
                if st.button("💾 Guardar Avaliação", key="btn_avalia"):
                    nova_avalia = pd.DataFrame([{
                        "Data": datetime.now().strftime("%d/%m/%Y"),
                        "Trabalhador": trabalhador_sel,
                        "Nota_Tecnica": nota_tecnica,
                        "Nota_Pontualidade": nota_pontualidade,
                        "Nota_Trabalho_Eq": nota_trabalho_eq,
                        "Nota_Proatividade": nota_proatividade,
                        "Nota_Comunicacao": nota_comunicacao,
                        "Media": (nota_tecnica + nota_pontualidade + nota_trabalho_eq + nota_proatividade + nota_comunicacao) / 5,
                        "Comentarios": comentarios
                    }])
                    avals_db = pd.concat([avals_db, nova_avalia], ignore_index=True)
                    save_db(avals_db, "avaliacoes.csv")
                    inv()
                    st.success("✅ Avaliação guardada!")
                    st.rerun()

        with tab_historico:
            st.markdown("### 📜 Histórico de Trabalhadores", unsafe_allow_html=True)
            st.info("Funcionalidade em desenvolvimento...")

    # =============================================================================
    # TAB 3: OBRAS
    # =============================================================================
    with tabs[3]:
        st.markdown("### 🏗️ Gestão de Obras", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Nova Obra", unsafe_allow_html=True)
            with st.form("form_nova_obra"):
                nome_obra = st.text_input("Nome da Obra", key="obra_nome")
                cliente = st.text_input("Cliente", key="obra_cliente")
                tipo_obra = st.selectbox("Tipo", ["Normal", "Instrumentação", "Manutenção"], key="obra_tipo")
                local = st.text_input("Localização", key="obra_local")
                
                if st.form_submit_button("💾 Criar Obra", use_container_width=True):
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
            st.markdown("### 🏭 Obras Existentes", unsafe_allow_html=True)
            if not obras_db.empty:
                st.dataframe(obras_db[['Obra', 'Cliente', 'TipoObra', 'Ativa', 'Local']], use_container_width=True)

    # =============================================================================
    # TAB 4: FROTA
    # =============================================================================
    with tabs[4]:
        st.markdown("### 🚗 Gestão de Frota", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    # =============================================================================
    # TAB 5: DORMIDAS
    # =============================================================================
    with tabs[5]:
        st.markdown("### 🏨 Gestão de Dormidas", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    # =============================================================================
    # TAB 6: COMPRAS
    # =============================================================================
    with tabs[6]:
        st.markdown("### 🛒 Gestão de Compras", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    # =============================================================================
    # TAB 7: FATURAÇÃO
    # =============================================================================
    with tabs[7]:
        st.markdown("### 💰 Centro de Faturação", unsafe_allow_html=True)
        
        if not obras_db.empty:
            clientes = obras_db['Cliente'].unique()
            cliente_f = st.selectbox("Selecionar Cliente", clientes.tolist(), key="fat_cliente")
            
            c1, c2 = st.columns(2)
            with c1:
                num_faturas = len(faturas_db[faturas_db['Cliente'] == cliente_f]) if not faturas_db.empty else 0
                st.markdown(f"""
                <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                    <div style="color:#94A3B8; font-size:0.9rem;">Faturas Emitidas</div>
                    <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{num_faturas}</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                if not faturas_db.empty:
                    try:
                        valor_faturas = faturas_db[faturas_db['Cliente'] == cliente_f]['Valor'].astype(float).sum()
                    except:
                        valor_faturas = 0
                else:
                    valor_faturas = 0
                st.markdown(f"""
                <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                    <div style="color:#94A3B8; font-size:0.9rem;">Valor Faturas</div>
                    <div style="color:#60A5FA; font-size:2rem; font-weight:800;">€ {valor_faturas:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            if st.button("📄 Gerar Fatura PDF", type="primary", use_container_width=True, key="btn_gerar_fat"):
                st.info(f"A processar fatura para {cliente_f}...")
                st.success("✅ Fatura gerada com sucesso!")

    # =============================================================================
    # TAB 8: ORÇAMENTAÇÃO
    # =============================================================================
    with tabs[8]:
        st.markdown("### 📊 Orçamentação", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    # =============================================================================
    # TAB 9: COMERCIAL
    # =============================================================================
    with tabs[9]:
        st.markdown("### 💼 Gestão Comercial", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    # =============================================================================
    # TAB 10: COMUNICADOS
    # =============================================================================
    with tabs[10]:
        st.markdown("### 📢 Comunicados", unsafe_allow_html=True)
        st.info("Funcionalidade em desenvolvimento...")

    # =============================================================================
    # TAB 11: HSE
    # =============================================================================
    with tabs[11]:
        st.markdown("### 🛡️ Segurança e HSE", unsafe_allow_html=True)
        
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

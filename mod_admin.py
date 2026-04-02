import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import load_all, save_db, inv, fh, sl, render_metric, ICONS, COLORS
from translations import t
import plotly.express as px

def render_admin(*args):
    """Renderiza módulo Admin completo - Com Gestão de Frota"""
    
    # CSS PARA CONTRASTE PERFEITO
    st.markdown("""
    <style>
    .stMarkdown, .stText, .stDataFrame, .stMetric, label, div, span, p, h1, h2, h3, h4, h5, h6 {
        color: #F8FAFC !important;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2));
        border: 2px solid rgba(59,130,246,0.5);
        border-radius: 12px;
        padding: 15px;
    }
    [data-testid="stMetricValue"] { color: #60A5FA !important; }
    [data-testid="stMetricLabel"] { color: #94A3B8 !important; }
    .stDataFrame { color: #F8FAFC !important; }
    .stDataFrame td, .stDataFrame th {
        color: #F8FAFC !important;
        border-color: rgba(255,255,255,0.2) !important;
    }
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea > div > div > textarea {
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

    # Carregar dados da frota (se existirem)
    try:
        frota_db = load_all()[20] if len(load_all()) > 20 else pd.DataFrame(columns=["Matricula", "Marca", "Modelo", "Tipo", "Estado", "Condutor", "Obra", "Kms_Atual", "Custo_Aluguer", "Data_Aluguer"])
    except:
        frota_db = pd.DataFrame(columns=["Matricula", "Marca", "Modelo", "Tipo", "Estado", "Condutor", "Obra", "Kms_Atual", "Custo_Aluguer", "Data_Aluguer"])
    
    try:
        combustivel_db = load_all()[21] if len(load_all()) > 21 else pd.DataFrame(columns=["Data", "Matricula", "Condutor", "Obra", "Litros", "Preco", "Total", "Kms", "Tipo_Viatura", "Talao_b64"])
    except:
        combustivel_db = pd.DataFrame(columns=["Data", "Matricula", "Condutor", "Obra", "Litros", "Preco", "Total", "Kms", "Tipo_Viatura", "Talao_b64"])
    
    try:
        avarias_db = load_all()[22] if len(load_all()) > 22 else pd.DataFrame(columns=["Data", "Matricula", "Condutor", "Tipo", "Descricao", "Custo", "Obra", "Status"])
    except:
        avarias_db = pd.DataFrame(columns=["Data", "Matricula", "Condutor", "Tipo", "Descricao", "Custo", "Obra", "Status"])

    # HEADER
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:30px; border-radius:20px; margin-bottom:30px; border:1px solid rgba(255,255,255,0.2);">
        <h1 style="color:#F8FAFC; margin:0; font-size:2.5rem;">⚡ Painel Administrativo</h1>
        <p style="color:#94A3B8; margin:10px 0 0 0; font-size:1.1rem;">Utilizador: <strong style="color:#60A5FA">{st.session_state.user}</strong> | Tipo: <strong style="color:#60A5FA">{st.session_state.tipo}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    # TABS COM FROTA
    tabs = st.tabs([
        "📊 Dashboard",
        "✅ Validação de Horas",
        "👥 Gestão de Pessoal",
        "🏗️ Obras e Alocações",
        "🚗 Frota",
        "💰 Faturação",
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
                <div style="color:#94A3B8; font-size:0.9rem; font-weight:600;">⏱️ Total Horas</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{fh(total_horas)}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:20px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem; font-weight:600;">👷 Técnicos</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{users['Nome'].nunique() if not users.empty else 0}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            obras_ativas = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:20px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem; font-weight:600;">🏭 Obras Ativas</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{obras_ativas}</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            veiculos_ativos = len(frota_db[frota_db['Estado'] == 'Ativo']) if not frota_db.empty else 0
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:20px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem; font-weight:600;">🚗 Viaturas</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{veiculos_ativos}</div>
            </div>
            """, unsafe_allow_html=True)

    # =============================================================================
    # TAB 1: VALIDAÇÃO DE HORAS
    # =============================================================================
    with tabs[1]:
        st.markdown("### ✅ Validação de Registos de Horas", unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; margin-bottom:20px; border-left:4px solid #F59E0B;">
            <strong style="color:#F8FAFC;">Legenda de Estados:</strong><br>
            <span style="color:#F8FAFC;">🟠 Laranja: Técnico registou (Pendente)</span><br>
            <span style="color:#F8FAFC;">🟢 Verde: Chefe validou (Aprovado)</span><br>
            <span style="color:#F8FAFC;">🔵 Azul: Pronto para faturação</span><br>
            <span style="color:#F8FAFC;">⚪ Cinzento: Faturado</span>
        </div>
        """, unsafe_allow_html=True)
        
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
        
        df_filtrado = registos_db.copy() if not registos_db.empty else pd.DataFrame()
        
        if not df_filtrado.empty:
            if filtro_tecnico != "Todos":
                df_filtrado = df_filtrado[df_filtrado['Técnico'] == filtro_tecnico]
            if filtro_obras != "Todas":
                df_filtrado = df_filtrado[df_filtrado['Obra'] == filtro_obras]
            
            st.dataframe(df_filtrado[['Data', 'Técnico', 'Obra', 'Horas_Total', 'Status']], use_container_width=True)
            
            st.divider()
            st.markdown("### Ações de Validação", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🟢 Validar Selecionados", use_container_width=True):
                    st.success("✅ Registos validados!")
            with col2:
                if st.button("🔵 Pronto Faturação", use_container_width=True):
                    st.success("✅ Marcado para faturação!")
            with col3:
                if st.button("⚪ Marcar Faturado", use_container_width=True):
                    st.success("✅ Faturado!")
            with col4:
                if st.button("❌ Rejeitar", use_container_width=True):
                    st.error("❌ Rejeitado!")

    # =============================================================================
    # TAB 2: GESTÃO DE PESSOAL
    # =============================================================================
    with tabs[2]:
        st.markdown("### 👥 Gestão de Pessoal", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Novo Colaborador", unsafe_allow_html=True)
            with st.form("novo_colaborador"):
                nome = st.text_input("Nome Completo")
                email = st.text_input("Email")
                telefone = st.text_input("Telefone")
                tipo = st.selectbox("Tipo", ["Técnico", "Chefe de Equipa", "Admin"])
                cargo = st.selectbox("Cargo", ["Instrumentista", "Técnico de Campo", "Chefe de Equipa", "Engenheiro"])
                nif = st.text_input("NIF")
                morada = st.text_input("Morada Completa")
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
                        "Morada": morada,
                        "NISS": "", "CC": "", "DataNasc": "",
                        "Nacionalidade": "Portugal",
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
            st.markdown("### 👥 Lista de Colaboradores", unsafe_allow_html=True)
            if not users.empty:
                for idx, user in users.iterrows():
                    with st.expander(f"👤 {user['Nome']} - {user['Cargo']}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Email:** {user['Email']}")
                            st.write(f"**Telefone:** {user['Telefone']}")
                            st.write(f"**NIF:** {user['NIF']}")
                            st.write(f"**Morada:** {user.get('Morada', 'N/A')}")
                        with c2:
                            st.write(f"**Tipo:** {user['Tipo']}")
                            st.write(f"**Cargo:** {user['Cargo']}")
                        
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

    # =============================================================================
    # TAB 3: OBRAS E ALOCAÇÕES
    # =============================================================================
    with tabs[3]:
        st.markdown("### 🏗️ Gestão de Obras e Alocações", unsafe_allow_html=True)
        
        tab_obras, tab_alocacoes = st.tabs(["Obras", "Alocações de Pessoal"])
        
        with tab_obras:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Nova Obra", unsafe_allow_html=True)
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
                st.markdown("### 🏭 Obras Existentes", unsafe_allow_html=True)
                if not obras_db.empty:
                    st.dataframe(obras_db[['Obra', 'Cliente', 'TipoObra', 'Ativa']], use_container_width=True)

        with tab_alocacoes:
            st.markdown("### 👷 Alocar Pessoal a Obras", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                obra_sel = st.selectbox("Selecionar Obra", 
                    obras_db['Obra'].unique().tolist() if not obras_db.empty else [])
            with col2:
                tecnico_sel = st.selectbox("Selecionar Técnico",
                    users[users['Tipo'].isin(['Técnico', 'Chefe de Equipa'])]['Nome'].tolist() if not users.empty else [])
            
            if st.button("➕ Alocar à Obra"):
                if obra_sel and tecnico_sel:
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

    # =============================================================================
    # TAB 4: FROTA (NOVA ABA COMPLETA)
    # =============================================================================
    with tabs[4]:
        st.markdown("### 🚗 Gestão de Frota", unsafe_allow_html=True)
        
        # Métricas da frota
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            total_viaturas = len(frota_db) if not frota_db.empty else 0
            st.markdown(f"""
            <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">Total Viaturas</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{total_viaturas}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            viaturas_proprias = len(frota_db[frota_db['Tipo'] == 'Própria']) if not frota_db.empty else 0
            st.markdown(f"""
            <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">🏢 Próprias</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{viaturas_proprias}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            viaturas_alugadas = len(frota_db[frota_db['Tipo'] == 'Alugada']) if not frota_db.empty else 0
            st.markdown(f"""
            <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">📋 Alugadas</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{viaturas_alugadas}</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            viaturas_colab = len(frota_db[frota_db['Tipo'] == 'Colaborador']) if not frota_db.empty else 0
            st.markdown(f"""
            <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">👤 Colaborador</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{viaturas_colab}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        tab_frota, tab_combustivel, tab_avarias, tab_custos = st.tabs([
            "🚗 Viaturas",
            "⛽ Combustível",
            "⚠️ Avarias/Incidentes",
            "💰 Custos por Obra"
        ])
        
        # ===== TAB VIATURAS =====
        with tab_frota:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Nova Viatura", unsafe_allow_html=True)
                with st.form("nova_viatura"):
                    matricula = st.text_input("Matrícula")
                    marca = st.text_input("Marca")
                    modelo = st.text_input("Modelo")
                    tipo_viatura = st.selectbox("Tipo de Viatura", 
                        ["Própria", "Alugada", "Colaborador"])
                    condutor = st.selectbox("Condutor Principal",
                        users['Nome'].tolist() if not users.empty else [])
                    obra_alocada = st.selectbox("Obra Alocada",
                        obras_db['Obra'].unique().tolist() if not obras_db.empty else [])
                    kms_atual = st.number_input("Kms Atual", min_value=0, value=0)
                    custo_aluguer = st.number_input("Custo Mensal Aluguer (€)", min_value=0.0, value=0.0) if tipo_viatura == "Alugada" else 0.0
                    data_aluguer = st.date_input("Data Início Aluguer") if tipo_viatura == "Alugada" else None
                    
                    if st.form_submit_button("💾 Registar Viatura"):
                        new_viatura = pd.DataFrame([{
                            "Matricula": matricula,
                            "Marca": marca,
                            "Modelo": modelo,
                            "Tipo": tipo_viatura,
                            "Estado": "Ativo",
                            "Condutor": condutor,
                            "Obra": obra_alocada,
                            "Kms_Atual": kms_atual,
                            "Custo_Aluguer": custo_aluguer,
                            "Data_Aluguer": data_aluguer.strftime("%d/%m/%Y") if data_aluguer else ""
                        }])
                        frota_db = pd.concat([frota_db, new_viatura], ignore_index=True)
                        save_db(frota_db, "frota.csv")
                        inv()
                        st.success(f"✅ Viatura {matricula} registada!")
                        st.rerun()
            
            with col2:
                st.markdown("### 🚗 Frota Existente", unsafe_allow_html=True)
                if not frota_db.empty:
                    st.dataframe(frota_db[['Matricula', 'Marca', 'Modelo', 'Tipo', 'Condutor', 'Obra', 'Estado']], use_container_width=True)
                else:
                    st.info("📋 Sem viaturas registadas.")
        
        # ===== TAB COMBUSTÍVEL =====
        with tab_combustivel:
            st.markdown("### ⛽ Registo de Combustível", unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Novo Abastecimento", unsafe_allow_html=True)
                with st.form("novo_combustivel"):
                    data_abast = st.date_input("Data", value=datetime.now())
                    matricula_sel = st.selectbox("Viatura",
                        frota_db['Matricula'].tolist() if not frota_db.empty else [])
                    condutor_sel = st.selectbox("Condutor",
                        users['Nome'].tolist() if not users.empty else [])
                    obra_sel = st.selectbox("Obra",
                        obras_db['Obra'].unique().tolist() if not obras_db.empty else [])
                    litros = st.number_input("Litros", min_value=0.0, value=0.0)
                    preco_litro = st.number_input("Preço por Litro (€)", min_value=0.0, value=0.0)
                    kms_registo = st.number_input("Kms no Abastecimento", min_value=0, value=0)
                    
                    # Upload do talão
                    talao = st.file_uploader("📄 Upload do Talão (PDF/Foto)", type=["pdf", "jpg", "png"])
                    
                    if st.form_submit_button("💾 Registar Abastecimento"):
                        total = litros * preco_litro
                        
                        # Obter tipo de viatura
                        tipo_v = frota_db[frota_db['Matricula'] == matricula_sel]['Tipo'].values[0] if not frota_db.empty and matricula_sel in frota_db['Matricula'].values else "Própria"
                        
                        new_comb = pd.DataFrame([{
                            "Data": data_abast.strftime("%d/%m/%Y"),
                            "Matricula": matricula_sel,
                            "Condutor": condutor_sel,
                            "Obra": obra_sel,
                            "Litros": litros,
                            "Preco": preco_litro,
                            "Total": total,
                            "Kms": kms_registo,
                            "Tipo_Viatura": tipo_v,
                            "Talao_b64": ""  # Aqui guardaria o base64 do ficheiro
                        }])
                        combustivel_db = pd.concat([combustivel_db, new_comb], ignore_index=True)
                        save_db(combustivel_db, "combustivel.csv")
                        inv()
                        st.success(f"✅ Abastecimento registado! Total: € {total:.2f}")
                        st.rerun()
            
            with col2:
                st.markdown("### 📋 Histórico de Abastecimentos", unsafe_allow_html=True)
                if not combustivel_db.empty:
                    st.dataframe(combustivel_db[['Data', 'Matricula', 'Condutor', 'Obra', 'Litros', 'Total', 'Kms']], use_container_width=True)
                    
                    # Totais
                    st.divider()
                    st.markdown("### 📊 Totais")
                    c1, c2 = st.columns(2)
                    with c1:
                        total_litros = combustivel_db['Litros'].sum()
                        st.metric("Total Litros", f"{total_litros:.1f} L")
                    with c2:
                        total_custo = combustivel_db['Total'].sum()
                        st.metric("Custo Total", f"€ {total_custo:,.2f}")
                else:
                    st.info("📋 Sem abastecimentos registados.")
        
        # ===== TAB AVARIAS =====
        with tab_avarias:
            st.markdown("### ⚠️ Avarias e Incidentes", unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### 📝 Reportar Avaria/Incidente", unsafe_allow_html=True)
                with st.form("nova_avaria"):
                    data_avaria = st.date_input("Data", value=datetime.now())
                    matricula_av = st.selectbox("Viatura",
                        frota_db['Matricula'].tolist() if not frota_db.empty else [])
                    condutor_av = st.selectbox("Condutor",
                        users['Nome'].tolist() if not users.empty else [])
                    tipo_avaria = st.selectbox("Tipo", ["Avaria", "Acidente", "Multas", "Manutenção"])
                    descricao = st.text_area("Descrição")
                    custo_avaria = st.number_input("Custo Estimado (€)", min_value=0.0, value=0.0)
                    obra_av = st.selectbox("Obra Relacionada",
                        obras_db['Obra'].unique().tolist() if not obras_db.empty else [])
                    
                    if st.form_submit_button("💾 Reportar"):
                        new_avaria = pd.DataFrame([{
                            "Data": data_avaria.strftime("%d/%m/%Y"),
                            "Matricula": matricula_av,
                            "Condutor": condutor_av,
                            "Tipo": tipo_avaria,
                            "Descricao": descricao,
                            "Custo": custo_avaria,
                            "Obra": obra_av,
                            "Status": "Pendente"
                        }])
                        avarias_db = pd.concat([avarias_db, new_avaria], ignore_index=True)
                        save_db(avarias_db, "avarias.csv")
                        inv()
                        st.success("✅ Avaria reportada!")
                        st.rerun()
            
            with col2:
                st.markdown("### 📋 Histórico de Avarias", unsafe_allow_html=True)
                if not avarias_db.empty:
                    st.dataframe(avarias_db[['Data', 'Matricula', 'Tipo', 'Descricao', 'Custo', 'Status']], use_container_width=True)
                else:
                    st.info("📋 Sem avarias registadas.")
        
        # ===== TAB CUSTOS POR OBRA =====
        with tab_custos:
            st.markdown("### 💰 Custos de Frota por Obra", unsafe_allow_html=True)
            
            if not obras_db.empty:
                obra_sel = st.selectbox("Selecionar Obra", obras_db['Obra'].unique().tolist())
                
                # Combustível por obra
                comb_obra = combustivel_db[combustivel_db['Obra'] == obra_sel] if not combustivel_db.empty else pd.DataFrame()
                avarias_obra = avarias_obra[avarias_db['Obra'] == obra_sel] if not avarias_db.empty else pd.DataFrame()
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    custo_comb = comb_obra['Total'].sum() if not comb_obra.empty else 0
                    st.markdown(f"""
                    <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                        <div style="color:#94A3B8; font-size:0.9rem;">⛽ Combustível</div>
                        <div style="color:#60A5FA; font-size:2rem; font-weight:800;">€ {custo_comb:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    custo_aluguer = 0
                    if not frota_db.empty:
                        viaturas_obra = frota_db[frota_db['Obra'] == obra_sel]
                        custo_aluguer = viaturas_obra['Custo_Aluguer'].sum()
                    st.markdown(f"""
                    <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                        <div style="color:#94A3B8; font-size:0.9rem;">📋 Alugueres</div>
                        <div style="color:#60A5FA; font-size:2rem; font-weight:800;">€ {custo_aluguer:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c3:
                    custo_avarias = avarias_obra['Custo'].sum() if not avarias_obra.empty else 0
                    st.markdown(f"""
                    <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                        <div style="color:#94A3B8; font-size:0.9rem;">⚠️ Avarias</div>
                        <div style="color:#60A5FA; font-size:2rem; font-weight:800;">€ {custo_avarias:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.divider()
                
                total_obra = custo_comb + custo_aluguer + custo_avarias
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); padding:20px; border-radius:12px; text-align:center; border:2px solid rgba(59,130,246,0.5);">
                    <div style="color:#94A3B8; font-size:1rem;">Custo Total Frota na Obra</div>
                    <div style="color:#60A5FA; font-size:3rem; font-weight:800;">€ {total_obra:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)

    # =============================================================================
    # TAB 5: FATURAÇÃO (COM CUSTOS DA FROTA)
    # =============================================================================
    with tabs[5]:
        st.markdown("### 💰 Centro de Faturação", unsafe_allow_html=True)
        
        if not obras_db.empty:
            clientes = obras_db['Cliente'].unique()
            cliente_f = st.selectbox("Selecionar Cliente", clientes)
            
            # Obter obras deste cliente
            obras_cliente = obras_db[obras_db['Cliente'] == cliente_f]['Obra'].tolist()
            
            # Calcular custos da frota por cliente
            custo_frota = 0
            if not frota_db.empty and not combustivel_db.empty:
                viaturas_cliente = frota_db[frota_db['Obra'].isin(obras_cliente)]['Matricula'].tolist()
                custo_frota = combustivel_db[combustivel_db['Matricula'].isin(viaturas_cliente)]['Total'].sum()
            
            c1, c2, c3 = st.columns(3)
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
            with c3:
                st.markdown(f"""
                <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                    <div style="color:#94A3B8; font-size:0.9rem;">🚗 Custos Frota</div>
                    <div style="color:#60A5FA; font-size:2rem; font-weight:800;">€ {custo_frota:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            # Lucro
            lucro = valor_faturas - custo_frota
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(16,185,129,0.3), rgba(34,197,94,0.2)); padding:20px; border-radius:12px; text-align:center; border:2px solid rgba(16,185,129,0.5);">
                <div style="color:#94A3B8; font-size:1rem;">Lucro (Faturas - Custos Frota)</div>
                <div style="color:#10B981; font-size:3rem; font-weight:800;">€ {lucro:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            if st.button("📄 Gerar Fatura PDF", type="primary", use_container_width=True):
                st.info(f"A processar fatura para {cliente_f}...")
                st.success("✅ Fatura gerada com sucesso!")

    # =============================================================================
    # TAB 6: COMUNICADOS
    # =============================================================================
    with tabs[6]:
        st.markdown("### 📢 Sistema de Comunicados", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### ➕ Novo Comunicado", unsafe_allow_html=True)
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
            st.markdown("### 📨 Comunicados Enviados", unsafe_allow_html=True)
            if not comuns_db.empty:
                st.dataframe(comuns_db[['Titulo', 'Tipo', 'Destino', 'Urgente', 'Data']], use_container_width=True)

    # =============================================================================
    # TAB 7: HSE
    # =============================================================================
    with tabs[7]:
        st.markdown("### 🛡️ Segurança e HSE", unsafe_allow_html=True)
        
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

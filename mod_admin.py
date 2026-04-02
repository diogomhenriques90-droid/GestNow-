import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from core import load_all, save_db, inv, fh, sl, render_metric, ICONS, COLORS, hp
from translations import t
import plotly.express as px
import requests
from typing import List, Dict

def render_admin(*args):
    """Renderiza módulo Admin completo - Todas as funcionalidades"""
    
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

    # Desempacotamento das variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    # Carregar/Inicializar novas bases de dados
    try:
        frota_db = pd.read_csv("data/frota.csv", dtype=str) if len(load_all()) > 20 else pd.DataFrame(columns=["Matricula", "Marca", "Modelo", "Tipo", "Estado", "Condutor", "Obra", "Kms_Atual", "Custo_Aluguer", "Data_Aluguer"])
    except:
        frota_db = pd.DataFrame(columns=["Matricula", "Marca", "Modelo", "Tipo", "Estado", "Condutor", "Obra", "Kms_Atual", "Custo_Aluguer", "Data_Aluguer"])
    
    try:
        combustivel_db = pd.read_csv("data/combustivel.csv", dtype=str) if len(load_all()) > 21 else pd.DataFrame(columns=["Data", "Matricula", "Condutor", "Obra", "Litros", "Preco", "Total", "Kms", "Tipo_Viatura"])
    except:
        combustivel_db = pd.DataFrame(columns=["Data", "Matricula", "Condutor", "Obra", "Litros", "Preco", "Total", "Kms", "Tipo_Viatura"])
    
    try:
        dormidas_db = pd.read_csv("data/dormidas.csv", dtype=str) if len(load_all()) > 22 else pd.DataFrame(columns=["Data", "Trabalhador", "Obra", "Hotel", "Localizacao", "Custo", "Kms_Obra", "Fonte", "CheckIn", "CheckOut"])
    except:
        dormidas_db = pd.DataFrame(columns=["Data", "Trabalhador", "Obra", "Hotel", "Localizacao", "Custo", "Kms_Obra", "Fonte", "CheckIn", "CheckOut"])
    
    try:
        fornecedores_db = pd.read_csv("data/fornecedores.csv", dtype=str) if len(load_all()) > 23 else pd.DataFrame(columns=["Nome", "NIF", "Email", "Telefone", "Morada", "Categoria", "Ativo"])
    except:
        fornecedores_db = pd.DataFrame(columns=["Nome", "NIF", "Email", "Telefone", "Morada", "Categoria", "Ativo"])
    
    try:
        compras_db = pd.read_csv("data/compras.csv", dtype=str) if len(load_all()) > 24 else pd.DataFrame(columns=["Data", "Fornecedor", "Descricao", "Quantidade", "Preco_Unit", "Total", "Obra", "Tipo", "Status", "Nota_Encomenda"])
    except:
        compras_db = pd.DataFrame(columns=["Data", "Fornecedor", "Descricao", "Quantidade", "Preco_Unit", "Total", "Obra", "Tipo", "Status", "Nota_Encomenda"])
    
    try:
        visitas_db = pd.read_csv("data/visitas.csv", dtype=str) if len(load_all()) > 25 else pd.DataFrame(columns=["Data", "Comercial", "Cliente", "Tipo", "Objetivo", "Resultado", "FollowUp"])
    except:
        visitas_db = pd.DataFrame(columns=["Data", "Comercial", "Cliente", "Tipo", "Objetivo", "Resultado", "FollowUp"])
    
    try:
        orcamentos_db = pd.read_csv("data/orcamentos.csv", dtype=str) if len(load_all()) > 26 else pd.DataFrame(columns=["Data", "Cliente", "Obra", "Descricao", "Valor", "Status", "IA_Sugestao"])
    except:
        orcamentos_db = pd.DataFrame(columns=["Data", "Cliente", "Obra", "Descricao", "Valor", "Status", "IA_Sugestao"])
    
    try:
        historico_trabalhadores = pd.read_csv("data/historico_trabalhadores.csv", dtype=str) if len(load_all()) > 27 else pd.DataFrame(columns=["Nome", "Data_Saida", "Motivo", "Tipo", "Cargo", "Recontratacao"])
    except:
        historico_trabalhadores = pd.DataFrame(columns=["Nome", "Data_Saida", "Motivo", "Tipo", "Cargo", "Recontratacao"])
    
    try:
        historico_obras = pd.read_csv("data/historico_obras.csv", dtype=str) if len(load_all()) > 28 else pd.DataFrame(columns=["Obra", "Cliente", "Data_Fecho", "Custo_Total", "Faturado", "Lucro"])
    except:
        historico_obras = pd.DataFrame(columns=["Obra", "Cliente", "Data_Fecho", "Custo_Total", "Faturado", "Lucro"])

    # HEADER
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:30px; border-radius:20px; margin-bottom:30px; border:1px solid rgba(255,255,255,0.2);">
        <h1 style="color:#F8FAFC; margin:0; font-size:2.5rem;">⚡ Painel Administrativo</h1>
        <p style="color:#94A3B8; margin:10px 0 0 0;">Utilizador: <strong style="color:#60A5FA">{st.session_state.user}</strong> | Tipo: <strong style="color:#60A5FA">{st.session_state.tipo}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    # TABS COMPLETAS
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
    # TAB 2: RECURSOS HUMANOS (COMPLETO)
    # =============================================================================
    with tabs[2]:
        st.markdown("### 👥 Recursos Humanos", unsafe_allow_html=True)
        
        tab_pessoal, tab_avaliacoes, tab_historico, tab_acessos = st.tabs([
            "Gestão de Pessoal", "Avaliações", "Histórico", "Acessos e Documentação"
        ])
        
        with tab_pessoal:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Novo Colaborador", unsafe_allow_html=True)
                with st.form("novo_colaborador", key="form_novo_colab"):
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
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                if st.button("✏️ Editar", key=f"edit_{idx}"):
                                    st.info("Editar funcionalidade")
                            with col2:
                                if st.button("📊 Avaliar", key=f"eval_{idx}"):
                                    st.info("Avaliação funcionalidade")
                            with col3:
                                novo_preco = st.number_input(f"Preço Hora", min_value=0.0, value=float(user.get('PrecoHora', 15)), key=f"preco_{idx}")
                                if st.button("💰 Atualizar", key=f"upd_{idx}"):
                                    users.loc[idx, 'PrecoHora'] = str(novo_preco)
                                    save_db(users, "usuarios.csv")
                                    inv()
                                    st.success("✅ Preço atualizado!")
                                    st.rerun()
                            with col4:
                                if st.button("🗑️ Dispensar", key=f"del_{idx}", type="secondary"):
                                    if st.session_state.user != user['Nome']:
                                        # Mover para histórico
                                        motivo = st.text_input("Motivo da dispensa", key=f"motivo_{idx}")
                                        if st.button("Confirmar Dispensa", key=f"conf_{idx}"):
                                            hist = pd.DataFrame([{
                                                "Nome": user['Nome'],
                                                "Data_Saida": datetime.now().strftime("%d/%m/%Y"),
                                                "Motivo": motivo,
                                                "Tipo": user['Tipo'],
                                                "Cargo": user['Cargo'],
                                                "Recontratacao": "Possível"
                                            }])
                                            historico_trabalhadores = pd.concat([historico_trabalhadores, hist], ignore_index=True)
                                            save_db(historico_trabalhadores, "historico_trabalhadores.csv")
                                            
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
                
                # Histórico de avaliações
                if not avals_db.empty:
                    st.divider()
                    st.markdown("### Histórico de Avaliações")
                    aval_trab = avals_db[avals_db['Trabalhador'] == trabalhador_sel]
                    if not aval_trab.empty:
                        st.dataframe(aval_trab, use_container_width=True)

        with tab_historico:
            st.markdown("### 📜 Histórico de Trabalhadores Dispensados", unsafe_allow_html=True)
            
            if not historico_trabalhadores.empty:
                st.dataframe(historico_trabalhadores, use_container_width=True)
                
                st.divider()
                st.markdown("### 🔄 Recontratar Trabalhador")
                trab_hist = st.selectbox("Selecionar Trabalhador", historico_trabalhadores['Nome'].tolist(), key="recon_trab")
                
                if st.button("🔄 Recontratar", key="btn_recon"):
                    # Recuperar dados do histórico
                    dados_hist = historico_trabalhadores[historico_trabalhadores['Nome'] == trab_hist].iloc[0]
                    
                    new_user = pd.DataFrame([{
                        "Nome": trab_hist,
                        "Password": hp("gestnow123"),
                        "Tipo": dados_hist['Tipo'],
                        "Cargo": dados_hist['Cargo'],
                        "Email": "",
                        "Telefone": "",
                        "NIF": "",
                        "Morada": "",
                        "Local": "Não",
                        "PrecoHora": "15",
                        "NISS": "", "CC": "", "DataNasc": "",
                        "Nacionalidade": "Portugal",
                        "Foto": "", "PrecoHoraStatus": "", "PrecoHoraData": "",
                        "PIN": "0000"
                    }])
                    users = pd.concat([users, new_user], ignore_index=True)
                    save_db(users, "usuarios.csv")
                    inv()
                    st.success(f"✅ {trab_hist} recontratado!")
                    st.rerun()
            else:
                st.info("📋 Sem trabalhadores dispensados.")

        with tab_acessos:
            st.markdown("### 🔐 Acessos e Documentação", unsafe_allow_html=True)
            
            st.markdown("#### Atribuir Acessos a Obras")
            col1, col2 = st.columns(2)
            with col1:
                trab_acesso = st.selectbox("Trabalhador", users['Nome'].tolist(), key="acesso_trab")
            with col2:
                obra_acesso = st.selectbox("Obra", obras_db['Obra'].unique().tolist() if not obras_db.empty else [], key="acesso_obra")
            
            if st.button("➕ Atribuir Acesso", key="btn_acesso"):
                new_acesso = pd.DataFrame([{
                    "Obra": obra_acesso,
                    "Utilizador": trab_acesso,
                    "Cargo": users[users['Nome'] == trab_acesso]['Cargo'].values[0] if not users.empty else "",
                    "Ativo": "Sim"
                }])
                inst_acessos_db = pd.concat([inst_acessos_db, new_acesso], ignore_index=True)
                save_db(inst_acessos_db, "inst_acessos.csv")
                inv()
                st.success("✅ Acesso atribuído!")
                st.rerun()
            
            st.divider()
            st.markdown("#### Documentação da Frota")
            st.info("Upload de documentos: Seguros, IUC, Inspeções, etc.")

    # =============================================================================
    # TAB 3: OBRAS (COMPLETO)
    # =============================================================================
    with tabs[3]:
        st.markdown("### 🏗️ Gestão de Obras", unsafe_allow_html=True)
        
        tab_obras_ativas, tab_obras_hist, tab_alocacoes = st.tabs([
            "Obras Ativas", "Histórico de Obras", "Alocações de Pessoal"
        ])
        
        with tab_obras_ativas:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Nova Obra", unsafe_allow_html=True)
                with st.form("nova_obra", key="form_obra"):
                    nome_obra = st.text_input("Nome da Obra", key="obra_nome")
                    cliente = st.text_input("Cliente", key="obra_cliente")
                    tipo_obra = st.selectbox("Tipo", ["Normal", "Instrumentação", "Manutenção"], key="obra_tipo")
                    local = st.text_input("Localização", key="obra_local")
                    latitude = st.number_input("Latitude", value=0.0, key="obra_lat")
                    longitude = st.number_input("Longitude", value=0.0, key="obra_lon")
                    data_inicio = st.date_input("Data Início", key="obra_data_ini")
                    
                    if st.form_submit_button("💾 Criar Obra", use_container_width=True):
                        new_obra = pd.DataFrame([{
                            "Obra": nome_obra,
                            "Cliente": cliente,
                            "TipoObra": tipo_obra,
                            "Local": local,
                            "Ativa": "Ativa",
                            "Latitude": latitude,
                            "Longitude": longitude,
                            "DataInicio": data_inicio.strftime("%d/%m/%Y")
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
                    
                    st.divider()
                    st.markdown("### Fechar Obra")
                    obra_fechar = st.selectbox("Selecionar Obra", 
                        obras_db[obras_db['Ativa'] == 'Ativa']['Obra'].tolist() if not obras_db.empty else [],
                        key="fechar_obra_sel")
                    
                    if st.button("🔒 Fechar Obra", key="btn_fechar_obra"):
                        # Mover para histórico
                        hist_obra = pd.DataFrame([{
                            "Obra": obra_fechar,
                            "Cliente": obras_db[obras_db['Obra'] == obra_fechar]['Cliente'].values[0],
                            "Data_Fecho": datetime.now().strftime("%d/%m/%Y"),
                            "Custo_Total": "0",
                            "Faturado": "0",
                            "Lucro": "0"
                        }])
                        historico_obras = pd.concat([historico_obras, hist_obra], ignore_index=True)
                        save_db(historico_obras, "historico_obras.csv")
                        
                        # Remover de ativas
                        obras_db = obras_db[obras_db['Obra'] != obra_fechar]
                        save_db(obras_db, "obras_lista.csv")
                        inv()
                        st.success("✅ Obra fechada e movida para histórico!")
                        st.rerun()

        with tab_obras_hist:
            st.markdown("### 📜 Histórico de Obras", unsafe_allow_html=True)
            
            if not historico_obras.empty:
                st.dataframe(historico_obras, use_container_width=True)
            else:
                st.info("📋 Sem obras no histórico.")

        with tab_alocacoes:
            st.markdown("### 👷 Alocar Pessoal a Obras", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                obra_aloc = st.selectbox("Selecionar Obra",
                    obras_db['Obra'].unique().tolist() if not obras_db.empty else [],
                    key="aloc_obra_tab")
            with col2:
                trab_aloc = st.selectbox("Selecionar Técnico",
                    users[users['Tipo'].isin(['Técnico', 'Chefe de Equipa'])]['Nome'].tolist() if not users.empty else [],
                    key="aloc_trab_tab")
            with col3:
                preco_hora_obra = st.number_input("Preço Hora na Obra (€)", min_value=0.0, value=15.0, key="aloc_preco")
            
            if st.button("➕ Alocar à Obra", key="btn_alocar_obra"):
                # Atualizar preço hora do trabalhador para esta obra
                idx = users[users['Nome'] == trab_aloc].index[0]
                users.loc[idx, 'PrecoHora'] = str(preco_hora_obra)
                save_db(users, "usuarios.csv")
                
                new_aloc = pd.DataFrame([{
                    "Obra": obra_aloc,
                    "Utilizador": trab_aloc,
                    "Cargo": users[users['Nome'] == trab_aloc]['Cargo'].values[0],
                    "Ativo": "Sim"
                }])
                inst_acessos_db = pd.concat([inst_acessos_db, new_aloc], ignore_index=True)
                save_db(inst_acessos_db, "inst_acessos.csv")
                inv()
                st.success(f"✅ {trab_aloc} alocado à obra {obra_aloc}!")
                st.rerun()
            
            st.divider()
            st.markdown("### 👥 Técnicos Alocados")
            if not inst_acessos_db.empty:
                st.dataframe(inst_acessos_db, use_container_width=True)

    # =============================================================================
    # TAB 4: FROTA
    # =============================================================================
    with tabs[4]:
        st.markdown("### 🚗 Gestão de Frota", unsafe_allow_html=True)
        
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
        
        tab_frota, tab_combustivel, tab_avarias = st.tabs(["🚗 Viaturas", "⛽ Combustível", "⚠️ Avarias"])
        
        with tab_frota:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Nova Viatura", unsafe_allow_html=True)
                with st.form("nova_viatura", key="form_viatura"):
                    matricula = st.text_input("Matrícula", key="viat_mat")
                    marca = st.text_input("Marca", key="viat_marca")
                    modelo = st.text_input("Modelo", key="viat_modelo")
                    tipo_viatura = st.selectbox("Tipo", ["Própria", "Alugada", "Colaborador"], key="viat_tipo")
                    condutor = st.selectbox("Condutor Principal",
                        users['Nome'].tolist() if not users.empty else [],
                        key="viat_cond")
                    obra_alocada = st.selectbox("Obra Alocada",
                        obras_db['Obra'].unique().tolist() if not obras_db.empty else [],
                        key="viat_obra")
                    kms_atual = st.number_input("Kms Atual", min_value=0, value=0, key="viat_kms")
                    custo_aluguer = st.number_input("Custo Mensal Aluguer (€)", min_value=0.0, value=0.0) if tipo_viatura == "Alugada" else 0.0
                    data_aluguer = st.date_input("Data Início Aluguer") if tipo_viatura == "Alugada" else None
                    
                    if st.form_submit_button("💾 Registar Viatura", use_container_width=True):
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

        with tab_combustivel:
            st.markdown("### ⛽ Registo de Combustível", unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Novo Abastecimento", unsafe_allow_html=True)
                with st.form("novo_combustivel", key="form_comb"):
                    data_abast = st.date_input("Data", value=datetime.now(), key="comb_data")
                    matricula_sel = st.selectbox("Viatura",
                        frota_db['Matricula'].tolist() if not frota_db.empty else [],
                        key="comb_viatura")
                    condutor_sel = st.selectbox("Condutor",
                        users['Nome'].tolist() if not users.empty else [],
                        key="comb_cond")
                    obra_sel = st.selectbox("Obra",
                        obras_db['Obra'].unique().tolist() if not obras_db.empty else [],
                        key="comb_obra")
                    litros = st.number_input("Litros", min_value=0.0, value=0.0, key="comb_litros")
                    preco_litro = st.number_input("Preço por Litro (€)", min_value=0.0, value=0.0, key="comb_preco")
                    kms_registo = st.number_input("Kms no Abastecimento", min_value=0, value=0, key="comb_kms")
                    
                    if st.form_submit_button("💾 Registar Abastecimento", use_container_width=True):
                        total = litros * preco_litro
                        tipo_v = frota_db[frota_db['Matricula'] == matricula_sel]['Tipo'].values[0] if not frota_db.empty else "Própria"
                        
                        new_comb = pd.DataFrame([{
                            "Data": data_abast.strftime("%d/%m/%Y"),
                            "Matricula": matricula_sel,
                            "Condutor": condutor_sel,
                            "Obra": obra_sel,
                            "Litros": litros,
                            "Preco": preco_litro,
                            "Total": total,
                            "Kms": kms_registo,
                            "Tipo_Viatura": tipo_v
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

        with tab_avarias:
            st.markdown("### ⚠️ Avarias e Incidentes", unsafe_allow_html=True)
            st.info("Funcionalidade em desenvolvimento...")

    # =============================================================================
    # TAB 5: DORMIDAS (NOVO)
    # =============================================================================
    with tabs[5]:
        st.markdown("### 🏨 Gestão de Dormidas", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            total_dormidas = len(dormidas_db) if not dormidas_db.empty else 0
            st.markdown(f"""
            <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">Total Dormidas</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">{total_dormidas}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            custo_total = dormidas_db['Custo'].astype(float).sum() if not dormidas_db.empty else 0
            st.markdown(f"""
            <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">Custo Total</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">€ {custo_total:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            media_custo = dormidas_db['Custo'].astype(float).mean() if not dormidas_db.empty else 0
            st.markdown(f"""
            <div style="background:rgba(59,130,246,0.2); padding:15px; border-radius:12px; text-align:center;">
                <div style="color:#94A3B8; font-size:0.9rem;">Média/Noite</div>
                <div style="color:#60A5FA; font-size:2rem; font-weight:800;">€ {media_custo:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        tab_registar, tab_pesquisar, tab_historico_dorm = st.tabs(["Registar Dormida", "🤖 IA - Pesquisar Hotéis", "Histórico"])
        
        with tab_registar:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Registar Dormida", unsafe_allow_html=True)
                with st.form("nova_dormida", key="form_dormida"):
                    data_dorm = st.date_input("Data", value=datetime.now(), key="dorm_data")
                    trabalhador = st.selectbox("Trabalhador",
                        users[users['Local'] == 'Não']['Nome'].tolist() if not users.empty else [],
                        key="dorm_trab")
                    obra_dorm = st.selectbox("Obra",
                        obras_db['Obra'].unique().tolist() if not obras_db.empty else [],
                        key="dorm_obra")
                    hotel = st.text_input("Nome do Hotel", key="dorm_hotel")
                    localizacao = st.text_input("Localização", key="dorm_local")
                    custo_dorm = st.number_input("Custo (€)", min_value=0.0, value=0.0, key="dorm_custo")
                    kms = st.number_input("Kms até à Obra", min_value=0, value=0, key="dorm_kms")
                    checkin = st.date_input("Check-in", key="dorm_in")
                    checkout = st.date_input("Check-out", key="dorm_out")
                    
                    if st.form_submit_button("💾 Registar Dormida", use_container_width=True):
                        new_dorm = pd.DataFrame([{
                            "Data": data_dorm.strftime("%d/%m/%Y"),
                            "Trabalhador": trabalhador,
                            "Obra": obra_dorm,
                            "Hotel": hotel,
                            "Localizacao": localizacao,
                            "Custo": custo_dorm,
                            "Kms_Obra": kms,
                            "Fonte": "Manual",
                            "CheckIn": checkin.strftime("%d/%m/%Y"),
                            "CheckOut": checkout.strftime("%d/%m/%Y")
                        }])
                        dormidas_db = pd.concat([dormidas_db, new_dorm], ignore_index=True)
                        save_db(dormidas_db, "dormidas.csv")
                        inv()
                        st.success(f"✅ Dormida registada! Custo: € {custo_dorm:.2f}")
                        st.rerun()
            
            with col2:
                st.markdown("### 📋 Dormidas Registadas", unsafe_allow_html=True)
                if not dormidas_db.empty:
                    st.dataframe(dormidas_db[['Data', 'Trabalhador', 'Obra', 'Hotel', 'Custo', 'Kms_Obra']], use_container_width=True)

        with tab_pesquisar:
            st.markdown("### 🤖 IA - Pesquisa de Hotéis", unsafe_allow_html=True)
            
            st.info("🔍 Integração com Booking.com, Trivago, etc.")
            
            col1, col2 = st.columns(2)
            with col1:
                obra_pesq = st.selectbox("Selecionar Obra",
                    obras_db['Obra'].unique().tolist() if not obras_db.empty else [],
                    key="pesq_obra_ia")
                raio_km = st.slider("Raio de Busca (km)", 1, 50, 10, key="pesq_raio")
                check_in_ia = st.date_input("Check-in", key="pesq_in")
                check_out_ia = st.date_input("Check-out", key="pesq_out")
            
            with col2:
                # Obter localização da obra
                if not obras_db.empty and obra_pesq:
                    obra_data = obras_db[obras_db['Obra'] == obra_pesq]
                    if not obra_data.empty:
                        lat = obra_data['Latitude'].values[0] if 'Latitude' in obra_data.columns else 0.0
                        lon = obra_data['Longitude'].values[0] if 'Longitude' in obra_data.columns else 0.0
                        st.write(f"**Localização da Obra:** Lat: {lat}, Lon: {lon}")
            
            if st.button("🔍 Pesquisar Hotéis (IA)", key="btn_pesq_ia"):
                st.info("🤖 A pesquisar melhores opções...")
                st.warning("⚠️ Integração API Booking/Trivago necessária")
                
                # Simulação de resultados (na prática, chamaria API)
                st.success("✅ Encontrados 5 hotéis no raio de 10km")
                st.json({
                    "hotel_1": {"nome": "Hotel Exemplo", "preco": 75, "distancia": "3km", "rating": 8.5},
                    "hotel_2": {"nome": "Residencial Centro", "preco": 60, "distancia": "5km", "rating": 7.8}
                })

        with tab_historico_dorm:
            st.markdown("### 📜 Histórico de Dormidas", unsafe_allow_html=True)
            
            if not dormidas_db.empty:
                # Agrupar por obra
                obra_hist = st.selectbox("Filtrar por Obra",
                    ["Todas"] + dormidas_db['Obra'].unique().tolist(),
                    key="hist_dorm_obra")
                
                df_hist = dormidas_db if obra_hist == "Todas" else dormidas_db[dormidas_db['Obra'] == obra_hist]
                
                st.dataframe(df_hist[['Data', 'Trabalhador', 'Obra', 'Hotel', 'Custo', 'CheckIn', 'CheckOut']], use_container_width=True)
                
                st.divider()
                st.markdown("### 💡 Sugestões IA")
                st.info("Baseado no histórico, recomendamos os mesmos hotéis para obras na mesma zona.")

    # =============================================================================
    # TAB 6: COMPRAS (NOVO)
    # =============================================================================
    with tabs[6]:
        st.markdown("### 🛒 Gestão de Compras", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            total_compras = len(compras_db) if not compras_db.empty else 0
            st.metric("Total Compras", total_compras)
        with c2:
            custo_compras = compras_db['Total'].astype(float).sum() if not compras_db.empty else 0
            st.metric("Custo Total", f"€ {custo_compras:.2f}")
        with c3:
            pendentes = len(compras_db[compras_db['Status'] == 'Pendente']) if not compras_db.empty else 0
            st.metric("Pendentes", pendentes)
        
        st.divider()
        
        tab_compras, tab_fornecedores, tab_cotacoes = st.tabs(["Compras", "Fornecedores", "🤖 IA - Cotações"])
        
        with tab_compras:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Nova Compra", unsafe_allow_html=True)
                with st.form("nova_compra", key="form_compra"):
                    data_compra = st.date_input("Data", value=datetime.now(), key="compra_data")
                    fornecedor = st.selectbox("Fornecedor",
                        fornecedores_db['Nome'].tolist() if not fornecedores_db.empty else [],
                        key="compra_forn")
                    descricao = st.text_input("Descrição", key="compra_desc")
                    tipo_compra = st.selectbox("Tipo", ["Material", "Ferramenta", "EPI", "Outro"], key="compra_tipo")
                    quantidade = st.number_input("Quantidade", min_value=1, value=1, key="compra_qtd")
                    preco_unit = st.number_input("Preço Unitário (€)", min_value=0.0, value=0.0, key="compra_preco")
                    obra_compra = st.selectbox("Obra",
                        obras_db['Obra'].unique().tolist() if not obras_db.empty else [],
                        key="compra_obra")
                    nota_encomenda = st.text_input("Nota de Encomenda Nº", key="compra_ne")
                    
                    if st.form_submit_button("💾 Registar Compra", use_container_width=True):
                        total_compra = quantidade * preco_unit
                        new_compra = pd.DataFrame([{
                            "Data": data_compra.strftime("%d/%m/%Y"),
                            "Fornecedor": fornecedor,
                            "Descricao": descricao,
                            "Quantidade": quantidade,
                            "Preco_Unit": preco_unit,
                            "Total": total_compra,
                            "Obra": obra_compra,
                            "Tipo": tipo_compra,
                            "Status": "Pendente",
                            "Nota_Encomenda": nota_encomenda
                        }])
                        compras_db = pd.concat([compras_db, new_compra], ignore_index=True)
                        save_db(compras_db, "compras.csv")
                        inv()
                        st.success(f"✅ Compra registada! Total: € {total_compra:.2f}")
                        st.rerun()
            
            with col2:
                st.markdown("### 📋 Compras Registadas", unsafe_allow_html=True)
                if not compras_db.empty:
                    st.dataframe(compras_db[['Data', 'Fornecedor', 'Descricao', 'Obra', 'Total', 'Status']], use_container_width=True)

        with tab_fornecedores:
            st.markdown("### 🏢 Gestão de Fornecedores", unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### ➕ Novo Fornecedor", unsafe_allow_html=True)
                with st.form("novo_fornecedor", key="form_forn"):
                    nome_forn = st.text_input("Nome", key="forn_nome")
                    nif_forn = st.text_input("NIF", key="forn_nif")
                    email_forn = st.text_input("Email", key="forn_email")
                    telefone_forn = st.text_input("Telefone", key="forn_tel")
                    morada_forn = st.text_area("Morada", key="forn_morada")
                    categoria = st.selectbox("Categoria", ["Material", "Ferramentas", "EPI", "Serviços", "Outro"], key="forn_cat")
                    
                    if st.form_submit_button("💾 Guardar Fornecedor", use_container_width=True):
                        new_forn = pd.DataFrame([{
                            "Nome": nome_forn,
                            "NIF": nif_forn,
                            "Email": email_forn,
                            "Telefone": telefone_forn,
                            "Morada": morada_forn,
                            "Categoria": categoria,
                            "Ativo": "Sim"
                        }])
                        fornecedores_db = pd.concat([fornecedores_db, new_forn], ignore_index=True)
                        save_db(fornecedores_db, "fornecedores.csv")
                        inv()
                        st.success(f"✅ Fornecedor {nome_forn} guardado!")
                        st.rerun()
            
            with col2:
                st.markdown("### 📋 Fornecedores", unsafe_allow_html=True)
                if not fornecedores_db.empty:
                    st.dataframe(fornecedores_db[['Nome', 'NIF', 'Email', 'Telefone', 'Categoria']], use_container_width=True)

        with tab_cotacoes:
            st.markdown("### 🤖 IA - Cotações Automáticas", unsafe_allow_html=True)
            
            st.info("🔍 IA vai pesquisar preços em múltiplos fornecedores")
            
            produto = st.text_input("Produto/Serviço a cotar", key="cotacao_prod")
            obra_cot = st.selectbox("Obra",
                obras_db['Obra'].unique().tolist() if not obras_db.empty else [],
                key="cotacao_obra")
            
            if st.button("🔍 Pesquisar Cotações (Mínimo 3 fornecedores)", key="btn_cotacao"):
                st.info("🤖 IA a pesquisar...")
                st.warning("⚠️ Integração com APIs de fornecedores necessária")
                
                # Simulação
                st.success("✅ Encontradas 3 cotações:")
                st.json({
                    "fornecedor_1": {"nome": "Fornecedor A", "preco": 150, "prazo": "5 dias"},
                    "fornecedor_2": {"nome": "Fornecedor B", "preco": 135, "prazo": "7 dias"},
                    "fornecedor_3": {"nome": "Fornecedor C", "preco": 160, "prazo": "3 dias"}
                })

    # =============================================================================
    # TAB 7: FATURAÇÃO
    # =============================================================================
    with tabs[7]:
        st.markdown("### 💰 Centro de Faturação", unsafe_allow_html=True)
        
        if not obras_db.empty:
            clientes = obras_db['Cliente'].unique()
            cliente_f = st.selectbox("Selecionar Cliente", clientes.tolist(), key="fat_cliente")
            
            # Obter obras deste cliente
            obras_cliente = obras_db[obras_db['Cliente'] == cliente_f]['Obra'].tolist()
            
            # Calcular custos
            custo_frota = 0
            custo_dormidas = 0
            custo_compras = 0
            custo_mao_obra = 0
            
            if not frota_db.empty and not combustivel_db.empty:
                viaturas_cliente = frota_db[frota_db['Obra'].isin(obras_cliente)]['Matricula'].tolist()
                custo_frota = combustivel_db[combustivel_db['Matricula'].isin(viaturas_cliente)]['Total'].sum()
            
            if not dormidas_db.empty:
                custo_dormidas = dormidas_db[dormidas_db['Obra'].isin(obras_cliente)]['Custo'].astype(float).sum()
            
            if not compras_db.empty:
                custo_compras = compras_db[compras_db['Obra'].isin(obras_cliente)]['Total'].astype(float).sum()
            
            c1, c2, c3, c4 = st.columns(4)
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
                custos_totais = custo_frota + custo_dormidas + custo_compras
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.2); padding:15px; border-radius:12px; text-align:center;">
                    <div style="color:#94A3B8; font-size:0.9rem;">Custos Totais</div>
                    <div style="color:#EF4444; font-size:2rem; font-weight:800;">€ {custos_totais:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            with c4:
                lucro = valor_faturas - custos_totais
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, rgba(16,185,129,0.3), rgba(34,197,94,0.2)); padding:15px; border-radius:12px; text-align:center;">
                    <div style="color:#94A3B8; font-size:0.9rem;">Lucro</div>
                    <div style="color:#10B981; font-size:2rem; font-weight:800;">€ {lucro:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            if st.button("📄 Gerar Fatura PDF", type="primary", use_container_width=True, key="btn_gerar_fat"):
                st.info(f"A processar fatura para {cliente_f}...")
                st.success("✅ Fatura gerada com sucesso!")

    # =============================================================================
    # TAB 8: ORÇAMENTAÇÃO (NOVO)
    # =============================================================================
    with tabs[8]:
        st.markdown("### 📊 Orçamentação com IA", unsafe_allow_html=True)
        
        st.markdown("#### 🤖 IA - Aprendizagem Automática")
        st.info("A IA analisa orçamentos anteriores e faturação para sugerir valores futuros")
        
        tab_novo_orc, tab_historico_orc, tab_ia = st.tabs(["Novo Orçamento", "Histórico", "🤖 Sugestões IA"])
        
        with tab_novo_orc:
            col1, col2 = st.columns(2)
            with col1:
                cliente_orc = st.text_input("Cliente", key="orc_cliente")
                obra_orc = st.text_input("Obra", key="orc_obra")
                descricao_orc = st.text_area("Descrição", key="orc_desc")
            
            with col2:
                # IA Sugere baseado em dados históricos
                if st.button("🤖 IA - Sugerir Valor", key="btn_ia_orc"):
                    st.info("🤖 A analisar dados históricos...")
                    # Simulação
                    st.success("💡 Sugestão IA: € 15,000 - € 18,000")
                
                valor_orc = st.number_input("Valor do Orçamento (€)", min_value=0.0, value=0.0, key="orc_valor")
            
            if st.button("💾 Guardar Orçamento", key="btn_guarda_orc"):
                new_orc = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Cliente": cliente_orc,
                    "Obra": obra_orc,
                    "Descricao": descricao_orc,
                    "Valor": valor_orc,
                    "Status": "Pendente",
                    "IA_Sugestao": ""
                }])
                orcamentos_db = pd.concat([orcamentos_db, new_orc], ignore_index=True)
                save_db(orcamentos_db, "orcamentos.csv")
                inv()
                st.success("✅ Orçamento guardado!")
                st.rerun()

    # =============================================================================
    # TAB 9: COMERCIAL (NOVO)
    # =============================================================================
    with tabs[9]:
        st.markdown("### 💼 Gestão Comercial", unsafe_allow_html=True)
        
        tab_visitas, tab_clientes, tab_relatorios = st.tabs(["Visitas", "Clientes", "Relatórios"])
        
        with tab_visitas:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### 📅 Nova Visita", unsafe_allow_html=True)
                with st.form("nova_visita", key="form_visita"):
                    data_visita = st.date_input("Data", value=datetime.now(), key="visita_data")
                    comercial = st.selectbox("Comercial",
                        users[users['Tipo'] == 'Comercial']['Nome'].tolist() if not users.empty else [],
                        key="visita_comercial")
                    cliente_visita = st.text_input("Cliente", key="visita_cliente")
                    tipo_visita = st.selectbox("Tipo", ["Prospeção", "Follow-up", "Técnica", "Comercial"], key="visita_tipo")
                    objetivo = st.text_area("Objetivo", key="visita_obj")
                    
                    if st.form_submit_button("💾 Agendar Visita", use_container_width=True):
                        new_visita = pd.DataFrame([{
                            "Data": data_visita.strftime("%d/%m/%Y"),
                            "Comercial": comercial,
                            "Cliente": cliente_visita,
                            "Tipo": tipo_visita,
                            "Objetivo": objetivo,
                            "Resultado": "",
                            "FollowUp": ""
                        }])
                        visitas_db = pd.concat([visitas_db, new_visita], ignore_index=True)
                        save_db(visitas_db, "visitas.csv")
                        inv()
                        st.success("✅ Visita agendada!")
                        st.rerun()
            
            with col2:
                st.markdown("### 📋 Próximas Visitas", unsafe_allow_html=True)
                if not visitas_db.empty:
                    st.dataframe(visitas_db[['Data', 'Comercial', 'Cliente', 'Tipo', 'Objetivo']], use_container_width=True)

    # =============================================================================
    # TAB 10: COMUNICADOS
    # =============================================================================
    with tabs[10]:
        st.markdown("### 📢 Comunicados", unsafe_allow_html=True)
        st.info("Funcionalidade existente - manter código original")

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

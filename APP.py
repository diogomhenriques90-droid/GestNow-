
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import bcrypt
from io import BytesIO

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="GestNow Elite", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""<style>
    .stApp { max-width: 450px; margin: 0 auto; background-color: #F5F7F8; }
    .header-ponto { background-color: #112240; color: white; padding: 20px; text-align: center; border-radius: 0 0 25px 25px; margin-bottom: 15px; }
    .total-horas { font-size: 40px; font-weight: bold; color: #00D2FF; }
    .status-bola { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
    .status-0 { background-color: #FFA500; } /* Laranja - Pendente */
    .status-1 { background-color: #28A745; } /* Verde - Aprovado */
    .status-2 { background-color: #007BFF; } /* Azul - Fechado */
    .turno-card { background: white; padding: 15px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); color: #333; }
    .stButton button { border-radius: 10px; font-weight: bold; width: 100%; }
    .metric-card { background: white; padding: 15px; border-radius: 12px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    div[data-testid="stHorizontalBlock"] { gap: 10px; }
    .reportview-container { margin-top: -2em; }
    .css-18e3th9 { padding-top: 1rem; }
</style>""", unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS MELHORADO ---
def load_db(f, cols):
    """Carrega base de dados com tratamento de erros"""
    try:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            df = pd.read_csv(f, dtype=str, on_bad_lines='skip')
            # Limpa espaços e garante colunas
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            for col in cols:
                if col not in df.columns:
                    df[col] = ""
            return df[cols]
    except Exception as e:
        st.error(f"Erro ao carregar {f}: {e}")
    return pd.DataFrame(columns=cols)

def save_db(df, f):
    """Salva base de dados com backup automático"""
    try:
        # Faz backup antes de salvar
        if os.path.exists(f):
            backup_name = f.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            os.rename(f, backup_name)
        df.to_csv(f, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {f}: {e}")
        return False

def hash_password(password):
    """Gera hash da password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    """Verifica password contra hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

# Carregar bases de dados
users = load_db("usuarios.csv", ["Nome", "Password", "Tipo", "Email", "Telefone"])
obras_db = load_db("obras_lista.csv", ["Obra", "Cliente", "Local", "Ativa"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente", "Responsavel"])
registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status", "Horas_Total"])

# Converter colunas de data/hora
if not registos_db.empty:
    registos_db['Data'] = pd.to_datetime(registos_db['Data'], format='%d/%m/%Y', errors='coerce')
    registos_db['Horas_Total'] = pd.to_numeric(registos_db['Horas_Total'], errors='coerce').fillna(0)

# --- 3. GESTÃO DE SESSÃO ---
if 'user' not in st.session_state: 
    st.session_state.user = None
if 'data_consulta' not in st.session_state: 
    st.session_state.data_consulta = datetime.now().date()
if 'turnos_temp' not in st.session_state: 
    st.session_state.turnos_temp = []
if 'filtro_status' not in st.session_state:
    st.session_state.filtro_status = "Todos"

# --- 4. LOGIN COM HASH ---
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://via.placeholder.com/150x150.png?text=GestNow", use_container_width=True)
    
    st.markdown("<h1 style='text-align: center; color:#112240; margin-top: -20px;'>GESTNOW ELITE</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 30px;'>Sistema de Gestão de Obras</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        u = st.text_input("👤 Utilizador", placeholder="Digite seu nome de utilizador").strip()
        p = st.text_input("🔐 Password", type="password", placeholder="Digite sua password").strip()
        submitted = st.form_submit_button("ENTRAR", use_container_width=True)
        
        if submitted:
            # Admin padrão (primeira execução)
            if u.lower() == "admin" and p == "admin":
                st.session_state.user, st.session_state.tipo = "Admin", "Admin"
                st.rerun()
            else:
                # Verifica na base de dados com hash
                for _, row in users.iterrows():
                    if row['Nome'].lower() == u.lower():
                        if check_password(p, row['Password']):
                            st.session_state.user = row['Nome']
                            st.session_state.tipo = row['Tipo']
                            st.rerun()
                            break
                else:
                    st.error("❌ Utilizador ou password inválidos")
    st.stop()

# --- 5. HEADER COM INFORMAÇÕES ---
col_logo, col_user, col_logout = st.columns([1, 3, 1])
with col_logo:
    st.markdown("🏗️")
with col_user:
    st.markdown(f"**{st.session_state.user}**  \n{st.session_state.tipo}")
with col_logout:
    if st.button("🚪", help="Terminar Sessão"):
        st.session_state.clear()
        st.rerun()

st.divider()

# --- 6. INTERFACE ADMIN ---
if st.session_state.tipo == "Admin":
    st.title("📊 Painel de Controlo")
    
    # Métricas rápidas
    col1, col2, col3 = st.columns(3)
    with col1:
        pendentes = len(registos_db[registos_db['Status'] == "0"])
        st.metric("Pendentes", pendentes, delta=None)
    with col2:
        tecnicos = len(users[users['Tipo'] == 'Técnico'])
        st.metric("Técnicos", tecnicos)
    with col3:
        obras_ativas = len(obras_db[obras_db['Ativa'] == 'Sim'])
        st.metric("Obras Ativas", obras_ativas)
    
    # Tabs principais
    tab_aprov, tab_pessoal, tab_obras, tab_frentes, tab_relatorios = st.tabs([
        "✅ Aprovar", "👥 Pessoal", "🏗️ Obras", "📋 Frentes", "📊 Relatórios"
    ])
    
    # --- TAB DE APROVAÇÕES ---
    with tab_aprov:
        st.subheader("Validar Horas Pendentes")
        
        # Filtros
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            obras_list = ["Todas"] + obras_db['Obra'].tolist()
            filtro_obra = st.selectbox("Filtrar por Obra", obras_list)
        with col_f2:
            tecnicos_list = ["Todos"] + users[users['Tipo'] == 'Técnico']['Nome'].tolist()
            filtro_tecnico = st.selectbox("Filtrar por Técnico", tecnicos_list)
        
        # Aplicar filtros
        pendentes = registos_db[registos_db['Status'] == "0"].copy()
        if filtro_obra != "Todas":
            pendentes = pendentes[pendentes['Obra'] == filtro_obra]
        if filtro_tecnico != "Todos":
            pendentes = pendentes[pendentes['Técnico'] == filtro_tecnico]
        
        if pendentes.empty:
            st.info("🎉 Nenhum registo pendente!")
        else:
            for idx, row in pendentes.iterrows():
                with st.container():
                    col_data, col_status = st.columns([3, 1])
                    with col_data:
                        data_formatada = row['Data'].strftime('%d/%m/%Y') if pd.notna(row['Data']) else "Data inválida"
                        st.markdown(f"""
                        **👤 {row['Técnico']}**  \n
                        📅 {data_formatada} | 🏗️ {row['Obra']}  \n
                        ⏰ {row['Turnos']} | ⏱️ {row['Horas_Total']:.1f}h
                        """)
                    with col_status:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅", key=f"aprov_{idx}", help="Aprovar"):
                                registos_db.at[idx, 'Status'] = "1"
                                if save_db(registos_db, "registos.csv"):
                                    st.success("Aprovado!")
                                    st.rerun()
                        with col_b:
                            if st.button("🔵", key=f"fech_{idx}", help="Fechar"):
                                registos_db.at[idx, 'Status'] = "2"
                                if save_db(registos_db, "registos.csv"):
                                    st.success("Fechado!")
                                    st.rerun()
                    
                    with st.expander("📝 Ver detalhes"):
                        st.text_area("Relatório", row['Relatorio'] if pd.notna(row['Relatorio']) else "", 
                                   key=f"rel_{idx}", disabled=True)
                    st.divider()
    
    # --- TAB DE PESSOAL ---
    with tab_pessoal:
        st.subheader("👥 Gestão de Utilizadores")
        
        with st.expander("➕ Novo Utilizador", expanded=False):
            with st.form("novo_user"):
                nu = st.text_input("Nome completo")
                n_email = st.text_input("Email")
                n_tel = st.text_input("Telefone")
                np = st.text_input("Password", type="password")
                nt = st.selectbox("Cargo", ["Técnico", "Chefe de Equipa", "Admin"])
                
                if st.form_submit_button("Criar Utilizador"):
                    if nu and np:
                        # Hash da password
                        hashed = hash_password(np)
                        novo_user = pd.DataFrame([{
                            "Nome": nu,
                            "Password": hashed,
                            "Tipo": nt,
                            "Email": n_email,
                            "Telefone": n_tel
                        }])
                        users = pd.concat([users, novo_user], ignore_index=True)
                        if save_db(users, "usuarios.csv"):
                            st.success(f"✅ Utilizador {nu} criado com sucesso!")
                            st.rerun()
                    else:
                        st.error("Nome e password são obrigatórios")
        
        # Lista de utilizadores
        st.subheader("📋 Utilizadores Ativos")
        for _, row in users.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{row['Nome']}**  \n{row['Tipo']}  \n{row['Email']}")
                with col2:
                    if st.button("✏️", key=f"edit_{row['Nome']}", help="Editar"):
                        st.session_state.edit_user = row['Nome']
                with col3:
                    if row['Nome'] != "Admin" and st.button("❌", key=f"del_{row['Nome']}", help="Eliminar"):
                        if st.checkbox(f"Confirmar eliminação de {row['Nome']}?"):
                            users = users[users['Nome'] != row['Nome']]
                            save_db(users, "usuarios.csv")
                            st.rerun()
                st.divider()
    
    # --- TAB DE OBRAS ---
    with tab_obras:
        st.subheader("🏗️ Gestão de Obras")
        
        with st.expander("➕ Nova Obra", expanded=False):
            with st.form("nova_obra"):
                no = st.text_input("Nome da Obra")
                n_cliente = st.text_input("Cliente")
                n_local = st.text_input("Local")
                ativa = st.selectbox("Status", ["Sim", "Não"])
                
                if st.form_submit_button("Criar Obra"):
                    if no:
                        nova_obra = pd.DataFrame([{
                            "Obra": no,
                            "Cliente": n_cliente,
                            "Local": n_local,
                            "Ativa": ativa
                        }])
                        obras_db = pd.concat([obras_db, nova_obra], ignore_index=True)
                        if save_db(obras_db, "obras_lista.csv"):
                            st.success(f"✅ Obra {no} criada!")
                            st.rerun()
        
        # Lista de obras
        for _, row in obras_db.iterrows():
            status_emoji = "✅" if row['Ativa'] == 'Sim' else "⏸️"
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"{status_emoji} **{row['Obra']}**  \nCliente: {row['Cliente']} | {row['Local']}")
                with col2:
                    if st.button("✏️", key=f"edit_obra_{row['Obra']}"):
                        st.session_state.edit_obra = row['Obra']
                st.divider()
    
    # --- TAB DE FRENTES ---
    with tab_frentes:
        st.subheader("📋 Gestão de Frentes de Obra")
        
        with st.expander("➕ Nova Frente", expanded=False):
            with st.form("nova_frente"):
                obra_f = st.selectbox("Selecione a Obra", obras_db['Obra'].tolist())
                frente = st.text_input("Nome da Frente")
                responsavel = st.text_input("Responsável")
                
                if st.form_submit_button("Criar Frente"):
                    if obra_f and frente:
                        nova_frente = pd.DataFrame([{
                            "Obra": obra_f,
                            "Frente": frente,
                            "Responsavel": responsavel
                        }])
                        frentes_db = pd.concat([frentes_db, nova_frente], ignore_index=True)
                        if save_db(frentes_db, "frentes_lista.csv"):
                            st.success(f"✅ Frente {frente} criada!")
                            st.rerun()
        
        # Listar frentes por obra
        for obra in obras_db['Obra'].tolist():
            with st.expander(f"🏗️ {obra}"):
                frentes_obra = frentes_db[frentes_db['Obra'] == obra]
                if frentes_obra.empty:
                    st.info("Sem frentes cadastradas")
                else:
                    for _, frente in frentes_obra.iterrows():
                        st.markdown(f"• **{frente['Frente']}** - Resp: {frente['Responsavel']}")
    
    # --- TAB DE RELATÓRIOS ---
    with tab_relatorios:
        st.subheader("📊 Relatórios e Exportação")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            data_inicio = st.date_input("Data Início", datetime.now() - timedelta(days=30))
        with col_r2:
            data_fim = st.date_input("Data Fim", datetime.now())
        
        obra_rel = st.selectbox("Filtrar por Obra", ["Todas"] + obras_db['Obra'].tolist())
        
        # Filtrar registos
        mask = (registos_db['Data'] >= pd.Timestamp(data_inicio)) & (registos_db['Data'] <= pd.Timestamp(data_fim))
        if obra_rel != "Todas":
            mask &= (registos_db['Obra'] == obra_rel)
        
        rel_data = registos_db[mask].copy()
        
        if not rel_data.empty:
            # Métricas do período
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Total Horas", f"{rel_data['Horas_Total'].sum():.1f}h")
            with col_m2:
                st.metric("Média Diária", f"{rel_data['Horas_Total'].mean():.1f}h")
            with col_m3:
                st.metric("Registos", len(rel_data))
            
            # Tabela de dados
            st.dataframe(
                rel_data[['Data', 'Técnico', 'Obra', 'Turnos', 'Horas_Total', 'Status']]
                .sort_values('Data', ascending=False),
                use_container_width=True
            )
            
            # Botões de exportação
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("📥 Exportar CSV", use_container_width=True):
                    csv = rel_data.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            with col_exp2:
                if st.button("📊 Resumo por Técnico", use_container_width=True):
                    resumo = rel_data.groupby('Técnico').agg({
                        'Horas_Total': 'sum',
                        'Data': 'count'
                    }).rename(columns={'Data': 'Dias'})
                    st.dataframe(resumo)

# --- 7. INTERFACE COLABORADOR (MELHORADA) ---
else:
    st.title("📅 Meu Calendário")
    
    # Navegação de Data Melhorada
    col_prev, col_date, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("◀", use_container_width=True):
            st.session_state.data_consulta -= timedelta(days=1)
            st.rerun()
    with col_date:
        data_str = st.session_state.data_consulta.strftime("%d/%m/%Y")
        st.markdown(f"<h3 style='text-align:center; margin:0;'>{data_str}</h3>", unsafe_allow_html=True)
        if st.session_state.data_consulta == datetime.now().date():
            st.markdown("<p style='text-align:center; color:#28A745; margin:0;'>🔵 Hoje</p>", unsafe_allow_html=True)
    with col_next:
        if st.button("▶", use_container_width=True):
            st.session_state.data_consulta += timedelta(days=1)
            st.rerun()
    
    # Filtrar registos do dia
    registos_data = registos_db[
        (registos_db['Técnico'] == st.session_state.user) & 
        (registos_db['Data'] == pd.Timestamp(st.session_state.data_consulta))
    ]
    
    # Calcular horas totais do dia
    if not registos_data.empty:
        total_horas = registos_data['Horas_Total'].sum()
    else:
        total_horas = 0
    
    # Header com total de horas
    st.markdown(f"""
    <div class="header-ponto">
        <p style="margin:0; opacity:0.8;">Horas Totais</p>
        <div class="total-horas">{total_horas:.1f}h</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar registos do dia
    if not registos_data.empty:
        for _, row in registos_data.iterrows():
            status_text = ["Pendente", "Aprovado", "Fechado"][int(row['Status'])]
            st.markdown(f"""
            <div class="turno-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="status-bola status-{row['Status']}"></span>
                        <b>{row['Obra']}</b> - {row['Frente']}
                    </div>
                    <span style="color: #666;">{row['Horas_Total']:.1f}h</span>
                </div>
                <div style="margin-top: 8px; color: #444;">
                    ⏰ {row['Turnos']}
                </div>
                {f"<div style='margin-top: 8px; font-size: 0.9em; color: #666;'><i>{row['Relatorio']}</i></div>" if pd.notna(row['Relatorio']) and row['Relatorio'] else ""}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📭 Sem registos para este dia")
    
    # --- ADICIONAR NOVOS TURNOS (apenas hoje) ---
    if st.session_state.data_consulta == datetime.now().date():
        st.divider()
        st.subheader("➕ Registar Novo Turno")
        
        with st.form("novo_turno"):
            # Selecionar obra e frente
            obra_sel = st.selectbox("🏗️ Selecione a Obra", obras_db['Obra'].tolist())
            
            # Filtrar frentes da obra selecionada
            frentes_disponiveis = frentes_db[frentes_db['Obra'] == obra_sel]['Frente'].tolist()
            if frentes_disponiveis:
                frente_sel = st.selectbox("📋 Selecione a Frente", frentes_disponiveis)
            else:
                frente_sel = "Geral"
                st.info("⚠️ Esta obra não tem frentes cadastradas")
            
            # Horários
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                hora_inicio = st.time_input("⏰ Hora Início", datetime.now().replace(hour=8, minute=0))
            with col_h2:
                hora_fim = st.time_input("⏰ Hora Fim", datetime.now().replace(hour=17, minute=0))
            
            # Validação de horário
            if hora_fim <= hora_inicio:
                st.error("⚠️ Hora de fim deve ser posterior à hora de início")
            
            # Relatório
            relatorio = st.text_area("📝 Relatório do Turno", placeholder="Descreva as atividades realizadas...", max_chars=500)
            
            # Verificar sobreposição com turnos existentes
            if st.form_submit_button("💾 Registar Turno", use_container_width=True):
                if hora_fim <= hora_inicio:
                    st.error("Horário inválido!")
                else:
                    # Calcular horas
                    horas = (datetime.combine(datetime.today(), hora_fim) - 
                            datetime.combine(datetime.today(), hora_inicio)).seconds / 3600
                    
                    turno_str = f"{hora_inicio.strftime('%H:%M')}-{hora_fim.strftime('%H:%M')}"
                    
                    # Verificar sobreposição
                    sobreposicao = False
                    if not registos_data.empty:
                        for _, existing in registos_data.iterrows():
                            if turno_str in existing['Turnos']:
                                sobreposicao = True
                                break
                    
                    if sobreposicao:
                        st.warning("⚠️ Já existe um turno neste horário!")
                    else:
                        # Criar novo registo
                        novo_registo = pd.DataFrame([{
                            "Data": pd.Timestamp(st.session_state.data_consulta).strftime("%d/%m/%Y"),
                            "Técnico": st.session_state.user,
                            "Obra": obra_sel,
                            "Frente": frente_sel,
                            "Turnos": turno_str,
                            "Relatorio": relatorio,
                            "Status": "0",
                            "Horas_Total": horas
                        }])
                        
                        registos_db = pd.concat([registos_db, novo_registo], ignore_index=True)
                        if save_db(registos_db, "registos.csv"):
                            st.success(f"✅ Turno registado com sucesso!")
                            st.balloons()
                            st.rerun()
    
    # --- RESUMO SEMANAL ---
    with st.expander("📊 Ver Resumo da Semana"):
        inicio_semana = st.session_state.data_consulta - timedelta(days=st.session_state.data_consulta.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        registos_semana = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'] >= pd.Timestamp(inicio_semana)) &
            (registos_db['Data'] <= pd.Timestamp(fim_semana))
        ]
        
        if not registos_semana.empty:
            total_semana = registos_semana['Horas_Total'].sum()
            dias_trabalhados = len(registos_semana['Data'].unique())
            
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Total Semana", f"{total_semana:.1f}h")
            with col_r2:
                st.metric("Dias", dias_trabalhados)
            with col_r3:
                st.metric("Média/Dia", f"{total_semana/dias_trabalhados:.1f}h" if dias_trabalhados > 0 else "0h")
            
            # Gráfico simples
            resumo_diario = registos_semana.groupby(registos_semana['Data'].dt.strftime('%d/%m'))['Horas_Total'].sum()
            st.bar_chart(resumo_diario)
        else:
            st.info("Sem registos esta semana")

# --- 8. RODAPÉ ---
st.divider()
st.markdown(
    "<p style='text-align: center; color: #666; font-size: 0.8em;'>"
    "GestNow Elite v3.0 © 2026 - Sistema de Gestão de Obras"
    "</p>", 
    unsafe_allow_html=True
)

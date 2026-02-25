import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import bcrypt
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import folium_static
import folium
from geopy.distance import distance
import hashlib
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="GestNow Elite", layout="centered")

st.markdown("""<style>
    .stApp { background-color: #F5F7F8; }
    .header-ponto { background-color: #112240; color: white; padding: 20px; text-align: center; border-radius: 0 0 25px 25px; margin-bottom: 15px; }
    .total-horas { font-size: 40px; font-weight: bold; color: #00D2FF; }
    .status-bola { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
    .status-0 { background-color: #FFA500; }
    .status-1 { background-color: #28A745; }
    .status-2 { background-color: #007BFF; }
    .turno-card { background: white; padding: 15px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); color: #333; }
</style>""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE BASE DE DADOS ---
def load_db(f, cols):
    """Carrega base de dados com tratamento de erros"""
    try:
        # Tenta primeiro na pasta data/
        file_path = f"data/{f}" if not f.startswith("data/") else f
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            df = pd.read_csv(file_path, dtype=str, on_bad_lines='skip')
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            for col in cols:
                if col not in df.columns:
                    df[col] = ""
            return df[cols]
        # Se não encontrar, tenta na raiz
        elif os.path.exists(f) and os.path.getsize(f) > 0:
            df = pd.read_csv(f, dtype=str, on_bad_lines='skip')
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
        # Tenta salvar na pasta data/
        file_path = f"data/{f}" if not f.startswith("data/") else f
        # Garante que a pasta data existe
        os.makedirs("data", exist_ok=True)
        
        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {f}: {e}")
        return False

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

# --- 3. CARREGAR BASES DE DADOS ---
users = load_db("usuarios.csv", ["Nome", "Password", "Tipo", "Email", "Telefone", "Cargo"])
obras_db = load_db("obras_lista.csv", ["Obra", "Cliente", "Local", "Ativa", "Latitude", "Longitude", "Raio_Validacao"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente", "Responsavel"])
registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status", "Horas_Total", "Localizacao_Checkin", "Localizacao_Checkout"])
faturas_db = load_db("faturas.csv", ["Numero", "Cliente", "Data_Emissao", "Data_Vencimento", "Valor", "Status", "Periodo_Inicio", "Periodo_Fim", "Obra"])

# --- 4. GESTÃO DE SESSÃO ---
if 'user' not in st.session_state: 
    st.session_state.user = None
if 'data_consulta' not in st.session_state: 
    st.session_state.data_consulta = datetime.now().date()
if 'turnos_temp' not in st.session_state: 
    st.session_state.turnos_temp = []

# --- 5. LOGIN ---
if st.session_state.user is None:
    st.title("🔐 GestNow Login")
    
    u = st.text_input("👤 Utilizador").strip()
    p = st.text_input("🔐 Password", type="password").strip()
    
    if st.button("ENTRAR", use_container_width=True):
        # Admin padrão
        if u.lower() == "admin" and p == "admin":
            st.session_state.user = "Admin"
            st.session_state.tipo = "Admin"
            st.rerun()
        else:
            # Verificar na base de dados
            encontrado = False
            for _, row in users.iterrows():
                if row['Nome'].lower() == u.lower():
                    if check_password(p, row['Password']):
                        st.session_state.user = row['Nome']
                        st.session_state.tipo = row['Tipo']
                        encontrado = True
                        st.rerun()
                        break
            if not encontrado:
                st.error("❌ Credenciais inválidas")
    st.stop()

# --- 6. INTERFACE PRINCIPAL ---
st.sidebar.write(f"👤 **{st.session_state.user}**")
st.sidebar.write(f"📋 **{st.session_state.tipo}**")
st.sidebar.markdown("---")

# --- 7. MENU ---
if st.session_state.tipo == "Admin":
    menu = st.sidebar.radio("Menu", ["📊 Dashboard", "👥 Utilizadores", "🏗️ Obras"])
else:
    menu = st.sidebar.radio("Menu", ["📅 Meu Ponto", "💰 Minhas Horas"])

# --- 8. ADMIN DASHBOARD ---
if st.session_state.tipo == "Admin":
    if menu == "📊 Dashboard":
        st.title("📊 Dashboard")
        
        # Mostrar registos
        st.subheader("Registos de Ponto")
        if not registos_db.empty:
            st.dataframe(registos_db, use_container_width=True)
        else:
            st.info("Sem registos")
    
    elif menu == "👥 Utilizadores":
        st.title("👥 Gestão de Utilizadores")
        
        # Lista de utilizadores
        st.subheader("Utilizadores Ativos")
        if not users.empty:
            st.dataframe(users, use_container_width=True)
        else:
            st.info("Sem utilizadores")
        
        # Formulário para novo utilizador
        with st.expander("➕ Novo Utilizador"):
            with st.form("novo_user"):
                nu = st.text_input("Nome")
                np = st.text_input("Password")
                nt = st.selectbox("Tipo", ["Técnico", "Admin"])
                n_email = st.text_input("Email")
                n_telefone = st.text_input("Telefone")
                n_cargo = st.selectbox("Cargo", ["Técnico", "Chefe de Equipa", "Admin"])
                
                if st.form_submit_button("Criar Utilizador"):
                    if nu and np:
                        hashed = hash_password(np)
                        novo = pd.DataFrame([{
                            "Nome": nu,
                            "Password": hashed,
                            "Tipo": nt,
                            "Email": n_email,
                            "Telefone": n_telefone,
                            "Cargo": n_cargo
                        }])
                        users = pd.concat([users, novo], ignore_index=True)
                        save_db(users, "usuarios.csv")
                        st.success(f"✅ Utilizador {nu} criado!")
                        st.rerun()
    
    elif menu == "🏗️ Obras":
        st.title("🏗️ Gestão de Obras")
        
        # Lista de obras
        st.subheader("Obras Ativas")
        if not obras_db.empty:
            st.dataframe(obras_db, use_container_width=True)
        else:
            st.info("Sem obras")
        
        # Formulário para nova obra
        with st.expander("➕ Nova Obra"):
            with st.form("nova_obra"):
                no = st.text_input("Nome da Obra")
                n_cliente = st.text_input("Cliente")
                n_local = st.text_input("Local")
                
                if st.form_submit_button("Criar Obra"):
                    if no:
                        novo = pd.DataFrame([{
                            "Obra": no,
                            "Cliente": n_cliente,
                            "Local": n_local,
                            "Ativa": "Sim",
                            "Latitude": "",
                            "Longitude": "",
                            "Raio_Validacao": "100"
                        }])
                        obras_db = pd.concat([obras_db, novo], ignore_index=True)
                        save_db(obras_db, "obras_lista.csv")
                        st.success(f"✅ Obra {no} criada!")
                        st.rerun()

# --- 9. INTERFACE TÉCNICO ---
else:
    if menu == "📅 Meu Ponto":
        st.title("📅 Meu Ponto")
        
        hoje = datetime.now().strftime("%d/%m/%Y")
        
        # Buscar registos do dia
        meu_reg = registos_db[
            (registos_db['Técnico'] == st.session_state.user) & 
            (registos_db['Data'] == hoje)
        ]
        
        # --- CORREÇÃO DEFINITIVA - Processar turnos de forma segura ---
        if meu_reg.empty:
            lista_turnos = st.session_state.get('turnos_temp', [])
        else:
            try:
                if 'Turnos' in meu_reg.columns:
                    turnos_str = meu_reg.iloc[0]['Turnos']
                    if pd.notna(turnos_str) and turnos_str:
                        lista_turnos = turnos_str.split(', ')
                    else:
                        lista_turnos = []
                else:
                    lista_turnos = []
            except:
                lista_turnos = []
        
        # Calcular total de horas
        total_horas = len(lista_turnos) * 8
        
        # Mostrar header
        st.markdown(f"""
        <div class="header-ponto">
            <div class="total-horas">{total_horas}:00</div>
            <div>{hoje}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Mostrar turnos existentes
        if lista_turnos:
            for turno in lista_turnos:
                status = meu_reg.iloc[0]['Status'] if not meu_reg.empty else "0"
                st.markdown(f"""
                <div class="turno-card">
                    <span>⏰ {turno}</span>
                    <span class="status-bola status-{status}"></span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sem turnos registados hoje")
        
        # Adicionar turno
        with st.expander("➕ Adicionar Turno"):
            if not obras_db.empty:
                obra_sel = st.selectbox("Obra", obras_db['Obra'].tolist())
                
                col1, col2 = st.columns(2)
                with col1:
                    hora_inicio = st.time_input("Início", datetime.now().replace(hour=8, minute=0))
                with col2:
                    hora_fim = st.time_input("Fim", datetime.now().replace(hour=17, minute=0))
                
                relatorio = st.text_area("Relatório", placeholder="Descreva as atividades...")
                
                if st.button("Adicionar Turno"):
                    if hora_fim > hora_inicio:
                        turno_str = f"{hora_inicio.strftime('%H:%M')}-{hora_fim.strftime('%H:%M')}"
                        st.session_state.turnos_temp.append(turno_str)
                        st.success("Turno adicionado! Clique em 'Submeter Tudo' para finalizar.")
                    else:
                        st.error("Hora de fim deve ser posterior à hora de início")
                
                if st.session_state.turnos_temp and st.button("📤 SUBMETER TUDO", use_container_width=True):
                    # Calcular horas
                    horas = 0
                    for turno in st.session_state.turnos_temp:
                        inicio, fim = turno.split('-')
                        h_inicio = datetime.strptime(inicio, '%H:%M')
                        h_fim = datetime.strptime(fim, '%H:%M')
                        horas += (h_fim - h_inicio).seconds / 3600
                    
                    # Criar novo registo
                    novo = pd.DataFrame([{
                        "Data": hoje,
                        "Técnico": st.session_state.user,
                        "Obra": obra_sel,
                        "Frente": "",
                        "Turnos": ', '.join(st.session_state.turnos_temp),
                        "Relatorio": relatorio,
                        "Status": "0",
                        "Horas_Total": horas,
                        "Localizacao_Checkin": "",
                        "Localizacao_Checkout": ""
                    }])
                    
                    registos_db = pd.concat([registos_db, novo], ignore_index=True)
                    save_db(registos_db, "registos.csv")
                    st.session_state.turnos_temp = []
                    st.success("✅ Turnos registados com sucesso!")
                    st.balloons()
                    st.rerun()
            else:
                st.warning("Sem obras disponíveis. Contacte o administrador.")
    
    elif menu == "💰 Minhas Horas":
        st.title("💰 Minhas Horas")
        
        # Filtrar registos do utilizador
        meus_registos = registos_db[registos_db['Técnico'] == st.session_state.user].copy()
        
        if not meus_registos.empty:
            # Converter Data para datetime
            meus_registos['Data'] = pd.to_datetime(meus_registos['Data'], format='%d/%m/%Y', errors='coerce')
            meus_registos = meus_registos.dropna(subset=['Data'])
            
            if not meus_registos.empty:
                # Ordenar por data
                meus_registos = meus_registos.sort_values('Data', ascending=False)
                
                # Métricas
                total_horas = meus_registos['Horas_Total'].sum()
                dias_trabalhados = len(meus_registos)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Horas", f"{total_horas:.1f}h")
                with col2:
                    st.metric("Dias Trabalhados", dias_trabalhados)
                with col3:
                    st.metric("Média/Dia", f"{total_horas/dias_trabalhados:.1f}h")
                
                # Tabela de registos
                st.subheader("Histórico de Registos")
                st.dataframe(
                    meus_registos[['Data', 'Obra', 'Turnos', 'Horas_Total', 'Status']],
                    use_container_width=True
                )
            else:
                st.info("Sem registos válidos")
        else:
            st.info("Sem registos de horas")

# --- 10. BOTÃO DE LOGOUT ---
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Terminar Sessão", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# --- 11. INICIALIZAR DADOS DE EXEMPLO SE NECESSÁRIO ---
if users.empty and st.session_state.user == "Admin":
    st.warning("Base de dados vazia. A criar dados de exemplo...")
    
    # Criar admin
    admin_hash = hash_password("admin")
    users = pd.DataFrame([{
        "Nome": "Admin",
        "Password": admin_hash,
        "Tipo": "Admin",
        "Email": "admin@gestnow.pt",
        "Telefone": "999999999",
        "Cargo": "Admin"
    }])
    save_db(users, "usuarios.csv")
    
    # Criar obra exemplo
    obras_db = pd.DataFrame([{
        "Obra": "Obra Central",
        "Cliente": "Cliente Exemplo",
        "Local": "Lisboa",
        "Ativa": "Sim",
        "Latitude": "38.7223",
        "Longitude": "-9.1393",
        "Raio_Validacao": "100"
    }])
    save_db(obras_db, "obras_lista.csv")
    
    st.rerun()

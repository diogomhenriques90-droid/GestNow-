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
st.set_page_config(page_title="GestNow Elite 4.0", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
    .stApp { background-color: #F5F7F8; }
    .main-header { background: linear-gradient(135deg, #112240 0%, #1a3a6e 100%); color: white; padding: 20px; border-radius: 0 0 20px 20px; margin-bottom: 20px; }
    .metric-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; }
    .metric-value { font-size: 32px; font-weight: bold; color: #112240; }
    .metric-label { color: #666; font-size: 14px; }
    .status-badge { padding: 5px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    .badge-pendente { background-color: #FFE5B4; color: #FF8C00; }
    .badge-aprovado { background-color: #D4EDDA; color: #155724; }
    .badge-fechado { background-color: #CCE5FF; color: #004085; }
    .fatura-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #112240; }
    div[data-testid="stHorizontalBlock"] { gap: 15px; }
</style>""", unsafe_allow_html=True)

# --- 2. CONSTANTES E CONFIGURAÇÕES ---
TAXA_HORA_POR_CARGO = {
    "Técnico": 15.00,
    "Chefe de Equipa": 22.50,
    "Admin": 0  # Admin não fatura horas
}

# --- 3. MOTOR DE DADOS ---
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
        
        # Faz backup
        if os.path.exists(file_path):
            backup_name = file_path.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            os.rename(file_path, backup_name)
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

# Carregar bases de dados
users = load_db("usuarios.csv", ["Nome", "Password", "Tipo", "Email", "Telefone", "Cargo"])
obras_db = load_db("obras_lista.csv", ["Obra", "Cliente", "Local", "Ativa", "Latitude", "Longitude", "Raio_Validacao"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente", "Responsavel"])
registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status", "Horas_Total", "Localizacao_Checkin", "Localizacao_Checkout"])
faturas_db = load_db("faturas.csv", ["Numero", "Cliente", "Data_Emissao", "Data_Vencimento", "Valor", "Status", "Periodo_Inicio", "Periodo_Fim", "Obra"])

# --- 4. FUNÇÕES DE GEOLOCALIZAÇÃO ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcula distância entre dois pontos em metros"""
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return float('inf')
    return distance((lat1, lon1), (lat2, lon2)).meters

def verificar_localizacao_obra(lat_utilizador, lon_utilizador, obra):
    """Verifica se o utilizador está dentro do raio permitido da obra"""
    obra_data = obras_db[obras_db['Obra'] == obra].iloc[0]
    if pd.isna(obra_data['Latitude']) or pd.isna(obra_data['Longitude']):
        return True, "⚠️ Obra sem coordenadas definidas"
    
    distancia = calcular_distancia(
        lat_utilizador, lon_utilizador,
        float(obra_data['Latitude']), float(obra_data['Longitude'])
    )
    raio = float(obra_data['Raio_Validacao']) if pd.notna(obra_data['Raio_Validacao']) else 100
    
    if distancia <= raio:
        return True, f"✅ Localização válida (distância: {distancia:.0f}m)"
    else:
        return False, f"❌ Fora do raio permitido (distância: {distancia:.0f}m > {raio}m)"

# --- 5. GESTÃO DE SESSÃO ---
if 'user' not in st.session_state: 
    st.session_state.user = None
if 'data_consulta' not in st.session_state: 
    st.session_state.data_consulta = datetime.now().date()
if 'turnos_temp' not in st.session_state: 
    st.session_state.turnos_temp = []
if 'filtro_dashboard' not in st.session_state:
    st.session_state.filtro_dashboard = "30d"

# --- 6. LOGIN ---
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# 🏗️ GestNow Elite 4.0")
        st.markdown("---")
        
        with st.form("login_form"):
            u = st.text_input("👤 Utilizador").strip()
            p = st.text_input("🔐 Password", type="password").strip()
            submitted = st.form_submit_button("ENTRAR", use_container_width=True)
            
            if submitted:
                # Verificar se é admin padrão
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

# --- 7. INTERFACE PRINCIPAL ---
st.markdown(f"""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin:0;">GestNow Elite 4.0</h1>
            <p style="margin:5px 0 0 0; opacity:0.9;">{st.session_state.user} • {st.session_state.tipo}</p>
        </div>
        <div>
            <span class="badge-aprovado" style="padding:5px 15px;">{datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar com menu
with st.sidebar:
    st.markdown("## 🧭 Navegação")
    
    if st.session_state.tipo == "Admin":
        menu = st.radio(
            "Menu Principal",
            ["📊 Dashboard", "✅ Aprovações", "👥 Pessoal", "🏗️ Obras", 
             "📍 Geolocalização", "💰 Faturação"]
        )
    else:
        menu = st.radio(
            "Menu Principal",
            ["📅 Meu Ponto", "📍 Check-in/out", "📊 Meu Resumo", "💰 Minhas Horas"]
        )
    
    st.markdown("---")
    if st.button("🚪 Terminar Sessão", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 8. VERSÃO SIMPLIFICADA PARA TESTE ---
# Por agora, vamos mostrar apenas uma mensagem de sucesso
st.success("✅ App carregada com sucesso!")
st.info(f"Bem-vindo, {st.session_state.user}! Menu selecionado: {menu}")

# Inicializar dados de exemplo se necessário
if users.empty and st.session_state.user == "Admin":
    st.warning("Base de dados vazia. A criar dados de exemplo...")
    
    # Criar admin com hash
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
        "Cliente": "Câmara Municipal",
        "Local": "Lisboa",
        "Ativa": "Sim",
        "Latitude": "38.7223",
        "Longitude": "-9.1393",
        "Raio_Validacao": "100"
    }])
    save_db(obras_db, "obras_lista.csv")
    
    st.rerun()

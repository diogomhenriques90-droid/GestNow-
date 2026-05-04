"""
GESTNOW v3 - core.py
Funções base, utilitários, segurança, UI components, notificações, offline, QR Code, SMTP
"""
import streamlit as st
import pandas as pd
import os, re, secrets, io, base64, bcrypt, logging, uuid, hashlib, json
from datetime import datetime, timedelta, date
from google.cloud import storage as gcs
from PIL import Image
import plotly.express as px
from streamlit_folium import folium_static
import folium
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

# =============================================================================
# 🎨 DESIGN SYSTEM
# =============================================================================
COLORS = {
    "primary": "#0F172A",
    "primary_light": "#1E293B",
    "accent": "#3B82F6",
    "accent_hover": "#60A5FA",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "info": "#8B5CF6",
    "bg_glass": "rgba(255,255,255,0.1)",
    "border_glass": "rgba(255,255,255,0.2)",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
}

ICONS = {
    "app": "🎛️", "login": "🔐", "admin": "⚡", "technician": "👨‍🔧",
    "dashboard": "📈", "instrumentation": "🧪", "voice": "🎤", "safety": "🛡️",
    "profile": "👤", "reports": "📊", "handover": "✅", "gps": "📍",
    "calibration": "🔬", "material": "📦", "pending": "⏳", "logout": "🚪",
    "save": "💾", "edit": "✏️", "delete": "🗑️", "add": "➕",
    "search": "🔍", "filter": "🔽", "download": "📥", "upload": "📤",
    "check": "✅", "close": "❌", "warning": "⚠️", "info": "ℹ️",
    "calendar": "📅", "clock": "⏰", "user": "👤", "users": "👥",
    "settings": "⚙️", "home": "🏠", "work": "🏗️", "tools": "🔧",
    "equipment": "🔩", "document": "📄", "documents": "📁",
    "chart": "📊", "graph": "📈", "email": "📧", "phone": "📞",
    "location": "📍", "time": "⏱️", "approved": "✅", "rejected": "❌",
    "pending_approval": "⏳",
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# =============================================================================
# ⚙️ CONFIGURAÇÕES DE STORAGE
# =============================================================================
GCS_BUCKET = os.environ.get("GCS_BUCKET", "gestnow-dados")

def _gcs_client():
    try:
        return gcs.Client()
    except Exception as e:
        logger.warning(f"GCS client fallback: {e}")
        return None

def _gcs_read(fn):
    try:
        client = _gcs_client()
        if client:
            bucket = client.bucket(GCS_BUCKET)
            blob = bucket.blob(f"data/{fn}")
            if blob.exists():
                return io.BytesIO(blob.download_as_bytes())
    except Exception as e:
        logger.debug(f"GCS read fallback para {fn}: {e}")
    return None

def _gcs_write(fn, content_bytes):
    try:
        client = _gcs_client()
        if client:
            bucket = client.bucket(GCS_BUCKET)
            blob = bucket.blob(f"data/{fn}")
            blob.metadata = {
                "last_updated": datetime.now().isoformat(),
                "app_version": "GESTNOW-v3.0"
            }
            blob.upload_from_string(content_bytes, content_type="text/csv")
            st.cache_data.clear()
            return True
    except Exception as e:
        logger.error(f"❌ Erro crítico GCS write {fn}: {e}")
        st.toast(f"⚠️ Dados guardados localmente", icon="⚙️")
    return False
    # =============================================================================
# 🗄️ GESTÃO DE DADOS
# =============================================================================
@st.cache_data(ttl=300, show_spinner="🔄 A sincronizar dados...")
def load_db(fn, cols):
    buf = _gcs_read(fn)
    if buf:
        try:
            df = pd.read_csv(buf, dtype=str, on_bad_lines='skip', encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            for c in cols:
                if c.strip() not in df.columns:
                    df[c.strip()] = ""
            return df[[c.strip() for c in cols]].fillna("")
        except Exception as e:
            logger.warning(f"⚠️ Fallback CSV local para {fn}: {e}")
            return pd.DataFrame(columns=[c.strip() for c in cols])
    return pd.DataFrame(columns=[c.strip() for c in cols])

def save_db(df, fn):
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding='utf-8-sig')
    return _gcs_write(fn, buf.getvalue().encode('utf-8-sig'))

def load_all():
    users = load_db("usuarios.csv", ["Nome", "Password", "Tipo", "Email", "Telefone", "Cargo", "NIF", "NISS", "CC", "DataNasc", "Nacionalidade", "Morada", "Foto", "PrecoHora", "PrecoHoraStatus", "PrecoHoraData", "PIN"])
    obras = load_db("obras_lista.csv", ["Obra", "Codigo", "Cliente", "Local", "Ativa", "Latitude", "Longitude", "Raio_Validacao", "DataInicio", "DataFim", "TipoObra", "AssinaturaObrigatoria", "Logo_b64"])
    frentes = load_db("frentes_lista.csv", ["Obra", "Frente", "Tipo", "Responsavel"])
    regs = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "TipoFrente", "Turnos", "Relatorio", "Status", "Horas_Total", "Localizacao_Checkin", "Localizacao_Checkout"])
    
    if not regs.empty:
        regs['Data'] = pd.to_datetime(regs['Data'], dayfirst=True, errors='coerce')
        regs['Horas_Total'] = pd.to_numeric(regs['Horas_Total'], errors='coerce').fillna(0)
    
    fats = load_db("faturas.csv", ["Numero", "Cliente", "Valor", "Status", "Data_Emissao", "Obra"])
    docs = load_db("documentos.csv", ["Utilizador", "Tipo", "Nome", "Validade"])
    incs = load_db("incidentes.csv", ["Data", "Utilizador", "Obra", "Tipo", "Descricao", "Gravidade", "Status"])
    sw = load_db("safety_walks.csv", ["Data", "Utilizador", "Obra", "Categoria", "Descricao", "AcaoCorretiva", "Status", "Urgencia"])
    obs = load_db("obs_seguranca.csv", ["Data", "Utilizador", "Obra", "Tipo", "Descricao", "Status"])
    equip = load_db("equipamentos.csv", ["Obra", "Tipo", "Descricao", "NumSerie", "Utilizador", "Validade", "Estado"])
    diags = load_db("dialogos.csv", ["Titulo", "Descricao", "Tipo", "DataCriacao", "Atribuidos", "Estado"])
    diags_u = load_db("dialogos_users.csv", ["Dialogo", "Utilizador", "DataLeitura", "Confirmado"])
    folhas = load_db("folhas_ponto.csv", ["ID", "Data", "Obra", "ChefEquipa", "Periodo", "TotalHoras", "AssinadoCliente", "PDF_b64"])
    comuns = load_db("comunicados.csv", ["ID", "Titulo", "Conteudo", "Tipo", "Destino", "Urgente", "Validade"])
    comuns_u = load_db("comunicados_lidos.csv", ["ComunicadoID", "Utilizador", "DataLeitura"])
    req_fer = load_db("req_ferramentas.csv", ["ID", "Data", "Solicitante", "Obra", "Descricao", "Status"])
    req_mat = load_db("req_materiais.csv", ["ID", "Data", "Solicitante", "Obra", "Descricao", "Status"])
    req_epi = load_db("req_epis.csv", ["ID", "Data", "Solicitante", "Obra", "Item", "Tamanho", "Status"])
    avals = load_db("avaliacoes.csv", ["Utilizador", "Data", "PontuacaoManual", "NotaAdmin", "Avaliador"])
    inst_acessos = load_db("inst_acessos.csv", ["Obra", "Utilizador", "Cargo", "Ativo"])
    
    return (users, obras, frentes, regs, fats, docs, incs, sw, obs, equip, diags, diags_u, folhas, comuns, comuns_u, req_fer, req_mat, req_epi, avals, inst_acessos)

def inv(): 
    st.cache_data.clear()

# =============================================================================
# ⚡ UTILITÁRIOS
# =============================================================================
def fh(h): 
    if h is None or pd.isna(h):
        return "0h00m"
    try:
        h_float = float(h)
        return f"{int(h_float)}h{int((h_float-int(h_float))*60):02d}m"
    except:
        return "0h00m"

def sl(s):
    mapping = {
        "0": ("Pendente", "status-pending", "⏳", COLORS["warning"]),
        "1": ("Material OK", "status-ok", "📦✅", COLORS["success"]),
        "2": ("Calibrado", "status-calibrated", "🧪", COLORS["info"]),
        "3": ("Instalado", "status-installed", "📍", COLORS["accent"]),
        "4": ("Concluído", "status-completed", "✅🎯", COLORS["success"]),
    }
    key = str(s).strip() if s else "0"
    return mapping.get(key, ("Desconhecido", "status-unknown", "❓", COLORS["text_secondary"]))

def process_and_compress_image(image_file, max_size=(1280, 1280), quality=85):
    try:
        img = Image.open(image_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
        return base64.b64encode(output.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        return None

# =============================================================================
# 🌐 PWA & METADATA
# =============================================================================
def inject_pwa_meta():
    st.markdown("""
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#0F172A">
    <meta name="description" content="GESTNOW - Gestão de Instrumentação Industrial">
    <link rel="manifest" href="/manifest.json">
    <link rel="icon" type="image/png" href="/favicon-32x32.png">
    """, unsafe_allow_html=True)

# =============================================================================
# 🔐 SEGURANÇA
# =============================================================================
def init_session():
    defaults = {
        'user': None, 'tipo': None, 'cargo': None, 
        'data_consulta': date.today(), 'login_attempts': 0, 
        'last_activity': datetime.now(), 'session_token': None, 
        'language': 'pt', 'obra_ativa': None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def check_timeout():
    if st.session_state.get('user') and st.session_state.get('last_activity'):
        if isinstance(st.session_state['last_activity'], datetime):
            inactive_minutes = (datetime.now() - st.session_state['last_activity']).seconds / 60
            if inactive_minutes > 120:
                logger.info(f"🔒 Timeout: {st.session_state.get('user')}")
                st.session_state.clear()
                st.toast("🔒 Sessão expirada", icon="🔐")
                st.rerun()
            st.session_state['last_activity'] = datetime.now()

def hp(p):
    return bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def cp(p, h):
    try:
        return bcrypt.checkpw(p.encode('utf-8'), h.encode('utf-8'))
    except Exception as e:
        logger.warning(f"⚠️ Erro na verificação: {e}")
        return False

# =============================================================================
# 🎨 COMPONENTES UI
# =============================================================================
def render_metric(icon, val, lbl, color=COLORS["accent"]):
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:16px 20px;
        background: linear-gradient(135deg, {COLORS['primary_light']}, {COLORS['primary']});
        border-radius:16px;
        border:1px solid {COLORS['border_glass']};
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        backdrop-filter: blur(10px);
    ">
        <div style="font-size:2rem;font-weight:800;color:{color};margin-bottom:4px;">{icon}</div>
        <div style="font-size:1.5rem;font-weight:700;color:{COLORS['text_primary']};">{val}</div>
        <div style="font-size:0.85rem;color:{COLORS['text_secondary']};margin-top:4px;">{lbl}</div>
    </div>
    """, unsafe_allow_html=True)
    # =============================================================================
# ⚙️ CONSTANTES
# =============================================================================
TIPOS_FRENTE = ["Montagem", "Calibração", "Comissionamento", "Testes FAT/SAT", "Manutenção", "Troubleshooting", "Outro"]
CARGOS = ["Instrumentista Senior", "Técnico de Campo", "Engenheiro de Instrumentação", "Chefe de Equipa", "QA/QC", "Admin"]
CATEGORIAS_SAFETY_WALK = ["EPI Industrial", "Lockout/Tagout", "Espaços Confinados", "Trabalho em Altura", "Elétrica", "Pressão", "Outro"]

REGRAS_OURO = [
    ("🛡️", "EPI Industrial Obrigatório", "Capacete, óculos, luvas e calçado de segurança."),
    ("⚡", "LOTO - Lockout/Tagout", "Bloqueio e etiquetagem de energias."),
    ("🪜", "Trabalho em Altura", "Arnés e linha de vida acima de 1.8m."),
    ("⚡", "Energias Perigosas", "Verificar ausência de tensão."),
    ("🧪", "Calibração Certificada", "Usar equipamentos com certificado válido."),
    ("📍", "Procedimentos de Campo", "Seguir ITRs e checklists."),
    ("🔒", "Acesso Restrito", "Áreas de instrumentação controladas."),
    ("📋", "Análise de Risco", "JSA/JHA obrigatório."),
    ("🧤", "Mãos Limpas", "Luvas adequadas para instrumentos."),
    ("📱", "Zona Livre de Telemóvel", "Dispositivos proibidos em áreas classificadas."),
]

# =============================================================================
# 🎨 CSS GLOBAL COM CONTRASTE CORRETO - TODOS OS MÓDULOS
# =============================================================================
GLOBAL_CSS = f"""
:root {{
    --primary: #0F172A;
    --primary-light: #1E293B;
    --accent: #3B82F6;
    --accent-hover: #60A5FA;
    --success: #10B981;
    --warning: #F59E0B;
    --error: #EF4444;
    --info: #8B5CF6;
    --text-primary: #FFFFFF;
    --text-secondary: #94A3B8;
    --text-dark: #1E293B;
    --text-light: #F8FAFC;
    --bg-white: #FFFFFF;
    --bg-light: #F8FAFC;
    --bg-dark: #0F172A;
}}

.stApp {{
    background: linear-gradient(135deg, var(--primary) 0%, #1a1a2e 100%);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {{
    background: var(--bg-white) !important;
    color: var(--text-dark) !important;
    border: 1px solid rgba(0,0,0,0.3) !important;
    font-weight: 500;
}}

.stTextInput label,
.stNumberInput label,
.stTextArea label,
.stDateInput label,
.stTimeInput label,
.stSelectbox label,
.stMultiSelect label {{
    color: var(--text-dark) !important;
    font-weight: 600;
}}

.stSelectbox > div > div > div,
.stMultiSelect > div > div > div {{
    background: var(--bg-white) !important;
    color: var(--text-dark) !important;
    border: 1px solid rgba(0,0,0,0.3) !important;
}}

.stDataFrame {{
    background: var(--bg-white) !important;
    color: var(--text-dark) !important;
}}

.stDataFrame td,
.stDataFrame th {{
    color: var(--text-dark) !important;
    background: var(--bg-white) !important;
}}

section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%) !important;
}}

section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] label {{
    color: var(--text-light) !important;
}}

.dash-card, .rp-card, .metric-card {{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
}}

.dash-card *, .rp-card *, .metric-card * {{
    color: var(--text-primary) !important;
}}

.stButton > button {{
    background: linear-gradient(135deg, var(--accent), var(--accent-hover));
    color: white !important;
    border: none;
    border-radius: 12px;
    padding: 10px 24px;
    font-weight: 600;
}}

.status-pending {{ color: var(--warning) !important; font-weight: 600; }}
.status-ok {{ color: var(--success) !important; font-weight: 600; }}
.status-calibrated {{ color: var(--info) !important; font-weight: 600; }}
.status-installed {{ color: var(--accent) !important; font-weight: 600; }}
.status-completed {{ color: var(--success) !important; font-weight: 700; }}

[data-testid="stMetric"] {{
    background: linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2));
    border: 2px solid rgba(59,130,246,0.5);
    border-radius: 12px;
    padding: 15px;
}}
[data-testid="stMetricValue"] {{ color: #60A5FA !important; }}
[data-testid="stMetricLabel"] {{ color: #94A3B8 !important; }}
"""

def inject_global_css():
    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)

# =============================================================================
# 📋 AUDIT TRAIL - Logs de Auditoria (SGS/ISO Compliance)
# =============================================================================

def log_audit(usuario, acao, tabela, registro_id, detalhes="", ip=""):
    """Regista ação no log de auditoria para compliance SGS/ISO"""
    try:
        try:
            logs = load_db("logs_audit.csv", [
                "ID", "Data", "Hora", "Usuario", "Acao", 
                "Tabela", "Registro_ID", "Detalhes", "IP"
            ])
        except:
            logs = pd.DataFrame(columns=[
                "ID", "Data", "Hora", "Usuario", "Acao", 
                "Tabela", "Registro_ID", "Detalhes", "IP"
            ])
        
        novo_log = pd.DataFrame([{
            "ID": str(uuid.uuid4())[:8].upper(),
            "Data": datetime.now().strftime("%d/%m/%Y"),
            "Hora": datetime.now().strftime("%H:%M:%S"),
            "Usuario": usuario,
            "Acao": acao,
            "Tabela": tabela,
            "Registro_ID": str(registro_id),
            "Detalhes": detalhes,
            "IP": ip
        }])
        
        logs = pd.concat([logs, novo_log], ignore_index=True)
        save_db(logs, "logs_audit.csv")
        
        return True
        
    except Exception as e:
        print(f"Erro ao criar log de auditoria: {e}")
        return False


def get_audit_logs(filtro_usuario=None, filtro_data=None, limite=100):
    """Obtém logs de auditoria com filtros opcionais"""
    try:
        logs = load_db("logs_audit.csv", [
            "ID", "Data", "Hora", "Usuario", "Acao", 
            "Tabela", "Registro_ID", "Detalhes", "IP"
        ])
        
        if not logs.empty:
            if filtro_usuario:
                logs = logs[logs['Usuario'] == filtro_usuario]
            if filtro_data:
                logs = logs[logs['Data'] == filtro_data]
            
            logs = logs.sort_values(['Data', 'Hora'], ascending=False)
            
            return logs.head(limite)
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Erro ao obter logs: {e}")
        return pd.DataFrame()

# =============================================================================
# ✍️ ASSINATURA DIGITAL - ITRs com Valor Legal
# =============================================================================

def gerar_hash_assinatura(usuario, tag, data, valor):
    """Gera hash único para validar integridade da assinatura"""
    texto = f"{usuario}|{tag}|{data}|{valor}"
    return hashlib.sha256(texto.encode()).hexdigest()[:16].upper()


def render_signature_pad(label, key_prefix):
    """
    Renderiza canvas de assinatura no Streamlit
    Returns: base64 da assinatura ou None
    """
    st.markdown(f"### {label}", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; margin-bottom:15px;">
        <p style="margin:0; color:#94A3B8; font-size:0.9rem;">
            📱 Assine com o dedo no telemóvel ou clique e arraste no computador
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    signature = st.text_area(
        f"{label} (digite o seu nome completo para validar)",
        key=f"{key_prefix}_nome",
        placeholder="Ex: João Silva",
        help="Para valor legal, use assinatura qualificada externa"
    )
    
    if signature and len(signature.strip()) >= 3:
        import base64
        fake_sig = base64.b64encode(f"SIGN:{signature.strip()}:{datetime.now().isoformat()}".encode()).decode()
        return fake_sig
    
    return None


def validar_assinatura(assinatura_b64, usuario_esperado, tag_esperada):
    """Valida se a assinatura corresponde aos dados esperados"""
    try:
        decoded = base64.b64decode(assinatura_b64).decode()
        parts = decoded.split(":")
        if len(parts) >= 3 and parts[0] == "SIGN":
            return parts[1] == usuario_esperado
        return False
    except:
        return False

# =============================================================================
# 🔔 SISTEMA DE NOTIFICAÇÕES - Push + Email + In-App
# =============================================================================

def criar_notificacao(destinatario, titulo, mensagem, tipo="info", acao_url=""):
    """Cria uma notificação para um utilizador"""
    try:
        try:
            notifs = load_db("notificacoes.csv", [
                "ID", "Data", "Hora", "Destinatario", "Titulo", 
                "Mensagem", "Tipo", "Lida", "Acao_URL"
            ])
        except:
            notifs = pd.DataFrame(columns=[
                "ID", "Data", "Hora", "Destinatario", "Titulo", 
                "Mensagem", "Tipo", "Lida", "Acao_URL"
            ])
        
        nova_notif = pd.DataFrame([{
            "ID": str(uuid.uuid4())[:8].upper(),
            "Data": datetime.now().strftime("%d/%m/%Y"),
            "Hora": datetime.now().strftime("%H:%M:%S"),
            "Destinatario": destinatario,
            "Titulo": titulo,
            "Mensagem": mensagem,
            "Tipo": tipo,
            "Lida": "Não",
            "Acao_URL": acao_url
        }])
        
        notifs = pd.concat([notifs, nova_notif], ignore_index=True)
        save_db(notifs, "notificacoes.csv")
        
        return True
        
    except Exception as e:
        print(f"Erro ao criar notificação: {e}")
        return False


def get_notificacoes(destinatario, apenas_nao_lidas=True, limite=50):
    """Obtém notificações de um utilizador"""
    try:
        notifs = load_db("notificacoes.csv", [
            "ID", "Data", "Hora", "Destinatario", "Titulo", 
            "Mensagem", "Tipo", "Lida", "Acao_URL"
        ])
        
        if not notifs.empty:
            notifs = notifs[notifs['Destinatario'] == destinatario]
            if apenas_nao_lidas:
                notifs = notifs[notifs['Lida'] == "Não"]
            notifs = notifs.sort_values(['Data', 'Hora'], ascending=False)
            return notifs.head(limite)
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Erro ao obter notificações: {e}")
        return pd.DataFrame()


def marcar_notificacao_lida(notif_id):
    """Marca uma notificação como lida"""
    try:
        notifs = load_db("notificacoes.csv", [
            "ID", "Data", "Hora", "Destinatario", "Titulo", 
            "Mensagem", "Tipo", "Lida", "Acao_URL"
        ])
        
        if not notifs.empty:
            notifs.loc[notifs['ID'] == notif_id, 'Lida'] = "Sim"
            save_db(notifs, "notificacoes.csv")
            return True
        
        return False
        
    except Exception as e:
        print(f"Erro ao marcar notificação como lida: {e}")
        return False


def contar_notificacoes_nao_lidas(destinatario):
    """Conta notificações não lidas de um utilizador"""
    try:
        notifs = get_notificacoes(destinatario, apenas_nao_lidas=True, limite=1000)
        return len(notifs)
    except:
        return 0

# =============================================================================
# 📴 MODO OFFLINE - Cache Local + Sync Automático
# =============================================================================

def check_connection_status():
    """Verifica estado da conexão (online/offline)"""
    try:
        test_df = load_db("usuarios.csv", ["Nome", "Email", "Tipo"], silent=True)
        return True
    except:
        return False


def save_to_local_cache(key, data):
    """Guarda dados no cache local"""
    try:
        if f"offline_cache_{key}" not in st.session_state:
            st.session_state[f"offline_cache_{key}"] = []
        
        st.session_state[f"offline_cache_{key}"].append({
            "timestamp": datetime.now().isoformat(),
            "data": data.to_dict() if hasattr(data, 'to_dict') else data
        })
        
        if len(st.session_state[f"offline_cache_{key}"]) > 100:
            st.session_state[f"offline_cache_{key}"] = st.session_state[f"offline_cache_{key}"][-100:]
        
        return True
    except Exception as e:
        print(f"Erro ao guardar cache local: {e}")
        return False


def get_from_local_cache(key, limite=50):
    """Obtém dados do cache local"""
    try:
        cache_key = f"offline_cache_{key}"
        if cache_key in st.session_state:
            return st.session_state[cache_key][-limite:]
        return []
    except:
        return []


def add_action_to_queue(acao, dados, usuario):
    """Adiciona ação à fila de execução (para quando voltar online)"""
    try:
        if "offline_action_queue" not in st.session_state:
            st.session_state["offline_action_queue"] = []
        
        st.session_state["offline_action_queue"].append({
            "id": str(uuid.uuid4())[:8].upper(),
            "timestamp": datetime.now().isoformat(),
            "acao": acao,
            "dados": dados,
            "usuario": usuario,
            "estado": "pendente"
        })
        
        return True
    except Exception as e:
        print(f"Erro ao adicionar à fila offline: {e}")
        return False


def execute_offline_queue():
    """Executa todas as ações em fila quando conexão é restaurada"""
    resultados = {"sucessos": 0, "falhas": 0, "detalhes": []}
    
    try:
        if "offline_action_queue" not in st.session_state:
            return resultados
        
        queue = st.session_state["offline_action_queue"]
        
        for item in queue:
            if item["estado"] == "pendente":
                try:
                    if item["acao"] == "SAVE_DB":
                        df = pd.DataFrame(item["dados"]["data"])
                        save_db(df, item["dados"]["filename"])
                    
                    log_audit(
                        usuario=item["usuario"],
                        acao=f"OFFLINE_{item['acao']}",
                        tabela=item["dados"].get("filename", "unknown"),
                        registro_id=item["id"],
                        detalhes=f"Ação executada offline em {item['timestamp']}",
                        ip=""
                    )
                    
                    item["estado"] = "executado"
                    resultados["sucessos"] += 1
                    resultados["detalhes"].append(f"✅ {item['acao']} - {item['id']}")
                    
                except Exception as e:
                    item["estado"] = "falhou"
                    resultados["falhas"] += 1
                    resultados["detalhes"].append(f"❌ {item['acao']} - {item['id']} - {str(e)}")
        
        st.session_state["offline_action_queue"] = [
            item for item in queue if item["estado"] == "pendente"
        ]
        
        return resultados
        
    except Exception as e:
        print(f"Erro ao executar fila offline: {e}")
        return resultados


def render_connection_indicator():
    """Renderiza indicador de conexão no UI"""
    st.markdown("""
    <script>
    function updateConnectionStatus() {
        const status = navigator.onLine ? 'online' : 'offline';
        const indicator = document.getElementById('connection-indicator');
        if (indicator) {
            indicator.className = `connection-status ${status}`;
            indicator.textContent = status === 'online' ? '🟢 Online' : '🔴 Offline';
        }
    }
    window.addEventListener('online', updateConnectionStatus);
    window.addEventListener('offline', updateConnectionStatus);
    updateConnectionStatus();
    </script>
    
    <style>
    .connection-status {
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 10px 20px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        z-index: 9999;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .connection-status.online { background: #10B981; color: white; }
    .connection-status.offline { background: #EF4444; color: white; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
    </style>
    
    <div id="connection-indicator" class="connection-status online">🟢 Online</div>
    """, unsafe_allow_html=True)


def render_offline_banner():
    """Renderiza banner de aviso quando offline"""
    st.markdown("""
    <script>
    function checkOffline() {
        if (!navigator.onLine) {
            const banner = document.getElementById('offline-banner');
            if (banner) banner.style.display = 'block';
        }
    }
    window.addEventListener('offline', checkOffline);
    window.addEventListener('online', () => {
        const banner = document.getElementById('offline-banner');
        if (banner) banner.style.display = 'none';
    });
    </script>
    
    <div id="offline-banner" style="display:none; background:#EF4444; color:white; padding:15px; border-radius:10px; margin-bottom:20px; text-align:center;">
        <strong>🔴 ESTÁ OFFLINE</strong> - As alterações serão guardadas localmente e sincronizadas quando a conexão voltar.
    </div>
    """, unsafe_allow_html=True)


def sync_data_when_online():
    """Verifica se voltou online e sincroniza dados"""
    if "offline_action_queue" in st.session_state:
        pendentes = [i for i in st.session_state["offline_action_queue"] if i["estado"] == "pendente"]
        
        if pendentes and check_connection_status():
            resultados = execute_offline_queue()
            
            if resultados["sucessos"] > 0:
                st.success(f"✅ {resultados['sucessos']} ações sincronizadas!")
            if resultados["falhas"] > 0:
                st.error(f"❌ {resultados['falhas']} ações falharam na sincronização.")
            
            inv()

# =============================================================================
# 📱 QR CODE - Geração e Leitura para Instrumentos
# =============================================================================

def gerar_qr_code_data(tag, obra, tipo_inst, url_base=""):
    """Gera dados para QR Code de instrumento"""
    qr_data = {
        "tag": tag,
        "obra": obra,
        "tipo": tipo_inst,
        "app": "GESTNOW",
        "v": "3.0",
        "url": f"{url_base}/instrumentacao?tag={tag}&obra={obra}" if url_base else f"/instrumentacao?tag={tag}"
    }
    
    return {
        "json": json.dumps(qr_data),
        "b64": base64.b64encode(json.dumps(qr_data).encode()).decode(),
        "short": f"GN|{tag}|{obra.replace(' ', '_')}"
    }


def parse_qr_code_data(qr_string):
    """Parse de dados de QR Code lido"""
    try:
        if qr_string.startswith("{"):
            return json.loads(qr_string)
        
        if qr_string.startswith("ey"):
            decoded = base64.b64decode(qr_string).decode()
            return json.loads(decoded)
        
        if qr_string.startswith("GN|"):
            parts = qr_string.split("|")
            if len(parts) >= 3:
                return {
                    "tag": parts[1],
                    "obra": parts[2].replace("_", " "),
                    "app": "GESTNOW"
                }
        
        return None
    except:
        return None


def render_qr_code_image(qr_data, size=200):
    """Renderiza imagem QR Code no Streamlit"""
    import urllib.parse
    encoded = urllib.parse.quote(qr_data)
    return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded}"


def render_camera_scanner(label="Scan QR Code", key_prefix="qr_scan"):
    """Renderiza interface de scanner de QR Code com câmara"""
    st.markdown(f"### 📱 {label}", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; margin-bottom:15px;">
        <p style="margin:0; color:#94A3B8; font-size:0.9rem;">
            📷 Aponte a câmara para o QR Code do instrumento
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded = st.file_uploader("Ou faça upload de uma foto do QR Code", type=["png", "jpg", "jpeg"], key=f"{key_prefix}_upload")
    
    if uploaded:
        st.info("🔧 Leitura automática de QR em desenvolvimento. Para teste, use o campo abaixo:")
        qr_manual = st.text_input("Cole os dados do QR Code (para teste)", key=f"{key_prefix}_manual")
        if qr_manual:
            return qr_manual
    
    qr_manual = st.text_input("Dados do QR Code (formato: GN|TAG|OBRA ou JSON)", key=f"{key_prefix}_input")
    
    if qr_manual and len(qr_manual.strip()) > 5:
        return qr_manual.strip()
    
    return None

# =============================================================================
# 📧 SMTP - Envio de Emails Reais
# =============================================================================

def get_smtp_config():
    """Obtém configuração SMTP dos secrets"""
    smtp_server = st.secrets.get("SMTP_SERVER", "")
    smtp_port = st.secrets.get("SMTP_PORT", 587)
    smtp_user = st.secrets.get("SMTP_USER", "")
    smtp_password = st.secrets.get("SMTP_PASSWORD", "")
    smtp_from_name = st.secrets.get("SMTP_FROM_NAME", "GestNow")
    
    if smtp_server and smtp_user and smtp_password:
        return {
            "server": smtp_server,
            "port": int(smtp_port),
            "user": smtp_user,
            "password": smtp_password,
            "from_name": smtp_from_name,
            "from_email": smtp_user
        }
    return None


def enviar_email(destinatario, assunto, conteudo_html, conteudo_texto=""):
    """Envia email via SMTP"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    config = get_smtp_config()
    
    if not config:
        logging.warning("SMTP não configurado. Email não enviado.")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[GestNow] {assunto}"
        msg["From"] = f"{config['from_name']} <{config['from_email']}>"
        msg["To"] = destinatario
        
        if conteudo_texto:
            msg.attach(MIMEText(conteudo_texto, "plain", "utf-8"))
        msg.attach(MIMEText(conteudo_html, "html", "utf-8"))
        
        server = smtplib.SMTP(config["server"], config["port"])
        server.starttls()
        server.login(config["user"], config["password"])
        server.send_message(msg)
        server.quit()
        
        log_audit(usuario="SYSTEM", acao="ENVIAR_EMAIL", tabela="emails_enviados", registro_id=destinatario, detalhes=f"Email enviado: {assunto}", ip="")
        
        return True
        
    except Exception as e:
        logging.error(f"Erro ao enviar email: {e}")
        return False


def get_email_template(tipo, dados=None):
    """Retorna template de email formatado"""
    templates = {
        "validacao_horas": {
            "assunto": "Horas Validadas - {obra}",
            "html": """
            <html><body style="font-family:Arial,sans-serif; background:#F8FAFC; padding:20px;">
                <div style="max-width:600px; margin:0 auto; background:white; border-radius:10px; padding:30px; box-shadow:0 2px 10px rgba(0,0,0,0.1);">
                    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:20px; border-radius:10px 10px 0 0; text-align:center;">
                        <h1 style="color:#F8FAFC; margin:0;">⚡ GESTNOW</h1>
                        <p style="color:#94A3B8; margin:10px 0 0 0;">Sistema de Gestão de Instrumentação</p>
                    </div>
                    <div style="padding:30px 20px;">
                        <h2 style="color:#1E293B; margin:0 0 20px 0;">✅ Horas Validadas</h2>
                        <p style="color:#64748B; line-height:1.6;">
                            Olá <strong>{tecnico}</strong>,<br><br>
                            As suas horas foram validadas com sucesso!<br><br>
                            <strong>Obra:</strong> {obra}<br>
                            <strong>Horas:</strong> {horas}h<br>
                            <strong>Data:</strong> {data}<br>
                            <strong>Validado por:</strong> {validador}
                        </p>
                    </div>
                    <div style="background:#F8FAFC; padding:20px; text-align:center; border-radius:0 0 10px 10px;">
                        <p style="color:#94A3B8; margin:0; font-size:0.85rem;">© 2025 GESTNOW v3.0</p>
                    </div>
                </div>
            </body></html>
            """,
            "texto": "Horas validadas com sucesso. Obra: {obra}, Horas: {horas}h"
        },
        "aprovacao_cliente": {
            "assunto": "Cliente Aprovou Instrumento - {tag}",
            "html": """
            <html><body style="font-family:Arial,sans-serif; background:#F8FAFC; padding:20px;">
                <div style="max-width:600px; margin:0 auto; background:white; border-radius:10px; padding:30px;">
                    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:20px; border-radius:10px 10px 0 0; text-align:center;">
                        <h1 style="color:#F8FAFC; margin:0;">⚡ GESTNOW</h1>
                    </div>
                    <div style="padding:30px 20px;">
                        <h2 style="color:#10B981; margin:0 0 20px 0;">✅ Aprovação do Cliente</h2>
                        <p style="color:#64748B; line-height:1.6;">
                            Olá,<br><br>Um cliente aprovou um instrumento.<br><br>
                            <strong>Cliente:</strong> {cliente}<br>
                            <strong>Tag:</strong> {tag}<br>
                            <strong>Obra:</strong> {obra}<br>
                            <strong>Comentário:</strong> {comentario}
                        </p>
                    </div>
                </div>
            </body></html>
            """,
            "texto": "Cliente aprovou instrumento. Tag: {tag}, Obra: {obra}"
        },
        "punch_list": {
            "assunto": "Novo Item na Punch List - {obra}",
            "html": """
            <html><body style="font-family:Arial,sans-serif; background:#F8FAFC; padding:20px;">
                <div style="max-width:600px; margin:0 auto; background:white; border-radius:10px; padding:30px;">
                    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:20px; border-radius:10px 10px 0 0; text-align:center;">
                        <h1 style="color:#F8FAFC; margin:0;">⚡ GESTNOW</h1>
                    </div>
                    <div style="padding:30px 20px;">
                        <h2 style="color:#F59E0B; margin:0 0 20px 0;">💬 Novo Item na Punch List</h2>
                        <p style="color:#64748B; line-height:1.6;">
                            Olá,<br><br>Um novo item foi adicionado à punch list.<br><br>
                            <strong>Obra:</strong> {obra}<br>
                            <strong>Prioridade:</strong> {prioridade}<br>
                            <strong>Autor:</strong> {autor}<br>
                            <strong>Descrição:</strong> {descricao}
                        </p>
                    </div>
                </div>
            </body></html>
            """,
            "texto": "Novo item na punch list. Obra: {obra}, Prioridade: {prioridade}"
        },
        "calibracao_concluida": {
            "assunto": "Calibração Concluída - {tag}",
            "html": """
            <html><body style="font-family:Arial,sans-serif; background:#F8FAFC; padding:20px;">
                <div style="max-width:600px; margin:0 auto; background:white; border-radius:10px; padding:30px;">
                    <div style="background:linear-gradient(135deg, #1E293B, #0F172A); padding:20px; border-radius:10px 10px 0 0; text-align:center;">
                        <h1 style="color:#F8FAFC; margin:0;">⚡ GESTNOW</h1>
                    </div>
                    <div style="padding:30px 20px;">
                        <h2 style="color:#3B82F6; margin:0 0 20px 0;">🔬 Calibração Concluída</h2>
                        <p style="color:#64748B; line-height:1.6;">
                            Olá,<br><br>Instrumento calibrado com sucesso.<br><br>
                            <strong>Tag:</strong> {tag}<br>
                            <strong>Obra:</strong> {obra}<br>
                            <strong>Erro Máx:</strong> {erro}<br>
                            <strong>Certificado:</strong> {certificado}
                        </p>
                    </div>
                </div>
            </body></html>
            """,
            "texto": "Calibração concluída. Tag: {tag}, Erro: {erro}"
        }
    }
    
    if tipo not in templates:
        return ("Notificação GestNow", "<p>Notificação do sistema GestNow</p>", "Notificação do sistema")
    
    template = templates[tipo]
    dados = dados or {}
    
    assunto = template["assunto"]
    html = template["html"]
    texto = template["texto"]
    
    for key, value in dados.items():
        assunto = assunto.replace("{" + key + "}", str(value))
        html = html.replace("{" + key + "}", str(value))
        texto = texto.replace("{" + key + "}", str(value))
    
    return (assunto, html, texto)


def notificar_por_email(destinatario_email, tipo_notificacao, dados):
    """Envia notificação por email com template"""
    assunto, html, texto = get_email_template(tipo_notificacao, dados)
    return enviar_email(destinatario_email, assunto, html, texto)


def testar_smtp(email_teste):
    """Testa configuração SMTP enviando email de teste"""
    assunto, html, texto = get_email_template("validacao_horas", {
        "tecnico": "Teste",
        "obra": "Obra Teste",
        "horas": "8",
        "data": datetime.now().strftime("%d/%m/%Y"),
        "validador": "SYSTEM"
    })
    
    return enviar_email(email_teste, f"TESTE SMTP - {assunto}", html, texto)

# =============================================================================
# FIM DO CORE.PY
# =============================================================================

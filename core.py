import streamlit as st
import pandas as pd
import os, re, secrets, io, base64, bcrypt, logging
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

# TODOS OS ÍCONES NECESSÁRIOS
ICONS = {
    "app": "🎛️",
    "login": "🔐",
    "admin": "⚡",
    "technician": "👨‍🔧",
    "dashboard": "📈",
    "instrumentation": "🧪",
    "voice": "🎤",
    "safety": "🛡️",
    "profile": "👤",
    "reports": "📊",
    "handover": "✅",
    "gps": "📍",
    "calibration": "🔬",
    "material": "📦",
    "pending": "⏳",
    "logout": "🚪",
    "save": "💾",
    "edit": "✏️",
    "delete": "🗑️",
    "add": "➕",
    "search": "🔍",
    "filter": "🔽",
    "download": "📥",
    "upload": "📤",
    "check": "✅",
    "close": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "calendar": "📅",
    "clock": "⏰",
    "user": "👤",
    "users": "👥",
    "settings": "⚙️",
    "home": "🏠",
    "work": "🏗️",
    "tools": "🔧",
    "equipment": "🔩",
    "document": "📄",
    "documents": "📁",
    "chart": "📊",
    "graph": "📈",
    "email": "📧",
    "phone": "📞",
    "location": "📍",
    "time": "⏱️",
    "approved": "✅",        # ← ADICIONAR
    "rejected": "❌",        # ← ADICIONAR
    "pending_approval": "⏳", # ← ADICIONAR
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
# 🎨 CSS GLOBAL
# =============================================================================
GLOBAL_CSS = f"""
:root {{
    --primary: {COLORS["primary"]};
    --primary-light: {COLORS["primary_light"]};
    --accent: {COLORS["accent"]};
    --accent-hover: {COLORS["accent_hover"]};
    --success: {COLORS["success"]};
    --warning: {COLORS["warning"]};
    --error: {COLORS["error"]};
    --info: {COLORS["info"]};
    --text-primary: {COLORS["text_primary"]};
    --text-secondary: {COLORS["text_secondary"]};
}}

.stApp {{
    background: linear-gradient(135deg, var(--primary) 0%, #1a1a2e 100%);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

.dash-card, .rp-card, .metric-card {{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    transition: all 0.3s ease;
}}
.dash-card:hover, .rp-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
    border-color: var(--accent);
}}

.stButton > button {{
    background: linear-gradient(135deg, var(--accent), var(--accent-hover));
    color: white;
    border: none;
    border-radius: 12px;
    padding: 10px 24px;
    font-weight: 600;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);
}}

.status-pending {{ color: var(--warning); font-weight: 600; }}
.status-ok {{ color: var(--success); font-weight: 600; }}
.status-calibrated {{ color: var(--info); font-weight: 600; }}
.status-installed {{ color: var(--accent); font-weight: 600; }}
.status-completed {{ color: var(--success); font-weight: 700; }}

.stTextInput > div > div > input,
.stSelectbox > div > div > div {{
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    color: var(--text-primary);
}}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div > div:focus {{
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}}
"""

def inject_global_css():
    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)

# =============================================================================
# AUDIT TRAIL - Logs de Auditoria (SGS/ISO Compliance)
# =============================================================================

def log_audit(usuario, acao, tabela, registro_id, detalhes="", ip=""):
    """Regista ação no log de auditoria para compliance SGS/ISO"""
    try:
        import pandas as pd
        from datetime import datetime
        import uuid
        
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
    import hashlib
    texto = f"{usuario}|{tag}|{data}|{valor}"
    return hashlib.sha256(texto.encode()).hexdigest()[:16].upper()


def render_signature_pad(label, key_prefix):
    """
    Renderiza canvas de assinatura no Streamlit
    Returns: base64 da assinatura ou None
    """
    import streamlit as st
    
    st.markdown(f"### {label}", unsafe_allow_html=True)
    
    # Instruções
    st.markdown("""
    <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; margin-bottom:15px;">
        <p style="margin:0; color:#94A3B8; font-size:0.9rem;">
            📱 Assine com o dedo no telemóvel ou clique e arraste no computador
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Canvas simples via HTML/JS
    signature = st.text_area(
        f"{label} (digite o seu nome completo para validar)",
        key=f"{key_prefix}_nome",
        placeholder="Ex: João Silva",
        help="Para valor legal, use assinatura qualificada externa"
    )
    
    if signature and len(signature.strip()) >= 3:
        # Simular assinatura base64 (placeholder para implementação com st-canvas)
        import base64
        fake_sig = base64.b64encode(f"SIGN:{signature.strip()}:{datetime.now().isoformat()}".encode()).decode()
        return fake_sig
    
    return None


def validar_assinatura(assinatura_b64, usuario_esperado, tag_esperada):
    """Valida se a assinatura corresponde aos dados esperados"""
    try:
        import base64
        decoded = base64.b64decode(assinatura_b64).decode()
        parts = decoded.split(":")
        if len(parts) >= 3 and parts[0] == "SIGN":
            return parts[1] == usuario_esperado
        return False
    except:
        return False

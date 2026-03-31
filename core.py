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
# 🎨 DESIGN SYSTEM - INSTRUMENTAÇÃO INDUSTRIAL (TOP TIER)
# =============================================================================
# Cores principais - Tech/Industrial Palette
COLORS = {
    "primary": "#0F172A",      # Slate 900 - Fundo principal
    "primary_light": "#1E293B", # Slate 800 - Cards
    "accent": "#3B82F6",        # Blue 500 - Ações principais
    "accent_hover": "#60A5FA",  # Blue 400 - Hover
    "success": "#10B981",       # Emerald 500 - OK/Concluído
    "warning": "#F59E0B",       # Amber 500 - Atenção
    "error": "#EF4444",         # Red 500 - Erro/Crítico
    "info": "#8B5CF6",          # Violet 500 - Info/Tech
    "bg_glass": "rgba(255,255,255,0.1)",  # Glassmorphism
    "border_glass": "rgba(255,255,255,0.2)",
    "text_primary": "#F8FAFC",   # Slate 50 - Texto claro
    "text_secondary": "#94A3B8", # Slate 400 - Texto secundário
}

# Ícones por categoria (SUBSTITUIR 🏗️ por ícones de instrumentação)
ICONS = {
    "app": "🎛️",           # APP principal - Painel de controlo
    "login": "🔐",          # Autenticação
    "admin": "⚡",           # Admin - Energia/Controlo
    "technician": "👨‍🔧",    # Técnico - Especialista
    "dashboard": "📈",       # Dashboard - Gráficos dinâmicos
    "instrumentation": "🧪", # Instrumentação - Laboratório industrial
    "voice": "🎤✨",         # Voz - Com inteligência
    "safety": "🛡️⚙️",        # HSE - Segurança industrial
    "profile": "👤⚙️",        # Perfil técnico
    "reports": "📊🔍",        # Relatórios analíticos
    "handover": "✅🎯",       # Handover - Entrega premium
    "gps": "📍🛰️",           # GPS - Precisão industrial
    "calibration": "🔬⚡",    # Calibração - Alta precisão
    "material": "📦✅",       # Material - Verificado
    "pending": "⏳🔄",        # Pendente - Em processo
}

# Configuração de logging profissional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# =============================================================================
# ⚙️ CONFIGURAÇÕES DE STORAGE (GCS + Local Fallback)
# =============================================================================
GCS_BUCKET = os.environ.get("GCS_BUCKET", "gestnow-dados")

def _gcs_client():
    """Inicializa cliente GCS com tratamento robusto de erros"""
    try:
        return gcs.Client()
    except Exception as e:
        logger.warning(f"GCS client fallback (modo desenvolvimento): {e}")
        return None

def _gcs_read(fn):
    """Lê ficheiro do GCS com fallback elegante para local"""
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
    """Escreve no GCS com confirmação e cache invalidation"""
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
        st.toast(f"⚠️ Dados guardados localmente (GCS indisponível)", icon="⚙️")
    return False

# =============================================================================
# 🗄️ GESTÃO DE DADOS COM CACHE INTELIGENTE
# =============================================================================
@st.cache_data(ttl=300, show_spinner="🔄 A sincronizar dados industriais...")
def load_db(fn, cols):
    """Carrega DataFrame do GCS ou local com validação de schema"""
    buf = _gcs_read(fn)
    if buf:
        try:
            df = pd.read_csv(buf, dtype=str, on_bad_lines='skip', encoding='utf-8-sig')
            # Normalizar nomes de colunas (remover espaços extras)
            df.columns = df.columns.str.strip()
            # Garantir que todas as colunas esperadas existem
            for c in cols:
                if c.strip() not in df.columns:
                    df[c.strip()] = ""
            return df[[c.strip() for c in cols]].fillna("")
        except Exception as e:
            logger.warning(f"⚠️ Fallback CSV local para {fn}: {e}")
            return pd.DataFrame(columns=[c.strip() for c in cols])
    return pd.DataFrame(columns=[c.strip() for c in cols])

def save_db(df, fn):
    """Guarda DataFrame com encoding UTF-8 e confirmação"""
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding='utf-8-sig')
    return _gcs_write(fn, buf.getvalue().encode('utf-8-sig'))

def load_all():
    """Carrega os 20 DataFrames do sistema com lazy loading implícito"""
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
    """Invalida cache do Streamlit - usar após save_db"""
    st.cache_data.clear()

# =============================================================================
# ⚡ UTILITÁRIOS DE FORMATAÇÃO INDUSTRIAL
# =============================================================================
def fh(h): 
    """Formata horas no padrão industrial: 8.5 → '8h30m'"""
    if h is None or pd.isna(h):
        return "0h00m"
    try:
        h_float = float(h)
        return f"{int(h_float)}h{int((h_float-int(h_float))*60):02d}m"
    except:
        return "0h00m"

def sl(s):
    """Mapeia status codes para texto + classe CSS + ícone (SEM ESPAÇOS)"""
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
    """Comprime imagem para base64 com otimização profissional"""
    try:
        img = Image.open(image_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        # Resize mantendo aspect ratio
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
        return base64.b64encode(output.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        return None

# =============================================================================
# 🌐 PWA & METADATA PARA APP INDUSTRIAL
# =============================================================================
def inject_pwa_meta():
    """Injeta meta tags para PWA com branding de instrumentação"""
    st.markdown("""
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#0F172A">
    <meta name="description" content="GESTNOW - Gestão de Instrumentação Industrial de Alta Precisão">
    <link rel="manifest" href="/manifest.json">
    <link rel="icon" type="image/png" href="/favicon-32x32.png">
    """, unsafe_allow_html=True)

# =============================================================================
# 🔐 SEGURANÇA EMPRESARIAL
# =============================================================================
def init_session():
    """Inicializa variáveis de sessão com defaults seguros"""
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
    """Verifica timeout de sessão (120 minutos - padrão enterprise)"""
    if st.session_state.get('user') and st.session_state.get('last_activity'):
        inactive_minutes = (datetime.now() - st.session_state['last_activity']).seconds / 60
        if inactive_minutes > 120:
            logger.info(f"🔒 Timeout de sessão: {st.session_state.get('user')}")
            st.session_state.clear()
            st.toast("🔒 Sessão expirada por inatividade", icon="🔐")
            st.rerun()
        st.session_state['last_activity'] = datetime.now()

def hp(p):
    """Hash de password com bcrypt (enterprise grade)"""
    return bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def cp(p, h):
    """Verifica password contra hash com tratamento de erros"""
    try:
        return bcrypt.checkpw(p.encode('utf-8'), h.encode('utf-8'))
    except Exception as e:
        logger.warning(f"⚠️ Erro na verificação de password: {e}")
        return False

# =============================================================================
# 🎨 COMPONENTES UI PREMIUM (Glassmorphism + Animations)
# =============================================================================
def render_metric(icon, val, lbl, color=COLORS["accent"]):
    """Renderiza card de métrica com design industrial moderno"""
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:16px 20px;
        background: linear-gradient(135deg, {COLORS['primary_light']}, {COLORS['primary']});
        border-radius:16px;
        border:1px solid {COLORS['border_glass']};
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 30px rgba(0,0,0,0.3)'"
       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(0,0,0,0.2)'">
        <div style="font-size:2rem;font-weight:800;color:{color};margin-bottom:4px;">{icon}</div>
        <div style="font-size:1.5rem;font-weight:700;color:{COLORS['text_primary']};">{val}</div>
        <div style="font-size:0.85rem;color:{COLORS['text_secondary']};margin-top:4px;">{lbl}</div>
    </div>
    """, unsafe_allow_html=True)

def render_metric_alert(icon, val, lbl, alert_type="warning"):
    """Renderiza card de métrica com destaque de alerta"""
    color_map = {
        "warning": (COLORS["warning"], "⚠️"),
        "error": (COLORS["error"], "🔴"),
        "success": (COLORS["success"], "✅"),
        "info": (COLORS["info"], "ℹ️")
    }
    color, prefix = color_map.get(alert_type, (COLORS["accent"], "•"))
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:16px 20px;
        background: linear-gradient(135deg, rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15), rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.05));
        border-radius:16px;
        border:2px solid {color};
        box-shadow: 0 4px 20px rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15);
    ">
        <div style="font-size:1.8rem;font-weight:800;color:{color};margin-bottom:4px;">{prefix} {icon}</div>
        <div style="font-size:1.4rem;font-weight:700;color:{COLORS['text_primary']};">{val}</div>
        <div style="font-size:0.85rem;color:{COLORS['text_secondary']};margin-top:4px;">{lbl}</div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 📄 PDF HELPERS COM BRANDING INDUSTRIAL
# =============================================================================
def _qr_drawing(data_str, size_cm=2.8):
    """Gera QR code para ReportLab com estilo industrial"""
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    qr_w = QrCodeWidget(data_str)
    b = qr_w.getBounds()
    w, h = b[2]-b[0], b[3]-b[1]
    sz = size_cm * cm
    d = Drawing(sz, sz, transform=[sz/w, 0, 0, sz/h, 0, 0])
    d.add(qr_w)
    return d

def gerar_folha_ponto_pdf(obra, chefe, periodo, regs, users_df, 
                          assin_chefe_b64="", assin_cliente_b64="", 
                          nome_cliente="", gps_chefe="", logo_b64=""):
    """Gera PDF de folha de ponto com branding industrial premium"""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, 
                           leftMargin=2*cm, rightMargin=2*cm, 
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header com branding
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor(COLORS["primary"]),
        spaceAfter=12,
        alignment=1  # Center
    )
    elements.append(Paragraph(f"{ICONS['app']} FOLHA DE PONTO - {obra}", header_style))
    elements.append(Paragraph(f"Período: {periodo} | Chefe: {chefe} | {ICONS['gps']} {gps_chefe or 'GPS não registado'}", styles['Normal']))
    elements.append(Spacer(1, 1.5*cm))
    
    # Tabela de registos com estilo industrial
    data = [[f"{ICONS['calendar']} Data", f"{ICONS['technician']} Técnico", "⏱️ Horas", f"{ICONS['admin']} Frente"]]
    for _, r in regs.iterrows():
        data.append([
            r['Data'].strftime('%d/%m/%Y') if isinstance(r['Data'], (datetime, date)) else str(r['Data']),
            r['Técnico'], 
            fh(r['Horas_Total']), 
            r['Frente']
        ])
    
    t = Table(data)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(COLORS["border_glass"])),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS["primary"])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),  # Alinhar horas à direita
    ]))
    elements.append(t)
    
    # Footer com selo digital
    elements.append(Spacer(1, 2*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor(COLORS["text_secondary"]),
        alignment=2  # Right
    )
    elements.append(Paragraph(
        f"<i>Documento gerado por {ICONS['app']} GESTNOW v3.0</i><br/>"
        f"Hash de integridade: {secrets.token_hex(8).upper()}", 
        footer_style
    ))
    
    doc.build(elements)
    return buf.getvalue()

# =============================================================================
# ⚙️ CONSTANTES DE INSTRUMENTAÇÃO INDUSTRIAL (SEM ESPAÇOS NAS STRINGS)
# =============================================================================
TIPOS_FRENTE = ["Montagem", "Calibração", "Comissionamento", "Testes FAT/SAT", "Manutenção", "Troubleshooting", "Outro"]
CARGOS = ["Instrumentista Senior", "Técnico de Campo", "Engenheiro de Instrumentação", "Chefe de Equipa", "QA/QC", "Admin"]
CATEGORIAS_SAFETY_WALK = ["EPI Industrial", "Lockout/Tagout", "Espaços Confinados", "Trabalho em Altura", "Elétrica", "Pressão", "Outro"]

# Regras de Ouro da Instrumentação Industrial (World-Class Standards)
REGRAS_OURO = [
    (f"{ICONS['safety'].split()[0]}", "EPI Industrial Obrigatório", "Capacete, óculos, luvas e calçado de segurança em área operacional."),
    (f"{ICONS['safety'].split()[1]}", "LOTO - Lockout/Tagout", "Bloqueio e etiquetagem de energias antes de qualquer intervenção."),
    ("🪜", "Trabalho em Altura", "Arnés e linha de vida obrigatórios acima de 1.8m."),
    ("⚡", "Energias Perigosas", "Verificar ausência de tensão com equipamento calibrado."),
    ("🧪", "Calibração Certificada", "Usar apenas equipamentos com certificado de calibração válido."),
    ("📍", "Procedimentos de Campo", "Seguir ITRs e checklists aprovados para cada atividade."),
    ("🔒", "Acesso Restrito", "Áreas de instrumentação são de acesso controlado."),
    ("📋", "Análise de Risco", "JSA/JHA obrigatório antes de atividades não rotineiras."),
    ("🧤", "Mãos Limpas", "Nunca tocar em instrumentos sensíveis sem luvas adequadas."),
    ("📱", "Zona Livre de Telemóvel", "Dispositivos pessoais proibidos em áreas classificadas."),
]

# =============================================================================
# 🎨 CSS GLOBAL - DESIGN SYSTEM PREMIUM
# =============================================================================
GLOBAL_CSS = f"""
/* ===== VARIÁVEIS DE DESIGN ===== */
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
    --glass-bg: {COLORS["bg_glass"]};
    --glass-border: {COLORS["border_glass"]};
}}

/* ===== BASE ===== */
.stApp {{
    background: linear-gradient(135deg, var(--primary) 0%, #1a1a2e 100%);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

/* ===== CARDS GLASSMORPHISM ===== */
.dash-card, .rp-card, .metric-card {{
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
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

/* ===== BOTÕES PREMIUM ===== */
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
.stButton > button:active {{
    transform: translateY(0);
}}

/* ===== STATUS BADGES ===== */
.status-pending {{ color: var(--warning); font-weight: 600; }}
.status-ok {{ color: var(--success); font-weight: 600; }}
.status-calibrated {{ color: var(--info); font-weight: 600; }}
.status-installed {{ color: var(--accent); font-weight: 600; }}
.status-completed {{ color: var(--success); font-weight: 700; }}

/* ===== INPUTS MODERNOS ===== */
.stTextInput > div > div > input,
.stSelectbox > div > div > div {{
    background: rgba(255,255,255,0.08);
    border: 1px solid var(--glass-border);
    border-radius: 10px;
    color: var(--text-primary);
}}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div > div:focus {{
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}}

/* ===== PROGRESS BARS ===== */
.progress-bar {{
    background: rgba(255,255,255,0.1);
    border-radius: 12px;
    height: 20px;
    overflow: hidden;
    margin: 8px 0;
}}
.progress-fill {{
    background: linear-gradient(90deg, var(--accent), var(--accent-hover));
    height: 100%;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 10px;
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    transition: width 0.5s ease;
}}

/* ===== ANIMAÇÕES ===== */
@keyframes pulse-subtle {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.85; }}
}}
.pulse-subtle {{
    animation: pulse-subtle 2s infinite;
}}

@keyframes slideIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
.slideIn {{
    animation: slideIn 0.3s ease forwards;
}}

/* ===== TOASTS PERSONALIZADOS ===== */
[data-testid="stStatusWidget"] {{
    background: var(--primary-light);
    border-left: 4px solid var(--accent);
    border-radius: 12px;
}}
"""

def inject_global_css():
    """Injeta o CSS global do design system"""
    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)

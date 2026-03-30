import streamlit as st
import pandas as pd
import os, re, secrets, io, base64, bcrypt
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

# --- CONFIGURAÇÕES DE STORAGE ---
GCS_BUCKET = os.environ.get("GCS_BUCKET", "gestnow-dados")

def _gcs_client():
    return gcs.Client()

def _gcs_read(fn):
    try:
        bucket = _gcs_client().bucket(GCS_BUCKET)
        blob = bucket.blob(f"data/{fn}")
        if blob.exists():
            return io.BytesIO(blob.download_as_bytes())
    except Exception as e:
        print(f"Erro GCS Read {fn}: {e}")
    return None

def _gcs_write(fn, content_bytes):
    try:
        bucket = _gcs_client().bucket(GCS_BUCKET)
        blob = bucket.blob(f"data/{fn}")
        blob.metadata = {"last_updated": datetime.now().isoformat()}
        blob.upload_from_string(content_bytes, content_type="text/csv")
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro Crítico GCS Write {fn}: {e}")
        return False

# --- GESTÃO DE DADOS ---
@st.cache_data(ttl=300)
def load_db(fn, cols):
    buf = _gcs_read(fn)
    if buf:
        try:
            df = pd.read_csv(buf, dtype=str, on_bad_lines='skip')
            df.columns = df.columns.str.strip()
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols].fillna("")
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_db(df, fn):
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding='utf-8-sig')
    return _gcs_write(fn, buf.getvalue().encode('utf-8-sig'))

def load_all():
    users = load_db("usuarios.csv", ["Nome","Password","Tipo","Email","Telefone","Cargo","NIF","NISS","CC","DataNasc","Nacionalidade","Morada","Foto","PrecoHora","PrecoHoraStatus","PrecoHoraData","PIN"])
    obras = load_db("obras_lista.csv", ["Obra","Codigo","Cliente","Local","Ativa","Latitude","Longitude","Raio_Validacao","DataInicio","DataFim","TipoObra","AssinaturaObrigatoria","Logo_b64"])
    frentes = load_db("frentes_lista.csv", ["Obra","Frente","Tipo","Responsavel"])
    regs = load_db("registos.csv", ["Data","Técnico","Obra","Frente","TipoFrente","Turnos","Relatorio","Status","Horas_Total","Localizacao_Checkin","Localizacao_Checkout"])
    if not regs.empty:
        regs['Data'] = pd.to_datetime(regs['Data'], dayfirst=True, errors='coerce')
        regs['Horas_Total'] = pd.to_numeric(regs['Horas_Total'], errors='coerce').fillna(0)
    
    fats = load_db("faturas.csv", ["Numero","Cliente","Valor","Status","Data_Emissao","Obra"])
    docs = load_db("documentos.csv", ["Utilizador","Tipo","Nome","Validade"])
    incs = load_db("incidentes.csv", ["Data","Utilizador","Obra","Tipo","Descricao","Gravidade","Status"])
    sw = load_db("safety_walks.csv", ["Data","Utilizador","Obra","Categoria","Descricao","AcaoCorretiva","Status","Urgencia"])
    obs = load_db("obs_seguranca.csv", ["Data","Utilizador","Obra","Tipo","Descricao","Status"])
    equip = load_db("equipamentos.csv", ["Obra","Tipo","Descricao","NumSerie","Utilizador","Validade","Estado"])
    diags = load_db("dialogos.csv", ["Titulo","Descricao","Tipo","DataCriacao","Atribuidos","Estado"])
    diags_u = load_db("dialogos_users.csv", ["Dialogo","Utilizador","DataLeitura","Confirmado"])
    folhas = load_db("folhas_ponto.csv", ["ID","Data","Obra","ChefEquipa","Periodo","TotalHoras","AssinadoCliente","PDF_b64"])
    comuns = load_db("comunicados.csv", ["ID","Titulo","Conteudo","Tipo","Destino","Urgente","Validade"])
    comuns_u = load_db("comunicados_lidos.csv", ["ComunicadoID","Utilizador","DataLeitura"])
    req_fer = load_db("req_ferramentas.csv", ["ID","Data","Solicitante","Obra","Descricao","Status"])
    req_mat = load_db("req_materiais.csv", ["ID","Data","Solicitante","Obra","Descricao","Status"])
    req_epi = load_db("req_epis.csv", ["ID","Data","Solicitante","Obra","Item","Tamanho","Status"])
    avals = load_db("avaliacoes.csv", ["Utilizador","Data","PontuacaoManual","NotaAdmin","Avaliador"])
    inst_acessos = load_db("inst_acessos.csv", ["Obra","Utilizador","Cargo","Ativo"])

    return (users, obras, frentes, regs, fats, docs, incs, sw, obs, equip, diags, diags_u, folhas, comuns, comuns_u, req_fer, req_mat, req_epi, avals, inst_acessos)

def inv(): st.cache_data.clear()

# --- UTILITÁRIOS ---
def fh(h): return f"{int(h)}h{int((h-int(h))*60):02d}m"
def sl(s): return {"0":("Pendente","status-pendente"),"1":("Aprovado","status-aprovado"),"2":("Fechado","status-fechado")}.get(s,("—","status-fechado"))

def process_and_compress_image(image_file, max_size=(1024, 1024), quality=75):
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail(max_size, Image.LANCZOS)
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(output.getvalue()).decode()

def inject_pwa_meta():
    st.markdown("""
    <link rel="manifest" href="https://raw.githubusercontent.com/user/repo/main/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    """, unsafe_allow_html=True)

# --- SEGURANÇA ---
def init_session():
    for k, v in {'user': None, 'tipo': None, 'cargo': None, 'data_consulta': date.today(),
                'login_attempts': 0, 'last_activity': datetime.now(), 'session_token': None, 'language': 'pt'}.items():
        if k not in st.session_state: st.session_state[k] = v

def check_timeout():
    if st.session_state.get('user') and st.session_state.get('last_activity'):
        if (datetime.now() - st.session_state['last_activity']).seconds / 60 > 120:
            st.session_state.clear()
            st.rerun()
    st.session_state['last_activity'] = datetime.now()

def hp(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def cp(p, h):
    try: return bcrypt.checkpw(p.encode(), h.encode())
    except: return False

# --- COMPONENTES UI ---
def render_metric(icon, val, lbl):
    st.markdown(f"<div class='metric-card'><div class='metric-icon'>{icon}</div><div class='metric-value'>{val}</div><div class='metric-label'>{lbl}</div></div>", unsafe_allow_html=True)

def render_metric_red(icon, val, lbl):
    st.markdown(f"<div class='metric-card-red'><div class='mic-icon'>{icon}</div><div class='mic-value'>{val}</div><div class='mic-label'>{lbl}</div></div>", unsafe_allow_html=True)

# --- PDF HELPERS ---
def _qr_drawing(data_str, size_cm=2.8):
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    qr_w = QrCodeWidget(data_str)
    b = qr_w.getBounds()
    w, h = b[2]-b[0], b[3]-b[1]
    sz = size_cm * cm
    d = Drawing(sz, sz, transform=[sz/w, 0, 0, sz/h, 0, 0])
    d.add(qr_w)
    return d

def gerar_folha_ponto_pdf(obra, chefe, periodo, regs, users_df, assin_chefe_b64="", assin_cliente_b64="", nome_cliente="", gps_chefe="", logo_b64=""):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    el = []
    sty = getSampleStyleSheet()
    el.append(Paragraph(f"FOLHA DE PONTO - {obra}", sty['Title']))
    el.append(Paragraph(f"Período: {periodo} | Chefe: {chefe}", sty['Normal']))
    el.append(Spacer(1, 1*cm))
    # Tabela simplificada para o Core
    data = [["Data", "Técnico", "Horas", "Frente"]]
    for _, r in regs.iterrows():
        data.append([r['Data'].strftime('%d/%m/%Y'), r['Técnico'], str(r['Horas_Total']), r['Frente']])
    t = Table(data)
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    el.append(t)
    doc.build(el)
    return buf.getvalue()

# Constantes HSE e Obras
TIPOS_FRENTE = ["Trabalho em obra", "Deslocação", "Formação", "Preparação", "Segurança", "Outro"]
CARGOS = ["Técnico", "Instrumentista", "Mecânico", "Eletricista", "Chefe de Equipa", "Admin"]
CATEGORIAS_SAFETY_WALK = ["EPI", "Trabalho em Altura", "Ordem e Limpeza", "Ferramentas", "Outro"]
REGRAS_OURO = [
    ("🦺", "EPI Obrigatório", "Uso obrigatório de proteção individual."),
    ("💊", "Álcool e Drogas", "Proibido trabalhar sob o efeito de substâncias."),
    ("🪜", "Trabalho em Altura", "Uso de arnês obrigatório acima de 2m."),
    ("🔒", "Bloqueios", "Bloqueio de energias obrigatório."),
    ("🚗", "Condução", "Condução apenas autorizada."),
    ("⚠️", "Espaços Confinados", "Acesso apenas com permissão."),
    ("🚬", "Fumar", "Apenas em locais autorizados."),
    ("📋", "Análise Risco", "Avaliação prévia obrigatória."),
    ("👕", "Vestuário", "Roupa justa e sem adornos."),
    ("📱", "Telemóvel", "Uso proibido em áreas operacionais.")
]

"""
GESTNOW v3 — core.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FONTE ÚNICA DE VERDADE.

Todos os módulos fazem: from core import *
Nenhum módulo importa de outro módulo.

Quando precisares de partilhar algo novo entre módulos → adicionar aqui.
Quando quiseres alterar um módulo → edita só esse ficheiro.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import streamlit as st
import pandas as pd
import os, re, secrets, shutil, io
from datetime import datetime, timedelta, date
import bcrypt
from google.cloud import storage as gcs

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
        st.warning(f"⚠️ Erro ao ler {fn} do Storage: {e}")
    return None

def _gcs_write(fn, content_bytes):
    try:
        bucket = _gcs_client().bucket(GCS_BUCKET)
        # backup antes de escrever
        blob = bucket.blob(f"data/{fn}")
        if blob.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            bucket.copy_blob(blob, bucket, f"backups/{fn.replace('.csv','')}_{ts}.csv")
        blob.upload_from_string(content_bytes, content_type="text/csv")
        return True
    except Exception as e:
        st.error(f"⚠️ Erro ao guardar {fn} no Storage: {e}")
        return False
import plotly.express as px
from streamlit_folium import folium_static
import folium
from geopy.distance import distance as geo_distance
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

# ============================================================
# 1. CONFIG
# ============================================================
st.set_page_config(page_title="GESTNOW", page_icon="🏗️", layout="wide", initial_sidebar_state="collapsed")

# ============================================================
# 2. ESTILOS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,.stApp{background:#F4F7FB;font-family:'Inter',sans-serif;}
.app-header{text-align:center;padding:3rem 0 2rem;}
.app-header h1{font-size:3rem;font-weight:800;background:linear-gradient(135deg,#0A2463,#3E92CC);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.app-header p{color:#7A8BA6;font-size:.9rem;letter-spacing:2px;text-transform:uppercase;}
.login-box{max-width:400px;margin:0 auto;background:white;padding:2.5rem;border-radius:24px;box-shadow:0 20px 60px rgba(10,36,99,.12);border:1px solid #E5EDFF;}
.stButton>button{border-radius:12px!important;font-weight:600!important;background:linear-gradient(135deg,#0A2463,#3E92CC)!important;color:white!important;border:none!important;box-shadow:0 4px 12px rgba(10,36,99,.25)!important;transition:all .2s!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 20px rgba(10,36,99,.35)!important;}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:white;padding:6px;border-radius:16px;border:1px solid #E5EDFF;box-shadow:0 2px 8px rgba(10,36,99,.06);flex-wrap:nowrap!important;overflow-x:auto!important;overflow-y:hidden!important;-webkit-overflow-scrolling:touch;scrollbar-width:none;}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar{display:none;}
.stTabs [data-baseweb="tab"]{border-radius:10px;padding:8px 14px;font-weight:500;font-size:.8rem;color:#5A6B85;white-space:nowrap!important;flex-shrink:0!important;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#0A2463,#3E92CC)!important;color:white!important;font-weight:600!important;}
.turno-card{background:white;padding:1.25rem 1.5rem;border-radius:16px;margin-bottom:.75rem;border:1px solid #E5EDFF;box-shadow:0 2px 10px rgba(10,36,99,.05);transition:box-shadow .2s;}
.turno-card:hover{box-shadow:0 6px 20px rgba(10,36,99,.1);}
.turno-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;font-weight:600;color:#0A2463;}
.turno-status{padding:4px 14px;border-radius:20px;font-size:.75rem;font-weight:700;text-transform:uppercase;}
.status-pendente{background:#FFF3CD;color:#8A6200;}
.status-aprovado{background:#D1FAE5;color:#065F46;}
.status-fechado{background:#E5E7EB;color:#374151;}
.status-vencida{background:#FEE2E2;color:#991B1B;}
.metric-card{background:white;padding:1.5rem;border-radius:16px;text-align:center;box-shadow:0 2px 10px rgba(10,36,99,.06);border:1px solid #E5EDFF;transition:transform .2s;}
.metric-card:hover{transform:translateY(-2px);}
.metric-icon{font-size:1.8rem;margin-bottom:.5rem;}
.metric-value{font-size:2.2rem;font-weight:800;color:#0A2463;line-height:1;}
.metric-label{color:#7A8BA6;font-size:.8rem;margin-top:4px;font-weight:500;text-transform:uppercase;letter-spacing:.5px;}
.metric-card-red{background:linear-gradient(135deg,#C0392B,#E74C3C);padding:1.4rem;border-radius:16px;text-align:left;box-shadow:0 4px 15px rgba(192,57,43,.3);}
.metric-card-red .mic-icon{font-size:1.3rem;margin-bottom:.3rem;color:rgba(255,255,255,.8);}
.metric-card-red .mic-value{font-size:2rem;font-weight:800;color:white;line-height:1;}
.metric-card-red .mic-label{color:rgba(255,255,255,.8);font-size:.8rem;margin-top:4px;}
.topbar{display:flex;justify-content:space-between;align-items:center;background:white;padding:1rem 1.5rem;border-radius:16px;margin-bottom:1.5rem;box-shadow:0 2px 10px rgba(10,36,99,.07);border:1px solid #E5EDFF;}
.topbar-logo{font-size:1.4rem;font-weight:800;background:linear-gradient(135deg,#0A2463,#3E92CC);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.topbar-user{display:flex;align-items:center;gap:12px;color:#374151;font-weight:500;font-size:.9rem;}
.badge-tipo{background:#EEF2FF;color:#4F46E5;padding:4px 12px;border-radius:20px;font-size:.75rem;font-weight:700;}
.badge-hora{background:#F0FDF4;color:#15803D;padding:4px 12px;border-radius:20px;font-size:.75rem;font-weight:600;}
.obra-codigo{font-family:monospace;font-size:.8rem;color:#3E92CC;background:#EEF6FF;padding:2px 8px;border-radius:6px;font-weight:600;}
.section-title{font-size:1.3rem;font-weight:700;color:#0A2463;margin-bottom:1.2rem;padding-bottom:.5rem;border-bottom:2px solid #E5EDFF;}
.perfil-campo{background:white;border-radius:12px;padding:1rem 1.25rem;margin-bottom:.5rem;border:1px solid #E5EDFF;}
.perfil-label{font-size:.75rem;color:#7A8BA6;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px;}
.perfil-valor{font-size:1rem;color:#1F2A44;font-weight:500;}
.seg-card{display:flex;align-items:center;gap:1rem;background:white;border-radius:14px;padding:1rem 1.25rem;margin-bottom:.6rem;border:1px solid #E5EDFF;box-shadow:0 2px 8px rgba(10,36,99,.04);transition:all .2s;}
.seg-card:hover{box-shadow:0 6px 16px rgba(10,36,99,.1);transform:translateX(4px);}
.seg-icon{font-size:1.5rem;width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.seg-title{font-weight:600;color:#1F2A44;font-size:.95rem;}
.seg-sub{font-size:.78rem;color:#7A8BA6;}
.security-badge{display:inline-flex;align-items:center;gap:6px;background:#ECFDF5;color:#065F46;font-size:.75rem;font-weight:600;padding:4px 10px;border-radius:8px;margin-top:1rem;}
.stAlert{border-radius:12px!important;}

/* ══════════════════════════════════════════════════════
   DARK MODE — Dark Slate Naval (inspirado no design industrial)
   Fundo: #0D1B2A | Surface: #1A2535 | Accent: #3E92CC
   ══════════════════════════════════════════════════════ */
@media (prefers-color-scheme: dark) {
  html, body, .stApp {
    background: #0D1B2A !important;
  }
  /* Inputs, selects, textareas */
  .stTextInput input, .stTextArea textarea, .stSelectbox select,
  .stNumberInput input, .stDateInput input,
  [data-baseweb="input"] input,
  [data-baseweb="textarea"] textarea,
  [data-baseweb="select"] div {
    background: #0F2236 !important;
    color: #C8D8E8 !important;
    border-color: rgba(62,146,204,0.25) !important;
  }
  /* Contentor geral dos inputs */
  [data-baseweb="base-input"],
  [data-baseweb="input"],
  [data-baseweb="textarea"] {
    background: #0F2236 !important;
    border-color: rgba(62,146,204,0.25) !important;
  }
  /* Form containers */
  [data-testid="stForm"] {
    background: #162033 !important;
    border: 1px solid rgba(62,146,204,0.18) !important;
    border-radius: 16px !important;
    padding: 1.25rem !important;
  }
  /* Cards */
  .turno-card, .metric-card, .seg-card, .perfil-campo,
  .week-bar, .rp-card, .pt-chip, .obra-card-sel {
    background: #162033 !important;
    border-color: rgba(62,146,204,0.2) !important;
    color: #C8D8E8 !important;
  }
  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    background: #162033 !important;
    border-color: rgba(62,146,204,0.2) !important;
  }
  .stTabs [data-baseweb="tab"] { color: #7A95B0 !important; }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg,#0A2463,#3E92CC) !important;
    color: white !important;
  }
  /* Texto geral */
  p, span, div, h1, h2, h3, label {
    color: #C8D8E8;
  }
  /* Section titles */
  .section-title { color: #7BBCDE !important; border-color: rgba(62,146,204,0.3) !important; }
  /* Topbar */
  .topbar { background: #162033 !important; border-color: rgba(62,146,204,0.2) !important; }
  /* Selectbox dropdown */
  [data-baseweb="popover"] [role="listbox"] {
    background: #1A2A3E !important;
    border: 1px solid rgba(62,146,204,0.3) !important;
  }
  [data-baseweb="popover"] [role="option"]:hover {
    background: rgba(62,146,204,0.15) !important;
  }
  /* Alertas */
  .stAlert { background: #162033 !important; border-color: rgba(62,146,204,0.3) !important; }
  /* Botões secundários */
  .stButton > button[kind="secondary"] {
    background: #1A2A3E !important;
    color: #7BBCDE !important;
    border-color: rgba(62,146,204,0.3) !important;
  }
  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #0D1B2A; }
  ::-webkit-scrollbar-thumb { background: rgba(62,146,204,0.4); border-radius: 3px; }
  /* Profile card mantém o gradiente mas mais rico */
  .tec-profile-card {
    background: linear-gradient(135deg, #0D1B2A 0%, #1A2A4A 50%, #1A3A5C 100%) !important;
    border: 1px solid rgba(62,146,204,0.3) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(62,146,204,0.2) !important;
  }
  /* Status badges */
  .status-pendente { background: rgba(234,179,8,0.15) !important; color: #FCD34D !important; }
  .status-aprovado { background: rgba(16,185,129,0.15) !important; color: #6EE7B7 !important; }
  .status-fechado  { background: rgba(99,102,241,0.15) !important; color: #A5B4FC !important; }
  .status-vencida  { background: rgba(239,68,68,0.15) !important; color: #FCA5A5 !important; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 3. CONSTANTES
# ============================================================
TAXA_HORA_POR_CARGO = {"Técnico":15.0,"Chefe de Equipa":22.5,"Admin":0.0}
SESSION_TIMEOUT = 60
MAX_LOGIN_ATTEMPTS = 5
DIAS_PT = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
MESES_PT = ["","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

TIPOS_FRENTE = [
    "Trabalho em obra","Deslocação","Formação","Reunião com cliente",
    "Preparação / Orçamento","Compras / Aprovisionamento","Administrativo / Documentação",
    "Qualidade / Inspeção","Segurança (SST)","Trabalho Noturno",
    "Trabalho ao Fim de Semana","Standby","Outro",
]

CARGOS = ["Técnico","Eletricista","Serralheiro","Mecânico","Instrumentista",
          "Chefe de Equipa","Encarregado","Admin","Outro"]

REGRAS_OURO = [
    ("🦺","EPI Obrigatório",
     "É obrigatório o uso de Equipamento de Proteção Individual (EPI) de acordo com a tarefa a ser executada."),
    ("💊","Álcool e Drogas",
     "É proibido dirigir-se para o trabalho ou desempenhar atividades ao serviço da empresa sob o efeito de álcool ou drogas."),
    ("🪜","Trabalho em Altura",
     "Não é permitido realizar tarefas a mais de 2 metros de altura sem o uso de arnês de segurança preso a um produto de ancoragem seguro."),
    ("🔒","Bloqueios e Isolamentos",
     "É obrigatório realizar os bloqueios necessários antes das intervenções humanas em máquinas, equipamentos ou tubagens."),
    ("🚗","Condução de Veículos",
     "É proibido operar ou conduzir veículos ou equipamentos automotores sem capacidade, formação e autorização."),
    ("⚠️","Espaços Confinados",
     "Os trabalhos em espaço confinado estão restritos a profissionais treinados, com conhecimento dos procedimentos cujo cumprimento é obrigatório."),
    ("🚬","Proibição de Fumar",
     "Não é permitido fumar durante a execução de tarefas manuais. Apenas é permitido fumar em locais identificados para o efeito."),
    ("📋","Análise de Risco",
     "Não é permitido executar nenhuma atividade sem previamente ser efetuada uma análise preliminar de risco."),
    ("👕","Roupa e Acessórios",
     "Não é permitido expor nenhuma parte do corpo na linha da frente de uma máquina em funcionamento. Não é permitido o uso de roupa larga, pulseiras, anéis ou outro tipo de acessórios que possam ser engatados."),
    ("📱","Uso de Telemóvel",
     "Não é aconselhável o uso de telemóveis durante o trabalho. Em atmosferas ATEX é proibido o seu uso. Evite caminhar e utilizar o telemóvel."),
]

# Categorias de Safety Walks
CATEGORIAS_SAFETY_WALK = [
    "EPI / Equipamentos de Proteção","Trabalho em Altura","Espaços Confinados",
    "Ferramentas e Equipamentos","Ordem e Limpeza","Sinalização e Delimitação",
    "Risco Elétrico","Produtos Químicos","Ergonomia","Comportamento","Outro",
]

# Tipos de Equipamentos/Meios
TIPOS_EQUIPAMENTO = [
    "Veículo Ligeiro","Veículo Pesado","Máquina Elevadora","Andaime","Escada",
    "Gerador","Compressor","Ferramenta Elétrica","Ferramenta Manual",
    "EPI Individual","Kit de Primeiros Socorros","Extintor","Outro",
]

# ============================================================
# 4. SEGURANÇA
# ============================================================
def init_session():
    for k,v in {'user':None,'tipo':None,'cargo':None,'data_consulta':datetime.now().date(),
                'login_attempts':0,'last_activity':datetime.now(),'session_token':None}.items():
        if k not in st.session_state: st.session_state[k]=v

def check_timeout():
    if st.session_state.get('user') and st.session_state.get('last_activity'):
        if (datetime.now()-st.session_state['last_activity']).seconds/60 > SESSION_TIMEOUT:
            st.session_state.clear(); st.warning("⏱️ Sessão expirada."); st.rerun()
    st.session_state['last_activity']=datetime.now()

def hp(p): return bcrypt.hashpw(p.encode(),bcrypt.gensalt(rounds=12)).decode()
def cp(p,h):
    try: return bcrypt.checkpw(p.encode(),h.encode())
    except: return False

def val_pw(p):
    if len(p)<8: return False,"Mínimo 8 caracteres."
    if not re.search(r'[A-Z]',p): return False,"Precisa de uma maiúscula."
    if not re.search(r'[0-9]',p): return False,"Precisa de um número."
    return True,"OK"

# ============================================================
# 5. BASE DE DADOS
# ============================================================
def load_db(fn,cols):
    try:
        buf = _gcs_read(fn)
        if buf:
            df=pd.read_csv(buf,dtype=str,on_bad_lines='skip')
            df.columns=df.columns.str.strip()
            for c in df.columns: df[c]=df[c].astype(str).str.strip().replace('nan','')
            for c in cols:
                if c not in df.columns: df[c]=""
            return df[cols]
    except Exception as e: st.error(f"⚠️ Erro ao carregar {fn}: {e}")
    return pd.DataFrame(columns=cols)

def save_db(df,fn):
    try:
        buf = io.StringIO()
        df.to_csv(buf,index=False,encoding='utf-8-sig')
        return _gcs_write(fn, buf.getvalue().encode('utf-8-sig'))
    except Exception as e: st.error(f"⚠️ Erro ao guardar {fn}: {e}"); return False

@st.cache_data(ttl=30)
def load_all():
    users  =load_db("usuarios.csv",["Nome","Password","Tipo","Email","Telefone","Cargo","NIF","NISS","CC","DataNasc","Nacionalidade","Morada","Foto"])
    obras  =load_db("obras_lista.csv",["Obra","Codigo","Cliente","Local","Ativa","Latitude","Longitude","Raio_Validacao","DataInicio","DataFim"])
    frentes=load_db("frentes_lista.csv",["Obra","Frente","Tipo","Responsavel"])
    regs   =load_db("registos.csv",["Data","Técnico","Obra","Frente","TipoFrente","Turnos","Relatorio","Status","Horas_Total","Localizacao_Checkin","Localizacao_Checkout"])
    fats   =load_db("faturas.csv",["Numero","Cliente","Data_Emissao","Data_Vencimento","Valor","Status","Periodo_Inicio","Periodo_Fim","Obra"])
    docs   =load_db("documentos.csv",["Utilizador","Tipo","Nome","Validade","Ficheiro"])
    incs   =load_db("incidentes.csv",["Data","Utilizador","Obra","Tipo","Descricao","Gravidade","Status"])
    sw     =load_db("safety_walks.csv",["Data","Utilizador","Obra","Categoria","Descricao","AcaoCorretiva","Status","Urgencia"])
    obs    =load_db("obs_seguranca.csv",["Data","Utilizador","Obra","Tipo","Descricao","Status"])
    equip  =load_db("equipamentos.csv",["Obra","Tipo","Descricao","NumSerie","Utilizador","DataAtrib","Validade","Estado"])
    diags  =load_db("dialogos.csv",["Titulo","Descricao","Tipo","DataCriacao","Atribuidos","Estado"])
    diags_u=load_db("dialogos_users.csv",["Dialogo","Utilizador","DataLeitura","Confirmado"])
    folhas =load_db("folhas_ponto.csv",["ID","Data","Obra","CodObra","ChefEquipa","Periodo","Tecnicos","TotalHoras","AssinadoCliente","AssinaturaChefe","AssinaturaCliente","NomeCliente","GPS_Chefe","DataCriacao","PDF_b64"])
    comuns =load_db("comunicados.csv",["ID","Titulo","Conteudo","Tipo","Destino","Obra","DataCriacao","Autor","Validade","Urgente"])
    comuns_u=load_db("comunicados_lidos.csv",["ComunicadoID","Utilizador","DataLeitura"])
    req_fer=load_db("req_ferramentas.csv",["ID","Data","Solicitante","Obra","Categoria","Descricao","Referencia","Quantidade","DataNecessaria","Status","NotaAdmin","DataResposta"])
    req_mat=load_db("req_materiais.csv",["ID","Data","Solicitante","Obra","Categoria","Descricao","Referencia","Quantidade","Unidade","DataNecessaria","Status","NotaAdmin","DataResposta"])
    req_epi=load_db("req_epis.csv",["ID","Data","Solicitante","Obra","TipoReq","Item","Tamanho","Quantidade","Motivo","Status","NotaAdmin","DataResposta"])
    avals  =load_db("avaliacoes.csv",["Utilizador","Data","PontuacaoManual","NotaAdmin","Avaliador"])
    # Campos novos nos users
    for col in ["PrecoHora","PrecoHoraStatus","PrecoHoraData","PIN","Foto"]:
        if col not in users.columns: users[col]=""
    # Campos novos nas obras
    for col in ["AssinaturaObrigatoria","Logo_b64"]:
        if col not in obras.columns: obras[col]=""
    if not regs.empty:
        regs['Data']=pd.to_datetime(regs['Data'],dayfirst=True,errors='coerce')
        regs['Horas_Total']=pd.to_numeric(regs['Horas_Total'],errors='coerce').fillna(0)
    if not fats.empty:
        for c in ['Data_Emissao','Data_Vencimento','Periodo_Inicio','Periodo_Fim']:
            fats[c]=pd.to_datetime(fats[c],dayfirst=True,errors='coerce')
        fats['Valor']=pd.to_numeric(fats['Valor'],errors='coerce').fillna(0)
    return users,obras,frentes,regs,fats,docs,incs,sw,obs,equip,diags,diags_u,folhas,comuns,comuns_u,req_fer,req_mat,req_epi,avals

def inv(): load_all.clear()

# ============================================================
# 6. UTILIDADES
# ====================

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
.stTabs [data-baseweb="tab-list"]{gap:4px;background:white;padding:6px;border-radius:16px;border:1px solid #E5EDFF;box-shadow:0 2px 8px rgba(10,36,99,.06);}
.stTabs [data-baseweb="tab"]{border-radius:10px;padding:8px 16px;font-weight:500;font-size:.85rem;color:#5A6B85;}
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
# ============================================================
def fh(h): h=float(h); return f"{int(h)}h{int((h-int(h))*60):02d}m"
def sl(s): return {"0":("Pendente","status-pendente"),"1":("Aprovado","status-aprovado"),"2":("Fechado","status-fechado")}.get(s,("—","status-fechado"))
def calc_val(rd,ud):
    t=0.0
    for _,r in rd.iterrows():
        u=ud[ud['Nome']==r['Técnico']]; cargo=u.iloc[0]['Cargo'] if not u.empty else 'Técnico'
        t+=float(r['Horas_Total'])*TAXA_HORA_POR_CARGO.get(cargo,15.0)
    return t

def gen_cod(obras_df):
    ano=datetime.now().year
    if obras_df.empty or 'Codigo' not in obras_df.columns: return f"GN.{ano}.OBR.0001"
    nums=[int(str(c).split('.')[-1]) for c in obras_df['Codigo'].dropna() if str(c).split('.')[-1].isdigit()]
    return f"GN.{ano}.OBR.{(max(nums)+1 if nums else 1):04d}"

def semana_de(d):
    dow=d.weekday(); inicio=d-timedelta(days=(dow+1)%7)
    return [inicio+timedelta(days=i) for i in range(7)]

# ============================================================
# 7. COMPONENTES
# ============================================================
def render_metric(icon,val,lbl):
    st.markdown(f"<div class='metric-card'><div class='metric-icon'>{icon}</div><div class='metric-value'>{val}</div><div class='metric-label'>{lbl}</div></div>",unsafe_allow_html=True)

def render_metric_red(icon,val,lbl):
    st.markdown(f"<div class='metric-card-red'><div class='mic-icon'>{icon}</div><div class='mic-value'>{val}</div><div class='mic-label'>{lbl}</div></div>",unsafe_allow_html=True)

def estado_bolinha(status):
    """Retorna emoji bolinha colorida conforme o estado do registo."""
    return {"0":"🟠","1":"🟢","2":"🔵"}.get(status,"⚪")

def render_card(obra,cod,st_txt,st_cls,turno,horas,frente="",rel=None,status="0"):
    cod_h=f"<span class='obra-codigo'>{cod}</span> " if cod else ""
    fr_h=f"<span style='color:#7A8BA6;font-size:.82rem;'> · {frente}</span>" if frente else ""
    rl_h=f"<div style='color:#6B7280;font-size:.8rem;margin-top:6px;'>📝 {rel}</div>" if rel else ""
    bolinha=estado_bolinha(status)
    st.markdown(f"<div class='turno-card'><div class='turno-header'><span>{bolinha} {cod_h}{obra}{fr_h}</span><span class='turno-status {st_cls}'>{st_txt}</span></div><div style='color:#374151;font-size:.9rem;'>⏱️ {turno} &nbsp;|&nbsp; <strong>{fh(horas)}</strong></div>{rl_h}</div>",unsafe_allow_html=True)

def cor_bolinha_dia(d, regs_user):
    """
    Determina a cor da bolinha para um dia do calendário.
    Regras (do estado mais avançado para o menor):
      🔵 Azul    = pelo menos um registo Faturado (Status "2") 
      🟢 Verde   = pelo menos um aprovado (Status "1"), nenhum faturado
      🟠 Laranja = apenas pendentes (Status "0")
      None       = sem registos ou dia há mais de 31 dias
    """
    hoje = datetime.now().date()
    # Apagar bolinhas com mais de 31 dias
    if (hoje - d).days > 31:
        return None
    if regs_user.empty:
        return None
    dia_regs = regs_user[regs_user['Data'].dt.date == d]
    if dia_regs.empty:
        return None
    statuses = set(dia_regs['Status'].tolist())
    if "2" in statuses:
        return "#3E92CC"   # Azul — Faturado
    elif "1" in statuses:
        return "#27AE60"   # Verde — Aprovado
    else:
        return "#E67E22"   # Laranja — Pendente

def render_cal(data_sel, regs_user):
    semana = semana_de(data_sel)
    hoje = datetime.now().date()
    mes = MESES_PT[data_sel.month]

    html = f"<div style='text-align:center;font-weight:700;color:#0A2463;margin-bottom:.5rem;font-size:1.1rem;'>📅 {mes} {data_sel.year}</div>"
    html += "<div style='display:flex;gap:6px;justify-content:center;background:white;padding:1rem;border-radius:16px;margin-bottom:.5rem;border:1px solid #E5EDFF;box-shadow:0 2px 10px rgba(10,36,99,.05);'>"

    for d in semana:
        is_sel = d == data_sel
        is_hoje = d == hoje
        cor = cor_bolinha_dia(d, regs_user)

        bg = "background:linear-gradient(135deg,#0A2463,#3E92CC);box-shadow:0 4px 12px rgba(10,36,99,.3);" if is_sel else "background:#F8FAFF;"
        txt_c = "color:white;" if is_sel else "color:#0A2463;"
        nome_c = "rgba(255,255,255,.8)" if is_sel else "#7A8BA6"
        nome = DIAS_PT[d.weekday()]

        # Bolinha colorida com cor do status
        if cor:
            dot_color = "rgba(255,255,255,.9)" if is_sel else cor
            dot = f"<div style='width:8px;height:8px;border-radius:50%;background:{dot_color};margin:3px auto 0;box-shadow:0 0 4px {dot_color};'></div>"
        else:
            dot = "<div style='width:8px;height:8px;margin:3px auto 0;'></div>"

        # Anel extra para "hoje"
        hoje_ring = "outline:2px solid #E74C3C;outline-offset:2px;" if is_hoje and not is_sel else ""

        html += f"<div style='display:flex;flex-direction:column;align-items:center;width:52px;padding:10px 6px;border-radius:12px;{bg}{hoje_ring}cursor:pointer;'>"
        html += f"<div style='font-size:.65rem;font-weight:700;color:{nome_c};text-transform:uppercase;margin-bottom:3px;letter-spacing:.5px;'>{nome}</div>"
        html += f"<div style='font-size:1.15rem;font-weight:700;{txt_c}'>{d.day}</div>"
        html += dot
        html += "</div>"

    html += "</div>"

    # Legenda das cores
    html += """<div style='display:flex;gap:1rem;justify-content:center;margin-bottom:.75rem;flex-wrap:wrap;'>
    <span style='font-size:.75rem;color:#7A8BA6;display:flex;align-items:center;gap:4px;'>
        <span style='width:8px;height:8px;border-radius:50%;background:#E67E22;display:inline-block;'></span>Pendente</span>
    <span style='font-size:.75rem;color:#7A8BA6;display:flex;align-items:center;gap:4px;'>
        <span style='width:8px;height:8px;border-radius:50%;background:#27AE60;display:inline-block;'></span>Aprovado</span>
    <span style='font-size:.75rem;color:#7A8BA6;display:flex;align-items:center;gap:4px;'>
        <span style='width:8px;height:8px;border-radius:50%;background:#3E92CC;display:inline-block;'></span>Faturado</span>
    </div>"""

    st.markdown(html, unsafe_allow_html=True)

    # Navegação semanal
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("◀ Semana", key="cal_p"):
            st.session_state.data_consulta -= timedelta(days=7); st.rerun()
    with c2:
        st.markdown(f"<p style='text-align:center;color:#7A8BA6;font-size:.85rem;margin:.3rem 0;'>"
                    f"{semana[0].strftime('%d/%m')} – {semana[-1].strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)
    with c3:
        if st.button("Semana ▶", key="cal_n"):
            if semana[-1] < hoje:
                st.session_state.data_consulta += timedelta(days=7); st.rerun()

    # Seletor de dia
    nomes = [f"{DIAS_PT[d.weekday()]} {d.day}" for d in semana]
    idx = semana.index(data_sel) if data_sel in semana else 0
    escolha = st.radio("", nomes, index=idx, horizontal=True, key="cal_r", label_visibility="collapsed")
    nd = semana[nomes.index(escolha)]
    if nd != data_sel:
        st.session_state.data_consulta = nd; st.rerun()

# ============================================================
# 8. PDF
# ============================================================
def gerar_pdf(dados,regs,users_df):
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,topMargin=2*cm,bottomMargin=2*cm)
    sty=getSampleStyleSheet(); el=[]
    ts=ParagraphStyle('T',parent=sty['Title'],fontSize=22,textColor=colors.HexColor('#0A2463'),spaceAfter=4)
    ss=ParagraphStyle('S',parent=sty['Normal'],fontSize=10,textColor=colors.HexColor('#7A8BA6'),spaceAfter=20)
    el.append(Paragraph(f"FATURA Nº {dados['Numero']}",ts))
    el.append(Paragraph("GESTNOW — Gestão de Obras e Equipas",ss))
    el.append(Spacer(1,.3*cm))
    def ds(v): return str(v)[:10] if v else "—"
    info=[["Cliente:",dados['Cliente']],["Obra:",dados.get('Obra','—')],["Emissão:",ds(dados.get('Data_Emissao'))],["Vencimento:",ds(dados.get('Data_Vencimento'))]]
    ti=Table(info,colWidths=[4*cm,12*cm])
    ti.setStyle(TableStyle([('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),10),('TEXTCOLOR',(0,0),(0,-1),colors.HexColor('#0A2463')),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    el.append(ti); el.append(Spacer(1,.5*cm))
    hdr=[['Data','Técnico','Cargo','Turno','Horas','€/h','Total']]; rows=[]
    for _,r in regs.iterrows():
        u=users_df[users_df['Nome']==r['Técnico']]; cargo=u.iloc[0]['Cargo'] if not u.empty else 'Técnico'
        taxa=TAXA_HORA_POR_CARGO.get(cargo,15.0)
        d_s=r['Data'].strftime('%d/%m/%Y') if hasattr(r['Data'],'strftime') else str(r['Data'])
        rows.append([d_s,r['Técnico'],cargo,r['Turnos'],f"{float(r['Horas_Total']):.1f}h",f"€{taxa:.2f}",f"€{float(r['Horas_Total'])*taxa:.2f}"])
    rows.append(['','','','','','TOTAL',f"€{dados['Valor']:,.2f}"])
    tab=Table(hdr+rows,colWidths=[2.5*cm,3.5*cm,2.5*cm,2.5*cm,1.5*cm,1.5*cm,2*cm])
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0A2463')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),('ALIGN',(0,0),(-1,-1),'CENTER'),('ROWBACKGROUNDS',(0,1),(-1,-2),[colors.white,colors.HexColor('#F4F7FB')]),('GRID',(0,0),(-1,-2),.5,colors.HexColor('#D1DAF5')),('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#0A2463')),('TEXTCOLOR',(0,-1),(-1,-1),colors.white),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    el.append(tab); el.append(Spacer(1,1*cm))
    el.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} • GESTNOW",ParagraphStyle('R',parent=sty['Normal'],fontSize=8,textColor=colors.HexColor('#9CA3AF'),alignment=1)))
    doc.build(el); buf.seek(0); return buf


# ============================================================
# 8b. FOLHA DE PONTO PDF
# ============================================================
def _qr_drawing(data_str, size_cm=2.8):
    """Gera QR code como Drawing do ReportLab (sem dependências externas)."""
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    qr_w = QrCodeWidget(data_str)
    b = qr_w.getBounds()
    w, h = b[2]-b[0], b[3]-b[1]
    sz = size_cm * cm
    d = Drawing(sz, sz, transform=[sz/w, 0, 0, sz/h, 0, 0])
    d.add(qr_w)
    return d

def gerar_folha_ponto_pdf(obra, cod_obra, chefe, periodo_label, regs_obra, users_df,
                           assin_chefe_b64="", assin_cliente_b64="", nome_cliente="",
                           gps_chefe="", logo_b64="", doc_id=None,
                           assin_cliente_obrigatoria=False):
    """
    Gera PDF da folha de ponto com:
    - Logo da empresa (se fornecido)
    - QR code de verificação
    - GPS do chefe de equipa
    - Tabela detalhada de presença (entrada/saída, cargo, frente)
    - Zona de assinaturas (chefe + cliente, obrigatoriedade configurável)
    - Rodapé legal com ID único
    """
    import base64, uuid as _uuid

    doc_id = doc_id or _uuid.uuid4().hex[:12].upper()
    buf = io.BytesIO()

    # Largura útil A4 com margens 1.8cm: 21cm - 3.6cm = 17.4cm
    PAGE_W = 17.4 * cm

    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=2.2*cm)
    el = []

    # ── Estilos ──────────────────────────────────────────────
    RED   = colors.HexColor('#C0392B')
    NAVY  = colors.HexColor('#0A2463')
    GREY  = colors.HexColor('#7A8BA6')
    LGREY = colors.HexColor('#F8FAFF')

    ts_title = ParagraphStyle('FT',  fontSize=14, fontName='Helvetica-Bold',
                               textColor=NAVY, spaceAfter=2, leading=16)
    ts_sub   = ParagraphStyle('FSub', fontSize=7, textColor=GREY, spaceAfter=6)
    ts_h2    = ParagraphStyle('FH2',  fontSize=9, fontName='Helvetica-Bold',
                               textColor=NAVY, spaceBefore=8, spaceAfter=4)
    ts_tiny  = ParagraphStyle('FTiny', fontSize=7, textColor=GREY, alignment=1)
    ts_label = ParagraphStyle('FLbl', fontSize=7, fontName='Helvetica-Bold',
                               textColor=GREY, spaceAfter=1)
    ts_val   = ParagraphStyle('FVal', fontSize=8, textColor=NAVY)

    # ── CABEÇALHO: Logo + Título + QR ────────────────────────
    if logo_b64 and len(logo_b64) > 20:
        try:
            logo_bytes = base64.b64decode(logo_b64)
            logo_buf   = io.BytesIO(logo_bytes)
            from reportlab.platypus import Image as RLImage
            logo_el = RLImage(logo_buf, width=3.5*cm, height=1.6*cm, kind='proportional')
        except:
            logo_el = Paragraph("<b>GESTNOW</b>", ParagraphStyle('LG',
                fontSize=14, fontName='Helvetica-Bold', textColor=RED))
    else:
        logo_el = Paragraph("<b>GESTNOW</b>", ParagraphStyle('LG',
            fontSize=14, fontName='Helvetica-Bold', textColor=NAVY))

    titulo_el = [
        Paragraph("FOLHA DE REGISTO DE PONTO", ts_title),
        Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  ID: {doc_id}", ts_sub),
    ]

    # QR code — com fallback robusto
    qr_el = Paragraph(f"<b>{doc_id}</b>", ParagraphStyle('QRF',
        fontSize=6, textColor=GREY, alignment=1))
    try:
        from reportlab.platypus import Image as _RLI
        from reportlab.graphics import renderPM as _rPM
        qr_data = f"GESTNOW|FP|{doc_id}|{obra}|{chefe}|{periodo_label}"
        qr_draw = _qr_drawing(qr_data, size_cm=2.4)
        qr_png  = io.BytesIO()
        _rPM.drawToFile(qr_draw, qr_png, fmt='PNG', dpi=144)
        qr_png.seek(0)
        qr_el = _RLI(qr_png, width=2.4*cm, height=2.4*cm)
    except Exception:
        pass

    # colWidths somam exactamente PAGE_W = 17.4cm
    hdr_table = Table(
        [[logo_el, titulo_el, qr_el]],
        colWidths=[4*cm, 10.6*cm, 2.8*cm]
    )
    hdr_table.setStyle(TableStyle([
        ('VALIGN',      (0,0),(-1,-1),'MIDDLE'),
        ('ALIGN',       (1,0),(1,0),  'LEFT'),
        ('ALIGN',       (2,0),(2,0),  'CENTER'),
        ('LINEBELOW',   (0,0),(-1,0), 1, colors.HexColor('#E5EDFF')),
        ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',  (0,0),(-1,-1),4),
    ]))
    el.append(hdr_table)
    el.append(Spacer(1, 0.25*cm))

    # ── DADOS DA OBRA ─────────────────────────────────────────
    gps_str = gps_chefe if gps_chefe else "Não disponível"
    info_rows = [
        [Paragraph("<b>Obra</b>", ts_label),    Paragraph(str(obra), ts_val),
         Paragraph("<b>Código</b>", ts_label),  Paragraph(str(cod_obra or "—"), ts_val)],
        [Paragraph("<b>Período</b>", ts_label),  Paragraph(str(periodo_label), ts_val),
         Paragraph("<b>Chefe de Equipa</b>", ts_label), Paragraph(str(chefe), ts_val)],
        [Paragraph("<b>Cliente</b>", ts_label),  Paragraph(str(nome_cliente or "—"), ts_val),
         Paragraph("<b>GPS (chefe)</b>", ts_label), Paragraph(str(gps_str), ts_val)],
    ]
    # colWidths somam 17.4cm
    ti = Table(info_rows, colWidths=[3*cm, 6.2*cm, 3.8*cm, 4.4*cm])
    ti.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), LGREY),
        ('GRID',          (0,0),(-1,-1), 0.3, colors.HexColor('#DDE6F5')),
        ('TOPPADDING',    (0,0),(-1,-1), 4),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('LEFTPADDING',   (0,0),(-1,-1), 5),
        ('RIGHTPADDING',  (0,0),(-1,-1), 4),
        ('FONTSIZE',      (0,0),(-1,-1), 8),
    ]))
    el.append(ti)
    el.append(Spacer(1, 0.35*cm))

    # ── TABELA DE PRESENÇA ────────────────────────────────────
    el.append(Paragraph("Registos de Presença", ts_h2))

    hdrs = [['Data', 'Técnico', 'Cargo', 'Frente / Trabalho', 'Turno', 'Horas', 'Estado']]
    rows = []
    total_h = 0.0
    tecnicos_presentes = {}

    for _, r in regs_obra.sort_values('Data').iterrows():
        u_row = users_df[users_df['Nome'] == r.get('Técnico', '')]
        cargo = u_row.iloc[0]['Cargo'] if not u_row.empty else '—'
        try:
            h = float(r.get('Horas_Total', 0))
        except (TypeError, ValueError):
            h = 0.0
        total_h += h
        tec_nome = str(r.get('Técnico', '—'))
        tecnicos_presentes[tec_nome] = tecnicos_presentes.get(tec_nome, 0) + h

        try:
            data_str = r['Data'].strftime('%d/%m/%Y') if pd.notnull(r.get('Data')) else '—'
        except Exception:
            data_str = '—'

        estado_map = {"0": "Pendente", "1": "Aprovado", "2": "Faturado"}
        turno_str  = str(r.get('Turnos', '—')) if pd.notnull(r.get('Turnos')) else '—'
        frente_str = str(r.get('TipoFrente', r.get('Frente', '—')))

        rows.append([
            data_str,
            tec_nome,
            str(cargo),
            frente_str,
            turno_str,
            f"{h:.1f}h",
            estado_map.get(str(r.get('Status', '0')), '—')
        ])

    rows.append(['', '', '', '', 'TOTAL', f"{total_h:.1f}h", f"{len(rows)} reg."])

    # colWidths somam 17.4cm
    tbl_regs = Table(hdrs + rows,
        colWidths=[2*cm, 3.6*cm, 2.8*cm, 4.2*cm, 2.8*cm, 1.5*cm, 2.5*cm],
        repeatRows=1)
    tbl_regs.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0),  NAVY),
        ('TEXTCOLOR',     (0,0),  (-1,0),  colors.white),
        ('FONTNAME',      (0,0),  (-1,0),  'Helvetica-Bold'),
        ('ALIGN',         (0,0),  (-1,0),  'CENTER'),
        ('FONTSIZE',      (0,0),  (-1,-1), 7),
        ('GRID',          (0,0),  (-1,-1), 0.3, colors.HexColor('#D1D9F0')),
        ('ROWBACKGROUNDS',(0,1),  (-1,-2), [colors.white, LGREY]),
        ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND',    (0,-1), (-1,-1), colors.HexColor('#EEF2FF')),
        ('LINEABOVE',     (0,-1), (-1,-1), 0.8, NAVY),
        ('ALIGN',         (5,0),  (6,-1),  'CENTER'),
        ('TOPPADDING',    (0,0),  (-1,-1), 3),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 3),
        ('LEFTPADDING',   (0,0),  (-1,-1), 4),
        ('RIGHTPADDING',  (0,0),  (-1,-1), 3),
        ('WORDWRAP',      (0,0),  (-1,-1), 1),
    ]))
    el.append(tbl_regs)

    # ── RESUMO POR TÉCNICO ────────────────────────────────────
    if len(tecnicos_presentes) > 1:
        el.append(Spacer(1, 0.25*cm))
        el.append(Paragraph("Resumo por Técnico", ts_h2))
        res_rows = [[
            Paragraph('<b>Técnico</b>', ts_label),
            Paragraph('<b>Total Horas</b>', ts_label),
            Paragraph('<b>Cargo</b>', ts_label)
        ]]
        for tec_n, tec_h in sorted(tecnicos_presentes.items()):
            u_r = users_df[users_df['Nome'] == tec_n]
            cg_ = u_r.iloc[0]['Cargo'] if not u_r.empty else '—'
            res_rows.append([str(tec_n), f"{tec_h:.1f}h", str(cg_)])
        # colWidths somam 17.4cm
        tbl_res = Table(res_rows, colWidths=[7*cm, 3.4*cm, 7*cm])
        tbl_res.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,0), colors.HexColor('#EEF2FF')),
            ('FONTSIZE',      (0,0),(-1,-1), 7),
            ('GRID',          (0,0),(-1,-1), 0.3, colors.HexColor('#D1D9F0')),
            ('TOPPADDING',    (0,0),(-1,-1), 3),
            ('BOTTOMPADDING', (0,0),(-1,-1), 3),
            ('LEFTPADDING',   (0,0),(-1,-1), 4),
        ]))
        el.append(tbl_res)

    el.append(Spacer(1, 0.4*cm))

    # ── ZONA DE ASSINATURAS ───────────────────────────────────
    # NOTA: NÃO usar KeepTogether aqui — causa "too large on page" quando
    # a tabela de registos já ocupou muito espaço. Cada célula é uma lista
    # simples de elementos; o ReportLab quebra a página naturalmente.
    el.append(Paragraph("Assinaturas", ts_h2))

    if assin_cliente_obrigatoria and not (assin_cliente_b64 and len(assin_cliente_b64) > 20):
        obrig_note = " (obrigatoria para validar)"
    else:
        obrig_note = ""

    def _sig_cell_elements(titulo, b64_img, nome="", obrig_txt=""):
        """Devolve lista de Flowables para uma célula de assinatura."""
        cell_els = []
        cell_els.append(Paragraph(f"<b>{titulo}</b>{obrig_txt}",
            ParagraphStyle('SH', fontSize=8, fontName='Helvetica-Bold',
                           textColor=GREY, spaceAfter=3)))
        if b64_img and len(b64_img) > 20:
            try:
                ib  = base64.b64decode(b64_img)
                ibf = io.BytesIO(ib)
                from reportlab.platypus import Image as _I
                cell_els.append(_I(ibf, width=6.5*cm, height=2*cm))
                cell_els.append(Paragraph("Assinatura digital capturada",
                    ParagraphStyle('SOK', fontSize=7,
                                   textColor=colors.HexColor('#059669'), spaceAfter=2)))
            except Exception:
                cell_els.append(Spacer(1, 2*cm))
                cell_els.append(Paragraph("_" * 38,
                    ParagraphStyle('SL', fontSize=8,
                                   textColor=colors.HexColor('#CBD5E1'), spaceAfter=2)))
        else:
            cell_els.append(Spacer(1, 2*cm))
            cell_els.append(Paragraph("_" * 38,
                ParagraphStyle('SL', fontSize=8,
                               textColor=colors.HexColor('#CBD5E1'), spaceAfter=2)))
        if nome:
            cell_els.append(Paragraph(str(nome),
                ParagraphStyle('SN', fontSize=8, textColor=NAVY, spaceBefore=2)))
        cell_els.append(Paragraph(datetime.now().strftime('%d/%m/%Y'),
            ParagraphStyle('SD', fontSize=7, textColor=GREY)))
        return cell_els

    sig_tbl = Table(
        [[_sig_cell_elements("Chefe de Equipa", assin_chefe_b64, chefe),
          _sig_cell_elements("Representante do Cliente", assin_cliente_b64,
                             nome_cliente, obrig_note)]],
        colWidths=[8.7*cm, 8.7*cm]   # 17.4cm total
    )
    sig_tbl.setStyle(TableStyle([
        ('VALIGN',       (0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',  (0,0),(-1,-1),8),
        ('RIGHTPADDING', (0,0),(-1,-1),8),
        ('TOPPADDING',   (0,0),(-1,-1),6),
        ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('BOX',          (0,0),(0,0), 0.5, colors.HexColor('#E5EDFF')),
        ('BOX',          (1,0),(1,0), 0.5, colors.HexColor('#E5EDFF')),
        ('BACKGROUND',   (0,0),(-1,-1), LGREY),
    ]))
    el.append(sig_tbl)
    el.append(Spacer(1, 0.35*cm))

    # ── RODAPÉ ────────────────────────────────────────────────
    footer_lines = [
        f"ID: {doc_id}  |  GESTNOW  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "Documento com validade legal quando assinado por ambas as partes.",
    ]
    if gps_chefe:
        footer_lines.append(f"GPS Chefe de Equipa: {gps_chefe}")
    for fl in footer_lines:
        el.append(Paragraph(fl, ts_tiny))

    doc.build(el)
    buf.seek(0)
    return buf.read(), total_h, doc_id

# ============================================================

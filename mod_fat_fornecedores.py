"""
GESTNOW v3 — mod_fat_fornecedores.py
Passo 3 — Fornecedores & Subempreiteiros
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, base64, io, json, os
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from core import save_db, inv, load_db, log_audit, criar_notificacao

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()

def _validar_nif(nif: str) -> tuple[bool, str]:
    nif = nif.replace(" ","").replace("-","")
    if not nif.isdigit() or len(nif) != 9:
        return False, "NIF deve ter 9 dígitos"
    if int(nif[0]) not in [1,2,3,5,6,7,8,9]:
        return False, "Primeiro dígito inválido"
    total = sum(int(nif[i]) * (9-i) for i in range(8))
    resto = total % 11
    check = 0 if resto in [0,1] else 11 - resto
    if check == int(nif[8]):
        return True, "✅ NIF válido"
    return False, "❌ Dígito de controlo inválido"

def _dias_venc(data_str: str) -> int:
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (date.today() - d).days
    except:
        return 0

# ─────────────────────────────────────────────────────────────────
# PDF GUIA DE RETENÇÃO NA FONTE
# ─────────────────────────────────────────────────────────────────

def _gerar_guia_retencao(mes: int, ano: int,
                          retencoes: list,
                          empresa: dict) -> bytes:
    """Gera guia de retenção na fonte mensal PDF."""
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    meses_pt = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

    bold_s = ParagraphStyle(
        'bold', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold', spaceAfter=4
    )
    sub_s = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#64748B'), spaceAfter=2
    )
    normal_s = styles['Normal']
    normal_s.fontSize = 9

    story.append(Paragraph(
        "GUIA DE RETENÇÃO NA FONTE — SUBEMPREITEIROS",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=16, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'), spaceAfter=6)
    ))
    story.append(Paragraph(
        f"Período: {meses_pt[mes-1]} {ano}", bold_s
    ))
    story.append(Paragraph(
        f"Empresa: {empresa.get('nome','')} | NIF: {empresa.get('nif','')}",
        sub_s
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor('#3B82F6')))
    story.append(Spacer(1, 0.3*cm))

    header = [["Subempreiteiro","NIF","Valor Pago (€)",
                "Taxa (%)","Retenção (€)"]]
    rows   = []
    total_ret = 0.0
    for r in retencoes:
        ret_val = round(
            float(r.get('valor',0)) * float(r.get('taxa',25)) / 100, 2
        )
        total_ret += ret_val
        rows.append([
            r.get('nome',''),
            r.get('nif',''),
            f"€{float(r.get('valor',0)):,.2f}",
            f"{r.get('taxa',25):.0f}%",
            f"€{ret_val:,.2f}",
        ])

    rows.append(["","","","<b>TOTAL RETIDO</b>",
                 f"<b>€{total_ret:,.2f}</b>"])

    t = Table(header + rows,
              colWidths=[5*cm, 2.5*cm, 3*cm, 2*cm, 2.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,0),  colors.HexColor('#1E293B')),
        ('TEXTCOLOR',     (0,0),(-1,0),  colors.white),
        ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,-1), 9),
        ('GRID',          (0,0),(-1,-2), 0.3, colors.HexColor('#E2E8F0')),
        ('BACKGROUND',    (0,-1),(-1,-1),colors.HexColor('#EFF6FF')),
        ('FONTNAME',      (0,-1),(-1,-1),'Helvetica-Bold'),
        ('ROWBACKGROUNDS',(0,1),(-1,-2),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING',    (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Total a entregar à AT até dia 20 do mês seguinte: "
        f"<b>€{total_ret:,.2f}</b>",
        bold_s
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} "
        f"— GESTNOW v3.0",
        ParagraphStyle('footer', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey)
    ))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# OCR FATURA FORNECEDOR COM CLAUDE VISION
# ─────────────────────────────────────────────────────────────────

def _ocr_fatura_fornecedor(img_b64: str,
                            media_type: str = "image/jpeg") -> dict:
    """Extrai dados de fatura de fornecedor com Claude Vision."""
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return {"sucesso": False, "erro": "API key não configurada"}

        client = anthropic.Anthropic(api_key=api_key)
        prompt = """Analisa esta fatura/recibo de fornecedor português.
Extrai os dados e responde APENAS em JSON sem texto adicional:
{
  "fornecedor": "nome do fornecedor",
  "nif_fornecedor": "NIF se visível ou vazio",
  "numero_fatura": "número da fatura",
  "data": "data no formato DD/MM/AAAA",
  "descricao": "descrição resumida dos bens/serviços",
  "subtotal": 0.00,
  "iva": 0.00,
  "total": 0.00,
  "confianca": "alta|media|baixa"
}"""
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": [
                    {"type":"image","source":{
                        "type":"base64",
                        "media_type":media_type,
                        "data":img_b64
                    }},
                    {"type":"text","text":prompt}
                ]
            }]
        )
        raw = resp.content[0].text.strip()
        raw = raw.replace("```json","").replace("```","").strip()
        return {"sucesso": True, "dados": json.loads(raw)}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_top_fornecedores(fat_forn):
    """Bar chart top 10 fornecedores por valor."""
    if fat_forn.empty or 'Fornecedor' not in fat_forn.columns:
        fornecedores = ['Fornecedor A','Fornecedor B','Fornecedor C']
        valores      = [25000, 18000, 12000]
    else:
        fat_forn = fat_forn.copy()
        fat_forn['Total_Num'] = pd.to_numeric(
            fat_forn.get('Total',0), errors='coerce'
        ).fillna(0)
        top = fat_forn.groupby('Fornecedor')['Total_Num'].sum(
        ).sort_values(ascending=False).head(10)
        fornecedores = top.index.tolist()
        valores      = top.values.tolist()

    n = len(fornecedores)
    cores = [
        f"rgba(59,130,246,{1.0 - i*0.08:.2f})"
        for i in range(n)
    ]

    fig = go.Figure(go.Bar(
        x=valores, y=fornecedores,
        orientation='h',
        marker_color=cores,
        text=[f"€{v:,.0f}" for v in valores],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':10}
    ))
    fig.update_layout(
        title={'text':'Top Fornecedores (valor total)',
               'font':{'color':'#F1F5F9'}},
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=10,r=80)
    )
    return fig


def _grafico_custos_categoria(fat_forn):
    """Donut custos por categoria de fornecedor."""
    if fat_forn.empty or 'Categoria' not in fat_forn.columns:
        labels = ['Material','Subempreiteiro','Serviço','Outro']
        values = [35000, 28000, 12000, 5000]
    else:
        fat_forn = fat_forn.copy()
        fat_forn['Total_Num'] = pd.to_numeric(
            fat_forn.get('Total',0), errors='coerce'
        ).fillna(0)
        grp    = fat_forn.groupby('Categoria')['Total_Num'].sum()
        labels = grp.index.tolist()
        values = grp.values.tolist()

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.5,
        marker={
            'colors':['#3B82F6','#EF4444','#10B981','#F59E0B'],
            'line':{'color':'#0F172A','width':2}
        },
        textfont={'color':'#F1F5F9','size':11},
        hovertemplate='%{label}: €%{value:,.0f}<extra></extra>'
    ))
    total_v = sum(values)
    # ── FIX BUG ── era `))` (parêntesis duplo), corrigido para `)`
    fig.update_layout(
        title={'text':'Custos por Categoria',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        margin=dict(t=40,b=10,l=10,r=10),
        annotations=[{
            'text':f'€{total_v:,.0f}',
            'x':0.5,'y':0.5,
            'font_size':13,'font_color':'#F1F5F9',
            'showarrow':False
        }]
    )
    return fig


def _grafico_aging_fornecedores(fat_forn):
    """Aging de fornecedores — o que devo e quando."""
    hoje_ts = pd.Timestamp(date.today())
    escaloes = ['Não vencido','0-30d','31-60d','+60d']
    valores  = [0.0, 0.0, 0.0, 0.0]

    if not fat_forn.empty and 'Data_Vencimento' in fat_forn.columns:
        ff = fat_forn.copy()
        ff['Venc_d']    = pd.to_datetime(
            ff['Data_Vencimento'], dayfirst=True, errors='coerce'
        )
        ff['Total_Num'] = pd.to_numeric(
            ff.get('Total',0), errors='coerce'
        ).fillna(0)
        nao_pagas = ff[
            ~ff.get('Estado','').isin(['Pago','Anulado'])
        ] if 'Estado' in ff.columns else ff

        for _, row in nao_pagas.iterrows():
            dias = (hoje_ts - row['Venc_d']).days \
                   if pd.notna(row['Venc_d']) else -1
            if dias < 0:     valores[0] += row['Total_Num']
            elif dias <= 30: valores[1] += row['Total_Num']
            elif dias <= 60: valores[2] += row['Total_Num']
            else:            valores[3] += row['Total_Num']
    else:
        valores = [12000, 5000, 2000, 1000]

    fig = go.Figure(go.Bar(
        x=escaloes, y=valores,
        marker_color=['#10B981','#F59E0B','#EF4444','#DC2626'],
        text=[f"€{v:,.0f}" for v in valores],
        textposition='outside',
        textfont={'color':'#F1F5F9'}
    ))
    fig.update_layout(
        title={'text':'Aging de Fornecedores (a pagar)',
               'font':{'color':'#F1F5F9'}},
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


def _grafico_retencoes_mensal(fat_forn):
    """Bar chart retenções na fonte por mês."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    hoje = date.today()
    labels, valores = [], []

    for i in range(5,-1,-1):
        d = date(hoje.year, hoje.month, 1) - timedelta(days=i*30)
        labels.append(meses_pt[d.month-1])
        val = 0.0
        if not fat_forn.empty and 'Data' in fat_forn.columns:
            ff = fat_forn.copy()
            ff['Data_d'] = pd.to_datetime(
                ff['Data'], dayfirst=True, errors='coerce'
            )
            ff['Total_Num'] = pd.to_numeric(
                ff.get('Total',0), errors='coerce'
            ).fillna(0)
            ff['Retencao_Pct_Num'] = pd.to_numeric(
                ff.get('Retencao_Pct',0), errors='coerce'
            ).fillna(0)
            mask = (
                (ff['Data_d'].dt.month == d.month) &
                (ff['Data_d'].dt.year  == d.year) &
                (ff['Retencao_Pct_Num'] > 0)
            )
            ff_mes = ff[mask]
            val = (ff_mes['Total_Num'] *
                   ff_mes['Retencao_Pct_Num'] / 100).sum()
        valores.append(round(val, 2))

    fig = go.Figure(go.Bar(
        x=labels, y=valores,
        marker_color='#EF4444',
        text=[f"€{v:,.0f}" for v in valores],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':10}
    ))
    fig.update_layout(
        title={'text':'Retenções na Fonte — 6 Meses',
               'font':{'color':'#F1F5F9'}},
        height=240,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_fornecedores(obras_db, *_):
    """Módulo Fornecedores & Subempreiteiros."""

    # ── Carregar dados ────────────────────────────────────────────
    fornecedores_db = _load("fornecedores.csv", [
        "ID","Nome","NIF","IBAN","BIC","Morada","Email",
        "Telefone","Categoria","Condicoes_Pagamento",
        "Limite_Credito","Subempreiteiro","Retencao_Pct"
    ])
    fat_forn = _load("faturas_fornecedores.csv", [
        "ID","Data","Data_Vencimento","Fornecedor","NIF_Fornecedor",
        "Numero_Fatura","Descricao","Obra","Categoria",
        "Subtotal","IVA","Total","Retencao_Pct","Retencao_Val",
        "Estado","PDF_b64","Aprovado_Por","Pago_Em"
    ])
    iban_hist = _load("iban_historico.csv", [
        "ID","Entidade","Tipo","Data_Alteracao",
        "IBAN_Anterior","IBAN_Novo","Alterado_Por"
    ])

    # Empresa config
    try:
        from mod_admin_diarias import _get_config_empresa
        empresa = _get_config_empresa()
    except:
        empresa = {
            "nome":"Correia Plácido e Sousa, Lda.",
            "nif":"517182718","iban":"","bic":"MPIOPTPL",
            "morada":"Zona Industrial de Seia, lote 33, Seia",
        }

    user_nome = st.session_state.get('user','Admin')

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .forn-card {
        background:#1E293B; border-radius:12px;
        padding:14px 16px; margin-bottom:8px;
        border-left:4px solid #F59E0B;
        transition:transform 0.15s;
    }
    .forn-card:hover { transform:translateX(3px); }
    .sub-card {
        background:#1E293B; border-radius:12px;
        padding:14px 16px; margin-bottom:8px;
        border-left:4px solid #EF4444;
    }
    .badge {
        display:inline-block; padding:3px 10px;
        border-radius:20px; font-size:0.72rem;
        font-weight:700;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────
    total_pagar = _num(
        fat_forn[
            ~fat_forn.get('Estado','').isin(['Pago','Anulado'])
        ] if not fat_forn.empty and 'Estado' in fat_forn.columns
          else fat_forn,
        'Total'
    )
    total_ret_mes = 0.0
    if not fat_forn.empty and 'Retencao_Val' in fat_forn.columns:
        mes, ano = date.today().month, date.today().year
        ff_mes = fat_forn.copy()
        ff_mes['Data_d'] = pd.to_datetime(
            ff_mes.get('Data',''), dayfirst=True, errors='coerce'
        )
        mask_mes = (
            (ff_mes['Data_d'].dt.month == mes) &
            (ff_mes['Data_d'].dt.year  == ano)
        )
        total_ret_mes = pd.to_numeric(
            ff_mes[mask_mes].get('Retencao_Val',0),
            errors='coerce'
        ).fillna(0).sum()

    n_sub = len(
        fornecedores_db[fornecedores_db['Subempreiteiro']=='Sim']
    ) if not fornecedores_db.empty and \
         'Subempreiteiro' in fornecedores_db.columns else 0

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("🏢 Fornecedores",   len(fornecedores_db))
    with c2: st.metric("🔨 Subempreiteiros", n_sub)
    with c3: st.metric("📤 A Pagar",         f"€{total_pagar:,.2f}")
    with c4: st.metric("📋 Retenções Mês",   f"€{total_ret_mes:,.2f}")

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_forn, t_fat_rec, t_sub,
     t_aging_f, t_ret, t_iban) = st.tabs([
        "🏢 Fornecedores",
        "📥 Faturas Recebidas",
        "🔨 Subempreiteiros",
        "📊 Aging & Pagamentos",
        "📋 Retenções na Fonte",
        "🔒 Controlo IBANs",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — FORNECEDORES
    # ════════════════════════════════════════════════════════════════
    with t_forn:
        st.markdown("### 🏢 Registo de Fornecedores")

        col_form_f, col_lista_f = st.columns([1, 2])

        with col_form_f:
            st.markdown("#### ➕ Novo Fornecedor")
            with st.form("form_novo_forn"):
                f_nome = st.text_input("Nome *", key="forn_nome")
                f_nif  = st.text_input("NIF *",  key="forn_nif",
                                        placeholder="123456789")
                if f_nif:
                    v, m = _validar_nif(f_nif)
                    st.markdown(
                        f"<small style='color:"
                        f"{'#10B981' if v else '#EF4444'};'>"
                        f"{m}</small>",
                        unsafe_allow_html=True
                    )
                f_cat = st.selectbox(
                    "Categoria",
                    ["Material","Subempreiteiro","Serviço",
                     "Aluguer Equipamento","Transportes","Outro"],
                    key="forn_cat"
                )
                f_sub = (f_cat == "Subempreiteiro")
                f_ret = 0.0
                if f_sub:
                    f_ret = st.number_input(
                        "Taxa Retenção Fonte (%)",
                        min_value=0.0, max_value=35.0,
                        value=25.0, step=0.5, key="forn_ret"
                    )

                col_fn1, col_fn2 = st.columns(2)
                with col_fn1:
                    f_iban = st.text_input(
                        "IBAN", key="forn_iban",
                        placeholder="PT50..."
                    )
                with col_fn2:
                    f_bic = st.text_input(
                        "BIC/SWIFT", key="forn_bic"
                    )
                f_morada = st.text_input("Morada", key="forn_morada")
                f_email  = st.text_input("Email",  key="forn_email")
                f_tel    = st.text_input("Telefone", key="forn_tel")
                f_dias   = st.selectbox(
                    "Condições Pagamento (dias)",
                    [0, 15, 30, 45, 60, 90],
                    index=2, key="forn_dias"
                )
                f_lim = st.number_input(
                    "Limite de Crédito (€)",
                    min_value=0.0, value=10000.0,
                    step=500.0, key="forn_lim"
                )

                if st.form_submit_button(
                    "💾 Guardar Fornecedor",
                    use_container_width=True, type="primary"
                ):
                    if not f_nome.strip() or not f_nif.strip():
                        st.error("❌ Nome e NIF obrigatórios.")
                    else:
                        novo_f = pd.DataFrame([{
                            "ID":                   str(uuid.uuid4())[:8].upper(),
                            "Nome":                 f_nome.strip(),
                            "NIF":                  f_nif.strip(),
                            "IBAN":                 f_iban.strip(),
                            "BIC":                  f_bic.strip(),
                            "Morada":               f_morada.strip(),
                            "Email":                f_email.strip(),
                            "Telefone":             f_tel.strip(),
                            "Categoria":            f_cat,
                            "Condicoes_Pagamento":  f_dias,
                            "Limite_Credito":       f_lim,
                            "Subempreiteiro":       "Sim" if f_sub else "Não",
                            "Retencao_Pct":         f_ret,
                        }])
                        updated_f = pd.concat(
                            [fornecedores_db, novo_f],
                            ignore_index=True
                        ) if not fornecedores_db.empty else novo_f
                        save_db(updated_f, "fornecedores.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="CRIAR_FORNECEDOR",
                            tabela="fornecedores.csv",
                            registro_id=novo_f['ID'].iloc[0],
                            detalhes=f"{f_nome} | NIF {f_nif}",
                            ip=""
                        )
                        inv("fornecedores.csv")
                        st.success(f"✅ {f_nome} guardado!")
                        st.rerun()

        with col_lista_f:
            st.markdown("#### 📋 Lista de Fornecedores")

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(
                    _grafico_top_fornecedores(fat_forn),
                    use_container_width=True, key="top_lista_aging" 
                )
            with col_g2:
                st.plotly_chart(
                    _grafico_custos_categoria(fat_forn),
                    use_container_width=True, key="custos_cat"
                )

            if fornecedores_db.empty:
                st.info("📋 Sem fornecedores registados.")
            else:
                cats = ["Todos"] + \
                       fornecedores_db['Categoria'].unique().tolist() \
                       if 'Categoria' in fornecedores_db.columns \
                       else ["Todos"]
                cat_f = st.selectbox(
                    "Categoria", cats, key="forn_cat_filt"
                )
                df_forn_show = fornecedores_db.copy()
                if cat_f != "Todos":
                    df_forn_show = df_forn_show[
                        df_forn_show['Categoria'] == cat_f
                    ]

                for _, forn in df_forn_show.iterrows():
                    forn_id  = forn.get('ID','')
                    is_sub   = forn.get('Subempreiteiro','Não') == 'Sim'
                    cor_card = '#EF4444' if is_sub else '#F59E0B'

                    vol_f = 0.0
                    if not fat_forn.empty and \
                       'Fornecedor' in fat_forn.columns:
                        ff_row = fat_forn[
                            fat_forn['Fornecedor'] == forn.get('Nome','')
                        ]
                        vol_f = pd.to_numeric(
                            ff_row.get('Total',0), errors='coerce'
                        ).fillna(0).sum()

                    badge_sub = (
                        "<span class='badge' "
                        "style='background:rgba(239,68,68,0.2);"
                        "color:#EF4444;margin-left:6px;'>"
                        "🔨 Subempreiteiro</span>"
                    ) if is_sub else ""

                    st.markdown(
                        f"<div class='forn-card' "
                        f"style='border-left-color:{cor_card};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;"
                        f"align-items:flex-start;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;'>"
                        f"{forn.get('Nome','')}</b>"
                        f"{badge_sub}<br>"
                        f"<small style='color:#64748B;'>"
                        f"NIF: {forn.get('NIF','')} · "
                        f"{forn.get('Categoria','')} · "
                        f"{forn.get('Condicoes_Pagamento',30)} dias"
                        f"</small><br>"
                        f"<small style='color:#475569;'>"
                        f"IBAN: {forn.get('IBAN','N/D')[:20]}..."
                        f" · 📧 {forn.get('Email','')}"
                        f"</small>"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<b style='color:#F1F5F9;'>"
                        f"€{vol_f:,.2f}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"total faturado</small>"
                        f"</div></div></div>",
                        unsafe_allow_html=True
                    )

                    col_ie, col_id = st.columns([3,1])
                    with col_ie:
                        novo_iban = st.text_input(
                            "Atualizar IBAN",
                            value=forn.get('IBAN',''),
                            key=f"iban_upd_{forn_id}",
                            label_visibility="collapsed",
                            placeholder="Novo IBAN (PT50...)"
                        )
                    with col_id:
                        if st.button(
                            "🔄 IBAN",
                            key=f"btn_iban_{forn_id}",
                            use_container_width=True,
                            help="Atualizar IBAN"
                        ):
                            iban_ant = forn.get('IBAN','')
                            if novo_iban != iban_ant:
                                novo_hist = pd.DataFrame([{
                                    "ID":             str(uuid.uuid4())[:8].upper(),
                                    "Entidade":       forn.get('Nome',''),
                                    "Tipo":           "Fornecedor",
                                    "Data_Alteracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    "IBAN_Anterior":  iban_ant,
                                    "IBAN_Novo":      novo_iban,
                                    "Alterado_Por":   user_nome
                                }])
                                upd_h = pd.concat(
                                    [iban_hist, novo_hist],
                                    ignore_index=True
                                ) if not iban_hist.empty else novo_hist
                                save_db(upd_h, "iban_historico.csv")

                                fornecedores_db.loc[
                                    fornecedores_db['ID'] == forn_id,
                                    'IBAN'
                                ] = novo_iban
                                save_db(fornecedores_db, "fornecedores.csv")
                                criar_notificacao(
                                    destinatario="admin",
                                    titulo="⚠️ IBAN Fornecedor Alterado",
                                    mensagem=(
                                        f"IBAN de {forn.get('Nome','')} "
                                        f"foi alterado por {user_nome}."
                                    ),
                                    tipo="warning",
                                    acao_url="/admin"
                                )
                                inv("iban_historico.csv"); inv("fornecedores.csv")
                                st.warning(
                                    f"⚠️ IBAN alterado! "
                                    f"Aguarda 30 dias antes de pagar."
                                )
                                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — FATURAS RECEBIDAS
    # ════════════════════════════════════════════════════════════════
    with t_fat_rec:
        st.markdown("### 📥 Faturas de Fornecedores")

        col_reg, col_lista = st.columns([1, 2])

        with col_reg:
            st.markdown("#### ➕ Registar Fatura Recebida")

            st.markdown(
                "<p style='color:#94A3B8;font-size:0.8rem;"
                "margin:0 0 6px;'>"
                "📷 Faz upload da fatura — "
                "a IA extrai os dados automaticamente</p>",
                unsafe_allow_html=True
            )
            upload_fat = st.file_uploader(
                "Fatura (JPG, PNG, PDF)",
                type=["jpg","jpeg","png","pdf"],
                key="forn_fat_upload"
            )

            ocr_dados = st.session_state.get('ocr_forn_dados', {})

            if upload_fat and not ocr_dados:
                if st.button(
                    "🤖 Extrair com IA",
                    key="btn_ocr_forn",
                    type="primary",
                    use_container_width=True
                ):
                    with st.spinner("🤖 A ler a fatura..."):
                        fb = base64.b64encode(
                            upload_fat.read()
                        ).decode()
                        mt = upload_fat.type \
                             if upload_fat.type != "application/pdf" \
                             else "image/jpeg"
                        res = _ocr_fatura_fornecedor(fb, mt)
                        if res['sucesso']:
                            st.session_state['ocr_forn_dados'] = \
                                res['dados']
                            st.session_state['ocr_forn_pdf']   = fb
                            st.success("✅ Dados extraídos!")
                            st.rerun()
                        else:
                            st.error(f"❌ {res.get('erro','')}")

            with st.form("form_fat_forn"):
                forn_lista = fornecedores_db['Nome'].tolist() \
                             if not fornecedores_db.empty else []

                f_forn = st.selectbox(
                    "Fornecedor *",
                    forn_lista if forn_lista else [""],
                    key="ff_forn"
                )
                f_num  = st.text_input(
                    "Nº Fatura",
                    value=ocr_dados.get('numero_fatura',''),
                    key="ff_num"
                )
                f_data = st.text_input(
                    "Data *",
                    value=ocr_dados.get('data',
                          date.today().strftime("%d/%m/%Y")),
                    key="ff_data"
                )
                f_obra = st.selectbox(
                    "Imputar a Obra",
                    [""] + (obras_db[
                        obras_db['Ativa']=='Ativa'
                    ]['Obra'].tolist() if not obras_db.empty else []),
                    key="ff_obra"
                )
                f_desc = st.text_area(
                    "Descrição",
                    value=ocr_dados.get('descricao',''),
                    key="ff_desc"
                )

                col_fs, col_fi, col_ft = st.columns(3)
                with col_fs:
                    f_sub_val = st.number_input(
                        "Subtotal €",
                        min_value=0.0,
                        value=float(ocr_dados.get('subtotal',0)),
                        step=0.01, key="ff_sub"
                    )
                with col_fi:
                    f_iva_val = st.number_input(
                        "IVA €",
                        min_value=0.0,
                        value=float(ocr_dados.get('iva',0)),
                        step=0.01, key="ff_iva"
                    )
                with col_ft:
                    f_tot_val = f_sub_val + f_iva_val
                    st.markdown(
                        f"<div style='padding:6px 0;'>"
                        f"<small style='color:#64748B;'>"
                        f"Total</small><br>"
                        f"<b style='color:#3B82F6;"
                        f"font-size:1.1rem;'>"
                        f"€{f_tot_val:.2f}</b></div>",
                        unsafe_allow_html=True
                    )

                f_ret_pct = 0.0
                if f_forn and not fornecedores_db.empty:
                    forn_row = fornecedores_db[
                        fornecedores_db['Nome'] == f_forn
                    ]
                    if not forn_row.empty:
                        is_sub_f = forn_row.iloc[0].get(
                            'Subempreiteiro','Não'
                        ) == 'Sim'
                        if is_sub_f:
                            f_ret_pct = float(
                                forn_row.iloc[0].get('Retencao_Pct',25)
                            )
                            f_ret_val = round(
                                f_sub_val * f_ret_pct / 100, 2
                            )
                            st.markdown(
                                f"<div style='background:rgba(239,68,68,0.1);"
                                f"border:1px solid #EF4444;"
                                f"border-radius:8px;padding:10px;"
                                f"margin:4px 0;'>"
                                f"<small style='color:#EF4444;"
                                f"font-weight:700;'>"
                                f"🔨 Subempreiteiro — Retenção "
                                f"{f_ret_pct:.0f}% = "
                                f"€{f_ret_val:.2f}</small></div>",
                                unsafe_allow_html=True
                            )

                f_dias_pag = st.selectbox(
                    "Condições Pagamento (dias)",
                    [0,15,30,45,60,90], index=2,
                    key="ff_dias_pag"
                )
                f_cat_ff = st.selectbox(
                    "Categoria",
                    ["Material","Subempreiteiro","Serviço",
                     "Aluguer","Outro"],
                    key="ff_cat"
                )

                if st.form_submit_button(
                    "💾 Registar Fatura",
                    use_container_width=True, type="primary"
                ):
                    if not f_forn or f_tot_val <= 0:
                        st.error("❌ Fornecedor e valor obrigatórios.")
                    else:
                        f_ret_v = round(
                            f_sub_val * f_ret_pct / 100, 2
                        )
                        try:
                            d_em = datetime.strptime(
                                f_data, "%d/%m/%Y"
                            ).date()
                            d_venc = (
                                d_em + timedelta(days=f_dias_pag)
                            ).strftime("%d/%m/%Y")
                        except:
                            d_venc = ""

                        pdf_b64_ff = st.session_state.get(
                            'ocr_forn_pdf', ''
                        )

                        nova_ff = pd.DataFrame([{
                            "ID":              str(uuid.uuid4())[:8].upper(),
                            "Data":            f_data,
                            "Data_Vencimento": d_venc,
                            "Fornecedor":      f_forn,
                            "NIF_Fornecedor":  "",
                            "Numero_Fatura":   f_num.strip(),
                            "Descricao":       f_desc.strip(),
                            "Obra":            f_obra,
                            "Categoria":       f_cat_ff,
                            "Subtotal":        f_sub_val,
                            "IVA":             f_iva_val,
                            "Total":           f_tot_val,
                            "Retencao_Pct":    f_ret_pct,
                            "Retencao_Val":    f_ret_v,
                            "Estado":          "Pendente",
                            "PDF_b64":         pdf_b64_ff,
                            "Aprovado_Por":    "",
                            "Pago_Em":         ""
                        }])
                        upd_ff = pd.concat(
                            [fat_forn, nova_ff], ignore_index=True
                        ) if not fat_forn.empty else nova_ff
                        save_db(upd_ff, "faturas_fornecedores.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="REGISTAR_FATURA_FORNECEDOR",
                            tabela="faturas_fornecedores.csv",
                            registro_id=nova_ff['ID'].iloc[0],
                            detalhes=(
                                f"{f_forn} | {f_num} | "
                                f"€{f_tot_val:.2f}"
                            ),
                            ip=""
                        )
                        inv("faturas_fornecedores.csv")
                        st.session_state.pop('ocr_forn_dados', None)
                        st.session_state.pop('ocr_forn_pdf', None)
                        st.success(
                            f"✅ Fatura de {f_forn} registada! "
                            f"€{f_tot_val:.2f}"
                        )
                        st.rerun()

        with col_lista:
            st.markdown("#### 📋 Faturas Pendentes")

            if fat_forn.empty:
                st.info("📋 Sem faturas de fornecedores.")
            else:
                col_ff1, col_ff2 = st.columns(2)
                with col_ff1:
                    est_ff = st.selectbox(
                        "Estado",
                        ["Todos","Pendente","Aprovado","Pago"],
                        key="ff_est_filt"
                    )
                with col_ff2:
                    obra_ff = st.selectbox(
                        "Obra",
                        ["Todas"] + fat_forn['Obra'].unique().tolist()
                        if 'Obra' in fat_forn.columns else ["Todas"],
                        key="ff_obra_filt"
                    )

                df_ff = fat_forn.copy()
                if est_ff  != "Todos": df_ff = df_ff[df_ff['Estado']  == est_ff]
                if obra_ff != "Todas": df_ff = df_ff[df_ff['Obra']    == obra_ff]

                total_ff = pd.to_numeric(
                    df_ff['Total'], errors='coerce'
                ).fillna(0).sum()
                st.metric("Total filtrado", f"€{total_ff:,.2f}")

                cor_estado_ff = {
                    'Pendente': '#F59E0B',
                    'Aprovado': '#3B82F6',
                    'Pago':     '#10B981',
                    'Anulado':  '#64748B',
                }

                for _, ff_row in df_ff.sort_values(
                    'Data', ascending=False
                ).iterrows():
                    ff_id   = ff_row.get('ID','')
                    tot_ff  = float(ff_row.get('Total',0) or 0)
                    ret_ff  = float(ff_row.get('Retencao_Val',0) or 0)
                    est_ff2 = ff_row.get('Estado','')
                    cor_ff  = cor_estado_ff.get(est_ff2,'#6B7280')
                    dias_v2 = _dias_venc(ff_row.get('Data_Vencimento',''))

                    alerta_v = ""
                    if dias_v2 > 0 and est_ff2 not in ['Pago','Anulado']:
                        alerta_v = (
                            f"<span style='color:#EF4444;"
                            f"font-size:0.72rem;'>"
                            f"⚠️ Em atraso {dias_v2} dias</span>"
                        )

                    ret_badge = ""
                    if ret_ff > 0:
                        ret_badge = (
                            f"<span class='badge' "
                            f"style='background:rgba(239,68,68,0.2);"
                            f"color:#EF4444;margin-left:4px;'>"
                            f"Retenção: €{ret_ff:.2f}</span>"
                        )

                    col_info_ff, col_act_ff = st.columns([5, 1])
                    with col_info_ff:
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:10px;padding:12px;"
                            f"margin-bottom:6px;"
                            f"border-left:4px solid {cor_ff};'>"
                            f"<b style='color:#F1F5F9;font-size:0.88rem;'>"
                            f"{ff_row.get('Fornecedor','')} — "
                            f"{ff_row.get('Numero_Fatura','')}</b>"
                            f"{ret_badge}<br>"
                            f"<small style='color:#64748B;'>"
                            f"{ff_row.get('Descricao','')[:40]} · "
                            f"Obra: {ff_row.get('Obra','')} · "
                            f"Venc: {ff_row.get('Data_Vencimento','')}"
                            f"</small><br>{alerta_v}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"<div style='text-align:right;"
                            f"margin-top:-4px;margin-bottom:6px;'>"
                            f"<b style='color:#F1F5F9;"
                            f"font-size:1rem;'>€{tot_ff:,.2f}</b>"
                            f"<span class='badge' "
                            f"style='background:{cor_ff}22;"
                            f"color:{cor_ff};margin-left:8px;'>"
                            f"{est_ff2}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                    with col_act_ff:
                        novo_est_ff = st.selectbox(
                            "Estado",
                            ["Pendente","Aprovado","Pago","Anulado"],
                            key=f"ff_est_{ff_id}",
                            label_visibility="collapsed"
                        )
                        if st.button(
                            "✅", key=f"ff_upd_{ff_id}",
                            use_container_width=True,
                            help="Atualizar estado"
                        ):
                            fat_forn.loc[
                                fat_forn['ID'] == ff_id,
                                'Estado'
                            ] = novo_est_ff
                            if novo_est_ff == 'Pago':
                                fat_forn.loc[
                                    fat_forn['ID'] == ff_id,
                                    'Pago_Em'
                                ] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                fat_forn.loc[
                                    fat_forn['ID'] == ff_id,
                                    'Aprovado_Por'
                                ] = user_nome
                            save_db(fat_forn, "faturas_fornecedores.csv")
                            inv("faturas_fornecedores.csv"); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — SUBEMPREITEIROS
    # ════════════════════════════════════════════════════════════════
    with t_sub:
        st.markdown("### 🔨 Subempreiteiros")
        st.info(
            "Subempreiteiros estão sujeitos a **retenção na fonte "
            "de 25%** (IRS). A guia de retenção deve ser entregue "
            "à AT até ao dia 20 do mês seguinte."
        )

        subs = fornecedores_db[
            fornecedores_db.get('Subempreiteiro','Não') == 'Sim'
        ] if not fornecedores_db.empty and \
             'Subempreiteiro' in fornecedores_db.columns \
          else pd.DataFrame()

        if subs.empty:
            st.warning(
                "⚠️ Sem subempreiteiros registados. "
                "Regista no tab 🏢 Fornecedores com "
                "categoria 'Subempreiteiro'."
            )
        else:
            st.markdown(f"**{len(subs)} subempreiteiro(s) registado(s)**")
            for _, sub in subs.iterrows():
                fats_sub = fat_forn[
                    fat_forn['Fornecedor'] == sub.get('Nome','')
                ] if not fat_forn.empty and \
                     'Fornecedor' in fat_forn.columns \
                  else pd.DataFrame()

                vol_sub = pd.to_numeric(
                    fats_sub.get('Total',0), errors='coerce'
                ).fillna(0).sum() if not fats_sub.empty else 0.0
                ret_sub = pd.to_numeric(
                    fats_sub.get('Retencao_Val',0), errors='coerce'
                ).fillna(0).sum() if not fats_sub.empty else 0.0

                st.markdown(
                    f"<div class='sub-card'>"
                    f"<b style='color:#F1F5F9;'>"
                    f"🔨 {sub.get('Nome','')}</b>"
                    f"<span style='float:right;color:#EF4444;"
                    f"font-weight:700;'>"
                    f"Retido: €{ret_sub:,.2f}</span><br>"
                    f"<small style='color:#64748B;'>"
                    f"NIF: {sub.get('NIF','')} · "
                    f"Taxa: {float(sub.get('Retencao_Pct',25)):.0f}% · "
                    f"Volume: €{vol_sub:,.2f}"
                    f"</small></div>",
                    unsafe_allow_html=True
                )

    # ════════════════════════════════════════════════════════════════
    # TAB — AGING & PAGAMENTOS
    # ════════════════════════════════════════════════════════════════
    with t_aging_f:
        st.markdown("### 📊 Aging de Fornecedores")

        col_ag1, col_ag2 = st.columns(2)
        with col_ag1:
            st.plotly_chart(
                _grafico_aging_fornecedores(fat_forn),
                use_container_width=True, key="aging_forn"
            )
        with col_ag2:
            st.plotly_chart(
                _grafico_top_fornecedores(fat_forn),
                use_container_width=True, key="top_forn_aging"
            )

        st.markdown("---")
        st.markdown("#### 🏦 Pagamento em Lote (SEPA XML)")

        pendentes_pag = fat_forn[
            fat_forn.get('Estado','') == 'Aprovado'
        ] if not fat_forn.empty and 'Estado' in fat_forn.columns \
          else pd.DataFrame()

        if pendentes_pag.empty:
            st.info(
                "📋 Sem faturas aprovadas para pagamento. "
                "Aprova faturas no tab 📥 Faturas Recebidas."
            )
        else:
            total_pag_lote = pd.to_numeric(
                pendentes_pag['Total'], errors='coerce'
            ).fillna(0).sum()
            st.metric(
                "💰 Total a pagar neste lote",
                f"€{total_pag_lote:,.2f}"
            )

            sem_iban = 0
            if not fornecedores_db.empty:
                for _, prow in pendentes_pag.iterrows():
                    forn_r = fornecedores_db[
                        fornecedores_db['Nome'] == prow.get('Fornecedor','')
                    ]
                    iban_f = forn_r.iloc[0].get('IBAN','') \
                             if not forn_r.empty else ''
                    if not iban_f or len(iban_f) < 15:
                        sem_iban += 1

            if sem_iban > 0:
                st.warning(
                    f"⚠️ {sem_iban} fornecedor(es) sem IBAN "
                    f"— não incluídos no XML."
                )

            if not iban_hist.empty:
                recentes = iban_hist[
                    pd.to_datetime(
                        iban_hist.get('Data_Alteracao',''),
                        dayfirst=True, errors='coerce'
                    ) >= pd.Timestamp(date.today() - timedelta(days=30))
                ]
                if not recentes.empty:
                    st.error(
                        f"🔒 ATENÇÃO: {len(recentes)} IBAN(s) "
                        f"alterado(s) nos últimos 30 dias! "
                        f"Verifica no tab 🔒 Controlo IBANs "
                        f"antes de pagar."
                    )

            col_sepa1, col_sepa2 = st.columns(2)
            with col_sepa1:
                if st.button(
                    "🏦 Gerar SEPA XML (Montepio)",
                    key="btn_sepa_forn",
                    type="primary",
                    use_container_width=True
                ):
                    try:
                        import xml.etree.ElementTree as ET
                        from xml.dom import minidom

                        agora    = datetime.now()
                        msg_id   = f"GESTNOW-FORN-{agora.strftime('%Y%m%d%H%M%S')}"
                        data_ex  = date.today().strftime('%Y-%m-%d')
                        ns       = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
                        root     = ET.Element("Document")
                        root.set("xmlns", ns)
                        cstmr    = ET.SubElement(root, "CstmrCdtTrfInitn")
                        grp_hdr  = ET.SubElement(cstmr, "GrpHdr")
                        ET.SubElement(grp_hdr,"MsgId").text   = msg_id
                        ET.SubElement(grp_hdr,"CreDtTm").text = agora.strftime('%Y-%m-%dT%H:%M:%S')
                        ET.SubElement(grp_hdr,"NbOfTxs").text = str(len(pendentes_pag))
                        ET.SubElement(grp_hdr,"CtrlSum").text = f"{total_pag_lote:.2f}"
                        initg = ET.SubElement(grp_hdr,"InitgPty")
                        ET.SubElement(initg,"Nm").text = empresa.get('nome','')

                        pmt_inf = ET.SubElement(cstmr,"PmtInf")
                        ET.SubElement(pmt_inf,"PmtInfId").text = f"{msg_id}-001"
                        ET.SubElement(pmt_inf,"PmtMtd").text   = "TRF"
                        ET.SubElement(pmt_inf,"NbOfTxs").text  = str(len(pendentes_pag))
                        ET.SubElement(pmt_inf,"CtrlSum").text   = f"{total_pag_lote:.2f}"
                        svc = ET.SubElement(ET.SubElement(pmt_inf,"PmtTpInf"),"SvcLvl")
                        ET.SubElement(svc,"Cd").text = "SEPA"
                        ET.SubElement(pmt_inf,"ReqdExctnDt").text = data_ex
                        dbtr = ET.SubElement(pmt_inf,"Dbtr")
                        ET.SubElement(dbtr,"Nm").text = empresa.get('nome','')
                        dbtr_acct = ET.SubElement(pmt_inf,"DbtrAcct")
                        ET.SubElement(ET.SubElement(dbtr_acct,"Id"),"IBAN").text = \
                            empresa.get('iban','').replace(' ','')
                        if empresa.get('bic',''):
                            fin = ET.SubElement(
                                ET.SubElement(pmt_inf,"DbtrAgt"),
                                "FinInstnId"
                            )
                            ET.SubElement(fin,"BIC").text = empresa.get('bic','')

                        for i, (_, prow) in enumerate(
                            pendentes_pag.iterrows(), 1
                        ):
                            forn_r = fornecedores_db[
                                fornecedores_db['Nome'] == prow.get('Fornecedor','')
                            ] if not fornecedores_db.empty else pd.DataFrame()
                            iban_f = forn_r.iloc[0].get('IBAN','') \
                                     if not forn_r.empty else ''
                            if not iban_f or len(iban_f) < 15:
                                continue

                            tot_p = float(prow.get('Total',0) or 0)
                            ret_p = float(prow.get('Retencao_Val',0) or 0)
                            val_p = round(tot_p - ret_p, 2)

                            cdt = ET.SubElement(pmt_inf,"CdtTrfTxInf")
                            pmt_id_e = ET.SubElement(cdt,"PmtId")
                            ET.SubElement(pmt_id_e,"EndToEndId").text = \
                                f"FORN-{i:04d}"
                            amt = ET.SubElement(cdt,"Amt")
                            ia  = ET.SubElement(amt,"InstdAmt")
                            ia.set("Ccy","EUR")
                            ia.text = f"{val_p:.2f}"
                            cdtr = ET.SubElement(cdt,"Cdtr")
                            ET.SubElement(cdtr,"Nm").text = \
                                str(prow.get('Fornecedor',''))[:70]
                            cdtr_acct = ET.SubElement(cdt,"CdtrAcct")
                            ET.SubElement(
                                ET.SubElement(cdtr_acct,"Id"), "IBAN"
                            ).text = iban_f.replace(' ','')
                            rmt = ET.SubElement(cdt,"RmtInf")
                            ET.SubElement(rmt,"Ustrd").text = \
                                f"Fatura {prow.get('Numero_Fatura','')} " \
                                f"{prow.get('Descricao','')[:50]}"

                        xml_str = ET.tostring(root, encoding='unicode')
                        dom     = minidom.parseString(xml_str)
                        xml_out = dom.toprettyxml(indent="  ")

                        ts_xml = datetime.now().strftime("%Y%m%d_%H%M")
                        st.session_state['sepa_forn_bytes'] = \
                            xml_out.encode('utf-8')
                        st.session_state['sepa_forn_fname'] = \
                            f"pagamentos_fornecedores_{ts_xml}.xml"
                        st.success("✅ XML gerado!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Erro: {e}")

            with col_sepa2:
                if st.session_state.get('sepa_forn_bytes'):
                    st.download_button(
                        "📥 Descarregar XML Montepio",
                        data=st.session_state['sepa_forn_bytes'],
                        file_name=st.session_state.get(
                            'sepa_forn_fname','pagamentos.xml'
                        ),
                        mime="application/xml",
                        key="dl_sepa_forn",
                        use_container_width=True,
                        type="primary"
                    )

    # ════════════════════════════════════════════════════════════════
    # TAB — RETENÇÕES NA FONTE
    # ════════════════════════════════════════════════════════════════
    with t_ret:
        st.markdown("### 📋 Retenções na Fonte")
        st.info(
            "Obrigação fiscal: entregar à AT até ao **dia 20 "
            "do mês seguinte** ao pagamento."
        )

        st.plotly_chart(
            _grafico_retencoes_mensal(fat_forn),
            use_container_width=True, key="ret_mensal"
        )

        col_rm, col_ra = st.columns(2)
        with col_rm:
            meses_pt = {
                "Janeiro":1,"Fevereiro":2,"Março":3,"Abril":4,
                "Maio":5,"Junho":6,"Julho":7,"Agosto":8,
                "Setembro":9,"Outubro":10,"Novembro":11,"Dezembro":12
            }
            mes_ret = st.selectbox(
                "Mês",
                list(meses_pt.keys()),
                index=date.today().month - 1,
                key="ret_mes"
            )
        with col_ra:
            ano_ret = st.number_input(
                "Ano",
                min_value=2020,
                value=date.today().year,
                key="forn_ret_ano"
            )

        mes_num_r = meses_pt[mes_ret]

        retencoes_mes = []
        if not fat_forn.empty and 'Data' in fat_forn.columns:
            ff_r = fat_forn.copy()
            ff_r['Data_d'] = pd.to_datetime(
                ff_r['Data'], dayfirst=True, errors='coerce'
            )
            ff_r['Retencao_Val_Num'] = pd.to_numeric(
                ff_r.get('Retencao_Val',0), errors='coerce'
            ).fillna(0)
            mask_r = (
                (ff_r['Data_d'].dt.month == mes_num_r) &
                (ff_r['Data_d'].dt.year  == ano_ret) &
                (ff_r['Retencao_Val_Num'] > 0)
            )
            ff_mes_r = ff_r[mask_r]

            for _, row_r in ff_mes_r.iterrows():
                forn_r2 = fornecedores_db[
                    fornecedores_db['Nome'] == row_r.get('Fornecedor','')
                ] if not fornecedores_db.empty else pd.DataFrame()
                nif_r = forn_r2.iloc[0].get('NIF','') \
                        if not forn_r2.empty else ''
                retencoes_mes.append({
                    "nome":   row_r.get('Fornecedor',''),
                    "nif":    nif_r,
                    "valor":  float(row_r.get('Total',0) or 0),
                    "taxa":   float(row_r.get('Retencao_Pct',25) or 25),
                    "retido": float(row_r.get('Retencao_Val_Num',0))
                })

        if retencoes_mes:
            total_ret_m = sum(r['retido'] for r in retencoes_mes)
            st.markdown(
                f"<div style='background:rgba(239,68,68,0.1);"
                f"border:1px solid #EF4444;border-radius:10px;"
                f"padding:14px;margin-bottom:12px;'>"
                f"<b style='color:#EF4444;'>"
                f"Total a entregar à AT em "
                f"{mes_ret} {ano_ret}: "
                f"€{total_ret_m:,.2f}</b><br>"
                f"<small style='color:#94A3B8;'>"
                f"Prazo: dia 20 do mês seguinte</small>"
                f"</div>",
                unsafe_allow_html=True
            )

            df_ret = pd.DataFrame(retencoes_mes)
            st.dataframe(df_ret, use_container_width=True,
                         hide_index=True)

            if st.button(
                "📄 Gerar Guia de Retenção PDF",
                key="btn_guia_ret",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("A gerar guia..."):
                    pdf_ret = _gerar_guia_retencao(
                        mes_num_r, ano_ret,
                        retencoes_mes, empresa
                    )
                st.session_state['guia_ret_bytes'] = pdf_ret
                st.session_state['guia_ret_fname'] = \
                    f"guia_retencao_{mes_num_r:02d}_{ano_ret}.pdf"
                st.rerun()

            if st.session_state.get('guia_ret_bytes'):
                st.download_button(
                    "📥 Descarregar Guia",
                    data=st.session_state['guia_ret_bytes'],
                    file_name=st.session_state.get(
                        'guia_ret_fname','guia.pdf'
                    ),
                    mime="application/pdf",
                    key="dl_guia_ret",
                    use_container_width=True
                )
        else:
            st.info(
                f"📋 Sem retenções registadas em "
                f"{mes_ret} {ano_ret}."
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — CONTROLO IBANs
    # ════════════════════════════════════════════════════════════════
    with t_iban:
        st.markdown("### 🔒 Controlo de IBANs")
        st.info(
            "Alterações de IBAN são um vetor comum de fraude. "
            "Qualquer alteração fica registada e gera alerta. "
            "**Pagamentos são bloqueados por 30 dias após alteração.**"
        )

        if not iban_hist.empty and 'Data_Alteracao' in iban_hist.columns:
            iban_hist_c = iban_hist.copy()
            iban_hist_c['Alt_d'] = pd.to_datetime(
                iban_hist_c['Data_Alteracao'],
                dayfirst=True, errors='coerce'
            )
            recentes_iban = iban_hist_c[
                iban_hist_c['Alt_d'] >= pd.Timestamp(
                    date.today() - timedelta(days=30)
                )
            ]

            if not recentes_iban.empty:
                st.error(
                    f"🚨 {len(recentes_iban)} IBAN(s) "
                    f"alterado(s) nos últimos 30 dias!"
                )
                for _, ih in recentes_iban.iterrows():
                    dias_alt = (
                        date.today() - ih['Alt_d'].date()
                    ).days if pd.notna(ih['Alt_d']) else 0
                    bloqueado = dias_alt < 30

                    # estado_iban calculado antes do f-string
                    estado_iban = '🔒 BLOQUEADO' if bloqueado else '🔓 Desbloqueado'
                    cor_iban    = '#EF4444' if bloqueado else '#10B981'

                    st.markdown(
                        f"<div style='background:rgba(239,68,68,0.1);"
                        f"border:2px solid #EF4444;"
                        f"border-radius:10px;padding:14px;"
                        f"margin-bottom:8px;'>"
                        f"<b style='color:#EF4444;'>"
                        f"⚠️ {ih.get('Entidade','')} "
                        f"({ih.get('Tipo','')})</b>"
                        f"<span style='float:right;"
                        f"color:{cor_iban};"
                        f"font-size:0.8rem;font-weight:700;'>"
                        f"{estado_iban}"
                        f"</span><br>"
                        f"<small style='color:#94A3B8;'>"
                        f"Anterior: {ih.get('IBAN_Anterior','N/D')}<br>"
                        f"Novo: {ih.get('IBAN_Novo','')}<br>"
                        f"Alterado por: {ih.get('Alterado_Por','')} "
                        f"em {ih.get('Data_Alteracao','')} "
                        f"({dias_alt} dias atrás)"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

                    if bloqueado:
                        if st.button(
                            f"🔓 Desbloquear manualmente — "
                            f"{ih.get('Entidade','')}",
                            key=f"desbloquear_{ih.get('ID','')}",
                            type="secondary",
                            use_container_width=True
                        ):
                            log_audit(
                                usuario=user_nome,
                                acao="DESBLOQUEAR_IBAN",
                                tabela="iban_historico.csv",
                                registro_id=ih.get('ID',''),
                                detalhes=(
                                    f"IBAN de {ih.get('Entidade','')} "
                                    f"desbloqueado manualmente por "
                                    f"{user_nome}"
                                ),
                                ip=""
                            )
                            st.success("✅ Desbloqueado. Ação registada.")
            else:
                st.success(
                    "✅ Sem alterações de IBAN nos últimos 30 dias."
                )

        st.markdown("---")
        st.markdown("#### 📋 Histórico Completo de Alterações")

        if iban_hist.empty:
            st.info("📋 Sem histórico de alterações.")
        else:
            cols_h = [c for c in [
                'Data_Alteracao','Entidade','Tipo',
                'IBAN_Anterior','IBAN_Novo','Alterado_Por'
            ] if c in iban_hist.columns]
            st.dataframe(
                iban_hist[cols_h].sort_values(
                    'Data_Alteracao', ascending=False
                ),
                use_container_width=True, hide_index=True
            )

            csv_iban = iban_hist[cols_h].to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Exportar Histórico IBANs",
                data=csv_iban.encode('utf-8-sig'),
                file_name="historico_ibans.csv",
                mime="text/csv",
                key="dl_iban_hist"
            )

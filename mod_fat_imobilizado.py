"""
GESTNOW v3 — mod_fat_imobilizado.py
Passo 10 — Imobilizado, Amortizações, Seguros, Cauções, Alvarás
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, io, os
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from core import save_db, inv, load_db, log_audit

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)

def _dias_para(data_str: str) -> int:
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return 999

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()


# ─────────────────────────────────────────────────────────────────
# TABELAS DE AMORTIZAÇÃO (PORTUGAL — Decreto Reg. 25/2009)
# ─────────────────────────────────────────────────────────────────

TAXAS_AMORTIZACAO = {
    "Edifícios Industriais":         {"taxa": 5.0,  "vida": 20},
    "Instalações e Adaptações":      {"taxa": 12.5, "vida": 8},
    "Equipamento Básico Industrial": {"taxa": 14.29,"vida": 7},
    "Equipamento Instrumentação":    {"taxa": 20.0, "vida": 5},
    "Equipamento Informático":       {"taxa": 33.33,"vida": 3},
    "Software":                      {"taxa": 33.33,"vida": 3},
    "Viaturas Ligeiras":             {"taxa": 25.0, "vida": 4},
    "Viaturas Pesadas":              {"taxa": 20.0, "vida": 5},
    "Ferramentas e Utensílios":      {"taxa": 25.0, "vida": 4},
    "Mobiliário e Equipamento":      {"taxa": 12.5, "vida": 8},
    "Outro":                         {"taxa": 10.0, "vida": 10},
}


def _calcular_amortizacao(valor_compra: float,
                           taxa_anual: float,
                           data_compra_str: str,
                           metodo: str = "linear") -> dict:
    """
    Calcula amortizações pelo método linear ou decrescente.
    Retorna valor contabilístico atual e mapa anual.
    """
    try:
        d_compra = datetime.strptime(
            data_compra_str, "%d/%m/%Y"
        ).date()
    except:
        d_compra = date.today()

    anos_decorr  = (date.today() - d_compra).days / 365.25
    vida_util    = round(100 / taxa_anual) if taxa_anual > 0 else 10
    amort_anual  = round(valor_compra * taxa_anual / 100, 2)

    if metodo == "linear":
        amort_acum   = round(
            min(amort_anual * anos_decorr, valor_compra), 2
        )
        val_contabil = round(
            max(0, valor_compra - amort_acum), 2
        )
    else:  # decrescente
        val_contabil = valor_compra
        for _ in range(int(anos_decorr)):
            val_contabil = round(
                val_contabil * (1 - taxa_anual / 100), 2
            )
        amort_acum = round(valor_compra - val_contabil, 2)

    # Mapa anual
    mapa = []
    val_res = valor_compra
    ano_ini = d_compra.year
    for i in range(vida_util + 1):
        ano = ano_ini + i
        if metodo == "linear":
            amort_a = min(amort_anual, val_res)
        else:
            amort_a = round(val_res * taxa_anual / 100, 2)
        val_res = round(max(0, val_res - amort_a), 2)
        mapa.append({
            "Ano":            ano,
            "Amortização":    amort_a,
            "Val.Contabilístico": val_res
        })
        if val_res <= 0:
            break

    return {
        "valor_compra":   valor_compra,
        "taxa_anual":     taxa_anual,
        "vida_util":      vida_util,
        "anos_decorr":    round(anos_decorr, 1),
        "amort_anual":    amort_anual,
        "amort_acum":     amort_acum,
        "val_contabil":   val_contabil,
        "pct_amortizado": round(amort_acum / valor_compra * 100, 1)
                          if valor_compra > 0 else 0,
        "mapa_anual":     mapa,
        "data_compra":    d_compra,
        "data_amort_total": date(
            d_compra.year + vida_util, d_compra.month, d_compra.day
        )
    }


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_amort_timeline(mapa_anual: list,
                             nome: str):
    """Area chart valor contabilístico ao longo do tempo."""
    anos  = [str(m['Ano'])            for m in mapa_anual]
    vals  = [m['Val.Contabilístico']  for m in mapa_anual]
    amort = [m['Amortização']         for m in mapa_anual]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Amortização Anual',
        x=anos, y=amort,
        marker_color='rgba(239,68,68,0.6)',
        hovertemplate='%{x}<br>Amort: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        name='Valor Contabilístico',
        x=anos, y=vals,
        mode='lines+markers',
        line={'color':'#3B82F6','width':3},
        marker={'size':6},
        fill='tozeroy',
        fillcolor='rgba(59,130,246,0.08)',
        hovertemplate='%{x}<br>Val: €%{y:,.2f}<extra></extra>',
        yaxis='y2'
    ))
    # Hoje
    hoje_ano = str(date.today().year)
    if hoje_ano in anos:
        fig.add_vline(
            x=hoje_ano,
            line_dash="dash",
            line_color="#F59E0B",
            line_width=2,
            annotation_text="Hoje",
            annotation_font_color="#F59E0B"
        )

    fig.update_layout(
        title={'text':f'Amortização — {nome[:30]}',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€',
               'title':{'text':'Amort. Anual',
                        'font':{'color':'#94A3B8'}}},
        yaxis2={'overlaying':'y','side':'right',
                'tickprefix':'€',
                'tickfont':{'color':'#3B82F6'},
                'showgrid':False,
                'title':{'text':'Val. Contabilístico',
                         'font':{'color':'#3B82F6'}}},
        margin=dict(t=40,b=20,l=60,r=60),
        hovermode='x unified'
    )
    return fig


def _grafico_imobilizado_donut(imob_db):
    """Donut composição do imobilizado por categoria."""
    if imob_db.empty:
        return None

    imob_db = imob_db.copy()
    imob_db['Val_Num'] = pd.to_numeric(
        imob_db.get('Valor_Compra',0), errors='coerce'
    ).fillna(0)

    grp = imob_db.groupby(
        'Categoria' if 'Categoria' in imob_db.columns else 'Descricao'
    )['Val_Num'].sum()

    if grp.empty:
        return None

    cores = ['#3B82F6','#10B981','#F59E0B','#EF4444',
             '#8B5CF6','#06B6D4','#F97316','#64748B']

    fig = go.Figure(go.Pie(
        labels=grp.index.tolist(),
        values=grp.values.tolist(),
        hole=0.5,
        marker={'colors':cores[:len(grp)],
                'line':{'color':'#0F172A','width':2}},
        textfont={'color':'#F1F5F9','size':10},
        hovertemplate='%{label}<br>€%{value:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Imobilizado por Categoria',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        margin=dict(t=40,b=10,l=10,r=10),
        annotations=[{
            'text':f"€{grp.sum():,.0f}",
            'x':0.5,'y':0.5,
            'font_size':13,'font_color':'#F1F5F9',
            'showarrow':False
        }]
    )
    return fig


def _grafico_amort_acumulada_total(imob_db):
    """Bar chart amortização acumulada vs valor bruto por ativo."""
    if imob_db.empty:
        return None

    nomes  = []
    brutos = []
    acums  = []
    conts  = []

    for _, row in imob_db.iterrows():
        vc  = float(row.get('Valor_Compra',0) or 0)
        vco = float(row.get('Val_Contabil',0) or 0)
        ac  = round(vc - vco, 2)
        nomes.append(str(row.get('Descricao',''))[:20])
        brutos.append(vc)
        acums.append(ac)
        conts.append(vco)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Valor Bruto',
        x=nomes, y=brutos,
        marker_color='rgba(100,116,139,0.4)',
        hovertemplate='%{x}<br>Bruto: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Amort. Acumulada',
        x=nomes, y=acums,
        marker_color='rgba(239,68,68,0.7)',
        hovertemplate='%{x}<br>Amort: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Val. Contabilístico',
        x=nomes, y=conts,
        marker_color='#3B82F6',
        hovertemplate='%{x}<br>Contab: €%{y:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Imobilizado — Valor Bruto vs Amortizado',
               'font':{'color':'#F1F5F9'}},
        barmode='overlay',
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10)
    )
    return fig


def _grafico_seguros_timeline(seguros_db):
    """Gantt de validade dos seguros."""
    if seguros_db.empty:
        return None

    fig = go.Figure()
    cores_seg = ['#3B82F6','#10B981','#F59E0B',
                 '#8B5CF6','#EF4444','#06B6D4']
    hoje_ts = datetime.now()

    for i, (_, row) in enumerate(seguros_db.iterrows()):
        try:
            ini = datetime.strptime(
                row.get('Data_Inicio','01/01/2024'),"%d/%m/%Y"
            )
            fim = datetime.strptime(
                row.get('Data_Fim','31/12/2025'),"%d/%m/%Y"
            )
        except:
            continue

        dias_r = (fim.date() - date.today()).days
        cor_s  = '#EF4444' if dias_r <= 30 \
                 else '#F59E0B' if dias_r <= 60 \
                 else cores_seg[i % len(cores_seg)]

        fig.add_trace(go.Scatter(
            x=[ini, fim],
            y=[row.get('Tipo','')[:30],
               row.get('Tipo','')[:30]],
            mode='lines',
            line={'color':cor_s,'width':18},
            name=row.get('Tipo',''),
            hovertemplate=(
                f"<b>{row.get('Tipo','')}</b><br>"
                f"Seguradora: {row.get('Entidade','')}<br>"
                f"Prémio: €{float(row.get('Valor_Anual',0) or 0):,.2f}/ano<br>"
                f"{ini.strftime('%d/%m/%Y')} → "
                f"{fim.strftime('%d/%m/%Y')}<br>"
                f"{'⚠️ ' + str(dias_r) + ' dias restantes' if dias_r <= 60 else ''}"
                f"<extra></extra>"
            ),
            showlegend=False
        ))

    fig.add_vline(
        x=hoje_ts,
        line_dash="dash",
        line_color="#F1F5F9",
        line_width=2,
        annotation_text="Hoje",
        annotation_font_color="#94A3B8"
    )
    fig.update_layout(
        title={'text':'Validade dos Seguros',
               'font':{'color':'#F1F5F9'}},
        height=max(200, len(seguros_db)*55 + 80),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=200,r=10),
        showlegend=False
    )
    return fig


def _grafico_caucoes_timeline(caucoes_db):
    """Bar chart cauções — capital imobilizado por data."""
    if caucoes_db.empty:
        return None

    caucoes_db = caucoes_db.copy()
    caucoes_db['Fim_d'] = pd.to_datetime(
        caucoes_db.get('Data_Libertacao',''),
        dayfirst=True, errors='coerce'
    )
    caucoes_db['Val_Num'] = pd.to_numeric(
        caucoes_db.get('Valor',0), errors='coerce'
    ).fillna(0)
    caucoes_db = caucoes_db.sort_values('Fim_d')

    obras = caucoes_db.get('Obra', pd.Series()).tolist()
    vals  = caucoes_db['Val_Num'].tolist()
    datas = caucoes_db['Fim_d'].dt.strftime(
        '%d/%m/%Y'
    ).fillna('N/D').tolist()
    hoje_ts = pd.Timestamp(date.today())
    cores = [
        '#EF4444' if pd.notna(d) and d <= hoje_ts + timedelta(days=30)
        else '#F59E0B' if pd.notna(d) and d <= hoje_ts + timedelta(days=90)
        else '#10B981'
        for d in caucoes_db['Fim_d']
    ]

    fig = go.Figure(go.Bar(
        x=[o[:20] for o in obras],
        y=vals,
        marker_color=cores,
        text=[f"€{v:,.0f}" for v in vals],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':10},
        customdata=datas,
        hovertemplate=(
            '%{x}<br>Valor: €%{y:,.0f}<br>'
            'Libertação: %{customdata}<extra></extra>'
        )
    ))
    fig.update_layout(
        title={'text':'Cauções — Capital Imobilizado',
               'font':{'color':'#F1F5F9'}},
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF QUADRO DE AMORTIZAÇÕES
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_amortizacoes(imob_db, empresa: dict) -> bytes:
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    bold_s = ParagraphStyle(
        'bold', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', spaceAfter=3
    )
    sub_s = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#64748B'), spaceAfter=2
    )

    story.append(Paragraph(
        "QUADRO DE IMOBILIZADO E AMORTIZAÇÕES",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=15, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'),
                       spaceAfter=4)
    ))
    story.append(Paragraph(
        f"{empresa.get('nome','')} | "
        f"NIF: {empresa.get('nif','')} | "
        f"Ano: {date.today().year}",
        sub_s
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    # Tabela principal
    header = [
        "Descrição", "Categoria", "Data Compra",
        "Valor Bruto €", "Taxa %", "Amort. Anual €",
        "Amort. Acum. €", "Val. Contab. €", "% Amort."
    ]
    rows = [header]
    tot_bruto = tot_amort_anual = tot_acum = tot_cont = 0.0

    for _, row in imob_db.iterrows():
        vc    = float(row.get('Valor_Compra',0) or 0)
        aa    = float(row.get('Amort_Anual',0) or 0)
        acum  = float(row.get('Amort_Acum',0) or 0)
        cont  = float(row.get('Val_Contabil',0) or 0)
        pct   = round(acum/vc*100,1) if vc > 0 else 0

        rows.append([
            str(row.get('Descricao',''))[:25],
            str(row.get('Categoria','')),
            str(row.get('Data_Compra','')),
            f"€{vc:,.2f}",
            f"{float(row.get('Taxa_Amort',0) or 0):.2f}%",
            f"€{aa:,.2f}",
            f"€{acum:,.2f}",
            f"€{cont:,.2f}",
            f"{pct:.1f}%"
        ])
        tot_bruto       += vc
        tot_amort_anual += aa
        tot_acum        += acum
        tot_cont        += cont

    rows.append([
        "TOTAIS","","",
        f"€{tot_bruto:,.2f}","",
        f"€{tot_amort_anual:,.2f}",
        f"€{tot_acum:,.2f}",
        f"€{tot_cont:,.2f}",
        f"{round(tot_acum/tot_bruto*100,1) if tot_bruto>0 else 0}%"
    ])

    colws = [4*cm,3*cm,2.2*cm,2.5*cm,1.5*cm,
             2.5*cm,2.5*cm,2.5*cm,1.8*cm]
    t = Table(rows, colWidths=colws)
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
        ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTNAME',    (0,-1),(-1,-1),'Helvetica-Bold'),
        ('FONTSIZE',    (0,0),(-1,-1), 7),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('BACKGROUND',  (0,-1),(-1,-1),colors.HexColor('#EFF6FF')),
        ('ROWBACKGROUNDS',(0,1),(-1,-2),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING',  (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING', (0,0),(-1,-1), 4),
        ('ALIGN',       (3,0),(-1,-1), 'RIGHT'),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        f"Documento gerado em "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')} — GESTNOW v3.0",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey)
    ))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_imobilizado(*_):
    """Módulo Imobilizado, Amortizações, Seguros, Cauções, Alvarás."""

    # ── Carregar dados ────────────────────────────────────────────
    imob_db    = _load("imobilizado_db.csv", [
        "ID","Descricao","Categoria","Numero_Serie",
        "Valor_Compra","Data_Compra","Taxa_Amort",
        "Metodo_Amort","Amort_Anual","Amort_Acum",
        "Val_Contabil","Obra_Afeta","Estado","Notas"
    ])
    seguros_db = _load("seguros_db.csv", [
        "ID","Tipo","Entidade","Viatura","Valor_Anual",
        "Data_Inicio","Data_Fim","Apolice","Cobertura",
        "Obra"
    ])
    caucoes_db = _load("caucoes_db.csv", [
        "ID","Obra","Banco","Valor","Data_Constituicao",
        "Data_Libertacao","Estado","Tipo_Cauco","Notas"
    ])
    alvaras_db = _load("alvaras_db.csv", [
        "ID","Tipo","Numero","Entidade","Data_Emissao",
        "Data_Validade","Custo_Renovacao","Estado","Notas"
    ])

    try:
        from mod_admin_diarias import _get_config_empresa
        empresa = _get_config_empresa()
    except:
        empresa = {
            "nome":"Correia Plácido e Sousa, Lda.",
            "nif":"517182718"
        }

    user_nome = st.session_state.get('user','Admin')
    hoje      = date.today()

    # ── KPIs ──────────────────────────────────────────────────────
    val_bruto  = _num(imob_db, 'Valor_Compra')
    val_cont   = _num(imob_db, 'Val_Contabil')
    amort_mes  = _num(imob_db, 'Amort_Anual') / 12
    caucoes_tot= _num(caucoes_db, 'Valor')

    # Alertas expiração
    n_seg_exp = 0
    if not seguros_db.empty and 'Data_Fim' in seguros_db.columns:
        sdb = seguros_db.copy()
        sdb['Fim_d'] = pd.to_datetime(
            sdb['Data_Fim'], dayfirst=True, errors='coerce'
        )
        n_seg_exp = len(sdb[
            sdb['Fim_d'] <= pd.Timestamp(
                hoje + timedelta(days=60)
            )
        ])

    n_alv_exp = 0
    if not alvaras_db.empty and 'Data_Validade' in alvaras_db.columns:
        adb = alvaras_db.copy()
        adb['Val_d'] = pd.to_datetime(
            adb['Data_Validade'], dayfirst=True, errors='coerce'
        )
        n_alv_exp = len(adb[
            adb['Val_d'] <= pd.Timestamp(
                hoje + timedelta(days=90)
            )
        ])

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("🏭 Valor Bruto",    f"€{val_bruto:,.2f}")
    with c2: st.metric("📊 Val. Contabilístico",f"€{val_cont:,.2f}")
    with c3: st.metric("📉 Amort./Mês",     f"€{amort_mes:,.2f}")
    with c4: st.metric("🔒 Cauções",         f"€{caucoes_tot:,.2f}")
    with c5:
        n_alertas = n_seg_exp + n_alv_exp
        cor_alerta = "#EF4444" if n_alertas > 0 else "#10B981"
        st.metric(
            "⚠️ Alertas",
            n_alertas,
            delta="seguros/alvarás a expirar" if n_alertas > 0 else "OK"
        )

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_imob, t_seg,
     t_caucoes, t_alvaras) = st.tabs([
        "🏭 Imobilizado & Amortizações",
        "🛡️ Seguros",
        "🔒 Cauções Bancárias",
        "📋 Alvarás & Licenças",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — IMOBILIZADO & AMORTIZAÇÕES
    # ════════════════════════════════════════════════════════════════
    with t_imob:
        st.markdown("### 🏭 Imobilizado & Amortizações")

        col_form_i, col_lista_i = st.columns([1, 2])

        with col_form_i:
            st.markdown("#### ➕ Novo Ativo")
            with st.form("form_imob"):
                i_desc   = st.text_input(
                    "Descrição *", key="imob_desc",
                    placeholder="Ex: Multímetro Fluke 289"
                )
                i_cat    = st.selectbox(
                    "Categoria *",
                    list(TAXAS_AMORTIZACAO.keys()),
                    key="imob_cat"
                )
                # Taxa automática pela categoria
                taxa_auto = TAXAS_AMORTIZACAO[i_cat]["taxa"]
                vida_auto = TAXAS_AMORTIZACAO[i_cat]["vida"]

                i_serie  = st.text_input(
                    "Nº Série / Referência", key="imob_serie"
                )
                col_iv1, col_iv2 = st.columns(2)
                with col_iv1:
                    i_valor  = st.number_input(
                        "Valor de Compra (€) *",
                        min_value=0.0, step=100.0,
                        key="imob_valor"
                    )
                with col_iv2:
                    i_data   = st.text_input(
                        "Data Compra (dd/mm/aaaa)",
                        value=hoje.strftime("%d/%m/%Y"),
                        key="imob_data"
                    )

                i_taxa   = st.number_input(
                    f"Taxa Amortização (% / ano) — "
                    f"automático: {taxa_auto}%",
                    min_value=0.0, max_value=100.0,
                    value=taxa_auto, step=0.5,
                    key="imob_taxa"
                )
                i_metodo = st.selectbox(
                    "Método",
                    ["linear","decrescente"],
                    key="imob_metodo"
                )
                i_obra   = st.text_input(
                    "Obra/Departamento afeto",
                    key="imob_obra"
                )
                i_estado = st.selectbox(
                    "Estado",
                    ["Ativo","Em Manutenção",
                     "Abatido","Cedido"],
                    key="imob_estado"
                )
                i_notas  = st.text_area(
                    "Notas", key="imob_notas"
                )

                # Preview amortização
                if i_valor > 0 and i_taxa > 0:
                    amort_calc = _calcular_amortizacao(
                        i_valor, i_taxa, i_data, i_metodo
                    )
                    st.markdown(
                        f"<div style='background:rgba(59,130,246,0.1);"
                        f"border:1px solid #3B82F6;"
                        f"border-radius:8px;padding:10px;"
                        f"margin:8px 0;'>"
                        f"<small style='color:#94A3B8;'>"
                        f"Amort. anual: "
                        f"<b style='color:#3B82F6;'>"
                        f"€{amort_calc['amort_anual']:,.2f}</b> · "
                        f"Vida útil: {amort_calc['vida_util']} anos · "
                        f"Val. atual: "
                        f"<b style='color:#10B981;'>"
                        f"€{amort_calc['val_contabil']:,.2f}</b>"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

                if st.form_submit_button(
                    "💾 Registar Ativo",
                    use_container_width=True, type="primary"
                ):
                    if not i_desc.strip() or i_valor <= 0:
                        st.error("❌ Descrição e valor obrigatórios.")
                    else:
                        amort_f = _calcular_amortizacao(
                            i_valor, i_taxa, i_data, i_metodo
                        )
                        novo_i = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Descricao":   i_desc.strip(),
                            "Categoria":   i_cat,
                            "Numero_Serie":i_serie.strip(),
                            "Valor_Compra":i_valor,
                            "Data_Compra": i_data.strip(),
                            "Taxa_Amort":  i_taxa,
                            "Metodo_Amort":i_metodo,
                            "Amort_Anual": amort_f['amort_anual'],
                            "Amort_Acum":  amort_f['amort_acum'],
                            "Val_Contabil":amort_f['val_contabil'],
                            "Obra_Afeta":  i_obra.strip(),
                            "Estado":      i_estado,
                            "Notas":       i_notas.strip()
                        }])
                        upd_i = pd.concat(
                            [imob_db, novo_i], ignore_index=True
                        ) if not imob_db.empty else novo_i
                        save_db(upd_i, "imobilizado_db.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="CRIAR_ATIVO_IMOBILIZADO",
                            tabela="imobilizado_db.csv",
                            registro_id=novo_i['ID'].iloc[0],
                            detalhes=(
                                f"{i_desc} | "
                                f"€{i_valor} | {i_cat}"
                            ),
                            ip=""
                        )
                        inv()
                        st.success(
                            f"✅ {i_desc} registado! "
                            f"Amort. anual: "
                            f"€{amort_f['amort_anual']:,.2f}"
                        )
                        st.rerun()

        with col_lista_i:
            st.markdown("#### 📊 Inventário de Imobilizado")

            # Gráficos
            col_dg1, col_dg2 = st.columns(2)
            with col_dg1:
                fig_don = _grafico_imobilizado_donut(imob_db)
                if fig_don:
                    st.plotly_chart(
                        fig_don, use_container_width=True
                    )
            with col_dg2:
                fig_bar = _grafico_amort_acumulada_total(imob_db)
                if fig_bar:
                    st.plotly_chart(
                        fig_bar, use_container_width=True
                    )

            if imob_db.empty:
                st.info("📋 Sem ativos registados.")
            else:
                # Filtro estado
                estados_f = ["Todos"] + \
                            imob_db['Estado'].unique().tolist() \
                            if 'Estado' in imob_db.columns \
                            else ["Todos"]
                est_filt = st.selectbox(
                    "Filtrar", estados_f, key="imob_filt"
                )
                df_imob = imob_db.copy()
                if est_filt != "Todos":
                    df_imob = df_imob[
                        df_imob['Estado'] == est_filt
                    ]

                for _, ativo in df_imob.iterrows():
                    aid    = ativo.get('ID','')
                    vc_a   = float(ativo.get('Valor_Compra',0) or 0)
                    vco_a  = float(ativo.get('Val_Contabil',0) or 0)
                    pct_a  = round(
                        (vc_a - vco_a) / vc_a * 100, 0
                    ) if vc_a > 0 else 0
                    est_a  = ativo.get('Estado','')
                    cor_a  = {
                        'Ativo':         '#10B981',
                        'Em Manutenção': '#F59E0B',
                        'Abatido':       '#64748B',
                        'Cedido':        '#3B82F6',
                    }.get(est_a,'#6B7280')

                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:12px;"
                        f"margin-bottom:8px;"
                        f"border-left:4px solid {cor_a};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:0.9rem;'>"
                        f"{ativo.get('Descricao','')[:35]}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"📦 {ativo.get('Categoria','')} · "
                        f"#{ativo.get('Numero_Serie','')} · "
                        f"🏭 {ativo.get('Obra_Afeta','')} · "
                        f"Compra: {ativo.get('Data_Compra','')}"
                        f"</small>"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<b style='color:#F1F5F9;'>"
                        f"€{vco_a:,.2f}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"/{vc_a:,.2f} bruto</small>"
                        f"</div></div>"
                        f"<div style='background:#0F172A;"
                        f"border-radius:3px;height:5px;"
                        f"margin:8px 0 4px;'>"
                        f"<div style='background:#EF4444;"
                        f"width:{pct_a:.0f}%;height:5px;"
                        f"border-radius:3px;'></div></div>"
                        f"<small style='color:#64748B;'>"
                        f"Amortizado: {pct_a:.0f}% · "
                        f"Taxa: {float(ativo.get('Taxa_Amort',0) or 0):.1f}%/ano · "
                        f"€{float(ativo.get('Amort_Anual',0) or 0):,.2f}/ano"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

                    # Ver detalhe + timeline
                    col_ad1, col_ad2 = st.columns([3,1])
                    with col_ad2:
                        if st.button(
                            "📊",
                            key=f"imob_det_{aid}",
                            use_container_width=True,
                            help="Ver timeline amortização"
                        ):
                            st.session_state['imob_detail'] = aid

                    if st.session_state.get('imob_detail') == aid:
                        amort_d = _calcular_amortizacao(
                            vc_a,
                            float(ativo.get('Taxa_Amort',10) or 10),
                            str(ativo.get('Data_Compra','')),
                            str(ativo.get('Metodo_Amort','linear'))
                        )
                        st.plotly_chart(
                            _grafico_amort_timeline(
                                amort_d['mapa_anual'],
                                ativo.get('Descricao','')
                            ),
                            use_container_width=True
                        )
                        # Tabela mapa
                        df_mapa = pd.DataFrame(
                            amort_d['mapa_anual']
                        )
                        st.dataframe(
                            df_mapa,
                            use_container_width=True,
                            hide_index=True
                        )
                        if st.button(
                            "✖ Fechar",
                            key=f"fechar_imob_{aid}"
                        ):
                            st.session_state.pop(
                                'imob_detail', None
                            )
                            st.rerun()

        # Quadro anual + export PDF
        st.markdown("---")
        st.markdown("#### 📋 Quadro de Amortizações Anual")

        ano_qa = st.number_input(
            "Ano",
            min_value=2020,
            value=date.today().year,
            key="qa_ano"
        )

        if not imob_db.empty:
            col_qa1, col_qa2 = st.columns(2)
            total_amort_anual = _num(imob_db, 'Amort_Anual')
            total_bruto       = _num(imob_db, 'Valor_Compra')
            total_contabil    = _num(imob_db, 'Val_Contabil')

            with col_qa1:
                st.metric(
                    "📉 Total Amortizações Anuais",
                    f"€{total_amort_anual:,.2f}"
                )
            with col_qa2:
                st.metric(
                    "📊 Val. Líquido Contabilístico",
                    f"€{total_contabil:,.2f}",
                    delta=f"de €{total_bruto:,.2f} bruto"
                )

            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button(
                    "📄 Gerar Quadro PDF",
                    key="btn_pdf_amort",
                    type="primary",
                    use_container_width=True
                ):
                    with st.spinner("A gerar..."):
                        pdf_qa = _gerar_pdf_amortizacoes(
                            imob_db, empresa
                        )
                    st.session_state['amort_pdf'] = pdf_qa
                    st.rerun()

            with col_exp2:
                if st.session_state.get('amort_pdf'):
                    st.download_button(
                        "📥 Descarregar PDF",
                        data=st.session_state['amort_pdf'],
                        file_name=(
                            f"quadro_amortizacoes_{ano_qa}.pdf"
                        ),
                        mime="application/pdf",
                        key="dl_amort_pdf",
                        use_container_width=True,
                        type="primary"
                    )

            # Export CSV
            csv_imob = imob_db[[
                c for c in [
                    'Descricao','Categoria','Data_Compra',
                    'Valor_Compra','Taxa_Amort','Amort_Anual',
                    'Amort_Acum','Val_Contabil','Estado'
                ] if c in imob_db.columns
            ]].to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 Exportar CSV",
                data=csv_imob.encode('utf-8-sig'),
                file_name=f"imobilizado_{ano_qa}.csv",
                mime="text/csv",
                key="dl_imob_csv"
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — SEGUROS
    # ════════════════════════════════════════════════════════════════
    with t_seg:
        st.markdown("### 🛡️ Gestão de Seguros")

        col_sf, col_sl = st.columns([1, 2])

        with col_sf:
            st.markdown("#### ➕ Novo Seguro")
            with st.form("form_seg_imob"):
                s_tipo  = st.selectbox(
                    "Tipo *",
                    ["Responsabilidade Civil Geral",
                     "Responsabilidade Civil Obras",
                     "Acidentes de Trabalho",
                     "Seguro Multirriscos Instalações",
                     "Seguro Automóvel (RC)",
                     "Seguro Automóvel (Danos Próprios)",
                     "Seguro de Equipamentos",
                     "Seguro de Caução",
                     "Seguro de Saúde Grupo",
                     "Outro"],
                    key="seg_tipo_imob"
                )
                s_ent   = st.text_input(
                    "Seguradora *", key="seg_ent_imob"
                )
                s_apol  = st.text_input(
                    "Nº Apólice", key="seg_apol_imob"
                )
                s_cob   = st.text_area(
                    "Cobertura", key="seg_cob_imob",
                    placeholder="Ex: RC até €5.000.000, "
                                "danos materiais, pessoais..."
                )
                col_sv1, col_sv2 = st.columns(2)
                with col_sv1:
                    s_val = st.number_input(
                        "Prémio Anual (€)",
                        min_value=0.0, step=50.0,
                        key="seg_val_imob"
                    )
                with col_sv2:
                    s_obra = st.text_input(
                        "Obra / Ativo",
                        key="seg_obra_imob",
                        placeholder="Toda a empresa"
                    )
                col_sd1, col_sd2 = st.columns(2)
                with col_sd1:
                    s_ini = st.date_input(
                        "Início",
                        value=hoje, key="seg_ini_imob"
                    )
                with col_sd2:
                    s_fim = st.date_input(
                        "Fim",
                        value=hoje + timedelta(days=365),
                        key="seg_fim_imob"
                    )

                if st.form_submit_button(
                    "💾 Guardar Seguro",
                    use_container_width=True, type="primary"
                ):
                    if not s_ent.strip():
                        st.error("❌ Seguradora obrigatória.")
                    else:
                        novo_s = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Tipo":        s_tipo,
                            "Entidade":    s_ent.strip(),
                            "Viatura":     "",
                            "Valor_Anual": s_val,
                            "Data_Inicio": s_ini.strftime("%d/%m/%Y"),
                            "Data_Fim":    s_fim.strftime("%d/%m/%Y"),
                            "Apolice":     s_apol.strip(),
                            "Cobertura":   s_cob.strip(),
                            "Obra":        s_obra.strip()
                        }])
                        upd_s = pd.concat(
                            [seguros_db, novo_s], ignore_index=True
                        ) if not seguros_db.empty else novo_s
                        save_db(upd_s, "seguros_db.csv")
                        inv()
                        st.success("✅ Seguro registado!")
                        st.rerun()

        with col_sl:
            st.markdown("#### 📋 Seguros Ativos")

            # Timeline
            fig_seg_tl = _grafico_seguros_timeline(seguros_db)
            if fig_seg_tl:
                st.plotly_chart(
                    fig_seg_tl, use_container_width=True
                )

            if seguros_db.empty:
                st.info("📋 Sem seguros registados.")
            else:
                total_premios = _num(seguros_db, 'Valor_Anual')
                st.metric(
                    "💰 Total Prémios Anuais",
                    f"€{total_premios:,.2f}",
                    delta=f"€{total_premios/12:,.2f}/mês"
                )

                for _, seg in seguros_db.sort_values(
                    'Data_Fim'
                ).iterrows():
                    sid    = seg.get('ID','')
                    dias_s = _dias_para(seg.get('Data_Fim',''))
                    val_s  = float(seg.get('Valor_Anual',0) or 0)

                    if dias_s <= 0:
                        cor_s   = "#EF4444"
                        alert_s = "🔴 EXPIRADO"
                    elif dias_s <= 30:
                        cor_s   = "#EF4444"
                        alert_s = f"🔴 Expira em {dias_s}d!"
                    elif dias_s <= 60:
                        cor_s   = "#F59E0B"
                        alert_s = f"⚠️ {dias_s} dias"
                    else:
                        cor_s   = "#10B981"
                        alert_s = f"✅ {dias_s}d"

                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:12px;"
                        f"margin-bottom:8px;"
                        f"border-left:4px solid {cor_s};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:0.9rem;'>"
                        f"{seg.get('Tipo','')[:40]}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"🏢 {seg.get('Entidade','')} · "
                        f"📋 {seg.get('Apolice','')} · "
                        f"🏭 {seg.get('Obra','')}"
                        f"</small><br>"
                        f"<small style='color:#94A3B8;'>"
                        f"{seg.get('Cobertura','')[:60]}</small><br>"
                        f"<small style='color:#64748B;'>"
                        f"{seg.get('Data_Inicio','')} → "
                        f"{seg.get('Data_Fim','')}"
                        f"</small>"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<b style='color:#F1F5F9;'>"
                        f"€{val_s:,.2f}/ano</b><br>"
                        f"<span style='color:{cor_s};"
                        f"font-size:0.8rem;font-weight:700;'>"
                        f"{alert_s}</span>"
                        f"</div></div></div>",
                        unsafe_allow_html=True
                    )

    # ════════════════════════════════════════════════════════════════
    # TAB — CAUÇÕES BANCÁRIAS
    # ════════════════════════════════════════════════════════════════
    with t_caucoes:
        st.markdown("### 🔒 Cauções Bancárias")
        st.info(
            "As cauções são garantias financeiras exigidas "
            "em contratos de obra (normalmente 5-10% do valor). "
            "O capital fica imobilizado no banco até libertação "
            "pelo dono de obra."
        )

        col_cf1, col_cf2 = st.columns([1, 2])

        with col_cf1:
            st.markdown("#### ➕ Nova Caução")
            with st.form("form_caucao"):
                ca_obra  = st.text_input(
                    "Obra *", key="ca_obra"
                )
                ca_banco = st.selectbox(
                    "Banco *",
                    ["Montepio","CGD","BCP","Santander",
                     "Novo Banco","BPI","EuroBic","Outro"],
                    key="ca_banco"
                )
                ca_tipo  = st.selectbox(
                    "Tipo Caução",
                    ["Caução de Boa Execução",
                     "Caução de Garantia",
                     "Garantia Bancária Autónoma",
                     "Depósito a Prazo Caucionado",
                     "Outro"],
                    key="ca_tipo"
                )
                ca_val   = st.number_input(
                    "Valor (€) *",
                    min_value=0.0, step=500.0,
                    key="ca_val"
                )
                col_cd1, col_cd2 = st.columns(2)
                with col_cd1:
                    ca_ini = st.date_input(
                        "Constituição",
                        value=hoje, key="ca_ini"
                    )
                with col_cd2:
                    ca_lib = st.date_input(
                        "Libertação Prevista",
                        value=hoje + timedelta(days=365),
                        key="ca_lib"
                    )
                ca_notas = st.text_area(
                    "Notas", key="ca_notas"
                )

                if st.form_submit_button(
                    "💾 Registar Caução",
                    use_container_width=True, type="primary"
                ):
                    if not ca_obra.strip() or ca_val <= 0:
                        st.error("❌ Obra e valor obrigatórios.")
                    else:
                        nova_ca = pd.DataFrame([{
                            "ID":               str(uuid.uuid4())[:8].upper(),
                            "Obra":             ca_obra.strip(),
                            "Banco":            ca_banco,
                            "Valor":            ca_val,
                            "Data_Constituicao":ca_ini.strftime("%d/%m/%Y"),
                            "Data_Libertacao":  ca_lib.strftime("%d/%m/%Y"),
                            "Estado":           "Ativa",
                            "Tipo_Cauco":       ca_tipo,
                            "Notas":            ca_notas.strip()
                        }])
                        upd_ca = pd.concat(
                            [caucoes_db, nova_ca], ignore_index=True
                        ) if not caucoes_db.empty else nova_ca
                        save_db(upd_ca, "caucoes_db.csv")
                        inv()
                        st.success(
                            f"✅ Caução €{ca_val:,.2f} "
                            f"registada para {ca_obra}!"
                        )
                        st.rerun()

        with col_cf2:
            st.markdown("#### 📊 Cauções Ativas")

            # Gráfico
            fig_cau = _grafico_caucoes_timeline(caucoes_db)
            if fig_cau:
                st.plotly_chart(
                    fig_cau, use_container_width=True
                )

            if caucoes_db.empty:
                st.info("📋 Sem cauções registadas.")
            else:
                # KPIs
                cau_ativas = caucoes_db[
                    caucoes_db.get('Estado','') == 'Ativa'
                ] if 'Estado' in caucoes_db.columns else caucoes_db
                total_cau  = _num(cau_ativas, 'Valor')
                n_cau      = len(cau_ativas)

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("🔒 Cauções Ativas", n_cau)
                with c2:
                    st.metric(
                        "💰 Capital Imobilizado",
                        f"€{total_cau:,.2f}"
                    )

                for _, cau in caucoes_db.sort_values(
                    'Data_Libertacao'
                ).iterrows():
                    cau_id  = cau.get('ID','')
                    dias_c  = _dias_para(
                        cau.get('Data_Libertacao','')
                    )
                    val_c   = float(cau.get('Valor',0) or 0)
                    est_c   = cau.get('Estado','Ativa')

                    if est_c == 'Libertada':
                        cor_c   = "#64748B"
                        alert_c = "✅ Libertada"
                    elif dias_c <= 0:
                        cor_c   = "#10B981"
                        alert_c = "🔓 Pronta a libertar!"
                    elif dias_c <= 30:
                        cor_c   = "#10B981"
                        alert_c = f"🔓 Liberta em {dias_c}d"
                    elif dias_c <= 90:
                        cor_c   = "#3B82F6"
                        alert_c = f"📅 {dias_c} dias"
                    else:
                        cor_c   = "#F59E0B"
                        alert_c = f"🔒 {dias_c} dias"

                    col_ci, col_cb = st.columns([5,1])
                    with col_ci:
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:10px;padding:12px;"
                            f"margin-bottom:6px;"
                            f"border-left:4px solid {cor_c};'>"
                            f"<div style='display:flex;"
                            f"justify-content:space-between;'>"
                            f"<div>"
                            f"<b style='color:#F1F5F9;'>"
                            f"🔒 {cau.get('Obra','')[:30]}</b><br>"
                            f"<small style='color:#64748B;'>"
                            f"🏦 {cau.get('Banco','')} · "
                            f"{cau.get('Tipo_Cauco','')} · "
                            f"Constitução: "
                            f"{cau.get('Data_Constituicao','')}"
                            f"</small><br>"
                            f"<small style='color:#94A3B8;'>"
                            f"Libertação: "
                            f"{cau.get('Data_Libertacao','')}"
                            f"</small>"
                            f"</div>"
                            f"<div style='text-align:right;'>"
                            f"<b style='color:#F1F5F9;"
                            f"font-size:1.05rem;'>"
                            f"€{val_c:,.2f}</b><br>"
                            f"<span style='color:{cor_c};"
                            f"font-weight:700;"
                            f"font-size:0.8rem;'>"
                            f"{alert_c}</span>"
                            f"</div></div></div>",
                            unsafe_allow_html=True
                        )
                    with col_cb:
                        if est_c != 'Libertada':
                            if st.button(
                                "🔓",
                                key=f"libertar_{cau_id}",
                                use_container_width=True,
                                help="Marcar como libertada"
                            ):
                                caucoes_db.loc[
                                    caucoes_db['ID'] == cau_id,
                                    'Estado'
                                ] = 'Libertada'
                                save_db(
                                    caucoes_db, "caucoes_db.csv"
                                )
                                inv()
                                st.success(
                                    f"✅ Caução €{val_c:,.2f} "
                                    f"libertada!"
                                )
                                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — ALVARÁS & LICENÇAS
    # ════════════════════════════════════════════════════════════════
    with t_alvaras:
        st.markdown("### 📋 Alvarás & Licenças")
        st.info(
            "Controlo de todas as licenças e alvarás obrigatórios. "
            "A empresa fica sem poder operar se um alvará expirar. "
            "Alertas a 90/60/30 dias."
        )

        col_af, col_al = st.columns([1, 2])

        with col_af:
            st.markdown("#### ➕ Novo Alvará / Licença")
            with st.form("form_alvara"):
                al_tipo = st.selectbox(
                    "Tipo *",
                    ["Alvará de Construção (INCI)",
                     "Alvará Classe 1 — Obras Simples",
                     "Alvará Classe 2 — Obras até €332.000",
                     "Alvará Classe 3 — Obras até €1.328.000",
                     "Alvará Classe 4 — Obras até €5.312.000",
                     "Alvará Especialidade Instalações",
                     "Alvará Especialidade Instrumentação",
                     "Licença Ambiental",
                     "Certificação ISO 9001",
                     "Certificação ISO 14001",
                     "OHSAS 18001 / ISO 45001",
                     "Licença Utilização Instalações",
                     "Registo IMPIC",
                     "Outro"],
                    key="al_tipo"
                )
                al_num  = st.text_input(
                    "Número *", key="al_num"
                )
                al_ent  = st.text_input(
                    "Entidade Emissora",
                    key="al_ent",
                    placeholder="Ex: IMPIC, INCM, APCER..."
                )
                col_ad1, col_ad2 = st.columns(2)
                with col_ad1:
                    al_emis = st.date_input(
                        "Emissão",
                        value=hoje, key="al_emis"
                    )
                with col_ad2:
                    al_val  = st.date_input(
                        "Validade",
                        value=hoje + timedelta(days=365),
                        key="al_val"
                    )
                al_custo = st.number_input(
                    "Custo de Renovação (€)",
                    min_value=0.0, step=50.0,
                    key="al_custo"
                )
                al_notas = st.text_area(
                    "Notas", key="al_notas",
                    placeholder="Ex: Subcategorias, condições..."
                )

                if st.form_submit_button(
                    "💾 Registar Alvará",
                    use_container_width=True, type="primary"
                ):
                    if not al_num.strip():
                        st.error("❌ Número obrigatório.")
                    else:
                        novo_al = pd.DataFrame([{
                            "ID":             str(uuid.uuid4())[:8].upper(),
                            "Tipo":           al_tipo,
                            "Numero":         al_num.strip(),
                            "Entidade":       al_ent.strip(),
                            "Data_Emissao":   al_emis.strftime("%d/%m/%Y"),
                            "Data_Validade":  al_val.strftime("%d/%m/%Y"),
                            "Custo_Renovacao":al_custo,
                            "Estado":         "Válido",
                            "Notas":          al_notas.strip()
                        }])
                        upd_al = pd.concat(
                            [alvaras_db, novo_al], ignore_index=True
                        ) if not alvaras_db.empty else novo_al
                        save_db(upd_al, "alvaras_db.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="CRIAR_ALVARA",
                            tabela="alvaras_db.csv",
                            registro_id=novo_al['ID'].iloc[0],
                            detalhes=(
                                f"{al_tipo} | "
                                f"Nº {al_num}"
                            ),
                            ip=""
                        )
                        inv()
                        st.success("✅ Alvará registado!")
                        st.rerun()

        with col_al:
            st.markdown("#### 📊 Alvarás & Licenças")

            if alvaras_db.empty:
                st.info("📋 Sem alvarás registados.")
            else:
                # KPIs
                tot_al   = len(alvaras_db)
                a_expirar= len(alvaras_db[
                    pd.to_datetime(
                        alvaras_db.get('Data_Validade',''),
                        dayfirst=True, errors='coerce'
                    ) <= pd.Timestamp(hoje + timedelta(days=90))
                ]) if 'Data_Validade' in alvaras_db.columns else 0

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("📋 Total Alvarás", tot_al)
                with c2:
                    st.metric(
                        "⚠️ A Expirar (90d)",
                        a_expirar,
                        delta="🔴 Urgente!" if a_expirar > 0 else "✅"
                    )

                # Ordenar por validade
                alvaras_s = alvaras_db.copy()
                if 'Data_Validade' in alvaras_s.columns:
                    alvaras_s['Val_d'] = pd.to_datetime(
                        alvaras_s['Data_Validade'],
                        dayfirst=True, errors='coerce'
                    )
                    alvaras_s = alvaras_s.sort_values('Val_d')

                for _, al in alvaras_s.iterrows():
                    al_id   = al.get('ID','')
                    dias_al = _dias_para(al.get('Data_Validade',''))
                    custo_r = float(al.get('Custo_Renovacao',0) or 0)

                    if dias_al <= 0:
                        cor_al  = "#EF4444"
                        alert_al= "🔴 EXPIRADO — RENOVAR URGENTE!"
                    elif dias_al <= 30:
                        cor_al  = "#EF4444"
                        alert_al= f"🔴 Expira em {dias_al} dias!"
                    elif dias_al <= 60:
                        cor_al  = "#F59E0B"
                        alert_al= f"⚠️ Expira em {dias_al} dias"
                    elif dias_al <= 90:
                        cor_al  = "#F59E0B"
                        alert_al= f"📋 {dias_al} dias"
                    else:
                        cor_al  = "#10B981"
                        alert_al= f"✅ {dias_al} dias"

                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:12px;"
                        f"margin-bottom:8px;"
                        f"border-left:4px solid {cor_al};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;"
                        f"align-items:flex-start;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:0.9rem;'>"
                        f"{al.get('Tipo','')[:40]}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"Nº {al.get('Numero','')} · "
                        f"{al.get('Entidade','')} · "
                        f"Emissão: {al.get('Data_Emissao','')} · "
                        f"Validade: {al.get('Data_Validade','')}"
                        f"</small>"
                        f"</div>"
                        f"<div style='text-align:right;"
                        f"min-width:160px;'>"
                        f"<span style='color:{cor_al};"
                        f"font-weight:700;"
                        f"font-size:0.8rem;'>"
                        f"{alert_al}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"Renovação: €{custo_r:,.2f}"
                        f"</small>"
                        f"</div></div>"
                        f"{'<br><small style=color:#94A3B8;>' + str(al.get('Notas',''))[:80] + '</small>' if al.get('Notas') else ''}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    col_as, col_ar = st.columns([3,1])
                    with col_ar:
                        novo_est_al = st.selectbox(
                            "Estado",
                            ["Válido","Renovado","Expirado",
                             "Em Renovação"],
                            key=f"al_est_{al_id}",
                            label_visibility="collapsed"
                        )
                        if st.button(
                            "✅",
                            key=f"al_upd_{al_id}",
                            use_container_width=True,
                            help="Atualizar estado"
                        ):
                            alvaras_db.loc[
                                alvaras_db['ID'] == al_id,
                                'Estado'
                            ] = novo_est_al
                            save_db(alvaras_db, "alvaras_db.csv")
                            inv(); st.rerun()

                # Export
                csv_al = alvaras_db[[
                    c for c in [
                        'Tipo','Numero','Entidade',
                        'Data_Emissao','Data_Validade',
                        'Custo_Renovacao','Estado'
                    ] if c in alvaras_db.columns
                ]].to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "📥 Exportar Alvarás",
                    data=csv_al.encode('utf-8-sig'),
                    file_name="alvaras_licencas.csv",
                    mime="text/csv",
                    key="dl_alv_csv"
                )

                # Custo total renovações próximas
                if a_expirar > 0:
                    alv_exp = alvaras_db.copy()
                    if 'Data_Validade' in alv_exp.columns:
                        alv_exp['Val_d'] = pd.to_datetime(
                            alv_exp['Data_Validade'],
                            dayfirst=True, errors='coerce'
                        )
                        alv_exp_90 = alv_exp[
                            alv_exp['Val_d'] <= pd.Timestamp(
                                hoje + timedelta(days=90)
                            )
                        ]
                        custo_renov = pd.to_numeric(
                            alv_exp_90.get('Custo_Renovacao',0),
                            errors='coerce'
                        ).fillna(0).sum()
                        st.markdown(
                            f"<div style='background:rgba(239,68,68,0.1);"
                            f"border:1px solid #EF4444;"
                            f"border-radius:8px;padding:12px;"
                            f"margin-top:8px;'>"
                            f"<b style='color:#EF4444;'>"
                            f"⚠️ Custo total renovações urgentes "
                            f"(90 dias): "
                            f"€{custo_renov:,.2f}</b>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

"""
GESTNOW v3 — mod_fat_obras.py
Passo 6 — Performance por Obra (P&L, Orçamento vs Real, WIP, Score)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import uuid, io, os
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from core import save_db, inv, load_db, fh, log_audit

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

def _num_row(row, col, default=0.0):
    try:
        return float(row.get(col, default) or default)
    except:
        return default

# ─────────────────────────────────────────────────────────────────
# MOTOR DE P&L POR OBRA
# ─────────────────────────────────────────────────────────────────

def _calcular_pl_obra(obra: str,
                       registos_db, faturas_cli,
                       compras_db, dormidas_db,
                       comb_db, diarias_pag_db,
                       rh_db, inst_acessos_db) -> dict:
    """Calcula P&L completo de uma obra."""

    # ── RECEITA ───────────────────────────────────────────────────
    # Faturas emitidas ao cliente para esta obra
    rec_faturas = 0.0
    if not faturas_cli.empty and 'Obra' in faturas_cli.columns:
        fc_obra = faturas_cli[faturas_cli['Obra'] == obra]
        rec_faturas = pd.to_numeric(
            fc_obra.get('Total', 0), errors='coerce'
        ).fillna(0).sum()

    # Horas × preço hora (a faturar / em curso)
    rec_horas_est = 0.0
    horas_totais  = 0.0
    if not registos_db.empty and 'Obra' in registos_db.columns:
        regs = registos_db[registos_db['Obra'] == obra].copy()
        horas_totais = pd.to_numeric(
            regs.get('Horas_Total', 0), errors='coerce'
        ).fillna(0).sum()
        # Preço hora médio por técnico
        preco_hora_medio = 15.0
        if not inst_acessos_db.empty and \
           'Obra' in inst_acessos_db.columns:
            ac = inst_acessos_db[inst_acessos_db['Obra'] == obra]
            if not ac.empty and 'PrecoHora' in ac.columns:
                ph = pd.to_numeric(
                    ac['PrecoHora'], errors='coerce'
                ).fillna(15.0)
                preco_hora_medio = ph.mean() if not ph.empty else 15.0
        rec_horas_est = round(horas_totais * preco_hora_medio, 2)

    receita_total = max(rec_faturas, rec_horas_est)

    # ── CUSTOS DIRETOS ────────────────────────────────────────────
    # Mão de obra (custo empresa)
    custo_mao_obra = 0.0
    if not registos_db.empty and 'Obra' in registos_db.columns:
        regs_c = registos_db[registos_db['Obra'] == obra]
        # Custo hora empresa estimado (TSU incluída)
        custo_hora_emp = 12.0  # estimativa €12/h custo empresa
        if not rh_db.empty and 'Salario_Base' in rh_db.columns:
            sal_medio = pd.to_numeric(
                rh_db['Salario_Base'], errors='coerce'
            ).fillna(870).mean()
            # Custo hora = salário × 1.4 (encargos) / 160h
            custo_hora_emp = round(sal_medio * 1.4 / 160, 2)
        custo_mao_obra = round(horas_totais * custo_hora_emp, 2)

    # Materiais / Compras
    custo_materiais = 0.0
    if not compras_db.empty and 'Obra' in compras_db.columns:
        c_obra = compras_db[compras_db['Obra'] == obra]
        custo_materiais = _num(c_obra, 'Total')

    # Dormidas
    custo_dormidas = 0.0
    if not dormidas_db.empty and 'Obra' in dormidas_db.columns:
        d_obra = dormidas_db[dormidas_db['Obra'] == obra]
        custo_dormidas = _num(d_obra, 'Total')

    # Diárias
    custo_diarias = 0.0
    if not diarias_pag_db.empty:
        if 'Obras' in diarias_pag_db.columns:
            d_obra2 = diarias_pag_db[
                diarias_pag_db['Obras'].str.contains(obra, na=False)
            ]
            custo_diarias = _num(d_obra2, 'Valor_Total')

    # Combustível (estimativa proporcional)
    custo_comb = 0.0
    if not comb_db.empty:
        custo_comb = _num(comb_db, 'Valor') / max(1, 3)  # / nº obras ativas

    custo_total = round(
        custo_mao_obra + custo_materiais +
        custo_dormidas + custo_diarias + custo_comb, 2
    )

    # ── MARGEM ────────────────────────────────────────────────────
    margem_bruta  = round(receita_total - custo_total, 2)
    margem_pct    = round(
        margem_bruta / receita_total * 100, 1
    ) if receita_total > 0 else 0.0

    return {
        "obra":             obra,
        "receita_faturas":  rec_faturas,
        "receita_horas":    rec_horas_est,
        "receita_total":    receita_total,
        "horas_totais":     horas_totais,
        "custo_mao_obra":   custo_mao_obra,
        "custo_materiais":  custo_materiais,
        "custo_dormidas":   custo_dormidas,
        "custo_diarias":    custo_diarias,
        "custo_comb":       custo_comb,
        "custo_total":      custo_total,
        "margem_bruta":     margem_bruta,
        "margem_pct":       margem_pct,
    }


def _calcular_score_pl(pl: dict, orc: dict) -> tuple[int, dict]:
    """Score 0-100 baseado no P&L e orçamento."""
    score = 0
    det   = {}

    # 1. Margem (0-25 pts)
    m = pl.get('margem_pct', 0)
    if m >= 30:      pts = 25
    elif m >= 20:    pts = 20
    elif m >= 10:    pts = 12
    elif m >= 0:     pts = 5
    else:            pts = 0
    score += pts; det['Margem'] = (pts, 25)

    # 2. Desvio custos vs orçamento (0-20 pts)
    orc_custos = float(orc.get('Orcamento_Custos', 0) or 0)
    if orc_custos > 0:
        desvio = (pl['custo_total'] - orc_custos) / orc_custos * 100
        if desvio <= 0:      pts = 20
        elif desvio <= 5:    pts = 17
        elif desvio <= 10:   pts = 12
        elif desvio <= 20:   pts = 6
        else:                pts = 0
    else:
        pts = 10  # sem orçamento, neutro
    score += pts; det['Custos vs Orc.'] = (pts, 20)

    # 3. Receita vs orçamento (0-20 pts)
    orc_rec = float(orc.get('Orcamento_Receita', 0) or 0)
    if orc_rec > 0:
        pct_rec = pl['receita_total'] / orc_rec * 100
        if pct_rec >= 100:    pts = 20
        elif pct_rec >= 85:   pts = 15
        elif pct_rec >= 70:   pts = 8
        else:                 pts = 0
    else:
        pts = 10
    score += pts; det['Receita vs Orc.'] = (pts, 20)

    # 4. Horas registadas (0-15 pts)
    if pl['horas_totais'] > 0:    pts = 15
    elif pl['horas_totais'] > -1: pts = 5
    else:                         pts = 0
    score += pts; det['Atividade'] = (pts, 15)

    # 5. WIP controlado (0-10 pts)
    wip = float(orc.get('WIP', 0) or 0)
    if wip == 0:     pts = 10
    elif wip < 5000: pts = 7
    else:            pts = 3
    score += pts; det['WIP'] = (pts, 10)

    # 6. Cobrança (0-10 pts)
    if pl['receita_faturas'] > 0: pts = 10
    else:                         pts = 5
    score += pts; det['Faturação'] = (pts, 10)

    return min(100, score), det


def _rag(score):
    if score >= 70: return "#10B981", "🟢"
    if score >= 40: return "#F59E0B", "🟡"
    return "#EF4444", "🔴"


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_pl_waterfall(pl: dict, obra: str):
    """Waterfall P&L completo."""
    categorias = [
        "Receita","Mão de Obra","Materiais",
        "Dormidas","Diárias","Combustível","Margem"
    ]
    valores = [
        pl['receita_total'],
        -pl['custo_mao_obra'],
        -pl['custo_materiais'],
        -pl['custo_dormidas'],
        -pl['custo_diarias'],
        -pl['custo_comb'],
        0
    ]
    medidas = [
        "absolute","relative","relative",
        "relative","relative","relative","total"
    ]
    textos = [
        f"€{pl['receita_total']:,.0f}",
        f"-€{pl['custo_mao_obra']:,.0f}",
        f"-€{pl['custo_materiais']:,.0f}",
        f"-€{pl['custo_dormidas']:,.0f}",
        f"-€{pl['custo_diarias']:,.0f}",
        f"-€{pl['custo_comb']:,.0f}",
        f"€{pl['margem_bruta']:,.0f} ({pl['margem_pct']:.1f}%)"
    ]

    fig = go.Figure(go.Waterfall(
        name="P&L",
        orientation="v",
        measure=medidas,
        x=categorias,
        y=valores,
        text=textos,
        textposition="outside",
        textfont={"color":"#F1F5F9","size":9},
        connector={"line":{"color":"#334155","width":1}},
        increasing={"marker":{"color":"#10B981"}},
        decreasing={"marker":{"color":"#EF4444"}},
        totals={"marker":{
            "color":"#3B82F6" if pl['margem_bruta'] >= 0
            else "#DC2626"
        }}
    ))
    cor_margem = "#10B981" if pl['margem_pct'] >= 20 \
                 else "#F59E0B" if pl['margem_pct'] >= 10 \
                 else "#EF4444"
    fig.update_layout(
        title={'text':f'P&L — {obra[:25]}',
               'font':{'color':'#F1F5F9'}},
        height=320,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False,
        annotations=[{
            'text':f"Margem: {pl['margem_pct']:.1f}%",
            'x':0.98,'y':0.98,
            'xref':'paper','yref':'paper',
            'showarrow':False,
            'font':{'color':cor_margem,'size':14,'family':'Arial Black'},
            'align':'right'
        }]
    ))
    return fig


def _grafico_orc_vs_real(pl: dict, orc: dict, obra: str):
    """Bullet chart orçamento vs real por categoria."""
    categorias = ['Receita','Mão de Obra','Materiais',
                  'Dormidas','Diárias']
    reais = [
        pl['receita_total'],
        pl['custo_mao_obra'],
        pl['custo_materiais'],
        pl['custo_dormidas'],
        pl['custo_diarias'],
    ]
    orcados = [
        float(orc.get('Orcamento_Receita',0) or 0),
        float(orc.get('Orc_Mao_Obra',0) or 0),
        float(orc.get('Orc_Materiais',0) or 0),
        float(orc.get('Orc_Dormidas',0) or 0),
        float(orc.get('Orc_Diarias',0) or 0),
    ]

    cores_real = []
    for i, (r, o) in enumerate(zip(reais, orcados)):
        if o == 0:
            cores_real.append('#64748B')
        elif i == 0:  # receita: real >= orc é bom
            cores_real.append('#10B981' if r >= o else '#EF4444')
        else:         # custos: real <= orc é bom
            cores_real.append('#10B981' if r <= o else '#EF4444')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Orçado',
        x=orcados, y=categorias,
        orientation='h',
        marker_color='rgba(100,116,139,0.4)',
        hovertemplate='%{y}<br>Orçado: €%{x:,.0f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Real',
        x=reais, y=categorias,
        orientation='h',
        marker_color=cores_real,
        hovertemplate='%{y}<br>Real: €%{x:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':f'Orçamento vs Real — {obra[:20]}',
               'font':{'color':'#F1F5F9'}},
        barmode='overlay',
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=100,r=10)
    )
    return fig


def _grafico_radar_score(det: dict, obra: str):
    """Radar chart score por dimensão."""
    cats = list(det.keys())
    vals = [round(v[0]/v[1]*100,0) for v in det.values()]
    cats_c = cats + [cats[0]]
    vals_c = vals + [vals[0]]

    fig = go.Figure(go.Scatterpolar(
        r=vals_c, theta=cats_c,
        fill='toself',
        fillcolor='rgba(59,130,246,0.2)',
        line={'color':'#3B82F6','width':2},
        marker={'color':'#3B82F6','size':6}
    ))
    fig.update_layout(
        title={'text':f'Score — {obra[:20]}',
               'font':{'color':'#F1F5F9','size':11}},
        polar={
            'radialaxis':{
                'visible':True,'range':[0,100],
                'tickfont':{'color':'#64748B','size':8},
                'gridcolor':'#334155'
            },
            'angularaxis':{'tickfont':{'color':'#94A3B8','size':9}},
            'bgcolor':'rgba(30,41,59,0.5)'
        },
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        margin=dict(t=50,b=20,l=20,r=20),
        showlegend=False
    )
    return fig


def _grafico_scatter_obras(obras_pl: list):
    """Scatter plot lucratividade — volume vs margem."""
    if not obras_pl:
        return None

    nomes    = [p['obra'][:18] for p in obras_pl]
    volumes  = [p['receita_total'] for p in obras_pl]
    margens  = [p['margem_pct']    for p in obras_pl]
    horas    = [max(p['horas_totais'], 1) for p in obras_pl]

    fig = go.Figure(go.Scatter(
        x=volumes, y=margens,
        mode='markers+text',
        text=nomes,
        textposition='top center',
        textfont={'color':'#F1F5F9','size':9},
        marker={
            'size':[max(h/10, 12) for h in horas],
            'color':margens,
            'colorscale':[
                [0,'#EF4444'],[0.4,'#F59E0B'],[1,'#10B981']
            ],
            'showscale':True,
            'colorbar':{
                'title':{'text':'Margem %',
                         'font':{'color':'#94A3B8'}},
                'tickfont':{'color':'#94A3B8'}
            },
            'line':{'color':'#F1F5F9','width':1}
        },
        hovertemplate=(
            '<b>%{text}</b><br>'
            'Volume: €%{x:,.0f}<br>'
            'Margem: %{y:.1f}%<extra></extra>'
        )
    ))
    # Linha break-even (0% margem)
    if volumes:
        fig.add_hline(
            y=0, line_dash="dash",
            line_color="#EF4444", line_width=1,
            annotation_text="Break-even",
            annotation_font_color="#EF4444"
        )
    # Linha 20% margem objetivo
    fig.add_hline(
        y=20, line_dash="dot",
        line_color="#10B981", line_width=1,
        annotation_text="Objetivo 20%",
        annotation_font_color="#10B981"
    )

    fig.update_layout(
        title={'text':'Lucratividade por Obra '
                      '(tamanho = horas)',
               'font':{'color':'#F1F5F9'}},
        height=340,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={
            'gridcolor':'#334155',
            'tickfont':{'color':'#94A3B8'},
            'title':{'text':'Receita (€)',
                     'font':{'color':'#94A3B8'}},
            'tickprefix':'€'
        },
        yaxis={
            'gridcolor':'#334155',
            'tickfont':{'color':'#94A3B8'},
            'title':{'text':'Margem (%)',
                     'font':{'color':'#94A3B8'}},
            'ticksuffix':'%'
        },
        margin=dict(t=40,b=40,l=60,r=10)
    )
    return fig


def _grafico_timeline_financeira(faturas_cli, diarias_pag_db,
                                  obra: str):
    """Timeline financeira da obra."""
    eventos = []

    # Faturas emitidas
    if not faturas_cli.empty and 'Obra' in faturas_cli.columns:
        fc = faturas_cli[faturas_cli['Obra'] == obra].copy()
        fc['Data_d'] = pd.to_datetime(
            fc.get('Data_Emissao',''), dayfirst=True, errors='coerce'
        )
        for _, row in fc.iterrows():
            if pd.notna(row['Data_d']):
                tot = float(row.get('Total',0) or 0)
                est = row.get('Estado','')
                cor = {'Paga':'#10B981','Enviada':'#3B82F6',
                       'Emitida':'#8B5CF6'}.get(est,'#64748B')
                eventos.append({
                    'data':  row['Data_d'],
                    'tipo':  f"🧾 {row.get('Numero','')}",
                    'valor': tot,
                    'cor':   cor,
                    'desc':  f"{est} — €{tot:,.2f}"
                })

    # Pagamentos de diárias
    if not diarias_pag_db.empty:
        if 'Obras' in diarias_pag_db.columns and \
           'Data_Pagamento' in diarias_pag_db.columns:
            dp = diarias_pag_db[
                diarias_pag_db['Obras'].str.contains(obra, na=False)
            ].copy()
            dp['Data_d'] = pd.to_datetime(
                dp['Data_Pagamento'], dayfirst=True, errors='coerce'
            )
            for _, row in dp.iterrows():
                if pd.notna(row['Data_d']):
                    val = float(row.get('Valor_Total',0) or 0)
                    eventos.append({
                        'data':  row['Data_d'],
                        'tipo':  '💶 Diárias',
                        'valor': -val,
                        'cor':   '#F59E0B',
                        'desc':  f"Pagamento diárias — €{val:,.2f}"
                    })

    if not eventos:
        return None

    eventos.sort(key=lambda x: x['data'])

    fig = go.Figure()
    for ev in eventos:
        cor = ev['cor']
        fig.add_trace(go.Scatter(
            x=[ev['data']],
            y=[ev['valor']],
            mode='markers+text',
            text=[ev['tipo']],
            textposition='top center',
            textfont={'color':'#F1F5F9','size':9},
            marker={
                'size':14,'color':cor,
                'line':{'color':'#F1F5F9','width':1}
            },
            hovertemplate=(
                f"<b>{ev['tipo']}</b><br>"
                f"{ev['desc']}<br>"
                f"{ev['data'].strftime('%d/%m/%Y')}"
                f"<extra></extra>"
            ),
            showlegend=False
        ))

    # Linha do zero
    fig.add_hline(
        y=0, line_dash="dash",
        line_color="#334155", line_width=1
    )
    # Linha hoje
    fig.add_vline(
        x=datetime.now(),
        line_dash="dash",
        line_color="#64748B", line_width=1,
        annotation_text="Hoje",
        annotation_font_color="#94A3B8"
    )

    fig.update_layout(
        title={'text':f'Timeline Financeira — {obra[:25]}',
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
        margin=dict(t=40,b=20,l=60,r=10)
    )
    return fig


def _grafico_evolucao_margem(obras_pl: list):
    """Bar chart margem por obra — ranking."""
    if not obras_pl:
        return None

    obras_s = sorted(obras_pl, key=lambda x: x['margem_pct'],
                     reverse=True)
    nomes   = [p['obra'][:20]    for p in obras_s]
    margens = [p['margem_pct']   for p in obras_s]
    cores   = ['#10B981' if m >= 20
               else '#F59E0B' if m >= 10
               else '#EF4444'
               for m in margens]

    fig = go.Figure(go.Bar(
        x=nomes, y=margens,
        marker_color=cores,
        text=[f"{m:.1f}%" for m in margens],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':10},
        hovertemplate='%{x}<br>Margem: %{y:.1f}%<extra></extra>'
    ))
    fig.add_hline(
        y=20, line_dash="dot",
        line_color="#10B981", line_width=2,
        annotation_text="Objetivo 20%",
        annotation_font_color="#10B981"
    )
    fig.update_layout(
        title={'text':'Ranking de Margem por Obra',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'ticksuffix':'%'},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF P&L POR OBRA
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_pl(pl: dict, orc: dict,
                  score: int, obra: str,
                  empresa: dict) -> bytes:
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    bold_s = ParagraphStyle(
        'bold', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold', spaceAfter=4
    )
    sub_s = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#64748B'),
        spaceAfter=2
    )
    normal_s = ParagraphStyle(
        'normal', parent=styles['Normal'],
        fontSize=9, spaceAfter=2
    )

    # Header
    cor_score = (
        '#10B981' if score >= 70 else
        '#F59E0B' if score >= 40 else
        '#EF4444'
    )
    story.append(Paragraph(
        f"RELATÓRIO P&L — {obra.upper()}",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=16, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'),
                       spaceAfter=4)
    ))
    story.append(Paragraph(
        f"{empresa.get('nome','')} | "
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_s
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    # Score
    story.append(Paragraph(
        f"Score de Obra: {score}/100",
        ParagraphStyle('score', parent=styles['Normal'],
                       fontSize=14, fontName='Helvetica-Bold',
                       textColor=colors.HexColor(cor_score),
                       spaceAfter=6)
    ))
    story.append(Spacer(1, 0.2*cm))

    # P&L
    story.append(Paragraph("<b>DEMONSTRAÇÃO DE RESULTADOS</b>",
                            bold_s))
    pl_data = [
        ["RECEITAS","",""],
        ["Faturação emitida",
         f"€{pl['receita_faturas']:,.2f}",""],
        ["Estimativa horas (não faturado)",
         f"€{pl['receita_horas']:,.2f}",""],
        ["TOTAL RECEITA","",
         f"€{pl['receita_total']:,.2f}"],
        ["","",""],
        ["CUSTOS DIRETOS","",""],
        ["Mão de Obra",
         f"€{pl['custo_mao_obra']:,.2f}",
         f"{pl['custo_mao_obra']/pl['receita_total']*100:.1f}%"
         if pl['receita_total'] > 0 else "—"],
        ["Materiais/Compras",
         f"€{pl['custo_materiais']:,.2f}",
         f"{pl['custo_materiais']/pl['receita_total']*100:.1f}%"
         if pl['receita_total'] > 0 else "—"],
        ["Dormidas",
         f"€{pl['custo_dormidas']:,.2f}",
         f"{pl['custo_dormidas']/pl['receita_total']*100:.1f}%"
         if pl['receita_total'] > 0 else "—"],
        ["Diárias",
         f"€{pl['custo_diarias']:,.2f}",
         f"{pl['custo_diarias']/pl['receita_total']*100:.1f}%"
         if pl['receita_total'] > 0 else "—"],
        ["Combustível",
         f"€{pl['custo_comb']:,.2f}",
         f"{pl['custo_comb']/pl['receita_total']*100:.1f}%"
         if pl['receita_total'] > 0 else "—"],
        ["TOTAL CUSTOS","",
         f"€{pl['custo_total']:,.2f}"],
        ["","",""],
        ["MARGEM BRUTA","",
         f"€{pl['margem_bruta']:,.2f} ({pl['margem_pct']:.1f}%)"],
    ]

    t = Table(pl_data, colWidths=[9*cm, 3.5*cm, 4.5*cm])
    t.setStyle(TableStyle([
        ('FONTSIZE',     (0,0),(-1,-1), 9),
        ('FONTNAME',     (0,0),(0,0),  'Helvetica-Bold'),
        ('FONTNAME',     (0,5),(0,5),  'Helvetica-Bold'),
        ('FONTNAME',     (0,3),(-1,3), 'Helvetica-Bold'),
        ('FONTNAME',     (0,11),(-1,11),'Helvetica-Bold'),
        ('FONTNAME',     (0,13),(-1,13),'Helvetica-Bold'),
        ('BACKGROUND',   (0,0),(-1,0), colors.HexColor('#EFF6FF')),
        ('BACKGROUND',   (0,5),(-1,5), colors.HexColor('#FFF7ED')),
        ('BACKGROUND',   (0,13),(-1,13),
         colors.HexColor('#10B981') if pl['margem_pct'] >= 20
         else colors.HexColor('#F59E0B') if pl['margem_pct'] >= 10
         else colors.HexColor('#EF4444')),
        ('TEXTCOLOR',    (0,13),(-1,13), colors.white),
        ('LINEBELOW',    (0,3),(-1,3), 1, colors.HexColor('#3B82F6')),
        ('LINEBELOW',    (0,11),(-1,11),1, colors.HexColor('#E2E8F0')),
        ('GRID',         (0,0),(-1,-1), 0.2, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',   (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING',  (0,0),(-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    # Orçamento vs Real
    if any(float(orc.get(k,0) or 0) > 0
           for k in ['Orcamento_Receita','Orcamento_Custos']):
        story.append(Paragraph("<b>ORÇAMENTO VS REAL</b>", bold_s))
        orc_rec_v  = float(orc.get('Orcamento_Receita',0) or 0)
        orc_cust_v = float(orc.get('Orcamento_Custos',0) or 0)
        desvio_r   = round(pl['receita_total'] - orc_rec_v, 2)
        desvio_c   = round(pl['custo_total']   - orc_cust_v, 2)

        orc_data = [
            ["","Orçado","Real","Desvio"],
            ["Receita",
             f"€{orc_rec_v:,.2f}",
             f"€{pl['receita_total']:,.2f}",
             f"{'+'if desvio_r>=0 else ''}€{desvio_r:,.2f}"],
            ["Custos",
             f"€{orc_cust_v:,.2f}",
             f"€{pl['custo_total']:,.2f}",
             f"{'+'if desvio_c>=0 else ''}€{desvio_c:,.2f}"],
        ]
        ot = Table(orc_data, colWidths=[4*cm,4*cm,4*cm,5*cm])
        ot.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR',  (0,0),(-1,0), colors.white),
            ('FONTNAME',   (0,0),(-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0),(-1,-1), 9),
            ('GRID',       (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0),(-1,-1), 5),
            ('BOTTOMPADDING',(0,0),(-1,-1), 5),
            ('LEFTPADDING',(0,0),(-1,-1), 6),
        ]))
        story.append(ot)

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        f"GESTNOW v3.0 | {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_obras(obras_db, registos_db,
                     faturas_db, diarias_pag_db, *_):
    """Módulo Performance por Obra."""

    # ── Carregar dados ────────────────────────────────────────────
    faturas_cli  = _load("faturas_clientes.csv", [
        "ID","Numero","Data_Emissao","Data_Vencimento",
        "Cliente","Obra","Total","Estado"
    ])
    compras_db   = _load("compras.csv", ["Obra","Total","Status"])
    dormidas_db  = _load("dormidas.csv", ["Obra","Total"])
    comb_db      = _load("frota_combustivel.csv",
                         ["Matricula","Data","Litros","Valor","KM"])
    rh_db        = _load("colaboradores_rh.csv",
                         ["Nome","Salario_Base"])
    inst_ac      = _load("inst_acessos.csv",
                         ["Obra","Utilizador","PrecoHora","Ativo"])
    orc_db       = _load("obras_orcamento.csv", [
        "ID","Obra","Orcamento_Receita","Orcamento_Custos",
        "Orc_Mao_Obra","Orc_Materiais","Orc_Dormidas",
        "Orc_Diarias","WIP","Data_Criacao"
    ])
    wip_db       = _load("obras_wip.csv", [
        "ID","Obra","Descricao","Valor_Est",
        "Data_Registo","Estado"
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

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .obra-card {
        background:#1E293B; border-radius:12px;
        padding:16px; margin-bottom:10px;
        border-left:5px solid #3B82F6;
        transition:transform 0.15s;
    }
    .obra-card:hover { transform:translateX(3px); }
    .pl-linha {
        display:flex; justify-content:space-between;
        padding:5px 0; border-bottom:1px solid #1E293B;
    }
    .score-ring {
        width:70px; height:70px; border-radius:50%;
        display:flex; align-items:center;
        justify-content:center;
        font-size:1.3rem; font-weight:900;
        border:4px solid;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Obras ativas ──────────────────────────────────────────────
    if obras_db.empty:
        st.info("📋 Sem obras para analisar.")
        return

    obras_ativas = obras_db[
        obras_db['Ativa'] == 'Ativa'
    ]['Obra'].tolist() if not obras_db.empty else []

    if not obras_ativas:
        st.info("📋 Sem obras ativas.")
        return

    # Pré-calcular P&L de todas as obras
    todas_pl = []
    for ob in obras_ativas:
        orc_row = {}
        if not orc_db.empty and 'Obra' in orc_db.columns:
            r = orc_db[orc_db['Obra'] == ob]
            if not r.empty:
                orc_row = r.iloc[0].to_dict()
        pl = _calcular_pl_obra(
            ob, registos_db, faturas_cli,
            compras_db, dormidas_db, comb_db,
            diarias_pag_db, rh_db, inst_ac
        )
        score, det = _calcular_score_pl(pl, orc_row)
        todas_pl.append({**pl, 'score':score, 'det':det})

    # ── KPIs globais ──────────────────────────────────────────────
    rec_total  = sum(p['receita_total']  for p in todas_pl)
    cust_total = sum(p['custo_total']    for p in todas_pl)
    marg_total = round(rec_total - cust_total, 2)
    marg_pct_g = round(marg_total/rec_total*100,1) \
                 if rec_total > 0 else 0.0
    score_med  = round(sum(p['score'] for p in todas_pl) /
                       len(todas_pl), 0) if todas_pl else 0

    cor_marg = "#10B981" if marg_pct_g >= 20 \
               else "#F59E0B" if marg_pct_g >= 10 \
               else "#EF4444"

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("🏭 Obras Ativas",   len(obras_ativas))
    with c2: st.metric("💰 Receita Total",  f"€{rec_total:,.2f}")
    with c3: st.metric("💸 Custo Total",    f"€{cust_total:,.2f}")
    with c4: st.metric("📈 Margem Global",  f"{marg_pct_g:.1f}%")
    with c5: st.metric("⭐ Score Médio",    f"{score_med:.0f}/100")

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_visao, t_pl, t_orc,
     t_wip, t_timeline, t_scatter) = st.tabs([
        "📊 Visão Geral",
        "💰 P&L por Obra",
        "📋 Orçamento vs Real",
        "🔄 WIP",
        "📅 Timeline",
        "🎯 Lucratividade",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — VISÃO GERAL (scorecard)
    # ════════════════════════════════════════════════════════════════
    with t_visao:
        st.markdown("### 📊 Scorecard de Obras")

        # Gráficos globais
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_rank = _grafico_evolucao_margem(todas_pl)
            if fig_rank:
                st.plotly_chart(
                    fig_rank, use_container_width=True
                )
        with col_g2:
            fig_sc_all = _grafico_scatter_obras(todas_pl)
            if fig_sc_all:
                st.plotly_chart(
                    fig_sc_all, use_container_width=True
                )

        st.markdown("---")

        # Cards de obra com score
        for pl_data in sorted(
            todas_pl, key=lambda x: x['score'], reverse=True
        ):
            obra    = pl_data['obra']
            score_o = pl_data['score']
            det_o   = pl_data['det']
            cor_o, ic_o = _rag(score_o)

            col_card, col_rad = st.columns([3, 1])
            with col_card:
                # P&L resumido
                m_pct = pl_data['margem_pct']
                cor_m = "#10B981" if m_pct>=20 \
                        else "#F59E0B" if m_pct>=10 \
                        else "#EF4444"

                st.markdown(
                    f"<div class='obra-card' "
                    f"style='border-left-color:{cor_o};'>"
                    f"<div style='display:flex;"
                    f"justify-content:space-between;"
                    f"align-items:center;'>"
                    f"<div>"
                    f"<b style='color:#F1F5F9;"
                    f"font-size:1.05rem;'>{obra}</b><br>"
                    f"<small style='color:#64748B;'>"
                    f"Receita: €{pl_data['receita_total']:,.2f} · "
                    f"Custo: €{pl_data['custo_total']:,.2f} · "
                    f"Horas: {fh(pl_data['horas_totais'])}"
                    f"</small>"
                    f"</div>"
                    f"<div style='text-align:right;"
                    f"display:flex;align-items:center;gap:16px;'>"
                    f"<div>"
                    f"<b style='color:{cor_m};"
                    f"font-size:1.4rem;'>{m_pct:.1f}%</b><br>"
                    f"<small style='color:#64748B;'>margem</small>"
                    f"</div>"
                    f"<div style='width:60px;height:60px;"
                    f"border-radius:50%;display:flex;"
                    f"align-items:center;justify-content:center;"
                    f"border:4px solid {cor_o};"
                    f"background:{cor_o}22;'>"
                    f"<b style='color:{cor_o};"
                    f"font-size:1.1rem;'>{score_o}</b>"
                    f"</div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

                # Barras de progresso por dimensão
                st.markdown(
                    "<div style='margin-top:10px;"
                    "display:grid;"
                    "grid-template-columns:repeat(3,1fr);"
                    "gap:6px;'>",
                    unsafe_allow_html=True
                )
                for dim, (pts, max_pts) in det_o.items():
                    pct_d = pts/max_pts*100
                    cor_d = "#10B981" if pct_d>=70 \
                            else "#F59E0B" if pct_d>=40 \
                            else "#EF4444"
                    st.markdown(
                        f"<div>"
                        f"<small style='color:#64748B;"
                        f"font-size:0.7rem;'>{dim}</small>"
                        f"<div style='background:#0F172A;"
                        f"border-radius:3px;height:5px;"
                        f"margin-top:2px;'>"
                        f"<div style='background:{cor_d};"
                        f"width:{pct_d:.0f}%;height:5px;"
                        f"border-radius:3px;'></div>"
                        f"</div>"
                        f"<small style='color:{cor_d};"
                        f"font-size:0.68rem;'>"
                        f"{pts}/{max_pts}</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                st.markdown("</div></div>",
                            unsafe_allow_html=True)

            with col_rad:
                if st.button(
                    "📊 Radar",
                    key=f"radar_ob_{obra}",
                    use_container_width=True
                ):
                    st.session_state['radar_pl_obra'] = obra

        # Radar popup
        if st.session_state.get('radar_pl_obra'):
            obra_r = st.session_state['radar_pl_obra']
            pl_r   = next(
                (p for p in todas_pl if p['obra'] == obra_r),
                None
            )
            if pl_r:
                st.markdown("---")
                col_rar1, col_rar2 = st.columns([1, 2])
                with col_rar1:
                    st.plotly_chart(
                        _grafico_radar_score(pl_r['det'], obra_r),
                        use_container_width=True
                    )
                with col_rar2:
                    st.markdown(
                        f"### 📋 Análise Detalhada — {obra_r}"
                    )
                    for dim, (pts, max_pts) in pl_r['det'].items():
                        pct = pts/max_pts*100
                        cor = "#10B981" if pct>=70 \
                              else "#F59E0B" if pct>=40 \
                              else "#EF4444"
                        st.markdown(
                            f"<div style='margin-bottom:10px;'>"
                            f"<div style='display:flex;"
                            f"justify-content:space-between;"
                            f"margin-bottom:3px;'>"
                            f"<span style='color:#94A3B8;'>"
                            f"{dim}</span>"
                            f"<span style='color:{cor};"
                            f"font-weight:700;'>"
                            f"{pts}/{max_pts} "
                            f"({pct:.0f}%)</span></div>"
                            f"<div style='background:#0F172A;"
                            f"border-radius:4px;height:8px;'>"
                            f"<div style='background:{cor};"
                            f"width:{pct:.0f}%;height:8px;"
                            f"border-radius:4px;'></div>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
                    if st.button(
                        "✖ Fechar",
                        key="fechar_radar_pl"
                    ):
                        st.session_state.pop(
                            'radar_pl_obra', None
                        )
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — P&L POR OBRA
    # ════════════════════════════════════════════════════════════════
    with t_pl:
        st.markdown("### 💰 P&L Detalhado por Obra")

        obra_pl = st.selectbox(
            "Selecionar Obra",
            obras_ativas,
            key="pl_obra_sel"
        )

        pl_sel = next(
            (p for p in todas_pl if p['obra'] == obra_pl),
            None
        )
        orc_sel = {}
        if not orc_db.empty and 'Obra' in orc_db.columns:
            r = orc_db[orc_db['Obra'] == obra_pl]
            if not r.empty:
                orc_sel = r.iloc[0].to_dict()

        if pl_sel:
            score_sel, det_sel = pl_sel['score'], pl_sel['det']
            cor_sel, ic_sel    = _rag(score_sel)

            # KPIs P&L
            c1,c2,c3,c4 = st.columns(4)
            with c1:
                st.metric(
                    "💰 Receita",
                    f"€{pl_sel['receita_total']:,.2f}"
                )
            with c2:
                st.metric(
                    "💸 Custo Total",
                    f"€{pl_sel['custo_total']:,.2f}"
                )
            with c3:
                m_pct = pl_sel['margem_pct']
                cor_m = "normal" if m_pct >= 20 else "inverse"
                st.metric(
                    "📈 Margem",
                    f"{m_pct:.1f}%",
                    delta=f"€{pl_sel['margem_bruta']:,.2f}"
                )
            with c4:
                st.metric(
                    "⭐ Score",
                    f"{score_sel}/100",
                    delta=ic_sel
                )

            # Waterfall P&L
            col_wf, col_rd = st.columns([2, 1])
            with col_wf:
                st.plotly_chart(
                    _grafico_pl_waterfall(pl_sel, obra_pl),
                    use_container_width=True
                )
            with col_rd:
                st.plotly_chart(
                    _grafico_radar_score(det_sel, obra_pl),
                    use_container_width=True
                )

            # Detalhe linhas P&L
            st.markdown("#### 📋 Detalhe P&L")

            # RECEITA
            st.markdown(
                "<p style='color:#10B981;font-weight:700;"
                "font-size:0.85rem;margin:8px 0 4px;'>"
                "▶ RECEITA</p>",
                unsafe_allow_html=True
            )
            rec_items = [
                ("Faturação emitida (faturas)",
                 pl_sel['receita_faturas']),
                ("Estimativa horas não faturadas",
                 pl_sel['receita_horas']),
            ]
            for label, val in rec_items:
                pct = val/pl_sel['receita_total']*100 \
                      if pl_sel['receita_total'] > 0 else 0
                st.markdown(
                    f"<div class='pl-linha'>"
                    f"<span style='color:#94A3B8;"
                    f"font-size:0.85rem;'>{label}</span>"
                    f"<span style='color:#10B981;"
                    f"font-weight:700;'>"
                    f"€{val:,.2f} "
                    f"<small style='color:#64748B;'>"
                    f"({pct:.1f}%)</small></span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            st.markdown(
                f"<div style='display:flex;"
                f"justify-content:space-between;"
                f"padding:8px 0;border-top:"
                f"2px solid #10B981;margin:4px 0 12px;'>"
                f"<b style='color:#F1F5F9;'>TOTAL RECEITA</b>"
                f"<b style='color:#10B981;"
                f"font-size:1.05rem;'>"
                f"€{pl_sel['receita_total']:,.2f}</b>"
                f"</div>",
                unsafe_allow_html=True
            )

            # CUSTOS
            st.markdown(
                "<p style='color:#EF4444;font-weight:700;"
                "font-size:0.85rem;margin:8px 0 4px;'>"
                "▶ CUSTOS DIRETOS</p>",
                unsafe_allow_html=True
            )
            cust_items = [
                ("Mão de Obra",    pl_sel['custo_mao_obra']),
                ("Materiais",      pl_sel['custo_materiais']),
                ("Dormidas",       pl_sel['custo_dormidas']),
                ("Diárias",        pl_sel['custo_diarias']),
                ("Combustível",    pl_sel['custo_comb']),
            ]
            for label, val in cust_items:
                pct = val/pl_sel['receita_total']*100 \
                      if pl_sel['receita_total'] > 0 else 0
                cor_c = "#EF4444" if pct > 30 \
                        else "#F59E0B" if pct > 20 \
                        else "#94A3B8"
                st.markdown(
                    f"<div class='pl-linha'>"
                    f"<span style='color:#94A3B8;"
                    f"font-size:0.85rem;'>{label}</span>"
                    f"<span style='color:{cor_c};"
                    f"font-weight:700;'>"
                    f"€{val:,.2f} "
                    f"<small style='color:#64748B;'>"
                    f"({pct:.1f}%)</small></span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            cor_marg = "#10B981" if pl_sel['margem_pct'] >= 20 \
                       else "#F59E0B" if pl_sel['margem_pct'] >= 10 \
                       else "#EF4444"

            st.markdown(
                f"<div style='display:flex;"
                f"justify-content:space-between;"
                f"padding:10px;border-radius:10px;"
                f"background:{cor_marg}22;"
                f"border:2px solid {cor_marg};"
                f"margin-top:12px;'>"
                f"<b style='color:#F1F5F9;"
                f"font-size:1.05rem;'>MARGEM BRUTA</b>"
                f"<b style='color:{cor_marg};"
                f"font-size:1.2rem;'>"
                f"€{pl_sel['margem_bruta']:,.2f} "
                f"({pl_sel['margem_pct']:.1f}%)</b>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Download PDF
            st.markdown("---")
            col_pdf1, col_pdf2 = st.columns(2)
            with col_pdf1:
                if st.button(
                    "📄 Gerar Relatório P&L PDF",
                    key="btn_pl_pdf",
                    type="primary",
                    use_container_width=True
                ):
                    with st.spinner("A gerar..."):
                        pdf_pl = _gerar_pdf_pl(
                            pl_sel, orc_sel,
                            score_sel, obra_pl, empresa
                        )
                    st.session_state['pl_pdf_bytes'] = pdf_pl
                    st.session_state['pl_pdf_nome']  = (
                        f"pl_{obra_pl.replace(' ','_')}_"
                        f"{date.today().strftime('%Y%m%d')}.pdf"
                    )
                    st.rerun()

            with col_pdf2:
                if st.session_state.get('pl_pdf_bytes'):
                    st.download_button(
                        "📥 Descarregar PDF",
                        data=st.session_state['pl_pdf_bytes'],
                        file_name=st.session_state.get(
                            'pl_pdf_nome','pl.pdf'
                        ),
                        mime="application/pdf",
                        key="dl_pl_pdf",
                        use_container_width=True,
                        type="primary"
                    )

    # ════════════════════════════════════════════════════════════════
    # TAB — ORÇAMENTO vs REAL
    # ════════════════════════════════════════════════════════════════
    with t_orc:
        st.markdown("### 📋 Orçamento vs Real")

        obra_orc = st.selectbox(
            "Obra", obras_ativas, key="orc_obra_sel"
        )
        pl_orc = next(
            (p for p in todas_pl if p['obra'] == obra_orc),
            None
        )
        orc_row = {}
        if not orc_db.empty and 'Obra' in orc_db.columns:
            r = orc_db[orc_db['Obra'] == obra_orc]
            if not r.empty:
                orc_row = r.iloc[0].to_dict()

        col_of, col_og = st.columns([1, 2])

        with col_of:
            st.markdown("#### ✏️ Definir Orçamento")
            with st.form("form_orcamento"):
                orc_rec = st.number_input(
                    "Receita Orçamentada (€)",
                    min_value=0.0,
                    value=float(orc_row.get('Orcamento_Receita',0) or 0),
                    step=1000.0, key="orc_rec"
                )
                orc_cust = st.number_input(
                    "Custo Total Orçamentado (€)",
                    min_value=0.0,
                    value=float(orc_row.get('Orcamento_Custos',0) or 0),
                    step=500.0, key="orc_cust"
                )
                st.markdown(
                    "<p style='color:#64748B;font-size:0.75rem;"
                    "margin:4px 0;'>Por categoria:</p>",
                    unsafe_allow_html=True
                )
                orc_mo = st.number_input(
                    "Mão de Obra (€)",
                    min_value=0.0,
                    value=float(orc_row.get('Orc_Mao_Obra',0) or 0),
                    step=500.0, key="orc_mo"
                )
                orc_mat = st.number_input(
                    "Materiais (€)",
                    min_value=0.0,
                    value=float(orc_row.get('Orc_Materiais',0) or 0),
                    step=200.0, key="orc_mat"
                )
                orc_dorm = st.number_input(
                    "Dormidas (€)",
                    min_value=0.0,
                    value=float(orc_row.get('Orc_Dormidas',0) or 0),
                    step=100.0, key="orc_dorm"
                )
                orc_diar = st.number_input(
                    "Diárias (€)",
                    min_value=0.0,
                    value=float(orc_row.get('Orc_Diarias',0) or 0),
                    step=100.0, key="orc_diar"
                )

                if st.form_submit_button(
                    "💾 Guardar Orçamento",
                    use_container_width=True, type="primary"
                ):
                    novo_orc = {
                        "ID":                orc_row.get(
                            'ID',
                            str(uuid.uuid4())[:8].upper()
                        ),
                        "Obra":              obra_orc,
                        "Orcamento_Receita": orc_rec,
                        "Orcamento_Custos":  orc_cust,
                        "Orc_Mao_Obra":      orc_mo,
                        "Orc_Materiais":     orc_mat,
                        "Orc_Dormidas":      orc_dorm,
                        "Orc_Diarias":       orc_diar,
                        "WIP":               0,
                        "Data_Criacao":      datetime.now().strftime(
                            "%d/%m/%Y"
                        )
                    }
                    if not orc_db.empty and \
                       'Obra' in orc_db.columns and \
                       obra_orc in orc_db['Obra'].values:
                        for k, v in novo_orc.items():
                            orc_db.loc[
                                orc_db['Obra'] == obra_orc, k
                            ] = v
                        save_db(orc_db, "obras_orcamento.csv")
                    else:
                        novo_df = pd.DataFrame([novo_orc])
                        upd = pd.concat(
                            [orc_db, novo_df], ignore_index=True
                        ) if not orc_db.empty else novo_df
                        save_db(upd, "obras_orcamento.csv")
                    inv()
                    st.success("✅ Orçamento guardado!")
                    st.rerun()

        with col_og:
            if pl_orc:
                st.plotly_chart(
                    _grafico_orc_vs_real(pl_orc, orc_row, obra_orc),
                    use_container_width=True
                )

                # Tabela desvios
                st.markdown("#### 📊 Análise de Desvios")
                desvios = []
                pares = [
                    ("Receita",
                     pl_orc['receita_total'],
                     float(orc_row.get('Orcamento_Receita',0) or 0),
                     True),
                    ("Mão de Obra",
                     pl_orc['custo_mao_obra'],
                     float(orc_row.get('Orc_Mao_Obra',0) or 0),
                     False),
                    ("Materiais",
                     pl_orc['custo_materiais'],
                     float(orc_row.get('Orc_Materiais',0) or 0),
                     False),
                    ("Dormidas",
                     pl_orc['custo_dormidas'],
                     float(orc_row.get('Orc_Dormidas',0) or 0),
                     False),
                    ("Diárias",
                     pl_orc['custo_diarias'],
                     float(orc_row.get('Orc_Diarias',0) or 0),
                     False),
                ]
                for label, real, orc_v, maior_e_melhor in pares:
                    if orc_v == 0:
                        status = "—"
                        desvio_pct = 0
                    else:
                        desvio_pct = round(
                            (real - orc_v) / orc_v * 100, 1
                        )
                        if maior_e_melhor:
                            status = "🟢" if real >= orc_v else "🔴"
                        else:
                            status = "🟢" if real <= orc_v else "🔴"

                    desvios.append({
                        "Categoria": label,
                        "Orçado":    f"€{orc_v:,.2f}",
                        "Real":      f"€{real:,.2f}",
                        "Desvio %":  f"{desvio_pct:+.1f}%" \
                                     if orc_v > 0 else "—",
                        "Status":    status
                    })

                st.dataframe(
                    pd.DataFrame(desvios),
                    use_container_width=True, hide_index=True
                )

                # Alerta se desvio > 15%
                for d in desvios:
                    try:
                        dp = float(
                            d['Desvio %'].replace('%','').replace('+','')
                        )
                        if abs(dp) > 15 and d['Status'] == "🔴":
                            st.error(
                                f"⚠️ {d['Categoria']}: "
                                f"desvio de {d['Desvio %']} "
                                f"— ação corretiva recomendada!"
                            )
                    except:
                        pass

    # ════════════════════════════════════════════════════════════════
    # TAB — WIP (Trabalhos em Curso)
    # ════════════════════════════════════════════════════════════════
    with t_wip:
        st.markdown("### 🔄 Trabalhos em Curso (WIP)")
        st.info(
            "WIP — Work In Progress. "
            "Trabalho executado mas ainda não faturado ao cliente. "
            "Representa receita potencial imediata."
        )

        col_wf1, col_wf2 = st.columns([1, 2])

        with col_wf1:
            st.markdown("#### ➕ Registar WIP")
            with st.form("form_wip"):
                wip_obra = st.selectbox(
                    "Obra *", obras_ativas, key="wip_obra"
                )
                wip_desc = st.text_area(
                    "Descrição *", key="wip_desc",
                    placeholder="Ex: Instalação de 23 instrumentos "
                                "na área de produção..."
                )
                wip_val = st.number_input(
                    "Valor Estimado (€) *",
                    min_value=0.0, step=500.0, key="wip_val"
                )
                wip_est = st.selectbox(
                    "Estado",
                    ["Em Curso","Pronto para Faturar",
                     "Faturado","Cancelado"],
                    key="wip_est"
                )

                if st.form_submit_button(
                    "💾 Registar WIP",
                    use_container_width=True, type="primary"
                ):
                    if not wip_desc.strip() or wip_val <= 0:
                        st.error("❌ Descrição e valor obrigatórios.")
                    else:
                        novo_wip = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Obra":         wip_obra,
                            "Descricao":    wip_desc.strip(),
                            "Valor_Est":    wip_val,
                            "Data_Registo": date.today().strftime(
                                "%d/%m/%Y"
                            ),
                            "Estado":       wip_est
                        }])
                        upd_wip = pd.concat(
                            [wip_db, novo_wip], ignore_index=True
                        ) if not wip_db.empty else novo_wip
                        save_db(upd_wip, "obras_wip.csv")
                        inv()
                        st.success(
                            f"✅ WIP registado! €{wip_val:,.2f}"
                        )
                        st.rerun()

        with col_wf2:
            st.markdown("#### 📋 WIP por Obra")

            if wip_db.empty:
                st.info("📋 Sem trabalhos em curso registados.")
            else:
                # KPIs WIP
                wip_ativo = wip_db[
                    wip_db.get('Estado','') != 'Faturado'
                ] if 'Estado' in wip_db.columns else wip_db

                total_wip = pd.to_numeric(
                    wip_ativo.get('Valor_Est',0), errors='coerce'
                ).fillna(0).sum()
                pronto_fat = pd.to_numeric(
                    wip_db[
                        wip_db.get('Estado','') ==
                        'Pronto para Faturar'
                    ].get('Valor_Est',0),
                    errors='coerce'
                ).fillna(0).sum() \
                if 'Estado' in wip_db.columns else 0.0

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("🔄 WIP Total", f"€{total_wip:,.2f}")
                with c2:
                    st.metric(
                        "✅ Pronto a Faturar",
                        f"€{pronto_fat:,.2f}"
                    )

                # Filtro por obra
                obras_wip_f = ["Todas"] + \
                              wip_db['Obra'].unique().tolist() \
                              if 'Obra' in wip_db.columns else ["Todas"]
                obra_wip_f  = st.selectbox(
                    "Filtrar", obras_wip_f, key="wip_filt"
                )
                df_wip_show = wip_db.copy()
                if obra_wip_f != "Todas":
                    df_wip_show = df_wip_show[
                        df_wip_show['Obra'] == obra_wip_f
                    ]

                cor_est_wip = {
                    'Em Curso':            '#3B82F6',
                    'Pronto para Faturar': '#10B981',
                    'Faturado':            '#64748B',
                    'Cancelado':           '#EF4444',
                }

                for _, wip_row in df_wip_show.iterrows():
                    wid     = wip_row.get('ID','')
                    est_wip = wip_row.get('Estado','')
                    cor_w   = cor_est_wip.get(est_wip,'#6B7280')
                    val_w   = float(wip_row.get('Valor_Est',0) or 0)

                    col_wi, col_wa = st.columns([5, 1])
                    with col_wi:
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:10px;padding:12px;"
                            f"margin-bottom:6px;"
                            f"border-left:4px solid {cor_w};'>"
                            f"<div style='display:flex;"
                            f"justify-content:space-between;'>"
                            f"<div>"
                            f"<b style='color:#F1F5F9;"
                            f"font-size:0.88rem;'>"
                            f"{wip_row.get('Obra','')}</b><br>"
                            f"<small style='color:#94A3B8;'>"
                            f"{wip_row.get('Descricao','')[:60]}"
                            f"</small><br>"
                            f"<small style='color:#64748B;'>"
                            f"{wip_row.get('Data_Registo','')}"
                            f"</small>"
                            f"</div>"
                            f"<div style='text-align:right;'>"
                            f"<b style='color:#F1F5F9;"
                            f"font-size:1rem;'>"
                            f"€{val_w:,.2f}</b><br>"
                            f"<span style='background:{cor_w}22;"
                            f"color:{cor_w};padding:2px 8px;"
                            f"border-radius:10px;font-size:0.7rem;"
                            f"font-weight:700;'>"
                            f"{est_wip}</span>"
                            f"</div></div></div>",
                            unsafe_allow_html=True
                        )
                    with col_wa:
                        novo_est_wip = st.selectbox(
                            "Est.",
                            ['Em Curso','Pronto para Faturar',
                             'Faturado','Cancelado'],
                            key=f"wip_est_{wid}",
                            label_visibility="collapsed"
                        )
                        if st.button(
                            "✅", key=f"wip_upd_{wid}",
                            use_container_width=True
                        ):
                            wip_db.loc[
                                wip_db['ID'] == wid, 'Estado'
                            ] = novo_est_wip
                            save_db(wip_db, "obras_wip.csv")
                            inv(); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — TIMELINE FINANCEIRA
    # ════════════════════════════════════════════════════════════════
    with t_timeline:
        st.markdown("### 📅 Timeline Financeira por Obra")

        obra_tl = st.selectbox(
            "Obra", obras_ativas, key="tl_obra_sel"
        )

        fig_tl = _grafico_timeline_financeira(
            faturas_cli, diarias_pag_db, obra_tl
        )
        if fig_tl:
            st.plotly_chart(fig_tl, use_container_width=True)
        else:
            st.info(
                f"📋 Sem eventos financeiros registados "
                f"para {obra_tl}."
            )

        # Resumo temporal
        if not faturas_cli.empty and 'Obra' in faturas_cli.columns:
            fc_tl = faturas_cli[
                faturas_cli['Obra'] == obra_tl
            ].copy()
            if not fc_tl.empty:
                st.markdown("#### 📋 Faturas desta Obra")
                fc_tl['Total_Num'] = pd.to_numeric(
                    fc_tl.get('Total',0), errors='coerce'
                ).fillna(0)
                cols_tl = [c for c in [
                    'Numero','Data_Emissao','Data_Vencimento',
                    'Cliente','Total','Estado'
                ] if c in fc_tl.columns]
                st.dataframe(
                    fc_tl[cols_tl].sort_values(
                        'Data_Emissao', ascending=False
                    ),
                    use_container_width=True, hide_index=True
                )

                total_fat_tl = fc_tl['Total_Num'].sum()
                pagas_tl = fc_tl[
                    fc_tl.get('Estado','') == 'Paga'
                ]['Total_Num'].sum() \
                if 'Estado' in fc_tl.columns else 0.0

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("📋 Faturas",    len(fc_tl))
                with c2:
                    st.metric("💰 Total Fat.", f"€{total_fat_tl:,.2f}")
                with c3:
                    st.metric("✅ Recebido",   f"€{pagas_tl:,.2f}")

    # ════════════════════════════════════════════════════════════════
    # TAB — SCATTER LUCRATIVIDADE
    # ════════════════════════════════════════════════════════════════
    with t_scatter:
        st.markdown("### 🎯 Análise de Lucratividade")

        fig_scat = _grafico_scatter_obras(todas_pl)
        if fig_scat:
            st.plotly_chart(
                fig_scat, use_container_width=True
            )

        # Tabela comparativa todas as obras
        st.markdown("#### 📊 Comparativo Geral")
        rows_comp = []
        for p in sorted(todas_pl,
                        key=lambda x: x['margem_pct'],
                        reverse=True):
            cor_m = "🟢" if p['margem_pct'] >= 20 \
                    else "🟡" if p['margem_pct'] >= 10 \
                    else "🔴"
            _, ic = _rag(p['score'])
            rows_comp.append({
                "Obra":       p['obra'][:25],
                "Receita":    f"€{p['receita_total']:,.2f}",
                "Custos":     f"€{p['custo_total']:,.2f}",
                "Margem €":   f"€{p['margem_bruta']:,.2f}",
                "Margem %":   f"{cor_m} {p['margem_pct']:.1f}%",
                "Horas":      f"{p['horas_totais']:.0f}h",
                "Score":      f"{ic} {p['score']}/100",
            })

        df_comp = pd.DataFrame(rows_comp)
        st.dataframe(
            df_comp, use_container_width=True, hide_index=True
        )

        # Export
        csv_comp = df_comp.to_csv(
            index=False, encoding='utf-8-sig'
        )
        st.download_button(
            "📥 Exportar Comparativo",
            data=csv_comp.encode('utf-8-sig'),
            file_name=(
                f"comparativo_obras_"
                f"{date.today().strftime('%Y%m%d')}.csv"
            ),
            mime="text/csv",
            key="dl_comp_obras"
        )

        # Insights IA
        st.markdown("---")
        st.markdown("#### 🤖 Insights de Lucratividade")

        if st.button(
            "🤖 Analisar com IA",
            key="btn_insights_obras",
            type="primary",
            use_container_width=True
        ):
            import anthropic, json
            api_key = os.environ.get("ANTHROPIC_API_KEY","")
            if not api_key:
                st.error("❌ API key não configurada.")
            else:
                ctx = {
                    "obras": [
                        {
                            "nome": p['obra'],
                            "receita": p['receita_total'],
                            "custo": p['custo_total'],
                            "margem_pct": p['margem_pct'],
                            "horas": p['horas_totais'],
                            "score": p['score']
                        }
                        for p in todas_pl
                    ],
                    "margem_global": marg_pct_g,
                    "receita_total": rec_total
                }
                prompt = (
                    "Analisa este P&L de obras de uma empresa "
                    "portuguesa de mão de obra especializada "
                    "em instrumentação industrial.\n"
                    f"Dados: {json.dumps(ctx, ensure_ascii=False)}\n\n"
                    "Fornece:\n"
                    "1. Qual a obra mais rentável e porquê\n"
                    "2. Qual a obra com mais risco e o que fazer\n"
                    "3. 3 ações concretas para melhorar a margem global\n"
                    "4. Padrão que identifies nos dados\n\n"
                    "Responde em português, conciso e direto, "
                    "com dados concretos."
                )
                with st.spinner("🤖 A analisar..."):
                    try:
                        client  = anthropic.Anthropic(api_key=api_key)
                        resp    = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=700,
                            messages=[{
                                "role":"user","content":prompt
                            }]
                        )
                        insight = resp.content[0].text
                        st.markdown(
                            f"<div style='background:rgba(59,130,246,0.1);"
                            f"border:1px solid #3B82F6;"
                            f"border-radius:12px;padding:16px;"
                            f"color:#E2E8F0;font-size:0.9rem;"
                            f"line-height:1.6;'>"
                            f"<p style='color:#3B82F6;"
                            f"font-weight:700;margin:0 0 8px;'>"
                            f"🤖 ANÁLISE IA — LUCRATIVIDADE</p>"
                            f"{insight.replace(chr(10),'<br>')}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")

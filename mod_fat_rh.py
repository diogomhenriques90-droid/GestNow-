"""
GESTNOW v3 — mod_fat_rh.py
Passo 4 — RH Financeiro
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import uuid, base64, io, json, os
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from core import save_db, inv, load_db, log_audit, criar_notificacao, _gcs_read

# ─────────────────────────────────────────────────────────────────
# CONSTANTES LEGAIS PORTUGAL 2025
# ─────────────────────────────────────────────────────────────────

TSU_EMPRESA        = 23.75   # %
TSU_TRABALHADOR    = 11.00   # %
SEG_ACID_TRABALHO  = 1.50    # % estimativa média
FCT_RATE           = 0.925   # %
FGCT_RATE          = 0.075   # %
SUB_ALIM_DIA       = 6.00    # € (isento IRS cartão)
DIAS_FERIAS_ANO    = 22      # dias úteis
SALARIO_MINIMO     = 870.00  # € SMN 2025

# Tabelas IRS simplificadas (solteiro, sem dependentes)
_TABELA_IRS = [
    (0,      820,    0.0),
    (820,    935,    13.5),
    (935,    1001,   18.0),
    (1001,   1123,   23.0),
    (1123,   1765,   26.0),
    (1765,   2174,   32.75),
    (2174,   2674,   37.0),
    (2674,   3471,   39.0),
    (3471,   5765,   40.0),
    (5765,   9999999, 43.0),
]

def _calcular_irs(salario_bruto: float,
                  estado_civil: str = "Solteiro",
                  dependentes: int = 0) -> float:
    """Calcula retenção IRS mensal estimada."""
    for min_s, max_s, taxa in _TABELA_IRS:
        if min_s <= salario_bruto < max_s:
            base = salario_bruto * taxa / 100
            # Dedução dependentes (estimativa)
            ded = dependentes * 21.0
            return max(0, round(base - ded, 2))
    return 0.0


def _custo_real(salario_base: float) -> dict:
    """Calcula custo real mensal do colaborador."""
    sub_ferias_prov  = round(salario_base / 12, 2)
    sub_natal_prov   = round(salario_base / 12, 2)
    tsu_emp          = round(salario_base * TSU_EMPRESA / 100, 2)
    seg_acid         = round(salario_base * SEG_ACID_TRABALHO / 100, 2)
    fct              = round(salario_base * FCT_RATE / 100, 2)
    fgct             = round(salario_base * FGCT_RATE / 100, 2)
    total            = round(
        salario_base + sub_ferias_prov + sub_natal_prov +
        tsu_emp + seg_acid + fct + fgct, 2
    )
    pct_sobre_base = round((total - salario_base) / salario_base * 100, 1) \
                     if salario_base > 0 else 0.0

    return {
        "salario_base":      salario_base,
        "sub_ferias_prov":   sub_ferias_prov,
        "sub_natal_prov":    sub_natal_prov,
        "tsu_empresa":       tsu_emp,
        "seg_acid_trabalho": seg_acid,
        "fct":               fct,
        "fgct":              fgct,
        "total":             total,
        "pct_acrescimo":     pct_sobre_base,
    }


def _liquido(salario_base: float,
             estado_civil: str = "Solteiro",
             dependentes: int = 0) -> dict:
    """Calcula salário líquido do colaborador."""
    tsu_trab = round(salario_base * TSU_TRABALHADOR / 100, 2)
    irs      = _calcular_irs(salario_base, estado_civil, dependentes)
    liquido  = round(salario_base - tsu_trab - irs, 2)
    return {
        "bruto":          salario_base,
        "tsu_trabalhador":tsu_trab,
        "irs":            irs,
        "liquido":        liquido,
    }


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)


def _load_users_fresh():
    try:
        buf = _gcs_read("usuarios.csv")
        if buf:
            df = pd.read_csv(buf, dtype=str,
                             on_bad_lines='skip',
                             encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            return df.fillna("")
    except:
        pass
    return pd.DataFrame()


def _dias_uteis(inicio: date, fim: date) -> int:
    """Conta dias úteis entre duas datas."""
    total = 0
    d = inicio
    while d <= fim:
        if d.weekday() < 5:  # Seg-Sex
            total += 1
        d += timedelta(days=1)
    return total


# ─────────────────────────────────────────────────────────────────
# PDF RECIBO DE VENCIMENTO
# ─────────────────────────────────────────────────────────────────

def _gerar_recibo_vencimento(colaborador: dict,
                              mes: int, ano: int,
                              empresa: dict,
                              registos_db: pd.DataFrame) -> bytes:
    """Gera recibo de vencimento mensal PDF."""
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story  = []

    meses_pt = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

    bold_s = ParagraphStyle(
        'bold', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', spaceAfter=3
    )
    sub_s = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#64748B'), spaceAfter=2
    )
    normal_s = ParagraphStyle(
        'normal', parent=styles['Normal'],
        fontSize=9, spaceAfter=2
    )

    # Header
    header_data = [[
        Paragraph(
            f"<b>{empresa.get('nome','')}</b><br/>"
            f"<font size=7 color='#64748B'>"
            f"NIF: {empresa.get('nif','')} | "
            f"{empresa.get('morada','')}</font>",
            bold_s
        ),
        Paragraph(
            f"<b>RECIBO DE VENCIMENTO</b><br/>"
            f"<font size=9 color='#3B82F6'>"
            f"{meses_pt[mes-1]} {ano}</font>",
            ParagraphStyle('rh', parent=styles['Normal'],
                           fontSize=13, fontName='Helvetica-Bold',
                           alignment=2, spaceAfter=4)
        )
    ]]
    ht = Table(header_data, colWidths=[10*cm, 7*cm])
    ht.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(ht)
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor('#3B82F6')))
    story.append(Spacer(1, 0.3*cm))

    # Dados colaborador
    sal_base = float(colaborador.get('Salario_Base', 0) or 0)
    ec       = colaborador.get('Estado_Civil', 'Solteiro(a)')
    dep      = int(colaborador.get('N_Dependentes', 0) or 0)
    liq_calc = _liquido(sal_base, ec, dep)
    custo_c  = _custo_real(sal_base)

    # Horas do mês nos registos — apenas validados (Status 1,2,3,4)
    horas_mes = 0.0
    diarias_m = 0.0
    if not registos_db.empty and 'Técnico' in registos_db.columns:
        regs_c = registos_db[
            (registos_db['Técnico'] == colaborador.get('Nome','')) &
            (registos_db['Status'].astype(str).isin(['1','2','3','4']))
        ].copy()
        regs_c['Data_d'] = pd.to_datetime(
            regs_c['Data'], dayfirst=True, errors='coerce'
        )
        regs_mes = regs_c[
            (regs_c['Data_d'].dt.month == mes) &
            (regs_c['Data_d'].dt.year  == ano)
        ]
        horas_mes = pd.to_numeric(
            regs_mes['Horas_Total'], errors='coerce'
        ).fillna(0).sum()

    colab_data = [
        ["Nome:", colaborador.get('Nome',''),
         "NIF:", colaborador.get('NIF','')],
        ["Cargo:", colaborador.get('Cargo',''),
         "NISS:", colaborador.get('NISS','')],
        ["Início:", colaborador.get('DataInicio',''),
         "Categoria:", colaborador.get('Tipo','')],
        ["Estado Civil:", ec,
         "Dependentes:", str(dep)],
    ]
    ct = Table(colab_data, colWidths=[2.5*cm,5*cm,2.5*cm,5*cm])
    ct.setStyle(TableStyle([
        ('FONTSIZE',   (0,0),(-1,-1), 8),
        ('FONTNAME',   (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTNAME',   (2,0),(2,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0),(-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID',       (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(ct)
    story.append(Spacer(1, 0.4*cm))

    # Remunerações e descontos
    story.append(Paragraph("<b>REMUNERAÇÕES E DESCONTOS</b>", bold_s))

    # Tabela principal
    rows_rem = [
        # Header
        [Paragraph("<b>Descrição</b>",sub_s),
         Paragraph("<b>Dias/Horas</b>",sub_s),
         Paragraph("<b>Valor (€)</b>",sub_s)],
        # Abonos
        [Paragraph("<b>ABONOS</b>",
                   ParagraphStyle('ab', parent=styles['Normal'],
                                  fontSize=9, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#10B981'))),
         "",""],
        [f"Vencimento Base", "—", f"€{sal_base:,.2f}"],
        [f"Sub. Alimentação ({int(22)} dias úteis)",
         "22 dias", f"€{22*SUB_ALIM_DIA:.2f}"],
    ]

    # Horas extra se tiver
    if horas_mes > 160:
        h_extra = horas_mes - 160
        val_extra = round(h_extra * (sal_base/160) * 1.25, 2)
        rows_rem.append([
            f"Horas Extra ({h_extra:.1f}h × 125%)",
            f"{h_extra:.1f}h",
            f"€{val_extra:.2f}"
        ])
    else:
        val_extra = 0.0

    sub_alim = 22 * SUB_ALIM_DIA
    total_abonos = sal_base + sub_alim + val_extra

    rows_rem.append(["","",
        Paragraph(f"<b>Total Abonos: €{total_abonos:.2f}</b>",
                  ParagraphStyle('tot_ab', parent=styles['Normal'],
                                 fontSize=9, fontName='Helvetica-Bold',
                                 textColor=colors.HexColor('#10B981')))
    ])

    rows_rem.append([
        Paragraph("<b>DESCONTOS</b>",
                  ParagraphStyle('desc', parent=styles['Normal'],
                                 fontSize=9, fontName='Helvetica-Bold',
                                 textColor=colors.HexColor('#EF4444'))),
        "",""])
    rows_rem.append([
        f"Seg. Social Trabalhador ({TSU_TRABALHADOR:.2f}%)",
        "—", f"-€{liq_calc['tsu_trabalhador']:,.2f}"
    ])
    rows_rem.append([
        f"IRS (taxa estimada)",
        "—", f"-€{liq_calc['irs']:,.2f}"
    ])
    total_descontos = liq_calc['tsu_trabalhador'] + liq_calc['irs']
    rows_rem.append(["","",
        Paragraph(f"<b>Total Descontos: -€{total_descontos:.2f}</b>",
                  ParagraphStyle('tot_d', parent=styles['Normal'],
                                 fontSize=9, fontName='Helvetica-Bold',
                                 textColor=colors.HexColor('#EF4444')))
    ])

    rt = Table(rows_rem, colWidths=[9*cm, 3*cm, 5*cm])
    rt.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0),  colors.HexColor('#1E293B')),
        ('TEXTCOLOR',   (0,0),(-1,0),  colors.white),
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('GRID',        (0,0),(-1,-1), 0.2, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(rt)
    story.append(Spacer(1, 0.3*cm))

    # Total líquido
    liquido_final = round(total_abonos - total_descontos, 2)
    liq_data = [[
        Paragraph("<b>VALOR LÍQUIDO A RECEBER</b>",
                  ParagraphStyle('liq_l', parent=styles['Normal'],
                                 fontSize=13, fontName='Helvetica-Bold')),
        Paragraph(f"<b>€{liquido_final:,.2f}</b>",
                  ParagraphStyle('liq_v', parent=styles['Normal'],
                                 fontSize=18, fontName='Helvetica-Bold',
                                 textColor=colors.HexColor('#3B82F6'),
                                 alignment=2))
    ]]
    lt = Table(liq_data, colWidths=[10*cm, 7*cm])
    lt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX',(0,0),(-1,-1), 2, colors.HexColor('#3B82F6')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1), 10),
        ('BOTTOMPADDING',(0,0),(-1,-1), 10),
        ('LEFTPADDING',(0,0),(-1,-1), 12),
    ]))
    story.append(lt)
    story.append(Spacer(1, 0.3*cm))

    # Encargos empresa (informativo)
    enc_data = [
        ["Encargos Empresa (informativo):",""],
        [f"TSU Empresa ({TSU_EMPRESA:.2f}%)",
         f"€{custo_c['tsu_empresa']:,.2f}"],
        ["Sub. Férias Provisionado (1/12)",
         f"€{custo_c['sub_ferias_prov']:,.2f}"],
        ["Sub. Natal Provisionado (1/12)",
         f"€{custo_c['sub_natal_prov']:,.2f}"],
        [f"Seg. Acidentes Trabalho (~{SEG_ACID_TRABALHO:.1f}%)",
         f"€{custo_c['seg_acid_trabalho']:,.2f}"],
        [f"FCT+FGCT ({FCT_RATE+FGCT_RATE:.3f}%)",
         f"€{custo_c['fct']+custo_c['fgct']:,.2f}"],
        ["CUSTO TOTAL EMPRESA",
         f"€{custo_c['total']:,.2f}"],
    ]
    et = Table(enc_data, colWidths=[10*cm, 7*cm])
    et.setStyle(TableStyle([
        ('FONTSIZE',  (0,0),(-1,-1), 8),
        ('TEXTCOLOR', (0,0),(-1,0),  colors.HexColor('#64748B')),
        ('FONTNAME',  (0,-1),(-1,-1),'Helvetica-Bold'),
        ('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#F1F5F9')),
        ('LINEBELOW', (0,-2),(-1,-2), 1, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',(0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
        ('LEFTPADDING',(0,0),(-1,-1), 6),
        ('TEXTCOLOR', (0,0),(-1,-2), colors.HexColor('#64748B')),
    ]))
    story.append(et)
    story.append(Spacer(1, 0.5*cm))

    # Dados pagamento
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Spacer(1, 0.2*cm))
    iban_colab = colaborador.get('Banco_IBAN','N/D')
    story.append(Paragraph(
        f"<b>Pagamento por transferência bancária:</b> "
        f"IBAN {iban_colab}",
        sub_s
    ))
    story.append(Paragraph(
        f"Processado por GESTNOW v3.0 | "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_custo_real_breakdown(nome, custo):
    """Waterfall custo real do colaborador."""
    categorias = [
        "Salário Base","Sub.Férias","Sub.Natal",
        "TSU Empresa","Seg.Acidentes","FCT+FGCT","Total"
    ]
    valores = [
        custo['salario_base'],
        custo['sub_ferias_prov'],
        custo['sub_natal_prov'],
        custo['tsu_empresa'],
        custo['seg_acid_trabalho'],
        custo['fct'] + custo['fgct'],
        0
    ]
    medidas = [
        "absolute","relative","relative",
        "relative","relative","relative","total"
    ]

    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=medidas,
        x=categorias,
        y=valores,
        connector={"line":{"color":"#334155"}},
        increasing={"marker":{"color":"#3B82F6"}},
        decreasing={"marker":{"color":"#EF4444"}},
        totals={"marker":{"color":"#10B981"}},
        text=[f"€{v:,.2f}" for v in valores],
        textposition="outside",
        textfont={"color":"#F1F5F9","size":9}
    ))
    fig.update_layout(
        title={'text':f'Custo Real — {nome[:20]}',
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


def _grafico_mapa_remuneracoes(rh_db, users_df):
    """Bar chart custo total por colaborador."""
    if rh_db.empty:
        return None

    nomes, custos, liquidos = [], [], []
    for _, row in rh_db.iterrows():
        sal = float(row.get('Salario_Base',0) or 0)
        c   = _custo_real(sal)
        lq  = _liquido(sal)
        nomes.append(str(row.get('Nome','')).split()[0])
        custos.append(c['total'])
        liquidos.append(lq['liquido'])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Custo Empresa', x=nomes, y=custos,
        marker_color='#3B82F6',
        hovertemplate='%{x}<br>Custo: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Líquido Colaborador', x=nomes, y=liquidos,
        marker_color='#10B981',
        hovertemplate='%{x}<br>Líquido: €%{y:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Mapa de Remunerações',
               'font':{'color':'#F1F5F9'}},
        barmode='group',
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


def _grafico_ferias_calendario(ferias_db, users_df):
    """Heatmap de férias por colaborador e mês."""
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun",
             "Jul","Ago","Set","Out","Nov","Dez"]
    if ferias_db.empty:
        return None

    nomes = ferias_db['Colaborador'].unique().tolist() \
            if 'Colaborador' in ferias_db.columns else []
    if not nomes:
        return None

    z = [[0]*12 for _ in range(len(nomes))]
    for i, nome in enumerate(nomes):
        fds = ferias_db[ferias_db['Colaborador'] == nome] \
              if 'Colaborador' in ferias_db.columns \
              else pd.DataFrame()
        for _, fd in fds.iterrows():
            try:
                ini = datetime.strptime(fd.get('Data_Inicio',''),
                                        "%d/%m/%Y").date()
                fim = datetime.strptime(fd.get('Data_Fim',''),
                                        "%d/%m/%Y").date()
                d = ini
                while d <= fim:
                    if d.weekday() < 5:
                        z[i][d.month - 1] += 1
                    d += timedelta(days=1)
            except:
                pass

    fig = go.Figure(go.Heatmap(
        z=z,
        x=meses,
        y=[n.split()[0] for n in nomes],
        colorscale=[
            [0,   'rgba(30,41,59,0.5)'],
            [0.3, 'rgba(59,130,246,0.4)'],
            [1,   'rgba(16,185,129,1)'],
        ],
        showscale=True,
        colorbar={'title':{'text':'Dias','font':{'color':'#94A3B8'}},
                  'tickfont':{'color':'#94A3B8'}},
        hovertemplate='%{y} — %{x}: %{z} dias<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Calendário de Férias (dias por mês)',
               'font':{'color':'#F1F5F9'}},
        height=max(200, len(nomes)*40 + 60),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'tickfont':{'color':'#94A3B8'}},
        yaxis={'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=80,r=10)
    )
    return fig


def _grafico_provisoes_acumuladas(rh_db, mes_atual, ano_atual):
    """Line chart provisões acumuladas vs pagas."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    labels, prov_ac, pag_ac = [], [], []

    total_prov_mes = 0.0
    if not rh_db.empty:
        for _, row in rh_db.iterrows():
            sal = float(row.get('Salario_Base',0) or 0)
            c   = _custo_real(sal)
            total_prov_mes += c['sub_ferias_prov'] + c['sub_natal_prov']

    ac = 0.0
    for m in range(1, mes_atual + 1):
        ac += total_prov_mes
        labels.append(meses_pt[m-1])
        prov_ac.append(round(ac, 2))
        # Simula pagamento em junho (férias) e dezembro (natal)
        pago = 0.0
        if m == 6 and not rh_db.empty:
            pago = sum(
                float(r.get('Salario_Base',0) or 0)
                for _, r in rh_db.iterrows()
            )
        if m == 12 and not rh_db.empty:
            pago = sum(
                float(r.get('Salario_Base',0) or 0)
                for _, r in rh_db.iterrows()
            )
        pag_ac.append(round(pago, 2))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=prov_ac,
        mode='lines+markers',
        name='Provisionado',
        line={'color':'#3B82F6','width':3},
        fill='tozeroy',
        fillcolor='rgba(59,130,246,0.1)'
    ))
    fig.add_trace(go.Bar(
        x=labels, y=pag_ac,
        name='Pago',
        marker_color='#10B981',
        opacity=0.7
    ))
    fig.update_layout(
        title={'text':'Provisões Sub. Férias + Natal',
               'font':{'color':'#F1F5F9'}},
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155','tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10)
    )
    return fig


def _grafico_evolucao_custo_rh(rh_db):
    """Donut breakdown custo total RH."""
    if rh_db.empty:
        return None

    tot_sal = tot_tsu = tot_sub = tot_seg = 0.0
    for _, row in rh_db.iterrows():
        sal = float(row.get('Salario_Base',0) or 0)
        c   = _custo_real(sal)
        tot_sal += sal
        tot_tsu += c['tsu_empresa']
        tot_sub += c['sub_ferias_prov'] + c['sub_natal_prov']
        tot_seg += c['seg_acid_trabalho'] + c['fct'] + c['fgct']

    fig = go.Figure(go.Pie(
        labels=['Salários','TSU Empresa','Subsídios','Seguros+FCT'],
        values=[tot_sal, tot_tsu, tot_sub, tot_seg],
        hole=0.5,
        marker={
            'colors':['#3B82F6','#EF4444','#10B981','#F59E0B'],
            'line':{'color':'#0F172A','width':2}
        },
        textfont={'color':'#F1F5F9','size':10},
        hovertemplate='%{label}: €%{value:,.2f}<extra></extra>'
    ))
    total_rh = tot_sal + tot_tsu + tot_sub + tot_seg
    fig.update_layout(
        title={'text':'Breakdown Custo RH Total',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        margin=dict(t=40,b=10,l=10,r=10),
        annotations=[{
            'text':f'€{total_rh:,.0f}',
            'x':0.5,'y':0.5,
            'font_size':13,'font_color':'#F1F5F9',
            'showarrow':False
        }]
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_rh(obras_db, registos_db, *_):
    """Módulo RH Financeiro."""

    # ── Carregar dados ────────────────────────────────────────────
    users_df  = _load_users_fresh()
    rh_db     = _load("colaboradores_rh.csv", [
        "ID","Nome","NIF","NISS","Tipo","Cargo","Salario_Base",
        "Data_Inicio","Estado_Civil","N_Dependentes",
        "Banco_IBAN","Contrato","Ativo",
        "Genero","DataNasc","Naturalidade","Nacionalidade","Pais_Residencia",
        "CC","CC_Validade","Passaporte","Passaporte_Validade",
        "IRS_Escalao","IRS_Percentagem","Titular_Unico","Taxa_Retencao_IRS",
        "Isencao_IRS","Artigo_IRS",
        "Tipo_Contrato","Modalidade_Horario","Horas_Semana",
        "Contrato_Inicio","Contrato_Fim","Contrato_Indeterminado",
        "Periodo_Experimental","Periodo_Experimental_Fim",
        "Local_Trabalho","Funcao_Contratual",
        "Subsidio_Alimentacao","Subsidio_Ferias","Subsidio_Natal",
        "Premio_Producao","Outros_Complementos","Forma_Pagamento",
        "IBAN_Validado","SWIFT_BIC",
        "Nivel_Habilitacoes","Situacao_Profissional","Profissao_CPP",
        "Categoria_CCT","IRCT_Aplicavel","Vinculo_Empresa",
        "Reducao_Horario","Data_Ultima_Promocao","Antiguidade_Anos",
        "Nivel_Remuneratorio","Grau_Deficiencia","Deficiencia_Tipo",
        "Seg_Social_Cartao","Cartao_Prof_Num","Cartao_Prof_Validade",
        "Alvara_Num","Alvara_Validade",
    ])
    ferias_db = _load("ferias_db.csv", [
        "ID","Colaborador","Data_Inicio","Data_Fim",
        "Dias_Uteis","Estado","Aprovado_Por","Obra"
    ])
    provisoes_db = _load("provisoes_db.csv", [
        "ID","Colaborador","Mes","Ano","Tipo",
        "Valor_Provisionado","Valor_Pago","Data_Pagamento"
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
            "morada":"Zona Industrial de Seia",
        }

    user_nome = st.session_state.get('user','Admin')
    mes_atual = date.today().month
    ano_atual = date.today().year
    meses_pt  = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                 "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .rh-card {
        background:#1E293B; border-radius:12px;
        padding:14px 16px; margin-bottom:8px;
        border-left:4px solid #8B5CF6;
    }
    .custo-breakdown {
        background:linear-gradient(135deg,
            rgba(30,41,59,0.9),rgba(15,23,42,0.9));
        border-radius:12px; padding:16px; margin-bottom:8px;
    }
    .ferias-badge {
        display:inline-block; padding:3px 10px;
        border-radius:20px; font-size:0.72rem; font-weight:700;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────
    n_colab   = len(rh_db) if not rh_db.empty else 0
    n_ativos  = len(rh_db[rh_db.get('Ativo','Sim')=='Sim']) \
                if not rh_db.empty and 'Ativo' in rh_db.columns \
                else n_colab

    total_sal = 0.0
    total_custo_rh = 0.0
    if not rh_db.empty:
        for _, row in rh_db.iterrows():
            sal = float(row.get('Salario_Base',0) or 0)
            total_sal      += sal
            total_custo_rh += _custo_real(sal)['total']

    # Férias pendentes de aprovação
    ferias_pend = len(ferias_db[
        ferias_db['Estado'] == 'Pendente'
    ]) if not ferias_db.empty and 'Estado' in ferias_db.columns else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("👥 Colaboradores",    n_ativos)
    with c2: st.metric("💰 Massa Salarial",   f"€{total_sal:,.2f}")
    with c3: st.metric("💸 Custo Real Total", f"€{total_custo_rh:,.2f}")
    with c4: st.metric("📈 Acréscimo",
                        f"+{round((total_custo_rh-total_sal)/total_sal*100,1) if total_sal>0 else 0:.1f}%")
    with c5: st.metric("🏖️ Férias Pendentes", ferias_pend)

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_colab, t_mapa, t_recibos,
     t_ferias, t_prov, t_irs) = st.tabs([
        "👤 Colaboradores",
        "💰 Mapa Remunerações",
        "📄 Recibos Vencimento",
        "🏖️ Férias & Subsídios",
        "📊 Provisões",
        "📋 Mapa IRS/SS",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — COLABORADORES (ficha financeira)
    # ════════════════════════════════════════════════════════════════
    with t_colab:
        st.markdown("### 👤 Fichas Financeiras dos Colaboradores")

        col_form_c, col_lista_c = st.columns([1, 2])

        with col_form_c:
            st.markdown("#### ➕ Adicionar/Editar Colaborador")

            # Pré-preencher com utilizadores existentes
            users_lista = users_df['Nome'].tolist() \
                          if not users_df.empty else []

            with st.form("form_colab_rh"):
                if users_lista:
                    nome_sel = st.selectbox(
                        "Colaborador *",
                        users_lista, key="rh_nome_sel"
                    )
                    # Auto-preencher NIF se disponível
                    u_row = users_df[
                        users_df['Nome'] == nome_sel
                    ] if not users_df.empty else pd.DataFrame()
                    nif_auto = u_row.iloc[0].get('NIF','') \
                               if not u_row.empty else ''
                    niss_auto= u_row.iloc[0].get('NISS','') \
                               if not u_row.empty else ''
                    cargo_auto=u_row.iloc[0].get('Cargo','') \
                               if not u_row.empty else ''
                    tipo_auto = u_row.iloc[0].get('Tipo','') \
                               if not u_row.empty else ''
                    iban_auto = u_row.iloc[0].get('Banco_IBAN','') \
                               if not u_row.empty else ''
                else:
                    nome_sel  = st.text_input("Nome *", key="rh_nome")
                    nif_auto  = niss_auto = cargo_auto = ""
                    tipo_auto = iban_auto = ""

                col_rh1, col_rh2 = st.columns(2)
                with col_rh1:
                    rh_nif = st.text_input(
                        "NIF", value=nif_auto, key="rh_nif"
                    )
                    rh_niss = st.text_input(
                        "NISS", value=niss_auto, key="rh_niss"
                    )
                    rh_sal = st.number_input(
                        "Salário Base (€) *",
                        min_value=SALARIO_MINIMO,
                        value=SALARIO_MINIMO,
                        step=50.0, key="rh_sal"
                    )
                    rh_data_ini = st.text_input(
                        "Data Início (dd/mm/aaaa)",
                        value=date.today().strftime("%d/%m/%Y"),
                        key="rh_data_ini"
                    )
                with col_rh2:
                    rh_ec = st.selectbox(
                        "Estado Civil",
                        ["Solteiro(a)","Casado(a)","Divorciado(a)",
                         "Viúvo(a)","União de Facto"],
                        key="rh_ec"
                    )
                    rh_dep = st.number_input(
                        "Nº Dependentes",
                        min_value=0, value=0,
                        key="rh_dep"
                    )
                    rh_contrato = st.selectbox(
                        "Tipo Contrato",
                        ["Sem Termo","A Termo Certo",
                         "Prestação Serviços","Outro"],
                        key="rh_contrato"
                    )
                    rh_iban = st.text_input(
                        "IBAN Pagamento",
                        value=iban_auto,
                        key="rh_iban"
                    )

                # Preview custo real
                if rh_sal > 0:
                    c_prev = _custo_real(rh_sal)
                    lq_prev = _liquido(rh_sal, rh_ec, rh_dep)
                    st.markdown(
                        f"<div style='background:rgba(59,130,246,0.1);"
                        f"border:1px solid #3B82F6;border-radius:8px;"
                        f"padding:10px;margin:8px 0;font-size:0.8rem;'>"
                        f"💰 Custo empresa: <b style='color:#3B82F6;'>"
                        f"€{c_prev['total']:,.2f}/mês</b> "
                        f"(+{c_prev['pct_acrescimo']:.1f}%)<br>"
                        f"💵 Líquido colaborador: "
                        f"<b style='color:#10B981;'>"
                        f"€{lq_prev['liquido']:,.2f}/mês</b>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                if st.form_submit_button(
                    "💾 Guardar Ficha",
                    use_container_width=True, type="primary"
                ):
                    nome_final = nome_sel if users_lista \
                                 else st.session_state.get(
                                     'rh_nome',''
                                 )
                    if not nome_final:
                        st.error("❌ Nome obrigatório.")
                    else:
                        # Verificar se já existe
                        existe = not rh_db.empty and \
                                 nome_final in rh_db.get(
                                     'Nome', pd.Series()
                                 ).values

                        nova_ficha = {
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Nome":         nome_final,
                            "NIF":          rh_nif.strip(),
                            "NISS":         rh_niss.strip(),
                            "Tipo":         tipo_auto,
                            "Cargo":        cargo_auto,
                            "Salario_Base": rh_sal,
                            "Data_Inicio":  rh_data_ini,
                            "Estado_Civil": rh_ec,
                            "N_Dependentes":rh_dep,
                            "Banco_IBAN":   rh_iban.strip(),
                            "Contrato":     rh_contrato,
                            "Ativo":        "Sim"
                        }

                        if existe:
                            for k, v in nova_ficha.items():
                                if k != 'ID':
                                    rh_db.loc[
                                        rh_db['Nome'] == nome_final, k
                                    ] = v
                            save_db(rh_db, "colaboradores_rh.csv")
                            msg = f"✅ Ficha de {nome_final} atualizada!"
                        else:
                            nova_df = pd.DataFrame([nova_ficha])
                            upd = pd.concat(
                                [rh_db, nova_df], ignore_index=True
                            ) if not rh_db.empty else nova_df
                            save_db(upd, "colaboradores_rh.csv")
                            msg = f"✅ Ficha de {nome_final} criada!"

                        log_audit(
                            usuario=user_nome,
                            acao="FICHA_RH",
                            tabela="colaboradores_rh.csv",
                            registro_id=nome_final,
                            detalhes=f"Salário: €{rh_sal}",
                            ip=""
                        )
                        inv("colaboradores_rh.csv")
                        st.success(msg)
                        st.rerun()

        with col_lista_c:
            st.markdown("#### 📋 Fichas Registadas")

            # Gráficos
            col_gc1, col_gc2 = st.columns(2)
            with col_gc1:
                fig_mapa = _grafico_mapa_remuneracoes(rh_db, users_df)
                if fig_mapa:
                    st.plotly_chart(
                        fig_mapa, use_container_width=True
                    )
            with col_gc2:
                fig_dnt = _grafico_evolucao_custo_rh(rh_db)
                if fig_dnt:
                    st.plotly_chart(
                        fig_dnt, use_container_width=True
                    )

            if rh_db.empty:
                st.info(
                    "📋 Sem fichas financeiras. "
                    "Adiciona colaboradores no formulário."
                )
            else:
                for _, colab in rh_db.iterrows():
                    sal    = float(colab.get('Salario_Base',0) or 0)
                    c_real = _custo_real(sal)
                    lq     = _liquido(
                        sal,
                        colab.get('Estado_Civil','Solteiro(a)'),
                        int(colab.get('N_Dependentes',0) or 0)
                    )

                    with st.expander(
                        f"👤 {colab.get('Nome','')} — "
                        f"€{sal:,.2f} base | "
                        f"€{c_real['total']:,.2f} custo real",
                        expanded=False
                    ):
                        col_cd1, col_cd2 = st.columns(2)
                        with col_cd1:
                            st.markdown(
                                f"<div class='custo-breakdown'>"
                                f"<p style='color:#94A3B8;"
                                f"font-size:0.75rem;font-weight:700;"
                                f"text-transform:uppercase;margin:0 0 8px;'>"
                                f"CUSTO EMPRESA</p>",
                                unsafe_allow_html=True
                            )
                            items_custo = [
                                ("Salário Base", c_real['salario_base'],
                                 "#3B82F6"),
                                ("Sub.Férias (1/12)", c_real['sub_ferias_prov'],
                                 "#8B5CF6"),
                                ("Sub.Natal (1/12)", c_real['sub_natal_prov'],
                                 "#8B5CF6"),
                                ("TSU Empresa", c_real['tsu_empresa'],
                                 "#EF4444"),
                                ("Seg.Acidentes", c_real['seg_acid_trabalho'],
                                 "#F59E0B"),
                                ("FCT+FGCT", c_real['fct']+c_real['fgct'],
                                 "#F59E0B"),
                            ]
                            for label, val, cor in items_custo:
                                pct = (val/c_real['total']*100) \
                                      if c_real['total'] > 0 else 0.0
                                st.markdown(
                                    f"<div style='display:flex;"
                                    f"justify-content:space-between;"
                                    f"margin-bottom:4px;'>"
                                    f"<small style='color:#94A3B8;'>"
                                    f"{label}</small>"
                                    f"<small style='color:{cor};"
                                    f"font-weight:700;'>"
                                    f"€{val:,.2f} "
                                    f"({pct:.1f}%)</small></div>",
                                    unsafe_allow_html=True
                                )
                            st.markdown(
                                f"<div style='border-top:"
                                f"1px solid #334155;padding-top:6px;"
                                f"margin-top:4px;display:flex;"
                                f"justify-content:space-between;'>"
                                f"<b style='color:#F1F5F9;'>TOTAL</b>"
                                f"<b style='color:#10B981;"
                                f"font-size:1.05rem;'>"
                                f"€{c_real['total']:,.2f}</b></div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with col_cd2:
                            st.markdown(
                                f"<div class='custo-breakdown'>"
                                f"<p style='color:#94A3B8;"
                                f"font-size:0.75rem;font-weight:700;"
                                f"text-transform:uppercase;margin:0 0 8px;'>"
                                f"RECIBO COLABORADOR</p>",
                                unsafe_allow_html=True
                            )
                            items_liq = [
                                ("Salário Bruto", lq['bruto'], "#F1F5F9"),
                                ("TSU (11%)", -lq['tsu_trabalhador'],
                                 "#EF4444"),
                                ("IRS (estimado)", -lq['irs'], "#EF4444"),
                            ]
                            for label, val, cor in items_liq:
                                st.markdown(
                                    f"<div style='display:flex;"
                                    f"justify-content:space-between;"
                                    f"margin-bottom:4px;'>"
                                    f"<small style='color:#94A3B8;'>"
                                    f"{label}</small>"
                                    f"<small style='color:{cor};"
                                    f"font-weight:700;'>"
                                    f"{'€' if val>=0 else '-€'}"
                                    f"{abs(val):,.2f}</small></div>",
                                    unsafe_allow_html=True
                                )
                            st.markdown(
                                f"<div style='border-top:"
                                f"1px solid #334155;padding-top:6px;"
                                f"margin-top:4px;display:flex;"
                                f"justify-content:space-between;'>"
                                f"<b style='color:#F1F5F9;'>LÍQUIDO</b>"
                                f"<b style='color:#3B82F6;"
                                f"font-size:1.05rem;'>"
                                f"€{lq['liquido']:,.2f}</b></div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )

                        # Waterfall
                        st.plotly_chart(_grafico_custo_real_breakdown(colab.get('Nome',''), c_real), key=f"custo_{colab.get('Nome','')}") 

    # ════════════════════════════════════════════════════════════════
    # TAB — MAPA DE REMUNERAÇÕES
    # ════════════════════════════════════════════════════════════════
    with t_mapa:
        st.markdown("### 💰 Mapa de Remunerações Mensal")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            mes_mapa = st.selectbox(
                "Mês", meses_pt,
                index=mes_atual - 1, key="mapa_mes"
            )
        with col_m2:
            ano_mapa = st.number_input(
                "Ano", min_value=2020,
                value=ano_atual, key="mapa_ano"
            )

        mes_num_m = meses_pt.index(mes_mapa) + 1

        if rh_db.empty:
            st.info(
                "📋 Sem fichas financeiras. "
                "Adiciona no tab 👤 Colaboradores."
            )
        else:
            # Construir tabela
            rows_mapa = []
            tot_base  = tot_sub_alim = tot_bruto = 0.0
            tot_tsu_t = tot_irs_mapa = tot_liq = 0.0
            tot_tsu_e = tot_sub_fv   = tot_custo = 0.0

            for _, colab in rh_db.iterrows():
                sal  = float(colab.get('Salario_Base',0) or 0)
                ec   = colab.get('Estado_Civil','Solteiro(a)')
                dep  = int(colab.get('N_Dependentes',0) or 0)
                c    = _custo_real(sal)
                lq   = _liquido(sal, ec, dep)
                sub_alim = 22 * SUB_ALIM_DIA

                # Dias trabalhados no mês — apenas registos validados (Status 1,2,3,4)
                horas_m = 0
                if not registos_db.empty and \
                   'Técnico' in registos_db.columns:
                    regs_c = registos_db[
                        (registos_db['Técnico'] == colab.get('Nome','')) &
                        (registos_db['Status'].astype(str).isin(['1','2','3','4']))
                    ].copy()
                    regs_c['Data_d'] = pd.to_datetime(
                        regs_c['Data'], dayfirst=True, errors='coerce'
                    )
                    rm = regs_c[
                        (regs_c['Data_d'].dt.month == mes_num_m) &
                        (regs_c['Data_d'].dt.year  == ano_mapa)
                    ]
                    # Dias únicos trabalhados
                    horas_m = rm['Data_d'].dt.date.nunique()

                sub_alim_real = horas_m * SUB_ALIM_DIA
                bruto_real    = sal + sub_alim_real

                rows_mapa.append({
                    "Nome":         colab.get('Nome','')[:20],
                    "Cargo":        colab.get('Cargo','')[:15],
                    "Sal.Base":     f"€{sal:,.2f}",
                    "Sub.Alim":     f"€{sub_alim_real:.2f}",
                    "Bruto":        f"€{bruto_real:,.2f}",
                    "TSU Trab":     f"-€{lq['tsu_trabalhador']:,.2f}",
                    "IRS":          f"-€{lq['irs']:,.2f}",
                    "Líquido":      f"€{lq['liquido']:,.2f}",
                    "TSU Emp":      f"€{c['tsu_empresa']:,.2f}",
                    "Custo Total":  f"€{c['total']:,.2f}",
                })

                tot_base     += sal
                tot_sub_alim += sub_alim_real
                tot_bruto    += bruto_real
                tot_tsu_t    += lq['tsu_trabalhador']
                tot_irs_mapa += lq['irs']
                tot_liq      += lq['liquido']
                tot_tsu_e    += c['tsu_empresa']
                tot_custo    += c['total']

            if rows_mapa:
                df_mapa = pd.DataFrame(rows_mapa)
                st.dataframe(
                    df_mapa, use_container_width=True, hide_index=True
                )

                # Totais
                st.markdown(
                    f"<div style='background:#1E293B;"
                    f"border-radius:10px;padding:14px;"
                    f"display:grid;"
                    f"grid-template-columns:repeat(5,1fr);"
                    f"gap:12px;margin-top:8px;'>"
                    f"<div style='text-align:center;'>"
                    f"<small style='color:#64748B;'>Massa Salarial</small><br>"
                    f"<b style='color:#3B82F6;'>€{tot_base:,.2f}</b></div>"
                    f"<div style='text-align:center;'>"
                    f"<small style='color:#64748B;'>Total Bruto</small><br>"
                    f"<b style='color:#F1F5F9;'>€{tot_bruto:,.2f}</b></div>"
                    f"<div style='text-align:center;'>"
                    f"<small style='color:#64748B;'>Total Líquido</small><br>"
                    f"<b style='color:#10B981;'>€{tot_liq:,.2f}</b></div>"
                    f"<div style='text-align:center;'>"
                    f"<small style='color:#64748B;'>TSU Empresa</small><br>"
                    f"<b style='color:#EF4444;'>€{tot_tsu_e:,.2f}</b></div>"
                    f"<div style='text-align:center;'>"
                    f"<small style='color:#64748B;'>Custo Total RH</small><br>"
                    f"<b style='color:#F59E0B;"
                    f"font-size:1.1rem;'>€{tot_custo:,.2f}</b></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                # Export Excel
                csv_mapa = df_mapa.to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    f"📥 Exportar Mapa {mes_mapa} {ano_mapa}",
                    data=csv_mapa.encode('utf-8-sig'),
                    file_name=(
                        f"mapa_remuneracoes_"
                        f"{mes_num_m:02d}_{ano_mapa}.csv"
                    ),
                    mime="text/csv",
                    key="dl_mapa_rem"
                )

    # ════════════════════════════════════════════════════════════════
    # TAB — RECIBOS DE VENCIMENTO
    # ════════════════════════════════════════════════════════════════
    with t_recibos:
        st.markdown("### 📄 Recibos de Vencimento")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            mes_rec = st.selectbox(
                "Mês", meses_pt,
                index=mes_atual - 1, key="rec_mes"
            )
        with col_r2:
            ano_rec = st.number_input(
                "Ano", min_value=2020,
                value=ano_atual, key="rec_ano"
            )

        mes_num_r = meses_pt.index(mes_rec) + 1

        if rh_db.empty:
            st.info("📋 Sem fichas financeiras para gerar recibos.")
        else:
            # Gerar todos em ZIP
            if st.button(
                f"📦 Gerar Todos os Recibos — {mes_rec} {ano_rec}",
                key="btn_recibos_todos",
                type="primary",
                use_container_width=True
            ):
                import zipfile as zf
                buf_zip = io.BytesIO()
                n_gerados = 0
                with st.spinner(
                    f"A gerar {len(rh_db)} recibo(s)..."
                ):
                    with zf.ZipFile(
                        buf_zip, 'w', zf.ZIP_DEFLATED
                    ) as zfile:
                        for _, colab in rh_db.iterrows():
                            try:
                                pdf_r = _gerar_recibo_vencimento(
                                    dict(colab),
                                    mes_num_r, ano_rec,
                                    empresa, registos_db
                                )
                                nome_f = (
                                    colab.get('Nome','colab')
                                    .replace(' ','_')
                                )
                                zfile.writestr(
                                    f"recibo_{nome_f}_"
                                    f"{mes_num_r:02d}_{ano_rec}.pdf",
                                    pdf_r
                                )
                                n_gerados += 1
                            except Exception as ex:
                                st.warning(
                                    f"⚠️ Erro em "
                                    f"{colab.get('Nome','')}: {ex}"
                                )

                buf_zip.seek(0)
                st.session_state['recibos_zip'] = buf_zip.getvalue()
                st.session_state['recibos_zip_nome'] = (
                    f"recibos_{mes_num_r:02d}_{ano_rec}.zip"
                )
                st.success(f"✅ {n_gerados} recibo(s) gerado(s)!")
                st.rerun()

            if st.session_state.get('recibos_zip'):
                st.download_button(
                    f"📥 Descarregar ZIP Recibos",
                    data=st.session_state['recibos_zip'],
                    file_name=st.session_state.get(
                        'recibos_zip_nome','recibos.zip'
                    ),
                    mime="application/zip",
                    key="dl_recibos_zip",
                    use_container_width=True,
                    type="primary"
                )

            st.markdown("---")
            st.markdown("#### 📄 Recibo Individual")

            colab_sel_r = st.selectbox(
                "Colaborador",
                rh_db['Nome'].tolist()
                if 'Nome' in rh_db.columns else [],
                key="rec_colab_sel"
            )

            if colab_sel_r:
                colab_row = rh_db[
                    rh_db['Nome'] == colab_sel_r
                ].iloc[0] if not rh_db.empty else None

                if colab_row is not None:
                    sal_prev = float(colab_row.get('Salario_Base',0) or 0)
                    c_pr     = _custo_real(sal_prev)
                    lq_pr    = _liquido(
                        sal_prev,
                        colab_row.get('Estado_Civil','Solteiro(a)'),
                        int(colab_row.get('N_Dependentes',0) or 0)
                    )

                    # Preview
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:14px;'>"
                        f"<b style='color:#F1F5F9;'>"
                        f"{colab_sel_r}</b> — "
                        f"{mes_rec} {ano_rec}<br>"
                        f"<small style='color:#64748B;'>"
                        f"Bruto: €{sal_prev:,.2f} · "
                        f"TSU: -€{lq_pr['tsu_trabalhador']:,.2f} · "
                        f"IRS: -€{lq_pr['irs']:,.2f} · "
                        f"</small>"
                        f"<b style='color:#3B82F6;'>"
                        f"Líquido: €{lq_pr['liquido']:,.2f}</b>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    if st.button(
                        f"📄 Gerar Recibo — {colab_sel_r}",
                        key="btn_recibo_ind",
                        type="primary",
                        use_container_width=True
                    ):
                        with st.spinner("A gerar..."):
                            pdf_ind = _gerar_recibo_vencimento(
                                dict(colab_row),
                                mes_num_r, ano_rec,
                                empresa, registos_db
                            )
                        st.session_state['recibo_ind_bytes'] = pdf_ind
                        st.session_state['recibo_ind_nome']  = (
                            f"recibo_{colab_sel_r.replace(' ','_')}_"
                            f"{mes_num_r:02d}_{ano_rec}.pdf"
                        )
                        st.rerun()

                    if st.session_state.get('recibo_ind_bytes'):
                        st.download_button(
                            "📥 Descarregar Recibo",
                            data=st.session_state['recibo_ind_bytes'],
                            file_name=st.session_state.get(
                                'recibo_ind_nome','recibo.pdf'
                            ),
                            mime="application/pdf",
                            key="dl_recibo_ind",
                            use_container_width=True
                        )

    # ════════════════════════════════════════════════════════════════
    # TAB — FÉRIAS & SUBSÍDIOS
    # ════════════════════════════════════════════════════════════════
    with t_ferias:
        st.markdown("### 🏖️ Gestão de Férias & Subsídios")

        col_f1, col_f2 = st.columns([1, 2])

        with col_f1:
            st.markdown("#### ➕ Marcar Férias")
            with st.form("form_ferias"):
                colab_lista_f = rh_db['Nome'].tolist() \
                                if not rh_db.empty else []
                f_colab = st.selectbox(
                    "Colaborador *",
                    colab_lista_f if colab_lista_f else [""],
                    key="fer_colab"
                )
                col_fd1, col_fd2 = st.columns(2)
                with col_fd1:
                    f_ini = st.date_input(
                        "Início *", value=date.today(),
                        key="fer_ini"
                    )
                with col_fd2:
                    f_fim = st.date_input(
                        "Fim *",
                        value=date.today() + timedelta(days=5),
                        key="fer_fim"
                    )

                # Calcular dias úteis
                if f_ini and f_fim and f_fim >= f_ini:
                    du = _dias_uteis(f_ini, f_fim)
                    st.markdown(
                        f"<small style='color:#3B82F6;'>"
                        f"📅 {du} dia(s) útil(eis)</small>",
                        unsafe_allow_html=True
                    )

                f_obra_fer = st.selectbox(
                    "Obra em que estava alocado",
                    [""] + (obras_db[
                        obras_db['Ativa']=='Ativa'
                    ]['Obra'].tolist()
                    if not obras_db.empty else []),
                    key="fer_obra"
                )
                f_estado_fer = st.selectbox(
                    "Estado",
                    ["Pendente","Aprovado","Gozado","Cancelado"],
                    key="fer_estado"
                )

                if st.form_submit_button(
                    "💾 Marcar Férias",
                    use_container_width=True, type="primary"
                ):
                    if not f_colab or f_fim < f_ini:
                        st.error("❌ Dados inválidos.")
                    else:
                        du2 = _dias_uteis(f_ini, f_fim)
                        nova_fer = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Colaborador":  f_colab,
                            "Data_Inicio":  f_ini.strftime("%d/%m/%Y"),
                            "Data_Fim":     f_fim.strftime("%d/%m/%Y"),
                            "Dias_Uteis":   du2,
                            "Estado":       f_estado_fer,
                            "Aprovado_Por": user_nome
                            if f_estado_fer == 'Aprovado' else "",
                            "Obra":         f_obra_fer
                        }])
                        upd_fer = pd.concat(
                            [ferias_db, nova_fer], ignore_index=True
                        ) if not ferias_db.empty else nova_fer
                        save_db(upd_fer, "ferias_db.csv")
                        inv("ferias_db.csv")
                        st.success(
                            f"✅ Férias marcadas para {f_colab}! "
                            f"{du2} dia(s)"
                        )
                        st.rerun()

        with col_f2:
            st.markdown("#### 📊 Calendário de Férias")

            # Heatmap calendário
            fig_cal = _grafico_ferias_calendario(ferias_db, users_df)
            if fig_cal:
                st.plotly_chart(
                    fig_cal, use_container_width=True
                )
            else:
                st.info("📅 Sem férias marcadas.")

            # Controlo de dias disponíveis
            if not rh_db.empty and not ferias_db.empty:
                st.markdown("#### 📋 Saldo de Férias")
                for _, colab in rh_db.iterrows():
                    nome_c = colab.get('Nome','')
                    # Dias gozados este ano
                    fer_colab = ferias_db[
                        (ferias_db.get('Colaborador','') == nome_c) &
                        (ferias_db.get('Estado','') == 'Gozado')
                    ] if 'Colaborador' in ferias_db.columns else \
                      pd.DataFrame()

                    dias_gozados = pd.to_numeric(
                        fer_colab.get('Dias_Uteis',0),
                        errors='coerce'
                    ).fillna(0).sum() if not fer_colab.empty else 0

                    dias_disponiveis = DIAS_FERIAS_ANO - dias_gozados
                    pct_fer = dias_gozados / DIAS_FERIAS_ANO * 100

                    cor_fer = "#10B981" if dias_disponiveis > 10 \
                              else "#F59E0B" if dias_disponiveis > 5 \
                              else "#EF4444"

                    # Alerta férias vencidas
                    alerta_ven = ""
                    if dias_disponiveis > 0 and \
                       date.today().month >= 10:
                        alerta_ven = (
                            f"<span style='color:#EF4444;"
                            f"font-size:0.72rem;'>"
                            f"⚠️ Risco legal: férias por gozar "
                            f"até final do ano</span>"
                        )

                    st.markdown(
                        f"<div class='rh-card' "
                        f"style='border-left-color:{cor_fer};'>"
                        f"<b style='color:#F1F5F9;'>{nome_c}</b>"
                        f"<span style='float:right;color:{cor_fer};"
                        f"font-weight:700;'>"
                        f"{dias_disponiveis} dias disponíveis</span><br>"
                        f"<div style='background:#0F172A;"
                        f"border-radius:4px;height:6px;margin:6px 0;'>"
                        f"<div style='background:{cor_fer};"
                        f"width:{pct_fer:.0f}%;height:6px;"
                        f"border-radius:4px;'></div></div>"
                        f"<small style='color:#64748B;'>"
                        f"Gozados: {dias_gozados} / "
                        f"{DIAS_FERIAS_ANO} dias · "
                        f"{pct_fer:.0f}%</small><br>"
                        f"{alerta_ven}</div>",
                        unsafe_allow_html=True
                    )

        # Subsídios
        st.markdown("---")
        st.markdown("#### 💰 Subsídios de Férias e Natal")
        st.info(
            f"Sub. Férias — pago normalmente em **junho**, "
            f"antes das férias. "
            f"Sub. Natal — pago até **20 de dezembro**. "
            f"Valor de cada um: 1 mês de salário base."
        )

        if not rh_db.empty:
            mes_sub = st.selectbox(
                "Calcular para mês",
                ["Junho (Sub. Férias)","Dezembro (Sub. Natal)"],
                key="sub_mes_sel"
            )
            col_sub1, col_sub2 = st.columns(2)
            total_sub = 0.0
            for _, colab in rh_db.iterrows():
                sal_s = float(colab.get('Salario_Base',0) or 0)
                total_sub += sal_s

            with col_sub1:
                st.metric(
                    f"💰 Total {mes_sub[:5]}",
                    f"€{total_sub:,.2f}"
                )
            with col_sub2:
                st.metric(
                    "📅 Data de Pagamento",
                    "Junho" if "Férias" in mes_sub else "20 Dezembro"
                )

    # ════════════════════════════════════════════════════════════════
    # TAB — PROVISÕES
    # ════════════════════════════════════════════════════════════════
    with t_prov:
        st.markdown("### 📊 Provisões Obrigatórias")
        st.info(
            "As provisões são reservas mensais para fazer face "
            "às obrigações futuras — subsídios, TSU, seguros. "
            "Devem ser contabilizadas todos os meses."
        )

        if rh_db.empty:
            st.info("📋 Sem fichas para calcular provisões.")
        else:
            col_pv1, col_pv2 = st.columns(2)
            with col_pv1:
                st.plotly_chart(
                    _grafico_provisoes_acumuladas(
                        rh_db, mes_atual, ano_atual
                    ),
                    use_container_width=True
                )
            with col_pv2:
                # Resumo provisões do mês
                st.markdown("#### 📋 Provisões do Mês Atual")
                total_prov_m  = 0.0
                total_tsu_emp = 0.0
                total_seg_a   = 0.0

                for _, colab in rh_db.iterrows():
                    sal = float(colab.get('Salario_Base',0) or 0)
                    c   = _custo_real(sal)
                    total_prov_m  += c['sub_ferias_prov'] + \
                                     c['sub_natal_prov']
                    total_tsu_emp += c['tsu_empresa']
                    total_seg_a   += c['seg_acid_trabalho'] + \
                                     c['fct'] + c['fgct']

                provisoes_lista = [
                    ("📅 Sub. Férias (1/12)",   total_prov_m/2, "#8B5CF6"),
                    ("🎄 Sub. Natal (1/12)",    total_prov_m/2, "#3B82F6"),
                    ("🏛️ TSU Empresa (23.75%)", total_tsu_emp,  "#EF4444"),
                    ("🛡️ Seguros+FCT",          total_seg_a,    "#F59E0B"),
                ]
                total_prov_total = sum(v for _,v,_ in provisoes_lista)

                for label, val, cor in provisoes_lista:
                    st.markdown(
                        f"<div style='display:flex;"
                        f"justify-content:space-between;"
                        f"padding:8px 0;border-bottom:"
                        f"1px solid #1E293B;'>"
                        f"<span style='color:#94A3B8;'>{label}</span>"
                        f"<b style='color:{cor};'>&#8364;{val:.2f}</b></div>",
                        unsafe_allow_html=True
                    )
                st.markdown(
                    f"<div style='display:flex;"
                    f"justify-content:space-between;"
                    f"padding:10px 0;border-top:"
                    f"2px solid #334155;margin-top:4px;'>"
                    f"<b style='color:#F1F5F9;"
                    f"font-size:1rem;'>TOTAL MENSAL</b>"
                    f"<b style='color:#F59E0B;"
                    f"font-size:1.1rem;'>"
                    f"€{total_prov_total:,.2f}</b></div>",
                    unsafe_allow_html=True
                )

                # Botão registar provisão
                if st.button(
                    f"✅ Registar Provisão — "
                    f"{meses_pt[mes_atual-1]} {ano_atual}",
                    key="btn_reg_prov",
                    use_container_width=True
                ):
                    novas_prov = []
                    for _, colab in rh_db.iterrows():
                        sal = float(colab.get('Salario_Base',0) or 0)
                        c   = _custo_real(sal)
                        for tipo, val in [
                            ("Sub.Férias", c['sub_ferias_prov']),
                            ("Sub.Natal",  c['sub_natal_prov']),
                            ("TSU",        c['tsu_empresa']),
                        ]:
                            novas_prov.append({
                                "ID":                str(uuid.uuid4())[:8].upper(),
                                "Colaborador":       colab.get('Nome',''),
                                "Mes":               mes_atual,
                                "Ano":               ano_atual,
                                "Tipo":              tipo,
                                "Valor_Provisionado":val,
                                "Valor_Pago":        0,
                                "Data_Pagamento":    ""
                            })
                    df_prov_n = pd.DataFrame(novas_prov)
                    upd_prov  = pd.concat(
                        [provisoes_db, df_prov_n], ignore_index=True
                    ) if not provisoes_db.empty else df_prov_n
                    save_db(upd_prov, "provisoes_db.csv")
                    inv("provisoes_db.csv")
                    st.success(
                        f"✅ Provisões de "
                        f"{meses_pt[mes_atual-1]} registadas!"
                    )
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — MAPA IRS/SS ANUAL
    # ════════════════════════════════════════════════════════════════
    with t_irs:
        st.markdown("### 📋 Mapa Anual IRS / Segurança Social")
        st.info(
            "Resumo anual para declaração de rendimentos (IRS) "
            "e declaração de remunerações (SS). "
            "Para entregar ao contabilista."
        )

        ano_irs = st.number_input(
            "Ano", min_value=2020, value=ano_atual, key="irs_ano"
        )

        if rh_db.empty:
            st.info("📋 Sem fichas financeiras.")
        else:
            rows_irs = []
            for _, colab in rh_db.iterrows():
                sal  = float(colab.get('Salario_Base',0) or 0)
                ec   = colab.get('Estado_Civil','Solteiro(a)')
                dep  = int(colab.get('N_Dependentes',0) or 0)
                lq   = _liquido(sal, ec, dep)

                # Calcular para 12 meses + subsídios
                rend_anual = sal * 12 + sal  # + sub férias
                # Dezembro tem sub natal
                rend_anual += sal            # + sub natal
                tsu_t_anual = lq['tsu_trabalhador'] * 14  # 14 meses
                irs_anual   = lq['irs'] * 12
                tsu_e_anual = _custo_real(sal)['tsu_empresa'] * 14

                rows_irs.append({
                    "Nome":            colab.get('Nome',''),
                    "NIF":             colab.get('NIF',''),
                    "NISS":            colab.get('NISS',''),
                    "Rendimento Anual":f"€{rend_anual:,.2f}",
                    "TSU Trabalhador": f"€{tsu_t_anual:,.2f}",
                    "IRS Retido":      f"€{irs_anual:,.2f}",
                    "TSU Empresa":     f"€{tsu_e_anual:,.2f}",
                    "Sub.Férias":      f"€{sal:,.2f}",
                    "Sub.Natal":       f"€{sal:,.2f}",
                })

            df_irs = pd.DataFrame(rows_irs)
            st.dataframe(
                df_irs, use_container_width=True, hide_index=True
            )

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                csv_irs = df_irs.to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    f"📥 Export IRS/SS {ano_irs}",
                    data=csv_irs.encode('utf-8-sig'),
                    file_name=f"mapa_irs_ss_{ano_irs}.csv",
                    mime="text/csv",
                    key="dl_irs_ss"
                )
            with col_dl2:
                # DRI Mensal (Declaração Remunerações SS)
                mes_dri = st.selectbox(
                    "Mês DRI",
                    meses_pt,
                    index=mes_atual - 1,
                    key="dri_mes"
                )
                if st.button(
                    f"📋 Gerar DRI — {mes_dri}",
                    key="btn_dri",
                    use_container_width=True
                ):
                    mes_dri_num = meses_pt.index(mes_dri) + 1
                    rows_dri    = []
                    for _, colab in rh_db.iterrows():
                        sal  = float(colab.get('Salario_Base',0) or 0)
                        c    = _custo_real(sal)
                        lq_d = _liquido(sal)
                        rows_dri.append({
                            "Nome":    colab.get('Nome',''),
                            "NISS":    colab.get('NISS',''),
                            "Rend.":   f"€{sal:,.2f}",
                            "TSU Trab":f"€{lq_d['tsu_trabalhador']:,.2f}",
                            "TSU Emp": f"€{c['tsu_empresa']:,.2f}",
                            "Total SS":f"€{lq_d['tsu_trabalhador']+c['tsu_empresa']:,.2f}",
                        })
                    df_dri = pd.DataFrame(rows_dri)
                    total_ss = sum(
                        float(colab.get('Salario_Base',0) or 0) *
                        (TSU_EMPRESA + TSU_TRABALHADOR) / 100
                        for _, colab in rh_db.iterrows()
                    )
                    st.markdown(
                        f"<div style='background:rgba(59,130,246,0.1);"
                        f"border:1px solid #3B82F6;border-radius:8px;"
                        f"padding:12px;margin:8px 0;'>"
                        f"<b style='color:#3B82F6;'>"
                        f"DRI {mes_dri} {ano_irs} — "
                        f"Total SS a pagar: €{total_ss:,.2f}</b><br>"
                        f"<small style='color:#94A3B8;'>"
                        f"Prazo: dia 10 do mês seguinte</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    st.dataframe(
                        df_dri, use_container_width=True, hide_index=True
                    )
                    csv_dri = df_dri.to_csv(
                        index=False, encoding='utf-8-sig'
                    )
                    st.download_button(
                        f"📥 DRI {mes_dri} {ano_irs}",
                        data=csv_dri.encode('utf-8-sig'),
                        file_name=(
                            f"DRI_{mes_dri_num:02d}_{ano_irs}.csv"
                        ),
                        mime="text/csv",
                        key="dl_dri"
                    )

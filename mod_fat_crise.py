"""
GESTNOW v3 — mod_fat_crise.py
Passo 8 — Simulador de Crise & Alertas Antecipados
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, io, os, json
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from core import save_db, inv, load_db

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


# ─────────────────────────────────────────────────────────────────
# MODELO ALTMAN Z-SCORE ADAPTADO PME PORTUGUESA
# ─────────────────────────────────────────────────────────────────

def _altman_z_score(ativo_total: float,
                    passivo_corrente: float,
                    ativo_corrente: float,
                    resultados_retidos: float,
                    ebit: float,
                    capital_proprio: float,
                    passivo_total: float,
                    vendas: float) -> dict:
    """
    Altman Z-Score adaptado para PMEs não cotadas.
    Z' = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4 + 0.998*X5
    """
    if ativo_total <= 0:
        return {
            "z_score":      0,
            "zona":         "indefinida",
            "probabilidade":50,
            "descricao":    "Dados insuficientes"
        }

    capital_circulante = ativo_corrente - passivo_corrente

    x1 = capital_circulante / ativo_total
    x2 = resultados_retidos / ativo_total
    x3 = ebit / ativo_total
    x4 = capital_proprio / passivo_total if passivo_total > 0 else 1
    x5 = vendas / ativo_total

    z = round(
        0.717*x1 + 0.847*x2 + 3.107*x3 +
        0.420*x4 + 0.998*x5, 3
    )

    if z >= 2.9:
        zona         = "saudável"
        prob         = max(2, round((3.5 - z) * 10, 1))
        descricao    = "Empresa financeiramente sólida"
        cor          = "#10B981"
        emoji        = "🟢"
    elif z >= 1.23:
        zona         = "atenção"
        prob         = round(20 + (2.9 - z) * 18, 1)
        descricao    = "Zona cinzenta — monitorizar"
        cor          = "#F59E0B"
        emoji        = "🟡"
    else:
        zona         = "perigo"
        prob         = min(90, round(60 + (1.23 - z) * 20, 1))
        descricao    = "Risco elevado de insolvência"
        cor          = "#EF4444"
        emoji        = "🔴"

    return {
        "z_score":      z,
        "zona":         zona,
        "probabilidade":max(0, min(99, prob)),
        "descricao":    descricao,
        "cor":          cor,
        "emoji":        emoji,
        "x1":           round(x1, 4),
        "x2":           round(x2, 4),
        "x3":           round(x3, 4),
        "x4":           round(x4, 4),
        "x5":           round(x5, 4),
    }


# ─────────────────────────────────────────────────────────────────
# MOTOR DE STRESS TEST
# ─────────────────────────────────────────────────────────────────

def _stress_test(cenario: str,
                 saldo_atual: float,
                 custos_fixos_mes: float,
                 fat_mes: float,
                 a_receber: float,
                 parametros: dict) -> dict:
    """Calcula impacto de cada cenário de crise."""

    resultado = {
        "cenario":        cenario,
        "saldo_inicial":  saldo_atual,
        "custos_mes":     custos_fixos_mes,
        "fat_base":       fat_mes,
    }

    if cenario == "cliente_nao_paga":
        atraso_dias = parametros.get("atraso_dias", 60)
        valor_fat   = parametros.get("valor_fatura", a_receber * 0.6)
        gap         = round(valor_fat, 2)
        meses_crit  = round(gap / custos_fixos_mes, 1) \
                      if custos_fixos_mes > 0 else 99
        saldo_novo  = saldo_atual - gap
        resultado.update({
            "impacto_imediato":  gap,
            "saldo_apos":        round(saldo_novo, 2),
            "meses_autonomia":   round(
                saldo_novo / custos_fixos_mes, 1
            ) if custos_fixos_mes > 0 and saldo_novo > 0 else 0,
            "critico":           saldo_novo < custos_fixos_mes,
            "financiamento_nec": max(0, round(-saldo_novo + custos_fixos_mes * 2, 2)),
            "data_critica":      (
                date.today() + timedelta(days=atraso_dias)
            ).strftime("%d/%m/%Y"),
            "acoes": [
                f"Contactar cliente imediatamente — "
                f"€{gap:,.2f} em dívida",
                "Ativar linha de crédito de curto prazo",
                "Renegociar prazo com fornecedores (+30 dias)",
                "Considerar factoring da fatura em atraso",
                "Reduzir despesas discricionárias"
            ]
        })

    elif cenario == "perda_obra_principal":
        pct_perda  = parametros.get("pct_receita", 0.60)
        fat_perdida = round(fat_mes * pct_perda, 2)
        fat_nova    = fat_mes - fat_perdida
        custo_novo  = custos_fixos_mes * 0.85  # reduz 15% custos variáveis
        resultado.update({
            "fat_perdida":       fat_perdida,
            "fat_nova":          fat_nova,
            "custo_ajustado":    custo_novo,
            "margem_nova":       round(
                (fat_nova - custo_novo) / fat_nova * 100, 1
            ) if fat_nova > 0 else -100,
            "autonomia_meses":   round(
                saldo_atual / (custo_novo - fat_nova), 1
            ) if (custo_novo - fat_nova) > 0 else 99,
            "critico":           fat_nova < custo_novo,
            "break_even_mensal": round(custo_novo, 2),
            "acoes": [
                "Ativar pipeline comercial de imediato",
                f"Break-even requer €{custo_novo:,.0f}/mês "
                f"de nova faturação",
                "Lay-off simplificado para equipa sem alocação",
                "Renegociar contratos de renting",
                "Contactar IEFP e IAPMEI para apoios"
            ]
        })

    elif cenario == "aumento_custos":
        pct_aum_sal  = parametros.get("pct_sal", 0.05)
        pct_aum_comb = parametros.get("pct_comb", 0.20)
        aum_sal      = round(custos_fixos_mes * 0.70 * pct_aum_sal, 2)
        aum_comb     = round(custos_fixos_mes * 0.08 * pct_aum_comb, 2)
        custo_novo   = custos_fixos_mes + aum_sal + aum_comb
        margem_nova  = round(
            (fat_mes - custo_novo) / fat_mes * 100, 1
        ) if fat_mes > 0 else 0
        resultado.update({
            "aumento_sal":       aum_sal,
            "aumento_comb":      aum_comb,
            "custo_novo":        round(custo_novo, 2),
            "aumento_total":     round(aum_sal + aum_comb, 2),
            "margem_nova":       margem_nova,
            "impacto_anual":     round((aum_sal + aum_comb) * 12, 2),
            "critico":           margem_nova < 10,
            "acoes": [
                f"Aumentar preços ao cliente "
                f"+{pct_aum_sal*100:.0f}% para absorver custos",
                "Renegociar contratos de combustível (frota elétrica)",
                "Verificar elegibilidade para apoios à energia",
                "Otimizar rotas para reduzir combustível",
                "Rever mix de contratos (mais valor, menos volume)"
            ]
        })

    elif cenario == "quebra_sazonal":
        pct_quebra  = parametros.get("pct_quebra", 0.35)
        fat_quebra  = round(fat_mes * (1 - pct_quebra), 2)
        meses_crit  = parametros.get("meses_duracao", 2)
        perda_total = round(
            (fat_mes - fat_quebra) * meses_crit, 2
        )
        reserva_nec = round(
            custos_fixos_mes * meses_crit - fat_quebra * meses_crit
            + saldo_atual * 0.3, 2  # manter 30% de reserva
        )
        resultado.update({
            "fat_quebra":       fat_quebra,
            "perda_total":      perda_total,
            "meses_duracao":    meses_crit,
            "reserva_necessaria":max(0, reserva_nec),
            "reserva_atual":    saldo_atual,
            "suficiente":       saldo_atual >= max(0, reserva_nec),
            "deficit":          max(0, reserva_nec - saldo_atual),
            "acoes": [
                f"Constituir reserva de €{max(0,reserva_nec):,.0f} "
                f"antes do período crítico",
                "Antecipar faturação antes da quebra sazonal",
                "Negociar pagamento diferido de salários "
                "em meses críticos",
                "Planear férias coletivas no período baixo",
                "Diversificar setores de cliente para atenuar sazonalidade"
            ]
        })

    elif cenario == "crise_global":
        pct_impacto = parametros.get("pct_impacto", 0.70)
        fat_crisis  = round(fat_mes * (1 - pct_impacto), 2)
        custo_min   = round(custos_fixos_mes * 0.55, 2)
        meses_aguen = round(
            saldo_atual / max(1, custo_min - fat_crisis), 1
        ) if (custo_min - fat_crisis) > 0 else 99
        resultado.update({
            "fat_crisis":        fat_crisis,
            "custo_minimo":      custo_min,
            "meses_aguenta":     meses_aguen,
            "deficit_mensal":    round(
                max(0, custo_min - fat_crisis), 2
            ),
            "critico":           meses_aguen < 3,
            "acoes": [
                "Ativar lay-off simplificado imediatamente",
                "Contactar banco para moratória de créditos",
                "Submeter candidatura urgente IAPMEI/PRR",
                f"Autonomia estimada: {meses_aguen:.1f} meses",
                "Contactar mediador de crédito (Banco de Portugal)"
            ]
        })

    return resultado


# ─────────────────────────────────────────────────────────────────
# BASE DE DADOS DE AJUDA EM CRISE
# ─────────────────────────────────────────────────────────────────

FONTES_AJUDA = [
    {
        "nome":        "IAPMEI — Instituto de Apoio às PME",
        "tipo":        "Estado",
        "valor_max":   "Variável",
        "prazo_resp":  "15-30 dias",
        "descricao":   "Apoios à capitalização, linhas de crédito "
                       "bonificadas, garantias mútuas e consultoria.",
        "contacto":    "808 200 115",
        "url":         "www.iapmei.pt",
        "urgencia":    "média",
        "cor":         "#3B82F6"
    },
    {
        "nome":        "IEFP — Lay-off Simplificado",
        "tipo":        "Estado",
        "valor_max":   "70% salário (máx. 3×SMN)",
        "prazo_resp":  "5-10 dias úteis",
        "descricao":   "Apoio temporário ao emprego em situação "
                       "de crise. Empresa paga 30%, Estado 70%.",
        "contacto":    "300 010 001",
        "url":         "www.iefp.pt",
        "urgencia":    "alta",
        "cor":         "#EF4444"
    },
    {
        "nome":        "Linha PME Crescimento",
        "tipo":        "Banca c/ garantia Estado",
        "valor_max":   "€1.500.000",
        "prazo_resp":  "7-15 dias",
        "descricao":   "Linha de crédito com garantia mútua "
                       "(SPGM/Garval). Juros bonificados, "
                       "carência até 12 meses.",
        "contacto":    "Via banco habitual",
        "url":         "www.spgm.pt",
        "urgencia":    "média",
        "cor":         "#10B981"
    },
    {
        "nome":        "Factoring — Antecipação de Faturas",
        "tipo":        "Banca",
        "valor_max":   "95% do valor das faturas",
        "prazo_resp":  "24-48 horas",
        "descricao":   "Antecipação imediata de faturas emitidas. "
                       "Solução rápida para falta de liquidez. "
                       "Custo ~2-4% ao ano.",
        "contacto":    "Via banco habitual",
        "url":         "—",
        "urgencia":    "alta",
        "cor":         "#F59E0B"
    },
    {
        "nome":        "Mediador de Crédito (Banco de Portugal)",
        "tipo":        "Estado",
        "valor_max":   "N/A (mediação)",
        "prazo_resp":  "Imediato",
        "descricao":   "Mediação gratuita entre empresa e banco "
                       "em situação de incumprimento ou risco. "
                       "Confidencial.",
        "contacto":    "213 130 000",
        "url":         "www.bportugal.pt/mediador-credito",
        "urgencia":    "crítica",
        "cor":         "#DC2626"
    },
    {
        "nome":        "Norgarante / Garval / Lisgarante",
        "tipo":        "Garantia Mútua",
        "valor_max":   "€1.500.000",
        "prazo_resp":  "10-20 dias",
        "descricao":   "Sociedades de garantia mútua. "
                       "Facilitam acesso a crédito bancário "
                       "sem colateral imobiliário.",
        "contacto":    "Via IAPMEI ou banco",
        "url":         "www.spgm.pt",
        "urgencia":    "média",
        "cor":         "#8B5CF6"
    },
    {
        "nome":        "PRR — Plano de Recuperação e Resiliência",
        "tipo":        "Fundos UE",
        "valor_max":   "Até 80% do investimento",
        "prazo_resp":  "30-90 dias",
        "descricao":   "Candidaturas abertas para PMEs. "
                       "Subvenções a fundo perdido para "
                       "inovação, digitalização e capitalização.",
        "contacto":    "Via IAPMEI",
        "url":         "www.recuperarportugal.gov.pt",
        "urgencia":    "baixa",
        "cor":         "#06B6D4"
    },
    {
        "nome":        "APOIAR.PT — Programa de Apoio",
        "tipo":        "Estado",
        "valor_max":   "€750.000",
        "prazo_resp":  "5-10 dias",
        "descricao":   "Subsídio não reembolsável para empresas "
                       "afetadas por crises. "
                       "Cobre custos fixos e salários.",
        "contacto":    "Via IAPMEI / CCDR",
        "url":         "www.iapmei.pt/apoiar",
        "urgencia":    "alta",
        "cor":         "#EF4444"
    },
]


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_gauge_saude(score: int, titulo: str):
    """Gauge de saúde financeira."""
    cor = "#10B981" if score >= 70 \
          else "#F59E0B" if score >= 40 \
          else "#EF4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={'text':titulo, 'font':{'color':'#F1F5F9','size':13}},
        gauge={
            'axis':{'range':[0,100],'tickcolor':'#64748B'},
            'bar':{'color':cor},
            'bgcolor':'#1E293B',
            'bordercolor':'#334155',
            'steps':[
                {'range':[0,40],  'color':'rgba(239,68,68,0.15)'},
                {'range':[40,70], 'color':'rgba(245,158,11,0.15)'},
                {'range':[70,100],'color':'rgba(16,185,129,0.15)'},
            ],
            'threshold':{
                'line':{'color':'#F1F5F9','width':2},
                'thickness':0.75,'value':score
            }
        },
        number={'font':{'color':'#F1F5F9','size':28}}
    ))
    fig.update_layout(
        height=200,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        margin=dict(t=40,b=10,l=20,r=20)
    )
    return fig


def _grafico_autonomia_gauge(meses: float):
    """Gauge de autonomia financeira."""
    score = min(100, round(meses / 12 * 100))
    return _grafico_gauge_saude(score, f"Autonomia: {meses:.1f} meses")


def _grafico_cenario_cashflow(saldo_ini: float,
                               fat_mes: float,
                               custo_mes: float,
                               fat_cenario: float,
                               custo_cenario: float,
                               meses: int = 6,
                               label_base: str = "Base",
                               label_cen: str = "Cenário Crise"):
    """Line chart comparação cash flow base vs cenário."""
    labels = [f"M{i}" for i in range(meses + 1)]

    # Base
    sal_b = [saldo_ini]
    for _ in range(meses):
        sal_b.append(round(sal_b[-1] + fat_mes - custo_mes, 2))

    # Cenário
    sal_c = [saldo_ini]
    for _ in range(meses):
        sal_c.append(round(sal_c[-1] + fat_cenario - custo_cenario, 2))

    fig = go.Figure()

    # Zona perigo
    fig.add_hrect(
        y0=-999999, y1=0,
        fillcolor='rgba(239,68,68,0.08)',
        line_width=0
    )

    fig.add_trace(go.Scatter(
        x=labels, y=sal_b,
        mode='lines+markers',
        name=label_base,
        line={'color':'#10B981','width':3,'dash':'solid'},
        marker={'size':8},
        fill='tozeroy',
        fillcolor='rgba(16,185,129,0.05)',
        hovertemplate='%{x}<br>Base: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=sal_c,
        mode='lines+markers',
        name=label_cen,
        line={'color':'#EF4444','width':3,'dash':'dash'},
        marker={'size':8,'symbol':'diamond'},
        fill='tozeroy',
        fillcolor='rgba(239,68,68,0.05)',
        hovertemplate='%{x}<br>Crise: €%{y:,.2f}<extra></extra>'
    ))

    # Linha zero
    fig.add_hline(
        y=0, line_dash="solid",
        line_color="#334155", line_width=1,
        annotation_text="Break-even",
        annotation_font_color="#64748B"
    )

    fig.update_layout(
        title={'text':'Projeção Cash Flow — Base vs Cenário',
               'font':{'color':'#F1F5F9'}},
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'title':{'text':'Meses',
                        'font':{'color':'#94A3B8'}}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=30,l=60,r=10),
        hovermode='x unified'
    )
    return fig


def _grafico_semaforo_indicadores(indicadores: list):
    """Gráfico de semáforo com todos os indicadores."""
    nomes  = [i['nome']  for i in indicadores]
    scores = [i['score'] for i in indicadores]
    cores  = ['#10B981' if s >= 70
              else '#F59E0B' if s >= 40
              else '#EF4444'
              for s in scores]

    fig = go.Figure(go.Bar(
        x=scores, y=nomes,
        orientation='h',
        marker_color=cores,
        text=[f"{s}" for s in scores],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':11},
        hovertemplate='%{y}: %{x}/100<extra></extra>'
    ))
    fig.add_vline(
        x=40, line_dash="dash",
        line_color="#F59E0B", line_width=1,
        annotation_text="Atenção",
        annotation_font_color="#F59E0B"
    )
    fig.add_vline(
        x=70, line_dash="dash",
        line_color="#10B981", line_width=1,
        annotation_text="Saudável",
        annotation_font_color="#10B981"
    )
    fig.update_layout(
        title={'text':'Indicadores de Saúde Financeira',
               'font':{'color':'#F1F5F9'}},
        height=max(200, len(indicadores)*45 + 60),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'range':[0,120]},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=150,r=60),
        showlegend=False
    )
    return fig


def _grafico_waterfall_altman(altman: dict):
    """Waterfall das componentes do Z-Score."""
    componentes = ['X1 (Liquidez)', 'X2 (Rent.Acum)',
                   'X3 (EBIT/Ativo)', 'X4 (Cap.Prp/Pass)',
                   'X5 (Vendas/Ativo)']
    pesos       = [0.717, 0.847, 3.107, 0.420, 0.998]
    xvals       = [
        altman.get('x1',0), altman.get('x2',0),
        altman.get('x3',0), altman.get('x4',0),
        altman.get('x5',0)
    ]
    contribuicoes = [round(p*x, 3) for p, x in zip(pesos, xvals)]

    fig = go.Figure(go.Waterfall(
        name="Z-Score",
        orientation="v",
        measure=["relative"]*5 + ["total"],
        x=componentes + ["Z-Score Total"],
        y=contribuicoes + [0],
        text=[f"{c:.3f}" for c in contribuicoes] +
             [f"{altman.get('z_score',0):.3f}"],
        textposition="outside",
        textfont={"color":"#F1F5F9","size":9},
        connector={"line":{"color":"#334155"}},
        increasing={"marker":{"color":"#10B981"}},
        decreasing={"marker":{"color":"#EF4444"}},
        totals={"marker":{
            "color": altman.get('cor','#6B7280')
        }}
    ))

    # Linhas de referência
    fig.add_hline(
        y=2.9, line_dash="dot",
        line_color="#10B981", line_width=1,
        annotation_text="Saudável (2.9)",
        annotation_font_color="#10B981"
    )
    fig.add_hline(
        y=1.23, line_dash="dot",
        line_color="#EF4444", line_width=1,
        annotation_text="Perigo (1.23)",
        annotation_font_color="#EF4444"
    )

    fig.update_layout(
        title={'text':'Componentes Altman Z-Score',
               'font':{'color':'#F1F5F9'}},
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF PLANO DE CONTINGÊNCIA
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_contingencia(score_global: int,
                             nivel: str,
                             indicadores: list,
                             acoes: list,
                             fontes_ativas: list,
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
        fontSize=8, textColor=colors.HexColor('#64748B'), spaceAfter=2
    )
    normal_s = ParagraphStyle(
        'normal', parent=styles['Normal'],
        fontSize=9, spaceAfter=3
    )

    cor_map = {
        "🟢 SAUDÁVEL":   '#10B981',
        "🟡 ATENÇÃO":    '#F59E0B',
        "🔴 ALERTA":     '#EF4444',
        "🆘 CRISE":      '#DC2626',
    }
    cor_nivel = cor_map.get(nivel, '#64748B')

    # Header
    story.append(Paragraph(
        "PLANO DE CONTINGÊNCIA FINANCEIRA",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=18, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'),
                       spaceAfter=6)
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

    # Nível de crise
    story.append(Paragraph(
        f"Nível Atual: {nivel} | Score: {score_global}/100",
        ParagraphStyle('nivel', parent=styles['Normal'],
                       fontSize=14, fontName='Helvetica-Bold',
                       textColor=colors.HexColor(cor_nivel),
                       spaceAfter=6)
    ))
    story.append(Spacer(1, 0.2*cm))

    # Indicadores
    story.append(Paragraph("<b>INDICADORES DE SAÚDE</b>", bold_s))
    ind_data = [["Indicador","Score","Status"]]
    for ind in indicadores:
        sc  = ind['score']
        st  = "🟢 OK" if sc >= 70 \
              else "🟡 Atenção" if sc >= 40 \
              else "🔴 Risco"
        ind_data.append([ind['nome'], f"{sc}/100", st])

    it = Table(ind_data, colWidths=[8*cm, 3*cm, 6*cm])
    it.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,0),  colors.HexColor('#1E293B')),
        ('TEXTCOLOR',  (0,0),(-1,0),  colors.white),
        ('FONTNAME',   (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',   (0,0),(-1,-1), 9),
        ('GRID',       (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(it)
    story.append(Spacer(1, 0.4*cm))

    # Ações prioritárias
    story.append(Paragraph(
        "<b>AÇÕES PRIORITÁRIAS IMEDIATAS</b>", bold_s
    ))
    for i, acao in enumerate(acoes, 1):
        story.append(Paragraph(
            f"{i}. {acao}", normal_s
        ))
    story.append(Spacer(1, 0.4*cm))

    # Fontes de ajuda
    if fontes_ativas:
        story.append(Paragraph(
            "<b>FONTES DE AJUDA DISPONÍVEIS</b>", bold_s
        ))
        fonte_data = [["Entidade","Tipo","Valor Máx","Contacto"]]
        for f in fontes_ativas:
            fonte_data.append([
                f['nome'][:30],
                f['tipo'],
                f['valor_max'],
                f['contacto']
            ])
        ft = Table(
            fonte_data,
            colWidths=[6*cm, 3*cm, 3.5*cm, 4.5*cm]
        )
        ft.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,0),  colors.HexColor('#1E293B')),
            ('TEXTCOLOR',  (0,0),(-1,0),  colors.white),
            ('FONTNAME',   (0,0),(-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',   (0,0),(-1,-1), 8),
            ('GRID',       (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),
             [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0,0),(-1,-1), 4),
            ('BOTTOMPADDING',(0,0),(-1,-1), 4),
            ('LEFTPADDING', (0,0),(-1,-1), 6),
        ]))
        story.append(ft)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"GESTNOW v3.0 | "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_crise(obras_db, registos_db,
                     faturas_db, diarias_pag_db, *_):
    """Módulo Simulador de Crise & Alertas Antecipados."""

    # ── Carregar dados ────────────────────────────────────────────
    faturas_cli  = _load("faturas_clientes.csv", [
        "ID","Numero","Data_Emissao","Data_Vencimento",
        "Cliente","Obra","Total","Estado"
    ])
    faturas_forn = _load("faturas_fornecedores.csv",
                         ["ID","Total","Estado"])
    contas_db    = _load("contas_bancarias.csv",
                         ["ID","Nome","Banco","Saldo"])
    rh_db        = _load("colaboradores_rh.csv",
                         ["Nome","Salario_Base"])
    renting_db   = _load("renting_contratos.csv",
                         ["ID","Valor_Mensal","Estado","Data_Fim"])
    seguros_db   = _load("seguros_db.csv",
                         ["ID","Tipo","Data_Fim","Valor_Anual"])
    alvaras_db   = _load("alvaras_db.csv",
                         ["ID","Tipo","Data_Validade"])
    iban_hist    = _load("iban_historico.csv",
                         ["ID","Data_Alteracao","Entidade"])

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

    # ── Calcular métricas base ────────────────────────────────────
    saldo_atual = pd.to_numeric(
        contas_db.get('Saldo', pd.Series()), errors='coerce'
    ).fillna(0).sum() if not contas_db.empty else 0.0

    custo_sal_mes = 0.0
    if not rh_db.empty and 'Salario_Base' in rh_db.columns:
        custo_sal_mes = pd.to_numeric(
            rh_db['Salario_Base'], errors='coerce'
        ).fillna(0).sum() * 1.2375

    renda_mes = 0.0
    if not renting_db.empty and 'Valor_Mensal' in renting_db.columns:
        at = renting_db[
            renting_db.get('Estado','') != 'Terminado'
        ] if 'Estado' in renting_db.columns else renting_db
        renda_mes = pd.to_numeric(
            at['Valor_Mensal'], errors='coerce'
        ).fillna(0).sum()

    custos_fixos_mes = custo_sal_mes + renda_mes

    fat_mes = 0.0
    if not faturas_cli.empty and 'Data_Emissao' in faturas_cli.columns:
        fc = faturas_cli.copy()
        fc['Data_d'] = pd.to_datetime(
            fc['Data_Emissao'], dayfirst=True, errors='coerce'
        )
        fc['Total_Num'] = pd.to_numeric(
            fc.get('Total',0), errors='coerce'
        ).fillna(0)
        mask_m = (
            (fc['Data_d'].dt.month == hoje.month) &
            (fc['Data_d'].dt.year  == hoje.year)
        )
        fat_mes = fc[mask_m]['Total_Num'].sum()

    a_receber = 0.0
    if not faturas_cli.empty and 'Estado' in faturas_cli.columns:
        nao_pagas = faturas_cli[
            ~faturas_cli['Estado'].isin(['Paga','Anulada'])
        ]
        a_receber = pd.to_numeric(
            nao_pagas.get('Total',0), errors='coerce'
        ).fillna(0).sum()

    autonomia = round(
        saldo_atual / custos_fixos_mes, 1
    ) if custos_fixos_mes > 0 else 99.0

    # Faturas vencidas
    fat_venc = 0
    if not faturas_cli.empty and 'Data_Vencimento' in faturas_cli.columns:
        fc2 = faturas_cli.copy()
        fc2['Venc_d'] = pd.to_datetime(
            fc2['Data_Vencimento'], dayfirst=True, errors='coerce'
        )
        fat_venc = len(fc2[
            (fc2['Venc_d'] < pd.Timestamp(hoje)) &
            (~fc2.get('Estado','').isin(['Paga','Anulada']))
        ]) if 'Estado' in fc2.columns else 0

    # Concentração de clientes
    conc_cliente = 0.0
    if not faturas_cli.empty and 'Cliente' in faturas_cli.columns:
        fc3 = faturas_cli.copy()
        fc3['Total_Num'] = pd.to_numeric(
            fc3.get('Total',0), errors='coerce'
        ).fillna(0)
        grp = fc3.groupby('Cliente')['Total_Num'].sum()
        if grp.sum() > 0:
            conc_cliente = round(grp.max() / grp.sum() * 100, 1)

    # Margem estimada
    margem_pct = round(
        (fat_mes - custos_fixos_mes) / fat_mes * 100, 1
    ) if fat_mes > 0 else 0.0

    # ── Score global de saúde ─────────────────────────────────────
    indicadores = [
        {
            "nome":  "Autonomia Financeira",
            "score": min(100, round(autonomia / 6 * 100)),
            "valor": f"{autonomia:.1f} meses",
            "ok":    autonomia >= 3
        },
        {
            "nome":  "Margem Operacional",
            "score": min(100, max(0, round(margem_pct * 2.5))),
            "valor": f"{margem_pct:.1f}%",
            "ok":    margem_pct >= 20
        },
        {
            "nome":  "Faturas Vencidas",
            "score": max(0, 100 - fat_venc * 20),
            "valor": f"{fat_venc} fat.",
            "ok":    fat_venc == 0
        },
        {
            "nome":  "Concentração Clientes",
            "score": max(0, 100 - round(max(0, conc_cliente - 30) * 2)),
            "valor": f"{conc_cliente:.0f}% top cliente",
            "ok":    conc_cliente <= 50
        },
        {
            "nome":  "Cobertura Custos Fixos",
            "score": min(100, round(fat_mes / max(1, custos_fixos_mes) * 60)),
            "valor": f"€{fat_mes:,.0f} / €{custos_fixos_mes:,.0f}",
            "ok":    fat_mes >= custos_fixos_mes
        },
        {
            "nome":  "Saldo Bancário",
            "score": min(100, round(saldo_atual / max(1, custos_fixos_mes) * 40)),
            "valor": f"€{saldo_atual:,.2f}",
            "ok":    saldo_atual >= custos_fixos_mes
        },
    ]

    score_global = round(
        sum(i['score'] for i in indicadores) / len(indicadores)
    )

    # Nível de alerta
    if score_global >= 70:
        nivel      = "🟢 SAUDÁVEL"
        cor_nivel  = "#10B981"
        nivel_desc = "Empresa em boa situação financeira."
    elif score_global >= 50:
        nivel      = "🟡 ATENÇÃO"
        cor_nivel  = "#F59E0B"
        nivel_desc = "Monitorizar de perto. Alguns indicadores em risco."
    elif score_global >= 30:
        nivel      = "🔴 ALERTA"
        cor_nivel  = "#EF4444"
        nivel_desc = "Ação corretiva necessária com urgência."
    else:
        nivel      = "🆘 CRISE"
        cor_nivel  = "#DC2626"
        nivel_desc = "ATIVAR PLANO DE CONTINGÊNCIA IMEDIATAMENTE!"

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .crise-card {
        background:#1E293B; border-radius:12px;
        padding:16px; margin-bottom:10px;
    }
    .fonte-card {
        background:#1E293B; border-radius:10px;
        padding:14px; margin-bottom:8px;
        border-left:4px solid;
        transition:transform 0.15s;
    }
    .fonte-card:hover { transform:translateX(3px); }
    .acao-item {
        background:rgba(30,41,59,0.8);
        border-radius:8px; padding:10px 14px;
        margin-bottom:6px;
        border-left:3px solid #3B82F6;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header nível de alerta ────────────────────────────────────
    st.markdown(
        f"<div style='background:{cor_nivel}18;"
        f"border:2px solid {cor_nivel};"
        f"border-radius:16px;padding:20px;"
        f"margin-bottom:20px;'>"
        f"<div style='display:flex;"
        f"justify-content:space-between;align-items:center;'>"
        f"<div>"
        f"<h2 style='color:{cor_nivel};margin:0;"
        f"font-size:1.8rem;'>{nivel}</h2>"
        f"<p style='color:#94A3B8;margin:4px 0 0;'>"
        f"{nivel_desc}</p>"
        f"</div>"
        f"<div style='text-align:center;"
        f"background:{cor_nivel}22;border-radius:50%;"
        f"width:80px;height:80px;display:flex;"
        f"align-items:center;justify-content:center;"
        f"border:3px solid {cor_nivel};'>"
        f"<b style='color:{cor_nivel};font-size:1.8rem;'>"
        f"{score_global}</b>"
        f"</div></div></div>",
        unsafe_allow_html=True
    )

    # ── KPIs ──────────────────────────────────────────────────────
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("🏦 Saldo",         f"€{saldo_atual:,.2f}")
    with c2: st.metric("📅 Autonomia",      f"{autonomia:.1f}m")
    with c3: st.metric("📈 Margem",         f"{margem_pct:.1f}%")
    with c4: st.metric("🔴 Fat. Vencidas",  fat_venc)
    with c5: st.metric("🎯 Score Saúde",    f"{score_global}/100")

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_semaforo, t_stress, t_simulador,
     t_altman, t_ajuda, t_contingencia) = st.tabs([
        "🚦 Semáforo",
        "⚡ Stress Tests",
        "🎛️ Simulador E-se?",
        "📐 Altman Z-Score",
        "🆘 Fontes de Ajuda",
        "📋 Plano Contingência",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — SEMÁFORO DE SAÚDE
    # ════════════════════════════════════════════════════════════════
    with t_semaforo:
        st.markdown("### 🚦 Semáforo de Saúde Financeira")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(
                _grafico_gauge_saude(
                    score_global, "Score Global"
                ),
                use_container_width=True
            )
        with col_g2:
            st.plotly_chart(
                _grafico_autonomia_gauge(autonomia),
                use_container_width=True
            )

        # Gráfico indicadores
        st.plotly_chart(
            _grafico_semaforo_indicadores(indicadores),
            use_container_width=True
        )

        # Cards por indicador
        st.markdown("#### 📊 Detalhe dos Indicadores")
        cols_ind = st.columns(3)
        for i, ind in enumerate(indicadores):
            with cols_ind[i % 3]:
                sc  = ind['score']
                cor_i = "#10B981" if sc >= 70 \
                        else "#F59E0B" if sc >= 40 \
                        else "#EF4444"
                ic_i  = "🟢" if sc >= 70 \
                        else "🟡" if sc >= 40 \
                        else "🔴"
                # Barra progresso
                st.markdown(
                    f"<div class='crise-card' "
                    f"style='border-top:3px solid {cor_i};'>"
                    f"<p style='color:#64748B;"
                    f"font-size:0.72rem;font-weight:700;"
                    f"text-transform:uppercase;"
                    f"margin:0 0 4px;'>"
                    f"{ind['nome']}</p>"
                    f"<div style='display:flex;"
                    f"justify-content:space-between;"
                    f"align-items:center;margin-bottom:6px;'>"
                    f"<b style='color:{cor_i};"
                    f"font-size:1.2rem;'>"
                    f"{ic_i} {sc}/100</b>"
                    f"<small style='color:#94A3B8;'>"
                    f"{ind['valor']}</small>"
                    f"</div>"
                    f"<div style='background:#0F172A;"
                    f"border-radius:4px;height:8px;'>"
                    f"<div style='background:{cor_i};"
                    f"width:{sc}%;height:8px;"
                    f"border-radius:4px;transition:width 0.5s;'>"
                    f"</div></div>"
                    f"<small style='color:#475569;"
                    f"font-size:0.7rem;'>"
                    f"{'✅ OK' if ind['ok'] else '⚠️ Atenção'}"
                    f"</small></div>",
                    unsafe_allow_html=True
                )

        # Alertas ativos
        alertas_ativos = [i for i in indicadores if not i['ok']]
        if alertas_ativos:
            st.markdown("---")
            st.markdown("#### ⚡ Alertas Ativos")
            for al in alertas_ativos:
                sc_a  = al['score']
                cor_a = "#F59E0B" if sc_a >= 40 else "#EF4444"
                st.markdown(
                    f"<div style='background:{cor_a}12;"
                    f"border-left:4px solid {cor_a};"
                    f"border-radius:8px;padding:10px 14px;"
                    f"margin-bottom:6px;'>"
                    f"<b style='color:{cor_a};'>"
                    f"⚠️ {al['nome']}</b> — "
                    f"<span style='color:#94A3B8;'>"
                    f"{al['valor']}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # Outros alertas operacionais
        st.markdown("---")
        st.markdown("#### 🔔 Alertas Operacionais")

        alertas_op = []

        # Seguros a expirar
        if not seguros_db.empty and 'Data_Fim' in seguros_db.columns:
            seg_exp = seguros_db.copy()
            seg_exp['Fim_d'] = pd.to_datetime(
                seg_exp['Data_Fim'], dayfirst=True, errors='coerce'
            )
            prox_seg = seg_exp[
                seg_exp['Fim_d'] <= pd.Timestamp(
                    hoje + timedelta(days=60)
                )
            ]
            if not prox_seg.empty:
                alertas_op.append({
                    "msg": f"🛡️ {len(prox_seg)} seguro(s) "
                           f"a expirar em 60 dias",
                    "cor": "#F59E0B"
                })

        # Alvarás a expirar
        if not alvaras_db.empty and \
           'Data_Validade' in alvaras_db.columns:
            alv_exp = alvaras_db.copy()
            alv_exp['Val_d'] = pd.to_datetime(
                alv_exp['Data_Validade'], dayfirst=True, errors='coerce'
            )
            prox_alv = alv_exp[
                alv_exp['Val_d'] <= pd.Timestamp(
                    hoje + timedelta(days=90)
                )
            ]
            if not prox_alv.empty:
                alertas_op.append({
                    "msg": f"📋 {len(prox_alv)} alvará(s)/licença(s) "
                           f"a expirar em 90 dias",
                    "cor": "#EF4444"
                })

        # IBANs alterados recentemente
        if not iban_hist.empty and \
           'Data_Alteracao' in iban_hist.columns:
            ih = iban_hist.copy()
            ih['Alt_d'] = pd.to_datetime(
                ih['Data_Alteracao'], dayfirst=True, errors='coerce'
            )
            rec_iban = ih[
                ih['Alt_d'] >= pd.Timestamp(
                    hoje - timedelta(days=30)
                )
            ]
            if not rec_iban.empty:
                alertas_op.append({
                    "msg": f"🏦 {len(rec_iban)} IBAN(s) alterado(s) "
                           f"nos últimos 30 dias",
                    "cor": "#EF4444"
                })

        # Renting a terminar
        if not renting_db.empty and 'Data_Fim' in renting_db.columns:
            rent_exp = renting_db.copy()
            rent_exp['Fim_d'] = pd.to_datetime(
                rent_exp['Data_Fim'], dayfirst=True, errors='coerce'
            )
            prox_rent = rent_exp[
                rent_exp['Fim_d'] <= pd.Timestamp(
                    hoje + timedelta(days=60)
                )
            ]
            if not prox_rent.empty:
                alertas_op.append({
                    "msg": f"🚗 {len(prox_rent)} contrato(s) renting "
                           f"a terminar em 60 dias",
                    "cor": "#F59E0B"
                })

        if alertas_op:
            for alop in alertas_op:
                st.markdown(
                    f"<div style='background:{alop['cor']}12;"
                    f"border-left:4px solid {alop['cor']};"
                    f"border-radius:8px;padding:10px 14px;"
                    f"margin-bottom:6px;'>"
                    f"<span style='color:{alop['cor']};'>"
                    f"{alop['msg']}</span></div>",
                    unsafe_allow_html=True
                )
        else:
            st.success("✅ Sem alertas operacionais.")

    # ════════════════════════════════════════════════════════════════
    # TAB — STRESS TESTS
    # ════════════════════════════════════════════════════════════════
    with t_stress:
        st.markdown("### ⚡ Stress Tests — 5 Cenários")
        st.info(
            "Cada cenário simula um choque financeiro e calcula "
            "o impacto real no cash flow e saldo da empresa."
        )

        cenarios_config = [
            {
                "id":     "cliente_nao_paga",
                "titulo": "📭 Cliente Não Paga",
                "desc":   "O principal cliente atrasa o pagamento",
                "cor":    "#F59E0B",
                "params": {
                    "atraso_dias": st.session_state.get(
                        "st_atraso", 60
                    ),
                    "valor_fatura": a_receber * 0.6
                }
            },
            {
                "id":     "perda_obra_principal",
                "titulo": "🏗️ Perda de Obra Principal",
                "desc":   "A obra mais importante é cancelada",
                "cor":    "#EF4444",
                "params": {"pct_receita": 0.60}
            },
            {
                "id":     "aumento_custos",
                "titulo": "📈 Aumento de Custos",
                "desc":   "Salários +5% e combustível +20%",
                "cor":    "#8B5CF6",
                "params": {"pct_sal":0.05,"pct_comb":0.20}
            },
            {
                "id":     "quebra_sazonal",
                "titulo": "📉 Quebra Sazonal",
                "desc":   "Quebra de 35% durante 2 meses (verão)",
                "cor":    "#3B82F6",
                "params": {"pct_quebra":0.35,"meses_duracao":2}
            },
            {
                "id":     "crise_global",
                "titulo": "🌍 Crise Global",
                "desc":   "Quebra de 70% de faturação (COVID-like)",
                "cor":    "#DC2626",
                "params": {"pct_impacto":0.70}
            },
        ]

        for cen in cenarios_config:
            res = _stress_test(
                cen['id'], saldo_atual, custos_fixos_mes,
                fat_mes if fat_mes > 0 else custos_fixos_mes * 1.3,
                a_receber, cen['params']
            )

            cor_c = cen['cor']
            critico = res.get('critico', False)
            cor_c2  = "#EF4444" if critico else "#10B981"

            with st.expander(
                f"{cen['titulo']} — {cen['desc']}",
                expanded=critico
            ):
                col_s1, col_s2 = st.columns([1, 2])

                with col_s1:
                    st.markdown(
                        f"<div class='crise-card' "
                        f"style='border-left:4px solid {cor_c};'>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:1rem;'>{cen['titulo']}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"{cen['desc']}</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    # Métricas específicas por cenário
                    if cen['id'] == 'cliente_nao_paga':
                        st.metric(
                            "💸 Gap de Cash Flow",
                            f"€{res.get('impacto_imediato',0):,.2f}"
                        )
                        st.metric(
                            "🏦 Saldo Após Impacto",
                            f"€{res.get('saldo_apos',0):,.2f}",
                            delta=f"{'🔴 Crítico' if critico else '🟢 OK'}"
                        )
                        if res.get('financiamento_nec',0) > 0:
                            st.error(
                                f"💰 Financiamento necessário: "
                                f"€{res.get('financiamento_nec',0):,.2f}"
                            )

                    elif cen['id'] == 'perda_obra_principal':
                        st.metric(
                            "📉 Receita Perdida/Mês",
                            f"€{res.get('fat_perdida',0):,.2f}"
                        )
                        m_nova = res.get('margem_nova',0)
                        st.metric(
                            "📈 Margem Nova",
                            f"{m_nova:.1f}%",
                            delta="🔴 Negativa" if m_nova < 0
                            else f"↓ {margem_pct-m_nova:.1f}%"
                        )
                        st.metric(
                            "📅 Autonomia Restante",
                            f"{res.get('autonomia_meses',0):.1f} meses"
                        )

                    elif cen['id'] == 'aumento_custos':
                        st.metric(
                            "💸 Aumento Mensal",
                            f"€{res.get('aumento_total',0):,.2f}"
                        )
                        st.metric(
                            "📈 Margem Nova",
                            f"{res.get('margem_nova',0):.1f}%"
                        )
                        st.metric(
                            "💸 Impacto Anual",
                            f"€{res.get('impacto_anual',0):,.2f}"
                        )

                    elif cen['id'] == 'quebra_sazonal':
                        suf = res.get('suficiente', False)
                        st.metric(
                            "💰 Reserva Necessária",
                            f"€{res.get('reserva_necessaria',0):,.2f}"
                        )
                        st.metric(
                            "🏦 Reserva Atual",
                            f"€{res.get('reserva_atual',0):,.2f}",
                            delta="✅ Suficiente" if suf
                            else f"❌ Déficit €{res.get('deficit',0):,.2f}"
                        )

                    elif cen['id'] == 'crise_global':
                        st.metric(
                            "📅 Meses que Aguenta",
                            f"{res.get('meses_aguenta',0):.1f}"
                        )
                        st.metric(
                            "💸 Déficit Mensal",
                            f"€{res.get('deficit_mensal',0):,.2f}"
                        )

                    # Badge crítico/ok
                    st.markdown(
                        f"<div style='background:{cor_c2}18;"
                        f"border:1px solid {cor_c2};"
                        f"border-radius:8px;padding:8px;"
                        f"text-align:center;margin-top:8px;'>"
                        f"<b style='color:{cor_c2};'>"
                        f"{'🔴 CENÁRIO CRÍTICO' if critico else '🟢 Manejável'}"
                        f"</b></div>",
                        unsafe_allow_html=True
                    )

                with col_s2:
                    # Gráfico projeção
                    fat_cen = fat_mes * (
                        1 - cen['params'].get('pct_receita',0) -
                        cen['params'].get('pct_impacto',0) -
                        cen['params'].get('pct_quebra',0)
                    ) if cen['id'] in [
                        'perda_obra_principal',
                        'crise_global', 'quebra_sazonal'
                    ] else fat_mes

                    cust_cen = custos_fixos_mes * (
                        1 + cen['params'].get('pct_sal',0) * 0.7 +
                        cen['params'].get('pct_comb',0) * 0.08
                    ) if cen['id'] == 'aumento_custos' \
                      else custos_fixos_mes

                    st.plotly_chart(
                        _grafico_cenario_cashflow(
                            saldo_atual,
                            fat_mes if fat_mes > 0
                            else custos_fixos_mes * 1.3,
                            custos_fixos_mes,
                            max(0, fat_cen),
                            cust_cen,
                            meses=6,
                            label_base="Situação Atual",
                            label_cen=cen['titulo']
                        ),
                        use_container_width=True
                    )

                    # Ações recomendadas
                    st.markdown(
                        "<p style='color:#64748B;"
                        "font-size:0.8rem;font-weight:700;"
                        "text-transform:uppercase;"
                        "margin:8px 0 6px;'>Ações Recomendadas:</p>",
                        unsafe_allow_html=True
                    )
                    for j, acao in enumerate(
                        res.get('acoes',[]), 1
                    ):
                        st.markdown(
                            f"<div class='acao-item'>"
                            f"<small style='color:#3B82F6;"
                            f"font-weight:700;'>{j}.</small>"
                            f"<small style='color:#E2E8F0;"
                            f"margin-left:6px;'>{acao}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

    # ════════════════════════════════════════════════════════════════
    # TAB — SIMULADOR E-SE?
    # ════════════════════════════════════════════════════════════════
    with t_simulador:
        st.markdown("### 🎛️ Simulador Interativo — E se?")
        st.info(
            "Ajusta os sliders e vê o impacto em tempo real "
            "no saldo e na margem da empresa."
        )

        col_sl1, col_sl2 = st.columns(2)
        with col_sl1:
            st.markdown("#### 📉 Choques Negativos")
            pct_fat_reduz = st.slider(
                "Redução de faturação (%)",
                0, 90, 0, 5, key="sim_fat"
            )
            pct_aum_sal = st.slider(
                "Aumento de salários (%)",
                0, 30, 0, 1, key="sim_sal"
            )
            atraso_rec = st.slider(
                "Atraso médio de recebimento (dias)",
                0, 120, 30, 10, key="sim_atraso"
            )
            perda_obras = st.slider(
                "N.º obras perdidas",
                0, max(1, len(obras_db) if not obras_db.empty else 5),
                0, 1, key="sim_obras"
            )

        with col_sl2:
            st.markdown("#### 📈 Melhorias")
            pct_fat_aum = st.slider(
                "Aumento de faturação (%)",
                0, 100, 0, 5, key="sim_fat_aum"
            )
            red_custos = st.slider(
                "Redução de custos fixos (%)",
                0, 40, 0, 2, key="sim_red_cust"
            )
            nova_obra_val = st.number_input(
                "Receita de nova obra (€/mês)",
                min_value=0.0, value=0.0,
                step=1000.0, key="sim_nova_obra"
            )
            fat_antecip = st.number_input(
                "Antecipação de faturas (factoring €)",
                min_value=0.0, value=0.0,
                step=1000.0, key="sim_factor"
            )

        # Calcular impacto
        fat_sim = fat_mes \
                  * (1 - pct_fat_reduz/100) \
                  * (1 + pct_fat_aum/100) \
                  + nova_obra_val
        cust_sim = custos_fixos_mes \
                   * (1 + pct_aum_sal/100 * 0.7) \
                   * (1 - red_custos/100)
        saldo_sim = saldo_atual + fat_antecip
        margem_sim = round(
            (fat_sim - cust_sim) / fat_sim * 100, 1
        ) if fat_sim > 0 else 0.0
        auto_sim   = round(
            saldo_sim / cust_sim, 1
        ) if cust_sim > 0 else 99.0

        st.markdown("---")
        st.markdown("#### 📊 Resultado da Simulação")

        col_r1,col_r2,col_r3,col_r4 = st.columns(4)
        delta_fat  = fat_sim  - fat_mes
        delta_cust = cust_sim - custos_fixos_mes
        delta_marg = margem_sim - margem_pct
        delta_auto = auto_sim  - autonomia

        with col_r1:
            st.metric(
                "💰 Faturação",
                f"€{fat_sim:,.0f}",
                delta=f"€{delta_fat:+,.0f}"
            )
        with col_r2:
            st.metric(
                "💸 Custos",
                f"€{cust_sim:,.0f}",
                delta=f"€{delta_cust:+,.0f}",
                delta_color="inverse"
            )
        with col_r3:
            st.metric(
                "📈 Margem",
                f"{margem_sim:.1f}%",
                delta=f"{delta_marg:+.1f}%"
            )
        with col_r4:
            st.metric(
                "📅 Autonomia",
                f"{auto_sim:.1f}m",
                delta=f"{delta_auto:+.1f}m"
            )

        # Gráfico comparação
        st.plotly_chart(
            _grafico_cenario_cashflow(
                saldo_sim,
                fat_mes if fat_mes > 0 else cust_sim * 1.3,
                custos_fixos_mes,
                fat_sim,
                cust_sim,
                meses=6,
                label_base="Situação Atual",
                label_cen="Simulação"
            ),
            use_container_width=True
        )

        # Veredito
        if fat_sim >= cust_sim * 1.2 and auto_sim >= 3:
            verdict_cor = "#10B981"
            verdict     = "✅ Simulação positiva — empresa sustentável"
        elif fat_sim >= cust_sim:
            verdict_cor = "#F59E0B"
            verdict     = "⚠️ Margem estreita — monitorizar de perto"
        else:
            verdict_cor = "#EF4444"
            verdict     = "🔴 Insustentável — ação corretiva necessária"

        st.markdown(
            f"<div style='background:{verdict_cor}18;"
            f"border:2px solid {verdict_cor};"
            f"border-radius:10px;padding:14px;"
            f"text-align:center;margin-top:8px;'>"
            f"<b style='color:{verdict_cor};"
            f"font-size:1.05rem;'>{verdict}</b>"
            f"</div>",
            unsafe_allow_html=True
        )

    # ════════════════════════════════════════════════════════════════
    # TAB — ALTMAN Z-SCORE
    # ════════════════════════════════════════════════════════════════
    with t_altman:
        st.markdown("### 📐 Modelo Altman Z-Score")
        st.info(
            "O Altman Z-Score é um modelo académico validado "
            "que estima a probabilidade de dificuldades financeiras "
            "nos próximos 12-24 meses. "
            "Desenvolvido em 1968, continua a ser o modelo "
            "mais utilizado em análise de crédito de PMEs."
        )

        col_az1, col_az2 = st.columns(2)

        with col_az1:
            st.markdown("#### 📥 Dados Financeiros")
            st.markdown(
                "<small style='color:#64748B;'>"
                "Preenche com os valores do último balanço. "
                "Se não tiveres os dados exactos, usa estimativas."
                "</small>",
                unsafe_allow_html=True
            )

            az_ativo = st.number_input(
                "Ativo Total (€)",
                min_value=0.0,
                value=max(saldo_atual * 3, 100000.0),
                step=5000.0, key="az_ativo"
            )
            az_ac = st.number_input(
                "Ativo Corrente (€)",
                min_value=0.0,
                value=max(saldo_atual * 1.5, 50000.0),
                step=1000.0, key="az_ac"
            )
            az_pc = st.number_input(
                "Passivo Corrente (€)",
                min_value=0.0,
                value=max(custos_fixos_mes * 2, 20000.0),
                step=1000.0, key="az_pc"
            )
            az_pt = st.number_input(
                "Passivo Total (€)",
                min_value=0.0,
                value=max(custos_fixos_mes * 4, 40000.0),
                step=1000.0, key="az_pt"
            )
            az_cp = st.number_input(
                "Capital Próprio (€)",
                min_value=0.0,
                value=max(az_ativo - az_pt, 10000.0)
                if az_ativo > az_pt else 10000.0,
                step=1000.0, key="az_cp"
            )
            az_rr = st.number_input(
                "Resultados Retidos (€)",
                min_value=-999999.0,
                value=max(az_cp * 0.3, 5000.0),
                step=1000.0, key="az_rr"
            )
            az_ebit = st.number_input(
                "EBIT — Resultado antes Juros e Impostos (€)",
                min_value=-999999.0,
                value=max(fat_mes * 0.15 * 12, 5000.0),
                step=1000.0, key="az_ebit"
            )
            az_vendas = st.number_input(
                "Vendas/Faturação Anual (€)",
                min_value=0.0,
                value=max(fat_mes * 12, 50000.0),
                step=5000.0, key="az_vendas"
            )

        with col_az2:
            altman = _altman_z_score(
                az_ativo, az_pc, az_ac, az_rr,
                az_ebit, az_cp, az_pt, az_vendas
            )

            # Gauge Z-Score
            z_score_norm = min(100, max(0, round(
                (altman['z_score'] / 4) * 100
            )))
            st.plotly_chart(
                _grafico_gauge_saude(
                    z_score_norm,
                    f"Z-Score: {altman['z_score']:.3f}"
                ),
                use_container_width=True
            )

            # Resultado
            cor_alt = altman.get('cor','#64748B')
            st.markdown(
                f"<div style='background:{cor_alt}18;"
                f"border:2px solid {cor_alt};"
                f"border-radius:12px;padding:16px;"
                f"text-align:center;'>"
                f"<h2 style='color:{cor_alt};margin:0;'>"
                f"{altman.get('emoji','')} "
                f"Z = {altman['z_score']:.3f}</h2>"
                f"<p style='color:#94A3B8;margin:4px 0;'>"
                f"{altman['descricao']}</p>"
                f"<b style='color:{cor_alt};"
                f"font-size:1.2rem;'>"
                f"Zona: {altman['zona'].upper()}</b><br>"
                f"<p style='color:#64748B;margin:6px 0 0;'>"
                f"Prob. dificuldades: "
                f"<b style='color:{cor_alt};'>"
                f"~{altman['probabilidade']}%</b></p>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Referências
            st.markdown(
                "<div style='background:#1E293B;"
                "border-radius:8px;padding:12px;margin-top:10px;'>"
                "<p style='color:#64748B;font-size:0.75rem;"
                "font-weight:700;text-transform:uppercase;"
                "margin:0 0 6px;'>Referências Z-Score:</p>"
                "<div style='display:flex;"
                "justify-content:space-between;"
                "margin:3px 0;'>"
                "<small style='color:#10B981;'>🟢 Z > 2.9</small>"
                "<small style='color:#94A3B8;'>Saudável</small>"
                "</div>"
                "<div style='display:flex;"
                "justify-content:space-between;margin:3px 0;'>"
                "<small style='color:#F59E0B;'>"
                "🟡 1.23 ≤ Z < 2.9</small>"
                "<small style='color:#94A3B8;'>Atenção</small>"
                "</div>"
                "<div style='display:flex;"
                "justify-content:space-between;margin:3px 0;'>"
                "<small style='color:#EF4444;'>🔴 Z < 1.23</small>"
                "<small style='color:#94A3B8;'>Perigo</small>"
                "</div></div>",
                unsafe_allow_html=True
            )

        # Waterfall componentes
        st.plotly_chart(
            _grafico_waterfall_altman(altman),
            use_container_width=True
        )

        # Explicação das componentes
        st.markdown("#### 📋 Interpretação das Componentes")
        comp_exp = [
            ("X1 = Capital Circulante / Ativo Total",
             f"{altman.get('x1',0):.4f}",
             "Mede a liquidez. Valor negativo indica dificuldades "
             "de curto prazo."),
            ("X2 = Resultados Retidos / Ativo Total",
             f"{altman.get('x2',0):.4f}",
             "Mede a rentabilidade acumulada. PMEs jovens "
             "tendem a ter valores baixos."),
            ("X3 = EBIT / Ativo Total",
             f"{altman.get('x3',0):.4f}",
             "Mede eficiência operacional. "
             "Quanto ganha por cada euro de ativo."),
            ("X4 = Capital Próprio / Passivo Total",
             f"{altman.get('x4',0):.4f}",
             "Mede estrutura de capital. "
             "Quanto capital próprio existe por dívida."),
            ("X5 = Vendas / Ativo Total",
             f"{altman.get('x5',0):.4f}",
             "Mede eficiência dos ativos. "
             "Quanto fatura por cada euro de ativo."),
        ]
        for label, val, exp in comp_exp:
            st.markdown(
                f"<div style='background:#1E293B;"
                f"border-radius:8px;padding:10px 14px;"
                f"margin-bottom:6px;'>"
                f"<b style='color:#3B82F6;"
                f"font-size:0.85rem;'>{label}: {val}</b><br>"
                f"<small style='color:#64748B;'>{exp}</small>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — FONTES DE AJUDA
    # ════════════════════════════════════════════════════════════════
    with t_ajuda:
        st.markdown("### 🆘 Fontes de Ajuda em Crise")
        st.info(
            "Listagem de entidades e instrumentos disponíveis "
            "em Portugal para empresas em dificuldade. "
            "Ordenadas por urgência."
        )

        # Filtro por urgência
        urg_filt = st.selectbox(
            "Filtrar por urgência",
            ["Todas","crítica","alta","média","baixa"],
            key="ajuda_urg_filt"
        )

        fontes_show = FONTES_AJUDA
        if urg_filt != "Todas":
            fontes_show = [
                f for f in FONTES_AJUDA
                if f['urgencia'] == urg_filt
            ]

        # Ordenar por urgência
        ordem_urg = {"crítica":0,"alta":1,"média":2,"baixa":3}
        fontes_show = sorted(
            fontes_show,
            key=lambda x: ordem_urg.get(x['urgencia'], 9)
        )

        for fonte in fontes_show:
            cor_f  = fonte['cor']
            urg_ic = {
                "crítica":"🆘","alta":"🔴","média":"🟡","baixa":"🔵"
            }.get(fonte['urgencia'],"⚪")

            st.markdown(
                f"<div class='fonte-card' "
                f"style='border-left-color:{cor_f};'>"
                f"<div style='display:flex;"
                f"justify-content:space-between;"
                f"align-items:flex-start;'>"
                f"<div>"
                f"<b style='color:#F1F5F9;"
                f"font-size:0.95rem;'>"
                f"{urg_ic} {fonte['nome']}</b><br>"
                f"<small style='color:#64748B;'>"
                f"🏷️ {fonte['tipo']} · "
                f"💰 {fonte['valor_max']} · "
                f"⏱️ {fonte['prazo_resp']}"
                f"</small><br>"
                f"<small style='color:#94A3B8;"
                f"margin-top:4px;display:block;'>"
                f"{fonte['descricao']}"
                f"</small>"
                f"</div>"
                f"<div style='text-align:right;"
                f"min-width:140px;'>"
                f"<span style='background:{cor_f}22;"
                f"color:{cor_f};padding:3px 10px;"
                f"border-radius:10px;font-size:0.72rem;"
                f"font-weight:700;'>"
                f"Urgência: {fonte['urgencia'].upper()}"
                f"</span><br>"
                f"<small style='color:#64748B;"
                f"margin-top:4px;display:block;'>"
                f"📞 {fonte['contacto']}</small>"
                f"<small style='color:#3B82F6;'>"
                f"🌐 {fonte['url']}</small>"
                f"</div></div></div>",
                unsafe_allow_html=True
            )

        # Calculadora de financiamento rápido
        st.markdown("---")
        st.markdown("#### 💰 Calculadora de Necessidade de Financiamento")

        col_calc1, col_calc2 = st.columns(2)
        with col_calc1:
            calc_gap = st.number_input(
                "Gap de cash flow identificado (€)",
                min_value=0.0,
                value=max(0.0, custos_fixos_mes * 2 - saldo_atual),
                step=1000.0, key="calc_gap"
            )
            calc_meses = st.slider(
                "Meses para cobrir", 1, 12, 3,
                key="calc_meses"
            )

        with col_calc2:
            total_nec = calc_gap + custos_fixos_mes * calc_meses
            st.markdown(
                f"<div style='background:#1E293B;"
                f"border-radius:10px;padding:16px;"
                f"border-left:4px solid #3B82F6;'>"
                f"<p style='color:#64748B;margin:0 0 6px;'>"
                f"Financiamento total necessário:</p>"
                f"<b style='color:#3B82F6;"
                f"font-size:1.8rem;'>"
                f"€{total_nec:,.2f}</b><br>"
                f"<small style='color:#64748B;'>"
                f"Gap: €{calc_gap:,.0f} + "
                f"{calc_meses} meses × "
                f"€{custos_fixos_mes:,.0f}</small><br><br>"
                f"<b style='color:#F1F5F9;"
                f"font-size:0.85rem;'>Opções:</b><br>"
                f"<small style='color:#94A3B8;'>"
                f"• Factoring: €{total_nec*0.95:,.0f} "
                f"(em 48h, custo ~3%)<br>"
                f"• Linha PME: €{min(total_nec,1500000):,.0f} "
                f"(7-15 dias)<br>"
                f"• APOIAR.PT: €{min(total_nec,750000):,.0f} "
                f"(5-10 dias)</small>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — PLANO DE CONTINGÊNCIA
    # ════════════════════════════════════════════════════════════════
    with t_contingencia:
        st.markdown("### 📋 Plano de Contingência")
        st.info(
            "Plano automático gerado com base no nível de crise "
            "atual. Pode ser editado e descarregado em PDF "
            "para apresentar a sócios, banco ou IAPMEI."
        )

        # Ações por nível
        acoes_por_nivel = {
            "🟢 SAUDÁVEL": [
                "Manter reserva mínima de 3 meses de custos fixos",
                "Diversificar carteira de clientes "
                "(objetivo: nenhum >40% receita)",
                "Renegociar contratos de renting próximos do fim",
                "Avaliar elegibilidade para fundos europeus "
                "(PT2030/PRR)",
                "Implementar monitorização mensal do Z-Score",
            ],
            "🟡 ATENÇÃO": [
                "Acelerar cobranças — contactar clientes "
                "em atraso imediatamente",
                "Suspender despesas discricionárias (>€500 "
                "requerem aprovação)",
                "Solicitar linha de crédito preventiva ao banco "
                "(antes de precisar)",
                "Renegociar prazos de pagamento com fornecedores "
                "(+30-45 dias)",
                "Convocar reunião de gestão para revisão do budget",
                "Avaliar redução temporária de frota",
            ],
            "🔴 ALERTA": [
                "URGENTE: Contactar banco para renegociar créditos",
                "Ativar factoring para faturas pendentes "
                "— liquidez imediata",
                "Contactar IAPMEI para apoios disponíveis "
                "(808 200 115)",
                "Avaliar lay-off simplificado para equipa "
                "sem obra alocada",
                "Reduzir salários dos sócios temporariamente",
                "Vender ativos não essenciais",
                "Contactar mediador de crédito "
                "(Banco de Portugal — 213 130 000)",
            ],
            "🆘 CRISE": [
                "IMEDIATO: Contactar mediador de crédito "
                "(213 130 000)",
                "IMEDIATO: Submeter pedido lay-off simplificado "
                "(IEFP — 300 010 001)",
                "Contactar advogado especialista em insolvência",
                "Notificar sócios e preparar injeção de capital",
                "Avaliar PER (Processo Especial de Revitalização)",
                "Contactar AT para pagamento faseado de impostos",
                "Solicitar moratória bancária urgente",
                "Avaliar cessão de créditos ou factoring de urgência",
            ],
        }

        acoes_nivel = acoes_por_nivel.get(nivel, [])

        # Ações editáveis
        st.markdown(f"#### ⚡ Ações para Nível {nivel}")

        acoes_editadas = []
        for i, acao in enumerate(acoes_nivel):
            ac_edit = st.text_input(
                f"Ação {i+1}",
                value=acao,
                key=f"acao_edit_{i}"
            )
            acoes_editadas.append(ac_edit)

        # Adicionar ação personalizada
        if st.button("➕ Adicionar Ação", key="btn_add_acao"):
            st.session_state['n_acoes_extra'] = \
                st.session_state.get('n_acoes_extra', 0) + 1

        for j in range(st.session_state.get('n_acoes_extra', 0)):
            ac_extra = st.text_input(
                f"Ação extra {j+1}", key=f"acao_extra_{j}"
            )
            if ac_extra:
                acoes_editadas.append(ac_extra)

        # Fontes recomendadas para o nível atual
        urgencias_nivel = {
            "🟢 SAUDÁVEL": ["baixa","média"],
            "🟡 ATENÇÃO":  ["média","alta"],
            "🔴 ALERTA":   ["alta","crítica"],
            "🆘 CRISE":    ["crítica","alta"],
        }
        urgs_rec = urgencias_nivel.get(nivel, ["média"])
        fontes_rec = [
            f for f in FONTES_AJUDA
            if f['urgencia'] in urgs_rec
        ]

        st.markdown("---")
        col_pdf1, col_pdf2 = st.columns(2)
        with col_pdf1:
            if st.button(
                "📄 Gerar Plano PDF",
                key="btn_contingencia_pdf",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("A gerar plano..."):
                    pdf_cont = _gerar_pdf_contingencia(
                        score_global, nivel,
                        indicadores, acoes_editadas,
                        fontes_rec, empresa
                    )
                st.session_state['cont_pdf'] = pdf_cont
                st.session_state['cont_pdf_nome'] = (
                    f"plano_contingencia_"
                    f"{hoje.strftime('%Y%m%d')}.pdf"
                )
                st.rerun()

        with col_pdf2:
            if st.session_state.get('cont_pdf'):
                st.download_button(
                    "📥 Descarregar PDF",
                    data=st.session_state['cont_pdf'],
                    file_name=st.session_state.get(
                        'cont_pdf_nome','plano.pdf'
                    ),
                    mime="application/pdf",
                    key="dl_cont_pdf",
                    use_container_width=True,
                    type="primary"
                )

        # Co-Piloto IA para contingência
        st.markdown("---")
        st.markdown("#### 🤖 Conselho IA para a Situação Atual")

        if st.button(
            "🤖 Pedir Análise e Recomendações IA",
            key="btn_ia_contingencia",
            use_container_width=True
        ):
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY","")
            if not api_key:
                st.error("❌ API key não configurada.")
            else:
                ctx_ia = {
                    "nivel":          nivel,
                    "score_global":   score_global,
                    "saldo_atual":    round(saldo_atual, 2),
                    "autonomia_meses":autonomia,
                    "margem_pct":     margem_pct,
                    "fat_mes":        round(fat_mes, 2),
                    "custos_fixos_mes":round(custos_fixos_mes, 2),
                    "fat_vencidas":   fat_venc,
                    "conc_cliente":   conc_cliente,
                    "indicadores": [
                        {"nome":i['nome'],
                         "score":i['score'],
                         "valor":i['valor']}
                        for i in indicadores
                    ]
                }
                prompt = (
                    f"Sou o CFO de uma PME portuguesa de "
                    f"instrumentação industrial (CPS). "
                    f"A situação financeira atual é {nivel} "
                    f"(score {score_global}/100).\n\n"
                    f"Dados: {json.dumps(ctx_ia, ensure_ascii=False)}\n\n"
                    f"Como CFO sénior experiente em PMEs portuguesas, "
                    f"dá-me:\n"
                    f"1. Diagnóstico honesto em 2 frases\n"
                    f"2. As 3 ações MÁS URGENTES que devo fazer "
                    f"esta semana\n"
                    f"3. O maior risco que estou a ignorar\n"
                    f"4. Uma mensagem de encorajamento realista\n\n"
                    f"Tom: direto, sem rodeios, como um consultor "
                    f"de confiança. Máximo 5 parágrafos."
                )
                with st.spinner("🤖 A pensar como CFO..."):
                    try:
                        client = anthropic.Anthropic(api_key=api_key)
                        resp   = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=700,
                            messages=[{
                                "role":"user",
                                "content":prompt
                            }]
                        )
                        conselho = resp.content[0].text
                        st.session_state['ia_conselho'] = conselho
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")

        if st.session_state.get('ia_conselho'):
            st.markdown(
                f"<div style='background:rgba(59,130,246,0.1);"
                f"border:1px solid #3B82F6;"
                f"border-radius:12px;padding:20px;"
                f"color:#E2E8F0;font-size:0.9rem;"
                f"line-height:1.7;'>"
                f"<p style='color:#3B82F6;font-weight:700;"
                f"margin:0 0 10px;'>"
                f"🤖 CONSELHO CFO IA — {nivel}</p>"
                f"{st.session_state['ia_conselho'].replace(chr(10),'<br>')}"
                f"</div>",
                unsafe_allow_html=True
            )

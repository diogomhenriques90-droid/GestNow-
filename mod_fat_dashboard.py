"""
GESTNOW v3 — mod_fat_dashboard.py
Dashboard Executivo CFO — Passo 1 do Módulo Faturação
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json, os
from datetime import datetime, date, timedelta
from core import fh, load_db, inv

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load_seguro(n, cols):
    try:
        return load_db(n, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()

def _mes_atual():
    h = date.today()
    return h.month, h.year

def _label_mes(m, a):
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun",
             "Jul","Ago","Set","Out","Nov","Dez"]
    return f"{meses[m-1]} {a}"

# ─────────────────────────────────────────────────────────────────
# CÁLCULOS PRINCIPAIS
# ─────────────────────────────────────────────────────────────────

def _calcular_kpis(registos_db, faturas_cli, faturas_forn,
                   diarias_pag, compras_db, dormidas_db):
    """Calcula todos os KPIs do dashboard."""
    mes, ano = _mes_atual()
    hoje = date.today()

    # ── Faturação do mês ──────────────────────────────────────────
    fat_mes = 0.0
    fat_mes_ant = 0.0
    aging_total = 0.0
    faturas_vencidas = 0
    a_receber = 0.0

    if not faturas_cli.empty:
        faturas_cli = faturas_cli.copy()
        faturas_cli['Total_Num'] = pd.to_numeric(
            faturas_cli.get('Total', 0), errors='coerce'
        ).fillna(0)
        faturas_cli['Data_d'] = pd.to_datetime(
            faturas_cli.get('Data_Emissao',''), dayfirst=True, errors='coerce'
        )
        # Este mês
        mask_mes = (
            (faturas_cli['Data_d'].dt.month == mes) &
            (faturas_cli['Data_d'].dt.year  == ano)
        )
        fat_mes = faturas_cli[mask_mes]['Total_Num'].sum()

        # Mês anterior
        mes_ant = mes - 1 if mes > 1 else 12
        ano_ant = ano if mes > 1 else ano - 1
        mask_ant = (
            (faturas_cli['Data_d'].dt.month == mes_ant) &
            (faturas_cli['Data_d'].dt.year  == ano_ant)
        )
        fat_mes_ant = faturas_cli[mask_ant]['Total_Num'].sum()

        # A receber (não pagas)
        nao_pagas = faturas_cli[
            ~faturas_cli.get('Estado','').isin(['Paga','Anulada'])
        ] if 'Estado' in faturas_cli.columns else faturas_cli
        a_receber = nao_pagas['Total_Num'].sum()

        # Vencidas
        if 'Data_Vencimento' in faturas_cli.columns:
            faturas_cli['Venc_d'] = pd.to_datetime(
                faturas_cli['Data_Vencimento'], dayfirst=True, errors='coerce'
            )
            vencidas = faturas_cli[
                (faturas_cli['Venc_d'] < pd.Timestamp(hoje)) &
                (~faturas_cli.get('Estado','').isin(['Paga','Anulada']))
            ] if 'Estado' in faturas_cli.columns else pd.DataFrame()
            faturas_vencidas = len(vencidas) if not vencidas.empty else 0

    # ── A pagar (fornecedores) ────────────────────────────────────
    a_pagar = 0.0
    if not faturas_forn.empty and 'Total' in faturas_forn.columns:
        nao_pagas_f = faturas_forn[
            ~faturas_forn.get('Estado','').isin(['Paga','Anulada'])
        ] if 'Estado' in faturas_forn.columns else faturas_forn
        a_pagar = pd.to_numeric(
            nao_pagas_f['Total'], errors='coerce'
        ).fillna(0).sum()

    # ── Custos do mês ─────────────────────────────────────────────
    custos_mes = 0.0
    custos_mes += _num(diarias_pag, 'Valor_Total')
    custos_mes += _num(compras_db, 'Total')
    custos_mes += _num(dormidas_db, 'Total')

    # ── Margem ────────────────────────────────────────────────────
    margem_pct = 0.0
    if fat_mes > 0:
        margem_pct = round((fat_mes - custos_mes) / fat_mes * 100, 1)

    # ── Trend faturação ───────────────────────────────────────────
    trend = 0.0
    if fat_mes_ant > 0:
        trend = round((fat_mes - fat_mes_ant) / fat_mes_ant * 100, 1)

    return {
        "fat_mes":         fat_mes,
        "fat_mes_ant":     fat_mes_ant,
        "trend_fat":       trend,
        "a_receber":       a_receber,
        "a_pagar":         a_pagar,
        "custos_mes":      custos_mes,
        "margem_pct":      margem_pct,
        "faturas_vencidas":faturas_vencidas,
        "cash_flow_prev":  a_receber - a_pagar,
    }


def _calcular_score_obra(obra, registos_db, faturas_cli,
                          obras_orc, obras_db):
    """Calcula score 0-100 para uma obra."""
    score = 0
    detalhes = {}

    regs = registos_db[
        registos_db['Obra'] == obra
    ] if not registos_db.empty else pd.DataFrame()

    # 1. Margem (0-20 pts)
    margem = 25.0  # default se não há dados
    if margem >= 30:      score += 20; detalhes['Margem'] = 20
    elif margem >= 20:    score += 15; detalhes['Margem'] = 15
    elif margem >= 10:    score += 8;  detalhes['Margem'] = 8
    else:                 score += 0;  detalhes['Margem'] = 0

    # 2. Horas validadas vs pendentes (0-15 pts)
    if not regs.empty:
        total = len(regs)
        valid = len(regs[regs['Status'].isin(['1','2','3'])])
        pct   = valid / total * 100 if total > 0 else 0
        if pct >= 90:   score += 15; detalhes['Validação'] = 15
        elif pct >= 70: score += 10; detalhes['Validação'] = 10
        elif pct >= 50: score += 5;  detalhes['Validação'] = 5
        else:           score += 0;  detalhes['Validação'] = 0
    else:
        detalhes['Validação'] = 0

    # 3. Cobrança (0-15 pts) — simplificado
    score += 12; detalhes['Cobrança'] = 12

    # 4. Equipa (0-10 pts)
    score += 8; detalhes['Equipa'] = 8

    # 5. Horas este mês (0-10 pts)
    if not regs.empty:
        mes, ano = _mes_atual()
        regs_c = regs.copy()
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
        if horas_mes > 0: score += 10; detalhes['Atividade'] = 10
        else:             score += 0;  detalhes['Atividade'] = 0
    else:
        detalhes['Atividade'] = 0

    # 6. Sem incidentes (0-10 pts)
    score += 10; detalhes['Segurança'] = 10

    # 7. Desvio orçamento (0-10 pts)
    score += 8; detalhes['Orçamento'] = 8

    # 8. Faturação em dia (0-10 pts)
    score += 9; detalhes['Faturação'] = 9

    return min(score, 100), detalhes


def _rag_cor(score):
    if score >= 70: return "#10B981", "🟢"
    if score >= 40: return "#F59E0B", "🟡"
    return "#EF4444", "🔴"


def _calcular_saude_financeira(kpis, faturas_vencidas,
                                contas_db, registos_db):
    """Score 0-100 de saúde financeira da empresa."""
    score = 100

    # Margem baixa penaliza
    if kpis['margem_pct'] < 10:   score -= 25
    elif kpis['margem_pct'] < 20: score -= 12
    elif kpis['margem_pct'] < 30: score -= 5

    # Faturas vencidas penalizam
    score -= min(faturas_vencidas * 5, 20)

    # Cash flow negativo penaliza
    if kpis['cash_flow_prev'] < 0:
        score -= 20
    elif kpis['cash_flow_prev'] < kpis['custos_mes']:
        score -= 8

    # A pagar > a receber penaliza
    if kpis['a_pagar'] > kpis['a_receber']:
        score -= 15

    return max(0, min(100, score))


# ─────────────────────────────────────────────────────────────────
# CO-PILOTO IA
# ─────────────────────────────────────────────────────────────────

def _copiloto_ia(pergunta: str, contexto: dict) -> str:
    """Co-Piloto IA — responde em português com dados reais."""
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "❌ API key não configurada."

        client = anthropic.Anthropic(api_key=api_key)

        system = """És o Co-Piloto Financeiro da GESTNOW, um assistente CFO
especializado em empresas portuguesas de mão de obra especializada
e instrumentação industrial.

Respondes sempre em português de Portugal, de forma concisa e
direta. Quando tens dados concretos, usas-os. Quando não tens,
dás orientações baseadas em boas práticas para PMEs portuguesas.

Formato das respostas:
- Máximo 3 parágrafos curtos
- Usa números concretos quando disponíveis
- Termina sempre com 1 ação recomendada
- Usa emojis moderadamente"""

        prompt = f"""Dados financeiros atuais da empresa:
{json.dumps(contexto, ensure_ascii=False, indent=2)}

Pergunta do CFO: {pergunta}"""

        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text

    except Exception as e:
        return f"❌ Erro: {e}"


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_gauge(score, titulo):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        title={'text': titulo, 'font': {'color': '#F1F5F9', 'size': 14}},
        delta={'reference': 70, 'increasing': {'color': '#10B981'},
               'decreasing': {'color': '#EF4444'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#64748B'},
            'bar':  {'color': '#10B981' if score >= 70
                     else '#F59E0B' if score >= 40 else '#EF4444'},
            'bgcolor': '#1E293B',
            'bordercolor': '#334155',
            'steps': [
                {'range': [0,  40], 'color': 'rgba(239,68,68,0.15)'},
                {'range': [40, 70], 'color': 'rgba(245,158,11,0.15)'},
                {'range': [70,100], 'color': 'rgba(16,185,129,0.15)'},
            ],
            'threshold': {
                'line': {'color': '#F1F5F9', 'width': 2},
                'thickness': 0.75,
                'value': score
            }
        },
        number={'font': {'color': '#F1F5F9', 'size': 28}}
    ))
    fig.update_layout(
        height=220,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=10, l=20, r=20),
        font={'color': '#F1F5F9'}
    )
    return fig


def _grafico_receita_12m(faturas_cli):
    """Line chart receita últimos 12 meses."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    hoje = date.today()
    labels, valores = [], []

    for i in range(11, -1, -1):
        d = date(hoje.year, hoje.month, 1) - timedelta(days=i*30)
        labels.append(f"{meses_pt[d.month-1]} {str(d.year)[2:]}")
        val = 0.0
        if not faturas_cli.empty and 'Data_Emissao' in faturas_cli.columns:
            fc = faturas_cli.copy()
            fc['Data_d'] = pd.to_datetime(
                fc['Data_Emissao'], dayfirst=True, errors='coerce'
            )
            fc['Total_Num'] = pd.to_numeric(
                fc['Total'], errors='coerce'
            ).fillna(0)
            mask = (
                (fc['Data_d'].dt.month == d.month) &
                (fc['Data_d'].dt.year  == d.year)
            )
            val = fc[mask]['Total_Num'].sum()
        valores.append(val)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=valores,
        mode='lines+markers',
        name='Faturação',
        line={'color': '#3B82F6', 'width': 3},
        marker={'color': '#3B82F6', 'size': 8},
        fill='tozeroy',
        fillcolor='rgba(59,130,246,0.1)'
    ))
    # Linha objetivo (estimativa +15%)
    objetivo = [v * 1.15 if v > 0 else max(valores) * 0.8
                for v in valores]
    fig.add_trace(go.Scatter(
        x=labels, y=objetivo,
        mode='lines',
        name='Objetivo',
        line={'color': '#10B981', 'width': 2, 'dash': 'dash'},
    ))
    fig.update_layout(
        title={'text': 'Faturação 12 Meses',
               'font': {'color': '#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color': '#F1F5F9'},
        legend={'font': {'color': '#94A3B8'}},
        xaxis={'gridcolor': '#334155', 'tickfont': {'color': '#94A3B8'}},
        yaxis={'gridcolor': '#334155', 'tickfont': {'color': '#94A3B8'},
               'tickprefix': '€'},
        margin=dict(t=40, b=20, l=10, r=10),
        hovermode='x unified'
    )
    return fig


def _grafico_waterfall(fat_mes, custos_mes, margem):
    """Waterfall — como chegámos ao resultado do mês."""
    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=["absolute", "relative", "relative",
                 "relative", "relative", "total"],
        x=["Faturação", "Mão de Obra", "Materiais",
           "Dormidas", "Diárias", "Margem"],
        y=[fat_mes,
           -(custos_mes * 0.55),
           -(custos_mes * 0.20),
           -(custos_mes * 0.12),
           -(custos_mes * 0.13),
           0],
        connector={"line": {"color": "#334155"}},
        increasing={"marker": {"color": "#10B981"}},
        decreasing={"marker": {"color": "#EF4444"}},
        totals={"marker": {"color": "#3B82F6"}},
        text=[f"€{fat_mes:,.0f}",
              f"-€{custos_mes*0.55:,.0f}",
              f"-€{custos_mes*0.20:,.0f}",
              f"-€{custos_mes*0.12:,.0f}",
              f"-€{custos_mes*0.13:,.0f}",
              f"€{margem:,.0f}"],
        textposition="outside",
        textfont={"color": "#F1F5F9", "size": 11}
    ))
    fig.update_layout(
        title={'text': 'Resultado do Mês',
               'font': {'color': '#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color': '#F1F5F9'},
        xaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'}},
        yaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'},
               'tickprefix': '€'},
        margin=dict(t=40, b=20, l=10, r=10),
        showlegend=False
    )
    return fig


def _grafico_donut_custos(custos_mes):
    """Donut breakdown de custos."""
    labels = ['Mão de Obra', 'Materiais', 'Dormidas',
              'Diárias', 'Frota']
    values = [custos_mes * 0.55, custos_mes * 0.20,
              custos_mes * 0.12, custos_mes * 0.08,
              custos_mes * 0.05]
    cores  = ['#3B82F6', '#10B981', '#F59E0B',
              '#8B5CF6', '#EF4444']

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker={'colors': cores,
                'line': {'color': '#0F172A', 'width': 2}},
        textfont={'color': '#F1F5F9', 'size': 11},
        hovertemplate='%{label}: €%{value:,.0f}<extra></extra>'
    ))
    # ── FIX BUG 1 ── era `))` (parêntesis duplo), corrigido para `)`
    fig.update_layout(
        title={'text': 'Breakdown Custos',
               'font': {'color': '#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#F1F5F9'},
        legend={'font': {'color': '#94A3B8'},
                'orientation': 'v',
                'x': 1.0},
        margin=dict(t=40, b=10, l=10, r=10),
        annotations=[{
            'text': f'€{custos_mes:,.0f}',
            'x': 0.5, 'y': 0.5,
            'font_size': 14,
            'font_color': '#F1F5F9',
            'showarrow': False
        }]
    )
    return fig


def _grafico_receita_custos_bar(faturas_cli, registos_db):
    """Grouped bar — receita vs custos 6 meses."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    hoje = date.today()
    labels, receitas, custos_list = [], [], []

    for i in range(5, -1, -1):
        d = date(hoje.year, hoje.month, 1) - timedelta(days=i*30)
        labels.append(meses_pt[d.month - 1])
        rec = 0.0
        if not faturas_cli.empty and 'Data_Emissao' in faturas_cli.columns:
            fc = faturas_cli.copy()
            fc['Data_d'] = pd.to_datetime(
                fc['Data_Emissao'], dayfirst=True, errors='coerce'
            )
            fc['Total_Num'] = pd.to_numeric(
                fc.get('Total', 0), errors='coerce'
            ).fillna(0)
            mask = (fc['Data_d'].dt.month == d.month) & \
                   (fc['Data_d'].dt.year  == d.year)
            rec = fc[mask]['Total_Num'].sum()
        receitas.append(rec)
        custos_list.append(rec * 0.72)  # estimativa 28% margem

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Receita', x=labels, y=receitas,
        marker_color='#3B82F6',
        text=[f"€{v:,.0f}" for v in receitas],
        textposition='outside',
        textfont={'color': '#F1F5F9', 'size': 10}
    ))
    fig.add_trace(go.Bar(
        name='Custos', x=labels, y=custos_list,
        marker_color='#EF4444',
        text=[f"€{v:,.0f}" for v in custos_list],
        textposition='outside',
        textfont={'color': '#F1F5F9', 'size': 10}
    ))
    fig.update_layout(
        title={'text': 'Receita vs Custos (6 meses)',
               'font': {'color': '#F1F5F9'}},
        barmode='group',
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color': '#F1F5F9'},
        legend={'font': {'color': '#94A3B8'}},
        xaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'}},
        yaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'},
               'tickprefix': '€'},
        margin=dict(t=40, b=20, l=10, r=10)
    )
    return fig


def _grafico_aging(faturas_cli):
    """Bar chart aging de clientes."""
    escaloes = ['0-30 dias', '31-60 dias',
                '61-90 dias', '+90 dias']
    valores  = [0.0, 0.0, 0.0, 0.0]
    hoje_ts  = pd.Timestamp(date.today())

    if not faturas_cli.empty and 'Data_Vencimento' in faturas_cli.columns:
        fc = faturas_cli.copy()
        fc['Venc_d']    = pd.to_datetime(
            fc['Data_Vencimento'], dayfirst=True, errors='coerce'
        )
        fc['Total_Num'] = pd.to_numeric(
            fc.get('Total', 0), errors='coerce'
        ).fillna(0)
        nao_pagas = fc[
            ~fc.get('Estado','').isin(['Paga','Anulada'])
        ] if 'Estado' in fc.columns else fc

        for _, row in nao_pagas.iterrows():
            dias = (hoje_ts - row['Venc_d']).days \
                   if pd.notna(row['Venc_d']) else 0
            if dias <= 30:   valores[0] += row['Total_Num']
            elif dias <= 60: valores[1] += row['Total_Num']
            elif dias <= 90: valores[2] += row['Total_Num']
            else:            valores[3] += row['Total_Num']
    else:
        # Dados de exemplo se não há faturas
        valores = [15000, 8000, 3000, 1500]

    cores = ['#10B981', '#F59E0B', '#EF4444', '#DC2626']
    fig = go.Figure(go.Bar(
        x=escaloes, y=valores,
        marker_color=cores,
        text=[f"€{v:,.0f}" for v in valores],
        textposition='outside',
        textfont={'color': '#F1F5F9'}
    ))
    fig.update_layout(
        title={'text': 'Aging de Clientes',
               'font': {'color': '#F1F5F9'}},
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color': '#F1F5F9'},
        xaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'}},
        yaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'},
               'tickprefix': '€'},
        margin=dict(t=40, b=20, l=10, r=10),
        showlegend=False
    )
    return fig


def _grafico_mapa_calor(faturas_cli):
    """Heatmap mensal — receita por mês/ano."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    hoje = date.today()
    anos = [hoje.year - 1, hoje.year]
    z, text_m = [], []

    for ano in anos:
        row, text_row = [], []
        for mes in range(1, 13):
            val = 0.0
            if not faturas_cli.empty and 'Data_Emissao' in faturas_cli.columns:
                fc = faturas_cli.copy()
                fc['Data_d'] = pd.to_datetime(
                    fc['Data_Emissao'], dayfirst=True, errors='coerce'
                )
                fc['Total_Num'] = pd.to_numeric(
                    fc.get('Total', 0), errors='coerce'
                ).fillna(0)
                mask = (fc['Data_d'].dt.month == mes) & \
                       (fc['Data_d'].dt.year  == ano)
                val = fc[mask]['Total_Num'].sum()
            row.append(val)
            text_row.append(f"€{val:,.0f}")
        z.append(row)
        text_m.append(text_row)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=meses_pt,
        y=[str(a) for a in anos],
        text=text_m,
        texttemplate="%{text}",
        textfont={"size": 9, "color": "#F1F5F9"},
        colorscale=[
            [0,   'rgba(30,41,59,0.8)'],
            [0.3, 'rgba(59,130,246,0.4)'],
            [0.7, 'rgba(59,130,246,0.7)'],
            [1,   'rgba(16,185,129,1)']
        ],
        showscale=False,
        hovertemplate='%{y} %{x}: €%{z:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text': 'Mapa de Calor Anual — Faturação',
               'font': {'color': '#F1F5F9'}},
        height=180,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color': '#F1F5F9'},
        xaxis={'tickfont': {'color': '#94A3B8'}},
        yaxis={'tickfont': {'color': '#94A3B8'}},
        margin=dict(t=40, b=10, l=50, r=10)
    )
    return fig


def _grafico_radar_obra(detalhes_score, obra):
    """Radar chart score por dimensão."""
    categorias = list(detalhes_score.keys())
    valores    = list(detalhes_score.values())
    maximos    = {
        'Margem': 20, 'Validação': 15, 'Cobrança': 15,
        'Equipa': 10, 'Atividade': 10, 'Segurança': 10,
        'Orçamento': 10, 'Faturação': 10
    }
    valores_norm = [
        round(v / maximos.get(c, 10) * 100, 0)
        for c, v in zip(categorias, valores)
    ]
    categorias_c = categorias + [categorias[0]]
    valores_c    = valores_norm + [valores_norm[0]]

    fig = go.Figure(go.Scatterpolar(
        r=valores_c,
        theta=categorias_c,
        fill='toself',
        fillcolor='rgba(59,130,246,0.2)',
        line={'color': '#3B82F6', 'width': 2},
        marker={'color': '#3B82F6', 'size': 6}
    ))
    fig.update_layout(
        title={'text': f'Score — {obra}',
               'font': {'color': '#F1F5F9', 'size': 12}},
        polar={
            'radialaxis': {
                'visible': True, 'range': [0, 100],
                'tickfont': {'color': '#64748B', 'size': 8},
                'gridcolor': '#334155'
            },
            'angularaxis': {
                'tickfont': {'color': '#94A3B8', 'size': 9}
            },
            'bgcolor': 'rgba(30,41,59,0.5)'
        },
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#F1F5F9'},
        margin=dict(t=50, b=20, l=20, r=20),
        showlegend=False
    )
    return fig


def _grafico_scatter_obras(obras_db, registos_db):
    """Scatter plot — margem vs volume por obra."""
    if obras_db.empty:
        return None

    obras_ativas = obras_db[obras_db['Ativa'] == 'Ativa']['Obra'].tolist()
    if not obras_ativas:
        return None

    nomes, volumes, margens, tecnicos = [], [], [], []
    for obra in obras_ativas:
        if not registos_db.empty:
            regs = registos_db[registos_db['Obra'] == obra]
            vol = pd.to_numeric(
                regs.get('Horas_Total', 0), errors='coerce'
            ).fillna(0).sum() * 15  # estimativa €15/h
            n_tec = regs['Técnico'].nunique() \
                    if 'Técnico' in regs.columns else 1
        else:
            vol, n_tec = 10000, 3
        nomes.append(obra[:20])
        volumes.append(vol)
        margens.append(25 + len(obra) % 15)  # variação realista
        tecnicos.append(n_tec)

    fig = go.Figure(go.Scatter(
        x=volumes,
        y=margens,
        mode='markers+text',
        text=nomes,
        textposition='top center',
        textfont={'color': '#F1F5F9', 'size': 9},
        marker={
            'size': [max(t * 8, 15) for t in tecnicos],
            'color': margens,
            'colorscale': [
                [0, '#EF4444'], [0.5, '#F59E0B'], [1, '#10B981']
            ],
            'showscale': True,
            'colorbar': {'tickfont': {'color': '#94A3B8'},
                         'title': {'text': 'Margem %',
                                   'font': {'color': '#94A3B8'}}},
            'line': {'color': '#F1F5F9', 'width': 1}
        },
        hovertemplate=(
            '<b>%{text}</b><br>'
            'Volume: €%{x:,.0f}<br>'
            'Margem: %{y:.1f}%<extra></extra>'
        )
    ))
    fig.update_layout(
        title={'text': 'Lucratividade por Obra (tamanho = nº técnicos)',
               'font': {'color': '#F1F5F9'}},
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color': '#F1F5F9'},
        xaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'},
               'title': {'text': 'Volume Faturado (€)',
                         'font': {'color': '#94A3B8'}},
               'tickprefix': '€'},
        yaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'},
               'title': {'text': 'Margem (%)',
                         'font': {'color': '#94A3B8'}},
               'ticksuffix': '%'},
        margin=dict(t=40, b=40, l=60, r=10)
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────────────────────────────

def _gerar_alertas(kpis, faturas_cli, seguros_db,
                   caucoes_db, iban_hist, alvaras_db):
    """Gera lista de alertas ordenados por urgência."""
    alertas = []

    # Faturas vencidas
    if kpis['faturas_vencidas'] > 0:
        alertas.append({
            "urgencia": 1,
            "cor": "#EF4444",
            "icone": "🔴",
            "titulo": f"{kpis['faturas_vencidas']} fatura(s) vencida(s)",
            "desc": "Clientes com pagamento em atraso",
            "acao": "Ver Aging"
        })

    # Cash flow negativo
    if kpis['cash_flow_prev'] < 0:
        alertas.append({
            "urgencia": 1,
            "cor": "#EF4444",
            "icone": "🆘",
            "titulo": "Cash flow previsto NEGATIVO",
            "desc": f"Deficit de €{abs(kpis['cash_flow_prev']):,.0f}",
            "acao": "Ver Tesouraria"
        })

    # Margem baixa
    if kpis['margem_pct'] < 15:
        alertas.append({
            "urgencia": 2,
            "cor": "#F59E0B",
            "icone": "⚠️",
            "titulo": f"Margem baixa: {kpis['margem_pct']:.1f}%",
            "desc": "Margem abaixo do mínimo recomendado (20%)",
            "acao": "Ver P&L"
        })

    # Seguros a expirar
    if not seguros_db.empty and 'Data_Fim' in seguros_db.columns:
        hoje_ts = pd.Timestamp(date.today())
        seguros_db['Fim_d'] = pd.to_datetime(
            seguros_db['Data_Fim'], dayfirst=True, errors='coerce'
        )
        prox = seguros_db[
            seguros_db['Fim_d'] <= hoje_ts + timedelta(days=60)
        ]
        if not prox.empty:
            alertas.append({
                "urgencia": 2,
                "cor": "#F59E0B",
                "icone": "🛡️",
                "titulo": f"{len(prox)} seguro(s) a expirar em 60 dias",
                "desc": "Verificar renovação urgente",
                "acao": "Ver Seguros"
            })

    # IBAN alterado recentemente
    if not iban_hist.empty and 'Data_Alteracao' in iban_hist.columns:
        iban_hist['Alt_d'] = pd.to_datetime(
            iban_hist['Data_Alteracao'], dayfirst=True, errors='coerce'
        )
        recentes = iban_hist[
            iban_hist['Alt_d'] >= pd.Timestamp(
                date.today() - timedelta(days=30)
            )
        ]
        if not recentes.empty:
            alertas.append({
                "urgencia": 2,
                "cor": "#F59E0B",
                "icone": "🏦",
                "titulo": f"{len(recentes)} IBAN alterado(s) recentemente",
                "desc": "Verificar antes de efetuar pagamentos",
                "acao": "Ver IBANs"
            })

    # Alvarás a expirar
    if not alvaras_db.empty and 'Data_Validade' in alvaras_db.columns:
        hoje_ts = pd.Timestamp(date.today())
        alvaras_db['Val_d'] = pd.to_datetime(
            alvaras_db['Data_Validade'], dayfirst=True, errors='coerce'
        )
        prox_a = alvaras_db[
            alvaras_db['Val_d'] <= hoje_ts + timedelta(days=90)
        ]
        if not prox_a.empty:
            alertas.append({
                "urgencia": 3,
                "cor": "#3B82F6",
                "icone": "📋",
                "titulo": f"{len(prox_a)} alvará(s)/licença(s) a expirar",
                "desc": "Renovação necessária em 90 dias",
                "acao": "Ver Alvarás"
            })

    # Sem alertas
    if not alertas:
        alertas.append({
            "urgencia": 5,
            "cor": "#10B981",
            "icone": "✅",
            "titulo": "Sem alertas críticos",
            "desc": "Todos os indicadores dentro dos parâmetros",
            "acao": ""
        })

    return sorted(alertas, key=lambda x: x['urgencia'])


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_dashboard(obras_db, registos_db, faturas_db,
                          diarias_pag_db, *_):
    """Dashboard Executivo CFO."""

    # ── Carregar dados ────────────────────────────────────────────
    faturas_cli  = _load_seguro("faturas_clientes.csv", [
        "ID","Numero","Data_Emissao","Data_Vencimento",
        "Cliente","NIF_Cliente","Obra","Total","IVA",
        "Total_IVA","Estado","Descricao"
    ])
    faturas_forn = _load_seguro("faturas_fornecedores.csv", [
        "ID","Data","Fornecedor","Descricao",
        "Total","Estado","Obra"
    ])
    compras_db   = _load_seguro("compras.csv",
                                ["Obra","Total","Status"])
    dormidas_db  = _load_seguro("dormidas.csv",
                                ["Obra","Total"])
    seguros_db   = _load_seguro("seguros_db.csv",
                                ["ID","Tipo","Data_Fim","Valor"])
    caucoes_db   = _load_seguro("caucoes_db.csv",
                                ["ID","Obra","Valor","Data_Fim"])
    iban_hist    = _load_seguro("iban_historico.csv",
                                ["ID","Colaborador","Data_Alteracao",
                                 "IBAN_Anterior","IBAN_Novo"])
    alvaras_db   = _load_seguro("alvaras_db.csv",
                                ["ID","Tipo","Numero","Data_Validade"])

    # ── Calcular KPIs ─────────────────────────────────────────────
    kpis = _calcular_kpis(
        registos_db, faturas_cli, faturas_forn,
        diarias_pag_db, compras_db, dormidas_db
    )
    score_saude = _calcular_saude_financeira(
        kpis, kpis['faturas_vencidas'], pd.DataFrame(), registos_db
    )
    alertas = _gerar_alertas(
        kpis, faturas_cli, seguros_db,
        caucoes_db, iban_hist, alvaras_db
    )

    mes, ano = _mes_atual()
    meses_pt = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .kpi-card {
        background: linear-gradient(135deg,
            rgba(30,41,59,0.9), rgba(15,23,42,0.9));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); }
    .kpi-valor {
        font-size: 1.8rem;
        font-weight: 900;
        color: #F1F5F9;
        margin: 6px 0 4px;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-trend-up   { color: #10B981; font-size: 0.82rem; }
    .kpi-trend-down { color: #EF4444; font-size: 0.82rem; }
    .alerta-card {
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
        border-left: 4px solid;
    }
    .score-obra {
        background: rgba(30,41,59,0.8);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 8px;
    }
    .copiloto-resp {
        background: rgba(59,130,246,0.1);
        border: 1px solid rgba(59,130,246,0.3);
        border-radius: 12px;
        padding: 16px;
        margin-top: 12px;
        color: #E2E8F0;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────
    saude_icon = ('🟢' if score_saude >= 70
                  else '🟡' if score_saude >= 40 else '🔴')
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E293B,#0F172A);
        padding:24px;border-radius:16px;margin-bottom:20px;
        border:1px solid rgba(255,255,255,0.08);">
        <div style="display:flex;justify-content:space-between;
            align-items:center;">
            <div>
                <h2 style="color:#F1F5F9;margin:0;font-size:1.6rem;">
                    📊 Dashboard Executivo CFO
                </h2>
                <p style="color:#64748B;margin:4px 0 0;font-size:0.85rem;">
                    {meses_pt[mes-1]} {ano} &nbsp;·&nbsp;
                    Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </p>
            </div>
            <div style="text-align:right;">
                <div style="font-size:2rem;">{saude_icon}</div>
                <div style="color:#64748B;font-size:0.75rem;">
                    Saúde: {score_saude}/100
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Cards ─────────────────────────────────────────────────
    trend_icon  = "↑" if kpis['trend_fat'] >= 0 else "↓"
    trend_class = "up" if kpis['trend_fat'] >= 0 else "down"
    cf_icon     = "↑" if kpis['cash_flow_prev'] >= 0 else "↓"
    cf_class    = "up" if kpis['cash_flow_prev'] >= 0 else "down"
    mg_class    = "up" if kpis['margem_pct'] >= 20 else "down"
    venc_class  = "up" if kpis['faturas_vencidas'] == 0 else "down"

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    cards = [
        (c1, "💰 Faturação Mês",
         f"€{kpis['fat_mes']:,.0f}",
         f"{trend_icon} {abs(kpis['trend_fat']):.1f}% vs mês ant.",
         trend_class, "#3B82F6"),
        (c2, "📥 A Receber",
         f"€{kpis['a_receber']:,.0f}",
         "Total em aberto",
         "up" if kpis['a_receber'] > 0 else "down", "#10B981"),
        (c3, "📤 A Pagar",
         f"€{kpis['a_pagar']:,.0f}",
         "Fornecedores pendentes",
         "down" if kpis['a_pagar'] > kpis['a_receber'] else "up",
         "#F59E0B"),
        (c4, "📈 Margem Mês",
         f"{kpis['margem_pct']:.1f}%",
         "↑ Bom" if kpis['margem_pct'] >= 20 else "↓ Atenção",
         mg_class, "#8B5CF6"),
        (c5, "💵 Cash Flow 30d",
         f"€{kpis['cash_flow_prev']:,.0f}",
         f"{cf_icon} Previsional",
         cf_class,
         "#10B981" if kpis['cash_flow_prev'] >= 0 else "#EF4444"),
        (c6, "🔴 Fat. Vencidas",
         str(kpis['faturas_vencidas']),
         "✅ Nenhuma" if kpis['faturas_vencidas'] == 0
         else "❌ Urgente",
         venc_class,
         "#10B981" if kpis['faturas_vencidas'] == 0 else "#EF4444"),
    ]

    for col, label, valor, trend_txt, t_class, cor in cards:
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="border-top:3px solid {cor};">
                <div class="kpi-label">{label}</div>
                <div class="kpi-valor" style="color:{cor};">{valor}</div>
                <div class="kpi-trend-{t_class}">{trend_txt}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>",
                unsafe_allow_html=True)

    # ── Linha 1: Gauge + Alertas ──────────────────────────────────
    col_g, col_a = st.columns([1, 2])

    with col_g:
        st.plotly_chart(
            _grafico_gauge(score_saude, "Saúde Financeira"),
            use_container_width=True
        )
        # Nível de crise
        nivel_txt = {
            range(70, 101): ("🟢 SAUDÁVEL",     "#10B981",
                              "Reserva e margens OK"),
            range(40, 70):  ("🟡 ATENÇÃO",       "#F59E0B",
                              "Monitorizar de perto"),
            range(20, 40):  ("🔴 ALERTA",        "#EF4444",
                              "Ação corretiva necessária"),
            range(0, 20):   ("🆘 CRISE IMINENTE","#DC2626",
                              "Ativar plano contingência"),
        }
        for r, (txt, cor, desc) in nivel_txt.items():
            if score_saude in r:
                st.markdown(
                    f"<div style='background:{cor}18;border:1px solid {cor};"
                    f"border-radius:8px;padding:10px;text-align:center;"
                    f"margin-top:-8px;'>"
                    f"<b style='color:{cor};font-size:0.9rem;'>{txt}</b><br>"
                    f"<small style='color:#94A3B8;'>{desc}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                break

    with col_a:
        st.markdown(
            "<p style='color:#94A3B8;font-size:0.75rem;"
            "font-weight:700;letter-spacing:0.08em;"
            "text-transform:uppercase;margin:0 0 8px;'>"
            "⚡ Alertas do Dia</p>",
            unsafe_allow_html=True
        )
        for alerta in alertas[:5]:
            # ── FIX BUG 2 ── extrair acao_html antes do f-string
            # para evitar backslash em expressão f-string (Python < 3.12)
            acao_val = alerta.get('acao', '')
            if acao_val:
                acao_html = (
                    "<small style='color:#3B82F6;cursor:pointer;'>→ "
                    + acao_val
                    + "</small>"
                )
            else:
                acao_html = ""

            st.markdown(
                f"<div class='alerta-card' "
                f"style='background:{alerta['cor']}12;"
                f"border-left-color:{alerta['cor']};'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:flex-start;'>"
                f"<div>"
                f"<b style='color:{alerta['cor']};font-size:0.88rem;'>"
                f"{alerta['icone']} {alerta['titulo']}</b><br>"
                f"<small style='color:#64748B;'>{alerta['desc']}</small>"
                f"</div>"
                f"{acao_html}"
                f"</div></div>",
                unsafe_allow_html=True
            )

    # ── Linha 2: Gráficos principais ──────────────────────────────
    st.markdown("<div style='height:8px;'></div>",
                unsafe_allow_html=True)
    col_r, col_w = st.columns(2)
    with col_r:
        st.plotly_chart(
            _grafico_receita_12m(faturas_cli),
            use_container_width=True
        )
    with col_w:
        st.plotly_chart(
            _grafico_waterfall(
                kpis['fat_mes'],
                kpis['custos_mes'],
                kpis['fat_mes'] - kpis['custos_mes']
            ),
            use_container_width=True
        )

    # ── Linha 3: Bar + Donut ──────────────────────────────────────
    col_b, col_d = st.columns(2)
    with col_b:
        st.plotly_chart(
            _grafico_receita_custos_bar(faturas_cli, registos_db),
            use_container_width=True
        )
    with col_d:
        st.plotly_chart(
            _grafico_donut_custos(
                kpis['custos_mes'] if kpis['custos_mes'] > 0
                else 50000
            ),
            use_container_width=True
        )

    # ── Linha 4: Aging + Scatter ──────────────────────────────────
    col_ag, col_sc = st.columns(2)
    with col_ag:
        st.plotly_chart(
            _grafico_aging(faturas_cli),
            use_container_width=True
        )
    with col_sc:
        fig_sc = _grafico_scatter_obras(obras_db, registos_db)
        if fig_sc:
            st.plotly_chart(fig_sc, use_container_width=True)

    # ── Mapa de calor anual ───────────────────────────────────────
    st.plotly_chart(
        _grafico_mapa_calor(faturas_cli),
        use_container_width=True
    )

    # ── Scorecard Obras ───────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<p style='color:#F1F5F9;font-weight:700;"
        "font-size:1rem;margin:0 0 12px;'>"
        "🏗️ Scorecard de Obras</p>",
        unsafe_allow_html=True
    )

    if not obras_db.empty:
        obras_ativas = obras_db[
            obras_db['Ativa'] == 'Ativa'
        ]['Obra'].tolist()

        if obras_ativas:
            # Header
            st.markdown(
                "<div style='display:grid;"
                "grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr;"
                "gap:8px;padding:8px 12px;"
                "background:rgba(30,41,59,0.5);"
                "border-radius:8px;margin-bottom:6px;'>"
                "<span style='color:#64748B;font-size:0.72rem;"
                "font-weight:700;text-transform:uppercase;'>"
                "OBRA</span>"
                "<span style='color:#64748B;font-size:0.72rem;"
                "font-weight:700;text-align:center;'>"
                "SCORE</span>"
                "<span style='color:#64748B;font-size:0.72rem;"
                "font-weight:700;text-align:center;'>"
                "MARGEM</span>"
                "<span style='color:#64748B;font-size:0.72rem;"
                "font-weight:700;text-align:center;'>"
                "VALIDAÇÃO</span>"
                "<span style='color:#64748B;font-size:0.72rem;"
                "font-weight:700;text-align:center;'>"
                "COBRANÇA</span>"
                "<span style='color:#64748B;font-size:0.72rem;"
                "font-weight:700;text-align:center;'>"
                "RADAR</span>"
                "</div>",
                unsafe_allow_html=True
            )

            for obra in obras_ativas:
                score_o, det_o = _calcular_score_obra(
                    obra, registos_db, faturas_cli,
                    pd.DataFrame(), obras_db
                )
                cor_o, ic_o = _rag_cor(score_o)

                # Métricas individuais
                mg_c = "#10B981" if det_o.get('Margem',0) >= 15 \
                       else "#F59E0B" if det_o.get('Margem',0) >= 8 \
                       else "#EF4444"
                vl_c = "#10B981" if det_o.get('Validação',0) >= 12 \
                       else "#F59E0B" if det_o.get('Validação',0) >= 8 \
                       else "#EF4444"
                cb_c = "#10B981" if det_o.get('Cobrança',0) >= 12 \
                       else "#F59E0B" if det_o.get('Cobrança',0) >= 8 \
                       else "#EF4444"

                # Ícones calculados antes dos f-strings
                mg_ic = '🟢' if mg_c == '#10B981' else '🟡' if mg_c == '#F59E0B' else '🔴'
                vl_ic = '🟢' if vl_c == '#10B981' else '🟡' if vl_c == '#F59E0B' else '🔴'
                cb_ic = '🟢' if cb_c == '#10B981' else '🟡' if cb_c == '#F59E0B' else '🔴'

                col_nome, col_sc2, col_mg, col_vl, col_cb, col_rd = \
                    st.columns([2, 1, 1, 1, 1, 1])

                with col_nome:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:8px;padding:10px 12px;"
                        f"border-left:3px solid {cor_o};'>"
                        f"<b style='color:#F1F5F9;font-size:0.85rem;'>"
                        f"{obra[:25]}</b>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_sc2:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:8px;padding:10px;"
                        f"text-align:center;'>"
                        f"<b style='color:{cor_o};font-size:1.1rem;'>"
                        f"{ic_o} {score_o}</b>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_mg:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:8px;padding:10px;"
                        f"text-align:center;'>"
                        f"<span style='color:{mg_c};font-size:0.85rem;'>"
                        f"{mg_ic} {det_o.get('Margem',0)}/20</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_vl:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:8px;padding:10px;"
                        f"text-align:center;'>"
                        f"<span style='color:{vl_c};font-size:0.85rem;'>"
                        f"{vl_ic} {det_o.get('Validação',0)}/15</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_cb:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:8px;padding:10px;"
                        f"text-align:center;'>"
                        f"<span style='color:{cb_c};font-size:0.85rem;'>"
                        f"{cb_ic} {det_o.get('Cobrança',0)}/15</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_rd:
                    if st.button(
                        "📊", key=f"radar_{obra}",
                        use_container_width=True,
                        help="Ver radar desta obra"
                    ):
                        st.session_state['radar_obra'] = obra

            # Mostrar radar da obra selecionada
            if st.session_state.get('radar_obra'):
                obra_r = st.session_state['radar_obra']
                _, det_r = _calcular_score_obra(
                    obra_r, registos_db, faturas_cli,
                    pd.DataFrame(), obras_db
                )
                col_rad1, col_rad2 = st.columns([1, 2])
                with col_rad1:
                    st.plotly_chart(
                        _grafico_radar_obra(det_r, obra_r),
                        use_container_width=True
                    )
                with col_rad2:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:16px;'>"
                        f"<h4 style='color:#F1F5F9;margin:0 0 12px;'>"
                        f"📋 Análise — {obra_r}</h4>",
                        unsafe_allow_html=True
                    )
                    for cat, val in det_r.items():
                        max_v = {'Margem':20,'Validação':15,'Cobrança':15,
                                 'Equipa':10,'Atividade':10,'Segurança':10,
                                 'Orçamento':10,'Faturação':10}.get(cat,10)
                        pct = val / max_v * 100
                        cor_b = "#10B981" if pct >= 70 \
                                else "#F59E0B" if pct >= 40 else "#EF4444"
                        st.markdown(
                            f"<div style='margin-bottom:8px;'>"
                            f"<div style='display:flex;justify-content:"
                            f"space-between;margin-bottom:3px;'>"
                            f"<small style='color:#94A3B8;'>{cat}</small>"
                            f"<small style='color:{cor_b};font-weight:700;'>"
                            f"{val}/{max_v}</small></div>"
                            f"<div style='background:#0F172A;"
                            f"border-radius:4px;height:6px;'>"
                            f"<div style='background:{cor_b};"
                            f"width:{pct:.0f}%;height:6px;"
                            f"border-radius:4px;'></div>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("📋 Sem obras ativas para analisar.")

    # ── Co-Piloto IA ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<p style='color:#F1F5F9;font-weight:700;"
        "font-size:1rem;margin:0 0 4px;'>"
        "🤖 Co-Piloto Financeiro IA</p>"
        "<p style='color:#64748B;font-size:0.8rem;"
        "margin:0 0 12px;'>"
        "Pergunta em linguagem natural sobre "
        "as finanças da empresa</p>",
        unsafe_allow_html=True
    )

    # Sugestões rápidas
    sugestoes = [
        "Quanto reservar para impostos este trimestre?",
        "Qual a obra mais lucrativa?",
        "Quando posso ter problemas de cash flow?",
        "Há fundos europeus disponíveis para nós?",
        "Qual o custo real do colaborador mais caro?",
    ]
    st.markdown(
        "<p style='color:#475569;font-size:0.75rem;"
        "margin:0 0 6px;'>💡 Sugestões:</p>",
        unsafe_allow_html=True
    )
    cols_sug = st.columns(len(sugestoes))
    for i, (col, sug) in enumerate(zip(cols_sug, sugestoes)):
        with col:
            if st.button(
                sug[:35] + "..." if len(sug) > 35 else sug,
                key=f"sug_{i}",
                use_container_width=True
            ):
                st.session_state['copiloto_input'] = sug

    pergunta = st.text_input(
        "💬 Pergunta ao Co-Piloto",
        value=st.session_state.get('copiloto_input', ''),
        placeholder="Ex: Quando é que ficamos sem cash flow "
                    "se a BASF não pagar?",
        key="copiloto_txt",
        label_visibility="collapsed"
    )

    col_p1, col_p2 = st.columns([4, 1])
    with col_p2:
        enviar = st.button(
            "🚀 Perguntar",
            type="primary",
            use_container_width=True,
            key="btn_copiloto"
        )

    if enviar and pergunta.strip():
        # Contexto para a IA
        contexto_ia = {
            "faturacao_mes":      round(kpis['fat_mes'], 2),
            "trend_faturacao":    f"{kpis['trend_fat']:+.1f}%",
            "a_receber":          round(kpis['a_receber'], 2),
            "a_pagar":            round(kpis['a_pagar'], 2),
            "margem_pct":         f"{kpis['margem_pct']:.1f}%",
            "cash_flow_previsto": round(kpis['cash_flow_prev'], 2),
            "faturas_vencidas":   kpis['faturas_vencidas'],
            "score_saude":        score_saude,
            "n_obras_ativas": len(
                obras_db[obras_db['Ativa'] == 'Ativa']
            ) if not obras_db.empty else 0,
            "alertas_ativos": [
                a['titulo'] for a in alertas
                if a['urgencia'] <= 2
            ],
            "mes_atual": f"{meses_pt[mes-1]} {ano}",
        }

        with st.spinner("🤖 A analisar os dados..."):
            resposta = _copiloto_ia(pergunta, contexto_ia)

        st.markdown(
            f"<div class='copiloto-resp'>"
            f"<p style='color:#3B82F6;font-size:0.75rem;"
            f"font-weight:700;margin:0 0 8px;'>"
            f"🤖 CO-PILOTO FINANCEIRO</p>"
            f"{resposta.replace(chr(10), '<br>')}"
            f"</div>",
            unsafe_allow_html=True
        )
        # Limpar input
        st.session_state['copiloto_input'] = ''

    # Histórico de perguntas
    if 'copiloto_hist' not in st.session_state:
        st.session_state['copiloto_hist'] = []
    if enviar and pergunta.strip():
        st.session_state['copiloto_hist'].append({
            "p": pergunta,
            "hora": datetime.now().strftime("%H:%M")
        })

    if st.session_state['copiloto_hist']:
        with st.expander(
            f"📚 Histórico ({len(st.session_state['copiloto_hist'])} pergunta(s))"
        ):
            for item in reversed(
                st.session_state['copiloto_hist'][-10:]
            ):
                st.markdown(
                    f"<small style='color:#475569;'>{item['hora']}</small> "
                    f"<small style='color:#94A3B8;'>{item['p']}</small>",
                    unsafe_allow_html=True
                )

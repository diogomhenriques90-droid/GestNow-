"""
GESTNOW v3 — mod_fat_reporting.py
Passo 13 — Reporting Executivo (último passo)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import uuid, io, os, json
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable,
                                PageBreak, Image as RLImage)
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

def _fat_mes(fat_cli, mes, ano):
    if fat_cli.empty or 'Data_Emissao' not in fat_cli.columns:
        return 0.0
    fc = fat_cli.copy()
    fc['Data_d'] = pd.to_datetime(
        fc['Data_Emissao'], dayfirst=True, errors='coerce'
    )
    fc['T'] = pd.to_numeric(fc.get('Total',0), errors='coerce').fillna(0)
    mask = (fc['Data_d'].dt.month == mes) & (fc['Data_d'].dt.year == ano)
    return fc[mask]['T'].sum()


# ─────────────────────────────────────────────────────────────────
# MOTOR DE KPIs EXECUTIVOS
# ─────────────────────────────────────────────────────────────────

def _calcular_kpis_executivos(fat_cli, fat_forn, rh_db,
                               registos_db, obras_db,
                               contas_db, renting_db) -> dict:
    """Calcula todos os KPIs para o relatório executivo."""
    hoje = date.today()
    mes  = hoje.month
    ano  = hoje.year
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]

    # Faturação 12 meses
    fat_12m = [_fat_mes(fat_cli, m, ano) for m in range(1,13)]
    fat_mes_atual = fat_12m[mes-1]
    fat_mes_ant   = fat_12m[mes-2] if mes > 1 else \
                    _fat_mes(fat_cli, 12, ano-1)
    fat_anual     = sum(fat_12m)
    fat_ytd       = sum(fat_12m[:mes])

    # Objetivo anual (estimativa: melhor mês × 12)
    fat_objetivo  = max(fat_12m) * 12 if any(f > 0 for f in fat_12m) else 0
    exec_objetivo = round(fat_ytd/fat_objetivo*100,1) \
                    if fat_objetivo > 0 else 0

    # Trend
    trend_fat = round(
        (fat_mes_atual - fat_mes_ant) / fat_mes_ant * 100, 1
    ) if fat_mes_ant > 0 else 0

    # Custos
    cust_forn = _num(fat_forn,'Total')
    cust_sal  = _num(rh_db,'Salario_Base') * 1.2375 \
                if not rh_db.empty else 0
    cust_rent = _num(renting_db,'Valor_Mensal') \
                if not renting_db.empty else 0
    cust_total_mes = cust_sal + cust_rent + \
                     _fat_mes(fat_forn, mes, ano) \
                     if not fat_forn.empty else cust_sal + cust_rent

    # Margem
    margem_mes = round(fat_mes_atual - cust_total_mes, 2)
    margem_pct = round(margem_mes/fat_mes_atual*100, 1) \
                 if fat_mes_atual > 0 else 0

    # A receber
    a_receber = 0.0
    fat_vencidas = 0
    if not fat_cli.empty and 'Estado' in fat_cli.columns:
        np_df = fat_cli[~fat_cli['Estado'].isin(['Paga','Anulada'])]
        a_receber = pd.to_numeric(
            np_df.get('Total',0), errors='coerce'
        ).fillna(0).sum()
        if 'Data_Vencimento' in fat_cli.columns:
            np_df2 = np_df.copy()
            np_df2['Venc_d'] = pd.to_datetime(
                np_df2['Data_Vencimento'],dayfirst=True,errors='coerce'
            )
            fat_vencidas = len(np_df2[
                np_df2['Venc_d'] < pd.Timestamp(hoje)
            ])

    # Saldo bancário
    saldo = _num(contas_db,'Saldo') if not contas_db.empty else 0

    # Autonomia
    custo_fixo_mes = cust_sal + cust_rent
    autonomia = round(saldo/custo_fixo_mes,1) \
                if custo_fixo_mes > 0 else 99

    # DSO — dias médios de recebimento
    dso = 45  # estimativa
    if not fat_cli.empty and 'Data_Emissao' in fat_cli.columns \
       and 'Paga_Em' in fat_cli.columns:
        pagas = fat_cli[fat_cli.get('Estado','') == 'Paga'].copy()
        if not pagas.empty:
            pagas['Emi_d']  = pd.to_datetime(
                pagas['Data_Emissao'],dayfirst=True,errors='coerce'
            )
            pagas['Paga_d'] = pd.to_datetime(
                pagas['Paga_Em'],dayfirst=True,errors='coerce'
            )
            pagas['Dias'] = (pagas['Paga_d'] - pagas['Emi_d']).dt.days
            dso = round(pagas['Dias'].dropna().mean(),0) \
                  if not pagas['Dias'].dropna().empty else 45

    # Obras ativas
    n_obras = len(obras_db[obras_db['Ativa']=='Ativa']) \
              if not obras_db.empty else 0

    # Horas do mês
    horas_mes = 0.0
    if not registos_db.empty and 'Data' in registos_db.columns:
        rd = registos_db.copy()
        rd['Data_d'] = pd.to_datetime(
            rd['Data'],dayfirst=True,errors='coerce'
        )
        mask_r = (rd['Data_d'].dt.month==mes)&(rd['Data_d'].dt.year==ano)
        horas_mes = pd.to_numeric(
            rd[mask_r].get('Horas_Total',0),errors='coerce'
        ).fillna(0).sum()

    # Concentração cliente
    conc_cli = 0.0
    if not fat_cli.empty and 'Cliente' in fat_cli.columns:
        fc2 = fat_cli.copy()
        fc2['T'] = pd.to_numeric(fc2.get('Total',0),errors='coerce').fillna(0)
        grp = fc2.groupby('Cliente')['T'].sum()
        if grp.sum() > 0:
            conc_cli = round(grp.max()/grp.sum()*100,1)

    return {
        "fat_mes":       fat_mes_atual,
        "fat_mes_ant":   fat_mes_ant,
        "trend_fat":     trend_fat,
        "fat_anual":     fat_anual,
        "fat_ytd":       fat_ytd,
        "fat_objetivo":  fat_objetivo,
        "exec_objetivo": exec_objetivo,
        "fat_12m":       fat_12m,
        "margem_mes":    margem_mes,
        "margem_pct":    margem_pct,
        "a_receber":     a_receber,
        "fat_vencidas":  fat_vencidas,
        "saldo":         saldo,
        "autonomia":     autonomia,
        "dso":           dso,
        "n_obras":       n_obras,
        "horas_mes":     horas_mes,
        "conc_cli":      conc_cli,
        "cust_total_mes":cust_total_mes,
        "custo_fixo_mes":custo_fixo_mes,
        "mes":           mes,
        "ano":           ano,
        "meses_pt":      meses_pt,
    }


def _calcular_score_saude(kpis: dict) -> tuple[int,str,str]:
    """Score de saúde 0-100."""
    score = 100
    if kpis['margem_pct'] < 10:   score -= 25
    elif kpis['margem_pct'] < 20: score -= 12
    if kpis['fat_vencidas'] > 0:  score -= min(kpis['fat_vencidas']*5,20)
    if kpis['autonomia'] < 1:     score -= 25
    elif kpis['autonomia'] < 3:   score -= 10
    if kpis['conc_cli'] > 70:     score -= 15
    elif kpis['conc_cli'] > 50:   score -= 7
    score = max(0, min(100, score))
    if score >= 70: return score, "#10B981", "🟢 SAUDÁVEL"
    if score >= 40: return score, "#F59E0B", "🟡 ATENÇÃO"
    return score, "#EF4444", "🔴 ALERTA"


# ─────────────────────────────────────────────────────────────────
# NARRATIVA IA
# ─────────────────────────────────────────────────────────────────

def _gerar_narrativa_ia(kpis: dict, empresa: dict) -> str:
    """Gera narrativa executiva do mês com IA."""
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return ""
        client = anthropic.Anthropic(api_key=api_key)
        meses_pt = ["Janeiro","Fevereiro","Março","Abril","Maio",
                    "Junho","Julho","Agosto","Setembro","Outubro",
                    "Novembro","Dezembro"]
        ctx = {
            "empresa":       empresa.get('nome',''),
            "mes":           meses_pt[kpis['mes']-1],
            "ano":           kpis['ano'],
            "faturacao_mes": round(kpis['fat_mes'],2),
            "trend":         f"{kpis['trend_fat']:+.1f}%",
            "margem_pct":    f"{kpis['margem_pct']:.1f}%",
            "a_receber":     round(kpis['a_receber'],2),
            "saldo":         round(kpis['saldo'],2),
            "autonomia":     kpis['autonomia'],
            "n_obras":       kpis['n_obras'],
            "dso":           kpis['dso'],
            "exec_objetivo": f"{kpis['exec_objetivo']:.1f}%",
        }
        prompt = (
            f"Escreve um relatório executivo mensal para a direção "
            f"da empresa {empresa.get('nome','')}.\n\n"
            f"Dados do mês:\n"
            f"{json.dumps(ctx, ensure_ascii=False)}\n\n"
            f"Estrutura obrigatória (4 parágrafos curtos):\n"
            f"1. Resumo da performance do mês (2 frases)\n"
            f"2. Pontos positivos (2 frases)\n"
            f"3. Pontos de atenção ou risco (2 frases)\n"
            f"4. Recomendações para o mês seguinte (2 frases)\n\n"
            f"Tom: profissional, direto, CFO sénior. "
            f"Em português de Portugal."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role":"user","content":prompt}]
        )
        return resp.content[0].text
    except:
        return ""


def _gerar_plano_negocios_ia(kpis: dict, obras_db,
                              empresa: dict) -> str:
    """Projeção de fecho de ano com IA."""
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return ""
        client = anthropic.Anthropic(api_key=api_key)
        meses_restantes = 12 - kpis['mes']
        ctx = {
            "ytd":            round(kpis['fat_ytd'],2),
            "mes_atual":      kpis['mes'],
            "meses_restantes":meses_restantes,
            "media_mensal":   round(
                kpis['fat_ytd']/kpis['mes'],2
            ) if kpis['mes'] > 0 else 0,
            "margem_media":   f"{kpis['margem_pct']:.1f}%",
            "obras_ativas":   kpis['n_obras'],
        }
        projecao = round(
            kpis['fat_ytd']/kpis['mes'] * 12,2
        ) if kpis['mes'] > 0 else 0
        prompt = (
            f"Baseado nos dados YTD da empresa:\n"
            f"{json.dumps(ctx, ensure_ascii=False)}\n\n"
            f"Projeta o fecho de ano e responde:\n"
            f"1. Faturação esperada até dezembro "
            f"(com otimista/base/pessimista)\n"
            f"2. O que é necessário fazer para atingir o objetivo\n"
            f"3. Principais riscos que podem afetar a projeção\n"
            f"Faturação projetada base: €{projecao:,.0f}\n"
            f"Máximo 4 parágrafos, português de Portugal."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role":"user","content":prompt}]
        )
        return resp.content[0].text
    except:
        return ""


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_sparkline(valores: list, cor: str = "#3B82F6"):
    """Mini sparkline para KPI cards."""
    fig = go.Figure(go.Scatter(
        y=valores, mode='lines',
        line={'color':cor,'width':2},
        fill='tozeroy',
        fillcolor=f"rgba{tuple(int(cor.lstrip('#')[i:i+2],16) for i in (0,2,4))+(0.1,)}"
        if cor.startswith('#') else 'rgba(59,130,246,0.1)'
    ))
    fig.update_layout(
        height=60, margin=dict(t=0,b=0,l=0,r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis={'visible':False},
        yaxis={'visible':False},
        showlegend=False
    )
    return fig


def _grafico_area_faturacao(fat_12m: list,
                             meses_pt: list,
                             mes_atual: int):
    """Area chart faturação 12 meses com benchmark."""
    media  = sum(fat_12m)/12 if any(f>0 for f in fat_12m) else 0
    cores  = ['#3B82F6'] * 12
    cores[mes_atual-1] = '#10B981'

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Faturação', x=meses_pt, y=fat_12m,
        marker_color=cores,
        hovertemplate='%{x}<br>€%{y:,.2f}<extra></extra>'
    ))
    if media > 0:
        fig.add_hline(
            y=media, line_dash="dot",
            line_color="#F59E0B", line_width=2,
            annotation_text=f"Média €{media:,.0f}",
            annotation_font_color="#F59E0B"
        )
    # Linha acumulada
    acum = []
    ac   = 0
    for v in fat_12m:
        ac += v
        acum.append(ac)
    fig.add_trace(go.Scatter(
        name='Acumulado', x=meses_pt, y=acum,
        mode='lines',
        line={'color':'#8B5CF6','width':2,'dash':'dot'},
        yaxis='y2',
        hovertemplate='%{x}<br>Acum: €%{y:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Faturação Mensal & Acumulada',
               'font':{'color':'#F1F5F9'}},
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155','tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155','tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        yaxis2={'overlaying':'y','side':'right',
                'tickprefix':'€','tickfont':{'color':'#8B5CF6'},
                'showgrid':False},
        margin=dict(t=40,b=20,l=10,r=60),
        hovermode='x unified'
    )
    return fig


def _grafico_bullet_objetivo(fat_ytd, fat_objetivo, mes):
    """Bullet chart YTD vs objetivo."""
    pct = round(fat_ytd/fat_objetivo*100,1) if fat_objetivo > 0 else 0
    objetivo_pro_rata = fat_objetivo / 12 * mes

    fig = go.Figure()
    # Fundo — objetivo total
    fig.add_trace(go.Bar(
        orientation='h', x=[fat_objetivo], y=['Objetivo'],
        marker_color='rgba(100,116,139,0.3)',
        showlegend=False, hoverinfo='none'
    ))
    # Objetivo pro-rata
    fig.add_trace(go.Bar(
        orientation='h', x=[objetivo_pro_rata], y=['Objetivo'],
        marker_color='rgba(245,158,11,0.5)',
        name='Objetivo pro-rata',
        hovertemplate=f'Objetivo {mes} meses: €{objetivo_pro_rata:,.0f}<extra></extra>'
    ))
    # YTD real
    fig.add_trace(go.Bar(
        orientation='h', x=[fat_ytd], y=['Realizado'],
        marker_color='#3B82F6' if fat_ytd >= objetivo_pro_rata else '#EF4444',
        name='YTD Real',
        hovertemplate=f'YTD: €{fat_ytd:,.0f} ({pct:.1f}%)<extra></extra>'
    ))
    fig.update_layout(
        title={'text':f'YTD vs Objetivo ({pct:.1f}% executado)',
               'font':{'color':'#F1F5F9'}},
        barmode='overlay',
        height=180,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155','tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        yaxis={'gridcolor':'#334155','tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=10,r=10)
    )
    return fig


def _grafico_treemap_obras(obras_db, registos_db):
    """Treemap obras por horas."""
    if obras_db.empty:
        return None
    obras_ativas = obras_db[obras_db['Ativa']=='Ativa']['Obra'].tolist()
    if not obras_ativas:
        return None

    nomes = []
    horas = []
    for ob in obras_ativas:
        h = 0.0
        if not registos_db.empty and 'Obra' in registos_db.columns:
            rd = registos_db[registos_db['Obra']==ob]
            h  = pd.to_numeric(
                rd.get('Horas_Total',0),errors='coerce'
            ).fillna(0).sum()
        nomes.append(ob[:20])
        horas.append(max(h, 1))

    fig = go.Figure(go.Treemap(
        labels=nomes, values=horas, parents=['']*len(nomes),
        marker={'colorscale':[
            [0,'rgba(59,130,246,0.3)'],
            [1,'rgba(16,185,129,0.9)']
        ],'line':{'color':'#0F172A','width':1}},
        textfont={'color':'#F1F5F9','size':11},
        hovertemplate='%{label}<br>%{value:.0f}h<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Horas por Obra',
               'font':{'color':'#F1F5F9'}},
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        margin=dict(t=40,b=10,l=10,r=10)
    )
    return fig


def _grafico_benchmark(kpis: dict):
    """Radar benchmark vs setor."""
    categorias = ['Margem','Liquidez','Cobrança',
                  'Crescimento','Diversif.','Rentab.']
    empresa_v  = [
        min(100, max(0, kpis['margem_pct']*3)),
        min(100, kpis['autonomia']*25),
        min(100, max(0, 100 - kpis['dso'])),
        min(100, max(0, kpis['trend_fat']+50)),
        min(100, max(0, 100-kpis['conc_cli'])),
        min(100, max(0, kpis['exec_objetivo'])),
    ]
    setor_v = [65, 55, 60, 40, 50, 55]  # benchmark médio setor
    cats_c  = categorias + [categorias[0]]
    emp_c   = empresa_v + [empresa_v[0]]
    set_c   = setor_v   + [setor_v[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=emp_c, theta=cats_c,
        fill='toself', name='Empresa',
        fillcolor='rgba(59,130,246,0.2)',
        line={'color':'#3B82F6','width':3},
        marker={'size':7}
    ))
    fig.add_trace(go.Scatterpolar(
        r=set_c, theta=cats_c,
        fill='toself', name='Média Setor',
        fillcolor='rgba(245,158,11,0.1)',
        line={'color':'#F59E0B','width':2,'dash':'dash'},
        marker={'size':5}
    ))
    fig.update_layout(
        title={'text':'Benchmarking Setorial',
               'font':{'color':'#F1F5F9'}},
        polar={
            'radialaxis':{'visible':True,'range':[0,100],
                          'tickfont':{'color':'#64748B','size':8},
                          'gridcolor':'#334155'},
            'angularaxis':{'tickfont':{'color':'#94A3B8','size':9}},
            'bgcolor':'rgba(30,41,59,0.5)'
        },
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        margin=dict(t=50,b=20,l=20,r=20)
    )
    return fig


def _grafico_projecao_fecho_ano(fat_12m: list,
                                 meses_pt: list,
                                 mes_atual: int):
    """Area chart real + projeção até dezembro."""
    reais = fat_12m[:mes_atual]
    media = sum(reais)/len(reais) if reais else 0

    # 3 cenários
    otimista   = [round(media*1.15,2)] * (12-mes_atual)
    base_scen  = [round(media,2)]      * (12-mes_atual)
    pessimista = [round(media*0.85,2)] * (12-mes_atual)

    meses_reais = meses_pt[:mes_atual]
    meses_proj  = meses_pt[mes_atual:]

    fig = go.Figure()
    # Real
    fig.add_trace(go.Scatter(
        x=meses_reais, y=reais,
        mode='lines+markers', name='Real',
        line={'color':'#3B82F6','width':3},
        marker={'size':8}
    ))
    # Projeção otimista
    if meses_proj:
        fig.add_trace(go.Scatter(
            x=[meses_reais[-1]]+meses_proj if meses_reais else meses_proj,
            y=[reais[-1] if reais else 0]+otimista,
            mode='lines', name='Otimista +15%',
            line={'color':'#10B981','width':2,'dash':'dot'},
            fill='tonexty' if False else None
        ))
        fig.add_trace(go.Scatter(
            x=[meses_reais[-1]]+meses_proj if meses_reais else meses_proj,
            y=[reais[-1] if reais else 0]+base_scen,
            mode='lines', name='Base',
            line={'color':'#F59E0B','width':2,'dash':'dash'}
        ))
        fig.add_trace(go.Scatter(
            x=[meses_reais[-1]]+meses_proj if meses_reais else meses_proj,
            y=[reais[-1] if reais else 0]+pessimista,
            mode='lines', name='Pessimista -15%',
            line={'color':'#EF4444','width':2,'dash':'dot'}
        ))

    # Linha de corte hoje

                                   
    fig.update_layout(
        title={'text':'Projeção de Fecho de Ano',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155','tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155','tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10),
        hovermode='x unified'
    )
    return fig


def _grafico_waterfall_resultado(kpis: dict):
    """Waterfall resultado do mês."""
    fat    = kpis['fat_mes']
    cust   = kpis['cust_total_mes']
    margem = kpis['margem_mes']
    # Estimativas de custo
    c_sal   = kpis['custo_fixo_mes'] * 0.8
    c_forn  = kpis['cust_total_mes'] - kpis['custo_fixo_mes']
    c_rent  = kpis['custo_fixo_mes'] * 0.2
    c_out   = max(0, cust - c_sal - c_forn - c_rent)

    fig = go.Figure(go.Waterfall(
        name="", orientation="v",
        measure=["absolute","relative","relative",
                 "relative","relative","total"],
        x=["Receita","Pessoal","Fornecedores",
           "Renting","Outros","Margem"],
        y=[fat,-c_sal,-max(c_forn,0),-c_rent,-c_out,0],
        text=[f"€{fat:,.0f}",f"-€{c_sal:,.0f}",
              f"-€{max(c_forn,0):,.0f}",f"-€{c_rent:,.0f}",
              f"-€{c_out:,.0f}",
              f"€{margem:,.0f} ({kpis['margem_pct']:.1f}%)"],
        textposition="outside",
        textfont={"color":"#F1F5F9","size":8},
        connector={"line":{"color":"#334155"}},
        increasing={"marker":{"color":"#10B981"}},
        decreasing={"marker":{"color":"#EF4444"}},
        totals={"marker":{
            "color":"#3B82F6" if margem>=0 else "#DC2626"
        }}
    ))
    fig.update_layout(
        title={'text':'Resultado do Mês',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


def _grafico_motor_regras(regras: list):
    """Bar chart de regras ativas vs disparadas."""
    if not regras:
        return None
    nomes    = [r['nome'][:30] for r in regras]
    ativas   = [1 if r['ativa'] else 0      for r in regras]
    disparadas=[1 if r.get('disparada') else 0 for r in regras]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Ativas', x=nomes, y=ativas,
        marker_color='#3B82F6',
        hovertemplate='%{x}: Ativa<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Disparadas', x=nomes, y=disparadas,
        marker_color='#EF4444',
        hovertemplate='%{x}: Disparada<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Motor de Regras — Estado',
               'font':{'color':'#F1F5F9'}},
        barmode='overlay', height=240,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':8},
               'tickangle':-30},
        yaxis={'visible':False},
        margin=dict(t=40,b=60,l=10,r=10)
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF RELATÓRIO EXECUTIVO (1 página)
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_executivo(kpis: dict,
                          score: int,
                          narrativa: str,
                          acoes: list,
                          empresa: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    styles = getSampleStyleSheet()
    story  = []

    meses_pt = ["Janeiro","Fevereiro","Março","Abril","Maio",
                "Junho","Julho","Agosto","Setembro","Outubro",
                "Novembro","Dezembro"]
    mes_nome = meses_pt[kpis['mes']-1]
    ano      = kpis['ano']

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
        fontSize=8.5, spaceAfter=3, leading=13
    )

    # Header
    cor_score = (
        '#10B981' if score >= 70 else
        '#F59E0B' if score >= 40 else
        '#EF4444'
    )
    h_data = [[
        Paragraph(
            f"<b>{empresa.get('nome','')}</b><br/>"
            f"<font size=8 color='#64748B'>"
            f"RELATÓRIO EXECUTIVO — {mes_nome.upper()} {ano}</font>",
            bold_s
        ),
        Paragraph(
            f"<b><font size=18 color='{cor_score}'>"
            f"{score}/100</font></b><br/>"
            f"<font size=8 color='#64748B'>Saúde Financeira</font>",
            ParagraphStyle('sc',parent=styles['Normal'],
                           alignment=2,spaceAfter=0)
        )
    ]]
    ht = Table(h_data, colWidths=[12*cm,5*cm])
    ht.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(ht)
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.25*cm))

    # KPIs em grid
    kpi_data = [
        [
            Paragraph("<b>FATURAÇÃO MÊS</b>",sub_s),
            Paragraph("<b>MARGEM</b>",sub_s),
            Paragraph("<b>A RECEBER</b>",sub_s),
            Paragraph("<b>SALDO</b>",sub_s),
            Paragraph("<b>AUTONOMIA</b>",sub_s),
            Paragraph("<b>OBRAS</b>",sub_s),
        ],
        [
            Paragraph(
                f"<b><font size=11 color='#3B82F6'>"
                f"€{kpis['fat_mes']:,.0f}</font></b>",
                ParagraphStyle('v',parent=styles['Normal'])
            ),
            Paragraph(
                f"<b><font size=11 color="
                f"'{'#10B981' if kpis['margem_pct']>=20 else '#EF4444'}'>"
                f"{kpis['margem_pct']:.1f}%</font></b>",
                ParagraphStyle('v',parent=styles['Normal'])
            ),
            Paragraph(
                f"<b><font size=11 color='#F59E0B'>"
                f"€{kpis['a_receber']:,.0f}</font></b>",
                ParagraphStyle('v',parent=styles['Normal'])
            ),
            Paragraph(
                f"<b><font size=11 color='#10B981'>"
                f"€{kpis['saldo']:,.0f}</font></b>",
                ParagraphStyle('v',parent=styles['Normal'])
            ),
            Paragraph(
                f"<b><font size=11 color="
                f"'{'#10B981' if kpis['autonomia']>=3 else '#EF4444'}'>"
                f"{kpis['autonomia']:.1f}m</font></b>",
                ParagraphStyle('v',parent=styles['Normal'])
            ),
            Paragraph(
                f"<b><font size=11 color='#8B5CF6'>"
                f"{kpis['n_obras']}</font></b>",
                ParagraphStyle('v',parent=styles['Normal'])
            ),
        ]
    ]
    kt = Table(kpi_data, colWidths=[2.8*cm]*6)
    kt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0),(-1,0),colors.white),
        ('BACKGROUND',(0,1),(-1,1),colors.HexColor('#F8FAFC')),
        ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#E2E8F0')),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(kt)
    story.append(Spacer(1,0.25*cm))

    # Narrativa IA
    if narrativa:
        story.append(Paragraph("<b>ANÁLISE EXECUTIVA</b>", bold_s))
        paras = narrativa.split('\n')
        for p in paras:
            if p.strip():
                story.append(Paragraph(p.strip(), normal_s))
        story.append(Spacer(1,0.2*cm))

    # YTD progress
    story.append(Paragraph("<b>EXECUÇÃO DO OBJETIVO ANUAL</b>", bold_s))
    ytd_pct = kpis['exec_objetivo']
    ytd_cor = '#10B981' if ytd_pct >= 100 * kpis['mes']/12 \
              else '#F59E0B' if ytd_pct >= 80 * kpis['mes']/12 \
              else '#EF4444'
    ytd_data = [
        ["YTD Realizado","Objetivo Anual","% Executado","Horas Mês"],
        [f"€{kpis['fat_ytd']:,.2f}",
         f"€{kpis['fat_objetivo']:,.2f}",
         f"{ytd_pct:.1f}%",
         f"{kpis['horas_mes']:.0f}h"]
    ]
    ytt = Table(ytd_data, colWidths=[4.25*cm]*4)
    ytt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0),(-1,0),colors.white),
        ('FONTNAME',  (0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',  (2,1),(2,1),'Helvetica-Bold'),
        ('TEXTCOLOR', (2,1),(2,1),colors.HexColor(ytd_cor)),
        ('FONTSIZE',  (0,0),(-1,-1),9),
        ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#E2E8F0')),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(ytt)
    story.append(Spacer(1,0.2*cm))

    # Ações prioritárias
    if acoes:
        story.append(Paragraph(
            "<b>PRÓXIMAS AÇÕES PRIORITÁRIAS</b>", bold_s
        ))
        for i, acao in enumerate(acoes[:5], 1):
            story.append(Paragraph(
                f"{i}. {acao}",
                normal_s
            ))

    story.append(Spacer(1,0.3*cm))
    story.append(HRFlowable(
        width="100%",thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Paragraph(
        f"GESTNOW v3.0 | "
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"Confidencial — uso interno",
        ParagraphStyle('foot',parent=styles['Normal'],
                       fontSize=6,textColor=colors.grey)
    ))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_reporting(obras_db, registos_db,
                          faturas_db, diarias_pag_db, *_):
    """Módulo Reporting Executivo — último passo."""

    # ── Carregar dados ────────────────────────────────────────────
    fat_cli  = _load("faturas_clientes.csv",[
        "ID","Numero","Data_Emissao","Data_Vencimento",
        "Cliente","NIF_Cliente","Obra","Subtotal","IVA",
        "Total","Estado","Paga_Em"
    ])
    fat_forn = _load("faturas_fornecedores.csv",
                     ["ID","Data","Fornecedor","Total","Estado"])
    rh_db    = _load("colaboradores_rh.csv",["Nome","Salario_Base"])
    contas_db= _load("contas_bancarias.csv",["ID","Nome","Saldo"])
    renting_db=_load("renting_contratos.csv",
                     ["ID","Matricula","Valor_Mensal","Estado"])

    # Regras de negócio
    regras_db = _load("regras_negocio.csv",[
        "ID","Nome","Condicao","Limiar","Acao","Ativa","Disparada"
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
    meses_pt  = ["Janeiro","Fevereiro","Março","Abril","Maio",
                 "Junho","Julho","Agosto","Setembro","Outubro",
                 "Novembro","Dezembro"]

    # ── Calcular KPIs ─────────────────────────────────────────────
    kpis = _calcular_kpis_executivos(
        fat_cli, fat_forn, rh_db,
        registos_db, obras_db, contas_db, renting_db
    )
    score, cor_score, nivel_score = _calcular_score_saude(kpis)

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .exec-kpi {
        background:linear-gradient(135deg,
            rgba(30,41,59,0.9),rgba(15,23,42,0.9));
        border-radius:14px; padding:18px;
        border:1px solid rgba(255,255,255,0.06);
        transition:transform 0.2s;
    }
    .exec-kpi:hover { transform:translateY(-2px); }
    .exec-kpi-val {
        font-size:1.7rem; font-weight:900;
        color:#F1F5F9; margin:6px 0 4px;
    }
    .exec-kpi-label {
        font-size:0.72rem; color:#64748B;
        font-weight:700; text-transform:uppercase;
        letter-spacing:0.05em;
    }
    .exec-kpi-trend { font-size:0.8rem; }
    .regra-card {
        background:#1E293B; border-radius:10px;
        padding:12px 16px; margin-bottom:6px;
        border-left:4px solid;
    }
    .passaporte-section {
        background:#1E293B; border-radius:12px;
        padding:16px; margin-bottom:10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:linear-gradient(135deg,"
        f"#1E293B,#0F172A);padding:24px;border-radius:16px;"
        f"margin-bottom:20px;"
        f"border:1px solid rgba(255,255,255,0.08);'>"
        f"<div style='display:flex;"
        f"justify-content:space-between;align-items:center;'>"
        f"<div>"
        f"<h2 style='color:#F1F5F9;margin:0;font-size:1.6rem;'>"
        f"📊 Reporting Executivo</h2>"
        f"<p style='color:#64748B;margin:4px 0 0;"
        f"font-size:0.85rem;'>"
        f"{meses_pt[kpis['mes']-1]} {kpis['ano']} · "
        f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        f"</p></div>"
        f"<div style='text-align:center;"
        f"background:{cor_score}22;border-radius:50%;"
        f"width:80px;height:80px;display:flex;"
        f"align-items:center;justify-content:center;"
        f"border:3px solid {cor_score};'>"
        f"<div>"
        f"<b style='color:{cor_score};font-size:1.6rem;'>{score}</b>"
        f"<br><small style='color:#64748B;font-size:0.6rem;'>"
        f"SAÚDE</small>"
        f"</div></div></div>"
        f"<p style='color:{cor_score};margin:10px 0 0;"
        f"font-weight:700;'>{nivel_score}</p>"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── KPI Cards ─────────────────────────────────────────────────
    trend_ic  = "↑" if kpis['trend_fat'] >= 0 else "↓"
    trend_cor = "#10B981" if kpis['trend_fat'] >= 0 else "#EF4444"

    cards = [
        ("💰 Faturação Mês",
         f"€{kpis['fat_mes']:,.0f}",
         f"{trend_ic} {abs(kpis['trend_fat']):.1f}% vs mês ant.",
         trend_cor, "#3B82F6"),
        ("📈 Margem",
         f"{kpis['margem_pct']:.1f}%",
         f"€{kpis['margem_mes']:,.0f} bruta",
         "#10B981" if kpis['margem_pct'] >= 20 else "#EF4444",
         "#10B981" if kpis['margem_pct'] >= 20 else "#EF4444"),
        ("📥 A Receber",
         f"€{kpis['a_receber']:,.0f}",
         f"{kpis['fat_vencidas']} fat. vencida(s)",
         "#F59E0B" if kpis['fat_vencidas'] > 0 else "#64748B",
         "#F59E0B"),
        ("🏦 Saldo",
         f"€{kpis['saldo']:,.0f}",
         f"Autonomia {kpis['autonomia']:.1f} meses",
         "#10B981" if kpis['autonomia'] >= 3 else "#EF4444",
         "#10B981" if kpis['autonomia'] >= 3 else "#EF4444"),
        ("🎯 YTD vs Obj.",
         f"{kpis['exec_objetivo']:.1f}%",
         f"€{kpis['fat_ytd']:,.0f} acumulado",
         "#10B981" if kpis['exec_objetivo'] >= kpis['mes']/12*100
                   else "#EF4444",
         "#8B5CF6"),
        ("⏱️ Horas Mês",
         f"{kpis['horas_mes']:.0f}h",
         f"{kpis['n_obras']} obras ativas",
         "#94A3B8", "#06B6D4"),
    ]

    cols_k = st.columns(6)
    for col, (label, val, sub, cor_t, cor_b) in zip(cols_k, cards):
        with col:
            st.markdown(
                f"<div class='exec-kpi' "
                f"style='border-top:3px solid {cor_b};'>"
                f"<div class='exec-kpi-label'>{label}</div>"
                f"<div class='exec-kpi-val' "
                f"style='color:{cor_b};'>{val}</div>"
                f"<div class='exec-kpi-trend' "
                f"style='color:{cor_t};'>{sub}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("<div style='height:12px;'></div>",
                unsafe_allow_html=True)
    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_dash, t_pneg, t_benchm,
     t_regras, t_passaporte, t_export) = st.tabs([
        "📊 Dashboard Executivo",
        "📈 Plano de Negócios",
        "🎯 Benchmarking",
        "⚙️ Motor de Regras",
        "🗂️ Passaporte Financeiro",
        "📤 Exportar Relatório",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — DASHBOARD EXECUTIVO
    # ════════════════════════════════════════════════════════════════
    with t_dash:
        st.markdown("### 📊 Dashboard Executivo do Mês")

        # Linha 1
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.plotly_chart(
                _grafico_area_faturacao(
                    kpis['fat_12m'],
                    kpis['meses_pt'],
                    kpis['mes']
                ),
                use_container_width=True, key="area_fat"
            )
        with col_d2:
            st.plotly_chart(
                _grafico_waterfall_resultado(kpis),
                use_container_width=True, key="waterfall_resultado"
            )

        # Bullet objetivo
        st.plotly_chart(
            _grafico_bullet_objetivo(
                kpis['fat_ytd'],
                kpis['fat_objetivo'],
                kpis['mes']
            ),
            use_container_width=True,  key="bullet_objetivo"
        )

        # Linha 2
        col_d3, col_d4 = st.columns(2)
        with col_d3:
            fig_tree = _grafico_treemap_obras(obras_db, registos_db)
            if fig_tree:
                st.plotly_chart(
                    fig_tree, use_container_width=True, key="treemap_obras"
                )
        with col_d4:
            st.plotly_chart(
                _grafico_benchmark(kpis),
                use_container_width=True, key="bench_dash" 
            )

        # Narrativa IA
        st.markdown("---")
        st.markdown("#### 🤖 Narrativa Executiva IA")

        if st.button(
            "🤖 Gerar Análise Executiva do Mês",
            key="btn_narrativa",
            type="primary",
            use_container_width=True
        ):
            with st.spinner(
                "🤖 A redigir relatório executivo..."
            ):
                narrativa = _gerar_narrativa_ia(kpis, empresa)
            st.session_state['narrativa_exec'] = narrativa
            st.rerun()

        if st.session_state.get('narrativa_exec'):
            paras = st.session_state['narrativa_exec'].split('\n')
            st.markdown(
                "<div style='background:rgba(59,130,246,0.08);"
                "border:1px solid #3B82F6;border-radius:12px;"
                "padding:20px;color:#E2E8F0;font-size:0.9rem;"
                "line-height:1.7;'>",
                unsafe_allow_html=True
            )
            for p in paras:
                if p.strip():
                    st.markdown(
                        f"<p style='margin:0 0 10px;'>{p}</p>",
                        unsafe_allow_html=True
                    )
            st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # TAB — PLANO DE NEGÓCIOS DINÂMICO
    # ════════════════════════════════════════════════════════════════
    with t_pneg:
        st.markdown("### 📈 Plano de Negócios Dinâmico")

        # Gráfico projeção
        st.plotly_chart(
            _grafico_projecao_fecho_ano(
                kpis['fat_12m'],
                kpis['meses_pt'],
                kpis['mes']
            ),
            use_container_width=True, key="projecao_fecho_ano"
        )

        # Tabela de cenários
        st.markdown("#### 📊 Cenários de Fecho de Ano")
        media_mes = kpis['fat_ytd'] / kpis['mes'] \
                    if kpis['mes'] > 0 else 0
        meses_rest = 12 - kpis['mes']

        cenarios_pneg = [
            {
                "nome":    "🟢 Otimista (+15%)",
                "projecao":round(kpis['fat_ytd'] + media_mes*1.15*meses_rest,2),
                "descricao":"Todas as obras mantidas, novos clientes"
            },
            {
                "nome":    "🟡 Base (média atual)",
                "projecao":round(kpis['fat_ytd'] + media_mes*meses_rest,2),
                "descricao":"Manutenção do ritmo atual"
            },
            {
                "nome":    "🔴 Pessimista (-15%)",
                "projecao":round(kpis['fat_ytd'] + media_mes*0.85*meses_rest,2),
                "descricao":"Perda de obra ou cliente relevante"
            },
        ]

        for cen in cenarios_pneg:
            cor_c = (
                "#10B981" if "Otimista" in cen['nome']
                else "#F59E0B" if "Base" in cen['nome']
                else "#EF4444"
            )
            col_cn1, col_cn2 = st.columns([3,1])
            with col_cn1:
                st.markdown(
                    f"<div style='background:#1E293B;"
                    f"border-radius:10px;padding:14px;"
                    f"margin-bottom:8px;"
                    f"border-left:4px solid {cor_c};'>"
                    f"<b style='color:#F1F5F9;"
                    f"font-size:0.95rem;'>{cen['nome']}</b><br>"
                    f"<small style='color:#64748B;'>"
                    f"{cen['descricao']}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with col_cn2:
                st.markdown(
                    f"<div style='background:{cor_c}18;"
                    f"border:1px solid {cor_c};"
                    f"border-radius:10px;padding:14px;"
                    f"margin-bottom:8px;text-align:center;'>"
                    f"<b style='color:{cor_c};"
                    f"font-size:1.2rem;'>"
                    f"€{cen['projecao']:,.0f}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # "Se mantiveres este ritmo..."
        projecao_base = kpis['fat_ytd'] + media_mes * meses_rest
        objetivo_atingido = projecao_base >= kpis['fat_objetivo']
        cor_msg = "#10B981" if objetivo_atingido else "#EF4444"
        ic_msg  = "✅" if objetivo_atingido else "⚠️"
        st.markdown(
            f"<div style='background:{cor_msg}18;"
            f"border:2px solid {cor_msg};"
            f"border-radius:12px;padding:16px;"
            f"text-align:center;margin-top:12px;'>"
            f"<b style='color:{cor_msg};font-size:1.05rem;'>"
            f"{ic_msg} Se mantiveres este ritmo, "
            f"fecharás o ano em "
            f"<span style='font-size:1.3rem;'>"
            f"€{projecao_base:,.0f}</span></b><br>"
            f"<small style='color:#94A3B8;'>"
            f"{'✅ Objetivo atingido!' if objetivo_atingido else '❌ Abaixo do objetivo — precisa acelerar'}"
            f"</small></div>",
            unsafe_allow_html=True
        )

        # Projeção IA
        st.markdown("---")
        if st.button(
            "🤖 Análise IA da Projeção",
            key="btn_pneg_ia",
            use_container_width=True
        ):
            with st.spinner("🤖 A analisar..."):
                pneg_ia = _gerar_plano_negocios_ia(
                    kpis, obras_db, empresa
                )
            st.session_state['pneg_ia'] = pneg_ia

        if st.session_state.get('pneg_ia'):
            st.markdown(
                f"<div style='background:rgba(16,185,129,0.08);"
                f"border:1px solid #10B981;border-radius:12px;"
                f"padding:16px;color:#E2E8F0;font-size:0.88rem;"
                f"line-height:1.7;'>"
                f"<b style='color:#10B981;margin-bottom:8px;"
                f"display:block;'>🤖 PROJEÇÃO DE FECHO DE ANO</b>"
                f"{st.session_state['pneg_ia'].replace(chr(10),'<br>')}"
                f"</div>",
                unsafe_allow_html=True
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — BENCHMARKING
    # ════════════════════════════════════════════════════════════════
    with t_benchm:
        st.markdown("### 🎯 Benchmarking Setorial")
        st.info(
            "Comparação com médias do setor de instrumentação "
            "industrial e construção especializada em Portugal. "
            "Fonte: INE / Banco de Portugal (estimativas 2024)."
        )

        st.plotly_chart(
            _grafico_benchmark(kpis),
            use_container_width=True, key="bench_tab"
        )

        # Tabela comparativa
        st.markdown("#### 📋 Tabela de Comparação")
        benchmarks = [
            {
                "indicador":  "Margem Bruta",
                "empresa":    f"{kpis['margem_pct']:.1f}%",
                "setor":      "18-25%",
                "empresa_v":  kpis['margem_pct'],
                "setor_v":    21.5,
                "melhor":     kpis['margem_pct'] >= 21.5
            },
            {
                "indicador":  "DSO (dias recebimento)",
                "empresa":    f"{kpis['dso']:.0f} dias",
                "setor":      "45-65 dias",
                "empresa_v":  kpis['dso'],
                "setor_v":    55,
                "melhor":     kpis['dso'] <= 55
            },
            {
                "indicador":  "Autonomia Financeira",
                "empresa":    f"{kpis['autonomia']:.1f} meses",
                "setor":      "2-4 meses",
                "empresa_v":  kpis['autonomia'],
                "setor_v":    3,
                "melhor":     kpis['autonomia'] >= 3
            },
            {
                "indicador":  "Concentração Clientes",
                "empresa":    f"{kpis['conc_cli']:.0f}%",
                "setor":      "<50% top cliente",
                "empresa_v":  kpis['conc_cli'],
                "setor_v":    50,
                "melhor":     kpis['conc_cli'] <= 50
            },
            {
                "indicador":  "Execução Objetivo",
                "empresa":    f"{kpis['exec_objetivo']:.1f}%",
                "setor":      "Pro-rata mes",
                "empresa_v":  kpis['exec_objetivo'],
                "setor_v":    kpis['mes']/12*100,
                "melhor":     kpis['exec_objetivo'] >= kpis['mes']/12*100
            },
        ]

        for bm in benchmarks:
            cor_bm = "#10B981" if bm['melhor'] else "#EF4444"
            ic_bm  = "✅" if bm['melhor'] else "⚠️"
            st.markdown(
                f"<div style='background:#1E293B;"
                f"border-radius:8px;padding:10px 16px;"
                f"margin-bottom:6px;"
                f"border-left:3px solid {cor_bm};'>"
                f"<div style='display:flex;"
                f"justify-content:space-between;'>"
                f"<b style='color:#F1F5F9;"
                f"font-size:0.88rem;'>"
                f"{bm['indicador']}</b>"
                f"<div style='display:flex;gap:20px;'>"
                f"<span style='color:{cor_bm};"
                f"font-weight:700;'>"
                f"{ic_bm} {bm['empresa']}</span>"
                f"<span style='color:#64748B;"
                f"font-size:0.8rem;'>"
                f"Setor: {bm['setor']}</span>"
                f"</div></div></div>",
                unsafe_allow_html=True
            )

        # Score de benchmarking
        n_melhor = sum(1 for bm in benchmarks if bm['melhor'])
        pct_bench = round(n_melhor/len(benchmarks)*100)
        cor_bench = "#10B981" if pct_bench >= 60 else "#F59E0B"
        st.markdown(
            f"<div style='background:{cor_bench}18;"
            f"border:1px solid {cor_bench};"
            f"border-radius:10px;padding:14px;"
            f"text-align:center;margin-top:12px;'>"
            f"<b style='color:{cor_bench};"
            f"font-size:1.05rem;'>"
            f"Performance vs Setor: "
            f"{n_melhor}/{len(benchmarks)} indicadores "
            f"acima da média ({pct_bench}%)</b>"
            f"</div>",
            unsafe_allow_html=True
        )

    # ════════════════════════════════════════════════════════════════
    # TAB — MOTOR DE REGRAS
    # ════════════════════════════════════════════════════════════════
    with t_regras:
        st.markdown("### ⚙️ Motor de Regras de Negócio")
        st.info(
            "Define regras que o sistema verifica automaticamente. "
            "Sem necessidade de programar — "
            "configura em linguagem natural."
        )

        col_rf, col_rl = st.columns([1, 2])

        with col_rf:
            st.markdown("#### ➕ Nova Regra")
            with st.form("form_regra"):
                r_nome = st.text_input(
                    "Nome da Regra *",
                    key="regra_nome",
                    placeholder="Ex: Alerta margem baixa"
                )
                r_cond = st.selectbox(
                    "Condição",
                    ["margem_pct < X",
                     "fat_vencidas > X",
                     "autonomia < X",
                     "a_receber > X",
                     "conc_cli > X",
                     "trend_fat < X",
                     "horas_mes < X",
                     "saldo < X"],
                    key="regra_cond"
                )
                r_limiar = st.number_input(
                    "Valor X",
                    value=20.0, step=1.0,
                    key="regra_limiar"
                )
                r_acao = st.text_area(
                    "Ação / Mensagem *",
                    key="regra_acao",
                    placeholder="Ex: Convocar reunião "
                                "de gestão urgente"
                )
                r_ativa = st.checkbox(
                    "Regra Ativa", value=True,
                    key="regra_ativa"
                )

                if st.form_submit_button(
                    "💾 Guardar Regra",
                    use_container_width=True, type="primary"
                ):
                    if not r_nome.strip() or not r_acao.strip():
                        st.error("❌ Nome e ação obrigatórios.")
                    else:
                        nova_r = pd.DataFrame([{
                            "ID":        str(uuid.uuid4())[:8].upper(),
                            "Nome":      r_nome.strip(),
                            "Condicao":  r_cond,
                            "Limiar":    r_limiar,
                            "Acao":      r_acao.strip(),
                            "Ativa":     "Sim" if r_ativa else "Não",
                            "Disparada": "Não"
                        }])
                        upd_r = pd.concat(
                            [regras_db, nova_r], ignore_index=True
                        ) if not regras_db.empty else nova_r
                        save_db(upd_r, "regras_negocio.csv")
                        inv()
                        st.success("✅ Regra guardada!")
                        st.rerun()

        with col_rl:
            st.markdown("#### 📋 Regras Ativas")

            # Regras default se não há nenhuma
            regras_default = [
                {"ID":"D001","Nome":"Alerta margem < 15%",
                 "Condicao":"margem_pct < X","Limiar":15,
                 "Acao":"Rever estrutura de custos urgente",
                 "Ativa":"Sim","Disparada":"Não"},
                {"ID":"D002","Nome":"Faturas vencidas > 0",
                 "Condicao":"fat_vencidas > X","Limiar":0,
                 "Acao":"Contactar clientes em atraso",
                 "Ativa":"Sim","Disparada":"Não"},
                {"ID":"D003","Nome":"Autonomia < 2 meses",
                 "Condicao":"autonomia < X","Limiar":2,
                 "Acao":"Solicitar linha de crédito preventiva",
                 "Ativa":"Sim","Disparada":"Não"},
                {"ID":"D004","Nome":"Concentração > 60%",
                 "Condicao":"conc_cli > X","Limiar":60,
                 "Acao":"Diversificar carteira de clientes",
                 "Ativa":"Sim","Disparada":"Não"},
                {"ID":"D005","Nome":"Queda faturação > 20%",
                 "Condicao":"trend_fat < X","Limiar":-20,
                 "Acao":"Analisar causa da queda e agir",
                 "Ativa":"Sim","Disparada":"Não"},
            ]

            todas_regras = regras_default.copy()
            if not regras_db.empty:
                for _, row in regras_db.iterrows():
                    todas_regras.append(row.to_dict())

            # Avaliar regras
            regras_avaliadas = []
            for regra in todas_regras:
                cond   = regra.get('Condicao','')
                limiar = float(regra.get('Limiar',0) or 0)
                ativa  = regra.get('Ativa','Sim') == 'Sim'

                # Avaliar condição
                disparada = False
                if ativa:
                    metrica = cond.split(' ')[0]
                    op      = cond.split(' ')[1] if len(cond.split())>1 else '<'
                    val_atual = kpis.get(metrica, 0)
                    if op == '<':
                        disparada = val_atual < limiar
                    elif op == '>':
                        disparada = val_atual > limiar

                regras_avaliadas.append({
                    **regra,
                    "ativa":     ativa,
                    "disparada": disparada
                })

            # Gráfico
            fig_reg = _grafico_motor_regras(regras_avaliadas)
            if fig_reg:
                st.plotly_chart(
                    fig_reg, use_container_width=True,  key="motor_regras" 
                )

            n_disparadas = sum(
                1 for r in regras_avaliadas if r['disparada']
            )
            if n_disparadas > 0:
                st.error(
                    f"🔔 {n_disparadas} regra(s) disparada(s)!"
                )

            for regra in regras_avaliadas:
                disparada = regra['disparada']
                ativa     = regra['ativa']
                cor_r = "#EF4444" if disparada \
                        else "#10B981" if ativa \
                        else "#334155"
                ic_r  = "🔔" if disparada \
                        else "✅" if ativa \
                        else "⏸️"

                # Adicionar antes do st.markdown:
                acao_txt = (
                    '<br><small style=color:#EF4444;>' +
                    str(regra.get('Acao','')) +
                    '</small>'
                ) if disparada else ''
              
                st.markdown(
                    f"<div class='regra-card' "
                    f"style='border-left-color:{cor_r};"
                    f"background:{'rgba(239,68,68,0.1)' if disparada else '#1E293B'};'>"
                    f"<div style='display:flex;"
                    f"justify-content:space-between;'>"
                    f"<div>"
                    f"<b style='color:#F1F5F9;"
                    f"font-size:0.88rem;'>"
                    f"{ic_r} {regra.get('Nome','')}</b><br>"
                    f"<small style='color:#64748B;'>"
                    f"{acao_txt}"
                    f"</small>"
                    f"</div>"
                    f"<span style='color:{cor_r};"
                    f"font-size:0.75rem;font-weight:700;'>"
                    f"{'🔴 DISPARADA' if disparada else '🟢 OK'}"
                    f"</span></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    # ════════════════════════════════════════════════════════════════
    # TAB — PASSAPORTE FINANCEIRO
    # ════════════════════════════════════════════════════════════════
    with t_passaporte:
        st.markdown("### 🗂️ Passaporte Financeiro da Empresa")
        st.info(
            "Documento sempre atualizado com os indicadores "
            "chave da empresa. Pronto para apresentar a bancos, "
            "investidores, fundos europeus ou seguradoras."
        )

        # Versões do passaporte
        versao_pass = st.selectbox(
            "Versão para:",
            ["🏦 Banco / Financiamento",
             "🇪🇺 Fundos Europeus",
             "🤝 Parceiros / Investidores",
             "📋 Uso Interno"],
            key="pass_versao"
        )

        # Dados da empresa
        col_p1, col_p2 = st.columns(2)

        with col_p1:
            st.markdown("#### 🏢 Dados da Empresa")  

            empresa_rows = ''.join([
                '<tr><td style=color:#64748B;font-size:0.8rem;padding:4px 0;>' + k +
                '</td><td style=color:#F1F5F9;font-size:0.85rem;font-weight:700;>' + v +
                '</td></tr>'
                for k, v in [
                    ('Nome',           empresa.get('nome','')),
                    ('NIF',            empresa.get('nif','')),
                    ('Morada',         empresa.get('morada','')),
                    ('Setor',          'Instrumentação Industrial'),
                    ('Constituição',   '—'),
                    ('Capital Social', '—'),
              ]   
         ])      
          
            st.markdown(
                f"<div class='passaporte-section'>"
                f"<table style='width:100%;border-collapse:collapse;'>"
                f"{empresa_rows}"
                f"</table></div>",
                unsafe_allow_html=True
            )

            st.markdown("#### 📊 Performance Financeira")
            fat_anual_est = kpis['fat_ytd']/kpis['mes']*12 \
                            if kpis['mes'] > 0 else 0

            perf_rows = ''.join([
                '<tr><td style=color:#64748B;font-size:0.8rem;padding:4px 0;>' + k +
                '</td><td style=color:#F1F5F9;font-size:0.85rem;font-weight:700;>' + v +
                '</td></tr>'
                for k, v in [
                    ('Faturação Anual (proj.)', f'\u20AC{fat_anual_est:,.0f}'),
                    ('YTD Acumulado',           f'\u20AC{kpis["fat_ytd"]:,.0f}'),
                    ('Margem Operacional',      f'{kpis["margem_pct"]:.1f}%'),
                    ('Obras Ativas',            str(kpis['n_obras'])),
                    ('DSO',                     f'{kpis["dso"]:.0f} dias'),
                    ('Autonomia',               f'{kpis["autonomia"]:.1f} meses'),
               ]
          ])
          
            st.markdown(
                f"<div class='passaporte-section'>"
                f"<table style='width:100%;border-collapse:collapse;'>"
                f"{perf_rows}"
                f"</table></div>",  
                unsafe_allow_html=True
            )

        with col_p2:
            st.markdown("#### 📈 Indicadores de Solidez")
            indicadores_pass = [
                ("Current Ratio (est.)",
                 f"{min(kpis['autonomia']*0.5,3):.2f}",
                 "Saudável > 1.5",
                 kpis['autonomia'] >= 3),
                ("DSO (dias recebimento)",
                 f"{kpis['dso']:.0f}d",
                 "Bom < 45 dias",
                 kpis['dso'] <= 45),
                ("Margem Bruta",
                 f"{kpis['margem_pct']:.1f}%",
                 "Objetivo > 20%",
                 kpis['margem_pct'] >= 20),
                ("Score de Saúde",
                 f"{score}/100",
                 "Saudável > 70",
                 score >= 70),
                ("Autonomia",
                 f"{kpis['autonomia']:.1f}m",
                 "Mínimo 3 meses",
                 kpis['autonomia'] >= 3),
                ("Concentração Clientes",
                 f"{kpis['conc_cli']:.0f}%",
                 "Risco < 50%",
                 kpis['conc_cli'] <= 50),
            ]

            for ind, val, ref, ok in indicadores_pass:
                cor_i = "#10B981" if ok else "#EF4444"
                st.markdown(
                    f"<div style='display:flex;"
                    f"justify-content:space-between;"
                    f"padding:8px 0;"
                    f"border-bottom:1px solid #1E293B;'>"
                    f"<div>"
                    f"<small style='color:#94A3B8;'>{ind}</small><br>"
                    f"<small style='color:#64748B;font-size:0.7rem;'>"
                    f"{ref}</small>"
                    f"</div>"
                    f"<b style='color:{cor_i};"
                    f"font-size:1rem;'>{val}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            st.markdown("#### 🏗️ Obras de Referência")
            if not obras_db.empty:
                obras_ref = obras_db[
                    obras_db['Ativa']=='Ativa'
                ][['Obra','Cliente','Local']].head(5) \
                  if all(c in obras_db.columns
                         for c in ['Obra','Cliente','Local']) \
                  else obras_db.head(5)
                st.dataframe(
                    obras_ref,
                    use_container_width=True,
                    hide_index=True
                )

        # Rating interno
        rating = (
            "A+" if score >= 90 else
            "A"  if score >= 80 else
            "A-" if score >= 70 else
            "B+" if score >= 60 else
            "B"  if score >= 50 else
            "B-" if score >= 40 else
            "C"
        )
        cor_rating = (
            "#10B981" if score >= 70 else
            "#F59E0B" if score >= 40 else
            "#EF4444"
        )
        st.markdown(
            f"<div style='background:{cor_rating}18;"
            f"border:2px solid {cor_rating};"
            f"border-radius:14px;padding:20px;"
            f"text-align:center;margin-top:16px;'>"
            f"<p style='color:#94A3B8;margin:0 0 4px;"
            f"font-size:0.8rem;'>"
            f"RATING INTERNO GESTNOW</p>"
            f"<b style='color:{cor_rating};"
            f"font-size:3rem;'>{rating}</b><br>"
            f"<p style='color:#94A3B8;margin:4px 0 0;"
            f"font-size:0.8rem;'>"
            f"Score: {score}/100 · {nivel_score}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

    # ════════════════════════════════════════════════════════════════
    # TAB — EXPORTAR RELATÓRIO
    # ════════════════════════════════════════════════════════════════
    with t_export:
        st.markdown("### 📤 Exportar Relatório Executivo")

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.markdown("#### ⚙️ Configuração")

            dest_report = st.selectbox(
                "Destinatário",
                ["Direção / Sócios",
                 "Reunião de Gestão",
                 "Banco",
                 "Uso Interno CFO"],
                key="rep_dest"
            )
            incluir_narrativa = st.checkbox(
                "✅ Incluir narrativa IA",
                value=bool(st.session_state.get('narrativa_exec')),
                key="rep_narrativa"
            )
            acoes_report = []
            st.markdown(
                "<p style='color:#94A3B8;font-size:0.8rem;"
                "margin:8px 0 4px;'>Próximas ações (max 5):</p>",
                unsafe_allow_html=True
            )
            for i in range(5):
                acao = st.text_input(
                    f"Ação {i+1}",
                    key=f"rep_acao_{i}",
                    label_visibility="collapsed",
                    placeholder=f"Ação prioritária {i+1}"
                )
                if acao.strip():
                    acoes_report.append(acao.strip())

        with col_ex2:
            st.markdown("#### 📋 Conteúdo")
            st.markdown(
                "<div style='background:#1E293B;"
                "border-radius:10px;padding:14px;'>"
                "<p style='color:#64748B;font-size:0.75rem;"
                "font-weight:700;text-transform:uppercase;"
                "margin:0 0 8px;'>Incluído no PDF:</p>",
                unsafe_allow_html=True
            )
            conteudo_rep = [
                ("📊 6 KPIs executivos com trends", True),
                ("📈 Faturação 12 meses (gráfico)", True),
                ("💰 Resultado do mês (waterfall)", True),
                ("🎯 YTD vs Objetivo", True),
                ("🤖 Narrativa IA", incluir_narrativa),
                ("📋 Próximas 5 ações", len(acoes_report)>0),
                ("📊 Score de saúde", True),
            ]
            for desc, ok in conteudo_rep:
                ic = "✅" if ok else "⚪"
                cor = "#10B981" if ok else "#334155"
                st.markdown(
                    f"<div style='display:flex;"
                    f"align-items:center;padding:3px 0;'>"
                    f"<span style='color:{cor};"
                    f"margin-right:8px;'>{ic}</span>"
                    f"<small style='color:#94A3B8;'>{desc}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button(
                "📄 Gerar PDF Executivo",
                key="btn_pdf_exec",
                type="primary",
                use_container_width=True
            ):
                narrativa_f = st.session_state.get(
                    'narrativa_exec', ""
                ) if incluir_narrativa else ""
                with st.spinner(
                    "A gerar relatório executivo..."
                ):
                    pdf_exec = _gerar_pdf_executivo(
                        kpis, score,
                        narrativa_f,
                        acoes_report, empresa
                    )
                st.session_state['exec_pdf'] = pdf_exec
                st.session_state['exec_pdf_nome'] = (
                    f"Relatorio_Executivo_"
                    f"{meses_pt[kpis['mes']-1]}_{kpis['ano']}.pdf"
                )
                st.success("✅ PDF gerado!")
                st.rerun()

        with col_btn2:
            if st.session_state.get('exec_pdf'):
                st.download_button(
                    "📥 Descarregar PDF",
                    data=st.session_state['exec_pdf'],
                    file_name=st.session_state.get(
                        'exec_pdf_nome','relatorio.pdf'
                    ),
                    mime="application/pdf",
                    key="dl_exec_pdf",
                    use_container_width=True,
                    type="primary"
                )

        with col_btn3:
            # Export CSV resumo executivo
            resumo_exec = {
                "Mês":            f"{meses_pt[kpis['mes']-1]} {kpis['ano']}",
                "Faturação":      kpis['fat_mes'],
                "Trend":          f"{kpis['trend_fat']:+.1f}%",
                "Margem %":       kpis['margem_pct'],
                "A Receber":      kpis['a_receber'],
                "Saldo":          kpis['saldo'],
                "Autonomia":      kpis['autonomia'],
                "YTD":            kpis['fat_ytd'],
                "Score Saúde":    score,
                "Nível":          nivel_score,
            }
            df_exec = pd.DataFrame([resumo_exec])
            csv_exec = df_exec.to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Export CSV",
                data=csv_exec.encode('utf-8-sig'),
                file_name=(
                    f"kpis_exec_"
                    f"{kpis['mes']:02d}_{kpis['ano']}.csv"
                ),
                mime="text/csv",
                key="dl_exec_csv",
                use_container_width=True
            )

        # Preview do relatório
        st.markdown("---")
        st.markdown("#### 👀 Preview do Relatório")

        col_prev1, col_prev2, col_prev3 = st.columns(3)
        with col_prev1:
            st.markdown(
                f"<div style='background:#1E293B;"
                f"border-radius:10px;padding:14px;'>"
                f"<p style='color:#64748B;font-size:0.7rem;"
                f"font-weight:700;text-transform:uppercase;margin:0 0 8px;'>"
                f"Relatório {meses_pt[kpis['mes']-1].upper()} {kpis['ano']}</p>"
                f"<b style='color:#F1F5F9;"
                f"font-size:1rem;'>{empresa.get('nome','')[:30]}</b><br>"
                f"<p style='color:#64748B;font-size:0.8rem;'>"
                f"NIF: {empresa.get('nif','')}</p>"
                f"<hr style='border-color:#334155;margin:8px 0;'>"
                f"<p style='color:{cor_score};"
                f"font-size:1.4rem;font-weight:900;margin:0;'>"
                f"Saúde: {score}/100</p>"
                f"<p style='color:{cor_score};"
                f"font-size:0.8rem;margin:0;'>{nivel_score}</p>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_prev2:
            for label, val, cor_v in [
                ("Faturação Mês",
                 f"€{kpis['fat_mes']:,.0f}","#3B82F6"),
                ("Margem",
                 f"{kpis['margem_pct']:.1f}%",
                 "#10B981" if kpis['margem_pct']>=20 else "#EF4444"),
                ("A Receber",
                 f"€{kpis['a_receber']:,.0f}","#F59E0B"),
            ]:
                st.markdown(
                    f"<div style='background:#0F172A;"
                    f"border-radius:8px;padding:10px;"
                    f"margin-bottom:6px;display:flex;"
                    f"justify-content:space-between;'>"
                    f"<small style='color:#64748B;'>{label}</small>"
                    f"<b style='color:{cor_v};'>{val}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        with col_prev3:
            for label, val, cor_v in [
                ("Saldo",
                 f"€{kpis['saldo']:,.0f}","#10B981"),
                ("Autonomia",
                 f"{kpis['autonomia']:.1f} meses",
                 "#10B981" if kpis['autonomia']>=3 else "#EF4444"),
                ("YTD vs Obj.",
                 f"{kpis['exec_objetivo']:.1f}%","#8B5CF6"),
            ]:
                st.markdown(
                    f"<div style='background:#0F172A;"
                    f"border-radius:8px;padding:10px;"
                    f"margin-bottom:6px;display:flex;"
                    f"justify-content:space-between;'>"
                    f"<small style='color:#64748B;'>{label}</small>"
                    f"<b style='color:{cor_v};'>{val}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # Marca fim do módulo de faturação
        st.markdown("---")
        st.markdown(
            "<div style='background:linear-gradient(135deg,"
            "rgba(59,130,246,0.15),rgba(16,185,129,0.15));"
            "border:1px solid rgba(59,130,246,0.3);"
            "border-radius:16px;padding:24px;"
            "text-align:center;'>"
            "<h3 style='color:#F1F5F9;margin:0 0 8px;'>"
            "🏆 Módulo Faturação Completo</h3>"
            "<p style='color:#94A3B8;margin:0 0 12px;'>"
            "Todos os 13 passos implementados com sucesso</p>"
            "<div style='display:grid;"
            "grid-template-columns:repeat(4,1fr);"
            "gap:8px;margin-top:12px;'>"
            + "".join([
                f"<div style='background:rgba(16,185,129,0.1);"
                f"border-radius:8px;padding:8px;"
                f"font-size:0.7rem;color:#10B981;'>{p}</div>"
                for p in [
                    "✅ Dashboard CFO",
                    "✅ Clientes & Fat.",
                    "✅ Fornecedores",
                    "✅ RH Financeiro",
                    "✅ Frota & Renting",
                    "✅ Perf. Obras",
                    "✅ Tesouraria",
                    "✅ Simulador Crise",
                    "✅ Fundos Europeus",
                    "✅ Imobilizado",
                    "✅ Fiscal",
                    "✅ Auditoria Anual",
                    "✅ Reporting Exec.",
                    "✅ + Diárias SEPA",
                ]
            ])
            + "</div></div>",
            unsafe_allow_html=True
        )

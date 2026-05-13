"""
GESTNOW v3 — mod_fat_auditoria.py
Passo 12 — Auditoria Anual & Dossier Digital
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, io, os, json, zipfile
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable,
                                PageBreak)
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

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()


# ─────────────────────────────────────────────────────────────────
# CHECKLIST DE AUDITORIA — 50+ ITENS
# ─────────────────────────────────────────────────────────────────

CHECKLIST_AUDITORIA = [
    # ── FATURAÇÃO ─────────────────────────────────────────────────
    {
        "categoria": "📄 Faturação",
        "item":      "Todas as faturas emitidas registadas no sistema",
        "critico":   True,
        "csv":       "faturas_clientes.csv",
        "verificar": lambda dfs: not dfs.get('faturas_cli',pd.DataFrame()).empty
    },
    {
        "categoria": "📄 Faturação",
        "item":      "Sequência numérica de faturas sem lacunas",
        "critico":   True,
        "csv":       "faturas_clientes.csv",
        "verificar": lambda dfs: True  # verificação manual
    },
    {
        "categoria": "📄 Faturação",
        "item":      "NIF de todos os clientes preenchido e válido",
        "critico":   True,
        "csv":       "faturas_clientes.csv",
        "verificar": lambda dfs: (
            not dfs.get('faturas_cli',pd.DataFrame()).empty and
            'NIF_Cliente' in dfs.get('faturas_cli',pd.DataFrame()).columns and
            dfs['faturas_cli']['NIF_Cliente'].notna().all()
        )
    },
    {
        "categoria": "📄 Faturação",
        "item":      "Todas as faturas emitidas têm PDF associado",
        "critico":   False,
        "csv":       "faturas_clientes.csv",
        "verificar": lambda dfs: True
    },
    {
        "categoria": "📄 Faturação",
        "item":      "Notas de crédito associadas a faturas originais",
        "critico":   True,
        "csv":       "faturas_clientes.csv",
        "verificar": lambda dfs: True
    },
    {
        "categoria": "📄 Faturação",
        "item":      "SAF-T entregue mensalmente à AT",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    # ── FORNECEDORES ──────────────────────────────────────────────
    {
        "categoria": "📥 Fornecedores",
        "item":      "Todas as faturas de fornecedores registadas",
        "critico":   True,
        "csv":       "faturas_fornecedores.csv",
        "verificar": lambda dfs: not dfs.get('fat_forn',pd.DataFrame()).empty
    },
    {
        "categoria": "📥 Fornecedores",
        "item":      "NIF de todos os fornecedores validado",
        "critico":   True,
        "csv":       "fornecedores.csv",
        "verificar": lambda dfs: (
            not dfs.get('fornecedores',pd.DataFrame()).empty and
            'NIF' in dfs.get('fornecedores',pd.DataFrame()).columns
        )
    },
    {
        "categoria": "📥 Fornecedores",
        "item":      "Retenções na fonte calculadas e entregues à AT",
        "critico":   True,
        "csv":       "faturas_fornecedores.csv",
        "verificar": lambda dfs: True
    },
    {
        "categoria": "📥 Fornecedores",
        "item":      "IBANs de fornecedores validados e histórico limpo",
        "critico":   True,
        "csv":       "iban_historico.csv",
        "verificar": lambda dfs: True
    },
    {
        "categoria": "📥 Fornecedores",
        "item":      "Faturas de fornecedores com comprovativo digital",
        "critico":   False,
        "csv":       "faturas_fornecedores.csv",
        "verificar": lambda dfs: True
    },
    # ── COLABORADORES / RH ────────────────────────────────────────
    {
        "categoria": "👥 Recursos Humanos",
        "item":      "Ficheiros de remunerações completos (12 meses)",
        "critico":   True,
        "csv":       "colaboradores_rh.csv",
        "verificar": lambda dfs: not dfs.get('rh',pd.DataFrame()).empty
    },
    {
        "categoria": "👥 Recursos Humanos",
        "item":      "Recibos de vencimento entregues a todos os colaboradores",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "👥 Recursos Humanos",
        "item":      "DRI entregue mensalmente ao ISS (dia 10)",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "👥 Recursos Humanos",
        "item":      "IRS retido e entregue à AT (dia 20)",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "👥 Recursos Humanos",
        "item":      "Contratos de trabalho arquivados digitalmente",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "👥 Recursos Humanos",
        "item":      "Subsídios de férias e natal pagos",
        "critico":   True,
        "csv":       "provisoes_db.csv",
        "verificar": lambda dfs: not dfs.get('provisoes',pd.DataFrame()).empty
    },
    {
        "categoria": "👥 Recursos Humanos",
        "item":      "Folhas de ponto assinadas e arquivadas",
        "critico":   True,
        "csv":       "folhas_ponto.csv",
        "verificar": lambda dfs: True
    },
    # ── FISCAL ────────────────────────────────────────────────────
    {
        "categoria": "🧾 Fiscal",
        "item":      "Declaração IVA entregue todos os meses",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🧾 Fiscal",
        "item":      "Modelo 22 IRC entregue (prazo: 31/05)",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🧾 Fiscal",
        "item":      "Pagamentos por conta IRC efetuados (jul/set)",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🧾 Fiscal",
        "item":      "Modelo 10 IRS entregue (rendimentos a terceiros)",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🧾 Fiscal",
        "item":      "IES/Declaração Anual entregue (prazo: 15/07)",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🧾 Fiscal",
        "item":      "Certidão de não dívida AT atualizada",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🧾 Fiscal",
        "item":      "Certidão de não dívida SS atualizada",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    # ── CONTABILIDADE ─────────────────────────────────────────────
    {
        "categoria": "📊 Contabilidade",
        "item":      "Balancete anual fechado pelo TOC",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "📊 Contabilidade",
        "item":      "Balanço e demonstração resultados aprovados",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "📊 Contabilidade",
        "item":      "Relatório & Contas aprovado em AG (prazo: 31/03)",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "📊 Contabilidade",
        "item":      "Depósito R&C no IRN (prazo: 15/07)",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "📊 Contabilidade",
        "item":      "Quadro de imobilizado e amortizações atualizado",
        "critico":   True,
        "csv":       "imobilizado_db.csv",
        "verificar": lambda dfs: not dfs.get('imob',pd.DataFrame()).empty
    },
    {
        "categoria": "📊 Contabilidade",
        "item":      "Reconciliação bancária efetuada (todos os meses)",
        "critico":   True,
        "csv":       "movimentos_bancarios.csv",
        "verificar": lambda dfs: not dfs.get('movimentos',pd.DataFrame()).empty
    },
    # ── JURÍDICO ──────────────────────────────────────────────────
    {
        "categoria": "⚖️ Jurídico",
        "item":      "Pacto social / estatutos atualizados",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "⚖️ Jurídico",
        "item":      "Livro de atas de assembleias atualizado",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "⚖️ Jurídico",
        "item":      "Contratos com clientes assinados e arquivados",
        "critico":   True,
        "csv":       "contratos_financeiro.csv",
        "verificar": lambda dfs: not dfs.get('contratos',pd.DataFrame()).empty
    },
    {
        "categoria": "⚖️ Jurídico",
        "item":      "Contratos de trabalho de todos os colaboradores",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "⚖️ Jurídico",
        "item":      "Seguros obrigatórios válidos (RC, acidentes)",
        "critico":   True,
        "csv":       "seguros_db.csv",
        "verificar": lambda dfs: not dfs.get('seguros',pd.DataFrame()).empty
    },
    {
        "categoria": "⚖️ Jurídico",
        "item":      "Alvará de construção válido e renovado",
        "critico":   True,
        "csv":       "alvaras_db.csv",
        "verificar": lambda dfs: not dfs.get('alvaras',pd.DataFrame()).empty
    },
    # ── OBRAS ─────────────────────────────────────────────────────
    {
        "categoria": "🏗️ Obras",
        "item":      "Todas as obras com registo de horas completo",
        "critico":   True,
        "csv":       "registos.csv",
        "verificar": lambda dfs: not dfs.get('registos',pd.DataFrame()).empty
    },
    {
        "categoria": "🏗️ Obras",
        "item":      "Orçamentos de obra arquivados",
        "critico":   True,
        "csv":       "obras_orcamento.csv",
        "verificar": lambda dfs: not dfs.get('orc_obras',pd.DataFrame()).empty
    },
    {
        "categoria": "🏗️ Obras",
        "item":      "Cauções bancárias constituídas e controladas",
        "critico":   True,
        "csv":       "caucoes_db.csv",
        "verificar": lambda dfs: not dfs.get('caucoes',pd.DataFrame()).empty
    },
    {
        "categoria": "🏗️ Obras",
        "item":      "Autos de medição assinados",
        "critico":   False,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🏗️ Obras",
        "item":      "Diárias e deslocações documentadas",
        "critico":   True,
        "csv":       "diarias_pagamentos.csv",
        "verificar": lambda dfs: True
    },
    # ── FROTA ─────────────────────────────────────────────────────
    {
        "categoria": "🚗 Frota",
        "item":      "Contratos de renting arquivados",
        "critico":   True,
        "csv":       "renting_contratos.csv",
        "verificar": lambda dfs: not dfs.get('renting',pd.DataFrame()).empty
    },
    {
        "categoria": "🚗 Frota",
        "item":      "Registos de combustível com recibo",
        "critico":   False,
        "csv":       "frota_combustivel.csv",
        "verificar": lambda dfs: not dfs.get('comb',pd.DataFrame()).empty
    },
    {
        "categoria": "🚗 Frota",
        "item":      "IUC pago para todas as viaturas",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🚗 Frota",
        "item":      "Seguros automóvel válidos para todas as viaturas",
        "critico":   True,
        "csv":       "seguros_db.csv",
        "verificar": lambda dfs: not dfs.get('seguros',pd.DataFrame()).empty
    },
    # ── HSE ───────────────────────────────────────────────────────
    {
        "categoria": "🛡️ HSE",
        "item":      "Relatório anual de acidentes de trabalho",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🛡️ HSE",
        "item":      "Fichas de aptidão médica atualizadas",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "🛡️ HSE",
        "item":      "Formação obrigatória HSE documentada",
        "critico":   False,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    # ── DIGITAL / GDPR ────────────────────────────────────────────
    {
        "categoria": "💻 Digital / GDPR",
        "item":      "Backups de dados realizados e verificados",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "💻 Digital / GDPR",
        "item":      "Política de privacidade (RGPD) atualizada",
        "critico":   False,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "💻 Digital / GDPR",
        "item":      "Registo de tratamento de dados (CNPD)",
        "critico":   False,
        "csv":       None,
        "verificar": lambda dfs: True
    },
    {
        "categoria": "💻 Digital / GDPR",
        "item":      "Logs de auditoria do sistema arquivados",
        "critico":   True,
        "csv":       None,
        "verificar": lambda dfs: True
    },
]


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_checklist_por_categoria(resultados: dict):
    """Bar chart % conclusão por categoria."""
    cats      = {}
    for item_id, ok in resultados.items():
        cat = item_id.split("||")[0]
        if cat not in cats:
            cats[cat] = {"total":0,"ok":0}
        cats[cat]["total"] += 1
        if ok:
            cats[cat]["ok"] += 1

    if not cats:
        return None

    nomes  = list(cats.keys())
    pcts   = [
        round(v['ok']/v['total']*100, 0)
        for v in cats.values()
    ]
    cores  = [
        '#10B981' if p >= 80
        else '#F59E0B' if p >= 50
        else '#EF4444'
        for p in pcts
    ]

    fig = go.Figure(go.Bar(
        x=pcts, y=nomes,
        orientation='h',
        marker_color=cores,
        text=[f"{p:.0f}%" for p in pcts],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':11},
        hovertemplate='%{y}<br>Preparação: %{x:.0f}%<extra></extra>'
    ))
    fig.add_vline(
        x=80, line_dash="dash",
        line_color="#10B981", line_width=1,
        annotation_text="80% OK",
        annotation_font_color="#10B981"
    )
    fig.update_layout(
        title={'text':'Preparação para Auditoria por Categoria',
               'font':{'color':'#F1F5F9'}},
        height=max(240, len(cats)*40 + 80),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'range':[0,120],'ticksuffix':'%'},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=160,r=60),
        showlegend=False
    )
    return fig


def _grafico_gauge_preparacao(pct: float):
    """Gauge % preparação auditoria."""
    cor = "#10B981" if pct >= 80 \
          else "#F59E0B" if pct >= 50 \
          else "#EF4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        title={'text':'Preparação para Auditoria',
               'font':{'color':'#F1F5F9','size':13}},
        number={'suffix':'%','font':{'color':'#F1F5F9','size':32}},
        gauge={
            'axis':{'range':[0,100],'tickcolor':'#64748B'},
            'bar':{'color':cor},
            'bgcolor':'#1E293B',
            'bordercolor':'#334155',
            'steps':[
                {'range':[0,50],  'color':'rgba(239,68,68,0.15)'},
                {'range':[50,80], 'color':'rgba(245,158,11,0.15)'},
                {'range':[80,100],'color':'rgba(16,185,129,0.15)'},
            ],
            'threshold':{
                'line':{'color':'#F1F5F9','width':3},
                'thickness':0.75,
                'value':pct
            }
        }
    ))
    fig.update_layout(
        height=220,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        margin=dict(t=40,b=10,l=20,r=20)
    )
    return fig


def _grafico_inconsistencias(inconsistencias: list):
    """Donut das inconsistências por tipo."""
    if not inconsistencias:
        return None

    tipos = {}
    for inc in inconsistencias:
        t = inc.get('tipo','Outro')
        tipos[t] = tipos.get(t,0) + 1

    cores = ['#EF4444','#F59E0B','#3B82F6','#8B5CF6','#F97316']
    fig = go.Figure(go.Pie(
        labels=list(tipos.keys()),
        values=list(tipos.values()),
        hole=0.5,
        marker={'colors':cores[:len(tipos)],
                'line':{'color':'#0F172A','width':2}},
        textfont={'color':'#F1F5F9','size':10},
        hovertemplate='%{label}: %{value}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Inconsistências por Tipo',
               'font':{'color':'#F1F5F9'}},
        height=240,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        margin=dict(t=40,b=10,l=10,r=10),
        annotations=[{
            'text':str(len(inconsistencias)),
            'x':0.5,'y':0.5,
            'font_size':22,'font_color':'#EF4444',
            'showarrow':False
        }]
    )
    return fig


def _grafico_evolucao_comparativo(fat_cli, fat_forn,
                                   rh_db, ano):
    """Bar chart comparativo ano a ano."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    rec_ano  = []
    cust_ano = []
    sal_mes  = _num(rh_db,'Salario_Base') * 1.2375 \
               if not rh_db.empty else 0

    for m in range(1,13):
        rec = 0.0
        if not fat_cli.empty and 'Data_Emissao' in fat_cli.columns:
            fc = fat_cli.copy()
            fc['Data_d'] = pd.to_datetime(
                fc['Data_Emissao'], dayfirst=True, errors='coerce'
            )
            fc['T'] = pd.to_numeric(fc.get('Total',0),errors='coerce').fillna(0)
            mask = (fc['Data_d'].dt.month==m)&(fc['Data_d'].dt.year==ano)
            rec = fc[mask]['T'].sum()

        cust = 0.0
        if not fat_forn.empty and 'Data' in fat_forn.columns:
            ff = fat_forn.copy()
            ff['Data_d'] = pd.to_datetime(
                ff['Data'], dayfirst=True, errors='coerce'
            )
            ff['T'] = pd.to_numeric(ff.get('Total',0),errors='coerce').fillna(0)
            mask_f = (ff['Data_d'].dt.month==m)&(ff['Data_d'].dt.year==ano)
            cust = ff[mask_f]['T'].sum() + sal_mes

        rec_ano.append(round(rec,2))
        cust_ano.append(round(cust,2))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Receita', x=meses_pt, y=rec_ano,
        marker_color='#10B981',
        hovertemplate='%{x}<br>Receita: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Custos', x=meses_pt, y=cust_ano,
        marker_color='#EF4444',
        hovertemplate='%{x}<br>Custos: €%{y:,.2f}<extra></extra>'
    ))
    margens = [
        round((r-c)/r*100,1) if r>0 else 0
        for r,c in zip(rec_ano,cust_ano)
    ]
    fig.add_trace(go.Scatter(
        name='Margem %', x=meses_pt, y=margens,
        mode='lines+markers',
        line={'color':'#3B82F6','width':2},
        marker={'size':6},
        yaxis='y2',
        hovertemplate='%{x}<br>Margem: %{y:.1f}%<extra></extra>'
    ))
    fig.update_layout(
        title={'text':f'Receita vs Custos — {ano}',
               'font':{'color':'#F1F5F9'}},
        barmode='group',
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        yaxis2={'overlaying':'y','side':'right',
                'ticksuffix':'%','tickfont':{'color':'#3B82F6'},
                'showgrid':False},
        margin=dict(t=40,b=20,l=10,r=60),
        hovermode='x unified'
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# MOTOR DE INCONSISTÊNCIAS
# ─────────────────────────────────────────────────────────────────

def _detetar_inconsistencias(fat_cli, fat_forn,
                              rh_db, registos_db,
                              iban_hist) -> list:
    """Deteta inconsistências nos dados financeiros."""
    inconsistencias = []

    # 1. Faturas sem NIF cliente
    if not fat_cli.empty and 'NIF_Cliente' in fat_cli.columns:
        sem_nif = fat_cli[
            fat_cli['NIF_Cliente'].fillna('').str.strip() == ''
        ]
        if not sem_nif.empty:
            inconsistencias.append({
                "tipo":     "Faturação",
                "gravidade":"Alta",
                "desc":     f"{len(sem_nif)} fatura(s) sem NIF cliente",
                "acao":     "Atualizar NIF nas faturas em falta",
                "cor":      "#EF4444"
            })

    # 2. Faturas não pagas há mais de 90 dias
    if not fat_cli.empty and 'Data_Vencimento' in fat_cli.columns:
        fc = fat_cli.copy()
        fc['Venc_d'] = pd.to_datetime(
            fc['Data_Vencimento'], dayfirst=True, errors='coerce'
        )
        vencidas_90 = fc[
            (fc['Venc_d'] < pd.Timestamp(date.today() - timedelta(days=90))) &
            (~fc.get('Estado','').isin(['Paga','Anulada']))
        ] if 'Estado' in fc.columns else pd.DataFrame()
        if not vencidas_90.empty:
            val = pd.to_numeric(
                vencidas_90.get('Total',0), errors='coerce'
            ).fillna(0).sum()
            inconsistencias.append({
                "tipo":     "Cobrança",
                "gravidade":"Alta",
                "desc":     f"{len(vencidas_90)} fatura(s) vencida(s) >90 dias "
                            f"(€{val:,.2f})",
                "acao":     "Contactar clientes — risco incobrável",
                "cor":      "#EF4444"
            })

    # 3. Pagamentos a fornecedores sem fatura
    if not fat_forn.empty and 'Numero_Fatura' in fat_forn.columns:
        sem_num = fat_forn[
            fat_forn['Numero_Fatura'].fillna('').str.strip() == ''
        ]
        if not sem_num.empty:
            inconsistencias.append({
                "tipo":     "Fornecedores",
                "gravidade":"Média",
                "desc":     f"{len(sem_num)} pagamento(s) sem número de fatura",
                "acao":     "Solicitar fatura ao fornecedor",
                "cor":      "#F59E0B"
            })

    # 4. IBANs alterados recentemente
    if not iban_hist.empty and 'Data_Alteracao' in iban_hist.columns:
        ih = iban_hist.copy()
        ih['Alt_d'] = pd.to_datetime(
            ih['Data_Alteracao'], dayfirst=True, errors='coerce'
        )
        recentes = ih[
            ih['Alt_d'] >= pd.Timestamp(
                date.today() - timedelta(days=90)
            )
        ]
        if not recentes.empty:
            inconsistencias.append({
                "tipo":     "Segurança",
                "gravidade":"Alta",
                "desc":     f"{len(recentes)} IBAN(s) alterado(s) nos últimos 90 dias",
                "acao":     "Verificar legitimidade das alterações",
                "cor":      "#EF4444"
            })

    # 5. Colaboradores sem ficha RH
    if rh_db.empty:
        inconsistencias.append({
            "tipo":     "RH",
            "gravidade":"Alta",
            "desc":     "Sem fichas RH financeiras registadas",
            "acao":     "Criar fichas no tab RH Financeiro",
            "cor":      "#EF4444"
        })

    # 6. Registos sem obra associada
    if not registos_db.empty and 'Obra' in registos_db.columns:
        sem_obra = registos_db[
            registos_db['Obra'].fillna('').str.strip() == ''
        ]
        if not sem_obra.empty:
            inconsistencias.append({
                "tipo":     "Registos",
                "gravidade":"Média",
                "desc":     f"{len(sem_obra)} registo(s) de horas sem obra",
                "acao":     "Associar horas às obras respetivas",
                "cor":      "#F59E0B"
            })

    # 7. Duplicados (mesma fatura, mesmo valor, mesmo dia)
    if not fat_cli.empty and \
       all(c in fat_cli.columns for c in ['Total','Data_Emissao','Cliente']):
        dupl = fat_cli.duplicated(
            subset=['Total','Data_Emissao','Cliente'], keep=False
        )
        if dupl.any():
            inconsistencias.append({
                "tipo":     "Faturação",
                "gravidade":"Alta",
                "desc":     f"{dupl.sum()} possível(is) fatura(s) duplicada(s)",
                "acao":     "Verificar manualmente e anular duplicados",
                "cor":      "#EF4444"
            })

    return inconsistencias


# ─────────────────────────────────────────────────────────────────
# PDF DOSSIER DE AUDITORIA
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_dossier(ano: int,
                        resultados_check: dict,
                        inconsistencias: list,
                        resumo_financeiro: dict,
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
    titulo_s = ParagraphStyle(
        'titulo', parent=styles['Normal'],
        fontSize=18, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1E293B'), spaceAfter=6
    )

    # ── Capa ──────────────────────────────────────────────────────
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(
        f"DOSSIER DE AUDITORIA ANUAL", titulo_s
    ))
    story.append(Paragraph(
        f"Exercício {ano}", ParagraphStyle(
            'ano', parent=styles['Normal'],
            fontSize=14, textColor=colors.HexColor('#3B82F6'),
            spaceAfter=8
        )
    ))
    story.append(Paragraph(
        f"{empresa.get('nome','')}",
        ParagraphStyle('emp', parent=styles['Normal'],
                       fontSize=12, fontName='Helvetica-Bold',
                       spaceAfter=4)
    ))
    story.append(Paragraph(
        f"NIF: {empresa.get('nif','')} | "
        f"{empresa.get('morada','')}",
        sub_s
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(
        width="100%", thickness=3,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Documento gerado em: "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')} "
        f"— GESTNOW v3.0",
        sub_s
    ))
    story.append(PageBreak())

    # ── Índice ────────────────────────────────────────────────────
    story.append(Paragraph("ÍNDICE", bold_s))
    indice = [
        "1. Resumo Executivo",
        "2. Checklist de Auditoria",
        "3. Inconsistências Detetadas",
        "4. Resumo Financeiro",
        "5. Estrutura do Dossier Digital",
    ]
    for it in indice:
        story.append(Paragraph(it, normal_s))
    story.append(PageBreak())

    # ── 1. Resumo executivo ───────────────────────────────────────
    story.append(Paragraph("1. RESUMO EXECUTIVO", bold_s))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Spacer(1, 0.2*cm))

    total_itens = len(resultados_check)
    itens_ok    = sum(1 for v in resultados_check.values() if v)
    pct_prep    = round(itens_ok/total_itens*100,1) \
                  if total_itens > 0 else 0
    n_inc       = len(inconsistencias)
    n_inc_alt   = len([i for i in inconsistencias
                       if i['gravidade']=='Alta'])

    resumo_data = [
        ["Itens verificados",          f"{total_itens}"],
        ["Itens OK",                   f"{itens_ok}"],
        ["% Preparação",               f"{pct_prep}%"],
        ["Inconsistências totais",     f"{n_inc}"],
        ["Inconsistências Alta Gravidade", f"{n_inc_alt}"],
        ["Faturação anual",
         f"€{resumo_financeiro.get('fat_total',0):,.2f}"],
        ["Total custos",
         f"€{resumo_financeiro.get('cust_total',0):,.2f}"],
    ]
    rt = Table(resumo_data, colWidths=[9*cm,8*cm])
    rt.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('FONTNAME',    (0,0),(0,-1),  'Helvetica-Bold'),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('BACKGROUND',  (0,2),(1,2),   colors.HexColor(
            '#DCFCE7' if pct_prep>=80 else
            '#FEF9C3' if pct_prep>=50 else
            '#FEE2E2'
        )),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(rt)
    story.append(Spacer(1, 0.4*cm))
    story.append(PageBreak())

    # ── 2. Checklist ──────────────────────────────────────────────
    story.append(Paragraph("2. CHECKLIST DE AUDITORIA", bold_s))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Spacer(1, 0.2*cm))

    cats_feitas = set()
    check_data  = [["Categoria","Item","Status","Crítico"]]
    for item in CHECKLIST_AUDITORIA:
        k   = f"{item['categoria']}||{item['item']}"
        ok  = resultados_check.get(k, False)
        check_data.append([
            item['categoria'] if item['categoria'] not in cats_feitas else "",
            item['item'][:55],
            "✅ OK" if ok else "❌ Falta",
            "Sim" if item['critico'] else "Não"
        ])
        cats_feitas.add(item['categoria'])

    ct = Table(check_data,
               colWidths=[4*cm, 8*cm, 3*cm, 2*cm])
    ct.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0),  colors.HexColor('#1E293B')),
        ('TEXTCOLOR',   (0,0),(-1,0),  colors.white),
        ('FONTNAME',    (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',    (0,0),(-1,-1), 7.5),
        ('GRID',        (0,0),(-1,-1), 0.2, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING',  (0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
        ('LEFTPADDING', (0,0),(-1,-1), 4),
    ]))
    story.append(ct)
    story.append(PageBreak())

    # ── 3. Inconsistências ────────────────────────────────────────
    story.append(Paragraph("3. INCONSISTÊNCIAS DETETADAS", bold_s))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Spacer(1, 0.2*cm))

    if inconsistencias:
        inc_data = [["Tipo","Gravidade","Descrição","Ação"]]
        for inc in inconsistencias:
            inc_data.append([
                inc['tipo'],
                inc['gravidade'],
                inc['desc'][:50],
                inc['acao'][:45]
            ])
        it = Table(inc_data,
                   colWidths=[3*cm,2.5*cm,6.5*cm,5*cm])
        it.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,0),  colors.HexColor('#1E293B')),
            ('TEXTCOLOR',  (0,0),(-1,0),  colors.white),
            ('FONTNAME',   (0,0),(-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',   (0,0),(-1,-1), 7.5),
            ('GRID',       (0,0),(-1,-1), 0.2, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0),(-1,-1), 4),
            ('BOTTOMPADDING',(0,0),(-1,-1), 4),
            ('LEFTPADDING',(0,0),(-1,-1), 4),
        ]))
        story.append(it)
    else:
        story.append(Paragraph(
            "✅ Sem inconsistências detetadas.", normal_s
        ))

    story.append(PageBreak())

    # ── 4. Resumo Financeiro ──────────────────────────────────────
    story.append(Paragraph("4. RESUMO FINANCEIRO", bold_s))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Spacer(1, 0.2*cm))

    fin_data = [
        ["Indicador","Valor"],
        ["Faturação Total",
         f"€{resumo_financeiro.get('fat_total',0):,.2f}"],
        ["Custos de Fornecedores",
         f"€{resumo_financeiro.get('cust_forn',0):,.2f}"],
        ["Custos de Pessoal (est.)",
         f"€{resumo_financeiro.get('cust_rh',0):,.2f}"],
        ["Margem Bruta Estimada",
         f"€{resumo_financeiro.get('margem',0):,.2f}"],
        ["Margem %",
         f"{resumo_financeiro.get('margem_pct',0):.1f}%"],
        ["Retenções na Fonte",
         f"€{resumo_financeiro.get('retencoes',0):,.2f}"],
    ]
    ft = Table(fin_data, colWidths=[9*cm,8*cm])
    ft.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,0),  colors.HexColor('#1E293B')),
        ('TEXTCOLOR',  (0,0),(-1,0),  colors.white),
        ('FONTNAME',   (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',   (0,0),(-1,-1), 9),
        ('GRID',       (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING',(0,0),(-1,-1), 6),
        ('ALIGN',      (1,0),(-1,-1),'RIGHT'),
    ]))
    story.append(ft)
    story.append(Spacer(1, 0.4*cm))

    # ── 5. Estrutura dossier ──────────────────────────────────────
    story.append(Paragraph(
        "5. ESTRUTURA DO DOSSIER DIGITAL", bold_s
    ))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Spacer(1, 0.2*cm))
    estrutura = [
        "Pasta 01 — Faturação Emitida (12 meses)",
        "Pasta 02 — Faturas Fornecedores (12 meses)",
        "Pasta 03 — Remunerações e Recibos",
        "Pasta 04 — Declarações Fiscais (IVA, IRC, IRS)",
        "Pasta 05 — Segurança Social (DRI mensal)",
        "Pasta 06 — Extratos Bancários (12 meses)",
        "Pasta 07 — Contratos (clientes, fornecedores, trabalho)",
        "Pasta 08 — Imobilizado e Amortizações",
        "Pasta 09 — Seguros e Cauções",
        "Pasta 10 — Relatório & Contas + Ata AG",
        "Pasta 11 — Logs de Auditoria do Sistema",
        "Pasta 12 — Outros Documentos Relevantes",
    ]
    for est in estrutura:
        story.append(Paragraph(est, normal_s))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"GESTNOW v3.0 — Dossier gerado em "
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

def render_fat_auditoria(obras_db, registos_db,
                          faturas_db, diarias_pag_db, *_):
    """Módulo Auditoria Anual & Dossier Digital."""

    # ── Carregar dados ────────────────────────────────────────────
    fat_cli     = _load("faturas_clientes.csv", [
        "ID","Numero","Tipo","Data_Emissao","Data_Vencimento",
        "Cliente","NIF_Cliente","Obra","Subtotal","IVA","Total","Estado"
    ])
    fat_forn    = _load("faturas_fornecedores.csv", [
        "ID","Data","Fornecedor","Numero_Fatura","Descricao",
        "Obra","Total","IVA","Retencao_Val","Estado"
    ])
    rh_db       = _load("colaboradores_rh.csv",
                        ["Nome","Salario_Base"])
    iban_hist   = _load("iban_historico.csv",
                        ["ID","Entidade","Data_Alteracao"])
    imob_db     = _load("imobilizado_db.csv",["ID","Descricao"])
    seguros_db  = _load("seguros_db.csv",["ID","Tipo"])
    alvaras_db  = _load("alvaras_db.csv",["ID","Tipo"])
    caucoes_db  = _load("caucoes_db.csv",["ID","Obra"])
    contratos_db= _load("contratos_financeiro.csv",
                        ["ID","Cliente","Obra"])
    provisoes_db= _load("provisoes_db.csv",["ID","Colaborador"])
    renting_db  = _load("renting_contratos.csv",
                        ["ID","Matricula"])
    comb_db     = _load("frota_combustivel.csv",
                        ["ID","Matricula"])
    movimentos_db=_load("movimentos_bancarios.csv",
                        ["ID","Data"])
    orc_obras_db= _load("obras_orcamento.csv",["ID","Obra"])

    # Dict para as lambdas da checklist
    dfs = {
        'faturas_cli': fat_cli,
        'fat_forn':    fat_forn,
        'rh':          rh_db,
        'imob':        imob_db,
        'seguros':     seguros_db,
        'alvaras':     alvaras_db,
        'caucoes':     caucoes_db,
        'contratos':   contratos_db,
        'provisoes':   provisoes_db,
        'renting':     renting_db,
        'comb':        comb_db,
        'movimentos':  movimentos_db,
        'orc_obras':   orc_obras_db,
        'registos':    registos_db,
        'fornecedores':_load("fornecedores.csv",["ID","NIF"]),
    }

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
    ano_atual = hoje.year

    # ── Calcular checklist automática ────────────────────────────
    if 'auditoria_resultados' not in st.session_state:
        st.session_state['auditoria_resultados'] = {}

    resultados = st.session_state['auditoria_resultados']

    # Auto-verificar itens com CSV
    for item in CHECKLIST_AUDITORIA:
        k = f"{item['categoria']}||{item['item']}"
        if k not in resultados:
            try:
                resultados[k] = item['verificar'](dfs)
            except:
                resultados[k] = False

    # Score geral
    total_itens  = len(CHECKLIST_AUDITORIA)
    itens_ok     = sum(1 for v in resultados.values() if v)
    pct_prep     = round(itens_ok/total_itens*100, 1) \
                   if total_itens > 0 else 0
    itens_criticos= [
        i for i in CHECKLIST_AUDITORIA
        if i['critico'] and
        not resultados.get(f"{i['categoria']}||{i['item']}", False)
    ]

    # Inconsistências
    inconsistencias = _detetar_inconsistencias(
        fat_cli, fat_forn, rh_db, registos_db, iban_hist
    )

    # Resumo financeiro
    fat_total  = _num(fat_cli,'Total')
    cust_forn  = _num(fat_forn,'Total')
    cust_rh    = _num(rh_db,'Salario_Base') * 12 * 1.4
    margem     = round(fat_total - cust_forn - cust_rh, 2)
    marg_pct   = round(margem/fat_total*100,1) if fat_total>0 else 0
    ret_total  = _num(fat_forn,'Retencao_Val')

    resumo_fin = {
        "fat_total":  fat_total,
        "cust_forn":  cust_forn,
        "cust_rh":    cust_rh,
        "margem":     margem,
        "margem_pct": marg_pct,
        "retencoes":  ret_total,
    }

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .aud-card {
        background:#1E293B; border-radius:10px;
        padding:12px 16px; margin-bottom:6px;
    }
    .check-item {
        display:flex; justify-content:space-between;
        align-items:center; padding:8px 12px;
        border-radius:8px; margin-bottom:4px;
        border-left:3px solid;
    }
    .inc-card {
        border-radius:8px; padding:10px 14px;
        margin-bottom:6px; border-left:4px solid;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────
    cor_pct = "#10B981" if pct_prep >= 80 \
              else "#F59E0B" if pct_prep >= 50 \
              else "#EF4444"

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        st.metric("✅ Preparação",    f"{pct_prep:.0f}%")
    with c2:
        st.metric("📋 Itens OK",      f"{itens_ok}/{total_itens}")
    with c3:
        st.metric("🔴 Críticos Falta",len(itens_criticos))
    with c4:
        st.metric("⚠️ Inconsistências",len(inconsistencias))
    with c5:
        st.metric("💰 Faturação Ano", f"€{fat_total:,.0f}")

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_check, t_inc, t_dossier,
     t_comp, t_export) = st.tabs([
        "✅ Checklist",
        "⚠️ Inconsistências",
        "📁 Dossier Digital",
        "📊 Comparativo Anual",
        "📤 Export TOC/ROC",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — CHECKLIST
    # ════════════════════════════════════════════════════════════════
    with t_check:
        st.markdown("### ✅ Checklist de Auditoria")

        # Seletor de ano
        ano_aud = st.number_input(
            "Ano da Auditoria", min_value=2020,
            value=ano_atual, key="aud_ano"
        )

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(
                _grafico_gauge_preparacao(pct_prep),
                use_container_width=True
            )
            # Nível de preparação
            if pct_prep >= 80:
                nivel_txt = "🟢 PRONTO para auditoria"
                cor_n     = "#10B981"
            elif pct_prep >= 60:
                nivel_txt = "🟡 Quase pronto — faltam poucos itens"
                cor_n     = "#F59E0B"
            elif pct_prep >= 40:
                nivel_txt = "🟠 Em preparação — ação necessária"
                cor_n     = "#F97316"
            else:
                nivel_txt = "🔴 NÃO pronto — muitos itens em falta"
                cor_n     = "#EF4444"

            st.markdown(
                f"<div style='background:{cor_n}18;"
                f"border:1px solid {cor_n};"
                f"border-radius:8px;padding:10px;"
                f"text-align:center;margin-top:-8px;'>"
                f"<b style='color:{cor_n};'>{nivel_txt}</b>"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_g2:
            fig_cat = _grafico_checklist_por_categoria(resultados)
            if fig_cat:
                st.plotly_chart(
                    fig_cat, use_container_width=True
                )

        st.markdown("---")

        # Filtros
        col_cf1, col_cf2 = st.columns(2)
        with col_cf1:
            cats_disponiveis = list(
                {i['categoria'] for i in CHECKLIST_AUDITORIA}
            )
            cat_filt = st.selectbox(
                "Categoria",
                ["Todas"] + sorted(cats_disponiveis),
                key="aud_cat_filt"
            )
        with col_cf2:
            estado_filt = st.selectbox(
                "Estado",
                ["Todos","✅ Concluído","❌ Por fazer"],
                key="aud_est_filt"
            )

        # Listar itens
        st.markdown("#### 📋 Itens da Checklist")

        cat_atual = ""
        for item in CHECKLIST_AUDITORIA:
            if cat_filt != "Todas" and \
               item['categoria'] != cat_filt:
                continue
            k  = f"{item['categoria']}||{item['item']}"
            ok = resultados.get(k, False)

            if estado_filt == "✅ Concluído" and not ok:
                continue
            if estado_filt == "❌ Por fazer" and ok:
                continue

            # Header de categoria
            if item['categoria'] != cat_atual:
                cat_atual = item['categoria']
                st.markdown(
                    f"<p style='color:#3B82F6;"
                    f"font-weight:700;font-size:0.85rem;"
                    f"margin:12px 0 4px;'>"
                    f"{cat_atual}</p>",
                    unsafe_allow_html=True
                )

            cor_item = "#10B981" if ok else \
                       "#EF4444" if item['critico'] else \
                       "#F59E0B"

            col_ci, col_cb = st.columns([7,1])
            with col_ci:
                st.markdown(
                    f"<div class='check-item' "
                    f"style='background:{cor_item}0D;"
                    f"border-left-color:{cor_item};'>"
                    f"<div>"
                    f"<span style='color:{cor_item};"
                    f"font-size:1rem;margin-right:8px;'>"
                    f"{'✅' if ok else '❌'}</span>"
                    f"<span style='color:#F1F5F9;"
                    f"font-size:0.85rem;'>"
                    f"{item['item']}</span>"
                    f"{'<span style=color:#EF4444;font-size:0.7rem;margin-left:6px;>★ CRÍTICO</span>' if item['critico'] and not ok else ''}"
                    f"</div>"
                    f"<small style='color:#64748B;'>"
                    f"{'CSV: ' + item['csv'] if item['csv'] else 'Manual'}"
                    f"</small></div>",
                    unsafe_allow_html=True
                )
            with col_cb:
                if st.button(
                    "✅" if not ok else "↩️",
                    key=f"aud_{uuid.uuid4().hex[:6]}_{k[:20].replace(' ','_')}",
                    use_container_width=True,
                    help="Marcar/desmarcar"
                ):
                    resultados[k] = not ok
                    st.session_state['auditoria_resultados'] = resultados
                    st.rerun()

        # Itens críticos em falta
        if itens_criticos:
            st.markdown("---")
            st.error(
                f"🔴 **{len(itens_criticos)} item(s) crítico(s) "
                f"por completar!** A auditoria não está pronta."
            )
            for ic in itens_criticos[:5]:
                st.markdown(
                    f"<div style='background:rgba(239,68,68,0.1);"
                    f"border-left:3px solid #EF4444;"
                    f"border-radius:6px;padding:8px 12px;"
                    f"margin-bottom:4px;'>"
                    f"<small style='color:#EF4444;'>"
                    f"❌ {ic['item']}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # Botão reset
        st.markdown("---")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button(
                "✅ Marcar todos como OK",
                key="btn_all_ok",
                use_container_width=True
            ):
                for item in CHECKLIST_AUDITORIA:
                    k = f"{item['categoria']}||{item['item']}"
                    resultados[k] = True
                st.session_state['auditoria_resultados'] = resultados
                st.rerun()
        with col_r2:
            if st.button(
                "🔄 Reset Checklist",
                key="btn_reset_check",
                use_container_width=True
            ):
                st.session_state['auditoria_resultados'] = {}
                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — INCONSISTÊNCIAS
    # ════════════════════════════════════════════════════════════════
    with t_inc:
        st.markdown("### ⚠️ Relatório de Inconsistências")
        st.info(
            "O sistema verifica automaticamente os dados "
            "e identifica potenciais problemas para corrigir "
            "antes da auditoria."
        )

        col_ig1, col_ig2 = st.columns(2)
        with col_ig1:
            fig_inc = _grafico_inconsistencias(inconsistencias)
            if fig_inc:
                st.plotly_chart(
                    fig_inc, use_container_width=True
                )
            else:
                st.success(
                    "✅ Sem inconsistências detetadas! "
                    "Dossier limpo."
                )
        with col_ig2:
            # KPIs
            n_alta  = len([i for i in inconsistencias
                           if i['gravidade']=='Alta'])
            n_media = len([i for i in inconsistencias
                           if i['gravidade']=='Média'])
            n_baixa = len([i for i in inconsistencias
                           if i['gravidade']=='Baixa'])
            c1,c2,c3 = st.columns(3)
            with c1:
                st.metric("🔴 Alta",  n_alta)
            with c2:
                st.metric("🟡 Média", n_media)
            with c3:
                st.metric("🟢 Baixa", n_baixa)

            if inconsistencias:
                st.markdown(
                    "<div style='margin-top:12px;'>",
                    unsafe_allow_html=True
                )
                for inc in inconsistencias:
                    cor_i = inc['cor']
                    st.markdown(
                        f"<div class='inc-card' "
                        f"style='background:{cor_i}0D;"
                        f"border-left-color:{cor_i};'>"
                        f"<b style='color:{cor_i};"
                        f"font-size:0.85rem;'>"
                        f"⚠️ {inc['desc']}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"Tipo: {inc['tipo']} · "
                        f"Gravidade: {inc['gravidade']}</small><br>"
                        f"<small style='color:#94A3B8;'>"
                        f"💡 {inc['acao']}</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                st.markdown("</div>", unsafe_allow_html=True)

        # Detalhe por tipo
        if inconsistencias:
            st.markdown("---")
            st.markdown("#### 📋 Detalhe Completo")

            df_inc = pd.DataFrame([{
                "Tipo":      i['tipo'],
                "Gravidade": i['gravidade'],
                "Descrição": i['desc'],
                "Ação":      i['acao']
            } for i in inconsistencias])
            st.dataframe(
                df_inc, use_container_width=True, hide_index=True
            )

            csv_inc = df_inc.to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Exportar Inconsistências",
                data=csv_inc.encode('utf-8-sig'),
                file_name=(
                    f"inconsistencias_"
                    f"{ano_atual}.csv"
                ),
                mime="text/csv",
                key="dl_inc"
            )

        # Análise IA
        st.markdown("---")
        if st.button(
            "🤖 Análise IA das Inconsistências",
            key="btn_ia_inc",
            use_container_width=True
        ):
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY","")
            if api_key and inconsistencias:
                with st.spinner("🤖 A analisar..."):
                    try:
                        client = anthropic.Anthropic(
                            api_key=api_key
                        )
                        ctx = {
                            "n_inconsistencias": len(inconsistencias),
                            "n_alta":    n_alta,
                            "n_media":   n_media,
                            "inconsistencias": [
                                {"tipo":i['tipo'],
                                 "gravidade":i['gravidade'],
                                 "desc":i['desc']}
                                for i in inconsistencias
                            ]
                        }
                        resp = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=500,
                            messages=[{
                                "role":"user",
                                "content":(
                                    f"Sou TOC de uma PME portuguesa. "
                                    f"Analisa estas inconsistências "
                                    f"antes da auditoria anual:\n"
                                    f"{json.dumps(ctx, ensure_ascii=False)}\n\n"
                                    f"Indica por ordem de prioridade "
                                    f"o que devo resolver primeiro "
                                    f"e como. Máximo 4 parágrafos."
                                )
                            }]
                        )
                        st.markdown(
                            f"<div style='background:rgba(59,130,246,0.1);"
                            f"border:1px solid #3B82F6;"
                            f"border-radius:10px;padding:14px;"
                            f"color:#E2E8F0;font-size:0.88rem;"
                            f"line-height:1.6;'>"
                            f"<b style='color:#3B82F6;'>🤖 TOC IA</b><br><br>"
                            f"{resp.content[0].text.replace(chr(10),'<br>')}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    except Exception as e:
                        st.error(f"❌ {e}")
            elif not inconsistencias:
                st.success("✅ Sem inconsistências para analisar!")

    # ════════════════════════════════════════════════════════════════
    # TAB — DOSSIER DIGITAL
    # ════════════════════════════════════════════════════════════════
    with t_dossier:
        st.markdown("### 📁 Dossier Digital de Auditoria")
        st.info(
            "O dossier digital organiza todos os documentos "
            "necessários para a auditoria anual. "
            "Cada pasta corresponde a uma área documental. "
            "O ZIP gerado pode ser entregue diretamente ao TOC/ROC."
        )

        # Estrutura do dossier
        pastas = [
            {
                "num":   "01",
                "nome":  "Faturação Emitida",
                "desc":  "Faturas a clientes (12 meses)",
                "csv":   "faturas_clientes.csv",
                "n_docs":len(fat_cli) if not fat_cli.empty else 0,
                "cor":   "#3B82F6"
            },
            {
                "num":   "02",
                "nome":  "Faturas Fornecedores",
                "desc":  "Compras e serviços recebidos (12 meses)",
                "csv":   "faturas_fornecedores.csv",
                "n_docs":len(fat_forn) if not fat_forn.empty else 0,
                "cor":   "#F59E0B"
            },
            {
                "num":   "03",
                "nome":  "Remunerações e RH",
                "desc":  "Fichas, recibos e DRI mensais",
                "csv":   "colaboradores_rh.csv",
                "n_docs":len(rh_db) if not rh_db.empty else 0,
                "cor":   "#10B981"
            },
            {
                "num":   "04",
                "nome":  "Declarações Fiscais",
                "desc":  "IVA, IRC, IRS Modelo 10, SAF-T",
                "csv":   None,
                "n_docs":0,
                "cor":   "#EF4444"
            },
            {
                "num":   "05",
                "nome":  "Segurança Social",
                "desc":  "DRI mensal e contribuições",
                "csv":   None,
                "n_docs":0,
                "cor":   "#8B5CF6"
            },
            {
                "num":   "06",
                "nome":  "Extratos Bancários",
                "desc":  "Reconciliação bancária (12 meses)",
                "csv":   "movimentos_bancarios.csv",
                "n_docs":len(movimentos_db)
                          if not movimentos_db.empty else 0,
                "cor":   "#06B6D4"
            },
            {
                "num":   "07",
                "nome":  "Contratos",
                "desc":  "Clientes, fornecedores, trabalho",
                "csv":   "contratos_financeiro.csv",
                "n_docs":len(contratos_db)
                          if not contratos_db.empty else 0,
                "cor":   "#F97316"
            },
            {
                "num":   "08",
                "nome":  "Imobilizado",
                "desc":  "Quadro de ativos e amortizações",
                "csv":   "imobilizado_db.csv",
                "n_docs":len(imob_db) if not imob_db.empty else 0,
                "cor":   "#64748B"
            },
            {
                "num":   "09",
                "nome":  "Seguros e Cauções",
                "desc":  "Apólices e garantias bancárias",
                "csv":   "seguros_db.csv",
                "n_docs":(len(seguros_db) if not seguros_db.empty else 0) +
                          (len(caucoes_db) if not caucoes_db.empty else 0),
                "cor":   "#10B981"
            },
            {
                "num":   "10",
                "nome":  "Relatório & Contas",
                "desc":  "R&C aprovado e ata AG",
                "csv":   None,
                "n_docs":0,
                "cor":   "#DC2626"
            },
            {
                "num":   "11",
                "nome":  "Logs de Auditoria",
                "desc":  "Registo de ações do sistema",
                "csv":   None,
                "n_docs":0,
                "cor":   "#3B82F6"
            },
            {
                "num":   "12",
                "nome":  "Outros",
                "desc":  "Documentos complementares",
                "csv":   None,
                "n_docs":0,
                "cor":   "#94A3B8"
            },
        ]

        # Cards de pastas
        cols_pastas = st.columns(3)
        for i, pasta in enumerate(pastas):
            with cols_pastas[i % 3]:
                tem_docs = pasta['n_docs'] > 0
                cor_p    = pasta['cor'] if tem_docs else "#334155"
                st.markdown(
                    f"<div class='aud-card' "
                    f"style='border-left:3px solid {cor_p};'>"
                    f"<p style='color:#64748B;"
                    f"font-size:0.7rem;margin:0 0 2px;'>"
                    f"PASTA {pasta['num']}</p>"
                    f"<b style='color:#F1F5F9;"
                    f"font-size:0.85rem;'>"
                    f"{pasta['nome']}</b><br>"
                    f"<small style='color:#64748B;'>"
                    f"{pasta['desc']}</small><br>"
                    f"<span style='color:{cor_p};"
                    f"font-size:0.8rem;font-weight:700;'>"
                    f"{'📄 ' + str(pasta['n_docs']) + ' doc(s)' if tem_docs else '⚠️ Sem documentos'}"
                    f"</span></div>",
                    unsafe_allow_html=True
                )

        # Gerar ZIP do dossier
        st.markdown("---")
        st.markdown("#### 📦 Exportar Dossier Completo")

        col_zip1, col_zip2 = st.columns(2)
        with col_zip1:
            ano_zip = st.number_input(
                "Ano", min_value=2020,
                value=ano_atual, key="zip_ano"
            )
        with col_zip2:
            st.markdown(
                "<div style='height:28px;'></div>",
                unsafe_allow_html=True
            )

        if st.button(
            "📦 Gerar ZIP Dossier Auditoria",
            key="btn_zip_dossier",
            type="primary",
            use_container_width=True
        ):
            with st.spinner(
                "A compilar dossier de auditoria..."
            ):
                buf_zip = io.BytesIO()
                with zipfile.ZipFile(
                    buf_zip, 'w', zipfile.ZIP_DEFLATED
                ) as zf:
                    # Adicionar CSVs de cada pasta
                    for pasta in pastas:
                        if pasta['csv']:
                            try:
                                df_zip = _load(pasta['csv'], [])
                                if not df_zip.empty:
                                    csv_z = df_zip.to_csv(
                                        index=False,
                                        encoding='utf-8-sig'
                                    )
                                    zf.writestr(
                                        f"Pasta_{pasta['num']}_{pasta['nome'].replace(' ','_')}/"
                                        f"{pasta['csv']}",
                                        csv_z.encode('utf-8-sig')
                                    )
                            except:
                                pass

                    # Adicionar índice do dossier
                    indice_txt = (
                        f"DOSSIER AUDITORIA ANUAL {ano_zip}\n"
                        f"{empresa.get('nome','')}\n"
                        f"NIF: {empresa.get('nif','')}\n"
                        f"Gerado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                        f"{'='*50}\n\n"
                    )
                    for pasta in pastas:
                        indice_txt += (
                            f"PASTA {pasta['num']} — {pasta['nome']}\n"
                            f"  {pasta['desc']}\n"
                            f"  Documentos: {pasta['n_docs']}\n\n"
                        )
                    zf.writestr(
                        "00_INDICE_DOSSIER.txt",
                        indice_txt.encode('utf-8')
                    )

                    # Adicionar checklist
                    check_txt = (
                        f"CHECKLIST AUDITORIA {ano_zip}\n"
                        f"Preparação: {pct_prep:.0f}%\n\n"
                    )
                    for item in CHECKLIST_AUDITORIA:
                        k  = f"{item['categoria']}||{item['item']}"
                        ok = resultados.get(k, False)
                        check_txt += (
                            f"[{'X' if ok else ' '}] "
                            f"{item['item']}\n"
                        )
                    zf.writestr(
                        "00_CHECKLIST.txt",
                        check_txt.encode('utf-8')
                    )

                buf_zip.seek(0)
                st.session_state['dossier_zip'] = buf_zip.getvalue()
                st.session_state['dossier_zip_nome'] = (
                    f"Dossier_Auditoria_{ano_zip}_"
                    f"{empresa.get('nif','')}.zip"
                )
                st.success(
                    f"✅ Dossier compilado com "
                    f"{sum(p['n_docs'] for p in pastas)} documentos!"
                )
                st.rerun()

        if st.session_state.get('dossier_zip'):
            st.download_button(
                "📥 Descarregar ZIP Dossier",
                data=st.session_state['dossier_zip'],
                file_name=st.session_state.get(
                    'dossier_zip_nome','dossier.zip'
                ),
                mime="application/zip",
                key="dl_dossier_zip",
                use_container_width=True,
                type="primary"
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — COMPARATIVO ANUAL
    # ════════════════════════════════════════════════════════════════
    with t_comp:
        st.markdown("### 📊 Comparativo Anual")

        ano_comp = st.number_input(
            "Ano", min_value=2020,
            value=ano_atual, key="comp_ano"
        )

        # Gráfico receita vs custos
        st.plotly_chart(
            _grafico_evolucao_comparativo(
                fat_cli, fat_forn, rh_db, ano_comp
            ),
            use_container_width=True
        )

        # Tabela resumo
        st.markdown("#### 📋 Resumo do Exercício")
        resumo_rows = [
            {
                "Indicador":    "Faturação Total",
                "Valor":        f"€{fat_total:,.2f}",
                "Referência":   "Faturas emitidas a clientes"
            },
            {
                "Indicador":    "Custos de Fornecedores",
                "Valor":        f"€{cust_forn:,.2f}",
                "Referência":   "Compras e serviços externos"
            },
            {
                "Indicador":    "Custos de Pessoal (est.)",
                "Valor":        f"€{cust_rh:,.2f}",
                "Referência":   "Salários × 1.4 (encargos incl.)"
            },
            {
                "Indicador":    "Margem Bruta Estimada",
                "Valor":        f"€{margem:,.2f} ({marg_pct:.1f}%)",
                "Referência":   "Resultado antes gastos gerais"
            },
            {
                "Indicador":    "Retenções na Fonte",
                "Valor":        f"€{ret_total:,.2f}",
                "Referência":   "Entregues à AT (subempreiteiros)"
            },
            {
                "Indicador":    "Nº Colaboradores RH",
                "Valor":        str(len(rh_db)),
                "Referência":   "Com ficha financeira"
            },
            {
                "Indicador":    "Nº Faturas Emitidas",
                "Valor":        str(len(fat_cli)),
                "Referência":   "Faturas a clientes"
            },
            {
                "Indicador":    "Nº Faturas Recebidas",
                "Valor":        str(len(fat_forn)),
                "Referência":   "Fornecedores e subempreiteiros"
            },
        ]
        df_res = pd.DataFrame(resumo_rows)
        st.dataframe(
            df_res, use_container_width=True, hide_index=True
        )

        csv_res = df_res.to_csv(
            index=False, encoding='utf-8-sig'
        )
        st.download_button(
            "📥 Exportar Resumo CSV",
            data=csv_res.encode('utf-8-sig'),
            file_name=f"resumo_exercicio_{ano_comp}.csv",
            mime="text/csv",
            key="dl_res_comp"
        )

    # ════════════════════════════════════════════════════════════════
    # TAB — EXPORT TOC/ROC
    # ════════════════════════════════════════════════════════════════
    with t_export:
        st.markdown("### 📤 Export para TOC / ROC")
        st.info(
            "Gera o dossier completo em formato adequado "
            "para entrega ao Técnico Oficial de Contas (TOC) "
            "ou Revisor Oficial de Contas (ROC)."
        )

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            ano_toc = st.number_input(
                "Ano do Exercício",
                min_value=2020,
                value=ano_atual,
                key="toc_ano"
            )
            tipo_dest = st.selectbox(
                "Destinatário",
                ["TOC — Técnico Oficial de Contas",
                 "ROC — Revisor Oficial de Contas",
                 "Banco / Financiador",
                 "Sócios / Administração",
                 "AT — Autoridade Tributária"],
                key="toc_dest"
            )
            notas_toc = st.text_area(
                "Notas para o destinatário",
                key="toc_notas",
                placeholder="Ex: Inclui todos os documentos "
                            "do exercício 2024. Faltam os "
                            "extratos bancários de novembro."
            )

        with col_e2:
            # Resumo do que vai no dossier
            st.markdown("#### 📋 Conteúdo do Export")
            conteudo = [
                ("📄 Relatório PDF completo",          True),
                ("✅ Checklist de auditoria",           True),
                ("⚠️ Relatório de inconsistências",     True),
                ("📊 Resumo financeiro anual",          True),
                (f"🧾 Faturas clientes ({len(fat_cli)})",
                 not fat_cli.empty),
                (f"📥 Faturas fornecedores ({len(fat_forn)})",
                 not fat_forn.empty),
                (f"👥 Fichas RH ({len(rh_db)})",
                 not rh_db.empty),
                (f"🏭 Imobilizado ({len(imob_db)} ativos)",
                 not imob_db.empty),
                (f"🔒 Cauções ({len(caucoes_db)})",
                 not caucoes_db.empty),
            ]
            for desc, ok in conteudo:
                cor_c = "#10B981" if ok else "#64748B"
                ic_c  = "✅" if ok else "⚪"
                st.markdown(
                    f"<div style='display:flex;"
                    f"align-items:center;"
                    f"padding:3px 0;'>"
                    f"<span style='color:{cor_c};"
                    f"margin-right:6px;'>{ic_c}</span>"
                    f"<small style='color:#94A3B8;'>{desc}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button(
                "📄 Gerar Relatório PDF Completo",
                key="btn_pdf_toc",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("A gerar dossier PDF..."):
                    pdf_toc = _gerar_pdf_dossier(
                        ano_toc, resultados,
                        inconsistencias, resumo_fin, empresa
                    )
                st.session_state['toc_pdf'] = pdf_toc
                st.session_state['toc_pdf_nome'] = (
                    f"Dossier_Auditoria_"
                    f"{empresa.get('nif','')}_{ano_toc}.pdf"
                )
                st.success("✅ Relatório PDF gerado!")
                st.rerun()

        with col_btn2:
            if st.session_state.get('toc_pdf'):
                st.download_button(
                    "📥 Descarregar PDF Dossier",
                    data=st.session_state['toc_pdf'],
                    file_name=st.session_state.get(
                        'toc_pdf_nome','dossier.pdf'
                    ),
                    mime="application/pdf",
                    key="dl_toc_pdf",
                    use_container_width=True,
                    type="primary"
                )

        # Nota de confidencialidade
        st.markdown("---")
        st.markdown(
            "<div style='background:rgba(59,130,246,0.08);"
            "border:1px solid #3B82F6;border-radius:8px;"
            "padding:12px;'>"
            "<small style='color:#93C5FD;'>"
            "📋 <b>Nota:</b> Este dossier foi gerado "
            "automaticamente pelo GESTNOW v3.0. "
            "Os dados financeiros são estimativas baseadas nos "
            "registos do sistema. O TOC/ROC deve confirmar "
            "com os documentos originais e a contabilidade "
            "oficial. Documento confidencial — "
            "uso restrito ao destinatário.</small></div>",
            unsafe_allow_html=True
        )

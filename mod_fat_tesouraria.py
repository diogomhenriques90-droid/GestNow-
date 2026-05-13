"""
GESTNOW v3 — mod_fat_tesouraria.py
Passo 7 — Tesouraria & Cash Flow
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, io, os, base64
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

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()

def _dias_para(data_str: str) -> int:
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return 999

def _parse_data(data_str: str):
    for fmt in ["%d/%m/%Y", "%d/%m/%Y %H:%M"]:
        try:
            return datetime.strptime(data_str, fmt).date()
        except:
            pass
    return None


# ─────────────────────────────────────────────────────────────────
# MOTOR DE CASH FLOW PREVISIONAL
# ─────────────────────────────────────────────────────────────────

def _calcular_cashflow_90d(faturas_cli, faturas_forn,
                            rh_db, renting_db,
                            diarias_pag_db,
                            contas_db) -> list:
    """
    Projeta cash flow dia a dia para os próximos 90 dias.
    Devolve lista de dicts com data, entradas, saídas, saldo.
    """
    hoje        = date.today()
    saldo_ini   = 0.0

    # Saldo atual das contas bancárias
    if not contas_db.empty and 'Saldo' in contas_db.columns:
        saldo_ini = pd.to_numeric(
            contas_db['Saldo'], errors='coerce'
        ).fillna(0).sum()

    # Dicionário dia → {entradas, saídas, items}
    dias = {}
    for i in range(91):
        d = hoje + timedelta(days=i)
        dias[d] = {"entradas": 0.0, "saidas": 0.0, "items": []}

    # ── ENTRADAS — faturas a receber ──────────────────────────────
    if not faturas_cli.empty and 'Data_Vencimento' in faturas_cli.columns:
        fc = faturas_cli.copy()
        fc['Venc_d']    = pd.to_datetime(
            fc['Data_Vencimento'], dayfirst=True, errors='coerce'
        )
        fc['Total_Num'] = pd.to_numeric(
            fc.get('Total',0), errors='coerce'
        ).fillna(0)
        nao_pagas = fc[
            ~fc.get('Estado','').isin(['Paga','Anulada'])
        ] if 'Estado' in fc.columns else fc

        for _, row in nao_pagas.iterrows():
            if pd.notna(row['Venc_d']):
                d_venc = row['Venc_d'].date()
                # DNA do cliente — estimativa de atraso
                atraso = 0  # pode ser personalizado por cliente
                d_real = d_venc + timedelta(days=atraso)
                if hoje <= d_real <= hoje + timedelta(days=90):
                    dias[d_real]["entradas"] += row['Total_Num']
                    dias[d_real]["items"].append({
                        "tipo":  "entrada",
                        "desc":  f"🧾 {row.get('Numero','')} — "
                                 f"{row.get('Cliente','')}",
                        "valor": row['Total_Num']
                    })

    # ── SAÍDAS — salários (dia 25 de cada mês) ───────────────────
    custo_sal_total = 0.0
    if not rh_db.empty and 'Salario_Base' in rh_db.columns:
        for _, rh_row in rh_db.iterrows():
            sal = float(rh_row.get('Salario_Base',0) or 0)
            custo_sal_total += sal * 1.2375  # salário + TSU estimada

    for i in range(3):  # próximos 3 meses
        mes_sal = (hoje.month + i - 1) % 12 + 1
        ano_sal = hoje.year + ((hoje.month + i - 1) // 12)
        try:
            d_sal = date(ano_sal, mes_sal, 25)
        except:
            d_sal = date(ano_sal, mes_sal, 28)
        if hoje <= d_sal <= hoje + timedelta(days=90):
            if d_sal in dias:
                dias[d_sal]["saidas"] += custo_sal_total
                dias[d_sal]["items"].append({
                    "tipo":  "saida",
                    "desc":  f"👥 Salários {mes_sal:02d}/{ano_sal}",
                    "valor": custo_sal_total
                })

    # ── SAÍDAS — rendas de renting (dia 1 de cada mês) ───────────
    if not renting_db.empty and 'Valor_Mensal' in renting_db.columns:
        ativos_rent = renting_db[
            renting_db.get('Estado','') != 'Terminado'
        ] if 'Estado' in renting_db.columns else renting_db
        renda_total = pd.to_numeric(
            ativos_rent['Valor_Mensal'], errors='coerce'
        ).fillna(0).sum()

        for i in range(3):
            mes_r = (hoje.month + i - 1) % 12 + 1
            ano_r = hoje.year + ((hoje.month + i - 1) // 12)
            try:
                d_rent = date(ano_r, mes_r, 1)
            except:
                continue
            if hoje <= d_rent <= hoje + timedelta(days=90):
                if d_rent in dias:
                    dias[d_rent]["saidas"] += renda_total
                    dias[d_rent]["items"].append({
                        "tipo":  "saida",
                        "desc":  f"🚗 Rendas Renting {mes_r:02d}/{ano_r}",
                        "valor": renda_total
                    })

    # ── SAÍDAS — faturas fornecedores ─────────────────────────────
    faturas_forn_db = _load("faturas_fornecedores.csv", [
        "ID","Data_Vencimento","Fornecedor","Total","Estado"
    ])
    if not faturas_forn_db.empty and \
       'Data_Vencimento' in faturas_forn_db.columns:
        ff = faturas_forn_db.copy()
        ff['Venc_d']    = pd.to_datetime(
            ff['Data_Vencimento'], dayfirst=True, errors='coerce'
        )
        ff['Total_Num'] = pd.to_numeric(
            ff.get('Total',0), errors='coerce'
        ).fillna(0)
        pend_forn = ff[
            ~ff.get('Estado','').isin(['Pago','Anulado'])
        ] if 'Estado' in ff.columns else ff

        for _, row in pend_forn.iterrows():
            if pd.notna(row['Venc_d']):
                d_vf = row['Venc_d'].date()
                if hoje <= d_vf <= hoje + timedelta(days=90):
                    if d_vf in dias:
                        dias[d_vf]["saidas"] += row['Total_Num']
                        dias[d_vf]["items"].append({
                            "tipo":  "saida",
                            "desc":  f"📥 {row.get('Fornecedor','')}",
                            "valor": row['Total_Num']
                        })

    # ── Construir série temporal ──────────────────────────────────
    resultado = []
    saldo_ac  = saldo_ini
    for i in range(91):
        d     = hoje + timedelta(days=i)
        ent   = dias[d]["entradas"]
        sai   = dias[d]["saidas"]
        saldo_ac = round(saldo_ac + ent - sai, 2)
        resultado.append({
            "data":     d,
            "entradas": ent,
            "saidas":   sai,
            "saldo":    saldo_ac,
            "items":    dias[d]["items"]
        })

    return resultado


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_cashflow_90d(cf_data: list):
    """
    Área + line chart cash flow 90 dias.
    Entradas, saídas e saldo acumulado.
    """
    datas   = [d['data'].strftime("%d/%m")  for d in cf_data]
    entradas = [d['entradas'] for d in cf_data]
    saidas   = [d['saidas']   for d in cf_data]
    saldo    = [d['saldo']    for d in cf_data]

    # Cores saldo (verde acima 0, vermelho abaixo)
    cor_saldo = ['#10B981' if s >= 0 else '#EF4444' for s in saldo]

    fig = go.Figure()

    # Zona perigo (saldo negativo)
    fig.add_hrect(
        y0=-999999999, y1=0,
        fillcolor='rgba(239,68,68,0.06)',
        line_width=0,
        annotation_text="Zona de risco",
        annotation_font_color="#EF4444",
        annotation_position="bottom right"
    )

    # Entradas
    fig.add_trace(go.Bar(
        name='Entradas',
        x=datas, y=entradas,
        marker_color='rgba(16,185,129,0.6)',
        hovertemplate='%{x}<br>Entrada: €%{y:,.2f}<extra></extra>'
    ))

    # Saídas (negativo para visualização)
    fig.add_trace(go.Bar(
        name='Saídas',
        x=datas, y=[-s for s in saidas],
        marker_color='rgba(239,68,68,0.6)',
        hovertemplate='%{x}<br>Saída: €%{customdata:,.2f}<extra></extra>',
        customdata=saidas
    ))

    # Saldo acumulado
    fig.add_trace(go.Scatter(
        name='Saldo Acumulado',
        x=datas, y=saldo,
        mode='lines',
        line={'color':'#3B82F6','width':3},
        fill='tozeroy',
        fillcolor='rgba(59,130,246,0.08)',
        hovertemplate='%{x}<br>Saldo: €%{y:,.2f}<extra></extra>',
        yaxis='y2'
    ))

    # Linha zero
    fig.add_hline(
        y=0, line_dash="solid",
        line_color="#334155", line_width=1,
        yref='y2'
    )

    fig.update_layout(
        title={
            'text':'Cash Flow Previsional — 90 Dias',
            'font':{'color':'#F1F5F9'}
        },
        barmode='relative',
        height=360,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'},
                'orientation':'h',
                'y':-0.15},
        xaxis={
            'gridcolor':'#334155',
            'tickfont':{'color':'#94A3B8','size':8},
            'tickangle':-45,
            # Mostrar só 1 em cada 7 dias
            'tickmode':'array',
            'tickvals':[datas[i] for i in range(0,91,7)],
        },
        yaxis={
            'gridcolor':'#334155',
            'tickfont':{'color':'#94A3B8'},
            'tickprefix':'€',
            'title':{'text':'Fluxo Diário',
                     'font':{'color':'#94A3B8'}}
        },
        yaxis2={
            'overlaying':'y',
            'side':'right',
            'tickprefix':'€',
            'tickfont':{'color':'#3B82F6'},
            'gridcolor':'rgba(59,130,246,0.1)',
            'title':{'text':'Saldo Acumulado',
                     'font':{'color':'#3B82F6'}}
        },
        margin=dict(t=40,b=60,l=60,r=60),
        hovermode='x unified'
    )
    return fig


def _grafico_cashflow_mensal(cf_data: list):
    """Stacked area entradas vs saídas por semana."""
    # Agregar por semana
    semanas  = {}
    for d in cf_data:
        # Número da semana
        iso = d['data'].isocalendar()
        chave = f"S{iso[1]:02d}"
        if chave not in semanas:
            semanas[chave] = {'e':0.0,'s':0.0,'saldo':0.0}
        semanas[chave]['e']     += d['entradas']
        semanas[chave]['s']     += d['saidas']
        semanas[chave]['saldo']  = d['saldo']

    labels   = list(semanas.keys())
    entradas = [v['e']     for v in semanas.values()]
    saidas   = [v['s']     for v in semanas.values()]
    saldos   = [v['saldo'] for v in semanas.values()]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Recebimentos', x=labels, y=entradas,
        marker_color='#10B981',
        hovertemplate='%{x}<br>€%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Pagamentos', x=labels, y=saidas,
        marker_color='#EF4444',
        hovertemplate='%{x}<br>€%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        name='Saldo', x=labels, y=saldos,
        mode='lines+markers',
        line={'color':'#3B82F6','width':2},
        marker={'size':7},
        hovertemplate='%{x}<br>Saldo: €%{y:,.2f}<extra></extra>',
        yaxis='y2'
    ))
    fig.update_layout(
        title={'text':'Resumo Semanal — Cash Flow',
               'font':{'color':'#F1F5F9'}},
        barmode='group',
        height=280,
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
                'tickprefix':'€',
                'tickfont':{'color':'#3B82F6'},
                'showgrid':False},
        margin=dict(t=40,b=20,l=10,r=60)
    )
    return fig


def _grafico_saldo_contas(contas_db):
    """Bar chart saldo por conta bancária."""
    if contas_db.empty:
        return None

    nomes  = contas_db.get('Nome', pd.Series()).tolist()
    saldos = pd.to_numeric(
        contas_db.get('Saldo',0), errors='coerce'
    ).fillna(0).tolist()
    cores  = ['#10B981' if s >= 0 else '#EF4444' for s in saldos]

    fig = go.Figure(go.Bar(
        x=nomes, y=saldos,
        marker_color=cores,
        text=[f"€{s:,.2f}" for s in saldos],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':10},
        hovertemplate='%{x}<br>Saldo: €%{y:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Saldo por Conta Bancária',
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


def _grafico_reconciliacao(movimentos_db):
    """Scatter reconciliação — conciliado vs pendente."""
    if movimentos_db.empty:
        return None

    conc = movimentos_db[
        movimentos_db.get('Estado','') == 'Conciliado'
    ] if 'Estado' in movimentos_db.columns else pd.DataFrame()
    pend = movimentos_db[
        movimentos_db.get('Estado','') != 'Conciliado'
    ] if 'Estado' in movimentos_db.columns else movimentos_db

    fig = go.Figure()
    if not conc.empty:
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(
                conc.get('Data',''), dayfirst=True, errors='coerce'
            ),
            y=pd.to_numeric(
                conc.get('Valor',0), errors='coerce'
            ).fillna(0),
            mode='markers',
            name='Conciliado',
            marker={'color':'#10B981','size':10,
                    'symbol':'circle'},
            hovertemplate='%{x|%d/%m/%Y}<br>€%{y:,.2f}<extra></extra>'
        ))
    if not pend.empty:
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(
                pend.get('Data',''), dayfirst=True, errors='coerce'
            ),
            y=pd.to_numeric(
                pend.get('Valor',0), errors='coerce'
            ).fillna(0),
            mode='markers',
            name='Por Conciliar',
            marker={'color':'#F59E0B','size':10,
                    'symbol':'diamond'},
            hovertemplate='%{x|%d/%m/%Y}<br>€%{y:,.2f}<extra></extra>'
        ))

    fig.update_layout(
        title={'text':'Movimentos Bancários — Reconciliação',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10)
    )
    return fig


def _grafico_fundo_maneio(fm_db):
    """Bar chart fundo maneio por obra."""
    if fm_db.empty:
        return None

    obras_fm = fm_db.get('Obra', pd.Series()).unique().tolist() \
               if 'Obra' in fm_db.columns else []
    if not obras_fm:
        return None

    adiantados = []
    gastos     = []
    saldos_fm  = []
    for ob in obras_fm:
        df_ob = fm_db[fm_db['Obra'] == ob] \
                if 'Obra' in fm_db.columns else fm_db
        ad = pd.to_numeric(
            df_ob.get('Adiantamento',0), errors='coerce'
        ).fillna(0).sum()
        ga = pd.to_numeric(
            df_ob.get('Gasto',0), errors='coerce'
        ).fillna(0).sum()
        adiantados.append(ad)
        gastos.append(ga)
        saldos_fm.append(round(ad - ga, 2))

    obras_short = [o[:15] for o in obras_fm]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Adiantado', x=obras_short, y=adiantados,
        marker_color='rgba(59,130,246,0.5)',
        hovertemplate='%{x}<br>Adiantado: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Gasto', x=obras_short, y=gastos,
        marker_color='#EF4444',
        hovertemplate='%{x}<br>Gasto: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        name='Saldo', x=obras_short, y=saldos_fm,
        mode='markers+text',
        text=[f"€{s:,.0f}" for s in saldos_fm],
        textposition='top center',
        textfont={'color':'#F1F5F9','size':9},
        marker={'color':'#10B981','size':10},
        hovertemplate='%{x}<br>Saldo: €%{y:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Fundo de Maneio por Obra',
               'font':{'color':'#F1F5F9'}},
        barmode='overlay',
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10)
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PREVISÃO IA
# ─────────────────────────────────────────────────────────────────

def _previsao_cashflow_ia(cf_data: list,
                           saldo_atual: float,
                           custos_fixos_mes: float) -> str:
    """Gera previsão inteligente do cash flow com IA."""
    try:
        import anthropic, json
        api_key = os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return "❌ API key não configurada."

        client = anthropic.Anthropic(api_key=api_key)

        # Resumo para IA
        meses_res = {}
        for d in cf_data:
            mes_k = d['data'].strftime("%Y-%m")
            if mes_k not in meses_res:
                meses_res[mes_k] = {'e':0.0,'s':0.0}
            meses_res[mes_k]['e'] += d['entradas']
            meses_res[mes_k]['s'] += d['saidas']

        saldo_min = min(d['saldo'] for d in cf_data)
        saldo_max = max(d['saldo'] for d in cf_data)
        dias_neg  = sum(1 for d in cf_data if d['saldo'] < 0)
        data_neg  = next(
            (d['data'].strftime("%d/%m/%Y")
             for d in cf_data if d['saldo'] < 0),
            None
        )

        contexto = {
            "saldo_atual":          round(saldo_atual, 2),
            "custos_fixos_mes":     round(custos_fixos_mes, 2),
            "autonomia_meses":      round(
                saldo_atual / custos_fixos_mes, 1
            ) if custos_fixos_mes > 0 else 99,
            "saldo_min_90d":        round(saldo_min, 2),
            "saldo_max_90d":        round(saldo_max, 2),
            "dias_saldo_negativo":  dias_neg,
            "primeira_data_negativa": data_neg,
            "resumo_mensal":        {
                k: {"recebimentos": round(v['e'],2),
                    "pagamentos":   round(v['s'],2),
                    "saldo_mes":    round(v['e']-v['s'],2)}
                for k, v in meses_res.items()
            }
        }

        prompt = f"""Analisa o cash flow desta empresa portuguesa 
de instrumentação industrial (CPS) para os próximos 90 dias.

Dados: {json.dumps(contexto, ensure_ascii=False)}

Fornece uma análise curta com:
1. Situação atual em 1 frase
2. Principal risco identificado
3. Mês mais crítico e porquê
4. 2 ações concretas e imediatas recomendadas
5. Se há risco de ruptura de tesouraria — quando e valor necessário

Responde em português, tom profissional de CFO sénior, máximo 5 parágrafos."""

        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role":"user","content":prompt}]
        )
        return resp.content[0].text

    except Exception as e:
        return f"❌ Erro: {e}"


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_tesouraria(obras_db, registos_db,
                           faturas_db, diarias_pag_db, *_):
    """Módulo Tesouraria & Cash Flow."""

    # ── Carregar dados ────────────────────────────────────────────
    contas_db   = _load("contas_bancarias.csv", [
        "ID","Nome","Banco","IBAN","Tipo","Saldo",
        "Data_Saldo","Moeda","Ativa"
    ])
    movimentos_db = _load("movimentos_bancarios.csv", [
        "ID","Data","Conta","Descricao","Valor",
        "Tipo","Estado","Fatura_ID","Categoria"
    ])
    faturas_cli = _load("faturas_clientes.csv", [
        "ID","Numero","Data_Emissao","Data_Vencimento",
        "Cliente","Obra","Total","Estado"
    ])
    rh_db       = _load("colaboradores_rh.csv",
                        ["Nome","Salario_Base"])
    renting_db  = _load("renting_contratos.csv",
                        ["ID","Matricula","Valor_Mensal",
                         "Data_Fim","Estado"])
    fm_db       = _load("fundo_maneio.csv", [
        "ID","Obra","Responsavel","Data","Descricao",
        "Adiantamento","Gasto","Comprovativo_b64","Estado"
    ])

    try:
        from mod_admin_diarias import _get_config_empresa
        empresa = _get_config_empresa()
    except:
        empresa = {
            "nome":"Correia Plácido e Sousa, Lda.",
            "nif":"517182718","iban":"","bic":"MPIOPTPL"
        }

    user_nome = st.session_state.get('user','Admin')
    hoje      = date.today()

    # ── Calcular cash flow ────────────────────────────────────────
    cf_data = _calcular_cashflow_90d(
        faturas_cli, pd.DataFrame(),
        rh_db, renting_db, diarias_pag_db, contas_db
    )

    # Métricas base
    saldo_atual   = pd.to_numeric(
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
    autonomia_meses  = round(
        saldo_atual / custos_fixos_mes, 1
    ) if custos_fixos_mes > 0 else 99.0

    # Cash flow próximos 30 dias
    cf_30 = cf_data[:30]
    ent_30 = sum(d['entradas'] for d in cf_30)
    sai_30 = sum(d['saidas']   for d in cf_30)
    sal_30 = cf_30[-1]['saldo'] if cf_30 else saldo_atual

    # Dias com saldo negativo
    dias_neg = sum(1 for d in cf_data if d['saldo'] < 0)
    data_primeiro_neg = next(
        (d['data'].strftime("%d/%m/%Y")
         for d in cf_data if d['saldo'] < 0),
        None
    )

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .conta-card {
        background:#1E293B; border-radius:12px;
        padding:16px; margin-bottom:10px;
        border-left:4px solid #3B82F6;
    }
    .mv-linha {
        display:flex; justify-content:space-between;
        padding:6px 0; border-bottom:1px solid #0F172A;
    }
    .alerta-cf {
        border-radius:10px; padding:12px 16px;
        margin-bottom:8px; border-left:4px solid;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────
    cor_aut = "#10B981" if autonomia_meses >= 3 \
              else "#F59E0B" if autonomia_meses >= 1 \
              else "#EF4444"
    cor_cf  = "#10B981" if sal_30 >= 0 else "#EF4444"
    cor_neg = "#10B981" if dias_neg == 0 else "#EF4444"

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        st.metric("🏦 Saldo Atual",
                   f"€{saldo_atual:,.2f}")
    with c2:
        st.metric("📥 A Receber 30d",
                   f"€{ent_30:,.2f}")
    with c3:
        st.metric("📤 A Pagar 30d",
                   f"€{sai_30:,.2f}")
    with c4:
        st.metric("💵 Saldo Prev. 30d",
                   f"€{sal_30:,.2f}")
    with c5:
        st.metric("📅 Autonomia",
                   f"{autonomia_meses:.1f} meses")

    # Alerta saldo negativo
    if dias_neg > 0:
        st.error(
            f"🆘 **ALERTA:** Saldo previsto negativo em "
            f"**{dias_neg} dia(s)** nos próximos 90 dias. "
            f"Primeiro evento crítico: **{data_primeiro_neg}**"
        )
    elif autonomia_meses < 1:
        st.error(
            "🔴 Autonomia inferior a 1 mês — "
            "ativar plano de contingência!"
        )
    elif autonomia_meses < 3:
        st.warning(
            f"⚠️ Autonomia de {autonomia_meses:.1f} meses — "
            "monitorizar de perto."
        )
    else:
        st.success(
            f"✅ Tesouraria saudável — "
            f"{autonomia_meses:.1f} meses de autonomia."
        )

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_cf, t_contas, t_rec,
     t_fm, t_ia) = st.tabs([
        "💵 Cash Flow 90 Dias",
        "🏦 Contas Bancárias",
        "🔄 Reconciliação Bancária",
        "💼 Fundo de Maneio",
        "🤖 Previsão IA",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — CASH FLOW 90 DIAS
    # ════════════════════════════════════════════════════════════════
    with t_cf:
        st.markdown("### 💵 Cash Flow Previsional — 90 Dias")

        # Gráfico principal
        st.plotly_chart(
            _grafico_cashflow_90d(cf_data),
            use_container_width=True
        )

        # Gráfico semanal
        st.plotly_chart(
            _grafico_cashflow_mensal(cf_data),
            use_container_width=True
        )

        # Resumo por período
        st.markdown("#### 📊 Resumo por Período")
        col_30, col_60, col_90 = st.columns(3)

        for col, dias_n, label in [
            (col_30, 30, "30 dias"),
            (col_60, 60, "60 dias"),
            (col_90, 90, "90 dias"),
        ]:
            cf_p  = cf_data[:dias_n]
            e_p   = sum(d['entradas'] for d in cf_p)
            s_p   = sum(d['saidas']   for d in cf_p)
            sal_p = cf_p[-1]['saldo'] if cf_p else saldo_atual
            cor_p = "#10B981" if sal_p >= 0 else "#EF4444"

            with col:
                st.markdown(
                    f"<div style='background:#1E293B;"
                    f"border-radius:10px;padding:14px;"
                    f"border-top:3px solid {cor_p};'>"
                    f"<p style='color:#94A3B8;"
                    f"font-size:0.75rem;font-weight:700;"
                    f"text-transform:uppercase;margin:0 0 8px;'>"
                    f"Próximos {label}</p>"
                    f"<div class='mv-linha'>"
                    f"<small style='color:#64748B;'>Entradas</small>"
                    f"<b style='color:#10B981;'>"
                    f"€{e_p:,.2f}</b></div>"
                    f"<div class='mv-linha'>"
                    f"<small style='color:#64748B;'>Saídas</small>"
                    f"<b style='color:#EF4444;'>"
                    f"€{s_p:,.2f}</b></div>"
                    f"<div style='display:flex;"
                    f"justify-content:space-between;"
                    f"padding-top:8px;border-top:"
                    f"1px solid #334155;margin-top:4px;'>"
                    f"<b style='color:#F1F5F9;'>Saldo</b>"
                    f"<b style='color:{cor_p};"
                    f"font-size:1.05rem;'>€{sal_p:,.2f}</b>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

        # Eventos críticos
        st.markdown("---")
        st.markdown("#### ⚡ Eventos Críticos Previstos")

        eventos_crit = [
            d for d in cf_data
            if d['entradas'] > 0 or d['saidas'] > 0
        ][:20]  # top 20 eventos

        if not eventos_crit:
            st.info("📋 Sem eventos financeiros previstos.")
        else:
            for ev in eventos_crit:
                for item in ev['items']:
                    cor_it = "#10B981" if item['tipo'] == 'entrada' \
                             else "#EF4444"
                    ic_it  = "📥" if item['tipo'] == 'entrada' \
                             else "📤"
                    d_str  = ev['data'].strftime("%d/%m/%Y")
                    dias_r = (ev['data'] - hoje).days

                    st.markdown(
                        f"<div class='alerta-cf' "
                        f"style='background:{cor_it}0D;"
                        f"border-left-color:{cor_it};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<span style='color:{cor_it};"
                        f"font-size:0.85rem;'>"
                        f"{ic_it} {item['desc']}</span>"
                        f"<span style='color:#64748B;"
                        f"font-size:0.8rem;'>"
                        f"{d_str} "
                        f"({'hoje' if dias_r==0 else f'em {dias_r}d'})"
                        f"</span>"
                        f"</div>"
                        f"<b style='color:{cor_it};"
                        f"font-size:1rem;'>"
                        f"{'+ ' if item['tipo']=='entrada' else '- '}"
                        f"€{item['valor']:,.2f}</b>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        # Export CSV
        st.markdown("---")
        df_cf_exp = pd.DataFrame([{
            "Data":     d['data'].strftime("%d/%m/%Y"),
            "Entradas": d['entradas'],
            "Saidas":   d['saidas'],
            "Saldo":    d['saldo']
        } for d in cf_data])

        csv_cf = df_cf_exp.to_csv(
            index=False, encoding='utf-8-sig'
        )
        st.download_button(
            "📥 Exportar Cash Flow CSV",
            data=csv_cf.encode('utf-8-sig'),
            file_name=(
                f"cashflow_90d_"
                f"{hoje.strftime('%Y%m%d')}.csv"
            ),
            mime="text/csv",
            key="dl_cf_csv"
        )

    # ════════════════════════════════════════════════════════════════
    # TAB — CONTAS BANCÁRIAS
    # ════════════════════════════════════════════════════════════════
    with t_contas:
        st.markdown("### 🏦 Contas Bancárias")

        col_cform, col_clista = st.columns([1, 2])

        with col_cform:
            st.markdown("#### ➕ Registar Conta")
            with st.form("form_conta"):
                c_nome  = st.text_input(
                    "Nome da Conta *",
                    key="ct_nome",
                    placeholder="Ex: Conta Corrente Principal"
                )
                c_banco = st.selectbox(
                    "Banco *",
                    ["Montepio","CGD","BCP","Santander",
                     "Novo Banco","BPI","EuroBic","Outro"],
                    key="ct_banco"
                )
                c_iban  = st.text_input(
                    "IBAN", key="ct_iban",
                    placeholder="PT50..."
                )
                c_tipo  = st.selectbox(
                    "Tipo",
                    ["Conta Corrente","Conta Poupança",
                     "Conta Ordenado","Conta Projeto"],
                    key="ct_tipo"
                )
                c_saldo = st.number_input(
                    "Saldo Atual (€)",
                    min_value=-999999.0,
                    value=0.0, step=100.0,
                    key="ct_saldo"
                )
                c_data  = st.date_input(
                    "Data do Saldo",
                    value=hoje, key="ct_data"
                )

                if st.form_submit_button(
                    "💾 Guardar Conta",
                    use_container_width=True, type="primary"
                ):
                    if not c_nome.strip():
                        st.error("❌ Nome obrigatório.")
                    else:
                        nova_c = pd.DataFrame([{
                            "ID":         str(uuid.uuid4())[:8].upper(),
                            "Nome":       c_nome.strip(),
                            "Banco":      c_banco,
                            "IBAN":       c_iban.strip(),
                            "Tipo":       c_tipo,
                            "Saldo":      c_saldo,
                            "Data_Saldo": c_data.strftime("%d/%m/%Y"),
                            "Moeda":      "EUR",
                            "Ativa":      "Sim"
                        }])
                        upd_c = pd.concat(
                            [contas_db, nova_c], ignore_index=True
                        ) if not contas_db.empty else nova_c
                        save_db(upd_c, "contas_bancarias.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="CRIAR_CONTA_BANCARIA",
                            tabela="contas_bancarias.csv",
                            registro_id=nova_c['ID'].iloc[0],
                            detalhes=f"{c_nome} | {c_banco} | "
                                     f"€{c_saldo}",
                            ip=""
                        )
                        inv()
                        st.success(f"✅ Conta {c_nome} guardada!")
                        st.rerun()

        with col_clista:
            st.markdown("#### 📊 Posição Bancária")

            # Gráfico saldo
            fig_sal = _grafico_saldo_contas(contas_db)
            if fig_sal:
                st.plotly_chart(
                    fig_sal, use_container_width=True
                )

            if contas_db.empty:
                st.info("📋 Sem contas registadas.")
            else:
                total_bancos = pd.to_numeric(
                    contas_db.get('Saldo', pd.Series()),
                    errors='coerce'
                ).fillna(0).sum()
                st.metric(
                    "💰 Posição Total",
                    f"€{total_bancos:,.2f}"
                )

                for _, conta in contas_db.iterrows():
                    ct_id   = conta.get('ID','')
                    saldo_c = float(conta.get('Saldo',0) or 0)
                    cor_s   = "#10B981" if saldo_c >= 0 \
                              else "#EF4444"

                    st.markdown(
                        f"<div class='conta-card'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;'>"
                        f"🏦 {conta.get('Nome','')}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"{conta.get('Banco','')} · "
                        f"{conta.get('Tipo','')} · "
                        f"IBAN: {conta.get('IBAN','N/D')[:20]}"
                        f"</small><br>"
                        f"<small style='color:#475569;'>"
                        f"Atualizado: "
                        f"{conta.get('Data_Saldo','')}</small>"
                        f"</div>"
                        f"<b style='color:{cor_s};"
                        f"font-size:1.4rem;'>"
                        f"€{saldo_c:,.2f}</b>"
                        f"</div></div>",
                        unsafe_allow_html=True
                    )

                    # Atualizar saldo
                    col_sa, col_sb = st.columns([3,1])
                    with col_sa:
                        novo_sal = st.number_input(
                            "Novo saldo",
                            value=saldo_c,
                            step=100.0,
                            key=f"sal_upd_{ct_id}",
                            label_visibility="collapsed"
                        )
                    with col_sb:
                        if st.button(
                            "💾",
                            key=f"sal_btn_{ct_id}",
                            use_container_width=True,
                            help="Atualizar saldo"
                        ):
                            contas_db.loc[
                                contas_db['ID'] == ct_id,
                                ['Saldo','Data_Saldo']
                            ] = [novo_sal,
                                 hoje.strftime("%d/%m/%Y")]
                            save_db(contas_db, "contas_bancarias.csv")
                            inv(); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — RECONCILIAÇÃO BANCÁRIA
    # ════════════════════════════════════════════════════════════════
    with t_rec:
        st.markdown("### 🔄 Reconciliação Bancária")
        st.info(
            "Faz upload do extrato bancário (CSV/OFX) ou "
            "regista movimentos manualmente. "
            "O sistema compara com os registos da app."
        )

        col_rec1, col_rec2 = st.columns([1, 2])

        with col_rec1:
            st.markdown("#### 📤 Upload Extrato")

            upload_ext = st.file_uploader(
                "Extrato bancário (CSV)",
                type=["csv","txt"],
                key="ext_upload"
            )

            if upload_ext:
                with st.spinner("A processar extrato..."):
                    try:
                        df_ext = pd.read_csv(
                            upload_ext,
                            encoding='utf-8-sig',
                            sep=None,
                            engine='python',
                            on_bad_lines='skip'
                        )
                        st.success(
                            f"✅ {len(df_ext)} movimentos carregados!"
                        )
                        st.dataframe(
                            df_ext.head(10),
                            use_container_width=True
                        )

                        # Mapeamento de colunas
                        colunas = df_ext.columns.tolist()
                        col_data_ext = st.selectbox(
                            "Coluna Data",
                            colunas, key="ext_col_data"
                        )
                        col_desc_ext = st.selectbox(
                            "Coluna Descrição",
                            colunas, key="ext_col_desc"
                        )
                        col_val_ext = st.selectbox(
                            "Coluna Valor",
                            colunas, key="ext_col_val"
                        )

                        if st.button(
                            "🔄 Importar Movimentos",
                            key="btn_import_ext",
                            type="primary",
                            use_container_width=True
                        ):
                            conta_sel = ""
                            if not contas_db.empty:
                                conta_sel = st.session_state.get(
                                    'rec_conta_sel',
                                    contas_db['Nome'].iloc[0]
                                )
                            novos_mv  = []
                            for _, row_ext in df_ext.iterrows():
                                val_mv = 0.0
                                try:
                                    val_mv = float(
                                        str(row_ext[col_val_ext])
                                        .replace(',','.')
                                        .replace(' ','')
                                    )
                                except:
                                    pass
                                novos_mv.append({
                                    "ID":       str(uuid.uuid4())[:8].upper(),
                                    "Data":     str(row_ext.get(col_data_ext,'')),
                                    "Conta":    conta_sel,
                                    "Descricao":str(row_ext.get(col_desc_ext,'')),
                                    "Valor":    val_mv,
                                    "Tipo":     "Crédito" if val_mv>=0
                                                else "Débito",
                                    "Estado":   "Por Conciliar",
                                    "Fatura_ID":"",
                                    "Categoria":""
                                })
                            df_novos = pd.DataFrame(novos_mv)
                            upd_mv   = pd.concat(
                                [movimentos_db, df_novos],
                                ignore_index=True
                            ) if not movimentos_db.empty else df_novos
                            save_db(upd_mv, "movimentos_bancarios.csv")
                            inv()
                            st.success(
                                f"✅ {len(novos_mv)} movimentos importados!"
                            )
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao ler extrato: {e}")

            st.markdown("---")
            st.markdown("#### ➕ Registo Manual")

            with st.form("form_movimento"):
                if not contas_db.empty:
                    ct_sel_mv = st.selectbox(
                        "Conta *",
                        contas_db['Nome'].tolist(),
                        key="mv_conta"
                    )
                else:
                    ct_sel_mv = st.text_input(
                        "Conta *", key="mv_conta_txt"
                    )
                mv_data  = st.date_input(
                    "Data", value=hoje, key="mv_data"
                )
                mv_desc  = st.text_input(
                    "Descrição *", key="mv_desc"
                )
                mv_val   = st.number_input(
                    "Valor (€) — positivo=entrada, "
                    "negativo=saída",
                    step=0.01, key="mv_val"
                )
                mv_cat   = st.selectbox(
                    "Categoria",
                    ["Recebimento Cliente","Pagamento Fornecedor",
                     "Salários","Renting","Impostos",
                     "Transferência","Outro"],
                    key="mv_cat"
                )

                if st.form_submit_button(
                    "💾 Registar",
                    use_container_width=True, type="primary"
                ):
                    if not mv_desc.strip():
                        st.error("❌ Descrição obrigatória.")
                    else:
                        novo_mv = pd.DataFrame([{
                            "ID":       str(uuid.uuid4())[:8].upper(),
                            "Data":     mv_data.strftime("%d/%m/%Y"),
                            "Conta":    ct_sel_mv,
                            "Descricao":mv_desc.strip(),
                            "Valor":    mv_val,
                            "Tipo":     "Crédito" if mv_val>=0
                                        else "Débito",
                            "Estado":   "Por Conciliar",
                            "Fatura_ID":"",
                            "Categoria":mv_cat
                        }])
                        upd_mv2 = pd.concat(
                            [movimentos_db, novo_mv],
                            ignore_index=True
                        ) if not movimentos_db.empty else novo_mv
                        save_db(upd_mv2, "movimentos_bancarios.csv")
                        inv()
                        st.success("✅ Movimento registado!")
                        st.rerun()

        with col_rec2:
            st.markdown("#### 📊 Movimentos por Conciliar")

            # Gráfico reconciliação
            fig_rec = _grafico_reconciliacao(movimentos_db)
            if fig_rec:
                st.plotly_chart(
                    fig_rec, use_container_width=True
                )

            if movimentos_db.empty:
                st.info("📋 Sem movimentos registados.")
            else:
                # KPIs reconciliação
                total_mv  = len(movimentos_db)
                concil_mv = len(movimentos_db[
                    movimentos_db.get('Estado','') == 'Conciliado'
                ]) if 'Estado' in movimentos_db.columns else 0
                pend_mv   = total_mv - concil_mv

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("📋 Total",        total_mv)
                with c2:
                    st.metric("✅ Conciliados",   concil_mv)
                with c3:
                    st.metric("🟡 Pendentes",     pend_mv)

                # Lista movimentos por conciliar
                mv_pend = movimentos_db[
                    movimentos_db.get('Estado','') != 'Conciliado'
                ] if 'Estado' in movimentos_db.columns \
                  else movimentos_db

                if not mv_pend.empty:
                    for _, mv in mv_pend.sort_values(
                        'Data', ascending=False
                    ).head(20).iterrows():
                        mv_id  = mv.get('ID','')
                        val_mv = float(mv.get('Valor',0) or 0)
                        cor_mv = "#10B981" if val_mv >= 0 \
                                 else "#EF4444"
                        ic_mv  = "📥" if val_mv >= 0 else "📤"

                        col_mi, col_mc = st.columns([5,1])
                        with col_mi:
                            st.markdown(
                                f"<div style='background:#1E293B;"
                                f"border-radius:8px;padding:10px;"
                                f"margin-bottom:4px;"
                                f"border-left:3px solid {cor_mv};'>"
                                f"{ic_mv} "
                                f"<b style='color:#F1F5F9;"
                                f"font-size:0.85rem;'>"
                                f"{mv.get('Descricao','')[:40]}</b>"
                                f"<span style='float:right;"
                                f"color:{cor_mv};font-weight:700;'>"
                                f"{'+ ' if val_mv>=0 else '- '}"
                                f"€{abs(val_mv):,.2f}</span><br>"
                                f"<small style='color:#64748B;'>"
                                f"{mv.get('Data','')} · "
                                f"{mv.get('Conta','')} · "
                                f"{mv.get('Categoria','')}"
                                f"</small></div>",
                                unsafe_allow_html=True
                            )
                        with col_mc:
                            if st.button(
                                "✅",
                                key=f"concil_{mv_id}",
                                use_container_width=True,
                                help="Marcar como conciliado"
                            ):
                                movimentos_db.loc[
                                    movimentos_db['ID'] == mv_id,
                                    'Estado'
                                ] = 'Conciliado'
                                save_db(
                                    movimentos_db,
                                    "movimentos_bancarios.csv"
                                )
                                inv(); st.rerun()

                # Export
                csv_mv = movimentos_db.drop(
                    columns=['Fatura_ID'], errors='ignore'
                ).to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "📥 Exportar Movimentos",
                    data=csv_mv.encode('utf-8-sig'),
                    file_name="movimentos_bancarios.csv",
                    mime="text/csv",
                    key="dl_mv"
                )

    # ════════════════════════════════════════════════════════════════
    # TAB — FUNDO DE MANEIO
    # ════════════════════════════════════════════════════════════════
    with t_fm:
        st.markdown("### 💼 Fundo de Maneio por Obra")
        st.info(
            "Dinheiro adiantado ao chefe de equipa para "
            "despesas em obra. "
            "Cada gasto requer comprovativo. "
            "Acerto semanal automático."
        )

        # Gráfico
        fig_fm = _grafico_fundo_maneio(fm_db)
        if fig_fm:
            st.plotly_chart(fig_fm, use_container_width=True)

        col_fm1, col_fm2 = st.columns([1, 2])

        with col_fm1:
            obras_ativas_fm = []
            if not obras_db.empty and 'Ativa' in obras_db.columns:
                obras_ativas_fm = obras_db[
                    obras_db['Ativa'] == 'Ativa'
                ]['Obra'].tolist()

            st.markdown("#### ➕ Adiantamento")
            with st.form("form_fm_adiant"):
                fm_obra  = st.selectbox(
                    "Obra *",
                    obras_ativas_fm if obras_ativas_fm else [""],
                    key="fm_obra"
                )
                fm_resp  = st.text_input(
                    "Responsável *", key="fm_resp"
                )
                fm_adiant = st.number_input(
                    "Valor Adiantado (€) *",
                    min_value=0.0, step=50.0, key="fm_adiant"
                )
                fm_data  = st.date_input(
                    "Data", value=hoje, key="fm_data"
                )
                fm_desc  = st.text_input(
                    "Descrição", key="fm_desc",
                    placeholder="Ex: Fundo maneio semana 20"
                )

                if st.form_submit_button(
                    "💰 Registar Adiantamento",
                    use_container_width=True, type="primary"
                ):
                    if not fm_resp.strip() or fm_adiant <= 0:
                        st.error("❌ Responsável e valor obrigatórios.")
                    else:
                        novo_fm = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Obra":         fm_obra,
                            "Responsavel":  fm_resp.strip(),
                            "Data":         fm_data.strftime("%d/%m/%Y"),
                            "Descricao":    fm_desc.strip(),
                            "Adiantamento": fm_adiant,
                            "Gasto":        0,
                            "Comprovativo_b64":"",
                            "Estado":       "Em Aberto"
                        }])
                        upd_fm = pd.concat(
                            [fm_db, novo_fm], ignore_index=True
                        ) if not fm_db.empty else novo_fm
                        save_db(upd_fm, "fundo_maneio.csv")
                        inv()
                        st.success(
                            f"✅ Adiantamento €{fm_adiant:.2f} "
                            f"para {fm_resp}!"
                        )
                        st.rerun()

            st.markdown("---")
            st.markdown("#### 🧾 Registar Gasto")
            with st.form("form_fm_gasto"):
                fm_id_sel = ""
                if not fm_db.empty:
                    em_aberto = fm_db[
                        fm_db.get('Estado','') == 'Em Aberto'
                    ] if 'Estado' in fm_db.columns else fm_db
                    if not em_aberto.empty:
                        opt = em_aberto.apply(
                            lambda r: f"{r.get('Obra','')} — "
                                      f"{r.get('Responsavel','')} — "
                                      f"€{float(r.get('Adiantamento',0) or 0):,.2f}",
                            axis=1
                        ).tolist()
                        fm_sel_str = st.selectbox(
                            "Fundo", opt, key="fm_gasto_sel"
                        )
                        # Encontrar ID
                        idx_fm = opt.index(fm_sel_str) \
                                 if fm_sel_str in opt else 0
                        fm_id_sel = em_aberto.iloc[idx_fm].get('ID','') \
                                    if not em_aberto.empty else ""

                fm_gasto_val = st.number_input(
                    "Valor Gasto (€) *",
                    min_value=0.0, step=5.0, key="fm_gasto_val"
                )
                fm_gasto_desc = st.text_input(
                    "Descrição *", key="fm_gasto_desc"
                )
                fm_comp = st.file_uploader(
                    "Comprovativo *",
                    type=["jpg","jpeg","png","pdf"],
                    key="fm_comp"
                )

                if st.form_submit_button(
                    "🧾 Registar Gasto",
                    use_container_width=True, type="primary"
                ):
                    if fm_gasto_val <= 0 or not fm_gasto_desc.strip():
                        st.error("❌ Valor e descrição obrigatórios.")
                    elif not fm_comp:
                        st.error(
                            "❌ Comprovativo obrigatório "
                            "para registar gasto."
                        )
                    else:
                        comp_b64 = base64.b64encode(
                            fm_comp.read()
                        ).decode()
                        if fm_id_sel:
                            # Acumular gasto
                            gasto_atual = float(
                                fm_db.loc[
                                    fm_db['ID'] == fm_id_sel,
                                    'Gasto'
                                ].values[0] or 0
                            )
                            fm_db.loc[
                                fm_db['ID'] == fm_id_sel,
                                'Gasto'
                            ] = gasto_atual + fm_gasto_val
                            save_db(fm_db, "fundo_maneio.csv")
                            inv()
                            st.success(
                                f"✅ Gasto €{fm_gasto_val:.2f} "
                                f"registado com comprovativo!"
                            )
                            st.rerun()

        with col_fm2:
            st.markdown("#### 📋 Fundos em Aberto")

            if fm_db.empty:
                st.info("📋 Sem fundos de maneio registados.")
            else:
                em_aberto_show = fm_db[
                    fm_db.get('Estado','') == 'Em Aberto'
                ] if 'Estado' in fm_db.columns else fm_db

                if em_aberto_show.empty:
                    st.success("✅ Todos os fundos acertados!")
                else:
                    for _, fm_row in em_aberto_show.iterrows():
                        fm_rid   = fm_row.get('ID','')
                        adiant   = float(fm_row.get('Adiantamento',0) or 0)
                        gasto    = float(fm_row.get('Gasto',0) or 0)
                        saldo_fm = round(adiant - gasto, 2)
                        pct_gst  = round(gasto/adiant*100,0) \
                                   if adiant > 0 else 0
                        cor_fm   = "#10B981" if saldo_fm >= 0 \
                                   else "#EF4444"

                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:12px;padding:14px;"
                            f"margin-bottom:10px;"
                            f"border-left:4px solid {cor_fm};'>"
                            f"<b style='color:#F1F5F9;'>"
                            f"💼 {fm_row.get('Obra','')} — "
                            f"{fm_row.get('Responsavel','')}</b>"
                            f"<span style='float:right;"
                            f"color:{cor_fm};font-weight:700;'>"
                            f"Saldo: €{saldo_fm:,.2f}</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"Adiantado: €{adiant:,.2f} · "
                            f"Gasto: €{gasto:,.2f} · "
                            f"{fm_row.get('Data','')}"
                            f"</small>"
                            f"<div style='background:#0F172A;"
                            f"border-radius:3px;height:6px;"
                            f"margin:8px 0 4px;'>"
                            f"<div style='background:{cor_fm};"
                            f"width:{min(pct_gst,100):.0f}%;"
                            f"height:6px;border-radius:3px;'>"
                            f"</div></div>"
                            f"<small style='color:#475569;'>"
                            f"{pct_gst:.0f}% utilizado"
                            f"</small></div>",
                            unsafe_allow_html=True
                        )

                        col_fma, col_fmb = st.columns(2)
                        with col_fma:
                            if st.button(
                                "✅ Acertar / Fechar",
                                key=f"fm_fechar_{fm_rid}",
                                use_container_width=True
                            ):
                                fm_db.loc[
                                    fm_db['ID'] == fm_rid,
                                    'Estado'
                                ] = 'Acertado'
                                save_db(fm_db, "fundo_maneio.csv")
                                inv()
                                st.success("✅ Fundo acertado!")
                                st.rerun()
                        with col_fmb:
                            st.markdown(
                                f"<small style='color:"
                                f"{'#10B981' if saldo_fm >= 0 else '#EF4444'};'>"
                                f"{'Troco a devolver' if saldo_fm > 0 else 'Em dívida'}: "
                                f"€{abs(saldo_fm):,.2f}</small>",
                                unsafe_allow_html=True
                            )

    # ════════════════════════════════════════════════════════════════
    # TAB — PREVISÃO IA
    # ════════════════════════════════════════════════════════════════
    with t_ia:
        st.markdown("### 🤖 Previsão Inteligente de Tesouraria")
        st.info(
            "A IA analisa o cash flow previsto, os padrões "
            "históricos e sugere ações preventivas."
        )

        # Indicadores de saúde
        st.markdown("#### 🩺 Diagnóstico Atual")

        indicadores = [
            ("🏦 Saldo Atual",
             f"€{saldo_atual:,.2f}",
             "#10B981" if saldo_atual > 0 else "#EF4444"),
            ("📅 Autonomia Financeira",
             f"{autonomia_meses:.1f} meses",
             "#10B981" if autonomia_meses >= 3
             else "#F59E0B" if autonomia_meses >= 1
             else "#EF4444"),
            ("📉 Dias Saldo Negativo (90d)",
             str(dias_neg),
             "#10B981" if dias_neg == 0 else "#EF4444"),
            ("⚠️ Primeira Data Crítica",
             data_primeiro_neg or "Nenhuma",
             "#10B981" if not data_primeiro_neg else "#EF4444"),
            ("💸 Custos Fixos/Mês",
             f"€{custos_fixos_mes:,.2f}",
             "#94A3B8"),
        ]

        cols_ind = st.columns(len(indicadores))
        for col_i, (label, val, cor_i) in zip(
            cols_ind, indicadores
        ):
            with col_i:
                st.markdown(
                    f"<div style='background:#1E293B;"
                    f"border-radius:10px;padding:12px;"
                    f"text-align:center;"
                    f"border-top:3px solid {cor_i};'>"
                    f"<small style='color:#64748B;"
                    f"font-size:0.7rem;font-weight:700;"
                    f"text-transform:uppercase;'>"
                    f"{label}</small><br>"
                    f"<b style='color:{cor_i};"
                    f"font-size:1.05rem;'>{val}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # Sugestões rápidas
        sugestoes_ia = [
            "Quando é o próximo momento crítico de cash flow?",
            "Quanto preciso de financiamento e quando?",
            "Como posso melhorar a minha tesouraria?",
            "Qual cliente devo priorizar para receber?",
            "Devo pedir uma linha de crédito agora?",
        ]
        st.markdown(
            "<p style='color:#475569;font-size:0.75rem;"
            "margin:0 0 6px;'>💡 Sugestões:</p>",
            unsafe_allow_html=True
        )
        cols_sug = st.columns(len(sugestoes_ia))
        for i, (col_sg, sug) in enumerate(
            zip(cols_sug, sugestoes_ia)
        ):
            with col_sg:
                if st.button(
                    sug[:30]+"...",
                    key=f"cf_sug_{i}",
                    use_container_width=True
                ):
                    st.session_state['cf_ia_input'] = sug

        pergunta_cf = st.text_input(
            "💬 Pergunta à IA sobre Tesouraria",
            value=st.session_state.get('cf_ia_input',''),
            placeholder="Ex: Se o cliente BASF atrasar 30 dias, "
                        "quando fico sem dinheiro?",
            key="cf_ia_txt",
            label_visibility="collapsed"
        )

        col_ia1, col_ia2 = st.columns([4,1])
        with col_ia2:
            analisar = st.button(
                "🤖 Analisar",
                type="primary",
                use_container_width=True,
                key="btn_cf_ia"
            )

        # Análise automática sempre visível
        with st.expander(
            "📊 Análise Automática de Tesouraria",
            expanded=True
        ):
            if st.button(
                "🔄 Gerar Análise Completa",
                key="btn_analise_auto",
                use_container_width=True
            ):
                with st.spinner(
                    "🤖 A analisar cash flow..."
                ):
                    analise = _previsao_cashflow_ia(
                        cf_data, saldo_atual, custos_fixos_mes
                    )
                st.session_state['cf_analise'] = analise

            if st.session_state.get('cf_analise'):
                st.markdown(
                    f"<div style='background:rgba(59,130,246,0.1);"
                    f"border:1px solid #3B82F6;"
                    f"border-radius:12px;padding:16px;"
                    f"color:#E2E8F0;font-size:0.9rem;"
                    f"line-height:1.6;'>"
                    f"<p style='color:#3B82F6;font-weight:700;"
                    f"margin:0 0 8px;'>🤖 ANÁLISE CFO</p>"
                    f"{st.session_state['cf_analise'].replace(chr(10),'<br>')}"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # Pergunta personalizada
        if analisar and pergunta_cf.strip():
            ctx_ia = {
                "saldo_atual":         round(saldo_atual, 2),
                "autonomia_meses":     autonomia_meses,
                "custos_fixos_mes":    round(custos_fixos_mes, 2),
                "dias_saldo_negativo": dias_neg,
                "data_critica":        data_primeiro_neg,
                "entradas_30d":        round(ent_30, 2),
                "saidas_30d":          round(sai_30, 2),
                "saldo_prev_30d":      round(sal_30, 2),
            }
            with st.spinner("🤖 A pensar..."):
                resposta = _previsao_cashflow_ia(
                    cf_data, saldo_atual, custos_fixos_mes
                )
            st.markdown(
                f"<div style='background:rgba(16,185,129,0.08);"
                f"border:1px solid #10B981;"
                f"border-radius:12px;padding:16px;margin-top:12px;"
                f"color:#E2E8F0;font-size:0.9rem;line-height:1.6;'>"
                f"<p style='color:#10B981;font-weight:700;"
                f"margin:0 0 8px;'>💬 {pergunta_cf}</p>"
                f"{resposta.replace(chr(10),'<br>')}"
                f"</div>",
                unsafe_allow_html=True
            )
            st.session_state['cf_ia_input'] = ''

"""
GESTNOW v3 — mod_iso9001.py
Sistema de Gestão da Qualidade — ISO 9001:2015
6 módulos: Objetivos, Riscos, Partes Interessadas,
           Auditorias Internas, Revisão pela Gestão,
           Avaliação de Fornecedores
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, io, os, json
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable, PageBreak)
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

def _dias_para(data_str):
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return 999

def _cor_rag(pct):
    if pct >= 80: return "#10B981"
    if pct >= 50: return "#F59E0B"
    return "#EF4444"


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_matriz_riscos(riscos_db):
    """Heatmap de calor — Probabilidade × Impacto."""
    if riscos_db.empty:
        return None

    niveis = {"Muito Baixo":1,"Baixo":2,"Médio":3,"Alto":4,"Muito Alto":5}

    fig = go.Figure()

    # Zonas de cor de fundo
    for i in range(1, 6):
        for j in range(1, 6):
            score = i * j
            cor = (
                "rgba(16,185,129,0.15)"  if score <= 4  else
                "rgba(245,158,11,0.15)"  if score <= 9  else
                "rgba(239,68,68,0.15)"
            )
            fig.add_shape(
                type="rect",
                x0=j-0.5, x1=j+0.5,
                y0=i-0.5, y1=i+0.5,
                fillcolor=cor,
                line_width=0,
                layer="below"
            )

    # Pontos dos riscos
    for _, r in riscos_db.iterrows():
        prob   = niveis.get(r.get('Probabilidade','Médio'), 3)
        imp    = niveis.get(r.get('Impacto','Médio'), 3)
        score  = prob * imp
        cor_p  = (
            "#10B981" if score <= 4  else
            "#F59E0B" if score <= 9  else
            "#EF4444"
        )
        fig.add_trace(go.Scatter(
            x=[imp], y=[prob],
            mode='markers+text',
            marker={'size':18,'color':cor_p,
                    'line':{'color':'#F1F5F9','width':2}},
            text=[str(r.get('ID',''))[:4]],
            textposition='middle center',
            textfont={'color':'#F1F5F9','size':8,'family':'Helvetica-Bold'},
            hovertemplate=(
                f"<b>{r.get('Descricao','')[:40]}</b><br>"
                f"Prob: {r.get('Probabilidade','')} · "
                f"Imp: {r.get('Impacto','')}<br>"
                f"Score: {score}<extra></extra>"
            ),
            showlegend=False
        ))

    niveis_label = ["","Muito Baixo","Baixo","Médio","Alto","Muito Alto"]
    fig.update_layout(
        title={'text':'Matriz de Risco — Probabilidade × Impacto',
               'font':{'color':'#F1F5F9'}},
        height=360,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={
            'title':{'text':'Impacto','font':{'color':'#94A3B8'}},
            'tickvals':list(range(1,6)),
            'ticktext':niveis_label[1:],
            'tickfont':{'color':'#94A3B8','size':9},
            'gridcolor':'#334155','range':[0.5,5.5]
        },
        yaxis={
            'title':{'text':'Probabilidade','font':{'color':'#94A3B8'}},
            'tickvals':list(range(1,6)),
            'ticktext':niveis_label[1:],
            'tickfont':{'color':'#94A3B8','size':9},
            'gridcolor':'#334155','range':[0.5,5.5]
        },
        margin=dict(t=50,b=40,l=100,r=20)
    )
    return fig


def _grafico_objetivos_progresso(obj_db):
    """Bar horizontal — progresso dos objetivos."""
    if obj_db.empty:
        return None

    obj_db = obj_db.copy()
    obj_db['Prog_N'] = pd.to_numeric(
        obj_db.get('Progresso',0), errors='coerce'
    ).fillna(0)

    nomes  = [str(r.get('Objetivo',''))[:35] for _, r in obj_db.iterrows()]
    progs  = obj_db['Prog_N'].tolist()
    metas  = [float(r.get('Meta',100) or 100) for _, r in obj_db.iterrows()]
    pcts   = [round(p/m*100,1) if m>0 else 0
              for p,m in zip(progs,metas)]
    cores  = [_cor_rag(p) for p in pcts]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Meta', x=metas, y=nomes,
        orientation='h',
        marker_color='rgba(100,116,139,0.25)',
        hoverinfo='skip', showlegend=True
    ))
    fig.add_trace(go.Bar(
        name='Realizado', x=progs, y=nomes,
        orientation='h',
        marker_color=cores,
        text=[f"{p:.0f}%" for p in pcts],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':10},
        hovertemplate='%{y}<br>Realizado: %{x}<extra></extra>',
        showlegend=True
    ))
    fig.update_layout(
        title={'text':'Progresso dos Objetivos da Qualidade',
               'font':{'color':'#F1F5F9'}},
        barmode='overlay',
        height=max(200, len(obj_db)*45+80),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=220,r=80)
    )
    return fig


def _grafico_radar_clausulas(resultados_aud: dict):
    """Radar de maturidade por cláusula ISO."""
    clausulas = [
        "4. Contexto", "5. Liderança", "6. Planeamento",
        "7. Suporte", "8. Operação", "9. Avaliação",
        "10. Melhoria"
    ]
    scores = [resultados_aud.get(c, 0) for c in clausulas]
    cats_c = clausulas + [clausulas[0]]
    vals_c = scores    + [scores[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_c, theta=cats_c,
        fill='toself', name='Maturidade',
        fillcolor='rgba(59,130,246,0.2)',
        line={'color':'#3B82F6','width':3},
        marker={'size':8}
    ))
    # Linha de referência (conforme = 3)
    fig.add_trace(go.Scatterpolar(
        r=[3]*len(clausulas)+[3],
        theta=cats_c,
        fill='toself', name='Mínimo Aceitável',
        fillcolor='rgba(245,158,11,0.05)',
        line={'color':'#F59E0B','width':2,'dash':'dash'},
        marker={'size':4}
    ))
    fig.update_layout(
        polar={
            'radialaxis':{
                'visible':True, 'range':[0,5],
                'tickvals':[1,2,3,4,5],
                'ticktext':['1\nInic.','2\nParcial','3\nDef.',
                            '4\nGerido','5\nOtimiz.'],
                'tickfont':{'color':'#64748B','size':8},
                'gridcolor':'#334155'
            },
            'angularaxis':{'tickfont':{'color':'#94A3B8','size':9}},
            'bgcolor':'rgba(30,41,59,0.5)'
        },
        title={'text':'Maturidade do SGQ por Cláusula ISO 9001',
               'font':{'color':'#F1F5F9'}},
        height=320,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        margin=dict(t=50,b=20,l=20,r=20)
    )
    return fig


def _grafico_fornecedores_score(forn_aval_db):
    """Bar chart score de fornecedores."""
    if forn_aval_db.empty:
        return None

    forn_aval_db = forn_aval_db.copy()
    forn_aval_db['Score_N'] = pd.to_numeric(
        forn_aval_db.get('Score_Total',0), errors='coerce'
    ).fillna(0)

    top = forn_aval_db.sort_values('Score_N', ascending=False).head(10)

    fig = go.Figure(go.Bar(
        x=[str(r.get('Fornecedor',''))[:25] for _, r in top.iterrows()],
        y=top['Score_N'].tolist(),
        marker_color=[
            '#10B981' if s >= 70
            else '#F59E0B' if s >= 50
            else '#EF4444'
            for s in top['Score_N']
        ],
        text=[f"{s:.0f}" for s in top['Score_N']],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':10},
        hovertemplate='%{x}<br>Score: %{y}/100<extra></extra>'
    ))
    fig.add_hline(
        y=70, line_dash="dash",
        line_color="#10B981", line_width=1,
        annotation_text="Qualificado (70)",
        annotation_font_color="#10B981"
    )
    fig.add_hline(
        y=50, line_dash="dash",
        line_color="#F59E0B", line_width=1,
        annotation_text="Condicional (50)",
        annotation_font_color="#F59E0B"
    )
    fig.update_layout(
        title={'text':'Score de Avaliação de Fornecedores',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9},
               'tickangle':-30},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'range':[0,120]},
        margin=dict(t=40,b=60,l=10,r=10),
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF REVISÃO PELA GESTÃO
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_revisao(
    ano: int,
    semestre: str,
    dados: dict,
    empresa: dict
) -> bytes:
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
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
        fontSize=9, spaceAfter=3, leading=13
    )
    h2_s = ParagraphStyle(
        'h2', parent=styles['Normal'],
        fontSize=12, fontName='Helvetica-Bold',
        spaceAfter=4, spaceBefore=8,
        textColor=colors.HexColor('#1E293B')
    )

    # Capa
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "REVISÃO PELA GESTÃO",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=20, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'),
                       spaceAfter=6, alignment=1)
    ))
    story.append(Paragraph(
        f"Sistema de Gestão da Qualidade — ISO 9001:2015",
        ParagraphStyle('sub2', parent=styles['Normal'],
                       fontSize=12, spaceAfter=4,
                       textColor=colors.HexColor('#64748B'),
                       alignment=1)
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(
        width="100%", thickness=3,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    meta_data = [
        ["Empresa",       empresa.get('nome','')],
        ["NIF",           empresa.get('nif','')],
        ["Ano / Período", f"{ano} — {semestre}"],
        ["Data",          datetime.now().strftime('%d/%m/%Y')],
        ["Elaborado por", dados.get('elaborado_por','')],
        ["Aprovado por",  dados.get('aprovado_por','')],
    ]
    mt = Table(meta_data, colWidths=[5*cm,12*cm])
    mt.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('FONTNAME',    (0,0),(0,-1),  'Helvetica-Bold'),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('BACKGROUND',  (0,0),(0,-1),  colors.HexColor('#F8FAFC')),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(mt)
    story.append(PageBreak())

    # Índice
    story.append(Paragraph("ÍNDICE", bold_s))
    for i, sec in enumerate([
        "1. Resultados de Auditorias",
        "2. Retorno de Informação de Clientes",
        "3. Desempenho de Processos e Conformidade",
        "4. Não Conformidades e Ações Corretivas",
        "5. Objetivos da Qualidade",
        "6. Avaliação de Fornecedores",
        "7. Gestão de Riscos",
        "8. Adequação de Recursos",
        "9. Decisões e Ações de Melhoria",
    ], 1):
        story.append(Paragraph(sec, normal_s))
    story.append(PageBreak())

    # Secções
    secoes = [
        ("1. Resultados de Auditorias",
         dados.get('auditorias',
                   'Sem auditorias internas realizadas neste período.')),
        ("2. Retorno de Informação de Clientes",
         dados.get('clientes',
                   'Sem reclamações registadas. Satisfação geral positiva.')),
        ("3. Desempenho de Processos e Conformidade",
         dados.get('processos',
                   'Indicadores de processo dentro dos limites definidos.')),
        ("4. Não Conformidades e Ações Corretivas",
         dados.get('ncs',
                   'Sem não conformidades críticas abertas.')),
        ("5. Objetivos da Qualidade",
         dados.get('objetivos',
                   'Objetivos em curso conforme plano anual.')),
        ("6. Avaliação de Fornecedores",
         dados.get('fornecedores',
                   'Fornecedores avaliados conforme procedimento PGQ-003.')),
        ("7. Gestão de Riscos e Oportunidades",
         dados.get('riscos',
                   'Sem novos riscos identificados de impacto elevado.')),
        ("8. Adequação de Recursos",
         dados.get('recursos',
                   'Recursos humanos e materiais considerados adequados.')),
        ("9. Decisões e Ações de Melhoria",
         dados.get('melhorias',
                   'Sem ações de melhoria pendentes.')),
    ]

    for titulo_s, conteudo_s in secoes:
        story.append(Paragraph(titulo_s, h2_s))
        story.append(HRFlowable(
            width="100%", thickness=1,
            color=colors.HexColor('#E2E8F0')
        ))
        story.append(Spacer(1, 0.15*cm))
        for linha in conteudo_s.split('\n'):
            if linha.strip():
                story.append(Paragraph(linha.strip(), normal_s))
        story.append(Spacer(1, 0.3*cm))

    # Indicadores chave
    story.append(PageBreak())
    story.append(Paragraph("INDICADORES CHAVE DO SGQ", bold_s))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    ind_data = [
        ["Indicador","Resultado","Meta","Estado"],
        ["NCs abertas",
         str(dados.get('n_nc_aber',0)),
         "0",
         "✅ OK" if dados.get('n_nc_aber',0)==0 else "⚠️"],
        ["Taxa conformidade inspeções",
         f"{dados.get('taxa_conf',0):.0f}%",
         "≥ 95%",
         "✅ OK" if dados.get('taxa_conf',0)>=95 else "⚠️"],
        ["Objetivos atingidos",
         f"{dados.get('obj_ating',0)}/{dados.get('obj_total',0)}",
         "100%",
         "✅ OK" if dados.get('obj_ating',0)==dados.get('obj_total',1) else "⚠️"],
        ["Fornecedores qualificados",
         f"{dados.get('forn_qual',0)}/{dados.get('forn_total',0)}",
         "≥ 80%",
         "✅ OK"],
        ["Auditorias realizadas",
         str(dados.get('aud_real',0)),
         str(dados.get('aud_plan',0)),
         "✅ OK" if dados.get('aud_real',0)>=dados.get('aud_plan',1) else "⚠️"],
    ]
    it = Table(ind_data, colWidths=[7*cm,3.5*cm,3.5*cm,3*cm])
    it.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR',    (0,0),(-1,0), colors.white),
        ('FONTNAME',     (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0),(-1,-1), 9),
        ('GRID',         (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING',   (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING',  (0,0),(-1,-1), 6),
    ]))
    story.append(it)
    story.append(Spacer(1, 1*cm))

    # Assinaturas
    ass_data = [
        ["Elaborado por:",          "Aprovado por (Gestão de Topo):"],
        [dados.get('elaborado_por','_________________'),
         dados.get('aprovado_por','_________________')],
        ["Data: ___/___/______",    "Data: ___/___/______"],
        ["Assinatura:",             "Assinatura:"],
        ["_____________________",  "_____________________"],
    ]
    at = Table(ass_data, colWidths=[8.5*cm,8.5*cm])
    at.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
        ('TOPPADDING',  (0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
    ]))
    story.append(at)
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Paragraph(
        f"GESTNOW v3.0 · ISO 9001:2015 · "
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        f"Confidencial — uso interno",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey,
                       alignment=1)
    ))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_iso9001(*_):
    """Módulo ISO 9001:2015 — Sistema de Gestão da Qualidade."""

    # ── Carregar dados ────────────────────────────────────────────
    obj_db   = _load("iso_objetivos.csv", [
        "ID","Ano","Objetivo","Indicador","Meta","Unidade",
        "Progresso","Responsavel","Prazo","Status","Notas"
    ])
    riscos_db = _load("iso_riscos.csv", [
        "ID","Data","Processo","Descricao","Tipo",
        "Probabilidade","Impacto","Score","Tratamento",
        "Responsavel","Prazo","Status","Residual"
    ])
    partes_db = _load("iso_partes_interessadas.csv", [
        "ID","Nome","Tipo","Expectativas","Requisitos",
        "Nivel_Influencia","Nivel_Interesse","Acao","Responsavel"
    ])
    aud_db   = _load("iso_auditorias.csv", [
        "ID","Data_Planeada","Data_Real","Tipo","Auditor",
        "Clausulas","Scope","Resultado","Achados",
        "NCs_Aber","NCs_Men","Obs_Positivas","Status",
        "Relatorio_b64"
    ])
    forn_aval_db = _load("iso_fornecedores_aval.csv", [
        "ID","Fornecedor","Data_Aval","Obra","Categoria",
        "Q_Qualidade","Q_Prazo","Q_Preco","Q_Comunicacao",
        "Q_Documentacao","Score_Total","Classificacao",
        "Acao","Avaliado_Por","Notas"
    ])
    nc_db    = _load("nao_conformidades.csv", [
        "ID","Data","Obra","Tipo","Gravidade","Status",
        "Descricao","Causa_Raiz","Acao_Corretiva","Prazo_AC"
    ])
    insp_db  = _load("inspecoes_qualidade.csv", [
        "ID","Data","Obra","Tipo_Inspecao","Resultado"
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
    ano_atual = hoje.year

    # ── KPIs gerais ───────────────────────────────────────────────
    n_riscos_altos = 0
    if not riscos_db.empty and 'Score' in riscos_db.columns:
        riscos_db['Score_N'] = pd.to_numeric(
            riscos_db['Score'], errors='coerce'
        ).fillna(0)
        n_riscos_altos = len(riscos_db[riscos_db['Score_N'] >= 12])

    n_obj_tot = len(obj_db) if not obj_db.empty else 0
    n_obj_ok  = 0
    if not obj_db.empty and 'Status' in obj_db.columns:
        n_obj_ok = len(obj_db[obj_db['Status']=='Atingido'])

    n_aud_ano = 0
    if not aud_db.empty and 'Data_Planeada' in aud_db.columns:
        adb = aud_db.copy()
        adb['Ano_d'] = pd.to_datetime(
            adb['Data_Planeada'], dayfirst=True, errors='coerce'
        ).dt.year
        n_aud_ano = len(adb[adb['Ano_d'] == ano_atual])

    nc_abertas = 0
    if not nc_db.empty and 'Status' in nc_db.columns:
        nc_abertas = len(nc_db[
            nc_db['Status'].isin(['Aberta','Em Tratamento'])
        ])

    taxa_conf = 0.0
    if not insp_db.empty and 'Resultado' in insp_db.columns:
        tot_i  = len(insp_db)
        conf_i = len(insp_db[insp_db['Resultado']=='Conforme'])
        taxa_conf = round(conf_i/tot_i*100,1) if tot_i > 0 else 0.0

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .iso-card {
        background:#1E293B; border-radius:12px;
        padding:14px 16px; margin-bottom:8px;
    }
    .iso-badge {
        display:inline-block; padding:3px 10px;
        border-radius:20px; font-size:0.72rem; font-weight:700;
    }
    .clausula-item {
        background:#1E293B; border-radius:8px;
        padding:10px 14px; margin-bottom:6px;
        border-left:3px solid;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1E293B,#0F172A);"
        "padding:20px;border-radius:14px;margin-bottom:16px;"
        "border:1px solid rgba(255,255,255,0.08);'>"
        "<h2 style='color:#F1F5F9;margin:0;font-size:1.5rem;'>"
        "🏆 ISO 9001:2015 — Sistema de Gestão da Qualidade</h2>"
        "<p style='color:#64748B;margin:4px 0 0;font-size:0.85rem;'>"
        f"{empresa.get('nome','')} · Atualizado: "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
        "</p></div>",
        unsafe_allow_html=True
    )

    # KPIs
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("🎯 Objetivos",
                       f"{n_obj_ok}/{n_obj_tot}",
                       delta="atingidos")
    with c2: st.metric("⚠️ Riscos Altos",  n_riscos_altos)
    with c3: st.metric("🔍 Auditorias/Ano",n_aud_ano)
    with c4: st.metric("🔴 NCs Abertas",   nc_abertas)
    with c5: st.metric("✅ Taxa Conformidade",f"{taxa_conf:.0f}%")

    st.divider()

    # ── 6 Tabs ────────────────────────────────────────────────────
    (t_obj, t_ris, t_part,
     t_aud, t_rev, t_forn) = st.tabs([
        "🎯 Objetivos",
        "⚠️ Gestão de Riscos",
        "🏢 Partes Interessadas",
        "🔍 Auditorias Internas",
        "📊 Revisão pela Gestão",
        "🏭 Avaliação Fornecedores",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 — OBJETIVOS DA QUALIDADE (Cláusula 6.2)
    # ════════════════════════════════════════════════════════════════
    with t_obj:
        st.markdown("### 🎯 Objetivos da Qualidade")
        st.info(
            "ISO 9001:2015 Cláusula 6.2 — Os objetivos devem ser "
            "mensuráveis, monitorizados, comunicados e atualizados."
        )

        col_of, col_ol = st.columns([1, 2])

        with col_of:
            st.markdown("#### ➕ Novo Objetivo")
            with st.form("form_obj_iso"):
                o_ano    = st.number_input(
                    "Ano", min_value=2024,
                    value=ano_atual, key="o_ano"
                )
                o_obj    = st.text_area(
                    "Objetivo *", key="o_obj",
                    placeholder="Ex: Reduzir NCs em 20%"
                )
                o_ind    = st.text_input(
                    "Indicador *", key="o_ind",
                    placeholder="Ex: Nº de NCs abertas"
                )
                col_om1, col_om2 = st.columns(2)
                with col_om1:
                    o_meta = st.number_input(
                        "Meta *", min_value=0.0,
                        step=1.0, key="o_meta"
                    )
                with col_om2:
                    o_uni  = st.text_input(
                        "Unidade", key="o_uni",
                        placeholder="%, nº, €..."
                    )
                o_prog   = st.number_input(
                    "Progresso Atual",
                    min_value=0.0, step=0.5,
                    key="o_prog"
                )
                o_resp   = st.text_input(
                    "Responsável",
                    value=user_nome, key="o_resp"
                )
                o_prazo  = st.text_input(
                    "Prazo (dd/mm/aaaa)",
                    value=f"31/12/{ano_atual}",
                    key="o_prazo"
                )
                o_stat   = st.selectbox(
                    "Estado",
                    ["Em Curso","Atingido","Não Atingido",
                     "Cancelado"],
                    key="o_stat"
                )
                o_notas  = st.text_area("Notas", key="o_notas")

                if st.form_submit_button(
                    "💾 Guardar Objetivo",
                    use_container_width=True, type="primary"
                ):
                    if not o_obj.strip() or not o_ind.strip():
                        st.error("❌ Objetivo e indicador obrigatórios.")
                    else:
                        novo_o = pd.DataFrame([{
                            "ID":         str(uuid.uuid4())[:8].upper(),
                            "Ano":        o_ano,
                            "Objetivo":   o_obj.strip(),
                            "Indicador":  o_ind.strip(),
                            "Meta":       o_meta,
                            "Unidade":    o_uni.strip(),
                            "Progresso":  o_prog,
                            "Responsavel":o_resp.strip(),
                            "Prazo":      o_prazo.strip(),
                            "Status":     o_stat,
                            "Notas":      o_notas.strip()
                        }])
                        upd = pd.concat(
                            [obj_db, novo_o], ignore_index=True
                        ) if not obj_db.empty else novo_o
                        save_db(upd,"iso_objetivos.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="CRIAR_OBJETIVO_ISO",
                            tabela="iso_objetivos.csv",
                            registro_id=novo_o['ID'].iloc[0],
                            detalhes=f"{o_obj[:50]} | Meta:{o_meta}",
                            ip=""
                        )
                        inv("iso_objetivos.csv"); st.success("✅ Objetivo criado!"); st.rerun()

        with col_ol:
            st.markdown("#### 📊 Objetivos em Curso")

            # Filtro ano
            anos_obj = [ano_atual]
            if not obj_db.empty and 'Ano' in obj_db.columns:
                anos_obj = sorted(
                    obj_db['Ano'].dropna().astype(int).unique().tolist(),
                    reverse=True
                )
            ano_filt_o = st.selectbox(
                "Ano", anos_obj, key="obj_ano_filt"
            )

            df_o = obj_db[
                obj_db['Ano'].astype(str) == str(ano_filt_o)
            ] if not obj_db.empty else pd.DataFrame()

            # Gráfico
            fig_obj = _grafico_objetivos_progresso(df_o)
            if fig_obj:
                st.plotly_chart(
                    fig_obj, use_container_width=True
                )

            if df_o.empty:
                st.info("📋 Sem objetivos para este ano.")
            else:
                for _, obj in df_o.iterrows():
                    oid   = obj.get('ID','')
                    meta  = float(obj.get('Meta',100) or 100)
                    prog  = float(obj.get('Progresso',0) or 0)
                    pct   = round(prog/meta*100,1) if meta>0 else 0
                    stat  = obj.get('Status','')
                    cor_s = {
                        'Atingido':    '#10B981',
                        'Em Curso':    '#3B82F6',
                        'Não Atingido':'#EF4444',
                        'Cancelado':   '#64748B'
                    }.get(stat,'#6B7280')
                    cor_p = _cor_rag(pct)

                    st.markdown(
                        f"<div class='iso-card' "
                        f"style='border-left:3px solid {cor_p};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:0.88rem;'>"
                        f"{obj.get('Objetivo','')[:50]}</b>"
                        f"<span class='iso-badge' "
                        f"style='background:{cor_s}22;color:{cor_s};'>"
                        f"{stat}</span>"
                        f"</div>"
                        f"<small style='color:#64748B;'>"
                        f"📊 {obj.get('Indicador','')} · "
                        f"Meta: {meta} {obj.get('Unidade','')} · "
                        f"Responsável: {obj.get('Responsavel','')}</small>"
                        f"<div style='background:#0F172A;"
                        f"border-radius:3px;height:6px;margin:8px 0 4px;'>"
                        f"<div style='background:{cor_p};width:{min(pct,100):.0f}%;"
                        f"height:6px;border-radius:3px;'></div></div>"
                        f"<small style='color:{cor_p};"
                        f"font-weight:700;'>{pct:.1f}% "
                        f"({prog}/{meta} {obj.get('Unidade','')})</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    # Editar progresso inline
                    col_ep, col_es = st.columns([3,1])
                    with col_ep:
                        novo_prog = st.number_input(
                            "Atualizar progresso",
                            min_value=0.0,
                            value=prog,
                            step=0.5,
                            key=f"prog_{oid}",
                            label_visibility="collapsed"
                        )
                    with col_es:
                        if st.button(
                            "✅",
                            key=f"upd_obj_{oid}",
                            use_container_width=True,
                            help="Guardar progresso"
                        ):
                            obj_db.loc[
                                obj_db['ID']==oid,'Progresso'
                            ] = novo_prog
                            # Auto-atingido se >= meta
                            if novo_prog >= meta:
                                obj_db.loc[
                                    obj_db['ID']==oid,'Status'
                                ] = 'Atingido'
                            save_db(obj_db,"iso_objetivos.csv")
                            inv("iso_objetivos.csv"); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 2 — GESTÃO DE RISCOS (Cláusula 6.1)
    # ════════════════════════════════════════════════════════════════
    with t_ris:
        st.markdown("### ⚠️ Gestão de Riscos e Oportunidades")
        st.info(
            "ISO 9001:2015 Cláusula 6.1 — Identificar riscos e "
            "oportunidades que podem afetar a conformidade "
            "de produtos/serviços."
        )

        col_rf, col_rl = st.columns([1, 2])

        with col_rf:
            st.markdown("#### ➕ Novo Risco / Oportunidade")
            with st.form("form_risco"):
                r_proc   = st.selectbox(
                    "Processo *",
                    ["Comercial","Produção / Obras","Compras",
                     "RH","Qualidade","IT","HSE",
                     "Gestão de Topo","Outro"],
                    key="r_proc"
                )
                r_tipo   = st.selectbox(
                    "Tipo",
                    ["Risco","Oportunidade"],
                    key="r_tipo"
                )
                r_desc   = st.text_area(
                    "Descrição *", key="r_desc",
                    placeholder="Descreve o risco ou oportunidade..."
                )
                col_rp, col_ri = st.columns(2)
                niveis_risco = ["Muito Baixo","Baixo","Médio",
                                "Alto","Muito Alto"]
                with col_rp:
                    r_prob   = st.selectbox(
                        "Probabilidade",
                        niveis_risco, index=2, key="r_prob"
                    )
                with col_ri:
                    r_imp    = st.selectbox(
                        "Impacto",
                        niveis_risco, index=2, key="r_imp"
                    )

                nivel_map = {
                    "Muito Baixo":1,"Baixo":2,"Médio":3,
                    "Alto":4,"Muito Alto":5
                }
                score_calc = nivel_map[r_prob] * nivel_map[r_imp]
                cor_sc = (
                    "#10B981" if score_calc <= 4  else
                    "#F59E0B" if score_calc <= 9  else
                    "#EF4444"
                )
                st.markdown(
                    f"<div style='background:{cor_sc}18;"
                    f"border:1px solid {cor_sc};"
                    f"border-radius:6px;padding:8px;"
                    f"text-align:center;'>"
                    f"<b style='color:{cor_sc};'>Score: {score_calc}/25</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                r_trat   = st.text_area(
                    "Tratamento / Ação *", key="r_trat",
                    placeholder="Ex: Implementar procedimento..."
                )
                r_resp   = st.text_input(
                    "Responsável",
                    value=user_nome, key="r_resp"
                )
                r_prazo  = st.text_input(
                    "Prazo",
                    value=(hoje + timedelta(days=30)).strftime("%d/%m/%Y"),
                    key="r_prazo"
                )

                if st.form_submit_button(
                    "💾 Registar",
                    use_container_width=True, type="primary"
                ):
                    if not r_desc.strip():
                        st.error("❌ Descrição obrigatória.")
                    else:
                        novo_r = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Data":         hoje.strftime("%d/%m/%Y"),
                            "Processo":     r_proc,
                            "Descricao":    r_desc.strip(),
                            "Tipo":         r_tipo,
                            "Probabilidade":r_prob,
                            "Impacto":      r_imp,
                            "Score":        score_calc,
                            "Tratamento":   r_trat.strip(),
                            "Responsavel":  r_resp.strip(),
                            "Prazo":        r_prazo.strip(),
                            "Status":       "Aberto",
                            "Residual":     ""
                        }])
                        upd_r = pd.concat(
                            [riscos_db, novo_r], ignore_index=True
                        ) if not riscos_db.empty else novo_r
                        save_db(upd_r,"iso_riscos.csv")
                        inv("iso_riscos.csv")
                        st.success(
                            f"✅ {r_tipo} registado! Score: {score_calc}"
                        )
                        st.rerun()

        with col_rl:
            # Matriz de calor
            fig_mat = _grafico_matriz_riscos(riscos_db)
            if fig_mat:
                st.plotly_chart(fig_mat, use_container_width=True)
            else:
                st.info("📋 Sem riscos para mostrar na matriz.")

            # Lista de riscos
            if not riscos_db.empty:
                riscos_db['Score_N'] = pd.to_numeric(
                    riscos_db.get('Score',0), errors='coerce'
                ).fillna(0)

                # Filtros
                col_rf1, col_rf2 = st.columns(2)
                with col_rf1:
                    tipo_filt = st.selectbox(
                        "Tipo",
                        ["Todos","Risco","Oportunidade"],
                        key="ris_tipo_f"
                    )
                with col_rf2:
                    stat_filt = st.selectbox(
                        "Estado",
                        ["Todos","Aberto","Em Tratamento","Fechado"],
                        key="ris_stat_f"
                    )

                df_r = riscos_db.copy()
                if tipo_filt != "Todos":
                    df_r = df_r[df_r['Tipo']==tipo_filt]
                if stat_filt != "Todos" and 'Status' in df_r.columns:
                    df_r = df_r[df_r['Status']==stat_filt]

                df_r = df_r.sort_values('Score_N',ascending=False)

                for _, ris in df_r.iterrows():
                    rid   = ris.get('ID','')
                    score = float(ris.get('Score_N',0))
                    cor_s = (
                        "#10B981" if score<=4  else
                        "#F59E0B" if score<=9  else
                        "#EF4444"
                    )
                    ic_t  = "⚠️" if ris.get('Tipo')=='Risco' else "✨"

                    with st.expander(
                        f"{ic_t} [{ris.get('Processo','')}] "
                        f"{str(ris.get('Descricao',''))[:45]} "
                        f"| Score: {score:.0f}",
                        expanded=(score >= 12)
                    ):
                        col_ri1, col_ri2 = st.columns([3,1])
                        with col_ri1:
                            st.markdown(
                                f"<div class='iso-card'>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Tipo:</b> {ris.get('Tipo','')} · "
                                f"<b>Processo:</b> {ris.get('Processo','')}</p>"
                                f"<p style='color:#94A3B8;margin:2px 0;'>"
                                f"{ris.get('Descricao','')}</p>"
                                f"<p style='color:#3B82F6;margin:2px 0;'>"
                                f"<b>Tratamento:</b> "
                                f"{ris.get('Tratamento','')}</p>"
                                f"<p style='color:#64748B;margin:2px 0;'>"
                                f"Responsável: {ris.get('Responsavel','')} · "
                                f"Prazo: {ris.get('Prazo','')}</p>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with col_ri2:
                            st.markdown(
                                f"<div style='background:{cor_s}18;"
                                f"border:1px solid {cor_s};"
                                f"border-radius:8px;padding:12px;"
                                f"text-align:center;'>"
                                f"<b style='color:{cor_s};"
                                f"font-size:1.5rem;'>"
                                f"{score:.0f}</b><br>"
                                f"<small style='color:#64748B;'>"
                                f"{ris.get('Probabilidade','')} × "
                                f"{ris.get('Impacto','')}</small>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            novo_stat_r = st.selectbox(
                                "Estado",
                                ["Aberto","Em Tratamento","Fechado"],
                                key=f"r_st_{rid}",
                                index=["Aberto","Em Tratamento",
                                       "Fechado"].index(
                                    ris.get('Status','Aberto')
                                ) if ris.get('Status','Aberto') in [
                                    "Aberto","Em Tratamento","Fechado"
                                ] else 0
                            )
                            residual = st.text_input(
                                "Risco Residual",
                                value=str(ris.get('Residual','')),
                                key=f"r_res_{rid}"
                            )
                            if st.button(
                                "💾",
                                key=f"r_upd_{rid}",
                                use_container_width=True
                            ):
                                riscos_db.loc[
                                    riscos_db['ID']==rid,'Status'
                                ] = novo_stat_r
                                riscos_db.loc[
                                    riscos_db['ID']==rid,'Residual'
                                ] = residual
                                save_db(riscos_db,"iso_riscos.csv")
                                inv("iso_riscos.csv"); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 3 — PARTES INTERESSADAS (Cláusula 4.2)
    # ════════════════════════════════════════════════════════════════
    with t_part:
        st.markdown("### 🏢 Partes Interessadas")
        st.info(
            "ISO 9001:2015 Cláusula 4.2 — Identificar partes "
            "interessadas relevantes e as suas expectativas e "
            "requisitos que afetam o SGQ."
        )

        col_pf, col_pl = st.columns([1, 2])

        with col_pf:
            st.markdown("#### ➕ Nova Parte Interessada")
            with st.form("form_parte"):
                p_nome  = st.text_input(
                    "Nome *", key="p_nome",
                    placeholder="Ex: Clientes da Refinaria Sines"
                )
                p_tipo  = st.selectbox(
                    "Tipo *",
                    ["Cliente","Fornecedor","Colaborador",
                     "Acionista / Sócio","Regulador / Estado",
                     "Comunidade","Parceiro","Outro"],
                    key="iso_p_tipo"
                )
                p_exp   = st.text_area(
                    "Expectativas", key="p_exp",
                    placeholder="O que esperam de nós?"
                )
                p_req   = st.text_area(
                    "Requisitos", key="p_req",
                    placeholder="Requisitos legais, contratuais..."
                )
                col_pi1, col_pi2 = st.columns(2)
                with col_pi1:
                    p_inf  = st.selectbox(
                        "Nível Influência",
                        ["Baixo","Médio","Alto"],
                        index=1, key="p_inf"
                    )
                with col_pi2:
                    p_int  = st.selectbox(
                        "Nível Interesse",
                        ["Baixo","Médio","Alto"],
                        index=1, key="p_int"
                    )
                p_acao  = st.text_area(
                    "Ação de Gestão", key="p_acao",
                    placeholder="Como gerimos esta relação?"
                )
                p_resp  = st.text_input(
                    "Responsável",
                    value=user_nome, key="p_resp"
                )

                if st.form_submit_button(
                    "💾 Registar",
                    use_container_width=True, type="primary"
                ):
                    if not p_nome.strip():
                        st.error("❌ Nome obrigatório.")
                    else:
                        nova_p = pd.DataFrame([{
                            "ID":              str(uuid.uuid4())[:8].upper(),
                            "Nome":            p_nome.strip(),
                            "Tipo":            p_tipo,
                            "Expectativas":    p_exp.strip(),
                            "Requisitos":      p_req.strip(),
                            "Nivel_Influencia":p_inf,
                            "Nivel_Interesse": p_int,
                            "Acao":            p_acao.strip(),
                            "Responsavel":     p_resp.strip()
                        }])
                        upd_p = pd.concat(
                            [partes_db, nova_p], ignore_index=True
                        ) if not partes_db.empty else nova_p
                        save_db(upd_p,"iso_partes_interessadas.csv")
                        inv("iso_partes_interessadas.csv")
                        st.success(f"✅ {p_nome} registado!")
                        st.rerun()

        with col_pl:
            st.markdown("#### 📋 Mapa de Partes Interessadas")

            if partes_db.empty:
                st.info("📋 Sem partes interessadas registadas.")
            else:
                # Matriz Influência × Interesse
                inf_map  = {"Baixo":1,"Médio":2,"Alto":3}
                int_map  = {"Baixo":1,"Médio":2,"Alto":3}
                cores_t  = {
                    "Cliente":     "#3B82F6",
                    "Fornecedor":  "#10B981",
                    "Colaborador": "#8B5CF6",
                    "Acionista / Sócio":"#F59E0B",
                    "Regulador / Estado":"#EF4444",
                    "Comunidade":  "#06B6D4",
                    "Parceiro":    "#F97316",
                    "Outro":       "#64748B",
                }

                fig_pi = go.Figure()
                for _, pi in partes_db.iterrows():
                    xi = int_map.get(pi.get('Nivel_Interesse','Médio'),2)
                    yi = inf_map.get(pi.get('Nivel_Influencia','Médio'),2)
                    cor_pi = cores_t.get(pi.get('Tipo','Outro'),'#6B7280')
                    fig_pi.add_trace(go.Scatter(
                        x=[xi], y=[yi],
                        mode='markers+text',
                        marker={'size':22,'color':cor_pi,
                                'line':{'color':'#F1F5F9','width':2}},
                        text=[str(pi.get('Nome',''))[:12]],
                        textposition='top center',
                        textfont={'color':'#F1F5F9','size':8},
                        hovertemplate=(
                            f"<b>{pi.get('Nome','')}</b><br>"
                            f"Tipo: {pi.get('Tipo','')}<br>"
                            f"Influência: {pi.get('Nivel_Influencia','')}<br>"
                            f"Interesse: {pi.get('Nivel_Interesse','')}"
                            f"<extra></extra>"
                        ),
                        showlegend=False
                    ))

                fig_pi.update_layout(
                    title={'text':'Matriz Influência × Interesse',
                           'font':{'color':'#F1F5F9'}},
                    height=300,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(30,41,59,0.5)',
                    font={'color':'#F1F5F9'},
                    xaxis={
                        'title':{'text':'Interesse',
                                 'font':{'color':'#94A3B8'}},
                        'tickvals':[1,2,3],
                        'ticktext':['Baixo','Médio','Alto'],
                        'tickfont':{'color':'#94A3B8'},
                        'gridcolor':'#334155','range':[0.5,3.5]
                    },
                    yaxis={
                        'title':{'text':'Influência',
                                 'font':{'color':'#94A3B8'}},
                        'tickvals':[1,2,3],
                        'ticktext':['Baixo','Médio','Alto'],
                        'tickfont':{'color':'#94A3B8'},
                        'gridcolor':'#334155','range':[0.5,3.5]
                    },
                    margin=dict(t=50,b=40,l=80,r=20)
                )
                st.plotly_chart(fig_pi, use_container_width=True)

                # Tabela
                cols_pi = [c for c in [
                    'Nome','Tipo','Nivel_Influencia',
                    'Nivel_Interesse','Acao','Responsavel'
                ] if c in partes_db.columns]
                st.dataframe(
                    partes_db[cols_pi],
                    use_container_width=True,
                    hide_index=True
                )

                csv_pi = partes_db[cols_pi].to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    "📥 Exportar",
                    data=csv_pi.encode('utf-8-sig'),
                    file_name="partes_interessadas.csv",
                    mime="text/csv",
                    key="dl_pi"
                )

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — AUDITORIAS INTERNAS (Cláusula 9.2)
    # ════════════════════════════════════════════════════════════════
    with t_aud:
        st.markdown("### 🔍 Auditorias Internas")
        st.info(
            "ISO 9001:2015 Cláusula 9.2 — Realizar auditorias "
            "internas planeadas para verificar conformidade "
            "com os requisitos da norma e do SGQ."
        )

        col_af2, col_al2 = st.columns([1, 2])

        with col_af2:
            st.markdown("#### ➕ Planear Auditoria")
            with st.form("form_aud"):
                a_tipo  = st.selectbox(
                    "Tipo *",
                    ["Auditoria Interna ISO 9001",
                     "Auditoria de Processo",
                     "Auditoria de Produto/Serviço",
                     "Auditoria de Fornecedor",
                     "Auditoria de Follow-Up"],
                    key="a_tipo"
                )
                a_aud   = st.text_input(
                    "Auditor *",
                    value=user_nome, key="a_aud"
                )
                a_scope = st.text_area(
                    "Âmbito / Scope", key="a_scope",
                    placeholder="Ex: Processos de produção, "
                                "cláusulas 8.1 a 8.7"
                )
                a_claus = st.multiselect(
                    "Cláusulas ISO a auditar",
                    ["4 - Contexto","5 - Liderança",
                     "6 - Planeamento","7 - Suporte",
                     "8 - Operação","9 - Avaliação Desempenho",
                     "10 - Melhoria"],
                    key="a_claus"
                )
                col_ad1, col_ad2 = st.columns(2)
                with col_ad1:
                    a_plan = st.date_input(
                        "Data Planeada",
                        value=hoje + timedelta(days=14),
                        key="a_plan"
                    )
                with col_ad2:
                    a_real_d = st.date_input(
                        "Data Real (se já realizada)",
                        value=hoje,
                        key="a_real_d"
                    )
                a_result = st.selectbox(
                    "Resultado",
                    ["Pendente","Conforme","Conforme c/ Obs.",
                     "Não Conforme","Suspenso"],
                    key="a_result"
                )
                a_achados = st.text_area(
                    "Achados / Observações", key="a_achados"
                )
                col_an1, col_an2, col_an3 = st.columns(3)
                with col_an1:
                    a_nc_aber = st.number_input(
                        "NCs Abertas", min_value=0,
                        value=0, key="a_nc_aber"
                    )
                with col_an2:
                    a_nc_men = st.number_input(
                        "NCs Menores", min_value=0,
                        value=0, key="a_nc_men"
                    )
                with col_an3:
                    a_obs_pos = st.number_input(
                        "Obs. Positivas", min_value=0,
                        value=0, key="a_obs_pos"
                    )

                if st.form_submit_button(
                    "💾 Guardar Auditoria",
                    use_container_width=True, type="primary"
                ):
                    nova_a = pd.DataFrame([{
                        "ID":           str(uuid.uuid4())[:8].upper(),
                        "Data_Planeada":a_plan.strftime("%d/%m/%Y"),
                        "Data_Real":    a_real_d.strftime("%d/%m/%Y")
                                        if a_result != "Pendente" else "",
                        "Tipo":         a_tipo,
                        "Auditor":      a_aud.strip(),
                        "Clausulas":    ", ".join(a_claus),
                        "Scope":        a_scope.strip(),
                        "Resultado":    a_result,
                        "Achados":      a_achados.strip(),
                        "NCs_Aber":     a_nc_aber,
                        "NCs_Men":      a_nc_men,
                        "Obs_Positivas":a_obs_pos,
                        "Status":       "Planeada" if a_result=="Pendente"
                                        else "Concluída",
                        "Relatorio_b64":""
                    }])
                    upd_a = pd.concat(
                        [aud_db, nova_a], ignore_index=True
                    ) if not aud_db.empty else nova_a
                    save_db(upd_a,"iso_auditorias.csv")
                    log_audit(
                        usuario=user_nome,
                        acao="CRIAR_AUDITORIA_ISO",
                        tabela="iso_auditorias.csv",
                        registro_id=nova_a['ID'].iloc[0],
                        detalhes=(
                            f"{a_tipo} | {a_result} | "
                            f"NCs: {a_nc_aber}"
                        ),
                        ip=""
                    )
                    inv("iso_auditorias.csv")
                    st.success("✅ Auditoria registada!")
                    st.rerun()

        with col_al2:
            st.markdown("#### 📊 Plano Anual de Auditorias")

            # Calendário anual
            ano_aud = st.number_input(
                "Ano", min_value=2024,
                value=ano_atual, key="aud_ano_filt"
            )

            if not aud_db.empty:
                adb2 = aud_db.copy()
                adb2['Data_Planeada_d'] = pd.to_datetime(
                    adb2['Data_Planeada'], dayfirst=True, errors='coerce'
                )
                adb2 = adb2[
                    adb2['Data_Planeada_d'].dt.year == ano_aud
                ]

                if adb2.empty:
                    st.info(f"📋 Sem auditorias planeadas para {ano_aud}.")
                else:
                    # KPIs
                    n_plan  = len(adb2)
                    n_conc  = len(adb2[adb2['Status']=='Concluída'])
                    n_nc_t  = pd.to_numeric(
                        adb2.get('NCs_Aber',0), errors='coerce'
                    ).fillna(0).sum()

                    c1,c2,c3 = st.columns(3)
                    with c1: st.metric("📋 Planeadas", n_plan)
                    with c2: st.metric("✅ Concluídas",n_conc)
                    with c3: st.metric("🔴 NCs Total", int(n_nc_t))

                    # Radar maturidade (se há dados por cláusula)
                    result_map = {
                        'Conforme':3,
                        'Conforme c/ Obs.':2,
                        'Não Conforme':1,
                        'Pendente':0,
                    }
                    clausulas_radar = {
                        "4. Contexto":3, "5. Liderança":3,
                        "6. Planeamento":3, "7. Suporte":3,
                        "8. Operação":3, "9. Avaliação":3,
                        "10. Melhoria":3
                    }
                    # Actualizar com resultados reais
                    for _, aud_r in adb2.iterrows():
                        claus_str = str(aud_r.get('Clausulas',''))
                        result_v  = result_map.get(
                            aud_r.get('Resultado','Pendente'), 0
                        )
                        for k in clausulas_radar.keys():
                            num = k.split('.')[0]
                            if num in claus_str:
                                clausulas_radar[k] = min(
                                    clausulas_radar[k], result_v+2
                                )

                    fig_rad = _grafico_radar_clausulas(clausulas_radar)
                    st.plotly_chart(fig_rad, use_container_width=True)

                    # Lista
                    for _, aud_r in adb2.sort_values(
                        'Data_Planeada_d'
                    ).iterrows():
                        aid    = aud_r.get('ID','')
                        res    = aud_r.get('Resultado','Pendente')
                        cor_r  = {
                            'Conforme':          '#10B981',
                            'Conforme c/ Obs.':  '#F59E0B',
                            'Não Conforme':      '#EF4444',
                            'Pendente':          '#64748B',
                            'Suspenso':          '#94A3B8',
                        }.get(res,'#6B7280')

                        with st.expander(
                            f"🔍 {aud_r.get('Data_Planeada','')} — "
                            f"{aud_r.get('Tipo','')} | {res}",
                            expanded=False
                        ):
                            st.markdown(
                                f"<div class='iso-card' "
                                f"style='border-left:3px solid {cor_r};'>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Auditor:</b> {aud_r.get('Auditor','')}</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Cláusulas:</b> "
                                f"{aud_r.get('Clausulas','')}</p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Âmbito:</b> {aud_r.get('Scope','')}</p>"
                                f"<p style='color:#94A3B8;margin:2px 0;'>"
                                f"{aud_r.get('Achados','')}</p>"
                                f"<small style='color:#64748B;'>"
                                f"NCs Abertas: {aud_r.get('NCs_Aber',0)} · "
                                f"NCs Menores: {aud_r.get('NCs_Men',0)} · "
                                f"Obs. Positivas: "
                                f"{aud_r.get('Obs_Positivas',0)}"
                                f"</small></div>",
                                unsafe_allow_html=True
                            )

            else:
                st.info("📋 Sem auditorias registadas.")

    # ════════════════════════════════════════════════════════════════
    # TAB 5 — REVISÃO PELA GESTÃO (Cláusula 9.3)
    # ════════════════════════════════════════════════════════════════
    with t_rev:
        st.markdown("### 📊 Revisão pela Gestão")
        st.info(
            "ISO 9001:2015 Cláusula 9.3 — A gestão de topo deve "
            "rever o SGQ a intervalos planeados para assegurar "
            "a sua pertinência, adequação e eficácia."
        )

        col_rv1, col_rv2 = st.columns([1, 1])

        with col_rv1:
            st.markdown("#### ⚙️ Parâmetros")

            ano_rev  = st.number_input(
                "Ano", min_value=2024,
                value=ano_atual, key="rev_ano"
            )
            sem_rev  = st.selectbox(
                "Semestre",
                ["1º Semestre","2º Semestre","Anual"],
                key="rev_sem"
            )
            elab_rev = st.text_input(
                "Elaborado por *",
                value=user_nome, key="rev_elab"
            )
            aprov_rev= st.text_input(
                "Aprovado por (Gestão de Topo) *",
                key="rev_aprov",
                placeholder="Ex: Diogo Correia"
            )

            st.markdown("---")
            st.markdown("#### 📝 Conteúdo das Secções")
            st.markdown(
                "<small style='color:#64748B;'>"
                "Preenche cada secção — os dados dos módulos "
                "são preenchidos automaticamente onde possível."
                "</small>",
                unsafe_allow_html=True
            )

            # Auto-preencher dados dos módulos
            # Auditorias
            n_aud_r = n_aud_ano
            n_nc_aud= 0
            if not aud_db.empty and 'NCs_Aber' in aud_db.columns:
                n_nc_aud = int(pd.to_numeric(
                    aud_db['NCs_Aber'], errors='coerce'
                ).fillna(0).sum())

            txt_aud_auto = (
                f"Realizadas {n_aud_r} auditoria(s) internas. "
                f"Total de NCs identificadas: {n_nc_aud}."
            )
            s_aud = st.text_area(
                "1. Resultados de Auditorias",
                value=txt_aud_auto,
                key="rev_aud", height=80
            )

            s_cli = st.text_area(
                "2. Retorno de Informação de Clientes",
                placeholder="Reclamações, satisfação, feedback...",
                key="rev_cli", height=80
            )

            txt_proc_auto = (
                f"Taxa de conformidade nas inspeções: "
                f"{taxa_conf:.0f}%. "
                f"NCs abertas: {nc_abertas}."
            )
            s_proc = st.text_area(
                "3. Desempenho de Processos",
                value=txt_proc_auto,
                key="rev_proc", height=80
            )

            txt_nc_auto = (
                f"{nc_abertas} NC(s) abertas. "
                f"Total registado: {len(nc_db) if not nc_db.empty else 0}."
            )
            s_ncs = st.text_area(
                "4. Não Conformidades e ACs",
                value=txt_nc_auto,
                key="rev_ncs", height=80
            )

            txt_obj_auto = (
                f"{n_obj_ok} de {n_obj_tot} objetivo(s) atingidos."
            )
            s_obj = st.text_area(
                "5. Objetivos da Qualidade",
                value=txt_obj_auto,
                key="rev_obj", height=80
            )

            s_forn = st.text_area(
                "6. Avaliação de Fornecedores",
                placeholder="Score médio, fornecedores qualificados...",
                key="rev_forn", height=80
            )

            txt_ris_auto = (
                f"{n_riscos_altos} risco(s) de score alto/crítico."
            )
            s_ris = st.text_area(
                "7. Gestão de Riscos",
                value=txt_ris_auto,
                key="rev_ris", height=80
            )

            s_rec = st.text_area(
                "8. Adequação de Recursos",
                placeholder="Recursos humanos, financeiros, "
                            "infraestrutura...",
                key="rev_rec", height=80
            )

            s_mel = st.text_area(
                "9. Decisões e Ações de Melhoria",
                placeholder="Decisões tomadas, ações definidas...",
                key="rev_mel", height=100
            )

        with col_rv2:
            st.markdown("#### 📊 Resumo Automático")

            # Dashboard indicadores
            indicadores_rev = [
                ("🔍 Auditorias Realizadas",
                 n_aud_r, f"de {n_aud_ano} planeadas",
                 "#3B82F6"),
                ("🔴 NCs Abertas",
                 nc_abertas, "devem ser 0",
                 "#10B981" if nc_abertas==0 else "#EF4444"),
                ("✅ Taxa Conformidade",
                 f"{taxa_conf:.0f}%", "objetivo ≥ 95%",
                 "#10B981" if taxa_conf>=95 else "#F59E0B"),
                ("🎯 Objetivos Atingidos",
                 f"{n_obj_ok}/{n_obj_tot}",
                 "do plano anual",
                 "#10B981" if n_obj_ok==n_obj_tot and n_obj_tot>0
                 else "#F59E0B"),
                ("⚠️ Riscos Altos",
                 n_riscos_altos,
                 "riscos score ≥ 12",
                 "#10B981" if n_riscos_altos==0 else "#EF4444"),
                ("🏭 Fornecedores Avaliados",
                 len(forn_aval_db),
                 "registos este período",
                 "#3B82F6"),
            ]

            cols_rev = st.columns(2)
            for i, (label,val,sub,cor) in enumerate(indicadores_rev):
                with cols_rev[i%2]:
                    st.markdown(
                        f"<div class='iso-card' "
                        f"style='border-top:3px solid {cor};"
                        f"text-align:center;'>"
                        f"<p style='color:#64748B;font-size:0.72rem;"
                        f"margin:0 0 4px;text-transform:uppercase;'>"
                        f"{label}</p>"
                        f"<b style='color:{cor};"
                        f"font-size:1.4rem;'>{val}</b><br>"
                        f"<small style='color:#64748B;'>{sub}</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

            st.markdown("---")

            # Gerar PDF
            if st.button(
                "📄 Gerar Revisão pela Gestão PDF",
                key="btn_rev_pdf",
                type="primary",
                use_container_width=True
            ):
                if not elab_rev.strip() or not aprov_rev.strip():
                    st.error(
                        "❌ Elaborado por e Aprovado por obrigatórios."
                    )
                else:
                    dados_rev = {
                        "elaborado_por": elab_rev,
                        "aprovado_por":  aprov_rev,
                        "auditorias":    s_aud,
                        "clientes":      s_cli,
                        "processos":     s_proc,
                        "ncs":           s_ncs,
                        "objetivos":     s_obj,
                        "fornecedores":  s_forn,
                        "riscos":        s_ris,
                        "recursos":      s_rec,
                        "melhorias":     s_mel,
                        "n_nc_aber":     nc_abertas,
                        "taxa_conf":     taxa_conf,
                        "obj_ating":     n_obj_ok,
                        "obj_total":     n_obj_tot,
                        "forn_qual":     len(forn_aval_db),
                        "forn_total":    len(forn_aval_db),
                        "aud_real":      n_aud_r,
                        "aud_plan":      max(n_aud_ano,1),
                    }
                    with st.spinner("A gerar documento..."):
                        pdf_rev = _gerar_pdf_revisao(
                            ano_rev, sem_rev, dados_rev, empresa
                        )
                    st.session_state['rev_pdf'] = pdf_rev
                    st.session_state['rev_pdf_nome'] = (
                        f"Revisao_Gestao_ISO9001_"
                        f"{ano_rev}_{sem_rev.replace(' ','')}.pdf"
                    )
                    st.success("✅ Documento gerado!")
                    st.rerun()

            if st.session_state.get('rev_pdf'):
                st.download_button(
                    "📥 Descarregar Revisão pela Gestão",
                    data=st.session_state['rev_pdf'],
                    file_name=st.session_state.get(
                        'rev_pdf_nome','revisao.pdf'
                    ),
                    mime="application/pdf",
                    key="dl_rev_pdf",
                    use_container_width=True,
                    type="primary"
                )

            # IA — análise do SGQ
            st.markdown("---")
            if st.button(
                "🤖 Análise IA do SGQ",
                key="btn_ia_rev",
                use_container_width=True
            ):
                api_key = os.environ.get("ANTHROPIC_API_KEY","")
                if api_key:
                    import anthropic
                    ctx = {
                        "nc_abertas":     nc_abertas,
                        "taxa_conf":      f"{taxa_conf:.0f}%",
                        "obj_atingidos":  f"{n_obj_ok}/{n_obj_tot}",
                        "riscos_altos":   n_riscos_altos,
                        "auditorias":     n_aud_r,
                        "empresa":        empresa.get('nome',''),
                        "setor":          "Instrumentação Industrial"
                    }
                    with st.spinner("🤖 A analisar o SGQ..."):
                        try:
                            client = anthropic.Anthropic(
                                api_key=api_key
                            )
                            resp = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=600,
                                messages=[{
                                    "role":"user",
                                    "content":(
                                        f"Sou responsável do SGQ de "
                                        f"uma PME portuguesa de "
                                        f"instrumentação industrial. "
                                        f"Dados actuais:\n"
                                        f"{json.dumps(ctx,ensure_ascii=False)}\n\n"
                                        f"Como consultor ISO 9001 "
                                        f"experiente:\n"
                                        f"1. Avaliação do estado "
                                        f"actual do SGQ (2 frases)\n"
                                        f"2. 3 pontos mais críticos "
                                        f"a resolver antes de uma "
                                        f"auditoria de certificação\n"
                                        f"3. Oportunidades de melhoria "
                                        f"imediatas\n"
                                        f"4. Probabilidade estimada de "
                                        f"certificação no estado actual\n"
                                        f"Máximo 5 parágrafos, "
                                        f"português de Portugal."
                                    )
                                }]
                            )
                            st.markdown(
                                f"<div style='background:rgba(59,130,246,0.08);"
                                f"border:1px solid #3B82F6;"
                                f"border-radius:12px;padding:16px;"
                                f"color:#E2E8F0;font-size:0.88rem;"
                                f"line-height:1.7;'>"
                                f"<b style='color:#3B82F6;'>🤖 Consultor ISO IA</b>"
                                f"<br><br>"
                                f"{resp.content[0].text.replace(chr(10),'<br>')}"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        except Exception as e:
                            st.error(f"❌ {e}")

    # ════════════════════════════════════════════════════════════════
    # TAB 6 — AVALIAÇÃO DE FORNECEDORES (Cláusula 8.4)
    # ════════════════════════════════════════════════════════════════
    with t_forn:
        st.markdown("### 🏭 Avaliação e Qualificação de Fornecedores")
        st.info(
            "ISO 9001:2015 Cláusula 8.4 — Controlar processos, "
            "produtos e serviços de fornecedores externos. "
            "Avaliar com base em critérios definidos."
        )

        col_ff2, col_fl2 = st.columns([1, 2])

        with col_ff2:
            st.markdown("#### ➕ Nova Avaliação")

            # Lista de fornecedores disponíveis
            forn_lista = []
            forn_db2 = _load("fornecedores.csv",["ID","Nome"])
            if not forn_db2.empty and 'Nome' in forn_db2.columns:
                forn_lista = forn_db2['Nome'].tolist()
            if not forn_lista:
                forn_lista = ["Fornecedor sem registo"]

            obras_db2 = _load("obras_lista.csv",["Obra","Ativa"])
            obras_ativas = obras_db2[
                obras_db2['Ativa']=='Ativa'
            ]['Obra'].tolist() if not obras_db2.empty else []

            with st.form("form_aval_forn"):
                fa_forn = st.selectbox(
                    "Fornecedor *", forn_lista, key="fa_forn"
                )
                fa_obra = st.selectbox(
                    "Obra / Contexto",
                    obras_ativas if obras_ativas else ["—"],
                    key="fa_obra"
                )
                fa_cat  = st.selectbox(
                    "Categoria",
                    ["Materiais","Ferramentas","EPIs",
                     "Equipamento","Serviços Especializados",
                     "Subempreitada","Outro"],
                    key="fa_cat"
                )

                st.markdown(
                    "<p style='color:#94A3B8;"
                    "font-size:0.8rem;margin:8px 0 4px;'>"
                    "Avaliação por critério (1=Muito Mau → 5=Excelente):"
                    "</p>",
                    unsafe_allow_html=True
                )

                criterios = [
                    ("Q_Qualidade",     "🎯 Qualidade do produto/serviço"),
                    ("Q_Prazo",         "⏱️ Cumprimento de prazos"),
                    ("Q_Preco",         "💰 Competitividade de preço"),
                    ("Q_Comunicacao",   "📞 Comunicação e suporte"),
                    ("Q_Documentacao",  "📋 Documentação e certificações"),
                ]
                scores_crit = {}
                for k, label in criterios:
                    scores_crit[k] = st.slider(
                        label, 1, 5, 3, key=f"fa_{k}"
                    )

                # Score automático (média ponderada)
                pesos = {
                    "Q_Qualidade":    0.35,
                    "Q_Prazo":        0.25,
                    "Q_Preco":        0.15,
                    "Q_Comunicacao":  0.15,
                    "Q_Documentacao": 0.10,
                }
                score_tot = round(
                    sum(
                        scores_crit[k] * pesos[k] * 20
                        for k in scores_crit
                    ), 1
                )
                class_forn = (
                    "✅ Qualificado"    if score_tot >= 70 else
                    "⚠️ Condicional"   if score_tot >= 50 else
                    "❌ Desqualificado"
                )
                cor_score_f = _cor_rag(score_tot)

                st.markdown(
                    f"<div style='background:{cor_score_f}18;"
                    f"border:1px solid {cor_score_f};"
                    f"border-radius:8px;padding:10px;"
                    f"text-align:center;margin:8px 0;'>"
                    f"<b style='color:{cor_score_f};"
                    f"font-size:1.3rem;'>"
                    f"Score: {score_tot}/100</b><br>"
                    f"<span style='color:{cor_score_f};'>"
                    f"{class_forn}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                fa_acao  = st.text_area(
                    "Ação / Observação", key="fa_acao",
                    placeholder="Ex: Manter como fornecedor aprovado..."
                )
                fa_notas = st.text_area("Notas", key="fa_notas")

                if st.form_submit_button(
                    "💾 Guardar Avaliação",
                    use_container_width=True, type="primary"
                ):
                    nova_fa = pd.DataFrame([{
                        "ID":            str(uuid.uuid4())[:8].upper(),
                        "Fornecedor":    fa_forn,
                        "Data_Aval":     hoje.strftime("%d/%m/%Y"),
                        "Obra":          fa_obra,
                        "Categoria":     fa_cat,
                        **scores_crit,
                        "Score_Total":   score_tot,
                        "Classificacao": class_forn,
                        "Acao":          fa_acao.strip(),
                        "Avaliado_Por":  user_nome,
                        "Notas":         fa_notas.strip()
                    }])
                    upd_fa = pd.concat(
                        [forn_aval_db, nova_fa], ignore_index=True
                    ) if not forn_aval_db.empty else nova_fa
                    save_db(upd_fa,"iso_fornecedores_aval.csv")
                    log_audit(
                        usuario=user_nome,
                        acao="AVALIAR_FORNECEDOR_ISO",
                        tabela="iso_fornecedores_aval.csv",
                        registro_id=nova_fa['ID'].iloc[0],
                        detalhes=(
                            f"{fa_forn} | Score: {score_tot} | "
                            f"{class_forn}"
                        ),
                        ip=""
                    )
                    inv("iso_fornecedores_aval.csv")
                    st.success(
                        f"✅ {fa_forn} avaliado! "
                        f"Score: {score_tot}/100 — {class_forn}"
                    )
                    st.rerun()

        with col_fl2:
            st.markdown("#### 📊 Painel de Fornecedores")

            fig_forn = _grafico_fornecedores_score(forn_aval_db)
            if fig_forn:
                st.plotly_chart(fig_forn, use_container_width=True)

            if forn_aval_db.empty:
                st.info("📋 Sem avaliações registadas.")
            else:
                # Última avaliação por fornecedor
                forn_aval_db['Score_N'] = pd.to_numeric(
                    forn_aval_db.get('Score_Total',0),
                    errors='coerce'
                ).fillna(0)

                ultimo_por_forn = forn_aval_db.sort_values(
                    'Data_Aval', ascending=False
                ).drop_duplicates('Fornecedor')

                st.markdown("#### 📋 Estado Actual dos Fornecedores")

                # KPIs
                n_qual = len(ultimo_por_forn[
                    ultimo_por_forn['Score_N'] >= 70
                ])
                n_cond = len(ultimo_por_forn[
                    (ultimo_por_forn['Score_N'] >= 50) &
                    (ultimo_por_forn['Score_N'] < 70)
                ])
                n_desq = len(ultimo_por_forn[
                    ultimo_por_forn['Score_N'] < 50
                ])

                c1,c2,c3 = st.columns(3)
                with c1:
                    st.metric("✅ Qualificados", n_qual)
                with c2:
                    st.metric("⚠️ Condicionais", n_cond)
                with c3:
                    st.metric("❌ Desqualificados", n_desq)

                # Lista
                for _, fa in ultimo_por_forn.sort_values(
                    'Score_N', ascending=False
                ).iterrows():
                    score_f = float(fa.get('Score_N',0))
                    cls_f   = fa.get('Classificacao','')
                    cor_f   = _cor_rag(score_f)

                    st.markdown(
                        f"<div class='iso-card' "
                        f"style='border-left:4px solid {cor_f};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;'>"
                        f"{fa.get('Fornecedor','')}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"🏷️ {fa.get('Categoria','')} · "
                        f"🏗️ {fa.get('Obra','')} · "
                        f"📅 {fa.get('Data_Aval','')}</small>"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<b style='color:{cor_f};"
                        f"font-size:1.1rem;'>{score_f:.0f}/100</b><br>"
                        f"<small style='color:{cor_f};'>{cls_f}</small>"
                        f"</div></div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                st.markdown("---")

                # Tabela completa + export
                cols_fa = [c for c in [
                    'Fornecedor','Data_Aval','Obra','Categoria',
                    'Score_Total','Classificacao','Avaliado_Por'
                ] if c in forn_aval_db.columns]
                st.dataframe(
                    forn_aval_db[cols_fa].sort_values(
                        'Data_Aval', ascending=False
                    ),
                    use_container_width=True,
                    hide_index=True
                )

                csv_fa = forn_aval_db[cols_fa].to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    "📥 Exportar Avaliações",
                    data=csv_fa.encode('utf-8-sig'),
                    file_name="avaliacao_fornecedores_iso.csv",
                    mime="text/csv",
                    key="dl_fa"
                )

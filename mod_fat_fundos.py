"""
GESTNOW v3 — mod_fat_fundos.py
Passo 9 — Fundos Europeus & Candidaturas
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
from core import save_db, inv, load_db, log_audit

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)

# ─────────────────────────────────────────────────────────────────
# BASE DE DADOS DE FUNDOS EUROPEUS — PORTUGAL 2024-2027
# ─────────────────────────────────────────────────────────────────

FUNDOS_DB = [
    # ── PRR ──────────────────────────────────────────────────────
    {
        "id":           "PRR-C15-I01",
        "nome":         "PRR — Capitalização e Inovação Empresarial",
        "programa":     "PRR",
        "componente":   "C15 — Empresas e Inovação",
        "tipo":         "Subvenção não reembolsável",
        "valor_min":    25000,
        "valor_max":    2500000,
        "pct_max":      80,
        "regioes":      ["Norte","Centro","Alentejo","Algarve","Lisboa"],
        "setores_ok":   ["Construção","Instrumentação","Indústria",
                         "Serviços Especializados"],
        "n_trabalhadores_min": 1,
        "n_trabalhadores_max": 250,
        "tipos_invest": ["Equipamento","Digital","Inovação",
                         "Eficiência Energética"],
        "prazo_decisao":"45-90 dias",
        "entidade":     "IAPMEI / Agência para a Competitividade",
        "url":          "www.iapmei.pt/prr",
        "contacto":     "808 200 115",
        "descricao":    "Apoio à capitalização, inovação produtiva "
                        "e digitalização de PMEs. Inclui compra "
                        "de equipamento especializado, software "
                        "de gestão e certificações.",
        "documentos":   ["Candidatura online IAPMEI","Balanço 3 anos",
                         "Plano de Negócios","Orçamentos investimento",
                         "Certidões AT e SS","Alvará/licenças"],
        "cor":          "#3B82F6",
        "elegibilidade_score": 0  # calculado dinamicamente
    },
    {
        "id":           "PRR-C16-I02",
        "nome":         "PRR — Eficiência Energética Empresas",
        "programa":     "PRR",
        "componente":   "C16 — Descarbonização",
        "tipo":         "Subvenção não reembolsável",
        "valor_min":    10000,
        "valor_max":    1000000,
        "pct_max":      70,
        "regioes":      ["Norte","Centro","Alentejo","Algarve",
                         "Lisboa","Açores","Madeira"],
        "setores_ok":   ["Construção","Indústria","Serviços"],
        "n_trabalhadores_min": 1,
        "n_trabalhadores_max": 500,
        "tipos_invest": ["Eficiência Energética","Energias Renováveis",
                         "Frota Elétrica","Mobilidade"],
        "prazo_decisao":"30-60 dias",
        "entidade":     "ADENE / DGEG",
        "url":          "www.adene.pt",
        "contacto":     "213 229 890",
        "descricao":    "Apoio à redução do consumo energético "
                        "em empresas. Relevante para frota elétrica, "
                        "painéis solares em instalações "
                        "e sistemas de monitorização.",
        "documentos":   ["Auditoria energética","Orçamentos",
                         "Certidões AT e SS","Candidatura DGEG"],
        "cor":          "#10B981",
        "elegibilidade_score": 0
    },
    # ── PT2030 ───────────────────────────────────────────────────
    {
        "id":           "PT2030-COMP-01",
        "nome":         "COMPETE 2030 — Inovação Produtiva",
        "programa":     "PT2030",
        "componente":   "COMPETE 2030",
        "tipo":         "Subvenção não reembolsável",
        "valor_min":    50000,
        "valor_max":    5000000,
        "pct_max":      60,
        "regioes":      ["Norte","Centro","Alentejo","Algarve"],
        "setores_ok":   ["Indústria","Instrumentação",
                         "Construção Especializada",
                         "Engenharia","Tecnologia"],
        "n_trabalhadores_min": 5,
        "n_trabalhadores_max": 250,
        "tipos_invest": ["Equipamento Industrial","I&D",
                         "Qualidade e Certificação","Digital"],
        "prazo_decisao":"60-120 dias",
        "entidade":     "IAPMEI / CCDR",
        "url":          "www.compete2030.pt",
        "contacto":     "808 200 115",
        "descricao":    "Apoio a projetos de inovação produtiva, "
                        "qualificação e internacionalização de PMEs "
                        "industriais. Ideal para compra de "
                        "equipamento de instrumentação avançado.",
        "documentos":   ["Candidatura IAPMEI","Business Plan",
                         "Orçamentos detalhados","Balanços 3 anos",
                         "Certidões fiscais","Registo empresarial"],
        "cor":          "#8B5CF6",
        "elegibilidade_score": 0
    },
    {
        "id":           "PT2030-QUAL-01",
        "nome":         "PT2030 — Qualificação PME",
        "programa":     "PT2030",
        "componente":   "Qualificação e Internacionalização",
        "tipo":         "Subvenção não reembolsável",
        "valor_min":    15000,
        "valor_max":    500000,
        "pct_max":      75,
        "regioes":      ["Norte","Centro","Alentejo","Algarve",
                         "Lisboa","Açores","Madeira"],
        "setores_ok":   ["Todos os setores"],
        "n_trabalhadores_min": 1,
        "n_trabalhadores_max": 250,
        "tipos_invest": ["Certificações ISO","Software Gestão",
                         "Formação","Marketing","Internacionalização"],
        "prazo_decisao":"30-60 dias",
        "entidade":     "IAPMEI / AICEP",
        "url":          "www.iapmei.pt/pt2030",
        "contacto":     "808 200 115",
        "descricao":    "Apoio à qualificação empresarial: "
                        "certificações ISO 9001, OHSAS 18001, "
                        "software ERP/gestão, formação de "
                        "colaboradores. Muito acessível para PMEs.",
        "documentos":   ["Candidatura simplificada IAPMEI",
                         "Certidões fiscais","Orçamentos"],
        "cor":          "#F59E0B",
        "elegibilidade_score": 0
    },
    # ── FORMAÇÃO ─────────────────────────────────────────────────
    {
        "id":           "IEFP-FORM-01",
        "nome":         "IEFP — Apoios à Formação Profissional",
        "programa":     "FSE+",
        "componente":   "Fundo Social Europeu",
        "tipo":         "Subvenção (formação paga)",
        "valor_min":    1000,
        "valor_max":    200000,
        "pct_max":      100,
        "regioes":      ["Todas as regiões"],
        "setores_ok":   ["Todos os setores"],
        "n_trabalhadores_min": 1,
        "n_trabalhadores_max": 9999,
        "tipos_invest": ["Formação Técnica","Segurança no Trabalho",
                         "Gestão","Digitalização","Línguas"],
        "prazo_decisao":"15-30 dias",
        "entidade":     "IEFP",
        "url":          "www.iefp.pt/formacao-empresas",
        "contacto":     "300 010 001",
        "descricao":    "Financiamento de formação profissional "
                        "para trabalhadores. Inclui cursos técnicos "
                        "de instrumentação, calibração, HSE, "
                        "gestão de projetos. Até 100% comparticipado.",
        "documentos":   ["Pedido IEFP","Lista trabalhadores",
                         "Programa formação","Certidões SS"],
        "cor":          "#06B6D4",
        "elegibilidade_score": 0
    },
    # ── IAPMEI LINHAS ────────────────────────────────────────────
    {
        "id":           "IAPMEI-PME-CRESC",
        "nome":         "Linha PME Crescimento 2024",
        "programa":     "IAPMEI",
        "componente":   "Linhas de Crédito Bonificadas",
        "tipo":         "Crédito bonificado (reembolsável)",
        "valor_min":    25000,
        "valor_max":    1500000,
        "pct_max":      100,
        "regioes":      ["Todas as regiões"],
        "setores_ok":   ["Todos os setores"],
        "n_trabalhadores_min": 1,
        "n_trabalhadores_max": 250,
        "tipos_invest": ["Capital de Maneio","Investimento",
                         "Expansão","Tesouraria"],
        "prazo_decisao":"7-15 dias",
        "entidade":     "IAPMEI + Bancos + Garantia Mútua",
        "url":          "www.spgm.pt/pme-crescimento",
        "contacto":     "Via banco habitual",
        "descricao":    "Linha de crédito com garantia mútua "
                        "(SPGM/Garval/Norgarante). "
                        "Taxa de juro bonificada, carência 12m, "
                        "prazo até 7 anos. Sem colateral imobiliário.",
        "documentos":   ["Pedido ao banco","Balanços 2 anos",
                         "Declarações AT e SS","Plano financeiro"],
        "cor":          "#10B981",
        "elegibilidade_score": 0
    },
    # ── SIFIDE ───────────────────────────────────────────────────
    {
        "id":           "SIFIDE-II",
        "nome":         "SIFIDE II — Sistema de Incentivos Fiscais I&D",
        "programa":     "Benefícios Fiscais",
        "componente":   "IRC — Dedução fiscal",
        "tipo":         "Benefício fiscal (dedução IRC)",
        "valor_min":    5000,
        "valor_max":    9999999,
        "pct_max":      82.5,
        "regioes":      ["Todas as regiões"],
        "setores_ok":   ["Todos os setores com I&D"],
        "n_trabalhadores_min": 1,
        "n_trabalhadores_max": 9999,
        "tipos_invest": ["Investigação & Desenvolvimento",
                         "Inovação","Protótipos","Software"],
        "prazo_decisao":"Declaração IRC anual",
        "entidade":     "AT — Autoridade Tributária",
        "url":          "info.portaldasfinancas.gov.pt/sifide",
        "contacto":     "217 206 707",
        "descricao":    "Dedução fiscal de 32.5% a 82.5% das "
                        "despesas em I&D. Se a empresa desenvolve "
                        "software de gestão (GESTNOW), "
                        "pode ser elegível. Consultar TOC.",
        "documentos":   ["Declaração IRC","Mapa despesas I&D",
                         "Relatório técnico","Candidatura FCT"],
        "cor":          "#EF4444",
        "elegibilidade_score": 0
    },
    # ── RFAI ─────────────────────────────────────────────────────
    {
        "id":           "RFAI-2024",
        "nome":         "RFAI — Regime Fiscal Apoio Investimento",
        "programa":     "Benefícios Fiscais",
        "componente":   "IRC — Dedução fiscal",
        "tipo":         "Benefício fiscal (dedução IRC)",
        "valor_min":    5000,
        "valor_max":    9999999,
        "pct_max":      25,
        "regioes":      ["Norte","Centro","Alentejo","Algarve",
                         "Açores","Madeira"],
        "setores_ok":   ["Indústria","Construção","Serviços"],
        "n_trabalhadores_min": 1,
        "n_trabalhadores_max": 9999,
        "tipos_invest": ["Equipamento","Instalações","Software",
                         "Ativos Tangíveis"],
        "prazo_decisao":"Declaração IRC anual",
        "entidade":     "AT — Autoridade Tributária",
        "url":          "info.portaldasfinancas.gov.pt",
        "contacto":     "217 206 707",
        "descricao":    "Dedução de 25% do investimento em ativos "
                        "ao IRC. Para equipamento novo, software, "
                        "obras de melhoria em instalações. "
                        "Simples de aplicar com o TOC.",
        "documentos":   ["Declaração IRC","Faturas investimento",
                         "Mapa de ativos"],
        "cor":          "#F97316",
        "elegibilidade_score": 0
    },
]

# ─────────────────────────────────────────────────────────────────
# MOTOR DE MATCHING
# ─────────────────────────────────────────────────────────────────

def _calcular_elegibilidade(fundo: dict,
                             perfil: dict) -> tuple[int, list]:
    """
    Calcula score de elegibilidade 0-100 e lista de motivos.
    """
    score    = 0
    motivos  = []
    alertas  = []

    n_trab   = perfil.get('n_trabalhadores', 10)
    regiao   = perfil.get('regiao', 'Norte')
    setor    = perfil.get('setor', 'Instrumentação')
    vol_neg  = perfil.get('volume_negocios', 500000)
    tipo_inv = perfil.get('tipo_investimento', [])
    anos_act = perfil.get('anos_atividade', 5)
    tem_dividas = perfil.get('tem_dividas_fiscais', False)

    # 1. Nº trabalhadores (0-20 pts)
    n_min = fundo.get('n_trabalhadores_min', 0)
    n_max = fundo.get('n_trabalhadores_max', 9999)
    if n_min <= n_trab <= n_max:
        score += 20
        motivos.append("✅ Dimensão da empresa elegível")
    else:
        alertas.append(
            f"❌ Nº trabalhadores ({n_trab}) fora do intervalo "
            f"({n_min}-{n_max})"
        )

    # 2. Região (0-20 pts)
    regioes_ok = fundo.get('regioes', [])
    if regiao in regioes_ok or "Todas as regiões" in regioes_ok:
        score += 20
        motivos.append(f"✅ Região {regiao} elegível")
    else:
        alertas.append(
            f"❌ Região {regiao} não está na lista elegível"
        )

    # 3. Setor (0-20 pts)
    setores_ok = fundo.get('setores_ok', [])
    if any(s in setor or setor in s
           for s in setores_ok) or \
       "Todos os setores" in setores_ok:
        score += 20
        motivos.append(f"✅ Setor {setor} elegível")
    else:
        alertas.append(
            f"❌ Setor {setor} pode não ser elegível"
        )

    # 4. Tipo de investimento (0-20 pts)
    tipos_fundo = fundo.get('tipos_invest', [])
    matches = [
        t for t in tipo_inv
        if any(t in tf or tf in t for tf in tipos_fundo)
    ]
    if matches:
        score += 20
        motivos.append(
            f"✅ Investimento compatível: "
            f"{', '.join(matches[:2])}"
        )
    elif not tipo_inv:
        score += 10  # neutro se não especificado
    else:
        alertas.append(
            "⚠️ Tipo de investimento pode não ser elegível"
        )

    # 5. Situação fiscal (0-10 pts)
    if not tem_dividas:
        score += 10
        motivos.append("✅ Sem dívidas fiscais ou à SS")
    else:
        alertas.append(
            "❌ Dívidas fiscais/SS impedem candidatura"
        )

    # 6. Anos de atividade (0-10 pts)
    if anos_act >= 3:
        score += 10
        motivos.append(f"✅ {anos_act} anos de atividade")
    elif anos_act >= 1:
        score += 5
        alertas.append(
            "⚠️ Menos de 3 anos — verificar elegibilidade"
        )
    else:
        alertas.append("❌ Empresa em início de atividade")

    return score, motivos + alertas


def _calcular_apoio(valor_invest: float,
                    pct_max: float,
                    tipo: str) -> dict:
    """Calcula o valor de apoio esperado."""
    apoio_max = round(valor_invest * pct_max / 100, 2)
    contrapartida = round(valor_invest - apoio_max, 2)

    return {
        "valor_investimento": valor_invest,
        "pct_apoio":          pct_max,
        "apoio_max":          apoio_max,
        "contrapartida":      contrapartida,
        "tipo":               tipo,
        "reembolsavel":       "reembolsável" in tipo.lower()
    }


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_radar_elegibilidade(fundos_scores: list):
    """Radar dos fundos mais elegíveis."""
    if not fundos_scores:
        return None

    top5 = sorted(
        fundos_scores, key=lambda x: x[1], reverse=True
    )[:5]
    nomes  = [f[0][:25] for f in top5]
    scores = [f[1]       for f in top5]

    fig = go.Figure(go.Bar(
        x=scores, y=nomes,
        orientation='h',
        marker_color=[
            '#10B981' if s >= 70
            else '#F59E0B' if s >= 40
            else '#EF4444'
            for s in scores
        ],
        text=[f"{s}%" for s in scores],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':11},
        hovertemplate='%{y}<br>Elegibilidade: %{x}%<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Top Fundos por Elegibilidade',
               'font':{'color':'#F1F5F9'}},
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'range':[0,120],
               'ticksuffix':'%'},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=200,r=60),
        showlegend=False
    )
    return fig


def _grafico_timeline_candidaturas(cand_db):
    """Gantt das candidaturas por estado."""
    if cand_db.empty:
        return None

    estados_cor = {
        'Identificado':     '#64748B',
        'A Preparar':       '#F59E0B',
        'Submetido':        '#3B82F6',
        'Em Análise':       '#8B5CF6',
        'Aprovado':         '#10B981',
        'Rejeitado':        '#EF4444',
        'Em Execução':      '#06B6D4',
        'Concluído':        '#94A3B8',
    }

    fig = go.Figure()
    for i, (_, row) in enumerate(cand_db.iterrows()):
        try:
            ini = datetime.strptime(
                row.get('Data_Inicio','01/01/2025'),
                "%d/%m/%Y"
            )
            fim_str = row.get('Data_Fim','')
            if fim_str:
                fim = datetime.strptime(fim_str, "%d/%m/%Y")
            else:
                fim = ini + timedelta(days=90)
        except:
            continue

        est = row.get('Estado','')
        cor = estados_cor.get(est,'#6B7280')
        val = float(row.get('Valor_Apoio',0) or 0)

        fig.add_trace(go.Scatter(
            x=[ini, fim],
            y=[row.get('Fundo','')[:25],
               row.get('Fundo','')[:25]],
            mode='lines',
            line={'color':cor,'width':20},
            name=est,
            hovertemplate=(
                f"<b>{row.get('Fundo','')}</b><br>"
                f"Estado: {est}<br>"
                f"Apoio: €{val:,.2f}<br>"
                f"{ini.strftime('%d/%m/%Y')} → "
                f"{fim.strftime('%d/%m/%Y')}"
                f"<extra></extra>"
            ),
            showlegend=False
        ))

    fig.add_vline(
        x=datetime.now(),
        line_dash="dash",
        line_color="#F1F5F9",
        line_width=1,
        annotation_text="Hoje",
        annotation_font_color="#94A3B8"
    )

    fig.update_layout(
        title={'text':'Timeline de Candidaturas',
               'font':{'color':'#F1F5F9'}},
        height=max(200, len(cand_db)*60 + 80),
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


def _grafico_apoio_donut(fundos_elegíveis: list,
                          valor_invest: float):
    """Donut com potencial de apoio por fundo."""
    if not fundos_elegíveis:
        return None

    top = sorted(
        fundos_elegíveis, key=lambda x: x['score'], reverse=True
    )[:5]

    labels = [f['nome'][:30] for f in top]
    values = [
        round(valor_invest * f.get('pct_max', 50) / 100, 0)
        for f in top
    ]
    cores = [f['cor'] for f in top]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.5,
        marker={'colors':cores,
                'line':{'color':'#0F172A','width':2}},
        textfont={'color':'#F1F5F9','size':9},
        hovertemplate='%{label}<br>€%{value:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Potencial de Apoio por Fundo',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'},'x':1.0},
        margin=dict(t=40,b=10,l=10,r=10),
        annotations=[{
            'text': f"€{sum(values):,.0f}",
            'x':0.5,'y':0.5,
            'font_size':13,'font_color':'#F1F5F9',
            'showarrow':False
        }]
    )
    return fig


def _grafico_calendario_fundos(cand_db):
    """Scatter de prazos de candidatura."""
    if cand_db.empty:
        return None

    prazos = []
    if 'Prazo_Candidatura' in cand_db.columns:
        for _, row in cand_db.iterrows():
            try:
                d = datetime.strptime(
                    row['Prazo_Candidatura'], "%d/%m/%Y"
                ).date()
                dias = (d - date.today()).days
                prazos.append({
                    'nome':  row.get('Fundo','')[:20],
                    'data':  d,
                    'dias':  dias,
                    'val':   float(row.get('Valor_Apoio',0) or 0),
                    'est':   row.get('Estado','')
                })
            except:
                pass

    if not prazos:
        return None

    prazos.sort(key=lambda x: x['data'])
    cores = [
        '#EF4444' if p['dias'] < 30
        else '#F59E0B' if p['dias'] < 60
        else '#10B981'
        for p in prazos
    ]

    fig = go.Figure(go.Scatter(
        x=[p['data'] for p in prazos],
        y=[p['val']  for p in prazos],
        mode='markers+text',
        text=[p['nome'] for p in prazos],
        textposition='top center',
        textfont={'color':'#F1F5F9','size':9},
        marker={
            'size':  [max(p['val']/10000, 12) for p in prazos],
            'color': cores,
            'line':  {'color':'#F1F5F9','width':1}
        },
        hovertemplate=(
            '<b>%{text}</b><br>'
            'Prazo: %{x|%d/%m/%Y}<br>'
            'Apoio: €%{y:,.0f}<extra></extra>'
        )
    ))
    fig.add_vline(
        x=datetime.now(),
        line_dash="dash",
        line_color="#64748B", line_width=1,
        annotation_text="Hoje",
        annotation_font_color="#94A3B8"
    )
    fig.update_layout(
        title={'text':'Prazos de Candidatura',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=60,r=10),
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF DOSSIER DE CANDIDATURA
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_candidatura(fundo: dict,
                            apoio: dict,
                            perfil: dict,
                            motivos: list,
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
        fontSize=9, spaceAfter=3
    )

    # Header
    story.append(Paragraph(
        f"FICHA DE CANDIDATURA — {fundo['nome'].upper()}",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=14, fontName='Helvetica-Bold',
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

    # Dados do fundo
    story.append(Paragraph("<b>DADOS DO FUNDO</b>", bold_s))
    fundo_data = [
        ["Programa",     fundo.get('programa','')],
        ["Fundo",        fundo.get('nome','')],
        ["Tipo",         fundo.get('tipo','')],
        ["Entidade",     fundo.get('entidade','')],
        ["% Apoio Máx.", f"{fundo.get('pct_max',0)}%"],
        ["Valor Máximo", f"€{fundo.get('valor_max',0):,.0f}"],
        ["Contacto",     fundo.get('contacto','')],
        ["URL",          fundo.get('url','')],
    ]
    ft = Table(fundo_data, colWidths=[5*cm, 12*cm])
    ft.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('FONTNAME',    (0,0),(0,-1),  'Helvetica-Bold'),
        ('BACKGROUND',  (0,0),(0,-1),  colors.HexColor('#F8FAFC')),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(ft)
    story.append(Spacer(1, 0.4*cm))

    # Dados da empresa
    story.append(Paragraph("<b>PERFIL DA EMPRESA</b>", bold_s))
    emp_data = [
        ["Nome",            empresa.get('nome','')],
        ["NIF",             empresa.get('nif','')],
        ["Setor",           perfil.get('setor','')],
        ["Região",          perfil.get('regiao','')],
        ["Nº Trabalhadores",str(perfil.get('n_trabalhadores',''))],
        ["Vol. Negócios",   f"€{perfil.get('volume_negocios',0):,.0f}"],
        ["Anos Atividade",  str(perfil.get('anos_atividade',''))],
    ]
    et = Table(emp_data, colWidths=[5*cm, 12*cm])
    et.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('FONTNAME',    (0,0),(0,-1),  'Helvetica-Bold'),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(et)
    story.append(Spacer(1, 0.4*cm))

    # Simulação de apoio
    story.append(Paragraph("<b>SIMULAÇÃO DE APOIO</b>", bold_s))
    ap_data = [
        ["Investimento Previsto",
         f"€{apoio['valor_investimento']:,.2f}"],
        ["% de Apoio",
         f"{apoio['pct_apoio']:.0f}%"],
        ["Apoio Estimado (Fundo Perdido/Crédito)",
         f"€{apoio['apoio_max']:,.2f}"],
        ["Contrapartida Empresa",
         f"€{apoio['contrapartida']:,.2f}"],
        ["Tipo de Apoio",
         apoio['tipo']],
    ]
    at = Table(ap_data, colWidths=[8*cm, 9*cm])
    at.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('FONTNAME',    (0,-1),(-1,-1),'Helvetica-Bold'),
        ('BACKGROUND',  (0,-1),(-1,-1),colors.HexColor('#EFF6FF')),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(at)
    story.append(Spacer(1, 0.4*cm))

    # Elegibilidade
    story.append(Paragraph("<b>ANÁLISE DE ELEGIBILIDADE</b>", bold_s))
    for m in motivos:
        story.append(Paragraph(m, normal_s))
    story.append(Spacer(1, 0.3*cm))

    # Documentos necessários
    story.append(Paragraph("<b>DOCUMENTOS NECESSÁRIOS</b>", bold_s))
    docs = fundo.get('documentos', [])
    for i, doc in enumerate(docs, 1):
        story.append(Paragraph(f"{i}. {doc}", normal_s))
    story.append(Spacer(1, 0.3*cm))

    # Próximos passos
    story.append(Paragraph("<b>PRÓXIMOS PASSOS</b>", bold_s))
    passos = [
        f"1. Contactar {fundo.get('entidade','')} "
        f"({fundo.get('contacto','')})",
        "2. Obter certidões fiscais e SS atualizadas",
        "3. Preparar plano de negócios e orçamentos",
        f"4. Submeter candidatura via {fundo.get('url','')}",
        "5. Acompanhar processo no portal do programa",
    ]
    for passo in passos:
        story.append(Paragraph(passo, normal_s))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
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
# PESQUISA IA DE AVISOS ABERTOS
# ─────────────────────────────────────────────────────────────────

def _pesquisar_avisos_ia(perfil: dict) -> str:
    """Usa IA para pesquisar avisos abertos relevantes."""
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return "❌ API key não configurada."

        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""Sou gestor de uma PME portuguesa de instrumentação industrial 
e construção especializada com o seguinte perfil:
- Setor: {perfil.get('setor','Instrumentação Industrial')}
- Região: {perfil.get('regiao','Norte')}
- Nº trabalhadores: {perfil.get('n_trabalhadores',15)}
- Volume negócios: €{perfil.get('volume_negocios',800000):,.0f}/ano
- Anos atividade: {perfil.get('anos_atividade',5)}
- Investimento previsto: {perfil.get('tipo_investimento',['Equipamento'])}

Com base neste perfil, indica-me:
1. Os 3 fundos/apoios europeus mais relevantes disponíveis 
   em Portugal em 2025-2026
2. Para cada um: nome, entidade gestora, % de apoio, 
   valor máximo e prazo estimado
3. O que devo fazer ESTA SEMANA para começar a candidatura
4. Qualquer aviso aberto urgente que não deva perder

Responde em português, de forma prática e direta. 
Máximo 6 parágrafos."""

        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=700,
            messages=[{"role":"user","content":prompt}]
        )
        return resp.content[0].text

    except Exception as e:
        return f"❌ Erro: {e}"


def _gerar_plano_candidatura_ia(fundo: dict,
                                 perfil: dict,
                                 empresa: dict) -> str:
    """Gera plano detalhado de candidatura com IA."""
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return "❌ API key não configurada."

        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""Preciso de candidatar a empresa {empresa.get('nome','')} 
(NIF: {empresa.get('nif','')}) ao seguinte fundo:

FUNDO: {fundo['nome']}
Programa: {fundo['programa']}
Tipo: {fundo['tipo']}
% Apoio: {fundo['pct_max']}%
Entidade: {fundo['entidade']}

PERFIL EMPRESA:
- Setor: {perfil.get('setor','Instrumentação')}
- Região: {perfil.get('regiao','Norte')}
- Trabalhadores: {perfil.get('n_trabalhadores',15)}
- Volume negócios: €{perfil.get('volume_negocios',800000):,.0f}
- Investimento previsto: €{perfil.get('valor_investimento',100000):,.0f}
- Tipo investimento: {perfil.get('tipo_investimento',['Equipamento'])}

Cria um plano de candidatura com:
1. Pontos fortes desta candidatura (o que joga a favor)
2. Pontos fracos / riscos (o que pode impedir aprovação)
3. Checklist de 8 documentos prioritários a preparar
4. Argumentário para a memória descritiva (3 parágrafos)
5. Timeline realista em semanas

Tom profissional, prático, em português de Portugal."""

        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role":"user","content":prompt}]
        )
        return resp.content[0].text

    except Exception as e:
        return f"❌ Erro: {e}"


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_fundos(*_):
    """Módulo Fundos Europeus & Candidaturas."""

    # ── Carregar dados ────────────────────────────────────────────
    cand_db = _load("fundos_candidaturas.csv", [
        "ID","Fundo","Programa","Data_Inicio","Prazo_Candidatura",
        "Data_Fim","Valor_Investimento","Valor_Apoio","Pct_Apoio",
        "Estado","Notas","Responsavel","Documentos_OK"
    ])

    try:
        from mod_admin_diarias import _get_config_empresa
        empresa = _get_config_empresa()
    except:
        empresa = {
            "nome":"Correia Plácido e Sousa, Lda.",
            "nif":"517182718",
            "morada":"Zona Industrial de Seia"
        }

    user_nome = st.session_state.get('user','Admin')
    hoje      = date.today()

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .fundo-card {
        background:#1E293B; border-radius:12px;
        padding:16px; margin-bottom:10px;
        border-left:5px solid #3B82F6;
        transition:transform 0.15s;
    }
    .fundo-card:hover { transform:translateX(3px); }
    .cand-card {
        background:#1E293B; border-radius:10px;
        padding:14px; margin-bottom:8px;
        border-left:4px solid;
    }
    .badge-fundo {
        display:inline-block; padding:3px 10px;
        border-radius:20px; font-size:0.72rem; font-weight:700;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────
    n_cand   = len(cand_db) if not cand_db.empty else 0
    n_ativas = len(cand_db[
        ~cand_db.get('Estado','').isin(['Concluído','Rejeitado'])
    ]) if not cand_db.empty and 'Estado' in cand_db.columns \
      else 0
    val_aprov = pd.to_numeric(
        cand_db[
            cand_db.get('Estado','') == 'Aprovado'
        ].get('Valor_Apoio',0) if not cand_db.empty and
        'Estado' in cand_db.columns
        else pd.Series(),
        errors='coerce'
    ).fillna(0).sum()
    val_pend = pd.to_numeric(
        cand_db[
            cand_db.get('Estado','') == 'Submetido'
        ].get('Valor_Apoio',0) if not cand_db.empty and
        'Estado' in cand_db.columns
        else pd.Series(),
        errors='coerce'
    ).fillna(0).sum()

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("📋 Candidaturas",    n_cand)
    with c2: st.metric("🔄 Ativas",           n_ativas)
    with c3: st.metric("✅ Aprovado",          f"€{val_aprov:,.2f}")
    with c4: st.metric("⏳ Submetido/Análise", f"€{val_pend:,.2f}")

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_match, t_calc, t_fundos,
     t_cand, t_ia, t_calendario) = st.tabs([
        "🎯 Matcher",
        "💰 Calculadora",
        "📚 Fundos Disponíveis",
        "📋 Gestão Candidaturas",
        "🤖 IA Consultora",
        "📅 Calendário",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — MATCHER DE ELEGIBILIDADE
    # ════════════════════════════════════════════════════════════════
    with t_match:
        st.markdown("### 🎯 Matcher de Elegibilidade")
        st.info(
            "Preenche o perfil da empresa e o sistema "
            "identifica automaticamente os fundos mais adequados."
        )

        col_perf, col_res = st.columns([1, 2])

        with col_perf:
            st.markdown("#### 🏢 Perfil da Empresa")

            m_setor = st.selectbox(
                "Setor de atividade",
                ["Instrumentação Industrial",
                 "Construção Especializada",
                 "Engenharia e Manutenção",
                 "Indústria",
                 "Serviços Técnicos",
                 "Outro"],
                key="m_setor"
            )
            m_regiao = st.selectbox(
                "Região",
                ["Norte","Centro","Lisboa","Alentejo",
                 "Algarve","Açores","Madeira"],
                key="m_regiao"
            )
            m_n_trab = st.number_input(
                "Nº de trabalhadores",
                min_value=1, value=15,
                key="m_n_trab"
            )
            m_vol = st.number_input(
                "Volume de negócios anual (€)",
                min_value=0.0, value=800000.0,
                step=50000.0, key="m_vol"
            )
            m_anos = st.number_input(
                "Anos de atividade",
                min_value=0, value=5,
                key="m_anos"
            )
            m_dividas = st.checkbox(
                "❌ Tem dívidas à AT ou SS?",
                key="m_dividas"
            )

            st.markdown("**Tipo de investimento previsto:**")
            tipos_inv_opcoes = [
                "Equipamento Industrial",
                "Software de Gestão (ERP)",
                "Digital / Automação",
                "Formação Profissional",
                "Certificações ISO",
                "Eficiência Energética",
                "Frota Elétrica",
                "I&D / Inovação",
                "Internacionalização",
                "Capital de Maneio",
            ]
            m_tipos = []
            cols_tipos = st.columns(2)
            for i, tipo_opt in enumerate(tipos_inv_opcoes):
                with cols_tipos[i % 2]:
                    if st.checkbox(
                        tipo_opt,
                        key=f"m_tipo_{i}"
                    ):
                        m_tipos.append(tipo_opt)

            m_valor_invest = st.number_input(
                "Valor de investimento previsto (€)",
                min_value=0.0, value=100000.0,
                step=5000.0, key="m_valor_invest"
            )

            perfil_atual = {
                "setor":              m_setor,
                "regiao":             m_regiao,
                "n_trabalhadores":    m_n_trab,
                "volume_negocios":    m_vol,
                "anos_atividade":     m_anos,
                "tem_dividas_fiscais":m_dividas,
                "tipo_investimento":  m_tipos,
                "valor_investimento": m_valor_invest,
            }

            if st.button(
                "🎯 Encontrar Fundos",
                key="btn_match",
                type="primary",
                use_container_width=True
            ):
                st.session_state['perfil_match'] = perfil_atual
                st.rerun()

        with col_res:
            st.markdown("#### 📊 Fundos Elegíveis")

            perfil_calc = st.session_state.get(
                'perfil_match', perfil_atual
            )

            # Calcular elegibilidade para todos os fundos
            fundos_com_score = []
            for fundo in FUNDOS_DB:
                score, motivos = _calcular_elegibilidade(
                    fundo, perfil_calc
                )
                fundo_c = dict(fundo)
                fundo_c['elegibilidade_score'] = score
                fundo_c['motivos']             = motivos
                fundos_com_score.append(fundo_c)

            # Ordenar por score
            fundos_com_score.sort(
                key=lambda x: x['elegibilidade_score'],
                reverse=True
            )

            # Gráfico
            scores_plot = [
                (f['nome'][:30], f['elegibilidade_score'])
                for f in fundos_com_score
            ]
            fig_match = _grafico_radar_elegibilidade(scores_plot)
            if fig_match:
                st.plotly_chart(
                    fig_match, use_container_width=True
                )

            # Cards por fundo
            for fundo_s in fundos_com_score:
                sc      = fundo_s['elegibilidade_score']
                cor_s   = "#10B981" if sc >= 70 \
                          else "#F59E0B" if sc >= 40 \
                          else "#EF4444"
                ic_s    = "🟢" if sc >= 70 \
                          else "🟡" if sc >= 40 \
                          else "🔴"

                apoio_c = _calcular_apoio(
                    perfil_calc.get('valor_investimento',100000),
                    fundo_s.get('pct_max',50),
                    fundo_s.get('tipo','')
                )

                with st.expander(
                    f"{ic_s} {fundo_s['nome'][:40]} "
                    f"— {sc}% elegível",
                    expanded=(sc >= 70)
                ):
                    col_fd1, col_fd2 = st.columns([2,1])
                    with col_fd1:
                        st.markdown(
                            f"<div style='background:#0F172A;"
                            f"border-radius:8px;padding:12px;'>"
                            f"<p style='color:#64748B;"
                            f"font-size:0.75rem;margin:0 0 4px;'>"
                            f"🏷️ {fundo_s.get('programa','')} · "
                            f"{fundo_s.get('tipo','')}</p>"
                            f"<p style='color:#94A3B8;"
                            f"font-size:0.85rem;margin:0 0 8px;'>"
                            f"{fundo_s.get('descricao','')}</p>"
                            f"<small style='color:#64748B;'>"
                            f"📞 {fundo_s.get('contacto','')} · "
                            f"🌐 {fundo_s.get('url','')}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        # Critérios de elegibilidade
                        for motivo in fundo_s.get('motivos',[])[:4]:
                            cor_m = "#10B981" if motivo.startswith("✅") \
                                    else "#EF4444" if motivo.startswith("❌") \
                                    else "#F59E0B"
                            st.markdown(
                                f"<small style='color:{cor_m};'>"
                                f"{motivo}</small><br>",
                                unsafe_allow_html=True
                            )

                    with col_fd2:
                        st.markdown(
                            f"<div style='background:{cor_s}18;"
                            f"border:1px solid {cor_s};"
                            f"border-radius:10px;padding:12px;"
                            f"text-align:center;'>"
                            f"<b style='color:{cor_s};"
                            f"font-size:1.5rem;'>{sc}%</b><br>"
                            f"<small style='color:#64748B;'>"
                            f"elegível</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:10px;"
                            f"margin-top:8px;text-align:center;'>"
                            f"<small style='color:#64748B;'>"
                            f"Apoio estimado</small><br>"
                            f"<b style='color:#3B82F6;"
                            f"font-size:1.1rem;'>"
                            f"€{apoio_c['apoio_max']:,.0f}</b>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        if sc >= 40:
                            if st.button(
                                "📋 Adicionar",
                                key=f"add_cand_{fundo_s['id']}",
                                use_container_width=True,
                                type="primary"
                            ):
                                nova_cand = pd.DataFrame([{
                                    "ID":               str(uuid.uuid4())[:8].upper(),
                                    "Fundo":            fundo_s['nome'],
                                    "Programa":         fundo_s['programa'],
                                    "Data_Inicio":      hoje.strftime("%d/%m/%Y"),
                                    "Prazo_Candidatura":"",
                                    "Data_Fim":         "",
                                    "Valor_Investimento":perfil_calc.get(
                                        'valor_investimento',0
                                    ),
                                    "Valor_Apoio":      apoio_c['apoio_max'],
                                    "Pct_Apoio":        fundo_s.get('pct_max',0),
                                    "Estado":           "Identificado",
                                    "Notas":            "",
                                    "Responsavel":      user_nome,
                                    "Documentos_OK":    "Não"
                                }])
                                upd_cand = pd.concat(
                                    [cand_db, nova_cand],
                                    ignore_index=True
                                ) if not cand_db.empty \
                                  else nova_cand
                                save_db(
                                    upd_cand,
                                    "fundos_candidaturas.csv"
                                )
                                inv()
                                st.success(
                                    f"✅ Adicionado a candidaturas!"
                                )
                                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — CALCULADORA DE APOIO
    # ════════════════════════════════════════════════════════════════
    with t_calc:
        st.markdown("### 💰 Calculadora de Apoio")
        st.info(
            "Simula o valor de apoio que podes obter "
            "para um investimento específico."
        )

        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.markdown("#### ⚙️ Parâmetros")

            fundo_calc = st.selectbox(
                "Fundo",
                [f['nome'] for f in FUNDOS_DB],
                key="calc_fundo"
            )
            fundo_sel = next(
                (f for f in FUNDOS_DB if f['nome'] == fundo_calc),
                FUNDOS_DB[0]
            )

            invest_calc = st.number_input(
                "Valor do Investimento (€)",
                min_value=0.0, value=150000.0,
                step=5000.0, key="calc_invest"
            )

            pct_calc = st.slider(
                "% de Apoio (máx. "
                f"{fundo_sel.get('pct_max',50)}%)",
                0,
                fundo_sel.get('pct_max',80),
                fundo_sel.get('pct_max',50) // 2,
                5,
                key="calc_pct"
            )

            anos_exec = st.slider(
                "Anos de execução", 1, 5, 2,
                key="calc_anos"
            )

        with col_c2:
            st.markdown("#### 📊 Resultado")

            apoio_r = _calcular_apoio(
                invest_calc, pct_calc,
                fundo_sel.get('tipo','')
            )

            # Cards resultado
            st.markdown(
                f"<div style='background:#1E293B;"
                f"border-radius:12px;padding:20px;'>"
                f"<div style='display:grid;"
                f"grid-template-columns:1fr 1fr;"
                f"gap:12px;margin-bottom:16px;'>"
                f"<div style='background:#0F172A;"
                f"border-radius:8px;padding:12px;"
                f"text-align:center;'>"
                f"<small style='color:#64748B;'>Investimento</small><br>"
                f"<b style='color:#F1F5F9;font-size:1.3rem;'>"
                f"€{invest_calc:,.0f}</b>"
                f"</div>"
                f"<div style='background:#0F172A;"
                f"border-radius:8px;padding:12px;"
                f"text-align:center;'>"
                f"<small style='color:#64748B;'>% Apoio</small><br>"
                f"<b style='color:#3B82F6;font-size:1.3rem;'>"
                f"{pct_calc}%</b>"
                f"</div>"
                f"</div>"
                f"<div style='background:rgba(16,185,129,0.1);"
                f"border:2px solid #10B981;"
                f"border-radius:10px;padding:16px;"
                f"text-align:center;margin-bottom:12px;'>"
                f"<small style='color:#64748B;'>APOIO ESTIMADO</small><br>"
                f"<b style='color:#10B981;font-size:2rem;'>"
                f"€{apoio_r['apoio_max']:,.0f}</b><br>"
                f"<small style='color:#64748B;'>"
                f"{'Fundo perdido' if not apoio_r['reembolsavel'] else 'Reembolsável'}"
                f"</small></div>"
                f"<div style='background:rgba(239,68,68,0.08);"
                f"border-radius:8px;padding:12px;"
                f"text-align:center;'>"
                f"<small style='color:#64748B;'>"
                f"Contrapartida empresa</small><br>"
                f"<b style='color:#EF4444;"
                f"font-size:1.2rem;'>"
                f"€{apoio_r['contrapartida']:,.0f}</b>"
                f"</div></div>",
                unsafe_allow_html=True
            )

            # ROI do apoio
            if invest_calc > 0:
                roi_apoio = round(
                    apoio_r['apoio_max'] /
                    apoio_r['contrapartida'] * 100, 0
                ) if apoio_r['contrapartida'] > 0 else 0
                st.markdown(
                    f"<div style='background:rgba(59,130,246,0.1);"
                    f"border:1px solid #3B82F6;"
                    f"border-radius:8px;padding:12px;"
                    f"text-align:center;margin-top:8px;'>"
                    f"<b style='color:#3B82F6;'>"
                    f"Por cada €100 investidos, "
                    f"o Estado co-financia €"
                    f"{pct_calc}</b><br>"
                    f"<small style='color:#64748B;'>"
                    f"ROI mínimo do apoio: "
                    f"{roi_apoio:.0f}%</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # Tabela comparativa todos os fundos
        st.markdown("---")
        st.markdown("#### 📊 Comparativo de Apoio por Fundo")

        rows_comp = []
        for f in FUNDOS_DB:
            apoio_f = _calcular_apoio(
                invest_calc,
                f.get('pct_max', 50),
                f.get('tipo','')
            )
            rows_comp.append({
                "Fundo":         f['nome'][:35],
                "Programa":      f['programa'],
                "Tipo":          f['tipo'][:30],
                "% Apoio":       f"{f.get('pct_max',0)}%",
                "Apoio Est.(€)": f"€{apoio_f['apoio_max']:,.0f}",
                "Contrapartida": f"€{apoio_f['contrapartida']:,.0f}",
            })

        df_comp = pd.DataFrame(rows_comp)
        st.dataframe(
            df_comp, use_container_width=True, hide_index=True
        )

        csv_comp = df_comp.to_csv(
            index=False, encoding='utf-8-sig'
        )
        st.download_button(
            "📥 Exportar Comparativo",
            data=csv_comp.encode('utf-8-sig'),
            file_name="comparativo_fundos.csv",
            mime="text/csv",
            key="dl_comp_fundos"
        )

    # ════════════════════════════════════════════════════════════════
    # TAB — FUNDOS DISPONÍVEIS
    # ════════════════════════════════════════════════════════════════
    with t_fundos:
        st.markdown("### 📚 Catálogo de Fundos")

        # Filtros
        col_ff1, col_ff2, col_ff3 = st.columns(3)
        with col_ff1:
            prog_filt = st.selectbox(
                "Programa",
                ["Todos"] + list(
                    set(f['programa'] for f in FUNDOS_DB)
                ),
                key="ff_prog"
            )
        with col_ff2:
            tipo_filt = st.selectbox(
                "Tipo",
                ["Todos",
                 "Subvenção não reembolsável",
                 "Crédito bonificado (reembolsável)",
                 "Benefício fiscal (dedução IRC)"],
                key="ff_tipo"
            )
        with col_ff3:
            valor_min_filt = st.number_input(
                "Apoio mínimo que preciso (€)",
                min_value=0.0, value=0.0,
                step=10000.0, key="ff_val_min"
            )

        fundos_filtrados = [
            f for f in FUNDOS_DB
            if (prog_filt == "Todos" or f['programa'] == prog_filt)
            and (tipo_filt == "Todos" or f['tipo'] == tipo_filt)
            and f.get('valor_max',0) >= valor_min_filt
        ]

        st.markdown(
            f"<p style='color:#64748B;font-size:0.8rem;'>"
            f"{len(fundos_filtrados)} fundo(s) encontrado(s)</p>",
            unsafe_allow_html=True
        )

        for fundo_f in fundos_filtrados:
            cor_f = fundo_f['cor']
            tipo_badge_cor = {
                "Subvenção não reembolsável":       "#10B981",
                "Crédito bonificado (reembolsável)":"#3B82F6",
                "Benefício fiscal (dedução IRC)":   "#F59E0B",
            }.get(fundo_f.get('tipo',''),"#6B7280")

            with st.expander(
                f"🏦 {fundo_f['nome']}",
                expanded=False
            ):
                col_fi1, col_fi2, col_fi3 = st.columns([3,1,1])

                with col_fi1:
                    st.markdown(
                        f"<div style='background:#0F172A;"
                        f"border-radius:8px;padding:12px;'>"
                        f"<span class='badge-fundo' "
                        f"style='background:{tipo_badge_cor}22;"
                        f"color:{tipo_badge_cor};'>"
                        f"{fundo_f.get('tipo','')}</span>"
                        f"<span class='badge-fundo' "
                        f"style='background:rgba(59,130,246,0.15);"
                        f"color:#3B82F6;margin-left:8px;'>"
                        f"{fundo_f.get('programa','')}</span><br><br>"
                        f"<p style='color:#94A3B8;"
                        f"font-size:0.85rem;margin:0 0 8px;'>"
                        f"{fundo_f.get('descricao','')}</p>"
                        f"<small style='color:#64748B;'>"
                        f"🏢 {fundo_f.get('entidade','')} · "
                        f"⏱️ {fundo_f.get('prazo_decisao','')} · "
                        f"📞 {fundo_f.get('contacto','')} · "
                        f"🌐 {fundo_f.get('url','')}</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    # Documentos necessários
                    st.markdown(
                        "<p style='color:#64748B;"
                        "font-size:0.75rem;font-weight:700;"
                        "text-transform:uppercase;"
                        "margin:8px 0 4px;'>Documentos:</p>",
                        unsafe_allow_html=True
                    )
                    for doc in fundo_f.get('documentos',[]):
                        st.markdown(
                            f"<small style='color:#94A3B8;'>"
                            f"📄 {doc}</small><br>",
                            unsafe_allow_html=True
                        )

                with col_fi2:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:8px;padding:12px;"
                        f"text-align:center;'>"
                        f"<small style='color:#64748B;'>"
                        f"Apoio máximo</small><br>"
                        f"<b style='color:{cor_f};"
                        f"font-size:1.1rem;'>"
                        f"{fundo_f.get('pct_max',0)}%</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"€{fundo_f.get('valor_min',0):,} — "
                        f"€{fundo_f.get('valor_max',0):,.0f}"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

                with col_fi3:
                    if st.button(
                        "📋 Candidatar",
                        key=f"cand_{fundo_f['id']}",
                        use_container_width=True,
                        type="primary"
                    ):
                        st.session_state[
                            'fundo_candidatar'
                        ] = fundo_f
                        st.info(
                            "✅ Vai ao tab 📋 Gestão Candidaturas "
                            "para completar."
                        )

    # ════════════════════════════════════════════════════════════════
    # TAB — GESTÃO DE CANDIDATURAS
    # ════════════════════════════════════════════════════════════════
    with t_cand:
        st.markdown("### 📋 Gestão de Candidaturas")

        col_cf, col_cl = st.columns([1, 2])

        with col_cf:
            st.markdown("#### ➕ Nova Candidatura")
            fundo_pre = st.session_state.get('fundo_candidatar')

            with st.form("form_candidatura"):
                cand_fundo = st.selectbox(
                    "Fundo *",
                    [f['nome'] for f in FUNDOS_DB],
                    index=[f['nome'] for f in FUNDOS_DB].index(
                        fundo_pre['nome']
                    ) if fundo_pre else 0,
                    key="cand_fundo"
                )
                cand_prog = next(
                    (f['programa'] for f in FUNDOS_DB
                     if f['nome'] == cand_fundo),
                    ""
                )

                cand_invest = st.number_input(
                    "Valor Investimento (€) *",
                    min_value=0.0, value=100000.0,
                    step=5000.0, key="cand_invest"
                )
                cand_pct = next(
                    (f.get('pct_max',50) for f in FUNDOS_DB
                     if f['nome'] == cand_fundo),
                    50
                )
                apoio_est = round(cand_invest * cand_pct / 100, 2)

                cand_prazo = st.text_input(
                    "Prazo de Candidatura (dd/mm/aaaa)",
                    key="cand_prazo"
                )
                cand_estado = st.selectbox(
                    "Estado",
                    ["Identificado","A Preparar","Submetido",
                     "Em Análise","Aprovado","Rejeitado",
                     "Em Execução","Concluído"],
                    key="cand_estado"
                )
                cand_resp = st.text_input(
                    "Responsável",
                    value=user_nome,
                    key="cand_resp"
                )
                cand_notas = st.text_area(
                    "Notas", key="cand_notas"
                )
                cand_docs = st.checkbox(
                    "✅ Documentos em ordem?",
                    key="cand_docs"
                )

                if st.form_submit_button(
                    "💾 Guardar Candidatura",
                    use_container_width=True, type="primary"
                ):
                    if cand_invest <= 0:
                        st.error("❌ Valor de investimento obrigatório.")
                    else:
                        nova_c = pd.DataFrame([{
                            "ID":               str(uuid.uuid4())[:8].upper(),
                            "Fundo":            cand_fundo,
                            "Programa":         cand_prog,
                            "Data_Inicio":      hoje.strftime("%d/%m/%Y"),
                            "Prazo_Candidatura":cand_prazo.strip(),
                            "Data_Fim":         "",
                            "Valor_Investimento":cand_invest,
                            "Valor_Apoio":      apoio_est,
                            "Pct_Apoio":        cand_pct,
                            "Estado":           cand_estado,
                            "Notas":            cand_notas.strip(),
                            "Responsavel":      cand_resp.strip(),
                            "Documentos_OK":    "Sim" if cand_docs else "Não"
                        }])
                        upd_c2 = pd.concat(
                            [cand_db, nova_c], ignore_index=True
                        ) if not cand_db.empty else nova_c
                        save_db(upd_c2, "fundos_candidaturas.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="CRIAR_CANDIDATURA_FUNDO",
                            tabela="fundos_candidaturas.csv",
                            registro_id=nova_c['ID'].iloc[0],
                            detalhes=(
                                f"{cand_fundo} | "
                                f"€{apoio_est:,.0f}"
                            ),
                            ip=""
                        )
                        st.session_state.pop(
                            'fundo_candidatar', None
                        )
                        inv()
                        st.success(
                            f"✅ Candidatura criada! "
                            f"Apoio est.: €{apoio_est:,.0f}"
                        )
                        st.rerun()

        with col_cl:
            st.markdown("#### 📊 Candidaturas em Curso")

            # Timeline
            fig_tl_c = _grafico_timeline_candidaturas(cand_db)
            if fig_tl_c:
                st.plotly_chart(
                    fig_tl_c, use_container_width=True
                )

            if cand_db.empty:
                st.info("📋 Sem candidaturas registadas.")
            else:
                est_cores = {
                    'Identificado':  '#64748B',
                    'A Preparar':    '#F59E0B',
                    'Submetido':     '#3B82F6',
                    'Em Análise':    '#8B5CF6',
                    'Aprovado':      '#10B981',
                    'Rejeitado':     '#EF4444',
                    'Em Execução':   '#06B6D4',
                    'Concluído':     '#94A3B8',
                }

                for _, cand_row in cand_db.sort_values(
                    'Data_Inicio', ascending=False
                ).iterrows():
                    cid     = cand_row.get('ID','')
                    est_c   = cand_row.get('Estado','')
                    cor_c   = est_cores.get(est_c,'#6B7280')
                    val_c   = float(cand_row.get('Valor_Apoio',0) or 0)
                    pct_c   = float(cand_row.get('Pct_Apoio',0) or 0)
                    docs_ok = cand_row.get('Documentos_OK','Não')

                    # Alerta prazo
                    prazo_str = cand_row.get('Prazo_Candidatura','')
                    alerta_pz = ""
                    if prazo_str:
                        try:
                            d_pz = datetime.strptime(
                                prazo_str, "%d/%m/%Y"
                            ).date()
                            dias_pz = (d_pz - hoje).days
                            if dias_pz < 0:
                                alerta_pz = (
                                    "<span style='color:#EF4444;"
                                    "font-size:0.72rem;'>"
                                    "🔴 Prazo expirado!</span>"
                                )
                            elif dias_pz <= 14:
                                alerta_pz = (
                                    f"<span style='color:#EF4444;"
                                    f"font-size:0.72rem;'>"
                                    f"⚠️ Prazo em {dias_pz} dias!"
                                    f"</span>"
                                )
                            elif dias_pz <= 30:
                                alerta_pz = (
                                    f"<span style='color:#F59E0B;"
                                    f"font-size:0.72rem;'>"
                                    f"⏰ {dias_pz} dias para prazo"
                                    f"</span>"
                                )
                        except:
                            pass

                    col_ci, col_ca = st.columns([5,1])
                    with col_ci:
                        st.markdown(
                            f"<div class='cand-card' "
                            f"style='border-left-color:{cor_c};'>"
                            f"<div style='display:flex;"
                            f"justify-content:space-between;"
                            f"align-items:flex-start;'>"
                            f"<div>"
                            f"<b style='color:#F1F5F9;"
                            f"font-size:0.9rem;'>"
                            f"{cand_row.get('Fundo','')[:35]}</b><br>"
                            f"<small style='color:#64748B;'>"
                            f"🏷️ {cand_row.get('Programa','')} · "
                            f"📅 {cand_row.get('Data_Inicio','')} · "
                            f"Prazo: {prazo_str} · "
                            f"📁 {docs_ok}</small><br>"
                            f"{alerta_pz}"
                            f"</div>"
                            f"<div style='text-align:right;'>"
                            f"<b style='color:#10B981;"
                            f"font-size:1rem;'>"
                            f"€{val_c:,.0f}</b><br>"
                            f"<span class='badge-fundo' "
                            f"style='background:{cor_c}22;"
                            f"color:{cor_c};'>{est_c}</span>"
                            f"</div></div></div>",
                            unsafe_allow_html=True
                        )

                    with col_ca:
                        novo_est_c = st.selectbox(
                            "Estado",
                            ['Identificado','A Preparar','Submetido',
                             'Em Análise','Aprovado','Rejeitado',
                             'Em Execução','Concluído'],
                            key=f"c_est_{cid}",
                            label_visibility="collapsed"
                        )
                        if st.button(
                            "✅",
                            key=f"c_upd_{cid}",
                            use_container_width=True
                        ):
                            cand_db.loc[
                                cand_db['ID'] == cid,
                                'Estado'
                            ] = novo_est_c
                            save_db(
                                cand_db,
                                "fundos_candidaturas.csv"
                            )
                            inv(); st.rerun()

                        # Gerar PDF
                        if st.button(
                            "📄",
                            key=f"c_pdf_{cid}",
                            use_container_width=True,
                            help="Gerar ficha PDF"
                        ):
                            f_sel = next(
                                (f for f in FUNDOS_DB
                                 if f['nome'] == cand_row.get('Fundo','')),
                                FUNDOS_DB[0]
                            )
                            apoio_p = _calcular_apoio(
                                float(cand_row.get(
                                    'Valor_Investimento',0
                                ) or 0),
                                float(cand_row.get('Pct_Apoio',50) or 50),
                                f_sel.get('tipo','')
                            )
                            perf_p = {
                                "setor":   m_setor,
                                "regiao":  m_regiao,
                                "n_trabalhadores": m_n_trab,
                                "volume_negocios": m_vol,
                                "anos_atividade":  m_anos,
                                "tipo_investimento": m_tipos,
                                "valor_investimento": float(
                                    cand_row.get('Valor_Investimento',0) or 0
                                )
                            }
                            _, mots = _calcular_elegibilidade(
                                f_sel, perf_p
                            )
                            with st.spinner("PDF..."):
                                pdf_c = _gerar_pdf_candidatura(
                                    f_sel, apoio_p,
                                    perf_p, mots, empresa
                                )
                            st.session_state[f'cand_pdf_{cid}'] = pdf_c
                            st.rerun()

                        if st.session_state.get(f'cand_pdf_{cid}'):
                            st.download_button(
                                "📥",
                                data=st.session_state[f'cand_pdf_{cid}'],
                                file_name=f"candidatura_{cid}.pdf",
                                mime="application/pdf",
                                key=f"dl_cand_{cid}",
                                use_container_width=True
                            )

    # ════════════════════════════════════════════════════════════════
    # TAB — IA CONSULTORA
    # ════════════════════════════════════════════════════════════════
    with t_ia:
        st.markdown("### 🤖 IA Consultora de Fundos Europeus")
        st.info(
            "A IA analisa o perfil da empresa e "
            "recomenda os melhores fundos com um plano "
            "de candidatura personalizado."
        )

        col_ia1, col_ia2 = st.columns(2)

        with col_ia1:
            st.markdown("#### 🔍 Pesquisa de Avisos Abertos")
            st.markdown(
                "<small style='color:#64748B;'>"
                "A IA pesquisa e sugere fundos relevantes "
                "para o perfil da empresa.</small>",
                unsafe_allow_html=True
            )

            perfil_ia = st.session_state.get(
                'perfil_match',
                {
                    "setor":"Instrumentação Industrial",
                    "regiao":"Norte",
                    "n_trabalhadores":15,
                    "volume_negocios":800000,
                    "anos_atividade":5,
                    "tipo_investimento":["Equipamento"],
                }
            )

            # Preview do perfil atual
            st.markdown(
                f"<div style='background:#1E293B;"
                f"border-radius:8px;padding:10px;"
                f"margin-bottom:8px;'>"
                f"<small style='color:#64748B;'>"
                f"Setor: {perfil_ia.get('setor','')} · "
                f"Região: {perfil_ia.get('regiao','')} · "
                f"{perfil_ia.get('n_trabalhadores','')} trabalhadores"
                f"</small></div>",
                unsafe_allow_html=True
            )

            if st.button(
                "🔍 Pesquisar Avisos Abertos",
                key="btn_pesq_avisos",
                type="primary",
                use_container_width=True
            ):
                with st.spinner(
                    "🤖 A pesquisar avisos relevantes..."
                ):
                    resultado_ia = _pesquisar_avisos_ia(perfil_ia)
                st.session_state['ia_avisos'] = resultado_ia

            if st.session_state.get('ia_avisos'):
                st.markdown(
                    f"<div style='background:rgba(59,130,246,0.1);"
                    f"border:1px solid #3B82F6;"
                    f"border-radius:12px;padding:16px;"
                    f"color:#E2E8F0;font-size:0.85rem;"
                    f"line-height:1.7;'>"
                    f"<p style='color:#3B82F6;font-weight:700;"
                    f"margin:0 0 8px;'>"
                    f"🤖 AVISOS ABERTOS — IA</p>"
                    f"{st.session_state['ia_avisos'].replace(chr(10),'<br>')}"
                    f"</div>",
                    unsafe_allow_html=True
                )

        with col_ia2:
            st.markdown("#### 📋 Plano de Candidatura IA")
            st.markdown(
                "<small style='color:#64748B;'>"
                "Seleciona um fundo e a IA gera um plano "
                "detalhado de candidatura.</small>",
                unsafe_allow_html=True
            )

            fundo_plano = st.selectbox(
                "Fundo para plano",
                [f['nome'] for f in FUNDOS_DB],
                key="ia_fundo_plano"
            )
            invest_plano = st.number_input(
                "Investimento previsto (€)",
                min_value=0.0, value=150000.0,
                step=10000.0, key="ia_invest_plano"
            )

            if st.button(
                "📋 Gerar Plano de Candidatura",
                key="btn_plano_cand",
                type="primary",
                use_container_width=True
            ):
                f_plano = next(
                    (f for f in FUNDOS_DB
                     if f['nome'] == fundo_plano),
                    FUNDOS_DB[0]
                )
                perf_plano = {
                    **perfil_ia,
                    "valor_investimento": invest_plano
                }
                with st.spinner(
                    "🤖 A elaborar plano de candidatura..."
                ):
                    plano_ia = _gerar_plano_candidatura_ia(
                        f_plano, perf_plano, empresa
                    )
                st.session_state['ia_plano_cand'] = plano_ia
                st.session_state['ia_plano_fundo'] = fundo_plano

            if st.session_state.get('ia_plano_cand'):
                st.markdown(
                    f"<div style='background:rgba(16,185,129,0.08);"
                    f"border:1px solid #10B981;"
                    f"border-radius:12px;padding:16px;"
                    f"color:#E2E8F0;font-size:0.85rem;"
                    f"line-height:1.7;'>"
                    f"<p style='color:#10B981;font-weight:700;"
                    f"margin:0 0 8px;'>"
                    f"📋 PLANO — "
                    f"{st.session_state.get('ia_plano_fundo','')[:30]}"
                    f"</p>"
                    f"{st.session_state['ia_plano_cand'].replace(chr(10),'<br>')}"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # Pergunta livre
        st.markdown("---")
        st.markdown("#### 💬 Pergunta Livre sobre Fundos")

        pergunta_fundos = st.text_input(
            "Pergunta",
            placeholder="Ex: Posso candidatar ao SIFIDE "
                        "com o desenvolvimento do GESTNOW?",
            key="fundos_pergunta",
            label_visibility="collapsed"
        )
        if st.button(
            "🤖 Perguntar",
            key="btn_pergunta_fundos",
            use_container_width=True
        ):
            if pergunta_fundos.strip():
                import anthropic
                api_key = os.environ.get("ANTHROPIC_API_KEY","")
                if api_key:
                    with st.spinner("🤖 A pesquisar..."):
                        try:
                            client = anthropic.Anthropic(
                                api_key=api_key
                            )
                            resp   = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=600,
                                messages=[{
                                    "role":"user",
                                    "content":(
                                        f"Sou gestor de uma PME "
                                        f"portuguesa de instrumentação "
                                        f"industrial (CPS, Sines). "
                                        f"Pergunta sobre fundos europeus: "
                                        f"{pergunta_fundos}\n\n"
                                        f"Responde em português, "
                                        f"prático e direto."
                                    )
                                }]
                            )
                            st.markdown(
                                f"<div style='background:rgba(59,130,246,0.1);"
                                f"border:1px solid #3B82F6;"
                                f"border-radius:10px;padding:14px;"
                                f"color:#E2E8F0;font-size:0.88rem;"
                                f"line-height:1.6;margin-top:8px;'>"
                                f"{resp.content[0].text.replace(chr(10),'<br>')}"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        except Exception as e:
                            st.error(f"❌ {e}")

    # ════════════════════════════════════════════════════════════════
    # TAB — CALENDÁRIO DE FUNDOS
    # ════════════════════════════════════════════════════════════════
    with t_calendario:
        st.markdown("### 📅 Calendário de Fundos & Prazos")

        # Gráfico prazos
        fig_cal = _grafico_calendario_fundos(cand_db)
        if fig_cal:
            st.plotly_chart(
                fig_cal, use_container_width=True
            )

        # Donut potencial
        perfil_cal = st.session_state.get(
            'perfil_match',
            {"setor":"Instrumentação","regiao":"Norte",
             "n_trabalhadores":15}
        )
        fundos_elig = [
            {**f, 'score': _calcular_elegibilidade(f, perfil_cal)[0]}
            for f in FUNDOS_DB
            if _calcular_elegibilidade(f, perfil_cal)[0] >= 40
        ]
        fig_don = _grafico_apoio_donut(
            fundos_elig,
            st.session_state.get('perfil_match',{}).get(
                'valor_investimento', 150000
            )
        )
        if fig_don:
            st.plotly_chart(
                fig_don, use_container_width=True
            )

        # Alertas de prazos
        st.markdown("#### ⏰ Alertas de Prazos")

        if not cand_db.empty and \
           'Prazo_Candidatura' in cand_db.columns:
            alertas_pz = []
            for _, row in cand_db.iterrows():
                pz = row.get('Prazo_Candidatura','')
                if not pz:
                    continue
                try:
                    d_pz  = datetime.strptime(
                        pz, "%d/%m/%Y"
                    ).date()
                    dias  = (d_pz - hoje).days
                    if 0 <= dias <= 60:
                        alertas_pz.append({
                            "fundo": row.get('Fundo','')[:30],
                            "prazo": pz,
                            "dias":  dias,
                            "val":   float(
                                row.get('Valor_Apoio',0) or 0
                            )
                        })
                except:
                    pass

            if alertas_pz:
                alertas_pz.sort(key=lambda x: x['dias'])
                for ap in alertas_pz:
                    cor_ap = "#EF4444" if ap['dias'] < 14 \
                             else "#F59E0B"
                    st.markdown(
                        f"<div style='background:{cor_ap}10;"
                        f"border-left:4px solid {cor_ap};"
                        f"border-radius:8px;padding:10px 14px;"
                        f"margin-bottom:6px;'>"
                        f"<b style='color:{cor_ap};'>"
                        f"⏰ {ap['fundo']}</b>"
                        f"<span style='float:right;color:#64748B;'>"
                        f"€{ap['val']:,.0f}</span><br>"
                        f"<small style='color:#94A3B8;'>"
                        f"Prazo: {ap['prazo']} — "
                        f"faltam {ap['dias']} dia(s)</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.success("✅ Sem prazos urgentes nos próximos 60 dias.")
        else:
            st.info(
                "📋 Adiciona prazos de candidatura no tab "
                "📋 Gestão Candidaturas."
            )

        # Calendário fiscal de obrigações de reporte
        st.markdown("---")
        st.markdown("#### 📋 Obrigações de Reporte para Fundos Ativos")
        st.info(
            "Projetos aprovados têm obrigações de reporte "
            "trimestrais/anuais. Regista aqui os prazos."
        )

        candidaturas_ativas = cand_db[
            cand_db.get('Estado','') == 'Em Execução'
        ] if not cand_db.empty and \
             'Estado' in cand_db.columns \
          else pd.DataFrame()

        if candidaturas_ativas.empty:
            st.info(
                "📋 Sem projetos em execução. "
                "Quando um projeto for aprovado e iniciado, "
                "aparece aqui."
            )
        else:
            for _, proj in candidaturas_ativas.iterrows():
                st.markdown(
                    f"<div style='background:#1E293B;"
                    f"border-radius:8px;padding:12px;"
                    f"margin-bottom:8px;"
                    f"border-left:3px solid #06B6D4;'>"
                    f"<b style='color:#F1F5F9;'>"
                    f"▶ {proj.get('Fundo','')[:35]}</b><br>"
                    f"<small style='color:#64748B;'>"
                    f"Valor apoio: "
                    f"€{float(proj.get('Valor_Apoio',0) or 0):,.0f} · "
                    f"Início: {proj.get('Data_Inicio','')}</small><br>"
                    f"<small style='color:#06B6D4;'>"
                    f"📊 Próximo reporte trimestral — verificar portal"
                    f"</small></div>",
                    unsafe_allow_html=True
                )

"""
GESTNOW v3 — mod_admin_comercial.py
Módulo Comercial — Pipeline, Clientes, Visitas, Ranking, KPIs
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

def _hoje_str():
    return date.today().strftime("%d/%m/%Y")


# ─────────────────────────────────────────────────────────────────
# PIPELINE STAGES
# ─────────────────────────────────────────────────────────────────

PIPELINE_STAGES = [
    {"id": "prospeto",    "nome": "🔍 Prospeto",       "cor": "#64748B", "prob": 10},
    {"id": "contactado",  "nome": "📞 Contactado",      "cor": "#3B82F6", "prob": 25},
    {"id": "reuniao",     "nome": "🤝 Reunião Marcada", "cor": "#8B5CF6", "prob": 40},
    {"id": "proposta",    "nome": "📄 Proposta Enviada","cor": "#F59E0B", "prob": 60},
    {"id": "negociacao",  "nome": "💬 Negociação",      "cor": "#F97316", "prob": 75},
    {"id": "ganho",       "nome": "✅ Ganho",            "cor": "#10B981", "prob": 100},
    {"id": "perdido",     "nome": "❌ Perdido",          "cor": "#EF4444", "prob": 0},
]

STAGE_NOMES = [s["nome"] for s in PIPELINE_STAGES]
STAGE_IDS   = [s["id"]   for s in PIPELINE_STAGES]

def _get_stage(stage_id):
    return next((s for s in PIPELINE_STAGES if s["id"] == stage_id), PIPELINE_STAGES[0])


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_funil_pipeline(oport_db):
    """Funil de oportunidades por stage."""
    stages_ativos = [s for s in PIPELINE_STAGES
                     if s["id"] not in ["ganho","perdido"]]
    vals = []
    for s in stages_ativos:
        if not oport_db.empty and 'Stage' in oport_db.columns:
            n = len(oport_db[oport_db['Stage'] == s["id"]])
        else:
            n = 0
        vals.append(n)

    fig = go.Figure(go.Funnel(
        y=[s["nome"] for s in stages_ativos],
        x=vals,
        textinfo="value+percent initial",
        marker={
            "color": [s["cor"] for s in stages_ativos],
            "line":  {"width": 1, "color": "#0F172A"}
        },
        connector={"line": {"color": "#334155", "width": 1}},
        textfont={"color": "#F1F5F9"}
    ))
    fig.update_layout(
        title={"text": "Funil de Vendas", "font": {"color": "#F1F5F9"}},
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,41,59,0.5)",
        font={"color": "#F1F5F9"},
        margin=dict(t=40, b=10, l=10, r=10)
    )
    return fig


def _grafico_valor_pipeline(oport_db):
    """Bar chart valor por stage."""
    stages_ativos = [s for s in PIPELINE_STAGES
                     if s["id"] not in ["perdido"]]
    vals = []
    for s in stages_ativos:
        if not oport_db.empty and 'Stage' in oport_db.columns:
            df_s = oport_db[oport_db['Stage'] == s["id"]]
            val  = pd.to_numeric(
                df_s.get('Valor_Est', 0), errors='coerce'
            ).fillna(0).sum()
        else:
            val = 0
        vals.append(round(val, 2))

    fig = go.Figure(go.Bar(
        x=[s["nome"] for s in stages_ativos],
        y=vals,
        marker_color=[s["cor"] for s in stages_ativos],
        text=[f"\u20AC{v:,.0f}" for v in vals],
        textposition="outside",
        textfont={"color": "#F1F5F9", "size": 9},
        hovertemplate="%{x}<br>\u20AC%{y:,.2f}<extra></extra>"
    ))
    fig.update_layout(
        title={"text": "Valor por Stage", "font": {"color": "#F1F5F9"}},
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,41,59,0.5)",
        font={"color": "#F1F5F9"},
        xaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8", "size": 9}},
        yaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}, "tickprefix": "\u20AC"},
        margin=dict(t=40, b=20, l=10, r=10),
        showlegend=False
    )
    return fig


def _grafico_ranking_comerciais(oport_db):
    """Bar chart ranking por comercial."""
    if oport_db.empty or 'Comercial' not in oport_db.columns:
        return None

    ganhos = oport_db[oport_db['Stage'] == 'ganho'].copy()
    if ganhos.empty:
        ganhos = oport_db.copy()

    ganhos['Valor_Num'] = pd.to_numeric(
        ganhos.get('Valor_Est', 0), errors='coerce'
    ).fillna(0)

    grp = ganhos.groupby('Comercial').agg(
        valor=('Valor_Num', 'sum'),
        n=('Valor_Num', 'count')
    ).sort_values('valor', ascending=True)

    if grp.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Valor Angariado',
        y=grp.index.tolist(),
        x=grp['valor'].tolist(),
        orientation='h',
        marker_color='#10B981',
        text=[f"\u20AC{v:,.0f}" for v in grp['valor']],
        textposition='outside',
        textfont={'color': '#F1F5F9', 'size': 10},
        hovertemplate='%{y}<br>\u20AC%{x:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={"text": "Ranking Comerciais", "font": {"color": "#F1F5F9"}},
        height=max(200, len(grp) * 50 + 80),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,41,59,0.5)",
        font={"color": "#F1F5F9"},
        xaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}, "tickprefix": "\u20AC"},
        yaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}},
        margin=dict(t=40, b=20, l=120, r=80),
        showlegend=False
    )
    return fig


def _grafico_visitas_semana(visitas_db):
    """Bar chart visitas por dia da semana."""
    if visitas_db.empty or 'Data' not in visitas_db.columns:
        return None

    vdb = visitas_db.copy()
    vdb['Data_d'] = pd.to_datetime(vdb['Data'], dayfirst=True, errors='coerce')
    vdb['DiaSemana'] = vdb['Data_d'].dt.day_name()

    dias_pt = {
        'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua',
        'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sáb', 'Sunday': 'Dom'
    }
    vdb['DiaSemana_PT'] = vdb['DiaSemana'].map(dias_pt)
    ordem = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    grp = vdb.groupby('DiaSemana_PT').size().reindex(ordem, fill_value=0)

    fig = go.Figure(go.Bar(
        x=grp.index.tolist(),
        y=grp.values.tolist(),
        marker_color='#3B82F6',
        text=grp.values.tolist(),
        textposition='outside',
        textfont={'color': '#F1F5F9', 'size': 10}
    ))
    fig.update_layout(
        title={"text": "Visitas por Dia da Semana", "font": {"color": "#F1F5F9"}},
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,41,59,0.5)",
        font={"color": "#F1F5F9"},
        xaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}},
        yaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}},
        margin=dict(t=40, b=20, l=10, r=10),
        showlegend=False
    )
    return fig


def _grafico_novos_clientes_mes(clientes_db):
    """Bar chart novos clientes por mês."""
    if clientes_db.empty or 'Data_Angariacao' not in clientes_db.columns:
        return None

    cdb = clientes_db.copy()
    cdb['Data_d'] = pd.to_datetime(
        cdb['Data_Angariacao'], dayfirst=True, errors='coerce'
    )
    meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    ano = date.today().year
    vals = []
    for m in range(1, 13):
        n = len(cdb[
            (cdb['Data_d'].dt.month == m) &
            (cdb['Data_d'].dt.year == ano)
        ])
        vals.append(n)

    fig = go.Figure(go.Bar(
        x=meses_pt, y=vals,
        marker_color=['#10B981' if v > 0 else '#334155' for v in vals],
        text=[str(v) if v > 0 else '' for v in vals],
        textposition='outside',
        textfont={'color': '#F1F5F9', 'size': 10}
    ))
    fig.update_layout(
        title={"text": f"Novos Clientes — {ano}", "font": {"color": "#F1F5F9"}},
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,41,59,0.5)",
        font={"color": "#F1F5F9"},
        xaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}},
        yaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}},
        margin=dict(t=40, b=20, l=10, r=10),
        showlegend=False
    )
    return fig


def _grafico_taxa_conversao(oport_db):
    """Gauge taxa de conversão."""
    total = len(oport_db) if not oport_db.empty else 0
    ganhos = len(oport_db[oport_db['Stage'] == 'ganho']) \
             if not oport_db.empty and 'Stage' in oport_db.columns else 0
    taxa = round(ganhos / total * 100, 1) if total > 0 else 0

    cor = "#10B981" if taxa >= 30 else "#F59E0B" if taxa >= 15 else "#EF4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=taxa,
        title={"text": "Taxa Conversão", "font": {"color": "#F1F5F9", "size": 13}},
        number={"suffix": "%", "font": {"color": "#F1F5F9", "size": 28}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#64748B"},
            "bar":  {"color": cor},
            "bgcolor": "#1E293B",
            "bordercolor": "#334155",
            "steps": [
                {"range": [0, 15],  "color": "rgba(239,68,68,0.15)"},
                {"range": [15, 30], "color": "rgba(245,158,11,0.15)"},
                {"range": [30, 100],"color": "rgba(16,185,129,0.15)"},
            ],
            "threshold": {
                "line": {"color": "#F1F5F9", "width": 2},
                "thickness": 0.75, "value": taxa
            }
        }
    ))
    fig.update_layout(
        height=200,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#F1F5F9"},
        margin=dict(t=40, b=10, l=20, r=20)
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF RELATÓRIO COMERCIAL
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_relatorio_comercial(oport_db, visitas_db,
                                    clientes_db, empresa: dict) -> bytes:
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    bold_s = ParagraphStyle('bold', parent=styles['Normal'],
                             fontSize=10, fontName='Helvetica-Bold', spaceAfter=3)
    sub_s  = ParagraphStyle('sub', parent=styles['Normal'],
                             fontSize=8, textColor=colors.HexColor('#64748B'), spaceAfter=2)
    norm_s = ParagraphStyle('norm', parent=styles['Normal'],
                             fontSize=9, spaceAfter=3)

    # Header
    story.append(Paragraph(
        "RELATÓRIO COMERCIAL",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=16, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'), spaceAfter=4)
    ))
    story.append(Paragraph(
        f"{empresa.get('nome','')} | "
        f"Gerado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_s
    ))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor('#3B82F6')))
    story.append(Spacer(1, 0.3*cm))

    # KPIs
    total_oport  = len(oport_db) if not oport_db.empty else 0
    val_pipeline = pd.to_numeric(
        oport_db.get('Valor_Est', 0), errors='coerce'
    ).fillna(0).sum() if not oport_db.empty else 0
    ganhos = len(oport_db[oport_db['Stage'] == 'ganho']) \
             if not oport_db.empty and 'Stage' in oport_db.columns else 0
    taxa   = round(ganhos / total_oport * 100, 1) if total_oport > 0 else 0

    kpi_data = [
        ["Oportunidades Ativas", str(total_oport)],
        ["Valor Total Pipeline", f"\u20AC{val_pipeline:,.2f}"],
        ["Oportunidades Ganhas", str(ganhos)],
        ["Taxa de Conversão",    f"{taxa:.1f}%"],
        ["Total Visitas",        str(len(visitas_db) if not visitas_db.empty else 0)],
        ["Novos Clientes",       str(len(clientes_db) if not clientes_db.empty else 0)],
    ]
    story.append(Paragraph("<b>KPIs COMERCIAIS</b>", bold_s))
    kt = Table(kpi_data, colWidths=[9*cm, 8*cm])
    kt.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('FONTNAME',    (0,0),(0,-1), 'Helvetica-Bold'),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,0),(-1,-1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(kt)
    story.append(Spacer(1, 0.4*cm))

    # Pipeline por stage
    if not oport_db.empty and 'Stage' in oport_db.columns:
        story.append(Paragraph("<b>PIPELINE POR STAGE</b>", bold_s))
        pipe_data = [["Stage", "Oportunidades", "Valor Est."]]
        for s in PIPELINE_STAGES:
            df_s = oport_db[oport_db['Stage'] == s["id"]]
            n    = len(df_s)
            val  = pd.to_numeric(df_s.get('Valor_Est', 0),
                                  errors='coerce').fillna(0).sum()
            if n > 0:
                pipe_data.append([s["nome"], str(n), f"\u20AC{val:,.2f}"])
        pt = Table(pipe_data, colWidths=[7*cm, 4*cm, 6*cm])
        pt.setStyle(TableStyle([
            ('BACKGROUND',  (0,0),(-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
            ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0),(-1,-1), 9),
            ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),
             [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING',  (0,0),(-1,-1), 5),
            ('BOTTOMPADDING',(0,0),(-1,-1), 5),
            ('LEFTPADDING', (0,0),(-1,-1), 6),
        ]))
        story.append(pt)
        story.append(Spacer(1, 0.3*cm))

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

def render_comercial(*_):
    """Módulo Comercial — Pipeline, Visitas, Clientes, Ranking."""

    # ── Carregar dados ────────────────────────────────────────────
    oport_db   = _load("comercial_oportunidades.csv", [
        "ID", "Nome", "Cliente", "Setor", "Comercial",
        "Stage", "Valor_Est", "Prob_Fecho", "Data_Criacao",
        "Data_Fecho_Est", "Origem", "Notas", "Obra_Associada"
    ])
    visitas_db = _load("comercial_visitas.csv", [
        "ID", "Cliente", "Contacto", "Comercial", "Data",
        "Hora", "Tipo", "Local", "Oportunidade_ID",
        "Estado", "Resultado", "Proxima_Acao", "Notas"
    ])
    clientes_db = _load("comercial_clientes.csv", [
        "ID", "Nome", "NIF", "Setor", "Morada", "Email",
        "Telefone", "Contacto", "Comercial_Resp",
        "Data_Angariacao", "Origem", "Potencial", "Notas"
    ])

    try:
        from mod_admin_diarias import _get_config_empresa
        empresa = _get_config_empresa()
    except:
        empresa = {"nome": "Correia Plácido e Sousa, Lda.", "nif": "517182718"}

    user_nome = st.session_state.get('user', 'Admin')
    hoje      = date.today()

    # ── Alertas de visitas próximas ───────────────────────────────
    alertas_visitas = []
    if not visitas_db.empty and 'Data' in visitas_db.columns:
        vp = visitas_db[visitas_db.get('Estado', '') != 'Realizada'].copy() \
             if 'Estado' in visitas_db.columns else visitas_db.copy()
        for _, v in vp.iterrows():
            dias = _dias_para(v.get('Data', ''))
            if dias <= 2:
                alertas_visitas.append({
                    "cliente": v.get('Cliente', ''),
                    "data":    v.get('Data', ''),
                    "hora":    v.get('Hora', ''),
                    "dias":    dias,
                    "tipo":    v.get('Tipo', ''),
                })

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .com-card {
        background:#1E293B; border-radius:12px;
        padding:14px 16px; margin-bottom:8px;
        border-left:4px solid #3B82F6;
        transition:transform 0.15s;
    }
    .com-card:hover { transform:translateX(3px); }
    .stage-badge {
        display:inline-block; padding:3px 10px;
        border-radius:20px; font-size:0.72rem; font-weight:700;
    }
    .alerta-visita {
        border-radius:8px; padding:10px 14px;
        margin-bottom:6px; border-left:4px solid;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Alertas topo ──────────────────────────────────────────────
    if alertas_visitas:
        for av in alertas_visitas:
            cor_av = "#EF4444" if av['dias'] <= 0 \
                     else "#F59E0B" if av['dias'] == 1 \
                     else "#3B82F6"
            txt_av = "HOJE" if av['dias'] == 0 \
                     else "AMANHÃ" if av['dias'] == 1 \
                     else f"em {av['dias']} dias" if av['dias'] > 0 \
                     else "EM ATRASO"
            st.markdown(
                f"<div class='alerta-visita' "
                f"style='background:{cor_av}12;"
                f"border-left-color:{cor_av};'>"
                f"<b style='color:{cor_av};'>🗓️ Visita {txt_av}:</b> "
                f"{av['cliente']} — {av['data']} {av['hora']} "
                f"({av['tipo']})"
                f"</div>",
                unsafe_allow_html=True
            )

    # ── KPIs ──────────────────────────────────────────────────────
    total_oport   = len(oport_db) if not oport_db.empty else 0
    oport_ativas  = len(oport_db[
        ~oport_db.get('Stage', pd.Series()).isin(['ganho', 'perdido'])
    ]) if not oport_db.empty and 'Stage' in oport_db.columns else 0
    val_pipeline  = _num(oport_db, 'Valor_Est')
    ganhos_n      = len(oport_db[oport_db['Stage'] == 'ganho']) \
                    if not oport_db.empty and 'Stage' in oport_db.columns else 0
    taxa_conv     = round(ganhos_n / total_oport * 100, 1) \
                    if total_oport > 0 else 0
    n_visitas_mes = 0
    if not visitas_db.empty and 'Data' in visitas_db.columns:
        vdb2 = visitas_db.copy()
        vdb2['Data_d'] = pd.to_datetime(
            vdb2['Data'], dayfirst=True, errors='coerce'
        )
        n_visitas_mes = len(vdb2[
            (vdb2['Data_d'].dt.month == hoje.month) &
            (vdb2['Data_d'].dt.year  == hoje.year)
        ])
    n_clientes = len(clientes_db) if not clientes_db.empty else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("📋 Oportunidades",  oport_ativas)
    with c2: st.metric("💰 Pipeline",        f"\u20AC{val_pipeline:,.0f}")
    with c3: st.metric("✅ Ganhos",           ganhos_n)
    with c4: st.metric("🎯 Conversão",        f"{taxa_conv:.1f}%")
    with c5: st.metric("🗓️ Visitas/Mês",     n_visitas_mes)
    with c6: st.metric("👥 Clientes",         n_clientes)

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_pipeline, t_visitas, t_clientes,
     t_ranking, t_relatorio) = st.tabs([
        "📊 Pipeline",
        "🗓️ Visitas",
        "👥 Clientes & Angariações",
        "🏆 Ranking",
        "📤 Relatório",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — PIPELINE
    # ════════════════════════════════════════════════════════════════
    with t_pipeline:
        st.markdown("### 📊 Pipeline Comercial")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.plotly_chart(
                _grafico_funil_pipeline(oport_db),
                use_container_width=True, key="funil_pipeline"
            )
        with col_p2:
            st.plotly_chart(
                _grafico_valor_pipeline(oport_db),
                use_container_width=True, key="valor_pipeline"
            )

        st.markdown("---")

        # Formulário nova oportunidade
        col_form_p, col_lista_p = st.columns([1, 2])

        with col_form_p:
            st.markdown("#### ➕ Nova Oportunidade")
            with st.form("form_oportunidade"):
                op_nome    = st.text_input("Nome da Oportunidade *", key="op_nome")
                op_cliente = st.text_input("Cliente *", key="op_cliente")
                op_setor   = st.selectbox("Setor",
                    ["Construção", "Indústria", "Petroquímica",
                     "Energia", "Farmacêutica", "Alimentar",
                     "Serviços", "Outro"],
                    key="op_setor"
                )
                op_comercial = st.text_input(
                    "Comercial Responsável",
                    value=user_nome, key="op_comercial"
                )
                op_stage = st.selectbox(
                    "Stage",
                    STAGE_NOMES,
                    key="op_stage"
                )
                op_valor = st.number_input(
                    "Valor Estimado (€)",
                    min_value=0.0, step=1000.0, key="op_valor"
                )
                op_fecho = st.text_input(
                    "Data Fecho Estimada (dd/mm/aaaa)",
                    key="op_fecho",
                    placeholder="31/12/2025"
                )
                op_origem = st.selectbox(
                    "Origem",
                    ["Prospecção", "Referência", "Inbound",
                     "Networking", "Licitação Pública", "Outro"],
                    key="op_origem"
                )
                op_notas = st.text_area("Notas", key="op_notas")

                if st.form_submit_button(
                    "💾 Guardar Oportunidade",
                    use_container_width=True, type="primary"
                ):
                    if not op_nome.strip() or not op_cliente.strip():
                        st.error("❌ Nome e cliente obrigatórios.")
                    else:
                        stage_id = STAGE_IDS[STAGE_NOMES.index(op_stage)]
                        stage_info = _get_stage(stage_id)
                        nova_op = pd.DataFrame([{
                            "ID":             str(uuid.uuid4())[:8].upper(),
                            "Nome":           op_nome.strip(),
                            "Cliente":        op_cliente.strip(),
                            "Setor":          op_setor,
                            "Comercial":      op_comercial.strip(),
                            "Stage":          stage_id,
                            "Valor_Est":      op_valor,
                            "Prob_Fecho":     stage_info['prob'],
                            "Data_Criacao":   _hoje_str(),
                            "Data_Fecho_Est": op_fecho.strip(),
                            "Origem":         op_origem,
                            "Notas":          op_notas.strip(),
                            "Obra_Associada": ""
                        }])
                        upd_op = pd.concat(
                            [oport_db, nova_op], ignore_index=True
                        ) if not oport_db.empty else nova_op
                        save_db(upd_op, "comercial_oportunidades.csv")
                        log_audit(user_nome, "CRIAR_OPORTUNIDADE",
                                  "comercial_oportunidades.csv",
                                  nova_op['ID'].iloc[0],
                                  f"{op_nome} | {op_cliente} | \u20AC{op_valor:,.0f}", "")
                        inv()
                        st.success(f"✅ Oportunidade criada!")
                        st.rerun()

        with col_lista_p:
            st.markdown("#### 📋 Oportunidades Ativas")

            # Filtros
            col_pf1, col_pf2 = st.columns(2)
            with col_pf1:
                stage_filt = st.selectbox(
                    "Stage", ["Todos"] + STAGE_NOMES, key="pipe_stage_filt"
                )
            with col_pf2:
                com_filt = st.selectbox(
                    "Comercial",
                    ["Todos"] + (
                        oport_db['Comercial'].dropna().unique().tolist()
                        if not oport_db.empty and 'Comercial' in oport_db.columns
                        else []
                    ),
                    key="pipe_com_filt"
                )

            df_pipe = oport_db.copy() if not oport_db.empty else pd.DataFrame()
            if not df_pipe.empty and stage_filt != "Todos":
                stage_id_f = STAGE_IDS[STAGE_NOMES.index(stage_filt)]
                df_pipe = df_pipe[df_pipe['Stage'] == stage_id_f]
            if not df_pipe.empty and com_filt != "Todos":
                df_pipe = df_pipe[df_pipe['Comercial'] == com_filt]

            if df_pipe.empty:
                st.info("📋 Sem oportunidades. Cria a primeira no formulário.")
            else:
                for _, op in df_pipe.sort_values(
                    'Data_Criacao', ascending=False
                ).iterrows():
                    op_id     = op.get('ID', '')
                    stage_inf = _get_stage(op.get('Stage', 'prospeto'))
                    val_op    = float(op.get('Valor_Est', 0) or 0)
                    dias_fecho = _dias_para(op.get('Data_Fecho_Est', ''))

                    # Alerta de fecho
                    alerta_f = ""
                    if op.get('Stage') not in ['ganho', 'perdido']:
                        if dias_fecho < 0:
                            alerta_f = "<span style='color:#EF4444;font-size:0.72rem;'>⚠️ Data fecho ultrapassada</span>"
                        elif dias_fecho <= 14:
                            alerta_f = f"<span style='color:#F59E0B;font-size:0.72rem;'>⏰ Fecho em {dias_fecho} dias</span>"

                    col_oi, col_oa = st.columns([5, 1])
                    with col_oi:
                        st.markdown(
                            f"<div class='com-card' "
                            f"style='border-left-color:{stage_inf['cor']};'>"
                            f"<div style='display:flex;justify-content:space-between;"
                            f"align-items:flex-start;'>"
                            f"<div>"
                            f"<b style='color:#F1F5F9;font-size:0.9rem;'>"
                            f"{op.get('Nome', '')}</b><br>"
                            f"<small style='color:#64748B;'>"
                            f"🏢 {op.get('Cliente', '')} · "
                            f"👤 {op.get('Comercial', '')} · "
                            f"📅 {op.get('Data_Fecho_Est', '')}"
                            f"</small><br>{alerta_f}"
                            f"</div>"
                            f"<div style='text-align:right;'>"
                            f"<b style='color:#F1F5F9;font-size:1rem;'>"
                            f"\u20AC{val_op:,.0f}</b><br>"
                            f"<span class='stage-badge' "
                            f"style='background:{stage_inf['cor']}22;"
                            f"color:{stage_inf['cor']};'>"
                            f"{stage_inf['nome']}</span>"
                            f"</div></div></div>",
                            unsafe_allow_html=True
                        )
                    with col_oa:
                        novo_stage = st.selectbox(
                            "Stage",
                            STAGE_NOMES,
                            key=f"op_st_{op_id}",
                            label_visibility="collapsed"
                        )
                        if st.button("✅", key=f"op_upd_{op_id}",
                                     use_container_width=True):
                            new_sid = STAGE_IDS[STAGE_NOMES.index(novo_stage)]
                            oport_db.loc[oport_db['ID'] == op_id, 'Stage'] = new_sid
                            save_db(oport_db, "comercial_oportunidades.csv")
                            inv(); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — VISITAS
    # ════════════════════════════════════════════════════════════════
    with t_visitas:
        st.markdown("### 🗓️ Gestão de Visitas Comerciais")

        # Alertas visitas próximas
        if alertas_visitas:
            st.markdown("#### ⚡ Visitas nas Próximas 48h")
            for av in alertas_visitas:
                cor_av = "#EF4444" if av['dias'] <= 0 else "#F59E0B"
                st.markdown(
                    f"<div class='alerta-visita' "
                    f"style='background:{cor_av}12;"
                    f"border-left-color:{cor_av};'>"
                    f"<b style='color:{cor_av};'>"
                    f"🗓️ {av['cliente']}</b> — "
                    f"{av['data']} às {av['hora']} · {av['tipo']}"
                    f"</div>",
                    unsafe_allow_html=True
                )
            st.markdown("---")

        col_vf, col_vl = st.columns([1, 2])

        with col_vf:
            st.markdown("#### ➕ Agendar Visita")
            with st.form("form_visita"):
                v_cliente  = st.text_input("Cliente *", key="v_cliente")
                v_contacto = st.text_input("Contacto", key="v_contacto")
                v_comercial = st.text_input(
                    "Comercial", value=user_nome, key="v_comercial"
                )
                v_tipo = st.selectbox("Tipo de Visita",
                    ["Visita Presencial", "Videochamada",
                     "Chamada Telefónica", "Almoço de Negócios",
                     "Apresentação", "Demo Técnica", "Follow-up"],
                    key="v_tipo"
                )
                col_vd1, col_vd2 = st.columns(2)
                with col_vd1:
                    v_data = st.date_input(
                        "Data *", value=hoje + timedelta(days=1),
                        key="v_data"
                    )
                with col_vd2:
                    v_hora = st.time_input(
                        "Hora", key="v_hora",
                        value=datetime.strptime("09:00", "%H:%M").time()
                    )
                v_local = st.text_input(
                    "Local", key="v_local",
                    placeholder="Morada ou link video"
                )
                # Associar a oportunidade
                oport_opts = ["—"] + (
                    oport_db['Nome'].tolist()
                    if not oport_db.empty and 'Nome' in oport_db.columns
                    else []
                )
                v_oport = st.selectbox(
                    "Oportunidade Associada",
                    oport_opts, key="v_oport"
                )
                v_notas = st.text_area("Notas / Agenda", key="v_notas")

                if st.form_submit_button(
                    "📅 Agendar Visita",
                    use_container_width=True, type="primary"
                ):
                    if not v_cliente.strip():
                        st.error("❌ Cliente obrigatório.")
                    else:
                        # Encontrar ID da oportunidade
                        oport_id = ""
                        if v_oport != "—" and not oport_db.empty:
                            m = oport_db[oport_db['Nome'] == v_oport]
                            if not m.empty:
                                oport_id = m.iloc[0].get('ID', '')

                        nova_v = pd.DataFrame([{
                            "ID":             str(uuid.uuid4())[:8].upper(),
                            "Cliente":        v_cliente.strip(),
                            "Contacto":       v_contacto.strip(),
                            "Comercial":      v_comercial.strip(),
                            "Data":           v_data.strftime("%d/%m/%Y"),
                            "Hora":           v_hora.strftime("%H:%M"),
                            "Tipo":           v_tipo,
                            "Local":          v_local.strip(),
                            "Oportunidade_ID":oport_id,
                            "Estado":         "Agendada",
                            "Resultado":      "",
                            "Proxima_Acao":   "",
                            "Notas":          v_notas.strip()
                        }])
                        upd_v = pd.concat(
                            [visitas_db, nova_v], ignore_index=True
                        ) if not visitas_db.empty else nova_v
                        save_db(upd_v, "comercial_visitas.csv")
                        inv()
                        st.success(
                            f"✅ Visita agendada para "
                            f"{v_data.strftime('%d/%m/%Y')} "
                            f"às {v_hora.strftime('%H:%M')}!"
                        )
                        st.rerun()

        with col_vl:
            st.markdown("#### 📋 Visitas Agendadas & Histórico")

            # Gráfico distribuição semanal
            fig_vsem = _grafico_visitas_semana(visitas_db)
            if fig_vsem:
                st.plotly_chart(
                    fig_vsem, use_container_width=True,
                    key="visitas_semana"
                )

            if visitas_db.empty:
                st.info("📋 Sem visitas agendadas.")
            else:
                # Filtro estado
                est_v_filt = st.selectbox(
                    "Estado",
                    ["Todas", "Agendada", "Realizada", "Cancelada"],
                    key="v_est_filt"
                )
                df_vis = visitas_db.copy()
                if est_v_filt != "Todas":
                    df_vis = df_vis[
                        df_vis.get('Estado', pd.Series()) == est_v_filt
                    ] if 'Estado' in df_vis.columns else df_vis

                # Ordenar por data
                if 'Data' in df_vis.columns:
                    df_vis['_sort'] = pd.to_datetime(
                        df_vis['Data'], dayfirst=True, errors='coerce'
                    )
                    df_vis = df_vis.sort_values('_sort', ascending=True)

                for _, vis in df_vis.iterrows():
                    vid       = vis.get('ID', '')
                    est_v     = vis.get('Estado', 'Agendada')
                    dias_v    = _dias_para(vis.get('Data', ''))
                    cor_v     = {
                        'Agendada':  '#3B82F6',
                        'Realizada': '#10B981',
                        'Cancelada': '#64748B',
                    }.get(est_v, '#6B7280')

                    # Badge data
                    if est_v == 'Agendada':
                        if dias_v < 0:
                            badge_v = "⚠️ EM ATRASO"
                            cor_badge = "#EF4444"
                        elif dias_v == 0:
                            badge_v = "🔴 HOJE"
                            cor_badge = "#EF4444"
                        elif dias_v == 1:
                            badge_v = "🟡 AMANHÃ"
                            cor_badge = "#F59E0B"
                        else:
                            badge_v = f"📅 em {dias_v}d"
                            cor_badge = "#3B82F6"
                    else:
                        badge_v   = est_v
                        cor_badge = cor_v

                    col_vi, col_va = st.columns([5, 1])
                    with col_vi:
                        st.markdown(
                            f"<div class='com-card' "
                            f"style='border-left-color:{cor_v};'>"
                            f"<div style='display:flex;"
                            f"justify-content:space-between;'>"
                            f"<div>"
                            f"<b style='color:#F1F5F9;"
                            f"font-size:0.9rem;'>"
                            f"{vis.get('Cliente', '')}</b><br>"
                            f"<small style='color:#64748B;'>"
                            f"📅 {vis.get('Data', '')} "
                            f"às {vis.get('Hora', '')} · "
                            f"{vis.get('Tipo', '')} · "
                            f"👤 {vis.get('Comercial', '')}"
                            f"</small>"
                            f"{'<br><small style=color:#94A3B8;>' + vis.get('Local','') + '</small>' if vis.get('Local') else ''}"
                            f"</div>"
                            f"<span style='color:{cor_badge};"
                            f"font-weight:700;font-size:0.8rem;'>"
                            f"{badge_v}</span>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
                    with col_va:
                        novo_est_v = st.selectbox(
                            "Estado",
                            ["Agendada", "Realizada", "Cancelada"],
                            key=f"v_est_{vid}",
                            label_visibility="collapsed"
                        )
                        if st.button("✅", key=f"v_upd_{vid}",
                                     use_container_width=True):
                            visitas_db.loc[
                                visitas_db['ID'] == vid, 'Estado'
                            ] = novo_est_v
                            save_db(visitas_db, "comercial_visitas.csv")
                            inv(); st.rerun()

                    # Resultado da visita (se realizada)
                    if est_v == 'Realizada':
                        with st.expander(
                            f"📝 Resultado — {vis.get('Cliente', '')}",
                            expanded=False
                        ):
                            col_res1, col_res2 = st.columns(2)
                            with col_res1:
                                res_txt = st.text_area(
                                    "Resultado",
                                    value=vis.get('Resultado', ''),
                                    key=f"v_res_{vid}"
                                )
                            with col_res2:
                                prox_acao = st.text_input(
                                    "Próxima Ação",
                                    value=vis.get('Proxima_Acao', ''),
                                    key=f"v_prox_{vid}"
                                )
                            if st.button(
                                "💾 Guardar Resultado",
                                key=f"v_res_save_{vid}",
                                use_container_width=True
                            ):
                                visitas_db.loc[
                                    visitas_db['ID'] == vid, 'Resultado'
                                ] = res_txt
                                visitas_db.loc[
                                    visitas_db['ID'] == vid, 'Proxima_Acao'
                                ] = prox_acao
                                save_db(visitas_db, "comercial_visitas.csv")
                                inv()
                                st.success("✅ Resultado guardado!")
                                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — CLIENTES & ANGARIAÇÕES
    # ════════════════════════════════════════════════════════════════
    with t_clientes:
        st.markdown("### 👥 Clientes & Angariações")

        # Gráfico novos clientes
        fig_nc = _grafico_novos_clientes_mes(clientes_db)
        if fig_nc:
            st.plotly_chart(
                fig_nc, use_container_width=True,
                key="novos_clientes_mes"
            )

        col_cf, col_cl = st.columns([1, 2])

        with col_cf:
            st.markdown("#### ➕ Registar Cliente Angariado")
            with st.form("form_cliente_com"):
                cc_nome    = st.text_input("Nome da Empresa *", key="cc_nome")
                cc_nif     = st.text_input("NIF", key="cc_nif",
                                            placeholder="123456789")
                cc_setor   = st.selectbox("Setor",
                    ["Construção", "Indústria", "Petroquímica",
                     "Energia", "Farmacêutica", "Alimentar",
                     "Serviços Técnicos", "Outro"],
                    key="cc_setor"
                )
                cc_contacto = st.text_input("Contacto Principal", key="cc_contacto")
                cc_email    = st.text_input("Email", key="cc_email")
                cc_tel      = st.text_input("Telefone", key="cc_tel")
                cc_morada   = st.text_input("Morada", key="cc_morada")
                cc_comercial = st.text_input(
                    "Comercial Responsável",
                    value=user_nome, key="cc_comercial"
                )
                cc_data = st.date_input(
                    "Data de Angariação",
                    value=hoje, key="cc_data"
                )
                cc_origem = st.selectbox(
                    "Origem da Angariação",
                    ["Prospecção Directa", "Referência de Cliente",
                     "Networking / Evento", "Licitação Pública",
                     "Inbound / Website", "Parceiro", "Outro"],
                    key="cc_origem"
                )
                cc_potencial = st.selectbox(
                    "Potencial",
                    ["Alto", "Médio", "Baixo"],
                    key="cc_potencial"
                )
                cc_notas = st.text_area("Notas", key="cc_notas")

                if st.form_submit_button(
                    "💾 Registar Cliente",
                    use_container_width=True, type="primary"
                ):
                    if not cc_nome.strip():
                        st.error("❌ Nome obrigatório.")
                    else:
                        novo_c = pd.DataFrame([{
                            "ID":              str(uuid.uuid4())[:8].upper(),
                            "Nome":            cc_nome.strip(),
                            "NIF":             cc_nif.strip(),
                            "Setor":           cc_setor,
                            "Morada":          cc_morada.strip(),
                            "Email":           cc_email.strip(),
                            "Telefone":        cc_tel.strip(),
                            "Contacto":        cc_contacto.strip(),
                            "Comercial_Resp":  cc_comercial.strip(),
                            "Data_Angariacao": cc_data.strftime("%d/%m/%Y"),
                            "Origem":          cc_origem,
                            "Potencial":       cc_potencial,
                            "Notas":           cc_notas.strip()
                        }])
                        upd_c = pd.concat(
                            [clientes_db, novo_c], ignore_index=True
                        ) if not clientes_db.empty else novo_c
                        save_db(upd_c, "comercial_clientes.csv")
                        log_audit(user_nome, "ANGARIAR_CLIENTE",
                                  "comercial_clientes.csv",
                                  novo_c['ID'].iloc[0],
                                  f"{cc_nome} | {cc_origem}", "")
                        inv()
                        st.success(f"✅ Cliente {cc_nome} angariado!")
                        st.rerun()

        with col_cl:
            st.markdown("#### 📋 Clientes Angariados")

            if clientes_db.empty:
                st.info("📋 Sem clientes registados.")
            else:
                # Filtro potencial
                pot_filt = st.selectbox(
                    "Potencial",
                    ["Todos", "Alto", "Médio", "Baixo"],
                    key="cli_pot_filt"
                )
                df_cli = clientes_db.copy()
                if pot_filt != "Todos" and 'Potencial' in df_cli.columns:
                    df_cli = df_cli[df_cli['Potencial'] == pot_filt]

                for _, cli in df_cli.sort_values(
                    'Data_Angariacao', ascending=False
                ).iterrows():
                    pot   = cli.get('Potencial', 'Médio')
                    cor_p = {
                        'Alto':  '#10B981',
                        'Médio': '#F59E0B',
                        'Baixo': '#64748B',
                    }.get(pot, '#6B7280')

                    st.markdown(
                        f"<div class='com-card' "
                        f"style='border-left-color:{cor_p};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:0.9rem;'>"
                        f"{cli.get('Nome', '')}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"🏭 {cli.get('Setor', '')} · "
                        f"👤 {cli.get('Contacto', '')} · "
                        f"📅 {cli.get('Data_Angariacao', '')} · "
                        f"🎯 {cli.get('Origem', '')}"
                        f"</small><br>"
                        f"<small style='color:#475569;'>"
                        f"📧 {cli.get('Email', '')} · "
                        f"📞 {cli.get('Telefone', '')}"
                        f"</small>"
                        f"</div>"
                        f"<span style='color:{cor_p};"
                        f"font-weight:700;font-size:0.85rem;'>"
                        f"⭐ {pot}</span>"
                        f"</div></div>",
                        unsafe_allow_html=True
                    )

    # ════════════════════════════════════════════════════════════════
    # TAB — RANKING
    # ════════════════════════════════════════════════════════════════
    with t_ranking:
        st.markdown("### 🏆 Ranking Comercial")

        col_rk1, col_rk2 = st.columns(2)
        with col_rk1:
            # Taxa de conversão gauge
            st.plotly_chart(
                _grafico_taxa_conversao(oport_db),
                use_container_width=True, key="taxa_conversao"
            )
        with col_rk2:
            # Ranking comerciais
            fig_rank = _grafico_ranking_comerciais(oport_db)
            if fig_rank:
                st.plotly_chart(
                    fig_rank, use_container_width=True,
                    key="ranking_comerciais"
                )
            else:
                st.info("📋 Sem dados suficientes para ranking.")

        # Tabela de ranking detalhado
        st.markdown("---")
        st.markdown("#### 📊 Tabela de Performance")

        if not oport_db.empty and 'Comercial' in oport_db.columns:
            comerciais = oport_db['Comercial'].dropna().unique().tolist()
            rows_rank  = []
            for com in comerciais:
                df_com     = oport_db[oport_db['Comercial'] == com]
                n_total    = len(df_com)
                n_ganhos   = len(df_com[df_com['Stage'] == 'ganho'])
                n_perdidos = len(df_com[df_com['Stage'] == 'perdido'])
                n_ativos   = n_total - n_ganhos - n_perdidos
                val_ganho  = pd.to_numeric(
                    df_com[df_com['Stage'] == 'ganho'].get('Valor_Est', 0),
                    errors='coerce'
                ).fillna(0).sum()
                val_pipe   = pd.to_numeric(
                    df_com[~df_com['Stage'].isin(['ganho', 'perdido'])].get('Valor_Est', 0),
                    errors='coerce'
                ).fillna(0).sum()
                taxa_c = round(n_ganhos / n_total * 100, 1) if n_total > 0 else 0

                # Visitas do comercial
                n_vis_com = 0
                if not visitas_db.empty and 'Comercial' in visitas_db.columns:
                    n_vis_com = len(visitas_db[visitas_db['Comercial'] == com])

                # Clientes angariados
                n_cli_com = 0
                if not clientes_db.empty and 'Comercial_Resp' in clientes_db.columns:
                    n_cli_com = len(clientes_db[clientes_db['Comercial_Resp'] == com])

                rows_rank.append({
                    "Comercial":     com,
                    "Oport. Ativas": n_ativos,
                    "Ganhos":        n_ganhos,
                    "Perdidos":      n_perdidos,
                    "Conversão":     f"{taxa_c:.1f}%",
                    "Val. Ganho":    f"\u20AC{val_ganho:,.0f}",
                    "Pipeline":      f"\u20AC{val_pipe:,.0f}",
                    "Visitas":       n_vis_com,
                    "Clientes":      n_cli_com,
                })

            if rows_rank:
                df_rank = pd.DataFrame(rows_rank)
                # Ordenar por valor ganho
                df_rank['_sort'] = df_rank['Val. Ganho'].str.replace(
                    '[€,]', '', regex=True
                ).str.strip()
                df_rank = df_rank.sort_values('_sort', ascending=False).drop(columns=['_sort'])

                st.dataframe(df_rank, use_container_width=True, hide_index=True)

                # Medalhas top 3
                if len(rows_rank) >= 1:
                    st.markdown("#### 🥇 Top Comerciais")
                    medalhas = ["🥇", "🥈", "🥉"]
                    for i, row in enumerate(rows_rank[:3]):
                        med = medalhas[i] if i < 3 else "🏅"
                        cor_m = ["#F59E0B", "#94A3B8", "#CD7F32"][i] \
                                if i < 3 else "#64748B"
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:10px;padding:14px;"
                            f"margin-bottom:6px;"
                            f"border-left:4px solid {cor_m};'>"
                            f"<b style='color:{cor_m};"
                            f"font-size:1.1rem;'>"
                            f"{med} {row['Comercial']}</b>"
                            f"<span style='float:right;"
                            f"color:#10B981;font-weight:700;'>"
                            f"{row['Val. Ganho']} ganho</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"Ganhos: {row['Ganhos']} · "
                            f"Conversão: {row['Conversão']} · "
                            f"Visitas: {row['Visitas']} · "
                            f"Clientes: {row['Clientes']}"
                            f"</small></div>",
                            unsafe_allow_html=True
                        )
        else:
            st.info("📋 Sem dados de comerciais para ranking.")

        # Ranking angariações de novos clientes
        st.markdown("---")
        st.markdown("#### 🌟 Ranking de Angariações")

        if not clientes_db.empty and 'Comercial_Resp' in clientes_db.columns:
            grp_ang = clientes_db.groupby('Comercial_Resp').size()\
                                  .reset_index(name='N_Clientes')\
                                  .sort_values('N_Clientes', ascending=False)

            for i, (_, row_a) in enumerate(grp_ang.iterrows()):
                pos   = i + 1
                med_a = "🥇" if pos == 1 else "🥈" if pos == 2 \
                        else "🥉" if pos == 3 else f"#{pos}"
                cor_a = "#F59E0B" if pos == 1 else "#94A3B8" if pos == 2 \
                        else "#CD7F32" if pos == 3 else "#334155"

                # Calcular alto potencial
                df_ang_com = clientes_db[
                    clientes_db['Comercial_Resp'] == row_a['Comercial_Resp']
                ]
                n_alto = len(df_ang_com[
                    df_ang_com.get('Potencial', '') == 'Alto'
                ]) if 'Potencial' in df_ang_com.columns else 0

                st.markdown(
                    f"<div style='background:#1E293B;"
                    f"border-radius:8px;padding:10px 14px;"
                    f"margin-bottom:6px;"
                    f"border-left:3px solid {cor_a};'>"
                    f"<b style='color:{cor_a};'>"
                    f"{med_a} {row_a['Comercial_Resp']}</b>"
                    f"<span style='float:right;"
                    f"color:#10B981;font-weight:700;'>"
                    f"{row_a['N_Clientes']} cliente(s)</span><br>"
                    f"<small style='color:#64748B;'>"
                    f"Alto potencial: {n_alto}"
                    f"</small></div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("📋 Sem angariações registadas.")

    # ════════════════════════════════════════════════════════════════
    # TAB — RELATÓRIO
    # ════════════════════════════════════════════════════════════════
    with t_relatorio:
        st.markdown("### 📤 Relatório Comercial")
        st.info(
            "Gera relatório completo do pipeline, visitas "
            "e ranking para apresentar à direção."
        )

        col_re1, col_re2 = st.columns(2)
        with col_re1:
            st.markdown("#### 📊 Resumo")

            # Valor ponderado pelo pipeline
            val_ponderado = 0.0
            if not oport_db.empty and 'Stage' in oport_db.columns:
                for _, op in oport_db.iterrows():
                    si  = _get_stage(op.get('Stage', 'prospeto'))
                    val = float(op.get('Valor_Est', 0) or 0)
                    val_ponderado += val * si['prob'] / 100

            resumo_items = [
                ("Pipeline Total",       f"\u20AC{val_pipeline:,.2f}"),
                ("Pipeline Ponderado",   f"\u20AC{val_ponderado:,.2f}"),
                ("Oportunidades Ativas", str(oport_ativas)),
                ("Taxa de Conversão",    f"{taxa_conv:.1f}%"),
                ("Visitas este mês",     str(n_visitas_mes)),
                ("Clientes Angariados",  str(n_clientes)),
                ("Alertas Visitas",      str(len(alertas_visitas))),
            ]
            for label, val in resumo_items:
                st.markdown(
                    f"<div style='display:flex;"
                    f"justify-content:space-between;"
                    f"padding:6px 0;border-bottom:1px solid #1E293B;'>"
                    f"<small style='color:#94A3B8;'>{label}</small>"
                    f"<b style='color:#F1F5F9;'>{val}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        with col_re2:
            st.markdown("#### 📥 Exportar")

            col_re_b1, col_re_b2 = st.columns(2)
            with col_re_b1:
                if st.button(
                    "📄 Gerar PDF",
                    key="btn_pdf_comercial",
                    type="primary",
                    use_container_width=True
                ):
                    with st.spinner("A gerar relatório..."):
                        pdf_com = _gerar_pdf_relatorio_comercial(
                            oport_db, visitas_db,
                            clientes_db, empresa
                        )
                    st.session_state['com_pdf'] = pdf_com
                    st.session_state['com_pdf_nome'] = (
                        f"relatorio_comercial_"
                        f"{hoje.strftime('%Y%m%d')}.pdf"
                    )
                    st.success("✅ PDF gerado!")
                    st.rerun()

            with col_re_b2:
                if st.session_state.get('com_pdf'):
                    st.download_button(
                        "📥 Descarregar PDF",
                        data=st.session_state['com_pdf'],
                        file_name=st.session_state.get(
                            'com_pdf_nome', 'relatorio_comercial.pdf'
                        ),
                        mime="application/pdf",
                        key="dl_com_pdf",
                        use_container_width=True,
                        type="primary"
                    )

            # Export CSV oportunidades
            if not oport_db.empty:
                cols_exp = [c for c in [
                    'Nome', 'Cliente', 'Setor', 'Comercial',
                    'Stage', 'Valor_Est', 'Prob_Fecho',
                    'Data_Criacao', 'Data_Fecho_Est', 'Origem'
                ] if c in oport_db.columns]
                csv_op = oport_db[cols_exp].to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    "📥 Exportar Pipeline CSV",
                    data=csv_op.encode('utf-8-sig'),
                    file_name=f"pipeline_{hoje.strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="dl_pipeline_csv",
                    use_container_width=True
                )

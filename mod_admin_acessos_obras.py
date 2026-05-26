"""
GESTNOW v3 — mod_admin_acessos_obras.py
Gestão de Acessos de Colaboradores a Obras
Controlo de documentos, autorizações, alertas e crachás
"""
import streamlit as st
import pandas as pd
import uuid, io, base64
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
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

def _dias_para(data_str: str) -> int:
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return 999

def _cor_dias(dias: int) -> tuple:
    if dias < 0:
        return "#EF4444", "🔴", "EXPIRADO"
    if dias <= 15:
        return "#EF4444", "🔴", f"{dias}d"
    if dias <= 30:
        return "#F59E0B", "🟡", f"{dias}d"
    if dias <= 60:
        return "#F59E0B", "⚠️", f"{dias}d"
    return "#10B981", "🟢", f"{dias}d"

def _estado_acesso_cor(estado: str) -> tuple:
    return {
        "Activo":    ("#10B981", "✅"),
        "Pendente":  ("#F59E0B", "⏳"),
        "Expirado":  ("#EF4444", "🔴"),
        "Suspenso":  ("#EF4444", "⛔"),
        "Revogado":  ("#64748B", "❌"),
    }.get(estado, ("#6B7280", "❓"))


# ─────────────────────────────────────────────────────────────────
# DOCUMENTOS PADRÃO POR TIPO DE OBRA
# ─────────────────────────────────────────────────────────────────

DOCS_PADRAO = {
    "Refinaria / Petroquímica": [
        "Cartão de Cidadão",
        "Exame Médico de Aptidão",
        "Formação HSE Indução Geral",
        "Formação H2S",
        "Formação Trabalho em Altura",
        "Formação ATEX (áreas classificadas)",
        "Seguro Acidentes de Trabalho",
        "Crachá Emitido pelo Cliente",
        "Certificado LOTO/LOTOTO",
        "Formação Espaços Confinados",
    ],
    "Construção Industrial": [
        "Cartão de Cidadão",
        "Exame Médico de Aptidão",
        "Formação HSE Indução Geral",
        "Formação Trabalho em Altura",
        "Seguro Acidentes de Trabalho",
        "Crachá Emitido pelo Cliente",
        "Certificado LOTO/LOTOTO",
    ],
    "Instrumentação / Calibração": [
        "Cartão de Cidadão",
        "Exame Médico de Aptidão",
        "Formação HSE Indução Geral",
        "Seguro Acidentes de Trabalho",
        "Certificados de Calibração Equipamentos",
        "Crachá Emitido pelo Cliente",
    ],
    "Manutenção Industrial": [
        "Cartão de Cidadão",
        "Exame Médico de Aptidão",
        "Formação HSE Indução Geral",
        "Formação Trabalho em Altura",
        "Seguro Acidentes de Trabalho",
        "Crachá Emitido pelo Cliente",
        "Certificado LOTO/LOTOTO",
    ],
    "Outro": [
        "Cartão de Cidadão",
        "Exame Médico de Aptidão",
        "Formação HSE Indução Geral",
        "Seguro Acidentes de Trabalho",
    ],
}

TODOS_DOCS = sorted(set(
    doc for lista in DOCS_PADRAO.values() for doc in lista
))


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_estado_acessos(acessos_db):
    import plotly.graph_objects as go
    if acessos_db.empty or 'Estado' not in acessos_db.columns:
        return None
    grp = acessos_db['Estado'].value_counts()
    cores = {
        'Activo':   '#10B981',
        'Pendente': '#F59E0B',
        'Expirado': '#EF4444',
        'Suspenso': '#DC2626',
        'Revogado': '#64748B',
    }
    fig = go.Figure(go.Pie(
        labels=grp.index.tolist(),
        values=grp.values.tolist(),
        hole=0.5,
        marker={'colors':[cores.get(e,'#6B7280') for e in grp.index],
                'line':{'color':'#0F172A','width':2}},
        textfont={'color':'#F1F5F9','size':11},
        hovertemplate='%{label}: %{value}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Estado dos Acessos',
               'font':{'color':'#F1F5F9'}},
        height=240,
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        margin=dict(t=40,b=10,l=10,r=10),
        annotations=[{
            'text':str(len(acessos_db)),
            'x':0.5,'y':0.5,
            'font_size':20,'font_color':'#F1F5F9',
            'showarrow':False
        }]
    )
    return fig


def _grafico_docs_em_falta(docs_db, acessos_db):
    import plotly.graph_objects as go
    if docs_db.empty:
        return None
    docs_db2 = docs_db.copy()
    docs_db2['Dias_N'] = docs_db2['Validade'].apply(_dias_para)
    expirados = docs_db2[docs_db2['Dias_N'] < 0]
    proximos  = docs_db2[(docs_db2['Dias_N'] >= 0) & (docs_db2['Dias_N'] <= 30)]
    ok        = docs_db2[docs_db2['Dias_N'] > 30]

    fig = go.Figure(go.Bar(
        x=['✅ Válidos','⚠️ Expiram 30d','🔴 Expirados'],
        y=[len(ok), len(proximos), len(expirados)],
        marker_color=['#10B981','#F59E0B','#EF4444'],
        text=[len(ok), len(proximos), len(expirados)],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':12}
    ))
    fig.update_layout(
        title={'text':'Estado dos Documentos',
               'font':{'color':'#F1F5F9'}},
        height=220,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF CARTÃO DE ACESSO
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_cartao_acesso(colaborador: str,
                              obra: str,
                              nivel: str,
                              validade: str,
                              docs_ok: list,
                              empresa: dict,
                              foto_b64: str = "") -> bytes:
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
        fontSize=10, fontName='Helvetica-Bold', spaceAfter=3
    )
    sub_s = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#64748B'), spaceAfter=2
    )
    normal_s = ParagraphStyle(
        'normal', parent=styles['Normal'],
        fontSize=9, spaceAfter=3
    )

    # Cabeçalho
    story.append(Paragraph(
        "AUTORIZAÇÃO DE ACESSO A OBRA",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=16, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'),
                       spaceAfter=4, alignment=1)
    ))
    story.append(Paragraph(
        empresa.get('nome',''),
        ParagraphStyle('emp', parent=styles['Normal'],
                       fontSize=11, spaceAfter=2, alignment=1,
                       textColor=colors.HexColor('#3B82F6'))
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    # Dados
    dados = [
        ["Colaborador:",  colaborador],
        ["Obra / Local:", obra],
        ["Nível Acesso:", nivel],
        ["Válido até:",   validade],
        ["Emitido em:",   date.today().strftime("%d/%m/%Y")],
        ["Emitido por:",  empresa.get('nome','')],
    ]
    dt = Table(dados, colWidths=[5*cm, 12*cm])
    dt.setStyle(TableStyle([
        ('FONTNAME',    (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0),(-1,-1), 10),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('BACKGROUND',  (0,0),(0,-1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING',  (0,0),(-1,-1), 7),
        ('BOTTOMPADDING',(0,0),(-1,-1), 7),
        ('LEFTPADDING', (0,0),(-1,-1), 8),
    ]))
    story.append(dt)
    story.append(Spacer(1, 0.4*cm))

    # Documentos verificados
    story.append(Paragraph(
        "<b>DOCUMENTOS VERIFICADOS E VÁLIDOS:</b>", bold_s
    ))
    for doc_ok in docs_ok:
        story.append(Paragraph(f"✓ {doc_ok}", normal_s))
    story.append(Spacer(1, 0.4*cm))

    # Condições
    story.append(Paragraph(
        "<b>CONDIÇÕES DE ACESSO:</b>", bold_s
    ))
    condicoes = [
        "O titular deve apresentar este documento à entrada da obra.",
        "O acesso é pessoal e intransmissível.",
        "O acesso será revogado em caso de incumprimento das "
        "regras de segurança.",
        "Os EPIs obrigatórios devem ser usados em todas as áreas.",
        "Em caso de emergência, seguir os planos de evacuação da obra.",
    ]
    for c in condicoes:
        story.append(Paragraph(f"• {c}", normal_s))
    story.append(Spacer(1, 0.6*cm))

    # Assinaturas
    ass_data = [
        ["Responsável da Obra:",    "Responsável da Empresa:"],
        ["_____________________",   "_____________________"],
        ["Data: ___/___/______",     "Data: ___/___/______"],
    ]
    at = Table(ass_data, colWidths=[8.5*cm, 8.5*cm])
    at.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
        ('TOPPADDING',  (0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
    ]))
    story.append(at)
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Paragraph(
        f"GESTNOW v3.0 · Gestão de Acessos · "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')} · Confidencial",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey,
                       alignment=1)
    ))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _gerar_pdf_relatorio_acessos(obra: str,
                                  acessos_obra: pd.DataFrame,
                                  docs_db: pd.DataFrame,
                                  empresa: dict) -> bytes:
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
        fontSize=10, fontName='Helvetica-Bold', spaceAfter=3
    )
    sub_s = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#64748B'), spaceAfter=2
    )
    normal_s = ParagraphStyle(
        'normal', parent=styles['Normal'],
        fontSize=9, spaceAfter=3
    )

    story.append(Paragraph(
        f"RELATÓRIO DE ACESSOS — {obra.upper()}",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=14, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'),
                       spaceAfter=4)
    ))
    story.append(Paragraph(
        f"{empresa.get('nome','')} · "
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_s
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    # Resumo
    n_activos = len(acessos_obra[acessos_obra.get('Estado','')=='Activo']) \
                if 'Estado' in acessos_obra.columns else 0
    resumo_data = [
        ["Total Colaboradores", str(len(acessos_obra))],
        ["Acessos Activos",     str(n_activos)],
        ["Data do Relatório",   date.today().strftime("%d/%m/%Y")],
    ]
    rt = Table(resumo_data, colWidths=[8*cm, 9*cm])
    rt.setStyle(TableStyle([
        ('FONTNAME',    (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(rt)
    story.append(Spacer(1, 0.4*cm))

    # Tabela de acessos
    story.append(Paragraph("<b>LISTA DE ACESSOS</b>", bold_s))
    header = [["Colaborador","Nível","Data Início",
                "Validade","Estado","Docs OK"]]
    rows   = []
    for _, ac in acessos_obra.iterrows():
        # Contar docs válidos
        n_docs_ok = 0
        if not docs_db.empty and 'Colaborador' in docs_db.columns:
            docs_col = docs_db[
                (docs_db['Colaborador'] == ac.get('Colaborador','')) &
                (docs_db['Obra'] == obra)
            ]
            if not docs_col.empty and 'Validade' in docs_col.columns:
                n_docs_ok = len(docs_col[
                    docs_col['Validade'].apply(_dias_para) >= 0
                ])
        rows.append([
            str(ac.get('Colaborador',''))[:25],
            str(ac.get('Nivel_Acesso','')),
            str(ac.get('Data_Inicio','')),
            str(ac.get('Data_Fim','')),
            str(ac.get('Estado','')),
            str(n_docs_ok),
        ])
    at2 = Table(
        header + rows,
        colWidths=[5*cm,3*cm,2.5*cm,2.5*cm,2.5*cm,1.5*cm]
    )
    at2.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
        ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0),(-1,-1), 8),
        ('GRID',        (0,0),(-1,-1), 0.2, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING',  (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING', (0,0),(-1,-1), 4),
    ]))
    story.append(at2)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"GESTNOW v3.0 · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey)
    ))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_acessos_obras(users, obras_db, *_):
    """Módulo de Gestão de Acessos de Colaboradores a Obras."""

    # ── Carregar dados ────────────────────────────────────────────
    acessos_db = _load("acessos_obras.csv", [
        "ID","Obra","Colaborador","Nivel_Acesso","Data_Inicio",
        "Data_Fim","Estado","Motivo_Suspensao","Cracha_Numero",
        "Cracha_Emitido","Notas","Criado_Por","Criado_Em"
    ])
    docs_db = _load("acessos_documentos.csv", [
        "ID","Colaborador","Obra","Tipo_Doc","Numero_Doc",
        "Emissao","Validade","Verificado_Por","Verificado_Em",
        "Estado_Doc","Ficheiro_b64","Notas"
    ])
    req_db = _load("acessos_requisitos_obras.csv", [
        "ID","Obra","Tipo_Obra","Documentos_Obrigatorios",
        "Nivel_Seguranca","Instrucoes","Atualizado_Em"
    ])

    try:
        from mod_admin_diarias import _get_config_empresa
        empresa = _get_config_empresa()
    except:
        empresa = {
            "nome":"Correia Plácido e Sousa, Lda.",
            "nif":"517182718"
        }

    user_nome  = st.session_state.get('user','Admin')
    hoje       = date.today()
    users_list = users['Nome'].tolist() if not users.empty else []
    obras_list = obras_db[
        obras_db['Ativa']=='Ativa'
    ]['Obra'].tolist() if not obras_db.empty else []

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .acesso-card {
        background:#1E293B; border-radius:12px;
        padding:14px 16px; margin-bottom:8px;
        border-left:5px solid;
    }
    .doc-item {
        display:flex; justify-content:space-between;
        align-items:center; padding:8px 12px;
        border-radius:8px; margin-bottom:4px;
        background:#0F172A;
    }
    .nivel-badge {
        display:inline-block; padding:3px 10px;
        border-radius:20px; font-size:0.72rem; font-weight:700;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🔐 Gestão de Acessos a Obras")

    # ── KPIs ──────────────────────────────────────────────────────
    n_activos  = len(acessos_db[acessos_db['Estado']=='Activo']) \
                 if not acessos_db.empty else 0
    n_pend     = len(acessos_db[acessos_db['Estado']=='Pendente']) \
                 if not acessos_db.empty else 0
    n_expirado = len(acessos_db[acessos_db['Estado']=='Expirado']) \
                 if not acessos_db.empty else 0

    # Documentos a expirar em 30 dias
    n_docs_alerta = 0
    if not docs_db.empty and 'Validade' in docs_db.columns:
        docs_db['Dias_N'] = docs_db['Validade'].apply(_dias_para)
        n_docs_alerta = len(docs_db[
            (docs_db['Dias_N'] >= 0) & (docs_db['Dias_N'] <= 30)
        ])
        n_docs_expirados = len(docs_db[docs_db['Dias_N'] < 0])
        n_docs_alerta += n_docs_expirados

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("✅ Acessos Activos",  n_activos)
    with c2: st.metric("⏳ Pendentes",         n_pend)
    with c3: st.metric("🔴 Expirados",         n_expirado)
    with c4: st.metric("⚠️ Docs Alerta",       n_docs_alerta)
    with c5: st.metric("👷 Colaboradores",
                       acessos_db['Colaborador'].nunique()
                       if not acessos_db.empty else 0)

    st.divider()

    # ── Alertas imediatos no topo ──────────────────────────────────
    if n_docs_alerta > 0 and not docs_db.empty:
        docs_urgentes = docs_db[docs_db['Dias_N'] <= 15].sort_values('Dias_N')
        if not docs_urgentes.empty:
            st.markdown(
                "<div style='background:rgba(239,68,68,0.1);"
                "border:1px solid #EF4444;border-radius:10px;"
                "padding:12px 16px;margin-bottom:12px;'>"
                "<b style='color:#EF4444;'>🚨 Documentos urgentes:</b> " +
                " · ".join([
                    f"{r['Colaborador']} — {r['Tipo_Doc']} "
                    f"({'EXPIRADO' if r['Dias_N']<0 else str(r['Dias_N'])+'d'})"
                    for _, r in docs_urgentes.head(4).iterrows()
                ]) +
                "</div>",
                unsafe_allow_html=True
            )

    # ── Tabs ──────────────────────────────────────────────────────
    (t_painel, t_novo, t_docs,
     t_obra, t_requisitos, t_relatorio) = st.tabs([
        "📊 Painel Geral",
        "➕ Conceder Acesso",
        "📋 Documentos",
        "🏗️ Por Obra",
        "⚙️ Requisitos por Obra",
        "📄 Relatórios",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — PAINEL GERAL
    # ════════════════════════════════════════════════════════════════
    with t_painel:
        st.markdown("#### 📊 Painel de Acessos")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            import plotly.graph_objects as go
            fig_e = _grafico_estado_acessos(acessos_db)
            if fig_e:
                st.plotly_chart(fig_e)
        with col_g2:
            fig_d = _grafico_docs_em_falta(docs_db, acessos_db)
            if fig_d:
                st.plotly_chart(fig_d)

        st.markdown("---")

        # Filtros
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            obra_filt = st.selectbox(
                "Obra", ["Todas"] + obras_list,
                key="painel_obra_filt"
            )
        with col_f2:
            est_filt = st.selectbox(
                "Estado",
                ["Todos","Activo","Pendente","Expirado",
                 "Suspenso","Revogado"],
                key="painel_est_filt"
            )
        with col_f3:
            colab_filt = st.selectbox(
                "Colaborador",
                ["Todos"] + users_list,
                key="painel_colab_filt"
            )

        df_p = acessos_db.copy() if not acessos_db.empty \
               else pd.DataFrame()

        if not df_p.empty:
            if obra_filt  != "Todas":
                df_p = df_p[df_p['Obra']  == obra_filt]
            if est_filt   != "Todos":
                df_p = df_p[df_p['Estado']== est_filt]
            if colab_filt != "Todos":
                df_p = df_p[df_p['Colaborador']== colab_filt]

        if df_p.empty:
            st.info("📋 Sem acessos registados.")
        else:
            for _, ac in df_p.sort_values(
                'Data_Fim', ascending=True
            ).iterrows():
                aid    = ac.get('ID','')
                estado = ac.get('Estado','')
                cor_e, ic_e = _estado_acesso_cor(estado)

                dias_fim = _dias_para(ac.get('Data_Fim',''))
                cor_df, ic_df, txt_df = _cor_dias(dias_fim)

                nivel  = ac.get('Nivel_Acesso','')
                cores_nivel = {
                    'Área Geral':       '#3B82F6',
                    'Área Restrita':    '#F59E0B',
                    'Supervisão':       '#8B5CF6',
                    'Acesso Total':     '#10B981',
                }
                cor_nivel = cores_nivel.get(nivel,'#6B7280')

                # Contar docs do colaborador nesta obra
                n_docs_colab = 0
                n_docs_exp   = 0
                if not docs_db.empty:
                    dc = docs_db[
                        (docs_db['Colaborador']==ac.get('Colaborador','')) &
                        (docs_db['Obra']==ac.get('Obra',''))
                    ]
                    if not dc.empty and 'Dias_N' in dc.columns:
                        n_docs_colab = len(dc[dc['Dias_N'] >= 0])
                        n_docs_exp   = len(dc[dc['Dias_N'] < 0])

                # ── FIX BUG 1 ── extrair motivo_html antes do f-string
                # para evitar backslash dentro de expressão f-string
                # (SyntaxError em Python < 3.12)
                motivo_suspensao = ac.get('Motivo_Suspensao', '')
                if motivo_suspensao:
                    motivo_html = (
                        "<br><small style='color:#F59E0B;'>"
                        + str(motivo_suspensao)
                        + "</small>"
                    )
                else:
                    motivo_html = ""

                docs_exp_html = (
                    f"&nbsp;&nbsp;🔴 {n_docs_exp} expirado(s)"
                    if n_docs_exp > 0 else ""
                )

                col_ac1, col_ac2 = st.columns([6,1])
                with col_ac1:
                    st.markdown(
                        f"<div class='acesso-card' "
                        f"style='border-left-color:{cor_e};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;"
                        f"align-items:flex-start;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;font-size:0.95rem;'>"
                        f"{ic_e} {ac.get('Colaborador','')}</b>"
                        f"<span class='nivel-badge' "
                        f"style='background:{cor_nivel}22;"
                        f"color:{cor_nivel};margin-left:8px;'>"
                        f"{nivel}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"🏗️ {ac.get('Obra','')} · "
                        f"📅 {ac.get('Data_Inicio','')} → "
                        f"{ac.get('Data_Fim','')} · "
                        f"🎫 Crachá: {ac.get('Cracha_Numero','—')}"
                        f"</small>"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<span style='color:{cor_df};"
                        f"font-weight:700;font-size:0.82rem;'>"
                        f"{ic_df} Validade: {txt_df}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"📄 {n_docs_colab} doc(s) válido(s)"
                        f"{docs_exp_html}"
                        f"</small></div></div>"
                        f"{motivo_html}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with col_ac2:
                    novo_est = st.selectbox(
                        "Estado",
                        ["Activo","Pendente","Expirado",
                         "Suspenso","Revogado"],
                        key=f"est_{aid}",
                        label_visibility="collapsed"
                    )
                    if st.button(
                        "✅",
                        key=f"upd_ac_{aid}",
                        use_container_width=True,
                        help="Actualizar estado"
                    ):
                        acessos_db.loc[
                            acessos_db['ID']==aid,'Estado'
                        ] = novo_est
                        save_db(acessos_db,"acessos_obras.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="ATUALIZAR_ACESSO",
                            tabela="acessos_obras.csv",
                            registro_id=aid,
                            detalhes=(
                                f"{ac.get('Colaborador','')} | "
                                f"{ac.get('Obra','')} | "
                                f"{novo_est}"
                            ),
                            ip=""
                        )
                        criar_notificacao(
                            destinatario=ac.get('Colaborador',''),
                            titulo=f"🔐 Acesso {novo_est}",
                            mensagem=(
                                f"O teu acesso à obra "
                                f"{ac.get('Obra','')} "
                                f"foi actualizado: {novo_est}."
                            ),
                            tipo="info",
                            acao_url="/"
                        )
                        inv("acessos_obras.csv"); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — CONCEDER ACESSO
    # ════════════════════════════════════════════════════════════════
    with t_novo:
        st.markdown("#### ➕ Conceder Acesso a Obra")

        col_nf, col_ni = st.columns([1, 1])

        with col_nf:
            with st.form("form_novo_acesso"):
                na_colab  = st.selectbox(
                    "Colaborador *",
                    users_list if users_list else ["—"],
                    key="na_colab"
                )
                na_obra   = st.selectbox(
                    "Obra *",
                    obras_list if obras_list else ["—"],
                    key="na_obra"
                )
                na_nivel  = st.selectbox(
                    "Nível de Acesso *",
                    ["Área Geral","Área Restrita",
                     "Supervisão","Acesso Total"],
                    key="na_nivel"
                )
                col_nd1, col_nd2 = st.columns(2)
                with col_nd1:
                    na_ini = st.date_input(
                        "Data Início",
                        value=hoje, key="na_ini"
                    )
                with col_nd2:
                    na_fim = st.date_input(
                        "Data Fim (validade)",
                        value=hoje + timedelta(days=365),
                        key="na_fim"
                    )
                na_cracha = st.text_input(
                    "Nº Crachá",
                    key="na_cracha",
                    placeholder="Ex: CPS-2025-001"
                )
                na_cracha_emitido = st.checkbox(
                    "✅ Crachá já emitido pelo cliente?",
                    key="na_cracha_emitido"
                )
                na_notas  = st.text_area("Notas", key="na_notas")

                if st.form_submit_button(
                    "🔐 Conceder Acesso",
                    use_container_width=True,
                    type="primary"
                ):
                    if na_colab == "—" or na_obra == "—":
                        st.error("❌ Colaborador e obra obrigatórios.")
                    else:
                        # Verificar se já existe
                        ja_existe = False
                        if not acessos_db.empty:
                            ex = acessos_db[
                                (acessos_db['Colaborador']==na_colab) &
                                (acessos_db['Obra']==na_obra) &
                                (acessos_db['Estado']=='Activo')
                            ]
                            ja_existe = not ex.empty

                        if ja_existe:
                            st.warning(
                                f"⚠️ {na_colab} já tem acesso activo "
                                f"a {na_obra}."
                            )
                        else:
                            novo_ac = pd.DataFrame([{
                                "ID":           str(uuid.uuid4())[:8].upper(),
                                "Obra":         na_obra,
                                "Colaborador":  na_colab,
                                "Nivel_Acesso": na_nivel,
                                "Data_Inicio":  na_ini.strftime("%d/%m/%Y"),
                                "Data_Fim":     na_fim.strftime("%d/%m/%Y"),
                                "Estado":       "Activo",
                                "Motivo_Suspensao":"",
                                "Cracha_Numero":na_cracha.strip(),
                                "Cracha_Emitido":"Sim" if na_cracha_emitido else "Não",
                                "Notas":        na_notas.strip(),
                                "Criado_Por":   user_nome,
                                "Criado_Em":    hoje.strftime("%d/%m/%Y")
                            }])
                            upd = pd.concat(
                                [acessos_db, novo_ac],
                                ignore_index=True
                            ) if not acessos_db.empty else novo_ac
                            save_db(upd,"acessos_obras.csv")
                            log_audit(
                                usuario=user_nome,
                                acao="CONCEDER_ACESSO_OBRA",
                                tabela="acessos_obras.csv",
                                registro_id=novo_ac['ID'].iloc[0],
                                detalhes=(
                                    f"{na_colab} | {na_obra} | "
                                    f"{na_nivel} | "
                                    f"até {na_fim.strftime('%d/%m/%Y')}"
                                ),
                                ip=""
                            )
                            criar_notificacao(
                                destinatario=na_colab,
                                titulo="✅ Acesso à Obra Concedido",
                                mensagem=(
                                    f"Tens acesso autorizado à obra "
                                    f"{na_obra} até "
                                    f"{na_fim.strftime('%d/%m/%Y')}. "
                                    f"Nível: {na_nivel}."
                                ),
                                tipo="success",
                                acao_url="/"
                            )
                            inv("acessos_obras.csv")
                            st.success(
                                f"✅ Acesso concedido a {na_colab} "
                                f"para {na_obra}!"
                            )
                            st.rerun()

        with col_ni:
            # Preview dos requisitos da obra selecionada
            st.markdown("##### 📋 Requisitos da Obra")
            obra_preview = st.session_state.get(
                "na_obra", obras_list[0] if obras_list else ""
            )

            req_obra = pd.DataFrame()
            if not req_db.empty and 'Obra' in req_db.columns:
                req_obra = req_db[req_db['Obra']==obra_preview]

            if not req_obra.empty:
                req_row  = req_obra.iloc[0]
                docs_req = str(req_row.get(
                    'Documentos_Obrigatorios',''
                )).split('|')
                nivel_seg = req_row.get('Nivel_Seguranca','')
                instrucoes= req_row.get('Instrucoes','')

                cor_ns = {
                    'Baixo':  '#10B981',
                    'Médio':  '#F59E0B',
                    'Alto':   '#EF4444',
                    'Crítico':'#DC2626'
                }.get(nivel_seg,'#6B7280')

                st.markdown(
                    f"<div style='background:{cor_ns}18;"
                    f"border:1px solid {cor_ns};"
                    f"border-radius:8px;padding:10px;"
                    f"margin-bottom:8px;'>"
                    f"<b style='color:{cor_ns};'>"
                    f"Nível de Segurança: {nivel_seg}</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                st.markdown(
                    "<p style='color:#94A3B8;font-size:0.8rem;"
                    "font-weight:700;text-transform:uppercase;"
                    "margin:8px 0 4px;'>Documentos obrigatórios:</p>",
                    unsafe_allow_html=True
                )
                for doc_r in docs_req:
                    if doc_r.strip():
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:6px;padding:6px 10px;"
                            f"margin-bottom:3px;'>"
                            f"<small style='color:#94A3B8;'>"
                            f"📄 {doc_r.strip()}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                if instrucoes:
                    st.markdown(
                        f"<div style='background:rgba(59,130,246,0.1);"
                        f"border-radius:8px;padding:10px;"
                        f"margin-top:8px;'>"
                        f"<small style='color:#93C5FD;'>"
                        f"ℹ️ {instrucoes}</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.info(
                    "📋 Sem requisitos definidos para esta obra. "
                    "Configura no tab ⚙️ Requisitos."
                )

            # Verificação de documentos do colaborador
            colab_check = st.session_state.get(
                "na_colab", users_list[0] if users_list else ""
            )
            if colab_check and obra_preview and not docs_db.empty:
                st.markdown("##### ✅ Documentos do Colaborador")
                dc = docs_db[
                    (docs_db['Colaborador']==colab_check) &
                    (docs_db['Obra']==obra_preview)
                ]
                if dc.empty:
                    st.warning(
                        "⚠️ Sem documentos registados para "
                        "este colaborador nesta obra."
                    )
                else:
                    for _, d in dc.iterrows():
                        dias_d = _dias_para(d.get('Validade',''))
                        cor_d, ic_d, txt_d = _cor_dias(dias_d)
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:6px;padding:6px 10px;"
                            f"margin-bottom:3px;display:flex;"
                            f"justify-content:space-between;'>"
                            f"<small style='color:#94A3B8;'>"
                            f"{d.get('Tipo_Doc','')}</small>"
                            f"<small style='color:{cor_d};'>"
                            f"{ic_d} {txt_d}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

    # ════════════════════════════════════════════════════════════════
    # TAB — DOCUMENTOS
    # ════════════════════════════════════════════════════════════════
    with t_docs:
        st.markdown("#### 📋 Gestão de Documentos de Acesso")

        col_df, col_dl = st.columns([1, 2])

        with col_df:
            st.markdown("##### ➕ Registar Documento")
            with st.form("form_doc_acesso"):
                da_colab  = st.selectbox(
                    "Colaborador *",
                    users_list if users_list else ["—"],
                    key="da_colab"
                )
                da_obra   = st.selectbox(
                    "Obra",
                    ["Todas as obras"] + obras_list,
                    key="da_obra"
                )
                da_tipo   = st.selectbox(
                    "Tipo de Documento *",
                    TODOS_DOCS + ["Outro"],
                    key="da_tipo"
                )
                da_num    = st.text_input(
                    "Nº / Referência",
                    key="da_num",
                    placeholder="Ex: EXP-2025-001"
                )
                col_dd1, col_dd2 = st.columns(2)
                with col_dd1:
                    da_emis = st.date_input(
                        "Data Emissão",
                        value=hoje, key="da_emis"
                    )
                with col_dd2:
                    da_val  = st.date_input(
                        "Validade *",
                        value=hoje + timedelta(days=365),
                        key="da_val"
                    )
                da_ficheiro = st.file_uploader(
                    "Anexar documento (opcional)",
                    type=["pdf","jpg","jpeg","png"],
                    key="da_fich"
                )
                da_notas  = st.text_area("Notas", key="da_notas")

                if st.form_submit_button(
                    "💾 Registar Documento",
                    use_container_width=True,
                    type="primary"
                ):
                    if da_colab == "—":
                        st.error("❌ Colaborador obrigatório.")
                    else:
                        fich_b64 = ""
                        if da_ficheiro:
                            fich_b64 = base64.b64encode(
                                da_ficheiro.read()
                            ).decode()

                        obra_doc = da_obra if da_obra != "Todas as obras" \
                                   else "Geral"
                        novo_d = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Colaborador":  da_colab,
                            "Obra":         obra_doc,
                            "Tipo_Doc":     da_tipo,
                            "Numero_Doc":   da_num.strip(),
                            "Emissao":      da_emis.strftime("%d/%m/%Y"),
                            "Validade":     da_val.strftime("%d/%m/%Y"),
                            "Verificado_Por":user_nome,
                            "Verificado_Em":hoje.strftime("%d/%m/%Y"),
                            "Estado_Doc":   "Válido",
                            "Ficheiro_b64": fich_b64,
                            "Notas":        da_notas.strip()
                        }])
                        upd_d = pd.concat(
                            [docs_db, novo_d], ignore_index=True
                        ) if not docs_db.empty else novo_d
                        save_db(upd_d,"acessos_documentos.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="REGISTAR_DOC_ACESSO",
                            tabela="acessos_documentos.csv",
                            registro_id=novo_d['ID'].iloc[0],
                            detalhes=(
                                f"{da_colab} | {da_tipo} | "
                                f"até {da_val.strftime('%d/%m/%Y')}"
                            ),
                            ip=""
                        )
                        inv("acessos_documentos.csv")
                        st.success(
                            f"✅ {da_tipo} registado para {da_colab}!"
                        )
                        st.rerun()

        with col_dl:
            st.markdown("##### 📋 Documentos Registados")

            if docs_db.empty:
                st.info("📋 Sem documentos registados.")
            else:
                docs_db['Dias_N'] = docs_db['Validade'].apply(_dias_para)

                # Filtros
                col_df1, col_df2 = st.columns(2)
                with col_df1:
                    colab_df = st.selectbox(
                        "Colaborador",
                        ["Todos"] + users_list,
                        key="doc_colab_filt"
                    )
                with col_df2:
                    estado_df = st.selectbox(
                        "Estado",
                        ["Todos","✅ Válidos",
                         "⚠️ Expiram 30d","🔴 Expirados"],
                        key="doc_est_filt"
                    )

                df_d = docs_db.copy()
                if colab_df != "Todos":
                    df_d = df_d[df_d['Colaborador']==colab_df]
                if estado_df == "✅ Válidos":
                    df_d = df_d[df_d['Dias_N'] > 30]
                elif estado_df == "⚠️ Expiram 30d":
                    df_d = df_d[
                        (df_d['Dias_N'] >= 0) & (df_d['Dias_N'] <= 30)
                    ]
                elif estado_df == "🔴 Expirados":
                    df_d = df_d[df_d['Dias_N'] < 0]

                df_d = df_d.sort_values('Dias_N', ascending=True)

                for _, doc in df_d.iterrows():
                    did    = doc.get('ID','')
                    dias_d = int(doc.get('Dias_N',999))
                    cor_d, ic_d, txt_d = _cor_dias(dias_d)

                    col_di, col_da = st.columns([5,1])
                    with col_di:
                        st.markdown(
                            f"<div class='doc-item' "
                            f"style='border-left:3px solid {cor_d};'>"
                            f"<div>"
                            f"<b style='color:#F1F5F9;"
                            f"font-size:0.85rem;'>"
                            f"{doc.get('Tipo_Doc','')}</b><br>"
                            f"<small style='color:#64748B;'>"
                            f"👤 {doc.get('Colaborador','')} · "
                            f"🏗️ {doc.get('Obra','')} · "
                            f"Nº {doc.get('Numero_Doc','—')} · "
                            f"Emissão: {doc.get('Emissao','')} · "
                            f"Validade: {doc.get('Validade','')}"
                            f"</small>"
                            f"</div>"
                            f"<span style='color:{cor_d};"
                            f"font-weight:700;font-size:0.85rem;'>"
                            f"{ic_d} {txt_d}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with col_da:
                        # Download ficheiro se existir
                        fich_b = doc.get('Ficheiro_b64','')
                        if fich_b and len(str(fich_b)) > 50:
                            try:
                                ext = "pdf"
                                st.download_button(
                                    "📎",
                                    data=base64.b64decode(fich_b),
                                    file_name=(
                                        f"{doc.get('Tipo_Doc','doc')}_"
                                        f"{doc.get('Colaborador','').replace(' ','_')}"
                                        f".{ext}"
                                    ),
                                    mime="application/pdf",
                                    key=f"dl_doc_{did}",
                                    use_container_width=True,
                                    help="Descarregar documento"
                                )
                            except:
                                pass

                # Exportar lista completa
                st.markdown("---")
                cols_exp = [c for c in [
                    'Colaborador','Obra','Tipo_Doc','Numero_Doc',
                    'Emissao','Validade','Estado_Doc','Verificado_Por'
                ] if c in docs_db.columns]
                csv_docs = docs_db[cols_exp].to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    "📥 Exportar Documentos",
                    data=csv_docs.encode('utf-8-sig'),
                    file_name="documentos_acesso_obras.csv",
                    mime="text/csv",
                    key="dl_docs_exp"
                )

    # ════════════════════════════════════════════════════════════════
    # TAB — POR OBRA
    # ════════════════════════════════════════════════════════════════
    with t_obra:
        st.markdown("#### 🏗️ Acessos por Obra")

        obra_sel = st.selectbox(
            "Seleccionar Obra",
            obras_list if obras_list else ["—"],
            key="obra_sel_tab"
        )

        if obra_sel and obra_sel != "—":
            acessos_obra = acessos_db[
                acessos_db['Obra'] == obra_sel
            ] if not acessos_db.empty else pd.DataFrame()

            # KPIs da obra
            n_act_o = len(acessos_obra[acessos_obra['Estado']=='Activo']) \
                      if not acessos_obra.empty else 0
            n_tot_o = len(acessos_obra)

            c1,c2,c3 = st.columns(3)
            with c1: st.metric("👷 Total",          n_tot_o)
            with c2: st.metric("✅ Activos",         n_act_o)
            with c3:
                # Docs a expirar nos próximos 30d nesta obra
                n_da = 0
                if not docs_db.empty and 'Obra' in docs_db.columns:
                    docs_obra = docs_db[docs_db['Obra']==obra_sel].copy()
                    if not docs_obra.empty and 'Dias_N' in docs_obra.columns:
                        n_da = len(docs_obra[
                            docs_obra['Dias_N'].between(0,30)
                        ])
                st.metric("⚠️ Docs Expiram 30d", n_da)

            if acessos_obra.empty:
                st.info(
                    f"📋 Sem colaboradores com acesso a {obra_sel}."
                )
            else:
                st.markdown(f"#### 👷 Colaboradores em {obra_sel}")

                for _, ac in acessos_obra.sort_values(
                    'Estado'
                ).iterrows():
                    estado = ac.get('Estado','')
                    cor_e, ic_e = _estado_acesso_cor(estado)
                    dias_fim    = _dias_para(ac.get('Data_Fim',''))
                    cor_df2, ic_df2, txt_df2 = _cor_dias(dias_fim)

                    # Documentos deste colaborador nesta obra
                    docs_colab = pd.DataFrame()
                    if not docs_db.empty:
                        docs_colab = docs_db[
                            (docs_db['Colaborador']==ac.get('Colaborador','')) &
                            (docs_db['Obra'].isin(
                                [obra_sel,'Geral']
                            ))
                        ]
                        if not docs_colab.empty and \
                           'Dias_N' not in docs_colab.columns:
                            docs_colab['Dias_N'] = docs_colab[
                                'Validade'
                            ].apply(_dias_para)

                    # Documentos obrigatórios da obra
                    docs_obrig = []
                    if not req_db.empty and 'Obra' in req_db.columns:
                        rq = req_db[req_db['Obra']==obra_sel]
                        if not rq.empty:
                            docs_obrig = [
                                d.strip() for d in
                                str(rq.iloc[0].get(
                                    'Documentos_Obrigatorios',''
                                )).split('|')
                                if d.strip()
                            ]

                    # Calcular documentos em falta
                    docs_tem = set(
                        docs_colab['Tipo_Doc'].tolist()
                    ) if not docs_colab.empty else set()
                    docs_falta = [
                        d for d in docs_obrig if d not in docs_tem
                    ]
                    docs_expirados_c = []
                    if not docs_colab.empty and 'Dias_N' in docs_colab.columns:
                        docs_expirados_c = docs_colab[
                            docs_colab['Dias_N'] < 0
                        ]['Tipo_Doc'].tolist()

                    completude = round(
                        (len(docs_obrig) - len(docs_falta)) /
                        len(docs_obrig) * 100
                    ) if docs_obrig else 100
                    cor_comp = ("#10B981" if completude >= 80
                                else "#F59E0B" if completude >= 50
                                else "#EF4444")

                    with st.expander(
                        f"{ic_e} {ac.get('Colaborador','')} "
                        f"— {ac.get('Nivel_Acesso','')} "
                        f"| Docs: {completude}%",
                        expanded=(
                            len(docs_falta) > 0 or
                            len(docs_expirados_c) > 0
                        )
                    ):
                        col_ca1, col_ca2 = st.columns([3,1])
                        with col_ca1:
                            cracha_estado = (
                                'Emitido'
                                if ac.get('Cracha_Emitido') == 'Sim'
                                else 'Por emitir'
                            )
                            st.markdown(
                                f"<div style='background:#1E293B;"
                                f"border-radius:8px;padding:12px;'>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Estado:</b> "
                                f"<span style='color:{cor_e};'>"
                                f"{estado}</span></p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Validade acesso:</b> "
                                f"{ac.get('Data_Inicio','')} → "
                                f"{ac.get('Data_Fim','')} "
                                f"<span style='color:{cor_df2};'>"
                                f"({txt_df2})</span></p>"
                                f"<p style='color:#F1F5F9;margin:2px 0;'>"
                                f"<b>Crachá:</b> "
                                f"{ac.get('Cracha_Numero','—')} "
                                f"({cracha_estado})"
                                f"</p>"
                                f"</div>",
                                unsafe_allow_html=True
                            )

                            # Documentos OK
                            if not docs_colab.empty:
                                st.markdown(
                                    "<p style='color:#10B981;"
                                    "font-size:0.78rem;"
                                    "font-weight:700;"
                                    "text-transform:uppercase;"
                                    "margin:8px 0 4px;'>"
                                    "✅ Documentos válidos:</p>",
                                    unsafe_allow_html=True
                                )
                                docs_validos = docs_colab[
                                    docs_colab['Dias_N'] >= 0
                                ]
                                for _, dv in docs_validos.iterrows():
                                    dias_dv = int(dv.get('Dias_N',999))
                                    cor_dv, _, txt_dv = _cor_dias(dias_dv)
                                    st.markdown(
                                        f"<div style='background:#0F172A;"
                                        f"border-radius:5px;padding:4px 8px;"
                                        f"margin-bottom:2px;display:flex;"
                                        f"justify-content:space-between;'>"
                                        f"<small style='color:#94A3B8;'>"
                                        f"✓ {dv.get('Tipo_Doc','')}</small>"
                                        f"<small style='color:{cor_dv};'>"
                                        f"{txt_dv}</small>"
                                        f"</div>",
                                        unsafe_allow_html=True
                                    )

                            # Documentos em falta
                            if docs_falta:
                                st.markdown(
                                    f"<p style='color:#EF4444;"
                                    f"font-size:0.78rem;"
                                    f"font-weight:700;"
                                    f"text-transform:uppercase;"
                                    f"margin:8px 0 4px;'>"
                                    f"❌ Documentos em falta "
                                    f"({len(docs_falta)}):</p>",
                                    unsafe_allow_html=True
                                )
                                for df_m in docs_falta:
                                    st.markdown(
                                        f"<div style='background:"
                                        f"rgba(239,68,68,0.1);"
                                        f"border-radius:5px;"
                                        f"padding:4px 8px;"
                                        f"margin-bottom:2px;'>"
                                        f"<small style='color:#EF4444;'>"
                                        f"❌ {df_m}</small>"
                                        f"</div>",
                                        unsafe_allow_html=True
                                    )

                            # Documentos expirados
                            if docs_expirados_c:
                                st.markdown(
                                    "<p style='color:#F59E0B;"
                                    "font-size:0.78rem;"
                                    "font-weight:700;"
                                    "text-transform:uppercase;"
                                    "margin:8px 0 4px;'>"
                                    "⚠️ Documentos expirados:</p>",
                                    unsafe_allow_html=True
                                )
                                for de_c in docs_expirados_c:
                                    st.markdown(
                                        f"<div style='background:"
                                        f"rgba(245,158,11,0.1);"
                                        f"border-radius:5px;"
                                        f"padding:4px 8px;"
                                        f"margin-bottom:2px;'>"
                                        f"<small style='color:#F59E0B;'>"
                                        f"⚠️ {de_c}</small>"
                                        f"</div>",
                                        unsafe_allow_html=True
                                    )

                        with col_ca2:
                            # Barra de completude
                            st.markdown(
                                f"<div style='background:{cor_comp}18;"
                                f"border:1px solid {cor_comp};"
                                f"border-radius:10px;padding:12px;"
                                f"text-align:center;'>"
                                f"<p style='color:#64748B;"
                                f"font-size:0.7rem;margin:0 0 4px;'>"
                                f"DOCUMENTAÇÃO</p>"
                                f"<b style='color:{cor_comp};"
                                f"font-size:1.6rem;'>"
                                f"{completude}%</b><br>"
                                f"<small style='color:#64748B;'>"
                                f"{len(docs_obrig)-len(docs_falta)}/"
                                f"{len(docs_obrig)} docs</small>"
                                f"</div>",
                                unsafe_allow_html=True
                            )

                            # Gerar cartão de acesso PDF
                            if completude == 100 and \
                               estado == "Activo":
                                if st.button(
                                    "🎫 Cartão PDF",
                                    key=f"cartao_{ac.get('ID','')}",
                                    use_container_width=True,
                                    type="primary"
                                ):
                                    docs_ok_list = docs_colab[
                                        docs_colab['Dias_N'] >= 0
                                    ]['Tipo_Doc'].tolist() \
                                    if not docs_colab.empty else []
                                    pdf_cartao = _gerar_pdf_cartao_acesso(
                                        colaborador=ac.get('Colaborador',''),
                                        obra=obra_sel,
                                        nivel=ac.get('Nivel_Acesso',''),
                                        validade=ac.get('Data_Fim',''),
                                        docs_ok=docs_ok_list,
                                        empresa=empresa
                                    )
                                    st.session_state[
                                        f'cartao_{ac.get("ID","")}'
                                    ] = pdf_cartao
                                    st.rerun()

                            ckey = f'cartao_{ac.get("ID","")}'
                            if st.session_state.get(ckey):
                                st.download_button(
                                    "📥 Descarregar",
                                    data=st.session_state[ckey],
                                    file_name=(
                                        f"cartao_acesso_"
                                        f"{ac.get('Colaborador','').replace(' ','_')}"
                                        f"_{obra_sel.replace(' ','_')}.pdf"
                                    ),
                                    mime="application/pdf",
                                    key=f"dl_cartao_{ac.get('ID','')}",
                                    use_container_width=True
                                )

            # Relatório da obra
            st.markdown("---")
            if st.button(
                f"📄 Relatório PDF — {obra_sel}",
                key="btn_rel_obra",
                use_container_width=True,
                type="primary"
            ):
                if not acessos_obra.empty:
                    pdf_rel = _gerar_pdf_relatorio_acessos(
                        obra_sel, acessos_obra, docs_db, empresa
                    )
                    st.download_button(
                        "📥 Descarregar Relatório",
                        data=pdf_rel,
                        file_name=(
                            f"relatorio_acessos_"
                            f"{obra_sel.replace(' ','_')}.pdf"
                        ),
                        mime="application/pdf",
                        key="dl_rel_obra"
                    )
                else:
                    st.info("📋 Sem dados para gerar relatório.")

    # ════════════════════════════════════════════════════════════════
    # TAB — REQUISITOS POR OBRA
    # ════════════════════════════════════════════════════════════════
    with t_requisitos:
        st.markdown("#### ⚙️ Requisitos de Acesso por Obra")
        st.info(
            "Define os documentos obrigatórios e o nível de segurança "
            "de cada obra. Estes requisitos são usados para validar "
            "automaticamente se um colaborador pode ter acesso."
        )

        col_rf2, col_rl2 = st.columns([1, 2])

        with col_rf2:
            st.markdown("##### ➕ Configurar Requisitos")
            with st.form("form_req_obra"):
                rq_obra   = st.selectbox(
                    "Obra *",
                    obras_list if obras_list else ["—"],
                    key="rq_obra"
                )
                rq_tipo   = st.selectbox(
                    "Tipo de Obra",
                    list(DOCS_PADRAO.keys()),
                    key="rq_tipo"
                )

                # Auto-preencher documentos pelo tipo
                docs_auto = DOCS_PADRAO.get(rq_tipo, [])

                rq_nivel  = st.selectbox(
                    "Nível de Segurança",
                    ["Baixo","Médio","Alto","Crítico"],
                    index=1, key="rq_nivel"
                )

                st.markdown(
                    "<p style='color:#94A3B8;font-size:0.8rem;"
                    "margin:8px 0 4px;'>"
                    "Documentos obrigatórios:</p>",
                    unsafe_allow_html=True
                )
                docs_sel = st.multiselect(
                    "Seleccionar documentos",
                    TODOS_DOCS,
                    default=docs_auto,
                    key="rq_docs_sel"
                )

                rq_instrucoes = st.text_area(
                    "Instruções especiais",
                    key="rq_instrucoes",
                    placeholder="Ex: Zona ATEX — formação ATEX "
                                "obrigatória antes de entrar..."
                )

                if st.form_submit_button(
                    "💾 Guardar Requisitos",
                    use_container_width=True,
                    type="primary"
                ):
                    docs_str = "|".join(docs_sel)
                    # Verificar se já existe
                    if not req_db.empty and 'Obra' in req_db.columns:
                        req_db = req_db[req_db['Obra'] != rq_obra]

                    novo_rq = pd.DataFrame([{
                        "ID":    str(uuid.uuid4())[:8].upper(),
                        "Obra":  rq_obra,
                        "Tipo_Obra": rq_tipo,
                        "Documentos_Obrigatorios": docs_str,
                        "Nivel_Seguranca": rq_nivel,
                        "Instrucoes": rq_instrucoes.strip(),
                        "Atualizado_Em": hoje.strftime("%d/%m/%Y")
                    }])
                    upd_rq = pd.concat(
                        [req_db, novo_rq], ignore_index=True
                    ) if not req_db.empty else novo_rq
                    save_db(upd_rq,"acessos_requisitos_obras.csv")
                    inv("acessos_requisitos_obras.csv")
                    st.success(
                        f"✅ Requisitos de {rq_obra} guardados! "
                        f"{len(docs_sel)} documentos obrigatórios."
                    )
                    st.rerun()

        with col_rl2:
            st.markdown("##### 📋 Requisitos Configurados")
            if req_db.empty:
                st.info("📋 Sem requisitos configurados.")
            else:
                for _, rq in req_db.iterrows():
                    nivel_rq = rq.get('Nivel_Seguranca','')
                    cor_rq   = {
                        'Baixo':  '#10B981',
                        'Médio':  '#F59E0B',
                        'Alto':   '#EF4444',
                        'Crítico':'#DC2626',
                    }.get(nivel_rq,'#6B7280')

                    docs_rq = [
                        d.strip() for d in
                        str(rq.get('Documentos_Obrigatorios','')).split('|')
                        if d.strip()
                    ]

                    with st.expander(
                        f"🏗️ {rq.get('Obra','')} "
                        f"[{nivel_rq}] — {len(docs_rq)} docs obrigatórios"
                    ):
                        # ── FIX BUG 2 ── extrair instrucoes_html antes do
                        # f-string para evitar backslash em Python < 3.12
                        instrucoes_val = rq.get('Instrucoes', '')
                        if instrucoes_val:
                            instrucoes_html = (
                                "<p style='color:#94A3B8;margin:4px 0;'>"
                                + str(instrucoes_val)
                                + "</p>"
                            )
                        else:
                            instrucoes_html = ""

                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:12px;'>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Tipo:</b> {rq.get('Tipo_Obra','')}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Nível segurança:</b> "
                            f"<span style='color:{cor_rq};'>"
                            f"{nivel_rq}</span></p>"
                            f"{instrucoes_html}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            "<p style='color:#64748B;"
                            "font-size:0.75rem;"
                            "font-weight:700;"
                            "text-transform:uppercase;"
                            "margin:8px 0 4px;'>"
                            "Documentos obrigatórios:</p>",
                            unsafe_allow_html=True
                        )
                        cols_docs = st.columns(2)
                        for i, doc_rq in enumerate(docs_rq):
                            with cols_docs[i%2]:
                                st.markdown(
                                    f"<div style='background:#0F172A;"
                                    f"border-radius:5px;padding:5px 8px;"
                                    f"margin-bottom:3px;'>"
                                    f"<small style='color:#94A3B8;'>"
                                    f"📄 {doc_rq}</small>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )

    # ════════════════════════════════════════════════════════════════
    # TAB — RELATÓRIOS
    # ════════════════════════════════════════════════════════════════
    with t_relatorio:
        st.markdown("#### 📄 Relatórios e Alertas")

        # Alertas automáticos
        st.markdown("##### 🔔 Alertas Activos")

        alertas = []

        # Acessos a expirar em 30 dias
        if not acessos_db.empty and 'Data_Fim' in acessos_db.columns:
            ac2 = acessos_db.copy()
            ac2['Dias_Fim'] = ac2['Data_Fim'].apply(_dias_para)
            exp_30 = ac2[
                (ac2['Dias_Fim'] >= 0) &
                (ac2['Dias_Fim'] <= 30) &
                (ac2['Estado'] == 'Activo')
            ]
            for _, a in exp_30.iterrows():
                alertas.append({
                    "tipo":  "Acesso a expirar",
                    "msg":   f"{a.get('Colaborador','')} — "
                             f"{a.get('Obra','')}",
                    "dias":  int(a.get('Dias_Fim',0)),
                    "cor":   "#F59E0B"
                })

        # Documentos a expirar
        if not docs_db.empty and 'Dias_N' in docs_db.columns:
            docs_exp_30 = docs_db[
                docs_db['Dias_N'].between(0, 30)
            ]
            for _, d in docs_exp_30.iterrows():
                alertas.append({
                    "tipo": "Documento a expirar",
                    "msg":  f"{d.get('Colaborador','')} — "
                            f"{d.get('Tipo_Doc','')}",
                    "dias": int(d.get('Dias_N',0)),
                    "cor":  "#F59E0B"
                })

            docs_expirados_all = docs_db[docs_db['Dias_N'] < 0]
            for _, d in docs_expirados_all.iterrows():
                alertas.append({
                    "tipo": "Documento EXPIRADO",
                    "msg":  f"{d.get('Colaborador','')} — "
                            f"{d.get('Tipo_Doc','')}",
                    "dias": int(d.get('Dias_N',0)),
                    "cor":  "#EF4444"
                })

        if not alertas:
            st.success("✅ Sem alertas activos. Tudo em ordem!")
        else:
            alertas.sort(key=lambda x: x['dias'])
            for alerta in alertas:
                st.markdown(
                    f"<div style='background:{alerta['cor']}12;"
                    f"border-left:4px solid {alerta['cor']};"
                    f"border-radius:8px;padding:10px 14px;"
                    f"margin-bottom:5px;'>"
                    f"<b style='color:{alerta['cor']};'>"
                    f"{alerta['tipo']}</b> — "
                    f"<span style='color:#F1F5F9;'>"
                    f"{alerta['msg']}</span>"
                    f"<span style='float:right;color:{alerta['cor']};'>"
                    f"{'EXPIRADO' if alerta['dias']<0 else str(alerta['dias'])+'d'}"
                    f"</span></div>",
                    unsafe_allow_html=True
                )

        # Exportar alertas
        if alertas:
            df_alertas = pd.DataFrame(alertas)
            csv_alertas = df_alertas.to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Exportar Alertas",
                data=csv_alertas.encode('utf-8-sig'),
                file_name=f"alertas_acessos_{hoje.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="dl_alertas"
            )

        st.markdown("---")

        # Relatório global
        st.markdown("##### 📊 Relatório Global de Acessos")
        col_rg1, col_rg2 = st.columns(2)
        with col_rg1:
            obra_rel = st.selectbox(
                "Obra para relatório",
                ["Todas"] + obras_list,
                key="obra_rel"
            )
        with col_rg2:
            st.markdown(
                "<div style='height:28px;'></div>",
                unsafe_allow_html=True
            )

        if st.button(
            "📄 Gerar Relatório Completo PDF",
            key="btn_rel_global",
            type="primary",
            use_container_width=True
        ):
            if obra_rel == "Todas":
                acessos_para_rel = acessos_db
                nome_obra_rel    = "Todas as Obras"
            else:
                acessos_para_rel = acessos_db[
                    acessos_db['Obra']==obra_rel
                ] if not acessos_db.empty else pd.DataFrame()
                nome_obra_rel = obra_rel

            if not acessos_para_rel.empty:
                pdf_global = _gerar_pdf_relatorio_acessos(
                    nome_obra_rel,
                    acessos_para_rel,
                    docs_db,
                    empresa
                )
                st.download_button(
                    "📥 Descarregar Relatório",
                    data=pdf_global,
                    file_name=(
                        f"relatorio_acessos_"
                        f"{nome_obra_rel.replace(' ','_')}_"
                        f"{hoje.strftime('%Y%m%d')}.pdf"
                    ),
                    mime="application/pdf",
                    key="dl_rel_global",
                    use_container_width=True,
                    type="primary"
                )
            else:
                st.info("📋 Sem dados para o relatório.")

        # Tabela completa exportável
        st.markdown("---")
        st.markdown("##### 📋 Tabela Completa")
        if not acessos_db.empty:
            cols_ac = [c for c in [
                'Colaborador','Obra','Nivel_Acesso','Data_Inicio',
                'Data_Fim','Estado','Cracha_Numero',
                'Cracha_Emitido','Criado_Por'
            ] if c in acessos_db.columns]
            st.dataframe(
                acessos_db[cols_ac].sort_values(
                    'Data_Fim', ascending=True
                ),
                use_container_width=True,
                hide_index=True
            )
            csv_ac = acessos_db[cols_ac].to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Exportar Todos os Acessos",
                data=csv_ac.encode('utf-8-sig'),
                file_name=(
                    f"acessos_obras_"
                    f"{hoje.strftime('%Y%m%d')}.csv"
                ),
                mime="text/csv",
                key="dl_ac_todos"
            )
        else:
            st.info("📋 Sem acessos registados.")

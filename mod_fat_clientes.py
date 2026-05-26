"""
GESTNOW v3 — mod_fat_clientes.py
Passo 2 — Clientes & Faturação
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, base64, io, json, os
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

def _proximo_numero(faturas_cli, tipo="FT"):
    """Gera próximo número sequencial de fatura."""
    ano = date.today().year
    if faturas_cli.empty or 'Numero' not in faturas_cli.columns:
        return f"{tipo} {ano}/1"
    serie = faturas_cli[
        faturas_cli['Numero'].str.startswith(f"{tipo} {ano}/", na=False)
    ]
    if serie.empty:
        return f"{tipo} {ano}/1"
    nums = []
    for n in serie['Numero']:
        try:
            nums.append(int(n.split("/")[-1]))
        except:
            pass
    return f"{tipo} {ano}/{max(nums)+1 if nums else 1}"

def _data_vencimento(data_emissao_str, dias):
    try:
        d = datetime.strptime(data_emissao_str, "%d/%m/%Y").date()
        return (d + timedelta(days=dias)).strftime("%d/%m/%Y")
    except:
        return ""

def _dias_vencimento(data_venc_str):
    try:
        d = datetime.strptime(data_venc_str, "%d/%m/%Y").date()
        return (date.today() - d).days
    except:
        return 0

# ─────────────────────────────────────────────────────────────────
# PDF FATURA LEGAL PORTUGUESA
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_fatura(fatura: dict, linhas: list,
                       empresa: dict) -> bytes:
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # Estilos
    titulo_s = ParagraphStyle(
        'titulo', parent=styles['Normal'],
        fontSize=22, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1E293B'), spaceAfter=4
    )
    sub_s = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#64748B'), spaceAfter=2
    )
    bold_s = ParagraphStyle(
        'bold', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', spaceAfter=2
    )
    normal_s = styles['Normal']
    normal_s.fontSize = 9

    # Header — empresa + número fatura
    header_data = [[
        Paragraph(f"<b>{empresa.get('nome','')}</b>", bold_s),
        Paragraph(
            f"<b style='font-size:18pt'>{fatura.get('Numero','')}</b>",
            ParagraphStyle('num', parent=styles['Normal'],
                           fontSize=18, fontName='Helvetica-Bold',
                           textColor=colors.HexColor('#3B82F6'),
                           alignment=2)
        )
    ]]
    header_t = Table(header_data, colWidths=[10*cm, 7*cm])
    header_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(header_t)

    # Dados empresa
    story.append(Paragraph(
        f"NIF: {empresa.get('nif','')} | "
        f"{empresa.get('morada','')}",
        sub_s
    ))
    story.append(Paragraph(
        f"Email: {empresa.get('email','')} | "
        f"Tel: {empresa.get('telefone','')}",
        sub_s
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    # Dados fatura + cliente
    info_data = [[
        Table([
            [Paragraph("<b>DATA DE EMISSÃO</b>", sub_s),
             Paragraph(fatura.get('Data_Emissao',''), normal_s)],
            [Paragraph("<b>DATA DE VENCIMENTO</b>", sub_s),
             Paragraph(fatura.get('Data_Vencimento',''), normal_s)],
            [Paragraph("<b>OBRA/REFERÊNCIA</b>", sub_s),
             Paragraph(fatura.get('Obra',''), normal_s)],
        ], colWidths=[4*cm, 4*cm],
           style=TableStyle([
               ('FONTSIZE', (0,0), (-1,-1), 9),
               ('BOTTOMPADDING', (0,0), (-1,-1), 4),
           ])),
        Table([
            [Paragraph("<b>CLIENTE</b>", sub_s),
             Paragraph(fatura.get('Cliente',''), bold_s)],
            [Paragraph("<b>NIF</b>", sub_s),
             Paragraph(fatura.get('NIF_Cliente',''), normal_s)],
            [Paragraph("<b>MORADA</b>", sub_s),
             Paragraph(fatura.get('Morada_Cliente',''), normal_s)],
        ], colWidths=[2.5*cm, 5.5*cm],
           style=TableStyle([
               ('FONTSIZE', (0,0), (-1,-1), 9),
               ('BOTTOMPADDING', (0,0), (-1,-1), 4),
           ])),
    ]]
    info_t = Table(info_data, colWidths=[9*cm, 9*cm])
    info_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (0,0), 0.5, colors.HexColor('#E2E8F0')),
        ('BOX', (1,0), (1,0), 0.5, colors.HexColor('#BFDBFE')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 0.4*cm))

    # Linhas da fatura
    header_linhas = [
        Paragraph("<b>Descrição</b>", sub_s),
        Paragraph("<b>Qtd</b>", sub_s),
        Paragraph("<b>Unit. €</b>", sub_s),
        Paragraph("<b>IVA %</b>", sub_s),
        Paragraph("<b>Total €</b>", sub_s),
    ]
    rows = [header_linhas]
    subtotal = 0.0
    total_iva = 0.0
    for linha in linhas:
        qtd     = float(linha.get('Quantidade', 1))
        unit    = float(linha.get('Preco_Unit', 0))
        iva_pct = float(linha.get('IVA_Pct', 23))
        sub_l   = round(qtd * unit, 2)
        iva_l   = round(sub_l * iva_pct / 100, 2)
        subtotal  += sub_l
        total_iva += iva_l
        rows.append([
            Paragraph(linha.get('Descricao',''), normal_s),
            Paragraph(f"{qtd:.2f}", normal_s),
            Paragraph(f"€{unit:.2f}", normal_s),
            Paragraph(f"{iva_pct:.0f}%", normal_s),
            Paragraph(f"€{sub_l:.2f}", normal_s),
        ])

    total_geral = subtotal + total_iva
    rows.append(["", "", "",
                 Paragraph("<b>Subtotal</b>", bold_s),
                 Paragraph(f"<b>€{subtotal:.2f}</b>", bold_s)])
    rows.append(["", "", "",
                 Paragraph("<b>IVA</b>", bold_s),
                 Paragraph(f"<b>€{total_iva:.2f}</b>", bold_s)])
    rows.append(["", "", "",
                 Paragraph("<b>TOTAL</b>",
                            ParagraphStyle('tot', parent=styles['Normal'],
                                           fontSize=12,
                                           fontName='Helvetica-Bold',
                                           textColor=colors.HexColor('#3B82F6'))),
                 Paragraph(f"<b>€{total_geral:.2f}</b>",
                            ParagraphStyle('tot2', parent=styles['Normal'],
                                           fontSize=12,
                                           fontName='Helvetica-Bold',
                                           textColor=colors.HexColor('#3B82F6')))])

    linhas_t = Table(rows, colWidths=[8*cm, 2*cm, 2.5*cm, 2*cm, 2.5*cm])
    linhas_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#1E293B')),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('GRID',          (0,0), (-1,-2), 0.3, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS',(0,1), (-1,-4),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('BACKGROUND',    (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('LINEABOVE',     (0,-3), (-1,-3), 1, colors.HexColor('#3B82F6')),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
    ]))
    story.append(linhas_t)
    story.append(Spacer(1, 0.5*cm))

    # Notas
    if fatura.get('Notas'):
        story.append(Paragraph("<b>Notas:</b>", bold_s))
        story.append(Paragraph(fatura['Notas'], normal_s))
        story.append(Spacer(1, 0.3*cm))

    # Dados bancários
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"<b>Dados para pagamento:</b> IBAN: "
        f"{empresa.get('iban','')} | BIC: "
        f"{empresa.get('bic','')}",
        sub_s
    ))
    story.append(Paragraph(
        f"Documento processado por GESTNOW v3.0 | "
        f"Emitido em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle('footer', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_funil_faturas(faturas_cli):
    """Funil de estados das faturas."""
    estados = ['Rascunho', 'Emitida', 'Enviada',
               'Em Análise', 'Paga']
    if not faturas_cli.empty and 'Estado' in faturas_cli.columns:
        valores = [
            len(faturas_cli[faturas_cli['Estado'] == e])
            for e in estados
        ]
    else:
        valores = [2, 8, 6, 4, 15]

    fig = go.Figure(go.Funnel(
        y=estados, x=valores,
        textinfo="value+percent initial",
        marker={
            'color': ['#64748B','#3B82F6','#8B5CF6',
                      '#F59E0B','#10B981'],
            'line': {'width': 1, 'color': '#0F172A'}
        },
        connector={'line': {'color': '#334155', 'width': 1}},
        textfont={'color': '#F1F5F9'}
    ))
    fig.update_layout(
        title={'text': 'Pipeline de Faturas',
               'font': {'color': '#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color': '#F1F5F9'},
        margin=dict(t=40, b=10, l=10, r=10)
    )
    return fig


def _grafico_aging_detalhado(faturas_cli):
    """Aging detalhado com linha de tendência."""
    hoje_ts = pd.Timestamp(date.today())
    clientes_aging = {}

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
            cli  = row.get('Cliente', 'Desconhecido')
            dias = (hoje_ts - row['Venc_d']).days \
                   if pd.notna(row['Venc_d']) else 0
            val  = row['Total_Num']
            if cli not in clientes_aging:
                clientes_aging[cli] = [0, 0, 0, 0]
            if dias <= 30:   clientes_aging[cli][0] += val
            elif dias <= 60: clientes_aging[cli][1] += val
            elif dias <= 90: clientes_aging[cli][2] += val
            else:            clientes_aging[cli][3] += val

    if not clientes_aging:
        clientes_aging = {
            'Cliente A': [15000, 0, 0, 0],
            'Cliente B': [8000, 5000, 0, 0],
            'Cliente C': [0, 0, 3000, 1500],
        }

    clientes = list(clientes_aging.keys())
    escaloes = ['0-30d', '31-60d', '61-90d', '+90d']
    cores    = ['#10B981', '#F59E0B', '#EF4444', '#DC2626']

    fig = go.Figure()
    for i, (esc, cor) in enumerate(zip(escaloes, cores)):
        fig.add_trace(go.Bar(
            name=esc,
            x=clientes,
            y=[clientes_aging[c][i] for c in clientes],
            marker_color=cor,
            hovertemplate='%{x}<br>' + esc + ': €%{y:,.0f}<extra></extra>'
        ))

    fig.update_layout(
        title={'text': 'Aging Detalhado por Cliente',
               'font': {'color': '#F1F5F9'}},
        barmode='stack',
        height=300,
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


def _grafico_timeline_cliente(faturas_cli, cliente):
    """Timeline de documentos de um cliente."""
    if faturas_cli.empty:
        return None
    fc = faturas_cli[
        faturas_cli.get('Cliente','') == cliente
    ].copy() if 'Cliente' in faturas_cli.columns else pd.DataFrame()

    if fc.empty:
        return None

    fc['Data_d'] = pd.to_datetime(
        fc['Data_Emissao'], dayfirst=True, errors='coerce'
    )
    fc['Total_Num'] = pd.to_numeric(
        fc.get('Total', 0), errors='coerce'
    ).fillna(0)
    fc = fc.sort_values('Data_d')

    cor_estado = {
        'Paga':       '#10B981',
        'Enviada':    '#3B82F6',
        'Emitida':    '#8B5CF6',
        'Vencida':    '#EF4444',
        'Rascunho':   '#64748B',
        'Em Análise': '#F59E0B',
    }

    fig = go.Figure()
    for _, row in fc.iterrows():
        cor = cor_estado.get(row.get('Estado',''), '#6B7280')
        fig.add_trace(go.Scatter(
            x=[row['Data_d']],
            y=[row['Total_Num']],
            mode='markers+text',
            text=[row.get('Numero','')],
            textposition='top center',
            textfont={'color': '#F1F5F9', 'size': 9},
            marker={'size': 14, 'color': cor,
                    'line': {'color': '#F1F5F9', 'width': 1}},
            name=row.get('Estado',''),
            hovertemplate=(
                f"{row.get('Numero','')}<br>"
                f"€{row['Total_Num']:,.0f}<br>"
                f"{row.get('Estado','')}<extra></extra>"
            ),
            showlegend=False
        ))

    fig.update_layout(
        title={'text': f'Timeline — {cliente}',
               'font': {'color': '#F1F5F9'}},
        height=220,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color': '#F1F5F9'},
        xaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'}},
        yaxis={'gridcolor': '#334155',
               'tickfont': {'color': '#94A3B8'},
               'tickprefix': '€'},
        margin=dict(t=40, b=20, l=10, r=10)
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# VALIDAÇÃO NIF (Portugal)
# ─────────────────────────────────────────────────────────────────

def _validar_nif(nif: str) -> tuple[bool, str]:
    """Valida NIF português."""
    nif = nif.replace(" ", "").replace("-", "")
    if not nif.isdigit() or len(nif) != 9:
        return False, "NIF deve ter 9 dígitos"
    primeiros = int(nif[0])
    if primeiros not in [1, 2, 3, 5, 6, 7, 8, 9]:
        return False, "Primeiro dígito inválido"
    total = sum(int(nif[i]) * (9 - i) for i in range(8))
    resto = total % 11
    check = 0 if resto in [0, 1] else 11 - resto
    if check == int(nif[8]):
        return True, "NIF válido ✅"
    return False, "Dígito de controlo inválido"


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_clientes(obras_db, registos_db, *_):
    """Módulo Clientes & Faturação."""

    # ── Carregar dados ────────────────────────────────────────────
    faturas_cli = _load("faturas_clientes.csv", [
        "ID","Numero","Tipo","Data_Emissao","Data_Vencimento",
        "Cliente","NIF_Cliente","Morada_Cliente","Obra",
        "Subtotal","IVA","Total","Estado","Notas",
        "PDF_b64","Enviada_Em","Paga_Em"
    ])
    clientes_db = _load("clientes_financeiro.csv", [
        "ID","Nome","NIF","Morada","Email","Telefone",
        "Condicoes_Pagamento","Limite_Credito","Contacto_Fat"
    ])
    linhas_fat  = _load("faturas_linhas.csv", [
        "ID","Fatura_ID","Descricao","Quantidade",
        "Preco_Unit","IVA_Pct","Total"
    ])

    # Empresa config
    try:
        from mod_admin_diarias import _get_config_empresa
        empresa = _get_config_empresa()
    except:
        empresa = {
            "nome":"Correia Plácido e Sousa, Lda.",
            "nif":"517182718", "iban":"", "bic":"MPIOPTPL",
            "morada":"Zona Industrial de Seia, lote 33, Seia",
            "email":"geral@cps.pt", "telefone":""
        }

    user_nome = st.session_state.get('user', 'Admin')

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .fat-card {
        background: #1E293B;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 8px;
        border-left: 4px solid #3B82F6;
        transition: transform 0.15s;
    }
    .fat-card:hover { transform: translateX(3px); }
    .estado-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_emitir, t_lista, t_clientes,
     t_aging, t_contratos, t_nc) = st.tabs([
        "➕ Emitir Fatura",
        "📋 Histórico",
        "🏢 Clientes",
        "📊 Aging",
        "📑 Contratos",
        "🔄 Notas de Crédito",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — EMITIR FATURA
    # ════════════════════════════════════════════════════════════════
    with t_emitir:
        st.markdown("### ➕ Nova Fatura")

        col_form, col_prev = st.columns([1, 1])

        with col_form:
            # Tipo de documento
            tipo_doc = st.selectbox(
                "Tipo de Documento",
                ["FT — Fatura", "FS — Fatura Simplificada",
                 "FR — Fatura-Recibo", "NC — Nota de Crédito",
                 "PF — Pró-forma"],
                key="fat_tipo"
            )
            tipo_cod = tipo_doc[:2]
            num_auto = _proximo_numero(faturas_cli, tipo_cod)
            st.markdown(
                f"<div style='background:rgba(59,130,246,0.1);"
                f"border:1px solid #3B82F6;border-radius:8px;"
                f"padding:10px;margin-bottom:12px;'>"
                f"<b style='color:#3B82F6;'>Número: {num_auto}</b>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Cliente
            st.markdown("#### 👤 Cliente")
            clientes_lista = clientes_db['Nome'].tolist() \
                             if not clientes_db.empty else []
            usar_existente = st.checkbox(
                "Usar cliente registado",
                value=bool(clientes_lista),
                key="fat_usar_existente"
            )

            if usar_existente and clientes_lista:
                cliente_sel = st.selectbox(
                    "Cliente", clientes_lista, key="fat_cli_sel"
                )
                # Preencher dados automaticamente
                cli_row = clientes_db[
                    clientes_db['Nome'] == cliente_sel
                ].iloc[0] if not clientes_db.empty else None
                nif_cli     = cli_row['NIF']     if cli_row is not None else ""
                morada_cli  = cli_row['Morada']  if cli_row is not None else ""
                dias_pag    = int(cli_row.get('Condicoes_Pagamento', 30)
                                  ) if cli_row is not None else 30
            else:
                cliente_sel = st.text_input(
                    "Nome do Cliente *", key="fat_cli_nome"
                )
                c_n1, c_n2 = st.columns(2)
                with c_n1:
                    nif_cli = st.text_input(
                        "NIF *", key="fat_nif",
                        placeholder="123456789"
                    )
                    if nif_cli:
                        valido, msg = _validar_nif(nif_cli)
                        if valido:
                            st.success(msg)
                        else:
                            st.error(msg)
                with c_n2:
                    dias_pag = st.selectbox(
                        "Condições Pagamento",
                        [30, 45, 60, 90],
                        key="fat_dias_pag"
                    )
                morada_cli = st.text_input(
                    "Morada", key="fat_morada"
                )

            # Datas
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                data_em = st.date_input(
                    "Data de Emissão",
                    value=date.today(),
                    key="fat_data_em"
                )
            with col_d2:
                data_venc_auto = data_em + timedelta(days=dias_pag)
                data_venc = st.date_input(
                    f"Data de Vencimento ({dias_pag} dias)",
                    value=data_venc_auto,
                    key="fat_data_venc"
                )

            # Obra
            obras_lista = obras_db[
                obras_db['Ativa'] == 'Ativa'
            ]['Obra'].tolist() if not obras_db.empty else [""]
            obra_fat = st.selectbox(
                "Obra/Referência", [""] + obras_lista,
                key="fat_obra_sel"
            )

            st.markdown("---")
            st.markdown("#### 📋 Linhas da Fatura")

            # Linhas dinâmicas
            if 'fat_linhas' not in st.session_state:
                st.session_state['fat_linhas'] = [
                    {"Descricao": "", "Quantidade": 1.0,
                     "Preco_Unit": 0.0, "IVA_Pct": 23.0}
                ]

            linhas_atuais = st.session_state['fat_linhas']
            subtotal_total = 0.0
            iva_total      = 0.0

            for i, linha in enumerate(linhas_atuais):
                st.markdown(
                    f"<p style='color:#64748B;font-size:0.75rem;"
                    f"margin:4px 0;'>Linha {i+1}</p>",
                    unsafe_allow_html=True
                )
                col_d, col_q, col_p, col_i = st.columns([4,1,1,1])
                with col_d:
                    desc = st.text_input(
                        "Descrição",
                        value=linha['Descricao'],
                        key=f"fl_desc_{i}",
                        label_visibility="collapsed",
                        placeholder="Ex: Mão de obra especializada"
                    )
                with col_q:
                    qtd = st.number_input(
                        "Qtd", min_value=0.0,
                        value=float(linha['Quantidade']),
                        step=0.5, key=f"fl_qtd_{i}",
                        label_visibility="collapsed"
                    )
                with col_p:
                    preco = st.number_input(
                        "€/unit", min_value=0.0,
                        value=float(linha['Preco_Unit']),
                        step=0.01, key=f"fl_preco_{i}",
                        label_visibility="collapsed"
                    )
                with col_i:
                    iva_sel = st.selectbox(
                        "IVA",
                        [0, 6, 13, 23],
                        index=[0,6,13,23].index(
                            int(linha['IVA_Pct'])
                        ) if int(linha['IVA_Pct']) in [0,6,13,23] else 3,
                        key=f"fl_iva_{i}",
                        label_visibility="collapsed"
                    )

                sub_l   = round(qtd * preco, 2)
                iva_l   = round(sub_l * iva_sel / 100, 2)
                subtotal_total += sub_l
                iva_total      += iva_l

                st.markdown(
                    f"<p style='text-align:right;color:#3B82F6;"
                    f"font-size:0.8rem;margin:0 0 6px;'>"
                    f"= €{sub_l:.2f} + IVA €{iva_l:.2f}"
                    f"</p>",
                    unsafe_allow_html=True
                )

                # Atualizar linha
                st.session_state['fat_linhas'][i] = {
                    "Descricao":  desc,
                    "Quantidade": qtd,
                    "Preco_Unit": preco,
                    "IVA_Pct":    iva_sel
                }

            col_add, col_rem = st.columns(2)
            with col_add:
                if st.button("➕ Linha", key="fat_add_linha",
                              use_container_width=True):
                    st.session_state['fat_linhas'].append(
                        {"Descricao":"","Quantidade":1.0,
                         "Preco_Unit":0.0,"IVA_Pct":23.0}
                    )
                    st.rerun()
            with col_rem:
                if len(linhas_atuais) > 1:
                    if st.button("➖ Remover", key="fat_rem_linha",
                                  use_container_width=True):
                        st.session_state['fat_linhas'].pop()
                        st.rerun()

            # Totais
            total_geral = subtotal_total + iva_total
            st.markdown(
                f"<div style='background:#1E293B;border-radius:10px;"
                f"padding:14px;margin:12px 0;'>"
                f"<div style='display:flex;justify-content:space-between;'>"
                f"<span style='color:#94A3B8;'>Subtotal</span>"
                f"<span style='color:#F1F5F9;"
                f"font-weight:700;'>€{subtotal_total:.2f}</span>"
                f"</div>"
                f"<div style='display:flex;justify-content:space-between;"
                f"margin-top:4px;'>"
                f"<span style='color:#94A3B8;'>IVA</span>"
                f"<span style='color:#F1F5F9;"
                f"font-weight:700;'>€{iva_total:.2f}</span>"
                f"</div>"
                f"<div style='display:flex;justify-content:space-between;"
                f"margin-top:8px;border-top:1px solid #334155;"
                f"padding-top:8px;'>"
                f"<span style='color:#3B82F6;font-size:1.1rem;"
                f"font-weight:900;'>TOTAL</span>"
                f"<span style='color:#3B82F6;font-size:1.2rem;"
                f"font-weight:900;'>€{total_geral:.2f}</span>"
                f"</div></div>",
                unsafe_allow_html=True
            )

            notas = st.text_area(
                "Notas / Observações",
                key="fat_notas",
                placeholder="Ex: Referente a obra Sines, semana 18-22 março"
            )

            # Botões ação
            col_em, col_pf = st.columns(2)
            with col_em:
                emitir = st.button(
                    "🧾 Emitir Fatura",
                    type="primary",
                    use_container_width=True,
                    key="btn_emitir_fat"
                )
            with col_pf:
                proforma = st.button(
                    "📄 Gerar Pró-forma",
                    use_container_width=True,
                    key="btn_proforma"
                )

            if emitir or proforma:
                if not cliente_sel or not str(cliente_sel).strip():
                    st.error("❌ Cliente obrigatório.")
                elif total_geral <= 0:
                    st.error("❌ Fatura não pode ter total €0.")
                else:
                    tipo_final = "PF" if proforma else tipo_cod
                    num_final  = _proximo_numero(
                        faturas_cli, tipo_final
                    )
                    estado_final = "Rascunho" if proforma else "Emitida"
                    data_em_str   = data_em.strftime("%d/%m/%Y")
                    data_venc_str = data_venc.strftime("%d/%m/%Y")

                    # Gerar PDF
                    fatura_dict = {
                        "Numero":          num_final,
                        "Data_Emissao":    data_em_str,
                        "Data_Vencimento": data_venc_str,
                        "Cliente":         cliente_sel,
                        "NIF_Cliente":     nif_cli,
                        "Morada_Cliente":  morada_cli,
                        "Obra":            obra_fat,
                        "Notas":           notas,
                    }
                    with st.spinner("A gerar fatura..."):
                        pdf_bytes = _gerar_pdf_fatura(
                            fatura_dict,
                            st.session_state['fat_linhas'],
                            empresa
                        )
                    pdf_b64 = base64.b64encode(pdf_bytes).decode()

                    # Guardar ID das linhas
                    fat_id = str(uuid.uuid4())[:8].upper()

                    # Guardar linhas
                    novas_linhas = []
                    for idx_l, linha in enumerate(
                        st.session_state['fat_linhas']
                    ):
                        qtd_l  = float(linha['Quantidade'])
                        pr_l   = float(linha['Preco_Unit'])
                        iva_l2 = float(linha['IVA_Pct'])
                        sub_l2 = round(qtd_l * pr_l, 2)
                        novas_linhas.append({
                            "ID":         str(uuid.uuid4())[:8].upper(),
                            "Fatura_ID":  fat_id,
                            "Descricao":  linha['Descricao'],
                            "Quantidade": qtd_l,
                            "Preco_Unit": pr_l,
                            "IVA_Pct":    iva_l2,
                            "Total":      sub_l2
                        })

                    df_novas_l = pd.DataFrame(novas_linhas)
                    updated_l  = pd.concat(
                        [linhas_fat, df_novas_l], ignore_index=True
                    ) if not linhas_fat.empty else df_novas_l
                    save_db(updated_l, "faturas_linhas.csv")

                    # Guardar fatura
                    nova_fat = pd.DataFrame([{
                        "ID":              fat_id,
                        "Numero":          num_final,
                        "Tipo":            tipo_final,
                        "Data_Emissao":    data_em_str,
                        "Data_Vencimento": data_venc_str,
                        "Cliente":         cliente_sel,
                        "NIF_Cliente":     nif_cli,
                        "Morada_Cliente":  morada_cli,
                        "Obra":            obra_fat,
                        "Subtotal":        subtotal_total,
                        "IVA":             iva_total,
                        "Total":           total_geral,
                        "Estado":          estado_final,
                        "Notas":           notas,
                        "PDF_b64":         pdf_b64,
                        "Enviada_Em":      "",
                        "Paga_Em":         ""
                    }])
                    updated_f = pd.concat(
                        [faturas_cli, nova_fat], ignore_index=True
                    ) if not faturas_cli.empty else nova_fat
                    save_db(updated_f, "faturas_clientes.csv")

                    log_audit(
                        usuario=user_nome,
                        acao="EMITIR_FATURA",
                        tabela="faturas_clientes.csv",
                        registro_id=fat_id,
                        detalhes=(
                            f"{num_final} | {cliente_sel} | "
                            f"€{total_geral:.2f}"
                        ),
                        ip=""
                    )
                    inv("faturas_clientes.csv")

                    st.success(
                        f"✅ {num_final} emitida! "
                        f"Total: €{total_geral:.2f}"
                    )

                    # Guardar PDF no session_state para download
                    st.session_state['fat_pdf_bytes'] = pdf_bytes
                    st.session_state['fat_pdf_nome']  = (
                        f"{num_final.replace(' ','_').replace('/','_')}.pdf"
                    )
                    # Limpar linhas
                    st.session_state['fat_linhas'] = [
                        {"Descricao":"","Quantidade":1.0,
                         "Preco_Unit":0.0,"IVA_Pct":23.0}
                    ]
                    st.rerun()

            # Botão download depois de emitir
            if st.session_state.get('fat_pdf_bytes'):
                st.download_button(
                    "📥 Descarregar Fatura PDF",
                    data=st.session_state['fat_pdf_bytes'],
                    file_name=st.session_state.get(
                        'fat_pdf_nome', 'fatura.pdf'
                    ),
                    mime="application/pdf",
                    key="dl_fat_pdf",
                    use_container_width=True,
                    type="primary"
                )

        with col_prev:
            st.markdown("#### 👀 Pré-visualização")
            st.markdown(
                "<div style='background:#F8FAFC;border:1px solid #E2E8F0;"
                "border-radius:12px;padding:20px;color:#1E293B;'>"
                f"<div style='border-bottom:3px solid #3B82F6;"
                f"padding-bottom:12px;margin-bottom:12px;'>"
                f"<h3 style='color:#1E293B;margin:0;'>"
                f"{empresa.get('nome','')}</h3>"
                f"<small style='color:#64748B;'>"
                f"NIF: {empresa.get('nif','')} | "
                f"{empresa.get('morada','')}</small>"
                f"</div>",
                unsafe_allow_html=True
            )
            # Número e datas
            num_prev = _proximo_numero(faturas_cli, tipo_cod)
            st.markdown(
                f"<div style='display:grid;"
                f"grid-template-columns:1fr 1fr;"
                f"gap:8px;margin-bottom:12px;'>"
                f"<div style='background:#EFF6FF;"
                f"border-radius:8px;padding:10px;'>"
                f"<small style='color:#3B82F6;font-weight:700;'>"
                f"NÚMERO</small><br>"
                f"<b style='color:#1E293B;'>{num_prev}</b>"
                f"</div>"
                f"<div style='background:#F0FDF4;"
                f"border-radius:8px;padding:10px;'>"
                f"<small style='color:#10B981;font-weight:700;'>"
                f"VENCIMENTO</small><br>"
                f"<b style='color:#1E293B;'>"
                f"{date.today() + timedelta(days=30)}"
                f"</b></div></div>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Linhas em preview
            st.markdown("**Linhas:**")
            total_prev = 0.0
            for linha in st.session_state.get('fat_linhas', []):
                qtd_p  = float(linha.get('Quantidade', 0))
                prec_p = float(linha.get('Preco_Unit', 0))
                sub_p  = qtd_p * prec_p
                total_prev += sub_p
                if linha.get('Descricao'):
                    st.markdown(
                        f"<div style='display:flex;"
                        f"justify-content:space-between;"
                        f"padding:4px 0;border-bottom:"
                        f"1px solid rgba(0,0,0,0.05);'>"
                        f"<small style='color:#374151;'>"
                        f"{linha['Descricao'][:40]}</small>"
                        f"<small style='color:#1E293B;"
                        f"font-weight:700;'>"
                        f"€{sub_p:.2f}</small></div>",
                        unsafe_allow_html=True
                    )

            st.markdown(
                f"<div style='text-align:right;margin-top:12px;"
                f"font-size:1.2rem;font-weight:900;color:#3B82F6;'>"
                f"TOTAL: €{total_prev:.2f}</div>",
                unsafe_allow_html=True
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — HISTÓRICO
    # ════════════════════════════════════════════════════════════════
    with t_lista:
        st.markdown("### 📋 Histórico de Faturas")

        if faturas_cli.empty:
            st.info("📋 Ainda não há faturas emitidas.")
        else:
            # Filtros
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                cli_filt = st.selectbox(
                    "Cliente",
                    ["Todos"] + faturas_cli['Cliente'].unique().tolist(),
                    key="hist_cli_filt"
                )
            with col_f2:
                est_filt = st.selectbox(
                    "Estado",
                    ["Todos","Rascunho","Emitida","Enviada",
                     "Em Análise","Paga","Vencida"],
                    key="hist_est_filt"
                )
            with col_f3:
                obra_filt = st.selectbox(
                    "Obra",
                    ["Todas"] + faturas_cli['Obra'].unique().tolist()
                    if 'Obra' in faturas_cli.columns else ["Todas"],
                    key="hist_obra_filt"
                )

            df_show = faturas_cli.copy()
            if cli_filt  != "Todos": df_show = df_show[df_show['Cliente'] == cli_filt]
            if est_filt  != "Todos": df_show = df_show[df_show['Estado']  == est_filt]
            if obra_filt != "Todas": df_show = df_show[df_show['Obra']    == obra_filt]

            # KPIs filtrados
            total_filt = pd.to_numeric(
                df_show['Total'], errors='coerce'
            ).fillna(0).sum()
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("📋 Faturas",   len(df_show))
            with c2: st.metric("💰 Total",     f"€{total_filt:,.2f}")
            with c3:
                pagas = df_show[
                    df_show['Estado'] == 'Paga'
                ] if 'Estado' in df_show.columns else pd.DataFrame()
                st.metric(
                    "✅ Pagas",
                    f"€{pd.to_numeric(pagas['Total'], errors='coerce').fillna(0).sum():,.2f}"
                    if not pagas.empty else "€0"
                )

            # Funil
            col_fun, col_aging_g = st.columns(2)
            with col_fun:
                st.plotly_chart(_grafico_aging_detalhado(faturas_cli), key="aging_lista")
                
            with col_aging_g:
                st.plotly_chart(_grafico_aging_detalhado(faturas_cli), key="aging_tab")   
                

            st.markdown("---")

            # Lista de faturas
            cor_estado = {
                'Paga':       '#10B981',
                'Enviada':    '#3B82F6',
                'Emitida':    '#8B5CF6',
                'Vencida':    '#EF4444',
                'Rascunho':   '#64748B',
                'Em Análise': '#F59E0B',
            }

            for _, fat in df_show.sort_values(
                'Data_Emissao', ascending=False
            ).iterrows():
                fat_id = fat.get('ID','')
                total_f = float(fat.get('Total', 0) or 0)
                estado  = fat.get('Estado','')
                cor_f   = cor_estado.get(estado, '#6B7280')
                dias_v  = _dias_vencimento(
                    fat.get('Data_Vencimento','')
                )

                col_fi, col_fa, col_fb = st.columns([5, 1, 1])
                with col_fi:
                    venc_txt = ""
                    if estado not in ['Paga','Anulada','Rascunho']:
                        if dias_v > 0:
                            venc_txt = (
                                f"<span style='color:#EF4444;"
                                f"font-size:0.72rem;'>"
                                f"⚠️ Vencida há {dias_v} dias</span>"
                            )
                        elif dias_v > -7:
                            venc_txt = (
                                f"<span style='color:#F59E0B;"
                                f"font-size:0.72rem;'>"
                                f"⏰ Vence em breve</span>"
                            )

                    st.markdown(
                        f"<div class='fat-card' "
                        f"style='border-left-color:{cor_f};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;"
                        f"align-items:flex-start;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:0.9rem;'>"
                        f"{fat.get('Numero','')} — "
                        f"{fat.get('Cliente','')}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"{fat.get('Obra','')} · "
                        f"Emissão: {fat.get('Data_Emissao','')} · "
                        f"Venc.: {fat.get('Data_Vencimento','')}"
                        f"</small><br>{venc_txt}"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:1.05rem;'>"
                        f"€{total_f:,.2f}</b><br>"
                        f"<span class='estado-badge' "
                        f"style='background:{cor_f}22;"
                        f"color:{cor_f};'>{estado}</span>"
                        f"</div></div></div>",
                        unsafe_allow_html=True
                    )

                with col_fa:
                    # Alterar estado
                    novo_est = st.selectbox(
                        "Estado",
                        ["Emitida","Enviada","Em Análise",
                         "Paga","Vencida","Anulada"],
                        key=f"est_{fat_id}",
                        label_visibility="collapsed"
                    )
                    if st.button(
                        "✅", key=f"upd_est_{fat_id}",
                        use_container_width=True,
                        help="Atualizar estado"
                    ):
                        faturas_cli.loc[
                            faturas_cli['ID'] == fat_id, 'Estado'
                        ] = novo_est
                        if novo_est == 'Paga':
                            faturas_cli.loc[
                                faturas_cli['ID'] == fat_id, 'Paga_Em'
                            ] = datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(faturas_cli, "faturas_clientes.csv")
                        inv("faturas_clientes.csv")
                        st.rerun()

                with col_fb:
                    # Download PDF
                    pdf_b64_f = fat.get('PDF_b64','')
                    if pdf_b64_f:
                        try:
                            pdf_dl = base64.b64decode(pdf_b64_f)
                            num_fn = fat.get('Numero','fat').replace(
                                ' ','_'
                            ).replace('/','_')
                            st.download_button(
                                "📄",
                                data=pdf_dl,
                                file_name=f"{num_fn}.pdf",
                                mime="application/pdf",
                                key=f"dl_{fat_id}",
                                use_container_width=True,
                                help="Descarregar PDF"
                            )
                        except:
                            pass

    # ════════════════════════════════════════════════════════════════
    # TAB — CLIENTES
    # ════════════════════════════════════════════════════════════════
    with t_clientes:
        st.markdown("### 🏢 Registo de Clientes")

        col_form_c, col_lista_c = st.columns([1, 2])

        with col_form_c:
            st.markdown("#### ➕ Novo Cliente")
            with st.form("form_novo_cliente"):
                cli_nome  = st.text_input("Nome *",   key="cli_nome")
                cli_nif   = st.text_input("NIF *",    key="cli_nif",
                                           placeholder="123456789")
                if cli_nif:
                    v, m = _validar_nif(cli_nif)
                    st.markdown(
                        f"<small style='color:"
                        f"{'#10B981' if v else '#EF4444'};'>"
                        f"{m}</small>",
                        unsafe_allow_html=True
                    )
                cli_morada = st.text_input("Morada",  key="cli_morada")
                cli_email  = st.text_input("Email",   key="cli_email")
                cli_tel    = st.text_input("Telefone",key="cli_tel")
                cli_cont   = st.text_input(
                    "Contacto Faturação", key="cli_cont"
                )
                cli_dias = st.selectbox(
                    "Condições Pagamento (dias)",
                    [30, 45, 60, 90], key="cli_dias"
                )
                cli_lim = st.number_input(
                    "Limite de Crédito (€)",
                    min_value=0.0, value=50000.0,
                    step=1000.0, key="cli_lim"
                )

                if st.form_submit_button(
                    "💾 Guardar Cliente",
                    use_container_width=True, type="primary"
                ):
                    if not cli_nome.strip() or not cli_nif.strip():
                        st.error("❌ Nome e NIF obrigatórios.")
                    else:
                        novo_c = pd.DataFrame([{
                            "ID":                   str(uuid.uuid4())[:8].upper(),
                            "Nome":                 cli_nome.strip(),
                            "NIF":                  cli_nif.strip(),
                            "Morada":               cli_morada.strip(),
                            "Email":                cli_email.strip(),
                            "Telefone":             cli_tel.strip(),
                            "Contacto_Fat":         cli_cont.strip(),
                            "Condicoes_Pagamento":  cli_dias,
                            "Limite_Credito":       cli_lim,
                        }])
                        updated_c = pd.concat(
                            [clientes_db, novo_c], ignore_index=True
                        ) if not clientes_db.empty else novo_c
                        save_db(updated_c, "clientes_financeiro.csv")
                        inv("clientes_financeiro.csv")
                        st.success(
                            f"✅ Cliente {cli_nome} guardado!"
                        )
                        st.rerun()

        with col_lista_c:
            st.markdown("#### 📋 Clientes Registados")
            if clientes_db.empty:
                st.info("📋 Sem clientes registados.")
            else:
                for _, cli in clientes_db.iterrows():
                    # Volume faturado a este cliente
                    vol_cli = 0.0
                    if not faturas_cli.empty and \
                       'Cliente' in faturas_cli.columns:
                        fc_cli = faturas_cli[
                            faturas_cli['Cliente'] == cli.get('Nome','')
                        ]
                        vol_cli = pd.to_numeric(
                            fc_cli.get('Total', 0), errors='coerce'
                        ).fillna(0).sum()

                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:14px;"
                        f"margin-bottom:8px;"
                        f"border-left:3px solid #3B82F6;'>"
                        f"<b style='color:#F1F5F9;'>"
                        f"{cli.get('Nome','')}</b>"
                        f"<span style='float:right;color:#10B981;"
                        f"font-weight:700;'>"
                        f"€{vol_cli:,.2f} faturado</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"NIF: {cli.get('NIF','')} · "
                        f"{cli.get('Condicoes_Pagamento',30)} dias · "
                        f"Limite: €{float(cli.get('Limite_Credito',0)):,.0f}"
                        f"</small><br>"
                        f"<small style='color:#475569;'>"
                        f"📧 {cli.get('Email','')} · "
                        f"📞 {cli.get('Telefone','')}"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

                    # Timeline do cliente
                    fig_tl = _grafico_timeline_cliente(
                        faturas_cli, cli.get('Nome','')
                    )
                    if fig_tl:
                        with st.expander(
                            f"📈 Timeline — {cli.get('Nome','')}",
                            expanded=False
                        ):
                            st.plotly_chart(fig_tl, key=f"tl_{cli.get('Nome','')}")

    # ════════════════════════════════════════════════════════════════
    # TAB — AGING
    # ════════════════════════════════════════════════════════════════
    with t_aging:
        st.markdown("### 📊 Aging de Clientes")

        hoje_ts = pd.Timestamp(date.today())

        if faturas_cli.empty:
            st.info("📋 Sem faturas para analisar.")
        else:
            # Gráfico
            st.plotly_chart(
                _grafico_aging_detalhado(faturas_cli),
                use_container_width=True
            )

            # Tabela de aging
            st.markdown("#### 📋 Detalhe por Fatura")
            aging_rows = []

            if 'Data_Vencimento' in faturas_cli.columns:
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
                    if dias <= 0:
                        escalao = "✅ Não vencida"
                        cor_a = "#10B981"
                    elif dias <= 30:
                        escalao = "🟡 0-30 dias"
                        cor_a = "#F59E0B"
                    elif dias <= 60:
                        escalao = "🟠 31-60 dias"
                        cor_a = "#F97316"
                    elif dias <= 90:
                        escalao = "🔴 61-90 dias"
                        cor_a = "#EF4444"
                    else:
                        escalao = "🆘 +90 dias"
                        cor_a = "#DC2626"

                    aging_rows.append({
                        "Fatura":   row.get('Numero',''),
                        "Cliente":  row.get('Cliente',''),
                        "Vencimento": row.get('Data_Vencimento',''),
                        "Dias":     max(dias, 0),
                        "Valor":    f"€{row['Total_Num']:,.2f}",
                        "Escalão":  escalao,
                    })

            if aging_rows:
                df_aging = pd.DataFrame(aging_rows).sort_values(
                    'Dias', ascending=False
                )
                st.dataframe(
                    df_aging, use_container_width=True, hide_index=True
                )

                # Botão lembrete em massa
                st.markdown("---")
                vencidas_cli = df_aging[
                    df_aging['Dias'] > 0
                ]['Cliente'].unique().tolist() if not df_aging.empty else []

                if vencidas_cli:
                    cli_lem = st.selectbox(
                        "Enviar lembrete a",
                        ["Todos com faturas vencidas"] + vencidas_cli,
                        key="aging_lem_cli"
                    )
                    if st.button(
                        "📧 Enviar Lembrete de Pagamento",
                        key="btn_lem_pag",
                        type="primary",
                        use_container_width=True
                    ):
                        st.success(
                            f"✅ Lembrete enviado para: {cli_lem}"
                        )
                        st.info(
                            "ℹ️ Configura o SMTP no tab IT para "
                            "envio real de emails."
                        )

    # ════════════════════════════════════════════════════════════════
    # TAB — CONTRATOS
    # ════════════════════════════════════════════════════════════════
    with t_contratos:
        st.markdown("### 📑 Contratos & Cauções")

        contratos_db = _load("contratos_financeiro.csv", [
            "ID","Cliente","Obra","Valor_Total","Valor_Faturado",
            "Retencao_Pct","Valor_Retido","Data_Inicio","Data_Fim",
            "Data_Libertacao","Estado"
        ])

        col_c1, col_c2 = st.columns([1, 2])

        with col_c1:
            st.markdown("#### ➕ Novo Contrato")
            with st.form("form_contrato"):
                ct_cli  = st.selectbox(
                    "Cliente",
                    clientes_db['Nome'].tolist()
                    if not clientes_db.empty else [""],
                    key="ct_cli"
                )
                ct_obra = st.selectbox(
                    "Obra",
                    obras_db[obras_db['Ativa']=='Ativa']['Obra'].tolist()
                    if not obras_db.empty else [""],
                    key="ct_obra"
                )
                ct_val  = st.number_input(
                    "Valor Total Contrato (€)",
                    min_value=0.0, step=1000.0, key="ct_val"
                )
                ct_ret  = st.number_input(
                    "% Retenção de Garantia",
                    min_value=0.0, max_value=20.0,
                    value=5.0, step=0.5, key="ct_ret"
                )
                col_cd1, col_cd2 = st.columns(2)
                with col_cd1:
                    ct_ini = st.date_input(
                        "Início", value=date.today(), key="ct_ini"
                    )
                with col_cd2:
                    ct_fim = st.date_input(
                        "Fim", value=date.today() + timedelta(days=365),
                        key="ct_fim"
                    )
                ct_lib = st.date_input(
                    "Data Libertação Retenção",
                    value=date.today() + timedelta(days=395),
                    key="ct_lib"
                )

                if st.form_submit_button(
                    "💾 Guardar Contrato",
                    use_container_width=True, type="primary"
                ):
                    novo_ct = pd.DataFrame([{
                        "ID":              str(uuid.uuid4())[:8].upper(),
                        "Cliente":         ct_cli,
                        "Obra":            ct_obra,
                        "Valor_Total":     ct_val,
                        "Valor_Faturado":  0.0,
                        "Retencao_Pct":    ct_ret,
                        "Valor_Retido":    round(ct_val * ct_ret / 100, 2),
                        "Data_Inicio":     ct_ini.strftime("%d/%m/%Y"),
                        "Data_Fim":        ct_fim.strftime("%d/%m/%Y"),
                        "Data_Libertacao": ct_lib.strftime("%d/%m/%Y"),
                        "Estado":          "Ativo"
                    }])
                    upd_ct = pd.concat(
                        [contratos_db, novo_ct], ignore_index=True
                    ) if not contratos_db.empty else novo_ct
                    save_db(upd_ct, "contratos_financeiro.csv")
                    inv("contratos_financeiro.csv")
                    st.success("✅ Contrato guardado!")
                    st.rerun()

        with col_c2:
            st.markdown("#### 📋 Contratos Ativos")
            if contratos_db.empty:
                st.info("📋 Sem contratos registados.")
            else:
                hoje_ts2 = pd.Timestamp(date.today())
                for _, ct in contratos_db.iterrows():
                    val_t   = float(ct.get('Valor_Total',0) or 0)
                    val_fat = float(ct.get('Valor_Faturado',0) or 0)
                    val_ret = float(ct.get('Valor_Retido',0) or 0)
                    pct_ex  = round(val_fat/val_t*100,1) if val_t>0 else 0

                    # Alerta libertação
                    alerta_lib = ""
                    try:
                        lib_d = datetime.strptime(
                            ct.get('Data_Libertacao',''),
                            "%d/%m/%Y"
                        )
                        dias_lib = (lib_d.date() - date.today()).days
                        if 0 <= dias_lib <= 30:
                            alerta_lib = (
                                f"<span style='color:#10B981;"
                                f"font-size:0.75rem;'>"
                                f"🔓 Retenção liberta em {dias_lib} dias!"
                                f"</span>"
                            )
                        elif dias_lib < 0:
                            alerta_lib = (
                                f"<span style='color:#F59E0B;"
                                f"font-size:0.75rem;'>"
                                f"⚠️ Retenção deveria ter sido libertada"
                                f"</span>"
                            )
                    except:
                        pass

                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:14px;"
                        f"margin-bottom:8px;"
                        f"border-left:4px solid #8B5CF6;'>"
                        f"<b style='color:#F1F5F9;'>"
                        f"{ct.get('Obra','')} — {ct.get('Cliente','')}"
                        f"</b>"
                        f"<span style='float:right;color:#8B5CF6;"
                        f"font-weight:700;'>"
                        f"€{val_t:,.2f}</span><br>"
                        f"<div style='background:#0F172A;"
                        f"border-radius:4px;height:8px;"
                        f"margin:8px 0;'>"
                        f"<div style='background:#8B5CF6;"
                        f"width:{min(pct_ex,100):.0f}%;"
                        f"height:8px;border-radius:4px;'>"
                        f"</div></div>"
                        f"<small style='color:#64748B;'>"
                        f"Faturado: €{val_fat:,.2f} ({pct_ex:.1f}%) · "
                        f"Retido: €{val_ret:,.2f} · "
                        f"Libertação: {ct.get('Data_Libertacao','')}"
                        f"</small><br>{alerta_lib}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

    # ════════════════════════════════════════════════════════════════
    # TAB — NOTAS DE CRÉDITO
    # ════════════════════════════════════════════════════════════════
    with t_nc:
        st.markdown("### 🔄 Notas de Crédito")
        st.info(
            "Uma nota de crédito anula total ou parcialmente "
            "uma fatura emitida. O saldo do cliente é atualizado "
            "automaticamente."
        )

        faturas_emitidas = faturas_cli[
            faturas_cli.get('Estado','') != 'Anulada'
        ] if not faturas_cli.empty and 'Estado' in faturas_cli.columns \
          else faturas_cli

        if faturas_emitidas.empty:
            st.info("📋 Sem faturas disponíveis para nota de crédito.")
        else:
            with st.form("form_nc"):
                fat_nc = st.selectbox(
                    "Fatura a retificar *",
                    faturas_emitidas['Numero'].tolist()
                    if not faturas_emitidas.empty else [],
                    key="nc_fat"
                )

                # Mostrar valor da fatura selecionada
                if fat_nc and not faturas_emitidas.empty:
                    fat_sel = faturas_emitidas[
                        faturas_emitidas['Numero'] == fat_nc
                    ]
                    if not fat_sel.empty:
                        val_orig = float(
                            fat_sel.iloc[0].get('Total', 0) or 0
                        )
                        st.markdown(
                            f"<small style='color:#3B82F6;'>"
                            f"Valor original: €{val_orig:,.2f}</small>",
                            unsafe_allow_html=True
                        )

                nc_motivo = st.selectbox(
                    "Motivo *",
                    ["Erro na fatura","Devolução de material",
                     "Desconto comercial","Trabalho não executado",
                     "Outro"],
                    key="nc_motivo"
                )
                nc_valor = st.number_input(
                    "Valor da Nota de Crédito (€)",
                    min_value=0.0, step=100.0, key="nc_valor"
                )
                nc_desc = st.text_area(
                    "Descrição *", key="nc_desc",
                    placeholder="Descreve o motivo detalhado..."
                )

                if st.form_submit_button(
                    "🔄 Emitir Nota de Crédito",
                    use_container_width=True, type="primary"
                ):
                    if not nc_desc.strip() or nc_valor <= 0:
                        st.error("❌ Valor e descrição obrigatórios.")
                    else:
                        num_nc = _proximo_numero(faturas_cli, "NC")
                        # Criar NC como fatura com valor negativo
                        fat_orig_row = faturas_emitidas[
                            faturas_emitidas['Numero'] == fat_nc
                        ].iloc[0] if not faturas_emitidas.empty else None

                        nova_nc = pd.DataFrame([{
                            "ID":              str(uuid.uuid4())[:8].upper(),
                            "Numero":          num_nc,
                            "Tipo":            "NC",
                            "Data_Emissao":    date.today().strftime(
                                "%d/%m/%Y"
                            ),
                            "Data_Vencimento": date.today().strftime(
                                "%d/%m/%Y"
                            ),
                            "Cliente":         fat_orig_row.get(
                                'Cliente',''
                            ) if fat_orig_row is not None else '',
                            "NIF_Cliente":     fat_orig_row.get(
                                'NIF_Cliente',''
                            ) if fat_orig_row is not None else '',
                            "Morada_Cliente":  "",
                            "Obra":            fat_orig_row.get(
                                'Obra',''
                            ) if fat_orig_row is not None else '',
                            "Subtotal":        -nc_valor,
                            "IVA":             0,
                            "Total":           -nc_valor,
                            "Estado":          "Emitida",
                            "Notas":           f"NC de {fat_nc} — {nc_motivo}: {nc_desc}",
                            "PDF_b64":         "",
                            "Enviada_Em":      "",
                            "Paga_Em":         ""
                        }])
                        updated_nc = pd.concat(
                            [faturas_cli, nova_nc], ignore_index=True
                        ) if not faturas_cli.empty else nova_nc
                        save_db(updated_nc, "faturas_clientes.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="EMITIR_NOTA_CREDITO",
                            tabela="faturas_clientes.csv",
                            registro_id=num_nc,
                            detalhes=(
                                f"NC de {fat_nc} | "
                                f"€{nc_valor:.2f} | {nc_motivo}"
                            ),
                            ip=""
                        )
                        inv("faturas_clientes.csv")
                        st.success(
                            f"✅ {num_nc} emitida — "
                            f"€{nc_valor:.2f} creditados ao cliente!"
                        )
                        st.rerun()

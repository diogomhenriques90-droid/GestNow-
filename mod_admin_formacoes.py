"""
GESTNOW v3 — mod_admin_formacoes.py
Gestão de Formações dos Colaboradores
ISO 9001:2015 Cláusula 7.2 — Competência
Integrado no tab RH
"""
import streamlit as st
import pandas as pd
import uuid, io, base64
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

def _dias_para(data_str: str) -> int:
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return 9999

def _cor_validade(dias: int) -> tuple:
    if dias < 0:
        return "#EF4444", "🔴", "EXPIRADA"
    if dias <= 30:
        return "#EF4444", "🔴", f"{dias}d"
    if dias <= 60:
        return "#F59E0B", "⚠️", f"{dias}d"
    if dias <= 90:
        return "#F59E0B", "🟡", f"{dias}d"
    return "#10B981", "✅", f"{dias}d"

def _cor_rag(pct: float) -> str:
    if pct >= 80: return "#10B981"
    if pct >= 50: return "#F59E0B"
    return "#EF4444"


# ─────────────────────────────────────────────────────────────────
# CATÁLOGO DE FORMAÇÕES PADRÃO
# ─────────────────────────────────────────────────────────────────

CATALOGO_PADRAO = [
    # Segurança
    ("Formação HSE Indução Geral",        "Segurança",      365, True),
    ("Trabalho em Altura",                "Segurança",      365, True),
    ("Espaços Confinados",                "Segurança",      365, True),
    ("H2S — Gás Sulfídrico",              "Segurança",      365, True),
    ("ATEX — Atmosferas Explosivas",      "Segurança",      730, True),
    ("LOTO / LOTOTO",                     "Segurança",      365, True),
    ("Combate a Incêndios",               "Segurança",      365, True),
    ("Primeiros Socorros",                "Segurança",      730, True),
    ("Manobrador de Empilhador",          "Segurança",      365, True),
    ("Manobrador de Plataforma Elevatória","Segurança",     365, True),
    # Técnica
    ("Calibração de Instrumentos",        "Técnica",        730, False),
    ("Leitura de P&IDs",                  "Técnica",       1825, False),
    ("Normas IEC 61511 (SIS)",            "Técnica",       1825, False),
    ("Soldadura — Qualificação",          "Técnica",       1095, False),
    ("Electricidade BT/MT",               "Técnica",        730, False),
    # Qualidade
    ("ISO 9001 Sensibilização",           "Qualidade",     1825, False),
    ("Auditor Interno ISO 9001",          "Qualidade",     1095, False),
    ("Controlo de Qualidade Soldadura",   "Qualidade",      730, False),
    # Gestão
    ("Gestão de Projecto",                "Gestão",        1825, False),
    ("Liderança de Equipas",              "Gestão",        1825, False),
    ("Inglês Técnico",                    "Línguas",       9999, False),
    # Licenças
    ("Carta de Condução Cat. B",          "Licença",       3650, True),
    ("Carta de Condução Cat. C",          "Licença",       3650, True),
]

CATEGORIAS_FORM = [
    "Segurança", "Técnica", "Qualidade",
    "Gestão", "Línguas", "Licença", "Outra"
]

ENTIDADES_FORM = [
    "IEFP", "ACT", "Bureau Veritas", "SGS",
    "TÜV Rheinland", "Lloyd's Register",
    "Escola Superior Técnica", "Interna (CPS)",
    "Outra"
]


# ─────────────────────────────────────────────────────────────────
# PDF COMPROVATIVO DE FORMAÇÃO
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_comprovativo(
    colaborador: str,
    formacao: str,
    entidade: str,
    data_conclusao: str,
    data_validade: str,
    duracao_h: float,
    aprovado: str,
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

    story.append(Paragraph(
        "COMPROVATIVO DE FORMAÇÃO",
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
    story.append(Spacer(1, 0.4*cm))

    dados = [
        ["Colaborador:",     colaborador],
        ["Formação:",        formacao],
        ["Entidade:",        entidade],
        ["Data Conclusão:",  data_conclusao],
        ["Válida até:",      data_validade],
        ["Duração:",         f"{duracao_h:.0f} horas"],
        ["Resultado:",       aprovado],
        ["Emitido em:",      date.today().strftime("%d/%m/%Y")],
    ]
    dt = Table(dados, colWidths=[5*cm, 12*cm])
    dt.setStyle(TableStyle([
        ('FONTNAME',     (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0),(-1,-1), 10),
        ('GRID',         (0,0),(-1,-1), 0.3,
         colors.HexColor('#E2E8F0')),
        ('BACKGROUND',   (0,0),(0,-1),
         colors.HexColor('#F8FAFC')),
        ('TOPPADDING',   (0,0),(-1,-1), 7),
        ('BOTTOMPADDING',(0,0),(-1,-1), 7),
        ('LEFTPADDING',  (0,0),(-1,-1), 8),
    ]))
    story.append(dt)
    story.append(Spacer(1, 1*cm))

    ass_data = [
        ["Responsável de RH:",    "Colaborador:"],
        ["_____________________", "_____________________"],
        ["Data: ___/___/______",  "Data: ___/___/______"],
    ]
    at = Table(ass_data, colWidths=[8.5*cm, 8.5*cm])
    at.setStyle(TableStyle([
        ('FONTSIZE',     (0,0),(-1,-1), 9),
        ('ALIGN',        (0,0),(-1,-1), 'CENTER'),
        ('TOPPADDING',   (0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
    ]))
    story.append(at)
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E2E8F0')
    ))
    story.append(Paragraph(
        f"GESTNOW v3.0 · Gestão de Formações · "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        f"Confidencial",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey,
                       alignment=1)
    ))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _gerar_pdf_plano_anual(
    ano: int,
    plano_db: pd.DataFrame,
    form_db: pd.DataFrame,
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

    story.append(Paragraph(
        f"PLANO DE FORMAÇÃO {ano}",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=14, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'),
                       spaceAfter=4)
    ))
    story.append(Paragraph(
        f"{empresa.get('nome','')} · "
        f"ISO 9001:2015 Cláusula 7.2 · "
        f"Gerado em {datetime.now().strftime('%d/%m/%Y')}",
        ParagraphStyle('sub', parent=styles['Normal'],
                       fontSize=8,
                       textColor=colors.HexColor('#64748B'),
                       spaceAfter=4)
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    if not plano_db.empty:
        header = [[
            "Colaborador", "Formação", "Categoria",
            "Previsto", "Pago Por", "Custo Est.", "Estado"
        ]]
        rows = []
        for _, p in plano_db.sort_values(
            'Data_Prevista'
        ).iterrows():
            rows.append([
                str(p.get('Colaborador',''))[:20],
                str(p.get('Formacao',''))[:30],
                str(p.get('Categoria','')),
                str(p.get('Data_Prevista','')),
                str(p.get('Pago_Por','')),
                f"€{float(p.get('Custo_Estimado',0) or 0):.2f}",
                str(p.get('Estado','')),
            ])

        t = Table(
            header + rows,
            colWidths=[3.5*cm,4.5*cm,2.5*cm,2.2*cm,3*cm,2*cm,2.3*cm]
        )
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,0),
             colors.HexColor('#1E293B')),
            ('TEXTCOLOR',     (0,0),(-1,0), colors.white),
            ('FONTNAME',      (0,0),(-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 7.5),
            ('GRID',          (0,0),(-1,-1), 0.2,
             colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0,1),(-1,-1),
             [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING',    (0,0),(-1,-1), 4),
            ('BOTTOMPADDING', (0,0),(-1,-1), 4),
            ('LEFTPADDING',   (0,0),(-1,-1), 4),
        ]))
        story.append(t)

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

def render_formacoes(users, obras_db, *_):
    """Módulo de Gestão de Formações — ISO 9001 Cláusula 7.2."""

    # ── Carregar dados ────────────────────────────────────────────
    form_db  = _load("formacoes.csv", [
        "ID","Colaborador","Formacao","Categoria","Entidade",
        "Data_Conclusao","Data_Validade","Duracao_H","Resultado",
        "Pago_Por","Custo","Obra_Imputacao","Reembolsado",
        "Certificado_b64","Notas","Criado_Por","Criado_Em"
    ])
    plano_db = _load("formacoes_plano.csv", [
        "ID","Ano","Colaborador","Formacao","Categoria",
        "Data_Prevista","Pago_Por","Custo_Estimado","Estado",
        "Prioridade","Notas"
    ])
    cat_db   = _load("formacoes_catalogo.csv", [
        "ID","Nome","Categoria","Validade_Dias","Obrigatoria","Ativa"
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
    ano_atual  = hoje.year
    users_list = users['Nome'].tolist() if not users.empty else []
    obras_list = obras_db[
        obras_db['Ativa']=='Ativa'
    ]['Obra'].tolist() if not obras_db.empty else []

    # Catálogo de nomes de formações
    nomes_catalogo = sorted(
        cat_db['Nome'].tolist()
        if not cat_db.empty and 'Nome' in cat_db.columns
        else [c[0] for c in CATALOGO_PADRAO]
    )

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .form-card {
        background:#1E293B; border-radius:12px;
        padding:14px 16px; margin-bottom:8px;
        border-left:5px solid;
    }
    .form-badge {
        display:inline-block; padding:2px 9px;
        border-radius:20px; font-size:0.7rem; font-weight:700;
    }
    .collab-row {
        background:#0F172A; border-radius:8px;
        padding:10px 14px; margin-bottom:4px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🎓 Gestão de Formações")
    st.markdown(
        "<p style='color:#64748B;font-size:0.82rem;margin:0 0 12px;'>"
        "ISO 9001:2015 — Cláusula 7.2 Competência · "
        "Registo, validades, plano anual e custos"
        "</p>",
        unsafe_allow_html=True
    )

    # ── KPIs ──────────────────────────────────────────────────────
    # Formações com validade
    n_validas   = 0
    n_expiradas = 0
    n_alerta    = 0
    if not form_db.empty and 'Data_Validade' in form_db.columns:
        form_db['Dias_N'] = form_db['Data_Validade'].apply(_dias_para)
        n_validas   = len(form_db[form_db['Dias_N'] > 60])
        n_alerta    = len(form_db[
            form_db['Dias_N'].between(0, 60)
        ])
        n_expiradas = len(form_db[form_db['Dias_N'] < 0])

    # Reembolsos pendentes
    n_reemb = 0
    if not form_db.empty:
        n_reemb = len(form_db[
            (form_db['Pago_Por']=='Colaborador (reembolso)') &
            (form_db.get('Reembolsado','') != 'Sim')
        ])

    # Custo do ano
    custo_ano = 0.0
    if not form_db.empty and 'Criado_Em' in form_db.columns:
        fd2 = form_db.copy()
        fd2['d'] = pd.to_datetime(
            fd2['Criado_Em'], dayfirst=True, errors='coerce'
        )
        fd2['c'] = pd.to_numeric(
            fd2.get('Custo',0), errors='coerce'
        ).fillna(0)
        custo_ano = fd2[
            fd2['d'].dt.year == ano_atual
        ]['c'].sum()

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("✅ Válidas",       n_validas)
    with c2: st.metric("⚠️ Alerta 60d",   n_alerta)
    with c3: st.metric("🔴 Expiradas",    n_expiradas)
    with c4: st.metric("💰 Reembolsos",   n_reemb)
    with c5: st.metric("💶 Custo Ano",    f"€{custo_ano:,.2f}")

    # Alertas urgentes
    if (n_alerta > 0 or n_expiradas > 0) and not form_db.empty:
        urgentes = form_db[
            form_db['Dias_N'] <= 30
        ].sort_values('Dias_N')
        if not urgentes.empty:
            msg = " · ".join([
                f"{r['Colaborador']} — {r['Formacao'][:25]} "
                f"({'EXPIRADA' if r['Dias_N']<0 else str(r['Dias_N'])+'d'})"
                for _, r in urgentes.head(4).iterrows()
            ])
            st.markdown(
                f"<div style='background:rgba(239,68,68,0.1);"
                f"border:1px solid #EF4444;border-radius:8px;"
                f"padding:10px 14px;margin-bottom:12px;'>"
                f"<b style='color:#EF4444;'>🚨 Formações urgentes:</b> "
                f"<span style='color:#94A3B8;'>{msg}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────
    (t_reg, t_nova, t_colab,
     t_plano, t_custos, t_catalogo) = st.tabs([
        "📋 Formações Registadas",
        "➕ Registar Formação",
        "👤 Por Colaborador",
        "📅 Plano Anual",
        "💰 Custos & Reembolsos",
        "📚 Catálogo",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — FORMAÇÕES REGISTADAS
    # ════════════════════════════════════════════════════════════════
    with t_reg:
        st.markdown("#### 📋 Todas as Formações")

        if form_db.empty:
            st.info("📋 Sem formações registadas.")
        else:
            # Filtros
            col_f1,col_f2,col_f3,col_f4 = st.columns(4)
            with col_f1:
                colab_filt = st.selectbox(
                    "Colaborador",["Todos"]+users_list,
                    key="fr_colab_f"
                )
            with col_f2:
                cat_filt = st.selectbox(
                    "Categoria",
                    ["Todas"]+CATEGORIAS_FORM,
                    key="fr_cat_f"
                )
            with col_f3:
                est_filt = st.selectbox(
                    "Estado Validade",
                    ["Todos","✅ Válida","⚠️ Alerta","🔴 Expirada"],
                    key="fr_est_f"
                )
            with col_f4:
                pago_filt = st.selectbox(
                    "Pago por",
                    ["Todos","Empresa","Colaborador (reembolso)"],
                    key="fr_pago_f"
                )

            df_f = form_db.copy()
            if 'Dias_N' not in df_f.columns:
                df_f['Dias_N'] = df_f['Data_Validade'].apply(_dias_para)

            if colab_filt != "Todos":
                df_f = df_f[df_f['Colaborador']==colab_filt]
            if cat_filt   != "Todas":
                df_f = df_f[df_f['Categoria']==cat_filt]
            if est_filt   == "✅ Válida":
                df_f = df_f[df_f['Dias_N'] > 60]
            elif est_filt == "⚠️ Alerta":
                df_f = df_f[df_f['Dias_N'].between(0,60)]
            elif est_filt == "🔴 Expirada":
                df_f = df_f[df_f['Dias_N'] < 0]
            if pago_filt  != "Todos":
                df_f = df_f[df_f['Pago_Por']==pago_filt]

            df_f = df_f.sort_values('Dias_N', ascending=True)

            st.markdown(
                f"<p style='color:#64748B;font-size:0.82rem;'>"
                f"{len(df_f)} formação(ões)</p>",
                unsafe_allow_html=True
            )

            for _, fr in df_f.iterrows():
                fid    = fr.get('ID','')
                dias_f = int(fr.get('Dias_N',9999))
                cor_v, ic_v, txt_v = _cor_validade(dias_f)

                cat_f  = fr.get('Categoria','')
                cores_cat = {
                    'Segurança': '#EF4444',
                    'Técnica':   '#3B82F6',
                    'Qualidade': '#10B981',
                    'Gestão':    '#8B5CF6',
                    'Línguas':   '#F59E0B',
                    'Licença':   '#06B6D4',
                }
                cor_cat = cores_cat.get(cat_f,'#6B7280')

                pago   = fr.get('Pago_Por','')
                ic_pago = "🏢" if pago=='Empresa' else "👤"
                custo_f = float(fr.get('Custo',0) or 0)
                reemb_f = fr.get('Reembolsado','')

                col_fi, col_fa = st.columns([6,1])
                with col_fi:
                    st.markdown(
                        f"<div class='form-card' "
                        f"style='border-left-color:{cor_v};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;"
                        f"font-size:0.92rem;'>"
                        f"{fr.get('Formacao','')}</b>"
                        f"<span class='form-badge' "
                        f"style='background:{cor_cat}22;"
                        f"color:{cor_cat};margin-left:8px;'>"
                        f"{cat_f}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"👤 {fr.get('Colaborador','')} · "
                        f"🏫 {fr.get('Entidade','')} · "
                        f"📅 {fr.get('Data_Conclusao','')} · "
                        f"⏱️ {fr.get('Duracao_H',0)}h · "
                        f"{ic_pago} €{custo_f:.2f}"
                        f"{'  · 💰 Reemb. pendente' if pago=='Colaborador (reembolso)' and reemb_f!='Sim' else ''}"
                        f"</small>"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<span style='color:{cor_v};"
                        f"font-weight:700;'>"
                        f"{ic_v} {txt_v}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"Válida até {fr.get('Data_Validade','—')}"
                        f"</small>"
                        f"</div></div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_fa:
                    # Download certificado
                    cert_b = fr.get('Certificado_b64','')
                    if cert_b and len(str(cert_b)) > 50:
                        try:
                            st.download_button(
                                "📜",
                                data=base64.b64decode(cert_b),
                                file_name=(
                                    f"cert_"
                                    f"{fr.get('Colaborador','').replace(' ','_')}"
                                    f"_{fid}.pdf"
                                ),
                                mime="application/pdf",
                                key=f"dl_cert_{fid}",
                                use_container_width=True,
                                help="Descarregar certificado"
                            )
                        except:
                            pass

            # Exportar
            st.markdown("---")
            if not form_db.empty:
                cols_exp = [c for c in [
                    'Colaborador','Formacao','Categoria','Entidade',
                    'Data_Conclusao','Data_Validade','Duracao_H',
                    'Resultado','Pago_Por','Custo','Reembolsado'
                ] if c in form_db.columns]
                csv_f = form_db[cols_exp].to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    "📥 Exportar Formações",
                    data=csv_f.encode('utf-8-sig'),
                    file_name=(
                        f"formacoes_"
                        f"{hoje.strftime('%Y%m%d')}.csv"
                    ),
                    mime="text/csv",
                    key="dl_form_exp"
                )

    # ════════════════════════════════════════════════════════════════
    # TAB — REGISTAR FORMAÇÃO
    # ════════════════════════════════════════════════════════════════
    with t_nova:
        st.markdown("#### ➕ Registar Nova Formação")

        with st.form("form_nova_formacao"):
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                nf_colab  = st.selectbox(
                    "Colaborador *",
                    users_list if users_list else ["—"],
                    key="nf_colab"
                )
                nf_form   = st.selectbox(
                    "Formação *",
                    nomes_catalogo + ["Outra (escrever)"],
                    key="nf_form"
                )
                if nf_form == "Outra (escrever)":
                    nf_form_txt = st.text_input(
                        "Nome da formação",
                        key="nf_form_txt"
                    )
                else:
                    nf_form_txt = nf_form

                nf_cat    = st.selectbox(
                    "Categoria",
                    CATEGORIAS_FORM,
                    key="nf_cat"
                )
                nf_ent    = st.selectbox(
                    "Entidade Formadora",
                    ENTIDADES_FORM,
                    key="nf_ent"
                )
                nf_res    = st.selectbox(
                    "Resultado",
                    ["Aprovado","Reprovado","Em Curso",
                     "Concluído s/ avaliação"],
                    key="nf_res"
                )

            with col_n2:
                col_nd1, col_nd2 = st.columns(2)
                with col_nd1:
                    nf_data_c = st.date_input(
                        "Data Conclusão *",
                        value=hoje, key="nf_data_c"
                    )
                with col_nd2:
                    nf_duracao = st.number_input(
                        "Duração (h)",
                        min_value=0.0,
                        step=1.0, key="nf_duracao"
                    )

                # Auto-calcular validade pelo catálogo
                validade_auto = hoje + timedelta(days=365)
                if not cat_db.empty and 'Nome' in cat_db.columns:
                    match_cat = cat_db[
                        cat_db['Nome'] == nf_form_txt
                    ]
                    if not match_cat.empty:
                        dias_val = int(
                            match_cat.iloc[0].get('Validade_Dias',365)
                        )
                        validade_auto = nf_data_c + timedelta(days=dias_val)

                nf_validade = st.date_input(
                    "Válida até *",
                    value=validade_auto,
                    key="nf_validade"
                )
                st.markdown(
                    "<small style='color:#64748B;'>"
                    "Preenchida automaticamente pelo catálogo "
                    "— ajusta se necessário.</small>",
                    unsafe_allow_html=True
                )

                # Custos
                nf_pago   = st.selectbox(
                    "Pago por *",
                    ["Empresa","Colaborador (reembolso)"],
                    key="nf_pago"
                )
                nf_custo  = st.number_input(
                    "Custo (€)",
                    min_value=0.0, step=5.0,
                    key="nf_custo"
                )
                nf_obra   = st.selectbox(
                    "Imputar a obra",
                    ["RH / Geral"] + obras_list,
                    key="nf_obra"
                )

                nf_cert   = st.file_uploader(
                    "Anexar certificado (PDF/imagem)",
                    type=["pdf","jpg","jpeg","png"],
                    key="nf_cert"
                )

            nf_notas = st.text_area("Notas", key="nf_notas")

            if st.form_submit_button(
                "💾 Registar Formação",
                use_container_width=True,
                type="primary"
            ):
                nome_final = (
                    nf_form_txt.strip()
                    if nf_form == "Outra (escrever)"
                    else nf_form
                )
                if not nome_final or nf_colab == "—":
                    st.error("❌ Colaborador e formação obrigatórios.")
                else:
                    cert_b64 = ""
                    if nf_cert:
                        cert_b64 = base64.b64encode(
                            nf_cert.read()
                        ).decode()

                    nova_f = pd.DataFrame([{
                        "ID":           str(uuid.uuid4())[:8].upper(),
                        "Colaborador":  nf_colab,
                        "Formacao":     nome_final,
                        "Categoria":    nf_cat,
                        "Entidade":     nf_ent,
                        "Data_Conclusao":nf_data_c.strftime("%d/%m/%Y"),
                        "Data_Validade": nf_validade.strftime("%d/%m/%Y"),
                        "Duracao_H":    nf_duracao,
                        "Resultado":    nf_res,
                        "Pago_Por":     nf_pago,
                        "Custo":        nf_custo,
                        "Obra_Imputacao":nf_obra,
                        "Reembolsado":  "Não" if nf_pago==
                                        "Colaborador (reembolso)"
                                        else "N/A",
                        "Certificado_b64":cert_b64,
                        "Notas":        nf_notas.strip(),
                        "Criado_Por":   user_nome,
                        "Criado_Em":    hoje.strftime("%d/%m/%Y")
                    }])
                    upd = pd.concat(
                        [form_db, nova_f], ignore_index=True
                    ) if not form_db.empty else nova_f
                    save_db(upd,"formacoes.csv")
                    log_audit(
                        usuario=user_nome,
                        acao="REGISTAR_FORMACAO",
                        tabela="formacoes.csv",
                        registro_id=nova_f['ID'].iloc[0],
                        detalhes=(
                            f"{nf_colab} | {nome_final} | "
                            f"€{nf_custo:.2f} | {nf_pago}"
                        ),
                        ip=""
                    )
                    # Notificar colaborador
                    criar_notificacao(
                        destinatario=nf_colab,
                        titulo=f"🎓 Formação Registada — {nome_final}",
                        mensagem=(
                            f"A tua formação '{nome_final}' foi "
                            f"registada. Válida até "
                            f"{nf_validade.strftime('%d/%m/%Y')}."
                        ),
                        tipo="success",
                        acao_url="/"
                    )
                    inv("formacoes.csv")
                    st.success(
                        f"✅ Formação registada! "
                        f"{nf_colab} · {nome_final} · "
                        f"Válida até "
                        f"{nf_validade.strftime('%d/%m/%Y')}"
                    )
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — POR COLABORADOR (Matriz de Competências)
    # ════════════════════════════════════════════════════════════════
    with t_colab:
        st.markdown("#### 👤 Formações por Colaborador")
        st.markdown(
            "<small style='color:#64748B;'>"
            "Matriz de competências — ISO 9001 Cláusula 7.2. "
            "Verde = válida · Amarelo = expira 60d · "
            "Vermelho = expirada · Cinzento = não tem</small>",
            unsafe_allow_html=True
        )

        colab_sel = st.selectbox(
            "Seleccionar Colaborador",
            users_list if users_list else ["—"],
            key="colab_sel_form"
        )

        if colab_sel and colab_sel != "—":
            form_colab = form_db[
                form_db['Colaborador'] == colab_sel
            ].copy() if not form_db.empty else pd.DataFrame()

            if 'Dias_N' not in form_colab.columns and \
               not form_colab.empty:
                form_colab['Dias_N'] = form_colab[
                    'Data_Validade'
                ].apply(_dias_para)

            # KPIs do colaborador
            n_total_c  = len(form_colab) if not form_colab.empty else 0
            n_validas_c= len(form_colab[
                form_colab['Dias_N'] > 60
            ]) if not form_colab.empty else 0
            n_exp_c    = len(form_colab[
                form_colab['Dias_N'] < 0
            ]) if not form_colab.empty else 0
            h_total    = form_colab['Duracao_H'].sum() \
                         if not form_colab.empty and \
                         'Duracao_H' in form_colab.columns else 0

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("📋 Total",        n_total_c)
            with c2: st.metric("✅ Válidas",       n_validas_c)
            with c3: st.metric("🔴 Expiradas",     n_exp_c)
            with c4: st.metric("⏱️ Horas Total",  f"{h_total:.0f}h")

            if form_colab.empty:
                st.info(
                    f"📋 {colab_sel} não tem formações registadas."
                )
            else:
                # Agrupar por categoria
                for cat_c in CATEGORIAS_FORM:
                    forms_cat = form_colab[
                        form_colab['Categoria'] == cat_c
                    ]
                    if forms_cat.empty:
                        continue

                    cores_cat = {
                        'Segurança': '#EF4444',
                        'Técnica':   '#3B82F6',
                        'Qualidade': '#10B981',
                        'Gestão':    '#8B5CF6',
                        'Línguas':   '#F59E0B',
                        'Licença':   '#06B6D4',
                    }
                    cor_cat_c = cores_cat.get(cat_c,'#6B7280')

                    st.markdown(
                        f"<p style='color:{cor_cat_c};"
                        f"font-weight:700;font-size:0.82rem;"
                        f"text-transform:uppercase;"
                        f"margin:12px 0 6px;'>"
                        f"■ {cat_c}</p>",
                        unsafe_allow_html=True
                    )

                    for _, fc in forms_cat.sort_values(
                        'Dias_N'
                    ).iterrows():
                        fid_c  = fc.get('ID','')
                        dias_c = int(fc.get('Dias_N',9999))
                        cor_vc, ic_vc, txt_vc = _cor_validade(dias_c)

                        col_fc1, col_fc2, col_fc3 = st.columns([4,2,1])
                        with col_fc1:
                            st.markdown(
                                f"<div class='collab-row'>"
                                f"<b style='color:#F1F5F9;"
                                f"font-size:0.85rem;'>"
                                f"{fc.get('Formacao','')}</b><br>"
                                f"<small style='color:#64748B;'>"
                                f"🏫 {fc.get('Entidade','')} · "
                                f"📅 {fc.get('Data_Conclusao','')} · "
                                f"⏱️ {fc.get('Duracao_H',0)}h · "
                                f"{fc.get('Resultado','')}"
                                f"</small>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with col_fc2:
                            st.markdown(
                                f"<div style='background:{cor_vc}18;"
                                f"border:1px solid {cor_vc};"
                                f"border-radius:8px;padding:8px;"
                                f"text-align:center;"
                                f"margin-top:4px;'>"
                                f"<b style='color:{cor_vc};'>"
                                f"{ic_vc} {txt_vc}</b><br>"
                                f"<small style='color:#64748B;'>"
                                f"até {fc.get('Data_Validade','—')}"
                                f"</small>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with col_fc3:
                            # Gerar comprovativo PDF
                            if st.button(
                                "📄",
                                key=f"comp_{fid_c}",
                                use_container_width=True,
                                help="Gerar comprovativo"
                            ):
                                pdf_comp = _gerar_pdf_comprovativo(
                                    colaborador=colab_sel,
                                    formacao=fc.get('Formacao',''),
                                    entidade=fc.get('Entidade',''),
                                    data_conclusao=fc.get('Data_Conclusao',''),
                                    data_validade=fc.get('Data_Validade',''),
                                    duracao_h=float(fc.get('Duracao_H',0)),
                                    aprovado=fc.get('Resultado',''),
                                    empresa=empresa
                                )
                                st.session_state[f'comp_{fid_c}'] = pdf_comp
                                st.rerun()

                            if st.session_state.get(f'comp_{fid_c}'):
                                st.download_button(
                                    "📥",
                                    data=st.session_state[f'comp_{fid_c}'],
                                    file_name=(
                                        f"comprovativo_"
                                        f"{colab_sel.replace(' ','_')}"
                                        f"_{fid_c}.pdf"
                                    ),
                                    mime="application/pdf",
                                    key=f"dl_comp_{fid_c}",
                                    use_container_width=True
                                )

            # Formações obrigatórias em falta
            if not cat_db.empty and 'Obrigatoria' in cat_db.columns:
                obrig = cat_db[
                    cat_db['Obrigatoria'].astype(str)
                    .isin(['True','true','1','Sim','sim'])
                ]
                if not obrig.empty:
                    form_colab_nomes = set(
                        form_colab['Formacao'].tolist()
                    ) if not form_colab.empty else set()
                    obrig_falta = obrig[
                        ~obrig['Nome'].isin(form_colab_nomes)
                    ]
                    if not obrig_falta.empty:
                        st.markdown("---")
                        st.markdown(
                            f"<p style='color:#EF4444;"
                            f"font-weight:700;font-size:0.82rem;'>"
                            f"❌ Formações obrigatórias em falta "
                            f"({len(obrig_falta)}):</p>",
                            unsafe_allow_html=True
                        )
                        for _, of in obrig_falta.iterrows():
                            st.markdown(
                                f"<div style='background:"
                                f"rgba(239,68,68,0.08);"
                                f"border-radius:6px;"
                                f"padding:6px 10px;"
                                f"margin-bottom:3px;'>"
                                f"<small style='color:#EF4444;'>"
                                f"❌ {of.get('Nome','')} — "
                                f"{of.get('Categoria','')}</small>"
                                f"</div>",
                                unsafe_allow_html=True
                            )

    # ════════════════════════════════════════════════════════════════
    # TAB — PLANO ANUAL
    # ════════════════════════════════════════════════════════════════
    with t_plano:
        st.markdown("#### 📅 Plano Anual de Formações")
        st.info(
            "ISO 9001:2015 Cláusula 7.2 — O plano anual de "
            "formações é evidência obrigatória para certificação."
        )

        col_pf, col_pl = st.columns([1, 2])

        with col_pf:
            st.markdown("##### ➕ Adicionar ao Plano")
            with st.form("form_plano"):
                pp_ano   = st.number_input(
                    "Ano", min_value=2024,
                    value=ano_atual, key="pp_ano"
                )
                pp_colab = st.selectbox(
                    "Colaborador *",
                    users_list if users_list else ["—"],
                    key="pp_colab"
                )
                pp_form  = st.selectbox(
                    "Formação *",
                    nomes_catalogo + ["Outra"],
                    key="pp_form"
                )
                pp_cat   = st.selectbox(
                    "Categoria",
                    CATEGORIAS_FORM,
                    key="pp_cat"
                )
                pp_data  = st.date_input(
                    "Data Prevista",
                    value=hoje + timedelta(days=30),
                    key="pp_data"
                )
                pp_pago  = st.selectbox(
                    "Pago por",
                    ["Empresa","Colaborador (reembolso)"],
                    key="pp_pago"
                )
                pp_custo = st.number_input(
                    "Custo Estimado (€)",
                    min_value=0.0, step=10.0,
                    key="pp_custo"
                )
                pp_prior = st.selectbox(
                    "Prioridade",
                    ["Alta","Média","Baixa"],
                    key="pp_prior"
                )
                pp_notas = st.text_area("Notas", key="pp_notas")

                if st.form_submit_button(
                    "➕ Adicionar ao Plano",
                    use_container_width=True,
                    type="primary"
                ):
                    novo_p = pd.DataFrame([{
                        "ID":            str(uuid.uuid4())[:8].upper(),
                        "Ano":           pp_ano,
                        "Colaborador":   pp_colab,
                        "Formacao":      pp_form,
                        "Categoria":     pp_cat,
                        "Data_Prevista": pp_data.strftime("%d/%m/%Y"),
                        "Pago_Por":      pp_pago,
                        "Custo_Estimado":pp_custo,
                        "Estado":        "Planeada",
                        "Prioridade":    pp_prior,
                        "Notas":         pp_notas.strip()
                    }])
                    upd_p = pd.concat(
                        [plano_db, novo_p], ignore_index=True
                    ) if not plano_db.empty else novo_p
                    save_db(upd_p,"formacoes_plano.csv")
                    inv("formacoes_plano.csv")
                    st.success("✅ Adicionado ao plano!")
                    st.rerun()

        with col_pl:
            ano_plan = st.number_input(
                "Ano do Plano",
                min_value=2024,
                value=ano_atual,
                key="plano_ano_view"
            )

            plano_ano = plano_db[
                plano_db['Ano'].astype(str) == str(ano_plan)
            ] if not plano_db.empty else pd.DataFrame()

            if plano_ano.empty:
                st.info(
                    f"📋 Sem plano para {ano_plan}. "
                    f"Adiciona formações ao plano."
                )
            else:
                # KPIs do plano
                tot_est  = pd.to_numeric(
                    plano_ano.get('Custo_Estimado',0),
                    errors='coerce'
                ).fillna(0).sum()
                n_plan_t = len(plano_ano)
                n_conc_p = len(plano_ano[
                    plano_ano['Estado']=='Concluída'
                ])
                pct_conc = round(n_conc_p/n_plan_t*100) \
                           if n_plan_t > 0 else 0

                c1,c2,c3 = st.columns(3)
                with c1: st.metric("📋 Planeadas",    n_plan_t)
                with c2: st.metric("✅ Concluídas",
                                   f"{n_conc_p} ({pct_conc}%)")
                with c3: st.metric("💶 Custo Est.",   f"€{tot_est:,.2f}")

                # Por prioridade
                for prior_p in ["Alta","Média","Baixa"]:
                    pp_filt = plano_ano[
                        plano_ano['Prioridade']==prior_p
                    ]
                    if pp_filt.empty:
                        continue
                    cor_prior = {
                        'Alta':  '#EF4444',
                        'Média': '#F59E0B',
                        'Baixa': '#10B981'
                    }.get(prior_p,'#6B7280')

                    st.markdown(
                        f"<p style='color:{cor_prior};"
                        f"font-weight:700;"
                        f"font-size:0.82rem;"
                        f"text-transform:uppercase;"
                        f"margin:10px 0 4px;'>"
                        f"■ Prioridade {prior_p} "
                        f"({len(pp_filt)})</p>",
                        unsafe_allow_html=True
                    )

                    for _, pp in pp_filt.sort_values(
                        'Data_Prevista'
                    ).iterrows():
                        pid_p  = pp.get('ID','')
                        est_p  = pp.get('Estado','')
                        cor_ep = {
                            'Planeada':  '#F59E0B',
                            'Concluída': '#10B981',
                            'Cancelada': '#EF4444',
                            'Em Curso':  '#3B82F6'
                        }.get(est_p,'#6B7280')

                        col_pp1, col_pp2 = st.columns([5,1])
                        with col_pp1:
                            st.markdown(
                                f"<div style='background:#1E293B;"
                                f"border-radius:8px;"
                                f"padding:8px 12px;"
                                f"margin-bottom:3px;"
                                f"border-left:3px solid {cor_ep};'>"
                                f"<b style='color:#F1F5F9;"
                                f"font-size:0.83rem;'>"
                                f"{pp.get('Formacao','')}</b>"
                                f"<span style='float:right;"
                                f"color:{cor_ep};"
                                f"font-size:0.72rem;'>"
                                f"{est_p}</span><br>"
                                f"<small style='color:#64748B;'>"
                                f"👤 {pp.get('Colaborador','')} · "
                                f"📅 {pp.get('Data_Prevista','')} · "
                                f"€{float(pp.get('Custo_Estimado',0) or 0):.2f}"
                                f"</small>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with col_pp2:
                            novo_est_p = st.selectbox(
                                "Estado",
                                ['Planeada','Em Curso',
                                 'Concluída','Cancelada'],
                                key=f"pp_st_{pid_p}",
                                label_visibility="collapsed"
                            )
                            if st.button(
                                "✅",
                                key=f"upd_pp_{pid_p}",
                                use_container_width=True
                            ):
                                plano_db.loc[
                                    plano_db['ID']==pid_p,
                                    'Estado'
                                ] = novo_est_p
                                save_db(plano_db,"formacoes_plano.csv")
                                inv("formacoes_plano.csv"); st.rerun()

                # PDF do plano
                st.markdown("---")
                if st.button(
                    f"📄 Gerar Plano {ano_plan} PDF",
                    key="btn_pdf_plano",
                    use_container_width=True,
                    type="primary"
                ):
                    pdf_plano = _gerar_pdf_plano_anual(
                        ano_plan, plano_ano,
                        form_db, empresa
                    )
                    st.download_button(
                        "📥 Descarregar Plano",
                        data=pdf_plano,
                        file_name=(
                            f"plano_formacoes_{ano_plan}.pdf"
                        ),
                        mime="application/pdf",
                        key="dl_plano_pdf",
                        use_container_width=True,
                        type="primary"
                    )

    # ════════════════════════════════════════════════════════════════
    # TAB — CUSTOS & REEMBOLSOS
    # ════════════════════════════════════════════════════════════════
    with t_custos:
        st.markdown("#### 💰 Custos e Reembolsos de Formações")

        if form_db.empty:
            st.info("📋 Sem formações registadas.")
        else:
            import plotly.graph_objects as go

            form_db2 = form_db.copy()
            form_db2['Custo_N'] = pd.to_numeric(
                form_db2.get('Custo',0), errors='coerce'
            ).fillna(0)
            form_db2['d'] = pd.to_datetime(
                form_db2.get('Criado_Em',''),
                dayfirst=True, errors='coerce'
            )

            # KPIs
            tot_empresa = form_db2[
                form_db2['Pago_Por']=='Empresa'
            ]['Custo_N'].sum()
            tot_colab   = form_db2[
                form_db2['Pago_Por']=='Colaborador (reembolso)'
            ]['Custo_N'].sum()
            tot_reemb_p = form_db2[
                (form_db2['Pago_Por']=='Colaborador (reembolso)') &
                (form_db2.get('Reembolsado','') != 'Sim')
            ]['Custo_N'].sum()

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("🏢 Pago Empresa",
                               f"€{tot_empresa:,.2f}")
            with c2: st.metric("👤 Pago Colaborador",
                               f"€{tot_colab:,.2f}")
            with c3: st.metric("💰 Reembolso Pendente",
                               f"€{tot_reemb_p:,.2f}")
            with c4: st.metric("💶 Total",
                               f"€{tot_empresa+tot_colab:,.2f}")

            col_cg1, col_cg2 = st.columns(2)

            with col_cg1:
                # Por categoria
                grp_cat = form_db2.groupby('Categoria')['Custo_N'].sum() \
                          .sort_values(ascending=False)
                if not grp_cat.empty:
                    fig_cat = go.Figure(go.Pie(
                        labels=grp_cat.index.tolist(),
                        values=grp_cat.values.tolist(),
                        hole=0.4,
                        marker={'colors':[
                            '#EF4444','#3B82F6','#10B981',
                            '#8B5CF6','#F59E0B','#06B6D4','#6B7280'
                        ],'line':{'color':'#0F172A','width':2}},
                        textfont={'color':'#F1F5F9','size':10},
                        hovertemplate=(
                            '%{label}: €%{value:,.2f}'
                            '<extra></extra>'
                        )
                    ))
                    fig_cat.update_layout(
                        title={'text':'Custo por Categoria',
                               'font':{'color':'#F1F5F9'}},
                        height=240,
                        paper_bgcolor='rgba(0,0,0,0)',
                        font={'color':'#F1F5F9'},
                        legend={'font':{'color':'#94A3B8'}},
                        margin=dict(t=40,b=10,l=10,r=10)
                    )
                    st.plotly_chart(fig_cat, use_container_width=True)

            with col_cg2:
                # Top colaboradores por custo
                grp_col = form_db2.groupby(
                    'Colaborador'
                )['Custo_N'].sum().sort_values(ascending=False).head(8)
                if not grp_col.empty:
                    fig_col = go.Figure(go.Bar(
                        x=grp_col.values.tolist(),
                        y=grp_col.index.tolist(),
                        orientation='h',
                        marker_color='#3B82F6',
                        text=[f"€{v:,.0f}" for v in grp_col.values],
                        textposition='outside',
                        textfont={'color':'#F1F5F9','size':9}
                    ))
                    fig_col.update_layout(
                        title={'text':'Custo por Colaborador',
                               'font':{'color':'#F1F5F9'}},
                        height=240,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(30,41,59,0.5)',
                        font={'color':'#F1F5F9'},
                        xaxis={'gridcolor':'#334155',
                               'tickfont':{'color':'#94A3B8'},
                               'tickprefix':'€'},
                        yaxis={'gridcolor':'#334155',
                               'tickfont':{'color':'#94A3B8'}},
                        margin=dict(t=40,b=20,l=10,r=60),
                        showlegend=False
                    )
                    st.plotly_chart(fig_col, use_container_width=True)

            # Reembolsos pendentes
            st.markdown("---")
            st.markdown("##### 💰 Reembolsos Pendentes")

            reemb_pend = form_db2[
                (form_db2['Pago_Por']=='Colaborador (reembolso)') &
                (form_db2.get('Reembolsado','') != 'Sim')
            ]

            if reemb_pend.empty:
                st.success("✅ Sem reembolsos pendentes!")
            else:
                for colab_r, grp_r in reemb_pend.groupby('Colaborador'):
                    tot_c = grp_r['Custo_N'].sum()
                    with st.expander(
                        f"👤 {colab_r} — €{tot_c:.2f} "
                        f"({len(grp_r)} formação(ões))",
                        expanded=True
                    ):
                        for _, fr in grp_r.iterrows():
                            st.markdown(
                                f"<div style='background:#1E293B;"
                                f"border-radius:8px;padding:10px;"
                                f"margin-bottom:4px;display:flex;"
                                f"justify-content:space-between;'>"
                                f"<div>"
                                f"<small style='color:#F1F5F9;'>"
                                f"🎓 {fr.get('Formacao','')}</small><br>"
                                f"<small style='color:#64748B;'>"
                                f"📅 {fr.get('Data_Conclusao','')} · "
                                f"🏫 {fr.get('Entidade','')}"
                                f"</small></div>"
                                f"<b style='color:#F97316;'>"
                                f"€{float(fr.get('Custo_N',0)):,.2f}"
                                f"</b></div>",
                                unsafe_allow_html=True
                            )

                        col_rp1, col_rp2 = st.columns(2)
                        with col_rp1:
                            st.markdown(
                                f"<div style='background:"
                                f"rgba(249,115,22,0.1);"
                                f"border-radius:8px;padding:10px;"
                                f"text-align:center;'>"
                                f"<b style='color:#F97316;'>"
                                f"Total: €{tot_c:.2f}</b>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with col_rp2:
                            if st.button(
                                "✅ Marcar como reembolsado",
                                key=f"reemb_form_{colab_r}",
                                use_container_width=True,
                                type="primary"
                            ):
                                ids_r = grp_r['ID'].tolist()
                                for rid in ids_r:
                                    form_db.loc[
                                        form_db['ID']==rid,
                                        'Reembolsado'
                                    ] = 'Sim'
                                save_db(form_db,"formacoes.csv")
                                criar_notificacao(
                                    destinatario=colab_r,
                                    titulo="💰 Reembolso de Formações Processado",
                                    mensagem=(
                                        f"O teu reembolso de "
                                        f"formações (€{tot_c:.2f}) "
                                        f"foi processado."
                                    ),
                                    tipo="success",
                                    acao_url="/"
                                )
                                inv("formacoes.csv"); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB — CATÁLOGO
    # ════════════════════════════════════════════════════════════════
    with t_catalogo:
        st.markdown("#### 📚 Catálogo de Formações")
        st.info(
            "Define as formações disponíveis, as validades e "
            "quais são obrigatórias para todos os colaboradores. "
            "Estas definições alimentam automaticamente o registo "
            "de formações e os alertas."
        )

        col_cf, col_cl = st.columns([1, 2])

        with col_cf:
            st.markdown("##### ➕ Adicionar ao Catálogo")

            # Inicializar catálogo com padrão se vazio
            if cat_db.empty:
                if st.button(
                    "🚀 Inicializar com Catálogo Padrão",
                    key="btn_init_catalogo",
                    use_container_width=True,
                    type="primary"
                ):
                    rows_cat = []
                    for nome_c, cat_c, val_c, obrig_c in CATALOGO_PADRAO:
                        rows_cat.append({
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Nome":         nome_c,
                            "Categoria":    cat_c,
                            "Validade_Dias":val_c,
                            "Obrigatoria":  str(obrig_c),
                            "Ativa":        "True"
                        })
                    save_db(
                        pd.DataFrame(rows_cat),
                        "formacoes_catalogo.csv"
                    )
                    inv("formacoes_catalogo.csv")
                    st.success(
                        f"✅ Catálogo inicializado com "
                        f"{len(rows_cat)} formações!"
                    )
                    st.rerun()

            with st.form("form_cat"):
                c_nome  = st.text_input(
                    "Nome da Formação *", key="c_nome"
                )
                c_cat   = st.selectbox(
                    "Categoria", CATEGORIAS_FORM, key="c_cat"
                )
                c_val   = st.number_input(
                    "Validade (dias)",
                    min_value=0, value=365,
                    key="c_val",
                    help="0 = sem validade"
                )
                c_obrig = st.checkbox(
                    "✅ Obrigatória para todos",
                    key="c_obrig"
                )

                if st.form_submit_button(
                    "➕ Adicionar",
                    use_container_width=True,
                    type="primary"
                ):
                    if not c_nome.strip():
                        st.error("❌ Nome obrigatório.")
                    else:
                        novo_c = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Nome":         c_nome.strip(),
                            "Categoria":    c_cat,
                            "Validade_Dias":c_val,
                            "Obrigatoria":  str(c_obrig),
                            "Ativa":        "True"
                        }])
                        upd_c = pd.concat(
                            [cat_db, novo_c], ignore_index=True
                        ) if not cat_db.empty else novo_c
                        save_db(upd_c,"formacoes_catalogo.csv")
                        inv("formacoes_catalogo.csv")
                        st.success(f"✅ {c_nome} adicionado!")
                        st.rerun()

        with col_cl:
            st.markdown("##### 📋 Catálogo Actual")

            if cat_db.empty:
                st.info(
                    "📋 Catálogo vazio. Inicializa com o botão "
                    "ao lado ou adiciona formações manualmente."
                )
            else:
                # Filtro categoria
                cat_filt_c = st.selectbox(
                    "Categoria",
                    ["Todas"]+CATEGORIAS_FORM,
                    key="cat_cat_filt"
                )
                df_cat = cat_db.copy()
                if cat_filt_c != "Todas":
                    df_cat = df_cat[df_cat['Categoria']==cat_filt_c]

                for cat_grupo in CATEGORIAS_FORM:
                    grupo = df_cat[df_cat['Categoria']==cat_grupo]
                    if grupo.empty:
                        continue

                    cores_cat2 = {
                        'Segurança': '#EF4444',
                        'Técnica':   '#3B82F6',
                        'Qualidade': '#10B981',
                        'Gestão':    '#8B5CF6',
                        'Línguas':   '#F59E0B',
                        'Licença':   '#06B6D4',
                    }
                    cor_cg = cores_cat2.get(cat_grupo,'#6B7280')

                    st.markdown(
                        f"<p style='color:{cor_cg};"
                        f"font-weight:700;font-size:0.8rem;"
                        f"text-transform:uppercase;"
                        f"margin:10px 0 4px;'>"
                        f"■ {cat_grupo} ({len(grupo)})</p>",
                        unsafe_allow_html=True
                    )

                    for _, cit in grupo.iterrows():
                        val_d = int(cit.get('Validade_Dias',365))
                        obrig = str(cit.get('Obrigatoria','')).lower() \
                                in ['true','1','sim']
                        val_txt = (
                            f"{val_d//365} ano(s)"
                            if val_d >= 365
                            else f"{val_d} dias"
                            if val_d > 0
                            else "Sem validade"
                        )
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:6px;padding:7px 12px;"
                            f"margin-bottom:3px;display:flex;"
                            f"justify-content:space-between;"
                            f"align-items:center;'>"
                            f"<div>"
                            f"<small style='color:#F1F5F9;'>"
                            f"{cit.get('Nome','')}</small>"
                            f"{'<span style=color:#EF4444;font-size:0.65rem;margin-left:6px;>OBRIGATÓRIA</span>' if obrig else ''}"
                            f"</div>"
                            f"<small style='color:#64748B;'>"
                            f"⏱️ {val_txt}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                # Exportar catálogo
                csv_cat = cat_db.to_csv(
                    index=False, encoding='utf-8-sig'
                )
                st.download_button(
                    "📥 Exportar Catálogo",
                    data=csv_cat.encode('utf-8-sig'),
                    file_name="catalogo_formacoes.csv",
                    mime="text/csv",
                    key="dl_cat"
                )

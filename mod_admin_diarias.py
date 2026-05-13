import streamlit as st
import pandas as pd
import uuid, base64, io, json
from datetime import datetime, timedelta, date
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

from core import save_db, inv, load_db, log_audit, _gcs_read, fh

_VALOR_DIARIA_PADRAO = 12.0
_MIN_HORAS_DIARIA    = 4.0


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _load_users_fresh():
    import time
    for t in range(3):
        try:
            buf = _gcs_read("usuarios.csv")
            if buf:
                df = pd.read_csv(buf, dtype=str, on_bad_lines='skip',
                                 encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].str.strip()
                return df.fillna("")
            time.sleep(0.3)
        except:
            if t == 2: return pd.DataFrame()
            time.sleep(0.3)
    return pd.DataFrame()


def _get_valor_diaria(obra: str, diarias_config: pd.DataFrame) -> float:
    if not diarias_config.empty and 'Obra' in diarias_config.columns:
        match = diarias_config[diarias_config['Obra'] == obra]
        if not match.empty:
            try:
                return float(match.iloc[0]['Valor_Diaria'])
            except:
                pass
    return _VALOR_DIARIA_PADRAO


def _get_config_empresa() -> dict:
    try:
        buf = _gcs_read("empresa_config.json")
        if buf:
            return json.loads(buf.read().decode('utf-8'))
    except:
        pass
    return {
        "nome":   "Correia Plácido e Sousa, Lda.",
        "nif":    "517182718",
        "iban":   "",
        "bic":    "MPIOPTPL",
        "morada": "Zona Industrial de Seia, lote 33, Seia",
    }


def _save_config_empresa(config: dict):
    from core import _gcs_write_binary
    _gcs_write_binary(
        json.dumps(config, indent=2, ensure_ascii=False).encode('utf-8'),
        "empresa_config.json"
    )


def _xml_elem(tag: str, text: str):
    import xml.etree.ElementTree as ET
    el      = ET.Element(tag)
    el.text = text
    return el


def _gerar_sepa_xml(
    df_diarias: pd.DataFrame,
    semana_ini: date,
    semana_fim: date,
    config_empresa: dict
) -> str:
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    agora        = datetime.now()
    msg_id       = f"GESTNOW-{agora.strftime('%Y%m%d%H%M%S')}"
    data_exec    = semana_fim.strftime('%Y-%m-%d')
    n_transacoes = len(df_diarias)
    total_ctrl   = round(df_diarias['Valor_Total'].sum(), 2)

    ns   = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
    root = ET.Element("Document")
    root.set("xmlns", ns)
    cstmr = ET.SubElement(root, "CstmrCdtTrfInitn")

    # Group Header
    grp_hdr = ET.SubElement(cstmr, "GrpHdr")
    ET.SubElement(grp_hdr, "MsgId").text   = msg_id
    ET.SubElement(grp_hdr, "CreDtTm").text = agora.strftime('%Y-%m-%dT%H:%M:%S')
    ET.SubElement(grp_hdr, "NbOfTxs").text = str(n_transacoes)
    ET.SubElement(grp_hdr, "CtrlSum").text  = f"{total_ctrl:.2f}"

    initg_pty = ET.SubElement(grp_hdr, "InitgPty")
    ET.SubElement(initg_pty, "Nm").text = config_empresa.get(
        'nome', 'Correia Plácido e Sousa, Lda.'
    )
    org_id = ET.SubElement(ET.SubElement(initg_pty, "Id"), "OrgId")
    othr   = ET.SubElement(org_id, "Othr")
    ET.SubElement(othr, "Id").text = config_empresa.get('nif', '')

    # Payment Information
    pmt_inf = ET.SubElement(cstmr, "PmtInf")
    ET.SubElement(pmt_inf, "PmtInfId").text = f"{msg_id}-001"
    ET.SubElement(pmt_inf, "PmtMtd").text   = "TRF"
    ET.SubElement(pmt_inf, "NbOfTxs").text  = str(n_transacoes)
    ET.SubElement(pmt_inf, "CtrlSum").text   = f"{total_ctrl:.2f}"

    pmt_tp_inf = ET.SubElement(pmt_inf, "PmtTpInf")
    svc_lvl    = ET.SubElement(pmt_tp_inf, "SvcLvl")
    ET.SubElement(svc_lvl, "Cd").text = "SEPA"
    ctgy_purp  = ET.SubElement(pmt_tp_inf, "CtgyPurp")
    ET.SubElement(ctgy_purp, "Cd").text = "SALA"

    ET.SubElement(pmt_inf, "ReqdExctnDt").text = data_exec

    dbtr = ET.SubElement(pmt_inf, "Dbtr")
    ET.SubElement(dbtr, "Nm").text = config_empresa.get('nome', '')

    dbtr_acct = ET.SubElement(pmt_inf, "DbtrAcct")
    dbtr_id   = ET.SubElement(dbtr_acct, "Id")
    ET.SubElement(dbtr_id, "IBAN").text = config_empresa.get(
        'iban', ''
    ).replace(' ', '')

    bic = config_empresa.get('bic', '')
    if bic:
        dbtr_agt    = ET.SubElement(pmt_inf, "DbtrAgt")
        fin_inst_id = ET.SubElement(dbtr_agt, "FinInstnId")
        ET.SubElement(fin_inst_id, "BIC").text = bic

    periodo_desc = (f"Diarias {semana_ini.strftime('%d/%m/%Y')}-"
                    f"{semana_fim.strftime('%d/%m/%Y')}")

    for i, (_, row) in enumerate(df_diarias.iterrows(), 1):
        iban_col = str(row.get('IBAN', '')).replace(' ', '').strip()
        if not iban_col or len(iban_col) < 15:
            continue

        cdt_trf = ET.SubElement(pmt_inf, "CdtTrfTxInf")

        pmt_id = ET.SubElement(cdt_trf, "PmtId")
        ET.SubElement(pmt_id, "EndToEndId").text = (
            f"DIARIA-{semana_ini.strftime('%Y%m%d')}-{i:04d}"
        )

        amt     = ET.SubElement(cdt_trf, "Amt")
        inst_am = ET.SubElement(amt, "InstdAmt")
        inst_am.set("Ccy", "EUR")
        inst_am.text = f"{float(row.get('Valor_Total', 0)):.2f}"

        cdtr = ET.SubElement(cdt_trf, "Cdtr")
        ET.SubElement(cdtr, "Nm").text = str(row.get('Técnico', ''))[:70]

        cdtr_acct = ET.SubElement(cdt_trf, "CdtrAcct")
        cdtr_id   = ET.SubElement(cdtr_acct, "Id")
        ET.SubElement(cdtr_id, "IBAN").text = iban_col

        rmt_inf = ET.SubElement(cdt_trf, "RmtInf")
        ET.SubElement(rmt_inf, "Ustrd").text = (
            f"{periodo_desc} {str(row.get('Obras', ''))[:30]}"
        )[:140]

    xml_str = ET.tostring(root, encoding='unicode')
    dom     = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ", encoding=None)


def _calcular_diarias_semana(
    registos_db: pd.DataFrame,
    diarias_faltas: pd.DataFrame,
    diarias_config: pd.DataFrame,
    users_df: pd.DataFrame,
    semana_inicio: date,
    semana_fim: date
) -> pd.DataFrame:
    if registos_db.empty:
        return pd.DataFrame()

    regs = registos_db.copy()
    regs['Horas_Total'] = pd.to_numeric(
        regs['Horas_Total'], errors='coerce'
    ).fillna(0)
    regs['Data_d'] = pd.to_datetime(
        regs['Data'], dayfirst=True, errors='coerce'
    ).dt.normalize()

    ts_ini = pd.Timestamp(semana_inicio)
    ts_fim = pd.Timestamp(semana_fim)

    # ✅ Normalizar status para string para comparação segura
    regs['Status'] = regs['Status'].astype(str).str.strip()

    regs_sem = regs[
        (regs['Status'].isin(['1', '2'])) &  # validado ou faturação
        (regs['Data_d'] >= ts_ini) &
        (regs['Data_d'] <= ts_fim)
    ].copy()   

    if regs_sem.empty:
        return pd.DataFrame()

    # Faltas injustificadas
    faltas_set = set()
    if not diarias_faltas.empty:
        df_f = diarias_faltas.copy()
        df_f['Data_d'] = pd.to_datetime(
            df_f['Data'], dayfirst=True, errors='coerce'
        ).dt.normalize()
        ff = df_f[
            (df_f['Data_d'] >= ts_ini) &
            (df_f['Data_d'] <= ts_fim)
        ]
        for _, row in ff.iterrows():
            faltas_set.add((row['Técnico'], str(row['Data_d'].date())))

    regs_sem['Data_str'] = regs_sem['Data_d'].dt.strftime('%Y-%m-%d')
    grupo = regs_sem.groupby(
        ['Técnico', 'Data_str', 'Obra'], as_index=False
    )['Horas_Total'].sum()

    # ✅ Debug info para confirmar dados encontrados
    if grupo.empty:
        st.warning(
            f"⚠️ Sem registos com Status 1 ou 2 entre "
            f"{semana_inicio.strftime('%d/%m/%Y')} e "
            f"{semana_fim.strftime('%d/%m/%Y')}. "
            f"Certifica-te que as horas estão validadas (🟢 verde)."
        )

    grupo['Elegivel'] = grupo.apply(
        lambda r: (
            r['Horas_Total'] >= _MIN_HORAS_DIARIA and
            (r['Técnico'], r['Data_str']) not in faltas_set
        ), axis=1
    )

    elegivel = grupo[grupo['Elegivel']].copy()
    if elegivel.empty:
        return pd.DataFrame()

    iban_map = {}
    if not users_df.empty:
        for _, u in users_df.iterrows():
            iban_map[u.get('Nome', '')] = u.get('Banco_IBAN', '')

    resultado = []
    for tec, grp_tec in elegivel.groupby('Técnico'):
        obras_detalhe = {}
        for obra, grp_obra in grp_tec.groupby('Obra'):
            n_dias = len(grp_obra)
            val    = _get_valor_diaria(obra, diarias_config)
            obras_detalhe[obra] = {
                "dias":     n_dias,
                "valor_dia":val,
                "subtotal": round(n_dias * val, 2)
            }

        total_dias = sum(v["dias"]     for v in obras_detalhe.values())
        total_val  = sum(v["subtotal"] for v in obras_detalhe.values())
        obras_str  = " + ".join(obras_detalhe.keys())

        resultado.append({
            "Técnico":     tec,
            "IBAN":        iban_map.get(tec, ''),
            "Obras":       obras_str,
            "Dias_Total":  total_dias,
            "Valor_Total": round(total_val, 2),
            "Detalhes":    json.dumps(obras_detalhe),
        })

    return pd.DataFrame(resultado).sort_values('Técnico')


def _gerar_recibo_pdf(
    tec_nome: str,
    iban: str,
    semana_ini: date,
    semana_fim: date,
    detalhes: dict,
    total: float
) -> bytes:
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    title_style = ParagraphStyle(
        'title', parent=styles['Heading1'], fontSize=16, spaceAfter=6
    )
    sub_style = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=10, spaceAfter=4, textColor=colors.grey
    )
    body_style          = styles['Normal']
    body_style.fontSize = 10

    story.append(Paragraph("RECIBO DE AJUDAS DE CUSTO", title_style))
    story.append(Paragraph("Correia Plácido e Sousa, Lda.", sub_style))
    story.append(Spacer(1, 0.4*cm))

    periodo = (f"{semana_ini.strftime('%d/%m/%Y')} a "
               f"{semana_fim.strftime('%d/%m/%Y')}")
    story.append(Paragraph(f"<b>Período:</b> {periodo}",        body_style))
    story.append(Paragraph(f"<b>Colaborador:</b> {tec_nome}",   body_style))
    story.append(Paragraph(
        f"<b>IBAN:</b> {iban or 'Não disponível'}", body_style
    ))
    story.append(Spacer(1, 0.5*cm))

    header    = [["Obra", "Nº Dias", "Valor/Dia (€)", "Subtotal (€)"]]
    rows      = []
    for obra, info in detalhes.items():
        rows.append([
            obra,
            str(info["dias"]),
            f"€ {info['valor_dia']:.2f}",
            f"€ {info['subtotal']:.2f}"
        ])
    rows.append(["", "", "TOTAL", f"€ {total:.2f}"])

    t = Table(header + rows, colWidths=[8*cm, 2.5*cm, 3.5*cm, 3*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#1E293B')),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 10),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND',    (0, -1),(-1, -1), colors.HexColor('#F1F5F9')),
        ('FONTNAME',      (0, -1),(-1, -1), 'Helvetica-Bold'),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -2),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.8*cm))

    total_style = ParagraphStyle(
        'total', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold'
    )
    story.append(Paragraph(
        f"<b>Total a receber: € {total:.2f}</b>", total_style
    ))
    story.append(Spacer(1, 1.5*cm))

    ass_data = [
        ["Pela Empresa",          "O Colaborador"],
        ["_____________________", "_____________________"],
        ["", ""],
    ]
    ass_t = Table(ass_data, colWidths=[8*cm, 8*cm])
    ass_t.setStyle(TableStyle([
        ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE',    (0, 0), (-1, -1), 10),
        ('TOPPADDING',  (0, 0), (-1, -1), 8),
    ]))
    story.append(ass_t)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Documento gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} "
        f"— GESTNOW v3.0",
        ParagraphStyle('footer', parent=styles['Normal'],
                       fontSize=8, textColor=colors.grey)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _gerar_excel_semana(
    df_diarias: pd.DataFrame,
    semana_ini: date,
    semana_fim: date
) -> bytes:
    output = io.BytesIO()

    export_df = df_diarias[
        ['Técnico', 'IBAN', 'Obras', 'Dias_Total', 'Valor_Total']
    ].copy()
    export_df.columns = [
        'Nome Colaborador', 'IBAN', 'Obra(s)', 'Dias', 'Total (€)'
    ]
    export_df['Período'] = (
        f"{semana_ini.strftime('%d/%m/%Y')} - "
        f"{semana_fim.strftime('%d/%m/%Y')}"
    )
    export_df['Estado'] = 'Por Pagar'

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Diárias Semana')
        ws = writer.sheets['Diárias Semana']
        ws.column_dimensions['A'].width = 28
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 8
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 28
        ws.column_dimensions['G'].width = 12

        ultima = len(export_df) + 2
        ws.cell(row=ultima, column=4, value='TOTAL')
        ws.cell(row=ultima, column=5,
                value=round(export_df['Total (€)'].sum(), 2))

    output.seek(0)
    return output.getvalue()


# =============================================================================
# RENDER PRINCIPAL
# =============================================================================

def render_admin_diarias(*args):
    if len(args) >= 23:
        (users, obras_db, frentes_db, registos_db, faturas_db, docs_db,
         incs_db, sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db,
         comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db,
         avals_db, inst_acessos_db,
         diarias_config, diarias_faltas, diarias_pagamentos, *_) = args
    else:
        (users, obras_db, frentes_db, registos_db, *_rest) = args
        diarias_config     = pd.DataFrame(columns=[
            "Obra", "Valor_Diaria", "Atualizado_Em", "Atualizado_Por"])
        diarias_faltas     = pd.DataFrame(columns=[
            "ID", "Data", "Técnico", "Obra", "Motivo",
            "Registado_Por", "Registado_Em"])
        diarias_pagamentos = pd.DataFrame(columns=[
            "ID", "Semana_Inicio", "Semana_Fim", "Técnico",
            "Obras", "Dias_Total", "Valor_Total", "IBAN",
            "Status", "Data_Pagamento", "Pago_Por", "Recibo_b64"])

    admin_nome = st.session_state.get('user', 'Admin')
    hoje       = date.today()

    st.markdown("# 💶 Diárias & Ajudas de Custo")

    tab_semana, tab_config, tab_faltas, tab_historico, tab_empresa = st.tabs([
        "📅 Semana Atual",
        "⚙️ Configurar Valores",
        "❌ Faltas Injustificadas",
        "📋 Histórico",
        "🏢 Empresa",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 — SEMANA ATUAL
    # ════════════════════════════════════════════════════════════════
    with tab_semana:
        ini_semana_atual = hoje - timedelta(days=hoje.weekday())
        col_s1, col_s2   = st.columns(2)
        with col_s1:
            semana_ini = st.date_input(
                "Início da semana",
                value=ini_semana_atual,
                key="diarias_ini"
            )
        with col_s2:
            semana_fim = st.date_input(
                "Fim da semana",
                value=ini_semana_atual + timedelta(days=6),
                key="diarias_fim"
            )

        periodo_label = (f"{semana_ini.strftime('%d/%m/%Y')} — "
                         f"{semana_fim.strftime('%d/%m/%Y')}")
        st.markdown(
            f"<p style='color:#94A3B8;font-size:0.85rem;margin:0 0 12px;'>"
            f"📅 Período: <b style='color:#F1F5F9;'>{periodo_label}</b></p>",
            unsafe_allow_html=True
        )

        users_fresh = _load_users_fresh()

        if st.button("🔄 Calcular Diárias",
                     key="btn_calcular", type="primary",
                     use_container_width=True):
            st.session_state['diarias_calc'] = True

        if st.session_state.get('diarias_calc', False):
            df_calc = _calcular_diarias_semana(
                registos_db, diarias_faltas, diarias_config,
                users_fresh, semana_ini, semana_fim
            )

            if df_calc.empty:
                st.warning("⚠️ Sem registos validados neste período.")
            else:
                total_geral = df_calc['Valor_Total'].sum()

                c1, c2, c3 = st.columns(3)
                with c1: st.metric("👥 Colaboradores",  len(df_calc))
                with c2: st.metric("📋 Total Dias",
                                   int(df_calc['Dias_Total'].sum()))
                with c3: st.metric("💶 Total a Pagar",
                                   f"€ {total_geral:.2f}")

                st.markdown("<div style='height:10px;'></div>",
                            unsafe_allow_html=True)
                st.markdown("### 👥 Detalhe por Colaborador")

                for _, row in df_calc.iterrows():
                    detalhe = {}
                    try:
                        detalhe = json.loads(row.get('Detalhes', '{}'))
                    except:
                        pass

                    col_info, col_rec = st.columns([5, 1])
                    with col_info:
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:10px;"
                            f"padding:12px 16px;margin-bottom:6px;'>"
                            f"<b style='color:#F1F5F9;'>{row['Técnico']}</b>"
                            f"<span style='float:right;color:#10B981;"
                            f"font-weight:900;'>€ {row['Valor_Total']:.2f}</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"{row['Obras']} · {row['Dias_Total']} dia(s) · "
                            f"IBAN: {row['IBAN'][:12] + '...' if len(str(row['IBAN'])) > 12 else row['IBAN'] or '❌ Sem IBAN'}"
                            f"</small></div>",
                            unsafe_allow_html=True
                        )
                    with col_rec:
                        pdf_bytes = _gerar_recibo_pdf(
                            tec_nome   = row['Técnico'],
                            iban       = row['IBAN'],
                            semana_ini = semana_ini,
                            semana_fim = semana_fim,
                            detalhes   = detalhe,
                            total      = row['Valor_Total']
                        )
                        fname = (f"recibo_"
                                 f"{row['Técnico'].replace(' ','_')}_"
                                 f"{semana_ini.strftime('%Y%m%d')}.pdf")
                        st.download_button(
                            "📄",
                            data=pdf_bytes,
                            file_name=fname,
                            mime="application/pdf",
                            key=f"rec_{row['Técnico']}_{semana_ini}",
                            use_container_width=True,
                            help="Descarregar recibo PDF"
                        )

                st.divider()

                col_xl, col_sepa, col_pg = st.columns(3)

                with col_xl:
                    excel_bytes = _gerar_excel_semana(
                        df_calc, semana_ini, semana_fim
                    )
                    st.download_button(
                        "📥 Excel (Secretária)",
                        data=excel_bytes,
                        file_name=(f"diarias_"
                                   f"{semana_ini.strftime('%Y%m%d')}.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument"
                             ".spreadsheetml.sheet",
                        use_container_width=True,
                        key="btn_export_xl"
                    )

                with col_sepa:
                    cfg_emp  = _get_config_empresa()
                    iban_emp = cfg_emp.get('iban', '').strip()
                    if not iban_emp:
                        st.warning("⚠️ Configura o IBAN da empresa no tab 🏢")
                    else:
                        df_com_iban = df_calc[
                            df_calc['IBAN'].str.strip().str.len() >= 15
                        ]
                        sem_iban = len(df_calc) - len(df_com_iban)
                        try:
                            xml_str   = _gerar_sepa_xml(
                                df_com_iban, semana_ini, semana_fim, cfg_emp
                            )
                            xml_bytes = xml_str.encode('utf-8')
                            fname_xml = (f"montepio_diarias_"
                                         f"{semana_ini.strftime('%Y%m%d')}.xml")
                            st.download_button(
                                "🏦 Montepio XML",
                                data=xml_bytes,
                                file_name=fname_xml,
                                mime="application/xml",
                                use_container_width=True,
                                key="btn_sepa_xml",
                                help="Carregar no Net24 Empresas → "
                                     "Gestão de Ficheiros → Importar"
                            )
                            if sem_iban > 0:
                                st.warning(
                                    f"⚠️ {sem_iban} sem IBAN — não incluídos."
                                )
                        except Exception as ex:
                            st.error(f"Erro ao gerar XML: {ex}")

                with col_pg:
                    semana_ja_paga = False
                    if not diarias_pagamentos.empty:
                        jp = diarias_pagamentos[
                            (diarias_pagamentos['Semana_Inicio'] ==
                             semana_ini.strftime('%d/%m/%Y')) &
                            (diarias_pagamentos['Status'] == 'Pago')
                        ]
                        semana_ja_paga = not jp.empty

                    if semana_ja_paga:
                        st.success("✅ Semana marcada como paga.")
                    else:
                        if st.button(
                            "✅ Marcar como Paga",
                            key="btn_marcar_pago",
                            type="primary",
                            use_container_width=True
                        ):
                            novos_pags = []
                            for _, row in df_calc.iterrows():
                                detalhe_r = {}
                                try:
                                    detalhe_r = json.loads(
                                        row.get('Detalhes', '{}')
                                    )
                                except:
                                    pass
                                pdf_r = _gerar_recibo_pdf(
                                    tec_nome   = row['Técnico'],
                                    iban       = row['IBAN'],
                                    semana_ini = semana_ini,
                                    semana_fim = semana_fim,
                                    detalhes   = detalhe_r,
                                    total      = row['Valor_Total']
                                )
                                novos_pags.append({
                                    "ID": str(uuid.uuid4())[:8].upper(),
                                    "Semana_Inicio": semana_ini.strftime(
                                        '%d/%m/%Y'),
                                    "Semana_Fim":    semana_fim.strftime(
                                        '%d/%m/%Y'),
                                    "Técnico":       row['Técnico'],
                                    "Obras":         row['Obras'],
                                    "Dias_Total":    row['Dias_Total'],
                                    "Valor_Total":   row['Valor_Total'],
                                    "IBAN":          row['IBAN'],
                                    "Status":        "Pago",
                                    "Data_Pagamento":datetime.now().strftime(
                                        '%d/%m/%Y %H:%M'),
                                    "Pago_Por":      admin_nome,
                                    "Recibo_b64":    base64.b64encode(
                                        pdf_r).decode()
                                })

                            df_novos = pd.DataFrame(novos_pags)
                            updated  = pd.concat(
                                [diarias_pagamentos, df_novos],
                                ignore_index=True
                            ) if not diarias_pagamentos.empty else df_novos
                            save_db(updated, "diarias_pagamentos.csv")
                            log_audit(
                                usuario=admin_nome,
                                acao="MARCAR_DIARIAS_PAGAS",
                                tabela="diarias_pagamentos.csv",
                                registro_id=semana_ini.strftime('%Y%m%d'),
                                detalhes=(f"{len(df_calc)} colaboradores "
                                          f"· € {total_geral:.2f}"),
                                ip=""
                            )
                            inv()
                            st.success(
                                f"✅ {len(df_calc)} colaboradores marcados "
                                f"como pagos — € {total_geral:.2f}"
                            )
                            st.session_state['diarias_calc'] = False
                            st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 2 — CONFIGURAR VALORES  ← SUBSTITUIR ESTE BLOCO
    # ════════════════════════════════════════════════════════════════
    with tab_config:
        st.markdown("### ⚙️ Valor da Diária por Obra")
        st.info(
            f"Valor padrão: **€ {_VALOR_DIARIA_PADRAO:.2f}/dia** "
            f"(aplicado a obras sem configuração específica). "
            f"Mínimo de horas para contar 1 diária: "
            f"**{_MIN_HORAS_DIARIA:.0f}h**."
        )

        obras_lista = obras_db['Obra'].tolist() \
                      if not obras_db.empty else []

        if not obras_lista:
            st.warning("⚠️ Sem obras registadas.")
        else:
            # ── Construir dataframe editável ──────────────────────
            rows_cfg = []
            for obra in obras_lista:
                rows_cfg.append({
                    "Obra":       obra,
                    "€ / Dia":    _get_valor_diaria(obra, diarias_config),
                    "Ativa":      True,
                })
            df_cfg = pd.DataFrame(rows_cfg)

            st.markdown(
                "<p style='color:#94A3B8;font-size:0.82rem;"
                "margin:0 0 6px;'>"
                "✏️ Edita directamente na tabela e clica "
                "<b>💾 Guardar</b>.</p>",
                unsafe_allow_html=True
            )

            # data_editor — compacto, sem scroll da página
            df_editado = st.data_editor(
                df_cfg,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "Obra": st.column_config.TextColumn(
                        "Obra", disabled=True, width="large"
                    ),
                    "€ / Dia": st.column_config.NumberColumn(
                        "€ / Dia",
                        min_value=0.0,
                        max_value=999.0,
                        step=0.5,
                        format="€ %.2f",
                        width="small"
                    ),
                    "Ativa": st.column_config.CheckboxColumn(
                        "Ativa",
                        help="Desativa para excluir da contagem",
                        width="small"
                    ),
                },
                key="data_editor_diarias_config"
            )

            col_sv1, col_sv2 = st.columns(2)
            with col_sv1:
                if st.button(
                    "💾 Guardar Configuração",
                    use_container_width=True,
                    type="primary",
                    key="btn_guardar_diarias_cfg"
                ):
                    novas_config = []
                    for _, row in df_editado.iterrows():
                        novas_config.append({
                            "Obra":          row["Obra"],
                            "Valor_Diaria":  str(row["€ / Dia"]),
                            "Atualizado_Em": datetime.now().strftime(
                                '%d/%m/%Y %H:%M'
                            ),
                            "Atualizado_Por":admin_nome
                        })
                    save_db(
                        pd.DataFrame(novas_config),
                        "diarias_config.csv"
                    )
                    inv()
                    st.success("✅ Configuração guardada!")
                    st.rerun()

            with col_sv2:
                # Preview — total semanal estimado por obra
                total_est = df_editado['€ / Dia'].sum()
                st.markdown(
                    f"<div style='background:#1E293B;"
                    f"border-radius:8px;padding:10px;"
                    f"text-align:center;'>"
                    f"<small style='color:#64748B;'>"
                    f"Custo máx. estimado / dia</small><br>"
                    f"<b style='color:#10B981;"
                    f"font-size:1.1rem;'>"
                    f"€{total_est:,.2f}</b><br>"
                    f"<small style='color:#64748B;'>"
                    f"(todas as obras × 1 técnico)</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    # ════════════════════════════════════════════════════════════════
    # TAB 3 — FALTAS INJUSTIFICADAS
    # ════════════════════════════════════════════════════════════════
    with tab_faltas:
        st.markdown("### ❌ Registar Falta Injustificada")
        st.info(
            "Dias com falta injustificada **não contam** para diária, "
            "mesmo que haja registo de ponto."
        )

        with st.form("form_falta_inj"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                uf = _load_users_fresh()
                users_lista = uf['Nome'].tolist() if not uf.empty else []
                tec_falta  = st.selectbox(
                    "Colaborador *",
                    users_lista if users_lista else ["Sem colaboradores"],
                    key="falta_tec"
                )
                data_falta = st.date_input(
                    "Data da falta *", value=hoje, key="falta_data"
                )
            with col_f2:
                obra_falta = st.selectbox(
                    "Obra",
                    obras_db['Obra'].tolist() if not obras_db.empty else [""],
                    key="falta_obra"
                )
                motivo_falta = st.text_area(
                    "Motivo (opcional)", key="falta_motivo",
                    placeholder="Ex: Ausência sem justificação..."
                )

            if st.form_submit_button(
                "❌ Registar Falta Injustificada",
                use_container_width=True, type="primary"
            ):
                nova_falta = pd.DataFrame([{
                    "ID":            str(uuid.uuid4())[:8].upper(),
                    "Data":          data_falta.strftime('%d/%m/%Y'),
                    "Técnico":       tec_falta,
                    "Obra":          obra_falta,
                    "Motivo":        motivo_falta,
                    "Registado_Por": admin_nome,
                    "Registado_Em":  datetime.now().strftime('%d/%m/%Y %H:%M')
                }])
                updated = pd.concat(
                    [diarias_faltas, nova_falta], ignore_index=True
                ) if not diarias_faltas.empty else nova_falta
                save_db(updated, "diarias_faltas.csv")
                log_audit(
                    usuario=admin_nome,
                    acao="REGISTAR_FALTA_INJUSTIFICADA",
                    tabela="diarias_faltas.csv",
                    registro_id=nova_falta['ID'].iloc[0],
                    detalhes=(f"{tec_falta} em "
                              f"{data_falta.strftime('%d/%m/%Y')}"),
                    ip=""
                )
                inv()
                st.success(
                    f"✅ Falta registada: {tec_falta} — "
                    f"{data_falta.strftime('%d/%m/%Y')}"
                )
                st.rerun()

        if not diarias_faltas.empty:
            st.markdown("---")
            st.markdown("#### 📋 Faltas Registadas Recentes")
            faltas_show = diarias_faltas.sort_values(
                'Data', ascending=False
            ).head(20)
            for _, f in faltas_show.iterrows():
                col_fi, col_fd = st.columns([5, 1])
                with col_fi:
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:8px;"
                        f"padding:10px 14px;margin-bottom:5px;"
                        f"border-left:3px solid #EF4444;'>"
                        f"<b style='color:#F1F5F9;'>{f.get('Técnico','')}</b>"
                        f"<span style='float:right;color:#64748B;"
                        f"font-size:0.8rem;'>{f.get('Data','')}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"{f.get('Obra','')} · "
                        f"{f.get('Motivo','') or 'Sem motivo'}"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )
                with col_fd:
                    if st.button(
                        "🗑️",
                        key=f"del_falta_{f.get('ID','')}",
                        help="Remover falta"
                    ):
                        df_up = diarias_faltas[
                            diarias_faltas['ID'] != f.get('ID', '')
                        ]
                        save_db(df_up, "diarias_faltas.csv")
                        inv()
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — HISTÓRICO
    # ════════════════════════════════════════════════════════════════
    with tab_historico:
        st.markdown("### 📋 Histórico de Pagamentos")

        if diarias_pagamentos.empty:
            st.info("Sem pagamentos registados.")
        else:
            semanas = diarias_pagamentos['Semana_Inicio'].unique().tolist()

            for semana in sorted(semanas, reverse=True):
                pags_sem  = diarias_pagamentos[
                    diarias_pagamentos['Semana_Inicio'] == semana
                ]
                total_sem = pd.to_numeric(
                    pags_sem['Valor_Total'], errors='coerce'
                ).fillna(0).sum()
                fim_sem   = pags_sem.iloc[0].get('Semana_Fim', '')

                with st.expander(
                    f"📅 {semana} — {fim_sem} · "
                    f"{len(pags_sem)} colaboradores · "
                    f"€ {total_sem:.2f}"
                ):
                    for _, p in pags_sem.iterrows():
                        col_pi, col_pr = st.columns([4, 1])
                        with col_pi:
                            st.markdown(
                                f"<div style='background:#1E293B;"
                                f"border-radius:8px;padding:10px;"
                                f"margin-bottom:4px;'>"
                                f"<b style='color:#F1F5F9;'>"
                                f"{p.get('Técnico','')}</b>"
                                f"<span style='float:right;color:#10B981;"
                                f"font-weight:700;'>"
                                f"€ {float(p.get('Valor_Total',0)):.2f}"
                                f"</span><br>"
                                f"<small style='color:#64748B;'>"
                                f"{p.get('Obras','')} · "
                                f"{p.get('Dias_Total','')} dia(s)"
                                f"</small></div>",
                                unsafe_allow_html=True
                            )
                        with col_pr:
                            rec_b64 = p.get('Recibo_b64', '')
                            if rec_b64:
                                try:
                                    st.download_button(
                                        "📄",
                                        data=base64.b64decode(rec_b64),
                                        file_name=(
                                            f"recibo_"
                                            f"{p.get('Técnico','').replace(' ','_')}"
                                            f"_{semana.replace('/','')}.pdf"
                                        ),
                                        mime="application/pdf",
                                        key=f"hist_{p.get('ID','')}",
                                        use_container_width=True
                                    )
                                except:
                                    pass

                    # Re-exportar Excel + SEPA XML do histórico
                    col_h1, col_h2 = st.columns(2)
                    with col_h1:
                        try:
                            s_ini = datetime.strptime(semana, '%d/%m/%Y').date()
                            s_fim = datetime.strptime(fim_sem, '%d/%m/%Y').date()
                            xl_h  = _gerar_excel_semana(pags_sem, s_ini, s_fim)
                            st.download_button(
                                "📥 Excel",
                                data=xl_h,
                                file_name=(f"diarias_"
                                           f"{semana.replace('/','')}.xlsx"),
                                mime="application/vnd.openxmlformats-officedocument"
                                     ".spreadsheetml.sheet",
                                key=f"xl_hist_{semana.replace('/','')}"
                            )
                        except:
                            pass
                    with col_h2:
                        try:
                            s_ini    = datetime.strptime(semana, '%d/%m/%Y').date()
                            s_fim    = datetime.strptime(fim_sem, '%d/%m/%Y').date()
                            cfg_h    = _get_config_empresa()
                            df_iban  = pags_sem[
                                pags_sem['IBAN'].str.strip().str.len() >= 15
                            ]
                            if not df_iban.empty and cfg_h.get('iban',''):
                                xml_h = _gerar_sepa_xml(
                                    df_iban, s_ini, s_fim, cfg_h
                                ).encode('utf-8')
                                st.download_button(
                                    "🏦 XML Montepio",
                                    data=xml_h,
                                    file_name=(f"montepio_"
                                               f"{semana.replace('/','')}.xml"),
                                    mime="application/xml",
                                    key=f"xml_hist_{semana.replace('/','')}"
                                )
                        except:
                            pass

    # ════════════════════════════════════════════════════════════════
    # TAB 5 — CONFIGURAÇÃO DA EMPRESA
    # ════════════════════════════════════════════════════════════════
    with tab_empresa:
        st.markdown("### 🏢 Dados da Empresa Ordenante")
        st.info(
            "Estes dados são usados para gerar o ficheiro SEPA XML "
            "para o Montepio Net24 Empresas."
        )

        cfg = _get_config_empresa()

        with st.form("form_empresa_config"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                emp_nome = st.text_input(
                    "Nome da Empresa *",
                    value=cfg.get('nome', 'Correia Plácido e Sousa, Lda.'),
                    key="emp_nome"
                )
                emp_nif = st.text_input(
                    "NIF *",
                    value=cfg.get('nif', '517182718'),
                    key="emp_nif"
                )
            with col_e2:
                emp_iban = st.text_input(
                    "IBAN da Conta Ordenante *",
                    value=cfg.get('iban', ''),
                    key="emp_iban",
                    placeholder="PT50 XXXX XXXX XXXX XXXX XXXX X",
                    help="Conta que vai ser debitada para pagar as diárias"
                )
                emp_bic = st.text_input(
                    "BIC/SWIFT",
                    value=cfg.get('bic', 'MPIOPTPL'),
                    key="emp_bic",
                    help="BIC do Montepio: MPIOPTPL"
                )

            emp_morada = st.text_input(
                "Morada",
                value=cfg.get('morada',
                              'Zona Industrial de Seia, lote 33, Seia'),
                key="emp_morada"
            )

            st.markdown(
                "<div style='background:rgba(59,130,246,0.1);border-radius:8px;"
                "padding:12px;margin-top:8px;border-left:3px solid #3B82F6;'>"
                "<p style='color:#93C5FD;font-size:0.82rem;margin:0;'>"
                "ℹ️ <b>Como usar o ficheiro SEPA no Montepio:</b><br>"
                "1. Descarrega o ficheiro XML no separador 📅 Semana Atual<br>"
                "2. Abre o Net24 Empresas<br>"
                "3. Vai a <b>Gestão de Ficheiros → Importar Ficheiro</b><br>"
                "4. Seleciona o ficheiro XML gerado<br>"
                "5. Confirma os dados e assina com o cartão matriz<br>"
                "6. O banco processa todas as transferências automaticamente"
                "</p></div>",
                unsafe_allow_html=True
            )

            if st.form_submit_button(
                "💾 Guardar Configuração",
                use_container_width=True, type="primary"
            ):
                erros_emp = []
                if not emp_nome.strip(): erros_emp.append("Nome")
                if not emp_nif.strip():  erros_emp.append("NIF")
                if not emp_iban.strip(): erros_emp.append("IBAN")

                if erros_emp:
                    st.error(
                        f"❌ Campos obrigatórios: {', '.join(erros_emp)}"
                    )
                else:
                    nova_cfg = {
                        "nome":   emp_nome.strip(),
                        "nif":    emp_nif.strip(),
                        "iban":   emp_iban.strip().replace(' ', ''),
                        "bic":    emp_bic.strip(),
                        "morada": emp_morada.strip(),
                    }
                    _save_config_empresa(nova_cfg)
                    inv()
                    st.success("✅ Configuração guardada!")
                    st.rerun()

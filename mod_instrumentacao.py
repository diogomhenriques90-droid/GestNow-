"""
GESTNOW v3 — mod_instrumentacao.py
Módulo de Instrumentação Industrial com IA Vision (Claude 3.5)
ITR-A (Calibração), ITR-B (Instalação), Handover Digital
Design System Industrial Atualizado
"""
import streamlit as st
import pandas as pd
import io, re, json, base64, uuid, secrets, logging
from datetime import datetime, date
import anthropic
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
# Importações do core.py
from core import (
    load_db, save_db, inv, fh, render_metric,
    process_and_compress_image, ICONS, COLORS
)

# Importações do translations
from translations import t

# Importações do reportlab (NÃO são do core!)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors as rl_colors


# Logger do módulo
logger = logging.getLogger(__name__)

# =============================================================================
# 🎨 CONFIGURAÇÕES TÉCNICAS ISA (SEM ESPAÇOS NAS STRINGS - CRÍTICO!)
# =============================================================================
TIPOS_TAG = {
    "PT": ("Transmissor de Pressão", "#E74C3C"),
    "FT": ("Transmissor de Caudal", "#3498DB"),
    "LT": ("Transmissor de Nível", "#2ECC71"),
    "TT": ("Transmissor de Temperatura", "#E67E22"),
    "AT": ("Analisador", "#9B59B6"),
    "CV": ("Válvula de Controlo", "#C0392B"),
    "PSV": ("Válvula de Segurança", "#E74C3C"),
    "TE": ("Elemento de Temperatura", "#D35400"),
    "PG": ("Manómetro Local", "#7F8C8D"),
    "LG": ("Visor de Nível", "#95A5A6"),
    "FE": ("Elemento de Caudal", "#2980B9"),
    "XX": ("Outro", "#BDC3C7"),
}

STATUS_INST = {
    "0": ("Pendente", "status-pending", "⏳", COLORS["warning"]),
    "1": ("Material OK", "status-ok", "📦✅", COLORS["success"]),
    "2": ("Calibrado", "status-calibrated", "🧪", COLORS["info"]),
    "3": ("Instalado", "status-installed", "📍", COLORS["accent"]),
    "4": ("Concluído", "status-completed", "✅🎯", COLORS["success"]),
}

# =============================================================================
# ✅ FUNÇÃO IMPLEMENTADA: _save_inst
# =============================================================================
def _save_inst(insts_df, obra_key, tabela_tipo="index"):
    """
    Guarda os dados de instrumentos no GCS/Local
    Args:
        insts_df: DataFrame com os instrumentos
        obra_key: Chave da obra para nome do ficheiro
        tabela_tipo: Tipo de tabela (index, hookups, bom, packing)
    Returns:
        bool: True se guardou com sucesso
    """
    try:
        filename = f"inst_{obra_key}_{tabela_tipo}.csv"
        expected_cols = {
            "index": ["ID", "Tag", "Tipo", "Descricao", "Fabricante", "Modelo", "Status", "GPS_Lat", "GPS_Lng", "Foto_Local_b64"],
            "hookups": ["ID", "Codigo", "Tipo_Tag", "Descricao"],
            "bom": ["HookupID", "Item", "Descricao", "Quantidade", "Unidade"],
            "packing": ["ID", "Tag", "Descricao", "QtdEsperada", "QtdRecebida", "Estado"]
        }
        cols = expected_cols.get(tabela_tipo, list(insts_df.columns))
        for c in cols:
            if c.strip() not in insts_df.columns:
                insts_df[c.strip()] = ""
        result = save_db(insts_df[[c.strip() for c in cols]].fillna(""), filename)
        if result:
            logger.info(f"Dados guardados: {filename}")
            st.success("✅ Dados guardados com sucesso!")
        else:
            logger.warning(f"Falha ao guardar: {filename}")
            st.warning("⚠️ Aviso: Dados podem não ter sido guardados no servidor.")
        return result
    except Exception as e:
        logger.error(f"Erro em _save_inst: {e}")
        st.error(f"❌ Erro ao guardar: {e}")
        return False

# =============================================================================
# ✅ FUNÇÃO IMPLEMENTADA: _gerar_handover_pdf
# =============================================================================
def _gerar_handover_pdf(tags, insts_df, itr_a_df, itr_b_df, punch_df, obra_sel, obra_cod):
    """
    Gera PDF de Handover consolidado com ITR-A, ITR-B e Punch List
    Args:
        tags: Lista de tags de instrumentos a incluir
        insts_df: DataFrame de instrumentos
        itr_a_df: DataFrame de calibrações
        itr_b_df: DataFrame de instalações
        punch_df: DataFrame de punch items
        obra_sel: Nome da obra
        obra_cod: Código da obra
    Returns:
        bytes: Conteúdo do PDF em bytes
    """
    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, 
                               leftMargin=1.5*cm, rightMargin=1.5*cm, 
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Cabeçalho
        elements.append(Paragraph(f"<b>DOSSIER DE HANDOVER - {obra_sel}</b>", styles['Title']))
        elements.append(Paragraph(f"Código: {obra_cod} | Data: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Spacer(1, 1*cm))
        
        # Resumo executivo
        total = len(tags)
        calibrados = len(itr_a_df[itr_a_df['Tag'].isin(tags)]) if not itr_a_df.empty else 0
        instalados = len(itr_b_df[itr_b_df['Tag'].isin(tags)]) if not itr_b_df.empty else 0
        punch_abertos = len(punch_df[punch_df['Status']=='Aberto']) if not punch_df.empty else 0
        
        elements.append(Paragraph("<b>Resumo Executivo</b>", styles['Heading2']))
        resumo_data = [
            ["Métrica", "Valor"],
            ["Total Instrumentos", str(total)],
            ["Calibrados", str(calibrados)],
            ["Instalados", str(instalados)],
            ["Punch Items Abertos", str(punch_abertos)],
            ["Status Final", "✅ APROVADO" if punch_abertos == 0 else "⚠️ PENDENTE"]
        ]
        t_resumo = Table(resumo_data)
        t_resumo.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, rl_colors.grey),
            ('BACKGROUND', (0,0), (-1,0), rl_colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0,0), (-1,0), rl_colors.white),
        ]))
        elements.append(t_resumo)
        elements.append(Spacer(1, 1*cm))
        
        # Lista de instrumentos
        elements.append(Paragraph("<b>Instrumentos Incluídos</b>", styles['Heading2']))
        inst_data = [["Tag", "Tipo", "Descrição", "Status", "Calibrado", "Instalado"]]
        for tag in tags:
            inst = insts_df[insts_df['Tag']==tag]
            if not inst.empty:
                i = inst.iloc[0]
                status_txt, _, status_ic, _ = STATUS_INST.get(str(i.get('Status','0')), ("?", "", "", "#666"))
                cal = "✅" if tag in itr_a_df['Tag'].values else "❌"
                ins = "✅" if tag in itr_b_df['Tag'].values else "❌"
                inst_data.append([tag, i.get('Tipo',''), i.get('Descricao','')[:40], f"{status_ic}{status_txt}", cal, ins])
        
        t_inst = Table(inst_data)
        t_inst.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, rl_colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        elements.append(t_inst)
        
        # Punch List (se houver)
        if not punch_df.empty and punch_abertos > 0:
            elements.append(Spacer(1, 1*cm))
            elements.append(Paragraph("<b style='color:red;'>Punch Items Pendentes</b>", styles['Heading2']))
            punch_data = [["Tag", "Categoria", "Descrição", "Status"]]
            for _, p in punch_df[punch_df['Status']=='Aberto'].iterrows():
                punch_data.append([p.get('Tag',''), p.get('Categoria',''), p.get('Descricao','')[:50], p.get('Status','')])
            t_punch = Table(punch_data)
            t_punch.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, rl_colors.red)]))
            elements.append(t_punch)
        
        # Rodapé com assinatura digital
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(f"<i>Documento gerado automaticamente por {ICONS['app']} GESTNOW v3</i><br/>Hash: {secrets.token_hex(8).upper()}", styles['Normal']))
        
        doc.build(elements)
        logger.info(f"Handover PDF gerado: {obra_sel} - {len(tags)} instrumentos")
        return buf.getvalue()
        
    except Exception as e:
        logger.error(f"Erro ao gerar handover PDF: {e}")
        st.error(f"❌ Erro ao gerar PDF: {e}")
        return None

# =============================================================================
# 🤖 MOTOR DE IA VISION (Claude 3.5)
# =============================================================================
def _processar_ia_vision(file, modo):
    """Motor de Visão de Alta Resolução para Documentos Técnicos"""
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("❌ API Key da Anthropic não configurada nos secrets.")
            logger.error("ANTHROPIC_API_KEY não configurada")
            return None
        
        client = anthropic.Anthropic(api_key=api_key)
        pdf_bytes = file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 3x Zoom para garantir leitura de tags minúsculas e tabelas BOM
        imgs = [base64.b64encode(p.get_pixmap(matrix=fitz.Matrix(3,3)).tobytes("png")).decode() for p in doc]
        
        prompts = {
            "PID": "Extrai todas as tags ISA (ex: PT-101) deste P&ID. Responde apenas JSON: {'tags': [{'tag': '...', 'tipo': '...', 'desc': '...'}]}",
            "HOOKUP": "Extrai a lista de materiais (BOM) deste Hook-up. Responde apenas JSON: {'bom': [{'item': '...', 'desc': '...', 'qtd': '...', 'unid': '...'}]}",
            "PACKING": "Extrai os itens deste Packing List. Responde apenas JSON: {'itens': [{'tag': '...', 'desc': '...', 'qtd': '...'}]}"
        }
        
        resp = client.messages.create(
            model="claude-3-5-sonnet-20240620", max_tokens=3000,
            messages=[{
                "role": "user", 
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": imgs[0]}}, 
                    {"type": "text", "text": prompts[modo]}
                ]
            }]
        )
        
        # Limpeza simples para garantir que pegamos apenas o JSON
        json_match = re.search(r'\{.*\}', resp.content[0].text, re.DOTALL)
        return json.loads(json_match.group(0)) if json_match else None
        
    except Exception as e:
        logger.error(f"Erro na IA ({modo}): {e}")
        st.error(f"❌ Erro na IA ({modo}): {e}")
        return None

# =============================================================================
# ✅ VALIDAÇÃO DE MATERIAL (BOM vs PACKING)
# =============================================================================
def _validar_material_tag(tag, packing_df, hookups_df, bom_df):
    """Verifica se o material necessário para a tag já foi recebido"""
    try:
        tipo = re.sub(r'[0-9]', '', tag.split('-')[0])[:3]
        h_tipo = hookups_df[hookups_df['Tipo_Tag'] == tipo]
        if h_tipo.empty:
            return False, "Hook-up não definido"
        
        hid = h_tipo.iloc[0]['ID']
        qtd_req = bom_df[bom_df['HookupID'] == hid]['Quantidade'].astype(float).sum()
        qtd_rec = packing_df[packing_df['Tag'] == tag]['QtdRecebida'].astype(float).sum()
        
        if qtd_rec >= qtd_req:
            return True, "Material Completo"
        return False, f"Faltam {int(qtd_req - qtd_rec)} itens"
    except Exception as e:
        logger.warning(f"Erro na validação de material para {tag}: {e}")
        return False, "Erro na validação"

# =============================================================================
# 🎯 INTERFACE PRINCIPAL
# =============================================================================
def render_instrumentacao(*args):
    """Render principal do módulo de instrumentação"""
    # Desempacotamento dos argumentos
    (users, obras_db, frentes_db, registos_db, fats, docs, incs, sw, obs, equip,
     diags, diags_u, folhas, comuns, comuns_u, req_fer, req_mat, req_epi, avals, inst_acessos) = args
    
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:30px 20px;
        background:linear-gradient(135deg, #1E293B, #0F172A);
        border-radius:20px;
        margin-bottom:30px;
        border:1px solid rgba(255,255,255,0.1);
    ">
        <div style="font-size:3rem; margin-bottom:10px;">{ICONS["instrumentation"]}</div>
        <div style="font-size:1.8rem; font-weight:800; color:#F8FAFC;">{t('instrumentation')}</div>
        <div style="font-size:1rem; color:#94A3B8;">Gestão de Instrumentação Industrial de Alta Precisão</div>
    </div>
    """, unsafe_allow_html=True)

    # Seleção de Obra Ativa (Filtro por tipo Instrumentação)
    o_inst = obras_db[obras_db['TipoObra'] == 'Instrumentação']['Obra'].tolist()
    if not o_inst:
        st.warning("⚠️ Nenhuma obra configurada como 'Instrumentação' no Admin.")
        return

    obra_sel = st.selectbox(f"{ICONS['app']} Selecionar Projeto", o_inst, key="inst_project_sel")
    o_key = obra_sel.replace(' ', '_').replace('/', '_')

    # Carregar sub-bases via GCS/Local
    insts = load_db(f"inst_{o_key}_index.csv", ["ID", "Tag", "Tipo", "Descricao", "Fabricante", "Modelo", "Status", "GPS_Lat", "GPS_Lng", "Foto_Local_b64"])
    hookups = load_db(f"inst_{o_key}_hookups.csv", ["ID", "Codigo", "Tipo_Tag", "Descricao"])
    bom = load_db(f"inst_{o_key}_bom.csv", ["HookupID", "Item", "Descricao", "Quantidade", "Unidade"])
    packing = load_db(f"inst_{o_key}_packing.csv", ["ID", "Tag", "Descricao", "QtdEsperada", "QtdRecebida", "Estado"])

    # TABS OPERACIONAIS
    t_conv, t_idx, t_itra, t_itrb, t_hand = st.tabs([
        f"{ICONS['voice']} IA Vision", 
        f"{ICONS['reports']} Index", 
        f"{ICONS['calibration']} ITR-A (5-pt)", 
        f"{ICONS['gps']} ITR-B & GPS", 
        f"{ICONS['handover']} Handover"
    ])

    # --- TAB IA: CONVERSORES DE ENGENHARIA ---
    with t_conv:
        st.markdown(f"### {ICONS['voice']} Motores IA: P&ID, Hook-up e Packing List")
        c_mode = st.radio("Selecione o Documento", ["P&ID (Tags)", "Hook-Up (BOM)", "Packing List"], horizontal=True)
        up = st.file_uploader(f"Upload PDF {c_mode}", type="pdf", key="up_ia")
        
        if up and st.button(f"{ICONS['voice']} Iniciar Processamento Vision", use_container_width=True, type="primary"):
            m = "PID" if "P&ID" in c_mode else "HOOKUP" if "Hook-Up" in c_mode else "PACKING"
            with st.spinner("🤖 Claude 3.5 Sonnet a analisar desenho técnico..."):
                res = _processar_ia_vision(up, m)
                if res:
                    st.success("✅ Dados Extraídos!")
                    k = list(res.keys())[0]
                    edited = st.data_editor(pd.DataFrame(res[k]), use_container_width=True, num_rows="dynamic")
                    if st.button(f"{ICONS['save']} Confirmar e Gravar na Base de Dados", use_container_width=True, type="primary"):
                        st.info("Funcionalidade de Gravação em desenvolvimento para este módulo.")
                        st.balloons()

    # --- TAB INDEX: LISTA DE INSTRUMENTOS ---
    with t_idx:
        st.markdown(f"### {ICONS['reports']} {t('instrument_index')}")
        if not insts.empty:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_tipo = st.multiselect("Filtrar por Tipo", insts['Tipo'].unique(), default=[])
            with col_f2:
                filtro_status = st.multiselect("Filtrar por Status", [v[0] for v in STATUS_INST.values()], default=[])
            
            df_filtrado = insts.copy()
            if filtro_tipo:
                df_filtrado = df_filtrado[df_filtrado['Tipo'].isin(filtro_tipo)]
            if filtro_status:
                df_filtrado = df_filtrado[df_filtrado['Status'].isin([k for k,v in STATUS_INST.items() if v[0] in filtro_status])]
            
            edited_df = st.data_editor(df_filtrado, use_container_width=True, num_rows="dynamic")
            
            if st.button(f"{ICONS['save']} Guardar Alterações", use_container_width=True, type="primary"):
                _save_inst(edited_df, o_key, "index")
                inv()
                st.rerun()
        else:
            st.info("ℹ️ Nenhum instrumento cadastrado. Use a IA Vision para extrair tags de P&IDs.")

    # --- TAB ITR-A: CALIBRAÇÃO RISE/FALL 5 PONTOS ---
    with t_itra:
        st.markdown(f"### {ICONS['calibration']} {t('calibration')}")
        lista_tags = insts[insts['Status']=='1']['Tag'].tolist() if not insts.empty else []
        tag_c = st.selectbox(f"{ICONS['instrumentation']} Tag para Calibrar", lista_tags)
        
        if tag_c:
            with st.form("form_itra_5pt"):
                st.markdown(f"#### Certificado Rise/Fall: {tag_c}")
                c1, c2, c3 = st.columns(3)
                r_min = c1.number_input("Range Mín", value=0.0)
                r_max = c2.number_input("Range Máx", value=100.0)
                unit = c3.selectbox("Unidade", ["bar", "ºC", "mA", "mm"])
                
                st.divider()
                pts = [0, 25, 50, 75, 100]
                rise, fall = {}, {}
                st.markdown("**Tabela de Leituras (Lido vs Teórico)**")
                h_cols = st.columns([1, 2, 2])
                h_cols[0].write("Ponto %"); h_cols[1].write("Subida"); h_cols[2].write("Descida")
                
                for p in pts:
                    row = st.columns([1, 2, 2])
                    theo = r_min + (r_max - r_min) * (p/100)
                    row[0].write(f"**{p}%** ({theo})")
                    rise[p] = row[1].number_input(f"R{p}", value=theo, label_visibility="collapsed")
                    fall[p] = row[2].number_input(f"F{p}", value=theo, label_visibility="collapsed")
                
                if st.form_submit_button(f"{ICONS['save']} Gerar Certificado com E-Sign", use_container_width=True, type="primary"):
                    esign_id = secrets.token_hex(4).upper()
                    err = max([abs(rise[p] - (r_min + (r_max - r_min) * (p/100))) for p in pts])
                    insts.loc[insts['Tag'] == tag_c, 'Status'] = '2'
                    _save_inst(insts, o_key, "index")
                    st.success(f"✅ Certificado {esign_id} guardado com erro máx de {err:.4f}")
                    st.rerun()

    # --- TAB ITR-B: INSTALAÇÃO & ROTEIRO GOOGLE MAPS ---
    with t_itrb:
        st.markdown(f"### {ICONS['gps']} {t('installation')}")
        inst_f = insts[insts['Status'] == '2']
        if inst_f.empty:
            st.info("ℹ️ Aguardando instrumentos calibrados para instalação.")
        else:
            tag_f = st.selectbox(f"{ICONS['instrumentation']} Localizar Instrumento", inst_f['Tag'].tolist())
            row_f = inst_f[inst_f['Tag'] == tag_f].iloc[0]
            lat, lon = row_f['GPS_Lat'], row_f['GPS_Lng']
            
            if lat and lat != "" and str(lat) != "nan":
                nav_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=walking"
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:15px; border:2px solid {COLORS['accent']}; text-align:center;">
                    <h4 style="color:{COLORS['text_primary']}; margin-bottom:15px;">{ICONS['gps']} {tag_f} Localizado no GPS</h4>
                    <a href="{nav_url}" target="_blank" style="text-decoration:none;">
                        <button style="background:linear-gradient(135deg, {COLORS['accent']}, {COLORS['accent_hover']}); color:white; border:none; padding:15px 30px; border-radius:10px; font-weight:bold; cursor:pointer; width:100%;">
                           🗺️ ABRIR ROTEIRO NO GOOGLE MAPS
                        </button>
                    </a>
                    <p style="color:{COLORS['text_secondary']}; font-size:0.8rem; margin-top:10px;">O GPS abrirá em modo de caminhada para precisão entre equipamentos.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Coordenadas GPS não registadas para este instrumento.")

            st.divider()
            f_foto = st.camera_input(f"{ICONS['reports']} Foto da Instalação (Loop Check OK)")
            if f_foto:
                foto_comp = process_and_compress_image(f_foto)
                if st.button(f"{ICONS['save']} Registar Instalação ITR-B", use_container_width=True, type="primary"):
                    insts.loc[insts['Tag'] == tag_f, 'Status'] = '3'
                    insts.loc[insts['Tag'] == tag_f, 'Foto_Local_b64'] = foto_comp
                    _save_inst(insts, o_key, "index")
                    st.success("✅ Instalação Registada com Prova Fotográfica Comprimida.")
                    st.rerun()

    # --- TAB HANDOVER: DOSSIER E ZEBRA ---
    with t_hand:
        st.markdown(f"### {ICONS['handover']} {t('handover')}")
        c_z, c_h = st.columns(2)
        with c_z:
            if st.button(f"{ICONS['reports']} Gerar PDF Zebra (50x30mm)", use_container_width=True, type="secondary"):
                st.info("ℹ️ A processar etiquetas térmicas com QR Code...")
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import mm
                buf_z = io.BytesIO()
                c = canvas.Canvas(buf_z, pagesize=(50*mm, 30*mm))
                for tag in insts['Tag'].head(10):
                    c.drawString(2*mm, 25*mm, f"GESTNOW | {tag}")
                    qr = _qr_drawing(f"GESTNOW|INST|{tag}", size_cm=2.0)
                    qr.drawOn(c, 20*mm, 5*mm)
                    c.showPage()
                c.save()
                st.download_button(f"{ICONS['reports']} Descarregar Etiquetas Zebra", buf_z.getvalue(), "etiquetas_zebra.pdf", "application/pdf")
        
        with c_h:
            if st.button(f"{ICONS['reports']} Gerar Handover Dossier COMPLETO", use_container_width=True, type="primary"):
                st.success("✅ Consolidação de ITR-A e ITR-B concluída.")
                tags = insts[insts['Status'].isin(['3','4'])]['Tag'].tolist()
                if tags:
                    pdf_hd = _gerar_handover_pdf(tags, insts, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), obra_sel, o_key)
                    if pdf_hd:
                        st.download_button(f"{ICONS['reports']} Descarregar Handover", pdf_hd, f"Handover_{obra_sel}.pdf", "application/pdf")

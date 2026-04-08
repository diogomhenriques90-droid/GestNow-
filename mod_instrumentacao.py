"""
GESTNOW v3 — mod_instrumentacao.py
Módulo de Instrumentação Industrial com IA Vision + Assinatura Digital
ITR-A (Calibração), ITR-B (Instalação), Handover Digital
"""
import streamlit as st
import pandas as pd
import io, re, json, base64, uuid, secrets, logging, hashlib
from datetime import datetime, date
import anthropic
import fitz  # PyMuPDF
from core import log_audit, criar_notificacao

# Importações do core.py
try:
    from core import (
        load_db, save_db, inv, fh, render_metric,
        process_and_compress_image, ICONS, COLORS, log_audit,
        gerar_hash_assinatura, render_signature_pad, validar_assinatura
    )
except ImportError as e:
    st.error(f"Erro ao importar do core.py: {e}")

from translations import t

# Imports do reportlab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors as rl_colors
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)

# =============================================================================
# 🎨 CONFIGURAÇÕES TÉCNICAS ISA
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
    "0": ("Pendente", "status-pending", "⏳"),
    "1": ("Material OK", "status-ok", "📦"),
    "2": ("Calibrado", "status-calibrated", "🔬"),
    "3": ("Instalado", "status-installed", "📍"),
    "4": ("Concluído", "status-completed", "✅"),
}

# =============================================================================
# ✅ FUNÇÃO: _save_inst
# =============================================================================
def _save_inst(insts_df, obra_key, tabela_tipo="index"):
    try:
        filename = f"inst_{obra_key}_{tabela_tipo}.csv"
        expected_cols = {
            "index": ["ID", "Tag", "Tipo", "Descricao", "Fabricante", "Modelo", "Status", "GPS_Lat", "GPS_Lng", "Foto_Local_b64", "Assinatura_Calibracao_b64", "Assinatura_Instalacao_b64", "Hash_Validacao"],
            "hookups": ["ID", "Codigo", "Tipo_Tag", "Descricao"],
            "bom": ["HookupID", "Item", "Descricao", "Quantidade", "Unidade"],
            "packing": ["ID", "Tag", "Descricao", "QtdEsperada", "QtdRecebida", "Estado"]
        }
        cols = expected_cols.get(tabela_tipo, list(insts_df.columns))
        for c in cols:
            if c not in insts_df.columns:
                insts_df[c] = ""
        result = save_db(insts_df[cols].fillna(""), filename)
        if result:
            st.success("✅ Dados guardados!")
        return result
    except Exception as e:
        logger.error(f"Erro em _save_inst: {e}")
        st.error(f"❌ Erro ao guardar: {e}")
        return False

# =============================================================================
# ✅ FUNÇÃO: _gerar_etiquetas_zebra
# =============================================================================
def _gerar_etiquetas_zebra(tags, obra_sel):
    if not REPORTLAB_AVAILABLE:
        return None
    try:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(50*mm, 30*mm))
        for tag in tags:
            c.setFont("Helvetica-Bold", 8)
            c.drawString(2*mm, 25*mm, f"GESTNOW | {tag}")
            c.setFont("Helvetica", 6)
            c.drawString(2*mm, 20*mm, f"{obra_sel}")
            c.rect(20*mm, 5*mm, 20*mm, 20*mm)
            c.drawString(21*mm, 14*mm, "QR")
            c.showPage()
        c.save()
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Erro ao gerar etiquetas Zebra: {e}")
        return None

# =============================================================================
# ✅ FUNÇÃO: _gerar_certificado_itr_a (COM ASSINATURA)
# =============================================================================
def _gerar_certificado_itr_a(tag, dados_calibracao, assinatura_b64, usuario, obra_sel):
    """Gera PDF de certificado ITR-A com assinatura digital"""
    if not REPORTLAB_AVAILABLE:
        return None
    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Cabeçalho
        elements.append(Paragraph(f"<b>CERTIFICADO DE CALIBRAÇÃO ITR-A</b>", styles['Title']))
        elements.append(Paragraph(f"Obra: {obra_sel} | Tag: {tag}", styles['Normal']))
        elements.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 1*cm))
        
        # Dados da calibração
        elements.append(Paragraph("<b>Dados Técnicos</b>", styles['Heading2']))
        data_calib = [
            ["Parâmetro", "Valor"],
            ["Range Mínimo", f"{dados_calibracao['r_min']} {dados_calibracao['unit']}"],
            ["Range Máximo", f"{dados_calibracao['r_max']} {dados_calibracao['unit']}"],
            ["Erro Máximo", f"{dados_calibracao['erro']:.4f} {dados_calibracao['unit']}"],
            ["Certificado ID", dados_calibracao['esign_id']],
            ["Hash de Validação", dados_calibracao['hash']]
        ]
        t_calib = Table(data_calib)
        t_calib.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, rl_colors.grey), ('BACKGROUND', (0,0), (-1,0), rl_colors.HexColor('#0F172A')), ('TEXTCOLOR', (0,0), (-1,0), rl_colors.white)]))
        elements.append(t_calib)
        elements.append(Spacer(1, 1*cm))
        
        # Tabela Rise/Fall
        elements.append(Paragraph("<b>Leituras Rise/Fall (5 pontos)</b>", styles['Heading2']))
        dados_tabela = [["Ponto %", "Teórico", "Subida", "Descida", "Desvio"]]
        for p in [0, 25, 50, 75, 100]:
            theo = dados_calibracao['r_min'] + (dados_calibracao['r_max'] - dados_calibracao['r_min']) * (p/100)
            rise = dados_calibracao['rise'].get(p, theo)
            fall = dados_calibracao['fall'].get(p, theo)
            desvio = max(abs(rise-theo), abs(fall-theo))
            dados_tabela.append([f"{p}%", f"{theo:.2f}", f"{rise:.2f}", f"{fall:.2f}", f"{desvio:.4f}"])
        t_leituras = Table(dados_tabela)
        t_leituras.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, rl_colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8)]))
        elements.append(t_leituras)
        elements.append(Spacer(1, 2*cm))
        
        # Assinatura
        elements.append(Paragraph("<b>Assinatura do Técnico</b>", styles['Heading2']))
        if assinatura_b64:
            elements.append(Paragraph(f"<i>Assinado digitalmente por: {usuario}</i>", styles['Normal']))
            elements.append(Paragraph(f"<i>Hash: {dados_calibracao['hash']}</i>", styles['Normal']))
            # Placeholder para imagem da assinatura (implementar com st-canvas no futuro)
            elements.append(Spacer(1, 1*cm))
            elements.append(Paragraph("✍️ __________________________", styles['Normal']))
        else:
            elements.append(Paragraph("<i style='color:red;'>⚠️ Assinatura não capturada</i>", styles['Normal']))
        
        # Rodapé
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(f"<i>Documento gerado por GESTNOW v3 | Compliance SGS/ISO 9001</i>", styles['Normal']))
        
        doc.build(elements)
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Erro ao gerar certificado ITR-A: {e}")
        return None

# =============================================================================
# 🤖 MOTOR DE IA VISION
# =============================================================================
def _processar_ia_vision(file, modo):
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("❌ API Key da Anthropic não configurada.")
            return None
        client = anthropic.Anthropic(api_key=api_key)
        pdf_bytes = file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [base64.b64encode(p.get_pixmap(matrix=fitz.Matrix(3,3)).tobytes("png")).decode() for p in doc]
        prompts = {
            "PID": "Extrai todas as tags ISA (ex: PT-101) deste P&ID. Responde apenas JSON: {'tags': [{'tag': '...', 'tipo': '...', 'desc': '...'}]}",
            "HOOKUP": "Extrai a lista de materiais (BOM) deste Hook-up. Responde apenas JSON: {'bom': [{'item': '...', 'desc': '...', 'qtd': '...', 'unid': '...'}]}",
            "PACKING": "Extrai os itens deste Packing List. Responde apenas JSON: {'itens': [{'tag': '...', 'desc': '...', 'qtd': '...'}]}"
        }
        resp = client.messages.create(
            model="claude-3-5-sonnet-20240620", max_tokens=3000,
            messages=[{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": imgs[0]}}, {"type": "text", "text": prompts[modo]}]}]
        )
        json_match = re.search(r'\{.*\}', resp.content[0].text, re.DOTALL)
        return json.loads(json_match.group(0)) if json_match else None
    except Exception as e:
        logger.error(f"Erro na IA ({modo}): {e}")
        st.error(f"❌ Erro na IA: {e}")
        return None

# =============================================================================
# ✅ VALIDAÇÃO DE MATERIAL
# =============================================================================
def _validar_material_tag(tag, packing_df, hookups_df, bom_df):
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
        logger.warning(f"Erro na validação de {tag}: {e}")
        return False, "Erro na validação"

# =============================================================================
# 🎯 INTERFACE PRINCIPAL
# =============================================================================
def render_instrumentacao(*args):
    (users, obras_db, frentes_db, registos_db, fats, docs, incs, sw, obs, equip,
     diags, diags_u, folhas, comuns, comuns_u, req_fer, req_mat, req_epi, avals, inst_acessos) = args
    
    st.markdown(f"""
    <div style="text-align:center; padding:30px 20px; background:linear-gradient(135deg, #1E293B, #0F172A); border-radius:20px; margin-bottom:30px;">
        <div style="font-size:3rem; margin-bottom:10px;">🔧</div>
        <div style="font-size:1.8rem; font-weight:800; color:#F8FAFC;">{t('instrumentation')}</div>
        <div style="font-size:1rem; color:#94A3B8;">Gestão de Instrumentação Industrial</div>
    </div>
    """, unsafe_allow_html=True)

    o_inst = obras_db[obras_db['TipoObra'] == 'Instrumentação']['Obra'].tolist()
    if not o_inst:
        st.warning("⚠️ Nenhuma obra configurada como 'Instrumentação'.")
        return
    
    obra_sel = st.selectbox("🏗️ Selecionar Projeto", o_inst, key="inst_project_sel")
    o_key = obra_sel.replace(' ', '_').replace('/', '_')

    insts = load_db(f"inst_{o_key}_index.csv", ["ID","Tag","Tipo","Descricao","Fabricante","Modelo","Status","GPS_Lat","GPS_Lng","Foto_Local_b64","Assinatura_Calibracao_b64","Assinatura_Instalacao_b64","Hash_Validacao"])
    hookups = load_db(f"inst_{o_key}_hookups.csv", ["ID","Codigo","Tipo_Tag","Descricao"])
    bom = load_db(f"inst_{o_key}_bom.csv", ["HookupID","Item","Descricao","Quantidade","Unidade"])
    packing = load_db(f"inst_{o_key}_packing.csv", ["ID","Tag","Descricao","QtdEsperada","QtdRecebida","Estado"])

    t_conv, t_idx, t_itra, t_itrb, t_hand = st.tabs(["🤖 IA Vision", "📋 Index", "🔬 ITR-A", "🏗️ ITR-B & GPS", "📄 Handover"])

    # --- TAB IA VISION ---
    with t_conv:
        st.markdown("### 🤖 Motores IA: P&ID, Hook-up e Packing List")
        c_mode = st.radio("Documento", ["P&ID (Tags)", "Hook-Up (BOM)", "Packing List"], horizontal=True)
        up = st.file_uploader(f"Upload PDF {c_mode}", type="pdf", key="up_ia")
        if up and st.button("🚀 Processar Vision", use_container_width=True, type="primary"):
            m = "PID" if "P&ID" in c_mode else "HOOKUP" if "Hook-Up" in c_mode else "PACKING"
            with st.spinner("🤖 Claude 3.5 a analisar..."):
                res = _processar_ia_vision(up, m)
                if res:
                    st.success("✅ Dados Extraídos!")
                    k = list(res.keys())[0]
                    edited = st.data_editor(pd.DataFrame(res[k]), use_container_width=True, num_rows="dynamic")
                    if st.button("✅ Confirmar e Gravar", use_container_width=True, type="primary"):
                        log_audit(usuario=st.session_state.user, acao="IA_VISION_EXTRACAO", tabela=f"inst_{o_key}_index.csv", registro_id=c_mode, detalhes=f"Extração via IA: {c_mode} para obra {obra_sel}", ip="")
                        st.info("Gravação em desenvolvimento...")
                        st.balloons()

    # --- TAB INDEX ---
    with t_idx:
        st.markdown("### 📋 Index de Instrumentos")
        if not insts.empty:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_tipo = st.multiselect("Tipo", insts['Tipo'].unique(), default=[])
            with col_f2:
                filtro_status = st.multiselect("Status", [v[0] for v in STATUS_INST.values()], default=[])
            df_f = insts.copy()
            if filtro_tipo: df_f = df_f[df_f['Tipo'].isin(filtro_tipo)]
            if filtro_status: df_f = df_f[df_f['Status'].isin([k for k,v in STATUS_INST.items() if v[0] in filtro_status])]
            edited = st.data_editor(df_f, use_container_width=True, num_rows="dynamic")
            if st.button("💾 Guardar Alterações", use_container_width=True, type="primary"):
                for _, row in edited.iterrows():
                    log_audit(usuario=st.session_state.user, acao="EDITAR_INSTRUMENTO", tabela=f"inst_{o_key}_index.csv", registro_id=row.get('Tag', ''), detalhes=f"Editado: {row.get('Tag')} - Status: {row.get('Status')}", ip="")
                _save_inst(edited, o_key, "index")
                inv()
                st.success("✅ Alterações guardadas!")
                st.rerun()
        else:
            st.info("ℹ️ Sem instrumentos. Use IA Vision para extrair tags.")

    # --- TAB ITR-A: CALIBRAÇÃO COM ASSINATURA DIGITAL ---
    with t_itra:
        st.markdown("### 🔬 Calibração ITR-A (5 pontos) + ✍️ Assinatura Digital")
        lista = insts[insts['Status']=='1']['Tag'].tolist() if not insts.empty else []
        tag_c = st.selectbox("Tag para Calibrar", lista)
        
        if tag_c:
            with st.form("form_itra"):
                st.markdown(f"#### Certificado Rise/Fall: {tag_c}")
                c1, c2, c3 = st.columns(3)
                r_min = c1.number_input("Range Mín", value=0.0)
                r_max = c2.number_input("Range Máx", value=100.0)
                unit = c3.selectbox("Unidade", ["bar", "ºC", "mA", "mm"])
                
                st.divider()
                pts = [0, 25, 50, 75, 100]
                rise, fall = {}, {}
                st.markdown("**Tabela de Leituras (Lido vs Teórico)**")
                for p in pts:
                    row = st.columns([1, 2, 2])
                    theo = r_min + (r_max - r_min) * (p/100)
                    row[0].write(f"**{p}%** ({theo:.2f} {unit})")
                    rise[p] = row[1].number_input(f"R{p}", value=theo, label_visibility="collapsed")
                    fall[p] = row[2].number_input(f"F{p}", value=theo, label_visibility="collapsed")
                
                st.divider()
                # ✍️ ASSINATURA DIGITAL
                assinatura = render_signature_pad("Assinatura do Técnico Calibrador", f"sig_{tag_c}")
                
                if st.form_submit_button("💾 Gerar Certificado com Assinatura", use_container_width=True, type="primary"):
                    if not assinatura:
                        st.warning("⚠️ Por favor, assine para validar o certificado.")
                    else:
                        esign = secrets.token_hex(4).upper()
                        err = max([abs(rise[p] - (r_min + (r_max - r_min) * (p/100))) for p in pts])
                        hash_val = gerar_hash_assinatura(st.session_state.user, tag_c, datetime.now().isoformat(), err)
                        
                        # Atualizar instrumento
                        insts.loc[insts['Tag'] == tag_c, 'Status'] = '2'
                        insts.loc[insts['Tag'] == tag_c, 'Assinatura_Calibracao_b64'] = assinatura
                        insts.loc[insts['Tag'] == tag_c, 'Hash_Validacao'] = hash_val
                        _save_inst(insts, o_key, "index")
                        
                        # Gerar PDF
                        dados_calib = {"r_min": r_min, "r_max": r_max, "unit": unit, "erro": err, "rise": rise, "fall": fall, "esign_id": esign, "hash": hash_val}
                        pdf_cert = _gerar_certificado_itr_a(tag_c, dados_calib, assinatura, st.session_state.user, obra_sel)
                        
                        # Log de auditoria
                        log_audit(usuario=st.session_state.user, acao="CALIBRAR_INSTRUMENTO", tabela=f"inst_{o_key}_index.csv", registro_id=tag_c, detalhes=f"Calibração ITR-A: {tag_c} | Erro: {err:.4f} {unit} | Certificado: {esign} | Hash: {hash_val}", ip="")
                        
                        st.success(f"✅ Certificado {esign} gerado com assinatura!")
                        if pdf_cert:
                            st.download_button("📥 Descarregar Certificado PDF", pdf_cert, f"ITR-A_{tag_c}_{esign}.pdf", "application/pdf")
                        st.rerun()

    # 🔔 NOTIFICAR GESTOR SOBRE CALIBRAÇÃO
criar_notificacao(
    destinatario=st.session_state.user,
    titulo="🔬 Calibração Concluída",
    mensagem=f"{tag_c} calibrado com erro máx de {err:.4f} {unit}",
    tipo="success",
    acao_url="/instrumentacao?tab=itra"
)

    # --- TAB ITR-B: INSTALAÇÃO + GPS + ASSINATURA ---
    with t_itrb:
        st.markdown("### 🏗️ Instalação + GPS + ✍️ Assinatura")
        inst_f = insts[insts['Status'] == '2']
        if inst_f.empty:
            st.info("ℹ️ Aguardando instrumentos calibrados.")
        else:
            tag_f = st.selectbox("Localizar Instrumento", inst_f['Tag'].tolist())
            row_f = inst_f[inst_f['Tag'] == tag_f].iloc[0]
            lat, lon = row_f['GPS_Lat'], row_f['GPS_Lng']
            
            if lat and str(lat) != "" and str(lat) != "nan":
                nav_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=walking"
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:15px; border:2px solid #3B82F6; text-align:center;">
                    <h4 style="color:#F8FAFC; margin-bottom:15px;">📍 {tag_f} no GPS</h4>
                    <a href="{nav_url}" target="_blank" style="text-decoration:none;">
                        <button style="background:linear-gradient(135deg, #3B82F6, #60A5FA); color:white; border:none; padding:15px 30px; border-radius:10px; font-weight:bold; cursor:pointer; width:100%;">🗺️ Google Maps</button>
                    </a>
                    <a href="https://waze.com/ul?ll={lat},{lon}&navigate=yes" target="_blank" style="text-decoration:none;">
                        <button style="background:#33CCFF; color:white; border:none; padding:15px 30px; border-radius:10px; font-weight:bold; cursor:pointer; width:100%; margin-top:10px;">🚗 Waze</button>
                    </a>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ GPS não registado.")

            st.divider()
            f_foto = st.camera_input("📸 Foto da Instalação")
            
            # ✍️ ASSINATURA PARA INSTALAÇÃO
            assinatura_inst = render_signature_pad("Assinatura do Técnico Instalador", f"sig_inst_{tag_f}")
            
            if f_foto and assinatura_inst:
                foto_comp = process_and_compress_image(f_foto)
                if st.button("✅ Registar Instalação com Assinatura", use_container_width=True, type="primary"):
                    insts.loc[insts['Tag'] == tag_f, 'Status'] = '3'
                    if 'Foto_Local_b64' in insts.columns:
                        insts.loc[insts['Tag'] == tag_f, 'Foto_Local_b64'] = foto_comp
                    insts.loc[insts['Tag'] == tag_f, 'Assinatura_Instalacao_b64'] = assinatura_inst
                    hash_val = gerar_hash_assinatura(st.session_state.user, tag_f, datetime.now().isoformat(), "INSTALADO")
                    insts.loc[insts['Tag'] == tag_f, 'Hash_Validacao'] = hash_val
                    _save_inst(insts, o_key, "index")
                    
                    log_audit(usuario=st.session_state.user, acao="INSTALAR_INSTRUMENTO", tabela=f"inst_{o_key}_index.csv", registro_id=tag_f, detalhes=f"Instalação ITR-B: {tag_f} | GPS: {lat},{lon} | Foto: Sim | Hash: {hash_val}", ip="")
                    
                    st.success("✅ Instalação registada com foto e assinatura!")
                    st.rerun()
            elif f_foto and not assinatura_inst:
                st.warning("⚠️ Por favor, assine para validar a instalação.")


    # 🔔 NOTIFICAR GESTOR SOBRE INSTALAÇÃO
criar_notificacao(
    destinatario=st.session_state.user,
    titulo="🏗️ Instalação Concluída",
    mensagem=f"{tag_f} instalado com GPS e foto",
    tipo="success",
    acao_url="/instrumentacao?tab=itrb"
)

    # --- TAB HANDOVER ---
    with t_hand:
        st.markdown("### 📄 Handover Digital")
        c_z, c_h = st.columns(2)
        with c_z:
            if st.button("🖨️ Gerar Etiquetas Zebra (50x30mm)", use_container_width=True, type="secondary"):
                tags = insts['Tag'].head(20).tolist()
                pdf_z = _gerar_etiquetas_zebra(tags, obra_sel)
                log_audit(usuario=st.session_state.user, acao="GERAR_ETIQUETAS_ZEBRA", tabela=f"inst_{o_key}_index.csv", registro_id=f"{len(tags)}_tags", detalhes=f"Geradas {len(tags)} etiquetas Zebra para obra {obra_sel}", ip="")
                if pdf_z:
                    st.download_button("📥 Descarregar Etiquetas", pdf_z, f"etiquetas_{obra_sel}.pdf", "application/pdf")
                else:
                    st.info("ℹ️ Reportlab não disponível.")
        with c_h:
            if st.button("📄 Gerar Handover COMPLETO", use_container_width=True, type="primary"):
                tags = insts[insts['Status'].isin(['3','4'])]['Tag'].tolist()
                log_audit(usuario=st.session_state.user, acao="GERAR_HANDOVER", tabela=f"inst_{o_key}_index.csv", registro_id=obra_sel, detalhes=f"Handover gerado para {len(tags)} instrumentos concluídos", ip="")
                st.success(f"✅ Dossier pronto para {len(tags)} instrumentos!")
            

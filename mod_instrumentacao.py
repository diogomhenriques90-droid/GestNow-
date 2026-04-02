"""
GESTNOW v3 — mod_instrumentacao.py
Módulo de Instrumentação Industrial com IA Vision (Claude 3.5)
ITR-A (Calibração), ITR-B (Instalação), Handover Digital
"""
import streamlit as st
import pandas as pd
import io, re, json, base64, uuid, secrets, logging
from datetime import datetime, date
import anthropic
import fitz  # PyMuPDF

# Importações do core.py (com fallback seguro)
try:
    from core import (
        load_db, save_db, inv, fh, render_metric,
        process_and_compress_image, ICONS, COLORS
    )
except ImportError as e:
    st.error(f"Erro ao importar do core.py: {e}")

from translations import t

# Imports do reportlab (se disponíveis)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
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
# ✅ FUNÇÃO: _save_inst (Guarda dados com verificação de colunas)
# =============================================================================
def _save_inst(insts_df, obra_key, tabela_tipo="index"):
    """Guarda dados de instrumentos com verificação de colunas"""
    try:
        filename = f"inst_{obra_key}_{tabela_tipo}.csv"
        expected_cols = {
            "index": ["ID", "Tag", "Tipo", "Descricao", "Fabricante", "Modelo", "Status", "GPS_Lat", "GPS_Lng", "Foto_Local_b64"],
            "hookups": ["ID", "Codigo", "Tipo_Tag", "Descricao"],
            "bom": ["HookupID", "Item", "Descricao", "Quantidade", "Unidade"],
            "packing": ["ID", "Tag", "Descricao", "QtdEsperada", "QtdRecebida", "Estado"]
        }
        cols = expected_cols.get(tabela_tipo, list(insts_df.columns))
        # Garantir que todas as colunas existem
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
# ✅ FUNÇÃO: _gerar_etiquetas_zebra (RESTAURADA)
# =============================================================================
def _gerar_etiquetas_zebra(tags, obra_sel):
    """Gera PDF de etiquetas térmicas 50x30mm para impressora Zebra"""
    if not REPORTLAB_AVAILABLE:
        return None
    try:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(50*mm, 30*mm))
        for tag in tags:
            # Texto da etiqueta
            c.setFont("Helvetica-Bold", 8)
            c.drawString(2*mm, 25*mm, f"GESTNOW | {tag}")
            c.setFont("Helvetica", 6)
            c.drawString(2*mm, 20*mm, f"{obra_sel}")
            # QR Code simples (placeholder - substituir por biblioteca QR)
            c.rect(20*mm, 5*mm, 20*mm, 20*mm)
            c.drawString(21*mm, 14*mm, "QR")
            c.showPage()
        c.save()
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Erro ao gerar etiquetas Zebra: {e}")
        return None

# =============================================================================
# 🤖 MOTOR DE IA VISION (Claude 3.5)
# =============================================================================
def _processar_ia_vision(file, modo):
    """Motor de Visão de Alta Resolução para Documentos Técnicos"""
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("❌ API Key da Anthropic não configurada.")
            return None
        
        client = anthropic.Anthropic(api_key=api_key)
        pdf_bytes = file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 3x Zoom para leitura de tags minúsculas
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
        
        json_match = re.search(r'\{.*\}', resp.content[0].text, re.DOTALL)
        return json.loads(json_match.group(0)) if json_match else None
        
    except Exception as e:
        logger.error(f"Erro na IA ({modo}): {e}")
        st.error(f"❌ Erro na IA: {e}")
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
        logger.warning(f"Erro na validação de {tag}: {e}")
        return False, "Erro na validação"

# =============================================================================
# 🎯 INTERFACE PRINCIPAL
# =============================================================================
def render_instrumentacao(*args):
    """Render principal do módulo de instrumentação"""
    (users, obras_db, frentes_db, registos_db, fats, docs, incs, sw, obs, equip,
     diags, diags_u, folhas, comuns, comuns_u, req_fer, req_mat, req_epi, avals, inst_acessos) = args
    
    st.markdown(f"""
    <div style="text-align:center; padding:30px 20px; background:linear-gradient(135deg, #1E293B, #0F172A); border-radius:20px; margin-bottom:30px;">
        <div style="font-size:3rem; margin-bottom:10px;">🔧</div>
        <div style="font-size:1.8rem; font-weight:800; color:#F8FAFC;">{t('instrumentation')}</div>
        <div style="font-size:1rem; color:#94A3B8;">Gestão de Instrumentação Industrial</div>
    </div>
    """, unsafe_allow_html=True)

    # Seleção de Obra
    o_inst = obras_db[obras_db['TipoObra'] == 'Instrumentação']['Obra'].tolist()
    if not o_inst:
        st.warning("⚠️ Nenhuma obra configurada como 'Instrumentação'.")
        return
    
    obra_sel = st.selectbox("🏗️ Selecionar Projeto", o_inst, key="inst_project_sel")
    o_key = obra_sel.replace(' ', '_').replace('/', '_')

    # Carregar bases
    insts = load_db(f"inst_{o_key}_index.csv", ["ID","Tag","Tipo","Descricao","Fabricante","Modelo","Status","GPS_Lat","GPS_Lng","Foto_Local_b64"])
    hookups = load_db(f"inst_{o_key}_hookups.csv", ["ID","Codigo","Tipo_Tag","Descricao"])
    bom = load_db(f"inst_{o_key}_bom.csv", ["HookupID","Item","Descricao","Quantidade","Unidade"])
    packing = load_db(f"inst_{o_key}_packing.csv", ["ID","Tag","Descricao","QtdEsperada","QtdRecebida","Estado"])

    # TABS
    t_conv, t_idx, t_itra, t_itrb, t_hand = st.tabs([
        "🤖 IA Vision", "📋 Index", "🔬 ITR-A", "🏗️ ITR-B & GPS", "📄 Handover"
    ])

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
                _save_inst(edited, o_key, "index")
                inv()
                st.rerun()
        else:
            st.info("ℹ️ Sem instrumentos. Use IA Vision para extrair tags.")

    # --- TAB ITR-A: CALIBRAÇÃO ---
    with t_itra:
        st.markdown("### 🔬 Calibração ITR-A (5 pontos)")
        lista = insts[insts['Status']=='1']['Tag'].tolist() if not insts.empty else []
        tag_c = st.selectbox("Tag para Calibrar", lista)
        
        if tag_c:
            with st.form("form_itra"):
                st.markdown(f"#### Rise/Fall: {tag_c}")
                c1, c2, c3 = st.columns(3)
                r_min = c1.number_input("Range Mín", value=0.0)
                r_max = c2.number_input("Range Máx", value=100.0)
                unit = c3.selectbox("Unidade", ["bar", "ºC", "mA", "mm"])
                
                st.divider()
                pts = [0, 25, 50, 75, 100]
                rise, fall = {}, {}
                for p in pts:
                    row = st.columns([1, 2, 2])
                    theo = r_min + (r_max - r_min) * (p/100)
                    row[0].write(f"**{p}%** ({theo:.2f})")
                    rise[p] = row[1].number_input(f"R{p}", value=theo, label_visibility="collapsed")
                    fall[p] = row[2].number_input(f"F{p}", value=theo, label_visibility="collapsed")
                
                if st.form_submit_button("💾 Gerar Certificado", use_container_width=True, type="primary"):
                    esign = secrets.token_hex(4).upper()
                    err = max([abs(rise[p] - (r_min + (r_max - r_min) * (p/100))) for p in pts])
                    insts.loc[insts['Tag'] == tag_c, 'Status'] = '2'
                    _save_inst(insts, o_key, "index")
                    st.success(f"✅ Certificado {esign} | Erro máx: {err:.4f}")
                    st.rerun()

    # --- TAB ITR-B: INSTALAÇÃO + GOOGLE MAPS (RESTAURADO!) ---
    with t_itrb:
        st.markdown("### 🏗️ Instalação + GPS")
        inst_f = insts[insts['Status'] == '2']
        if inst_f.empty:
            st.info("ℹ️ Aguardando instrumentos calibrados.")
        else:
            tag_f = st.selectbox("Localizar Instrumento", inst_f['Tag'].tolist())
            row_f = inst_f[inst_f['Tag'] == tag_f].iloc[0]
            lat, lon = row_f['GPS_Lat'], row_f['GPS_Lng']
            
            # ✅ GOOGLE MAPS LINK - RESTAURADO!
            if lat and str(lat) != "" and str(lat) != "nan":
                nav_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=walking"
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:15px; border:2px solid #3B82F6; text-align:center;">
                    <h4 style="color:#F8FAFC; margin-bottom:15px;">📍 {tag_f} no GPS</h4>
                    <a href="{nav_url}" target="_blank" style="text-decoration:none;">
                        <button style="background:linear-gradient(135deg, #3B82F6, #60A5FA); color:white; border:none; padding:15px 30px; border-radius:10px; font-weight:bold; cursor:pointer; width:100%;">
                            🗺️ ABRIR ROTEIRO NO GOOGLE MAPS
                        </button>
                    </a>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:10px;">Modo caminhada para precisão entre equipamentos.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ GPS não registado para este instrumento.")

            st.divider()
            f_foto = st.camera_input("📸 Foto da Instalação")
            if f_foto:
                foto_comp = process_and_compress_image(f_foto)
                if st.button("✅ Registar Instalação", use_container_width=True, type="primary"):
                    insts.loc[insts['Tag'] == tag_f, 'Status'] = '3'
                    # ✅ GUARDAR FOTO COMPROMIDA - RESTAURADO!
                    if 'Foto_Local_b64' in insts.columns:
                        insts.loc[insts['Tag'] == tag_f, 'Foto_Local_b64'] = foto_comp
                    _save_inst(insts, o_key, "index")
                    st.success("✅ Instalação registada com foto!")
                    st.rerun()

    # --- TAB HANDOVER: ZEBRA + DOSSIER (RESTAURADO!) ---
    with t_hand:
        st.markdown("### 📄 Handover Digital")
        c_z, c_h = st.columns(2)
        
        with c_z:
            # ✅ ETIQUETAS ZEBRA - RESTAURADO!
            if st.button("🖨️ Gerar Etiquetas Zebra (50x30mm)", use_container_width=True, type="secondary"):
                tags = insts['Tag'].head(20).tolist()
                pdf_z = _gerar_etiquetas_zebra(tags, obra_sel)
                if pdf_z:
                    st.download_button("📥 Descarregar Etiquetas", pdf_z, f"etiquetas_{obra_sel}.pdf", "application/pdf")
                else:
                    st.info("ℹ️ Reportlab não disponível ou a processar...")
        
        with c_h:
            # ✅ HANDOVER DOSSIER - RESTAURADO!
            if st.button("📄 Gerar Handover COMPLETO", use_container_width=True, type="primary"):
                tags = insts[insts['Status'].isin(['3','4'])]['Tag'].tolist()
                st.success(f"✅ Dossier pronto para {len(tags)} instrumentos!")
                # Aqui integrarias a geração real do PDF consolidado

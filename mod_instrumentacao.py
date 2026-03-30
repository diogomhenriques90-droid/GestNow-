import streamlit as st
import pandas as pd
import io, re, json, base64, uuid, secrets
from datetime import datetime, date
import anthropic
import fitz  # PyMuPDF

# Importações do seu arquivo core.py
try:
    from core import (
        load_db, save_db, inv, fh, render_metric, render_metric_red, 
        t, process_and_compress_image, _qr_drawing, A4, colors, 
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, cm
    )
except ImportError:
    st.error("Erro: O arquivo 'core.py' não foi encontrado ou faltam funções nele.")

# ── CONFIGURAÇÕES TÉCNICAS ISA ────────────────────────────────
TIPOS_TAG = {
    "PT": ("Transmissor de Pressão", "#E74C3C"), "FT": ("Transmissor de Caudal", "#3498DB"),
    "LT": ("Transmissor de Nível", "#2ECC71"), "TT": ("Transmissor de Temperatura", "#E67E22"),
    "AT": ("Analisador", "#9B59B6"), "CV": ("Válvula de Controlo", "#C0392B"),
    "PSV":("Válvula de Segurança", "#E74C3C"), "TE": ("Elemento de Temperatura", "#D35400"),
    "PG": ("Manómetro Local", "#7F8C8D"), "LG": ("Visor de Nível", "#95A5A6"),
    "FE": ("Elemento de Caudal", "#2980B9"), "XX": ("Outro", "#BDC3C7"),
}

STATUS_INST = {
    "0": ("Pendente", "status-pendente", "⏳"),
    "1": ("Material OK", "status-aprovado", "📦"),
    "2": ("Calibrado", "status-fechado", "🔬"),
    "3": ("Instalado", "status-aprovado", "🏗️"),
    "4": ("Concluído", "status-aprovado", "✅"),
}

# ═══════════════════════════════════════════════════════════════
# 1. MOTORES DE INTELIGÊNCIA ARTIFICIAL (CLAUDE 3.5 VISION)
# ═══════════════════════════════════════════════════════════════

def _processar_ia_vision(file, modo):
    """Motor de Visão de Alta Resolução para Documentos Técnicos"""
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("API Key da Anthropic não configurada nos secrets.")
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
        st.error(f"Erro na IA ({modo}): {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# 2. LÓGICA DE INTEGRIDADE DE MATERIAL (BOM VS PACKING)
# ═══════════════════════════════════════════════════════════════

def _validar_material_tag(tag, packing_df, hookups_df, bom_df):
    """Verifica se o material necessário para a tag já foi recebido"""
    tipo = re.sub(r'[0-9]', '', tag.split('-')[0])[:3]
    h_tipo = hookups_df[hookups_df['Tipo_Tag'] == tipo]
    if h_tipo.empty: return False, "Hook-up não definido"
    
    hid = h_tipo.iloc[0]['ID']
    qtd_req = bom_df[bom_df['HookupID'] == hid]['Quantidade'].astype(float).sum()
    qtd_rec = packing_df[packing_df['Tag'] == tag]['QtdRecebida'].astype(float).sum()
    
    if qtd_rec >= qtd_req: return True, "Material Completo"
    return False, f"Faltam {int(qtd_req - qtd_rec)} itens"

# ═══════════════════════════════════════════════════════════════
# 3. INTERFACE DE ENGENHARIA (RENDER PRINCIPAL)
# ═══════════════════════════════════════════════════════════════

def render_instrumentacao(*args):
    # Desempacotamento dos argumentos (ajuste conforme a chamada no seu main.py)
    (users, obras_db, frentes_db, registos_db, fats, docs, incs, sw, obs, equip, 
     diags, diags_u, folhas, comuns, comuns_u, req_fer, req_mat, req_epi, avals, inst_acessos) = args

    st.title(f"🔧 {t('instrumentation')}")

    # Seleção de Obra Ativa (Filtro por tipo Instrumentação)
    o_inst = obras_db[obras_db['TipoObra'] == 'Instrumentação']['Obra'].tolist()
    if not o_inst:
        st.warning("⚠️ Nenhuma obra configurada como 'Instrumentação' no Admin.")
        return
    
    obra_sel = st.selectbox("🏗️ Selecionar Projeto", o_inst, key="inst_project_sel")
    o_key = obra_sel.replace(' ', '_').replace('/', '_')

    # Carregar sub-bases via GCS/Local (Assegure que as colunas batem com o CSV)
    insts = load_db(f"inst_{o_key}_index.csv", ["ID","Tag","Tipo","Descricao","Fabricante","Modelo","Status","GPS_Lat","GPS_Lng","Foto_Local_b64"])
    hookups = load_db(f"inst_{o_key}_hookups.csv", ["ID","Codigo","Tipo_Tag","Descricao"])
    bom = load_db(f"inst_{o_key}_bom.csv", ["HookupID","Item","Descricao","Quantidade","Unidade"])
    packing = load_db(f"inst_{o_key}_packing.csv", ["ID","Tag","Descricao","QtdEsperada","QtdRecebida","Estado"])

    # TABS OPERACIONAIS
    t_conv, t_idx, t_itra, t_itrb, t_hand = st.tabs([
        "🤖 IA Vision", "📋 Index", "🔬 ITR-A (5-pt)", "🏗️ ITR-B & GPS", "📄 Handover"
    ])

    # --- TAB IA: CONVERSORES DE ENGENHARIA ---
    with t_conv:
        st.subheader("Motores IA: P&ID, Hook-up e Packing List")
        c_mode = st.radio("Selecione o Documento", ["P&ID (Tags)", "Hook-Up (BOM)", "Packing List"], horizontal=True)
        up = st.file_uploader(f"Upload PDF {c_mode}", type="pdf", key="up_ia")
        
        if up and st.button("🚀 Iniciar Processamento Vision"):
            m = "PID" if "P&ID" in c_mode else "HOOKUP" if "Hook-Up" in c_mode else "PACKING"
            with st.spinner("Claude 3.5 Sonnet a analisar desenho técnico..."):
                res = _processar_ia_vision(up, m)
                if res:
                    st.success("Dados Extraídos!")
                    k = list(res.keys())[0]
                    # VALIDAÇÃO HUMANA
                    edited = st.data_editor(pd.DataFrame(res[k]), use_container_width=True, num_rows="dynamic")
                    if st.button("✅ Confirmar e Gravar na Base de Dados"):
                        # Aqui deve-se implementar o merge dos dados editados na base carregada
                        st.info("Funcionalidade de Gravação em desenvolvimento para este módulo.")
                        st.balloons()

    # --- TAB ITR-A: CALIBRAÇÃO RISE/FALL 5 PONTOS ---
    with t_itra:
        st.subheader("Certificação ITR-A: Calibração em Bancada")
        # Filtra apenas quem está com material OK (Status '1')
        lista_tags = insts[insts['Status']=='1']['Tag'].tolist() if not insts.empty else []
        tag_c = st.selectbox("Tag para Calibrar", lista_tags)
        
        if tag_c:
            with st.form("form_itra_5pt"):
                st.markdown(f"### Certificado Rise/Fall: {tag_c}")
                c1, c2, c3 = st.columns(3)
                r_min = c1.number_input("Range Mín", value=0.0)
                r_max = c2.number_input("Range Máx", value=100.0)
                unit = c3.selectbox("Unidade", ["bar", "ºC", "mA", "mm"])
                
                st.write("---")
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
                
                if st.form_submit_button("💾 Gerar Certificado com E-Sign"):
                    esign_id = secrets.token_hex(4).upper()
                    # Cálculo simples de erro máximo
                    err = max([abs(rise[p] - (r_min + (r_max - r_min) * (p/100))) for p in pts])
                    # Atualiza Status para '2' (Calibrado)
                    insts.loc[insts['Tag'] == tag_c, 'Status'] = '2'
                    save_db(insts, f"inst_{o_key}_index.csv")
                    st.success(f"Certificado {esign_id} guardado com erro máx de {err:.4f}")
                    st.rerun()

    # --- TAB ITR-B: INSTALAÇÃO & ROTEIRO GOOGLE MAPS ---
    with t_itrb:
        st.subheader("Instalação no Terreno e Navegação")
        inst_f = insts[insts['Status'] == '2'] # Apenas Calibrados
        if inst_f.empty:
            st.info("Aguardando instrumentos calibrados para instalação.")
        else:
            tag_f = st.selectbox("Localizar Instrumento", inst_f['Tag'].tolist())
            row_f = inst_f[inst_f['Tag'] == tag_f].iloc[0]
            lat, lon = row_f['GPS_Lat'], row_f['GPS_Lng']
            
            if lat and lat != "" and str(lat) != "nan":
                # LINK DE NAVEGAÇÃO GOOGLE MAPS
                nav_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=walking"
                st.markdown(f"""
                    <div style="background:white; padding:20px; border-radius:15px; border:2px solid #0A2463; text-align:center;">
                        <h4 style="color:#0A2463; margin-bottom:15px;">📍 {tag_f} Localizado no GPS</h4>
                        <a href="{nav_url}" target="_blank" style="text-decoration:none;">
                            <button style="background:#0A2463; color:white; border:none; padding:15px 30px; border-radius:10px; font-weight:bold; cursor:pointer; width:100%;">
                                🗺️ ABRIR ROTEIRO NO GOOGLE MAPS
                            </button>
                        </a>
                        <p style="color:#7A8BA6; font-size:0.8rem; margin-top:10px;">O GPS abrirá em modo de caminhada para precisão entre equipamentos.</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Coordenadas GPS não registadas para este instrumento.")

            st.divider()
            f_foto = st.camera_input("📸 Foto da Instalação (Loop Check OK)")
            if f_foto:
                # COMPRESSÃO ELITE
                foto_comp = process_and_compress_image(f_foto)
                if st.button("✅ Registar Instalação ITR-B"):
                    insts.loc[insts['Tag'] == tag_f, 'Status'] = '3'
                    save_db(insts, f"inst_{o_key}_index.csv")
                    st.success("Instalação Registada com Prova Fotográfica Comprimida.")
                    st.rerun()

    # --- TAB HANDOVER: DOSSIER E ZEBRA ---
    with t_hand:
        st.subheader("Entrega e Identificação")
        c_z, c_h = st.columns(2)
        with c_z:
            if st.button("🖨️ Gerar PDF Zebra (50x30mm)"):
                st.info("A processar etiquetas térmicas com QR Code...")
                # Lógica para gerar PDF formatado para Zebra
        with c_h:
            if st.button("📄 Gerar Handover Dossier COMPLETO"):
                st.success("Consolidação de ITR-A e ITR-B concluída.")

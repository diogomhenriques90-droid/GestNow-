"""
GESTNOW v3 — mod_instrumentacao.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Módulo de Gestão de Instrumentação Industrial

Fluxo: P&ID → Hook-Ups → Packing List → Calibração (ITR-A)
       → Instalação+GPS (ITR-B) → Punch List → Handover Dossier

NOVIDADE: Extracção de tags por Claude Vision API
  → Lê qualquer P&ID (vectorial, CAD, escaneado)
  → Devolve JSON estruturado com todas as tags ISA
  → Sem OCR clássico, sem regex, sem falhas

requirements.txt:
  pymupdf      ← converter PDF → imagem
  anthropic    ← Claude Vision API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
# Imports seguros — não re-executa set_page_config
import streamlit as st
import pandas as pd
import io, re, uuid as _uuid_inst
from datetime import datetime, timedelta, date

# Importar funções do core que são usadas fora do render principal
try:
    from core import load_db, save_db, inv, fh, sl, render_metric, render_metric_red
    from core import _qr_drawing, gerar_folha_ponto_pdf
    from core import A4, colors, SimpleDocTemplate, Table, TableStyle
    from core import Paragraph, Spacer, getSampleStyleSheet, ParagraphStyle, cm
    from core import TIPOS_FRENTE, CARGOS
except Exception:
    pass  # Serão importados novamente dentro do render_instrumentacao

# ── Tipos ISA standard + cores de identificação ──────────────
TIPOS_TAG = {
    "PT": ("Transmissor de Pressão",     "#E74C3C"),
    "FT": ("Transmissor de Caudal",      "#3498DB"),
    "LT": ("Transmissor de Nível",       "#2ECC71"),
    "TT": ("Transmissor de Temperatura", "#E67E22"),
    "AT": ("Analisador",                 "#9B59B6"),
    "DT": ("Transmissor de Densidade",   "#1ABC9C"),
    "IT": ("Transmissor de Corrente",    "#F39C12"),
    "ST": ("Transmissor de Velocidade",  "#27AE60"),
    "ZT": ("Posicionador",               "#8E44AD"),
    "CV": ("Válvula de Controlo",        "#C0392B"),
    "PSV":("Válvula de Segurança",       "#E74C3C"),
    "TE": ("Elemento de Temperatura",    "#D35400"),
    "PG": ("Manómetro Local",            "#7F8C8D"),
    "LG": ("Visor de Nível",             "#95A5A6"),
    "FE": ("Elemento de Caudal",         "#2980B9"),
    "XX": ("Outro",                      "#BDC3C7"),
}

STATUS_INST = {
    "0": ("Pendente",     "status-pendente",  "⏳"),
    "1": ("Material OK",  "status-aprovado",  "📦"),
    "2": ("Calibrado",    "status-fechado",   "🔬"),
    "3": ("Instalado",    "status-aprovado",  "🏗️"),
    "4": ("Concluído",    "status-aprovado",  "✅"),
    "X": ("Bloqueado",    "status-vencida",   "🔴"),
}

# ── Claude Vision — Extracção de Tags de P&ID ────────────────
def _extrair_tags_claude_vision(pdf_file, nome_ficheiro):
    """
    Usa Claude Vision para extrair tags ISA de um P&ID.
    Funciona em qualquer formato: vectorial CAD, escaneado, imagem.
    Retorna lista de dicts: [{"tag": "PT-101", "tipo": "PT", "descricao": "...", "linha": "..."}]
    """
    import base64, json, urllib.request
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "❌ PyMuPDF não instalado. Adiciona 'pymupdf' ao requirements.txt"

    try:
        # Converter primeira página do PDF em imagem PNG alta resolução
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)  # reset para leituras futuras

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs_b64 = []
        for page_num in range(min(len(doc), 3)):  # máx 3 páginas por P&ID
            page = doc[page_num]
            # 3x zoom para alta resolução — tags pequenas ficam legíveis
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            imgs_b64.append(base64.standard_b64encode(img_bytes).decode())

        doc.close()

        # Construir payload para Claude Vision
        content = []
        for i, img_b64 in enumerate(imgs_b64):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64
                }
            })

        prompt = """Analisa este P&ID (Piping and Instrumentation Diagram) industrial.

Extrai TODAS as tags de instrumentação presentes no desenho.

Tags de instrumentação seguem a norma ISA 5.1:
- Formato típico: XX-NNNN (ex: PT-101, FT-1234, LT-001A)
- Também podem ter prefixo de área: 3075-PT-101
- Tipos comuns: PT, FT, LT, TT, AT, CV, PSV, TE, PG, LG, FE, ZT, ST, IT, DT, PIC, FIC, LIC, TIC, FCV, PCV, LCV

Para cada tag encontrada, indica:
1. Tag completa (ex: PT-101)
2. Tipo de instrumento (as 2-3 letras do tipo: PT, FT, etc.)
3. Descrição em português (ex: Transmissor de Pressão)
4. Linha de processo associada se visível (ex: 3075-CS-001)

Responde APENAS em JSON válido, sem markdown, sem explicações:
{
  "tags": [
    {"tag": "PT-101", "tipo": "PT", "descricao": "Transmissor de Pressão", "linha": "3075-CW-001"},
    {"tag": "FT-202", "tipo": "FT", "descricao": "Transmissor de Caudal", "linha": ""}
  ]
}

Se não encontrares tags, responde: {"tags": []}
"""
        content.append({"type": "text", "text": prompt})

        # Chamada à API Claude
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": content}]
        }).encode("utf-8")

        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return "❌ ANTHROPIC_API_KEY não configurada. Adiciona nas variáveis de ambiente do Cloud Run."

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": api_key,
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

        # Extrair o JSON da resposta
        resposta_texto = result["content"][0]["text"].strip()
        # Limpar possível markdown
        resposta_texto = resposta_texto.replace("```json","").replace("```","").strip()
        dados = json.loads(resposta_texto)
        tags = dados.get("tags", [])

        # Normalizar e enriquecer com descrições do dicionário local
        for t in tags:
            tipo = t.get("tipo","XX")[:3].upper()
            if tipo not in TIPOS_TAG:
                # Tentar extrair tipo da tag
                m = re.match(r"([A-Z]{1,3})", t.get("tag",""))
                if m: tipo = m.group(1)
            t["tipo"] = tipo
            if not t.get("descricao"):
                t["descricao"] = TIPOS_TAG.get(tipo, ("Instrumento",""))[0]

        return tags

    except Exception as e:
        return f"Erro na análise IA: {str(e)}"


def _importar_tags(tags_lista, insts_df, obra_sel, obra_key, pid_ref):
    """Importa lista de tags para o Instrument Index."""
    tags_existentes = insts_df["Tag"].tolist() if not insts_df.empty else []
    novas = []
    for t in tags_lista:
        tag = t.get("tag","")
        if not tag or tag in tags_existentes:
            continue
        tipo = t.get("tipo","XX")
        desc = t.get("descricao","") or TIPOS_TAG.get(tipo, ("Instrumento",""))[0]
        novas.append({
            "ID": "INST"+_uuid_inst.uuid4().hex[:8].upper(),
            "Tag": tag,
            "Tipo": tipo,
            "Descricao": desc,
            "Fabricante": "",
            "Modelo": "",
            "PID_Ref": pid_ref,
            "LinhaProcesso": t.get("linha",""),
            "Obra": obra_sel,
            "Unidade": "",
            "Status": "0",
            "GPS_Lat": "", "GPS_Lng": "", "Elevacao": "",
            "Foto_Local_b64": "",
            "DataCriacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "QR_impresso": "0",
        })
    if novas:
        novo_df = pd.DataFrame(novas)
        upd = pd.concat([insts_df, novo_df], ignore_index=True)
        _save_inst(upd, obra_key, "index")
        inv()
        st.success(f"✅ {len(novas)} tags importadas para o Instrument Index!")
    else:
        st.info("ℹ️ Todas as tags já existem.")


# ── Carregamento dos CSVs próprios deste módulo ───────────────
def _load_inst(obra):
    """Carrega todos os CSVs de instrumentação para uma obra."""
    insts   = load_db(f"inst_{obra}_index.csv",
        ["ID","Tag","Tipo","Descricao","Fabricante","Modelo","PID_Ref",
         "LinhaProcesso","Obra","Unidade","Status","GPS_Lat","GPS_Lng","Elevacao",
         "Foto_Local_b64","DataCriacao","QR_impresso"])
    hookups = load_db(f"inst_{obra}_hookups.csv",
        ["ID","Obra","Codigo","Tipo_Tag","Descricao","DataCriacao"])
    bom     = load_db(f"inst_{obra}_bom.csv",
        ["HookupID","Item","Descricao","Quantidade","Unidade","Especificacao"])
    packing = load_db(f"inst_{obra}_packing.csv",
        ["ID","Obra","Tag","Item","Descricao",
         "QtdEsperada","QtdRecebida","Estado","DataRecepcao","Observacao"])
    itr_a   = load_db(f"inst_{obra}_itr_a.csv",
        ["ID","Tag","Obra","Instrumentista","DataCalibracao",
         "RangeMin","RangeMax","Unidade","SetPoint","ResultadoReal",
         "Desvio","PassFail","Observacoes","Assinatura_b64"])
    itr_b   = load_db(f"inst_{obra}_itr_b.csv",
        ["ID","Tag","Obra","Tecnico","DataInstalacao",
         "GPS_Lat","GPS_Lng","Elevacao","Foto_b64",
         "LoopCheck","Observacoes","Assinatura_b64"])
    punch   = load_db(f"inst_{obra}_punch.csv",
        ["ID","Tag","Obra","Categoria","Descricao",
         "Responsavel","Prazo","Status","DataCriacao","DataFecho"])
    return insts, hookups, bom, packing, itr_a, itr_b, punch

def _save_inst(df, obra, nome):
    save_db(df, f"inst_{obra}_{nome}.csv")


# ── CSS do módulo ─────────────────────────────────────────────
_CSS_INST = """
<style>
.inst-header{background:linear-gradient(135deg,#0A2463 0%,#1A3A6A 60%,#C0392B 100%);
  border-radius:18px;padding:20px 24px;color:white;margin-bottom:20px;
  box-shadow:0 8px 32px rgba(10,36,99,.3);}
.inst-header h2{margin:0;font-size:1.4rem;font-weight:800;}
.inst-header p{margin:4px 0 0;opacity:.75;font-size:.85rem;}

.inst-tag-card{background:white;border-radius:14px;padding:14px 16px;
  margin-bottom:10px;border:1px solid #E5EDFF;
  box-shadow:0 2px 8px rgba(10,36,99,.05);
  display:flex;align-items:center;gap:14px;}
.inst-tag-badge{border-radius:10px;padding:6px 12px;font-weight:800;
  font-size:.85rem;color:white;min-width:60px;text-align:center;flex-shrink:0;}
.inst-tag-desc{flex:1;}
.inst-tag-desc .tag-nome{font-weight:700;color:#1A1A2E;font-size:.95rem;}
.inst-tag-desc .tag-sub{color:#7A8BA6;font-size:.78rem;margin-top:2px;}

.inst-semaforo{display:inline-flex;align-items:center;gap:6px;
  padding:4px 12px;border-radius:20px;font-size:.75rem;font-weight:700;}
.sem-verde{background:#D1FAE5;color:#065F46;}
.sem-amarelo{background:#FEF3C7;color:#92400E;}
.sem-vermelho{background:#FEE2E2;color:#991B1B;}
.sem-cinza{background:#F3F4F6;color:#6B7280;}

.phase-bar{display:flex;gap:4px;margin-bottom:20px;overflow-x:auto;padding-bottom:4px;}
.phase-step{flex:1;min-width:80px;text-align:center;padding:8px 4px;
  border-radius:10px;font-size:.7rem;font-weight:600;border:1.5px solid transparent;}
.phase-done{background:#D1FAE5;color:#065F46;border-color:#6EE7B7;}
.phase-active{background:linear-gradient(135deg,#0A2463,#3E92CC);color:white;}
.phase-pending{background:#F9FAFB;color:#9CA3AF;border-color:#E5E7EB;}

.itr-card{background:white;border-radius:14px;padding:16px;
  margin-bottom:10px;border-left:4px solid #3E92CC;
  box-shadow:0 2px 8px rgba(10,36,99,.06);}
.itr-card.pass{border-left-color:#10B981;}
.itr-card.fail{border-left-color:#EF4444;}

.punch-card{background:white;border-radius:12px;padding:14px 16px;
  margin-bottom:8px;border:1px solid #E5EDFF;}
.punch-a{border-left:4px solid #EF4444;}
.punch-b{border-left:4px solid #F59E0B;}
.punch-c{border-left:4px solid #6B7280;}

.stat-pill{display:inline-block;padding:3px 10px;border-radius:12px;
  font-size:.72rem;font-weight:700;margin-left:6px;}
</style>
"""


# ═══════════════════════════════════════════════════════════════
# RENDER PRINCIPAL
# ═══════════════════════════════════════════════════════════════
def render_instrumentacao(**DB):
    # Core já importado no topo do módulo

    inst_acessos_db = DB.get("inst_acessos_db", pd.DataFrame())
    st.markdown(_CSS_INST, unsafe_allow_html=True)

    users    = DB.get('users', pd.DataFrame())
    obras_db = DB.get('obras_db', pd.DataFrame())

    # ── Selecção de obra ──────────────────────────────────────
    obras_lista = obras_db[obras_db['Ativa'].isin(
        ['Ativa','ativa','Sim','sim','true','True','1']
    )]['Obra'].tolist() if not obras_db.empty else []

    # ── Determinar cargo do utilizador nesta sessão ────────────
    user_atual  = st.session_state.get('user','')
    cargo_atual = st.session_state.get('cargo','')
    tipo_atual  = st.session_state.get('tipo','')

    # Cargo na instrumentação (pode ser diferente do cargo geral)
    cargo_inst = ""
    if not inst_acessos_db.empty:
        acesso_row = inst_acessos_db[
            inst_acessos_db['Utilizador'] == user_atual
        ]
        if not acesso_row.empty:
            cargo_inst = str(acesso_row.iloc[0].get('Cargo',''))

    # Nível de acesso: admin > chefe > tecnico
    is_admin_inst  = tipo_atual == "Admin"
    is_chefe_inst  = cargo_inst in ['Chefe de Equipa','Supervisor'] or                      cargo_atual in ['Chefe de Equipa','Encarregado','Supervisor']
    is_instr_inst  = cargo_inst == 'Instrumentista'
    # Técnico de campo ou instrumentista veem as mesmas tabs operacionais

    if not obras_lista:
        st.warning("⚠️ Sem obras ativas. Cria uma obra primeiro no módulo Admin.")
        return

    # Filtrar obras por acesso (técnicos só vêem as suas obras)
    if is_admin_inst:
        obras_filtradas = obras_lista
    else:
        obras_com_acesso = inst_acessos_db[
            (inst_acessos_db['Utilizador'] == user_atual) &
            (inst_acessos_db['Ativo'].isin(['Sim','sim','1','true','True']))
        ]['Obra'].tolist() if not inst_acessos_db.empty else []
        obras_filtradas = [o for o in obras_lista if o in obras_com_acesso]
        if not obras_filtradas:
            st.warning("⚠️ Não tens acesso a nenhuma obra de instrumentação. "
                "Pede ao administrador para te adicionar.")
            return

    col_ob, col_info = st.columns([3,1])
    with col_ob:
        obra_sel = st.selectbox("🏗️ Obra de Instrumentação", obras_filtradas,
            key="inst_obra_sel")
    obra_cod = ""
    if not obras_db.empty and obra_sel in obras_db['Obra'].values:
        obra_cod = obras_db[obras_db['Obra']==obra_sel].iloc[0].get('Codigo','')
    with col_info:
        st.markdown(f"<div style='padding:10px;background:#EEF2FF;border-radius:10px;"
            f"text-align:center;margin-top:28px;font-size:.8rem;color:#4F46E5;font-weight:700;'>"
            f"🔖 {obra_cod or 'S/código'}</div>", unsafe_allow_html=True)

    # ── Carregar dados da obra ────────────────────────────────
    obra_key = obra_sel.replace(' ','_').replace('/','_')
    insts, hookups, bom, packing, itr_a, itr_b, punch = _load_inst(obra_key)

    # ── Estatísticas rápidas ──────────────────────────────────
    n_total  = len(insts)
    n_mat_ok = len(insts[insts['Status'].isin(['1','2','3','4'])]) if not insts.empty else 0
    n_cal    = len(insts[insts['Status'].isin(['2','3','4'])]) if not insts.empty else 0
    n_inst   = len(insts[insts['Status'].isin(['3','4'])]) if not insts.empty else 0
    n_punch_a= len(punch[(punch['Categoria']=='A')&(punch['Status']=='Aberto')]) if not punch.empty else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: render_metric("📋", n_total,  "Instrumentos")
    with c2: render_metric("📦", n_mat_ok, "Material OK")
    with c3: render_metric("🔬", n_cal,    "Calibrados")
    with c4: render_metric("🏗️", n_inst,   "Instalados")
    with c5: render_metric_red("⚠️", n_punch_a, "Punch Cat.A")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────
    # ── Tabs filtradas por cargo ────────────────────────────────
    if is_admin_inst or is_chefe_inst:
        # Admin e Chefe — acesso total
        tab1,tab2,tab3,tab4,tab5,tab6,tab7 = st.tabs([
            "📋 Instrument Index",
            "🔩 Hook-Ups & BOM",
            "📦 Packing List",
            "🔬 Calibração ITR-A",
            "🏗️ Instalação ITR-B",
            "⚠️ Punch List",
            "📄 Handover",
        ])
        tab2_visivel = True
        tab3_visivel = True
        tab6_visivel = True
        tab7_visivel = True
    else:
        # Técnico / Instrumentista — só tabs operacionais
        tab1,tab4,tab5 = st.tabs([
            "📋 Os Meus Instrumentos",
            "🔬 Calibração ITR-A",
            "🏗️ Instalação ITR-B",
        ])
        tab2 = None; tab3 = None; tab6 = None; tab7 = None
        tab2_visivel = False
        tab3_visivel = False
        tab6_visivel = False
        tab7_visivel = False

    # ══════════════════════════════════════════════════════════
    # TAB 1 — INSTRUMENT INDEX
    # ══════════════════════════════════════════════════════════
    with tab1:
        st.markdown('<div class="section-title">📋 Instrument Index</div>',
            unsafe_allow_html=True)

        sub_pid, sub_manual, sub_lista, sub_etiquetas = st.tabs([
            "📄 Extrair de P&ID",
            "✏️ Adicionar Manual",
            "📊 Lista Completa",
            "🏷️ Etiquetas QR",
        ])

        # ── Sub: Extrair de P&ID — Claude Vision ─────────────────
        with sub_pid:
            st.markdown("""
            <div style='background:linear-gradient(135deg,#0A2463,#1A3A6A);border-radius:16px;
            padding:18px 20px;color:white;margin-bottom:16px;'>
            <div style='font-size:1.2rem;font-weight:800;margin-bottom:4px;'>
            🤖 Extracção Automática com IA</div>
            <div style='opacity:.8;font-size:.85rem;'>Claude Vision analisa o P&ID e extrai todas
            as tags ISA automaticamente — funciona em qualquer formato de PDF, incluindo CAD vectorial.</div>
            </div>""", unsafe_allow_html=True)

            pid_file = st.file_uploader("📄 Upload do P&ID (PDF)",
                type=["pdf"], key="inst_pid_upload")

            if pid_file:
                col_btn, col_info = st.columns([2,3])
                with col_btn:
                    analisar = st.button("🤖 Analisar com IA",
                        use_container_width=True, type="primary",
                        key="inst_analisar_ia")
                with col_info:
                    st.caption(f"📄 {pid_file.name} — {pid_file.size/1024:.0f} KB")

                if analisar or st.session_state.get("pid_tags_cache_key") == pid_file.name:

                    # Verificar cache — não re-analisar o mesmo ficheiro
                    cache_key = f"pid_tags_{obra_key}_{pid_file.name}"
                    tags_cache = st.session_state.get(cache_key)

                    if not tags_cache or analisar:
                        with st.spinner("🤖 A analisar P&ID com Claude Vision... (pode demorar 10-20 segundos)"):
                            tags_cache = _extrair_tags_claude_vision(pid_file, pid_file.name)
                            if tags_cache:
                                st.session_state[cache_key] = tags_cache
                                st.session_state["pid_tags_cache_key"] = pid_file.name

                    if tags_cache and "erro" not in str(tags_cache).lower()[:20]:
                        tags_unicas = tags_cache
                        tags_existentes = insts["Tag"].tolist() if not insts.empty else []
                        novas_count = len([t for t in tags_unicas if t["tag"] not in tags

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

# ═══════════════════════════════════════════════════════════════
# FUNÇÕES DE EXTRAÇÃO COM CLAUDE VISION
# ═══════════════════════════════════════════════════════════════

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


def _extrair_bom_hookup_claude(pdf_file, nome_ficheiro):
    """
    Usa Claude Vision para extrair BOM (Bill of Materials) de um Hook-Up PDF.
    Retorna lista de itens: [{"item": "1", "descricao": "...", "quantidade": 1, "unidade": "un"}]
    """
    import base64, json, urllib.request
    try:
        import fitz
    except ImportError:
        return "❌ PyMuPDF não instalado"

    try:
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs_b64 = []
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            imgs_b64.append(base64.standard_b64encode(img_bytes).decode())
        doc.close()

        content = []
        for img_b64 in imgs_b64:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img_b64}
            })

        prompt = """Analisa este desenho de Hook-Up de instrumentação industrial.

Extrai a lista de materiais (BOM - Bill of Materials) presente no desenho.
A BOM geralmente está numa tabela com:
- Item (número)
- Descrição do material
- Quantidade
- Unidade (ex: un, m, kg, etc.)

Responde APENAS em JSON válido:
{
  "bom": [
    {"item": "1", "descricao": "Válvula de bloco 1/2\" SS", "quantidade": 1, "unidade": "un"},
    {"item": "2", "descricao": "Tubo 1/2\" x 3m", "quantidade": 3, "unidade": "m"},
    {"item": "3", "descricao": "Porca de pressão", "quantidade": 2, "unidade": "un"}
  ]
}

Se não encontrares BOM, responde: {"bom": []}
"""
        content.append({"type": "text", "text": prompt})

        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "❌ ANTHROPIC_API_KEY não configurada"

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": content}]
        }).encode("utf-8")

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

        resposta_texto = result["content"][0]["text"].strip()
        resposta_texto = resposta_texto.replace("```json", "").replace("```", "").strip()
        dados = json.loads(resposta_texto)
        return dados.get("bom", [])

    except Exception as e:
        return f"Erro: {str(e)}"


def _extrair_packing_list_claude(pdf_file, nome_ficheiro):
    """
    Usa Claude Vision para extrair itens de um Packing List.
    Retorna lista de dicts: [{"tag": "PT-101", "descricao": "...", "quantidade": 1, "observacao": "..."}]
    """
    import base64, json, urllib.request
    try:
        import fitz
    except ImportError:
        return "❌ PyMuPDF não instalado"

    try:
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs_b64 = []
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            imgs_b64.append(base64.standard_b64encode(img_bytes).decode())
        doc.close()

        content = []
        for img_b64 in imgs_b64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64
                }
            })

        prompt = """Analisa este Packing List (lista de materiais) de um projeto industrial.

Extrai TODOS os itens listados, incluindo:
1. Tag do instrumento associado (se houver, ex: PT-101, FT-202, LT-001)
2. Descrição do material (ex: "Transmissor de Pressão", "Válvula 1/2" SS")
3. Quantidade
4. Observações (ex: "urgente", "substituir por...")

O Packing List pode ser:
- Uma tabela com colunas: Tag, Descrição, Qtd
- Uma lista numerada
- Um texto corrido com itens

Para cada item, responde APENAS em JSON válido:
{
  "itens": [
    {"tag": "PT-101", "descricao": "Transmissor de Pressão", "quantidade": 2, "observacao": ""},
    {"tag": "", "descricao": "Cabo 2x1.5mm", "quantidade": 100, "observacao": "metros"},
    {"tag": "FT-202", "descricao": "Transmissor de Caudal", "quantidade": 1, "observacao": "urgente"}
  ]
}

Se não encontrares itens, responde: {"itens": []}
"""
        content.append({"type": "text", "text": prompt})

        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "❌ ANTHROPIC_API_KEY não configurada"

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": content}]
        }).encode("utf-8")

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

        resposta_texto = result["content"][0]["text"].strip()
        resposta_texto = resposta_texto.replace("```json", "").replace("```", "").strip()
        dados = json.loads(resposta_texto)
        itens = dados.get("itens", [])
        
        for item in itens:
            if "tag" not in item:
                item["tag"] = ""
            if "quantidade" in item:
                try:
                    item["quantidade"] = float(item["quantidade"])
                except:
                    item["quantidade"] = 1
            else:
                item["quantidade"] = 1
            if "observacao" not in item:
                item["observacao"] = ""

        return itens

    except Exception as e:
        return f"Erro na análise IA: {str(e)}"


def _check_material_completo(tag, packing, bom, hookups):
    """
    Verifica se o material de um instrumento está completo
    comparando BOM do Hook-Up com Packing List recebido
    """
    if packing.empty:
        return False, "Sem packing list"
    
    if bom.empty:
        return False, "Sem BOM definida"
    
    # Encontrar Hook-Up para este tipo de instrumento
    tipo = tag.split('-')[0] if '-' in tag else tag[:2]
    # Remover números do tipo (ex: PT-101 -> PT)
    tipo = re.sub(r'[0-9]', '', tipo)[:3]
    
    hookups_tipo = hookups[hookups['Tipo_Tag'] == tipo] if not hookups.empty else pd.DataFrame()
    
    if hookups_tipo.empty:
        return False, f"Sem Hook-Up para tipo {tipo}"
    
    # Pegar BOM dos Hook-Ups deste tipo
    bom_ids = hookups_tipo['ID'].tolist()
    bom_total = bom[bom['HookupID'].isin(bom_ids)] if not bom.empty else pd.DataFrame()
    
    # Pegar packing list para esta tag
    packing_tag = packing[packing['Tag'] == tag] if not packing.empty else pd.DataFrame()
    
    if bom_total.empty:
        return False, "BOM vazia"
    
    if packing_tag.empty:
        return False, "Nada recebido no packing list"
    
    # Comparar quantidades
    total_esperado = bom_total['Quantidade'].sum() if not bom_total.empty else 0
    total_recebido = packing_tag[packing_tag['Estado'] == 'Recebido OK']['QtdRecebida'].sum() if not packing_tag.empty else 0
    
    if total_recebido >= total_esperado:
        return True, "Material completo"
    else:
        return False, f"Faltam {int(total_esperado - total_recebido)} itens"


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
    is_admin_inst = tipo_atual == "Admin"
    is_chefe_inst = (cargo_inst in ['Chefe de Equipa', 'Supervisor']) or \
                    (cargo_atual in ['Chefe de Equipa', 'Encarregado', 'Supervisor']) or \
                    (tipo_atual == 'Chefe de Equipa')
    is_instr_inst = cargo_inst == 'Instrumentista'

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
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
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
        tab_inst, tab_cal, tab_instal = st.tabs([
            "📋 Os Meus Instrumentos",
            "🔬 Calibração ITR-A",
            "🏗️ Instalação ITR-B",
        ])
        tab1 = tab_inst
        tab2 = None
        tab3 = None
        tab4 = tab_cal
        tab5 = tab_instal
        tab6 = None
        tab7 = None
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
                        novas_count = len([t for t in tags_unicas if t["tag"] not in tags_existentes])

                        st.success(f"✅ **{len(tags_unicas)} tags encontradas** — {novas_count} novas para importar")

                        # Preview agrupado por tipo
                        por_tipo = {}
                        for t in tags_unicas:
                            por_tipo.setdefault(t["tipo"], []).append(t)

                        for tipo, lst in sorted(por_tipo.items()):
                            desc, cor = TIPOS_TAG.get(tipo, ("Outro","#7F8C8D"))
                            tags_str = ", ".join(t["tag"] for t in lst[:8])
                            extra = f" +{len(lst)-8} mais" if len(lst) > 8 else ""
                            st.markdown(
                                f"<div style='margin-bottom:6px;'>"
                                f"<span class='inst-tag-badge' style='background:{cor}'>{tipo}</span>"
                                f" <b>{desc}</b> — {len(lst)} tags: "
                                f"<small style='color:#7A8BA6'>{tags_str}{extra}</small></div>",
                                unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)

                        col_imp1, col_imp2 = st.columns(2)
                        with col_imp1:
                            if st.button("📥 Importar TODAS as tags",
                                    use_container_width=True, type="primary",
                                    key="inst_importar_todas"):
                                _importar_tags(tags_unicas, insts, obra_sel,
                                    obra_key, pid_file.name)
                                st.rerun()
                        with col_imp2:
                            if st.button("📥 Importar só as NOVAS",
                                    use_container_width=True,
                                    key="inst_importar_novas"):
                                novas = [t for t in tags_unicas
                                    if t["tag"] not in tags_existentes]
                                _importar_tags(novas, insts, obra_sel,
                                    obra_key, pid_file.name)
                                st.rerun()

                    elif tags_cache:
                        st.error(f"❌ {tags_cache}")

        # ── Sub: Adicionar Manual ─────────────────────────────
        with sub_manual:
            st.markdown("#### ✏️ Adicionar Instrumento Manualmente")
            with st.form("inst_add_manual"):
                c1m, c2m = st.columns(2)
                with c1m:
                    m_tipo = st.selectbox("Tipo de Tag",
                        list(TIPOS_TAG.keys()),
                        format_func=lambda x: f"{x} — {TIPOS_TAG[x][0]}",
                        key="im_tipo")
                    m_num  = st.text_input("Número da Tag",
                        placeholder="Ex: 101, 1234A", key="im_num")
                    m_desc = st.text_input("Descrição",
                        value=TIPOS_TAG.get(m_tipo,("",""))[0],
                        key="im_desc")
                    m_unid = st.text_input("Unidade de Processo",
                        placeholder="Ex: U-1200, AREA-03", key="im_unid")
                with c2m:
                    m_fab  = st.text_input("Fabricante", key="im_fab")
                    m_mod  = st.text_input("Modelo / Referência", key="im_mod")
                    m_pid  = st.text_input("Referência P&ID",
                        placeholder="Ex: P&ID-101-Rev2", key="im_pid")

                if st.form_submit_button("➕ Adicionar", use_container_width=True):
                    if not m_num.strip():
                        st.error("Número da tag obrigatório.")
                    else:
                        tag_full = f"{m_tipo}-{m_num.strip().upper()}"
                        tags_ex  = insts['Tag'].tolist() if not insts.empty else []
                        if tag_full in tags_ex:
                            st.warning(f"Tag {tag_full} já existe.")
                        else:
                            novo = pd.DataFrame([{
                                "ID": "INST"+_uuid_inst.uuid4().hex[:8].upper(),
                                "Tag": tag_full, "Tipo": m_tipo,
                                "Descricao": m_desc, "Fabricante": m_fab,
                                "Modelo": m_mod, "PID_Ref": m_pid,
                                "Obra": obra_sel, "Unidade": m_unid,
                                "Status": "0", "GPS_Lat": "", "GPS_Lng": "",
                                "Elevacao": "", "Foto_Local_b64": "",
                                "DataCriacao": datetime.now().strftime('%d/%m/%Y %H:%M'),
                                "QR_impresso": "0",
                            }])
                            _save_inst(pd.concat([insts, novo], ignore_index=True),
                                obra_key, "index")
                            inv()
                            st.success(f"✅ {tag_full} adicionado!")
                            st.rerun()

        # ── Sub: Lista Completa ───────────────────────────────
        with sub_lista:
            st.markdown("#### 📊 Todos os Instrumentos")

            if insts.empty:
                st.info("Sem instrumentos. Importa de P&ID ou adiciona manualmente.")
            else:
                # Filtros
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    f_tipo = st.multiselect("Tipo", list(TIPOS_TAG.keys()),
                        key="inst_f_tipo")
                with fc2:
                    f_status = st.multiselect("Estado",
                        [f"{v[2]} {v[0]}" for v in STATUS_INST.values()],
                        key="inst_f_status")
                with fc3:
                    f_pesq = st.text_input("🔍 Pesquisar tag",
                        placeholder="PT-101", key="inst_f_pesq")

                df_show = insts.copy()
                if f_tipo:
                    df_show = df_show[df_show['Tipo'].isin(f_tipo)]
                if f_pesq:
                    df_show = df_show[df_show['Tag'].str.contains(
                        f_pesq.upper(), na=False)]

                for _, row in df_show.iterrows():
                    _, cor = TIPOS_TAG.get(row.get('Tipo','XX'), ("Outro","#7F8C8D"))
                    st_code = str(row.get('Status','0'))
                    st_txt, st_cls, st_ic = STATUS_INST.get(st_code, ("?","","?"))
                    gps_ok = bool(row.get('GPS_Lat') and str(row.get('GPS_Lat')) not in ('','nan'))

                    gps_badge = "<span class='stat-pill' style='background:#EEF2FF;color:#4F46E5'>📍 GPS</span>" if gps_ok else ""
                    st.markdown(
                        f"<div class='inst-tag-card'>"
                        f"<div class='inst-tag-badge' style='background:{cor}'>{row.get('Tipo','?')}</div>"
                        f"<div class='inst-tag-desc'>"
                        f"<div class='tag-nome'>{row.get('Tag','—')} "
                        f"<span class='stat-pill turno-status {st_cls}'>{st_ic} {st_txt}</span>"
                        f"{gps_badge}"
                        f"</div>"
                        f"<div class='tag-sub'>{row.get('Descricao','—')} | "
                        f"{row.get('Fabricante','')} {row.get('Modelo','')} | "
                        f"Unidade: {row.get('Unidade','—')}</div>"
                        f"</div></div>",
                        unsafe_allow_html=True)

                st.markdown(f"**{len(df_show)}** instrumentos mostrados de {len(insts)} total.")

                # ── Export Excel e CSV ───────────────────────────────
                if not insts.empty:
                    st.markdown("---")
                    col_ex1, col_ex2 = st.columns(2)
                    with col_ex1:
                        try:
                            excel_buf = io.BytesIO()
                            export_df = df_show[[c for c in df_show.columns
                                if c not in ["Foto_Local_b64","QR_impresso"]]].copy()
                            export_df.to_excel(excel_buf, index=False, engine="openpyxl")
                            excel_buf.seek(0)
                            st.download_button(
                                label="📊 Exportar Excel",
                                data=excel_buf.getvalue(),
                                file_name=f"InstrumentIndex_{obra_sel}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        except Exception as _ex:
                            st.caption(f"Excel: instala openpyxl")
                    with col_ex2:
                        csv_str = df_show.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📋 Exportar CSV",
                            data=csv_str,
                            file_name=f"InstrumentIndex_{obra_sel}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

        # ── Sub: Etiquetas QR ─────────────────────────────────
        with sub_etiquetas:
            st.markdown("#### 🏷️ Etiquetas QR para Impressão — Zebra 50×30mm")
            st.caption("Gera PDF com etiquetas prontas a imprimir na Zebra. "
                "Uma etiqueta por instrumento com Tag, Descrição e QR Code.")

            if insts.empty:
                st.info("Sem instrumentos no Index.")
            else:
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    filter_nao_impressos = st.checkbox(
                        "Só não impressos ainda", value=True, key="et_filtro")
                with col_e2:
                    et_todos = st.button("🖨️ Gerar PDF de Etiquetas",
                        use_container_width=True, type="primary", key="et_gerar")

                df_et = insts.copy()
                if filter_nao_impressos:
                    df_et = df_et[df_et['QR_impresso'] != '1']

                st.caption(f"{len(df_et)} etiquetas a gerar.")

                if et_todos and not df_et.empty:
                    try:
                        pdf_et = _gerar_etiquetas_zebra(df_et, obra_sel, obra_cod)
                        st.download_button(
                            label=f"⬇️ Descarregar PDF ({len(df_et)} etiquetas)",
                            data=pdf_et,
                            file_name=f"Etiquetas_{obra_key}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                        # Marcar como impressos
                        insts_upd = insts.copy()
                        insts_upd.loc[insts_upd['ID'].isin(df_et['ID'].tolist()),
                            'QR_impresso'] = '1'
                        _save_inst(insts_upd, obra_key, "index")
                        inv()
                        st.success(f"✅ {len(df_et)} etiquetas marcadas como impressas.")
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar etiquetas: {e}")

    # ══════════════════════════════════════════════════════════
    # TAB 2 — HOOK-UPS & BOM (Admin / Chefe) COM IA
    # ══════════════════════════════════════════════════════════
    if tab2_visivel:
        with tab2:
            st.markdown('<div class="section-title">🔩 Hook-Ups & BOM</div>',
                unsafe_allow_html=True)

            sub_hu1, sub_hu2, sub_hu3 = st.tabs([
                "📄 Upload Hook-Up com IA",
                "✏️ BOM Manual",
                "📚 Biblioteca",
            ])

            with sub_hu1:
                st.markdown("#### 📄 Upload Hook-Up (PDF) com Extracção Automática de BOM")
                st.info("💡 Faz upload do PDF do Hook-Up. A IA extrai automaticamente a lista de materiais (BOM).")
                
                hu_tipo = st.selectbox("Tipo de Tag deste Hook-Up",
                    list(TIPOS_TAG.keys()),
                    format_func=lambda x: f"{x} — {TIPOS_TAG[x][0]}",
                    key="hu_tipo_upload")
                hu_cod  = st.text_input("Código do Hook-Up",
                    placeholder="Ex: HU-PT-001, HU-FT-STD", key="hu_cod_upload")
                hu_desc = st.text_input("Descrição", key="hu_desc_upload",
                    placeholder="Ex: Transmissor de Pressão — Serviço Standard")
                hu_file = st.file_uploader("PDF do Hook-Up", type=["pdf"],
                    key="hu_pdf_upload")

                if hu_file:
                    col_btn_bom, col_info_bom = st.columns([2,3])
                    with col_btn_bom:
                        analisar_bom = st.button("🤖 Extrair BOM com IA", 
                            use_container_width=True, type="primary", key="hu_analisar_bom")
                    
                    if analisar_bom:
                        with st.spinner("🤖 A analisar Hook-Up e extrair BOM... (10-20 segundos)"):
                            bom_extraida = _extrair_bom_hookup_claude(hu_file, hu_file.name)
                            
                            if bom_extraida and "erro" not in str(bom_extraida).lower():
                                st.success(f"✅ **{len(bom_extraida)} itens extraídos da BOM**")
                                
                                st.markdown("#### 📋 BOM Extraída:")
                                bom_df = pd.DataFrame(bom_extraida)
                                st.dataframe(bom_df, use_container_width=True)
                                
                                st.session_state[f"bom_extraida_{hu_cod}"] = bom_extraida
                                
                                if st.button("💾 Guardar Hook-Up + BOM", use_container_width=True, type="primary"):
                                    if not hu_cod.strip():
                                        st.error("Código do Hook-Up obrigatório.")
                                    else:
                                        novo_hu = pd.DataFrame([{
                                            "ID": "HU"+_uuid_inst.uuid4().hex[:8].upper(),
                                            "Obra": obra_sel,
                                            "Codigo": hu_cod.strip(),
                                            "Tipo_Tag": hu_tipo,
                                            "Descricao": hu_desc,
                                            "DataCriacao": datetime.now().strftime('%d/%m/%Y %H:%M'),
                                        }])
                                        _save_inst(pd.concat([hookups, novo_hu], ignore_index=True),
                                            obra_key, "hookups")
                                        
                                        hu_id = novo_hu.iloc[0]['ID']
                                        bom_items = []
                                        for i, item in enumerate(bom_extraida):
                                            bom_items.append({
                                                "HookupID": hu_id,
                                                "Item": item.get("item", str(i+1)),
                                                "Descricao": item.get("descricao", ""),
                                                "Quantidade": item.get("quantidade", 1),
                                                "Unidade": item.get("unidade", "un"),
                                                "Especificacao": "",
                                            })
                                        if bom_items:
                                            novo_bom_df = pd.DataFrame(bom_items)
                                            _save_inst(pd.concat([bom, novo_bom_df], ignore_index=True),
                                                obra_key, "bom")
                                        
                                        inv()
                                        st.success(f"✅ Hook-Up {hu_cod} guardado com {len(bom_items)} itens na BOM!")
                                        st.rerun()
                            else:
                                st.error(f"❌ {bom_extraida}")

            with sub_hu2:
                st.markdown("#### ✏️ Introduzir BOM Manualmente")

                if hookups.empty:
                    st.info("Cria primeiro um Hook-Up na tab anterior.")
                else:
                    hu_sel = st.selectbox("Hook-Up",
                        hookups['Codigo'].tolist(), key="bom_hu_sel")
                    hu_id_sel = hookups[hookups['Codigo']==hu_sel]['ID'].iloc[0] \
                        if not hookups.empty else ""

                    st.markdown(f"**BOM actual do {hu_sel}:**")
                    bom_hu = bom[bom['HookupID']==hu_id_sel] if not bom.empty else pd.DataFrame()
                    if not bom_hu.empty:
                        for _, br in bom_hu.iterrows():
                            st.markdown(
                                f"• **{br.get('Quantidade','')} {br.get('Unidade','')}** "
                                f"{br.get('Descricao','—')} "
                                f"<small style='color:#7A8BA6'>({br.get('Especificacao','')})</small>",
                                unsafe_allow_html=True)
                    else:
                        st.caption("Sem itens ainda.")

                    st.markdown("**Adicionar item:**")
                    with st.form("bom_add_item"):
                        bc1, bc2, bc3 = st.columns([1,1,2])
                        with bc1:
                            b_qtd  = st.number_input("Qtd", min_value=0.0,
                                value=1.0, step=0.5, key="b_qtd")
                        with bc2:
                            b_unid = st.selectbox("Unidade",
                                ["un","m","ml","kg","L","rolo","par","cx","jg"],
                                key="b_unid")
                        with bc3:
                            b_desc = st.text_input("Descrição *",
                                placeholder="Ex: Válvula de bloco 1/2\" SS")
                        b_esp = st.text_input("Especificação técnica",
                            placeholder="Ex: PN40, SS316, DN15")

                        if st.form_submit_button("➕ Adicionar Item",
                                use_container_width=True):
                            if not b_desc.strip():
                                st.error("Descrição obrigatória.")
                            else:
                                novo_bom = pd.DataFrame([{
                                    "HookupID": hu_id_sel,
                                    "Item": len(bom_hu)+1,
                                    "Descricao": b_desc.strip(),
                                    "Quantidade": b_qtd,
                                    "Unidade": b_unid,
                                    "Especificacao": b_esp,
                                }])
                                _save_inst(pd.concat([bom, novo_bom], ignore_index=True),
                                    obra_key, "bom")
                                inv()
                                st.success("✅ Item adicionado!")
                                st.rerun()

            with sub_hu3:
                st.markdown("#### 📚 Biblioteca de Hook-Ups desta Obra")
                if hookups.empty:
                    st.info("Sem Hook-Ups criados ainda.")
                else:
                    for _, hu in hookups.iterrows():
                        _, cor = TIPOS_TAG.get(hu.get('Tipo_Tag','XX'), ("","#7F8C8D"))
                        n_bom = len(bom[bom['HookupID']==hu.get('ID','')]) \
                            if not bom.empty else 0
                        n_inst_tipo = len(insts[insts['Tipo']==hu.get('Tipo_Tag','')]) \
                            if not insts.empty else 0
                        st.markdown(
                            f"<div class='inst-tag-card'>"
                            f"<div class='inst-tag-badge' style='background:{cor}'>"
                            f"{hu.get('Tipo_Tag','?')}</div>"
                            f"<div class='inst-tag-desc'>"
                            f"<div class='tag-nome'>{hu.get('Codigo','—')} — {hu.get('Descricao','')}</div>"
                            f"<div class='tag-sub'>📋 {n_bom} itens na BOM | "
                            f"🔧 {n_inst_tipo} instrumentos deste tipo</div>"
                            f"</div></div>",
                            unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # TAB 3 — PACKING LIST (Admin / Chefe) COM IA
    # ══════════════════════════════════════════════════════════
    if tab3_visivel:
        with tab3:
            st.markdown('<div class="section-title">📦 Packing List & Material Check</div>',
                unsafe_allow_html=True)

            sub_pk1, sub_pk2, sub_pk3 = st.tabs([
                "📥 Importar / Registar",
                "✅ Check-in de Recepção",
                "🚦 Semáforo por Instrumento",
            ])

            with sub_pk1:
                st.markdown("#### 🤖 Extrair de PDF (Claude Vision)")
                st.info("💡 Faz upload do PDF do Packing List enviado pelo cliente. "
                    "A IA extrai automaticamente as tags, descrições e quantidades.")
                
                pk_pdf = st.file_uploader("📄 Packing List (PDF)", 
                    type=["pdf"], key="pk_pdf_upload", 
                    help="Pode ser digital ou escaneado. A IA lê tags ISA e materiais.")
                
                if pk_pdf:
                    col_pk1, col_pk2 = st.columns([2,3])
                    with col_pk1:
                        analisar_pk = st.button("🤖 Analisar Packing List", 
                            use_container_width=True, type="primary", key="pk_analisar_ia")
                    with col_pk2:
                        st.caption(f"📄 {pk_pdf.name} — {pk_pdf.size/1024:.0f} KB")
                    
                    if analisar_pk or st.session_state.get("pk_tags_cache_key") == pk_pdf.name:
                        cache_key_pk = f"pk_tags_{obra_key}_{pk_pdf.name}"
                        pk_tags_cache = st.session_state.get(cache_key_pk)
                        
                        if not pk_tags_cache or analisar_pk:
                            with st.spinner("🤖 A analisar Packing List com Claude Vision... (pode demorar 10-20 segundos)"):
                                pk_tags_cache = _extrair_packing_list_claude(pk_pdf, pk_pdf.name)
                                if pk_tags_cache:
                                    st.session_state[cache_key_pk] = pk_tags_cache
                                    st.session_state["pk_tags_cache_key"] = pk_pdf.name
                        
                        if pk_tags_cache and "erro" not in str(pk_tags_cache).lower()[:20]:
                            st.success(f"✅ **{len(pk_tags_cache)} itens encontrados**")
                            
                            preview_df = pd.DataFrame(pk_tags_cache)
                            st.dataframe(preview_df, use_container_width=True)
                            
                            col_imp1, col_imp2 = st.columns(2)
                            with col_imp1:
                                if st.button("📥 Importar TODOS os itens",
                                        use_container_width=True, type="primary",
                                        key="pk_importar_ia"):
                                    itens_para_importar = []
                                    for item in pk_tags_cache:
                                        tag = item.get("tag", "")
                                        if not tag:
                                            tag = f"MAT-{_uuid_inst.uuid4().hex[:4].upper()}"
                                        
                                        itens_para_importar.append({
                                            "ID": "PK"+_uuid_inst.uuid4().hex[:8].upper(),
                                            "Obra": obra_sel,
                                            "Tag": tag,
                                            "Item": "",
                                            "Descricao": item.get("descricao", ""),
                                            "QtdEsperada": item.get("quantidade", 1),
                                            "QtdRecebida": "0",
                                            "Estado": "Pendente",
                                            "DataRecepcao": "",
                                            "Observacao": item.get("observacao", ""),
                                        })
                                    
                                    if itens_para_importar:
                                        novo_df_pk = pd.DataFrame(itens_para_importar)
                                        _save_inst(pd.concat([packing, novo_df_pk], ignore_index=True),
                                            obra_key, "packing")
                                        inv()
                                        st.success(f"✅ {len(itens_para_importar)} itens importados!")
                                        st.rerun()
                                    else:
                                        st.warning("Nenhum item para importar.")
                            with col_imp2:
                                if st.button("📋 Copiar para Excel", use_container_width=True):
                                    try:
                                        excel_buf = io.BytesIO()
                                        preview_df.to_excel(excel_buf, index=False, engine="openpyxl")
                                        excel_buf.seek(0)
                                        st.download_button(
                                            label="⬇️ Descarregar Excel",
                                            data=excel_buf.getvalue(),
                                            file_name=f"PackingList_extraido_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            key="pk_download_excel"
                                        )
                                    except Exception as e:
                                        st.error(f"Erro: {e}")
                        elif pk_tags_cache:
                            st.error(f"❌ {pk_tags_cache}")
                
                st.markdown("---")
                st.markdown("#### 📥 Importar CSV do Cliente")
                st.caption("Se tiveres o Packing List em Excel/CSV, importa aqui.")
                
                pk_csv = st.file_uploader("CSV do Packing List (Tag, Descrição, Qtd)",
                    type=["csv"], key="pk_csv_upload")

                if pk_csv:
                    try:
                        df_pk_raw = pd.read_csv(pk_csv)
                        st.success(f"✅ {len(df_pk_raw)} linhas encontradas.")
                        st.dataframe(df_pk_raw.head(10), use_container_width=True)

                        col_tag = st.selectbox("Coluna da Tag",
                            df_pk_raw.columns.tolist(), key="pk_col_tag")
                        col_desc = st.selectbox("Coluna Descrição",
                            df_pk_raw.columns.tolist(), key="pk_col_desc")
                        col_qtd = st.selectbox("Coluna Quantidade",
                            df_pk_raw.columns.tolist(), key="pk_col_qtd")

                        if st.button("📥 Importar", use_container_width=True,
                                type="primary", key="pk_importar_csv"):
                            novos_pk = []
                            for _, row_pk in df_pk_raw.iterrows():
                                novos_pk.append({
                                    "ID": "PK"+_uuid_inst.uuid4().hex[:8].upper(),
                                    "Obra": obra_sel,
                                    "Tag": str(row_pk.get(col_tag,'')),
                                    "Item": "",
                                    "Descricao": str(row_pk.get(col_desc,'')),
                                    "QtdEsperada": str(row_pk.get(col_qtd,1)),
                                    "QtdRecebida": "0",
                                    "Estado": "Pendente",
                                    "DataRecepcao": "",
                                    "Observacao": "",
                                })
                            novo_df_pk = pd.DataFrame(novos_pk)
                            _save_inst(pd.concat([packing, novo_df_pk], ignore_index=True),
                                obra_key, "packing")
                            inv()
                            st.success(f"✅ {len(novos_pk)} itens importados!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

                st.markdown("---")
                st.markdown("**Ou adiciona item manualmente:**")
                with st.form("pk_add_manual"):
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        pk_tag  = st.selectbox("Tag",
                            ["—"]+insts['Tag'].tolist() if not insts.empty else ["—"],
                            key="pk_tag_m")
                        pk_desc = st.text_input("Descrição do item", key="pk_desc_m")
                    with pc2:
                        pk_qtd  = st.number_input("Quantidade esperada",
                            min_value=1, value=1, key="pk_qtd_m")
                    if st.form_submit_button("➕ Adicionar", use_container_width=True):
                        novo_pk = pd.DataFrame([{
                            "ID": "PK"+_uuid_inst.uuid4().hex[:8].upper(),
                            "Obra": obra_sel, "Tag": pk_tag,
                            "Item": "", "Descricao": pk_desc,
                            "QtdEsperada": pk_qtd, "QtdRecebida": "0",
                            "Estado": "Pendente", "DataRecepcao": "", "Observacao": "",
                        }])
                        _save_inst(pd.concat([packing, novo_pk], ignore_index=True),
                            obra_key, "packing")
                        inv()
                        st.success("✅ Item adicionado!")
                        st.rerun()

            with sub_pk2:
                st.markdown("#### ✅ Check-in — Confirmar Recepção")

                pendentes_pk = packing[packing['Estado']=='Pendente'] \
                    if not packing.empty else pd.DataFrame()

                if pendentes_pk.empty:
                    st.success("✅ Todos os itens verificados!")
                else:
                    st.caption(f"{len(pendentes_pk)} itens por verificar.")
                    for _, pk_row in pendentes_pk.iterrows():
                        with st.expander(
                                f"📦 {pk_row.get('Tag','—')} — {pk_row.get('Descricao','—')[:50]}"):
                            cc1, cc2, cc3 = st.columns(3)
                            with cc1:
                                qtd_rec = st.number_input(
                                    "Qtd recebida",
                                    min_value=0,
                                    value=int(float(str(pk_row.get('QtdEsperada',1)))),
                                    key=f"pk_rec_{pk_row.get('ID','')}")
                            with cc2:
                                est_rec = st.selectbox("Estado",
                                    ["Recebido OK","Recebido com defeito","Em falta"],
                                    key=f"pk_est_{pk_row.get('ID','')}")
                            with cc3:
                                obs_rec = st.text_input("Obs",
                                    key=f"pk_obs_{pk_row.get('ID','')}")

                            if st.button("✅ Confirmar recepção",
                                    key=f"pk_conf_{pk_row.get('ID','')}",
                                    use_container_width=True):
                                pk_upd = packing.copy()
                                idx = pk_upd[pk_upd['ID']==pk_row['ID']].index
                                pk_upd.loc[idx, 'QtdRecebida'] = qtd_rec
                                pk_upd.loc[idx, 'Estado']      = est_rec
                                pk_upd.loc[idx, 'Observacao']  = obs_rec
                                pk_upd.loc[idx, 'DataRecepcao']= datetime.now().strftime('%d/%m/%Y')
                                _save_inst(pk_upd, obra_key, "packing")

                                # Se Recebido OK → atualizar status do instrumento
                                if est_rec == "Recebido OK" and not insts.empty:
                                    tag_pk = pk_row.get('Tag','')
                                    if tag_pk in insts['Tag'].values:
                                        # Verificar se material do Hook-Up está completo
                                        material_completo, msg = _check_material_completo(
                                            tag_pk, pk_upd, bom, hookups)
                                        if material_completo:
                                            inst_upd = insts.copy()
                                            inst_upd.loc[inst_upd['Tag']==tag_pk, 'Status'] = '1'
                                            _save_inst(inst_upd, obra_key, "index")
                                            st.success(f"✅ {tag_pk}: {msg}")
                                        else:
                                            st.warning(f"⚠️ {tag_pk}: {msg}")

                                inv()
                                st.rerun()

            with sub_pk3:
                st.markdown("#### 🚦 Semáforo — Material por Instrumento")

                if insts.empty:
                    st.info("Sem instrumentos no Index.")
                else:
                    for _, inst_row in insts.iterrows():
                        tag = inst_row.get('Tag','')
                        status = str(inst_row.get('Status','0'))
                        _, cor = TIPOS_TAG.get(inst_row.get('Tipo','XX'), ("","#7F8C8D"))

                        # Verificar material completo
                        material_completo, msg = _check_material_completo(tag, packing, bom, hookups)
                        
                        if material_completo:
                            sem_cls, sem_txt, sem_ic = "sem-verde", "Material OK", "🟢"
                        else:
                            sem_cls, sem_txt, sem_ic = "sem-vermelho", msg, "🔴"

                        gps_badge = ""
                        if inst_row.get('GPS_Lat') and str(inst_row.get('GPS_Lat')) not in ('','nan'):
                            gps_badge = "<span class='stat-pill' style='background:#EEF2FF;color:#4F46E5;'>📍 Localizado</span>"

                        st.markdown(
                            f"<div class='inst-tag-card'>"
                            f"<div class='inst-tag-badge' style='background:{cor}'>"
                            f"{inst_row.get('Tipo','?')}</div>"
                            f"<div class='inst-tag-desc'>"
                            f"<div class='tag-nome'>{tag} {gps_badge}</div>"
                            f"<div class='tag-sub'>{inst_row.get('Descricao','—')}</div>"
                            f"</div>"
                            f"<span class='inst-semaforo {sem_cls}'>{sem_ic} {sem_txt}</span>"
                            f"</div>",
                            unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # TAB 4 — CALIBRAÇÃO ITR-A (com formulário completo)
    # ══════════════════════════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-title">🔬 Calibração em Bancada — ITR-A</div>',
            unsafe_allow_html=True)

        # Verificar material completo para cada instrumento antes de mostrar
        inst_para_cal = []
        if not insts.empty:
            for _, inst in insts.iterrows():
                if inst['Status'] == '1':  # Material OK
                    tag = inst['Tag']
                    material_completo, msg = _check_material_completo(tag, packing, bom, hookups)
                    if material_completo:
                        inst_para_cal.append(inst)
                    else:
                        st.warning(f"⚠️ {tag}: {msg} - pendente de material para calibração")
        
        inst_para_cal = pd.DataFrame(inst_para_cal) if inst_para_cal else pd.DataFrame()
        inst_calibrados = insts[insts['Status'].isin(['2','3','4'])] \
            if not insts.empty else pd.DataFrame()

        sub_cal1, sub_cal2 = st.tabs(["🔬 Nova Calibração", "📋 Histórico ITR-A"])

        with sub_cal1:
            if inst_para_cal.empty:
                st.info("Sem instrumentos prontos para calibrar. "
                    "Verifica o Packing List — os instrumentos precisam de estar com "
                    "🟢 Material OK e com o material do Hook-Up completo.")
            else:
                # Instrumentistas só vêem os atribuídos a eles via ITR-A
                if not is_admin_inst and not is_chefe_inst:
                    tags_ja_minhas = itr_a[itr_a['Instrumentista']==user_atual]['Tag'].tolist() \
                        if not itr_a.empty else []
                    inst_para_cal = inst_para_cal[
                        ~inst_para_cal['Tag'].isin(tags_ja_minhas)
                    ]
                st.caption(f"{len(inst_para_cal)} instrumento(s) prontos para calibração.")

                tag_cal = st.selectbox("Seleccionar instrumento",
                    inst_para_cal['Tag'].tolist() if not inst_para_cal.empty else [],
                    key="cal_tag_sel")

                if tag_cal and not inst_para_cal.empty:
                    inst_sel = inst_para_cal[inst_para_cal['Tag']==tag_cal].iloc[0]
                    _, cor = TIPOS_TAG.get(inst_sel.get('Tipo','XX'), ("","#7F8C8D"))

                    st.markdown(
                        f"<div class='inst-tag-card'>"
                        f"<div class='inst-tag-badge' style='background:{cor}'>"
                        f"{inst_sel.get('Tipo','?')}</div>"
                        f"<div class='inst-tag-desc'>"
                        f"<div class='tag-nome'>{tag_cal}</div>"
                        f"<div class='tag-sub'>{inst_sel.get('Descricao','—')} | "
                        f"{inst_sel.get('Fabricante','')} {inst_sel.get('Modelo','')}</div>"
                        f"</div></div>",
                        unsafe_allow_html=True)

                    # ──────────────────────────────────────────────────────────
                    # FORMULÁRIO COMPLETO DE CALIBRAÇÃO
                    # ──────────────────────────────────────────────────────────
                    with st.form("cal_form_completo"):
                        st.markdown("#### 📋 Identificação do Equipamento")
                        col_id1, col_id2, col_id3, col_id4 = st.columns(4)
                        with col_id1:
                            cal_marca = st.text_input("Marca", key="cal_marca")
                        with col_id2:
                            cal_modelo = st.text_input("Modelo", value=inst_sel.get('Modelo',''), key="cal_modelo")
                        with col_id3:
                            cal_nserie = st.text_input("Nº Série", key="cal_nserie")
                        with col_id4:
                            cal_tipo = st.text_input("Tipo", value=inst_sel.get('Tipo',''), key="cal_tipo")

                        st.markdown("#### 🔧 Estado do Equipamento")
                        col_est1, col_est2, col_est3, col_est4 = st.columns(4)
                        with col_est1:
                            cal_carcaca = st.selectbox("Carcaça", ["OK", "Danificado", "Não aplicável"], key="cal_carcaca")
                        with col_est2:
                            cal_roscas = st.selectbox("Roscas", ["OK", "Danificado", "Não aplicável"], key="cal_roscas")
                        with col_est3:
                            cal_eletronica = st.selectbox("Eletrónica", ["OK", "Danificado", "Não aplicável"], key="cal_eletronica")
                        with col_est4:
                            cal_sensor = st.selectbox("Elemento sensorial", ["OK", "Danificado", "Não aplicável"], key="cal_sensor")

                        st.markdown("#### 📊 Dados de Processo / Parâmetros")
                        col_dp1, col_dp2, col_dp3, col_dp4 = st.columns(4)
                        with col_dp1:
                            cal_funcao = st.text_input("Função", key="cal_funcao")
                        with col_dp2:
                            cal_faixa_min = st.number_input("Faixa de medição (min)", value=0.0, step=0.1, key="cal_faixa_min")
                        with col_dp3:
                            cal_faixa_max = st.number_input("Faixa de medição (max)", value=100.0, step=0.1, key="cal_faixa_max")
                        with col_dp4:
                            cal_unidade = st.text_input("Unidades", key="cal_unidade")

                        # ──────────────────────────────────────────────────────
                        # TESTE SUBIDA - 5 pontos
                        # ──────────────────────────────────────────────────────
                        st.markdown("#### 📈 Teste de Subida")
                        st.markdown("Preencha os valores para os pontos 0%, 25%, 50%, 75% e 100%")
                        
                        col_sub1, col_sub2, col_sub3, col_sub4, col_sub5 = st.columns(5)
                        
                        pontos = [0, 0.25, 0.5, 0.75, 1]
                        valores_subida = {}
                        
                        for i, ponto in enumerate(pontos):
                            pct = int(ponto * 100)
                            with [col_sub1, col_sub2, col_sub3, col_sub4, col_sub5][i]:
                                st.markdown(f"**{pct}%**")
                                val_teorico = cal_faixa_min + ponto * (cal_faixa_max - cal_faixa_min)
                                st.caption(f"Teórico: {val_teorico:.1f}")
                                valores_subida[f"simulado_{pct}"] = st.number_input(
                                    "Simulado", value=val_teorico, step=0.1, key=f"sub_sim_{i}",
                                    label_visibility="collapsed"
                                )
                                valores_subida[f"lido_{pct}"] = st.number_input(
                                    "Lido", value=val_teorico, step=0.01, key=f"sub_li_{i}",
                                    label_visibility="collapsed"
                                )

                        # ──────────────────────────────────────────────────────
                        # TESTE DESCIDA - 5 pontos
                        # ──────────────────────────────────────────────────────
                        st.markdown("#### 📉 Teste de Descida")
                        st.markdown("Preencha os valores para os pontos 100%, 75%, 50%, 25% e 0%")
                        
                        col_desc1, col_desc2, col_desc3, col_desc4, col_desc5 = st.columns(5)
                        
                        pontos_desc = [1, 0.75, 0.5, 0.25, 0]
                        valores_descida = {}
                        
                        for i, ponto in enumerate(pontos_desc):
                            pct = int(ponto * 100)
                            with [col_desc1, col_desc2, col_desc3, col_desc4, col_desc5][i]:
                                st.markdown(f"**{pct}%**")
                                val_teorico = cal_faixa_min + ponto * (cal_faixa_max - cal_faixa_min)
                                st.caption(f"Teórico: {val_teorico:.1f}")
                                valores_descida[f"simulado_{pct}"] = st.number_input(
                                    "Simulado", value=val_teorico, step=0.1, key=f"desc_sim_{i}",
                                    label_visibility="collapsed"
                                )
                                valores_descida[f"lido_{pct}"] = st.number_input(
                                    "Lido", value=val_teorico, step=0.01, key=f"desc_li_{i}",
                                    label_visibility="collapsed"
                                )

                        # ──────────────────────────────────────────────────────
                        # DIAGNÓSTICO E VEREDITO
                        # ──────────────────────────────────────────────────────
                        st.markdown("#### 📝 Diagnóstico e Veredito")
                        
                        col_diag1, col_diag2 = st.columns(2)
                        with col_diag1:
                            st.markdown("**Antes da Calibração**")
                            cal_estado_antes = st.selectbox("Estado", ["OK", "Fora de especificação", "Não testado"], key="cal_estado_antes")
                            cal_calibrar_antes = st.selectbox("Necessário calibrar?", ["Sim", "Não", "Parcialmente"], key="cal_calibrar_antes")
                            cal_obs_antes = st.text_area("Comentário", height=60, key="cal_obs_antes")
                        
                        with col_diag2:
                            st.markdown("**Após Calibração**")
                            cal_estado_depois = st.selectbox("Estado", ["OK", "Fora de especificação", "Não testado"], key="cal_estado_depois")
                            cal_calibrar_depois = st.selectbox("Necessário calibrar?", ["Sim", "Não", "Parcialmente"], key="cal_calibrar_depois")
                            cal_obs_depois = st.text_area("Comentário", height=60, key="cal_obs_depois")

                        # ──────────────────────────────────────────────────────
                        # VEREDITO FINAL E ASSINATURAS
                        # ──────────────────────────────────────────────────────
                        st.markdown("#### ✅ Veredito Final e Assinaturas")
                        
                        col_ver1, col_ver2 = st.columns(2)
                        with col_ver1:
                            cal_veredito = st.selectbox("Estado Final", ["Aprovado", "Reprovado", "Condicional"], key="cal_veredito")
                            cal_tecnico = st.text_input("Técnico", value=st.session_state.get('user',''), key="cal_tecnico")
                            cal_data = st.date_input("Data", value=datetime.now().date(), key="cal_data")
                        
                        with col_ver2:
                            cal_necessario = st.selectbox("Necessário calibrar?", ["Sim", "Não"], key="cal_necessario")
                            cal_responsavel = st.text_input("Responsável", key="cal_responsavel")
                            cal_data_resp = st.date_input("Data (Responsável)", value=datetime.now().date(), key="cal_data_resp")

                        # Botão de submissão
                        if st.form_submit_button("💾 Registar Calibração ITR-A", use_container_width=True, type="primary"):
                            # Calcular erros máximos
                            erro_max_subida = 0
                            for ponto in [0, 25, 50, 75, 100]:
                                teorico = cal_faixa_min + (ponto/100) * (cal_faixa_max - cal_faixa_min)
                                lido = valores_subida.get(f"lido_{ponto/100}", teorico)
                                if teorico != 0:
                                    erro = abs((lido - teorico) / teorico) * 100
                                    erro_max_subida = max(erro_max_subida, erro)
                            
                            erro_max_descida = 0
                            for ponto in [100, 75, 50, 25, 0]:
                                teorico = cal_faixa_min + (ponto/100) * (cal_faixa_max - cal_faixa_min)
                                lido = valores_descida.get(f"lido_{ponto}", teorico)
                                if teorico != 0:
                                    erro = abs((lido - teorico) / teorico) * 100
                                    erro_max_descida = max(erro_max_descida, erro)
                            
                            erro_max_global = max(erro_max_subida, erro_max_descida)
                            pass_fail = "PASS" if erro_max_global <= 1.0 else "FAIL"
                            
                            # Criar registro
                            novo_itr = pd.DataFrame([{
                                "ID": "ITRA"+_uuid_inst.uuid4().hex[:8].upper(),
                                "Tag": tag_cal,
                                "Obra": obra_sel,
                                "Instrumentista": cal_tecnico,
                                "DataCalibracao": cal_data.strftime('%d/%m/%Y'),
                                "Marca": cal_marca,
                                "Modelo": cal_modelo,
                                "NSerie": cal_nserie,
                                "Tipo": cal_tipo,
                                "Estado_Carcaca": cal_carcaca,
                                "Estado_Roscas": cal_roscas,
                                "Estado_Eletronica": cal_eletronica,
                                "Estado_Sensor": cal_sensor,
                                "Funcao": cal_funcao,
                                "RangeMin": cal_faixa_min,
                                "RangeMax": cal_faixa_max,
                                "Unidade": cal_unidade,
                                "ValsSubida": str(valores_subida),
                                "ValsDescida": str(valores_descida),
                                "ErroMaximo": erro_max_global,
                                "PassFail": pass_fail,
                                "EstadoAntes": cal_estado_antes,
                                "CalibrarAntes": cal_calibrar_antes,
                                "ObsAntes": cal_obs_antes,
                                "EstadoDepois": cal_estado_depois,
                                "CalibrarDepois": cal_calibrar_depois,
                                "ObsDepois": cal_obs_depois,
                                "Veredito": cal_veredito,
                                "Responsavel": cal_responsavel,
                                "DataResponsavel": cal_data_resp.strftime('%d/%m/%Y'),
                                "Assinatura_b64": "",
                            }])
                            _save_inst(pd.concat([itr_a, novo_itr], ignore_index=True),
                                obra_key, "itr_a")

                            if pass_fail == "PASS":
                                inst_upd = insts.copy()
                                inst_upd.loc[inst_upd['Tag']==tag_cal, 'Status'] = '2'
                                _save_inst(inst_upd, obra_key, "index")

                            inv()
                            st.success(f"✅ Calibração registada para {tag_cal}!")
                            st.success(f"📊 Erro máximo: {erro_max_global:.2f}% — {pass_fail}")
                            st.rerun()

        with sub_cal2:
            if itr_a.empty:
                st.info("Sem calibrações registadas.")
            else:
                st.markdown("#### 📋 Histórico de Calibrações")
                
                # Filtros
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filtro_tag = st.multiselect("Filtrar por Tag", 
                        itr_a['Tag'].unique().tolist() if not itr_a.empty else [],
                        key="hist_filtro_tag")
                with col_f2:
                    filtro_result = st.multiselect("Resultado", ["PASS", "FAIL"],
                        default=["PASS", "FAIL"], key="hist_filtro_res")
                
                df_hist = itr_a.copy()
                if filtro_tag:
                    df_hist = df_hist[df_hist['Tag'].isin(filtro_tag)]
                if filtro_result:
                    df_hist = df_hist[df_hist['PassFail'].isin(filtro_result)]
                
                for _, itr_row in df_hist.sort_values('DataCalibracao',
                        ascending=False).iterrows():
                    pf = itr_row.get('PassFail','')
                    cls_ = "pass" if pf=="PASS" else "fail"
                    ic_  = "✅" if pf=="PASS" else "❌"
                    
                    with st.expander(f"{ic_} {itr_row.get('Tag','—')} — {itr_row.get('DataCalibracao','—')} — Erro: {itr_row.get('ErroMaximo',0):.2f}%"):
                        st.markdown(f"**Marca:** {itr_row.get('Marca','—')} | **Modelo:** {itr_row.get('Modelo','—')} | **Nº Série:** {itr_row.get('NSerie','—')}")
                        st.markdown(f"**Faixa:** {itr_row.get('RangeMin','')} – {itr_row.get('RangeMax','')} {itr_row.get('Unidade','')}")
                        st.markdown(f"**Estado do equipamento:** Carcaça: {itr_row.get('Estado_Carcaca','—')} | Roscas: {itr_row.get('Estado_Roscas','—')}")
                        st.markdown(f"**Veredito Final:** {itr_row.get('Veredito','—')} | Responsável: {itr_row.get('Responsavel','—')}")
                        st.markdown(f"**Observações:** {itr_row.get('ObsDepois','—')}")
                        
                        if st.button("📄 Gerar PDF da Calibração", key=f"pdf_{itr_row.get('ID','')}"):
                            try:
                                pdf_bytes = _gerar_pdf_calibracao(itr_row, tag_cal if 'tag_cal' in dir() else itr_row.get('Tag',''))
                                st.download_button(
                                    label="⬇️ Descarregar PDF",
                                    data=pdf_bytes,
                                    file_name=f"Calibracao_{itr_row.get('Tag','')}_{itr_row.get('DataCalibracao','')}.pdf",
                                    mime="application/pdf",
                                    key=f"download_{itr_row.get('ID','')}"
                                )
                            except Exception as e:
                                st.error(f"Erro ao gerar PDF: {e}")

    # ══════════════════════════════════════════════════════════
    # TAB 5 — INSTALAÇÃO ITR-B + GPS
    # ══════════════════════════════════════════════════════════
    with tab5:
        st.markdown('<div class="section-title">🏗️ Instalação no Terreno — ITR-B</div>',
            unsafe_allow_html=True)

        sub_it1, sub_it2, sub_it3 = st.tabs([
            "📍 Marcar Localização (tu)",
            "🔧 Registar Instalação (técnico)",
            "🗺️ Mapa da Obra",
        ])

                with sub_it1:
            st.markdown("#### 📍 Levantamento de Posições — Chefe vai ao Terreno")
            st.caption("Vai ao local de cada instrumento, captura o GPS, tira uma foto e define a elevação. "
                "Os técnicos seguirão estas coordenadas e terão a foto como referência.")
            
            # Botão de refresh manual
            col_refresh, col_gps_info = st.columns([1, 3])
            with col_refresh:
                if st.button("🔄 Atualizar GPS", use_container_width=True, type="primary", key="btn_refresh_gps"):
                    st.query_params["refresh_gps"] = str(datetime.now().timestamp())
                    st.rerun()
            
            # Componente HTML/JS para captura de GPS com atualização automática
            gps_inst_html = """
<div id="gps-inst-status" style="color:#7A8BA6;font-size:.82rem;padding:.3rem 0;
  background:#F0F9FF;border-radius:8px;padding:8px 12px;margin-bottom:8px;">
  📍 A obter GPS...
</div>
<div id="gps-coords" style="display:none;"></div>
<script>
(function(){
  function updatePosition(pos) {
    var lat = pos.coords.latitude.toFixed(6);
    var lon = pos.coords.longitude.toFixed(6);
    var acc = Math.round(pos.coords.accuracy);
    var timestamp = new Date().toLocaleTimeString();
    
    var statusDiv = document.getElementById('gps-inst-status');
    statusDiv.innerHTML = '📍 GPS: <b style="color:#0A2463">'+lat+', '+lon+'</b> (±'+acc+'m) - Atualizado às '+timestamp;
    statusDiv.style.color = '#059669';
    statusDiv.style.background = '#D1FAE5';
    
    var url = new URL(window.location.href);
    url.searchParams.set('inst_lat', lat);
    url.searchParams.set('inst_lon', lon);
    url.searchParams.set('gps_timestamp', timestamp);
    window.history.replaceState({}, '', url);
    
    window.dispatchEvent(new Event('gps-updated'));
  }
  
  function showError(err) {
    var statusDiv = document.getElementById('gps-inst-status');
    var errorMsg = '';
    switch(err.code) {
      case err.PERMISSION_DENIED:
        errorMsg = 'Permissão negada. Permita acesso à localização.';
        break;
      case err.POSITION_UNAVAILABLE:
        errorMsg = 'Localização indisponível. Verifique o GPS.';
        break;
      case err.TIMEOUT:
        errorMsg = 'Tempo esgotado. Tente novamente.';
        break;
      default:
        errorMsg = 'Erro: ' + err.message;
    }
    statusDiv.innerHTML = '⚠️ GPS: ' + errorMsg;
    statusDiv.style.color = '#D97706';
    statusDiv.style.background = '#FEF3C7';
  }
  
  if(!navigator.geolocation){
    document.getElementById('gps-inst-status').innerHTML = '⚠️ GPS não suportado neste navegador';
    return;
  }
  
  function getLocation() {
    navigator.geolocation.getCurrentPosition(updatePosition, showError, {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 0
    });
  }
  
  getLocation();
  
  var urlParams = new URLSearchParams(window.location.search);
  if(urlParams.has('refresh_gps')) {
    getLocation();
  }
  
  setInterval(function() {
    getLocation();
  }, 30000);
  
})();
</script>"""
            
            st.components.v1.html(gps_inst_html, height=80)
            
            # Obter coordenadas dos query params (atualizadas automaticamente)
            gps_lat = st.query_params.get("inst_lat", "")
            gps_lon = st.query_params.get("inst_lon", "")
            gps_timestamp = st.query_params.get("gps_timestamp", "")
            
            # Mostrar timestamp se disponível
            if gps_timestamp:
                st.caption(f"🕐 Última atualização GPS: {gps_timestamp}")
            
            # Lista de instrumentos sem GPS
            sem_gps = insts[
                (insts['GPS_Lat'].isna() | (insts['GPS_Lat']=='') | (insts['GPS_Lat']=='nan'))
            ] if not insts.empty else pd.DataFrame()
            
            # Instrumentos com GPS já registado
            com_gps = insts[
                insts['GPS_Lat'].notna() & 
                (insts['GPS_Lat'] != '') & 
                (insts['GPS_Lat'] != 'nan')
            ] if not insts.empty else pd.DataFrame()
            
            # Mostrar contadores
            col_count1, col_count2 = st.columns(2)
            with col_count1:
                st.metric("📌 Instrumentos sem GPS", len(sem_gps))
            with col_count2:
                st.metric("📍 Instrumentos com GPS", len(com_gps))
            
            if sem_gps.empty:
                st.success("✅ Todos os instrumentos têm localização GPS!")
            else:
                st.caption(f"Selecione um instrumento da lista abaixo para marcar a localização atual e tirar foto.")
                
                tag_gps = st.selectbox("Instrumento a localizar",
                    sem_gps['Tag'].tolist(), key="gps_tag_sel")
                
                # Preencher automaticamente os campos com o GPS capturado
                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1:
                    lat_man = st.text_input("Latitude",
                        value=gps_lat, key="gps_lat_man",
                        help="Valor capturado automaticamente do GPS")
                with col_g2:
                    lon_man = st.text_input("Longitude",
                        value=gps_lon, key="gps_lon_man",
                        help="Valor capturado automaticamente do GPS")
                with col_g3:
                    elev_man = st.number_input("Elevação (m)",
                        value=0.0, step=0.5,
                        help="0m=piso 0, 6m=plataforma 1, 12m=plataforma 2",
                        key="gps_elev_man")
                
                # Nota sobre o preenchimento automático
                if gps_lat and gps_lon:
                    st.info("✅ Latitude e Longitude preenchidas automaticamente com o GPS atual!")
                else:
                    st.warning("⏳ Aguardando leitura do GPS... Clique em '🔄 Atualizar GPS' se necessário.")
                
                # ──────────────────────────────────────────────────────────────
                # SEÇÃO DE FOTO - NOVO!
                # ──────────────────────────────────────────────────────────────
                st.markdown("#### 📸 Foto do Instrumento")
                st.caption("Tire uma foto do instrumento para ajudar os técnicos a encontrá-lo no terreno.")
                
                # Verificar se já existe foto para este instrumento
                inst_sel = insts[insts['Tag'] == tag_gps].iloc[0] if not insts.empty and tag_gps in insts['Tag'].values else None
                if inst_sel and inst_sel.get('Foto_Local_b64') and inst_sel.get('Foto_Local_b64') != '':
                    try:
                        st.image(base64.b64decode(inst_sel['Foto_Local_b64']), 
                                 caption=f"📸 Foto atual de {tag_gps}", 
                                 width=300,
                                 use_container_width=True)
                        if st.button("🗑️ Remover foto", key=f"del_foto_{tag_gps}"):
                            inst_upd = insts.copy()
                            inst_upd.loc[inst_upd['Tag'] == tag_gps, 'Foto_Local_b64'] = ''
                            _save_inst(inst_upd, obra_key, "index")
                            inv()
                            st.rerun()
                    except Exception as e:
                        st.warning(f"Não foi possível carregar a foto: {e}")
                
                # Upload de foto
                foto_file = st.file_uploader("📸 Tirar foto ou fazer upload", 
                                             type=["jpg", "jpeg", "png"], 
                                             key=f"foto_upload_{tag_gps}",
                                             help="Tire uma foto com o telemóvel ou faça upload de uma imagem existente")
                
                if foto_file:
                    img_bytes = foto_file.read()
                    img_b64 = base64.b64encode(img_bytes).decode()
                    st.image(img_bytes, caption="Pré-visualização", width=200)
                    
                    if st.button("💾 Guardar Foto", key=f"guardar_foto_{tag_gps}"):
                        inst_upd = insts.copy()
                        inst_upd.loc[inst_upd['Tag'] == tag_gps, 'Foto_Local_b64'] = img_b64
                        _save_inst(inst_upd, obra_key, "index")
                        inv()
                        st.success(f"✅ Foto guardada para {tag_gps}!")
                        st.rerun()
                
                st.markdown("---")
                
                obs_local = st.text_area("Notas do local",
                    placeholder="Ex: Entre linha P-101 e coluna C-14, face norte. Próximo ao tanque T-123.",
                    height=60, key="gps_obs_man")
                
                # Botão para guardar localização
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("📍 Guardar Localização", use_container_width=True, type="primary", key="gps_guardar"):
                        if not lat_man or not lon_man:
                            st.error("Latitude e Longitude obrigatórias. Aguarde a leitura do GPS ou clique em 'Atualizar GPS'.")
                        else:
                            inst_upd = insts.copy()
                            inst_upd.loc[inst_upd['Tag']==tag_gps, 'GPS_Lat'] = lat_man
                            inst_upd.loc[inst_upd['Tag']==tag_gps, 'GPS_Lng'] = lon_man
                            inst_upd.loc[inst_upd['Tag']==tag_gps, 'Elevacao'] = elev_man
                            _save_inst(inst_upd, obra_key, "index")
                            inv()
                            st.success(f"✅ {tag_gps} localizado — {lat_man}, {lon_man} (+{elev_man}m)")
                            st.rerun()
                
                with col_btn2:
                    if st.button("➡️ Próximo Instrumento", use_container_width=True, key="gps_proximo"):
                        sem_gps_atualizado = insts[
                            (insts['GPS_Lat'].isna() | (insts['GPS_Lat']=='') | (insts['GPS_Lat']=='nan'))
                        ] if not insts.empty else pd.DataFrame()
                        if not sem_gps_atualizado.empty and len(sem_gps_atualizado) > 0:
                            next_tag = sem_gps_atualizado['Tag'].iloc[0]
                            st.session_state['gps_tag_sel'] = next_tag
                            st.rerun()
                        else:
                            st.success("✅ Todos os instrumentos já têm GPS!")

        with sub_it2:
            st.markdown("#### 🔧 Registar Instalação — ITR-B")

            inst_para_instalar = insts[insts['Status']=='2'] \
                if not insts.empty else pd.DataFrame()

            if inst_para_instalar.empty:
                st.info("Sem instrumentos calibrados prontos para instalar.")
            else:
                tag_it = st.selectbox("Instrumento a instalar",
                    inst_para_instalar['Tag'].tolist(), key="itb_tag_sel")

                inst_it = inst_para_instalar[inst_para_instalar['Tag']==tag_it].iloc[0]
                lat_it = str(inst_it.get('GPS_Lat',''))
                lon_it = str(inst_it.get('GPS_Lng',''))
                elv_it = str(inst_it.get('Elevacao',''))

                if lat_it and lat_it not in ('','nan'):
                    nav_url = f"https://maps.google.com/?q={lat_it},{lon_it}"
                    st.markdown(
                        f"📍 **Localização:** {lat_it}, {lon_it} &nbsp;|&nbsp; "
                        f"Elevação: **+{elv_it}m** &nbsp;|&nbsp; "
                        f"<a href='{nav_url}' target='_blank'>🗺️ Navegar no Google Maps</a>",
                        unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Este instrumento não tem GPS definido. "
                        "Pede ao chefe para marcar a localização.")

                with st.form("itb_form"):
                    it1, it2 = st.columns(2)
                    with it1:
                        it_tecnico = st.text_input("Técnico instalador",
                            value=st.session_state.get('user',''), key="itb_tec")
                        it_loop = st.selectbox("Loop Check",
                            ["✅ OK","❌ Falhou","⏳ Pendente"], key="itb_loop")
                    with sub_it2:
    st.markdown("#### 🔧 Registar Instalação — ITR-B")

    inst_para_instalar = insts[insts['Status']=='2'] \
        if not insts.empty else pd.DataFrame()

    if inst_para_instalar.empty:
        st.info("Sem instrumentos calibrados prontos para instalar.")
    else:
        tag_it = st.selectbox("Instrumento a instalar",
            inst_para_instalar['Tag'].tolist(), key="itb_tag_sel")

        inst_it = inst_para_instalar[inst_para_instalar['Tag']==tag_it].iloc[0]
        lat_it = str(inst_it.get('GPS_Lat',''))
        lon_it = str(inst_it.get('GPS_Lng',''))
        elv_it = str(inst_it.get('Elevacao',''))

        # ──────────────────────────────────────────────────────────────
        # MOSTRAR LOCALIZAÇÃO
        # ──────────────────────────────────────────────────────────────
        if lat_it and lat_it not in ('','nan'):
            nav_url = f"https://maps.google.com/?q={lat_it},{lon_it}"
            st.markdown(
                f"📍 **Localização:** {lat_it}, {lon_it} &nbsp;|&nbsp; "
                f"Elevação: **+{elv_it}m** &nbsp;|&nbsp; "
                f"<a href='{nav_url}' target='_blank'>🗺️ Navegar no Google Maps</a>",
                unsafe_allow_html=True)
        else:
            st.warning("⚠️ Este instrumento não tem GPS definido. "
                "Pede ao chefe para marcar a localização.")
        
        st.markdown("---")
        
        # ──────────────────────────────────────────────────────────────
        # MOSTRAR FOTO DO INSTRUMENTO (para técnicos)
        # ──────────────────────────────────────────────────────────────
        st.markdown("#### 📸 Foto de Referência")
        st.caption("Foto tirada pelo chefe de equipa no momento do levantamento GPS")
        
        # Buscar a foto do instrumento
        inst_foto = insts[insts['Tag'] == tag_it].iloc[0] if not insts.empty and tag_it in insts['Tag'].values else None
        
        if inst_foto is not None:
            foto_b64 = inst_foto.get('Foto_Local_b64', '')
            if foto_b64 and foto_b64 != '' and foto_b64 != 'nan':
                try:
                    import base64
                    # Decodificar a imagem base64
                    img_data = base64.b64decode(foto_b64)
                    st.image(img_data, 
                             caption=f"📸 {tag_it} - Foto tirada pelo chefe de equipa", 
                             width=300,
                             use_container_width=True)
                    st.success("✅ Foto disponível! Use esta imagem como referência para localizar o instrumento.")
                except Exception as e:
                    st.warning(f"⚠️ Não foi possível carregar a foto: {e}")
            else:
                st.info("📸 Nenhuma foto disponível para este instrumento. Pode solicitar ao chefe de equipa que tire uma foto.")
        else:
            st.info("📸 Nenhuma foto disponível para este instrumento.")
        
        st.markdown("---")

        # ──────────────────────────────────────────────────────────────
        # FORMULÁRIO DE INSTALAÇÃO
        # ──────────────────────────────────────────────────────────────
        with st.form("itb_form"):
            it1, it2 = st.columns(2)
            with it1:
                it_tecnico = st.text_input("Técnico instalador",
                    value=st.session_state.get('user',''), key="itb_tec")
                it_loop = st.selectbox("Loop Check",
                    ["✅ OK","❌ Falhou","⏳ Pendente"], key="itb_loop")
            with it2:
                it_obs = st.text_area("Observações", height=80, key="itb_obs")

            # Botão de submissão
            if st.form_submit_button("✅ Confirmar Instalação",
                    use_container_width=True, type="primary"):
                novo_itb = pd.DataFrame([{
                    "ID": "ITRB"+_uuid_inst.uuid4().hex[:8].upper(),
                    "Tag": tag_it, "Obra": obra_sel,
                    "Tecnico": it_tecnico,
                    "DataInstalacao": datetime.now().strftime('%d/%m/%Y %H:%M'),
                    "GPS_Lat": lat_it, "GPS_Lng": lon_it, "Elevacao": elv_it,
                    "Foto_b64": "", "LoopCheck": it_loop,
                    "Observacoes": it_obs, "Assinatura_b64": "",
                }])
                _save_inst(pd.concat([itr_b, novo_itb], ignore_index=True),
                    obra_key, "itr_b")

                if "OK" in it_loop:
                    inst_upd = insts.copy()
                    inst_upd.loc[inst_upd['Tag']==tag_it, 'Status'] = '3'
                    _save_inst(inst_upd, obra_key, "index")

                inv()
                st.success(f"✅ ITR-B registado para {tag_it}!")
                st.rerun()

        with sub_it3:
            st.markdown("#### 🗺️ Mapa da Obra — Instrumentos Geolocalizados")

            inst_com_gps = insts[
                insts['GPS_Lat'].notna() &
                (insts['GPS_Lat'] != '') &
                (insts['GPS_Lat'] != 'nan')
            ] if not insts.empty else pd.DataFrame()

            if inst_com_gps.empty:
                st.info("Sem instrumentos com GPS. Marca as localizações na tab anterior.")
            else:
                try:
                    import folium
                    from streamlit_folium import folium_static

                    lat_c = float(inst_com_gps['GPS_Lat'].iloc[0])
                    lon_c = float(inst_com_gps['GPS_Lng'].iloc[0])

                    mapa = folium.Map(
                        location=[lat_c, lon_c], zoom_start=18,
                        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                        attr='Google Satellite'
                    )

                    for _, mi in inst_com_gps.iterrows():
                        try:
                            lt = float(mi['GPS_Lat'])
                            ln = float(mi['GPS_Lng'])
                            _, cor_m = TIPOS_TAG.get(mi.get('Tipo','XX'),("","#7F8C8D"))
                            st_code = str(mi.get('Status','0'))
                            _, _, st_ic = STATUS_INST.get(st_code,("","","?"))
                            elv = mi.get('Elevacao','0')
                            popup_html = (
                                f"<b>{mi.get('Tag','—')}</b><br>"
                                f"{mi.get('Descricao','—')}<br>"
                                f"Estado: {st_ic}<br>"
                                f"Elevação: +{elv}m<br>"
                                f"{mi.get('Fabricante','')} {mi.get('Modelo','')}"
                            )
                            folium.CircleMarker(
                                location=[lt, ln],
                                radius=10,
                                color=cor_m, fill=True, fill_color=cor_m,
                                fill_opacity=0.8,
                                popup=folium.Popup(popup_html, max_width=200),
                                tooltip=f"{mi.get('Tag','—')} +{elv}m"
                            ).add_to(mapa)
                        except Exception:
                            pass

                    folium_static(mapa, width=None, height=450)
                    st.caption(f"🗺️ {len(inst_com_gps)} instrumentos no mapa. "
                        "Clica em cada marcador para ver detalhes.")
                except Exception as e:
                    st.error(f"Erro ao carregar mapa: {e}")

    # ══════════════════════════════════════════════════════════
    # TAB 6 — PUNCH LIST (Admin / Chefe)
    # ══════════════════════════════════════════════════════════
    if tab6_visivel:
        with tab6:
            st.markdown('<div class="section-title">⚠️ Punch List</div>',
                unsafe_allow_html=True)

            def _punch_count(cat, estado="Aberto"):
                if punch.empty: return 0
                return len(punch[(punch['Categoria']==cat)&(punch['Status']==estado)])

            c_a, c_b, c_c = st.columns(3)
            with c_a:
                render_metric_red("🔴", _punch_count("A"), "Cat A — Crítico")
            with c_b:
                render_metric("🟡", _punch_count("B"), "Cat B — Não Crítico")
            with c_c:
                render_metric("⚫", _punch_count("C"), "Cat C — Cosmético")

            if _punch_count("A") > 0:
                st.error("🔴 Existem Punch Items **Cat A** abertos — "
                    "o Handover está BLOQUEADO até serem resolvidos.")

            st.markdown("<br>", unsafe_allow_html=True)

            sub_p1, sub_p2 = st.tabs(["➕ Novo Item", "📋 Lista"])

            with sub_p1:
                with st.form("punch_add"):
                    pp1, pp2 = st.columns(2)
                    with pp1:
                        p_tag = st.selectbox("Tag associada",
                            ["Geral"]+insts['Tag'].tolist() if not insts.empty else ["Geral"],
                            key="punch_tag")
                        p_cat = st.selectbox("Categoria",
                            ["A — Crítico (bloqueia handover)",
                             "B — Não crítico",
                             "C — Cosmético / documentação"],
                            key="punch_cat")
                        p_resp = st.text_input("Responsável",
                            value=st.session_state.get('user',''), key="punch_resp")
                    with pp2:
                        p_desc = st.text_area("Descrição *", height=100, key="punch_desc")
                        p_prazo = st.date_input("Prazo",
                            value=date.today()+timedelta(days=7), key="punch_prazo")

                    if st.form_submit_button("➕ Registar Punch Item",
                            use_container_width=True):
                        if not p_desc.strip():
                            st.error("Descrição obrigatória.")
                        else:
                            cat_letra = p_cat[0]
                            novo_p = pd.DataFrame([{
                                "ID": "P"+_uuid_inst.uuid4().hex[:8].upper(),
                                "Tag": p_tag, "Obra": obra_sel,
                                "Categoria": cat_letra,
                                "Descricao": p_desc.strip(),
                                "Responsavel": p_resp,
                                "Prazo": str(p_prazo),
                                "Status": "Aberto",
                                "DataCriacao": datetime.now().strftime('%d/%m/%Y %H:%M'),
                                "DataFecho": "",
                            }])
                            _save_inst(pd.concat([punch, novo_p], ignore_index=True),
                                obra_key, "punch")
                            inv()
                            st.success("✅ Punch item registado!")
                            st.rerun()

            with sub_p2:
                if punch.empty:
                    st.success("✅ Punch List limpa! Boa obra.")
                else:
                    f_pcat = st.multiselect("Filtrar categoria",
                        ["A","B","C"], default=["A","B","C"], key="punch_f_cat")
                    f_pest = st.multiselect("Estado",
                        ["Aberto","Fechado"], default=["Aberto"], key="punch_f_est")

                    df_punch_show = punch.copy()
                    if f_pcat:
                        df_punch_show = df_punch_show[df_punch_show['Categoria'].isin(f_pcat)]
                    if f_pest:
                        df_punch_show = df_punch_show[df_punch_show['Status'].isin(f_pest)]

                    for _, p_row in df_punch_show.iterrows():
                        cat = p_row.get('Categoria','C')
                        cls_p = {'A':'punch-a','B':'punch-b','C':'punch-c'}.get(cat,'punch-c')
                        ic_p  = {'A':'🔴','B':'🟡','C':'⚫'}.get(cat,'⚫')
                        est_p = p_row.get('Status','Aberto')

                        col_punch, col_fechar = st.columns([5,1])
                        with col_punch:
                            st.markdown(
                                f"<div class='punch-card {cls_p}'>"
                                f"<b>{ic_p} Cat {cat} — {p_row.get('Tag','Geral')}</b> "
                                f"<small style='color:#7A8BA6'>({est_p})</small><br>"
                                f"{p_row.get('Descricao','—')}<br>"
                                f"<small style='color:#9CA3AF'>👤 {p_row.get('Responsavel','—')} "
                                f"| 📅 Prazo: {p_row.get('Prazo','—')}</small>"
                                f"</div>",
                                unsafe_allow_html=True)
                        with col_fechar:
                            if est_p == "Aberto":
                                if st.button("✅", key=f"punch_fechar_{p_row.get('ID','')}",
                                        help="Fechar item"):
                                    punch_upd = punch.copy()
                                    punch_upd.loc[punch_upd['ID']==p_row['ID'],
                                        'Status'] = 'Fechado'
                                    punch_upd.loc[punch_upd['ID']==p_row['ID'],
                                        'DataFecho'] = datetime.now().strftime('%d/%m/%Y')
                                    _save_inst(punch_upd, obra_key, "punch")
                                    inv()
                                    st.rerun()

    # ══════════════════════════════════════════════════════════
    # TAB 7 — HANDOVER DOSSIER (Admin)
    # ══════════════════════════════════════════════════════════
    if tab7_visivel:
        with tab7:
            st.markdown('<div class="section-title">📄 Handover Dossier</div>',
                unsafe_allow_html=True)

            punch_a_abertos = _punch_count("A") if not punch.empty else 0
            if punch_a_abertos > 0:
                st.error(f"🔴 **HANDOVER BLOQUEADO** — {punch_a_abertos} Punch Item(s) "
                    f"Cat A por fechar.")
            else:
                st.success("✅ Punch List Cat A limpa — Handover desbloqueado!")

            st.markdown("<br>", unsafe_allow_html=True)

            total = len(insts) if not insts.empty else 0
            if total > 0:
                p_mat  = round(100 * len(insts[insts['Status'].isin(['1','2','3','4'])]) / total)
                p_cal  = round(100 * len(insts[insts['Status'].isin(['2','3','4'])]) / total)
                p_inst = round(100 * len(insts[insts['Status'].isin(['3','4'])]) / total)

                st.markdown(f"""
<div style='background:white;border-radius:16px;padding:20px;border:1px solid #E5EDFF;margin-bottom:16px;'>
  <div style='font-weight:700;color:#0A2463;margin-bottom:12px;'>Progresso da Obra</div>
  <div style='margin-bottom:8px;'>
    <div style='display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:3px;'>
      <span>📦 Material</span><span style='font-weight:700;'>{p_mat}%</span>
    </div>
    <div style='background:#E5EDFF;border-radius:6px;height:8px;'>
      <div style='background:linear-gradient(90deg,#3E92CC,#0A2463);height:8px;
        border-radius:6px;width:{p_mat}%;'></div>
    </div>
  </div>
  <div style='margin-bottom:8px;'>
    <div style='display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:3px;'>
      <span>🔬 Calibração</span><span style='font-weight:700;'>{p_cal}%</span>
    </div>
    <div style='background:#E5EDFF;border-radius:6px;height:8px;'>
      <div style='background:linear-gradient(90deg,#27AE60,#1A7A45);height:8px;
        border-radius:6px;width:{p_cal}%;'></div>
    </div>
  </div>
  <div>
    <div style='display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:3px;'>
      <span>🏗️ Instalação</span><span style='font-weight:700;'>{p_inst}%</span>
    </div>
    <div style='background:#E5EDFF;border-radius:6px;height:8px;'>
      <div style='background:linear-gradient(90deg,#E67E22,#C0392B);height:8px;
        border-radius:6px;width:{p_inst}%;'></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            if not insts.empty:
                hd_tag = st.selectbox("Gerar dossier para instrumento",
                    ["— Todos —"] + insts['Tag'].tolist(), key="hd_tag_sel")

                if st.button("📄 Gerar Handover Dossier PDF",
                        use_container_width=True, type="primary", key="hd_gerar"):
                    try:
                        tags_dossier = insts['Tag'].tolist() if hd_tag == "— Todos —" \
                            else [hd_tag]
                        pdf_hd = _gerar_handover_pdf(
                            tags_dossier, insts, itr_a, itr_b, punch,
                            obra_sel, obra_cod)
                        fname = (f"Handover_{obra_key}_"
                            f"{'COMPLETO' if hd_tag=='— Todos —' else hd_tag}_"
                            f"{datetime.now().strftime('%Y%m%d')}.pdf")
                        st.download_button(
                            label="⬇️ Descarregar Handover Dossier",
                            data=pdf_hd,
                            file_name=fname,
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"Erro ao gerar dossier: {e}")


# ═══════════════════════════════════════════════════════════════
# FUNÇÕES PDF
# ═══════════════════════════════════════════════════════════════

def _gerar_etiquetas_zebra(df_inst, obra, cod_obra):
    """Gera PDF com etiquetas 50×30mm para impressora Zebra."""
    from reportlab.lib.pagesizes import landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib.units import mm

    LAB_W = 50 * mm
    LAB_H = 30 * mm
    COLS  = 3

    buf = io.BytesIO()

    doc = SimpleDocTemplate(buf,
        pagesize=(210*mm, 297*mm),
        leftMargin=5*mm, rightMargin=5*mm,
        topMargin=5*mm, bottomMargin=5*mm)

    from reportlab.graphics import renderPM as _rPM
    from reportlab.platypus import Image as _RLI, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors

    NAVY = colors.HexColor('#0A2463')
    GREY = colors.HexColor('#7A8BA6')

    ts_tag  = ParagraphStyle('ET', fontSize=9, fontName='Helvetica-Bold',
        textColor=NAVY, leading=10)
    ts_desc = ParagraphStyle('ED', fontSize=6, textColor=GREY, leading=7)
    ts_obra = ParagraphStyle('EO', fontSize=5, textColor=GREY, leading=6)

    etiquetas = []
    for _, row in df_inst.iterrows():
        tag  = str(row.get('Tag','?'))
        desc = str(row.get('Descricao',''))[:30]
        tipo_cor = TIPOS_TAG.get(row.get('Tipo','XX'), ("","#7F8C8D"))[1]

        qr_data = f"GESTNOW|INST|{tag}|{obra}|{row.get('ID','')}"
        qr_el = Paragraph(f"<b>{tag}</b>",
            ParagraphStyle('QRF', fontSize=6, textColor=GREY))
        try:
            qr_draw = _qr_drawing(qr_data, size_cm=1.8)
            qr_png  = io.BytesIO()
            _rPM.drawToFile(qr_draw, qr_png, fmt='PNG', dpi=150)
            qr_png.seek(0)
            qr_el = _RLI(qr_png, width=18*mm, height=18*mm)
        except Exception:
            pass

        txt_cell = [
            Paragraph(tag, ts_tag),
            Paragraph(desc, ts_desc),
            Spacer(1, 1*mm),
            Paragraph(f"{obra} | {cod_obra}", ts_obra),
        ]

        etiquetas.append([qr_el, txt_cell])

    all_rows = []
    row_curr = []
    for i, et in enumerate(etiquetas):
        inner = Table([et], colWidths=[20*mm, 28*mm])
        inner.setStyle(TableStyle([
            ('VALIGN',  (0,0),(-1,-1),'MIDDLE'),
            ('BOX',     (0,0),(-1,-1), 0.5, colors.HexColor('#E5EDFF')),
            ('LEFTPADDING', (0,0),(-1,-1), 2),
            ('RIGHTPADDING',(0,0),(-1,-1), 2),
            ('TOPPADDING',  (0,0),(-1,-1), 2),
            ('BOTTOMPADDING',(0,0),(-1,-1), 2),
        ]))
        row_curr.append(inner)
        if len(row_curr) == COLS or i == len(etiquetas)-1:
            while len(row_curr) < COLS:
                row_curr.append("")
            all_rows.append(row_curr)
            row_curr = []

    if all_rows:
        tbl = Table(all_rows,
            colWidths=[50*mm]*COLS,
            rowHeights=[30*mm]*len(all_rows))
        tbl.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('ALIGN', (0,0),(-1,-1),'CENTER'),
        ]))
        doc.build([tbl])

    buf.seek(0)
    return buf.read()


def _gerar_handover_pdf(tags, insts, itr_a, itr_b, punch, obra, cod_obra):
    """Gera PDF de Handover Dossier com histórico completo por instrumento."""
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
        Table, TableStyle, PageBreak)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=2*cm)

    NAVY  = colors.HexColor('#0A2463')
    GREY  = colors.HexColor('#7A8BA6')
    LGREY = colors.HexColor('#F8FAFF')
    GREEN = colors.HexColor('#10B981')
    RED   = colors.HexColor('#EF4444')

    ts_h1  = ParagraphStyle('H1', fontSize=16, fontName='Helvetica-Bold',
        textColor=NAVY, spaceAfter=4)
    ts_h2  = ParagraphStyle('H2', fontSize=11, fontName='Helvetica-Bold',
        textColor=NAVY, spaceBefore=10, spaceAfter=4)
    ts_h3  = ParagraphStyle('H3', fontSize=9,  fontName='Helvetica-Bold',
        textColor=GREY, spaceBefore=6, spaceAfter=3)
    ts_body= ParagraphStyle('B',  fontSize=8,  textColor=NAVY)
    ts_tiny= ParagraphStyle('T',  fontSize=7,  textColor=GREY, alignment=1)

    el = []

    el.append(Spacer(1, 2*cm))
    el.append(Paragraph("HANDOVER DOSSIER", ts_h1))
    el.append(Paragraph(f"Obra: {obra} | Código: {cod_obra}", ts_h2))
    el.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"GESTNOW v3 | {len(tags)} instrumento(s)",
        ParagraphStyle('sub', fontSize=8, textColor=GREY)))
    el.append(Spacer(1, 0.5*cm))

    total = len(insts) if not insts.empty else 0
    n_conc = len(insts[insts['Status'].isin(['3','4'])]) if not insts.empty else 0
    punch_a = len(punch[(punch['Categoria']=='A')&(punch['Status']=='Aberto')]) \
        if not punch.empty else 0

    sum_data = [
        ['Total Instrumentos', str(total)],
        ['Instalados/Concluídos', str(n_conc)],
        ['Punch Cat A Abertos', str(punch_a)],
        ['Estado Handover', '✅ APROVADO' if punch_a==0 else '🔴 BLOQUEADO'],
    ]
    tbl_sum = Table(sum_data, colWidths=[8*cm, 8*cm])
    tbl_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), LGREY),
        ('FONTSIZE',   (0,0),(-1,-1), 8),
        ('GRID',       (0,0),(-1,-1), 0.3, colors.HexColor('#DDE6F5')),
        ('FONTNAME',   (0,0),(0,-1),  'Helvetica-Bold'),
        ('TOPPADDING', (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING', (0,0),(-1,-1),6),
    ]))
    el.append(tbl_sum)
    el.append(PageBreak())

    for tag in tags:
        inst_rows = insts[insts['Tag']==tag] if not insts.empty else pd.DataFrame()
        if inst_rows.empty:
            continue
        inst = inst_rows.iloc[0]
        _, cor_hex = TIPOS_TAG.get(inst.get('Tipo','XX'), ("","#0A2463"))
        cor = colors.HexColor(cor_hex)

        el.append(Paragraph(f"🔧 {tag}", ts_h2))
        el.append(Paragraph(
            f"{inst.get('Descricao','—')} | {inst.get('Fabricante','')} "
            f"{inst.get('Modelo','')} | P&ID: {inst.get('PID_Ref','')}",
            ts_body))

        itr_a_tag = itr_a[itr_a['Tag']==tag] if not itr_a.empty else pd.DataFrame()
        el.append(Paragraph("Calibração (ITR-A)", ts_h3))
        if not itr_a_tag.empty:
            ia = itr_a_tag.iloc[0]
            pf_cor = GREEN if ia.get('PassFail','')=='PASS' else RED
            ia_data = [
                ['Data', ia.get('DataCalibracao','—'),
                 'Resultado', ia.get('PassFail','—')],
                ['Range', f"{ia.get('RangeMin','')}–{ia.get('RangeMax','')} {ia.get('Unidade','')}",
                 'Desvio', f"{ia.get('Desvio','')}%"],
                ['Instrumentista', ia.get('Instrumentista','—'), 'Obs', ia.get('Observacoes','')[:40]],
            ]
            tbl_ia = Table(ia_data, colWidths=[3*cm,5.7*cm,2.5*cm,5.2*cm])
            tbl_ia.setStyle(TableStyle([
                ('FONTSIZE',  (0,0),(-1,-1),7),
                ('GRID',      (0,0),(-1,-1),0.3,colors.HexColor('#DDE6F5')),
                ('BACKGROUND',(0,0),(-1,-1),LGREY),
                ('FONTNAME',  (0,0),(0,-1),'Helvetica-Bold'),
                ('FONTNAME',  (2,0),(2,-1),'Helvetica-Bold'),
                ('TOPPADDING',(0,0),(-1,-1),3),
                ('BOTTOMPADDING',(0,0),(-1,-1),3),
                ('LEFTPADDING',(0,0),(-1,-1),4),
            ]))
            el.append(tbl_ia)
        else:
            el.append(Paragraph("— Sem ITR-A registado —",
                ParagraphStyle('na', fontSize=7, textColor=RED)))

        itr_b_tag = itr_b[itr_b['Tag']==tag] if not itr_b.empty else pd.DataFrame()
        el.append(Paragraph("Instalação (ITR-B)", ts_h3))
        if not itr_b_tag.empty:
            ib = itr_b_tag.iloc[0]
            lat_ib = str(ib.get('GPS_Lat',''))
            lon_ib = str(ib.get('GPS_Lng',''))
            gps_str = f"{lat_ib}, {lon_ib} +{ib.get('Elevacao',0)}m" \
                if lat_ib and lat_ib not in ('','nan') else "N/D"
            ib_data = [
                ['Data Instalação', ib.get('DataInstalacao','—'),
                 'Loop Check', ib.get('LoopCheck','—')],
                ['Técnico',    ib.get('Tecnico','—'),
                 'GPS', gps_str],
            ]
            tbl_ib = Table(ib_data, colWidths=[3*cm,5.7*cm,2.5*cm,5.2*cm])
            tbl_ib.setStyle(TableStyle([
                ('FONTSIZE',  (0,0),(-1,-1),7),
                ('GRID',      (0,0),(-1,-1),0.3,colors.HexColor('#DDE6F5')),
                ('BACKGROUND',(0,0),(-1,-1),LGREY),
                ('FONTNAME',  (0,0),(0,-1),'Helvetica-Bold'),
                ('FONTNAME',  (2,0),(2,-1),'Helvetica-Bold'),
                ('TOPPADDING',(0,0),(-1,-1),3),
                ('BOTTOMPADDING',(0,0),(-1,-1),3),
                ('LEFTPADDING',(0,0),(-1,-1),4),
            ]))
            el.append(tbl_ib)
        else:
            el.append(Paragraph("— Sem ITR-B registado —",
                ParagraphStyle('na', fontSize=7, textColor=RED)))

        el.append(Spacer(1, 0.3*cm))
        el.append(Paragraph("─" * 80, ParagraphStyle('sep', fontSize=4, textColor=GREY)))
        el.append(Spacer(1, 0.2*cm))

    el.append(PageBreak())
    el.append(Paragraph(
        f"Documento gerado automaticamente pelo GESTNOW v3 | {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ts_tiny))
    el.append(Paragraph(
        "Este documento constitui o Dossier de Handover da obra e deve ser entregue ao cliente.",
        ts_tiny))

    doc.build(el)
    buf.seek(0)
    return buf.read()


def _gerar_pdf_calibracao(cal_data, tag):
    """Gera PDF com a folha de calibração completa."""
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
        Table, TableStyle, PageBreak)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    import ast

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm)

    NAVY = colors.HexColor('#0A2463')
    GREY = colors.HexColor('#7A8BA6')
    BLACK = colors.black

    ts_title = ParagraphStyle('Title', fontSize=14, fontName='Helvetica-Bold',
        textColor=NAVY, alignment=1, spaceAfter=12)
    ts_h2 = ParagraphStyle('H2', fontSize=11, fontName='Helvetica-Bold',
        textColor=NAVY, spaceAfter=6)
    ts_body = ParagraphStyle('Body', fontSize=8, textColor=BLACK, spaceAfter=3)
    
    el = []
    
    # Título
    el.append(Paragraph("FOLHA DE CALIBRAÇÃO - ITR-A", ts_title))
    el.append(Paragraph(f"Instrumento: {tag}", ts_h2))
    el.append(Spacer(1, 0.5*cm))
    
    # Dados do instrumento
    data_table = [
        ["Marca", cal_data.get('Marca','—'), "Modelo", cal_data.get('Modelo','—')],
        ["Nº Série", cal_data.get('NSerie','—'), "Tipo", cal_data.get('Tipo','—')],
        ["Faixa", f"{cal_data.get('RangeMin','')} – {cal_data.get('RangeMax','')} {cal_data.get('Unidade','')}", "Data", cal_data.get('DataCalibracao','—')],
    ]
    tbl = Table(data_table, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
    tbl.setStyle(TableStyle([
        ('FONTSIZE', (0,0),(-1,-1), 8),
        ('GRID', (0,0),(-1,-1), 0.5, GREY),
        ('BACKGROUND', (0,0),(-1,-1), colors.HexColor('#F8FAFF')),
    ]))
    el.append(tbl)
    el.append(Spacer(1, 0.5*cm))
    
    # Resultado
    pf = cal_data.get('PassFail','')
    pf_text = "APROVADO" if pf == "PASS" else "REPROVADO"
    pf_color = colors.HexColor('#10B981') if pf == "PASS" else colors.HexColor('#EF4444')
    el.append(Paragraph(f"Resultado: {pf_text} | Erro máximo: {cal_data.get('ErroMaximo',0):.2f}%", 
        ParagraphStyle('Result', fontSize=10, fontName='Helvetica-Bold', textColor=pf_color)))
    el.append(Spacer(1, 0.5*cm))
    
    # Assinaturas
    el.append(Paragraph(f"Técnico: {cal_data.get('Instrumentista','—')}", ts_body))
    el.append(Paragraph(f"Responsável: {cal_data.get('Responsavel','—')}", ts_body))
    
    doc.build(el)
    buf.seek(0)
    return buf.read()

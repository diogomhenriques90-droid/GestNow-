"""
GESTNOW v3 — mod_instrumentacao.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Módulo de Gestão de Instrumentação Industrial

Fluxo: P&ID → Hook-Ups → Packing List → Calibração (ITR-A)
       → Instalação+GPS (ITR-B) → Punch List → Handover Dossier

Bibliotecas novas: pdfplumber (requirements.txt)
Tudo o resto já existe no core.py
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

# ── Carregamento dos CSVs próprios deste módulo ───────────────
def _load_inst(obra):
    """Carrega todos os CSVs de instrumentação para uma obra."""
    insts   = load_db(f"inst_{obra}_index.csv",
        ["ID","Tag","Tipo","Descricao","Fabricante","Modelo","PID_Ref",
         "Obra","Unidade","Status","GPS_Lat","GPS_Lng","Elevacao",
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

        # ── Sub: Extrair de P&ID ──────────────────────────────
        with sub_pid:
            st.markdown("#### 📄 Upload P&ID — Extracção Automática de Tags")
            st.caption("Carrega o PDF do P&ID. O sistema extrai todas as tags ISA automaticamente.")

            pid_file = st.file_uploader("Selecciona o PDF do P&ID",
                type=["pdf"], key="inst_pid_upload")

            if pid_file:
                try:
                    import pdfplumber
                    texto_total = ""
                    with pdfplumber.open(pid_file) as pdf:
                        for page in pdf.pages:
                            t = page.extract_text()
                            if t: texto_total += t + "\n"

                    # Regex para tags ISA: PT-101, FT-1234A, LT-002, etc.
                    padrao = r'\b([A-Z]{1,3}[A-Z]?)[- ]?(\d{2,5}[A-Z]?)\b'
                    matches = re.findall(padrao, texto_total)

                    # Filtrar só tipos conhecidos
                    tags_encontradas = []
                    for tipo, num in matches:
                        if tipo in TIPOS_TAG:
                            tag_full = f"{tipo}-{num}"
                            tags_encontradas.append({
                                "tag": tag_full, "tipo": tipo, "num": num
                            })

                    # Deduplicate
                    tags_unicas = list({t['tag']: t for t in tags_encontradas}.values())

                    if tags_unicas:
                        st.success(f"✅ {len(tags_unicas)} tags encontradas no P&ID!")

                        # Preview agrupado por tipo
                        por_tipo = {}
                        for t in tags_unicas:
                            por_tipo.setdefault(t['tipo'], []).append(t['tag'])

                        for tipo, lst in sorted(por_tipo.items()):
                            desc, cor = TIPOS_TAG.get(tipo, ("Outro","#7F8C8D"))
                            st.markdown(
                                f"<span class='inst-tag-badge' style='background:{cor}'>{tipo}</span> "
                                f"**{desc}** — {len(lst)} tags: "
                                f"<small style='color:#7A8BA6'>{', '.join(lst[:8])}"
                                f"{'...' if len(lst)>8 else ''}</small>",
                                unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)

                        # Botão para importar todas
                        if st.button("📥 Importar todas para Instrument Index",
                                use_container_width=True, type="primary",
                                key="inst_importar_pid"):
                            novas = []
                            tags_existentes = insts['Tag'].tolist() if not insts.empty else []
                            adicionadas = 0
                            for t in tags_unicas:
                                if t['tag'] not in tags_existentes:
                                    desc_auto, _ = TIPOS_TAG.get(t['tipo'], ("Instrumento","#7F8C8D"))
                                    novas.append({
                                        "ID": "INST"+_uuid_inst.uuid4().hex[:8].upper(),
                                        "Tag": t['tag'],
                                        "Tipo": t['tipo'],
                                        "Descricao": desc_auto,
                                        "Fabricante": "",
                                        "Modelo": "",
                                        "PID_Ref": pid_file.name,
                                        "Obra": obra_sel,
                                        "Unidade": "",
                                        "Status": "0",
                                        "GPS_Lat": "",
                                        "GPS_Lng": "",
                                        "Elevacao": "",
                                        "Foto_Local_b64": "",
                                        "DataCriacao": datetime.now().strftime('%d/%m/%Y %H:%M'),
                                        "QR_impresso": "0",
                                    })
                                    adicionadas += 1

                            if novas:
                                novo_df = pd.DataFrame(novas)
                                insts_upd = pd.concat([insts, novo_df], ignore_index=True)
                                _save_inst(insts_upd, obra_key, "index")
                                inv()
                                st.success(f"✅ {adicionadas} tags importadas! "
                                    f"({len(tags_unicas)-adicionadas} já existiam)")
                                st.rerun()
                            else:
                                st.info("Todas as tags já existem no Instrument Index.")
                    else:
                        st.warning("Nenhuma tag ISA encontrada. Verifica se o PDF tem texto seleccionável.")
                        st.info("💡 Se o PDF for uma imagem escaneada, usa a tab 'Adicionar Manual'.")

                except ImportError:
                    st.error("❌ `pdfplumber` não está instalado. Adiciona ao requirements.txt e faz deploy.")
                except Exception as e:
                    st.error(f"❌ Erro ao processar PDF: {e}")

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
    # TAB 2 — HOOK-UPS & BOM (Admin / Chefe)
    # ══════════════════════════════════════════════════════════
    if tab2_visivel:
     with tab2:
        st.markdown('<div class="section-title">🔩 Hook-Ups & BOM</div>',
            unsafe_allow_html=True)

        sub_hu1, sub_hu2, sub_hu3 = st.tabs([
            "📄 Upload Hook-Up (PDF)",
            "✏️ BOM Manual",
            "📚 Biblioteca",
        ])

        with sub_hu1:
            st.markdown("#### 📄 Upload e Extracção de BOM do Hook-Up")
            st.info("💡 O sistema tenta extrair a lista de materiais automaticamente. "
                "Podes sempre editar antes de confirmar.")

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

            if hu_file and hu_cod:
                st.markdown("**📋 BOM extraída — revisa antes de guardar:**")
                try:
                    import pdfplumber
                    texto_hu = ""
                    with pdfplumber.open(hu_file) as pdf:
                        for pg in pdf.pages:
                            t = pg.extract_text()
                            if t: texto_hu += t + "\n"

                    # Tentar extrair linhas que parecem BOM
                    # Padrões: "1 off valve block 1/2 SS" ou "2x cable 2x1.5"
                    linhas_bom = []
                    for linha in texto_hu.split('\n'):
                        linha = linha.strip()
                        if len(linha) > 5 and any(
                            c.isdigit() for c in linha[:4]
                        ):
                            linhas_bom.append(linha)

                    if linhas_bom:
                        st.success(f"✅ {len(linhas_bom)} linhas extraídas do PDF")
                        for i, l in enumerate(linhas_bom[:20]):
                            st.text(f"  {l}")
                    else:
                        st.warning("Não foi possível extrair BOM automaticamente. "
                            "Usa a tab 'BOM Manual'.")
                except ImportError:
                    st.error("❌ pdfplumber não instalado.")
                except Exception as e:
                    st.warning(f"Erro na extracção: {e}. Usa BOM Manual.")

            if st.button("💾 Guardar Hook-Up", key="hu_guardar",
                    use_container_width=True):
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
                    inv()
                    st.success(f"✅ Hook-Up {hu_cod} guardado!")
                    st.rerun()

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
    # TAB 3 — PACKING LIST (Admin / Chefe)
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
            st.markdown("#### 📥 Importar Packing List do Cliente")
            st.caption("Importa o CSV do cliente ou regista itens manualmente.")

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
                            type="primary", key="pk_importar"):
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

                            # Se Recebido OK e BOM completa → atualizar status do instrumento
                            if est_rec == "Recebido OK" and not insts.empty:
                                tag_pk = pk_row.get('Tag','')
                                if tag_pk in insts['Tag'].values:
                                    inst_upd = insts.copy()
                                    inst_upd.loc[inst_upd['Tag']==tag_pk, 'Status'] = '1'
                                    _save_inst(inst_upd, obra_key, "index")

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

                    pk_tag_items = packing[packing['Tag']==tag] \
                        if not packing.empty else pd.DataFrame()

                    if pk_tag_items.empty:
                        sem_cls, sem_txt, sem_ic = "sem-cinza", "Sem dados", "⚪"
                    else:
                        todos_ok = all(
                            pk_tag_items['Estado'] == 'Recebido OK')
                        algum_falta = any(
                            pk_tag_items['Estado'] == 'Em falta')
                        if todos_ok:
                            sem_cls, sem_txt, sem_ic = "sem-verde", "Material OK", "🟢"
                        elif algum_falta:
                            sem_cls, sem_txt, sem_ic = "sem-vermelho", "Em Falta", "🔴"
                        else:
                            sem_cls, sem_txt, sem_ic = "sem-amarelo", "Parcial", "🟡"

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
    # TAB 4 — CALIBRAÇÃO ITR-A
    # ══════════════════════════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-title">🔬 Calibração em Bancada — ITR-A</div>',
            unsafe_allow_html=True)

        # Só instrumentos com material OK (status >= 1)
        inst_para_cal = insts[insts['Status'].isin(['1'])] \
            if not insts.empty else pd.DataFrame()
        inst_calibrados = insts[insts['Status'].isin(['2','3','4'])] \
            if not insts.empty else pd.DataFrame()

        sub_cal1, sub_cal2 = st.tabs(["🔬 Calibrar", "📋 Histórico ITR-A"])

        with sub_cal1:
            if inst_para_cal.empty:
                st.info("Sem instrumentos prontos para calibrar. "
                    "Verifica o Packing List — os instrumentos precisam de estar com "
                    "🟢 Material OK.")
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
                    inst_para_cal['Tag'].tolist(), key="cal_tag_sel")

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

                with st.form("cal_form"):
                    st.markdown("**Parâmetros de Calibração:**")
                    ca1, ca2, ca3 = st.columns(3)
                    with ca1:
                        cal_range_min = st.number_input("Range Mín",
                            value=0.0, step=0.1, key="cal_rmin")
                        cal_resultado = st.number_input("Resultado Real",
                            value=0.0, step=0.01, key="cal_res")
                    with ca2:
                        cal_range_max = st.number_input("Range Máx",
                            value=100.0, step=0.1, key="cal_rmax")
                        cal_desvio = st.number_input("Desvio (%)",
                            value=0.0, step=0.001, key="cal_dev")
                    with ca3:
                        cal_unidade = st.text_input("Unidade de Engenharia",
                            placeholder="Ex: mbar, °C, m³/h", key="cal_unid")
                        cal_setpoint = st.number_input("Set Point",
                            value=50.0, step=0.1, key="cal_sp")

                    cal_pass = st.radio("Resultado",
                        ["✅ PASS", "❌ FAIL"], horizontal=True, key="cal_pf")
                    cal_obs = st.text_area("Observações", height=80, key="cal_obs")
                    cal_inst_nome = st.text_input("Instrumentista responsável",
                        value=st.session_state.get('user',''), key="cal_inst")

                    if st.form_submit_button("💾 Registar ITR-A",
                            use_container_width=True, type="primary"):
                        novo_itr = pd.DataFrame([{
                            "ID": "ITRA"+_uuid_inst.uuid4().hex[:8].upper(),
                            "Tag": tag_cal, "Obra": obra_sel,
                            "Instrumentista": cal_inst_nome,
                            "DataCalibracao": datetime.now().strftime('%d/%m/%Y %H:%M'),
                            "RangeMin": cal_range_min, "RangeMax": cal_range_max,
                            "Unidade": cal_unidade, "SetPoint": cal_setpoint,
                            "ResultadoReal": cal_resultado, "Desvio": cal_desvio,
                            "PassFail": "PASS" if "PASS" in cal_pass else "FAIL",
                            "Observacoes": cal_obs, "Assinatura_b64": "",
                        }])
                        _save_inst(pd.concat([itr_a, novo_itr], ignore_index=True),
                            obra_key, "itr_a")

                        # Actualizar status do instrumento
                        if "PASS" in cal_pass:
                            inst_upd = insts.copy()
                            inst_upd.loc[inst_upd['Tag']==tag_cal, 'Status'] = '2'
                            _save_inst(inst_upd, obra_key, "index")

                        inv()
                        st.success(f"✅ ITR-A registado para {tag_cal}!")
                        st.rerun()

        with sub_cal2:
            if itr_a.empty:
                st.info("Sem calibrações registadas.")
            else:
                for _, itr_row in itr_a.sort_values('DataCalibracao',
                        ascending=False).iterrows():
                    pf = itr_row.get('PassFail','')
                    cls_ = "pass" if pf=="PASS" else "fail"
                    ic_  = "✅" if pf=="PASS" else "❌"
                    st.markdown(
                        f"<div class='itr-card {cls_}'>"
                        f"<b>{itr_row.get('Tag','—')}</b> {ic_} {pf} &nbsp;|&nbsp; "
                        f"Range: {itr_row.get('RangeMin','')}–{itr_row.get('RangeMax','')} "
                        f"{itr_row.get('Unidade','')} &nbsp;|&nbsp; "
                        f"Desvio: {itr_row.get('Desvio','')}% &nbsp;|&nbsp; "
                        f"<small style='color:#7A8BA6'>{itr_row.get('Instrumentista','—')} "
                        f"· {itr_row.get('DataCalibracao','—')}</small>"
                        f"</div>",
                        unsafe_allow_html=True)

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

        # ── Sub: Marcar localização ────────────────────────────
        with sub_it1:
            st.markdown("#### 📍 Levantamento de Posições — Chefe vai ao Terreno")
            st.caption("Vai ao local de cada instrumento, captura o GPS e define a elevação. "
                "Os técnicos seguirão estas coordenadas.")

            # GPS JS
            gps_inst_html = """
<div id="gps-inst-status" style="color:#7A8BA6;font-size:.82rem;padding:.3rem 0;
  background:#F0F9FF;border-radius:8px;padding:8px 12px;margin-bottom:8px;">
  📍 A obter GPS...
</div>
<script>
(function(){
  if(!navigator.geolocation){
    document.getElementById('gps-inst-status').textContent='⚠️ GPS não suportado';return;
  }
  navigator.geolocation.getCurrentPosition(
    function(pos){
      var lat=pos.coords.latitude.toFixed(6);
      var lon=pos.coords.longitude.toFixed(6);
      var acc=Math.round(pos.coords.accuracy);
      document.getElementById('gps-inst-status').innerHTML=
        '📍 GPS: <b style="color:#0A2463">'+lat+', '+lon+'</b> (±'+acc+'m)';
      document.getElementById('gps-inst-status').style.color='#059669';
      var url=new URL(window.location.href);
      url.searchParams.set('inst_lat',lat);
      url.searchParams.set('inst_lon',lon);
      window.history.replaceState({},'',url);
    },
    function(err){
      document.getElementById('gps-inst-status').innerHTML=
        '⚠️ GPS indisponível: '+err.message;
      document.getElementById('gps-inst-status').style.color='#D97706';
    },
    {enableHighAccuracy:true,timeout:10000}
  );
})();
</script>"""
            st.components.v1.html(gps_inst_html, height=50)
            gps_lat = st.query_params.get("inst_lat","")
            gps_lon = st.query_params.get("inst_lon","")

            # Instrumentos sem GPS
            sem_gps = insts[
                (insts['GPS_Lat'].isna() | (insts['GPS_Lat']=='') | (insts['GPS_Lat']=='nan'))
            ] if not insts.empty else pd.DataFrame()

            if sem_gps.empty:
                st.success("✅ Todos os instrumentos têm localização GPS!")
            else:
                st.caption(f"{len(sem_gps)} instrumento(s) sem GPS.")
                tag_gps = st.selectbox("Instrumento a localizar",
                    sem_gps['Tag'].tolist(), key="gps_tag_sel")

                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1:
                    lat_man = st.text_input("Latitude",
                        value=gps_lat, key="gps_lat_man")
                with col_g2:
                    lon_man = st.text_input("Longitude",
                        value=gps_lon, key="gps_lon_man")
                with col_g3:
                    elev_man = st.number_input("Elevação (m)",
                        value=0.0, step=0.5,
                        help="0m=piso 0, 6m=plataforma 1, 12m=plataforma 2",
                        key="gps_elev_man")

                obs_local = st.text_area("Notas do local",
                    placeholder="Ex: Entre linha P-101 e coluna C-14, face norte",
                    height=60, key="gps_obs_man")

                if st.button("📍 Guardar Localização",
                        use_container_width=True, type="primary", key="gps_guardar"):
                    if not lat_man or not lon_man:
                        st.error("Latitude e Longitude obrigatórias.")
                    else:
                        inst_upd = insts.copy()
                        inst_upd.loc[inst_upd['Tag']==tag_gps, 'GPS_Lat'] = lat_man
                        inst_upd.loc[inst_upd['Tag']==tag_gps, 'GPS_Lng'] = lon_man
                        inst_upd.loc[inst_upd['Tag']==tag_gps, 'Elevacao'] = elev_man
                        _save_inst(inst_upd, obra_key, "index")
                        inv()
                        st.success(f"✅ {tag_gps} localizado — {lat_man}, {lon_man} (+{elev_man}m)")
                        st.rerun()

        # ── Sub: Registar instalação ───────────────────────────
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
                    with it2:
                        it_obs = st.text_area("Observações", height=80, key="itb_obs")

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

        # ── Sub: Mapa ──────────────────────────────────────────
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

        # Contadores por categoria
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

        # Check punch cat A
        punch_a_abertos = _punch_count("A") if not punch.empty else 0
        if punch_a_abertos > 0:
            st.error(f"🔴 **HANDOVER BLOQUEADO** — {punch_a_abertos} Punch Item(s) "
                f"Cat A por fechar.")
        else:
            st.success("✅ Punch List Cat A limpa — Handover desbloqueado!")

        st.markdown("<br>", unsafe_allow_html=True)

        # Dashboard de progresso
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
    """
    Gera PDF com etiquetas 50×30mm para impressora Zebra.
    Layout: QR Code à esquerda, Tag + Descrição à direita.
    """
    from reportlab.lib.pagesizes import landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib.units import mm

    LAB_W = 50 * mm
    LAB_H = 30 * mm
    COLS  = 3  # etiquetas por linha em A4

    buf = io.BytesIO()

    # Página A4 landscape para caber 3 etiquetas por linha
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

        # QR Code
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

    # Agrupar em linhas de 1 etiqueta (tabela simples)
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

    # Capa
    el.append(Spacer(1, 2*cm))
    el.append(Paragraph("HANDOVER DOSSIER", ts_h1))
    el.append(Paragraph(f"Obra: {obra} | Código: {cod_obra}", ts_h2))
    el.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"GESTNOW v3 | {len(tags)} instrumento(s)",
        ParagraphStyle('sub', fontSize=8, textColor=GREY)))
    el.append(Spacer(1, 0.5*cm))

    # Sumário
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

    # Ficha por instrumento
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

        # Calibração
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

        # Instalação
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

    # Rodapé final
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

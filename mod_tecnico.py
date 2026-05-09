import streamlit as st
import pandas as pd
import uuid, secrets, base64, io, json
from datetime import datetime, timedelta, date
from streamlit_drawable_canvas import st_canvas
import time

from core import (
    save_db, inv, fh, sl, load_db, canvas_to_b64,
    ICONS, COLORS, TIPOS_FRENTE, REGRAS_OURO,
    log_audit, criar_notificacao, process_and_compress_image,
    _gcs_read, hp
)
from translations import t

_STATUS_CSS = {
    "0": "pendente", "1": "aprovado", "2": "fechado",
    "-1": "fechado", "3": "fechado", "4": "fechado"
}

_DIAS_PT = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']

def _load_users_fresh():
    for tentativa in range(3):
        try:
            buf = _gcs_read("usuarios.csv")
            if buf:
                df = pd.read_csv(buf, dtype=str, on_bad_lines='skip', encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].str.strip()
                return df.fillna("")
            time.sleep(0.3)
        except:
            if tentativa == 2: return pd.DataFrame()
            time.sleep(0.3)
    return pd.DataFrame()

def render_tecnico(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    user_nome  = st.session_state.get('user', '')
    cargo_user = st.session_state.get('cargo', 'Técnico')
    user_tipo  = st.session_state.get('tipo',  'Técnico')

    is_chefe = (user_tipo in ['Chefe de Equipa','Admin','Gestor'] or
                cargo_user in ['Chefe de Equipa','Encarregado'])

    # Carregar dados frescos do utilizador
    try:
        users_fresh = _load_users_fresh()
        user_match  = users_fresh[users_fresh['Nome'] == user_nome]
        user_data   = user_match.iloc[0] if not user_match.empty else None
        user_idx    = user_match.index[0] if not user_match.empty else None
    except:
        user_data = None
        user_idx  = None

    # Header
    st.markdown(f"""
    <div style="text-align:center;padding:25px 20px;
        background:linear-gradient(135deg,#1E293B,#0F172A);
        border-radius:20px;margin-bottom:25px;
        border:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:2.5rem;margin-bottom:8px;">{ICONS["technician"]}</div>
        <div style="font-size:1.6rem;font-weight:800;color:#F8FAFC;">{user_nome}</div>
        <div style="font-size:0.9rem;color:#94A3B8;">{cargo_user} | {user_tipo}</div>
    </div>
    """, unsafe_allow_html=True)

    # CSS
    st.markdown("""
    <style>
    /* Cards */
    .rp-card {
        background:rgba(255,255,255,0.05); padding:15px; border-radius:12px;
        border-left:5px solid #3B82F6; margin-bottom:10px;
    }
    .rp-card.pendente  { border-left-color:#F59E0B; }
    .rp-card.aprovado  { border-left-color:#10B981; }
    .rp-card.fechado   { border-left-color:#3B82F6; }

    /* Calendário */
    .cal-nav-btn button {
        background: rgba(255,255,255,0.1) !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        font-size: 1.2rem !important; padding: 8px !important;
    }
    .cal-semana {
        text-align:center; color:#60A5FA; font-weight:600;
        font-size:0.95rem; padding:10px 0;
    }

    /* Dias */
    div[data-testid="column"] .stButton > button {
        font-size: 0.75rem !important;
        padding: 6px 2px !important;
        border-radius: 10px !important;
        min-height: 52px !important;
        line-height: 1.3 !important;
    }

    /* Esign */
    .esign-seal {
        border:2px dashed #10B981; padding:15px;
        background:rgba(16,185,129,0.1); border-radius:10px;
        color:#10B981; font-family:monospace; font-size:0.85rem; margin-top:15px;
    }
    .pedido-card {
        background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.3);
        border-radius:10px; padding:12px; margin-bottom:8px;
    }

    /* Labels globais */
    .stTextInput label, .stNumberInput label, .stTextArea label,
    .stSelectbox label, .stDateInput label, .stTimeInput label,
    .stRadio label, .stCheckbox label {
        color:#F8FAFC !important; font-weight:500;
    }
    .stTextInput > div > div > input, .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background:#FFFFFF !important; color:#1E293B !important;
    }
    .stSelectbox > div > div > div { background:#FFFFFF !important; color:#1E293B !important; }
    h1,h2,h3,h4,h5,h6 { color:#F8FAFC !important; }
    .streamlit-expanderHeader { color:#F8FAFC !important; }
    .stTabs [data-baseweb="tab"] { color:#F8FAFC !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { font-weight:bold; }
    </style>
    """, unsafe_allow_html=True)

    # Tabs
    menu = [f"{ICONS['dashboard']} Pontos", f"{ICONS['safety']} HSE",
            f"{ICONS['profile']} Perfil", f"{ICONS['material']} Pedidos"]
    if is_chefe:
        menu.insert(1, f"{ICONS['reports']} Folha de Ponto")

    tabs = st.tabs(menu)

    # ═══════════════════════════════════════════════════════════════
    # TAB 0: REGISTO DE PONTO — CALENDÁRIO NOVO
    # ═══════════════════════════════════════════════════════════════
    with tabs[0]:
        hoje = date.today()

        # Inicializar estado da semana
        if 'data_consulta' not in st.session_state:
            st.session_state.data_consulta = hoje
        if 'semana_offset' not in st.session_state:
            st.session_state.semana_offset = 0

        # Calcular início da semana com offset
        data_ref   = hoje + timedelta(weeks=st.session_state.semana_offset)
        inicio_sem = data_ref - timedelta(days=data_ref.weekday())
        fim_sem    = inicio_sem + timedelta(days=6)
        dias_sem   = [inicio_sem + timedelta(days=i) for i in range(7)]

        # ── Navegação entre semanas ───────────────────────────────
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.05);border-radius:15px;
            padding:12px 15px;margin-bottom:15px;">
            <p style="text-align:center;color:#60A5FA;font-weight:600;
                font-size:1rem;margin:0;">
                📅 {inicio_sem.strftime('%d %b')} — {fim_sem.strftime('%d %b %Y')}
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_prev, col_hoje_btn, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Ant.", use_container_width=True, key="sem_prev"):
                st.session_state.semana_offset -= 1
                # Manter data_consulta na semana nova
                novo_inicio = inicio_sem - timedelta(weeks=1)
                st.session_state.data_consulta = novo_inicio + timedelta(
                    days=st.session_state.data_consulta.weekday()
                )
                st.rerun()
        with col_hoje_btn:
            if st.button("📅 Hoje", use_container_width=True, key="sem_hoje", type="secondary"):
                st.session_state.semana_offset  = 0
                st.session_state.data_consulta  = hoje
                st.rerun()
        with col_next:
            if st.button("Próx. →", use_container_width=True, key="sem_next"):
                st.session_state.semana_offset += 1
                novo_inicio = inicio_sem + timedelta(weeks=1)
                st.session_state.data_consulta = novo_inicio + timedelta(
                    days=st.session_state.data_consulta.weekday()
                )
                st.rerun()

        # ── 7 botões de dias ────────────────────────────────────────
        day_cols = st.columns(7)
        for col, d in zip(day_cols, dias_sem):
            with col:
                selecionado = d == st.session_state.data_consulta
                eh_hoje     = d == hoje
                dia_pt      = _DIAS_PT[d.weekday()]
                # Contar registos do dia
                n_regs = 0
                if not registos_db.empty and 'Técnico' in registos_db.columns:
                    ru = registos_db[registos_db['Técnico'] == user_nome]
                    if not ru.empty:
                        datas = pd.to_datetime(ru['Data'], dayfirst=True, errors='coerce').dt.date
                        n_regs = int((datas == d).sum())

                # Indicador visual de registos
                indicador = f"\n{'🟢' if n_regs > 0 else '·'}"

                label = f"{dia_pt}\n{d.day}{indicador}"

                if st.button(label, key=f"day_{d.strftime('%Y%m%d')}",
                             use_container_width=True,
                             type="primary" if selecionado else "secondary"):
                    st.session_state.data_consulta = d
                    st.rerun()

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        # ── Registos do dia selecionado ───────────────────────────
        data_sel    = st.session_state.data_consulta
        data_label  = data_sel.strftime('%A, %d de %B').capitalize()
        eh_hoje_sel = data_sel == hoje

        st.markdown(f"### {'📍 ' if eh_hoje_sel else ''}Registos — {data_sel.strftime('%d/%m/%Y')}")

        regs_dia = pd.DataFrame()
        if not registos_db.empty and 'Técnico' in registos_db.columns:
            meus = registos_db[registos_db['Técnico'] == user_nome]
            if not meus.empty:
                datas_parse = pd.to_datetime(meus['Data'], dayfirst=True, errors='coerce').dt.date
                regs_dia    = meus[datas_parse == data_sel]

        if not regs_dia.empty:
            total_dia = pd.to_numeric(regs_dia['Horas_Total'], errors='coerce').fillna(0).sum()
            st.markdown(f"**Total: {fh(total_dia)}**")
            for _, r in regs_dia.iterrows():
                status_info  = sl(r.get('Status','0'))
                cor_status   = status_info[3]
                texto_status = status_info[0]
                classe_card  = _STATUS_CSS.get(str(r.get('Status','0')), 'pendente')
                periodo_info = f" (P{r.get('Periodo',1)})" if str(r.get('Periodo','1')) != "1" else ""
                relatorio_t  = str(r.get("Relatorio",""))[:80]
                st.markdown(
                    f'<div class="rp-card {classe_card}">'
                    f'<b>{r.get("Obra","")}{periodo_info}</b> | {r.get("Turnos","")} '
                    f'(<b>{fh(r.get("Horas_Total",0))}</b>)<br>'
                    f'<small style="color:#94A3B8;">{r.get("Frente","")} · {relatorio_t}</small><br>'
                    f'<small style="color:{cor_status};">{texto_status}</small>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03);padding:20px;
                border-radius:12px;text-align:center;border:1px dashed rgba(255,255,255,0.1);">
                <p style="color:#64748B;margin:0;">Sem registos neste dia</p>
            </div>""", unsafe_allow_html=True)

        # ── Formulário de registo ─────────────────────────────────
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        with st.expander(f"➕ Registar horas em {data_sel.strftime('%d/%m/%Y')}", expanded=False):
            st.markdown("#### ⏱️ Períodos de Trabalho")

            if 'periodos_trabalho' not in st.session_state:
                st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"17:00"}]

            if st.button("➕ Adicionar Período", use_container_width=True,
                         type="secondary", key="add_periodo"):
                st.session_state.periodos_trabalho.append({"entrada":"13:00","saida":"17:00"})
                st.rerun()

            with st.form("ponto_form"):
                obras_list = obras_db['Obra'].unique() if not obras_db.empty else ["Geral"]
                col1, col2 = st.columns(2)
                with col1:
                    obra   = st.selectbox("🏗️ Obra",   obras_list,   key="reg_obra")
                with col2:
                    frente = st.selectbox("🔧 Frente", TIPOS_FRENTE, key="reg_frente")

                total_horas_dia = 0.0
                for idx, periodo in enumerate(st.session_state.periodos_trabalho):
                    st.markdown(f"**Período {idx + 1}**")
                    col_e, col_s = st.columns(2)
                    with col_e:
                        entrada = st.time_input(f"Entrada {idx+1}",
                            value=datetime.strptime(periodo["entrada"], "%H:%M").time(),
                            key=f"period_{idx}_entrada")
                    with col_s:
                        saida = st.time_input(f"Saída {idx+1}",
                            value=datetime.strptime(periodo["saida"], "%H:%M").time(),
                            key=f"period_{idx}_saida")
                    t1 = datetime.combine(date.today(), entrada)
                    t2 = datetime.combine(date.today(), saida)
                    delta_h = round(max((t2 - t1).seconds / 3600, 0), 2)
                    total_horas_dia += delta_h
                    st.markdown("---")

                if total_horas_dia > 0:
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.1);border:2px solid #10B981;
                        border-radius:10px;padding:12px;margin:10px 0;">
                        <p style="margin:0;color:#10B981;font-weight:bold;">
                            ⏱️ Total: {total_horas_dia:.2f}h
                        </p>
                    </div>""", unsafe_allow_html=True)

                relat = st.text_area("📝 Relatório (opcional)",
                    placeholder="Descreve o trabalho realizado...", key="reg_relatorio")

                if st.form_submit_button("💾 Gravar Registo",
                                          use_container_width=True, type="primary"):
                    if total_horas_dia <= 0:
                        st.error("⚠️ Regista pelo menos um período válido.")
                    else:
                        for idx, periodo in enumerate(st.session_state.periodos_trabalho):
                            entrada_v = st.session_state.get(f"period_{idx}_entrada") or \
                                        datetime.strptime(periodo["entrada"], "%H:%M").time()
                            saida_v   = st.session_state.get(f"period_{idx}_saida") or \
                                        datetime.strptime(periodo["saida"],   "%H:%M").time()
                            t1 = datetime.combine(date.today(), entrada_v)
                            t2 = datetime.combine(date.today(), saida_v)
                            delta_h = round(max((t2 - t1).seconds / 3600, 0), 2)
                            if delta_h > 0:
                                new_r = pd.DataFrame([{
                                    "ID":         str(uuid.uuid4())[:8].upper(),
                                    "Data":       data_sel.strftime("%d/%m/%Y"),
                                    "Técnico":    user_nome,
                                    "Obra":       obra,
                                    "Frente":     frente,
                                    "Turnos":     f"{entrada_v.strftime('%H:%M')}-{saida_v.strftime('%H:%M')}",
                                    "Horas_Total":delta_h,
                                    "Relatorio":  relat,
                                    "Status":     "0",
                                    "Periodo":    idx + 1
                                }])
                                updated = pd.concat([registos_db, new_r], ignore_index=True) \
                                          if not registos_db.empty else new_r
                                save_db(updated, "registos.csv")
                                log_audit(usuario=user_nome, acao="REGISTAR_PONTO",
                                          tabela="registos.csv",
                                          registro_id=new_r['ID'].iloc[0],
                                          detalhes=f"{delta_h}h em {obra}", ip="")

                        st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"17:00"}]
                        inv()
                        st.success(f"✅ Ponto registado! ({total_horas_dia:.2f}h)")
                        st.rerun()

    # ═══════════════════════════════════════════════════════════════
    # TAB FOLHA DE PONTO (só chefe)
    # ═══════════════════════════════════════════════════════════════
    offset = 0
    if is_chefe:
        offset = 1
        with tabs[1]:
            st.markdown(f"### {ICONS['reports']} Folha de Ponto & Assinatura Digital")

            obra_f = st.selectbox("Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Sem Obras"],
                key="esign_obra")

            inicio_sem_d = hoje - timedelta(days=hoje.weekday())
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                semana_inicio = st.date_input("Início", value=inicio_sem_d, key="fp_inicio")
            with col_p2:
                semana_fim    = st.date_input("Fim",
                    value=inicio_sem_d + timedelta(days=6), key="fp_fim")

            if not registos_db.empty:
                regs_fp = registos_db[
                    (registos_db['Obra'] == obra_f) &
                    (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date >= semana_inicio) &
                    (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date <= semana_fim)
                ]
                if not regs_fp.empty:
                    for tec in regs_fp['Técnico'].unique():
                        regs_t = regs_fp[regs_fp['Técnico'] == tec]
                        total  = pd.to_numeric(regs_t['Horas_Total'], errors='coerce').fillna(0).sum()
                        st.markdown(f"""
                        <div class="pedido-card">
                            <b>👤 {tec}</b><br>
                            <small>{len(regs_t)} dias | <b>{total:.1f}h</b></small>
                        </div>""", unsafe_allow_html=True)

                    st.markdown("### ✍️ Assinatura do Responsável")
                    canvas_sig = None
                    try:
                        canvas_sig = st_canvas(
                            fill_color="rgba(255,255,255,0)", stroke_width=2.5,
                            stroke_color="#3B82F6", background_color="#FFFFFF",
                            height=180, width=400, drawing_mode="freedraw",
                            key="canvas_esign_fp"
                        )
                    except:
                        st.info("ℹ️ Canvas não disponível.")

                    nome_resp = st.text_input("Nome do Responsável", key="fp_resp_nome")
                    if st.button("🔒 Gerar Folha com Selo",
                                 use_container_width=True, type="primary", key="btn_gerar_folha"):
                        if nome_resp:
                            esign_id  = secrets.token_hex(6).upper()
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            sig_b64   = ""
                            if canvas_sig is not None and canvas_sig.image_data is not None:
                                sig_b64 = canvas_to_b64(canvas_sig.image_data) or ""
                            nova_folha = pd.DataFrame([{
                                "ID":             str(uuid.uuid4())[:8].upper(),
                                "Obra":           obra_f,
                                "Periodo":        f"{semana_inicio.strftime('%d/%m')} - {semana_fim.strftime('%d/%m/%Y')}",
                                "Responsavel":    nome_resp,
                                "Data_Assinatura":timestamp,
                                "Assinatura_b64": sig_b64,
                                "Selo":           esign_id,
                                "Status":         "Assinado"
                            }])
                            updated = pd.concat([folhas_db, nova_folha], ignore_index=True) \
                                      if not folhas_db.empty else nova_folha
                            save_db(updated, "folhas_ponto.csv")
                            log_audit(usuario=user_nome, acao="ASSINAR_FOLHA_PONTO",
                                      tabela="folhas_ponto.csv",
                                      registro_id=nova_folha['ID'].iloc[0],
                                      detalhes=f"Assinado por {nome_resp} — {obra_f}", ip="")
                            st.markdown(f"""
                            <div class="esign-seal">
                                <b>🔒 SELO GESTNOW #{esign_id}</b><br>
                                ASSINADO POR: {nome_resp}<br>
                                DATA/HORA: {timestamp}<br>
                                OBRA: {obra_f}
                            </div>""", unsafe_allow_html=True)
                            inv()
                            st.success(f"✅ Folha #{esign_id} gerada!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Indica o nome do responsável.")
                else:
                    st.info(f"📋 Sem registos para {obra_f} neste período.")

    # ═══════════════════════════════════════════════════════════════
    # TAB HSE
    # ═══════════════════════════════════════════════════════════════
    with tabs[1 + offset]:
        st.markdown(f"### {ICONS['safety']} Regras de Ouro HSE")
        for ic, tit, des in REGRAS_OURO:
            with st.expander(f"{ic} {tit}"):
                st.write(des)

        st.divider()
        st.markdown("### 🚨 Reportar Incidente")
        with st.form("hse_report"):
            io_hse = st.selectbox("Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="hse_obra")
            it_hse = st.selectbox("Gravidade",
                ["Baixa","Média","Alta (Crítica)"], key="hse_grav")
            id_hse = st.text_area("Descrição da Ocorrência", key="hse_desc")
            if st.form_submit_button("📤 Submeter Alerta HSE",
                                      use_container_width=True, type="primary"):
                if id_hse:
                    ni = pd.DataFrame([{
                        "ID":         str(uuid.uuid4())[:8].upper(),
                        "Data":       date.today().strftime("%d/%m/%Y"),
                        "Utilizador": user_nome, "Obra": io_hse,
                        "Status":     "Aberto", "Gravidade": it_hse,
                        "Descricao":  id_hse, "Tipo": "HSE"
                    }])
                    updated = pd.concat([incs_db, ni], ignore_index=True) if not incs_db.empty else ni
                    save_db(updated, "incidentes.csv")
                    log_audit(usuario=user_nome, acao="REPORTAR_INCIDENTE_HSE",
                              tabela="incidentes.csv", registro_id=ni['ID'].iloc[0],
                              detalhes=f"{user_nome} em {io_hse}", ip="")
                    inv()
                    st.success("✅ Alerta HSE enviado!")
                    st.rerun()
                else:
                    st.warning("⚠️ Descreve o incidente.")

    # ═══════════════════════════════════════════════════════════════
    # TAB PERFIL
    # ═══════════════════════════════════════════════════════════════
    with tabs[-2]:
        st.markdown(f"### {ICONS['profile']} Perfil do Colaborador")

        if user_data is not None:
            # Feedback de estado
            st.markdown("### 📋 Estado das Validações")
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                pdfs_val      = user_data.get('PDFs_Validados', 'Não')
                pdfs_val_data = user_data.get('PDFs_Validacao_Data', '')
                if pdfs_val == 'Sim':
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.1);border:2px solid #10B981;
                        border-radius:10px;padding:15px;text-align:center;">
                        <b style="color:#10B981;">✅ Documentos Validados</b>
                        <p style="color:#64748B;font-size:0.8rem;margin:8px 0 0 0;">Em {pdfs_val_data}</p>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="background:rgba(239,68,68,0.1);border:2px solid #EF4444;
                        border-radius:10px;padding:15px;text-align:center;">
                        <b style="color:#EF4444;">❌ Documentos Pendentes</b>
                    </div>""", unsafe_allow_html=True)

            with col_v2:
                preco_s = user_data.get('PrecoHoraStatus', '')
                preco_d = user_data.get('PrecoHoraData',   '')
                preco_v = user_data.get('PrecoHora',       '15.0')
                if preco_s == 'Aceite':
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.1);border:2px solid #10B981;
                        border-radius:10px;padding:15px;text-align:center;">
                        <b style="color:#10B981;">✅ €{preco_v}/h Aceite</b>
                        <p style="color:#64748B;font-size:0.8rem;margin:8px 0 0 0;">Em {preco_d}</p>
                    </div>""", unsafe_allow_html=True)
                elif preco_s == 'Recusado':
                    st.markdown(f"""
                    <div style="background:rgba(239,68,68,0.1);border:2px solid #EF4444;
                        border-radius:10px;padding:15px;text-align:center;">
                        <b style="color:#EF4444;">❌ €{preco_v}/h Recusado</b>
                        <p style="color:#64748B;font-size:0.8rem;margin:8px 0 0 0;">Aguarda contacto admin</p>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:rgba(245,158,11,0.1);border:2px solid #F59E0B;
                        border-radius:10px;padding:15px;text-align:center;">
                        <b style="color:#F59E0B;">⏳ €{preco_v}/h Pendente</b>
                    </div>""", unsafe_allow_html=True)

            st.divider()

            try:
                campos_bloqueados = json.loads(user_data.get('Campos_Bloqueados', '[]'))
            except:
                campos_bloqueados = []

            st.markdown("### ✏️ Editar Perfil")

            with st.form("form_editar_perfil"):
                st.markdown("**📋 Contactos**")
                col1, col2 = st.columns(2)
                with col1:
                    telefone = st.text_input("Telefone",
                        value=user_data.get('Telefone',''),
                        disabled='Telefone' in campos_bloqueados, key="edit_tel")
                    email_v  = st.text_input("Email",
                        value=user_data.get('Email',''),
                        disabled='Email' in campos_bloqueados, key="edit_email")
                    c_emerg  = st.text_input("Tel. Emergência",
                        value=user_data.get('Contacto_Emergencia',''),
                        disabled='Contacto_Emergencia' in campos_bloqueados, key="edit_emerg")
                with col2:
                    n_emerg  = st.text_input("Nome Emergência",
                        value=user_data.get('Nome_Emergencia',''),
                        disabled='Nome_Emergencia' in campos_bloqueados, key="edit_n_emerg")
                    grau     = st.text_input("Grau Parentesco",
                        value=user_data.get('Grau_Parentesco',''),
                        disabled='Grau_Parentesco' in campos_bloqueados, key="edit_grau")

                st.markdown("**📍 Morada**")
                morada = st.text_input("Morada",
                    value=user_data.get('Morada',''),
                    disabled='Morada' in campos_bloqueados, key="edit_morada")
                c3, c4, c5 = st.columns(3)
                with c3:
                    localidade = st.text_input("Localidade",
                        value=user_data.get('Localidade',''),
                        disabled='Localidade' in campos_bloqueados, key="edit_loc")
                with c4:
                    concelho   = st.text_input("Concelho",
                        value=user_data.get('Concelho',''),
                        disabled='Concelho' in campos_bloqueados, key="edit_conc")
                with c5:
                    cod_postal = st.text_input("Código Postal",
                        value=user_data.get('Codigo_Postal',''),
                        disabled='Codigo_Postal' in campos_bloqueados, key="edit_cp")

                st.markdown("**🆔 Documentos**")
                col8, col9 = st.columns(2)
                with col8:
                    nif  = st.text_input("NIF",
                        value=user_data.get('NIF',''),
                        disabled='NIF' in campos_bloqueados, key="edit_nif")
                    cc   = st.text_input("CC",
                        value=user_data.get('CC',''),
                        disabled='CC' in campos_bloqueados, key="edit_cc")
                with col9:
                    cc_v = st.text_input("Validade CC",
                        value=user_data.get('CC_Validade',''),
                        disabled='CC_Validade' in campos_bloqueados, key="edit_cc_val")
                    niss = st.text_input("NISS",
                        value=user_data.get('NISS',''),
                        disabled='NISS' in campos_bloqueados, key="edit_niss")

                st.markdown("**👕 Fardamento**")
                col12, col13, col14 = st.columns(3)
                cam_opts = ["XS","S","M","L","XL","XXL","XXXL"]
                cal_opts = ["XS (34/36)","S (38)","M (40/42)","L (42/44)","XL (46/48)","XXL (50/52)"]
                bot_opts = ["40","41","42","43","44","45","Outro"]
                with col12:
                    cam_v = user_data.get('Tamanho_Camisola','M')
                    tam_cam = st.selectbox("Camisola", cam_opts,
                        index=cam_opts.index(cam_v) if cam_v in cam_opts else 3, key="edit_cam")
                with col13:
                    cal_v = user_data.get('Tamanho_Calca','')
                    tam_cal = st.selectbox("Calça", cal_opts,
                        index=cal_opts.index(cal_v) if cal_v in cal_opts else 0, key="edit_calc")
                with col14:
                    bot_v = user_data.get('Tamanho_Botas','')
                    tam_bot = st.selectbox("Botas", bot_opts,
                        index=bot_opts.index(bot_v) if bot_v in bot_opts else 2, key="edit_bot")

                st.markdown("**🔐 Alterar Password**")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    pwd_atual = st.text_input("Password Atual", type="password", key="edit_pwd_atual")
                with col_p2:
                    pwd_nova  = st.text_input("Nova Password",  type="password", key="edit_pwd_nova")

                novo_pin = st.text_input("🔢 Novo PIN (4 dígitos numéricos)",
                    max_chars=4, key="edit_pin", placeholder="0000")

                st.info("🔒 Nome, Tipo, Cargo e IBAN são geridos pelo Administrador.")

                if st.form_submit_button("💾 Guardar Alterações",
                                          use_container_width=True, type="primary"):
                    u_live = _load_users_fresh()
                    if not u_live.empty:
                        mask = u_live['Nome'] == user_nome
                        if mask.any():
                            updates = {
                                'Telefone': telefone.strip(), 'Email': email_v.strip(),
                                'Morada': morada.strip(), 'Localidade': localidade.strip(),
                                'Concelho': concelho.strip(), 'Codigo_Postal': cod_postal.strip(),
                                'NIF': nif.strip(), 'CC': cc.strip(),
                                'CC_Validade': cc_v.strip(), 'NISS': niss.strip(),
                                'Contacto_Emergencia': c_emerg.strip(),
                                'Nome_Emergencia': n_emerg.strip(),
                                'Grau_Parentesco': grau.strip(),
                                'Tamanho_Camisola': tam_cam,
                                'Tamanho_Calca': tam_cal, 'Tamanho_Botas': tam_bot,
                            }
                            for campo, valor in updates.items():
                                if campo not in campos_bloqueados:
                                    u_live.loc[mask, campo] = valor

                            # Password
                            if pwd_nova.strip() and pwd_atual.strip():
                                from core import cp as check_pwd
                                pwd_hash_atual = str(u_live.loc[mask, 'Password'].values[0])
                                if check_pwd(pwd_atual.strip(), pwd_hash_atual):
                                    if len(pwd_nova.strip()) >= 4:
                                        u_live.loc[mask, 'Password'] = hp(pwd_nova.strip())
                                        st.success("🔐 Password atualizada!")
                                    else:
                                        st.error("❌ Mínimo 4 caracteres.")
                                else:
                                    st.error("❌ Password atual incorreta.")

                            # PIN
                            if novo_pin.strip():
                                if len(novo_pin.strip()) == 4 and novo_pin.strip().isdigit():
                                    u_live.loc[mask, 'PIN'] = novo_pin.strip()
                                else:
                                    st.error("❌ PIN deve ter 4 dígitos numéricos.")

                            save_db(u_live, "usuarios.csv")
                            log_audit(usuario=user_nome, acao="EDITAR_PERFIL",
                                      tabela="usuarios.csv", registro_id=user_nome,
                                      detalhes="Perfil atualizado", ip="")
                            inv()
                            st.success("✅ Perfil atualizado!")
                            st.rerun()
        else:
            st.warning("⚠️ Não foi possível carregar os dados do utilizador.")

    # ═══════════════════════════════════════════════════════════════
    # TAB PEDIDOS
    # ═══════════════════════════════════════════════════════════════
    with tabs[-1]:
        st.markdown(f"### {ICONS['material']} Pedidos & Reportes")

        sub_fer, sub_epi, sub_mat, sub_gas, sub_avar, sub_meus = st.tabs([
            "🔧 Ferramentas", "🦺 EPIs", "📦 Materiais",
            "⛽ Gasóleo", "🔧 Avarias", "📋 Os Meus"
        ])

        with sub_fer:
            with st.form("form_pedir_fer"):
                obra_ped = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_fer_obra")
                desc_fer = st.text_area("Descrição da ferramenta", key="ped_fer_desc")
                urg_fer  = st.selectbox("Urgência", ["Baixa","Média","Alta"], key="ped_fer_urg")
                foto_fer = st.file_uploader("Foto (opcional)",
                    type=["png","jpg","jpeg"], key="ped_fer_foto")
                if st.form_submit_button("📤 Enviar", use_container_width=True, type="primary"):
                    if desc_fer:
                        foto_b64 = process_and_compress_image(foto_fer) if foto_fer else None
                        novo = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_ped,
                            "Descricao": desc_fer, "Urgencia": urg_fer,
                            "Foto_b64": foto_b64, "Status": "Pendente"
                        }])
                        updated = pd.concat([req_fer_db, novo], ignore_index=True) if not req_fer_db.empty else novo
                        save_db(updated, "req_ferramentas.csv")
                        criar_notificacao(destinatario="admin", titulo="🔧 Pedido Ferramenta",
                            mensagem=f"{user_nome}: {desc_fer[:40]} em {obra_ped}",
                            tipo="warning", acao_url="/admin?tab=validacoes")
                        inv(); st.success("✅ Pedido enviado!"); st.rerun()
                    else:
                        st.warning("⚠️ Descreve a ferramenta.")

        with sub_epi:
            with st.form("form_pedir_epi"):
                obra_epi = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_epi_obra")
                item_epi = st.selectbox("EPI",
                    ["Capacete","Óculos","Luvas","Botas","Arnés","Protetor Auditivo","Máscara","Outro"],
                    key="ped_epi_tipo")
                col_t, col_q = st.columns(2)
                with col_t: tam_epi = st.selectbox("Tamanho", ["P","M","G","XG","Único"], key="ped_epi_tam")
                with col_q: qtd_epi = st.number_input("Quantidade", min_value=1, value=1, key="ped_epi_qtd")
                if st.form_submit_button("📤 Enviar", use_container_width=True, type="primary"):
                    novo = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8].upper(),
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante": user_nome, "Obra": obra_epi,
                        "Item": item_epi, "Tamanho": tam_epi,
                        "Quantidade": qtd_epi, "Status": "Pendente"
                    }])
                    updated = pd.concat([req_epi_db, novo], ignore_index=True) if not req_epi_db.empty else novo
                    save_db(updated, "req_epis.csv")
                    criar_notificacao(destinatario="admin", titulo="🦺 Pedido EPI",
                        mensagem=f"{user_nome}: {qtd_epi}x {item_epi} ({tam_epi}) em {obra_epi}",
                        tipo="warning", acao_url="/admin?tab=validacoes")
                    inv(); st.success("✅ Pedido enviado!"); st.rerun()

        with sub_mat:
            with st.form("form_pedir_mat"):
                obra_mat = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_mat_obra")
                desc_mat = st.text_area("Descrição do material", key="ped_mat_desc")
                col_q2, col_u = st.columns(2)
                with col_q2: qtd_mat = st.number_input("Quantidade", min_value=1, value=1, key="ped_mat_qtd")
                with col_u:  unid_mat= st.selectbox("Unidade", ["un","m","kg","l","cx"], key="ped_mat_unid")
                urg_mat = st.selectbox("Urgência", ["Baixa","Média","Alta"], key="ped_mat_urg")
                if st.form_submit_button("📤 Enviar", use_container_width=True, type="primary"):
                    if desc_mat:
                        novo = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_mat,
                            "Descricao": desc_mat, "Quantidade": qtd_mat,
                            "Unidade": unid_mat, "Urgencia": urg_mat, "Status": "Pendente"
                        }])
                        updated = pd.concat([req_mat_db, novo], ignore_index=True) if not req_mat_db.empty else novo
                        save_db(updated, "req_materiais.csv")
                        criar_notificacao(destinatario="admin", titulo="📦 Pedido Material",
                            mensagem=f"{user_nome}: {qtd_mat}{unid_mat} de {desc_mat[:30]}",
                            tipo="warning", acao_url="/admin?tab=validacoes")
                        inv(); st.success("✅ Pedido enviado!"); st.rerun()
                    else:
                        st.warning("⚠️ Descreve o material.")

        with sub_gas:
            with st.form("form_pedir_gas"):
                obra_gas   = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_gas_obra")
                col_l, col_v = st.columns(2)
                with col_l: litros = st.number_input("Litros", min_value=0.0, step=0.1, key="ped_gas_lit")
                with col_v: valor  = st.number_input("Valor €", min_value=0.0, step=0.01, key="ped_gas_val")
                data_gas  = st.date_input("Data abastecimento", value=date.today(), key="ped_gas_data")
                recibo    = st.file_uploader("📄 Recibo (obrigatório)",
                    type=["png","jpg","jpeg","pdf"], key="ped_gas_rec")
                obs_gas   = st.text_area("Observações (viatura, km...)", key="ped_gas_obs")
                if st.form_submit_button("📤 Enviar", use_container_width=True, type="primary"):
                    if recibo and litros > 0:
                        rec_b64 = base64.b64encode(recibo.read()).decode() if recibo.type=="application/pdf" \
                                  else process_and_compress_image(recibo)
                        novo = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_gas,
                            "Litros": litros, "Valor": valor,
                            "Data_Abastecimento": data_gas.strftime("%d/%m/%Y"),
                            "Descricao": obs_gas, "Recibo_b64": rec_b64,
                            "Status": "Pendente", "Tipo": "Gasóleo"
                        }])
                        updated = pd.concat([req_mat_db, novo], ignore_index=True) if not req_mat_db.empty else novo
                        save_db(updated, "req_materiais.csv")
                        criar_notificacao(destinatario="admin", titulo="⛽ Gasóleo",
                            mensagem=f"{user_nome}: {litros}L (€{valor}) em {obra_gas}",
                            tipo="info", acao_url="/admin?tab=validacoes")
                        inv(); st.success("✅ Registo enviado!"); st.rerun()
                    else:
                        st.warning("⚠️ Faz upload do recibo e indica os litros.")

        with sub_avar:
            with st.form("form_pedir_avar"):
                obra_av  = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"], key="ped_av_obra")
                equip_av = st.text_input("Equipamento / Viatura", key="ped_av_equip",
                    placeholder="Ex: Viatura ABC-123")
                desc_av  = st.text_area("Descrição da Avaria", key="ped_av_desc")
                col_u2, col_v2 = st.columns(2)
                with col_u2: urg_av = st.selectbox("Urgência",
                    ["Baixa","Média","Alta","Crítica - Paragem"], key="ped_av_urg")
                with col_v2: val_av = st.number_input("Valor Est. €", min_value=0.0, key="ped_av_val")
                fat_av   = st.file_uploader("📄 Fatura/Orçamento (obrigatório)",
                    type=["png","jpg","jpeg","pdf"], key="ped_av_fat")
                if st.form_submit_button("📤 Enviar", use_container_width=True, type="primary"):
                    if fat_av and desc_av:
                        fat_b64 = base64.b64encode(fat_av.read()).decode() if fat_av.type=="application/pdf" \
                                  else process_and_compress_image(fat_av)
                        novo = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_av,
                            "Equipamento": equip_av, "Descricao": desc_av,
                            "Urgencia": urg_av, "Valor_Estimado": val_av,
                            "Fatura_b64": fat_b64, "Status": "Pendente", "Tipo": "Avaria"
                        }])
                        updated = pd.concat([incs_db, novo], ignore_index=True) if not incs_db.empty else novo
                        save_db(updated, "incidentes.csv")
                        criar_notificacao(destinatario="admin", titulo="🔧 Avaria Reportada",
                            mensagem=f"{urg_av}: {equip_av} em {obra_av}",
                            tipo="error" if urg_av=="Crítica - Paragem" else "warning",
                            acao_url="/admin?tab=validacoes")
                        inv(); st.success("✅ Reporte enviado!"); st.rerun()
                    else:
                        st.warning("⚠️ Descreve a avaria e faz upload da fatura/orçamento.")

        with sub_meus:
            st.markdown("#### 📋 Os Meus Pedidos Recentes")
            sem = True
            for db, tipo_p, campo_d in [
                (req_fer_db,"🔧 Ferramentas","Descricao"),
                (req_epi_db,"🦺 EPIs","Item"),
                (req_mat_db,"📦 Materiais/Outros","Descricao"),
            ]:
                if not db.empty and 'Solicitante' in db.columns:
                    meus = db[db['Solicitante']==user_nome]
                    if not meus.empty:
                        sem = False
                        st.markdown(f"##### {tipo_p}")
                        for _, p in meus.tail(4).iterrows():
                            cor = {"Pendente":"#F59E0B","Aprovado":"#10B981","Rejeitado":"#EF4444"}.get(
                                p.get('Status','Pendente'),"#6B7280")
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);padding:10px;
                                border-radius:8px;margin-bottom:6px;border-left:3px solid {cor};">
                                <span style="color:#F8FAFC;">{str(p.get(campo_d,'N/A'))[:45]}</span>
                                <span style="color:{cor};font-size:0.8rem;float:right;">
                                    {p.get('Status','Pendente')}
                                </span>
                            </div>""", unsafe_allow_html=True)
            if sem:
                st.info("📋 Ainda não fizeste nenhum pedido.")

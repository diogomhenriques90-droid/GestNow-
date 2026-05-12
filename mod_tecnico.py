import streamlit as st
import pandas as pd
import uuid, base64, json, secrets
from datetime import datetime, timedelta, date
from streamlit_drawable_canvas import st_canvas
import time

from core import (
    save_db, inv, fh, sl, load_db, canvas_to_b64,
    ICONS, COLORS, TIPOS_FRENTE, REGRAS_OURO,
    log_audit, criar_notificacao, process_and_compress_image,
    _gcs_read, hp
)

_DOT_COLOR = {
    "0": "#F97316",
    "1": "#10B981",
    "2": "#3B82F6",
    "3": "#6B7280",
    "4": "#6B7280",
    "-1": "#EF4444",
}
_DOT_LABEL = {
    "0": "Pendente",
    "1": "Validado",
    "2": "Faturação",
    "3": "Pago",
    "4": "Pago",
    "-1": "Rejeitado",
}
_MESES_PT = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
             'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
_DIAS_LETRA = ['D','S','T','Q','Q','S','S']
_HORAS_30   = [f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)]

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
    # ✅ *_ apanha os novos valores de diárias sem quebrar
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     *_) = args

    user_nome  = st.session_state.get('user', '')
    cargo_user = st.session_state.get('cargo', 'Técnico')
    user_tipo  = st.session_state.get('tipo',  'Técnico')
    hoje       = date.today()

    is_chefe = (user_tipo in ['Chefe de Equipa','Admin','Gestor'] or
                cargo_user in ['Chefe de Equipa','Encarregado'])

    try:
        users_fresh = _load_users_fresh()
        user_match  = users_fresh[users_fresh['Nome'] == user_nome]
        user_data   = user_match.iloc[0]  if not user_match.empty else None
        user_idx    = user_match.index[0] if not user_match.empty else None
    except:
        user_data = None
        user_idx  = None

    # ── Session state ─────────────────────────────────────────────────
    for k, v in [
        ('data_consulta',      hoje),
        ('semana_offset',      0),
        ('show_reg_form',      False),
        ('periodos_trabalho',  [{"entrada":"08:00","saida":"17:00"}]),
        ('reg_sucesso',        None),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    # ── CSS ───────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .stApp { background: #0F172A !important; }
    .main .block-container { padding-top: 0.5rem !important; }
    h1,h2,h3,h4,h5,h6 { color:#F1F5F9 !important; }
    p,div,span { color:#CBD5E1; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background:#1E293B !important;
        border-bottom:2px solid #334155 !important;
        gap:0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color:#64748B !important;
        font-size:0.76rem !important;
        padding:10px 6px !important;
        background:transparent !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color:#DC2626 !important;
        font-weight:700 !important;
        border-bottom:3px solid #DC2626 !important;
    }

    /* Botões */
    .stButton>button {
        border-radius:12px !important;
        font-weight:600 !important;
        height:44px !important;
    }
    .stButton>button[kind="primary"] {
        background:#DC2626 !important;
        color:white !important;
        border:none !important;
    }
    .stButton>button[kind="secondary"] {
        background:#1E293B !important;
        color:#CBD5E1 !important;
        border:1px solid #334155 !important;
    }

    /* Inputs */
    .stTextInput label, .stSelectbox label, .stNumberInput label,
    .stTextArea label, .stRadio label, .stCheckbox label {
        color:#CBD5E1 !important;
        font-size:0.82rem !important;
        font-weight:500 !important;
    }
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stTextArea>div>div>textarea {
        background:#1E293B !important;
        color:#F1F5F9 !important;
        border:1px solid #334155 !important;
        border-radius:10px !important;
    }
    .stSelectbox>div>div>div {
        background:#1E293B !important;
        color:#F1F5F9 !important;
        border:1px solid #334155 !important;
    }

    /* Botões calendário — tornar circulares e compactos */
    [data-testid="stHorizontalBlock"] .stButton>button {
        border-radius: 50% !important;
        padding: 0 !important;
        height: 38px !important;
        min-height: 38px !important;
        width: 38px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }

    .streamlit-expanderHeader {
        background:#1E293B !important;
        color:#F1F5F9 !important;
        border-radius:10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────
    menu = ["📋 Pontos", "🛡️ HSE", "👤 Perfil", "📦 Pedidos"]
    if is_chefe:
        menu.insert(1, "📊 Folha")
    tabs = st.tabs(menu)

    # ════════════════════════════════════════════════════════════════
    # TAB 0 — PONTOS
    # ════════════════════════════════════════════════════════════════
    with tabs[0]:

        # Calcular dots de status por dia
        dias_status = {}
        if not registos_db.empty and 'Técnico' in registos_db.columns:
            ru = registos_db[registos_db['Técnico'] == user_nome].copy()
            if not ru.empty:
                ru['Data_d'] = pd.to_datetime(
                    ru['Data'], dayfirst=True, errors='coerce'
                ).dt.date
                sp = {"4":6,"3":5,"2":4,"1":3,"0":2,"-1":1}
                for d_u in ru['Data_d'].dropna().unique():
                    rd     = ru[ru['Data_d'] == d_u]
                    melhor = max(rd['Status'].tolist(),
                                 key=lambda s: sp.get(str(s), 0))
                    dias_status[d_u] = str(melhor)

        if not st.session_state.show_reg_form:

            # ── Calendário ────────────────────────────────────────
            data_ref   = hoje + timedelta(weeks=st.session_state.semana_offset)
            inicio_sem = data_ref - timedelta(days=(data_ref.weekday() + 1) % 7)
            dias_sem   = [inicio_sem + timedelta(days=i) for i in range(7)]
            mes_label  = _MESES_PT[dias_sem[3].month - 1]
            ano_label  = dias_sem[3].year

            col_prev, col_mes, col_next = st.columns([1, 4, 1])
            with col_prev:
                if st.button("‹", key="cal_prev", use_container_width=True):
                    st.session_state.semana_offset -= 1
                    st.rerun()
            with col_mes:
                st.markdown(
                    f"<p style='text-align:center;color:#F1F5F9;font-weight:700;"
                    f"font-size:0.95rem;margin:8px 0;'>"
                    f"Pontos &nbsp;·&nbsp; "
                    f"<span style='color:#DC2626;'>{mes_label} {ano_label}</span></p>",
                    unsafe_allow_html=True
                )
            with col_next:
                if st.button("›", key="cal_next", use_container_width=True):
                    st.session_state.semana_offset += 1
                    st.rerun()

            letras_cols = st.columns(7)
            for col, d in zip(letras_cols, dias_sem):
                with col:
                    dl     = _DIAS_LETRA[(d.weekday() + 1) % 7]
                    fim_s  = (d.weekday() + 1) % 7 in (0, 6)
                    cor_l  = "#475569" if fim_s else "#64748B"
                    st.markdown(
                        f"<p style='text-align:center;color:{cor_l};"
                        f"font-size:0.6rem;font-weight:700;margin:0;"
                        f"text-transform:uppercase;'>{dl}</p>",
                        unsafe_allow_html=True
                    )

            btn_cols = st.columns(7)
            for col, d in zip(btn_cols, dias_sem):
                with col:
                    dot_cor = _DOT_COLOR.get(dias_status.get(d, ''), '')
                    eh_hoje = d == hoje
                    eh_sel  = d == st.session_state.data_consulta

                    if eh_sel:
                        btn_type = "primary"
                    else:
                        btn_type = "secondary"

                    if st.button(
                        str(d.day),
                        key=f"day_{d.strftime('%Y%m%d')}",
                        use_container_width=True,
                        type=btn_type
                    ):
                        st.session_state.data_consulta = d
                        st.rerun()

                    if dot_cor:
                        st.markdown(
                            f"<div style='width:7px;height:7px;border-radius:50%;"
                            f"background:{dot_cor};margin:-6px auto 4px;'></div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            "<div style='height:11px;'></div>",
                            unsafe_allow_html=True
                        )

            st.markdown(
                "<div style='display:flex;gap:12px;justify-content:center;"
                "flex-wrap:wrap;margin:4px 0 12px;'>"
                "<span style='font-size:0.62rem;color:#64748B;'>"
                "<span style='color:#F97316;'>●</span> Pendente</span>"
                "<span style='font-size:0.62rem;color:#64748B;'>"
                "<span style='color:#10B981;'>●</span> Validado</span>"
                "<span style='font-size:0.62rem;color:#64748B;'>"
                "<span style='color:#3B82F6;'>●</span> Faturação</span>"
                "<span style='font-size:0.62rem;color:#64748B;'>"
                "<span style='color:#6B7280;'>●</span> Pago</span>"
                "</div>",
                unsafe_allow_html=True
            )

            st.markdown(
                "<hr style='border:none;border-top:1px solid #1E293B;margin:0 0 12px;'>",
                unsafe_allow_html=True
            )

            data_sel    = st.session_state.data_consulta
            meses       = _MESES_PT[data_sel.month - 1]
            dia_l       = _DIAS_LETRA[(data_sel.weekday() + 1) % 7]
            eh_hoje_sel = data_sel == hoje

            col_data, col_fab = st.columns([4, 1])
            with col_data:
                prefix = "📍 Hoje" if eh_hoje_sel else f"{dia_l}"
                st.markdown(
                    f"<p style='color:#F1F5F9;font-weight:700;font-size:0.92rem;margin:0;'>"
                    f"{prefix}, {data_sel.day} de {meses}</p>",
                    unsafe_allow_html=True
                )
            with col_fab:
                if st.button("＋", key="fab_btn", type="primary",
                              use_container_width=True):
                    st.session_state.show_reg_form    = True
                    st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"17:00"}]
                    st.rerun()

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

            regs_dia = pd.DataFrame()
            if not registos_db.empty and 'Técnico' in registos_db.columns:
                meus = registos_db[registos_db['Técnico'] == user_nome].copy()
                if not meus.empty:
                    dp       = pd.to_datetime(meus['Data'], dayfirst=True, errors='coerce').dt.date
                    regs_dia = meus[dp == data_sel].copy()

            if not regs_dia.empty:
                regs_dia['_h'] = pd.to_numeric(
                    regs_dia['Horas_Total'], errors='coerce'
                ).fillna(0)
                total_dia = regs_dia['_h'].sum()

                col_nt, col_tt = st.columns([3, 1])
                with col_nt:
                    st.markdown(
                        f"<p style='color:#64748B;font-size:0.78rem;margin:0;'>"
                        f"{len(regs_dia)} registo(s)</p>",
                        unsafe_allow_html=True
                    )
                with col_tt:
                    st.markdown(
                        f"<p style='color:#DC2626;font-weight:900;font-size:0.88rem;"
                        f"text-align:right;margin:0;'>{fh(total_dia)}</p>",
                        unsafe_allow_html=True
                    )

                st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

                for _, r in regs_dia.iterrows():
                    s_str  = str(r.get('Status', '0'))
                    dot_c  = _DOT_COLOR.get(s_str, '#6B7280')
                    dot_l  = _DOT_LABEL.get(s_str, 'N/A')
                    relat  = str(r.get('Relatorio', ''))[:55]
                    turnos = r.get('Turnos', '')

                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:12px;"
                        f"padding:13px 15px;margin-bottom:8px;"
                        f"border-left:4px solid {dot_c};'>"
                        f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:flex-start;'>"
                        f"<div style='flex:1;'>"
                        f"<p style='margin:0;font-weight:700;color:#F1F5F9;"
                        f"font-size:0.9rem;'>{r.get('Obra', '')}</p>"
                        f"<p style='margin:3px 0 0;color:#64748B;font-size:0.78rem;'>"
                        f"{r.get('Frente','')} · {turnos}</p>"
                        f"{'<p style=margin:3px 0 0;color:#475569;font-size:0.73rem;>' + relat + '</p>' if relat else ''}"
                        f"</div>"
                        f"<div style='text-align:right;margin-left:10px;'>"
                        f"<p style='margin:0;font-weight:900;color:#F1F5F9;"
                        f"font-size:1.05rem;'>{fh(r.get('Horas_Total', 0))}</p>"
                        f"<p style='margin:3px 0 0;background:{dot_c}22;color:{dot_c};"
                        f"padding:2px 8px;border-radius:8px;font-size:0.68rem;"
                        f"font-weight:700;'>{dot_l}</p>"
                        f"</div></div></div>",
                        unsafe_allow_html=True
                    )
            else:
                st.markdown(
                    "<div style='background:#1E293B;border-radius:14px;"
                    "padding:44px 20px;text-align:center;"
                    "border:1px dashed #334155;margin-top:8px;'>"
                    "<p style='font-size:2.5rem;margin:0 0 10px;opacity:0.3;'>📋</p>"
                    "<p style='color:#475569;font-weight:600;margin:0;font-size:0.88rem;'>"
                    "Sem ponto registado neste dia</p>"
                    "</div>",
                    unsafe_allow_html=True
                )

        # ════════════════════════════════════════════════════════════
        # FORMULÁRIO DE REGISTO
        # ════════════════════════════════════════════════════════════
        else:
            data_sel = st.session_state.data_consulta

            st.markdown(
                f"<div style='background:#1E293B;border-radius:14px;"
                f"padding:14px 16px;margin-bottom:14px;border:1px solid #334155;'>"
                f"<p style='color:#94A3B8;font-size:0.72rem;margin:0;'>Registo de ponto</p>"
                f"<p style='color:#F1F5F9;font-weight:700;font-size:0.95rem;margin:2px 0;'>"
                f"{user_nome} &nbsp;·&nbsp; "
                f"<span style='color:#DC2626;'>{data_sel.strftime('%d/%m/%Y')}</span></p>"
                f"</div>",
                unsafe_allow_html=True
            )

            with st.form("form_ponto", clear_on_submit=False):

                st.markdown(
                    "<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                    "letter-spacing:0.08em;text-transform:uppercase;margin:0 0 6px;'>"
                    "🏗️ Obra</p>",
                    unsafe_allow_html=True
                )
                obras_lista = []
                if not obras_db.empty:
                    at = obras_db[obras_db['Ativa'] == 'Ativa']
                    obras_lista = at['Obra'].tolist() if not at.empty else obras_db['Obra'].tolist()

                obra_sel = st.selectbox(
                    "Obra", obras_lista if obras_lista else ["Sem obras"],
                    key="reg_obra", label_visibility="collapsed"
                )

                if not obras_db.empty and obra_sel in obras_db['Obra'].values:
                    oi  = obras_db[obras_db['Obra'] == obra_sel].iloc[0]
                    cod = oi.get('Codigo', '')
                    cli = oi.get('Cliente', '')
                    if cod or cli:
                        st.markdown(
                            f"<p style='color:#DC2626;font-size:0.72rem;"
                            f"font-weight:700;margin:-2px 0 8px;'>"
                            f"{cod}"
                            f"{'  ·  ' + cli if cli else ''}</p>",
                            unsafe_allow_html=True
                        )

                st.markdown(
                    "<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                    "letter-spacing:0.08em;text-transform:uppercase;margin:8px 0 6px;'>"
                    "🔧 Frente</p>",
                    unsafe_allow_html=True
                )
                frente_sel = st.selectbox(
                    "Frente", TIPOS_FRENTE,
                    key="reg_frente", label_visibility="collapsed"
                )

                st.markdown(
                    "<hr style='border:none;border-top:1px solid #1E293B;margin:12px 0;'>",
                    unsafe_allow_html=True
                )

                st.markdown(
                    "<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                    "letter-spacing:0.08em;text-transform:uppercase;margin:0 0 8px;'>"
                    "⏱️ Horas</p>",
                    unsafe_allow_html=True
                )

                total_horas      = 0.0
                periodos_validos = []

                for idx, periodo in enumerate(st.session_state.periodos_trabalho):
                    if idx > 0:
                        st.markdown(
                            "<hr style='border:none;border-top:1px dashed #1E293B;margin:6px 0;'>",
                            unsafe_allow_html=True
                        )

                    col_e, col_s = st.columns(2)
                    with col_e:
                        ie      = _HORAS_30.index(periodo["entrada"]) \
                                  if periodo["entrada"] in _HORAS_30 else 16
                        entrada = st.selectbox(
                            f"Entrada {idx+1 if len(st.session_state.periodos_trabalho)>1 else ''}",
                            _HORAS_30, index=ie, key=f"ent_{idx}"
                        )
                    with col_s:
                        is_     = _HORAS_30.index(periodo["saida"]) \
                                  if periodo["saida"] in _HORAS_30 else 34
                        saida   = st.selectbox(
                            f"Saída {idx+1 if len(st.session_state.periodos_trabalho)>1 else ''}",
                            _HORAS_30, index=is_, key=f"sai_{idx}"
                        )

                    t1    = datetime.strptime(entrada, "%H:%M")
                    t2    = datetime.strptime(saida,   "%H:%M")
                    delta = (t2 - t1).seconds / 3600

                    if delta > 0:
                        total_horas += delta
                        periodos_validos.append({
                            "entrada": entrada,
                            "saida":   saida,
                            "horas":   round(delta, 2)
                        })
                        st.markdown(
                            f"<p style='text-align:right;color:#DC2626;"
                            f"font-weight:700;font-size:0.8rem;margin:0 0 4px;'>"
                            f"= {fh(delta)}</p>",
                            unsafe_allow_html=True
                        )
                    elif delta < 0:
                        st.warning("⚠️ Saída antes da entrada")

                if total_horas > 0:
                    st.markdown(
                        f"<div style='background:#7F1D1D;border-radius:10px;"
                        f"padding:12px;text-align:center;margin:10px 0;'>"
                        f"<p style='color:rgba(255,255,255,0.7);font-size:0.7rem;margin:0;'>"
                        f"TOTAL</p>"
                        f"<p style='color:white;font-size:1.8rem;font-weight:900;margin:2px 0 0;'>"
                        f"{fh(total_horas)}</p></div>",
                        unsafe_allow_html=True
                    )

                relatorio = st.text_area(
                    "📝 Descrição (opcional)",
                    placeholder="Ex: Montagem de instrumentos...",
                    key="reg_relat", height=70
                )

                st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

                # Desktop: + Período à esquerda, Guardar à direita
                # Mobile: + Período em cima, Guardar em baixo
                st.markdown("""
                <style>
                @media (max-width: 768px) {
                    [data-testid="stHorizontalBlock"]:has(button) {
                        flex-direction: column !important;
                    }
                }
                </style>
                """, unsafe_allow_html=True)

                col_c, col_g = st.columns(2)
                with col_c:
                    mais_per = st.form_submit_button(
                        "➕ Período", use_container_width=True
                    )
                with col_g:
                    guardar = st.form_submit_button(
                        "💾 Guardar", use_container_width=True, type="primary"
                    )

            if st.button("← Voltar", key="btn_voltar"):
                st.session_state.show_reg_form    = False
                st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"17:00"}]
                st.rerun()

            if mais_per:
                st.session_state.periodos_trabalho.append({"entrada":"13:00","saida":"17:00"})
                st.rerun()

            if guardar:
                if total_horas <= 0:
                    st.error("⚠️ Horas têm de ser superiores a 0.")
                elif not obra_sel or obra_sel == "Sem obras":
                    st.error("⚠️ Seleciona uma obra.")
                else:
                    for pv in periodos_validos:
                        new_r = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Data":        data_sel.strftime("%d/%m/%Y"),
                            "Técnico":     user_nome,
                            "Obra":        obra_sel,
                            "Frente":      frente_sel,
                            "Turnos":      f"{pv['entrada']}-{pv['saida']}",
                            "Horas_Total": pv['horas'],
                            "Relatorio":   relatorio,
                            "Status":      "0",
                            "Periodo":     periodos_validos.index(pv) + 1
                        }])
                        updated = pd.concat(
                            [registos_db, new_r], ignore_index=True
                        ) if not registos_db.empty else new_r
                        save_db(updated, "registos.csv")
                        log_audit(
                            usuario=user_nome, acao="REGISTAR_PONTO",
                            tabela="registos.csv",
                            registro_id=new_r['ID'].iloc[0],
                            detalhes=f"{pv['horas']}h em {obra_sel} "
                                     f"({pv['entrada']}-{pv['saida']})",
                            ip=""
                        )

                    criar_notificacao(
                        destinatario="admin",
                        titulo="📋 Novo Registo de Ponto",
                        mensagem=f"{user_nome} registou {fh(total_horas)} "
                                 f"em {obra_sel}",
                        tipo="info",
                        acao_url="/admin?tab=validacoes"
                    )

                    st.session_state.show_reg_form    = False
                    st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"17:00"}]
                    inv()
                    st.success(f"✅ {fh(total_horas)} registadas em {obra_sel}")
                    time.sleep(1)
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TABS RESTANTES
    # ════════════════════════════════════════════════════════════════
    offset = 0
    if is_chefe:
        offset = 1
        with tabs[1]:
            st.markdown("### 📊 Folha de Ponto")
            st.info("Seleciona a obra e o período para gerar a folha assinada.")

            obra_f = st.selectbox("Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Sem obras"],
                key="fp_obra")
            col_fi, col_ff = st.columns(2)
            with col_fi:
                sem_ini = st.date_input("Início",
                    value=hoje - timedelta(days=hoje.weekday()), key="fp_ini")
            with col_ff:
                sem_fim = st.date_input("Fim",
                    value=hoje - timedelta(days=hoje.weekday()) + timedelta(days=6),
                    key="fp_fim")

            if not registos_db.empty:
                dp      = pd.to_datetime(registos_db['Data'],
                              dayfirst=True, errors='coerce').dt.date
                regs_fp = registos_db[
                    (registos_db['Obra'] == obra_f) &
                    (dp >= sem_ini) & (dp <= sem_fim)
                ]
                if not regs_fp.empty:
                    for tec in regs_fp['Técnico'].unique():
                        rt    = regs_fp[regs_fp['Técnico'] == tec]
                        total = pd.to_numeric(rt['Horas_Total'],
                                    errors='coerce').fillna(0).sum()
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:10px;"
                            f"padding:12px 16px;margin-bottom:8px;'>"
                            f"<b style='color:#F1F5F9;'>👤 {tec}</b>"
                            f"<span style='float:right;color:#DC2626;font-weight:900;'>"
                            f"{fh(total)}</span><br>"
                            f"<small style='color:#64748B;'>{len(rt)} dia(s)</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                    nome_resp = st.text_input("Nome do Responsável", key="fp_resp")
                    if st.button("🔒 Gerar Folha com Selo",
                                  use_container_width=True, type="primary"):
                        if nome_resp:
                            import secrets as sec
                            selo = sec.token_hex(6).upper()
                            ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            nova = pd.DataFrame([{
                                "ID": str(uuid.uuid4())[:8].upper(),
                                "Obra": obra_f,
                                "Periodo": f"{sem_ini.strftime('%d/%m')}-{sem_fim.strftime('%d/%m/%Y')}",
                                "Responsavel": nome_resp,
                                "Data_Assinatura": ts,
                                "Assinatura_b64": "",
                                "Selo": selo, "Status": "Assinado"
                            }])
                            upd = pd.concat([folhas_db, nova], ignore_index=True) \
                                  if not folhas_db.empty else nova
                            save_db(upd, "folhas_ponto.csv")
                            st.success(f"✅ Folha #{selo} gerada — {ts}")
                            inv()
                        else:
                            st.warning("⚠️ Indica o nome do responsável.")
                else:
                    st.info("Sem registos para este período.")

    with tabs[1 + offset]:
        st.markdown("### 🛡️ Segurança HSE")
        for ic, tit, des in REGRAS_OURO:
            with st.expander(f"{ic} {tit}"):
                st.write(des)
        st.divider()
        st.markdown("### 🚨 Reportar Incidente")
        with st.form("hse_form"):
            o_hse = st.selectbox("Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                key="hse_obra")
            g_hse = st.selectbox("Gravidade",
                ["Baixa","Média","Alta (Crítica)"], key="hse_grav")
            d_hse = st.text_area("Descrição", key="hse_desc")
            if st.form_submit_button("📤 Submeter",
                use_container_width=True, type="primary"):
                if d_hse:
                    ni = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8].upper(),
                        "Data": hoje.strftime("%d/%m/%Y"),
                        "Utilizador": user_nome, "Obra": o_hse,
                        "Status": "Aberto", "Gravidade": g_hse,
                        "Descricao": d_hse, "Tipo": "HSE"
                    }])
                    upd = pd.concat([incs_db, ni], ignore_index=True) \
                          if not incs_db.empty else ni
                    save_db(upd, "incidentes.csv")
                    inv()
                    st.success("✅ Alerta HSE enviado!")
                    st.rerun()
                else:
                    st.warning("⚠️ Descreve o incidente.")

    # ════════════════════════════════════════════════════════════════
    # TAB PERFIL
    # ════════════════════════════════════════════════════════════════
    with tabs[-2]:
        st.markdown("### 👤 Perfil")
        if user_data is not None:
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                pv  = user_data.get('PDFs_Validados','Não')
                pvd = user_data.get('PDFs_Validacao_Data','')
                cp_ = "#10B981" if pv=='Sim' else "#EF4444"
                st.markdown(
                    f"<div style='background:#1E293B;border:2px solid {cp_};"
                    f"border-radius:10px;padding:12px;text-align:center;'>"
                    f"<b style='color:{cp_};'>{'✅' if pv=='Sim' else '❌'} Documentos</b>"
                    f"<p style='color:#64748B;font-size:0.73rem;margin:5px 0 0;'>"
                    f"{'Em ' + pvd if pv=='Sim' else 'Pendentes'}</p></div>",
                    unsafe_allow_html=True
                )
            with col_v2:
                ps  = user_data.get('PrecoHoraStatus','')
                pv_ = user_data.get('PrecoHora','15.0')
                pd_ = user_data.get('PrecoHoraData','')
                cp2 = "#10B981" if ps=='Aceite' else "#EF4444" if ps=='Recusado' else "#F59E0B"
                ic_ = "✅" if ps=='Aceite' else "❌" if ps=='Recusado' else "⏳"
                st.markdown(
                    f"<div style='background:#1E293B;border:2px solid {cp2};"
                    f"border-radius:10px;padding:12px;text-align:center;'>"
                    f"<b style='color:{cp2};'>{ic_} €{pv_}/h</b>"
                    f"<p style='color:#64748B;font-size:0.73rem;margin:5px 0 0;'>"
                    f"{'Aceite em ' + pd_ if ps=='Aceite' else ps if ps else 'Pendente'}"
                    f"</p></div>",
                    unsafe_allow_html=True
                )
            st.divider()
            try:
                cb = json.loads(user_data.get('Campos_Bloqueados','[]'))
            except:
                cb = []

            with st.form("form_perfil"):
                c1, c2 = st.columns(2)
                with c1:
                    tel  = st.text_input("Telefone",
                        value=user_data.get('Telefone',''),
                        disabled='Telefone' in cb, key="p_tel")
                    em_  = st.text_input("Email",
                        value=user_data.get('Email',''),
                        disabled='Email' in cb, key="p_em")
                    ce_  = st.text_input("Tel. Emergência",
                        value=user_data.get('Contacto_Emergencia',''),
                        disabled='Contacto_Emergencia' in cb, key="p_ce")
                with c2:
                    ne_  = st.text_input("Nome Emergência",
                        value=user_data.get('Nome_Emergencia',''),
                        disabled='Nome_Emergencia' in cb, key="p_ne")
                    gp_  = st.text_input("Grau Parentesco",
                        value=user_data.get('Grau_Parentesco',''),
                        disabled='Grau_Parentesco' in cb, key="p_gp")
                mor_ = st.text_input("Morada",
                    value=user_data.get('Morada',''),
                    disabled='Morada' in cb, key="p_mor")
                c3,c4,c5 = st.columns(3)
                with c3:
                    loc_ = st.text_input("Localidade",
                        value=user_data.get('Localidade',''),
                        disabled='Localidade' in cb, key="p_loc")
                with c4:
                    con_ = st.text_input("Concelho",
                        value=user_data.get('Concelho',''),
                        disabled='Concelho' in cb, key="p_con")
                with c5:
                    cp3  = st.text_input("Cód. Postal",
                        value=user_data.get('Codigo_Postal',''),
                        disabled='Codigo_Postal' in cb, key="p_cp")
                c6,c7 = st.columns(2)
                with c6:
                    pa_ = st.text_input("Password atual", type="password", key="p_pa")
                with c7:
                    pn_ = st.text_input("Nova password",  type="password", key="p_pn")
                pin_ = st.text_input("🔢 Novo PIN (4 dígitos)",
                    max_chars=4, key="p_pin", placeholder="0000")
                st.info("🔒 Nome, Tipo, Cargo e IBAN são geridos pelo Administrador.")
                if st.form_submit_button("💾 Guardar",
                    use_container_width=True, type="primary"):
                    ul = _load_users_fresh()
                    if not ul.empty:
                        m = ul['Nome'] == user_nome
                        if m.any():
                            for campo, val in {
                                'Telefone': tel.strip(), 'Email': em_.strip(),
                                'Morada': mor_.strip(), 'Localidade': loc_.strip(),
                                'Concelho': con_.strip(), 'Codigo_Postal': cp3.strip(),
                                'Contacto_Emergencia': ce_.strip(),
                                'Nome_Emergencia': ne_.strip(),
                                'Grau_Parentesco': gp_.strip(),
                            }.items():
                                if campo not in cb:
                                    ul.loc[m, campo] = val
                            if pn_.strip() and pa_.strip():
                                from core import cp as chk
                                ph = str(ul.loc[m,'Password'].values[0])
                                if chk(pa_.strip(), ph):
                                    if len(pn_.strip()) >= 4:
                                        ul.loc[m,'Password'] = hp(pn_.strip())
                                        st.success("🔐 Password atualizada!")
                                    else:
                                        st.error("❌ Mínimo 4 caracteres.")
                                else:
                                    st.error("❌ Password atual incorreta.")
                            if pin_.strip():
                                if len(pin_.strip())==4 and pin_.strip().isdigit():
                                    ul.loc[m,'PIN'] = pin_.strip()
                                else:
                                    st.error("❌ PIN: 4 dígitos numéricos.")
                            save_db(ul, "usuarios.csv")
                            log_audit(usuario=user_nome, acao="EDITAR_PERFIL",
                                tabela="usuarios.csv", registro_id=user_nome,
                                detalhes="Perfil atualizado", ip="")
                            inv()
                            st.success("✅ Perfil atualizado!")
                            st.rerun()

            # ── Contrato de Trabalho ──────────────────────────────
            st.markdown("---")
            st.markdown("#### 📄 Contrato de Trabalho")

            ct_enviado  = user_data.get('Contrato_Enviado','')  == 'Sim'
            ct_assinado = user_data.get('Contrato_Assinado','') == 'Sim'
            ct_validado = user_data.get('Contrato_Validado_Admin','') == 'Sim'

            if ct_validado:
                st.success("✅ Contrato assinado e validado pela empresa.")

            elif ct_assinado:
                st.info("⏳ Assinatura submetida — aguarda validação do RH.")

            elif ct_enviado:
                st.info("📄 O teu contrato está disponível para assinar.")
                ct_b64 = user_data.get('Contrato_b64','')
                if ct_b64:
                    try:
                        ct_bytes = base64.b64decode(ct_b64)
                        st.download_button(
                            "📥 Descarregar Contrato para Assinar",
                            data=ct_bytes,
                            file_name=f"contrato_{user_nome.replace(' ','_')}.docx",
                            mime="application/vnd.openxmlformats-officedocument"
                                 ".wordprocessingml.document",
                            key="btn_dl_ct_colab"
                        )
                    except:
                        st.error("Erro ao processar o contrato.")

                st.markdown(
                    "<div style='background:rgba(59,130,246,0.1);border-radius:10px;"
                    "padding:14px;margin:12px 0;border-left:3px solid #3B82F6;'>"
                    "<p style='color:#93C5FD;font-size:0.85rem;margin:0;'>"
                    "📋 <b>Instruções:</b><br>"
                    "1. Descarrega o contrato acima<br>"
                    "2. Imprime e assina à mão<br>"
                    "3. Fotografa ou digitaliza<br>"
                    "4. Faz upload abaixo</p></div>",
                    unsafe_allow_html=True
                )

                ficheiro_assin = st.file_uploader(
                    "📤 Upload do contrato assinado (foto/PDF)",
                    type=["jpg","jpeg","png","pdf"],
                    key="colab_ct_upload"
                )
                if ficheiro_assin:
                    if st.button("✅ Submeter assinatura",
                                  key="btn_submeter_assin",
                                  type="primary",
                                  use_container_width=True):
                        f_b64 = base64.b64encode(ficheiro_assin.read()).decode()
                        u_ct  = _load_users_fresh()
                        mask  = u_ct['Nome'] == user_nome
                        if mask.any():
                            u_ct.loc[mask, 'Contrato_Assinado']        = 'Sim'
                            u_ct.loc[mask, 'Contrato_Assinatura_b64']  = f_b64
                            u_ct.loc[mask, 'Contrato_Assinatura_Data'] = \
                                datetime.now().strftime("%d/%m/%Y %H:%M")
                            save_db(u_ct, "usuarios.csv")
                            criar_notificacao(destinatario="admin",
                                titulo="✍️ Contrato Assinado",
                                mensagem=f"{user_nome} submeteu o contrato assinado.",
                                tipo="success", acao_url="/admin?tab=rh")
                            log_audit(usuario=user_nome, acao="SUBMETER_CONTRATO",
                                      tabela="usuarios.csv", registro_id=user_nome,
                                      detalhes="Contrato assinado submetido", ip="")
                            inv()
                            st.success("✅ Assinatura submetida! O RH será notificado.")
                            time.sleep(1)
                            st.rerun()
            else:
                st.markdown(
                    "<p style='color:#64748B;font-size:0.85rem;'>"
                    "⏳ Contrato ainda não disponível. "
                    "Será notificado quando estiver pronto.</p>",
                    unsafe_allow_html=True
                )

            # ── Histórico de Diárias ──────────────────────────────
            st.markdown("---")
            st.markdown("#### 💶 Histórico de Diárias")
            try:
                diarias_hist = load_db("diarias_pagamentos.csv", [
                    "ID","Semana_Inicio","Semana_Fim","Técnico",
                    "Obras","Dias_Total","Valor_Total","Status",
                    "Data_Pagamento","Recibo_b64"
                ], silent=True)
                if not diarias_hist.empty:
                    meus_pag = diarias_hist[
                        diarias_hist['Técnico'] == user_nome
                    ].sort_values('Semana_Inicio', ascending=False)
                    if not meus_pag.empty:
                        total_recebido = pd.to_numeric(
                            meus_pag['Valor_Total'], errors='coerce'
                        ).fillna(0).sum()
                        st.markdown(
                            f"<p style='color:#10B981;font-weight:700;'>"
                            f"Total recebido: € {total_recebido:.2f}</p>",
                            unsafe_allow_html=True
                        )
                        for _, dp in meus_pag.head(10).iterrows():
                            col_di, col_dr = st.columns([4, 1])
                            with col_di:
                                st.markdown(
                                    f"<div style='background:#1E293B;"
                                    f"border-radius:8px;padding:10px;"
                                    f"margin-bottom:5px;'>"
                                    f"<b style='color:#F1F5F9;font-size:0.85rem;'>"
                                    f"{dp.get('Semana_Inicio','')} — "
                                    f"{dp.get('Semana_Fim','')}</b>"
                                    f"<span style='float:right;color:#10B981;"
                                    f"font-weight:700;'>"
                                    f"€ {float(dp.get('Valor_Total',0)):.2f}"
                                    f"</span><br>"
                                    f"<small style='color:#64748B;'>"
                                    f"{dp.get('Obras','')} · "
                                    f"{dp.get('Dias_Total','')} dia(s) · "
                                    f"{dp.get('Status','')}</small>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                            with col_dr:
                                rec = dp.get('Recibo_b64','')
                                if rec:
                                    try:
                                        st.download_button(
                                            "📄",
                                            data=base64.b64decode(rec),
                                            file_name=(
                                                f"recibo_"
                                                f"{dp.get('Semana_Inicio','').replace('/','')}"
                                                f".pdf"
                                            ),
                                            mime="application/pdf",
                                            key=f"dp_{dp.get('ID','')}",
                                            use_container_width=True
                                        )
                                    except:
                                        pass
                    else:
                        st.info("Sem diárias registadas.")
                else:
                    st.info("Sem diárias registadas.")
            except:
                st.info("Módulo de diárias não disponível.")

        else:
            st.warning("⚠️ Não foi possível carregar os dados.")

    # ════════════════════════════════════════════════════════════════
    # TAB PEDIDOS
    # ════════════════════════════════════════════════════════════════
    with tabs[-1]:
        st.markdown("### 📦 Pedidos")
        s1,s2,s3,s4,s5,s6 = st.tabs([
            "🔧 Ferramentas","🦺 EPIs","📦 Materiais",
            "⛽ Gasóleo","🔧 Avarias","📋 Os Meus"
        ])

        def _notif(t, m):
            criar_notificacao(destinatario="admin", titulo=t,
                mensagem=m, tipo="warning", acao_url="/admin?tab=validacoes")

        with s1:
            with st.form("ff"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="ff_o")
                d_ = st.text_area("Descrição", key="ff_d")
                u_ = st.selectbox("Urgência", ["Baixa","Média","Alta"], key="ff_u")
                f_ = st.file_uploader("Foto opcional",
                    type=["png","jpg","jpeg"], key="ff_f")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    if d_:
                        fb = process_and_compress_image(f_) if f_ else None
                        n  = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                            "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante":user_nome,"Obra":o_,
                            "Descricao":d_,"Urgencia":u_,
                            "Foto_b64":fb,"Status":"Pendente"}])
                        upd = pd.concat([req_fer_db,n],ignore_index=True) \
                              if not req_fer_db.empty else n
                        save_db(upd,"req_ferramentas.csv")
                        _notif("🔧 Ferramenta",f"{user_nome}: {d_[:40]}")
                        inv(); st.success("✅"); st.rerun()
                    else: st.warning("⚠️ Descreve a ferramenta.")

        with s2:
            with st.form("fe"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="fe_o")
                i_ = st.selectbox("EPI",["Capacete","Óculos","Luvas","Botas",
                    "Arnés","Protetor Auditivo","Máscara","Outro"], key="fe_i")
                c1_,c2_ = st.columns(2)
                with c1_: t_ = st.selectbox("Tamanho",["P","M","G","XG","Único"],key="fe_t")
                with c2_: q_ = st.number_input("Qtd",min_value=1,value=1,key="fe_q")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    n = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                        "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante":user_nome,"Obra":o_,
                        "Item":i_,"Tamanho":t_,"Quantidade":q_,"Status":"Pendente"}])
                    upd = pd.concat([req_epi_db,n],ignore_index=True) \
                          if not req_epi_db.empty else n
                    save_db(upd,"req_epis.csv")
                    _notif("🦺 EPI",f"{user_nome}: {q_}x {i_}")
                    inv(); st.success("✅"); st.rerun()

        with s3:
            with st.form("fm"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="fm_o")
                d_ = st.text_area("Descrição", key="fm_d")
                c1_,c2_ = st.columns(2)
                with c1_: q_ = st.number_input("Qtd",min_value=1,value=1,key="fm_q")
                with c2_: u_ = st.selectbox("Unidade",["un","m","kg","l","cx"],key="fm_u")
                ug_ = st.selectbox("Urgência",["Baixa","Média","Alta"],key="fm_ug")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    if d_:
                        n = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                            "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante":user_nome,"Obra":o_,
                            "Descricao":d_,"Quantidade":q_,
                            "Unidade":u_,"Urgencia":ug_,"Status":"Pendente"}])
                        upd = pd.concat([req_mat_db,n],ignore_index=True) \
                              if not req_mat_db.empty else n
                        save_db(upd,"req_materiais.csv")
                        _notif("📦 Material",f"{user_nome}: {q_}{u_} de {d_[:30]}")
                        inv(); st.success("✅"); st.rerun()
                    else: st.warning("⚠️ Descreve o material.")

        with s4:
            with st.form("fg"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="fg_o")
                c1_,c2_ = st.columns(2)
                with c1_: l_ = st.number_input("Litros",min_value=0.0,step=0.5,key="fg_l")
                with c2_: v_ = st.number_input("Valor €",min_value=0.0,step=0.01,key="fg_v")
                dg_ = st.date_input("Data", value=hoje, key="fg_d")
                rg_ = st.file_uploader("📄 Recibo (obrigatório)",
                    type=["png","jpg","jpeg","pdf"],key="fg_r")
                og_ = st.text_area("Observações",key="fg_obs")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    if rg_ and l_>0:
                        rb = base64.b64encode(rg_.read()).decode() \
                             if rg_.type=="application/pdf" \
                             else process_and_compress_image(rg_)
                        n = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                            "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante":user_nome,"Obra":o_,
                            "Litros":l_,"Valor":v_,
                            "Data_Abastecimento":dg_.strftime("%d/%m/%Y"),
                            "Descricao":og_,"Recibo_b64":rb,
                            "Status":"Pendente","Tipo":"Gasóleo"}])
                        upd = pd.concat([req_mat_db,n],ignore_index=True) \
                              if not req_mat_db.empty else n
                        save_db(upd,"req_materiais.csv")
                        _notif("⛽ Gasóleo",f"{user_nome}: {l_}L")
                        inv(); st.success("✅"); st.rerun()
                    else: st.warning("⚠️ Faz upload do recibo e indica os litros.")

        with s5:
            with st.form("fa"):
                o_  = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="fa_o")
                eq_ = st.text_input("Equipamento/Viatura",
                    key="fa_eq", placeholder="Ex: Viatura ABC-123")
                d_  = st.text_area("Descrição da avaria",key="fa_d")
                c1_,c2_ = st.columns(2)
                with c1_: u_ = st.selectbox("Urgência",
                    ["Baixa","Média","Alta","Crítica - Paragem"],key="fa_u")
                with c2_: v_ = st.number_input("Valor Est. €",min_value=0.0,key="fa_v")
                ft_ = st.file_uploader("📄 Fatura/Orçamento (obrigatório)",
                    type=["png","jpg","jpeg","pdf"],key="fa_f")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    if ft_ and d_:
                        fb = base64.b64encode(ft_.read()).decode() \
                             if ft_.type=="application/pdf" \
                             else process_and_compress_image(ft_)
                        n = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                            "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante":user_nome,"Obra":o_,
                            "Equipamento":eq_,"Descricao":d_,
                            "Urgencia":u_,"Valor_Estimado":v_,
                            "Fatura_b64":fb,"Status":"Pendente","Tipo":"Avaria"}])
                        upd = pd.concat([incs_db,n],ignore_index=True) \
                              if not incs_db.empty else n
                        save_db(upd,"incidentes.csv")
                        _notif("🔧 Avaria",f"{u_}: {eq_} em {o_}")
                        inv(); st.success("✅"); st.rerun()
                    else: st.warning("⚠️ Descreve e faz upload da fatura.")

        with s6:
            st.markdown("#### 📋 Os Meus Pedidos")
            sem = True
            for db_,tp_,cp4 in [
                (req_fer_db,"🔧","Descricao"),
                (req_epi_db,"🦺","Item"),
                (req_mat_db,"📦","Descricao"),
            ]:
                if not db_.empty and 'Solicitante' in db_.columns:
                    m_ = db_[db_['Solicitante']==user_nome]
                    if not m_.empty:
                        sem = False
                        for _,p_ in m_.tail(5).iterrows():
                            cor = {"Pendente":"#F97316","Aprovado":"#10B981",
                                   "Rejeitado":"#EF4444"}.get(
                                       p_.get('Status',''),"#6B7280")
                            st.markdown(
                                f"<div style='background:#1E293B;padding:10px;"
                                f"border-radius:9px;margin-bottom:5px;"
                                f"border-left:3px solid {cor};'>"
                                f"<span style='color:#F1F5F9;'>"
                                f"{tp_} {str(p_.get(cp4,''))[:40]}</span>"
                                f"<span style='color:{cor};font-size:0.77rem;"
                                f"float:right;font-weight:700;'>"
                                f"{p_.get('Status','')}</span><br>"
                                f"<small style='color:#475569;'>"
                                f"{p_.get('Data','')}</small></div>",
                                unsafe_allow_html=True
                            )
            if sem:
                st.info("📋 Ainda não fizeste nenhum pedido.")

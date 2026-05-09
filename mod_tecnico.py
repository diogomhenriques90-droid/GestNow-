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

# Horas em intervalos de 30 minutos para dropdown
_HORAS = [f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)]

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

    try:
        users_fresh = _load_users_fresh()
        user_match  = users_fresh[users_fresh['Nome'] == user_nome]
        user_data   = user_match.iloc[0] if not user_match.empty else None
        user_idx    = user_match.index[0] if not user_match.empty else None
    except:
        user_data = None
        user_idx  = None

    # ── CSS GERAL — tema claro com acentos vermelhos ──────────────────
    st.markdown("""
    <style>
    /* Fundo branco geral */
    .stApp {
        background: #F5F5F5 !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%) !important;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #FFFFFF;
        border-bottom: 2px solid #E5E7EB;
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        color: #6B7280 !important;
        font-size: 0.8rem !important;
        padding: 10px 12px !important;
        border-radius: 0 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #DC2626 !important;
        font-weight: bold !important;
        border-bottom: 3px solid #DC2626 !important;
    }
    /* Cards brancos */
    .card-branco {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    /* Card de obra */
    .obra-card {
        background: #FFFFFF;
        border: 2px solid #E5E7EB;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .obra-card.selected {
        border-color: #DC2626;
        background: #FEF2F2;
    }
    /* Registo card */
    .reg-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border-left: 4px solid #E5E7EB;
    }
    .reg-card.pendente  { border-left-color: #F59E0B; }
    .reg-card.aprovado  { border-left-color: #10B981; }
    .reg-card.fechado   { border-left-color: #6B7280; }
    /* FAB */
    .fab-container {
        position: fixed;
        bottom: 85px;
        right: 20px;
        z-index: 9999;
    }
    /* Labels */
    .stTextInput label, .stSelectbox label, .stNumberInput label,
    .stTextArea label, .stRadio label, .stCheckbox label {
        color: #374151 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 8px !important;
    }
    .stSelectbox > div > div > div {
        background: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #D1D5DB !important;
    }
    /* Botão primário vermelho */
    .stButton > button[kind="primary"] {
        background: #DC2626 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="secondary"] {
        background: #FFFFFF !important;
        color: #374151 !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 10px !important;
    }
    /* Expander */
    .streamlit-expanderHeader {
        background: #FFFFFF !important;
        color: #111827 !important;
        border-radius: 10px !important;
    }
    /* Métricas */
    [data-testid="stMetricValue"] { color: #DC2626 !important; }
    [data-testid="stMetricLabel"] { color: #6B7280 !important; }
    /* Headings */
    h1,h2,h3,h4,h5,h6 { color: #111827 !important; }
    p, div, span, small { color: #374151; }
    </style>
    """, unsafe_allow_html=True)

    # ── Tabs principais ───────────────────────────────────────────────
    menu = ["📋 Pontos", "🛡️ HSE", "👤 Perfil", "📦 Pedidos"]
    if is_chefe:
        menu.insert(1, "📊 Folha de Ponto")

    tabs = st.tabs(menu)

    # ════════════════════════════════════════════════════════════════
    # TAB 0 — PONTOS
    # ════════════════════════════════════════════════════════════════
    with tabs[0]:
        hoje = date.today()

        if 'data_consulta'  not in st.session_state:
            st.session_state.data_consulta = hoje
        if 'semana_offset'  not in st.session_state:
            st.session_state.semana_offset = 0
        if 'show_reg_form'  not in st.session_state:
            st.session_state.show_reg_form = False
        if 'obra_selecionada' not in st.session_state:
            st.session_state.obra_selecionada = None
        if 'frente_selecionada' not in st.session_state:
            st.session_state.frente_selecionada = None

        data_ref   = hoje + timedelta(weeks=st.session_state.semana_offset)
        inicio_sem = data_ref - timedelta(days=data_ref.weekday())
        dias_sem   = [inicio_sem + timedelta(days=i) for i in range(7)]
        fim_sem    = dias_sem[-1]

        # ── Calendário horizontal compacto ────────────────────────
        # Calcular que dias têm registos
        dias_com_regs = set()
        if not registos_db.empty and 'Técnico' in registos_db.columns:
            ru = registos_db[registos_db['Técnico'] == user_nome]
            if not ru.empty:
                datas = pd.to_datetime(ru['Data'], dayfirst=True, errors='coerce').dt.date
                dias_com_regs = set(datas.dropna().tolist())

        # Header do calendário
        st.markdown(f"""
        <div style="background:#FFFFFF;border-radius:14px;padding:12px 15px;
            margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <p style="text-align:center;color:#111827;font-weight:700;
                font-size:1rem;margin:0 0 12px 0;">
                Pontos &nbsp;·&nbsp;
                <span style="color:#DC2626;">
                    {inicio_sem.strftime('%B %Y').capitalize()}
                </span>
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Navegação e dias
        col_prev, *day_cols, col_next = st.columns([0.5] + [1]*7 + [0.5])

        with col_prev:
            if st.button("‹", key="sem_prev", use_container_width=True):
                st.session_state.semana_offset -= 1
                novo_inicio = inicio_sem - timedelta(weeks=1)
                wd = min(st.session_state.data_consulta.weekday(), 6)
                st.session_state.data_consulta = novo_inicio + timedelta(days=wd)
                st.rerun()

        for col, d in zip(day_cols, dias_sem):
            with col:
                selecionado = d == st.session_state.data_consulta
                eh_hoje     = d == hoje
                tem_reg     = d in dias_com_regs
                dia_pt      = _DIAS_PT[d.weekday()]

                # Círculo vermelho para selecionado/hoje, ponto verde para com registo
                if selecionado:
                    bg = "#DC2626"; cor_txt = "white"; borda = "#DC2626"
                elif eh_hoje:
                    bg = "#FEE2E2"; cor_txt = "#DC2626"; borda = "#DC2626"
                else:
                    bg = "transparent"; cor_txt = "#374151"; borda = "transparent"

                dot = "🟢" if tem_reg and not selecionado else ""

                st.markdown(f"""
                <div style="text-align:center;margin-bottom:2px;">
                    <span style="font-size:0.65rem;color:#9CA3AF;font-weight:500;">
                        {dia_pt}
                    </span>
                </div>""", unsafe_allow_html=True)

                if st.button(
                    f"{d.day}{'●' if tem_reg and not selecionado else ''}",
                    key=f"day_{d.strftime('%Y%m%d')}",
                    use_container_width=True,
                    type="primary" if selecionado else "secondary"
                ):
                    st.session_state.data_consulta = d
                    st.session_state.show_reg_form = False
                    st.rerun()

        with col_next:
            if st.button("›", key="sem_next", use_container_width=True):
                st.session_state.semana_offset += 1
                novo_inicio = inicio_sem + timedelta(weeks=1)
                wd = min(st.session_state.data_consulta.weekday(), 6)
                st.session_state.data_consulta = novo_inicio + timedelta(days=wd)
                st.rerun()

        # ── Área de registos do dia ───────────────────────────────
        data_sel = st.session_state.data_consulta

        # Buscar registos do dia
        regs_dia = pd.DataFrame()
        if not registos_db.empty and 'Técnico' in registos_db.columns:
            meus = registos_db[registos_db['Técnico'] == user_nome]
            if not meus.empty:
                dp = pd.to_datetime(meus['Data'], dayfirst=True, errors='coerce').dt.date
                regs_dia = meus[dp == data_sel].copy()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        if not st.session_state.show_reg_form:
            # ── Vista de registos ─────────────────────────────────
            if not regs_dia.empty:
                total_dia = pd.to_numeric(
                    regs_dia['Horas_Total'], errors='coerce'
                ).fillna(0).sum()
                st.markdown(f"""
                <div style="background:#FFFFFF;border-radius:12px;padding:14px 16px;
                    margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);
                    display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#374151;font-weight:600;">
                        📅 {data_sel.strftime('%d de %B').capitalize()}
                    </span>
                    <span style="background:#FEE2E2;color:#DC2626;
                        padding:4px 12px;border-radius:20px;font-weight:700;font-size:0.9rem;">
                        {fh(total_dia)}
                    </span>
                </div>
                """, unsafe_allow_html=True)

                for _, r in regs_dia.iterrows():
                    status_info  = sl(r.get('Status','0'))
                    cor_s        = status_info[3]
                    txt_s        = status_info[0]
                    classe       = _STATUS_CSS.get(str(r.get('Status','0')), 'pendente')
                    horas_f      = fh(r.get('Horas_Total',0))
                    relat        = str(r.get("Relatorio",""))[:60]
                    turnos       = r.get("Turnos","")

                    st.markdown(f"""
                    <div class="reg-card {classe}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                            <div style="flex:1;">
                                <p style="margin:0;font-weight:700;color:#111827;font-size:0.95rem;">
                                    {r.get('Obra','')}
                                </p>
                                <p style="margin:3px 0;color:#6B7280;font-size:0.82rem;">
                                    {r.get('Frente','')}
                                    {f' · {turnos}' if turnos else ''}
                                </p>
                                {f'<p style="margin:3px 0;color:#9CA3AF;font-size:0.78rem;">{relat}</p>' if relat else ''}
                            </div>
                            <div style="text-align:right;margin-left:10px;">
                                <p style="margin:0;font-weight:800;color:#DC2626;font-size:1.1rem;">
                                    {horas_f}
                                </p>
                                <p style="margin:3px 0;color:{cor_s};font-size:0.75rem;font-weight:600;">
                                    {txt_s}
                                </p>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:#FFFFFF;border-radius:14px;padding:50px 20px;
                    text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-top:10px;">
                    <div style="font-size:3.5rem;margin-bottom:15px;">📋</div>
                    <p style="color:#6B7280;font-weight:600;margin:0 0 5px 0;font-size:0.95rem;">
                        Sem ponto registado neste dia
                    </p>
                    <p style="color:#9CA3AF;font-size:0.85rem;margin:0;">
                        {data_sel.strftime('%d de %B de %Y').capitalize()}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            # ── FAB — botão "+" flutuante ─────────────────────────
            st.markdown("""
            <div style='height:80px;'></div>
            """, unsafe_allow_html=True)

            # Simular FAB com botão vermelho fixo em baixo
            col_esp, col_fab = st.columns([4, 1])
            with col_fab:
                if st.button("＋", key="fab_add", type="primary",
                              use_container_width=True):
                    st.session_state.show_reg_form = True
                    st.session_state.obra_selecionada   = None
                    st.session_state.frente_selecionada = None
                    st.rerun()

        else:
            # ════════════════════════════════════════════════════════
            # FORMULÁRIO DE REGISTO — estilo Meiworld
            # ════════════════════════════════════════════════════════
            st.markdown(f"""
            <div style="background:#FFFFFF;border-radius:14px;padding:16px;
                margin-bottom:15px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <p style="margin:0;font-weight:700;color:#111827;font-size:1rem;">
                            {user_nome}
                        </p>
                        <p style="margin:0;color:#6B7280;font-size:0.85rem;">{cargo_user}</p>
                    </div>
                    <span style="background:#FEE2E2;color:#DC2626;
                        padding:5px 12px;border-radius:20px;font-weight:700;font-size:0.85rem;">
                        {data_sel.strftime('%d-%m-%Y')}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── PASSO 1: Selecionar Obra ──────────────────────────
            if st.session_state.obra_selecionada is None:
                st.markdown("""
                <p style="color:#374151;font-weight:700;font-size:0.95rem;margin-bottom:10px;">
                    🏗️ Selecione uma obra
                </p>
                """, unsafe_allow_html=True)

                # Barra de pesquisa
                pesq_obra = st.text_input("🔍 Pesquisar obra...",
                    key="pesq_obra", label_visibility="collapsed",
                    placeholder="🔍 Pesquisar obra...")

                obras_lista = obras_db[obras_db['Ativa']=='Ativa'] \
                              if not obras_db.empty else pd.DataFrame()

                if pesq_obra and not obras_lista.empty:
                    obras_lista = obras_lista[
                        obras_lista['Obra'].str.contains(pesq_obra, case=False, na=False)
                    ]

                if not obras_lista.empty:
                    for _, obra_row in obras_lista.iterrows():
                        obra_nome   = obra_row.get('Obra','')
                        obra_cod    = obra_row.get('Codigo','')
                        obra_cli    = obra_row.get('Cliente','')
                        obra_tipo   = obra_row.get('TipoObra','')
                        selecionado = st.session_state.obra_selecionada == obra_nome

                        col_card, col_btn = st.columns([4, 1])
                        with col_card:
                            st.markdown(f"""
                            <div class="obra-card {'selected' if selecionado else ''}">
                                <p style="margin:0;font-weight:700;color:#111827;font-size:0.9rem;">
                                    {obra_nome}
                                </p>
                                <p style="margin:3px 0;color:#6B7280;font-size:0.8rem;">
                                    {obra_tipo}
                                </p>
                                <p style="margin:0;color:#9CA3AF;font-size:0.75rem;
                                    font-family:monospace;">
                                    {obra_cod}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_btn:
                            st.markdown("<div style='height:20px;'></div>",
                                        unsafe_allow_html=True)
                            if st.button("✓", key=f"sel_obra_{obra_cod}",
                                          type="primary", use_container_width=True):
                                st.session_state.obra_selecionada = obra_nome
                                st.rerun()
                else:
                    st.info("📋 Sem obras ativas disponíveis.")

                col_canc, _ = st.columns([1, 3])
                with col_canc:
                    if st.button("← Cancelar", key="canc_obra",
                                  use_container_width=True):
                        st.session_state.show_reg_form = False
                        st.rerun()

            # ── PASSO 2: Selecionar Frente ────────────────────────
            elif st.session_state.frente_selecionada is None:
                obra_sel = st.session_state.obra_selecionada

                st.markdown(f"""
                <div style="background:#FEE2E2;border-radius:10px;
                    padding:10px 14px;margin-bottom:14px;">
                    <p style="margin:0;color:#DC2626;font-weight:700;font-size:0.9rem;">
                        ✓ {obra_sel}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <p style="color:#374151;font-weight:700;font-size:0.95rem;margin-bottom:10px;">
                    🔧 Selecione a frente de trabalho
                </p>
                """, unsafe_allow_html=True)

                for frente in TIPOS_FRENTE:
                    col_f, col_fb = st.columns([4, 1])
                    with col_f:
                        st.markdown(f"""
                        <div style="background:#FFFFFF;border:1px solid #E5E7EB;
                            border-radius:10px;padding:12px 14px;margin-bottom:8px;">
                            <p style="margin:0;color:#374151;font-weight:600;
                                font-size:0.9rem;">🔧 {frente}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_fb:
                        st.markdown("<div style='height:8px;'></div>",
                                    unsafe_allow_html=True)
                        if st.button("✓", key=f"sel_frente_{frente}",
                                      type="primary", use_container_width=True):
                            st.session_state.frente_selecionada = frente
                            st.rerun()

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("← Obra", key="back_obra",
                                  use_container_width=True):
                        st.session_state.obra_selecionada = None
                        st.rerun()
                with col_b2:
                    if st.button("✕ Cancelar", key="canc_frente",
                                  use_container_width=True):
                        st.session_state.show_reg_form    = False
                        st.session_state.obra_selecionada = None
                        st.rerun()

            # ── PASSO 3: Registar Horas ───────────────────────────
            else:
                obra_sel   = st.session_state.obra_selecionada
                frente_sel = st.session_state.frente_selecionada

                st.markdown(f"""
                <div style="background:#FEE2E2;border-radius:10px;
                    padding:10px 14px;margin-bottom:14px;">
                    <p style="margin:0 0 3px 0;color:#DC2626;font-weight:700;font-size:0.9rem;">
                        ✓ {obra_sel}
                    </p>
                    <p style="margin:0;color:#EF4444;font-size:0.82rem;">
                        🔧 {frente_sel}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <p style="color:#374151;font-weight:700;font-size:0.95rem;margin:0 0 12px 0;">
                    ⏱️ Registo de horas
                </p>""", unsafe_allow_html=True)

                # Períodos de trabalho
                if 'periodos_trabalho' not in st.session_state:
                    st.session_state.periodos_trabalho = [
                        {"entrada":"08:00","saida":"17:00"}
                    ]

                total_horas = 0.0
                periodos_validos = []

                for idx, periodo in enumerate(st.session_state.periodos_trabalho):
                    st.markdown(f"""
                    <div style="background:#F9FAFB;border-radius:10px;
                        padding:14px;margin-bottom:10px;
                        border:1px solid #E5E7EB;">
                        <p style="margin:0 0 10px 0;color:#374151;
                            font-weight:600;font-size:0.85rem;">
                            Período {idx+1}
                        </p>
                    </div>""", unsafe_allow_html=True)

                    col_e, col_s = st.columns(2)
                    with col_e:
                        # Dropdown de horas (intervalos 30 min)
                        idx_e = _HORAS.index(periodo["entrada"]) \
                                if periodo["entrada"] in _HORAS else 16  # 08:00
                        entrada = st.selectbox(
                            "Hora de entrada",
                            _HORAS, index=idx_e,
                            key=f"entrada_{idx}"
                        )
                    with col_s:
                        idx_s = _HORAS.index(periodo["saida"]) \
                                if periodo["saida"] in _HORAS else 34  # 17:00
                        saida = st.selectbox(
                            "Hora de saída",
                            _HORAS, index=idx_s,
                            key=f"saida_{idx}"
                        )

                    # Calcular horas
                    t1 = datetime.strptime(entrada, "%H:%M")
                    t2 = datetime.strptime(saida,   "%H:%M")
                    delta = (t2 - t1).seconds / 3600
                    if delta > 0:
                        total_horas += delta
                        periodos_validos.append({
                            "entrada": entrada,
                            "saida":   saida,
                            "horas":   round(delta, 2)
                        })
                        st.markdown(f"""
                        <div style="text-align:center;margin:5px 0 10px 0;">
                            <span style="background:#FEE2E2;color:#DC2626;
                                padding:4px 16px;border-radius:20px;
                                font-weight:700;font-size:0.85rem;">
                                {fh(delta)}
                            </span>
                        </div>""", unsafe_allow_html=True)
                    elif delta < 0:
                        st.warning("⚠️ Hora de saída anterior à entrada")

                # Adicionar período
                col_add, col_rem = st.columns(2)
                with col_add:
                    if st.button("➕ Adicionar período", key="add_per",
                                  use_container_width=True):
                        st.session_state.periodos_trabalho.append(
                            {"entrada":"13:00","saida":"17:00"}
                        )
                        st.rerun()
                with col_rem:
                    if len(st.session_state.periodos_trabalho) > 1:
                        if st.button("➖ Remover último", key="rem_per",
                                      use_container_width=True):
                            st.session_state.periodos_trabalho.pop()
                            st.rerun()

                # Total
                if total_horas > 0:
                    st.markdown(f"""
                    <div style="background:#DC2626;border-radius:12px;
                        padding:14px;text-align:center;margin:12px 0;">
                        <p style="margin:0;color:white;font-size:0.85rem;opacity:0.9;">
                            Total de horas
                        </p>
                        <p style="margin:4px 0 0 0;color:white;
                            font-size:2rem;font-weight:900;">
                            {fh(total_horas)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                # Horas normais / extras
                col_hn, col_he = st.columns(2)
                with col_hn:
                    h_normais = st.number_input(
                        "Horas normais", min_value=0.0,
                        max_value=float(max(total_horas, 0)),
                        value=min(8.0, total_horas),
                        step=0.5, key="h_normais"
                    )
                with col_he:
                    h_extras = round(max(total_horas - h_normais, 0), 2)
                    st.markdown(f"""
                    <div style="padding:8px 0;">
                        <label style="color:#374151;font-weight:500;font-size:0.9rem;">
                            Horas extras
                        </label>
                        <p style="margin:4px 0 0 0;font-size:1.1rem;
                            font-weight:700;color:#DC2626;">
                            {h_extras:.1f}h
                        </p>
                    </div>""", unsafe_allow_html=True)

                relat = st.text_area(
                    "📝 Descrição do trabalho (opcional)",
                    placeholder="Ex: Montagem de instrumentos, calibração...",
                    key="reg_relatorio"
                )

                st.markdown("<div style='height:10px;'></div>",
                            unsafe_allow_html=True)

                col_g, col_c = st.columns(2)
                with col_g:
                    guardar = st.button("💾 Guardar",
                        key="btn_guardar", type="primary",
                        use_container_width=True)
                with col_c:
                    cancelar = st.button("✕ Cancelar",
                        key="btn_cancelar",
                        use_container_width=True)

                if cancelar:
                    st.session_state.show_reg_form      = False
                    st.session_state.obra_selecionada   = None
                    st.session_state.frente_selecionada = None
                    st.session_state.periodos_trabalho  = [{"entrada":"08:00","saida":"17:00"}]
                    st.rerun()

                if guardar:
                    if total_horas <= 0:
                        st.error("⚠️ As horas têm de ser superiores a 0.")
                    else:
                        for pv in periodos_validos:
                            new_r = pd.DataFrame([{
                                "ID":         str(uuid.uuid4())[:8].upper(),
                                "Data":       data_sel.strftime("%d/%m/%Y"),
                                "Técnico":    user_nome,
                                "Obra":       obra_sel,
                                "Frente":     frente_sel,
                                "Turnos":     f"{pv['entrada']}-{pv['saida']}",
                                "Horas_Total":pv['horas'],
                                "Relatorio":  relat,
                                "Status":     "0",
                                "Periodo":    periodos_validos.index(pv) + 1
                            }])
                            updated = pd.concat(
                                [registos_db, new_r], ignore_index=True
                            ) if not registos_db.empty else new_r
                            save_db(updated, "registos.csv")
                            log_audit(
                                usuario=user_nome, acao="REGISTAR_PONTO",
                                tabela="registos.csv",
                                registro_id=new_r['ID'].iloc[0],
                                detalhes=f"{pv['horas']}h em {obra_sel}",
                                ip=""
                            )

                        criar_notificacao(
                            destinatario="admin",
                            titulo="📋 Novo Registo de Ponto",
                            mensagem=f"{user_nome} registou {fh(total_horas)} em {obra_sel}",
                            tipo="info", acao_url="/admin?tab=validacoes"
                        )

                        # Limpar estado
                        st.session_state.show_reg_form      = False
                        st.session_state.obra_selecionada   = None
                        st.session_state.frente_selecionada = None
                        st.session_state.periodos_trabalho  = [{"entrada":"08:00","saida":"17:00"}]
                        inv()
                        st.success(f"✅ Ponto registado! ({fh(total_horas)})")
                        time.sleep(1)
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB FOLHA DE PONTO (só chefe)
    # ════════════════════════════════════════════════════════════════
    offset = 0
    if is_chefe:
        offset = 1
        with tabs[1]:
            st.markdown("### 📊 Folha de Ponto & Assinatura Digital")

            obra_f = st.selectbox("Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Sem Obras"],
                key="esign_obra")

            inicio_sem_d = hoje - timedelta(days=hoje.weekday())
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                sem_ini = st.date_input("Início", value=inicio_sem_d, key="fp_ini")
            with col_p2:
                sem_fim = st.date_input("Fim",
                    value=inicio_sem_d + timedelta(days=6), key="fp_fim")

            if not registos_db.empty:
                regs_fp = registos_db[
                    (registos_db['Obra'] == obra_f) &
                    (pd.to_datetime(registos_db['Data'],
                        dayfirst=True, errors='coerce').dt.date >= sem_ini) &
                    (pd.to_datetime(registos_db['Data'],
                        dayfirst=True, errors='coerce').dt.date <= sem_fim)
                ]
                if not regs_fp.empty:
                    for tec in regs_fp['Técnico'].unique():
                        regs_t = regs_fp[regs_fp['Técnico'] == tec]
                        total  = pd.to_numeric(
                            regs_t['Horas_Total'], errors='coerce'
                        ).fillna(0).sum()
                        st.markdown(f"""
                        <div class="card-branco">
                            <b style="color:#111827;">👤 {tec}</b>
                            <span style="float:right;color:#DC2626;font-weight:700;">
                                {total:.1f}h
                            </span><br>
                            <small style="color:#6B7280;">
                                {len(regs_t)} dia(s)
                            </small>
                        </div>""", unsafe_allow_html=True)

                    st.markdown("### ✍️ Assinatura do Responsável")
                    canvas_sig = None
                    try:
                        canvas_sig = st_canvas(
                            fill_color="rgba(255,255,255,0)",
                            stroke_width=2.5, stroke_color="#DC2626",
                            background_color="#FFFFFF",
                            height=160, width=350, drawing_mode="freedraw",
                            key="canvas_esign_fp"
                        )
                    except:
                        st.info("ℹ️ Canvas não disponível.")

                    nome_resp = st.text_input("Nome do Responsável", key="fp_resp")
                    if st.button("🔒 Gerar Folha com Selo",
                                  use_container_width=True, type="primary",
                                  key="btn_gerar_folha"):
                        if nome_resp:
                            esign_id  = secrets.token_hex(6).upper()
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            sig_b64   = ""
                            if canvas_sig is not None and canvas_sig.image_data is not None:
                                sig_b64 = canvas_to_b64(canvas_sig.image_data) or ""
                            nova_folha = pd.DataFrame([{
                                "ID": str(uuid.uuid4())[:8].upper(),
                                "Obra": obra_f,
                                "Periodo": f"{sem_ini.strftime('%d/%m')} - {sem_fim.strftime('%d/%m/%Y')}",
                                "Responsavel": nome_resp,
                                "Data_Assinatura": timestamp,
                                "Assinatura_b64": sig_b64,
                                "Selo": esign_id, "Status": "Assinado"
                            }])
                            updated = pd.concat(
                                [folhas_db, nova_folha], ignore_index=True
                            ) if not folhas_db.empty else nova_folha
                            save_db(updated, "folhas_ponto.csv")
                            st.markdown(f"""
                            <div style="border:2px dashed #10B981;padding:15px;
                                background:#F0FDF4;border-radius:10px;
                                font-family:monospace;font-size:0.85rem;
                                color:#065F46;margin-top:15px;">
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

    # ════════════════════════════════════════════════════════════════
    # TAB HSE
    # ════════════════════════════════════════════════════════════════
    with tabs[1 + offset]:
        st.markdown("### 🛡️ Regras de Ouro HSE")
        for ic, tit, des in REGRAS_OURO:
            with st.expander(f"{ic} {tit}"):
                st.write(des)
        st.divider()
        st.markdown("### 🚨 Reportar Incidente")
        with st.form("hse_report"):
            io_hse = st.selectbox("Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                key="hse_obra")
            it_hse = st.selectbox("Gravidade",
                ["Baixa","Média","Alta (Crítica)"], key="hse_grav")
            id_hse = st.text_area("Descrição da Ocorrência", key="hse_desc")
            if st.form_submit_button("📤 Submeter Alerta HSE",
                                      use_container_width=True, type="primary"):
                if id_hse:
                    ni = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8].upper(),
                        "Data": date.today().strftime("%d/%m/%Y"),
                        "Utilizador": user_nome, "Obra": io_hse,
                        "Status": "Aberto", "Gravidade": it_hse,
                        "Descricao": id_hse, "Tipo": "HSE"
                    }])
                    updated = pd.concat([incs_db, ni], ignore_index=True) \
                              if not incs_db.empty else ni
                    save_db(updated, "incidentes.csv")
                    inv()
                    st.success("✅ Alerta HSE enviado!")
                    st.rerun()
                else:
                    st.warning("⚠️ Descreve o incidente.")

    # ════════════════════════════════════════════════════════════════
    # TAB PERFIL
    # ════════════════════════════════════════════════════════════════
    with tabs[-2]:
        st.markdown("### 👤 Perfil do Colaborador")

        if user_data is not None:
            # Badges de estado
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                pdfs_val  = user_data.get('PDFs_Validados', 'Não')
                pdfs_data = user_data.get('PDFs_Validacao_Data', '')
                cor_pdf   = "#10B981" if pdfs_val=='Sim' else "#EF4444"
                ic_pdf    = "✅" if pdfs_val=='Sim' else "❌"
                txt_pdf   = f"Validados em {pdfs_data}" if pdfs_val=='Sim' else "Pendentes"
                st.markdown(f"""
                <div style="background:#FFFFFF;border:2px solid {cor_pdf};
                    border-radius:10px;padding:12px;text-align:center;
                    box-shadow:0 1px 3px rgba(0,0,0,0.06);">
                    <b style="color:{cor_pdf};">{ic_pdf} Documentos</b>
                    <p style="color:#6B7280;font-size:0.78rem;margin:5px 0 0 0;">
                        {txt_pdf}
                    </p>
                </div>""", unsafe_allow_html=True)

            with col_v2:
                preco_s = user_data.get('PrecoHoraStatus','')
                preco_v = user_data.get('PrecoHora','15.0')
                preco_d = user_data.get('PrecoHoraData','')
                if preco_s == 'Aceite':
                    cor_p = "#10B981"; ic_p = "✅"; txt_p = f"Aceite em {preco_d}"
                elif preco_s == 'Recusado':
                    cor_p = "#EF4444"; ic_p = "❌"; txt_p = "Recusado — contactar admin"
                else:
                    cor_p = "#F59E0B"; ic_p = "⏳"; txt_p = "Aguarda validação"
                st.markdown(f"""
                <div style="background:#FFFFFF;border:2px solid {cor_p};
                    border-radius:10px;padding:12px;text-align:center;
                    box-shadow:0 1px 3px rgba(0,0,0,0.06);">
                    <b style="color:{cor_p};">{ic_p} €{preco_v}/h</b>
                    <p style="color:#6B7280;font-size:0.78rem;margin:5px 0 0 0;">
                        {txt_p}
                    </p>
                </div>""", unsafe_allow_html=True)

            st.divider()

            try:
                campos_bloqueados = json.loads(
                    user_data.get('Campos_Bloqueados','[]')
                )
            except:
                campos_bloqueados = []

            st.markdown("### ✏️ Editar Dados")

            with st.form("form_perfil"):
                col1, col2 = st.columns(2)
                with col1:
                    telefone = st.text_input("Telefone",
                        value=user_data.get('Telefone',''),
                        disabled='Telefone' in campos_bloqueados, key="e_tel")
                    email_v  = st.text_input("Email",
                        value=user_data.get('Email',''),
                        disabled='Email' in campos_bloqueados, key="e_email")
                    c_emerg  = st.text_input("Tel. Emergência",
                        value=user_data.get('Contacto_Emergencia',''),
                        disabled='Contacto_Emergencia' in campos_bloqueados,
                        key="e_emerg")
                with col2:
                    n_emerg = st.text_input("Nome Emergência",
                        value=user_data.get('Nome_Emergencia',''),
                        disabled='Nome_Emergencia' in campos_bloqueados,
                        key="e_n_emerg")
                    grau    = st.text_input("Grau Parentesco",
                        value=user_data.get('Grau_Parentesco',''),
                        disabled='Grau_Parentesco' in campos_bloqueados,
                        key="e_grau")

                morada = st.text_input("Morada",
                    value=user_data.get('Morada',''),
                    disabled='Morada' in campos_bloqueados, key="e_morada")
                col3, col4, col5 = st.columns(3)
                with col3:
                    local = st.text_input("Localidade",
                        value=user_data.get('Localidade',''),
                        disabled='Localidade' in campos_bloqueados, key="e_loc")
                with col4:
                    conc  = st.text_input("Concelho",
                        value=user_data.get('Concelho',''),
                        disabled='Concelho' in campos_bloqueados, key="e_conc")
                with col5:
                    cp    = st.text_input("Cód. Postal",
                        value=user_data.get('Codigo_Postal',''),
                        disabled='Codigo_Postal' in campos_bloqueados, key="e_cp")

                st.markdown("**🔐 Alterar Password**")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    pwd_atual = st.text_input("Password atual",
                        type="password", key="e_pwd_atual")
                with col_p2:
                    pwd_nova  = st.text_input("Nova password",
                        type="password", key="e_pwd_nova")

                novo_pin = st.text_input("🔢 Novo PIN (4 dígitos)",
                    max_chars=4, key="e_pin", placeholder="0000")

                st.info("🔒 Nome, Tipo, Cargo e IBAN são geridos pelo Administrador.")

                if st.form_submit_button("💾 Guardar Alterações",
                                          use_container_width=True, type="primary"):
                    u_live = _load_users_fresh()
                    if not u_live.empty:
                        mask = u_live['Nome'] == user_nome
                        if mask.any():
                            updates = {
                                'Telefone': telefone.strip(), 'Email': email_v.strip(),
                                'Morada': morada.strip(), 'Localidade': local.strip(),
                                'Concelho': conc.strip(), 'Codigo_Postal': cp.strip(),
                                'Contacto_Emergencia': c_emerg.strip(),
                                'Nome_Emergencia': n_emerg.strip(),
                                'Grau_Parentesco': grau.strip(),
                            }
                            for campo, valor in updates.items():
                                if campo not in campos_bloqueados:
                                    u_live.loc[mask, campo] = valor

                            if pwd_nova.strip() and pwd_atual.strip():
                                from core import cp as check_pwd
                                ph = str(u_live.loc[mask,'Password'].values[0])
                                if check_pwd(pwd_atual.strip(), ph):
                                    if len(pwd_nova.strip()) >= 4:
                                        u_live.loc[mask,'Password'] = hp(pwd_nova.strip())
                                        st.success("🔐 Password atualizada!")
                                    else:
                                        st.error("❌ Mínimo 4 caracteres.")
                                else:
                                    st.error("❌ Password atual incorreta.")

                            if novo_pin.strip():
                                if len(novo_pin.strip())==4 and novo_pin.strip().isdigit():
                                    u_live.loc[mask,'PIN'] = novo_pin.strip()
                                else:
                                    st.error("❌ PIN deve ter 4 dígitos numéricos.")

                            save_db(u_live, "usuarios.csv")
                            log_audit(usuario=user_nome, acao="EDITAR_PERFIL",
                                      tabela="usuarios.csv", registro_id=user_nome,
                                      detalhes="Perfil atualizado", ip="")
                            inv()
                            st.success("✅ Perfil atualizado com sucesso!")
                            st.rerun()
        else:
            st.warning("⚠️ Não foi possível carregar os dados.")

    # ════════════════════════════════════════════════════════════════
    # TAB PEDIDOS
    # ════════════════════════════════════════════════════════════════
    with tabs[-1]:
        st.markdown("### 📦 Pedidos & Reportes")

        sub_fer, sub_epi, sub_mat, sub_gas, sub_avar, sub_meus = st.tabs([
            "🔧 Ferramentas","🦺 EPIs","📦 Materiais",
            "⛽ Gasóleo","🔧 Avarias","📋 Os Meus"
        ])

        with sub_fer:
            with st.form("form_fer"):
                obra_ped = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="pf_obra")
                desc_fer = st.text_area("Descrição", key="pf_desc")
                urg_fer  = st.selectbox("Urgência",
                    ["Baixa","Média","Alta"], key="pf_urg")
                foto_fer = st.file_uploader("Foto (opcional)",
                    type=["png","jpg","jpeg"], key="pf_foto")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    if desc_fer:
                        foto_b64 = process_and_compress_image(foto_fer) \
                                   if foto_fer else None
                        novo = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_ped,
                            "Descricao": desc_fer, "Urgencia": urg_fer,
                            "Foto_b64": foto_b64, "Status": "Pendente"
                        }])
                        updated = pd.concat([req_fer_db, novo], ignore_index=True) \
                                  if not req_fer_db.empty else novo
                        save_db(updated, "req_ferramentas.csv")
                        criar_notificacao(destinatario="admin",
                            titulo="🔧 Pedido Ferramenta",
                            mensagem=f"{user_nome}: {desc_fer[:40]}",
                            tipo="warning", acao_url="/admin?tab=validacoes")
                        inv(); st.success("✅ Pedido enviado!"); st.rerun()
                    else:
                        st.warning("⚠️ Descreve a ferramenta.")

        with sub_epi:
            with st.form("form_epi"):
                obra_epi = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="pe_obra")
                item_epi = st.selectbox("EPI",
                    ["Capacete","Óculos","Luvas","Botas","Arnés",
                     "Protetor Auditivo","Máscara","Outro"], key="pe_item")
                col_t, col_q = st.columns(2)
                with col_t: tam_epi = st.selectbox("Tamanho",
                    ["P","M","G","XG","Único"], key="pe_tam")
                with col_q: qtd_epi = st.number_input("Qtd",
                    min_value=1, value=1, key="pe_qtd")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    novo = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8].upper(),
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante": user_nome, "Obra": obra_epi,
                        "Item": item_epi, "Tamanho": tam_epi,
                        "Quantidade": qtd_epi, "Status": "Pendente"
                    }])
                    updated = pd.concat([req_epi_db, novo], ignore_index=True) \
                              if not req_epi_db.empty else novo
                    save_db(updated, "req_epis.csv")
                    criar_notificacao(destinatario="admin",
                        titulo="🦺 Pedido EPI",
                        mensagem=f"{user_nome}: {qtd_epi}x {item_epi}",
                        tipo="warning", acao_url="/admin?tab=validacoes")
                    inv(); st.success("✅ Pedido enviado!"); st.rerun()

        with sub_mat:
            with st.form("form_mat"):
                obra_mat = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="pm_obra")
                desc_mat = st.text_area("Descrição", key="pm_desc")
                col_q2, col_u = st.columns(2)
                with col_q2: qtd_mat  = st.number_input("Qtd",
                    min_value=1, value=1, key="pm_qtd")
                with col_u:  unid_mat = st.selectbox("Unidade",
                    ["un","m","kg","l","cx"], key="pm_unid")
                urg_mat = st.selectbox("Urgência",
                    ["Baixa","Média","Alta"], key="pm_urg")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    if desc_mat:
                        novo = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_mat,
                            "Descricao": desc_mat, "Quantidade": qtd_mat,
                            "Unidade": unid_mat, "Urgencia": urg_mat,
                            "Status": "Pendente"
                        }])
                        updated = pd.concat([req_mat_db, novo], ignore_index=True) \
                                  if not req_mat_db.empty else novo
                        save_db(updated, "req_materiais.csv")
                        criar_notificacao(destinatario="admin",
                            titulo="📦 Pedido Material",
                            mensagem=f"{user_nome}: {qtd_mat}{unid_mat} de {desc_mat[:30]}",
                            tipo="warning", acao_url="/admin?tab=validacoes")
                        inv(); st.success("✅ Pedido enviado!"); st.rerun()
                    else:
                        st.warning("⚠️ Descreve o material.")

        with sub_gas:
            with st.form("form_gas"):
                obra_gas  = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="pg_obra")
                col_l, col_v = st.columns(2)
                with col_l: litros = st.number_input("Litros",
                    min_value=0.0, step=0.5, key="pg_lit")
                with col_v: valor  = st.number_input("Valor €",
                    min_value=0.0, step=0.01, key="pg_val")
                data_gas = st.date_input("Data",
                    value=date.today(), key="pg_data")
                recibo   = st.file_uploader("📄 Recibo (obrigatório)",
                    type=["png","jpg","jpeg","pdf"], key="pg_rec")
                obs_gas  = st.text_area("Observações", key="pg_obs")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    if recibo and litros > 0:
                        rec_b64 = base64.b64encode(recibo.read()).decode() \
                                  if recibo.type=="application/pdf" \
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
                        updated = pd.concat([req_mat_db, novo], ignore_index=True) \
                                  if not req_mat_db.empty else novo
                        save_db(updated, "req_materiais.csv")
                        criar_notificacao(destinatario="admin",
                            titulo="⛽ Gasóleo",
                            mensagem=f"{user_nome}: {litros}L (€{valor})",
                            tipo="info", acao_url="/admin?tab=validacoes")
                        inv(); st.success("✅ Registo enviado!"); st.rerun()
                    else:
                        st.warning("⚠️ Faz upload do recibo e indica os litros.")

        with sub_avar:
            with st.form("form_avar"):
                obra_av  = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="pa_obra")
                equip_av = st.text_input("Equipamento / Viatura",
                    key="pa_equip", placeholder="Ex: Viatura ABC-123")
                desc_av  = st.text_area("Descrição da Avaria", key="pa_desc")
                col_u2, col_v2 = st.columns(2)
                with col_u2: urg_av = st.selectbox("Urgência",
                    ["Baixa","Média","Alta","Crítica - Paragem"], key="pa_urg")
                with col_v2: val_av = st.number_input("Valor Est. €",
                    min_value=0.0, key="pa_val")
                fat_av = st.file_uploader("📄 Fatura/Orçamento (obrigatório)",
                    type=["png","jpg","jpeg","pdf"], key="pa_fat")
                if st.form_submit_button("📤 Enviar",
                    use_container_width=True, type="primary"):
                    if fat_av and desc_av:
                        fat_b64 = base64.b64encode(fat_av.read()).decode() \
                                  if fat_av.type=="application/pdf" \
                                  else process_and_compress_image(fat_av)
                        novo = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante": user_nome, "Obra": obra_av,
                            "Equipamento": equip_av, "Descricao": desc_av,
                            "Urgencia": urg_av, "Valor_Estimado": val_av,
                            "Fatura_b64": fat_b64,
                            "Status": "Pendente", "Tipo": "Avaria"
                        }])
                        updated = pd.concat([incs_db, novo], ignore_index=True) \
                                  if not incs_db.empty else novo
                        save_db(updated, "incidentes.csv")
                        criar_notificacao(destinatario="admin",
                            titulo="🔧 Avaria Reportada",
                            mensagem=f"{urg_av}: {equip_av}",
                            tipo="error" if urg_av=="Crítica - Paragem" else "warning",
                            acao_url="/admin?tab=validacoes")
                        inv(); st.success("✅ Reporte enviado!"); st.rerun()
                    else:
                        st.warning("⚠️ Descreve e faz upload da fatura/orçamento.")

        with sub_meus:
            st.markdown("#### 📋 Os Meus Pedidos Recentes")
            sem = True
            for db, tipo_p, campo_d in [
                (req_fer_db,"🔧","Descricao"),
                (req_epi_db,"🦺","Item"),
                (req_mat_db,"📦","Descricao"),
            ]:
                if not db.empty and 'Solicitante' in db.columns:
                    meus = db[db['Solicitante']==user_nome]
                    if not meus.empty:
                        sem = False
                        for _, p in meus.tail(4).iterrows():
                            cor = {"Pendente":"#F59E0B","Aprovado":"#10B981",
                                   "Rejeitado":"#EF4444"}.get(
                                       p.get('Status','Pendente'),"#6B7280")
                            st.markdown(f"""
                            <div style="background:#FFFFFF;padding:12px;border-radius:10px;
                                margin-bottom:8px;border-left:4px solid {cor};
                                box-shadow:0 1px 3px rgba(0,0,0,0.06);">
                                <span style="color:#111827;">
                                    {tipo_p} {str(p.get(campo_d,'N/A'))[:40]}
                                </span>
                                <span style="color:{cor};font-size:0.8rem;
                                    float:right;font-weight:600;">
                                    {p.get('Status','Pendente')}
                                </span><br>
                                <small style="color:#9CA3AF;">
                                    {p.get('Data','')}
                                </small>
                            </div>""", unsafe_allow_html=True)
            if sem:
                st.info("📋 Ainda não fizeste nenhum pedido.")

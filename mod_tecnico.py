import streamlit as st
import streamlit.components.v1 as components
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

# ── Mapeamento de status → dot color ────────────────────────────────
_DOT_COLOR = {
    "0":  "#F97316",   # Laranja  — pendente
    "1":  "#10B981",   # Verde    — validado
    "2":  "#3B82F6",   # Azul     — faturação
    "3":  "#6B7280",   # Cinzento — faturado
    "4":  "#6B7280",   # Cinzento — pago
    "-1": "#EF4444",   # Vermelho — rejeitado
}
_DOT_LABEL = {
    "0":  "Pendente",
    "1":  "Validado",
    "2":  "Faturação",
    "3":  "Pago",
    "4":  "Pago",
    "-1": "Rejeitado",
}
_DIAS_PT    = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']
_MESES_PT   = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
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

def _render_calendario(registos_db, user_nome, semana_offset, data_consulta):
    """
    Renderiza o calendário semanal como HTML puro com dots de status.
    Devolve a data clicada (ou None se não houve clique).
    """
    hoje       = date.today()
    data_ref   = hoje + timedelta(weeks=semana_offset)
    inicio_sem = data_ref - timedelta(days=(data_ref.weekday() + 1) % 7)  # começa Domingo
    dias       = [inicio_sem + timedelta(days=i) for i in range(7)]
    mes_label  = _MESES_PT[dias[3].month - 1]  # mês do meio da semana
    ano_label  = dias[3].year

    # Calcular dot por dia
    dots = {}
    if not registos_db.empty and 'Técnico' in registos_db.columns:
        ru = registos_db[registos_db['Técnico'] == user_nome].copy()
        if not ru.empty:
            ru['Data_d'] = pd.to_datetime(ru['Data'], dayfirst=True, errors='coerce').dt.date
            for d in dias:
                regs_d = ru[ru['Data_d'] == d]
                if not regs_d.empty:
                    # Prioridade: status mais alto (4>3>2>1>0>-1)
                    status_prio = {"4":6,"3":5,"2":4,"1":3,"0":2,"-1":1}
                    statuses    = regs_d['Status'].tolist()
                    melhor      = max(statuses, key=lambda s: status_prio.get(str(s), 0))
                    dots[d]     = str(melhor)

    # Montar HTML do calendário
    html_dias = ""
    for d in dias:
        eh_hoje      = d == hoje
        eh_sel       = d == data_consulta
        dia_semana   = _DIAS_PT[d.weekday() + 1 if d.weekday() < 6 else 0] if True else ""
        # weekday(): 0=Mon...6=Sun → queremos Dom=0,Seg=1...
        dia_idx      = (d.weekday() + 1) % 7
        dia_letra    = ['D','S','T','Q','Q','S','S'][dia_idx]
        dot_color    = _DOT_COLOR.get(dots.get(d, ''), '')
        dot_html     = f'<span style="display:block;width:6px;height:6px;border-radius:50%;background:{dot_color};margin:2px auto 0;"></span>' if dot_color else '<span style="display:block;height:8px;"></span>'

        # Estilos do número
        if eh_sel:
            num_bg   = "#DC2626"
            num_col  = "white"
            num_font = "800"
        elif eh_hoje:
            num_bg   = "rgba(220,38,38,0.15)"
            num_col  = "#DC2626"
            num_font = "700"
        else:
            num_bg   = "transparent"
            num_col  = "#E2E8F0"
            num_font = "500"

        fim_semana   = dia_idx in (0, 6)  # Domingo ou Sábado
        letra_col    = "#6B7280" if fim_semana else "#94A3B8"

        html_dias += f"""
        <div class="cal-day" onclick="selectDay('{d.isoformat()}')" data-date="{d.isoformat()}">
            <span class="cal-letra" style="color:{letra_col};">{dia_letra}</span>
            <span class="cal-num" style="background:{num_bg};color:{num_col};font-weight:{num_font};">{d.day}</span>
            {dot_html}
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #1E293B;
        padding: 0;
        overflow: hidden;
    }}
    .cal-header {{
        text-align: center;
        padding: 14px 16px 10px;
        background: #1E293B;
    }}
    .cal-header-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 14px;
    }}
    .cal-nav {{
        background: rgba(255,255,255,0.1);
        border: none;
        color: #E2E8F0;
        font-size: 1.4rem;
        width: 36px; height: 36px;
        border-radius: 50%;
        cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        transition: background 0.2s;
        -webkit-tap-highlight-color: transparent;
    }}
    .cal-nav:active {{ background: rgba(220,38,38,0.3); }}
    .cal-title {{ color: #F8FAFC; font-size: 1.05rem; font-weight: 700; }}
    .cal-mes   {{ color: #DC2626; }}
    .cal-grid  {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 2px;
        padding: 0 8px 12px;
    }}
    .cal-day {{
        display: flex;
        flex-direction: column;
        align-items: center;
        cursor: pointer;
        padding: 4px 2px;
        border-radius: 10px;
        transition: background 0.15s;
        -webkit-tap-highlight-color: transparent;
        user-select: none;
    }}
    .cal-day:active {{ background: rgba(255,255,255,0.05); }}
    .cal-letra {{
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        margin-bottom: 4px;
        text-transform: uppercase;
    }}
    .cal-num {{
        width: 32px; height: 32px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.88rem;
        transition: all 0.2s;
    }}
    .legend {{
        display: flex;
        justify-content: center;
        gap: 12px;
        padding: 6px 16px 10px;
        flex-wrap: wrap;
    }}
    .legend-item {{
        display: flex; align-items: center; gap: 4px;
        font-size: 0.65rem; color: #94A3B8;
    }}
    .legend-dot {{
        width: 7px; height: 7px; border-radius: 50%;
    }}
    </style>
    </head>
    <body>
    <div class="cal-header">
        <div class="cal-header-top">
            <button class="cal-nav" onclick="navigate(-1)">‹</button>
            <span class="cal-title">
                Pontos &nbsp;·&nbsp;
                <span class="cal-mes">{mes_label} {ano_label}</span>
            </span>
            <button class="cal-nav" onclick="navigate(1)">›</button>
        </div>
        <div class="cal-grid">{html_dias}</div>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-dot" style="background:#F97316;"></div>Pendente
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#10B981;"></div>Validado
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#3B82F6;"></div>Faturação
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#6B7280;"></div>Pago
            </div>
        </div>
    </div>

    <script>
    function navigate(dir) {{
        const offset = {semana_offset} + dir;
        window.parent.postMessage({{type: 'cal_nav', offset: offset}}, '*');
    }}
    function selectDay(dateStr) {{
        window.parent.postMessage({{type: 'cal_select', date: dateStr}}, '*');
    }}
    </script>
    </body>
    </html>
    """
    return html, dias

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
        user_data   = user_match.iloc[0]  if not user_match.empty else None
        user_idx    = user_match.index[0] if not user_match.empty else None
    except:
        user_data = None
        user_idx  = None

    # ── Session state init ────────────────────────────────────────────
    for k, v in [
        ('data_consulta',     date.today()),
        ('semana_offset',     0),
        ('show_reg_form',     False),
        ('periodos_trabalho', [{"entrada":"08:00","saida":"17:00"}]),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    hoje = date.today()

    # ── CSS global escuro ─────────────────────────────────────────────
    st.markdown("""
    <style>
    /* Fundo app */
    .stApp { background: #0F172A !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #1E293B !important;
        border-bottom: 2px solid #334155 !important;
        gap: 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #64748B !important;
        font-size: 0.78rem !important;
        padding: 10px 8px !important;
        border-radius: 0 !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #DC2626 !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #DC2626 !important;
    }

    /* Inputs */
    .stTextInput label, .stSelectbox label, .stNumberInput label,
    .stTextArea label, .stRadio label, .stCheckbox label {
        color: #CBD5E1 !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
    }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #1E293B !important;
        color: #F1F5F9 !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }
    .stSelectbox > div > div > div {
        background: #1E293B !important;
        color: #F1F5F9 !important;
        border: 1px solid #334155 !important;
    }

    /* Botões */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        transition: all 0.2s !important;
    }
    .stButton > button[kind="primary"] {
        background: #DC2626 !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button[kind="secondary"] {
        background: #1E293B !important;
        color: #CBD5E1 !important;
        border: 1px solid #334155 !important;
    }

    /* Headings */
    h1,h2,h3,h4,h5,h6 { color: #F1F5F9 !important; }
    p, div, span       { color: #CBD5E1; }

    /* Expander */
    .streamlit-expanderHeader {
        background: #1E293B !important;
        color: #F1F5F9 !important;
        border-radius: 10px !important;
    }

    /* Métricas */
    [data-testid="stMetric"] {
        background: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
    }
    [data-testid="stMetricValue"] { color: #DC2626 !important; }
    [data-testid="stMetricLabel"] { color: #94A3B8 !important; }

    /* Dataframe */
    .stDataFrame { background: #1E293B !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E293B,#0F172A);
        border-radius:16px;padding:20px;margin-bottom:20px;
        border:1px solid #334155;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <p style="color:#94A3B8;font-size:0.8rem;margin:0;">Área Técnica</p>
                <p style="color:#F1F5F9;font-size:1.4rem;font-weight:800;margin:2px 0;">
                    {user_nome}
                </p>
                <p style="color:#64748B;font-size:0.82rem;margin:0;">
                    {cargo_user} · {user_tipo}
                </p>
            </div>
            <div style="width:48px;height:48px;border-radius:50%;
                background:linear-gradient(135deg,#DC2626,#991B1B);
                display:flex;align-items:center;justify-content:center;
                font-size:1.4rem;">
                👷
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────
    menu = ["📋 Pontos", "🛡️ HSE", "👤 Perfil", "📦 Pedidos"]
    if is_chefe:
        menu.insert(1, "📊 Folha Ponto")

    tabs = st.tabs(menu)

    # ════════════════════════════════════════════════════════════════
    # TAB 0 — PONTOS (CALENDÁRIO + REGISTO)
    # ════════════════════════════════════════════════════════════════
    with tabs[0]:

        if not st.session_state.show_reg_form:

            # ── Calendário HTML ───────────────────────────────────────
            cal_html, dias_semana = _render_calendario(
                registos_db,
                user_nome,
                st.session_state.semana_offset,
                st.session_state.data_consulta
            )

            # Renderizar o calendário HTML
            components.html(cal_html, height=200, scrolling=False)

            # Navegação real via botões Streamlit (os botões HTML enviam mensagens
            # que não chegam ao Python — usamos botões Streamlit abaixo do calendário)
            col_nav1, col_nav2, col_nav3, *col_dias_nav = st.columns(
                [1, 2, 1] + [1]*7
            )

            # Botões de navegação de semana
            with col_nav1:
                if st.button("‹", key="nav_prev", use_container_width=True,
                              help="Semana anterior"):
                    st.session_state.semana_offset -= 1
                    # Ajustar data_consulta para a mesma posição da semana
                    hoje_ref   = date.today() + timedelta(weeks=st.session_state.semana_offset)
                    ini        = hoje_ref - timedelta(days=(hoje_ref.weekday() + 1) % 7)
                    wd_old     = (st.session_state.data_consulta.weekday() + 1) % 7
                    st.session_state.data_consulta = ini + timedelta(days=wd_old)
                    st.rerun()
            with col_nav3:
                if st.button("›", key="nav_next", use_container_width=True,
                              help="Próxima semana"):
                    st.session_state.semana_offset += 1
                    hoje_ref   = date.today() + timedelta(weeks=st.session_state.semana_offset)
                    ini        = hoje_ref - timedelta(days=(hoje_ref.weekday() + 1) % 7)
                    wd_old     = (st.session_state.data_consulta.weekday() + 1) % 7
                    st.session_state.data_consulta = ini + timedelta(days=wd_old)
                    st.rerun()
            with col_nav2:
                if st.button("Hoje", key="nav_hoje", use_container_width=True):
                    st.session_state.semana_offset = 0
                    st.session_state.data_consulta = date.today()
                    st.rerun()

            # Botões dos dias (invisíveis mas funcionais — o visual vem do HTML acima)
            st.markdown("""
            <style>
            /* Botões dos dias — compactos e circulares */
            div[data-testid="stHorizontalBlock"] > div:nth-child(n+4)
                .stButton > button {
                border-radius: 50% !important;
                padding: 0 !important;
                height: 36px !important;
                min-height: 36px !important;
                font-size: 0.8rem !important;
                font-weight: 600 !important;
                background: transparent !important;
                border: none !important;
                color: transparent !important;
            }
            </style>
            """, unsafe_allow_html=True)

            # Botões transparentes por cima de cada dia
            for i, d in enumerate(dias_semana):
                with col_dias_nav[i]:
                    if st.button(
                        str(d.day),
                        key=f"d_{d.strftime('%Y%m%d')}",
                        use_container_width=True
                    ):
                        st.session_state.data_consulta = d
                        st.rerun()

            # ── Linha separadora com data selecionada ─────────────────
            data_sel    = st.session_state.data_consulta
            dia_semana  = _DIAS_PT[(data_sel.weekday() + 1) % 7]
            mes_str     = _MESES_PT[data_sel.month - 1]
            eh_hoje_sel = data_sel == hoje

            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                padding:14px 0 10px;border-top:1px solid #1E293B;margin-top:8px;">
                <span style="color:#F1F5F9;font-weight:700;font-size:0.95rem;">
                    {'📍 ' if eh_hoje_sel else ''}{dia_semana}, {data_sel.day} de {mes_str}
                </span>
                <button onclick="void(0)"
                    style="background:#DC2626;border:none;color:white;
                        border-radius:50%;width:38px;height:38px;
                        font-size:1.4rem;cursor:pointer;
                        display:flex;align-items:center;justify-content:center;
                        box-shadow:0 4px 12px rgba(220,38,38,0.4);">
                </button>
            </div>
            """, unsafe_allow_html=True)

            # Mostrar registos do dia
            regs_dia = pd.DataFrame()
            if not registos_db.empty and 'Técnico' in registos_db.columns:
                meus = registos_db[registos_db['Técnico'] == user_nome].copy()
                if not meus.empty:
                    dp        = pd.to_datetime(meus['Data'], dayfirst=True, errors='coerce').dt.date
                    regs_dia  = meus[dp == data_sel].copy()

            if not regs_dia.empty:
                regs_dia['_h'] = pd.to_numeric(regs_dia['Horas_Total'], errors='coerce').fillna(0)
                total_dia      = regs_dia['_h'].sum()

                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;
                    align-items:center;margin-bottom:12px;">
                    <span style="color:#94A3B8;font-size:0.82rem;">
                        {len(regs_dia)} registo(s)
                    </span>
                    <span style="background:rgba(220,38,38,0.15);color:#DC2626;
                        padding:4px 14px;border-radius:20px;
                        font-weight:800;font-size:0.9rem;">
                        {fh(total_dia)}
                    </span>
                </div>
                """, unsafe_allow_html=True)

                for _, r in regs_dia.iterrows():
                    status_s   = str(r.get('Status','0'))
                    dot_color  = _DOT_COLOR.get(status_s,  '#6B7280')
                    dot_label  = _DOT_LABEL.get(status_s,  'N/A')
                    horas_f    = fh(r.get('Horas_Total', 0))
                    turnos     = r.get('Turnos', '')
                    relat      = str(r.get('Relatorio', ''))[:55]

                    st.markdown(f"""
                    <div style="background:#1E293B;border-radius:12px;
                        padding:14px 16px;margin-bottom:8px;
                        border-left:4px solid {dot_color};
                        box-shadow:0 2px 8px rgba(0,0,0,0.2);">
                        <div style="display:flex;justify-content:space-between;
                            align-items:flex-start;">
                            <div style="flex:1;">
                                <p style="margin:0;font-weight:700;
                                    color:#F1F5F9;font-size:0.92rem;">
                                    {r.get('Obra','')}
                                </p>
                                <p style="margin:3px 0 0;color:#64748B;font-size:0.8rem;">
                                    {r.get('Frente','')}
                                    {f' · <span style="color:#94A3B8;">{turnos}</span>' if turnos else ''}
                                </p>
                                {f'<p style="margin:4px 0 0;color:#475569;font-size:0.75rem;">{relat}</p>' if relat else ''}
                            </div>
                            <div style="text-align:right;margin-left:12px;">
                                <p style="margin:0;font-weight:900;
                                    color:#F1F5F9;font-size:1.1rem;">
                                    {horas_f}
                                </p>
                                <span style="background:{dot_color}22;color:{dot_color};
                                    padding:2px 8px;border-radius:10px;
                                    font-size:0.7rem;font-weight:700;">
                                    {dot_label}
                                </span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            else:
                st.markdown("""
                <div style="background:#1E293B;border-radius:16px;padding:48px 20px;
                    text-align:center;border:1px dashed #334155;margin-top:8px;">
                    <div style="font-size:3rem;margin-bottom:12px;opacity:0.4;">📋</div>
                    <p style="color:#475569;font-weight:600;margin:0;font-size:0.9rem;">
                        Sem ponto registado neste dia
                    </p>
                </div>
                """, unsafe_allow_html=True)

            # ── FAB "+" ───────────────────────────────────────────────
            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
            col_esp, col_fab = st.columns([3, 1])
            with col_fab:
                if st.button("＋  Registar", key="fab_add",
                              type="primary", use_container_width=True):
                    st.session_state.show_reg_form    = True
                    st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"17:00"}]
                    st.rerun()

        # ────────────────────────────────────────────────────────────
        # FORMULÁRIO DE REGISTO — numa página só
        # ────────────────────────────────────────────────────────────
        else:
            data_sel = st.session_state.data_consulta
            mes_str  = _MESES_PT[data_sel.month - 1]

            # Header do formulário
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1E293B,#0F172A);
                border-radius:14px;padding:16px;margin-bottom:16px;
                border:1px solid #334155;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <p style="color:#94A3B8;font-size:0.75rem;margin:0;">
                            Registo de ponto
                        </p>
                        <p style="color:#F1F5F9;font-size:1rem;font-weight:700;margin:2px 0;">
                            {user_nome}
                        </p>
                        <p style="color:#64748B;font-size:0.8rem;margin:0;">{cargo_user}</p>
                    </div>
                    <div style="text-align:right;">
                        <p style="color:#DC2626;font-size:1.3rem;font-weight:900;margin:0;">
                            {data_sel.day:02d}/{data_sel.month:02d}/{data_sel.year}
                        </p>
                        <p style="color:#64748B;font-size:0.75rem;margin:2px 0 0;">
                            {_DIAS_PT[(data_sel.weekday()+1)%7]}
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.form("form_registo_ponto", clear_on_submit=False):

                # ── Seleção de Obra ───────────────────────────────
                st.markdown("""
                <p style="color:#94A3B8;font-size:0.7rem;font-weight:700;
                    letter-spacing:0.1em;text-transform:uppercase;margin:0 0 8px;">
                    🏗️ OBRA
                </p>""", unsafe_allow_html=True)

                obras_lista = []
                if not obras_db.empty:
                    ativas      = obras_db[obras_db['Ativa'] == 'Ativa']
                    obras_lista = ativas['Obra'].tolist() if not ativas.empty else obras_db['Obra'].tolist()

                obra_sel = st.selectbox(
                    "Selecionar obra",
                    obras_lista if obras_lista else ["Sem obras ativas"],
                    key="reg_obra",
                    label_visibility="collapsed"
                )

                # Mostrar código da obra se disponível
                if not obras_db.empty and obra_sel in obras_db['Obra'].values:
                    obra_info = obras_db[obras_db['Obra'] == obra_sel].iloc[0]
                    cod       = obra_info.get('Codigo', '')
                    cli       = obra_info.get('Cliente', '')
                    if cod or cli:
                        st.markdown(f"""
                        <div style="background:rgba(220,38,38,0.08);border-radius:8px;
                            padding:8px 12px;margin:-4px 0 10px;">
                            <span style="color:#DC2626;font-size:0.75rem;font-weight:700;">
                                {cod}
                            </span>
                            {f'<span style="color:#64748B;font-size:0.75rem;"> · {cli}</span>' if cli else ''}
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

                # ── Frente de Trabalho ────────────────────────────
                st.markdown("""
                <p style="color:#94A3B8;font-size:0.7rem;font-weight:700;
                    letter-spacing:0.1em;text-transform:uppercase;margin:0 0 8px;">
                    🔧 FRENTE DE TRABALHO
                </p>""", unsafe_allow_html=True)

                frente_sel = st.selectbox(
                    "Frente",
                    TIPOS_FRENTE,
                    key="reg_frente",
                    label_visibility="collapsed"
                )

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                st.markdown('<div style="height:1px;background:#1E293B;margin:8px 0;"></div>',
                            unsafe_allow_html=True)

                # ── Períodos de horas ─────────────────────────────
                st.markdown("""
                <p style="color:#94A3B8;font-size:0.7rem;font-weight:700;
                    letter-spacing:0.1em;text-transform:uppercase;margin:0 0 10px;">
                    ⏱️ HORAS
                </p>""", unsafe_allow_html=True)

                total_horas     = 0.0
                periodos_validos = []

                for idx, periodo in enumerate(st.session_state.periodos_trabalho):
                    if idx > 0:
                        st.markdown(
                            '<div style="height:1px;background:#1E293B;margin:6px 0;"></div>',
                            unsafe_allow_html=True
                        )

                    col_e, col_s = st.columns(2)
                    with col_e:
                        idx_e   = _HORAS_30.index(periodo["entrada"]) \
                                  if periodo["entrada"] in _HORAS_30 else 16
                        entrada = st.selectbox(
                            f"Entrada {'' if len(st.session_state.periodos_trabalho)==1 else idx+1}",
                            _HORAS_30, index=idx_e,
                            key=f"ent_{idx}"
                        )
                    with col_s:
                        idx_s   = _HORAS_30.index(periodo["saida"]) \
                                  if periodo["saida"] in _HORAS_30 else 34
                        saida   = st.selectbox(
                            f"Saída {'' if len(st.session_state.periodos_trabalho)==1 else idx+1}",
                            _HORAS_30, index=idx_s,
                            key=f"sai_{idx}"
                        )

                    t1     = datetime.strptime(entrada, "%H:%M")
                    t2     = datetime.strptime(saida,   "%H:%M")
                    delta  = (t2 - t1).seconds / 3600
                    if delta > 0:
                        total_horas += delta
                        periodos_validos.append({
                            "entrada": entrada,
                            "saida":   saida,
                            "horas":   round(delta, 2)
                        })
                        st.markdown(f"""
                        <p style="text-align:right;color:#DC2626;
                            font-weight:700;font-size:0.82rem;margin:2px 0 0;">
                            = {fh(delta)}
                        </p>""", unsafe_allow_html=True)
                    elif delta < 0:
                        st.markdown("""
                        <p style="text-align:right;color:#EF4444;
                            font-size:0.78rem;margin:2px 0 0;">
                            ⚠️ Saída antes da entrada
                        </p>""", unsafe_allow_html=True)

                # Total
                if total_horas > 0:
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#7F1D1D,#991B1B);
                        border-radius:12px;padding:14px;text-align:center;margin:12px 0;">
                        <p style="margin:0;color:rgba(255,255,255,0.7);font-size:0.75rem;">
                            TOTAL
                        </p>
                        <p style="margin:4px 0 0;color:#FFF;font-size:2rem;font-weight:900;">
                            {fh(total_horas)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                # Relatório
                relatorio = st.text_area(
                    "📝 Descrição do trabalho (opcional)",
                    placeholder="Ex: Montagem de instrumentos, calibração de válvulas...",
                    key="reg_relat", height=80
                )

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

                # Botões do formulário
                col_g, col_c, col_p = st.columns([3, 2, 2])
                with col_g:
                    guardar = st.form_submit_button(
                        "💾 Guardar", use_container_width=True, type="primary"
                    )
                with col_p:
                    st.form_submit_button(
                        "＋ Período", use_container_width=True
                    )

            # ── Cancelar (fora do form) ───────────────────────────
            if st.button("← Voltar", key="btn_voltar",
                          use_container_width=False):
                st.session_state.show_reg_form = False
                st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"17:00"}]
                st.rerun()

            # ── Adicionar período (fora do form) ──────────────────
            col_add, _ = st.columns([1, 2])
            with col_add:
                if st.button("➕ Adicionar período", key="add_per",
                              use_container_width=True):
                    st.session_state.periodos_trabalho.append(
                        {"entrada":"13:00","saida":"17:00"}
                    )
                    st.rerun()

            # ── Processar guardar ─────────────────────────────────
            if guardar:
                if total_horas <= 0:
                    st.error("⚠️ As horas têm de ser superiores a 0.")
                elif not obra_sel or obra_sel == "Sem obras ativas":
                    st.error("⚠️ Seleciona uma obra.")
                else:
                    reg_ids = []
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
                        reg_ids.append(new_r['ID'].iloc[0])
                        log_audit(
                            usuario=user_nome,
                            acao="REGISTAR_PONTO",
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
                                 f"em {obra_sel} a {data_sel.strftime('%d/%m')}",
                        tipo="info",
                        acao_url="/admin?tab=validacoes"
                    )

                    # Limpar e voltar
                    st.session_state.show_reg_form     = False
                    st.session_state.periodos_trabalho = [{"entrada":"08:00","saida":"17:00"}]
                    inv()

                    # Feedback de sucesso
                    st.success(f"✅ Ponto registado — {fh(total_horas)} em {obra_sel}")
                    time.sleep(1.2)
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB FOLHA DE PONTO (só chefe)
    # ════════════════════════════════════════════════════════════════
    offset = 0
    if is_chefe:
        offset = 1
        with tabs[1]:
            st.markdown("### 📊 Folha de Ponto & Assinatura")

            obra_f = st.selectbox("Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Sem obras"],
                key="fp_obra")

            col_fi, col_ff = st.columns(2)
            with col_fi:
                sem_ini = st.date_input("Início",
                    value=hoje - timedelta(days=hoje.weekday()),
                    key="fp_ini")
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
                    st.markdown("#### 👥 Equipa")
                    for tec in regs_fp['Técnico'].unique():
                        regs_t = regs_fp[regs_fp['Técnico'] == tec]
                        total  = pd.to_numeric(
                            regs_t['Horas_Total'], errors='coerce'
                        ).fillna(0).sum()
                        validadas = pd.to_numeric(
                            regs_t[regs_t['Status']=='1']['Horas_Total'],
                            errors='coerce'
                        ).fillna(0).sum()
                        st.markdown(f"""
                        <div style="background:#1E293B;border-radius:10px;
                            padding:12px 16px;margin-bottom:8px;
                            border:1px solid #334155;">
                            <div style="display:flex;justify-content:space-between;">
                                <div>
                                    <p style="margin:0;color:#F1F5F9;font-weight:700;">
                                        👤 {tec}
                                    </p>
                                    <p style="margin:3px 0 0;color:#64748B;font-size:0.8rem;">
                                        {len(regs_t)} dia(s) ·
                                        <span style="color:#10B981;">
                                            {fh(validadas)} validadas
                                        </span>
                                    </p>
                                </div>
                                <span style="color:#DC2626;font-weight:900;font-size:1.1rem;">
                                    {fh(total)}
                                </span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("#### ✍️ Assinatura Digital")
                    canvas_sig = None
                    try:
                        canvas_sig = st_canvas(
                            fill_color="rgba(255,255,255,0)",
                            stroke_width=2.5,
                            stroke_color="#DC2626",
                            background_color="#1E293B",
                            height=150, width=320,
                            drawing_mode="freedraw",
                            key="canvas_fp"
                        )
                    except:
                        st.info("ℹ️ Canvas não disponível.")

                    nome_resp = st.text_input("Nome do Responsável", key="fp_resp")
                    if st.button("🔒 Gerar Folha com Selo",
                                  use_container_width=True, type="primary"):
                        if nome_resp:
                            selo      = secrets.token_hex(6).upper()
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            sig_b64   = ""
                            if canvas_sig and canvas_sig.image_data is not None:
                                sig_b64 = canvas_to_b64(canvas_sig.image_data) or ""
                            nova_f = pd.DataFrame([{
                                "ID":             str(uuid.uuid4())[:8].upper(),
                                "Obra":           obra_f,
                                "Periodo":        f"{sem_ini.strftime('%d/%m')}-{sem_fim.strftime('%d/%m/%Y')}",
                                "Responsavel":    nome_resp,
                                "Data_Assinatura":timestamp,
                                "Assinatura_b64": sig_b64,
                                "Selo":           selo,
                                "Status":         "Assinado"
                            }])
                            updated = pd.concat([folhas_db, nova_f], ignore_index=True) \
                                      if not folhas_db.empty else nova_f
                            save_db(updated, "folhas_ponto.csv")
                            st.markdown(f"""
                            <div style="border:2px dashed #10B981;padding:14px;
                                background:rgba(16,185,129,0.08);border-radius:10px;
                                font-family:monospace;color:#10B981;margin-top:12px;">
                                🔒 SELO #{selo} · {timestamp}<br>
                                Assinado por: {nome_resp} · {obra_f}
                            </div>
                            """, unsafe_allow_html=True)
                            inv()
                            st.success("✅ Folha gerada!")
                        else:
                            st.warning("⚠️ Indica o nome do responsável.")
                else:
                    st.info("📋 Sem registos para este período.")

    # ════════════════════════════════════════════════════════════════
    # TAB HSE
    # ════════════════════════════════════════════════════════════════
    with tabs[1 + offset]:
        st.markdown("### 🛡️ Segurança HSE")

        for ic, tit, des in REGRAS_OURO:
            with st.expander(f"{ic} {tit}"):
                st.write(des)

        st.divider()
        st.markdown("### 🚨 Reportar Incidente")

        with st.form("form_hse"):
            obra_hse = st.selectbox("Obra",
                obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                key="hse_obra")
            grav_hse = st.selectbox("Gravidade",
                ["Baixa","Média","Alta (Crítica)"], key="hse_grav")
            desc_hse = st.text_area("Descrição", key="hse_desc")

            if st.form_submit_button("📤 Submeter Alerta",
                use_container_width=True, type="primary"):
                if desc_hse:
                    ni = pd.DataFrame([{
                        "ID":         str(uuid.uuid4())[:8].upper(),
                        "Data":       hoje.strftime("%d/%m/%Y"),
                        "Utilizador": user_nome,
                        "Obra":       obra_hse,
                        "Status":     "Aberto",
                        "Gravidade":  grav_hse,
                        "Descricao":  desc_hse,
                        "Tipo":       "HSE"
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
        st.markdown("### 👤 Perfil")

        if user_data is not None:
            # Estado das validações
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                pv   = user_data.get('PDFs_Validados', 'Não')
                pvd  = user_data.get('PDFs_Validacao_Data','')
                c_p  = "#10B981" if pv=='Sim' else "#EF4444"
                st.markdown(f"""
                <div style="background:#1E293B;border:2px solid {c_p};
                    border-radius:10px;padding:12px;text-align:center;">
                    <b style="color:{c_p};">{'✅' if pv=='Sim' else '❌'} Documentos</b>
                    <p style="color:#64748B;font-size:0.75rem;margin:5px 0 0;">
                        {('Em ' + pvd) if pv=='Sim' else 'Pendentes'}
                    </p>
                </div>""", unsafe_allow_html=True)
            with col_v2:
                ps   = user_data.get('PrecoHoraStatus','')
                pv_  = user_data.get('PrecoHora','15.0')
                pd_  = user_data.get('PrecoHoraData','')
                c_pr = "#10B981" if ps=='Aceite' else "#EF4444" if ps=='Recusado' else "#F59E0B"
                ic_  = "✅" if ps=='Aceite' else "❌" if ps=='Recusado' else "⏳"
                st.markdown(f"""
                <div style="background:#1E293B;border:2px solid {c_pr};
                    border-radius:10px;padding:12px;text-align:center;">
                    <b style="color:{c_pr};">{ic_} €{pv_}/h</b>
                    <p style="color:#64748B;font-size:0.75rem;margin:5px 0 0;">
                        {('Aceite em ' + pd_) if ps=='Aceite' else ps if ps else 'Pendente'}
                    </p>
                </div>""", unsafe_allow_html=True)

            st.divider()
            try:
                cb = json.loads(user_data.get('Campos_Bloqueados','[]'))
            except:
                cb = []

            with st.form("form_perfil"):
                c1, c2 = st.columns(2)
                with c1:
                    tel    = st.text_input("Telefone",
                        value=user_data.get('Telefone',''),
                        disabled='Telefone' in cb, key="p_tel")
                    email_ = st.text_input("Email",
                        value=user_data.get('Email',''),
                        disabled='Email' in cb, key="p_email")
                    ce     = st.text_input("Tel. Emergência",
                        value=user_data.get('Contacto_Emergencia',''),
                        disabled='Contacto_Emergencia' in cb, key="p_ce")
                with c2:
                    ne     = st.text_input("Nome Emergência",
                        value=user_data.get('Nome_Emergencia',''),
                        disabled='Nome_Emergencia' in cb, key="p_ne")
                    gp     = st.text_input("Grau Parentesco",
                        value=user_data.get('Grau_Parentesco',''),
                        disabled='Grau_Parentesco' in cb, key="p_gp")

                mor    = st.text_input("Morada",
                    value=user_data.get('Morada',''),
                    disabled='Morada' in cb, key="p_mor")

                c3, c4, c5 = st.columns(3)
                with c3:
                    loc = st.text_input("Localidade",
                        value=user_data.get('Localidade',''),
                        disabled='Localidade' in cb, key="p_loc")
                with c4:
                    con = st.text_input("Concelho",
                        value=user_data.get('Concelho',''),
                        disabled='Concelho' in cb, key="p_con")
                with c5:
                    cp_ = st.text_input("Cód. Postal",
                        value=user_data.get('Codigo_Postal',''),
                        disabled='Codigo_Postal' in cb, key="p_cp")

                st.markdown("**🔐 Alterar Password**")
                cp1, cp2 = st.columns(2)
                with cp1:
                    pa = st.text_input("Atual", type="password", key="p_pa")
                with cp2:
                    pn = st.text_input("Nova",  type="password", key="p_pn")

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
                                'Telefone': tel.strip(),
                                'Email': email_.strip(),
                                'Morada': mor.strip(),
                                'Localidade': loc.strip(),
                                'Concelho': con.strip(),
                                'Codigo_Postal': cp_.strip(),
                                'Contacto_Emergencia': ce.strip(),
                                'Nome_Emergencia': ne.strip(),
                                'Grau_Parentesco': gp.strip(),
                            }.items():
                                if campo not in cb:
                                    ul.loc[m, campo] = val

                            if pn.strip() and pa.strip():
                                from core import cp as chk
                                ph = str(ul.loc[m,'Password'].values[0])
                                if chk(pa.strip(), ph):
                                    if len(pn.strip()) >= 4:
                                        ul.loc[m,'Password'] = hp(pn.strip())
                                        st.success("🔐 Password atualizada!")
                                    else:
                                        st.error("❌ Mínimo 4 caracteres.")
                                else:
                                    st.error("❌ Password atual incorreta.")

                            if pin_.strip():
                                if len(pin_.strip())==4 and pin_.strip().isdigit():
                                    ul.loc[m,'PIN'] = pin_.strip()
                                else:
                                    st.error("❌ PIN deve ter 4 dígitos numéricos.")

                            save_db(ul, "usuarios.csv")
                            log_audit(usuario=user_nome, acao="EDITAR_PERFIL",
                                tabela="usuarios.csv", registro_id=user_nome,
                                detalhes="Perfil atualizado", ip="")
                            inv()
                            st.success("✅ Perfil atualizado!")
                            st.rerun()
        else:
            st.warning("⚠️ Não foi possível carregar os dados.")

    # ════════════════════════════════════════════════════════════════
    # TAB PEDIDOS
    # ════════════════════════════════════════════════════════════════
    with tabs[-1]:
        st.markdown("### 📦 Pedidos & Reportes")

        s1,s2,s3,s4,s5,s6 = st.tabs([
            "🔧 Ferramentas","🦺 EPIs","📦 Materiais",
            "⛽ Gasóleo","🔧 Avarias","📋 Os Meus"
        ])

        def _quick_notify(titulo, msg):
            criar_notificacao(destinatario="admin", titulo=titulo,
                mensagem=msg, tipo="warning", acao_url="/admin?tab=validacoes")

        with s1:
            with st.form("ff"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="ff_o")
                d_ = st.text_area("Descrição", key="ff_d")
                u_ = st.selectbox("Urgência", ["Baixa","Média","Alta"], key="ff_u")
                f_ = st.file_uploader("Foto opcional",
                    type=["png","jpg","jpeg"], key="ff_f")
                if st.form_submit_button("📤 Enviar", use_container_width=True,
                    type="primary"):
                    if d_:
                        fb = process_and_compress_image(f_) if f_ else None
                        novo = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                            "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante":user_nome,"Obra":o_,
                            "Descricao":d_,"Urgencia":u_,
                            "Foto_b64":fb,"Status":"Pendente"}])
                        upd = pd.concat([req_fer_db,novo],ignore_index=True) \
                              if not req_fer_db.empty else novo
                        save_db(upd,"req_ferramentas.csv")
                        _quick_notify("🔧 Ferramenta",f"{user_nome}: {d_[:40]}")
                        inv(); st.success("✅ Enviado!"); st.rerun()
                    else: st.warning("⚠️ Descreve a ferramenta.")

        with s2:
            with st.form("fe"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="fe_o")
                i_ = st.selectbox("EPI",["Capacete","Óculos","Luvas","Botas",
                    "Arnés","Protetor Auditivo","Máscara","Outro"], key="fe_i")
                c1_,c2_ = st.columns(2)
                with c1_: t_ = st.selectbox("Tamanho",
                    ["P","M","G","XG","Único"], key="fe_t")
                with c2_: q_ = st.number_input("Qtd",min_value=1,value=1, key="fe_q")
                if st.form_submit_button("📤 Enviar", use_container_width=True,
                    type="primary"):
                    novo = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                        "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante":user_nome,"Obra":o_,
                        "Item":i_,"Tamanho":t_,"Quantidade":q_,"Status":"Pendente"}])
                    upd = pd.concat([req_epi_db,novo],ignore_index=True) \
                          if not req_epi_db.empty else novo
                    save_db(upd,"req_epis.csv")
                    _quick_notify("🦺 EPI",f"{user_nome}: {q_}x {i_}")
                    inv(); st.success("✅ Enviado!"); st.rerun()

        with s3:
            with st.form("fm"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="fm_o")
                d_ = st.text_area("Descrição", key="fm_d")
                c1_,c2_ = st.columns(2)
                with c1_: q_ = st.number_input("Qtd",min_value=1,value=1,key="fm_q")
                with c2_: u_ = st.selectbox("Unidade",
                    ["un","m","kg","l","cx"],key="fm_u")
                ug_ = st.selectbox("Urgência",["Baixa","Média","Alta"],key="fm_ug")
                if st.form_submit_button("📤 Enviar",use_container_width=True,
                    type="primary"):
                    if d_:
                        novo = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                            "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante":user_nome,"Obra":o_,
                            "Descricao":d_,"Quantidade":q_,
                            "Unidade":u_,"Urgencia":ug_,"Status":"Pendente"}])
                        upd = pd.concat([req_mat_db,novo],ignore_index=True) \
                              if not req_mat_db.empty else novo
                        save_db(upd,"req_materiais.csv")
                        _quick_notify("📦 Material",f"{user_nome}: {q_}{u_} de {d_[:30]}")
                        inv(); st.success("✅ Enviado!"); st.rerun()
                    else: st.warning("⚠️ Descreve o material.")

        with s4:
            with st.form("fg"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="fg_o")
                c1_,c2_ = st.columns(2)
                with c1_: l_ = st.number_input("Litros",min_value=0.0,step=0.5,key="fg_l")
                with c2_: v_ = st.number_input("Valor €",min_value=0.0,step=0.01,key="fg_v")
                dg_ = st.date_input("Data",value=hoje,key="fg_d")
                rg_ = st.file_uploader("📄 Recibo (obrigatório)",
                    type=["png","jpg","jpeg","pdf"],key="fg_r")
                og_ = st.text_area("Observações",key="fg_obs")
                if st.form_submit_button("📤 Enviar",use_container_width=True,
                    type="primary"):
                    if rg_ and l_>0:
                        rb = base64.b64encode(rg_.read()).decode() \
                             if rg_.type=="application/pdf" \
                             else process_and_compress_image(rg_)
                        novo = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                            "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante":user_nome,"Obra":o_,
                            "Litros":l_,"Valor":v_,
                            "Data_Abastecimento":dg_.strftime("%d/%m/%Y"),
                            "Descricao":og_,"Recibo_b64":rb,
                            "Status":"Pendente","Tipo":"Gasóleo"}])
                        upd = pd.concat([req_mat_db,novo],ignore_index=True) \
                              if not req_mat_db.empty else novo
                        save_db(upd,"req_materiais.csv")
                        _quick_notify("⛽ Gasóleo",f"{user_nome}: {l_}L (€{v_})")
                        inv(); st.success("✅ Enviado!"); st.rerun()
                    else: st.warning("⚠️ Faz upload do recibo e indica os litros.")

        with s5:
            with st.form("fa"):
                o_ = st.selectbox("Obra",
                    obras_db['Obra'].unique() if not obras_db.empty else ["Geral"],
                    key="fa_o")
                eq_ = st.text_input("Equipamento/Viatura",
                    key="fa_eq",placeholder="Ex: Viatura ABC-123")
                d_  = st.text_area("Descrição da avaria",key="fa_d")
                c1_,c2_ = st.columns(2)
                with c1_: u_ = st.selectbox("Urgência",
                    ["Baixa","Média","Alta","Crítica - Paragem"],key="fa_u")
                with c2_: v_ = st.number_input("Valor Est. €",
                    min_value=0.0,key="fa_v")
                ft_ = st.file_uploader("📄 Fatura/Orçamento (obrigatório)",
                    type=["png","jpg","jpeg","pdf"],key="fa_f")
                if st.form_submit_button("📤 Enviar",use_container_width=True,
                    type="primary"):
                    if ft_ and d_:
                        fb = base64.b64encode(ft_.read()).decode() \
                             if ft_.type=="application/pdf" \
                             else process_and_compress_image(ft_)
                        novo = pd.DataFrame([{"ID":str(uuid.uuid4())[:8].upper(),
                            "Data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Solicitante":user_nome,"Obra":o_,
                            "Equipamento":eq_,"Descricao":d_,
                            "Urgencia":u_,"Valor_Estimado":v_,
                            "Fatura_b64":fb,"Status":"Pendente","Tipo":"Avaria"}])
                        upd = pd.concat([incs_db,novo],ignore_index=True) \
                              if not incs_db.empty else novo
                        save_db(upd,"incidentes.csv")
                        _quick_notify("🔧 Avaria",
                            f"{u_}: {eq_} em {o_}")
                        inv(); st.success("✅ Enviado!"); st.rerun()
                    else: st.warning("⚠️ Descreve e faz upload da fatura.")

        with s6:
            st.markdown("#### 📋 Os Meus Pedidos")
            sem_ped = True
            for db_,tipo_,campo_ in [
                (req_fer_db,"🔧","Descricao"),
                (req_epi_db,"🦺","Item"),
                (req_mat_db,"📦","Descricao"),
            ]:
                if not db_.empty and 'Solicitante' in db_.columns:
                    meus_ = db_[db_['Solicitante']==user_nome]
                    if not meus_.empty:
                        sem_ped = False
                        for _,p_ in meus_.tail(5).iterrows():
                            cor = {"Pendente":"#F97316","Aprovado":"#10B981",
                                   "Rejeitado":"#EF4444"}.get(
                                       p_.get('Status','Pendente'),"#6B7280")
                            st.markdown(f"""
                            <div style="background:#1E293B;padding:12px;border-radius:10px;
                                margin-bottom:6px;border-left:3px solid {cor};">
                                <span style="color:#F1F5F9;">
                                    {tipo_} {str(p_.get(campo_,''))[:42]}
                                </span>
                                <span style="color:{cor};font-size:0.78rem;
                                    float:right;font-weight:700;">
                                    {p_.get('Status','')}
                                </span><br>
                                <small style="color:#475569;">{p_.get('Data','')}</small>
                            </div>""", unsafe_allow_html=True)
            if sem_ped:
                st.info("📋 Ainda não fizeste nenhum pedido.")

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import fh, ICONS, load_db

_DOT_COLOR = {
    "0": "#F97316",
    "1": "#10B981",
    "2": "#3B82F6",
    "3": "#6B7280",
    "4": "#6B7280",
}
_DIAS_PT = ['D','S','T','Q','Q','S','S']

@st.fragment
def render_inicio(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db, *_) = args

    user_nome = st.session_state.get('user', 'Utilizador')
    user_tipo = st.session_state.get('tipo',  'Técnico')
    cargo     = st.session_state.get('cargo', 'Técnico')

    hoje       = date.today()
    inicio_mes = hoje.replace(day=1)
    sete_dias  = hoje - timedelta(days=6)
    hora       = datetime.now().hour
    saudacao   = "Bom dia" if hora < 12 else "Boa tarde" if hora < 19 else "Boa noite"

    # ── CSS ───────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .stApp { background: #0F172A !important; }
    .main .block-container { padding-top: 0.5rem !important; }
    h1,h2,h3,h4,h5,h6 { color: #F1F5F9 !important; }
    p, div, span { color: #CBD5E1; }
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        height: 46px !important;
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
    [data-testid="stMetric"] {
        background: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 12px !important;
    }
    [data-testid="stMetricValue"] { color: #DC2626 !important; font-weight: 900 !important; }
    [data-testid="stMetricLabel"] { color: #64748B !important; font-size: 0.75rem !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── Estatísticas ──────────────────────────────────────────────────
    horas_mes  = 0.0
    horas_pend = 0.0
    regs_7     = pd.DataFrame()
    dias_regs  = {}

    # Timestamps para comparação com datetime64
    ts_inicio_mes = pd.Timestamp(inicio_mes)
    ts_sete_dias  = pd.Timestamp(sete_dias)

    if not registos_db.empty and 'Técnico' in registos_db.columns:
        ru = registos_db[registos_db['Técnico'] == user_nome].copy()
        if not ru.empty:
            ru['Data_d']      = pd.to_datetime(ru['Data'], dayfirst=True, errors='coerce').dt.normalize()
            ru['Horas_Total'] = pd.to_numeric(ru['Horas_Total'], errors='coerce').fillna(0)
            horas_mes         = ru[
                (ru['Data_d'] >= ts_inicio_mes) & (ru['Status'] == '1')
            ]['Horas_Total'].sum()
            horas_pend        = ru[ru['Status'] == '0']['Horas_Total'].sum()
            regs_7            = ru[
                (ru['Data_d'] >= ts_sete_dias) & (ru['Status'] == '1')
            ].copy()
            sp = {"4":6,"3":5,"2":4,"1":3,"0":2,"-1":1}
            for d_u in ru['Data_d'].dropna().unique():
                rd     = ru[ru['Data_d'] == pd.Timestamp(d_u)]
                melhor = max(rd['Status'].tolist(), key=lambda s: sp.get(str(s), 0))
                # Guardar como date para o mini-calendário
                dias_regs[pd.Timestamp(d_u).date()] = str(melhor)

    # ── Header ────────────────────────────────────────────────────────
    st.markdown(
        f"<p style='color:#94A3B8;font-size:0.82rem;margin:0 0 0px;'>{saudacao}</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='color:#F1F5F9;font-size:1.8rem;font-weight:900;"
        f"margin:0 0 2px;line-height:1.1;'>{user_nome.split()[0]}</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='color:#64748B;font-size:0.78rem;margin:0 0 16px;'>"
        f"{cargo} &nbsp;·&nbsp; {user_tipo}</p>",
        unsafe_allow_html=True
    )

    # ── KPI Cards ─────────────────────────────────────────────────────
    col_h, col_p = st.columns(2)

    with col_h:
        st.markdown(
            f"<div style='background:rgba(220,38,38,0.12);"
            f"border:1px solid rgba(220,38,38,0.3);"
            f"border-radius:14px;padding:14px 12px;text-align:left;'>"
            f"<p style='color:#94A3B8;font-size:0.7rem;margin:0 0 4px;'>⏱️ Horas este mês</p>"
            f"<p style='color:#F1F5F9;font-size:1.5rem;font-weight:900;margin:0;'>"
            f"{fh(horas_mes)}</p></div>",
            unsafe_allow_html=True
        )

    with col_p:
        cor = "rgba(249,115,22,0.15)" if horas_pend > 0 else "rgba(16,185,129,0.1)"
        brd = "rgba(249,115,22,0.4)"  if horas_pend > 0 else "rgba(16,185,129,0.3)"
        st.markdown(
            f"<div style='background:{cor};border:1px solid {brd};"
            f"border-radius:14px;padding:14px 12px;text-align:left;'>"
            f"<p style='color:#94A3B8;font-size:0.7rem;margin:0 0 4px;'>📋 Por validar</p>"
            f"<p style='color:#F1F5F9;font-size:1.5rem;font-weight:900;margin:0;'>"
            f"{fh(horas_pend)}</p></div>",
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── KPIs secundários ──────────────────────────────────────────────
    n_obras = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
    n_pend  = 0
    for db_, c_ in [(req_fer_db,'Solicitante'),(req_epi_db,'Solicitante'),(req_mat_db,'Solicitante')]:
        if not db_.empty and c_ in db_.columns:
            n_pend += len(db_[(db_[c_] == user_nome) & (db_['Status'] == 'Pendente')])

    n_regs = 0
    if not registos_db.empty and 'Técnico' in registos_db.columns:
        ru2 = registos_db[registos_db['Técnico'] == user_nome]
        if not ru2.empty:
            dc2    = pd.to_datetime(ru2['Data'], dayfirst=True, errors='coerce').dt.normalize()
            n_regs = int((dc2 >= ts_inicio_mes).sum())

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("🏭 Obras",    n_obras)
    with c2: st.metric("📦 Pedidos",  n_pend)
    with c3: st.metric("📋 Registos", n_regs)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── Acesso Rápido ─────────────────────────────────────────────────
    st.markdown(
        "<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
        "letter-spacing:0.08em;text-transform:uppercase;margin:0 0 8px;'>"
        "Acesso Rápido</p>",
        unsafe_allow_html=True
    )

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("📋 Registar Ponto",
                     use_container_width=True, type="primary", key="btn_rp"):
            st.session_state['menu_selected'] = f"{ICONS['technician']} Obra"
            st.session_state['_menu_locked']  = True
            st.rerun()
    with col_r2:
        if st.button("👤 O Meu Perfil",
                     use_container_width=True, type="secondary", key="btn_mp"):
            st.session_state['menu_selected'] = f"{ICONS['profile']} Perfil"
            st.session_state['_menu_locked']  = True
            st.rerun()

    tem_inst = (user_tipo in ['Chefe de Equipa','Admin','Gestor'] or
                cargo in ['Chefe de Equipa','Encarregado','Instrumentista'])
    if tem_inst:
        if st.button("🧪 Instrumentação",
                     use_container_width=True, type="secondary", key="btn_inst"):
            st.session_state['menu_selected'] = f"{ICONS['instrumentation']} Instrumentação"
            st.session_state['_menu_locked']  = True
            st.rerun()

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    # ── Mini-calendário 7 dias ────────────────────────────────────────
    st.markdown(
        "<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
        "letter-spacing:0.08em;text-transform:uppercase;margin:0 0 8px;'>"
        "Últimos 7 dias</p>",
        unsafe_allow_html=True
    )

    dias_7   = [sete_dias + timedelta(days=i) for i in range(7)]
    cols_cal = st.columns(7)

    for col, d in zip(cols_cal, dias_7):
        with col:
            # dias_regs tem keys como date objects
            dot_cor = _DOT_COLOR.get(dias_regs.get(d, ''), '')
            eh_hoje = d == hoje
            num_col = "#DC2626" if eh_hoje else "#94A3B8"
            num_wt  = "900"     if eh_hoje else "400"
            dl      = _DIAS_PT[(d.weekday() + 1) % 7]
            dot_html = (
                f"<div style='width:7px;height:7px;border-radius:50%;"
                f"background:{dot_cor};margin:3px auto 0;'></div>"
                if dot_cor else
                "<div style='height:10px;'></div>"
            )
            st.markdown(
                f"<div style='text-align:center;padding:4px 0;'>"
                f"<p style='color:#475569;font-size:0.58rem;font-weight:600;"
                f"margin:0;text-transform:uppercase;'>{dl}</p>"
                f"<p style='color:{num_col};font-size:0.8rem;font-weight:{num_wt};"
                f"margin:3px 0 0;'>{d.day}</p>"
                f"{dot_html}</div>",
                unsafe_allow_html=True
            )

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    # ── Lista registos aprovados ──────────────────────────────────────
    if not regs_7.empty:
        total_7 = regs_7['Horas_Total'].sum()

        col_tl, col_tv = st.columns([3, 1])
        with col_tl:
            st.markdown(
                "<p style='color:#64748B;font-size:0.78rem;margin:0;'>Registos aprovados</p>",
                unsafe_allow_html=True
            )
        with col_tv:
            st.markdown(
                f"<p style='color:#10B981;font-weight:800;font-size:0.82rem;"
                f"text-align:right;margin:0;'>{fh(total_7)}</p>",
                unsafe_allow_html=True
            )

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

        for _, r in regs_7.sort_values('Data_d', ascending=False).head(5).iterrows():
            try:
                ds = pd.Timestamp(r['Data_d']).strftime('%d/%m')
            except:
                ds = str(r.get('Data', ''))[:5]

            sub = f"{ds} · {r.get('Frente','') or r.get('Turnos','')}"

            col_i, col_hv = st.columns([4, 1])
            with col_i:
                st.markdown(
                    f"<div style='border-left:3px solid #10B981;"
                    f"padding:8px 12px;background:#1E293B;"
                    f"border-radius:0 10px 10px 0;margin-bottom:6px;'>"
                    f"<p style='margin:0;font-weight:700;color:#F1F5F9;font-size:0.86rem;'>"
                    f"{r.get('Obra','')}</p>"
                    f"<p style='margin:2px 0 0;color:#64748B;font-size:0.73rem;'>{sub}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with col_hv:
                st.markdown(
                    f"<p style='color:#10B981;font-weight:900;font-size:0.92rem;"
                    f"text-align:right;margin:12px 0 0;'>{fh(r.get('Horas_Total', 0))}</p>",
                    unsafe_allow_html=True
                )
    else:
        st.markdown(
            "<div style='background:#1E293B;border-radius:14px;padding:36px 20px;"
            "text-align:center;border:1px dashed #334155;'>"
            "<p style='font-size:2rem;margin:0 0 8px;opacity:0.3;'>📋</p>"
            "<p style='color:#475569;font-size:0.84rem;margin:0;font-weight:600;'>"
            "Sem registos aprovados nos últimos 7 dias</p>"
            "<p style='color:#334155;font-size:0.75rem;margin:5px 0 0;'>"
            "Clica em Registar Ponto para começar</p>"
            "</div>",
            unsafe_allow_html=True
        )

    # ── Alertas ───────────────────────────────────────────────────────
    try:
        uc = load_db("usuarios.csv",
                     ["Nome", "PDFs_Validados", "PrecoHoraStatus"], silent=True)
        m_ = uc[uc['Nome'] == user_nome]
        if not m_.empty:
            row = m_.iloc[0]
            if row.get('PDFs_Validados', 'Não') != 'Sim':
                st.warning("📄 Tens documentos obrigatórios por validar.")
            if row.get('PrecoHoraStatus', '') == '':
                st.warning("💰 Tens o preço hora por aceitar.")
            elif row.get('PrecoHoraStatus', '') == 'Recusado':
                st.error("❌ Preço hora recusado — contacta o administrador.")
    except:
        pass

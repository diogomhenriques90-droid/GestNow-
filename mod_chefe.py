"""
GESTNOW v3 — mod_chefe.py
Módulo do Chefe de Equipa / Gestor
"""
import streamlit as st
import pandas as pd
import uuid, secrets, base64, io, json
from datetime import datetime, timedelta, date
import time

from core import (
    save_db, inv, fh, sl, load_db,
    ICONS, COLORS, TIPOS_FRENTE, REGRAS_OURO,
    log_audit, criar_notificacao, process_and_compress_image,
    hp, _load_users_cached
)
from translations import t

# ── Constantes visuais (iguais ao mod_tecnico) ────────────────────────────────
_DOT_COLOR = {
    "0":  "#F97316",
    "1":  "#10B981",
    "2":  "#3B82F6",
    "3":  "#6B7280",
    "4":  "#6B7280",
    "-1": "#EF4444",
}
_DOT_LABEL = {
    "0":  "Pendente",
    "1":  "Validado",
    "2":  "Faturação",
    "3":  "Pago",
    "4":  "Pago",
    "-1": "Rejeitado",
}
_MESES_PT   = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
_DIAS_LETRA = ['D','S','T','Q','Q','S','S']
_HORAS_30   = [f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)]


def _load_users_fresh():
    return _load_users_cached()


def render_chefe(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     *_) = args

    user_nome  = st.session_state.get('user', '')
    user_tipo  = st.session_state.get('tipo', '')
    cargo_user = st.session_state.get('cargo', '')
    hoje       = date.today()

    # ── CSS idêntico ao mod_tecnico ───────────────────────────────────────────
    st.markdown("""
    <style>
    .stApp { background:#0F172A !important; }
    .main .block-container { padding-top:0.5rem !important; }
    h1,h2,h3,h4,h5,h6 { color:#F1F5F9 !important; }
    p,div,span { color:#CBD5E1; }

    .stTabs [data-baseweb="tab-list"] {
        background:#1E293B !important;
        border-bottom:2px solid #334155 !important;
        gap:0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color:#64748B !important; font-size:0.76rem !important;
        padding:10px 6px !important; background:transparent !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color:#DC2626 !important; font-weight:700 !important;
        border-bottom:3px solid #DC2626 !important;
    }
    .stButton>button {
        border-radius:12px !important; font-weight:600 !important;
        height:44px !important;
    }
    .stButton>button[kind="primary"] {
        background:#DC2626 !important; color:white !important;
        border:none !important;
    }
    .stButton>button[kind="secondary"] {
        background:#1E293B !important; color:#CBD5E1 !important;
        border:1px solid #334155 !important;
    }
    .stTextInput label,.stSelectbox label,.stNumberInput label,
    .stTextArea label,.stRadio label,.stCheckbox label {
        color:#CBD5E1 !important; font-size:0.82rem !important;
        font-weight:500 !important;
    }
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stTextArea>div>div>textarea {
        background:#1E293B !important; color:#F1F5F9 !important;
        border:1px solid #334155 !important; border-radius:10px !important;
    }
    .stSelectbox>div>div>div {
        background:#1E293B !important; color:#F1F5F9 !important;
        border:1px solid #334155 !important;
    }
    [data-testid="stHorizontalBlock"] .stButton>button {
        border-radius:50% !important; padding:0 !important;
        height:38px !important; min-height:38px !important;
        width:38px !important; font-size:0.82rem !important;
        font-weight:600 !important;
    }
    .streamlit-expanderHeader {
        background:#1E293B !important; color:#F1F5F9 !important;
        border-radius:10px !important;
    }
    .ponto-card {
        background:#1E3A4A; border-radius:14px;
        padding:16px 18px; margin-bottom:10px;
        box-shadow:0 2px 8px rgba(0,0,0,0.3);
    }
    .ponto-card-header {
        display:flex; justify-content:space-between;
        align-items:flex-start; margin-bottom:10px;
    }
    .ponto-card-title { font-weight:700; color:#F1F5F9; font-size:0.95rem; margin:0; }
    .ponto-card-horas { font-weight:900; color:#F1F5F9; font-size:1.2rem; }
    .ponto-card-status {
        font-size:0.72rem; font-weight:600; padding:2px 8px;
        border-radius:10px; display:inline-block; margin-top:2px;
    }
    .ponto-card-grid {
        display:grid; grid-template-columns:1fr 1fr; gap:6px 16px;
        border-top:1px solid rgba(255,255,255,0.08);
        padding-top:10px; margin-top:4px;
    }
    .ponto-card-label {
        color:#64748B; font-size:0.72rem; font-weight:600;
        text-transform:uppercase; letter-spacing:0.05em;
    }
    .ponto-card-value { color:#CBD5E1; font-size:0.85rem; font-weight:500; }
    .total-horas-bar {
        display:flex; justify-content:space-between; align-items:center;
        padding:12px 4px 8px; border-bottom:1px solid #1E293B; margin-bottom:12px;
    }
    .total-horas-label { color:#64748B; font-size:0.82rem; font-weight:600; }
    .total-horas-value { color:#DC2626; font-size:1.05rem; font-weight:900; }
    </style>
    """, unsafe_allow_html=True)

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center;padding:20px;
        background:linear-gradient(135deg,#1E293B,#0F172A);
        border-radius:16px;margin-bottom:20px;
        border:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:2rem;margin-bottom:6px;">👷</div>
        <div style="font-size:1.3rem;font-weight:800;color:#F8FAFC;">{user_nome}</div>
        <div style="font-size:0.85rem;color:#94A3B8;">{cargo_user} | {user_tipo}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    inicio_mes = hoje.replace(day=1)
    obras_chefe = []
    if not inst_acessos_db.empty and 'Utilizador' in inst_acessos_db.columns:
        obras_chefe = inst_acessos_db[
            inst_acessos_db['Utilizador'] == user_nome
        ]['Obra'].tolist()

    regs_equipa = pd.DataFrame()
    if not registos_db.empty:
        regs_equipa = (registos_db[registos_db['Obra'].isin(obras_chefe)]
                       if obras_chefe else registos_db.copy())

    pendentes = len(regs_equipa[regs_equipa['Status'] == '0']) \
                if not regs_equipa.empty else 0
    horas_mes = 0
    if not regs_equipa.empty:
        regs_mes = regs_equipa[
            pd.to_datetime(
                regs_equipa['Data'], dayfirst=True, errors='coerce'
            ).dt.date >= inicio_mes
        ]
        horas_mes = pd.to_numeric(
            regs_mes['Horas_Total'], errors='coerce'
        ).fillna(0).sum()
    num_tec = len(regs_equipa['Técnico'].unique()) if not regs_equipa.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("👷 Técnicos", num_tec)
    with c2: st.metric("⏱️ Horas Mês", f"{horas_mes:.0f}h")
    with c3: st.metric("⏳ Pendentes", pendentes)
    with c4: st.metric("🏭 Obras",
        len(obras_chefe) or (len(obras_db) if not obras_db.empty else 0))

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "👥 Equipa", "✅ Validar Horas", "📋 Meu Ponto",
        "📊 Folha de Ponto", "🛡️ HSE", "📦 Pedidos"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 0 — EQUIPA
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        st.markdown("### 👷 Visão Geral da Equipa")
        if not regs_equipa.empty:
            resumo = regs_equipa.groupby('Técnico').agg(
                Horas=('Horas_Total', lambda x: pd.to_numeric(x, errors='coerce').sum()),
                Registos=('Técnico', 'count'),
                Pendentes=('Status', lambda x: (x == '0').sum()),
                Aprovados=('Status', lambda x: (x == '1').sum())
            ).reset_index()
            for _, row in resumo.iterrows():
                cor = "#10B981" if row['Pendentes'] == 0 else "#F59E0B"
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05);padding:14px;
                    border-radius:12px;margin-bottom:8px;border-left:4px solid {cor};">
                    <div style="display:flex;justify-content:space-between;">
                        <div>
                            <b style="color:#F8FAFC;">👤 {row['Técnico']}</b>
                            <div style="color:#94A3B8;font-size:0.82rem;">
                                {row['Registos']} registos | {fh(row['Horas'])} totais
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:#10B981;font-size:0.82rem;">✅ {row['Aprovados']}</div>
                            <div style="color:#F59E0B;font-size:0.82rem;">⏳ {row['Pendentes']}</div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("📋 Sem dados de equipa.")

        st.divider()
        st.markdown("### 📣 Comunicado à Equipa")
        with st.form("form_comunicado_chefe"):
            titulo_com   = st.text_input("Título", key="com_ch_titulo")
            conteudo_com = st.text_area("Mensagem", key="com_ch_msg")
            urgente      = st.checkbox("Urgente", key="com_ch_urg")
            if st.form_submit_button("📣 Enviar", use_container_width=True,
                                      type="primary"):
                if titulo_com and conteudo_com:
                    novo = pd.DataFrame([{
                        "ID":       str(uuid.uuid4())[:8].upper(),
                        "Titulo":   titulo_com,
                        "Conteudo": conteudo_com,
                        "Tipo":     "Chefe",
                        "Destino":  "Equipa",
                        "Urgente":  "Sim" if urgente else "Não",
                        "Validade": (date.today() + timedelta(days=30)
                                     ).strftime("%d/%m/%Y")
                    }])
                    upd = pd.concat([comuns_db, novo], ignore_index=True) \
                          if not comuns_db.empty else novo
                    save_db(upd, "comunicados.csv")
                    inv("comunicados.csv")
                    st.success("✅ Comunicado enviado!")
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — VALIDAR HORAS
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown("### ✅ Validação de Horas da Equipa")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            regs_fmt = pd.DataFrame()
            if not regs_equipa.empty:
                regs_fmt = regs_equipa.copy()
                if pd.api.types.is_datetime64_any_dtype(regs_fmt['Data']):
                    regs_fmt['Data'] = regs_fmt['Data'].dt.strftime(
                        '%d/%m/%Y').fillna('—')
                else:
                    regs_fmt['Data'] = regs_fmt['Data'].astype(str).replace(
                        {'NaT': '—', 'None': '—'})
                regs_fmt['Horas_Total'] = pd.to_numeric(
                    regs_fmt['Horas_Total'], errors='coerce').fillna(0)

            df_pend = regs_fmt[regs_fmt['Status'] == '0'] \
                      if not regs_fmt.empty else pd.DataFrame()

            if not df_pend.empty:
                col_vm, col_rm = st.columns(2)
                with col_vm:
                    if st.button("🟢 Validar Todos", key="ch_val_todos",
                                  type="primary", use_container_width=True):
                        for tec in df_pend['Técnico'].unique():
                            registos_db.loc[
                                (registos_db['Técnico'] == tec) &
                                (registos_db['Status'] == '0'), 'Status'
                            ] = '1'
                            criar_notificacao(
                                destinatario=tec,
                                titulo="🟢 Horas Validadas",
                                mensagem=f"As tuas horas foram validadas por {user_nome}.",
                                tipo="success", acao_url="/")
                        save_db(registos_db, "registos.csv")
                        inv("registos.csv")
                        st.success("✅ Todos validados!")
                        st.rerun()
                with col_rm:
                    if st.button("❌ Rejeitar Todos", key="ch_rej_todos",
                                  use_container_width=True):
                        for tec in df_pend['Técnico'].unique():
                            registos_db.loc[
                                (registos_db['Técnico'] == tec) &
                                (registos_db['Status'] == '0'), 'Status'
                            ] = '-1'
                            criar_notificacao(
                                destinatario=tec,
                                titulo="❌ Horas Rejeitadas",
                                mensagem=f"As tuas horas foram rejeitadas. Contacta {user_nome}.",
                                tipo="error", acao_url="/")
                        save_db(registos_db, "registos.csv")
                        inv("registos.csv")
                        st.error("❌ Todos rejeitados.")
                        st.rerun()

                st.markdown("---")

                for tecnico in df_pend['Técnico'].unique():
                    regs_t    = df_pend[df_pend['Técnico'] == tecnico]
                    total_h_t = regs_t['Horas_Total'].sum()

                    with st.expander(
                        f"👤 {tecnico} — {fh(total_h_t)} ({len(regs_t)} registos)",
                        expanded=True
                    ):
                        col_vt, col_rt = st.columns(2)
                        with col_vt:
                            if st.button(f"🟢 Validar {tecnico}",
                                          key=f"apr_{tecnico}",
                                          use_container_width=True,
                                          type="primary"):
                                registos_db.loc[
                                    (registos_db['Técnico'] == tecnico) &
                                    (registos_db['Status'] == '0'), 'Status'
                                ] = '1'
                                save_db(registos_db, "registos.csv")
                                criar_notificacao(
                                    destinatario=tecnico,
                                    titulo="🟢 Horas Validadas",
                                    mensagem=f"As tuas horas foram validadas por {user_nome}.",
                                    tipo="success", acao_url="/")
                                inv("registos.csv")
                                st.success("✅")
                                st.rerun()
                        with col_rt:
                            if st.button(f"❌ Rejeitar {tecnico}",
                                          key=f"rej_{tecnico}",
                                          use_container_width=True,
                                          type="secondary"):
                                registos_db.loc[
                                    (registos_db['Técnico'] == tecnico) &
                                    (registos_db['Status'] == '0'), 'Status'
                                ] = '-1'
                                save_db(registos_db, "registos.csv")
                                criar_notificacao(
                                    destinatario=tecnico,
                                    titulo="❌ Horas Rejeitadas",
                                    mensagem=f"As tuas horas foram rejeitadas. Contacta {user_nome}.",
                                    tipo="error", acao_url="/")
                                inv("registos.csv")
                                st.error("❌")
                                st.rerun()

                        st.markdown("---")

                        for _, reg in regs_t.iterrows():
                            reg_id = reg.get('ID', '')
                            col_i, col_v, col_r = st.columns([5, 1, 1])
                            with col_i:
                                st.markdown(
                                    f"<div style='background:#0F172A;border-radius:8px;"
                                    f"padding:8px 12px;margin-bottom:3px;'>"
                                    f"<span style='color:#F1F5F9;font-size:0.85rem;'>"
                                    f"{reg.get('Data','')} · {reg.get('Obra','')} · "
                                    f"{reg.get('Frente','')} · {reg.get('Turnos','')}</span>"
                                    f"<span style='float:right;color:#F59E0B;"
                                    f"font-weight:700;'>{fh(reg.get('Horas_Total',0))}</span>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                            with col_v:
                                if st.button("✅", key=f"val_ind_{reg_id}",
                                              use_container_width=True,
                                              help="Validar"):
                                    registos_db.loc[
                                        registos_db['ID'] == reg_id, 'Status'
                                    ] = '1'
                                    save_db(registos_db, "registos.csv")
                                    criar_notificacao(
                                        destinatario=tecnico,
                                        titulo="🟢 Horas Validadas",
                                        mensagem=f"{fh(reg.get('Horas_Total',0))} em "
                                                 f"{reg.get('Obra','')} validadas.",
                                        tipo="success", acao_url="/")
                                    inv("registos.csv")
                                    st.rerun()
                            with col_r:
                                if st.button("❌", key=f"rej_ind_{reg_id}",
                                              use_container_width=True,
                                              help="Rejeitar"):
                                    registos_db.loc[
                                        registos_db['ID'] == reg_id, 'Status'
                                    ] = '-1'
                                    save_db(registos_db, "registos.csv")
                                    criar_notificacao(
                                        destinatario=tecnico,
                                        titulo="❌ Horas Rejeitadas",
                                        mensagem=f"{fh(reg.get('Horas_Total',0))} rejeitadas.",
                                        tipo="error", acao_url="/")
                                    inv("registos.csv")
                                    st.rerun()
            else:
                st.success("✅ Sem horas pendentes!")

        with sub_h:
            hist = regs_equipa[
                regs_equipa['Status'].isin(['1', '2', '3', '-1'])
            ] if not regs_equipa.empty else pd.DataFrame()
            if not hist.empty:
                hist = hist.copy()
                if pd.api.types.is_datetime64_any_dtype(hist['Data']):
                    hist['Data'] = hist['Data'].dt.strftime('%d/%m/%Y').fillna('—')
                hist['Estado'] = hist['Status'].map({
                    "1": "🟢 Validado", "2": "🔵 Faturação",
                    "3": "⚫ Processado", "-1": "❌ Rejeitado"
                })
                cols_show = [c for c in ['Data', 'Técnico', 'Obra',
                                          'Horas_Total', 'Estado']
                             if c in hist.columns]
                st.dataframe(hist[cols_show], use_container_width=True,
                             hide_index=True)
            else:
                st.info("📋 Sem histórico.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — MEU PONTO (estilo Meivworld, idêntico ao mod_tecnico)
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[2]:

        # ── Session state ─────────────────────────────────────────────────
        for k, v in [
            ('data_consulta_ch',     hoje),
            ('semana_offset_ch',     0),
            ('show_reg_form_ch',     False),
            ('periodos_trabalho_ch', [{"entrada": "08:00", "saida": "17:00"}]),
        ]:
            if k not in st.session_state:
                st.session_state[k] = v

        # ── Foto do chefe ─────────────────────────────────────────────────
        foto_b64 = ""
        try:
            u_data = _load_users_fresh()
            u_match = u_data[u_data['Nome'] == user_nome]
            if not u_match.empty:
                foto_b64 = str(u_match.iloc[0].get('Foto', ''))
        except:
            pass

        # ── Calcular dots de status ───────────────────────────────────────
        dias_status = {}
        if not registos_db.empty and 'Técnico' in registos_db.columns:
            ru = registos_db[registos_db['Técnico'] == user_nome].copy()
            if not ru.empty:
                ru['Data_d'] = pd.to_datetime(
                    ru['Data'], dayfirst=True, errors='coerce'
                ).dt.normalize().dt.date
                sp = {"-1": 6, "0": 5, "1": 4, "2": 3, "3": 2, "4": 1}
                for d_u in ru['Data_d'].dropna().unique():
                    rd   = ru[ru['Data_d'] == d_u]
                    pior = max(rd['Status'].tolist(),
                               key=lambda s: sp.get(str(s), 0))
                    dias_status[d_u] = str(pior)

        # ══════════════════════════════════════════════════════════════
        # VISTA CALENDÁRIO
        # ══════════════════════════════════════════════════════════════
        if not st.session_state.show_reg_form_ch:

            data_ref   = hoje + timedelta(weeks=st.session_state.semana_offset_ch)
            inicio_sem = data_ref - timedelta(days=(data_ref.weekday() + 1) % 7)
            dias_sem   = [inicio_sem + timedelta(days=i) for i in range(7)]
            mes_label  = _MESES_PT[dias_sem[3].month - 1]
            ano_label  = dias_sem[3].year

            col_prev, col_mes, col_foto = st.columns([1, 5, 1])
            with col_prev:
                if st.button("‹", key="ch_cal_prev", use_container_width=True):
                    st.session_state.semana_offset_ch -= 1
                    st.rerun()
            with col_mes:
                st.markdown(
                    f"<div style='text-align:center;padding:6px 0;'>"
                    f"<p style='color:#F1F5F9;font-weight:700;font-size:0.88rem;"
                    f"margin:0 0 2px;'>Meu Ponto</p>"
                    f"<p style='color:#DC2626;font-weight:900;font-size:1.05rem;"
                    f"margin:0;'>{mes_label} {ano_label}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with col_foto:
                col_next, col_img = st.columns([1, 1])
                with col_next:
                    if st.button("›", key="ch_cal_next", use_container_width=True):
                        st.session_state.semana_offset_ch += 1
                        st.rerun()
                with col_img:
                    if foto_b64 and len(foto_b64) > 100:
                        try:
                            st.markdown(
                                f"<img src='data:image/jpeg;base64,{foto_b64}' "
                                f"style='width:34px;height:34px;border-radius:50%;"
                                f"object-fit:cover;border:2px solid #DC2626;"
                                f"margin-top:2px;'>",
                                unsafe_allow_html=True
                            )
                        except:
                            pass

            letras_cols = st.columns(7)
            for col, d in zip(letras_cols, dias_sem):
                with col:
                    dl    = _DIAS_LETRA[(d.weekday() + 1) % 7]
                    fim_s = (d.weekday() + 1) % 7 in (0, 6)
                    cor_l = "#475569" if fim_s else "#64748B"
                    st.markdown(
                        f"<p style='text-align:center;color:{cor_l};"
                        f"font-size:0.6rem;font-weight:700;margin:0;"
                        f"text-transform:uppercase;'>{dl}</p>",
                        unsafe_allow_html=True
                    )

            btn_cols = st.columns(7)
            for col, d in zip(btn_cols, dias_sem):
                with col:
                    dot_cor  = _DOT_COLOR.get(dias_status.get(d, ''), '')
                    eh_sel   = d == st.session_state.data_consulta_ch
                    btn_type = "primary" if eh_sel else "secondary"
                    if st.button(str(d.day),
                                 key=f"ch_day_{d.strftime('%Y%m%d')}",
                                 use_container_width=True,
                                 type=btn_type):
                        st.session_state.data_consulta_ch = d
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
                "flex-wrap:wrap;margin:4px 0 8px;'>"
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
                "<hr style='border:none;border-top:1px solid #1E293B;"
                "margin:4px 0 10px;'>",
                unsafe_allow_html=True
            )

            data_sel    = st.session_state.data_consulta_ch
            mes_nome    = _MESES_PT[data_sel.month - 1]
            dia_letra   = _DIAS_LETRA[(data_sel.weekday() + 1) % 7]
            eh_hoje_sel = data_sel == hoje

            col_data, col_fab = st.columns([4, 1])
            with col_data:
                prefix = "📍 Hoje" if eh_hoje_sel else dia_letra
                st.markdown(
                    f"<p style='color:#F1F5F9;font-weight:700;"
                    f"font-size:0.92rem;margin:0;'>"
                    f"{prefix}, {data_sel.day} de {mes_nome}</p>",
                    unsafe_allow_html=True
                )
            with col_fab:
                if st.button("＋", key="ch_fab_btn", type="primary",
                             use_container_width=True):
                    st.session_state.show_reg_form_ch    = True
                    st.session_state.periodos_trabalho_ch = [
                        {"entrada": "08:00", "saida": "17:00"}
                    ]
                    st.rerun()

            st.markdown("<div style='height:6px;'></div>",
                        unsafe_allow_html=True)

            # Cards do dia
            regs_dia = pd.DataFrame()
            if not registos_db.empty and 'Técnico' in registos_db.columns:
                meus = registos_db[
                    registos_db['Técnico'] == user_nome
                ].copy()
                if not meus.empty:
                    data_sel_d = data_sel.date() \
                                 if hasattr(data_sel, 'date') else data_sel
                    dp = pd.to_datetime(
                        meus['Data'], dayfirst=True, errors='coerce'
                    ).dt.normalize().dt.date
                    regs_dia = meus[dp == data_sel_d].copy()

            if not regs_dia.empty:
                regs_dia['_h'] = pd.to_numeric(
                    regs_dia['Horas_Total'], errors='coerce'
                ).fillna(0)
                total_dia = regs_dia['_h'].sum()
                st.markdown(
                    f"<div class='total-horas-bar'>"
                    f"<span class='total-horas-label'>Total de horas reportadas</span>"
                    f"<span class='total-horas-value'>{fh(total_dia)}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                for _, r in regs_dia.iterrows():
                    s_str  = str(r.get('Status', '0'))
                    dot_c  = _DOT_COLOR.get(s_str, '#6B7280')
                    dot_l  = _DOT_LABEL.get(s_str, 'Pendente')
                    turnos = str(r.get('Turnos', ''))
                    obra   = str(r.get('Obra', ''))
                    frente = str(r.get('Frente', ''))
                    horas_r = r.get('Horas_Total', 0)
                    relat  = str(r.get('Relatorio', ''))[:60]
                    entrada_str = saida_str = ""
                    if '-' in turnos:
                        partes = turnos.split('-')
                        if len(partes) == 2:
                            entrada_str = partes[0].strip()
                            saida_str   = partes[1].strip()
                    cod_obra = cli_obra = ""
                    if not obras_db.empty and obra in obras_db['Obra'].values:
                        oi       = obras_db[obras_db['Obra'] == obra].iloc[0]
                        cod_obra = str(oi.get('Codigo', ''))
                        cli_obra = str(oi.get('Cliente', ''))
                    st.markdown(
                        f"<div class='ponto-card' style='border-left:4px solid {dot_c};'>"
                        f"<div class='ponto-card-header'>"
                        f"<div>"
                        f"<p class='ponto-card-title'>{frente if frente else obra}</p>"
                        f"<span class='ponto-card-status' "
                        f"style='background:{dot_c}22;color:{dot_c};'>{dot_l}</span>"
                        f"</div>"
                        f"<span class='ponto-card-horas'>{fh(horas_r)}</span>"
                        f"</div>"
                        f"<div class='ponto-card-grid'>"
                        f"<div><p class='ponto-card-label'>Cliente</p>"
                        f"<p class='ponto-card-value'>{cli_obra if cli_obra else obra}</p></div>"
                        f"<div style='text-align:right;'><p class='ponto-card-label'>Entrada</p>"
                        f"<p class='ponto-card-value'><b>{entrada_str if entrada_str else '—'}</b></p></div>"
                        f"<div><p class='ponto-card-label'>{cod_obra if cod_obra else 'Obra'}</p>"
                        f"<p class='ponto-card-value'>"
                        f"{obra[:28] if not cod_obra else frente[:28]}</p></div>"
                        f"<div style='text-align:right;'><p class='ponto-card-label'>Saída</p>"
                        f"<p class='ponto-card-value'><b>{saida_str if saida_str else '—'}</b></p></div>"
                        f"</div>"
                        + (f"<p style='color:#475569;font-size:0.73rem;"
                           f"margin:8px 0 0;border-top:1px solid rgba(255,255,255,0.06);"
                           f"padding-top:6px;'>{relat}</p>" if relat else "")
                        + "</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.markdown(
                    "<div style='text-align:center;padding:50px 20px 40px;'>"
                    "<div style='font-size:3.5rem;margin-bottom:12px;opacity:0.25;'>📋</div>"
                    "<p style='color:#475569;font-weight:600;margin:0;"
                    "font-size:0.9rem;'>Sem ponto registado neste dia</p>"
                    "</div>",
                    unsafe_allow_html=True
                )

        # ══════════════════════════════════════════════════════════════
        # FORMULÁRIO DE REGISTO (idêntico ao mod_tecnico)
        # ══════════════════════════════════════════════════════════════
        else:
            data_sel = st.session_state.data_consulta_ch

            # Cabeçalho foto + nome + data
            foto_html = ""
            if foto_b64 and len(foto_b64) > 100:
                foto_html = (
                    f"<img src='data:image/jpeg;base64,{foto_b64}' "
                    f"style='width:44px;height:44px;border-radius:50%;"
                    f"object-fit:cover;border:2px solid #DC2626;flex-shrink:0;'>"
                )
            else:
                ini = str(user_nome)[:1].upper()
                foto_html = (
                    f"<div style='width:44px;height:44px;border-radius:50%;"
                    f"background:#DC2626;display:flex;align-items:center;"
                    f"justify-content:center;font-weight:900;color:white;"
                    f"font-size:1.1rem;flex-shrink:0;'>{ini}</div>"
                )

            st.markdown(
                f"<div style='background:#1E293B;border-radius:14px;"
                f"padding:14px 16px;margin-bottom:14px;"
                f"border:1px solid #334155;"
                f"display:flex;align-items:center;gap:14px;'>"
                f"{foto_html}"
                f"<div style='flex:1;'>"
                f"<p style='color:#94A3B8;font-size:0.7rem;margin:0;'>"
                f"Registo de ponto</p>"
                f"<p style='color:#F1F5F9;font-weight:700;"
                f"font-size:0.95rem;margin:2px 0 0;'>{user_nome}</p>"
                f"<p style='color:#DC2626;font-size:0.82rem;"
                f"font-weight:600;margin:1px 0 0;'>"
                f"{data_sel.strftime('%d/%m/%Y')}</p>"
                f"</div></div>",
                unsafe_allow_html=True
            )

            with st.form("form_ponto_ch", clear_on_submit=False):
                st.markdown(
                    "<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                    "letter-spacing:0.08em;text-transform:uppercase;margin:0 0 6px;'>"
                    "🏗️ Obra</p>",
                    unsafe_allow_html=True
                )
                obras_lista = []
                if not obras_db.empty:
                    at = obras_db[obras_db['Ativa'] == 'Ativa']
                    obras_lista = (at['Obra'].tolist() if not at.empty
                                   else obras_db['Obra'].tolist())
                obra_sel = st.selectbox(
                    "Obra",
                    obras_lista if obras_lista else ["Sem obras"],
                    key="ch_reg_obra",
                    label_visibility="collapsed"
                )

                if not obras_db.empty and obra_sel in obras_db['Obra'].values:
                    oi  = obras_db[obras_db['Obra'] == obra_sel].iloc[0]
                    cod = str(oi.get('Codigo', ''))
                    cli = str(oi.get('Cliente', ''))
                    if cod or cli:
                        st.markdown(
                            f"<div style='background:#0F172A;border-radius:10px;"
                            f"padding:10px 14px;margin:-4px 0 10px;"
                            f"border-left:3px solid #DC2626;'>"
                            f"<p style='color:#F1F5F9;font-weight:700;"
                            f"font-size:0.82rem;margin:0;'>"
                            f"{cli if cli else obra_sel}</p>"
                            f"{'<p style=color:#DC2626;font-size:0.72rem;margin:2px 0 0;>' + cod + '</p>' if cod else ''}"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                st.markdown(
                    "<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                    "letter-spacing:0.08em;text-transform:uppercase;"
                    "margin:8px 0 6px;'>🔧 Frente de Trabalho</p>",
                    unsafe_allow_html=True
                )
                frente_sel = st.selectbox(
                    "Frente", TIPOS_FRENTE,
                    key="ch_reg_frente",
                    label_visibility="collapsed"
                )

                st.markdown(
                    "<hr style='border:none;border-top:1px solid #1E293B;"
                    "margin:12px 0;'>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    "<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                    "letter-spacing:0.08em;text-transform:uppercase;"
                    "margin:0 0 8px;'>⏱️ Horas de Trabalho</p>",
                    unsafe_allow_html=True
                )

                total_horas      = 0.0
                periodos_validos = []

                for idx, periodo in enumerate(
                    st.session_state.periodos_trabalho_ch
                ):
                    if idx > 0:
                        st.markdown(
                            "<hr style='border:none;border-top:1px dashed "
                            "#1E293B;margin:6px 0;'>",
                            unsafe_allow_html=True
                        )
                    col_e, col_s = st.columns(2)
                    with col_e:
                        ie = (_HORAS_30.index(periodo["entrada"])
                              if periodo["entrada"] in _HORAS_30 else 16)
                        entrada = st.selectbox(
                            f"Entrada" + (f" {idx+1}" if
                               len(st.session_state.periodos_trabalho_ch) > 1
                               else ""),
                            _HORAS_30, index=ie, key=f"ch_ent_{idx}"
                        )
                    with col_s:
                        is_ = (_HORAS_30.index(periodo["saida"])
                               if periodo["saida"] in _HORAS_30 else 34)
                        saida = st.selectbox(
                            f"Saída" + (f" {idx+1}" if
                               len(st.session_state.periodos_trabalho_ch) > 1
                               else ""),
                            _HORAS_30, index=is_, key=f"ch_sai_{idx}"
                        )
                    t1    = datetime.strptime(entrada, "%H:%M")
                    t2    = datetime.strptime(saida,   "%H:%M")
                    delta = (t2 - t1).seconds / 3600
                    if delta > 0:
                        total_horas += delta
                        periodos_validos.append({
                            "entrada": entrada, "saida": saida,
                            "horas": round(delta, 2)
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
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin:10px 0;"
                        f"display:flex;justify-content:space-between;"
                        f"align-items:center;'>"
                        f"<span style='color:#64748B;font-size:0.78rem;"
                        f"font-weight:600;text-transform:uppercase;"
                        f"letter-spacing:0.06em;'>Total</span>"
                        f"<span style='color:#F1F5F9;font-size:1.6rem;"
                        f"font-weight:900;'>{fh(total_horas)}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                relatorio = st.text_area(
                    "📝 Descrição (opcional)",
                    placeholder="Ex: Supervisão, reunião, visita...",
                    key="ch_reg_relat", height=70
                )
                st.markdown("<div style='height:6px;'></div>",
                            unsafe_allow_html=True)
                col_c, col_g = st.columns(2)
                with col_c:
                    mais_per = st.form_submit_button(
                        "➕ Adicionar Período",
                        use_container_width=True
                    )
                with col_g:
                    guardar = st.form_submit_button(
                        "💾 Guardar Ponto",
                        use_container_width=True,
                        type="primary"
                    )

            if st.button("← Voltar", key="ch_btn_voltar"):
                st.session_state.show_reg_form_ch    = False
                st.session_state.periodos_trabalho_ch = [
                    {"entrada": "08:00", "saida": "17:00"}
                ]
                st.rerun()

            if mais_per:
                st.session_state.periodos_trabalho_ch.append(
                    {"entrada": "13:00", "saida": "17:00"}
                )
                st.rerun()

            if guardar:
                if total_horas <= 0:
                    st.error("⚠️ Horas têm de ser superiores a 0.")
                elif not obra_sel or obra_sel == "Sem obras":
                    st.error("⚠️ Seleciona uma obra.")
                else:
                    regs_atual = (registos_db.copy()
                                  if not registos_db.empty
                                  else pd.DataFrame())
                    ids_guardados = []
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
                        ids_guardados.append(new_r['ID'].iloc[0])
                        regs_atual = pd.concat(
                            [regs_atual, new_r], ignore_index=True
                        )
                    save_db(regs_atual, "registos.csv")
                    for reg_id in ids_guardados:
                        log_audit(
                            usuario=user_nome, acao="REGISTAR_PONTO_CHEFE",
                            tabela="registos.csv", registro_id=reg_id,
                            detalhes=f"{total_horas}h em {obra_sel}", ip=""
                        )
                    criar_notificacao(
                        destinatario="admin",
                        titulo="📋 Novo Registo de Ponto (Chefe)",
                        mensagem=f"{user_nome} registou {fh(total_horas)} em {obra_sel}",
                        tipo="info", acao_url="/admin?tab=validacoes"
                    )
                    st.session_state.show_reg_form_ch    = False
                    st.session_state.periodos_trabalho_ch = [
                        {"entrada": "08:00", "saida": "17:00"}
                    ]
                    st.session_state.data_consulta_ch = data_sel
                    inv("registos.csv")
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — FOLHA DE PONTO
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown("### 📊 Folha de Ponto")

        obras_l_fp = obras_db['Obra'].unique().tolist() \
                     if not obras_db.empty else ["Sem Obras"]
        obra_fp = st.selectbox("Obra", obras_l_fp, key="fp_ch_obra")
        ini_s   = hoje - timedelta(days=hoje.weekday())
        c1, c2  = st.columns(2)
        with c1:
            sem_ini = st.date_input("Início da Semana", value=ini_s,
                                     key="fp_ch_ini")
        with c2:
            sem_fim = st.date_input("Fim da Semana",
                                     value=ini_s + timedelta(days=6),
                                     key="fp_ch_fim")

        regs_fp = pd.DataFrame()
        if not registos_db.empty:
            dp_fp = pd.to_datetime(
                registos_db['Data'], dayfirst=True, errors='coerce'
            ).dt.date
            regs_fp = registos_db[
                (registos_db['Obra'] == obra_fp) &
                (dp_fp >= sem_ini) &
                (dp_fp <= sem_fim)
            ]

        if not regs_fp.empty:
            st.markdown(
                f"#### Registos — {sem_ini.strftime('%d/%m')} a "
                f"{sem_fim.strftime('%d/%m/%Y')}"
            )
            for tec in regs_fp['Técnico'].unique():
                rt  = regs_fp[regs_fp['Técnico'] == tec]
                tot = pd.to_numeric(
                    rt['Horas_Total'], errors='coerce'
                ).fillna(0).sum()
                st.markdown(
                    f"<div style='background:#1E293B;border-radius:10px;"
                    f"padding:12px 16px;margin-bottom:8px;'>"
                    f"<b style='color:#F1F5F9;'>👤 {tec}</b>"
                    f"<span style='float:right;color:#DC2626;"
                    f"font-weight:900;'>{fh(tot)}</span><br>"
                    f"<small style='color:#64748B;'>{len(rt)} dia(s)</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")
        st.markdown("### ✍️ Gerar Folha com Selo Digital")
        nome_resp = st.text_input("Nome do Responsável", key="fp_ch_resp")
        if st.button("🔒 Gerar Folha com Selo", use_container_width=True,
                      type="primary", key="btn_fp_ch"):
            if nome_resp:
                esign_id = secrets.token_hex(6).upper()
                ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                nova = pd.DataFrame([{
                    "ID":              str(uuid.uuid4())[:8].upper(),
                    "Obra":            obra_fp,
                    "Periodo":         (f"{sem_ini.strftime('%d/%m')}"
                                        f"-{sem_fim.strftime('%d/%m/%Y')}"),
                    "Responsavel":     nome_resp,
                    "Data_Assinatura": ts,
                    "Assinatura_b64":  "",
                    "Selo":            esign_id,
                    "Status":          "Assinado"
                }])
                upd = pd.concat([folhas_db, nova], ignore_index=True) \
                      if not folhas_db.empty else nova
                save_db(upd, "folhas_ponto.csv")
                log_audit(
                    usuario=user_nome, acao="ASSINAR_FOLHA_PONTO",
                    tabela="folhas_ponto.csv",
                    registro_id=nova['ID'].iloc[0],
                    detalhes=f"Folha assinada: {nome_resp} | {obra_fp}",
                    ip=""
                )
                st.markdown(
                    f"<div style='border:2px dashed #10B981;padding:15px;"
                    f"background:rgba(16,185,129,0.1);border-radius:10px;"
                    f"font-family:monospace;color:#10B981;'>"
                    f"<b>🔒 SELO #{esign_id}</b><br>"
                    f"Assinado por: {nome_resp} | {ts}<br>"
                    f"Período: {sem_ini.strftime('%d/%m')} a "
                    f"{sem_fim.strftime('%d/%m/%Y')} | Obra: {obra_fp}"
                    f"</div>",
                    unsafe_allow_html=True
                )
                inv("folhas_ponto.csv")
                st.success(f"✅ Folha #{esign_id} gerada!")
                st.rerun()
            else:
                st.warning("⚠️ Indica o nome do responsável.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — HSE
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[4]:
        st.markdown("### 🛡️ Segurança & HSE")
        sub_r, sub_rep, sub_list = st.tabs([
            "📋 Regras de Ouro", "⚠️ Reportar", "📊 Incidentes"
        ])

        with sub_r:
            for ic, tit, des in REGRAS_OURO:
                with st.expander(f"{ic} {tit}"):
                    st.write(des)

        with sub_rep:
            with st.form("hse_ch_form"):
                o_hse = st.selectbox(
                    "Obra",
                    obras_db['Obra'].unique().tolist()
                    if not obras_db.empty else ["Geral"]
                )
                g_hse = st.selectbox(
                    "Gravidade", ["Baixa", "Média", "Alta (Crítica)"]
                )
                d_hse = st.text_area("Descrição")
                if st.form_submit_button("🛡️ Submeter Alerta HSE",
                                          use_container_width=True,
                                          type="primary"):
                    if d_hse:
                        ni = pd.DataFrame([{
                            "ID":         str(uuid.uuid4())[:8].upper(),
                            "Data":       date.today().strftime("%d/%m/%Y"),
                            "Utilizador": user_nome,
                            "Obra":       o_hse,
                            "Status":     "Aberto",
                            "Gravidade":  g_hse,
                            "Descricao":  d_hse,
                            "Tipo":       "HSE"
                        }])
                        upd = pd.concat([incs_db, ni], ignore_index=True) \
                              if not incs_db.empty else ni
                        save_db(upd, "incidentes.csv")
                        inv("incidentes.csv")
                        st.success("✅ Alerta HSE submetido!")
                        st.rerun()

        with sub_list:
            if not incs_db.empty:
                i_eq = incs_db[incs_db['Obra'].isin(obras_chefe)] \
                       if obras_chefe else incs_db
                cols_s = [c for c in [
                    'Data', 'Utilizador', 'Obra', 'Descricao', 'Gravidade', 'Status'
                ] if c in i_eq.columns]
                if not i_eq.empty:
                    st.dataframe(i_eq[cols_s], use_container_width=True,
                                 hide_index=True)
                else:
                    st.success("✅ Sem incidentes.")
            else:
                st.success("✅ Sem incidentes.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — PEDIDOS
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[5]:
        st.markdown("### 📦 Pedidos da Equipa")
        tecnicos_equipa = regs_equipa['Técnico'].unique().tolist() \
                          if not regs_equipa.empty else []

        sub_f, sub_e, sub_m = st.tabs([
            "🔧 Ferramentas", "🦺 EPIs", "📦 Materiais"
        ])

        def _mostrar_pedidos(df):
            if df.empty:
                st.info("📋 Sem pedidos.")
                return
            df_eq = (df[df['Solicitante'].isin(tecnicos_equipa)]
                     if tecnicos_equipa and 'Solicitante' in df.columns
                     else df)
            if df_eq.empty:
                st.success("✅ Sem pedidos da equipa.")
                return
            for _, ped in df_eq.iterrows():
                cor = {
                    "Pendente":  "#F59E0B",
                    "Aprovado":  "#10B981",
                    "Rejeitado": "#EF4444"
                }.get(ped.get('Status', 'Pendente'), "#6B7280")
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05);"
                     "border-left:4px solid {cor};"
                     "padding:12px;border-radius:8px;margin-bottom:8px;">
                    <b style="color:#F8FAFC;">
                        {ped.get('Descricao', ped.get('Item', 'N/A'))}
                    </b><br>
                    <small style="color:#94A3B8;">
                        {ped.get('Solicitante','N/A')} |
                        {ped.get('Obra','N/A')} |
                        {ped.get('Data','N/A')}
                    </small><br>
                    <small style="color:{cor};font-weight:bold;">
                        {ped.get('Status','Pendente')}
                    </small>
                </div>
                """, unsafe_allow_html=True)

        with sub_f: _mostrar_pedidos(req_fer_db)
        with sub_e: _mostrar_pedidos(req_epi_db)
        with sub_m: _mostrar_pedidos(req_mat_db)

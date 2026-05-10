import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import fh, ICONS, load_db, inv, _gcs_read

_MESES_PT = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
             'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
_DOT_COLOR = {
    "0": "#F97316",  # Laranja  — pendente
    "1": "#10B981",  # Verde    — validado
    "2": "#3B82F6",  # Azul     — faturação
    "3": "#6B7280",  # Cinzento — pago
    "4": "#6B7280",
}

def render_inicio(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    user_nome = st.session_state.get('user', 'Utilizador')
    user_tipo = st.session_state.get('tipo',  'Técnico')
    cargo     = st.session_state.get('cargo', 'Técnico')

    hoje       = date.today()
    inicio_mes = hoje.replace(day=1)
    sete_dias  = hoje - timedelta(days=6)

    hora = datetime.now().hour
    saudacao = "Bom dia" if hora < 12 else "Boa tarde" if hora < 19 else "Boa noite"

    # ── CSS ───────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .stApp { background: #0F172A !important; }
    [data-testid="stMetric"] {
        background: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 14px !important;
    }
    [data-testid="stMetricValue"] { color: #DC2626 !important; font-weight:900 !important; }
    [data-testid="stMetricLabel"] { color: #64748B !important; }
    h1,h2,h3,h4,h5,h6 { color: #F1F5F9 !important; }
    p, div, span { color: #CBD5E1; }
    .stButton > button[kind="primary"] {
        background: #DC2626 !important; color: white !important;
        border: none !important; border-radius: 12px !important;
        font-weight: 700 !important;
    }
    .stButton > button[kind="secondary"] {
        background: #1E293B !important; color: #CBD5E1 !important;
        border: 1px solid #334155 !important; border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Calcular estatísticas ─────────────────────────────────────────
    horas_mes       = 0.0
    horas_pendentes = 0.0
    regs_ultimos7   = pd.DataFrame()

    if not registos_db.empty and 'Técnico' in registos_db.columns:
        ru = registos_db[registos_db['Técnico'] == user_nome].copy()
        if not ru.empty:
            ru['Data_d']     = pd.to_datetime(ru['Data'], dayfirst=True, errors='coerce').dt.date
            ru['Horas_Total'] = pd.to_numeric(ru['Horas_Total'], errors='coerce').fillna(0)
            horas_mes        = ru[(ru['Data_d'] >= inicio_mes) & (ru['Status']=='1')]['Horas_Total'].sum()
            horas_pendentes  = ru[ru['Status']=='0']['Horas_Total'].sum()
            regs_ultimos7    = ru[(ru['Data_d'] >= sete_dias) & (ru['Status']=='1')].copy()

    # ── Header "Olá / Nome" ───────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E293B 0%,#0F172A 100%);
        border-radius:20px;padding:24px 20px 20px;margin-bottom:20px;
        border:1px solid #334155;">

        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <p style="color:#94A3B8;font-size:0.85rem;margin:0;">
                    {saudacao}
                </p>
                <p style="color:#F1F5F9;font-size:2rem;font-weight:900;
                    margin:2px 0;line-height:1.1;">
                    {user_nome.split()[0] if user_nome else user_nome}
                </p>
                <p style="color:#64748B;font-size:0.8rem;margin:0;">
                    {cargo} · {user_tipo}
                </p>
            </div>
            <div style="display:flex;gap:10px;align-items:center;">
                <div style="width:44px;height:44px;border-radius:50%;
                    background:linear-gradient(135deg,#DC2626,#991B1B);
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.3rem;">
                    👷
                </div>
                <div style="width:40px;height:40px;border-radius:50%;
                    background:#1E293B;border:2px solid #334155;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.1rem;cursor:pointer;">
                    📱
                </div>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:20px;">
            <div style="background:rgba(220,38,38,0.15);border:1px solid rgba(220,38,38,0.3);
                border-radius:14px;padding:16px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <span style="font-size:1.1rem;">⏱️</span>
                    <span style="color:#94A3B8;font-size:0.75rem;">Horas este mês</span>
                </div>
                <p style="color:#F1F5F9;font-size:1.6rem;font-weight:900;margin:0;">
                    {fh(horas_mes)}
                </p>
            </div>
            <div style="background:{'rgba(249,115,22,0.15)' if horas_pendentes > 0 else 'rgba(16,185,129,0.1)'};
                border:1px solid {'rgba(249,115,22,0.4)' if horas_pendentes > 0 else 'rgba(16,185,129,0.3)'};
                border-radius:14px;padding:16px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <span style="font-size:1.1rem;">📋</span>
                    <span style="color:#94A3B8;font-size:0.75rem;">Por validar</span>
                </div>
                <p style="color:#F1F5F9;font-size:1.6rem;font-weight:900;margin:0;">
                    {fh(horas_pendentes)}
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────────
    n_obras = len(obras_db[obras_db['Ativa']=='Ativa']) if not obras_db.empty else 0

    n_pend = 0
    for db_, c_ in [(req_fer_db,'Solicitante'),(req_epi_db,'Solicitante'),(req_mat_db,'Solicitante')]:
        if not db_.empty and c_ in db_.columns:
            n_pend += len(db_[(db_[c_]==user_nome) & (db_['Status']=='Pendente')])

    n_regs_mes = 0
    if not registos_db.empty and 'Técnico' in registos_db.columns:
        ru2 = registos_db[registos_db['Técnico']==user_nome]
        if not ru2.empty:
            dc2 = pd.to_datetime(ru2['Data'],dayfirst=True,errors='coerce').dt.date
            n_regs_mes = int((dc2 >= inicio_mes).sum())

    c1,c2,c3 = st.columns(3)
    with c1: st.metric("🏭 Obras Ativas",   n_obras)
    with c2: st.metric("📦 Pedidos Pend.",  n_pend)
    with c3: st.metric("📋 Registos Mês",   n_regs_mes)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── Navegação Rápida ──────────────────────────────────────────────
    st.markdown("""
    <p style="color:#94A3B8;font-size:0.7rem;font-weight:700;
        letter-spacing:0.1em;text-transform:uppercase;margin:0 0 10px;">
        Acesso Rápido
    </p>""", unsafe_allow_html=True)

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

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── Mini-calendário de status últimos 7 dias ──────────────────────
    st.markdown("""
    <p style="color:#94A3B8;font-size:0.7rem;font-weight:700;
        letter-spacing:0.1em;text-transform:uppercase;margin:0 0 10px;">
        Últimos 7 dias
    </p>""", unsafe_allow_html=True)

    # Calcular dots dos últimos 7 dias
    dias_7 = [sete_dias + timedelta(days=i) for i in range(7)]
    dots_7 = {}
    if not registos_db.empty and 'Técnico' in registos_db.columns:
        ru = registos_db[registos_db['Técnico'] == user_nome].copy()
        if not ru.empty:
            ru['Data_d']     = pd.to_datetime(ru['Data'], dayfirst=True, errors='coerce').dt.date
            ru['Horas_Total'] = pd.to_numeric(ru['Horas_Total'], errors='coerce').fillna(0)
            sp = {"4":6,"3":5,"2":4,"1":3,"0":2,"-1":1}
            for d in dias_7:
                rd = ru[ru['Data_d'] == d]
                if not rd.empty:
                    melhor = max(rd['Status'].tolist(),
                                 key=lambda s: sp.get(str(s), 0))
                    dots_7[d] = str(melhor)

    # Renderizar mini-calendário dos 7 dias
    dias_html = ""
    for d in dias_7:
        cor_dot  = _DOT_COLOR.get(dots_7.get(d, ''), '')
        dot_html = f'<div style="width:8px;height:8px;border-radius:50%;background:{cor_dot};margin:3px auto 0;"></div>' if cor_dot else '<div style="height:11px;"></div>'
        eh_hoje  = d == hoje
        num_col  = "#DC2626" if eh_hoje else "#CBD5E1"
        num_wt   = "900" if eh_hoje else "500"
        dias_abr = ['D','S','T','Q','Q','S','S']
        dl       = dias_abr[(d.weekday()+1)%7]
        fim_sem  = (d.weekday()+1)%7 in (0,6)
        letra_c  = "#475569" if fim_sem else "#64748B"

        dias_html += f"""
        <div style="flex:1;text-align:center;padding:6px 2px;">
            <p style="margin:0;font-size:0.62rem;font-weight:600;
                color:{letra_c};text-transform:uppercase;">{dl}</p>
            <p style="margin:3px 0 0;font-size:0.85rem;font-weight:{num_wt};
                color:{num_col};">{d.day}</p>
            {dot_html}
        </div>"""

    st.markdown(f"""
    <div style="background:#1E293B;border-radius:14px;padding:12px;
        border:1px solid #334155;">
        <div style="display:flex;gap:0;">
            {dias_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    # ── Lista dos últimos registos aprovados ──────────────────────────
    if not regs_ultimos7.empty:
        total_7 = regs_ultimos7['Horas_Total'].sum()
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;
            align-items:center;margin-bottom:10px;">
            <span style="color:#94A3B8;font-size:0.82rem;">
                Registos aprovados
            </span>
            <span style="color:#10B981;font-weight:800;font-size:0.88rem;">
                {fh(total_7)} total
            </span>
        </div>
        """, unsafe_allow_html=True)

        for _, r in regs_ultimos7.sort_values('Data_d', ascending=False).head(5).iterrows():
            try:
                data_str = r['Data_d'].strftime('%d/%m') \
                           if hasattr(r.get('Data_d'), 'strftime') \
                           else str(r.get('Data',''))[:5]
            except:
                data_str = str(r.get('Data',''))[:5]

            st.markdown(f"""
            <div style="background:#1E293B;border-radius:10px;padding:12px 14px;
                margin-bottom:6px;border-left:3px solid #10B981;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <p style="margin:0;font-weight:700;color:#F1F5F9;font-size:0.88rem;">
                            {r.get('Obra','')}
                        </p>
                        <p style="margin:2px 0 0;color:#64748B;font-size:0.75rem;">
                            {data_str} · {r.get('Frente','') or r.get('Turnos','')}
                        </p>
                    </div>
                    <span style="color:#10B981;font-weight:900;font-size:1rem;">
                        {fh(r.get('Horas_Total',0))}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div style="background:#1E293B;border-radius:14px;padding:40px 20px;
            text-align:center;border:1px dashed #334155;">
            <div style="font-size:2.5rem;margin-bottom:10px;opacity:0.3;">📋</div>
            <p style="color:#475569;font-size:0.88rem;margin:0;">
                Sem registos aprovados nos últimos 7 dias
            </p>
            <p style="color:#334155;font-size:0.78rem;margin:6px 0 0;">
                Clica em "Registar Ponto" para começar
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ── Alertas (PDFs / Preço Hora pendentes) ─────────────────────────
    try:
        uc = load_db("usuarios.csv",
                     ["Nome","PDFs_Validados","PrecoHoraStatus"], silent=True)
        m_ = uc[uc['Nome'] == user_nome]
        if not m_.empty:
            row = m_.iloc[0]
            if row.get('PDFs_Validados','Não') != 'Sim':
                st.warning("📄 Tens documentos obrigatórios por validar.")
            if row.get('PrecoHoraStatus','') == '':
                st.warning("💰 Tens o preço hora por aceitar.")
            elif row.get('PrecoHoraStatus','') == 'Recusado':
                st.error("❌ Preço hora recusado — contacta o admin.")
    except:
        pass

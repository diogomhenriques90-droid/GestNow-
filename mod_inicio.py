import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import fh, ICONS, load_db, inv, criar_notificacao

def render_inicio(*args):
    """Dashboard Inicial — Tipo App Mobile"""

    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    user_nome = st.session_state.get('user', 'Utilizador')
    user_tipo = st.session_state.get('tipo', 'Técnico')
    cargo     = st.session_state.get('cargo', 'Técnico')

    # ── Header ────────────────────────────────────────────────────────
    hora = datetime.now().hour
    saudacao = "Bom dia" if hora < 12 else "Boa tarde" if hora < 19 else "Boa noite"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E293B,#0F172A);
        padding:30px 20px;border-radius:20px;margin-bottom:30px;text-align:center;">
        <h1 style="margin:0;color:#F8FAFC;font-size:2rem;">{saudacao}, {user_nome} 👋</h1>
        <p style="margin:10px 0 0 0;color:#94A3B8;">Bem-vindo ao GESTNOW</p>
        <p style="margin:5px 0 0 0;color:#64748B;font-size:0.85rem;">{cargo} | {user_tipo}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Calcular estatísticas ─────────────────────────────────────────
    hoje       = date.today()
    inicio_mes = hoje.replace(day=1)
    sete_dias  = hoje - timedelta(days=7)

    horas_mes      = 0.0
    horas_pendentes= 0.0
    registos_7dias = pd.DataFrame()

    if not registos_db.empty:
        # registos_db['Data'] já é datetime após load_all()
        regs_user = registos_db[registos_db['Técnico'] == user_nome].copy()

        if not regs_user.empty:
            # Garantir que Data é datetime
            if not pd.api.types.is_datetime64_any_dtype(regs_user['Data']):
                regs_user['Data'] = pd.to_datetime(regs_user['Data'], dayfirst=True, errors='coerce')

            regs_user['Data_d'] = regs_user['Data'].dt.date

            # Horas aprovadas este mês
            regs_mes = regs_user[
                (regs_user['Data_d'] >= inicio_mes) &
                (regs_user['Status'] == '1')
            ]
            horas_mes = regs_mes['Horas_Total'].astype(float).sum()

            # Horas pendentes
            regs_pend = regs_user[regs_user['Status'] == '0']
            horas_pendentes = regs_pend['Horas_Total'].astype(float).sum()

            # Últimos 7 dias (aprovadas)
            registos_7dias = regs_user[
                (regs_user['Data_d'] >= sete_dias) &
                (regs_user['Status'] == '1')
            ].copy()

    # ── Cards de Resumo ───────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#DC2626,#B91C1C);
            padding:25px;border-radius:15px;text-align:center;
            box-shadow:0 4px 12px rgba(220,38,38,0.3);">
            <div style="font-size:2.5rem;margin-bottom:10px;">⏱️</div>
            <div style="color:#F8FAFC;font-size:0.9rem;margin-bottom:5px;">Horas deste mês</div>
            <div style="color:#FFFFFF;font-size:2rem;font-weight:bold;">{fh(horas_mes)}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        cor_pend = "#F59E0B" if horas_pendentes > 0 else "#10B981"
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{cor_pend},{cor_pend}CC);
            padding:25px;border-radius:15px;text-align:center;
            box-shadow:0 4px 12px {cor_pend}4D;">
            <div style="font-size:2.5rem;margin-bottom:10px;">📋</div>
            <div style="color:#F8FAFC;font-size:0.9rem;margin-bottom:5px;">Por validar</div>
            <div style="color:#FFFFFF;font-size:2rem;font-weight:bold;">{fh(horas_pendentes)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── KPIs adicionais ───────────────────────────────────────────────
    n_obras_ativas = len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0
    n_pedidos_pend = 0
    if not req_fer_db.empty and 'Solicitante' in req_fer_db.columns:
        n_pedidos_pend += len(req_fer_db[(req_fer_db['Solicitante'] == user_nome) & (req_fer_db['Status'] == 'Pendente')])
    if not req_epi_db.empty and 'Solicitante' in req_epi_db.columns:
        n_pedidos_pend += len(req_epi_db[(req_epi_db['Solicitante'] == user_nome) & (req_epi_db['Status'] == 'Pendente')])
    if not req_mat_db.empty and 'Solicitante' in req_mat_db.columns:
        n_pedidos_pend += len(req_mat_db[(req_mat_db['Solicitante'] == user_nome) & (req_mat_db['Status'] == 'Pendente')])

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("🏭 Obras Ativas",   n_obras_ativas)
    with c2: st.metric("📦 Pedidos Pend.",  n_pedidos_pend)
    with c3:
        n_regs_mes = 0
        if not registos_db.empty:
            regs_u = registos_db[registos_db['Técnico'] == user_nome]
            if not regs_u.empty:
                data_col = regs_u['Data']
                if not pd.api.types.is_datetime64_any_dtype(data_col):
                    data_col = pd.to_datetime(data_col, dayfirst=True, errors='coerce')
                n_regs_mes = len(regs_u[data_col.dt.date >= inicio_mes])
        st.metric("📋 Registos Mês", n_regs_mes)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── Navegação Rápida ──────────────────────────────────────────────
    st.markdown("### 📍 Navegação Rápida")

    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button(f"{ICONS['technician']} Registar Ponto",
                     use_container_width=True, type="primary", key="btn_nav_registar"):
            st.session_state.menu_selected = f"{ICONS['technician']} Obra"
            st.rerun()

    with col_nav2:
        if st.button(f"{ICONS['profile']} O Meu Perfil",
                     use_container_width=True, type="secondary", key="btn_nav_perfil"):
            st.session_state.menu_selected = f"{ICONS['profile']} Perfil"
            st.rerun()

    # Botão instrumentação (apenas se tiver acesso)
    tem_inst = (user_tipo in ['Chefe de Equipa','Admin','Gestor'] or
                cargo in ['Chefe de Equipa','Encarregado','Instrumentista'])
    if tem_inst:
        if st.button(f"{ICONS['instrumentation']} Instrumentação",
                     use_container_width=True, type="secondary", key="btn_nav_inst"):
            st.session_state.menu_selected = f"{ICONS['instrumentation']} Instrumentação"
            st.rerun()

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── Comunicados não lidos ─────────────────────────────────────────
    if not comuns_db.empty and not comuns_u_db.empty:
        # Comunicados ainda não lidos por este utilizador
        lidos_ids = comuns_u_db[comuns_u_db['Utilizador'] == user_nome]['ComunicadoID'].tolist() if 'Utilizador' in comuns_u_db.columns else []
        nao_lidos = comuns_db[~comuns_db['ID'].isin(lidos_ids)] if 'ID' in comuns_db.columns else pd.DataFrame()

        if not nao_lidos.empty:
            urgentes = nao_lidos[nao_lidos.get('Urgente','') == 'Sim'] if 'Urgente' in nao_lidos.columns else pd.DataFrame()
            n_urgentes = len(urgentes)

            if n_urgentes > 0:
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.15);border:2px solid #EF4444;
                    border-radius:12px;padding:15px;margin-bottom:15px;">
                    <strong style="color:#EF4444;">🔴 {n_urgentes} comunicado(s) urgente(s) não lido(s)!</strong>
                </div>""", unsafe_allow_html=True)
            elif len(nao_lidos) > 0:
                st.info(f"📣 Tens {len(nao_lidos)} comunicado(s) por ler.")
    elif not comuns_db.empty:
        # Sem tabela de lidos — mostrar os mais recentes
        pass

    # ── Últimos 7 dias ────────────────────────────────────────────────
    st.markdown("### 📅 Últimos 7 dias")

    if not registos_7dias.empty:
        total_7 = registos_7dias['Horas_Total'].astype(float).sum()
        st.markdown(f"**Total aprovado: {fh(total_7)}**")

        for _, reg in registos_7dias.sort_values('Data', ascending=False).iterrows():
            data_str = reg['Data'].strftime('%d/%m/%Y') if hasattr(reg['Data'], 'strftime') else str(reg.get('Data',''))
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05);padding:15px;border-radius:12px;
                margin-bottom:10px;border-left:4px solid #10B981;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="color:#F8FAFC;font-weight:600;font-size:1.05rem;">{reg.get('Obra','')}</div>
                        <div style="color:#94A3B8;font-size:0.85rem;margin-top:4px;">
                            {data_str} • {reg.get('Turnos','') if reg.get('Turnos') else ''}
                        </div>
                        <div style="color:#64748B;font-size:0.8rem;">{reg.get('Frente','')}</div>
                    </div>
                    <div style="color:#10B981;font-weight:bold;font-size:1.2rem;">
                        {fh(reg.get('Horas_Total',0))}
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.05);padding:40px;border-radius:15px;text-align:center;">
            <div style="font-size:3rem;margin-bottom:15px;">📋</div>
            <p style="color:#94A3B8;margin:0;">Sem registos aprovados nos últimos 7 dias</p>
            <p style="color:#64748B;font-size:0.85rem;margin:10px 0 0 0;">
                Clica em "Registar Ponto" para começar
            </p>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # ── Pedidos recentes ──────────────────────────────────────────────
    pedidos_recentes = []
    for db, tipo_ped, campo_desc in [
        (req_fer_db, "🔧 Ferramenta",  "Descricao"),
        (req_epi_db, "🦺 EPI",         "Item"),
        (req_mat_db, "📦 Material",     "Descricao"),
    ]:
        if not db.empty and 'Solicitante' in db.columns:
            meus = db[db['Solicitante'] == user_nome]
            if not meus.empty:
                for _, p in meus.tail(2).iterrows():
                    pedidos_recentes.append({
                        "tipo":    tipo_ped,
                        "desc":    p.get(campo_desc, 'N/A'),
                        "status":  p.get('Status', 'Pendente'),
                        "data":    p.get('Data', 'N/A')
                    })

    if pedidos_recentes:
        st.markdown("### 📦 Pedidos Recentes")
        for ped in pedidos_recentes[-4:]:
            cor = {"Pendente":"#F59E0B","Aprovado":"#10B981","Rejeitado":"#EF4444"}.get(ped['status'],"#6B7280")
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:10px;
                margin-bottom:8px;border-left:3px solid {cor};">
                <span style="color:#F8FAFC;">{ped['tipo']}: {str(ped['desc'])[:40]}</span>
                <span style="color:{cor};font-size:0.85rem;float:right;font-weight:bold;">
                    {ped['status']}
                </span>
            </div>""", unsafe_allow_html=True)

    # ── Aviso de PDFs / Preço Hora pendentes ─────────────────────────
    try:
        users_check = load_db("usuarios.csv", [
            "Nome", "PDFs_Validados", "PrecoHoraStatus"
        ], silent=True)
        match = users_check[users_check['Nome'] == user_nome]
        if not match.empty:
            row = match.iloc[0]
            if row.get('PDFs_Validados','Não') != 'Sim':
                st.warning("⚠️ Tens documentos obrigatórios por validar. Vai à Área Técnica para completar.")
            if row.get('PrecoHoraStatus','') == '':
                st.warning("⚠️ Tens o preço hora por validar. Vai à Área Técnica para aceitar ou recusar.")
            elif row.get('PrecoHoraStatus','') == 'Recusado':
                st.error("❌ O teu preço hora foi recusado. Contacta o admin.")
    except:
        pass

"""
GESTNOW v3 — mod_tecnico.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Interface do técnico e chefe de equipa.

Tabs (técnico): Pontos · Comunicados · Ferramentas · Material/EPI · Perfil/Segurança
Tabs (chefe):   + Folha de Ponto

Para adicionar uma tab nova → adicionar em st.tabs() e criar o bloco.
Para alterar lógica de BD → editar core.py.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from core import *


def render_tecnico(users, obras_db, frentes_db, registos_db, faturas_db,
                   docs_db, incs_db, sw_db, obs_db, equip_db,
                   diags_db, diags_u_db, folhas_db,
                   comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db):
    """Renderiza a interface do técnico / chefe de equipa."""
    # 12. TÉCNICO
    # ============================================================
    # --- Alerta de documentos a caducar ---
    if not docs_db.empty:
        meus_docs_alerta = docs_db[docs_db['Utilizador']==st.session_state.user]
        if not meus_docs_alerta.empty:
            hj_alerta=date.today()
            docs_problema=[]
            for _,d_ in meus_docs_alerta.iterrows():
                try:
                    vd_=pd.to_datetime(d_['Validade']).date()
                    if vd_ < hj_alerta or 0<=(vd_-hj_alerta).days<=30:
                        docs_problema.append(f"{d_['Tipo']}: {d_['Nome']} (val. {d_['Validade']})")
                except: pass
            if docs_problema and not st.session_state.get('doc_alerta_visto'):
                st.warning("⚠️ **Documentos a caducar** — Por favor verifique os seus documentos: " + " | ".join(docs_problema))
                c_conf, c_ver = st.columns(2)
                with c_conf:
                    if st.button("✓ Confirmar",use_container_width=True): st.session_state['doc_alerta_visto']=True; st.rerun()
                with c_ver:
                    if st.button("👤 Ver Perfil →",use_container_width=True): st.session_state['doc_alerta_visto']=True; st.session_state['ir_para_perfil']=True; st.rerun()
                st.stop()

    hj_dt=datetime.now()
    mt=registos_db[registos_db['Técnico']==st.session_state.user].copy() if not registos_db.empty else pd.DataFrame()
    if not mt.empty and 'Data' in mt.columns:
        mt['Data'] = pd.to_datetime(mt['Data'], errors='coerce')

    is_chefe = st.session_state.get('cargo','') in ['Chefe de Equipa','Encarregado','Supervisor']

    # Calcular badges de pendentes para mostrar nas tabs
    _n_com_tec = 0
    if not comuns_db.empty and not comuns_u_db.empty:
        hoje_tec=date.today()
        obra_atual_tec=""
        for _,_rc in comuns_db.iterrows():
            try:
                if pd.to_datetime(_rc.get('Validade','')).date()<hoje_tec: continue
            except: pass
            _tp=_rc.get('Tipo',''); _ds=_rc.get('Destino','')
            _rel=(_tp=="Todos os colaboradores" or
                  (_tp=="Apenas Chefes de Equipa" and is_chefe) or
                  (_tp=="Colaborador individual" and _ds==st.session_state.user))
            if not _rel: continue
            _lido=len(comuns_u_db[(comuns_u_db['ComunicadoID']==_rc.get('ID',''))&(comuns_u_db['Utilizador']==st.session_state.user)])>0
            if not _lido: _n_com_tec+=1
    _badge_com = f" ({_n_com_tec})" if _n_com_tec>0 else ""

    _n_req_tec = 0
    for _rdb in [req_fer_db, req_mat_db, req_epi_db]:
        if not _rdb.empty:
            _n_req_tec += len(_rdb[(_rdb['Solicitante']==st.session_state.user)&(_rdb['Status']=='Pendente')])
    _badge_req = f" ({_n_req_tec})" if _n_req_tec>0 else ""

    if is_chefe:
        tab1,tab2,tab3,tab4,tab5,tab6=st.tabs([
            "📅 Pontos","📋 Folha de Ponto",
            f"📢 Comunicados{_badge_com}",
            "🔧 Ferramentas","📦 Material / EPI","👤 Perfil / Segurança"
        ])
        tab_perfil=tab6; tab_seg=tab6
    else:
        tab1,tab3,tab4,tab5,tab6=st.tabs([
            "📅 Pontos",
            f"📢 Comunicados{_badge_com}",
            "🔧 Ferramentas","📦 Material / EPI","👤 Perfil / Segurança"
        ])
        tab2=None; tab_perfil=tab6; tab_seg=tab6

    with tab1:
        # ── CSS Tab Pontos ───────────────────────────────────────────
        st.markdown("""
        <style>
        /* ── Perfil header ── */
        .tec-profile-card {
            background: linear-gradient(135deg, #1A1A2E 0%, #C0392B 100%);
            border-radius: 20px; padding: 18px 22px;
            display: flex; align-items: center; gap: 14px;
            margin-bottom: 16px; color: white; position: relative; overflow: hidden;
        }
        .tec-profile-card::before {
            content:''; position:absolute; top:-30px; right:-30px;
            width:110px; height:110px; background:rgba(255,255,255,.06); border-radius:50%;
        }
        .tec-profile-card::after {
            content:''; position:absolute; bottom:-20px; right:55px;
            width:70px; height:70px; background:rgba(255,255,255,.04); border-radius:50%;
        }
        .tec-av-big {
            width:52px; height:52px; border-radius:50%;
            background:rgba(255,255,255,.2); border:2px solid rgba(255,255,255,.4);
            display:flex; align-items:center; justify-content:center;
            font-size:1.3rem; font-weight:800; flex-shrink:0; z-index:1;
        }
        .tec-prof-info { flex:1; z-index:1; }
        .tec-prof-name  { font-size:1.05rem; font-weight:800; line-height:1; }
        .tec-prof-cargo { font-size:.76rem; opacity:.75; margin-top:3px; }
        .tec-clock-wrap { text-align:right; z-index:1; }
        .tec-clock {
            font-family: 'DM Mono', 'Courier New', monospace;
            font-size:1.9rem; font-weight:500; letter-spacing:-1px; line-height:1;
        }
        .tec-date-sm { font-size:.68rem; opacity:.6; margin-top:2px; }
        /* ── Chips métricas ── */
        .pt-metrics { display:flex; gap:10px; margin-bottom:18px; }
        .pt-chip {
            flex:1; background:#fff; border:1px solid #E8ECF2;
            border-radius:12px; padding:11px 12px; text-align:center;
        }
        .pt-chip .pcv { font-size:1.25rem; font-weight:800; color:#1A1A2E; }
        .pt-chip .pcl { font-size:.66rem; color:#8A95A3; text-transform:uppercase; font-weight:600; letter-spacing:.4px; margin-top:2px; }
        .pt-chip .pcv.orange { color:#E67E22; }
        /* ── Calendário semanal ── */
        .week-bar {
            background:#fff; border:1px solid #E8ECF2;
            border-radius:14px; padding:12px 14px; margin-bottom:16px;
        }
        .week-bar-title { font-size:.68rem; font-weight:700; color:#8A95A3; text-transform:uppercase; letter-spacing:.6px; margin-bottom:8px; }
        /* ── Total do dia ── */
        .dia-total-wrap { text-align:center; padding:14px 0 10px; }
        .dia-total-h {
            font-family:'DM Mono','Courier New',monospace;
            font-size:2.8rem; font-weight:500; color:#1A1A2E; line-height:1;
        }
        .dia-total-sub { font-size:.82rem; color:#8A95A3; margin-top:5px; }
        /* ── Card de registo ── */
        .rp-card {
            background:#fff; border:1px solid #E8ECF2;
            border-radius:13px; padding:14px 16px; margin-bottom:9px;
            position:relative; overflow:hidden;
        }
        .rp-card::before {
            content:''; position:absolute; left:0; top:0; bottom:0;
            width:4px; border-radius:4px 0 0 4px;
        }
        .rp-card.pendente::before  { background:#E67E22; }
        .rp-card.aprovado::before  { background:#27AE60; }
        .rp-card.fechado::before   { background:#2980B9; }
        .rp-top { display:flex; justify-content:space-between; align-items:flex-start; }
        .rp-frente { font-weight:700; font-size:.93rem; color:#1A1A2E; }
        .rp-obra   { font-size:.76rem; color:#8A95A3; margin-top:2px; }
        .rp-horas  { font-family:'DM Mono','Courier New',monospace; font-size:1.25rem; font-weight:500; color:#1A1A2E; }
        .rp-pills  { display:flex; gap:8px; margin-top:9px; flex-wrap:wrap; }
        .rp-pill {
            display:inline-flex; align-items:center; gap:3px;
            background:#F4F6F8; border-radius:20px; padding:3px 9px;
            font-size:.73rem; font-weight:600; color:#4A5568;
        }
        .rp-pill.pendente { background:#FEF3E7; color:#C47A1B; }
        .rp-pill.aprovado { background:#EDFAF3; color:#1E8449; }
        .rp-pill.fechado  { background:#EAF4FB; color:#1A6FA0; }
        .rp-cod { display:inline-block; background:#EBF5FB; color:#2980B9; border-radius:5px; padding:1px 6px; font-size:.7rem; font-weight:700; margin-left:5px; }
        /* ── Form steps ── */
        .form-step-title {
            font-size:.68rem; font-weight:700; color:#8A95A3;
            text-transform:uppercase; letter-spacing:.6px; margin:14px 0 6px;
        }
        .obra-card-sel {
            background:#fff; border:2px solid #E8ECF2; border-radius:13px;
            padding:12px 14px; margin-bottom:6px; display:flex; align-items:center; gap:10px;
        }
        .obra-card-sel.selected { border-color:#C0392B; background:#FEF9F8; }
        /* ── Horas preview ── */
        .horas-preview {
            text-align:center; padding:10px; background:#F8FAFC;
            border-radius:11px; margin:6px 0;
        }
        /* ── Vazio ── */
        .pt-empty { text-align:center; padding:36px 16px; color:#8A95A3; }
        .pt-empty-ico { font-size:2.5rem; margin-bottom:10px; }
        .pt-empty-title { font-weight:700; color:#1A1A2E; font-size:.98rem; }
        .pt-empty-sub   { font-size:.82rem; margin-top:3px; }
        </style>
        """, unsafe_allow_html=True)

        hj = datetime.now().date()
        ds_ = st.session_state.data_consulta

        # ── Dados do utilizador ──────────────────────────────────────
        user_nome  = st.session_state.user
        user_cargo = st.session_state.get('cargo', 'Técnico')
        initials   = "".join([p[0].upper() for p in user_nome.split()[:2]])
        hora_atual = datetime.now().strftime('%H:%M')
        data_label = datetime.now().strftime('%A, %d %b').capitalize()

        # ── Calcular métricas ────────────────────────────────────────
        def _flt(x):
            try: return float(x)
            except: return 0.0
        h_hoje = mt[mt['Data'] == pd.Timestamp(hj)]['Horas_Total'].apply(_flt).sum() if not mt.empty else 0
        h_mes  = mt[mt['Data'].dt.month == hj_dt.month]['Horas_Total'].apply(_flt).sum() if not mt.empty else 0
        h_pend = mt[mt['Status'] == "0"]['Horas_Total'].apply(_flt).sum() if not mt.empty else 0

        # ── HEADER: avatar + relógio ─────────────────────────────────
        st.markdown(f"""
        <div class="tec-profile-card">
            <div class="tec-av-big">{initials}</div>
            <div class="tec-prof-info">
                <div class="tec-prof-name">{user_nome}</div>
                <div class="tec-prof-cargo">{user_cargo}</div>
            </div>
            <div class="tec-clock-wrap">
                <div class="tec-clock" id="pt-clock">{hora_atual}</div>
                <div class="tec-date-sm">{data_label}</div>
            </div>
        </div>
        <script>
        (function() {{
            function tick() {{
                var n=new Date();
                var s=String(n.getHours()).padStart(2,'0')+':'+String(n.getMinutes()).padStart(2,'0');
                var el=document.getElementById('pt-clock');
                if(el) el.textContent=s;
            }}
            tick(); setInterval(tick,1000);
        }})();
        </script>
        """, unsafe_allow_html=True)

        # ── Chips métricas ───────────────────────────────────────────
        st.markdown(f"""
        <div class="pt-metrics">
            <div class="pt-chip"><div class="pcv">{fh(h_hoje)}</div><div class="pcl">Hoje</div></div>
            <div class="pt-chip"><div class="pcv">{fh(h_mes)}</div><div class="pcl">Este mês</div></div>
            <div class="pt-chip"><div class="pcv orange">{fh(h_pend)}</div><div class="pcl">Por validar</div></div>
        </div>
        """, unsafe_allow_html=True)

        # ── Calendário semanal ───────────────────────────────────────
        inicio_sem = hj - timedelta(days=hj.weekday())
        dias_sem   = [inicio_sem + timedelta(days=i) for i in range(7)]
        nomes_pt   = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']
        dias_com_reg = set(mt['Data'].dt.date.unique()) if not mt.empty else set()

        st.markdown('<div class="week-bar"><div class="week-bar-title">📅 Semana</div>', unsafe_allow_html=True)
        cols_w = st.columns(7)
        for i, (dia, nome) in enumerate(zip(dias_sem, nomes_pt)):
            with cols_w[i]:
                dot    = "🟠" if dia in dias_com_reg else ""
                is_sel = (dia == ds_)
                lbl    = f"{nome} {dia.day}{' ' + dot if dot else ''}"
                if st.button(lbl, key=f"pt_w_{i}", use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state.data_consulta = dia
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Registos do dia selecionado ──────────────────────────────
        rd = mt[mt['Data'] == pd.Timestamp(ds_)] if not mt.empty else pd.DataFrame()
        ds_label = "Hoje" if ds_ == hj else ds_.strftime('%d de %B de %Y')

        if not rd.empty:
            th = rd['Horas_Total'].apply(_flt).sum()
            st.markdown(f"""
            <div class="dia-total-wrap">
                <div class="dia-total-h">{fh(th)}</div>
                <div class="dia-total-sub">⏱ Total em {ds_label}</div>
            </div>
            """, unsafe_allow_html=True)

            for _, row in rd.iterrows():
                st_txt, st_cls = sl(row['Status'])
                cod_ = ""
                if not obras_db.empty and row['Obra'] in obras_db['Obra'].values:
                    cod_ = obras_db[obras_db['Obra'] == row['Obra']]['Codigo'].values[0]
                hrs = _flt(row.get('Horas_Total', 0))
                turno_s = str(row.get('Turnos','—')) if pd.notna(row.get('Turnos')) else '—'

                if row['Status'] == "0":   css_c = "pendente"; pill_c = "pendente"
                elif row['Status'] == "1": css_c = "aprovado"; pill_c = "aprovado"
                else:                      css_c = "fechado";  pill_c = "fechado"

                rel_html = ""
                rel_val = row.get('Relatorio', '')
                if rel_val and str(rel_val).strip() and str(rel_val).strip() != 'nan':
                    rel_html = f"<div style='margin-top:9px;font-size:.8rem;color:#4A5568;padding:7px 10px;background:#F8FAFC;border-radius:7px;'>📝 {str(rel_val)[:120]}</div>"

                st.markdown(f"""
                <div class="rp-card {css_c}">
                    <div class="rp-top">
                        <div>
                            <div class="rp-frente">{row.get('Frente','—')}
                                {'<span class="rp-cod">'+cod_+'</span>' if cod_ else ''}
                            </div>
                            <div class="rp-obra">📍 {row['Obra']}</div>
                        </div>
                        <div class="rp-horas">{fh(hrs)}</div>
                    </div>
                    <div class="rp-pills">
                        <span class="rp-pill">🕐 {turno_s}</span>
                        <span class="rp-pill">🏷️ {row.get('TipoFrente','—')}</span>
                        <span class="rp-pill {pill_c}">{st_txt}</span>
                    </div>
                    {rel_html}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pt-empty">
                <div class="pt-empty-ico">📭</div>
                <div class="pt-empty-title">Sem registos em {ds_label}</div>
                <div class="pt-empty-sub">{'Regista o teu ponto abaixo ↓' if ds_ == hj else 'Seleciona outro dia ou regista hoje.'}</div>
            </div>
            """, unsafe_allow_html=True)

        # ── Formulário de novo registo (só hoje) ─────────────────────
        if ds_ == hj:
            st.markdown('<div style="text-align:center;color:#8A95A3;font-size:.8rem;margin:6px 0 14px;">＋ Adicionar período</div>', unsafe_allow_html=True)
            with st.expander("➕ Registar Ponto", expanded=rd.empty):
                if obras_db.empty:
                    st.warning("⚠️ Sem obras disponíveis. Contacta o administrador.")
                else:
                    oa = obras_db[obras_db['Ativa'].isin(['Ativa','ativa','Sim','sim','true','True','1'])]
                    if oa.empty: oa = obras_db

                    # Step 1 — Obra
                    st.markdown('<div class="form-step-title">1. Seleciona a obra</div>', unsafe_allow_html=True)
                    pesq = st.text_input("🔍 Pesquisar obra", placeholder="Nome ou código...",
                                         key="pt_pesq", label_visibility="collapsed")
                    if pesq.strip():
                        oa_f = oa[oa['Obra'].str.contains(pesq, case=False, na=False)]
                        if oa_f.empty: oa_f = oa
                    else:
                        oa_f = oa

                    ob_ = st.selectbox("Obra", oa_f['Obra'].tolist(), key="pt_obra",
                                       label_visibility="collapsed",
                                       format_func=lambda x: f"🏗️ {x}")

                    if ob_:
                        oi_ = oa[oa['Obra'] == ob_].iloc[0]
                        cod_obra = str(oi_.get('Codigo',''))
                        cli_obra = str(oi_.get('Cliente',''))
                        cod_badge = f'<span style="background:#EBF5FB;color:#2980B9;border-radius:5px;padding:1px 7px;font-size:.7rem;font-weight:700;">{cod_obra}</span>' if cod_obra and cod_obra != 'nan' else ''
                        cli_txt  = cli_obra if cli_obra and cli_obra != 'nan' else ''
                        st.markdown(f"""
                        <div class="obra-card-sel selected">
                            <div style="flex:1;">
                                <div style="font-weight:700;font-size:.93rem;color:#1A1A2E;">{ob_}</div>
                                <div style="font-size:.76rem;color:#C0392B;margin-top:2px;">{cod_badge} {cli_txt}</div>
                            </div>
                            <div style="color:#27AE60;font-size:1.1rem;">✓</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if oi_.get('DataFim'):
                            try:
                                df_fim = pd.to_datetime(oi_['DataFim']).date()
                                if df_fim < hj: st.warning(f"⚠️ Obra com prazo previsto em {df_fim.strftime('%d/%m/%Y')}!")
                            except: pass

                    # Step 2 — Frente
                    st.markdown('<div class="form-step-title">2. Frente de trabalho</div>', unsafe_allow_html=True)
                    fr_d = frentes_db[frentes_db['Obra'] == ob_]['Frente'].tolist() if not frentes_db.empty else []
                    fr_  = st.selectbox("Frente", fr_d if fr_d else ["Geral"], key="pt_frente",
                                        label_visibility="collapsed",
                                        format_func=lambda x: f"📋 {x}")
                    tf_  = st.selectbox("Tipo de Frente", TIPOS_FRENTE, key="pt_tipo",
                                        label_visibility="collapsed",
                                        format_func=lambda x: f"🏷️ {x}")

                    # Step 3 — Horário
                    st.markdown('<div class="form-step-title">3. Horário</div>', unsafe_allow_html=True)
                    col_h1, col_h2 = st.columns(2)
                    with col_h1:
                        st.markdown('<div style="font-size:.75rem;font-weight:700;color:#27AE60;margin-bottom:4px;">🟢 Entrada</div>', unsafe_allow_html=True)
                        h1 = st.time_input("Entrada",
                                           value=datetime.now().replace(hour=8,minute=0,second=0,microsecond=0).time(),
                                           key="pt_h1", label_visibility="collapsed")
                        st.markdown(f'<div style="text-align:center;font-family:monospace;font-size:1.7rem;font-weight:500;color:#27AE60;margin-top:-4px;">{h1.strftime("%H:%M")}</div>', unsafe_allow_html=True)
                    with col_h2:
                        st.markdown('<div style="font-size:.75rem;font-weight:700;color:#C0392B;margin-bottom:4px;">🔴 Saída</div>', unsafe_allow_html=True)
                        h2 = st.time_input("Saída",
                                           value=datetime.now().replace(hour=17,minute=0,second=0,microsecond=0).time(),
                                           key="pt_h2", label_visibility="collapsed")
                        st.markdown(f'<div style="text-align:center;font-family:monospace;font-size:1.7rem;font-weight:500;color:#C0392B;margin-top:-4px;">{h2.strftime("%H:%M")}</div>', unsafe_allow_html=True)

                    if h2 > h1:
                        hc = (datetime.combine(hj, h2) - datetime.combine(hj, h1)).seconds / 3600
                        cor_hc = "#27AE60" if hc <= 10 else ("#E67E22" if hc <= 14 else "#C0392B")
                        st.markdown(f"""
                        <div class="horas-preview">
                            <span style="font-family:monospace;font-size:1.4rem;font-weight:500;color:{cor_hc};">{fh(hc)}</span>
                            <span style="font-size:.78rem;color:#8A95A3;margin-left:6px;">de trabalho</span>
                        </div>
                        """, unsafe_allow_html=True)
                    elif h2.hour > 0 and h2 <= h1:
                        st.error("⚠️ A saída deve ser posterior à entrada.")

                    # Step 4 — Relatório
                    st.markdown('<div class="form-step-title">4. Relatório (opcional)</div>', unsafe_allow_html=True)
                    rel_ = st.text_area("Relatório", placeholder="📝 Descreve o trabalho realizado hoje...",
                                        height=90, key="pt_rel", label_visibility="collapsed")

                    # Submeter
                    col_s1, col_s2 = st.columns([3, 1])
                    with col_s1:
                        submeter = st.button("📍 Registar Ponto", use_container_width=True,
                                             type="primary", key="pt_submit")
                    with col_s2:
                        st.markdown(f'<div style="padding:7px;text-align:center;font-size:.68rem;color:#8A95A3;border:1px solid #E8ECF2;border-radius:9px;"><div style="font-weight:700;color:#1A1A2E;font-size:.85rem;">Hoje</div><div>{hj.strftime("%d/%m/%Y")}</div></div>', unsafe_allow_html=True)

                    if submeter:
                        if h2 <= h1:
                            st.error("⚠️ A saída deve ser posterior à entrada.")
                        else:
                            hc = (datetime.combine(hj, h2) - datetime.combine(hj, h1)).seconds / 3600
                            if hc > 16:
                                st.error("⚠️ Mais de 16 horas. Verifica os horários.")
                            else:
                                ts_ = f"{h1.strftime('%H:%M')}-{h2.strftime('%H:%M')}"
                                nr = pd.DataFrame([{
                                    "Data": hj.strftime('%d/%m/%Y'),
                                    "Técnico": st.session_state.user,
                                    "Obra": ob_, "Frente": fr_, "TipoFrente": tf_,
                                    "Turnos": ts_, "Relatorio": rel_.strip(),
                                    "Status": "0", "Horas_Total": round(hc, 2),
                                    "Localizacao_Checkin": "", "Localizacao_Checkout": ""
                                }])
                                if save_db(pd.concat([registos_db, nr], ignore_index=True), "registos.csv"):
                                    inv()
                                    st.success(f"✅ Ponto registado! {fh(hc)} em {ob_}")
                                    st.balloons()
                                    st.rerun()
        else:
            st.info(f"📅 Só podes registar pontos no próprio dia. Seleciona **hoje** no calendário para registar.")


    # ─────────────────────────────────────────────────
    # TAB FOLHA DE PONTO — só para Chefe de Equipa
    # ─────────────────────────────────────────────────
    if is_chefe and tab2 is not None:
      with tab2:
        st.markdown('<div class="section-title">📋 Folha de Registo de Ponto</div>', unsafe_allow_html=True)
        st.caption("Gera, assina e envia a folha de ponto da tua equipa para o cliente no momento.")
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Seleção de obra e período ──
        obras_ativas = obras_db[obras_db['Ativa'].isin(['Ativa','ativa','Sim','sim','true','True','1'])]['Obra'].tolist() if not obras_db.empty else []
        if not obras_ativas:
            st.warning("Sem obras ativas disponíveis.")
        else:
            c_ob, c_per = st.columns(2)
            with c_ob:
                obra_fp = st.selectbox("🏗️ Obra", obras_ativas, key="fp_obra")
            with c_per:
                periodo_fp = st.selectbox("📅 Período", ["Hoje","Ontem","Esta semana","Semana passada","Mês atual","Personalizado"], key="fp_periodo")

            hoje_fp = date.today()
            if periodo_fp == "Hoje":
                d_ini_fp = d_fim_fp = hoje_fp
                per_label = hoje_fp.strftime('%d/%m/%Y')
            elif periodo_fp == "Ontem":
                d_ini_fp = d_fim_fp = hoje_fp - timedelta(days=1)
                per_label = d_ini_fp.strftime('%d/%m/%Y')
            elif periodo_fp == "Esta semana":
                d_ini_fp = hoje_fp - timedelta(days=hoje_fp.weekday())
                d_fim_fp = hoje_fp
                per_label = f"{d_ini_fp.strftime('%d/%m')} – {d_fim_fp.strftime('%d/%m/%Y')}"
            elif periodo_fp == "Semana passada":
                d_ini_fp = hoje_fp - timedelta(days=hoje_fp.weekday()+7)
                d_fim_fp = d_ini_fp + timedelta(days=6)
                per_label = f"{d_ini_fp.strftime('%d/%m')} – {d_fim_fp.strftime('%d/%m/%Y')}"
            elif periodo_fp == "Mês atual":
                d_ini_fp = hoje_fp.replace(day=1)
                d_fim_fp = hoje_fp
                per_label = hoje_fp.strftime('%B %Y')
            else:
                ca_,cb_=st.columns(2)
                with ca_: d_ini_fp = st.date_input("De",value=hoje_fp,key="fp_ini")
                with cb_: d_fim_fp = st.date_input("Até",value=hoje_fp,key="fp_fim")
                per_label = f"{d_ini_fp.strftime('%d/%m')} – {d_fim_fp.strftime('%d/%m/%Y')}"

            # Registos da obra no período
            regs_fp = pd.DataFrame()
            if not registos_db.empty:
                regs_fp = registos_db[
                    (registos_db['Obra']==obra_fp) &
                    (registos_db['Data'].dt.date >= d_ini_fp) &
                    (registos_db['Data'].dt.date <= d_fim_fp)
                ].copy()

            if regs_fp.empty:
                st.info(f"Sem registos para **{obra_fp}** no período selecionado.")
            else:
                n_tec = regs_fp['Técnico'].nunique()
                total_h_fp = regs_fp['Horas_Total'].sum()
                c1f,c2f,c3f=st.columns(3)
                with c1f: render_metric("👷",n_tec,"Técnicos")
                with c2f: render_metric("⏱️",fh(total_h_fp),"Total Horas")
                with c3f: render_metric("📝",len(regs_fp),"Registos")
                st.markdown("<br>", unsafe_allow_html=True)

                # Código da obra
                cod_obra_fp=""
                if not obras_db.empty and obra_fp in obras_db['Obra'].values:
                    cod_obra_fp = obras_db[obras_db['Obra']==obra_fp].iloc[0].get('Codigo','')

                # ── Assinaturas digitais ──
                st.markdown("#### ✍️ Assinaturas")
                st.caption("Usa o rato ou o dedo para assinar na área abaixo.")

                sig_html = """
    <div style="display:flex;gap:1rem;flex-wrap:wrap;">
      <div style="flex:1;min-width:280px;">
    <div style="color:#7A8BA6;font-size:.8rem;font-weight:600;margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;">
      ✍️ Assinatura do Chefe de Equipa
    </div>
    <canvas id="sig-chefe" width="340" height="140"
      style="border:2px solid #E5EDFF;border-radius:12px;background:white;cursor:crosshair;touch-action:none;display:block;"></canvas>
    <button onclick="clearCanvas('sig-chefe')"
      style="margin-top:6px;padding:5px 14px;border:1px solid #E5EDFF;border-radius:8px;
      background:white;color:#7A8BA6;font-size:.8rem;cursor:pointer;">🗑️ Limpar</button>
      </div>
      <div style="flex:1;min-width:280px;">
    <div style="color:#7A8BA6;font-size:.8rem;font-weight:600;margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;">
      ✍️ Assinatura do Representante do Cliente
    </div>
    <canvas id="sig-cliente" width="340" height="140"
      style="border:2px solid #E5EDFF;border-radius:12px;background:white;cursor:crosshair;touch-action:none;display:block;"></canvas>
    <button onclick="clearCanvas('sig-cliente')"
      style="margin-top:6px;padding:5px 14px;border:1px solid #E5EDFF;border-radius:8px;
      background:white;color:#7A8BA6;font-size:.8rem;cursor:pointer;">🗑️ Limpar</button>
      </div>
    </div>
    <div style="margin-top:1rem;">
      <input id="nome-cliente-input" type="text" placeholder="Nome do representante do cliente (opcional)"
    style="width:100%;padding:10px 14px;border:1px solid #E5EDFF;border-radius:10px;
    font-size:.9rem;color:#374151;box-sizing:border-box;"/>
    </div>
    <div style="margin-top:.75rem;display:flex;gap:.75rem;flex-wrap:wrap;">
      <button id="btn-gerar" onclick="prepareSignatures()"
    style="flex:1;padding:.75rem;background:linear-gradient(135deg,#0A2463,#3E92CC);
    color:white;border:none;border-radius:12px;font-size:.95rem;font-weight:700;
    cursor:pointer;min-width:200px;box-shadow:0 4px 12px rgba(10,36,99,.25);">
    📄 Gerar Folha de Ponto com Assinaturas
      </button>
    </div>
    <input type="hidden" id="sig-chefe-data" />
    <input type="hidden" id="sig-cliente-data" />
    <input type="hidden" id="nome-cliente-data" />

    <script>
    // ── Setup canvas de assinatura ──
    function setupCanvas(id) {
      const canvas = document.getElementById(id);
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      let drawing = false;
      ctx.strokeStyle = '#1E3A8A';
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      function getPos(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    if (e.touches) {
      return {
        x: (e.touches[0].clientX - rect.left) * scaleX,
        y: (e.touches[0].clientY - rect.top) * scaleY
      };
    }
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
      }

      ['mousedown','touchstart'].forEach(ev =>
    canvas.addEventListener(ev, e => {
      e.preventDefault(); drawing = true;
      const p = getPos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y);
    }, {passive:false})
      );
      ['mousemove','touchmove'].forEach(ev =>
    canvas.addEventListener(ev, e => {
      e.preventDefault();
      if (!drawing) return;
      const p = getPos(e); ctx.lineTo(p.x, p.y); ctx.stroke();
    }, {passive:false})
      );
      ['mouseup','touchend','mouseleave'].forEach(ev =>
    canvas.addEventListener(ev, () => { drawing = false; })
      );
    }

    function clearCanvas(id) {
      const canvas = document.getElementById(id);
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    function isCanvasEmpty(id) {
      const canvas = document.getElementById(id);
      const ctx = canvas.getContext('2d');
      const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      return !data.some(v => v !== 0);
    }

    function prepareSignatures() {
      const chefeCanvas = document.getElementById('sig-chefe');
      const clienteCanvas = document.getElementById('sig-cliente');
      const nomeCliente = document.getElementById('nome-cliente-input').value;

      const sigChefeB64 = isCanvasEmpty('sig-chefe') ? '' :
    chefeCanvas.toDataURL('image/png').split(',')[1];
      const sigClienteB64 = isCanvasEmpty('sig-cliente') ? '' :
    clienteCanvas.toDataURL('image/png').split(',')[1];

      // Passar para os hidden inputs (Streamlit vai ler via query params)
      const params = new URLSearchParams(window.location.search);
      params.set('sig_chefe', sigChefeB64 ? '1' : '0');
      params.set('sig_cliente', sigClienteB64 ? '1' : '0');
      params.set('nome_cliente', encodeURIComponent(nomeCliente));
      params.set('gerar_folha', '1');
      params.set('sig_chefe_b64', sigChefeB64.substring(0, 100)); // preview apenas

      // Guardar em sessionStorage para acesso pelo Streamlit
      sessionStorage.setItem('gestnow_sig_chefe', sigChefeB64);
      sessionStorage.setItem('gestnow_sig_cliente', sigClienteB64);
      sessionStorage.setItem('gestnow_nome_cliente', nomeCliente);

      // Notificar Streamlit via componente customizado
      window.parent.postMessage({
    type: 'streamlit:setComponentValue',
    value: {
      sig_chefe: sigChefeB64,
      sig_cliente: sigClienteB64,
      nome_cliente: nomeCliente
    }
      }, '*');

      // Fallback: update URL para Streamlit detetar
      const url = window.location.href.split('?')[0];
      const newUrl = url + '?gerar_folha=1&nc=' + encodeURIComponent(nomeCliente);
      window.location.href = newUrl;
    }

    // Inicializar quando DOM estiver pronto
    setTimeout(() => { setupCanvas('sig-chefe'); setupCanvas('sig-cliente'); }, 300);
    </script>
    """
                st.components.v1.html(sig_html, height=480, scrolling=False)
                st.markdown("<br>", unsafe_allow_html=True)

                # Verificar se foi pedida geração de folha
                gerar_param = st.query_params.get("gerar_folha","")
                nome_cli_param = st.query_params.get("nc","")

                # Botão alternativo para gerar sem assinatura
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    gerar_sem_assin = st.button("📄 Gerar PDF (sem assinatura)",
                        use_container_width=True, key="fp_gerar_sem")
                with col_g2:
                    assin_opcional = st.text_input("Nome do cliente (para o PDF)",
                        placeholder="Nome do representante", key="fp_nome_cli")

                # ── GPS capture via JS ──────────────────────
                gps_html = """
    <div id="gps-status" style="color:#7A8BA6;font-size:.8rem;padding:.4rem 0;">
      📍 A obter localização GPS...
    </div>
    <input type="hidden" id="gps-coords" value="" />
    <script>
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
    pos => {
      const lat = pos.coords.latitude.toFixed(6);
      const lon = pos.coords.longitude.toFixed(6);
      const acc = Math.round(pos.coords.accuracy);
      document.getElementById('gps-coords').value = lat + ',' + lon;
      document.getElementById('gps-status').innerHTML =
        '📍 GPS obtido: <b>' + lat + ', ' + lon + '</b> (±' + acc + 'm)';
      document.getElementById('gps-status').style.color = '#059669';
      // Passar para Streamlit via URL param
      const url = new URL(window.location.href);
      url.searchParams.set('gps_chefe', lat + ',' + lon);
      window.history.replaceState({}, '', url);
    },
    err => {
      document.getElementById('gps-status').innerHTML =
        '⚠️ GPS não disponível (' + err.message + ')';
      document.getElementById('gps-status').style.color = '#D97706';
    },
    { enableHighAccuracy: true, timeout: 10000 }
      );
    } else {
      document.getElementById('gps-status').textContent = '⚠️ GPS não suportado neste dispositivo';
    }
    </script>"""
                st.components.v1.html(gps_html, height=50)
                gps_param = st.query_params.get("gps_chefe","")

                # Verificar configuração de assinatura obrigatória desta obra
                assin_obrig = False
                logo_obra   = ""
                if not obras_db.empty and obra_fp in obras_db['Obra'].values:
                    obra_row   = obras_db[obras_db['Obra']==obra_fp].iloc[0]
                    assin_obrig = str(obra_row.get('AssinaturaObrigatoria','')).lower() in ('sim','yes','true','1')
                    logo_obra   = obra_row.get('Logo_b64','')

                if assin_obrig:
                    st.warning("⚠️ Esta obra requer **assinatura do cliente** para validar a folha.")

                if gerar_sem_assin or gerar_param == "1":
                    nome_cli_final = assin_opcional or nome_cli_param
                    if assin_obrig and not nome_cli_final:
                        st.error("❌ Esta obra requer o nome do representante do cliente.")
                    else:
                        try:
                            import base64 as b64_mod
                            pdf_bytes, total_horas, folha_id = gerar_folha_ponto_pdf(
                                obra=obra_fp,
                                cod_obra=cod_obra_fp,
                                chefe=st.session_state.user,
                                periodo_label=per_label,
                                regs_obra=regs_fp,
                                users_df=users,
                                assin_chefe_b64="",
                                assin_cliente_b64="",
                                nome_cliente=nome_cli_final,
                                gps_chefe=gps_param,
                                logo_b64=logo_obra,
                                assin_cliente_obrigatoria=assin_obrig
                            )
                            pdf_b64 = b64_mod.b64encode(pdf_bytes).decode()
                            nova_folha = pd.DataFrame([{
                                "ID": folha_id,
                                "Data": hoje_fp.strftime('%d/%m/%Y'),
                                "Obra": obra_fp,
                                "CodObra": cod_obra_fp,
                                "ChefEquipa": st.session_state.user,
                                "Periodo": per_label,
                                "Tecnicos": "|".join(regs_fp['Técnico'].unique()),
                                "TotalHoras": round(total_horas, 2),
                                "AssinadoCliente": "Sim" if (assin_cliente_b64 and len(assin_cliente_b64)>20) else "Não",
                                "AssinaturaChefe": "",
                                "AssinaturaCliente": "",
                                "NomeCliente": nome_cli_final,
                                "GPS_Chefe": gps_param,
                                "DataCriacao": datetime.now().strftime('%d/%m/%Y %H:%M'),
                                "PDF_b64": pdf_b64
                            }])
                            save_db(pd.concat([folhas_db, nova_folha], ignore_index=True), "folhas_ponto.csv")
                            inv()
                            assin_cli_txt = " ✅ com assinatura do cliente" if (assin_cli_final := "") else ""
                            st.success(f"✅ Folha **{folha_id}** gerada — {fh(total_horas)} • {regs_fp['Técnico'].nunique()} técnico(s){' 📍 GPS incluído' if gps_param else ''}")
                            st.download_button(
                                label="⬇️ Descarregar Folha de Ponto PDF",
                                data=pdf_bytes,
                                file_name=f"FP_{obra_fp.replace(' ','_')}_{hoje_fp.strftime('%Y%m%d')}_{folha_id}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            if gerar_param == "1":
                                st.query_params.clear()
                        except Exception as e:
                            st.error(f"❌ Erro ao gerar PDF: {e}")

                # Histórico das folhas deste chefe
                st.markdown("<br>")
                st.markdown("#### 📁 Folhas Anteriores")
                minhas_folhas = folhas_db[folhas_db['ChefEquipa']==st.session_state.user] if not folhas_db.empty else pd.DataFrame()
                if not minhas_folhas.empty:
                    for _,f_ in minhas_folhas.sort_values('DataCriacao',ascending=False).head(20).iterrows():
                        assin_ic = "✅" if f_.get('AssinadoCliente','')=="Sim" else "⏳"
                        col_a, col_b = st.columns([4,1])
                        with col_a:
                            st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                                f"<span>{assin_ic} {f_.get('Obra','—')} — {f_.get('Periodo','—')}</span>"
                                f"<span class='turno-status {'status-aprovado' if f_.get('AssinadoCliente')=='Sim' else 'status-pendente'}'>"
                                f"{'Assinado' if f_.get('AssinadoCliente')=='Sim' else 'Pendente assinatura'}</span></div>"
                                f"<div style='color:#7A8BA6;font-size:.8rem;'>🆔 {f_.get('ID','—')} &nbsp;|&nbsp; "
                                f"⏱️ {f_.get('TotalHoras',0)}h &nbsp;|&nbsp; 👤 {f_.get('NomeCliente','—')} &nbsp;|&nbsp; "
                                f"📅 {f_.get('DataCriacao','—')}</div></div>",
                                unsafe_allow_html=True)
                        with col_b:
                            if f_.get('PDF_b64',''):
                                try:
                                    import base64 as b64_dl
                                    pdf_dl = b64_dl.b64decode(f_['PDF_b64'])
                                    st.download_button("⬇️",data=pdf_dl,
                                        file_name=f"folha_{f_.get('ID','x')}.pdf",
                                        mime="application/pdf",key=f"dl_{f_.get('ID','x')}")
                                except: pass
                else:
                    st.info("Ainda não geraste nenhuma folha.")

    # ── Comunicados ────────────────────────────────────
    with tab3:
        st.markdown('<div class="section-title">📢 Comunicados</div>', unsafe_allow_html=True)
        if _n_com_tec > 0:
            st.warning(f"📬 **{_n_com_tec}** comunicado(s) por confirmar.")
        if comuns_db.empty:
            st.info("Sem comunicados de momento.")
        else:
            hoje_tc=date.today()
            relevantes_tc=[]
            for _,row_tc in comuns_db.iterrows():
                try:
                    if pd.to_datetime(row_tc.get('Validade','')).date()<hoje_tc: continue
                except: pass
                tp_tc=row_tc.get('Tipo',''); ds_tc=row_tc.get('Destino','')
                if (tp_tc=="Todos os colaboradores" or
                    (tp_tc=="Apenas Chefes de Equipa" and is_chefe) or
                    (tp_tc=="Colaborador individual" and ds_tc==st.session_state.user)):
                    relevantes_tc.append(row_tc)
            if not relevantes_tc:
                st.info("✅ Sem comunicados pendentes.")
            else:
                for idx_tc,row_tc in enumerate(sorted(relevantes_tc,
                        key=lambda x: x.get('Urgente','')=="Sim", reverse=True)):
                    com_id_tc=row_tc.get('ID','')
                    ja_leu_tc=(not comuns_u_db.empty and
                               len(comuns_u_db[(comuns_u_db['ComunicadoID']==com_id_tc)&
                                              (comuns_u_db['Utilizador']==st.session_state.user)])>0)
                    urg_tc=row_tc.get('Urgente')=="Sim"
                    st.markdown(
                        f"<div class='turno-card' style='border-left:4px solid {'#DC2626' if urg_tc else '#E5EDFF'};background:{'#FEF2F2' if urg_tc else 'white'};'>"
                        f"<div class='turno-header'><span>{'🚨' if urg_tc else '✅' if ja_leu_tc else '📬'} <b>{row_tc.get('Titulo','—')}</b></span>"
                        f"<span class='turno-status {'status-fechado' if urg_tc else 'status-aprovado'}'>{'🚨 Urgente' if urg_tc else '✅ Lido' if ja_leu_tc else '📬 Por ler'}</span></div>"
                        f"<div style='color:#374151;margin:.4rem 0;line-height:1.5;'>{row_tc.get('Conteudo','')}</div>"
                        f"<div style='color:#7A8BA6;font-size:.78rem;'>📅 {row_tc.get('DataCriacao','—')} | 👤 {row_tc.get('Autor','—')}</div></div>",
                        unsafe_allow_html=True)
                    if not ja_leu_tc:
                        if st.button("✅ Confirmar leitura",key=f"com_ler_tec_{com_id_tc}_{idx_tc}",use_container_width=True):
                            nova_leit_tc=pd.DataFrame([{"ComunicadoID":com_id_tc,"Utilizador":st.session_state.user,
                                "DataLeitura":datetime.now().strftime('%d/%m/%Y %H:%M')}])
                            save_db(pd.concat([comuns_u_db,nova_leit_tc],ignore_index=True),"comunicados_lidos.csv")
                            inv(); st.success("✅ Leitura confirmada!"); st.rerun()

    # ── Ferramentas (chefe) ────────────────────────────
    with tab4:
        obras_ativas_tec=obras_db[obras_db['Ativa'].isin(['Ativa','ativa','Sim','sim','true','True','1'])]['Obra'].tolist() if not obras_db.empty else []
        st.markdown('<div class="section-title">🔧 Requisitar Ferramenta</div>', unsafe_allow_html=True)
        if not obras_ativas_tec:
            st.warning("Sem obras ativas disponíveis.")
        else:
            with st.form("f_req_fer_tec"):
                rfc1,rfc2=st.columns(2)
                with rfc1:
                    rf_obra=st.selectbox("Obra",obras_ativas_tec,key="rf_o")
                    rf_cat=st.selectbox("Categoria",["Ferramenta Elétrica","Ferramenta Manual","Equipamento de Medição","Equipamento de Elevação","Equipamento de Segurança","Máquina","Outro"],key="rf_c")
                    rf_desc=st.text_input("Descrição *",placeholder="Ex: Berbequim Bosch GSB 21-2RE")
                    rf_ref=st.text_input("Referência / Nº Série",placeholder="Opcional")
                with rfc2:
                    rf_qtd=st.number_input("Quantidade",min_value=1,value=1,key="rf_q")
                    rf_dnec=st.date_input("Data necessária",value=date.today()+timedelta(days=1),key="rf_dn")
                    rf_mot=st.text_area("Observação",height=100,key="rf_m")
                if st.form_submit_button("📤 Enviar Requisição",use_container_width=True):
                    if not rf_desc.strip(): st.error("Descrição obrigatória.")
                    else:
                        import uuid as _uuid_rf
                        nid_rf="RF"+_uuid_rf.uuid4().hex[:8].upper()
                        nova_rf=pd.DataFrame([{"ID":nid_rf,"Data":datetime.now().strftime('%d/%m/%Y'),
                            "Solicitante":st.session_state.user,"Obra":rf_obra,"Categoria":rf_cat,
                            "Descricao":rf_desc.strip(),"Referencia":rf_ref,"Quantidade":rf_qtd,
                            "DataNecessaria":str(rf_dnec),"Status":"Pendente","NotaAdmin":"","DataResposta":""}])
                        save_db(pd.concat([req_fer_db,nova_rf],ignore_index=True),"req_ferramentas.csv")
                        inv(); st.success(f"✅ Requisição {nid_rf} enviada!"); st.rerun()
            st.markdown("#### 📁 As Minhas Requisições")
            if not req_fer_db.empty:
                minhas_rf=req_fer_db[req_fer_db['Solicitante']==st.session_state.user].sort_values('Data',ascending=False)
                for _,row_rf in minhas_rf.head(15).iterrows():
                    st_ic_rf={"Pendente":"⏳","Aprovada":"✅","Rejeitada":"❌","Entregue":"📦"}.get(row_rf.get('Status',''),"⏳")
                    st_cls_rf={"Pendente":"status-pendente","Aprovada":"status-aprovado","Rejeitada":"status-fechado","Entregue":"status-aprovado"}.get(row_rf.get('Status',''),"")
                    st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                        f"<span>{st_ic_rf} <b>{row_rf.get('Descricao','—')}</b></span>"
                        f"<span class='turno-status {st_cls_rf}'>{row_rf.get('Status','—')}</span></div>"
                        f"<div style='color:#7A8BA6;font-size:.82rem;'>🏗️ {row_rf.get('Obra','—')} | "
                        f"🔢 {row_rf.get('Quantidade','—')} | 📅 {row_rf.get('DataNecessaria','—')} | 🆔 {row_rf.get('ID','—')}</div></div>",
                        unsafe_allow_html=True)
            else: st.info("Sem requisições.")

    # ── Material e EPI ─────────────────────────────────
    with tab5:
        obras_ativas_tec2=obras_db[obras_db['Ativa'].isin(['Ativa','ativa','Sim','sim','true','True','1'])]['Obra'].tolist() if not obras_db.empty else []
        st.markdown('<div class="section-title">📦 Material / Consumíveis / EPI</div>', unsafe_allow_html=True)
        sub_mat, sub_epi = st.tabs(["📦 Material e Consumíveis","🦺 Fardamento e EPI"])

        with sub_mat:
            if not obras_ativas_tec2:
                st.warning("Sem obras ativas disponíveis.")
            else:
                with st.form("f_req_mat_tec"):
                    rmc1,rmc2=st.columns(2)
                    with rmc1:
                        rm_obra=st.selectbox("Obra",obras_ativas_tec2,key="rm_o")
                        rm_cat=st.selectbox("Categoria",["Cabo / Fio","Tubagem","Fixações / Parafusaria","Consumíveis Elétricos","Consumíveis Mecânicos","Tintas / Revestimentos","Produtos Químicos","Material Civil","Outro"],key="rm_c")
                        rm_desc=st.text_input("Descrição *",placeholder="Ex: Cabo VVF 3x2.5mm²")
                        rm_ref=st.text_input("Referência",placeholder="Opcional")
                    with rmc2:
                        rm_qtd=st.number_input("Quantidade",min_value=1,value=1,key="rm_q")
                        rm_unid=st.selectbox("Unidade",["un","m","m²","m³","kg","L","cx","rolo","Outro"],key="rm_u")
                        rm_dnec=st.date_input("Data necessária",value=date.today()+timedelta(days=1),key="rm_dn")
                        rm_mot=st.text_area("Observação",height=80,key="rm_m")
                    if st.form_submit_button("📤 Enviar Requisição",use_container_width=True):
                        if not rm_desc.strip(): st.error("Descrição obrigatória.")
                        else:
                            import uuid as _uuid_rm
                            nid_rm="RM"+_uuid_rm.uuid4().hex[:8].upper()
                            nova_rm=pd.DataFrame([{"ID":nid_rm,"Data":datetime.now().strftime('%d/%m/%Y'),
                                "Solicitante":st.session_state.user,"Obra":rm_obra,"Categoria":rm_cat,
                                "Descricao":rm_desc.strip(),"Referencia":rm_ref,"Quantidade":rm_qtd,"Unidade":rm_unid,
                                "DataNecessaria":str(rm_dnec),"Status":"Pendente","NotaAdmin":"","DataResposta":""}])
                            save_db(pd.concat([req_mat_db,nova_rm],ignore_index=True),"req_materiais.csv")
                            inv(); st.success(f"✅ Requisição {nid_rm} enviada!"); st.rerun()
                st.markdown("#### 📁 As Minhas Requisições de Material")
                if not req_mat_db.empty:
                    minhas_rm=req_mat_db[req_mat_db['Solicitante']==st.session_state.user].sort_values('Data',ascending=False)
                    for _,row_rm in minhas_rm.head(10).iterrows():
                        st_ic_rm={"Pendente":"⏳","Aprovada":"✅","Rejeitada":"❌","Entregue":"📦"}.get(row_rm.get('Status',''),"⏳")
                        st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                            f"<span>{st_ic_rm} <b>{row_rm.get('Descricao','—')}</b></span>"
                            f"<span class='turno-status'>  {row_rm.get('Status','—')}</span></div>"
                            f"<div style='color:#7A8BA6;font-size:.82rem;'>🏗️ {row_rm.get('Obra','—')} | "
                            f"🔢 {row_rm.get('Quantidade','—')} {row_rm.get('Unidade','')} | {row_rm.get('Data','—')}</div></div>",
                            unsafe_allow_html=True)

        with sub_epi:
            with st.form("f_req_epi_tec"):
                re_obra=st.selectbox("Obra",obras_ativas_tec2 or ["—"],key="re_o")
                rec1,rec2=st.columns(2)
                with rec1:
                    re_tipo=st.selectbox("Tipo",["EPI","Fardamento"],key="re_t")
                    re_item=st.selectbox("Item",["Capacete","Luvas Corte","Luvas Eléctricas","Óculos Proteção","Viseira","Protetor Auricular","Arnês Segurança","Botins Biqueira Aço","Colete Refletor","Fato Trabalho","Impermeável","Máscara FFP2","Polo Manga Curta","Polo Manga Comprida","Sweatshirt","Casaco","Calças Trabalho","Outro"],key="re_i")
                with rec2:
                    re_tam=st.selectbox("Tamanho",["N/A","XS","S","M","L","XL","XXL","XXXL"],key="re_tam")
                    re_qtd=st.number_input("Quantidade",min_value=1,value=1,key="re_q")
                re_mot=st.text_area("Motivo (desgaste, extravio, novo...)",height=60,key="re_m")
                if st.form_submit_button("📤 Enviar Pedido",use_container_width=True):
                    import uuid as _uuid_re
                    nid_re="RE"+_uuid_re.uuid4().hex[:8].upper()
                    nova_re=pd.DataFrame([{"ID":nid_re,"Data":datetime.now().strftime('%d/%m/%Y'),
                        "Solicitante":st.session_state.user,"Obra":re_obra,"TipoReq":re_tipo,
                        "Item":re_item,"Tamanho":re_tam,"Quantidade":re_qtd,"Motivo":re_mot,
                        "Status":"Pendente","NotaAdmin":"","DataResposta":""}])
                    save_db(pd.concat([req_epi_db,nova_re],ignore_index=True),"req_epis.csv")
                    inv(); st.success(f"✅ Pedido {nid_re} enviado!"); st.rerun()
            st.markdown("#### 📁 Os Meus Pedidos EPI / Fardamento")
            if not req_epi_db.empty:
                minhas_re=req_epi_db[req_epi_db['Solicitante']==st.session_state.user].sort_values('Data',ascending=False)
                for _,row_re in minhas_re.head(10).iterrows():
                    st_ic_re={"Pendente":"⏳","Aprovada":"✅","Rejeitada":"❌","Entregue":"📦"}.get(row_re.get('Status',''),"⏳")
                    st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                        f"<span>{st_ic_re} <b>{row_re.get('Item','—')}</b> {row_re.get('TipoReq','')}</span>"
                        f"<span class='turno-status'>{row_re.get('Status','—')}</span></div>"
                        f"<div style='color:#7A8BA6;font-size:.82rem;'>🔢 {row_re.get('Quantidade','—')} | "
                        f"📏 {row_re.get('Tamanho','—')} | {row_re.get('Data','—')}</div></div>",
                        unsafe_allow_html=True)

    with tab_perfil:
        st.markdown('<div class="section-title">👤 O Meu Perfil</div>',unsafe_allow_html=True)
        mp=users[users['Nome']==st.session_state.user]
        if not mp.empty:
            p_=mp.iloc[0]
            ca_,ci_=st.columns([1,3])
            with ca_:
                foto_b64=p_.get('Foto','')
                if foto_b64 and foto_b64 not in ('','nan'):
                    st.markdown(f"<div style='text-align:center;'><img src='data:image/jpeg;base64,{foto_b64}' style='width:80px;height:80px;border-radius:50%;object-fit:cover;border:3px solid #3E92CC;'/></div>",unsafe_allow_html=True)
                else:
                    st.markdown("<div style='text-align:center;background:linear-gradient(135deg,#0A2463,#3E92CC);width:80px;height:80px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:2rem;color:white;margin:0 auto;'>👷</div>",unsafe_allow_html=True)
                # Upload de foto
                foto_file=st.file_uploader("📷",type=["jpg","jpeg","png"],key="foto_up",label_visibility="collapsed",help="Clica para alterar a foto de perfil")
                if foto_file:
                    import base64
                    fb64=base64.b64encode(foto_file.read()).decode()
                    idx_f=users[users['Nome']==st.session_state.user].index[0]
                    users.at[idx_f,'Foto']=fb64; save_db(users,"usuarios.csv"); inv(); st.success("✅"); st.rerun()
            with ci_: st.markdown(f"### {p_['Nome']}"); st.caption(f"{p_.get('Cargo','—')} • {p_.get('Tipo','—')}")
            st.markdown("<br>",unsafe_allow_html=True)
            for lbl,val in [("📧 Email",p_.get('Email','—')),("📱 Telefone",p_.get('Telefone','—')),("🎂 Data de Nascimento",p_.get('DataNasc','—')),("🌍 Nacionalidade",p_.get('Nacionalidade','—')),("🪪 CC / Passaporte",p_.get('CC','—')),("🧾 NIF",p_.get('NIF','—')),("🏛️ NISS",p_.get('NISS','—')),("🏠 Morada",p_.get('Morada','—'))]:
                if val and val not in ('—','','nan'): st.markdown(f"<div class='perfil-campo'><div class='perfil-label'>{lbl}</div><div class='perfil-valor'>{val}</div></div>",unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("#### 📄 Os Meus Documentos")
            md_=docs_db[docs_db['Utilizador']==st.session_state.user] if not docs_db.empty else pd.DataFrame()
            if not md_.empty:
                hj_d=date.today()
                for _,doc in md_.iterrows():
                    try: vd=pd.to_datetime(doc['Validade']).date(); exp=vd<hj_d; prx=0<=(vd-hj_d).days<=30
                    except: exp=False; prx=False
                    ic="🔴 Expirado" if exp else ("🟡 A expirar" if prx else "🟢 Válido")
                    cor="#991B1B" if exp else ("#8A6200" if prx else "#065F46")
                    st.markdown(f"<div class='perfil-campo'><div class='perfil-label'>{doc['Tipo']}</div><div class='perfil-valor'>{doc['Nome']} • Val: {doc['Validade']} <small style='color:{cor};'>{ic}</small></div></div>",unsafe_allow_html=True)
            else: st.info("Sem documentos. Contacta o administrador.")
            with st.expander("🔑 Alterar Password"):
                with st.form("mpw"):
                    pa=st.text_input("Password atual",type="password"); pn=st.text_input("Nova",type="password"); pc=st.text_input("Confirmar",type="password")
                    if st.form_submit_button("Alterar"):
                        if not cp(pa,p_['Password']): st.error("Password atual incorreta.")
                        elif pn!=pc: st.error("Não coincidem.")
                        else:
                            ok,msg=val_pw(pn)
                            if not ok: st.error(msg)
                            else:
                                i=users[users['Nome']==st.session_state.user].index[0]; users.at[i,'Password']=hp(pn)
                                save_db(users,"usuarios.csv"); inv(); st.success("✅ Password alterada!")
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("#### 📊 As Minhas Horas")
            if not mt.empty:
                hj2=datetime.now(); hs=mt[mt['Data']>=pd.Timestamp(hj2-timedelta(days=hj2.weekday()))]['Horas_Total'].sum()
                hm2=mt[mt['Data'].dt.month==hj2.month]['Horas_Total'].sum(); ha=mt[mt['Data'].dt.year==hj2.year]['Horas_Total'].sum()
                c1,c2,c3=st.columns(3)
                with c1: render_metric("📅",fh(hs),"Esta Semana")
                with c2: render_metric("🗓️",fh(hm2),"Este Mês")
                with c3: render_metric("📆",fh(ha),"Este Ano")
                hist=mt.sort_values('Data',ascending=False).head(30).copy()
                hist['Data']=hist['Data'].dt.strftime('%d/%m/%Y'); hist['Estado']=hist['Status'].map({"0":"⏳ Pendente","1":"✅ Aprovado","2":"🔵 Fechado"}); hist['Horas']=hist['Horas_Total'].apply(fh)
                cols_h=['Data','Obra','TipoFrente','Turnos','Horas','Estado']
                st.dataframe(hist[[c for c in cols_h if c in hist.columns]],use_container_width=True,hide_index=True)
        else: st.info("Perfil não encontrado.")

    with tab_seg:
        st.markdown('<div class="section-title">🛡️ Segurança</div>',unsafe_allow_html=True)
        # Menu de navegação rápida
        for icn,bg,titulo,sub in [("🥇","#FFF3CD","Regras de Ouro","As 10 regras essenciais"),("💬","#EEF2FF","Diálogos de Segurança","Listagem de diálogos atribuídos"),("🚶","#F0FDF4","Safety Walk","Registar inspeção de segurança"),("👁️","#FFF0F0","Observação","Registar observação de segurança"),("⚠️","#FEE2E2","Reportar Incidente","Registar situação de perigo")]:
            st.markdown(f"<div class='seg-card'><div class='seg-icon' style='background:{bg};'>{icn}</div><div><div class='seg-title'>{titulo}</div><div class='seg-sub'>{sub}</div></div><div style='margin-left:auto;color:#9CA3AF;'>›</div></div>",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)

        # 10 Regras de Ouro com texto completo
        st.markdown("#### 🥇 As 10 Regras de Ouro")
        for i,(icn,titulo,desc) in enumerate(REGRAS_OURO,1):
            st.markdown(f"""<div class='turno-card'>
            <div style='display:flex;align-items:flex-start;gap:1rem;'>
            <div style='font-size:1.8rem;font-weight:800;color:#C0392B;min-width:32px;'>{i}</div>
            <div><div style='font-weight:600;color:#1F2A44;margin-bottom:4px;'>{icn} {titulo}</div>
            <div style='color:#374151;font-size:.9rem;line-height:1.5;'>{desc}</div></div></div></div>""",unsafe_allow_html=True)

        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("#### 💬 Diálogos de Segurança Atribuídos")
        if not diags_u_db.empty:
            meus_dlg=diags_u_db[diags_u_db['Utilizador']==st.session_state.user]
            if not meus_dlg.empty:
                f_dlg=st.selectbox("Estado",["Todos","Por confirmar","Confirmados"],key="f_dlg_tec")
                for _,du in meus_dlg.iterrows():
                    confirmado=du.get('Confirmado','0')=="1"
                    if f_dlg=="Por confirmar" and confirmado: continue
                    if f_dlg=="Confirmados" and not confirmado: continue
                    dlg_info=diags_db[diags_db['Titulo']==du['Dialogo']] if not diags_db.empty else pd.DataFrame()
                    desc_dlg=dlg_info.iloc[0].get('Descricao','') if not dlg_info.empty else ''
                    tipo_dlg=dlg_info.iloc[0].get('Tipo','') if not dlg_info.empty else ''
                    est_ic="✅" if confirmado else "📬"
                    st.markdown(f"<div class='turno-card'><div class='turno-header'><span>{est_ic} {du.get('Dialogo','—')}</span><span class='turno-status {'status-aprovado' if confirmado else 'status-pendente'}'>{'Confirmado' if confirmado else 'Por confirmar'}</span></div><div style='color:#374151;font-size:.9rem;'>{tipo_dlg}</div><div style='color:#6B7280;font-size:.85rem;margin-top:4px;'>{desc_dlg[:120]}{'...' if len(desc_dlg)>120 else ''}</div></div>",unsafe_allow_html=True)
                    if not confirmado:
                        if st.button(f"✅ Confirmar leitura — {du.get('Dialogo','')[:30]}",key=f"conf_dlg_{_}",use_container_width=True):
                            idx_du=diags_u_db[(diags_u_db['Utilizador']==st.session_state.user)&(diags_u_db['Dialogo']==du['Dialogo'])].index[0]
                            diags_u_db.at[idx_du,'Confirmado']="1"; diags_u_db.at[idx_du,'DataLeitura']=datetime.now().strftime('%d/%m/%Y %H:%M')
                            save_db(diags_u_db,"dialogos_users.csv"); inv(); st.success("✅ Leitura confirmada!"); st.rerun()
            else: st.info("Sem diálogos atribuídos.")
        else: st.info("Sem diálogos atribuídos.")

        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("#### 🚶 Registar Safety Walk")
        with st.form("sw_tec"):
            c1,c2=st.columns(2)
            with c1:
                sw_ob_t=st.selectbox("Obra",obras_db['Obra'].tolist() if not obras_db.empty else ["—"],key="sw_ob_t")
                sw_cat_t=st.selectbox("Categoria",CATEGORIAS_SAFETY_WALK,key="sw_cat_t")
                sw_urg_t=st.selectbox("Urgência",["Baixa","Média","Alta"],key="sw_urg_t")
            with c2:
                sw_desc_t=st.text_area("O que observaste?",height=80,key="sw_desc_t")
                sw_ac_t=st.text_area("Ação corretiva sugerida",height=80,key="sw_ac_t")
            if st.form_submit_button("📨 Submeter Safety Walk",use_container_width=True):
                if sw_desc_t.strip():
                    nsw_t=pd.DataFrame([{"Data":datetime.now().strftime('%d/%m/%Y'),"Utilizador":st.session_state.user,"Obra":sw_ob_t,"Categoria":sw_cat_t,"Descricao":sw_desc_t,"AcaoCorretiva":sw_ac_t,"Status":"Aberta","Urgencia":sw_urg_t}])
                    save_db(pd.concat([sw_db,nsw_t],ignore_index=True),"safety_walks.csv"); inv(); st.success("✅ Safety Walk submetida!"); st.rerun()
                else: st.error("Descreve o que observaste.")

        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("#### ⚠️ Reportar Situação de Perigo")
        with st.form("it_"):
            oi2=st.selectbox("Obra",obras_db['Obra'].tolist() if not obras_db.empty else ["—"]); ti2=st.selectbox("Tipo",["Quase-acidente","Situação insegura","Dano material","Outro"])
            di2=st.text_area("Descrição",placeholder="Quanto mais detalhe melhor..."); gi2=st.selectbox("Gravidade",["Baixa","Média","Alta"])
            if st.form_submit_button("📨 Enviar Reporte",use_container_width=True):
                if di2.strip():
                    ni=pd.DataFrame([{"Data":datetime.now().strftime('%d/%m/%Y'),"Utilizador":st.session_state.user,"Obra":oi2,"Tipo":ti2,"Descricao":di2,"Gravidade":gi2,"Status":"Aberto"}])
                    save_db(pd.concat([incs_db,ni],ignore_index=True),"incidentes.csv"); inv(); st.success("✅ Reporte enviado!"); st.rerun()

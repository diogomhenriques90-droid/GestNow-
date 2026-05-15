"""
GESTNOW v3 — mod_chefe.py
Módulo do Chefe de Equipa / Gestor
"""
import streamlit as st
import pandas as pd
import uuid, secrets, base64, io, json
from datetime import datetime, timedelta, date
from streamlit_drawable_canvas import st_canvas
import time

from core import (
    save_db, inv, fh, sl, load_db, canvas_to_b64,
    ICONS, COLORS, TIPOS_FRENTE, REGRAS_OURO,
    log_audit, criar_notificacao, process_and_compress_image
)
from translations import t


def render_chefe(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    user_nome  = st.session_state.get('user', '')
    user_tipo  = st.session_state.get('tipo', '')
    cargo_user = st.session_state.get('cargo', '')

    st.markdown(f"""
    <div style="text-align:center;padding:25px 20px;
        background:linear-gradient(135deg,#1E293B,#0F172A);
        border-radius:20px;margin-bottom:25px;
        border:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:2.5rem;margin-bottom:8px;">👷</div>
        <div style="font-size:1.6rem;font-weight:800;color:#F8FAFC;">{user_nome}</div>
        <div style="font-size:0.95rem;color:#94A3B8;">{cargo_user} | {user_tipo}</div>
    </div>
    """, unsafe_allow_html=True)

    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    obras_chefe = []
    if not inst_acessos_db.empty and 'Utilizador' in inst_acessos_db.columns:
        obras_chefe = inst_acessos_db[inst_acessos_db['Utilizador'] == user_nome]['Obra'].tolist()

    regs_equipa = pd.DataFrame()
    if not registos_db.empty:
        if obras_chefe:
            regs_equipa = registos_db[registos_db['Obra'].isin(obras_chefe)]
        else:
            regs_equipa = registos_db.copy()

    pendentes_horas = len(regs_equipa[regs_equipa['Status'] == '0']) if not regs_equipa.empty else 0
    horas_mes = 0
    if not regs_equipa.empty:
        regs_mes = regs_equipa[
            pd.to_datetime(regs_equipa['Data'], dayfirst=True, errors='coerce').dt.date >= inicio_mes
        ]
        horas_mes = regs_mes['Horas_Total'].astype(float).sum()

    num_tecnicos = len(regs_equipa['Técnico'].unique()) if not regs_equipa.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("👷 Técnicos", num_tecnicos)
    with c2: st.metric("⏱️ Horas Mês", f"{horas_mes:.0f}h")
    with c3: st.metric("⏳ Pendentes", pendentes_horas)
    with c4: st.metric("🏭 Obras", len(obras_chefe) or (len(obras_db) if not obras_db.empty else 0))

    st.divider()

    tabs = st.tabs([
        "👥 Equipa", "✅ Validar Horas", "📈 Meu Ponto",
        "📊 Folha de Ponto", "🛡️ HSE", "📦 Pedidos"
    ])

    # ── TAB 0: EQUIPA ────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### 👷 Visão Geral da Equipa")
        if not regs_equipa.empty:
            resumo = regs_equipa.groupby('Técnico').agg(
                Horas=('Horas_Total', lambda x: x.astype(float).sum()),
                Registos=('Técnico', 'count'),
                Pendentes=('Status', lambda x: (x == '0').sum()),
                Aprovados=('Status', lambda x: (x == '1').sum())
            ).reset_index()
            for _, row in resumo.iterrows():
                cor = "#10B981" if row['Pendentes'] == 0 else "#F59E0B"
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05);padding:15px;
                    border-radius:12px;margin-bottom:10px;border-left:4px solid {cor};">
                    <div style="display:flex;justify-content:space-between;">
                        <div>
                            <strong style="color:#F8FAFC;">👤 {row['Técnico']}</strong>
                            <div style="color:#94A3B8;font-size:0.85rem;">{row['Registos']} registos | {fh(row['Horas'])} totais</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:#10B981;font-size:0.85rem;">✅ {row['Aprovados']}</div>
                            <div style="color:#F59E0B;font-size:0.85rem;">⏳ {row['Pendentes']}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📋 Sem dados de equipa.")

        st.divider()
        st.markdown("### 📣 Comunicado à Equipa")
        with st.form("form_comunicado_chefe"):
            titulo_com   = st.text_input("Título", key="com_ch_titulo")
            conteudo_com = st.text_area("Mensagem", key="com_ch_msg")
            urgente      = st.checkbox("Urgente", key="com_ch_urg")
            if st.form_submit_button("📣 Enviar", use_container_width=True, type="primary"):
                if titulo_com and conteudo_com:
                    novo_com = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8].upper(), "Titulo": titulo_com,
                        "Conteudo": conteudo_com, "Tipo": "Chefe", "Destino": "Equipa",
                        "Urgente": "Sim" if urgente else "Não",
                        "Validade": (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
                    }])
                    updated = pd.concat([comuns_db, novo_com], ignore_index=True) if not comuns_db.empty else novo_com
                    save_db(updated, "comunicados.csv")
                    inv()
                    st.success("✅ Comunicado enviado!")
                    st.rerun()

    # ── TAB 1: VALIDAR HORAS ────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### ✅ Validação de Horas da Equipa")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            # Fix Data
            regs_eq_fmt = pd.DataFrame()
            if not regs_equipa.empty:
                regs_eq_fmt = regs_equipa.copy()
                if pd.api.types.is_datetime64_any_dtype(regs_eq_fmt['Data']):
                    regs_eq_fmt['Data'] = regs_eq_fmt['Data'].dt.strftime('%d/%m/%Y').fillna('—')
                else:
                    regs_eq_fmt['Data'] = regs_eq_fmt['Data'].astype(str).replace({'NaT':'—','None':'—'})
                regs_eq_fmt['Horas_Total'] = pd.to_numeric(
                    regs_eq_fmt['Horas_Total'], errors='coerce').fillna(0)

            df_pend = regs_eq_fmt[regs_eq_fmt['Status'] == '0'] if not regs_eq_fmt.empty else pd.DataFrame()

            if not df_pend.empty:
                # ── Validar/Rejeitar em massa ─────────────────────
                col_vm, col_rm = st.columns(2)
                with col_vm:
                    if st.button("🟢 Validar Todos", key="ch_val_todos",
                                  type="primary", use_container_width=True):
                        for tecnico in df_pend['Técnico'].unique():
                            registos_db.loc[
                                (registos_db['Técnico'] == tecnico) &
                                (registos_db['Status']  == '0'), 'Status'
                            ] = '1'
                            criar_notificacao(destinatario=tecnico,
                                titulo="🟢 Horas Validadas",
                                mensagem=f"As tuas horas foram validadas pelo chefe {user_nome}.",
                                tipo="success", acao_url="/")
                        save_db(registos_db, "registos.csv")
                        inv(); st.success("✅ Todos validados!"); st.rerun()
                with col_rm:
                    if st.button("❌ Rejeitar Todos", key="ch_rej_todos",
                                  use_container_width=True):
                        for tecnico in df_pend['Técnico'].unique():
                            registos_db.loc[
                                (registos_db['Técnico'] == tecnico) &
                                (registos_db['Status']  == '0'), 'Status'
                            ] = '-1'
                            criar_notificacao(destinatario=tecnico,
                                titulo="❌ Horas Rejeitadas",
                                mensagem=f"As tuas horas foram rejeitadas. Contacta {user_nome}.",
                                tipo="error", acao_url="/")
                        save_db(registos_db, "registos.csv")
                        inv(); st.error("❌ Todos rejeitados."); st.rerun()

                st.markdown("---")

                # ── Por técnico com validação individual ──────────
                for tecnico in df_pend['Técnico'].unique():
                    regs_t    = df_pend[df_pend['Técnico'] == tecnico]
                    total_h_t = regs_t['Horas_Total'].sum()

                    with st.expander(
                        f"👤 {tecnico} — {fh(total_h_t)} ({len(regs_t)} registos)",
                        expanded=True
                    ):
                        # Validar/Rejeitar este técnico
                        col_vt, col_rt = st.columns(2)
                        with col_vt:
                            if st.button(f"🟢 Validar {tecnico}",
                                          key=f"apr_{tecnico}",
                                          use_container_width=True, type="primary"):
                                registos_db.loc[
                                    (registos_db['Técnico'] == tecnico) &
                                    (registos_db['Status']  == '0'), 'Status'
                                ] = '1'
                                save_db(registos_db, "registos.csv")
                                criar_notificacao(destinatario=tecnico,
                                    titulo="🟢 Horas Validadas",
                                    mensagem=f"As tuas horas foram validadas pelo chefe {user_nome}.",
                                    tipo="success", acao_url="/")
                                inv(); st.success("✅"); st.rerun()
                        with col_rt:
                            if st.button(f"❌ Rejeitar {tecnico}",
                                          key=f"rej_{tecnico}",
                                          use_container_width=True, type="secondary"):
                                registos_db.loc[
                                    (registos_db['Técnico'] == tecnico) &
                                    (registos_db['Status']  == '0'), 'Status'
                                ] = '-1'
                                save_db(registos_db, "registos.csv")
                                criar_notificacao(destinatario=tecnico,
                                    titulo="❌ Horas Rejeitadas",
                                    mensagem=f"As tuas horas foram rejeitadas. Contacta {user_nome}.",
                                    tipo="error", acao_url="/")
                                inv(); st.error("❌"); st.rerun()

                        st.markdown("---")

                        # Linha a linha
                        for _, reg in regs_t.iterrows():
                            reg_id = reg.get('ID','')
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
                                              use_container_width=True, help="Validar"):
                                    registos_db.loc[registos_db['ID'] == reg_id, 'Status'] = '1'
                                    save_db(registos_db, "registos.csv")
                                    criar_notificacao(destinatario=tecnico,
                                        titulo="🟢 Horas Validadas",
                                        mensagem=f"{fh(reg.get('Horas_Total',0))} em {reg.get('Obra','')} validadas.",
                                        tipo="success", acao_url="/")
                                    inv(); st.rerun()
                            with col_r:
                                if st.button("❌", key=f"rej_ind_{reg_id}",
                                              use_container_width=True, help="Rejeitar"):
                                    registos_db.loc[registos_db['ID'] == reg_id, 'Status'] = '-1'
                                    save_db(registos_db, "registos.csv")
                                    criar_notificacao(destinatario=tecnico,
                                        titulo="❌ Horas Rejeitadas",
                                        mensagem=f"{fh(reg.get('Horas_Total',0))} rejeitadas.",
                                        tipo="error", acao_url="/")
                                    inv(); st.rerun()
            else:
                st.success("✅ Sem horas pendentes!")

        with sub_h:
            hist = regs_equipa[regs_equipa['Status'].isin(['1','2','3','-1'])] \
                   if not regs_equipa.empty else pd.DataFrame()
            if not hist.empty:
                hist = hist.copy()
                if pd.api.types.is_datetime64_any_dtype(hist['Data']):
                    hist['Data'] = hist['Data'].dt.strftime('%d/%m/%Y').fillna('—')
                hist['Estado'] = hist['Status'].map({
                    "1":"🟢 Validado","2":"🔵 Faturação",
                    "3":"⚫ Processado","-1":"❌ Rejeitado"
                })
                cols_show = [c for c in ['Data','Técnico','Obra','Horas_Total','Estado']
                             if c in hist.columns]
                st.dataframe(hist[cols_show], use_container_width=True, hide_index=True)
            else:
                st.info("📋 Sem histórico.")  
                   
    # ── TAB 2: MEU PONTO ────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 📈 Registo de Ponto")
        hoje_d = date.today()
        if 'data_consulta_chefe' not in st.session_state:
            st.session_state.data_consulta_chefe = hoje_d

        inicio_sem = hoje_d - timedelta(days=hoje_d.weekday())
        dias_sem   = [inicio_sem + timedelta(days=i) for i in range(14)]
        cols_cal   = st.columns(len(dias_sem))
        for i, d in enumerate(dias_sem):
            with cols_cal[i]:
                sel = d == st.session_state.data_consulta_chefe
                if st.button(f"{d.strftime('%a')[:3]}\n{d.day}", key=f"ch_date_{d}", use_container_width=True,
                             type="primary" if sel else "secondary"):
                    st.session_state.data_consulta_chefe = d
                    st.rerun()

        if 'periodos_chefe' not in st.session_state:
            st.session_state.periodos_chefe = [{"entrada": "08:00", "saida": "17:00"}]
        if st.button("➕ Adicionar Período", key="add_p_ch", type="secondary"):
            st.session_state.periodos_chefe.append({"entrada": "13:00", "saida": "17:00"})
            st.rerun()

        with st.form("form_ponto_chefe"):
            obras_l = obras_db['Obra'].unique().tolist() if not obras_db.empty else ["Geral"]
            c1, c2 = st.columns(2)
            with c1: obra   = st.selectbox("Obra", obras_l, key="ch_obra")
            with c2: frente = st.selectbox("Frente", TIPOS_FRENTE, key="ch_frente")
            total_h = 0
            for idx, periodo in enumerate(st.session_state.periodos_chefe):
                st.markdown(f"**Período {idx+1}**")
                ce, cs = st.columns(2)
                with ce: entrada = st.time_input(f"Entrada {idx+1}", value=datetime.strptime(periodo["entrada"],"%H:%M").time(), key=f"ch_p{idx}_e")
                with cs: saida   = st.time_input(f"Saída {idx+1}",   value=datetime.strptime(periodo["saida"],  "%H:%M").time(), key=f"ch_p{idx}_s")
                delta = round(max((datetime.combine(date.today(),saida)-datetime.combine(date.today(),entrada)).seconds/3600,0),2)
                total_h += delta
            relat = st.text_area("Relatório", key="ch_relat")
            if st.form_submit_button("💾 Gravar Ponto", use_container_width=True, type="primary"):
                if total_h <= 0:
                    st.error("⚠️ Regista pelo menos um período válido.")
                else:
                    for idx, _ in enumerate(st.session_state.periodos_chefe):
                        entrada_v = st.session_state.get(f"ch_p{idx}_e")
                        saida_v   = st.session_state.get(f"ch_p{idx}_s")
                        if entrada_v and saida_v:
                            dh = round(max((datetime.combine(date.today(),saida_v)-datetime.combine(date.today(),entrada_v)).seconds/3600,0),2)
                            if dh > 0:
                                new_r = pd.DataFrame([{
                                    "ID": str(uuid.uuid4())[:8].upper(),
                                    "Data": st.session_state.data_consulta_chefe.strftime("%d/%m/%Y"),
                                    "Técnico": user_nome, "Obra": obra, "Frente": frente,
                                    "Turnos": f"{entrada_v.strftime('%H:%M')}-{saida_v.strftime('%H:%M')}",
                                    "Horas_Total": dh, "Relatorio": relat,
                                    "Status": "0", "Periodo": idx+1
                                }])
                                updated = pd.concat([registos_db, new_r], ignore_index=True) if not registos_db.empty else new_r
                                save_db(updated, "registos.csv")
                    st.session_state.periodos_chefe = [{"entrada":"08:00","saida":"17:00"}]
                    inv()
                    st.success(f"✅ Ponto registado! ({total_h:.1f}h)")
                    st.rerun()

        # Cards do dia
        st.markdown(f"### Registos de {st.session_state.data_consulta_chefe.strftime('%d/%m/%Y')}")
        if not registos_db.empty:
            meus = registos_db[registos_db['Técnico'] == user_nome]
            dia  = meus[pd.to_datetime(meus['Data'], dayfirst=True, errors='coerce').dt.date == st.session_state.data_consulta_chefe]
            if dia.empty:
                st.caption("ℹ️ Sem registos para este dia.")
            else:
                for _, r in dia.iterrows():
                    info = sl(r.get('Status','0'))
                    cor  = info[3]
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.05);padding:15px;
                        border-radius:12px;margin-bottom:10px;border-left:4px solid {cor};">
                        <b>{r.get('Obra','')}</b> | {r.get('Turnos','')} (<b>{fh(r.get('Horas_Total',0))}h</b>)<br>
                        <small style="color:{cor};">{info[0]}</small>
                    </div>
                    """, unsafe_allow_html=True)

    # ── TAB 3: FOLHA DE PONTO ───────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📊 Folha de Ponto & Upload Físico")

        obras_l_fp = obras_db['Obra'].unique().tolist() if not obras_db.empty else ["Sem Obras"]
        obra_fp    = st.selectbox("Obra", obras_l_fp, key="fp_ch_obra")
        ini_s      = hoje - timedelta(days=hoje.weekday())
        c1, c2     = st.columns(2)
        with c1: sem_ini = st.date_input("Início da Semana", value=ini_s, key="fp_ch_ini")
        with c2: sem_fim = st.date_input("Fim da Semana", value=ini_s+timedelta(days=6), key="fp_ch_fim")

        regs_fp = pd.DataFrame()
        if not registos_db.empty:
            regs_fp = registos_db[
                (registos_db['Obra'] == obra_fp) &
                (pd.to_datetime(registos_db['Data'],dayfirst=True,errors='coerce').dt.date >= sem_ini) &
                (pd.to_datetime(registos_db['Data'],dayfirst=True,errors='coerce').dt.date <= sem_fim)
            ]

        if not regs_fp.empty:
            st.markdown(f"#### Registos na App — {sem_ini.strftime('%d/%m')} a {sem_fim.strftime('%d/%m/%Y')}")
            for tec in regs_fp['Técnico'].unique():
                rt  = regs_fp[regs_fp['Técnico'] == tec]
                tot = rt['Horas_Total'].astype(float).sum()
                st.markdown(
                    f"<div style='background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);"
                    f"border-radius:10px;padding:12px;margin-bottom:8px;'>"
                    f"<b>👤 {tec}</b> — {len(rt)} dia(s) | <b>{tot:.1f}h</b>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")
        st.markdown("### 📷 Upload da Folha de Ponto Física")
        st.info(
            "Tira uma foto clara à folha de ponto assinada e faz upload. "
            "O sistema vai ler automaticamente os nomes e horas com IA."
        )

        foto_folha = st.file_uploader(
            "📷 Foto da folha de ponto (JPG, PNG ou PDF)",
            type=["jpg","jpeg","png","pdf"],
            key="fp_foto_upload"
        )

        if foto_folha:
            # Mostrar preview se for imagem
            if foto_folha.type in ["image/jpeg","image/png","image/jpg"]:
                st.image(foto_folha, caption="Preview da folha", use_column_width=True)

            st.success(f"✅ Ficheiro carregado: {foto_folha.name}")

            if st.button("🤖 Extrair Dados com IA",
                          key="btn_extrair_vision",
                          type="primary",
                          use_container_width=True):
                with st.spinner("A analisar a folha de ponto com Claude Vision..."):
                    try:
                        from core import extrair_folha_ponto_vision
                        import base64 as _b64

                        # Preparar imagem
                        file_bytes = foto_folha.read()
                        img_b64    = _b64.b64encode(file_bytes).decode('utf-8')

                        # Determinar media type
                        mt_map = {
                            "image/jpeg": "image/jpeg",
                            "image/jpg":  "image/jpeg",
                            "image/png":  "image/png",
                            "application/pdf": "application/pdf"
                        }
                        media_type = mt_map.get(foto_folha.type, "image/jpeg")

                        # Chamar Vision
                        resultado = extrair_folha_ponto_vision(img_b64, media_type)

                        if resultado["sucesso"] and resultado["dados"]:
                            st.session_state['fp_ocr_resultado']  = resultado
                            st.session_state['fp_ocr_obra']       = obra_fp
                            st.session_state['fp_ocr_sem_ini']    = sem_ini.strftime('%d/%m/%Y')
                            st.session_state['fp_ocr_sem_fim']    = sem_fim.strftime('%d/%m/%Y')
                            st.session_state['fp_ocr_img_b64']    = img_b64
                            st.success(
                                f"✅ Extraídos **{len(resultado['dados'])}** "
                                f"trabalhador(es) da folha!"
                            )
                            if resultado.get('periodo'):
                                st.info(f"📅 Período identificado: {resultado['periodo']}")
                        else:
                            st.error(f"❌ Erro na extração: {resultado.get('erro','Resultado vazio')}")
                            if resultado.get('raw'):
                                with st.expander("Ver resposta bruta"):
                                    st.text(resultado['raw'])

                    except Exception as e:
                        st.error(f"❌ Erro: {e}")

        # ── Mostrar e confirmar resultado da extração ─────────────────
        if st.session_state.get('fp_ocr_resultado') and \
           st.session_state.get('fp_ocr_obra') == obra_fp:

            resultado  = st.session_state['fp_ocr_resultado']
            sem_ini_s  = st.session_state.get('fp_ocr_sem_ini','')
            sem_fim_s  = st.session_state.get('fp_ocr_sem_fim','')

            st.markdown("---")
            st.markdown("### ✅ Dados Extraídos — Confirmar antes de Guardar")

            if resultado.get('obs'):
                st.info(f"ℹ️ Nota da IA: {resultado['obs']}")

            dados_editados = []
            for i, trab in enumerate(resultado['dados']):
                col_n, col_h = st.columns([3, 1])
                with col_n:
                    nome_ed = st.text_input(
                        "Nome",
                        value=trab.get('nome',''),
                        key=f"ocr_nome_{i}",
                        label_visibility="collapsed"
                    )
                with col_h:
                    horas_ed = st.number_input(
                        "Horas",
                        value=float(trab.get('horas_total', 0)),
                        min_value=0.0, step=0.5,
                        key=f"ocr_horas_{i}",
                        label_visibility="collapsed"
                    )
                dados_editados.append({
                    "nome":        nome_ed,
                    "horas_total": horas_ed,
                    "dias":        trab.get('dias', [])
                })

            st.markdown(
                "<p style='color:#94A3B8;font-size:0.8rem;'>"
                "Corrige os dados se necessário antes de guardar.</p>",
                unsafe_allow_html=True
            )

            if st.button("💾 Guardar Folha de Ponto",
                          key="btn_guardar_ocr",
                          type="primary",
                          use_container_width=True):
                import uuid as _uuid, json as _json
                from core import save_db as _save

                # Carregar CSV de folhas OCR
                try:
                    from core import load_db as _load
                    folhas_ocr_db = _load("folhas_ocr.csv", [
                        "ID","Obra","Periodo","Semana_Inicio","Semana_Fim",
                        "Tecnico","Horas_Folha","Dias","Extraido_Em",
                        "Extraido_Por","Imagem_b64","Confianca"
                    ], silent=True)
                except:
                    folhas_ocr_db = pd.DataFrame(columns=[
                        "ID","Obra","Periodo","Semana_Inicio","Semana_Fim",
                        "Tecnico","Horas_Folha","Dias","Extraido_Em",
                        "Extraido_Por","Imagem_b64","Confianca"
                    ])

                novas = []
                img_b64_store = st.session_state.get('fp_ocr_img_b64','')

                for d in dados_editados:
                    if d['nome'].strip() and d['horas_total'] > 0:
                        novas.append({
                            "ID":           str(_uuid.uuid4())[:8].upper(),
                            "Obra":         obra_fp,
                            "Periodo":      f"{sem_ini_s} - {sem_fim_s}",
                            "Semana_Inicio":sem_ini_s,
                            "Semana_Fim":   sem_fim_s,
                            "Tecnico":      d['nome'].strip(),
                            "Horas_Folha":  d['horas_total'],
                            "Dias":         _json.dumps(d['dias']),
                            "Extraido_Em":  datetime.now().strftime('%d/%m/%Y %H:%M'),
                            "Extraido_Por": user_nome,
                            "Imagem_b64":   img_b64_store[:500],  # guardar só preview
                            "Confianca":    "Vision"
                        })

                if novas:
                    df_novas = pd.DataFrame(novas)

                    # Remover entradas anteriores da mesma obra+período
                    if not folhas_ocr_db.empty:
                        folhas_ocr_db = folhas_ocr_db[
                            ~(
                                (folhas_ocr_db['Obra']          == obra_fp) &
                                (folhas_ocr_db['Semana_Inicio']  == sem_ini_s)
                            )
                        ]
                    updated = pd.concat([folhas_ocr_db, df_novas], ignore_index=True) \
                              if not folhas_ocr_db.empty else df_novas

                    _save(updated, "folhas_ocr.csv")
                    log_audit(
                        usuario=user_nome,
                        acao="UPLOAD_FOLHA_PONTO_OCR",
                        tabela="folhas_ocr.csv",
                        registro_id=f"{obra_fp}_{sem_ini_s}",
                        detalhes=f"{len(novas)} técnicos extraídos via Vision",
                        ip=""
                    )
                    inv()
                    st.session_state.pop('fp_ocr_resultado', None)
                    st.session_state.pop('fp_ocr_img_b64', None)
                    st.success(
                        f"✅ Folha de ponto guardada — "
                        f"{len(novas)} técnico(s) para {obra_fp}!"
                    )
                    st.rerun()
                else:
                    st.error("❌ Sem dados válidos para guardar.")

        # ── Folhas já guardadas ────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📋 Folhas Guardadas")
        try:
            from core import load_db as _load2
            folhas_ok = _load2("folhas_ocr.csv", [
                "ID","Obra","Periodo","Tecnico","Horas_Folha","Extraido_Em","Extraido_Por"
            ], silent=True)
            if not folhas_ok.empty:
                fp_obra = folhas_ok[folhas_ok['Obra'] == obra_fp]
                if not fp_obra.empty:
                    st.dataframe(fp_obra, use_container_width=True, hide_index=True)
                else:
                    st.info("Sem folhas guardadas para esta obra.")
            else:
                st.info("Sem folhas guardadas.")
        except:
            st.info("Sem folhas guardadas.")

        # ── Assinatura digital (mantida do original) ──────────────────
        st.markdown("---")
        st.markdown("### ✍️ Gerar Folha com Selo Digital")
        nome_resp = st.text_input("Nome do Responsável", key="fp_ch_resp")
        if st.button("📋 Gerar Folha com Selo",
                      use_container_width=True, type="primary",
                      key="btn_fp_ch"):
            if nome_resp:
                esign_id = secrets.token_hex(6).upper()
                ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                nova_folha = pd.DataFrame([{
                    "ID": str(uuid.uuid4())[:8].upper(),
                    "Obra": obra_fp,
                    "Periodo": f"{sem_ini.strftime('%d/%m')} - {sem_fim.strftime('%d/%m/%Y')}",
                    "Responsavel": nome_resp,
                    "Data_Assinatura": ts,
                    "Assinatura_b64": "",
                    "Selo": esign_id,
                    "Status": "Assinado"
                }])
                updated = pd.concat([folhas_db, nova_folha], ignore_index=True) \
                          if not folhas_db.empty else nova_folha
                save_db(updated, "folhas_ponto.csv")
                log_audit(usuario=user_nome, acao="ASSINAR_FOLHA_PONTO",
                          tabela="folhas_ponto.csv",
                          registro_id=nova_folha['ID'].iloc[0],
                          detalhes=f"Folha assinada: {nome_resp} | {obra_fp}", ip="")
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
                inv()
                st.success(f"✅ Folha #{esign_id} gerada!")
                st.rerun()
            else:
                st.warning("⚠️ Indica o nome do responsável.")  

    # ── TAB 4: HSE ──────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 🛡️ Segurança & HSE")
        sub_r, sub_rep, sub_list = st.tabs(["📋 Regras de Ouro", "⚠️ Reportar", "📊 Incidentes"])

        with sub_r:
            for ic, tit, des in REGRAS_OURO:
                with st.expander(f"{ic} {tit}"):
                    st.write(des)

        with sub_rep:
            with st.form("hse_ch_form"):
                o_hse = st.selectbox("Obra", obras_db['Obra'].unique().tolist() if not obras_db.empty else ["Geral"])
                g_hse = st.selectbox("Gravidade", ["Baixa","Média","Alta (Crítica)"])
                d_hse = st.text_area("Descrição")
                if st.form_submit_button("🛡️ Submeter Alerta HSE", use_container_width=True, type="primary"):
                    if d_hse:
                        ni = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8].upper(),
                            "Data": date.today().strftime("%d/%m/%Y"),
                            "Utilizador": user_nome, "Obra": o_hse,
                            "Status": "Aberto", "Gravidade": g_hse,
                            "Descricao": d_hse, "Tipo": "HSE"
                        }])
                        updated = pd.concat([incs_db, ni], ignore_index=True) if not incs_db.empty else ni
                        save_db(updated, "incidentes.csv")
                        inv()
                        st.success("✅ Alerta HSE submetido!")
                        st.rerun()

        with sub_list:
            if not incs_db.empty:
                i_eq = incs_db[incs_db['Obra'].isin(obras_chefe)] if obras_chefe else incs_db
                cols_s = [c for c in ['Data','Utilizador','Obra','Descricao','Gravidade','Status'] if c in i_eq.columns]
                if not i_eq.empty:
                    st.dataframe(i_eq[cols_s], use_container_width=True, hide_index=True)
                else:
                    st.success("✅ Sem incidentes.")
            else:
                st.success("✅ Sem incidentes.")

    # ── TAB 5: PEDIDOS ──────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### 📦 Pedidos da Equipa")
        tecnicos_equipa = regs_equipa['Técnico'].unique().tolist() if not regs_equipa.empty else []

        sub_f, sub_e, sub_m = st.tabs(["🔧 Ferramentas", "🦺 EPIs", "📦 Materiais"])

        def mostrar_pedidos_chefe(df):
            if df.empty:
                st.info("📋 Sem pedidos.")
                return
            df_eq = df[df['Solicitante'].isin(tecnicos_equipa)] if tecnicos_equipa and 'Solicitante' in df.columns else df
            if df_eq.empty:
                st.success("✅ Sem pedidos da equipa.")
                return
            for _, ped in df_eq.iterrows():
                cor = {"Pendente":"#F59E0B","Aprovado":"#10B981","Rejeitado":"#EF4444"}.get(ped.get('Status','Pendente'),"#6B7280")
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05);border-left:4px solid {cor};
                    padding:12px;border-radius:8px;margin-bottom:8px;">
                    <b style="color:#F8FAFC;">{ped.get('Descricao',ped.get('Item','N/A'))}</b><br>
                    <small style="color:#94A3B8;">{ped.get('Solicitante','N/A')} | {ped.get('Obra','N/A')} | {ped.get('Data','N/A')}</small><br>
                    <small style="color:{cor};font-weight:bold;">{ped.get('Status','Pendente')}</small>
                </div>
                """, unsafe_allow_html=True)

        with sub_f: mostrar_pedidos_chefe(req_fer_db)
        with sub_e: mostrar_pedidos_chefe(req_epi_db)
        with sub_m: mostrar_pedidos_chefe(req_mat_db)

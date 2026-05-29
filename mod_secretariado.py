# mod_secretariado.py — VERSÃO CORRIGIDA (com Gasóleo e Avarias adicionados)
"""
GESTNOW v3 — mod_secretariado.py
Validação de horas (1ª e 2ª), faturação, comparação com folhas de ponto,
gasóleo e avarias de frota.

Status das horas:
  0 = 🟠 Pendente      (técnico registou)
  1 = 🟢 Verde         (1ª validação — chefe ou secretariado)
  2 = 🔵 Azul          (2ª validação — faturação)
  3 = ⚫ Cinzento      (processado/pago)
"""
import streamlit as st
import pandas as pd
import base64, io
from datetime import datetime, date, timedelta
from core import save_db, inv, log_audit, criar_notificacao, fh

_STATUS_COR = {
    "0": "#F97316",
    "1": "#10B981",
    "2": "#3B82F6",
    "3": "#6B7280",
}
_STATUS_LABEL = {
    "0": "🟠 Pendente",
    "1": "🟢 Validado",
    "2": "🔵 Faturação",
    "3": "⚫ Processado",
}


def _fmt_data(val):
    try:
        if pd.isnull(val):
            return "—"
    except:
        pass
    if isinstance(val, str):
        return val if val else "—"
    try:
        return pd.Timestamp(val).strftime('%d/%m/%Y')
    except:
        return str(val)


def _regs_com_data(registos_db: pd.DataFrame) -> pd.DataFrame:
    df = registos_db.copy()
    if pd.api.types.is_datetime64_any_dtype(df['Data']):
        df['Data'] = df['Data'].dt.strftime('%d/%m/%Y').fillna('—')
    else:
        df['Data'] = df['Data'].astype(str).replace({'NaT':'—','None':'—','nan':'—'})
    df['Horas_Total'] = pd.to_numeric(df['Horas_Total'], errors='coerce').fillna(0)
    return df


@st.fragment
def render_secretariado(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     *_) = args

    user_nome = st.session_state.get('user', '')

    st.markdown("# 🗂️ Secretariado")

    regs = _regs_com_data(registos_db) if not registos_db.empty else pd.DataFrame()

    # Obras com chefe activo — apenas estas passam pelo Chefe antes do Secretariado
    obras_com_chefe = set(inst_acessos_db['Obra'].dropna()) \
                      if not inst_acessos_db.empty else set()

    _n_1val = len(regs[(regs['Status'] == '0') & (~regs['Obra'].isin(obras_com_chefe))]) \
              if not regs.empty else 0
    _n_2val = len(regs[regs['Status'] == '1']) if not regs.empty else 0

    tab_1val, tab_2val, tab_fat, tab_gasoleos, tab_avarias, tab_hist = st.tabs([
        f"🟢 1ª Validação{f' ({_n_1val})' if _n_1val else ''}",
        f"🔵 2ª Validação{f' ({_n_2val})' if _n_2val else ''}",
        "📄 Faturação & Folhas",
        "⛽ Gasóleo",
        "🔧 Avarias Frota",
        "📋 Histórico",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 — 1ª VALIDAÇÃO
    # ════════════════════════════════════════════════════════════════
    with tab_1val:
        st.markdown("### 🟢 Primeira Validação de Horas")
        st.info(
            "Aqui validas as horas de obras **sem Chefe de Equipa** ou registos "
            "que o chefe não validou. Após validação a bolinha fica **🟢 verde**."
        )

        if registos_db.empty:
            st.info("📋 Sem registos.")
        else:
            pendentes = regs[
                (regs['Status'] == '0') & (~regs['Obra'].isin(obras_com_chefe))
            ].copy()

            if pendentes.empty:
                st.success("✅ Sem horas pendentes de 1ª validação.")
            else:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    tecs = ["Todos"] + sorted(pendentes['Técnico'].dropna().unique().tolist())
                    filtro_tec = st.selectbox("Técnico", tecs, key="s1_tec")
                with col_f2:
                    obras = ["Todas"] + sorted(pendentes['Obra'].dropna().unique().tolist())
                    filtro_obra = st.selectbox("Obra", obras, key="s1_obra")

                df_view = pendentes.copy()
                if filtro_tec  != "Todos": df_view = df_view[df_view['Técnico'] == filtro_tec]
                if filtro_obra != "Todas": df_view = df_view[df_view['Obra']    == filtro_obra]

                st.markdown(f"**{len(df_view)} registo(s) pendente(s)**")

                col_va, col_vr = st.columns(2)
                with col_va:
                    if st.button("🟢 Validar Todos (filtro)",
                                  key="s1_val_todos", type="primary",
                                  use_container_width=True):
                        ids = df_view.index
                        registos_db.loc[ids, 'Status']         = '1'
                        registos_db.loc[ids, 'Validado1_Por']  = user_nome
                        registos_db.loc[ids, 'Validado1_Data'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                        save_db(registos_db, "registos.csv")
                        for _, r in df_view.iterrows():
                            criar_notificacao(destinatario=r['Técnico'],
                                titulo="🟢 Horas Validadas",
                                mensagem=f"{r['Horas_Total']}h em {r['Obra']} validadas.",
                                tipo="success", acao_url="/")
                        log_audit(usuario=user_nome, acao="VALIDACAO1_HORAS",
                                  tabela="registos.csv",
                                  registro_id=f"batch_{len(ids)}",
                                  detalhes=f"1ª validação de {len(ids)} registos", ip="")
                        inv("registos.csv")
                        st.success(f"✅ {len(ids)} registos validados!")
                        st.rerun()
                with col_vr:
                    if st.button("❌ Rejeitar Todos (filtro)",
                                  key="s1_rej_todos",
                                  use_container_width=True):
                        ids = df_view.index
                        registos_db.loc[ids, 'Status'] = '-1'
                        save_db(registos_db, "registos.csv")
                        for _, r in df_view.iterrows():
                            criar_notificacao(destinatario=r['Técnico'],
                                titulo="❌ Horas Rejeitadas",
                                mensagem=f"{r['Horas_Total']}h em {r['Obra']} rejeitadas.",
                                tipo="error", acao_url="/")
                        inv("registos.csv")
                        st.error(f"❌ {len(ids)} registos rejeitados.")
                        st.rerun()

                st.markdown("---")

                for idx1, row in df_view.iterrows():
                    reg_id = row.get('ID', '') or f"idx_{idx1}"
                    col_i, col_v, col_r = st.columns([5, 1, 1])
                    with col_i:
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:8px;"
                            f"padding:10px 14px;margin-bottom:4px;'>"
                            f"<b style='color:#F1F5F9;'>{row.get('Técnico','')}</b>"
                            f"<span style='float:right;color:#F59E0B;font-weight:700;'>"
                            f"{fh(row.get('Horas_Total',0))}</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"{row.get('Data','')} · {row.get('Obra','')} · "
                            f"{row.get('Frente','')} · {row.get('Turnos','')}"
                            f"</small></div>",
                            unsafe_allow_html=True
                        )
                    with col_v:
                        if st.button("✅", key=f"s1_val_{reg_id}_{idx1}",
                                      use_container_width=True, help="Validar"):
                            registos_db.loc[registos_db['ID'] == reg_id, 'Status']         = '1'
                            registos_db.loc[registos_db['ID'] == reg_id, 'Validado1_Por']  = user_nome
                            registos_db.loc[registos_db['ID'] == reg_id, 'Validado1_Data'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                            save_db(registos_db, "registos.csv")
                            criar_notificacao(destinatario=row.get('Técnico',''),
                                titulo="🟢 Horas Validadas",
                                mensagem=f"{fh(row.get('Horas_Total',0))} em {row.get('Obra','')} validadas.",
                                tipo="success", acao_url="/")
                            inv("registos.csv"); st.rerun()
                    with col_r:
                        if st.button("❌", key=f"s1_rej_{reg_id}_{idx1}",
                                      use_container_width=True, help="Rejeitar"):
                            registos_db.loc[registos_db['ID'] == reg_id, 'Status'] = '-1'
                            save_db(registos_db, "registos.csv")
                            criar_notificacao(destinatario=row.get('Técnico',''),
                                titulo="❌ Horas Rejeitadas",
                                mensagem=f"{fh(row.get('Horas_Total',0))} em {row.get('Obra','')} rejeitadas.",
                                tipo="error", acao_url="/")
                            inv("registos.csv"); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 2 — 2ª VALIDAÇÃO
    # ════════════════════════════════════════════════════════════════
    with tab_2val:
        st.markdown("### 🔵 Segunda Validação — Enviar para Faturação")
        st.info(
            "Aqui validas horas já aprovadas pelo Chefe/Secretariado. "
            "Após esta validação a bolinha fica **🔵 azul** e os dados entram na faturação."
        )

        if registos_db.empty:
            st.info("📋 Sem registos.")
        else:
            verdes = regs[regs['Status'] == '1'].copy()

            if verdes.empty:
                st.success("✅ Sem horas a aguardar 2ª validação.")
            else:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    tecs2 = ["Todos"] + sorted(verdes['Técnico'].dropna().unique().tolist())
                    filtro_tec2 = st.selectbox("Técnico", tecs2, key="s2_tec")
                with col_f2:
                    obras2 = ["Todas"] + sorted(verdes['Obra'].dropna().unique().tolist())
                    filtro_obra2 = st.selectbox("Obra", obras2, key="s2_obra")

                df_view2 = verdes.copy()
                if filtro_tec2  != "Todos": df_view2 = df_view2[df_view2['Técnico'] == filtro_tec2]
                if filtro_obra2 != "Todas": df_view2 = df_view2[df_view2['Obra']    == filtro_obra2]

                total_h = df_view2['Horas_Total'].sum()
                col_k1, col_k2 = st.columns(2)
                with col_k1: st.metric("📋 Registos", len(df_view2))
                with col_k2: st.metric("⏱️ Total Horas", fh(total_h))

                col_va2, col_vr2 = st.columns(2)
                with col_va2:
                    if st.button("🔵 Enviar Todos para Faturação",
                                  key="s2_val_todos", type="primary",
                                  use_container_width=True):
                        ids2 = df_view2.index
                        registos_db.loc[ids2, 'Status']         = '2'
                        registos_db.loc[ids2, 'Validado2_Por']  = user_nome
                        registos_db.loc[ids2, 'Validado2_Data'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                        save_db(registos_db, "registos.csv")
                        log_audit(usuario=user_nome, acao="VALIDACAO2_HORAS",
                                  tabela="registos.csv",
                                  registro_id=f"batch_{len(ids2)}",
                                  detalhes=f"2ª validação de {len(ids2)} registos — {fh(total_h)}", ip="")
                        inv("registos.csv")
                        st.success(f"✅ {len(ids2)} registos enviados para faturação!")
                        st.rerun()
                with col_vr2:
                    if st.button("🟠 Devolver (anular 1ª validação)",
                                  key="s2_dev_todos",
                                  use_container_width=True):
                        ids2 = df_view2.index
                        registos_db.loc[ids2, 'Status'] = '0'
                        save_db(registos_db, "registos.csv")
                        inv("registos.csv")
                        st.warning("⚠️ Registos devolvidos para pendente.")
                        st.rerun()

                st.markdown("---")

                for idx2, row in df_view2.iterrows():
                    reg_id = row.get('ID','') or f"idx_{idx2}"
                    col_i, col_v, col_d = st.columns([5, 1, 1])
                    with col_i:
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:8px;"
                            f"padding:10px 14px;margin-bottom:4px;"
                            f"border-left:3px solid #10B981;'>"
                            f"<b style='color:#F1F5F9;'>{row.get('Técnico','')}</b>"
                            f"<span style='float:right;color:#3B82F6;font-weight:700;'>"
                            f"{fh(row.get('Horas_Total',0))}</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"{row.get('Data','')} · {row.get('Obra','')} · "
                            f"{row.get('Turnos','')}</small></div>",
                            unsafe_allow_html=True
                        )
                    with col_v:
                        if st.button("🔵", key=f"s2_val_{reg_id}_{idx2}",
                                      use_container_width=True,
                                      help="Enviar para faturação"):
                            registos_db.loc[registos_db['ID'] == reg_id, 'Status']         = '2'
                            registos_db.loc[registos_db['ID'] == reg_id, 'Validado2_Por']  = user_nome
                            registos_db.loc[registos_db['ID'] == reg_id, 'Validado2_Data'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                            save_db(registos_db, "registos.csv")
                            inv("registos.csv"); st.rerun()
                    with col_d:
                        if st.button("🟠", key=f"s2_dev_{reg_id}_{idx2}",
                                      use_container_width=True,
                                      help="Devolver"):
                            registos_db.loc[registos_db['ID'] == reg_id, 'Status'] = '0'
                            save_db(registos_db, "registos.csv")
                            inv("registos.csv"); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 3 — FATURAÇÃO & FOLHAS DE PONTO
    # ════════════════════════════════════════════════════════════════
    with tab_fat:
        st.markdown("### 📄 Faturação — Comparação com Folhas de Ponto")

        if registos_db.empty:
            st.info("📋 Sem registos.")
        else:
            azuis = regs[regs['Status'] == '2'].copy()

            if azuis.empty:
                st.info("📋 Sem horas com 🔵 status de faturação.")
            else:
                obras_fat = sorted(azuis['Obra'].dropna().unique().tolist())
                obra_sel  = st.selectbox("Selecionar Obra", obras_fat, key="fat_obra")

                azuis_obra = azuis[azuis['Obra'] == obra_sel]
                total_app  = azuis_obra['Horas_Total'].sum()

                st.markdown(f"#### 📱 Horas na App — {obra_sel}")
                c1, c2 = st.columns(2)
                with c1: st.metric("Total Registos", len(azuis_obra))
                with c2: st.metric("Total Horas (App)", fh(total_app))

                resumo_tec = azuis_obra.groupby('Técnico').agg(
                    Horas=('Horas_Total','sum'),
                    Dias=('Data','nunique')
                ).reset_index()
                st.dataframe(resumo_tec, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("#### 📋 Folha de Ponto Física")

                folhas_obra = pd.DataFrame()
                if not folhas_db.empty and 'Obra' in folhas_db.columns:
                    folhas_obra = folhas_db[folhas_db['Obra'] == obra_sel]

                if not folhas_obra.empty:
                    for _, fp in folhas_obra.iterrows():
                        periodo = fp.get('Periodo','')
                        resp    = fp.get('Responsavel','')
                        selo    = fp.get('Selo','')
                        status  = fp.get('Status','')
                        cor_fp  = "#10B981" if status == 'Conferido' else "#F59E0B"
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:10px;"
                            f"padding:12px 16px;margin-bottom:8px;"
                            f"border-left:4px solid {cor_fp};'>"
                            f"<b style='color:#F1F5F9;'>📋 {periodo}</b>"
                            f"<span style='float:right;color:{cor_fp};font-size:0.8rem;'>"
                            f"{status}</span><br>"
                            f"<small style='color:#64748B;'>Responsável: {resp} · Selo: {selo}</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                st.markdown("---")
                st.markdown("#### ⚖️ Comparação App vs Folha de Ponto (IA)")

                from core import load_db as _load_ocr
                try:
                    folhas_ocr = _load_ocr("folhas_ocr.csv", [
                        "ID","Obra","Semana_Inicio","Semana_Fim",
                        "Tecnico","Horas_Folha"
                    ], silent=True)
                except:
                    folhas_ocr = pd.DataFrame()

                ocr_obra = pd.DataFrame()
                if not folhas_ocr.empty:
                    ocr_obra = folhas_ocr[folhas_ocr['Obra'] == obra_sel].copy()
                    ocr_obra['Horas_Folha'] = pd.to_numeric(
                        ocr_obra['Horas_Folha'], errors='coerce'
                    ).fillna(0)

                inconformes = []
                todos_ok    = True

                if ocr_obra.empty:
                    st.warning(
                        "⚠️ Sem folha de ponto extraída por IA para esta obra. "
                        "O Chefe precisa de fazer upload da foto no seu módulo."
                    )
                    for _, tec_row in resumo_tec.iterrows():
                        tec_nome  = tec_row['Técnico']
                        horas_app = tec_row['Horas']
                        col_tn, col_happ, col_hfp, col_diff = st.columns([3,1,1,1])
                        with col_tn:
                            st.markdown(
                                f"<p style='color:#F1F5F9;font-size:0.88rem;"
                                f"padding:8px 0;margin:0;'>{tec_nome}</p>",
                                unsafe_allow_html=True
                            )
                        with col_happ:
                            st.markdown(
                                f"<p style='color:#3B82F6;font-size:0.82rem;"
                                f"padding:8px 0;margin:0;'>App: <b>{fh(horas_app)}</b></p>",
                                unsafe_allow_html=True
                            )
                        with col_hfp:
                            h_folha = st.number_input(
                                "Folha",
                                min_value=0.0,
                                value=float(horas_app),
                                step=0.5,
                                key=f"fat_fp_manual_{tec_nome.replace(' ','_')}",
                                label_visibility="collapsed"
                            )
                        with col_diff:
                            diff = round(horas_app - h_folha, 2)
                            if abs(diff) > 0.25:
                                todos_ok = False
                                inconformes.append({
                                    "Técnico":     tec_nome,
                                    "Horas App":   fh(horas_app),
                                    "Horas Folha": fh(h_folha),
                                    "Diferença":   fh(abs(diff)),
                                    "Sentido":     "App > Folha" if diff > 0 else "Folha > App"
                                })
                                st.markdown(
                                    f"<p style='color:#EF4444;font-size:0.8rem;"
                                    f"padding:8px 0;margin:0;'>⚠️ {fh(abs(diff))}</p>",
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(
                                    "<p style='color:#10B981;font-size:0.8rem;"
                                    "padding:8px 0;margin:0;'>✅ OK</p>",
                                    unsafe_allow_html=True
                                )
                else:
                    st.success("✅ Folha extraída por IA disponível — comparação automática!")

                    periodos_disp = ocr_obra['Semana_Inicio'].unique().tolist()
                    if len(periodos_disp) > 1:
                        periodo_sel = st.selectbox(
                            "Período da folha", periodos_disp, key="fat_periodo_ocr"
                        )
                        ocr_obra = ocr_obra[ocr_obra['Semana_Inicio'] == periodo_sel]

                    folha_dict = {
                        row['Tecnico']: float(row['Horas_Folha'])
                        for _, row in ocr_obra.iterrows()
                    }

                    for _, tec_row in resumo_tec.iterrows():
                        tec_nome  = tec_row['Técnico']
                        horas_app = float(tec_row['Horas'])

                        h_folha = None
                        for nome_ocr, h_ocr in folha_dict.items():
                            if (tec_nome.lower() in nome_ocr.lower() or
                                nome_ocr.lower() in tec_nome.lower() or
                                tec_nome.split()[0].lower() in nome_ocr.lower()):
                                h_folha = h_ocr
                                break

                        col_i, col_a, col_f, col_d, col_e = st.columns([3,1,1,1,1])
                        if h_folha is None:
                            todos_ok = False
                            inconformes.append({
                                "Técnico": tec_nome, "Horas App": fh(horas_app),
                                "Horas Folha": "—", "Diferença": "—",
                                "Sentido": "❌ Não encontrado na folha"
                            })
                            with col_i: st.markdown(f"**{tec_nome}**")
                            with col_a: st.markdown(f"🔵 {fh(horas_app)}")
                            with col_f: st.markdown("—")
                            with col_d: st.markdown("—")
                            with col_e: st.markdown("❌ Não na folha")
                        else:
                            diff = round(horas_app - h_folha, 2)
                            with col_i: st.markdown(f"**{tec_nome}**")
                            with col_a: st.markdown(f"🔵 {fh(horas_app)}")
                            with col_f: st.markdown(f"📋 {fh(h_folha)}")
                            if abs(diff) > 0.25:
                                todos_ok = False
                                inconformes.append({
                                    "Técnico": tec_nome, "Horas App": fh(horas_app),
                                    "Horas Folha": fh(h_folha), "Diferença": fh(abs(diff)),
                                    "Sentido": "App > Folha" if diff > 0 else "Folha > App"
                                })
                                with col_d:
                                    st.markdown(
                                        f"<span style='color:#EF4444;font-weight:700;'>"
                                        f"⚠️ {fh(abs(diff))}</span>",
                                        unsafe_allow_html=True
                                    )
                                with col_e:
                                    st.markdown(
                                        f"<span style='color:#EF4444;'>"
                                        f"{'App > Folha' if diff>0 else 'Folha > App'}"
                                        f"</span>",
                                        unsafe_allow_html=True
                                    )
                            else:
                                with col_d: st.markdown("✅ OK")
                                with col_e: st.markdown("✅")

                    nomes_app = set(resumo_tec['Técnico'].str.lower().tolist())
                    for nome_ocr, h_ocr in folha_dict.items():
                        encontrado = any(
                            nome_ocr.lower() in n or n in nome_ocr.lower()
                            for n in nomes_app
                        )
                        if not encontrado:
                            todos_ok = False
                            inconformes.append({
                                "Técnico": nome_ocr, "Horas App": "—",
                                "Horas Folha": fh(h_ocr), "Diferença": "—",
                                "Sentido": "❌ Só na folha, não na app"
                            })
                            st.markdown(
                                f"<div style='background:rgba(239,68,68,0.1);"
                                f"border-radius:8px;padding:8px;margin-top:4px;'>"
                                f"⚠️ <b>{nome_ocr}</b> — na folha ({fh(h_ocr)}) "
                                f"mas <b>sem registo na app</b></div>",
                                unsafe_allow_html=True
                            )

                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

                if not todos_ok:
                    st.error(
                        f"🚨 **{len(inconformes)} inconformidade(s) detetada(s)** — "
                        f"Pagamento bloqueado até resolução manual."
                    )
                    st.dataframe(pd.DataFrame(inconformes),
                                 use_container_width=True, hide_index=True)
                    st.warning(
                        "⚠️ Verifica com o Chefe de Equipa se houve erro "
                        "na app, na folha ou no registo do técnico."
                    )
                    with st.expander("🔓 Forçar aprovação com justificação"):
                        justificacao = st.text_area(
                            "Justificação obrigatória *",
                            key="fat_just",
                            placeholder="Descreve o motivo..."
                        )
                        if st.button("⚠️ Aprovar com Inconformidade",
                                      key="fat_forcar", type="secondary",
                                      use_container_width=True):
                            if justificacao.strip():
                                _processar_pagamento(
                                    registos_db, azuis_obra, obra_sel,
                                    user_nome, justificacao, inconformes
                                )
                                inv("registos.csv")
                                st.success("✅ Processado com ressalva.")
                                st.rerun()
                            else:
                                st.error("❌ Justificação obrigatória.")
                else:
                    st.success("✅ Todos os registos conferem com a folha de ponto!")
                    if st.button("✅ Processar Pagamento",
                                  key="fat_processar", type="primary",
                                  use_container_width=True):
                        _processar_pagamento(
                            registos_db, azuis_obra, obra_sel,
                            user_nome, "Conferido sem inconformidades", []
                        )
                        inv("registos.csv")
                        st.success(f"✅ Pagamento processado para {obra_sel}!")
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — GASÓLEO (migrado do armazém)
    # ════════════════════════════════════════════════════════════════
    with tab_gasoleos:
        st.markdown("### ⛽ Validação de Gasóleo")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not req_mat_db.empty:
                if 'Data_Validacao' not in req_mat_db.columns: req_mat_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in req_mat_db.columns: req_mat_db['Validado_Por']   = ""
                pend_gas = req_mat_db[
                    (req_mat_db['Status'] == 'Pendente') &
                    (req_mat_db.get('Tipo', pd.Series([''] * len(req_mat_db))) == 'Gasóleo')
                ]
                if not pend_gas.empty:
                    st.markdown(f"**{len(pend_gas)} pedido(s) pendente(s)**")
                    for idx, ped in pend_gas.iterrows():
                        ped_id = ped.get('ID', f"GAS_{idx}")
                        with st.expander(
                            f"⛽ {ped.get('Litros',0)}L — "
                            f"{ped.get('Solicitante','N/A')} ({ped.get('Obra','N/A')})",
                            expanded=True
                        ):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);
                                padding:15px;border-radius:10px;">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Litros:</strong> {ped.get('Litros',0)}L</p>
                                <p><strong>Valor:</strong> €{ped.get('Valor',0)}</p>
                                <p><strong>Data:</strong> {ped.get('Data_Abastecimento','N/A')}</p>
                            </div>""", unsafe_allow_html=True)
                            if ped.get('Recibo_b64'):
                                recibo_str = str(ped.get('Recibo_b64',''))
                                if recibo_str.startswith('JVBER'):
                                    st.info("📄 Recibo PDF — descarrega para visualizar")
                                else:
                                    try:
                                        st.image(
                                            f"data:image/png;base64,{recibo_str}",
                                            caption="Recibo", width=300
                                        )
                                    except:
                                        pass
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Validar", key=f"sec_apr_gas_{ped_id}",
                                              use_container_width=True):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Aprovado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = user_nome
                                    save_db(req_mat_db, "req_materiais.csv")
                                    criar_notificacao(
                                        destinatario=ped.get('Solicitante',''),
                                        titulo="✅ Gasóleo Validado",
                                        mensagem=f"{ped.get('Litros')}L validados!",
                                        tipo="success", acao_url="/tecnico"
                                    )
                                    inv("req_materiais.csv"); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"sec_rej_gas_{ped_id}",
                                              use_container_width=True, type="secondary"):
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Status']         = 'Rejeitado'
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    req_mat_db.loc[req_mat_db['ID'] == ped_id, 'Validado_Por']   = user_nome
                                    save_db(req_mat_db, "req_materiais.csv")
                                    inv("req_materiais.csv"); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem gasóleos pendentes!")
            else:
                st.info("📋 Sem registos de gasóleo.")

        with sub_h:
            if not req_mat_db.empty:
                hist_gas = req_mat_db[
                    (req_mat_db['Status'].isin(['Aprovado','Rejeitado'])) &
                    (req_mat_db.get('Tipo', pd.Series([''] * len(req_mat_db))) == 'Gasóleo')
                ]
                if not hist_gas.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Litros',
                                        'Valor','Status','Data_Validacao','Validado_Por']
                            if c in hist_gas.columns]
                    st.dataframe(hist_gas[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico de gasóleo.")

    # ════════════════════════════════════════════════════════════════
    # TAB 5 — AVARIAS FROTA (migrado do armazém)
    # ════════════════════════════════════════════════════════════════
    with tab_avarias:
        st.markdown("### 🔧 Avarias de Frota")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📋 Histórico"])

        with sub_p:
            if not incs_db.empty:
                if 'Data_Validacao' not in incs_db.columns: incs_db['Data_Validacao'] = ""
                if 'Validado_Por'   not in incs_db.columns: incs_db['Validado_Por']   = ""
                pend_av = incs_db[
                    (incs_db['Status'] == 'Pendente') &
                    (incs_db.get('Tipo', pd.Series([''] * len(incs_db))) == 'Avaria')
                ]
                if not pend_av.empty:
                    st.markdown(f"**{len(pend_av)} avaria(s) pendente(s)**")
                    for idx, ped in pend_av.iterrows():
                        ped_id = ped.get('ID', f"AVAR_{idx}")
                        cor_u  = {"Baixa":"#10B981","Média":"#F59E0B",
                                  "Alta":"#EF4444","Crítica - Paragem":"#DC2626"}.get(
                                      ped.get('Urgencia','Média'),"#6B7280")
                        with st.expander(
                            f"🔧 {str(ped.get('Equipamento','Equipamento'))[:40]} — "
                            f"{ped.get('Solicitante','N/A')}",
                            expanded=True
                        ):
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);
                                padding:15px;border-radius:10px;
                                border-left:4px solid {cor_u};">
                                <p><strong>Solicitante:</strong> {ped.get('Solicitante','N/A')}</p>
                                <p><strong>Obra:</strong> {ped.get('Obra','N/A')}</p>
                                <p><strong>Equipamento:</strong> {ped.get('Equipamento','N/A')}</p>
                                <p><strong>Descrição:</strong> {ped.get('Descricao','N/A')}</p>
                                <p><strong>Urgência:</strong>
                                    <span style="color:{cor_u};font-weight:bold;">
                                        {ped.get('Urgencia','N/A')}
                                    </span></p>
                                <p><strong>Valor Estimado:</strong> €{ped.get('Valor_Estimado',0)}</p>
                            </div>""", unsafe_allow_html=True)
                            if ped.get('Fatura_b64'):
                                fat_str = str(ped.get('Fatura_b64',''))
                                if fat_str.startswith('JVBER'):
                                    st.info("📄 Fatura PDF")
                                else:
                                    try:
                                        st.image(
                                            f"data:image/png;base64,{fat_str}",
                                            caption="Fatura", width=300
                                        )
                                    except:
                                        pass
                            ca, cr = st.columns(2)
                            with ca:
                                if st.button("✅ Aprovar", key=f"sec_apr_av_{ped_id}",
                                              use_container_width=True):
                                    incs_db.loc[incs_db.index == idx, 'Status']         = 'Aprovado'
                                    incs_db.loc[incs_db.index == idx, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    incs_db.loc[incs_db.index == idx, 'Validado_Por']   = user_nome
                                    save_db(incs_db, "incidentes.csv")
                                    criar_notificacao(
                                        destinatario=ped.get('Solicitante',''),
                                        titulo="✅ Reparação Aprovada",
                                        mensagem=f"A tua reparação de {ped.get('Equipamento')} foi aprovada!",
                                        tipo="success", acao_url="/tecnico"
                                    )
                                    inv("incidentes.csv"); st.success("✅"); st.rerun()
                            with cr:
                                if st.button("❌ Rejeitar", key=f"sec_rej_av_{ped_id}",
                                              use_container_width=True, type="secondary"):
                                    incs_db.loc[incs_db.index == idx, 'Status']         = 'Rejeitado'
                                    incs_db.loc[incs_db.index == idx, 'Data_Validacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    incs_db.loc[incs_db.index == idx, 'Validado_Por']   = user_nome
                                    save_db(incs_db, "incidentes.csv")
                                    inv("incidentes.csv"); st.error("❌"); st.rerun()
                else:
                    st.success("✅ Sem avarias pendentes!")
            else:
                st.info("📋 Sem avarias registadas.")

        with sub_h:
            if not incs_db.empty:
                hist_av = incs_db[
                    (incs_db['Status'].isin(['Aprovado','Rejeitado'])) &
                    (incs_db.get('Tipo', pd.Series([''] * len(incs_db))) == 'Avaria')
                ]
                if not hist_av.empty:
                    cols = [c for c in ['Data','Solicitante','Obra','Equipamento',
                                        'Urgencia','Status','Data_Validacao','Validado_Por']
                            if c in hist_av.columns]
                    st.dataframe(hist_av[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("📋 Sem histórico de avarias.")

    # ════════════════════════════════════════════════════════════════
    # TAB 6 — HISTÓRICO
    # ════════════════════════════════════════════════════════════════
    with tab_hist:
        st.markdown("### 📋 Histórico de Horas Processadas")

        if registos_db.empty:
            st.info("📋 Sem registos.")
        else:
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1:
                anos = sorted(set(
                    str(d)[:4] for d in regs['Data'].tolist()
                    if str(d) and str(d) != '—' and len(str(d)) >= 4
                ), reverse=True)
                ano_sel = st.selectbox("Ano", ["Todos"] + anos, key="hist_ano")
            with col_h2:
                meses_pt = {
                    "01":"Janeiro","02":"Fevereiro","03":"Março","04":"Abril",
                    "05":"Maio","06":"Junho","07":"Julho","08":"Agosto",
                    "09":"Setembro","10":"Outubro","11":"Novembro","12":"Dezembro"
                }
                mes_sel = st.selectbox(
                    "Mês",
                    ["Todos"] + [f"{k} — {v}" for k, v in meses_pt.items()],
                    key="hist_mes"
                )
            with col_h3:
                status_sel = st.selectbox(
                    "Estado",
                    ["Todos","🟢 Verde (1)","🔵 Azul (2)","⚫ Processado (3)","❌ Rejeitado"],
                    key="hist_status"
                )

            status_map = {
                "🟢 Verde (1)":     "1",
                "🔵 Azul (2)":      "2",
                "⚫ Processado (3)": "3",
                "❌ Rejeitado":     "-1",
            }

            hist_all = regs[regs['Status'].isin(['1','2','3','-1'])].copy()

            if ano_sel != "Todos":
                hist_all = hist_all[
                    hist_all['Data'].str.endswith(ano_sel, na=False)
                ]
            if mes_sel != "Todos":
                mes_num = mes_sel[:2]
                hist_all = hist_all[
                    hist_all['Data'].str.contains(f"/{mes_num}/", na=False)
                ]
            if status_sel != "Todos":
                hist_all = hist_all[
                    hist_all['Status'] == status_map.get(status_sel,'')
                ]

            hist_all['Estado'] = hist_all['Status'].map(_STATUS_LABEL)

            if not hist_all.empty:
                total_h_hist = hist_all['Horas_Total'].sum()
                col_m1, col_m2 = st.columns(2)
                with col_m1: st.metric("📋 Registos", len(hist_all))
                with col_m2: st.metric("⏱️ Total", fh(total_h_hist))

                cols_show = [c for c in ['Data','Técnico','Obra','Horas_Total','Estado']
                             if c in hist_all.columns]
                st.dataframe(
                    hist_all[cols_show].sort_values('Data', ascending=False),
                    use_container_width=True, hide_index=True
                )

                csv = hist_all[cols_show].to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "📥 Exportar CSV",
                    data=csv.encode('utf-8-sig'),
                    file_name=f"historico_{ano_sel}_{mes_sel[:2] if mes_sel!='Todos' else 'all'}.csv",
                    mime="text/csv",
                    key="hist_export"
                )
            else:
                st.info("📋 Sem registos com este filtro.")


def _processar_pagamento(
    registos_db: pd.DataFrame,
    azuis_obra: pd.DataFrame,
    obra: str,
    user_nome: str,
    justificacao: str,
    inconformes: list
):
    ids_processar = azuis_obra['ID'].tolist() if 'ID' in azuis_obra.columns else []

    if ids_processar:
        mask = registos_db['ID'].isin(ids_processar)
        registos_db.loc[mask, 'Status']          = '3'
        registos_db.loc[mask, 'Processado_Por']  = user_nome
        registos_db.loc[mask, 'Processado_Data'] = datetime.now().strftime('%d/%m/%Y %H:%M')
    else:
        ids_idx = azuis_obra.index
        registos_db.loc[ids_idx, 'Status']          = '3'
        registos_db.loc[ids_idx, 'Processado_Por']  = user_nome
        registos_db.loc[ids_idx, 'Processado_Data'] = datetime.now().strftime('%d/%m/%Y %H:%M')

    save_db(registos_db, "registos.csv")

    for tec in azuis_obra['Técnico'].unique():
        criar_notificacao(
            destinatario=tec,
            titulo="⚫ Horas Processadas",
            mensagem=f"As tuas horas em {obra} foram processadas para pagamento.",
            tipo="info", acao_url="/"
        )

    log_audit(
        usuario=user_nome,
        acao="PROCESSAR_PAGAMENTO",
        tabela="registos.csv",
        registro_id=f"{obra}_{datetime.now().strftime('%Y%m%d')}",
        detalhes=(
            f"Obra: {obra} · {len(azuis_obra)} registos. "
            f"Inconformes: {len(inconformes)}. "
            f"Justificação: {justificacao[:100]}"
        ),
        ip=""
    )

# mod_contactos_iso.py
"""
GESTNOW v3 — mod_contactos_iso.py
Rastreabilidade de Contactos — ISO 9001:2015 Cláusula 8.2
"""
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date, timedelta
from core import save_db, inv, load_db, log_audit

_COLS = [
    "ID", "Data", "Hora", "Canal", "Sentido",
    "Cliente_Nome", "Contacto_Nome", "Contacto_Telefone", "Contacto_Email",
    "Assunto", "Resumo", "Responsavel",
    "Evidencia_Tipo", "Evidencia_Path",
    "Oportunidade_ID", "Estado",
    "Proximo_Passo", "Data_Proximo_Passo", "Notas",
]

_COLS_OPORT = [
    "ID", "Nome", "Cliente", "Setor", "Comercial",
    "Stage", "Valor_Est", "Prob_Fecho", "Data_Criacao",
    "Data_Fecho_Est", "Origem", "Notas", "Obra_Associada",
]

_STAGES_ATIVOS = {"prospeto", "contactado", "reuniao", "proposta", "negociacao"}

_CANAIS = [
    "📞 Telefone",
    "📧 Email",
    "💬 WhatsApp / Mensagem",
    "🏆 Concurso Público",
    "🤝 Visita Presencial",
    "📋 Indicação / Referência",
    "🌐 Website / LinkedIn",
    "📮 Correio / Fax",
    "🔄 Renovação de Contrato",
]

_ESTADOS   = ["Aberto", "Em Seguimento", "Fechado"]
_SENTIDOS  = ["Entrada", "Saída"]
_EV_TIPOS  = ["Nenhuma", "Print de Chamada", "Email (PDF)", "WhatsApp (Print)", "Documento", "Outro"]

_COR_ESTADO = {
    "Aberto":        "#F59E0B",
    "Em Seguimento": "#3B82F6",
    "Fechado":       "#10B981",
}

_CANAL_ICON = {c: c.split()[0] for c in _CANAIS}  # primeiro emoji de cada string


def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except Exception:
        return pd.DataFrame(columns=cols)


def _upload_evidencia(ficheiro, contacto_id: str) -> str:
    """Faz upload da evidência para GCS e devolve o path gs://."""
    from google.cloud import storage as gcs
    import datetime as dt
    client = gcs.Client()
    bucket = client.bucket("gestnow-dados")
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_name = f"evidencias_contactos/{contacto_id}/{ts}_{ficheiro.name}"
    blob = bucket.blob(blob_name)
    blob.upload_from_file(ficheiro, content_type=ficheiro.type)
    return f"gs://gestnow-dados/{blob_name}"


def _get_evidencia_url(gcs_path: str, expiry_minutes: int = 60) -> str:
    """Gera URL assinada temporária para aceder à evidência."""
    import datetime as dt
    if not gcs_path or not gcs_path.startswith("gs://"):
        return ""
    try:
        from google.cloud import storage as gcs
        parts = gcs_path.replace("gs://gestnow-dados/", "")
        client = gcs.Client()
        bucket = client.bucket("gestnow-dados")
        blob = bucket.blob(parts)
        return blob.generate_signed_url(
            expiration=dt.timedelta(minutes=expiry_minutes),
            method="GET",
        )
    except Exception:
        return ""


def render_contactos_iso(*_):
    """Módulo de Rastreabilidade de Contactos — ISO 9001:2015 Cl. 8.2"""

    ct_db  = _load("com_contactos.csv",               _COLS)
    op_db  = _load("comercial_oportunidades.csv",      _COLS_OPORT)
    user   = st.session_state.get("user", "Admin")
    hoje   = date.today()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    n_total  = len(ct_db) if not ct_db.empty else 0
    n_aberto = int((ct_db["Estado"] == "Aberto").sum()) if not ct_db.empty else 0
    n_sem_ev = int((ct_db["Evidencia_Tipo"] == "Nenhuma").sum()) if not ct_db.empty else 0
    n_sem_op = int(
        (ct_db["Oportunidade_ID"].isna() | (ct_db["Oportunidade_ID"] == "")).sum()
    ) if not ct_db.empty else 0

    st.markdown("### 🔗 Contactos ISO 9001:2015")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("📋 Total Contactos",   n_total)
    with c2: st.metric("🟡 Em Aberto",          n_aberto)
    with c3: st.metric("⚠️ Sem Evidência",      n_sem_ev)
    with c4: st.metric("🔗 Sem Oportunidade",   n_sem_op)
    st.divider()

    tab_lista, tab_novo, tab_timeline, tab_analytics = st.tabs([
        "📋 Contactos",
        "➕ Registar Contacto",
        "🔗 Timeline por Cliente",
        "📊 Analytics ISO",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — LISTA
    # ══════════════════════════════════════════════════════════════════════════
    with tab_lista:
        if ct_db.empty:
            st.info("📋 Sem contactos registados. Usa o tab ➕ Registar Contacto.")
        else:
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                f_canal  = st.selectbox("Canal",       ["Todos"] + _CANAIS,   key="ct_f_canal")
            with col_f2:
                f_estado = st.selectbox("Estado",      ["Todos"] + _ESTADOS,  key="ct_f_estado")
            with col_f3:
                resp_u   = sorted(ct_db["Responsavel"].dropna().unique().tolist())
                f_resp   = st.selectbox("Responsável", ["Todos"] + resp_u,     key="ct_f_resp")
            with col_f4:
                f_cli    = st.text_input("Cliente", key="ct_f_cliente", placeholder="Filtrar...")

            df_f = ct_db.copy()
            if f_canal  != "Todos":
                df_f = df_f[df_f["Canal"] == f_canal]
            if f_estado != "Todos":
                df_f = df_f[df_f["Estado"] == f_estado]
            if f_resp   != "Todos":
                df_f = df_f[df_f["Responsavel"] == f_resp]
            if f_cli.strip():
                df_f = df_f[df_f["Cliente_Nome"].str.contains(f_cli.strip(), case=False, na=False)]

            st.markdown(f"**{len(df_f)} contacto(s)**")

            for _, ct in df_f.sort_values("Data", ascending=False).iterrows():
                cid    = ct.get("ID", "")
                estado = ct.get("Estado", "Aberto")
                tem_ev = ct.get("Evidencia_Tipo", "Nenhuma") != "Nenhuma"
                tem_op = bool(ct.get("Oportunidade_ID", ""))
                cor_e  = _COR_ESTADO.get(estado, "#64748B")
                icon   = _CANAL_ICON.get(ct.get("Canal", ""), "📋")

                with st.expander(
                    f"{icon} {ct.get('Data','')} {ct.get('Hora','')} — "
                    f"{ct.get('Cliente_Nome','')} | {ct.get('Contacto_Nome','')} "
                    f"| {estado} {'✅' if tem_ev else '⚠️'} {'🔗' if tem_op else ''}",
                    expanded=False,
                ):
                    col_d1, col_d2 = st.columns([2, 1])
                    with col_d1:
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:8px;padding:12px;'>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Canal:</b> {ct.get('Canal','')} | "
                            f"<b>Sentido:</b> {ct.get('Sentido','')}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Empresa:</b> {ct.get('Cliente_Nome','')}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Contacto:</b> {ct.get('Contacto_Nome','')} | "
                            f"{ct.get('Contacto_Telefone','')} | "
                            f"{ct.get('Contacto_Email','')}</p>"
                            f"<p style='color:#F1F5F9;margin:2px 0;'>"
                            f"<b>Assunto:</b> {ct.get('Assunto','')}</p>"
                            f"<p style='color:#94A3B8;margin:4px 0;font-size:0.9rem;'>"
                            f"{ct.get('Resumo','')}</p>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        if ct.get("Proximo_Passo", ""):
                            st.markdown(
                                f"<div style='background:#0F172A;"
                                f"border-left:3px solid #F59E0B;"
                                f"border-radius:4px;padding:8px;margin-top:6px;'>"
                                f"<small style='color:#F59E0B;'>🗓️ Próximo passo: "
                                f"{ct.get('Proximo_Passo','')} — "
                                f"{ct.get('Data_Proximo_Passo','')}</small>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        if tem_op:
                            st.markdown(
                                f"<div style='background:#0F172A;"
                                f"border-left:3px solid #3B82F6;"
                                f"border-radius:4px;padding:8px;margin-top:6px;'>"
                                f"<small style='color:#3B82F6;'>🔗 Oportunidade: "
                                f"{ct.get('Oportunidade_ID','')}</small>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        if ct.get("Notas", ""):
                            st.caption(f"📝 {ct.get('Notas','')}")

                    with col_d2:
                        st.markdown(
                            f"<div style='background:{cor_e}18;"
                            f"border:1px solid {cor_e};"
                            f"border-radius:8px;padding:10px;text-align:center;'>"
                            f"<b style='color:{cor_e};'>{estado}</b><br>"
                            f"<small style='color:#64748B;'>"
                            f"Responsável: {ct.get('Responsavel','')}</small>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                        ev_path = ct.get("Evidencia_Path", "")
                        if ev_path:
                            url = _get_evidencia_url(ev_path)
                            if url:
                                st.link_button(
                                    "📎 Ver Evidência", url,
                                    use_container_width=True,
                                )
                        else:
                            st.caption("⚠️ Sem evidência")

                        novo_est = st.selectbox(
                            "Estado",
                            _ESTADOS,
                            index=_ESTADOS.index(estado) if estado in _ESTADOS else 0,
                            key=f"ct_est_{cid}",
                        )
                        if st.button(
                            "✅ Atualizar", key=f"ct_upd_{cid}",
                            use_container_width=True, type="primary",
                        ):
                            ct_db.loc[ct_db["ID"] == cid, "Estado"] = novo_est
                            save_db(ct_db, "com_contactos.csv")
                            inv("com_contactos.csv")
                            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — REGISTAR CONTACTO
    # ══════════════════════════════════════════════════════════════════════════
    with tab_novo:
        st.markdown("#### ➕ Registar Novo Contacto")

        st.markdown("**A — Identificação**")
        col_a1, col_a2, col_a3, col_a4 = st.columns(4)
        with col_a1:
            n_data    = st.date_input("Data *", value=hoje, key="ct_n_data")
        with col_a2:
            n_hora    = st.time_input(
                "Hora *",
                value=datetime.now().time().replace(second=0, microsecond=0),
                key="ct_n_hora",
            )
        with col_a3:
            n_canal   = st.selectbox("Canal *",   _CANAIS,   key="ct_n_canal")
        with col_a4:
            n_sentido = st.selectbox("Sentido *", _SENTIDOS, key="ct_n_sentido")

        st.markdown("**B — Cliente / Contacto**")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            n_cli_nome = st.text_input("Nome da Empresa *",  key="ct_n_cli_nome")
            n_ct_nome  = st.text_input("Nome do Contacto *", key="ct_n_ct_nome")
        with col_b2:
            n_ct_tel   = st.text_input("Telefone", key="ct_n_ct_tel")
            n_ct_email = st.text_input("Email",    key="ct_n_ct_email")

        st.markdown("**C — Conteúdo**")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            n_assunto = st.text_input("Assunto *",  key="ct_n_assunto")
            n_resumo  = st.text_area("Resumo *",    key="ct_n_resumo", height=110)
        with col_c2:
            n_resp       = st.text_input("Responsável *", value=user, key="ct_n_resp")
            n_prox       = st.text_input("Próximo Passo", key="ct_n_prox")
            n_data_prox  = st.date_input(
                "Data Próximo Passo",
                value=hoje + timedelta(days=7),
                key="ct_n_data_prox",
            )
            n_notas = st.text_area("Notas", key="ct_n_notas", height=60)

        st.markdown("**D — Evidência**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            n_ev_tipo = st.selectbox("Tipo de Evidência *", _EV_TIPOS, key="ct_n_ev_tipo")
        with col_d2:
            n_ev_file = None
            if n_ev_tipo != "Nenhuma":
                n_ev_file = st.file_uploader(
                    "Ficheiro (jpg/png/pdf, máx 5 MB)",
                    type=["jpg", "jpeg", "png", "pdf", "eml"],
                    key="ct_n_ev_file",
                )
                if n_ev_file and n_ev_file.size > 5 * 1024 * 1024:
                    st.error("❌ Ficheiro excede 5 MB.")
                    n_ev_file = None

        st.markdown("**E — Ligar a Oportunidade (opcional)**")
        ops_label = ["— Nenhuma —"]
        if not op_db.empty:
            ativos = op_db[op_db["Stage"].isin(_STAGES_ATIVOS)]
            ops_label += [
                f"{r['ID']} — {r['Nome']} ({r['Cliente']})"
                for _, r in ativos.iterrows()
            ]
        n_op = st.selectbox("Oportunidade", ops_label, key="ct_n_op")

        st.divider()
        if st.button("💾 Guardar Contacto", key="ct_btn_save", type="primary"):
            erros = []
            if not n_cli_nome.strip(): erros.append("Nome da empresa")
            if not n_ct_nome.strip():  erros.append("Nome do contacto")
            if not n_assunto.strip():  erros.append("Assunto")
            if not n_resumo.strip():   erros.append("Resumo")

            if erros:
                st.error(f"❌ Campos obrigatórios em falta: {', '.join(erros)}")
            else:
                cid = str(uuid.uuid4())[:8].upper()

                ev_path = ""
                if n_ev_file and n_ev_tipo != "Nenhuma":
                    try:
                        ev_path = _upload_evidencia(n_ev_file, cid)
                    except Exception as e:
                        st.warning(f"⚠️ Upload de evidência falhou: {e}")

                op_id = ""
                if n_op != "— Nenhuma —":
                    op_id = n_op.split(" — ")[0].strip()

                novo = pd.DataFrame([{
                    "ID":                  cid,
                    "Data":                n_data.strftime("%d/%m/%Y"),
                    "Hora":                n_hora.strftime("%H:%M"),
                    "Canal":               n_canal,
                    "Sentido":             n_sentido,
                    "Cliente_Nome":        n_cli_nome.strip(),
                    "Contacto_Nome":       n_ct_nome.strip(),
                    "Contacto_Telefone":   n_ct_tel.strip(),
                    "Contacto_Email":      n_ct_email.strip(),
                    "Assunto":             n_assunto.strip(),
                    "Resumo":              n_resumo.strip(),
                    "Responsavel":         n_resp.strip() or user,
                    "Evidencia_Tipo":      n_ev_tipo,
                    "Evidencia_Path":      ev_path,
                    "Oportunidade_ID":     op_id,
                    "Estado":              "Aberto",
                    "Proximo_Passo":       n_prox.strip(),
                    "Data_Proximo_Passo":  n_data_prox.strftime("%d/%m/%Y") if n_prox.strip() else "",
                    "Notas":               n_notas.strip(),
                }])

                upd = pd.concat([ct_db, novo], ignore_index=True) if not ct_db.empty else novo
                save_db(upd, "com_contactos.csv")
                log_audit(
                    usuario=user, acao="CRIAR_CONTACTO",
                    tabela="com_contactos.csv", registro_id=cid,
                    detalhes=f"{n_cli_nome} | {n_canal} | {n_sentido}", ip="",
                )
                inv("com_contactos.csv")
                st.success(f"✅ Contacto {cid} registado com sucesso!")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — TIMELINE POR CLIENTE
    # ══════════════════════════════════════════════════════════════════════════
    with tab_timeline:
        st.markdown("#### 🔗 Timeline de Rastreabilidade por Cliente")

        if ct_db.empty:
            st.info("📋 Sem contactos para mostrar timeline.")
        else:
            clientes_u = sorted(ct_db["Cliente_Nome"].dropna().unique().tolist())
            sel_cli = st.selectbox("Selecionar Cliente", clientes_u, key="ct_tl_cli")

            cts_cli = ct_db[ct_db["Cliente_Nome"] == sel_cli].sort_values("Data")

            for _, ct in cts_cli.iterrows():
                cid    = ct.get("ID", "")
                tem_ev = ct.get("Evidencia_Tipo", "Nenhuma") != "Nenhuma"
                op_id  = str(ct.get("Oportunidade_ID", "") or "")
                icon   = _CANAL_ICON.get(ct.get("Canal", ""), "📋")
                resumo = str(ct.get("Resumo", ""))
                ev_txt = (
                    f"<small style='color:#10B981;'>📎 {ct.get('Evidencia_Tipo','')}</small>"
                    if tem_ev else
                    "<small style='color:#EF4444;'>⚠️ Sem evidência</small>"
                )
                op_txt = (
                    f"<br><small style='color:#3B82F6;'>🔗 Oportunidade: {op_id}</small>"
                    if op_id else ""
                )

                st.markdown(
                    f"<div style='border-left:3px solid #3B82F6;"
                    f"padding:10px 16px;margin-bottom:6px;"
                    f"background:#1E293B;border-radius:0 8px 8px 0;'>"
                    f"<b style='color:#F1F5F9;'>"
                    f"{icon} {ct.get('Data','')} {ct.get('Hora','')} — "
                    f"{ct.get('Canal','')} ({ct.get('Sentido','')})</b><br>"
                    f"<span style='color:#94A3B8;'>"
                    f"{ct.get('Contacto_Nome','')} | {ct.get('Assunto','')}</span><br>"
                    f"<small style='color:#64748B;'>"
                    f"{resumo[:140]}{'...' if len(resumo) > 140 else ''}</small><br>"
                    f"{ev_txt}{op_txt}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if op_id and not op_db.empty:
                    op_row = op_db[op_db["ID"] == op_id]
                    if not op_row.empty:
                        op = op_row.iloc[0]
                        valor = float(op.get("Valor_Est", 0) or 0)
                        st.markdown(
                            f"<div style='margin-left:20px;"
                            f"border-left:3px solid #8B5CF6;"
                            f"padding:8px 14px;background:#0F172A;"
                            f"border-radius:0 6px 6px 0;margin-bottom:8px;'>"
                            f"<small style='color:#8B5CF6;'>↳ Oportunidade: "
                            f"<b>{op.get('Nome','')}</b> | "
                            f"Stage: {op.get('Stage','')} | "
                            f"Valor: €{valor:,.0f}</small>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — ANALYTICS ISO
    # ══════════════════════════════════════════════════════════════════════════
    with tab_analytics:
        st.markdown("#### 📊 Analytics ISO 9001:2015")

        if ct_db.empty:
            st.info("📋 Sem dados suficientes para analytics.")
        else:
            import plotly.graph_objects as go
            import plotly.express as px

            col_an1, col_an2 = st.columns(2)

            with col_an1:
                canal_counts = ct_db["Canal"].value_counts().reset_index()
                canal_counts.columns = ["Canal", "Contagem"]
                fig_p = px.pie(
                    canal_counts, names="Canal", values="Contagem",
                    title="Origem por Canal",
                    color_discrete_sequence=px.colors.sequential.Blues_r,
                    hole=0.4,
                )
                fig_p.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#F1F5F9"},
                    title_font_color="#F1F5F9",
                    legend={"font": {"color": "#94A3B8"}},
                    height=280, margin=dict(t=40, b=20, l=10, r=10),
                )
                st.plotly_chart(fig_p, use_container_width=True)

            with col_an2:
                n_com_prox = int(
                    (ct_db["Proximo_Passo"].notna() & (ct_db["Proximo_Passo"] != "")).sum()
                )
                n_sem_prox = n_total - n_com_prox
                fig_fu = go.Figure(go.Bar(
                    x=["Com próximo passo", "Sem próximo passo"],
                    y=[n_com_prox, n_sem_prox],
                    marker_color=["#10B981", "#EF4444"],
                    text=[n_com_prox, n_sem_prox],
                    textposition="outside",
                    textfont={"color": "#F1F5F9"},
                ))
                fig_fu.update_layout(
                    title={"text": "Taxa de Follow-up", "font": {"color": "#F1F5F9"}},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(30,41,59,0.5)",
                    font={"color": "#F1F5F9"},
                    xaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}},
                    yaxis={"gridcolor": "#334155", "tickfont": {"color": "#94A3B8"}},
                    height=280, margin=dict(t=40, b=20, l=10, r=10),
                    showlegend=False,
                )
                st.plotly_chart(fig_fu, use_container_width=True)

            st.divider()
            col_kpi1, col_kpi2 = st.columns(2)

            with col_kpi1:
                st.markdown("**🔗 Contactos sem Oportunidade Ligada**")
                sem_op = ct_db[
                    ct_db["Oportunidade_ID"].isna() | (ct_db["Oportunidade_ID"] == "")
                ]
                if not sem_op.empty:
                    for _, ct in sem_op.head(10).iterrows():
                        assunto = str(ct.get("Assunto", ""))
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:6px;"
                            f"padding:6px 10px;margin-bottom:4px;'>"
                            f"<small style='color:#F1F5F9;'>"
                            f"{ct.get('Data','')} — {ct.get('Cliente_Nome','')} — "
                            f"{assunto[:50]}</small>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    if len(sem_op) > 10:
                        st.caption(f"... e mais {len(sem_op) - 10}")
                else:
                    st.success("✅ Todos os contactos têm oportunidade ligada.")

            with col_kpi2:
                st.markdown("**⚠️ Contactos sem Evidência**")
                sem_ev = ct_db[ct_db["Evidencia_Tipo"] == "Nenhuma"]
                if not sem_ev.empty:
                    for _, ct in sem_ev.head(10).iterrows():
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:6px;"
                            f"padding:6px 10px;margin-bottom:4px;'>"
                            f"<small style='color:#F1F5F9;'>"
                            f"{ct.get('Data','')} — {ct.get('Cliente_Nome','')} — "
                            f"{ct.get('Canal','')}</small>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    if len(sem_ev) > 10:
                        st.caption(f"... e mais {len(sem_ev) - 10}")
                else:
                    st.success("✅ Todos os contactos têm evidência.")

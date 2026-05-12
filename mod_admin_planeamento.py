import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, timedelta, date
from core import save_db, inv, load_db

def render_planeamento():
    st.markdown("### 📋 Planeamento e Engenharia")

    try:
        pacotes_db = load_db("planeamento_pacotes.csv", [
            "ID","Obra","Frente","Descricao","Horas_Plan",
            "Horas_Reais","Data_Inicio","Data_Fim","Status","Criado_Por"
        ], silent=True)
    except:
        pacotes_db = pd.DataFrame(columns=[
            "ID","Obra","Frente","Descricao","Horas_Plan",
            "Horas_Reais","Data_Inicio","Data_Fim","Status","Criado_Por"
        ])

    try:
        milestones_db = load_db("planeamento_milestones.csv", [
            "ID","Obra","Descricao","Data_Alvo","Responsavel","Status"
        ], silent=True)
    except:
        milestones_db = pd.DataFrame(columns=[
            "ID","Obra","Descricao","Data_Alvo","Responsavel","Status"
        ])

    try:
        desenhos_db = load_db("planeamento_desenhos.csv", [
            "ID","Obra","Tipo","Revisao","Ficheiro_b64","Data_Upload","Upload_Por"
        ], silent=True)
    except:
        desenhos_db = pd.DataFrame(columns=[
            "ID","Obra","Tipo","Revisao","Ficheiro_b64","Data_Upload","Upload_Por"
        ])

    user_nome = st.session_state.get('user', 'Admin')

    tab_producao, tab_cronograma, tab_recursos, tab_desenhos = st.tabs([
        "🏭 Produção", "📅 Cronograma", "👷 Recursos", "📐 Desenhos"
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB PRODUÇÃO
    # ════════════════════════════════════════════════════════════════
    with tab_producao:
        st.markdown("### 🏭 Produção e Progresso")

        if not pacotes_db.empty:
            total_plan  = pd.to_numeric(pacotes_db['Horas_Plan'],  errors='coerce').fillna(0).sum()
            total_reais = pd.to_numeric(pacotes_db['Horas_Reais'], errors='coerce').fillna(0).sum()
            prod = round((total_reais / total_plan * 100), 1) if total_plan > 0 else 0
            ativos = len(pacotes_db[pacotes_db['Status'] == 'Em Curso'])
        else:
            total_plan = total_reais = prod = ativos = 0

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("📋 Pacotes Ativos",   ativos)
        with c2: st.metric("⏱️ Horas Planeadas",  f"{total_plan:.0f}h")
        with c3: st.metric("⏱️ Horas Reais",      f"{total_reais:.0f}h")
        with c4: st.metric("📈 Produtividade",    f"{prod:.0f}%")

        st.divider()

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("#### ➕ Novo Pacote de Trabalho")
            with st.form("form_pacote"):
                obra_p      = st.text_input("Obra *", key="prod_obra")
                frente_p    = st.text_input("Frente", key="prod_frente")
                desc_p      = st.text_area("Descrição *", key="prod_desc")
                horas_plan  = st.number_input(
                    "Horas Planeadas", min_value=0, value=0, key="prod_horas"
                )
                col_di, col_df = st.columns(2)
                with col_di:
                    data_ini = st.date_input(
                        "Início", value=date.today(), key="prod_ini"
                    )
                with col_df:
                    data_fim = st.date_input(
                        "Fim", value=date.today() + timedelta(days=30),
                        key="prod_fim"
                    )
                status_p = st.selectbox(
                    "Estado",
                    ["Planeado","Em Curso","Concluído","Suspenso"],
                    key="prod_status"
                )

                if st.form_submit_button(
                    "💾 Criar Pacote",
                    use_container_width=True, type="primary"
                ):
                    if not obra_p.strip() or not desc_p.strip():
                        st.error("❌ Obra e Descrição obrigatórios.")
                    else:
                        novo_p = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Obra":        obra_p.strip(),
                            "Frente":      frente_p.strip(),
                            "Descricao":   desc_p.strip(),
                            "Horas_Plan":  horas_plan,
                            "Horas_Reais": 0,
                            "Data_Inicio": data_ini.strftime("%d/%m/%Y"),
                            "Data_Fim":    data_fim.strftime("%d/%m/%Y"),
                            "Status":      status_p,
                            "Criado_Por":  user_nome
                        }])
                        updated_p = pd.concat(
                            [pacotes_db, novo_p], ignore_index=True
                        ) if not pacotes_db.empty else novo_p
                        save_db(updated_p, "planeamento_pacotes.csv")
                        inv()
                        st.success(f"✅ Pacote criado: {desc_p[:30]}")
                        st.rerun()

        with col2:
            st.markdown("#### 📋 Pacotes de Trabalho")
            if pacotes_db.empty:
                st.info("📋 Sem pacotes criados.")
            else:
                # Filtro por estado
                estados_f = ["Todos"] + pacotes_db['Status'].unique().tolist()
                filtro_est = st.selectbox(
                    "Filtrar por estado", estados_f, key="pac_filtro"
                )
                df_pac = pacotes_db.copy()
                if filtro_est != "Todos":
                    df_pac = df_pac[df_pac['Status'] == filtro_est]

                for _, pac in df_pac.iterrows():
                    pac_id = pac.get('ID','')
                    h_plan  = float(pac.get('Horas_Plan',0)  or 0)
                    h_reais = float(pac.get('Horas_Reais',0) or 0)
                    pct     = round(h_reais/h_plan*100,0) if h_plan > 0 else 0
                    cor_s   = {
                        "Em Curso":"#3B82F6","Concluído":"#10B981",
                        "Suspenso":"#EF4444","Planeado":"#F59E0B"
                    }.get(pac.get('Status',''),"#6B7280")

                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin-bottom:8px;"
                        f"border-left:4px solid {cor_s};'>"
                        f"<b style='color:#F1F5F9;'>{pac.get('Descricao','')[:50]}</b>"
                        f"<span style='float:right;color:{cor_s};font-size:0.8rem;'>"
                        f"{pac.get('Status','')}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"{pac.get('Obra','')} · {pac.get('Frente','')} · "
                        f"{h_reais:.0f}h/{h_plan:.0f}h ({pct:.0f}%) · "
                        f"{pac.get('Data_Inicio','')}→{pac.get('Data_Fim','')}"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

                    # Atualizar horas reais
                    col_hr, col_st = st.columns([2, 2])
                    with col_hr:
                        novas_h = st.number_input(
                            "Horas reais",
                            min_value=0.0,
                            value=h_reais,
                            step=0.5,
                            key=f"hr_{pac_id}",
                            label_visibility="collapsed"
                        )
                    with col_st:
                        novo_st = st.selectbox(
                            "Estado",
                            ["Planeado","Em Curso","Concluído","Suspenso"],
                            index=["Planeado","Em Curso","Concluído","Suspenso"].index(
                                pac.get('Status','Planeado')
                            ) if pac.get('Status') in
                            ["Planeado","Em Curso","Concluído","Suspenso"] else 0,
                            key=f"st_{pac_id}",
                            label_visibility="collapsed"
                        )
                    if st.button("✅ Guardar", key=f"save_pac_{pac_id}",
                                  use_container_width=True):
                        pacotes_db.loc[pacotes_db['ID'] == pac_id, 'Horas_Reais'] = novas_h
                        pacotes_db.loc[pacotes_db['ID'] == pac_id, 'Status']      = novo_st
                        save_db(pacotes_db, "planeamento_pacotes.csv")
                        inv()
                        st.success("✅ Atualizado!")
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB CRONOGRAMA
    # ════════════════════════════════════════════════════════════════
    with tab_cronograma:
        st.markdown("### 📅 Cronograma e Milestones")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("#### ➕ Novo Milestone")
            with st.form("form_milestone"):
                obra_m  = st.text_input("Obra *",        key="mile_obra")
                desc_m  = st.text_input("Descrição *",   key="mile_desc")
                data_m  = st.date_input("Data Alvo",     key="mile_data",
                                         value=date.today() + timedelta(days=30))
                resp_m  = st.text_input("Responsável",   key="mile_resp")
                status_m = st.selectbox(
                    "Estado",
                    ["Pendente","Em Risco","Concluído"],
                    key="mile_status"
                )

                if st.form_submit_button(
                    "💾 Criar Milestone",
                    use_container_width=True, type="primary"
                ):
                    if not obra_m.strip() or not desc_m.strip():
                        st.error("❌ Obra e Descrição obrigatórios.")
                    else:
                        novo_m = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Obra":        obra_m.strip(),
                            "Descricao":   desc_m.strip(),
                            "Data_Alvo":   data_m.strftime("%d/%m/%Y"),
                            "Responsavel": resp_m.strip(),
                            "Status":      status_m
                        }])
                        updated_m = pd.concat(
                            [milestones_db, novo_m], ignore_index=True
                        ) if not milestones_db.empty else novo_m
                        save_db(updated_m, "planeamento_milestones.csv")
                        inv()
                        st.success(f"✅ Milestone criado!")
                        st.rerun()

        with col2:
            st.markdown("#### 📋 Milestones")
            if milestones_db.empty:
                st.info("📋 Sem milestones.")
            else:
                for _, ms in milestones_db.sort_values(
                    'Data_Alvo', ascending=True
                ).iterrows():
                    ms_id  = ms.get('ID','')
                    cor_ms = {
                        "Concluído":"#10B981",
                        "Em Risco": "#EF4444",
                        "Pendente": "#F59E0B"
                    }.get(ms.get('Status',''),"#6B7280")
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin-bottom:8px;"
                        f"border-left:4px solid {cor_ms};'>"
                        f"<b style='color:#F1F5F9;'>{ms.get('Descricao','')}</b>"
                        f"<span style='float:right;color:{cor_ms};'>"
                        f"{ms.get('Status','')}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"{ms.get('Obra','')} · {ms.get('Data_Alvo','')} · "
                        f"{ms.get('Responsavel','')}</small></div>",
                        unsafe_allow_html=True
                    )
                    col_ms_s, col_ms_d = st.columns([3, 1])
                    with col_ms_s:
                        novo_ms_st = st.selectbox(
                            "Estado",
                            ["Pendente","Em Risco","Concluído"],
                            index=["Pendente","Em Risco","Concluído"].index(
                                ms.get('Status','Pendente')
                            ) if ms.get('Status') in
                            ["Pendente","Em Risco","Concluído"] else 0,
                            key=f"ms_st_{ms_id}",
                            label_visibility="collapsed"
                        )
                    with col_ms_d:
                        if st.button("✅", key=f"ms_save_{ms_id}",
                                      use_container_width=True):
                            milestones_db.loc[
                                milestones_db['ID'] == ms_id, 'Status'
                            ] = novo_ms_st
                            save_db(milestones_db, "planeamento_milestones.csv")
                            inv()
                            st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB RECURSOS
    # ════════════════════════════════════════════════════════════════
    with tab_recursos:
        st.markdown("### 👷 Planeamento de Recursos")

        if not pacotes_db.empty:
            obras_pac = pacotes_db['Obra'].unique().tolist()
            obra_rec  = st.selectbox("Obra", obras_pac, key="rec_obra")
            df_rec    = pacotes_db[pacotes_db['Obra'] == obra_rec]

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("📋 Pacotes", len(df_rec))
            with c2:
                h_plan_r = pd.to_numeric(
                    df_rec['Horas_Plan'], errors='coerce'
                ).fillna(0).sum()
                st.metric("⏱️ Horas Planeadas", f"{h_plan_r:.0f}h")
            with c3:
                h_reais_r = pd.to_numeric(
                    df_rec['Horas_Reais'], errors='coerce'
                ).fillna(0).sum()
                st.metric("⏱️ Horas Reais", f"{h_reais_r:.0f}h")

            st.dataframe(
                df_rec[['Frente','Descricao','Horas_Plan',
                         'Horas_Reais','Status']],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("📋 Sem pacotes de trabalho criados.")

    # ════════════════════════════════════════════════════════════════
    # TAB DESENHOS
    # ════════════════════════════════════════════════════════════════
    with tab_desenhos:
        st.markdown("### 📐 Gestão de Desenhos Técnicos")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("#### ➕ Upload de Desenho")
            with st.form("form_desenho"):
                obra_d    = st.text_input("Obra *", key="des_obra")
                tipo_d    = st.selectbox(
                    "Tipo",
                    ["P&ID","Layout","Esquemático","Isométrico","Outro"],
                    key="des_tipo"
                )
                revisao_d  = st.text_input("Revisão", key="des_rev",
                                            placeholder="Rev A")
                ficheiro_d = st.file_uploader(
                    "Ficheiro (PDF, DWG, DXF)",
                    type=["pdf","dwg","dxf"],
                    key="des_file"
                )

                if st.form_submit_button(
                    "💾 Upload", use_container_width=True, type="primary"
                ):
                    if not obra_d.strip():
                        st.error("❌ Obra obrigatória.")
                    elif not ficheiro_d:
                        st.error("❌ Seleciona um ficheiro.")
                    else:
                        import base64 as _b64
                        f_b64 = _b64.b64encode(
                            ficheiro_d.read()
                        ).decode('utf-8')
                        novo_d = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Obra":        obra_d.strip(),
                            "Tipo":        tipo_d,
                            "Revisao":     revisao_d.strip(),
                            "Ficheiro_b64":f_b64[:100],  # preview
                            "Data_Upload": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Upload_Por":  user_nome
                        }])
                        updated_d = pd.concat(
                            [desenhos_db, novo_d], ignore_index=True
                        ) if not desenhos_db.empty else novo_d
                        save_db(updated_d, "planeamento_desenhos.csv")
                        inv()
                        st.success(
                            f"✅ Desenho carregado: {ficheiro_d.name}"
                        )
                        st.rerun()

        with col2:
            st.markdown("#### 📋 Biblioteca de Desenhos")
            if desenhos_db.empty:
                st.info("📋 Sem desenhos carregados.")
            else:
                cols_d = [c for c in [
                    'Obra','Tipo','Revisao','Data_Upload','Upload_Por'
                ] if c in desenhos_db.columns]
                st.dataframe(
                    desenhos_db[cols_d],
                    use_container_width=True, hide_index=True
                )

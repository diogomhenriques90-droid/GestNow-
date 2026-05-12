import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date
from core import save_db, inv, load_db

def render_dormidas():
    st.markdown("### 🏨 Gestão de Dormidas")

    try:
        dormidas_db = load_db("dormidas.csv", [
            "ID","Data_Entrada","Data_Saida","Trabalhador","Obra",
            "Hotel","Cidade","Custo_Noite","Noites","Total",
            "Registado_Por","Recibo_b64"
        ], silent=True)
    except:
        dormidas_db = pd.DataFrame(columns=[
            "ID","Data_Entrada","Data_Saida","Trabalhador","Obra",
            "Hotel","Cidade","Custo_Noite","Noites","Total",
            "Registado_Por","Recibo_b64"
        ])

    try:
        from core import load_db as _ld
        users_db = _ld("usuarios.csv", ["Nome","Tipo","Cargo"], silent=True)
    except:
        users_db = pd.DataFrame(columns=["Nome","Tipo","Cargo"])

    try:
        obras_db = load_db("obras_lista.csv",
                           ["Obra","Cliente","Ativa"], silent=True)
    except:
        obras_db = pd.DataFrame(columns=["Obra","Cliente","Ativa"])

    user_nome = st.session_state.get('user', 'Admin')

    tab_registar, tab_pesquisar, tab_historico = st.tabs([
        "📝 Registar", "🤖 IA Pesquisa Hotéis", "📋 Histórico"
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB REGISTAR
    # ════════════════════════════════════════════════════════════════
    with tab_registar:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("#### ➕ Nova Dormida")

            users_lista = users_db['Nome'].tolist() \
                          if not users_db.empty else []
            obras_lista = obras_db[
                obras_db['Ativa'] == 'Ativa'
            ]['Obra'].tolist() if not obras_db.empty else []

            with st.form("form_dormida"):
                trabalhador = st.selectbox(
                    "Trabalhador *",
                    users_lista if users_lista else ["Sem utilizadores"],
                    key="dorm_trab"
                )
                obra_d = st.selectbox(
                    "Obra *",
                    obras_lista if obras_lista else ["Sem obras"],
                    key="dorm_obra"
                )
                hotel   = st.text_input("Hotel *", key="dorm_hotel")
                cidade  = st.text_input("Cidade",  key="dorm_cidade")

                col_e, col_s = st.columns(2)
                with col_e:
                    data_ent = st.date_input(
                        "Entrada", value=date.today(),
                        key="dorm_entrada"
                    )
                with col_s:
                    data_sai = st.date_input(
                        "Saída",
                        value=date.today(),
                        key="dorm_saida"
                    )

                custo_noite = st.number_input(
                    "Custo por Noite (€)",
                    min_value=0.0, value=0.0,
                    step=5.0, key="dorm_custo"
                )
                recibo_d = st.file_uploader(
                    "Recibo/Fatura (PDF ou foto)",
                    type=["pdf","jpg","jpeg","png"],
                    key="dorm_recibo"
                )

                if st.form_submit_button(
                    "💾 Registar Dormida",
                    use_container_width=True, type="primary"
                ):
                    if not hotel.strip():
                        st.error("❌ Hotel obrigatório.")
                    else:
                        noites = max((data_sai - data_ent).days, 1)
                        total  = round(noites * custo_noite, 2)
                        rec_b64 = ""
                        if recibo_d:
                            import base64
                            rec_b64 = base64.b64encode(
                                recibo_d.read()
                            ).decode()
                        nova_d = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Data_Entrada": data_ent.strftime("%d/%m/%Y"),
                            "Data_Saida":   data_sai.strftime("%d/%m/%Y"),
                            "Trabalhador":  trabalhador,
                            "Obra":         obra_d,
                            "Hotel":        hotel.strip(),
                            "Cidade":       cidade.strip(),
                            "Custo_Noite":  custo_noite,
                            "Noites":       noites,
                            "Total":        total,
                            "Registado_Por":user_nome,
                            "Recibo_b64":   rec_b64
                        }])
                        updated_d = pd.concat(
                            [dormidas_db, nova_d], ignore_index=True
                        ) if not dormidas_db.empty else nova_d
                        save_db(updated_d, "dormidas.csv")
                        inv()
                        st.success(
                            f"✅ Dormida registada! "
                            f"{noites} noite(s) em {hotel} — € {total:.2f}"
                        )
                        st.rerun()

        with col2:
            st.markdown("#### 📋 Dormidas Registadas")
            if dormidas_db.empty:
                st.info("📋 Sem dormidas registadas.")
            else:
                total_geral = pd.to_numeric(
                    dormidas_db['Total'], errors='coerce'
                ).fillna(0).sum()
                c1, c2 = st.columns(2)
                with c1: st.metric("📋 Registos",   len(dormidas_db))
                with c2: st.metric("💰 Total Gasto", f"€ {total_geral:.2f}")

                # Filtro por obra
                obras_filt = ["Todas"] + dormidas_db['Obra'].unique().tolist()
                obra_filt  = st.selectbox(
                    "Filtrar por obra", obras_filt, key="dorm_filt"
                )
                df_show = dormidas_db.copy()
                if obra_filt != "Todas":
                    df_show = df_show[df_show['Obra'] == obra_filt]

                cols_d = [c for c in [
                    'Data_Entrada','Data_Saida','Trabalhador',
                    'Obra','Hotel','Cidade','Noites','Total'
                ] if c in df_show.columns]
                st.dataframe(
                    df_show[cols_d].sort_values(
                        'Data_Entrada', ascending=False
                    ),
                    use_container_width=True, hide_index=True
                )

    # ════════════════════════════════════════════════════════════════
    # TAB IA PESQUISA HOTÉIS
    # ════════════════════════════════════════════════════════════════
    with tab_pesquisar:
        st.markdown("#### 🤖 Pesquisa de Hotéis com IA")
        st.info(
            "A IA pesquisa e sugere hotéis próximos da obra, "
            "com estimativas de preço e distância."
        )

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            local_pesq = st.text_input(
                "Localização / Obra *",
                key="pesq_local",
                placeholder="Ex: Sines, Portugal"
            )
            raio = st.slider(
                "Raio de busca (km)", 1, 50, 15, key="pesq_raio"
            )
        with col_p2:
            noites_pesq = st.number_input(
                "Nº de noites", min_value=1, value=5, key="pesq_noites"
            )
            n_pessoas = st.number_input(
                "Nº de pessoas", min_value=1, value=1, key="pesq_pessoas"
            )

        orcamento = st.number_input(
            "Orçamento máximo por noite (€)",
            min_value=0.0, value=80.0, step=10.0,
            key="pesq_orcamento"
        )

        if st.button(
            "🔍 Pesquisar Hotéis com IA",
            key="btn_pesq_hotel", type="primary",
            use_container_width=True
        ):
            if not local_pesq.strip():
                st.error("❌ Indica a localização.")
            else:
                import os, anthropic, json
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                if not api_key:
                    st.error("❌ API key não configurada.")
                else:
                    with st.spinner(
                        f"🤖 A pesquisar hotéis perto de {local_pesq}..."
                    ):
                        try:
                            client = anthropic.Anthropic(api_key=api_key)
                            prompt = f"""És um assistente especializado em alojamento para trabalhadores de construção e instrumentação industrial em Portugal.

Pesquisa hotéis e alojamentos próximos de: "{local_pesq}" (raio: {raio}km)
Para: {n_pessoas} pessoa(s), {noites_pesq} noite(s), orçamento máximo: €{orcamento}/noite

Sugere 4 opções realistas de alojamento em Portugal com:
- Nome do hotel/residencial
- Cidade/localidade
- Distância estimada ao local de obra
- Preço estimado por noite em €
- Tipo (Hotel, Residencial, Apartamento, Pensão)
- Adequabilidade para trabalhadores (sim/não + motivo)

Responde APENAS em JSON:
{{
  "local": "{local_pesq}",
  "hoteis": [
    {{
      "nome": "...",
      "cidade": "...",
      "distancia_km": 5,
      "preco_noite": 65.00,
      "tipo": "Hotel",
      "adequado": true,
      "motivo": "...",
      "total_estimado": 325.00
    }}
  ]
}}"""

                            resp = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=1200,
                                messages=[{"role":"user","content":prompt}]
                            )
                            raw = resp.content[0].text.strip()
                            raw = raw.replace("```json","").replace("```","").strip()
                            dados = json.loads(raw)
                            hoteis = dados.get("hoteis", [])

                            st.success(
                                f"✅ {len(hoteis)} opção(ões) encontrada(s) "
                                f"perto de {local_pesq}!"
                            )

                            for h in hoteis:
                                preco = h.get('preco_noite', 0)
                                total_h = round(preco * noites_pesq * n_pessoas, 2)
                                adequado = h.get('adequado', True)
                                cor_h = "#10B981" if adequado else "#F59E0B"
                                dentro_orcamento = preco <= orcamento

                                st.markdown(
                                    f"<div style='background:#1E293B;"
                                    f"border-radius:12px;padding:16px;"
                                    f"margin-bottom:10px;"
                                    f"border-left:4px solid {cor_h};'>"
                                    f"<b style='color:#F1F5F9;font-size:1rem;'>"
                                    f"{'✅' if adequado else '⚠️'} "
                                    f"{h.get('nome','')}</b>"
                                    f"<span style='float:right;"
                                    f"color:{'#10B981' if dentro_orcamento else '#EF4444'};"
                                    f"font-weight:700;font-size:1.1rem;'>"
                                    f"€ {preco:.2f}/noite</span><br>"
                                    f"<small style='color:#64748B;'>"
                                    f"📍 {h.get('cidade','')} · "
                                    f"🚗 {h.get('distancia_km','')}km · "
                                    f"🏨 {h.get('tipo','')}</small><br>"
                                    f"<small style='color:#94A3B8;'>"
                                    f"{h.get('motivo','')}</small><br>"
                                    f"<small style='color:#3B82F6;'>"
                                    f"💰 Total estimado "
                                    f"({noites_pesq}n × {n_pessoas}p): "
                                    f"<b>€ {total_h:.2f}</b></small>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )

                                # Botão registar diretamente
                                if st.button(
                                    f"📝 Registar {h.get('nome','')}",
                                    key=f"reg_hotel_{h.get('nome','').replace(' ','_')[:20]}",
                                    use_container_width=True
                                ):
                                    st.session_state['hotel_pre_fill'] = h
                                    st.session_state['hotel_pre_noites'] = noites_pesq
                                    st.info(
                                        "✅ Dados pré-preenchidos! "
                                        "Vai ao tab 📝 Registar para confirmar."
                                    )

                        except json.JSONDecodeError:
                            st.error("❌ Erro ao interpretar resposta da IA.")
                        except Exception as e:
                            st.error(f"❌ Erro: {e}")

    # ════════════════════════════════════════════════════════════════
    # TAB HISTÓRICO
    # ════════════════════════════════════════════════════════════════
    with tab_historico:
        st.markdown("#### 📋 Histórico de Dormidas")

        if dormidas_db.empty:
            st.info("📋 Sem histórico.")
        else:
            # Filtros
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1:
                obras_h = ["Todas"] + dormidas_db['Obra'].unique().tolist()
                obra_h  = st.selectbox("Obra", obras_h, key="hist_dorm_obra")
            with col_h2:
                trabs_h = ["Todos"] + dormidas_db['Trabalhador'].unique().tolist()
                trab_h  = st.selectbox(
                    "Trabalhador", trabs_h, key="hist_dorm_trab"
                )
            with col_h3:
                st.markdown(
                    "<div style='height:28px;'></div>",
                    unsafe_allow_html=True
                )

            df_hist = dormidas_db.copy()
            if obra_h != "Todas":
                df_hist = df_hist[df_hist['Obra'] == obra_h]
            if trab_h != "Todos":
                df_hist = df_hist[df_hist['Trabalhador'] == trab_h]

            total_hist = pd.to_numeric(
                df_hist['Total'], errors='coerce'
            ).fillna(0).sum()
            total_noites = pd.to_numeric(
                df_hist['Noites'], errors='coerce'
            ).fillna(0).sum()

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("📋 Registos",    len(df_hist))
            with c2: st.metric("🌙 Noites",       int(total_noites))
            with c3: st.metric("💰 Total",        f"€ {total_hist:.2f}")

            cols_h = [c for c in [
                'Data_Entrada','Data_Saida','Trabalhador',
                'Obra','Hotel','Cidade','Noites','Total'
            ] if c in df_hist.columns]
            st.dataframe(
                df_hist[cols_h].sort_values(
                    'Data_Entrada', ascending=False
                ),
                use_container_width=True, hide_index=True
            )

            # Export
            csv_dorm = df_hist[cols_h].to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Exportar CSV",
                data=csv_dorm.encode('utf-8-sig'),
                file_name="dormidas_historico.csv",
                mime="text/csv",
                key="export_dorm_hist"
            )

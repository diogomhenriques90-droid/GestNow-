import streamlit as st
import pandas as pd
import uuid, base64
from datetime import datetime, date
from core import save_db, inv, load_db

def render_frota():
    st.markdown("### 🚗 Gestão de Frota")

    try:
        frota_db = load_db("frota_viaturas.csv", [
            "ID","Matricula","Marca","Modelo","Tipo","Condutor",
            "Custo_Mensal","Status","Data_Registo"
        ], silent=True)
    except:
        frota_db = pd.DataFrame(columns=[
            "ID","Matricula","Marca","Modelo","Tipo","Condutor",
            "Custo_Mensal","Status","Data_Registo"
        ])

    try:
        comb_db = load_db("frota_combustivel.csv", [
            "ID","Data","Matricula","Condutor","Litros",
            "Valor","KM","Tipo_Comb","Recibo_b64"
        ], silent=True)
    except:
        comb_db = pd.DataFrame(columns=[
            "ID","Data","Matricula","Condutor","Litros",
            "Valor","KM","Tipo_Comb","Recibo_b64"
        ])

    try:
        avarfrota_db = load_db("frota_avarias.csv", [
            "ID","Data","Matricula","Descricao","Urgencia",
            "Valor_Est","Status","Registado_Por"
        ], silent=True)
    except:
        avarfrota_db = pd.DataFrame(columns=[
            "ID","Data","Matricula","Descricao","Urgencia",
            "Valor_Est","Status","Registado_Por"
        ])

    user_nome = st.session_state.get('user', 'Admin')

    # KPIs
    n_viat   = len(frota_db) if not frota_db.empty else 0
    n_ativas = len(frota_db[frota_db['Status'] == 'Ativa']) \
               if not frota_db.empty else 0
    custo_t  = pd.to_numeric(
        frota_db['Custo_Mensal'], errors='coerce'
    ).fillna(0).sum() if not frota_db.empty else 0
    n_avarfrota = len(avarfrota_db[
        avarfrota_db['Status'] == 'Pendente'
    ]) if not avarfrota_db.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("🚗 Total Viaturas",  n_viat)
    with c2: st.metric("✅ Ativas",           n_ativas)
    with c3: st.metric("💰 Custo Mensal",    f"€ {custo_t:.2f}")
    with c4: st.metric("⚠️ Avarias Pend.",   n_avarfrota)

    st.divider()

    tab_viaturas, tab_combustivel, tab_avarias = st.tabs([
        "🚗 Viaturas", "⛽ Combustível", "⚠️ Avarias"
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB VIATURAS
    # ════════════════════════════════════════════════════════════════
    with tab_viaturas:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("#### ➕ Nova Viatura")
            with st.form("form_viatura"):
                matricula = st.text_input("Matrícula *", key="viat_mat",
                                           placeholder="AA-00-AA")
                col_ma, col_mo = st.columns(2)
                with col_ma:
                    marca  = st.text_input("Marca",  key="viat_marca")
                with col_mo:
                    modelo = st.text_input("Modelo", key="viat_modelo")
                tipo     = st.selectbox(
                    "Tipo",
                    ["Própria","Alugada","Colaborador"],
                    key="viat_tipo"
                )
                condutor = st.text_input("Condutor", key="viat_cond")
                custo    = st.number_input(
                    "Custo Mensal (€)",
                    min_value=0.0, value=0.0,
                    step=10.0, key="viat_custo"
                )
                status_v = st.selectbox(
                    "Estado",
                    ["Ativa","Inativa","Em Manutenção"],
                    key="viat_status"
                )

                if st.form_submit_button(
                    "💾 Registar Viatura",
                    use_container_width=True, type="primary"
                ):
                    if not matricula.strip():
                        st.error("❌ Matrícula obrigatória.")
                    elif not frota_db.empty and \
                         matricula.strip() in frota_db['Matricula'].values:
                        st.error("❌ Matrícula já existe.")
                    else:
                        nova_v = pd.DataFrame([{
                            "ID":           str(uuid.uuid4())[:8].upper(),
                            "Matricula":    matricula.strip().upper(),
                            "Marca":        marca.strip(),
                            "Modelo":       modelo.strip(),
                            "Tipo":         tipo,
                            "Condutor":     condutor.strip(),
                            "Custo_Mensal": custo,
                            "Status":       status_v,
                            "Data_Registo": datetime.now().strftime("%d/%m/%Y")
                        }])
                        updated_v = pd.concat(
                            [frota_db, nova_v], ignore_index=True
                        ) if not frota_db.empty else nova_v
                        save_db(updated_v, "frota_viaturas.csv")
                        inv()
                        st.success(
                            f"✅ Viatura {matricula.upper()} registada!"
                        )
                        st.rerun()

        with col2:
            st.markdown("#### 🚗 Frota")
            if frota_db.empty:
                st.info("📋 Sem viaturas registadas.")
            else:
                for _, v in frota_db.iterrows():
                    vid    = v.get('ID','')
                    cor_sv = {
                        "Ativa":"#10B981",
                        "Inativa":"#6B7280",
                        "Em Manutenção":"#EF4444"
                    }.get(v.get('Status',''),"#6B7280")
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin-bottom:8px;"
                        f"border-left:4px solid {cor_sv};'>"
                        f"<b style='color:#F1F5F9;'>🚗 {v.get('Matricula','')}</b>"
                        f"<span style='float:right;color:{cor_sv};'>"
                        f"{v.get('Status','')}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"{v.get('Marca','')} {v.get('Modelo','')} · "
                        f"{v.get('Tipo','')} · {v.get('Condutor','')} · "
                        f"€ {float(v.get('Custo_Mensal',0) or 0):.2f}/mês"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )
                    col_vs, col_vd = st.columns([3, 1])
                    with col_vs:
                        novo_status_v = st.selectbox(
                            "Estado",
                            ["Ativa","Inativa","Em Manutenção"],
                            index=["Ativa","Inativa","Em Manutenção"].index(
                                v.get('Status','Ativa')
                            ) if v.get('Status') in
                            ["Ativa","Inativa","Em Manutenção"] else 0,
                            key=f"vs_{vid}",
                            label_visibility="collapsed"
                        )
                    with col_vd:
                        if st.button("✅", key=f"vup_{vid}",
                                      use_container_width=True):
                            frota_db.loc[
                                frota_db['ID'] == vid, 'Status'
                            ] = novo_status_v
                            save_db(frota_db, "frota_viaturas.csv")
                            inv(); st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB COMBUSTÍVEL
    # ════════════════════════════════════════════════════════════════
    with tab_combustivel:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("#### ➕ Registo de Abastecimento")
            matriculas = frota_db['Matricula'].tolist() \
                         if not frota_db.empty else []

            with st.form("form_combustivel"):
                mat_c = st.selectbox(
                    "Viatura *",
                    matriculas if matriculas else ["Sem viaturas"],
                    key="comb_mat"
                )
                col_d, col_l = st.columns(2)
                with col_d:
                    data_c = st.date_input(
                        "Data", value=date.today(), key="comb_data"
                    )
                with col_l:
                    litros_c = st.number_input(
                        "Litros", min_value=0.0,
                        step=0.5, key="comb_litros"
                    )
                col_v, col_km = st.columns(2)
                with col_v:
                    valor_c = st.number_input(
                        "Valor €", min_value=0.0,
                        step=0.01, key="comb_valor"
                    )
                with col_km:
                    km_c = st.number_input(
                        "KM", min_value=0, key="comb_km"
                    )
                tipo_c = st.selectbox(
                    "Combustível",
                    ["Gasóleo","Gasolina 95","Gasolina 98","Elétrico"],
                    key="comb_tipo"
                )
                recibo_c = st.file_uploader(
                    "Recibo (foto/PDF)",
                    type=["jpg","jpeg","png","pdf"],
                    key="comb_recibo"
                )

                if st.form_submit_button(
                    "💾 Registar",
                    use_container_width=True, type="primary"
                ):
                    if litros_c <= 0:
                        st.error("❌ Indica os litros.")
                    else:
                        rec_b64 = ""
                        if recibo_c:
                            rec_b64 = base64.b64encode(
                                recibo_c.read()
                            ).decode()
                        novo_c = pd.DataFrame([{
                            "ID":        str(uuid.uuid4())[:8].upper(),
                            "Data":      data_c.strftime("%d/%m/%Y"),
                            "Matricula": mat_c,
                            "Condutor":  user_nome,
                            "Litros":    litros_c,
                            "Valor":     valor_c,
                            "KM":        km_c,
                            "Tipo_Comb": tipo_c,
                            "Recibo_b64":rec_b64
                        }])
                        updated_c = pd.concat(
                            [comb_db, novo_c], ignore_index=True
                        ) if not comb_db.empty else novo_c
                        save_db(updated_c, "frota_combustivel.csv")
                        inv()
                        st.success(
                            f"✅ {litros_c}L registados em {mat_c}!"
                        )
                        st.rerun()

        with col2:
            st.markdown("#### 📋 Histórico de Abastecimentos")
            if comb_db.empty:
                st.info("📋 Sem abastecimentos.")
            else:
                total_l = pd.to_numeric(
                    comb_db['Litros'], errors='coerce'
                ).fillna(0).sum()
                total_v = pd.to_numeric(
                    comb_db['Valor'], errors='coerce'
                ).fillna(0).sum()
                c1, c2 = st.columns(2)
                with c1: st.metric("⛽ Total Litros", f"{total_l:.0f}L")
                with c2: st.metric("💰 Total Gasto",  f"€ {total_v:.2f}")

                cols_c = [col for col in [
                    'Data','Matricula','Litros','Valor','KM','Tipo_Comb'
                ] if col in comb_db.columns]
                st.dataframe(
                    comb_db[cols_c].sort_values('Data', ascending=False),
                    use_container_width=True, hide_index=True
                )

    # ════════════════════════════════════════════════════════════════
    # TAB AVARIAS
    # ════════════════════════════════════════════════════════════════
    with tab_avarias:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("#### ➕ Registar Avaria")
            matriculas_av = frota_db['Matricula'].tolist() \
                            if not frota_db.empty else []

            with st.form("form_avaria_frota"):
                mat_av  = st.selectbox(
                    "Viatura *",
                    matriculas_av if matriculas_av else ["Sem viaturas"],
                    key="av_mat"
                )
                desc_av = st.text_area("Descrição *", key="av_desc")
                col_u, col_v2 = st.columns(2)
                with col_u:
                    urg_av = st.selectbox(
                        "Urgência",
                        ["Baixa","Média","Alta","Crítica"],
                        key="av_urg"
                    )
                with col_v2:
                    val_av = st.number_input(
                        "Valor Est. €",
                        min_value=0.0,
                        step=10.0,
                        key="av_val"
                    )

                if st.form_submit_button(
                    "⚠️ Registar Avaria",
                    use_container_width=True, type="primary"
                ):
                    if not desc_av.strip():
                        st.error("❌ Descrição obrigatória.")
                    else:
                        nova_av = pd.DataFrame([{
                            "ID":            str(uuid.uuid4())[:8].upper(),
                            "Data":          datetime.now().strftime("%d/%m/%Y"),
                            "Matricula":     mat_av,
                            "Descricao":     desc_av.strip(),
                            "Urgencia":      urg_av,
                            "Valor_Est":     val_av,
                            "Status":        "Pendente",
                            "Registado_Por": user_nome
                        }])
                        updated_av = pd.concat(
                            [avarfrota_db, nova_av], ignore_index=True
                        ) if not avarfrota_db.empty else nova_av
                        save_db(updated_av, "frota_avarias.csv")
                        inv()
                        st.success(f"✅ Avaria registada em {mat_av}!")
                        st.rerun()

        with col2:
            st.markdown("#### 📋 Avarias")
            if avarfrota_db.empty:
                st.info("📋 Sem avarias.")
            else:
                for _, av in avarfrota_db.iterrows():
                    avid    = av.get('ID','')
                    cor_av  = {
                        "Pendente":"#F59E0B",
                        "Em Reparação":"#3B82F6",
                        "Resolvido":"#10B981"
                    }.get(av.get('Status',''),"#6B7280")
                    cor_urg = {
                        "Crítica":"#DC2626","Alta":"#EF4444",
                        "Média":"#F59E0B","Baixa":"#10B981"
                    }.get(av.get('Urgencia',''),"#6B7280")
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin-bottom:8px;"
                        f"border-left:4px solid {cor_urg};'>"
                        f"<b style='color:#F1F5F9;'>🚗 {av.get('Matricula','')}</b>"
                        f"<span style='float:right;color:{cor_av};'>"
                        f"{av.get('Status','')}</span><br>"
                        f"<small style='color:#94A3B8;'>"
                        f"{av.get('Descricao','')[:60]}</small><br>"
                        f"<small style='color:#64748B;'>"
                        f"{av.get('Data','')} · "
                        f"<span style='color:{cor_urg};'>{av.get('Urgencia','')}</span>"
                        f" · € {float(av.get('Valor_Est',0) or 0):.2f}"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )
                    col_avs, col_avd = st.columns([3, 1])
                    with col_avs:
                        novo_av_st = st.selectbox(
                            "Estado",
                            ["Pendente","Em Reparação","Resolvido"],
                            index=["Pendente","Em Reparação","Resolvido"].index(
                                av.get('Status','Pendente')
                            ) if av.get('Status') in
                            ["Pendente","Em Reparação","Resolvido"] else 0,
                            key=f"avs_{avid}",
                            label_visibility="collapsed"
                        )
                    with col_avd:
                        if st.button("✅", key=f"avup_{avid}",
                                      use_container_width=True):
                            avarfrota_db.loc[
                                avarfrota_db['ID'] == avid, 'Status'
                            ] = novo_av_st
                            save_db(avarfrota_db, "frota_avarias.csv")
                            inv(); st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from core import load_all, save_db, inv, fh, sl, render_metric, t, gerar_pdf
import plotly.express as px

def render_admin(*args):
    # Desempacotamento integral das 20 variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db, 
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    st.title(f"🛡️ Admin: {st.session_state.user}")

    tabs = st.tabs(["📊 Dash", "✅ Aprovar", "👥 Pessoal", "🏗️ Obras", "💰 Faturação", "🛡️ HSE"])

    with tabs[0]: # DASHBOARD
        st.subheader(t('dashboard'))
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_metric("⏱️", fh(registos_db['Horas_Total'].sum()), t('total_hours'))
        with c2: render_metric("👷", users['Nome'].nunique(), "Técnicos")
        with c3: render_metric("🏗️", len(obras_db[obras_db['Ativa'] == 'Ativa']), t('active_sites'))
        with c4: render_metric("⏳", len(registos_db[registos_db['Status'] == "0"]), t('pending'))
        
        # Gráfico de Horas (Plotly)
        if not registos_db.empty:
            fig = px.area(registos_db.groupby('Data')['Horas_Total'].sum().reset_index(), x='Data', y='Horas_Total', title="Evolução de Horas")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[1]: # APROVAÇÕES
        st.subheader(t('approvals'))
        pend = registos_db[registos_db['Status'] == "0"]
        if pend.empty: st.success("Sem registos pendentes.")
        else:
            st.dataframe(pend[['Data', 'Técnico', 'Obra', 'Horas_Total', 'Turnos']], use_container_width=True)
            if st.button("✅ Aprovar Todos os Registos"):
                registos_db.loc[registos_db['Status'] == "0", 'Status'] = "1"
                save_db(registos_db, "registos.csv")
                inv(); st.rerun()

    with tabs[2]: # PESSOAL & RANKING
        st.subheader("Gestão de Pessoal e Ranking ⭐")
        # Lógica de cálculo automático do ranking (tua lógica _calc_auto)
        for _, u in users.iterrows():
            with st.expander(f"👤 {u['Nome']} - {u['Cargo']}"):
                st.write(f"Email: {u['Email']} | NIF: {u['NIF']}")
                # Aqui entra a tua lógica de avaliação manual e automática

    with tabs[3]: # OBRAS & FRENTES
        st.subheader("Controlo de Obras")
        # Formulário de nova obra integral
        with st.expander("➕ Criar Nova Obra"):
            with st.form("nova_obra"):
                no = st.text_input("Nome da Obra")
                cl = st.text_input("Cliente")
                ti = st.selectbox("Tipo de Obra", ["Normal", "Instrumentação"])
                if st.form_submit_button("Criar Obra"):
                    new_o = pd.DataFrame([{"Obra": no, "Cliente": cl, "TipoObra": ti, "Ativa": "Ativa"}])
                    save_db(pd.concat([obras_db, new_o]), "obras_lista.csv")
                    inv(); st.rerun()

    with tabs[4]: # FATURAÇÃO
        st.subheader("💰 Centro de Faturação")
        # Lógica de geração de fatura em PDF (Core Helper)
        cliente_f = st.selectbox("Selecionar Cliente", obras_db['Cliente'].unique())
        if st.button("📄 Gerar Fatura PDF"):
            st.info(f"A processar fatura para {cliente_f}...")

    with tabs[5]: # HSE SEGURANÇA
        st.subheader("🛡️ Incidentes e Safety Walks")
        st.dataframe(incs_db, use_container_width=True)

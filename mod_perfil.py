"""
GESTNOW v3 — mod_perfil.py
Perfil completo do utilizador — editável, com estatísticas e alteração de password
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

from core import save_db, inv, load_db, fh, hp, cp, log_audit, ICONS


def render_perfil(*args):
    (users, obras_db, frentes_db, registos_db, *_) = args

    user_nome = st.session_state.get('user', '')
    user_tipo = st.session_state.get('tipo', '')
    cargo     = st.session_state.get('cargo', '')

    # Carregar dados frescos do utilizador
    try:
        users_fresh = load_db("usuarios.csv", [
            "Nome","Password","Tipo","Cargo","Email","Telefone","Morada","Localidade",
            "Concelho","Codigo_Postal","Naturalidade","Nacionalidade","NIF","NISS","CC",
            "CC_Validade","DataNasc","Estado_Civil","Sexo","Dependentes","Profissao",
            "Categoria_Profissional","Habilitacoes_Literarias","Contacto_Emergencia",
            "Nome_Emergencia","Grau_Parentesco","Banco_IBAN","Observacoes",
            "Tamanho_Camisola","Tamanho_Calca","Tamanho_Botas",
            "Local","PrecoHora","PrecoHoraStatus","PrecoHoraData",
            "PIN","Foto","Campos_Bloqueados","PDFs_Vistos","PDFs_Validados","PDFs_Validacao_Data"
        ])
        match = users_fresh[users_fresh['Nome'] == user_nome]
        if not match.empty:
            user_data = match.iloc[0]
            user_idx  = match.index[0]
        else:
            user_data = None
            user_idx  = None
    except Exception as e:
        st.error(f"Erro ao carregar perfil: {e}")
        return

    if user_data is None:
        st.warning("⚠️ Utilizador não encontrado na base de dados.")
        return

    # Header
    st.markdown(f"""
    <div style="text-align:center;padding:30px 20px;
        background:linear-gradient(135deg,#1E293B,#0F172A);
        border-radius:20px;margin-bottom:25px;
        border:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:3rem;margin-bottom:10px;">👤</div>
        <div style="font-size:1.8rem;font-weight:800;color:#F8FAFC;">{user_nome}</div>
        <div style="font-size:1rem;color:#94A3B8;">{cargo} | {user_tipo}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Estatísticas rápidas ──────────────────────────────────────────
    if not registos_db.empty:
        meus_regs = registos_db[registos_db['Técnico'] == user_nome]
        horas_tot = meus_regs['Horas_Total'].astype(float).sum()
        horas_apr = meus_regs[meus_regs['Status'] == '1']['Horas_Total'].astype(float).sum()
        pendentes = len(meus_regs[meus_regs['Status'] == '0'])
        n_registos = len(meus_regs)
    else:
        horas_tot = horas_apr = pendentes = n_registos = 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("⏱️ Horas Totais",   fh(horas_tot))
    with c2: st.metric("✅ Horas Aprovadas", fh(horas_apr))
    with c3: st.metric("⏳ Pendentes",       pendentes)
    with c4: st.metric("📋 Registos",        n_registos)

    st.divider()

    tabs = st.tabs(["✏️ Editar Perfil", "🔐 Password & PIN", "📊 Histórico de Horas"])

    # ── TAB 0: EDITAR PERFIL ─────────────────────────────────────────
    with tabs[0]:
        try:
            campos_bloqueados = json.loads(user_data.get('Campos_Bloqueados', '[]'))
        except:
            campos_bloqueados = []

        with st.form("form_perfil_edit"):
            # Identificação
            st.markdown("#### 📋 Identificação")
            c1, c2 = st.columns(2)
            with c1:
                telefone = st.text_input("Telefone",  value=user_data.get('Telefone',''),  disabled='Telefone' in campos_bloqueados,  key="pf_tel")
                email    = st.text_input("Email",     value=user_data.get('Email',''),     disabled='Email' in campos_bloqueados,     key="pf_email")
                c_emerg  = st.text_input("Contacto Emergência", value=user_data.get('Contacto_Emergencia',''), disabled='Contacto_Emergencia' in campos_bloqueados, key="pf_emerg")
            with c2:
                n_emerg  = st.text_input("Nome Emergência", value=user_data.get('Nome_Emergencia',''), disabled='Nome_Emergencia' in campos_bloqueados, key="pf_n_emerg")
                grau     = st.text_input("Grau Parentesco", value=user_data.get('Grau_Parentesco',''), disabled='Grau_Parentesco' in campos_bloqueados, key="pf_grau")

            # Morada
            st.markdown("#### 📍 Morada")
            morada = st.text_input("Morada", value=user_data.get('Morada',''), disabled='Morada' in campos_bloqueados, key="pf_morada")
            c3, c4, c5 = st.columns(3)
            with c3: localidade = st.text_input("Localidade", value=user_data.get('Localidade',''), disabled='Localidade' in campos_bloqueados, key="pf_loc")
            with c4: concelho   = st.text_input("Concelho",   value=user_data.get('Concelho',''),   disabled='Concelho' in campos_bloqueados,   key="pf_conc")
            with c5: cod_postal = st.text_input("Código Postal", value=user_data.get('Codigo_Postal',''), disabled='Codigo_Postal' in campos_bloqueados, key="pf_cp")

            # Dados Pessoais
            st.markdown("#### 🌍 Dados Pessoais")
            c6, c7 = st.columns(2)
            with c6:
                naturalidade = st.text_input("Naturalidade", value=user_data.get('Naturalidade',''), disabled='Naturalidade' in campos_bloqueados, key="pf_nat")
                ec_opts = ["Solteiro(a)","Casado(a)","Divorciado(a)","Viúvo(a)","União de Facto"]
                ec_val = user_data.get('Estado_Civil','Solteiro(a)')
                estado_civil = st.selectbox("Estado Civil", ec_opts,
                    index=ec_opts.index(ec_val) if ec_val in ec_opts else 0,
                    disabled='Estado_Civil' in campos_bloqueados, key="pf_ec")
            with c7:
                nacionalidade = st.text_input("Nacionalidade", value=user_data.get('Nacionalidade','Portugal'), disabled='Nacionalidade' in campos_bloqueados, key="pf_nac")
                sexo_opts = ["Masculino","Feminino"]
                sexo_val  = user_data.get('Sexo','Masculino')
                sexo = st.radio("Sexo", sexo_opts,
                    index=sexo_opts.index(sexo_val) if sexo_val in sexo_opts else 0,
                    horizontal=True, disabled='Sexo' in campos_bloqueados, key="pf_sexo")

            # Documentos
            st.markdown("#### 🆔 Documentos")
            c8, c9 = st.columns(2)
            with c8:
                nif  = st.text_input("NIF",  value=user_data.get('NIF',''),  disabled='NIF' in campos_bloqueados,  key="pf_nif")
                cc   = st.text_input("CC",   value=user_data.get('CC',''),   disabled='CC' in campos_bloqueados,   key="pf_cc")
                niss = st.text_input("NISS", value=user_data.get('NISS',''), disabled='NISS' in campos_bloqueados, key="pf_niss")
            with c9:
                cc_val = st.text_input("Validade CC", value=user_data.get('CC_Validade',''), disabled='CC_Validade' in campos_bloqueados, key="pf_cc_val")
                dep_raw = user_data.get('Dependentes','0')
                try: dep_int = int(dep_raw) if dep_raw else 0
                except: dep_int = 0
                dependentes = st.number_input("Dependentes", min_value=0, value=dep_int,
                    disabled='Dependentes' in campos_bloqueados, key="pf_dep")

            # Profissional
            st.markdown("#### 💼 Dados Profissionais")
            profissao = st.text_input("Profissão", value=user_data.get('Profissao',''), disabled='Profissao' in campos_bloqueados, key="pf_prof")
            c10, c11 = st.columns(2)
            with c10:
                categoria = st.text_input("Categoria Profissional", value=user_data.get('Categoria_Profissional',''),
                    disabled='Categoria_Profissional' in campos_bloqueados, key="pf_cat")
            with c11:
                hab_opts = ["4º Ano","6º Ano","9º Ano","12º Ano","Curso Técnico","Licenciatura","Mestrado","Doutoramento"]
                hab_val  = user_data.get('Habilitacoes_Literarias','')
                habilitacoes = st.selectbox("Habilitações", hab_opts,
                    index=hab_opts.index(hab_val) if hab_val in hab_opts else 0,
                    disabled='Habilitacoes_Literarias' in campos_bloqueados, key="pf_hab")

            # Fardamento
            st.markdown("#### 👕 Fardamento")
            c12, c13, c14 = st.columns(3)
            cam_opts = ["XS","S","M","L","XL","XXL","XXXL"]
            cal_opts = ["XS (34/36)","S (38)","M (40/42)","L (42/44)","XL (46/48)","XXL (50/52)"]
            bot_opts = ["40","41","42","43","44","45","Outro"]
            with c12:
                cam_v = user_data.get('Tamanho_Camisola','M')
                tam_camisola = st.selectbox("Camisola", cam_opts, index=cam_opts.index(cam_v) if cam_v in cam_opts else 2, key="pf_cam")
            with c13:
                cal_v = user_data.get('Tamanho_Calca','')
                tam_calca = st.selectbox("Calça", cal_opts, index=cal_opts.index(cal_v) if cal_v in cal_opts else 0, key="pf_calc")
            with c14:
                bot_v = user_data.get('Tamanho_Botas','')
                tam_botas = st.selectbox("Botas", bot_opts, index=bot_opts.index(bot_v) if bot_v in bot_opts else 0, key="pf_bot")

            obs = st.text_area("Observações", value=user_data.get('Observacoes',''), disabled='Observacoes' in campos_bloqueados, key="pf_obs")

            st.info("🔒 Nome, Tipo, Cargo e IBAN são geridos pelo Admin e não são editáveis aqui.")

            if st.form_submit_button("💾 Guardar Alterações", use_container_width=True, type="primary"):
                updates = {
                    'Telefone': telefone, 'Email': email, 'Morada': morada,
                    'Localidade': localidade, 'Concelho': concelho, 'Codigo_Postal': cod_postal,
                    'Naturalidade': naturalidade, 'Nacionalidade': nacionalidade,
                    'Estado_Civil': estado_civil, 'Sexo': sexo, 'NIF': nif,
                    'CC': cc, 'CC_Validade': cc_val, 'NISS': niss,
                    'Dependentes': str(dependentes), 'Profissao': profissao,
                    'Categoria_Profissional': categoria, 'Habilitacoes_Literarias': habilitacoes,
                    'Contacto_Emergencia': c_emerg, 'Nome_Emergencia': n_emerg,
                    'Grau_Parentesco': grau, 'Tamanho_Camisola': tam_camisola,
                    'Tamanho_Calca': tam_calca, 'Tamanho_Botas': tam_botas, 'Observacoes': obs
                }
                for campo, valor in updates.items():
                    if campo not in campos_bloqueados:
                        users_fresh.loc[user_idx, campo] = valor
                save_db(users_fresh, "usuarios.csv")
                log_audit(usuario=user_nome, acao="EDITAR_PERFIL", tabela="usuarios.csv",
                          registro_id=user_nome, detalhes="Perfil atualizado via mod_perfil", ip="")
                inv("usuarios.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                st.success("✅ Perfil atualizado com sucesso!")
                st.rerun()

    # ── TAB 1: PASSWORD & PIN ────────────────────────────────────────
    with tabs[1]:
        st.markdown("#### 🔐 Alterar Password")
        with st.form("form_pwd"):
            pwd_atual = st.text_input("Password Atual", type="password", key="pf_pwd_atual")
            pwd_nova  = st.text_input("Nova Password",  type="password", key="pf_pwd_nova")
            pwd_conf  = st.text_input("Confirmar Nova Password", type="password", key="pf_pwd_conf")
            if st.form_submit_button("🔑 Alterar Password", use_container_width=True, type="primary"):
                if not pwd_atual or not pwd_nova:
                    st.error("❌ Preenche todos os campos.")
                elif pwd_nova != pwd_conf:
                    st.error("❌ As passwords não coincidem.")
                elif len(pwd_nova) < 6:
                    st.error("❌ A password deve ter pelo menos 6 caracteres.")
                else:
                    hash_atual = user_data.get('Password', '')
                    if cp(pwd_atual, hash_atual):
                        users_fresh.loc[user_idx, 'Password'] = hp(pwd_nova)
                        save_db(users_fresh, "usuarios.csv")
                        log_audit(usuario=user_nome, acao="ALTERAR_PASSWORD", tabela="usuarios.csv",
                                  registro_id=user_nome, detalhes="Password alterada pelo utilizador", ip="")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        st.success("✅ Password alterada com sucesso!")
                    else:
                        st.error("❌ Password atual incorreta.")

        st.divider()
        st.markdown("#### 🔢 Alterar PIN")
        with st.form("form_pin"):
            pin_novo  = st.text_input("Novo PIN (4 dígitos)", type="password", max_chars=4, key="pf_pin_novo")
            pin_conf  = st.text_input("Confirmar PIN", type="password", max_chars=4, key="pf_pin_conf")
            if st.form_submit_button("🔢 Alterar PIN", use_container_width=True):
                if len(pin_novo) != 4 or not pin_novo.isdigit():
                    st.error("❌ O PIN deve ter exatamente 4 dígitos.")
                elif pin_novo != pin_conf:
                    st.error("❌ Os PINs não coincidem.")
                else:
                    users_fresh.loc[user_idx, 'PIN'] = pin_novo
                    save_db(users_fresh, "usuarios.csv")
                    log_audit(usuario=user_nome, acao="ALTERAR_PIN", tabela="usuarios.csv",
                              registro_id=user_nome, detalhes="PIN alterado pelo utilizador", ip="")
                    inv("usuarios.csv")
                    from core import _cached_load_all
                    _cached_load_all.clear()
                    st.success("✅ PIN alterado com sucesso!")

    # ── TAB 2: HISTÓRICO DE HORAS ────────────────────────────────────
    with tabs[2]:
        st.markdown("#### 📊 Histórico de Horas")
        if not registos_db.empty:
            meus = registos_db[registos_db['Técnico'] == user_nome].copy()
            if meus.empty:
                st.info("📋 Sem registos ainda.")
            else:
                # Filtros
                c1, c2 = st.columns(2)
                with c1:
                    obras_minhas = ["Todas"] + meus['Obra'].unique().tolist()
                    obra_filt = st.selectbox("Filtrar por Obra", obras_minhas, key="pf_hist_obra")
                with c2:
                    status_opts = {"Todos": None, "✅ Aprovado": "1", "⏳ Pendente": "0", "❌ Rejeitado": "-1"}
                    status_sel  = st.selectbox("Estado", list(status_opts.keys()), key="pf_hist_status")

                if obra_filt != "Todas":
                    meus = meus[meus['Obra'] == obra_filt]
                if status_opts[status_sel]:
                    meus = meus[meus['Status'] == status_opts[status_sel]]

                total_h = meus['Horas_Total'].astype(float).sum()
                st.metric("Total filtrado", fh(total_h))

                meus['Estado'] = meus['Status'].map({"0":"⏳ Pendente","1":"✅ Aprovado","2":"🔵 Faturação","-1":"❌ Rejeitado"}).fillna("❓")
                cols_show = [c for c in ['Data','Obra','Frente','Turnos','Horas_Total','Estado','Relatorio'] if c in meus.columns]
                st.dataframe(meus[cols_show].sort_values('Data', ascending=False), use_container_width=True, hide_index=True)

                # Exportar CSV
                csv = meus[cols_show].to_csv(index=False).encode('utf-8')
                st.download_button("📥 Exportar CSV", csv, f"horas_{user_nome}.csv", "text/csv")
        else:
            st.info("📋 Sem registos de horas.")

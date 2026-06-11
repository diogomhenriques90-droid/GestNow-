import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from core import save_db, inv, load_db, cliente_select, registar_novo_cliente

def render_obras(obras_db, frentes_db, users, inst_acessos_db):
    st.markdown("### 🏗️ Gestão de Obras")

    # Carregar histórico de obras
    try:
        obras_historico = load_db("obras_historico.csv", [
            "Obra","Cliente","TipoObra","Local","DataInicio",
            "DataFecho","Fechada_Por"
        ], silent=True)
    except:
        obras_historico = pd.DataFrame(columns=[
            "Obra","Cliente","TipoObra","Local","DataInicio",
            "DataFecho","Fechada_Por"
        ])

    user_nome = st.session_state.get('user', 'Admin')

    tab_obras, tab_alocacoes, tab_historico = st.tabs([
        "🏗️ Obras", "👷 Alocações", "📜 Histórico"
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB OBRAS
    # ════════════════════════════════════════════════════════════════
    with tab_obras:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("#### ➕ Nova Obra")
            with st.form("form_nova_obra"):
                nome     = st.text_input("Nome da Obra *", key="obra_nome")
                cliente, cliente_novo = cliente_select("Cliente *", "obra_cliente")
                tipo     = st.selectbox(
                    "Tipo",
                    ["Normal","Instrumentação","Manutenção","Comissionamento"],
                    key="obra_tipo"
                )
                local    = st.text_input("Localização", key="obra_local")
                cod      = st.text_input("Código Obra", key="obra_cod",
                                          placeholder="Ex: SINES-001")

                if st.form_submit_button(
                    "💾 Criar Obra",
                    use_container_width=True, type="primary"
                ):
                    if not nome.strip() or not cliente.strip():
                        st.error("❌ Nome e Cliente obrigatórios.")
                    elif not obras_db.empty and \
                         nome.strip() in obras_db['Obra'].values:
                        st.error("❌ Obra já existe.")
                    else:
                        if cliente_novo:
                            registar_novo_cliente(cliente)
                        nova = pd.DataFrame([{
                            "Obra":       nome.strip(),
                            "Cliente":    cliente.strip(),
                            "Codigo":     cod.strip(),
                            "TipoObra":   tipo,
                            "Local":      local.strip(),
                            "Ativa":        "Ativa",
                            "DataInicio":   datetime.now().strftime("%d/%m/%Y"),
                            "Orcamento_ID": "",
                        }])
                        obras_db = pd.concat(
                            [obras_db, nova], ignore_index=True
                        ) if not obras_db.empty else nova
                        save_db(obras_db, "obras_lista.csv")
                        inv("obras_lista.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        st.success(f"✅ Obra '{nome}' criada!")
                        st.rerun()

        with col2:
            st.markdown("#### 🏭 Obras Ativas")
            if obras_db.empty:
                st.info("📋 Sem obras.")
            else:
                ativas = obras_db[obras_db['Ativa'] == 'Ativa']
                if ativas.empty:
                    st.info("📋 Sem obras ativas.")
                else:
                    for _, ob in ativas.iterrows():
                        ob_nome = ob.get('Obra','')
                        ob_cli  = ob.get('Cliente','')
                        ob_loc  = ob.get('Local','')
                        ob_tipo = ob.get('TipoObra','')

                        # Contar colaboradores alocados
                        n_colabs = 0
                        if not inst_acessos_db.empty and 'Obra' in inst_acessos_db.columns:
                            n_colabs = len(inst_acessos_db[
                                (inst_acessos_db['Obra']  == ob_nome) &
                                (inst_acessos_db['Ativo'] == 'Sim')
                            ])

                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:10px;"
                            f"padding:12px 16px;margin-bottom:8px;"
                            f"border-left:4px solid #10B981;'>"
                            f"<b style='color:#F1F5F9;'>{ob_nome}</b>"
                            f"<span style='float:right;color:#10B981;"
                            f"font-size:0.8rem;'>✅ Ativa</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"{ob_cli} · {ob_tipo} · {ob_loc} · "
                            f"👷 {n_colabs} colaborador(es)</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        col_ed, col_del = st.columns([3, 1])
                        with col_ed:
                            # Editar cliente/local inline
                            pass
                        with col_del:
                            if st.button(
                                "🗄️ Fechar",
                                key=f"fechar_obra_{ob_nome}",
                                use_container_width=True,
                                help="Fechar obra e mover para histórico"
                            ):
                                st.session_state[f'confirmar_fechar_{ob_nome}'] = True

                        # Confirmação fechar
                        if st.session_state.get(f'confirmar_fechar_{ob_nome}'):
                            st.warning(
                                f"⚠️ Confirmas que queres fechar a obra **{ob_nome}**? "
                                f"Vai para o histórico."
                            )
                            col_sim, col_nao = st.columns(2)
                            with col_sim:
                                if st.button(
                                    "✅ Sim, fechar",
                                    key=f"sim_fechar_{ob_nome}",
                                    type="primary",
                                    use_container_width=True
                                ):
                                    # Mover para histórico
                                    hist_row = pd.DataFrame([{
                                        "Obra":       ob_nome,
                                        "Cliente":    ob_cli,
                                        "TipoObra":   ob_tipo,
                                        "Local":      ob_loc,
                                        "DataInicio": ob.get('DataInicio',''),
                                        "DataFecho":  datetime.now().strftime("%d/%m/%Y"),
                                        "Fechada_Por":user_nome
                                    }])
                                    obras_historico = pd.concat(
                                        [obras_historico, hist_row],
                                        ignore_index=True
                                    ) if not obras_historico.empty else hist_row
                                    save_db(obras_historico, "obras_historico.csv")

                                    # Marcar como inativa
                                    obras_db.loc[
                                        obras_db['Obra'] == ob_nome, 'Ativa'
                                    ] = 'Inativa'
                                    save_db(obras_db, "obras_lista.csv")

                                    # Desativar alocações
                                    if not inst_acessos_db.empty:
                                        inst_acessos_db.loc[
                                            inst_acessos_db['Obra'] == ob_nome,
                                            'Ativo'
                                        ] = 'Não'
                                        save_db(inst_acessos_db, "inst_acessos.csv")

                                    inv("obras_historico.csv"); inv("obras_lista.csv"); inv("inst_acessos.csv")
                                    from core import _cached_load_all
                                    _cached_load_all.clear()
                                    st.session_state.pop(
                                        f'confirmar_fechar_{ob_nome}', None
                                    )
                                    st.success(f"✅ Obra '{ob_nome}' fechada e movida para histórico.")
                                    st.rerun()
                            with col_nao:
                                if st.button(
                                    "❌ Cancelar",
                                    key=f"nao_fechar_{ob_nome}",
                                    use_container_width=True
                                ):
                                    st.session_state.pop(
                                        f'confirmar_fechar_{ob_nome}', None
                                    )
                                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB ALOCAÇÕES
    # ════════════════════════════════════════════════════════════════
    with tab_alocacoes:
        st.markdown("#### 👷 Alocação de Colaboradores")

        obras_ativas = obras_db[
            obras_db['Ativa'] == 'Ativa'
        ]['Obra'].tolist() if not obras_db.empty else []

        col1, col2 = st.columns(2)
        with col1:
            obra_aloc = st.selectbox(
                "Obra", obras_ativas if obras_ativas else ["Sem obras"],
                key="aloc_obra"
            )
        with col2:
            users_lista = users['Nome'].tolist() if not users.empty else []
            tec_aloc    = st.selectbox(
                "Colaborador",
                users_lista if users_lista else ["Sem utilizadores"],
                key="aloc_tec"
            )

        col3, col4 = st.columns(2)
        with col3:
            preco_hora = st.number_input(
                "Preço Hora na Obra (€)",
                min_value=0.0, value=15.0, step=0.5,
                key="aloc_preco"
            )
        with col4:
            cargo_aloc = ""
            if not users.empty and tec_aloc in users['Nome'].values:
                cargo_aloc = str(
                    users[users['Nome'] == tec_aloc]['Cargo'].values[0]
                )
            st.markdown(
                f"<p style='color:#94A3B8;font-size:0.85rem;"
                f"padding:28px 0 0;margin:0;'>Cargo: {cargo_aloc}</p>",
                unsafe_allow_html=True
            )

        if st.button(
            "➕ Alocar Colaborador",
            key="btn_alocar", type="primary",
            use_container_width=True
        ):
            # Verificar se já está alocado
            ja_alocado = False
            if not inst_acessos_db.empty:
                check = inst_acessos_db[
                    (inst_acessos_db['Obra']       == obra_aloc) &
                    (inst_acessos_db['Utilizador'] == tec_aloc)  &
                    (inst_acessos_db['Ativo']      == 'Sim')
                ]
                ja_alocado = not check.empty

            if ja_alocado:
                st.warning(
                    f"⚠️ {tec_aloc} já está alocado à obra {obra_aloc}."
                )
            else:
                nova_aloc = pd.DataFrame([{
                    "Obra":        obra_aloc,
                    "Utilizador":  tec_aloc,
                    "Cargo":       cargo_aloc,
                    "PrecoHora":   preco_hora,
                    "Ativo":       "Sim",
                    "Data_Aloc":   datetime.now().strftime("%d/%m/%Y")
                }])
                inst_acessos_db = pd.concat(
                    [inst_acessos_db, nova_aloc], ignore_index=True
                ) if not inst_acessos_db.empty else nova_aloc
                save_db(inst_acessos_db, "inst_acessos.csv")
                inv("inst_acessos.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                st.success(f"✅ {tec_aloc} alocado à obra {obra_aloc}!")
                st.rerun()

        # ── Colaboradores por obra ────────────────────────────────
        st.markdown("---")
        st.markdown("#### 👥 Colaboradores por Obra")

        if not inst_acessos_db.empty and not obras_ativas:
            st.info("📋 Sem obras ativas.")
        elif inst_acessos_db.empty:
            st.info("📋 Sem alocações.")
        else:
            obra_ver = st.selectbox(
                "Ver colaboradores da obra",
                obras_ativas if obras_ativas else [""],
                key="ver_colabs_obra"
            )
            colabs_obra = inst_acessos_db[
                (inst_acessos_db['Obra']  == obra_ver) &
                (inst_acessos_db['Ativo'] == 'Sim')
            ] if not inst_acessos_db.empty else pd.DataFrame()

            if colabs_obra.empty:
                st.info(f"📋 Sem colaboradores em {obra_ver}.")
            else:
                for _, colab in colabs_obra.iterrows():
                    col_ci, col_cm = st.columns([4, 1])
                    with col_ci:
                        st.markdown(
                            f"<div style='background:#1E293B;border-radius:8px;"
                            f"padding:10px 14px;margin-bottom:4px;'>"
                            f"<b style='color:#F1F5F9;'>"
                            f"{colab.get('Utilizador','')}</b>"
                            f"<span style='float:right;color:#3B82F6;'>"
                            f"€ {colab.get('PrecoHora','')}/h</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"{colab.get('Cargo','')} · "
                            f"Desde {colab.get('Data_Aloc','')}"
                            f"</small></div>",
                            unsafe_allow_html=True
                        )
                    with col_cm:
                        colab_idx = colab.name
                        if st.button(
                            "🔄 Mover/Remover",
                            key=f"mv_{colab_idx}",
                            use_container_width=True
                        ):
                            st.session_state[
                                f'acao_colab_{colab_idx}'
                            ] = True

                    if st.session_state.get(f'acao_colab_{colab_idx}'):
                        col_mv, col_rm = st.columns(2)
                        with col_mv:
                            nova_obra_mv = st.selectbox(
                                "Mover para obra",
                                [o for o in obras_ativas if o != obra_ver],
                                key=f"nova_obra_{colab_idx}"
                            )
                            if st.button(
                                "✅ Mover",
                                key=f"confirmar_mv_{colab_idx}",
                                type="primary",
                                use_container_width=True
                            ):
                                inst_acessos_db.loc[
                                    colab_idx, 'Obra'
                                ] = nova_obra_mv
                                save_db(inst_acessos_db, "inst_acessos.csv")
                                inv("inst_acessos.csv")
                                from core import _cached_load_all
                                _cached_load_all.clear()
                                st.session_state.pop(
                                    f'acao_colab_{colab_idx}', None
                                )
                                st.success(
                                    f"✅ {colab.get('Utilizador','')} "
                                    f"movido para {nova_obra_mv}!"
                                )
                                st.rerun()
                        with col_rm:
                            st.markdown(
                                "<div style='height:28px;'></div>",
                                unsafe_allow_html=True
                            )
                            if st.button(
                                "❌ Remover da Obra",
                                key=f"remover_{colab_idx}",
                                use_container_width=True
                            ):
                                inst_acessos_db.loc[
                                    colab_idx, 'Ativo'
                                ] = 'Não'
                                save_db(inst_acessos_db, "inst_acessos.csv")
                                inv("inst_acessos.csv")
                                from core import _cached_load_all
                                _cached_load_all.clear()
                                st.session_state.pop(
                                    f'acao_colab_{colab_idx}', None
                                )
                                st.success(
                                    f"✅ {colab.get('Utilizador','')} "
                                    f"removido de {obra_ver}."
                                )
                                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB HISTÓRICO
    # ════════════════════════════════════════════════════════════════
    with tab_historico:
        st.markdown("#### 📜 Obras Fechadas")

        if obras_historico.empty:
            st.info("📋 Sem obras no histórico.")
        else:
            for _, ob_h in obras_historico.sort_values(
                'DataFecho', ascending=False
            ).iterrows():
                st.markdown(
                    f"<div style='background:#1E293B;border-radius:10px;"
                    f"padding:12px 16px;margin-bottom:8px;"
                    f"border-left:4px solid #6B7280;'>"
                    f"<b style='color:#94A3B8;'>{ob_h.get('Obra','')}</b>"
                    f"<span style='float:right;color:#6B7280;"
                    f"font-size:0.8rem;'>⚫ Fechada</span><br>"
                    f"<small style='color:#64748B;'>"
                    f"{ob_h.get('Cliente','')} · {ob_h.get('TipoObra','')} · "
                    f"{ob_h.get('Local','')} · "
                    f"Início: {ob_h.get('DataInicio','')} · "
                    f"Fecho: {ob_h.get('DataFecho','')} · "
                    f"Por: {ob_h.get('Fechada_Por','')}"
                    f"</small></div>",
                    unsafe_allow_html=True
                )

            # Reativar obra do histórico
            st.markdown("---")
            st.markdown("#### 🔄 Reativar Obra")
            obras_hist_lista = obras_historico['Obra'].tolist()
            obra_reativar    = st.selectbox(
                "Selecionar obra para reativar",
                obras_hist_lista,
                key="obra_reativar"
            )
            if st.button(
                "🔄 Reativar Obra",
                key="btn_reativar",
                use_container_width=True
            ):
                obras_db.loc[
                    obras_db['Obra'] == obra_reativar, 'Ativa'
                ] = 'Ativa'
                obras_historico = obras_historico[
                    obras_historico['Obra'] != obra_reativar
                ]
                save_db(obras_db,        "obras_lista.csv")
                save_db(obras_historico, "obras_historico.csv")
                inv("obras_lista.csv"); inv("obras_historico.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                st.success(f"✅ Obra '{obra_reativar}' reativada!")
                st.rerun()

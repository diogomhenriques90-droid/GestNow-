import streamlit as st
import pandas as pd
from core import load_all, inv, ICONS, fh, save_db
from datetime import datetime

def render_admin(*args):
    """Hub Principal do Admin â€” 10 tabs reorganizados"""

    st.markdown("""
    <style>
    .stMarkdown,.stText,.stDataFrame,label,div,span,p,h1,h2,h3 { color:#F8FAFC !important; }
    [data-testid="stMetric"] {
        background:linear-gradient(135deg,rgba(59,130,246,0.3),rgba(96,165,250,0.2));
        border:2px solid rgba(59,130,246,0.5); border-radius:12px; padding:15px;
    }
    [data-testid="stMetricValue"] { color:#60A5FA !important; }
    [data-testid="stMetricLabel"] { color:#94A3B8 !important; }
    </style>
    """, unsafe_allow_html=True)

    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     diarias_config_db, diarias_faltas_db, diarias_pagamentos_db,
     folhas_ocr_db) = args

    from core import (render_connection_indicator, render_offline_banner,
                      sync_data_when_online)
    render_connection_indicator()
    render_offline_banner()
    sync_data_when_online()

    # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E293B,#0F172A);padding:30px;
        border-radius:20px;margin-bottom:30px;border:1px solid rgba(255,255,255,0.2);">
        <h1 style="color:#F8FAFC;margin:0;font-size:2.5rem;">âš¡ Painel Administrativo</h1>
        <p style="color:#94A3B8;margin:10px 0 0 0;">
            Utilizador: <strong style="color:#60A5FA">{st.session_state.user}</strong> |
            Tipo: <strong style="color:#60A5FA">{st.session_state.tipo}</strong>
        </p>
        <p style="color:#64748B;margin:5px 0 0 0;font-size:0.9rem;">
            Ãšltima atualizaÃ§Ã£o: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # â”€â”€ NotificaÃ§Ãµes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    from core import (get_notificacoes, marcar_notificacao_lida,
                      contar_notificacoes_nao_lidas)
    user_atual  = st.session_state.user
    n_nao_lidas = contar_notificacoes_nao_lidas(user_atual)

    col_n1, col_n2 = st.columns([10, 1])
    with col_n2:
        if n_nao_lidas > 0:
            st.markdown(
                f"<div style='text-align:right;'>"
                f"<span style='font-size:1.5rem;'>ðŸ””</span>"
                f"<span style='background:#EF4444;color:white;border-radius:50%;"
                f"padding:2px 8px;font-size:0.8rem;margin-left:-10px;'>"
                f"{n_nao_lidas}</span></div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div style='text-align:right;'>"
                "<span style='font-size:1.5rem;opacity:0.5;'>ðŸ””</span></div>",
                unsafe_allow_html=True
            )

    with st.expander("ðŸ”” Ver NotificaÃ§Ãµes", expanded=n_nao_lidas > 0):
        notifs_df = get_notificacoes(user_atual, apenas_nao_lidas=True, limite=20)
        if not notifs_df.empty:
            for _, notif in notifs_df.iterrows():
                cor = {"info":"#3B82F6","warning":"#F59E0B",
                       "error":"#EF4444","success":"#10B981"}.get(
                    notif.get('Tipo','info'),"#6B7280"
                )
                st.markdown(
                    f"<div style='background:{cor}22;border-left:4px solid {cor};"
                    f"padding:15px;border-radius:8px;margin-bottom:10px;'>"
                    f"<strong style='color:{cor};'>{notif.get('Titulo','')}</strong>"
                    f"<p style='margin:5px 0 0 0;color:#94A3B8;'>"
                    f"{notif.get('Mensagem','')}</p>"
                    f"<small style='color:#6B7280;'>"
                    f"{notif.get('Data','')} {notif.get('Hora','')}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            if st.button("âœ… Marcar Todas como Lidas",
                          key="marcar_todas_lidas"):
                for _, notif in notifs_df.iterrows():
                    marcar_notificacao_lida(notif['ID'])
                inv()
                st.rerun()
        else:
            st.info("âœ… Sem notificaÃ§Ãµes pendentes.")

    st.divider()

    # â”€â”€ MÃ©tricas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown("### ðŸ“Š VisÃ£o Geral")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("ðŸ‘· TÃ©cnicos", len(users))
    with c2: st.metric("ðŸ­ Obras Ativas",
        len(obras_db[obras_db['Ativa'] == 'Ativa']) if not obras_db.empty else 0)
    with c3: st.metric("â³ ValidaÃ§Ãµes",
        len(registos_db[registos_db['Status'] == "0"]) if not registos_db.empty else 0)
    with c4: st.metric("ðŸ“‹ Pedidos",
        len(req_fer_db) + len(req_mat_db) + len(req_epi_db))
    with c5: st.metric("âš ï¸ Incidentes",
        len(incs_db) if not incs_db.empty else 0)
    with c6: st.metric("ðŸ’° Faturas",
        len(faturas_db) if not faturas_db.empty else 0)

    st.divider()

    # â”€â”€ 10 Tabs principais â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tabs = st.tabs([
        "ðŸ“¦ ArmazÃ©m",
        "ðŸ‘¥ RH",
        "ðŸ—‚ï¸ Secretariado",
        "ðŸ­ ProduÃ§Ã£o",
        "ðŸ’° FaturaÃ§Ã£o",
        "ðŸ“Š OrÃ§amentaÃ§Ã£o",
        "ðŸ’¼ Comercial",
        "ðŸŽ¯ Qualidade",
        "ðŸ’» IT",
        "ðŸ›¡ï¸ HSE",
    ])

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 0 â€” ARMAZÃ‰M
    # EPIs, Ferramentas, Materiais, ValidaÃ§Ã£o Compras
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[0]:
        from mod_armazem import render_armazem
        render_armazem(req_fer_db, req_mat_db, req_epi_db, incs_db)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 1 â€” RH
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[1]:
        from mod_admin_rh import render_admin_rh as render_rh
        render_rh(users, obras_db, frentes_db, registos_db, faturas_db,
                  docs_db, incs_db, sw_db, obs_db, equip_db, diags_db,
                  diags_u_db, folhas_db, comuns_db, comuns_u_db,
                  req_fer_db, req_mat_db, req_epi_db, avals_db,
                  inst_acessos_db)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 2 â€” SECRETARIADO
    # 1Âª/2Âª validaÃ§Ã£o horas, gasÃ³leo, avarias carrinhas, histÃ³rico
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[2]:
        from mod_secretariado import render_secretariado
        render_secretariado(
            users, obras_db, frentes_db, registos_db, faturas_db,
            docs_db, incs_db, sw_db, obs_db, equip_db, diags_db,
            diags_u_db, folhas_db, comuns_db, comuns_u_db,
            req_fer_db, req_mat_db, req_epi_db, avals_db,
            inst_acessos_db, diarias_config_db, diarias_faltas_db,
            diarias_pagamentos_db
        )
        
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 3 â€” PRODUÃ‡ÃƒO
    # Obras, Frota, DeslocaÃ§Ãµes, Planeamento, Acessos
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[3]:
        st.markdown("## ðŸ­ ProduÃ§Ã£o")
        prod_tabs = st.tabs([
            "ðŸ—ï¸ Obras",
            "ðŸš— Frota",
            "ðŸ—ºï¸ DeslocaÃ§Ãµes",      # â† era "ðŸ¨ Dormidas"
            "ðŸ“‹ Planeamento",
            "ðŸ” Acessos",
        ])
        with prod_tabs[0]:
            from mod_admin_obras import render_obras
            render_obras(obras_db, frentes_db, users, inst_acessos_db)
        with prod_tabs[1]:
            from mod_admin_frota import render_frota
            render_frota()
        with prod_tabs[2]:
            from mod_admin_deslocacoes import render_deslocacoes
            render_deslocacoes(obras_db, users)
        with prod_tabs[3]:
            from mod_admin_planeamento import render_planeamento
            render_planeamento()
        with prod_tabs[4]:
            from mod_admin_acessos_obras import render_acessos_obras
            render_acessos_obras(users, obras_db)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 4 â€” FATURAÃ‡ÃƒO
    # Custos por obra, frota, dormidas, folhas ponto,
    # faturaÃ§Ã£o horas, diÃ¡rias, emissÃ£o mensal
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[4]:
        st.markdown("## ðŸ’° FaturaÃ§Ã£o")
        fat_tabs = st.tabs([
            # â”€â”€ 13 mÃ³dulos novos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            "ðŸ“Š Dashboard CFO",
            "ðŸ§¾ Clientes & FaturaÃ§Ã£o",
            "ðŸ“¥ Fornecedores",
            "ðŸ‘¥ RH Financeiro",
            "ðŸš— Frota & Renting",
            "ðŸ“ˆ Performance Obras",
            "ðŸ’µ Tesouraria",
            "ðŸ†˜ Simulador Crise",
            "ðŸ‡ªðŸ‡º Fundos Europeus",
            "ðŸ­ Imobilizado",
            "ðŸ§¾ Fiscal",
            "ðŸ“‹ Auditoria Anual",
            "ðŸ“Š Reporting",
            # â”€â”€ mÃ³dulos existentes a manter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            "ðŸ“Š Custos por Obra",
            "ðŸ’¶ DiÃ¡rias",
            "ðŸ“„ Folhas de Ponto",
            "â±ï¸ Horas FaturaÃ§Ã£o",
            "ðŸ“¤ EmissÃ£o Mensal",
            "ðŸ“¤ Export Contabilidade",
        ])

        # â”€â”€ 13 mÃ³dulos novos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        with fat_tabs[0]:
            from mod_fat_dashboard import render_fat_dashboard
            render_fat_dashboard(obras_db, registos_db,
                                 faturas_db, diarias_pagamentos_db)

        with fat_tabs[1]:
            from mod_fat_clientes import render_fat_clientes
            render_fat_clientes(obras_db, registos_db)

        with fat_tabs[2]:
            from mod_fat_fornecedores import render_fat_fornecedores
            render_fat_fornecedores(obras_db)

        with fat_tabs[3]:
            from mod_fat_rh import render_fat_rh
            render_fat_rh(obras_db, registos_db)

        with fat_tabs[4]:
            from mod_fat_frota import render_fat_frota
            render_fat_frota()

        with fat_tabs[5]:
            from mod_fat_obras import render_fat_obras
            render_fat_obras(obras_db, registos_db,
                             faturas_db, diarias_pagamentos_db)

        with fat_tabs[6]:
            from mod_fat_tesouraria import render_fat_tesouraria
            render_fat_tesouraria(obras_db, registos_db,
                                  faturas_db, diarias_pagamentos_db)

        with fat_tabs[7]:
            from mod_fat_crise import render_fat_crise
            render_fat_crise(obras_db, registos_db,
                             faturas_db, diarias_pagamentos_db)

        with fat_tabs[8]:
            from mod_fat_fundos import render_fat_fundos
            render_fat_fundos()

        with fat_tabs[9]:
            from mod_fat_imobilizado import render_fat_imobilizado
            render_fat_imobilizado()

        with fat_tabs[10]:
            from mod_fat_fiscal import render_fat_fiscal
            render_fat_fiscal(obras_db, registos_db,
                              faturas_db, diarias_pagamentos_db)

        with fat_tabs[11]:
            from mod_fat_auditoria import render_fat_auditoria
            render_fat_auditoria(obras_db, registos_db,
                                 faturas_db, diarias_pagamentos_db)

        with fat_tabs[12]:
            from mod_fat_reporting import render_fat_reporting
            render_fat_reporting(obras_db, registos_db,
                                 faturas_db, diarias_pagamentos_db)


        with fat_tabs[13]:
            _render_custos_por_obra(
                obras_db, registos_db, req_mat_db,
                req_fer_db, req_epi_db, incs_db
            )

        with fat_tabs[14]:
            from mod_admin_diarias import render_admin_diarias
            render_admin_diarias(
                users, obras_db, frentes_db, registos_db, faturas_db,
                docs_db, incs_db, sw_db, obs_db, equip_db, diags_db,
                diags_u_db, folhas_db, comuns_db, comuns_u_db,
                req_fer_db, req_mat_db, req_epi_db, avals_db,
                inst_acessos_db, diarias_config_db, diarias_faltas_db,
                diarias_pagamentos_db
            )

        with fat_tabs[15]:
            _render_folhas_ponto_fat(folhas_db, folhas_ocr_db, obras_db)

        with fat_tabs[16]:
            # FaturaÃ§Ã£o de horas â€” vem do secretariado tab faturaÃ§Ã£o
            import pandas as pd
            st.markdown("### â±ï¸ Horas para FaturaÃ§Ã£o ao Cliente")
            if registos_db.empty:
                st.info("ðŸ“‹ Sem registos.")
            else:
                from core import load_db as _ld
                regs = registos_db.copy()
                regs['Horas_Total'] = pd.to_numeric(
                    regs['Horas_Total'], errors='coerce'
                ).fillna(0)
                azuis = regs[regs['Status'] == '2']
                if azuis.empty:
                    st.info("ðŸ“‹ Sem horas com status ðŸ”µ faturaÃ§Ã£o.")
                else:
                    obras_fat = sorted(
                        azuis['Obra'].dropna().unique().tolist()
                    )
                    obra_sel_fat = st.selectbox(
                        "Obra", obras_fat, key="fat_h_obra"
                    )
                    azuis_obra = azuis[azuis['Obra'] == obra_sel_fat]
                    total_h_fat = azuis_obra['Horas_Total'].sum()

                    c1, c2 = st.columns(2)
                    with c1: st.metric("Registos", len(azuis_obra))
                    with c2: st.metric("Total Horas", fh(total_h_fat))

                    resumo = azuis_obra.groupby('TÃ©cnico').agg(
                        Horas=('Horas_Total','sum'),
                        Dias=('Data','nunique')
                    ).reset_index()
                    st.dataframe(
                        resumo, use_container_width=True, hide_index=True
                    )

                    # PreÃ§o hora por tÃ©cnico
                    from core import load_db as _ld2
                    try:
                        users_full = _ld2("usuarios.csv", ["Nome","PrecoHora"],
                                          silent=True)
                    except:
                        users_full = pd.DataFrame(
                            columns=["Nome","PrecoHora"]
                        )

                    st.markdown("---")
                    st.markdown("#### ðŸ’° Valor a Faturar")
                    total_faturar = 0
                    for _, tr in resumo.iterrows():
                        tec_nome = tr['TÃ©cnico']
                        h_tec    = tr['Horas']
                        preco_h  = 15.0
                        if not users_full.empty and \
                           tec_nome in users_full['Nome'].values:
                            try:
                                preco_h = float(
                                    users_full[
                                        users_full['Nome'] == tec_nome
                                    ]['PrecoHora'].values[0]
                                )
                            except:
                                pass
                        subtotal = round(h_tec * preco_h, 2)
                        total_faturar += subtotal
                        st.markdown(
                            f"<div style='background:#1E293B;"
                            f"border-radius:8px;padding:10px;"
                            f"margin-bottom:4px;'>"
                            f"<b style='color:#F1F5F9;'>{tec_nome}</b>"
                            f"<span style='float:right;color:#10B981;"
                            f"font-weight:700;'>â‚¬ {subtotal:.2f}</span><br>"
                            f"<small style='color:#64748B;'>"
                            f"{fh(h_tec)} Ã— â‚¬{preco_h}/h</small>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    st.metric("ðŸ’° Total a Faturar", f"â‚¬ {total_faturar:.2f}")

        with fat_tabs[17]:
            _render_emissao_mensal(
                obras_db, registos_db, faturas_db,
                diarias_pagamentos_db
            )
            
        with fat_tabs[18]:
            from mod_exportacao_contabilidade import render_exportacao_contabilidade
            render_exportacao_contabilidade()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 5 â€” ORÃ‡AMENTAÃ‡ÃƒO
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[5]:
        from mod_admin_orcamentacao import render_orcamentacao
        render_orcamentacao()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 6 â€” COMERCIAL
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[6]:
        from mod_admin_comercial import render_comercial
        render_comercial()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 7 â€” QUALIDADE + ISO 9001 + LOGS AUDIT
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[7]:
        st.markdown("## ðŸŽ¯ Qualidade & Auditoria")
        qual_tabs = st.tabs([
            "ðŸŽ¯ Qualidade Operacional",
            "ðŸ† ISO 9001:2015",
            "ðŸ“‹ Logs Audit"
        ])

        with qual_tabs[0]:
            from mod_admin_qualidade import render_qualidade
            render_qualidade()

        with qual_tabs[1]:
            from mod_iso9001 import render_iso9001
            render_iso9001()

        with qual_tabs[2]:
            st.markdown("### ðŸ“‹ Logs de Auditoria")
            from core import get_audit_logs
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                filtro_user = st.selectbox(
                    "Utilizador",
                    ["Todos"] + users['Nome'].tolist(),
                    key="log_filt_user"
                )
            with col_f2:
                apenas_clientes = st.checkbox(
                    "ðŸ‘¥ Apenas Clientes", key="log_filt_clientes"
                )
            with col_f3:
                limite = st.number_input(
                    "Limite", min_value=10, max_value=1000,
                    value=100, key="log_limite"
                )
            usuario_f = None if filtro_user == "Todos" else filtro_user
            logs_df   = get_audit_logs(
                filtro_usuario=usuario_f, limite=limite
            )
            if apenas_clientes and not logs_df.empty:
                logs_df = logs_df[
                    logs_df['Usuario'].str.contains("CLIENTE:", na=False)
                ]
            if not logs_df.empty:
                st.metric("Total AÃ§Ãµes", len(logs_df))
                cols_show = [c for c in [
                    'Data','Hora','Usuario','Acao',
                    'Tabela','Registro_ID','Detalhes'
                ] if c in logs_df.columns]
                st.dataframe(
                    logs_df[cols_show],
                    use_container_width=True, hide_index=True
                )
                csv_logs = logs_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "ðŸ“¥ Exportar Logs",
                    csv_logs,
                    f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    "text/csv", use_container_width=True
                )
            else:
                st.info("ðŸ“‹ Sem registos de auditoria.")

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 8 â€” IT + CONFIG EMAIL + BACKUP + INFRAESTRUTURA
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[8]:
        st.markdown("## ðŸ’» IT & Sistemas")
        it_tabs = st.tabs([
            "ðŸ’» IT & Infraestrutura",
            "ðŸ“§ Config Email",
        ])

        with it_tabs[0]:
            from mod_admin_it import render_it
            render_it()

        with it_tabs[1]:
            st.markdown("### ðŸ“§ ConfiguraÃ§Ã£o de Email SMTP")
            st.info("""
            **Para configurar emails:**
            1. Vai ao Google Cloud Console â†’ Secret Manager
            2. Adiciona: SMTP_SERVER, SMTP_PORT, SMTP_USER,
               SMTP_PASSWORD, SMTP_FROM_NAME
            3. Reinicia o Cloud Run
            """)
            from core import get_smtp_config, testar_smtp
            config = get_smtp_config()
            if config:
                st.success("âœ… SMTP Configurado!")
                st.markdown(
                    f"<div style='background:rgba(16,185,129,0.1);"
                    f"border:2px solid #10B981;border-radius:10px;"
                    f"padding:20px;'>"
                    f"<p><b>Server:</b> {config['server']}</p>"
                    f"<p><b>Porta:</b> {config['port']}</p>"
                    f"<p><b>User:</b> {config['user']}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                st.divider()
                email_teste = st.text_input(
                    "Email para teste",
                    placeholder="exemplo@email.com",
                    key="smtp_test_email"
                )
                if st.button(
                    "ðŸ“§ Enviar Email de Teste",
                    use_container_width=True, type="primary"
                ):
                    if email_teste:
                        with st.spinner("A enviar..."):
                            if testar_smtp(email_teste):
                                st.success(f"âœ… Email enviado para {email_teste}!")
                            else:
                                st.error("âŒ Falha. Verifica a configuraÃ§Ã£o.")
                    else:
                        st.warning("âš ï¸ Insere um email.")
            else:
                st.warning("âš ï¸ SMTP nÃ£o configurado.")

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 9 â€” HSE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tabs[9]:
        st.markdown("### ðŸ›¡ï¸ SeguranÃ§a e HSE")
        tab_inc, tab_sw = st.tabs(["âš ï¸ Incidentes", "ðŸš¶ Safety Walks"])

        with tab_inc:
            if not incs_db.empty:
                hse = incs_db[
                    incs_db.get('Tipo','') != 'Avaria'
                ] if 'Tipo' in incs_db.columns else incs_db
                cols_hse = [c for c in [
                    'ID','Data','Utilizador','Obra',
                    'Descricao','Gravidade','Status'
                ] if c in hse.columns]
                st.dataframe(
                    hse[cols_hse],
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("ðŸ“‹ Sem incidentes.")

        with tab_sw:
            if not sw_db.empty:
                st.dataframe(
                    sw_db, use_container_width=True, hide_index=True
                )
            else:
                st.info("ðŸ“‹ Sem safety walks.")


# =============================================================================
# FUNÃ‡Ã•ES AUXILIARES DE FATURAÃ‡ÃƒO
# =============================================================================

def _render_custos_por_obra(
    obras_db, registos_db, req_mat_db,
    req_fer_db, req_epi_db, incs_db
):
    import pandas as pd
    from core import fh, load_db
    st.markdown("### ðŸ“Š Custos Totais por Obra")

    if obras_db.empty:
        st.info("ðŸ“‹ Sem obras.")
        return

    obras_ativas = obras_db[obras_db['Ativa'] == 'Ativa']['Obra'].tolist()
    if not obras_ativas:
        st.info("ðŸ“‹ Sem obras ativas.")
        return

    obra_c = st.selectbox("Obra", obras_ativas, key="custos_obra")

    # Horas
    horas_obra = 0
    if not registos_db.empty:
        ro = registos_db[registos_db['Obra'] == obra_c]
        horas_obra = pd.to_numeric(
            ro['Horas_Total'], errors='coerce'
        ).fillna(0).sum()

    # Materiais
    mat_total = 0
    try:
        compras_db = load_db("compras.csv", [
            "Obra","Total","Status"
        ], silent=True)
        if not compras_db.empty:
            mc = compras_db[compras_db['Obra'] == obra_c]
            mat_total = pd.to_numeric(
                mc['Total'], errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    # Dormidas
    dorm_total = 0
    try:
        dormidas_db = load_db("dormidas.csv", [
            "Obra","Total"
        ], silent=True)
        if not dormidas_db.empty:
            dc = dormidas_db[dormidas_db['Obra'] == obra_c]
            dorm_total = pd.to_numeric(
                dc['Total'], errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    # CombustÃ­vel frota
    comb_total = 0
    try:
        comb_db = load_db("frota_combustivel.csv", [
            "Valor"
        ], silent=True)
        if not comb_db.empty:
            comb_total = pd.to_numeric(
                comb_db['Valor'], errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("â±ï¸ Horas",      fh(horas_obra))
    with c2: st.metric("ðŸ“¦ Materiais",  f"â‚¬ {mat_total:.2f}")
    with c3: st.metric("ðŸ¨ Dormidas",   f"â‚¬ {dorm_total:.2f}")
    with c4: st.metric("â›½ CombustÃ­vel", f"â‚¬ {comb_total:.2f}")

    total_custos = mat_total + dorm_total + comb_total
    st.metric("ðŸ’° Total Custos (sem horas)", f"â‚¬ {total_custos:.2f}")


def _render_folhas_ponto_fat(folhas_db, folhas_ocr_db, obras_db):
    import pandas as pd
    st.markdown("### ðŸ“„ Folhas de Ponto por Obra")

    obras_lista = obras_db[
        obras_db['Ativa'] == 'Ativa'
    ]['Obra'].tolist() if not obras_db.empty else []

    if not obras_lista:
        st.info("ðŸ“‹ Sem obras ativas.")
        return

    obra_fp = st.selectbox("Obra", obras_lista, key="fat_fp_obra")

    # Folhas assinadas
    st.markdown("#### âœï¸ Folhas Assinadas pelo Chefe")
    if not folhas_db.empty and 'Obra' in folhas_db.columns:
        fp_obra = folhas_db[folhas_db['Obra'] == obra_fp]
        if not fp_obra.empty:
            cols_fp = [c for c in [
                'Periodo','Responsavel','Data_Assinatura','Selo','Status'
            ] if c in fp_obra.columns]
            st.dataframe(
                fp_obra[cols_fp],
                use_container_width=True, hide_index=True
            )
        else:
            st.info(f"ðŸ“‹ Sem folhas assinadas para {obra_fp}.")
    else:
        st.info("ðŸ“‹ Sem folhas.")

    # Folhas OCR (extraÃ­das por IA)
    st.markdown("---")
    st.markdown("#### ðŸ¤– Folhas ExtraÃ­das por IA (OCR)")
    if not folhas_ocr_db.empty and 'Obra' in folhas_ocr_db.columns:
        ocr_obra = folhas_ocr_db[folhas_ocr_db['Obra'] == obra_fp]
        if not ocr_obra.empty:
            cols_ocr = [c for c in [
                'Semana_Inicio','Semana_Fim','Tecnico',
                'Horas_Folha','Extraido_Em','Extraido_Por'
            ] if c in ocr_obra.columns]
            st.dataframe(
                ocr_obra[cols_ocr],
                use_container_width=True, hide_index=True
            )

            # Admin pode ver e descarregar
            st.markdown("---")
            st.markdown("#### ðŸ‘ï¸ Ver Folha de Ponto (Imagem)")
            periodos_ocr = ocr_obra['Semana_Inicio'].unique().tolist()
            periodo_ver  = st.selectbox(
                "PerÃ­odo", periodos_ocr, key="fat_periodo_ver"
            )
            ocr_periodo = ocr_obra[
                ocr_obra['Semana_Inicio'] == periodo_ver
            ]
            if not ocr_periodo.empty:
                img_b64 = ocr_periodo.iloc[0].get('Imagem_b64','')
                if img_b64 and len(img_b64) > 100:
                    import base64
                    try:
                        st.image(
                            f"data:image/jpeg;base64,{img_b64}",
                            caption=f"Folha de ponto â€” {periodo_ver}",
                            use_column_width=True
                        )
                        img_bytes = base64.b64decode(img_b64)
                        st.download_button(
                            "ðŸ“¥ Descarregar Imagem",
                            data=img_bytes,
                            file_name=f"folha_{obra_fp}_{periodo_ver.replace('/','')}.jpg",
                            mime="image/jpeg",
                            key="dl_folha_img"
                        )
                    except:
                        st.info("ðŸ“· Imagem nÃ£o disponÃ­vel para visualizaÃ§Ã£o.")
                else:
                    st.info("ðŸ“· Imagem nÃ£o armazenada neste registo.")
        else:
            st.info(f"ðŸ“‹ Sem folhas OCR para {obra_fp}.")
    else:
        st.info("ðŸ“‹ Sem folhas OCR disponÃ­veis.")


def _render_emissao_mensal(
    obras_db, registos_db, faturas_db, diarias_pagamentos_db
):
    import pandas as pd
    from core import fh, save_db, load_db
    import uuid
    from datetime import datetime

    st.markdown("### ðŸ“¤ EmissÃ£o de Fatura Mensal ao Cliente")
    st.info(
        "Gera o resumo mensal de custos por obra para enviar ao cliente."
    )

    obras_ativas = obras_db[
        obras_db['Ativa'] == 'Ativa'
    ]['Obra'].tolist() if not obras_db.empty else []

    if not obras_ativas:
        st.info("ðŸ“‹ Sem obras ativas.")
        return

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        obra_em = st.selectbox("Obra", obras_ativas, key="emissao_obra")
    with col_e2:
        import calendar
        hoje_em = datetime.now()
        meses   = {
            "Janeiro":1,"Fevereiro":2,"MarÃ§o":3,"Abril":4,
            "Maio":5,"Junho":6,"Julho":7,"Agosto":8,
            "Setembro":9,"Outubro":10,"Novembro":11,"Dezembro":12
        }
        mes_sel_em = st.selectbox(
            "MÃªs",
            list(meses.keys()),
            index=hoje_em.month - 1,
            key="emissao_mes"
        )

    mes_num = meses[mes_sel_em]
    ano_em  = hoje_em.year

    # Horas processadas (Status 3)
    horas_fat = 0
    valor_horas = 0
    if not registos_db.empty:
        regs_em = registos_db[
            (registos_db['Obra']   == obra_em) &
            (registos_db['Status'] == '3')
        ].copy()
        regs_em['Data_d'] = pd.to_datetime(
            regs_em['Data'], dayfirst=True, errors='coerce'
        )
        regs_mes = regs_em[
            (regs_em['Data_d'].dt.month == mes_num) &
            (regs_em['Data_d'].dt.year  == ano_em)
        ]
        horas_fat = pd.to_numeric(
            regs_mes['Horas_Total'], errors='coerce'
        ).fillna(0).sum()

    # DiÃ¡rias do mÃªs
    diarias_mes = 0
    if not diarias_pagamentos_db.empty:
        dp_em = diarias_pagamentos_db[
            diarias_pagamentos_db['Obras'].str.contains(
                obra_em, na=False
            )
        ]
        diarias_mes = pd.to_numeric(
            dp_em['Valor_Total'], errors='coerce'
        ).fillna(0).sum()

    # Materiais
    mat_mes = 0
    try:
        compras_em = load_db("compras.csv",["Obra","Total"], silent=True)
        if not compras_em.empty:
            mat_mes = pd.to_numeric(
                compras_em[compras_em['Obra'] == obra_em]['Total'],
                errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    # Dormidas
    dorm_mes = 0
    try:
        dorm_em = load_db("dormidas.csv",["Obra","Total"], silent=True)
        if not dorm_em.empty:
            dorm_mes = pd.to_numeric(
                dorm_em[dorm_em['Obra'] == obra_em]['Total'],
                errors='coerce'
            ).fillna(0).sum()
    except:
        pass

    st.markdown(f"#### ðŸ“Š Resumo â€” {mes_sel_em} {ano_em} â€” {obra_em}")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("â±ï¸ Horas",     fh(horas_fat))
    with c2: st.metric("ðŸ’¶ DiÃ¡rias",   f"â‚¬ {diarias_mes:.2f}")
    with c3: st.metric("ðŸ“¦ Materiais", f"â‚¬ {mat_mes:.2f}")
    with c4: st.metric("ðŸ¨ Dormidas",  f"â‚¬ {dorm_mes:.2f}")

    total_fat = diarias_mes + mat_mes + dorm_mes
    st.metric("ðŸ’° Total a Faturar (sem horas)", f"â‚¬ {total_fat:.2f}")
    st.info(
        "â„¹ï¸ O valor das horas depende do preÃ§o/hora contratado com o cliente."
    )

    if st.button(
        "ðŸ“„ Gerar Resumo PDF",
        key="btn_gerar_fat_mensal",
        type="primary",
        use_container_width=True
    ):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            )
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            import io

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4,
                                    rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            story  = []

            story.append(Paragraph(
                f"RESUMO DE FATURAÃ‡ÃƒO â€” {mes_sel_em.upper()} {ano_em}",
                styles['Heading1']
            ))
            story.append(Paragraph(
                f"Obra: {obra_em}", styles['Normal']
            ))
            story.append(Spacer(1, 0.5*cm))

            dados_pdf = [
                ["DescriÃ§Ã£o", "Valor (â‚¬)"],
                ["Horas trabalhadas", f"{fh(horas_fat)}"],
                ["Ajudas de custo (diÃ¡rias)", f"â‚¬ {diarias_mes:.2f}"],
                ["Materiais/Compras", f"â‚¬ {mat_mes:.2f}"],
                ["Alojamento (dormidas)", f"â‚¬ {dorm_mes:.2f}"],
                ["TOTAL (sem horas)", f"â‚¬ {total_fat:.2f}"],
            ]
            t = Table(dados_pdf, colWidths=[12*cm, 5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0),(-1,0),  colors.HexColor('#1E293B')),
                ('TEXTCOLOR',     (0,0),(-1,0),  colors.white),
                ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0,0),(-1,-1), 11),
                ('GRID',          (0,0),(-1,-1), 0.5, colors.grey),
                ('BACKGROUND',    (0,-1),(-1,-1),colors.HexColor('#F1F5F9')),
                ('FONTNAME',      (0,-1),(-1,-1),'Helvetica-Bold'),
                ('TOPPADDING',    (0,0),(-1,-1), 8),
                ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph(
                f"Documento gerado em "
                f"{datetime.now().strftime('%d/%m/%Y %H:%M')} â€” GESTNOW v3.0",
                styles['Normal']
            ))
            doc.build(story)
            buf.seek(0)

            st.download_button(
                f"ðŸ“¥ Descarregar PDF â€” {mes_sel_em} {ano_em}",
                data=buf.getvalue(),
                file_name=(
                    f"faturacao_{obra_em.replace(' ','_')}_"
                    f"{mes_num:02d}_{ano_em}.pdf"
                ),
                mime="application/pdf",
                key="dl_fat_mensal_pdf"
            )
        except Exception as e:
            st.error(f"âŒ Erro ao gerar PDF: {e}")



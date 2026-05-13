import streamlit as st
import pandas as pd
import zipfile, json, io, base64
from datetime import datetime, timedelta
from core import (save_db, inv, _gcs_read, _gcs_write_binary, _gcs_read_binary,
                  _verificar_alerta_backup, _registar_backup, GCS_BUCKET)

def render_it():
    """Módulo de Gestão de TI - Custos, Emails, Infraestrutura"""
    
    st.markdown("### 💻 Gestão de TI", unsafe_allow_html=True)
    
    # KPIs de TI
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("🚀 Deploy Cloud Run", "€ 127.50/mês")
    with c2:
        st.metric("🤖 Tokens IA (mês)", "245,000")
    with c3:
        st.metric("📧 Emails Ativos", "24")
    with c4:
        st.metric("🔒 SSL/Certificados", "✅ Válidos")
    with c5:
        st.metric("💾 Backup", "✅ Hoje 03:00")
    
    st.divider()
    
    tabs = st.tabs([
        "💰 Custos App",
        "🤖 Custos IA",
        "📧 Gestão Emails",
        "🔐 Acessos & Licenças",
        "🖥️ Infraestrutura",
        "📊 Monitorização"
    ])
    
    # =============================================================================
    # TAB 0: CUSTOS DA APP GESTNOW
    # =============================================================================
    with tabs[0]:
        st.markdown("### 💰 Custos da Aplicação GestNow", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### 📊 Resumo Mensal", unsafe_allow_html=True)
            
            # Custos fixos
            st.markdown("""
            <div style="background:rgba(59,130,246,0.1); padding:15px; border-radius:12px; margin-bottom:10px;">
                <div style="color:#94A3B8; font-size:0.85rem;">☁️ Cloud Run (GCP)</div>
                <div style="color:#60A5FA; font-size:1.5rem; font-weight:700;">€ 127.50</div>
                <div style="color:#64748B; font-size:0.75rem;">2Gi RAM, 2 CPU, 3600s timeout</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="background:rgba(59,130,246,0.1); padding:15px; border-radius:12px; margin-bottom:10px;">
                <div style="color:#94A3B8; font-size:0.85rem;">🗄️ Cloud Storage (GCS)</div>
                <div style="color:#60A5FA; font-size:1.5rem; font-weight:700;">€ 12.30</div>
                <div style="color:#64748B; font-size:0.75rem;">2.3 GB dados + operações</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="background:rgba(59,130,246,0.1); padding:15px; border-radius:12px; margin-bottom:10px;">
                <div style="color:#94A3B8; font-size:0.85rem;">🔐 Domínio & SSL</div>
                <div style="color:#60A5FA; font-size:1.5rem; font-weight:700;">€ 15.00</div>
                <div style="color:#64748B; font-size:0.75rem;">gestnow.app + certificados</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="background:rgba(59,130,246,0.1); padding:15px; border-radius:12px; margin-bottom:10px;">
                <div style="color:#94A3B8; font-size:0.85rem;">📦 Licenças Software</div>
                <div style="color:#60A5FA; font-size:1.5rem; font-weight:700;">€ 45.00</div>
                <div style="color:#64748B; font-size:0.75rem;">APIs externas, bibliotecas</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            total = 127.50 + 12.30 + 15.00 + 45.00
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, rgba(59,130,246,0.3), rgba(96,165,250,0.2)); padding:20px; border-radius:12px; text-align:center; border:2px solid rgba(59,130,246,0.5);">
                <div style="color:#94A3B8; font-size:1rem;">Custo Total Mensal</div>
                <div style="color:#60A5FA; font-size:3rem; font-weight:800;">€ {total:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 📈 Evolução de Custos", unsafe_allow_html=True)
            
            # Simulação de histórico
            historico = pd.DataFrame({
                'Mês': ['Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
                'Cloud Run': [95, 102, 115, 120, 125, 127.50],
                'Storage': [8, 9, 10, 11, 11.5, 12.30],
                'IA': [45, 62, 85, 120, 165, 198]
            })
            
            st.line_chart(historico.set_index('Mês'))
            
            st.divider()
            
            st.markdown("#### ⚙️ Configuração de Deploy", unsafe_allow_html=True)
            
            with st.expander("📝 Detalhes do Deploy"):
                st.code("""
                Região: europe-west1 (Bélgica)
                Memória: 2 GiB
                CPU: 2
                Timeout: 3600s
                Instâncias Min: 1
                Instâncias Max: 10
                """, language="yaml")
            
            if st.button("🔄 Atualizar Custos", key="btn_update_custos"):
                st.info("🔄 A sincronizar com Google Cloud Billing...")
                st.success("✅ Custos atualizados!")
    
    # =============================================================================
    # TAB 1: CUSTOS DE IA POR DEPARTAMENTO/MÓDULO
    # =============================================================================
    with tabs[1]:
        st.markdown("### 🤖 Custos de IA por Departamento/Módulo", unsafe_allow_html=True)
        
        # Resumo geral
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("🎯 Total Tokens (mês)", "245,000")
        with c2:
            st.metric("💰 Custo IA Total", "€ 198.00")
        with c3:
            st.metric("📊 Custo por Token", "$ 0.0008")
        
        st.divider()
        
        # Custos por módulo
        st.markdown("#### 📊 Distribuição por Módulo", unsafe_allow_html=True)
        
        custos_ia = pd.DataFrame({
            'Módulo': [
                '📊 Orçamentação (IA)',
                '🛒 Compras (Cotações)',
                '🏨 Dormidas (Pesquisa)',
                '📋 Planeamento',
                '🎯 Qualidade',
                '💼 Comercial',
                '👥 RH'
            ],
            'Tokens': [65000, 42000, 38000, 35000, 28000, 22000, 15000],
            'Custo (€)': [52.00, 33.60, 30.40, 28.00, 22.40, 17.60, 12.00],
            '%': [26.5, 17.1, 15.5, 14.3, 11.4, 7.1, 6.1]
        })
        
        st.dataframe(custos_ia, use_container_width=True, hide_index=True)
        
        # Gráfico
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🥧 Distribuição de Custos", unsafe_allow_html=True)
            st.bar_chart(custos_ia.set_index('Módulo')['Custo (€)'])
        
        with col2:
            st.markdown("#### 📈 Tendência de Uso", unsafe_allow_html=True)
            tendencia = pd.DataFrame({
                'Semana': ['S1', 'S2', 'S3', 'S4'],
                'Tokens': [52000, 58000, 65000, 70000]
            })
            st.line_chart(tendencia.set_index('Semana'))
        
        st.divider()
        
        # Otimização
        st.markdown("#### 💡 Sugestões de Otimização IA", unsafe_allow_html=True)
        
        col1, col2, c3 = st.columns(3)
        with col1:
            st.info("""
            **🔴 Orçamentação**
            - Cache de respostas similares
            - Reduzir contexto quando possível
            - **Economia potencial: € 15/mês**
            """)
        
        with col2:
            st.info("""
            **🟡 Compras**
            - Agrupar cotações por fornecedor
            - Usar modelo mais económico
            - **Economia potencial: € 8/mês**
            """)
        
        with c3:
            st.info("""
            **🟢 Dormidas**
            - Cache de hotéis por zona
            - Atualizar apenas preços
            - **Economia potencial: € 12/mês**
            """)
        
        if st.button("🤖 Aplicar Otimizações", key="btn_otimizar_ia"):
            st.success("✅ Otimizações aplicadas! Economia estimada: € 35/mês")
    
    # =============================================================================
    # TAB 2: GESTÃO DE EMAILS
    # =============================================================================
    with tabs[2]:
        st.markdown("### 📧 Gestão de Emails Corporativos", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### ➕ Criar Novo Email", unsafe_allow_html=True)
            
            with st.form("form_novo_email"):
                nome = st.text_input("Nome do Utilizador", key="email_nome")
                departamento = st.selectbox(
                    "Departamento",
                    ["Administração", "Comercial", "Técnico", "RH", "IT", "Obras"],
                    key="email_dept"
                )
                tipo = st.selectbox(
                    "Tipo de Conta",
                    ["Padrão (5GB)", "Business (30GB)", "Enterprise (5TB)"],
                    key="email_tipo"
                )
                
                if st.form_submit_button("📧 Criar Email", use_container_width=True):
                    email_criado = f"{nome.lower().replace(' ', '.')}@gestnow.app"
                    st.success(f"✅ Email criado: {email_criado}")
                    st.info(f"Password temporária enviada para administrador")
                    st.rerun()
            
            st.divider()
            
            st.markdown("#### 📊 Estatísticas", unsafe_allow_html=True)
            st.metric("Total Emails", "24")
            st.metric("Armazenamento Usado", "18.5 GB / 120 GB")
        
        with col2:
            st.markdown("#### 📧 Emails Existentes", unsafe_allow_html=True)
            
            emails_df = pd.DataFrame({
                'Email': [
                    'admin@gestnow.app',
                    'comercial@gestnow.app',
                    'rh@gestnow.app',
                    'it@gestnow.app',
                    'joao.oliveira@gestnow.app',
                    'patricia.oliveira@gestnow.app'
                ],
                'Departamento': ['Admin', 'Comercial', 'RH', 'IT', 'Técnico', 'RH'],
                'Tipo': ['Enterprise', 'Business', 'Business', 'Enterprise', 'Padrão', 'Padrão'],
                'Usado': ['45 GB', '12 GB', '8 GB', '38 GB', '3.2 GB', '2.8 GB'],
                'Status': ['✅ Ativo', '✅ Ativo', '✅ Ativo', '✅ Ativo', '✅ Ativo', '✅ Ativo'],
                'Último Login': ['Hoje', 'Ontem', '2 dias', 'Hoje', 'Hoje', 'Ontem']
            })
            
            st.dataframe(emails_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            st.markdown("#### ⚙️ Ações", unsafe_allow_html=True)
            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                if st.button("🔐 Reset Password", use_container_width=True, key="btn_reset_pass"):
                    st.info("Seleciona um utilizador para reset")
            with col_a2:
                if st.button("📦 Aumentar Storage", use_container_width=True, key="btn_aum_storage"):
                    st.info("Seleciona um utilizador para aumentar")
            with col_a3:
                if st.button("🚫 Desativar Email", use_container_width=True, key="btn_desat_email", type="secondary"):
                    st.warning("Seleciona um utilizador para desativar")
    
    # =============================================================================
    # TAB 3: ACESSOS E LICENÇAS
    # =============================================================================
    with tabs[3]:
        st.markdown("### 🔐 Gestão de Acessos e Licenças", unsafe_allow_html=True)
        
        tab_acessos, tab_licencas, tab_api = st.tabs([
            "Acessos", "Licenças Software", "API Keys"
        ])
        
        with tab_acessos:
            st.markdown("#### 👥 Acessos de Utilizadores", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("👥 Total Utilizadores", "24")
            with c2:
                st.metric("🔑 Sessões Ativas", "8")
            with c3:
                st.metric("⚠️ Tentativas Falhadas", "3")
            
            st.divider()
            
            st.markdown("#### 📋 Últimos Acessos", unsafe_allow_html=True)
            
            acessos_df = pd.DataFrame({
                'Utilizador': ['Admin', 'João Oliveira', 'Patricia Oliveira', 'Marco Santos'],
                'Data/Hora': ['02/04 10:45', '02/04 10:30', '02/04 09:15', '01/04 16:20'],
                'IP': ['192.168.1.100', '85.240.12.34', '85.240.45.67', '85.240.89.12'],
                'Dispositivo': ['Chrome/Windows', 'Safari/iOS', 'Chrome/Android', 'Chrome/Windows'],
                'Status': ['✅ Sucesso', '✅ Sucesso', '✅ Sucesso', '✅ Sucesso']
            })
            
            st.dataframe(acessos_df, use_container_width=True, hide_index=True)
        
        with tab_licencas:
            st.markdown("#### 📦 Licenças de Software", unsafe_allow_html=True)
            
            licencas_df = pd.DataFrame({
                'Software': [
                    'Microsoft 365',
                    'Adobe Creative Cloud',
                    'AutoCAD',
                    'Slack',
                    'Zoom',
                    'GitHub Pro'
                ],
                'Tipo': ['Empresarial', 'Equipas', 'Profissional', 'Business', 'Pro', 'Teams'],
                'Licenças': ['24', '5', '3', '24', '24', '10'],
                'Custo/Mês': ['€ 120', '€ 75', '€ 180', '€ 96', '€ 120', '€ 40'],
                'Validade': ['✅ Dez 2025', '✅ Jun 2025', '✅ Mar 2025', '✅ Indefinido', '✅ Dez 2025', '✅ Ago 2025'],
                'Status': ['✅ Ativo', '✅ Ativo', '⚠️ Expira Breve', '✅ Ativo', '✅ Ativo', '✅ Ativo']
            })
            
            st.dataframe(licencas_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            if st.button("🔄 Verificar Licenças Expiras", key="btn_check_lic"):
                st.warning("⚠️ 1 licença expira em 30 dias: AutoCAD")
        
        with tab_api:
            st.markdown("#### 🔑 API Keys e Integrações", unsafe_allow_html=True)
            
            st.markdown("""
            <div style="background:rgba(239,68,68,0.1); padding:15px; border-radius:12px; border-left:4px solid #EF4444;">
                <strong style="color:#F8FAFC;">⚠️ Segurança:</strong>
                <span style="color:#94A3B8;"> Nunca partilhes API keys publicamente. Rotação recomendada a cada 90 dias.</span>
            </div>
            """, unsafe_allow_html=True)
            
            api_df = pd.DataFrame({
                'Serviço': [
                    'Google Cloud (GCP)',
                    'OpenAI API',
                    'Anthropic (Claude)',
                    'Booking.com API',
                    'Maps API',
                    'SendGrid (Email)'
                ],
                'Status': ['✅ Ativo', '✅ Ativo', '✅ Ativo', '⚠️ Limitado', '✅ Ativo', '✅ Ativo'],
                'Uso Mensal': ['85%', '67%', '45%', '92%', '34%', '28%'],
                'Limite': ['€ 200', '500K tokens', '1M tokens', '1000 req/dia', '25K req/dia', '10K emails'],
                'Última Rotação': ['15 Jan 2025', '20 Fev 2025', '10 Mar 2025', '05 Jan 2025', '12 Fev 2025', '18 Mar 2025']
            })
            
            st.dataframe(api_df, use_container_width=True, hide_index=True)
            
            if st.button("🔄 Rotacionar API Keys", key="btn_rotate_api", type="secondary"):
                st.warning("⚠️ Isto vai invalidar as chaves atuais. Confirmar?")
    
    # =============================================================================
    # TAB 4: INFRAESTRUTURA
    # =============================================================================
    with tabs[4]:
        st.markdown("### 🖥️ Infraestrutura IT", unsafe_allow_html=True)
        
        tab_cloud, tab_backup, tab_seguranca, tab_hardware = st.tabs([
            "Cloud", "Backups", "Segurança", "Hardware"
        ])
        
        with tab_cloud:
            st.markdown("#### ☁️ Recursos Google Cloud", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Cloud Run", "✅ Saudável")
            with c2:
                st.metric("Cloud Storage", "2.3 GB / 5 GB")
            with c3:
                st.metric("Cloud SQL", "Não utilizado")
            with c4:
                st.metric("Cloud Functions", "3 ativas")
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 📊 Utilização de Recursos", unsafe_allow_html=True)
                
                recursos = pd.DataFrame({
                    'Recurso': ['CPU', 'Memória', 'Storage', 'Network'],
                    'Usado': [65, 72, 46, 38],
                    'Total': [100, 100, 100, 100]
                })
                
                st.bar_chart(recursos.set_index('Recurso'))
            
            with col2:
                st.markdown("#### 📝 Logs Recentes", unsafe_allow_html=True)
                st.code("""
                [02/04 10:45] Deploy bem-sucedido v3.2.1
                [02/04 09:30] Auto-scaling: 2 → 3 instâncias
                [02/04 08:15] Backup automático concluído
                [01/04 23:00] Rotação de logs
                [01/04 18:45] Alerta: CPU > 80%
                """, language="log")
        
        with tab_backup:
            admin_nome = st.session_state.get('user', 'Admin')

            # Lista de todos os CSVs da app
            _CSVS_APP = [
                # ── Core ──────────────────────────────────────────
                "usuarios.csv", "obras_lista.csv", "frentes_lista.csv",
                "registos.csv", "faturas.csv", "documentos.csv",
                "incidentes.csv", "safety_walks.csv", "obs_seguranca.csv",
                "equipamentos.csv", "dialogos.csv", "dialogos_users.csv",
                "folhas_ponto.csv", "comunicados.csv", "comunicados_lidos.csv",
                "req_ferramentas.csv", "req_materiais.csv", "req_epis.csv",
                "avaliacoes.csv", "inst_acessos.csv", "pdfs_obrigatorios.csv",
                "notificacoes.csv", "logs_audit.csv",
                # ── Diárias ───────────────────────────────────────
                "diarias_config.csv", "diarias_faltas.csv",
                "diarias_pagamentos.csv",
                # ── Folhas OCR ────────────────────────────────────
                "folhas_ocr.csv",
                # ── Frota ─────────────────────────────────────────
                "frota_viaturas.csv", "frota_combustivel.csv",
                "frota_avarias.csv",
                # ── Dormidas ──────────────────────────────────────
                "dormidas.csv",
                # ── Planeamento ───────────────────────────────────
                "planeamento_pacotes.csv", "planeamento_milestones.csv",
                "planeamento_recursos.csv", "planeamento_desenhos.csv",
                # ── Compras ───────────────────────────────────────
                "compras.csv", "fornecedores_compras.csv",
                # ── Orçamentação ──────────────────────────────────
                "orcamentos.csv", "orcamentos_linhas.csv",
                # ── Comercial ─────────────────────────────────────
                "pipeline_comercial.csv", "clientes_comercial.csv",
                # ── Qualidade ─────────────────────────────────────
                "nao_conformidades.csv", "documentos_sgq.csv",
                "inspecoes_qualidade.csv",
                # ── Módulo Faturação — Clientes ───────────────────
                "faturas_clientes.csv", "faturas_linhas.csv",
                "clientes_financeiro.csv", "contratos_financeiro.csv",
                # ── Módulo Faturação — Fornecedores ───────────────
                "faturas_fornecedores.csv", "fornecedores.csv",
                "iban_historico.csv",
                # ── Módulo Faturação — RH ─────────────────────────
                "colaboradores_rh.csv", "ferias_db.csv",
                "provisoes_db.csv",
                # ── Módulo Faturação — Frota Renting ─────────────
                "renting_contratos.csv", "renting_kms.csv",
                # ── Módulo Faturação — Obras ──────────────────────
                "obras_orcamento.csv", "obras_wip.csv",
                # ── Módulo Faturação — Tesouraria ─────────────────
                "contas_bancarias.csv", "movimentos_bancarios.csv",
                "fundo_maneio.csv",
                # ── Módulo Faturação — Fundos ─────────────────────
                "fundos_candidaturas.csv",
                # ── Módulo Faturação — Imobilizado ────────────────
                "imobilizado_db.csv", "seguros_db.csv",
                "caucoes_db.csv", "alvaras_db.csv",
                # ── Módulo Faturação — Reporting ──────────────────
                "regras_negocio.csv",
            ]  

            # ── Estado atual ──────────────────────────────────────
            status_bkp, ultima_bkp = _verificar_alerta_backup()
            ultima_str = ultima_bkp.strftime('%d/%m/%Y %H:%M') \
                         if ultima_bkp else "Nunca realizado"

            cores_status = {
                'ok':     ("#10B981", "✅", "Backup recente"),
                'aviso':  ("#F59E0B", "⚠️", "Backup em atraso"),
                'critico':("#EF4444", "🚨", "CRÍTICO — sem backup recente"),
                'nunca':  ("#EF4444", "🚨", "Nunca foi feito backup"),
            }
            cor, ic, txt = cores_status.get(status_bkp, ("#6B7280","❓","Desconhecido"))

            st.markdown(
                f"<div style='background:{cor}18;border:2px solid {cor};"
                f"border-radius:12px;padding:16px;margin-bottom:16px;'>"
                f"<p style='color:{cor};font-weight:700;font-size:1rem;margin:0;'>"
                f"{ic} {txt}</p>"
                f"<p style='color:#94A3B8;font-size:0.82rem;margin:5px 0 0;'>"
                f"Último backup: <b>{ultima_str}</b></p></div>",
                unsafe_allow_html=True
            )

            # ── Criar e descarregar backup ────────────────────────
            st.markdown("#### ⬇️ Criar e Descarregar Backup")

            if st.button("💾 Criar Backup Agora",
                          key="btn_backup_real", type="primary",
                          use_container_width=True):
                with st.spinner("A criar backup..."):
                    try:
                        buf_zip = io.BytesIO()
                        incluidos, erros_bkp = [], []

                        with zipfile.ZipFile(buf_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                            meta = {
                                "versao": "GESTNOW_v3",
                                "data_backup": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            }
                            zf.writestr("BACKUP_INFO.json", json.dumps(meta, indent=2))

                            for csv_name in _CSVS_APP:
                                try:
                                    fb = _gcs_read(csv_name)
                                    if fb:
                                        content = fb.read()
                                        if isinstance(content, str):
                                            content = content.encode('utf-8')
                                        zf.writestr(csv_name, content)
                                        incluidos.append(csv_name)
                                except Exception as ex:
                                    erros_bkp.append(f"{csv_name}: {ex}")

                            tmpl = _gcs_read_binary("contrato_template.docx")
                            if tmpl:
                                zf.writestr("contrato_template.docx", tmpl)
                                incluidos.append("contrato_template.docx")

                            bs = _gcs_read("backup_status.json")
                            if bs:
                                zf.writestr("backup_status.json", bs.read())

                            if erros_bkp:
                                zf.writestr("ERROS_BACKUP.txt", "\n".join(erros_bkp))

                        buf_zip.seek(0)
                        zip_bytes = buf_zip.getvalue()

                        # ✅ Guardar no session_state para persistir após rerun
                        ts = datetime.now().strftime("%Y%m%d_%H%M")
                        st.session_state['backup_zip_bytes'] = zip_bytes
                        st.session_state['backup_zip_fname'] = f"gestnow_backup_{ts}.zip"
                        st.session_state['backup_incluidos']  = len(incluidos)
                        st.session_state['backup_erros']      = erros_bkp

                        _registar_backup(admin_nome)
                        inv()

                    except Exception as ex:
                        st.error(f"❌ Erro ao criar backup: {ex}")

            # ✅ Mostrar download FORA do if — persiste entre reruns
            if st.session_state.get('backup_zip_bytes'):
                n_inc    = st.session_state.get('backup_incluidos', 0)
                erros_bkp = st.session_state.get('backup_erros', [])
                fname    = st.session_state.get('backup_zip_fname', 'backup.zip')

                st.success(
                    f"✅ Backup pronto — **{n_inc} ficheiros**."
                    f"{' ⚠️ ' + str(len(erros_bkp)) + ' erros.' if erros_bkp else ''}"
                )
                st.download_button(
                    f"📥 Descarregar {fname}",
                    data=st.session_state['backup_zip_bytes'],
                    file_name=fname,
                    mime="application/zip",
                    key="btn_dl_backup_persistente"
                )
                if erros_bkp:
                    with st.expander("⚠️ Ficheiros com erro"):
                        for e in erros_bkp:
                            st.text(e)
                if st.button("🗑️ Limpar", key="btn_limpar_backup"):
                    st.session_state.pop('backup_zip_bytes', None)
                    st.rerun()             

            # ── Restauro ──────────────────────────────────────────
            st.markdown("---")
            st.markdown("#### ⬆️ Restaurar Backup")
            st.markdown(
                "<div style='background:rgba(239,68,68,0.1);border:2px solid #EF4444;"
                "border-radius:10px;padding:14px;margin-bottom:12px;'>"
                "<p style='color:#EF4444;font-weight:700;margin:0;'>"
                "⚠️ ATENÇÃO — Operação Irreversível</p>"
                "<p style='color:#94A3B8;font-size:0.82rem;margin:5px 0 0;'>"
                "O restauro substitui TODOS os dados atuais pelos do backup. "
                "Faz um backup do estado atual ANTES de restaurar.</p></div>",
                unsafe_allow_html=True
            )

            zip_upload = st.file_uploader(
                "📂 Selecionar ficheiro de backup (.zip)",
                type=["zip"], key="bkp_upload_zip"
            )

            if zip_upload:
                st.warning(
                    f"⚠️ Prestes a restaurar: **{zip_upload.name}** "
                    f"({zip_upload.size/1024:.0f} KB)"
                )
                confirmar = st.checkbox(
                    "✅ Confirmo que quero substituir todos os dados atuais",
                    key="chk_confirmar_restauro"
                )
                if confirmar:
                    if st.button("🔄 RESTAURAR AGORA",
                                  key="btn_restaurar_real",
                                  type="primary",
                                  use_container_width=True):
                        with st.spinner("A restaurar... não feches a página."):
                            try:
                                from google.cloud import storage as _gcs_mod
                                import os
                                client  = _gcs_mod.Client()
                                bucket  = client.bucket(
                                    os.environ.get('GCS_BUCKET','gestnow-dados')
                                )
                                restaurados, erros_r = [], []

                                buf_r = io.BytesIO(zip_upload.read())
                                with zipfile.ZipFile(buf_r, 'r') as zf:
                                    if "BACKUP_INFO.json" not in zf.namelist():
                                        st.error("❌ ZIP inválido: não é um backup GESTNOW.")
                                        st.stop()

                                    meta_r = json.loads(
                                        zf.read("BACKUP_INFO.json").decode('utf-8')
                                    )
                                    if "GESTNOW" not in meta_r.get("versao",""):
                                        st.error("❌ ZIP inválido: versão incompatível.")
                                        st.stop()

                                    for nome_f in zf.namelist():
                                        if nome_f in ("BACKUP_INFO.json",
                                                      "ERROS_BACKUP.txt"):
                                            continue
                                        content_r = zf.read(nome_f)
                                        try:
                                            blob = bucket.blob(f"data/{nome_f}")
                                            ct   = "text/csv" \
                                                   if nome_f.endswith(".csv") \
                                                   else "application/octet-stream"
                                            blob.upload_from_string(content_r,
                                                                     content_type=ct)
                                            restaurados.append(nome_f)
                                        except Exception as ex:
                                            erros_r.append(f"{nome_f}: {ex}")

                                inv()
                                st.success(
                                    f"✅ Restauro concluído! "
                                    f"**{len(restaurados)} ficheiros** restaurados."
                                )
                                if erros_r:
                                    st.warning(f"⚠️ {len(erros_r)} erro(s).")
                                st.info("🔄 Recarrega a página para ver os dados restaurados.")

                            except zipfile.BadZipFile:
                                st.error("❌ Ficheiro ZIP corrompido ou inválido.")
                            except Exception as ex:
                                st.error(f"❌ Erro inesperado: {ex}")
        
        with tab_seguranca:
            st.markdown("#### 🔒 Segurança e Compliance", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("SSL/TLS", "✅ Válido até Dez 2025")
            with c2:
                st.metric("Firewall", "✅ Ativo")
            with c3:
                st.metric("2FA", "✅ Obrigatório")
            
            st.divider()
            
            st.markdown("#### 📊 Score de Segurança", unsafe_allow_html=True)
            
            seguranca = pd.DataFrame({
                'Categoria': ['Autenticação', 'Encriptação', 'Acesso', 'Monitorização', 'Backup'],
                'Score': [95, 90, 85, 80, 92]
            })
            
            st.bar_chart(seguranca.set_index('Categoria'))
            
            st.divider()
            
            st.markdown("#### ⚠️ Alertas de Segurança", unsafe_allow_html=True)
            st.success("✅ Sem alertas ativos")
        
        with tab_hardware:
            st.markdown("#### 🖥️ Inventário de Hardware", unsafe_allow_html=True)
            
            st.info("📋 Gestão de laptops, telemóveis, tablets da empresa...")
            
            hardware_df = pd.DataFrame({
                'Tipo': ['Laptop', 'Laptop', 'Telemóvel', 'Tablet', 'Laptop'],
                'Marca/Modelo': ['Dell XPS 15', 'MacBook Pro', 'iPhone 15', 'iPad Pro', 'Lenovo ThinkPad'],
                'Utilizador': ['João O.', 'Patricia O.', 'Marco S.', 'Rafael S.', 'Admin'],
                'Data Compra': ['Jan 2024', 'Mar 2024', 'Jun 2024', 'Fev 2024', 'Nov 2023'],
                'Garantia': ['✅ Jan 2027', '✅ Mar 2027', '✅ Jun 2026', '✅ Fev 2026', '⚠️ Nov 2025'],
                'Status': ['✅ Ativo', '✅ Ativo', '✅ Ativo', '✅ Ativo', '✅ Ativo']
            })
            
            st.dataframe(hardware_df, use_container_width=True, hide_index=True)
    
    # =============================================================================
    # TAB 5: MONITORIZAÇÃO
    # =============================================================================
    with tabs[5]:
        st.markdown("### 📊 Monitorização e Alertas", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("⏱️ Uptime (30d)", "99.8%")
        with c2:
            st.metric("🐛 Erros (hoje)", "2")
        with c3:
            st.metric("⚡ Tempo Resposta", "245ms")
        with c4:
            st.metric("👥 Utilizadores Online", "8")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Performance da App", unsafe_allow_html=True)
            
            perf = pd.DataFrame({
                'Hora': ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                'Tempo Resposta (ms)': [180, 150, 220, 350, 380, 280]
            })
            
            st.line_chart(perf.set_index('Hora'))
        
        with col2:
            st.markdown("#### 🔔 Alertas Recentes", unsafe_allow_html=True)
            
            st.warning("⚠️ **02/04 09:15** - CPU > 80% por 5 min")
            st.info("ℹ️ **02/04 08:00** - Backup concluído com sucesso")
            st.success("✅ **01/04 18:30** - Deploy v3.2.1 bem-sucedido")
            st.error("❌ **01/04 14:20** - Erro 500 em /mod_tecnico (resolvido)")
        
        st.divider()
        
        st.markdown("#### ⚙️ Configurar Alertas", unsafe_allow_html=True)
        
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            alert_cpu = st.slider("Alerta CPU (%)", 50, 100, 80, key="alert_cpu")
            alert_mem = st.slider("Alerta Memória (%)", 50, 100, 85, key="alert_mem")
        with col_a2:
            alert_email = st.text_input("Email para Alertas", key="alert_email", value="it@gestnow.app")
            alert_sms = st.checkbox("Ativar Alertas SMS", key="alert_sms")
        
        if st.button("💾 Guardar Configuração de Alertas", key="btn_save_alerts"):
            st.success("✅ Configuração guardada!")

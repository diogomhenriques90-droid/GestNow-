"""
GESTNOW v3 — mod_cliente.py
Portal do Cliente
"""
import streamlit as st
import pandas as pd
import uuid  # ✅ CORRIGIDO — estava em falta
from datetime import datetime
from core import (
    load_db, save_db, inv, log_audit, criar_notificacao,
    gerar_qr_code_data, parse_qr_code_data, render_qr_code_image
)

def render_cliente_portal():
    st.markdown("""
    <style>
    .cliente-header {
        background: linear-gradient(135deg, #1E293B, #0F172A);
        padding: 30px; border-radius: 20px; margin-bottom: 30px;
        border: 2px solid rgba(59,130,246,0.5);
    }
    .cliente-card {
        background: rgba(59,130,246,0.1);
        border: 2px solid rgba(59,130,246,0.3);
        border-radius: 15px; padding: 20px; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="cliente-header">
        <h1 style="color:#F8FAFC; margin:0;">🏢 Portal do Cliente</h1>
        <p style="color:#94A3B8; margin:10px 0 0 0;">Bem-vindo, <strong style="color:#60A5FA">{st.session_state.user}</strong></p>
        <p style="color:#64748B; margin:5px 0 0 0; font-size:0.9rem;">{datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        obras_db = load_db("obras_lista.csv", ["Obra", "Cliente", "TipoObra", "Ativa"], silent=True)
        logs_db  = load_db("logs_audit.csv",  ["ID","Data","Hora","Usuario","Acao","Tabela","Registro_ID","Detalhes","IP"], silent=True)
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return

    cliente_nome  = st.session_state.user
    obras_cliente = obras_db[
        (obras_db['Cliente'] == cliente_nome) & (obras_db['Ativa'] == 'Ativa')
    ] if not obras_db.empty else pd.DataFrame()

    if obras_cliente.empty:
        st.warning("⚠️ Não tem obras ativas associadas à sua conta.")
        st.info("Contacte o administrador para configurar o acesso às suas obras.")
        return

    obra_sel = st.selectbox("🏗️ Selecione o Projeto", obras_cliente['Obra'].tolist(), key="cliente_obra_sel")
    if not obra_sel:
        return

    o_key = obra_sel.replace(' ', '_').replace('/', '_')

    try:
        insts_db = load_db(f"inst_{o_key}_index.csv", [
            "ID", "Tag", "Tipo", "Descricao", "Status",
            "GPS_Lat", "GPS_Lng", "Assinatura_Calibracao_b64",
            "Assinatura_Instalacao_b64", "Hash_Validacao"
        ], silent=True)
    except:
        insts_db = pd.DataFrame()

    try:
        punch_db = load_db(f"punch_{o_key}.csv", [
            "ID", "Data", "Autor", "Tag", "Descricao", "Prioridade", "Estado"
        ], silent=True)
    except:
        punch_db = pd.DataFrame(columns=["ID","Data","Autor","Tag","Descricao","Prioridade","Estado"])

    # Dashboard de Progresso
    st.markdown("### 📊 Progresso da Obra")
    total     = len(insts_db) if not insts_db.empty else 0
    pendentes = len(insts_db[insts_db['Status'] == '0']) if not insts_db.empty else 0
    mat_ok    = len(insts_db[insts_db['Status'] == '1']) if not insts_db.empty else 0
    calibrados= len(insts_db[insts_db['Status'] == '2']) if not insts_db.empty else 0
    instalados= len(insts_db[insts_db['Status'].isin(['3','4'])]) if not insts_db.empty else 0
    progresso = (instalados / total * 100) if total > 0 else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("📦 Total",      total)
    with c2: st.metric("⏳ Pendentes",  pendentes)
    with c3: st.metric("📦 Material OK",mat_ok)
    with c4: st.metric("🔬 Calibrados", calibrados)
    with c5: st.metric("✅ Instalados", instalados)

    st.progress(progresso / 100)
    st.write(f"**{progresso:.1f}% Concluído**")
    st.divider()

    status_map = {
        '0': '⏳ Pendente', '1': '📦 Material OK',
        '2': '🔬 Calibrado', '3': '📍 Instalado', '4': '✅ Concluído'
    }

    tab_res, tab_inst, tab_qr, tab_apr, tab_docs, tab_punch = st.tabs([
        "📋 Resumo", "🔧 Instrumentos", "📱 QR Codes",
        "✅ Aprovações", "📄 Documentação", "💬 Punch List"
    ])

    # ── TAB RESUMO ───────────────────────────────────────────────────
    with tab_res:
        st.markdown("### 📋 Resumo do Projeto")
        st.markdown(f"""
        <div class="cliente-card">
            <h3>🏗️ {obra_sel}</h3>
            <p><strong>Cliente:</strong> {cliente_nome}</p>
            <p><strong>Progresso:</strong> {progresso:.1f}%</p>
            <p><strong>Instrumentos Instalados:</strong> {instalados} de {total}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🕐 Atividades Recentes")
        if not logs_db.empty:
            logs_obra = logs_db[logs_db['Detalhes'].str.contains(obra_sel, na=False)]
            if not logs_obra.empty:
                for _, log in logs_obra.tail(10).iterrows():
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.05);padding:10px;border-radius:8px;margin-bottom:10px;">
                        <small style="color:#64748B;">{log.get('Data','')} {log.get('Hora','')}</small>
                        <p style="margin:5px 0;color:#F8FAFC;"><strong>{log.get('Acao','')}</strong>: {log.get('Detalhes','')}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📋 Sem atividades recentes.")
        else:
            st.info("📋 Sem logs disponíveis.")

    # ── TAB INSTRUMENTOS ─────────────────────────────────────────────
    with tab_inst:
        st.markdown("### 🔧 Lista de Instrumentos")
        if not insts_db.empty:
            c1, c2 = st.columns(2)
            with c1:
                filt_tipo = st.multiselect("Tipo", insts_db['Tipo'].unique() if 'Tipo' in insts_db.columns else [], key="cli_filt_tipo")
            with c2:
                filt_stat = st.multiselect("Status", list(status_map.values()), key="cli_filt_stat")

            df_f = insts_db.copy()
            if filt_tipo:
                df_f = df_f[df_f['Tipo'].isin(filt_tipo)]
            if filt_stat:
                df_f = df_f[df_f['Status'].map(status_map).isin(filt_stat)]

            if 'Status' in df_f.columns:
                df_f = df_f.copy()
                df_f['Estado'] = df_f['Status'].map(status_map)

            cols_show = [c for c in ['Tag','Tipo','Descricao','Estado'] if c in df_f.columns]
            st.dataframe(df_f[cols_show], use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Sem instrumentos registados para esta obra.")

    # ── TAB QR CODES ─────────────────────────────────────────────────
    with tab_qr:
        st.markdown("### 📱 QR Codes dos Instrumentos")
        if not insts_db.empty and 'Tag' in insts_db.columns:
            tag_sel = st.selectbox("Selecionar Instrumento", insts_db['Tag'].tolist(), key="cli_qr_sel")
            if tag_sel:
                inst = insts_db[insts_db['Tag'] == tag_sel].iloc[0]
                qr_data = gerar_qr_code_data(tag_sel, obra_sel, inst.get('Tipo', 'XX'))
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(render_qr_code_image(qr_data['short'], size=200), caption=f"QR: {tag_sel}")
                with c2:
                    st.markdown(f"""
                    <div class="cliente-card">
                        <h4>🔧 {tag_sel}</h4>
                        <p><strong>Tipo:</strong> {inst.get('Tipo','N/A')}</p>
                        <p><strong>Descrição:</strong> {inst.get('Descricao','N/A')}</p>
                        <p><strong>Status:</strong> {status_map.get(inst.get('Status','0'),'N/A')}</p>
                        <p style="font-family:monospace;font-size:0.8rem;color:#64748B;">QR: {qr_data['short']}</p>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()
            if st.button("📱 Gerar Todos os QR Codes (max 50)", use_container_width=True, type="primary"):
                tags = insts_db['Tag'].head(50).tolist()
                if tags:
                    st.markdown(f"**{len(tags)} QR Codes gerados**")
                    cols = st.columns(5)
                    for i, tag in enumerate(tags):
                        row = insts_db[insts_db['Tag'] == tag]
                        tipo = row.iloc[0].get('Tipo','XX') if not row.empty else 'XX'
                        qr_d = gerar_qr_code_data(tag, obra_sel, tipo)
                        with cols[i % 5]:
                            st.image(render_qr_code_image(qr_d['short'], size=100), caption=tag)
                    st.info("💡 Faz screenshot para guardar as etiquetas.")
        else:
            st.info("ℹ️ Sem instrumentos disponíveis.")

    # ── TAB APROVAÇÕES ───────────────────────────────────────────────
    with tab_apr:
        st.markdown("### ✅ Aprovação de ITRs")
        if not insts_db.empty and 'Status' in insts_db.columns:
            prontos = insts_db[insts_db['Status'].isin(['2','3','4'])]
            if not prontos.empty:
                tag_ap = st.selectbox("Selecione o Instrumento", prontos['Tag'].tolist(), key="cli_apr_tag")
                if tag_ap:
                    inst = prontos[prontos['Tag'] == tag_ap].iloc[0]
                    st.markdown(f"""
                    <div class="cliente-card">
                        <h4>🔧 {tag_ap}</h4>
                        <p><strong>Tipo:</strong> {inst.get('Tipo','N/A')}</p>
                        <p><strong>Descrição:</strong> {inst.get('Descricao','N/A')}</p>
                        <p><strong>Status:</strong> {status_map.get(inst.get('Status','0'),'N/A')}</p>
                        <p><strong>Calibração:</strong> {'✅ Assinada' if inst.get('Assinatura_Calibracao_b64') else '⏳ Pendente'}</p>
                        <p><strong>Instalação:</strong> {'✅ Assinada' if inst.get('Assinatura_Instalacao_b64') else '⏳ Pendente'}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    confirmar = st.checkbox("✅ Confirmo que este instrumento está instalado e funcional", key=f"cli_conf_{tag_ap}")
                    if confirmar:
                        comentario = st.text_area("Comentários (opcional)", key=f"cli_coment_{tag_ap}")
                        if st.button("✅ Aprovar Instrumento", use_container_width=True, type="primary", key=f"cli_btn_apr_{tag_ap}"):
                            log_audit(
                                usuario=f"CLIENTE: {cliente_nome}",
                                acao="APROVAR_INSTRUMENTO_CLIENTE",
                                tabela=f"inst_{o_key}_index.csv",
                                registro_id=tag_ap,
                                detalhes=f"Cliente aprovou {tag_ap}. Comentário: {comentario}",
                                ip=""
                            )
                            criar_notificacao(
                                destinatario="admin",
                                titulo="✅ Cliente Aprovou Instrumento",
                                mensagem=f"{cliente_nome} aprovou {tag_ap} em {obra_sel}",
                                tipo="success",
                                acao_url=f"/instrumentacao?obra={o_key}"
                            )
                            st.success(f"✅ {tag_ap} aprovado com sucesso!")
                            st.rerun()
            else:
                st.info("ℹ️ Nenhum instrumento pronto para aprovação.")
        else:
            st.info("ℹ️ Sem instrumentos disponíveis.")

    # ── TAB DOCUMENTAÇÃO ─────────────────────────────────────────────
    with tab_docs:
        st.markdown("### 📄 Documentação da Obra")
        st.info("""
        **📋 Documentação Disponível:**
        - ✅ Relatórios de Calibração (ITR-A) — por instrumento
        - ✅ Relatórios de Instalação (ITR-B) — por instrumento
        - ✅ Certificados com Assinatura Digital
        - 🔄 Handover Completo — em breve
        - 🔄 Dossier Final da Obra — em breve

        **Para descarregar:** vá à tab Aprovações, selecione o instrumento e após aprovação poderá descarregar o certificado.
        """)

    # ── TAB PUNCH LIST ───────────────────────────────────────────────
    with tab_punch:
        st.markdown("### 💬 Punch List / Comentários")

        if not punch_db.empty:
            st.markdown("#### 📋 Punch List Existente")
            filt_estado = st.selectbox("Filtrar", ["Todos","Aberto","Em Progresso","Fechado"], key="cli_punch_filt")
            pf = punch_db.copy()
            if filt_estado != "Todos":
                pf = pf[pf['Estado'] == filt_estado]

            if not pf.empty:
                for _, item in pf.iterrows():
                    cor = {"Baixa":"#10B981","Média":"#F59E0B","Alta":"#EF4444","Crítica":"#DC2626"}.get(item.get('Prioridade','Média'),"#6B7280")
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.05);border-left:4px solid {cor};
                        padding:15px;border-radius:8px;margin-bottom:15px;">
                        <div style="display:flex;justify-content:space-between;">
                            <strong style="color:{cor};">{item.get('Prioridade','Média')} — {item.get('Tag','N/A')}</strong>
                            <small style="color:#64748B;">{item.get('Data','N/A')}</small>
                        </div>
                        <p style="margin:10px 0;color:#F8FAFC;">{item.get('Descricao','N/A')}</p>
                        <small style="color:#94A3B8;">Autor: {item.get('Autor','N/A')} | Estado: {item.get('Estado','Aberto')}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📋 Sem itens com este filtro.")

        st.divider()
        st.markdown("#### ➕ Adicionar Novo Item")
        with st.form("form_punch_cliente"):
            c1, c2 = st.columns(2)
            with c1: tag_punch  = st.text_input("Tag do Instrumento (opcional)", key="cli_punch_tag")
            with c2: prioridade = st.selectbox("Prioridade", ["Baixa","Média","Alta","Crítica"], key="cli_punch_prior")
            descricao = st.text_area("Descrição do Issue / Comentário", key="cli_punch_desc")

            if st.form_submit_button("💬 Adicionar à Punch List", use_container_width=True, type="primary"):
                if descricao:
                    novo_id = str(uuid.uuid4())[:8].upper()
                    novo_item = pd.DataFrame([{
                        "ID":        novo_id,
                        "Data":      datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Autor":     f"CLIENTE: {cliente_nome}",
                        "Tag":       tag_punch if tag_punch else "N/A",
                        "Descricao": descricao,
                        "Prioridade":prioridade,
                        "Estado":    "Aberto"
                    }])
                    updated = pd.concat([punch_db, novo_item], ignore_index=True) if not punch_db.empty else novo_item
                    save_db(updated, f"punch_{o_key}.csv")
                    log_audit(
                        usuario=f"CLIENTE: {cliente_nome}",
                        acao="CRIAR_PUNCH_ITEM",
                        tabela=f"punch_{o_key}.csv",
                        registro_id=novo_id,
                        detalhes=f"Punch item: {descricao[:50]}",
                        ip=""
                    )
                    criar_notificacao(
                        destinatario="admin",
                        titulo="💬 Novo Punch Item",
                        mensagem=f"{cliente_nome} adicionou issue em {obra_sel}: {descricao[:50]}",
                        tipo="warning",
                        acao_url="/admin?tab=qualidade"
                    )
                    inv()
                    st.success("✅ Item adicionado à punch list!")
                    st.rerun()
                else:
                    st.warning("⚠️ Preenche a descrição.")

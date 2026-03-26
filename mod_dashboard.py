"""
GESTNOW v3 — mod_dashboard.py
Módulo de Dashboard e Funcionalidades Avançadas
"""

import streamlit as st
import pandas as pd
import io
import base64
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid as _uuid_inst

try:
    from core import load_db, save_db, inv, render_metric, render_metric_red
except Exception:
    pass

from translations import t
from mod_voz_assistente import render_voice_assistant_global

# CSS do Dashboard
_DASH_CSS = """
<style>
.dash-card {
    background: white;
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    border: 1px solid #E5EDFF;
    transition: all 0.3s ease;
}
.dash-card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    transform: translateY(-2px);
}
.dash-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #0A2463;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 2px solid #E5EDFF;
    padding-bottom: 8px;
}
.progress-bar {
    background: #E5EDFF;
    border-radius: 12px;
    height: 24px;
    overflow: hidden;
    margin: 12px 0;
}
.progress-fill {
    background: linear-gradient(90deg, #0A2463, #3E92CC);
    height: 100%;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 10px;
    color: white;
    font-size: 0.75rem;
    font-weight: bold;
}
.notification-badge {
    background: #EF4444;
    color: white;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: bold;
    margin-left: 8px;
}
.qr-scanner-container {
    background: #1F2A44;
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    color: white;
}
.status-ok { color: #10B981; font-weight: bold; }
.status-warning { color: #F59E0B; font-weight: bold; }
.status-error { color: #EF4444; font-weight: bold; }
.metric-card {
    text-align: center;
    padding: 15px;
    background: #F8FAFF;
    border-radius: 16px;
}
.metric-value {
    font-size: 2rem;
    font-weight: 800;
    color: #0A2463;
}
.metric-label {
    font-size: 0.8rem;
    color: #6B7280;
}
</style>
"""

STATUS_INST = {
    "0": ("Pendente", "⏳", "#6B7280"),
    "1": ("Material OK", "📦", "#F59E0B"),
    "2": ("Calibrado", "🔬", "#3B82F6"),
    "3": ("Instalado", "🏗️", "#10B981"),
    "4": ("Concluído", "✅", "#10B981"),
}

STATUS_VOZ = {
    "0": "Pendente",
    "1": "Material OK",
    "2": "Calibrado",
    "3": "Instalado",
    "4": "Concluído",
}

def render_dashboard_completo(obra_sel, obra_cod, insts, packing, bom, hookups, punch, itr_a, itr_b, user_atual, obra_key):
    """Render principal do dashboard com todas as funcionalidades"""
    
    st.markdown(_DASH_CSS, unsafe_allow_html=True)
    
    # =========================================================
    # CABEÇALHO DA OBRA
    # =========================================================
    st.markdown(f"""
    <div class="dash-card">
        <div class="dash-title">
            🏗️ {obra_sel}
            <span style="font-size:0.8rem; color:#7A8BA6;">Código: {obra_cod}</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <div>📅 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            <div>👥 Responsável: {user_atual}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # =========================================================
    # MÉTRICAS PRINCIPAIS
    # =========================================================
    total_inst = len(insts) if not insts.empty else 0
    material_ok = len(insts[insts['Status'].isin(['1','2','3','4'])]) if not insts.empty else 0
    calibrados = len(insts[insts['Status'].isin(['2','3','4'])]) if not insts.empty else 0
    instalados = len(insts[insts['Status'].isin(['3','4'])]) if not insts.empty else 0
    punch_a = len(punch[(punch['Categoria']=='A')&(punch['Status']=='Aberto')]) if not punch.empty else 0
    
    pct_material = int((material_ok / total_inst * 100)) if total_inst > 0 else 0
    pct_calibracao = int((calibrados / total_inst * 100)) if total_inst > 0 else 0
    pct_instalacao = int((instalados / total_inst * 100)) if total_inst > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_inst}</div>
            <div class="metric-label">📋 {t('total_instruments')}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{material_ok}</div>
            <div class="metric-label">📦 {t('material_ok')}</div>
            <div class="progress-bar"><div class="progress-fill" style="width:{pct_material}%">{pct_material}%</div></div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{calibrados}</div>
            <div class="metric-label">🔬 {t('calibrated')}</div>
            <div class="progress-bar"><div class="progress-fill" style="width:{pct_calibracao}%">{pct_calibracao}%</div></div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{instalados}</div>
            <div class="metric-label">🏗️ {t('installed')}</div>
            <div class="progress-bar"><div class="progress-fill" style="width:{pct_instalacao}%">{pct_instalacao}%</div></div>
        </div>
        """, unsafe_allow_html=True)
    
    # =========================================================
    # GRÁFICOS
    # =========================================================
    if not insts.empty:
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown("### 📊 Distribuição por Tipo")
            tipo_counts = insts['Tipo'].value_counts().reset_index()
            tipo_counts.columns = ['Tipo', 'Quantidade']
            fig_pie = px.pie(tipo_counts, values='Quantidade', names='Tipo', 
                             title='Instrumentos por Tipo',
                             color_discrete_sequence=px.colors.qualitative.Set2)
            fig_pie.update_layout(height=350, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_graf2:
            st.markdown("### 📈 Status dos Instrumentos")
            status_counts = insts['Status'].map(lambda x: STATUS_INST.get(str(x), ('Desconhecido','',''))[0]).value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            colors_status = [STATUS_INST.get(k, ('','','#6B7280'))[2] for k in status_counts['Status'].map(lambda x: next((k for k,v in STATUS_INST.items() if v[0]==x), '0'))]
            fig_bar = px.bar(status_counts, x='Status', y='Quantidade', 
                            title='Instrumentos por Status',
                            color='Status', text='Quantidade',
                            color_discrete_sequence=colors_status)
            fig_bar.update_layout(height=350)
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # =========================================================
    # ALERTA PUNCH CAT A
    # =========================================================
    if punch_a > 0:
        st.error(f"🔴 **{t('handover_blocked')}** — {punch_a} Punch Item(s) Cat A por fechar.")
    
    st.markdown("---")
    
    # =========================================================
    # TABS DO DASHBOARD
    # =========================================================
    tab_notif, tab_qr, tab_rel, tab_fotos, tab_comp, tab_mapa, tab_email, tab_handover = st.tabs([
        "🔔 Notificações", "📱 QR Scanner", "📄 Relatórios", "📸 Fotos", "🛒 Comparação", "🗺️ Mapa", "📧 Email", "📄 Handover"
    ])
    
    with tab_notif:
        render_notificacoes(insts, packing, punch, itr_a)
    
    with tab_qr:
        render_qr_scanner(insts, obra_sel)
    
    with tab_rel:
        render_relatorios(obra_sel, insts, itr_a, itr_b, punch, packing)
    
    with tab_fotos:
        render_fotos_anexos(insts, obra_key)
    
    with tab_comp:
        render_comparacao_pedido(packing, bom, hookups, insts)
    
    with tab_mapa:
        render_mapa_avancado(insts)
    
    with tab_email:
        render_email_templates(obra_sel, insts, punch)
    
    with tab_handover:
        render_handover_digital(insts, itr_a, itr_b, punch, obra_sel, obra_cod)
    
    # =========================================================
    # ASSISTENTE DE VOZ
    # =========================================================
    render_voice_assistant_global(
        user_tipo=st.session_state.get('tipo', ''),
        user_nome=st.session_state.get('user', ''),
        obra_sel=obra_sel,
        insts=insts,
        itr_a=itr_a,
        itr_b=itr_b,
        punch=punch
    )


def render_notificacoes(insts, packing, punch, itr_a):
    """Exibe notificações e alertas"""
    st.markdown("### 🔔 Notificações e Alertas")
    
    notificacoes = []
    alertas = []
    
    if not packing.empty:
        pendentes = packing[packing['Estado'] == 'Pendente']
        if not pendentes.empty:
            notificacoes.append(f"⚠️ {len(pendentes)} itens pendentes no Packing List")
    
    if not insts.empty:
        sem_material = insts[insts['Status'] == '0']
        if not sem_material.empty:
            notificacoes.append(f"📦 {len(sem_material)} instrumentos aguardam material")
            for _, inst in sem_material.head(3).iterrows():
                notificacoes.append(f"   • {inst.get('Tag')} - {inst.get('Descricao', '')[:40]}")
    
    if not insts.empty:
        prontos_cal = insts[insts['Status'] == '1']
        if not prontos_cal.empty:
            notificacoes.append(f"🔬 {len(prontos_cal)} instrumentos prontos para calibração")
    
    if not punch.empty:
        punch_a = punch[(punch['Categoria'] == 'A') & (punch['Status'] == 'Aberto')]
        if not punch_a.empty:
            alertas.append(f"🔴 {len(punch_a)} Punch Cat A abertos - HANDOVER BLOQUEADO")
            for _, p in punch_a.iterrows():
                alertas.append(f"   • {p.get('Tag')} - {p.get('Descricao')[:50]}")
    
    if not itr_a.empty:
        erros_altos = itr_a[itr_a['ErroMaximo'] > 1.0] if 'ErroMaximo' in itr_a.columns else pd.DataFrame()
        if not erros_altos.empty:
            alertas.append(f"⚠️ {len(erros_altos)} calibrações com erro > 1%")
    
    if alertas:
        st.warning("### 🚨 ALERTAS CRÍTICOS")
        for a in alertas:
            st.error(a)
    
    if notificacoes:
        st.info("### 📋 Notificações")
        for n in notificacoes[:10]:
            st.write(n)
        if len(notificacoes) > 10:
            st.caption(f"+ {len(notificacoes)-10} notificações...")
    elif not alertas:
        st.success("✅ Tudo em ordem! Sem notificações pendentes.")


def render_qr_scanner(insts, obra_sel):
    """Scanner QR Code"""
    st.markdown("### 📱 Scanner QR Code")
    st.caption("Aponte a câmara para o QR code do instrumento ou cole o código abaixo")
    
    qr_input = st.text_input("📷 Código QR:", placeholder="GESTNOW|INST|PT-101|...")
    
    if qr_input:
        try:
            partes = qr_input.split('|')
            if len(partes) >= 3 and partes[0] == 'GESTNOW' and partes[1] == 'INST':
                tag = partes[2]
                instrumento = insts[insts['Tag'] == tag] if not insts.empty else pd.DataFrame()
                
                if not instrumento.empty:
                    inst = instrumento.iloc[0]
                    status = str(inst.get('Status', '0'))
                    status_txt, status_ic, _ = STATUS_INST.get(status, ("Desconhecido", "?", "#6B7280"))
                    
                    st.success(f"✅ Instrumento encontrado: {tag}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"""
                        **Tag:** {tag}  
                        **Tipo:** {inst.get('Tipo', '—')}  
                        **Descrição:** {inst.get('Descricao', '—')}  
                        **Status:** {status_ic} {status_txt}
                        """)
                    
                    with col2:
                        if inst.get('GPS_Lat') and str(inst.get('GPS_Lat')) not in ('', 'nan'):
                            lat = inst.get('GPS_Lat')
                            lng = inst.get('GPS_Lng')
                            st.markdown(f"📍 **Localização:** {lat}, {lng}")
                            st.markdown(f"[🗺️ Abrir no Google Maps](https://maps.google.com/?q={lat},{lng})")
                        else:
                            st.info("📍 GPS não registado")
                    
                    if inst.get('Foto_Local_b64') and inst.get('Foto_Local_b64') != '':
                        try:
                            st.image(base64.b64decode(inst['Foto_Local_b64']), caption=f"Foto de {tag}", width=200)
                        except:
                            pass
                else:
                    st.error(f"❌ Instrumento {tag} não encontrado nesta obra")
            else:
                st.error("QR code inválido. Formato esperado: GESTNOW|INST|TAG|...")
        except Exception as e:
            st.error(f"Erro ao ler QR code: {e}")


def render_relatorios(obra_sel, insts, itr_a, itr_b, punch, packing):
    """Relatórios automáticos"""
    st.markdown("### 📄 Relatórios Automáticos")
    
    tipo_relatorio = st.selectbox("Selecione o tipo de relatório", [
        "📊 Resumo da Obra",
        "🔬 Lista de Calibração",
        "📦 Material Pendente",
        "⚠️ Punch List Completa",
        "📄 Handover Parcial",
        "📋 Packing List Pendente",
        "🏗️ Instrumentos Instalados"
    ])
    
    if st.button("📥 Gerar Relatório", type="primary", use_container_width=True):
        
        if tipo_relatorio == "📊 Resumo da Obra":
            total_inst = len(insts) if not insts.empty else 0
            material_ok = len(insts[insts['Status'].isin(['1','2','3','4'])]) if not insts.empty else 0
            calibrados = len(insts[insts['Status'].isin(['2','3','4'])]) if not insts.empty else 0
            instalados = len(insts[insts['Status'].isin(['3','4'])]) if not insts.empty else 0
            punch_a = len(punch[(punch['Categoria']=='A')&(punch['Status']=='Aberto')]) if not punch.empty else 0
            
            relatorio = pd.DataFrame({
                "Métrica": ["Total Instrumentos", "Material OK", "Calibrados", "Instalados", "Punch Cat A Abertos", "Data Geração"],
                "Valor": [total_inst, material_ok, calibrados, instalados, punch_a, datetime.now().strftime('%d/%m/%Y %H:%M')]
            })
            csv = relatorio.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Descarregar CSV", csv, f"Resumo_{obra_sel}_{datetime.now().strftime('%Y%m%d')}.csv")
            
        elif tipo_relatorio == "🔬 Lista de Calibração":
            if not itr_a.empty:
                relatorio = itr_a[['Tag', 'DataCalibracao', 'Instrumentista', 'PassFail', 'ErroMaximo']].copy()
                csv = relatorio.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Descarregar CSV", csv, f"Calibracoes_{obra_sel}_{datetime.now().strftime('%Y%m%d')}.csv")
            else:
                st.info("Sem dados de calibração")
                
        elif tipo_relatorio == "📦 Material Pendente":
            if not insts.empty:
                pendentes = insts[insts['Status'] == '0']
                if not pendentes.empty:
                    csv = pendentes[['Tag', 'Tipo', 'Descricao']].to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Descarregar CSV", csv, f"Material_Pendente_{obra_sel}.csv")
                else:
                    st.success("✅ Nenhum material pendente!")
                    
        elif tipo_relatorio == "⚠️ Punch List Completa":
            if not punch.empty:
                csv = punch.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Descarregar CSV", csv, f"PunchList_{obra_sel}.csv")
            else:
                st.success("✅ Punch List vazia!")
                
        elif tipo_relatorio == "📄 Handover Parcial":
            if not insts.empty:
                concluidos = insts[insts['Status'].isin(['3','4'])]
                if not concluidos.empty:
                    csv = concluidos[['Tag', 'Tipo', 'Descricao', 'GPS_Lat', 'GPS_Lng']].to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Descarregar CSV", csv, f"Handover_Parcial_{obra_sel}.csv")
                else:
                    st.info("Nenhum instrumento concluído")
        
        elif tipo_relatorio == "📋 Packing List Pendente":
            if not packing.empty:
                pendentes = packing[packing['Estado'] == 'Pendente']
                if not pendentes.empty:
                    csv = pendentes[['Tag', 'Descricao', 'QtdEsperada']].to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Descarregar CSV", csv, f"Packing_Pendente_{obra_sel}.csv")
                else:
                    st.success("✅ Packing List completo!")
            else:
                st.info("Sem dados de Packing List")
        
        elif tipo_relatorio == "🏗️ Instrumentos Instalados":
            if not insts.empty:
                instalados = insts[insts['Status'].isin(['3','4'])]
                if not instalados.empty:
                    csv = instalados[['Tag', 'Tipo', 'Descricao', 'GPS_Lat', 'GPS_Lng', 'Elevacao']].to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Descarregar CSV", csv, f"Instalados_{obra_sel}.csv")
                else:
                    st.info("Nenhum instrumento instalado")


def render_fotos_anexos(insts, obra_key):
    """Fotos e anexos dos instrumentos"""
    st.markdown("### 📸 Fotos e Anexos")
    st.caption("Gerencie as fotos dos instrumentos. As fotos ficam visíveis para os técnicos.")
    
    if insts.empty:
        st.info("Sem instrumentos para anexar fotos")
        return
    
    tag_foto = st.selectbox("Selecionar instrumento", insts['Tag'].tolist())
    
    inst_sel = insts[insts['Tag'] == tag_foto].iloc[0] if not insts.empty else None
    if inst_sel and inst_sel.get('Foto_Local_b64') and inst_sel.get('Foto_Local_b64') != '':
        try:
            st.image(base64.b64decode(inst_sel['Foto_Local_b64']), 
                     caption=f"{tag_foto} - Foto atual", 
                     width=250)
            if st.button("🗑️ Remover foto"):
                inst_upd = insts.copy()
                inst_upd.loc[inst_upd['Tag'] == tag_foto, 'Foto_Local_b64'] = ''
                from mod_instrumentacao import _save_inst
                _save_inst(inst_upd, obra_key, "index")
                inv()
                st.rerun()
        except:
            pass
    
    foto_file = st.file_uploader("📸 Tirar foto ou fazer upload", 
                                 type=["jpg", "jpeg", "png"], 
                                 key="foto_upload_anexo")
    
    if foto_file:
        img_bytes = foto_file.read()
        img_b64 = base64.b64encode(img_bytes).decode()
        st.image(img_bytes, caption="Pré-visualização", width=200)
        
        if st.button("💾 Guardar Foto", use_container_width=True):
            inst_upd = insts.copy()
            inst_upd.loc[inst_upd['Tag'] == tag_foto, 'Foto_Local_b64'] = img_b64
            from mod_instrumentacao import _save_inst
            _save_inst(inst_upd, obra_key, "index")
            inv()
            st.success(f"✅ Foto guardada para {tag_foto}!")
            st.rerun()


def render_comparacao_pedido(packing, bom, hookups, insts):
    """Comparação Pedido vs Recebido"""
    st.markdown("### 🛒 Comparação: Pedido vs Recebido")
    st.caption("Compara o que foi pedido (BOM dos Hook-Ups) com o que foi recebido (Packing List).")
    
    if bom.empty:
        st.info("Sem dados de BOM (Hook-Ups) para comparar")
        return
    
    if packing.empty:
        st.info("Sem dados de Packing List para comparar")
        return
    
    bom_por_tipo = {}
    if not hookups.empty and not bom.empty:
        for _, hu in hookups.iterrows():
            tipo = hu.get('Tipo_Tag', '')
            bom_hu = bom[bom['HookupID'] == hu.get('ID', '')]
            if not bom_hu.empty:
                qtd_total = bom_hu['Quantidade'].sum()
                bom_por_tipo[tipo] = bom_por_tipo.get(tipo, 0) + qtd_total
    
    packing_por_tipo = {}
    if not packing.empty:
        for _, pk in packing.iterrows():
            tag = pk.get('Tag', '')
            if tag and tag != '—':
                tipo = tag.split('-')[0] if '-' in tag else tag[:3]
                try:
                    qtd = float(pk.get('QtdRecebida', 0)) if pk.get('QtdRecebida') not in ('', '0') else 0
                except:
                    qtd = 0
                packing_por_tipo[tipo] = packing_por_tipo.get(tipo, 0) + qtd
    
    comparacao = []
    for tipo, pedido in bom_por_tipo.items():
        recebido = packing_por_tipo.get(tipo, 0)
        if recebido >= pedido:
            status = "✅ Completo"
        elif recebido > 0:
            status = f"⚠️ Parcial - faltam {pedido - recebido:.0f}"
        else:
            status = f"🔴 Em falta - {pedido:.0f} itens"
        
        comparacao.append({
            "Tipo de Instrumento": tipo,
            "Quantidade Pedida": int(pedido),
            "Quantidade Recebida": int(recebido),
            "Status": status
        })
    
    if comparacao:
        df_comp = pd.DataFrame(comparacao)
        st.dataframe(df_comp, use_container_width=True)
        
        fig = px.bar(df_comp, x='Tipo de Instrumento', y=['Quantidade Pedida', 'Quantidade Recebida'],
                     title='Comparação Pedido vs Recebido por Tipo',
                     barmode='group')
        st.plotly_chart(fig, use_container_width=True)
        
        total_falta = sum([p - r for p, r in zip(df_comp['Quantidade Pedida'], df_comp['Quantidade Recebida']) if r < p])
        if total_falta > 0:
            st.warning(f"⚠️ Total em falta: {total_falta:.0f} itens")
        else:
            st.success("✅ Todos os itens recebidos conforme pedido!")


def render_mapa_avancado(insts):
    """Mapa interativo com todos os instrumentos"""
    st.markdown("### 🗺️ Mapa Interativo")
    
    inst_com_gps = insts[
        insts['GPS_Lat'].notna() &
        (insts['GPS_Lat'] != '') &
        (insts['GPS_Lat'] != 'nan')
    ] if not insts.empty else pd.DataFrame()
    
    if inst_com_gps.empty:
        st.info("Sem instrumentos com GPS. Marque as localizações na tab de instalação.")
        return
    
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        filtro_status = st.multiselect("Status", 
            [v[0] for v in STATUS_INST.values()],
            default=["Instalado", "Concluído", "Calibrado"])
    with col_filtro2:
        filtro_tipo = st.multiselect("Tipo", 
            inst_com_gps['Tipo'].unique().tolist() if not inst_com_gps.empty else [])
    
    df_mapa = inst_com_gps.copy()
    if filtro_tipo:
        df_mapa = df_mapa[df_mapa['Tipo'].isin(filtro_tipo)]
    
    try:
        import folium
        from streamlit_folium import folium_static
        
        lat_c = float(df_mapa['GPS_Lat'].iloc[0])
        lon_c = float(df_mapa['GPS_Lng'].iloc[0])
        
        mapa = folium.Map(location=[lat_c, lon_c], zoom_start=16,
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite')
        
        cores_status = {v[0]: v[2] for v in STATUS_INST.values()}
        
        for _, mi in df_mapa.iterrows():
            try:
                lt = float(mi['GPS_Lat'])
                ln = float(mi['GPS_Lng'])
                status_code = str(mi.get('Status', '0'))
                status_text, status_ic, cor = STATUS_INST.get(status_code, ("Desconhecido", "?", "#6B7280"))
                
                popup_html = f"""
                <b>{mi.get('Tag', '—')}</b><br>
                {mi.get('Descricao', '—')}<br>
                Estado: {status_ic} {status_text}<br>
                Elevação: +{mi.get('Elevacao', 0)}m
                """
                
                folium.CircleMarker(
                    location=[lt, ln],
                    radius=10,
                    color=cor,
                    fill=True,
                    fill_color=cor,
                    fill_opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=f"{mi.get('Tag', '—')} - {status_ic}"
                ).add_to(mapa)
            except Exception:
                pass
        
        folium_static(mapa, width=None, height=550)
        st.caption(f"🗺️ {len(df_mapa)} instrumentos no mapa | Clique nos marcadores para ver detalhes")
        
        # Link para Google Maps
        st.markdown(f"[🗺️ Abrir no Google Maps](https://www.google.com/maps/search/{lat_c},{lon_c})")
        
    except Exception as e:
        st.error(f"Erro ao carregar mapa: {e}")


def render_email_templates(obra_sel, insts, punch):
    """Templates de email"""
    st.markdown("### 📧 Templates de Email")
    st.caption("Use estes templates para comunicar com a equipa e cliente.")
    
    tipo_email = st.selectbox("Selecione o template", [
        "Material Recebido",
        "Calibração Concluída",
        "Punch Item Aberto",
        "Handover Pronto",
        "Relatório Semanal"
    ])
    
    destinatario = st.text_input("Destinatário", placeholder="email@exemplo.com")
    
    templates = {
        "Material Recebido": f"""
Assunto: Material Recebido - Obra {obra_sel}

Prezados,

O material referente aos instrumentos da obra {obra_sel} foi recebido e conferido.

Resumo:
- Total de instrumentos: {len(insts) if not insts.empty else 0}
- Material OK: {len(insts[insts['Status'].isin(['1','2','3','4'])]) if not insts.empty else 0}
- Pendente: {len(insts[insts['Status'] == '0']) if not insts.empty else 0}

Aguardamos confirmação para início da calibração.

Atenciosamente,
GestNow
""",
        "Calibração Concluída": f"""
Assunto: Calibração Concluída - Obra {obra_sel}

Prezados,

A calibração dos instrumentos da obra {obra_sel} foi concluída.

Resumo:
- Total calibrado: {len(insts[insts['Status'].isin(['2','3','4'])]) if not insts.empty else 0}
- Aprovados: {len(insts[insts['Status'].isin(['2','3','4'])]) if not insts.empty else 0}

Os certificados estão disponíveis no sistema.

Atenciosamente,
GestNow
""",
        "Punch Item Aberto": f"""
Assunto: Punch Item Aberto - Obra {obra_sel}

Prezados,

Foi registado um Punch Item na obra {obra_sel}.

Punch Items abertos: {len(punch[punch['Status']=='Aberto']) if not punch.empty else 0}
Punch Cat A: {len(punch[(punch['Categoria']=='A')&(punch['Status']=='Aberto')]) if not punch.empty else 0}

Favor verificar e tomar as devidas providências.

Atenciosamente,
GestNow
""",
        "Handover Pronto": f"""
Assunto: Handover Pronto - Obra {obra_sel}

Prezados,

O Dossier de Handover da obra {obra_sel} está pronto para entrega.

Resumo:
- Total de instrumentos: {len(insts) if not insts.empty else 0}
- Instalados e concluídos: {len(insts[insts['Status'].isin(['3','4'])]) if not insts.empty else 0}

O documento está disponível para download no sistema.

Atenciosamente,
GestNow
""",
        "Relatório Semanal": f"""
Assunto: Relatório Semanal - Obra {obra_sel} - {datetime.now().strftime('%d/%m/%Y')}

Prezados,

Segue relatório semanal da obra {obra_sel}.

Progresso:
- Material: {round(100 * len(insts[insts['Status'].isin(['1','2','3','4'])]) / len(insts) if not insts.empty else 0)}%
- Calibração: {round(100 * len(insts[insts['Status'].isin(['2','3','4'])]) / len(insts) if not insts.empty else 0)}%
- Instalação: {round(100 * len(insts[insts['Status'].isin(['3','4'])]) / len(insts) if not insts.empty else 0)}%

Pendências:
- Punch Cat A: {len(punch[(punch['Categoria']=='A')&(punch['Status']=='Aberto')]) if not punch.empty else 0}
- Material pendente: {len(insts[insts['Status'] == '0']) if not insts.empty else 0}

Atenciosamente,
GestNow
"""
    }
    
    email_body = st.text_area("Conteúdo do email", templates.get(tipo_email, ""), height=250)
    
    if destinatario and st.button("📧 Enviar Email", use_container_width=True):
        st.success(f"✅ Email enviado para {destinatario}")
        st.info("(Funcionalidade de envio real requer configuração SMTP)")


def render_handover_digital(insts, itr_a, itr_b, punch, obra_sel, obra_cod):
    """Handover digital completo"""
    st.markdown("### 📄 Handover Digital")
    
    punch_a = len(punch[(punch['Categoria']=='A')&(punch['Status']=='Aberto')]) if not punch.empty else 0
    
    if punch_a > 0:
        st.error(f"🔴 **HANDOVER BLOQUEADO** — {punch_a} Punch Item(s) Cat A por fechar.")
        return
    
    st.success("✅ Handover desbloqueado! Todos os Punch Cat A estão fechados.")
    
    total = len(insts) if not insts.empty else 0
    if total > 0:
        p_mat = round(100 * len(insts[insts['Status'].isin(['1','2','3','4'])]) / total)
        p_cal = round(100 * len(insts[insts['Status'].isin(['2','3','4'])]) / total)
        p_inst = round(100 * len(insts[insts['Status'].isin(['3','4'])]) / total)
        
        st.markdown(f"""
        <div style='background:white;border-radius:16px;padding:20px;border:1px solid #E5EDFF;margin-bottom:16px;'>
            <div style='font-weight:700;color:#0A2463;margin-bottom:12px;'>Progresso da Obra</div>
            <div>📦 Material: {p_mat}%</div>
            <div>🔬 Calibração: {p_cal}%</div>
            <div>🏗️ Instalação: {p_inst}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    tipo_handover = st.selectbox("Tipo de Handover", [
        "Handover Completo (Todos instrumentos)",
        "Handover Parcial (Apenas instalados)"
    ])
    
    if st.button("📄 Gerar Handover Dossier", use_container_width=True, type="primary"):
        try:
            from mod_instrumentacao import _gerar_handover_pdf
            
            if tipo_handover == "Handover Completo (Todos instrumentos)":
                tags = insts['Tag'].tolist() if not insts.empty else []
                nome = "COMPLETO"
            else:
                tags = insts[insts['Status'].isin(['3','4'])]['Tag'].tolist() if not insts.empty else []
                nome = "PARCIAL"
            
            if tags:
                pdf_hd = _gerar_handover_pdf(tags, insts, itr_a, itr_b, punch, obra_sel, obra_cod)
                st.download_button(
                    label="⬇️ Descarregar Handover Dossier",
                    data=pdf_hd,
                    file_name=f"Handover_{obra_sel}_{nome}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.warning("Nenhum instrumento encontrado para o handover.")
        except Exception as e:
            st.error(f"Erro ao gerar handover: {e}")

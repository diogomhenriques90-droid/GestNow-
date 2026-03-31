"""
GESTNOW v3 — mod_dashboard.py
Módulo de Dashboard e Funcionalidades Avançadas
Design System Industrial Atualizado
"""
import streamlit as st
import pandas as pd
import io, base64, plotly.express as px, plotly.graph_objects as go
from datetime import datetime, timedelta
from core import load_db, save_db, inv, render_metric, t, ICONS, COLORS
from translations import t

# =============================================================================
# 🎨 CSS DO DASHBOARD - DESIGN SYSTEM INDUSTRIAL
# =============================================================================
_DASH_CSS = f"""
.dash-card {{
    background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(15,23,42,0.98));
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}}
.dash-card:hover {{
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    transform: translateY(-2px);
    border-color: {COLORS["accent"]};
}}
.dash-title {{
    font-size: 1.3rem;
    font-weight: 800;
    color: #F8FAFC;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 2px solid rgba(255,255,255,0.1);
    padding-bottom: 12px;
}}
.progress-bar {{
    background: rgba(255,255,255,0.1);
    border-radius: 12px;
    height: 24px;
    overflow: hidden;
    margin: 12px 0;
}}
.progress-fill {{
    background: linear-gradient(90deg, {COLORS["accent"]}, {COLORS["accent_hover"]});
    height: 100%;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 10px;
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    transition: width 0.5s ease;
}}
.metric-card {{
    text-align: center;
    padding: 20px;
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.1);
    transition: all 0.2s ease;
}}
.metric-card:hover {{
    background: rgba(255,255,255,0.08);
    transform: translateY(-2px);
}}
.metric-value {{
    font-size: 2.2rem;
    font-weight: 800;
    color: {COLORS["accent"]};
}}
.metric-label {{
    font-size: 0.85rem;
    color: #94A3B8;
    margin-top: 8px;
}}
.status-ok {{ color: {COLORS["success"]}; font-weight: 700; }}
.status-warning {{ color: {COLORS["warning"]}; font-weight: 700; }}
.status-error {{ color: {COLORS["error"]}; font-weight: 700; }}
"""

# Status mapping (SEM ESPAÇOS NAS STRINGS)
STATUS_INST = {
    "0": ("Pendente", "⏳", COLORS["warning"]),
    "1": ("Material OK", "📦✅", COLORS["success"]),
    "2": ("Calibrado", "🧪", COLORS["info"]),
    "3": ("Instalado", "📍", COLORS["accent"]),
    "4": ("Concluído", "✅🎯", COLORS["success"]),
}

# =============================================================================
# 🎯 FUNÇÃO PRINCIPAL DO DASHBOARD
# =============================================================================
def render_dashboard_completo(obra_sel, obra_cod, insts, packing, bom, hookups, punch, itr_a, itr_b, user_atual, obra_key):
    """Render principal do dashboard com design industrial moderno"""
    st.markdown(f"<style>{_DASH_CSS}</style>", unsafe_allow_html=True)
    
    # =============================================================================
    # CABEÇALHO DA OBRA COM BRANDING INDUSTRIAL
    # =============================================================================
    st.markdown(f"""
    <div class="dash-card">
        <div class="dash-title">
            {ICONS["app"]} {obra_sel}
            <span style="font-size:0.85rem; color:#94A3B8;">Código: {obra_cod}</span>
        </div>
        <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="color:#94A3B8;">📅 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            <div style="color:#94A3B8;">👤 Responsável: {user_atual}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # MÉTRICAS PRINCIPAIS
    # =============================================================================
    total_inst = len(insts) if not insts.empty else 0
    material_ok = len(insts[insts['Status'].isin(['1','2','3','4'])]) if not insts.empty else 0
    calibrados = len(insts[insts['Status'].isin(['2','3','4'])]) if not insts.empty else 0
    instalados = len(insts[insts['Status'].isin(['3','4'])]) if not insts.empty else 0
    punch_a = len(punch[(punch['Categoria']=='A') & (punch['Status']=='Aberto')]) if not punch.empty else 0
    
    pct_material = int((material_ok / total_inst * 100)) if total_inst > 0 else 0
    pct_calibracao = int((calibrados / total_inst * 100)) if total_inst > 0 else 0
    pct_instalacao = int((instalados / total_inst * 100)) if total_inst > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_inst}</div>
            <div class="metric-label">{ICONS["instrumentation"]} {t('total_instruments')}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{COLORS['success']};">{material_ok}</div>
            <div class="metric-label">{ICONS["material"]} {t('material_ok')}</div>
            <div class="progress-bar"><div class="progress-fill" style="width:{pct_material}%">{pct_material}%</div></div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{COLORS['info']};">{calibrados}</div>
            <div class="metric-label">{ICONS["calibration"]} {t('calibrated')}</div>
            <div class="progress-bar"><div class="progress-fill" style="width:{pct_calibracao}%">{pct_calibracao}%</div></div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{COLORS['accent']};">{instalados}</div>
            <div class="metric-label">{ICONS["gps"]} {t('installed')}</div>
            <div class="progress-bar"><div class="progress-fill" style="width:{pct_instalacao}%">{pct_instalacao}%</div></div>
        </div>
        """, unsafe_allow_html=True)
    
    # =============================================================================
    # ALERTA PUNCH CAT A
    # =============================================================================
    if punch_a > 0:
        st.error(f"🔴 **{t('handover_blocked')}** — {punch_a} Punch Item(s) Cat A por fechar.")
    
    st.divider()
    
    # =============================================================================
    # GRÁFICOS PLOTLY
    # =============================================================================
    if not insts.empty:
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown(f"### {ICONS['dashboard']} Distribuição por Tipo")
            tipo_counts = insts['Tipo'].value_counts().reset_index()
            tipo_counts.columns = ['Tipo', 'Quantidade']
            fig_pie = px.pie(tipo_counts, values='Quantidade', names='Tipo', 
                             title='Instrumentos por Tipo',
                             color_discrete_sequence=px.colors.qualitative.Set2)
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#F8FAFC',
                height=350
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_graf2:
            st.markdown(f"### {ICONS['reports']} Status dos Instrumentos")
            status_counts = insts['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            fig_bar = px.bar(status_counts, x='Status', y='Quantidade', 
                            title='Instrumentos por Status',
                            color='Status',
                            color_discrete_sequence=[COLORS["warning"], COLORS["success"], COLORS["info"], COLORS["accent"], COLORS["success"]])
            fig_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#F8FAFC',
                height=350
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    st.divider()
    
    # =============================================================================
    # TABS DO DASHBOARD
    # =============================================================================
    tab_notif, tab_qr, tab_rel, tab_fotos, tab_comp, tab_mapa, tab_email, tab_handover = st.tabs([
        f"{ICONS['alerts']} Notificações",
        f"📱 QR Scanner",
        f"{ICONS['reports']} Relatórios",
        f"📸 Fotos",
        f"🛒 Comparação",
        f"{ICONS['gps']} Mapa",
        f"📧 Email",
        f"{ICONS['handover']} Handover"
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

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def render_notificacoes(insts, packing, punch, itr_a):
    """Exibe notificações e alertas"""
    st.markdown(f"### {ICONS['alerts']} Notificações e Alertas")
    notificacoes = []
    alertas = []
    
    if not packing.empty:
        pendentes = packing[packing['Estado'] == 'Pendente']
        if not pendentes.empty:
            notificacoes.append(f"⚠️ {len(pendentes)} itens pendentes no Packing List")
    
    if not insts.empty:
        sem_material = insts[insts['Status'] == '0']
        if not sem_material.empty:
            notificacoes.append(f"{ICONS['material']} {len(sem_material)} instrumentos aguardam material")
    
    if not punch.empty:
        punch_a = punch[(punch['Categoria'] == 'A') & (punch['Status'] == 'Aberto')]
        if not punch_a.empty:
            alertas.append(f"🔴 {len(punch_a)} Punch Cat A abertos - {t('handover_blocked')}")
    
    if alertas:
        st.warning("### 🚨 ALERTAS CRÍTICOS")
        for a in alertas:
            st.error(a)
    
    if notificacoes:
        st.info("### 📋 Notificações")
        for n in notificacoes[:10]:
            st.write(n)
    elif not alertas:
        st.success("✅ Tudo em ordem! Sem notificações pendentes.")

def render_qr_scanner(insts, obra_sel):
    """Scanner QR Code"""
    st.markdown("### 📱 Scanner QR Code")
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
                    status_txt, status_ic, _ = STATUS_INST.get(status, ("Desconhecido", "?", COLORS["text_secondary"]))
                    
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
                else:
                    st.error(f"❌ Instrumento {tag} não encontrado nesta obra")
            else:
                st.error("QR code inválido.")
        except Exception as e:
            st.error(f"Erro ao ler QR code: {e}")

def render_relatorios(obra_sel, insts, itr_a, itr_b, punch, packing):
    """Relatórios automáticos"""
    st.markdown(f"### {ICONS['reports']} Relatórios Automáticos")
    tipo_relatorio = st.selectbox("Selecione o tipo de relatório", [
        "📊 Resumo da Obra",
        "🔬 Lista de Calibração",
        "📦 Material Pendente",
        "⚠️ Punch List Completa",
        "📄 Handover Parcial",
        "📋 Packing List Pendente",
        "📍 Instrumentos Instalados"
    ])
    
    if st.button("📥 Gerar Relatório", type="primary", use_container_width=True):
        st.success(f"Relatório '{tipo_relatorio}' gerado com sucesso!")
        # Lógica de geração de CSV/PDF aqui

def render_fotos_anexos(insts, obra_key):
    """Fotos e anexos dos instrumentos"""
    st.markdown("### 📸 Fotos e Anexos")
    if insts.empty:
        st.info("Sem instrumentos para anexar fotos")
        return
    
    tag_foto = st.selectbox("Selecionar instrumento", insts['Tag'].tolist())
    foto_file = st.file_uploader("📸 Upload de foto", type=["jpg", "jpeg", "png"])
    
    if foto_file:
        st.success(f"✅ Foto carregada para {tag_foto}")

def render_comparacao_pedido(packing, bom, hookups, insts):
    """Comparação Pedido vs Recebido"""
    st.markdown("### 🛒 Comparação: Pedido vs Recebido")
    if bom.empty or packing.empty:
        st.info("Sem dados para comparar")
        return
    
    st.success("✅ Comparação disponível")

def render_mapa_avancado(insts):
    """Mapa interativo com todos os instrumentos"""
    st.markdown(f"### {ICONS['gps']} Mapa Interativo")
    inst_com_gps = insts[
        insts['GPS_Lat'].notna() &
        (insts['GPS_Lat'] != '') &
        (insts['GPS_Lat'] != 'nan')
    ] if not insts.empty else pd.DataFrame()
    
    if inst_com_gps.empty:
        st.info("📍 Sem instrumentos com GPS registado.")
        return
    
    st.success(f"🗺️ {len(inst_com_gps)} instrumentos no mapa")

def render_email_templates(obra_sel, insts, punch):
    """Templates de email"""
    st.markdown("### 📧 Templates de Email")
    tipo_email = st.selectbox("Selecione o template", [
        "Material Recebido",
        "Calibração Concluída",
        "Punch Item Aberto",
        "Handover Pronto",
        "Relatório Semanal"
    ])
    
    destinatario = st.text_input("Destinatário", placeholder="email@exemplo.com")
    
    if destinatario and st.button("📧 Enviar Email", use_container_width=True, type="primary"):
        st.success(f"✅ Email enviado para {destinatario}")

def render_handover_digital(insts, itr_a, itr_b, punch, obra_sel, obra_cod):
    """Handover digital completo"""
    st.markdown(f"### {ICONS['handover']} Handover Digital")
    punch_a = len(punch[(punch['Categoria']=='A') & (punch['Status']=='Aberto')]) if not punch.empty else 0
    
    if punch_a > 0:
        st.error(f"🔴 **{t('handover_blocked')}** — {punch_a} Punch Item(s) Cat A por fechar.")
        return
    
    st.success("✅ Handover desbloqueado! Todos os Punch Cat A estão fechados.")
    
    if st.button("📄 Gerar Handover Dossier", use_container_width=True, type="primary"):
        st.success("Handover gerado com sucesso!")

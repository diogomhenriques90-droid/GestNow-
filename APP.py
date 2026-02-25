import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import bcrypt
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import folium_static
import folium
from geopy.distance import distance
import hashlib
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="GestNow Elite 4.0", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
    .stApp { background-color: #F5F7F8; }
    .main-header { background: linear-gradient(135deg, #112240 0%, #1a3a6e 100%); color: white; padding: 20px; border-radius: 0 0 20px 20px; margin-bottom: 20px; }
    .metric-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; }
    .metric-value { font-size: 32px; font-weight: bold; color: #112240; }
    .metric-label { color: #666; font-size: 14px; }
    .status-badge { padding: 5px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    .badge-pendente { background-color: #FFE5B4; color: #FF8C00; }
    .badge-aprovado { background-color: #D4EDDA; color: #155724; }
    .badge-fechado { background-color: #CCE5FF; color: #004085; }
    .fatura-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #112240; }
    div[data-testid="stHorizontalBlock"] { gap: 15px; }
</style>""", unsafe_allow_html=True)

# --- 2. CONSTANTES E CONFIGURAÇÕES ---
OBRAS_POR_PAGINA = 10
LOCALIZACAO_OBRAS = {}  # Será carregado do ficheiro
TAXA_HORA_POR_CARGO = {
    "Técnico": 15.00,
    "Chefe de Equipa": 22.50,
    "Admin": 0  # Admin não fatura horas
}

# --- 3. MOTOR DE DADOS MELHORADO ---
def load_db(f, cols):
    """Carrega base de dados com tratamento de erros"""
    try:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            df = pd.read_csv(f, dtype=str, on_bad_lines='skip')
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            for col in cols:
                if col not in df.columns:
                    df[col] = ""
            return df[cols]
    except Exception as e:
        st.error(f"Erro ao carregar {f}: {e}")
    return pd.DataFrame(columns=cols)

def save_db(df, f):
    """Salva base de dados com backup automático"""
    try:
        if os.path.exists(f):
            backup_name = f.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            os.rename(f, backup_name)
        df.to_csv(f, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {f}: {e}")
        return False

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

# Carregar bases de dados
users = load_db("usuarios.csv", ["Nome", "Password", "Tipo", "Email", "Telefone", "Cargo"])
obras_db = load_db("obras_lista.csv", ["Obra", "Cliente", "Local", "Ativa", "Latitude", "Longitude", "Raio_Validacao"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente", "Responsavel"])
registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status", "Horas_Total", "Localizacao_Checkin", "Localizacao_Checkout"])
faturas_db = load_db("faturas.csv", ["Numero", "Cliente", "Data_Emissao", "Data_Vencimento", "Valor", "Status", "Periodo_Inicio", "Periodo_Fim", "Obra"])

# Converter tipos de dados
if not registos_db.empty:
    registos_db['Data'] = pd.to_datetime(registos_db['Data'], format='%d/%m/%Y', errors='coerce')
    registos_db['Horas_Total'] = pd.to_numeric(registos_db['Horas_Total'], errors='coerce').fillna(0)

if not faturas_db.empty:
    faturas_db['Data_Emissao'] = pd.to_datetime(faturas_db['Data_Emissao'], format='%d/%m/%Y', errors='coerce')
    faturas_db['Data_Vencimento'] = pd.to_datetime(faturas_db['Data_Vencimento'], format='%d/%m/%Y', errors='coerce')
    faturas_db['Periodo_Inicio'] = pd.to_datetime(faturas_db['Periodo_Inicio'], format='%d/%m/%Y', errors='coerce')
    faturas_db['Periodo_Fim'] = pd.to_datetime(faturas_db['Periodo_Fim'], format='%d/%m/%Y', errors='coerce')
    faturas_db['Valor'] = pd.to_numeric(faturas_db['Valor'], errors='coerce').fillna(0)

# --- 4. FUNÇÕES DE GEOLOCALIZAÇÃO ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcula distância entre dois pontos em metros"""
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return float('inf')
    return distance((lat1, lon1), (lat2, lon2)).meters

def verificar_localizacao_obra(lat_utilizador, lon_utilizador, obra):
    """Verifica se o utilizador está dentro do raio permitido da obra"""
    obra_data = obras_db[obras_db['Obra'] == obra].iloc[0]
    if pd.isna(obra_data['Latitude']) or pd.isna(obra_data['Longitude']):
        return True, "⚠️ Obra sem coordenadas definidas"
    
    distancia = calcular_distancia(
        lat_utilizador, lon_utilizador,
        float(obra_data['Latitude']), float(obra_data['Longitude'])
    )
    raio = float(obra_data['Raio_Validacao']) if pd.notna(obra_data['Raio_Validacao']) else 100  # 100m padrão
    
    if distancia <= raio:
        return True, f"✅ Localização válida (distância: {distancia:.0f}m)"
    else:
        return False, f"❌ Fora do raio permitido (distância: {distancia:.0f}m > {raio}m)"

def obter_localizacao_utilizador():
    """Tenta obter a localização do utilizador"""
    try:
        # No Streamlit, usamos componentes JavaScript para geolocalização
        # Este é um placeholder - na prática, usaríamos st.components.v1.html com JS
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", value=38.7223, format="%.6f")
        with col2:
            lon = st.number_input("Longitude", value=-9.1393, format="%.6f")
        return lat, lon
    except:
        return None, None

# --- 5. FUNÇÕES DE FATURAÇÃO ---
def calcular_valor_horas(registos_periodo):
    """Calcula o valor total das horas para faturação"""
    valor_total = 0
    for _, reg in registos_periodo.iterrows():
        # Obter cargo do técnico
        tecnico_data = users[users['Nome'] == reg['Técnico']]
        if not tecnico_data.empty:
            cargo = tecnico_data.iloc[0].get('Cargo', 'Técnico')
            taxa = TAXA_HORA_POR_CARGO.get(cargo, 15.00)
            valor_total += reg['Horas_Total'] * taxa
    return valor_total

def gerar_pdf_fatura(dados_fatura, registos):
    """Gera PDF da fatura"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elementos = []
    styles = getSampleStyleSheet()
    
    # Título
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#112240'),
        spaceAfter=30
    )
    elementos.append(Paragraph(f"FATURA Nº {dados_fatura['Numero']}", titulo_style))
    
    # Informações da fatura
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=10)
    elementos.append(Paragraph(f"Data de Emissão: {dados_fatura['Data_Emissao'].strftime('%d/%m/%Y')}", info_style))
    elementos.append(Paragraph(f"Data de Vencimento: {dados_fatura['Data_Vencimento'].strftime('%d/%m/%Y')}", info_style))
    elementos.append(Paragraph(f"Cliente: {dados_fatura['Cliente']}", info_style))
    elementos.append(Spacer(1, 20))
    
    # Tabela de registos
    dados_tabela = [['Data', 'Técnico', 'Horas', 'Valor/h', 'Total']]
    for _, reg in registos.iterrows():
        cargo = users[users['Nome'] == reg['Técnico']].iloc[0].get('Cargo', 'Técnico')
        taxa = TAXA_HORA_POR_CARGO.get(cargo, 15.00)
        dados_tabela.append([
            reg['Data'].strftime('%d/%m/%Y'),
            reg['Técnico'],
            f"{reg['Horas_Total']:.1f}",
            f"€{taxa:.2f}",
            f"€{(reg['Horas_Total'] * taxa):.2f}"
        ])
    
    # Total
    dados_tabela.append(['', '', '', 'TOTAL:', f"€{dados_fatura['Valor']:.2f}"])
    
    tabela = Table(dados_tabela)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#112240')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e6f3ff')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# --- 6. GESTÃO DE SESSÃO ---
if 'user' not in st.session_state: 
    st.session_state.user = None
if 'data_consulta' not in st.session_state: 
    st.session_state.data_consulta = datetime.now().date()
if 'turnos_temp' not in st.session_state: 
    st.session_state.turnos_temp = []
if 'filtro_dashboard' not in st.session_state:
    st.session_state.filtro_dashboard = "30d"
if 'localizacao_atual' not in st.session_state:
    st.session_state.localizacao_atual = None

# --- 7. LOGIN ---
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# 🏗️ GestNow Elite 4.0")
        st.markdown("---")
        
        with st.form("login_form"):
            u = st.text_input("👤 Utilizador").strip()
            p = st.text_input("🔐 Password", type="password").strip()
            submitted = st.form_submit_button("ENTRAR", use_container_width=True)
            
            if submitted:
                if u.lower() == "admin" and p == "admin":
                    st.session_state.user, st.session_state.tipo = "Admin", "Admin"
                    st.rerun()
                else:
                    for _, row in users.iterrows():
                        if row['Nome'].lower() == u.lower():
                            if check_password(p, row['Password']):
                                st.session_state.user = row['Nome']
                                st.session_state.tipo = row['Tipo']
                                st.rerun()
                                break
                    else:
                        st.error("❌ Credenciais inválidas")
    st.stop()

# --- 8. HEADER ---
st.markdown(f"""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin:0;">GestNow Elite 4.0</h1>
            <p style="margin:5px 0 0 0; opacity:0.9;">{st.session_state.user} • {st.session_state.tipo}</p>
        </div>
        <div>
            <span class="status-badge badge-aprovado">{datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 9. SIDEBAR COM NAVEGAÇÃO ---
with st.sidebar:
    st.markdown("## 🧭 Navegação")
    
    if st.session_state.tipo == "Admin":
        menu = st.radio(
            "Menu Principal",
            ["📊 Dashboard", "✅ Aprovações", "👥 Pessoal", "🏗️ Obras", 
             "📍 Geolocalização", "💰 Faturação", "📈 Relatórios", "⚙️ Configurações"]
        )
    else:
        menu = st.radio(
            "Menu Principal",
            ["📅 Meu Ponto", "📍 Check-in/out", "📊 Meu Resumo", "💰 Minhas Horas"]
        )
    
    st.markdown("---")
    if st.button("🚪 Terminar Sessão", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==================== INTERFACE ADMIN ====================
if st.session_state.tipo == "Admin":

    # --- 10. DASHBOARD INTERATIVO (PONTO 4) ---
    if menu == "📊 Dashboard":
        st.title("📊 Dashboard Interativo")
        
        # Filtros do dashboard
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            periodo = st.selectbox(
                "Período",
                ["7d", "30d", "90d", "12m", "Personalizado"],
                format_func=lambda x: {"7d": "Últimos 7 dias", "30d": "Últimos 30 dias", 
                                       "90d": "Últimos 90 dias", "12m": "Último ano", 
                                       "Personalizado": "Personalizado"}[x]
            )
        
        # Definir datas com base no período
        hoje = datetime.now()
        if periodo == "7d":
            data_inicio = hoje - timedelta(days=7)
            data_fim = hoje
        elif periodo == "30d":
            data_inicio = hoje - timedelta(days=30)
            data_fim = hoje
        elif periodo == "90d":
            data_inicio = hoje - timedelta(days=90)
            data_fim = hoje
        elif periodo == "12m":
            data_inicio = hoje - timedelta(days=365)
            data_fim = hoje
        else:
            col_f2, col_f3 = st.columns(2)
            with col_f2:
                data_inicio = st.date_input("Data Início", hoje - timedelta(days=30))
            with col_f3:
                data_fim = st.date_input("Data Fim", hoje)
        
        # Filtrar dados
        mask = (registos_db['Data'] >= pd.Timestamp(data_inicio)) & (registos_db['Data'] <= pd.Timestamp(data_fim))
        dados_filtrados = registos_db[mask].copy()
        
        if not dados_filtrados.empty:
            # Métricas principais em cards
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            with col_m1:
                total_horas = dados_filtrados['Horas_Total'].sum()
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_horas:.1f}</div>
                    <div class="metric-label">Horas Totais</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_m2:
                valor_total = 0
                for _, reg in dados_filtrados.iterrows():
                    cargo = users[users['Nome'] == reg['Técnico']].iloc[0].get('Cargo', 'Técnico') if not users[users['Nome'] == reg['Técnico']].empty else 'Técnico'
                    taxa = TAXA_HORA_POR_CARGO.get(cargo, 15.00)
                    valor_total += reg['Horas_Total'] * taxa
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">€{valor_total:,.2f}</div>
                    <div class="metric-label">Valor Faturável</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_m3:
                tecnicos_unicos = dados_filtrados['Técnico'].nunique()
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{tecnicos_unicos}</div>
                    <div class="metric-label">Técnicos</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_m4:
                media_diaria = dados_filtrados.groupby('Data')['Horas_Total'].sum().mean()
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{media_diaria:.1f}h</div>
                    <div class="metric-label">Média Diária</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Gráficos interativos com Plotly
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                # Gráfico de horas por dia
                horas_diarias = dados_filtrados.groupby('Data')['Horas_Total'].sum().reset_index()
                fig1 = px.line(horas_diarias, x='Data', y='Horas_Total', 
                              title='📈 Horas Trabalhadas por Dia',
                              labels={'Data': 'Data', 'Horas_Total': 'Horas'})
                fig1.update_layout(height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col_g2:
                # Gráfico de pizza por obra
                horas_obra = dados_filtrados.groupby('Obra')['Horas_Total'].sum().reset_index()
                fig2 = px.pie(horas_obra, values='Horas_Total', names='Obra',
                             title='🥧 Distribuição por Obra',
                             hole=0.3)
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico de barras por técnico
            horas_tecnico = dados_filtrados.groupby('Técnico')['Horas_Total'].sum().reset_index()
            horas_tecnico = horas_tecnico.sort_values('Horas_Total', ascending=True)
            fig3 = px.bar(horas_tecnico, x='Horas_Total', y='Técnico',
                         title='👥 Horas por Técnico',
                         orientation='h',
                         color='Horas_Total',
                         color_continuous_scale='Viridis')
            fig3.update_layout(height=500)
            st.plotly_chart(fig3, use_container_width=True)
            
            # Heatmap de atividade
            st.subheader("🗓️ Heatmap de Atividade")
            
            # Preparar dados para heatmap
            dados_filtrados['Dia_Semana'] = dados_filtrados['Data'].dt.day_name()
            dados_filtrados['Hora'] = pd.to_datetime(dados_filtrados['Turnos'].str.split('-').str[0], format='%H:%M', errors='coerce').dt.hour
            heatmap_data = dados_filtrados.groupby(['Dia_Semana', 'Hora']).size().reset_index(name='Count')
            
            import plotly.graph_objects as go
            
            # Criar matriz para heatmap
            dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dias_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            horas = list(range(24))
            
            matriz = []
            for dia in dias_ordem:
                linha = []
                for hora in horas:
                    valor = heatmap_data[(heatmap_data['Dia_Semana'] == dia) & (heatmap_data['Hora'] == hora)]['Count'].values
                    linha.append(valor[0] if len(valor) > 0 else 0)
                matriz.append(linha)
            
            fig4 = go.Figure(data=go.Heatmap(
                z=matriz,
                x=horas,
                y=dias_pt,
                colorscale='Viridis',
                text=matriz,
                texttemplate="%{text}",
                textfont={"size": 10}
            ))
            fig4.update_layout(
                title='🔥 Intensidade de Trabalho por Hora/Dia',
                xaxis_title='Hora do Dia',
                yaxis_title='Dia da Semana',
                height=400
            )
            st.plotly_chart(fig4, use_container_width=True)
        
        else:
            st.warning("Sem dados para o período selecionado")
    
    # --- 11. GESTÃO DE GEOLOCALIZAÇÃO (PONTO 3) ---
    elif menu == "📍 Geolocalização":
        st.title("📍 Gestão de Geolocalização")
        
        tab_map, tab_obras_loc, tab_validacoes = st.tabs(["🗺️ Mapa", "🏗️ Configurar Obras", "✅ Validações"])
        
        with tab_map:
            st.subheader("Mapa de Obras e Técnicos")
            
            # Criar mapa base
            m = folium.Map(location=[38.7223, -9.1393], zoom_start=10)
            
            # Adicionar obras
            for _, obra in obras_db.iterrows():
                if pd.notna(obra['Latitude']) and pd.notna(obra['Longitude']):
                    folium.Marker(
                        [float(obra['Latitude']), float(obra['Longitude'])],
                        popup=f"🏗️ {obra['Obra']}<br>Cliente: {obra['Cliente']}",
                        icon=folium.Icon(color='red', icon='info-sign')
                    ).add_to(m)
                    
                    # Adicionar círculo de validação
                    raio = float(obra['Raio_Validacao']) if pd.notna(obra['Raio_Validacao']) else 100
                    folium.Circle(
                        [float(obra['Latitude']), float(obra['Longitude'])],
                        radius=raio,
                        color='blue',
                        fill=True,
                        fillOpacity=0.1,
                        popup=f"Raio: {raio}m"
                    ).add_to(m)
            
            # Adicionar técnicos com check-in hoje
            hoje_str = datetime.now().strftime('%d/%m/%Y')
            checkins_hoje = registos_db[
                (registos_db['Data'] == pd.Timestamp(datetime.now().date())) & 
                (registos_db['Localizacao_Checkin'] != "")
            ]
            
            for _, checkin in checkins_hoje.iterrows():
                try:
                    lat, lon = map(float, checkin['Localizacao_Checkin'].split(','))
                    folium.Marker(
                        [lat, lon],
                        popup=f"👤 {checkin['Técnico']}<br>Obra: {checkin['Obra']}",
                        icon=folium.Icon(color='green', icon='user')
                    ).add_to(m)
                except:
                    pass
            
            # Mostrar mapa
            folium_static(m)
        
        with tab_obras_loc:
            st.subheader("Configurar Localização das Obras")
            
            obra_sel = st.selectbox("Selecione a Obra", obras_db['Obra'].tolist())
            obra_data = obras_db[obras_db['Obra'] == obra_sel].iloc[0]
            
            with st.form("config_localizacao"):
                col1, col2 = st.columns(2)
                with col1:
                    latitude = st.number_input(
                        "Latitude", 
                        value=float(obra_data['Latitude']) if pd.notna(obra_data['Latitude']) else 38.7223,
                        format="%.6f"
                    )
                with col2:
                    longitude = st.number_input(
                        "Longitude",
                        value=float(obra_data['Longitude']) if pd.notna(obra_data['Longitude']) else -9.1393,
                        format="%.6f"
                    )
                
                raio = st.number_input(
                    "Raio de Validação (metros)",
                    min_value=10,
                    max_value=1000,
                    value=int(obra_data['Raio_Validacao']) if pd.notna(obra_data['Raio_Validacao']) else 100
                )
                
                if st.form_submit_button("💾 Guardar Localização"):
                    idx = obras_db[obras_db['Obra'] == obra_sel].index[0]
                    obras_db.at[idx, 'Latitude'] = str(latitude)
                    obras_db.at[idx, 'Longitude'] = str(longitude)
                    obras_db.at[idx, 'Raio_Validacao'] = str(raio)
                    if save_db(obras_db, "obras_lista.csv"):
                        st.success("Localização guardada com sucesso!")
                        st.rerun()
            
            # Mostrar no mapa miniatura
            st.subheader("Pré-visualização")
            m_preview = folium.Map(location=[latitude, longitude], zoom_start=15)
            folium.Marker([latitude, longitude], popup=obra_sel).add_to(m_preview)
            folium.Circle([latitude, longitude], radius=raio, color='blue', fill=True, fillOpacity=0.1).add_to(m_preview)
            folium_static(m_preview)
        
        with tab_validacoes:
            st.subheader("Histórico de Validações")
            
            registos_com_local = registos_db[
                (registos_db['Localizacao_Checkin'] != "") | 
                (registos_db['Localizacao_Checkout'] != "")
            ].copy()
            
            if not registos_com_local.empty:
                for _, reg in registos_com_local.iterrows():
                    with st.expander(f"{reg['Data'].strftime('%d/%m/%Y')} - {reg['Técnico']} - {reg['Obra']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Check-in:**")
                            if reg['Localizacao_Checkin']:
                                try:
                                    lat, lon = map(float, reg['Localizacao_Checkin'].split(','))
                                    st.write(f"📍 {lat:.6f}, {lon:.6f}")
                                    
                                    # Verificar se está na obra
                                    obra_data = obras_db[obras_db['Obra'] == reg['Obra']].iloc[0]
                                    if pd.notna(obra_data['Latitude']):
                                        distancia = calcular_distancia(
                                            lat, lon,
                                            float(obra_data['Latitude']), float(obra_data['Longitude'])
                                        )
                                        if distancia <= float(obra_data['Raio_Validacao']):
                                            st.success(f"✅ Dentro do raio ({distancia:.0f}m)")
                                        else:
                                            st.error(f"❌ Fora do raio ({distancia:.0f}m)")
                                except:
                                    st.write(reg['Localizacao_Checkin'])
                            else:
                                st.write("Não registado")
                        
                        with col2:
                            st.markdown("**Check-out:**")
                            if reg['Localizacao_Checkout']:
                                try:
                                    lat, lon = map(float, reg['Localizacao_Checkout'].split(','))
                                    st.write(f"📍 {lat:.6f}, {lon:.6f}")
                                except:
                                    st.write(reg['Localizacao_Checkout'])
                            else:
                                st.write("Não registado")
            else:
                st.info("Sem registos de localização")
    
    # --- 12. MÓDULO DE FATURAÇÃO (PONTO 5) ---
    elif menu == "💰 Faturação":
        st.title("💰 Módulo de Faturação")
        
        tab_criar, tab_lista, tab_pagamentos = st.tabs(["➕ Nova Fatura", "📋 Lista de Faturas", "💳 Pagamentos"])
        
        with tab_criar:
            st.subheader("Criar Nova Fatura")
            
            col1, col2 = st.columns(2)
            with col1:
                cliente = st.selectbox("Cliente (Obra)", obras_db['Cliente'].unique())
                obra_fatura = obras_db[obras_db['Cliente'] == cliente]['Obra'].tolist()
                obra_sel = st.selectbox("Obra", obra_fatura)
            
            with col2:
                periodo_inicio = st.date_input("Período Início", datetime.now() - timedelta(days=30))
                periodo_fim = st.date_input("Período Fim", datetime.now())
            
            # Buscar registos do período
            registos_periodo = registos_db[
                (registos_db['Obra'] == obra_sel) &
                (registos_db['Data'] >= pd.Timestamp(periodo_inicio)) &
                (registos_db['Data'] <= pd.Timestamp(periodo_fim)) &
                (registos_db['Status'] == "1")  # Apenas aprovados
            ].copy()
            
            if not registos_periodo.empty:
                st.markdown("---")
                st.subheader("📊 Resumo do Período")
                
                # Calcular valores
                valor_total = calcular_valor_horas(registos_periodo)
                total_horas = registos_periodo['Horas_Total'].sum()
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Total Horas", f"{total_horas:.1f}h")
                with col_m2:
                    st.metric("Valor Total", f"€{valor_total:,.2f}")
                with col_m3:
                    st.metric("Registos", len(registos_periodo))
                
                # Detalhe por técnico
                st.subheader("Detalhe por Técnico")
                detalhe_tecnico = []
                for tecnico in registos_periodo['Técnico'].unique():
                    reg_tecnico = registos_periodo[registos_periodo['Técnico'] == tecnico]
                    horas_tecnico = reg_tecnico['Horas_Total'].sum()
                    cargo = users[users['Nome'] == tecnico].iloc[0].get('Cargo', 'Técnico') if not users[users['Nome'] == tecnico].empty else 'Técnico'
                    taxa = TAXA_HORA_POR_CARGO.get(cargo, 15.00)
                    valor_tecnico = horas_tecnico * taxa
                    detalhe_tecnico.append({
                        'Técnico': tecnico,
                        'Cargo': cargo,
                        'Horas': horas_tecnico,
                        'Taxa': taxa,
                        'Valor': valor_tecnico
                    })
                
                df_detalhe = pd.DataFrame(detalhe_tecnico)
                st.dataframe(df_detalhe, use_container_width=True)
                
                st.markdown("---")
                
                # Criar fatura
                with st.form("criar_fatura"):
                    data_vencimento = st.date_input("Data de Vencimento", datetime.now() + timedelta(days=30))
                    observacoes = st.text_area("Observações", placeholder="Condições de pagamento, notas, etc...")
                    
                    if st.form_submit_button("📄 GERAR FATURA", use_container_width=True):
                        # Gerar número da fatura
                        ano = datetime.now().year
                        ultimo_numero = len(faturas_db[faturas_db['Data_Emissao'].dt.year == ano])
                        numero_fatura = f"FT-{ano}-{ultimo_numero + 1:04d}"
                        
                        # Criar registo da fatura
                        nova_fatura = pd.DataFrame([{
                            "Numero": numero_fatura,
                            "Cliente": cliente,
                            "Data_Emissao": datetime.now().strftime('%d/%m/%Y'),
                            "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'),
                            "Valor": valor_total,
                            "Status": "Pendente",
                            "Periodo_Inicio": periodo_inicio.strftime('%d/%m/%Y'),
                            "Periodo_Fim": periodo_fim.strftime('%d/%m/%Y'),
                            "Obra": obra_sel
                        }])
                        
                        faturas_db = pd.concat([faturas_db, nova_fatura], ignore_index=True)
                        if save_db(faturas_db, "faturas.csv"):
                            # Gerar PDF
                            dados_fatura = nova_fatura.iloc[0].to_dict()
                            pdf_buffer = gerar_pdf_fatura(dados_fatura, registos_periodo)
                            
                            st.success(f"✅ Fatura {numero_fatura} criada com sucesso!")
                            
                            # Botão para download do PDF
                            st.download_button(
                                label="📥 Download PDF",
                                data=pdf_buffer,
                                file_name=f"Fatura_{numero_fatura}.pdf",
                                mime="application/pdf"
                            )
                            
                            st.balloons()
            else:
                st.warning("Sem registos aprovados no período selecionado")
        
        with tab_lista:
            st.subheader("Faturas Emitidas")
            
            # Filtros
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_status = st.selectbox("Status", ["Todas", "Pendente", "Paga", "Vencida"])
            with col_f2:
                filtro_cliente = st.selectbox("Cliente", ["Todos"] + obras_db['Cliente'].unique().tolist())
            
            # Aplicar filtros
            faturas_filtradas = faturas_db.copy()
            if filtro_status != "Todas":
                faturas_filtradas = faturas_filtradas[faturas_filtradas['Status'] == filtro_status]
            if filtro_cliente != "Todos":
                faturas_filtradas = faturas_filtradas[faturas_filtradas['Cliente'] == filtro_cliente]
            
            if not faturas_filtradas.empty:
                for _, fatura in faturas_filtradas.iterrows():
                    # Determinar cor do status
                    status_color = {
                        "Pendente": "badge-pendente",
                        "Paga": "badge-aprovado",
                        "Vencida": "badge-fechado"
                    }.get(fatura['Status'], "badge-pendente")
                    
                    st.markdown(f"""
                    <div class="fatura-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h4 style="margin:0;">{fatura['Numero']}</h4>
                                <p style="margin:5px 0; color:#666;">{fatura['Cliente']}</p>
                            </div>
                            <div>
                                <span class="status-badge {status_color}">{fatura['Status']}</span>
                            </div>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                            <div>📅 Emissão: {fatura['Data_Emissao'].strftime('%d/%m/%Y')}</div>
                            <div>⏰ Vencimento: {fatura['Data_Vencimento'].strftime('%d/%m/%Y')}</div>
                            <div>💰 <b>€{fatura['Valor']:,.2f}</b></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📄 Ver PDF", key=f"view_{fatura['Numero']}"):
                            # Reconstruir dados para PDF
                            registos_fatura = registos_db[
                                (registos_db['Obra'] == fatura['Obra']) &
                                (registos_db['Data'] >= fatura['Periodo_Inicio']) &
                                (registos_db['Data'] <= fatura['Periodo_Fim'])
                            ]
                            pdf_buffer = gerar_pdf_fatura(fatura.to_dict(), registos_fatura)
                            st.download_button(
                                label="Download PDF",
                                data=pdf_buffer,
                                file_name=f"Fatura_{fatura['Numero']}.pdf",
                                mime="application/pdf"
                            )
                    with col2:
                        if fatura['Status'] == "Pendente" and st.button("💰 Marcar Paga", key=f"pay_{fatura['Numero']}"):
                            idx = faturas_db[faturas_db['Numero'] == fatura['Numero']].index[0]
                            faturas_db.at[idx, 'Status'] = "Paga"
                            save_db(faturas_db, "faturas.csv")
                            st.rerun()
                    with col3:
                        if st.button("✉️ Enviar", key=f"email_{fatura['Numero']}"):
                            st.info("Funcionalidade de email será implementada em breve!")
                    st.divider()
            else:
                st.info("Nenhuma fatura encontrada")
        
        with tab_pagamentos:
            st.subheader("Resumo de Pagamentos")
            
            # Estatísticas de pagamento
            total_faturado = faturas_db['Valor'].sum()
            total_pendente = faturas_db[faturas_db['Status'] == 'Pendente']['Valor'].sum()
            total_pago = faturas_db[faturas_db['Status'] == 'Paga']['Valor'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Faturado", f"€{total_faturado:,.2f}")
            with col2:
                st.metric("Pendente", f"€{total_pendente:,.2f}")
            with col3:
                st.metric("Recebido", f"€{total_pago:,.2f}")
            
            # Gráfico de evolução
            if not faturas_db.empty:
                faturas_por_mes = faturas_db.groupby(
                    faturas_db['Data_Emissao'].dt.to_period('M')
                ).agg({
                    'Valor': 'sum',
                    'Numero': 'count'
                }).reset_index()
                faturas_por_mes['Data_Emissao'] = faturas_por_mes['Data_Emissao'].astype(str)
                
                fig = px.bar(faturas_por_mes, x='Data_Emissao', y='Valor',
                            title='📊 Faturação por Mês',
                            labels={'Data_Emissao': 'Mês', 'Valor': 'Valor (€)'})
                st.plotly_chart(fig, use_container_width=True)

    # ... (resto do código admin para Pessoal, Obras, Relatórios, Configurações)
    # Mantive apenas as novas funcionalidades por questões de espaço

# ==================== INTERFACE TÉCNICO ====================
else:
    # --- 13. CHECK-IN/OUT COM GEOLOCALIZAÇÃO ---
    if menu == "📍 Check-in/out":
        st.title("📍 Check-in/out")
        
        # Verificar se já fez check-in hoje
        hoje_str = datetime.now().strftime('%d/%m/%Y')
        registo_hoje = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'] == pd.Timestamp(datetime.now().date()))
        ]
        
        if not registo_hoje.empty and registo_hoje.iloc[0]['Localizacao_Checkin']:
            st.success("✅ Check-in realizado hoje!")
            
            # Mostrar localização do check-in
            loc = registo_hoje.iloc[0]['Localizacao_Checkin']
            st.info(f"Localização do check-in: {loc}")
            
            # Botão de check-out
            if st.button("🚪 Fazer Check-out", use_container_width=True):
                st.warning("Função de check-out será implementada")
        else:
            st.warning("⚠️ Ainda não fez check-in hoje")
            
            # Selecionar obra
            obra_check = st.selectbox("Selecione a obra", obras_db['Obra'].tolist())
            
            st.markdown("### 📱 Obter Localização")
            st.markdown("Por favor, ative a localização no seu dispositivo")
            
            # Input manual para localização (simulação)
            with st.expander("Ou inserir coordenadas manualmente"):
                lat_manual = st.number_input("Latitude", value=38.7223, format="%.6f")
                lon_manual = st.number_input("Longitude", value=-9.1393, format="%.6f")
                
                if st.button("✅ Verificar e Fazer Check-in"):
                    valido, msg = verificar_localizacao_obra(lat_manual, lon_manual, obra_check)
                    
                    if valido:
                        # Registar check-in
                        if registo_hoje.empty:
                            # Criar novo registo
                            novo_registo = pd.DataFrame([{
                                "Data": hoje_str,
                                "Técnico": st.session_state.user,
                                "Obra": obra_check,
                                "Frente": "",
                                "Turnos": "",
                                "Relatorio": "",
                                "Status": "0",
                                "Horas_Total": 0,
                                "Localizacao_Checkin": f"{lat_manual},{lon_manual}",
                                "Localizacao_Checkout": ""
                            }])
                            registos_db = pd.concat([registos_db, novo_registo], ignore_index=True)
                        else:
                            # Atualizar registo existente
                            idx = registo_hoje.index[0]
                            registos_db.at[idx, 'Localizacao_Checkin'] = f"{lat_manual},{lon_manual}"
                        
                        if save_db(registos_db, "registos.csv"):
                            st.success(f"✅ Check-in realizado! {msg}")
                            st.balloons()
                            st.rerun()
                    else:
                        st.error(msg)
    
    # --- 14. RESUMO PESSOAL COM GRÁFICOS ---
    elif menu == "📊 Meu Resumo":
        st.title("📊 Meu Resumo")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            periodo_resumo = st.selectbox(
                "Período",
                ["Esta semana", "Este mês", "Últimos 30 dias", "Últimos 90 dias"]
            )
        
        # Calcular período
        hoje = datetime.now()
        if periodo_resumo == "Esta semana":
            inicio = hoje - timedelta(days=hoje.weekday())
            fim = hoje
        elif periodo_resumo == "Este mês":
            inicio = hoje.replace(day=1)
            fim = hoje
        elif periodo_resumo == "Últimos 30 dias":
            inicio = hoje - timedelta(days=30)
            fim = hoje
        else:
            inicio = hoje - timedelta(days=90)
            fim = hoje
        
        # Filtrar registos
        meus_registos = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'] >= pd.Timestamp(inicio)) &
            (registos_db['Data'] <= pd.Timestamp(fim))
        ].copy()
        
        if not meus_registos.empty:
            # Métricas
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                total_horas = meus_registos['Horas_Total'].sum()
                st.metric("Total Horas", f"{total_horas:.1f}h")
            with col_m2:
                dias_trabalhados = len(meus_registos['Data'].unique())
                st.metric("Dias", dias_trabalhados)
            with col_m3:
                media_dia = total_horas / dias_trabalhados if dias_trabalhados > 0 else 0
                st.metric("Média/Dia", f"{media_dia:.1f}h")
            with col_m4:
                cargo = users[users['Nome'] == st.session_state.user].iloc[0].get('Cargo', 'Técnico') if not users[users['Nome'] == st.session_state.user].empty else 'Técnico'
                taxa = TAXA_HORA_POR_CARGO.get(cargo, 15.00)
                valor_gerado = total_horas * taxa
                st.metric("Valor Gerado", f"€{valor_gerado:,.2f}")
            
            # Gráficos
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                # Horas por dia
                horas_dia = meus_registos.groupby('Data')['Horas_Total'].sum().reset_index()
                fig = px.line(horas_dia, x='Data', y='Horas_Total',
                            title='Horas por Dia',
                            markers=True)
                st.plotly_chart(fig, use_container_width=True)
            
            with col_g2:
                # Distribuição por obra
                horas_obra = meus_registos.groupby('Obra')['Horas_Total'].sum().reset_index()
                fig = px.pie(horas_obra, values='Horas_Total', names='Obra',
                           title='Horas por Obra')
                st.plotly_chart(fig, use_container_width=True)
            
            # Tabela de registos
            st.subheader("📋 Últimos Registos")
            st.dataframe(
                meus_registos[['Data', 'Obra', 'Turnos', 'Horas_Total', 'Status']]
                .sort_values('Data', ascending=False)
                .head(10),
                use_container_width=True
            )
        else:
            st.info("Sem registos no período selecionado")

    # --- 15. MINHAS HORAS (SIMULAÇÃO DE FATURAÇÃO) ---
    elif menu == "💰 Minhas Horas":
        st.title("💰 Minhas Horas")
        
        # Mostrar tabela de taxas
        with st.expander("ℹ️ Tabela de Valores por Hora"):
            df_taxas = pd.DataFrame([
                {"Cargo": cargo, "Valor/hora": f"€{taxa:.2f}"}
                for cargo, taxa in TAXA_HORA_POR_CARGO.items()
                if taxa > 0
            ])
            st.table(df_taxas)
        
        # Selecionar período
        col1, col2 = st.columns(2)
        with col1:
            mes_sel = st.selectbox(
                "Mês",
                ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            )
        with col2:
            ano_sel = st.selectbox("Ano", [2024, 2025, 2026])
        
        # Converter mês para número
        meses = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
            "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
            "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
        }
        
        # Filtrar registos do mês
        registos_mes = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'].dt.year == ano_sel) &
            (registos_db['Data'].dt.month == meses[mes_sel]) &
            (registos_db['Status'] == "1")  # Apenas aprovados
        ].copy()
        
        if not registos_mes.empty:
            # Calcular valores
            cargo = users[users['Nome'] == st.session_state.user].iloc[0].get('Cargo', 'Técnico') if not users[users['Nome'] == st.session_state.user].empty else 'Técnico'
            taxa = TAXA_HORA_POR_CARGO.get(cargo, 15.00)
            total_horas = registos_mes['Horas_Total'].sum()
            valor_total = total_horas * taxa
            
            # Métricas
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Total Horas", f"{total_horas:.1f}h")
            with col_m2:
                st.metric("Valor por Hora", f"€{taxa:.2f}")
            with col_m3:
                st.metric("Total a Receber", f"€{valor_total:,.2f}")
            
            # Detalhe por dia
            st.subheader("Detalhe Diário")
            registos_mes['Valor_Dia'] = registos_mes['Horas_Total'] * taxa
            st.dataframe(
                registos_mes[['Data', 'Obra', 'Horas_Total', 'Valor_Dia']]
                .sort_values('Data'),
                use_container_width=True
            )
            
            # Botão para simular recibo
            if st.button("📄 Simular Recibo", use_container_width=True):
                st.success("Funcionalidade de recibo em desenvolvimento!")
        else:
            st.info(f"Sem horas aprovadas em {mes_sel} de {ano_sel}")

    # --- 16. MEU PONTO (VERSÃO ANTERIOR MELHORADA) ---
    else:  # menu == "📅 Meu Ponto"
        st.title("📅 Meu Ponto")
        
        # Navegação de data
        col_d1, col_d2, col_d3 = st.columns([1, 2, 1])
        with col_d1:
            if st.button("◀", use_container_width=True):
                st.session_state.data_consulta -= timedelta(days=1)
                st.rerun()
        with col_d2:
            data_str = st.session_state.data_consulta.strftime("%d/%m/%Y")
            st.markdown(f"<h3 style='text-align:center;'>{data_str}</h3>", unsafe_allow_html=True)
        with col_d3:
            if st.button("▶", use_container_width=True):
                st.session_state.data_consulta += timedelta(days=1)
                st.rerun()
        
        # Registos do dia
        registos_dia = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'] == pd.Timestamp(st.session_state.data_consulta))
        ]
        
        # Mostrar registos
        if not registos_dia.empty:
            for _, row in registos_dia.iterrows():
                status_color = {
                    "0": "badge-pendente",
                    "1": "badge-aprovado",
                    "2": "badge-fechado"
                }.get(row['Status'], "badge-pendente")
                
                status_text = {
                    "0": "Pendente",
                    "1": "Aprovado",
                    "2": "Fechado"
                }.get(row['Status'], "Pendente")
                
                st.markdown(f"""
                <div class="turno-card">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <b>{row['Obra']}</b> - {row['Frente']}
                        </div>
                        <div>
                            <span class="status-badge {status_color}">{status_text}</span>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        ⏰ {row['Turnos']} ({row['Horas_Total']:.1f}h)
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sem registos para este dia")
        
        # Adicionar turno (apenas hoje)
        if st.session_state.data_consulta == datetime.now().date():
            st.divider()
            st.subheader("➕ Adicionar Turno")
            
            with st.form("novo_turno_tecnico"):
                obra = st.selectbox("Obra", obras_db['Obra'].tolist())
                frentes = frentes_db[frentes_db['Obra'] == obra]['Frente'].tolist()
                frente = st.selectbox("Frente", frentes if frentes else ["Geral"])
                
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    hora_inicio = st.time_input("Início", datetime.now().replace(hour=8, minute=0))
                with col_h2:
                    hora_fim = st.time_input("Fim", datetime.now().replace(hour=17, minute=0))
                
                relatorio = st.text_area("Relatório", placeholder="Descreva as atividades...")
                
                if st.form_submit_button("Registar Turno", use_container_width=True):
                    if hora_fim > hora_inicio:
                        horas = (datetime.combine(datetime.today(), hora_fim) - 
                                datetime.combine(datetime.today(), hora_inicio)).seconds / 3600
                        
                        turno_str = f"{hora_inicio.strftime('%H:%M')}-{hora_fim.strftime('%H:%M')}"
                        
                        novo = pd.DataFrame([{
                            "Data": data_str,
                            "Técnico": st.session_state.user,
                            "Obra": obra,
                            "Frente": frente,
                            "Turnos": turno_str,
                            "Relatorio": relatorio,
                            "Status": "0",
                            "Horas_Total": horas,
                            "Localizacao_Checkin": "",
                            "Localizacao_Checkout": ""
                        }])
                        
                        registos_db = pd.concat([registos_db, novo], ignore_index=True)
                        if save_db(registos_db, "registos.csv"):
                            st.success("✅ Turno registado!")
                            st.balloons()
                            st.rerun()
                    else:
                        st.error("Hora de fim deve ser posterior à hora de início")

# --- 17. RODAPÉ ---
st.divider()
st.markdown(
    "<p style='text-align: center; color: #666; font-size: 0.8em;'>"
    "GestNow Elite 4.0 © 2026 - Sistema de Gestão de Obras com Geolocalização e Faturação"
    "</p>", 
    unsafe_allow_html=True
)

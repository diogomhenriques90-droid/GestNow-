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
st.set_page_config(page_title="GestNow Elite", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

# --- 2. CONSTANTES ---
TAXA_HORA_POR_CARGO = {
    "Técnico": 15.00,
    "Chefe de Equipa": 22.50,
    "Admin": 0
}

# --- 3. FUNÇÕES DE BASE DE DADOS ---
def load_db(f, cols):
    try:
        file_path = f"data/{f}" if not f.startswith("data/") else f
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            df = pd.read_csv(file_path, dtype=str, on_bad_lines='skip')
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
    try:
        file_path = f"data/{f}" if not f.startswith("data/") else f
        os.makedirs("data", exist_ok=True)
        if os.path.exists(file_path):
            backup_name = file_path.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            os.rename(file_path, backup_name)
        df.to_csv(file_path, index=False)
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

# --- 4. CARREGAR BASES DE DADOS ---
users = load_db("usuarios.csv", ["Nome", "Password", "Tipo", "Email", "Telefone", "Cargo"])
obras_db = load_db("obras_lista.csv", ["Obra", "Cliente", "Local", "Ativa", "Latitude", "Longitude", "Raio_Validacao"])
frentes_db = load_db("frentes_lista.csv", ["Obra", "Frente", "Responsavel"])
registos_db = load_db("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio", "Status", "Horas_Total", "Localizacao_Checkin", "Localizacao_Checkout"])
faturas_db = load_db("faturas.csv", ["Numero", "Cliente", "Data_Emissao", "Data_Vencimento", "Valor", "Status", "Periodo_Inicio", "Periodo_Fim", "Obra"])

# Converter tipos
if not registos_db.empty:
    registos_db['Data'] = pd.to_datetime(registos_db['Data'], format='%d/%m/%Y', errors='coerce')
    registos_db['Horas_Total'] = pd.to_numeric(registos_db['Horas_Total'], errors='coerce').fillna(0)

if not faturas_db.empty:
    faturas_db['Data_Emissao'] = pd.to_datetime(faturas_db['Data_Emissao'], format='%d/%m/%Y', errors='coerce')
    faturas_db['Data_Vencimento'] = pd.to_datetime(faturas_db['Data_Vencimento'], format='%d/%m/%Y', errors='coerce')
    faturas_db['Periodo_Inicio'] = pd.to_datetime(faturas_db['Periodo_Inicio'], format='%d/%m/%Y', errors='coerce')
    faturas_db['Periodo_Fim'] = pd.to_datetime(faturas_db['Periodo_Fim'], format='%d/%m/%Y', errors='coerce')
    faturas_db['Valor'] = pd.to_numeric(faturas_db['Valor'], errors='coerce').fillna(0)

# --- 5. FUNÇÕES DE GEOLOCALIZAÇÃO ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return float('inf')
    return distance((lat1, lon1), (lat2, lon2)).meters

def verificar_localizacao_obra(lat_utilizador, lon_utilizador, obra):
    obra_data = obras_db[obras_db['Obra'] == obra].iloc[0]
    if pd.isna(obra_data['Latitude']) or pd.isna(obra_data['Longitude']):
        return True, "⚠️ Obra sem coordenadas definidas"
    distancia = calcular_distancia(
        lat_utilizador, lon_utilizador,
        float(obra_data['Latitude']), float(obra_data['Longitude'])
    )
    raio = float(obra_data['Raio_Validacao']) if pd.notna(obra_data['Raio_Validacao']) else 100
    if distancia <= raio:
        return True, f"✅ Localização válida (distância: {distancia:.0f}m)"
    else:
        return False, f"❌ Fora do raio permitido (distância: {distancia:.0f}m > {raio}m)"

# --- 6. FUNÇÕES DE FATURAÇÃO ---
def calcular_valor_horas(registos_periodo):
    valor_total = 0
    for _, reg in registos_periodo.iterrows():
        tecnico_data = users[users['Nome'] == reg['Técnico']]
        if not tecnico_data.empty:
            cargo = tecnico_data.iloc[0].get('Cargo', 'Técnico')
            taxa = TAXA_HORA_POR_CARGO.get(cargo, 15.00)
            valor_total += reg['Horas_Total'] * taxa
    return valor_total

def gerar_pdf_fatura(dados_fatura, registos):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elementos = []
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#112240'),
        spaceAfter=30
    )
    elementos.append(Paragraph(f"FATURA Nº {dados_fatura['Numero']}", titulo_style))
    
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=10)
    elementos.append(Paragraph(f"Data de Emissão: {dados_fatura['Data_Emissao'].strftime('%d/%m/%Y')}", info_style))
    elementos.append(Paragraph(f"Data de Vencimento: {dados_fatura['Data_Vencimento'].strftime('%d/%m/%Y')}", info_style))
    elementos.append(Paragraph(f"Cliente: {dados_fatura['Cliente']}", info_style))
    elementos.append(Spacer(1, 20))
    
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

# --- 7. GESTÃO DE SESSÃO ---
if 'user' not in st.session_state: 
    st.session_state.user = None
if 'data_consulta' not in st.session_state: 
    st.session_state.data_consulta = datetime.now().date()
if 'turnos_temp' not in st.session_state: 
    st.session_state.turnos_temp = []

# --- 8. LOGIN ---
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# 🏗️ GestNow Elite")
        st.markdown("---")
        with st.form("login_form"):
            u = st.text_input("👤 Utilizador").strip()
            p = st.text_input("🔐 Password", type="password").strip()
            submitted = st.form_submit_button("ENTRAR", use_container_width=True)
            if submitted:
                if u.lower() == "admin" and p == "admin":
                    st.session_state.user = "Admin"
                    st.session_state.tipo = "Admin"
                    st.rerun()
                else:
                    for _, row in users.iterrows():
                        if row['Nome'].lower() == u.lower() and check_password(p, row['Password']):
                            st.session_state.user = row['Nome']
                            st.session_state.tipo = row['Tipo']
                            st.rerun()
                    st.error("❌ Credenciais inválidas")
    st.stop()

# --- 9. HEADER ---
st.markdown(f"""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin:0;">GestNow Elite</h1>
            <p style="margin:5px 0 0 0; opacity:0.9;">{st.session_state.user} • {st.session_state.tipo}</p>
        </div>
        <div>
            <span class="status-badge badge-aprovado">{datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🧭 Navegação")
    if st.session_state.tipo == "Admin":
        menu = st.radio("Menu Principal", [
            "📊 Dashboard", "✅ Aprovações", "👥 Pessoal", "🏗️ Obras",
            "📍 Geolocalização", "💰 Faturação", "📈 Relatórios", "⚙️ Configurações"
        ])
    else:
        menu = st.radio("Menu Principal", ["📅 Meu Ponto", "📍 Check-in/out", "📊 Meu Resumo", "💰 Minhas Horas"])
    st.markdown("---")
    if st.button("🚪 Terminar Sessão", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 10. ADMIN ---
if st.session_state.tipo == "Admin":
    if menu == "📊 Dashboard":
        st.title("📊 Dashboard")
        periodo = st.selectbox("Período", ["7d", "30d", "90d", "12m"])
        hoje = datetime.now()
        dias = {"7d": 7, "30d": 30, "90d": 90, "12m": 365}[periodo]
        data_inicio = hoje - timedelta(days=dias)
        mask = registos_db['Data'] >= pd.Timestamp(data_inicio)
        dados = registos_db[mask].copy()
        if not dados.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Horas Totais", f"{dados['Horas_Total'].sum():.1f}h")
            with col2:
                st.metric("Técnicos", dados['Técnico'].nunique())
            with col3:
                st.metric("Obras", dados['Obra'].nunique())
            with col4:
                st.metric("Média Diária", f"{dados.groupby('Data')['Horas_Total'].sum().mean():.1f}h")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                horas_dia = dados.groupby('Data')['Horas_Total'].sum().reset_index()
                fig = px.line(horas_dia, x='Data', y='Horas_Total', title='Horas por Dia')
                st.plotly_chart(fig, use_container_width=True)
            with col_g2:
                horas_obra = dados.groupby('Obra')['Horas_Total'].sum().reset_index()
                fig = px.pie(horas_obra, values='Horas_Total', names='Obra', title='Horas por Obra')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados no período")

    elif menu == "✅ Aprovações":
        st.title("✅ Aprovações")
        pendentes = registos_db[registos_db['Status'] == "0"].copy()
        if pendentes.empty:
            st.info("Nenhum registo pendente")
        else:
            for idx, row in pendentes.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        data_str = row['Data'].strftime('%d/%m/%Y') if pd.notna(row['Data']) else "Data inválida"
                        st.markdown(f"**{row['Técnico']}** | {row['Obra']} | {data_str} | {row['Turnos']} | {row['Horas_Total']:.1f}h")
                    with col2:
                        if st.button("✅ Aprovar", key=f"ap_{idx}"):
                            registos_db.at[idx, 'Status'] = "1"
                            save_db(registos_db, "registos.csv")
                            st.rerun()
                    with col3:
                        if st.button("🔵 Fechar", key=f"fe_{idx}"):
                            registos_db.at[idx, 'Status'] = "2"
                            save_db(registos_db, "registos.csv")
                            st.rerun()
                    with st.expander("📝 Ver relatório"):
                        st.write(row['Relatorio'] if pd.notna(row['Relatorio']) else "Sem relatório")
                    st.divider()

    elif menu == "👥 Pessoal":
        st.title("👥 Pessoal")
        with st.expander("➕ Novo Utilizador"):
            with st.form("novo_user"):
                nu = st.text_input("Nome")
                np = st.text_input("Password", type="password")
                nt = st.selectbox("Tipo", ["Técnico", "Chefe de Equipa", "Admin"])
                email = st.text_input("Email")
                tel = st.text_input("Telefone")
                cargo = st.selectbox("Cargo", ["Técnico", "Chefe de Equipa", "Admin"])
                if st.form_submit_button("Criar"):
                    if nu and np:
                        hashed = hash_password(np)
                        novo = pd.DataFrame([{
                            "Nome": nu, "Password": hashed, "Tipo": nt,
                            "Email": email, "Telefone": tel, "Cargo": cargo
                        }])
                        users = pd.concat([users, novo], ignore_index=True)
                        save_db(users, "usuarios.csv")
                        st.success(f"✅ {nu} criado!")
                        st.rerun()
        st.dataframe(users, use_container_width=True)

    elif menu == "🏗️ Obras":
        st.title("🏗️ Obras")
        with st.expander("➕ Nova Obra"):
            with st.form("nova_obra"):
                no = st.text_input("Nome da Obra")
                cliente = st.text_input("Cliente")
                local = st.text_input("Local")
                ativa = st.selectbox("Ativa", ["Sim", "Não"])
                lat = st.number_input("Latitude", value=38.7223, format="%.6f")
                lon = st.number_input("Longitude", value=-9.1393, format="%.6f")
                raio = st.number_input("Raio de Validação (m)", value=100, min_value=10)
                if st.form_submit_button("Criar"):
                    if no:
                        nova = pd.DataFrame([{
                            "Obra": no, "Cliente": cliente, "Local": local, "Ativa": ativa,
                            "Latitude": str(lat), "Longitude": str(lon), "Raio_Validacao": str(raio)
                        }])
                        obras_db = pd.concat([obras_db, nova], ignore_index=True)
                        save_db(obras_db, "obras_lista.csv")
                        st.success(f"✅ Obra {no} criada!")
                        st.rerun()
        st.dataframe(obras_db, use_container_width=True)

    elif menu == "📍 Geolocalização":
        st.title("📍 Geolocalização")
        tab1, tab2, tab3 = st.tabs(["🗺️ Mapa", "🏗️ Configurar Obras", "✅ Validações"])
        with tab1:
            m = folium.Map(location=[38.7223, -9.1393], zoom_start=10)
            for _, obra in obras_db.iterrows():
                if pd.notna(obra['Latitude']) and pd.notna(obra['Longitude']):
                    folium.Marker(
                        [float(obra['Latitude']), float(obra['Longitude'])],
                        popup=f"🏗️ {obra['Obra']}",
                        icon=folium.Icon(color='red')
                    ).add_to(m)
                    raio = float(obra['Raio_Validacao']) if pd.notna(obra['Raio_Validacao']) else 100
                    folium.Circle(
                        [float(obra['Latitude']), float(obra['Longitude'])],
                        radius=raio, color='blue', fill=True, fillOpacity=0.1
                    ).add_to(m)
            for _, reg in registos_db.iterrows():
                if reg['Localizacao_Checkin']:
                    try:
                        lat, lon = map(float, reg['Localizacao_Checkin'].split(','))
                        folium.Marker(
                            [lat, lon],
                            popup=f"👤 {reg['Técnico']}",
                            icon=folium.Icon(color='green', icon='user')
                        ).add_to(m)
                    except:
                        pass
            folium_static(m)
        with tab2:
            obra = st.selectbox("Selecionar Obra", obras_db['Obra'].tolist())
            obra_data = obras_db[obras_db['Obra'] == obra].iloc[0]
            with st.form("config_local"):
                lat = st.number_input("Latitude", value=float(obra_data['Latitude']) if pd.notna(obra_data['Latitude']) else 38.7223, format="%.6f")
                lon = st.number_input("Longitude", value=float(obra_data['Longitude']) if pd.notna(obra_data['Longitude']) else -9.1393, format="%.6f")
                raio = st.number_input("Raio (m)", value=int(obra_data['Raio_Validacao']) if pd.notna(obra_data['Raio_Validacao']) else 100)
                if st.form_submit_button("Guardar"):
                    idx = obras_db[obras_db['Obra'] == obra].index[0]
                    obras_db.at[idx, 'Latitude'] = str(lat)
                    obras_db.at[idx, 'Longitude'] = str(lon)
                    obras_db.at[idx, 'Raio_Validacao'] = str(raio)
                    save_db(obras_db, "obras_lista.csv")
                    st.success("✅ Coordenadas atualizadas!")
                    st.rerun()
        with tab3:
            validados = registos_db[registos_db['Localizacao_Checkin'] != ""].copy()
            if not validados.empty:
                st.dataframe(validados[['Data', 'Técnico', 'Obra', 'Localizacao_Checkin']])
            else:
                st.info("Sem registos com localização")

    elif menu == "💰 Faturação":
        st.title("💰 Faturação")
        tab1, tab2 = st.tabs(["➕ Nova Fatura", "📋 Lista"])
        with tab1:
            st.subheader("Criar Nova Fatura")
            col1, col2 = st.columns(2)
            with col1:
                cliente = st.selectbox("Cliente", obras_db['Cliente'].unique())
                obra_sel = obras_db[obras_db['Cliente'] == cliente]['Obra'].tolist()
                obra = st.selectbox("Obra", obra_sel)
            with col2:
                inicio = st.date_input("Período Início", datetime.now() - timedelta(days=30))
                fim = st.date_input("Período Fim", datetime.now())
            regs = registos_db[
                (registos_db['Obra'] == obra) &
                (registos_db['Data'] >= pd.Timestamp(inicio)) &
                (registos_db['Data'] <= pd.Timestamp(fim)) &
                (registos_db['Status'] == "1")
            ].copy()
            if not regs.empty:
                st.metric("Total Horas", f"{regs['Horas_Total'].sum():.1f}h")
                st.metric("Valor Total", f"€{calcular_valor_horas(regs):,.2f}")
                if st.button("📄 GERAR FATURA"):
                    ano = datetime.now().year
                    ultimo = len(faturas_db[faturas_db['Data_Emissao'].dt.year == ano])
                    num = f"FT-{ano}-{ultimo + 1:04d}"
                    nova = pd.DataFrame([{
                        "Numero": num,
                        "Cliente": cliente,
                        "Data_Emissao": datetime.now().strftime('%d/%m/%Y'),
                        "Data_Vencimento": (datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y'),
                        "Valor": calcular_valor_horas(regs),
                        "Status": "Pendente",
                        "Periodo_Inicio": inicio.strftime('%d/%m/%Y'),
                        "Periodo_Fim": fim.strftime('%d/%m/%Y'),
                        "Obra": obra
                    }])
                    faturas_db = pd.concat([faturas_db, nova], ignore_index=True)
                    save_db(faturas_db, "faturas.csv")
                    pdf = gerar_pdf_fatura(nova.iloc[0].to_dict(), regs)
                    st.success(f"✅ Fatura {num} criada!")
                    st.download_button("📥 Download PDF", data=pdf, file_name=f"Fatura_{num}.pdf", mime="application/pdf")
            else:
                st.warning("Sem registos aprovados no período")
        with tab2:
            st.subheader("Faturas Emitidas")
            if not faturas_db.empty:
                for _, fat in faturas_db.iterrows():
                    status_class = {
                        "Pendente": "badge-pendente",
                        "Paga": "badge-aprovado",
                        "Vencida": "badge-fechado"
                    }.get(fat['Status'], "badge-pendente")
                    st.markdown(f"""
                    <div class="fatura-card">
                        <div style="display: flex; justify-content: space-between;">
                            <h4>{fat['Numero']}</h4>
                            <span class="status-badge {status_class}">{fat['Status']}</span>
                        </div>
                        <p>{fat['Cliente']} | €{fat['Valor']:,.2f}</p>
                        <p>Emissão: {fat['Data_Emissao'].strftime('%d/%m/%Y')} | Vencimento: {fat['Data_Vencimento'].strftime('%d/%m/%Y')}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Sem faturas")

# --- 11. TÉCNICO ---
else:
    if menu == "📅 Meu Ponto":
        st.title("📅 Meu Ponto")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀", use_container_width=True):
                st.session_state.data_consulta -= timedelta(days=1)
                st.rerun()
        with col2:
            data_str = st.session_state.data_consulta.strftime("%d/%m/%Y")
            st.markdown(f"<h3 style='text-align:center;'>{data_str}</h3>", unsafe_allow_html=True)
        with col3:
            if st.button("▶", use_container_width=True):
                st.session_state.data_consulta += timedelta(days=1)
                st.rerun()
        meus_regs = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'] == pd.Timestamp(st.session_state.data_consulta))
        ]
        if not meus_regs.empty:
            total = meus_regs['Horas_Total'].sum()
            st.markdown(f"<h2 style='text-align:center;'>{total:.1f}h</h2>", unsafe_allow_html=True)
            for _, row in meus_regs.iterrows():
                status = ["Pendente", "Aprovado", "Fechado"][int(row['Status'])]
                st.markdown(f"""
                <div style="background:white; padding:10px; border-radius:5px; margin-bottom:5px;">
                    <b>{row['Obra']}</b> – {row['Turnos']} ({row['Horas_Total']:.1f}h) – <span style="color:{'orange' if status=='Pendente' else 'green'};">{status}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sem registos neste dia")
        if st.session_state.data_consulta == datetime.now().date():
            st.divider()
            with st.expander("➕ Adicionar Turno"):
                obra = st.selectbox("Obra", obras_db['Obra'].tolist())
                frentes = frentes_db[frentes_db['Obra'] == obra]['Frente'].tolist()
                frente = st.selectbox("Frente", frentes if frentes else ["Geral"])
                h1 = st.time_input("Início", datetime.now().replace(hour=8, minute=0))
                h2 = st.time_input("Fim", datetime.now().replace(hour=17, minute=0))
                rel = st.text_area("Relatório")
                if st.button("Registar"):
                    if h2 > h1:
                        horas = (datetime.combine(datetime.today(), h2) - datetime.combine(datetime.today(), h1)).seconds / 3600
                        turno = f"{h1.strftime('%H:%M')}-{h2.strftime('%H:%M')}"
                        novo = pd.DataFrame([{
                            "Data": data_str,
                            "Técnico": st.session_state.user,
                            "Obra": obra,
                            "Frente": frente,
                            "Turnos": turno,
                            "Relatorio": rel,
                            "Status": "0",
                            "Horas_Total": horas,
                            "Localizacao_Checkin": "",
                            "Localizacao_Checkout": ""
                        }])
                        registos_db = pd.concat([registos_db, novo], ignore_index=True)
                        save_db(registos_db, "registos.csv")
                        st.success("✅ Turno registado!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Fim deve ser após início")

    elif menu == "📍 Check-in/out":
        st.title("📍 Check-in/out")
        hoje = datetime.now().strftime("%d/%m/%Y")
        meu_hoje = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'] == pd.Timestamp(datetime.now().date()))
        ]
        if not meu_hoje.empty and meu_hoje.iloc[0]['Localizacao_Checkin']:
            st.success("✅ Check-in realizado hoje")
        else:
            st.warning("Ainda não fez check-in hoje")
            obra = st.selectbox("Selecionar obra", obras_db['Obra'].tolist())
            st.markdown("### 📱 Inserir coordenadas manualmente")
            lat = st.number_input("Latitude", value=38.7223, format="%.6f")
            lon = st.number_input("Longitude", value=-9.1393, format="%.6f")
            if st.button("✅ Fazer Check-in"):
                valido, msg = verificar_localizacao_obra(lat, lon, obra)
                if valido:
                    if meu_hoje.empty:
                        novo = pd.DataFrame([{
                            "Data": hoje,
                            "Técnico": st.session_state.user,
                            "Obra": obra,
                            "Frente": "",
                            "Turnos": "",
                            "Relatorio": "",
                            "Status": "0",
                            "Horas_Total": 0,
                            "Localizacao_Checkin": f"{lat},{lon}",
                            "Localizacao_Checkout": ""
                        }])
                        registos_db = pd.concat([registos_db, novo], ignore_index=True)
                    else:
                        idx = meu_hoje.index[0]
                        registos_db.at[idx, 'Localizacao_Checkin'] = f"{lat},{lon}"
                    save_db(registos_db, "registos.csv")
                    st.success(f"✅ Check-in realizado! {msg}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)

    elif menu == "📊 Meu Resumo":
        st.title("📊 Meu Resumo")
        periodo = st.selectbox("Período", ["Esta semana", "Este mês", "Últimos 30 dias"])
        hoje = datetime.now()
        if periodo == "Esta semana":
            inicio = hoje - timedelta(days=hoje.weekday())
        elif periodo == "Este mês":
            inicio = hoje.replace(day=1)
        else:
            inicio = hoje - timedelta(days=30)
        meus = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'] >= pd.Timestamp(inicio)) &
            (registos_db['Data'] <= pd.Timestamp(hoje))
        ].copy()
        if not meus.empty:
            total = meus['Horas_Total'].sum()
            dias = meus['Data'].nunique()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Horas", f"{total:.1f}h")
            with col2:
                st.metric("Dias", dias)
            with col3:
                st.metric("Média/Dia", f"{total/dias:.1f}h")
            horas_dia = meus.groupby('Data')['Horas_Total'].sum().reset_index()
            fig = px.bar(horas_dia, x='Data', y='Horas_Total', title='Horas por Dia')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados no período")

    elif menu == "💰 Minhas Horas":
        st.title("💰 Minhas Horas")
        mes = st.selectbox("Mês", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        ano = st.selectbox("Ano", [2024, 2025, 2026])
        meses = {"Janeiro":1, "Fevereiro":2, "Março":3, "Abril":4, "Maio":5, "Junho":6,
                 "Julho":7, "Agosto":8, "Setembro":9, "Outubro":10, "Novembro":11, "Dezembro":12}
        meus = registos_db[
            (registos_db['Técnico'] == st.session_state.user) &
            (registos_db['Data'].dt.year == ano) &
            (registos_db['Data'].dt.month == meses[mes]) &
            (registos_db['Status'] == "1")
        ].copy()
        if not meus.empty:
            cargo = users[users['Nome'] == st.session_state.user].iloc[0].get('Cargo', 'Técnico')
            taxa = TAXA_HORA_POR_CARGO.get(cargo, 15.00)
            total = meus['Horas_Total'].sum()
            valor = total * taxa
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Horas", f"{total:.1f}h")
            with col2:
                st.metric("Valor/h", f"€{taxa:.2f}")
            with col3:
                st.metric("Total", f"€{valor:,.2f}")
            st.dataframe(meus[['Data', 'Obra', 'Horas_Total']])
        else:
            st.info("Sem horas aprovadas neste mês")

# --- 12. INICIALIZAR DADOS ---
if users.empty and st.session_state.user == "Admin":
    admin_hash = hash_password("admin")
    users = pd.DataFrame([{
        "Nome": "Admin", "Password": admin_hash, "Tipo": "Admin",
        "Email": "admin@gestnow.pt", "Telefone": "999999999", "Cargo": "Admin"
    }])
    save_db(users, "usuarios.csv")
    obras_db = pd.DataFrame([{
        "Obra": "Obra Central", "Cliente": "Cliente Exemplo", "Local": "Lisboa",
        "Ativa": "Sim", "Latitude": "38.7223", "Longitude": "-9.1393", "Raio_Validacao": "100"
    }])
    save_db(obras_db, "obras_lista.csv")
    st.rerun()

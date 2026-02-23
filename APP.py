import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# 1. Configuração da Página
st.set_page_config(page_title="GestNow", page_icon="🎯", layout="wide")

# 2. LIMPEZA TOTAL DA INTERFACE (CSS)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stStatusWidget"] {visibility: hidden;}
    [data-testid="stDecoration"] {display:none;}
    .main { background-color: #f5f7f9; }
    .stButton>button { 
        border-radius: 5px; height: 3em; background-color: #004b87; 
        color: white; font-weight: bold; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def carregar_csv(ficheiro, colunas):
    if os.path.exists(ficheiro):
        df = pd.read_csv(ficheiro)
        return df.dropna(subset=['Nome']) if 'Nome' in df.columns else df
    return pd.DataFrame(columns=colunas)

def guardar_csv(df, ficheiro):
    df.to_csv(ficheiro, index=False)

def calcular_horas(row):
    try:
        fmt = '%H:%M'
        tdelta = datetime.strptime(row['Saída'], fmt) - datetime.strptime(row['Entrada'], fmt)
        return round(tdelta.total_seconds() / 3600, 2)
    except: return 0

# --- INICIALIZAÇÃO ---
df_users = carregar_csv("usuarios.csv", ["Nome", "Password", "Tipo"])

# ATUALIZAÇÃO DE PASSWORD MESTRE
if df_users.empty or not df_users[df_users['Nome'] == 'Admin']['Password'].iloc[0] == 'DeltaPlus2026':
    df_users = pd.DataFrame([{"Nome": "Admin", "Password": "DeltaPlus2026", "Tipo": "Admin"}])
    guardar_csv(df_users, "usuarios.csv")

df_obras = carregar_csv("obras.csv", ["Nome"])
# Limpeza de valores nulos/nan nas obras
df_obras = df_obras.dropna().reset_index(drop=True)

df_registos = carregar_csv("registos_completos.csv", ["Data", "Trabalhador", "Obra", "Entrada", "Saída"])
if not df_registos.empty:
    df_registos['Horas'] = df_registos.apply(calcular_horas, axis=1)

# --- SISTEMA DE LOGIN ---
if 'user' not in st.session_state: st.session_state['user'] = None

if st.session_state['user'] is None:
    # IMAGEM FUTURISTA GESTÃO INTELIGENTE
    st.image("https://raw.githubusercontent.com/diogofilipe24/gestnow/main/gestao_capa.png", use_container_width=True, caption="GESTÃO INTELIGENTE - DELTAPLUS")
    st.title("GestNow")
    with st.form("login"):
        u = st.text_input("Utilizador")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Entrar"):
            user_match = df_users[(df_users['Nome'] == u) & (df_users['Password'] == p)]
            if not user_match.empty:
                st.session_state['user'] = u
                st.session_state['tipo'] = user_match.iloc[0]['Tipo']
                st.rerun()
            else: st.error("Dados incorretos.")
    st.stop()

# --- INTERFACE ---
st.sidebar.title(f"Olá, {st.session_state['user']}")
if st.sidebar.button("Sair"):
    st.session_state['user'] = None
    st.rerun()

# ÁREA COLABORADOR
if st.session_state['tipo'] == "Colaborador":
    st.header(f"📍 Ponto: {st.session_state['user']}")
    with st.container(border=True):
        d = st.date_input("Data", datetime.now())
        # Filtro para garantir que não aparece "nan"
        lista_obras = df_obras['Nome'].tolist() if not df_obras.empty else []
        o = st.selectbox("Obra", ["Seleccione a Obra"] + lista_obras)
        c1, c2 = st.columns(2)
        with c1: ent = st.time_input("Entrada", datetime.now().replace(hour=8, minute=0))
        with c2: sai = st.time_input("Saída", datetime.now().replace(hour=17, minute=0))
        
        if st.button("ENVIAR REGISTO"):
            if o == "Seleccione a Obra":
                st.error("Por favor, selecione uma obra válida.")
            else:
                novo = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Trabalhador": st.session_state['user'], "Obra": o, "Entrada": ent.strftime("%H:%M"), "Saída": sai.strftime("%H:%M")}])
                novo.to_csv("registos_completos.csv", mode='a', index=False, header=not os.path.exists("registos_completos.csv"))
                st.success("✅ Registo guardado com sucesso!")

# ÁREA ADMIN
else:
    st.header("⚙️ Painel de Controlo DeltaPlus")
    t1, t2, t3 = st.tabs(["👥 Gestão de Staff", "📊 Totais de Horas", "📥 Relatório Excel"])
    
    with t1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Trabalhadores")
            nu = st.text_input("Novo Nome")
            np = st.text_input("Password Colaborador", type="password")
            if st.button("💾 Guardar"):
                if nu and np:
                    df_users = pd.concat([df_users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": "Colaborador"}])], ignore_index=True)
                    guardar_csv(df_users, "usuarios.csv"); st.rerun()
            st.write("---")
            user_del = st.selectbox("Eliminar:", df_users[df_users['Tipo']=='Colaborador']['Nome'])
            if st.button("❌ Remover"):
                df_users = df_users[df_users['Nome'] != user_del]
                guardar_csv(df_users, "usuarios.csv"); st.rerun()
        with col2:
            st.subheader("Obras")
            no = st.text_input("Nova Obra")
            if st.button("💾 Registar"):
                if no:
                    df_obras = pd.concat([df_obras, pd.DataFrame([{"Nome": no}])], ignore_index=True)
                    guardar_csv(df_obras, "obras.csv"); st.rerun()
            st.write("---")
            obra_del = st.selectbox("Eliminar Obra:", df_obras['Nome'])
            if st.button("❌ Apagar"):
                df_obras = df_obras[df_obras['Nome'] != obra_del]
                guardar_csv(df_obras, "obras.csv"); st.rerun()

    with t2:
        st.subheader("Análise de Horas")
        f_o = st.multiselect("Filtrar Obra:", df_obras['Nome'])
        f_s = st.multiselect("Filtrar Trabalhador:", df_users['Nome'])
        df_view = df_registos.copy()
        if f_o: df_view = df_view[df_view['Obra'].isin(f_o)]
        if f_s: df_view = df_view[df_view['Trabalhador'].isin(f_s)]
        st.dataframe(df_view, use_container_width=True)
        if not df_view.empty:
            st.metric("SOMATÓRIO TOTAL", f"{df_view['Horas'].sum()} horas")
        if st.button("🔄 Atualizar Dados"): st.rerun()

    with t3:
        st.subheader("Exportação Profissional")
        if not df_registos.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_registos.sort_values(by='Data', ascending=False).to_excel(writer, index=False, sheet_name='Ponto')
                workbook = writer.book
                worksheet = writer.sheets['Ponto']
                # Formatação bonita
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#004b87', 'font_color': 'white'})
                for col_num, value in enumerate(df_registos.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)
                worksheet.set_column('A:F', 20) # Ajustar largura
            
            st.download_button(label="📥 DESCARREGAR EXCEL FORMATADO", data=output.getvalue(), file_name=f"Relatorio_Ponto_{datetime.now().strftime('%d_%m')}.xlsx")

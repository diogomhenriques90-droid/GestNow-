import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuração Base
st.set_page_config(page_title="GestNow Pro", layout="centered")

# --- SISTEMA DE ARQUIVOS ---
def carregar_dados(file, colunas):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, file):
    df.to_csv(file, index=False)

# Carregar listas (Obras e Colaboradores)
df_obras = carregar_dados("obras.csv", ["Nome"])
df_staff = carregar_dados("staff.csv", ["Nome"])
df_registos = carregar_dados("registos.csv", ["Data", "Hora", "Trabalhador", "Obra", "Tipo"])

# --- LOGIN SIMPLES ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔐 Acesso GestNow")
    senha = st.text_input("Introduza a Chave de Acesso:", type="password")
    if st.button("Entrar"):
        if senha == "1234": # <--- MUDA ESTA SENHA DEPOIS
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("Chave incorreta")
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.title("🏗️ GestNow - Gestão de Obra")
menu = st.sidebar.selectbox("Navegação", ["Registo de Ponto", "Painel Administrativo"])

# 1. REGISTO DE PONTO (PARA TRABALHADORES)
if menu == "Registo de Ponto":
    st.subheader("📍 Picagem de Ponto")
    
    if df_obras.empty or df_staff.empty:
        st.warning("⚠️ O Administrador precisa de configurar obras e staff primeiro.")
    else:
        obra = st.selectbox("Selecione a Obra:", df_obras["Nome"])
        nome = st.selectbox("Selecione o seu Nome:", df_staff["Nome"])
        tipo = st.radio("Tipo de Registo:", ["Entrada", "Saída"])
        hora_confirmada = st.time_input("Confirme o Horário:", datetime.now().time())
        
        if st.button("🔴 REGISTAR AGORA", use_container_width=True):
            agora = datetime.now().strftime("%d/%m/%Y")
            novo_registo = pd.DataFrame([{"Data": agora, "Hora": hora_confirmada.strftime("%H:%M"), "Trabalhador": nome, "Obra": obra, "Tipo": tipo}])
            df_registos = pd.concat([df_registos, novo_registo], ignore_index=True)
            salvar_dados(df_registos, "registos.csv")
            st.success(f"Registo de {tipo} efetuado para {nome}!")

# 2. PAINEL ADMINISTRATIVO (PARA TI)
elif menu == "Painel Administrativo":
    st.subheader("⚙️ Gestão de Dados")
    
    tab1, tab2, tab3 = st.tabs(["Listas de Base", "Visualizar Registos", "Exportar"])
    
    with tab1:
        st.write("---")
        nova_obra = st.text_input("Nova Obra / Frente:")
        if st.button("Adicionar Obra"):
            if nova_obra:
                df_obras = pd.concat([df_obras, pd.DataFrame([{"Nome": nova_obra}])], ignore_index=True)
                salvar_dados(df_obras, "obras.csv")
                st.rerun()

        st.write("---")
        novo_staff = st.text_input("Novo Colaborador:")
        if st.button("Adicionar Staff"):
            if novo_staff:
                df_staff = pd.concat([df_staff, pd.DataFrame([{"Nome": novo_staff}])], ignore_index=True)
                salvar_dados(df_staff, "staff.csv")
                st.rerun()
                
    with tab2:
        st.dataframe(df_registos, use_container_width=True)
        if st.button("Limpar Todos os Registos"):
            if st.checkbox("Confirmo que quero apagar tudo"):
                os.remove("registos.csv")
                st.rerun()

    with tab3:
        if not df_registos.empty:
            csv = df_registos.to_csv(index=False).encode('utf-8')
            st.download_button("📥 DESCARREGAR EXCEL (CSV)", csv, "registos_obra.csv", "text/csv")
        else:
            st.info("Ainda não há dados para exportar.")


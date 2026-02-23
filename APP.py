import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="GestNow Master", layout="centered")
st.title("🏗️ GestNow - Controlo de Obra")

menu = st.sidebar.selectbox("Menu", ["Registo de Ponto", "Histórico"])

if menu == "Registo de Ponto":
    st.subheader("📍 Registo Rápido")
    obra = st.selectbox("Obra:", ["Sines", "Setúbal", "Matosinhos"])
    nome = st.text_input("Trabalhador:")
    if st.button("🔴 REGISTAR", use_container_width=True):
        if nome:
            agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            path = "pontos.csv"
            pd.DataFrame([{"Data": agora, "Nome": nome, "Obra": obra}]).to_csv(path, mode='a', index=False, header=not os.path.exists(path))
            st.success(f"Feito! {nome}")
        else:
            st.error("Escreva o nome!")

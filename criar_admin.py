import streamlit as st
from core import hp, save_db, load_all
import pandas as pd

st.title("🔧 Criar Utilizador Admin")

if st.button("Criar Admin"):
    users = load_all()[0]
    
    # Criar admin
    new_admin = pd.DataFrame([{
        "Nome": "admin",
        "Password": hp("admin123"),  # Password: admin123
        "Tipo": "Admin",
        "Email": "admin@gestnow.com",
        "Telefone": "+351 912345678",
        "Cargo": "Administrador",
        "NIF": "",
        "NISS": "",
        "CC": "",
        "DataNasc": "",
        "Nacionalidade": "Portugal",
        "Morada": "",
        "Foto": "",
        "PrecoHora": "0",
        "PrecoHoraStatus": "",
        "PrecoHoraData": "",
        "PIN": "1234"  # PIN alternativo
    }])
    
    users = pd.concat([users, new_admin], ignore_index=True)
    save_db(users, "usuarios.csv")
    
    st.success("✅ Admin criado!")
    st.info("Utilizador: **admin**")
    st.info("Password: **admin123**")
    st.info("PIN: **1234**")
    st.warning("⚠️ Mude a password após login!")

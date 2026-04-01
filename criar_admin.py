import streamlit as st
from core import hp, save_db, load_all
import pandas as pd

st.title("🔧 Criar Utilizador Admin")
st.info("Este script cria o utilizador 'Admin' com password 'admin'")

if st.button("Criar Utilizador Admin", type="primary"):
    try:
        # Carregar utilizadores existentes
        users = load_all()[0]
        
        # Verificar se já existe
        if 'Admin' in users['Nome'].values:
            st.warning("⚠️ Utilizador 'Admin' já existe!")
            st.info("Utilizadores existentes:")
            st.write(users['Nome'].tolist())
        else:
            # Criar admin
            new_admin = pd.DataFrame([{
                "Nome": "Admin",
                "Password": hp("admin"),  # Hash da password "admin"
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
                "PIN": "0000"  # PIN alternativo
            }])
            
            # Adicionar e guardar
            users = pd.concat([users, new_admin], ignore_index=True)
            save_db(users, "usuarios.csv")
            
            st.success("✅ Utilizador Admin criado com sucesso!")
            st.markdown("---")
            st.info("👤 Utilizador: **Admin**")
            st.info("🔑 Password: **admin**")
            st.info("🔢 PIN: **0000**")
            st.warning("⚠️ **Mude a password após o primeiro login!**")
            
    except Exception as e:
        st.error(f"❌ Erro: {e}")

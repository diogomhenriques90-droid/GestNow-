import streamlit as st
from core import hp, save_db, load_all
import pandas as pd

def render_criar_admin():
    """Página para criar utilizador Admin"""
    st.title("🔧 Criar Utilizador Admin")
    st.info("Este script cria o utilizador 'Admin' com password 'admin'")
    
    if st.button("Criar Utilizador Admin", type="primary"):
        try:
            users = load_all()[0]
            
            if 'Admin' in users['Nome'].values:
                st.warning("⚠️ Utilizador 'Admin' já existe!")
                st.write(users[users['Nome'] == 'Admin'])
            else:
                new_admin = pd.DataFrame([{
                    "Nome": "Admin",
                    "Password": hp("admin"),
                    "Tipo": "Admin",
                    "Email": "admin@gestnow.com",
                    "Telefone": "+351 912345678",
                    "Cargo": "Administrador",
                    "NIF": "", "NISS": "", "CC": "",
                    "DataNasc": "", "Nacionalidade": "Portugal",
                    "Morada": "", "Foto": "",
                    "PrecoHora": "0", "PrecoHoraStatus": "",
                    "PrecoHoraData": "", "PIN": "0000"
                }])
                
                users = pd.concat([users, new_admin], ignore_index=True)
                save_db(users, "usuarios.csv")
                
                st.success("✅ Utilizador Admin criado!")
                st.markdown("---")
                st.info("👤 Utilizador: **Admin**")
                st.info("🔑 Password: **admin**")
                st.info("🔢 PIN: **0000**")
                st.warning("⚠️ **Mude a password após login!**")
                
                st.markdown("### 🔗 Links:")
                st.markdown("[Voltar ao Login](/?page=)")
                
        except Exception as e:
            st.error(f"❌ Erro: {e}")

import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- 1. DESIGN ---
st.set_page_config(page_title="GestNow | Turnos", layout="wide")
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0A192F; color: #FFFFFF !important; }
    .stButton>button { background-color: #00D2FF; color: #0A192F; font-weight: bold; border-radius: 5px; height: 3em; }
    .btn-add>button { background-color: #28A745 !important; color: white !important; }
    input, select, textarea { background-color: #112240 !important; color: #FFFFFF !important; border: 2px solid #00D2FF !important; }
    label, p, h1, h2, h3, span { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS ---
def engine(f, col):
    if os.path.exists(f):
        try: return pd.read_csv(f, dtype=str).apply(lambda x: x.str.strip())
        except: pass
    return pd.DataFrame(columns=col)

users = engine("usuarios.csv", ["Nome", "Password", "Tipo"])
obras_db = engine("obras_lista.csv", ["Obra"])
frentes_db = engine("frentes_lista.csv", ["Obra", "Frente"])
registos = engine("registos.csv", ["Data", "Técnico", "Obra", "Frente", "Turnos", "Relatorio"])

# --- 3. LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'turnos_temp' not in st.session_state: st.session_state.turnos_temp = []

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>GESTNOW</h1>", unsafe_allow_html=True)
    u_input = st.text_input("Utilizador").strip()
    p_input = st.text_input("Palavra-Passe", type="password").strip()
    if st.button("ENTRAR"):
        if u_input.lower() in ["diogo", "admin"] and p_input in ["rafael2026", "123"]:
            st.session_state.user, st.session_state.tipo = u_input, "Admin"
            st.rerun()
        match = users[(users['Nome'].str.lower() == u_input.lower()) & (users['Password'] == p_input)]
        if not match.empty:
            st.session_state.user, st.session_state.tipo = match.iloc[0]['Nome'], match.iloc[0]['Tipo']
            st.rerun()
        else: st.error("Acesso Negado.")
    st.stop()

# --- 4. INTERFACE ADMIN (Simplificada para foco nos Turnos) ---
if st.session_state.tipo == "Admin":
    st.title("📊 Painel Administrativo")
    jt1, jt2, jt3, jt4 = st.tabs(["👥 Pessoal", "🏗️ Obras", "🚧 Frentes", "📋 Histórico"])
    
    with jt1:
        c1, c2 = st.columns([1, 2])
        with c1:
            nu, np = st.text_input("Nome"), st.text_input("Senha")
            nt = st.selectbox("Cargo", ["Colaborador", "Chefe de Equipa", "Recursos Humanos"])
            if st.button("Registar"):
                users = pd.concat([users, pd.DataFrame([{"Nome": nu, "Password": np, "Tipo": nt}])]).drop_duplicates(subset=['Nome'], keep='last')
                users.to_csv("usuarios.csv", index=False); st.rerun()
            u_del = st.selectbox("Eliminar", ["--"] + users['Nome'].tolist())
            if st.button("Remover"):
                users = users[users['Nome'] != u_del]
                users.to_csv("usuarios.csv", index=False); st.rerun()
        with c2: st.dataframe(users, use_container_width=True)

    with jt2:
        no = st.text_input("Nova Obra")
        if st.button("Gravar Obra"):
            obras_db = pd.concat([obras_db, pd.DataFrame([{"Obra": no}])]).drop_duplicates()
            obras_db.to_csv("obras_lista.csv", index=False); st.rerun()
        st.dataframe(obras_db)

    with jt3:
        o_sel = st.selectbox("Obra", obras_db['Obra'].tolist())
        nf = st.text_input("Nova Frente")
        if st.button("Gravar Frente"):
            frentes_db = pd.concat([frentes_db, pd.DataFrame([{"Obra": o_sel, "Frente": nf}])]).drop_duplicates()
            frentes_db.to_csv("frentes_lista.csv", index=False); st.rerun()
        st.dataframe(frentes_db)

    with jt4:
        st.dataframe(registos, use_container_width=True)

# --- 5. REGISTO DE PONTO POR TURNOS ---
else:
    st.title("🕒 Registo por Turnos")
    
    # Seleção de Obra e Frente (Fixo no topo)
    obra_sel = st.selectbox("Obra", ["--"] + sorted(obras_db['Obra'].unique().tolist()))
    f_list = frentes_db[frentes_db['Obra'] == obra_sel]['Frente'].tolist() if obra_sel != "--" else []
    frente_sel = st.selectbox("Frente de Trabalho", ["--"] + sorted(f_list))
    
    st.markdown("---")
    st.subheader("Adicionar Bloco de Horário")
    c_h1, c_h2 = st.columns(2)
    h_in = c_h1.time_input("Início do Turno", datetime.now())
    h_out = c_h2.time_input("Fim do Turno", datetime.now())
    
    st.markdown('<div class="btn-add">', unsafe_allow_html=True)
    if st.button("➕ ADICIONAR TURNO (Manhã/Tarde/Extra)"):
        turno_str = f"{h_in.strftime('%H:%M')}-{h_out.strftime('%H:%M')}"
        st.session_state.turnos_temp.append(turno_str)
        st.success(f"Turno {turno_str} adicionado à lista!")
    st.markdown('</div>', unsafe_allow_html=True)

    # Visualização dos turnos adicionados
    if st.session_state.turnos_temp:
        st.info(f"**Turnos Registados hoje:** {' | '.join(st.session_state.turnos_temp)}")
        if st.button("🗑️ Limpar Turnos"):
            st.session_state.turnos_temp = []
            st.rerun()
        
        st.markdown("---")
        # Só aparece o relatório e o envio final se houver turnos
        obs = st.text_area("Relatório Final do Dia / Observações")
        if st.button("🚀 SUBMETER TUDO PARA O HISTÓRICO"):
            if obra_sel != "--" and frente_sel != "--":
                novo_reg = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Técnico": st.session_state.user,
                    "Obra": obra_sel,
                    "Frente": frente_sel,
                    "Turnos": " / ".join(st.session_state.turnos_temp),
                    "Relatorio": obs if obs else "N/A"
                }])
                novo_reg.to_csv("registos.csv", mode='a', index=False, header=not os.path.exists("registos.csv"))
                st.session_state.turnos_temp = [] # Limpa a lista
                st.success("✅ Todos os turnos foram gravados!")
                st.balloons()
            else:
                st.error("Selecione a Obra e Frente antes de submeter!")
    else:
        st.warning("Adicione pelo menos um turno (ex: entrada e saída da manhã) para continuar.")

if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.session_state.turnos_temp = []
    st.rerun()

import streamlit as st
import pandas as pd
import uuid, secrets
from datetime import datetime, timedelta, date
from streamlit_drawable_canvas import st_canvas

# Imports do core (divididos em múltiplas linhas)
from core import (
    save_db, inv, fh, sl, render_metric,
    ICONS, COLORS, TIPOS_FRENTE, REGRAS_OURO,
    CATEGORIAS_SAFETY_WALK
)
from translations import t

def render_tecnico(*args):
    """Renderiza módulo Técnico com design industrial moderno"""
    
    # 1. Desempacotamento das variáveis
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args

    user_nome = st.session_state.get('user', 'Usuário')
    cargo_user = st.session_state.get('cargo', 'Técnico')
    user_tipo = st.session_state.get('tipo', 'Técnico')

    # Lógica de Permissões
    is_chefe = user_tipo in ['Chefe de Equipa', 'Admin', 'Gestor'] or cargo_user in ['Chefe de Equipa', 'Encarregado']
    
    # =============================================================================
    # HEADER COM BRANDING INDUSTRIAL
    # =============================================================================
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:30px 20px;
        background:linear-gradient(135deg, #1E293B, #0F172A);
        border-radius:20px;
        margin-bottom:30px;
        border:1px solid rgba(255,255,255,0.1);
    ">
        <div style="font-size:3rem; margin-bottom:10px;">{ICONS["technician"]}</div>
        <div style="font-size:1.8rem; font-weight:800; color:#F8FAFC;">{user_nome}</div>
        <div style="font-size:1rem; color:#94A3B8;">{cargo_user} | {user_tipo}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # CSS PERSONALIZADO
    # =============================================================================
    st.markdown("""
    <style>
    .rp-card {
        background: rgba(255,255,255,0.05);
        padding: 18px;
        border-radius: 15px;
        border-left: 6px solid #3B82F6;
        margin-bottom: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        backdrop-filter: blur(10px);
    }
    .rp-card.pendente { border-left-color: #F59E0B; }
    .rp-card.aprovado { border-left-color: #10B981; }
    .rp-card.fechado { border-left-color: #3B82F6; }
    .week-bar {
        background: rgba(255,255,255,0.08);
        padding: 15px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 20px;
    }
    .esign-seal {
        border: 2px dashed #10B981;
        padding: 15px;
        background: rgba(16,185,129,0.1);
        border-radius: 10px;
        color: #10B981;
        font-family: monospace;
        font-size: 0.85rem;
        margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # DEFINIÇÃO DE TABS
    # =============================================================================
    menu = [f"{ICONS['dashboard']} Pontos", f"{ICONS['safety']} Segurança (HSE)", f"{ICONS['profile']} Perfil"]
    if is_chefe:
        menu.insert(1, f"{ICONS['reports']} Folha de Ponto")
    
    tabs = st.tabs(menu)
    
    # =============================================================================
    # TAB 1: REGISTO DE PONTO (CALENDÁRIO & CARDS)
    # =============================================================================
    with tabs[0]:
        st.markdown(f"### {ICONS['dashboard']} Registo de Ponto")
        
        # Calendário Semanal Interativo
        hoje = date.today()
        if 'data_consulta' not in st.session_state:
            st.session_state.data_consulta = hoje
        
        d_sel = st.session_state.data_consulta
        inicio_sem = d_sel - timedelta(days=d_sel.weekday())
        dias_sem = [inicio_sem + timedelta(days=i) for i in range(7)]
        
        st.markdown('<div class="week-bar">', unsafe_allow_html=True)
        cols_cal = st.columns(7)
        for i, d in enumerate(dias_sem):
            with cols_cal[i]:
                # Verificar se há registos para o ícone
                status_dia = "⚪"
                if not registos_db.empty:
                    dia_regs = registos_db[
                        (registos_db['Técnico'] == user_nome) &
                        (pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce').dt.date == d)
                    ]
                    if not dia_regs.empty:
                        status_dia = "🟢" if "1" in dia_regs['Status'].values else "🟠"
                
                tipo_btn = "primary" if d == d_sel else "secondary"
                if st.button(f"{status_dia}\n{d.day}", key=f"cal_{d}", use_container_width=True, type=tipo_btn):
                    st.session_state.data_consulta = d
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Formulário de Registo
        with st.expander(f"➕ Registar Trabalho em {st.session_state.data_consulta.strftime('%d/%m/%Y')}", expanded=(d_sel == hoje)):
            with st.form("ponto_form_elite"):
                obras_list = obras_db['Obra'].unique() if not obras_db.empty else ["Geral"]
                obra = st.selectbox(f"{ICONS['app']} Selecionar Obra", obras_list)
                frente = st.selectbox(f"{ICONS['reports']} Frente de Trabalho", TIPOS_FRENTE)
                
                c1, c2 = st.columns(2)
                h_ini = c1.time_input("Entrada", value=datetime.strptime("08:00", "%H:%M").time())
                h_fim = c2.time_input("Saída", value=datetime.strptime("17:00", "%H:%M").time())
                relat = st.text_area("📝 Relatório de Atividades")
                
                if st.form_submit_button(f"{ICONS['save']} Gravar Registo", use_container_width=True, type="primary"):
                    t1 = datetime.combine(date.today(), h_ini)
                    t2 = datetime.combine(date.today(), h_fim)
                    delta_h = round((t2 - t1).seconds / 3600, 2)
                    
                    if delta_h <= 0:
                        st.error("⚠️ Erro: A hora de saída deve ser posterior à de entrada.")
                    else:
                        new_r = pd.DataFrame([{
                            "Data": st.session_state.data_consulta.strftime("%d/%m/%Y"),
                            "Técnico": user_nome,
                            "Obra": obra,
                            "Frente": frente,
                            "Turnos": f"{h_ini.strftime('%H:%M')}-{h_fim.strftime('%H:%M')}",
                            "Horas_Total": delta_h,
                            "Relatorio": relat,
                            "Status": "0"
                        }])
                        save_db(pd.concat([registos_db, new_r]) if not registos_db.empty else new_r, "registos.csv")
                        st.success(f"{ICONS['approved']} Ponto registado com sucesso!")
                        inv()
                        st.rerun()
        
        # Visualização dos Cards do Dia Selecionado
        st.markdown(f"### Registos de {st.session_state.data_consulta.strftime('%d/%m/%Y')}")
        if not registos_db.empty:
            meus_regs = registos_db[registos_db['Técnico'] == user_nome]
            regs_dia = meus_regs[pd.to_datetime(meus_regs['Data'], dayfirst=True, errors='coerce').dt.date == st.session_state.data_consulta]
            
            if regs_dia.empty:
                st.caption("ℹ️ Nenhum registo encontrado para este dia.")
            
            for _, r in regs_dia.iterrows():
                _, st_cls = sl(r['Status'])[:2]
                st.markdown(f"""
                <div class="rp-card {st_cls.split('-')[1] if st_cls else 'pendente'}">
                    <b>{r["Obra"]}</b> | {r["Turnos"]} (<b>{fh(r["Horas_Total"])}h</b>)<br>
                    <small>{r["Frente"]}</small><br>
                    <small style="color:#94A3B8;">{r["Relatorio"][:100] if r["Relatorio"] else ""}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # =============================================================================
    # TAB 2 (CHEFE): FOLHA DE PONTO & E-SIGN
    # =============================================================================
    offset = 0
    if is_chefe:
        offset = 1
        with tabs[1]:
            st.markdown(f"### {ICONS['reports']} Assinatura e Validação Forense")
            st.caption("A assinatura abaixo será vinculada ao GPS e ao selo de autenticidade digital.")
            
            obra_f = st.selectbox(f"{ICONS['app']} Obra para Validar", 
                                  obras_db['Obra'].unique() if not obras_db.empty else ["Sem Obras"], 
                                  key="esign_obra")
            
            # Canvas para Assinatura
            canvas_sig = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=2.5,
                stroke_color="#3B82F6",
                background_color="#FFFFFF",
                height=180,
                drawing_mode="freedraw",
                key="canvas_esign"
            )
            
            nome_responsavel = st.text_input("Nome do Responsável / Cliente", placeholder="Ex: Eng. João Silva")
            
            if st.button(f"{ICONS['reports']} Gerar Folha com Selo de Segurança", use_container_width=True, type="primary"):
                if canvas_sig.image_data is not None and nome_responsavel:
                    esign_id = secrets.token_hex(6).upper()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    gps_data = st.session_state.get('last_gps', '38.7223, -9.1393')
                    
                    st.markdown(f"""
                    <div class="esign-seal">
                        <b>🔒 SELO DE SEGURANÇA GESTNOW #{esign_id}</b><br>
                        ASSINADO POR: {nome_responsavel}<br>
                        DATA/HORA: {timestamp}<br>
                        COORDENADAS: {gps_data}<br>
                        VERIFICADO POR: {user_nome} (Chefe de Equipa)
                    </div>
                    """, unsafe_allow_html=True)
                    st.success(f"{ICONS['approved']} Prova Digital de Identidade gerada com sucesso.")
                else:
                    st.warning("⚠️ Por favor, forneça a assinatura e o nome do responsável.")
    
    # =============================================================================
    # TAB HSE: SEGURANÇA
    # =============================================================================
    with tabs[1 + offset]:
        st.markdown(f"### {ICONS['safety']} Regras de Ouro")
        
        for ic, tit, des in REGRAS_OURO:
            with st.expander(f"{ic} {tit}"):
                st.write(des)
        
        st.divider()
        st.markdown(f"### {ICONS['safety']} Reportar Incidente HSE")
        
        with st.form("hse_report"):
            io = st.selectbox(f"{ICONS['app']} Obra", 
                             obras_db['Obra'].unique() if not obras_db.empty else ["Geral"])
            it = st.selectbox("Gravidade", ["Baixa", "Média", "Alta (Crítica)"])
            id_desc = st.text_area("Descrição da Ocorrência / Condição Insegura")
            
            if st.form_submit_button(f"{ICONS['safety']} Submeter Alerta HSE", use_container_width=True, type="primary"):
                ni = pd.DataFrame([{
                    "Data": date.today().strftime("%d/%m/%Y"),
                    "Utilizador": user_nome,
                    "Obra": io,
                    "Status": "Aberto",
                    "Gravidade": it,
                    "Descricao": id_desc
                }])
                save_db(pd.concat([incs_db, ni]) if not incs_db.empty else ni, "incidentes.csv")
                st.success(f"{ICONS['approved']} Alerta HSE enviado para o departamento de segurança.")
                inv()
                st.rerun()
    
    # =============================================================================
    # TAB PERFIL: INFORMAÇÕES E LOGOUT
    # =============================================================================
    with tabs[-1]:
        st.markdown(f"### {ICONS['profile']} Perfil do Colaborador")
        
        if not users.empty:
            u_data = users[users['Nome'] == user_nome]
            if not u_data.empty:
                u = u_data.iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(f"{ICONS['profile']} Cargo", u.get('Cargo', 'N/A'))
                with c2:
                    st.metric(f"{ICONS['admin']} Tipo de Acesso", st.session_state.get('tipo', 'Técnico'))
        
        st.divider()
        
        if st.button(f"{ICONS['logout']} Sair do Sistema", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core import fh, ICONS

def render_inicio(*args):
    """Dashboard Inicial - Tipo App Mobile"""
    
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db, sw_db, obs_db, equip_db,
     diags_db, diags_u_db, folhas_db, comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db) = args
    
    user_nome = st.session_state.get('user', 'Usuário')
    user_tipo = st.session_state.get('tipo', 'Técnico')
    
    # Header
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1E293B, #0F172A);
        padding: 30px 20px;
        border-radius: 20px;
        margin-bottom: 30px;
        text-align: center;
    ">
        <h1 style="margin: 0; color: #F8FAFC; font-size: 2rem;">Olá {user_nome} 👋</h1>
        <p style="margin: 10px 0 0 0; color: #94A3B8;">Bem-vindo à GestNow</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Calcular estatísticas
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)
    
    # Horas deste mês
    if not registos_db.empty:
        registos_db['Data_dt'] = pd.to_datetime(registos_db['Data'], dayfirst=True, errors='coerce')
        registos_mes = registos_db[
            (registos_db['Técnico'] == user_nome) & 
            (registos_db['Data_dt'].dt.date >= inicio_mes) &
            (registos_db['Status'] == '1')
        ]
        horas_mes = registos_mes['Horas_Total'].astype(float).sum()
    else:
        horas_mes = 0
    
    # Horas por validar
    if not registos_db.empty:
        registos_pendentes = registos_db[
            (registos_db['Técnico'] == user_nome) & 
            (registos_db['Status'] == '0')
        ]
        horas_pendentes = registos_pendentes['Horas_Total'].astype(float).sum()
    else:
        horas_pendentes = 0
    
    # Últimos 7 dias
    sete_dias_atras = hoje - timedelta(days=7)
    
    if not registos_db.empty:
        registos_7dias = registos_db[
            (registos_db['Técnico'] == user_nome) & 
            (registos_db['Data_dt'].dt.date >= sete_dias_atras) &
            (registos_db['Status'] == '1')
        ]
    else:
        registos_7dias = pd.DataFrame()
    
    # Cards de resumo (estilo mobile)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #DC2626, #B91C1C);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
        ">
            <div style="font-size: 2.5rem; margin-bottom: 10px;">⏱️</div>
            <div style="color: #F8FAFC; font-size: 0.9rem; margin-bottom: 5px;">Horas deste mês</div>
            <div style="color: #FFFFFF; font-size: 2rem; font-weight: bold;">{fh(horas_mes)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #F59E0B, #D97706);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        ">
            <div style="font-size: 2.5rem; margin-bottom: 10px;">📋</div>
            <div style="color: #F8FAFC; font-size: 0.9rem; margin-bottom: 5px;">Por validar</div>
            <div style="color: #FFFFFF; font-size: 2rem; font-weight: bold;">{fh(horas_pendentes)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    
    # ✅ BOTÕES DE NAVEGAÇÃO RÁPIDA COM AÇÃO
    st.markdown("### 📍 Navegação Rápida")
    
    col_nav1, col_nav2 = st.columns(2)
    
    with col_nav1:
        if st.button(f"{ICONS['technician']} Registar Ponto", use_container_width=True, type="primary", key="btn_nav_registar"):
            st.session_state.menu_selected = f"{ICONS['technician']} Obra"
            st.rerun()
    
    with col_nav2:
        if st.button(f"{ICONS['profile']} O Meu Perfil", use_container_width=True, type="secondary", key="btn_nav_perfil"):
            st.session_state.menu_selected = "Perfil"
            st.rerun()
    
    # Botão para ver histórico (apenas se houver registos)
    if not registos_7dias.empty:
        if st.button(f"{ICONS['dashboard']} Ver Histórico Completo", use_container_width=True, type="secondary", key="btn_nav_historico"):
            st.session_state.menu_selected = f"{ICONS['technician']} Obra"
            st.rerun()
    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # Últimos 7 dias
    st.markdown("### 📅 Últimos 7 dias")
    
    if not registos_7dias.empty:
        for _, reg in registos_7dias.iterrows():
            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.05);
                padding: 15px;
                border-radius: 12px;
                margin-bottom: 10px;
                border-left: 4px solid #10B981;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: #F8FAFC; font-weight: 600; font-size: 1.1rem;">{reg['Obra']}</div>
                        <div style="color: #94A3B8; font-size: 0.85rem; margin-top: 5px;">{reg['Data']} • {reg['Turnos']}</div>
                    </div>
                    <div style="color: #10B981; font-weight: bold; font-size: 1.2rem;">{fh(reg['Horas_Total'])}h</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.05);
            padding: 40px;
            border-radius: 15px;
            text-align: center;
        ">
            <div style="font-size: 3rem; margin-bottom: 15px;">📋</div>
            <p style="color: #94A3B8; margin: 0;">Sem registos nos últimos 7 dias</p>
            <p style="color: #64748B; font-size: 0.85rem; margin: 10px 0 0 0;">Clica em "Registar Ponto" para começar</p>
        </div>
        """, unsafe_allow_html=True)

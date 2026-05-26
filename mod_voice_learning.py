"""
GESTNOW v3 — mod_voice_learning.py
Módulo de Aprendizagem Contínua para IA com Voz
Regista interações, analisa padrões e melhora o modelo
Design System Industrial Atualizado
"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.express as px
from translations import t
from core import ICONS, COLORS

# =============================================================================
# 🗄️ ARQUIVOS DE DADOS
# =============================================================================
VOICE_LOGS_FILE = "voice_logs.csv"
VOICE_PATTERNS_FILE = "voice_patterns.json"
VOICE_FEEDBACK_FILE = "voice_feedback.csv"

# =============================================================================
# 🎨 CSS DO DASHBOARD DE APRENDIZAGEM - DESIGN SYSTEM INDUSTRIAL
# =============================================================================
_LEARNING_CSS = f"""
.learning-card {{
    background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(15,23,42,0.98));
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}}
.learning-card:hover {{
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    transform: translateY(-2px);
    border-color: {COLORS["accent"]};
}}
.metric-box {{
    text-align: center;
    padding: 20px;
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.1);
    transition: all 0.2s ease;
}}
.metric-box:hover {{
    background: rgba(255,255,255,0.08);
    transform: translateY(-2px);
}}
.metric-value {{
    font-size: 2.2rem;
    font-weight: 800;
    color: {COLORS["accent"]};
}}
.metric-label {{
    font-size: 0.85rem;
    color: {COLORS["text_secondary"]};
    margin-top: 8px;
}}
.feedback-good {{ color: {COLORS["success"]}; font-weight: 700; }}
.feedback-bad {{ color: {COLORS["error"]}; font-weight: 700; }}
.feedback-improve {{ color: {COLORS["warning"]}; font-weight: 700; }}
"""

# =============================================================================
# ⚙️ INICIALIZAÇÃO DOS ARQUIVOS DE APRENDIZAGEM
# =============================================================================
def init_voice_learning():
    """Inicializa os arquivos de aprendizagem se não existirem"""
    # Logs de comandos de voz
    if not os.path.exists(VOICE_LOGS_FILE):
        logs_df = pd.DataFrame(columns=[
            "timestamp", "user", "user_tipo", "obra", "command", 
            "command_processed", "response", "success", "processing_time_ms"
        ])
        logs_df.to_csv(VOICE_LOGS_FILE, index=False)

    # Feedback dos utilizadores
    if not os.path.exists(VOICE_FEEDBACK_FILE):
        feedback_df = pd.DataFrame(columns=[
            "timestamp", "user", "command", "feedback_type", "comment"
        ])
        feedback_df.to_csv(VOICE_FEEDBACK_FILE, index=False)

    # Padrões de comandos
    if not os.path.exists(VOICE_PATTERNS_FILE):
        patterns = {
            "command_patterns": {},
            "synonyms": {},
            "failed_commands": [],
            "learning_epochs": [],
            "last_updated": None
        }
        with open(VOICE_PATTERNS_FILE, 'w') as f:
            json.dump(patterns, f, indent=2)

# =============================================================================
# 📝 REGISTO DE COMANDOS E FEEDBACK
# =============================================================================
def log_voice_command(command, user, user_tipo, obra, response, success, processing_time_ms=0):
    """Regista um comando de voz para aprendizado"""
    init_voice_learning()

    try:
        logs_df = pd.read_csv(VOICE_LOGS_FILE)
        
        new_log = pd.DataFrame([{
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "user": user,
            "user_tipo": user_tipo,
            "obra": obra,
            "command": command,
            "command_processed": command.lower(),
            "response": response,
            "success": 1 if success else 0,
            "processing_time_ms": processing_time_ms
        }])
        
        logs_df = pd.concat([logs_df, new_log], ignore_index=True)
        logs_df.to_csv(VOICE_LOGS_FILE, index=False)
        
        # Atualizar padrões
        update_command_patterns(command, success)
        
    except Exception as e:
        print(f"Erro ao logar comando: {e}")

def register_feedback(user, command, feedback_type, comment=""):
    """Regista feedback do utilizador sobre a resposta de voz"""
    init_voice_learning()

    try:
        feedback_df = pd.read_csv(VOICE_FEEDBACK_FILE)
        
        new_feedback = pd.DataFrame([{
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "user": user,
            "command": command,
            "feedback_type": feedback_type,  # "good", "bad", "needs_improvement"
            "comment": comment
        }])
        
        feedback_df = pd.concat([feedback_df, new_feedback], ignore_index=True)
        feedback_df.to_csv(VOICE_FEEDBACK_FILE, index=False)
        
    except Exception as e:
        print(f"Erro ao registrar feedback: {e}")

def update_command_patterns(command, was_successful):
    """Atualiza os padrões de comando baseado no sucesso/falha"""
    try:
        with open(VOICE_PATTERNS_FILE, 'r') as f:
            patterns = json.load(f)
        
        command_lower = command.lower()
        
        if command_lower not in patterns["command_patterns"]:
            patterns["command_patterns"][command_lower] = {
                "count": 0,
                "success_count": 0,
                "fail_count": 0,
                "last_used": None
            }
        
        patterns["command_patterns"][command_lower]["count"] += 1
        if was_successful:
            patterns["command_patterns"][command_lower]["success_count"] += 1
        else:
            patterns["command_patterns"][command_lower]["fail_count"] += 1
            patterns["failed_commands"].append({
                "command": command_lower,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        patterns["command_patterns"][command_lower]["last_used"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        patterns["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Manter apenas últimos 100 comandos falhados
        if len(patterns["failed_commands"]) > 100:
            patterns["failed_commands"] = patterns["failed_commands"][-100:]
        
        with open(VOICE_PATTERNS_FILE, 'w') as f:
            json.dump(patterns, f, indent=2)
            
    except Exception as e:
        print(f"Erro ao atualizar padrões: {e}")

# =============================================================================
# 📊 INSIGHTS DE APRENDIZAGEM
# =============================================================================
def get_learning_insights():
    """Retorna insights sobre o aprendizado da IA"""
    init_voice_learning()

    insights = {
        "total_commands": 0,
        "success_rate": 0,
        "most_used_commands": [],
        "most_failed_commands": [],
        "commands_by_user_type": {},
        "commands_by_hour": {},
        "suggestions": []
    }

    try:
        logs_df = pd.read_csv(VOICE_LOGS_FILE)
        
        if not logs_df.empty:
            insights["total_commands"] = len(logs_df)
            insights["success_rate"] = (logs_df['success'].sum() / len(logs_df)) * 100
            
            # Comandos mais usados
            command_counts = logs_df['command_processed'].value_counts().head(10)
            insights["most_used_commands"] = command_counts.to_dict()
            
            # Comandos mais falhados
            failed_commands = logs_df[logs_df['success'] == 0]['command_processed'].value_counts().head(10)
            insights["most_failed_commands"] = failed_commands.to_dict()
            
            # Comandos por tipo de utilizador
            insights["commands_by_user_type"] = logs_df.groupby('user_tipo').size().to_dict()
            
            # Comandos por hora do dia
            logs_df['hour'] = pd.to_datetime(logs_df['timestamp']).dt.hour
            insights["commands_by_hour"] = logs_df.groupby('hour').size().to_dict()
            
            # Sugestões de melhoria
            if insights["success_rate"] < 80:
                insights["suggestions"].append(f"📊 Taxa de sucesso baixa ({insights['success_rate']:.1f}%). Considere treinar o modelo com mais exemplos.")
            
            if len(insights["most_failed_commands"]) > 0:
                top_failed = list(insights["most_failed_commands"].keys())[:3]
                insights["suggestions"].append(f"❌ Comandos mais falhados: {', '.join(top_failed)}")
            
            # Verificar se há feedback negativo
            if os.path.exists(VOICE_FEEDBACK_FILE):
                feedback_df = pd.read_csv(VOICE_FEEDBACK_FILE)
                if not feedback_df.empty:
                    bad_feedback = len(feedback_df[feedback_df['feedback_type'] == 'bad'])
                    if bad_feedback > 0:
                        insights["suggestions"].append(f"💬 {bad_feedback} feedbacks negativos registados. Reveja as respostas.")
            
    except Exception as e:
        print(f"Erro ao obter insights: {e}")

    return insights

# =============================================================================
# 🎯 DASHBOARD DE APRENDIZAGEM (APENAS ADMIN)
# =============================================================================
def render_voice_learning_dashboard():
    """Dashboard para administradores verem métricas de aprendizagem"""
    st.markdown(_LEARNING_CSS, unsafe_allow_html=True)
    
    # Header com branding industrial
    st.markdown(f"""
    <div class="learning-card">
        <div style="font-size:2rem; margin-bottom:10px;">{ICONS["voice"]}</div>
        <div style="font-size:1.5rem; font-weight:800; color:{COLORS["text_primary"]};">🧠 Aprendizagem da IA com Voz</div>
        <div style="font-size:0.95rem; color:{COLORS["text_secondary"]};">Esta página mostra como a IA está aprendendo com os comandos dos utilizadores.</div>
    </div>
    """, unsafe_allow_html=True)

    insights = get_learning_insights()

    # Métricas principais
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{insights["total_commands"]}</div>
            <div class="metric-label">{ICONS["voice"]} Total de Comandos</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        success_color = COLORS["success"] if insights["success_rate"] >= 80 else COLORS["warning"] if insights["success_rate"] >= 60 else COLORS["error"]
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color:{success_color};">{insights["success_rate"]:.1f}%</div>
            <div class="metric-label">📊 Taxa de Sucesso</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{len(insights["commands_by_user_type"])}</div>
            <div class="metric-label">👥 Utilizadores Ativos</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Gráficos
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        if insights["most_used_commands"]:
            st.markdown(f"#### {ICONS['reports']} Comandos Mais Usados")
            df_used = pd.DataFrame(list(insights["most_used_commands"].items()), 
                                   columns=['Comando', 'Frequência'])
            fig = px.bar(df_used, x='Comando', y='Frequência', title='Top 10 Comandos',
                          color='Frequência', text='Frequência',
                          color_continuous_scale=[COLORS["accent"], COLORS["accent_hover"]])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color=COLORS["text_primary"],
                height=350
            )
            st.plotly_chart(fig)
        else:
            st.info("ℹ️ Ainda sem dados suficientes")

    with col_graf2:
        if insights["commands_by_hour"]:
            st.markdown(f"#### 🕐 Horários de Uso")
            df_hour = pd.DataFrame(list(insights["commands_by_hour"].items()), 
                                   columns=['Hora', 'Comandos'])
            df_hour = df_hour.sort_values('Hora')
            fig = px.line(df_hour, x='Hora', y='Comandos', 
                          title='Atividade por Hora do Dia', markers=True,
                          color_discrete_sequence=[COLORS["accent"]])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color=COLORS["text_primary"],
                height=350
            )
            st.plotly_chart(fig)
        else:
            st.info("ℹ️ Ainda sem dados suficientes")

    # Comandos falhados
    st.divider()
    col_fail1, col_fail2 = st.columns(2)

    with col_fail1:
        if insights["most_failed_commands"]:
            st.markdown(f"#### {ICONS['error']} Comandos Mais Falhados")
            df_fail = pd.DataFrame(list(insights["most_failed_commands"].items()),
                                   columns=['Comando', 'Falhas'])
            st.dataframe(df_fail, use_container_width=True)
        else:
            st.success("✅ Nenhum comando falhado registado!")

    with col_fail2:
        if insights["suggestions"]:
            st.markdown(f"#### 💡 Sugestões de Melhoria")
            for s in insights["suggestions"]:
                if "🔴" in s or "❌" in s:
                    st.error(s)
                elif "📊" in s:
                    st.warning(s)
                else:
                    st.info(s)
        else:
            st.success("🎉 Tudo ótimo! A IA está aprendendo bem.")

    # Feedbacks dos utilizadores
    st.divider()
    st.markdown(f"#### 📝 Feedback dos Utilizadores")

    try:
        if os.path.exists(VOICE_FEEDBACK_FILE):
            feedback_df = pd.read_csv(VOICE_FEEDBACK_FILE)
            if not feedback_df.empty:
                feedback_df = feedback_df.sort_values('timestamp', ascending=False).head(20)
                st.dataframe(feedback_df, use_container_width=True)
            else:
                st.info("ℹ️ Nenhum feedback registado ainda.")
        else:
            st.info("ℹ️ Nenhum feedback registado ainda.")
    except Exception as e:
        st.info("ℹ️ Nenhum feedback registado ainda.")

# =============================================================================
# 👍 WIDGET DE FEEDBACK (PARA USAR APÓS RESPOSTA)
# =============================================================================
def render_voice_feedback_widget(command):
    """Widget para coletar feedback do utilizador sobre a resposta"""
    st.divider()
    st.markdown(f"#### 👍 Esta resposta foi útil?")

    col_fb1, col_fb2, col_fb3 = st.columns(3)
    with col_fb1:
        if st.button("✅ Sim, boa resposta", use_container_width=True, key="fb_good"):
            register_feedback(
                user=st.session_state.get('user', ''),
                command=command,
                feedback_type="good",
                comment="Resposta útil"
            )
            st.success("Obrigado pelo feedback! Isso ajuda a IA a melhorar.")
            st.rerun()

    with col_fb2:
        if st.button("⚠️ Podia ser melhor", use_container_width=True, key="fb_improve"):
            with st.popover("O que podia ser melhor?"):
                comentario = st.text_area("Sugestão:", key="fb_comment_improve")
                if st.button("Enviar feedback"):
                    if comentario:
                        register_feedback(
                            user=st.session_state.get('user', ''),
                            command=command,
                            feedback_type="needs_improvement",
                            comment=comentario
                        )
                        st.success("Feedback registado! Obrigado pela ajuda.")
                        st.rerun()

    with col_fb3:
        if st.button("❌ Resposta errada", use_container_width=True, key="fb_bad"):
            with st.popover("Qual era a resposta esperada?"):
                comentario = st.text_area("Resposta esperada:", key="fb_comment_bad")
                if st.button("Enviar feedback"):
                    if comentario:
                        register_feedback(
                            user=st.session_state.get('user', ''),
                            command=command,
                            feedback_type="bad",
                            comment=comentario
                        )
                        st.success("Feedback registado! Vamos melhorar este comando.")
                        st.rerun()

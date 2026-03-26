"""
GESTNOW v3 — mod_voice_learning.py
Módulo de Aprendizagem Contínua para IA com Voz
Registra interações, analisa padrões e melhora o modelo
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.express as px

# =========================================================
# ARQUIVOS DE DADOS
# =========================================================

VOICE_LOGS_FILE = "voice_logs.csv"
VOICE_PATTERNS_FILE = "voice_patterns.json"
VOICE_FEEDBACK_FILE = "voice_feedback.csv"


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


def log_voice_command(command, user, user_tipo, obra, response, success, processing_time_ms=0):
    """Registra um comando de voz para aprendizado"""
    
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
    """Registra feedback do utilizador sobre a resposta de voz"""
    
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
                insights["suggestions"].append("📊 Taxa de sucesso baixa. Considere treinar o modelo com mais exemplos.")
            
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


# =========================================================
# DASHBOARD DE APRENDIZAGEM (APENAS ADMIN)
# =========================================================

def render_voice_learning_dashboard():
    """Dashboard para administradores verem métricas de aprendizagem"""
    
    st.markdown("### 🧠 Aprendizagem da IA com Voz")
    st.caption("Esta página mostra como a IA está aprendendo com os comandos dos utilizadores.")
    
    insights = get_learning_insights()
    
    # Métricas principais
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎤 Total de Comandos", insights["total_commands"])
    with col2:
        success_color = "normal"
        if insights["success_rate"] < 70:
            success_color = "inverse"
        st.metric("📊 Taxa de Sucesso", f"{insights['success_rate']:.1f}%", delta=None, delta_color=success_color)
    with col3:
        st.metric("👥 Utilizadores Ativos", len(insights["commands_by_user_type"]))
    
    st.markdown("---")
    
    # Gráficos
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        if insights["most_used_commands"]:
            st.markdown("#### 📊 Comandos Mais Usados")
            df_used = pd.DataFrame(list(insights["most_used_commands"].items()), 
                                   columns=['Comando', 'Frequência'])
            fig = px.bar(df_used, x='Comando', y='Frequência', title='Top 10 Comandos',
                         color='Frequência', text='Frequência')
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ainda sem dados suficientes")
    
    with col_graf2:
        if insights["commands_by_hour"]:
            st.markdown("#### 🕐 Horários de Uso")
            df_hour = pd.DataFrame(list(insights["commands_by_hour"].items()), 
                                   columns=['Hora', 'Comandos'])
            df_hour = df_hour.sort_values('Hora')
            fig = px.line(df_hour, x='Hora', y='Comandos', 
                         title='Atividade por Hora do Dia', markers=True)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ainda sem dados suficientes")
    
    # Comandos falhados
    st.markdown("---")
    col_fail1, col_fail2 = st.columns(2)
    
    with col_fail1:
        if insights["most_failed_commands"]:
            st.markdown("#### ❌ Comandos Mais Falhados")
            df_fail = pd.DataFrame(list(insights["most_failed_commands"].items()),
                                   columns=['Comando', 'Falhas'])
            st.dataframe(df_fail, use_container_width=True)
        else:
            st.info("✅ Nenhum comando falhado registado!")
    
    with col_fail2:
        if insights["suggestions"]:
            st.markdown("#### 💡 Sugestões de Melhoria")
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
    st.markdown("---")
    st.markdown("#### 📝 Feedback dos Utilizadores")
    
    try:
        if os.path.exists(VOICE_FEEDBACK_FILE):
            feedback_df = pd.read_csv(VOICE_FEEDBACK_FILE)
            if not feedback_df.empty:
                feedback_df = feedback_df.sort_values('timestamp', ascending=False).head(20)
                st.dataframe(feedback_df, use_container_width=True)
            else:
                st.info("Nenhum feedback registado ainda.")
        else:
            st.info("Nenhum feedback registado ainda.")
    except Exception as e:
        st.info("Nenhum feedback registado ainda.")


# =========================================================
# WIDGET DE FEEDBACK (PARA USAR APÓS RESPOSTA)
# =========================================================

def render_voice_feedback_widget(command):
    """Widget para coletar feedback do utilizador sobre a resposta"""
    
    st.markdown("---")
    st.markdown("#### 👍 Esta resposta foi útil?")
    
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

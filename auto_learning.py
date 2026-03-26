"""
GESTNOW v3 — auto_learning.py
Sistema de Auto-Aprendizagem e Deploy Automático
Executado automaticamente pelo GitHub Actions
"""

import pandas as pd
import json
import os
import sys
from datetime import datetime
import subprocess

# =========================================================
# CONFIGURAÇÕES
# =========================================================

VOICE_LOGS_FILE = "voice_logs.csv"
VOICE_PATTERNS_FILE = "voice_patterns.json"
VOICE_FEEDBACK_FILE = "voice_feedback.csv"
LEARNING_REPORT_FILE = "learning_report.json"


def analyze_and_improve():
    """Função principal que analisa e gera melhorias automaticamente"""
    
    print("=" * 60)
    print("🤖 GESTNOW - Auto-Aprendizagem Iniciada")
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Verificar se há logs
    if not os.path.exists(VOICE_LOGS_FILE):
        print("⚠️ Nenhum log de voz encontrado. Aprendizagem cancelada.")
        return None
    
    # 2. Carregar logs
    try:
        logs = pd.read_csv(VOICE_LOGS_FILE)
        if logs.empty:
            print("⚠️ Logs vazios. Aprendizagem cancelada.")
            return None
        print(f"📊 Total de comandos analisados: {len(logs)}")
    except Exception as e:
        print(f"❌ Erro ao carregar logs: {e}")
        return None
    
    # 3. Analisar taxa de sucesso
    total_commands = len(logs)
    success_count = logs['success'].sum() if 'success' in logs.columns else 0
    success_rate = (success_count / total_commands) * 100 if total_commands > 0 else 0
    
    print(f"📈 Taxa de sucesso: {success_rate:.1f}% ({success_count}/{total_commands})")
    
    # 4. Identificar comandos problemáticos
    if 'command_processed' in logs.columns:
        failed_commands = logs[logs['success'] == 0] if 'success' in logs.columns else pd.DataFrame()
        if not failed_commands.empty:
            top_failed = failed_commands['command_processed'].value_counts().head(10)
            print(f"❌ Comandos mais falhados:")
            for cmd, count in top_failed.items():
                print(f"   - '{cmd}': {count} falhas")
    
    # 5. Carregar padrões existentes
    patterns = {}
    if os.path.exists(VOICE_PATTERNS_FILE):
        try:
            with open(VOICE_PATTERNS_FILE, 'r') as f:
                patterns = json.load(f)
        except:
            patterns = {"command_patterns": {}, "synonyms": {}, "failed_commands": []}
    
    # 6. Gerar recomendações
    recommendations = []
    
    if success_rate < 70:
        recommendations.append({
            "type": "critical",
            "message": f"Taxa de sucesso crítica ({success_rate:.1f}%). Necessário treinar modelo com urgência.",
            "action": "retrain_model"
        })
    elif success_rate < 85:
        recommendations.append({
            "type": "warning",
            "message": f"Taxa de sucesso moderada ({success_rate:.1f}%). Recomenda-se melhoria.",
            "action": "improve_patterns"
        })
    else:
        recommendations.append({
            "type": "success",
            "message": f"Taxa de sucesso excelente ({success_rate:.1f}%). Parabéns!",
            "action": "none"
        })
    
    # 7. Identificar novos padrões
    known_patterns = set(patterns.get("command_patterns", {}).keys())
    all_commands = set(logs['command_processed'].unique()) if 'command_processed' in logs.columns else set()
    new_commands = all_commands - known_patterns
    
    if new_commands:
        print(f"🆕 Novos comandos identificados: {len(new_commands)}")
        recommendations.append({
            "type": "info",
            "message": f"{len(new_commands)} novos comandos identificados. Adicione ao modelo.",
            "action": "add_patterns",
            "new_commands": list(new_commands)[:20]
        })
    
    # 8. Verificar feedback negativo
    if os.path.exists(VOICE_FEEDBACK_FILE):
        try:
            feedback = pd.read_csv(VOICE_FEEDBACK_FILE)
            if not feedback.empty:
                bad_feedback = feedback[feedback['feedback_type'] == 'bad']
                if not bad_feedback.empty:
                    print(f"💬 Feedback negativo: {len(bad_feedback)} registos")
                    recommendations.append({
                        "type": "warning",
                        "message": f"{len(bad_feedback)} feedbacks negativos. Reveja as respostas.",
                        "action": "review_feedback",
                        "feedback": bad_feedback.head(5).to_dict('records')
                    })
        except:
            pass
    
    # 9. Gerar relatório
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_commands": total_commands,
        "success_rate": success_rate,
        "success_count": success_count,
        "fail_count": total_commands - success_count,
        "unique_users": logs['user'].nunique() if 'user' in logs.columns else 0,
        "recommendations": recommendations,
        "top_failed_commands": dict(top_failed.head(10)) if 'top_failed' in locals() else {},
        "new_commands_identified": list(new_commands) if new_commands else [],
        "should_deploy": success_rate < 70 or len(new_commands) > 10
    }
    
    # 10. Salvar relatório
    try:
        with open(LEARNING_REPORT_FILE, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📄 Relatório salvo em: {LEARNING_REPORT_FILE}")
    except Exception as e:
        print(f"❌ Erro ao salvar relatório: {e}")
    
    # 11. Exibir resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DA APRENDIZAGEM")
    print("=" * 60)
    print(f"✅ Total de comandos: {total_commands}")
    print(f"📈 Taxa de sucesso: {success_rate:.1f}%")
    print(f"👥 Utilizadores únicos: {report['unique_users']}")
    print(f"🆕 Novos comandos: {len(new_commands)}")
    print(f"🚀 Deploy automático recomendado: {'SIM' if report['should_deploy'] else 'NÃO'}")
    
    if recommendations:
        print("\n💡 RECOMENDAÇÕES:")
        for rec in recommendations:
            emoji = "🔴" if rec['type'] == 'critical' else "🟡" if rec['type'] == 'warning' else "🟢"
            print(f"   {emoji} {rec['message']}")
    
    print("=" * 60)
    
    return report


def trigger_auto_deploy():
    """Dispara deploy automático se houver melhorias significativas"""
    
    if not os.path.exists(LEARNING_REPORT_FILE):
        print("⚠️ Nenhum relatório encontrado. Deploy cancelado.")
        return False
    
    try:
        with open(LEARNING_REPORT_FILE, 'r') as f:
            report = json.load(f)
        
        if report.get("should_deploy", False):
            print("🚀 Iniciando deploy automático...")
            
            # Tentar deploy via gcloud (se disponível no ambiente)
            try:
                result = subprocess.run(
                    ["gcloud", "run", "deploy", "gestnow-app", 
                     "--source", ".", 
                     "--platform", "managed", 
                     "--region", "europe-west1",
                     "--allow-unauthenticated",
                     "--quiet"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    print("✅ Deploy automático concluído com sucesso!")
                    return True
                else:
                    print(f"❌ Erro no deploy: {result.stderr}")
                    return False
                    
            except FileNotFoundError:
                print("⚠️ gcloud não encontrado. Deploy automático não disponível neste ambiente.")
                return False
            except Exception as e:
                print(f"❌ Erro durante deploy: {e}")
                return False
        else:
            print("✅ Nenhuma melhoria significativa detectada. Deploy não necessário.")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao ler relatório: {e}")
        return False


def generate_training_data():
    """Gera dados de treino para o modelo de voz"""
    
    if not os.path.exists(VOICE_LOGS_FILE):
        print("⚠️ Nenhum log encontrado.")
        return None
    
    try:
        logs = pd.read_csv(VOICE_LOGS_FILE)
        if logs.empty:
            return None
        
        # Gerar dados de treino
        training_data = []
        
        # Comandos bem-sucedidos (positivos)
        success_commands = logs[logs['success'] == 1] if 'success' in logs.columns else pd.DataFrame()
        for _, row in success_commands.iterrows():
            training_data.append({
                "command": row.get('command', ''),
                "command_processed": row.get('command_processed', ''),
                "user_tipo": row.get('user_tipo', ''),
                "success": True
            })
        
        # Comandos falhados (negativos - para aprendizado)
        failed_commands = logs[logs['success'] == 0] if 'success' in logs.columns else pd.DataFrame()
        for _, row in failed_commands.iterrows():
            training_data.append({
                "command": row.get('command', ''),
                "command_processed": row.get('command_processed', ''),
                "user_tipo": row.get('user_tipo', ''),
                "success": False
            })
        
        # Salvar dados de treino
        training_file = "training_data.json"
        with open(training_file, 'w') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)
        
        print(f"📚 Dados de treino gerados: {len(training_data)} exemplos")
        return training_data
        
    except Exception as e:
        print(f"❌ Erro ao gerar dados de treino: {e}")
        return None


def cleanup_old_data(days=30):
    """Limpa dados antigos para manter apenas registos recentes"""
    
    try:
        if os.path.exists(VOICE_LOGS_FILE):
            logs = pd.read_csv(VOICE_LOGS_FILE)
            if not logs.empty and 'timestamp' in logs.columns:
                cutoff = datetime.now() - timedelta(days=days)
                logs['timestamp_dt'] = pd.to_datetime(logs['timestamp'])
                logs_recent = logs[logs['timestamp_dt'] > cutoff]
                logs_recent.to_csv(VOICE_LOGS_FILE, index=False)
                print(f"🧹 Limpeza de dados: {len(logs) - len(logs_recent)} registos antigos removidos")
        
        if os.path.exists(VOICE_FEEDBACK_FILE):
            feedback = pd.read_csv(VOICE_FEEDBACK_FILE)
            if not feedback.empty and 'timestamp' in feedback.columns:
                cutoff = datetime.now() - timedelta(days=days)
                feedback['timestamp_dt'] = pd.to_datetime(feedback['timestamp'])
                feedback_recent = feedback[feedback['timestamp_dt'] > cutoff]
                feedback_recent.to_csv(VOICE_FEEDBACK_FILE, index=False)
                print(f"🧹 Limpeza de feedback: {len(feedback) - len(feedback_recent)} registos antigos removidos")
                
    except Exception as e:
        print(f"⚠️ Erro durante limpeza: {e}")


# =========================================================
# MAIN - EXECUTADO PELO GITHUB ACTIONS
# =========================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🤖 GESTNOW - Auto-Learning Pipeline")
    print("=" * 60 + "\n")
    
    # 1. Limpar dados antigos (últimos 30 dias)
    cleanup_old_data(days=30)
    
    # 2. Analisar e gerar melhorias
    report = analyze_and_improve()
    
    # 3. Gerar dados de treino
    if report and report.get("total_commands", 0) > 0:
        generate_training_data()
    
    # 4. Verificar se deploy automático é necessário
    if report and report.get("should_deploy", False):
        print("\n🚀 Iniciando deploy automático...")
        trigger_auto_deploy()
    else:
        print("\n✅ Pipeline concluído sem necessidade de deploy.")
    
    print("\n" + "=" * 60)
    print("🏁 Auto-Learning Pipeline Concluído")
    print("=" * 60)

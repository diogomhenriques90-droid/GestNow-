"""
GESTNOW v3 — auto_learning.py
Sistema de Auto-Aprendizagem e Deploy Automático
Executado automaticamente pelo GitHub Actions
Design System Industrial Atualizado
"""
import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta
import subprocess

# =============================================================================
# 🗄️ ARQUIVOS DE DADOS
# =============================================================================
VOICE_LOGS_FILE = "voice_logs.csv"
VOICE_PATTERNS_FILE = "voice_patterns.json"
VOICE_FEEDBACK_FILE = "voice_feedback.csv"
LEARNING_REPORT_FILE = "learning_report.json"
TRAINING_DATA_FILE = "training_data.json"

# =============================================================================
# 🎨 CORES DO DESIGN SYSTEM INDUSTRIAL (Para logs coloridos)
# =============================================================================
class Colors:
    """Cores ANSI para logs no terminal"""
    RESET = "\033[0m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"

def print_header(text):
    """Imprime cabeçalho formatado"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}🤖 GESTNOW - {text}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️ {text}{Colors.RESET}")

# =============================================================================
# ⚙️ FUNÇÃO PRINCIPAL DE ANÁLISE
# =============================================================================
def analyze_and_improve():
    """Função principal que analisa e gera melhorias automaticamente"""
    print_header("Auto-Aprendizagem Iniciada")
    
    print_info(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Verificar se há logs
    if not os.path.exists(VOICE_LOGS_FILE):
        print_warning("Nenhum log de voz encontrado. Aprendizagem cancelada.")
        return None
    
    # 2. Carregar logs
    try:
        logs = pd.read_csv(VOICE_LOGS_FILE)
        if logs.empty:
            print_warning("Logs vazios. Aprendizagem cancelada.")
            return None
        print_success(f"Total de comandos analisados: {len(logs)}")
    except Exception as e:
        print_error(f"Erro ao carregar logs: {e}")
        return None
    
    # 3. Analisar taxa de sucesso
    total_commands = len(logs)
    success_count = logs['success'].sum() if 'success' in logs.columns else 0
    success_rate = (success_count / total_commands) * 100 if total_commands > 0 else 0
    
    print_info(f"Taxa de sucesso: {success_rate:.1f}% ({success_count}/{total_commands})")
    
    # 4. Identificar comandos problemáticos
    top_failed = {}
    if 'command_processed' in logs.columns:
        failed_commands = logs[logs['success'] == 0] if 'success' in logs.columns else pd.DataFrame()
        if not failed_commands.empty:
            top_failed = failed_commands['command_processed'].value_counts().head(10)
            print_error("Comandos mais falhados:")
            for cmd, count in top_failed.items():
                print(f"   - '{cmd}': {count} falhas")
    
    # 5. Carregar padrões existentes
    patterns = {}
    if os.path.exists(VOICE_PATTERNS_FILE):
        try:
            with open(VOICE_PATTERNS_FILE, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
        except:
            patterns = {
                "command_patterns": {},
                "synonyms": {},
                "failed_commands": []
            }
    
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
        print_info(f"Novos comandos identificados: {len(new_commands)}")
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
                    print_warning(f"Feedback negativo: {len(bad_feedback)} registos")
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
        "top_failed_commands": dict(top_failed.head(10)) if len(top_failed) > 0 else {},
        "new_commands_identified": list(new_commands) if new_commands else [],
        "should_deploy": success_rate < 70 or len(new_commands) > 10
    }
    
    # 10. Salvar relatório
    try:
        with open(LEARNING_REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print_success(f"Relatório salvo em: {LEARNING_REPORT_FILE}")
    except Exception as e:
        print_error(f"Erro ao salvar relatório: {e}")
    
    # 11. Exibir resumo
    print_header("RESUMO DA APRENDIZAGEM")
    print_success(f"Total de comandos: {total_commands}")
    print_info(f"Taxa de sucesso: {success_rate:.1f}%")
    print_info(f"Utilizadores únicos: {report['unique_users']}")
    print_info(f"Novos comandos: {len(new_commands)}")
    
    deploy_status = "SIM" if report['should_deploy'] else "NÃO"
    print_info(f"Deploy automático recomendado: {deploy_status}")
    
    if recommendations:
        print_header("RECOMENDAÇÕES")
        for rec in recommendations:
            emoji = "🔴" if rec['type'] == 'critical' else "🟡" if rec['type'] == 'warning' else "🟢"
            print(f"   {emoji} {rec['message']}")
    
    print_header("FIM DA ANÁLISE")
    
    return report

# =============================================================================
# 🚀 TRIGGER DE DEPLOY AUTOMÁTICO
# =============================================================================
def trigger_auto_deploy():
    """Dispara deploy automático se houver melhorias significativas"""
    if not os.path.exists(LEARNING_REPORT_FILE):
        print_warning("Nenhum relatório encontrado. Deploy cancelado.")
        return False
    
    try:
        with open(LEARNING_REPORT_FILE, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        if report.get("should_deploy", False):
            print_header("Deploy Automático Iniciado")
            
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
                    print_success("Deploy automático concluído com sucesso!")
                    return True
                else:
                    print_error(f"Erro no deploy: {result.stderr}")
                    return False
                    
            except FileNotFoundError:
                print_warning("gcloud não encontrado. Deploy automático não disponível neste ambiente.")
                return False
            except Exception as e:
                print_error(f"Erro durante deploy: {e}")
                return False
        else:
            print_success("Nenhuma melhoria significativa detectada. Deploy não necessário.")
            return False
            
    except Exception as e:
        print_error(f"Erro ao ler relatório: {e}")
        return False

# =============================================================================
# 📚 GERAR DADOS DE TREINO
# =============================================================================
def generate_training_data():
    """Gera dados de treino para o modelo de voz"""
    if not os.path.exists(VOICE_LOGS_FILE):
        print_warning("Nenhum log encontrado.")
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
        with open(TRAINING_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)
        
        print_success(f"Dados de treino gerados: {len(training_data)} exemplos")
        return training_data
        
    except Exception as e:
        print_error(f"Erro ao gerar dados de treino: {e}")
        return None

# =============================================================================
# 🧹 LIMPEZA DE DADOS ANTIGOS
# =============================================================================
def cleanup_old_data(days=30):
    """Limpa dados antigos para manter apenas registos recentes"""
    try:
        if os.path.exists(VOICE_LOGS_FILE):
            logs = pd.read_csv(VOICE_LOGS_FILE)
            if not logs.empty and 'timestamp' in logs.columns:
                cutoff = datetime.now() - timedelta(days=days)
                logs['timestamp_dt'] = pd.to_datetime(logs['timestamp'])
                logs_recent = logs[logs['timestamp_dt'] > cutoff]
                removed_count = len(logs) - len(logs_recent)
                logs_recent.to_csv(VOICE_LOGS_FILE, index=False)
                if removed_count > 0:
                    print_info(f"Limpeza de dados: {removed_count} registos antigos removidos")
        
        if os.path.exists(VOICE_FEEDBACK_FILE):
            feedback = pd.read_csv(VOICE_FEEDBACK_FILE)
            if not feedback.empty and 'timestamp' in feedback.columns:
                cutoff = datetime.now() - timedelta(days=days)
                feedback['timestamp_dt'] = pd.to_datetime(feedback['timestamp'])
                feedback_recent = feedback[feedback['timestamp_dt'] > cutoff]
                removed_count = len(feedback) - len(feedback_recent)
                feedback_recent.to_csv(VOICE_FEEDBACK_FILE, index=False)
                if removed_count > 0:
                    print_info(f"Limpeza de feedback: {removed_count} registos antigos removidos")
            
    except Exception as e:
        print_warning(f"Erro durante limpeza: {e}")

# =============================================================================
# 🏁 MAIN - EXECUTADO PELO GITHUB ACTIONS
# =============================================================================
if __name__ == "__main__":
    print_header("Auto-Learning Pipeline")
    
    # 1. Limpar dados antigos (últimos 30 dias)
    cleanup_old_data(days=30)
    
    # 2. Analisar e gerar melhorias
    report = analyze_and_improve()
    
    # 3. Gerar dados de treino
    if report and report.get("total_commands", 0) > 0:
        generate_training_data()
    
    # 4. Verificar se deploy automático é necessário
    if report and report.get("should_deploy", False):
        print_header("Deploy Automático")
        trigger_auto_deploy()
    else:
        print_success("Pipeline concluído sem necessidade de deploy.")
    
    print_header("Auto-Learning Pipeline Concluído")

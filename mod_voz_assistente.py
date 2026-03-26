"""
GESTNOW v3 — mod_voz_assistente.py
Assistente de Voz Global com resposta falada
Funciona em toda a aplicação
"""

import streamlit as st
import pandas as pd
import base64
import re
from datetime import datetime
from translations import t

# CSS para o botão flutuante de voz
_VOZ_CSS = """
<style>
.voice-assistant {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 999;
    background: linear-gradient(135deg, #0A2463, #3E92CC);
    border-radius: 50%;
    width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    transition: all 0.3s ease;
}
.voice-assistant:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 16px rgba(0,0,0,0.4);
}
.voice-assistant.listening {
    background: linear-gradient(135deg, #EF4444, #F59E0B);
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.1); }
    100% { transform: scale(1); }
}
.voice-response {
    position: fixed;
    bottom: 100px;
    right: 20px;
    background: white;
    border-radius: 12px;
    padding: 12px 16px;
    max-width: 300px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    border-left: 4px solid #0A2463;
    z-index: 998;
    font-size: 14px;
    animation: slideIn 0.3s ease;
}
@keyframes slideIn {
    from { opacity: 0; transform: translateX(50px); }
    to { opacity: 1; transform: translateX(0); }
}
</style>
"""

# Mapeamento de status para português (usado nos comandos de voz)
STATUS_VOZ = {
    "0": "Pendente",
    "1": "Material OK",
    "2": "Calibrado",
    "3": "Instalado",
    "4": "Concluído",
}

STATUS_ICON = {
    "0": "⏳",
    "1": "📦",
    "2": "🔬",
    "3": "🏗️",
    "4": "✅",
}


def render_voice_assistant_global(user_tipo, user_nome, obra_sel=None, insts=None, 
                                   itr_a=None, itr_b=None, punch=None):
    """
    Renderiza o assistente de voz global (botão flutuante)
    Funciona em toda a aplicação
    """
    
    st.markdown(_VOZ_CSS, unsafe_allow_html=True)
    
    # Componente HTML/JS para reconhecimento de voz e resposta falada
    voice_html = """
    <div id="voice-assistant-container">
        <div id="voice-assistant-btn" class="voice-assistant" onclick="startListening()">
            🎤
        </div>
        <div id="voice-response" style="display: none;"></div>
    </div>
    
    <script>
    let isListening = false;
    let recognition = null;
    const btn = document.getElementById('voice-assistant-btn');
    const responseDiv = document.getElementById('voice-response');
    
    function showResponse(text, isError = false) {
        responseDiv.style.display = 'block';
        responseDiv.className = 'voice-response';
        responseDiv.innerHTML = text;
        responseDiv.style.borderLeftColor = isError ? '#EF4444' : '#10B981';
        
        // Falar a resposta
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'pt-PT';
            utterance.rate = 0.9;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }
        
        setTimeout(() => {
            responseDiv.style.display = 'none';
        }, 5000);
    }
    
    function startListening() {
        if (isListening) return;
        
        if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
            showResponse('⚠️ Reconhecimento de voz não suportado neste navegador.', true);
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = 'pt-PT';
        recognition.continuous = false;
        recognition.interimResults = false;
        
        btn.classList.add('listening');
        btn.innerHTML = '🔴';
        isListening = true;
        showResponse('🎤 Ouvindo... Fale agora', false);
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            btn.classList.remove('listening');
            btn.innerHTML = '🎤';
            isListening = false;
            showResponse('✅ Comando: "' + transcript + '"', false);
            
            // Enviar comando para o Streamlit via query params
            const url = new URL(window.location.href);
            url.searchParams.set('voice_command', transcript);
            window.history.replaceState({}, '', url);
            window.location.reload();
        };
        
        recognition.onerror = function(event) {
            btn.classList.remove('listening');
            btn.innerHTML = '🎤';
            isListening = false;
            showResponse('❌ Erro: ' + event.error, true);
        };
        
        recognition.onend = function() {
            btn.classList.remove('listening');
            btn.innerHTML = '🎤';
            isListening = false;
        };
        
        recognition.start();
    }
    </script>
    """
    
    st.components.v1.html(voice_html, height=0)
    
    # Processar comando de voz recebido
    voice_command = st.query_params.get("voice_command", "")
    
    if voice_command:
        resposta = _processar_comando_voz(
            voice_command, user_tipo, user_nome, obra_sel, 
            insts, itr_a, itr_b, punch
        )
        
        # Mostrar resposta na tela
        st.info(f"🎤 **Comando:** {voice_command}\n\n📢 **Resposta:** {resposta}")
        
        # Injetar script para falar a resposta
        speak_script = f"""
        <script>
        (function() {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                var utterance = new SpeechSynthesisUtterance("{resposta.replace('"', '\\"')}");
                utterance.lang = 'pt-PT';
                utterance.rate = 0.9;
                utterance.pitch = 1.0;
                window.speechSynthesis.speak(utterance);
            }}
        }})();
        </script>
        """
        st.components.v1.html(speak_script, height=0)
        
        # Limpar query param para não repetir
        st.query_params.clear()
        
        return resposta
    
    return None


def _processar_comando_voz(comando, user_tipo, user_nome, obra_sel, insts, itr_a, itr_b, punch):
    """Processa o comando de voz e retorna a resposta"""
    
    comando_lower = comando.lower()
    
    # =========================================================
    # COMANDOS GLOBAIS
    # =========================================================
    
    if "que horas são" in comando_lower or "que horas sao" in comando_lower:
        agora = datetime.now().strftime('%H:%M')
        return f"São {agora} horas."
    
    if "que dia é hoje" in comando_lower:
        hoje = datetime.now().strftime('%d de %B de %Y')
        return f"Hoje é {hoje}."
    
    if "ajuda" in comando_lower or "comandos" in comando_lower:
        return _get_comandos_ajuda(user_tipo)
    
    if "obra atual" in comando_lower or "obra selecionada" in comando_lower:
        if obra_sel:
            return f"Obra atual: {obra_sel}."
        return "Nenhuma obra selecionada."
    
    if "meu nome" in comando_lower:
        return f"Olá {user_nome}, você está logado como {user_tipo}."
    
    # =========================================================
    # COMANDOS DE INSTRUMENTOS
    # =========================================================
    
    if insts is not None and not insts.empty:
        
        if "total de instrumentos" in comando_lower or "quantos instrumentos" in comando_lower:
            total = len(insts)
            return f"Total de {total} instrumentos cadastrados."
        
        if "material ok" in comando_lower or "material recebido" in comando_lower:
            material_ok = len(insts[insts['Status'].isin(['1','2','3','4'])])
            return f"{material_ok} instrumentos com material OK."
        
        if "calibrados" in comando_lower:
            calibrados = len(insts[insts['Status'].isin(['2','3','4'])])
            return f"{calibrados} instrumentos calibrados."
        
        if "instalados" in comando_lower:
            instalados = len(insts[insts['Status'].isin(['3','4'])])
            return f"{instalados} instrumentos instalados."
        
        if "pendentes" in comando_lower:
            pendentes = len(insts[insts['Status'] == '0'])
            return f"{pendentes} instrumentos pendentes."
        
        # Buscar instrumento específico por tag
        tag_match = re.search(r'([A-Z]{2,3}-\d+[A-Z]?)', comando.upper())
        if tag_match:
            tag = tag_match.group(1)
            inst = insts[insts['Tag'] == tag]
            if not inst.empty:
                inst_row = inst.iloc[0]
                status_code = str(inst_row.get('Status', '0'))
                status_text = STATUS_VOZ.get(status_code, "Desconhecido")
                
                if "mostrar" in comando_lower or "informações" in comando_lower:
                    return f"Instrumento {tag}: {inst_row.get('Descricao', '')}. Status: {status_text}."
                
                if "localização" in comando_lower or "gps" in comando_lower:
                    lat = inst_row.get('GPS_Lat', '')
                    lng = inst_row.get('GPS_Lng', '')
                    if lat and lat not in ('', 'nan'):
                        return f"Localização de {tag}: latitude {lat}, longitude {lng}."
                    return f"{tag} ainda não tem localização GPS registada."
                
                if "status" in comando_lower:
                    return f"Status de {tag}: {status_text}."
                
                if "foto" in comando_lower:
                    if inst_row.get('Foto_Local_b64') and inst_row.get('Foto_Local_b64') != '':
                        return f"{tag} tem foto disponível."
                    return f"{tag} não tem foto disponível."
        
        # Próximo instrumento pendente
        if "próximo" in comando_lower or "proximo" in comando_lower:
            pendentes = insts[insts['Status'] == '0']
            if not pendentes.empty:
                next_inst = pendentes.iloc[0]
                return f"Próximo instrumento pendente: {next_inst['Tag']} - {next_inst.get('Descricao', '')}."
            return "Todos os instrumentos estão concluídos! Parabéns!"
        
        # Progresso da obra
        if "progresso" in comando_lower or "resumo" in comando_lower:
            total = len(insts)
            material = len(insts[insts['Status'].isin(['1','2','3','4'])])
            calibrados = len(insts[insts['Status'].isin(['2','3','4'])])
            instalados = len(insts[insts['Status'].isin(['3','4'])])
            pct_mat = int(material/total*100) if total > 0 else 0
            pct_cal = int(calibrados/total*100) if total > 0 else 0
            pct_inst = int(instalados/total*100) if total > 0 else 0
            return f"Progresso da obra: Material {pct_mat} por cento, Calibração {pct_cal} por cento, Instalação {pct_inst} por cento."
    
    # =========================================================
    # COMANDOS PARA ADMIN/CHEFE
    # =========================================================
    
    if user_tipo in ['Admin', 'Chefe de Equipa']:
        
        if "punch" in comando_lower:
            if punch is not None and not punch.empty:
                abertos = len(punch[punch['Status'] == 'Aberto'])
                cat_a = len(punch[(punch['Categoria'] == 'A') & (punch['Status'] == 'Aberto')])
                return f"{abertos} Punch Items abertos, sendo {cat_a} de categoria A crítica."
            return "Não há Punch Items registados."
        
        if "calibração pendente" in comando_lower or "calibracao pendente" in comando_lower:
            if itr_a is not None:
                calibrados = len(itr_a)
                total_cal = len(insts[insts['Status'].isin(['1','2','3','4'])]) if insts is not None else 0
                pendentes_cal = total_cal - calibrados
                return f"{pendentes_cal} instrumentos aguardam calibração."
        
        if "material em falta" in comando_lower:
            if insts is not None:
                sem_material = len(insts[insts['Status'] == '0'])
                return f"{sem_material} instrumentos aguardam material."
    
    # =========================================================
    # COMANDOS PARA TÉCNICOS
    # =========================================================
    
    if user_tipo in ['Técnico', 'Instrumentista']:
        
        if "minhas calibrações" in comando_lower or "minhas calibracoes" in comando_lower:
            if itr_a is not None and not itr_a.empty:
                minhas = len(itr_a[itr_a['Instrumentista'] == user_nome])
                return f"Você realizou {minhas} calibrações."
            return "Você ainda não realizou calibrações."
        
        if "minhas instalações" in comando_lower or "minhas instalacoes" in comando_lower:
            if itr_b is not None and not itr_b.empty:
                minhas = len(itr_b[itr_b['Tecnico'] == user_nome])
                return f"Você realizou {minhas} instalações."
            return "Você ainda não realizou instalações."
        
        if "o que fazer" in comando_lower:
            if insts is not None:
                para_calibrar = len(insts[insts['Status'] == '1'])
                para_instalar = len(insts[insts['Status'] == '2'])
                if para_calibrar > 0:
                    return f"Você tem {para_calibrar} instrumentos para calibrar."
                if para_instalar > 0:
                    return f"Você tem {para_instalar} instrumentos para instalar."
                return "Nenhuma tarefa pendente no momento."
    
    return "Comando não reconhecido. Diga 'Ajuda' para ver os comandos disponíveis."


def _get_comandos_ajuda(user_tipo):
    """Retorna lista de comandos disponíveis para o perfil"""
    
    comandos = """
🎤 **Comandos de Voz Disponíveis:**

**Gerais:**
• "Que horas são?"
• "Que dia é hoje?"
• "Qual é a obra atual?"
• "Meu nome"

**Instrumentos:**
• "Total de instrumentos"
• "Material OK"
• "Calibrados"
• "Instalados"
• "Pendentes"
• "Mostrar instrumento PT-101"
• "Localização de FT-202"
• "Status de LT-303"
• "Próximo instrumento pendente"
• "Progresso da obra"
"""
    
    if user_tipo in ['Admin', 'Chefe de Equipa']:
        comandos += """
    
**Admin/Chefe:**
• "Punch Items abertos"
• "Calibração pendente"
• "Material em falta"
"""
    
    if user_tipo in ['Técnico', 'Instrumentista']:
        comandos += """
    
**Técnico:**
• "Minhas calibrações"
• "Minhas instalações"
• "O que fazer?"
"""
    
    return comandos

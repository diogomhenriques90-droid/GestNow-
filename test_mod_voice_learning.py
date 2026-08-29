"""
Testes do módulo de Aprendizagem Contínua da IA com Voz
(mod_voice_learning.py) — Dashboard de métricas (render_voice_learning_dashboard).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py). Ao contrário de todos os outros módulos desta
fase, este não lê CSVs via core.load_db/GCS — lê/escreve ficheiros
locais (voice_logs.csv, voice_feedback.csv, voice_patterns.json) em
caminhos relativos. Os testes apontam esses caminhos para uma pasta
temporária, para não tocar em ficheiros reais do repositório.

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 2
gráficos Plotly (Top Comandos, Atividade por Hora) — incluindo o
font_color/plot_bgcolor que ainda usa core.COLORS (paleta escura
antiga), deliberadamente não tocado nesta fase. O widget de feedback
(render_voice_feedback_widget) não é acionado nestes testes — só o
dashboard é.

Correr:  python -m unittest test_mod_voice_learning -v
"""
import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_LOGS_RECORDS = [
    {"timestamp": "2026-08-01 09:00:00", "user": "Ana Teste",
     "user_tipo": "Técnico", "obra": "Obra Teste",
     "command": "Qual o meu saldo de horas?",
     "command_processed": "qual o meu saldo de horas?",
     "response": "Tens 5h", "success": 1, "processing_time_ms": 120},
    {"timestamp": "2026-08-01 10:00:00", "user": "Bruno Teste",
     "user_tipo": "Chefe de Equipa", "obra": "Obra Teste",
     "command": "Regista uma avaria",
     "command_processed": "regista uma avaria",
     "response": "Não percebi", "success": 0, "processing_time_ms": 200},
]

_FEEDBACK_RECORDS = [
    {"timestamp": "2026-08-01 10:05:00", "user": "Bruno Teste",
     "command": "Regista uma avaria", "feedback_type": "bad",
     "comment": "Não entendeu o comando"},
]


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_voice_learning import render_voice_learning_dashboard
    render_voice_learning_dashboard()


def _run(com_dados=True):
    core._cached_load_db.clear()
    with tempfile.TemporaryDirectory() as tmp:
        logs_path = os.path.join(tmp, "voice_logs.csv")
        feedback_path = os.path.join(tmp, "voice_feedback.csv")
        patterns_path = os.path.join(tmp, "voice_patterns.json")

        if com_dados:
            pd.DataFrame(_LOGS_RECORDS).to_csv(logs_path, index=False)
            pd.DataFrame(_FEEDBACK_RECORDS).to_csv(feedback_path, index=False)

        with patch("mod_voice_learning.VOICE_LOGS_FILE", logs_path), \
             patch("mod_voice_learning.VOICE_FEEDBACK_FILE", feedback_path), \
             patch("mod_voice_learning.VOICE_PATTERNS_FILE", patterns_path):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
    return at


class TestRenderVoiceLearningSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Os
    logs de teste incluem um comando falhado e um feedback negativo,
    de propósito, para exercitar as sugestões de melhoria e a lista
    de comandos mais falhados."""

    def test_sem_erro_com_dados(self):
        at = _run(com_dados=True)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(com_dados=False)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_voice_learning.py lê as suas
    cores de core.THEME em vez de core.COLORS (paleta escura antiga)
    — o cartão de aprendizagem deixa de forçar um fundo em gradiente
    escuro tipo "glass". Os 2 gráficos Plotly (que ainda usam
    core.COLORS no font_color/color_scale) ficam de fora, de
    propósito — Fase 4."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary",
                      "accent", "warning", "success", "error"):
            self.assertIn(core.THEME[chave], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("rgba(30,41,59", textos)
        self.assertNotIn("rgba(15,23,42", textos)
        self.assertNotIn("#F8FAFC", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

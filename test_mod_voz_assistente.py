"""
Testes do módulo Assistente de Voz Global (mod_voz_assistente.py) —
botão flutuante injetado em toda a app (render_voice_assistant_global).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

O botão flutuante e a caixa de resposta em si são um componente
HTML/JS injetado via `st.components.v1.html()` (não `st.markdown`) —
não é inspecionável por `at.markdown`, e o CSS que os estiliza
(`_VOZ_CSS`) é sempre renderizado via `st.markdown()` logo no
início, independentemente de haver um comando de voz pendente. Por
isso um único render básico já cobre o CSS a testar.

Correr:  python -m unittest test_mod_voz_assistente -v
"""
import unittest

from streamlit.testing.v1 import AppTest

import core


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    from mod_voz_assistente import render_voice_assistant_global
    render_voice_assistant_global(
        user_tipo="Técnico", user_nome="Ana Teste",
        obra_sel="Obra Voz Teste"
    )


def _run():
    at = AppTest.from_function(_script, default_timeout=30)
    at.run()
    return at


class TestRenderVoiceAssistantSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro com um utilizador
    Técnico e uma obra selecionada (caso comum)."""

    def test_sem_erro(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_voz_assistente.py lê as suas
    cores de core.THEME — o botão flutuante e a caixa de resposta
    deixam de usar gradientes fixos (azul/vermelho) e um fundo
    escuro tipo "glass" (#1E293B→#0F172A com blur), passando a um
    acento e uma superfície claros consistentes com o resto da app."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "accent",
                      "success", "error"):
            self.assertIn(core.THEME[chave], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("background: #1E293B", textos)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#F8FAFC", textos)
        self.assertNotIn("linear-gradient", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

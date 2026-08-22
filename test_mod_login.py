"""
Testes do ecrã de login (mod_login.py) — Fase 2 da Identidade Visual:
o primeiro ecrã que qualquer pessoa vê passa a ter o mesmo tema claro
e polimento dos restantes (cartão em torno do formulário, THEME
central), mantendo o logótipo da CPS exatamente como estava (mesmo
ficheiro, sem alterações de cor/forma/proporção).

Não tocam em GCS real: `mod_login._gcs_read` é mockado (devolve None
por omissão — não há tentativa de login nestes testes).

Correr:  python -m unittest test_mod_login -v
"""
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import core


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    from mod_login import render_login
    render_login()


def _run():
    core._cached_load_db.clear()
    with patch("mod_login._gcs_read", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderLoginSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro."""

    def test_sem_erro(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_logo_continua_presente(self):
        # O logótipo (o desenho em si, inalterado) continua a aparecer
        # via <img> em base64 — só o ficheiro/variante pode mudar
        # (ver TestLogotipoVarianteClara), nunca o logótipo em si.
        at = _run()
        html = " ".join(m.value for m in at.markdown)
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("CPS Smart Solutions", html)

    def test_os_dois_separadores_existem(self):
        at = _run()
        labels = [t.label for t in at.tabs]
        self.assertIn("🔑 Password", labels)
        self.assertIn("🔢 PIN", labels)


class TestLogotipoVarianteClara(unittest.TestCase):
    """Fase 2 da Identidade Visual: com o ecrã de login claro, o
    logótipo passa a usar a variante já preparada para fundo claro
    ("transparente" — texto em cinza-escuro) em vez de "tema_escuro"
    (texto branco, invisível em fundo claro)."""

    def test_usa_variante_clara(self):
        with open("mod_login.py", encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("logo_cps_tema_escuro.png", src)
        self.assertIn("logo_cps_transparente.png", src)


class TestSemSubtituloSobLogo(unittest.TestCase):
    """A frase "Gestão de Instrumentação Industrial" por baixo do
    logótipo foi removida — fica só o logótipo."""

    def test_frase_ja_nao_aparece(self):
        at = _run()
        html = " ".join(m.value for m in at.markdown)
        self.assertNotIn("Gestão de Instrumentação Industrial", html)
        self.assertNotIn("login-subtitle", html)


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 2 da Identidade Visual: o ecrã de login lê as suas cores
    de core.THEME, já não força fundo escuro, e o formulário passa a
    aparecer dentro de um cartão (antes flutuava direto no fundo)."""

    def test_nao_forca_fundo_escuro(self):
        at = _run()
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        self.assertNotIn(".stApp", css)
        self.assertNotIn("#0F172A", css)
        self.assertNotIn("#1E293B", css)

    def test_cartao_de_login_usa_theme(self):
        at = _run()
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        self.assertIn(".login-card", css)
        for chave in ("surface", "border", "radius"):
            self.assertIn(core.THEME[chave], css)
        # text_secondary já não aparece no <style> (a única regra que
        # o usava, .login-subtitle, foi removida) — continua a
        # aparecer no corpo do ecrã (ex. rodapé de ligações).
        html = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["text_secondary"], html)

    def test_ligacao_usa_acento(self):
        at = _run()
        html = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["accent"], html)
        self.assertNotIn("#3B82F6", html)
        self.assertNotIn("#64748B", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)

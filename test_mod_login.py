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
import io
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import core
from core import hp


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
        self.assertIn("Password", labels)
        self.assertIn("PIN", labels)


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


class TestLoginComNomesDuplicados(unittest.TestCase):
    """Caracteriza o comportamento ATUAL (Fase 0, antes da correção) quando
    dois colaboradores partilham o mesmo Nome em usuarios.csv — já
    aconteceu em produção (ver comentário em mod_dashboard_obra.py sobre
    "NUNCA de join por nome... gerou duplicados no passado").

    A via Password percorre as linhas por ordem e para (`break`) na
    primeira que bater com o Nome introduzido — por isso só a password da
    PRIMEIRA linha é alguma vez verificada, mesmo que seja a segunda
    pessoa a tentar entrar com a sua própria password correta.

    Depois da correção (recusar login quando há mais que um Nome a
    bater), este teste passa a esperar um erro explícito em vez desta
    rejeição silenciosa/ambígua.
    """

    PWD_PRIMEIRA = "PasswordPrimeira123"
    PWD_SEGUNDA  = "PasswordSegunda456"

    @classmethod
    def setUpClass(cls):
        cls.hash_primeira = hp(cls.PWD_PRIMEIRA)
        cls.hash_segunda  = hp(cls.PWD_SEGUNDA)
        cls.csv = (
            "Nome,Password,Tipo,Cargo,PIN\n"
            f"Maria Santos,{cls.hash_primeira},Técnico,Instrumentista,\n"
            f"Maria Santos,{cls.hash_segunda},Chefe de Equipa,Chefe,\n"
        ).encode("utf-8-sig")

    def _tentar_login(self, password):
        core._cached_load_db.clear()
        with patch("mod_login._gcs_read", return_value=io.BytesIO(self.csv)):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="login_u1").set_value("Maria Santos").run()
            at.text_input(key="login_p1").set_value(password).run()
            at.button(key="FormSubmitter:form_login_pwd-ENTRAR").click().run()
        return at

    def test_primeira_pessoa_entra_com_a_sua_password(self):
        at = self._tentar_login(self.PWD_PRIMEIRA)
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertEqual(at.session_state["user"], "Maria Santos")

    def test_segunda_pessoa_nao_consegue_entrar_com_a_sua_propria_password(self):
        # Bug atual: como o login para na primeira linha que bate com o
        # Nome, só essa password é verificada — a segunda pessoa é
        # rejeitada mesmo introduzindo a SUA password correta.
        at = self._tentar_login(self.PWD_SEGUNDA)
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Password incorreta", textos_erro)


if __name__ == "__main__":
    unittest.main(verbosity=2)

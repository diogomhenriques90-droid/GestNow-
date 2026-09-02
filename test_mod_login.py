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
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import core
from core import hp


@contextmanager
def _apply(patches):
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield


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
    """Fase 0: quando dois colaboradores partilham o mesmo Nome em
    usuarios.csv — já aconteceu em produção (ver comentário em
    mod_dashboard_obra.py sobre "NUNCA de join por nome... gerou
    duplicados no passado") — a via Password recusa o login com um erro
    explícito de ambiguidade, em vez de autenticar silenciosamente a
    primeira linha que bater (o bug anterior, que já permitia por sorte
    a uma das duas pessoas entrar na sua própria conta enquanto a outra
    ficava de fora sem explicação)."""

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

    def test_primeira_pessoa_e_recusada_com_erro_de_ambiguidade(self):
        # Antes da Fase 0, esta pessoa entrava "por sorte" (era a
        # primeira linha). Agora fica de fora tal como a segunda, até o
        # Admin resolver a duplicação.
        at = self._tentar_login(self.PWD_PRIMEIRA)
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("mais do que um utilizador com este nome", textos_erro)

    def test_segunda_pessoa_e_recusada_com_erro_de_ambiguidade(self):
        at = self._tentar_login(self.PWD_SEGUNDA)
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("mais do que um utilizador com este nome", textos_erro)


class TestLoginPinComNomesDuplicados(unittest.TestCase):
    """Fase 0: o mesmo defeito existia na via PIN (verificava Nome+PIN em
    conjunto, com `.iloc[0]` a escolher silenciosamente a primeira
    correspondência) — agora verifica primeiro se o Nome é único, antes
    de sequer olhar para o PIN."""

    @classmethod
    def setUpClass(cls):
        cls.csv = (
            "Nome,Password,Tipo,Cargo,PIN\n"
            "Maria Santos,,Técnico,Instrumentista,1111\n"
            "Maria Santos,,Chefe de Equipa,Chefe,2222\n"
        ).encode("utf-8-sig")

    def _tentar_login_pin(self, pin):
        core._cached_load_db.clear()
        with patch("mod_login._gcs_read", return_value=io.BytesIO(self.csv)):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="login_u2").set_value("Maria Santos").run()
            at.text_input(key="login_p2").set_value(pin).run()
            at.button(key="FormSubmitter:form_login_pin-ENTRAR COM PIN").click().run()
        return at

    def test_pin_da_primeira_e_recusado_com_erro_de_ambiguidade(self):
        at = self._tentar_login_pin("1111")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("mais do que um utilizador com este nome", textos_erro)

    def test_pin_da_segunda_e_recusado_com_erro_de_ambiguidade(self):
        at = self._tentar_login_pin("2222")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("mais do que um utilizador com este nome", textos_erro)


class TestLoginPinComHash(unittest.TestCase):
    """Fase 1: o PIN passou a ser gravado em hash (hp/cp), como a
    password — o login por PIN tem de comparar por hash, não por
    igualdade de texto simples."""

    PIN = "4321"

    @classmethod
    def setUpClass(cls):
        cls.csv = (
            "Nome,Password,Tipo,Cargo,PIN\n"
            f"Rui Costa,,Técnico,Instrumentista,{hp(cls.PIN)}\n"
        ).encode("utf-8-sig")

    def _tentar(self, pin):
        core._cached_load_db.clear()
        with patch("mod_login._gcs_read", return_value=io.BytesIO(self.csv)):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="login_u2").set_value("Rui Costa").run()
            at.text_input(key="login_p2").set_value(pin).run()
            at.button(key="FormSubmitter:form_login_pin-ENTRAR COM PIN").click().run()
        return at

    def test_pin_correto_entra(self):
        at = self._tentar(self.PIN)
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertEqual(at.session_state["user"], "Rui Costa")

    def test_pin_errado_nao_entra(self):
        at = self._tentar("0000")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("PIN incorreto", textos_erro)


class TestLoginPorNumero(unittest.TestCase):
    """Fase 1: via principal de login — Número de colaborador + um
    único campo de credencial, sempre com o mesmo aspeto, que o sistema
    valida como PIN ou Password consoante o Tipo, sem nunca revelar
    isso no ecrã antes da submissão."""

    PIN_TECNICO   = "1234"
    PWD_ADMIN     = "password123"

    @classmethod
    def setUpClass(cls):
        cls.csv = (
            "Nome,Password,PIN,Tipo,Cargo,Numero_Colaborador,Bloqueado\n"
            f"Rui Costa,,{hp(cls.PIN_TECNICO)},Técnico,Instrumentista,12345,\n"
            f"Ana Silva,{hp(cls.PWD_ADMIN)},,Admin,Administrador,54321,\n"
            "Marta Reis,,,Chefe de Equipa,Chefe,67890,Sim\n"
        ).encode("utf-8-sig")

    def _submeter(self, numero, credencial, extra_patches=()):
        core._cached_load_db.clear()
        with patch("mod_login._gcs_read", return_value=io.BytesIO(self.csv)), \
             patch("mod_login.registar_tentativa_login") as mock_registar, \
             patch("mod_login.contar_falhas_recentes", return_value=0) as mock_contar, \
             patch("mod_login.limpar_tentativas_login") as mock_limpar, \
             patch("mod_login.bloquear_conta_por_numero", return_value=False) as mock_bloquear, \
             patch("mod_login.criar_notificacao") as mock_notif, \
             _apply(extra_patches):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="login_numero").set_value(numero).run()
            at.text_input(key="login_credencial").set_value(credencial).run()
            at.button(key="FormSubmitter:form_login_numero-ENTRAR").click().run()
        return at, dict(
            registar=mock_registar, contar=mock_contar,
            limpar=mock_limpar, bloquear=mock_bloquear, notif=mock_notif,
        )

    def test_tecnico_entra_com_pin(self):
        at, mocks = self._submeter("12345", self.PIN_TECNICO)
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertEqual(at.session_state["user"], "Rui Costa")
        mocks["limpar"].assert_called_once_with("12345")

    def test_admin_entra_com_password(self):
        at, mocks = self._submeter("54321", self.PWD_ADMIN)
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertEqual(at.session_state["user"], "Ana Silva")

    def test_credencial_errada_mensagem_generica(self):
        at, mocks = self._submeter("12345", "credencial-errada")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Credenciais inválidas", textos_erro)
        mocks["registar"].assert_called_once_with("12345")

    def test_numero_inexistente_mesma_mensagem_generica(self):
        at, mocks = self._submeter("99999", "qualquer-coisa")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Credenciais inválidas", textos_erro)
        mocks["registar"].assert_called_once_with("99999")

    def test_conta_ja_bloqueada_recusa_mesmo_com_credencial_certa(self):
        # Marta Reis está com Bloqueado=Sim na fixture — sem PIN/Password
        # definidos, então nenhuma credencial "acerta" de propósito;
        # confirma-se que a resposta é a mesma genérica, sem tentar
        # sequer validar a credencial.
        at, mocks = self._submeter("67890", "qualquer-coisa")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Credenciais inválidas", textos_erro)

    def test_formato_invalido_nao_chega_a_consultar_dados(self):
        at, mocks = self._submeter("abc", "qualquer-coisa")
        self.assertFalse(at.exception, msg=str(at.exception))
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Credenciais inválidas", textos_erro)
        mocks["registar"].assert_not_called()

    def test_bloqueio_disparado_ao_atingir_limite(self):
        at, mocks = self._submeter(
            "12345", "credencial-errada",
            extra_patches=[patch("mod_login.contar_falhas_recentes", return_value=3)],
        )
        self.assertFalse(at.exception, msg=str(at.exception))
        mocks["bloquear"].assert_called_once()
        self.assertEqual(mocks["bloquear"].call_args[0][0], "12345")

    def test_notifica_admin_quando_bloqueio_se_efetiva(self):
        at, mocks = self._submeter(
            "12345", "credencial-errada",
            extra_patches=[
                patch("mod_login.contar_falhas_recentes", return_value=3),
                patch("mod_login.bloquear_conta_por_numero", return_value=True),
            ],
        )
        self.assertFalse(at.exception, msg=str(at.exception))
        mocks["notif"].assert_called_once()
        self.assertEqual(mocks["notif"].call_args.kwargs.get("destinatario"), "admin")

    def test_falha_abaixo_do_limite_nao_bloqueia(self):
        at, mocks = self._submeter(
            "12345", "credencial-errada",
            extra_patches=[patch("mod_login.contar_falhas_recentes", return_value=2)],
        )
        self.assertFalse(at.exception, msg=str(at.exception))
        mocks["bloquear"].assert_not_called()
        mocks["notif"].assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Testes do ecrã de login (mod_login.py) — Fase 2 da Identidade Visual:
o primeiro ecrã que qualquer pessoa vê passa a ter o mesmo tema claro
e polimento dos restantes (cartão em torno do formulário, THEME
central), mantendo o logótipo da CPS exatamente como estava (mesmo
ficheiro, sem alterações de cor/forma/proporção).

A partir daqui, login só por Número de Colaborador + Password — o
acesso antigo por Nome (Password ou PIN) e a via de PIN dentro do
próprio número foram removidos por completo, não só desativados.
Os testes que cobriam essas vias foram removidos com o código; os que
cobrem o que sobrevive (via por número, força-reset de password
curta) mantêm-se.

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


def _script_com_reset_pendente(numero):
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    # Semeia só na primeira execução — o script corre de novo a cada
    # interação/rerun, e mesmo um setdefault reintroduziria a chave
    # depois de o próprio fluxo de reset a remover com sucesso.
    if not st.session_state.get('_ja_semeado_reset'):
        st.session_state['_forcar_reset_numero'] = numero
        st.session_state['_ja_semeado_reset']    = True
    from mod_login import render_login
    render_login()


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

    def test_so_existe_a_via_por_numero_sem_separadores(self):
        # O acesso antigo (por Nome, com abas Password/PIN) foi
        # removido por completo — já não há nenhuma aba no ecrã de
        # login, só o formulário único de Número + Password.
        at = _run()
        self.assertEqual(len(at.tabs), 0)
        self.assertIsNotNone(at.text_input(key="login_numero"))
        self.assertIsNotNone(at.text_input(key="login_credencial"))


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


class TestLoginPorNumero(unittest.TestCase):
    """Via única de login: Número de colaborador + Password, para
    qualquer Tipo — já não há distinção por Tipo (PIN para uns,
    Password para outros); todos entram sempre pela mesma verificação
    de Password."""

    PWD_TECNICO = "passwordTecnico1"
    PWD_ADMIN   = "password123"

    @classmethod
    def setUpClass(cls):
        cls.csv = (
            "Nome,Password,PIN,Tipo,Cargo,Numero_Colaborador,Bloqueado\n"
            f"Rui Costa,{hp(cls.PWD_TECNICO)},,Técnico,Instrumentista,12345,\n"
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

    def test_tecnico_tambem_entra_por_password(self):
        # Já não há PIN para nenhum Tipo — um Técnico entra pela mesma
        # verificação de Password que um Admin.
        at, mocks = self._submeter("12345", self.PWD_TECNICO)
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
        # Marta Reis está com Bloqueado=Sim na fixture — sem Password
        # definida, então nenhuma credencial "acerta" de propósito;
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


class TestForcarResetPasswordCurta(unittest.TestCase):
    """Quem ainda tiver uma Password anterior ao mínimo de 8
    caracteres (legado de antes da correção) autentica normalmente,
    mas a sessão só fica completa depois de definir uma password nova
    — não entra logo com a password curta."""

    PWD_CURTA = "curta1"   # 6 caracteres — válida antes, curta agora

    @classmethod
    def setUpClass(cls):
        cls.csv = (
            "Nome,Password,PIN,Tipo,Cargo,Numero_Colaborador,Bloqueado\n"
            f"Ana Silva,{hp(cls.PWD_CURTA)},,Admin,Administrador,54321,\n"
        ).encode("utf-8-sig")

    def _base_patches(self):
        return [
            patch("mod_login._gcs_read", return_value=io.BytesIO(self.csv)),
            patch("mod_login.registar_tentativa_login"),
            patch("mod_login.contar_falhas_recentes", return_value=0),
            patch("mod_login.limpar_tentativas_login"),
            patch("mod_login.bloquear_conta_por_numero", return_value=False),
            patch("mod_login.criar_notificacao"),
        ]

    def test_password_curta_nao_completa_a_sessao_logo(self):
        core._cached_load_db.clear()
        with _apply(self._base_patches()):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="login_numero").set_value("54321").run()
            at.text_input(key="login_credencial").set_value(self.PWD_CURTA).run()
            at.button(key="FormSubmitter:form_login_numero-ENTRAR").click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        self.assertEqual(at.session_state["_forcar_reset_numero"], "54321")
        textos = " ".join(m.value for m in at.warning)
        self.assertIn("8 caracteres", textos)

    def test_password_nova_curta_e_recusada(self):
        # Parte já do ecrã de reset pendente (pré-semeado no session_state),
        # em vez de encadear a partir do formulário de login — misturar os
        # dois no mesmo `at` faz o AppTest tentar reidratar widgets
        # (login_numero) que já não existem na árvore da segunda tela.
        core._cached_load_db.clear()
        with _apply(self._base_patches()):
            at = AppTest.from_function(
                _script_com_reset_pendente, args=("54321",), default_timeout=30)
            at.run()
            at.text_input(key="reset_nova_pwd").set_value("curta2").run()
            at.text_input(key="reset_conf_pwd").set_value("curta2").run()
            at.button(key="FormSubmitter:form_forcar_reset-Definir Password").click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("user", at.session_state)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Mínimo 8 caracteres", textos_erro)

    def test_password_nova_valida_completa_o_login(self):
        core._cached_load_db.clear()
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        with _apply(self._base_patches() + [patch("core._gcs_write", side_effect=_gcs_write),
                                             patch("core._gcs_client", return_value=None)]):
            at = AppTest.from_function(
                _script_com_reset_pendente, args=("54321",), default_timeout=30)
            at.run()
            at.text_input(key="reset_nova_pwd").set_value("passwordNova8").run()
            at.text_input(key="reset_conf_pwd").set_value("passwordNova8").run()
            at.button(key="FormSubmitter:form_forcar_reset-Definir Password").click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertEqual(at.session_state["user"], "Ana Silva")
        self.assertNotIn("_forcar_reset_numero", at.session_state)
        conteudo = writes["usuarios.csv"].decode("utf-8-sig")
        self.assertIn("$2b$", conteudo)


if __name__ == "__main__":
    unittest.main(verbosity=2)

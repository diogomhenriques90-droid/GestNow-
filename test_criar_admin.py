"""
Testes de criar_admin.py — ecrã de setup do primeiro Admin. Nunca teve
nenhum teste antes desta sessão. Migrado do visual escuro antigo (cores
fixas) para o THEME central, e sem ícones.

Correr:  python -m unittest test_criar_admin -v
"""
import io
import unittest
from unittest.mock import patch
import re

from streamlit.testing.v1 import AppTest

import core

_PADRAO_EMOJI = re.compile(
    r'[\U0001F300-\U0001FAFF☀-➿←-⇿⬀-⯿️]'
)


def _script():
    from criar_admin import render_criar_admin
    render_criar_admin()


def _run(gcs_read_return=None):
    # Patch em "criar_admin._gcs_read" (não "core._gcs_read"): o módulo
    # importa a função com `from core import _gcs_read`, uma ligação de
    # nome própria — depois do primeiro import, um patch em core.* já
    # não a alcança, porque `criar_admin` fica em cache no sys.modules.
    with patch("criar_admin._gcs_read", return_value=gcs_read_return):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


def _sem_emoji(at):
    for m in at.markdown:
        assert not _PADRAO_EMOJI.search(m.value), f"emoji encontrado: {m.value!r}"


class TestCriarAdminSemAdminExistente(unittest.TestCase):
    """usuarios.csv inexistente (_gcs_read devolve None) -> setup permitido,
    formulário completo é mostrado."""

    def test_formulario_sem_erro_sem_icones(self):
        at = _run(gcs_read_return=None)
        self.assertFalse(at.exception, msg=str(at.exception))
        _sem_emoji(at)
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["text"], textos)
        # #0F172A/#DC2626/#334155 eram as cores escuras/vermelhas antigas,
        # fora da paleta THEME.
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#DC2626", textos)
        self.assertNotIn("#334155", textos)


class TestCriarAdminDeteccaoDeDuplicadoFraca(unittest.TestCase):
    """Caracteriza o comportamento ATUAL (Fase 0, antes da correção) da
    verificação de nome duplicado em criar_admin.py: é feita por
    `nome.strip() in df_users['Nome'].values` — comparação exata,
    sensível a maiúsculas/acentos. Uma variante do mesmo nome (só
    maiúsculas diferentes) passa despercebida hoje.

    Depois da correção (normalização tipo `_norm_nome_cliente`), este
    teste passa a esperar o erro "Já existe um utilizador...".
    """

    def _csv_com_tecnico(self, nome):
        return io.BytesIO(f"Nome,Tipo\n{nome},Técnico\n".encode("utf-8-sig"))

    def _submeter(self, nome_existente, nome_novo):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        # Três mocks são necessários, não só o de criar_admin._gcs_read:
        # save_db() usa a sua PRÓPRIA referência interna a _gcs_read (para
        # o teste de perda de registos) e a _gcs_client (para o backup
        # diário) — mockar só criar_admin._gcs_read deixa essas duas
        # chamadas caírem na GCS real. Já aconteceu nesta sessão.
        with patch("criar_admin._gcs_read",
                   side_effect=lambda fn: self._csv_com_tecnico(nome_existente)), \
             patch("core._gcs_read",
                   side_effect=lambda fn: self._csv_com_tecnico(nome_existente)), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="ca_nome").set_value(nome_novo).run()
            at.text_input(key="ca_pw").set_value("segredo123").run()
            at.text_input(key="ca_pw2").set_value("segredo123").run()
            at.button(
                key="FormSubmitter:form_criar_admin-Criar Administrador"
            ).click().run()
        return at, writes

    def test_nome_exatamente_igual_e_bloqueado(self):
        at, writes = self._submeter("João Silva", "João Silva")
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Já existe um utilizador", textos_erro)
        self.assertNotIn("usuarios.csv", writes)

    def test_variante_so_de_maiusculas_passa_despercebida(self):
        # Bug atual: "JOÃO SILVA" não é reconhecido como o mesmo nome que
        # já existe ("João Silva"), porque a comparação é exata.
        at, writes = self._submeter("João Silva", "JOÃO SILVA")
        self.assertFalse(at.exception, msg=str(at.exception))
        textos_erro = " ".join(m.value for m in at.error)
        self.assertNotIn("Já existe um utilizador", textos_erro)
        self.assertIn("usuarios.csv", writes)
        conteudo = writes["usuarios.csv"].decode("utf-8-sig")
        self.assertIn("JOÃO SILVA", conteudo)


class TestCriarAdminComAdminExistente(unittest.TestCase):
    """usuarios.csv já tem um Admin -> acesso bloqueado."""

    def test_acesso_negado_sem_erro_sem_icones(self):
        import io
        csv_bytes = io.BytesIO(
            "Nome,Tipo\nJoao,Admin\n".encode("utf-8")
        )
        at = _run(gcs_read_return=csv_bytes)
        self.assertFalse(at.exception, msg=str(at.exception))
        _sem_emoji(at)
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Acesso negado", textos_erro)


if __name__ == "__main__":
    unittest.main(verbosity=2)

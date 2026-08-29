"""
Testes de criar_admin.py — ecrã de setup do primeiro Admin. Nunca teve
nenhum teste antes desta sessão. Migrado do visual escuro antigo (cores
fixas) para o THEME central, e sem ícones.

Correr:  python -m unittest test_criar_admin -v
"""
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

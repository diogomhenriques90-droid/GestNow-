"""
Testes do ecrã de login (mod_login.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 2 da Identidade Visual dar a este ecrã (o primeiro que
qualquer pessoa vê) o mesmo polimento e tema claro dos restantes,
mantendo o logótipo da CPS exatamente como está (mesmo ficheiro,
sem alterações de cor/forma/proporção).

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
        # O logótipo (mesmo ficheiro, sem alterações) continua a
        # aparecer via <img> em base64.
        at = _run()
        html = " ".join(m.value for m in at.markdown)
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("CPS Smart Solutions", html)

    def test_os_dois_separadores_existem(self):
        at = _run()
        labels = [t.label for t in at.tabs]
        self.assertIn("🔑 Password", labels)
        self.assertIn("🔢 PIN", labels)


if __name__ == "__main__":
    unittest.main(verbosity=2)

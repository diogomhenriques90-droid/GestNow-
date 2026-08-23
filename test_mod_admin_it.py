"""
Testes do módulo de Gestão de TI (mod_admin_it.py, sub-separador
"IT & Infraestrutura" do separador "💻 IT" no Admin).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Quase todo o conteúdo deste módulo é demonstrativo (custos, emails,
licenças, hardware — dados fixos no código, não vêm de GCS/CSV) —
render_it() não recebe argumentos nem chama load_db. Só o separador
"Backups" (dentro de Infraestrutura) toca em GCS real
(core._gcs_read/_registar_backup/_verificar_alerta_backup), por isso
é o único ponto mockado.

Correr:  python -m unittest test_mod_admin_it -v
"""
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import core


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_it import render_it
    render_it()


def _run():
    core._cached_load_db.clear()
    with patch("mod_admin_it._gcs_read", return_value=None), \
         patch("mod_admin_it._verificar_alerta_backup",
               return_value=("nunca", None)):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderItSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro. Cobre os 6 separadores
    (Custos App, Custos IA, Gestão Emails, Acessos & Licenças,
    Infraestrutura, Monitorização) porque st.tabs() desenha o
    conteúdo de todos de uma vez — incluindo os sub-separadores de
    Acessos & Licenças e Infraestrutura, também st.tabs()."""

    def test_sem_erro(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

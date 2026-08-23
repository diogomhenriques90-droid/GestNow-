"""
Testes do Hub Principal do Admin (mod_admin.py) — cabeçalho,
notificações, métricas e seleção de módulo (segmented_control).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

`core._gcs_read` mockado para devolver None — todas as leituras (do
mod_admin.py e de qualquer módulo lazy-importado por ele, ex.
mod_armazem.py) caem no fallback de DataFrame vazio, sem tocar em
GCS real. As 24 posições de render_admin(*args) só alimentam o
cabeçalho/métricas — cada separador volta a chamar load_all()
internamente (_unpack()), por isso também é mockado.

Correr:  python -m unittest test_mod_admin -v
"""
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_N_ARGS = 24


def _script(tab_sel=None):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    st.session_state['tipo'] = 'Admin'
    if tab_sel:
        st.session_state['admin_tab_sel'] = tab_sel
    from mod_admin import render_admin
    vazio = pd.DataFrame()
    render_admin(*([vazio] * 24))


def _run(tab_sel=None, extra_patches=()):
    core._cached_load_db.clear()
    with patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        with _apply(extra_patches):
            at = AppTest.from_function(_script, args=(tab_sel,), default_timeout=30)
            at.run()
    return at


@contextmanager
def _apply(patches):
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield


class TestRenderAdminSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro. Por omissão fica no
    separador "📦 Armazém" (primeiro do segmented_control)."""

    def test_sem_erro_separador_omissao(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_separador_it(self):
        at = _run(tab_sel="💻 IT")
        self.assertFalse(at.exception, msg=str(at.exception))


class TestNotificacoesSemErro(unittest.TestCase):
    """Painel de notificações (badge + lista) — dados vêm de
    core.get_notificacoes/contar_notificacoes_nao_lidas, mockados
    diretamente (chamados via `from core import ...` dentro da
    função, por isso o patch tem de ser em core.*, não em
    mod_admin.*)."""

    def _run_com_notifs(self, notifs_df, n_nao_lidas):
        return _run(extra_patches=[
            patch("core.get_notificacoes", return_value=notifs_df),
            patch("core.contar_notificacoes_nao_lidas", return_value=n_nao_lidas),
        ])

    def test_sem_erro_com_notificacoes(self):
        notifs = pd.DataFrame([{
            "ID": "N1", "Data": "01/01/2026", "Hora": "10:00",
            "Destinatario": "Admin", "Titulo": "Nova aprovação",
            "Mensagem": "Um instrumento foi aprovado pelo cliente.",
            "Tipo": "success", "Lida": "Não", "Acao_URL": "",
        }])
        at = self._run_com_notifs(notifs, 1)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_notificacoes(self):
        at = self._run_com_notifs(pd.DataFrame(), 0)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestSmtpConfigSemErro(unittest.TestCase):
    """Caixa de configuração SMTP (separador IT › Config Email) —
    core.get_smtp_config mockado para simular SMTP configurado."""

    def test_sem_erro_smtp_configurado(self):
        config = {
            "server": "smtp.exemplo.pt", "port": 587, "user": "geral@exemplo.pt",
            "password": "x", "from_name": "GestNow", "from_email": "geral@exemplo.pt",
        }
        at = _run(tab_sel="💻 IT", extra_patches=[
            patch("core.get_smtp_config", return_value=config),
        ])
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

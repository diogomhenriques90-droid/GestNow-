"""
Testes do Hub Principal do Admin (mod_admin.py) — cabeçalho,
notificações, métricas e seleção de módulo (segmented_control) — Fase
3 da Identidade Visual: migração para o THEME central (core.py).

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
    separador "Armazém" (primeiro do segmented_control)."""

    def test_sem_erro_separador_omissao(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_separador_it(self):
        at = _run(tab_sel="IT")
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
        at = _run(tab_sel="IT", extra_patches=[
            patch("core.get_smtp_config", return_value=config),
        ])
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin.py lê as suas cores de
    core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados no cabeçalho, badge/
    cartões de notificação e caixa SMTP.

    Fixa também o bug mais grave encontrado nesta Fase: um bloco CSS
    global (`.stMarkdown,.stText,...,h1,h2,h3 { color:#F8FAFC
    !important; }`) forçava TODO o texto do painel Admin a
    quase-branco com !important — ilegível sobre o fundo claro do
    tema central. Removido, tal como o estilo duplicado/conflituante
    de st.metric (core.py já o define via THEME desde a Fase 1)."""

    def test_css_forcado_removido(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#F8FAFC", textos)
        self.assertNotIn("#60A5FA", textos)
        self.assertNotIn("!important", textos)

    def test_cabecalho_usa_theme(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary", "accent"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#6B7280", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)

    def test_notificacoes_usam_theme(self):
        notifs = pd.DataFrame([{
            "ID": "N1", "Data": "01/01/2026", "Hora": "10:00",
            "Destinatario": "Admin", "Titulo": "Nova aprovação",
            "Mensagem": "Um instrumento foi aprovado pelo cliente.",
            "Tipo": "success", "Lida": "Não", "Acao_URL": "",
        }])
        at = _run(extra_patches=[
            patch("core.get_notificacoes", return_value=notifs),
            patch("core.contar_notificacoes_nao_lidas", return_value=1),
        ])
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["error"], textos)   # badge de não lidas
        self.assertIn(core.THEME["success"], textos)  # cartão Tipo=success

    def test_smtp_box_usa_theme(self):
        config = {
            "server": "smtp.exemplo.pt", "port": 587, "user": "geral@exemplo.pt",
            "password": "x", "from_name": "GestNow", "from_email": "geral@exemplo.pt",
        }
        at = _run(tab_sel="IT", extra_patches=[
            patch("core.get_smtp_config", return_value=config),
        ])
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["success"], textos)
        self.assertIn(core.THEME["surface"], textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

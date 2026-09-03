"""
Testes do módulo de Gestão de TI (mod_admin_it.py, sub-separador
"IT & Infraestrutura" do separador "💻 IT" no Admin) — Fase 3 da
Identidade Visual: migração para o THEME central (core.py), em vez
de hexadecimais soltos.

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


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin_it.py lê as suas cores
    de core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros/em tom forçados nos cartões de
    Custos App, aviso de API Keys, estado do backup e aviso de
    restauro."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
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

    def test_sem_fundo_em_tom_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#F8FAFC", textos)
        self.assertNotIn("rgba(59,130,246,", textos)
        self.assertNotIn("rgba(239,68,68,", textos)

    def test_backup_nunca_feito_usa_theme_error(self):
        # Estado 'nunca' — cor mais grave (vermelho de estado real).
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["error"], textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

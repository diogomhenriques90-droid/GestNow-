"""
Testes do Dashboard Executivo CFO (mod_fat_dashboard.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 2 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4): as cores dos gráficos Plotly
(_grafico_*, ~10 funções) — não herdam do tema do Streamlit, precisam
da sua própria paleta partilhada em código à parte.

Não tocam em GCS real: `mod_fat_dashboard.load_db` é mockado
diretamente (devolve DataFrames vazios com as colunas certas).

Correr:  python -m unittest test_mod_fat_dashboard -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core


def _fake_load_db(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


_OBRAS_RECORDS = [{
    "Obra": "Obra Dashboard Teste", "Cliente": "Cliente Teste", "Ativa": "Ativa",
}]

_REGISTOS_RECORDS = [{
    "Técnico": "Ana Teste", "Obra": "Obra Dashboard Teste",
    "Data": "01/01/2026", "Horas_Total": "8", "Status": "3",
}]

_DIARIAS_PAG_RECORDS = [{
    "Obra": "Obra Dashboard Teste", "Valor_Total": "50",
}]


def _script(obras_records, registos_records, diarias_pag_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_dashboard import render_fat_dashboard
    vazio = pd.DataFrame()
    render_fat_dashboard(
        pd.DataFrame(obras_records),
        pd.DataFrame(registos_records),
        vazio,
        pd.DataFrame(diarias_pag_records),
    )


def _run(obras_records=None, registos_records=None, diarias_pag_records=None,
         load_db_fn=_fake_load_db):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    diarias_pag_records = diarias_pag_records if diarias_pag_records is not None else _DIARIAS_PAG_RECORDS
    core._cached_load_db.clear()
    with patch("mod_fat_dashboard.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, registos_records, diarias_pag_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderFatDashboardSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], registos_records=[], diarias_pag_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

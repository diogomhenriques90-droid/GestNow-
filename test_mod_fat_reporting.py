"""
Testes do módulo de Reporting Executivo (mod_fat_reporting.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 2 da Identidade Visual migrar este módulo (188 cores à
mão) para o THEME central (core.py) e as funções partilhadas
render_card()/render_badge().

Fora de âmbito, de propósito (Fase 4): as cores dos gráficos Plotly
(_grafico_*) e do PDF executivo (_gerar_pdf_executivo, reportlab) —
não herdam do tema do Streamlit, precisam da sua própria paleta
partilhada em código.

Não tocam em GCS real: `mod_fat_reporting.load_db` é mockado
diretamente (devolve DataFrames vazios com as colunas certas).

Correr:  python -m unittest test_mod_fat_reporting -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core


def _fake_load_db(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


_OBRAS_RECORDS = [{
    "Obra": "Obra Reporting Teste", "Cliente": "Cliente Teste", "Ativa": "Ativa",
}]

_REGISTOS_RECORDS = [{
    "Técnico": "Ana Teste", "Obra": "Obra Reporting Teste",
    "Data": "01/01/2026", "Horas_Total": "8",
}]

_FATURAS_RECORDS = [{
    "ID": "F1", "Numero": "FAT001", "Data_Emissao": "01/01/2026",
    "Data_Vencimento": "31/01/2026", "Cliente": "Cliente Teste",
    "NIF_Cliente": "123456789", "Obra": "Obra Reporting Teste",
    "Subtotal": "1000", "IVA": "230", "Total": "1230",
    "Estado": "Emitida", "Paga_Em": "",
}]


def _script(obras_records, registos_records, faturas_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_reporting import render_fat_reporting
    vazio = pd.DataFrame()
    render_fat_reporting(
        pd.DataFrame(obras_records),
        pd.DataFrame(registos_records),
        pd.DataFrame(faturas_records),
        vazio,
    )


def _run(obras_records=None, registos_records=None, faturas_records=None,
         load_db_fn=_fake_load_db):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    faturas_records = faturas_records if faturas_records is not None else _FATURAS_RECORDS
    core._cached_load_db.clear()
    with patch("mod_fat_reporting.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, registos_records, faturas_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderFatReportingSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    todos os separadores (Dashboard Executivo, Plano de Negócios,
    Benchmarking, Motor de Regras, Passaporte Financeiro, Exportar)
    porque st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], registos_records=[], faturas_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

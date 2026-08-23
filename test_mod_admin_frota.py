"""
Testes do módulo Gestão de Frota (mod_admin_frota.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Não tocam em GCS real: `mod_admin_frota.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_admin_frota -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_FROTA_RECORDS = [{
    "ID": "V1", "Matricula": "AA-00-AA", "Marca": "Renault", "Modelo": "Kangoo",
    "Tipo": "Própria", "Condutor": "Ana Teste", "Custo_Mensal": "250",
    "Status": "Ativa", "Data_Registo": "01/01/2026",
}]

_COMB_RECORDS = [{
    "ID": "C1", "Data": "01/01/2026", "Matricula": "AA-00-AA", "Condutor": "Ana Teste",
    "Litros": "40", "Valor": "60", "KM": "1000", "Tipo_Comb": "Gasóleo",
    "Recibo_b64": "",
}]

_AVARIAS_RECORDS = [{
    "ID": "AV1", "Data": "01/01/2026", "Matricula": "AA-00-AA",
    "Descricao": "Pneu furado", "Urgencia": "Alta", "Valor_Est": "80",
    "Status": "Pendente", "Registado_Por": "Admin",
}]


def _fake_load_db(fn, cols, silent=False):
    if fn == "frota_viaturas.csv":
        return pd.DataFrame(_FROTA_RECORDS)
    if fn == "frota_combustivel.csv":
        return pd.DataFrame(_COMB_RECORDS)
    if fn == "frota_avarias.csv":
        return pd.DataFrame(_AVARIAS_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_frota import render_frota
    render_frota()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_admin_frota.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderFrotaSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 3 separadores (Viaturas, Combustível, Avarias) porque
    st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

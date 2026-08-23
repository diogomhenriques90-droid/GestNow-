"""
Testes do módulo Planeamento e Engenharia (mod_admin_planeamento.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Não tocam em GCS real: `mod_admin_planeamento.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_admin_planeamento -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_PACOTES_RECORDS = [{
    "ID": "P1", "Obra": "Obra Teste", "Frente": "Frente A",
    "Descricao": "Instalação de instrumentos", "Horas_Plan": "40",
    "Horas_Reais": "20", "Data_Inicio": "01/01/2026", "Data_Fim": "31/01/2026",
    "Status": "Em Curso", "Criado_Por": "Admin",
}]

_MILESTONES_RECORDS = [{
    "ID": "M1", "Obra": "Obra Teste", "Descricao": "Entrega Fase 1",
    "Data_Alvo": "15/02/2026", "Responsavel": "Ana Teste", "Status": "Pendente",
}]

_DESENHOS_RECORDS = [{
    "ID": "D1", "Obra": "Obra Teste", "Tipo": "P&ID", "Revisao": "Rev A",
    "Ficheiro_b64": "", "Data_Upload": "01/01/2026 10:00", "Upload_Por": "Admin",
}]


def _fake_load_db(fn, cols, silent=False):
    if fn == "planeamento_pacotes.csv":
        return pd.DataFrame(_PACOTES_RECORDS)
    if fn == "planeamento_milestones.csv":
        return pd.DataFrame(_MILESTONES_RECORDS)
    if fn == "planeamento_desenhos.csv":
        return pd.DataFrame(_DESENHOS_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_planeamento import render_planeamento
    render_planeamento()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_admin_planeamento.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderPlaneamentoSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 4 separadores (Produção, Cronograma, Recursos, Desenhos) porque
    st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

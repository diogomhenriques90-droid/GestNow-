"""
Testes do módulo Simulador de Crise & Alertas Antecipados
(mod_fat_crise.py) — Semáforo, Stress Tests, Simulador E-se?, Altman
Z-Score, Fontes de Ajuda, Plano Contingência.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 4
gráficos Plotly (Gauge Saúde, Gauge Autonomia, Semáforo Indicadores,
Cash Flow, Waterfall Altman) e o PDF do Plano de Contingência
(reportlab). O Conselho IA não é acionado nestes testes (depende de
um botão não acionado).

Não tocam em GCS real: `mod_fat_crise.load_db` é mockado diretamente
(devolve DataFrames de teste, consoante o ficheiro pedido).

Correr:  python -m unittest test_mod_fat_crise -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_HOJE = pd.Timestamp.today()
_MES_ATUAL = _HOJE.strftime("%d/%m/%Y")

_FATURAS_CLI_RECORDS = [
    {"ID": "F1", "Numero": "FT 2026/1", "Data_Emissao": _MES_ATUAL,
     "Data_Vencimento": (_HOJE - pd.Timedelta(days=10)).strftime("%d/%m/%Y"),
     "Cliente": "Cliente Crise Teste", "Obra": "Obra Crise Teste",
     "Total": "20000", "Estado": "Emitida"},
]

_CONTAS_RECORDS = [
    {"ID": "C1", "Nome": "Conta Principal", "Banco": "Banco Teste",
     "Saldo": "50000"},
]

_RH_RECORDS = [{"Nome": "Ana Teste", "Salario_Base": "1200"}]

_RENTING_RECORDS = [
    {"ID": "R1", "Valor_Mensal": "500", "Estado": "Ativo",
     "Data_Fim": (_HOJE + pd.Timedelta(days=30)).strftime("%d/%m/%Y")},
]

_SEGUROS_RECORDS = [
    {"ID": "S1", "Tipo": "Frota",
     "Data_Fim": (_HOJE + pd.Timedelta(days=30)).strftime("%d/%m/%Y"),
     "Valor_Anual": "1200"},
]

_ALVARAS_RECORDS = [
    {"ID": "A1", "Tipo": "Alvará Obra",
     "Data_Validade": (_HOJE + pd.Timedelta(days=45)).strftime("%d/%m/%Y")},
]

_IBAN_HIST_RECORDS = [
    {"ID": "I1", "Data_Alteracao": (_HOJE - pd.Timedelta(days=5)).strftime("%d/%m/%Y"),
     "Entidade": "Fornecedor Teste"},
]


def _fake_load_db(fn, cols, silent=False):
    mapa = {
        "faturas_clientes.csv":    _FATURAS_CLI_RECORDS,
        "contas_bancarias.csv":    _CONTAS_RECORDS,
        "colaboradores_rh.csv":    _RH_RECORDS,
        "renting_contratos.csv":   _RENTING_RECORDS,
        "seguros_db.csv":          _SEGUROS_RECORDS,
        "alvaras_db.csv":          _ALVARAS_RECORDS,
        "iban_historico.csv":      _IBAN_HIST_RECORDS,
    }
    if fn in mapa:
        return pd.DataFrame(mapa[fn])
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_crise import render_fat_crise
    vazio = pd.DataFrame()
    render_fat_crise(vazio, vazio, vazio, vazio)


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_fat_crise.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderFatCriseSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Semáforo, Stress Tests, Simulador E-se?, Altman
    Z-Score, Fontes de Ajuda, Plano Contingência) porque st.tabs()
    desenha o conteúdo de todos de uma vez. Os dados de teste
    incluem seguro, alvará, IBAN e renting a expirar/alterado
    recentemente, de propósito, para exercitar os 4 tipos de Alerta
    Operacional."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Testes do módulo de Tesouraria & Cash Flow (mod_fat_tesouraria.py) —
Cash Flow 90 Dias, Contas Bancárias, Reconciliação Bancária, Fundo de
Maneio, Previsão IA.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 5
gráficos Plotly (Cash Flow 90 Dias, Resumo Semanal, Saldo por Conta,
Reconciliação, Fundo de Maneio por Obra).

Não tocam em GCS real nem na API Anthropic: `mod_fat_tesouraria.load_db`
é mockado diretamente (devolve DataFrames de teste, consoante o
ficheiro pedido); `core._gcs_read` mockado a devolver None (usado por
_get_config_empresa, cai no fallback local). A Previsão IA (botão
"Gerar Análise Completa") não é acionada nestes testes — sem
ANTHROPIC_API_KEY no ambiente de testes, _previsao_cashflow_ia devolve
mensagem de erro em vez de chamar a API real.

Correr:  python -m unittest test_mod_fat_tesouraria -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{"Obra": "Obra Tesouraria Teste", "Ativa": "Ativa"}]

_CONTAS_RECORDS = [
    {"ID": "CT1", "Nome": "Conta Principal", "Banco": "CGD",
     "IBAN": "PT50000000000000000000000", "Tipo": "Conta Corrente",
     "Saldo": "15000", "Data_Saldo": "01/08/2026", "Moeda": "EUR",
     "Ativa": "Sim"},
]

_MOVIMENTOS_RECORDS = [
    {"ID": "M1", "Data": "10/08/2026", "Conta": "Conta Principal",
     "Descricao": "Pagamento Fornecedor X", "Valor": "-500",
     "Tipo": "Débito", "Estado": "Por Conciliar", "Fatura_ID": "",
     "Categoria": "Pagamento Fornecedor"},
    {"ID": "M2", "Data": "15/08/2026", "Conta": "Conta Principal",
     "Descricao": "Recebimento Cliente Y", "Valor": "1200",
     "Tipo": "Crédito", "Estado": "Conciliado", "Fatura_ID": "",
     "Categoria": "Recebimento Cliente"},
]

_FATURAS_CLI_RECORDS = [
    {"ID": "F1", "Numero": "FT001", "Data_Emissao": "01/08/2026",
     "Data_Vencimento": "15/09/2026", "Cliente": "Cliente Tesouraria Teste",
     "Obra": "Obra Tesouraria Teste", "Total": "3000", "Estado": "Pendente"},
]

_RH_RECORDS = [{"Nome": "Ana Teste", "Salario_Base": "1200"}]

_RENTING_RECORDS = [
    {"ID": "R1", "Matricula": "AA-11-BB", "Valor_Mensal": "350",
     "Data_Fim": "01/01/2028", "Estado": "Ativo"},
]

_FM_RECORDS = [
    {"ID": "FM1", "Obra": "Obra Tesouraria Teste", "Responsavel": "Bruno Teste",
     "Data": "01/08/2026", "Descricao": "Fundo semana 31",
     "Adiantamento": "500", "Gasto": "200", "Comprovativo_b64": "",
     "Estado": "Em Aberto"},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "contas_bancarias.csv":
        return pd.DataFrame(_CONTAS_RECORDS)
    if fn == "movimentos_bancarios.csv":
        return pd.DataFrame(_MOVIMENTOS_RECORDS)
    if fn == "faturas_clientes.csv":
        return pd.DataFrame(_FATURAS_CLI_RECORDS)
    if fn == "colaboradores_rh.csv":
        return pd.DataFrame(_RH_RECORDS)
    if fn == "renting_contratos.csv":
        return pd.DataFrame(_RENTING_RECORDS)
    if fn == "fundo_maneio.csv":
        return pd.DataFrame(_FM_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(obras_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_tesouraria import render_fat_tesouraria
    render_fat_tesouraria(
        pd.DataFrame(obras_records), pd.DataFrame(),
        pd.DataFrame(), pd.DataFrame())


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_fat_tesouraria.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(_OBRAS_RECORDS,), default_timeout=30)
        at.run()
    return at


class TestRenderFatTesourariaSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 5 separadores (Cash Flow 90 Dias, Contas Bancárias,
    Reconciliação Bancária, Fundo de Maneio, Previsão IA) porque
    st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

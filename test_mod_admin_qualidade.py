"""
Testes do módulo de Gestão da Qualidade (mod_admin_qualidade.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério dos gráficos
Plotly): o gráfico de barras "NCs por Gravidade" na aba Indicadores
— inclui um dicionário de cores próprio (cores_g), separado do que
alimenta os cartões HTML (cor_g), usado só para colorir as barras.

Não tocam em GCS real: `mod_admin_qualidade.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_admin_qualidade -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_NC_RECORDS = [
    {"ID": "NC1", "Data": "01/01/2026", "Obra": "Obra Qualidade Teste",
     "Reportado_Por": "Ana Teste", "Tipo": "Processo",
     "Descricao": "Solda fora da especificação", "Gravidade": "Crítica",
     "Status": "Aberta", "Causa_Raiz": "Falta de formação",
     "Acao_Corretiva": "Reforçar formação da equipa",
     "Responsavel_AC": "Bruno Teste", "Prazo_AC": "10/01/2026",
     "Data_Fecho": "", "Verificado_Por": ""},
    {"ID": "NC2", "Data": "02/01/2026", "Obra": "Obra Qualidade Teste",
     "Reportado_Por": "Ana Teste", "Tipo": "Documental",
     "Descricao": "Registo em falta", "Gravidade": "Menor",
     "Status": "Fechada", "Causa_Raiz": "", "Acao_Corretiva": "",
     "Responsavel_AC": "", "Prazo_AC": "", "Data_Fecho": "05/01/2026",
     "Verificado_Por": "Admin"},
]

_INSP_RECORDS = [{
    "ID": "I1", "Data": "01/01/2026", "Obra": "Obra Qualidade Teste",
    "Tipo_Inspecao": "Inspeção Final", "Realizado_Por": "Ana Teste",
    "Resultado": "Não Conforme", "Obs": "Falha detetada no acabamento",
    "Status": "Fechado", "Evidencias_b64": "",
}]

_DOCS_RECORDS = [{
    "ID": "D1", "Codigo": "PGQ-001", "Titulo": "Procedimento de Soldadura",
    "Revisao": "Rev. A", "Data_Emissao": "01/01/2026",
    "Data_Revisao": "01/01/2026", "Tipo": "Procedimento",
    "Responsavel": "Admin", "Status": "Em vigor", "Ficheiro_b64": "",
}]

_OBRAS_RECORDS = [{"Obra": "Obra Qualidade Teste", "Ativa": "Ativa"}]


def _fake_load_db(fn, cols, silent=False):
    if fn == "nao_conformidades.csv":
        return pd.DataFrame(_NC_RECORDS)
    if fn == "inspecoes_qualidade.csv":
        return pd.DataFrame(_INSP_RECORDS)
    if fn == "documentos_sgq.csv":
        return pd.DataFrame(_DOCS_RECORDS)
    if fn == "obras_lista.csv":
        return pd.DataFrame(_OBRAS_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_qualidade import render_qualidade
    render_qualidade()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_admin_qualidade.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderQualidadeSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 5 separadores (Não Conformidades, Nova NC, Inspeções, Docs
    SGQ, Indicadores) porque st.tabs() desenha o conteúdo de todos de
    uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

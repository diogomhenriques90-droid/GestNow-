"""
Testes do módulo Planeamento e Engenharia (mod_admin_planeamento.py)
— Fase 3 da Identidade Visual: migração para o THEME central
(core.py), em vez de hexadecimais soltos.

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
}, {
    "ID": "P2", "Obra": "Obra Teste", "Frente": "Frente B",
    "Descricao": "Calibração concluída", "Horas_Plan": "10",
    "Horas_Reais": "10", "Data_Inicio": "01/01/2026", "Data_Fim": "05/01/2026",
    "Status": "Concluído", "Criado_Por": "Admin",
}]

_MILESTONES_RECORDS = [{
    "ID": "M1", "Obra": "Obra Teste", "Descricao": "Entrega Fase 1",
    "Data_Alvo": "15/02/2026", "Responsavel": "Ana Teste", "Status": "Pendente",
}, {
    "ID": "M2", "Obra": "Obra Teste", "Descricao": "Comissionamento em risco",
    "Data_Alvo": "01/03/2026", "Responsavel": "Ana Teste", "Status": "Em Risco",
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


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin_planeamento.py lê as
    suas cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados nos cartões de
    pacote de trabalho e de milestone."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary",
                      "accent", "success", "warning", "error"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#6B7280", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

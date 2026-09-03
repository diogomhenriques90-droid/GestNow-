"""
Testes do módulo ISO 9001:2015 (mod_iso9001.py) — Objetivos, Gestão
de Riscos, Partes Interessadas, Auditorias Internas, Revisão pela
Gestão, Avaliação de Fornecedores.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 5
gráficos Plotly (Matriz de Risco, Progresso dos Objetivos, Radar de
Cláusulas, Matriz Influência × Interesse, Score de Fornecedores) e o
PDF da Revisão pela Gestão (reportlab). A "Análise IA do SGQ" não é
acionada nestes testes.

Não tocam em GCS real: `mod_iso9001.load_db` é mockado diretamente
(devolve DataFrames de teste, consoante o ficheiro pedido).

Correr:  python -m unittest test_mod_iso9001 -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBJ_RECORDS = [
    {"ID": "O1", "Ano": "2026", "Objetivo": "Reduzir NCs em 20%",
     "Indicador": "Nº de NCs", "Meta": "10", "Unidade": "un",
     "Progresso": "6", "Responsavel": "Ana Teste",
     "Prazo": "31/12/2026", "Status": "Em Curso", "Notas": ""},
]

_RISCOS_RECORDS = [
    {"ID": "R1", "Data": "01/01/2026", "Processo": "Produção / Obras",
     "Descricao": "Falha de equipamento crítico", "Tipo": "Risco",
     "Probabilidade": "Alto", "Impacto": "Alto", "Score": "16",
     "Tratamento": "Manutenção preventiva", "Responsavel": "Bruno Teste",
     "Prazo": "01/09/2026", "Status": "Aberto", "Residual": ""},
]

_PARTES_RECORDS = [
    {"ID": "P1", "Nome": "Cliente Refinaria", "Tipo": "Cliente",
     "Expectativas": "Qualidade", "Requisitos": "Prazo",
     "Nivel_Influencia": "Alto", "Nivel_Interesse": "Alto",
     "Acao": "Reuniões mensais", "Responsavel": "Admin"},
]

_AUD_RECORDS = [
    {"ID": "A1", "Data_Planeada": "15/03/2026", "Data_Real": "15/03/2026",
     "Tipo": "Auditoria Interna ISO 9001", "Auditor": "Ana Teste",
     "Clausulas": "8 - Operação, 9 - Avaliação Desempenho",
     "Scope": "Produção", "Resultado": "Conforme c/ Obs.",
     "Achados": "Pequenos desvios", "NCs_Aber": "1", "NCs_Men": "2",
     "Obs_Positivas": "3", "Status": "Concluída", "Relatorio_b64": ""},
]

_FORN_AVAL_RECORDS = [
    {"ID": "FA1", "Fornecedor": "Fornecedor ISO Teste",
     "Data_Aval": "01/02/2026", "Obra": "Obra ISO Teste",
     "Categoria": "Materiais", "Q_Qualidade": "4", "Q_Prazo": "3",
     "Q_Preco": "3", "Q_Comunicacao": "4", "Q_Documentacao": "5",
     "Score_Total": "75", "Classificacao": "✅ Qualificado",
     "Acao": "Manter", "Avaliado_Por": "Admin", "Notas": ""},
]

_NC_RECORDS = [
    {"ID": "NC1", "Data": "01/01/2026", "Obra": "Obra ISO Teste",
     "Tipo": "Processo", "Gravidade": "Média", "Status": "Aberta",
     "Descricao": "Registo em falta", "Causa_Raiz": "",
     "Acao_Corretiva": "", "Prazo_AC": ""},
]

_INSP_RECORDS = [
    {"ID": "I1", "Data": "01/01/2026", "Obra": "Obra ISO Teste",
     "Tipo_Inspecao": "Final", "Resultado": "Conforme"},
]

_FORNECEDORES_RECORDS = [{"ID": "F1", "Nome": "Fornecedor ISO Teste"}]
_OBRAS_RECORDS = [{"Obra": "Obra ISO Teste", "Ativa": "Ativa"}]


def _fake_load_db(fn, cols, silent=False):
    mapa = {
        "iso_objetivos.csv": _OBJ_RECORDS,
        "iso_riscos.csv": _RISCOS_RECORDS,
        "iso_partes_interessadas.csv": _PARTES_RECORDS,
        "iso_auditorias.csv": _AUD_RECORDS,
        "iso_fornecedores_aval.csv": _FORN_AVAL_RECORDS,
        "nao_conformidades.csv": _NC_RECORDS,
        "inspecoes_qualidade.csv": _INSP_RECORDS,
        "fornecedores.csv": _FORNECEDORES_RECORDS,
        "obras_lista.csv": _OBRAS_RECORDS,
    }
    if fn in mapa:
        return pd.DataFrame(mapa[fn])
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_iso9001 import render_iso9001
    render_iso9001()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_iso9001.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderIso9001SemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Objetivos, Gestão de Riscos, Partes
    Interessadas, Auditorias Internas, Revisão pela Gestão, Avaliação
    Fornecedores) porque st.tabs() desenha o conteúdo de todos de uma
    vez. O risco de teste tem Score 16 (≥12) de propósito, para
    exercitar o expander expandido por omissão e o KPI de riscos
    altos."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_iso9001.py lê as suas cores de
    core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados. O dict `cores_t` (8 tipos
    de Partes Interessadas) e todas as cores dos 5 gráficos Plotly e
    do PDF (reportlab) ficam de fora, de propósito — mesmo critério
    de sempre, Fase 4."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary",
                      "accent", "warning", "success", "error"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("background:#1E293B", textos)
        self.assertNotIn("background: #1E293B", textos)
        self.assertNotIn("background:#0F172A", textos)
        self.assertNotIn("#F1F5F9", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

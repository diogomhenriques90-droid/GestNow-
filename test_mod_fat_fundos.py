"""
Testes do módulo Fundos Europeus & Candidaturas (mod_fat_fundos.py) —
Matcher, Calculadora, Fundos Disponíveis, Gestão Candidaturas, IA
Consultora, Calendário.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 3
gráficos Plotly (Radar Elegibilidade, Timeline Candidaturas,
Calendário/Donut) e o PDF de candidatura (reportlab). A pesquisa IA
não é acionada nestes testes (depende de botões não acionados).

Não tocam em GCS real: `mod_fat_fundos.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_fat_fundos -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_HOJE = pd.Timestamp.today()

_CAND_RECORDS = [
    {"ID": "C1", "Fundo": "PRR — Capitalização e Inovação Empresarial",
     "Programa": "PRR", "Data_Inicio": "01/01/2026",
     "Prazo_Candidatura": (_HOJE + pd.Timedelta(days=10)).strftime("%d/%m/%Y"),
     "Data_Fim": "", "Valor_Investimento": "100000",
     "Valor_Apoio": "50000", "Pct_Apoio": "50",
     "Estado": "Submetido", "Notas": "", "Responsavel": "Admin",
     "Documentos_OK": "Sim"},
    {"ID": "C2", "Fundo": "IEFP — Apoios à Formação Profissional",
     "Programa": "FSE+", "Data_Inicio": "01/01/2026",
     "Prazo_Candidatura": (_HOJE + pd.Timedelta(days=45)).strftime("%d/%m/%Y"),
     "Data_Fim": "", "Valor_Investimento": "20000",
     "Valor_Apoio": "20000", "Pct_Apoio": "100",
     "Estado": "Em Execução", "Notas": "", "Responsavel": "Admin",
     "Documentos_OK": "Sim"},
    {"ID": "C3", "Fundo": "Linha PME Crescimento 2024",
     "Programa": "IAPMEI", "Data_Inicio": "01/01/2026",
     "Prazo_Candidatura": "", "Data_Fim": "",
     "Valor_Investimento": "50000", "Valor_Apoio": "50000",
     "Pct_Apoio": "100", "Estado": "Aprovado", "Notas": "",
     "Responsavel": "Admin", "Documentos_OK": "Sim"},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "fundos_candidaturas.csv":
        return pd.DataFrame(_CAND_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_fundos import render_fat_fundos
    render_fat_fundos()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_fat_fundos.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderFatFundosSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Matcher, Calculadora, Fundos Disponíveis,
    Gestão Candidaturas, IA Consultora, Calendário) porque st.tabs()
    desenha o conteúdo de todos de uma vez. As candidaturas de teste
    incluem um prazo a 10 dias (alerta vermelho), um a 45 dias
    (alerta laranja) e um projeto Em Execução, de propósito, para
    exercitar os alertas de prazo e as Obrigações de Reporte."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_fat_fundos.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados. A cor "cor" por
    fundo (8 fundos, sem semântica boa/má) foi removida de FUNDOS_DB
    e colapsada num acento único, mesmo critério de
    mod_admin_formacoes.py. Os 3 gráficos Plotly e o PDF (reportlab)
    ficam de fora, de propósito — Fase 4."""

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

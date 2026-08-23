"""
Testes do Dashboard Executivo (mod_dashboard.py) — Fase 3 da
Identidade Visual: migração para o THEME central (core.py), em vez de
hexadecimais soltos.

Fora de âmbito, de propósito (Fase 4, mesmo critério dos gráficos
Plotly): as cores dos 4 st.bar_chart() — são cores de gráfico, não
HTML/CSS, e não herdam do tema do Streamlit por serem parâmetros
explícitos.

Não tocam em GCS real: `mod_dashboard.load_db` é mockado diretamente
(usado só pelo cache de instrumentos por obra).

Correr:  python -m unittest test_mod_dashboard -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{
    "Obra": "Obra Dashboard Teste", "Cliente": "Cliente Teste", "Ativa": "Ativa",
}]

_USERS_RECORDS = [{"Nome": "Ana Teste", "Tipo": "Técnico", "Cargo": "Instrumentista"}]

_REGISTOS_RECORDS = [{
    "Técnico": "Ana Teste", "Obra": "Obra Dashboard Teste",
    "Data": "01/01/2026", "Horas_Total": "8", "Status": "1",
}]

_INCS_RECORDS = [{
    "Data": "01/01/2026", "Utilizador": "Ana Teste", "Obra": "Obra Dashboard Teste",
    "Descricao": "Quase-acidente", "Gravidade": "Média", "Status": "Aberto",
    "Tipo": "Incidente",
}]

_INST_RECORDS = [{"Tag": "PT-101", "Status": "3", "Descricao": "Transmissor"}]


def _fake_load_db(fn, cols, silent=False):
    if fn.startswith("inst_") and fn.endswith("_index.csv"):
        return pd.DataFrame(_INST_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(obras_records, users_records, registos_records, incs_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_dashboard import render_dashboard
    vazio = pd.DataFrame()
    # (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
    #  sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
    #  comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
    #  *_) — 24 posições ao todo (load_all()), só as 20 primeiras são lidas.
    render_dashboard(
        pd.DataFrame(users_records), pd.DataFrame(obras_records), vazio,
        pd.DataFrame(registos_records), vazio, vazio, pd.DataFrame(incs_records),
        vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio,
    )


def _run(obras_records=None, users_records=None, registos_records=None,
         incs_records=None, load_db_fn=_fake_load_db):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    users_records = users_records if users_records is not None else _USERS_RECORDS
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    incs_records = incs_records if incs_records is not None else _INCS_RECORDS
    core._cached_load_db.clear()
    with patch("mod_dashboard.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, users_records, registos_records, incs_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderDashboardSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 4 separadores de gráficos (Progresso por Obra, Horas por
    Semana, Incidentes, Ranking Técnicos) porque st.tabs() desenha o
    conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], users_records=[], registos_records=[],
                   incs_records=[], load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_dashboard.py lê as suas cores
    de core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados no cabeçalho, cartões KPI
    (.kpi-card), previsões e atividades recentes."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        for chave in ("surface", "border", "accent", "text_secondary"):
            self.assertIn(core.THEME[chave], css)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#F8FAFC", textos)
        self.assertNotIn("#60A5FA", textos)

    def test_atividades_recentes_usam_theme(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["success"], textos)  # última validação
        self.assertIn(core.THEME["accent"], textos)   # última instalação


if __name__ == "__main__":
    unittest.main(verbosity=2)

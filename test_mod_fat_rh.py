"""
Testes do módulo RH Financeiro (mod_fat_rh.py) — Colaboradores, Mapa
Remunerações, Recibos Vencimento, Férias & Subsídios, Provisões, Mapa
IRS/SS.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 5
gráficos Plotly (Custo Real Waterfall, Mapa de Remunerações,
Calendário de Férias, Provisões Acumuladas, Breakdown Custo RH) e o
PDF de recibo de vencimento (reportlab). Os recibos (individual/ZIP)
e o DRI não são gerados nestes testes (dependem de botões não
acionados).

Não tocam em GCS real: `mod_fat_rh.load_db` é mockado diretamente
(devolve DataFrames de teste, consoante o ficheiro pedido);
`core._gcs_read` mockado a devolver None (usado por
_load_users_fresh e _get_config_empresa, cai no fallback local —
sem utilizadores pré-registados, a ficha usa o campo de texto livre).

Correr:  python -m unittest test_mod_fat_rh -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{"Obra": "Obra RH Teste", "Ativa": "Ativa"}]

_RH_RECORDS = [
    {"ID": "R1", "Nome": "Ana Teste", "NIF": "123456789",
     "NISS": "11111111111", "Tipo": "Técnico", "Cargo": "Instrumentista",
     "Salario_Base": "1200", "Data_Inicio": "01/01/2024",
     "Estado_Civil": "Solteiro(a)", "N_Dependentes": "0",
     "Banco_IBAN": "PT50000000000000000000000", "Contrato": "Sem Termo",
     "Ativo": "Sim"},
]

_FERIAS_RECORDS = [
    {"ID": "F1", "Colaborador": "Ana Teste", "Data_Inicio": "01/07/2026",
     "Data_Fim": "05/07/2026", "Dias_Uteis": "5", "Estado": "Aprovado",
     "Aprovado_Por": "Admin", "Obra": "Obra RH Teste"},
]


def _fake_load_db(fn, cols, silent=False):
    mapa = {
        "colaboradores_rh.csv": _RH_RECORDS,
        "ferias_db.csv": _FERIAS_RECORDS,
    }
    if fn in mapa:
        return pd.DataFrame(mapa[fn])
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(obras_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_rh import render_fat_rh
    render_fat_rh(pd.DataFrame(obras_records), pd.DataFrame())


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_fat_rh.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(_OBRAS_RECORDS,), default_timeout=30)
        at.run()
    return at


class TestRenderFatRhSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Colaboradores, Mapa Remunerações, Recibos
    Vencimento, Férias & Subsídios, Provisões, Mapa IRS/SS) porque
    st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_fat_rh.py lê as suas cores de
    core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados."""

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

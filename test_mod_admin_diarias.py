"""
Testes da grelha "⚙️ Valor da Diária por Obra" (mod_admin_diarias.py,
sub-aba de Faturação).

Bloqueia primeiro o comportamento ATUAL (só "Obra" / "€ / Dia" / "Ativa")
antes da Fase 2 do Painel de Obra (campos operacionais) acrescentar
"Modalidade" (Corrida Semanal / Outro) à mesma grelha.

Não tocam em GCS real: `mod_admin_diarias._gcs_read` é mockado (devolve
None por omissão — usa os fallbacks já existentes no módulo).

`st.data_editor` mapeia para o mesmo tipo de elemento que `st.dataframe`
no AppTest — acede-se via `at.dataframe`, filtrando por `.key`.

Correr:  python -m unittest test_mod_admin_diarias -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

_OBRAS_RECORDS = [{"Obra": "Obra Teste Diarias", "Cliente": "Cliente X", "Ativa": "Ativa"}]

# render_admin_diarias(*args) espera 23 posicionais quando len(args)>=23:
# users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
# sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
# comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db,
# inst_acessos_db, diarias_config, diarias_faltas, diarias_pagamentos.


def _script(obras_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_diarias import render_admin_diarias
    vazio = pd.DataFrame()
    obras_db = pd.DataFrame(obras_records)
    render_admin_diarias(
        vazio, obras_db, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio
    )


def _run():
    with patch("mod_admin_diarias._gcs_read", return_value=None):
        at = AppTest.from_function(_script, args=(_OBRAS_RECORDS,), default_timeout=30)
        at.run()
    return at


def _grelha_config(at):
    return next(d for d in at.dataframe if d.key == "data_editor_diarias_config")


class TestConfigurarValoresAtual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.at = _run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_grelha_nao_tem_modalidade(self):
        grelha = _grelha_config(self.at)
        self.assertEqual(list(grelha.value.columns), ["Obra", "€ / Dia", "Ativa"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

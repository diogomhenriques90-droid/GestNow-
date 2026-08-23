"""
Testes do módulo Gestão de Obras (mod_admin_obras.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Não tocam em GCS real: `mod_admin_obras.load_db` é mockado
diretamente (devolve DataFrames vazios ou de teste, consoante o
ficheiro pedido).

Correr:  python -m unittest test_mod_admin_obras -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{
    "Obra": "Obra Teste", "Cliente": "Cliente Teste", "Codigo": "TESTE-001",
    "TipoObra": "Normal", "Local": "Sines", "Ativa": "Ativa",
    "DataInicio": "01/01/2026", "DataFim": "", "Responsavel_Equipa": "",
    "Alojamento": "", "Viatura": "", "Ferramentas": "", "EPIs": "",
    "Plataforma": "", "Descricao_Trabalhos": "",
}]

_USERS_RECORDS = [{
    "Nome": "Ana Teste", "Cargo": "Instrumentista", "PrecoHora": "15",
    "Funcao": "", "Categoria_Operacional": "",
}]

_INST_ACESSOS_RECORDS = [{
    "Obra": "Obra Teste", "Utilizador": "Ana Teste", "Cargo": "Instrumentista",
    "PrecoHora": "15", "Ativo": "Sim", "Data_Aloc": "01/01/2026",
}]

_OBRAS_HISTORICO_RECORDS = [{
    "Obra": "Obra Antiga", "Cliente": "Cliente Antigo", "TipoObra": "Normal",
    "Local": "Lisboa", "DataInicio": "01/01/2025", "DataFecho": "01/06/2025",
    "Fechada_Por": "Admin",
}]


def _fake_load_db(fn, cols, silent=False):
    if fn == "obras_historico.csv":
        return pd.DataFrame(_OBRAS_HISTORICO_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(obras_records, users_records, inst_acessos_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_obras import render_obras
    render_obras(
        pd.DataFrame(obras_records),
        pd.DataFrame(),
        pd.DataFrame(users_records),
        pd.DataFrame(inst_acessos_records),
    )


def _run(obras_records=None, users_records=None, inst_acessos_records=None,
         load_db_fn=_fake_load_db):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    users_records = users_records if users_records is not None else _USERS_RECORDS
    inst_acessos_records = inst_acessos_records if inst_acessos_records is not None else _INST_ACESSOS_RECORDS
    core._cached_load_db.clear()
    with patch("mod_admin_obras.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, users_records, inst_acessos_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderObrasSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 3 separadores (Obras, Alocações, Histórico) porque st.tabs()
    desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], users_records=[], inst_acessos_records=[],
                   load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

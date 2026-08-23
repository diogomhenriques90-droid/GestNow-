"""
Testes do módulo de Gestão de Armazém (mod_armazem.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito: _badge_status() (dicionário de 5 cores
de estado) está definida mas nunca é chamada em lado nenhum do render
— código morto, sem impacto visual, não faz parte desta migração.

Nota de comportamento pré-existente (não é bug introduzido por esta
migração): se req_epi_db/req_fer_db/req_mat_db vier vazio, o
`return` dentro do sub-separador "Pendentes" sai da função inteira —
os separadores seguintes (Ferramentas, Materiais, Receção, Compras)
nem chegam a renderizar. Por isso os testes "sem dados" usam
DataFrames com as colunas certas mas sem linhas (tal como load_all()
devolveria), não None nem [].

A aba "🛒 Compras" lazy-importa mod_admin_compras.py (módulo
independente, ainda não migrado) — para isolar o teste deste módulo,
`mod_armazem.render_compras`... na verdade o import é feito dentro da
função (`from mod_admin_compras import render_compras`), por isso
mockamos ao nível do módulo importado.

Correr:  python -m unittest test_mod_armazem -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_EPI_COLS = ["ID","Item","Solicitante","Obra","Tamanho","Quantidade",
             "Data","Status","Data_Validacao","Validado_Por"]
_FER_COLS = ["ID","Descricao","Solicitante","Obra","Urgencia","Data",
             "Foto_b64","Status","Data_Validacao","Validado_Por"]
_MAT_COLS = ["ID","Descricao","Solicitante","Obra","Quantidade","Unidade",
             "Urgencia","Tipo","Status","Data_Validacao","Validado_Por"]

_REQ_EPI_RECORDS = [
    {"ID": "E1", "Item": "Capacete", "Solicitante": "Ana Teste",
     "Obra": "Obra Armazem Teste", "Tamanho": "M", "Quantidade": "1",
     "Data": "01/01/2026", "Status": "Pendente",
     "Data_Validacao": "", "Validado_Por": ""},
    {"ID": "E2", "Item": "Luvas", "Solicitante": "Bruno Teste",
     "Obra": "Obra Armazem Teste", "Tamanho": "L", "Quantidade": "2",
     "Data": "01/01/2026", "Status": "Aprovado",
     "Data_Validacao": "02/01/2026", "Validado_Por": "Admin"},
    {"ID": "E3", "Item": "Botas", "Solicitante": "Carla Teste",
     "Obra": "Obra Armazem Teste", "Tamanho": "40", "Quantidade": "1",
     "Data": "01/01/2026", "Status": "Enviado",
     "Data_Validacao": "02/01/2026", "Validado_Por": "Admin"},
]

_REQ_FER_RECORDS = [
    {"ID": "F1", "Descricao": "Berbequim", "Solicitante": "Ana Teste",
     "Obra": "Obra Armazem Teste", "Urgencia": "Média", "Data": "01/01/2026",
     "Foto_b64": "", "Status": "Pendente",
     "Data_Validacao": "", "Validado_Por": ""},
    {"ID": "F2", "Descricao": "Chave de fendas", "Solicitante": "Bruno Teste",
     "Obra": "Obra Armazem Teste", "Urgencia": "Baixa", "Data": "01/01/2026",
     "Foto_b64": "", "Status": "Aprovado",
     "Data_Validacao": "02/01/2026", "Validado_Por": "Admin"},
]

_REQ_MAT_RECORDS = [
    {"ID": "M1", "Descricao": "Cabo elétrico", "Solicitante": "Ana Teste",
     "Obra": "Obra Armazem Teste", "Quantidade": "10", "Unidade": "m",
     "Urgencia": "Média", "Tipo": "Material", "Status": "Pendente",
     "Data_Validacao": "", "Validado_Por": ""},
    {"ID": "M2", "Descricao": "Parafusos", "Solicitante": "Bruno Teste",
     "Obra": "Obra Armazem Teste", "Quantidade": "100", "Unidade": "un",
     "Urgencia": "Baixa", "Tipo": "Material", "Status": "Aprovado",
     "Data_Validacao": "02/01/2026", "Validado_Por": "Admin"},
]


def _script(req_fer_records, req_mat_records, req_epi_records):
    import streamlit as st
    import pandas as pd
    from unittest.mock import patch
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    fer_cols = ["ID","Descricao","Solicitante","Obra","Urgencia","Data",
                "Foto_b64","Status","Data_Validacao","Validado_Por"]
    mat_cols = ["ID","Descricao","Solicitante","Obra","Quantidade","Unidade",
                "Urgencia","Tipo","Status","Data_Validacao","Validado_Por"]
    epi_cols = ["ID","Item","Solicitante","Obra","Tamanho","Quantidade",
                "Data","Status","Data_Validacao","Validado_Por"]
    with patch("mod_admin_compras.render_compras", return_value=None):
        from mod_armazem import render_armazem
        vazio = pd.DataFrame()
        render_armazem(
            pd.DataFrame(req_fer_records, columns=fer_cols),
            pd.DataFrame(req_mat_records, columns=mat_cols),
            pd.DataFrame(req_epi_records, columns=epi_cols),
            vazio,
        )


def _run(req_fer_records=None, req_mat_records=None, req_epi_records=None):
    req_fer_records = req_fer_records if req_fer_records is not None else _REQ_FER_RECORDS
    req_mat_records = req_mat_records if req_mat_records is not None else _REQ_MAT_RECORDS
    req_epi_records = req_epi_records if req_epi_records is not None else _REQ_EPI_RECORDS
    core._cached_load_db.clear()
    with patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(req_fer_records, req_mat_records, req_epi_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderArmazemSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 5 separadores (EPIs, Ferramentas, Materiais, Receção/Entrega,
    Compras) porque st.tabs() desenha o conteúdo de todos de uma
    vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(req_fer_records=[], req_mat_records=[], req_epi_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Testes do módulo de Perfil do Utilizador (mod_perfil.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Não tocam em GCS real: `mod_perfil.load_db` é mockado diretamente
(devolve um DataFrame com um utilizador de teste).

Correr:  python -m unittest test_mod_perfil -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_USUARIOS_COLS = [
    "Nome","Password","Tipo","Cargo","Email","Telefone","Morada","Localidade",
    "Concelho","Codigo_Postal","Naturalidade","Nacionalidade","NIF","NISS","CC",
    "CC_Validade","DataNasc","Estado_Civil","Sexo","Dependentes","Profissao",
    "Categoria_Profissional","Habilitacoes_Literarias","Contacto_Emergencia",
    "Nome_Emergencia","Grau_Parentesco","Banco_IBAN","Observacoes",
    "Tamanho_Camisola","Tamanho_Calca","Tamanho_Botas",
    "Local","PrecoHora","PrecoHoraStatus","PrecoHoraData",
    "PIN","Foto","Campos_Bloqueados","PDFs_Vistos","PDFs_Validados","PDFs_Validacao_Data"
]

_USUARIO_TESTE = {
    "Nome": "Ana Teste", "Password": "x", "Tipo": "Técnico", "Cargo": "Instrumentista",
    "Email": "ana@teste.pt", "Telefone": "912345678",
}

_REGISTOS_RECORDS = [{
    "Técnico": "Ana Teste", "Obra": "Obra Teste",
    "Data": "01/01/2026", "Horas_Total": "8", "Status": "1",
    "Frente": "Frente A", "Turnos": "1", "Relatorio": "",
}]


def _fake_load_db_com_user(fn, cols, silent=False):
    if fn == "usuarios.csv":
        return pd.DataFrame([_USUARIO_TESTE], columns=_USUARIOS_COLS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_sem_user(fn, cols, silent=False):
    return pd.DataFrame(columns=cols if fn != "usuarios.csv" else _USUARIOS_COLS)


def _script(registos_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Ana Teste'
    st.session_state['tipo'] = 'Técnico'
    st.session_state['cargo'] = 'Instrumentista'
    from mod_perfil import render_perfil
    vazio = pd.DataFrame()
    render_perfil(vazio, vazio, vazio, pd.DataFrame(registos_records))


def _run(registos_records=None, load_db_fn=_fake_load_db_com_user):
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    core._cached_load_db.clear()
    with patch("mod_perfil.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(registos_records,), default_timeout=30)
        at.run()
    return at


class TestRenderPerfilSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados."""

    def test_sem_erro_com_utilizador(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_registos(self):
        at = _run(registos_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_utilizador_nao_encontrado(self):
        at = _run(load_db_fn=_fake_load_db_sem_user)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

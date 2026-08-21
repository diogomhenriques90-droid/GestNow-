"""
Testes do módulo do Chefe de Equipa (mod_chefe.py).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro,
com e sem dados — antes da Fase 2 da Identidade Visual migrar este
módulo (o que tem mais cores à mão da app, 247) para o THEME central
(core.py) e as funções partilhadas render_card()/render_badge().

Não tocam em GCS real: `core._gcs_read` é mockado com um CSV fixo em
memória. `render_chefe` é invocado diretamente (sem passar por
app.py/mod_admin.py).

Correr:  python -m unittest test_mod_chefe -v
"""
import io
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_USUARIOS_CSV = (
    "Nome,Tipo,Cargo,Foto\n"
    "Chefe Teste,Chefe de Equipa,Chefe de Equipa,\n"
    "Ana Alocada,Técnico,Instrumentista,\n"
).encode("utf-8-sig")


def _fake_gcs_read(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_CSV)
    return None


_OBRAS_RECORDS = [{
    "Obra": "Obra Chefe Teste", "Codigo": "OBR-001", "Cliente": "Cliente Teste",
    "Ativa": "Ativa",
}]

_REGISTOS_RECORDS = [{
    "ID": "R1", "Técnico": "Ana Alocada", "Obra": "Obra Chefe Teste",
    "Frente": "Frente A", "Turnos": "08:00-17:00", "Data": "01/01/2026",
    "Horas_Total": "8", "Status": "0", "Relatorio": "",
}]

_INST_ACESSOS_RECORDS = [{
    "Utilizador": "Chefe Teste", "Obra": "Obra Chefe Teste", "Ativo": "Sim",
}]

_REQ_FER_RECORDS = [{
    "ID": "F1", "Solicitante": "Ana Alocada", "Obra": "Obra Chefe Teste",
    "Data": "01/01/2026", "Status": "Pendente", "Descricao": "Chave de fendas",
}]


def _script(obras_records, registos_records, inst_acessos_records, req_fer_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user']  = 'Chefe Teste'
    st.session_state['tipo']  = 'Chefe de Equipa'
    st.session_state['cargo'] = 'Chefe de Equipa'
    from mod_chefe import render_chefe
    vazio = pd.DataFrame()
    args = [
        vazio,                              # users (não usado diretamente; _load_users_cached lê do GCS)
        pd.DataFrame(obras_records),         # obras_db
        vazio,                               # frentes_db
        pd.DataFrame(registos_records),      # registos_db
        vazio, vazio, vazio, vazio, vazio,   # faturas, docs, incs, sw, obs
        vazio, vazio, vazio,                 # equip, diags, diags_u
        vazio, vazio, vazio,                 # folhas, comuns, comuns_u
        pd.DataFrame(req_fer_records),       # req_fer_db
        vazio, vazio,                        # req_mat_db, req_epi_db
        vazio,                               # avals_db
        pd.DataFrame(inst_acessos_records),  # inst_acessos_db
    ]
    render_chefe(*args)


def _run(obras_records=None, registos_records=None, inst_acessos_records=None,
         req_fer_records=None):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    inst_acessos_records = inst_acessos_records if inst_acessos_records is not None \
        else _INST_ACESSOS_RECORDS
    req_fer_records = req_fer_records if req_fer_records is not None else _REQ_FER_RECORDS
    core._cached_load_db.clear()
    core._load_users_cached.clear()
    with patch("core._gcs_read", side_effect=_fake_gcs_read), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, registos_records, inst_acessos_records, req_fer_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderChefeSemErro(unittest.TestCase):
    """Smoke test do comportamento atual — o ecrã renderiza sem erro,
    com e sem dados. Cobre todos os separadores (Equipa, Validar Horas,
    Meu Ponto, Folha de Ponto, HSE, Pedidos) porque st.tabs() desenha o
    conteúdo de todos os separadores de uma vez, independente de qual
    está selecionado."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], registos_records=[],
                   inst_acessos_records=[], req_fer_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

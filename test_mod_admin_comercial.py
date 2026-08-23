"""
Testes do módulo Comercial (mod_admin_comercial.py) — Pipeline,
Visitas, Clientes & Angariações, Ranking, Relatório.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 5
gráficos Plotly (Funil de Vendas, Valor por Stage, Ranking
Comerciais, Visitas por Dia da Semana, Novos Clientes, Taxa
Conversão) e o PDF de relatório comercial (reportlab).

Não tocam em GCS real: `mod_admin_comercial.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido); `core._gcs_read` mockado a devolver None (usado por
_get_config_empresa, cai no fallback local).

Correr:  python -m unittest test_mod_admin_comercial -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OPORT_RECORDS = [
    {"ID": "OP1", "Nome": "Fornecimento Instrumentação",
     "Cliente": "Cliente Comercial Teste", "Setor": "Indústria",
     "Comercial": "Ana Teste", "Stage": "prospeto", "Valor_Est": "5000",
     "Prob_Fecho": "10", "Data_Criacao": "01/01/2026",
     "Data_Fecho_Est": "05/09/2026", "Origem": "Prospecção",
     "Notas": "", "Obra_Associada": "", "Contacto_Origem": ""},
    {"ID": "OP2", "Nome": "Contrato Manutenção Anual",
     "Cliente": "Cliente Comercial Teste", "Setor": "Petroquímica",
     "Comercial": "Bruno Teste", "Stage": "negociacao",
     "Valor_Est": "20000", "Prob_Fecho": "75",
     "Data_Criacao": "01/01/2026", "Data_Fecho_Est": "01/08/2026",
     "Origem": "Referência", "Notas": "", "Obra_Associada": "",
     "Contacto_Origem": ""},
    {"ID": "OP3", "Nome": "Shutdown 2026", "Cliente": "Cliente Ganho",
     "Setor": "Energia", "Comercial": "Ana Teste", "Stage": "ganho",
     "Valor_Est": "15000", "Prob_Fecho": "100",
     "Data_Criacao": "01/01/2026", "Data_Fecho_Est": "01/03/2026",
     "Origem": "Networking", "Notas": "", "Obra_Associada": "",
     "Contacto_Origem": ""},
]

_VISITAS_RECORDS = [
    {"ID": "V1", "Cliente": "Cliente Comercial Teste",
     "Contacto": "Sr. Silva", "Comercial": "Ana Teste",
     "Data": "23/08/2026", "Hora": "10:00", "Tipo": "Visita Presencial",
     "Local": "Sede do cliente", "Oportunidade_ID": "OP1",
     "Estado": "Agendada", "Resultado": "", "Proxima_Acao": "",
     "Notas": ""},
    {"ID": "V2", "Cliente": "Cliente Comercial Teste",
     "Contacto": "Sr. Silva", "Comercial": "Bruno Teste",
     "Data": "24/08/2026", "Hora": "14:00", "Tipo": "Videochamada",
     "Local": "", "Oportunidade_ID": "OP2", "Estado": "Agendada",
     "Resultado": "", "Proxima_Acao": "", "Notas": ""},
    {"ID": "V3", "Cliente": "Cliente Ganho", "Contacto": "Sra. Costa",
     "Comercial": "Ana Teste", "Data": "01/08/2026", "Hora": "09:00",
     "Tipo": "Demo Técnica", "Local": "", "Oportunidade_ID": "OP3",
     "Estado": "Realizada", "Resultado": "Correu bem",
     "Proxima_Acao": "Enviar proposta", "Notas": ""},
]

_CLIENTES_RECORDS = [
    {"ID": "C1", "Nome": "Cliente Comercial Teste", "NIF": "500000000",
     "Setor": "Indústria", "Morada": "", "Email": "geral@teste.pt",
     "Telefone": "912345678", "Contacto": "Sr. Silva",
     "Comercial_Resp": "Ana Teste", "Data_Angariacao": "01/01/2026",
     "Origem": "Prospecção Directa", "Potencial": "Alto", "Notas": ""},
    {"ID": "C2", "Nome": "Cliente Ganho", "NIF": "500000001",
     "Setor": "Energia", "Morada": "", "Email": "",
     "Telefone": "", "Contacto": "Sra. Costa",
     "Comercial_Resp": "Bruno Teste", "Data_Angariacao": "05/01/2026",
     "Origem": "Networking / Evento", "Potencial": "Médio", "Notas": ""},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "comercial_oportunidades.csv":
        return pd.DataFrame(_OPORT_RECORDS)
    if fn == "comercial_visitas.csv":
        return pd.DataFrame(_VISITAS_RECORDS)
    if fn == "comercial_clientes.csv":
        return pd.DataFrame(_CLIENTES_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_comercial import render_comercial
    render_comercial()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_admin_comercial.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderComercialSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 5 separadores (Pipeline, Visitas, Clientes & Angariações,
    Ranking, Relatório) porque st.tabs() desenha o conteúdo de todos
    de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

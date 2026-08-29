"""
Testes do módulo de Secretariado (mod_secretariado.py) — validação de
horas (1ª/2ª), faturação vs folha de ponto, gasóleo e avarias — Fase
3 da Identidade Visual: migração para o THEME central (core.py), em
vez de hexadecimais soltos.

Fora de âmbito, de propósito: _STATUS_COR (dicionário de 4 cores de
estado) está definido mas nunca é usado em lado nenhum do render —
código morto, sem impacto visual, não faz parte desta migração.

render_secretariado() não chama load_db a nível de módulo — todos os
DataFrames vêm como argumentos posicionais (load_all()). A única
exceção é a comparação com a folha extraída por IA (aba Faturação),
que importa `core.load_db` localmente para "folhas_ocr.csv" — por
isso `core._gcs_read` é mockado (devolve None ⇒ DataFrame vazio ⇒
ramo de comparação manual, sem OCR).

Correr:  python -m unittest test_mod_secretariado -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_REGISTOS_COLS = ["ID","Técnico","Obra","Data","Horas_Total","Status",
                  "Frente","Turnos","Validado1_Por","Validado1_Data",
                  "Validado2_Por","Validado2_Data"]
_FOLHAS_COLS = ["Obra","Periodo","Responsavel","Selo","Status"]
_REQ_MAT_COLS = ["ID","Solicitante","Obra","Litros","Valor",
                  "Data_Abastecimento","Tipo","Status","Recibo_b64",
                  "Data_Validacao","Validado_Por"]
_INCS_COLS = ["ID","Solicitante","Obra","Equipamento","Descricao",
              "Urgencia","Valor_Estimado","Tipo","Status","Fatura_b64",
              "Data_Validacao","Validado_Por"]

_REGISTOS_RECORDS = [
    {"ID": "R1", "Técnico": "Ana Teste", "Obra": "Obra Sec Teste",
     "Data": "07/01/2026", "Horas_Total": "8", "Status": "0",
     "Frente": "Frente A", "Turnos": "1"},
    {"ID": "R2", "Técnico": "Bruno Teste", "Obra": "Obra Sec Teste",
     "Data": "07/01/2026", "Horas_Total": "8", "Status": "1",
     "Frente": "Frente A", "Turnos": "1"},
    {"ID": "R3", "Técnico": "Carla Teste", "Obra": "Obra Sec Teste",
     "Data": "07/01/2026", "Horas_Total": "8", "Status": "2",
     "Frente": "Frente A", "Turnos": "1"},
]

_FOLHAS_RECORDS = [
    {"Obra": "Obra Sec Teste", "Periodo": "Semana 1",
     "Responsavel": "Chefe X", "Selo": "OK1", "Status": "Conferido"},
    {"Obra": "Obra Sec Teste", "Periodo": "Semana 2",
     "Responsavel": "Chefe X", "Selo": "OK2", "Status": "Pendente"},
]

_REQ_MAT_RECORDS = [
    {"ID": "G1", "Solicitante": "Ana Teste", "Obra": "Obra Sec Teste",
     "Litros": "40", "Valor": "60", "Data_Abastecimento": "01/01/2026",
     "Tipo": "Gasóleo", "Status": "Pendente", "Recibo_b64": "",
     "Data_Validacao": "", "Validado_Por": ""},
]

_INCS_RECORDS = [
    {"ID": "AV1", "Solicitante": "Bruno Teste", "Obra": "Obra Sec Teste",
     "Equipamento": "Gerador", "Descricao": "Não liga",
     "Urgencia": "Alta", "Valor_Estimado": "150", "Tipo": "Avaria",
     "Status": "Pendente", "Fatura_b64": "",
     "Data_Validacao": "", "Validado_Por": ""},
]


def _script(registos_records, folhas_records, req_mat_records, incs_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    registos_cols = ["ID","Técnico","Obra","Data","Horas_Total","Status",
                      "Frente","Turnos","Validado1_Por","Validado1_Data",
                      "Validado2_Por","Validado2_Data"]
    folhas_cols = ["Obra","Periodo","Responsavel","Selo","Status"]
    req_mat_cols = ["ID","Solicitante","Obra","Litros","Valor",
                     "Data_Abastecimento","Tipo","Status","Recibo_b64",
                     "Data_Validacao","Validado_Por"]
    incs_cols = ["ID","Solicitante","Obra","Equipamento","Descricao",
                 "Urgencia","Valor_Estimado","Tipo","Status","Fatura_b64",
                 "Data_Validacao","Validado_Por"]
    from mod_secretariado import render_secretariado
    vazio = pd.DataFrame()
    # (users, obras_db, frentes_db, registos_db, faturas_db, docs_db,
    #  incs_db, sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db,
    #  comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db,
    #  avals_db, inst_acessos_db, *_) — 20 posições.
    render_secretariado(
        vazio, vazio, vazio,
        pd.DataFrame(registos_records, columns=registos_cols),
        vazio, vazio,
        pd.DataFrame(incs_records, columns=incs_cols),
        vazio, vazio, vazio, vazio, vazio,
        pd.DataFrame(folhas_records, columns=folhas_cols),
        vazio, vazio, vazio,
        pd.DataFrame(req_mat_records, columns=req_mat_cols),
        vazio, vazio, vazio,
    )


def _run(registos_records=None, folhas_records=None, req_mat_records=None,
         incs_records=None):
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    folhas_records = folhas_records if folhas_records is not None else _FOLHAS_RECORDS
    req_mat_records = req_mat_records if req_mat_records is not None else _REQ_MAT_RECORDS
    incs_records = incs_records if incs_records is not None else _INCS_RECORDS
    core._cached_load_db.clear()
    with patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(registos_records, folhas_records, req_mat_records, incs_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderSecretariadoSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (1ª/2ª Validação, Faturação & Folhas, Gasóleo,
    Avarias Frota, Histórico) porque st.tabs() desenha o conteúdo de
    todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(registos_records=[], folhas_records=[],
                   req_mat_records=[], incs_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_secretariado.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros/em tom forçados nos
    cartões de 1ª/2ª validação, folha de ponto, comparação App vs
    Folha, gasóleo e avaria."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary",
                      "accent", "success", "warning", "error"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_em_tom_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("rgba(255,255,255,0.05)", textos)
        self.assertNotIn("rgba(239,68,68,", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Testes do Portal do Cliente (mod_cliente.py) — Fase 3 da Identidade
Visual: migração para o THEME central (core.py), em vez de
hexadecimais soltos.

Não tocam em GCS real: `mod_cliente.load_db` é mockado diretamente
(devolve DataFrames de teste, consoante o ficheiro pedido).

Correr:  python -m unittest test_mod_cliente -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{
    "Obra": "Obra Cliente Teste", "Cliente": "Cliente Teste",
    "TipoObra": "Normal", "Ativa": "Ativa",
}]

_LOGS_RECORDS = [{
    "ID": "L1", "Data": "01/01/2026", "Hora": "10:00", "Usuario": "Admin",
    "Acao": "APROVAR_INSTRUMENTO", "Tabela": "inst_x.csv", "Registro_ID": "PT-101",
    "Detalhes": "Aprovado PT-101 em Obra Cliente Teste", "IP": "",
}]

_INSTS_RECORDS = [{
    "ID": "I1", "Tag": "PT-101", "Tipo": "Pressão", "Descricao": "Transmissor",
    "Status": "3", "GPS_Lat": "", "GPS_Lng": "",
    "Assinatura_Calibracao_b64": "", "Assinatura_Instalacao_b64": "",
    "Hash_Validacao": "",
}]

_PUNCH_RECORDS = [{
    "ID": "PU1", "Data": "01/01/2026", "Autor": "Admin", "Tag": "PT-101",
    "Descricao": "Verificar isolamento", "Prioridade": "Alta", "Estado": "Aberto",
}, {
    "ID": "PU2", "Data": "02/01/2026", "Autor": "Admin", "Tag": "PT-102",
    "Descricao": "Cor da tubagem", "Prioridade": "Baixa", "Estado": "Aberto",
}]


def _fake_load_db(fn, cols, silent=False):
    if fn == "obras_lista.csv":
        return pd.DataFrame(_OBRAS_RECORDS)
    if fn == "logs_audit.csv":
        return pd.DataFrame(_LOGS_RECORDS)
    if fn.startswith("inst_") and fn.endswith("_index.csv"):
        return pd.DataFrame(_INSTS_RECORDS)
    if fn.startswith("punch_"):
        return pd.DataFrame(_PUNCH_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    if fn == "obras_lista.csv":
        return pd.DataFrame(_OBRAS_RECORDS)
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Cliente Teste'
    st.session_state['tipo'] = 'Cliente'
    from mod_cliente import render_cliente_portal
    render_cliente_portal()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_cliente.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderClientePortalSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Resumo, Instrumentos, QR Codes, Aprovações,
    Documentação, Punch List) porque st.tabs() desenha o conteúdo de
    todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_instrumentos_nem_punch(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_obras_associadas(self):
        def _load_sem_obras(fn, cols, silent=False):
            return pd.DataFrame(columns=cols)
        at = _run(load_db_fn=_load_sem_obras)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_cliente.py lê as suas cores de
    core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados no cabeçalho, cartões
    (.cliente-card), atividades recentes e punch list."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        for chave in ("surface", "border", "accent", "radius"):
            self.assertIn(core.THEME[chave], css)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#6B7280", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#F8FAFC", textos)
        self.assertNotIn("rgba(255,255,255,0.05)", textos)

    def test_punch_list_usa_theme(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["error"], textos)
        self.assertIn(core.THEME["success"], textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

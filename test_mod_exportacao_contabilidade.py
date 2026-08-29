"""
Testes do módulo de Exportação para Contabilidade — Eticadata
(mod_exportacao_contabilidade.py, sub-separador "📤 Export
Contabilidade" dentro de Admin → Faturação) — Fase 3 da Identidade
Visual: migração para o THEME central (core.py), em vez de
hexadecimais soltos.

Fora de âmbito, de propósito: o relatório PDF mensal
(_gerar_pdf_mensal, reportlab), mesmo critério das outras Fases.

Não tocam em GCS real: `mod_exportacao_contabilidade.load_db` é
mockado diretamente (devolve DataFrames de teste, consoante o
ficheiro pedido).

Correr:  python -m unittest test_mod_exportacao_contabilidade -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_FAT_CLI_RECORDS = [{
    "ID": "F1", "Numero": "FT1", "Tipo": "Fatura", "Data_Emissao": "15/01/2026",
    "Cliente": "Cliente Teste", "NIF_Cliente": "123456789",
    "Subtotal": "1000", "IVA": "230", "Total": "1230", "Estado": "Emitida",
}]

_HIST_RECORDS = [{
    "ID": "H1", "Mes": "1", "Ano": "2026", "Data_Export": "01/02/2026",
    "N_Lancamentos": "12", "Exportado_Por": "Admin", "Equilibrado": "Sim",
    "Total_Debito": "1230", "Total_Credito": "1230",
}]


def _fake_load_db(fn, cols, silent=False):
    if fn == "faturas_clientes.csv":
        return pd.DataFrame(_FAT_CLI_RECORDS)
    if fn == "historico_exports_cont.csv":
        return pd.DataFrame(_HIST_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_exportacao_contabilidade import render_exportacao_contabilidade
    render_exportacao_contabilidade()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_exportacao_contabilidade.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderExportacaoContabilidadeSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 4 separadores (Exportar Mês, Preview Lançamentos, Plano de
    Contas SNC, Histórico de Exports) porque st.tabs() desenha o
    conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_exportacao_contabilidade.py
    lê as suas cores de core.THEME — nunca mais hexadecimais soltos,
    um só cinzento secundário, sem fundos escuros/em tom forçados no
    cabeçalho, cartões de preview, caixa de Saldo IVA e cartão do
    histórico de exports."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary",
                      "accent", "success"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("rgba(16,185,129,", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

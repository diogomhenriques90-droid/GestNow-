"""
Testes do módulo Fiscal & Compliance (mod_fat_fiscal.py) — IVA, IRC,
Retenções na Fonte, SAF-T, Calendário Fiscal, Segurança Social.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 5
gráficos Plotly (IVA 12 Meses, Decomposição IRC, Mapa de Obrigações
Fiscais, Retenções na Fonte, Contribuições SS) e o PDF do mapa fiscal
(reportlab). O SAF-T XML e a Guia de Retenções PDF não são gerados
nestes testes (dependem de botões não acionados).

Não tocam em GCS real: `mod_fat_fiscal.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_fat_fiscal -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_FATURAS_CLI_RECORDS = [
    {"ID": "F1", "Numero": "FT 2026/1", "Tipo": "FT",
     "Data_Emissao": "05/08/2026", "Cliente": "Cliente Fiscal Teste",
     "NIF_Cliente": "123456789", "Obra": "Obra Fiscal Teste",
     "Subtotal": "40650", "IVA": "9350", "Total": "50000",
     "Estado": "Emitida"},
]

_FATURAS_FORN_RECORDS = [
    {"ID": "FF1", "Data": "05/08/2026", "Fornecedor": "Fornecedor Fiscal Teste",
     "Descricao": "Subempreitada", "Obra": "Obra Fiscal Teste",
     "Subtotal": "500", "IVA": "115", "Total": "615",
     "Retencao_Pct": "25", "Retencao_Val": "125", "Estado": "Pago"},
]

_RH_RECORDS = [{"Nome": "Ana Teste", "Salario_Base": "1200"}]


def _fake_load_db(fn, cols, silent=False):
    mapa = {
        "faturas_clientes.csv": _FATURAS_CLI_RECORDS,
        "faturas_fornecedores.csv": _FATURAS_FORN_RECORDS,
        "colaboradores_rh.csv": _RH_RECORDS,
    }
    if fn in mapa:
        return pd.DataFrame(mapa[fn])
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_fiscal import render_fat_fiscal
    vazio = pd.DataFrame()
    render_fat_fiscal(vazio, vazio, vazio, vazio)


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_fat_fiscal.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderFatFiscalSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (IVA, IRC, Retenções na Fonte, SAF-T, Calendário
    Fiscal, Segurança Social) porque st.tabs() desenha o conteúdo de
    todos de uma vez. A fatura de cliente tem Total elevado (€50.000)
    de propósito, para dar resultado fiscal positivo e exercitar o
    cálculo completo de IRC (não só o ramo resultado ≤ 0)."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_fat_fiscal.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados. As cores por
    tipo de obrigação fiscal (Calendário) e por benefício fiscal
    (IRC) não têm semântica boa/má — colapsadas num acento único,
    mesmo critério de mod_admin_formacoes.py."""

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
        self.assertNotIn("#F1F5F9", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

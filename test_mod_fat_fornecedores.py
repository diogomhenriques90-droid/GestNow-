"""
Testes do módulo de Fornecedores & Subempreiteiros (mod_fat_fornecedores.py)
— Fornecedores, Faturas Recebidas, Subempreiteiros, Aging & Pagamentos,
Retenções na Fonte, Controlo de IBANs.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 4
gráficos Plotly (_grafico_top_fornecedores, _grafico_custos_categoria,
_grafico_aging_fornecedores, _grafico_retencoes_mensal) e o PDF de
Guia de Retenção (reportlab).

Não tocam em GCS real: `mod_fat_fornecedores.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido); `core._gcs_read` mockado a devolver None (usado por
_get_config_empresa, cai no fallback local).

Correr:  python -m unittest test_mod_fat_fornecedores -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{"Obra": "Obra Forn Teste", "Ativa": "Ativa"}]

_FORNECEDORES_RECORDS = [
    {"ID": "F1", "Nome": "Fornecedor Normal", "NIF": "500000000",
     "IBAN": "PT50000000000000000000000", "BIC": "", "Morada": "",
     "Email": "", "Telefone": "", "Categoria": "Material",
     "Condicoes_Pagamento": "30", "Limite_Credito": "10000",
     "Subempreiteiro": "Não", "Retencao_Pct": "0"},
    {"ID": "F2", "Nome": "Subempreiteiro Teste", "NIF": "500000001",
     "IBAN": "PT50000000000000000000001", "BIC": "", "Morada": "",
     "Email": "", "Telefone": "", "Categoria": "Subempreiteiro",
     "Condicoes_Pagamento": "30", "Limite_Credito": "5000",
     "Subempreiteiro": "Sim", "Retencao_Pct": "25"},
]

_FATURAS_RECORDS = [
    {"ID": "FF1", "Data": "01/01/2026", "Data_Vencimento": "31/01/2026",
     "Fornecedor": "Fornecedor Normal", "NIF_Fornecedor": "",
     "Numero_Fatura": "NF1", "Descricao": "Material diverso",
     "Obra": "Obra Forn Teste", "Categoria": "Material",
     "Subtotal": "100", "IVA": "23", "Total": "123",
     "Retencao_Pct": "0", "Retencao_Val": "0", "Estado": "Pendente",
     "PDF_b64": "", "Aprovado_Por": "", "Pago_Em": ""},
    {"ID": "FF2", "Data": "10/08/2026", "Data_Vencimento": "10/09/2026",
     "Fornecedor": "Subempreiteiro Teste", "NIF_Fornecedor": "",
     "Numero_Fatura": "NF2", "Descricao": "Serviço de subempreitada",
     "Obra": "Obra Forn Teste", "Categoria": "Subempreiteiro",
     "Subtotal": "1000", "IVA": "230", "Total": "1230",
     "Retencao_Pct": "25", "Retencao_Val": "250", "Estado": "Aprovado",
     "PDF_b64": "", "Aprovado_Por": "", "Pago_Em": ""},
]

_IBAN_HIST_RECORDS = [
    {"ID": "H1", "Entidade": "Fornecedor Normal", "Tipo": "Fornecedor",
     "Data_Alteracao": "10/08/2026", "IBAN_Anterior": "PT50OLD",
     "IBAN_Novo": "PT50000000000000000000000", "Alterado_Por": "Admin"},
    # Exatamente 30 dias antes de "hoje" (23/08/2026) — dias_alt=30,
    # bloqueado=False (dias_alt<30), exercita o ramo "Desbloqueado".
    {"ID": "H2", "Entidade": "Subempreiteiro Teste", "Tipo": "Fornecedor",
     "Data_Alteracao": "24/07/2026", "IBAN_Anterior": "PT50OLD2",
     "IBAN_Novo": "PT50000000000000000000001", "Alterado_Por": "Admin"},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "fornecedores.csv":
        return pd.DataFrame(_FORNECEDORES_RECORDS)
    if fn == "faturas_fornecedores.csv":
        return pd.DataFrame(_FATURAS_RECORDS)
    if fn == "iban_historico.csv":
        return pd.DataFrame(_IBAN_HIST_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(obras_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_fornecedores import render_fat_fornecedores
    render_fat_fornecedores(pd.DataFrame(obras_records))


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_fat_fornecedores.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(_OBRAS_RECORDS,), default_timeout=30)
        at.run()
    return at


class TestRenderFatFornecedoresSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Fornecedores, Faturas Recebidas, Subempreiteiros,
    Aging & Pagamentos, Retenções na Fonte, Controlo de IBANs) porque
    st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_fat_fornecedores.py lê as
    suas cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados nos cartões de
    Fornecedor/Subempreiteiro, faturas, retenções e IBANs."""

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
        self.assertNotIn("#475569", textos)
        self.assertNotIn("#6B7280", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("background:#1E293B", textos)
        self.assertNotIn("background: #1E293B", textos)
        self.assertNotIn("#F1F5F9", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

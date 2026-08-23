"""
Testes do módulo de Gestão de Compras (mod_admin_compras.py, aba
"🛒 Compras" dentro de Admin → Armazém) — Fase 3 da Identidade
Visual: migração para o THEME central (core.py), em vez de
hexadecimais soltos.

Fora de âmbito, de propósito (Fase 4, mesmo critério dos gráficos
Plotly): o gráfico de pizza "Compras por Categoria" (Histórico) e o
gráfico de barras "Top Fornecedores" (Fornecedores) — não herdam do
tema do Streamlit, precisam da sua própria paleta partilhada em
código à parte.

Não tocam em GCS real: `mod_admin_compras.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_admin_compras -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_COMPRAS_RECORDS = [
    {"ID": "C1", "Data": "01/01/2026", "Solicitante": "Ana Teste",
     "Obra": "Obra Compras Teste", "Fornecedor": "Würth",
     "Descricao": "Cabo XLR 10m", "Quantidade": "5", "Unidade": "un",
     "Valor_Unit": "10", "Total": "50", "Categoria": "Materiais",
     "Urgencia": "Urgente", "Status": "Pendente",
     "Data_Aprovacao": "", "Aprovado_Por": "", "Numero_Fatura": "",
     "Notas": "Precisa até sexta", "Fatura_b64": ""},
    {"ID": "C2", "Data": "01/01/2026", "Solicitante": "Bruno Teste",
     "Obra": "Obra Compras Teste", "Fornecedor": "Amazon",
     "Descricao": "Parafusos", "Quantidade": "100", "Unidade": "un",
     "Valor_Unit": "0.1", "Total": "10", "Categoria": "Materiais",
     "Urgencia": "Baixa", "Status": "Aprovado",
     "Data_Aprovacao": "02/01/2026", "Aprovado_Por": "Admin",
     "Numero_Fatura": "", "Notas": "", "Fatura_b64": ""},
    {"ID": "C3", "Data": "01/01/2026", "Solicitante": "Carla Teste",
     "Obra": "Obra Compras Teste", "Fornecedor": "Leroy Merlin",
     "Descricao": "Fita isoladora", "Quantidade": "10", "Unidade": "un",
     "Valor_Unit": "2", "Total": "20", "Categoria": "Materiais",
     "Urgencia": "Baixa", "Status": "Pendente",
     "Data_Aprovacao": "", "Aprovado_Por": "", "Numero_Fatura": "",
     "Notas": "", "Fatura_b64": ""},
]

_OBRAS_RECORDS = [{"Obra": "Obra Compras Teste", "Ativa": "Ativa"}]

_FORN_RECORDS = [{
    "ID": "F1", "Nome": "Würth", "NIF": "123456789",
    "Email": "geral@wurth.pt", "Telefone": "911111111",
    "Categoria": "Materiais", "Prazo_Entrega": "2-3 dias úteis",
    "Notas": "", "Ativo": "Sim",
}]


def _fake_load_db(fn, cols, silent=False):
    if fn == "compras.csv":
        return pd.DataFrame(_COMPRAS_RECORDS)
    if fn == "obras_lista.csv":
        return pd.DataFrame(_OBRAS_RECORDS)
    if fn == "fornecedores_compras.csv":
        return pd.DataFrame(_FORN_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_compras import render_compras
    render_compras()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_admin_compras.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderComprasSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 4 separadores (Pendentes, Nova Compra, Histórico, Fornecedores)
    porque st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin_compras.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros/em tom forçados no banner
    de pendentes e nos cartões de detalhe/total/notas de cada
    compra pendente."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary",
                      "warning", "error", "success"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#6B7280", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_em_tom_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("rgba(245,158,11,", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

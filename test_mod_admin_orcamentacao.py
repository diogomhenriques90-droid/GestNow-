"""
Testes do módulo de Orçamentação (mod_admin_orcamentacao.py) — CPS
Orçamentação Pro (Tipo A Instrumentação, Tipo B Cedência de Mão de
Obra, Orçamento de Arquivo).

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): o
Funil de Conversão, o gráfico de pizza "Motivos de Rejeição" e o
gráfico de barras "Orçamentos por Mês" (todos Plotly, aba Analytics).

Não tocam em GCS real: `mod_admin_orcamentacao.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_admin_orcamentacao -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [
    {"Obra": "Obra Orc Teste", "Cliente": "Cliente Orc", "Ativa": "Ativa",
     "Tipo": "Normal", "Localizacao": "Sines"},
]

_ORC_RECORDS = [
    {"ID": "ORC1", "Obra": "Obra Orc Teste", "Cliente": "Cliente Orc",
     "Tipo": "A", "Versao": "1", "Data": "01/01/2026", "Criado_Por": "Admin",
     "Status": "Enviado", "Validade": "10/01/2026",
     "Total_Mao_Obra": "1000", "Total_Materiais": "200",
     "Total_Equipamentos": "0", "Total_Deslocacoes": "0",
     "Total_Dormidas": "0", "Total_Diarias": "0", "Margem_Pct": "20",
     "Total_Sem_Margem": "1200", "Total_Com_Margem": "1440",
     "Motivo_Rejeicao": "", "Notas": "Nota teste", "Versao_Pai": "",
     "Oportunidade_ID": "", "Anexos": "", "Origem": ""},
    {"ID": "ORC2", "Obra": "Obra Orc Teste", "Cliente": "Cliente Orc",
     "Tipo": "B", "Versao": "1", "Data": "05/01/2026", "Criado_Por": "Admin",
     "Status": "Adjudicado", "Validade": "01/03/2026",
     "Total_Mao_Obra": "3000", "Total_Materiais": "0",
     "Total_Equipamentos": "0", "Total_Deslocacoes": "300",
     "Total_Dormidas": "400", "Total_Diarias": "200", "Margem_Pct": "15",
     "Total_Sem_Margem": "3900", "Total_Com_Margem": "4485",
     "Motivo_Rejeicao": "", "Notas": "", "Versao_Pai": "",
     "Oportunidade_ID": "", "Anexos": "", "Origem": ""},
    {"ID": "ORC3", "Obra": "Obra Orc Teste", "Cliente": "Cliente Orc",
     "Tipo": "A", "Versao": "1", "Data": "03/01/2026", "Criado_Por": "Admin",
     "Status": "Rejeitado", "Validade": "01/02/2026",
     "Total_Mao_Obra": "500", "Total_Materiais": "0",
     "Total_Equipamentos": "0", "Total_Deslocacoes": "0",
     "Total_Dormidas": "0", "Total_Diarias": "0", "Margem_Pct": "25",
     "Total_Sem_Margem": "500", "Total_Com_Margem": "625",
     "Motivo_Rejeicao": "Preço acima do mercado", "Notas": "",
     "Versao_Pai": "", "Oportunidade_ID": "", "Anexos": "", "Origem": ""},
]

_ORC_LINHAS_RECORDS = [
    {"ID": "L1", "Orcamento_ID": "ORC1", "Descricao": "Transmissor pressão",
     "Categoria": "Mão de Obra", "Quantidade": "2", "Unidade": "un",
     "Minutos_Unit": "60", "Preco_Unit": "80", "Total": "160", "Notas": ""},
]

_CATALOGO_RECORDS = [
    {"ID": "C1", "Categoria": "Instrumentação", "Descricao": "Transmissor pressão",
     "Unidade": "un", "Minutos_Unit": "60", "Preco_Sugerido": "80",
     "Vezes_Usado": "3", "Activo": "Sim", "Data_Actualizacao": "01/01/2026"},
]

_TARIFAS_RECORDS = [
    {"ID": "T1", "Categoria": "Instrumentista", "Zona": "Portugal",
     "Valor_Hora": "12", "Horas_Dia": "8", "Diaria": "20",
     "Data_Actualizacao": "01/01/2026"},
]

_REF_PRECOS_RECORDS = [
    {"ID": "R1", "Tipo": "dormida", "Descricao": "Hotel padrão",
     "Valor_Dia": "60", "Capacidade": "", "Fonte": "",
     "Data_Actualizacao": "01/01/2026"},
]

_CLIENTES_RECORDS = [
    {"ID": "CL1", "Cliente": "Cliente Orc", "Contacto": "", "Email": "",
     "Telefone": "", "Setor": "", "Pais": "Portugal", "Notas": ""},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "orcamentos.csv":
        return pd.DataFrame(_ORC_RECORDS)
    if fn == "orcamentos_linhas.csv":
        return pd.DataFrame(_ORC_LINHAS_RECORDS)
    if fn == "obras_lista.csv":
        return pd.DataFrame(_OBRAS_RECORDS)
    if fn == "orc_catalogo.csv":
        return pd.DataFrame(_CATALOGO_RECORDS)
    if fn == "orc_tarifas.csv":
        return pd.DataFrame(_TARIFAS_RECORDS)
    if fn == "orc_ref_precos.csv":
        return pd.DataFrame(_REF_PRECOS_RECORDS)
    if fn == "orc_clientes.csv":
        return pd.DataFrame(_CLIENTES_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_orcamentacao import render_orcamentacao
    render_orcamentacao()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_admin_orcamentacao.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderOrcamentacaoSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 5 separadores (Cockpit, Orçamentos, Novo Orçamento, Catálogo,
    Analytics) porque st.tabs() desenha o conteúdo de todos de uma
    vez — dentro de Catálogo, os 3 sub-separadores (Catálogo de
    Tempos, Tarifas MO, Preços Referência)."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Testes do módulo de Auditoria Anual & Dossier Digital
(mod_fat_auditoria.py) — Checklist, Inconsistências, Dossier Digital,
Comparativo Anual, Export TOC/ROC.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 4
gráficos Plotly (Preparação por Categoria, Gauge de Preparação,
Inconsistências por Tipo, Receita vs Custos) e o PDF do dossier
(reportlab). O botão "Análise IA das Inconsistências" e o ZIP do
dossier não são acionados nestes testes — não tocam em GCS/API real.

Não tocam em GCS real: `mod_fat_auditoria.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_fat_auditoria -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{"Obra": "Obra Auditoria Teste", "Ativa": "Ativa"}]

_REGISTOS_RECORDS = [
    {"Obra": "Obra Auditoria Teste", "Colaborador": "Ana Teste",
     "Data": "01/08/2026", "Horas": "8"},
    {"Obra": "", "Colaborador": "Bruno Teste",
     "Data": "02/08/2026", "Horas": "8"},
]

_FAT_CLI_RECORDS = [
    {"ID": "F1", "Numero": "FT001", "Tipo": "Fatura",
     "Data_Emissao": "01/01/2026", "Data_Vencimento": "01/02/2026",
     "Cliente": "Cliente Auditoria Teste", "NIF_Cliente": "",
     "Obra": "Obra Auditoria Teste", "Subtotal": "1000", "IVA": "230",
     "Total": "1230", "Estado": "Pendente"},
    {"ID": "F2", "Numero": "FT002", "Tipo": "Fatura",
     "Data_Emissao": "01/02/2026", "Data_Vencimento": "01/03/2026",
     "Cliente": "Cliente Auditoria Teste", "NIF_Cliente": "500000000",
     "Obra": "Obra Auditoria Teste", "Subtotal": "2000", "IVA": "460",
     "Total": "2460", "Estado": "Pendente"},
]

_FAT_FORN_RECORDS = [
    {"ID": "FF1", "Data": "01/01/2026", "Fornecedor": "Fornecedor Teste",
     "Numero_Fatura": "", "Descricao": "Material", "Obra": "Obra Auditoria Teste",
     "Total": "500", "IVA": "115", "Retencao_Val": "0", "Estado": "Pago"},
]

_RH_RECORDS = [{"Nome": "Ana Teste", "Salario_Base": "1200"}]

_IBAN_HIST_RECORDS = [
    {"ID": "IH1", "Entidade": "Fornecedor Teste", "Data_Alteracao": "10/08/2026"},
]

_MOVIMENTOS_RECORDS = [{"ID": "M1", "Data": "01/08/2026"}]
_IMOB_RECORDS = [{"ID": "I1", "Descricao": "Viatura de serviço"}]
_SEGUROS_RECORDS = [{"ID": "S1", "Tipo": "Seguro Automóvel"}]
_ALVARAS_RECORDS = [{"ID": "A1", "Tipo": "Alvará de Construção"}]
_CAUCOES_RECORDS = [{"ID": "C1", "Obra": "Obra Auditoria Teste"}]
_CONTRATOS_RECORDS = [{"ID": "CT1", "Cliente": "Cliente Auditoria Teste",
                        "Obra": "Obra Auditoria Teste"}]
_PROVISOES_RECORDS = [{"ID": "P1", "Colaborador": "Ana Teste"}]
_RENTING_RECORDS = [{"ID": "R1", "Matricula": "AA-11-BB"}]
_COMB_RECORDS = [{"ID": "CB1", "Matricula": "AA-11-BB"}]
_ORC_OBRAS_RECORDS = [{"ID": "O1", "Obra": "Obra Auditoria Teste"}]
_FORNECEDORES_RECORDS = [{"ID": "FO1", "NIF": "500000001"}]


def _fake_load_db(fn, cols, silent=False):
    mapa = {
        "faturas_clientes.csv": _FAT_CLI_RECORDS,
        "faturas_fornecedores.csv": _FAT_FORN_RECORDS,
        "colaboradores_rh.csv": _RH_RECORDS,
        "iban_historico.csv": _IBAN_HIST_RECORDS,
        "imobilizado_db.csv": _IMOB_RECORDS,
        "seguros_db.csv": _SEGUROS_RECORDS,
        "alvaras_db.csv": _ALVARAS_RECORDS,
        "caucoes_db.csv": _CAUCOES_RECORDS,
        "contratos_financeiro.csv": _CONTRATOS_RECORDS,
        "provisoes_db.csv": _PROVISOES_RECORDS,
        "renting_contratos.csv": _RENTING_RECORDS,
        "frota_combustivel.csv": _COMB_RECORDS,
        "movimentos_bancarios.csv": _MOVIMENTOS_RECORDS,
        "obras_orcamento.csv": _ORC_OBRAS_RECORDS,
        "fornecedores.csv": _FORNECEDORES_RECORDS,
    }
    if fn in mapa:
        return pd.DataFrame(mapa[fn])
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(obras_records, registos_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_auditoria import render_fat_auditoria
    render_fat_auditoria(
        pd.DataFrame(obras_records), pd.DataFrame(registos_records),
        pd.DataFrame(), pd.DataFrame())


def _run(load_db_fn=_fake_load_db, registos_records=_REGISTOS_RECORDS):
    core._cached_load_db.clear()
    with patch("mod_fat_auditoria.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(_OBRAS_RECORDS, registos_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderFatAuditoriaSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 5 separadores (Checklist, Inconsistências, Dossier Digital,
    Comparativo Anual, Export TOC/ROC) porque st.tabs() desenha o
    conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio, registos_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_fat_auditoria.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados. As 12 pastas do
    Dossier Digital não têm semântica boa/má — colapsadas numa cor
    decorativa única (acento) quando têm documentos, mesmo critério
    de mod_admin_formacoes.py."""

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

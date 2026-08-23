"""
Testes do módulo de Frota & Renting (mod_fat_frota.py) — Contratos
Renting, Combustível & KM, Comparador TCO, Seguros Frota, Relatório
Financeiro.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 5
gráficos Plotly (Custos Frota Mensal, KM Reais vs Contratados, TCO
Comparação, Timeline Renting, Consumo por Viatura) e o PDF (reportlab,
se aplicável).

Não tocam em GCS real: `mod_fat_frota.load_db` é mockado diretamente
(devolve DataFrames de teste, consoante o ficheiro pedido).

Correr:  python -m unittest test_mod_fat_frota -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_RENTING_RECORDS = [
    {"ID": "R1", "Matricula": "AA-11-BB", "Marca": "Renault",
     "Modelo": "Kangoo", "Banco": "Millennium BCP",
     "Data_Inicio": "01/01/2024", "Data_Fim": "02/09/2026",
     "Valor_Mensal": "350", "KM_Ano": "20000",
     "KM_Excedente_Preco": "0.12", "Opcao_Compra": "5000",
     "Valor_Residual": "5000", "Estado": "Ativo",
     "Obra_Alocada": "Obra Frota Teste"},
    {"ID": "R2", "Matricula": "CC-22-DD", "Marca": "Fiat",
     "Modelo": "Ducato", "Banco": "Santander",
     "Data_Inicio": "01/01/2024", "Data_Fim": "07/10/2026",
     "Valor_Mensal": "450", "KM_Ano": "25000",
     "KM_Excedente_Preco": "0.15", "Opcao_Compra": "8000",
     "Valor_Residual": "8000", "Estado": "Ativo", "Obra_Alocada": ""},
]

_COMB_RECORDS = [
    {"ID": "C1", "Data": "05/08/2026", "Matricula": "AA-11-BB",
     "Condutor": "Ana Teste", "Litros": "40", "Valor": "64",
     "KM": "10000", "Tipo_Comb": "Gasóleo", "Recibo_b64": ""},
    {"ID": "C2", "Data": "15/08/2026", "Matricula": "AA-11-BB",
     "Condutor": "Ana Teste", "Litros": "38", "Valor": "60",
     "KM": "10600", "Tipo_Comb": "Gasóleo", "Recibo_b64": ""},
]

_FROTA_RECORDS = [
    {"ID": "F1", "Matricula": "EE-33-FF", "Marca": "Toyota",
     "Modelo": "Hilux", "Tipo": "Pickup", "Condutor": "Bruno Teste",
     "Custo_Mensal": "0", "Status": "Ativa", "Data_Registo": "01/01/2024"},
]

_SEGUROS_RECORDS = [
    {"ID": "S1", "Tipo": "Seguro Automóvel (RC Obrigatório)",
     "Entidade": "Fidelidade", "Viatura": "AA-11-BB",
     "Valor_Anual": "600", "Data_Inicio": "01/01/2026",
     "Data_Fim": "10/03/2027", "Apolice": "AP123"},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "renting_contratos.csv":
        return pd.DataFrame(_RENTING_RECORDS)
    if fn == "frota_combustivel.csv":
        return pd.DataFrame(_COMB_RECORDS)
    if fn == "frota_viaturas.csv":
        return pd.DataFrame(_FROTA_RECORDS)
    if fn == "seguros_db.csv":
        return pd.DataFrame(_SEGUROS_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(pre_session_state=None):
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    if pre_session_state:
        for k, v in pre_session_state.items():
            st.session_state[k] = v
    from mod_fat_frota import render_fat_frota
    render_fat_frota()


def _run(load_db_fn=_fake_load_db, pre_session_state=None):
    core._cached_load_db.clear()
    with patch("mod_fat_frota.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(pre_session_state,), default_timeout=30)
        at.run()
    return at


class TestRenderFatFrotaSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 5 separadores (Contratos Renting, Combustível & KM, Comparador
    TCO, Seguros Frota, Relatório Financeiro) porque st.tabs() desenha
    o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_com_tco_calculado(self):
        # Simula o estado após "Calcular TCO" (sem clicar no botão)
        # — exercita a caixa de comparação Renting vs Compra.
        tco_r = {"total_rendas": 12600.0, "custo_seguros": 1890.0,
                 "custo_manut": 0.0, "total": 14490.0,
                 "custo_mes": 402.5, "custo_km": 0.24}
        tco_c = {"preco_compra": 35000.0, "valor_residual": 7000.0,
                 "amort_anual": 9333.33, "juros_total": 2887.5,
                 "manut_total": 2100.0, "seguro_total": 2205.0,
                 "total": 35192.5, "custo_mes": 977.57, "custo_km": 0.59}
        at = _run(pre_session_state={
            "tco_r": tco_r, "tco_c": tco_c, "tco_anos_calc": 3,
        })
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_fat_frota.py lê as suas cores
    de core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados. Exceção documentada: as
    caixas/rótulos "RENTING" (#3B82F6) e "COMPRA" (#8B5CF6) na aba
    Comparador TCO mantêm-se, a par do gráfico Plotly de comparação
    logo abaixo, que usa as mesmas 2 cores para as mesmas 2
    categorias (fora de âmbito, Fase 4)."""

    def test_css_usa_theme(self):
        at = _run(pre_session_state={
            "tco_r": {"total_rendas": 12600.0, "custo_seguros": 1890.0,
                      "custo_manut": 0.0, "total": 14490.0,
                      "custo_mes": 402.5, "custo_km": 0.24},
            "tco_c": {"preco_compra": 35000.0, "valor_residual": 7000.0,
                      "amort_anual": 9333.33, "juros_total": 2887.5,
                      "manut_total": 2100.0, "seguro_total": 2205.0,
                      "total": 35192.5, "custo_mes": 977.57,
                      "custo_km": 0.59},
            "tco_anos_calc": 3,
        })
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
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("background:#1E293B", textos)
        self.assertNotIn("background: #1E293B", textos)
        self.assertNotIn("background:#0F172A", textos)
        self.assertNotIn("#F1F5F9", textos)

    def test_excecao_renting_compra_preservada(self):
        # Caixas de config da aba TCO mantêm-se de propósito, a par
        # do gráfico Plotly de comparação.
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn("#3B82F6", textos)
        self.assertIn("#8B5CF6", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

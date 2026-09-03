"""
Testes do módulo de Imobilizado, Amortizações, Seguros, Cauções e
Alvarás (mod_fat_imobilizado.py) — Imobilizado & Amortizações,
Seguros, Cauções Bancárias, Alvarás & Licenças.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 5
gráficos Plotly (Timeline Amortização, Donut Imobilizado por
Categoria, Valor Bruto vs Amortizado, Timeline Seguros, Timeline
Cauções) e o PDF do quadro de amortizações (reportlab).

Não tocam em GCS real: `mod_fat_imobilizado.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_fat_imobilizado -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_IMOB_RECORDS = [
    {"ID": "I1", "Descricao": "Multímetro Fluke 289",
     "Categoria": "Equipamento Instrumentação", "Numero_Serie": "SN123",
     "Valor_Compra": "1000", "Data_Compra": "01/01/2024",
     "Taxa_Amort": "20", "Metodo_Amort": "linear", "Amort_Anual": "200",
     "Amort_Acum": "400", "Val_Contabil": "600",
     "Obra_Afeta": "Obra Imob Teste", "Estado": "Ativo", "Notas": ""},
    # Estado "Em Manutenção" — exercita o ramo "warning" do estado
    # do ativo.
    {"ID": "I2", "Descricao": "Carrinha de Serviço",
     "Categoria": "Viaturas Ligeiras", "Numero_Serie": "SN456",
     "Valor_Compra": "20000", "Data_Compra": "01/01/2023",
     "Taxa_Amort": "25", "Metodo_Amort": "linear", "Amort_Anual": "5000",
     "Amort_Acum": "10000", "Val_Contabil": "10000",
     "Obra_Afeta": "Obra Imob Teste", "Estado": "Em Manutenção",
     "Notas": ""},
]

_SEGUROS_RECORDS = [
    {"ID": "S1", "Tipo": "Responsabilidade Civil Geral",
     "Entidade": "Fidelidade", "Viatura": "", "Valor_Anual": "1200",
     "Data_Inicio": "01/01/2026", "Data_Fim": "20/09/2026",
     "Apolice": "AP001", "Cobertura": "RC até 5M", "Obra": ""},
]

_CAUCOES_RECORDS = [
    {"ID": "C1", "Obra": "Obra Imob Teste", "Banco": "CGD",
     "Valor": "5000", "Data_Constituicao": "01/01/2026",
     "Data_Libertacao": "15/09/2026", "Estado": "Ativa",
     "Tipo_Cauco": "Caução de Boa Execução", "Notas": ""},
    # Liberta a ~60 dias — exercita o ramo "accent" (nem verde
    # próximo, nem âmbar distante).
    {"ID": "C2", "Obra": "Obra Imob Teste 2", "Banco": "CGD",
     "Valor": "3000", "Data_Constituicao": "01/01/2026",
     "Data_Libertacao": "22/10/2026", "Estado": "Ativa",
     "Tipo_Cauco": "Caução de Garantia", "Notas": ""},
]

_ALVARAS_RECORDS = [
    {"ID": "A1", "Tipo": "Alvará de Construção (INCI)",
     "Numero": "ALV001", "Entidade": "IMPIC",
     "Data_Emissao": "01/01/2024", "Data_Validade": "10/09/2026",
     "Custo_Renovacao": "300", "Estado": "Válido",
     "Notas": "Renovação anual"},
]


def _fake_load_db(fn, cols, silent=False):
    mapa = {
        "imobilizado_db.csv": _IMOB_RECORDS,
        "seguros_db.csv": _SEGUROS_RECORDS,
        "caucoes_db.csv": _CAUCOES_RECORDS,
        "alvaras_db.csv": _ALVARAS_RECORDS,
    }
    if fn in mapa:
        return pd.DataFrame(mapa[fn])
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
    from mod_fat_imobilizado import render_fat_imobilizado
    render_fat_imobilizado()


def _run(load_db_fn=_fake_load_db, pre_session_state=None):
    core._cached_load_db.clear()
    with patch("mod_fat_imobilizado.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(pre_session_state,), default_timeout=30)
        at.run()
    return at


class TestRenderFatImobilizadoSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 4 separadores (Imobilizado & Amortizações, Seguros, Cauções
    Bancárias, Alvarás & Licenças) porque st.tabs() desenha o
    conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_com_detalhe_ativo_aberto(self):
        # Abre o detalhe de amortização de um ativo (exercita o
        # gráfico de timeline + tabela do mapa anual).
        at = _run(pre_session_state={"imob_detail": "I1"})
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_fat_imobilizado.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados."""

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
        self.assertNotIn("background:#0F172A", textos)
        self.assertNotIn("#F1F5F9", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

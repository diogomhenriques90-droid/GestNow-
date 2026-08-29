"""
Testes do módulo Performance por Obra (mod_fat_obras.py) — Fase 2 da
Identidade Visual: migração para o THEME central (core.py), em vez de
hexadecimais soltos.

Fora de âmbito, de propósito (Fase 4): as cores dos gráficos Plotly
(_grafico_*, ~6 funções) e do PDF de P&L (_gerar_pdf_pl, reportlab) —
não herdam do tema do Streamlit, precisam da sua própria paleta
partilhada em código à parte.

Não tocam em GCS real: `mod_fat_obras.load_db` é mockado diretamente
(devolve DataFrames vazios com as colunas certas).

Correr:  python -m unittest test_mod_fat_obras -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core


def _fake_load_db(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


_OBRAS_RECORDS = [{
    "Obra": "Obra P&L Teste", "Cliente": "Cliente Teste", "Ativa": "Ativa",
}]

_REGISTOS_RECORDS = [{
    "Técnico": "Ana Teste", "Obra": "Obra P&L Teste",
    "Data": "01/01/2026", "Horas_Total": "8",
}]

_DIARIAS_PAG_RECORDS = [{
    "Obras": "Obra P&L Teste", "Valor_Total": "50",
    "Data_Pagamento": "01/01/2026",
}]


def _script(obras_records, registos_records, diarias_pag_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_obras import render_fat_obras
    vazio = pd.DataFrame()
    render_fat_obras(
        pd.DataFrame(obras_records),
        pd.DataFrame(registos_records),
        vazio,
        pd.DataFrame(diarias_pag_records),
    )


def _run(obras_records=None, registos_records=None, diarias_pag_records=None,
         load_db_fn=_fake_load_db):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    diarias_pag_records = diarias_pag_records if diarias_pag_records is not None else _DIARIAS_PAG_RECORDS
    core._cached_load_db.clear()
    with patch("mod_fat_obras.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, registos_records, diarias_pag_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderFatObrasSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    todos os separadores (Visão Geral, P&L, Orçamento vs Real, WIP,
    Timeline, Lucratividade) porque st.tabs() desenha o conteúdo de
    todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], registos_records=[], diarias_pag_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_obras_sem_ativas(self):
        obras_inativas = [{
            "Obra": "Obra Inativa", "Cliente": "Cliente Teste", "Ativa": "Inativa",
        }]
        at = _run(obras_records=obras_inativas)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 2 da Identidade Visual: mod_fat_obras.py lê as suas cores
    de core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados nos cartões de obra,
    scorecard, P&L detalhado e WIP."""

    def test_css_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        for chave in ("surface", "border", "accent"):
            self.assertIn(core.THEME[chave], css)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#6B7280", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        # #1E293B continua a aparecer — é agora THEME['text'] (texto
        # escuro sobre fundo claro), não um fundo. Os fundos escuros
        # antigos (#0F172A, #334155) é que têm de ter desaparecido do
        # HTML (continuam a existir dentro dos gráficos Plotly e do
        # PDF de P&L, fora de âmbito na Fase 2).
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#334155", textos)

    def test_rag_usa_theme(self):
        import mod_fat_obras
        self.assertEqual(mod_fat_obras._rag(80)[0], core.THEME["success"])
        self.assertEqual(mod_fat_obras._rag(50)[0], core.THEME["warning"])
        self.assertEqual(mod_fat_obras._rag(20)[0], core.THEME["error"])

    def test_wip_estado_usa_theme(self):
        # Força obras_wip.csv a devolver um registo para exercitar o
        # ramo do cartão WIP (vazio no smoke test por omissão).
        def _load_com_wip(fn, cols, silent=False):
            if fn == "obras_wip.csv":
                return pd.DataFrame([{
                    "ID": "W1", "Obra": "Obra P&L Teste",
                    "Descricao": "Instalação de instrumentos",
                    "Valor_Est": "1000", "Data_Registo": "01/01/2026",
                    "Estado": "Em Curso",
                }])
            return pd.DataFrame(columns=cols)

        at = _run(load_db_fn=_load_com_wip)
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#3B82F6", textos)
        self.assertIn(core.THEME["accent"], textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

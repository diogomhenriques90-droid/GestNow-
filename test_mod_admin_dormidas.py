"""
Testes do módulo Gestão de Dormidas (mod_admin_dormidas.py) —
Registar, IA Pesquisa Hotéis, Histórico.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Não tocam em GCS real: `mod_admin_dormidas.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_admin_dormidas -v
"""
import json
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_USERS_RECORDS = [
    {"Nome": "Ana Teste", "Tipo": "Técnico", "Cargo": "Instrumentista"},
]

_OBRAS_RECORDS = [
    {"Obra": "Obra Dormidas Teste", "Cliente": "Cliente Teste", "Ativa": "Ativa"},
]

_DORMIDAS_RECORDS = [
    {"ID": "D1", "Data_Entrada": "01/01/2026", "Data_Saida": "03/01/2026",
     "Trabalhador": "Ana Teste", "Obra": "Obra Dormidas Teste",
     "Hotel": "Hotel Teste", "Cidade": "Sines", "Custo_Noite": "50",
     "Noites": "2", "Total": "100", "Registado_Por": "Admin",
     "Recibo_b64": ""},
]


def _fake_load_db(fn, cols, silent=False):
    mapa = {
        "dormidas.csv":    _DORMIDAS_RECORDS,
        "usuarios.csv":    _USERS_RECORDS,
        "obras_lista.csv": _OBRAS_RECORDS,
    }
    if fn in mapa:
        return pd.DataFrame(mapa[fn])
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_dormidas import render_dormidas
    render_dormidas()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_admin_dormidas.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderDormidasSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 3 separadores (Registar, IA Pesquisa Hotéis, Histórico) porque
    st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin_dormidas.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário. As cores só aparecem nos cartões de hotel
    sugeridos pela IA — aciona o botão de pesquisa com
    anthropic.Anthropic mockado (uma sugestão adequada e dentro do
    orçamento, outra não, de propósito, para exercitar os 3 tons
    semânticos)."""

    def _run_com_resultados_ia(self):
        core._cached_load_db.clear()
        resposta_ia = json.dumps({
            "local": "Sines, Portugal",
            "hoteis": [
                {"nome": "Hotel Teste Adequado", "cidade": "Sines",
                 "distancia_km": 5, "preco_noite": 60.0, "tipo": "Hotel",
                 "adequado": True, "motivo": "Bom para trabalhadores",
                 "total_estimado": 300.0},
                {"nome": "Hotel Teste Caro", "cidade": "Sines",
                 "distancia_km": 10, "preco_noite": 150.0, "tipo": "Hotel",
                 "adequado": False, "motivo": "Muito caro",
                 "total_estimado": 750.0},
            ]
        })
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=resposta_ia)]

        with patch("mod_admin_dormidas.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", return_value=None), \
             patch("core._gcs_client", return_value=None), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), \
             patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.create.return_value = mock_resp
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="pesq_local").set_value("Sines, Portugal")
            at.button(key="btn_pesq_hotel").click().run()
        return at

    def test_css_usa_theme(self):
        at = self._run_com_resultados_ia()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("text_secondary", "accent", "warning",
                      "success", "error"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = self._run_com_resultados_ia()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = self._run_com_resultados_ia()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("background:#1E293B", textos)
        self.assertNotIn("background: #1E293B", textos)
        self.assertNotIn("#F1F5F9", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

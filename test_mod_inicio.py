"""
Testes do ecrã de Início (mod_inicio.py) — Fase 2 da Identidade Visual:
migração para o THEME central (core.py), em vez das cores escuras à
mão que existiam antes (38 cores fixas, fundo forçado a escuro, botão
"Registar Ponto" a vermelho como se fosse um estado de erro).

Não tocam em GCS real: `core._gcs_read` é mockado com um CSV fixo em
memória. `render_inicio` é invocado diretamente (sem passar por
app.py/mod_admin.py).

Correr:  python -m unittest test_mod_inicio -v
"""
import io
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_USUARIOS_CSV = (
    "Nome,PDFs_Validados,PrecoHoraStatus\n"
    "Jorge Chefe,Sim,Aceite\n"
).encode("utf-8-sig")


def _fake_gcs_read(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_CSV)
    return None


_OBRAS_RECORDS = [{
    "Obra": "Obra Início Teste", "Codigo": "OBR-002", "Cliente": "Cliente Teste",
    "Ativa": "Ativa",
}]

_REGISTOS_RECORDS = [{
    "ID": "R1", "Técnico": "Jorge Chefe", "Obra": "Obra Início Teste",
    "Frente": "Frente A", "Turnos": "08:00-17:00", "Data": "01/01/2026",
    "Horas_Total": "8", "Status": "1", "Relatorio": "",
}]

_REQ_FER_RECORDS = [{
    "ID": "F1", "Solicitante": "Jorge Chefe", "Obra": "Obra Início Teste",
    "Data": "01/01/2026", "Status": "Pendente", "Descricao": "Chave de fendas",
}]


def _script(obras_records, registos_records, req_fer_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user']  = 'Jorge Chefe'
    st.session_state['tipo']  = 'Chefe de Equipa'
    st.session_state['cargo'] = 'Chefe de Equipa'
    from mod_inicio import render_inicio
    vazio = pd.DataFrame()
    args = [
        vazio,                              # users
        pd.DataFrame(obras_records),         # obras_db
        vazio,                               # frentes_db
        pd.DataFrame(registos_records),      # registos_db
        vazio, vazio, vazio, vazio, vazio,   # faturas, docs, incs, sw, obs
        vazio, vazio, vazio,                 # equip, diags, diags_u
        vazio, vazio, vazio,                 # folhas, comuns, comuns_u
        pd.DataFrame(req_fer_records),       # req_fer_db
        vazio, vazio,                        # req_mat_db, req_epi_db
        vazio,                               # avals_db
        vazio,                               # inst_acessos_db
    ]
    render_inicio(*args)


def _run(obras_records=None, registos_records=None, req_fer_records=None):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    req_fer_records = req_fer_records if req_fer_records is not None else _REQ_FER_RECORDS
    core._cached_load_db.clear()
    with patch("core._gcs_read", side_effect=_fake_gcs_read), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, registos_records, req_fer_records),
            default_timeout=30)
        at.run()
    return at


class TestRenderInicioSemErro(unittest.TestCase):
    """Smoke test — o ecrã de boas-vindas (Chefe/Técnico) renderiza sem
    erro, com e sem dados."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], registos_records=[], req_fer_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_botao_registar_ponto_presente(self):
        at = _run()
        labels = [b.label for b in at.button]
        self.assertTrue(any("Registar Ponto" in l for l in labels))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 2 da Identidade Visual: mod_inicio.py lê as suas cores de
    core.THEME — o fundo escuro forçado (.stApp) desaparece e o botão
    "Registar Ponto" deixa de ser vermelho (cor de erro/perigo no
    resto da app) para usar o acento do THEME."""

    def test_nao_forca_fundo_escuro(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        self.assertNotIn(".stApp", css)
        self.assertNotIn("#0F172A", css)

    def test_css_usa_theme(self):
        at = _run()
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        for chave in ("surface", "border", "text", "text_secondary", "accent"):
            self.assertIn(core.THEME[chave], css)

    def test_botao_primario_nao_e_vermelho(self):
        # "Registar Ponto" (type="primary") já não usa #DC2626 — usa o
        # acento do THEME, como qualquer outro botão de destaque na app.
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#DC2626", textos)
        self.assertIn(core.THEME["accent"], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#475569", textos)
        self.assertNotIn("#CBD5E1", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_kpi_horas_mes_deixa_de_ser_vermelho(self):
        # O cartão "Horas este mês" era tingido de vermelho (rgba de
        # #DC2626) sem ser um estado de erro — passa a usar o acento.
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("rgba(220,38,38", textos)

    def test_dot_color_vem_do_theme(self):
        import mod_inicio
        self.assertEqual(mod_inicio._DOT_COLOR["0"], core.THEME["warning"])
        self.assertEqual(mod_inicio._DOT_COLOR["1"], core.THEME["success"])
        self.assertEqual(mod_inicio._DOT_COLOR["2"], core.THEME["accent"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

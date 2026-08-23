"""
Testes do módulo de Instrumentação Industrial (mod_instrumentacao.py)
— Fase 3 da Identidade Visual: migração para o THEME central
(core.py), em vez de hexadecimais soltos.

Fora de âmbito, de propósito: TIPOS_TAG (dicionário de cores por tipo
de tag ISA) está definido mas nunca é usado em lado nenhum do render
— é código morto, sem impacto visual, não faz parte desta migração. O
certificado ITR-A em PDF (_gerar_certificado_itr_a, reportlab)
também fica de fora, mesmo critério das outras Fases.

Não tocam em GCS real: `mod_instrumentacao.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_instrumentacao -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{
    "Obra": "Obra Instrumentação Teste", "Cliente": "Cliente Teste",
    "TipoObra": "Instrumentação", "Ativa": "Ativa",
}]

_INSTS_RECORDS = [{
    "ID": "I1", "Tag": "PT-101", "Tipo": "Pressão", "Descricao": "Transmissor",
    "Fabricante": "ABB", "Modelo": "266", "Status": "3",
    "GPS_Lat": "38.7", "GPS_Lng": "-9.1", "Foto_Local_b64": "",
    "Assinatura_Calibracao_b64": "", "Assinatura_Instalacao_b64": "",
    "Hash_Validacao": "",
}]


def _fake_load_db(fn, cols, silent=False):
    if fn.endswith("_index.csv"):
        return pd.DataFrame(_INSTS_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(obras_records, load_db_fn_name):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_instrumentacao import render_instrumentacao
    vazio = pd.DataFrame()
    # Tal como load_all() devolveria — mesmo "vazia" tem sempre as
    # colunas certas (obras_db não é protegida por `.empty` antes de
    # aceder a 'TipoObra' em render_instrumentacao()).
    obras_db = pd.DataFrame(
        obras_records, columns=["Obra", "Cliente", "TipoObra", "Ativa"])
    # (users, obras_db, frentes_db, registos_db, fats, docs, incs, sw, obs,
    #  equip, diags, diags_u, folhas, comuns, comuns_u, req_fer, req_mat,
    #  req_epi, avals, inst_acessos, *_) — 24 posições, só as 20
    # primeiras são lidas.
    render_instrumentacao(
        vazio, obras_db, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio,
    )


def _run(obras_records=None, load_db_fn=_fake_load_db):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    core._cached_load_db.clear()
    with patch("mod_instrumentacao.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(obras_records, None), default_timeout=30)
        at.run()
    return at


class TestRenderInstrumentacaoSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (IA Vision, Index, Scan QR, ITR-A, ITR-B & GPS,
    Handover) porque st.tabs() desenha o conteúdo de todos de uma
    vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_obra_instrumentacao(self):
        obras_sem_tipo = [{
            "Obra": "Obra Normal", "Cliente": "Cliente Teste",
            "TipoObra": "Normal", "Ativa": "Ativa",
        }]
        at = _run(obras_records=obras_sem_tipo)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_instrumentacao.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, sem fundos
    escuros forçados no cabeçalho, cartão do QR Code (aba Index),
    cartão do resultado do Scan QR e cartão de navegação GPS (ITR-B)."""

    def test_cabecalho_usa_theme(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary"):
            self.assertIn(core.THEME[chave], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#F8FAFC", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#60A5FA", textos)

    def test_gps_card_usa_theme(self):
        # Instrumento calibrado (Status=2) com GPS registado — aparece
        # por omissão na aba ITR-B (primeira opção do selectbox).
        insts_itrb = [{
            "ID": "I2", "Tag": "PT-102", "Tipo": "Pressão", "Descricao": "Transmissor",
            "Fabricante": "ABB", "Modelo": "266", "Status": "2",
            "GPS_Lat": "38.7", "GPS_Lng": "-9.1", "Foto_Local_b64": "",
            "Assinatura_Calibracao_b64": "", "Assinatura_Instalacao_b64": "",
            "Hash_Validacao": "",
        }]
        def _load_com_itrb(fn, cols, silent=False):
            if fn.endswith("_index.csv"):
                return pd.DataFrame(insts_itrb)
            return pd.DataFrame(columns=cols)
        at = _run(load_db_fn=_load_com_itrb)
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["accent"], textos)
        self.assertIn(core.THEME["surface"], textos)

    def test_scan_qr_usa_theme(self):
        # A interação (set_value + segundo .run()) tem de ficar DENTRO
        # do "with patch(...)" — _run() fecha o bloco ao devolver `at`,
        # por isso um .run() a seguir, já fora dele, deixa de ter
        # load_db mockado (cai no acesso real ao GCS e `insts` fica
        # vazio, escondendo o cartão sem gerar exceção).
        core._cached_load_db.clear()
        with patch("mod_instrumentacao.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", return_value=None), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script, args=(_OBRAS_RECORDS, None), default_timeout=30)
            at.run()
            self.assertFalse(at.exception, msg=str(at.exception))
            at.text_input(key="inst_scan_input").set_value(
                "GN|PT-101|Obra Instrumentação Teste").run()
            self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["accent"], textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

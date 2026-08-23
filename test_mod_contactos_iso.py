"""
Testes do módulo de Rastreabilidade de Contactos ISO 9001:2015 Cl. 8.2
(mod_contactos_iso.py) — Fase 3 da Identidade Visual: migração para
o THEME central (core.py), em vez de hexadecimais soltos.

Fora de âmbito, de propósito (Fase 4, mesmo critério dos gráficos
Plotly): os gráficos "Origem por Canal" (pizza) e "Taxa de Follow-up"
(barras) na aba Analytics ISO.

Não tocam em GCS real: `mod_contactos_iso.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_contactos_iso -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_CONTACTOS_RECORDS = [
    {"ID": "CT1", "Data": "01/01/2026", "Hora": "10:00", "Canal": "📞 Telefone",
     "Sentido": "Entrada", "Cliente_Nome": "Cliente ISO Teste",
     "Contacto_Nome": "João Cliente", "Contacto_Telefone": "911111111",
     "Contacto_Email": "joao@cliente.pt", "Assunto": "Pedido de orçamento",
     "Resumo": "Cliente pediu orçamento para nova obra.",
     "Responsavel": "Ana Teste", "Evidencia_Tipo": "Nenhuma",
     "Evidencia_Path": "", "Oportunidade_ID": "", "Estado": "Aberto",
     "Proximo_Passo": "Enviar proposta", "Data_Proximo_Passo": "08/01/2026",
     "Notas": ""},
    {"ID": "CT2", "Data": "02/01/2026", "Hora": "11:00", "Canal": "📧 Email",
     "Sentido": "Saída", "Cliente_Nome": "Cliente ISO Teste",
     "Contacto_Nome": "João Cliente", "Contacto_Telefone": "911111111",
     "Contacto_Email": "joao@cliente.pt", "Assunto": "Envio de proposta",
     "Resumo": "Proposta enviada por email.",
     "Responsavel": "Ana Teste", "Evidencia_Tipo": "Email (PDF)",
     "Evidencia_Path": "gs://gestnow-dados/evidencias_contactos/CT2/x.pdf",
     "Oportunidade_ID": "OP1", "Estado": "Fechado",
     "Proximo_Passo": "", "Data_Proximo_Passo": "", "Notas": ""},
]

_OPORT_RECORDS = [
    {"ID": "OP1", "Nome": "Obra ISO Teste", "Cliente": "Cliente ISO Teste",
     "Setor": "Industrial", "Comercial": "Ana Teste", "Stage": "proposta",
     "Valor_Est": "50000", "Prob_Fecho": "60", "Data_Criacao": "01/01/2026",
     "Data_Fecho_Est": "01/03/2026", "Origem": "Telefone", "Notas": "",
     "Obra_Associada": ""},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "com_contactos.csv":
        return pd.DataFrame(_CONTACTOS_RECORDS)
    if fn == "comercial_oportunidades.csv":
        return pd.DataFrame(_OPORT_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_contactos_iso import render_contactos_iso
    render_contactos_iso()


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_contactos_iso.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestRenderContactosIsoSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 4 separadores (Contactos, Registar Contacto, Timeline por
    Cliente, Analytics ISO) porque st.tabs() desenha o conteúdo de
    todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_contactos_iso.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados nos cartões de
    detalhe do contacto, estado, timeline por cliente e Analytics ISO."""

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
        self.assertNotIn("#0F172A", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

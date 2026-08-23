"""
Testes do módulo de Gestão de Acessos de Colaboradores a Obras
(mod_admin_acessos_obras.py) — Painel Geral, Conceder Acesso,
Documentos, Por Obra, Requisitos por Obra, Relatórios.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 2
gráficos Plotly (Estado dos Acessos, Estado dos Documentos, aba
Painel Geral) e os 2 PDFs (cartão de acesso, relatório, reportlab).

Não tocam em GCS real: `mod_admin_acessos_obras.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido); `core._gcs_read` mockado a devolver None (usado por
_get_config_empresa, cai no fallback local).

Correr:  python -m unittest test_mod_admin_acessos_obras -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_USERS_RECORDS = [{"Nome": "Ana Teste"}, {"Nome": "Bruno Teste"}]
_OBRAS_RECORDS = [{"Obra": "Obra Acessos Teste", "Ativa": "Ativa"}]

_ACESSOS_RECORDS = [
    {"ID": "A1", "Obra": "Obra Acessos Teste", "Colaborador": "Ana Teste",
     "Nivel_Acesso": "Área Geral", "Data_Inicio": "01/01/2026",
     "Data_Fim": "10/09/2026", "Estado": "Activo", "Motivo_Suspensao": "",
     "Cracha_Numero": "CPS-001", "Cracha_Emitido": "Sim", "Notas": "",
     "Criado_Por": "Admin", "Criado_Em": "01/01/2026"},
    {"ID": "A2", "Obra": "Obra Acessos Teste", "Colaborador": "Bruno Teste",
     "Nivel_Acesso": "Supervisão", "Data_Inicio": "01/01/2026",
     "Data_Fim": "01/02/2026", "Estado": "Suspenso",
     "Motivo_Suspensao": "Falta de formação", "Cracha_Numero": "",
     "Cracha_Emitido": "Não", "Notas": "", "Criado_Por": "Admin",
     "Criado_Em": "01/01/2026"},
]

_DOCS_RECORDS = [
    {"ID": "D1", "Colaborador": "Ana Teste", "Obra": "Obra Acessos Teste",
     "Tipo_Doc": "Cartão de Cidadão", "Numero_Doc": "12345678",
     "Emissao": "01/01/2020", "Validade": "10/09/2026",
     "Verificado_Por": "Admin", "Verificado_Em": "01/01/2026",
     "Estado_Doc": "Válido", "Ficheiro_b64": "", "Notas": ""},
    {"ID": "D2", "Colaborador": "Ana Teste", "Obra": "Obra Acessos Teste",
     "Tipo_Doc": "Exame Médico de Aptidão", "Numero_Doc": "",
     "Emissao": "01/01/2026", "Validade": "01/01/2027",
     "Verificado_Por": "Admin", "Verificado_Em": "01/01/2026",
     "Estado_Doc": "Válido", "Ficheiro_b64": "", "Notas": ""},
]

_REQ_RECORDS = [
    {"ID": "R1", "Obra": "Obra Acessos Teste",
     "Tipo_Obra": "Construção Industrial",
     "Documentos_Obrigatorios": (
         "Cartão de Cidadão|Exame Médico de Aptidão|"
         "Formação HSE Indução Geral"),
     "Nivel_Seguranca": "Médio", "Instrucoes": "Usar capacete e colete.",
     "Atualizado_Em": "01/01/2026"},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "acessos_obras.csv":
        return pd.DataFrame(_ACESSOS_RECORDS)
    if fn == "acessos_documentos.csv":
        return pd.DataFrame(_DOCS_RECORDS)
    if fn == "acessos_requisitos_obras.csv":
        return pd.DataFrame(_REQ_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(users_records, obras_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_acessos_obras import render_acessos_obras
    render_acessos_obras(pd.DataFrame(users_records), pd.DataFrame(obras_records))


def _run(load_db_fn=_fake_load_db):
    core._cached_load_db.clear()
    with patch("mod_admin_acessos_obras.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(_USERS_RECORDS, _OBRAS_RECORDS), default_timeout=30)
        at.run()
    return at


class TestRenderAcessosObrasSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Painel Geral, Conceder Acesso, Documentos, Por
    Obra, Requisitos por Obra, Relatórios) porque st.tabs() desenha o
    conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin_acessos_obras.py lê as
    suas cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados. Nível de acesso
    (Área Geral/Restrita/Supervisão/Acesso Total) não tem semântica
    boa/má — colapsado numa cor decorativa única (acento), mesmo
    critério de mod_admin_formacoes.py."""

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
        self.assertNotIn("#93C5FD", textos)
        self.assertNotIn("#6B7280", textos)
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

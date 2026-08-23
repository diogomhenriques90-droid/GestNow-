"""
Testes do módulo de Gestão de Formações (mod_admin_formacoes.py) —
ISO 9001:2015 Cláusula 7.2 Competência.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os 2
gráficos Plotly (Custo por Categoria, Custo por Colaborador, aba
Custos & Reembolsos) e os 2 PDFs (comprovativo de formação, plano
anual, reportlab).

Não tocam em GCS real: `mod_admin_formacoes.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido); `core._gcs_read` mockado a devolver None (usado por
_get_config_empresa, cai no fallback local).

Correr:  python -m unittest test_mod_admin_formacoes -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_USERS_RECORDS = [{"Nome": "Ana Teste"}, {"Nome": "Bruno Teste"}]
_OBRAS_RECORDS = [{"Obra": "Obra Formacoes Teste", "Ativa": "Ativa"}]

_FORMACOES_RECORDS = [
    {"ID": "F1", "Colaborador": "Ana Teste",
     "Formacao": "Trabalho em Altura", "Categoria": "Segurança",
     "Entidade": "IEFP", "Data_Conclusao": "01/01/2026",
     "Data_Validade": "20/09/2026", "Duracao_H": "8",
     "Resultado": "Aprovado", "Pago_Por": "Empresa", "Custo": "150",
     "Obra_Imputacao": "RH / Geral", "Reembolsado": "N/A",
     "Certificado_b64": "", "Notas": "", "Criado_Por": "Admin",
     "Criado_Em": "01/01/2026"},
    {"ID": "F2", "Colaborador": "Bruno Teste",
     "Formacao": "Calibração de Instrumentos", "Categoria": "Técnica",
     "Entidade": "Interna (CPS)", "Data_Conclusao": "01/02/2026",
     "Data_Validade": "01/03/2026", "Duracao_H": "16",
     "Resultado": "Aprovado", "Pago_Por": "Colaborador (reembolso)",
     "Custo": "200", "Obra_Imputacao": "RH / Geral",
     "Reembolsado": "Não", "Certificado_b64": "", "Notas": "",
     "Criado_Por": "Admin", "Criado_Em": "01/02/2026"},
]

_PLANO_RECORDS = [
    {"ID": "P1", "Ano": "2026", "Colaborador": "Ana Teste",
     "Formacao": "ATEX — Atmosferas Explosivas", "Categoria": "Segurança",
     "Data_Prevista": "01/10/2026", "Pago_Por": "Empresa",
     "Custo_Estimado": "300", "Estado": "Planeada", "Prioridade": "Alta",
     "Notas": ""},
    {"ID": "P2", "Ano": "2026", "Colaborador": "Bruno Teste",
     "Formacao": "ISO 9001 Sensibilização", "Categoria": "Qualidade",
     "Data_Prevista": "15/11/2026", "Pago_Por": "Empresa",
     "Custo_Estimado": "100", "Estado": "Concluída", "Prioridade": "Média",
     "Notas": ""},
]

_CATALOGO_RECORDS = [
    {"ID": "C1", "Nome": "Trabalho em Altura", "Categoria": "Segurança",
     "Validade_Dias": "365", "Obrigatoria": "True", "Ativa": "True"},
    {"ID": "C2", "Nome": "Espaços Confinados", "Categoria": "Segurança",
     "Validade_Dias": "365", "Obrigatoria": "True", "Ativa": "True"},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "formacoes.csv":
        return pd.DataFrame(_FORMACOES_RECORDS)
    if fn == "formacoes_plano.csv":
        return pd.DataFrame(_PLANO_RECORDS)
    if fn == "formacoes_catalogo.csv":
        return pd.DataFrame(_CATALOGO_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(users_records, obras_records, pre_session_state=None):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    if pre_session_state:
        for k, v in pre_session_state.items():
            st.session_state[k] = v
    from mod_admin_formacoes import render_formacoes
    render_formacoes(pd.DataFrame(users_records), pd.DataFrame(obras_records))


def _run(load_db_fn=_fake_load_db, pre_session_state=None):
    core._cached_load_db.clear()
    with patch("mod_admin_formacoes.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script, args=(_USERS_RECORDS, _OBRAS_RECORDS, pre_session_state),
            default_timeout=30)
        at.run()
    return at


class TestRenderFormacoesSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Formações Registadas, Registar Formação, Por
    Colaborador, Plano Anual, Custos & Reembolsos, Catálogo) porque
    st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_com_colaborador_selecionado(self):
        # Selecciona um colaborador na aba "Por Colaborador" para
        # exercitar a matriz de competências e o aviso de formações
        # obrigatórias em falta.
        at = _run(pre_session_state={"colab_sel_form": "Ana Teste"})
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin_formacoes.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados. As etiquetas de
    categoria (Segurança/Técnica/Qualidade/Gestão/Línguas/Licença) não
    têm semântica boa/má — colapsadas numa cor decorativa única
    (acento), mesmo critério de mod_exportacao_contabilidade.py."""

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

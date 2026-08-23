"""
Testes de mod_admin_diarias.py (sub-aba "💶 Diárias" de Faturação).

Fase 2 do Painel de Obra (campos operacionais): a grelha "⚙️ Valor da
Diária por Obra" passa a ter também "Modalidade" (Corrida Semanal /
Outro), ao lado do valor.

Fase 3 da Identidade Visual (TestTemaClaroAplicado, mais abaixo):
migração para o THEME central (core.py), em vez de hexadecimais
soltos. Fora de âmbito, de propósito: o recibo de ajudas de custo em
PDF (_gerar_recibo_pdf, reportlab), mesmo critério das outras Fases.

Não tocam em GCS real: `mod_admin_diarias._gcs_read` é mockado (devolve
None por omissão — usa os fallbacks já existentes no módulo).

`st.data_editor` mapeia para o mesmo tipo de elemento que `st.dataframe`
no AppTest (acede-se via `at.dataframe`, filtrando por `.key`) — mas,
ao contrário de text_input/selectbox, o nó `Dataframe` do AppTest não
tem `set_value()`: só se pode LER `.value`, não simular uma edição de
célula. Por isso o teste do botão "Guardar" verifica a gravação do
valor já carregado na grelha (o que a função de guardar lê de
`df_editado`), não uma edição simulada pelo utilizador.

Correr:  python -m unittest test_mod_admin_diarias -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{"Obra": "Obra Teste Diarias", "Cliente": "Cliente X", "Ativa": "Ativa"}]

# render_admin_diarias(*args) espera 23 posicionais quando len(args)>=23:
# users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
# sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
# comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db,
# inst_acessos_db, diarias_config, diarias_faltas, diarias_pagamentos.


def _script(obras_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_diarias import render_admin_diarias
    vazio = pd.DataFrame()
    obras_db = pd.DataFrame(obras_records)
    render_admin_diarias(
        vazio, obras_db, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio
    )


def _script_com_diarias_config(obras_records, diarias_config_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_diarias import render_admin_diarias
    vazio = pd.DataFrame()
    obras_db = pd.DataFrame(obras_records)
    diarias_config = pd.DataFrame(diarias_config_records)
    render_admin_diarias(
        vazio, obras_db, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, diarias_config, vazio, vazio
    )


def _run():
    with patch("mod_admin_diarias._gcs_read", return_value=None):
        core._cached_load_db.clear()
        at = AppTest.from_function(_script, args=(_OBRAS_RECORDS,), default_timeout=30)
        at.run()
    return at


def _grelha_config(at):
    return next(d for d in at.dataframe if d.key == "data_editor_diarias_config")


class TestConfigurarValoresModalidade(unittest.TestCase):
    """A grelha "⚙️ Valor da Diária por Obra" passa a ter também
    "Modalidade" (Corrida Semanal / Outro), editável na mesma linha do
    valor."""

    @classmethod
    def setUpClass(cls):
        cls.at = _run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_grelha_tem_modalidade_com_valor_padrao(self):
        grelha = _grelha_config(self.at)
        self.assertEqual(
            list(grelha.value.columns), ["Obra", "€ / Dia", "Modalidade", "Ativa"])
        # Sem configuração prévia — assume "Corrida Semanal" por omissão.
        self.assertEqual(grelha.value.iloc[0]["Modalidade"], "Corrida Semanal")

    def test_grelha_respeita_modalidade_ja_configurada(self):
        diarias_config_records = [{
            "Obra": "Obra Teste Diarias", "Valor_Diaria": "45.0",
            "Modalidade": "Outro", "Atualizado_Em": "", "Atualizado_Por": "",
        }]
        with patch("mod_admin_diarias._gcs_read", return_value=None):
            core._cached_load_db.clear()
            at = AppTest.from_function(
                _script_com_diarias_config,
                args=(_OBRAS_RECORDS, diarias_config_records),
                default_timeout=30)
            at.run()
        grelha = _grelha_config(at)
        self.assertEqual(grelha.value.iloc[0]["Modalidade"], "Outro")

    def test_guardar_grava_modalidade_carregada_na_grelha(self):
        # Sem set_value() disponível para data_editor no AppTest, testa-se
        # a gravação do valor já carregado (pré-existente) na grelha —
        # confirma que o handler de "Guardar" lê e persiste a coluna
        # Modalidade de df_editado, não apenas Valor_Diaria.
        diarias_config_records = [{
            "Obra": "Obra Teste Diarias", "Valor_Diaria": "45.0",
            "Modalidade": "Outro", "Atualizado_Em": "", "Atualizado_Por": "",
        }]
        with patch("mod_admin_diarias._gcs_read", return_value=None), \
             patch("mod_admin_diarias.save_db") as mock_save:
            mock_save.return_value = True
            core._cached_load_db.clear()
            at = AppTest.from_function(
                _script_com_diarias_config,
                args=(_OBRAS_RECORDS, diarias_config_records),
                default_timeout=30)
            at.run()
            at.button(key="btn_guardar_diarias_cfg").click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        self.assertTrue(mock_save.called)
        df_gravado = mock_save.call_args[0][0]
        self.assertEqual(df_gravado.iloc[0]["Modalidade"], "Outro")


_USERS_RECORDS = [{"Nome": "Ana Teste", "Banco_IBAN": "PT50000000000000000000000"}]

_REGISTOS_RECORDS = [{
    "Técnico": "Ana Teste", "Obra": "Obra Teste Diarias",
    "Data": "07/01/2026", "Horas_Total": "8", "Status": "1",
}]

_DIARIAS_FALTAS_RECORDS = [{
    # Técnico diferente do de _REGISTOS_RECORDS — senão exclui esse
    # dia do cálculo (mesma Técnico+Data em ambos == falta nesse dia).
    "ID": "F1", "Data": "07/01/2026", "Técnico": "Bruno Falta",
    "Obra": "Obra Teste Diarias", "Motivo": "Doença",
    "Registado_Por": "Admin", "Registado_Em": "07/01/2026",
}]

_DIARIAS_PAGAMENTOS_RECORDS = [{
    "ID": "P1", "Semana_Inicio": "2026-01-05", "Semana_Fim": "2026-01-11",
    "Técnico": "Ana Teste", "Obras": "Obra Teste Diarias", "Dias_Total": "3",
    "Valor_Total": "36.0", "IBAN": "PT50000000000000000000000",
    "Status": "Pago", "Data_Pagamento": "12/01/2026", "Pago_Por": "Admin",
    "Recibo_b64": "",
}]


def _script_completo(obras_records, users_records, registos_records,
                      diarias_faltas_records, diarias_pagamentos_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    # Semana fixa (2026-01-05 a 2026-01-11) — evita depender de
    # date.today() para que os registos caiam sempre dentro do
    # período calculado, e dispensa ter de clicar no botão.
    st.session_state['diarias_ini']  = pd.Timestamp("2026-01-05").date()
    st.session_state['diarias_fim']  = pd.Timestamp("2026-01-11").date()
    st.session_state['diarias_calc'] = True
    from mod_admin_diarias import render_admin_diarias
    vazio = pd.DataFrame()
    render_admin_diarias(
        pd.DataFrame(users_records), pd.DataFrame(obras_records), vazio,
        pd.DataFrame(registos_records), vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio,
        pd.DataFrame(diarias_faltas_records),
        pd.DataFrame(diarias_pagamentos_records),
    )


def _run_completo():
    with patch("mod_admin_diarias._gcs_read", return_value=None):
        core._cached_load_db.clear()
        at = AppTest.from_function(
            _script_completo,
            args=(_OBRAS_RECORDS, _USERS_RECORDS, _REGISTOS_RECORDS,
                  _DIARIAS_FALTAS_RECORDS, _DIARIAS_PAGAMENTOS_RECORDS),
            default_timeout=30)
        at.run()
    return at


class TestCartoesAdicionaisSemErro(unittest.TestCase):
    """Smoke test — cobre os cartões que TestConfigurarValoresModalidade
    não exercitava: colaborador calculado (Semana Atual), falta
    injustificada e histórico de pagamento."""

    def test_sem_erro(self):
        at = _run_completo()
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin_diarias.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados nos cartões de
    colaborador (Semana Atual), preview de custo (Configurar
    Valores), falta injustificada, histórico de pagamento e caixa
    informativa SEPA (Empresa)."""

    def test_css_usa_theme(self):
        at = _run_completo()
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary", "accent"):
            self.assertIn(core.THEME[chave], textos)

    def test_falta_usa_theme_error(self):
        at = _run_completo()
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["error"], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run_completo()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#93C5FD", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run_completo()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#F1F5F9", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

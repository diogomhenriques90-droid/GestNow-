"""
Testes da secção "🛠️ Gestão de Clientes" (mod_fat_clientes.py, aba
"🏢 Clientes" de Faturação).

Bloqueia primeiro o comportamento ATUAL (só os campos já existentes —
NIF/Email/Telefone/Morada/Sector/Contacto Faturação/Condições/Limite/
Activo/Notas) antes da Fase 5 do Painel de Obra (campos operacionais)
acrescentar "👥 Pessoas de Contacto" (contactos_clientes.csv) dentro do
mesmo expander por cliente.

Não tocam em GCS real: `mod_fat_clientes.load_db` é mockado
diretamente (evita cache cross-teste de st.cache_data); `core._gcs_read`
devolve None por omissão.

Correr:  python -m unittest test_mod_fat_clientes -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

_CLIENTES_RECORDS = [{
    "ID": "C1", "Nome": "Cliente Teste", "NIF": "123456789", "Morada": "",
    "Email": "cliente@x.pt", "Telefone": "911111111",
    "Condicoes_Pagamento": "30", "Limite_Credito": "50000",
    "Contacto_Fat": "", "Activo": "Sim", "Sector": "", "Origem": "Manual",
    "Criado_Por": "Admin", "Data_Criacao": "01/01/2026", "Notas": "",
}]


def _fake_load_db(clientes_records):
    def _inner(fn, cols, silent=False):
        if fn == "clientes_financeiro.csv":
            return pd.DataFrame(clientes_records)
        return pd.DataFrame(columns=cols)
    return _inner


def _script(clientes_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_clientes import render_fat_clientes
    vazio = pd.DataFrame()
    render_fat_clientes(vazio, vazio)


def _run(clientes_records=None):
    clientes_records = clientes_records if clientes_records is not None else _CLIENTES_RECORDS
    with patch("mod_fat_clientes.load_db", side_effect=_fake_load_db(clientes_records)), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, args=(clientes_records,), default_timeout=30)
        at.run()
    return at


class TestGestaoClientesBase(unittest.TestCase):
    """Comportamento base da secção "🛠️ Gestão de Clientes" — continua
    igual após a Fase 5."""

    @classmethod
    def setUpClass(cls):
        cls.at = _run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_expander_do_cliente_existe(self):
        labels = [e.label for e in self.at.expander]
        self.assertTrue(any("Cliente Teste" in l for l in labels))


class TestPessoasDeContacto(unittest.TestCase):
    """Fase 5 do Painel de Obra (campos operacionais): "👥 Pessoas de
    Contacto" dentro do expander de cada cliente, ligadas por
    Cliente_ID (não por nome) a clientes_financeiro.csv."""

    def test_secao_existe(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn("Pessoas de Contacto", textos)

    def test_sem_contactos_mostra_aviso(self):
        at = _run()
        textos_caption = " ".join(c.value for c in at.caption)
        self.assertIn("Sem pessoas de contacto registadas", textos_caption)

    def test_formulario_adicionar_existe(self):
        at = _run()
        self.assertEqual(
            at.text_input(key="gc_ct_nome_C1").label, "Nome *")
        self.assertEqual(
            at.text_input(key="gc_ct_cargo_C1").label, "Cargo")
        self.assertEqual(
            at.text_input(key="gc_ct_email_C1").label, "Email")
        self.assertEqual(
            at.text_input(key="gc_ct_tel_C1").label, "Telefone")

    def test_adicionar_sem_nome_da_erro(self):
        with patch("mod_fat_clientes.load_db",
                    side_effect=_fake_load_db(_CLIENTES_RECORDS)), \
             patch("core._gcs_read", return_value=None), \
             patch("core._gcs_client", return_value=None), \
             patch("mod_fat_clientes.save_db") as mock_save:
            at = AppTest.from_function(
                _script, args=(_CLIENTES_RECORDS,), default_timeout=30)
            at.run()
            at.button(
                key="FormSubmitter:gc_ct_form_C1-➕ Adicionar Pessoa de Contacto"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        mock_save.assert_not_called()
        erros = " ".join(e.value for e in at.error)
        self.assertIn("Nome obrigatório", erros)

    def test_adicionar_grava_ligado_por_cliente_id(self):
        with patch("mod_fat_clientes.load_db",
                    side_effect=_fake_load_db(_CLIENTES_RECORDS)), \
             patch("core._gcs_read", return_value=None), \
             patch("core._gcs_client", return_value=None), \
             patch("mod_fat_clientes.save_db") as mock_save:
            mock_save.return_value = True
            at = AppTest.from_function(
                _script, args=(_CLIENTES_RECORDS,), default_timeout=30)
            at.run()
            at.text_input(key="gc_ct_nome_C1").set_value("Miguel Pesquera").run()
            at.text_input(key="gc_ct_cargo_C1").set_value("Gestor de Projeto").run()
            at.text_input(key="gc_ct_email_C1").set_value("miguel@cliente.pt").run()
            at.text_input(key="gc_ct_tel_C1").set_value("912345678").run()
            at.button(
                key="FormSubmitter:gc_ct_form_C1-➕ Adicionar Pessoa de Contacto"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        self.assertTrue(mock_save.called)
        self.assertEqual(mock_save.call_args[0][1], "contactos_clientes.csv")
        df_gravado = mock_save.call_args[0][0]
        linha = df_gravado.iloc[0]
        self.assertEqual(linha["Cliente_ID"], "C1")
        self.assertEqual(linha["Nome"], "Miguel Pesquera")
        self.assertEqual(linha["Cargo"], "Gestor de Projeto")
        self.assertEqual(linha["Email"], "miguel@cliente.pt")
        self.assertEqual(linha["Telefone"], "912345678")

    def test_lista_mostra_contactos_do_cliente_certo(self):
        contactos_records = [
            {"ID": "CT1", "Cliente_ID": "C1", "Nome": "Pessoa Certa",
             "Cargo": "", "Email": "certa@x.pt", "Telefone": "911",
             "Notas": "", "Criado_Por": "Admin", "Data_Criacao": "01/01/2026"},
            {"ID": "CT2", "Cliente_ID": "OUTRO", "Nome": "Pessoa Errada",
             "Cargo": "", "Email": "errada@x.pt", "Telefone": "922",
             "Notas": "", "Criado_Por": "Admin", "Data_Criacao": "01/01/2026"},
        ]

        def _load_com_contactos(fn, cols, silent=False):
            if fn == "clientes_financeiro.csv":
                return pd.DataFrame(_CLIENTES_RECORDS)
            if fn == "contactos_clientes.csv":
                return pd.DataFrame(contactos_records)
            return pd.DataFrame(columns=cols)

        with patch("mod_fat_clientes.load_db", side_effect=_load_com_contactos), \
             patch("core._gcs_read", return_value=None), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script, args=(_CLIENTES_RECORDS,), default_timeout=30)
            at.run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn("Pessoa Certa", textos)
        self.assertNotIn("Pessoa Errada", textos)


# ─────────────────────────────────────────────────────────────────
# Fase 3 da Identidade Visual — cobertura de ecrã completo
# ─────────────────────────────────────────────────────────────────
# Bloqueia o comportamento atual dos restantes separadores (Emitir
# Fatura, Histórico, Aging, Contratos, Notas de Crédito) antes de
# migrar mod_fat_clientes.py para o THEME central. Não altera nem
# reescreve nada dos testes acima (Gestão de Clientes / Pessoas de
# Contacto) — apenas acrescenta cobertura em falta.
#
# Fora de âmbito, de propósito (Fase 4, mesmo critério de sempre): os
# 4 gráficos Plotly (Pipeline de Faturas, Aging Detalhado, Timeline
# por Cliente) e o PDF de fatura (reportlab).

import core

_OBRAS_RECORDS_FULL = [{"Obra": "Obra Clientes Teste", "Ativa": "Ativa"}]

_FATURAS_CLI_RECORDS_FULL = [
    {"ID": "F1", "Numero": "FT 2026/1", "Tipo": "FT",
     "Data_Emissao": "01/01/2026", "Data_Vencimento": "31/01/2026",
     "Cliente": "Cliente Teste", "NIF_Cliente": "123456789",
     "Morada_Cliente": "", "Obra": "Obra Clientes Teste",
     "Subtotal": "1000", "IVA": "230", "Total": "1230",
     "Estado": "Vencida", "Notas": "", "PDF_b64": "",
     "Enviada_Em": "", "Paga_Em": ""},
    {"ID": "F2", "Numero": "FT 2026/2", "Tipo": "FT",
     "Data_Emissao": "01/02/2026", "Data_Vencimento": "03/03/2026",
     "Cliente": "Cliente Teste", "NIF_Cliente": "123456789",
     "Morada_Cliente": "", "Obra": "Obra Clientes Teste",
     "Subtotal": "2000", "IVA": "460", "Total": "2460",
     "Estado": "Paga", "Notas": "", "PDF_b64": "",
     "Enviada_Em": "", "Paga_Em": "05/03/2026"},
    # Estado "Em Análise" — exercita o ramo "warning" de cor_estado.
    {"ID": "F3", "Numero": "FT 2026/3", "Tipo": "FT",
     "Data_Emissao": "10/08/2026", "Data_Vencimento": "10/09/2026",
     "Cliente": "Cliente Teste", "NIF_Cliente": "123456789",
     "Morada_Cliente": "", "Obra": "Obra Clientes Teste",
     "Subtotal": "500", "IVA": "115", "Total": "615",
     "Estado": "Em Análise", "Notas": "", "PDF_b64": "",
     "Enviada_Em": "", "Paga_Em": ""},
]

_CONTRATOS_RECORDS_FULL = [
    {"ID": "CT1", "Cliente": "Cliente Teste", "Obra": "Obra Clientes Teste",
     "Valor_Total": "50000", "Valor_Faturado": "20000",
     "Retencao_Pct": "5", "Valor_Retido": "2500",
     "Data_Inicio": "01/01/2026", "Data_Fim": "31/12/2026",
     "Data_Libertacao": "15/09/2026", "Estado": "Ativo"},
]


def _fake_load_db_full(fn, cols, silent=False):
    mapa = {
        "clientes_financeiro.csv": _CLIENTES_RECORDS,
        "faturas_clientes.csv": _FATURAS_CLI_RECORDS_FULL,
        "contratos_financeiro.csv": _CONTRATOS_RECORDS_FULL,
    }
    if fn in mapa:
        return pd.DataFrame(mapa[fn])
    return pd.DataFrame(columns=cols)


def _fake_load_db_full_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script_full(obras_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_fat_clientes import render_fat_clientes
    render_fat_clientes(pd.DataFrame(obras_records), pd.DataFrame())


def _run_full(load_db_fn=_fake_load_db_full):
    core._cached_load_db.clear()
    with patch("mod_fat_clientes.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script_full, args=(_OBRAS_RECORDS_FULL,), default_timeout=30)
        at.run()
    return at


class TestRenderFatClientesEcraCompletoSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    os 6 separadores (Emitir Fatura, Histórico, Clientes, Aging,
    Contratos, Notas de Crédito) porque st.tabs() desenha o conteúdo
    de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run_full()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run_full(load_db_fn=_fake_load_db_full_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_fat_clientes.py lê as suas
    cores de core.THEME — nunca mais hexadecimais soltos, um só
    cinzento secundário, sem fundos escuros forçados."""

    def test_css_usa_theme(self):
        at = _run_full()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("surface", "border", "text", "text_secondary",
                      "accent", "warning", "success", "error"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run_full()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#475569", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run_full()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("background:#1E293B", textos)
        self.assertNotIn("background: #1E293B", textos)
        self.assertNotIn("background:#0F172A", textos)
        self.assertNotIn("#F1F5F9", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)

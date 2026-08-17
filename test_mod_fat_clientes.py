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


class TestGestaoClientesSemContactosAtual(unittest.TestCase):
    """Comportamento ATUAL — antes da Fase 5 acrescentar "Pessoas de
    Contacto" ao expander de cada cliente."""

    @classmethod
    def setUpClass(cls):
        cls.at = _run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_expander_do_cliente_existe(self):
        labels = [e.label for e in self.at.expander]
        self.assertTrue(any("Cliente Teste" in l for l in labels))

    def test_nao_existe_secao_pessoas_de_contacto(self):
        textos = " ".join(m.value for m in self.at.markdown)
        self.assertNotIn("Pessoas de Contacto", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

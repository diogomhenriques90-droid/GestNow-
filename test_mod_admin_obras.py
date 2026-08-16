"""
Testes do formulário "➕ Nova Obra" (mod_admin_obras.py).

Bloqueia primeiro o comportamento ATUAL (sem Data de Término Prevista —
só DataInicio, gerada automaticamente na criação), antes da Fase 1 do
Painel de Obra (campos operacionais) acrescentar esse campo.

Não tocam em GCS real: `core._gcs_read`/`_gcs_client` são mockados;
`load_db` de mod_admin_obras é mockado diretamente para devolver
DataFrames vazios com as colunas certas (evita cache cross-teste de
st.cache_data em clientes_financeiro.csv).

Correr:  python -m unittest test_mod_admin_obras -v
"""
import io
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

_CLIENTES_FINANCEIRO_CSV = (
    "ID,Nome,Activo\nC1,Cliente Real X,Sim\n"
).encode("utf-8-sig")


def _fake_gcs_read(fn):
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    return None


def _fake_load_db(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script():
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_obras import render_obras
    vazio = pd.DataFrame()
    render_obras(vazio, vazio, vazio, vazio)


def _run():
    with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
         patch("core._gcs_read", side_effect=_fake_gcs_read), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
    return at


class TestNovaObraAtual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.at = _run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_formulario_nao_tem_campo_de_data(self):
        self.assertEqual(list(self.at.date_input), [])

    def test_criar_obra_grava_sem_data_fim(self):
        # render_obras() chama st.rerun(scope="fragment") ao gravar com
        # sucesso — só válido dentro do wrapper @st.fragment real
        # (mod_admin.py). Nestes testes chama-se render_obras() a direito,
        # por isso o rerun é mockado (o save_db já correu antes dele).
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("streamlit.rerun"), \
             patch("mod_admin_obras.save_db") as mock_save:
            mock_save.return_value = True
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="obra_nome").set_value("Obra Teste Atual").run()
            at.selectbox(key="obra_cliente").set_value("Cliente Real X").run()
            at.button(
                key="FormSubmitter:form_nova_obra-💾 Criar Obra"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        self.assertTrue(mock_save.called)
        df_gravado = mock_save.call_args[0][0]
        self.assertNotIn("DataFim", df_gravado.columns)


if __name__ == "__main__":
    unittest.main(verbosity=2)

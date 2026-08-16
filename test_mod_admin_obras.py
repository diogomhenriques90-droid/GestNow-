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


class TestNovaObraDataTermino(unittest.TestCase):
    """Fase 1 do Painel de Obra (campos operacionais): "Nova Obra" passa a
    pedir Data de Término Prevista (opcional — obras sem termo definido
    continuam a poder ser criadas)."""

    @classmethod
    def setUpClass(cls):
        cls.at = _run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_formulario_tem_data_termino_prevista(self):
        campo = self.at.date_input(key="obra_data_fim")
        self.assertEqual(campo.label, "Data de Término Prevista")
        self.assertIsNone(campo.value)

    def _criar(self, com_data_fim, mock_save):
        # render_obras() chama st.rerun(scope="fragment") ao gravar com
        # sucesso — só válido dentro do wrapper @st.fragment real
        # (mod_admin.py). Nestes testes chama-se render_obras() a direito,
        # por isso o rerun é mockado (o save_db já correu antes dele).
        at = AppTest.from_function(_script, default_timeout=30)
        at.run()
        at.text_input(key="obra_nome").set_value("Obra Teste Fase1").run()
        at.selectbox(key="obra_cliente").set_value("Cliente Real X").run()
        if com_data_fim:
            at.date_input(key="obra_data_fim").set_value(
                pd.Timestamp("2027-01-31").date()).run()
        at.button(
            key="FormSubmitter:form_nova_obra-💾 Criar Obra"
        ).click().run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_criar_obra_com_data_termino_grava_data(self):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("streamlit.rerun"), \
             patch("mod_admin_obras.save_db") as mock_save:
            mock_save.return_value = True
            self._criar(com_data_fim=True, mock_save=mock_save)
        df_gravado = mock_save.call_args[0][0]
        linha = df_gravado[df_gravado["Obra"] == "Obra Teste Fase1"].iloc[0]
        self.assertEqual(linha["DataFim"], "31/01/2027")

    def test_criar_obra_sem_data_termino_grava_vazio(self):
        # Campo é opcional — obras sem termo definido (ex. contratos
        # abertos) continuam a poder ser criadas sem preencher a data.
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("streamlit.rerun"), \
             patch("mod_admin_obras.save_db") as mock_save:
            mock_save.return_value = True
            self._criar(com_data_fim=False, mock_save=mock_save)
        df_gravado = mock_save.call_args[0][0]
        linha = df_gravado[df_gravado["Obra"] == "Obra Teste Fase1"].iloc[0]
        self.assertEqual(linha["DataFim"], "")


def _script_com_obra(obras_records):
    # AppTest.from_function() recompila só o CORPO desta função como um
    # script isolado — não tem acesso a globals do módulo de teste, por
    # isso a obra vem via `args=` (dados simples, serializáveis).
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_obras import render_obras
    vazio = pd.DataFrame()
    render_obras(pd.DataFrame(obras_records), vazio, vazio, vazio)


_OBRAS_RECORDS = [{
    "Obra": "Obra Existente Teste", "Cliente": "Cliente Real X",
    "Local": "Sines", "TipoObra": "Normal", "Ativa": "Ativa",
    "DataInicio": "01/01/2026", "DataFim": "",
    "Codigo": "OBR-001", "Orcamento_ID": "",
}]


# users/inst_acessos_db, para os testes da aba "👷 Alocações" (Fase 3 —
# Responsável de Equipa + Valor Hora auto-preenchido).
_USERS_RECORDS = [{
    "Nome": "Colaborador Caro", "Cargo": "Técnico Instrumentação",
    "PrecoHora": "22.5", "Funcao": "", "Categoria_Operacional": "",
}]


def _script_com_obra_e_users(obras_records, users_records, inst_acessos_records=None):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_obras import render_obras
    vazio = pd.DataFrame()
    inst_acessos_db = pd.DataFrame(inst_acessos_records) \
        if inst_acessos_records else vazio
    render_obras(
        pd.DataFrame(obras_records), vazio,
        pd.DataFrame(users_records), inst_acessos_db
    )


class TestListaObrasAtivasAtual(unittest.TestCase):
    """Comportamento ATUAL da lista "🏭 Obras Ativas" — antes da Fase 2
    do Painel de Obra (campos operacionais) acrescentar a capacidade de
    editar uma obra já criada. Hoje só existe "🗄️ Fechar"."""

    @classmethod
    def setUpClass(cls):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            cls.at = AppTest.from_function(
                _script_com_obra, args=(_OBRAS_RECORDS,), default_timeout=30)
            cls.at.run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_existe_botao_fechar(self):
        labels = [b.label for b in self.at.button]
        self.assertIn("🗄️ Fechar", labels)


class TestEditarObra(unittest.TestCase):
    """Fase 2 do Painel de Obra (campos operacionais): botão "✏️ Editar"
    por obra, abre um formulário com Data de Término Prevista e os 6
    campos operacionais novos (Alojamento, Viatura, Ferramentas, EPIs,
    Descrição dos Trabalhos, Plataforma)."""

    def test_botao_editar_existe(self):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script_com_obra, args=(_OBRAS_RECORDS,), default_timeout=30)
            at.run()
        labels = [b.label for b in at.button]
        self.assertIn("✏️ Editar", labels)

    def _abrir_editar(self):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script_com_obra, args=(_OBRAS_RECORDS,), default_timeout=30)
            at.run()
            at.button(key="editar_obra_Obra Existente Teste").click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        return at

    def test_clicar_editar_mostra_formulario_com_6_campos(self):
        at = self._abrir_editar()
        self.assertEqual(
            at.date_input(key="ed_datafim_Obra Existente Teste").label,
            "Data de Término Prevista")
        for campo, opcoes in [
            ("ed_aloj_Obra Existente Teste", "Alojamento"),
            ("ed_viat_Obra Existente Teste", "Viatura"),
            ("ed_ferr_Obra Existente Teste", "Ferramentas"),
            ("ed_epis_Obra Existente Teste", "EPIs"),
        ]:
            widget = at.selectbox(key=campo)
            self.assertEqual(widget.label, opcoes)
            self.assertEqual(list(widget.options), ["", "CPS", "Cliente", "Outro"])
        self.assertEqual(
            at.text_input(key="ed_plat_Obra Existente Teste").label, "Plataforma")
        self.assertEqual(
            at.text_area(key="ed_desc_Obra Existente Teste").label,
            "Descrição dos Trabalhos")

    def test_guardar_alteracoes_grava_os_6_campos_e_data_fim(self):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("streamlit.rerun"), \
             patch("mod_admin_obras.save_db") as mock_save:
            mock_save.return_value = True
            at = AppTest.from_function(
                _script_com_obra, args=(_OBRAS_RECORDS,), default_timeout=30)
            at.run()
            at.button(key="editar_obra_Obra Existente Teste").click().run()
            at.date_input(key="ed_datafim_Obra Existente Teste").set_value(
                pd.Timestamp("2027-06-30").date()).run()
            at.selectbox(key="ed_aloj_Obra Existente Teste").set_value("CPS").run()
            at.selectbox(key="ed_viat_Obra Existente Teste").set_value("Cliente").run()
            at.selectbox(key="ed_ferr_Obra Existente Teste").set_value("CPS").run()
            at.selectbox(key="ed_epis_Obra Existente Teste").set_value("Outro").run()
            at.text_input(key="ed_plat_Obra Existente Teste").set_value(
                "Andaime 8m").run()
            at.text_area(key="ed_desc_Obra Existente Teste").set_value(
                "Manutenção de instrumentação").run()
            at.button(
                key="FormSubmitter:form_editar_obra_Obra Existente Teste-"
                    "💾 Guardar Alterações"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        self.assertTrue(mock_save.called)
        df_gravado = mock_save.call_args[0][0]
        linha = df_gravado[df_gravado["Obra"] == "Obra Existente Teste"].iloc[0]
        self.assertEqual(linha["DataFim"], "30/06/2027")
        self.assertEqual(linha["Alojamento"], "CPS")
        self.assertEqual(linha["Viatura"], "Cliente")
        self.assertEqual(linha["Ferramentas"], "CPS")
        self.assertEqual(linha["EPIs"], "Outro")
        self.assertEqual(linha["Plataforma"], "Andaime 8m")
        self.assertEqual(linha["Descricao_Trabalhos"], "Manutenção de instrumentação")


class TestAlocacaoPrecoHoraAtual(unittest.TestCase):
    """Comportamento ATUAL da aba "👷 Alocações" — antes da Fase 3
    acrescentar o preenchimento automático do Preço Hora a partir do
    colaborador. Hoje o valor por omissão é sempre 15.0€, independente
    do PrecoHora real do colaborador selecionado (22.5€ na fixture)."""

    @classmethod
    def setUpClass(cls):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            cls.at = AppTest.from_function(
                _script_com_obra_e_users,
                args=(_OBRAS_RECORDS, _USERS_RECORDS),
                default_timeout=30)
            cls.at.run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_preco_hora_nao_reflete_o_colaborador(self):
        campo = self.at.number_input(key="aloc_preco")
        self.assertEqual(campo.label, "Preço Hora na Obra (€)")
        # Colaborador Caro tem PrecoHora=22.5€ em usuarios.csv, mas o
        # campo continua fixo em 15.0€.
        self.assertEqual(campo.value, 15.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

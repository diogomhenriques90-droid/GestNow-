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


class TestAlocacaoPrecoHoraAutoPreenchido(unittest.TestCase):
    """Fase 3 do Painel de Obra (campos operacionais): o "Preço Hora na
    Obra" passa a assumir por omissão o PrecoHora real do colaborador
    selecionado (usuarios.csv), continuando editável (override manual)."""

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

    def test_preco_hora_reflete_o_colaborador_selecionado(self):
        campo = self.at.number_input(key="aloc_preco_Colaborador Caro")
        self.assertEqual(campo.label, "Preço Hora na Obra (€)")
        self.assertEqual(campo.value, 22.5)

    def test_preco_hora_continua_editavel(self):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("streamlit.rerun"), \
             patch("mod_admin_obras.save_db") as mock_save:
            mock_save.return_value = True
            at = AppTest.from_function(
                _script_com_obra_e_users,
                args=(_OBRAS_RECORDS, _USERS_RECORDS),
                default_timeout=30)
            at.run()
            at.number_input(key="aloc_preco_Colaborador Caro").set_value(30.0).run()
            at.button(key="btn_alocar").click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        self.assertTrue(mock_save.called)
        df_gravado = mock_save.call_args[0][0]
        self.assertEqual(df_gravado.iloc[0]["PrecoHora"], 30.0)

    def test_colaborador_sem_precohora_valido_usa_15(self):
        users_sem_preco = [{
            "Nome": "Colaborador Sem Preco", "Cargo": "Técnico",
            "PrecoHora": "", "Funcao": "", "Categoria_Operacional": "",
        }]
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script_com_obra_e_users,
                args=(_OBRAS_RECORDS, users_sem_preco),
                default_timeout=30)
            at.run()
        campo = at.number_input(key="aloc_preco_Colaborador Sem Preco")
        self.assertEqual(campo.value, 15.0)


def _script_com_obra_e_equipa(obras_records, inst_acessos_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    st.session_state[f"a_editar_obra_{obras_records[0]['Obra']}"] = True
    from mod_admin_obras import render_obras
    vazio = pd.DataFrame()
    render_obras(
        pd.DataFrame(obras_records), vazio, vazio,
        pd.DataFrame(inst_acessos_records)
    )


_INST_ACESSOS_RECORDS = [
    {"Obra": "Obra Existente Teste", "Utilizador": "Ana Alocada",
     "Cargo": "Chefe de Equipa", "Ativo": "Sim"},
    {"Obra": "Obra Existente Teste", "Utilizador": "Bruno Alocado",
     "Cargo": "Técnico", "Ativo": "Sim"},
    {"Obra": "Obra Existente Teste", "Utilizador": "Carla Inativa",
     "Cargo": "Técnico", "Ativo": "Não"},
    {"Obra": "Outra Obra", "Utilizador": "Duarte Outra Obra",
     "Cargo": "Técnico", "Ativo": "Sim"},
]


class TestResponsavelDeEquipa(unittest.TestCase):
    """Segunda metade da Fase 3 do Painel de Obra (campos operacionais):
    "Responsável de Equipa" no ecrã Editar Obra, limitado a quem está
    atualmente alocado (Ativo=Sim) a essa obra especificamente."""

    def _abrir(self, obras_records=None, inst_acessos_records=None):
        obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
        inst_acessos_records = inst_acessos_records if inst_acessos_records is not None \
            else _INST_ACESSOS_RECORDS
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script_com_obra_e_equipa,
                args=(obras_records, inst_acessos_records),
                default_timeout=30)
            at.run()
        self.assertFalse(at.exception, msg=str(at.exception))
        return at

    def test_campo_existe(self):
        at = self._abrir()
        campo = at.selectbox(key="ed_resp_Obra Existente Teste")
        self.assertEqual(campo.label, "Responsável de Equipa")

    def test_lista_so_alocados_ativos_desta_obra(self):
        at = self._abrir()
        campo = at.selectbox(key="ed_resp_Obra Existente Teste")
        # Ana e Bruno estão ativos NESTA obra — entram.
        self.assertIn("Ana Alocada", campo.options)
        self.assertIn("Bruno Alocado", campo.options)
        # Carla está inativa; Duarte está alocado a OUTRA obra — de fora.
        self.assertNotIn("Carla Inativa", campo.options)
        self.assertNotIn("Duarte Outra Obra", campo.options)

    def test_obra_sem_equipa_fica_so_com_opcao_vazia(self):
        at = self._abrir(inst_acessos_records=[])
        campo = at.selectbox(key="ed_resp_Obra Existente Teste")
        self.assertEqual(list(campo.options), ["— Nenhum —"])

    def test_valor_ja_gravado_preservado_mesmo_sem_alocacao_atual(self):
        # Responsável designado anteriormente, entretanto desalocado —
        # não desaparece silenciosamente da lista.
        obras_com_resp = [{**_OBRAS_RECORDS[0], "Responsavel_Equipa": "Carla Inativa"}]
        at = self._abrir(obras_records=obras_com_resp)
        campo = at.selectbox(key="ed_resp_Obra Existente Teste")
        self.assertEqual(campo.value, "Carla Inativa")
        self.assertIn("Carla Inativa", campo.options)

    def test_guardar_grava_responsavel_escolhido(self):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("streamlit.rerun"), \
             patch("mod_admin_obras.save_db") as mock_save:
            mock_save.return_value = True
            at = AppTest.from_function(
                _script_com_obra_e_equipa,
                args=(_OBRAS_RECORDS, _INST_ACESSOS_RECORDS),
                default_timeout=30)
            at.run()
            at.selectbox(key="ed_resp_Obra Existente Teste").set_value("Ana Alocada").run()
            at.button(
                key="FormSubmitter:form_editar_obra_Obra Existente Teste-"
                    "💾 Guardar Alterações"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        df_gravado = mock_save.call_args[0][0]
        linha = df_gravado[df_gravado["Obra"] == "Obra Existente Teste"].iloc[0]
        self.assertEqual(linha["Responsavel_Equipa"], "Ana Alocada")

    def test_guardar_sem_escolher_grava_vazio(self):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("streamlit.rerun"), \
             patch("mod_admin_obras.save_db") as mock_save:
            mock_save.return_value = True
            at = AppTest.from_function(
                _script_com_obra_e_equipa,
                args=(_OBRAS_RECORDS, _INST_ACESSOS_RECORDS),
                default_timeout=30)
            at.run()
            at.button(
                key="FormSubmitter:form_editar_obra_Obra Existente Teste-"
                    "💾 Guardar Alterações"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        df_gravado = mock_save.call_args[0][0]
        linha = df_gravado[df_gravado["Obra"] == "Obra Existente Teste"].iloc[0]
        self.assertEqual(linha["Responsavel_Equipa"], "")


_REQ_OBRAS_RECORDS = [{
    "ID": "RQ1", "Obra": "Obra Existente Teste", "Tipo_Obra": "Refinaria / Petroquímica",
    "Documentos_Obrigatorios": "Cartão de Cidadão|Formação ATEX (áreas classificadas)",
    "Nivel_Seguranca": "Alto",
    "Instrucoes": "Zona ATEX — formação obrigatória antes de entrar.",
    "Atualizado_Em": "01/01/2026",
}]


def _load_db_com_requisitos(fn, cols, silent=False):
    if fn == "acessos_requisitos_obras.csv":
        return pd.DataFrame(_REQ_OBRAS_RECORDS)
    return pd.DataFrame(columns=cols)


class TestRequisitosDeAcessoSoLeitura(unittest.TestCase):
    """Fase 4 do Painel de Obra (campos operacionais): o ecrã "Editar
    Obra" passa a mostrar (só leitura) os Requisitos Adicionais e
    Formações/Documentos Obrigatórios já configurados em Gestão de
    Acessos › ⚙️ Requisitos de Acesso por Obra — sem duplicar a edição
    aqui (mesmo princípio seguido nas Diárias, Fase 2)."""

    def test_sem_requisitos_configurados_mostra_aviso(self):
        with patch("mod_admin_obras.load_db", side_effect=_fake_load_db), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script_com_obra_e_equipa,
                args=(_OBRAS_RECORDS, _INST_ACESSOS_RECORDS),
                default_timeout=30)
            at.run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos_info = " ".join(i.value for i in at.info)
        self.assertIn("Sem requisitos de acesso configurados", textos_info)
        self.assertIn("Gestão de Acessos", textos_info)

    def test_com_requisitos_mostra_documentos_e_instrucoes_so_leitura(self):
        with patch("mod_admin_obras.load_db", side_effect=_load_db_com_requisitos), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script_com_obra_e_equipa,
                args=(_OBRAS_RECORDS, _INST_ACESSOS_RECORDS),
                default_timeout=30)
            at.run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos_caption = " ".join(c.value for c in at.caption)
        self.assertIn("Cartão de Cidadão", textos_caption)
        self.assertIn("Formação ATEX (áreas classificadas)", textos_caption)
        self.assertIn("Zona ATEX", textos_caption)
        # Não é um campo editável aqui — não deve existir nenhum widget
        # para Requisitos/Formações neste ecrã (multiselect ou
        # text_area próprios, distintos de "Descrição dos Trabalhos").
        self.assertEqual(list(at.multiselect), [])
        labels_text_area = [t.label for t in at.text_area]
        self.assertNotIn("Requisitos Adicionais", labels_text_area)
        self.assertNotIn("Instruções", labels_text_area)


if __name__ == "__main__":
    unittest.main(verbosity=2)

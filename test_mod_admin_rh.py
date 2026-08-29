"""
Testes do comportamento ATUAL das abas "Gestão Individual" e "Dados Legais"
do módulo de RH (mod_admin_rh.py), antes da sua fusão numa única aba.

Objetivo: bloquear o que já funciona hoje — estrutura das abas, proveniência
dos dados (usuarios.csv vs colaboradores_rh.csv), o fallback de apresentação
em Dados Legais, e que cada aba grava apenas no seu próprio ficheiro — para
que a fusão não altere nenhum destes comportamentos sem se dar por isso.

Não tocam em GCS real: `_gcs_read`/`_gcs_write` são mockados com CSVs fixos
em memória. `render_admin_rh` é invocado diretamente (sem passar por
app.py/mod_admin.py), pelo que a verificação de permissões `tem_permissao`
não entra em jogo.

Correr:  python -m unittest test_mod_admin_rh -v
"""
import hashlib
import io
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import core

NOME = "Ana Teste"
SLUG = hashlib.md5(NOME.encode()).hexdigest()[:8]

# ── Fixtures ────────────────────────────────────────────────────────────────
# usuarios.csv: fonte "oficial" para os campos partilhados hoje editados em
# Gestão Individual.
_USUARIOS_CSV = (
    "Nome,Tipo,Cargo,Email,Telefone,NIF,NISS,CC,CC_Validade,DataNasc,"
    "Morada,Localidade,Concelho,Codigo_Postal,Banco_IBAN,Nacionalidade,"
    "Estado_Civil,PrecoHora,Local_Obra,Cliente_Obra\n"
    "Ana Teste,Técnico,Instrumentista,ana@usuarios.pt,911111111,123456789,"
    "11122233344,12345678,01/01/2030,15/05/1990,"
    "Rua A 100,Lisboa,Lisboa,1000-001,PT50000000000000000000000,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X\n"
).encode("utf-8-sig")

# colaboradores_rh.csv: NIF/CC/CC_Validade/Email/Morada/Nacionalidade/DataNasc
# ficam vazios de propósito (para testar o fallback de apresentação vindo de
# usuarios.csv). NISS e Estado_Civil ficam preenchidos com valores DIFERENTES
# dos de usuarios.csv, para confirmar que um valor próprio não é substituído.
_RH_CSV = (
    "Nome,NIF,NISS,CC,CC_Validade,Email,Morada,Nacionalidade,Estado_Civil,"
    "DataNasc,Tipo_Contrato,Salario_Base,Estado_Fiscal\n"
    "Ana Teste,,99999999999,,,,,,Casado(a),,Sem Termo,1200,Normal\n"
).encode("utf-8-sig")

# obras_lista.csv: duas obras reais, para os testes de Local_Obra/Cliente
# derivado (Fase 1 — Painel de Obra: campos operacionais).
_OBRAS_LISTA_CSV = (
    "Obra,Cliente,Ativa\n"
    "Obra Real X,Cliente Real X,Ativa\n"
    "Obra Real Y,Cliente Real Y,Ativa\n"
).encode("utf-8-sig")

# clientes_financeiro.csv: fonte canónica usada por cliente_select().
_CLIENTES_FINANCEIRO_CSV = (
    "ID,Nome,Activo\n"
    "C1,Cliente Real X,Sim\n"
    "C2,Cliente Real Y,Sim\n"
).encode("utf-8-sig")


def _fake_gcs_read(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    return None


def _script():
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    from mod_admin_rh import render_admin_rh
    vazio = pd.DataFrame()
    render_admin_rh(vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
                     vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
                     vazio, vazio, vazio, vazio)


def _run():
    # load_db() usa @st.cache_data — sem limpar, um ficheiro de teste
    # corrido antes deste no mesmo processo (ex. test_core.py) pode deixar
    # em cache um resultado para a mesma (ficheiro, colunas, _v) que aqui é
    # mockado de forma diferente.
    core._cached_load_db.clear()
    at = AppTest.from_function(_script, default_timeout=30)
    at.run()
    return at


class TestEstruturaAbas(unittest.TestCase):
    """Estrutura e proveniência dos dados, sem gravar nada."""

    @classmethod
    def setUpClass(cls):
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            cls.at = _run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_aba_ficha_do_colaborador_unifica_gestao_e_dados_legais(self):
        labels = [t.label for t in self.at.tabs]
        self.assertIn("Colaboradores", labels)
        self.assertIn("Ficha do Colaborador", labels)
        self.assertNotIn("Gestão Individual", labels)
        self.assertNotIn("Dados Legais", labels)
        # Conteúdo de ambas as secções antigas continua presente, agora
        # dentro da mesma aba.
        markdown_textos = " ".join(m.value for m in self.at.markdown)
        self.assertIn("Dados Legais e Fiscais", markdown_textos)

    def test_nome_bloqueado_em_gestao_individual(self):
        campo_nome = self.at.text_input(key=f"gi_nome_{SLUG}")
        self.assertTrue(campo_nome.disabled)
        self.assertEqual(campo_nome.value, NOME)

    def test_gestao_individual_mostra_dados_de_usuarios_csv(self):
        # NIF/CC/CC_Validade/NISS foram fundidos na secção "🪪 Documentos e
        # Identificação Legal" (dl_*) — deixaram de existir campos gi_nif/
        # gi_cc/gi_niss próprios.
        self.assertEqual(self.at.text_input(key=f"gi_email_{SLUG}").value,
                          "ana@usuarios.pt")
        self.assertEqual(self.at.text_input(key=f"gi_morada_{SLUG}").value,
                          "Rua A 100")
        self.assertEqual(self.at.text_input(key=f"gi_iban_{SLUG}").value,
                          "PT50000000000000000000000")
        self.assertEqual(self.at.text_input(key=f"gi_preco_{SLUG}").value, "15")
        # Local de Obra é agora um dropdown de obras reais (obra_select).
        # "Refinaria X" não existe em obras_lista.csv — fica preservado na
        # lista em runtime (não se perde o valor gravado), mas o Cliente
        # derivado fica "—" por não haver Obra correspondente.
        self.assertEqual(self.at.selectbox(key=f"gi_local_{SLUG}").value,
                          "Refinaria X")
        self.assertEqual(self.at.text_input(key=f"gi_cliente_{SLUG}").value, "—")
        self.assertTrue(self.at.text_input(key=f"gi_cliente_{SLUG}").disabled)

    def test_dados_legais_mostra_dados_proprios_quando_preenchidos(self):
        # Estado_Civil e NISS têm valor próprio em colaboradores_rh.csv,
        # diferente do que está em usuarios.csv — não deve ser substituído.
        self.assertEqual(self.at.selectbox(key=f"dl_estcivil_{SLUG}").value,
                          "Casado(a)")
        self.assertEqual(self.at.text_input(key=f"dl_niss_{SLUG}").value,
                          "99999999999")
        # Salario_Base mudou-se para a secção "💼 Profissional" (gi_salb),
        # lado a lado com PrecoHora.
        self.assertEqual(self.at.text_input(key=f"gi_salb_{SLUG}").value, "1200")

    def test_dados_legais_usa_fallback_de_usuarios_quando_vazio(self):
        # NIF/CC estão vazios em colaboradores_rh.csv — o campo fundido
        # (dual-write) pré-preenche com o valor de usuarios.csv.
        self.assertEqual(self.at.text_input(key=f"dl_nif_{SLUG}").value,
                          "123456789")
        self.assertEqual(self.at.text_input(key=f"dl_cc_{SLUG}").value,
                          "12345678")

    def test_datanasc_lado_a_lado_sem_fallback_entre_ficheiros(self):
        # DataNasc não é dual-write: cada lado mostra o seu próprio valor
        # bruto, mesmo que um esteja vazio (sem se copiar um para o outro).
        self.assertEqual(self.at.text_input(key=f"dl_datanasc_u_{SLUG}").value,
                          "15/05/1990")
        self.assertEqual(self.at.text_input(key=f"dl_datanasc_rh_{SLUG}").value,
                          "")

    def test_seletor_unico_de_colaborador_para_a_ficha_inteira(self):
        # Um único seletor (rh_gestao_sel) escolhe o colaborador tanto para a
        # secção de Gestão Individual como para a de Dados Legais — não há
        # um segundo seletor "dl_colab_sel" duplicado.
        self.assertEqual(self.at.session_state['rh_colaborador_sel'], NOME)
        self.assertEqual(self.at.selectbox(key="rh_gestao_sel").value, NOME)
        with self.assertRaises(KeyError):
            self.at.selectbox(key="dl_colab_sel")


class TestFusaoContactosMorada(unittest.TestCase):
    """Secção fundida "📍 Contactos & Morada": Email, Morada, Localidade e
    Codigo_Postal são dual-write; Telefone e Concelho só existem em
    usuarios.csv (sem equivalente em colaboradores_rh.csv)."""

    def _submeter(self, alteracoes: dict):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = _run()
            for key, valor in alteracoes.items():
                at.text_input(key=key).set_value(valor).run()
            at.button(
                key=f"FormSubmitter:gi_form_ident_{SLUG}-Guardar Contactos & Morada"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        return writes

    def test_email_editado_grava_nos_dois_ficheiros(self):
        writes = self._submeter({f"gi_email_{SLUG}": "novo@x.pt"})
        self.assertIn(b"novo@x.pt", writes["usuarios.csv"])
        self.assertIn(b"novo@x.pt", writes["colaboradores_rh.csv"])

    def test_morada_editada_grava_nos_dois_ficheiros(self):
        writes = self._submeter({f"gi_morada_{SLUG}": "Rua Nova 5"})
        self.assertIn(b"Rua Nova 5", writes["usuarios.csv"])
        self.assertIn(b"Rua Nova 5", writes["colaboradores_rh.csv"])

    def test_telefone_so_grava_em_usuarios(self):
        writes = self._submeter({f"gi_tel_{SLUG}": "935555555"})
        self.assertIn(b"935555555", writes["usuarios.csv"])
        self.assertNotIn(b"935555555", writes["colaboradores_rh.csv"])

    def test_concelho_so_grava_em_usuarios(self):
        writes = self._submeter({f"gi_concelho_{SLUG}": "Sintra"})
        self.assertIn(b"Sintra", writes["usuarios.csv"])
        self.assertNotIn(b"Sintra", writes["colaboradores_rh.csv"])


class TestFusaoBancarios(unittest.TestCase):
    """Secção fundida "🏦 Bancários": Banco_Nome e Banco_IBAN são
    dual-write (usuarios.csv fonte, espelho em colaboradores_rh.csv)."""

    def _submeter(self, alteracoes: dict):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = _run()
            for key, valor in alteracoes.items():
                at.text_input(key=key).set_value(valor).run()
            at.button(
                key=f"FormSubmitter:gi_form_banco_{SLUG}-Guardar Dados Bancários"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        return writes

    def test_iban_editado_grava_nos_dois_ficheiros(self):
        writes = self._submeter({f"gi_iban_{SLUG}": "PT50111122223333444455566"})
        self.assertIn(b"PT50111122223333444455566", writes["usuarios.csv"])
        self.assertIn(b"PT50111122223333444455566", writes["colaboradores_rh.csv"])

    def test_banco_nome_editado_grava_nos_dois_ficheiros(self):
        writes = self._submeter({f"gi_banco_{SLUG}": "Banco Teste"})
        self.assertIn(b"Banco Teste", writes["usuarios.csv"])
        self.assertIn(b"Banco Teste", writes["colaboradores_rh.csv"])


class TestFusaoProfissional(unittest.TestCase):
    """Secção fundida "💼 Profissional": Tipo/Cargo (Permissões APP),
    PrecoHora/Salario_Base e Local_Obra/Local_Trabalho ficam lado a lado,
    cada par com dois registos independentes, sem sincronização."""

    def _submeter_profissional(self, alteracoes: dict):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = _run()
            for key, valor in alteracoes.items():
                # gi_local_* é agora um selectbox (obra_select); os
                # restantes campos desta secção continuam text_input.
                try:
                    at.text_input(key=key).set_value(valor).run()
                except KeyError:
                    at.selectbox(key=key).set_value(valor).run()
            at.button(
                key=f"FormSubmitter:gi_form_prof_{SLUG}-Guardar Profissional"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        return writes

    def test_preco_hora_nao_e_espelhado_em_colaboradores_rh(self):
        writes = self._submeter_profissional({f"gi_preco_{SLUG}": "22.5"})
        self.assertIn(b"22.5", writes["usuarios.csv"])
        self.assertNotIn(b"22.5", writes["colaboradores_rh.csv"])

    def test_salario_base_nao_e_espelhado_em_usuarios(self):
        writes = self._submeter_profissional({f"gi_salb_{SLUG}": "1350"})
        self.assertIn(b"1350", writes["colaboradores_rh.csv"])
        self.assertNotIn(b"1350", writes["usuarios.csv"])

    def test_local_obra_nao_e_espelhado_em_colaboradores_rh(self):
        writes = self._submeter_profissional({f"gi_local_{SLUG}": "Obra Real Y"})
        self.assertIn(b"Obra Real Y", writes["usuarios.csv"])
        self.assertNotIn(b"Obra Real Y", writes["colaboradores_rh.csv"])

    def test_cliente_e_derivado_da_obra_escolhida_ao_gravar(self):
        # Ao escolher uma Obra real, o Cliente gravado em usuarios.csv é o
        # dessa obra (obras_lista.csv), não um valor escolhido à parte.
        writes = self._submeter_profissional({f"gi_local_{SLUG}": "Obra Real Y"})
        self.assertIn(b"Cliente Real Y", writes["usuarios.csv"])

    def test_local_trabalho_nao_e_espelhado_em_usuarios(self):
        writes = self._submeter_profissional({f"gi_localtrab_{SLUG}": "Obra RH"})
        self.assertIn(b"Obra RH", writes["colaboradores_rh.csv"])
        self.assertNotIn(b"Obra RH", writes["usuarios.csv"])

    def test_permissoes_app_continua_a_gravar_so_em_usuarios(self):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = _run()
            at.selectbox(key="rh_novo_cargo").set_value("Engenheiro").run()
            at.button(key="btn_guardar_funcao").click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn(b"Engenheiro", writes["usuarios.csv"])
        self.assertNotIn("colaboradores_rh.csv", writes)


class TestFusaoIdentificacao(unittest.TestCase):
    """Secção fundida "🪪 Documentos e Identificação Legal": os campos
    partilhados (NIF, NISS, CC, CC_Validade, Nacionalidade, Estado_Civil)
    são dual-write; DataNasc fica lado a lado, sem sincronização."""

    def _submeter(self, alteracoes: dict):
        """Aplica `alteracoes` (key do widget -> novo valor) aos campos do
        formulário de Identificação fundido e submete-o. Devolve o conteúdo
        gravado em cada ficheiro."""
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = _run()
            for key, valor in alteracoes.items():
                at.text_input(key=key).set_value(valor).run()
            at.button(
                key=f"FormSubmitter:dl_form_ident_{SLUG}-Guardar Identificação"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        return writes

    def test_campo_partilhado_editado_grava_nos_dois_ficheiros(self):
        writes = self._submeter({f"dl_nif_{SLUG}": "111222333"})
        self.assertIn(b"111222333", writes["usuarios.csv"])
        self.assertIn(b"111222333", writes["colaboradores_rh.csv"])

    def test_datanasc_usuarios_nao_e_espelhado_em_colaboradores_rh(self):
        writes = self._submeter({f"dl_datanasc_u_{SLUG}": "20/12/1985"})
        self.assertIn(b"20/12/1985", writes["usuarios.csv"])
        self.assertNotIn(b"20/12/1985", writes["colaboradores_rh.csv"])

    def test_datanasc_colaboradores_rh_nao_e_espelhado_em_usuarios(self):
        writes = self._submeter({f"dl_datanasc_rh_{SLUG}": "03/03/1975"})
        self.assertIn(b"03/03/1975", writes["colaboradores_rh.csv"])
        self.assertNotIn(b"03/03/1975", writes["usuarios.csv"])


class TestSaveDual(unittest.TestCase):
    """`_save_dual` — helper novo que grava em usuarios.csv (fonte) e espelha
    os mesmos campos em colaboradores_rh.csv. Usado pela ficha unificada."""

    def _call(self, updates, rh_csv=_RH_CSV, extra_usuarios=None, extra_rh=None):
        import mod_admin_rh as m

        def _gcs_read(fn):
            if fn == "usuarios.csv":
                return io.BytesIO(_USUARIOS_CSV)
            if fn == "colaboradores_rh.csv":
                return io.BytesIO(rh_csv) if rh_csv is not None else None
            return None

        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        with patch("mod_admin_rh._gcs_read", side_effect=_gcs_read), \
             patch("core._gcs_read", side_effect=_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            ok = m._save_dual(NOME, updates,
                               extra_usuarios=extra_usuarios, extra_rh=extra_rh)
        return ok, writes

    def test_grava_em_usuarios_e_espelha_em_colaboradores_rh(self):
        ok, writes = self._call({"Email": "novo@x.pt", "NIF": "999888777"})
        self.assertTrue(ok)
        self.assertIn("usuarios.csv", writes)
        self.assertIn("colaboradores_rh.csv", writes)
        self.assertIn(b"novo@x.pt", writes["usuarios.csv"])
        self.assertIn(b"novo@x.pt", writes["colaboradores_rh.csv"])
        self.assertIn(b"999888777", writes["colaboradores_rh.csv"])

    def test_cria_linha_em_colaboradores_rh_se_nao_existir(self):
        ok, writes = self._call({"Email": "a@x.pt"}, rh_csv=None)
        self.assertTrue(ok)
        self.assertIn(b"Ana Teste", writes["colaboradores_rh.csv"])
        self.assertIn(b"a@x.pt", writes["colaboradores_rh.csv"])

    def test_extra_usuarios_so_grava_em_usuarios_csv(self):
        # Campo "lado a lado" cujo lado usuarios.csv não é espelhado.
        ok, writes = self._call({"NIF": "999888777"},
                                 extra_usuarios={"DataNasc": "01/01/2000"})
        self.assertTrue(ok)
        self.assertIn(b"01/01/2000", writes["usuarios.csv"])
        self.assertNotIn(b"01/01/2000", writes["colaboradores_rh.csv"])

    def test_extra_rh_so_grava_em_colaboradores_rh_csv(self):
        # Campo só-RH (ex.: Genero) gravado no mesmo espelho, sem tocar em
        # usuarios.csv.
        ok, writes = self._call({"NIF": "999888777"},
                                 extra_rh={"Genero": "Feminino"})
        self.assertTrue(ok)
        self.assertNotIn(b"Feminino", writes["usuarios.csv"])
        self.assertIn(b"Feminino", writes["colaboradores_rh.csv"])

    def test_colaborador_inexistente_nao_grava_nada(self):
        import mod_admin_rh as m

        def _gcs_read(fn):
            if fn == "usuarios.csv":
                return io.BytesIO(_USUARIOS_CSV)
            return None

        with patch("mod_admin_rh._gcs_read", side_effect=_gcs_read), \
             patch("core._gcs_read", side_effect=_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write") as mock_write:
            ok = m._save_dual("Não Existe", {"Email": "x@x.pt"})
        self.assertFalse(ok)
        mock_write.assert_not_called()


def _script_criar():
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    st.session_state['show_criar_colab'] = True
    from mod_admin_rh import render_admin_rh
    vazio = pd.DataFrame()
    render_admin_rh(vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
                     vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
                     vazio, vazio, vazio, vazio)


class TestCriarColaboradorObraReal(unittest.TestCase):
    """Formulário "➕ Novo" (criar colaborador, aba Colaboradores) — Fase 1
    do Painel de Obra (campos operacionais): Local da Obra passa a dropdown
    de obras reais (obra_select) e Cliente passa a derivado (só leitura),
    tal como já acontece na Ficha do Colaborador. Substitui o antigo par
    independente texto-livre/dropdown."""

    @classmethod
    def setUpClass(cls):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            cls.at = AppTest.from_function(_script_criar, default_timeout=30)
            cls.at.run()

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_local_da_obra_e_dropdown_de_obras_reais(self):
        campo = self.at.selectbox(key="nc_local")
        self.assertEqual(campo.label, "Local da Obra *")
        self.assertIn("Obra Real X", campo.options)
        self.assertIn("Obra Real Y", campo.options)

    def test_cliente_e_so_leitura_e_comeca_vazio(self):
        campo = self.at.text_input(key="nc_cliente")
        self.assertEqual(campo.label, "Cliente *")
        self.assertTrue(campo.disabled)
        self.assertEqual(campo.value, "—")

    def test_criar_colaborador_deriva_cliente_da_obra_escolhida(self):
        # Nota: "Cliente" (dentro do form) só reflete a Obra escolhida no
        # momento do submit — widgets dentro de st.form não se recalculam
        # entre si antes disso (comportamento já existente no resto da
        # app, ex. cliente_select). Por isso só se verifica o resultado
        # final gravado, não uma pré-visualização a meio do formulário.
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(_script_criar, default_timeout=30)
            at.run()
            at.text_input(key="nc_nome").set_value("Novo Colaborador Teste").run()
            at.text_input(key="nc_tel").set_value("911111111").run()
            at.text_input(key="nc_pwd").set_value("segredo123").run()
            at.selectbox(key="nc_local").set_value("Obra Real Y").run()
            at.button(
                key="FormSubmitter:form_criar_colab-Criar Colaborador"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        gravado = writes.get("usuarios.csv", b"")
        self.assertIn(b"Obra Real Y", gravado)
        self.assertIn(b"Cliente Real Y", gravado)

    def test_sem_obra_escolhida_bloqueia_criacao(self):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write") as mock_write:
            at = AppTest.from_function(_script_criar, default_timeout=30)
            at.run()
            at.text_input(key="nc_nome").set_value("Sem Obra Teste").run()
            at.text_input(key="nc_tel").set_value("911111111").run()
            at.text_input(key="nc_pwd").set_value("segredo123").run()
            at.button(
                key="FormSubmitter:form_criar_colab-Criar Colaborador"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        mock_write.assert_not_called()


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_admin_rh.py lê as suas cores
    de core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados nos cartões de
    colaborador, cabeçalho da ficha, aviso de remoção e cartão da
    Lista Negra. Também remove um bloco CSS local redundante (fundo/
    texto do dropdown e do botão de download) — core.py já define os
    mesmos seletores (data-baseweb) centralmente via THEME desde a
    Fase 1.

    A aba "🎓 Gestão de Formações" (dentro do RH, a última) chama
    render_formacoes(), de mod_admin_formacoes.py — módulo à parte,
    ainda por migrar (~99 cores, mais à frente na lista da Fase 3).
    st.tabs() desenha o conteúdo de todas as abas de uma vez, por
    isso o texto dessa aba aparece sempre a seguir ao de
    mod_admin_rh.py no AppTest — os testes abaixo param a recolha no
    início dessa aba (marcador "Gestão de Formações"), para não
    apanhar cores que não são deste módulo."""

    @classmethod
    def setUpClass(cls):
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            cls.at = _run()
        partes = []
        for m in cls.at.markdown:
            if "Gestão de Formações" in m.value:
                break
            partes.append(m.value)
        cls.textos = " ".join(partes)

    def test_css_local_redundante_removido(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))
        self.assertNotIn("#111827", self.textos)
        self.assertNotIn("#D1D5DB", self.textos)

    def test_css_usa_theme(self):
        for chave in ("surface", "border", "text", "text_secondary", "error"):
            self.assertIn(core.THEME[chave], self.textos)

    def test_um_so_cinzento_secundario(self):
        self.assertNotIn("#64748B", self.textos)
        self.assertNotIn("#94A3B8", self.textos)
        self.assertIn(core.THEME["text_secondary"], self.textos)

    def test_sem_fundo_escuro_forcado(self):
        self.assertNotIn("#334155", self.textos)
        self.assertNotIn("#FCA5A5", self.textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

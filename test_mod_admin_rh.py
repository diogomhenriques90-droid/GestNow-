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


class TestCriarColaboradorPrecoHoraSemDefaultMagico(unittest.TestCase):
    """O campo "Preço Hora (€)" no formulário de criar colaborador deixa
    de arrancar a 15 (valor mágico que se confundia com preços reais
    negociados a €15/h — ver alocações). Passa a arrancar a 0. Ao
    contrário da Alocação (mod_admin_obras.py), este campo continua
    dentro de "Dados opcionais" — não bloqueia a criação do colaborador
    ficar a 0, só deixa de sugerir um valor que ninguém escolheu."""

    def test_campo_arranca_a_zero(self):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(_script_criar, default_timeout=30)
            at.run()
        campo = at.number_input(key="nc_preco")
        self.assertEqual(campo.label, "Preço Hora (€)")
        self.assertEqual(campo.value, 0.0)

    def test_criar_colaborador_com_preco_a_zero_nao_bloqueia(self):
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
            at.text_input(key="nc_nome").set_value("Preco Zero Teste").run()
            at.text_input(key="nc_tel").set_value("911111111").run()
            at.text_input(key="nc_pwd").set_value("segredo123").run()
            at.selectbox(key="nc_local").set_value("Obra Real Y").run()
            at.button(
                key="FormSubmitter:form_criar_colab-Criar Colaborador"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        gravado = writes.get("usuarios.csv", b"")
        self.assertIn(b"Preco Zero Teste", gravado)


class TestCriarColaboradorNomeDuplicado(unittest.TestCase):
    """Fase 0: a verificação de nome duplicado no "Criar Colaborador"
    passou a normalizar (via `_norm_nome_cliente`, reaproveitada de
    core.py) antes de comparar — "Ana Teste" já existe na fixture
    (_USUARIOS_CSV), e uma variante só de maiúsculas ("ANA TESTE") passa
    a ser apanhada."""

    def _submeter(self, nome_novo):
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
            at.text_input(key="nc_nome").set_value(nome_novo).run()
            at.text_input(key="nc_tel").set_value("911111111").run()
            at.text_input(key="nc_pwd").set_value("segredo123").run()
            at.selectbox(key="nc_local").set_value("Obra Real Y").run()
            at.button(
                key="FormSubmitter:form_criar_colab-Criar Colaborador"
            ).click().run()
        return at, writes

    def test_nome_exatamente_igual_e_bloqueado(self):
        at, writes = self._submeter("Ana Teste")
        self.assertFalse(at.exception, msg=str(at.exception))
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Já existe um colaborador", textos_erro)
        self.assertNotIn("usuarios.csv", writes)

    def test_variante_so_de_maiusculas_e_agora_apanhada(self):
        # Antes da Fase 0, "ANA TESTE" passava despercebido como se fosse
        # outra pessoa. Agora a normalização apanha-o.
        at, writes = self._submeter("ANA TESTE")
        self.assertFalse(at.exception, msg=str(at.exception))
        textos_erro = " ".join(m.value for m in at.error)
        self.assertIn("Já existe um colaborador", textos_erro)
        self.assertNotIn("usuarios.csv", writes)


_USUARIOS_PIN_CSV = (
    "Nome,Tipo,Cargo,Email,Telefone,NIF,NISS,CC,CC_Validade,DataNasc,"
    "Morada,Localidade,Concelho,Codigo_Postal,Banco_IBAN,Nacionalidade,"
    "Estado_Civil,PrecoHora,Local_Obra,Cliente_Obra,"
    "ID,Numero_Colaborador,PIN,Bloqueado,Bloqueado_Em\n"
    "Ana Teste,Técnico,Instrumentista,ana@usuarios.pt,911111111,123456789,"
    "11122233344,12345678,01/01/2030,15/05/1990,"
    "Rua A 100,Lisboa,Lisboa,1000-001,PT50000000000000000000000,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X,"
    "A1B2C3D4,12345,,,\n"
).encode("utf-8-sig")

_USUARIOS_PIN_JA_DEFINIDO_CSV = (
    "Nome,Tipo,Cargo,Email,Telefone,NIF,NISS,CC,CC_Validade,DataNasc,"
    "Morada,Localidade,Concelho,Codigo_Postal,Banco_IBAN,Nacionalidade,"
    "Estado_Civil,PrecoHora,Local_Obra,Cliente_Obra,"
    "ID,Numero_Colaborador,PIN,Bloqueado,Bloqueado_Em\n"
    "Ana Teste,Técnico,Instrumentista,ana@usuarios.pt,911111111,123456789,"
    "11122233344,12345678,01/01/2030,15/05/1990,"
    "Rua A 100,Lisboa,Lisboa,1000-001,PT50000000000000000000000,Portuguesa,"
    f"Solteiro(a),15,Refinaria X,Cliente X,"
    f"A1B2C3D4,12345,{core.hp('9999')},,\n"
).encode("utf-8-sig")

_USUARIOS_PIN_BLOQUEADA_CSV = (
    "Nome,Tipo,Cargo,Email,Telefone,NIF,NISS,CC,CC_Validade,DataNasc,"
    "Morada,Localidade,Concelho,Codigo_Postal,Banco_IBAN,Nacionalidade,"
    "Estado_Civil,PrecoHora,Local_Obra,Cliente_Obra,"
    "ID,Numero_Colaborador,PIN,Bloqueado,Bloqueado_Em\n"
    "Ana Teste,Técnico,Instrumentista,ana@usuarios.pt,911111111,123456789,"
    "11122233344,12345678,01/01/2030,15/05/1990,"
    "Rua A 100,Lisboa,Lisboa,1000-001,PT50000000000000000000000,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X,"
    "A1B2C3D4,12345,,Sim,01/09/2026 10:00\n"
).encode("utf-8-sig")


def _fake_gcs_read_pin(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_PIN_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    return None


def _fake_gcs_read_pin_ja_definido(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_PIN_JA_DEFINIDO_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    return None


def _fake_gcs_read_pin_bloqueada(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_PIN_BLOQUEADA_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    return None


class TestRedefinirPin(unittest.TestCase):
    """Fase 1 (login por número): bloco "Redefinir PIN" ao lado de
    "Redefinir Password", com ID/Número de colaborador visíveis como
    texto só de leitura — mesmo padrão já usado para Password."""

    def _run_com(self, fake_read):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=fake_read), \
             patch("core._gcs_read", side_effect=fake_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
        return at

    def test_mostra_id_e_numero_colaborador(self):
        at = self._run_com(_fake_gcs_read_pin)
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn("A1B2C3D4", textos)
        self.assertIn("12345", textos)

    def test_sem_pin_mostra_gerar_sem_aviso(self):
        # Ana Teste não tem PIN na fixture — o bloco chama-se "Gerar
        # PIN", não "Redefinir", e não mostra aviso de invalidação
        # (não há nada para invalidar).
        at = self._run_com(_fake_gcs_read_pin)
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertTrue(at.button(key="btn_gerar_pin"))
        textos_aviso = " ".join(m.value for m in at.warning)
        self.assertNotIn("invalida", textos_aviso)

    def test_com_pin_existente_mostra_redefinir_com_aviso(self):
        at = self._run_com(_fake_gcs_read_pin_ja_definido)
        self.assertTrue(at.button(key="btn_gerar_pin"))
        textos_aviso = " ".join(m.value for m in at.warning)
        self.assertIn("invalida", textos_aviso)
        self.assertIn("deixa de conseguir entrar com o PIN antigo", textos_aviso)

    def test_gerar_pin_grava_hash_e_marca_provisorio(self):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_pin), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_pin), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.button(key="btn_gerar_pin").click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        conteudo = writes["usuarios.csv"].decode("utf-8-sig")
        self.assertIn("$2b$", conteudo)
        self.assertIn("PIN_Provisorio", conteudo)
        linha_ana = [l for l in conteudo.splitlines() if l.startswith("Ana Teste")][0]
        self.assertIn("Sim", linha_ana)
        # O PIN gerado (texto simples) fica só no estado transitório da
        # sessão, para ser mostrado uma vez — nunca no ficheiro.
        pin_mostrado = at.session_state["rh_pin_gerado_para"]["pin"]
        self.assertEqual(len(pin_mostrado), 4)
        self.assertTrue(pin_mostrado.isdigit())
        self.assertNotIn(pin_mostrado, conteudo)

    def test_pin_gerado_aparece_uma_vez_e_desaparece_ao_reconhecer(self):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_pin), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_pin), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", return_value=True):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.button(key="btn_gerar_pin").click().run()

            pin_gerado = at.session_state["rh_pin_gerado_para"]["pin"]
            textos_sucesso = " ".join(m.value for m in at.success)
            self.assertIn(pin_gerado, textos_sucesso)

            at.button(key="btn_ack_pin_gerado").click().run()
            self.assertNotIn("rh_pin_gerado_para", at.session_state)
            textos_sucesso_depois = " ".join(m.value for m in at.success)
            self.assertNotIn(pin_gerado, textos_sucesso_depois)

    def test_acao_de_auditoria_distingue_gerar_de_redefinir(self):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_pin), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_pin), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", return_value=True), \
             patch("mod_admin_rh.log_audit") as mock_log:
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.button(key="btn_gerar_pin").click().run()
        self.assertEqual(mock_log.call_args.kwargs.get("acao"), "GERAR_PIN_INICIAL")

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_pin_ja_definido), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_pin_ja_definido), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", return_value=True), \
             patch("mod_admin_rh.log_audit") as mock_log2:
            at2 = AppTest.from_function(_script, default_timeout=30)
            at2.run()
            at2.button(key="btn_gerar_pin").click().run()
        self.assertEqual(mock_log2.call_args.kwargs.get("acao"), "REDEFINIR_PIN")

    def test_sem_conta_bloqueada_nao_mostra_botao_desbloquear(self):
        at = self._run_com(_fake_gcs_read_pin)
        with self.assertRaises(Exception):
            at.button(key="btn_desbloquear_conta")

    def test_conta_bloqueada_mostra_aviso_e_botao(self):
        at = self._run_com(_fake_gcs_read_pin_bloqueada)
        textos = " ".join(m.value for m in at.warning)
        self.assertIn("bloqueada", textos.lower())
        self.assertTrue(at.button(key="btn_desbloquear_conta"))

    def test_desbloquear_limpa_bloqueio_e_tentativas(self):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_pin_bloqueada), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_pin_bloqueada), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write), \
             patch("mod_admin_rh.limpar_tentativas_login") as mock_limpar:
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.button(key="btn_desbloquear_conta").click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        mock_limpar.assert_called_once_with("12345")
        conteudo = writes["usuarios.csv"].decode("utf-8-sig")
        linha_ana = [l for l in conteudo.splitlines() if l.startswith("Ana Teste")][0]
        self.assertNotIn("Sim", linha_ana)


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


# ── Fixture: geração de credenciais em massa (Tab 7) ─────────────────────
# Quatro contas para cobrir os casos de elegibilidade: Ana (Técnico, sem
# PIN, entra no grupo PIN), Bruno (Admin, já tem password, entra no grupo
# Password mesmo assim — o âmbito escolhido foi "forçar renovação de
# tudo"), Carla (Cliente, excluída por Tipo), Duarte (Técnico mas sem
# Numero_Colaborador, excluído por falta de número).
_USUARIOS_MASSA_CSV = (
    "Nome,Tipo,Cargo,Email,Telefone,NIF,NISS,CC,CC_Validade,DataNasc,"
    "Morada,Localidade,Concelho,Codigo_Postal,Banco_IBAN,Nacionalidade,"
    "Estado_Civil,PrecoHora,Local_Obra,Cliente_Obra,"
    "ID,Numero_Colaborador,PIN,Password,Password_Provisoria,PIN_Provisorio,"
    "Bloqueado,Bloqueado_Em\n"
    "Ana Teste,Técnico,Instrumentista,ana@usuarios.pt,911111111,123456789,"
    "11122233344,12345678,01/01/2030,15/05/1990,"
    "Rua A 100,Lisboa,Lisboa,1000-001,PT50000000000000000000000,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X,"
    "A1B2C3D4,11111,,,,,,\n"
    "Bruno Admin,Admin,Administrador,bruno@usuarios.pt,911111112,123456780,"
    "11122233345,12345679,01/01/2030,15/05/1985,"
    "Rua B 100,Lisboa,Lisboa,1000-001,PT50000000000000000000001,Portuguesa,"
    f"Casado(a),,,,"
    f"B1B2C3D4,22222,,{core.hp('passwordAntiga1')},,,,\n"
    "Carla Cliente,Cliente,Gestor de Projeto,carla@cliente.pt,911111113,"
    "123456781,11122233346,12345680,01/01/2030,15/05/1980,"
    "Rua C 100,Lisboa,Lisboa,1000-001,PT50000000000000000000002,Portuguesa,"
    "Solteiro(a),,,,"
    "C1B2C3D4,33333,,,,,,\n"
    "Duarte SemNumero,Técnico,Instrumentista,duarte@usuarios.pt,911111114,"
    "123456782,11122233347,12345681,01/01/2030,15/05/1992,"
    "Rua D 100,Lisboa,Lisboa,1000-001,PT50000000000000000000003,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X,"
    "D1B2C3D4,,,,,,,\n"
).encode("utf-8-sig")


def _fake_gcs_read_massa(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_MASSA_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    return None


class TestCredenciaisEmMassa(unittest.TestCase):
    """Tab 7 — "Credenciais Iniciais (em massa)". Não gera nada até ao
    segundo clique explícito (checkbox de confirmação + botão)."""

    def _run(self):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
        return at

    def test_lista_so_as_duas_elegiveis(self):
        # Ana (PIN) e Bruno (Password) entram; Carla (Cliente) e Duarte
        # (sem número) ficam de fora — mas nada é gravado nesta chamada.
        at = self._run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn("2 contas elegíveis", textos)
        self.assertIn("1 passwords", textos)
        self.assertIn("1 PINs", textos)

    def test_botao_gerar_desativado_sem_confirmar(self):
        at = self._run()
        botao = at.button(key="btn_gerar_lote")
        self.assertTrue(botao.disabled)

    def test_gerar_grava_hash_marca_provisorio_e_nao_expoe_texto_simples(self):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.checkbox(key="rh_lote_confirmar").set_value(True).run()
            at.button(key="btn_gerar_lote").click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        conteudo = writes["usuarios.csv"].decode("utf-8-sig")
        self.assertIn("$2b$", conteudo)

        linha_ana = [l for l in conteudo.splitlines() if l.startswith("Ana Teste")][0]
        self.assertIn("Sim", linha_ana.split(",")[
            conteudo.splitlines()[0].split(",").index("PIN_Provisorio")])

        resultado = at.session_state["rh_lote_gerado"]
        self.assertEqual(len(resultado), 2)
        valores = {r["Nome"]: r["Valor"] for r in resultado}
        self.assertEqual(len(valores["Ana Teste"]), 4)
        self.assertTrue(valores["Ana Teste"].isdigit())
        self.assertGreaterEqual(len(valores["Bruno Admin"]), 8)
        # Os valores em claro nunca vão parar ao ficheiro gravado.
        self.assertNotIn(valores["Ana Teste"], conteudo)
        self.assertNotIn(valores["Bruno Admin"], conteudo)

    def test_carla_cliente_e_duarte_sem_numero_nunca_sao_tocados(self):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.checkbox(key="rh_lote_confirmar").set_value(True).run()
            at.button(key="btn_gerar_lote").click().run()

        resultado = at.session_state["rh_lote_gerado"]
        nomes_gerados = {r["Nome"] for r in resultado}
        self.assertNotIn("Carla Cliente", nomes_gerados)
        self.assertNotIn("Duarte SemNumero", nomes_gerados)
        conteudo = writes["usuarios.csv"].decode("utf-8-sig")
        linha_carla = [l for l in conteudo.splitlines() if l.startswith("Carla Cliente")][0]
        cabecalho = conteudo.splitlines()[0].split(",")
        self.assertEqual(linha_carla.split(",")[cabecalho.index("PIN")], "")
        self.assertEqual(linha_carla.split(",")[cabecalho.index("Password")], "")

    def test_lista_gerada_aparece_uma_vez_e_desaparece_ao_reconhecer(self):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", return_value=True):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.checkbox(key="rh_lote_confirmar").set_value(True).run()
            at.button(key="btn_gerar_lote").click().run()

            self.assertIn("rh_lote_gerado", at.session_state)
            at.button(key="btn_ack_lote").click().run()
            self.assertNotIn("rh_lote_gerado", at.session_state)

    def test_auditoria_regista_numeros_nunca_o_valor(self):
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_massa), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", return_value=True), \
             patch("mod_admin_rh.log_audit") as mock_log:
            core._cached_load_db.clear()
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.checkbox(key="rh_lote_confirmar").set_value(True).run()
            at.button(key="btn_gerar_lote").click().run()

        self.assertEqual(mock_log.call_args.kwargs.get("acao"), "GERAR_CREDENCIAIS_MASSA")
        detalhes = mock_log.call_args.kwargs.get("detalhes")
        self.assertIn("11111", detalhes)
        self.assertIn("22222", detalhes)
        resultado = at.session_state["rh_lote_gerado"]
        for r in resultado:
            self.assertNotIn(r["Valor"], detalhes)


# ── Fixture: Documentos Obrigatórios / associação a funções (Tab 8) ──────
# Uma conta com Funcao="Eletricista" (para popular o catálogo de funções
# a partir de usuarios.csv, tal como em produção) e dois documentos:
# um universal (Funcoes=[]) e um específico de Eletricista.
_USUARIOS_FUNCAO_CSV = (
    "Nome,Tipo,Cargo,Email,Telefone,NIF,NISS,CC,CC_Validade,DataNasc,"
    "Morada,Localidade,Concelho,Codigo_Postal,Banco_IBAN,Nacionalidade,"
    "Estado_Civil,PrecoHora,Local_Obra,Cliente_Obra,Funcao\n"
    "Ana Teste,Técnico,Instrumentista,ana@usuarios.pt,911111111,123456789,"
    "11122233344,12345678,01/01/2030,15/05/1990,"
    "Rua A 100,Lisboa,Lisboa,1000-001,PT50000000000000000000000,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X,Eletricista\n"
).encode("utf-8-sig")

_PDFS_DOCS_CSV = (
    "ID,Nome,Descricao,Data_Upload,Upload_Por,Ficheiro_b64,Funcoes\n"
    'DOC1,Manual de Acolhimento,,01/01/2026 10:00,Admin,YWJj,[]\n'
    'DOC2,Ficha de Risco Eletricista,,01/01/2026 10:00,Admin,YWJj,'
    '"[""Eletricista""]"\n'
).encode("utf-8-sig")


def _fake_gcs_read_docs(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_FUNCAO_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    if fn == "pdfs_obrigatorios.csv":
        return io.BytesIO(_PDFS_DOCS_CSV)
    return None


class TestDocumentosObrigatoriosPorFuncao(unittest.TestCase):
    """Tab 8 — "Documentos Obrigatórios". Lista existente, edição da
    associação a funções, criação de novo documento, remoção com
    confirmação explícita."""

    def _run(self):
        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_docs), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_docs), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
        return at

    def test_lista_mostra_toda_a_gente_e_funcao_especifica(self):
        at = self._run()
        self.assertFalse(at.exception, msg=str(at.exception))
        titulos = [e.label for e in at.expander]
        self.assertTrue(any("Manual de Acolhimento" in t and "Toda a gente" in t
                             for t in titulos))
        self.assertTrue(any("Ficha de Risco Eletricista" in t and "Eletricista" in t
                             for t in titulos))

    def test_catalogo_de_funcoes_inclui_valores_em_uso_em_usuarios(self):
        at = self._run()
        multiselect = at.multiselect(key="doc_funcoes_DOC1")
        self.assertIn("Eletricista", multiselect.options)

    def test_guardar_novas_funcoes_grava_no_ficheiro(self):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_docs), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_docs), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            # DOC1 (Manual de Acolhimento) passa a ser só para Eletricista.
            at.multiselect(key="doc_funcoes_DOC1").set_value(["Eletricista"]).run()
            at.button(key="doc_guardar_DOC1").click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        conteudo = writes["pdfs_obrigatorios.csv"].decode("utf-8-sig")
        linha_doc1 = [l for l in conteudo.splitlines() if l.startswith("DOC1")][0]
        self.assertIn("Eletricista", linha_doc1)

    def test_remover_fica_desativado_sem_confirmar(self):
        at = self._run()
        botao = at.button(key="doc_remover_DOC1")
        self.assertTrue(botao.disabled)

    def test_remover_com_confirmacao_apaga_a_linha(self):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_docs), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_docs), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.checkbox(key="doc_confirmar_remover_DOC1").set_value(True).run()
            at.button(key="doc_remover_DOC1").click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        conteudo = writes["pdfs_obrigatorios.csv"].decode("utf-8-sig")
        self.assertNotIn("DOC1", conteudo)
        self.assertIn("DOC2", conteudo)

    def test_criar_documento_grava_com_funcoes_e_ficheiro(self):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        core._cached_load_db.clear()
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_docs), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_docs), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key="novo_doc_nome").set_value("Regras de Segurança").run()
            at.multiselect(key="novo_doc_funcoes").set_value(["Eletricista"]).run()
            at.file_uploader(key="novo_doc_ficheiro").set_value(
                ("regras.pdf", b"conteudo de teste", "application/pdf")).run()
            at.button(
                key="FormSubmitter:form_novo_doc_obrigatorio-Adicionar documento"
            ).click().run()

        self.assertFalse(at.exception, msg=str(at.exception))
        conteudo = writes["pdfs_obrigatorios.csv"].decode("utf-8-sig")
        self.assertIn("Regras de Segurança", conteudo)
        linha_nova = [l for l in conteudo.splitlines()
                      if "Regras de Segurança" in l][0]
        self.assertIn("Eletricista", linha_nova)
        # O conteúdo do ficheiro fica em base64, nunca em claro.
        import base64 as _b64
        self.assertIn(_b64.b64encode(b"conteudo de teste").decode(), conteudo)

    def test_auditoria_das_tres_acoes(self):
        for acao_esperada, interagir in [
            ("CRIAR_DOCUMENTO_OBRIGATORIO", lambda at: (
                at.text_input(key="novo_doc_nome").set_value("Doc X").run(),
                at.file_uploader(key="novo_doc_ficheiro").set_value(
                    ("x.pdf", b"x", "application/pdf")).run(),
                at.button(key="FormSubmitter:form_novo_doc_obrigatorio-"
                              "Adicionar documento").click().run(),
            )),
            ("EDITAR_FUNCOES_DOCUMENTO", lambda at: (
                at.multiselect(key="doc_funcoes_DOC1").set_value(["Eletricista"]).run(),
                at.button(key="doc_guardar_DOC1").click().run(),
            )),
            ("REMOVER_DOCUMENTO_OBRIGATORIO", lambda at: (
                at.checkbox(key="doc_confirmar_remover_DOC1").set_value(True).run(),
                at.button(key="doc_remover_DOC1").click().run(),
            )),
        ]:
            core._cached_load_db.clear()
            with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_docs), \
                 patch("core._gcs_read", side_effect=_fake_gcs_read_docs), \
                 patch("core._gcs_client", return_value=None), \
                 patch("core._gcs_write", return_value=True), \
                 patch("mod_admin_rh.log_audit") as mock_log:
                at = AppTest.from_function(_script, default_timeout=30)
                at.run()
                interagir(at)
            self.assertEqual(mock_log.call_args.kwargs.get("acao"), acao_esperada,
                              msg=f"falhou para {acao_esperada}")


# ── Fixture: reposição da decisão de Preço/Hora ao mudar o valor ────────
# Ana Teste com PrecoHoraStatus="Recusado" já definido — para confirmar
# que mudar o valor do Preço/Hora repõe a decisão (DESENHO_ONBOARDING.md,
# secção 3), e que NÃO mudar o valor a mantém intacta.
_USUARIOS_PRECO_RECUSADO_CSV = (
    "Nome,Tipo,Cargo,Email,Telefone,NIF,NISS,CC,CC_Validade,DataNasc,"
    "Morada,Localidade,Concelho,Codigo_Postal,Banco_IBAN,Nacionalidade,"
    "Estado_Civil,PrecoHora,PrecoHoraStatus,PrecoHoraData,Local_Obra,"
    "Cliente_Obra\n"
    "Ana Teste,Técnico,Instrumentista,ana@usuarios.pt,911111111,123456789,"
    "11122233344,12345678,01/01/2030,15/05/1990,"
    "Rua A 100,Lisboa,Lisboa,1000-001,PT50000000000000000000000,Portuguesa,"
    "Solteiro(a),15,Recusado,01/09/2026 10:00,Refinaria X,Cliente X\n"
).encode("utf-8-sig")


def _fake_gcs_read_preco(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_PRECO_RECUSADO_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    return None


class TestRepoDecisaoPrecoHora(unittest.TestCase):
    """Mudar o valor de Preço/Hora, na Ficha do Colaborador, repõe a
    decisão da pessoa (PrecoHoraStatus/PrecoHoraData) — sobretudo depois
    de uma recusa, para o RH não precisar de nenhum passo extra além de
    mudar o número. Não mudar o valor mantém a decisão intacta."""

    def _submeter(self, novo_preco):
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_preco), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_preco), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", side_effect=_gcs_write):
            core._cached_load_db.clear()
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.text_input(key=f"gi_preco_{SLUG}").set_value(novo_preco).run()
            at.button(
                key=f"FormSubmitter:gi_form_prof_{SLUG}-Guardar Profissional"
            ).click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
        return writes

    def _linha_ana(self, writes):
        conteudo = writes["usuarios.csv"].decode("utf-8-sig")
        cabecalho = conteudo.splitlines()[0].split(",")
        linha = [l for l in conteudo.splitlines() if l.startswith("Ana Teste")][0]
        return dict(zip(cabecalho, linha.split(",")))

    def test_mudar_o_valor_repoe_status_e_data(self):
        writes = self._submeter("22.5")
        campos = self._linha_ana(writes)
        self.assertEqual(campos["PrecoHora"], "22.5")
        self.assertEqual(campos["PrecoHoraStatus"], "")
        self.assertEqual(campos["PrecoHoraData"], "")

    def test_manter_o_mesmo_valor_nao_toca_no_status(self):
        writes = self._submeter("15")
        campos = self._linha_ana(writes)
        self.assertEqual(campos["PrecoHoraStatus"], "Recusado")
        self.assertEqual(campos["PrecoHoraData"], "01/09/2026 10:00")


# ── Fixture: lista "Contrato por gerar/enviar" (Tab Contratos) ──────────
# Quatro contas: Bruno (Técnico, completou o onboarding, sem contrato
# enviado — deve aparecer), Carla (Técnico, completou, mas já tem
# contrato enviado — não deve aparecer), Duarte (Técnico, onboarding
# incompleto — não deve aparecer), Elsa (Admin, com todos os campos de
# onboarding "completos" por acidente — não deve aparecer, é
# administrativa).
_USUARIOS_CONTRATOS_CSV = (
    "Nome,Tipo,Cargo,Email,Telefone,NIF,NISS,CC,CC_Validade,DataNasc,"
    "Morada,Localidade,Concelho,Codigo_Postal,Banco_IBAN,Nacionalidade,"
    "Estado_Civil,PrecoHora,Local_Obra,Cliente_Obra,"
    "PDFs_Validados,PrecoHoraStatus,Perfil_Completo,IBAN_Comprovativo_b64,"
    "Contrato_Gerado,Contrato_Enviado\n"
    "Bruno Tecnico,Técnico,Instrumentista,b@x.pt,911111111,123456789,"
    "11122233344,12345678,01/01/2030,15/05/1990,"
    "Rua A 100,Lisboa,Lisboa,1000-001,PT50000000000000000000000,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X,"
    "Sim,Aceite,Sim,abc,,\n"
    "Carla Tecnico,Técnico,Instrumentista,c@x.pt,911111112,123456780,"
    "11122233345,12345679,01/01/2030,15/05/1991,"
    "Rua B 100,Lisboa,Lisboa,1000-001,PT50000000000000000000001,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X,"
    "Sim,Aceite,Sim,abc,Sim,Sim\n"
    "Duarte Tecnico,Técnico,Instrumentista,d@x.pt,911111113,123456781,"
    "11122233346,12345680,01/01/2030,15/05/1992,"
    "Rua C 100,Lisboa,Lisboa,1000-001,PT50000000000000000000002,Portuguesa,"
    "Solteiro(a),15,Refinaria X,Cliente X,"
    "Sim,Aceite,,abc,,\n"
    "Elsa Admin,Admin,Administradora,e@x.pt,911111114,123456782,"
    "11122233347,12345681,01/01/2030,15/05/1980,"
    "Rua D 100,Lisboa,Lisboa,1000-001,PT50000000000000000000003,Portuguesa,"
    "Solteiro(a),,,Sim,,,\n"
).encode("utf-8-sig")


def _fake_gcs_read_contratos(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_CONTRATOS_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    return None


class TestListaContratoPorGerarEnviar(unittest.TestCase):
    """Tab "Contratos" — lista de quem completou o onboarding e ainda
    não tem contrato enviado (DESENHO_ONBOARDING.md, secção 4, ponto 2).
    Testes lêem só o texto do separador Contratos (após o marcador de
    Formações, onde os outros separadores terminam)."""

    @classmethod
    def setUpClass(cls):
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_contratos), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_contratos), \
             patch("core._gcs_client", return_value=None):
            cls.at = _run()
        # A aba "Colaboradores" também lista nomes com um resumo de
        # estado de contrato — isolar só a secção nova ("Contrato por
        # gerar/enviar" até às 4 caixas de passos do colaborador
        # seleccionado, que já existiam antes desta alteração).
        todo_o_texto = " ".join(m.value for m in cls.at.markdown)
        inicio = todo_o_texto.index("Contrato por gerar/enviar")
        fim    = todo_o_texto.index("border:2px solid #5A6478", inicio)
        cls.textos = todo_o_texto[inicio:fim]

    def test_sem_erro(self):
        self.assertFalse(self.at.exception, msg=str(self.at.exception))

    def test_bruno_aparece_carla_e_duarte_nao(self):
        self.assertIn("Bruno Tecnico", self.textos)
        self.assertNotIn("Carla Tecnico", self.textos)
        self.assertNotIn("Duarte Tecnico", self.textos)

    def test_admin_nunca_aparece_mesmo_com_campos_completos(self):
        self.assertNotIn("Elsa Admin", self.textos)

    def test_mostra_contagem_de_um_pendente(self):
        avisos = " ".join(w.value for w in self.at.warning)
        self.assertIn("1 colaborador", avisos)

    def test_botao_ver_existe_para_o_pendente(self):
        self.assertTrue(any(b.key == "ct_ir_para_Bruno Tecnico" for b in self.at.button))

    def test_ver_seleciona_o_colaborador_no_separador(self):
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read_contratos), \
             patch("core._gcs_read", side_effect=_fake_gcs_read_contratos), \
             patch("core._gcs_client", return_value=None):
            core._cached_load_db.clear()
            at = AppTest.from_function(_script, default_timeout=30)
            at.run()
            at.button(key="ct_ir_para_Bruno Tecnico").click().run()
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertEqual(at.session_state["ct_colab_sel"], "Bruno Tecnico")


if __name__ == "__main__":
    unittest.main(verbosity=2)

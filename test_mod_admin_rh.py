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


def _fake_gcs_read(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_CSV)
    if fn == "colaboradores_rh.csv":
        return io.BytesIO(_RH_CSV)
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
        self.assertIn("👥 Colaboradores", labels)
        self.assertIn("📋 Ficha do Colaborador", labels)
        self.assertNotIn("📋 Gestão Individual", labels)
        self.assertNotIn("📋 Dados Legais", labels)
        # Conteúdo de ambas as secções antigas continua presente, agora
        # dentro da mesma aba.
        markdown_textos = " ".join(m.value for m in self.at.markdown)
        self.assertIn("Dados Legais e Fiscais", markdown_textos)

    def test_nome_bloqueado_em_gestao_individual(self):
        campo_nome = self.at.text_input(key=f"gi_nome_{SLUG}")
        self.assertTrue(campo_nome.disabled)
        self.assertEqual(campo_nome.value, NOME)

    def test_gestao_individual_mostra_dados_de_usuarios_csv(self):
        self.assertEqual(self.at.text_input(key=f"gi_email_{SLUG}").value,
                          "ana@usuarios.pt")
        self.assertEqual(self.at.text_input(key=f"gi_morada_{SLUG}").value,
                          "Rua A 100")
        self.assertEqual(self.at.text_input(key=f"gi_nif_{SLUG}").value,
                          "123456789")
        self.assertEqual(self.at.text_input(key=f"gi_iban_{SLUG}").value,
                          "PT50000000000000000000000")
        self.assertEqual(self.at.text_input(key=f"gi_preco_{SLUG}").value, "15")
        self.assertEqual(self.at.text_input(key=f"gi_local_{SLUG}").value,
                          "Refinaria X")

    def test_dados_legais_mostra_dados_proprios_quando_preenchidos(self):
        # Estado_Civil e NISS têm valor próprio em colaboradores_rh.csv,
        # diferente do que está em usuarios.csv — não deve ser substituído.
        self.assertEqual(self.at.selectbox(key=f"dl_estcivil_{SLUG}").value,
                          "Casado(a)")
        self.assertEqual(self.at.text_input(key=f"dl_niss_{SLUG}").value,
                          "99999999999")
        self.assertEqual(self.at.text_input(key=f"dl_salb_{SLUG}").value, "1200")

    def test_dados_legais_usa_fallback_de_usuarios_quando_vazio(self):
        # NIF/CC/Email/Morada estão vazios em colaboradores_rh.csv — o
        # formulário pré-preenche (só apresentação) com o valor de
        # usuarios.csv.
        self.assertEqual(self.at.text_input(key=f"dl_nif_{SLUG}").value,
                          "123456789")
        self.assertEqual(self.at.text_input(key=f"dl_cc_{SLUG}").value,
                          "12345678")
        self.assertEqual(self.at.text_input(key=f"dl_datanasc_{SLUG}").value,
                          "15/05/1990")

    def test_seletor_colaborador_e_partilhado_entre_abas(self):
        self.assertEqual(self.at.session_state['rh_colaborador_sel'], NOME)
        self.assertEqual(self.at.selectbox(key="rh_gestao_sel").value, NOME)
        self.assertEqual(self.at.selectbox(key="dl_colab_sel").value, NOME)


class TestGravarComportamentoAtual(unittest.TestCase):
    """Cada aba grava hoje apenas no seu próprio ficheiro — sem dual-write."""

    def _submit(self, form_key, label):
        with patch("mod_admin_rh._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None), \
             patch("core._gcs_write", return_value=True) as mock_write:
            at = _run()
            at.button(key=f"FormSubmitter:{form_key}-{label}").click().run()
            self.assertFalse(at.exception, msg=str(at.exception))
            return mock_write

    def test_guardar_identificacao_em_gestao_individual_so_grava_usuarios(self):
        mock_write = self._submit(f"gi_form_ident_{SLUG}",
                                   "💾 Guardar Identificação")
        ficheiros_gravados = [c.args[0] for c in mock_write.call_args_list]
        self.assertIn("usuarios.csv", ficheiros_gravados)
        self.assertNotIn("colaboradores_rh.csv", ficheiros_gravados)

    def test_guardar_identificacao_em_dados_legais_so_grava_colaboradores_rh(self):
        mock_write = self._submit(f"dl_form_ident_{SLUG}",
                                   "💾 Guardar Identificação")
        ficheiros_gravados = [c.args[0] for c in mock_write.call_args_list]
        self.assertIn("colaboradores_rh.csv", ficheiros_gravados)
        self.assertNotIn("usuarios.csv", ficheiros_gravados)


class TestSaveDual(unittest.TestCase):
    """`_save_dual` — helper novo que grava em usuarios.csv (fonte) e espelha
    os mesmos campos em colaboradores_rh.csv. Usado pela ficha unificada."""

    def _call(self, updates, rh_csv=_RH_CSV):
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
            ok = m._save_dual(NOME, updates)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)

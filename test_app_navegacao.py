"""
Testes de NAVEGAÇÃO / ENCAMINHAMENTO do app.py (ponta-a-ponta com AppTest).

Protegem o comportamento ATUAL antes de se acrescentar o painel de obra ao
menu. Os dados são substituídos por vazio (core._gcs_read devolve None), por
isso os testes são deterministas e NÃO tocam em produção/GCS.

Asserções pensadas como INVARIANTES (presença dos ecrãs atuais), para que
acrescentar uma entrada nova ao menu não as quebre.

Correr:  python -m unittest test_app_navegacao -v
"""
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from core import ICONS


def _run(tipo, menu, user="Diogo Henriques", cargo="Administrador"):
    with patch("core._gcs_read", return_value=None):
        at = AppTest.from_file("app.py", default_timeout=30)
        at.session_state["user"] = user
        at.session_state["tipo"] = tipo
        at.session_state["cargo"] = cargo
        at.session_state["menu_selected"] = menu
        at.session_state["_fv"] = {}
        # Trinco de menu da própria app: impede que a barra de navegação
        # (componente externo, que em modo de teste não devolve a escolha)
        # reescreva o menu e faça a página saltar de ecrã.
        at.session_state["_menu_locked"] = True
        at.run()
        return at


def _texto(at):
    """Junta o texto visível de vários tipos de elemento (títulos, markdown,
    legendas e rótulos de botões) para procurar marcadores de ecrã."""
    partes = []
    for attr in ("title", "header", "subheader", "markdown", "caption", "text", "info"):
        for el in getattr(at, attr, []):
            v = getattr(el, "value", "")
            if v:
                partes.append(str(v))
    for b in getattr(at, "button", []):
        v = getattr(b, "label", "")
        if v:
            partes.append(str(v))
    return " ".join(partes)


class TestEncaminhamentoAdmin(unittest.TestCase):
    def test_dashboard_geral_abre(self):
        at = _run("Admin", f"{ICONS['dashboard']} Dashboard")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Dashboard Geral", _texto(at))

    def test_instrumentacao_abre(self):
        at = _run("Admin", f"{ICONS['instrumentation']} Instrumentação")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Instrumentação Industrial", _texto(at))

    def test_perfil_abre_sem_erro(self):
        # Smoke: confirma só que o ecrã de Perfil abre sem erro (com dados
        # vazios no ambiente de teste, o formulário pode não desenhar todas as
        # secções, por isso não se exige texto específico).
        at = _run("Admin", f"{ICONS['profile']} Perfil")
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_admin_abre_sem_erro(self):
        at = _run("Admin", f"{ICONS['admin']} Admin")
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_dashboard_de_obra_abre(self):
        # Fase B do Dashboard de Obra (campos operacionais): renomeado
        # de "🏗️ Painel de Obra" para "📊 Dashboard de Obra" no menu
        # lateral, para não se confundir com o nome interno do projeto.
        at = _run("Admin", f"{ICONS['work']} Dashboard de Obra")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Sem obras para apresentar", _texto(at))
        self.assertEqual(ICONS['work'], "📊")


class TestLogotipoNaBarraLateral(unittest.TestCase):
    """Fase 2 da Identidade Visual: com a barra lateral e a área de
    trabalho claras, o logótipo passa a usar a variante já preparada
    para fundo claro ("transparente" — texto em cinza-escuro) em vez
    da variante "tema_escuro" (texto branco, invisível em fundo
    claro).

    O logótipo aparece só uma vez, via st.logo() (mecanismo nativo do
    Streamlit, cobre também o caso da barra colapsada) — o segundo
    logótipo, que estava embutido manualmente logo a seguir dentro do
    bloco da barra lateral, foi removido por ser redundante (os dois
    empilhados ocupavam quase metade da barra antes da navegação)."""

    def test_usa_variante_clara_um_so_sitio(self):
        with open("app.py", encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("logo_cps_tema_escuro.png", src)
        self.assertEqual(src.count("logo_cps_transparente.png"), 1)
        self.assertIn('st.logo("assets/logo_cps_transparente.png"', src)

    def test_logotipo_embutido_manualmente_foi_removido(self):
        with open("app.py", encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("_logo_sb_b64", src)


class TestEncaminhamentoCliente(unittest.TestCase):
    def test_portal_cliente_abre(self):
        at = _run("Cliente", f"{ICONS['dashboard']} Portal", user="Cliente Teste")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Portal do Cliente", _texto(at))


if __name__ == "__main__":
    unittest.main(verbosity=2)

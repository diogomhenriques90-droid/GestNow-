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
        at = _run("Admin", f"Dashboard")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Dashboard Geral", _texto(at))

    def test_instrumentacao_abre(self):
        at = _run("Admin", f"Instrumentação")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Instrumentação Industrial", _texto(at))

    def test_perfil_abre_sem_erro(self):
        # Smoke: confirma só que o ecrã de Perfil abre sem erro (com dados
        # vazios no ambiente de teste, o formulário pode não desenhar todas as
        # secções, por isso não se exige texto específico).
        at = _run("Admin", f"Perfil")
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_admin_abre_sem_erro(self):
        at = _run("Admin", f"Admin")
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_dashboard_de_obra_abre(self):
        # Fase B do Dashboard de Obra (campos operacionais): renomeado
        # de "Painel de Obra" para "Dashboard de Obra" no menu lateral,
        # para não se confundir com o nome interno do projeto.
        at = _run("Admin", f"Dashboard de Obra")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Sem obras para apresentar", _texto(at))


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
        at = _run("Cliente", f"Portal", user="Cliente Teste")
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Portal do Cliente", _texto(at))


class TestBarraInferiorNaoTrancaSidebar(unittest.TestCase):
    """Lote 4 (barra inferior mobile, agora um st.segmented_control nativo
    em vez do streamlit_option_menu): um clique na barra inferior tem de
    sobreviver ao rerun que o próprio clique despoleta, sem o radio da
    sidebar (que fica com o seu próprio valor antigo, porque não foi ele
    que mudou) reverter menu_selected para o ecrã de onde se veio.

    A proteção usada (`_menu_locked=True` antes do st.rerun()) é a mesma
    já usada em mod_chefe.py/mod_inicio.py — cobre este rerun imediato,
    não uma cadeia de reruns não relacionados depois disso (limitação
    pré-existente da app, não introduzida aqui e fora do âmbito desta
    correção).

    Isto só passou a ser possível testar com um widget nativo — o
    componente externo antigo não é "clicável" em AppTest (daí o
    `_menu_locked=True` forçado em todos os outros testes desta
    classe)."""

    def test_clique_na_barra_sobrevive_ao_proprio_rerun(self):
        with patch("core._gcs_read", return_value=None):
            at = AppTest.from_file("app.py", default_timeout=30)
            at.session_state["user"] = "Diogo Henriques"
            at.session_state["tipo"] = "Admin"
            at.session_state["cargo"] = "Administrador"
            at.session_state["menu_selected"] = "Dashboard"
            at.session_state["_fv"] = {}
            at.run()
            self.assertFalse(at.exception, msg=str(at.exception))

            # Clique real na barra inferior: "Dashboard" -> "Perfil".
            at.segmented_control[0].set_value("Perfil").run()
            self.assertFalse(at.exception, msg=str(at.exception))
            self.assertEqual(at.session_state["menu_selected"], "Perfil")
            self.assertIn("Perfil", _texto(at))


class TestBarraInferiorSoMobile(unittest.TestCase):
    """A barra inferior é só para ecrãs estreitos — no desktop já existe a
    barra lateral, e mostrar as duas ao mesmo tempo não faz sentido.
    Confirmado por inspeção de git diff que esta limitação nunca existiu
    (nem no streamlit_option_menu antigo, nem em mais lado nenhum do
    código — sem @media anterior), por isso é uma correção nova, não uma
    regressão do Lote 4."""

    def test_media_query_esconde_barra_e_espacador_no_desktop(self):
        with open("app.py", encoding="utf-8") as f:
            src = f.read()
        self.assertIn("@media (min-width: 769px)", src)
        bloco = src[src.index("@media (min-width: 769px)"):]
        bloco = bloco[:bloco.index("</style>")]
        self.assertIn(".st-key-bottom_nav_bar", bloco)
        self.assertIn("display: none", bloco)
        self.assertIn(".bottom-nav-spacer", bloco)


if __name__ == "__main__":
    unittest.main(verbosity=2)

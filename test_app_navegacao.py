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

import core


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


class TestContratoPendenteSemIconesTemaClaro(unittest.TestCase):
    """Bloqueio "contrato pendente de assinatura" (app.py, MAIN routing,
    logo a seguir ao ponto onde o onboarding de 4 passos costumava
    correr) — migrado do visual escuro antigo (cores fixas) para o THEME
    central, e sem ícones, ao mesmo tempo que os outros ecrãs da app.

    Esta classe cobria antes também o ecrã de onboarding de 4 passos
    (_render_validacao_obrigatoria), removido de app.py por completo —
    esse percurso vive agora só no cps-ponto (DESENHO_ONBOARDING.md,
    passo 6). Os testes desses 4 passos saíram daqui com ele; fica só o
    teste do bloqueio de contrato, que é um bloco à parte e continua a
    existir em app.py.

    A sessão é marcada como já autenticada (Técnico) ANTES do `import app`
    dentro do script — assim o próprio fluxo normal de app.py chama o
    bloqueio sozinho, em vez de nós chamarmos explicitamente depois de
    app.py já ter corrido o ecrã de login como efeito secundário do
    import (o que gerava um erro de "form aninhado" — dois st.form() na
    mesma execução de script)."""

    def _run_passo(self, users_df, pdfs_df=None, tipo='Técnico', cargo='Técnico'):
        import pandas as pd
        if pdfs_df is None:
            pdfs_df = pd.DataFrame(columns=[
                "ID","Nome","Descricao","Data_Upload","Upload_Por","Ficheiro_b64"
            ])

        orig_load_db = core.load_db

        def _load_db_lado(fn, cols, silent=False):
            if fn == "pdfs_obrigatorios.csv":
                return pdfs_df
            return orig_load_db(fn, cols, silent)

        def _script(tipo, cargo):
            import streamlit as st
            st.session_state['user']          = 'Técnico Teste'
            st.session_state['tipo']          = tipo
            st.session_state['cargo']         = cargo
            st.session_state['menu_selected'] = ''
            st.session_state['_fv']           = {}
            import app  # noqa: F401 — dispara o routing completo, que chama a função sozinho

        with patch("core._gcs_read", return_value=None), \
             patch("core._load_users_cached", return_value=users_df), \
             patch("core.load_db", side_effect=_load_db_lado):
            at = AppTest.from_function(_script, default_timeout=30, args=(tipo, cargo))
            at.run()
        return at

    def _base_user(self, **overrides):
        import pandas as pd
        linha = {
            "Nome": "Técnico Teste", "PDFs_Validados": "Sim", "PDFs_Vistos": "[]",
            "PrecoHoraStatus": "Aceite", "PrecoHora": "15.0",
            "Perfil_Completo": "Sim", "IBAN_Comprovativo_b64": "abc",
        }
        linha.update(overrides)
        return pd.DataFrame([linha])

    def _sem_emoji(self, at):
        import re
        padrao = re.compile(r'[\U0001F300-\U0001FAFF☀-➿←-⇿⬀-⯿️]')
        for m in list(at.markdown) + list(at.warning):
            self.assertIsNone(padrao.search(m.value), f"emoji encontrado: {m.value!r}")

    def test_contrato_pendente_sem_erro_sem_icones_tema_claro(self):
        """Aviso "contrato pendente de assinatura" (app.py, MAIN routing)
        — sem ícones, mesma migração de tema. Não bloqueante: tinha um
        st.stop() que impedia o resto da app de aparecer (o mesmo bug já
        corrigido em _verificar_contrato() no cps-ponto); removido."""
        at = self._run_passo(self._base_user(
            Contrato_Enviado="Sim", Contrato_Assinado="",
            Contrato_Validado_Admin="",
        ))
        self.assertFalse(at.exception, msg=str(at.exception))
        self._sem_emoji(at)
        self.assertTrue(any(
            "contrato pendente de assinatura" in w.value.lower()
            for w in at.warning
        ))
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#0F172A", textos)
        self.assertNotIn("#1E40AF", textos)
        # Prova de que já não bloqueia: o resto do ecrã do Técnico (que
        # antes nunca era alcançado, por causa do st.stop()) aparece.
        self.assertIn("Horas este mês", textos)

    def test_secretariado_nao_ve_aviso_de_contrato(self):
        """Secretariado e Armazém ficam de fora deste aviso, tal como no
        cps-ponto (_ONBOARDING_TIPOS_SO_DOCUMENTOS) — o contrato deles é
        em papel, fora da app (DESENHO_ONBOARDING.md, secção 1)."""
        at = self._run_passo(self._base_user(
            Contrato_Enviado="Sim", Contrato_Assinado="",
            Contrato_Validado_Admin="",
        ), tipo='Secretariado', cargo='Secretariado')
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertFalse(any(
            "contrato pendente de assinatura" in w.value.lower()
            for w in at.warning
        ))


class TestPasswordProvisoria(unittest.TestCase):
    """_verificar_password_provisoria (app.py) — gémeo do
    _verificar_pin_provisorio do cps-ponto. Corre logo a seguir ao login,
    para qualquer Tipo (incluindo Admin, ao contrário do onboarding que só
    se aplica a Técnicos/Chefes), antes de load_all() e de qualquer outro
    ecrã."""

    @classmethod
    def setUpClass(cls):
        # Importar 'app' uma única vez, através de um AppTest normal (NÃO
        # um "import app" cru fora de qualquer script run — isso deixa o
        # registo interno de formulários do Streamlit por fechar, e todos
        # os st.form() a seguir, no processo inteiro, rebentam com "Forms
        # cannot be nested"). Sessão já autenticada como Admin, para o
        # topo do app.py nunca cair no ecrã de login (evita form aberto
        # aí) — só depois disto é que os testes fazem
        # patch("app._load_users_cached", ...) com segurança.
        import sys
        if 'app' not in sys.modules:
            import pandas as pd

            def _warmup_script():
                import streamlit as st
                st.session_state['user']          = 'Aquecimento'
                st.session_state['tipo']          = 'Admin'
                st.session_state['cargo']         = 'Administrador'
                st.session_state['menu_selected'] = 'Dashboard'
                st.session_state['_fv']           = {}
                st.session_state['_menu_locked']  = True
                import app  # noqa: F401

            df = pd.DataFrame([{"Nome": "Aquecimento", "Password_Provisoria": ""}])
            with patch("core._gcs_read", return_value=None), \
                 patch("core._load_users_cached", return_value=df):
                at = AppTest.from_function(_warmup_script, default_timeout=30)
                at.run()

    def _run_gate(self, nome, user_row, interagir=None):
        """Chama _verificar_password_provisoria() diretamente — evita
        depender de o 'import app' completo voltar a correr o ficheiro
        inteiro em cada teste (só executa mesmo na primeira vez em todo
        o processo, porque fica em sys.modules — chamar a função
        apontada resolve isto sem esse efeito colateral).

        interagir(at), se dado, corre AINDA DENTRO do with patch(...) —
        um set_value/click().run() feito depois do with já ter fechado
        executa sem mocks e bate em dados reais de produção (ver memória
        'patches em interações multi-passo')."""
        writes = {}

        def _gcs_write(fn, content_bytes):
            writes[fn] = content_bytes
            return True

        def _script(nome):
            import streamlit as st
            st.session_state['user'] = nome
            # 'app' já foi importado em setUpClass — isto só vai buscar a
            # função ao módulo já pronto, sem voltar a correr o topo do
            # ficheiro (routing completa) como efeito colateral.
            from app import _verificar_password_provisoria
            _verificar_password_provisoria(nome)

        import pandas as pd
        df = pd.DataFrame([user_row])

        # app.py faz "from core import ..., _load_users_cached" — a cópia
        # do nome é feita UMA SÓ VEZ, na primeira importação de 'app' em
        # todo o processo de testes. Corrigir só "core._load_users_cached"
        # não chega a partir da segunda vez: app.py continua com a cópia
        # antiga. Ambos têm de ser corrigidos.
        with patch("core._gcs_read", return_value=None), \
             patch("core._load_users_cached", return_value=df), \
             patch("app._load_users_cached", return_value=df), \
             patch("core._gcs_write", side_effect=_gcs_write):
            at = AppTest.from_function(
                _script, default_timeout=30,
                args=(nome,),
            )
            at.run()
            if interagir is not None:
                interagir(at)
        return at, writes

    def test_bloqueia_quando_provisoria_mesmo_para_admin(self):
        at, _ = self._run_gate("Diogo Henriques", {
            "Nome": "Diogo Henriques", "Password_Provisoria": "Sim",
        })
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Password provisória", _texto(at))

    def test_nao_bloqueia_quando_flag_vazia(self):
        at, _ = self._run_gate("Diogo Henriques", {
            "Nome": "Diogo Henriques", "Password_Provisoria": "",
        })
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertNotIn("Password provisória", _texto(at))

    def test_submissao_valida_grava_hash_limpa_flag_e_nao_expoe_texto_simples(self):
        def _interagir(at):
            at.text_input(key="npp_nova_pwd").set_value("umaPasswordNova123")
            at.text_input(key="npp_conf_pwd").set_value("umaPasswordNova123")
            [b for b in at.button if b.label == "Definir Password"][0].click().run()

        at, writes = self._run_gate(
            "Diogo Henriques", {"Nome": "Diogo Henriques", "Password_Provisoria": "Sim"},
            interagir=_interagir,
        )
        self.assertFalse(at.exception, msg=str(at.exception))
        conteudo = writes["usuarios.csv"].decode("utf-8-sig")
        self.assertNotIn("umaPasswordNova123", conteudo)
        self.assertIn("$2b$", conteudo)
        linha = [l for l in conteudo.splitlines() if l.startswith("Diogo Henriques")][0]
        campos = linha.split(",")
        # Password_Provisoria é a última coluna do cabeçalho escrito
        self.assertNotIn("Sim", campos[-1])

    def test_confirmacao_errada_mantem_bloqueado(self):
        def _interagir(at):
            at.text_input(key="npp_nova_pwd").set_value("umaPasswordNova123")
            at.text_input(key="npp_conf_pwd").set_value("outraCoisaqualquer")
            [b for b in at.button if b.label == "Definir Password"][0].click().run()

        at, writes = self._run_gate(
            "Diogo Henriques", {"Nome": "Diogo Henriques", "Password_Provisoria": "Sim"},
            interagir=_interagir,
        )
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertTrue(any("não coincidem" in e.value for e in at.error))
        self.assertNotIn("usuarios.csv", writes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

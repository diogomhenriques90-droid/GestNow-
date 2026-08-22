"""
Testes de core.py — helpers de seleção de Obra (obra_select, get_obras_opts,
get_cliente_da_obra), introduzidos na Fase 1 do Painel de Obra (campos
operacionais): Local_Obra na Ficha do Colaborador passa a escolher-se de
entre obras reais, e o Cliente passa a derivar-se daí em vez de ser um
campo independente.

Não tocam em GCS real — `_gcs_read` é mockado com um CSV fixo em memória.

Correr:  python -m unittest test_core -v
"""
import io
import os
import tomllib
import unittest
from unittest.mock import patch

import core

_CONFIG_TOML_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "config.toml")

_OBRAS_LISTA_CSV = (
    "Obra,Cliente,Ativa\n"
    "Obra Ativa X,Cliente X,Ativa\n"
    "Obra Ativa Y,Cliente Y,Ativa\n"
    "Obra Inativa Z,Cliente Z,Inativa\n"
).encode("utf-8-sig")

_CLIENTES_FINANCEIRO_CSV = (
    "ID,Nome,Activo\n"
    "C1,Cliente X,Sim\n"
    "C2,Cliente Y,Sim\n"
).encode("utf-8-sig")

_CONTACTOS_CLIENTES_CSV = (
    "ID,Cliente_ID,Nome,Cargo,Email,Telefone\n"
    "CT1,C1,Pessoa Um,Gestor de Projeto,um@x.pt,911111111\n"
    "CT2,C1,Pessoa Dois,,dois@x.pt,922222222\n"
    "CT3,C2,Pessoa Outro Cliente,,outro@x.pt,933333333\n"
).encode("utf-8-sig")


def _fake_gcs_read(fn):
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    if fn == "contactos_clientes.csv":
        return io.BytesIO(_CONTACTOS_CLIENTES_CSV)
    return None


class TestGetObrasOpts(unittest.TestCase):
    def setUp(self):
        # load_db() usa @st.cache_data — sem isto, o resultado do primeiro
        # teste fica em cache e é devolvido aos seguintes independentemente
        # do que _gcs_read esteja mockado a devolver.
        core._cached_load_db.clear()

    def test_devolve_so_obras_ativas_por_omissao(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            opts = core.get_obras_opts()
        self.assertEqual(opts, ["Obra Ativa X", "Obra Ativa Y"])

    def test_inclui_inativas_quando_pedido(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            opts = core.get_obras_opts(incluir_inativas=True)
        self.assertEqual(
            opts, ["Obra Ativa X", "Obra Ativa Y", "Obra Inativa Z"])

    def test_sem_ficheiro_devolve_lista_vazia(self):
        with patch("core._gcs_read", return_value=None):
            opts = core.get_obras_opts()
        self.assertEqual(opts, [])


class TestGetClienteDaObra(unittest.TestCase):
    def setUp(self):
        core._cached_load_db.clear()

    def test_devolve_cliente_da_obra_existente(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            cliente = core.get_cliente_da_obra("Obra Ativa X")
        self.assertEqual(cliente, "Cliente X")

    def test_obra_inativa_tambem_resolve_cliente(self):
        # Uma obra fechada continua a ter um Cliente válido — só deixa de
        # aparecer nas opções de obra_select por omissão.
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            cliente = core.get_cliente_da_obra("Obra Inativa Z")
        self.assertEqual(cliente, "Cliente Z")

    def test_obra_inexistente_devolve_vazio(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            cliente = core.get_cliente_da_obra("Obra Que Não Existe")
        self.assertEqual(cliente, "")

    def test_obra_vazia_devolve_vazio_sem_ler_ficheiro(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read) as mock_read:
            cliente = core.get_cliente_da_obra("")
        self.assertEqual(cliente, "")
        mock_read.assert_not_called()


class TestGetContactosCliente(unittest.TestCase):
    """Fase 5 do Painel de Obra (campos operacionais): liga a ficha de
    Obra às Pessoas de Contacto do Cliente (contactos_clientes.csv),
    via clientes_financeiro.csv como ponte Nome -> ID -> Cliente_ID."""

    def setUp(self):
        core._cached_load_db.clear()

    def test_devolve_todos_os_contactos_do_cliente(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            contactos = core.get_contactos_cliente("Cliente X")
        nomes = sorted(c["Nome"] for c in contactos)
        self.assertEqual(nomes, ["Pessoa Dois", "Pessoa Um"])

    def test_nao_devolve_contactos_de_outro_cliente(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            contactos = core.get_contactos_cliente("Cliente X")
        nomes = [c["Nome"] for c in contactos]
        self.assertNotIn("Pessoa Outro Cliente", nomes)

    def test_cliente_sem_contactos_devolve_lista_vazia(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            contactos = core.get_contactos_cliente("Cliente Sem Registo Algum")
        self.assertEqual(contactos, [])

    def test_cliente_vazio_devolve_lista_vazia_sem_ler_ficheiros(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read) as mock_read:
            contactos = core.get_contactos_cliente("")
        self.assertEqual(contactos, [])
        mock_read.assert_not_called()

    def test_campos_devolvidos(self):
        with patch("core._gcs_read", side_effect=_fake_gcs_read):
            contactos = core.get_contactos_cliente("Cliente X")
        um = next(c for c in contactos if c["Nome"] == "Pessoa Um")
        self.assertEqual(um["Cargo"], "Gestor de Projeto")
        self.assertEqual(um["Email"], "um@x.pt")
        self.assertEqual(um["Telefone"], "911111111")


class TestTemaCentral(unittest.TestCase):
    """Fase 1 da Identidade Visual: .streamlit/config.toml passa a ser a
    fonte de verdade do tema — os valores têm de bater certo com
    core.THEME, para as duas fontes nunca voltarem a divergir em silêncio
    (era exatamente isto que acontecia antes: config.toml definia um tema
    claro que o GLOBAL_CSS anulava com !important)."""

    @classmethod
    def setUpClass(cls):
        with open(_CONFIG_TOML_PATH, "rb") as f:
            cls.cfg = tomllib.load(f)["theme"]

    def test_base_claro(self):
        self.assertEqual(self.cfg["base"], "light")

    def test_cores_batem_certo_com_theme(self):
        self.assertEqual(self.cfg["primaryColor"], core.THEME["accent"])
        self.assertEqual(self.cfg["backgroundColor"], core.THEME["background"])
        self.assertEqual(self.cfg["secondaryBackgroundColor"], core.THEME["surface"])
        self.assertEqual(self.cfg["textColor"], core.THEME["text"])
        self.assertEqual(self.cfg["borderColor"], core.THEME["border"])
        self.assertEqual(self.cfg["greenColor"], core.THEME["success"])
        self.assertEqual(self.cfg["orangeColor"], core.THEME["warning"])
        self.assertEqual(self.cfg["redColor"], core.THEME["error"])

    def test_raio_centralizado(self):
        self.assertEqual(self.cfg["baseRadius"], core.THEME["radius"])
        self.assertEqual(self.cfg["buttonRadius"], core.THEME["radius"])

    def test_sidebar_clara(self):
        self.assertEqual(self.cfg["sidebar"]["backgroundColor"], core.THEME["surface"])
        self.assertEqual(self.cfg["sidebar"]["textColor"], core.THEME["text"])

    def test_theme_color_pwa_bate_certo(self):
        # inject_pwa_meta() usa THEME['background'] — confirma que não há
        # um hexadecimal solto e desalinhado a repetir a cor à parte.
        with patch("streamlit.markdown") as mock_md:
            core.inject_pwa_meta()
        html = mock_md.call_args[0][0]
        self.assertIn(f'content="{core.THEME["background"]}"', html)


class TestGlobalCssSemContradicao(unittest.TestCase):
    """Fase 1 da Identidade Visual: o GLOBAL_CSS deixa de forçar um fundo
    escuro em cima do tema claro do config.toml (o !important que hoje o
    anula) e deixa de forçar a barra lateral escura via CSS — isso passa
    a ser feito pelo [theme.sidebar] nativo do Streamlit."""

    def test_stapp_nao_forca_fundo_escuro(self):
        self.assertNotIn("#0F172A", core.GLOBAL_CSS)
        self.assertNotIn("#1a1a2e", core.GLOBAL_CSS)

    def test_sidebar_deixa_de_ser_forcada_via_css(self):
        self.assertNotIn('data-testid="stSidebar"', core.GLOBAL_CSS)

    def test_cores_vem_todas_do_theme(self):
        for chave in ("background", "surface", "border", "text",
                      "text_secondary", "accent", "accent_hover",
                      "success", "warning", "error", "radius"):
            self.assertIn(core.THEME[chave], core.GLOBAL_CSS)


class TestBotaoLabelHerdaCorDoBotao(unittest.TestCase):
    """O rótulo de qualquer st.button() vem embrulhado num <p>/<div>
    interno do Streamlit. Sem uma regra central a forçar herança, uma
    regra de módulo tão simples como "p, div, span { color: ... }"
    (usada em mais de um ecrã para o texto secundário) ganha ao branco
    do botão primário, porque uma cor especificada diretamente no
    elemento vence sempre uma cor apenas herdada — mesmo com
    !important do lado do botão. Isto causou um botão "Registar Ponto"
    com texto escuro sobre fundo de acento (contraste insuficiente)."""

    def test_regra_central_existe(self):
        self.assertIn(".stButton > button * ", core.GLOBAL_CSS)
        self.assertIn("color: inherit !important", core.GLOBAL_CSS)


class TestEscapeHtml(unittest.TestCase):
    def test_escapa_angulares(self):
        self.assertEqual(core.escape_html("<script>"), "&lt;script&gt;")

    def test_none_vira_vazio(self):
        self.assertEqual(core.escape_html(None), "")

    def test_numero_vira_string(self):
        self.assertEqual(core.escape_html(42), "42")


class TestRenderBadgeHtml(unittest.TestCase):
    def test_tom_valido_aplica_classe_certa(self):
        html = core.render_badge_html("Pendente", "warning")
        self.assertIn("gn-badge-warning", html)
        self.assertIn("Pendente", html)

    def test_tom_invalido_cai_em_neutral(self):
        html = core.render_badge_html("X", "cor-que-nao-existe")
        self.assertIn("gn-badge-neutral", html)

    def test_escapa_label(self):
        html = core.render_badge_html("<b>X</b>", "error")
        self.assertNotIn("<b>", html)
        self.assertIn("&lt;b&gt;", html)


class TestRenderCardHtml(unittest.TestCase):
    def test_titulo_e_subtitulo(self):
        html = core.render_card_html("Obra Teste", subtitle="Sines")
        self.assertIn("Obra Teste", html)
        self.assertIn("Sines", html)
        self.assertIn("gn-card-title", html)

    def test_sem_badge_nao_desenha_badge(self):
        html = core.render_card_html("Obra Teste")
        self.assertNotIn("gn-badge", html)

    def test_com_badge(self):
        html = core.render_card_html("Obra Teste", badge="Ativa", badge_tone="success")
        self.assertIn("gn-badge-success", html)
        self.assertIn("Ativa", html)

    def test_fields_em_grelha(self):
        html = core.render_card_html(
            "Obra Teste", fields=[("Cliente", "Cliente X"), ("Entrada", "08:00")])
        self.assertIn("gn-card-grid", html)
        self.assertIn("Cliente", html)
        self.assertIn("Cliente X", html)
        self.assertIn("08:00", html)

    def test_sem_fields_nao_desenha_grelha(self):
        html = core.render_card_html("Obra Teste")
        self.assertNotIn("gn-card-grid", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)

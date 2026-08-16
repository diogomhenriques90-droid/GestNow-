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
import unittest
from unittest.mock import patch

import core

_OBRAS_LISTA_CSV = (
    "Obra,Cliente,Ativa\n"
    "Obra Ativa X,Cliente X,Ativa\n"
    "Obra Ativa Y,Cliente Y,Ativa\n"
    "Obra Inativa Z,Cliente Z,Inativa\n"
).encode("utf-8-sig")


def _fake_gcs_read(fn):
    if fn == "obras_lista.csv":
        return io.BytesIO(_OBRAS_LISTA_CSV)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)

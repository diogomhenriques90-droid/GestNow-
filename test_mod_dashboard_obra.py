"""
Testes do painel de obra (mod_dashboard_obra) — bloqueiam o comportamento
ATUAL das funções de cálculo/normalização antes de futuras alterações.

Só testam funções puras (sem Streamlit, sem GCS, sem dados de produção):
  _nz   — limpeza de valores vazios/NaN
  _dur_meses — duração em meses a partir das datas
  _money — formatação monetária (€/h, valor)
  _esc  — escape de HTML

Correr:  python -m unittest test_mod_dashboard_obra -v
"""
import unittest
from mod_dashboard_obra import _nz, _dur_meses, _money, _esc


class TestNz(unittest.TestCase):
    def test_vazios_viram_string_vazia(self):
        self.assertEqual(_nz(None), "")
        self.assertEqual(_nz(""), "")
        self.assertEqual(_nz("   "), "")
        self.assertEqual(_nz("nan"), "")
        self.assertEqual(_nz("None"), "")

    def test_texto_e_limpo_mas_preservado(self):
        self.assertEqual(_nz("  Obra A  "), "Obra A")
        self.assertEqual(_nz("0"), "0")          # zero é valor válido, não vazio
        self.assertEqual(_nz("Cliente X"), "Cliente X")


class TestDurMeses(unittest.TestCase):
    def test_sem_data_fim_devolve_traco(self):
        self.assertEqual(_dur_meses("01/01/2025", ""), "—")
        self.assertEqual(_dur_meses("01/01/2025", None), "—")

    def test_sem_data_inicio_devolve_traco(self):
        self.assertEqual(_dur_meses("", "01/07/2025"), "—")

    def test_datas_invalidas_devolvem_traco(self):
        self.assertEqual(_dur_meses("xpto", "abc"), "—")

    def test_seis_meses(self):
        self.assertEqual(_dur_meses("01/01/2025", "01/07/2025"), "6 meses")

    def test_um_mes_singular(self):
        self.assertEqual(_dur_meses("01/01/2025", "01/02/2025"), "1 mês")

    def test_menos_de_um_mes(self):
        self.assertEqual(_dur_meses("01/01/2025", "15/01/2025"), "< 1 mês")

    def test_ajuste_quando_dia_fim_menor(self):
        # 15/jan -> 01/fev conta como < 1 mês (dia de fim menor que o de início)
        self.assertEqual(_dur_meses("15/01/2025", "01/02/2025"), "< 1 mês")


class TestMoney(unittest.TestCase):
    def test_vazio_devolve_traco(self):
        self.assertEqual(_money(""), "—")
        self.assertEqual(_money(None), "—")
        self.assertEqual(_money("nan"), "—")

    def test_invalido_devolve_traco(self):
        self.assertEqual(_money("abc"), "—")

    def test_ponto_e_virgula_decimal(self):
        self.assertEqual(_money("12.5"), "€ 12,50")
        self.assertEqual(_money("12,5"), "€ 12,50")

    def test_zero(self):
        self.assertEqual(_money("0"), "€ 0,00")


class TestEsc(unittest.TestCase):
    def test_escapa_angulares(self):
        self.assertEqual(_esc("<b>"), "&lt;b&gt;")

    def test_none_vira_vazio(self):
        self.assertEqual(_esc(None), "")

    def test_outros_caracteres_preservados(self):
        self.assertEqual(_esc("a & b"), "a & b")


if __name__ == "__main__":
    unittest.main(verbosity=2)

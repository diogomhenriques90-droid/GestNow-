"""
Testes do painel de obra (mod_dashboard_obra).

Duas partes:
1. Funções puras (sem Streamlit, sem GCS, sem dados de produção):
   _nz, _dur_meses, _money, _esc.
2. Fase A (Dashboard de Obra — campos operacionais): a vista de detalhe
   ("Ver detalhe →") passa a mostrar, só leitura, os campos já gravados
   noutros ecrãs (Responsável de Equipa, Modalidade da Diária,
   Alojamento/Viatura/Ferramentas/EPIs, Descrição dos Trabalhos,
   Requisitos Adicionais, Plataforma, Contacto do Cliente) — sem
   duplicar edição, que continua em Produção → Obras e Faturação →
   Clientes.

Não tocam em GCS real: `core._gcs_read` é mockado com CSVs fixos em
memória para acessos_requisitos_obras.csv / clientes_financeiro.csv /
contactos_clientes.csv (os únicos campos da Fase A que não vêm já nos
argumentos posicionais de render_dashboard_obra).

Correr:  python -m unittest test_mod_dashboard_obra -v
"""
import io
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core
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


# ─────────────────────────────────────────────────────────────────────────
# Fase A (Dashboard de Obra — campos operacionais): vista de detalhe
# ─────────────────────────────────────────────────────────────────────────

_OBRAS_RECORDS = [{
    "Obra": "Obra Dashboard Teste", "Cliente": "Cliente Dashboard Teste",
    "Local": "Sines", "Localizacao": "", "Ativa": "Ativa",
    "DataInicio": "01/01/2026", "DataFim": "01/07/2026",
    "Alojamento": "CPS", "Viatura": "Cliente", "Ferramentas": "CPS",
    "EPIs": "Outro", "Descricao_Trabalhos": "Manutenção de instrumentação",
    "Plataforma": "Andaime 6m", "Responsavel_Equipa": "Ana Responsável",
}]

_INST_ACESSOS_RECORDS = [{
    "Obra": "Obra Dashboard Teste", "Utilizador": "Ana Responsável",
    "Cargo": "Chefe de Equipa", "Ativo": "Sim", "PrecoHora": "20",
}]

_DIARIAS_CONFIG_RECORDS = [{
    "Obra": "Obra Dashboard Teste", "Valor_Diaria": "35",
    "Modalidade": "Corrida Semanal",
}]

_REQ_OBRAS_CSV = (
    "ID,Obra,Tipo_Obra,Documentos_Obrigatorios,Nivel_Seguranca,Instrucoes,Atualizado_Em\n"
    "RQ1,Obra Dashboard Teste,Normal,Cartão de Cidadão,Médio,"
    "Zona ATEX — cuidado.,01/01/2026\n"
).encode("utf-8-sig")

_CLIENTES_FINANCEIRO_CSV = (
    "ID,Nome,Activo\nC1,Cliente Dashboard Teste,Sim\n"
).encode("utf-8-sig")

_CONTACTOS_CLIENTES_CSV = (
    "ID,Cliente_ID,Nome,Cargo,Email,Telefone,Notas,Criado_Por,Data_Criacao\n"
    "CT1,C1,Miguel Contacto,Gestor de Projeto,miguel@cliente.pt,911111111,"
    ",Admin,01/01/2026\n"
).encode("utf-8-sig")


def _fake_gcs_read(fn):
    if fn == "acessos_requisitos_obras.csv":
        return io.BytesIO(_REQ_OBRAS_CSV)
    if fn == "clientes_financeiro.csv":
        return io.BytesIO(_CLIENTES_FINANCEIRO_CSV)
    if fn == "contactos_clientes.csv":
        return io.BytesIO(_CONTACTOS_CLIENTES_CSV)
    return None


def _script(obras_records, inst_acessos_records, diarias_config_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['dash_obra_detalhe'] = "Obra Dashboard Teste"
    from mod_dashboard_obra import render_dashboard_obra
    vazio = pd.DataFrame()
    obras_db = pd.DataFrame(obras_records)
    inst_acessos_db = pd.DataFrame(inst_acessos_records)
    diarias_config_db = pd.DataFrame(diarias_config_records)
    args = [vazio, obras_db] + [vazio] * 17 + [inst_acessos_db, diarias_config_db, vazio, vazio, vazio]
    render_dashboard_obra(*args)


def _run(obras_records=None, inst_acessos_records=None, diarias_config_records=None,
         gcs_read=_fake_gcs_read):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    inst_acessos_records = inst_acessos_records if inst_acessos_records is not None \
        else _INST_ACESSOS_RECORDS
    diarias_config_records = diarias_config_records if diarias_config_records is not None \
        else _DIARIAS_CONFIG_RECORDS
    core._cached_load_db.clear()
    with patch("core._gcs_read", side_effect=gcs_read), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, inst_acessos_records, diarias_config_records),
            default_timeout=30)
        at.run()
    return at


class TestCamposOperacionaisSoLeitura(unittest.TestCase):
    """Fase A do Dashboard de Obra (campos operacionais): a vista de
    detalhe ("Ver detalhe →") passa a mostrar, só leitura, os campos já
    gravados noutros ecrãs — Responsável de Equipa, Modalidade da
    Diária, Alojamento/Viatura/Ferramentas/EPIs, Descrição dos
    Trabalhos, Requisitos Adicionais e Contacto do Cliente. A edição
    continua a viver só em Produção → Obras e Faturação → Clientes."""

    def test_sem_erro(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_mostra_todos_os_campos_operacionais_preenchidos(self):
        at = _run()
        textos = " ".join(m.value for m in at.markdown) + \
                 " ".join(i.value for i in at.info) + \
                 " ".join(c.value for c in at.caption)
        self.assertIn("Ana Responsável", textos)
        self.assertIn("Corrida Semanal", textos)
        self.assertIn("CPS", textos)          # Alojamento
        self.assertIn("Andaime 6m", textos)   # Plataforma
        self.assertIn("Manutenção de instrumentação", textos)  # Descrição
        self.assertIn("Zona ATEX", textos)    # Requisitos Adicionais
        self.assertIn("Miguel Contacto", textos)
        self.assertIn("miguel@cliente.pt", textos)

    def test_obra_sem_campos_preenchidos_nao_mostra_secoes_vazias(self):
        obra_vazia = [{
            "Obra": "Obra Dashboard Teste", "Cliente": "Cliente Sem Dados",
            "Local": "Sines", "Localizacao": "", "Ativa": "Ativa",
            "DataInicio": "01/01/2026", "DataFim": "",
        }]
        at = _run(obras_records=obra_vazia, inst_acessos_records=[],
                  diarias_config_records=[], gcs_read=lambda fn: None)
        self.assertFalse(at.exception, msg=str(at.exception))
        titulos_grupo = [m.value for m in at.markdown
                          if '<p class="dob-group">' in m.value]
        self.assertFalse(any("Logística" in t for t in titulos_grupo))
        self.assertFalse(any("Descrição dos Trabalhos" in t for t in titulos_grupo))
        self.assertFalse(any("Requisitos Adicionais" in t for t in titulos_grupo))
        textos_info = " ".join(i.value for i in at.info)
        self.assertIn("Sem pessoas de contacto registadas", textos_info)

    def test_contacto_do_cliente_nao_mistura_com_outro_cliente(self):
        # Cliente da obra não tem contactos (só "Cliente Dashboard Teste"
        # tem, no fixture de contactos_clientes.csv) — confirma que a
        # ligação é por Cliente_ID e não aparece nada indevido.
        obra_outro_cliente = [{**_OBRAS_RECORDS[0], "Cliente": "Outro Cliente Qualquer"}]
        at = _run(obras_records=obra_outro_cliente)
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("Miguel Contacto", textos)
        textos_info = " ".join(i.value for i in at.info)
        self.assertIn("Sem pessoas de contacto registadas", textos_info)


if __name__ == "__main__":
    unittest.main(verbosity=2)

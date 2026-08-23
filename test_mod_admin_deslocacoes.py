"""
Testes do módulo de Gestão de Deslocações (mod_admin_deslocacoes.py)
— Dormidas + Bilhetes de Viagem + Resumo por Deslocação.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py).

Fora de âmbito, de propósito: o gráfico "Custo de Deslocações por
Obra" (Plotly, aba Resumo) e a mini-barra de progresso HTML +
legenda "■ Bilhetes X% / ■ Dormidas Y%" logo acima dele, no mesmo
cartão — usam as MESMAS 2 cores (#3B82F6 azul / #8B5CF6 roxo) para
codificar as mesmas 2 categorias (Bilhetes/Dormidas); migrar só a
barra HTML deixaria as duas representações lado a lado com cores
diferentes para os mesmos dados. O relatório PDF de reembolsos
(reportlab) também fica de fora, mesmo critério das outras Fases.

Não tocam em GCS real: `mod_admin_deslocacoes.load_db` é mockado
diretamente (devolve DataFrames de teste, consoante o ficheiro
pedido).

Correr:  python -m unittest test_mod_admin_deslocacoes -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_OBRAS_RECORDS = [{"Obra": "Obra Deslocacoes Teste", "Ativa": "Ativa"}]
_USERS_RECORDS = [{"Nome": "Ana Teste"}]

_DORMIDAS_RECORDS = [
    {"ID": "D1", "Data_Checkin": "01/01/2026", "Data_Checkout": "03/01/2026",
     "Colaborador": "Ana Teste", "Obra": "Obra Deslocacoes Teste",
     "Hotel": "Hotel Teste", "Cidade": "Sines", "Valor_Noite": "50",
     "Total": "100", "Estado": "Confirmado", "Confirmacao": "",
     "Pago_Por": "Empresa", "Notas": ""},
    {"ID": "D2", "Data_Checkin": "05/01/2026", "Data_Checkout": "06/01/2026",
     "Colaborador": "Ana Teste", "Obra": "Obra Deslocacoes Teste",
     "Hotel": "Hotel Cancelado", "Cidade": "Sines", "Valor_Noite": "50",
     "Total": "50", "Estado": "Cancelado", "Confirmacao": "",
     "Pago_Por": "Empresa", "Notas": ""},
]

_BILHETES_RECORDS = [
    {"ID": "B1", "Tipo": "Avião", "Companhia": "TAP", "Origem": "Lisboa",
     "Destino": "Porto", "Data_Ida": "01/01/2026", "Data_Volta": "",
     "Hora_Partida": "10:00", "Hora_Chegada": "11:00", "Duracao": "1h",
     "Colaborador": "Ana Teste", "Obra": "Obra Deslocacoes Teste",
     "N_Passageiros": "1", "Classe": "Económica", "Preco_Total": "80",
     "Pago_Por": "Empresa", "Estado": "Confirmado", "Referencia": "REF1",
     "Link_Reserva": "", "Escalas": "Direto", "Bagagem": "",
     "Cancelamento": "", "Bilhete_b64": "", "Notas": "",
     "Criado_Por": "Admin", "Criado_Em": "01/01/2026"},
    {"ID": "B2", "Tipo": "Comboio", "Companhia": "CP", "Origem": "Lisboa",
     "Destino": "Coimbra", "Data_Ida": "01/01/2026", "Data_Volta": "",
     "Hora_Partida": "09:00", "Hora_Chegada": "11:00", "Duracao": "2h",
     "Colaborador": "Ana Teste", "Obra": "Obra Deslocacoes Teste",
     "N_Passageiros": "1", "Classe": "", "Preco_Total": "30",
     "Pago_Por": "Colaborador (reembolso)", "Estado": "Reservado",
     "Referencia": "REF2", "Link_Reserva": "", "Escalas": "Direto",
     "Bagagem": "", "Cancelamento": "", "Bilhete_b64": "", "Notas": "",
     "Criado_Por": "Admin", "Criado_Em": "01/01/2026"},
]


def _fake_load_db(fn, cols, silent=False):
    if fn == "dormidas.csv":
        return pd.DataFrame(_DORMIDAS_RECORDS)
    if fn == "bilhetes_viagem.csv":
        return pd.DataFrame(_BILHETES_RECORDS)
    return pd.DataFrame(columns=cols)


def _fake_load_db_vazio(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(obras_records, users_records, pre_session_state=None):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user'] = 'Admin'
    if pre_session_state:
        for k, v in pre_session_state.items():
            st.session_state[k] = v
    from mod_admin_deslocacoes import render_deslocacoes
    render_deslocacoes(pd.DataFrame(obras_records), pd.DataFrame(users_records))


def _run(load_db_fn=_fake_load_db, pre_session_state=None):
    core._cached_load_db.clear()
    with patch("mod_admin_deslocacoes.load_db", side_effect=load_db_fn), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(_OBRAS_RECORDS, _USERS_RECORDS, pre_session_state),
            default_timeout=30)
        at.run()
    return at


class TestRenderDeslocacoesSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro, com e sem dados. Cobre
    as 3 abas (Dormidas, Bilhetes de Viagem, Resumo por Deslocação) —
    dentro de Bilhetes, também os 4 sub-separadores (Pesquisa IA,
    Registar Manual, Lista de Bilhetes, Reembolsos) — porque
    st.tabs() desenha o conteúdo de todos de uma vez."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(load_db_fn=_fake_load_db_vazio)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_com_opcao_ia_pesquisada(self):
        # Simula o estado após uma pesquisa IA (sem chamar a API real)
        # — exercita _render_card_opcao() e a caixa de confirmação.
        opcao = {
            "tipo": "Avião", "companhia": "TAP", "origem": "Lisboa",
            "destino": "Porto", "hora_partida": "10:00",
            "hora_chegada": "11:00", "duracao": "1h", "escalas": "Direto",
            "bagagem": "1x23kg", "preco_total": 80.0, "preco_por_pax": 80.0,
            "cancelamento": "Cancelamento gratuito até 24h antes",
            "link_reserva": "", "notas": "Voo direto",
        }
        at = _run(pre_session_state={
            "resultados_ia": [opcao],
            "pesquisa_params": {"tipo": "Avião", "n_pax": 1},
            "fonte_pesquisa_ia": "Pesquisa web",
            "aviso_ia": "",
            "mostrar_form_guardar": True,
            "opcao_selecionada": opcao,
        })
        self.assertFalse(at.exception, msg=str(at.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

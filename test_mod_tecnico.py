"""
Testes do módulo Técnico/Chefe de Equipa (mod_tecnico.py) — Pontos,
Validar Horas (chefe), Folha (chefe), HSE, Perfil, Pedidos.

Bloqueia primeiro o comportamento ATUAL — o ecrã renderiza sem erro —
antes da Fase 3 da Identidade Visual migrar este módulo para o THEME
central (core.py). Decisão do utilizador (2026-08-23): remover o
fundo escuro global (.stApp) e substituir o vermelho de marca
#DC2626 por THEME['accent'] — unificar com o resto da app.

Fora de âmbito, de propósito: uploads de ficheiros e assinatura (não
acionados nestes testes — dependem de widgets de upload).

Não tocam em GCS real: `mod_tecnico.load_db`/`_load_users_cached` são
mockados diretamente.

Correr:  python -m unittest test_mod_tecnico -v
"""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_USER_TECNICO = {
    "Nome": "Ana Teste", "Tipo": "Técnico", "Cargo": "Instrumentista",
    "Foto": "", "PDFs_Validados": "Sim", "PDFs_Validacao_Data": "01/01/2026",
    "PrecoHoraStatus": "Recusado", "PrecoHora": "15.0",
    "PrecoHoraData": "01/01/2026", "Campos_Bloqueados": "[]",
    "Telefone": "912345678", "NIF": "123456789",
    "Data_Nascimento": "01/01/1990", "Morada": "Rua Teste",
    "Localidade": "Porto", "Concelho": "Porto", "Codigo_Postal": "4000-000",
    "Nome_Emergencia": "Bruno Teste", "Contacto_Emergencia": "913456789",
    "Grau_Parentesco": "Irmão", "Email": "ana@teste.pt",
    "Password": "", "PIN": "", "Contrato_Enviado": "Não",
    "Contrato_Assinado": "Não", "Contrato_Validado_Admin": "Não",
    "Contrato_b64": "",
}

_USER_CHEFE = dict(_USER_TECNICO)
_USER_CHEFE.update({
    "Nome": "Bruno Chefe", "Tipo": "Chefe de Equipa", "Cargo": "Chefe de Equipa",
})

_OBRAS_RECORDS = [
    {"Obra": "Obra Técnico Teste", "Ativa": "Ativa",
     "Codigo": "OBR-01", "Cliente": "Cliente Teste"},
]

_REGISTOS_RECORDS = [
    {"ID": "R1", "Data": pd.Timestamp.today().strftime("%d/%m/%Y"),
     "Técnico": "Ana Teste", "Obra": "Obra Técnico Teste",
     "Frente": "Instrumentação", "Turnos": "08:00-17:00",
     "Horas_Total": "9", "Relatorio": "Montagem de instrumentos",
     "Status": "0", "Periodo": "1"},
]

_VAZIO_COLS = {
    "usuarios.csv": ["Nome", "Tipo", "Cargo"],
    "registos.csv": ["ID", "Data", "Técnico", "Obra", "Status"],
    "obras_lista.csv": ["Obra", "Ativa"],
}


def _fake_load_db(fn, cols, silent=False):
    return pd.DataFrame(columns=cols)


def _script(user_nome, tipo, cargo, obras_records, registos_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user']  = user_nome
    st.session_state['tipo']  = tipo
    st.session_state['cargo'] = cargo
    from mod_tecnico import render_tecnico
    vazio = pd.DataFrame()
    render_tecnico(
        pd.DataFrame(), pd.DataFrame(obras_records), vazio,
        pd.DataFrame(registos_records), vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio,
    )


def _run(user_nome="Ana Teste", tipo="Técnico", cargo="Instrumentista",
          user_record=None, obras_records=_OBRAS_RECORDS,
          registos_records=_REGISTOS_RECORDS):
    core._cached_load_db.clear()
    users_df = pd.DataFrame([user_record]) if user_record else pd.DataFrame()
    with patch("mod_tecnico.load_db", side_effect=_fake_load_db), \
         patch("mod_tecnico._load_users_cached", return_value=users_df), \
         patch("core._gcs_read", return_value=None), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(user_nome, tipo, cargo, obras_records, registos_records),
            default_timeout=30,
        )
        at.run()
    return at


class TestRenderTecnicoSemErro(unittest.TestCase):
    """Smoke test — o ecrã renderiza sem erro. Cobre a vista de
    Técnico normal (4 separadores: Pontos, HSE, Perfil, Pedidos) e a
    vista de Chefe de Equipa (6 separadores, com Validar Horas e
    Folha adicionais), com e sem dados."""

    def test_sem_erro_tecnico_com_dados(self):
        at = _run(user_record=_USER_TECNICO)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_chefe_com_dados(self):
        at = _run(user_nome="Bruno Chefe", tipo="Chefe de Equipa",
                   cargo="Chefe de Equipa", user_record=_USER_CHEFE)
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(user_record=None, obras_records=[], registos_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 3 da Identidade Visual: mod_tecnico.py lê as suas cores de
    core.THEME — nunca mais hexadecimais soltos, um só cinzento
    secundário, sem fundos escuros forçados. Decisão do utilizador
    (2026-08-23): o fundo global `.stApp` deixa de ser forçado a
    escuro e o vermelho de marca #DC2626 foi substituído por
    THEME['accent'] — não há mais um tema à parte para o Técnico."""

    def test_css_usa_theme(self):
        at = _run(user_record=_USER_TECNICO)
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        for chave in ("background", "surface", "border", "text",
                      "text_secondary", "accent", "warning", "success",
                      "error"):
            self.assertIn(core.THEME[chave], textos)

    def test_um_so_cinzento_secundario(self):
        at = _run(user_record=_USER_TECNICO)
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertNotIn("#475569", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_sem_fundo_escuro_forcado(self):
        at = _run(user_record=_USER_TECNICO)
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("background:#0F172A", textos)
        self.assertNotIn("background: #0F172A", textos)
        self.assertNotIn("background:#1E293B", textos)
        self.assertNotIn("#F1F5F9", textos)

    def test_vermelho_de_marca_substituido(self):
        at = _run(user_record=_USER_TECNICO)
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#DC2626", textos)


if __name__ == "__main__":
    unittest.main(verbosity=2)

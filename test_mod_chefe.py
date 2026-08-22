"""
Testes do módulo do Chefe de Equipa (mod_chefe.py) — Fase 2 da
Identidade Visual: migração para o THEME central (core.py) e as
funções partilhadas render_card()/render_badge(), em vez do HTML de
cartão/badge próprio que existia antes (247 cores à mão, a mais de
qualquer módulo da app).

Não tocam em GCS real: `core._gcs_read` é mockado com um CSV fixo em
memória. `render_chefe` é invocado diretamente (sem passar por
app.py/mod_admin.py).

Correr:  python -m unittest test_mod_chefe -v
"""
import io
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import core

_USUARIOS_CSV = (
    "Nome,Tipo,Cargo,Foto\n"
    "Chefe Teste,Chefe de Equipa,Chefe de Equipa,\n"
    "Ana Alocada,Técnico,Instrumentista,\n"
).encode("utf-8-sig")


def _fake_gcs_read(fn):
    if fn == "usuarios.csv":
        return io.BytesIO(_USUARIOS_CSV)
    return None


_OBRAS_RECORDS = [{
    "Obra": "Obra Chefe Teste", "Codigo": "OBR-001", "Cliente": "Cliente Teste",
    "Ativa": "Ativa",
}]

_REGISTOS_RECORDS = [{
    "ID": "R1", "Técnico": "Ana Alocada", "Obra": "Obra Chefe Teste",
    "Frente": "Frente A", "Turnos": "08:00-17:00", "Data": "01/01/2026",
    "Horas_Total": "8", "Status": "0", "Relatorio": "",
}]

_INST_ACESSOS_RECORDS = [{
    "Utilizador": "Chefe Teste", "Obra": "Obra Chefe Teste", "Ativo": "Sim",
}]

_REQ_FER_RECORDS = [{
    "ID": "F1", "Solicitante": "Ana Alocada", "Obra": "Obra Chefe Teste",
    "Data": "01/01/2026", "Status": "Pendente", "Descricao": "Chave de fendas",
}]


def _script(obras_records, registos_records, inst_acessos_records, req_fer_records):
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user']  = 'Chefe Teste'
    st.session_state['tipo']  = 'Chefe de Equipa'
    st.session_state['cargo'] = 'Chefe de Equipa'
    from mod_chefe import render_chefe
    vazio = pd.DataFrame()
    args = [
        vazio,                              # users (não usado diretamente; _load_users_cached lê do GCS)
        pd.DataFrame(obras_records),         # obras_db
        vazio,                               # frentes_db
        pd.DataFrame(registos_records),      # registos_db
        vazio, vazio, vazio, vazio, vazio,   # faturas, docs, incs, sw, obs
        vazio, vazio, vazio,                 # equip, diags, diags_u
        vazio, vazio, vazio,                 # folhas, comuns, comuns_u
        pd.DataFrame(req_fer_records),       # req_fer_db
        vazio, vazio,                        # req_mat_db, req_epi_db
        vazio,                               # avals_db
        pd.DataFrame(inst_acessos_records),  # inst_acessos_db
    ]
    render_chefe(*args)


def _run(obras_records=None, registos_records=None, inst_acessos_records=None,
         req_fer_records=None):
    obras_records = obras_records if obras_records is not None else _OBRAS_RECORDS
    registos_records = registos_records if registos_records is not None else _REGISTOS_RECORDS
    inst_acessos_records = inst_acessos_records if inst_acessos_records is not None \
        else _INST_ACESSOS_RECORDS
    req_fer_records = req_fer_records if req_fer_records is not None else _REQ_FER_RECORDS
    core._cached_load_db.clear()
    core._load_users_cached.clear()
    with patch("core._gcs_read", side_effect=_fake_gcs_read), \
         patch("core._gcs_client", return_value=None):
        at = AppTest.from_function(
            _script,
            args=(obras_records, registos_records, inst_acessos_records, req_fer_records),
            default_timeout=30)
        at.run()
    return at


def _script_data_ja_datetime(obras_records, registos_records, inst_acessos_records):
    # core.py._cached_load_all já converte registos_db['Data'] para
    # datetime64 antes de o passar a render_chefe — ao contrário de
    # _script() (que usa strings), este script reproduz fielmente essa
    # forma real dos dados, para apanhar bugs que só existem quando a
    # coluna chega já convertida (ver KPI "Horas Mês").
    import streamlit as st
    import pandas as pd
    st.session_state.setdefault('_fv', {})
    st.session_state['user']  = 'Chefe Teste'
    st.session_state['tipo']  = 'Chefe de Equipa'
    st.session_state['cargo'] = 'Chefe de Equipa'
    from mod_chefe import render_chefe
    vazio = pd.DataFrame()
    registos_df = pd.DataFrame(registos_records)
    registos_df['Data'] = pd.to_datetime(
        registos_df['Data'], dayfirst=True, errors='coerce'
    ).astype('datetime64[s]')
    args = [
        vazio, pd.DataFrame(obras_records), vazio, registos_df,
        vazio, vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        vazio, vazio, vazio, vazio, vazio, vazio, vazio,
        pd.DataFrame(inst_acessos_records),
    ]
    render_chefe(*args)


class TestKpiHorasMesComDataJaConvertida(unittest.TestCase):
    """Defesa: core.py._cached_load_all já converte registos_db['Data']
    para datetime64 antes de chegar a mod_chefe.py — este teste
    reproduz essa forma real dos dados (não strings) para o cálculo
    de "Horas Mês" (KPI do topo), que em produção rebentou com
    "TypeError: Invalid comparison between dtype=datetime64[s] and
    date" (comparação de datetime64 com um datetime.date puro).

    Não consegui reproduzir localmente a versão exata do pandas que
    causa o erro (a instalação local tolera .dt.date em
    datetime64[s]; requirements.txt fixa só "pandas>=2.2.0", sem
    limite superior, por isso produção pode ter resolvido para uma
    versão diferente da local). Reproduzi isoladamente a mensagem de
    erro exata comparando datetime64 diretamente com datetime.date
    (sem passar por .dt.date) — confirma o mecanismo. A correção
    (comparar com pd.Timestamp em vez de datetime.date) elimina essa
    classe de erro em qualquer versão do pandas, por isso mantenho
    este teste como proteção mesmo sem conseguir vê-lo falhar aqui."""

    def test_horas_mes_nao_rebenta_com_data_datetime64(self):
        core._cached_load_db.clear()
        core._load_users_cached.clear()
        with patch("core._gcs_read", side_effect=_fake_gcs_read), \
             patch("core._gcs_client", return_value=None):
            at = AppTest.from_function(
                _script_data_ja_datetime,
                args=(_OBRAS_RECORDS, _REGISTOS_RECORDS, _INST_ACESSOS_RECORDS),
                default_timeout=30)
            at.run()
        self.assertFalse(at.exception, msg=str(at.exception))


class TestRenderChefeSemErro(unittest.TestCase):
    """Smoke test — o ecrã continua a renderizar sem erro depois da
    migração para o THEME central. Cobre todos os separadores (Equipa,
    Validar Horas, Meu Ponto, Folha de Ponto, HSE, Pedidos) porque
    st.tabs() desenha o conteúdo de todos os separadores de uma vez,
    independente de qual está selecionado."""

    def test_sem_erro_com_dados(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))

    def test_sem_erro_sem_dados(self):
        at = _run(obras_records=[], registos_records=[],
                   inst_acessos_records=[], req_fer_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))


class TestTemaClaroAplicado(unittest.TestCase):
    """Fase 2 da Identidade Visual: mod_chefe.py lê as suas cores de
    core.THEME — nunca mais hexadecimais soltos a duplicar avisos/
    cinzentos, e o fundo escuro forçado (.stApp) desaparece."""

    def test_nao_forca_fundo_escuro(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        self.assertNotIn(".stApp", css)
        self.assertNotIn("#0F172A", css)
        self.assertNotIn("#1a1a2e", css)

    def test_css_usa_theme(self):
        at = _run()
        css = " ".join(m.value for m in at.markdown if "<style>" in m.value)
        for chave in ("surface", "border", "text", "text_secondary", "accent"):
            self.assertIn(core.THEME[chave], css)

    def test_corpo_usa_theme_para_estados(self):
        # success/warning aparecem no corpo do ecrã (cartões, não no
        # bloco <style> — ex. "Sem horas pendentes!", legenda de estado).
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn(core.THEME["success"], textos)
        self.assertIn(core.THEME["warning"], textos)

    def test_um_so_cinzento_secundario(self):
        # As duas duplicações originais (#64748B e #94A3B8) deixam de
        # aparecer — só o cinzento único do THEME.
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#64748B", textos)
        self.assertNotIn("#94A3B8", textos)
        self.assertIn(core.THEME["text_secondary"], textos)

    def test_um_so_aviso_e_um_so_erro(self):
        # As duplicações de aviso (#F59E0B / #F97316) e o vermelho usado
        # como acento decorativo (#DC2626) deixam de aparecer.
        at = _run()
        textos = " ".join(m.value for m in at.markdown)
        self.assertNotIn("#F59E0B", textos)
        self.assertNotIn("#F97316", textos)
        self.assertNotIn("#DC2626", textos)

    def test_dot_color_vem_do_theme(self):
        import mod_chefe
        self.assertEqual(mod_chefe._DOT_COLOR["0"], core.THEME["warning"])
        self.assertEqual(mod_chefe._DOT_COLOR["1"], core.THEME["success"])
        self.assertEqual(mod_chefe._DOT_COLOR["2"], core.THEME["accent"])
        self.assertEqual(mod_chefe._DOT_COLOR["-1"], core.THEME["error"])


class TestPedidosUsaRenderCard(unittest.TestCase):
    """A lista de Pedidos (aba "📦 Pedidos") passa a usar
    core.render_card()/render_badge() em vez de HTML de cartão próprio."""

    def test_pedido_aparece_com_badge_de_estado(self):
        at = _run()
        self.assertFalse(at.exception, msg=str(at.exception))
        textos = " ".join(m.value for m in at.markdown)
        self.assertIn("gn-card", textos)
        self.assertIn("gn-badge", textos)
        self.assertIn("Chave de fendas", textos)
        self.assertIn("Pendente", textos)

    def test_sem_pedidos_mostra_aviso(self):
        at = _run(req_fer_records=[])
        self.assertFalse(at.exception, msg=str(at.exception))
        self.assertIn("Sem pedidos", " ".join(i.value for i in at.info))


if __name__ == "__main__":
    unittest.main(verbosity=2)

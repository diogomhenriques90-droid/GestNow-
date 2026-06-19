"""
GESTNOW v3 — mod_dashboard_obra.py
Vista de CARDS DE OBRA (estilo Base44) — módulo ISOLADO, SÓ LEITURA.

NÃO ligado ao menu/navegação, NÃO escreve, NÃO toca em nenhum CSV, NÃO cria
colunas, NÃO faz deploy. Recebe os frames de load_all posicionalmente
(mesma assinatura de mod_dashboard.render_dashboard(*args)):
  - idx 1  → obras_lista.csv   (Obra, Cliente, Local, Localizacao, Ativa,
                                DataInicio, DataFim, ...)
  - idx 19 → inst_acessos.csv  (Obra, Utilizador, Ativo, ...)

Campos sem coluna real em obras_lista (Responsável, Valor) entram como
ESPAÇO RESERVADO "—" — honestidade visual, sem inventar dados.
"""
import streamlit as st
import pandas as pd

# ── Tokens de estética (claro, plano, moderno — sem gradientes/néon) ─────────
_TEXT   = "#1F2A44"
_MUTED  = "#5A6478"
_FAINT  = "#9AA3B2"
_BORDER = "#E6E9EF"
_LINE   = "#F2F4F8"

_CSS = f"""
<style>
.dob-title {{ font-size: 1.7rem; font-weight: 700; color: {_TEXT}; margin: 0; }}
.dob-sub {{ font-size: 0.9rem; color: {_MUTED}; margin: 2px 0 0 0; }}
.dob-group {{ font-size: 1.0rem; font-weight: 600; color: {_TEXT};
             margin: 14px 0 10px 0; }}
.ob-card {{ background: #FFFFFF; border: 1px solid {_BORDER}; border-radius: 12px;
           padding: 18px 18px 16px 18px; margin-bottom: 18px;
           box-shadow: 0 1px 3px rgba(16,24,40,0.05); }}
.ob-top {{ display: flex; justify-content: space-between; align-items: flex-start;
          gap: 10px; margin-bottom: 8px; }}
.ob-name {{ font-weight: 700; font-size: 1.05rem; color: {_TEXT}; line-height: 1.3; }}
.ob-loc {{ font-size: 0.82rem; color: {_MUTED}; margin: 2px 0 8px 0;
          display: flex; gap: 6px; align-items: center; }}
.ob-line {{ font-size: 0.86rem; color: {_MUTED}; margin: 5px 0;
           display: flex; gap: 7px; align-items: center; }}
.ob-line .k {{ color: {_FAINT}; }}
.ob-foot {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 14px;
           margin-top: 10px; padding-top: 10px; border-top: 1px solid {_LINE}; }}
.ob-foot .ob-line {{ margin: 0; }}
.badge {{ font-size: 0.72rem; font-weight: 600; padding: 3px 11px;
         border-radius: 999px; white-space: nowrap; }}
.badge.ativa {{ background: #E4F3E9; color: #2F7D4F; }}
.badge.inativa {{ background: #EEF0F3; color: #6B7280; }}
</style>
"""


def _esc(v):
    return (str(v) if v is not None else "").replace("<", "&lt;").replace(">", "&gt;")


def _nz(v):
    """Devolve string limpa ou '' para vazios/NaN."""
    s = "" if v is None else str(v).strip()
    return "" if s.lower() in ("", "nan", "none") else s


def _dur_meses(ini, fim):
    """Duração em meses calculada de DataInicio→DataFim. '—' se faltar fim."""
    d1 = pd.to_datetime(_nz(ini), dayfirst=True, errors="coerce")
    d2 = pd.to_datetime(_nz(fim), dayfirst=True, errors="coerce")
    if pd.isna(d1) or pd.isna(d2):
        return "—"
    m = (d2.year - d1.year) * 12 + (d2.month - d1.month)
    if d2.day < d1.day:
        m -= 1
    m = max(m, 0)
    if m == 0:
        return "< 1 mês"
    return "1 mês" if m == 1 else f"{m} meses"


def _card_html(row, n_colab):
    obra    = _esc(_nz(row.get("Obra", "")) or "(sem nome)")
    cliente = _nz(row.get("Cliente", ""))
    local   = _nz(row.get("Localizacao", "")) or _nz(row.get("Local", ""))
    dini    = _nz(row.get("DataInicio", "")) or "—"
    dur     = _dur_meses(row.get("DataInicio", ""), row.get("DataFim", ""))
    ativa   = _nz(row.get("Ativa", "")).lower() == "ativa"
    estado  = "Ativa" if ativa else "Inativa"
    badge   = "ativa" if ativa else "inativa"

    h = ['<div class="ob-card">']
    h.append(
        f'<div class="ob-top"><span class="ob-name">{obra}</span>'
        f'<span class="badge {badge}">{estado}</span></div>'
    )
    if local:
        h.append(f'<div class="ob-loc">📍 {_esc(local)}</div>')
    h.append(f'<div class="ob-line">🏢 <span class="k">Cliente:</span> {_esc(cliente) or "—"}</div>')
    h.append('<div class="ob-line">👤 <span class="k">Chefe de Equipa:</span> —</div>')
    h.append('<div class="ob-foot">')
    h.append(f'<div class="ob-line">📅 <span class="k">Início:</span> {_esc(dini)}</div>')
    h.append(f'<div class="ob-line">⏱️ <span class="k">Duração:</span> {dur}</div>')
    h.append(f'<div class="ob-line">👥 <span class="k">Colab.:</span> {n_colab}</div>')
    h.append('<div class="ob-line">💰 <span class="k">Valor:</span> —</div>')
    h.append('</div></div>')
    return "".join(h)


def _money(v):
    """Formata €/h ou valor; '—' se vazio/inválido."""
    s = _nz(v)
    if not s:
        return "—"
    try:
        return f"€ {float(s.replace(',', '.')):.2f}".replace(".", ",")
    except Exception:
        return "—"


def _render_detalhe(obra_nome, obras_db, inst_acessos_db, diarias_config_db):
    """Vista de detalhe de uma obra — só leitura. Substitui a grelha."""
    if st.button("← Voltar", key="dob_voltar"):
        st.session_state.pop("dash_obra_detalhe", None)
        st.rerun()

    alvo = str(obra_nome).strip()
    row = None
    if obras_db is not None and not obras_db.empty:
        m = obras_db[obras_db["Obra"].astype(str).str.strip() == alvo]
        if not m.empty:
            row = m.iloc[0]
    if row is None:
        st.warning("Obra não encontrada.")
        return

    ativa   = _nz(row.get("Ativa", "")).lower() == "ativa"
    estado  = "Ativa" if ativa else "Inativa"
    badge   = "ativa" if ativa else "inativa"
    local   = _nz(row.get("Localizacao", "")) or _nz(row.get("Local", ""))
    cliente = _nz(row.get("Cliente", "")) or "—"

    # Cabeçalho
    h = ['<div class="ob-card">']
    h.append(
        f'<div class="ob-top"><span class="ob-name" style="font-size:1.3rem">'
        f'{_esc(_nz(row.get("Obra", "")) or "(sem nome)")}</span>'
        f'<span class="badge {badge}">{estado}</span></div>'
    )
    if local:
        h.append(f'<div class="ob-loc">📍 {_esc(local)}</div>')
    h.append(f'<div class="ob-line">🏢 <span class="k">Cliente:</span> {_esc(cliente)}</div>')
    h.append("</div>")
    st.markdown("".join(h), unsafe_allow_html=True)

    # Datas + duração
    dini = _nz(row.get("DataInicio", "")) or "—"
    dfim = _nz(row.get("DataFim", "")) or "—"
    dur  = _dur_meses(row.get("DataInicio", ""), row.get("DataFim", ""))
    h2 = ['<div class="ob-card">']
    h2.append(f'<div class="ob-line">📅 <span class="k">Início:</span> {_esc(dini)}</div>')
    h2.append(f'<div class="ob-line">🏁 <span class="k">Término:</span> {_esc(dfim)}</div>')
    h2.append(f'<div class="ob-line">⏱️ <span class="k">Duração:</span> {dur}</div>')
    h2.append("</div>")
    st.markdown("".join(h2), unsafe_allow_html=True)

    # Equipa (inst_acessos: Obra == alvo E Ativo == 'Sim') — Função vem de Cargo,
    # NUNCA de join por nome ao usuarios.csv (gerou duplicados no passado).
    st.markdown('<p class="dob-group">Equipa alocada</p>', unsafe_allow_html=True)
    ia = inst_acessos_db if inst_acessos_db is not None else pd.DataFrame()
    if not ia.empty and "Obra" in ia.columns and "Ativo" in ia.columns:
        act = ia[(ia["Obra"].astype(str).str.strip() == alvo)
                 & (ia["Ativo"].astype(str).str.strip() == "Sim")]
    else:
        act = pd.DataFrame()
    st.markdown(
        f'<div class="ob-line"><b style="color:{_TEXT};font-size:1.0rem">{len(act)}</b>'
        f'&nbsp; colaborador(es) ativo(s)</div>', unsafe_allow_html=True,
    )
    if act.empty:
        st.info("Sem colaboradores ativos nesta obra.")
    else:
        linhas = []
        for _, r in act.iterrows():
            linhas.append({
                "Colaborador": _nz(r.get("Utilizador", "")) or "—",
                "Função": _nz(r.get("Cargo", "")) or "—",
                "Data alocação": _nz(r.get("Data_Aloc", "")) or "—",
                "VH Colaborador (€/h)": _money(r.get("PrecoHora", "")),
            })
        df_eq = pd.DataFrame(linhas, columns=[
            "Colaborador", "Função", "Data alocação", "VH Colaborador (€/h)"])
        st.dataframe(df_eq, use_container_width=True, hide_index=True)

    # Diária (valor) — só se existir linha em diarias_config para a obra
    if (diarias_config_db is not None and not diarias_config_db.empty
            and "Obra" in diarias_config_db.columns):
        dd = diarias_config_db[diarias_config_db["Obra"].astype(str).str.strip() == alvo]
        if not dd.empty:
            st.markdown(
                f'<div class="ob-line">🗓️ <span class="k">Diária (valor):</span> '
                f'{_money(dd.iloc[0].get("Valor_Diaria", ""))}</div>',
                unsafe_allow_html=True,
            )


def render_dashboard_obra(*args):
    """Vista de cards de obra — só leitura. Não integrada na navegação."""
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     diarias_config_db, *_) = args

    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Modo DETALHE: substitui a grelha (filtros/pesquisa só na grelha) ────
    if st.session_state.get("dash_obra_detalhe"):
        _render_detalhe(st.session_state["dash_obra_detalhe"],
                        obras_db, inst_acessos_db, diarias_config_db)
        return

    obras = obras_db.copy() if obras_db is not None else pd.DataFrame()
    total = len(obras)

    # ── 1. Cabeçalho ────────────────────────────────────────────────────────
    c_h, c_b = st.columns([6, 1])
    with c_h:
        st.markdown(
            f'<p class="dob-title">Obras</p>'
            f'<p class="dob-sub">{total} obra(s) registada(s)</p>',
            unsafe_allow_html=True,
        )
    with c_b:
        if st.button("↻ Atualizar", use_container_width=True, key="dob_refresh"):
            try:
                from core import inv
                inv("obras_lista.csv"); inv("inst_acessos.csv")
            except Exception:
                pass
            st.rerun()

    if obras.empty:
        st.info("Sem obras para apresentar.")
        return

    # Contagem de colaboradores ativos por obra (inst_acessos, Ativo=Sim)
    n_por_obra = {}
    if inst_acessos_db is not None and not inst_acessos_db.empty and "Ativo" in inst_acessos_db.columns:
        act = inst_acessos_db[inst_acessos_db["Ativo"].astype(str).str.strip() == "Sim"]
        n_por_obra = act.groupby(act["Obra"].astype(str).str.strip()).size().to_dict()

    # ── 2. Filtros: Cliente → Obra (dependente) + Estado ────────────────────
    def _vals(series):
        return sorted({v for v in series.astype(str).map(lambda x: x.strip())
                       if v and v.lower() not in ("nan", "none")})

    def _on_cliente_change():
        # Trocar de cliente reseta a obra (evita seleção órfã de outro cliente).
        st.session_state["dob_obra"] = "—"

    def _on_obra_change():
        # Escolher uma obra vai direto ao detalhe (reutiliza o mecanismo
        # existente). Repõe "—" para não criar loop ao Voltar e permitir
        # reselecionar a mesma obra.
        sel = st.session_state.get("dob_obra")
        if sel and sel != "—":
            st.session_state["dash_obra_detalhe"] = sel
            st.session_state["dob_obra"] = "—"

    clientes = _vals(obras["Cliente"])
    f1, f2, f3 = st.columns([2, 2, 1])
    with f1:
        cliente_f = st.selectbox("Cliente", ["Todos os clientes"] + clientes,
                                 key="dob_cliente", on_change=_on_cliente_change)
    # Lista de obras dependente do cliente selecionado
    obras_cli = obras if cliente_f == "Todos os clientes" else \
        obras[obras["Cliente"].astype(str).str.strip() == cliente_f]
    with f2:
        st.selectbox("Obra", ["—"] + _vals(obras_cli["Obra"]),
                     key="dob_obra", on_change=_on_obra_change)
    with f3:
        estado_f = st.selectbox("Estado", ["Todos", "Ativa", "Inativa"],
                               key="dob_estado")

    # Filtro de cliente aplica-se à grelha; o Estado aplica-se depois.
    df = obras_cli

    def _is_ativa(s):
        return s.astype(str).str.strip().str.lower() == "ativa"

    if estado_f == "Ativa":
        df = df[_is_ativa(df["Ativa"])]
    elif estado_f == "Inativa":
        df = df[~_is_ativa(df["Ativa"])]

    if df.empty:
        st.info("Nenhuma obra corresponde aos filtros.")
        return

    # ── 3. Grelha de cards (3 colunas), agrupada por estado ─────────────────
    def _render_grid(sub):
        sub = sub.sort_values("Obra", key=lambda s: s.astype(str).str.lower())
        cols = st.columns(3, gap="large")
        for i, (_, row) in enumerate(sub.iterrows()):
            obra_nome = str(row.get("Obra", "")).strip()
            n = int(n_por_obra.get(obra_nome, 0))
            with cols[i % 3]:
                st.markdown(_card_html(row, n), unsafe_allow_html=True)
                if st.button("Ver detalhe →", key=f"detalhe_{obra_nome}",
                             use_container_width=True):
                    st.session_state["dash_obra_detalhe"] = obra_nome
                    st.rerun()

    if estado_f == "Todos":
        grupos = [("Ativas", df[_is_ativa(df["Ativa"])]),
                  ("Inativas", df[~_is_ativa(df["Ativa"])])]
        for titulo, sub in grupos:
            if sub.empty:
                continue
            st.markdown(f'<p class="dob-group">{titulo} ({len(sub)})</p>', unsafe_allow_html=True)
            _render_grid(sub)
    else:
        st.markdown(f'<p class="dob-group">{estado_f}s ({len(df)})</p>', unsafe_allow_html=True)
        _render_grid(df)

# mod_admin_orcamentacao.py
"""
GESTNOW v3 — mod_admin_orcamentacao.py
CPS Orçamentação Pro — Módulo Master
Tipo A: Instrumentação (catálogo de tempos + linhas)
Tipo B: Cedência de Mão de Obra (calculadora automática)
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date, timedelta
from core import save_db, inv, load_db, log_audit

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except Exception:
        return pd.DataFrame(columns=cols)


def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()


def _today_str():
    return date.today().strftime("%d/%m/%Y")


def _next_month_str():
    today = date.today()
    if today.month < 12:
        return date(today.year, today.month + 1, today.day).strftime("%d/%m/%Y")
    return date(today.year + 1, 1, today.day).strftime("%d/%m/%Y")


def _days_until(validade_str):
    try:
        d = datetime.strptime(validade_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except Exception:
        return 999


def _score_orc(orc, clientes_db, orc_db):
    """Score de probabilidade 0-100 baseado em regras de negócio."""
    score = 50
    cliente = orc.get('Cliente', '')
    margem = float(orc.get('Margem_Pct', 20) or 20)
    validade = orc.get('Validade', '')
    status = orc.get('Status', '')

    # Cliente já adjudicou antes?
    if not clientes_db.empty and 'Cliente' in clientes_db.columns:
        hist = clientes_db[clientes_db['Cliente'] == cliente]
        if not hist.empty:
            adjudicados = len(hist[hist.get('Status', '') == 'Adjudicado']) if 'Status' in hist.columns else 0
            score += min(adjudicados * 8, 20)

    # Histórico de adjudicações deste cliente neste app
    if not orc_db.empty:
        prev = orc_db[(orc_db['Cliente'] == cliente) & (orc_db['Status'] == 'Adjudicado')]
        score += min(len(prev) * 5, 15)

    # Margem penaliza (preço mais alto)
    if margem > 30:
        score -= 15
    elif margem > 25:
        score -= 8
    elif margem < 15:
        score += 5

    # Validade
    days = _days_until(validade)
    if days < 0:
        score -= 30
    elif days < 7:
        score -= 15
    elif days < 15:
        score -= 8

    # Em revisão / negociação
    if status == 'Em Revisão':
        score += 10
    elif status == 'Enviado':
        score += 5

    return max(0, min(100, score))


def _score_badge(score):
    if score >= 65:
        return "🟢", "#10B981", "Alta"
    elif score >= 40:
        return "🟡", "#F59E0B", "Média"
    else:
        return "🔴", "#EF4444", "Baixa"


def _historico_item(item_desc, orc_linhas_db, orc_db):
    """Devolve últimas 3 ocorrências de um item no histórico."""
    if orc_linhas_db.empty or orc_db.empty:
        return []
    matches = orc_linhas_db[
        orc_linhas_db['Descricao'].str.contains(item_desc, case=False, na=False)
    ].head(10)
    resultados = []
    for _, row in matches.iterrows():
        oid = row.get('Orcamento_ID', '')
        orc_match = orc_db[orc_db['ID'] == oid]
        if not orc_match.empty:
            o = orc_match.iloc[0]
            resultados.append({
                'obra': o.get('Obra', ''),
                'data': o.get('Data', ''),
                'preco': float(row.get('Preco_Unit', 0) or 0),
                'unidade': row.get('Unidade', 'un'),
            })
        if len(resultados) >= 3:
            break
    return resultados


# ─────────────────────────────────────────────────────────────
# CSS INJECTADO
# ─────────────────────────────────────────────────────────────

def _inject_css():
    st.markdown("""
    <style>
    /* Pipeline Kanban cards */
    .orc-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
        transition: border-color 0.2s;
    }
    .orc-card:hover { border-color: #3B82F6; }
    .orc-card-title {
        color: #F1F5F9;
        font-weight: 700;
        font-size: 0.95rem;
        margin: 0 0 4px 0;
    }
    .orc-card-sub {
        color: #64748B;
        font-size: 0.78rem;
        margin: 2px 0;
    }
    .orc-card-valor {
        color: #3B82F6;
        font-weight: 700;
        font-size: 1.1rem;
        margin-top: 6px;
    }
    /* Estado badge */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    /* Alerta validade */
    .alerta-exp {
        background: rgba(239,68,68,0.12);
        border: 1px solid #EF4444;
        border-radius: 8px;
        padding: 8px 14px;
        color: #FCA5A5;
        font-size: 0.82rem;
        margin-bottom: 6px;
    }
    .alerta-warn {
        background: rgba(245,158,11,0.12);
        border: 1px solid #F59E0B;
        border-radius: 8px;
        padding: 8px 14px;
        color: #FCD34D;
        font-size: 0.82rem;
        margin-bottom: 6px;
    }
    /* Calculadora Tipo B */
    .calc-box {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
    }
    .calc-total {
        background: rgba(59,130,246,0.1);
        border: 2px solid #3B82F6;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .hist-box {
        background: rgba(59,130,246,0.06);
        border-left: 3px solid #3B82F6;
        border-radius: 0 8px 8px 0;
        padding: 8px 12px;
        font-size: 0.78rem;
        color: #94A3B8;
        margin-top: 6px;
    }
    /* KPI mini */
    .kpi-mini {
        background: #1E293B;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
    }
    .kpi-mini-val {
        font-size: 1.6rem;
        font-weight: 800;
        color: #F1F5F9;
        line-height: 1.1;
    }
    .kpi-mini-label {
        font-size: 0.75rem;
        color: #64748B;
        margin-top: 2px;
    }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# CARREGAR DADOS
# ─────────────────────────────────────────────────────────────

def _carregar_dados():
    orc_db = _load("orcamentos.csv", [
        "ID", "Obra", "Cliente", "Tipo", "Versao", "Data", "Criado_Por",
        "Status", "Validade", "Total_Mao_Obra", "Total_Materiais",
        "Total_Equipamentos", "Total_Deslocacoes", "Total_Dormidas",
        "Total_Diarias", "Margem_Pct", "Total_Sem_Margem",
        "Total_Com_Margem", "Motivo_Rejeicao", "Notas", "Versao_Pai", "Oportunidade_ID"
    ])
    orc_linhas = _load("orcamentos_linhas.csv", [
        "ID", "Orcamento_ID", "Descricao", "Categoria",
        "Quantidade", "Unidade", "Minutos_Unit", "Preco_Unit", "Total", "Notas"
    ])
    obras_db = _load("obras_lista.csv", ["Obra", "Cliente", "Ativa", "Tipo", "Localizacao"])
    catalogo = _load("orc_catalogo.csv", [
        "ID", "Categoria", "Descricao", "Unidade", "Minutos_Unit",
        "Preco_Sugerido", "Vezes_Usado", "Activo", "Data_Actualizacao"
    ])
    tarifas = _load("orc_tarifas.csv", [
        "ID", "Categoria", "Zona", "Valor_Hora", "Horas_Dia",
        "Diaria", "Data_Actualizacao"
    ])
    ref_precos = _load("orc_ref_precos.csv", [
        "ID", "Tipo", "Descricao", "Valor_Dia", "Capacidade",
        "Fonte", "Data_Actualizacao"
    ])
    clientes_db = _load("orc_clientes.csv", [
        "ID", "Cliente", "Contacto", "Email", "Telefone",
        "Setor", "Pais", "Notas"
    ])
    return orc_db, orc_linhas, obras_db, catalogo, tarifas, ref_precos, clientes_db


# ─────────────────────────────────────────────────────────────
# TAB 1 — COCKPIT
# ─────────────────────────────────────────────────────────────

def _tab_cockpit(orc_db, clientes_db):
    if orc_db.empty:
        st.info("📋 Sem orçamentos. Cria o primeiro no tab ➕ Novo Orçamento.")
        return

    today = date.today()

    # ── KPIs principais ──────────────────────────────────────
    ativos   = orc_db[orc_db['Status'].isin(['Rascunho', 'Enviado', 'Em Revisão'])]
    enviados = orc_db[orc_db['Status'] == 'Enviado']
    adj      = orc_db[orc_db['Status'] == 'Adjudicado']
    total_pipeline = _num(enviados, 'Total_Com_Margem')
    total_ganho    = _num(adj, 'Total_Com_Margem')
    taxa_conv = round(len(adj) / max(len(orc_db[orc_db['Status'].isin(
        ['Adjudicado', 'Rejeitado'])]), 1) * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='kpi-mini'>
            <div class='kpi-mini-val'>{len(ativos)}</div>
            <div class='kpi-mini-label'>🔄 Em Pipeline</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='kpi-mini'>
            <div class='kpi-mini-val'>€{total_pipeline:,.0f}</div>
            <div class='kpi-mini-label'>💰 Valor Enviado</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='kpi-mini'>
            <div class='kpi-mini-val' style='color:#10B981'>{taxa_conv}%</div>
            <div class='kpi-mini-label'>✅ Taxa Conversão</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class='kpi-mini'>
            <div class='kpi-mini-val' style='color:#10B981'>€{total_ganho:,.0f}</div>
            <div class='kpi-mini-label'>🏆 Total Ganho</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Alertas de validade ──────────────────────────────────
    alertas = []
    for _, row in enviados.iterrows():
        days = _days_until(row.get('Validade', ''))
        if days < 0:
            alertas.append(('exp', row, days))
        elif days <= 15:
            alertas.append(('warn', row, days))

    if alertas:
        st.markdown("#### ⚠️ Alertas de Validade")
        for tipo, row, days in sorted(alertas, key=lambda x: x[2]):
            total = float(row.get('Total_Com_Margem', 0) or 0)
            if tipo == 'exp':
                st.markdown(
                    f"<div class='alerta-exp'>🔴 <b>{row.get('Obra','')} — {row.get('Cliente','')}</b> "
                    f"| Expirou há {abs(days)} dias | €{total:,.2f}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='alerta-warn'>🟡 <b>{row.get('Obra','')} — {row.get('Cliente','')}</b> "
                    f"| Expira em {days} dias | €{total:,.2f}</div>",
                    unsafe_allow_html=True
                )
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Kanban visual ────────────────────────────────────────
    st.markdown("#### 📊 Pipeline por Estado")

    estados = [
        ('Rascunho',   '#6B7280', '📝'),
        ('Enviado',    '#3B82F6', '📤'),
        ('Em Revisão', '#8B5CF6', '🔍'),
        ('Adjudicado', '#10B981', '✅'),
        ('Rejeitado',  '#EF4444', '❌'),
    ]

    cols = st.columns(len(estados))
    for col, (estado, cor, icon) in zip(cols, estados):
        grupo = orc_db[orc_db['Status'] == estado]
        val   = _num(grupo, 'Total_Com_Margem')
        with col:
            st.markdown(
                f"<div style='border-top:3px solid {cor};padding-top:8px;'>"
                f"<div style='color:{cor};font-weight:700;font-size:0.85rem;'>"
                f"{icon} {estado}</div>"
                f"<div style='color:#94A3B8;font-size:0.75rem;'>"
                f"{len(grupo)} orç. | €{val:,.0f}</div></div>",
                unsafe_allow_html=True
            )
            for _, orc in grupo.sort_values('Data', ascending=False).head(4).iterrows():
                total  = float(orc.get('Total_Com_Margem', 0) or 0)
                score  = _score_orc(orc, clientes_db, orc_db)
                icon_s, cor_s, label_s = _score_badge(score)
                days   = _days_until(orc.get('Validade', ''))
                val_str = f"⏰ {days}d" if 0 <= days <= 30 else (
                    "🔴 Expirado" if days < 0 else "")
                st.markdown(
                    f"<div class='orc-card'>"
                    f"<p class='orc-card-title'>{orc.get('Obra','')}</p>"
                    f"<p class='orc-card-sub'>{orc.get('Cliente','')} · "
                    f"v{orc.get('Versao','1')} · {orc.get('Tipo','A')}</p>"
                    f"<p class='orc-card-sub'>{icon_s} {label_s} · {val_str}</p>"
                    f"<p class='orc-card-valor'>€{total:,.0f}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )


# ─────────────────────────────────────────────────────────────
# TAB 2 — LISTA + GESTÃO
# ─────────────────────────────────────────────────────────────

def _tab_lista(orc_db, orc_linhas, clientes_db):
    if orc_db.empty:
        st.info("📋 Sem orçamentos.")
        return

    # Filtros
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        status_opts = ["Todos"] + sorted(orc_db['Status'].dropna().unique().tolist())
        stat_f = st.selectbox("Estado", status_opts, key="orc_list_stat")
    with col_f2:
        obras_opts = ["Todas"] + sorted(orc_db['Obra'].dropna().unique().tolist())
        obra_f = st.selectbox("Obra", obras_opts, key="orc_list_obra")
    with col_f3:
        tipo_opts = ["Todos", "A - Instrumentação", "B - Cedência MO"]
        tipo_f = st.selectbox("Tipo", tipo_opts, key="orc_list_tipo")
    with col_f4:
        pesq = st.text_input("🔍 Pesquisar cliente/obra", key="orc_list_pesq")

    df_o = orc_db.copy()
    if stat_f != "Todos":
        df_o = df_o[df_o['Status'] == stat_f]
    if obra_f != "Todas":
        df_o = df_o[df_o['Obra'] == obra_f]
    if tipo_f == "A - Instrumentação":
        df_o = df_o[df_o.get('Tipo', 'A') != 'B']
    elif tipo_f == "B - Cedência MO":
        df_o = df_o[df_o.get('Tipo', 'A') == 'B']
    if pesq:
        mask = (
            df_o['Obra'].str.contains(pesq, case=False, na=False) |
            df_o['Cliente'].str.contains(pesq, case=False, na=False)
        )
        df_o = df_o[mask]

    st.markdown(f"**{len(df_o)} orçamento(s)**")

    ESTADOS = ['Rascunho', 'Enviado', 'Em Revisão', 'Adjudicado', 'Rejeitado']
    COR_EST = {
        'Rascunho':   '#6B7280',
        'Enviado':    '#3B82F6',
        'Em Revisão': '#8B5CF6',
        'Adjudicado': '#10B981',
        'Rejeitado':  '#EF4444',
    }
    MOTIVOS = ['Preço acima do mercado', 'Prazo não adequado',
               'Concorrência', 'Sem resposta do cliente',
               'Projecto cancelado', 'Outro']

    for _, orc in df_o.sort_values('Data', ascending=False).iterrows():
        oid   = orc.get('ID', '')
        stat  = orc.get('Status', 'Rascunho')
        total = float(orc.get('Total_Com_Margem', 0) or 0)
        cor   = COR_EST.get(stat, '#6B7280')
        tipo  = orc.get('Tipo', 'A')
        score = _score_orc(orc, clientes_db, orc_db)
        icon_s, cor_s, label_s = _score_badge(score)
        days  = _days_until(orc.get('Validade', ''))
        val_badge = (f" · ⏰ {days}d" if 0 < days <= 30 else
                     (" · 🔴 Expirado" if days <= 0 else ""))

        label_tipo = "🔧 Tipo A" if tipo != 'B' else "👷 Tipo B"

        with st.expander(
            f"{label_tipo} | {orc.get('Obra','')} — v{orc.get('Versao','1')} "
            f"| {orc.get('Cliente','')} | €{total:,.2f} | {stat}{val_badge}",
            expanded=False
        ):
            col_l, col_r = st.columns([2, 1])

            with col_l:
                st.markdown(
                    f"<div style='background:#1E293B;border-radius:8px;padding:12px;'>"
                    f"<p style='color:#F1F5F9;margin:2px 0;'>"
                    f"<b>Cliente:</b> {orc.get('Cliente','')} &nbsp;|&nbsp; "
                    f"<b>Data:</b> {orc.get('Data','')} &nbsp;|&nbsp; "
                    f"<b>Validade:</b> {orc.get('Validade','')}</p>"
                    f"<p style='color:#F1F5F9;margin:2px 0;'>"
                    f"<b>Margem:</b> {orc.get('Margem_Pct',0)}% &nbsp;|&nbsp; "
                    f"<b>Criado por:</b> {orc.get('Criado_Por','')}</p>"
                    f"<p style='color:#94A3B8;margin:4px 0;font-size:0.82rem;'>"
                    f"{orc.get('Notas','')}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                # Linhas (só Tipo A)
                if tipo != 'B' and not orc_linhas.empty:
                    linhas = orc_linhas[orc_linhas['Orcamento_ID'] == oid]
                    if not linhas.empty:
                        st.markdown("**Linhas:**")
                        cols_show = [c for c in [
                            'Descricao', 'Categoria', 'Quantidade',
                            'Unidade', 'Preco_Unit', 'Total'
                        ] if c in linhas.columns]
                        st.dataframe(linhas[cols_show],
                                     use_container_width=True, hide_index=True)
                        horas = pd.to_numeric(
                            linhas.get('Minutos_Unit', pd.Series([0])), errors='coerce'
                        ).fillna(0).sum() / 60
                        if horas > 0:
                            st.caption(f"⏱️ Total estimado: **{horas:.1f} horas**")

            with col_r:
                st.markdown(
                    f"<div class='calc-total' style='margin-bottom:10px;'>"
                    f"<div style='color:{cor};font-size:1.5rem;font-weight:800;'>"
                    f"€{total:,.2f}</div>"
                    f"<div style='color:#64748B;font-size:0.75rem;'>{stat}</div>"
                    f"<div style='margin-top:6px;font-size:0.8rem;color:{cor_s};'>"
                    f"{icon_s} Prob. {label_s}: {score}%</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                # Breakdown custos
                breakdown = [
                    ("Mão de Obra", 'Total_Mao_Obra'),
                    ("Materiais",   'Total_Materiais'),
                    ("Equip.",      'Total_Equipamentos'),
                    ("Deslocações", 'Total_Deslocacoes'),
                    ("Dormidas",    'Total_Dormidas'),
                    ("Diárias",     'Total_Diarias'),
                ]
                html_bd = "<div style='background:#1E293B;border-radius:8px;padding:10px;font-size:0.8rem;'>"
                for label_b, col_b in breakdown:
                    val_b = float(orc.get(col_b, 0) or 0)
                    if val_b > 0:
                        html_bd += (f"<p style='color:#64748B;margin:2px 0;'>"
                                    f"{label_b}: €{val_b:,.2f}</p>")
                html_bd += "</div>"
                st.markdown(html_bd, unsafe_allow_html=True)

                # Alterar estado
                idx_stat = ESTADOS.index(stat) if stat in ESTADOS else 0
                novo_stat = st.selectbox(
                    "Alterar estado",
                    ESTADOS,
                    index=idx_stat,
                    key=f"orc_st_{oid}"
                )

                # Motivo rejeição
                if novo_stat == 'Rejeitado':
                    motivo = st.selectbox(
                        "Motivo rejeição",
                        MOTIVOS,
                        key=f"orc_mot_{oid}"
                    )
                else:
                    motivo = orc.get('Motivo_Rejeicao', '')

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("✅ Actualizar", key=f"orc_upd_{oid}",
                                 use_container_width=True, type="primary"):
                        orc_db.loc[orc_db['ID'] == oid, 'Status'] = novo_stat
                        if motivo:
                            orc_db.loc[orc_db['ID'] == oid, 'Motivo_Rejeicao'] = motivo
                        save_db(orc_db, "orcamentos.csv")
                        inv("orcamentos.csv")
                        st.success("✅ Estado actualizado!")
                        st.rerun()

                with col_b2:
                    if st.button("📋 Duplicar", key=f"orc_dup_{oid}",
                                 use_container_width=True):
                        st.session_state['duplicar_orc_id'] = oid
                        st.info("💡 Abre o tab ➕ Novo — o orçamento foi pré-carregado.")

                # Adjudicação → Criar Obra
                if novo_stat == 'Adjudicado' or stat == 'Adjudicado':
                    st.markdown("---")
                    if st.button("🏗️ Criar Obra a partir deste orçamento",
                                 key=f"orc_obra_{oid}",
                                 use_container_width=True,
                                 type="primary"):
                        st.session_state[f'criar_obra_orc_{oid}'] = True

                    if st.session_state.get(f'criar_obra_orc_{oid}', False):
                        _modal_criar_obra(orc, oid, orc_db)


def _modal_criar_obra(orc, oid, orc_db):
    """Modal de validação para criar obra a partir do orçamento adjudicado."""
    st.markdown(
        "<div style='background:rgba(16,185,129,0.08);border:1px solid #10B981;"
        "border-radius:10px;padding:16px;margin-top:8px;'>",
        unsafe_allow_html=True
    )
    st.markdown("#### 🏗️ Validar e Criar Obra")
    st.caption("Confirma os dados antes de criar a obra.")

    co1, co2 = st.columns(2)
    with co1:
        obra_nome = st.text_input(
            "Nome da Obra *",
            value=orc.get('Obra', ''),
            key=f"cr_nome_{oid}"
        )
        obra_cliente = st.text_input(
            "Cliente *",
            value=orc.get('Cliente', ''),
            key=f"cr_cliente_{oid}"
        )
        obra_tipo = st.selectbox(
            "Tipo",
            ["Normal", "Shutdown", "Turnkey", "Cedência MO"],
            key=f"cr_tipo_{oid}"
        )
    with co2:
        obra_local = st.text_input(
            "Localização",
            key=f"cr_local_{oid}"
        )
        obra_codigo = st.text_input(
            "Código Obra",
            value=f"ORC-{oid}",
            key=f"cr_cod_{oid}"
        )

    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button("✅ Confirmar e Criar Obra",
                     key=f"cr_confirm_{oid}",
                     type="primary",
                     use_container_width=True):
            if not obra_nome or not obra_cliente:
                st.error("Nome e cliente obrigatórios.")
            else:
                obras_db = _load("obras_lista.csv",
                                 ["Obra", "Cliente", "Ativa", "Tipo",
                                  "Localizacao", "Codigo", "Orcamento_ID"])
                nova_obra = pd.DataFrame([{
                    "Obra":          obra_nome,
                    "Cliente":       obra_cliente,
                    "Ativa":         "Ativa",
                    "Tipo":          obra_tipo,
                    "Localizacao":   obra_local,
                    "Codigo":        obra_codigo,
                    "Orcamento_ID":  oid,
                }])
                upd = pd.concat([obras_db, nova_obra],
                                ignore_index=True) if not obras_db.empty else nova_obra
                save_db(upd, "obras_lista.csv")
                inv("obras_lista.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                # Ligar orçamento à obra
                orc_db.loc[orc_db['ID'] == oid, 'Status'] = 'Adjudicado'
                save_db(orc_db, "orcamentos.csv")
                inv("orcamentos.csv")
                log_audit(
                    usuario=st.session_state.get('user', 'Admin'),
                    acao="CRIAR_OBRA_ORC",
                    tabela="obras_lista.csv",
                    registro_id=oid,
                    detalhes=f"Obra '{obra_nome}' criada a partir do orçamento {oid}",
                    ip=""
                )
                st.success(f"✅ Obra '{obra_nome}' criada com sucesso!")
                st.session_state[f'criar_obra_orc_{oid}'] = False
                st.rerun()

    with col_cancel:
        if st.button("✖ Cancelar", key=f"cr_cancel_{oid}",
                     use_container_width=True):
            st.session_state[f'criar_obra_orc_{oid}'] = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TAB 3 — NOVO ORÇAMENTO (Tipo A + Tipo B)
# ─────────────────────────────────────────────────────────────

def _tab_novo(orc_db, orc_linhas, obras_db, catalogo, tarifas, ref_precos):
    user_nome = st.session_state.get('user', 'Admin')

    # Verificar se vem de duplicar
    orc_base = None
    dup_id = st.session_state.pop('duplicar_orc_id', None)
    if dup_id and not orc_db.empty:
        matches = orc_db[orc_db['ID'] == dup_id]
        if not matches.empty:
            orc_base = matches.iloc[0].to_dict()
            st.info(f"📋 A duplicar orçamento de: **{orc_base.get('Obra','')}** "
                    f"(v{orc_base.get('Versao','1')})")

    # Tipo de orçamento
    tipo_orc = st.radio(
        "Tipo de Orçamento",
        ["🔧 Tipo A — Instrumentação / Projecto",
         "👷 Tipo B — Cedência de Mão de Obra"],
        horizontal=True,
        key="novo_tipo_orc"
    )
    is_tipo_b = "Tipo B" in tipo_orc

    st.divider()

    _op_db = _load("comercial_oportunidades.csv", [
        "ID", "Nome", "Cliente", "Stage",
    ])
    _op_ativos = _op_db[
        _op_db["Stage"].isin(
            ["prospeto","contactado","reuniao","proposta","negociacao"]
        )
    ].copy() if not _op_db.empty else _op_db

    if is_tipo_b:
        _form_tipo_b(orc_db, obras_db, tarifas, ref_precos, user_nome, orc_base,
                     _op_ativos)
    else:
        _form_tipo_a(orc_db, orc_linhas, obras_db, catalogo, user_nome, orc_base,
                     _op_ativos)


# ── Tipo A ───────────────────────────────────────────────────

def _form_tipo_a(orc_db, orc_linhas, obras_db, catalogo, user_nome, orc_base, op_db=None):
    obras_ativas = (obras_db[obras_db['Ativa'] == 'Ativa']['Obra'].tolist()
                    if not obras_db.empty else [])

    col1, col2 = st.columns(2)
    with col1:
        obra_default = orc_base.get('Obra', '') if orc_base else None
        opcoes_obra = obras_ativas if obras_ativas else ["—"]
        idx_obra = (opcoes_obra.index(obra_default)
                    if obra_default in opcoes_obra else 0)
        no_obra = st.selectbox("Obra *", opcoes_obra,
                               index=idx_obra, key="noa_obra")

        cliente_auto = ""
        if not obras_db.empty and 'Cliente' in obras_db.columns:
            m = obras_db[obras_db['Obra'] == no_obra]
            if not m.empty:
                cliente_auto = m.iloc[0].get('Cliente', '')
        no_cliente = st.text_input(
            "Cliente *",
            value=orc_base.get('Cliente', cliente_auto) if orc_base else cliente_auto,
            key="noa_cliente"
        )
        no_versao = st.number_input(
            "Versão", min_value=1,
            value=int(orc_base.get('Versao', 1)) + 1 if orc_base else 1,
            key="noa_versao"
        )
        no_validade = st.text_input(
            "Validade (dd/mm/aaaa)",
            value=_next_month_str(),
            key="noa_validade"
        )

    with col2:
        no_margem = st.slider(
            "Margem (%)", 0, 50,
            int(orc_base.get('Margem_Pct', 20)) if orc_base else 20,
            key="noa_margem"
        )
        # Aviso margem baixa
        if no_margem < 15:
            st.warning("⚠️ Margem abaixo de 15% — confirma se é intencional.")
        elif no_margem > 35:
            st.warning("⚠️ Margem acima de 35% — pode reduzir competitividade.")

        no_notas = st.text_area(
            "Notas",
            value=orc_base.get('Notas', '') if orc_base else '',
            key="noa_notas"
        )

        _op_opts_a = ["— Nenhuma —"]
        if op_db is not None and not op_db.empty:
            _op_opts_a += [
                f"{r['ID']} — {r['Nome']} ({r['Cliente']})"
                for _, r in op_db.iterrows()
            ]
        no_op_id_raw = st.selectbox(
            "🔗 Oportunidade de Origem (ISO)",
            _op_opts_a, key="noa_op_id",
            help="Liga este orçamento à oportunidade comercial"
        )

    st.markdown("---")
    st.markdown("#### 📝 Linhas do Orçamento")

    # Inicializar linhas temp
    if 'orc_linhas_temp' not in st.session_state:
        st.session_state['orc_linhas_temp'] = []
        # Se duplicar, pré-carregar linhas
        if orc_base and not orc_linhas.empty:
            linhas_orig = orc_linhas[
                orc_linhas['Orcamento_ID'] == orc_base.get('ID', '')
            ]
            for _, l in linhas_orig.iterrows():
                st.session_state['orc_linhas_temp'].append({
                    "ID":          str(uuid.uuid4())[:6].upper(),
                    "Descricao":   l.get('Descricao', ''),
                    "Categoria":   l.get('Categoria', ''),
                    "Quantidade":  float(l.get('Quantidade', 1)),
                    "Unidade":     l.get('Unidade', 'un'),
                    "Minutos_Unit":float(l.get('Minutos_Unit', 0)),
                    "Preco_Unit":  float(l.get('Preco_Unit', 0)),
                    "Total":       float(l.get('Total', 0)),
                    "Notas":       l.get('Notas', ''),
                })

    # Pesquisa no catálogo
    if not catalogo.empty:
        cat_activo = catalogo[catalogo.get('Activo', 'Sim') != 'Não']
        col_cat1, col_cat2 = st.columns([3, 1])
        with col_cat1:
            pesq_cat = st.text_input(
                "🔍 Pesquisar no catálogo de tempos",
                key="noa_pesq_cat",
                placeholder="Ex: transmissor, passagem cabo, comissionamento..."
            )
        with col_cat2:
            cat_cat = st.selectbox(
                "Categoria",
                ["Todas"] + sorted(cat_activo['Categoria'].dropna().unique().tolist()),
                key="noa_cat_cat"
            )

        if pesq_cat or cat_cat != "Todas":
            df_cat = cat_activo.copy()
            if pesq_cat:
                df_cat = df_cat[
                    df_cat['Descricao'].str.contains(pesq_cat, case=False, na=False)
                ]
            if cat_cat != "Todas":
                df_cat = df_cat[df_cat['Categoria'] == cat_cat]

            if not df_cat.empty:
                for _, item in df_cat.head(8).iterrows():
                    preco_s = float(item.get('Preco_Sugerido', 0) or 0)
                    mins    = float(item.get('Minutos_Unit', 0) or 0)
                    usos    = int(item.get('Vezes_Usado', 0) or 0)

                    # Histórico de preços
                    hist = _historico_item(
                        item.get('Descricao', ''), orc_linhas, orc_db
                    )
                    hist_html = ""
                    if hist:
                        precos = [h['preco'] for h in hist]
                        media  = sum(precos) / len(precos)
                        hist_html = (
                            f"<div class='hist-box'>"
                            f"📊 Média histórica: €{media:.2f}/{item.get('Unidade','un')} "
                            f"· Última vez: {hist[0]['obra']} ({hist[0]['data']})"
                            f"</div>"
                        )

                    col_i1, col_i2, col_i3, col_i4 = st.columns([3, 1, 1, 1])
                    with col_i1:
                        st.markdown(
                            f"<div style='padding:6px 0;'>"
                            f"<span style='color:#F1F5F9;font-size:0.88rem;'>"
                            f"<b>{item.get('Descricao','')}</b></span>"
                            f"<span style='color:#64748B;font-size:0.76rem;'> · "
                            f"{item.get('Categoria','')} · {mins:.0f}min/{item.get('Unidade','un')} "
                            f"· usado {usos}×</span>"
                            f"{hist_html}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with col_i2:
                        qtd_i = st.number_input(
                            "Qtd", min_value=0.0, value=1.0, step=0.5,
                            key=f"cat_qtd_{item.get('ID','')}"
                        )
                    with col_i3:
                        preco_i = st.number_input(
                            "€/un", min_value=0.0, value=preco_s, step=0.5,
                            key=f"cat_preco_{item.get('ID','')}"
                        )
                    with col_i4:
                        if st.button("➕", key=f"cat_add_{item.get('ID','')}"):
                            st.session_state['orc_linhas_temp'].append({
                                "ID":          str(uuid.uuid4())[:6].upper(),
                                "Descricao":   item.get('Descricao', ''),
                                "Categoria":   item.get('Categoria', ''),
                                "Quantidade":  qtd_i,
                                "Unidade":     item.get('Unidade', 'un'),
                                "Minutos_Unit":mins * qtd_i,
                                "Preco_Unit":  preco_i,
                                "Total":       round(qtd_i * preco_i, 2),
                                "Notas":       "",
                            })
                            # Incrementar contador de uso no catálogo
                            if not catalogo.empty and 'ID' in catalogo.columns:
                                catalogo.loc[
                                    catalogo['ID'] == item.get('ID', ''),
                                    'Vezes_Usado'
                                ] = usos + 1
                                save_db(catalogo, "orc_catalogo.csv")
                            st.rerun()
            else:
                st.caption("Sem resultados no catálogo.")

    st.markdown("---")

    # Adicionar linha manual
    with st.expander("➕ Adicionar linha manual", expanded=False):
        with st.form("form_linha_manual"):
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                m_desc = st.text_input("Descrição *", key="m_desc")
                m_cat  = st.selectbox(
                    "Categoria",
                    ["Mão de Obra", "Materiais", "Equipamentos",
                     "Deslocações", "Subempreitada", "Comissionamento", "Outro"],
                    key="m_cat"
                )
            with col_m2:
                m_qtd  = st.number_input("Quantidade", min_value=0.0,
                                         value=1.0, step=0.5, key="m_qtd")
                m_uni  = st.selectbox(
                    "Unidade",
                    ["h", "un", "m", "m²", "m³", "kg", "L", "vg", "mês", "dia"],
                    key="m_uni"
                )
                m_mins = st.number_input(
                    "Minutos/unidade (opcional)", min_value=0.0,
                    value=0.0, step=1.0, key="m_mins"
                )
            with col_m3:
                m_preco = st.number_input("Preço Unit. (€)", min_value=0.0,
                                          step=1.0, key="m_preco")
                m_notas = st.text_input("Notas", key="m_notas")

            if st.form_submit_button("➕ Adicionar"):
                if m_desc.strip():
                    st.session_state['orc_linhas_temp'].append({
                        "ID":          str(uuid.uuid4())[:6].upper(),
                        "Descricao":   m_desc.strip(),
                        "Categoria":   m_cat,
                        "Quantidade":  m_qtd,
                        "Unidade":     m_uni,
                        "Minutos_Unit":m_mins * m_qtd,
                        "Preco_Unit":  m_preco,
                        "Total":       round(m_qtd * m_preco, 2),
                        "Notas":       m_notas.strip(),
                    })
                    st.rerun()

    # Preview e totais
    if st.session_state['orc_linhas_temp']:
        df_temp = pd.DataFrame(st.session_state['orc_linhas_temp'])

        # Tabela com botão remover
        st.markdown("**Linhas adicionadas:**")
        for i, lin in enumerate(st.session_state['orc_linhas_temp']):
            col_l1, col_l2, col_l3, col_l4, col_l5 = st.columns([3, 1, 1, 1, 0.5])
            with col_l1:
                st.caption(f"**{lin['Descricao']}** · {lin['Categoria']}")
            with col_l2:
                st.caption(f"{lin['Quantidade']} {lin['Unidade']}")
            with col_l3:
                st.caption(f"€{lin['Preco_Unit']:.2f}/un")
            with col_l4:
                st.caption(f"**€{lin['Total']:.2f}**")
            with col_l5:
                if st.button("🗑", key=f"rm_lin_{i}"):
                    st.session_state['orc_linhas_temp'].pop(i)
                    st.rerun()

        # Totais por categoria
        cats_totais = df_temp.groupby('Categoria')['Total'].sum()
        total_sem   = df_temp['Total'].sum()
        total_com   = round(total_sem * (1 + no_margem / 100), 2)
        total_horas = df_temp['Minutos_Unit'].sum() / 60 if 'Minutos_Unit' in df_temp else 0

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            html_cats = "<div style='background:#1E293B;border-radius:10px;padding:14px;'>"
            for cat, val in cats_totais.items():
                html_cats += (f"<p style='color:#94A3B8;margin:3px 0;font-size:0.85rem;'>"
                              f"{cat}: €{val:,.2f}</p>")
            if total_horas > 0:
                html_cats += (f"<p style='color:#F59E0B;margin:6px 0 3px;font-size:0.85rem;'>"
                              f"⏱️ Horas estimadas: <b>{total_horas:.1f}h</b></p>")
            html_cats += "</div>"
            st.markdown(html_cats, unsafe_allow_html=True)

        with col_t2:
            st.markdown(
                f"<div class='calc-total'>"
                f"<p style='color:#64748B;margin:0;font-size:0.85rem;'>"
                f"Sem margem: €{total_sem:,.2f}</p>"
                f"<div style='color:#3B82F6;font-size:1.8rem;font-weight:800;'>"
                f"€{total_com:,.2f}</div>"
                f"<p style='color:#64748B;margin:0;font-size:0.8rem;'>"
                f"Com margem {no_margem}%</p>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 Guardar Orçamento", type="primary",
                         use_container_width=True, key="btn_save_a"):
                if not no_obra or no_obra == "—":
                    st.error("❌ Selecciona uma obra.")
                else:
                    _no_op_id = (
                        no_op_id_raw.split(" — ")[0].strip()
                        if no_op_id_raw != "— Nenhuma —" else ""
                    )
                    _guardar_orcamento_a(
                        orc_db, orc_linhas,
                        no_obra, no_cliente, no_versao, no_validade,
                        no_margem, no_notas, total_sem, total_com,
                        cats_totais, user_nome,
                        orc_base.get('ID') if orc_base else None,
                        _no_op_id
                    )
        with col_s2:
            if st.button("🗑️ Limpar Linhas", use_container_width=True,
                         key="btn_clear_a"):
                st.session_state['orc_linhas_temp'] = []
                st.rerun()
    else:
        st.info("📝 Sem linhas. Pesquisa no catálogo ou adiciona manualmente.")


def _guardar_orcamento_a(orc_db, orc_linhas, obra, cliente, versao, validade,
                          margem, notas, total_sem, total_com,
                          cats_totais, user_nome, versao_pai_id,
                          oportunidade_id=""):
    from core import _cached_load_all
    orc_id = str(uuid.uuid4())[:8].upper()
    novo = pd.DataFrame([{
        "ID":                   orc_id,
        "Obra":                 obra,
        "Cliente":              cliente.strip(),
        "Tipo":                 "A",
        "Versao":               versao,
        "Data":                 _today_str(),
        "Criado_Por":           user_nome,
        "Status":               "Rascunho",
        "Validade":             validade.strip(),
        "Total_Mao_Obra":       float(cats_totais.get('Mão de Obra', 0)),
        "Total_Materiais":      float(cats_totais.get('Materiais', 0)),
        "Total_Equipamentos":   float(cats_totais.get('Equipamentos', 0)),
        "Total_Deslocacoes":    float(cats_totais.get('Deslocações', 0)),
        "Total_Dormidas":       0.0,
        "Total_Diarias":        0.0,
        "Margem_Pct":           margem,
        "Total_Sem_Margem":     total_sem,
        "Total_Com_Margem":     total_com,
        "Motivo_Rejeicao":      "",
        "Notas":                notas.strip(),
        "Versao_Pai":           versao_pai_id or "",
        "Oportunidade_ID":      oportunidade_id or "",
    }])
    upd_orc = (pd.concat([orc_db, novo], ignore_index=True)
               if not orc_db.empty else novo)
    save_db(upd_orc, "orcamentos.csv")

    linhas_novas = []
    for lin in st.session_state['orc_linhas_temp']:
        linhas_novas.append({**lin, "Orcamento_ID": orc_id})
    if linhas_novas:
        df_lin = pd.DataFrame(linhas_novas)
        upd_lin = (pd.concat([orc_linhas, df_lin], ignore_index=True)
                   if not orc_linhas.empty else df_lin)
        save_db(upd_lin, "orcamentos_linhas.csv")
        inv("orcamentos_linhas.csv")

    inv("orcamentos.csv")
    _cached_load_all.clear()
    log_audit(
        usuario=user_nome, acao="CRIAR_ORCAMENTO_A",
        tabela="orcamentos.csv", registro_id=orc_id,
        detalhes=f"{obra} | v{versao} | €{total_com:,.2f}", ip=""
    )
    st.session_state['orc_linhas_temp'] = []
    st.success(f"✅ Orçamento criado! Total: €{total_com:,.2f}")
    st.rerun()


# ── Tipo B — Cedência MO ─────────────────────────────────────

def _form_tipo_b(orc_db, obras_db, tarifas, ref_precos, user_nome, orc_base, op_db=None):
    obras_ativas = (obras_db[obras_db['Ativa'] == 'Ativa']['Obra'].tolist()
                    if not obras_db.empty else [])

    st.markdown("#### 👷 Orçamento de Cedência de Mão de Obra")
    st.caption("Preenche os campos — o total é calculado automaticamente.")

    col1, col2 = st.columns(2)
    with col1:
        opcoes_obra = obras_ativas if obras_ativas else ["—"]
        nb_obra    = st.selectbox("Obra / Proposta *", opcoes_obra, key="nb_obra")
        nb_cliente = st.text_input("Cliente *", key="nb_cliente")
        nb_versao  = st.number_input("Versão", min_value=1, value=1, key="nb_versao")
        nb_validade = st.text_input("Validade", value=_next_month_str(), key="nb_validade")
        nb_notas   = st.text_area("Notas", key="nb_notas")

    with col2:
        # Zonas disponíveis nas tarifas
        zonas = ["Portugal"]
        if not tarifas.empty and 'Zona' in tarifas.columns:
            zonas = sorted(tarifas['Zona'].dropna().unique().tolist())
        nb_zona = st.selectbox("🌍 Localização / Zona", zonas, key="nb_zona")
        nb_dias  = st.number_input("📅 Nº de Dias", min_value=1, value=5, key="nb_dias")
        nb_horas = st.number_input("⏱️ Horas/Dia", min_value=1, value=8,
                                   max_value=12, key="nb_horas")
        nb_margem = st.slider("Margem (%)", 0, 50, 15, key="nb_margem")
        if nb_margem < 10:
            st.warning("⚠️ Margem muito baixa.")

    st.markdown("---")
    st.markdown("#### 👥 Equipa")

    # Categorias de técnicos disponíveis nas tarifas
    cats_disponiveis = ["Instrumentista", "Mecânico", "Electricista",
                        "Engenheiro", "Supervisor"]
    if not tarifas.empty and 'Categoria' in tarifas.columns:
        cats_tarifas = tarifas[tarifas.get('Zona', '') == nb_zona
                               if 'Zona' in tarifas.columns
                               else tarifas.index >= 0]['Categoria'].dropna().unique().tolist()
        if cats_tarifas:
            cats_disponiveis = cats_tarifas

    equipa = {}
    cols_eq = st.columns(len(cats_disponiveis))
    for col_e, cat in zip(cols_eq, cats_disponiveis):
        with col_e:
            n = st.number_input(cat, min_value=0, value=0, key=f"nb_eq_{cat}")
            equipa[cat] = n

    total_pessoas = sum(equipa.values())

    st.markdown("---")
    st.markdown("#### 🚐 Logística")

    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        nb_car2 = st.number_input("Carrinha 2 lugares", min_value=0,
                                   value=0, key="nb_car2")
    with col_v2:
        nb_car5 = st.number_input("Carrinha 5 lugares", min_value=0,
                                   value=0, key="nb_car5")
    with col_v3:
        nb_car9 = st.number_input("Carrinha 9 lugares", min_value=0,
                                   value=0, key="nb_car9")

    nb_noites = st.number_input(
        "🛏️ Nº de Noites de Dormida",
        min_value=0, value=max(0, nb_dias - 1),
        key="nb_noites"
    )

    # Buscar valores de referência
    def _tarifa(categoria, zona):
        if tarifas.empty:
            return 35.0, 45.0
        t = tarifas[
            (tarifas['Categoria'] == categoria) &
            (tarifas['Zona'] == zona)
        ]
        if t.empty:
            t = tarifas[tarifas['Categoria'] == categoria]
        if t.empty:
            return 35.0, 45.0
        row = t.iloc[0]
        return float(row.get('Valor_Hora', 35)), float(row.get('Diaria', 45))

    def _ref_preco(tipo, capacidade=None):
        if ref_precos.empty:
            defaults = {'dormida': 80.0, 'carrinha_2': 45.0,
                        'carrinha_5': 65.0, 'carrinha_9': 95.0}
            return defaults.get(tipo, 50.0)
        f = ref_precos[ref_precos['Tipo'] == tipo]
        if capacidade:
            f2 = f[f['Capacidade'].astype(str) == str(capacidade)]
            if not f2.empty:
                return float(f2.iloc[0].get('Valor_Dia', 50))
        if not f.empty:
            return float(f.iloc[0].get('Valor_Dia', 50))
        return 50.0

    # ── Cálculo em tempo real ────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💰 Simulação em Tempo Real")

    linhas_b = []
    total_mo = 0.0
    total_diarias = 0.0

    for cat, n in equipa.items():
        if n <= 0:
            continue
        vh, diaria = _tarifa(cat, nb_zona)
        custo_mo = n * nb_dias * nb_horas * vh
        custo_diaria = n * nb_dias * diaria
        total_mo      += custo_mo
        total_diarias += custo_diaria
        linhas_b.append({
            "Item":    f"{cat} ×{n}",
            "Detalhe": f"{n} × {nb_dias}d × {nb_horas}h × €{vh:.2f}/h",
            "Total MO": custo_mo,
            "Diárias": custo_diaria,
        })

    # Carrinhas
    custo_car2 = nb_car2 * nb_dias * _ref_preco('carrinha_2')
    custo_car5 = nb_car5 * nb_dias * _ref_preco('carrinha_5')
    custo_car9 = nb_car9 * nb_dias * _ref_preco('carrinha_9')
    total_carrinhas = custo_car2 + custo_car5 + custo_car9

    # Dormidas
    custo_dorm_unit = _ref_preco('dormida')
    total_dormidas = total_pessoas * nb_noites * custo_dorm_unit

    total_sem = total_mo + total_diarias + total_carrinhas + total_dormidas
    total_com = round(total_sem * (1 + nb_margem / 100), 2)

    # Tabela simulação
    if linhas_b:
        df_sim = pd.DataFrame(linhas_b)
        st.dataframe(
            df_sim.style.format({"Total MO": "€{:.2f}", "Diárias": "€{:.2f}"}),
            use_container_width=True, hide_index=True
        )

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown(
            f"<div class='calc-box'>"
            f"<p style='color:#94A3B8;margin:3px 0;font-size:0.85rem;'>"
            f"👥 Mão de Obra: <b style='color:#F1F5F9;'>€{total_mo:,.2f}</b></p>"
            f"<p style='color:#94A3B8;margin:3px 0;font-size:0.85rem;'>"
            f"🍽️ Diárias: <b style='color:#F1F5F9;'>€{total_diarias:,.2f}</b></p>"
            f"<p style='color:#94A3B8;margin:3px 0;font-size:0.85rem;'>"
            f"🚐 Carrinhas: <b style='color:#F1F5F9;'>€{total_carrinhas:,.2f}</b></p>"
            f"<p style='color:#94A3B8;margin:3px 0;font-size:0.85rem;'>"
            f"🛏️ Dormidas ({total_pessoas}p × {nb_noites}n × €{custo_dorm_unit:.0f}): "
            f"<b style='color:#F1F5F9;'>€{total_dormidas:,.2f}</b></p>"
            f"<p style='color:#64748B;margin:6px 0 2px;font-size:0.8rem;'>"
            f"Total s/ margem: €{total_sem:,.2f}</p>"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_r2:
        st.markdown(
            f"<div class='calc-total'>"
            f"<p style='color:#64748B;margin:0;font-size:0.85rem;'>"
            f"Total Proposta</p>"
            f"<div style='color:#3B82F6;font-size:2rem;font-weight:800;'>"
            f"€{total_com:,.2f}</div>"
            f"<p style='color:#64748B;margin:4px 0 0;font-size:0.8rem;'>"
            f"Margem {nb_margem}% | {total_pessoas} pessoas | {nb_dias} dias</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Editar valores de referência inline
        with st.expander("✏️ Ajustar valores de referência"):
            st.caption("Estes valores substituem os padrões para este orçamento.")
            adj_dorm = st.number_input(
                "€/noite dormida", value=custo_dorm_unit, step=5.0, key="adj_dorm"
            )
            if adj_dorm != custo_dorm_unit:
                total_dormidas = total_pessoas * nb_noites * adj_dorm
                total_sem = total_mo + total_diarias + total_carrinhas + total_dormidas
                total_com = round(total_sem * (1 + nb_margem / 100), 2)

    _op_opts_b = ["— Nenhuma —"]
    if op_db is not None and not op_db.empty:
        _op_opts_b += [
            f"{r['ID']} — {r['Nome']} ({r['Cliente']})"
            for _, r in op_db.iterrows()
        ]
    nb_op_id_raw = st.selectbox(
        "🔗 Oportunidade de Origem (ISO)",
        _op_opts_b, key="nob_op_id",
        help="Liga este orçamento à oportunidade comercial"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Guardar Orçamento Tipo B", type="primary",
                 use_container_width=True, key="btn_save_b"):
        if not nb_obra or nb_obra == "—" or not nb_cliente.strip():
            st.error("❌ Obra e cliente obrigatórios.")
        elif total_pessoas == 0:
            st.error("❌ Adiciona pelo menos um técnico.")
        else:
            _nb_op_id = (
                nb_op_id_raw.split(" — ")[0].strip()
                if nb_op_id_raw != "— Nenhuma —" else ""
            )
            _guardar_orcamento_b(
                orc_db, nb_obra, nb_cliente, nb_versao, nb_validade,
                nb_margem, nb_notas, nb_zona, nb_dias, nb_horas,
                equipa, nb_noites, total_mo, total_diarias,
                total_carrinhas, total_dormidas, total_sem, total_com,
                user_nome, _nb_op_id
            )


def _guardar_orcamento_b(orc_db, obra, cliente, versao, validade,
                          margem, notas, zona, dias, horas,
                          equipa, noites, tot_mo, tot_diarias,
                          tot_carrinhas, tot_dormidas, total_sem,
                          total_com, user_nome, oportunidade_id=""):
    from core import _cached_load_all
    orc_id = str(uuid.uuid4())[:8].upper()
    equipa_str = ", ".join(f"{n}× {cat}" for cat, n in equipa.items() if n > 0)
    novo = pd.DataFrame([{
        "ID":                   orc_id,
        "Obra":                 obra,
        "Cliente":              cliente.strip(),
        "Tipo":                 "B",
        "Versao":               versao,
        "Data":                 _today_str(),
        "Criado_Por":           user_nome,
        "Status":               "Rascunho",
        "Validade":             validade.strip(),
        "Total_Mao_Obra":       tot_mo,
        "Total_Materiais":      0.0,
        "Total_Equipamentos":   0.0,
        "Total_Deslocacoes":    tot_carrinhas,
        "Total_Dormidas":       tot_dormidas,
        "Total_Diarias":        tot_diarias,
        "Margem_Pct":           margem,
        "Total_Sem_Margem":     total_sem,
        "Total_Com_Margem":     total_com,
        "Motivo_Rejeicao":      "",
        "Notas":                (f"Zona: {zona} | {dias}d×{horas}h | "
                                 f"{equipa_str} | {noites} noites | "
                                 f"{notas}").strip(),
        "Versao_Pai":           "",
        "Oportunidade_ID":      oportunidade_id or "",
    }])
    upd = (pd.concat([orc_db, novo], ignore_index=True)
           if not orc_db.empty else novo)
    save_db(upd, "orcamentos.csv")
    inv("orcamentos.csv")
    _cached_load_all.clear()
    log_audit(
        usuario=user_nome, acao="CRIAR_ORCAMENTO_B",
        tabela="orcamentos.csv", registro_id=orc_id,
        detalhes=f"{obra} | v{versao} | €{total_com:,.2f} | {equipa_str}", ip=""
    )
    st.success(f"✅ Orçamento Tipo B criado! Total: €{total_com:,.2f}")
    st.rerun()


# ─────────────────────────────────────────────────────────────
# TAB 4 — CATÁLOGO
# ─────────────────────────────────────────────────────────────

def _tab_catalogo(catalogo, tarifas, ref_precos):
    sub = st.tabs([
        "⚡ Catálogo de Tempos",
        "💶 Tarifas MO",
        "🚐 Preços Referência",
    ])

    # ── Catálogo de Tempos ────────────────────────────────────
    with sub[0]:
        st.markdown("#### ⚡ Catálogo de Itens e Tempos")
        st.caption("Base de dados de actividades com tempo estimado por unidade.")

        col_ca1, col_ca2 = st.columns([3, 1])
        with col_ca2:
            if st.button("➕ Novo Item", key="cat_novo_btn",
                         use_container_width=True, type="primary"):
                st.session_state['cat_novo_open'] = True

        if st.session_state.get('cat_novo_open', False):
            with st.form("form_cat_novo"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    c_cat  = st.selectbox(
                        "Categoria",
                        ["Instrumentação", "Cablagem", "Comissionamento",
                         "Civil", "Mecânica", "Inspecção", "Outro"],
                        key="c_cat"
                    )
                    c_desc = st.text_input("Descrição *", key="c_desc")
                    c_uni  = st.selectbox(
                        "Unidade",
                        ["un", "h", "m", "m²", "m³", "loop", "vg", "dia"],
                        key="c_uni"
                    )
                with cc2:
                    c_mins  = st.number_input("Minutos/unidade *",
                                               min_value=0.0, step=1.0, key="c_mins")
                    c_preco = st.number_input("Preço sugerido (€/un)",
                                               min_value=0.0, step=0.5, key="c_preco")

                if st.form_submit_button("💾 Guardar"):
                    if c_desc.strip() and c_mins > 0:
                        novo_item = pd.DataFrame([{
                            "ID":               str(uuid.uuid4())[:6].upper(),
                            "Categoria":        c_cat,
                            "Descricao":        c_desc.strip(),
                            "Unidade":          c_uni,
                            "Minutos_Unit":     c_mins,
                            "Preco_Sugerido":   c_preco,
                            "Vezes_Usado":      0,
                            "Activo":           "Sim",
                            "Data_Actualizacao":_today_str(),
                        }])
                        upd = (pd.concat([catalogo, novo_item], ignore_index=True)
                               if not catalogo.empty else novo_item)
                        save_db(upd, "orc_catalogo.csv")
                        inv("orc_catalogo.csv")
                        st.success("✅ Item adicionado ao catálogo!")
                        st.session_state['cat_novo_open'] = False
                        st.rerun()
                    else:
                        st.error("Descrição e minutos obrigatórios.")

        # Upload bulk
        with st.expander("📥 Importação em bulk (CSV)"):
            st.caption("Colunas: Categoria, Descricao, Unidade, Minutos_Unit, Preco_Sugerido")
            f_bulk = st.file_uploader("Upload CSV", type="csv", key="cat_bulk")
            if f_bulk and st.button("📥 Importar", key="cat_import_btn"):
                try:
                    df_imp = pd.read_csv(f_bulk)
                    df_imp['ID']               = [str(uuid.uuid4())[:6].upper()
                                                   for _ in range(len(df_imp))]
                    df_imp['Vezes_Usado']      = 0
                    df_imp['Activo']           = 'Sim'
                    df_imp['Data_Actualizacao'] = _today_str()
                    upd = (pd.concat([catalogo, df_imp], ignore_index=True)
                           if not catalogo.empty else df_imp)
                    save_db(upd, "orc_catalogo.csv")
                    inv("orc_catalogo.csv")
                    st.success(f"✅ {len(df_imp)} itens importados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

        # Tabela catálogo
        if not catalogo.empty:
            pesq_c = st.text_input("🔍 Filtrar", key="cat_pesq")
            df_c   = catalogo.copy()
            if pesq_c:
                df_c = df_c[
                    df_c['Descricao'].str.contains(pesq_c, case=False, na=False)
                ]
            cols_show = [c for c in [
                'Categoria', 'Descricao', 'Unidade',
                'Minutos_Unit', 'Preco_Sugerido', 'Vezes_Usado', 'Activo'
            ] if c in df_c.columns]
            st.dataframe(df_c[cols_show].sort_values('Vezes_Usado', ascending=False),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Catálogo vazio. Adiciona itens ou faz importação bulk.")

    # ── Tarifas MO ───────────────────────────────────────────
    with sub[1]:
        st.markdown("#### 💶 Tabela de Tarifas de Mão de Obra")
        st.caption("Valores hora e diária por categoria e zona geográfica.")

        if st.button("➕ Nova Tarifa", key="tar_novo_btn"):
            st.session_state['tar_novo_open'] = True

        if st.session_state.get('tar_novo_open', False):
            with st.form("form_tarifa"):
                t1, t2 = st.columns(2)
                with t1:
                    t_cat  = st.text_input("Categoria (ex: Instrumentista)", key="t_cat")
                    t_zona = st.text_input("Zona (ex: Portugal, Espanha)", key="t_zona")
                with t2:
                    t_vh   = st.number_input("Valor/hora (€)", min_value=0.0,
                                              step=0.5, key="t_vh")
                    t_hd   = st.number_input("Horas/dia", min_value=1,
                                              value=8, key="t_hd")
                    t_diaria = st.number_input("Diária (€)", min_value=0.0,
                                                step=1.0, key="t_diaria")

                if st.form_submit_button("💾 Guardar"):
                    if t_cat.strip() and t_zona.strip():
                        novo_t = pd.DataFrame([{
                            "ID":               str(uuid.uuid4())[:6].upper(),
                            "Categoria":        t_cat.strip(),
                            "Zona":             t_zona.strip(),
                            "Valor_Hora":       t_vh,
                            "Horas_Dia":        t_hd,
                            "Diaria":           t_diaria,
                            "Data_Actualizacao":_today_str(),
                        }])
                        upd = (pd.concat([tarifas, novo_t], ignore_index=True)
                               if not tarifas.empty else novo_t)
                        save_db(upd, "orc_tarifas.csv")
                        inv("orc_tarifas.csv")
                        st.success("✅ Tarifa guardada!")
                        st.session_state['tar_novo_open'] = False
                        st.rerun()

        if not tarifas.empty:
            st.dataframe(tarifas, use_container_width=True, hide_index=True)
        else:
            st.info("Sem tarifas. Adiciona a tabela de preços CPS.")

    # ── Preços Referência ────────────────────────────────────
    with sub[2]:
        st.markdown("#### 🚐 Preços de Referência (Carrinhas e Dormidas)")
        st.caption("Valores editáveis. Actualizados periodicamente.")

        if not ref_precos.empty:
            st.dataframe(ref_precos, use_container_width=True, hide_index=True)

        with st.expander("✏️ Actualizar / Adicionar preço"):
            with st.form("form_ref"):
                r1, r2 = st.columns(2)
                with r1:
                    r_tipo = st.selectbox(
                        "Tipo",
                        ["dormida", "carrinha_2", "carrinha_5", "carrinha_9", "outro"],
                        key="r_tipo"
                    )
                    r_desc = st.text_input("Descrição", key="r_desc")
                with r2:
                    r_val  = st.number_input("Valor/dia ou noite (€)",
                                              min_value=0.0, step=1.0, key="r_val")
                    r_fonte = st.text_input("Fonte (opcional)", key="r_fonte")

                if st.form_submit_button("💾 Guardar"):
                    novo_r = pd.DataFrame([{
                        "ID":               str(uuid.uuid4())[:6].upper(),
                        "Tipo":             r_tipo,
                        "Descricao":        r_desc.strip(),
                        "Valor_Dia":        r_val,
                        "Capacidade":       "",
                        "Fonte":            r_fonte.strip(),
                        "Data_Actualizacao":_today_str(),
                    }])
                    upd = (pd.concat([ref_precos, novo_r], ignore_index=True)
                           if not ref_precos.empty else novo_r)
                    save_db(upd, "orc_ref_precos.csv")
                    inv("orc_ref_precos.csv")
                    st.success("✅ Preço de referência actualizado!")
                    st.rerun()


# ─────────────────────────────────────────────────────────────
# TAB 5 — ANALYTICS
# ─────────────────────────────────────────────────────────────

def _tab_analytics(orc_db, clientes_db):
    if orc_db.empty:
        st.info("Sem dados para análise.")
        return

    try:
        import plotly.graph_objects as go
        import plotly.express as px
        HAS_PLOTLY = True
    except ImportError:
        HAS_PLOTLY = False

    st.markdown("#### 📈 Analytics de Orçamentação")

    # ── KPIs ─────────────────────────────────────────────────
    adj     = orc_db[orc_db['Status'] == 'Adjudicado']
    rej     = orc_db[orc_db['Status'] == 'Rejeitado']
    fechados = len(adj) + len(rej)
    tx_conv = round(len(adj) / max(fechados, 1) * 100, 1)
    margem_media = pd.to_numeric(
        orc_db['Margem_Pct'], errors='coerce'
    ).fillna(0).mean()
    val_ganho = _num(adj, 'Total_Com_Margem')
    val_perdido = _num(rej, 'Total_Com_Margem')

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("✅ Taxa Conversão", f"{tx_conv}%")
    with c2:
        st.metric("🏆 Valor Ganho", f"€{val_ganho:,.0f}")
    with c3:
        st.metric("❌ Valor Perdido", f"€{val_perdido:,.0f}")
    with c4:
        st.metric("📊 Margem Média", f"{margem_media:.1f}%")

    st.divider()

    col_a1, col_a2 = st.columns(2)

    # ── Funil de conversão ───────────────────────────────────
    with col_a1:
        st.markdown("**🔽 Funil de Conversão**")
        estados_funil = ['Rascunho', 'Enviado', 'Em Revisão', 'Adjudicado']
        vals_funil    = [len(orc_db[orc_db['Status'] == e])
                         for e in estados_funil]
        if HAS_PLOTLY and any(v > 0 for v in vals_funil):
            fig_f = go.Figure(go.Funnel(
                y=estados_funil, x=vals_funil,
                textinfo="value+percent initial",
                marker=dict(color=['#6B7280', '#3B82F6', '#8B5CF6', '#10B981']),
                textfont=dict(color='#F1F5F9')
            ))
            fig_f.update_layout(
                height=280, paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F1F5F9'),
                margin=dict(t=20, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_f, use_container_width=True)
        else:
            for e, v in zip(estados_funil, vals_funil):
                st.progress(v / max(max(vals_funil), 1), text=f"{e}: {v}")

    # ── Motivos de rejeição ──────────────────────────────────
    with col_a2:
        st.markdown("**❌ Motivos de Rejeição**")
        if not rej.empty and 'Motivo_Rejeicao' in rej.columns:
            motivos = rej['Motivo_Rejeicao'].dropna()
            motivos = motivos[motivos != '']
            if not motivos.empty:
                cnt = motivos.value_counts()
                if HAS_PLOTLY:
                    fig_m = px.pie(
                        values=cnt.values, names=cnt.index,
                        color_discrete_sequence=px.colors.sequential.Blues_r
                    )
                    fig_m.update_layout(
                        height=280, paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#F1F5F9'),
                        margin=dict(t=20, b=10, l=10, r=10),
                        showlegend=True,
                        legend=dict(font=dict(color='#94A3B8', size=11))
                    )
                    st.plotly_chart(fig_m, use_container_width=True)
                else:
                    for m, c in cnt.items():
                        st.text(f"{m}: {c}")
            else:
                st.info("Sem motivos registados.")
        else:
            st.info("Sem rejeições com motivo registado.")

    st.divider()

    # ── Top clientes ─────────────────────────────────────────
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown("**🏆 Top Clientes por Valor Adjudicado**")
        if not adj.empty:
            top_cli = (
                adj.groupby('Cliente')['Total_Com_Margem']
                .apply(lambda x: pd.to_numeric(x, errors='coerce').sum())
                .sort_values(ascending=False)
                .head(5)
            )
            for cli, val in top_cli.items():
                pct = val / max(top_cli.max(), 1)
                st.markdown(
                    f"<div style='margin-bottom:6px;'>"
                    f"<div style='display:flex;justify-content:space-between;"
                    f"color:#F1F5F9;font-size:0.85rem;'>"
                    f"<span>{cli}</span><span>€{val:,.0f}</span></div>"
                    f"<div style='background:#1E293B;border-radius:4px;height:6px;'>"
                    f"<div style='background:#10B981;width:{pct*100:.0f}%;"
                    f"height:6px;border-radius:4px;'></div></div></div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Sem adjudicações.")

    with col_b2:
        st.markdown("**📅 Orçamentos por Mês**")
        if not orc_db.empty and 'Data' in orc_db.columns:
            try:
                orc_db['_data_dt'] = pd.to_datetime(
                    orc_db['Data'], format="%d/%m/%Y", errors='coerce'
                )
                mensal = (
                    orc_db.dropna(subset=['_data_dt'])
                    .groupby(orc_db['_data_dt'].dt.to_period('M'))
                    .size()
                    .tail(12)
                )
                if not mensal.empty and HAS_PLOTLY:
                    fig_m2 = go.Figure(go.Bar(
                        x=[str(p) for p in mensal.index],
                        y=mensal.values,
                        marker_color='#3B82F6',
                        text=mensal.values,
                        textposition='outside',
                        textfont=dict(color='#94A3B8', size=11)
                    ))
                    fig_m2.update_layout(
                        height=250, paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(30,41,59,0.3)',
                        font=dict(color='#F1F5F9'),
                        xaxis=dict(tickfont=dict(color='#64748B', size=10),
                                   gridcolor='#1E293B'),
                        yaxis=dict(tickfont=dict(color='#64748B'),
                                   gridcolor='#1E293B'),
                        margin=dict(t=20, b=20, l=10, r=10)
                    )
                    st.plotly_chart(fig_m2, use_container_width=True)
                else:
                    st.dataframe(mensal.reset_index(), use_container_width=True,
                                 hide_index=True)
            except Exception:
                st.info("Dados insuficientes para gráfico mensal.")


# ─────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────

def render_orcamentacao(*_):
    """Módulo Master de Orçamentação — CPS Smart Solutions."""
    _inject_css()

    (orc_db, orc_linhas, obras_db,
     catalogo, tarifas, ref_precos, clientes_db) = _carregar_dados()

    user_nome = st.session_state.get('user', 'Admin')
    hoje = date.today()

    st.markdown("### 📊 Orçamentação")

    # KPI header rápido
    n_total   = len(orc_db) if not orc_db.empty else 0
    n_ativos  = len(orc_db[orc_db['Status'].isin(
        ['Rascunho', 'Enviado', 'Em Revisão'])]) if not orc_db.empty else 0
    val_pipe  = _num(
        orc_db[orc_db['Status'] == 'Enviado'] if not orc_db.empty
        else pd.DataFrame(), 'Total_Com_Margem'
    )
    # Alertas expiração
    n_exp = 0
    if not orc_db.empty:
        env = orc_db[orc_db['Status'] == 'Enviado']
        for _, r in env.iterrows():
            if _days_until(r.get('Validade', '')) <= 15:
                n_exp += 1

    col_h = st.columns(4)
    metricas = [
        ("📋 Total", n_total, None),
        ("🔄 Activos", n_ativos, None),
        ("💰 Em Pipeline", f"€{val_pipe:,.0f}", None),
        ("⚠️ A Expirar", n_exp,
         "⚠️" if n_exp > 0 else None),
    ]
    for col, (label, val, delta) in zip(col_h, metricas):
        with col:
            st.metric(label, val, delta=delta if delta else None,
                      delta_color="inverse" if delta else "normal")

    st.divider()

    tab_cockpit, tab_lista, tab_novo, tab_cat, tab_analytics = st.tabs([
        "🎯 Cockpit",
        "📋 Orçamentos",
        "➕ Novo Orçamento",
        "⚡ Catálogo",
        "📈 Analytics",
    ])

    with tab_cockpit:
        _tab_cockpit(orc_db, clientes_db)

    with tab_lista:
        _tab_lista(orc_db, orc_linhas, clientes_db)

    with tab_novo:
        _tab_novo(orc_db, orc_linhas, obras_db, catalogo, tarifas, ref_precos)

    with tab_cat:
        _tab_catalogo(catalogo, tarifas, ref_precos)

    with tab_analytics:
        _tab_analytics(orc_db, clientes_db)

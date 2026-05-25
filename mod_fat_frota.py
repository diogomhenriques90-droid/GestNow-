"""
GESTNOW v3 — mod_fat_frota.py
Passo 5 — Frota & Renting
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, base64, io, os
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from core import save_db, inv, load_db, log_audit

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load(nome, cols):
    try:
        return load_db(nome, cols, silent=True)
    except:
        return pd.DataFrame(columns=cols)

def _dias_para(data_str: str) -> int:
    """Dias até uma data futura (negativo = já passou)."""
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return 999

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()

# ─────────────────────────────────────────────────────────────────
# CALCULADORA TCO (Total Cost of Ownership)
# ─────────────────────────────────────────────────────────────────

def _calcular_tco_renting(valor_renda: float,
                           anos: int,
                           km_ano: int,
                           custo_km_exc: float = 0.12) -> dict:
    """Calcula TCO do renting."""
    total_rendas    = valor_renda * 12 * anos
    custo_seguros   = valor_renda * 0.15 * anos   # estimativa
    custo_manut     = 0.0                          # incluído no renting
    total_renting   = total_rendas + custo_seguros

    return {
        "total_rendas":  round(total_rendas, 2),
        "custo_seguros": round(custo_seguros, 2),
        "custo_manut":   round(custo_manut, 2),
        "total":         round(total_renting, 2),
        "custo_mes":     round(total_renting / (anos * 12), 2),
        "custo_km":      round(total_renting / (km_ano * anos), 4)
        if km_ano > 0 else 0,
    }


def _calcular_tco_compra(preco_compra: float,
                          anos: int,
                          km_ano: int,
                          taxa_juro: float = 5.0,
                          valor_residual_pct: float = 20.0) -> dict:
    """Calcula TCO da compra financiada."""
    # Amortização linear
    valor_residual = preco_compra * valor_residual_pct / 100
    amort_anual    = (preco_compra - valor_residual) / anos
    # Juros simples
    juros_total    = preco_compra * taxa_juro / 100 * anos / 2
    # Manutenção estimada 2% do valor/ano
    manut_total    = preco_compra * 0.02 * anos
    # Seguro estimado 3% do valor/ano decrescente
    seguro_total   = preco_compra * 0.03 * anos * 0.7
    total_compra   = (
        preco_compra - valor_residual +
        juros_total + manut_total + seguro_total
    )

    return {
        "preco_compra":   preco_compra,
        "valor_residual": round(valor_residual, 2),
        "amort_anual":    round(amort_anual, 2),
        "juros_total":    round(juros_total, 2),
        "manut_total":    round(manut_total, 2),
        "seguro_total":   round(seguro_total, 2),
        "total":          round(total_compra, 2),
        "custo_mes":      round(total_compra / (anos * 12), 2),
        "custo_km":       round(total_compra / (km_ano * anos), 4)
        if km_ano > 0 else 0,
    }


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_custos_frota_mensal(comb_db, renting_db):
    """Line chart custos totais frota por mês."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    hoje    = date.today()
    labels  = []
    comb_m  = []
    rent_m  = []

    renda_mensal = 0.0
    if not renting_db.empty and 'Valor_Mensal' in renting_db.columns:
        ativos = renting_db[
            renting_db.get('Estado','') != 'Terminado'
        ] if 'Estado' in renting_db.columns else renting_db
        renda_mensal = pd.to_numeric(
            ativos['Valor_Mensal'], errors='coerce'
        ).fillna(0).sum()

    for i in range(5, -1, -1):
        d = date(hoje.year, hoje.month, 1) - timedelta(days=i*30)
        labels.append(meses_pt[d.month - 1])

        val_c = 0.0
        if not comb_db.empty and 'Data' in comb_db.columns:
            cb = comb_db.copy()
            cb['Data_d'] = pd.to_datetime(
                cb['Data'], dayfirst=True, errors='coerce'
            )
            cb['Valor_Num'] = pd.to_numeric(
                cb.get('Valor', 0), errors='coerce'
            ).fillna(0)
            mask = (
                (cb['Data_d'].dt.month == d.month) &
                (cb['Data_d'].dt.year  == d.year)
            )
            val_c = cb[mask]['Valor_Num'].sum()
        comb_m.append(round(val_c, 2))
        rent_m.append(round(renda_mensal, 2))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Combustível', x=labels, y=comb_m,
        marker_color='#F59E0B',
        hovertemplate='%{x}<br>Comb: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Renting', x=labels, y=rent_m,
        marker_color='#3B82F6',
        hovertemplate='%{x}<br>Renting: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        name='Total',
        x=labels,
        y=[c + r for c, r in zip(comb_m, rent_m)],
        mode='lines+markers',
        line={'color':'#10B981','width':3},
        marker={'size':8},
        hovertemplate='%{x}<br>Total: €%{y:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Custos Frota — 6 Meses',
               'font':{'color':'#F1F5F9'}},
        barmode='stack',
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10)
    )
    return fig


def _grafico_km_vs_contratado(renting_db, comb_db):
    """Bar chart KM reais vs contratados por viatura."""
    if renting_db.empty:
        return None

    viaturas = renting_db['Matricula'].tolist() \
               if 'Matricula' in renting_db.columns else []
    if not viaturas:
        return None

    km_cont = []
    km_reais = []

    for mat in viaturas:
        row = renting_db[renting_db['Matricula'] == mat].iloc[0]
        km_c = float(row.get('KM_Ano', 0) or 0)
        km_cont.append(km_c)

        # KM reais dos abastecimentos
        km_r = 0.0
        if not comb_db.empty and 'Matricula' in comb_db.columns:
            c_mat = comb_db[comb_db['Matricula'] == mat]
            if not c_mat.empty and 'KM' in c_mat.columns:
                km_vals = pd.to_numeric(
                    c_mat['KM'], errors='coerce'
                ).dropna()
                if not km_vals.empty:
                    km_r = km_vals.max() - km_vals.min()
        km_reais.append(round(km_r, 0))

    viat_short = [m[:8] for m in viaturas]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='KM Contratados/Ano', x=viat_short, y=km_cont,
        marker_color='rgba(59,130,246,0.5)',
        hovertemplate='%{x}<br>Contratado: %{y:,.0f} km<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='KM Reais', x=viat_short, y=km_reais,
        marker_color=[ '#10B981' if r <= c
                       else '#EF4444'
                       for r, c in zip(km_reais, km_cont) ],
        hovertemplate='%{x}<br>Reais: %{y:,.0f} km<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'KM Reais vs Contratados',
               'font':{'color':'#F1F5F9'}},
        barmode='group',
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'ticksuffix':' km'},
        margin=dict(t=40,b=20,l=10,r=10)
    )
    return fig


def _grafico_tco_comparacao(tco_r, tco_c, anos):
    """Waterfall comparação TCO renting vs compra."""
    fig = go.Figure()

    categorias = ['Rendas/Amort.', 'Seguros', 'Manutenção',
                  'Juros', 'TOTAL']

    vals_rent = [
        tco_r['total_rendas'],
        tco_r['custo_seguros'],
        0,
        0,
        tco_r['total']
    ]
    vals_comp = [
        tco_c['preco_compra'] - tco_c['valor_residual'],
        tco_c['seguro_total'],
        tco_c['manut_total'],
        tco_c['juros_total'],
        tco_c['total']
    ]

    fig.add_trace(go.Bar(
        name=f'Renting ({anos}a)',
        x=categorias, y=vals_rent,
        marker_color='#3B82F6',
        text=[f"€{v:,.0f}" for v in vals_rent],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':9}
    ))
    fig.add_trace(go.Bar(
        name=f'Compra ({anos}a)',
        x=categorias, y=vals_comp,
        marker_color='#8B5CF6',
        text=[f"€{v:,.0f}" for v in vals_comp],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':9}
    ))
    fig.update_layout(
        title={'text':f'TCO Comparação — {anos} anos',
               'font':{'color':'#F1F5F9'}},
        barmode='group',
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10)
    )
    return fig


def _grafico_timeline_renting(renting_db):
    """Gantt timeline dos contratos de renting."""
    if renting_db.empty:
        return None

    fig = go.Figure()
    cores = ['#3B82F6','#10B981','#F59E0B','#8B5CF6',
             '#EF4444','#06B6D4']

    for i, (_, row) in enumerate(renting_db.iterrows()):
        try:
            ini = datetime.strptime(
                row.get('Data_Inicio','01/01/2024'), "%d/%m/%Y"
            )
            fim = datetime.strptime(
                row.get('Data_Fim','31/12/2026'), "%d/%m/%Y"
            )
        except:
            continue

        cor = cores[i % len(cores)]
        mat = row.get('Matricula','')
        ren = float(row.get('Valor_Mensal', 0) or 0)
        ban = row.get('Banco','')

        fig.add_trace(go.Scatter(
            x=[ini, fim],
            y=[mat, mat],
            mode='lines',
            line={'color':cor,'width':16},
            name=f"{mat} ({ban})",
            hovertemplate=(
                f"<b>{mat}</b><br>"
                f"Início: {row.get('Data_Inicio','')}<br>"
                f"Fim: {row.get('Data_Fim','')}<br>"
                f"Renda: €{ren:,.2f}/mês<br>"
                f"Banco: {ban}<extra></extra>"
            )
        ))
        # Marca hoje
        fig.add_vline(
            x=datetime.now(),
            line_dash="dash",
            line_color="#F1F5F9",
            line_width=1,
            annotation_text="Hoje",
            annotation_font_color="#94A3B8"
        )

    fig.update_layout(
        title={'text':'Timeline Contratos de Renting',
               'font':{'color':'#F1F5F9'}},
        height=max(200, len(renting_db) * 60 + 80),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=80,r=10),
        showlegend=False
    )
    return fig


def _grafico_consumo_viatura(comb_db, matricula):
    """Line chart consumo e custo de uma viatura."""
    if comb_db.empty or 'Matricula' not in comb_db.columns:
        return None

    cb = comb_db[comb_db['Matricula'] == matricula].copy()
    if cb.empty:
        return None

    cb['Data_d']     = pd.to_datetime(
        cb['Data'], dayfirst=True, errors='coerce'
    )
    cb['Litros_Num'] = pd.to_numeric(
        cb.get('Litros',0), errors='coerce'
    ).fillna(0)
    cb['Valor_Num']  = pd.to_numeric(
        cb.get('Valor',0), errors='coerce'
    ).fillna(0)
    cb = cb.sort_values('Data_d')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Litros',
        x=cb['Data_d'],
        y=cb['Litros_Num'],
        marker_color='#F59E0B',
        yaxis='y',
        hovertemplate='%{x|%d/%m/%Y}<br>%{y:.1f}L<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        name='Valor €',
        x=cb['Data_d'],
        y=cb['Valor_Num'],
        mode='lines+markers',
        line={'color':'#EF4444','width':2},
        yaxis='y2',
        hovertemplate='%{x|%d/%m/%Y}<br>€%{y:.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':f'Consumo — {matricula}',
               'font':{'color':'#F1F5F9'}},
        height=240,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        legend={'font':{'color':'#94A3B8'}},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'ticksuffix':'L','side':'left'},
        yaxis2={'overlaying':'y','side':'right',
                'tickprefix':'€',
                'tickfont':{'color':'#EF4444'},
                'showgrid':False},
        margin=dict(t=40,b=20,l=10,r=50)
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_frota(*_):
    """Módulo Frota & Renting — visão financeira."""

    # ── Carregar dados ────────────────────────────────────────────
    renting_db = _load("renting_contratos.csv", [
        "ID","Matricula","Marca","Modelo","Banco",
        "Data_Inicio","Data_Fim","Valor_Mensal","KM_Ano",
        "KM_Excedente_Preco","Opcao_Compra","Valor_Residual",
        "Estado","Obra_Alocada"
    ])
    comb_db = _load("frota_combustivel.csv", [
        "ID","Data","Matricula","Condutor","Litros",
        "Valor","KM","Tipo_Comb","Recibo_b64"
    ])
    frota_db = _load("frota_viaturas.csv", [
        "ID","Matricula","Marca","Modelo","Tipo",
        "Condutor","Custo_Mensal","Status","Data_Registo"
    ])
    seguros_db = _load("seguros_db.csv", [
        "ID","Tipo","Entidade","Viatura","Valor_Anual",
        "Data_Inicio","Data_Fim","Apolice"
    ])

    user_nome = st.session_state.get('user','Admin')

    # ── KPIs ──────────────────────────────────────────────────────
    n_viat    = len(frota_db) if not frota_db.empty else 0
    n_renting = len(renting_db[
        renting_db.get('Estado','') != 'Terminado'
    ]) if not renting_db.empty and 'Estado' in renting_db.columns \
      else len(renting_db)

    renda_total = pd.to_numeric(
        renting_db[
            renting_db.get('Estado','') != 'Terminado'
        ]['Valor_Mensal'] if not renting_db.empty and
        'Estado' in renting_db.columns else
        renting_db.get('Valor_Mensal', pd.Series()),
        errors='coerce'
    ).fillna(0).sum() if not renting_db.empty else 0.0

    custo_comb_mes = 0.0
    if not comb_db.empty and 'Data' in comb_db.columns:
        cb_m = comb_db.copy()
        cb_m['Data_d'] = pd.to_datetime(
            cb_m['Data'], dayfirst=True, errors='coerce'
        )
        mes_a = date.today()
        mask  = (
            (cb_m['Data_d'].dt.month == mes_a.month) &
            (cb_m['Data_d'].dt.year  == mes_a.year)
        )
        custo_comb_mes = pd.to_numeric(
            cb_m[mask].get('Valor',0), errors='coerce'
        ).fillna(0).sum()

    custo_total_mes = renda_total + custo_comb_mes

    # Alertas
    n_alertas_rent = 0
    if not renting_db.empty and 'Data_Fim' in renting_db.columns:
        for _, row in renting_db.iterrows():
            d = _dias_para(row.get('Data_Fim',''))
            if 0 <= d <= 60:
                n_alertas_rent += 1

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("🚗 Viaturas",        n_viat)
    with c2: st.metric("🏦 Em Renting",       n_renting)
    with c3: st.metric("💰 Rendas/Mês",       f"€{renda_total:,.2f}")
    with c4: st.metric("⛽ Comb. Mês",        f"€{custo_comb_mes:,.2f}")
    with c5: st.metric("💸 Custo Total Mês",  f"€{custo_total_mes:,.2f}")

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_rent, t_comb, t_tco,
     t_seguros, t_relatorio) = st.tabs([
        "🏦 Contratos Renting",
        "⛽ Combustível & KM",
        "📊 Comparador TCO",
        "🛡️ Seguros Frota",
        "📋 Relatório Financeiro",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — CONTRATOS RENTING
    # ════════════════════════════════════════════════════════════════
    with t_rent:
        st.markdown("### 🏦 Contratos de Renting")

        col_form_r, col_lista_r = st.columns([1, 2])

        with col_form_r:
            st.markdown("#### ➕ Novo Contrato")
            with st.form("form_renting"):
                r_mat   = st.text_input(
                    "Matrícula *", key="rent_mat",
                    placeholder="AA-00-AA"
                )
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    r_marca = st.text_input("Marca",  key="rent_marca")
                with col_r2:
                    r_mod   = st.text_input("Modelo", key="rent_mod")

                r_banco = st.selectbox(
                    "Banco/Financeira *",
                    ["Millennium BCP","BNP Paribas",
                     "Santander","CGD","Novo Banco",
                     "Montepio","EuroBic","Outro"],
                    key="rent_banco"
                )
                r_renda = st.number_input(
                    "Renda Mensal (€) *",
                    min_value=0.0, step=50.0,
                    key="rent_renda"
                )

                col_rd1, col_rd2 = st.columns(2)
                with col_rd1:
                    r_ini = st.date_input(
                        "Início", value=date.today(),
                        key="rent_ini"
                    )
                with col_rd2:
                    r_fim = st.date_input(
                        "Fim",
                        value=date.today() + timedelta(days=365*3),
                        key="rent_fim"
                    )

                col_rk1, col_rk2 = st.columns(2)
                with col_rk1:
                    r_km_ano = st.number_input(
                        "KM contratados/ano",
                        min_value=0, value=20000,
                        step=1000, key="rent_km"
                    )
                with col_rk2:
                    r_km_exc = st.number_input(
                        "€/km excedente",
                        min_value=0.0,
                        value=0.12, step=0.01,
                        key="rent_km_exc"
                    )

                r_opc_compra = st.number_input(
                    "Opção de Compra (€)",
                    min_value=0.0, step=100.0,
                    key="rent_opc"
                )
                r_obra = st.text_input(
                    "Obra alocada (opcional)",
                    key="rent_obra"
                )

                if st.form_submit_button(
                    "💾 Guardar Contrato",
                    use_container_width=True, type="primary"
                ):
                    if not r_mat.strip() or r_renda <= 0:
                        st.error("❌ Matrícula e renda obrigatórios.")
                    else:
                        meses_cont = max(
                            1,
                            (r_fim.year - r_ini.year) * 12 +
                            (r_fim.month - r_ini.month)
                        )
                        novo_r = pd.DataFrame([{
                            "ID":                str(uuid.uuid4())[:8].upper(),
                            "Matricula":         r_mat.strip().upper(),
                            "Marca":             r_marca.strip(),
                            "Modelo":            r_mod.strip(),
                            "Banco":             r_banco,
                            "Data_Inicio":       r_ini.strftime("%d/%m/%Y"),
                            "Data_Fim":          r_fim.strftime("%d/%m/%Y"),
                            "Valor_Mensal":      r_renda,
                            "KM_Ano":            r_km_ano,
                            "KM_Excedente_Preco":r_km_exc,
                            "Opcao_Compra":      r_opc_compra,
                            "Valor_Residual":    r_opc_compra,
                            "Estado":            "Ativo",
                            "Obra_Alocada":      r_obra.strip()
                        }])
                        upd_r = pd.concat(
                            [renting_db, novo_r], ignore_index=True
                        ) if not renting_db.empty else novo_r
                        save_db(upd_r, "renting_contratos.csv")
                        log_audit(
                            usuario=user_nome,
                            acao="CRIAR_CONTRATO_RENTING",
                            tabela="renting_contratos.csv",
                            registro_id=novo_r['ID'].iloc[0],
                            detalhes=(
                                f"{r_mat} | {r_banco} | "
                                f"€{r_renda}/mês"
                            ),
                            ip=""
                        )
                        inv("renting_contratos.csv")
                        st.success(
                            f"✅ Contrato {r_mat.upper()} guardado!"
                        )
                        st.rerun()

        with col_lista_r:
            st.markdown("#### 📋 Contratos Ativos")

            # Timeline
            fig_tl = _grafico_timeline_renting(renting_db)
            if fig_tl:
                st.plotly_chart(
                    fig_tl, use_container_width=True
                )

            if renting_db.empty:
                st.info("📋 Sem contratos de renting.")
            else:
                for _, row in renting_db.iterrows():
                    rent_id  = row.get('ID','')
                    renda    = float(row.get('Valor_Mensal',0) or 0)
                    km_c     = int(row.get('KM_Ano',0) or 0)
                    dias_fim = _dias_para(row.get('Data_Fim',''))
                    meses_rest = max(0, dias_fim // 30)
                    total_rest  = renda * meses_rest
                    estado   = row.get('Estado','Ativo')

                    # Cor e alerta
                    if dias_fim <= 0:
                        cor_r = "#EF4444"
                        alerta_r = "🔴 EXPIRADO"
                    elif dias_fim <= 30:
                        cor_r = "#EF4444"
                        alerta_r = f"🔴 Expira em {dias_fim} dias!"
                    elif dias_fim <= 60:
                        cor_r = "#F59E0B"
                        alerta_r = f"⚠️ Expira em {dias_fim} dias"
                    else:
                        cor_r = "#10B981"
                        alerta_r = f"✅ {dias_fim} dias restantes"

                    # Progresso do contrato
                    try:
                        ini_d = datetime.strptime(
                            row.get('Data_Inicio',''), "%d/%m/%Y"
                        ).date()
                        fim_d = datetime.strptime(
                            row.get('Data_Fim',''), "%d/%m/%Y"
                        ).date()
                        total_dias = (fim_d - ini_d).days
                        decorridos = (date.today() - ini_d).days
                        pct_prog   = min(
                            100,
                            max(0, decorridos/total_dias*100)
                        ) if total_dias > 0 else 0
                    except:
                        pct_prog = 0

                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:12px;padding:14px 16px;"
                        f"margin-bottom:10px;"
                        f"border-left:4px solid {cor_r};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;"
                        f"align-items:flex-start;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;font-size:0.95rem;'>"
                        f"🚗 {row.get('Matricula','')} — "
                        f"{row.get('Marca','')} "
                        f"{row.get('Modelo','')}</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"🏦 {row.get('Banco','')} · "
                        f"{row.get('Data_Inicio','')} → "
                        f"{row.get('Data_Fim','')} · "
                        f"{km_c:,} km/ano</small><br>"
                        f"<small style='color:{cor_r};'>"
                        f"{alerta_r}</small>"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<b style='color:#3B82F6;"
                        f"font-size:1.1rem;'>"
                        f"€{renda:,.2f}/mês</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"Resto: €{total_rest:,.0f}</small>"
                        f"</div></div>"
                        f"<div style='background:#0F172A;"
                        f"border-radius:4px;height:6px;"
                        f"margin:8px 0 4px;'>"
                        f"<div style='background:{cor_r};"
                        f"width:{pct_prog:.0f}%;height:6px;"
                        f"border-radius:4px;'></div></div>"
                        f"<small style='color:#475569;'>"
                        f"{pct_prog:.0f}% do contrato decorrido · "
                        f"Obra: {row.get('Obra_Alocada','N/A')}"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

                    # Ações
                    col_ra1, col_ra2, col_ra3 = st.columns(3)
                    with col_ra1:
                        novo_estado_r = st.selectbox(
                            "Estado",
                            ["Ativo","Suspenso","Terminado"],
                            key=f"rest_{rent_id}",
                            label_visibility="collapsed"
                        )
                    with col_ra2:
                        if st.button(
                            "✅ Atualizar",
                            key=f"rupd_{rent_id}",
                            use_container_width=True
                        ):
                            renting_db.loc[
                                renting_db['ID'] == rent_id,
                                'Estado'
                            ] = novo_estado_r
                            save_db(renting_db, "renting_contratos.csv")
                            inv("renting_contratos.csv"); st.rerun()
                    with col_ra3:
                        if row.get('Obra_Alocada',''):
                            st.markdown(
                                f"<small style='color:#3B82F6;'>"
                                f"📍 {row.get('Obra_Alocada','')}"
                                f"</small>",
                                unsafe_allow_html=True
                            )

    # ════════════════════════════════════════════════════════════════
    # TAB — COMBUSTÍVEL & KM
    # ════════════════════════════════════════════════════════════════
    with t_comb:
        st.markdown("### ⛽ Combustível & Quilómetros")

        # Gráficos topo
        col_gc1, col_gc2 = st.columns(2)
        with col_gc1:
            st.plotly_chart(
                _grafico_custos_frota_mensal(comb_db, renting_db),
                use_container_width=True
            )
        with col_gc2:
            fig_km = _grafico_km_vs_contratado(renting_db, comb_db)
            if fig_km:
                st.plotly_chart(
                    fig_km, use_container_width=True
                )
            else:
                st.info("📋 Regista abastecimentos para ver análise de KM.")

        st.markdown("---")

        # Registo de abastecimento
        col_reg_c, col_hist_c = st.columns([1, 2])

        with col_reg_c:
            st.markdown("#### ➕ Registo de Abastecimento")

            # Lista de viaturas (renting + frota)
            mats_rent = renting_db['Matricula'].tolist() \
                        if not renting_db.empty and \
                           'Matricula' in renting_db.columns else []
            mats_frot = frota_db['Matricula'].tolist() \
                        if not frota_db.empty and \
                           'Matricula' in frota_db.columns else []
            mats_all  = list(dict.fromkeys(mats_rent + mats_frot))

            with st.form("form_comb_fat"):
                cb_mat = st.selectbox(
                    "Viatura *",
                    mats_all if mats_all else ["Sem viaturas"],
                    key="cb_mat_fat"
                )
                col_cd1, col_cd2 = st.columns(2)
                with col_cd1:
                    cb_data = st.date_input(
                        "Data", value=date.today(), key="cb_data_fat"
                    )
                    cb_lit  = st.number_input(
                        "Litros *",
                        min_value=0.0, step=0.5, key="cb_lit_fat"
                    )
                with col_cd2:
                    cb_val = st.number_input(
                        "Valor (€) *",
                        min_value=0.0, step=0.01, key="cb_val_fat"
                    )
                    cb_km  = st.number_input(
                        "KM Atual",
                        min_value=0, key="cb_km_fat"
                    )
                cb_tipo = st.selectbox(
                    "Combustível",
                    ["Gasóleo","Gasolina 95",
                     "Gasolina 98","Elétrico"],
                    key="cb_tipo_fat"
                )

                # Preview €/L
                if cb_lit > 0 and cb_val > 0:
                    st.markdown(
                        f"<small style='color:#3B82F6;'>"
                        f"💧 €{cb_val/cb_lit:.3f}/litro</small>",
                        unsafe_allow_html=True
                    )

                cb_recibo = st.file_uploader(
                    "Recibo (foto/PDF)",
                    type=["jpg","jpeg","png","pdf"],
                    key="cb_recibo_fat"
                )

                if st.form_submit_button(
                    "💾 Registar Abastecimento",
                    use_container_width=True, type="primary"
                ):
                    if cb_lit <= 0 or cb_val <= 0:
                        st.error("❌ Litros e valor obrigatórios.")
                    else:
                        rec_b64 = ""
                        if cb_recibo:
                            rec_b64 = base64.b64encode(
                                cb_recibo.read()
                            ).decode()
                        novo_cb = pd.DataFrame([{
                            "ID":        str(uuid.uuid4())[:8].upper(),
                            "Data":      cb_data.strftime("%d/%m/%Y"),
                            "Matricula": cb_mat,
                            "Condutor":  user_nome,
                            "Litros":    cb_lit,
                            "Valor":     cb_val,
                            "KM":        cb_km,
                            "Tipo_Comb": cb_tipo,
                            "Recibo_b64":rec_b64
                        }])
                        upd_cb = pd.concat(
                            [comb_db, novo_cb], ignore_index=True
                        ) if not comb_db.empty else novo_cb
                        save_db(upd_cb, "frota_combustivel.csv")
                        inv("frota_combustivel.csv")
                        st.success(
                            f"✅ {cb_lit}L em {cb_mat} — "
                            f"€{cb_val:.2f}"
                        )
                        st.rerun()

        with col_hist_c:
            st.markdown("#### 📊 Análise por Viatura")

            if comb_db.empty:
                st.info("📋 Sem abastecimentos registados.")
            else:
                # Selector viatura
                mats_comb = comb_db['Matricula'].unique().tolist() \
                            if 'Matricula' in comb_db.columns else []
                if mats_comb:
                    mat_sel = st.selectbox(
                        "Viatura",
                        mats_comb,
                        key="comb_mat_sel"
                    )

                    # Gráfico consumo
                    fig_cons = _grafico_consumo_viatura(
                        comb_db, mat_sel
                    )
                    if fig_cons:
                        st.plotly_chart(
                            fig_cons, use_container_width=True
                        )

                    # Stats desta viatura
                    cb_viat = comb_db[
                        comb_db['Matricula'] == mat_sel
                    ].copy()
                    tot_l  = pd.to_numeric(
                        cb_viat.get('Litros',0), errors='coerce'
                    ).fillna(0).sum()
                    tot_v  = pd.to_numeric(
                        cb_viat.get('Valor',0), errors='coerce'
                    ).fillna(0).sum()
                    media_l_eur = tot_v / tot_l if tot_l > 0 else 0

                    # KM percorridos
                    kms = pd.to_numeric(
                        cb_viat.get('KM',0), errors='coerce'
                    ).dropna()
                    km_total = (
                        kms.max() - kms.min()
                    ) if len(kms) >= 2 else 0
                    consumo_100 = (
                        tot_l / km_total * 100
                    ) if km_total > 0 else 0

                    c1,c2,c3 = st.columns(3)
                    with c1:
                        st.metric("⛽ Total Litros",
                                   f"{tot_l:.0f}L")
                    with c2:
                        st.metric("💰 Total Gasto",
                                   f"€{tot_v:.2f}")
                    with c3:
                        st.metric("🚗 KM Registados",
                                   f"{km_total:.0f}")

                    if consumo_100 > 0:
                        st.markdown(
                            f"<div style='background:rgba(59,130,246,0.1);"
                            f"border:1px solid #3B82F6;"
                            f"border-radius:8px;padding:10px;'>"
                            f"<b style='color:#3B82F6;'>"
                            f"📊 Consumo médio: "
                            f"{consumo_100:.1f}L/100km · "
                            f"€{media_l_eur:.3f}/L</b>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                    # Alerta excesso KM
                    if not renting_db.empty and \
                       'Matricula' in renting_db.columns:
                        rent_row = renting_db[
                            renting_db['Matricula'] == mat_sel
                        ]
                        if not rent_row.empty:
                            km_ano_c = float(
                                rent_row.iloc[0].get('KM_Ano',0) or 0
                            )
                            preco_exc = float(
                                rent_row.iloc[0].get(
                                    'KM_Excedente_Preco',0.12
                                ) or 0.12
                            )
                            if km_total > km_ano_c and km_ano_c > 0:
                                exc = km_total - km_ano_c
                                custo_exc = round(exc * preco_exc, 2)
                                st.error(
                                    f"⚠️ KM EXCEDIDOS! "
                                    f"+{exc:.0f} km × "
                                    f"€{preco_exc}/km = "
                                    f"**€{custo_exc:.2f} extra**"
                                )

    # ════════════════════════════════════════════════════════════════
    # TAB — COMPARADOR TCO
    # ════════════════════════════════════════════════════════════════
    with t_tco:
        st.markdown("### 📊 Comparador Renting vs Compra (TCO)")
        st.info(
            "TCO — Total Cost of Ownership. "
            "Compara o custo total de posse ao longo do contrato, "
            "incluindo todos os encargos implícitos e explícitos. "
            "O impacto fiscal também é considerado."
        )

        col_tco1, col_tco2 = st.columns(2)

        with col_tco1:
            st.markdown(
                "<div style='background:rgba(59,130,246,0.1);"
                "border:1px solid #3B82F6;border-radius:10px;"
                "padding:14px;margin-bottom:12px;'>"
                "<b style='color:#3B82F6;'>🏦 RENTING</b>"
                "</div>",
                unsafe_allow_html=True
            )
            tco_renda   = st.number_input(
                "Renda mensal (€)",
                min_value=0.0, value=600.0, step=50.0,
                key="tco_renda"
            )
            tco_anos    = st.slider(
                "Anos do contrato", 1, 7, 3,
                key="tco_anos"
            )
            tco_km_ano  = st.number_input(
                "KM/ano contratados",
                min_value=0, value=20000, step=1000,
                key="tco_km"
            )
            tco_km_exc_p = st.number_input(
                "€/km excedente",
                min_value=0.0, value=0.12, step=0.01,
                key="tco_km_exc"
            )

        with col_tco2:
            st.markdown(
                "<div style='background:rgba(139,92,246,0.1);"
                "border:1px solid #8B5CF6;border-radius:10px;"
                "padding:14px;margin-bottom:12px;'>"
                "<b style='color:#8B5CF6;'>🛒 COMPRA FINANCIADA</b>"
                "</div>",
                unsafe_allow_html=True
            )
            tco_preco   = st.number_input(
                "Preço de compra (€)",
                min_value=0.0, value=35000.0, step=1000.0,
                key="tco_preco"
            )
            tco_juro    = st.number_input(
                "Taxa de juro anual (%)",
                min_value=0.0, max_value=20.0,
                value=5.5, step=0.1,
                key="tco_juro"
            )
            tco_vr_pct  = st.number_input(
                "Valor residual (%)",
                min_value=0.0, max_value=50.0,
                value=20.0, step=1.0,
                key="tco_vr"
            )

        if st.button(
            "📊 Calcular TCO",
            key="btn_tco",
            type="primary",
            use_container_width=True
        ):
            tco_r = _calcular_tco_renting(
                tco_renda, tco_anos, tco_km_ano, tco_km_exc_p
            )
            tco_c = _calcular_tco_compra(
                tco_preco, tco_anos, tco_km_ano,
                tco_juro, tco_vr_pct
            )

            st.session_state['tco_r'] = tco_r
            st.session_state['tco_c'] = tco_c
            st.session_state['tco_anos_calc'] = tco_anos

        if st.session_state.get('tco_r') and \
           st.session_state.get('tco_c'):
            tco_r = st.session_state['tco_r']
            tco_c = st.session_state['tco_c']
            anos_c = st.session_state.get('tco_anos_calc', 3)

            # Gráfico comparação
            st.plotly_chart(
                _grafico_tco_comparacao(tco_r, tco_c, anos_c),
                use_container_width=True
            )

            # Resumo lado a lado
            col_tr, col_tc = st.columns(2)
            with col_tr:
                diff = tco_r['total'] - tco_c['total']
                cor_r = "#10B981" if tco_r['total'] <= tco_c['total'] \
                        else "#EF4444"
                st.markdown(
                    f"<div style='background:rgba(59,130,246,0.1);"
                    f"border:2px solid {cor_r};"
                    f"border-radius:12px;padding:16px;'>"
                    f"<b style='color:#3B82F6;"
                    f"font-size:1rem;'>🏦 RENTING</b>"
                    f"{'<span style=float:right;color:#10B981;>✅ MAIS BARATO</span>' if tco_r['total'] <= tco_c['total'] else ''}"
                    f"<br><br>",
                    unsafe_allow_html=True
                )
                items_r = [
                    ("Rendas totais",    tco_r['total_rendas']),
                    ("Seguros est.",     tco_r['custo_seguros']),
                    ("Manutenção",       0),
                ]
                for label, val in items_r:
                    st.markdown(
                        f"<div style='display:flex;"
                        f"justify-content:space-between;margin:4px 0;'>"
                        f"<small style='color:#94A3B8;'>{label}</small>"
                        f"<small style='color:#F1F5F9;'>"
                        f"€{val:,.2f}</small></div>",
                        unsafe_allow_html=True
                    )
                st.markdown(
                    f"<div style='border-top:1px solid #334155;"
                    f"padding-top:8px;margin-top:8px;"
                    f"display:flex;justify-content:space-between;'>"
                    f"<b style='color:#F1F5F9;'>TOTAL</b>"
                    f"<b style='color:{cor_r};"
                    f"font-size:1.1rem;'>"
                    f"€{tco_r['total']:,.2f}</b></div>"
                    f"<br><small style='color:#64748B;'>"
                    f"€{tco_r['custo_mes']:,.2f}/mês · "
                    f"€{tco_r['custo_km']:.4f}/km</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            with col_tc:
                cor_c = "#10B981" if tco_c['total'] < tco_r['total'] \
                        else "#EF4444"
                st.markdown(
                    f"<div style='background:rgba(139,92,246,0.1);"
                    f"border:2px solid {cor_c};"
                    f"border-radius:12px;padding:16px;'>"
                    f"<b style='color:#8B5CF6;"
                    f"font-size:1rem;'>🛒 COMPRA</b>"
                    f"{'<span style=float:right;color:#10B981;>✅ MAIS BARATO</span>' if tco_c['total'] < tco_r['total'] else ''}"
                    f"<br><br>",
                    unsafe_allow_html=True
                )
                items_c = [
                    ("Amortização",     tco_c['preco_compra'] - tco_c['valor_residual']),
                    ("Juros est.",      tco_c['juros_total']),
                    ("Manutenção est.", tco_c['manut_total']),
                    ("Seguros est.",    tco_c['seguro_total']),
                    ("- Valor Residual",
                     -tco_c['valor_residual']),
                ]
                for label, val in items_c:
                    cor_item = "#EF4444" if val < 0 else "#F1F5F9"
                    st.markdown(
                        f"<div style='display:flex;"
                        f"justify-content:space-between;margin:4px 0;'>"
                        f"<small style='color:#94A3B8;'>{label}</small>"
                        f"<small style='color:{cor_item};'>"
                        f"{'€' if val>=0 else '-€'}"
                        f"{abs(val):,.2f}</small></div>",
                        unsafe_allow_html=True
                    )
                st.markdown(
                    f"<div style='border-top:1px solid #334155;"
                    f"padding-top:8px;margin-top:8px;"
                    f"display:flex;justify-content:space-between;'>"
                    f"<b style='color:#F1F5F9;'>TOTAL</b>"
                    f"<b style='color:{cor_c};"
                    f"font-size:1.1rem;'>"
                    f"€{tco_c['total']:,.2f}</b></div>"
                    f"<br><small style='color:#64748B;'>"
                    f"€{tco_c['custo_mes']:,.2f}/mês · "
                    f"€{tco_c['custo_km']:.4f}/km</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            # Veredito
            poupanca = abs(tco_r['total'] - tco_c['total'])
            vencedor = "Renting" if tco_r['total'] <= tco_c['total'] \
                       else "Compra"
            cor_v = "#10B981"

            st.markdown(
                f"<div style='background:rgba(16,185,129,0.1);"
                f"border:2px solid #10B981;border-radius:12px;"
                f"padding:16px;margin-top:12px;text-align:center;'>"
                f"<b style='color:#10B981;font-size:1.1rem;'>"
                f"✅ {vencedor} é mais económico</b><br>"
                f"<b style='color:#F1F5F9;font-size:1.5rem;'>"
                f"Poupança: €{poupanca:,.2f} em {anos_c} anos</b><br>"
                f"<small style='color:#94A3B8;'>"
                f"(€{poupanca/(anos_c*12):,.2f}/mês)</small>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Nota fiscal
            st.markdown(
                "<div style='background:rgba(59,130,246,0.08);"
                "border-radius:8px;padding:12px;margin-top:8px;'>"
                "<small style='color:#93C5FD;'>"
                "📋 <b>Nota fiscal:</b> No renting, a renda é "
                "dedutível como custo (reduz IRC). Na compra, "
                "só a amortização e juros são dedutíveis. "
                "Consulta o teu contabilista para o impacto "
                "fiscal específico.</small></div>",
                unsafe_allow_html=True
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — SEGUROS FROTA
    # ════════════════════════════════════════════════════════════════
    with t_seguros:
        st.markdown("### 🛡️ Seguros de Frota")

        col_sf1, col_sf2 = st.columns([1, 2])

        with col_sf1:
            st.markdown("#### ➕ Registar Seguro")
            with st.form("form_seg_frota"):
                s_tipo = st.selectbox(
                    "Tipo *",
                    ["Seguro Automóvel (RC Obrigatório)",
                     "Seguro Automóvel (Danos Próprios)",
                     "Seguro Frota Completo",
                     "Seguro Acidentes Ocupantes",
                     "Outro"],
                    key="sf_tipo"
                )
                s_seg = st.text_input(
                    "Seguradora *", key="sf_seg"
                )
                s_viat = st.selectbox(
                    "Viatura",
                    ["Todas (frota)"] + (
                        renting_db['Matricula'].tolist()
                        if not renting_db.empty and
                           'Matricula' in renting_db.columns
                        else []
                    ) + (
                        frota_db['Matricula'].tolist()
                        if not frota_db.empty and
                           'Matricula' in frota_db.columns
                        else []
                    ),
                    key="sf_viat"
                )
                s_apolice = st.text_input(
                    "Nº Apólice", key="sf_apolice"
                )
                s_val = st.number_input(
                    "Prémio Anual (€)",
                    min_value=0.0, step=50.0,
                    key="sf_val"
                )
                col_sd1, col_sd2 = st.columns(2)
                with col_sd1:
                    s_ini = st.date_input(
                        "Início", value=date.today(), key="sf_ini"
                    )
                with col_sd2:
                    s_fim = st.date_input(
                        "Fim",
                        value=date.today() + timedelta(days=365),
                        key="sf_fim"
                    )

                if st.form_submit_button(
                    "💾 Guardar Seguro",
                    use_container_width=True, type="primary"
                ):
                    if not s_seg.strip():
                        st.error("❌ Seguradora obrigatória.")
                    else:
                        novo_s = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Tipo":        s_tipo,
                            "Entidade":    s_seg.strip(),
                            "Viatura":     s_viat,
                            "Valor_Anual": s_val,
                            "Data_Inicio": s_ini.strftime("%d/%m/%Y"),
                            "Data_Fim":    s_fim.strftime("%d/%m/%Y"),
                            "Apolice":     s_apolice.strip()
                        }])
                        upd_s = pd.concat(
                            [seguros_db, novo_s], ignore_index=True
                        ) if not seguros_db.empty else novo_s
                        save_db(upd_s, "seguros_db.csv")
                        inv("seguros_db.csv")
                        st.success("✅ Seguro registado!")
                        st.rerun()

        with col_sf2:
            st.markdown("#### 📋 Seguros Ativos")
            if seguros_db.empty:
                st.info("📋 Sem seguros registados.")
            else:
                total_premios = pd.to_numeric(
                    seguros_db.get('Valor_Anual',0),
                    errors='coerce'
                ).fillna(0).sum()
                st.metric(
                    "💰 Total Prémios Anuais",
                    f"€{total_premios:,.2f}"
                )

                for _, seg in seguros_db.iterrows():
                    dias_s  = _dias_para(seg.get('Data_Fim',''))
                    if dias_s <= 0:
                        cor_s   = "#EF4444"
                        alerta_s = "🔴 EXPIRADO"
                    elif dias_s <= 30:
                        cor_s   = "#EF4444"
                        alerta_s = f"🔴 Expira em {dias_s} dias!"
                    elif dias_s <= 60:
                        cor_s   = "#F59E0B"
                        alerta_s = f"⚠️ Expira em {dias_s} dias"
                    else:
                        cor_s   = "#10B981"
                        alerta_s = f"✅ Válido ({dias_s}d)"

                    val_s = float(seg.get('Valor_Anual',0) or 0)
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:12px;"
                        f"margin-bottom:8px;"
                        f"border-left:4px solid {cor_s};'>"
                        f"<b style='color:#F1F5F9;'>"
                        f"{seg.get('Tipo','')[:40]}</b>"
                        f"<span style='float:right;color:{cor_s};'>"
                        f"{alerta_s}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"🏢 {seg.get('Entidade','')} · "
                        f"🚗 {seg.get('Viatura','')} · "
                        f"Apólice: {seg.get('Apolice','')} · "
                        f"{seg.get('Data_Inicio','')} → "
                        f"{seg.get('Data_Fim','')} · "
                        f"€{val_s:,.2f}/ano"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

    # ════════════════════════════════════════════════════════════════
    # TAB — RELATÓRIO FINANCEIRO FROTA
    # ════════════════════════════════════════════════════════════════
    with t_relatorio:
        st.markdown("### 📋 Relatório Financeiro da Frota")

        col_rel1, col_rel2 = st.columns(2)
        with col_rel1:
            mes_rel = st.selectbox(
                "Mês",
                ["Janeiro","Fevereiro","Março","Abril","Maio",
                 "Junho","Julho","Agosto","Setembro",
                 "Outubro","Novembro","Dezembro"],
                index=date.today().month - 1,
                key="rel_frota_mes"
            )
        with col_rel2:
            ano_rel = st.number_input(
                "Ano", min_value=2020,
                value=date.today().year,
                key="rel_frota_ano"
            )

        mes_rel_num = ["Janeiro","Fevereiro","Março","Abril","Maio",
                        "Junho","Julho","Agosto","Setembro",
                        "Outubro","Novembro","Dezembro"
                       ].index(mes_rel) + 1

        # Calcular totais do mês
        comb_mes_val = 0.0
        comb_mes_lit = 0.0
        if not comb_db.empty and 'Data' in comb_db.columns:
            cb_m2 = comb_db.copy()
            cb_m2['Data_d'] = pd.to_datetime(
                cb_m2['Data'], dayfirst=True, errors='coerce'
            )
            mask_m = (
                (cb_m2['Data_d'].dt.month == mes_rel_num) &
                (cb_m2['Data_d'].dt.year  == ano_rel)
            )
            cb_mes = cb_m2[mask_m]
            comb_mes_val = pd.to_numeric(
                cb_mes.get('Valor',0), errors='coerce'
            ).fillna(0).sum()
            comb_mes_lit = pd.to_numeric(
                cb_mes.get('Litros',0), errors='coerce'
            ).fillna(0).sum()

        renda_mes = renda_total  # mensal fixo

        seg_mensal = 0.0
        if not seguros_db.empty and 'Valor_Anual' in seguros_db.columns:
            seg_mensal = pd.to_numeric(
                seguros_db['Valor_Anual'], errors='coerce'
            ).fillna(0).sum() / 12

        total_frota_mes = renda_mes + comb_mes_val + seg_mensal

        # KPIs
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("🏦 Rendas",     f"€{renda_mes:,.2f}")
        with c2: st.metric("⛽ Combustível", f"€{comb_mes_val:,.2f}")
        with c3: st.metric("🛡️ Seguros",    f"€{seg_mensal:,.2f}")
        with c4: st.metric("💸 TOTAL",      f"€{total_frota_mes:,.2f}")

        # Detalhe por viatura
        st.markdown("---")
        st.markdown("#### 🚗 Custo por Viatura")

        viaturas_all = list(set(
            (renting_db['Matricula'].tolist()
             if not renting_db.empty and
                'Matricula' in renting_db.columns else []) +
            (frota_db['Matricula'].tolist()
             if not frota_db.empty and
                'Matricula' in frota_db.columns else [])
        ))

        rows_rel = []
        for mat in viaturas_all:
            # Renda
            renda_v = 0.0
            if not renting_db.empty and \
               'Matricula' in renting_db.columns:
                r_row = renting_db[
                    renting_db['Matricula'] == mat
                ]
                if not r_row.empty:
                    renda_v = float(
                        r_row.iloc[0].get('Valor_Mensal',0) or 0
                    )

            # Combustível
            comb_v = 0.0
            lits_v = 0.0
            if not comb_db.empty and 'Matricula' in comb_db.columns:
                cb_v = comb_db[
                    comb_db['Matricula'] == mat
                ].copy()
                cb_v['Data_d'] = pd.to_datetime(
                    cb_v['Data'], dayfirst=True, errors='coerce'
                )
                mask_v = (
                    (cb_v['Data_d'].dt.month == mes_rel_num) &
                    (cb_v['Data_d'].dt.year  == ano_rel)
                )
                comb_v = pd.to_numeric(
                    cb_v[mask_v].get('Valor',0), errors='coerce'
                ).fillna(0).sum()
                lits_v = pd.to_numeric(
                    cb_v[mask_v].get('Litros',0), errors='coerce'
                ).fillna(0).sum()

            total_v = renda_v + comb_v
            rows_rel.append({
                "Matrícula":   mat,
                "Renda":       f"€{renda_v:,.2f}",
                "Combustível": f"€{comb_v:,.2f} ({lits_v:.0f}L)",
                "Total Mês":   f"€{total_v:,.2f}",
            })

        if rows_rel:
            df_rel = pd.DataFrame(rows_rel)
            st.dataframe(
                df_rel, use_container_width=True, hide_index=True
            )

            # Export
            csv_rel = df_rel.to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                f"📥 Exportar Relatório Frota {mes_rel} {ano_rel}",
                data=csv_rel.encode('utf-8-sig'),
                file_name=(
                    f"relatorio_frota_"
                    f"{mes_rel_num:02d}_{ano_rel}.csv"
                ),
                mime="text/csv",
                key="dl_rel_frota"
            )

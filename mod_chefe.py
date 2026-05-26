"""
GESTNOW v3 — mod_chefe.py
Módulo do Chefe de Equipa / Gestor — Layout Profissional v2
Fixes: inputs fundo branco · validar horas desktop · histórico mensal · folha ponto completa
"""
import streamlit as st
import pandas as pd
import uuid, secrets, base64, io, json
from datetime import datetime, timedelta, date
import time

from core import (
    save_db, inv, fh, sl, load_db,
    ICONS, COLORS, TIPOS_FRENTE, REGRAS_OURO,
    log_audit, criar_notificacao, process_and_compress_image,
    hp, _load_users_cached
)
from translations import t

# ── Constantes visuais ────────────────────────────────────────────────────────
_DOT_COLOR = {
    "0":  "#F97316", "1":  "#10B981", "2":  "#3B82F6",
    "3":  "#6B7280", "4":  "#6B7280", "-1": "#EF4444",
}
_DOT_LABEL = {
    "0": "Pendente", "1": "Validado", "2": "Faturação",
    "3": "Pago", "4": "Pago", "-1": "Rejeitado",
}
_STATUS_ICON = {
    "0": "🟠", "1": "🟢", "2": "🔵", "3": "⚫", "4": "⚫", "-1": "🔴",
}
_MESES_PT   = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
_DIAS_LETRA = ['D','S','T','Q','Q','S','S']
_HORAS_30   = [f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)]


def _load_users_fresh():
    return _load_users_cached()


# =============================================================================
# FOLHA DE PONTO — gerador HTML para download / preview
# =============================================================================
def _gerar_html_folha(obra, periodo_str, regs_df, responsavel,
                      empresa="Correia, Plácido e Sousa, Lda.",
                      nif_empresa="517182718",
                      logo_b64: str = ""):
    """
    Gera HTML profissional da folha de ponto para preview e download.
    logo_b64: opcional — base64 da imagem PNG/JPG do logotipo CPS.
    """
    # ── Agrupar por técnico e calcular totais ──────────────────────────────
    total_h = 0.0
    tec_map: dict = {}   # tec → list de rows
    if not regs_df.empty:
        df_h = regs_df.copy()
        for col in ['Data', 'Frente', 'Turnos', 'Relatorio', 'Técnico']:
            if col not in df_h.columns:
                df_h[col] = '—'
        df_h['Horas_Total'] = pd.to_numeric(df_h['Horas_Total'], errors='coerce').fillna(0)
        total_h = float(df_h['Horas_Total'].sum())
        for tec, grp in df_h.groupby('Técnico', sort=False):
            tec_map[str(tec)] = [
                {
                    'data':   str(r.get('Data',      '—') or '—'),
                    'frente': str(r.get('Frente',    '—') or '—'),
                    'turno':  str(r.get('Turnos',    '—') or '—'),
                    'horas':  r.get('Horas_Total',   0),
                    'relat':  str(r.get('Relatorio', '') or '')[:80],
                }
                for r in grp.to_dict('records')
            ]

    # ── Linhas da tabela agrupadas por técnico ─────────────────────────────
    rows_html = ""
    for tec, regs in tec_map.items():
        tec_h = sum(r['horas'] for r in regs)
        first = True
        for rr in regs:
            bg = "#F8FAFC" if first else "#FFFFFF"
            rows_html += f"""
            <tr style="background:{bg}">
              {'<td rowspan="' + str(len(regs)) + '" style="vertical-align:middle;font-weight:700;color:#1E293B;border-right:2px solid #E2E8F0;background:#F1F5F9;font-size:12px;">' + tec + '</td>' if first else ''}
              <td style="font-size:12px;color:#475569">{rr['data']}</td>
              <td style="font-size:12px">{rr['frente']}</td>
              <td style="text-align:center;font-size:12px;color:#475569">{rr['turno']}</td>
              <td style="text-align:center;font-weight:700;color:#1E40AF;font-size:12px">{fh(rr['horas'])}</td>
              <td style="font-size:11px;color:#64748B">{rr['relat']}</td>
            </tr>"""
            first = False
        rows_html += f"""
        <tr style="background:#EFF6FF">
          <td colspan="4" style="text-align:right;font-size:11px;
              color:#1E40AF;font-weight:700;padding:4px 12px;
              border-top:1px dashed #BFDBFE;">
              Total {tec.split()[0]}
          </td>
          <td style="text-align:center;font-weight:900;color:#1E40AF;
              border-top:1px dashed #BFDBFE;">{fh(tec_h)}</td>
          <td style="border-top:1px dashed #BFDBFE;"></td>
        </tr>"""

    ts_gera  = datetime.now().strftime("%d/%m/%Y %H:%M")
    doc_num  = f"FP-{datetime.now().strftime('%Y%m')}-{secrets.token_hex(3).upper()}"
    n_tecs   = len(tec_map)
    n_regs   = sum(len(v) for v in tec_map.values())

    # Logo: imagem real ou bloco de texto profissional
    if logo_b64 and len(logo_b64) > 100:
        logo_html = f"""<img src="data:image/png;base64,{logo_b64}"
            style="height:60px;object-fit:contain;" alt="CPS Logo">"""
    else:
        logo_html = """
        <div style="display:inline-flex;align-items:center;gap:8px;">
          <div style="width:50px;height:50px;background:#DC2626;border-radius:8px;
              display:flex;align-items:center;justify-content:center;
              font-weight:900;color:white;font-size:18px;letter-spacing:-1px;">CPS</div>
          <div>
            <div style="font-size:14px;font-weight:900;color:#1E293B;
                letter-spacing:0.02em;">CORREIA, PLÁCIDO E SOUSA</div>
            <div style="font-size:10px;color:#64748B;letter-spacing:0.05em;">
                INSTRUMENTAÇÃO INDUSTRIAL, LDA.</div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Folha de Ponto — {obra}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  @page {{ size: A4; margin: 15mm 12mm; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #1E293B; background: white;
    font-size: 13px; line-height: 1.5;
  }}
  /* ── Cabeçalho ── */
  .page-header {{
    display: flex; justify-content: space-between; align-items: flex-start;
    border-bottom: 3px solid #DC2626; padding-bottom: 16px; margin-bottom: 20px;
  }}
  .doc-info {{ text-align: right; }}
  .doc-title {{
    font-size: 20px; font-weight: 900; color: #DC2626;
    letter-spacing: -0.02em; margin-bottom: 2px;
  }}
  .doc-num {{
    font-size: 11px; color: #64748B; font-family: monospace;
  }}
  /* ── Faixa de obra ── */
  .obra-banner {{
    background: #1E293B; color: white; border-radius: 10px;
    padding: 14px 20px; margin-bottom: 16px;
    display: flex; justify-content: space-between; align-items: center;
  }}
  .obra-name {{ font-size: 17px; font-weight: 800; }}
  .obra-periodo {{ font-size: 12px; color: #94A3B8; margin-top: 2px; }}
  .obra-badge {{
    background: #DC2626; border-radius: 8px;
    padding: 8px 16px; text-align: center;
  }}
  .obra-badge-h {{ font-size: 22px; font-weight: 900; }}
  .obra-badge-lbl {{ font-size: 10px; color: rgba(255,255,255,0.7);
                     text-transform: uppercase; letter-spacing: 0.05em; }}
  /* ── Meta grid ── */
  .meta-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 8px; margin-bottom: 18px;
  }}
  .meta-cell {{
    background: #F8FAFC; border: 1px solid #E2E8F0;
    border-radius: 8px; padding: 10px 12px;
  }}
  .meta-lbl {{ font-size: 10px; color: #64748B; font-weight: 700;
               text-transform: uppercase; letter-spacing: 0.05em; }}
  .meta-val {{ font-size: 14px; font-weight: 700; color: #1E293B; margin-top: 2px; }}
  /* ── Tabela ── */
  .section-title {{
    font-size: 11px; font-weight: 700; color: #DC2626;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 6px; padding-left: 4px;
  }}
  table {{ width: 100%; border-collapse: collapse; border-radius: 10px;
           overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  thead tr {{ background: #1E293B; }}
  th {{
    padding: 10px 12px; text-align: left; color: white;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #E2E8F0; }}
  .total-final td {{
    background: #1E293B !important; color: white !important;
    font-weight: 900; font-size: 13px;
    border-top: 2px solid #DC2626;
  }}
  /* ── Assinaturas ── */
  .sig-section {{
    margin-top: 40px;
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 30px;
  }}
  .sig-box {{ text-align: center; }}
  .sig-area {{
    height: 70px; border-bottom: 2px solid #1E293B;
    margin-bottom: 8px; position: relative;
  }}
  .sig-label {{ font-size: 11px; color: #64748B; }}
  .sig-name {{ font-size: 12px; font-weight: 700; color: #1E293B; margin-top: 2px; }}
  /* ── Selo ── */
  .seal-box {{
    margin-top: 24px; background: #F0FDF4;
    border: 1.5px dashed #10B981; border-radius: 8px;
    padding: 10px 16px; display: flex; align-items: center; gap: 14px;
  }}
  .seal-icon {{ font-size: 24px; flex-shrink: 0; }}
  .seal-text {{ font-family: monospace; font-size: 11px; color: #065F46; }}
  /* ── Footer ── */
  .page-footer {{
    margin-top: 20px; padding-top: 10px;
    border-top: 1px solid #E2E8F0;
    display: flex; justify-content: space-between;
    font-size: 10px; color: #94A3B8;
  }}
  @media print {{
    body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>

<!-- CABEÇALHO -->
<div class="page-header">
  <div>{logo_html}</div>
  <div class="doc-info">
    <div class="doc-title">Folha de Ponto</div>
    <div class="doc-num">Nº {doc_num}</div>
    <div style="font-size:11px;color:#94A3B8;margin-top:4px;">
      Gerado em {ts_gera}
    </div>
  </div>
</div>

<!-- FAIXA OBRA -->
<div class="obra-banner">
  <div>
    <div class="obra-name">🏭 {obra}</div>
    <div class="obra-periodo">📅 {periodo_str}</div>
  </div>
  <div class="obra-badge">
    <div class="obra-badge-h">{fh(total_h)}</div>
    <div class="obra-badge-lbl">Total Horas</div>
  </div>
</div>

<!-- META GRID -->
<div class="meta-grid">
  <div class="meta-cell">
    <div class="meta-lbl">Responsável</div>
    <div class="meta-val">{responsavel}</div>
  </div>
  <div class="meta-cell">
    <div class="meta-lbl">Técnicos</div>
    <div class="meta-val">{n_tecs}</div>
  </div>
  <div class="meta-cell">
    <div class="meta-lbl">Nº de Registos</div>
    <div class="meta-val">{n_regs}</div>
  </div>
  <div class="meta-cell">
    <div class="meta-lbl">Empresa (NIF)</div>
    <div class="meta-val" style="font-size:11px;">{empresa}<br>
      <span style="color:#64748B;font-weight:400;">NIF {nif_empresa}</span>
    </div>
  </div>
</div>

<!-- TABELA -->
<div class="section-title">📋 Registos de Trabalho</div>
<table>
  <thead>
    <tr>
      <th style="width:16%">Técnico</th>
      <th style="width:12%">Data</th>
      <th style="width:22%">Frente de Trabalho</th>
      <th style="width:14%;text-align:center">Horário</th>
      <th style="width:10%;text-align:center">Horas</th>
      <th>Observações</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
    <tr class="total-final">
      <td colspan="4" style="text-align:right;padding-right:16px;">
          TOTAL GERAL
      </td>
      <td style="text-align:center">{fh(total_h)}</td>
      <td>{n_regs} registo(s) · {n_tecs} técnico(s)</td>
    </tr>
  </tbody>
</table>

<!-- ASSINATURAS -->
<div class="sig-section">
  <div class="sig-box">
    <div class="sig-area"></div>
    <div class="sig-label">Chefe de Equipa / Responsável</div>
    <div class="sig-name">{responsavel}</div>
  </div>
  <div class="sig-box">
    <div class="sig-area"></div>
    <div class="sig-label">Representante do Cliente</div>
    <div class="sig-name">&nbsp;</div>
  </div>
  <div class="sig-box">
    <div class="sig-area"></div>
    <div class="sig-label">Data e Carimbo</div>
    <div class="sig-name">&nbsp;</div>
  </div>
</div>

<!-- RODAPÉ -->
<div class="page-footer">
  <span>{empresa} · NIF {nif_empresa}</span>
  <span>GESTNOW v3 · {ts_gera}</span>
  <span>Documento nº {doc_num}</span>
</div>

<script>
// Auto-print quando aberto directamente no browser
// window.onload = () => window.print();
</script>
</body>
</html>"""
    return html, total_h


# =============================================================================
# RENDER PRINCIPAL
# =============================================================================
@st.fragment
def render_chefe(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     *_) = args

    user_nome  = st.session_state.get('user', '')
    user_tipo  = st.session_state.get('tipo', '')
    cargo_user = st.session_state.get('cargo', '')
    hoje       = date.today()

    # ── CSS ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .stApp { background:#0F172A !important; }
    .main .block-container { padding-top:0.5rem !important; }
    h1,h2,h3,h4,h5,h6 { color:#F1F5F9 !important; }
    p,div,span { color:#CBD5E1; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background:#1E293B !important;
        border-bottom:2px solid #334155 !important; gap:0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color:#64748B !important; font-size:0.76rem !important;
        padding:10px 6px !important; background:transparent !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color:#DC2626 !important; font-weight:700 !important;
        border-bottom:3px solid #DC2626 !important;
    }

    /* ── Botões gerais ── */
    .stButton>button {
        border-radius:10px !important; font-weight:600 !important;
        height:40px !important; font-size:0.85rem !important;
    }
    .stButton>button[kind="primary"] {
        background:#DC2626 !important; color:white !important; border:none !important;
    }
    .stButton>button[kind="secondary"] {
        background:#1E293B !important; color:#CBD5E1 !important;
        border:1px solid #334155 !important;
    }

    /* ── Botões calendário (pequenos, circulares) ── */
    .cal-week [data-testid="stHorizontalBlock"] .stButton>button {
        border-radius:50% !important; padding:0 !important;
        height:36px !important; min-height:36px !important;
        width:36px !important; font-size:0.82rem !important;
    }

    /* ── INPUTS — FUNDO BRANCO ── */
    .stTextInput label, .stSelectbox label, .stNumberInput label,
    .stTextArea label, .stDateInput label, .stRadio label, .stCheckbox label {
        color:#CBD5E1 !important; font-size:0.82rem !important;
        font-weight:500 !important;
    }
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stTextArea>div>div>textarea {
        background:#FFFFFF !important; color:#1E293B !important;
        border:1px solid #CBD5E1 !important; border-radius:10px !important;
    }
    .stSelectbox>div>div>div {
        background:#FFFFFF !important; color:#1E293B !important;
        border:1px solid #CBD5E1 !important;
    }
    /* Dropdown list options */
    [data-baseweb="popover"] li {
        background:#FFFFFF !important; color:#1E293B !important;
    }
    [data-baseweb="popover"] li:hover {
        background:#F1F5F9 !important;
    }
    .stDateInput>div>div>input {
        background:#FFFFFF !important; color:#1E293B !important;
        border:1px solid #CBD5E1 !important; border-radius:10px !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background:#1E293B !important; color:#F1F5F9 !important;
        border-radius:10px !important;
    }

    /* ── Ponto cards ── */
    .ponto-card {
        background:#1E3A4A; border-radius:14px;
        padding:16px 18px; margin-bottom:10px;
        box-shadow:0 2px 8px rgba(0,0,0,0.3);
    }
    .ponto-card-header {
        display:flex; justify-content:space-between;
        align-items:flex-start; margin-bottom:10px;
    }
    .ponto-card-title { font-weight:700; color:#F1F5F9; font-size:0.95rem; margin:0; }
    .ponto-card-horas { font-weight:900; color:#F1F5F9; font-size:1.2rem; }
    .ponto-card-status {
        font-size:0.72rem; font-weight:600; padding:2px 8px;
        border-radius:10px; display:inline-block; margin-top:2px;
    }
    .ponto-card-grid {
        display:grid; grid-template-columns:1fr 1fr; gap:6px 16px;
        border-top:1px solid rgba(255,255,255,0.08);
        padding-top:10px; margin-top:4px;
    }
    .ponto-card-label {
        color:#64748B; font-size:0.72rem; font-weight:600;
        text-transform:uppercase; letter-spacing:0.05em;
    }
    .ponto-card-value { color:#CBD5E1; font-size:0.85rem; font-weight:500; }
    .total-horas-bar {
        display:flex; justify-content:space-between; align-items:center;
        padding:12px 4px 8px; border-bottom:1px solid #1E293B; margin-bottom:12px;
    }
    .total-horas-label { color:#64748B; font-size:0.82rem; font-weight:600; }
    .total-horas-value { color:#DC2626; font-size:1.05rem; font-weight:900; }

    /* ── Validação card ── */
    .val-card {
        background:#1E293B; border-radius:14px;
        padding:0; margin-bottom:16px;
        border:1px solid #334155; overflow:hidden;
    }
    .val-card-header {
        background:#162032; padding:14px 18px;
        display:flex; justify-content:space-between; align-items:center;
        border-bottom:1px solid #334155;
    }
    .val-reg-row {
        display:flex; justify-content:space-between; align-items:center;
        padding:10px 18px; border-bottom:1px solid rgba(255,255,255,0.04);
    }
    .val-reg-row:last-child { border-bottom:none; }
    .val-reg-info { flex:1; }
    .val-reg-data { color:#64748B; font-size:0.72rem; font-weight:600;
                    text-transform:uppercase; }
    .val-reg-desc { color:#F1F5F9; font-size:0.88rem; font-weight:500;
                    margin:2px 0; }
    .val-reg-meta { color:#64748B; font-size:0.75rem; }
    .val-reg-horas { color:#F59E0B; font-weight:900; font-size:1rem;
                     white-space:nowrap; margin:0 16px; }

    /* ── Histórico mensal ── */
    .hist-day-cell {
        background:#1E293B; border-radius:8px; padding:8px 6px;
        text-align:center; margin:3px;
    }
    .hist-day-num { font-size:0.75rem; color:#64748B; font-weight:600; }
    .hist-day-h { font-size:0.85rem; font-weight:900; }
    </style>
    """, unsafe_allow_html=True)

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center;padding:20px;
        background:linear-gradient(135deg,#1E293B,#0F172A);
        border-radius:16px;margin-bottom:20px;
        border:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:2rem;margin-bottom:6px;">👷</div>
        <div style="font-size:1.3rem;font-weight:800;color:#F8FAFC;">{user_nome}</div>
        <div style="font-size:0.85rem;color:#94A3B8;">{cargo_user} | {user_tipo}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    inicio_mes = hoje.replace(day=1)
    obras_chefe = []
    if not inst_acessos_db.empty and 'Utilizador' in inst_acessos_db.columns:
        obras_chefe = inst_acessos_db[
            inst_acessos_db['Utilizador'] == user_nome
        ]['Obra'].tolist()

    regs_equipa = pd.DataFrame()
    if not registos_db.empty:
        regs_equipa = (registos_db[registos_db['Obra'].isin(obras_chefe)]
                       if obras_chefe else registos_db.copy())

    pendentes = len(regs_equipa[regs_equipa['Status'] == '0']) \
                if not regs_equipa.empty else 0
    horas_mes = 0
    if not regs_equipa.empty:
        regs_mes = regs_equipa[
            pd.to_datetime(regs_equipa['Data'], dayfirst=True, errors='coerce'
            ).dt.date >= inicio_mes
        ]
        horas_mes = pd.to_numeric(regs_mes['Horas_Total'], errors='coerce'
                                  ).fillna(0).sum()
    num_tec = len(regs_equipa['Técnico'].unique()) if not regs_equipa.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("👷 Técnicos",   num_tec)
    with c2: st.metric("⏱️ Horas Mês",  f"{horas_mes:.0f}h")
    with c3: st.metric("⏳ Pendentes",  pendentes)
    with c4: st.metric("🏭 Obras",
        len(obras_chefe) or (len(obras_db) if not obras_db.empty else 0))

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "👥 Equipa", "✅ Validar Horas", "📋 Meu Ponto",
        "📊 Folha de Ponto", "🛡️ HSE", "📦 Pedidos"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 0 — EQUIPA
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        st.markdown("### 👷 Visão Geral da Equipa")
        if not regs_equipa.empty:
            resumo = regs_equipa.groupby('Técnico').agg(
                Horas     =('Horas_Total', lambda x: pd.to_numeric(x, errors='coerce').sum()),
                Registos  =('Técnico',     'count'),
                Pendentes =('Status',      lambda x: (x == '0').sum()),
                Aprovados =('Status',      lambda x: (x == '1').sum()),
            ).reset_index()
            for _, row in resumo.iterrows():
                cor = "#10B981" if row['Pendentes'] == 0 else "#F59E0B"
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05);padding:14px;
                    border-radius:12px;margin-bottom:8px;border-left:4px solid {cor};">
                    <div style="display:flex;justify-content:space-between;">
                        <div>
                            <b style="color:#F8FAFC;">👤 {row['Técnico']}</b>
                            <div style="color:#94A3B8;font-size:0.82rem;">
                                {row['Registos']} registos · {fh(row['Horas'])} totais
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:#10B981;font-size:0.82rem;">✅ {row['Aprovados']} aprovados</div>
                            <div style="color:#F59E0B;font-size:0.82rem;">⏳ {row['Pendentes']} pendentes</div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("📋 Sem dados de equipa.")

        st.divider()
        st.markdown("### 📣 Comunicado à Equipa")
        with st.form("form_comunicado_chefe"):
            titulo_com   = st.text_input("Título", key="com_ch_titulo")
            conteudo_com = st.text_area("Mensagem", key="com_ch_msg")
            urgente      = st.checkbox("Urgente", key="com_ch_urg")
            if st.form_submit_button("📣 Enviar", use_container_width=True, type="primary"):
                if titulo_com and conteudo_com:
                    novo = pd.DataFrame([{
                        "ID":       str(uuid.uuid4())[:8].upper(),
                        "Titulo":   titulo_com,
                        "Conteudo": conteudo_com,
                        "Tipo":     "Chefe",
                        "Destino":  "Equipa",
                        "Urgente":  "Sim" if urgente else "Não",
                        "Validade": (date.today() + timedelta(days=30)).strftime("%d/%m/%Y"),
                    }])
                    upd = pd.concat([comuns_db, novo], ignore_index=True) \
                          if not comuns_db.empty else novo
                    save_db(upd, "comunicados.csv")
                    inv("comunicados.csv")
                    st.success("✅ Comunicado enviado!")
                    st.session_state['_menu_locked'] = True
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — VALIDAR HORAS
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown("### ✅ Validação de Horas da Equipa")
        sub_p, sub_h = st.tabs(["🟠 Pendentes", "📅 Histórico Mensal"])

        # ── Pendentes ─────────────────────────────────────────────────────────
        with sub_p:
            regs_fmt = pd.DataFrame()
            if not regs_equipa.empty:
                regs_fmt = regs_equipa.copy()
                if pd.api.types.is_datetime64_any_dtype(regs_fmt['Data']):
                    regs_fmt['Data'] = regs_fmt['Data'].dt.strftime('%d/%m/%Y').fillna('—')
                else:
                    regs_fmt['Data'] = regs_fmt['Data'].astype(str).replace({'NaT':'—','None':'—'})
                regs_fmt['Horas_Total'] = pd.to_numeric(
                    regs_fmt['Horas_Total'], errors='coerce').fillna(0)

            df_pend = regs_fmt[regs_fmt['Status'] == '0'] \
                      if not regs_fmt.empty else pd.DataFrame()

            if not df_pend.empty:
                # Barra acções globais
                st.markdown(f"""
                <div style="background:#1E293B;border-radius:12px;padding:14px 18px;
                    margin-bottom:16px;display:flex;align-items:center;
                    justify-content:space-between;border:1px solid #334155;">
                    <div>
                        <span style="color:#F1F5F9;font-weight:700;font-size:0.95rem;">
                            ⏳ {len(df_pend)} registo(s) aguardam validação
                        </span><br>
                        <span style="color:#64748B;font-size:0.78rem;">
                            {len(df_pend['Técnico'].unique())} técnico(s) · 
                            {fh(df_pend['Horas_Total'].sum())} no total
                        </span>
                    </div>
                </div>""", unsafe_allow_html=True)

                col_vm, col_rm = st.columns(2)
                with col_vm:
                    if st.button("🟢 Validar Todos", key="ch_val_todos",
                                 type="primary", use_container_width=True):
                        for tec in df_pend['Técnico'].unique():
                            registos_db.loc[
                                (registos_db['Técnico'] == tec) &
                                (registos_db['Status']  == '0'), 'Status'] = '1'
                            criar_notificacao(destinatario=tec,
                                titulo="🟢 Horas Validadas",
                                mensagem=f"As tuas horas foram validadas por {user_nome}.",
                                tipo="success", acao_url="/")
                        save_db(registos_db, "registos.csv")
                        inv("registos.csv")
                        st.success("✅ Todos validados!")
                        st.session_state['_menu_locked'] = True
                        st.rerun()
                with col_rm:
                    if st.button("❌ Rejeitar Todos", key="ch_rej_todos",
                                 use_container_width=True):
                        for tec in df_pend['Técnico'].unique():
                            registos_db.loc[
                                (registos_db['Técnico'] == tec) &
                                (registos_db['Status']  == '0'), 'Status'] = '-1'
                            criar_notificacao(destinatario=tec,
                                titulo="❌ Horas Rejeitadas",
                                mensagem=f"As tuas horas foram rejeitadas. Contacta {user_nome}.",
                                tipo="error", acao_url="/")
                        save_db(registos_db, "registos.csv")
                        inv("registos.csv")
                        st.error("❌ Todos rejeitados.")
                        st.session_state['_menu_locked'] = True
                        st.rerun()

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

                # Cards por técnico
                for tecnico in df_pend['Técnico'].unique():
                    regs_t    = df_pend[df_pend['Técnico'] == tecnico]
                    total_h_t = regs_t['Horas_Total'].sum()
                    ini_t     = str(regs_t['Técnico'].iloc[0])[:1].upper()

                    # Header do card do técnico
                    st.markdown(f"""
                    <div class="val-card">
                      <div class="val-card-header">
                        <div style="display:flex;align-items:center;gap:12px;">
                          <div style="width:40px;height:40px;border-radius:50%;
                            background:#DC2626;display:flex;align-items:center;
                            justify-content:center;font-weight:900;color:white;
                            font-size:1rem;flex-shrink:0;">{ini_t}</div>
                          <div>
                            <div style="color:#F1F5F9;font-weight:700;font-size:0.95rem;">
                              👤 {tecnico}
                            </div>
                            <div style="color:#64748B;font-size:0.75rem;">
                              {len(regs_t)} registo(s) · {fh(total_h_t)} pendentes
                            </div>
                          </div>
                        </div>
                        <div style="color:#F59E0B;font-size:1.3rem;font-weight:900;">
                          {fh(total_h_t)}
                        </div>
                      </div>
                    """, unsafe_allow_html=True)

                    # Botões validar/rejeitar técnico
                    col_vt, col_rt = st.columns(2)
                    with col_vt:
                        if st.button(f"🟢 Validar todos de {tecnico.split()[0]}",
                                     key=f"apr_{tecnico}", use_container_width=True,
                                     type="primary"):
                            registos_db.loc[
                                (registos_db['Técnico'] == tecnico) &
                                (registos_db['Status']  == '0'), 'Status'] = '1'
                            save_db(registos_db, "registos.csv")
                            criar_notificacao(destinatario=tecnico,
                                titulo="🟢 Horas Validadas",
                                mensagem=f"As tuas horas foram validadas por {user_nome}.",
                                tipo="success", acao_url="/")
                            inv("registos.csv")
                            st.session_state['_menu_locked'] = True
                            st.rerun()
                    with col_rt:
                        if st.button(f"❌ Rejeitar todos de {tecnico.split()[0]}",
                                     key=f"rej_{tecnico}", use_container_width=True):
                            registos_db.loc[
                                (registos_db['Técnico'] == tecnico) &
                                (registos_db['Status']  == '0'), 'Status'] = '-1'
                            save_db(registos_db, "registos.csv")
                            criar_notificacao(destinatario=tecnico,
                                titulo="❌ Horas Rejeitadas",
                                mensagem=f"As tuas horas foram rejeitadas. Contacta {user_nome}.",
                                tipo="error", acao_url="/")
                            inv("registos.csv")
                            st.session_state['_menu_locked'] = True
                            st.rerun()

                    # Registos individuais
                    for _, reg in regs_t.iterrows():
                        reg_id  = reg.get('ID', '')
                        obra_r  = str(reg.get('Obra',  '—'))
                        frente_r= str(reg.get('Frente','—'))
                        turno_r = str(reg.get('Turnos','—'))
                        data_r  = str(reg.get('Data',  '—'))
                        horas_r = reg.get('Horas_Total', 0)

                        st.markdown(f"""
                        <div class="val-reg-row">
                          <div class="val-reg-info">
                            <div class="val-reg-data">{data_r}</div>
                            <div class="val-reg-desc">🏭 {obra_r} · {frente_r}</div>
                            <div class="val-reg-meta">⏰ {turno_r}</div>
                          </div>
                          <div class="val-reg-horas">{fh(horas_r)}</div>
                        </div>""", unsafe_allow_html=True)

                        col_i, col_v, col_r = st.columns([6, 1, 1])
                        with col_v:
                            if st.button("✅", key=f"val_ind_{reg_id}",
                                         use_container_width=True, help="Validar"):
                                registos_db.loc[
                                    registos_db['ID'] == reg_id, 'Status'] = '1'
                                save_db(registos_db, "registos.csv")
                                criar_notificacao(destinatario=tecnico,
                                    titulo="🟢 Horas Validadas",
                                    mensagem=f"{fh(horas_r)} em {obra_r} validadas.",
                                    tipo="success", acao_url="/")
                                inv("registos.csv")
                                st.session_state['_menu_locked'] = True
                                st.rerun()
                        with col_r:
                            if st.button("❌", key=f"rej_ind_{reg_id}",
                                         use_container_width=True, help="Rejeitar"):
                                registos_db.loc[
                                    registos_db['ID'] == reg_id, 'Status'] = '-1'
                                save_db(registos_db, "registos.csv")
                                criar_notificacao(destinatario=tecnico,
                                    titulo="❌ Horas Rejeitadas",
                                    mensagem=f"{fh(horas_r)} rejeitadas.",
                                    tipo="error", acao_url="/")
                                inv("registos.csv")
                                st.session_state['_menu_locked'] = True
                                st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            else:
                st.markdown("""
                <div style="text-align:center;padding:60px 20px;
                    background:#1E293B;border-radius:16px;border:1px solid #334155;">
                    <div style="font-size:3rem;margin-bottom:12px;">✅</div>
                    <p style="color:#10B981;font-weight:700;font-size:1.1rem;margin:0;">
                        Sem horas pendentes!
                    </p>
                    <p style="color:#64748B;font-size:0.85rem;margin:6px 0 0;">
                        Todos os registos estão validados.
                    </p>
                </div>""", unsafe_allow_html=True)

        # ── Histórico Mensal ───────────────────────────────────────────────────
        with sub_h:
            st.markdown("### 📅 Histórico de Horas por Colaborador")

            # Selecção colaborador + mês
            tecnicos_lista = sorted(regs_equipa['Técnico'].unique().tolist()) \
                             if not regs_equipa.empty else []
            if not tecnicos_lista:
                st.info("📋 Sem dados de equipa.")
            else:
                col_tc, col_mes, col_ano = st.columns([3, 2, 1])
                with col_tc:
                    tec_sel = st.selectbox("👤 Colaborador", tecnicos_lista,
                                           key="hist_tec_sel")
                with col_mes:
                    mes_sel_idx = st.selectbox("📅 Mês", range(1, 13),
                        format_func=lambda x: _MESES_PT[x-1],
                        index=hoje.month - 1, key="hist_mes_sel")
                with col_ano:
                    ano_sel = st.number_input("Ano", min_value=2020,
                        max_value=hoje.year + 1, value=hoje.year,
                        key="hist_ano_sel")

                # Filtrar registos
                regs_tec_all = regs_equipa[
                    regs_equipa['Técnico'] == tec_sel
                ].copy() if not regs_equipa.empty else pd.DataFrame()

                if not regs_tec_all.empty:
                    regs_tec_all['_data'] = pd.to_datetime(
                        regs_tec_all['Data'], dayfirst=True, errors='coerce'
                    ).dt.date
                    regs_mes_tec = regs_tec_all[
                        (regs_tec_all['_data'].apply(
                            lambda d: d.month if d else 0) == mes_sel_idx) &
                        (regs_tec_all['_data'].apply(
                            lambda d: d.year  if d else 0) == int(ano_sel))
                    ]
                else:
                    regs_mes_tec = pd.DataFrame()

                mes_nome  = _MESES_PT[mes_sel_idx - 1]

                # KPIs do mês
                total_h_m = pd.to_numeric(
                    regs_mes_tec['Horas_Total'], errors='coerce'
                ).fillna(0).sum() if not regs_mes_tec.empty else 0

                dias_trabalhados = regs_mes_tec['_data'].nunique() \
                                   if not regs_mes_tec.empty else 0
                media_dia = (total_h_m / dias_trabalhados
                             if dias_trabalhados > 0 else 0)

                # Validados vs Pendentes
                n_val  = len(regs_mes_tec[regs_mes_tec['Status'] == '1']) \
                         if not regs_mes_tec.empty else 0
                n_pend = len(regs_mes_tec[regs_mes_tec['Status'] == '0']) \
                         if not regs_mes_tec.empty else 0
                n_rej  = len(regs_mes_tec[regs_mes_tec['Status'] == '-1']) \
                         if not regs_mes_tec.empty else 0

                # Header mês
                ini_t = tec_sel[:1].upper()
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#1E293B,#162032);
                    border-radius:16px;padding:20px 24px;margin:16px 0;
                    border:1px solid #334155;">
                    <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
                        <div style="width:48px;height:48px;border-radius:50%;
                            background:#DC2626;display:flex;align-items:center;
                            justify-content:center;font-weight:900;color:white;
                            font-size:1.2rem;">{ini_t}</div>
                        <div>
                            <div style="color:#F1F5F9;font-weight:800;font-size:1.1rem;">
                                {tec_sel}
                            </div>
                            <div style="color:#DC2626;font-weight:600;font-size:0.9rem;">
                                {mes_nome} {int(ano_sel)}
                            </div>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
                        <div style="background:#0F172A;border-radius:10px;padding:12px;
                            text-align:center;">
                            <div style="color:#64748B;font-size:0.7rem;font-weight:700;
                                text-transform:uppercase;">Total Horas</div>
                            <div style="color:#DC2626;font-size:1.6rem;font-weight:900;">
                                {fh(total_h_m)}</div>
                        </div>
                        <div style="background:#0F172A;border-radius:10px;padding:12px;
                            text-align:center;">
                            <div style="color:#64748B;font-size:0.7rem;font-weight:700;
                                text-transform:uppercase;">Dias Trabalhados</div>
                            <div style="color:#F1F5F9;font-size:1.6rem;font-weight:900;">
                                {dias_trabalhados}</div>
                        </div>
                        <div style="background:#0F172A;border-radius:10px;padding:12px;
                            text-align:center;">
                            <div style="color:#64748B;font-size:0.7rem;font-weight:700;
                                text-transform:uppercase;">Média/Dia</div>
                            <div style="color:#3B82F6;font-size:1.6rem;font-weight:900;">
                                {fh(media_dia)}</div>
                        </div>
                        <div style="background:#0F172A;border-radius:10px;padding:12px;
                            text-align:center;">
                            <div style="color:#64748B;font-size:0.7rem;font-weight:700;
                                text-transform:uppercase;">Validados</div>
                            <div style="color:#10B981;font-size:1.6rem;font-weight:900;">
                                {n_val}</div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

                if not regs_mes_tec.empty:
                    # ── Calendário mensal visual ───────────────────────────────
                    st.markdown("#### 📆 Vista Calendário")

                    # Construir mapa dia → horas+status
                    import calendar as cal_lib
                    dias_no_mes = cal_lib.monthrange(int(ano_sel), mes_sel_idx)[1]
                    dia_inicio_semana = date(int(ano_sel), mes_sel_idx, 1).weekday()
                    # weekday: Mon=0..Sun=6 → ajustar para Dom=0
                    dia_inicio_adj = (dia_inicio_semana + 1) % 7

                    mapa_dia = {}
                    for _, rr in regs_mes_tec.iterrows():
                        d = rr.get('_data')
                        if not d:
                            continue
                        dia = d.day
                        h   = pd.to_numeric(rr.get('Horas_Total', 0), errors='coerce') or 0
                        st_  = str(rr.get('Status', '0'))
                        if dia not in mapa_dia:
                            mapa_dia[dia] = {'h': 0.0, 'status': st_}
                        mapa_dia[dia]['h'] += h
                        # status pior ganha
                        sp = {"-1":6,"0":5,"1":4,"2":3,"3":2,"4":1}
                        if sp.get(st_, 0) > sp.get(mapa_dia[dia]['status'], 0):
                            mapa_dia[dia]['status'] = st_

                    # Header dias da semana
                    dias_header = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']
                    header_html = "<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-bottom:4px;'>"
                    for dh in dias_header:
                        eh_fim = dh in ('Dom','Sáb')
                        header_html += f"<div style='text-align:center;font-size:0.68rem;font-weight:700;color:{'#EF4444' if eh_fim else '#64748B'};padding:4px 0;'>{dh}</div>"
                    header_html += "</div>"

                    # Células do calendário
                    cells_html = "<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:4px;'>"
                    # Células vazias antes do dia 1
                    for _ in range(dia_inicio_adj):
                        cells_html += "<div></div>"
                    for dia in range(1, dias_no_mes + 1):
                        d_obj  = date(int(ano_sel), mes_sel_idx, dia)
                        fim_s  = d_obj.weekday() in (5, 6)
                        tem_reg = dia in mapa_dia
                        if tem_reg:
                            h_dia  = mapa_dia[dia]['h']
                            st_dia = mapa_dia[dia]['status']
                            cor    = _DOT_COLOR.get(st_dia, '#6B7280')
                            h_str  = fh(h_dia)
                            cells_html += f"""
                            <div style="background:{cor}22;border:1px solid {cor};
                                border-radius:8px;padding:6px 4px;text-align:center;">
                                <div style="font-size:0.7rem;color:#94A3B8;font-weight:600;">{dia}</div>
                                <div style="font-size:0.82rem;font-weight:900;color:{cor};">{h_str}</div>
                            </div>"""
                        else:
                            bg = "rgba(239,68,68,0.05)" if fim_s else "rgba(255,255,255,0.02)"
                            cells_html += f"""
                            <div style="background:{bg};border:1px solid #1E293B;
                                border-radius:8px;padding:6px 4px;text-align:center;">
                                <div style="font-size:0.7rem;color:{'#EF444444' if fim_s else '#334155'};font-weight:600;">{dia}</div>
                                <div style="font-size:0.6rem;color:#1E293B;">—</div>
                            </div>"""
                    cells_html += "</div>"

                    st.markdown(header_html + cells_html, unsafe_allow_html=True)

                    # Legenda
                    st.markdown("""
                    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:10px 0;">
                        <span style="font-size:0.72rem;color:#64748B;">
                            <span style="color:#F97316;">●</span> Pendente</span>
                        <span style="font-size:0.72rem;color:#64748B;">
                            <span style="color:#10B981;">●</span> Validado</span>
                        <span style="font-size:0.72rem;color:#64748B;">
                            <span style="color:#3B82F6;">●</span> Faturação</span>
                        <span style="font-size:0.72rem;color:#64748B;">
                            <span style="color:#EF4444;">●</span> Rejeitado</span>
                    </div>""", unsafe_allow_html=True)

                    # ── Breakdown por obra ─────────────────────────────────────
                    st.markdown("#### 🏭 Breakdown por Obra")
                    breakdown = regs_mes_tec.groupby('Obra').agg(
                        Horas   =('Horas_Total', lambda x: pd.to_numeric(x, errors='coerce').sum()),
                        Registos=('Obra', 'count'),
                    ).reset_index().sort_values('Horas', ascending=False)
                    total_br = breakdown['Horas'].sum()

                    for _, br in breakdown.iterrows():
                        pct = int(br['Horas'] / total_br * 100) if total_br > 0 else 0
                        st.markdown(f"""
                        <div style="background:#1E293B;border-radius:10px;
                            padding:12px 16px;margin-bottom:8px;">
                            <div style="display:flex;justify-content:space-between;
                                align-items:center;margin-bottom:6px;">
                                <span style="color:#F1F5F9;font-weight:600;
                                    font-size:0.88rem;">🏭 {br['Obra']}</span>
                                <span style="color:#DC2626;font-weight:900;">
                                    {fh(br['Horas'])}</span>
                            </div>
                            <div style="background:#0F172A;border-radius:4px;height:6px;">
                                <div style="background:#DC2626;width:{pct}%;
                                    height:6px;border-radius:4px;"></div>
                            </div>
                            <div style="color:#64748B;font-size:0.72rem;margin-top:4px;">
                                {br['Registos']} registo(s) · {pct}% do mês
                            </div>
                        </div>""", unsafe_allow_html=True)

                    # ── Tabela detalhada ───────────────────────────────────────
                    with st.expander("📋 Ver todos os registos do mês"):
                        cols_show = [c for c in
                            ['Data','Obra','Frente','Turnos','Horas_Total','Status']
                            if c in regs_mes_tec.columns]
                        df_show = regs_mes_tec[cols_show].copy()
                        if 'Status' in df_show.columns:
                            df_show['Status'] = df_show['Status'].map({
                                "0":"🟠 Pendente","1":"🟢 Validado",
                                "2":"🔵 Faturação","3":"⚫ Processado","-1":"🔴 Rejeitado"
                            }).fillna(df_show['Status'])
                        st.dataframe(df_show, use_container_width=True, hide_index=True)

                        # Indicadores finais
                        col_iv, col_ip, col_ir = st.columns(3)
                        with col_iv:
                            st.metric("✅ Validados", n_val)
                        with col_ip:
                            st.metric("⏳ Pendentes", n_pend)
                        with col_ir:
                            st.metric("❌ Rejeitados", n_rej)
                else:
                    st.markdown(f"""
                    <div style="text-align:center;padding:50px 20px;
                        background:#1E293B;border-radius:16px;
                        border:1px solid #334155;margin-top:16px;">
                        <div style="font-size:3rem;margin-bottom:12px;opacity:0.3;">📅</div>
                        <p style="color:#475569;font-size:0.9rem;margin:0;">
                            Sem registos para {mes_nome} {int(ano_sel)}
                        </p>
                    </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — MEU PONTO (idêntico ao mod_tecnico / Meivworld)
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[2]:

        for k, v in [
            ('data_consulta_ch',     hoje),
            ('semana_offset_ch',     0),
            ('show_reg_form_ch',     False),
            ('periodos_trabalho_ch', [{"entrada": "08:00", "saida": "17:00"}]),
        ]:
            if k not in st.session_state:
                st.session_state[k] = v

        foto_b64 = ""
        try:
            u_data  = _load_users_fresh()
            u_match = u_data[u_data['Nome'] == user_nome]
            if not u_match.empty:
                foto_b64 = str(u_match.iloc[0].get('Foto', ''))
        except:
            pass

        dias_status = {}
        if not registos_db.empty and 'Técnico' in registos_db.columns:
            ru = registos_db[registos_db['Técnico'] == user_nome].copy()
            if not ru.empty:
                ru['Data_d'] = pd.to_datetime(
                    ru['Data'], dayfirst=True, errors='coerce'
                ).dt.normalize().dt.date
                sp = {"-1":6,"0":5,"1":4,"2":3,"3":2,"4":1}
                for d_u in ru['Data_d'].dropna().unique():
                    rd   = ru[ru['Data_d'] == d_u]
                    pior = max(rd['Status'].tolist(), key=lambda s: sp.get(str(s),0))
                    dias_status[d_u] = str(pior)

        # ── Vista calendário ──────────────────────────────────────────────────
        if not st.session_state.show_reg_form_ch:
            data_ref   = hoje + timedelta(weeks=st.session_state.semana_offset_ch)
            inicio_sem = data_ref - timedelta(days=(data_ref.weekday()+1) % 7)
            dias_sem   = [inicio_sem + timedelta(days=i) for i in range(7)]
            mes_label  = _MESES_PT[dias_sem[3].month - 1]
            ano_label  = dias_sem[3].year

            col_prev, col_mes, col_foto = st.columns([1, 5, 1])
            with col_prev:
                if st.button("‹", key="ch_cal_prev", use_container_width=True):
                    st.session_state.semana_offset_ch -= 1; st.session_state['_menu_locked'] = True
                    st.rerun()
            with col_mes:
                st.markdown(
                    f"<div style='text-align:center;padding:6px 0;'>"
                    f"<p style='color:#F1F5F9;font-weight:700;font-size:0.88rem;margin:0 0 2px;'>Meu Ponto</p>"
                    f"<p style='color:#DC2626;font-weight:900;font-size:1.05rem;margin:0;'>{mes_label} {ano_label}</p>"
                    f"</div>", unsafe_allow_html=True)
            with col_foto:
                col_next, col_img = st.columns([1,1])
                with col_next:
                    if st.button("›", key="ch_cal_next", use_container_width=True):
                        st.session_state.semana_offset_ch += 1; st.session_state['_menu_locked'] = True
                        st.rerun()
                with col_img:
                    if foto_b64 and len(foto_b64) > 100:
                        try:
                            st.markdown(
                                f"<img src='data:image/jpeg;base64,{foto_b64}' "
                                f"style='width:34px;height:34px;border-radius:50%;"
                                f"object-fit:cover;border:2px solid #DC2626;margin-top:2px;'>",
                                unsafe_allow_html=True)
                        except: pass

            # Marcadores dias semana
            letras_cols = st.columns(7)
            for col, d in zip(letras_cols, dias_sem):
                with col:
                    dl    = _DIAS_LETRA[(d.weekday()+1) % 7]
                    fim_s = (d.weekday()+1) % 7 in (0,6)
                    st.markdown(
                        f"<p style='text-align:center;color:{'#EF4444' if fim_s else '#64748B'};"
                        f"font-size:0.6rem;font-weight:700;margin:0;text-transform:uppercase;'>{dl}</p>",
                        unsafe_allow_html=True)

            # Botões dos dias
            st.markdown("<div class='cal-week'>", unsafe_allow_html=True)
            btn_cols = st.columns(7)
            for col, d in zip(btn_cols, dias_sem):
                with col:
                    dot_cor  = _DOT_COLOR.get(dias_status.get(d, ''), '')
                    eh_sel   = d == st.session_state.data_consulta_ch
                    btn_type = "primary" if eh_sel else "secondary"
                    if st.button(str(d.day), key=f"ch_day_{d.strftime('%Y%m%d')}",
                                 use_container_width=True, type=btn_type):
                        st.session_state.data_consulta_ch = d; st.session_state['_menu_locked'] = True
                        st.rerun()
                    if dot_cor:
                        st.markdown(
                            f"<div style='width:7px;height:7px;border-radius:50%;"
                            f"background:{dot_cor};margin:-6px auto 4px;'></div>",
                            unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='height:11px;'></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                "<div style='display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin:4px 0 8px;'>"
                "<span style='font-size:0.62rem;color:#64748B;'><span style='color:#F97316;'>●</span> Pendente</span>"
                "<span style='font-size:0.62rem;color:#64748B;'><span style='color:#10B981;'>●</span> Validado</span>"
                "<span style='font-size:0.62rem;color:#64748B;'><span style='color:#3B82F6;'>●</span> Faturação</span>"
                "<span style='font-size:0.62rem;color:#64748B;'><span style='color:#6B7280;'>●</span> Pago</span>"
                "</div>", unsafe_allow_html=True)
            st.markdown("<hr style='border:none;border-top:1px solid #1E293B;margin:4px 0 10px;'>",
                        unsafe_allow_html=True)

            data_sel    = st.session_state.data_consulta_ch
            mes_nome_d  = _MESES_PT[data_sel.month - 1]
            dia_letra_d = _DIAS_LETRA[(data_sel.weekday()+1) % 7]
            eh_hoje_sel = data_sel == hoje

            col_data, col_fab = st.columns([4,1])
            with col_data:
                prefix = "📍 Hoje" if eh_hoje_sel else dia_letra_d
                st.markdown(
                    f"<p style='color:#F1F5F9;font-weight:700;font-size:0.92rem;margin:0;'>"
                    f"{prefix}, {data_sel.day} de {mes_nome_d}</p>",
                    unsafe_allow_html=True)
            with col_fab:
                if st.button("＋", key="ch_fab_btn", type="primary", use_container_width=True):
                    st.session_state.show_reg_form_ch    = True
                    st.session_state.periodos_trabalho_ch = [{"entrada":"08:00","saida":"17:00"}]
                    st.session_state['_menu_locked'] = True
                    st.rerun()

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

            # Cards do dia
            regs_dia = pd.DataFrame()
            if not registos_db.empty and 'Técnico' in registos_db.columns:
                meus = registos_db[registos_db['Técnico'] == user_nome].copy()
                if not meus.empty:
                    data_sel_d = data_sel.date() if hasattr(data_sel,'date') else data_sel
                    dp = pd.to_datetime(meus['Data'], dayfirst=True, errors='coerce').dt.normalize().dt.date
                    regs_dia = meus[dp == data_sel_d].copy()

            if not regs_dia.empty:
                regs_dia['_h'] = pd.to_numeric(regs_dia['Horas_Total'], errors='coerce').fillna(0)
                total_dia = regs_dia['_h'].sum()
                st.markdown(
                    f"<div class='total-horas-bar'>"
                    f"<span class='total-horas-label'>Total de horas reportadas</span>"
                    f"<span class='total-horas-value'>{fh(total_dia)}</span></div>",
                    unsafe_allow_html=True)
                for _, r in regs_dia.iterrows():
                    s_str   = str(r.get('Status','0'))
                    dot_c   = _DOT_COLOR.get(s_str,'#6B7280')
                    dot_l   = _DOT_LABEL.get(s_str,'Pendente')
                    turnos  = str(r.get('Turnos',''))
                    obra    = str(r.get('Obra',''))
                    frente  = str(r.get('Frente',''))
                    horas_r = r.get('Horas_Total',0)
                    relat   = str(r.get('Relatorio',''))[:60]
                    entrada_str = saida_str = ""
                    if '-' in turnos:
                        partes = turnos.split('-')
                        if len(partes) == 2:
                            entrada_str = partes[0].strip()
                            saida_str   = partes[1].strip()
                    cod_obra = cli_obra = ""
                    if not obras_db.empty and obra in obras_db['Obra'].values:
                        oi       = obras_db[obras_db['Obra'] == obra].iloc[0]
                        cod_obra = str(oi.get('Codigo',''))
                        cli_obra = str(oi.get('Cliente',''))
                    st.markdown(
                        f"<div class='ponto-card' style='border-left:4px solid {dot_c};'>"
                        f"<div class='ponto-card-header'>"
                        f"<div><p class='ponto-card-title'>{frente if frente else obra}</p>"
                        f"<span class='ponto-card-status' style='background:{dot_c}22;color:{dot_c};'>"
                        f"{dot_l}</span></div>"
                        f"<span class='ponto-card-horas'>{fh(horas_r)}</span>"
                        f"</div><div class='ponto-card-grid'>"
                        f"<div><p class='ponto-card-label'>Cliente</p>"
                        f"<p class='ponto-card-value'>{cli_obra if cli_obra else obra}</p></div>"
                        f"<div style='text-align:right;'><p class='ponto-card-label'>Entrada</p>"
                        f"<p class='ponto-card-value'><b>{entrada_str if entrada_str else '—'}</b></p></div>"
                        f"<div><p class='ponto-card-label'>{'Cód.' if cod_obra else 'Obra'}</p>"
                        f"<p class='ponto-card-value'>{cod_obra if cod_obra else obra[:28]}</p></div>"
                        f"<div style='text-align:right;'><p class='ponto-card-label'>Saída</p>"
                        f"<p class='ponto-card-value'><b>{saida_str if saida_str else '—'}</b></p></div>"
                        f"</div>"
                        + (f"<p style='color:#475569;font-size:0.73rem;margin:8px 0 0;"
                           f"border-top:1px solid rgba(255,255,255,0.06);padding-top:6px;'>"
                           f"{relat}</p>" if relat else "")
                        + "</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    "<div style='text-align:center;padding:50px 20px 40px;'>"
                    "<div style='font-size:3.5rem;margin-bottom:12px;opacity:0.25;'>📋</div>"
                    "<p style='color:#475569;font-weight:600;margin:0;font-size:0.9rem;'>"
                    "Sem ponto registado neste dia</p></div>", unsafe_allow_html=True)

        # ── Formulário de registo ──────────────────────────────────────────────
        else:
            data_sel = st.session_state.data_consulta_ch
            foto_html = ""
            if foto_b64 and len(foto_b64) > 100:
                foto_html = (f"<img src='data:image/jpeg;base64,{foto_b64}' "
                             f"style='width:44px;height:44px;border-radius:50%;"
                             f"object-fit:cover;border:2px solid #DC2626;flex-shrink:0;'>")
            else:
                ini = str(user_nome)[:1].upper()
                foto_html = (f"<div style='width:44px;height:44px;border-radius:50%;"
                             f"background:#DC2626;display:flex;align-items:center;"
                             f"justify-content:center;font-weight:900;color:white;"
                             f"font-size:1.1rem;flex-shrink:0;'>{ini}</div>")

            st.markdown(
                f"<div style='background:#1E293B;border-radius:14px;padding:14px 16px;"
                f"margin-bottom:14px;border:1px solid #334155;"
                f"display:flex;align-items:center;gap:14px;'>"
                f"{foto_html}<div style='flex:1;'>"
                f"<p style='color:#94A3B8;font-size:0.7rem;margin:0;'>Registo de ponto</p>"
                f"<p style='color:#F1F5F9;font-weight:700;font-size:0.95rem;margin:2px 0 0;'>{user_nome}</p>"
                f"<p style='color:#DC2626;font-size:0.82rem;font-weight:600;margin:1px 0 0;'>"
                f"{data_sel.strftime('%d/%m/%Y')}</p></div></div>",
                unsafe_allow_html=True)

            with st.form("form_ponto_ch", clear_on_submit=False):
                st.markdown("<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                            "letter-spacing:0.08em;text-transform:uppercase;margin:0 0 6px;'>"
                            "🏗️ Obra</p>", unsafe_allow_html=True)
                obras_lista = []
                if not obras_db.empty:
                    at = obras_db[obras_db['Ativa'] == 'Ativa']
                    obras_lista = at['Obra'].tolist() if not at.empty else obras_db['Obra'].tolist()
                obra_sel = st.selectbox("Obra", obras_lista if obras_lista else ["Sem obras"],
                                        key="ch_reg_obra", label_visibility="collapsed")

                if not obras_db.empty and obra_sel in obras_db['Obra'].values:
                    oi  = obras_db[obras_db['Obra'] == obra_sel].iloc[0]
                    cod = str(oi.get('Codigo',''))
                    cli = str(oi.get('Cliente',''))
                    if cod or cli:
                        st.markdown(
                            f"<div style='background:#0F172A;border-radius:10px;"
                            f"padding:10px 14px;margin:-4px 0 10px;border-left:3px solid #DC2626;'>"
                            f"<p style='color:#F1F5F9;font-weight:700;font-size:0.82rem;margin:0;'>"
                            f"{cli if cli else obra_sel}</p>"
                            + (f"<p style='color:#DC2626;font-size:0.72rem;margin:2px 0 0;'>{cod}</p>" if cod else "")
                            + "</div>", unsafe_allow_html=True)

                st.markdown("<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                            "letter-spacing:0.08em;text-transform:uppercase;margin:8px 0 6px;'>"
                            "🔧 Frente de Trabalho</p>", unsafe_allow_html=True)
                frente_sel = st.selectbox("Frente", TIPOS_FRENTE, key="ch_reg_frente",
                                          label_visibility="collapsed")

                st.markdown("<hr style='border:none;border-top:1px solid #1E293B;margin:12px 0;'>",
                            unsafe_allow_html=True)
                st.markdown("<p style='color:#64748B;font-size:0.68rem;font-weight:700;"
                            "letter-spacing:0.08em;text-transform:uppercase;margin:0 0 8px;'>"
                            "⏱️ Horas de Trabalho</p>", unsafe_allow_html=True)

                total_horas = 0.0
                periodos_validos = []

                for idx, periodo in enumerate(st.session_state.periodos_trabalho_ch):
                    if idx > 0:
                        st.markdown("<hr style='border:none;border-top:1px dashed #1E293B;margin:6px 0;'>",
                                    unsafe_allow_html=True)
                    col_e, col_s = st.columns(2)
                    with col_e:
                        ie = _HORAS_30.index(periodo["entrada"]) if periodo["entrada"] in _HORAS_30 else 16
                        lbl_e = "Entrada" + (f" {idx+1}" if len(st.session_state.periodos_trabalho_ch) > 1 else "")
                        entrada = st.selectbox(lbl_e, _HORAS_30, index=ie, key=f"ch_ent_{idx}")
                    with col_s:
                        is_ = _HORAS_30.index(periodo["saida"]) if periodo["saida"] in _HORAS_30 else 34
                        lbl_s = "Saída" + (f" {idx+1}" if len(st.session_state.periodos_trabalho_ch) > 1 else "")
                        saida = st.selectbox(lbl_s, _HORAS_30, index=is_, key=f"ch_sai_{idx}")
                    t1    = datetime.strptime(entrada, "%H:%M")
                    t2    = datetime.strptime(saida,   "%H:%M")
                    delta = (t2 - t1).seconds / 3600
                    if delta > 0:
                        total_horas += delta
                        periodos_validos.append({"entrada": entrada, "saida": saida, "horas": round(delta, 2)})
                        st.markdown(f"<p style='text-align:right;color:#DC2626;font-weight:700;"
                                    f"font-size:0.8rem;margin:0 0 4px;'>= {fh(delta)}</p>",
                                    unsafe_allow_html=True)
                    elif delta < 0:
                        st.warning("⚠️ Saída antes da entrada")

                if total_horas > 0:
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;padding:12px 16px;"
                        f"margin:10px 0;display:flex;justify-content:space-between;align-items:center;'>"
                        f"<span style='color:#64748B;font-size:0.78rem;font-weight:600;"
                        f"text-transform:uppercase;letter-spacing:0.06em;'>Total</span>"
                        f"<span style='color:#F1F5F9;font-size:1.6rem;font-weight:900;'>{fh(total_horas)}</span>"
                        f"</div>", unsafe_allow_html=True)

                relatorio = st.text_area("📝 Descrição (opcional)",
                    placeholder="Ex: Supervisão, reunião, visita...", key="ch_reg_relat", height=70)
                st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
                col_c, col_g = st.columns(2)
                with col_c:
                    mais_per = st.form_submit_button("➕ Adicionar Período", use_container_width=True)
                with col_g:
                    guardar  = st.form_submit_button("💾 Guardar Ponto", use_container_width=True, type="primary")

            if st.button("← Voltar", key="ch_btn_voltar"):
                st.session_state.show_reg_form_ch    = False
                st.session_state.periodos_trabalho_ch = [{"entrada":"08:00","saida":"17:00"}]
                st.session_state['_menu_locked'] = True
                st.rerun()

            if mais_per:
                st.session_state.periodos_trabalho_ch.append({"entrada":"13:00","saida":"17:00"})
                st.session_state['_menu_locked'] = True
                st.rerun()

            if guardar:
                if total_horas <= 0:
                    st.error("⚠️ Horas têm de ser superiores a 0.")
                elif not obra_sel or obra_sel == "Sem obras":
                    st.error("⚠️ Seleciona uma obra.")
                else:
                    regs_atual = registos_db.copy() if not registos_db.empty else pd.DataFrame()
                    ids_guardados = []
                    for pv in periodos_validos:
                        new_r = pd.DataFrame([{
                            "ID":          str(uuid.uuid4())[:8].upper(),
                            "Data":        data_sel.strftime("%d/%m/%Y"),
                            "Técnico":     user_nome,
                            "Obra":        obra_sel,
                            "Frente":      frente_sel,
                            "Turnos":      f"{pv['entrada']}-{pv['saida']}",
                            "Horas_Total": pv['horas'],
                            "Relatorio":   relatorio,
                            "Status":      "0",
                            "Periodo":     periodos_validos.index(pv) + 1,
                        }])
                        ids_guardados.append(new_r['ID'].iloc[0])
                        regs_atual = pd.concat([regs_atual, new_r], ignore_index=True)
                    save_db(regs_atual, "registos.csv")
                    for reg_id in ids_guardados:
                        log_audit(usuario=user_nome, acao="REGISTAR_PONTO_CHEFE",
                                  tabela="registos.csv", registro_id=reg_id,
                                  detalhes=f"{total_horas}h em {obra_sel}", ip="")
                    criar_notificacao(destinatario="admin",
                        titulo="📋 Novo Registo de Ponto (Chefe)",
                        mensagem=f"{user_nome} registou {fh(total_horas)} em {obra_sel}",
                        tipo="info", acao_url="/admin?tab=validacoes")
                    st.session_state.show_reg_form_ch    = False
                    st.session_state.periodos_trabalho_ch = [{"entrada":"08:00","saida":"17:00"}]
                    st.session_state.data_consulta_ch    = data_sel
                    inv("registos.csv")
                    st.session_state['_menu_locked'] = True
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — FOLHA DE PONTO (fluxo completo)
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown("### 📊 Folha de Ponto")

        # Estado da folha em session_state
        for k, v in [
            ('fp_step',          'configurar'),   # configurar | preview | assinar | concluida
            ('fp_html',          ''),
            ('fp_total_h',       0.0),
            ('fp_obra',          ''),
            ('fp_periodo',       ''),
            ('fp_regs',          None),
            ('fp_responsavel',   ''),
            ('fp_modo_assin',    ''),              # digital | manual
            ('fp_folha_id',      ''),
        ]:
            if k not in st.session_state:
                st.session_state[k] = v

        # ── PASSO 1: Configurar ───────────────────────────────────────────────
        if st.session_state.fp_step == 'configurar':
            st.markdown("""
            <div style="background:#1E293B;border-radius:14px;padding:18px 20px;
                margin-bottom:16px;border:1px solid #334155;">
                <div style="color:#F1F5F9;font-weight:700;font-size:0.95rem;
                    margin-bottom:4px;">⚙️ Passo 1 de 3 — Configurar Folha</div>
                <div style="color:#64748B;font-size:0.8rem;">
                    Seleciona a obra, o período e os técnicos a incluir.
                </div>
            </div>""", unsafe_allow_html=True)

            obras_l_fp = obras_db['Obra'].unique().tolist() \
                         if not obras_db.empty else ["Sem Obras"]
            obra_fp = st.selectbox("🏭 Obra", obras_l_fp, key="fp_ch_obra_sel")

            ini_s   = hoje - timedelta(days=hoje.weekday())
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                sem_ini = st.date_input("📅 Data Início",
                    value=ini_s, key="fp_ch_ini_sel")
            with col_d2:
                sem_fim = st.date_input("📅 Data Fim",
                    value=ini_s + timedelta(days=6), key="fp_ch_fim_sel")

            # Técnicos disponíveis nesse período/obra
            regs_fp = pd.DataFrame()
            if not registos_db.empty:
                dp_fp = pd.to_datetime(registos_db['Data'],
                    dayfirst=True, errors='coerce').dt.date
                regs_fp = registos_db[
                    (registos_db['Obra'] == obra_fp) &
                    (dp_fp >= sem_ini) &
                    (dp_fp <= sem_fim)
                ].copy()

            tec_disponiveis = sorted(regs_fp['Técnico'].unique().tolist()) \
                              if not regs_fp.empty else []

            if tec_disponiveis:
                tec_sel_fp = st.multiselect(
                    "👷 Técnicos a incluir (todos por omissão)",
                    tec_disponiveis, default=tec_disponiveis,
                    key="fp_ch_tecs")
                regs_fp = regs_fp[regs_fp['Técnico'].isin(tec_sel_fp)] \
                          if tec_sel_fp else regs_fp
            else:
                tec_sel_fp = []

            nome_resp = st.text_input("✍️ Nome do Responsável pela Folha",
                value=user_nome, key="fp_ch_resp_nome")

            total_preview = pd.to_numeric(
                regs_fp['Horas_Total'], errors='coerce'
            ).fillna(0).sum() if not regs_fp.empty else 0

            if not regs_fp.empty:
                periodo_str = f"{sem_ini.strftime('%d/%m/%Y')} a {sem_fim.strftime('%d/%m/%Y')}"
                st.markdown(f"""
                <div style="background:rgba(16,185,129,0.08);border-radius:10px;
                    padding:14px 18px;margin:12px 0;border-left:3px solid #10B981;">
                    <div style="color:#10B981;font-weight:700;font-size:0.88rem;">
                        ✅ {len(regs_fp)} registos encontrados · {fh(total_preview)} totais
                    </div>
                    <div style="color:#64748B;font-size:0.78rem;margin-top:4px;">
                        {len(tec_sel_fp)} técnico(s) · {obra_fp} · {periodo_str}
                    </div>
                </div>""", unsafe_allow_html=True)

                if st.button("👁️ Gerar Preview da Folha →", use_container_width=True,
                             type="primary", key="btn_fp_preview"):
                    if not nome_resp.strip():
                        st.warning("⚠️ Indica o nome do responsável.")
                    else:
                        html_folha, total_h = _gerar_html_folha(
                            obra_fp, periodo_str, regs_fp, nome_resp)
                        st.session_state.fp_step        = 'preview'
                        st.session_state.fp_html        = html_folha
                        st.session_state.fp_total_h     = total_h
                        st.session_state.fp_obra        = obra_fp
                        st.session_state.fp_periodo     = periodo_str
                        st.session_state.fp_responsavel = nome_resp
                        st.session_state.fp_regs        = regs_fp.to_dict('records')
                        st.session_state['_menu_locked'] = True
                        st.rerun()
            else:
                st.info("📋 Sem registos para o período e obra seleccionados.")

        # ── PASSO 2: Preview ──────────────────────────────────────────────────
        elif st.session_state.fp_step == 'preview':
            st.markdown("""
            <div style="background:#1E293B;border-radius:14px;padding:18px 20px;
                margin-bottom:16px;border:1px solid #334155;">
                <div style="color:#F1F5F9;font-weight:700;font-size:0.95rem;
                    margin-bottom:4px;">👁️ Passo 2 de 3 — Preview da Folha</div>
                <div style="color:#64748B;font-size:0.8rem;">
                    Verifica os dados. Depois escolhe como queres assinar.
                </div>
            </div>""", unsafe_allow_html=True)

            # Info resumo
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;
                gap:10px;margin-bottom:16px;">
                <div style="background:#1E293B;border-radius:10px;padding:12px;text-align:center;">
                    <div style="color:#64748B;font-size:0.7rem;font-weight:700;
                        text-transform:uppercase;">Obra</div>
                    <div style="color:#F1F5F9;font-weight:700;font-size:0.88rem;">
                        {st.session_state.fp_obra}</div>
                </div>
                <div style="background:#1E293B;border-radius:10px;padding:12px;text-align:center;">
                    <div style="color:#64748B;font-size:0.7rem;font-weight:700;
                        text-transform:uppercase;">Período</div>
                    <div style="color:#F1F5F9;font-weight:700;font-size:0.82rem;">
                        {st.session_state.fp_periodo}</div>
                </div>
                <div style="background:#1E293B;border-radius:10px;padding:12px;text-align:center;">
                    <div style="color:#64748B;font-size:0.7rem;font-weight:700;
                        text-transform:uppercase;">Total Horas</div>
                    <div style="color:#DC2626;font-weight:900;font-size:1.1rem;">
                        {fh(st.session_state.fp_total_h)}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            # Preview iframe
            regs_prev = pd.DataFrame(st.session_state.fp_regs) \
                        if st.session_state.fp_regs else pd.DataFrame()
            if not regs_prev.empty:
                cols_p = [c for c in ['Data','Técnico','Frente','Turnos','Horas_Total']
                          if c in regs_prev.columns]
                st.dataframe(regs_prev[cols_p], use_container_width=True, hide_index=True)

            # Download HTML
            html_bytes = st.session_state.fp_html.encode('utf-8')
            nome_ficheiro = (f"folha_ponto_{st.session_state.fp_obra.replace(' ','_')}"
                             f"_{datetime.now().strftime('%Y%m%d')}.html")
            st.download_button(
                "📥 Download da Folha (para imprimir e assinar manualmente)",
                data=html_bytes,
                file_name=nome_ficheiro,
                mime="text/html",
                use_container_width=True,
                key="btn_download_folha"
            )

            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            st.markdown("**Escolhe como queres assinar:**")

            col_dig, col_man = st.columns(2)
            with col_dig:
                st.markdown("""
                <div style="background:rgba(59,130,246,0.08);border-radius:12px;
                    padding:14px;border:1px solid rgba(59,130,246,0.3);
                    text-align:center;margin-bottom:8px;">
                    <div style="font-size:1.5rem;">✍️</div>
                    <div style="color:#3B82F6;font-weight:700;font-size:0.88rem;">
                        Assinatura Digital</div>
                    <div style="color:#64748B;font-size:0.75rem;margin-top:4px;">
                        Confirma o nome e aprova online. Gera selo de autenticidade.
                    </div>
                </div>""", unsafe_allow_html=True)
                if st.button("✍️ Assinar Digitalmente", key="btn_modo_digital",
                             use_container_width=True, type="primary"):
                    st.session_state.fp_modo_assin = 'digital'
                    st.session_state.fp_step = 'assinar'
                    st.session_state['_menu_locked'] = True
                    st.rerun()

            with col_man:
                st.markdown("""
                <div style="background:rgba(16,185,129,0.08);border-radius:12px;
                    padding:14px;border:1px solid rgba(16,185,129,0.3);
                    text-align:center;margin-bottom:8px;">
                    <div style="font-size:1.5rem;">🖊️</div>
                    <div style="color:#10B981;font-weight:700;font-size:0.88rem;">
                        Assinatura Manual</div>
                    <div style="color:#64748B;font-size:0.75rem;margin-top:4px;">
                        Descarrega, imprime, assina e faz upload da folha assinada.
                    </div>
                </div>""", unsafe_allow_html=True)
                if st.button("🖊️ Upload Assinatura Manual", key="btn_modo_manual",
                             use_container_width=True):
                    st.session_state.fp_modo_assin = 'manual'
                    st.session_state.fp_step = 'assinar'
                    st.session_state['_menu_locked'] = True
                    st.rerun()

            if st.button("← Voltar à Configuração", key="btn_fp_back",
                         use_container_width=True):
                st.session_state.fp_step = 'configurar'
                st.session_state['_menu_locked'] = True
                st.rerun()

        # ── PASSO 3: Assinar ──────────────────────────────────────────────────
        elif st.session_state.fp_step == 'assinar':

            st.markdown("""
            <div style="background:#1E293B;border-radius:14px;padding:18px 20px;
                margin-bottom:16px;border:1px solid #334155;">
                <div style="color:#F1F5F9;font-weight:700;font-size:0.95rem;
                    margin-bottom:4px;">🔏 Passo 3 de 3 — Assinar e Submeter</div>
            </div>""", unsafe_allow_html=True)

            # ── Modo Digital ──────────────────────────────────────────────────
            if st.session_state.fp_modo_assin == 'digital':
                st.markdown("""
                <div style="background:rgba(59,130,246,0.08);border-radius:12px;
                    padding:16px 18px;border-left:3px solid #3B82F6;margin-bottom:16px;">
                    <p style="color:#93C5FD;font-size:0.85rem;margin:0;">
                        ℹ️ A assinatura digital consiste na confirmação do teu nome completo
                        e aprovação explícita do conteúdo da folha.
                        É gerado um selo único com timestamp e hash de autenticidade.
                    </p>
                </div>""", unsafe_allow_html=True)

                with st.form("form_assinar_digital"):
                    nome_conf = st.text_input(
                        "Confirma o teu nome completo *",
                        value=st.session_state.fp_responsavel,
                        key="fp_nome_confirm")
                    cargo_conf = st.text_input(
                        "Cargo / Função",
                        value=cargo_user,
                        key="fp_cargo_confirm")
                    aceito = st.checkbox(
                        "✅ Confirmo que li os dados da folha de ponto e que "
                        "são correctos. Autorizo a sua submissão.",
                        key="fp_aceito_check")
                    st.markdown(f"""
                    <div style="background:#0F172A;border-radius:8px;padding:12px 16px;
                        margin:10px 0;font-size:0.8rem;">
                        <span style="color:#64748B;">Folha: </span>
                        <span style="color:#F1F5F9;font-weight:600;">
                            {st.session_state.fp_obra} · {st.session_state.fp_periodo}</span><br>
                        <span style="color:#64748B;">Total: </span>
                        <span style="color:#DC2626;font-weight:700;">
                            {fh(st.session_state.fp_total_h)}</span>
                    </div>""", unsafe_allow_html=True)

                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        cancelar = st.form_submit_button("← Voltar",
                            use_container_width=True)
                    with col_s2:
                        confirmar = st.form_submit_button("🔏 Assinar e Submeter",
                            use_container_width=True, type="primary")

                if cancelar:
                    st.session_state.fp_step = 'preview'
                    st.session_state['_menu_locked'] = True
                    st.rerun()

                if confirmar:
                    if not nome_conf.strip():
                        st.error("⚠️ Confirma o teu nome completo.")
                    elif not aceito:
                        st.error("⚠️ Tens de confirmar os dados antes de assinar.")
                    else:
                        folha_id = str(uuid.uuid4())[:8].upper()
                        selo_id  = secrets.token_hex(8).upper()
                        ts_assin = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        nova_folha = pd.DataFrame([{
                            "ID":              folha_id,
                            "Obra":            st.session_state.fp_obra,
                            "Periodo":         st.session_state.fp_periodo,
                            "Responsavel":     nome_conf.strip(),
                            "Cargo":           cargo_conf.strip(),
                            "Data_Assinatura": ts_assin,
                            "Assinatura_b64":  "",
                            "Selo":            selo_id,
                            "Tipo_Assinatura": "Digital",
                            "Status":          "Aguarda_Validacao_Cliente",
                            "Total_Horas":     st.session_state.fp_total_h,
                            "Submetido_Por":   user_nome,
                            "Submetido_Em":    ts_assin,
                        }])
                        upd_f = pd.concat([folhas_db, nova_folha], ignore_index=True) \
                                if not folhas_db.empty else nova_folha
                        save_db(upd_f, "folhas_ponto.csv")
                        log_audit(usuario=user_nome, acao="ASSINAR_FOLHA_DIGITAL",
                                  tabela="folhas_ponto.csv", registro_id=folha_id,
                                  detalhes=f"{nome_conf} · {st.session_state.fp_obra}",
                                  ip="")
                        criar_notificacao(destinatario="admin",
                            titulo="📋 Folha de Ponto Assinada",
                            mensagem=f"{user_nome} assinou digitalmente folha #{folha_id} "
                                     f"— {st.session_state.fp_obra}",
                            tipo="success", acao_url="/admin?tab=folhas")
                        st.session_state.fp_folha_id = folha_id
                        st.session_state.fp_step     = 'concluida'
                        inv("folhas_ponto.csv")
                        st.session_state['_menu_locked'] = True
                        st.rerun()

            # ── Modo Manual ───────────────────────────────────────────────────
            else:
                st.markdown("""
                <div style="background:#1E293B;border-radius:12px;padding:14px 18px;
                    margin-bottom:16px;border-left:3px solid #10B981;">
                    <p style="color:#6EE7B7;font-size:0.85rem;margin:0 0 8px;font-weight:700;">
                        📋 Instruções:</p>
                    <p style="color:#94A3B8;font-size:0.82rem;margin:0;">
                        1. Descarrega a folha no passo anterior (Preview)<br>
                        2. Imprime e faz assinar pelo cliente / representante<br>
                        3. Fotografa ou digitaliza a folha assinada<br>
                        4. Faz upload aqui e submete ao Admin
                    </p>
                </div>""", unsafe_allow_html=True)

                ficheiro_assin = st.file_uploader(
                    "📤 Upload da folha assinada (JPG, PNG ou PDF)",
                    type=["jpg","jpeg","png","pdf"],
                    key="fp_upload_assinada"
                )

                if ficheiro_assin:
                    tam_kb = len(ficheiro_assin.getvalue()) / 1024
                    st.success(f"✅ {ficheiro_assin.name} ({tam_kb:.0f} KB)")

                    nome_cliente = st.text_input(
                        "Nome do cliente / representante que assinou",
                        key="fp_nome_cliente_manual")

                    if st.button("📤 Submeter Folha Assinada ao Admin",
                                 use_container_width=True, type="primary",
                                 key="btn_submeter_manual"):
                        folha_id    = str(uuid.uuid4())[:8].upper()
                        selo_id     = secrets.token_hex(8).upper()
                        ts_assin    = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        file_b64    = base64.b64encode(
                            ficheiro_assin.getvalue()).decode('utf-8')
                        nova_folha  = pd.DataFrame([{
                            "ID":              folha_id,
                            "Obra":            st.session_state.fp_obra,
                            "Periodo":         st.session_state.fp_periodo,
                            "Responsavel":     st.session_state.fp_responsavel,
                            "Cargo":           cargo_user,
                            "Data_Assinatura": ts_assin,
                            "Assinatura_b64":  file_b64,
                            "Selo":            selo_id,
                            "Tipo_Assinatura": "Manual",
                            "Status":          "Assinado_Manual",
                            "Total_Horas":     st.session_state.fp_total_h,
                            "Submetido_Por":   user_nome,
                            "Submetido_Em":    ts_assin,
                            "Cliente_Assinou": nome_cliente.strip(),
                        }])
                        upd_f = pd.concat([folhas_db, nova_folha], ignore_index=True) \
                                if not folhas_db.empty else nova_folha
                        save_db(upd_f, "folhas_ponto.csv")
                        log_audit(usuario=user_nome, acao="SUBMETER_FOLHA_MANUAL",
                                  tabela="folhas_ponto.csv", registro_id=folha_id,
                                  detalhes=f"{st.session_state.fp_obra} · assinatura manual",
                                  ip="")
                        criar_notificacao(destinatario="admin",
                            titulo="📋 Folha Assinada Manualmente",
                            mensagem=f"{user_nome} submeteu folha #{folha_id} assinada "
                                     f"manualmente — {st.session_state.fp_obra}",
                            tipo="success", acao_url="/admin?tab=folhas")
                        st.session_state.fp_folha_id = folha_id
                        st.session_state.fp_step     = 'concluida'
                        inv("folhas_ponto.csv")
                        st.session_state['_menu_locked'] = True
                        st.rerun()

                if st.button("← Voltar ao Preview", key="btn_fp_back_man",
                             use_container_width=True):
                    st.session_state.fp_step = 'preview'
                    st.session_state['_menu_locked'] = True
                    st.rerun()

        # ── PASSO FINAL: Concluída ─────────────────────────────────────────────
        elif st.session_state.fp_step == 'concluida':
            modo_label = ("Assinatura Digital" if st.session_state.fp_modo_assin == 'digital'
                          else "Assinatura Manual")
            st.markdown(f"""
            <div style="text-align:center;padding:40px 20px;
                background:linear-gradient(135deg,rgba(16,185,129,0.1),rgba(16,185,129,0.05));
                border-radius:20px;border:2px solid rgba(16,185,129,0.3);margin:10px 0;">
                <div style="font-size:3rem;margin-bottom:16px;">✅</div>
                <h3 style="color:#10B981;margin:0 0 8px;">Folha Submetida com Sucesso!</h3>
                <p style="color:#94A3B8;font-size:0.9rem;margin:0 0 20px;">
                    {modo_label} · #{st.session_state.fp_folha_id}
                </p>
                <div style="background:#0F172A;border-radius:12px;padding:14px 20px;
                    font-family:monospace;font-size:0.82rem;color:#10B981;
                    display:inline-block;">
                    📋 {st.session_state.fp_obra}<br>
                    📅 {st.session_state.fp_periodo}<br>
                    ⏱️ {fh(st.session_state.fp_total_h)}<br>
                    🔒 #{st.session_state.fp_folha_id}
                </div>
                <p style="color:#64748B;font-size:0.78rem;margin:16px 0 0;">
                    O Admin foi notificado. A folha está visível em Faturação → Folhas de Ponto.
                </p>
            </div>""", unsafe_allow_html=True)

            st.balloons()

            if st.button("➕ Criar Nova Folha", use_container_width=True,
                         type="primary", key="btn_nova_folha"):
                for k in ['fp_step','fp_html','fp_total_h','fp_obra','fp_periodo',
                          'fp_regs','fp_responsavel','fp_modo_assin','fp_folha_id']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state['_menu_locked'] = True
                st.rerun()

        # ── Histórico de folhas emitidas ──────────────────────────────────────
        if not folhas_db.empty:
            with st.expander("📁 Histórico de Folhas Emitidas"):
                cols_f = [c for c in ['ID','Obra','Periodo','Responsavel',
                                       'Data_Assinatura','Tipo_Assinatura','Status']
                          if c in folhas_db.columns]
                st.dataframe(folhas_db[cols_f].tail(20),
                             use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — HSE
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[4]:
        st.markdown("### 🛡️ Segurança & HSE")
        sub_r, sub_rep, sub_list = st.tabs(["📋 Regras de Ouro","⚠️ Reportar","📊 Incidentes"])

        with sub_r:
            for ic, tit, des in REGRAS_OURO:
                with st.expander(f"{ic} {tit}"):
                    st.write(des)

        with sub_rep:
            with st.form("hse_ch_form"):
                o_hse = st.selectbox("Obra",
                    obras_db['Obra'].unique().tolist() if not obras_db.empty else ["Geral"])
                g_hse = st.selectbox("Gravidade", ["Baixa","Média","Alta (Crítica)"])
                d_hse = st.text_area("Descrição")
                if st.form_submit_button("🛡️ Submeter Alerta HSE",
                                         use_container_width=True, type="primary"):
                    if d_hse:
                        ni = pd.DataFrame([{
                            "ID":         str(uuid.uuid4())[:8].upper(),
                            "Data":       date.today().strftime("%d/%m/%Y"),
                            "Utilizador": user_nome,
                            "Obra":       o_hse,
                            "Status":     "Aberto",
                            "Gravidade":  g_hse,
                            "Descricao":  d_hse,
                            "Tipo":       "HSE",
                        }])
                        upd = pd.concat([incs_db, ni], ignore_index=True) \
                              if not incs_db.empty else ni
                        save_db(upd, "incidentes.csv")
                        inv("incidentes.csv")
                        st.success("✅ Alerta HSE submetido!")
                        st.session_state['_menu_locked'] = True
                        st.rerun()

        with sub_list:
            if not incs_db.empty:
                i_eq = incs_db[incs_db['Obra'].isin(obras_chefe)] \
                       if obras_chefe else incs_db
                cols_s = [c for c in ['Data','Utilizador','Obra','Descricao','Gravidade','Status']
                          if c in i_eq.columns]
                if not i_eq.empty:
                    st.dataframe(i_eq[cols_s], use_container_width=True, hide_index=True)
                else:
                    st.success("✅ Sem incidentes.")
            else:
                st.success("✅ Sem incidentes.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — PEDIDOS
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[5]:
        st.markdown("### 📦 Pedidos da Equipa")
        tecnicos_equipa = regs_equipa['Técnico'].unique().tolist() \
                          if not regs_equipa.empty else []

        sub_f, sub_e, sub_m = st.tabs(["🔧 Ferramentas","🦺 EPIs","📦 Materiais"])

        def _mostrar_pedidos(df):
            if df.empty:
                st.info("📋 Sem pedidos.")
                return
            df_eq = (df[df['Solicitante'].isin(tecnicos_equipa)]
                     if tecnicos_equipa and 'Solicitante' in df.columns else df)
            if df_eq.empty:
                st.success("✅ Sem pedidos da equipa.")
                return
            for _, ped in df_eq.iterrows():
                cor = {"Pendente":"#F59E0B","Aprovado":"#10B981",
                       "Rejeitado":"#EF4444"}.get(ped.get('Status','Pendente'),"#6B7280")
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05);border-left:4px solid {cor};
                     padding:12px;border-radius:8px;margin-bottom:8px;">
                    <b style="color:#F8FAFC;">
                        {ped.get('Descricao', ped.get('Item','N/A'))}
                    </b><br>
                    <small style="color:#94A3B8;">
                        {ped.get('Solicitante','N/A')} |
                        {ped.get('Obra','N/A')} |
                        {ped.get('Data','N/A')}
                    </small><br>
                    <small style="color:{cor};font-weight:bold;">
                        {ped.get('Status','Pendente')}
                    </small>
                </div>""", unsafe_allow_html=True)

        with sub_f: _mostrar_pedidos(req_fer_db)
        with sub_e: _mostrar_pedidos(req_epi_db)
        with sub_m: _mostrar_pedidos(req_mat_db)

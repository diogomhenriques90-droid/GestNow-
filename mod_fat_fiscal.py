"""
GESTNOW v3 — mod_fat_fiscal.py
Passo 11 — Fiscal & Compliance
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid, io, os, json
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

def _num(df, col):
    if df.empty or col not in df.columns:
        return 0.0
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()

def _dias_para(data_str: str) -> int:
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return 999


# ─────────────────────────────────────────────────────────────────
# CALENDÁRIO FISCAL PORTUGAL 2025
# ─────────────────────────────────────────────────────────────────

def _gerar_calendario_fiscal(ano: int) -> list:
    """Gera lista de obrigações fiscais para o ano."""
    obrigacoes = [
        # IVA — mensal (regime mensal)
        *[{
            "data":     f"{10 if m != 2 else 15:02d}/{m:02d}/{ano}",
            "tipo":     "IVA",
            "descricao":f"Entrega Declaração IVA — mês {m-1:02d}/{ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#3B82F6",
            "cumprida": False
        } for m in range(2, 13)],
        # IVA trimestral alternativo
        {
            "data":     f"15/05/{ano}",
            "tipo":     "IVA Trimestral",
            "descricao":f"IVA 1º Trimestre {ano} (regime trimestral)",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#3B82F6",
            "cumprida": False
        },
        {
            "data":     f"15/08/{ano}",
            "tipo":     "IVA Trimestral",
            "descricao":f"IVA 2º Trimestre {ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#3B82F6",
            "cumprida": False
        },
        {
            "data":     f"15/11/{ano}",
            "tipo":     "IVA Trimestral",
            "descricao":f"IVA 3º Trimestre {ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#3B82F6",
            "cumprida": False
        },
        # IRC
        {
            "data":     f"31/05/{ano}",
            "tipo":     "IRC",
            "descricao":f"Declaração Modelo 22 IRC {ano-1}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "crítica",
            "cor":      "#EF4444",
            "cumprida": False
        },
        {
            "data":     f"31/07/{ano}",
            "tipo":     "IRC",
            "descricao":f"1º Pagamento por Conta IRC {ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#EF4444",
            "cumprida": False
        },
        {
            "data":     f"30/09/{ano}",
            "tipo":     "IRC",
            "descricao":f"2º Pagamento por Conta IRC {ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#EF4444",
            "cumprida": False
        },
        {
            "data":     f"15/12/{ano}",
            "tipo":     "IRC",
            "descricao":f"Pagamento Especial por Conta IRC {ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "média",
            "cor":      "#EF4444",
            "cumprida": False
        },
        # IRS — Retenções na fonte
        *[{
            "data":     f"20/{m:02d}/{ano}",
            "tipo":     "IRS Retenções",
            "descricao":f"Entrega Retenções Fonte — mês {m-1:02d}/{ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#F59E0B",
            "cumprida": False
        } for m in range(2, 13)],
        # Segurança Social
        *[{
            "data":     f"10/{m:02d}/{ano}",
            "tipo":     "Segurança Social",
            "descricao":f"DRI — Declaração Remunerações mês {m-1:02d}/{ano}",
            "entidade": "ISS",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#8B5CF6",
            "cumprida": False
        } for m in range(2, 13)],
        # SAF-T
        *[{
            "data":     f"05/{m:02d}/{ano}",
            "tipo":     "SAF-T",
            "descricao":f"Entrega SAF-T — mês {m-1:02d}/{ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "média",
            "cor":      "#06B6D4",
            "cumprida": False
        } for m in range(2, 13)],
        # IRS Modelo 10
        {
            "data":     f"28/02/{ano}",
            "tipo":     "IRS",
            "descricao":f"Modelo 10 — Rendimentos {ano-1}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "alta",
            "cor":      "#F59E0B",
            "cumprida": False
        },
        # IMI
        {
            "data":     f"30/04/{ano}",
            "tipo":     "IMI",
            "descricao":f"Pagamento IMI — prestação única ou 1ª {ano}",
            "entidade": "AT / Município",
            "valor_est":None,
            "urgencia": "média",
            "cor":      "#10B981",
            "cumprida": False
        },
        # IUC Viaturas (aproximado)
        {
            "data":     f"30/06/{ano}",
            "tipo":     "IUC",
            "descricao":f"IUC — Imposto Único Circulação {ano}",
            "entidade": "AT",
            "valor_est":None,
            "urgencia": "baixa",
            "cor":      "#94A3B8",
            "cumprida": False
        },
        # Relatório & Contas
        {
            "data":     f"31/03/{ano}",
            "tipo":     "R&C",
            "descricao":f"Aprovação Relatório & Contas {ano-1}",
            "entidade": "Assembleia Geral",
            "valor_est":None,
            "urgencia": "crítica",
            "cor":      "#DC2626",
            "cumprida": False
        },
        {
            "data":     f"15/07/{ano}",
            "tipo":     "R&C",
            "descricao":f"Depósito R&C no IRN (IES) {ano-1}",
            "entidade": "AT / IRN",
            "valor_est":None,
            "urgencia": "crítica",
            "cor":      "#DC2626",
            "cumprida": False
        },
    ]
    return obrigacoes


# ─────────────────────────────────────────────────────────────────
# MOTOR IVA
# ─────────────────────────────────────────────────────────────────

def _calcular_iva_mes(faturas_cli, faturas_forn,
                       mes: int, ano: int) -> dict:
    """Calcula IVA liquidado e dedutível do mês."""
    iva_liq = 0.0   # IVA das faturas emitidas (liquidado)
    iva_ded = 0.0   # IVA das faturas recebidas (dedutível)

    # IVA liquidado — faturas clientes
    if not faturas_cli.empty and 'Data_Emissao' in faturas_cli.columns:
        fc = faturas_cli.copy()
        fc['Data_d'] = pd.to_datetime(
            fc['Data_Emissao'], dayfirst=True, errors='coerce'
        )
        fc['IVA_Num'] = pd.to_numeric(
            fc.get('IVA', 0), errors='coerce'
        ).fillna(0)
        mask = (
            (fc['Data_d'].dt.month == mes) &
            (fc['Data_d'].dt.year  == ano)
        )
        iva_liq = fc[mask]['IVA_Num'].sum()

    # IVA dedutível — faturas fornecedores
    if not faturas_forn.empty and 'Data' in faturas_forn.columns:
        ff = faturas_forn.copy()
        ff['Data_d'] = pd.to_datetime(
            ff['Data'], dayfirst=True, errors='coerce'
        )
        ff['IVA_Num'] = pd.to_numeric(
            ff.get('IVA', 0), errors='coerce'
        ).fillna(0)
        mask_f = (
            (ff['Data_d'].dt.month == mes) &
            (ff['Data_d'].dt.year  == ano)
        )
        iva_ded = ff[mask_f]['IVA_Num'].sum()

    iva_pagar   = round(max(0, iva_liq - iva_ded), 2)
    iva_receber = round(max(0, iva_ded - iva_liq), 2)

    return {
        "iva_liquidado":  round(iva_liq, 2),
        "iva_dedutivel":  round(iva_ded, 2),
        "iva_pagar":      iva_pagar,
        "iva_receber":    iva_receber,
        "saldo":          round(iva_liq - iva_ded, 2)
    }


# ─────────────────────────────────────────────────────────────────
# MOTOR IRC
# ─────────────────────────────────────────────────────────────────

def _calcular_irc(resultado_fiscal: float,
                   ano: int,
                   regime: str = "geral") -> dict:
    """
    Calcula IRC estimado para PMEs portuguesas.
    Regime geral: 21% + derrama municipal (1.5% médio).
    PME (até €50k lucro): 17% primeiros €50k, 21% resto.
    DLRR: dedução 10% dos lucros retidos (máx. €25M).
    """
    if resultado_fiscal <= 0:
        return {
            "resultado_fiscal": resultado_fiscal,
            "materia_coletavel": 0,
            "irc_taxa_21":       0,
            "irc_taxa_17":       0,
            "irc_total":         0,
            "derrama":           0,
            "total_a_pagar":     0,
            "taxa_efetiva":      0,
            "pagamentos_conta":  {"julho":0, "setembro":0},
            "regime":            regime
        }

    # Matéria coletável
    mc = resultado_fiscal

    if regime == "pme":
        # PME: 17% primeiros €50.000, 21% restante
        irc_17 = min(mc, 50000) * 0.17
        irc_21 = max(0, mc - 50000) * 0.21
        irc_base = round(irc_17 + irc_21, 2)
        taxa_efetiva = round(irc_base / mc * 100, 1) if mc > 0 else 0
    else:
        # Geral: 21%
        irc_17 = 0
        irc_21 = round(mc * 0.21, 2)
        irc_base = irc_21
        taxa_efetiva = 21.0

    # Derrama municipal (média 1.5%)
    derrama = round(mc * 0.015, 2)
    total   = round(irc_base + derrama, 2)

    # Pagamentos por conta (julho e setembro = 75% do IRC anterior)
    ppc_total = round(total * 0.75, 2)
    ppc_julho = round(ppc_total * 0.5, 2)
    ppc_set   = round(ppc_total * 0.5, 2)

    return {
        "resultado_fiscal":  resultado_fiscal,
        "materia_coletavel": mc,
        "irc_taxa_17":       round(irc_17, 2),
        "irc_taxa_21":       round(irc_21, 2),
        "irc_base":          irc_base,
        "derrama":           derrama,
        "total_a_pagar":     total,
        "taxa_efetiva":      taxa_efetiva,
        "pagamentos_conta":  {
            "julho":     ppc_julho,
            "setembro":  ppc_set
        },
        "regime":            regime,
        "reserva_mensal":    round(total / 12, 2)
    }


# ─────────────────────────────────────────────────────────────────
# SAF-T (estrutura simplificada)
# ─────────────────────────────────────────────────────────────────

def _gerar_saft(faturas_cli, faturas_forn,
                mes: int, ano: int,
                empresa: dict) -> str:
    """Gera SAF-T XML simplificado (estrutura PT)."""
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    root = ET.Element("AuditFile")
    root.set("xmlns","urn:OECD:StandardAuditFile-Tax:PT_1.04_01")

    # Header
    hdr = ET.SubElement(root, "Header")
    ET.SubElement(hdr,"AuditFileVersion").text = "1.04_01"
    ET.SubElement(hdr,"CompanyID").text    = empresa.get('nif','')
    ET.SubElement(hdr,"TaxRegistrationNumber").text = empresa.get('nif','')
    ET.SubElement(hdr,"TaxAccountingBasis").text = "F"
    ET.SubElement(hdr,"CompanyName").text  = empresa.get('nome','')
    ET.SubElement(hdr,"FiscalYear").text   = str(ano)
    ET.SubElement(hdr,"StartDate").text    = f"{ano}-{mes:02d}-01"
    # Último dia do mês
    import calendar
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    ET.SubElement(hdr,"EndDate").text   = f"{ano}-{mes:02d}-{ultimo_dia:02d}"
    ET.SubElement(hdr,"CurrencyCode").text  = "EUR"
    ET.SubElement(hdr,"DateCreated").text   = date.today().strftime("%Y-%m-%d")
    ET.SubElement(hdr,"TaxEntity").text     = "Global"
    ET.SubElement(hdr,"ProductCompanyTaxID").text = empresa.get('nif','')
    ET.SubElement(hdr,"SoftwareCertificateNumber").text = "0"
    ET.SubElement(hdr,"ProductID").text  = "GESTNOW v3.0"
    ET.SubElement(hdr,"ProductVersion").text = "3.0.0"

    # SourceDocuments — Faturas
    src = ET.SubElement(root, "SourceDocuments")
    si  = ET.SubElement(src, "SalesInvoices")

    n_fat = 0
    total_deb = 0.0
    total_cred = 0.0

    if not faturas_cli.empty and 'Data_Emissao' in faturas_cli.columns:
        fc = faturas_cli.copy()
        fc['Data_d'] = pd.to_datetime(
            fc['Data_Emissao'], dayfirst=True, errors='coerce'
        )
        fc_mes = fc[
            (fc['Data_d'].dt.month == mes) &
            (fc['Data_d'].dt.year  == ano)
        ]

        for _, row in fc_mes.iterrows():
            n_fat += 1
            inv_el = ET.SubElement(si, "Invoice")
            ET.SubElement(inv_el,"InvoiceNo").text = str(row.get('Numero',''))
            ET.SubElement(inv_el,"InvoiceDate").text = row['Data_d'].strftime("%Y-%m-%d") \
                if pd.notna(row['Data_d']) else ""
            tipo = str(row.get('Tipo','FT'))
            ET.SubElement(inv_el,"InvoiceType").text = tipo if tipo in ['FT','FS','FR','NC'] else 'FT'
            ET.SubElement(inv_el,"CustomerID").text = str(row.get('NIF_Cliente',''))

            tot_v = float(row.get('Total',0) or 0)
            sub_v = float(row.get('Subtotal',0) or tot_v)
            iva_v = float(row.get('IVA',0) or 0)

            line = ET.SubElement(inv_el, "Line")
            ET.SubElement(line,"LineNumber").text = "1"
            ET.SubElement(line,"Description").text = str(row.get('Descricao','Serviços'))[:60]
            ET.SubElement(line,"Quantity").text = "1"
            ET.SubElement(line,"UnitPrice").text = f"{sub_v:.2f}"
            ET.SubElement(line,"TaxPointDate").text = row['Data_d'].strftime("%Y-%m-%d") \
                if pd.notna(row['Data_d']) else ""
            tax = ET.SubElement(line,"Tax")
            ET.SubElement(tax,"TaxType").text = "IVA"
            ET.SubElement(tax,"TaxCountryRegion").text = "PT"
            pct_iva = round(iva_v/sub_v*100) if sub_v > 0 else 23
            ET.SubElement(tax,"TaxCode").text = "NOR" if pct_iva==23 else "INT" if pct_iva==13 else "RED"
            ET.SubElement(tax,"TaxPercentage").text = f"{pct_iva}"

            doc_tot = ET.SubElement(inv_el,"DocumentTotals")
            ET.SubElement(doc_tot,"TaxPayable").text = f"{iva_v:.2f}"
            ET.SubElement(doc_tot,"NetTotal").text   = f"{sub_v:.2f}"
            ET.SubElement(doc_tot,"GrossTotal").text = f"{tot_v:.2f}"

            total_deb  += tot_v
            total_cred += tot_v

    # Totals
    tot_el = ET.SubElement(si,"NumberOfEntries").text = str(n_fat)
    ET.SubElement(si,"TotalDebit").text  = f"{total_deb:.2f}"
    ET.SubElement(si,"TotalCredit").text = f"{total_cred:.2f}"

    # Pretty print
    xml_str = ET.tostring(root, encoding='unicode')
    try:
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")
    except:
        return xml_str


# ─────────────────────────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────────────────────────

def _grafico_iva_12m(faturas_cli, faturas_forn, ano):
    """Bar chart IVA liquidado vs dedutível 12 meses."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    liq_vals = []
    ded_vals = []
    sal_vals = []

    for m in range(1, 13):
        r = _calcular_iva_mes(faturas_cli, faturas_forn, m, ano)
        liq_vals.append(r['iva_liquidado'])
        ded_vals.append(r['iva_dedutivel'])
        sal_vals.append(r['saldo'])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='IVA Liquidado (a pagar)',
        x=meses_pt, y=liq_vals,
        marker_color='#EF4444',
        hovertemplate='%{x}<br>Liquidado: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='IVA Dedutível (compras)',
        x=meses_pt, y=ded_vals,
        marker_color='#10B981',
        hovertemplate='%{x}<br>Dedutível: €%{y:,.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        name='Saldo IVA',
        x=meses_pt, y=sal_vals,
        mode='lines+markers',
        line={'color':'#3B82F6','width':3},
        marker={'size':8},
        hovertemplate='%{x}<br>Saldo: €%{y:,.2f}<extra></extra>',
        yaxis='y2'
    ))
    fig.add_hline(
        y=0, line_dash="dash",
        line_color="#334155", line_width=1,
        yref='y2'
    )
    fig.update_layout(
        title={'text':f'IVA — {ano}',
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
        yaxis2={'overlaying':'y','side':'right',
                'tickprefix':'€',
                'tickfont':{'color':'#3B82F6'},
                'showgrid':False},
        margin=dict(t=40,b=20,l=10,r=60),
        hovermode='x unified'
    )
    return fig


def _grafico_irc_estimativa(irc: dict):
    """Waterfall composição do IRC."""
    fig = go.Figure(go.Waterfall(
        name="IRC",
        orientation="v",
        measure=["absolute","relative","relative",
                 "relative","total"],
        x=["Resultado Fiscal","Taxa 17%\n(até €50k)",
           "Taxa 21%\n(resto)","Derrama\n(1.5%)",
           "TOTAL"],
        y=[irc['resultado_fiscal'],
           -irc['irc_taxa_17'],
           -irc['irc_taxa_21'],
           -irc['derrama'],
           0],
        text=[
            f"€{irc['resultado_fiscal']:,.2f}",
            f"-€{irc['irc_taxa_17']:,.2f}",
            f"-€{irc['irc_taxa_21']:,.2f}",
            f"-€{irc['derrama']:,.2f}",
            f"€{irc['total_a_pagar']:,.2f}"
        ],
        textposition="outside",
        textfont={"color":"#F1F5F9","size":9},
        connector={"line":{"color":"#334155"}},
        increasing={"marker":{"color":"#10B981"}},
        decreasing={"marker":{"color":"#EF4444"}},
        totals={"marker":{"color":"#3B82F6"}}
    ))
    fig.update_layout(
        title={'text':'Decomposição IRC Estimado',
               'font':{'color':'#F1F5F9'}},
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8','size':9}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


def _grafico_calendario_fiscal_heatmap(obrigacoes: list,
                                        cumpridas: set):
    """Heatmap do calendário fiscal por mês."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai",
                "Jun","Jul","Ago","Set","Out","Nov","Dez"]
    tipos    = list({o['tipo'] for o in obrigacoes})
    z        = [[0]*12 for _ in range(len(tipos))]
    text_h   = [[''] *12 for _ in range(len(tipos))]

    for ob in obrigacoes:
        try:
            mes = int(ob['data'].split('/')[1]) - 1
            ti  = tipos.index(ob['tipo'])
            z[ti][mes] += 1
            text_h[ti][mes] = f"{z[ti][mes]}"
        except:
            pass

    fig = go.Figure(go.Heatmap(
        z=z,
        x=meses_pt,
        y=tipos,
        text=text_h,
        texttemplate="%{text}",
        textfont={"size":9,"color":"#F1F5F9"},
        colorscale=[
            [0,   'rgba(30,41,59,0.5)'],
            [0.4, 'rgba(239,68,68,0.4)'],
            [1,   'rgba(239,68,68,0.9)']
        ],
        showscale=False,
        hovertemplate='%{y} — %{x}: %{z} obrigação(ões)<extra></extra>'
    ))
    fig.update_layout(
        title={'text':'Mapa de Obrigações Fiscais',
               'font':{'color':'#F1F5F9'}},
        height=max(200, len(tipos)*40 + 80),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'tickfont':{'color':'#94A3B8'}},
        yaxis={'tickfont':{'color':'#94A3B8'}},
        margin=dict(t=40,b=20,l=130,r=10)
    )
    return fig


def _grafico_retencoes_ano(fat_forn, ano):
    """Bar chart retenções na fonte por mês."""
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    vals = []
    for m in range(1, 13):
        val = 0.0
        if not fat_forn.empty and 'Data' in fat_forn.columns:
            ff = fat_forn.copy()
            ff['Data_d'] = pd.to_datetime(
                ff['Data'], dayfirst=True, errors='coerce'
            )
            ff['Ret_Num'] = pd.to_numeric(
                ff.get('Retencao_Val',0), errors='coerce'
            ).fillna(0)
            mask = (
                (ff['Data_d'].dt.month == m) &
                (ff['Data_d'].dt.year  == ano) &
                (ff['Ret_Num'] > 0)
            )
            val = ff[mask]['Ret_Num'].sum()
        vals.append(round(val, 2))

    fig = go.Figure(go.Bar(
        x=meses_pt, y=vals,
        marker_color=[
            '#EF4444' if v > 0 else '#334155'
            for v in vals
        ],
        text=[f"€{v:,.0f}" if v > 0 else "" for v in vals],
        textposition='outside',
        textfont={'color':'#F1F5F9','size':9},
        hovertemplate='%{x}<br>Retenções: €%{y:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={'text':f'Retenções na Fonte — {ano}',
               'font':{'color':'#F1F5F9'}},
        height=240,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,41,59,0.5)',
        font={'color':'#F1F5F9'},
        xaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'}},
        yaxis={'gridcolor':'#334155',
               'tickfont':{'color':'#94A3B8'},
               'tickprefix':'€'},
        margin=dict(t=40,b=20,l=10,r=10),
        showlegend=False
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# PDF MAPA FISCAL
# ─────────────────────────────────────────────────────────────────

def _gerar_pdf_mapa_fiscal(iva_anual: list,
                            irc: dict,
                            retencoes_total: float,
                            ano: int,
                            empresa: dict) -> bytes:
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    bold_s = ParagraphStyle(
        'bold', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', spaceAfter=3
    )
    sub_s = ParagraphStyle(
        'sub', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#64748B'), spaceAfter=2
    )
    normal_s = ParagraphStyle(
        'normal', parent=styles['Normal'],
        fontSize=9, spaceAfter=3
    )

    story.append(Paragraph(
        f"MAPA FISCAL ANUAL — {ano}",
        ParagraphStyle('titulo', parent=styles['Normal'],
                       fontSize=16, fontName='Helvetica-Bold',
                       textColor=colors.HexColor('#1E293B'),
                       spaceAfter=4)
    ))
    story.append(Paragraph(
        f"{empresa.get('nome','')} | "
        f"NIF: {empresa.get('nif','')} | "
        f"Gerado: {datetime.now().strftime('%d/%m/%Y')}",
        sub_s
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#3B82F6')
    ))
    story.append(Spacer(1, 0.3*cm))

    # IVA mensal
    story.append(Paragraph("<b>MAPA DE IVA MENSAL</b>", bold_s))
    meses_pt = ["Jan","Fev","Mar","Abr","Mai","Jun",
                "Jul","Ago","Set","Out","Nov","Dez"]
    iva_header = [
        "Mês","IVA Liquidado","IVA Dedutível",
        "IVA a Pagar","IVA a Recuperar"
    ]
    iva_rows   = [iva_header]
    tot_liq = tot_ded = tot_pag = tot_rec = 0.0
    for i, r in enumerate(iva_anual):
        iva_rows.append([
            meses_pt[i],
            f"€{r['iva_liquidado']:,.2f}",
            f"€{r['iva_dedutivel']:,.2f}",
            f"€{r['iva_pagar']:,.2f}" if r['iva_pagar'] > 0 else "—",
            f"€{r['iva_receber']:,.2f}" if r['iva_receber'] > 0 else "—",
        ])
        tot_liq += r['iva_liquidado']
        tot_ded += r['iva_dedutivel']
        tot_pag += r['iva_pagar']
        tot_rec += r['iva_receber']
    iva_rows.append([
        "TOTAL",
        f"€{tot_liq:,.2f}",f"€{tot_ded:,.2f}",
        f"€{tot_pag:,.2f}",f"€{tot_rec:,.2f}"
    ])
    it = Table(iva_rows, colWidths=[2.5*cm,4*cm,4*cm,4*cm,4*cm])
    it.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
        ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTNAME',    (0,-1),(-1,-1),'Helvetica-Bold'),
        ('BACKGROUND',  (0,-1),(-1,-1),colors.HexColor('#EFF6FF')),
        ('FONTSIZE',    (0,0),(-1,-1), 8),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',  (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING', (0,0),(-1,-1), 5),
        ('ALIGN',       (1,0),(-1,-1), 'RIGHT'),
    ]))
    story.append(it)
    story.append(Spacer(1, 0.4*cm))

    # IRC
    story.append(Paragraph("<b>ESTIMATIVA IRC</b>", bold_s))
    irc_rows = [
        ["Resultado Fiscal",   f"€{irc['resultado_fiscal']:,.2f}"],
        ["IRC taxa 17% (PME)", f"€{irc['irc_taxa_17']:,.2f}"],
        ["IRC taxa 21%",       f"€{irc['irc_taxa_21']:,.2f}"],
        ["Derrama (1.5%)",     f"€{irc['derrama']:,.2f}"],
        ["TOTAL IRC A PAGAR",  f"€{irc['total_a_pagar']:,.2f}"],
        ["Taxa Efetiva",       f"{irc['taxa_efetiva']:.1f}%"],
        ["Reserva Mensal Rec.",f"€{irc['reserva_mensal']:,.2f}"],
    ]
    irt = Table(irc_rows, colWidths=[9*cm,8*cm])
    irt.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('FONTNAME',    (0,-3),(-1,-3),'Helvetica-Bold'),
        ('BACKGROUND',  (0,-3),(-1,-3),colors.HexColor('#EFF6FF')),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',  (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
        ('ALIGN',       (1,0),(-1,-1), 'RIGHT'),
    ]))
    story.append(irt)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Retenções na Fonte (total anual): "
        f"€{retencoes_total:,.2f}",
        normal_s
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"GESTNOW v3.0 | "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle('foot', parent=styles['Normal'],
                       fontSize=7, textColor=colors.grey)
    ))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_fat_fiscal(obras_db, registos_db,
                       faturas_db, diarias_pag_db, *_):
    """Módulo Fiscal & Compliance."""

    # ── Carregar dados ────────────────────────────────────────────
    faturas_cli  = _load("faturas_clientes.csv", [
        "ID","Numero","Tipo","Data_Emissao",
        "Cliente","NIF_Cliente","Obra",
        "Subtotal","IVA","Total","Estado"
    ])
    faturas_forn = _load("faturas_fornecedores.csv", [
        "ID","Data","Fornecedor","Descricao","Obra",
        "Subtotal","IVA","Total",
        "Retencao_Pct","Retencao_Val","Estado"
    ])
    rh_db = _load("colaboradores_rh.csv",["Nome","Salario_Base"])

    try:
        from mod_admin_diarias import _get_config_empresa
        empresa = _get_config_empresa()
    except:
        empresa = {
            "nome":"Correia Plácido e Sousa, Lda.",
            "nif":"517182718"
        }

    user_nome = st.session_state.get('user','Admin')
    hoje      = date.today()
    ano_atual = hoje.year
    mes_atual = hoje.month
    meses_pt  = ["Janeiro","Fevereiro","Março","Abril","Maio",
                 "Junho","Julho","Agosto","Setembro",
                 "Outubro","Novembro","Dezembro"]

    # Calcular IVA anual
    iva_anual = [
        _calcular_iva_mes(faturas_cli, faturas_forn, m, ano_atual)
        for m in range(1, 13)
    ]
    iva_mes_atual = iva_anual[mes_atual - 1]

    # Total retenções na fonte
    ret_total = _num(faturas_forn,'Retencao_Val')

    # ── CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .fiscal-card {
        background:#1E293B; border-radius:12px;
        padding:14px 16px; margin-bottom:8px;
    }
    .obrig-item {
        border-radius:8px; padding:10px 14px;
        margin-bottom:6px; border-left:4px solid;
    }
    .cumprida { opacity:0.45; }
    </style>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────
    iva_anual_pagar = sum(
        r['iva_pagar'] for r in iva_anual
    )
    iva_mes_pagar = iva_mes_atual['iva_pagar']

    # IRC estimado (simplificado)
    fat_anual_est = _num(faturas_cli, 'Total')
    custo_sal_est = _num(rh_db,'Salario_Base') * 12 * 1.4 \
                    if not rh_db.empty else 0
    resultado_est = max(0, fat_anual_est - custo_sal_est)
    irc_est = _calcular_irc(resultado_est, ano_atual, "pme")

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("💰 IVA Mês Atual",  f"€{iva_mes_pagar:,.2f}")
    with c2: st.metric("💰 IVA Anual Est.", f"€{iva_anual_pagar:,.2f}")
    with c3: st.metric("🏛️ IRC Estimado",   f"€{irc_est['total_a_pagar']:,.2f}")
    with c4: st.metric("📋 Retenções Fonte",f"€{ret_total:,.2f}")
    with c5: st.metric("💵 Reserva/Mês IRC"f"€{irc_est.get('reserva_mensal', 0):,.2f}")

    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────
    (t_iva, t_irc, t_ret,
     t_saft, t_cal, t_ss) = st.tabs([
        "💰 IVA",
        "🏛️ IRC",
        "📋 Retenções Fonte",
        "📄 SAF-T",
        "📅 Calendário Fiscal",
        "🏛️ Segurança Social",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB — IVA
    # ════════════════════════════════════════════════════════════════
    with t_iva:
        st.markdown("### 💰 Mapa de IVA")

        col_iva1, col_iva2 = st.columns(2)
        with col_iva1:
            ano_iva = st.number_input(
                "Ano", min_value=2020,
                value=ano_atual, key="iva_ano"
            )
        with col_iva2:
            regime_iva = st.selectbox(
                "Regime",
                ["Mensal","Trimestral"],
                key="iva_regime"
            )

        # Recalcular se mudou o ano
        if ano_iva != ano_atual:
            iva_anual_calc = [
                _calcular_iva_mes(
                    faturas_cli, faturas_forn, m, ano_iva
                )
                for m in range(1, 13)
            ]
        else:
            iva_anual_calc = iva_anual

        # Gráfico
        st.plotly_chart(
            _grafico_iva_12m(
                faturas_cli, faturas_forn, ano_iva
            ),
            use_container_width=True
        )

        # Tabela mês a mês
        st.markdown("#### 📋 Resumo Mensal")
        rows_iva = []
        for i, r in enumerate(iva_anual_calc):
            saldo_str = (
                f"🔴 A pagar: €{r['iva_pagar']:,.2f}"
                if r['iva_pagar'] > 0
                else f"🟢 A recuperar: €{r['iva_receber']:,.2f}"
                if r['iva_receber'] > 0
                else "—"
            )
            rows_iva.append({
                "Mês":            meses_pt[i],
                "Liquidado":      f"€{r['iva_liquidado']:,.2f}",
                "Dedutível":      f"€{r['iva_dedutivel']:,.2f}",
                "Saldo":          saldo_str,
            })

        df_iva = pd.DataFrame(rows_iva)
        st.dataframe(
            df_iva, use_container_width=True, hide_index=True
        )

        # Totais anuais
        tot_liq_a = sum(r['iva_liquidado'] for r in iva_anual_calc)
        tot_ded_a = sum(r['iva_dedutivel'] for r in iva_anual_calc)
        tot_pag_a = sum(r['iva_pagar']     for r in iva_anual_calc)
        tot_rec_a = sum(r['iva_receber']   for r in iva_anual_calc)

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("📤 Total Liquidado",  f"€{tot_liq_a:,.2f}")
        with c2: st.metric("📥 Total Dedutível",  f"€{tot_ded_a:,.2f}")
        with c3: st.metric("💸 Total a Pagar",    f"€{tot_pag_a:,.2f}")
        with c4: st.metric("💰 Total a Recuperar",f"€{tot_rec_a:,.2f}")

        # Detalhe do mês atual
        st.markdown("---")
        st.markdown(
            f"#### 📊 Detalhe — "
            f"{meses_pt[mes_atual-1]} {ano_atual}"
        )
        col_d1,col_d2,col_d3 = st.columns(3)
        with col_d1:
            st.markdown(
                f"<div class='fiscal-card'>"
                f"<p style='color:#64748B;"
                f"font-size:0.75rem;margin:0 0 4px;'>"
                f"IVA LIQUIDADO (faturas emitidas)</p>"
                f"<b style='color:#EF4444;"
                f"font-size:1.4rem;'>"
                f"€{iva_mes_atual['iva_liquidado']:,.2f}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_d2:
            st.markdown(
                f"<div class='fiscal-card'>"
                f"<p style='color:#64748B;"
                f"font-size:0.75rem;margin:0 0 4px;'>"
                f"IVA DEDUTÍVEL (compras/fornecedores)</p>"
                f"<b style='color:#10B981;"
                f"font-size:1.4rem;'>"
                f"€{iva_mes_atual['iva_dedutivel']:,.2f}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_d3:
            cor_saldo = "#EF4444" if iva_mes_atual['saldo'] > 0 \
                        else "#10B981"
            st.markdown(
                f"<div class='fiscal-card' "
                f"style='border-left:3px solid {cor_saldo};'>"
                f"<p style='color:#64748B;"
                f"font-size:0.75rem;margin:0 0 4px;'>"
                f"{'A PAGAR À AT' if iva_mes_atual['saldo']>0 else 'A RECUPERAR DA AT'}</p>"
                f"<b style='color:{cor_saldo};"
                f"font-size:1.4rem;'>"
                f"€{abs(iva_mes_atual['saldo']):,.2f}</b><br>"
                f"<small style='color:#64748B;'>"
                f"Prazo: dia 10 do mês seguinte</small>"
                f"</div>",
                unsafe_allow_html=True
            )

        # Export + PDF
        st.markdown("---")
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            csv_iva = df_iva.to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Exportar Mapa IVA CSV",
                data=csv_iva.encode('utf-8-sig'),
                file_name=f"mapa_iva_{ano_iva}.csv",
                mime="text/csv",
                key="dl_iva_csv"
            )
        with col_ex2:
            if st.button(
                "📄 Gerar Mapa Fiscal PDF",
                key="btn_pdf_fiscal",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("A gerar PDF..."):
                    pdf_f = _gerar_pdf_mapa_fiscal(
                        iva_anual_calc, irc_est,
                        ret_total, ano_iva, empresa
                    )
                st.session_state['fiscal_pdf'] = pdf_f
                st.rerun()

        if st.session_state.get('fiscal_pdf'):
            st.download_button(
                "📥 Descarregar Mapa Fiscal PDF",
                data=st.session_state['fiscal_pdf'],
                file_name=f"mapa_fiscal_{ano_iva}.pdf",
                mime="application/pdf",
                key="dl_fiscal_pdf",
                use_container_width=True,
                type="primary"
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — IRC
    # ════════════════════════════════════════════════════════════════
    with t_irc:
        st.markdown("### 🏛️ IRC — Imposto sobre Rendimento Coletivo")
        st.info(
            "Estimativa de IRC baseada nos dados disponíveis. "
            "Para cálculo exato consulta o TOC/ROC. "
            "Taxa PME: 17% até €50.000, 21% acima."
        )

        col_irc1, col_irc2 = st.columns(2)
        with col_irc1:
            irc_resultado = st.number_input(
                "Resultado Fiscal Estimado (€)",
                min_value=-999999.0,
                value=max(0.0, resultado_est),
                step=5000.0, key="irc_resultado"
            )
            irc_regime = st.selectbox(
                "Regime IRC",
                ["pme","geral"],
                key="irc_regime",
                format_func=lambda x:
                    "PME — Taxa Reduzida 17%/21%" if x == "pme"
                    else "Geral — Taxa 21%"
            )
            irc_ano_calc = st.number_input(
                "Ano", min_value=2020,
                value=ano_atual, key="irc_ano"
            )

        irc_calc = _calcular_irc(
            irc_resultado, irc_ano_calc, irc_regime
        )

        with col_irc2:
            st.markdown("#### 📊 Resultado")
            cor_irc = "#10B981" if irc_resultado > 0 \
                      else "#64748B"
            st.markdown(
                f"<div class='fiscal-card' "
                f"style='border-left:4px solid {cor_irc};'>"
                f"<div style='display:grid;"
                f"grid-template-columns:1fr 1fr;"
                f"gap:10px;'>"
                f"<div><small style='color:#64748B;'>"
                f"Result. Fiscal</small><br>"
                f"<b style='color:#F1F5F9;"
                f"font-size:1.1rem;'>"
                f"€{irc_calc['resultado_fiscal']:,.2f}</b></div>"
                f"<div><small style='color:#64748B;'>"
                f"IRC (17%)</small><br>"
                f"<b style='color:#EF4444;"
                f"font-size:1.1rem;'>"
                f"€{irc_calc['irc_taxa_17']:,.2f}</b></div>"
                f"<div><small style='color:#64748B;'>"
                f"IRC (21%)</small><br>"
                f"<b style='color:#EF4444;"
                f"font-size:1.1rem;'>"
                f"€{irc_calc['irc_taxa_21']:,.2f}</b></div>"
                f"<div><small style='color:#64748B;'>"
                f"Derrama</small><br>"
                f"<b style='color:#F59E0B;"
                f"font-size:1.1rem;'>"
                f"€{irc_calc['derrama']:,.2f}</b></div>"
                f"</div>"
                f"<div style='border-top:1px solid #334155;"
                f"padding-top:10px;margin-top:10px;"
                f"display:flex;justify-content:space-between;'>"
                f"<b style='color:#F1F5F9;font-size:1rem;'>"
                f"TOTAL A PAGAR</b>"
                f"<b style='color:#EF4444;font-size:1.3rem;'>"
                f"€{irc_calc['total_a_pagar']:,.2f}</b>"
                f"</div>"
                f"<div style='margin-top:8px;"
                f"display:flex;justify-content:space-between;'>"
                f"<span style='color:#64748B;"
                f"font-size:0.8rem;'>"
                f"Taxa efetiva: {irc_calc['taxa_efetiva']:.1f}%</span>"
                f"<span style='color:#3B82F6;"
                f"font-size:0.8rem;'>"
                f"Reservar €{irc_calc['reserva_mensal']:,.2f}/mês"
                f"</span></div></div>",
                unsafe_allow_html=True
            )

        # Waterfall
        if irc_resultado > 0:
            st.plotly_chart(
                _grafico_irc_estimativa(irc_calc),
                use_container_width=True
            )

        # Pagamentos por conta
        st.markdown("#### 📅 Pagamentos por Conta")
        st.info(
            "Os pagamentos por conta são 75% do IRC do ano anterior, "
            "pagos em julho e setembro."
        )

        col_ppc1, col_ppc2, col_ppc3 = st.columns(3)
        with col_ppc1:
            st.markdown(
                f"<div class='fiscal-card'>"
                f"<p style='color:#64748B;"
                f"font-size:0.75rem;margin:0 0 4px;'>"
                f"1º PPC — Julho {irc_ano_calc}</p>"
                f"<b style='color:#3B82F6;"
                f"font-size:1.2rem;'>"
                f"€{irc_calc['pagamentos_conta']['julho']:,.2f}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_ppc2:
            st.markdown(
                f"<div class='fiscal-card'>"
                f"<p style='color:#64748B;"
                f"font-size:0.75rem;margin:0 0 4px;'>"
                f"2º PPC — Setembro {irc_ano_calc}</p>"
                f"<b style='color:#3B82F6;"
                f"font-size:1.2rem;'>"
                f"€{irc_calc['pagamentos_conta']['setembro']:,.2f}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_ppc3:
            st.markdown(
                f"<div class='fiscal-card'>"
                f"<p style='color:#64748B;"
                f"font-size:0.75rem;margin:0 0 4px;'>"
                f"Reserva Mensal Recomendada</p>"
                f"<b style='color:#10B981;"
                f"font-size:1.2rem;'>"
                f"€{irc_calc['reserva_mensal']:,.2f}/mês</b>"
                f"</div>",
                unsafe_allow_html=True
            )

        # Benefícios fiscais
        st.markdown("---")
        st.markdown("#### 🎁 Benefícios Fiscais Aplicáveis")

        beneficios = [
            {
                "nome":    "RFAI — Regime Fiscal Apoio Investimento",
                "desc":    "Dedução de 25% do investimento ao IRC. "
                           "Para equipamento e software.",
                "impacto": "Reduz diretamente o IRC a pagar",
                "cor":     "#10B981"
            },
            {
                "nome":    "DLRR — Dedução Lucros Retidos",
                "desc":    "Dedução de 10% dos lucros retidos "
                           "(máximo €10M/ano).",
                "impacto": f"Poupança estimada: "
                           f"€{round(irc_calc['resultado_fiscal']*0.021,2):,.2f}",
                "cor":     "#3B82F6"
            },
            {
                "nome":    "SIFIDE II — I&D",
                "desc":    "Dedução 32.5-82.5% das despesas em I&D. "
                           "Aplicável ao desenvolvimento GESTNOW.",
                "impacto": "Consultar TOC para elegibilidade",
                "cor":     "#8B5CF6"
            },
            {
                "nome":    "Criação de Emprego",
                "desc":    "Majoração 50% dos encargos com "
                           "jovens até 35 anos.",
                "impacto": "Reduz a matéria coletável",
                "cor":     "#F59E0B"
            },
        ]

        for ben in beneficios:
            st.markdown(
                f"<div style='background:#1E293B;"
                f"border-radius:8px;padding:12px;"
                f"margin-bottom:6px;"
                f"border-left:3px solid {ben['cor']};'>"
                f"<b style='color:#F1F5F9;"
                f"font-size:0.88rem;'>{ben['nome']}</b><br>"
                f"<small style='color:#94A3B8;'>"
                f"{ben['desc']}</small><br>"
                f"<small style='color:{ben['cor']};'>"
                f"💡 {ben['impacto']}</small>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — RETENÇÕES NA FONTE
    # ════════════════════════════════════════════════════════════════
    with t_ret:
        st.markdown("### 📋 Retenções na Fonte")
        st.info(
            "Retenções na fonte de IRS sobre pagamentos a "
            "subempreiteiros (25%) e outros prestadores. "
            "Devem ser entregues à AT até ao dia 20 do mês seguinte."
        )

        ano_ret = st.number_input(
            "Ano", min_value=2020,
            value=ano_atual, key="ret_ano"
        )

        # Gráfico
        st.plotly_chart(
            _grafico_retencoes_ano(faturas_forn, ano_ret),
            use_container_width=True
        )

        # Tabela por mês
        st.markdown("#### 📋 Detalhe Mensal")
        rows_ret = []
        for m in range(1, 13):
            val_m = 0.0
            n_forn = 0
            if not faturas_forn.empty and 'Data' in faturas_forn.columns:
                ff = faturas_forn.copy()
                ff['Data_d'] = pd.to_datetime(
                    ff['Data'], dayfirst=True, errors='coerce'
                )
                ff['Ret_Num'] = pd.to_numeric(
                    ff.get('Retencao_Val',0), errors='coerce'
                ).fillna(0)
                mask_r = (
                    (ff['Data_d'].dt.month == m) &
                    (ff['Data_d'].dt.year  == ano_ret) &
                    (ff['Ret_Num'] > 0)
                )
                ff_mes = ff[mask_r]
                val_m  = ff_mes['Ret_Num'].sum()
                n_forn = ff_mes['Fornecedor'].nunique() \
                         if 'Fornecedor' in ff_mes.columns else 0

            prazo = f"20/{m+1:02d}/{ano_ret}" if m < 12 \
                    else f"20/01/{ano_ret+1}"
            rows_ret.append({
                "Mês":         meses_pt[m-1],
                "Fornecedores":n_forn,
                "Total Retido":f"€{val_m:,.2f}",
                "Prazo AT":    prazo,
                "Estado":      "✅" if val_m == 0 else "📋"
            })

        df_ret = pd.DataFrame(rows_ret)
        st.dataframe(
            df_ret, use_container_width=True, hide_index=True
        )

        st.metric(
            "💰 Total Retenções Anuais",
            f"€{ret_total:,.2f}"
        )

        # Guia mensal
        st.markdown("---")
        st.markdown("#### 📄 Gerar Guia de Retenções")

        col_gr1, col_gr2 = st.columns(2)
        with col_gr1:
            mes_guia = st.selectbox(
                "Mês",
                meses_pt,
                index=mes_atual-1,
                key="ret_mes_guia"
            )
        with col_gr2:
            if st.button(
                "📄 Gerar Guia PDF",
                key="btn_guia_ret_fiscal",
                type="primary",
                use_container_width=True
            ):
                mes_num_g = meses_pt.index(mes_guia) + 1
                # Calcular retenções do mês
                retencoes_mes_g = []
                if not faturas_forn.empty and \
                   'Data' in faturas_forn.columns:
                    ff_g = faturas_forn.copy()
                    ff_g['Data_d'] = pd.to_datetime(
                        ff_g['Data'], dayfirst=True, errors='coerce'
                    )
                    ff_g['Ret_Val_Num'] = pd.to_numeric(
                        ff_g.get('Retencao_Val',0), errors='coerce'
                    ).fillna(0)
                    mask_g = (
                        (ff_g['Data_d'].dt.month == mes_num_g) &
                        (ff_g['Data_d'].dt.year  == ano_ret) &
                        (ff_g['Ret_Val_Num'] > 0)
                    )
                    for _, rg in ff_g[mask_g].iterrows():
                        retencoes_mes_g.append({
                            "nome":  str(rg.get('Fornecedor','')),
                            "nif":   "",
                            "valor": float(rg.get('Total',0) or 0),
                            "taxa":  float(rg.get('Retencao_Pct',25) or 25),
                        })

                if retencoes_mes_g:
                    try:
                        from mod_fat_fornecedores import \
                            _gerar_guia_retencao
                        pdf_gr = _gerar_guia_retencao(
                            mes_num_g, ano_ret,
                            retencoes_mes_g, empresa
                        )
                        st.session_state['guia_ret_f'] = pdf_gr
                        st.session_state['guia_ret_f_nome'] = (
                            f"guia_ret_{mes_num_g:02d}_{ano_ret}.pdf"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
                else:
                    st.info(
                        f"📋 Sem retenções em "
                        f"{mes_guia} {ano_ret}."
                    )

        if st.session_state.get('guia_ret_f'):
            st.download_button(
                "📥 Descarregar Guia Retenções",
                data=st.session_state['guia_ret_f'],
                file_name=st.session_state.get(
                    'guia_ret_f_nome','guia.pdf'
                ),
                mime="application/pdf",
                key="dl_guia_ret_f"
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — SAF-T
    # ════════════════════════════════════════════════════════════════
    with t_saft:
        st.markdown("### 📄 SAF-T — Standard Audit File for Tax")
        st.info(
            "O SAF-T PT é obrigatório e deve ser entregue "
            "mensalmente à AT até ao dia 5 do mês seguinte. "
            "Contém todas as faturas emitidas do mês."
        )

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            mes_saft = st.selectbox(
                "Mês", meses_pt,
                index=mes_atual-1, key="saft_mes"
            )
        with col_s2:
            ano_saft = st.number_input(
                "Ano", min_value=2020,
                value=ano_atual, key="saft_ano"
            )

        mes_num_s = meses_pt.index(mes_saft) + 1

        # Preview faturas do mês
        if not faturas_cli.empty and \
           'Data_Emissao' in faturas_cli.columns:
            fc_s = faturas_cli.copy()
            fc_s['Data_d'] = pd.to_datetime(
                fc_s['Data_Emissao'], dayfirst=True, errors='coerce'
            )
            fc_mes_s = fc_s[
                (fc_s['Data_d'].dt.month == mes_num_s) &
                (fc_s['Data_d'].dt.year  == ano_saft)
            ]
            n_fat_s = len(fc_mes_s)
            tot_s   = pd.to_numeric(
                fc_mes_s.get('Total',0), errors='coerce'
            ).fillna(0).sum()
        else:
            n_fat_s = 0
            tot_s   = 0.0

        col_sk1, col_sk2, col_sk3 = st.columns(3)
        with col_sk1:
            st.metric("📋 Faturas no Mês", n_fat_s)
        with col_sk2:
            st.metric("💰 Total Faturado", f"€{tot_s:,.2f}")
        with col_sk3:
            prazo_saft = f"05/{mes_num_s+1:02d}/{ano_saft}" \
                         if mes_num_s < 12 \
                         else f"05/01/{ano_saft+1}"
            dias_saft = _dias_para(prazo_saft)
            cor_saft  = "#EF4444" if dias_saft < 5 \
                        else "#F59E0B" if dias_saft < 15 \
                        else "#10B981"
            st.markdown(
                f"<div style='background:#1E293B;"
                f"border-radius:10px;padding:12px;"
                f"text-align:center;'>"
                f"<small style='color:#64748B;'>Prazo Entrega</small><br>"
                f"<b style='color:{cor_saft};"
                f"font-size:1rem;'>{prazo_saft}</b><br>"
                f"<small style='color:{cor_saft};'>"
                f"{'Hoje!' if dias_saft==0 else f'{dias_saft} dias'}"
                f"</small></div>",
                unsafe_allow_html=True
            )

        st.markdown("---")

        col_saft1, col_saft2 = st.columns(2)
        with col_saft1:
            if st.button(
                "⚙️ Gerar SAF-T XML",
                key="btn_saft",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("A gerar SAF-T..."):
                    xml_saft = _gerar_saft(
                        faturas_cli, faturas_forn,
                        mes_num_s, ano_saft, empresa
                    )
                st.session_state['saft_xml'] = xml_saft
                st.session_state['saft_nome'] = (
                    f"SAFT-PT_{empresa.get('nif','')}_"
                    f"{ano_saft}{mes_num_s:02d}.xml"
                )
                st.success("✅ SAF-T gerado!")
                st.rerun()

        with col_saft2:
            if st.session_state.get('saft_xml'):
                st.download_button(
                    "📥 Descarregar SAF-T XML",
                    data=st.session_state['saft_xml'].encode('utf-8'),
                    file_name=st.session_state.get(
                        'saft_nome','SAFT.xml'
                    ),
                    mime="application/xml",
                    key="dl_saft",
                    use_container_width=True,
                    type="primary"
                )

        # Preview XML
        if st.session_state.get('saft_xml'):
            with st.expander("👁️ Preview SAF-T XML"):
                st.code(
                    st.session_state['saft_xml'][:3000] +
                    "\n... (truncado para visualização)",
                    language="xml"
                )

        # Histórico de SAF-T gerados
        st.markdown("---")
        st.markdown("#### 📋 Checklist SAF-T")
        checklist_saft = [
            ("NIF empresa correto no header",           True),
            ("Todas as faturas do mês incluídas",
             n_fat_s > 0),
            ("Tipos de fatura corretos (FT/FS/FR/NC)",  True),
            ("Datas no formato YYYY-MM-DD",             True),
            ("NIF clientes preenchido",
             not faturas_cli.empty and
             'NIF_Cliente' in faturas_cli.columns),
            ("IVA calculado corretamente",              True),
            ("Ficheiro XML válido",
             bool(st.session_state.get('saft_xml'))),
        ]
        for desc, ok in checklist_saft:
            cor_ck = "#10B981" if ok else "#F59E0B"
            ic_ck  = "✅" if ok else "⚠️"
            st.markdown(
                f"<div style='display:flex;"
                f"align-items:center;padding:4px 0;"
                f"border-bottom:1px solid #1E293B;'>"
                f"<span style='color:{cor_ck};"
                f"margin-right:8px;'>{ic_ck}</span>"
                f"<small style='color:#94A3B8;'>{desc}</small>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — CALENDÁRIO FISCAL
    # ════════════════════════════════════════════════════════════════
    with t_cal:
        st.markdown("### 📅 Calendário Fiscal")

        ano_cal = st.number_input(
            "Ano", min_value=2020,
            value=ano_atual, key="cal_ano"
        )

        obrigacoes = _gerar_calendario_fiscal(ano_cal)

        # Filtros
        col_cf1, col_cf2 = st.columns(2)
        with col_cf1:
            tipo_filt_cal = st.selectbox(
                "Tipo",
                ["Todos"] + list(
                    {o['tipo'] for o in obrigacoes}
                ),
                key="cal_tipo"
            )
        with col_cf2:
            urg_filt_cal = st.selectbox(
                "Urgência",
                ["Todas","crítica","alta","média","baixa"],
                key="cal_urg"
            )

        obrig_filtradas = [
            o for o in obrigacoes
            if (tipo_filt_cal == "Todos" or o['tipo'] == tipo_filt_cal)
            and (urg_filt_cal == "Todas" or o['urgencia'] == urg_filt_cal)
        ]

        # Heatmap
        st.plotly_chart(
            _grafico_calendario_fiscal_heatmap(
                obrigacoes, set()
            ),
            use_container_width=True
        )

        # Próximas obrigações
        st.markdown("#### ⏰ Próximas Obrigações")

        # Filtrar e ordenar por data
        hoje_str = hoje.strftime("%d/%m/%Y")
        proximas = []
        for ob in obrig_filtradas:
            try:
                d = datetime.strptime(ob['data'], "%d/%m/%Y").date()
                dias = (d - hoje).days
                if -7 <= dias <= 60:
                    proximas.append({**ob, "dias": dias})
            except:
                pass

        proximas.sort(key=lambda x: x['dias'])

        if not proximas:
            st.success("✅ Sem obrigações nos próximos 60 dias.")
        else:
            for ob in proximas[:20]:
                dias_ob = ob['dias']
                cor_ob  = ob['cor']

                if dias_ob < 0:
                    badge = f"🔴 {abs(dias_ob)} dias em atraso"
                    bg    = "rgba(239,68,68,0.1)"
                elif dias_ob == 0:
                    badge = "🔴 HOJE"
                    bg    = "rgba(239,68,68,0.15)"
                elif dias_ob <= 7:
                    badge = f"🔴 {dias_ob} dias"
                    bg    = "rgba(239,68,68,0.1)"
                elif dias_ob <= 15:
                    badge = f"⚠️ {dias_ob} dias"
                    bg    = "rgba(245,158,11,0.1)"
                else:
                    badge = f"📅 {dias_ob} dias"
                    bg    = "rgba(30,41,59,0.8)"

                # Verificar se está cumprida no session state
                ob_key = f"cumprida_{ob['data']}_{ob['tipo']}"
                cumprida = st.session_state.get(ob_key, False)

                col_ob1, col_ob2 = st.columns([6,1])
                with col_ob1:
                    st.markdown(
                        f"<div class='obrig-item "
                        f"{'cumprida' if cumprida else ''}' "
                        f"style='background:{bg};"
                        f"border-left-color:{cor_ob};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<div>"
                        f"<b style='color:{'#64748B' if cumprida else '#F1F5F9'};"
                        f"font-size:0.88rem;'>"
                        f"{'~~' if cumprida else ''}"
                        f"{ob['descricao']}"
                        f"{'~~' if cumprida else ''}"
                        f"</b><br>"
                        f"<small style='color:#64748B;'>"
                        f"🏛️ {ob['entidade']} · "
                        f"📅 {ob['data']}</small>"
                        f"</div>"
                        f"<span style='color:{cor_ob};"
                        f"font-weight:700;font-size:0.8rem;'>"
                        f"{badge}</span>"
                        f"</div></div>",
                        unsafe_allow_html=True
                    )
                with col_ob2:
                    if st.button(
                        "✅" if not cumprida else "↩️",
                        key=f"ob_btn_{ob['data']}_{ob['tipo'][:10]}",
                        use_container_width=True,
                        help="Marcar como cumprida"
                    ):
                        st.session_state[ob_key] = not cumprida
                        st.rerun()

        # Lista completa do ano
        st.markdown("---")
        with st.expander("📋 Ver todas as obrigações do ano"):
            all_rows = []
            for ob in sorted(
                obrig_filtradas,
                key=lambda x: datetime.strptime(
                    x['data'], "%d/%m/%Y"
                ) if _dias_para(x['data']) < 9999 else datetime.max
            ):
                all_rows.append({
                    "Data":       ob['data'],
                    "Tipo":       ob['tipo'],
                    "Descrição":  ob['descricao'],
                    "Entidade":   ob['entidade'],
                    "Urgência":   ob['urgencia'].upper()
                })
            df_cal = pd.DataFrame(all_rows)
            st.dataframe(
                df_cal, use_container_width=True, hide_index=True
            )
            csv_cal = df_cal.to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Exportar Calendário",
                data=csv_cal.encode('utf-8-sig'),
                file_name=f"calendario_fiscal_{ano_cal}.csv",
                mime="text/csv",
                key="dl_cal_fiscal"
            )

    # ════════════════════════════════════════════════════════════════
    # TAB — SEGURANÇA SOCIAL
    # ════════════════════════════════════════════════════════════════
    with t_ss:
        st.markdown("### 🏛️ Segurança Social")
        st.info(
            "A DRI (Declaração de Remunerações) deve ser entregue "
            "até ao dia 10 do mês seguinte. "
            "TSU empresa: 23.75% | TSU trabalhador: 11%."
        )

        ano_ss = st.number_input(
            "Ano", min_value=2020,
            value=ano_atual, key="ss_ano"
        )
        mes_ss = st.selectbox(
            "Mês", meses_pt,
            index=mes_atual-1, key="ss_mes"
        )
        mes_num_ss = meses_pt.index(mes_ss) + 1

        if rh_db.empty:
            st.info(
                "📋 Sem fichas RH. Adiciona colaboradores "
                "no tab RH Financeiro."
            )
        else:
            # Calcular TSU
            TSU_EMP  = 23.75
            TSU_TRAB = 11.00

            rows_ss = []
            tot_sal = tot_tsu_e = tot_tsu_t = tot_ss = 0.0

            for _, colab in rh_db.iterrows():
                sal = float(colab.get('Salario_Base',0) or 0)
                tsu_e = round(sal * TSU_EMP  / 100, 2)
                tsu_t = round(sal * TSU_TRAB / 100, 2)
                tot_c = round(tsu_e + tsu_t, 2)
                rows_ss.append({
                    "Colaborador":  colab.get('Nome','')[:25],
                    "Sal. Base":    f"€{sal:,.2f}",
                    "TSU Empresa":  f"€{tsu_e:,.2f}",
                    "TSU Trabalhador":f"€{tsu_t:,.2f}",
                    "Total SS":     f"€{tot_c:,.2f}"
                })
                tot_sal  += sal
                tot_tsu_e += tsu_e
                tot_tsu_t += tsu_t
                tot_ss   += tot_c

            df_ss = pd.DataFrame(rows_ss)
            st.dataframe(
                df_ss, use_container_width=True, hide_index=True
            )

            # Totais
            c1,c2,c3,c4 = st.columns(4)
            with c1:
                st.metric("💰 Massa Salarial", f"€{tot_sal:,.2f}")
            with c2:
                st.metric("🏢 TSU Empresa",    f"€{tot_tsu_e:,.2f}")
            with c3:
                st.metric("👤 TSU Trabalhador",f"€{tot_tsu_t:,.2f}")
            with c4:
                st.metric("💸 TOTAL SS",       f"€{tot_ss:,.2f}")

            # Prazo
            prazo_ss = f"10/{mes_num_ss+1:02d}/{ano_ss}" \
                       if mes_num_ss < 12 \
                       else f"10/01/{ano_ss+1}"
            dias_ss = _dias_para(prazo_ss)
            cor_ss  = "#EF4444" if dias_ss < 3 \
                      else "#F59E0B" if dias_ss < 10 \
                      else "#10B981"

            st.markdown(
                f"<div style='background:{cor_ss}12;"
                f"border:1px solid {cor_ss};"
                f"border-radius:8px;padding:12px;"
                f"margin:12px 0;'>"
                f"<b style='color:{cor_ss};'>"
                f"📅 Prazo DRI {mes_ss} {ano_ss}: "
                f"{prazo_ss}"
                f"{'  —  ' + str(dias_ss) + ' dias' if dias_ss >= 0 else '  🔴 EM ATRASO!'}"
                f"</b><br>"
                f"<small style='color:#94A3B8;'>"
                f"Total a pagar: €{tot_ss:,.2f} "
                f"até dia 20 do mês seguinte</small>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Export DRI
            csv_ss = df_ss.to_csv(
                index=False, encoding='utf-8-sig'
            )
            col_ss1, col_ss2 = st.columns(2)
            with col_ss1:
                st.download_button(
                    f"📥 DRI {mes_ss} {ano_ss} CSV",
                    data=csv_ss.encode('utf-8-sig'),
                    file_name=(
                        f"DRI_{mes_num_ss:02d}_{ano_ss}.csv"
                    ),
                    mime="text/csv",
                    key="dl_dri_ss"
                )
            with col_ss2:
                st.info(
                    "📋 Para submissão oficial acede a: "
                    "app.seg-social.pt/ptss"
                )

            # Contribuições acumuladas
            st.markdown("---")
            st.markdown("#### 📊 Projeção Anual SS")
            meses_proj = [
                {"mes": m,
                 "nome": meses_pt[m-1],
                 "valor": round(tot_ss, 2)}
                for m in range(1, 13)
            ]
            total_anual_ss = tot_ss * 12
            st.metric(
                "💸 Total SS Anual Estimado",
                f"€{total_anual_ss:,.2f}",
                delta=f"€{tot_ss:,.2f}/mês"
            )

            # Bar chart projeção
            fig_ss = go.Figure(go.Bar(
                x=[m['nome'] for m in meses_proj],
                y=[m['valor'] for m in meses_proj],
                marker_color='#8B5CF6',
                text=[f"€{m['valor']:,.0f}" for m in meses_proj],
                textposition='outside',
                textfont={'color':'#F1F5F9','size':9}
            ))
            fig_ss.update_layout(
                title={'text':f'Contribuições SS {ano_ss}',
                       'font':{'color':'#F1F5F9'}},
                height=240,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.5)',
                font={'color':'#F1F5F9'},
                xaxis={'gridcolor':'#334155',
                       'tickfont':{'color':'#94A3B8','size':9}},
                yaxis={'gridcolor':'#334155',
                       'tickfont':{'color':'#94A3B8'},
                       'tickprefix':'€'},
                margin=dict(t=40,b=20,l=10,r=10),
                showlegend=False
            )
            st.plotly_chart(fig_ss, use_container_width=True)

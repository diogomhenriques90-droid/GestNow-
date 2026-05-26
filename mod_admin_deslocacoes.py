"""
GESTNOW v3 — mod_admin_deslocacoes.py
Gestão de Deslocações — Dormidas + Bilhetes (Avião/Comboio/Autocarro)
com pesquisa IA via Anthropic API + web_search
"""
import streamlit as st
import pandas as pd
import uuid, io, os, json, time
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from core import save_db, inv, load_db, log_audit, criar_notificacao

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

def _cor_estado(estado: str) -> tuple:
    return {
        "Por Comprar":  ("#F59E0B", "🟡"),
        "Reservado":    ("#3B82F6", "🔵"),
        "Confirmado":   ("#10B981", "✅"),
        "Utilizado":    ("#64748B", "✔️"),
        "Cancelado":    ("#EF4444", "❌"),
        "Reembolso Pendente": ("#F97316", "💰"),
    }.get(estado, ("#6B7280", "⚪"))

def _dias_para_viagem(data_str: str) -> int:
    try:
        d = datetime.strptime(data_str, "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return 999

COMPANHIAS = {
    "Avião": [
        "TAP Air Portugal", "Ryanair", "easyJet", "Iberia",
        "Vueling", "Lufthansa", "British Airways", "Outra"
    ],
    "Comboio": [
        "CP — Comboios de Portugal", "Renfe (Espanha)",
        "SNCF (França)", "Eurostar", "Outra"
    ],
    "Autocarro": [
        "Rede Expressos", "FlixBus", "ALSA", "Outra"
    ],
}

AEROPORTOS_PT = [
    "Lisboa (LIS)", "Porto (OPO)", "Faro (FAO)",
    "Funchal (FNC)", "Ponta Delgada (PDL)",
    "Horta (HOR)", "Terceira (TER)"
]


# ─────────────────────────────────────────────────────────────────
# PESQUISA IA — ANTHROPIC API + WEB SEARCH
# ─────────────────────────────────────────────────────────────────

def _pesquisar_opcoes_ia(
    tipo: str,
    origem: str,
    destino: str,
    data_ida: str,
    data_volta: str,
    n_pax: int,
    classe: str,
    obs: str
) -> list:
    """
    Chama Anthropic API com web_search para pesquisar
    opções reais de transporte. Devolve lista de dicts.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    import anthropic

    tipo_pt = {
        "Avião":     "voos",
        "Comboio":   "comboios",
        "Autocarro": "autocarros",
    }.get(tipo, "transporte")

    volta_txt = f" com regresso em {data_volta}" \
                if data_volta else " (só ida)"

    prompt = f"""Pesquisa opções de {tipo_pt} de {origem} para {destino}
em {data_ida}{volta_txt}, para {n_pax} passageiro(s), classe {classe}.
{f'Observações: {obs}' if obs else ''}

Pesquisa nos sites das companhias, Google Flights, Omio, CP, Rede Expressos,
FlixBus ou agregadores relevantes.

Responde APENAS com um JSON válido (sem markdown, sem texto antes ou depois):
{{
  "opcoes": [
    {{
      "companhia": "Nome da companhia",
      "tipo": "{tipo}",
      "origem": "{origem}",
      "destino": "{destino}",
      "data_ida": "{data_ida}",
      "hora_partida": "HH:MM",
      "hora_chegada": "HH:MM",
      "duracao": "Xh YYm",
      "preco_total": 0.00,
      "preco_por_pax": 0.00,
      "classe": "{classe}",
      "referencia": "código ou link curto",
      "link_reserva": "URL completo",
      "escalas": "Directo ou N escala(s)",
      "bagagem": "incluída / não incluída / 10kg",
      "cancelamento": "gratuito / pago / não reembolsável",
      "notas": "info adicional relevante"
    }}
  ],
  "fonte_pesquisa": "sites consultados",
  "aviso": "nota sobre disponibilidade/preços"
}}

Inclui 3 a 5 opções reais e variadas (melhor preço, mais rápido, melhor qualidade).
Se não encontrares dados reais, estima com base no mercado actual mas indica isso nas notas."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=[{
                "type":  "web_search_20250305",
                "name":  "web_search",
            }],
            messages=[{"role": "user", "content": prompt}]
        )

        # Extrair texto da resposta
        texto = ""
        for bloco in response.content:
            if hasattr(bloco, 'type') and bloco.type == "text":
                texto += bloco.text

        # Limpar e fazer parse do JSON
        texto = texto.strip()
        if "```" in texto:
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        texto = texto.strip()

        # Encontrar JSON no texto
        inicio = texto.find('{')
        fim    = texto.rfind('}') + 1
        if inicio >= 0 and fim > inicio:
            texto = texto[inicio:fim]

        dados = json.loads(texto)
        return dados.get("opcoes", []), \
               dados.get("fonte_pesquisa", ""), \
               dados.get("aviso", "")

    except Exception as e:
        return [], "", f"Erro na pesquisa: {str(e)}"


# ─────────────────────────────────────────────────────────────────
# CARDS DE RESULTADO DA PESQUISA IA
# ─────────────────────────────────────────────────────────────────

def _render_card_opcao(opcao: dict, idx: int,
                        n_pax: int,
                        obras_list: list,
                        users_list: list,
                        bilhetes_db: pd.DataFrame,
                        obras_db: pd.DataFrame) -> bool:
    """Renderiza card de opção de transporte com botão Seleccionar."""

    tipo   = opcao.get('tipo','')
    ic_tipo = {
        "Avião":     "✈️",
        "Comboio":   "🚂",
        "Autocarro": "🚌",
    }.get(tipo, "🚍")

    preco  = float(opcao.get('preco_total', 0))
    preco_p= float(opcao.get('preco_por_pax', preco))
    esc    = opcao.get('escalas','Directo')
    canc   = opcao.get('cancelamento','')
    bag    = opcao.get('bagagem','')
    link   = opcao.get('link_reserva','')

    cor_canc = (
        "#10B981" if 'gratuito' in canc.lower() else
        "#F59E0B" if 'pago'     in canc.lower() else
        "#EF4444"
    )

    selected = False

    with st.container():
       with st.container():
        notas_opcao = opcao.get('notas','') or ''
        notas_html  = (
            f"<br><small style='color:#94A3B8;'>{notas_opcao}</small>"
            if notas_opcao else ""
        )

        st.markdown(
            f"<div style='background:#1E293B;"
            f"border-radius:12px;padding:16px;"
            f"margin-bottom:8px;"
            f"border:1px solid rgba(255,255,255,0.08);'>"
            f"<div style='display:flex;"
            f"justify-content:space-between;"
            f"align-items:flex-start;'>"
            f"<div>"
            f"<b style='color:#F1F5F9;font-size:1rem;'>"
            f"{ic_tipo} {opcao.get('companhia','')}</b>"
            f"<span style='background:rgba(59,130,246,0.2);"
            f"color:#60A5FA;padding:2px 8px;"
            f"border-radius:10px;font-size:0.72rem;"
            f"font-weight:700;margin-left:8px;'>"
            f"{esc}</span><br>"
            f"<span style='color:#94A3B8;font-size:0.88rem;'>"
            f"{opcao.get('origem','')} "
            f"<b style='color:#F1F5F9;'>→</b> "
            f"{opcao.get('destino','')}</span><br>"
            f"<span style='color:#64748B;font-size:0.82rem;'>"
            f"⏱️ {opcao.get('hora_partida','')} → "
            f"{opcao.get('hora_chegada','')} "
            f"({opcao.get('duracao','')}) · "
            f"🧳 {bag}"
            f"</span>"
            f"</div>"
            f"<div style='text-align:right;'>"
            f"<b style='color:#10B981;font-size:1.3rem;'>"
            f"€{preco:.2f}</b><br>"
            f"<small style='color:#64748B;'>"
            f"€{preco_p:.2f}/pax</small><br>"
            f"<span style='color:{cor_canc};"
            f"font-size:0.72rem;'>{canc}</span>"
            f"</div></div>"
            f"{notas_html}"
            f"</div>",
            unsafe_allow_html=True
        )

        col_b1, col_b2, col_b3 = st.columns([2,2,1])
        with col_b1:
            if link:
                st.link_button(
                    "🔗 Ver no site",
                    url=link,
                    use_container_width=True
                ) 

        col_b1, col_b2, col_b3 = st.columns([2,2,1])
        with col_b1:
            if link:
                st.link_button(
                    "🔗 Ver no site",
                    url=link,
                    use_container_width=True
                )
        with col_b2:
            if st.button(
                "✅ Seleccionar esta opção",
                key=f"sel_opcao_{idx}",
                use_container_width=True,
                type="primary"
            ):
                st.session_state['opcao_selecionada'] = opcao
                st.session_state['mostrar_form_guardar'] = True
                selected = True
                st.rerun()

    return selected


# ─────────────────────────────────────────────────────────────────
# RENDER DORMIDAS (migrado do mod_admin_dormidas)
# ─────────────────────────────────────────────────────────────────

def _render_dormidas(obras_db, users):
    """Tab de dormidas — migrado de mod_admin_dormidas.py."""

    dormidas_db = _load("dormidas.csv", [
        "ID","Data_Checkin","Data_Checkout","Colaborador","Obra",
        "Hotel","Cidade","Valor_Noite","Total","Estado",
        "Confirmacao","Pago_Por","Notas"
    ])

    user_nome  = st.session_state.get('user','Admin')
    hoje       = date.today()
    obras_list = obras_db[obras_db['Ativa']=='Ativa']['Obra'].tolist() \
                 if not obras_db.empty else []
    users_list = users['Nome'].tolist() if not users.empty else []

    st.markdown("### 🏨 Gestão de Dormidas")

    # KPIs
    n_ativas  = len(dormidas_db[
        dormidas_db['Estado'].isin(['Reservado','Confirmado'])
    ]) if not dormidas_db.empty else 0
    val_mes   = 0.0
    if not dormidas_db.empty and 'Data_Checkin' in dormidas_db.columns:
        dm = dormidas_db.copy()
        dm['d'] = pd.to_datetime(dm['Data_Checkin'],dayfirst=True,errors='coerce')
        dm['v'] = pd.to_numeric(dm.get('Total',0),errors='coerce').fillna(0)
        val_mes = dm[
            (dm['d'].dt.month==hoje.month)&(dm['d'].dt.year==hoje.year)
        ]['v'].sum()

    c1,c2,c3 = st.columns(3)
    with c1: st.metric("🏨 Reservas Activas", n_ativas)
    with c2: st.metric("💰 Custo Mês",        f"€{val_mes:,.2f}")
    with c3: st.metric("📋 Total Registos",
                       len(dormidas_db) if not dormidas_db.empty else 0)

    st.divider()

    tab_nova_d, tab_lista_d = st.tabs(["➕ Nova Reserva","📋 Lista"])

    with tab_nova_d:
        with st.form("form_dormida"):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                d_colab = st.selectbox(
                    "Colaborador *",
                    users_list if users_list else ["—"],
                    key="d_colab"
                )
                d_obra  = st.selectbox(
                    "Obra *",
                    obras_list if obras_list else ["—"],
                    key="d_obra"
                )
                d_hotel = st.text_input(
                    "Hotel / Alojamento *",
                    key="d_hotel",
                    placeholder="Ex: Hotel Ibis Lisboa"
                )
                d_cidade = st.text_input(
                    "Cidade", key="d_cidade",
                    placeholder="Ex: Lisboa"
                )
            with col_d2:
                d_checkin  = st.date_input(
                    "Check-in *",
                    value=hoje, key="d_checkin"
                )
                d_checkout = st.date_input(
                    "Check-out *",
                    value=hoje+timedelta(days=1),
                    key="d_checkout"
                )
                d_vnoite = st.number_input(
                    "Valor por Noite (€)",
                    min_value=0.0, step=5.0,
                    key="d_vnoite"
                )
                d_pago = st.selectbox(
                    "Pago por",
                    ["Empresa","Colaborador (reembolso)"],
                    key="d_pago"
                )
                d_conf = st.text_input(
                    "Nº Confirmação",
                    key="d_conf",
                    placeholder="Ex: BK123456789"
                )
                d_notas = st.text_area("Notas", key="d_notas")

            n_noites = max((d_checkout - d_checkin).days, 0)
            total_d  = round(n_noites * d_vnoite, 2)
            if total_d > 0:
                st.info(
                    f"🌙 {n_noites} noite(s) × €{d_vnoite:.2f} = "
                    f"**€{total_d:.2f}**"
                )

            if st.form_submit_button(
                "💾 Guardar Reserva",
                use_container_width=True,
                type="primary"
            ):
                if not d_hotel.strip():
                    st.error("❌ Hotel obrigatório.")
                else:
                    nova_d = pd.DataFrame([{
                        "ID":           str(uuid.uuid4())[:8].upper(),
                        "Data_Checkin": d_checkin.strftime("%d/%m/%Y"),
                        "Data_Checkout":d_checkout.strftime("%d/%m/%Y"),
                        "Colaborador":  d_colab,
                        "Obra":         d_obra,
                        "Hotel":        d_hotel.strip(),
                        "Cidade":       d_cidade.strip(),
                        "Valor_Noite":  d_vnoite,
                        "Total":        total_d,
                        "Estado":       "Reservado",
                        "Confirmacao":  d_conf.strip(),
                        "Pago_Por":     d_pago,
                        "Notas":        d_notas.strip()
                    }])
                    upd = pd.concat(
                        [dormidas_db, nova_d], ignore_index=True
                    ) if not dormidas_db.empty else nova_d
                    save_db(upd,"dormidas.csv")
                    inv("dormidas.csv")
                    st.success(
                        f"✅ Reserva guardada! "
                        f"{n_noites} noite(s) · €{total_d:.2f}"
                    )
                    st.rerun()

    with tab_lista_d:
        if dormidas_db.empty:
            st.info("📋 Sem dormidas registadas.")
        else:
            col_fl1, col_fl2 = st.columns(2)
            with col_fl1:
                obra_fd = st.selectbox(
                    "Obra",["Todas"]+obras_list,
                    key="dorm_obra_filt"
                )
            with col_fl2:
                colab_fd = st.selectbox(
                    "Colaborador",["Todos"]+users_list,
                    key="dorm_colab_filt"
                )

            df_d = dormidas_db.copy()
            if obra_fd  != "Todas":
                df_d = df_d[df_d['Obra']==obra_fd]
            if colab_fd != "Todos":
                df_d = df_d[df_d['Colaborador']==colab_fd]

            for _, dorm in df_d.sort_values(
                'Data_Checkin',ascending=False
            ).iterrows():
                did    = dorm.get('ID','')
                estado = dorm.get('Estado','')
                cor_e  = {
                    'Reservado':'#3B82F6','Confirmado':'#10B981',
                    'Cancelado':'#EF4444','Concluído':'#64748B'
                }.get(estado,'#6B7280')
                total  = float(dorm.get('Total',0) or 0)

                col_di, col_de = st.columns([6,1])
                with col_di:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:12px 16px;"
                        f"margin-bottom:6px;"
                        f"border-left:4px solid {cor_e};'>"
                        f"<b style='color:#F1F5F9;'>"
                        f"🏨 {dorm.get('Hotel','')}</b>"
                        f"<span style='float:right;"
                        f"color:#10B981;font-weight:700;'>"
                        f"€{total:.2f}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"👤 {dorm.get('Colaborador','')} · "
                        f"🏗️ {dorm.get('Obra','')} · "
                        f"📅 {dorm.get('Data_Checkin','')} → "
                        f"{dorm.get('Data_Checkout','')} · "
                        f"📍 {dorm.get('Cidade','')}</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_de:
                    novo_est_d = st.selectbox(
                        "Estado",
                        ['Reservado','Confirmado','Cancelado','Concluído'],
                        key=f"dst_{did}",
                        label_visibility="collapsed"
                    )
                    if st.button(
                        "✅",
                        key=f"upd_d_{did}",
                        use_container_width=True
                    ):
                        dormidas_db.loc[
                            dormidas_db['ID']==did,'Estado'
                        ] = novo_est_d
                        save_db(dormidas_db,"dormidas.csv")
                        inv("dormidas.csv"); st.rerun()


# ─────────────────────────────────────────────────────────────────
# RENDER BILHETES
# ─────────────────────────────────────────────────────────────────

def _render_bilhetes(obras_db, users):
    """Tab de bilhetes de transporte com pesquisa IA."""

    bilhetes_db = _load("bilhetes_viagem.csv", [
        "ID","Tipo","Companhia","Origem","Destino",
        "Data_Ida","Data_Volta","Hora_Partida","Hora_Chegada",
        "Duracao","Colaborador","Obra","N_Passageiros","Classe",
        "Preco_Total","Pago_Por","Estado","Referencia",
        "Link_Reserva","Escalas","Bagagem","Cancelamento",
        "Bilhete_b64","Notas","Criado_Por","Criado_Em"
    ])

    user_nome  = st.session_state.get('user','Admin')
    hoje       = date.today()
    obras_list = obras_db[obras_db['Ativa']=='Ativa']['Obra'].tolist() \
                 if not obras_db.empty else []
    users_list = users['Nome'].tolist() if not users.empty else []

    st.markdown("### 🎫 Gestão de Bilhetes de Viagem")

    # KPIs
    n_conf   = len(bilhetes_db[
        bilhetes_db['Estado'].isin(['Confirmado','Reservado'])
    ]) if not bilhetes_db.empty else 0
    val_mes_b = 0.0
    if not bilhetes_db.empty and 'Criado_Em' in bilhetes_db.columns:
        bm = bilhetes_db.copy()
        bm['d'] = pd.to_datetime(bm['Criado_Em'],dayfirst=True,errors='coerce')
        bm['v'] = pd.to_numeric(bm.get('Preco_Total',0),errors='coerce').fillna(0)
        val_mes_b = bm[
            (bm['d'].dt.month==hoje.month)&(bm['d'].dt.year==hoje.year)
        ]['v'].sum()

    # Próximas viagens (7 dias)
    proximas = 0
    if not bilhetes_db.empty and 'Data_Ida' in bilhetes_db.columns:
        bdb2 = bilhetes_db.copy()
        bdb2['dias'] = bdb2['Data_Ida'].apply(_dias_para_viagem)
        proximas = len(bdb2[
            bdb2['dias'].between(0,7) &
            bdb2['Estado'].isin(['Confirmado','Reservado'])
        ])

    # Reembolsos pendentes
    n_reemb = len(bilhetes_db[
        bilhetes_db['Pago_Por']=='Colaborador (reembolso)'
    ]) if not bilhetes_db.empty else 0

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("🎫 Activos",      n_conf)
    with c2: st.metric("💰 Custo Mês",   f"€{val_mes_b:,.2f}")
    with c3: st.metric("✈️ Próx. 7 dias", proximas)
    with c4: st.metric("💰 Reembolsos",   n_reemb)

    # Alerta próximas viagens
    if proximas > 0 and not bilhetes_db.empty:
        bdb3 = bilhetes_db.copy()
        bdb3['dias'] = bdb3['Data_Ida'].apply(_dias_para_viagem)
        prox_lst = bdb3[bdb3['dias'].between(0,7)].sort_values('dias')
        msg = " · ".join([
            f"{r['Colaborador']} → {r['Destino']} "
            f"({r['dias']}d)"
            for _, r in prox_lst.head(3).iterrows()
        ])
        st.markdown(
            f"<div style='background:rgba(59,130,246,0.1);"
            f"border:1px solid #3B82F6;border-radius:8px;"
            f"padding:10px 14px;margin-bottom:8px;'>"
            f"<b style='color:#3B82F6;'>✈️ Viagens próximas:</b> "
            f"<span style='color:#94A3B8;'>{msg}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.divider()

    tab_ia, tab_manual, tab_lista, tab_reembolsos = st.tabs([
        "🤖 Pesquisa IA",
        "✏️ Registar Manual",
        "📋 Lista de Bilhetes",
        "💰 Reembolsos",
    ])

    # ════════════════════════════════════════════════════════════════
    # SUB-TAB — PESQUISA IA
    # ════════════════════════════════════════════════════════════════
    with tab_ia:
        st.markdown("#### 🤖 Pesquisa Inteligente de Transporte")
        st.markdown(
            "<p style='color:#94A3B8;font-size:0.85rem;'>"
            "A IA pesquisa opções reais na web (voos, comboios, autocarros) "
            "e apresenta as melhores opções. Selecciona a que queres "
            "e é guardada automaticamente na base de dados."
            "</p>",
            unsafe_allow_html=True
        )

        # Formulário de pesquisa
        with st.form("form_pesquisa_ia"):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                p_tipo = st.selectbox(
                    "Tipo de Transporte *",
                    ["Avião","Comboio","Autocarro"],
                    key="p_tipo"
                )
                p_colab = st.selectbox(
                    "Para quem *",
                    users_list if users_list else ["—"],
                    key="p_colab"
                )
                p_obra = st.selectbox(
                    "Obra associada",
                    obras_list if obras_list else ["—"],
                    key="p_obra"
                )
                p_pax = st.number_input(
                    "Nº Passageiros",
                    min_value=1, value=1, key="p_pax"
                )

            with col_p2:
                p_origem  = st.text_input(
                    "Origem *",
                    key="p_origem",
                    placeholder="Ex: Lisboa (LIS) ou Porto"
                )
                p_destino = st.text_input(
                    "Destino *",
                    key="p_destino",
                    placeholder="Ex: Madrid (MAD) ou Sines"
                )
                p_data_ida = st.date_input(
                    "Data de Ida *",
                    value=hoje+timedelta(days=7),
                    key="p_data_ida"
                )
                p_volta = st.checkbox(
                    "🔄 Incluir regresso",
                    key="p_volta"
                )
                p_data_volta = None
                if p_volta:
                    p_data_volta = st.date_input(
                        "Data de Regresso",
                        value=hoje+timedelta(days=10),
                        key="p_data_volta"
                    )
                p_classe = st.selectbox(
                    "Classe / Conforto",
                    ["Económica","Business","1ª Classe",
                     "Standard","Conforto","Premium"],
                    key="p_classe"
                )

            p_obs = st.text_area(
                "Preferências / Observações",
                key="p_obs",
                placeholder="Ex: voo directo, bagagem incluída, "
                            "manhã de preferência..."
            )

            pesquisar = st.form_submit_button(
                "🔍 Pesquisar com IA",
                use_container_width=True,
                type="primary"
            )

            if pesquisar:
                if not p_origem.strip() or not p_destino.strip():
                    st.error("❌ Origem e destino obrigatórios.")
                else:
                    st.session_state['pesquisa_params'] = {
                        "tipo":       p_tipo,
                        "origem":     p_origem.strip(),
                        "destino":    p_destino.strip(),
                        "data_ida":   p_data_ida.strftime("%d/%m/%Y"),
                        "data_volta": p_data_volta.strftime("%d/%m/%Y")
                                      if p_data_volta else "",
                        "n_pax":      p_pax,
                        "classe":     p_classe,
                        "obs":        p_obs.strip(),
                        "colab":      p_colab,
                        "obra":       p_obra,
                    }
                    st.session_state['resultados_ia']       = None
                    st.session_state['fonte_pesquisa_ia']   = ""
                    st.session_state['aviso_ia']            = ""
                    st.session_state['opcao_selecionada']   = None
                    st.session_state['mostrar_form_guardar']= False
                    st.rerun()

        # Executar pesquisa
        if st.session_state.get('pesquisa_params') and \
           st.session_state.get('resultados_ia') is None:
            params = st.session_state['pesquisa_params']
            tipo_ic = {
                "Avião":"✈️","Comboio":"🚂","Autocarro":"🚌"
            }.get(params['tipo'],'🚍')

            with st.spinner(
                f"🤖 A pesquisar {tipo_ic} de "
                f"{params['origem']} → {params['destino']} "
                f"em {params['data_ida']}..."
            ):
                resultados, fonte, aviso = _pesquisar_opcoes_ia(
                    tipo       = params['tipo'],
                    origem     = params['origem'],
                    destino    = params['destino'],
                    data_ida   = params['data_ida'],
                    data_volta = params['data_volta'],
                    n_pax      = params['n_pax'],
                    classe     = params['classe'],
                    obs        = params['obs'],
                )
                st.session_state['resultados_ia']     = resultados
                st.session_state['fonte_pesquisa_ia'] = fonte
                st.session_state['aviso_ia']          = aviso
                st.rerun()

        # Mostrar resultados
        resultados = st.session_state.get('resultados_ia')
        if resultados is not None:
            params = st.session_state.get('pesquisa_params',{})
            fonte  = st.session_state.get('fonte_pesquisa_ia','')
            aviso  = st.session_state.get('aviso_ia','')

            tipo_ic = {
                "Avião":"✈️","Comboio":"🚂","Autocarro":"🚌"
            }.get(params.get('tipo',''),'🚍')

            st.markdown(
                f"<div style='background:rgba(16,185,129,0.1);"
                f"border:1px solid #10B981;"
                f"border-radius:8px;padding:10px 14px;"
                f"margin-bottom:12px;'>"
                f"<b style='color:#10B981;'>"
                f"{tipo_ic} {len(resultados)} opção(ões) encontrada(s)</b>"
                f"{'  ·  <span style=color:#64748B;font-size:0.8rem;>' + fonte + '</span>' if fonte else ''}"
                f"</div>",
                unsafe_allow_html=True
            )

            if aviso:
                st.info(f"ℹ️ {aviso}")

            if not resultados:
                st.warning(
                    "⚠️ Sem resultados encontrados. "
                    "Tenta ajustar os parâmetros de pesquisa."
                )
            else:
                for i, opcao in enumerate(resultados):
                    _render_card_opcao(
                        opcao, i,
                        params.get('n_pax',1),
                        obras_list, users_list,
                        bilhetes_db, obras_db
                    )

            if st.button(
                "🔄 Nova Pesquisa",
                key="btn_nova_pesq",
                use_container_width=True
            ):
                st.session_state['pesquisa_params']      = None
                st.session_state['resultados_ia']        = None
                st.session_state['opcao_selecionada']    = None
                st.session_state['mostrar_form_guardar'] = False
                st.rerun()

        # Formulário de guardar opção seleccionada
        if st.session_state.get('mostrar_form_guardar') and \
           st.session_state.get('opcao_selecionada'):
            opcao  = st.session_state['opcao_selecionada']
            params = st.session_state.get('pesquisa_params',{})

            st.markdown("---")
            st.markdown(
                f"<div style='background:rgba(16,185,129,0.1);"
                f"border:1px solid #10B981;"
                f"border-radius:10px;padding:14px;"
                f"margin-bottom:12px;'>"
                f"<b style='color:#10B981;'>✅ Opção seleccionada: "
                f"{opcao.get('companhia','')} — "
                f"{opcao.get('origem','')} → "
                f"{opcao.get('destino','')} · "
                f"€{float(opcao.get('preco_total',0)):.2f}</b>"
                f"</div>",
                unsafe_allow_html=True
            )

            with st.form("form_guardar_ia"):
                st.markdown("##### 💾 Confirmar e Guardar")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    g_colab = st.selectbox(
                        "Colaborador *",
                        users_list,
                        index=users_list.index(params.get('colab',''))
                              if params.get('colab','') in users_list
                              else 0,
                        key="g_colab"
                    )
                    g_obra  = st.selectbox(
                        "Obra",
                        obras_list,
                        index=obras_list.index(params.get('obra',''))
                              if params.get('obra','') in obras_list
                              else 0,
                        key="g_obra"
                    )
                    g_pago  = st.selectbox(
                        "Pago por",
                        ["Empresa","Colaborador (reembolso)"],
                        key="g_pago"
                    )
                with col_g2:
                    g_ref   = st.text_input(
                        "Nº Reserva / Confirmação",
                        value=opcao.get('referencia',''),
                        key="g_ref"
                    )
                    g_preco = st.number_input(
                        "Preço Final (€)",
                        min_value=0.0,
                        value=float(opcao.get('preco_total',0)),
                        step=0.50,
                        key="g_preco"
                    )
                    g_estado = st.selectbox(
                        "Estado",
                        ["Por Comprar","Reservado","Confirmado"],
                        key="g_estado"
                    )

                g_bilhete = st.file_uploader(
                    "Anexar bilhete PDF (opcional)",
                    type=["pdf","jpg","jpeg","png"],
                    key="g_bilhete"
                )
                g_notas = st.text_area("Notas", key="g_notas")

                if st.form_submit_button(
                    "💾 Guardar Bilhete",
                    use_container_width=True,
                    type="primary"
                ):
                    import base64 as b64m
                    bil_b64 = ""
                    if g_bilhete:
                        bil_b64 = b64m.b64encode(
                            g_bilhete.read()
                        ).decode()

                    novo_b = pd.DataFrame([{
                        "ID":           str(uuid.uuid4())[:8].upper(),
                        "Tipo":         opcao.get('tipo',''),
                        "Companhia":    opcao.get('companhia',''),
                        "Origem":       opcao.get('origem',''),
                        "Destino":      opcao.get('destino',''),
                        "Data_Ida":     params.get('data_ida',''),
                        "Data_Volta":   params.get('data_volta',''),
                        "Hora_Partida": opcao.get('hora_partida',''),
                        "Hora_Chegada": opcao.get('hora_chegada',''),
                        "Duracao":      opcao.get('duracao',''),
                        "Colaborador":  g_colab,
                        "Obra":         g_obra,
                        "N_Passageiros":params.get('n_pax',1),
                        "Classe":       params.get('classe',''),
                        "Preco_Total":  g_preco,
                        "Pago_Por":     g_pago,
                        "Estado":       g_estado,
                        "Referencia":   g_ref.strip(),
                        "Link_Reserva": opcao.get('link_reserva',''),
                        "Escalas":      opcao.get('escalas',''),
                        "Bagagem":      opcao.get('bagagem',''),
                        "Cancelamento": opcao.get('cancelamento',''),
                        "Bilhete_b64":  bil_b64,
                        "Notas":        g_notas.strip(),
                        "Criado_Por":   user_nome,
                        "Criado_Em":    hoje.strftime("%d/%m/%Y")
                    }])
                    upd_b = pd.concat(
                        [bilhetes_db, novo_b], ignore_index=True
                    ) if not bilhetes_db.empty else novo_b
                    save_db(upd_b,"bilhetes_viagem.csv")
                    log_audit(
                        usuario=user_nome,
                        acao="REGISTAR_BILHETE_IA",
                        tabela="bilhetes_viagem.csv",
                        registro_id=novo_b['ID'].iloc[0],
                        detalhes=(
                            f"{g_colab} | "
                            f"{opcao.get('tipo','')} | "
                            f"{opcao.get('origem','')}→"
                            f"{opcao.get('destino','')} | "
                            f"€{g_preco:.2f}"
                        ),
                        ip=""
                    )
                    criar_notificacao(
                        destinatario=g_colab,
                        titulo=f"🎫 Bilhete Registado — "
                               f"{opcao.get('origem','')} → "
                               f"{opcao.get('destino','')}",
                        mensagem=(
                            f"Bilhete {opcao.get('tipo','')} de "
                            f"{opcao.get('companhia','')} "
                            f"para {params.get('data_ida','')} "
                            f"registado. Ref: {g_ref}."
                        ),
                        tipo="success",
                        acao_url="/"
                    )
                    inv("bilhetes_viagem.csv")
                    st.success(
                        f"✅ Bilhete guardado! "
                        f"{g_colab} · "
                        f"{opcao.get('origem','')} → "
                        f"{opcao.get('destino','')} · "
                        f"€{g_preco:.2f}"
                    )
                    st.session_state['mostrar_form_guardar'] = False
                    st.session_state['opcao_selecionada']   = None
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # SUB-TAB — REGISTAR MANUAL
    # ════════════════════════════════════════════════════════════════
    with tab_manual:
        st.markdown("#### ✏️ Registar Bilhete Manualmente")

        with st.form("form_bilhete_manual"):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_tipo    = st.selectbox(
                    "Tipo *",
                    ["Avião","Comboio","Autocarro"],
                    key="m_tipo"
                )
                m_comp    = st.selectbox(
                    "Companhia",
                    COMPANHIAS.get("Avião",[]),
                    key="m_comp"
                )
                m_origem  = st.text_input(
                    "Origem *", key="m_origem",
                    placeholder="Ex: Lisboa (LIS)"
                )
                m_destino = st.text_input(
                    "Destino *", key="m_destino",
                    placeholder="Ex: Madrid (MAD)"
                )
                col_md1, col_md2 = st.columns(2)
                with col_md1:
                    m_data_ida = st.date_input(
                        "Data Ida *",
                        value=hoje+timedelta(days=7),
                        key="m_data_ida"
                    )
                    m_hora_p  = st.text_input(
                        "Hora Partida",
                        key="m_hora_p",
                        placeholder="HH:MM"
                    )
                with col_md2:
                    m_data_v  = st.date_input(
                        "Data Volta (se aplicável)",
                        value=hoje+timedelta(days=10),
                        key="m_data_v"
                    )
                    m_hora_c  = st.text_input(
                        "Hora Chegada",
                        key="m_hora_c",
                        placeholder="HH:MM"
                    )

            with col_m2:
                m_colab   = st.selectbox(
                    "Colaborador *",
                    users_list if users_list else ["—"],
                    key="m_colab"
                )
                m_obra    = st.selectbox(
                    "Obra",
                    obras_list if obras_list else ["—"],
                    key="m_obra"
                )
                m_pax     = st.number_input(
                    "Nº Passageiros",
                    min_value=1, value=1, key="m_pax"
                )
                m_classe  = st.selectbox(
                    "Classe",
                    ["Económica","Business","1ª Classe",
                     "Standard","Conforto"],
                    key="m_classe"
                )
                m_preco   = st.number_input(
                    "Preço Total (€)",
                    min_value=0.0, step=1.0, key="m_preco"
                )
                m_pago    = st.selectbox(
                    "Pago por",
                    ["Empresa","Colaborador (reembolso)"],
                    key="m_pago"
                )
                m_ref     = st.text_input(
                    "Nº Reserva / Ref.",
                    key="m_ref",
                    placeholder="Ex: FR1234 / BK987654"
                )
                m_estado  = st.selectbox(
                    "Estado",
                    ["Por Comprar","Reservado","Confirmado"],
                    key="m_estado"
                )

            m_escalas = st.text_input(
                "Escalas",
                key="m_escalas",
                placeholder="Directo / 1 escala em Madrid"
            )
            m_bagagem = st.text_input(
                "Bagagem incluída",
                key="m_bagagem",
                placeholder="Cabine / 23kg / Não incluída"
            )
            m_bilhete = st.file_uploader(
                "Anexar bilhete (PDF/imagem)",
                type=["pdf","jpg","jpeg","png"],
                key="m_bilhete"
            )
            m_notas   = st.text_area("Notas", key="m_notas")

            if st.form_submit_button(
                "💾 Guardar Bilhete",
                use_container_width=True, type="primary"
            ):
                if not m_origem.strip() or not m_destino.strip():
                    st.error("❌ Origem e destino obrigatórios.")
                else:
                    import base64 as b64m2
                    bil_b64_m = ""
                    if m_bilhete:
                        bil_b64_m = b64m2.b64encode(
                            m_bilhete.read()
                        ).decode()

                    novo_bm = pd.DataFrame([{
                        "ID":           str(uuid.uuid4())[:8].upper(),
                        "Tipo":         m_tipo,
                        "Companhia":    m_comp,
                        "Origem":       m_origem.strip(),
                        "Destino":      m_destino.strip(),
                        "Data_Ida":     m_data_ida.strftime("%d/%m/%Y"),
                        "Data_Volta":   m_data_v.strftime("%d/%m/%Y"),
                        "Hora_Partida": m_hora_p.strip(),
                        "Hora_Chegada": m_hora_c.strip(),
                        "Duracao":      "",
                        "Colaborador":  m_colab,
                        "Obra":         m_obra,
                        "N_Passageiros":m_pax,
                        "Classe":       m_classe,
                        "Preco_Total":  m_preco,
                        "Pago_Por":     m_pago,
                        "Estado":       m_estado,
                        "Referencia":   m_ref.strip(),
                        "Link_Reserva": "",
                        "Escalas":      m_escalas.strip(),
                        "Bagagem":      m_bagagem.strip(),
                        "Cancelamento": "",
                        "Bilhete_b64":  bil_b64_m,
                        "Notas":        m_notas.strip(),
                        "Criado_Por":   user_nome,
                        "Criado_Em":    hoje.strftime("%d/%m/%Y")
                    }])
                    upd_bm = pd.concat(
                        [bilhetes_db, novo_bm], ignore_index=True
                    ) if not bilhetes_db.empty else novo_bm
                    save_db(upd_bm,"bilhetes_viagem.csv")
                    log_audit(
                        usuario=user_nome,
                        acao="REGISTAR_BILHETE_MANUAL",
                        tabela="bilhetes_viagem.csv",
                        registro_id=novo_bm['ID'].iloc[0],
                        detalhes=(
                            f"{m_colab} | {m_tipo} | "
                            f"{m_origem}→{m_destino} | "
                            f"€{m_preco:.2f}"
                        ),
                        ip=""
                    )
                    criar_notificacao(
                        destinatario=m_colab,
                        titulo=f"🎫 Bilhete — "
                               f"{m_origem} → {m_destino}",
                        mensagem=(
                            f"Bilhete {m_tipo} para "
                            f"{m_data_ida.strftime('%d/%m/%Y')} "
                            f"registado. Ref: {m_ref}."
                        ),
                        tipo="success", acao_url="/"
                    )
                    inv("bilhetes_viagem.csv")
                    st.success(
                        f"✅ Bilhete guardado! "
                        f"{m_colab} · {m_origem}→{m_destino} · "
                        f"€{m_preco:.2f}"
                    )
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # SUB-TAB — LISTA DE BILHETES
    # ════════════════════════════════════════════════════════════════
    with tab_lista:
        st.markdown("#### 📋 Todos os Bilhetes")

        if bilhetes_db.empty:
            st.info("📋 Sem bilhetes registados.")
        else:
            col_lf1,col_lf2,col_lf3,col_lf4 = st.columns(4)
            with col_lf1:
                tipo_filt  = st.selectbox(
                    "Tipo",["Todos","Avião","Comboio","Autocarro"],
                    key="bil_tipo_filt"
                )
            with col_lf2:
                colab_filt = st.selectbox(
                    "Colaborador",["Todos"]+users_list,
                    key="bil_colab_filt"
                )
            with col_lf3:
                obra_filt  = st.selectbox(
                    "Obra",["Todas"]+obras_list,
                    key="bil_obra_filt"
                )
            with col_lf4:
                est_filt   = st.selectbox(
                    "Estado",
                    ["Todos","Por Comprar","Reservado",
                     "Confirmado","Utilizado","Cancelado"],
                    key="bil_est_filt"
                )

            df_b = bilhetes_db.copy()
            if tipo_filt  != "Todos":
                df_b = df_b[df_b['Tipo']==tipo_filt]
            if colab_filt != "Todos":
                df_b = df_b[df_b['Colaborador']==colab_filt]
            if obra_filt  != "Todas":
                df_b = df_b[df_b['Obra']==obra_filt]
            if est_filt   != "Todos":
                df_b = df_b[df_b['Estado']==est_filt]

            df_b['dias'] = df_b['Data_Ida'].apply(_dias_para_viagem)
            df_b = df_b.sort_values('dias', ascending=True)

            for _, bil in df_b.iterrows():
                bid    = bil.get('ID','')
                estado = bil.get('Estado','')
                cor_e, ic_e = _cor_estado(estado)
                preco  = float(bil.get('Preco_Total',0) or 0)
                tipo_b = bil.get('Tipo','')
                ic_t   = {"Avião":"✈️","Comboio":"🚂",
                           "Autocarro":"🚌"}.get(tipo_b,'🚍')
                dias_b = int(bil.get('dias',999))

                cor_dias_b = (
                    "#EF4444" if dias_b < 0  else
                    "#F59E0B" if dias_b <= 3 else
                    "#3B82F6" if dias_b <= 7 else
                    "#64748B"
                )
                txt_dias = (
                    "PASSADO" if dias_b < 0 else
                    f"{dias_b}d"
                )

                col_bi, col_ba = st.columns([6,1])
                with col_bi:
                    st.markdown(
                        f"<div style='background:#1E293B;"
                        f"border-radius:10px;padding:12px 16px;"
                        f"margin-bottom:6px;"
                        f"border-left:4px solid {cor_e};'>"
                        f"<div style='display:flex;"
                        f"justify-content:space-between;'>"
                        f"<div>"
                        f"<b style='color:#F1F5F9;'>"
                        f"{ic_t} {bil.get('Companhia','')} — "
                        f"{bil.get('Origem','')} → "
                        f"{bil.get('Destino','')}</b>"
                        f"<span style='background:{cor_e}22;"
                        f"color:{cor_e};padding:2px 8px;"
                        f"border-radius:10px;font-size:0.7rem;"
                        f"font-weight:700;margin-left:8px;'>"
                        f"{ic_e} {estado}</span><br>"
                        f"<small style='color:#64748B;'>"
                        f"👤 {bil.get('Colaborador','')} · "
                        f"🏗️ {bil.get('Obra','')} · "
                        f"📅 {bil.get('Data_Ida','')} "
                        f"{bil.get('Hora_Partida','') and '@ ' + bil.get('Hora_Partida','')}"
                        f" · 🎫 Ref: {bil.get('Referencia','—')}"
                        f"</small>"
                        f"</div>"
                        f"<div style='text-align:right;'>"
                        f"<b style='color:#10B981;"
                        f"font-size:1rem;'>€{preco:.2f}</b><br>"
                        f"<span style='color:{cor_dias_b};"
                        f"font-size:0.78rem;'>{txt_dias}</span>"
                        f"</div></div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_ba:
                    # Download bilhete se existir
                    bil_b = bil.get('Bilhete_b64','')
                    if bil_b and len(str(bil_b)) > 50:
                        import base64 as b64v
                        try:
                            st.download_button(
                                "📎",
                                data=b64v.b64decode(bil_b),
                                file_name=(
                                    f"bilhete_"
                                    f"{bil.get('Colaborador','').replace(' ','_')}"
                                    f"_{bid}.pdf"
                                ),
                                mime="application/pdf",
                                key=f"dl_bil_{bid}",
                                use_container_width=True,
                                help="Descarregar bilhete"
                            )
                        except:
                            pass

                    # Alterar estado
                    novo_est_b = st.selectbox(
                        "Estado",
                        ["Por Comprar","Reservado","Confirmado",
                         "Utilizado","Cancelado"],
                        key=f"bil_st_{bid}",
                        label_visibility="collapsed"
                    )
                    if st.button(
                        "✅",
                        key=f"upd_bil_{bid}",
                        use_container_width=True,
                        help="Actualizar estado"
                    ):
                        bilhetes_db.loc[
                            bilhetes_db['ID']==bid,'Estado'
                        ] = novo_est_b
                        save_db(bilhetes_db,"bilhetes_viagem.csv")
                        inv("bilhetes_viagem.csv"); st.rerun()

            # Exportar
            st.markdown("---")
            cols_bil = [c for c in [
                'Tipo','Companhia','Origem','Destino',
                'Data_Ida','Data_Volta','Colaborador','Obra',
                'Preco_Total','Pago_Por','Estado','Referencia'
            ] if c in bilhetes_db.columns]
            csv_bil = bilhetes_db[cols_bil].to_csv(
                index=False, encoding='utf-8-sig'
            )
            st.download_button(
                "📥 Exportar Bilhetes",
                data=csv_bil.encode('utf-8-sig'),
                file_name=(
                    f"bilhetes_viagem_"
                    f"{date.today().strftime('%Y%m%d')}.csv"
                ),
                mime="text/csv",
                key="dl_bil_exp"
            )

    # ════════════════════════════════════════════════════════════════
    # SUB-TAB — REEMBOLSOS
    # ════════════════════════════════════════════════════════════════
    with tab_reembolsos:
        st.markdown("#### 💰 Reembolsos Pendentes")
        st.info(
            "Bilhetes pagos pelo colaborador que aguardam "
            "reembolso pela empresa."
        )

        if bilhetes_db.empty:
            st.info("📋 Sem bilhetes registados.")
        else:
            reemb = bilhetes_db[
                (bilhetes_db['Pago_Por']=='Colaborador (reembolso)') &
                (bilhetes_db['Estado'] != 'Cancelado')
            ].copy() if not bilhetes_db.empty else pd.DataFrame()

            # Separar pendentes de processados
            tab_pend_r, tab_proc_r = st.tabs([
                "⏳ Por Reembolsar",
                "✅ Reembolsados"
            ])

            with tab_pend_r:
                pend_r = reemb[
                    reemb['Estado'] != 'Reembolso Processado'
                ] if not reemb.empty else pd.DataFrame()

                if pend_r.empty:
                    st.success("✅ Sem reembolsos pendentes!")
                else:
                    total_reemb = pd.to_numeric(
                        pend_r.get('Preco_Total',0),
                        errors='coerce'
                    ).fillna(0).sum()

                    st.markdown(
                        f"<div style='background:rgba(249,115,22,0.1);"
                        f"border:1px solid #F97316;"
                        f"border-radius:8px;padding:10px 14px;"
                        f"margin-bottom:10px;'>"
                        f"<b style='color:#F97316;'>"
                        f"💰 Total pendente: "
                        f"€{total_reemb:,.2f} "
                        f"({len(pend_r)} bilhete(s))</b>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    # Agrupar por colaborador
                    for colab_r, grp_r in pend_r.groupby('Colaborador'):
                        total_c = pd.to_numeric(
                            grp_r.get('Preco_Total',0),
                            errors='coerce'
                        ).fillna(0).sum()

                        with st.expander(
                            f"👤 {colab_r} — "
                            f"€{total_c:.2f} "
                            f"({len(grp_r)} bilhete(s))",
                            expanded=True
                        ):
                            for _, rb in grp_r.iterrows():
                                rid   = rb.get('ID','')
                                preco_r = float(rb.get('Preco_Total',0) or 0)
                                ic_tr = {"Avião":"✈️","Comboio":"🚂",
                                         "Autocarro":"🚌"}.get(
                                    rb.get('Tipo',''),'🚍'
                                )
                                st.markdown(
                                    f"<div style='background:#1E293B;"
                                    f"border-radius:8px;padding:10px;"
                                    f"margin-bottom:4px;display:flex;"
                                    f"justify-content:space-between;'>"
                                    f"<div>"
                                    f"<small style='color:#F1F5F9;'>"
                                    f"{ic_tr} {rb.get('Origem','')} → "
                                    f"{rb.get('Destino','')}</small><br>"
                                    f"<small style='color:#64748B;'>"
                                    f"📅 {rb.get('Data_Ida','')} · "
                                    f"{rb.get('Companhia','')} · "
                                    f"Ref: {rb.get('Referencia','—')}"
                                    f"</small></div>"
                                    f"<b style='color:#F97316;'>"
                                    f"€{preco_r:.2f}</b>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )

                            col_rp1, col_rp2 = st.columns(2)
                            with col_rp1:
                                st.markdown(
                                    f"<div style='background:"
                                    f"rgba(249,115,22,0.1);"
                                    f"border-radius:8px;padding:10px;"
                                    f"text-align:center;'>"
                                    f"<b style='color:#F97316;'>"
                                    f"Total a reembolsar: "
                                    f"€{total_c:.2f}</b>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                            with col_rp2:
                                if st.button(
                                    "✅ Marcar tudo como reembolsado",
                                    key=f"reemb_{colab_r}",
                                    use_container_width=True,
                                    type="primary"
                                ):
                                    for rid2 in grp_r['ID'].tolist():
                                        bilhetes_db.loc[
                                            bilhetes_db['ID']==rid2,
                                            'Estado'
                                        ] = 'Reembolso Processado'
                                    save_db(
                                        bilhetes_db,
                                        "bilhetes_viagem.csv"
                                    )
                                    criar_notificacao(
                                        destinatario=colab_r,
                                        titulo="💰 Reembolso Processado",
                                        mensagem=(
                                            f"Os teus reembolsos de "
                                            f"bilhetes de viagem "
                                            f"(€{total_c:.2f}) "
                                            f"foram processados."
                                        ),
                                        tipo="success",
                                        acao_url="/"
                                    )
                                    inv("bilhetes_viagem.csv"); st.rerun()

            with tab_proc_r:
                proc_r = reemb[
                    reemb['Estado']=='Reembolso Processado'
                ] if not reemb.empty else pd.DataFrame()
                if proc_r.empty:
                    st.info("📋 Sem reembolsos processados.")
                else:
                    total_proc = pd.to_numeric(
                        proc_r.get('Preco_Total',0),
                        errors='coerce'
                    ).fillna(0).sum()
                    st.metric(
                        "✅ Total Reembolsado",
                        f"€{total_proc:,.2f}"
                    )
                    cols_proc = [c for c in [
                        'Colaborador','Tipo','Origem','Destino',
                        'Data_Ida','Companhia','Preco_Total'
                    ] if c in proc_r.columns]
                    st.dataframe(
                        proc_r[cols_proc],
                        use_container_width=True,
                        hide_index=True
                    )


# ─────────────────────────────────────────────────────────────────
# RENDER RESUMO VIAGEM
# ─────────────────────────────────────────────────────────────────

def _render_resumo_viagem(obras_db, users):
    """Tab que agrega dormidas + bilhetes da mesma deslocação."""

    dormidas_db = _load("dormidas.csv",[
        "ID","Data_Checkin","Colaborador","Obra","Hotel","Total"
    ])
    bilhetes_db = _load("bilhetes_viagem.csv",[
        "ID","Data_Ida","Colaborador","Obra","Tipo",
        "Origem","Destino","Preco_Total","Estado"
    ])

    st.markdown("### 📊 Resumo de Deslocações")
    st.info(
        "Visão agregada por colaborador e obra — "
        "bilhetes + dormidas da mesma missão."
    )

    obras_list = obras_db[obras_db['Ativa']=='Ativa']['Obra'].tolist() \
                 if not obras_db.empty else []
    users_list = users['Nome'].tolist() if not users.empty else []

    col_sf1, col_sf2 = st.columns(2)
    with col_sf1:
        obra_sf = st.selectbox(
            "Obra", ["Todas"]+obras_list, key="res_obra_filt"
        )
    with col_sf2:
        colab_sf = st.selectbox(
            "Colaborador", ["Todos"]+users_list, key="res_colab_filt"
        )

    # Agregação
    registos = []

    # Agregar bilhetes por colaborador/obra
    if not bilhetes_db.empty:
        bdb = bilhetes_db.copy()
        bdb['Preco_N'] = pd.to_numeric(
            bdb.get('Preco_Total',0),errors='coerce'
        ).fillna(0)
        for (colab, obra), grp in bdb.groupby(['Colaborador','Obra']):
            registos.append({
                "Colaborador": colab,
                "Obra":        obra,
                "Bilhetes":    len(grp),
                "Custo_Bilhetes": grp['Preco_N'].sum(),
                "Dormidas":    0,
                "Custo_Dormidas": 0.0,
            })

    # Agregar dormidas
    if not dormidas_db.empty:
        ddb = dormidas_db.copy()
        ddb['Total_N'] = pd.to_numeric(
            ddb.get('Total',0),errors='coerce'
        ).fillna(0)
        for (colab, obra), grp in ddb.groupby(['Colaborador','Obra']):
            # Verificar se já existe na lista
            existe = False
            for r in registos:
                if r['Colaborador']==colab and r['Obra']==obra:
                    r['Dormidas'] += len(grp)
                    r['Custo_Dormidas'] += grp['Total_N'].sum()
                    existe = True
                    break
            if not existe:
                registos.append({
                    "Colaborador":   colab,
                    "Obra":          obra,
                    "Bilhetes":      0,
                    "Custo_Bilhetes":0.0,
                    "Dormidas":      len(grp),
                    "Custo_Dormidas":grp['Total_N'].sum(),
                })

    if not registos:
        st.info("📋 Sem deslocações registadas.")
        return

    df_res = pd.DataFrame(registos)
    df_res['Total_Deslocacao'] = (
        df_res['Custo_Bilhetes'] + df_res['Custo_Dormidas']
    )

    if obra_sf  != "Todas":
        df_res = df_res[df_res['Obra']==obra_sf]
    if colab_sf != "Todos":
        df_res = df_res[df_res['Colaborador']==colab_sf]

    # KPIs globais
    tot_bil = df_res['Custo_Bilhetes'].sum()
    tot_dor = df_res['Custo_Dormidas'].sum()
    tot_tot = df_res['Total_Deslocacao'].sum()

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("💰 Total Bilhetes",  f"€{tot_bil:,.2f}")
    with c2: st.metric("🏨 Total Dormidas",   f"€{tot_dor:,.2f}")
    with c3: st.metric("📊 Total Deslocações",f"€{tot_tot:,.2f}")
    with c4: st.metric("👷 Colaboradores",     df_res['Colaborador'].nunique())

    st.divider()

    # Tabela de resumo por colaborador / obra
    for _, r in df_res.sort_values(
        'Total_Deslocacao', ascending=False
    ).iterrows():
        tot_r = float(r.get('Total_Deslocacao',0))
        pct_b = round(r['Custo_Bilhetes']/tot_r*100) \
                if tot_r > 0 else 0
        pct_d = 100 - pct_b

        st.markdown(
            f"<div style='background:#1E293B;"
            f"border-radius:12px;padding:14px 16px;"
            f"margin-bottom:8px;'>"
            f"<div style='display:flex;"
            f"justify-content:space-between;'>"
            f"<div>"
            f"<b style='color:#F1F5F9;'>"
            f"👤 {r.get('Colaborador','')}</b>"
            f"<span style='color:#64748B;margin-left:8px;'>"
            f"🏗️ {r.get('Obra','')}</span><br>"
            f"<small style='color:#64748B;'>"
            f"✈️ {int(r.get('Bilhetes',0))} bilhete(s) "
            f"€{r.get('Custo_Bilhetes',0):,.2f} · "
            f"🏨 {int(r.get('Dormidas',0))} dormida(s) "
            f"€{r.get('Custo_Dormidas',0):,.2f}"
            f"</small>"
            f"</div>"
            f"<b style='color:#10B981;font-size:1.1rem;'>"
            f"€{tot_r:,.2f}</b>"
            f"</div>"
            f"<div style='background:#0F172A;"
            f"border-radius:3px;height:5px;margin-top:8px;'>"
            f"<div style='background:#3B82F6;width:{pct_b}%;"
            f"height:5px;border-radius:3px;display:inline-block;'>"
            f"</div>"
            f"<div style='background:#8B5CF6;width:{pct_d}%;"
            f"height:5px;border-radius:3px;display:inline-block;'>"
            f"</div>"
            f"</div>"
            f"<small style='color:#3B82F6;'>■ Bilhetes {pct_b}%</small>"
            f"<small style='color:#8B5CF6;margin-left:8px;'>"
            f"■ Dormidas {pct_d}%</small>"
            f"</div>",
            unsafe_allow_html=True
        )

    # Gráfico por obra
    import plotly.graph_objects as go
    if len(df_res) > 1:
        df_g = df_res.groupby('Obra').agg(
            Bilhetes=('Custo_Bilhetes','sum'),
            Dormidas=('Custo_Dormidas','sum')
        ).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Bilhetes', x=df_g['Obra'],
            y=df_g['Bilhetes'],
            marker_color='#3B82F6',
            text=[f"€{v:,.0f}" for v in df_g['Bilhetes']],
            textposition='auto',
            textfont={'color':'#F1F5F9','size':9}
        ))
        fig.add_trace(go.Bar(
            name='Dormidas', x=df_g['Obra'],
            y=df_g['Dormidas'],
            marker_color='#8B5CF6',
            text=[f"€{v:,.0f}" for v in df_g['Dormidas']],
            textposition='auto',
            textfont={'color':'#F1F5F9','size':9}
        ))
        fig.update_layout(
            title={'text':'Custo de Deslocações por Obra',
                   'font':{'color':'#F1F5F9'}},
            barmode='stack',
            height=280,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.5)',
            font={'color':'#F1F5F9'},
            legend={'font':{'color':'#94A3B8'}},
            xaxis={'tickfont':{'color':'#94A3B8'},
                   'gridcolor':'#334155'},
            yaxis={'tickfont':{'color':'#94A3B8'},
                   'gridcolor':'#334155',
                   'tickprefix':'€'},
            margin=dict(t=40,b=20,l=10,r=10)
        )
        st.plotly_chart(fig)

    # Exportar
    csv_res = df_res.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        "📥 Exportar Resumo",
        data=csv_res.encode('utf-8-sig'),
        file_name=(
            f"resumo_deslocacoes_"
            f"{date.today().strftime('%Y%m%d')}.csv"
        ),
        mime="text/csv",
        key="dl_res_desl"
    )


# ─────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def render_deslocacoes(obras_db, users, *_):
    """Módulo de Deslocações — Dormidas + Bilhetes + Resumo."""

    st.markdown("## 🗺️ Gestão de Deslocações")

    tab_dorm, tab_bil, tab_res = st.tabs([
        "🏨 Dormidas",
        "🎫 Bilhetes de Viagem",
        "📊 Resumo por Deslocação",
    ])

    with tab_dorm:
        _render_dormidas(obras_db, users)

    with tab_bil:
        _render_bilhetes(obras_db, users)

    with tab_res:
        _render_resumo_viagem(obras_db, users)

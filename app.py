import streamlit as st
import pandas as pd
import json, base64, time
from datetime import datetime
from core import (init_session, check_timeout, load_all, inject_pwa_meta,
                  inject_global_css, ICONS, hp, save_db, log_audit,
                  criar_notificacao, load_db, _gcs_read, inv,
                  _verificar_alerta_backup, _registar_backup,
                  # FIX 1 — importar a versão cached de core em vez de redefinir
                  _load_users_cached)
from translations import init_language, t, get_language_options, set_language

try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

st.set_page_config(
    page_title="GESTNOW v3 - Instrumentação Industrial [DEV]",
    page_icon=ICONS["app"],
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help':    'https://github.com/diogomhenriques90-droid/GestNow',
        'Report a bug':"https://github.com/diogomhenriques90-droid/GestNow/issues",
        'About':       "# GESTNOW v3\nSistema de Gestão de Instrumentação Industrial"
    }
)

inject_pwa_meta()
inject_global_css()

st.markdown("""
<style>
.stApp { transition: none !important; }
[data-testid="stAppViewContainer"] { transition: none !important; }
iframe { transition: none !important; }
</style>
""", unsafe_allow_html=True)

init_session()
check_timeout()
init_language()

from streamlit_autorefresh import st_autorefresh

if st.session_state.get('user'):
    st_autorefresh(interval=300000, limit=None, key="auto_refresh")

page = st.query_params.get("page", "")
if page == "criar_admin":
    from criar_admin import render_criar_admin
    render_criar_admin()
    st.stop()

# =============================================================================
# FIX 1 — _load_users_fresh usa agora _load_users_cached do core (TTL=60s)
# Em vez de fazer leitura directa ao GCS em cada chamada,
# reutiliza o resultado em cache durante 60 segundos.
# Quando é necessário forçar leitura fresca (após save),
# chama-se _load_users_cached.clear() via inv("usuarios.csv").
# =============================================================================
def _load_users_fresh():
    """
    Wrapper que usa a versão cached do core.
    Para forçar re-leitura: inv("usuarios.csv")
    """
    return _load_users_cached()


def _verificar_validacoes_pendentes(user_nome):
    try:
        users = _load_users_fresh()
        if users.empty: return False, False, False, False
        match = users[users['Nome'] == user_nome]
        if match.empty: return False, False, False, False
        row = match.iloc[0]
        pdfs_pend   = row.get('PDFs_Validados',  'Não') != 'Sim'
        preco_pend  = row.get('PrecoHoraStatus', '')    == ''
        perfil_val  = str(row.get('Perfil_Completo', '')).strip()
        perfil_pend = perfil_val != 'Sim'
        iban_pend   = str(row.get('IBAN_Comprovativo_b64', '')).strip() == ''
        return pdfs_pend, preco_pend, perfil_pend, iban_pend
    except:
        return False, False, False, False

def _render_validacao_obrigatoria(user_nome):
    users_live = _load_users_fresh()
    if users_live.empty: return False
    match = users_live[users_live['Nome'] == user_nome]
    if match.empty: return False

    user_idx  = match.index[0]
    user_data = match.iloc[0]

    pdfs_validados   = user_data.get('PDFs_Validados',  'Não')
    preco_status     = user_data.get('PrecoHoraStatus', '')
    preco_hora_valor = user_data.get('PrecoHora',       '15.0')
    perfil_completo  = str(user_data.get('Perfil_Completo', '')).strip()

    try:
        pdfs_db = load_db("pdfs_obrigatorios.csv", [
            "ID","Nome","Descricao","Data_Upload","Upload_Por","Ficheiro_b64"
        ], silent=True)
    except:
        pdfs_db = pd.DataFrame(columns=[
            "ID","Nome","Descricao","Data_Upload","Upload_Por","Ficheiro_b64"
        ])

    try:
        pdfs_vistos = json.loads(user_data.get('PDFs_Vistos', '[]'))
    except:
        pdfs_vistos = []

    total_pdfs      = len(pdfs_db) if not pdfs_db.empty else 0
    pdf_ids_validos = pdfs_db['ID'].tolist() if not pdfs_db.empty else []
    pdfs_val_count  = len([p for p in pdfs_vistos if p in pdf_ids_validos])

    tem_pdfs_pend   = (pdfs_validados  != 'Sim') and (total_pdfs > 0)
    tem_preco_pend  = (preco_status    == '')
    tem_perfil_pend = (perfil_completo != 'Sim')
    tem_iban_pend   = str(user_data.get('IBAN_Comprovativo_b64', '')).strip() == ''

    if not tem_pdfs_pend and not tem_preco_pend and not tem_perfil_pend and not tem_iban_pend:
        return False

    st.markdown("""
    <style>
    .onboard-header {
        background: linear-gradient(135deg, #1E40AF, #1E293B);
        padding: 25px; border-radius: 20px; margin-bottom: 25px; text-align: center;
        border: 2px solid rgba(59,130,246,0.4);
    }
    .step-card {
        border-radius: 15px; padding: 20px; margin-bottom: 15px;
        border: 2px solid rgba(255,255,255,0.1);
    }
    .step-active  { background:rgba(59,130,246,0.15); border-color:#3B82F6; }
    .pdf-row {
        background:rgba(255,255,255,0.04); border-radius:10px;
        padding:12px 15px; margin-bottom:10px;
    }
    .stTextInput label, .stSelectbox label, .stNumberInput label,
    .stTextArea label, .stDateInput label, .stRadio label, .stCheckbox label {
        color: #F8FAFC !important; font-weight: 500 !important;
    }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #FFFFFF !important; color: #1E293B !important;
        border: 1px solid rgba(0,0,0,0.2) !important;
    }
    .stSelectbox > div > div > div {
        background: #FFFFFF !important; color: #1E293B !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="onboard-header">
        <div style="font-size:2.5rem;margin-bottom:12px;">👋</div>
        <h2 style="color:white;margin:0 0 8px 0;">Bem-vindo, {user_nome}!</h2>
        <p style="color:rgba(255,255,255,0.7);margin:0;font-size:1rem;">
            Completa os seguintes passos de integração para aceder à app.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    iban_ok = str(user_data.get('IBAN_Comprovativo_b64', '')).strip() != ''
    passos = [
        (pdfs_validados   == 'Sim',                 tem_pdfs_pend,  "📄", "Passo 1\nDocumentos"),
        (preco_status in ['Aceite','Recusado'],      tem_preco_pend, "💰", "Passo 2\nPreço Hora"),
        (perfil_completo  == 'Sim',                 tem_perfil_pend,"👤", "Passo 3\nMeu Perfil"),
        (iban_ok,                                   tem_iban_pend,  "🏦", "Passo 4\nIBAN"),
    ]
    for col, (done, active, ic, label) in zip([col_s1,col_s2,col_s3,col_s4], passos):
        cor = "#10B981" if done else "#3B82F6" if active else "#64748B"
        with col:
            st.markdown(f"""
            <div style="text-align:center;padding:15px;
                background:rgba(255,255,255,0.05);border-radius:12px;
                border:2px solid {cor};">
                <div style="font-size:1.8rem;">{ic}</div>
                <div style="color:{cor};font-weight:bold;font-size:0.85rem;
                    margin-top:5px;white-space:pre-line;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── PASSO 1: DOCUMENTOS ───────────────────────────────────────────
    if tem_pdfs_pend:
        pct = int(pdfs_val_count / total_pdfs * 100) if total_pdfs > 0 else 0
        st.markdown(f"""
        <div class="step-card step-active">
            <h3 style="color:#60A5FA;margin:0 0 8px 0;">📄 Passo 1 — Documentos Obrigatórios</h3>
            <p style="color:#94A3B8;margin:0 0 12px 0;font-size:0.9rem;">
                Lê e confirma cada documento. <b>{pdfs_val_count}/{total_pdfs}</b> validados.
            </p>
            <div style="background:rgba(0,0,0,0.3);border-radius:6px;height:8px;">
                <div style="background:#10B981;width:{pct}%;height:8px;border-radius:6px;"></div>
            </div>
        </div>""", unsafe_allow_html=True)

        if not pdfs_db.empty:
            for _, pdf in pdfs_db.iterrows():
                pdf_id   = str(pdf.get('ID','')).strip()
                pdf_nome = pdf.get('Nome','Documento')
                pdf_desc = pdf.get('Descricao','')
                visto    = pdf_id in pdfs_vistos

                st.markdown(f"""
                <div class="pdf-row" style="border-left:4px solid {'#10B981' if visto else '#EF4444'};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b style="color:{'#10B981' if visto else '#F8FAFC'};">
                                {'✅' if visto else '📄'} {pdf_nome}
                            </b>
                            <p style="color:#64748B;font-size:0.82rem;margin:3px 0 0 0;">{pdf_desc}</p>
                        </div>
                        <span style="color:{'#10B981' if visto else '#F59E0B'};
                            font-size:0.8rem;font-weight:bold;white-space:nowrap;margin-left:10px;">
                            {'Validado' if visto else '⚠️ Por ler'}
                        </span>
                    </div>
                </div>""", unsafe_allow_html=True)

                col_dl, col_ok = st.columns([2, 1])
                with col_dl:
                    if pdf.get('Ficheiro_b64'):
                        try:
                            pdf_data = base64.b64decode(pdf['Ficheiro_b64'])
                            st.download_button(
                                f"📥 Ler: {pdf_nome}", data=pdf_data,
                                file_name=f"{pdf_nome}.pdf", mime="application/pdf",
                                key=f"app_dl_pdf_{pdf_id}", use_container_width=True
                            )
                        except:
                            st.error("❌ Erro ao carregar PDF")
                with col_ok:
                    if not visto:
                        if st.button("✅ Confirmar", key=f"app_val_pdf_{pdf_id}",
                                     use_container_width=True, type="primary"):
                            pdfs_vistos.append(pdf_id)
                            novos_val = len([p for p in pdfs_vistos if p in pdf_ids_validos])
                            # Recarregar users frescos para editar
                            u_edit = _load_users_cached().copy()
                            mask   = u_edit['Nome'] == user_nome
                            if mask.any():
                                u_edit.loc[mask, 'PDFs_Vistos'] = json.dumps(pdfs_vistos)
                                if novos_val >= total_pdfs:
                                    u_edit.loc[mask, 'PDFs_Validados']      = 'Sim'
                                    u_edit.loc[mask, 'PDFs_Validacao_Data'] = \
                                        datetime.now().strftime("%d/%m/%Y %H:%M")
                                save_db(u_edit, "usuarios.csv")
                                # FIX 2 — inv selectivo
                                inv("usuarios.csv")
                            if novos_val >= total_pdfs:
                                log_audit(usuario=user_nome, acao="VALIDAR_PDFS",
                                          tabela="usuarios.csv", registro_id=user_nome,
                                          detalhes=f"Validou {novos_val} PDFs", ip="")
                                criar_notificacao(destinatario="admin",
                                    titulo="✅ PDFs Validados",
                                    mensagem=f"{user_nome} validou todos os documentos.",
                                    tipo="success", acao_url="/admin?tab=rh")
                                st.success("✅ Todos os documentos confirmados!")
                                time.sleep(1)
                            else:
                                st.success(f"✅ '{pdf_nome}' confirmado! ({novos_val}/{total_pdfs})")
                                time.sleep(0.5)
                            st.rerun()
                    else:
                        st.success("✅")

        if pdfs_val_count < total_pdfs:
            st.warning(f"⚠️ Faltam {total_pdfs - pdfs_val_count} documento(s).")
        st.stop()

    # ── PASSO 2: PREÇO HORA ───────────────────────────────────────────
    if tem_preco_pend:
        st.markdown(f"""
        <div class="step-card step-active">
            <h3 style="color:#60A5FA;margin:0 0 8px 0;">💰 Passo 2 — Validação do Preço Hora</h3>
            <p style="color:#94A3B8;margin:0;font-size:0.9rem;">
                Aceita ou recusa o preço hora proposto pela empresa.
            </p>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.07);border:2px solid rgba(255,255,255,0.15);
            border-radius:15px;padding:30px;text-align:center;margin-bottom:25px;">
            <p style="color:#94A3B8;margin:0 0 10px 0;">Preço Hora Proposto:</p>
            <p style="color:#10B981;font-size:3.5rem;font-weight:900;margin:0 0 15px 0;">
                € {preco_hora_valor}
                <span style="font-size:1.4rem;color:#64748B;">/hora</span>
            </p>
        </div>""", unsafe_allow_html=True)

        col_ac, col_rec = st.columns(2)
        with col_ac:
            if st.button("✅ ACEITAR", key="app_aceitar_preco",
                          use_container_width=True, type="primary"):
                u2 = _load_users_cached().copy()
                mask = u2['Nome'] == user_nome
                if mask.any():
                    u2.loc[mask, 'PrecoHoraStatus'] = 'Aceite'
                    u2.loc[mask, 'PrecoHoraData']   = datetime.now().strftime("%d/%m/%Y %H:%M")
                    save_db(u2, "usuarios.csv")
                    inv("usuarios.csv")  # FIX 2 — selectivo
                    log_audit(usuario=user_nome, acao="ACEITAR_PRECO_HORA",
                              tabela="usuarios.csv", registro_id=user_nome,
                              detalhes=f"Aceitou €{preco_hora_valor}/hora", ip="")
                    criar_notificacao(destinatario="admin",
                        titulo="💰 Preço Hora Aceite",
                        mensagem=f"{user_nome} aceitou €{preco_hora_valor}/hora.",
                        tipo="success", acao_url="/admin?tab=rh")
                    st.success("✅ Preço hora aceite!")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
        with col_rec:
            if st.button("❌ RECUSAR", key="app_recusar_preco",
                          use_container_width=True, type="secondary"):
                u2 = _load_users_cached().copy()
                mask = u2['Nome'] == user_nome
                if mask.any():
                    u2.loc[mask, 'PrecoHoraStatus'] = 'Recusado'
                    u2.loc[mask, 'PrecoHoraData']   = datetime.now().strftime("%d/%m/%Y %H:%M")
                    save_db(u2, "usuarios.csv")
                    inv("usuarios.csv")  # FIX 2 — selectivo
                    log_audit(usuario=user_nome, acao="RECUSAR_PRECO_HORA",
                              tabela="usuarios.csv", registro_id=user_nome,
                              detalhes=f"Recusou €{preco_hora_valor}/hora", ip="")
                    criar_notificacao(destinatario="admin",
                        titulo="💰 Preço Hora RECUSADO",
                        mensagem=f"{user_nome} RECUSOU €{preco_hora_valor}/hora.",
                        tipo="error", acao_url="/admin?tab=rh")
                    st.warning("❌ Preço recusado. Admin notificado.")
                    time.sleep(1.5)
                    st.rerun()
        st.stop()

    # ── PASSO 3: PERFIL ───────────────────────────────────────────────
    if tem_perfil_pend:
        st.markdown("""
        <div class="step-card step-active">
            <h3 style="color:#60A5FA;margin:0 0 8px 0;">👤 Passo 3 — Preencher o Meu Perfil</h3>
            <p style="color:#94A3B8;margin:0;font-size:0.9rem;">
                Preenche os teus dados para os Recursos Humanos.
                Campos com <b>*</b> são obrigatórios.
            </p>
        </div>""", unsafe_allow_html=True)

        with st.form("form_onboard_perfil"):
            st.markdown("#### 📋 Dados Pessoais")
            col1, col2 = st.columns(2)
            with col1:
                telefone     = st.text_input("Telefone *",
                    value=user_data.get('Telefone',''), key="onb_tel", placeholder="9XXXXXXXX")
                data_nasc    = st.text_input("Data Nascimento * (dd/mm/aaaa)",
                    value=user_data.get('DataNasc',''), key="onb_nasc", placeholder="01/01/1990")
                naturalidade = st.text_input("Naturalidade",
                    value=user_data.get('Naturalidade',''), key="onb_nat")
            with col2:
                nif          = st.text_input("NIF *",
                    value=user_data.get('NIF',''), key="onb_nif", placeholder="XXXXXXXXX")
                niss         = st.text_input("NISS",
                    value=user_data.get('NISS',''), key="onb_niss", placeholder="XXXXXXXXXXX")
                estado_civil = st.selectbox("Estado Civil *",
                    ["Solteiro(a)","Casado(a)","Divorciado(a)","Viúvo(a)","União de Facto"],
                    key="onb_ec")

            st.markdown("#### 📍 Morada")
            morada = st.text_input("Morada *",
                value=user_data.get('Morada',''), key="onb_morada", placeholder="Rua, nº, andar")
            col3, col4, col5 = st.columns(3)
            with col3:
                localidade = st.text_input("Localidade *",
                    value=user_data.get('Localidade',''), key="onb_loc")
            with col4:
                concelho   = st.text_input("Concelho",
                    value=user_data.get('Concelho',''), key="onb_conc")
            with col5:
                cod_postal = st.text_input("Código Postal",
                    value=user_data.get('Codigo_Postal',''), key="onb_cp", placeholder="XXXX-XXX")

            st.markdown("#### 🆔 Documentos & Contacto")
            col6, col7 = st.columns(2)
            with col6:
                cc    = st.text_input("Nº Cartão Cidadão", value=user_data.get('CC',''), key="onb_cc")
                cc_v  = st.text_input("Validade CC (dd/mm/aaaa)",
                    value=user_data.get('CC_Validade',''), key="onb_cc_val")
            with col7:
                email = st.text_input("Email", value=user_data.get('Email',''),
                    key="onb_email", placeholder="exemplo@email.com")

            st.markdown("#### 🚨 Emergência")
            col8, col9 = st.columns(2)
            with col8:
                nome_emerg = st.text_input("Nome *",
                    value=user_data.get('Nome_Emergencia',''), key="onb_emerg_nome")
                tel_emerg  = st.text_input("Telefone *",
                    value=user_data.get('Contacto_Emergencia',''), key="onb_emerg_tel")
            with col9:
                grau = st.text_input("Grau Parentesco",
                    value=user_data.get('Grau_Parentesco',''), key="onb_grau")

            st.markdown("#### 💼 Dados Profissionais")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                profissao = st.text_input("Profissão",
                    value=user_data.get('Profissao',''), key="onb_prof",
                    placeholder="Ex: Instrumentista")
                categoria = st.text_input("Categoria Profissional",
                    value=user_data.get('Categoria_Profissional',''), key="onb_cat",
                    placeholder="Ex: Técnico Sénior")
            with col_p2:
                hab_opts = ["9º Ano","12º Ano","Licenciatura","Mestrado","Doutoramento","Outro"]
                hab_v = user_data.get('Habilitacoes_Literarias','12º Ano')
                habilitacoes = st.selectbox("Habilitações",
                    hab_opts,
                    index=hab_opts.index(hab_v) if hab_v in hab_opts else 1,
                    key="onb_hab")

            st.markdown("#### 👕 Fardamento")
            col10, col11, col12 = st.columns(3)
            cam_opts = ["XS","S","M","L","XL","XXL","XXXL"]
            cal_opts = ["XS (34/36)","S (38)","M (40/42)","L (42/44)","XL (46/48)","XXL (50/52)"]
            bot_opts = ["40","41","42","43","44","45","Outro"]
            with col10:
                cam_v   = user_data.get('Tamanho_Camisola','M')
                tam_cam = st.selectbox("Camisola", cam_opts,
                    index=cam_opts.index(cam_v) if cam_v in cam_opts else 3, key="onb_cam")
            with col11:
                cal_v   = user_data.get('Tamanho_Calca','')
                tam_cal = st.selectbox("Calça", cal_opts,
                    index=cal_opts.index(cal_v) if cal_v in cal_opts else 0, key="onb_cal")
            with col12:
                bot_v   = user_data.get('Tamanho_Botas','')
                tam_bot = st.selectbox("Botas", bot_opts,
                    index=bot_opts.index(bot_v) if bot_v in bot_opts else 2, key="onb_bot")

            submitted = st.form_submit_button("💾 Guardar e Continuar →",
                use_container_width=True, type="primary")

        if submitted:
            erros = []
            if not telefone.strip():   erros.append("Telefone")
            if not nif.strip():        erros.append("NIF")
            if not data_nasc.strip():  erros.append("Data Nascimento")
            if not morada.strip():     erros.append("Morada")
            if not localidade.strip(): erros.append("Localidade")
            if not nome_emerg.strip(): erros.append("Nome Emergência")
            if not tel_emerg.strip():  erros.append("Telefone Emergência")
            if erros:
                st.error(f"❌ Campos em falta: {', '.join(erros)}")
            else:
                u3 = _load_users_cached().copy()
                mask = u3['Nome'] == user_nome
                if mask.any():
                    for campo, valor in {
                        'Telefone': telefone.strip(), 'NIF': nif.strip(),
                        'DataNasc': data_nasc.strip(), 'Morada': morada.strip(),
                        'Localidade': localidade.strip(), 'Concelho': concelho.strip(),
                        'Codigo_Postal': cod_postal.strip(), 'Naturalidade': naturalidade.strip(),
                        'Estado_Civil': estado_civil, 'CC': cc.strip(), 'CC_Validade': cc_v.strip(),
                        'NISS': niss.strip(), 'Email': email.strip(),
                        'Nome_Emergencia': nome_emerg.strip(), 'Contacto_Emergencia': tel_emerg.strip(),
                        'Grau_Parentesco': grau.strip(), 'Tamanho_Camisola': tam_cam,
                        'Tamanho_Calca': tam_cal, 'Tamanho_Botas': tam_bot,
                        'Profissao':                 profissao.strip(),
                        'Categoria_Profissional':    categoria.strip(),
                        'Habilitacoes_Literarias':   habilitacoes,
                        'Perfil_Completo': 'Sim',
                        'Perfil_Data': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    }.items():
                        if campo not in u3.columns:
                            u3[campo] = ''
                        u3.loc[mask, campo] = valor
                    save_db(u3, "usuarios.csv")
                    inv("usuarios.csv")  # FIX 2 — selectivo
                    log_audit(usuario=user_nome, acao="COMPLETAR_PERFIL_ONBOARDING",
                              tabela="usuarios.csv", registro_id=user_nome,
                              detalhes="Perfil preenchido no onboarding", ip="")
                    criar_notificacao(destinatario="admin",
                        titulo="👤 Perfil Preenchido",
                        mensagem=f"{user_nome} completou todos os passos de integração.",
                        tipo="success", acao_url="/admin?tab=rh")
                    st.success("✅ Perfil guardado! Bem-vindo(a) ao GESTNOW!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
        st.stop()

    # ── PASSO 4: UPLOAD COMPROVATIVO IBAN ─────────────────────────────
    if tem_iban_pend:
        st.markdown("""
        <div class="step-card step-active">
            <h3 style="color:#60A5FA;margin:0 0 8px 0;">🏦 Passo 4 — Comprovativo Bancário</h3>
            <p style="color:#94A3B8;margin:0;font-size:0.9rem;">
                Faz upload do comprovativo IBAN (extrato bancário, documento do banco
                ou captura do homebanking com o IBAN visível).
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:rgba(59,130,246,0.08);border-radius:10px;
            padding:14px;margin-bottom:16px;border-left:3px solid #3B82F6;">
            <p style="color:#93C5FD;font-size:0.85rem;margin:0;">
                ℹ️ O IBAN não é guardado como texto — apenas o comprovativo é armazenado
                de forma segura para acesso exclusivo do RH.
            </p>
        </div>
        """, unsafe_allow_html=True)

        ficheiro_iban = st.file_uploader(
            "📄 Comprovativo bancário (PDF, JPG ou PNG)",
            type=["pdf","jpg","jpeg","png"],
            key="onb_iban_file"
        )

        if ficheiro_iban:
            file_b64 = base64.b64encode(ficheiro_iban.read()).decode('utf-8')
            st.success(f"✅ Ficheiro carregado: {ficheiro_iban.name}")
            if st.button("💾 Guardar e Concluir Integração",
                         use_container_width=True, type="primary",
                         key="btn_guardar_iban"):
                u4 = _load_users_cached().copy()
                mask = u4['Nome'] == user_nome
                if mask.any():
                    u4.loc[mask, 'IBAN_Comprovativo_b64'] = file_b64
                    u4.loc[mask, 'IBAN_Data_Upload']      = \
                        datetime.now().strftime("%d/%m/%Y %H:%M")
                    save_db(u4, "usuarios.csv")
                    inv("usuarios.csv")  # FIX 2 — selectivo
                    log_audit(usuario=user_nome, acao="UPLOAD_IBAN",
                              tabela="usuarios.csv", registro_id=user_nome,
                              detalhes="Comprovativo IBAN uploaded", ip="")
                    criar_notificacao(destinatario="admin",
                        titulo="🏦 Comprovativo IBAN",
                        mensagem=f"{user_nome} submeteu o comprovativo bancário.",
                        tipo="info", acao_url="/admin?tab=rh")
                    st.success("✅ Integração completa! Bem-vindo(a) ao GESTNOW!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
        else:
            st.info("👆 Seleciona o ficheiro para continuar.")

        st.stop()

    return False


# =============================================================================
# SIDEBAR
# =============================================================================
if st.session_state.get('user'):
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:20px;
            background:linear-gradient(135deg,#1E293B,#0F172A);
            border-radius:16px;margin-bottom:20px;">
            <div style="font-size:3rem;margin-bottom:10px;">{ICONS["app"]}</div>
            <div style="font-size:1.2rem;font-weight:700;color:#F8FAFC;">GESTNOW v3</div>
            <div style="font-size:0.8rem;color:#94A3B8;">Instrumentação Industrial</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="padding:12px;background:rgba(255,255,255,0.05);
            border-radius:12px;margin-bottom:16px;">
            <div style="font-size:1rem;font-weight:600;color:#F8FAFC;">
                👤 {st.session_state.user}
            </div>
            <div style="font-size:0.85rem;color:#94A3B8;">
                {st.session_state.tipo} | {st.session_state.cargo}
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"**{ICONS['app']} {t('language')}**")
        lang_opts = get_language_options()
        curr_lang = st.session_state.language
        sel_lang  = st.selectbox(
            "🌐", options=list(lang_opts.keys()),
            format_func=lambda x: lang_opts[x],
            index=list(lang_opts.keys()).index(curr_lang),
            label_visibility="collapsed", key="sidebar_language_sel"
        )
        if sel_lang != curr_lang:
            set_language(sel_lang)
            st.rerun()

        st.divider()
        tipo  = st.session_state.get('tipo', '')
        cargo = st.session_state.get('cargo', '')
        tem_acesso_inst = (tipo in ['Chefe de Equipa','Admin','Gestor'] or
                           cargo in ['Chefe de Equipa','Encarregado','Instrumentista'])
        eh_cliente = (tipo == 'Cliente')

        if eh_cliente:
            menu_item = st.radio("Nav",
                [f"{ICONS['dashboard']} Portal", "Logout"],
                label_visibility="collapsed", key="sidebar_nav_cliente")
        elif tipo == 'Admin':
            menu_item = st.radio("Nav",
                [f"{ICONS['dashboard']} Dashboard", f"{ICONS['admin']} Admin",
                 f"{ICONS['instrumentation']} Instrumentação",
                 f"{ICONS['profile']} Perfil", "Logout"],
                label_visibility="collapsed", key="sidebar_nav_admin")
        elif tem_acesso_inst:
            menu_item = st.radio("Nav",
                [f"{ICONS['dashboard']} Início", f"{ICONS['technician']} Obra",
                 f"{ICONS['instrumentation']} Instrumentação",
                 f"{ICONS['profile']} Perfil", "Logout"],
                label_visibility="collapsed", key="sidebar_nav_chefe")
        else:
            menu_item = st.radio("Nav",
                [f"{ICONS['dashboard']} Início", f"{ICONS['technician']} Obra",
                 f"{ICONS['profile']} Perfil", "Logout"],
                label_visibility="collapsed", key="sidebar_nav_tecnico")

        if not st.session_state.get('_menu_locked', False):
            st.session_state.menu_selected = menu_item

        st.divider()
        if st.button(f"{ICONS['logout']} {t('logout')}", use_container_width=True,
                     type="secondary", key="sidebar_logout_btn"):
            st.session_state.clear()
            st.rerun()

# =============================================================================
# BOTTOM NAVIGATION BAR (MOBILE)
# =============================================================================
if st.session_state.get('user') and HAS_OPTION_MENU:
    tipo  = st.session_state.get('tipo', '')
    cargo = st.session_state.get('cargo', '')
    eh_cliente = (tipo == 'Cliente')

    if eh_cliente:
        nav_options = ["Portal", "Logout"]
        nav_icons   = ["house", "box-arrow-right"]
    elif tipo == 'Admin':
        nav_options = ["Dashboard","Admin","Instrumentação","Perfil","Logout"]
        nav_icons   = ["graph-up","gear","tools","person","box-arrow-right"]
    elif tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
        nav_options = ["Início","Obra","Instrumentação","Perfil","Logout"]
        nav_icons   = ["house","tools","wrench","person","box-arrow-right"]
    else:
        nav_options = ["Início","Obra","Perfil","Logout"]
        nav_icons   = ["house","tools","person","box-arrow-right"]

    current_menu  = st.session_state.get('menu_selected', '')
    default_index = 0
    if tipo == 'Admin':
        if   "Admin"          in current_menu: default_index = 1
        elif "Instrumentação" in current_menu: default_index = 2
        elif "Perfil"         in current_menu: default_index = 3
        else:                                  default_index = 0
    elif tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
        if   "Obra"           in current_menu: default_index = 1
        elif "Instrumentação" in current_menu: default_index = 2
        elif "Perfil"         in current_menu: default_index = 3
        else:                                  default_index = 0
    else:
        if   "Obra"           in current_menu: default_index = 1
        elif "Perfil"         in current_menu: default_index = 2
        else:                                  default_index = 0

    selected = option_menu(
        menu_title=None, options=nav_options, icons=nav_icons,
        menu_icon="cast", default_index=default_index, orientation="horizontal",
        styles={
            "container":        {"padding":"0!important","background-color":"#1E293B",
                                 "position":"fixed","bottom":"0","width":"100%",
                                 "z-index":"999","border-top":"1px solid rgba(255,255,255,0.1)"},
            "icon":             {"color":"#F8FAFC","font-size":"20px"},
            "nav-link":         {"color":"#F8FAFC","font-size":"11px","margin":"0px",
                                 "text-align":"center","padding":"8px 4px"},
            "nav-link-selected":{"background-color":"#DC2626","color":"#FFFFFF"},
        }
    )

    nav_map = {
        "Início":         f"{ICONS['dashboard']} Início",
        "Portal":         f"{ICONS['dashboard']} Portal",
        "Obra":           f"{ICONS['technician']} Obra",
        "Instrumentação": f"{ICONS['instrumentation']} Instrumentação",
        "Dashboard":      f"{ICONS['dashboard']} Dashboard",
        "Admin":          f"{ICONS['admin']} Admin",
        "Perfil":         f"{ICONS['profile']} Perfil",
        "Logout":         "Logout",
    }

    if st.session_state.get('_menu_locked', False):
        st.session_state['_menu_locked'] = False
    else:
        new_menu = nav_map.get(selected, '')
        if new_menu and new_menu != st.session_state.get('menu_selected', ''):
            st.session_state.menu_selected = new_menu
            if selected == "Logout":
                st.session_state.clear()
            st.rerun()

    st.markdown("<div style='height:70px;'></div>", unsafe_allow_html=True)

# =============================================================================
# ROUTING PRINCIPAL
# =============================================================================
if not st.session_state.get('user'):
    from mod_login import render_login
    render_login()
else:
    DATA = load_all()
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db, inst_acessos_db,
     diarias_config_db, diarias_faltas_db, diarias_pagamentos_db,
     folhas_ocr_db) = DATA

    tipo      = st.session_state.get('tipo', '')
    user_nome = st.session_state.get('user', '')
    cargo     = st.session_state.get('cargo', '')
    tem_acesso_inst = (tipo in ['Chefe de Equipa','Admin','Gestor'] or
                       cargo in ['Chefe de Equipa','Encarregado','Instrumentista'])
    eh_cliente = (tipo == 'Cliente')
    menu       = st.session_state.get('menu_selected', '')

    if "Logout" in menu:
        st.session_state.clear()
        st.rerun()

    # ── BLOQUEIO CENTRALIZADO — só Técnicos e Chefes ──────────────────
    if tipo not in ['Admin', 'Cliente']:
        pdfs_pend, preco_pend, perfil_pend, iban_pend = _verificar_validacoes_pendentes(user_nome)
        if pdfs_pend or preco_pend or perfil_pend or iban_pend:
            _render_validacao_obrigatoria(user_nome)
            st.stop()

        # ── Bloqueio contrato pendente de assinatura ───────────────
        try:
            u_ct_check = _load_users_fresh()
            if not u_ct_check.empty:
                m_ct = u_ct_check[u_ct_check['Nome'] == user_nome]
                if not m_ct.empty:
                    row_ct = m_ct.iloc[0]
                    ct_enviado  = row_ct.get('Contrato_Enviado','')  == 'Sim'
                    ct_assinado = row_ct.get('Contrato_Assinado','') == 'Sim'
                    ct_validado = row_ct.get('Contrato_Validado_Admin','') == 'Sim'

                    if ct_enviado and not ct_assinado and not ct_validado:
                        st.markdown("""
                        <style>.stApp{background:#0F172A!important;}</style>
                        """, unsafe_allow_html=True)

                        st.markdown("""
                        <div style="background:linear-gradient(135deg,#1E40AF,#1E293B);
                            padding:30px;border-radius:20px;margin-bottom:25px;
                            text-align:center;border:2px solid rgba(59,130,246,0.4);">
                            <div style="font-size:3rem;margin-bottom:12px;">📄</div>
                            <h2 style="color:white;margin:0 0 10px;">Contrato pendente de assinatura</h2>
                            <p style="color:rgba(255,255,255,0.7);margin:0;font-size:0.95rem;">
                                O teu contrato de trabalho está disponível.<br>
                                Assina e faz upload para continuar a usar a app.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        ct_b64 = row_ct.get('Contrato_b64','')
                        if ct_b64:
                            try:
                                ct_bytes = base64.b64decode(ct_b64)
                                st.download_button(
                                    "📥 Descarregar Contrato para Assinar",
                                    data=ct_bytes,
                                    file_name=f"contrato_{user_nome.replace(' ','_')}.docx",
                                    mime="application/vnd.openxmlformats-officedocument"
                                         ".wordprocessingml.document",
                                    use_container_width=True,
                                    key="blk_dl_ct"
                                )
                            except:
                                st.error("Erro ao processar o contrato.")

                        st.markdown("""
                        <div style="background:rgba(59,130,246,0.1);border-radius:10px;
                            padding:14px;margin:16px 0;border-left:3px solid #3B82F6;">
                            <p style="color:#93C5FD;font-size:0.85rem;margin:0;">
                                📋 <b>Instruções:</b><br>
                                1. Descarrega o contrato acima<br>
                                2. Imprime e assina à mão<br>
                                3. Fotografa ou digitaliza<br>
                                4. Faz upload abaixo
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        ficheiro_assin = st.file_uploader(
                            "📤 Upload do contrato assinado",
                            type=["jpg","jpeg","png","pdf","docx"],
                            key="blk_ct_upload"
                        )
                        if ficheiro_assin:
                            tam_kb = len(ficheiro_assin.getvalue()) / 1024
                            st.success(
                                f"✅ Ficheiro: **{ficheiro_assin.name}** "
                                f"({tam_kb:.0f} KB)"
                            )
                            st.markdown(
                                "<p style='color:#F59E0B;font-size:0.82rem;margin:8px 0;'>"
                                "⚠️ Confirma que o contrato está assinado antes de submeter.</p>",
                                unsafe_allow_html=True
                            )
                            if st.button("✅ Submeter contrato assinado ao RH",
                                          key="blk_btn_assin",
                                          type="primary",
                                          use_container_width=True):
                                f_b64 = base64.b64encode(ficheiro_assin.getvalue()).decode()
                                u_up  = _load_users_cached().copy()
                                mask  = u_up['Nome'] == user_nome
                                if mask.any():
                                    u_up.loc[mask,'Contrato_Assinado']        = 'Sim'
                                    u_up.loc[mask,'Contrato_Assinatura_b64']  = f_b64
                                    u_up.loc[mask,'Contrato_Assinatura_Data'] = \
                                        datetime.now().strftime("%d/%m/%Y %H:%M")
                                    save_db(u_up, "usuarios.csv")
                                    criar_notificacao(
                                        destinatario="admin",
                                        titulo="✍️ Contrato Assinado",
                                        mensagem=f"{user_nome} submeteu o contrato assinado.",
                                        tipo="success", acao_url="/admin?tab=rh"
                                    )
                                    log_audit(usuario=user_nome,
                                              acao="SUBMETER_CONTRATO",
                                              tabela="usuarios.csv",
                                              registro_id=user_nome,
                                              detalhes="Contrato assinado submetido",
                                              ip="")
                                    inv("usuarios.csv")  # FIX 2 — selectivo
                                    st.success("✅ Assinatura submetida! O RH será notificado.")
                                    time.sleep(1.5)
                                    st.rerun()
                        st.stop()
        except Exception as _e_ct:
            pass

    if eh_cliente:
        st.markdown(f"# {ICONS['dashboard']} Portal do Cliente")
        from mod_cliente import render_cliente_portal
        render_cliente_portal()

    elif tipo == 'Admin':
        # ── ALERTA BACKUP ─────────────────────────────────────────────
        _status_bkp, _ultima_bkp = _verificar_alerta_backup()
        if _status_bkp != 'ok':
            _ultima_str = _ultima_bkp.strftime('%d/%m/%Y %H:%M') \
                          if _ultima_bkp else 'Nunca realizado'
            if _status_bkp in ('critico', 'nunca'):
                st.error(
                    f"🚨 **BACKUP CRÍTICO** — Último: **{_ultima_str}** — "
                    f"Dados não protegidos!"
                )
            else:
                st.warning(f"⚠️ **Backup em atraso** — Último: **{_ultima_str}**")
            _col_b1, _col_b2 = st.columns(2)
            with _col_b1:
                if st.button("💾 Fazer Backup Agora",
                             key="alert_bkp_btn", type="primary",
                             use_container_width=True):
                    st.session_state['menu_selected'] = f"{ICONS['admin']} Admin"
                    st.session_state['_menu_locked']  = True
                    st.rerun()
            with _col_b2:
                if st.button("✅ Confirmar backup feito",
                             key="alert_bkp_confirm",
                             use_container_width=True):
                    _registar_backup(user_nome)
                    st.success("✅ Backup confirmado!")
                    time.sleep(0.8)
                    st.rerun()

        if f"{ICONS['admin']} Admin" in menu:
            from mod_admin import render_admin
            render_admin(*DATA)
        elif f"{ICONS['instrumentation']} Instrumentação" in menu:
            st.markdown(f"# {ICONS['instrumentation']} Instrumentação Industrial")
            from mod_instrumentacao import render_instrumentacao
            render_instrumentacao(*DATA)
        elif f"{ICONS['profile']} Perfil" in menu:
            st.markdown(f"# {ICONS['profile']} Perfil do Utilizador")
            from mod_perfil import render_perfil
            render_perfil(*DATA)
        elif f"{ICONS['dashboard']} Dashboard" in menu or menu == '':
            st.markdown(f"# {ICONS['dashboard']} Dashboard Geral")
            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("👥 Utilizadores", len(users))
            with c2: st.metric("🏭 Obras Ativas",
                len(obras_db[obras_db['Ativa']=='Ativa']) if not obras_db.empty else 0)
            with c3: st.metric("📋 Registos", len(registos_db) if not registos_db.empty else 0)
            with c4: st.metric("⚠️ Incidentes", len(incs_db) if not incs_db.empty else 0)
            st.divider()
            from mod_dashboard import render_dashboard
            render_dashboard(*DATA)
        else:
            from mod_admin import render_admin
            render_admin(*DATA)

    elif tipo == 'Secretariado':
        from mod_secretariado import render_secretariado
        render_secretariado(*DATA)

    elif tipo == 'Armazém':
        from mod_armazem import render_armazem
        req_fer_db2, req_mat_db2, req_epi_db2 = DATA[15], DATA[16], DATA[17]
        incs_db2 = DATA[6]
        render_armazem(req_fer_db2, req_mat_db2, req_epi_db2, incs_db2)

    else:
        if f"{ICONS['technician']} Obra" in menu:
            st.markdown(f"# {ICONS['technician']} Área Técnica")
            if tipo in ['Chefe de Equipa','Gestor'] or cargo in ['Chefe de Equipa','Encarregado']:
                from mod_chefe import render_chefe
                render_chefe(*DATA)
            else:
                from mod_tecnico import render_tecnico
                render_tecnico(*DATA)
        elif f"{ICONS['instrumentation']} Instrumentação" in menu:
            if tem_acesso_inst:
                st.markdown(f"# {ICONS['instrumentation']} Instrumentação Industrial")
                from mod_instrumentacao import render_instrumentacao
                render_instrumentacao(*DATA)
            else:
                st.warning("⚠️ Não tem acesso a este módulo.")
        elif f"{ICONS['profile']} Perfil" in menu:
            st.markdown(f"# {ICONS['profile']} Perfil do Utilizador")
            from mod_perfil import render_perfil
            render_perfil(*DATA)
        else:
            from mod_inicio import render_inicio
            render_inicio(*DATA)

st.markdown("""
<style>
.footer {
    position:fixed; bottom:60px; left:0; right:0;
    background:linear-gradient(135deg,#1E293B,#0F172A);
    padding:12px 20px; text-align:center;
    font-size:0.75rem; color:#64748B;
    border-top:1px solid rgba(255,255,255,0.1); z-index:9998;
}
@media (max-width:768px) { .footer { display:none; } }
</style>
<div class="footer">🎛️ GESTNOW v3.0 — Sistema de Gestão de Instrumentação Industrial</div>
""", unsafe_allow_html=True)

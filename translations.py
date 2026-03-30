import streamlit as st

TRANSLATIONS = {
    "app_title": {"pt": "GESTNOW - Gestão de Obra", "en": "GESTNOW - Site Management"},
    "login_title": {"pt": "Entrar no Sistema", "en": "System Login"},
    "user": {"pt": "Utilizador", "en": "User"},
    "password": {"pt": "Palavra-passe", "en": "Password"},
    "login_btn": {"pt": "Entrar →", "en": "Login →"},
    "logout": {"pt": "Terminar Sessão", "en": "Logout"},
    "dashboard": {"pt": "Dashboard", "en": "Dashboard"},
    "approvals": {"pt": "Aprovações", "en": "Approvals"},
    "staff": {"pt": "Pessoal", "en": "Staff"},
    "sites": {"pt": "Obras", "en": "Sites"},
    "points": {"pt": "Registo de Ponto", "en": "Time Sheets"},
    "comms": {"pt": "Comunicados", "en": "Announcements"},
    "tools": {"pt": "Ferramentas", "en": "Tools"},
    "materials": {"pt": "Materiais / EPI", "en": "Materials / PPE"},
    "profile": {"pt": "Meu Perfil", "en": "My Profile"},
    "safety": {"pt": "Segurança / HSE", "en": "Safety / HSE"},
    "instrumentation": {"pt": "Instrumentação", "en": "Instrumentation"},
    "success_save": {"pt": "Dados guardados com sucesso!", "en": "Data saved successfully!"},
    "error_auth": {"pt": "Credenciais incorretas", "en": "Invalid credentials"},
    "language": {"pt": "Idioma", "en": "Language"},
    "total_hours": {"pt": "Total Horas", "en": "Total Hours"},
    "active_sites": {"pt": "Obras Ativas", "en": "Active Sites"},
    "pending": {"pt": "Pendente", "en": "Pending"},
    "approved": {"pt": "Aprovado", "en": "Approved"},
    "save": {"pt": "Guardar", "en": "Save"},
    "cancel": {"pt": "Cancelar", "en": "Cancel"},
    "instrument_index": {"pt": "Índice de Instrumentos", "en": "Instrument Index"},
    "full_list": {"pt": "Lista Completa", "en": "Full List"},
    "upload_hookup": {"pt": "Upload P&ID IA", "en": "AI P&ID Upload"},
    "notifications": {"pt": "Notificações", "en": "Notifications"}
}

def get_text(key, lang="pt"):
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get("pt", key))
    return key

def get_language_options():
    return {"pt": "🇵🇹 Português", "en": "🇬🇧 English", "es": "🇪🇸 Español", "fr": "🇫🇷 Français"}

def init_language():
    if "language" not in st.session_state: st.session_state.language = "pt"

def set_language(lang): st.session_state.language = lang

def t(key):
    lang = st.session_state.get("language", "pt")
    return get_text(key, lang)

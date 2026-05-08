import streamlit as st

TRANSLATIONS = {
    "app_title":    {"pt": "GESTNOW - Gestão de Instrumentação", "en": "GESTNOW - Instrumentation Management", "es": "GESTNOW - Gestión de Instrumentación", "fr": "GESTNOW - Gestion d'Instrumentation"},
    "login_title":  {"pt": "Entrar no Sistema", "en": "System Login", "es": "Iniciar Sesión", "fr": "Connexion au Système"},
    "user":         {"pt": "Utilizador", "en": "User", "es": "Usuario", "fr": "Utilisateur"},
    "password":     {"pt": "Palavra-passe", "en": "Password", "es": "Contraseña", "fr": "Mot de passe"},
    "login_btn":    {"pt": "Entrar →", "en": "Login →", "es": "Entrar →", "fr": "Connexion →"},
    "logout":       {"pt": "Terminar Sessão", "en": "Logout", "es": "Cerrar Sesión", "fr": "Déconnexion"},
    "language":     {"pt": "Idioma", "en": "Language", "es": "Idioma", "fr": "Langue"},
    "save":         {"pt": "Guardar", "en": "Save", "es": "Guardar", "fr": "Enregistrer"},
    "cancel":       {"pt": "Cancelar", "en": "Cancel", "es": "Cancelar", "fr": "Annuler"},
    "error_auth":   {"pt": "Credenciais incorretas", "en": "Invalid credentials", "es": "Credenciales incorrectas", "fr": "Identifiants invalides"},
    "success_save": {"pt": "Dados guardados com sucesso!", "en": "Data saved successfully!", "es": "¡Datos guardados!", "fr": "Données enregistrées!"},
    "dashboard":    {"pt": "Dashboard", "en": "Dashboard", "es": "Panel", "fr": "Tableau de bord"},
    "total_hours":  {"pt": "Total Horas", "en": "Total Hours", "es": "Total Horas", "fr": "Total Heures"},
    "active_sites": {"pt": "Obras Ativas", "en": "Active Sites", "es": "Obras Activas", "fr": "Chantiers Actifs"},
    "pending":      {"pt": "Pendente", "en": "Pending", "es": "Pendiente", "fr": "En attente"},
    "approved":     {"pt": "Aprovado", "en": "Approved", "es": "Aprobado", "fr": "Approuvé"},
    "total_instruments": {"pt": "Total Instrumentos", "en": "Total Instruments", "es": "Total Instrumentos", "fr": "Total Instruments"},
    "material_ok":  {"pt": "Material OK", "en": "Material OK", "es": "Material OK", "fr": "Matériel OK"},
    "calibrated":   {"pt": "Calibrados", "en": "Calibrated", "es": "Calibrados", "fr": "Étalonnés"},
    "installed":    {"pt": "Instalados", "en": "Installed", "es": "Instalados", "fr": "Installés"},
    "handover_blocked": {"pt": "HANDOVER BLOQUEADO", "en": "HANDOVER BLOCKED", "es": "ENTREGA BLOQUEADA", "fr": "LIVRAISON BLOQUÉE"},
    "approvals":    {"pt": "Aprovações", "en": "Approvals", "es": "Aprobaciones", "fr": "Approbations"},
    "staff":        {"pt": "Pessoal", "en": "Staff", "es": "Personal", "fr": "Personnel"},
    "sites":        {"pt": "Obras", "en": "Sites", "es": "Obras", "fr": "Chantiers"},
    "billing":      {"pt": "Faturação", "en": "Billing", "es": "Facturación", "fr": "Facturation"},
    "hse":          {"pt": "Segurança / HSE", "en": "Safety / HSE", "es": "Seguridad / HSE", "fr": "Sécurité / HSE"},
    "points":       {"pt": "Registo de Ponto", "en": "Time Sheets", "es": "Registro de Tiempo", "fr": "Feuilles de Temps"},
    "comms":        {"pt": "Comunicados", "en": "Announcements", "es": "Comunicados", "fr": "Annonces"},
    "tools":        {"pt": "Ferramentas", "en": "Tools", "es": "Herramientas", "fr": "Outils"},
    "materials":    {"pt": "Materiais / EPI", "en": "Materials / PPE", "es": "Materiales / EPI", "fr": "Matériaux / EPI"},
    "profile":      {"pt": "Meu Perfil", "en": "My Profile", "es": "Mi Perfil", "fr": "Mon Profil"},
    "safety":       {"pt": "Segurança", "en": "Safety", "es": "Seguridad", "fr": "Sécurité"},
    "instrumentation":  {"pt": "Instrumentação", "en": "Instrumentation", "es": "Instrumentación", "fr": "Instrumentation"},
    "instrument_index": {"pt": "Índice de Instrumentos", "en": "Instrument Index", "es": "Índice de Instrumentos", "fr": "Index des Instruments"},
    "full_list":    {"pt": "Lista Completa", "en": "Full List", "es": "Lista Completa", "fr": "Liste Complète"},
    "upload_hookup": {"pt": "Upload P&ID IA", "en": "AI P&ID Upload", "es": "Subir P&ID IA", "fr": "Télécharger P&ID IA"},
    "calibration":  {"pt": "Calibração", "en": "Calibration", "es": "Calibración", "fr": "Étalonnage"},
    "installation": {"pt": "Instalação", "en": "Installation", "es": "Instalación", "fr": "Installation"},
    "handover":     {"pt": "Handover", "en": "Handover", "es": "Entrega", "fr": "Livraison"},
    "notifications": {"pt": "Notificações", "en": "Notifications", "es": "Notificaciones", "fr": "Notifications"},
    "alerts":       {"pt": "Alertas", "en": "Alerts", "es": "Alertas", "fr": "Alertes"},
    "no_notifications": {"pt": "Sem notificações pendentes", "en": "No pending notifications", "es": "Sin notificaciones pendientes", "fr": "Aucune notification en attente"},
    "voice_command": {"pt": "Comando de Voz", "en": "Voice Command", "es": "Comando de Voz", "fr": "Commande Vocale"},
    "voice_listening": {"pt": "🎤 Ouvindo... Fale agora", "en": "🎤 Listening... Speak now", "es": "🎤 Escuchando... Hable ahora", "fr": "🎤 Écoute... Parlez maintenant"},
    "voice_error":  {"pt": "❌ Erro no reconhecimento", "en": "❌ Recognition error", "es": "❌ Error de reconocimiento", "fr": "❌ Erreur de reconnaissance"},
    "voice_help":   {"pt": "Diga 'Ajuda' para ver comandos", "en": "Say 'Help' to see commands", "es": "Diga 'Ayuda' para ver comandos", "fr": "Dites 'Aide' pour voir les commandes"},
    "golden_rules": {"pt": "Regras de Ouro", "en": "Golden Rules", "es": "Reglas de Oro", "fr": "Règles d'Or"},
    "report_incident": {"pt": "Reportar Incidente", "en": "Report Incident", "es": "Reportar Incidente", "fr": "Signaler un Incident"},
    "safety_walk":  {"pt": "Safety Walk", "en": "Safety Walk", "es": "Safety Walk", "fr": "Safety Walk"},
    "status_pending":    {"pt": "Pendente",  "en": "Pending",   "es": "Pendiente",  "fr": "En attente"},
    "status_approved":   {"pt": "Aprovado",  "en": "Approved",  "es": "Aprobado",   "fr": "Approuvé"},
    "status_closed":     {"pt": "Fechado",   "en": "Closed",    "es": "Cerrado",    "fr": "Fermé"},
    "status_material_ok":{"pt": "Material OK","en": "Material OK","es": "Material OK","fr": "Matériel OK"},
    "status_calibrated": {"pt": "Calibrado", "en": "Calibrated","es": "Calibrado",  "fr": "Étalonné"},
    "status_installed":  {"pt": "Instalado", "en": "Installed", "es": "Instalado",  "fr": "Installé"},
    "status_completed":  {"pt": "Concluído", "en": "Completed", "es": "Completado", "fr": "Terminé"},
}

def get_text(key, lang="pt"):
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get("pt", key))
    return key

def get_language_options():
    return {
        "pt": "🇵🇹 Português",
        "en": "🇬🇧 English",
        "es": "🇪🇸 Español",
        "fr": "🇫🇷 Français"
    }

def init_language():
    if "language" not in st.session_state:
        st.session_state.language = "pt"

def set_language(lang):
    st.session_state.language = lang

def t(key):
    lang = st.session_state.get("language", "pt")
    return get_text(key, lang)

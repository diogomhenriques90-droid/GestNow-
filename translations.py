"""
GESTNOW v3 — translations.py
Sistema de tradução multilíngue para toda a aplicação
Idiomas: Português (PT), Inglês (EN), Espanhol (ES), Francês (FR)
"""

import streamlit as st

# Dicionário de traduções
TRANSLATIONS = {
    # =========================================================
    # GERAL / NAVEGAÇÃO
    # =========================================================
    "app_title": {
        "pt": "GESTNOW - Gestão de Instrumentação",
        "en": "GESTNOW - Instrumentation Management",
        "es": "GESTNOW - Gestión de Instrumentación",
        "fr": "GESTNOW - Gestion d'Instrumentation"
    },
    "dashboard": {
        "pt": "Dashboard",
        "en": "Dashboard",
        "es": "Panel",
        "fr": "Tableau de Bord"
    },
    "instrumentation": {
        "pt": "Instrumentação",
        "en": "Instrumentation",
        "es": "Instrumentación",
        "fr": "Instrumentation"
    },
    "obra_management": {
        "pt": "Gestão de Obra",
        "en": "Site Management",
        "es": "Gestión de Obra",
        "fr": "Gestion de Chantier"
    },
    "logout": {
        "pt": "Terminar Sessão",
        "en": "Logout",
        "es": "Cerrar Sesión",
        "fr": "Déconnexion"
    },
    "language": {
        "pt": "Idioma",
        "en": "Language",
        "es": "Idioma",
        "fr": "Langue"
    },
    "portuguese": {
        "pt": "Português",
        "en": "Portuguese",
        "es": "Portugués",
        "fr": "Portugais"
    },
    "english": {
        "pt": "Inglês",
        "en": "English",
        "es": "Inglés",
        "fr": "Anglais"
    },
    "spanish": {
        "pt": "Espanhol",
        "en": "Spanish",
        "es": "Español",
        "fr": "Espagnol"
    },
    "french": {
        "pt": "Francês",
        "en": "French",
        "es": "Francés",
        "fr": "Français"
    },
    
    # =========================================================
    # DASHBOARD / MÉTRICAS
    # =========================================================
    "total_instruments": {
        "pt": "Instrumentos",
        "en": "Instruments",
        "es": "Instrumentos",
        "fr": "Instruments"
    },
    "material_ok": {
        "pt": "Material OK",
        "en": "Material OK",
        "es": "Material OK",
        "fr": "Matériel OK"
    },
    "calibrated": {
        "pt": "Calibrados",
        "en": "Calibrated",
        "es": "Calibrados",
        "fr": "Étalonnés"
    },
    "installed": {
        "pt": "Instalados",
        "en": "Installed",
        "es": "Instalados",
        "fr": "Installés"
    },
    "pending": {
        "pt": "Pendente",
        "en": "Pending",
        "es": "Pendiente",
        "fr": "En attente"
    },
    "completed": {
        "pt": "Concluído",
        "en": "Completed",
        "es": "Completado",
        "fr": "Terminé"
    },
    "progress": {
        "pt": "Progresso",
        "en": "Progress",
        "es": "Progreso",
        "fr": "Progrès"
    },
    "punch_cat_a": {
        "pt": "Punch Cat.A",
        "en": "Punch Cat.A",
        "es": "Punch Cat.A",
        "fr": "Punch Cat.A"
    },
    
    # =========================================================
    # INSTRUMENT INDEX
    # =========================================================
    "instrument_index": {
        "pt": "Instrument Index",
        "en": "Instrument Index",
        "es": "Índice de Instrumentos",
        "fr": "Index des Instruments"
    },
    "extract_from_pid": {
        "pt": "Extrair de P&ID",
        "en": "Extract from P&ID",
        "es": "Extraer de P&ID",
        "fr": "Extraire de P&ID"
    },
    "add_manual": {
        "pt": "Adicionar Manual",
        "en": "Add Manual",
        "es": "Añadir Manual",
        "fr": "Ajouter Manuel"
    },
    "full_list": {
        "pt": "Lista Completa",
        "en": "Full List",
        "es": "Lista Completa",
        "fr": "Liste Complète"
    },
    "qr_labels": {
        "pt": "Etiquetas QR",
        "en": "QR Labels",
        "es": "Etiquetas QR",
        "fr": "Étiquettes QR"
    },
    "tag": {
        "pt": "Tag",
        "en": "Tag",
        "es": "Tag",
        "fr": "Tag"
    },
    "type": {
        "pt": "Tipo",
        "en": "Type",
        "es": "Tipo",
        "fr": "Type"
    },
    "description": {
        "pt": "Descrição",
        "en": "Description",
        "es": "Descripción",
        "fr": "Description"
    },
    "manufacturer": {
        "pt": "Fabricante",
        "en": "Manufacturer",
        "es": "Fabricante",
        "fr": "Fabricant"
    },
    "model": {
        "pt": "Modelo",
        "en": "Model",
        "es": "Modelo",
        "fr": "Modèle"
    },
    
    # =========================================================
    # HOOK-UPS & BOM
    # =========================================================
    "hookups_bom": {
        "pt": "Hook-Ups & BOM",
        "en": "Hook-Ups & BOM",
        "es": "Hook-Ups & BOM",
        "fr": "Hook-Ups & BOM"
    },
    "upload_hookup": {
        "pt": "Upload Hook-Up com IA",
        "en": "Upload Hook-Up with AI",
        "es": "Subir Hook-Up con IA",
        "fr": "Télécharger Hook-Up avec IA"
    },
    "manual_bom": {
        "pt": "BOM Manual",
        "en": "Manual BOM",
        "es": "BOM Manual",
        "fr": "BOM Manuel"
    },
    "library": {
        "pt": "Biblioteca",
        "en": "Library",
        "es": "Biblioteca",
        "fr": "Bibliothèque"
    },
    "quantity": {
        "pt": "Quantidade",
        "en": "Quantity",
        "es": "Cantidad",
        "fr": "Quantité"
    },
    "unit": {
        "pt": "Unidade",
        "en": "Unit",
        "es": "Unidad",
        "fr": "Unité"
    },
    
    # =========================================================
    # PACKING LIST
    # =========================================================
    "packing_list": {
        "pt": "Packing List",
        "en": "Packing List",
        "es": "Lista de Embalaje",
        "fr": "Liste de Colisage"
    },
    "import_register": {
        "pt": "Importar / Registar",
        "en": "Import / Register",
        "es": "Importar / Registrar",
        "fr": "Importer / Enregistrer"
    },
    "checkin": {
        "pt": "Check-in de Recepção",
        "en": "Receiving Check-in",
        "es": "Check-in de Recepción",
        "fr": "Contrôle de Réception"
    },
    "traffic_light": {
        "pt": "Semáforo por Instrumento",
        "en": "Traffic Light by Instrument",
        "es": "Semáforo por Instrumento",
        "fr": "Feu Tricolore par Instrument"
    },
    "received_ok": {
        "pt": "Recebido OK",
        "en": "Received OK",
        "es": "Recibido OK",
        "fr": "Reçu OK"
    },
    "missing": {
        "pt": "Em falta",
        "en": "Missing",
        "es": "Faltante",
        "fr": "Manquant"
    },
    
    # =========================================================
    # CALIBRATION (ITR-A)
    # =========================================================
    "calibration": {
        "pt": "Calibração ITR-A",
        "en": "Calibration ITR-A",
        "es": "Calibración ITR-A",
        "fr": "Étalonnage ITR-A"
    },
    "new_calibration": {
        "pt": "Nova Calibração",
        "en": "New Calibration",
        "es": "Nueva Calibración",
        "fr": "Nouvel Étalonnage"
    },
    "history": {
        "pt": "Histórico",
        "en": "History",
        "es": "Historial",
        "fr": "Historique"
    },
    "equipment_id": {
        "pt": "Identificação do Equipamento",
        "en": "Equipment Identification",
        "es": "Identificación del Equipo",
        "fr": "Identification de l'Équipement"
    },
    "range_min": {
        "pt": "Range Mín",
        "en": "Min Range",
        "es": "Rango Mín",
        "fr": "Plage Min"
    },
    "range_max": {
        "pt": "Range Máx",
        "en": "Max Range",
        "es": "Rango Máx",
        "fr": "Plage Max"
    },
    "test_rise": {
        "pt": "Teste de Subida",
        "en": "Rise Test",
        "es": "Prueba de Subida",
        "fr": "Test de Montée"
    },
    "test_fall": {
        "pt": "Teste de Descida",
        "en": "Fall Test",
        "es": "Prueba de Bajada",
        "fr": "Test de Descente"
    },
    "pass": {
        "pt": "APROVADO",
        "en": "PASS",
        "es": "APROBADO",
        "fr": "APPROUVÉ"
    },
    "fail": {
        "pt": "REPROVADO",
        "en": "FAIL",
        "es": "RECHAZADO",
        "fr": "ÉCHOUÉ"
    },
    
    # =========================================================
    # INSTALLATION (ITR-B)
    # =========================================================
    "installation": {
        "pt": "Instalação ITR-B",
        "en": "Installation ITR-B",
        "es": "Instalación ITR-B",
        "fr": "Installation ITR-B"
    },
    "mark_location": {
        "pt": "Marcar Localização",
        "en": "Mark Location",
        "es": "Marcar Ubicación",
        "fr": "Marquer l'Emplacement"
    },
    "register_installation": {
        "pt": "Registar Instalação",
        "en": "Register Installation",
        "es": "Registrar Instalación",
        "fr": "Enregistrer l'Installation"
    },
    "site_map": {
        "pt": "Mapa da Obra",
        "en": "Site Map",
        "es": "Mapa de la Obra",
        "fr": "Plan du Chantier"
    },
    "latitude": {
        "pt": "Latitude",
        "en": "Latitude",
        "es": "Latitud",
        "fr": "Latitude"
    },
    "longitude": {
        "pt": "Longitude",
        "en": "Longitude",
        "es": "Longitud",
        "fr": "Longitude"
    },
    "elevation": {
        "pt": "Elevação",
        "en": "Elevation",
        "es": "Elevación",
        "fr": "Élévation"
    },
    "photo": {
        "pt": "Foto",
        "en": "Photo",
        "es": "Foto",
        "fr": "Photo"
    },
    "reference_photo": {
        "pt": "Foto de Referência",
        "en": "Reference Photo",
        "es": "Foto de Referencia",
        "fr": "Photo de Référence"
    },
    
    # =========================================================
    # PUNCH LIST
    # =========================================================
    "punch_list": {
        "pt": "Punch List",
        "en": "Punch List",
        "es": "Lista de Pendientes",
        "fr": "Liste des Points à Corriger"
    },
    "new_item": {
        "pt": "Novo Item",
        "en": "New Item",
        "es": "Nuevo Ítem",
        "fr": "Nouvel Élément"
    },
    "category": {
        "pt": "Categoria",
        "en": "Category",
        "es": "Categoría",
        "fr": "Catégorie"
    },
    "responsible": {
        "pt": "Responsável",
        "en": "Responsible",
        "es": "Responsable",
        "fr": "Responsable"
    },
    "deadline": {
        "pt": "Prazo",
        "en": "Deadline",
        "es": "Plazo",
        "fr": "Délai"
    },
    
    # =========================================================
    # HANDOVER
    # =========================================================
    "handover": {
        "pt": "Handover Dossier",
        "en": "Handover Dossier",
        "es": "Dossier de Entrega",
        "fr": "Dossier de Remise"
    },
    "handover_blocked": {
        "pt": "HANDOVER BLOQUEADO",
        "en": "HANDOVER BLOCKED",
        "es": "ENTREGA BLOQUEADA",
        "fr": "REMISE BLOQUÉE"
    },
    "handover_unlocked": {
        "pt": "Handover desbloqueado",
        "en": "Handover unlocked",
        "es": "Entrega desbloqueada",
        "fr": "Remise débloquée"
    },
    
    # =========================================================
    # VOICE ASSISTANT
    # =========================================================
    "voice_assistant": {
        "pt": "Assistente por Voz",
        "en": "Voice Assistant",
        "es": "Asistente de Voz",
        "fr": "Assistant Vocal"
    },
    "speak_now": {
        "pt": "Clique e fale",
        "en": "Click and speak",
        "es": "Haga clic y hable",
        "fr": "Cliquez et parlez"
    },
    "listening": {
        "pt": "Ouvindo... Fale agora",
        "en": "Listening... Speak now",
        "es": "Escuchando... Hable ahora",
        "fr": "Écoute... Parlez maintenant"
    },
    "command_received": {
        "pt": "Comando recebido",
        "en": "Command received",
        "es": "Comando recibido",
        "fr": "Commande reçue"
    },
    "help_commands": {
        "pt": "Comandos disponíveis",
        "en": "Available commands",
        "es": "Comandos disponibles",
        "fr": "Commandes disponibles"
    },
    
    # =========================================================
    # MAPA / GOOGLE MAPS
    # =========================================================
    "google_maps": {
        "pt": "Google Maps",
        "en": "Google Maps",
        "es": "Google Maps",
        "fr": "Google Maps"
    },
    "navigate": {
        "pt": "Navegar",
        "en": "Navigate",
        "es": "Navegar",
        "fr": "Naviguer"
    },
    "route": {
        "pt": "Rota",
        "en": "Route",
        "es": "Ruta",
        "fr": "Itinéraire"
    },
    
    # =========================================================
    # RELATÓRIOS
    # =========================================================
    "reports": {
        "pt": "Relatórios",
        "en": "Reports",
        "es": "Informes",
        "fr": "Rapports"
    },
    "export_excel": {
        "pt": "Exportar Excel",
        "en": "Export Excel",
        "es": "Exportar Excel",
        "fr": "Exporter Excel"
    },
    "export_csv": {
        "pt": "Exportar CSV",
        "en": "Export CSV",
        "es": "Exportar CSV",
        "fr": "Exporter CSV"
    },
    "generate_pdf": {
        "pt": "Gerar PDF",
        "en": "Generate PDF",
        "es": "Generar PDF",
        "fr": "Générer PDF"
    },
    
    # =========================================================
    # NOTIFICAÇÕES
    # =========================================================
    "notifications": {
        "pt": "Notificações",
        "en": "Notifications",
        "es": "Notificaciones",
        "fr": "Notifications"
    },
    "alerts": {
        "pt": "Alertas",
        "en": "Alerts",
        "es": "Alertas",
        "fr": "Alertes"
    },
    
    # =========================================================
    # BOTÕES E AÇÕES
    # =========================================================
    "save": {
        "pt": "Guardar",
        "en": "Save",
        "es": "Guardar",
        "fr": "Enregistrer"
    },
    "cancel": {
        "pt": "Cancelar",
        "en": "Cancel",
        "es": "Cancelar",
        "fr": "Annuler"
    },
    "confirm": {
        "pt": "Confirmar",
        "en": "Confirm",
        "es": "Confirmar",
        "fr": "Confirmer"
    },
    "delete": {
        "pt": "Eliminar",
        "en": "Delete",
        "es": "Eliminar",
        "fr": "Supprimer"
    },
    "edit": {
        "pt": "Editar",
        "en": "Edit",
        "es": "Editar",
        "fr": "Modifier"
    },
    "search": {
        "pt": "Pesquisar",
        "en": "Search",
        "es": "Buscar",
        "fr": "Rechercher"
    },
    "filter": {
        "pt": "Filtrar",
        "en": "Filter",
        "es": "Filtrar",
        "fr": "Filtrer"
    },
    "refresh": {
        "pt": "Atualizar",
        "en": "Refresh",
        "es": "Actualizar",
        "fr": "Actualiser"
    },
    
    # =========================================================
    # MENSAGENS
    # =========================================================
    "success": {
        "pt": "Sucesso",
        "en": "Success",
        "es": "Éxito",
        "fr": "Succès"
    },
    "error": {
        "pt": "Erro",
        "en": "Error",
        "es": "Error",
        "fr": "Erreur"
    },
    "warning": {
        "pt": "Aviso",
        "en": "Warning",
        "es": "Advertencia",
        "fr": "Avertissement"
    },
    "info": {
        "pt": "Informação",
        "en": "Information",
        "es": "Información",
        "fr": "Information"
    },
    "loading": {
        "pt": "A carregar...",
        "en": "Loading...",
        "es": "Cargando...",
        "fr": "Chargement..."
    },
    "no_data": {
        "pt": "Sem dados",
        "en": "No data",
        "es": "Sin datos",
        "fr": "Aucune donnée"
    }
}


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def get_text(key, lang="pt"):
    """Retorna o texto traduzido para o idioma selecionado"""
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get("pt", key))
    return key


def get_language_options():
    """Retorna as opções de idioma disponíveis"""
    return {
        "pt": "🇵🇹 Português",
        "en": "🇬🇧 English",
        "es": "🇪🇸 Español",
        "fr": "🇫🇷 Français"
    }


def init_language():
    """Inicializa o idioma na sessão"""
    if "language" not in st.session_state:
        st.session_state.language = "pt"


def set_language(lang):
    """Define o idioma na sessão"""
    st.session_state.language = lang


def t(key):
    """Atalho para get_text usando o idioma da sessão"""
    lang = st.session_state.get("language", "pt")
    return get_text(key, lang)

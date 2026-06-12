import streamlit as st
import pandas as pd
import uuid, base64, hashlib, json, unicodedata, re
from datetime import datetime, date, timedelta
from io import BytesIO

from core import (
    save_db, inv, load_db, log_audit, criar_notificacao,
    hp, _gcs_read, _gcs_write_binary, _gcs_read_binary,
    _fill_contrato_template, ICONS, logger
)

# ── Tipos e cargos disponíveis ────────────────────────────────────────
TIPOS_USUARIO = ["Técnico","Instrumentista","Engenheiro","Chefe de Equipa",
                 "Secretariado","Armazém","Admin","Cliente"]
CARGOS_POR_TIPO = {
    "Técnico":        ["Técnico Eletricista","Técnico Mecânico","Técnico Automação",
                       "Técnico Instrumentação","Operador Especializado","Serralheiro","Outro"],
    "Instrumentista": ["Instrumentista","Técnico Instrumentista","Instrumentista Sénior"],
    "Engenheiro":     ["Engenheiro Eletrotécnico","Engenheiro Mecânico",
                       "Engenheiro Automação","Engenheiro Instrumentação",
                       "Engenheiro de Projeto"],
    "Chefe de Equipa":["Chefe de Equipa","Encarregado","Supervisor de Obra"],
    "Admin":          ["Administrador","Gestor RH","Gestor IT"],
    "Cliente":        ["Gestor de Projeto","Fiscal de Obra","Responsável Técnico"],
    "Secretariado": ["Secretária","Administrativo","Faturação","RH"],
    "Armazém":      ["Responsável de Armazém","Técnico de Armazém"],
}

# Campos do colaborador para exportação / visualização completa
CAMPOS_PERFIL = [
    ("Identificação",   ["Nome","NIF","NISS","CC","CC_Validade","DataNasc",
                         "Naturalidade","Estado_Civil","Nacionalidade"]),
    ("Contactos",       ["Telefone","Email"]),
    ("Morada",          ["Morada","Localidade","Concelho","Codigo_Postal"]),
    ("Emergência",      ["Nome_Emergencia","Contacto_Emergencia","Grau_Parentesco"]),
    ("Profissional",    ["Tipo","Cargo","PrecoHora","PrecoHoraStatus",
                         "Local_Obra","Cliente_Obra"]),
    ("Fardamento",      ["Tamanho_Camisola","Tamanho_Calca","Tamanho_Botas"]),
    ("Onboarding",      ["PDFs_Validados","PDFs_Validacao_Data",
                         "PrecoHoraData","Perfil_Completo","Perfil_Data",
                         "IBAN_Data_Upload"]),
    ("Contrato",        ["Contrato_Gerado","Contrato_Data","Contrato_Enviado",
                         "Contrato_Enviado_Data","Contrato_Assinado",
                         "Contrato_Assinatura_Data","Contrato_Validado_Admin",
                         "Contrato_Validado_Data"]),
]

# ── Constantes legais/fiscais para colaboradores_rh.csv ──────────────
ESTADO_CIVIL_OPTS    = ["Solteiro(a)","Casado(a)","União de Facto",
                        "Divorciado(a)","Viúvo(a)","Separado(a)"]
GENERO_OPTS          = ["Masculino","Feminino","Outro","Não especificado"]
MODALIDADE_HORARIO_OPTS = ["Tempo Inteiro","Tempo Parcial","Isenção de Horário",
                            "Trabalho por Turnos","Teletrabalho","Misto"]
TIPO_CONTRATO_OPTS   = ["A Termo Certo","A Termo Incerto","Sem Termo",
                        "Prestação de Serviços","Estágio Profissional","Outro"]
NIVEL_HABILITACOES_OPTS = [
    "Sem escolaridade","1º Ciclo (4ª classe)","2º Ciclo (6º ano)",
    "3º Ciclo (9º ano)","Ensino Secundário (12º ano)","Bacharelato",
    "Licenciatura","Mestrado","Doutoramento","Outro",
]

# Tabela 14 do Relatório Único — Níveis de Habilitação (gerada a partir de
# "Habilitações.xlsx"). NIVEL_HABILITACOES_OPTS é mantido acima apenas para
# backcompat de valores já gravados.
HABILITACOES_RU = {
    "14": "Técnico superior formação de professores e ciências da educação",
    "21": "Técnico Superior Profissional Artes",
    "22": "Técnico Superior Profissional Humanidades",
    "31": "Técnico Superior Profissional Ciências Sociais e do Comportamento",
    "32": "Técnico superior profissional informação e jornalismo",
    "34": "Técnico Superior Profissional Ciências Empresariais",
    "38": "Técnico Superior Profissional Direito",
    "42": "Técnico Superior Profissional Ciências da Vida",
    "44": "Técnico Superior Profissional Ciências Físicas",
    "46": "Técnico superior profissional matemática e estatística",
    "48": "Técnico Superior Profissional Informática",
    "52": "Técnico Superior Profissional Engenharia e Tecnicas Afins",
    "54": "Técnico Superior Profissional Indústrias Transformadoras",
    "58": "Técnico Superior Profissional Arquitectura e Construção",
    "62": "Técnico Superior Profissional Agricultura, Sivicultura e Pesca",
    "64": "Técnico Superior Profissional Ciências Veterinárias",
    "72": "Técnico Superior Profissional Saúde",
    "76": "Técnico Superior Profissional Serviços Sociais",
    "81": "Técnico Superior Profissional Serviços Pessoais",
    "84": "Técnico superior profissional serviços de transporte",
    "85": "Técnico Superior Profissional Protecção do Ambiente",
    "86": "Técnico Superior Profissional Serviços de Segurança",
    "99": "Técnico Superior Profissional Desconhecido ou Não Especificado",
    "111": "Não sabe ler nem escrever",
    "112": "Sabe ler e escrever",
    "211": "1º Ciclo do Ensino Básico",
    "212": "1º Ciclo Ensino Básico (I.P.)",
    "221": "2º Ciclo do Ensino Básico",
    "222": "2º Ciclo Ensino Básico (I.P.)",
    "231": "3º Ciclo do Ensino Básico",
    "232": "Ensino Téc.:Geral Comercial",
    "233": "3º Ciclo Ensino Básico (I.P.)",
    "234": "Escolas Profissionais-Nível II",
    "312": "Ensino Sec. Téc.Complementar",
    "313": "Ensino Sec. Téc.Profissional",
    "314": "Cursos Esc.Profiss.Nível III",
    "315": "Ensino Sec. (12 ou equiv.), Lic. Compl.",
    "316": "Ensino Sec.  c/cursos indole Profissional",
    "414": "Form.prof.form.educ.(Nível IV)",
    "421": "Artes (Nível IV)",
    "422": "Humanidades (Nível IV)",
    "431": "Ciênc.soc.comportam.(Nível IV)",
    "432": "Informação jornal. (Nível IV)",
    "434": "Ciênc. empresariais (Nível IV)",
    "438": "Direito (Nível IV)",
    "442": "Ciências da vida (Nível IV)",
    "444": "Ciências físicas (Nível IV)",
    "446": "Matemát. estatísti. (Nível IV)",
    "448": "Informática (Nível IV)",
    "452": "Eng. técnicas afins (Nível IV)",
    "454": "Indúst. transf. (Nível IV)",
    "458": "Arquit. construção (Nível IV)",
    "462": "Agric.,silvic.pescas(Nível IV)",
    "464": "Ciênc. veterinárias (Nível IV)",
    "472": "Saúde (Nível IV)",
    "476": "Serviços sociais (Nível IV)",
    "481": "Serviços pessoais (Nível IV)",
    "484": "Serviços transporte (Nível IV)",
    "485": "Protecção ambiente (Nível IV)",
    "486": "Serviços segurança (Nível IV)",
    "499": "Não especificado (Nível IV)",
    "514": "Form.prof.form.c.educ.(Bac.)",
    "521": "Artes (Bac.)",
    "522": "Humanidades (Bac.)",
    "531": "Ciênc. soc. comportam. (Bac.)",
    "532": "Informação jornalismo (Bac.)",
    "534": "Ciências empresariais (Bac.)",
    "538": "Direito (Bac.)",
    "542": "Ciências da vida (Bac.)",
    "544": "Ciências físicas (Bac.)",
    "546": "Matemática estatística (Bac.)",
    "548": "Informática (Bac.)",
    "552": "Eng. e técnicas afins (bac.)",
    "554": "Indúst. transformadoras (Bac.)",
    "558": "Arquitect. construção (Bac.)",
    "562": "Agric., silvic. pescas (Bac.)",
    "564": "Ciências veterinárias (Bac.)",
    "572": "Saúde (Bac.)",
    "576": "Serviços sociais (Bac.)",
    "581": "Serviços pessoais (Bac.)",
    "584": "Serviços de transporte (Bac.)",
    "585": "Protecção do ambiente (Bac.)",
    "586": "Serviços de segurança (Bac.)",
    "599": "Não especificado (Bac.)",
    "614": "Form.prof.form.c.educ.(Lic.)",
    "621": "Artes (Lic.)",
    "622": "Humanidades (Lic.)",
    "631": "Ciênc. soc. comportam. (Lic.)",
    "632": "Informação jornalismo (Lic.)",
    "634": "Ciências empresariais (Lic.)",
    "638": "Direito (Lic.)",
    "642": "Ciências da vida (Lic.)",
    "644": "Ciências físicas (Lic.)",
    "646": "Matemática estatística (Lic.)",
    "648": "Informática (Lic.)",
    "652": "Eng. e técnicas afins (Lic.)",
    "654": "Indúst. transformadoras (Lic.)",
    "658": "Arquitect. construção (Lic.)",
    "662": "Agric,silvic.e pescas(Lic.)",
    "664": "Ciências veterinárias (Lic.)",
    "672": "Saúde (Lic.)",
    "676": "Serviços sociais (Lic.)",
    "681": "Serviços pessoais (Lic.)",
    "684": "Serviços de transporte (Lic.)",
    "685": "Protecção do ambiente (Lic.)",
    "686": "Serviços de segurança (Lic.)",
    "699": "Não especificado (Lic.)",
    "714": "Form.prof.form.c.educ.(Mest.)",
    "721": "Artes (Mest.)",
    "722": "Humanidades (Mest.)",
    "731": "Ciênc. soc. comportam. (Mest.)",
    "732": "Informação jornalismo (Mest.)",
    "734": "Ciências empresariais (Mest.)",
    "738": "Direito (Mest.)",
    "742": "Ciências da vida (Mest.)",
    "744": "Ciências físicas (Mest.)",
    "746": "Matemática estatística (Mest.)",
    "748": "Informática (Mest.)",
    "752": "Eng. e técnicas afins (Mest.)",
    "754": "Indúst. transform.(Mest.)",
    "758": "Arquitect. construção (Mest.)",
    "762": "Agric.,silvic.e pescas(Mest.)",
    "764": "Ciências veterinárias (Mest.)",
    "772": "Saúde (Mest.)",
    "776": "Serviços sociais (Mest.)",
    "781": "Serviços pessoais (Mest.)",
    "784": "Serviços de transporte (Mest.)",
    "785": "Protecção do ambiente (Mest.)",
    "786": "Serviços de segurança (Mest.)",
    "799": "Não especificado (Mest.)",
    "814": "Form.prof.form.c.educ.(Dout.)",
    "821": "Artes (Dout.)",
    "822": "Humanidades (Dout.)",
    "831": "Ciênc. soc. comportam. (Dout.)",
    "832": "Informação jornalismo (Dout.)",
    "834": "Ciências empresariais (Dout.)",
    "838": "Direito (Dout.)",
    "842": "Ciências da vida (Dout.)",
    "844": "Ciências físicas (Dout.)",
    "846": "Matemática estatística (Dout.)",
    "848": "Informática (Dout.)",
    "852": "Eng. e técnicas afins (Dout.)",
    "854": "Indúst. transform. (Dout.)",
    "858": "Arquitect. construção (Dout.)",
    "862": "Agric.,silvic.e pescas(Dout.)",
    "864": "Ciências veterinárias (Dout.)",
    "872": "Saúde (Dout.)",
    "876": "Serviços sociais (Dout.)",
    "881": "Serviços pessoais (Dout.)",
    "884": "Serviços de transporte (Dout.)",
    "885": "Protecção do ambiente (Dout.)",
    "886": "Serviços de segurança (Dout.)",
    "899": "Não especificado (Dout.)",
}
HABILITACOES_RU_OPTS = [""] + [f"{_k} - {_v}" for _k, _v in HABILITACOES_RU.items()]

SITUACAO_PROFISSIONAL_OPTS = [
    "Quadro Permanente","Contrato a Termo Certo","Contrato a Termo Incerto",
    "Prestador de Serviços","Estagiário","Outro",
]
FORMA_PAGAMENTO_OPTS = ["Transferência Bancária","Numerário","Cheque","Outro"]
IRCT_OPTS            = ["IRCT 25989 – CCT Empresas Electrotécnicas",
                        "IRCT 5/2015 – CCT Metalúrgico","Outro","Não aplicável"]

# ── Constantes adicionais (Parte 1 — Fase 2 RH) ───────────────────────
ESTADO_FISCAL_OPTS = [
    "Não Casado", "Casado - Único Titular", "Casado - Dois Titulares",
    "Não Casado - Deficiente", "Casado - Único Titular Deficiente",
    "Casado - Dois Titulares Deficiente",
]
MEDIDA_FISCAL_OPTS = [
    "Nenhuma", "IRS Jovem", "Programa Regressar",
    "Residente Não Habitual (RNH)", "Outra",
]
ENQUADRAMENTO_SS_OPTS = [
    "Regime Geral - Trabalhador por Conta de Outrem",
    "Membro de Órgão Estatutário", "Pensionista",
    "Isento de Contribuições", "Trabalhador Independente", "Outro",
]
MODALIDADE_CONTRATO_OPTS = [
    "Contrato Sem Termo", "Contrato a Termo Certo", "Contrato a Termo Incerto",
    "Contrato de Trabalho Temporário", "Contrato de Muito Curta Duração",
    "Contrato de Trabalho a Tempo Parcial", "Comissão de Serviço",
    "Outra Situação",
]
PRESTACAO_TRABALHO_OPTS = ["Tempo Inteiro", "Tempo Parcial"]
MOTIVO_CONTRATO_OPTS = [
    "Substituição Direta ou Indireta de Trabalhador",
    "Atividade Sazonal",
    "Acréscimo Excecional de Atividade",
    "Execução de Tarefa Ocasional ou Serviço Determinado Precisamente Definido e Não Duradouro",
    "Execução de Obra, Projeto ou Outra Atividade Definida e Temporária",
    "Lançamento de Nova Atividade",
    "Contratação de Trabalhador à Procura de Primeiro Emprego",
    "Contratação de Desempregado de Longa Duração",
    "Outro",
]
MOTIVO_ENTRADA_OPTS = [
    "Novo Posto de Trabalho", "Substituição de Trabalhador",
    "Necessidades Temporárias", "Transferência", "Outro",
]
MOTIVO_SAIDA_OPTS = [
    "Caducidade do Contrato a Termo",
    "Despedimento por Iniciativa do Empregador",
    "Despedimento Coletivo",
    "Resolução pelo Trabalhador",
    "Revogação por Mútuo Acordo",
    "Reforma",
    "Morte do Trabalhador",
    "Denúncia pelo Trabalhador",
    "Outro",
]
SUB_ALIM_MODO_OPTS = [
    "Não Aplicável", "Subsídio em Dinheiro", "Cartão Refeição",
    "Refeitório/Cantina",
]
SUB_ALIM_ENTIDADE_OPTS = [
    "Empresa", "Cartão Edenred", "Cartão Sodexo", "Cartão Up Refeição", "Outro",
]
NIVEL_PROF_IGDT_OPTS = [
    "Quadro superior", "Quadro médio",
    "Encarregado, contramestre, mestre e chefe de equipa",
    "Profissional altamente qualificado", "Profissional qualificado",
    "Profissional semiqualificado", "Profissional não qualificado",
    "Praticante e aprendiz",
]
ORIGEM_ENS_SUP_OPTS = [
    "Não Aplicável", "Universitário Público", "Universitário Privado",
    "Politécnico Público", "Politécnico Privado",
]
TIPO_DOC_ID_OPTS = [
    "Cartão de Cidadão", "Passaporte", "Título de Residência Temporária",
    "Título de Residência Permanente", "Cartão Registo Cidadão UE/EEE",
]
NIVEL_QUALIF_OPTS = [
    "Quadro superior", "Quadro médio",
    "Encarregado, contramestre, mestre e chefe de equipa",
    "Profissional altamente qualificado", "Profissional qualificado",
    "Profissional semi-qualificado especializado",
    "Profissional não qualificado indiferenciado",
    "Estagiário, praticante e aprendiz",
]
TIPO_HORARIO_OPTS = [
    "Normal Fixo", "Horário Flexível", "Trabalho por Turnos",
    "Banco de Horas", "Adaptabilidade", "Isenção de Horário",
]
DURACAO_TT_OPTS = [
    "1 - Adaptabilidade por regulamentação colectiva (RU:10)",
    "2 - Adaptabilidade individual (RU:11)",
    "3 - Banco de horas por regulamentação colectiva (RU:12)",
    "4 - Banco de horas individual (RU:13)",
    "5 - Banco de horas grupal (RU:14)",
    "6 - Horário concentrado (RU:15)",
    "7 - Não aplicável",
]
REGIME_REFORMA_OPTS = [
    "1 - Segurança Social", "2 - Caixa Geral de Aposentações",
    "3 - Outro Regime de Proteção Social", "4 - Não Aplicável",
]
ORG_TT_OPTS = [
    "1 - Trabalho diurno", "2 - Trabalho noturno",
    "3 - Trabalho por turnos", "4 - Trabalho misto",
]
MODO_REMUN_OPTS = [
    "Mensal", "Quinzenal", "Semanal", "Diário", "Por Tarefa/Output", "Outro",
]
CARTA_CAT_OPTS = [
    "A1", "A2", "A", "B1", "B", "BE", "C1", "C1E", "C", "CE",
    "D1", "D1E", "D", "DE",
]

CATEGORIAS_CCT_25989 = {
    "02069": "AJUDANTES DE FOGUEIRO",
    "02070": "ANALISTA DE INFORMÁTICA ASSISTENTE",
    "02996": "ANALISTA DE INFORMÁTICA ESTAGIÁRIO",
    "02071": "ANALISTA DE INFORMÁTICA PRINCIPAL",
    "02072": "ANALISTA DE INFORMÁTICA PROFISSIONAL",
    "11285": "ASSISTENTE ADMINISTRATIVO DE 1.ª",
    "11286": "ASSISTENTE ADMINISTRATIVO DE 2.ª",
    "11287": "ASSISTENTE ADMINISTRATIVO DE 3.ª",
    "43991": "ASSISTENTE ADMINISTRATIVO ESTAGIÁRIO ATÉ 2 ANOS",
    "23130": "ASSISTENTE ADMINISTRATIVO ESTAGIÁRIO DO 2.º ANO",
    "03236": "AUXILIAR DE ENFERMAGEM",
    "00159": "CHEFE DE EQUIPA",
    "00081": "CHEFE DE SECÇÃO",
    "00080": "CHEFE DE SERVIÇOS",
    "00411": "CHEFE DE VENDAS",
    "30112": "CHEFE DE VIGILÂNCIA",
    "01427": "CONTABILISTA",
    "00527": "CONTÍNUO",
    "02176": "COORDENADOR DE OPERADORES ESPECIALIZADOS",
    "00532": "COZINHEIRO",
    "38497": "EMPREGADO DE REFEITÓRIO/CAFETARIA",
    "00412": "EMPREGADO DE SERVIÇOS EXTERNOS",
    "00023": "ENCARREGADO",
    "02097": "ENCARREGADO DE LIMPEZA",
    "02098": "ENCARREGADO DE REFEITÓRIO OU CANTINA",
    "00184": "ENCARREGADO GERAL",
    "00542": "ENFERMEIRO",
    "44140": "ENGENHEIRO I-A / ESPECIALISTA I-A",
    "44141": "ENGENHEIRO I-B / ESPECIALISTA I-B",
    "44142": "ENGENHEIRO II / ESPECIALISTA II",
    "44143": "ENGENHEIRO III / ESPECIALISTA III",
    "44310": "ENGENHEIRO IV / ESPECIALISTA IV",
    "44145": "ENGENHEIRO V / ESPECIALISTA V",
    "44146": "ENGENHEIRO VI / ESPECIALISTA VI",
    "02021": "ESTAGIÁRIO RECEPCIONISTA",
    "02103": "EXPOSITOR DECORADOR",
    "02108": "GUARDA OU VIGILANTE",
    "00328": "INSPECTOR DE VENDAS",
    "00478": "MOTORISTA DE LIGEIROS",
    "00479": "MOTORISTA DE PESADOS",
    "35679": "OPERADOR DE INFORMÁTICA PRINCIPAL",
    "35678": "OPERADOR DE INFORMÁTICA PROFISSIONAL",
    "02150": "OPERADOR ESPECIALIZADO DE 1.ª",
    "02151": "OPERADOR ESPECIALIZADO DE 2.ª",
    "02152": "OPERADOR ESPECIALIZADO DE 3.ª",
    "43990": "OPERADOR ESPECIALIZADO SÉNIOR",
    "38498": "OPERADOR INFORMÁTICO ESTAGIÁRIO",
    "00490": "PORTEIRO",
    "02155": "PROFISSIONAL QUALIFICADO OFICIAL",
    "31323": "PROFISSIONAL QUALIFICADO PRATICANTE ATÉ 2 ANOS",
    "02158": "PROFISSIONAL QUALIFICADO PRÉ-OFICIAL 1.º E 2.º ANOS",
    "03106": "PROGRAMADOR DE INFORMÁTICA ASSISTENTE",
    "35680": "PROGRAMADOR DE INFORMÁTICA PRINCIPAL",
    "03108": "PROGRAMADOR DE INFORMÁTICA PROFISSIONAL",
    "38499": "PROGRAMADOR INFORMÁTICO ESTAGIÁRIO",
    "02163": "PROJECTISTA",
    "00387": "PROMOTOR DE VENDAS",
    "00388": "PROSPECTOR DE VENDAS",
    "02032": "RECEPCIONISTA DE 1.ª",
    "02033": "RECEPCIONISTA DE 2.ª",
    "95989": "RESIDUAL (inclui o ignorado)",
    "25963": "SECRETÁRIO(A)",
    "00044": "SERVENTE",
    "35677": "SUPERVISOR DE LOGÍSTICA",
    "11288": "TÉCNICO ADMINISTRATIVO",
    "02182": "TÉCNICO DE SERVIÇO SOCIAL",
    "43989": "TÉCNICO OPERACIONAL 1 E 2 ANOS",
    "43988": "TÉCNICO OPERACIONAL 3 E 4 ANOS",
    "43987": "TÉCNICO OPERACIONAL 5 E 6 ANOS",
    "43986": "TÉCNICO OPERACIONAL MAIS DE 6 ANOS",
    "43992": "TÉCNICO OPERACIONAL PRATICANTE ATÉ 2 ANOS",
    "40876": "TÉCNICO OPERACIONAL PRINCIPAL",
    "00503": "VENDEDOR",
}

PROFISSOES_CPP_CPS = {
    "74121": "Electricista de instalações",
    "74122": "Electricista de manutenção",
    "74123": "Electricista de redes e subestações",
    "74124": "Electromecânico",
    "74131": "Técnico de instalações eléctricas industriais",
    "74141": "Técnico de instrumentação e controlo",
    "74142": "Técnico de automação industrial",
    "74143": "Técnico de telecomunicações industriais",
    "21411": "Engenheiro Electrotécnico",
    "21412": "Engenheiro de Automação",
    "21413": "Engenheiro de Instrumentação",
    "31211": "Técnico de electrónica",
    "31221": "Técnico de electromecânica",
    "33411": "Técnico Administrativo",
    "43110": "Escriturário",
    "72111": "Serralheiro mecânico",
    "72121": "Soldador",
    "91110": "Indiferenciado / Servente",
}

# Colunas completas do colaboradores_rh.csv
COLS_RH = [
    "ID","Nome","NIF","NISS","Tipo","Cargo",
    "Salario_Base","Data_Inicio","Estado_Civil","N_Dependentes",
    "Banco_IBAN","Contrato","Ativo",
    "Genero","DataNasc","Naturalidade","Nacionalidade","Pais_Residencia",
    "Email","Morada","Localidade","Codigo_Postal",
    "CC","CC_Validade","Passaporte","Passaporte_Validade",
    "IRS_Escalao","IRS_Percentagem","Titular_Unico","Taxa_Retencao_IRS",
    "Isencao_IRS","Artigo_IRS",
    "Tipo_Contrato","Modalidade_Horario","Horas_Semana",
    "Contrato_Inicio","Contrato_Fim","Contrato_Indeterminado",
    "Periodo_Experimental","Periodo_Experimental_Fim",
    "Local_Trabalho","Funcao_Contratual",
    "Subsidio_Alimentacao","Subsidio_Ferias","Subsidio_Natal",
    "Premio_Producao","Outros_Complementos","Forma_Pagamento",
    "IBAN_Validado","SWIFT_BIC",
    "Nivel_Habilitacoes","Situacao_Profissional","Profissao_CPP",
    "Categoria_CCT","IRCT_Aplicavel","Vinculo_Empresa",
    "Reducao_Horario","Data_Ultima_Promocao","Antiguidade_Anos",
    "Nivel_Remuneratorio","Grau_Deficiencia","Deficiencia_Tipo",
    "Seg_Social_Cartao","Cartao_Prof_Num","Cartao_Prof_Validade",
    "Alvara_Num","Alvara_Validade",
    # Campos dinâmicos do Eticadata (Parte 0c)
    "Eticadata_ID","Data_Admissao","Tipo_Doc_ID","Nivel_Qualificacao",
    "Tipo_Horario","Duracao_Tempo_Trabalho","Modo_Remuneracao","Pensionista",
    "Banco_Nome","Banco_Empresa_Pagamento","Num_Utente","Servico_Financas",
    "Regime_Reforma","Organizacao_Tempo_Trabalho","IRCT_Codigo","IRCT_Descricao",
    # Novos campos (Parte 1 — Fase 2 RH)
    "Estado_Fiscal","N_Dependentes_Deficiencia","Medida_Fiscal","Enquadramento_SS",
    "Modalidade_Contrato","Prestacao_Trabalho","Motivo_Contrato","Motivo_Entrada",
    "Motivo_Saida","Data_Saida","Sub_Alimentacao_Modo","Sub_Alimentacao_Entidade",
    "Num_Cartao_Refeicao","Seguradora_AT","Apolice_AT","Nivel_Profissional_IGDT",
    "Origem_Ensino_Superior","Carta_Conducao_Num","Carta_Conducao_Validade",
    "Carta_Conducao_Categoria","Regulamento_Assinado","Regulamento_Data",
]

# Campos que o importador Eticadata só preenche se estiverem vazios em
# colaboradores_rh.csv — preserva correções manuais feitas pelo admin
# (Nacionalidade/Estado_Civil/Naturalidade) e evita sobrepor o NIF já
# partilhado com usuarios.csv.
CAMPOS_PROTEGIDOS_RH = ["Nacionalidade", "Estado_Civil", "Naturalidade", "NIF"]

# Mapeamento Eticadata → COLS_RH (nome coluna Eticadata: nome campo GestNow)
ETICADATA_MAP = {
    "Nome": "Nome",
    "NIF": "NIF",
    "N.º Segurança Social": "NISS",
    "Nº Segurança Social": "NISS",
    "BI/CC": "CC",
    "N.º Cartão Cidadão": "CC",
    "Validade CC": "CC_Validade",
    "Validade BI/CC": "CC_Validade",
    "Data Nascimento": "DataNasc",
    "Data Nasc.": "DataNasc",
    "Sexo": "Genero",
    "Estado Civil": "Estado_Civil",
    "Nº Dependentes": "N_Dependentes",
    "N.º Dependentes": "N_Dependentes",
    "IBAN": "Banco_IBAN",
    "Categoria": "Categoria_CCT",
    "Remuneração Base": "Salario_Base",
    "Salário Base": "Salario_Base",
    "Rem. Base": "Salario_Base",
    "Data Admissão": "Contrato_Inicio",
    "Data Início": "Contrato_Inicio",
    "Data Cessação": "Contrato_Fim",
    "Data Fim": "Contrato_Fim",
    "Tipo Contrato": "Tipo_Contrato",
    "Habilitações": "Nivel_Habilitacoes",
    "Profissão CPP": "Profissao_CPP",
    "CPP": "Profissao_CPP",
    "Local Trabalho": "Local_Trabalho",
    "Função": "Funcao_Contratual",
}

# Mapas de conversão de valores Eticadata → GestNow
_ETICA_GENERO   = {"M": "Masculino", "F": "Feminino",
                   "1": "Masculino", "2": "Feminino"}
_ETICA_EST_CIVIL = {
    "1": "Solteiro(a)", "2": "Casado(a)", "3": "Divorciado(a)",
    "4": "Viúvo(a)",    "5": "União de Facto", "6": "Separado(a)",
}
_ETICA_HABILITACOES = {
    "1": "Sem escolaridade",
    "2": "1º Ciclo (4ª classe)",
    "3": "2º Ciclo (6º ano)",
    "4": "3º Ciclo (9º ano)",
    "5": "Ensino Secundário (12º ano)",
    "6": "Bacharelato",
    "7": "Licenciatura",
    "8": "Mestrado",
    "9": "Doutoramento",
}
_ETICA_TIPO_CONTRATO = {
    "1": "Sem Termo",
    "2": "A Termo Certo",
    "3": "A Termo Incerto",
    "4": "Prestação de Serviços",
    "5": "Estágio Profissional",
}

def _load_users_fresh():
    import time
    for t in range(3):
        try:
            buf = _gcs_read("usuarios.csv")
            if buf:
                df = pd.read_csv(buf, dtype=str, on_bad_lines='skip',
                                 encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].str.strip()
                return df.fillna("")
            time.sleep(0.3)
        except:
            if t == 2: return pd.DataFrame()
            time.sleep(0.3)
    return pd.DataFrame()


def _load_rh_fresh() -> pd.DataFrame:
    """Lê colaboradores_rh.csv directamente do GCS, sem cache."""
    import time
    for attempt in range(3):
        try:
            buf = _gcs_read("colaboradores_rh.csv")
            if buf:
                df = pd.read_csv(buf, dtype=str, on_bad_lines='skip',
                                 encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].str.strip()
                for c in COLS_RH:
                    if c not in df.columns:
                        df[c] = ""
                return df.fillna("")
            time.sleep(0.3)
        except Exception:
            if attempt == 2:
                return pd.DataFrame(columns=COLS_RH)
            time.sleep(0.3)
    return pd.DataFrame(columns=COLS_RH)


def _sync_rh_csv(nome: str, updates: dict) -> bool:
    """Aplica `updates` ao registo de `nome` em colaboradores_rh.csv.
    Cria linha nova se o colaborador ainda não existir.
    Devolve True/False consoante o resultado de save_db."""
    rh = _load_rh_fresh()
    mask = (rh['Nome'] == nome) if 'Nome' in rh.columns and not rh.empty else pd.Series([], dtype=bool)
    if mask.any():
        for k, v in updates.items():
            rh.loc[mask, k] = v
    else:
        novo = {c: "" for c in COLS_RH}
        novo['Nome'] = nome
        novo.update(updates)
        rh = pd.concat([rh, pd.DataFrame([novo])], ignore_index=True)
    ok = save_db(rh, "colaboradores_rh.csv")
    if ok:
        inv("colaboradores_rh.csv")
    return ok


def _exportar_excel_colaborador(user_row: pd.Series) -> bytes:
    """Gera um Excel com todos os dados do colaborador."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        linhas = []
        for secao, campos in CAMPOS_PERFIL:
            linhas.append({"Secção": f"── {secao} ──", "Campo": "", "Valor": ""})
            for campo in campos:
                valor = user_row.get(campo, '')
                # Não exportar dados binários
                if campo.endswith('_b64') or campo.endswith('_b64'):
                    valor = "(ficheiro binário)" if valor else ""
                linhas.append({"Secção": secao, "Campo": campo, "Valor": valor})
        df_export = pd.DataFrame(linhas)
        df_export.to_excel(writer, index=False, sheet_name="Dados Colaborador")

        # Formatar
        ws = writer.sheets["Dados Colaborador"]
        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 28
        ws.column_dimensions['C'].width = 45

    output.seek(0)
    return output.getvalue()


def render_admin_rh(*args):
    (users, obras_db, frentes_db, registos_db, faturas_db, docs_db, incs_db,
     sw_db, obs_db, equip_db, diags_db, diags_u_db, folhas_db, comuns_db,
     comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db,
     inst_acessos_db) = args

    admin_nome = st.session_state.get('user', 'Admin')

    st.markdown("""
    <style>
    [data-baseweb="select"] [role="option"] {
        color: #111827 !important;
        background: #FFFFFF !important;
    }
    [data-baseweb="menu"] {
        background: #FFFFFF !important;
    }
    [data-baseweb="menu"] li {
        color: #111827 !important;
    }
    .stDownloadButton > button {
        color: #111827 !important;
        background: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("# 👥 Recursos Humanos")

    # ── Painel de alertas de validade ─────────────────────────────────
    _today = date.today()
    _rh_alert = _load_rh_fresh()

    _VALIDADE_COLS = [
        ("CC_Validade",          "CC"),
        ("Passaporte_Validade",  "Passaporte"),
        ("Cartao_Prof_Validade", "Carta Prof."),
        ("Alvara_Validade",      "Alvará"),
        ("Carta_Conducao_Validade", "Carta de Condução"),
    ]
    _CAMPOS_OBG = ["NIF","NISS","CC","CC_Validade","Banco_IBAN","Tipo_Contrato",
                   "Estado_Fiscal","Enquadramento_SS","Categoria_CCT"]

    _n_exp, _n_prox, _n_ct, _n_inc, _n_reg = 0, 0, 0, 0, 0
    _det_exp, _det_prox, _det_ct, _det_inc, _det_reg = [], [], [], [], []

    def _parse_date(s):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return None

    if not _rh_alert.empty:
        for _, _r in _rh_alert.iterrows():
            _nm = _r.get('Nome', '')
            for _col, _lbl in _VALIDADE_COLS:
                _v = _parse_date(_r.get(_col, ''))
                if _v:
                    if _v < _today:
                        _n_exp += 1
                        _det_exp.append(f"{_nm} — {_lbl} expirado em {_r.get(_col,'')}")
                    elif _v <= _today + timedelta(days=60):
                        _n_prox += 1
                        _det_prox.append(f"{_nm} — {_lbl} expira em {_r.get(_col,'')}")
            _fim = _parse_date(_r.get('Contrato_Fim', ''))
            if _fim and _r.get('Contrato_Indeterminado', '') != 'Sim':
                _days = (_fim - _today).days
                if _days <= 90:
                    _n_ct += 1
                    _det_ct.append(f"{_nm} — contrato termina em {_r.get('Contrato_Fim','')} ({_days}d)")
            _falta = [c for c in _CAMPOS_OBG if not _r.get(c, '')]
            if _falta:
                _n_inc += 1
                _det_inc.append(f"{_nm} — em falta: {', '.join(_falta)}")
            if _r.get('Regulamento_Assinado', '') != 'Sim':
                _n_reg += 1
                _det_reg.append(f"{_nm} — regulamento interno por assinar")

    if _n_exp + _n_prox + _n_ct + _n_inc + _n_reg > 0:
        _ca1, _ca2, _ca3, _ca4, _ca5 = st.columns(5)
        _ca1.metric("🔴 Expirados",   _n_exp)
        _ca2.metric("🟡 A expirar",   _n_prox)
        _ca3.metric("🟠 Contratos",   _n_ct)
        _ca4.metric("⚪ Incompletos", _n_inc)
        _ca5.metric("⚪ Regulamento", _n_reg)
        with st.expander("📋 Ver detalhes dos alertas"):
            if _det_exp:
                st.markdown("**🔴 Documentos Expirados**")
                for _d in _det_exp: st.markdown(f"- {_d}")
            if _det_prox:
                st.markdown("**🟡 A Expirar nos próximos 60 dias**")
                for _d in _det_prox: st.markdown(f"- {_d}")
            if _det_ct:
                st.markdown("**🟠 Contratos a Terminar (≤ 90 dias)**")
                for _d in _det_ct: st.markdown(f"- {_d}")
            if _det_inc:
                st.markdown("**⚪ Fichas Incompletas**")
                for _d in _det_inc: st.markdown(f"- {_d}")
            if _det_reg:
                st.markdown("**⚪ Regulamento Interno por Assinar**")
                for _d in _det_reg: st.markdown(f"- {_d}")
        st.markdown("---")

    (tab_lista, tab_gestao, tab_dados_legais, tab_eticadata,
     tab_contrato, tab_template, tab_formacoes) = st.tabs([
        "👥 Colaboradores",
        "📋 Gestão Individual",
        "📋 Dados Legais",
        "📥 Importar Eticadata",
        "📄 Contratos",
        "⚙️ Templates & Config",
        "🎓 Formações",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 — LISTA DE COLABORADORES + CRIAR
    # ════════════════════════════════════════════════════════════════
    with tab_lista:

        col_titulo, col_btn = st.columns([4, 1])
        with col_titulo:
            st.markdown("### 👥 Todos os Colaboradores")
        with col_btn:
            if st.button("➕ Novo", key="btn_novo_colab",
                          type="primary", use_container_width=True):
                st.session_state['show_criar_colab'] = True
                st.rerun()

        users_live = _load_users_fresh()

        # ── Formulário de criação ─────────────────────────────────
        if st.session_state.get('show_criar_colab', False):
            st.markdown("---")
            st.markdown("#### ➕ Criar Novo Colaborador")

            with st.form("form_criar_colab"):
                st.markdown("**Dados obrigatórios**")
                c1, c2 = st.columns(2)
                with c1:
                    novo_nome = st.text_input("Nome Completo *",
                        key="nc_nome", placeholder="Nome completo")
                    novo_tipo = st.selectbox("Tipo de Acesso *",
    TIPOS_USUARIO, key="rh_nc_tipo")
                with c2:
                    novo_tel  = st.text_input("Contacto *",
                        key="nc_tel", placeholder="9XXXXXXXX")
                    novo_pwd  = st.text_input("Password *",
                        key="nc_pwd", type="password",
                        placeholder="Mínimo 4 caracteres")

                # Cargo dinâmico baseado no tipo
                cargos_disp = CARGOS_POR_TIPO.get(novo_tipo, ["Outro"])
                novo_cargo  = st.selectbox("Cargo / Função *",
                    cargos_disp, key="rh_nc_cargo") 

                st.markdown("**Dados da Obra** *(obrigatório para contrato)*")
                c3, c4 = st.columns(2)
                with c3:
                    novo_local  = st.text_input("Local da Obra *",
                        key="nc_local",
                        placeholder="Ex: Refinaria de Sines")
                with c4:
                    novo_cliente = st.text_input("Cliente *",
                        key="nc_cliente",
                        placeholder="Ex: GALP Energia")

                st.markdown("**Dados opcionais**")
                c5, c6 = st.columns(2)
                with c5:
                    novo_nif    = st.text_input("NIF (opcional na criação)",
                        key="nc_nif")
                    novo_preco  = st.number_input("Preço Hora (€)",
                        min_value=0.0, value=15.0, step=0.5,
                        key="nc_preco")
                with c6:
                    novo_email  = st.text_input("Email",
                        key="nc_email",
                        placeholder="colaborador@email.com")

                c_sub, c_can = st.columns(2)
                with c_sub:
                    submitted = st.form_submit_button(
                        "💾 Criar Colaborador",
                        use_container_width=True, type="primary"
                    )
                with c_can:
                    cancelar = st.form_submit_button(
                        "✕ Cancelar", use_container_width=True
                    )

            if cancelar:
                st.session_state['show_criar_colab'] = False
                st.rerun()

            if submitted:
                erros = []
                if not novo_nome.strip():   erros.append("Nome Completo")
                if not novo_tel.strip():    erros.append("Contacto")
                if not novo_pwd.strip() or len(novo_pwd.strip()) < 4:
                    erros.append("Password (mínimo 4 caracteres)")
                if not novo_local.strip():  erros.append("Local da Obra")
                if not novo_cliente.strip():erros.append("Cliente")

                if erros:
                    st.error(f"❌ Campos obrigatórios em falta: {', '.join(erros)}")
                else:
                    # Verificar nome duplicado
                    if not users_live.empty and \
                       novo_nome.strip() in users_live['Nome'].values:
                        st.error(f"❌ Já existe um colaborador com o nome '{novo_nome.strip()}'")
                    else:
                        novo_id  = str(uuid.uuid4())[:8].upper()
                        pwd_hash = hp(novo_pwd.strip())

                        novo_row = {
                            "ID": novo_id,
                            "Nome": novo_nome.strip(),
                            "Tipo": novo_tipo,
                            "Cargo": novo_cargo,
                            "Contacto": novo_tel.strip(),
                            "Telefone": novo_tel.strip(),
                            "Password": pwd_hash,
                            "NIF": novo_nif.strip(),
                            "Email": novo_email.strip(),
                            "PrecoHora": str(novo_preco),
                            "PrecoHoraStatus": "",
                            "Local_Obra": novo_local.strip(),
                            "Cliente_Obra": novo_cliente.strip(),
                            "PDFs_Validados": "Não",
                            "Perfil_Completo": "",
                            "Contrato_Gerado": "",
                            "Data_Criacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        }

                        nova_df = pd.DataFrame([novo_row])
                        updated = pd.concat(
                            [users_live, nova_df], ignore_index=True
                        ) if not users_live.empty else nova_df

                        save_db(updated, "usuarios.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        log_audit(usuario=admin_nome,
                                  acao="CRIAR_COLABORADOR",
                                  tabela="usuarios.csv",
                                  registro_id=novo_id,
                                  detalhes=f"Criado: {novo_nome.strip()} "
                                           f"({novo_tipo} / {novo_cargo})",
                                  ip="")

                        st.success(f"✅ Colaborador **{novo_nome.strip()}** criado com sucesso!")
                        st.session_state['show_criar_colab'] = False
                        inv("usuarios.csv")
                        st.rerun()

        # ── Tabela de colaboradores ───────────────────────────────
        if not users_live.empty:
            st.markdown(f"**{len(users_live)} colaborador(es)**")

            # Filtros
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_tipo = st.selectbox("Filtrar por tipo",
                    ["Todos"] + TIPOS_USUARIO, key="rh_filtro_tipo")
            with col_f2:
                filtro_nome = st.text_input("Pesquisar nome",
                    key="rh_filtro_nome", placeholder="Nome...")

            df_show = users_live.copy()
            if filtro_tipo != "Todos":
                df_show = df_show[df_show['Tipo'] == filtro_tipo]
            if filtro_nome:
                df_show = df_show[
                    df_show['Nome'].str.contains(filtro_nome, case=False, na=False)
                ]

            for _, row in df_show.iterrows():
                nome_c    = row.get('Nome','')
                tipo_c    = row.get('Tipo','')
                cargo_c   = row.get('Cargo','')
                estado_pdf = "✅" if row.get('PDFs_Validados','') == 'Sim' else "⏳"
                estado_pfx = "✅" if row.get('Perfil_Completo','') == 'Sim' else "⏳"
                estado_iban= "✅" if row.get('IBAN_Comprovativo_b64','') else "⏳"
                estado_ct  = "✅" if row.get('Contrato_Validado_Admin','') == 'Sim' \
                             else "🔵" if row.get('Contrato_Assinado','') == 'Sim' \
                             else "📄" if row.get('Contrato_Gerado','') == 'Sim' \
                             else "⬜"

                col_info, col_sel = st.columns([5, 1])
                with col_info:
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin-bottom:6px;'>"
                        f"<b style='color:#F1F5F9;'>{nome_c}</b> "
                        f"<span style='color:#64748B;font-size:0.8rem;'>"
                        f"· {tipo_c} · {cargo_c}</span><br>"
                        f"<span style='font-size:0.75rem;color:#94A3B8;'>"
                        f"PDFs {estado_pdf} &nbsp; Perfil {estado_pfx} &nbsp; "
                        f"IBAN {estado_iban} &nbsp; Contrato {estado_ct}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_sel:
                    if st.button("📋", key=f"sel_{nome_c}",
                                  use_container_width=True,
                                  help="Gerir colaborador"):
                        st.session_state['rh_colaborador_sel'] = nome_c
                        st.rerun()
        else:
            st.info("Sem colaboradores registados.")

    # ════════════════════════════════════════════════════════════════
    # TAB 2 — GESTÃO INDIVIDUAL
    # ════════════════════════════════════════════════════════════════
    with tab_gestao:
        users_live2 = _load_users_fresh()

        if users_live2.empty:
            st.info("Sem colaboradores.")
            return

        # Seletor
        nomes = users_live2['Nome'].tolist()
        sel_default = 0
        colab_sel   = st.session_state.get('rh_colaborador_sel', '')
        if colab_sel in nomes:
            sel_default = nomes.index(colab_sel)

        nome_sel = st.selectbox("Selecionar Colaborador",
            nomes, index=sel_default, key="rh_gestao_sel")
        st.session_state['rh_colaborador_sel'] = nome_sel

        match = users_live2[users_live2['Nome'] == nome_sel]
        if match.empty:
            st.warning("Colaborador não encontrado.")
            return
        row = match.iloc[0]

        # ── Cabeçalho do colaborador ──────────────────────────────
        st.markdown(
            f"<div style='background:#1E293B;border-radius:14px;"
            f"padding:16px;margin-bottom:16px;border:1px solid #334155;'>"
            f"<p style='color:#F1F5F9;font-size:1.2rem;font-weight:900;margin:0;'>"
            f"{nome_sel}</p>"
            f"<p style='color:#64748B;font-size:0.85rem;margin:3px 0 0;'>"
            f"{row.get('Tipo','')} · {row.get('Cargo','')} · "
            f"{row.get('Local_Obra','')} → {row.get('Cliente_Obra','')}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

        # ── Exportar Excel ────────────────────────────────────────
        excel_bytes = _exportar_excel_colaborador(row)
        st.download_button(
            "📥 Exportar dados em Excel",
            data=excel_bytes,
            file_name=f"colaborador_{nome_sel.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_export_excel"
        )

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        # ── Dados editáveis por secções (Gestão Individual) ───────
        _slug_gi = hashlib.md5(nome_sel.encode()).hexdigest()[:8]

        def _vg(campo, default=""):
            return row.get(campo, default)

        def _save_gi(updates: dict) -> bool:
            u_gi  = _load_users_fresh()
            mk_gi = u_gi['Nome'] == nome_sel
            if not mk_gi.any():
                return False
            for _k, _vv in updates.items():
                u_gi.loc[mk_gi, _k] = _vv
            ok = save_db(u_gi, "usuarios.csv")
            if ok:
                inv("usuarios.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                log_audit(usuario=st.session_state.get("user","admin"),
                          acao="ATUALIZAR_GESTAO_INDIVIDUAL",
                          tabela="usuarios.csv",
                          registro_id=nome_sel,
                          detalhes=f"Campos: {', '.join(updates.keys())}")
            return ok

        # ── 1. Identificação ───────────────────────────────────────
        with st.expander("👤 Identificação", expanded=True):
            with st.form(f"gi_form_ident_{_slug_gi}"):
                st.text_input("Nome", value=nome_sel, disabled=True,
                    key=f"gi_nome_{_slug_gi}",
                    help="Para alterar o nome contacte o developer.")
                _gc1, _gc2 = st.columns(2)
                with _gc1:
                    _gi_tel   = st.text_input("Contacto",
                        value=_vg("Telefone"), key=f"gi_tel_{_slug_gi}")
                    _gi_email = st.text_input("Email",
                        value=_vg("Email"), key=f"gi_email_{_slug_gi}")
                with _gc2:
                    _gi_datanasc = st.text_input("Data Nascimento (DD/MM/AAAA)",
                        value=_vg("DataNasc"), key=f"gi_datanasc_{_slug_gi}")
                if st.form_submit_button("💾 Guardar Identificação",
                                         use_container_width=True, type="primary"):
                    if _save_gi({"Telefone": _gi_tel, "Email": _gi_email,
                                  "DataNasc": _gi_datanasc}):
                        st.success("✅ Identificação guardada.")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao guardar — verifica ligação ao GCS")

        # ── 2. Morada ───────────────────────────────────────────────
        with st.expander("📍 Morada"):
            with st.form(f"gi_form_morada_{_slug_gi}"):
                _gc1, _gc2 = st.columns(2)
                with _gc1:
                    _gi_morada = st.text_input("Morada",
                        value=_vg("Morada"), key=f"gi_morada_{_slug_gi}")
                    _gi_localidade = st.text_input("Localidade",
                        value=_vg("Localidade"), key=f"gi_localidade_{_slug_gi}")
                with _gc2:
                    _gi_concelho = st.text_input("Concelho",
                        value=_vg("Concelho"), key=f"gi_concelho_{_slug_gi}")
                    _gi_cp = st.text_input("Código Postal",
                        value=_vg("Codigo_Postal"), key=f"gi_cp_{_slug_gi}")
                if st.form_submit_button("💾 Guardar Morada",
                                         use_container_width=True, type="primary"):
                    if _save_gi({"Morada": _gi_morada, "Localidade": _gi_localidade,
                                  "Concelho": _gi_concelho, "Codigo_Postal": _gi_cp}):
                        st.success("✅ Morada guardada.")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao guardar — verifica ligação ao GCS")

        # ── 3. Documentos ───────────────────────────────────────────
        with st.expander("🪪 Documentos"):
            with st.form(f"gi_form_docs_{_slug_gi}"):
                _gc1, _gc2 = st.columns(2)
                with _gc1:
                    _gi_cc = st.text_input("Cartão de Cidadão",
                        value=_vg("CC"), key=f"gi_cc_{_slug_gi}")
                    _gi_ccval = st.text_input("Validade CC (DD/MM/AAAA)",
                        value=_vg("CC_Validade"), key=f"gi_ccval_{_slug_gi}")
                with _gc2:
                    _gi_niss = st.text_input("NISS",
                        value=_vg("NISS"), key=f"gi_niss_{_slug_gi}")
                    _gi_nif = st.text_input("NIF",
                        value=_vg("NIF"), key=f"gi_nif_{_slug_gi}")
                if st.form_submit_button("💾 Guardar Documentos",
                                         use_container_width=True, type="primary"):
                    if _save_gi({"CC": _gi_cc, "CC_Validade": _gi_ccval,
                                  "NISS": _gi_niss, "NIF": _gi_nif}):
                        st.success("✅ Documentos guardados.")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao guardar — verifica ligação ao GCS")

        # ── 4. Bancários ────────────────────────────────────────────
        with st.expander("🏦 Bancários"):
            with st.form(f"gi_form_banco_{_slug_gi}"):
                _gi_iban = st.text_input("IBAN",
                    value=_vg("Banco_IBAN"), key=f"gi_iban_{_slug_gi}")
                if st.form_submit_button("💾 Guardar Dados Bancários",
                                         use_container_width=True, type="primary"):
                    if _save_gi({"Banco_IBAN": _gi_iban}):
                        st.success("✅ Dados bancários guardados.")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao guardar — verifica ligação ao GCS")

        # ── 5. Emergência ───────────────────────────────────────────
        with st.expander("🆘 Emergência"):
            with st.form(f"gi_form_emerg_{_slug_gi}"):
                _gc1, _gc2, _gc3 = st.columns(3)
                with _gc1:
                    _gi_nome_em = st.text_input("Nome Contacto Emergência",
                        value=_vg("Nome_Emergencia"), key=f"gi_nomeem_{_slug_gi}")
                with _gc2:
                    _gi_tel_em = st.text_input("Telefone Emergência",
                        value=_vg("Contacto_Emergencia"), key=f"gi_telem_{_slug_gi}")
                with _gc3:
                    _gi_grau_em = st.text_input("Grau de Parentesco",
                        value=_vg("Grau_Parentesco"), key=f"gi_grauem_{_slug_gi}")
                if st.form_submit_button("💾 Guardar Emergência",
                                         use_container_width=True, type="primary"):
                    if _save_gi({"Nome_Emergencia": _gi_nome_em,
                                  "Contacto_Emergencia": _gi_tel_em,
                                  "Grau_Parentesco": _gi_grau_em}):
                        st.success("✅ Dados de emergência guardados.")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao guardar — verifica ligação ao GCS")

        # ── 6. Profissional ─────────────────────────────────────────
        with st.expander("💼 Profissional"):
            with st.form(f"gi_form_prof_{_slug_gi}"):
                _gc1, _gc2 = st.columns(2)
                with _gc1:
                    _gi_preco  = st.text_input("Preço Hora (€)",
                        value=_vg("PrecoHora"), key=f"gi_preco_{_slug_gi}")
                    _gi_local  = st.text_input("Local de Obra",
                        value=_vg("Local_Obra"), key=f"gi_local_{_slug_gi}")
                    _gi_cliente= st.text_input("Cliente",
                        value=_vg("Cliente_Obra"), key=f"gi_cliente_{_slug_gi}")
                with _gc2:
                    _gi_camisola = st.text_input("Tamanho Camisola",
                        value=_vg("Tamanho_Camisola"), key=f"gi_camisola_{_slug_gi}")
                    _gi_calca = st.text_input("Tamanho Calça",
                        value=_vg("Tamanho_Calca"), key=f"gi_calca_{_slug_gi}")
                    _gi_botas = st.text_input("Tamanho Botas",
                        value=_vg("Tamanho_Botas"), key=f"gi_botas_{_slug_gi}")

                st.markdown("**Contrato**")
                _gc3, _gc4 = st.columns(2)
                with _gc3:
                    _gi_ct_ger = st.selectbox("Contrato Gerado", ["","Sim","Não"],
                        index=["","Sim","Não"].index(_vg("Contrato_Gerado"))
                              if _vg("Contrato_Gerado") in ["","Sim","Não"] else 0,
                        key=f"gi_ctger_{_slug_gi}")
                    _gi_ct_ger_data = st.text_input("Data Geração (DD/MM/AAAA)",
                        value=_vg("Contrato_Data"), key=f"gi_ctgerdata_{_slug_gi}")
                    _gi_ct_env = st.selectbox("Contrato Enviado", ["","Sim","Não"],
                        index=["","Sim","Não"].index(_vg("Contrato_Enviado"))
                              if _vg("Contrato_Enviado") in ["","Sim","Não"] else 0,
                        key=f"gi_ctenv_{_slug_gi}")
                    _gi_ct_env_data = st.text_input("Data Envio (DD/MM/AAAA)",
                        value=_vg("Contrato_Enviado_Data"), key=f"gi_ctenvdata_{_slug_gi}")
                with _gc4:
                    _gi_ct_assin = st.selectbox("Contrato Assinado", ["","Sim","Não"],
                        index=["","Sim","Não"].index(_vg("Contrato_Assinado"))
                              if _vg("Contrato_Assinado") in ["","Sim","Não"] else 0,
                        key=f"gi_ctassin_{_slug_gi}")
                    _gi_ct_assin_data = st.text_input("Data Assinatura (DD/MM/AAAA)",
                        value=_vg("Contrato_Assinatura_Data"), key=f"gi_ctassindata_{_slug_gi}")
                    _gi_ct_valid = st.selectbox("Contrato Validado (Admin)", ["","Sim","Não"],
                        index=["","Sim","Não"].index(_vg("Contrato_Validado_Admin"))
                              if _vg("Contrato_Validado_Admin") in ["","Sim","Não"] else 0,
                        key=f"gi_ctvalid_{_slug_gi}")
                    _gi_ct_valid_data = st.text_input("Data Validação (DD/MM/AAAA)",
                        value=_vg("Contrato_Validado_Data"), key=f"gi_ctvaliddata_{_slug_gi}")

                if st.form_submit_button("💾 Guardar Profissional",
                                         use_container_width=True, type="primary"):
                    if _save_gi({
                        "PrecoHora": _gi_preco, "Local_Obra": _gi_local,
                        "Cliente_Obra": _gi_cliente,
                        "Tamanho_Camisola": _gi_camisola, "Tamanho_Calca": _gi_calca,
                        "Tamanho_Botas": _gi_botas,
                        "Contrato_Gerado": _gi_ct_ger, "Contrato_Data": _gi_ct_ger_data,
                        "Contrato_Enviado": _gi_ct_env, "Contrato_Enviado_Data": _gi_ct_env_data,
                        "Contrato_Assinado": _gi_ct_assin, "Contrato_Assinatura_Data": _gi_ct_assin_data,
                        "Contrato_Validado_Admin": _gi_ct_valid, "Contrato_Validado_Data": _gi_ct_valid_data,
                    }):
                        st.success("✅ Dados profissionais guardados.")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao guardar — verifica ligação ao GCS")

        # ── Estado do perfil (só leitura) ─────────────────────────
        with st.expander("ℹ️ Estado do Perfil (só leitura)"):
            _onboarding_campos = next(
                (campos for secao, campos in CAMPOS_PERFIL if secao == "Onboarding"), []
            )
            c_left, c_right = st.columns(2)
            for i, campo in enumerate(_onboarding_campos):
                valor = row.get(campo, '')
                if campo.endswith('_b64'):
                    valor = "✅ Ficheiro presente" if valor else "❌ Não submetido"
                elif not valor:
                    valor = "—"
                col_use = c_left if i % 2 == 0 else c_right
                with col_use:
                    st.markdown(
                        f"<p style='color:#94A3B8;font-size:0.72rem;"
                        f"margin:0;text-transform:uppercase;'>{campo}</p>"
                        f"<p style='color:#F1F5F9;font-size:0.9rem;"
                        f"font-weight:600;margin:0 0 10px;'>{valor}</p>",
                        unsafe_allow_html=True
                    )

        # ── Download Comprovativo IBAN ────────────────────────────
        st.markdown("---")
        st.markdown("#### 🏦 Comprovativo IBAN")
        iban_b64 = row.get('IBAN_Comprovativo_b64', '')
        iban_data = row.get('IBAN_Data_Upload', '')
        if iban_b64:
            st.success(f"✅ Comprovativo submetido em {iban_data}")
            try:
                iban_bytes = base64.b64decode(iban_b64)
                st.download_button(
                    "📥 Descarregar Comprovativo IBAN",
                    data=iban_bytes,
                    file_name=f"iban_{nome_sel.replace(' ','_')}.pdf",
                    mime="application/octet-stream",
                    key="btn_dl_iban"
                )
            except:
                st.error("Erro ao processar o ficheiro IBAN.")
        else:
            st.warning("⏳ Colaborador ainda não submeteu o comprovativo bancário.")

        # ── Bloquear/Desbloquear campos ───────────────────────────
        st.markdown("---")
        st.markdown("#### 🔒 Campos Bloqueados")
        try:
            campos_bl = json.loads(row.get('Campos_Bloqueados', '[]'))
        except:
            campos_bl = []

        todos_bloqueáveis = ["NIF","CC","NISS","Morada","Localidade",
                             "Banco_IBAN","Email","Telefone"]
        novos_bl = st.multiselect(
            "Selecionar campos que o colaborador NÃO pode editar:",
            todos_bloqueáveis, default=campos_bl,
            key="rh_campos_bl"
        )
        if st.button("💾 Guardar Bloqueios",
                      key="btn_guardar_bloqueios"):
            u_fresh = _load_users_fresh()
            mask    = u_fresh['Nome'] == nome_sel
            if mask.any():
                u_fresh.loc[mask, 'Campos_Bloqueados'] = json.dumps(novos_bl)
                save_db(u_fresh, "usuarios.csv")
                inv("usuarios.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                st.success("✅ Campos bloqueados atualizados.")
                st.rerun()

        # ── Alterar Função e Password ─────────────────────────────
        st.markdown("---")
        st.markdown("#### ⚙️ Alterar Função / Password")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            tipos_opcoes = ["Técnico", "Chefe de Equipa", "Admin",
                            "Gestor", "Secretariado"]
            tipo_atual   = row.get("Tipo", "Técnico")
            idx_tipo     = tipos_opcoes.index(tipo_atual)                            if tipo_atual in tipos_opcoes else 0
            novo_tipo = st.selectbox("👤 Função (Tipo)",
                tipos_opcoes, index=idx_tipo, key="rh_novo_tipo")

        with col_f2:
            cargos_opcoes = ["Técnico", "Instrumentista", "Eletricista",
                             "Mecânico", "Chefe de Equipa", "Encarregado",
                             "Engenheiro", "QA/QC", "Admin", "Outro"]
            cargo_atual   = row.get("Cargo", "")
            idx_cargo     = cargos_opcoes.index(cargo_atual)                             if cargo_atual in cargos_opcoes else 0
            novo_cargo = st.selectbox("🏷️ Cargo",
                cargos_opcoes, index=idx_cargo, key="rh_novo_cargo")

        if st.button("💾 Guardar Função/Cargo",
                     key="btn_guardar_funcao", type="primary"):
            u_fn = _load_users_fresh()
            mk_fn = u_fn["Nome"] == nome_sel
            if mk_fn.any():
                u_fn.loc[mk_fn, "Tipo"]  = novo_tipo
                u_fn.loc[mk_fn, "Cargo"] = novo_cargo
                save_db(u_fn, "usuarios.csv")
                inv("usuarios.csv")
                from core import _cached_load_all
                _cached_load_all.clear()
                log_audit(usuario=st.session_state.get("user","admin"),
                          acao="ALTERAR_FUNCAO",
                          tabela="usuarios.csv",
                          registro_id=nome_sel,
                          detalhes=f"Tipo={novo_tipo}, Cargo={novo_cargo}")
                st.success(f"✅ Função actualizada: {novo_tipo} / {novo_cargo}")
                st.rerun()

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        with st.expander("🔐 Redefinir Password"):
            nova_pwd_admin = st.text_input(
                "Nova Password *", type="password", key="rh_nova_pwd_admin",
                placeholder="Mínimo 4 caracteres")
            conf_pwd_admin = st.text_input(
                "Confirmar Password *", type="password", key="rh_conf_pwd_admin")
            if st.button("🔐 Redefinir Password", key="btn_redef_pwd",
                         type="primary"):
                if not nova_pwd_admin.strip():
                    st.error("⚠️ Introduz uma nova password.")
                elif len(nova_pwd_admin.strip()) < 4:
                    st.error("⚠️ Mínimo 4 caracteres.")
                elif nova_pwd_admin != conf_pwd_admin:
                    st.error("⚠️ As passwords não coincidem.")
                else:
                    u_pw = _load_users_fresh()
                    mk_pw = u_pw["Nome"] == nome_sel
                    if mk_pw.any():
                        u_pw.loc[mk_pw, "Password"] = hp(nova_pwd_admin.strip())
                        save_db(u_pw, "usuarios.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        log_audit(usuario=st.session_state.get("user","admin"),
                                  acao="REDEFINIR_PASSWORD",
                                  tabela="usuarios.csv",
                                  registro_id=nome_sel,
                                  detalhes="Password redefinida pelo Admin")
                        st.success(f"✅ Password de {nome_sel} redefinida.")
                        st.rerun()

        # ── Remover ou Lista Negra ────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🚫 Remover Colaborador")

        st.markdown(
            "<div style='background:rgba(239,68,68,0.08);border-radius:10px;"
            "padding:12px 16px;border-left:3px solid #EF4444;margin-bottom:12px;'>"
            "<p style='color:#FCA5A5;font-size:0.82rem;margin:0;'>"
            "⚠️ <b>Atenção:</b> Estas acções são permanentes ou têm impacto "
            "no acesso do colaborador à plataforma.</p></div>",
            unsafe_allow_html=True
        )

        col_rm1, col_rm2 = st.columns(2)

        with col_rm1:
            st.markdown(
                "<p style='color:#F1F5F9;font-weight:700;margin:0 0 6px;'>"
                "🗑️ Remover Permanentemente</p>"
                "<p style='color:#64748B;font-size:0.78rem;'>"
                "Apaga o colaborador de forma definitiva. "
                "Registos de horas são mantidos.</p>",
                unsafe_allow_html=True)
            confirmar_rm = st.text_input(
                f"Escreve '{nome_sel}' para confirmar",
                key="rh_confirm_rm", placeholder="Nome completo")
            if st.button("🗑️ Remover Definitivamente",
                         key="btn_remover_def"):
                if confirmar_rm.strip() != nome_sel:
                    st.error("⚠️ Nome não coincide. Operação cancelada.")
                else:
                    u_rm = _load_users_fresh()
                    _row_rm = u_rm[u_rm["Nome"] == nome_sel]
                    _nif_rm = re.sub(
                        r'\D', '', str(_row_rm.iloc[0].get("NIF", ""))
                    ) if not _row_rm.empty else ""
                    u_rm = u_rm[u_rm["Nome"] != nome_sel]
                    save_db(u_rm, "usuarios.csv")
                    inv("usuarios.csv")

                    # Desactivar (não eliminar) o registo em colaboradores_rh.csv
                    # — mantém histórico para mod_fat_rh.py e rastreabilidade ISO.
                    # Match por NIF (mais fiável que o Nome, que pode divergir
                    # entre nome legal completo e nome curto), com fallback
                    # para Nome quando o NIF não está preenchido/encontrado.
                    rh_rm = _load_rh_fresh()
                    mask_rm = pd.Series([], dtype=bool)
                    if not rh_rm.empty:
                        if _nif_rm and 'NIF' in rh_rm.columns:
                            mask_rm = rh_rm['NIF'].apply(
                                lambda v: re.sub(r'\D', '', str(v))
                            ) == _nif_rm
                        if not mask_rm.any():
                            mask_rm = rh_rm["Nome"] == nome_sel
                    if mask_rm.any():
                        rh_rm.loc[mask_rm, "Ativo"] = "Não"
                        save_db(rh_rm, "colaboradores_rh.csv")
                        inv("colaboradores_rh.csv")

                    from core import _cached_load_all
                    _cached_load_all.clear()
                    log_audit(usuario=st.session_state.get("user","admin"),
                              acao="REMOVER_COLABORADOR",
                              tabela="usuarios.csv",
                              registro_id=nome_sel,
                              detalhes="Removido permanentemente pelo Admin")
                    st.success(f"✅ {nome_sel} removido da plataforma.")
                    st.session_state.pop("rh_colaborador_sel", None)
                    st.rerun()

        with col_rm2:
            st.markdown(
                "<p style='color:#F1F5F9;font-weight:700;margin:0 0 6px;'>"
                "⛔ Adicionar à Lista Negra</p>"
                "<p style='color:#64748B;font-size:0.78rem;'>"
                "Bloqueia o acesso mas mantém o registo. "
                "Fica vísivel na Lista Negra com observações.</p>",
                unsafe_allow_html=True)
            obs_ln = st.text_area(
                "Motivo / Observações *",
                key="rh_obs_ln", height=68,
                placeholder="Ex: Abandono de posto, comportamento inadequado...")
            if st.button("⛔ Enviar para Lista Negra",
                         key="btn_lista_negra"):
                if not obs_ln.strip():
                    st.error("⚠️ Indica o motivo.")
                else:
                    # 1. Bloquear utilizador (Tipo → Bloqueado)
                    u_ln = _load_users_fresh()
                    mk_ln = u_ln["Nome"] == nome_sel
                    if mk_ln.any():
                        u_ln.loc[mk_ln, "Tipo"]          = "Bloqueado"
                        u_ln.loc[mk_ln, "Lista_Negra"]   = "Sim"
                        u_ln.loc[mk_ln, "Lista_Negra_Data"] =                             datetime.now().strftime("%d/%m/%Y %H:%M")
                        u_ln.loc[mk_ln, "Lista_Negra_Obs"] = obs_ln.strip()
                        u_ln.loc[mk_ln, "Lista_Negra_Por"] =                             st.session_state.get("user", "admin")
                        save_db(u_ln, "usuarios.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        log_audit(
                            usuario=st.session_state.get("user","admin"),
                            acao="LISTA_NEGRA",
                            tabela="usuarios.csv",
                            registro_id=nome_sel,
                            detalhes=f"Lista negra: {obs_ln[:100]}")
                        st.success(f"⛔ {nome_sel} adicionado à lista negra.")
                        st.rerun()

        # ── Ver Lista Negra ───────────────────────────────────────
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        u_all_ln = _load_users_fresh()
        ln_users = u_all_ln[
            u_all_ln.get("Lista_Negra", pd.Series(["Não"]*len(u_all_ln))) == "Sim"
        ] if not u_all_ln.empty and "Lista_Negra" in u_all_ln.columns else pd.DataFrame()

        if not ln_users.empty:
            with st.expander(f"📋 Lista Negra ({len(ln_users)} colaborador(es))",
                             expanded=False):
                for _, ln_row in ln_users.iterrows():
                    ln_nome = ln_row.get("Nome","")
                    ln_data = ln_row.get("Lista_Negra_Data","")
                    ln_por  = ln_row.get("Lista_Negra_Por","")
                    ln_obs  = ln_row.get("Lista_Negra_Obs","")
                    st.markdown(
                        f"<div style='background:#1E293B;border-radius:10px;"
                        f"padding:12px 16px;margin-bottom:8px;"
                        f"border-left:4px solid #EF4444;'>"
                        f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:flex-start;'>"
                        f"<div>"
                        f"<p style='color:#F1F5F9;font-weight:700;margin:0;'>"
                        f"⛔ {ln_nome}</p>"
                        f"<p style='color:#64748B;font-size:0.75rem;margin:2px 0;'>"
                        f"Adicionado por {ln_por} em {ln_data}</p>"
                        f"<p style='color:#94A3B8;font-size:0.8rem;margin:4px 0 0;'>"
                        f"{ln_obs}</p>"
                        f"</div></div></div>",
                        unsafe_allow_html=True
                    )
                    # Opção de reactivar
                    if st.button(f"🔓 Reactivar {ln_nome}",
                                 key=f"btn_reactivar_{ln_nome}"):
                        u_ra = _load_users_fresh()
                        mk_ra = u_ra["Nome"] == ln_nome
                        if mk_ra.any():
                            u_ra.loc[mk_ra, "Tipo"]        = "Técnico"
                            u_ra.loc[mk_ra, "Lista_Negra"] = "Não"
                            u_ra.loc[mk_ra, "Lista_Negra_Data"] = ""
                            u_ra.loc[mk_ra, "Lista_Negra_Obs"]  = ""
                            u_ra.loc[mk_ra, "Lista_Negra_Por"]  = ""
                            save_db(u_ra, "usuarios.csv")
                            inv("usuarios.csv")
                            from core import _cached_load_all
                            _cached_load_all.clear()
                            log_audit(
                                usuario=st.session_state.get("user","admin"),
                                acao="REACTIVAR_COLABORADOR",
                                tabela="usuarios.csv",
                                registro_id=ln_nome,
                                detalhes="Reactivado da lista negra")
                            st.success(f"✅ {ln_nome} reactivado.")
                            st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 3 — DADOS LEGAIS
    # ════════════════════════════════════════════════════════════════
    with tab_dados_legais:
        st.markdown("### 📋 Dados Legais e Fiscais")

        _u_dl = _load_users_fresh()
        if _u_dl.empty:
            st.info("Sem colaboradores.")
        else:
            _nomes_dl = _u_dl['Nome'].tolist()
            _sel_dl_def = st.session_state.get('rh_colaborador_sel', _nomes_dl[0])
            _idx_dl = _nomes_dl.index(_sel_dl_def) if _sel_dl_def in _nomes_dl else 0
            _nome_dl = st.selectbox("Colaborador", _nomes_dl,
                                    index=_idx_dl, key="dl_colab_sel")
            st.session_state['rh_colaborador_sel'] = _nome_dl

            _rh_dl = _load_rh_fresh()
            _mask_dl = (_rh_dl['Nome'] == _nome_dl) if not _rh_dl.empty else pd.Series([], dtype=bool)
            _row_dl  = _rh_dl[_mask_dl].iloc[0].copy() if _mask_dl.any() else pd.Series(dtype=str)

            # Fallback de apresentação: campos partilhados que estejam vazios em
            # colaboradores_rh.csv são pré-preenchidos no formulário a partir de
            # usuarios.csv. Apenas visual — não grava nada (colaboradores_rh.csv
            # continua a ser a fonte de verdade quando já tem o campo preenchido).
            _mask_u_dl = (_u_dl['Nome'] == _nome_dl)
            if _mask_u_dl.any():
                _u_row_dl = _u_dl[_mask_u_dl].iloc[0]
                for _fk in ("NISS", "CC", "CC_Validade", "NIF", "Email",
                            "Morada", "Nacionalidade", "Estado_Civil", "DataNasc"):
                    if not str(_row_dl.get(_fk, "")).strip():
                        _uv = str(_u_row_dl.get(_fk, "")).strip()
                        if _uv:
                            _row_dl[_fk] = _uv

            def _v(campo, default=""):
                return _row_dl.get(campo, default) if not _row_dl.empty else default

            def _opt_idx(opts, val):
                return opts.index(val) if val in opts else 0

            def _sel_opts(opts, val):
                """Devolve (lista_opcoes, indice) com suporte a valores antigos
                gravados que já não constam da lista actual — são acrescentados
                no fim em runtime para não se perder o valor guardado."""
                o = list(opts)
                if val and val not in o:
                    o = o + [val]
                return o, (o.index(val) if val in o else 0)

            # Sufixo único por colaborador, para que os widgets (e o seu
            # value=) sejam recriados ao trocar de colaborador, em vez de
            # reaproveitarem o estado (e os valores) do anterior.
            _slug = hashlib.md5(_nome_dl.encode()).hexdigest()[:8]

            # ── 1. Identificação Legal ────────────────────────────
            with st.expander("🪪 Identificação Legal", expanded=True):
                with st.form(f"dl_form_ident_{_slug}"):
                    _c1, _c2, _c3 = st.columns(3)
                    with _c1:
                        _genero   = st.selectbox("Género", GENERO_OPTS,
                            index=_opt_idx(GENERO_OPTS, _v("Genero")), key=f"dl_genero_{_slug}")
                        _datanasc = st.text_input("Data Nascimento (DD/MM/AAAA)",
                            value=_v("DataNasc"), key=f"dl_datanasc_{_slug}")
                        _nat  = st.text_input("Naturalidade", value=_v("Naturalidade"), key=f"dl_nat_{_slug}")
                    with _c2:
                        _nac  = st.text_input("Nacionalidade", value=_v("Nacionalidade"), key=f"dl_nac_{_slug}")
                        _pais = st.text_input("País Residência", value=_v("Pais_Residencia"), key=f"dl_pais_{_slug}")
                        _nif  = st.text_input("NIF", value=_v("NIF"), key=f"dl_nif_{_slug}")
                    with _c3:
                        _niss = st.text_input("NISS", value=_v("NISS"), key=f"dl_niss_{_slug}")
                        _cc   = st.text_input("Nº Cartão Cidadão", value=_v("CC"), key=f"dl_cc_{_slug}")
                        _ccval= st.text_input("Validade CC (DD/MM/AAAA)",
                            value=_v("CC_Validade"), key=f"dl_ccval_{_slug}")
                    _c4, _c5 = st.columns(2)
                    with _c4:
                        _pass_num = st.text_input("Passaporte", value=_v("Passaporte"), key=f"dl_pass_{_slug}")
                        _pass_val = st.text_input("Validade Passaporte (DD/MM/AAAA)",
                            value=_v("Passaporte_Validade"), key=f"dl_passval_{_slug}")
                    with _c5:
                        _est_civil = st.selectbox("Estado Civil", ESTADO_CIVIL_OPTS,
                            index=_opt_idx(ESTADO_CIVIL_OPTS, _v("Estado_Civil")), key=f"dl_estcivil_{_slug}")
                        _n_dep = st.text_input("Nº Dependentes", value=_v("N_Dependentes"), key=f"dl_ndep_{_slug}")
                        _n_dep_def = st.text_input("Nº Dependentes c/ Deficiência",
                            value=_v("N_Dependentes_Deficiencia"), key=f"dl_ndepdef_{_slug}")
                    if st.form_submit_button("💾 Guardar Identificação",
                                             use_container_width=True, type="primary"):
                        if _sync_rh_csv(_nome_dl, {
                            "Genero": _genero, "DataNasc": _datanasc,
                            "Naturalidade": _nat, "Nacionalidade": _nac,
                            "Pais_Residencia": _pais, "NIF": _nif, "NISS": _niss,
                            "CC": _cc, "CC_Validade": _ccval,
                            "Passaporte": _pass_num, "Passaporte_Validade": _pass_val,
                            "Estado_Civil": _est_civil, "N_Dependentes": _n_dep,
                            "N_Dependentes_Deficiencia": _n_dep_def,
                        }):
                            st.success("✅ Identificação guardada.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao guardar — verifica ligação ao GCS")

            # ── 2. Dados Fiscais ──────────────────────────────────
            with st.expander("🏦 Dados Fiscais"):
                with st.form(f"dl_form_fiscal_{_slug}"):
                    _c1, _c2, _c3 = st.columns(3)
                    with _c1:
                        _irs_esc  = st.text_input("Escalão IRS", value=_v("IRS_Escalao"), key=f"dl_irs_esc_{_slug}")
                        _irs_pct  = st.text_input("Taxa IRS (%)", value=_v("IRS_Percentagem"), key=f"dl_irs_pct_{_slug}")
                        _tit_unico= st.selectbox("Titular Único", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Titular_Unico"))
                                  if _v("Titular_Unico") in ["","Sim","Não"] else 0,
                            key=f"dl_tit_unico_{_slug}")
                    with _c2:
                        _taxa_ret = st.text_input("Taxa Retenção (%)", value=_v("Taxa_Retencao_IRS"), key=f"dl_taxa_ret_{_slug}")
                        _isencao  = st.selectbox("Isenção IRS", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Isencao_IRS"))
                                  if _v("Isencao_IRS") in ["","Sim","Não"] else 0,
                            key=f"dl_isencao_{_slug}")
                        _artigo_irs = st.text_input("Artigo IRS", value=_v("Artigo_IRS"), key=f"dl_artigo_{_slug}")
                    with _c3:
                        _ef_opts, _ef_idx = _sel_opts(ESTADO_FISCAL_OPTS, _v("Estado_Fiscal"))
                        _est_fiscal = st.selectbox("Estado Fiscal", _ef_opts,
                            index=_ef_idx, key=f"dl_estfiscal_{_slug}")
                        _mf_opts, _mf_idx = _sel_opts(MEDIDA_FISCAL_OPTS, _v("Medida_Fiscal"))
                        _med_fiscal = st.selectbox("Medida Fiscal", _mf_opts,
                            index=_mf_idx, key=f"dl_medfiscal_{_slug}")
                        _ess_opts, _ess_idx = _sel_opts(ENQUADRAMENTO_SS_OPTS, _v("Enquadramento_SS"))
                        _enq_ss = st.selectbox("Enquadramento SS", _ess_opts,
                            index=_ess_idx, key=f"dl_enqss_{_slug}")
                    if st.form_submit_button("💾 Guardar Dados Fiscais",
                                             use_container_width=True, type="primary"):
                        if _sync_rh_csv(_nome_dl, {
                            "IRS_Escalao": _irs_esc, "IRS_Percentagem": _irs_pct,
                            "Titular_Unico": _tit_unico, "Taxa_Retencao_IRS": _taxa_ret,
                            "Isencao_IRS": _isencao, "Artigo_IRS": _artigo_irs,
                            "Estado_Fiscal": _est_fiscal, "Medida_Fiscal": _med_fiscal,
                            "Enquadramento_SS": _enq_ss,
                        }):
                            st.success("✅ Dados fiscais guardados.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao guardar — verifica ligação ao GCS")

            # ── 3. Dados Contratuais ──────────────────────────────
            with st.expander("📄 Dados Contratuais"):
                with st.form(f"dl_form_contrato_{_slug}"):
                    _c1, _c2, _c3 = st.columns(3)
                    with _c1:
                        _tp_ct = st.selectbox("Tipo Contrato", TIPO_CONTRATO_OPTS,
                            index=_opt_idx(TIPO_CONTRATO_OPTS, _v("Tipo_Contrato")), key=f"dl_tpct_{_slug}")
                        _mod_hr = st.selectbox("Modalidade Horário", MODALIDADE_HORARIO_OPTS,
                            index=_opt_idx(MODALIDADE_HORARIO_OPTS, _v("Modalidade_Horario")), key=f"dl_modhr_{_slug}")
                        _hrs_sem = st.text_input("Horas/Semana", value=_v("Horas_Semana"), key=f"dl_hrsem_{_slug}")
                    with _c2:
                        _ct_ini  = st.text_input("Data Início Contrato (DD/MM/AAAA)",
                            value=_v("Contrato_Inicio"), key=f"dl_ctini_{_slug}")
                        _ct_fim  = st.text_input("Data Fim Contrato (DD/MM/AAAA)",
                            value=_v("Contrato_Fim"), key=f"dl_ctfim_{_slug}")
                        _ct_ind  = st.selectbox("Contrato Indeterminado", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Contrato_Indeterminado"))
                                  if _v("Contrato_Indeterminado") in ["","Sim","Não"] else 0,
                            key=f"dl_ctind_{_slug}")
                    with _c3:
                        _pe      = st.text_input("Período Experimental (meses)",
                            value=_v("Periodo_Experimental"), key=f"dl_pe_{_slug}")
                        _pe_fim  = st.text_input("Fim Período Exp. (DD/MM/AAAA)",
                            value=_v("Periodo_Experimental_Fim"), key=f"dl_pefim_{_slug}")
                        _local_t = st.text_input("Local de Trabalho",
                            value=_v("Local_Trabalho"), key=f"dl_local_{_slug}")
                    _func_ct = st.text_input("Função Contratual",
                        value=_v("Funcao_Contratual"), key=f"dl_func_{_slug}")

                    st.markdown("**Relatório Único — Modalidade e Tempo de Trabalho**")
                    _c6, _c7, _c8 = st.columns(3)
                    with _c6:
                        _mc_opts, _mc_idx = _sel_opts(MODALIDADE_CONTRATO_OPTS, _v("Modalidade_Contrato"))
                        _mod_ct = st.selectbox("Modalidade Contrato (RU)", _mc_opts,
                            index=_mc_idx, key=f"dl_modct_{_slug}")
                        _pt_opts, _pt_idx = _sel_opts(PRESTACAO_TRABALHO_OPTS, _v("Prestacao_Trabalho"))
                        _prest_trab = st.selectbox("Prestação de Trabalho", _pt_opts,
                            index=_pt_idx, key=f"dl_presttrab_{_slug}")
                        _th_opts, _th_idx = _sel_opts(TIPO_HORARIO_OPTS, _v("Tipo_Horario"))
                        _tipo_hr = st.selectbox("Tipo Horário", _th_opts,
                            index=_th_idx, key=f"dl_tipohr_{_slug}")
                    with _c7:
                        _dtt_opts, _dtt_idx = _sel_opts(DURACAO_TT_OPTS, _v("Duracao_Tempo_Trabalho"))
                        _dur_tt = st.selectbox("Duração Tempo Trabalho (RU)", _dtt_opts,
                            index=_dtt_idx, key=f"dl_durtt_{_slug}")
                        _ott_opts, _ott_idx = _sel_opts(ORG_TT_OPTS, _v("Organizacao_Tempo_Trabalho"))
                        _org_tt = st.selectbox("Organização Tempo Trabalho (RU)", _ott_opts,
                            index=_ott_idx, key=f"dl_orgtt_{_slug}")
                    with _c8:
                        _mco_opts, _mco_idx = _sel_opts(MOTIVO_CONTRATO_OPTS, _v("Motivo_Contrato"))
                        _mot_ct = st.selectbox("Motivo Contrato", _mco_opts,
                            index=_mco_idx, key=f"dl_motct_{_slug}")
                        _me_opts, _me_idx = _sel_opts(MOTIVO_ENTRADA_OPTS, _v("Motivo_Entrada"))
                        _mot_ent = st.selectbox("Motivo Entrada", _me_opts,
                            index=_me_idx, key=f"dl_motent_{_slug}")

                    st.markdown("**Saída**")
                    _c9, _c10 = st.columns(2)
                    with _c9:
                        _ms_opts, _ms_idx = _sel_opts(MOTIVO_SAIDA_OPTS, _v("Motivo_Saida"))
                        _mot_sai = st.selectbox("Motivo Saída", _ms_opts,
                            index=_ms_idx, key=f"dl_motsai_{_slug}")
                    with _c10:
                        _data_sai = st.text_input("Data Saída (DD/MM/AAAA)",
                            value=_v("Data_Saida"), key=f"dl_datasai_{_slug}")

                    if st.form_submit_button("💾 Guardar Dados Contratuais",
                                             use_container_width=True, type="primary"):
                        if _sync_rh_csv(_nome_dl, {
                            "Tipo_Contrato": _tp_ct, "Modalidade_Horario": _mod_hr,
                            "Horas_Semana": _hrs_sem, "Contrato_Inicio": _ct_ini,
                            "Contrato_Fim": _ct_fim, "Contrato_Indeterminado": _ct_ind,
                            "Periodo_Experimental": _pe, "Periodo_Experimental_Fim": _pe_fim,
                            "Local_Trabalho": _local_t, "Funcao_Contratual": _func_ct,
                            "Modalidade_Contrato": _mod_ct, "Prestacao_Trabalho": _prest_trab,
                            "Tipo_Horario": _tipo_hr, "Duracao_Tempo_Trabalho": _dur_tt,
                            "Organizacao_Tempo_Trabalho": _org_tt, "Motivo_Contrato": _mot_ct,
                            "Motivo_Entrada": _mot_ent, "Motivo_Saida": _mot_sai,
                            "Data_Saida": _data_sai,
                        }):
                            st.success("✅ Dados contratuais guardados.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao guardar — verifica ligação ao GCS")

            # ── 4. Remuneração e Pagamento ────────────────────────
            with st.expander("💰 Remuneração e Pagamento"):
                with st.form(f"dl_form_rem_{_slug}"):
                    _c1, _c2, _c3 = st.columns(3)
                    with _c1:
                        _sal_b  = st.text_input("Salário Base (€)",
                            value=_v("Salario_Base"), key=f"dl_salb_{_slug}")
                        _sub_al = st.text_input("Subsídio Alimentação (€)",
                            value=_v("Subsidio_Alimentacao"), key=f"dl_subal_{_slug}")
                        _sub_fe = st.text_input("Subsídio Férias (€)",
                            value=_v("Subsidio_Ferias"), key=f"dl_subfe_{_slug}")
                    with _c2:
                        _sub_na = st.text_input("Subsídio Natal (€)",
                            value=_v("Subsidio_Natal"), key=f"dl_subna_{_slug}")
                        _prem   = st.text_input("Prémio Produção (€)",
                            value=_v("Premio_Producao"), key=f"dl_prem_{_slug}")
                        _outros = st.text_input("Outros Complementos",
                            value=_v("Outros_Complementos"), key=f"dl_outros_{_slug}")
                    with _c3:
                        _forma_pag = st.selectbox("Forma Pagamento", FORMA_PAGAMENTO_OPTS,
                            index=_opt_idx(FORMA_PAGAMENTO_OPTS, _v("Forma_Pagamento")), key=f"dl_fpag_{_slug}")
                        _iban_val  = st.selectbox("IBAN Validado", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("IBAN_Validado"))
                                  if _v("IBAN_Validado") in ["","Sim","Não"] else 0,
                            key=f"dl_ibanval_{_slug}")
                        _swift = st.text_input("SWIFT/BIC",
                            value=_v("SWIFT_BIC"), key=f"dl_swift_{_slug}")

                    st.markdown("**Subsídio de Alimentação e Banco**")
                    _c4, _c5, _c6 = st.columns(3)
                    with _c4:
                        _sam_opts, _sam_idx = _sel_opts(SUB_ALIM_MODO_OPTS, _v("Sub_Alimentacao_Modo"))
                        _sub_al_modo = st.selectbox("Subsídio Alimentação - Modo", _sam_opts,
                            index=_sam_idx, key=f"dl_subalmodo_{_slug}")
                        _sae_opts, _sae_idx = _sel_opts(SUB_ALIM_ENTIDADE_OPTS, _v("Sub_Alimentacao_Entidade"))
                        _sub_al_ent = st.selectbox("Subsídio Alimentação - Entidade", _sae_opts,
                            index=_sae_idx, key=f"dl_subalent_{_slug}")
                        _num_cartao_ref = st.text_input("Nº Cartão Refeição",
                            value=_v("Num_Cartao_Refeicao"), key=f"dl_numcartref_{_slug}")
                    with _c5:
                        _mr_opts, _mr_idx = _sel_opts(MODO_REMUN_OPTS, _v("Modo_Remuneracao"))
                        _modo_rem = st.selectbox("Modo Remuneração", _mr_opts,
                            index=_mr_idx, key=f"dl_modorem_{_slug}")
                        _banco_nome = st.text_input("Banco (Nome)",
                            value=_v("Banco_Nome"), key=f"dl_banconome_{_slug}")
                    with _c6:
                        _rr_opts, _rr_idx = _sel_opts(REGIME_REFORMA_OPTS, _v("Regime_Reforma"))
                        _reg_reforma = st.selectbox("Regime Reforma", _rr_opts,
                            index=_rr_idx, key=f"dl_regreforma_{_slug}")
                        _pensionista = st.selectbox("Pensionista", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Pensionista"))
                                  if _v("Pensionista") in ["","Sim","Não"] else 0,
                            key=f"dl_pensionista_{_slug}")

                    if st.form_submit_button("💾 Guardar Remuneração",
                                             use_container_width=True, type="primary"):
                        if _sync_rh_csv(_nome_dl, {
                            "Salario_Base": _sal_b, "Subsidio_Alimentacao": _sub_al,
                            "Subsidio_Ferias": _sub_fe, "Subsidio_Natal": _sub_na,
                            "Premio_Producao": _prem, "Outros_Complementos": _outros,
                            "Forma_Pagamento": _forma_pag, "IBAN_Validado": _iban_val,
                            "SWIFT_BIC": _swift,
                            "Sub_Alimentacao_Modo": _sub_al_modo, "Sub_Alimentacao_Entidade": _sub_al_ent,
                            "Num_Cartao_Refeicao": _num_cartao_ref, "Modo_Remuneracao": _modo_rem,
                            "Banco_Nome": _banco_nome, "Regime_Reforma": _reg_reforma,
                            "Pensionista": _pensionista,
                        }):
                            st.success("✅ Remuneração guardada.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao guardar — verifica ligação ao GCS")

            # ── 5. Profissional / Relatório Único ─────────────────
            with st.expander("📊 Profissional & Relatório Único"):
                with st.form(f"dl_form_prof_{_slug}"):
                    _c1, _c2 = st.columns(2)
                    with _c1:
                        _hab_opts  = HABILITACOES_RU_OPTS.copy()
                        _hab_val   = _v("Nivel_Habilitacoes")
                        _hab_match = next((o for o in _hab_opts if o.startswith(f"{_hab_val} - ")), "")
                        if not _hab_match and _hab_val:
                            _hab_opts  = _hab_opts + [_hab_val]
                            _hab_match = _hab_val
                        _hab_idx = _hab_opts.index(_hab_match) if _hab_match in _hab_opts else 0
                        _nivel_hab = st.selectbox("Nível Habilitações (RU)", _hab_opts,
                            index=_hab_idx, key=f"dl_nhab_{_slug}")
                        _sit_prof  = st.selectbox("Situação Profissional", SITUACAO_PROFISSIONAL_OPTS,
                            index=_opt_idx(SITUACAO_PROFISSIONAL_OPTS, _v("Situacao_Profissional")), key=f"dl_sitprof_{_slug}")
                        _cpp_opts  = [""] + [f"{k} – {v}" for k,v in PROFISSOES_CPP_CPS.items()]
                        _cpp_val   = _v("Profissao_CPP")
                        _cpp_match = next((o for o in _cpp_opts if o.startswith(_cpp_val)), "")
                        _cpp_idx   = _cpp_opts.index(_cpp_match) if _cpp_match in _cpp_opts else 0
                        _profissao = st.selectbox("Profissão (CPP 2010)", _cpp_opts,
                            index=_cpp_idx, key=f"dl_cpp_{_slug}")
                        _cct_opts  = [""] + [f"{k} – {v}" for k,v in CATEGORIAS_CCT_25989.items()]
                        _cct_val   = _v("Categoria_CCT")
                        _cct_match = next((o for o in _cct_opts if o.startswith(_cct_val)), "")
                        _cct_idx   = _cct_opts.index(_cct_match) if _cct_match in _cct_opts else 0
                        _cat_cct   = st.selectbox("Categoria CCT", _cct_opts,
                            index=_cct_idx, key=f"dl_catcct_{_slug}")
                    with _c2:
                        _irct = st.selectbox("IRCT Aplicável", IRCT_OPTS,
                            index=_opt_idx(IRCT_OPTS, _v("IRCT_Aplicavel")), key=f"dl_irct_{_slug}")
                        _vinculo = st.text_input("Vínculo Empresa",
                            value=_v("Vinculo_Empresa"), key=f"dl_vinculo_{_slug}")
                        _red_hr  = st.selectbox("Redução Horário", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Reducao_Horario"))
                                  if _v("Reducao_Horario") in ["","Sim","Não"] else 0,
                            key=f"dl_redhr_{_slug}")
                        _dt_prom = st.text_input("Data Última Promoção (DD/MM/AAAA)",
                            value=_v("Data_Ultima_Promocao"), key=f"dl_dtprom_{_slug}")
                        _ant_anos= st.text_input("Antiguidade (anos)",
                            value=_v("Antiguidade_Anos"), key=f"dl_antanos_{_slug}")
                        _n_rem   = st.text_input("Nível Remuneratório",
                            value=_v("Nivel_Remuneratorio"), key=f"dl_nrem_{_slug}")
                    _c3, _c4 = st.columns(2)
                    with _c3:
                        _grau_def = st.text_input("Grau Deficiência (%)",
                            value=_v("Grau_Deficiencia"), key=f"dl_graudef_{_slug}")
                        _def_tipo = st.text_input("Tipo Deficiência",
                            value=_v("Deficiencia_Tipo"), key=f"dl_deftipo_{_slug}")
                    with _c4:
                        _cartao_prof_num = st.text_input("Nº Cartão Profissional",
                            value=_v("Cartao_Prof_Num"), key=f"dl_cpnum_{_slug}")
                        _cartao_prof_val = st.text_input("Validade Cartão Prof. (DD/MM/AAAA)",
                            value=_v("Cartao_Prof_Validade"), key=f"dl_cpval_{_slug}")

                    st.markdown("**Relatório Único — Outros**")
                    _c11, _c12 = st.columns(2)
                    with _c11:
                        _npi_opts, _npi_idx = _sel_opts(NIVEL_PROF_IGDT_OPTS, _v("Nivel_Profissional_IGDT"))
                        _nivel_prof_igdt = st.selectbox("Nível Profissional (IGDT)", _npi_opts,
                            index=_npi_idx, key=f"dl_nivelprofigdt_{_slug}")
                        _oes_opts, _oes_idx = _sel_opts(ORIGEM_ENS_SUP_OPTS, _v("Origem_Ensino_Superior"))
                        _origem_ens_sup = st.selectbox("Origem Ensino Superior", _oes_opts,
                            index=_oes_idx, key=f"dl_origemenssup_{_slug}")
                        _tdi_opts, _tdi_idx = _sel_opts(TIPO_DOC_ID_OPTS, _v("Tipo_Doc_ID"))
                        _tipo_doc_id = st.selectbox("Tipo Documento Identificação", _tdi_opts,
                            index=_tdi_idx, key=f"dl_tipodocid_{_slug}")
                    with _c12:
                        _seg_at = st.text_input("Seguradora AT",
                            value=_v("Seguradora_AT"), key=f"dl_segat_{_slug}")
                        _apol_at = st.text_input("Apólice AT",
                            value=_v("Apolice_AT"), key=f"dl_apolat_{_slug}")

                    if st.form_submit_button("💾 Guardar Dados Profissionais",
                                             use_container_width=True, type="primary"):
                        _profissao_code = _profissao.split(" – ")[0] if " – " in _profissao else _profissao
                        _cat_cct_code   = _cat_cct.split(" – ")[0]   if " – " in _cat_cct   else _cat_cct
                        _nivel_hab_code = _nivel_hab.split(" - ")[0] if " - " in _nivel_hab else _nivel_hab
                        if _sync_rh_csv(_nome_dl, {
                            "Nivel_Habilitacoes": _nivel_hab_code, "Situacao_Profissional": _sit_prof,
                            "Profissao_CPP": _profissao_code, "Categoria_CCT": _cat_cct_code,
                            "IRCT_Aplicavel": _irct, "Vinculo_Empresa": _vinculo,
                            "Reducao_Horario": _red_hr, "Data_Ultima_Promocao": _dt_prom,
                            "Antiguidade_Anos": _ant_anos, "Nivel_Remuneratorio": _n_rem,
                            "Grau_Deficiencia": _grau_def, "Deficiencia_Tipo": _def_tipo,
                            "Cartao_Prof_Num": _cartao_prof_num, "Cartao_Prof_Validade": _cartao_prof_val,
                            "Nivel_Profissional_IGDT": _nivel_prof_igdt,
                            "Origem_Ensino_Superior": _origem_ens_sup,
                            "Tipo_Doc_ID": _tipo_doc_id,
                            "Seguradora_AT": _seg_at, "Apolice_AT": _apol_at,
                        }):
                            st.success("✅ Dados profissionais guardados.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao guardar — verifica ligação ao GCS")

            # ── 6. Condução e Documentos ──────────────────────────
            with st.expander("🚗 Condução e Documentos"):
                with st.form(f"dl_form_conducao_{_slug}"):
                    _c1, _c2 = st.columns(2)
                    with _c1:
                        _carta_num = st.text_input("Nº Carta de Condução",
                            value=_v("Carta_Conducao_Num"), key=f"dl_cartanum_{_slug}")
                        _carta_val = st.text_input("Validade Carta (DD/MM/AAAA)",
                            value=_v("Carta_Conducao_Validade"), key=f"dl_cartaval_{_slug}")
                        _cc_opts, _cc_idx = _sel_opts(CARTA_CAT_OPTS, _v("Carta_Conducao_Categoria"))
                        _carta_cat = st.selectbox("Categoria(s) Carta", _cc_opts,
                            index=_cc_idx, key=f"dl_cartacat_{_slug}")
                    with _c2:
                        _reg_assinado = st.selectbox("Regulamento Interno Assinado", ["","Sim","Não"],
                            index=["","Sim","Não"].index(_v("Regulamento_Assinado"))
                                  if _v("Regulamento_Assinado") in ["","Sim","Não"] else 0,
                            key=f"dl_regassinado_{_slug}")
                        _reg_data = st.text_input("Data Assinatura Regulamento (DD/MM/AAAA)",
                            value=_v("Regulamento_Data"), key=f"dl_regdata_{_slug}")
                    if st.form_submit_button("💾 Guardar Condução e Documentos",
                                             use_container_width=True, type="primary"):
                        if _sync_rh_csv(_nome_dl, {
                            "Carta_Conducao_Num": _carta_num, "Carta_Conducao_Validade": _carta_val,
                            "Carta_Conducao_Categoria": _carta_cat,
                            "Regulamento_Assinado": _reg_assinado, "Regulamento_Data": _reg_data,
                        }):
                            st.success("✅ Dados de condução guardados.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao guardar — verifica ligação ao GCS")

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — IMPORTAR ETICADATA
    # ════════════════════════════════════════════════════════════════
    with tab_eticadata:
        st.markdown("### 📥 Importar Lista de Trabalhadores (Eticadata)")
        st.info(
            "Exporta do Eticadata o ficheiro **`Lista_Trabalhadores.csv`** "
            "(separador `;`, codificação UTF-8 com BOM) e faz upload aqui. "
            "O match é feito pelo Nome com `usuarios.csv`. "
            "Colaboradores sem match são criados automaticamente."
        )

        # ── Migração de schema (Parte 0) ──────────────────────────
        if st.session_state.get('tipo') == 'Admin':
            with st.expander("🔧 Migrar schema colaboradores_rh.csv"):
                _DUPLICADOS_MIGRACAO = {
                    "Categoria_Profissional_Cod":  "Categoria_CCT",
                    "Categoria_Profissional_Desc": "Categoria_CCT",
                    "Profissao_CPP_Cod":           "Profissao_CPP",
                    "Profissao_CPP_Desc":          "Profissao_CPP",
                    "IRCT_Aplicabilidade":         "IRCT_Aplicavel",
                    "Habilitacoes":                "Nivel_Habilitacoes",
                    "Habilitacoes_Cod":            "Nivel_Habilitacoes",
                    "Habilitacoes_Desc":           "Nivel_Habilitacoes",
                }
                _df_mig = _load_rh_fresh()
                _cols_dup_presentes = [c for c in _DUPLICADOS_MIGRACAO if c in _df_mig.columns]

                if not _cols_dup_presentes:
                    st.success("✅ Schema já migrado.")
                else:
                    st.warning(
                        f"⚠️ Encontradas {len(_cols_dup_presentes)} coluna(s) "
                        f"duplicada(s): {', '.join(_cols_dup_presentes)}"
                    )
                    _relatorio_mig = []
                    for _dup, _canon in _DUPLICADOS_MIGRACAO.items():
                        if _dup not in _df_mig.columns:
                            continue
                        _n_merge = 0
                        for _idx in _df_mig.index:
                            _val_dup   = str(_df_mig.at[_idx, _dup]).strip()
                            _val_canon = str(_df_mig.at[_idx, _canon]).strip() \
                                if _canon in _df_mig.columns else ""
                            if _val_dup and not _val_canon:
                                _n_merge += 1
                        _relatorio_mig.append(
                            f"- `{_dup}` → `{_canon}`: {_n_merge} valor(es) a migrar"
                        )

                    st.markdown("**Relatório de migração:**")
                    for _l in _relatorio_mig:
                        st.markdown(_l)

                    if st.button("✅ Aplicar migração", key="btn_migrar_schema",
                                  type="primary"):
                        for _dup, _canon in _DUPLICADOS_MIGRACAO.items():
                            if _dup not in _df_mig.columns:
                                continue
                            if _canon not in _df_mig.columns:
                                _df_mig[_canon] = ""
                            for _idx in _df_mig.index:
                                _val_dup   = str(_df_mig.at[_idx, _dup]).strip()
                                _val_canon = str(_df_mig.at[_idx, _canon]).strip()
                                if _val_dup and not _val_canon:
                                    _df_mig.at[_idx, _canon] = _val_dup
                            _df_mig = _df_mig.drop(columns=[_dup])

                        _ok_mig = save_db(_df_mig, "colaboradores_rh.csv",
                                          permitir_reducao=True)
                        if _ok_mig:
                            inv("colaboradores_rh.csv")
                            from core import _cached_load_all
                            _cached_load_all.clear()
                            log_audit(
                                usuario=admin_nome,
                                acao="MIGRAR_SCHEMA_RH",
                                tabela="colaboradores_rh.csv",
                                registro_id="batch",
                                detalhes=f"Colunas migradas: {', '.join(_cols_dup_presentes)}",
                                ip=""
                            )
                            st.success("✅ Migração aplicada com sucesso.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao guardar — verifica ligação ao GCS")

        # ── Tabelas de conversão de valores Eticadata ─────────────
        _E_SEXO = {"0": "Masculino", "1": "Feminino"}
        _E_EST_CIVIL = {
            "1": "Solteiro(a)", "2": "Casado(a)", "3": "Viúvo(a)",
            "4": "Divorciado(a)", "5": "União de facto",
            "6": "Separado(a) judicialmente",
        }
        _E_NAC = {
            "0": "Português", "2": "Brasileiro",
            "3": "Outro UE/EEE", "4": "Extracomunitário",
        }
        _E_NIVEL_QUAL = {
            "0": "", "1": "Quadro superior", "2": "Quadro médio",
            "3": "Encarregado contramestre mestre e chefe de equipa",
            "4": "Profissional altamente qualificado",
            "5": "Profissional qualificado",
            "6": "Profissional semi-qualificado especializado",
            "7": "Profissional não qualificado indiferenciado",
            "8": "Estagiário praticante e aprendiz",
        }
        _E_DOC_TIPO = {
            "CC": "Cartão de Cidadão", "PASS": "Passaporte",
            "TRT": "Título de Residência Temporária",
            "TRP": "Título de Residência Permanente",
            "CRFCUNET": "Cartão Registo Cidadão UE/EEE",
        }
        _FIXED_RH = {
            # Campos para Dados Legais (nomes canónicos GestNow)
            "IRCT_Aplicavel":             "IRCT 25989 – CCT Empresas Electrotécnicas",
            "Situacao_Profissional":      "Trabalhador por Conta de Outrem",
            "Categoria_CCT":              "02155",
            "Profissao_CPP":              "74124",
            # Campos extra Eticadata (referência)
            "IRCT_Codigo":                "25989",
            "IRCT_Descricao":             "CCT - Empresas Electrotécnicas",
            "Modo_Remuneracao":           "Mensal",
            "Duracao_Tempo_Trabalho":     "1 - Adaptabilidade por regulamentação colectiva (RU:10)",
            "Tipo_Horario":               "Normal Fixo",
            "Pensionista":                "Não",
            "Regime_Reforma":             "1 - Segurança Social",
            "Organizacao_Tempo_Trabalho": "1 - Trabalho diurno",
        }

        def _etica_strip_date(s):
            """Remove parte horária — '29/03/2023 00:00' → '29/03/2023'."""
            s = str(s).strip()
            return s.split(" ")[0] if " " in s else s

        def _etica_map_row(er):
            """Converte linha Eticadata em (rh_dict, users_if_empty_dict, users_always_dict, chefe_bool)."""
            rh = {}
            rh["Eticadata_ID"]           = er.get("intCodigo", "")
            rh["Genero"]                 = _E_SEXO.get(er.get("bitSexo", ""), "")
            rh["Estado_Civil"]           = _E_EST_CIVIL.get(er.get("intEstadoCivil", ""), "")
            rh["Salario_Base"]           = er.get("fltVencActual", "")
            rh["Data_Admissao"]          = _etica_strip_date(er.get("dtmAdmissao", ""))
            # Nomes canónicos GestNow (coincidem com Dados Legais)
            rh["Contrato_Inicio"]        = _etica_strip_date(er.get("dtmInicioContr", ""))
            _fim_c                       = _etica_strip_date(er.get("dtmFimContr", ""))
            rh["Contrato_Fim"]           = _fim_c
            rh["Tipo_Contrato"]          = "Sem Termo" if not _fim_c else "A Termo Certo"
            rh["Horas_Semana"]           = er.get("fltHorasSemanais", "")
            rh["Subsidio_Alimentacao"]   = er.get("fltSubAlimentacao", "")
            rh["Banco_Nome"]             = er.get("strAbrevBanco", "")
            rh["Num_Utente"]             = er.get("strNumUtente", "")
            rh["SWIFT_BIC"]              = er.get("strBic", "")
            rh["Servico_Financas"]       = er.get("strCodRepFinancas", "")
            rh["Naturalidade"]           = er.get("strNaturalidade", "")
            rh["Banco_Empresa_Pagamento"]= er.get("strCodContaEmpresa", "")
            rh["Nacionalidade"]          = _E_NAC.get(er.get("intCodNacionalidade", ""), "")
            rh["Nivel_Qualificacao"]     = _E_NIVEL_QUAL.get(er.get("intNivelQualificacao", ""), "")
            _tdoc                        = er.get("strTypDocId", "")
            rh["Tipo_Doc_ID"]            = _E_DOC_TIPO.get(_tdoc, _tdoc)
            # Campos partilhados com usuarios.csv — também gravados aqui para
            # que fiquem visíveis na tab "Dados Legais" (lê de colaboradores_rh.csv)
            rh["CC"]                     = er.get("strNumBI", "")
            rh["CC_Validade"]            = _etica_strip_date(er.get("dtmValidadeBI", ""))
            rh["NISS"]                   = er.get("strNumSegSocial", "")
            rh["Email"]                  = er.get("strEmail", "")
            rh["Morada"]                 = er.get("strMorada1GRH", "")
            rh["Localidade"]             = er.get("strLocalidadeGRH", "")
            rh["Codigo_Postal"]          = er.get("strCodPostalGRH", "")
            rh["N_Dependentes"]          = er.get("intNumDep", "")
            rh["NIF"]                    = er.get("NIF", "")
            _motivo_saida_raw            = str(er.get("intMotivoSaida", "")).strip()
            try:
                _motivo_saida_int = int(_motivo_saida_raw) if _motivo_saida_raw else 0
            except ValueError:
                _motivo_saida_int = 0
            rh["Motivo_Saida"]           = str(_motivo_saida_int) if _motivo_saida_int > 0 else ""
            rh.update(_FIXED_RH)

            u_if_empty = {
                "Email":        er.get("strEmail", ""),
                "CC":           er.get("strNumBI", ""),
                "CC_Validade":  _etica_strip_date(er.get("dtmValidadeBI", "")),
                "NISS":         er.get("strNumSegSocial", ""),
                "Morada":       er.get("strMorada1GRH", ""),
                "Localidade":   er.get("strLocalidadeGRH", ""),
                "Codigo_Postal":er.get("strCodPostalGRH", ""),
                "Banco_IBAN":   er.get("strIban", ""),
                "DataNasc":     er.get("Data nascimento", ""),
                "NIF":          er.get("NIF", ""),
            }
            u_always = {
                "PrecoHora":  er.get("CA_Valor_Hora", ""),
                "Local_Obra": er.get("CA_Obra", ""),
            }
            chefe = er.get("CA_ChefedeEquipa", "").strip() == "1"
            return rh, u_if_empty, u_always, chefe

        # ── Upload → guardar imediatamente em session_state ────────
        _eti_ukey = f"eti_uploader_{st.session_state.get('eti_upload_key', 0)}"
        _eti_file = st.file_uploader(
            "Selecionar CSV do Eticadata (sep=;, UTF-8 BOM)",
            type=["csv"], key=_eti_ukey
        )
        if _eti_file is not None:
            try:
                _eti_raw = pd.read_csv(
                    _eti_file, sep=";", dtype=str,
                    encoding="utf-8-sig", on_bad_lines='skip'
                )
                _eti_raw.columns = _eti_raw.columns.str.strip()
                _eti_raw = _eti_raw.replace("NULL", "").fillna("")
                for _ec in _eti_raw.select_dtypes(include='object').columns:
                    _eti_raw[_ec] = _eti_raw[_ec].str.strip()
                st.session_state['eticadata_df'] = _eti_raw
            except Exception as _e:
                st.error(f"❌ Erro ao ler o ficheiro: {_e}")

        if 'eticadata_result' in st.session_state:
            _res = st.session_state['eticadata_result']
            st.success(
                f"✅ Importação concluída! "
                f"**{_res['n_act']}** actualizados, "
                f"**{_res['n_new']}** novos criados, "
                f"**{_res['n_campos']}** campos preenchidos."
            )
            if _res.get('novos'):
                st.markdown("#### 🆕 Passwords geradas — guardar agora!")
                st.warning(
                    "⚠️ Estas passwords só são mostradas uma vez. "
                    "Comunica-as aos colaboradores antes de fechar."
                )
                for _nc in _res['novos']:
                    st.markdown(f"- **{_nc['Nome']}** → `{_nc['Password']}`")
            if st.button("✓ Já guardei — fechar relatório",
                         key="imp_fechar_relatorio"):
                del st.session_state['eticadata_result']
                st.rerun()
        elif 'eticadata_df' not in st.session_state:
            st.info("Faz upload do CSV para começar.")
        else:
            _eti_df = st.session_state['eticadata_df']

            # ── Detectar coluna Nome no CSV ────────────────────────
            _nome_col_eti = None
            for _cn in ("Nome", "strNome", "NomeFuncionario", "nome", "NOME"):
                if _cn in _eti_df.columns:
                    _nome_col_eti = _cn
                    break

            # ── Remover linhas completamente vazias (lixo do Excel no
            # fim do export) — não contam para preview nem relatório.
            if _nome_col_eti is not None:
                _eti_df = _eti_df.dropna(subset=[_nome_col_eti])
                _eti_df = _eti_df[_eti_df[_nome_col_eti].astype(str).str.strip() != ""]
                _eti_df = _eti_df.reset_index(drop=True)
                st.session_state['eticadata_df'] = _eti_df

            _ecol_h, _ecol_btn = st.columns([5, 1])
            with _ecol_h:
                st.success(f"✅ Ficheiro carregado: **{len(_eti_df)}** registos, "
                           f"**{len(_eti_df.columns)}** colunas.")
            with _ecol_btn:
                if st.button("🗑️ Limpar", key="imp_limpar"):
                    del st.session_state['eticadata_df']
                    st.session_state['eti_upload_key'] = st.session_state.get('eti_upload_key', 0) + 1
                    st.rerun()

            with st.expander("👁️ CSV original (primeiras 5 linhas)"):
                st.dataframe(_eti_df.head(), use_container_width=True)

            if _nome_col_eti is None:
                st.error(
                    "❌ Coluna 'Nome' não encontrada no CSV. "
                    f"Colunas disponíveis: `{'`, `'.join(_eti_df.columns.tolist())}`"
                )
            else:
                # ── Match por Nome com usuarios.csv ───────────────
                _u_eti = _load_users_fresh()
                _nomes_exact = set(
                    _u_eti['Nome'].dropna().unique()
                ) if not _u_eti.empty and 'Nome' in _u_eti.columns else set()

                def _norm_nome(s):
                    s = str(s).strip().lower()
                    s = unicodedata.normalize('NFD', s)
                    s = s.encode('ascii', 'ignore').decode('ascii')
                    return re.sub(r'\s+', ' ', s)

                _nomes_ci  = {n.strip().lower(): n for n in _nomes_exact}
                _nomes_acc = {_norm_nome(n): n for n in _nomes_exact}

                # Lookups por NIF/NISS — mais fiáveis que o nome quando o
                # Eticadata usa o nome legal completo e o GestNow um nome
                # curto (ex.: "Ana Sofia Pires de Carvalho" vs "Ana Carvalho").
                def _digits(s):
                    return re.sub(r'\D', '', str(s))

                _nif_to_nome = {
                    _digits(v): n
                    for n, v in zip(_u_eti.get('Nome', []), _u_eti.get('NIF', []))
                    if _digits(v)
                } if not _u_eti.empty else {}
                _niss_to_nome = {
                    _digits(v): n
                    for n, v in zip(_u_eti.get('Nome', []), _u_eti.get('NISS', []))
                    if _digits(v)
                } if not _u_eti.empty else {}

                def _find_match_eti(nome_eti):
                    n = str(nome_eti).strip()
                    if n in _nomes_exact:                  # a. exacto
                        return n
                    ci = _nomes_ci.get(n.lower())
                    if ci:                                 # b. case-insensitive
                        return ci
                    acc = _nomes_acc.get(_norm_nome(n))
                    if acc:                                # c. sem acentos
                        return acc
                    # d. primeiro + último nome normalizados
                    parts = _norm_nome(n).split()
                    if len(parts) >= 2:
                        fl = f"{parts[0]} {parts[-1]}"
                        for gn in _nomes_exact:
                            gp = _norm_nome(gn).split()
                            if len(gp) >= 2 and f"{gp[0]} {gp[-1]}" == fl:
                                return gn
                    return None

                def _find_match_full(nome_eti, rh_v):
                    # Prioridade: NIF → NISS → variações do nome
                    nif_e = _digits(rh_v.get("NIF", ""))
                    if nif_e and nif_e in _nif_to_nome:
                        return _nif_to_nome[nif_e]
                    niss_e = _digits(rh_v.get("NISS", ""))
                    if niss_e and niss_e in _niss_to_nome:
                        return _niss_to_nome[niss_e]
                    return _find_match_eti(nome_eti)

                # ── Preview com status de match ────────────────────
                _prev_rows = []
                for _, _er in _eti_df.iterrows():
                    _nem = _er.get(_nome_col_eti, "")
                    _rh_p, _, _, _ = _etica_map_row(_er)
                    _ng  = _find_match_full(_nem, _rh_p)
                    _prev_rows.append({
                        "Status":         "✅ Match" if _ng else "⚠️ Sem match",
                        "Nome Eticadata": _nem,
                        "Nome GestNow":   _ng or "—",
                        "Salário Base":   _rh_p.get("Salario_Base", ""),
                        "Tipo Contrato":  _rh_p.get("Tipo_Contrato", ""),
                        "Data Admissão":  _rh_p.get("Data_Admissao", ""),
                        "Género":         _rh_p.get("Genero", ""),
                        "Nacionalidade":  _rh_p.get("Nacionalidade", ""),
                    })

                _prev_df   = pd.DataFrame(_prev_rows)
                _n_match   = int((_prev_df["Status"] == "✅ Match").sum())
                _n_nomatch = int((_prev_df["Status"] == "⚠️ Sem match").sum())

                _mc1, _mc2 = st.columns(2)
                _mc1.metric("✅ Com match", _n_match)
                _mc2.metric("⚠️ Sem match", _n_nomatch)

                st.markdown("#### 📋 Pré-visualização — todos os colaboradores")
                st.dataframe(_prev_df, use_container_width=True, height=400)

                if _n_nomatch > 0:
                    with st.expander(f"🆕 {_n_nomatch} sem match — serão criados como novos"):
                        for _sn in _prev_df[
                            _prev_df["Status"] == "⚠️ Sem match"
                        ]["Nome Eticadata"].tolist():
                            st.markdown(f"- `{_sn}`")

                st.markdown("---")

                _btn_label = (
                    f"🚀 Importar: {_n_match} actualiz."
                    + (f" + {_n_nomatch} novos" if _n_nomatch else "")
                )
                if _n_match == 0 and _n_nomatch == 0:
                    st.warning("⚠️ Nenhum registo encontrado no CSV.")
                else:
                    if st.button(
                        _btn_label,
                        key="imp_importar", type="primary",
                        use_container_width=True
                    ):
                        _df_rh    = _load_rh_fresh()
                        _df_users = _load_users_fresh()
                        logger.info(f"DEBUG A: _df_rh inicial = {len(_df_rh)} linhas")
                        _n_act    = 0
                        _n_new    = 0
                        _n_campos = 0
                        _novos_criados = []

                        for _, _er in _eti_df.iterrows():
                            _nem   = _er.get(_nome_col_eti, "")
                            _rh_v, _u_emp, _u_alw, _chefe = _etica_map_row(_er)
                            _ng    = _find_match_full(_nem, _rh_v)

                            if _ng:
                                _mu = (
                                    (_df_users['Nome'] == _ng)
                                    if not _df_users.empty and 'Nome' in _df_users.columns
                                    else pd.Series([], dtype=bool)
                                )

                                # Campos já existentes em usuarios.csv que devem
                                # ficar também visíveis em colaboradores_rh.csv
                                # (tab "Dados Legais")
                                _sync_fields = {}
                                if _mu.any():
                                    _u_row = _df_users.loc[_mu].iloc[0]
                                    for _fk in (
                                        "NISS", "CC", "CC_Validade", "Email",
                                        "Morada", "Localidade", "Codigo_Postal",
                                        "Banco_IBAN", "NIF",
                                    ):
                                        _uv = str(_u_row.get(_fk, "")).strip()
                                        if _uv:
                                            _sync_fields[_fk] = _uv

                                # Campos do Eticadata (sempre reescritos nesta
                                # importação — nunca acumulam valores de
                                # importações anteriores). Se o Eticadata vier
                                # vazio para um campo partilhado, cai-se para
                                # o valor de usuarios.csv.
                                _etica_keys = set(_rh_v.keys())
                                _rh_full = dict(_sync_fields)
                                for _k in _etica_keys:
                                    _vv = _rh_v.get(_k, "")
                                    _rh_full[_k] = _vv if _vv else _sync_fields.get(_k, "")

                                # Actualizar colaboradores_rh.csv — match robusto:
                                # 1º por Eticadata_ID (intCodigo, estável e único);
                                # 2º por NIF/NISS (partilhados com usuarios.csv);
                                # 3º fallback por Nome normalizado (sem acentos/maiúsc./espaços)
                                _eti_id  = str(_rh_v.get("Eticadata_ID", "")).strip()
                                _eti_nif  = _digits(_rh_v.get("NIF", ""))
                                _eti_niss = _digits(_rh_v.get("NISS", ""))
                                if _df_rh.empty:
                                    _mrh = pd.Series([], dtype=bool)
                                else:
                                    _mrh = pd.Series(False, index=_df_rh.index)
                                    if _eti_id and 'Eticadata_ID' in _df_rh.columns:
                                        _mrh = (
                                            _df_rh['Eticadata_ID'].astype(str).str.strip()
                                            == _eti_id
                                        )
                                    if not _mrh.any() and _eti_nif and 'NIF' in _df_rh.columns:
                                        _mrh = (
                                            _df_rh['NIF'].apply(_digits) == _eti_nif
                                        )
                                    if not _mrh.any() and _eti_niss and 'NISS' in _df_rh.columns:
                                        _mrh = (
                                            _df_rh['NISS'].apply(_digits) == _eti_niss
                                        )
                                    if not _mrh.any() and 'Nome' in _df_rh.columns:
                                        _mrh = (
                                            _df_rh['Nome'].apply(_norm_nome)
                                            == _norm_nome(_ng)
                                        )
                                if _mrh.any():
                                    for _k, _vv in _rh_full.items():
                                        if _k not in _df_rh.columns:
                                            _df_rh[_k] = ""
                                        if _k in CAMPOS_PROTEGIDOS_RH:
                                            _atual_v = str(_df_rh.loc[_mrh, _k].iloc[0]).strip()
                                            if _atual_v:
                                                continue
                                        _df_rh.loc[_mrh, _k] = _vv
                                        _n_campos += 1
                                else:
                                    _novo_rh = {c: "" for c in COLS_RH}
                                    _novo_rh['Nome'] = _ng
                                    _novo_rh.update(_rh_full)
                                    _df_rh = pd.concat(
                                        [_df_rh, pd.DataFrame([_novo_rh])],
                                        ignore_index=True
                                    )

                                # Actualizar usuarios.csv
                                if _mu.any():
                                    for _k, _vv in _u_emp.items():
                                        if _vv:
                                            if _k not in _df_users.columns:
                                                _df_users[_k] = ""
                                            if not str(_df_users.loc[_mu, _k].iloc[0]).strip():
                                                _df_users.loc[_mu, _k] = _vv
                                                _n_campos += 1
                                    for _k, _vv in _u_alw.items():
                                        if _vv:
                                            if _k not in _df_users.columns:
                                                _df_users[_k] = ""
                                            _df_users.loc[_mu, _k] = _vv
                                            _n_campos += 1
                                    if _chefe and 'Tipo' in _df_users.columns:
                                        _tipo_cur = str(_df_users.loc[_mu, 'Tipo'].iloc[0]).strip()
                                        if _tipo_cur not in ("Admin","Secretariado","Armazém","Cliente"):
                                            _df_users.loc[_mu, 'Tipo'] = "Chefe de Equipa"
                                _n_act += 1

                            else:
                                # Criar novo colaborador
                                _partes = str(_nem).strip().split()
                                _primeiro = _partes[0].capitalize() if _partes else "User"
                                _pwd_plain = f"{_primeiro}1234"
                                _novo_id   = str(uuid.uuid4())[:8].upper()

                                _novo_u = {
                                    "ID":              _novo_id,
                                    "Nome":            _nem,
                                    "Tipo":            "Chefe de Equipa" if _chefe else "Técnico",
                                    "Cargo":           "Técnico Instrumentação",
                                    "Password":        hp(_pwd_plain),
                                    "PDFs_Validados":  "Não",
                                    "Perfil_Completo": "",
                                    "Data_Criacao":    datetime.now().strftime("%d/%m/%Y %H:%M"),
                                }
                                for _k, _vv in _u_emp.items():
                                    if _vv:
                                        _novo_u[_k] = _vv
                                for _k, _vv in _u_alw.items():
                                    if _vv:
                                        _novo_u[_k] = _vv
                                _df_users = pd.concat(
                                    [_df_users, pd.DataFrame([_novo_u])],
                                    ignore_index=True
                                )

                                _novo_rh = {c: "" for c in COLS_RH}
                                _novo_rh['Nome'] = _nem
                                _novo_rh.update({k: v for k, v in _rh_v.items() if v})
                                _df_rh = pd.concat(
                                    [_df_rh, pd.DataFrame([_novo_rh])],
                                    ignore_index=True
                                )
                                _novos_criados.append({"Nome": _nem, "Password": _pwd_plain})
                                _n_new += 1

                            logger.info(f"DEBUG B: apos {_nem} -> _df_rh = {len(_df_rh)} linhas")

                        logger.info(f"DEBUG C: _df_rh FINAL antes save = {len(_df_rh)} linhas")

                        # Dedup defensivo — chave: Eticadata_ID se existir,
                        # senão Nome normalizado (sem acentos/maiúsculas/espaços)
                        if not _df_rh.empty:
                            def _rh_dedup_key(row):
                                _eid = str(row.get('Eticadata_ID', '')).strip()
                                return f"ID:{_eid}" if _eid else f"NOME:{_norm_nome(row.get('Nome', ''))}"

                            _df_rh['_dedup_key'] = _df_rh.apply(_rh_dedup_key, axis=1)
                            _df_rh = (
                                _df_rh.drop_duplicates(subset=['_dedup_key'], keep='last')
                                .drop(columns=['_dedup_key'])
                                .reset_index(drop=True)
                            )
                        logger.info(f"DEBUG D: _df_rh apos dedup = {len(_df_rh)} linhas")

                        _ok_rh = save_db(_df_rh, "colaboradores_rh.csv", permitir_reducao=True)
                        if not _ok_rh:
                            st.error("❌ Erro ao guardar colaboradores_rh.csv — "
                                     "verifica ligação ao GCS")
                            st.stop()

                        _ok_users = save_db(_df_users, "usuarios.csv")
                        if not _ok_users:
                            st.error("❌ Erro ao guardar usuarios.csv — "
                                     "verifica ligação ao GCS")
                            st.stop()

                        inv("colaboradores_rh.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        log_audit(
                            usuario=admin_nome,
                            acao="IMPORTAR_ETICADATA",
                            tabela="colaboradores_rh.csv+usuarios.csv",
                            registro_id="batch",
                            detalhes=(f"Actualizados: {_n_act}, "
                                      f"Novos: {_n_new}, "
                                      f"Campos: {_n_campos}"),
                            ip=""
                        )
                        st.session_state['eticadata_result'] = {
                            'n_act': _n_act, 'n_new': _n_new,
                            'n_campos': _n_campos, 'novos': _novos_criados,
                        }
                        del st.session_state['eticadata_df']
                        # incrementar chave força o file_uploader a renderizar
                        # sem ficheiro no próximo rerun — evita recriar eticadata_df
                        st.session_state['eti_upload_key'] = st.session_state.get('eti_upload_key', 0) + 1
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 5 — CONTRATOS
    # ════════════════════════════════════════════════════════════════
    with tab_contrato:
        users_ct = _load_users_fresh()
        if users_ct.empty:
            st.info("Sem colaboradores.")
            return

        nomes_ct    = users_ct['Nome'].tolist()
        colab_ct    = st.session_state.get('rh_colaborador_sel', nomes_ct[0])
        idx_ct      = nomes_ct.index(colab_ct) if colab_ct in nomes_ct else 0
        nome_ct_sel = st.selectbox("Colaborador",
            nomes_ct, index=idx_ct, key="ct_colab_sel")

        match_ct = users_ct[users_ct['Nome'] == nome_ct_sel]
        if match_ct.empty:
            st.warning("Colaborador não encontrado.")
            return
        row_ct = match_ct.iloc[0]

        # ── Estado do contrato ────────────────────────────────────
        ct_gerado    = row_ct.get('Contrato_Gerado','')    == 'Sim'
        ct_enviado   = row_ct.get('Contrato_Enviado','')   == 'Sim'
        ct_assinado  = row_ct.get('Contrato_Assinado','')  == 'Sim'
        ct_validado  = row_ct.get('Contrato_Validado_Admin','') == 'Sim'

        passos_ct = [
            ("📄 Gerado",    ct_gerado,   row_ct.get('Contrato_Data','')),
            ("📤 Enviado",   ct_enviado,  row_ct.get('Contrato_Enviado_Data','')),
            ("✍️ Assinado",  ct_assinado, row_ct.get('Contrato_Assinatura_Data','')),
            ("✅ Validado",  ct_validado, row_ct.get('Contrato_Validado_Data','')),
        ]

        col_ps = st.columns(4)
        for col_p, (label, feito, data_p) in zip(col_ps, passos_ct):
            with col_p:
                cor_p = "#10B981" if feito else "#334155"
                st.markdown(
                    f"<div style='background:{cor_p}22;border:2px solid {cor_p};"
                    f"border-radius:10px;padding:10px;text-align:center;'>"
                    f"<p style='color:{cor_p};font-weight:700;"
                    f"font-size:0.8rem;margin:0;'>{label}</p>"
                    f"<p style='color:#64748B;font-size:0.68rem;margin:3px 0 0;'>"
                    f"{data_p or '—'}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        # ── Verificar dados completos ─────────────────────────────
        campos_necessarios = ["NIF","NISS","CC","CC_Validade","Morada"]
        dados_em_falta = [c for c in campos_necessarios
                          if not row_ct.get(c,'').strip()]

        if dados_em_falta:
            st.warning(
                f"⚠️ Perfil incompleto para gerar contrato. "
                f"Em falta: **{', '.join(dados_em_falta)}**"
            )

        # ── PASSO 1: Gerar contrato ───────────────────────────────
        if not ct_gerado:
            template_ok = _gcs_read_binary("contrato_template.docx") is not None

            if not template_ok:
                st.error("❌ Template do contrato não encontrado. "
                         "Faz upload do template no separador '⚙️ Templates'.")
            else:
                st.markdown("#### 📄 Gerar Contrato")
                st.info(
                    "Os dados pessoais são preenchidos automaticamente "
                    "a partir do perfil do colaborador."
                )

                with st.form("form_gerar_ct"):
                    c1, c2 = st.columns(2)
                    with c1:
                        ct_local = st.text_input(
                            "Local da obra *",
                            value=row_ct.get('Local_Obra',''),
                            key="ct_local"
                        )
                        ct_data_inicio = st.date_input(
                            "Data de início *",
                            value=date.today(), key="ct_data_ini"
                        )
                    with c2:
                        ct_cliente = st.text_input(
                            "Cliente *",
                            value=row_ct.get('Cliente_Obra',''),
                            key="ct_cliente"
                        )
                        ct_data_doc = st.date_input(
                            "Data do documento",
                            value=date.today(), key="ct_data_doc"
                        )

                    if st.form_submit_button("📄 Gerar Contrato",
                        use_container_width=True, type="primary"):
                        if not ct_local or not ct_cliente:
                            st.error("❌ Local e Cliente são obrigatórios.")
                        else:
                            morada_completa = " ".join(filter(None, [
                                row_ct.get('Morada',''),
                                row_ct.get('Localidade',''),
                                row_ct.get('Codigo_Postal','')
                            ]))

                            subs = {
                                "{{nome}}":                         row_ct.get('Nome',''),
                                "{{morada}}":                       morada_completa,
                                "{{NIF}}":                          row_ct.get('NIF',''),
                                "{{NISS}}":                         row_ct.get('NISS',''),
                                "{{número de cartão de cidadão}}":  row_ct.get('CC',''),
                                "{{validade do cartão de cidadão}}":row_ct.get('CC_Validade',''),
                                "{{categoria profissional}}":       row_ct.get('Cargo',''),
                                "{{local}}":                        ct_local,
                                "{{Cliente}}":                      ct_cliente,
                                "{{data}}":                         ct_data_doc.strftime("%d de %B de %Y"),
                                "4 de Março de 2026":               ct_data_inicio.strftime("%d de %B de %Y"),
                            }

                            docx_bytes = _fill_contrato_template(subs)
                            if docx_bytes:
                                docx_b64 = base64.b64encode(docx_bytes).decode()
                                u_ct = _load_users_fresh()
                                mask = u_ct['Nome'] == nome_ct_sel
                                if mask.any():
                                    u_ct.loc[mask, 'Contrato_Gerado']  = 'Sim'
                                    u_ct.loc[mask, 'Contrato_Data']    = \
                                        datetime.now().strftime("%d/%m/%Y %H:%M")
                                    u_ct.loc[mask, 'Contrato_b64']     = docx_b64
                                    u_ct.loc[mask, 'Contrato_Local_Obra']   = ct_local
                                    u_ct.loc[mask, 'Contrato_Cliente_Obra'] = ct_cliente
                                    save_db(u_ct, "usuarios.csv")
                                    inv("usuarios.csv")
                                    from core import _cached_load_all
                                    _cached_load_all.clear()
                                    log_audit(
                                        usuario=admin_nome,
                                        acao="GERAR_CONTRATO",
                                        tabela="usuarios.csv",
                                        registro_id=row_ct.get('ID',''),
                                        detalhes=f"Contrato gerado para {nome_ct_sel}",
                                        ip=""
                                    )
                                    st.success("✅ Contrato gerado com sucesso!")
                                    st.rerun()
                            else:
                                st.error("❌ Erro ao gerar contrato. "
                                         "Verifica o template.")

        # ── PASSO 2: Download + Enviar ao colaborador ─────────────
        if ct_gerado and not ct_enviado:
            st.markdown("#### 📤 Rever e Enviar ao Colaborador")
            ct_b64 = row_ct.get('Contrato_b64','')
            if ct_b64:
                try:
                    ct_bytes = base64.b64decode(ct_b64)
                    st.download_button(
                        "📥 Descarregar contrato para rever",
                        data=ct_bytes,
                        file_name=f"contrato_{nome_ct_sel.replace(' ','_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument"
                             ".wordprocessingml.document",
                        key="btn_dl_contrato_admin"
                    )
                except:
                    st.error("Erro ao processar o contrato.")
                    
             # ── Re-upload do contrato editado ─────────────────
                st.markdown("##### 📤 Substituir contrato (versão editada)")
                ct_novo = st.file_uploader(
                    "Upload do contrato editado (.docx ou .pdf)",
                    type=["docx","pdf"],
                    key="ct_reupload"
                )
                if ct_novo:
                    if st.button("💾 Guardar versão editada",
                                  key="btn_guardar_ct_editado",
                                  use_container_width=True):
                        novo_b64 = base64.b64encode(ct_novo.read()).decode()
                        u_re = _load_users_fresh()
                        mask = u_re['Nome'] == nome_ct_sel
                        if mask.any():
                            u_re.loc[mask, 'Contrato_b64'] = novo_b64
                            save_db(u_re, "usuarios.csv")
                            inv("usuarios.csv")
                            from core import _cached_load_all
                            _cached_load_all.clear()
                            st.success("✅ Contrato atualizado com a versão editada!")
                            st.rerun()

                st.markdown("---")       

            col_env1, col_env2 = st.columns(2)
            with col_env1:
                if st.button("📤 Marcar como Enviado ao Colaborador",
                              key="btn_enviar_ct", type="primary",
                              use_container_width=True):
                    u_ct2 = _load_users_fresh()
                    mask  = u_ct2['Nome'] == nome_ct_sel
                    if mask.any():
                        u_ct2.loc[mask, 'Contrato_Enviado']      = 'Sim'
                        u_ct2.loc[mask, 'Contrato_Enviado_Data'] = \
                            datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(u_ct2, "usuarios.csv")
                        criar_notificacao(
                            destinatario=nome_ct_sel,
                            titulo="📄 Contrato disponível",
                            mensagem="O teu contrato de trabalho está disponível "
                                     "para assinar. Acede ao teu Perfil para descarregar.",
                            tipo="info",
                            acao_url="/perfil?tab=contrato"
                        )
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        st.success("✅ Colaborador notificado!")
                        st.rerun()
            with col_env2:
                if st.button("🔄 Regenerar Contrato",
                              key="btn_regen_ct",
                              use_container_width=True):
                    u_ct2 = _load_users_fresh()
                    mask  = u_ct2['Nome'] == nome_ct_sel
                    if mask.any():
                        for campo in ['Contrato_Gerado','Contrato_Data',
                                      'Contrato_b64','Contrato_Enviado',
                                      'Contrato_Enviado_Data']:
                            u_ct2.loc[mask, campo] = ''
                        save_db(u_ct2, "usuarios.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        st.rerun()

        # ── PASSO 3: Aguarda assinatura do colaborador ────────────
        if ct_enviado and not ct_assinado:
            st.info(
                "⏳ **Aguarda assinatura** — O colaborador recebeu o contrato "
                "e deve assinar fisicamente, fotografar e fazer upload na app."
            )

        # ── PASSO 4: Validar assinatura ───────────────────────────
        if ct_assinado and not ct_validado:
            st.markdown("#### ✅ Validar Assinatura do Colaborador")
            assin_b64 = row_ct.get('Contrato_Assinatura_b64','')
            if assin_b64:
                try:
                    assin_bytes = base64.b64decode(assin_b64)
                    st.download_button(
                        "📥 Ver contrato assinado pelo colaborador",
                        data=assin_bytes,
                        file_name=f"contrato_assinado_{nome_ct_sel.replace(' ','_')}.pdf",
                        mime="application/octet-stream",
                        key="btn_dl_assinado"
                    )
                except:
                    st.error("Erro ao processar o ficheiro.")

            col_val1, col_val2 = st.columns(2)
            with col_val1:
                if st.button("✅ Validar e Arquivar",
                              key="btn_validar_ct", type="primary",
                              use_container_width=True):
                    u_ct3 = _load_users_fresh()
                    mask  = u_ct3['Nome'] == nome_ct_sel
                    if mask.any():
                        u_ct3.loc[mask, 'Contrato_Validado_Admin'] = 'Sim'
                        u_ct3.loc[mask, 'Contrato_Validado_Data']  = \
                            datetime.now().strftime("%d/%m/%Y %H:%M")
                        save_db(u_ct3, "usuarios.csv")
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        criar_notificacao(
                            destinatario=nome_ct_sel,
                            titulo="✅ Contrato Validado",
                            mensagem="O teu contrato foi validado e está arquivado.",
                            tipo="success",
                            acao_url="/perfil?tab=contrato"
                        )
                        log_audit(
                            usuario=admin_nome,
                            acao="VALIDAR_CONTRATO",
                            tabela="usuarios.csv",
                            registro_id=row_ct.get('ID',''),
                            detalhes=f"Contrato validado para {nome_ct_sel}",
                            ip=""
                        )
                        st.success("✅ Contrato arquivado!")
                        st.rerun()
            with col_val2:
                if st.button("❌ Recusar (pedir nova assinatura)",
                              key="btn_recusar_ct",
                              use_container_width=True):
                    u_ct3 = _load_users_fresh()
                    mask  = u_ct3['Nome'] == nome_ct_sel
                    if mask.any():
                        for campo in ['Contrato_Assinado',
                                      'Contrato_Assinatura_b64',
                                      'Contrato_Assinatura_Data']:
                            u_ct3.loc[mask, campo] = ''
                        save_db(u_ct3, "usuarios.csv")
                        criar_notificacao(
                            destinatario=nome_ct_sel,
                            titulo="⚠️ Assinatura Recusada",
                            mensagem="A assinatura do contrato foi recusada. "
                                     "Por favor, assina novamente e faz upload.",
                            tipo="error",
                            acao_url="/perfil?tab=contrato"
                        )
                        inv("usuarios.csv")
                        from core import _cached_load_all
                        _cached_load_all.clear()
                        st.warning("Colaborador notificado para nova assinatura.")
                        st.rerun()

        # ── PASSO 5: Arquivo final ────────────────────────────────
        if ct_validado:
            st.success("✅ **Contrato arquivado e validado.**")
            ct_b64_f = row_ct.get('Contrato_b64','')
            if ct_b64_f:
                try:
                    ct_bytes_f = base64.b64decode(ct_b64_f)
                    st.download_button(
                        "📥 Descarregar contrato original",
                        data=ct_bytes_f,
                        file_name=f"contrato_final_{nome_ct_sel.replace(' ','_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument"
                             ".wordprocessingml.document",
                        key="btn_dl_ct_final"
                    )
                except:
                    pass

    # ════════════════════════════════════════════════════════════════
    # TAB 6 — TEMPLATES & CONFIG
    # ════════════════════════════════════════════════════════════════
    with tab_template:
        st.markdown("### ⚙️ Template do Contrato")

        template_existe = _gcs_read_binary("contrato_template.docx") is not None
        if template_existe:
            st.success("✅ Template do contrato carregado no sistema.")
        else:
            st.warning("⚠️ Nenhum template carregado. "
                       "Faz upload abaixo para activar a geração automática.")

        st.markdown("#### 📤 Upload do Template")
        st.info(
            "O template deve ser um ficheiro `.docx` com os campos marcados como:\n"
            "`{{nome}}` `{{morada}}` `{{NIF}}` `{{NISS}}` "
            "`{{número de cartão de cidadão}}` `{{validade do cartão de cidadão}}` "
            "`{{categoria profissional}}` `{{local}}` `{{Cliente}}` `{{data}}`"
        )

        if template_existe:
            st.warning(
                "⚠️ Já existe um template. Fazer upload de um novo **substitui** o atual."
            )

        template_file = st.file_uploader(
            "Selecionar novo template .docx",
            type=["docx"],
            key="upload_template_ct"
        )
        if template_file:
            acao_label = "🔄 Substituir Template Atual" if template_existe \
                         else "💾 Guardar Template"
            if st.button(acao_label,
                          key="btn_guardar_template",
                          type="primary", use_container_width=True):
                ok = _gcs_write_binary(
                    template_file.read(), "contrato_template.docx"
                )
                if ok:
                    st.success("✅ Template guardado no sistema!")
                    log_audit(
                        usuario=admin_nome,
                        acao="UPLOAD_TEMPLATE_CONTRATO",
                        tabela="GCS",
                        registro_id="contrato_template.docx",
                        detalhes="Template do contrato atualizado",
                        ip=""
                    )
                    st.rerun()
                else:
                    st.error("❌ Erro ao guardar o template.")

        if template_existe:
            st.markdown("---")
            st.markdown("#### 📥 Descarregar Template Atual")
            template_bytes = _gcs_read_binary("contrato_template.docx")
            if template_bytes:
                st.download_button(
                    "📥 Descarregar template atual",
                    data=template_bytes,
                    file_name="contrato_template.docx",
                    mime="application/vnd.openxmlformats-officedocument"
                         ".wordprocessingml.document",
                    key="btn_dl_template"
                )

    # ════════════════════════════════════════════════════════════════
    # TAB 7 — FORMAÇÕES
    # ════════════════════════════════════════════════════════════════
    with tab_formacoes:
        from mod_admin_formacoes import render_formacoes
        render_formacoes(users, obras_db)

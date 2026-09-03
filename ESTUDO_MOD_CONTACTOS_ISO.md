# ESTUDO TÉCNICO — Módulo de Rastreabilidade de Contactos
## GestNow v3 | ISO 9001:2015 — Cláusula 8.2 (Requisitos do Cliente)
**Preparado:** 05/06/2026 | **Para trabalhar:** 06/06/2026

---

## 1. PROBLEMA A RESOLVER

Para ISO 9001, a cláusula 8.2 exige que a organização **determine, analise e reveja** os requisitos relacionados com os produtos e serviços — e isso começa no **primeiro contacto com o cliente**.

Hoje o GestNow não tem forma de provar a um auditor:
- Quando foi o primeiro contacto
- Quem contactou / quem recebeu
- Por que canal (telefone, email, concurso, etc.)
- Qual é a evidência documental desse contacto

---

## 2. FLUXO COMPLETO DE RASTREABILIDADE

```
CONTACTO INICIAL
────────────────
Data + Hora + Canal + Pessoa + Evidência (foto/PDF/screenshot)
        │
        ▼
OPORTUNIDADE (já existe no mod_admin_comercial.py)
────────────────────────────────────────────────
Ligada ao Contacto_ID → rastreável de volta à origem
        │
        ▼
ORÇAMENTO (mod_admin_orcamentacao.py)
─────────────────────────────────────
Campo Oportunidade_ID → liga ao orçamento
        │
        ▼
OBRA (obras_lista.csv)
──────────────────────
Campo Orcamento_ID → rastreabilidade completa ponta a ponta
```

Para auditor ISO: um clique mostra todo o histórico.

---

## 3. ESTRUTURA DE DADOS — NOVO CSV

### Ficheiro: `com_contactos.csv`

| Campo | Tipo | Descrição | Obrigatório |
|-------|------|-----------|-------------|
| `ID` | string | UUID único | ✅ |
| `Data` | dd/mm/aaaa | Data do contacto | ✅ |
| `Hora` | HH:MM | Hora do contacto | ✅ |
| `Canal` | enum | Ver lista abaixo | ✅ |
| `Sentido` | enum | Entrada / Saída | ✅ |
| `Cliente_Nome` | string | Nome da empresa | ✅ |
| `Contacto_Nome` | string | Nome da pessoa | ✅ |
| `Contacto_Telefone` | string | Nº telefone | — |
| `Contacto_Email` | string | Email | — |
| `Assunto` | string | Assunto / motivo | ✅ |
| `Resumo` | text | Resumo do contacto | ✅ |
| `Responsavel` | string | Quem recebeu/fez | ✅ |
| `Evidencia_Tipo` | enum | Print/PDF/Foto/Nenhuma | ✅ |
| `Evidencia_Path` | string | Path no GCS | — |
| `Oportunidade_ID` | string | Liga à oportunidade | — |
| `Estado` | enum | Aberto/Em Seguimento/Fechado | ✅ |
| `Proximo_Passo` | string | Próxima acção | — |
| `Data_Proximo_Passo` | dd/mm/aaaa | Quando | — |
| `Notas` | text | Notas livres | — |

### Canais disponíveis:
- 📞 Telefone
- 📧 Email
- 💬 WhatsApp / Mensagem
- 🏆 Concurso Público
- 🤝 Visita Presencial
- 📋 Indicação / Referência
- 🌐 Website / LinkedIn
- 📮 Correio / Fax
- 🔄 Renovação de Contrato

---

## 4. GESTÃO DE EVIDÊNCIAS — PONTO CRÍTICO

### Problema técnico
O Streamlit + GCS suporta upload de ficheiros. Cada evidência é guardada no bucket `gestnow-dados` em:
```
gs://gestnow-dados/evidencias_contactos/{ID_CONTACTO}/{timestamp}_{filename}
```

### Tipos de evidência aceites
| Tipo | Extensão | Exemplo |
|------|----------|---------|
| Print de chamada | .jpg .png | Screenshot do telemóvel |
| Email | .pdf .eml | PDF do email exportado |
| Mensagem WhatsApp | .jpg .png | Screenshot da conversa |
| Documento concurso | .pdf | Caderno de encargos |
| Proposta recebida | .pdf .docx | Pedido de proposta |

### Função de upload (base para implementação)
```python
def _upload_evidencia(ficheiro, contacto_id: str) -> str:
    """
    Faz upload de evidência para GCS e devolve o path.
    Retorna: gs://gestnow-dados/evidencias_contactos/{id}/{filename}
    """
    from google.cloud import storage
    import datetime
    
    client  = storage.Client()
    bucket  = client.bucket("gestnow-dados")
    ts      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ext     = ficheiro.name.split('.')[-1].lower()
    blob_name = f"evidencias_contactos/{contacto_id}/{ts}_{ficheiro.name}"
    blob    = bucket.blob(blob_name)
    blob.upload_from_file(ficheiro, content_type=ficheiro.type)
    return f"gs://gestnow-dados/{blob_name}"

def _get_evidencia_url(gcs_path: str, expiry_minutes: int = 60) -> str:
    """Gera URL temporária para visualizar/descarregar evidência."""
    from google.cloud import storage
    import datetime
    
    if not gcs_path or not gcs_path.startswith("gs://"):
        return ""
    parts    = gcs_path.replace("gs://gestnow-dados/", "")
    client   = storage.Client()
    bucket   = client.bucket("gestnow-dados")
    blob     = bucket.blob(parts)
    url      = blob.generate_signed_url(
        expiration=datetime.timedelta(minutes=expiry_minutes),
        method="GET"
    )
    return url
```

---

## 5. ESTRUTURA DO MÓDULO — TABS

### Tab 1 — 📋 Contactos
Lista cronológica de todos os contactos com:
- Filtros: canal, estado, responsável, período
- Cada card mostra: canal (icon), cliente, pessoa, data/hora, responsável, estado
- Indicador visual se tem evidência anexa (✅) ou não (⚠️)
- Click para ver detalhe + evidência + oportunidade ligada

### Tab 2 — ➕ Registar Contacto
Formulário completo:
1. **Identificação** — data, hora, canal, sentido (entrada/saída)
2. **Cliente** — nome empresa, nome pessoa, telefone, email
   - Autocomplete a partir de `clientes_db` se já existir
3. **Conteúdo** — assunto, resumo (textarea), próximo passo + data
4. **Evidência** — upload de ficheiro (jpg/png/pdf) com preview inline
5. **Ligar a Oportunidade** — dropdown de oportunidades abertas (opcional)
6. Botão **💾 Guardar** — grava CSV + faz upload evidência para GCS

### Tab 3 — 🔗 Timeline por Cliente
Selecciona um cliente → vê timeline completa:
```
📞 15/03/2025 14:30 — Chamada entrada — João Silva (Repsol)
   └─ "Pedido de proposta para instalação transmissores"
   └─ 📎 print_chamada.jpg
   └─ → Oportunidade criada: ORC-2025-042
   
📧 20/03/2025 09:15 — Email saída — Proposta enviada
   └─ "Envio de proposta €45.000"
   └─ 📎 email_proposta.pdf
   └─ → Orçamento: ORC-2025-042-v1
   
✅ 02/04/2025 — Adjudicado
   └─ → Obra criada: Repsol Tarragona
```

### Tab 4 — 📊 Analytics ISO
KPIs específicos para ISO 9001:
- **Tempo médio de resposta** — do primeiro contacto até proposta enviada
- **Canal de origem** — gráfico de pizza: de onde vêm os negócios
- **Taxa de follow-up** — contactos com próximo passo definido vs sem
- **Contactos sem oportunidade** — lista dos que ficaram "no ar"
- **Evidências em falta** — contactos importantes sem prova documental

---

## 6. INTEGRAÇÃO COM MÓDULOS EXISTENTES

### No `mod_admin_comercial.py`
Ao criar uma nova oportunidade, adicionar campo opcional:
```python
origem_contacto_id = st.selectbox(
    "Contacto de Origem",
    contactos_sem_oportunidade,  # lista de contactos não ligados
    key="op_contacto_origem"
)
```

### No `mod_admin_orcamentacao.py`
No cabeçalho do orçamento, adicionar:
```python
# Campo já existe implicitamente via Obra — mas para ISO:
orc_oportunidade_id = st.text_input(
    "ID Oportunidade (rastreabilidade ISO)",
    key="orc_op_id"
)
```

### No `obras_lista.csv`
Adicionar colunas:
- `Orcamento_Origem` — ID do orçamento que gerou a obra
- `Oportunidade_Origem` — ID da oportunidade

---

## 7. RELATÓRIO ISO 9001 — EVIDÊNCIA DE AUDITORIA

Para gerar em PDF quando o auditor pede:

**"Mostre-me o processo desde o primeiro contacto até à execução da obra X"**

O sistema deve conseguir gerar um documento com:

```
RELATÓRIO DE RASTREABILIDADE — ISO 9001:2015 — Cláusula 8.2
═══════════════════════════════════════════════════════════

OBRA: Repsol Tarragona
CLIENTE: Repsol S.A.
PERÍODO: 15/03/2025 → 30/04/2025

1. PRIMEIRO CONTACTO
   Data: 15/03/2025 14:30
   Canal: Telefone (entrada)
   Pessoa: João Silva | +34 612 345 678
   Recebido por: [nome colaborador]
   Evidência: print_chamada_150325.jpg ✅

2. OPORTUNIDADE CRIADA
   ID: OP-2025-042
   Data: 15/03/2025
   Valor estimado: €45.000
   Responsável: [comercial]

3. ORÇAMENTO ENVIADO
   ID: ORC-2025-042-v1
   Data envio: 20/03/2025
   Valor: €47.250 (margem 5%)
   Evidência: email_proposta_200325.pdf ✅

4. ADJUDICAÇÃO
   Data: 28/03/2025
   Confirmação: email_adjudicacao.pdf ✅

5. OBRA CRIADA
   Data: 02/04/2025
   Código: ES.OBCM.001
   Estado: Activa

TEMPO TOTAL CONTACTO → ADJUDICAÇÃO: 13 dias
```

---

## 8. PONTOS DE ATENÇÃO PARA IMPLEMENTAÇÃO

### ⚠️ GCS — Upload de ficheiros
O Streamlit Cloud Run suporta `st.file_uploader`. O upload para GCS funciona via `google-cloud-storage` que já está no projecto. **Confirmar que as permissões do service account incluem `storage.objects.create` no bucket `gestnow-dados`.**

### ⚠️ Tamanho de ficheiros
Definir limite máximo de 5MB por evidência para não rebentar o Cloud Run. Aceitar: jpg, jpeg, png, pdf, eml.

### ⚠️ Privacidade / RGPD
Os prints de chamadas e emails contêm dados pessoais. Considerar:
- Acesso às evidências apenas para Admin e o próprio utilizador que registou
- Possibilidade de anonimizar ou eliminar evidências antigas

### ⚠️ Ligação ao `mod_admin_comercial.py`
O campo `Origem` já existe nas oportunidades mas não está a ser alimentado por um registo formal. A ideia é que o `com_contactos.csv` substitua esse campo informal.

---

## 9. FICHEIROS A CRIAR / MODIFICAR

| Acção | Ficheiro | Descrição |
|-------|----------|-----------|
| **CRIAR** | `mod_contactos_iso.py` | Módulo novo completo |
| **CRIAR** | `com_contactos.csv` | Base de dados de contactos |
| **MODIFICAR** | `mod_admin_comercial.py` | Adicionar ligação a contacto de origem |
| **MODIFICAR** | `mod_admin_orcamentacao.py` | Campo Oportunidade_ID |
| **MODIFICAR** | `obras_lista.csv` | Colunas Orcamento_Origem + Oportunidade_Origem |
| **MODIFICAR** | `core.py` | `com_contactos.csv` em `_LOAD_ALL_FILES` |
| **MODIFICAR** | `app.py` | Adicionar tab/menu para o novo módulo |

---

## 10. ORDEM DE TRABALHO SUGERIDA PARA AMANHÃ

1. **Criar `mod_contactos_iso.py`** — pedir ao Claude Code com este estudo como contexto
2. **Testar upload de evidência** — verificar permissões GCS
3. **Modificar `mod_admin_comercial.py`** — campo de ligação ao contacto
4. **Adicionar à navegação do `app.py`**
5. **Testar fluxo completo** — registar contacto → criar oportunidade → orçamento → obra
6. **Gerar relatório PDF de rastreabilidade** de teste

---

*Estudo preparado para sessão 06/06/2026*
*Módulo: GestNow — CPS Smart Solutions*

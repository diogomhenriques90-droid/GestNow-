# Briefing técnico — Ficha de Obra centralizada (GestNow)

**Para:** implementação via Claude Code no projeto GestNow (`gestnow-v3`)
**Objetivo:** centralizar toda a informação operacional de uma obra numa única ficha, puxando automaticamente (por referência, não por cópia) os dados que já existem nas fichas de colaboradores e de contactos, evitando duplicação e erros de preenchimento.

> **Nota de método:** este documento é um *briefing*, não uma ordem de implementação. O passo seguinte é o Claude Code produzir um **plano faseado** (sem escrever código), para revisão e aprovação antes de qualquer alteração. Produção em uso e auditoria ISO a decorrer — aplicar as regras do projeto (ver secção 6).

---

## 1. Princípio arquitetural central — referência vs. duplicação

O objetivo declarado é **evitar duplicação de registos**. Isso obriga a uma decisão de desenho que tem de ser respeitada em toda a implementação:

- A obra **guarda apenas referências** (IDs) para colaboradores, cliente e contacto — **não copia** os valores (nome, valor/hora, telefone, etc.) para dentro de `obras_lista.csv`.
- Os valores "puxados automaticamente" (Grupos B e C) são **resolvidos no momento da apresentação** (no detalhe da obra), lendo a ficha de origem em tempo real.
- Assim, se mudar o contacto de um cliente ou a função de um colaborador, a obra reflete sempre o valor atual, sem cópias desatualizadas espalhadas.

**Regra:** Grupo A = dados próprios da obra (escritos em `obras_lista.csv`). Grupos B e C = leitura/junção a partir de outras fichas; **nunca escritos como cópia na obra**.

---

## 2. Grupo A — campos guardados na própria obra (`obras_lista.csv`)

Campos que pertencem à obra e são preenchidos no formulário (dashboard):

| Campo | Tipo | Notas |
|---|---|---|
| Cliente | referência | ID do cliente (de `clientes_financeiro.csv`). Já assume da ficha existente. |
| Nº de colaboradores | **derivado** | ⚠️ Não deve ser campo manual — ver Alerta 1. Calcular a partir das alocações. |
| Data de início | data | |
| Data prevista de término | data | |
| Estado da obra | lista | Coerente com a coluna de estado já existente (`Ativa`/`Inativa` + estados de fase, a confirmar). |
| Responsável de Equipa | referência | ID de colaborador (de `usuarios.csv`). |
| Elementos da Equipa | referência (lista) | Lista de IDs de colaboradores — ver Alerta 1 (relação alocações). |
| Diária | lista | Corrida / Semanal / Outro |
| Alojamento | lista | CPS / Cliente / Outro |
| Viatura | lista | CPS / Cliente / Outro |
| Ferramentas | lista | CPS / Cliente / Outro |
| EPIs | lista | CPS / Cliente / Outro |
| Descrição dos Trabalhos | texto | campo aberto |
| Requisitos Adicionais | texto | campo aberto |
| Plataforma | texto | campo aberto |
| Formações Obrigatórias | texto | campo aberto |

---

## 3. Grupo B — campos puxados da ficha do colaborador (detalhe da obra)

Resolvidos por referência ao colaborador (`usuarios.csv` e/ou `colaboradores_rh.csv`), apresentados no detalhe, **não copiados** para a obra:

| Campo pedido | Origem provável | Notas |
|---|---|---|
| Gestor de Obra | ficha do colaborador | confirmar coluna |
| Contacto do Responsável de Equipa | ficha do colaborador | telefone/email do colaborador responsável |
| Contacto dos Elementos | ficha do colaborador | por cada elemento alocado |
| Função dos Elementos | `usuarios.csv` (`Funcao`/`Categoria_Operacional`) | já existem estes campos |
| Valor Hora dos Elementos | ⚠️ **ver Alerta 2** | **não** é atributo do colaborador |
| Valor da Diária | a definir | confirmar se é por obra ou por alocação |

---

## 4. Grupo C — campos puxados da ficha do contacto do cliente

Resolvidos por referência ao contacto (`com_contactos.csv`), apresentados no detalhe:

| Campo pedido | Origem provável | Notas |
|---|---|---|
| Pessoa de Contacto | `com_contactos.csv` | confirmar coluna do nome |
| Email do Contacto | `com_contactos.csv` | |
| Telefone do Contacto | `com_contactos.csv` | |

Implica que a obra guarde uma **referência ao contacto** (Contacto_ID), encaixando na cadeia de rastreabilidade ISO já existente (Contacto_ID → Oportunidade_ID → Orçamento_ID → Obra).

---

## 5. ⚠️ Alertas — conflitos a resolver ANTES de codificar

**Alerta 1 — "Nº de colaboradores" e "Elementos da Equipa" não devem ser campos manuais duplicados.**
A relação colaborador↔obra já vive nas **alocações** (`inst_acessos.csv`). Se a ficha de obra guardar também uma lista manual de elementos e um número, ficas com **dois sítios a dizer a mesma coisa** — exatamente a duplicação que queres evitar. Recomendação: "Elementos da Equipa" e "Nº de colaboradores" devem **derivar das alocações**, não ser reescritos na obra. Decisão a tomar: a ficha de obra passa a ser a interface para *gerir* essas alocações, ou continua a haver um módulo de Alocações à parte?

**Alerta 2 — "Valor Hora dos Elementos" NÃO é um dado da ficha do colaborador.**
Regra arquitetural já estabelecida no projeto: **`PrecoHora` é um atributo da alocação (por obra), não do colaborador**, e não existe (nem deve existir) sincronização entre `usuarios.csv` e `inst_acessos.csv`. Portanto, o "Valor Hora" tem de ser lido da **alocação** (`inst_acessos.csv`), não da ficha do colaborador. O briefing original coloca-o no grupo errado — corrigir.

**Alerta 3 — "Valor da Diária".**
Clarificar se a diária (valor) é definida ao nível da obra (parece ser, dado que "Diária: Corrida/Semanal/Outro" é campo da obra) ou por alocação. Definir a fonte única antes de implementar.

---

## 6. Regras do projeto a respeitar (não negociáveis)

- **Ficheiros tocados:** `obras_lista.csv` (escrita), `usuarios.csv`, `colaboradores_rh.csv`, `com_contactos.csv`, `inst_acessos.csv`, `clientes_financeiro.csv` (leitura/junção).
- `usuarios.csv` tem **risco de multi-escritor** (vários módulos): qualquer escrita exige guardas explícitas.
- `inst_acessos.csv` e `colaboradores_rh.csv` **não estão** em `_CRITICAL_FILES` → exigem guardas próprias.
- **Sem `.strip()` em valores** (preserva b64/JSON).
- `log_audit`: o campo `detalhes` só pode conter **nomes de colunas, nunca valores**.
- `rh_ativos` (filtrado) só para apresentação; `rh_db` (completo) exclusivamente para gravar.
- **Sem refactoring oportunista** adjacente à alteração.
- Não regredir os módulos que a Ana Carvalho usa (faturação/contratos).
- Commits via `_tmp_commit_msg.txt` + `git commit -F`; deploy só pelo trigger `gestnow-app-trigger-final`.
- Merges/alterações de config só em horário de baixo uso e com aviso prévio à Ana.

---

## 7. Abordagem faseada sugerida

1. **Fase 0 — Descoberta (sem código):** Claude Code mapeia as colunas reais de `obras_lista.csv`, `usuarios.csv`, `colaboradores_rh.csv`, `com_contactos.csv`, `inst_acessos.csv`, e confirma onde vive cada dado dos Grupos B e C. Resolve os Alertas 1–3.
2. **Fase 1 — Modelo de dados:** definir que colunas novas (se alguma) entram em `obras_lista.csv` (Grupo A), e que campos são apenas referências. Plano de migração para as obras existentes.
3. **Fase 2 — Formulário da obra (dashboard):** campos do Grupo A.
4. **Fase 3 — Detalhe da obra:** resolução automática (leitura) dos Grupos B e C.
5. **Fase 4 — Alocações:** integração com `inst_acessos.csv` (elementos, nº de colaboradores, valor/hora).
6. **Cada fase:** validação intermédia em produção antes da seguinte.

---

## 8. Perguntas em aberto para ti (Diogo) decidires

1. A ficha de obra passa a **gerir** as alocações (adicionar/remover elementos) ou só as **mostra**, ficando a gestão no módulo de Alocações?
2. "Estado da obra" — que estados existem além de Ativa/Inativa? (fases?)
3. "Valor da Diária" — por obra ou por alocação?
4. Os campos CPS/Cliente/Outro (Alojamento, Viatura, Ferramentas, EPIs) — quando é "Outro", há um campo de texto a especificar?

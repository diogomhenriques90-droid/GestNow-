# Auditoria — Cadeia ISO de rastreabilidade das obras

**Gerado:** 2026-06-18 · **Âmbito:** obras ATIVAS · **Origem:** leitura read-only (sem escrita)

Cadeia verificada: `Obra → Orcamento_ID → orcamentos.ID → Oportunidade_ID → comercial_oportunidades.ID → Contacto_Origem`.
Obras ativas cuja cadeia NÃO fecha: **4** (de 15). Nenhum valor de contacto é incluído.

| Obra | Elo onde parte | Causa | Classificação | Ação |
|---|---|---|---|---|
| Escritório | Orcamento_ID (VAZIO) | Obra interna sem cliente | EXCEÇÃO LEGÍTIMA | Nenhuma (documentar) |
| Geberit - Cedência de Mão de Obra | Oportunidade_ID (VAZIO no orçamento) | Orçamento sem oportunidade-mãe | GAP DE PROCESSO | Investigar e ligar orçamento à oportunidade |
| EFUELS - Cedência de mão de obra | Contacto_Origem (VAZIO) | Campo por preencher na oportunidade | DESCUIDO | Preencher Contacto_Origem na UI |
| Atlantic Cooper - Prestação de serviço | Contacto_Origem (VAZIO) | Campo por preencher na oportunidade | DESCUIDO | Preencher Contacto_Origem na UI |

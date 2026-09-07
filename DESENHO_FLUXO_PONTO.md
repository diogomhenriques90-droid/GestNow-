# Desenho do fluxo de registo e validação de horas — GestNow + cps-ponto

Documento único de referência para o fluxo de ponto entre os dois repositórios. Substitui, para este assunto específico, o que estava disperso por histórico de commits e por secções do `CLAUDE.md` de cada repositório que descreviam coisas que nunca chegaram a existir. Escrito por leitura direta de código, documentação e histórico dos dois repositórios — nada foi alterado em código ou produção ao escrever isto.

Relacionado: `AUDITORIA_REGISTO_PONTO.md` (auditoria de dados e bugs, mesma pasta).

---

## 1. Porque este documento existe

O desenho descrito na secção 2 já foi pensado e escrito antes — não num documento, mas no histórico de commits do GestNow, entre **29 de maio e 1 de junho de 2026**:

1. `e211f54` (29/05, 11:45) — "Fase A — chefe não valida próprias horas + secretariado filtra obras com chefe".
2. `48242e4` (29/05, 11:48) — "Fase B — Validado1_Por/Data e Rejeitado_Por/Data em todas as ações do chefe".
3. `56b8805` (29/05, 11:53) — junta as fases B–E (auditoria, performance, UX, cleanup) — confirma que existiu um plano faseado A–E.
4. `5cb80de` (29/05, 12:29) — **revert de emergência**: "reverter lógica cps-ponto aplicada por engano nos PRs #9 e #10". A própria mensagem diz que "chefe não valida próprias horas" e os campos de auditoria eram lógica pensada para o cps-ponto, aplicada por engano ao GestNow.
5. `b56cbec` (29/05, 17:13) — a mesma ideia do filtro "obras com chefe" é reimplementada nesse mesmo dia, à tarde, agora como lógica própria do GestNow.
6. `f2cd17f` (01/06) — junta esse filtro com a desativação do registo de horas no GestNow, a favor do cps-ponto.

O que sobreviveu: a separação registo (cps-ponto) / validação-faturação (GestNow), e o filtro "obras com chefe" no secretariado. O que não sobreviveu, e nunca foi reposto: "o chefe não valida as próprias horas" — resolvido agora de forma diferente e mais simples, por autovalidação automática no cps-ponto, confirmada já implementada.

---

## 2. O desenho alvo

- **cps-ponto** (telemóvel, terreno): o colaborador regista horas. O Chefe de Equipa faz a 1ª validação das horas de quem está alocado à obra dele. As horas do próprio chefe autovalidam-se. **Acaba aqui — não há mais validações dentro do cps-ponto.**
- **GestNow** (computador, escritório): o Secretariado faz a 2ª validação, confrontando com a folha de papel. Nas obras pequenas sem chefe atribuído, o Secretariado faz também a 1ª validação. A partir daí: faturação, pagamento, RH.
- O estado de cada registo é visível por cor.
- A informação validada pelo chefe transita automaticamente para o GestNow — **isto já é verdade hoje, mecanicamente**, porque os dois repositórios leem e escrevem o mesmo `registos.csv` no mesmo bucket GCS. Não há (nem precisa de haver) um passo de exportação/importação — é literalmente o mesmo ficheiro.

---

## 3. Estados de um registo (máquina de estados) — alvo vs. hoje

| Status | Significado | Quem muda, no desenho alvo | Quem muda, hoje |
|---|---|---|---|
| `0` | Pendente | Criado pelo Técnico no cps-ponto | Igual |
| `1` | Validado (1ª validação) | Chefe de Equipa, no cps-ponto — ou automático, se o próprio registo é do chefe (autovalidação) — ou Secretariado no GestNow, só para obras sem chefe atribuído | Igual, **mas** também pode ser posto a `1` por uma 2ª peça que não devia existir (ver abaixo) |
| `2` | Enviado a faturação (2ª validação) | Secretariado, no GestNow | **Também** pode acontecer dentro do cps-ponto, por um papel "Gestor" — ver secção 4 |
| `3` | Processado / pago | Secretariado, no GestNow ("Processar Pagamento") | Igual |
| `-1` | Rejeitado | Chefe (cps-ponto) ou Secretariado (GestNow), conforme a fase em que está | Igual |

**Problema de nomenclatura entre os dois repositórios**: quando o Chefe valida no cps-ponto, o registo fica com `Validado_Por`/`Validado_Data` preenchidos. Quando o Secretariado faz a 1ª validação no GestNow (caso "obra sem chefe"), preenche `Validado1_Por`/`Validado1_Data` — colunas diferentes para o mesmo conceito ("quem fez a validação que pôs isto em Status 1"). Hoje, nenhum dos dois lados consegue olhar para a coluna do outro e saber com certeza quem validou um registo em Status 1 — só sabe que "alguém validou".

---

## 4. O que já está feito, por comparação com o alvo

### cps-ponto

- ✅ Autovalidação do chefe — confirmado no código: ao criar o próprio registo, `Status` fica logo `"1"` em vez de `"0"`, com `Validado_Por` preenchido no mesmo passo.
- ✅ Validação do chefe sobre a equipa, excluindo os próprios registos (não os vê na lista de pendentes, porque já nasceram validados).
- ❌ **"Acaba aqui" não é verdade hoje.** Existe uma 2ª validação — papel "Gestor", dentro do próprio cps-ponto — que avança Status `1→2`, implementada de propósito (commit `433e7b1`, 1 de junho), ainda ativa. Isto é o maior desvio face ao desenho alvo: há duas peças de código diferentes (uma no cps-ponto, outra no `mod_secretariado.py` do GestNow) a fazerem a mesma transição de estado sobre o mesmo ficheiro, cada uma sem saber da outra.
- ⚪ Obras sem chefe atribuído ficam presas em Status `0` dentro do cps-ponto — isto **não é um bug a corrigir aqui**, é a divisão de responsabilidades a funcionar como deve: o GestNow já cobre este caso (ver abaixo). A própria auditoria do cps-ponto (`AUDITORIA_2026-09-06.md`) classifica isto como crítico, mas fê-lo sem visibilidade sobre o GestNow — visto a par dos dois repositórios, não é um beco sem saída.

### GestNow

- ✅ Secretariado faz 2ª validação (`mod_secretariado.py`, separador "2ª Validação", Status `1→2`).
- ✅ Secretariado faz 1ª validação para obras sem chefe (separador "1ª Validação", filtra exatamente as obras que não estão na lista de "obras com chefe").
- ✅ Processamento de pagamento (separador "Faturação & Folhas", Status `→3`).
- ⚠️ **Registo de ponto desativado no GestNow, mas não removido — só escondido atrás de uma flag.** O formulário continua fisicamente no código: `mod_tecnico.py`, linhas 521-799 (~280 linhas), e `mod_chefe.py`, linhas 1282-1439 (~157 linhas), cada um por trás de uma variável de sessão (`show_reg_form`/`show_reg_form_ch`) forçada a `False` em todos os renders. Hoje, na prática, é inacessível pela app — a flag é reposta a `False` incondicionalmente em todos os renders, não só uma vez, por isso nem manipular o estado da sessão chegaria lá. Mas isso é uma garantia de comportamento, não a ausência do caminho: o código que grava em `registos.csv` continua todo lá, a uma linha de distância de voltar a ficar acessível se algum dia alguém mexer nessa flag sem perceber porque está ali. O desenho alvo (registo só no cps-ponto) exige apagar estes dois blocos por completo — a garantia deixa de depender de uma variável nunca ser alterada, e passa a ser: o caminho simplesmente não existe.
- ❌ **A fonte de dados para "que obra tem chefe" está desatualizada.** Tanto `mod_secretariado.py` como `mod_chefe.py` usam `inst_acessos.csv` (um ficheiro cujo propósito documentado é outro — alocação de instrumentação, não chefia) para decidir isto. Desde agosto de 2026 existe um campo próprio, `Responsavel_Equipa` em `obras_lista.csv`, criado especificamente para o Painel de Obra — mas o fluxo de validação nunca foi atualizado para o usar. Há hoje duas fontes de verdade para a mesma pergunta de negócio, e nenhuma sabe da outra.
- ❌ **A escrita da Data no GestNow corrompe/apaga o valor mesmo sem qualquer concorrência com o cps-ponto.** Confirmado agora dos dois lados: o cps-ponto escreve sempre texto limpo (DD/MM/AAAA); o defeito está inteiramente na forma como o GestNow lê (converte para um valor de data real) e depois volta a escrever essa coluna já convertida. Já documentado em detalhe em `AUDITORIA_REGISTO_PONTO.md`.
- ❌ Escrita concorrente sem bloqueio (ler tudo → alterar → escrever tudo de volta) — confirmado nos dois lados, incluindo o próprio `AUDITORIA_2026-09-06.md` do cps-ponto a apontar exatamente o mesmo padrão, de forma independente.
- ⚪ "Chefe não valida as próprias horas" — a tentativa de maio foi revertida e nunca reposta; hoje `mod_chefe.py` não impede explicitamente o chefe de clicar "validar" nos seus próprios registos, mas isto acaba por não ter efeito prático, porque a autovalidação do cps-ponto já os entrega em Status `1` (nunca aparecem como "pendentes" para o chefe re-validar). Não é uma lacuna a fechar com urgência, mas vale a pena ter presente que a proteção existe só por acidente de fluxo, não por desenho explícito.

---

## 5. A aba "Obra" do Chefe de Equipa no GestNow — decisão tomada: sai por completo

**Decisão (ver também `DESENHO_AUTENTICACAO.md`): o Chefe de Equipa nunca mais entra no GestNow, sem exceções.** Não é uma escolha tab a tab — é uma exclusão total. Tudo o que hoje é do Chefe em `mod_chefe.py` (6 separadores: **Equipa**, **Validar Horas**, **Meu Ponto**, **Folha de Ponto**, **HSE**, **Pedidos**) tem de passar para o cps-ponto ou desaparecer. **Validar Horas** e **Meu Ponto** já estão cobertos pelo desenho geral (validação e histórico já vivem no cps-ponto). Os outros quatro, levantados um a um:

- **Equipa** — resumo de leitura por técnico (horas, registos, pendentes, aprovados), já baseado em `Responsavel_Equipa`. Não existe equivalente no cps-ponto, mas os dados de base já lá estão. Construção pequena.
- **Comunicados à Equipa** (dentro da aba Equipa) — **achado**: este formulário grava em `comunicados.csv`, mas não existe, em nenhum dos dois repositórios, nenhum ecrã que leia ou mostre esse conteúdo a alguém. `comunicados.csv` está encadeado como parâmetro por mais de dez módulos do GestNow, sem que nenhum o use de facto; `comunicados_lidos.csv` nunca é escrito em lado nenhum. É uma funcionalidade que hoje não funciona para ninguém — não há nada a migrar, é construção de raiz nas duas pontas (enviar e mostrar/marcar como lido). É a maior das quatro peças, exatamente por não haver nada existente para reaproveitar.
- **Folha de Ponto** — o cps-ponto já tem um gerador completo e equivalente (`_render_folha`, com assinatura por canvas). Não é migração, é decidir que a versão do GestNow deixa de ser usada. Construção nova: zero.
- **HSE** — o cps-ponto já reporta e lista incidentes, mas só os próprios da pessoa; a vista de equipa (todas as obras do chefe) não existe lá. Construção média — reaproveita o padrão já usado para o Secretariado (filtrar por `Responsavel_Equipa`), não é uma funcionalidade nova de base.
- **Pedidos** — vista de leitura dos pedidos de EPI/ferramenta/material da equipa. Não existe nada disto no cps-ponto, nem sequer o lado do técnico (submeter um pedido) — que também não existe lá. É a maior depêndencia das quatro: a vista do chefe só faz sentido depois de os técnicos poderem submeter pedidos no cps-ponto, o que é trabalho prévio, não paralelo.

---

## 6. Documentos antigos que passam a estar errados

- **`cps-ponto/CLAUDE.md`** descreve "Secretariado" (1ª e 2ª validação) como se fosse implementado localmente — nunca foi. A redação parece ter herdado uma mensagem de commit que descrevia trabalho feito em paralelo no GestNow. Precisa de correção.
- **`cps-ponto/CLAUDE.md`** refere as colunas `Validado1_Por`/`Validado1_Data` — o código do cps-ponto usa `Validado_Por`/`Validado_Data` (sem o "1"). Corrigir junto com a reconciliação de nomes entre repositórios (secção 3).
- **`cps-ponto/CLAUDE.md`** descreve GPS/check-in e mapas como parte da stack — o schema existe (`Localizacao_Checkin`/`Localizacao_Checkout`), mas nunca foi implementado nem no cps-ponto nem no GestNow. Corrigir ou remover a menção.
- **`cps-ponto/AUDITORIA_2026-09-06.md`** — não fica errado, mas o seu crítico #1 ("obras sem chefe ficam presas") deve passar a ler-se à luz deste documento: dentro do cps-ponto sozinho é verdade, mas de ponta a ponta o GestNow já cobre o caso.
- O histórico de commits de maio (PRs #9/#10) já está coberto pelo aviso existente no `CLAUDE.md` do GestNow — não precisa de novo documento, só de se manter presente para que ninguém tente repor "chefe não valida próprias horas" sem saber que já foi tentado, revertido, e substituído por outra solução.

---

## 7. Diagnóstico final

### 7.1 O que já está assim, e o que não está, por app

**cps-ponto**: registo, validação do chefe, e autovalidação — feitos, batem certo com o alvo. A "2ª validação Gestor" dentro do cps-ponto é o único desvio real, e é deliberado, não acidental.

**GestNow**: 1ª validação (obras sem chefe), 2ª validação, faturação, pagamento — feitos, batem certo com o alvo. Os desvios são todos de qualidade de dados subjacente (fonte de "obra tem chefe" desatualizada, nomes de coluna não reconciliados, escrita da Data avariada, escrita concorrente sem proteção) — não de desenho de fluxo.

### 7.2 O que existe hoje e não cabe neste desenho, e deve sair

- **cps-ponto**: a 2ª validação "Gestor" (Status `1→2`) dentro do cps-ponto — essa transição deve passar a existir só no GestNow.
- **GestNow**: os dois blocos de código do formulário de registo de ponto (`mod_tecnico.py` linhas 521-799, `mod_chefe.py` linhas 1282-1439) — hoje inacessíveis por uma flag, mas têm de ser apagados por completo, não só desligados (ver secção 4).
- **GestNow**: o Chefe de Equipa deixa de ter acesso à app, sem exceções — as abas Equipa, Folha de Ponto, HSE e Pedidos de `mod_chefe.py` saem todas (secção 5).
- **GestNow / cps-ponto**: um dos dois geradores de Folha de Ponto — ficar com os dois é manter duplicação ativa sobre os mesmos dados.
- **GestNow**: `inst_acessos.csv` como fonte de "que obra tem chefe" — sai, substituído por `Responsavel_Equipa`.

### 7.3 O que falta construir, por ordem de dependência

1. **Reconciliar a convenção de nomes de colunas de validação** entre os dois repositórios (`Validado_Por` vs `Validado1_Por`, e equivalentes de rejeição). Sem isto, não se sabe com confiança quem validou o quê — é a base de tudo o resto.
2. **Substituir `inst_acessos.csv` por `Responsavel_Equipa`** como fonte de "quem é o chefe desta obra", nos dois sítios que dependem disso hoje (`mod_secretariado.py` e `mod_chefe.py`). Pré-requisito para qualquer decisão futura sobre "obras sem chefe".
3. **Desligar a 2ª validação "Gestor" dentro do cps-ponto** — decisão e alteração de código do lado do cps-ponto.
4. **Remover ou esvaziar o separador "Validar Horas" de `mod_chefe.py`** no GestNow.
5. **Corrigir o formato da Data na escrita** (defeito já localizado, independente da concorrência) — pode ser feito em paralelo com o ponto seguinte, no mesmo sítio de código.
6. **Resolver a escrita concorrente com bloqueio otimista** ("só escreve se ninguém mexeu desde que li") — depende de 1 e 2 estarem estáveis, para não se estar a testar bloqueio em cima de uma base de dados ainda inconsistente. Decisão de arquitetura já tomada (ver histórico de conversa), plano de faseamento entre os dois repositórios por decidir à parte.
7. **Decidir e resolver a duplicação de Folha de Ponto / Meu Ponto** entre as duas apps — já resolvido no sentido Folha de Ponto (cps-ponto fica, GestNow sai, sem construção nova).
8. **Apagar por completo os dois blocos mortos de registo de ponto** em `mod_tecnico.py` e `mod_chefe.py` (secção 4) — não basta a flag que já os desliga.
9. **Migrar as quatro peças do Chefe de Equipa para o cps-ponto** (secção 5), por tamanho crescente: Equipa (pequena) → HSE de equipa (média, reaproveita o padrão de `Responsavel_Equipa`) → Comunicados à Equipa (grande, construção de raiz nas duas pontas, nada a reaproveitar) → Pedidos (a maior, depende primeiro de os técnicos poderem submeter pedidos no cps-ponto, que também não existe).
10. *(Achado relacionado, fora do fluxo de validação em si, mas no mesmo ficheiro `registos.csv`)*: corrigir os 24 de 25 pontos de escrita no cps-ponto que não verificam se `save_db()` teve sucesso — risco separado, mas do mesmo tipo ("a app diz que guardou e não guardou").

Não há prazo definido para este trabalho.

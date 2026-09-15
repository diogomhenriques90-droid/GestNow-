# Plano — Passo 1: reconciliar os nomes das colunas de validação

Primeiro passo do plano de dependências descrito em `DESENHO_FLUXO_PONTO.md` (secção 7.3). Documento de plano — nada foi implementado. Escrito por leitura direta do código dos dois repositórios e dos dados reais em `registos.csv` (leitura, sem alterações).

---

## 1. Nomes usados por cada app, lado a lado

Só existe um par de nomes verdadeiramente diferente entre as duas apps. Os restantes já coincidem.

| O que regista | cps-ponto | GestNow | Situação |
|---|---|---|---|
| 1ª validação (quem/quando) | `Validado_Por` / `Validado_Data` | `Validado1_Por` / `Validado1_Data` | **Únicos nomes diferentes — é aqui que está o trabalho.** |
| 2ª validação (quem/quando) | `Validado2_Por` / `Validado2_Data` | `Validado2_Por` / `Validado2_Data` | Já coincide, nada a fazer. |
| Rejeição (quem/quando) | `Rejeitado_Por` / `Rejeitado_Data` | `Rejeitado_Por` / `Rejeitado_Data` (nome existe, mas o GestNow nunca o escreve) | Nome já coincide — falha à parte, ver secção 4. |
| Pagamento/processamento | não existe | `Processado_Por` / `Processado_Data` | Só faz sentido no GestNow, sem equivalente necessário no cps-ponto. |

**Proposta**: o cps-ponto passa a escrever `Validado1_Por`/`Validado1_Data` em vez de `Validado_Por`/`Validado_Data`, para a validação do chefe. Mantém-se o nome do lado do GestNow (com o "1") porque a convenção numerada já funciona sem atrito para a 2ª validação nos dois lados — deixar a 1ª sem número seria a inconsistência a persistir.

**Alargamento de significado a documentar**: hoje, `Validado1_Por` no GestNow significa especificamente "validado pelo secretariado". Passa a significar "passou a 1ª validação, seja pelo chefe no terreno (cps-ponto) ou pelo secretariado no escritório (GestNow, só obras sem chefe)". Isto precisa de ficar escrito no `CLAUDE.md` de cada repositório para que não se assuma erradamente que `Validado1` é sempre secretariado.

---

## 2. O que acontece aos 79 registos existentes

Verificado nos dados reais de produção (leitura, sem alterações):

- **4 registos** têm `Validado_Por` preenchido (coluna do cps-ponto) — todos são o mesmo Chefe de Equipa (Jorge Oliveira) a validar as próprias horas — a autovalidação a funcionar como esperado.
- **1 registo** tem `Validado1_Por` preenchido (coluna do GestNow) — uma validação do secretariado.
- **1 registo** tem `Validado2_Por` preenchido — já é o mesmo nome dos dois lados, sem problema.
- **0 registos** têm `Rejeitado_Por` preenchido.

Não é um volume grande: só 5 das 79 linhas têm alguma informação de "quem validou" gravada nestas colunas.

**Verificação de colisão feita antes de propor qualquer conversão**: confirmei se alguma das 4 linhas com `Validado_Por` é a mesma linha que já tem `Validado1_Por` preenchido — não há sobreposição nenhuma. São conjuntos de linhas completamente distintos, pelo que uma conversão não teria de resolver nenhum conflito de valores.

---

## 3. Conversão necessária

Pequena e sem ambiguidade:

- As **4 linhas com `Validado_Por`/`Validado_Data`** têm de passar esse valor para `Validado1_Por`/`Validado1_Data` — cópia direta, célula a célula, sem decisão a tomar sobre qual valor prevalece (não há colisão).
- As restantes **75 linhas** não têm nada a converter nestas colunas.
- É uma operação a fazer **uma vez**, sobre o ficheiro tal como está hoje, antes ou no mesmo momento em que o cps-ponto passar a escrever no nome novo — não é uma migração contínua.

---

## 4. Achados por resolver (falhas de rastreabilidade, fora do âmbito deste passo)

Duas falhas encontradas ao verificar os dados para este plano, que não são um problema de nomes diferentes, mas de informação que nunca chegou a ser escrita. Ficam registadas aqui para decisão à parte — não fazem parte da reconciliação de nomes em si.

### 4.1 — 74 dos 79 registos têm estado avançado sem nenhum registo de quem os validou

Das 79 linhas, só 5 têm alguma coluna de "quem validou" preenchida (as do ponto 2, acima). As outras **74 já têm o estado avançado — validado, enviado a faturação, ou pago — sem que nenhuma coluna diga quem fez essa validação**. A causa mais provável: a maior parte dos ecrãs de validação do próprio GestNow (nomeadamente o separador "Validar Horas" do Chefe, que o desenho alvo prevê remover) muda o estado do registo sem escrever nenhuma informação de autoria — só toca no `Status`.

Isto significa que, mesmo depois de reconciliados os nomes, a maior parte do histórico continua sem responder a "quem validou isto". Precisa de decisão à parte: se se aceita este histórico como está (sem autoria retroativa), ou se há alguma forma de reconstruir parcialmente essa informação antes de o problema deixar de ter solução (por exemplo, por quem estava a operar cada obra nessa altura).

### 4.2 — Os botões de rejeitar do GestNow mudam o estado mas não escrevem `Rejeitado_Por`/`Rejeitado_Data`

Confirmado no código: tanto no ecrã do Chefe como no do Secretariado, as ações de rejeitar (individuais e em massa) mudam o `Status` para rejeitado, mas nunca escrevem `Rejeitado_Por` nem `Rejeitado_Data` — só o cps-ponto o faz. O nome da coluna já coincide entre as duas apps (ver secção 1), por isso isto não se resolve com a reconciliação de nomes — é uma escrita em falta do lado do GestNow, independente do passo 1.

Sem isto, uma rejeição feita no GestNow fica sem responsável nem data registados — o mesmo tipo de lacuna de rastreabilidade do ponto 4.1, mas do lado da rejeição em vez da validação.

---

## Nota final

Este documento cobre só o passo 1 do plano em `DESENHO_FLUXO_PONTO.md`. Nada foi implementado — é plano, para decisão e aprovação antes de qualquer alteração de código.

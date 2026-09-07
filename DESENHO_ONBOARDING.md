# Desenho do onboarding — GestNow + cps-ponto

Decisões sobre o percurso de integração do colaborador, a seguir à auditoria em `AUDITORIA_ONBOARDING.md` (mesma pasta). Nada disto está implementado — é o desenho acordado, para servir de referência ao trabalho que se seguir.

---

## 1. Onde vive o onboarding

**Decisão: só no cps-ponto**, tal como já aconteceu ao registo de ponto. O GestNow deixa de ter os 4 passos e fica só com o lado do RH: gerar e enviar o contrato, validar a assinatura, e acompanhar quem está por completar (ponto 3).

### Pré-requisito revisto: já não é preciso nenhum ecrã dedicado a Secretariado/Armazém

**Decisão corrigida (anula a versão anterior desta secção)**: Secretariado, Armazém e Faturação são papéis administrativos, existem só no GestNow, sem ecrã próprio no cps-ponto. Se alguém com um destes papéis precisar de registar ponto, entra no cps-ponto como qualquer colaborador — número + PIN — e cai no caminho por omissão que hoje já serve o Técnico (Meu Ponto, Histórico, Alertas, HSE, Perfil). Não há nada a construir de propósito para eles: o pré-requisito de "cps-ponto reconhecer Secretariado e Armazém" que estava aqui deixou de existir, porque deixou de fazer sentido a pergunta — eles não precisam de ser "reconhecidos" com um ecrã diferente, só de caber no caminho que já existe. Ver `DESENHO_AUTENTICACAO.md` para o detalhe desta decisão.

---

## 2. Recusar o preço/hora

**Decisão: trava o percurso e notifica o RH, sempre as duas coisas juntas — nunca uma sem a outra.** Uma recusa sem travar (o estado de hoje) deixa a pessoa a avançar com um preço por resolver; travar sem notificar deixa a pessoa bloqueada sem que ninguém saiba que precisa de agir. As duas têm de acontecer no mesmo momento.

---

## 3. O contrato — 5º passo invisível

**Decisão: não bloquear o acesso à app.** Impedir alguém de trabalhar no primeiro dia por causa de papelada em atraso é pior do que o problema que resolve. Em vez de bloqueio, três coisas:

1. **Aviso permanente à pessoa**, visível sempre que usa a app, de que falta assinar o contrato — até o RH validar a assinatura.
2. **Uma lista no GestNow**, do lado do RH, com quem já completou os 4 passos e ainda não tem contrato gerado/enviado — para deixar de depender de alguém se lembrar.
3. **Corrigir a notificação que hoje dispara cedo de mais** (no fim do Perfil, passo 3, em vez de no fim real dos 4 passos) — passa a disparar no momento certo, dirigida a quem trata de contratos.

---

## 4. A ordem dos passos

**Decisão: mantém-se — Documentos, Preço/Hora, Perfil, IBAN.** Só faz sentido depois da decisão do ponto 2: com a recusa a travar o percurso, mostrar o preço antes do formulário grande de perfil volta a funcionar como filtro — não vale a pena a pessoa investir tempo a preencher o perfil se os termos não estiverem aceites. Sem a correção do ponto 2, esta ordem seria só um acidente sem efeito.

---

## 5. Ordem de dependência para chegar aqui

1. **Migrar os 4 passos para serem só no cps-ponto** — a implementação de lá já existe e serve de base; o bloco do GestNow passa a candidato a remover (ponto 5). Já não há pré-requisito de reconhecer Secretariado/Armazém — caem no caminho por omissão que já existe.
2. **Aplicar as correções de comportamento na versão que fica** (cps-ponto, já que a do GestNow vai ser removida): recusa do preço a travar e a notificar em conjunto (secção 2). A ordem dos passos (secção 4) não exige trabalho — já é a atual, só passa a fazer sentido depois do ponto anterior.
3. **Construir o aviso permanente à pessoa** sobre o contrato em falta, no cps-ponto (onde a pessoa passa a estar).
4. **Construir, no GestNow, a lista para o RH** de quem completou os 4 passos sem contrato, e a notificação disparada no momento certo — pode ser feito em paralelo com os pontos 1-3, já que só depende de colunas já partilhadas em `usuarios.csv` (não há nomes a reconciliar, ao contrário do que foi preciso no ponto).
5. **Remover o bloco de onboarding do GestNow** — só depois de confirmar que o cps-ponto já cobre os 4 passos para todos os papéis.

Não há prazo definido. Nada disto foi implementado.

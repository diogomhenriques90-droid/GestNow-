# Desenho do onboarding — GestNow + cps-ponto

Decisões sobre o percurso de integração do colaborador, a seguir à auditoria em `AUDITORIA_ONBOARDING.md` (mesma pasta). Este é o desenho acordado, para servir de referência ao trabalho que se seguir.

**Estado (actualizado)**: passos 1, 2 e 5 da ordem de dependência (secção 6) feitos. `_render_onboarding()` no cps-ponto já distingue por Tipo quem pára nos documentos (Admin, Secretariado, Armazém) e quem faz os 4 passos completos (Técnico, Instrumentista, Engenheiro, Chefe de Equipa) — já filtra os documentos mostrados pela `Funcao` da pessoa (ecrã de gestão em RH, `mod_admin_rh.py`; documento sem função associada = toda a gente) — e o passo dos documentos já lê página a página dentro da app (um documento pendente de cada vez, navegação Anterior/Seguinte, botão de confirmar só na última página), com o registo por evento (abertura, cada página, confirmação) em `pdfs_leitura_log.csv`. Com isto, o cps-ponto já cobre onboarding — documentos incluídos, com o novo mecanismo de leitura — para todos os papéis; a remoção do bloco duplicado no GestNow (passo 6) continua por decidir explicitamente antes de ser feita. Passos 3 e 4 continuam por fazer.

---

## 1. Onde vive o onboarding, e quem faz o quê

**Decisão corrigida (substitui a versão anterior desta secção): os documentos são para toda a gente.** Cada função tem os documentos associados a ela; o Manual de Acolhimento é comum a todos. Ao contratar alguém administrativo, cria-se a função dessa pessoa e associam-se os documentos que fizerem sentido — mesmo que hoje seja só o manual.

**O que difere, por papel, é o resto do percurso:**
- **Colaboradores e chefes**: os 4 passos completos — Documentos, Preço/Hora, Perfil, IBAN.
- **Administrativos** (escritório, secretariado, armazém, faturação): **só os documentos da função.** Sem Preço/Hora, sem IBAN — o contrato deles é outra coisa, tratada em papel, fora da aplicação.

Isto substitui a decisão anterior de que os administrativos não faziam onboarding nenhum na app — faziam-no zero; passam a fazer só a parte documental.

**Onde isto acontece**: só no cps-ponto, tal como já decidido para o registo de ponto — não há razão para o percurso de documentos existir duplicado no GestNow. O bloco dos 4 passos que existe hoje no GestNow continua a sair por completo (código morto, não só desativado) — mas o cps-ponto passa a ter de saber que **nem todos os papéis fazem os 4 passos**: um administrativo pára depois dos documentos; um colaborador ou chefe continua.

**Implicação a ter presente para o passo 3** (não decidida aqui, só registada): o portão do onboarding no cps-ponto tem de saber, pelo Tipo da conta, até onde cada pessoa vai — documentos apenas, ou os 4 passos completos.

**Depois dos documentos, para um administrativo**: não há ecrã próprio no cps-ponto — se algum dia precisar de registar ponto, cai no caminho por omissão que hoje já serve o Técnico (Meu Ponto, Histórico, Alertas, HSE, Perfil). Não há nada a construir de propósito só para eles nessa parte (ver `DESENHO_AUTENTICACAO.md`).

### Nota de conformidade — dois processos de integração, duas rastreabilidades (ajustada)

Fica registado, para refletir no procedimento da qualidade: há **dois processos de integração diferentes, com rastreabilidade diferente** — mas agora só na parte não-documental. A parte documental (documentos da função + Manual de Acolhimento) fica registada na app **para toda a gente**, colaboradores e administrativos por igual. O que fica em papel, fora da aplicação, é só o resto do contrato dos administrativos — preço/hora e IBAN não se aplicam a eles, e o contrato propriamente dito é tratado à parte. Isto tem de estar escrito no procedimento da qualidade para que fique claro: os administrativos têm evidência documental na app, tal como os colaboradores — só o contrato de trabalho em si é que segue um processo diferente.

---

## 2. O passo dos documentos — muda o mecanismo de confirmação

✅ **Feito** — `_render_onboarding()` no cps-ponto (`app_ponto.py`), com `pdfs_leitura_log.csv` a registar cada evento (abertura, cada página, confirmação), um por linha, com hora ao segundo.

**Decisão: o documento passa a abrir dentro da app, e o botão de confirmação só fica disponível depois de a pessoa ter percorrido o documento até ao fim.**

Hoje, a pessoa descarrega o ficheiro e confirma num botão — isso prova que carregou no botão, não que abriu o documento. Não é evidência suficiente para a 9001 nem para a 19443. Percorrer até ao fim antes de poder confirmar não garante leitura a sério, mas é uma evidência muito mais forte do que existe hoje, e é isso que interessa como prova para auditoria.

**Mecanismo: por páginas, não por scroll contínuo.** Mostra-se o documento uma página de cada vez, avança-se página a página, e só depois de passar pela última é que o botão de confirmar aparece. Escolhido em vez de detetar scroll contínuo porque é mais barato de construir (não exige JavaScript nem um componente próprio — o Streamlit já sabe mostrar imagens de origem), é mais fiável em qualquer telemóvel (deixa de depender do leitor de PDF do browser, que varia muito entre aparelhos), e como evidência é pelo menos tão forte — obriga a uma ação explícita por página.

**O que fica registado, por documento e por pessoa**: hora de abertura, hora de passagem por cada página, e hora de confirmação final. Não só a confirmação. O objetivo é conseguir detetar confirmações suspeitas — por exemplo, um documento de 10 páginas confirmado poucos segundos depois de aberto. Timestamp total sozinho ("esteve X minutos") não chega, porque não prova progressão nenhuma; a sequência de horas por página conta uma história muito mais convincente para um auditor.

---

## 3. Recusar o preço/hora

**Decisão: trava o percurso e notifica o RH, sempre as duas coisas juntas — nunca uma sem a outra.** Uma recusa sem travar (o estado de hoje) deixa a pessoa a avançar com um preço por resolver; travar sem notificar deixa a pessoa bloqueada sem que ninguém saiba que precisa de agir. As duas têm de acontecer no mesmo momento. Aplica-se só a colaboradores e chefes — administrativos não passam por este passo (secção 1).

---

## 4. O contrato — passo invisível para colaboradores; papel para administrativos

**Decisão: não bloquear o acesso à app**, para colaboradores e chefes. Impedir alguém de trabalhar no primeiro dia por causa de papelada em atraso é pior do que o problema que resolve. Em vez de bloqueio, três coisas:

1. **Aviso permanente à pessoa**, visível sempre que usa a app, de que falta assinar o contrato — até o RH validar a assinatura.
2. **Uma lista no GestNow**, do lado do RH, com quem já completou os 4 passos e ainda não tem contrato gerado/enviado — para deixar de depender de alguém se lembrar.
3. **Corrigir a notificação que hoje dispara cedo de mais** (no fim do Perfil, em vez de no fim real dos 4 passos) — passa a disparar no momento certo, dirigida a quem trata de contratos.

Para administrativos, o contrato é todo em papel (secção 1) — nada disto se aplica a eles.

---

## 5. A ordem dos passos, para quem faz os 4 completos

**Decisão: mantém-se — Documentos, Preço/Hora, Perfil, IBAN.** Só faz sentido depois da decisão da secção 3: com a recusa a travar o percurso, mostrar o preço antes do formulário grande de perfil volta a funcionar como filtro — não vale a pena a pessoa investir tempo a preencher o perfil se os termos não estiverem aceites. Sem essa correção, esta ordem seria só um acidente sem efeito.

---

## 6. Ordem de dependência para chegar aqui

1. ✅ **Migrar os 4 passos para serem só no cps-ponto**, já distinguindo por Tipo quem para nos documentos e quem continua — feito em `_render_onboarding()` (`app_ponto.py`). O bloco do GestNow fica por remover de propósito, candidato ao ponto 6.
2. **Aplicar as correções de comportamento na versão que fica**: recusa do preço a travar e a notificar em conjunto (secção 3) — por fazer; ✅ o novo mecanismo de confirmação de documentos (secção 2) — feito.
3. **Construir o aviso permanente à pessoa** sobre o contrato em falta, no cps-ponto (onde a pessoa passa a estar) — só para colaboradores/chefes.
4. **Construir, no GestNow, a lista para o RH** de quem completou os 4 passos sem contrato, e a notificação disparada no momento certo — pode ser feito em paralelo com os pontos 1-3, já que só depende de colunas já partilhadas em `usuarios.csv`.
5. ✅ **Associar documentos a funções** — feito. Nova coluna `Funcoes` em `pdfs_obrigatorios.csv` (lista de valores de `usuarios.csv`/`Funcao`; vazia = toda a gente), novo ecrã de gestão em RH (`mod_admin_rh.py`, separador "Documentos Obrigatórios"), e `_render_onboarding()` no cps-ponto já filtra pela `Funcao` da pessoa.
6. **Remover o bloco de onboarding do GestNow** — os pré-requisitos (pontos 1 e 5) já estão feitos; falta decidir explicitamente avançar com a remoção.

Não há prazo definido.

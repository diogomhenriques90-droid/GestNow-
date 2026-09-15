# Desenho da autenticação — GestNow + cps-ponto

Decisões sobre login e credenciais, tomadas antes de qualquer implementação. Confirmado por leitura de código antes de escrever isto — nada foi alterado.

---

## 0. Estado confirmado antes de decidir

- **Auto-serviço de password**: já existe e funciona hoje, para qualquer conta — `Perfil → "Password & PIN" → Alterar Password`. Pede a password atual, exige mínimo 8 caracteres, grava em hash `bcrypt` (`hp()`), regista em auditoria. A conta de super-admin usa o mesmo ecrã, sem exceção.
- **Força-reset de password curta**: já existe (`mod_login.py`, Fase 1) — qualquer login bem-sucedido com password de menos de 8 caracteres é automaticamente desviado para definir uma nova antes de completar a sessão. Não há forma de saber, sem essa pessoa entrar, se a password dela é curta — o hash não revela o comprimento original.
- **Hashing**: `bcrypt`, nunca texto simples, confirmado para password e para PIN.

---

## 1. Decisões

1. **cps-ponto**: entrada só por Número de Colaborador (5 dígitos) + PIN (4 dígitos). Desaparece username/password nesta app. Todos os papéis entram assim, incluindo quem faz trabalho administrativo mas regista ponto.
2. **GestNow**: entrada só por Número de Colaborador + Password. Desaparece qualquer via por PIN. Só papéis administrativos têm acesso a esta app.
3. Uma pessoa com as duas apps tem duas credenciais, uma em cada — assumido e correto, não é para unificar.
4. O ecrã de "Acesso antigo (por Nome)" (GestNow) morre por completo. As credenciais atuais de técnicos são de teste e são substituídas.
5. **Criação de colaborador (GestNow, RH)**: a app gera um PIN inicial aleatório e mostra-o ao RH, que o transmite ao colaborador. O RH define também a categoria profissional.
6. **PIN provisório**: todo o PIN gerado pelo RH — seja primeira atribuição ou redefinição — nasce marcado `PIN_Provisorio=Sim`. O gate que obriga a definir um PIN próprio corre **logo a seguir ao login, antes do onboarding e da verificação de contrato** — não "no fim do onboarding" como estava decidido inicialmente aqui. Essa colocação inicial partia do caso da primeira entrada e não cobria a redefinição: para um colaborador já com a conta toda feita, o onboarding não tem nada pendente e passa direto, pelo que um gate colocado no fim dele nunca chegaria a disparar. Bloqueio incondicional (sem forma de contornar) implementado em `_verificar_pin_provisorio()` (cps-ponto, `app_ponto.py`).
7. **PIN esquecido**: recuperação automática por email.

### Pré-requisitos
- Email passa a ser obrigatório na ficha de colaborador — não desenhar para o caso de não haver email.
- Configuração de SMTP fica para o fim — a recuperação por email é a última peça, não pode bloquear nada anterior.

### Prioridade
Primeiro o acesso (decisões 1-4), depois os 4 passos do onboarding com PIN inicial (decisões 5-6), depois a recuperação (decisão 7).

### Secretariado, Armazém e Faturação: administrativos, só no GestNow — sem ecrã próprio no cps-ponto

**Decisão**: estes três papéis existem só no GestNow, com o resto dos administrativos. Não têm nenhum ecrã dedicado no cps-ponto. Se alguém com um destes papéis precisar de registar ponto, entra no cps-ponto **como qualquer colaborador** — número + PIN, e vê exatamente o mesmo que um Técnico vê (Meu Ponto, Histórico, Alertas, HSE, Perfil). Não há nada a construir de propósito para eles do lado do cps-ponto — cai no caminho por omissão, que já serve qualquer Tipo não reconhecido como Chefe/Gestor.

Isto anula uma tentativa anterior (um ramo de 3 abas — Início, Alertas, Perfil — pensado para Secretariado/Armazém no cps-ponto, com uma mensagem a remeter para o GestNow). Foi desfeita.

### O Chefe de Equipa nunca entra no GestNow — e isso não é um bloqueio, é a ausência de conta

**Decisão**: sem exceções — o GestNow é só para administrativos. Mas a forma de o alcançar importa: **não é mostrar uma mensagem a quem tenta entrar** ("vai para a CPS Ponto") — é o Chefe de Equipa simplesmente não ter, em GestNow, nenhuma credencial que funcione. A única credencial que tem é o número + PIN do cps-ponto, e mais nada.

**O que isto implica, confirmado nos dados reais:**
- Os 10 Chefes de Equipa têm hoje Password definida em `usuarios.csv`, mas nenhum tem PIN. Isso quer dizer que, hoje, a via principal do GestNow (que já os trata como tipo-PIN) já falha sempre para eles — na prática, só conseguem entrar no GestNow hoje pelo ecrã "Acesso antigo (por Nome)", com essa mesma Password. Essa Password é também, hoje, a que usam para entrar no cps-ponto (login por Nome+Password lá). É a mesma credencial a servir os dois lados, por acaso de arquitetura, não por desenho.
- Quando o GestNow fechar por completo o acesso deste Tipo, a Password destas 10 contas deixa de servir para o GestNow (não há já nenhum caminho que a use aqui) — mas continua a servir o cps-ponto, até esse migrar para número+PIN (decisão 1, ainda por fazer). Só nessa altura fica a Password destas contas totalmente sem uso, substituída pelo PIN.
- **Nada parte no GestNow.** Verifiquei especificamente se a atribuição de "Responsável de Equipa" a uma obra (`mod_admin_obras.py`) depende de os Chefes de Equipa terem acesso ao GestNow — não depende: a lista de candidatos vem de quem está alocado à obra em `inst_acessos.csv`, não de uma pesquisa por `Tipo = Chefe de Equipa` em `usuarios.csv`. O RH continua a conseguir escolher e atribuir um chefe normalmente. As únicas coisas que ficam "penduradas" são verificações de `Tipo` que hoje dão acesso à Instrumentação e a capacidades extra no assistente de voz — deixam de ser alcançadas, porque ninguém desse Tipo volta a entrar, mas não ficam partidas: ficam código morto, no mesmo sentido em que já classificámos outras coisas nesta auditoria.

**Sequenciamento — isto só acontece depois da migração**: o corte de acesso dos Chefes ao GestNow só pode acontecer depois de as peças do Chefe hoje em GestNow (Equipa, Folha de Ponto, HSE, Pedidos, Comunicados à Equipa) estarem migradas para o cps-ponto ou removidas — descrito com tamanhos em `DESENHO_FLUXO_PONTO.md`. Cortar o acesso antes disso deixaria essas funcionalidades sem ninguém as poder usar.

O levantamento tab a tab dessa migração está em `DESENHO_FLUXO_PONTO.md`, não aqui.

---

## 2. O que existe hoje e não cabe neste desenho

### GestNow
- A "via principal" de login já existe, por Número de Colaborador — mas hoje despacha por Tipo entre PIN e Password (`TIPOS_PIN`). ✅ `Armazém` já saiu deste conjunto (feito). `Chefe de Equipa` fica lá por agora — a saída dele não é só sair do PIN, é deixar de ter conta nenhuma no GestNow, e isso só acontece depois da migração das suas peças para o cps-ponto (ver acima).
- O ecrã "Acesso antigo (por Nome)", com formulários próprios de Password e PIN, fica todo obsoleto (decisão 4).
- O bloco de RH "Redefinir PIN / Desbloquear conta" (`mod_admin_rh.py`) mantém-se válido — passa a ser sobre o PIN de acesso ao cps-ponto, geríve a partir do GestNow, e serve de recuperação manual enquanto o email (decisão 7) não estiver ligado.

### cps-ponto
- O login de hoje é só Nome + Password — não existe noção nenhuma de Número de Colaborador nem de PIN neste repositório. Não é um ajuste, é construção nova: o ecrã de número+PIN não tem nada para reaproveitar aqui, só a coluna `PIN` e o hashing já existentes no `usuarios.csv` partilhado.
- O onboarding (já a ser migrado para aqui, decisão de trabalho anterior) ainda não tem o conceito de "PIN inicial gerado pelo RH" nem a troca obrigatória de PIN no fim (decisões 5 e 6) — é trabalho novo, não uma correção do que já existe.

---

## 3. Ordem de dependência

A prioridade número um, em qualquer momento desta lista, é **nunca ficar sem forma de entrar** — nem tu, nem os técnicos que hoje trabalham.

1. ✅ **Feito** — Verificação das 11 contas administrativas: todas têm Número e Password; uma (Adriana Pinto/Adriana Margarida, identidade duplicada) foi corrigida — ver histórico da conversa. A tua conta está confirmada.
2. ✅ **Parcial** — `Armazém` já saiu do conjunto que usa PIN no GestNow (feito; zero contas reais afetadas hoje). `Chefe de Equipa` ainda não sai — isso depende da migração das suas peças para o cps-ponto estar concluída primeiro (secção 1, "Sequenciamento").
2b. **Bloqueado até a migração do Chefe estar concluída** (ver `DESENHO_FLUXO_PONTO.md`): só depois disso, cortar por completo o acesso de `Chefe de Equipa` ao GestNow — sem mensagem nenhuma a remeter para o cps-ponto, simplesmente deixa de haver credencial nenhuma que funcione para esse Tipo aqui.
3. Remover o ecrã "Acesso antigo (por Nome)" do GestNow — só depois do passo 1 estar confirmado para toda a gente.
4. Simplificar a via principal do GestNow para só password, sem ramo de PIN.
5. Construir o ecrã de Número + PIN no cps-ponto, de raiz.
6. Construir, na criação de colaborador (RH, GestNow), a geração do PIN inicial aleatório mostrado ao RH, e o campo de categoria profissional.
7. Substituir as credenciais de teste dos técnicos atuais por Números + PIN gerados pelo mecanismo do passo 6.
8. Construir, no fim dos 4 passos do onboarding (cps-ponto), o bloqueio até à troca do PIN inicial por um próprio.
9. Retirar o login por Nome+Password do cps-ponto — só depois de confirmado que todos os técnicos ativos já têm Número + PIN a funcionar (passo 7), pelo mesmo cuidado do passo 1, agora para eles.
10. Tornar o email obrigatório na ficha de colaborador, e confirmar que todos os colaboradores existentes já têm email preenchido.
11. Ligar o SMTP e construir a recuperação automática por email (decisão 7) — por último, sem nada antes a depender disto.

---

## 4. Onde a falta de SMTP bloqueia, e o que se pode fazer sem ele

**Só bloqueia a decisão 7** — a recuperação automática de PIN por email. Não bloqueia nada mais: os passos 1 a 9 (acesso e onboarding) não dependem de email nenhum para funcionar.

Enquanto o SMTP não estiver ligado, um PIN esquecido continua a resolver-se pelo caminho que já existe hoje: o bloco de RH "Redefinir PIN" no GestNow, à mão. Não é a experiência final desejada, mas já é uma via de recuperação real e funcional — ninguém fica bloqueado à espera do SMTP, só sem a conveniência de o resolver sozinho.

---

Nada disto foi implementado. Sem prazo definido.

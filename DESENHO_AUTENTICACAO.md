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
6. **Primeira entrada**: o colaborador faz os 4 passos do onboarding com o PIN inicial. No fim, fica bloqueado até definir um PIN próprio.
7. **PIN esquecido**: recuperação automática por email.

### Pré-requisitos
- Email passa a ser obrigatório na ficha de colaborador — não desenhar para o caso de não haver email.
- Configuração de SMTP fica para o fim — a recuperação por email é a última peça, não pode bloquear nada anterior.

### Prioridade
Primeiro o acesso (decisões 1-4), depois os 4 passos do onboarding com PIN inicial (decisões 5-6), depois a recuperação (decisão 7).

### Tensão a resolver antes de avançar — não decidida aqui

A decisão 2 diz "só papéis administrativos têm acesso" ao GestNow. Mas o trabalho já feito nesta conversa sobre o ecrã do Chefe de Equipa manteve, de propósito, as abas Equipa/Folha de Ponto/HSE/Pedidos no GestNow para o Chefe — o que implica o Chefe continuar a precisar de entrar no GestNow, não só no cps-ponto. Isto não bate certo com "só administrativos". Precisa de decisão explícita: o Chefe de Equipa mantém conta de password no GestNow (para essas abas), ou essas abas saem do GestNow a favor do cps-ponto? Não avancei nenhum lado desta escolha.

---

## 2. O que existe hoje e não cabe neste desenho

### GestNow
- A "via principal" de login já existe, por Número de Colaborador — mas hoje despacha por Tipo entre PIN e Password (`TIPOS_PIN = {Técnico, Instrumentista, Engenheiro, Chefe de Equipa, Armazém}`). O PIN, para quem fica no GestNow, deixa de fazer sentido — `Armazém` (e, pendente da tensão acima, `Chefe de Equipa`) têm de sair deste conjunto.
- O ecrã "Acesso antigo (por Nome)", com formulários próprios de Password e PIN, fica todo obsoleto (decisão 4).
- O bloco de RH "Redefinir PIN / Desbloquear conta" (`mod_admin_rh.py`) mantém-se válido — passa a ser sobre o PIN de acesso ao cps-ponto, geríve a partir do GestNow, e serve de recuperação manual enquanto o email (decisão 7) não estiver ligado.

### cps-ponto
- O login de hoje é só Nome + Password — não existe noção nenhuma de Número de Colaborador nem de PIN neste repositório. Não é um ajuste, é construção nova: o ecrã de número+PIN não tem nada para reaproveitar aqui, só a coluna `PIN` e o hashing já existentes no `usuarios.csv` partilhado.
- O onboarding (já a ser migrado para aqui, decisão de trabalho anterior) ainda não tem o conceito de "PIN inicial gerado pelo RH" nem a troca obrigatória de PIN no fim (decisões 5 e 6) — é trabalho novo, não uma correção do que já existe.

---

## 3. Ordem de dependência

A prioridade número um, em qualquer momento desta lista, é **nunca ficar sem forma de entrar** — nem tu, nem os técnicos que hoje trabalham.

1. **Verificar, sem implementar nada**: confirmar que todas as 8-10 contas administrativas (incluindo a tua) têm Número de Colaborador atribuído e conseguem entrar com sucesso pela via principal (número + password) — antes de tocar em qualquer coisa que dependa disso. Esta verificação é o que impede um bloqueio acidental.
2. Tirar `Armazém` (e, consoante a decisão da tensão em aberto, `Chefe de Equipa`) do conjunto de tipos que usam PIN no GestNow.
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

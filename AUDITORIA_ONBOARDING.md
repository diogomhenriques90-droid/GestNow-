# Auditoria — Onboarding do colaborador (GestNow + cps-ponto)

Data: 06/09/2026. Feita por leitura direta do código dos dois repositórios — nada foi alterado em código, dados ou produção.

---

## Resumo executivo

Existem **duas implementações independentes do mesmo onboarding de 4 passos** — uma em cada app, cada uma a escrever nas mesmas colunas do `usuarios.csv` partilhado, sem que nenhuma redirecione para a outra (ao contrário do que aconteceu com o registo de ponto, que foi conscientemente desativado num lado a favor do outro). E o que achavas ser o 4º passo — assinar o contrato — não é um passo do onboarding em nenhuma das duas apps: é um 5º bloco, à parte, que só aparece depois de alguém do RH enviar o contrato manualmente noutro ecrã do GestNow. Sem essa ação, a pessoa completa os 4 passos e entra a usar a app livremente, sem nunca ver nada sobre contrato.

---

## 1. Onde acontece cada passo, e o que faz

A ordem real, nas duas apps, **não bate certo** com a que tinhas em mente. É a mesma nas duas:

| # | Passo real | GestNow | cps-ponto |
|---|---|---|---|
| 1 | **Documentos** (lista única, não "da função") | `app.py:130-216` | `_render_onboarding`, app_ponto.py |
| 2 | **Preço/Hora** (Aceitar/Recusar) | `app.py:218-279` | idem |
| 3 | **Perfil** (dados pessoais, morada, contacto de emergência) | `app.py:281-431` | idem |
| 4 | **Comprovativo IBAN** (upload) | `app.py:433-489` | idem |

Os dois blocos de "Documentos" não filtram por cargo/função apesar do nome sugerir isso — é uma lista fixa (`pdfs_obrigatorios.csv`), igual para toda a gente.

**O contrato é um 5º bloco, separado, só do lado do GestNow**: `app.py:695-794`, só visível se `Contrato_Enviado == 'Sim'`. Essa condição é escrita por um Admin do RH, num ecrã dedicado (`mod_admin_rh.py`), num fluxo próprio de três ações manuais: **Gerar Contrato** (a partir de um template) → **Marcar como Enviado ao Colaborador** (notifica a pessoa) → **Validar Contrato Assinado** (depois de a pessoa fazer upload da versão assinada). Este fluxo do lado do Admin está bem feito — usa registo de auditoria como deve ser, ao contrário de quase tudo o resto que já vimos nesta auditoria. O problema não é este fluxo em si: é que **nada nos 4 passos do onboarding avisa a pessoa (nem o admin) de que este 5º passo existe e está pendente** — não há nenhuma ligação visível entre "acabei os 4 passos" e "falta o contrato".

O cps-ponto tem o código para ler o mesmo estado de contrato (`_verificar_contrato`), mas nunca escreve `Contrato_Enviado` — essa ação só existe do lado do GestNow.

---

## 2. Partido, incompleto, código morto

**Nos dois lados, de forma independente (o mesmo defeito, implementado duas vezes):**
- **Recusar o preço/hora não leva a lado nenhum.** O código só verifica se o campo está vazio; "Recusado" conta como passo cumprido, exatamente como "Aceite". Quem recusa avança na mesma, sem ecrã de renegociação.
- Validação do Perfil é só "campo não vazio" — NIF, datas e outros campos aceitam qualquer texto, sem verificar formato.

**Só no GestNow:**
- O bloco do contrato (`app.py:695-794`) está envolvido num `try/except Exception: pass` genérico — qualquer erro ao ler o estado do contrato faz o bloco inteiro desaparecer em silêncio, sem aviso a ninguém.
- O Passo 1 (Documentos) nunca bloqueia ninguém se não houver nenhum PDF configurado no admin — não é tratado como erro, é tratado como "não há nada a validar".

**Só no cps-ponto:**
- O contrato só pode ser aceite — não há forma de o colaborador pedir alteração ou rejeitar.

---

## 3. Onde falha em silêncio

- **O mesmo padrão de escrita já identificado no `registos.csv` repete-se aqui, no `usuarios.csv`**: cada passo lê o ficheiro inteiro, altera a linha da pessoa, grava o ficheiro inteiro de volta — sem bloqueio nem verificação de concorrência. `usuarios.csv` é tocado a cada login de toda a gente, nas duas apps, ao mesmo tempo; com o crescimento anunciado para outubro, o risco de duas escritas simultâneas apagarem dados uma da outra é real, tal como já está identificado (e em plano) para o ponto.
- **Nenhuma das ~11 chamadas a gravação ao longo dos 4 passos (nas duas apps) verifica se a gravação teve sucesso.** É o mesmo padrão já conhecido do resto da app: a pessoa vê "Guardado!" mesmo que nada tenha sido gravado, e ao voltar pode cair no mesmo passo outra vez sem perceber porquê — parece um erro do sistema, não uma explicação do que aconteceu.
- **No GestNow, a notificação ao admin no fim do Passo 3 (Perfil) diz "completou todos os passos de integração"** — mas o Passo 4 (IBAN) ainda não foi feito nesse momento. É um aviso prematuro, um passo a menos do que devia.
- Se o registo de PDFs já vistos ficar corrompido (nas duas apps), a pessoa perde esse progresso em silêncio e tem de confirmar os documentos outra vez — não por ter parado a meio, mas por um erro de leitura absorvido sem aviso.

---

## 4. Consegue chegar ao fim sozinho, hoje, sem intervenção?

**Para os 4 passos (Documentos → Preço → Perfil → IBAN): sim**, em qualquer uma das duas apps, desde que a empresa já tenha configurado um preço/hora e, se aplicável, os documentos obrigatórios. Não há nenhuma aprovação intermédia a bloquear estes 4 passos.

**Para o contrato: não, por desenho, e isso está correto** — exige mesmo uma ação humana do RH (gerar e enviar o contrato). O problema não é essa exigência em si, é que **a pessoa completa os 4 passos e entra a usar a app livremente, sem nenhum aviso de que ainda falta assinar um contrato** — a menos que o RH se lembre de tratar disso, sem nenhum gatilho automático a avisar que "esta pessoa já está pronta para receber o contrato".

---

## 5. Parar a meio e voltar

Nas duas apps, o progresso é resistente a interrupções: tudo fica gravado célula a célula em `usuarios.csv`, não em nada temporário de sessão. Fechar o browser, mudar de dispositivo, voltar dias depois — a app relê o estado atual da conta e retoma exatamente no primeiro passo por fazer, incluindo o progresso dentro dos Documentos (sabe quais já foram vistos, um a um). A única exceção é o cenário já descrito de corrupção do registo de PDFs vistos, que obriga a repetir esse passo.

---

## Nota final

Dois pontos que valem a pena decidir, não só corrigir:

1. **Porque é que o onboarding continua duplicado nas duas apps**, ao contrário do registo de ponto (que foi conscientemente concentrado no cps-ponto)? Não há, em nenhum dos dois códigos, uma decisão ou comentário a explicar isto — parece ter ficado por decidir, não por escolha.
2. **O contrato devia estar mais ligado aos 4 passos** do que está hoje — mesmo mantendo a assinatura como ação manual do RH, faria sentido que o fim dos 4 passos disparasse um aviso automático a quem gere contratos, em vez de depender de alguém se lembrar.

Esta auditoria foi feita inteiramente por leitura de código nos dois repositórios. Nada foi alterado.

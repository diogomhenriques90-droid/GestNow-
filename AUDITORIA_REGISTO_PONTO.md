# Auditoria — Registo de Ponto no GestNow

Data da auditoria: 2026-09-06
Âmbito: só leitura — código-fonte deste repositório (GestNow) e dados reais em `gs://gestnow-dados/data/registos.csv` e `usuarios.csv`. Nada foi alterado em código, dados ou produção.

---

## 1. Funcionalidades e diferenças em relação ao cps-ponto

**Achado central: o GestNow já não regista ponto.** A introdução de horas está desativada em todo o GestNow — tanto no ecrã do Técnico como no do Chefe de Equipa, o botão que antes abria o formulário de registo foi substituído por uma mensagem a redirecionar explicitamente para a app cps-ponto, com um comentário no código a dizê-lo sem ambiguidade. O formulário antigo (seleção de obra, frente, horas de entrada/saída, gravação do registo) continua fisicamente no código, mas está inacessível — é código morto, não uma funcionalidade em uso.

O que o GestNow **ainda faz** hoje, a jusante do registo em si:
- **Consulta do histórico** pelo próprio técnico (calendário semanal com o estado de cada dia).
- **Cadeia de validação de horas**: Chefe de Equipa valida/rejeita → Secretariado faz 1ª e 2ª validação → passagem a faturação → processamento de pagamento.
- **Folha de Ponto semanal com "assinatura" do cliente**, gerada pelo Chefe de Equipa, com um caminho digital (confirmação por nome, sem desenho de assinatura) e um caminho manual (upload da folha assinada em papel).
- **Recibos de vencimento** gerados a partir das horas já validadas, para efeitos de RH.
- Notificações e registo de auditoria em cada validação, rejeição e pagamento.

O que o GestNow **não faz** (apesar de o esquema de dados ainda ter colunas para isso, nunca preenchidas): não captura GPS nem fotografias no momento do registo. Isso ficou do lado do cps-ponto.

**O que o cps-ponto tem, segundo confirmação direta da equipa/sessão desse repositório:**
- Check-in/check-out com GPS, permitindo vários períodos/turnos no mesmo dia.
- Edição e eliminação do próprio registo pelo técnico, mas só enquanto está "Pendente" — depois de validado, fica bloqueado.
- Geração da Folha de Ponto oficial (Excel → PDF), com assinatura por canvas (desenhada) além da opção de upload manual — portanto, ao contrário do que dissemos acima para o GestNow, o cps-ponto tem uma captura de assinatura mais robusta.
- Notificações internas, reporte de incidentes de segurança (HSE), onboarding obrigatório e assinatura de contrato.
- Instalável como aplicação (PWA), pensada para o técnico no telemóvel em obra.
- Não tem fotografia associada ao check-in — só GPS.

**Ponto de atenção que não conseguimos fechar com certeza**: a cadeia de validação descrita pelo lado do cps-ponto ("Chefe → 1ª validação no Secretariado, fora do cps-ponto → 2ª validação por um papel 'Gestor', dentro do cps-ponto → Faturação") não bate certo com a cadeia que vemos do lado do GestNow (onde o Secretariado, aqui, parece fazer tanto a 1ª como a 2ª validação). Isto sugere que **pode haver sobreposição ou ambiguidade sobre em qual dos dois sistemas certos passos de validação realmente acontecem** — vale a pena confirmar isto com quem opera o processo no dia a dia, porque os dois códigos foram escritos e evoluíram de forma independente sobre o mesmo ficheiro de dados.

**Ligação técnica entre os dois sistemas**: não há nenhuma sincronização, API ou importação de dados entre GestNow e cps-ponto — a única ligação visível no código é um link que abre a app cps-ponto noutro separador. Mas confirmámos (por informação direta da sessão do cps-ponto) que **os dois repositórios apontam para o mesmo bucket de armazenamento** (`gestnow-dados`) e, aparentemente, para os mesmos ficheiros (`registos.csv`, `usuarios.csv`, `folhas_ponto.csv`). Ou seja: não há duas bases de dados que precisem de ser sincronizadas — há uma só, partilhada, com dois códigos diferentes a lerem-na e a escreverem nela. Isto explica como é que o GestNow continua a mostrar registos novos mesmo tendo desativado o seu próprio formulário: o mais provável é que seja o cps-ponto a escrever as linhas novas diretamente no mesmo `registos.csv` que o GestNow depois lê para validar, faturar e pagar. Não confirmámos isto a 100% (não temos visibilidade total do código do cps-ponto), mas é a explicação mais consistente com os factos observados.

---

## 2. Quem usa isto hoje

Fomos aos dados reais em produção (leitura direta ao ficheiro em GCS, nada foi alterado nem apagado).

- `registos.csv` tem **79 linhas no total**, com a escrita mais recente em 2026-09-01.
- Aparecem **12 nomes distintos** como autores de registos: Jorge Oliveira (29), Diogo Henriques (18), Cleudir Rodrigues (9), Alexandre Reis (5), Shayan Shafie (4), Rafael Correia (3), Cesar Flor (3), Diana Plácido (3), Patrícia Oliveira (2), Rafael Santos (1), Renato Santos (1), Mauricio Figueiredo (1).
- Obras envolvidas: Basf, Sonae Mangualde, Sines, Luso Finsa, Greenvolt, EFUELS, Escritório.

**Limitações importantes que encontrámos nos próprios dados** (e que já são, em si, um achado da auditoria):
- A coluna de data está vazia em 78 das 79 linhas — só a primeira tem data preenchida. **Não é possível, a partir do ficheiro, dizer em que mês cada registo foi feito.** Não conseguimos, portanto, dar-te uma série mensal fiável de "registos por mês nos últimos meses" — os dados não têm essa informação gravada.
- Não existe uma chave comum fiável entre `registos.csv` (que guarda nomes abreviados, tipo "Cleudir Rodrigues") e `usuarios.csv` (que guarda o nome legal completo, tipo "Cesar Josue Lopez Garcia", sem coluna de utilizador/login comum). Só conseguimos confirmar o tipo de utilizador para 3 dos 12 nomes: Jorge Oliveira é Chefe de Equipa; Diogo Henriques, Diana Plácido e Mauricio Figueiredo são Admin. Para os restantes 9 nomes não há forma fiável de saber, só a partir dos dados, se são Técnicos, Chefes ou outra coisa.
- **Não conseguimos comparar com o cps-ponto**: pedimos à sessão que tem acesso a esse repositório números de utilização equivalentes, mas recusou puxar dados reais de produção sem autorização do respetivo utilizador — corretamente, na nossa opinião, dado que não é uma decisão que se deva tomar entre sessões sem essa luz verde. Isto significa que **não podemos responder com confiança se há pessoas que usam só o GestNow e nunca o cps-ponto** — precisarias de pedir esse cruzamento diretamente a quem gere o cps-ponto, ou autorizar explicitamente essa consulta.

Em resumo honesto: os números existem e são baixos (79 registos, 12 pessoas), mas a qualidade dos próprios dados (datas em falta, sem chave de cruzamento) impede-nos de dar uma resposta mais fina sobre tendência mensal ou sobreposição de utilizadores com o cps-ponto.

---

## 3. O que se perderia se este módulo desaparecesse e tudo passasse pelo cps-ponto

Partindo do que apurámos no ponto 1 — que o GestNow **já não é onde a hora é registada**, só onde é validada, faturada e usada para RH — "desaparecer o registo de ponto do GestNow" não é hoje uma operação de tirar o check-in a alguém (isso já não existe aqui). O que estaria realmente em causa é mover para o cps-ponto (ou para outro lado) estas peças:

- A **cadeia de validação por Chefe de Equipa e Secretariado**, com os estados intermédios (pendente/validado/faturação/pago/rejeitado).
- A **geração da Folha de Ponto semanal com confirmação do cliente**, incluindo o caminho de upload manual da folha assinada em papel — isto parece ser mais rico no lado do GestNow do que a "assinatura digital" que aqui existe (que, já se avisa no ponto 4, não é uma assinatura real).
- A **geração de recibos de vencimento** a partir das horas validadas, ligada ao módulo de RH.
- O ecrã de **consulta do histórico** pelo próprio técnico dentro do GestNow (redundante se o técnico já consulta o mesmo histórico no cps-ponto, mas é preciso confirmar se o cps-ponto mostra a mesma informação pós-validação/faturação).

Como o cps-ponto, segundo a informação recebida, também já tem uma parte do fluxo de validação (papel "Gestor" faz uma validação lá dentro), a pergunta "o que se perderia" depende de resolver primeiro a ambiguidade apontada no ponto 1 sobre onde é que cada validação realmente acontece hoje. Sem resolver essa ambiguidade, há o risco de subestimar o que teria de ser recriado no cps-ponto — ou de descobrir que já lá existe, duplicado.

---

## 4. Erros, bugs e código morto encontrados

### Crítico

- **Validações concorrentes podem apagar-se silenciosamente umas às outras.** O padrão em `mod_chefe.py`, `mod_tecnico.py` e `mod_secretariado.py`, ao validar ou rejeitar registos, é sempre: carregar o ficheiro completo para memória no início do ecrã, alterar linhas, e gravar o ficheiro completo de volta. Se dois chefes (ou um chefe e a secretaria) estiverem a validar ao mesmo tempo, quem gravar por último sobrescreve o ficheiro inteiro com a sua versão desatualizada — apagando sem aviso validações ou registos novos criados entretanto por outra pessoa. A proteção existente contra perda de dados (que bloqueia gravações que percam mais de 10% das linhas) não deteta este caso, porque compara com um instantâneo tirado no início da própria sessão, não com o estado atual em produção. **Isto agrava-se com a descoberta de que o cps-ponto escreve possivelmente no mesmo ficheiro** — o risco de conflito não é só entre pessoas dentro do GestNow, pode ser entre o GestNow e o cps-ponto a escrever ao mesmo tempo.
- **O formulário de registo de ponto está desativado, mas o texto que o sistema mostra ao técnico ainda promete que ele pode "corrigir e voltar a submeter" depois de uma rejeição.** Não há, hoje, nenhuma forma de o fazer dentro do GestNow — é um beco sem saída para quem recebe essa mensagem.

### Médio

- **Uma "Folha com Selo" pode ficar marcada como "Assinado" sem qualquer assinatura real.** O caminho digital de assinatura grava sempre um campo de assinatura vazio; o que realmente "certifica" a folha é só um nome escrito à mão pelo utilizador e um código aleatório gerado no momento. Só o caminho manual (upload da folha em papel) tem prova real. Para um documento que alimenta faturação e RH, isto é um ponto de confiança fraco. Também não há proteção contra gerar a mesma folha duas vezes (dois cliques, ou duas pessoas a gerar em simultâneo criam duas folhas "assinadas" diferentes).
- Existe lógica que testa se o utilizador é "Chefe de Equipa" ou "Gestor" dentro do ecrã do Técnico — mas o encaminhamento da aplicação já garante que esses perfis nunca chegam a esse ecrã. Não causa erro nenhum hoje, mas é código morto que engana quem lê e mantém o ficheiro.
- Um cálculo de número de período (ao gravar vários turnos no mesmo dia) pode atribuir o mesmo número a dois turnos diferentes, se tiverem exatamente a mesma hora de entrada e saída — inofensivo enquanto o formulário estiver desativado, mas reaparece se for reativado sem correção.

### Baixo (código morto / limpeza)

- Cerca de 600 linhas duplicadas dentro do ecrã do Técnico, que replicam (de forma diferente) funcionalidade de validação que já existe no ecrã do Chefe de Equipa — e que nunca podem ser executadas, porque o encaminhamento da app já desvia esses perfis antes de lá chegarem.
- O formulário de registo de ponto em si (cerca de 280 linhas), morto mas ainda presente em dois ficheiros diferentes (Técnico e Chefe), com lógica quase idêntica — qualquer correção futura, se for reativado, tem de ser feita a dobrar.
- Três colunas no esquema de dados (`Localização Check-in`, `Localização Check-out`, `Tipo de Frente`) que nunca são escritas nem lidas em lado nenhum — resíduos de uma funcionalidade de geolocalização que aparentemente nunca chegou a existir no GestNow.
- Um import relacionado com captura de assinatura por desenho (canvas) que parece não ser usado no ecrã do Técnico.
- No ecrã de validação do Chefe de Equipa, o filtro de obras não parece estar limitado às obras onde esse chefe está especificamente alocado — o que poderia, em teoria, permitir ver/validar registos de obras alheias. Não confirmámos com certeza absoluta se há um filtro anterior no código que já resolve isto.
- As funções principais dos ecrãs de Técnico e Chefe são muito extensas (cerca de 2000 linhas cada, tudo numa função só), o que não é um erro em si, mas torna mais fácil uma alteração futura mexer sem querer noutro fluxo vizinho.

---

## Nota final

Esta auditoria foi feita inteiramente por leitura — código-fonte deste repositório e dados reais em produção descarregados temporariamente e apagados após a análise. Não foi escrito nem alterado nada em produção, em código, ou no cps-ponto. Alguns dos achados (sobretudo a hipótese de o cps-ponto escrever diretamente no mesmo `registos.csv`, e a ambiguidade sobre onde acontece cada etapa de validação) dependem de confirmação de quem opera ou conhece melhor o cps-ponto — recomenda-se validar isso antes de decidir seja o que for sobre descontinuar qualquer uma das partes.

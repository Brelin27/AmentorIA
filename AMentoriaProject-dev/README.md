# 📚 amentorIA

**amentorIA** é um sistema de tutoria inteligente baseado em IA, focado na
preparação para o ENEM. Utilizando uma abordagem socrática, a plataforma guia o
aluno através de dicas progressivas, incentivando o raciocínio e o aprendizado
ativo, em vez de apenas fornecer respostas prontas.

---

## 🚀 Visão Geral

O objetivo do projeto é criar um tutor virtual capaz de:

- Ajudar estudantes a resolver questões do ENEM
- Estimular o pensamento crítico através de dicas graduais
- Gerar exercícios inéditos para fixação
- Fornecer aos professores visibilidade completa do aprendizado dos alunos

---

## 🧠 Como Funciona

O **amentorIA** atua como um professor que não entrega a resposta de imediato.
Em vez disso:

1. O aluno envia uma dúvida (texto ou imagem)
2. A IA identifica o tema (Matemática, Humanas, etc.)
3. O sistema fornece **dicas progressivas**
4. Caso necessário, apresenta a **resolução completa**
5. Ao final, gera uma **nova questão para fixação**

---

## 🏗️ Arquitetura Distribuída

O **amentorIA** é construído sobre uma **arquitetura cliente-servidor de 3
camadas**, onde cada componente opera de forma independente e se comunica
através de protocolos de rede bem definidos.

### Componentes do Sistema

| Componente         | Tecnologia                       | Responsabilidade                               |
| ------------------ | -------------------------------- | ---------------------------------------------- |
| **Frontend**       | Next.js (React)                  | Interface do usuário para alunos e professores |
| **Backend**        | FastAPI (Python)                 | API REST, lógica de negócio, autenticação      |
| **Banco de Dados** | PostgreSQL (Docker)              | Persistência de usuários, histórico e sessões  |
| **Serviço de IA**  | OpenAI GPT-4o-mini (API externa) | Geração de respostas socráticas                |

### Diagrama da Arquitetura

![Arquitetura do Projeto](Arquitetura%20Projeto.png)

### Protocolos de Comunicação

- **Frontend para Backend:** HTTP/REST com JSON. O frontend consome a API do
  FastAPI via `fetch`, enviando e recebendo dados em formato JSON.
- **Backend para PostgreSQL:** TCP via SQLAlchemy ORM. O backend gerencia
  conexões com o banco usando um pool de conexões do SQLAlchemy.
- **Backend para OpenAI API:** HTTPS/REST via OpenAI Python SDK. Cada mensagem
  do aluno gera uma requisição autenticada à API externa.

### Justificativa da Escolha Arquitetural

A arquitetura cliente-servidor de 3 camadas foi escolhida por adequar-se
diretamente ao contexto do projeto:

- **Separação de responsabilidades:** o frontend cuida da experiência do
  usuário, o backend concentra toda a lógica de negócio (autenticação, controle
  de limite de interações, persistência) e o banco garante a durabilidade dos
  dados.
- **Escalabilidade independente:** cada camada pode ser escalada separadamente.
  O frontend já está publicado na Vercel e o backend pode ser replicado
  horizontalmente sem afetar o banco.
- **Integração com serviço externo:** a API da OpenAI funciona como um
  componente distribuído adicional, desacoplado do backend, o que evita
  dependência de uma implementação local de IA.

---

## ⚡ Concorrência e Paralelismo

O projeto aplica concorrência em três pontos do backend, todos no componente
FastAPI (Python).

### 1. Thread Pool para chamada à OpenAI - `routers/chat.py`

```python
async def enviar_duvida(mensagem: ChatMessage, ...):
    texto_resposta_ia = await run_in_threadpool(
        ai_service.gerar_resposta, ...
    )
```

**Mecanismo:** Thread pool via `starlette.concurrency.run_in_threadpool`

A função `gerar_resposta()` é síncrona e bloqueante, pois aguarda a resposta da
API da OpenAI, o que pode levar vários segundos. Executá-la diretamente dentro
de um endpoint `async` travaria o event loop inteiro do FastAPI durante esse
tempo, impedindo o servidor de atender qualquer outro usuário. Ao delegar a
execução para uma thread do pool, o event loop permanece livre para processar
outras requisições enquanto a chamada à IA está em andamento.

### 2. Corrotinas (async/await) - FastAPI event loop

**Mecanismo:** Corrotinas via `asyncio` (nativo do FastAPI/Starlette)

Os endpoints do backend são definidos com `async def`, o que permite ao servidor
atender múltiplas requisições HTTP de forma concorrente sem alocar uma thread
por conexão. O event loop do asyncio alterna entre as corrotinas enquanto cada
uma aguarda operações de I/O (banco de dados, rede), maximizando o uso do
servidor com baixo custo de recursos.

### 3. Pool de conexões com o banco - `core/database.py`

```python
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
```

**Mecanismo:** Connection pool do SQLAlchemy

Em vez de abrir e encerrar uma conexão com o PostgreSQL a cada requisição, o
SQLAlchemy mantém um pool de conexões ativas que são reutilizadas entre threads
e corrotinas concorrentes. O `pool_pre_ping=True` garante que conexões inativas
sejam verificadas antes do uso, evitando erros em produção.

---

## 🔧 Otimização

### Otimizações já implementadas

**1. Truncamento de histórico e controle de tokens -
`services/gemini_service.py`**

A função `truncar_historico()` aplica três camadas de controle antes de cada
chamada à OpenAI:

- Trunca mensagens individuais que ultrapassam 1500 caracteres
- Mantém apenas as últimas 10 mensagens do histórico da conversa
- Estima o total de tokens (~4 caracteres por token) e remove mensagens mais
  antigas se o limite de 3000 tokens estimados for ultrapassado

O impacto direto é a redução no custo por requisição e no tempo de resposta da
IA, já que prompts menores são processados mais rápido.

**2. Rate limiting diário por usuário - `services/crud.py`**

A função `verificar_e_incrementar_limite()` consulta o banco antes de qualquer
chamada à OpenAI. Se o aluno já atingiu o limite diário de interações, o sistema
retorna imediatamente uma mensagem local, sem fazer a requisição à API externa.

Isso evita chamadas desnecessárias à OpenAI, controlando custos e protegendo o
serviço contra uso excessivo.

**3. Memoização da lista ordenada no frontend -
`frontend/src/lib/ordenecao.ts`**

```ts
const dadosOrdenados = useMemo(() => {
    return ordenacao(dadosIniciais, ordenarPor, ...);
}, [dadosIniciais, ordenarPor, direcao, ...]);
```

A lista de alunos e históricos só é reordenada quando alguma dependência real
muda (dados, critério ou direção). O `useMemo` evita que a operação de ordenação
seja executada a cada re-render do componente.

**4. Funções estabilizadas com `useCallback` - frontend**

Funções de fluxo de chat como `handleAnswer`, `handleTipFlow` e `sendMessage`
são criadas com `useCallback`, o que evita que componentes filhos recebam uma
nova referência de função a cada render e se re-renderizem desnecessariamente.

---

### Otimizações que poderiam ser aplicadas futuramente

**1. Streaming da resposta da IA**

Atualmente o backend aguarda a resposta completa da OpenAI antes de retornar ao
frontend. A API da OpenAI suporta streaming de tokens, o que permitiria exibir a
resposta palavra por palavra, reduzindo o tempo percebido de espera pelo aluno.

**2. Cache de respostas para perguntas frequentes**

Perguntas idênticas ou muito similares poderiam ter a resposta cacheada por um
período (ex: Redis com TTL de algumas horas), evitando chamadas repetidas à
OpenAI para o mesmo conteúdo.

**3. Índices no banco de dados**

As queries mais frequentes filtram por `aluno_email` e `data` na tabela de uso
diário e histórico. Adicionar índices nessas colunas reduziria o tempo de
consulta conforme o volume de dados crescer.

**4. Compressão de imagens antes do envio**

Imagens enviadas pelo aluno são convertidas para base64 e enviadas diretamente.
Redimensionar e comprimir a imagem no frontend antes do envio diminuiria o
tamanho do payload e o tempo de upload.

---

## 🧱 Tecnologias

- **Frontend:** Next.js / React / TypeScript / Tailwind CSS / Zustand
- **Backend:** Python / FastAPI / SQLAlchemy / Pydantic
- **IA:** OpenAI GPT-4o-mini
- **Banco de Dados:** PostgreSQL (Docker)
- **Autenticação:** JWT (JSON Web Tokens)
- **Infraestrutura:** Docker (banco de dados), Vercel (frontend)

---

## 📌 Status do Projeto

Em desenvolvimento

---

## 👥 Equipe

- Arthur Lima
- Bruno Dornelas
- Bruno Castilho
- Felipe Cisneiros
- Paulo Henrique

---

## 📄 Licença

Este projeto está sob a licença MIT.

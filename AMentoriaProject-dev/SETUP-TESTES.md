# Execução do ambiente de testes

As adaptações desta branch recuperam a instalação do frontend e permitem configurar as conexões de hospedagem. As telas, o modelo de IA, o prompt de tutoria e as regras de cadastro foram preservados.

## Local

Requisitos validados: Python 3.12.14 e Node.js 24. O backend tem alternativa SQLite; PostgreSQL não é obrigatório para o teste local.

Na pasta `AMentoriaProject-dev`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Crie `.env` nessa pasta e configure `SECRET_KEY` com um valor aleatório gerado por `python3 -c "import secrets; print(secrets.token_hex(32))"`. Para SQLite, use `DATABASE_URL=sqlite:///./amentoria.db`. Para Docker/PostgreSQL, configure uma senha própria e utilize a porta 5433 indicada no docker-compose.yml; o README-SETUP original contém uma URL de porta 5432 que não corresponde a esse mapeamento.

Configure `OPENAI_API_KEY` diretamente no `.env`, sem publicar a chave ou enviá-la para o frontend. Sem ela, cadastro e login funcionam, mas o chat responde 503, sem consumir o limite diário.

Inicie a API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Em outro terminal:

```bash
cd AMentoriaProject-dev/frontend
npm ci
npm run dev
```

Abra http://localhost:3000. A tela permite criar contas de aluno e professor; não há senha de demonstração predefinida. As contas são armazenadas no banco configurado.

## Publicação

### Backend no Render

O `render.yaml` na raiz descreve um Web Service Python no plano Free:

- Root Directory: `AMentoriaProject-dev`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check: `/`
- Python: 3.12.14
- `SECRET_KEY`: gerar um valor aleatório no servidor.
- `DATABASE_URL`: usar um PostgreSQL separado para este projeto, com SSL conforme o provedor.
- `OPENAI_API_KEY`: configurar diretamente no servidor para habilitar o tutor.
- `FRONTEND_URL`: origem HTTPS da Vercel, sem caminho nem barra final. Aceita várias origens separadas por vírgula.

O SQLite local usa arquivo e não garante persistência no disco efêmero de uma hospedagem gratuita; use PostgreSQL no ambiente publicado.

### Frontend na Vercel

- Root Directory: `AMentoriaProject-dev/frontend`
- Framework: Next.js
- Install Command: `npm ci`
- Build Command: `npm run build`
- Output Directory: padrão do Next.js.
- Node.js: 24.x
- `NEXT_PUBLIC_API_URL`: URL HTTPS do backend, sem barra final e sem `/api` no fim.

A variável pública é incorporada durante a compilação. Faça novo deploy após alterá-la. Cadastre a origem da Vercel em `FRONTEND_URL` no Render e reinicie o backend após mudar essa variável.

## Verificações realizadas

- Build de produção do Next.js e TypeScript concluído.
- Suíte existente do backend: 23 testes passaram e 1 já estava marcado para não executar.
- Integração com SQLite isolado: API, cadastro, login, criação/listagem de alunos, histórico e rejeição de requisição sem token.
- Preflight CORS da origem configurada.
- Sem chave de IA: resposta 503 sem gravar mensagem ou consumir cota.

A resposta real da OpenAI depende de chave válida e saldo/acesso do projeto de API. Nenhuma chamada real de IA foi efetuada nestas verificações. Os testes locais não equivalem a uma revisão de segurança nem validam todas as regras de permissão existentes na entrega.

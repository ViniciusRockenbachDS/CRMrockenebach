# CRM — Clientes, Funil de Vendas e Pagamentos (pronto para IA)

Sistema full stack de CRM com gestão de clientes, funil de vendas em Kanban, controle de
recebimentos/inadimplência, dashboard analítico e uma camada de Inteligência Artificial
(resumo de clientes, lead scoring e insights comerciais) que funciona offline e pode ser
ligada a OpenAI ou Anthropic trocando uma variável de ambiente.

| Camada | Tecnologias |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, JWT, Argon2 |
| Banco | PostgreSQL 16 (Docker), ENUMs nativos, índices GIN/trigram, constraints de integridade |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v4, TanStack Query, Axios, Lucide, Recharts |
| IA | Provedor heurístico offline (padrão) · OpenAI · Anthropic — com cache e rastreabilidade |

---

## Funcionalidades

- **Clientes:** cadastro completo (CPF/CNPJ e telefone validados), busca, filtros (status, origem, responsável, "sem contato há N dias"), tags e histórico de interações.
- **Funil de vendas:** Kanban com arrastar e soltar, probabilidade sugerida por etapa, motivo obrigatório ao perder e histórico de cada mudança de etapa.
- **Pagamentos:** faturas únicas ou parceladas (somente para negociações ganhas), baixa de recebimento, cancelamento e marcação automática de faturas vencidas como **Atrasado**.
- **Dashboard:** receita, ticket médio, conversão, pipeline ponderado, inadimplência, comparação com o período anterior, receita mensal, funil, origem dos leads, top clientes e maiores atrasos.
- **IA:** resumo do cliente (sentimento, riscos e próximas ações), chance de fechamento por negociação (com os fatores explicados) e insights sobre funil/receita/inadimplência.
- **Segurança e auditoria:** JWT com refresh automático, papéis (admin, gestor, vendedor), soft delete e trilha de auditoria com o diff de cada alteração.

---

## Passo a passo para rodar (primeira vez)

### 0. Instale os pré-requisitos

| Ferramenta | Versão | Link |
|---|---|---|
| Python | 3.11, 3.12 ou 3.13 (marque **"Add python.exe to PATH"** no instalador do Windows) | https://www.python.org/downloads/ |
| Node.js | 20 LTS ou 22 LTS | https://nodejs.org/ |
| Docker Desktop | qualquer versão recente | https://www.docker.com/products/docker-desktop/ |
| VS Code | recente | https://code.visualstudio.com/ |

Confira no terminal:

```bash
python --version      # macOS/Linux: python3 --version
node --version
docker --version
```

> **Sem Docker?** Instale o PostgreSQL 16 direto na máquina e crie um banco `crm`
> com usuário `crm` / senha `crm_dev_password` (ou ajuste o `backend/.env`).

### 1. Abra o projeto no VS Code

Descompacte o `.zip`, abra a pasta **`crm`** no VS Code (*File → Open Folder*) e aceite
instalar as **extensões recomendadas** quando o aviso aparecer.

### 2. Suba o banco (PostgreSQL no Docker)

Abra o Docker Desktop e espere ele iniciar. No terminal do VS Code (*Terminal → New Terminal*), na pasta `crm`:

```bash
# Windows (PowerShell):
copy .env.example .env
# macOS/Linux:
cp .env.example .env

docker compose up -d
docker compose ps            # o serviço "postgres" deve aparecer como "healthy"
```

### 3. Configure o backend

```bash
cd backend

# Ambiente virtual
python -m venv .venv
# Ative o ambiente:
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1
#   Windows (cmd):         .venv\Scripts\activate.bat
#   macOS/Linux:           source .venv/bin/activate

pip install -r requirements.txt

# Variáveis de ambiente
copy .env.example .env       # macOS/Linux: cp .env.example .env
```

> **PowerShell bloqueou a ativação?** Rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e tente de novo.

### 4. Crie as tabelas e os dados de demonstração

Ainda em `backend/`, com o ambiente virtual ativo:

```bash
python -m app.scripts.init_db        # aplica as migrations e cria todas as tabelas
python -m app.scripts.seed --demo    # cria o admin + equipe, 30 clientes, negociações e pagamentos fictícios
```

> Sem dados fictícios: rode só `python -m app.scripts.seed` (cria apenas o administrador).

### 5. Rode a API

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- **Swagger (documentação interativa):** http://localhost:8000/docs → clique em **Authorize** e entre com o admin.
- Saúde da API e do banco: http://localhost:8000/health

### 6. Rode o frontend

Abra **outro terminal** (deixe a API rodando no primeiro):

```bash
cd frontend
copy .env.example .env       # macOS/Linux: cp .env.example .env
npm install
npm run dev
```

Acesse **http://localhost:5173** e entre com:

| Usuário | E-mail | Senha |
|---|---|---|
| Administrador | `admin@crm.local` | `Admin@12345` |
| Gestora (demo) | `marina@crm.local` | `Demo@12345` |
| Vendedor (demo) | `rafael@crm.local` | `Demo@12345` |

### Nas próximas vezes

1. Abra o Docker Desktop.
2. No VS Code: **Terminal → Run Task → `CRM: iniciar tudo`** (sobe o banco, a API e o frontend).

Ou, manualmente: `docker compose up -d`, a API (passo 5, com o venv ativo) e o frontend (`npm run dev`).

---

## Usando no VS Code

A pasta `.vscode/` já vem configurada:

- **Tarefas** (*Terminal → Run Task*): subir o banco, preparar o banco, gerar dados de demonstração, rodar API, rodar frontend, rodar testes ou **iniciar tudo**.
- **Depuração** (aba *Run and Debug*): `Backend: FastAPI (debug)` permite colocar breakpoints nos endpoints.
- **Interpretador Python:** aponta para `backend/.venv`. No macOS/Linux, ajuste o caminho em `.vscode/settings.json` (instrução no próprio arquivo) ou use *Python: Select Interpreter*.

---

## Arquitetura

```
crm/
├── docker-compose.yml          # PostgreSQL (+ banco de testes e pgAdmin opcionais)
├── .vscode/                    # tarefas, debug e extensões recomendadas
├── docs/DATABASE.md            # diagrama ER, constraints e índices
├── backend/
│   ├── alembic/                # migrations (async)
│   ├── app/
│   │   ├── main.py             # app FastAPI, CORS, handlers de erro, /health
│   │   ├── core/               # config (.env), segurança (JWT/Argon2), exceções, logging
│   │   ├── db/                 # Base declarativa, mixins, tipos, sessão async
│   │   ├── models/             # SQLAlchemy: users, clients, interactions, deals,
│   │   │                       # deal_stage_history, payments, audit_logs, ai_insights
│   │   ├── schemas/            # Pydantic v2: entrada, saída, filtros, dashboard, IA
│   │   ├── services/           # regras de negócio + consultas (uma camada por domínio)
│   │   ├── ai/                 # features, heurísticas, prompts versionados, provedores
│   │   ├── api/v1/endpoints/   # rotas REST
│   │   ├── scripts/            # init_db e seed
│   │   └── utils/              # validação BR (CPF/CNPJ/telefone) e datas
│   └── tests/                  # pytest (validações, schemas, IA)
└── frontend/
    └── src/
        ├── api/                # axios (refresh automático de token) + endpoints
        ├── hooks/queries.ts    # TanStack Query (cache, invalidação, update otimista)
        ├── contexts/           # autenticação e notificações
        ├── components/         # ui, layout, clientes, negociações, pagamentos, dashboard
        ├── pages/              # Login, Dashboard, Clientes, Detalhe, Funil, Pagamentos, Usuários
        ├── lib/                # formatação (BRL, datas, telefone) e constantes
        └── types/api.ts        # tipos espelhando os schemas do backend
```

Fluxo de uma requisição: **endpoint** (valida entrada com Pydantic, injeta usuário e sessão) →
**service** (regras de negócio, auditoria, commit) → **models** (SQLAlchemy) → resposta tipada.
Todo erro sai no formato `{"code", "message", "details"}`.

### Principais endpoints (`/api/v1`)

| Recurso | Rotas |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/token` (Swagger), `POST /auth/refresh`, `GET/PATCH /auth/me` |
| Usuários | `GET/POST /users`, `PATCH /users/{id}` |
| Clientes | `GET/POST /clients`, `GET/PATCH/DELETE /clients/{id}`, `GET/POST /clients/{id}/interactions` |
| Negociações | `GET/POST /deals`, `GET /deals/board`, `POST /deals/{id}/move`, `GET /deals/{id}/history` |
| Pagamentos | `GET/POST /payments`, `POST /payments/installments`, `POST /payments/{id}/pay`, `POST /payments/{id}/cancel`, `GET /payments/summary` |
| Dashboard | `GET /dashboard?date_from=&date_to=&owner_id=` |
| IA | `GET /ai/status`, `POST /ai/clients/{id}/summary`, `POST /ai/deals/{id}/score`, `POST /ai/deals/score-batch`, `POST /ai/insights`, `GET /ai/history` |

### Regras de negócio

- Pagamentos só podem ser lançados em negociações **Fechado Ganho**.
- **Fechado Perdido** exige motivo; Ganho = 100% e Perdido = 0% de probabilidade.
- Negociação com faturas ativas não pode ser reaberta nem excluída.
- Ganhar uma negociação promove o cliente a **Cliente**; abrir a primeira negociação de um lead o torna **Prospect**.
- Faturas pendentes vencidas viram **Atrasado** automaticamente.
- Clientes com negociações abertas não podem ser excluídos; exclusões são lógicas (o histórico é preservado).
- Permissões: **vendedor** opera clientes/negociações/pagamentos; **gestor** também exclui e cancela; **admin** também gerencia usuários.

---

## Inteligência Artificial

Por padrão `AI_PROVIDER=stub`: um modelo heurístico determinístico que roda sem internet e
sem custo — ideal para desenvolver e demonstrar. Para usar um LLM real, edite `backend/.env`:

```env
AI_PROVIDER=openai          # ou anthropic
AI_API_KEY=sua-chave
AI_MODEL=nome-do-modelo     # conforme a documentação do provedor
```

Reinicie a API. Nada mais muda: os contratos de resposta são os mesmos.

Como a camada foi desenhada:

- `app/ai/features.py` decide **o que** a IA enxerga (features de negociação, contexto do cliente, métricas do período).
- O lead scoring envia ao LLM a linha de base heurística junto com as features — o modelo refina em vez de partir do zero.
- Toda saída é gravada em `ai_insights` (provedor, modelo, versão do prompt, tokens, latência) e reaproveitada por cache (`AI_CACHE_TTL_HOURS`).
- `deal_stage_history` + resultado final das negociações formam um dataset rotulado para, no futuro, treinar um modelo próprio de ML.

---

## Testes

```bash
cd backend
pytest -v
```

Os testes cobrem validações brasileiras, schemas/regras de entrada e as heurísticas de IA.

---

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `connection refused` ao rodar `init_db` ou a API | O Docker não está rodando ou o container não subiu: `docker compose ps` |
| Porta 5432 ocupada (PostgreSQL local instalado) | Em `.env` (raiz) use `POSTGRES_PORT=5433` e em `backend/.env` use `POSTGRES_PORT=5433`; depois `docker compose up -d` |
| `ModuleNotFoundError: No module named 'app'` | Rode os comandos de dentro da pasta `backend/` |
| Frontend mostra "Não foi possível conectar à API" | A API precisa estar rodando em http://localhost:8000 (confira `frontend/.env`) |
| Login volta para a tela inicial | Confira se rodou `python -m app.scripts.seed` |
| Recomeçar o banco do zero | `docker compose down -v`, apague os arquivos `*schema_inicial*.py` de `backend/alembic/versions/` e refaça o passo 4 |

---

## Próximos passos sugeridos

- Deploy (Render/Railway para a API, Vercel/Netlify para o front, Neon/Supabase para o banco).
- Integração com WhatsApp e gateway de pagamento (o campo `external_reference` já existe).
- Job agendado para atualizar inadimplência e recalcular scores diariamente.
- Treinar um modelo de ML com o histórico de negociações e compará-lo com a heurística.

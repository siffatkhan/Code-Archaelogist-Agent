# Code Archaeologist

Code Archaeologist is an agentic developer-intelligence platform that explains the history, architecture, risks, and undocumented knowledge inside a software repository.

It combines static code analysis, repository history, retrieval, deterministic risk scoring, and LangGraph workflows to give maintainers grounded answers instead of generic AI suggestions.

## Features

- Analyze public GitHub repositories without executing repository code.
- Browse repository files, entities, dependencies, and architecture.
- Generate deterministic file and module risk scores.
- Ask the Historian questions grounded in analyzed repository evidence.
- Generate implementation guidance from real files and dependency data.
- Detect and track knowledge gaps for human maintainers.
- Support offboarding reports and repository history views.

## Stack

- Frontend: React 19, TypeScript, Vite, Tailwind CSS, Radix UI, Lucide React, Monaco Editor
- Backend: Python, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy
- AI and retrieval: LangGraph, Groq, sentence-transformers, vector search
- Parsing: Python AST, Tree-sitter, Babel-based JavaScript parsing
- Data and auth: Supabase, PostgreSQL, Supabase JWT authentication

## Project Structure

```text
backend/                 FastAPI application and analysis services
	app/agents/            Historian, guidance, knowledge-gap, and offboarding agents
	app/api/               HTTP route modules
	app/graph/             LangGraph state, nodes, and workflow
	app/services/          GitHub, parsing, retrieval, risk, LLM, and persistence logic
	app/schemas/           API data models
database/migrations/     Supabase/PostgreSQL schema migrations
frontend/                React and Vite application
	src/features/          Auth, repository, and explorer features
	src/pages/             Application pages
	src/services/          Backend API clients
```

## Requirements

- Python 3.10+
- Node.js 20+
- npm
- Supabase project for authentication and persistent storage
- Groq API key for live AI responses

## Configuration

Create local environment files from the committed examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Set the following values:

- `backend/.env`: `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, and optionally `SUPABASE_SERVICE_ROLE_KEY`, `GROQ_API_KEY`, and `GROQ_MODEL`
- `frontend/.env`: `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY`

Never commit `.env` files, Supabase service-role keys, JWT secrets, or API keys.

## Run Locally

Start the backend from the `backend` directory so its `.env` file is loaded:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --app-dir ..
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`. The API runs at `http://localhost:8000`, with interactive docs at `/docs`.

## Database

Apply the migrations in `database/migrations/` to a Supabase PostgreSQL database in filename order. Do not run `0000_local_auth_stub_DO_NOT_RUN_ON_SUPABASE.sql` against a real Supabase project.

## Validation

```bash
# Backend
backend/.venv/bin/python -m pytest -q

# Frontend
cd frontend
npm run build
npm run lint
```

The backend tests are mocked and do not require a live Groq request.

## Security Notes

The analyzer treats repository content as untrusted data, uses authentication for protected routes, and does not execute analyzed repository code. Keep all local environment files outside version control and rotate any credential that was accidentally exposed.
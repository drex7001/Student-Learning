# Setup And Configuration

This project is a monorepo with a FastAPI backend, a Next.js frontend, PostgreSQL for student assessment evidence, and Neo4j for the curriculum knowledge graph.

## Prerequisites

- Docker and Docker Compose
- Node.js 22 if running the frontend outside Docker
- Python 3.12 if running the API or tests outside Docker

## Environment

Copy `.env.example` to `.env` before starting the stack.

| Variable | Purpose | Default |
| --- | --- | --- |
| `POSTGRES_DB` | PostgreSQL database name | `kgis` |
| `POSTGRES_USER` | PostgreSQL user | `kgis` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `kgis` |
| `POSTGRES_PORT` | Host port for PostgreSQL | `5432` |
| `DATABASE_URL` | SQLAlchemy database URL used by the API | `postgresql+psycopg://kgis:kgis@postgres:5432/kgis` |
| `NEO4J_URI` | Neo4j Bolt URI | `bolt://neo4j:7687` |
| `NEO4J_USERNAME` | Neo4j user | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `knowledge-graph-secret` |
| `NEXT_PUBLIC_API_BASE_URL` | Browser-facing API base URL | `http://localhost:8000` |
| `CORS_ORIGINS` | Allowed frontend origins for FastAPI CORS | `http://localhost:3000,http://127.0.0.1:3000` |

For local API execution outside Docker, use localhost service URLs:

```powershell
$env:DATABASE_URL='postgresql+psycopg://kgis:kgis@localhost:5432/kgis'
$env:NEO4J_URI='bolt://localhost:7687'
$env:PYTHONPATH='.'
```

## Start The Full Stack

```powershell
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Neo4j browser: `http://localhost:7474`
- PostgreSQL: `localhost:5432`

## First-Time Data Setup

The API creates PostgreSQL tables on startup, but curriculum and synthetic evidence are loaded through internal endpoints.

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/import/curriculum
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/generate/synthetic-data -ContentType 'application/json' -Body '{}'
```

Expected current seed summary:

- 4 subjects
- 40 concepts
- 45 prerequisite edges
- 240 students
- 960 assessments
- 38,400 concept scores

## Development Commands

Backend tests:

```powershell
cd api
$env:PYTHONPATH='.'
pytest
```

Frontend checks:

```powershell
cd web
npm run lint
npm run build
```

Frontend dev server outside Docker:

```powershell
cd web
npm run dev
```

If port `3000` is already used by Docker, run:

```powershell
npm run dev -- --port 3001
```

## Resetting Seed Data

To replace existing synthetic evidence without deleting Docker volumes:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/import/curriculum
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/generate/synthetic-data -ContentType 'application/json' -Body '{}'
```

`/internal/import/curriculum` replaces Neo4j subject and concept nodes. `/internal/generate/synthetic-data` replaces PostgreSQL students, assessments, questions, question results, and concept scores.

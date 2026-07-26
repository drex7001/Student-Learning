# Setup And Configuration

## Prerequisites

- Docker and Docker Compose
- Node.js 22 and Python 3.12 if running outside Docker

## Full stack

```powershell
Copy-Item .env.example .env
docker compose up --build -d
.\scripts\reset-and-seed.ps1
```

The seed script prints demonstration accounts. All use the password `wellbeing2026`.

| Service | URL |
|---|---|
| Application | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Neo4j browser | http://localhost:7474 |
| PostgreSQL | localhost:5432 |

## Environment

| Variable | Purpose | Default |
|---|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | PostgreSQL credentials | `kgis` |
| `DATABASE_URL` | SQLAlchemy URL | `postgresql+psycopg://kgis:kgis@postgres:5432/kgis` |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Neo4j connection | `bolt://neo4j:7687`, `neo4j`, `knowledge-graph-secret` |
| `API_ORIGIN` | Where Next rewrites `/api/*` | `http://api:8000` |
| `JWT_SECRET` | Session signing key | generated per process if unset — **sessions reset on every restart** |
| `RISK_MODEL_VARIANT` | `amended` or `baseline` | `amended` |
| `CORS_ORIGINS` | Allowed origins for direct API calls | `http://localhost:3000,http://127.0.0.1:3000` |

The browser never calls the API cross-origin: it calls `/api/*` on its own origin and
Next rewrites to the API. That keeps the session cookie first-party and means the API
target is read at request time rather than inlined into the bundle at build time.

## Local development

Run the databases in Docker and the two apps natively:

```powershell
docker compose up -d postgres neo4j

# API
cd api
$env:DATABASE_URL='postgresql+psycopg://kgis:kgis@localhost:5432/kgis'
$env:NEO4J_URI='bolt://localhost:7687'
$env:JWT_SECRET='dev-secret'
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Frontend
cd web
npm run dev
```

**Use `http://localhost:3000`, not `127.0.0.1`.** The Next dev server blocks
cross-origin requests to its own dev resources, and browsing the app on a different
host than the dev server expects silently prevents hydration — React handlers never
attach and the page looks broken for no visible reason.

### Python environment

Use the project virtualenv, not a system or Anaconda Python:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api\requirements.txt -r api\requirements-dev.txt
```

## Checks

```powershell
cd api
..\.venv\Scripts\python.exe -m pytest     # 206 tests, incl. the 133 model tests

cd ..\web
npm run lint
npm run build
```

`api/pyproject.toml` sets `pythonpath`, so `PYTHONPATH` no longer needs setting by hand.

## Reseeding

```powershell
# Preserve the schema, replace the data (needs an administrator sign-in)
.\scripts\reset-and-seed.ps1 -SkipBuild -AdminUser <principal-username>

# After a model change: drop and rebuild the schema first
.\scripts\reset-and-seed.ps1 -Recreate
```

`-Recreate` is needed after any change to `api/app/db/models.py`. The API creates
tables on startup but never alters them, so a new column on an existing table is
invisible without it. All data is generated, so this costs nothing.

Order matters and the script enforces it: curriculum → risk model → roster →
assessments → derived evidence → graph projection.

## Regenerating the research artefacts

The risk model's parameters, the authored copy and the research report must stay in
step. `build_ui_data.py` cross-validates `REPORT.md`'s edge table against the code and
fails the build on drift.

```powershell
cd research\dropout-ews
..\..\.venv\Scripts\python.exe ui\build_ui_data.py ui\ui_data.json
..\..\.venv\Scripts\python.exe ui\export_model.py ui\case_data.json
node ui\verify_infer.cjs ui\case_data.json
cd ..\..
.\.venv\Scripts\python.exe scripts\build_risk_factor_copy.py
```

A test asserts that `data/seeds/risk_factor_copy.json` carries the running model's
fingerprint, so a stale copy file fails the suite rather than shipping wrong labels.

# O/L Knowledge Graph Learning Intelligence System

Greenfield monorepo for a thesis-oriented learning intelligence platform that uses Sri Lankan G.C.E. Ordinary Level subject prerequisite graphs, synthetic student mastery data, and a root-cause diagnosis engine.

## Structure

- `web` - Next.js teacher dashboard and diagnosis workspace
- `api` - FastAPI backend for curriculum import, seed generation, and diagnosis
- `data/curriculum` - prototype O/L subject graph and data dictionary artifacts
- `docs` - thesis scope and scoring specification

## Documentation

- `docs/setup-and-configuration.md` - local setup, environment variables, Docker, and common commands
- `docs/architecture.md` - system components, data flow, API surface, and frontend workflows
- `docs/curriculum-and-seeding.md` - O/L subject graph format, synthetic data generation, and extension rules
- `docs/ai-context.md` - concise context for AI coding agents working in this repo
- `docs/foundation-spec.md` - thesis scope, scoring thresholds, confidence rules, and exclusions

## Local development

1. Copy `.env.example` to `.env`.
2. Start the stack with `docker compose up --build`.
3. Import the curriculum: `POST http://localhost:8000/internal/import/curriculum`.
4. Generate synthetic data: `POST http://localhost:8000/internal/generate/synthetic-data` with body `{}`.
5. Open `http://localhost:3000`.
6. Use the API docs at `http://localhost:8000/docs`.

## Core endpoints

- `POST /internal/import/curriculum`
- `POST /internal/generate/synthetic-data`
- `GET /api/subjects`
- `GET /api/options?subject_id=OL-MATH`
- `GET /api/concepts/{concept_id}/prerequisites`
- `GET /api/diagnosis/student/{student_id}/concept/{concept_id}`

# Knowledge Graph Learning Intelligence System

Greenfield monorepo for a thesis-oriented learning intelligence platform that uses a Grade 8 algebra prerequisite graph, synthetic student mastery data, and a root-cause diagnosis engine.

## Structure

- `web` - Next.js diagnosis workspace
- `api` - FastAPI backend for curriculum import, seed generation, and diagnosis
- `data/curriculum` - locked curriculum graph and data dictionary artifacts
- `docs` - thesis scope and scoring specification

## Local development

1. Copy `.env.example` to `.env`.
2. Start the stack with `docker compose up --build`.
3. Open `http://localhost:3000`.
4. Use the API docs at `http://localhost:8000/docs`.

## Core endpoints

- `POST /internal/import/curriculum`
- `POST /internal/generate/synthetic-data`
- `GET /api/concepts/{concept_id}/prerequisites`
- `GET /api/diagnosis/student/{student_id}/concept/{concept_id}`

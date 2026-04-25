# AI Context Guide

Use this document before making code changes. It is written for AI coding agents and human maintainers who need fast project context.

## Project Goal

This is a Sri Lankan G.C.E. Ordinary Level teacher support prototype. It helps teachers select a subject, inspect learner readiness, and identify prerequisite concepts that may be causing poor performance on a target concept.

The product is not a student learning app and not a marketing website. The first screen should remain a practical teacher dashboard.

## Current Scope

Subjects:

- Mathematics
- Science
- English
- ICT

The curriculum data is prototype-aligned. Do not describe it as official syllabus coverage unless official source mapping is later added.

## Core Workflows

- `/`: teacher dashboard with subject and concept selection
- `/students`: support queue for selected subject/concept
- `/diagnosis`: one learner and one subject-wide support map, with detailed diagnosis after selecting a concept
- `/concepts`: prerequisite and downstream concept map

Keep these workflows separate. Do not collapse everything into one page.

## Important Implementation Details

- Curriculum source: `data/curriculum/ol_subject_curriculum.json`
- Synthetic config: `data/seeds/generator_config.json`
- API settings: `api/app/core/config.py`
- Graph access: `api/app/repositories/graph_repository.py`
- PostgreSQL access: `api/app/repositories/postgres_repository.py`
- Diagnosis logic: `api/app/services/diagnosis.py`
- Dashboard: `web/src/components/teacher-dashboard.tsx`
- Support queue: `web/src/components/support-queue.tsx`
- Diagnosis workspace: `web/src/components/diagnosis-workspace.tsx`
- Concept map: `web/src/components/concept-explorer.tsx`

Concept IDs are globally unique and include subject prefixes such as `MATH-`, `SCI-`, `ENG-`, and `ICT-`.

## UI Copy Rules

Use teacher-facing language:

- learner
- subject
- concept
- support
- readiness
- prerequisite
- revision
- root cause
- learning path

Avoid internal design/process language in the visible UI:

- UI Direction Reset
- Stop making one page do every job
- decision surface
- student noise
- design intent
- route is only

## API Rules

Subject selection flows through query parameters:

- `GET /api/options?subject_id=OL-MATH`
- frontend links should preserve `subject` and `concept`
- `GET /api/diagnosis/student/{student_id}/subject/{subject_id}/map` powers the main diagnosis canvas

Do not change the existing diagnosis endpoint shape unless there is a strong reason:

```text
GET /api/diagnosis/student/{student_id}/concept/{concept_id}
```

The concept itself carries `subject_id`, so this endpoint can infer subject from the target concept.

## Data Rules

When adding or editing curriculum:

- keep each subject graph acyclic
- keep edges inside one subject
- keep each subject between 8 and 30 concepts
- add Sinhala fields where practical
- update synthetic weakness profiles if new concepts should appear in generated weakness patterns

## Verification Checklist

Backend:

```powershell
cd api
$env:PYTHONPATH='.'
pytest
```

Frontend:

```powershell
cd web
npm run lint
npm run build
```

Runtime seed:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/import/curriculum
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/generate/synthetic-data -ContentType 'application/json' -Body '{}'
```

Quick API smoke checks:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/subjects
Invoke-RestMethod -Uri 'http://localhost:8000/api/options?subject_id=OL-MATH'
Invoke-RestMethod -Uri http://localhost:8000/api/diagnosis/student/STU-001/subject/OL-MATH/map
Invoke-RestMethod -Uri http://localhost:8000/api/diagnosis/student/STU-001/concept/MATH-010
```

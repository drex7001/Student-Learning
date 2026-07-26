# AI Context Guide

Fast orientation for anyone — human or agent — changing this codebase. Read
`docs/architecture.md` for the full picture.

## What this is

An early-support screening and learning-intelligence system for Sri Lankan schools
(R26-IT-165, Component 3). Two engines, deliberately separate:

- **Disengagement risk** — a discrete Bayesian network (`api/app/risk/`). Estimates a
  distribution over next-term disengagement and, more importantly, what would change
  it. Teachers and counsellors only.
- **Academic support** — prerequisite-graph diagnosis (`api/app/services/diagnosis.py`).
  Which learners need teaching attention in a subject, and why. Also drives the
  student-facing learning portal.

Do not merge these vocabularies. A learner behind in mathematics is not thereby a
learner who will leave school.

## Rules that are not negotiable

These are enforced in code and covered by tests. If a change makes one fail, the change
is wrong, not the test.

1. **Students never see a risk score.** `deny_students` in `app/core/deps.py`.
2. **`do()` is an allowlist.** Intervening on a protected characteristic returns 403.
   Never widen `MODIFIABLE_NODES` without reading `research/dropout-ews/REPORT.md` §8.
3. **Provenance travels with the number.** `provenance`, `caveat`, `interpretation`,
   `model_variant`, `model_fingerprint` are required response fields.
4. **Drivers and actions never condition on the register.** The outcome's parents
   d-separate everything else from it; conditioning on them silently zeroes every
   contribution. See `app/services/risk_explain.py`.
5. **Actions condition only on non-descendants of a lever.** Computed from the graph,
   not hardcoded.
6. **No raw identifier reaches a screen.** Labels come from
   `data/seeds/risk_factor_copy.json`; a test fails if it drifts from the model.
7. **Every flag leads to an offer of support**, never a sanction. No streaming,
   exclusion, permanent record note, or automatic referral.

## Where things live

| Concern | File |
|---|---|
| The Bayesian network | `api/app/risk/dropout_ews_bn.py` (vendored unchanged) |
| Explanation estimands | `api/app/services/risk_explain.py` |
| Risk assembly and copy | `api/app/services/dropout_risk.py` |
| Seed roster and evidence | `api/app/services/school_seed.py` |
| Graph projection | `api/app/services/graph_projection.py` |
| Access rules | `api/app/core/deps.py` |
| Cypher | `api/app/repositories/graph_repository.py` |
| Risk endpoints | `api/app/routers/risk.py`, `graph.py` |
| Design tokens | `web/src/app/globals.css` |
| API client and types | `web/src/lib/api.ts`, `web/src/lib/types.ts` |
| The record screen | `web/src/app/teacher/students/[id]/page.tsx` |
| Research record | `research/dropout-ews/` |

## Data model notes

- `student_risk_evidence` mirrors the network's own shape: one row per
  `(student, term, variable, state)`. The **absence** of a row means "not recorded",
  which is a meaningful state for the model, not missing data to impute. Clearing a
  field deletes the row.
- Concept IDs are globally unique and carry a subject prefix (`MATH-`, `SCI-`, `ENG-`,
  `ICT-`), so Postgres stores `concept_id` without a subject column.
- Neo4j is a derived view. Rebuild it with `POST /internal/project/graph`; never write
  to it as a source of truth.

## UI copy rules

Teacher-facing: learner, subject, concept, support, readiness, prerequisite, root
cause, offer of support.

Risk-facing: use the authored copy. Frame the figure as *a share of students with the
same register pattern*, never as a prediction about the child in front of you.

Never write: "AI detects student distress", "at-risk student" as a label for a person,
or anything implying an unflagged learner is fine — the low band is "nothing marked".

## Checks

```powershell
cd api;  ..\.venv\Scripts\python.exe -m pytest
cd web;  npm run lint;  npm run build
```

After any change to `api/app/db/models.py`, reseed with `-Recreate` — the API creates
tables but never alters them.

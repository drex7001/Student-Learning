# Architecture

An early-support screening and learning-intelligence system for Sri Lankan schools
(R26-IT-165, Component 3 — Monitoring, Visualization & AI Learning Support Dashboard).

It answers two different questions, and keeps them apart on purpose:

| | Disengagement risk | Academic support |
|---|---|---|
| Question | Which learners may stop attending, and what would help? | Which learners need teaching attention in this subject, and why? |
| Engine | Discrete Bayesian network, exact inference (`app/risk`) | Deterministic prerequisite-graph diagnosis (`app/services/diagnosis.py`) |
| Output | Distribution over `Low / Medium / High` | Band `high_support / watch / stable` |
| Audience | Teachers and counsellors only | Teachers; learners see the learning half |

Conflating them would be the easiest way to make this system harmful. A learner who is
behind in mathematics is not thereby a learner who will leave school.

## Components

```
                        Next.js 16 (App Router)
     /login    /student/*  (learning only)    /teacher/*  (risk + learning)
                            │  same-origin /api/*  →  rewrite  →  FastAPI
                            ▼
                        FastAPI (one service)
 ┌─────────┬────────────┬──────────────┬────────────┬───────────┬──────────┐
 │ auth    │ risk (BN)  │ graph (Neo4j)│ diagnosis  │ learn     │ internal │
 └─────────┴────────────┴──────────────┴────────────┴───────────┴──────────┘
        │           │             │             │           │
        ▼           ▼             ▼             ▼           ▼
 ┌────────────────────────────┐        ┌───────────────────────────────┐
 │ PostgreSQL  (of record)    │───────▶│ Neo4j  (derived view)         │
 │ users, schools, classes,   │project │ School/Class/Teacher/Student  │
 │ teachers, students, terms, │        │ Subject/Concept/RiskFactor    │
 │ attendance, risk evidence, │        │ REQUIRED_FOR, INFLUENCES,     │
 │ risk_assessments (audit),  │        │ HAS_MASTERY, HAS_EVIDENCE,    │
 │ concept scores, quizzes    │        │ IN_CLASS, FRIENDS_WITH        │
 └────────────────────────────┘        └───────────────────────────────┘
```

One Python environment. `pgmpy` coexists with the API's existing pins
(`numpy 2.2.5 / pandas 2.2.3 / scikit-learn 1.6.1`), so the risk engine is a module,
not a second service.

## The risk engine

`api/app/risk/dropout_ews_bn.py` is the network described in
`research/dropout-ews/REPORT.md`, vendored unchanged so the API and the research build
scripts share exactly one copy of the model and its parameters. 25 nodes, 42 edges in
the `amended` variant, fingerprint `f12dd7f40c61ecd0`.

The model is built once at startup into `app.state.risk_model` and shared; `RiskModel`
is a frozen dataclass, so reuse is safe.

**The outcome has exactly three parents** — `Current_Attendance`, `Grade_Band` and
`School_Engagement`. A complete register therefore determines the headline figure
exactly: the whole screen is twelve numbers (`GET /api/risk/screening-matrix`).
Everything else in a record tells you *what to do*, not *what to expect*.

### Explanation — what replaces SHAP

Four exact estimands, in `app/services/risk_explain.py`:

| Function | Estimand | Panel |
|---|---|---|
| `drivers` | `P(High \| bg, X=concern) − P(High \| bg, X=reference)` | What's behind it |
| `action_candidates` | `P(High \| do(levers ∪ {X:=target}), bg) − P(High \| do(levers), bg)` | What would help |
| `worth_asking` | swing over the states of an unrecorded variable | What to find out next |
| `circumstance_gap` | `P(High \| do(levers), bg)` minus the register score | Circumstances ahead |

`routes` — how a factor reaches the outcome — is a Neo4j path query.

Two conditioning rules do the real work:

1. **Drivers and actions never condition on the register.** Condition on the outcome's
   parents and every other variable becomes d-separated from it, collapsing all
   contributions to exactly zero.
2. **Actions condition only on non-descendants of any lever**, computed from the graph
   rather than hardcoded. Conditioning on a variable an action is meant to change
   would block its own effect.

## Constraints enforced in code

1. `do()` is an allowlist. Intervening on `Neuro_Type`, `Sector`, `Grade_Band` or
   `Parent_Education` returns **403**, not 422 — a forbidden question, not a malformed
   one. Invalid evidence returns 422.
2. Every risk response carries `provenance`, `caveat`, `interpretation`,
   `model_variant` and `model_fingerprint` as **required** fields.
3. `observational_conditional` and `interventional_do` are never conflated.
4. **Students never see a risk score.** Enforced by `deny_students` in the API, not by
   omitting it from the UI.
5. A student may read only their own learning record (`authorise_student_access`).
6. Every profile view writes a `risk_assessments` row: who asked, about whom, on what
   evidence, against which fingerprint.
7. No raw identifier reaches a screen — the authored copy in
   `data/seeds/risk_factor_copy.json` covers every node and state, and a test fails if
   it drifts from the model.

## Data flow

1. `POST /internal/import/curriculum` — subjects, concepts, `REQUIRED_FOR` into Neo4j.
2. `POST /internal/import/risk-model` — the 25 factors and 42 causal edges into Neo4j,
   carrying each edge's mechanism and evidence level from the edge-justification table.
3. `POST /internal/seed/school-data` — three schools across the Urban/Rural/Estate
   sectors, their classes, teachers, students, login accounts, wellbeing evidence and
   attendance. Evidence is drawn by ancestral sampling from the network itself, with
   `Sector` pinned from the school and `Grade_Band` from the class, so a learner's
   circumstances are internally consistent.
4. `POST /internal/generate/synthetic-data` — assessment evidence for those learners.
   Mastery is depressed by an academic penalty derived from the same evidence draw, so
   the two halves describe one child.
5. `POST /internal/generate/evidence` — `Current_Academic_Performance` derived from
   the resulting concept scores.
6. `POST /internal/project/graph` — the Neo4j read view.

Internal endpoints are administrator-only, except while the database has no accounts
at all: the seed creates the first administrator, so requiring one would deadlock.

## Neo4j

Postgres is the system of record; the graph is a derived view, rebuilt rather than
incrementally maintained. It exists to answer questions that span boundaries the
relational schema keeps apart.

```cypher
(:Student)-[:IN_CLASS]->(:Class)-[:AT_SCHOOL]->(:School)
(:Teacher)-[:TEACHES_CLASS]->(:Class)
(:Student)-[:HAS_MASTERY {score, band}]->(:Concept)-[:REQUIRED_FOR]->(:Concept)
(:Student)-[:HAS_EVIDENCE {state, concern, source}]->(:RiskFactor)
(:RiskFactor)-[:INFLUENCES {evidence, mechanism, confounders, concern}]->(:RiskFactor)
(:Student)-[:FRIENDS_WITH]->(:Student)
```

Four queries earn the graph its place:

- **Causal routes** — `(:RiskFactor)-[:INFLUENCES*1..6]->(outcome)`. This is the
  "why this flag?" surface, and it makes visible that no protected characteristic
  reaches the outcome except through something a school can change.
- **Shared conditions** — concerns many learners hold in common. A factor half a
  school shares is a condition of that school with a school-level fix, not a list of
  children to watch. This reading is the ethical point of the whole screen.
- **Peer ties** — few connections is a prompt to look. Ties are generated, not
  surveyed, and are labelled as such wherever shown.
- **Root causes** — weak concepts joined to their prerequisite chain in one traversal.

## Frontend

Next.js 16 App Router, Tailwind v4 with a token-based design system, light and dark.

The API is reached same-origin through a rewrite (`/api/*` → the API container), so the
session cookie is first-party and the target is read at request time rather than
inlined at build time.

`src/proxy.ts` is an optimistic route guard only — it checks a cookie exists so an
unauthenticated visitor lands on sign-in rather than an empty dashboard. Every rule
that matters is enforced by the API against a verified token.

Design language: the attendance register. Ruled hairlines, ledger stock, a registrar's
indigo for structure, and a warm ramp for how much adult attention a line needs. The
ramp is **not** a traffic light — its low end is a pale neutral, never green, because
nothing here marks a student as good. Only two hues encode state; everything else is
ink and paper. Both were validated for colour-vision separation, chroma and contrast
against both surfaces.

## Frontend routes

```
/login                            portal picker and credentials

/teacher                          overview: bands, shared conditions, screening matrix
/teacher/caseload                 ranked list, review-threshold slider, burden readout
/teacher/students/[id]            the record screen (below)
/teacher/classes                  peer ties and shared conditions for one class
/teacher/queue                    academic support queue
/teacher/concepts                 prerequisite concept map

/student                          progress — no risk score
/student/lessons                  the learner's own concept map
/student/quiz                     personalised practice quiz
```

### The record screen, in action-first order

1. The figure, framed as a share of a cohort, with the register pattern that produced it
2. What's behind it — observational contrasts
3. What would help — true `do()` interventions; select several for the joint effect,
   shown beside the sum of the separate effects because the two differ
4. What to find out next — value of information
5. How it reaches the outcome — the causal routes, from the graph
6. The record — every field editable, "not recorded" always available
7. Not a lever — protected characteristics, with a button that invokes the engine and
   **displays the refusal** rather than describing it

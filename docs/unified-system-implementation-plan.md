# Unified System Implementation Plan

> **Status: implemented.** All six phases are complete and verified. This document is
> kept as the design record — the reasoning behind the merge, and the alternatives that
> were rejected. For how the system works now, read `docs/architecture.md`.
>
> Four things ended up differing from the plan below, each for a reason found during
> the build:
>
> 1. **Seeding needs a bootstrap exception.** `/internal/*` is administrator-only, but
>    the seed creates the first administrator — requiring one would deadlock. The
>    exception applies only while the `users` table is empty and closes itself.
> 2. **The API origin is baked at image build.** Next serialises `rewrites()` into the
>    routes manifest at build time, so `API_ORIGIN` is a Docker build arg, not only a
>    runtime variable.
> 3. **Demonstration accounts are read from the database**, not hardcoded on the login
>    screen: seeded names shift whenever the generator changes.
> 4. **Only two hues encode state.** The three-band ramp could not clear the
>    colour-vision and contrast gates with a near-neutral low end, so "nothing marked"
>    became a genuine non-colour — which is closer to the research tool's intent than
>    the original plan was.

Merging the **dropout-risk Bayesian network** (`Risk/`) into the **O/L learning intelligence platform**
(`api/` + `web/`) to produce one application: *AI-Based Student Wellbeing Monitoring System for Sri
Lankan Schools* (R26-IT-165, Component 3 — Monitoring, Visualization & AI Learning Support Dashboard).

---

## 1. Context

### Why this change

Two working prototypes exist side by side and neither is the system the proposal describes.

| | `api/` + `web/` | `Risk/` |
|---|---|---|
| What it does | O/L prerequisite-graph diagnosis, support queue, student quizzes | Discrete Bayesian network estimating next-term disengagement risk |
| Stack | FastAPI 0.115 + Postgres 16 + Neo4j 5.26 + Next.js 16.2.3 | Single `pgmpy` module + generated static HTML |
| Data | 240 students named `Student 001`…`Student 240` | 10,000 forward-sampled `SYNTH-000001` records |
| Users | None — no auth, identity is a `<select>` dropdown | None — a local HTML file |
| Risk model | Random Forest + SHAP over academic features | 25-node causal DAG, 42 edges, exact inference |

The proposal (Zoysa A.K.T.D., IT19064482) promises one dashboard that detects at-risk students early,
explains *why* transparently, and drives timely intervention — with separate audiences (class teachers,
counsellors, students, parents, zonal officers). Today a teacher cannot log in, cannot see a risk score,
and the two risk engines disagree about what "risk" even means.

### What this delivers

A single application where:

1. **The Bayesian network is the risk engine** (highest priority). It produces a calibrated distribution
   over `Low / Medium / High` for next-term disengagement, per student, with provenance attached.
2. **Neo4j is the explanation and connection layer** (second priority). The causal DAG, the curriculum
   graph, students, classes, schools, subjects, concepts and peer links live in one property graph, so
   "why was this student flagged?" is answered by graph traversal rather than a feature-importance bar.
3. **Two portals** — student and teacher/counsellor — behind real authentication.
4. **Realistic Sri Lankan data** in the database: three schools across the Urban/Rural/Estate sectors,
   authentic Sinhala, Tamil and Muslim names, medium of instruction, guardians, attendance, teachers.
5. **A modern UI**, rebuilt on a proper design-token system with light/dark support, EN/SI throughout,
   and one reusable graph renderer instead of the three hand-rolled ones in the codebase today.

### The SHAP substitution — and why it is an upgrade, not a compromise

The proposal specifies SHAP for explainability. We are replacing it with **exact Bayesian-network
queries over the causal graph**. This is worth stating plainly in the report because it is a stronger
claim, not a weaker one:

| | SHAP on a Random Forest | Graph/BN approach |
|---|---|---|
| Question answered | "Which features moved this prediction?" | "Which circumstances raise this risk, and which *actions* would lower it?" |
| Nature of the answer | Associational, approximate (sampled Shapley values) | Causal contrasts and exact `do()` interventions, computed by variable elimination |
| Auditability | Depends on a fitted forest that changes each retrain | Fixed DAG with a parameter fingerprint; every edge has a documented mechanism and evidence level |
| Actionability | A feature name | A named action, an owner, and the estimated effect in percentage points |
| Fairness guarantee | None structurally | `Neuro_Type` cannot reach the outcome except through changeable environment; `do()` on protected attributes is **refused in code** |

`Risk/` already implements four explanation estimands (`drivers`, `actionCandidates`, `worthAsking`,
`routes`) in JavaScript inside `Risk/ui/case.template.html`. We port them to Python and back `routes`
with Neo4j.

---

## 2. Target architecture

```
                       Next.js 16 (App Router)
        /login   /student/*  (learning only)   /teacher/*  (risk + learning)
                              │  same-origin  /api/*  (rewrite → FastAPI, httpOnly cookie)
                              ▼
                          FastAPI (one service)
   ┌────────────┬──────────────┬───────────────┬────────────┬──────────────┐
   │ auth       │ risk (BN)    │ graph (Neo4j) │ diagnosis  │ learn/quiz   │
   └────────────┴──────────────┴───────────────┴────────────┴──────────────┘
          │              │              │              │            │
          ▼              ▼              ▼              ▼            ▼
     ┌─────────────────────────────┐        ┌──────────────────────────────┐
     │ PostgreSQL                  │───────▶│ Neo4j                        │
     │ users, schools, classes,    │project │ School/Class/Teacher/Student │
     │ teachers, students,         │        │ Subject/Concept/RiskFactor   │
     │ risk_evidence, attendance,  │        │ REQUIRED_FOR, HAS_MASTERY,   │
     │ risk_assessments (audit),   │        │ HAS_EVIDENCE, INFLUENCES,    │
     │ support_actions, alerts,    │        │ FRIENDS_WITH, IN_CLASS       │
     │ concept_scores, quizzes     │        │                              │
     └─────────────────────────────┘        └──────────────────────────────┘
```

**One Python environment — verified.** `pgmpy==1.1.2` requires `numpy>=2.0, pandas>=1.5,
scikit-learn>=1.2, networkx>=3.0, scipy>=1.10` — all satisfied by the API's existing pins
(`numpy==2.2.5`, `pandas==2.2.3`, `scikit-learn==1.6.1`). A `pip install --dry-run` of the merged
requirement set resolves cleanly; only `pgmpy, networkx, opt_einsum, scikit-base, statsmodels` are
added. `Risk/requirements.txt`'s `pandas==3.0.5 / numpy==2.5.1` were that project's own choices, not
pgmpy constraints, and are dropped. **No second service, no separate venv, no microservice split.**

---

## 3. Phase plan

Ordered so the risk module lands first and each phase leaves the app runnable.

### Phase 0 — Repository reshape and dependency merge

Move the BN engine into the API package so there is exactly one copy of it, and keep the research
artefacts (which are the thesis evidence) together.

| From | To | Edits |
|---|---|---|
| `Risk/dropout_ews_bn.py` | `api/app/risk/dropout_ews_bn.py` | **none** — the module is self-contained |
| `Risk/test_dropout_ews_bn.py` | `api/tests/test_dropout_ews_bn.py` | 1 line: `import dropout_ews_bn as bn` → `from app.risk import dropout_ews_bn as bn` |
| `Risk/REPORT.md`, `risk_cal.md`, `ui/`, `outputs/` | `research/dropout-ews/` | 2 lines each in `ui/build_ui_data.py` and `ui/export_model.py`: point `sys.path` at `<repo>/api` and import `app.risk.dropout_ews_bn` |

`research/dropout-ews/ui/build_ui_data.py` cross-validates `REPORT.md`'s edge table against
`EDGE_EVIDENCE` in code and fails the build on drift — keeping `REPORT.md` next to `ui/` preserves that.

Also in this phase:
- `api/requirements.txt`: add `pgmpy==1.1.2`, `networkx==3.6.1`, `passlib[bcrypt]==1.7.4`,
  `pyjwt==2.10.1`; **remove `shap==0.47.2`** (see Phase 4).
- Replace the deprecated `@app.on_event("startup")` with a `lifespan` context that builds the BN once
  (`build_model(ModelVariant.AMENDED)`) into `app.state.risk_model` — the frozen `RiskModel` dataclass
  is thread-safe for reuse, as `REPORT.md` §4 specifies.
- Add `api/app/{core,repositories,routers,schemas,services}/__init__.py` and an `api/pyproject.toml`,
  so imports no longer depend on `PYTHONPATH` being set by hand.

**Gate:** `cd api && pytest` — the 133 BN tests plus the 5 existing suites must all pass.

---

### Phase 1 — Data model: realistic Sri Lankan schools, people, and risk evidence

#### New / changed Postgres tables

```
schools            id, name, name_si, name_ta, census_no, district, province,
                   sector('Urban'|'Rural'|'Estate'), school_type, medium_primary
classes            id, school_id→schools, grade(9|10|11), section('A'..'D'),
                   medium('Sinhala'|'Tamil'|'English'), class_teacher_id→teachers
teachers           id, school_id, full_name, full_name_si, role_title, subjects_json, email
users              id, username, password_hash, role('student'|'teacher'|'counsellor'|'admin'),
                   display_name, display_name_si, locale, student_id?, teacher_id?, is_active
students   (alter) + school_id, class_id, admission_no, full_name_si, gender, date_of_birth,
                   grade, medium, guardian_name, guardian_relationship, guardian_contact,
                   distance_to_school_km        (existing id/full_name/cohort retained)
terms              id, year, term_number(1..3), starts_on, ends_on
attendance_terms   student_id, term_id, days_present, days_total, max_consecutive_absences
student_risk_evidence  id, student_id, term_id, variable, state,
                   source('seed'|'teacher'|'register'|'derived'|'self'),
                   recorded_by→users, recorded_at, note
risk_assessments   id, student_id, term_id, model_variant, model_fingerprint,
                   evidence_json, posterior_json, p_high, band, interpretation,
                   circumstance_gap, computed_at, computed_by→users
support_actions    id, student_id, factor, action, owner_role, detail, status
                   ('offered'|'accepted'|'in_progress'|'closed'|'declined'),
                   opened_by, opened_at, closed_at, outcome_note
alerts             id, student_id, tier(1|2|3), audience_role, title, body, body_si,
                   status('new'|'ack'|'closed'), created_at, acknowledged_by
```

`student_risk_evidence` deliberately mirrors the BN's own shape — one row per
`(student, term, variable, state)` — so "not recorded" is the absence of a row, exactly as
`validate_evidence` expects, and every field carries its own provenance for the audit requirement in
`REPORT.md` §11.2.

#### Realistic seed data

Three schools chosen so the BN's `Sector` variable is genuinely exercised (and so the estate-sector
under-representation critique, C9, can actually be demonstrated):

| School | District / Province | Sector | Medium |
|---|---|---|---|
| Ruwanwella Central College | Colombo / Western | Urban | Sinhala + English |
| Mahaweli Maha Vidyalaya, Girandurukotte | Badulla / Uva | Rural | Sinhala |
| Bogawantalawa Tamil Maha Vidyalayam | Nuwara Eliya / Central | Estate | Tamil |

- ~240 students across grades 9–11 (grade 9 = `Junior_Secondary`, grades 10–11 = `OLevel_ALevel`,
  giving `Grade_Band` real variation), 4 sections per grade, ~20 per class.
- Authentic naming per school: Sinhala (`Kavindu Rathnayake`, `Sanduni Wickramasinghe`,
  `Thilina Bandara`), Tamil (`Thevarajah Mathangi`, `Sivakumar Arulnesan`), Muslim
  (`Mohamed Rizwan`, `Fathima Nusrath`) — with `full_name_si` populated.
- ~28 teachers with subject assignments and class-teacher roles, plus one counsellor and one principal
  per school.
- Guardian names/relationships/occupations, distance to school, and per-term attendance that is
  *consistent with* the seeded BN evidence (a student seeded `Transport_Burden=High` and
  `Access_Barrier=High` gets a matching attendance record — the register must not contradict the
  evidence, or the screening story falls apart).
- Wellbeing evidence seeded per student for all 24 non-target BN variables, with a realistic fraction
  deliberately left **unrecorded** so the "what to find out next" panel has something to say.

Everything remains clearly synthetic: a persistent demonstration-data banner stays in the UI and the
`SYNTHETIC_BANNER` / `PRIOR_PROVENANCE` strings from the engine are carried into every risk response.

New endpoints: `POST /internal/seed/school-data`, `POST /internal/generate/evidence`. Existing
`POST /internal/generate/synthetic-data` is rewritten to consume the new roster instead of inventing
`Student NNN`. Because `create_all` cannot add columns, `scripts/reset-and-seed.ps1` gains a
`-Recreate` switch that drops and rebuilds the schema; Alembic is noted as a follow-up, not adopted
now (all data is synthetic).

---

### Phase 2 — The risk service (highest priority)

`api/app/services/dropout_risk.py` wraps the engine; `api/app/routers/risk.py` exposes it.

#### Explanation estimands ported from `research/dropout-ews/ui/case.template.html`

All four are **exact BN queries**, not approximations:

| Function | Estimand | Purpose |
|---|---|---|
| `drivers(evidence)` | `P(High \| bg, X=concern) − P(High \| bg, X=reference)` per recorded circumstance | "What's behind it" — ranked, labelled **association, not effect of acting** |
| `action_candidates(evidence)` | `P(High \| do(levers ∪ {X:=target}), bg) − P(High \| do(levers), bg)` | "What would help" — real `do()`, sorted most-negative first |
| `worth_asking(evidence)` | Swing over unrecorded variables (causal contrast where modifiable, observational otherwise) | "What to find out next", each row flagged `causal: bool` |
| `circumstance_gap(evidence)` | `P(High \| do(levers), bg)` with the register left free, minus the register score | Surfaces students the attendance register has *not yet* flagged |

`routes(factor)` — enumerating how a factor reaches the outcome — moves to **Neo4j** (Phase 3).

Reuse directly, do not reimplement: `build_model`, `infer_dropout_risk`, `estimate_intervention_effect`,
`validate_evidence`, `compare_observational_and_interventional`, `estimate_screening_burden`,
`MODIFIABLE_NODES`, `PROTECTED_OR_IMMUTABLE_NODES`, `OBSERVABLE_AT_SCREENING`.

#### Endpoints

```
GET   /api/risk/model                            DAG + labels + variant + fingerprint
GET   /api/risk/screening-matrix                 the 12-cell register table
GET   /api/risk/caseload?school=&class=&threshold=   ranked students: p_high, band, gap, basis
GET   /api/risk/students/{id}                    posterior + basis + drivers + actions + worth_asking
POST  /api/risk/students/{id}/what-if            {evidence?, intervention?} → posterior
PUT   /api/risk/students/{id}/evidence           teacher wellbeing check-in
GET   /api/risk/students/{id}/audit              past risk_assessments
GET   /api/risk/factors/{factor}/cohort          students sharing this concern (school-level pattern)
```

#### Performance

`Next_Term_Dropout_Risk`'s only parents are `Current_Attendance`, `Grade_Band`, `School_Engagement` —
2 × 3 × 2 = **12 cells**. The caseload list therefore needs no per-student inference for the register
score: precompute the 12-cell table at startup. Only `circumstance_gap` needs a `do()` query per
student; memoize on `(variant, frozenset(evidence), frozenset(intervention))`. The full record view
runs ~40 variable-elimination queries on a 25-node network — milliseconds, and cached.

#### Ethical constraints that must survive the merge (enforced, tested)

1. `NonModifiableInterventionError` → **HTTP 403**, not 422. `EvidenceError` → 422.
   Asking what would change if a child were not autistic is a *forbidden* request, not a malformed one.
2. `provenance`, `caveat`, `interpretation`, `model_fingerprint`, `model_variant`, `computed_at` are
   **required fields on the Pydantic response models** — the caveat travels with the number.
3. `observational_conditional` and `interventional_do` are never conflated in payload or UI.
4. Every flag renders as an **offer of support** with a named owner (`support_actions`), never a
   sanction. No streaming, exclusion, permanent record note, or automatic authority referral.
5. **Students never see their own dropout-risk score.** The `/student/*` portal shows learning progress
   only. Enforced in the API by role, not just hidden in the UI.
6. `School_Distress` / `Psychological_Attendance_Barrier` are labelled modelling constructs, never
   clinical findings.
7. Raw identifiers (`Child_Labour_Household_Duties=High`) never reach a screen — the authored
   plain-language `label` / `stateLabels` / `action` copy from `research/dropout-ews/ui/export_model.py`
   is loaded as seed data and is a build-time contract.
8. Every inference writes a `risk_assessments` row: who queried, for whom, on what evidence, against
   which fingerprint.

---

### Phase 3 — Neo4j as the connection and explanation layer

Extend the existing graph; `Subject`, `Concept`, `REQUIRED_FOR`, `IN_SUBJECT` are unchanged.

```cypher
(:School {id,name,district,province,sector})
(:Class {id,grade,section,medium})-[:AT_SCHOOL]->(:School)
(:Teacher {id,name})-[:TEACHES_CLASS]->(:Class)
(:Teacher)-[:TEACHES_SUBJECT]->(:Subject)
(:Student {id,name,name_si,grade,medium})-[:IN_CLASS]->(:Class)
(:Student)-[:STUDIES]->(:Subject)
(:Student)-[:HAS_MASTERY {score,band,updated_at}]->(:Concept)
(:Student)-[:FRIENDS_WITH]->(:Student)

(:RiskFactor {id,label,label_si,group,modifiable,protected,states,state_labels})
(:RiskFactor)-[:INFLUENCES {evidence,mechanism,confounders,concern,amendment}]->(:RiskFactor)
(:Student)-[:HAS_EVIDENCE {state,state_label,concern,source,recorded_at}]->(:RiskFactor)
(:Student)-[:AT_RISK {band,p_high,gap,fingerprint,computed_at}]->(:RiskOutcome)
```

The 25 nodes and 42 edges come from `NODE_STATES` / `BASELINE_EDGES` + `AMENDMENT_EDGES`, and the edge
properties (`mechanism`, `confounders`, `concern`, `evidence` level SL/INT/EXP) come from
`research/dropout-ews/ui/ui_data.json` — which already carries the full edge-justification table.

#### What the graph buys us — five queries that are the "graph-based approach"

```cypher
-- 1. Why this flag: how does a factor reach the outcome?
MATCH p = (f:RiskFactor {id:$factor})-[:INFLUENCES*1..6]->(:RiskFactor {id:'Next_Term_Dropout_Risk'})
RETURN p ORDER BY length(p) ASC

-- 2. Shared-factor pattern: a school problem, not 23 student problems
MATCH (s:Student)-[e:HAS_EVIDENCE {concern:true}]->(f:RiskFactor)
WHERE (s)-[:IN_CLASS]->(:Class)-[:AT_SCHOOL]->(:School {id:$school})
RETURN f.label, count(s) AS students ORDER BY students DESC

-- 3. Academic root cause joined to the learner
MATCH (s:Student {id:$id})-[m:HAS_MASTERY]->(c:Concept)
WHERE m.band = 'weak'
MATCH path = (root:Concept)-[:REQUIRED_FOR*0..]->(c)
WHERE NOT EXISTS { MATCH (:Concept)-[:REQUIRED_FOR]->(root) }
RETURN path ORDER BY length(path) ASC

-- 4. Peer isolation (the proposal's "peer interaction patterns")
MATCH (s:Student)-[:IN_CLASS]->(:Class {id:$class})
OPTIONAL MATCH (s)-[:FRIENDS_WITH]-(peer:Student)
RETURN s.id, s.name, count(peer) AS ties ORDER BY ties ASC

-- 5. Ego network for the record screen
MATCH (s:Student {id:$id})
OPTIONAL MATCH (s)-[r]->(n) WHERE n:Concept OR n:RiskFactor OR n:Subject OR n:Class
RETURN s, r, n
```

Query 2 is the ethically important one: `REPORT.md` §11.1 argues most flagged students would not have
left anyway, so the honest output of a screen is often *"fix the toilets in this school"*, not
*"watch these nine children"*. The graph makes that visible; a per-student SHAP bar chart cannot.

New endpoints: `GET /api/graph/students/{id}/neighbourhood`, `GET /api/graph/peers/{class_id}`,
`GET /api/risk/students/{id}/paths/{factor}`, `POST /internal/import/risk-model`,
`POST /internal/project/graph`.

`GraphRepository` is refactored from per-request instantiation to a single driver held on
`app.state` and injected via `Depends`, and `import_curriculum` is generalised so the risk DAG and the
student projection reuse the same session handling.

---

### Phase 4 — Authentication and role separation

- `users` table; `passlib[bcrypt]` password hashing; `pyjwt` token in an **httpOnly, SameSite=Lax**
  cookie. `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`.
- FastAPI dependencies `current_user()` and `require_role("teacher", "counsellor")`; students are
  scoped to their own `student_id` **in the query layer**, so `/api/learn/student/{other}` returns 403.
- `/internal/*` moves behind `require_role("admin")`.
- **Next.js `rewrites`: `/api/:path*` → `http://api:8000/api/:path*`.** This makes the cookie
  first-party, removes CORS from the browser path, and fixes the existing bug where
  `NEXT_PUBLIC_API_BASE_URL` is baked into the Docker image at build time and cannot be overridden at
  runtime.
- `web/src/proxy.ts` (Next 16 middleware) guards `/teacher/*` and `/student/*` and redirects to
  `/login` with the intended path preserved.
- Demo credentials are printed by the seed script and shown on the login screen — this is a thesis
  demonstrator, and reviewers must be able to get in.

**Retired in this phase:** `api/app/services/student_support_ml.py` (a dead 3-line shim),
`api/app/services/student_support_model.py` (Random Forest + SHAP), `POST /internal/train/support-model`,
and the `shap` dependency. `student_support.py`'s deterministic additive scorer **stays** — it measures
*academic support need* (`high_support / watch / stable`), which is a genuinely different quantity from
*disengagement risk* (`Low / Medium / High`), and the UI will keep them visually and verbally distinct.

---

### Phase 5 — UI rebuild

#### Information architecture

```
/login                              portal picker + credentials

/teacher                            overview: school/class risk distribution, shared-factor patterns,
                                    alerts, today's caseload count
/teacher/caseload                   ranked list, review-threshold slider + live burden bar,
                                    sort by Risk / Gap / Register, search
/teacher/students/[id]              THE RECORD SCREEN (below)
/teacher/students/[id]/check-in     wellbeing check-in form (writes student_risk_evidence)
/teacher/class/[id]                 class view: peer graph, shared factors, mastery heatmap
/teacher/concepts                   prerequisite concept map (one renderer, reused)
/teacher/queue                      academic support queue (existing, restyled)
/teacher/alerts                     three-tier alert inbox

/student                            my progress — NO risk score
/student/subjects/[id]              lesson cards for weak concepts
/student/quiz                       personalized MCQ quiz (existing flow)
/student/wellbeing                  self check-in (source='self')
```

#### The record screen — action-first order, ported from `caseload.html`

1. **Header** — `P(High)` framed as *"% of students with this register pattern"* (frequency framing,
   never a personal prediction), band tag, "Circumstances ahead" tag when `gap ≥ 0.15`, a three-segment
   stacked posterior bar, and a `basis` sentence explaining that three register fields fully determine
   the number.
2. **What's behind it** — `drivers`, ranked bars, labelled as association.
3. **What would help** — `action_candidates` with owner and detail; multi-select builds a plan whose
   **joint** `do()` effect is computed and compared against the sum of the parts.
4. **What to find out next** — `worth_asking`.
5. **How it reaches the outcome** — the Neo4j causal-path graph for the selected factor.
6. **Learning picture** — the existing subject concept map + academic support panel.
7. **Not a lever** — `Neuro_Type` and other protected attributes, with a live button that invokes the
   engine and **displays the refusal**. This is a feature, not an error state.
8. **Offers of support** — open/track `support_actions`.

#### Design system

Replace the current 10-token `globals.css` with a full Tailwind v4 `@theme` set (color, radius, shadow,
spacing, type scale) plus `@custom-variant dark`. Adopt the **register/ledger design language** already
developed and justified in `research/dropout-ews/ui/case.template.html`:

- Ledger-paper ground, registrar's indigo for structure, and an ochre → rust attention ramp that is
  **deliberately not a traffic light** — its low end is a pale neutral, never green, because nothing
  here marks a student as good.
- `font-variant-numeric: tabular-nums` on every figure.
- The ~40 hardcoded hex/rgba values and 8 arbitrary radii scattered across the current components are
  promoted into tokens as part of this pass.

Fixes carried in the same pass: add **Noto Sans Sinhala** (Sinhala currently falls back to a system
font), replace `outline-none` with visible `focus-visible` rings (there is currently not one `focus:`
style in the codebase), add `aria-live` to the status messages, use real `<table>` markup for the
`/teacher/caseload` and `/teacher/queue` tables, and add a mobile drawer for the six-item nav.

#### Frontend consolidation

| Problem today | Fix |
|---|---|
| `API_BASE_URL` re-declared in 6 files, no wrapper, blind `as` casts | `web/src/lib/api.ts` — one typed client with `AbortController`, error normalisation, 401 → `/login` |
| Response types duplicated across components (`SubjectNode` ×6, and they disagree) | `web/src/lib/types.ts` — one set, generated notes kept in sync with the Pydantic schemas |
| Three incompatible graph renderers (`subject-support-canvas`, `concept-explorer`, none reusable) | One `<GraphCanvas>` on `@xyflow/react` + `@dagrejs/dagre`, with pan/zoom/keyboard, used for the concept map, the causal DAG and the peer graph |
| `displayName()` copy-pasted 7 times | `web/src/lib/i18n` — `useLocale()`, `en.ts` / `si.ts` dictionaries, `ta.ts` stub so Tamil is a data-only addition later |
| Every page is a client component with a request waterfall | Server Components fetch initial data; client components handle interaction only |

**New dependencies:** `@xyflow/react`, `@dagrejs/dagre`, `recharts`, `clsx`, `tailwind-merge`,
`lucide-react`. Chart work follows the `dataviz` skill (loaded before the first chart is written).

---

### Phase 6 — Alerts, reports, documentation

- **Tier 1** (Moderate) — in-app teacher notification, bell in the header, `alerts` table.
- **Tier 2** (consecutive absences) — generate the parent SMS **text** in EN/SI and display it for a
  human to send. We do not wire an SMS gateway: auto-messaging a family about a child is precisely what
  the governance section forbids without review.
- **Tier 3** (High) — a printable counsellor case summary (`/teacher/students/[id]/report`,
  browser print-to-PDF) carrying posterior, evidence, drivers, actions, provenance and caveat.
- Rewrite `docs/architecture.md`, `docs/ai-context.md`, `docs/setup-and-configuration.md`,
  `docs/curriculum-and-seeding.md`; replace `docs/student-help-risk.md` with `docs/risk-model.md`;
  update `AGENTS.md` and `README.md`.

---

## 4. Critical files

**Reused as-is (do not reimplement):**
- `api/app/risk/dropout_ews_bn.py` — `build_model`, `infer_dropout_risk`,
  `estimate_intervention_effect`, `validate_evidence`, `estimate_screening_burden`, `MODIFIABLE_NODES`
- `api/app/services/{diagnosis,subject_diagnosis,scoring,curriculum_service,learning}.py` — the
  academic engines are sound and stay
- `api/app/repositories/graph_repository.py` — Cypher patterns extended, not replaced
- `research/dropout-ews/ui/export_model.py` — the authored label/action copy is lifted into seed data
- `research/dropout-ews/ui/case.template.html` — source of the four estimands and the design language

**Rewritten:**
- `api/app/services/synthetic_data.py`, `api/app/db/models.py`, `api/app/main.py`
- `web/src/app/globals.css`, `web/src/app/layout.tsx`, all 6 routes, all 7 components

**New:** `api/app/{routers,services,schemas}/risk.py` · `api/app/routers/auth.py` ·
`api/app/services/{risk_explain,graph_projection,seed_school_data}.py` ·
`api/app/core/security.py` · `web/src/lib/{api,types,i18n}` · `web/src/components/graph-canvas.tsx` ·
`data/seeds/{schools,names,risk_factor_copy}.json`

**Deleted:** `api/app/services/student_support_ml.py` · `api/app/services/student_support_model.py` ·
`get.py` (a stray HuggingFace dataset snippet, unrelated to the app)

---

## 5. Verification

Run at each phase gate, not only at the end.

```powershell
# Backend — 133 BN tests + 5 existing suites + new auth/risk/seed tests
cd api; pytest

# Frontend
cd web; npm run lint; npm run build

# Full stack
docker compose down; docker compose up --build -d
```

**Seed and smoke:**

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/import/curriculum
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/import/risk-model
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/seed/school-data
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/generate/synthetic-data -ContentType 'application/json' -Body '{}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/project/graph
```

**Acceptance checks:**

| # | Check | Expected |
|---|---|---|
| 1 | `POST /api/auth/login` as a teacher, then `GET /api/risk/caseload` | 200, students ranked, no `Student NNN` names anywhere |
| 2 | Same cookie, `GET /api/learn/student/<other-student>/...` as a **student** | 403 |
| 3 | `POST /api/risk/students/{id}/what-if` with `intervention={"Neuro_Type":"Typical"}` | **403** with the guardrail message |
| 4 | `POST` the same with `intervention={"WASH_Quality":"Adequate"}` | 200, `interpretation: "interventional_do"`, `p_high` lower |
| 5 | Any risk response | contains `provenance`, `caveat`, `model_fingerprint`, `model_variant` |
| 6 | Neo4j: `MATCH (:RiskFactor)-[:INFLUENCES]->(:RiskFactor) RETURN count(*)` | 42 (amended variant) |
| 7 | Neo4j: `MATCH (n:Student)-[:HAS_EVIDENCE]->() RETURN count(DISTINCT n)` | equals the student count |
| 8 | `GET /api/risk/factors/WASH_Quality/cohort` | a school-level cluster, not one student |
| 9 | Student portal, any page | **no dropout-risk score visible** |
| 10 | `node research/dropout-ews/ui/verify_infer.cjs` | still exits 0 (BN parameters unchanged) |
| 11 | Toggle EN/සිංහල | labels, risk narratives and actions all switch |
| 12 | Lighthouse on `/teacher/caseload`, and tab through it | visible focus on every control; a11y ≥ 90 |

**Browser walkthrough** (Chrome MCP, recorded as a GIF for the report): log in as a class teacher →
caseload → open a flagged student → read "what's behind it" → select two actions and see the joint
`do()` effect → open the causal path graph → record a wellbeing check-in → watch the risk recompute →
open an offer of support → log out → log in as that student → confirm the learning portal shows
progress and quizzes and **no risk score**.

---

## 6. Decisions taken, and what I would flag

1. **One FastAPI service, one Python env** — verified by dependency resolution, not assumed. A separate
   risk microservice would add deployment surface for no benefit at this scale.
2. **The BN scores; Neo4j explains and connects.** The BN is already tested (133 tests), calibrated in
   structure, and ethically constrained in code. Re-deriving a risk score by graph propagation would
   discard all of that.
3. **SHAP and the Random Forest are removed, not kept alongside.** Two competing explanations of the
   same flag would undermine both. The report should present the graph/causal approach as the method,
   with the RF path documented as a superseded iteration.
4. **Students do not see their own risk score.** This is my strongest recommendation and it is baked
   into the API, not just the UI.
5. **No SMS gateway, no server-side PDF.** Tier 2 generates text for a human to send; Tier 3 is a
   printable page. Both are honest about what a prototype should automate.

**Flagged for your judgement:**

- The seeded Sri Lankan schools, students, teachers and guardians are **realistic but fictional**. They
  must stay labelled as demonstration data in the UI and in the report — the BN's own metadata forbids
  presenting model-generated records as empirical evidence, and the same standard should apply to the
  roster.
- `Grade_Band` only varies because I am including grade 9 alongside grades 10–11. If you would rather
  keep the cohort strictly O/L, that variable becomes constant and one of the outcome's three parents
  stops doing any work — worth a sentence in the limitations section either way.
- The proposal's trilingual objective is met in EN/SI only. The i18n layer will accept `ta.ts` without
  code changes, but I will not generate Tamil curriculum and risk-narrative content I cannot verify.

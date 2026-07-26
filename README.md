# AI-Based Student Wellbeing Monitoring System for Sri Lankan Schools

R26-IT-165 · Component 3 — Monitoring, Visualization & AI Learning Support Dashboard

An early-support screen and learning-intelligence platform for Sri Lankan schools. It
estimates next-term disengagement risk with a causal Bayesian network, explains every
flag through the causal graph rather than a feature-importance chart, and gives
learners a separate portal for practice and progress.

> **Demonstration system.** Schools, students, teachers and guardians are realistic but
> fictional. Risk figures come from illustrative expert-elicited priors, not validated
> Sri Lankan prevalence estimates. This is decision support for human review — not a
> diagnostic, disciplinary or automated decision-making system.

## Quick start

```powershell
Copy-Item .env.example .env
docker compose up --build -d
.\scripts\reset-and-seed.ps1
```

Then open http://localhost:3000. The seed prints demonstration accounts; all use the
password `wellbeing2026`.

## What it does

**For teachers and counsellors** — a caseload ranked by the share of students with the
same attendance and engagement record who the model expects to leave, and for each
learner a record screen in action-first order:

- **What's behind it** — which recorded circumstances raise the figure, and by how much
- **What would help** — real `do()` interventions with a named owner and an estimated
  effect in percentage points; select several and see their joint effect
- **What to find out next** — the unrecorded circumstances whose answers would move the
  figure most
- **How it reaches the outcome** — the causal routes, read from the graph
- **Not a lever** — protected characteristics, with a button that asks the model and
  displays its refusal

Plus shared conditions across a school, peer-connection counts within a class, the
prerequisite concept map, and the academic support queue.

**For learners** — progress, topics worth practising, a concept map and personalised
quizzes. No risk score, no band, no flag: a flag must cost the student nothing if it
was wrong, and that is enforced by the API rather than by omitting it from the screen.

## Why not SHAP

The proposal specified SHAP. This uses exact Bayesian-network queries instead, which is
a stronger claim rather than a weaker one:

| | SHAP on a forest | This |
|---|---|---|
| Answers | which features moved a prediction | which circumstances raise risk, and which **actions** lower it |
| Nature | associational, sampled approximation | causal contrasts and exact `do()` interventions |
| Stability | changes with every retrain | fixed DAG with a parameter fingerprint |
| Actionability | a feature name | a named action, an owner, and an effect size |
| Fairness | none structurally | `Neuro_Type` cannot reach the outcome except through changeable environment; `do()` on protected attributes is refused in code |

## Structure

```
api/          FastAPI: auth, risk, graph, diagnosis, learning
  app/risk/   the Bayesian network, vendored unchanged from the research
web/          Next.js 16 — /login, /teacher/*, /student/*
data/         curriculum, quiz banks, school roster, authored risk copy
research/
  dropout-ews/  the research record: REPORT.md, the generated study UI, outputs
docs/         architecture, setup, curriculum and seeding, AI context
scripts/      reset-and-seed, risk copy builder
```

## Documentation

- `docs/architecture.md` — components, the risk engine, the four estimands, the graph
- `docs/setup-and-configuration.md` — running, environment, reseeding
- `docs/curriculum-and-seeding.md` — curriculum format and the seed pipeline
- `docs/ai-context.md` — orientation and the rules that are not negotiable
- `research/dropout-ews/REPORT.md` — the model's critique, edge justification, CPD
  rationale, sensitivity analysis, ethics and sources

## Stack

Next.js 16 · React 19 · Tailwind v4 · FastAPI · PostgreSQL 16 · Neo4j 5 · pgmpy 1.1.2

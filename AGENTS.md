# Agent Instructions

Read `docs/ai-context.md` before making project changes, and
`docs/unified-system-implementation-plan.md` for the in-progress merge.

This is the Sri Lankan school wellbeing monitoring system (R26-IT-165). It has two halves:

- **Disengagement risk** — a discrete Bayesian network in `api/app/risk/dropout_ews_bn.py`.
  Read `research/dropout-ews/README.md` before touching it. It carries hard ethical constraints
  that are enforced in code and covered by tests; do not weaken them.
- **Academic learning support** — prerequisite-graph diagnosis, support queues, student quizzes.

Keep the UI practical and audience-appropriate. Do not add internal design-process copy to
visible screens. Never show a student their own dropout-risk score.

## Environment

Use the project virtualenv, not the base Anaconda environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r api\requirements.txt -r api\requirements-dev.txt
```

## Checks

Backend (`api/pyproject.toml` sets `pythonpath`, so `PYTHONPATH` no longer needs setting):

```powershell
cd api
..\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd web
npm run lint
npm run build
```

## When data changes

When curriculum or seed data changes, update:

- `data/curriculum/ol_subject_curriculum.json`
- `data/seeds/generator_config.json`
- `docs/curriculum-and-seeding.md` if behavior or shape changes
- `docs/ai-context.md` if workflow assumptions change

When the risk model changes, the research record must stay in step — `research/dropout-ews/ui/build_ui_data.py`
cross-validates `REPORT.md`'s edge table against `EDGE_EVIDENCE` in code and fails the build on drift:

```powershell
cd research\dropout-ews
..\..\.venv\Scripts\python.exe ui\build_ui_data.py ui\ui_data.json
..\..\.venv\Scripts\python.exe ui\export_model.py ui\case_data.json
node ui\verify_infer.cjs ui\case_data.json
```

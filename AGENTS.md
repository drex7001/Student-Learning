# Agent Instructions

Read `docs/ai-context.md` before making project changes.

This is a Sri Lankan O/L teacher support prototype. Keep the UI practical and teacher-facing. Do not add internal design-process copy to visible screens.

Before finishing code changes, run the relevant checks:

```powershell
cd api
$env:PYTHONPATH='.'
pytest
```

```powershell
cd web
npm run lint
npm run build
```

When curriculum or synthetic data changes, update:

- `data/curriculum/ol_subject_curriculum.json`
- `data/seeds/generator_config.json`
- `docs/curriculum-and-seeding.md` if behavior or shape changes
- `docs/ai-context.md` if workflow assumptions change

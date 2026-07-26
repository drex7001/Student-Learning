# School-disengagement early-support screen — research prototype

A discrete Bayesian network that estimates a distribution over next-term disengagement
risk for a student, in the Sri Lankan school context, from household, school-environment
and prior-term evidence.

> **This is a research prototype built on assumed parameters.** All probabilities are
> *illustrative expert-elicited priors for software testing; not validated Sri Lankan
> prevalence estimates.* No output may be shown to, or used about, a real student. It is
> not a diagnostic, disciplinary, or automated decision-making system.

## Files

| File | What it is |
|---|---|
| `risk_cal.md` | The original research brief |
| `REPORT.md` | **Start here.** Critical review, edge-justification table, DAG, CPD rationale, results, ethics, sources |
| `dropout_ews_bn.py` | The implementation (single module) |
| `test_dropout_ews_bn.py` | 133 tests: arithmetic, CPD-cell alignment, and the elicited semantics |
| `outputs/analysis_results.json` | Every number in the report, machine-readable |
| `outputs/synthetic_students_SYNTHETIC.csv` | 10,000 synthetic records — **cannot validate the model** |
| `outputs/synthetic_students_SYNTHETIC.metadata.json` | Provenance, permitted and prohibited uses |

## Setup and run

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # Linux/macOS

.venv/Scripts/python.exe dropout_ews_bn.py --out-dir outputs
.venv/Scripts/python.exe -m pytest -q test_dropout_ews_bn.py
```

Options: `--variant {baseline,amended}`, `--n-records N`, `--seed N`, `--quiet`.

`baseline` is the structure exactly as the brief specifies it. `amended` adds the six
critique-driven amendments (REPORT.md §1, §3) and is the variant to develop further.

## Three things to know before reading the numbers

1. **The outcome node is not an observable event**, so nothing here can currently be
   calibrated or falsified. REPORT.md §1 C1 proposes the fix, and it is the prerequisite
   for everything else.
2. **The baseline structure transmits only 1.1% of the accommodation signal to the
   outcome**, so Scenario A — the ethically important comparison — is practically
   invisible. The amended variant raises this to 7.9%. REPORT.md §1 C5.
3. **`pgmpy.CausalInference.query` is not safe for conditional interventional queries** in
   version 1.1.2. This module computes `do()` on the mutilated graph instead. REPORT.md
   §8.3.

## Ethical constraints enforced in code

- `Neuro_Type` has no direct edge to the outcome; every path from it runs through an
  environmental mechanism a school can change (tested).
- Interventions are restricted to an **allowlist** of modifiable factors. `do()` on
  `Neuro_Type`, `Sector`, `Grade_Band` or `Parent_Education` raises
  `NonModifiableInterventionError` (HTTP 403), because "risk if this child were not
  autistic" is a forbidden question, not a malformed one.
- No CPD entry may be exactly 0 or 1 — no elicited prior about a child's circumstances
  earns the claim "impossible".
- Every inference result carries a parameter fingerprint, the provenance banner, and a
  caveat string, so the warning cannot be detached from the number downstream.

## Must not be used to

Deny or restrict education · discipline, stream or exclude a student · rank schools or
teachers · label a child in any permanent record · report families to police, labour or
child-protection authorities automatically. Because most flagged students will not have
left school anyway (REPORT.md §11.1), every output must lead to an **offer** of support
that costs the student nothing if the flag was wrong.

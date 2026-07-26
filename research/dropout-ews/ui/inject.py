"""Slim the generated UI data and inject it into the page template.

Keeps the discipline from build_ui_data.py: the page's numbers are never typed by hand,
they are substituted into a placeholder from the verified payload.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "ui_data.json").read_text(encoding="utf-8"))

KEEP_SCENARIO = ("label", "posterior", "evidence", "n_evidence", "note", "group",
                 "highest_state", "highest_probability", "interpretation")
KEEP_PACKAGE = ("label", "posterior", "interpretation", "method", "intervention",
                "conditioning_evidence")
KEEP_OBS_INT = ("variable", "state", "conditioning_evidence", "observational",
                "interventional", "max_abs_difference", "identical_in_this_dag",
                "parents_of_variable", "explanation")
KEEP_SENS = ("target", "perturbed_parameter", "question", "relative_delta",
             "ranking_preserved", "p_high_shift_by_scenario", "max_abs_shift",
             "most_affected_scenario")
KEEP_PATH = ("pathway", "steps", "shift_at_first_mediator", "shift_at_outcome",
             "transmission_to_outcome", "monotone_decay", "parallel_pathway_signals",
             "n_directed_paths_first_to_last", "scenario_labels")


def pick(obj: dict, keys) -> dict:
    return {k: obj[k] for k in keys if k in obj}


def scenarios(block: dict) -> dict:
    return {
        "results": [pick(r, KEEP_SCENARIO) for r in block["results"]],
        "contrasts": block["contrasts"],
        "ranking": block["ranking_by_p_high_descending"],
        "fingerprint": block["model_fingerprint"],
    }


slim = {
    "meta": data["meta"],
    "nodes": data["nodes"],
    "edges": data["edges"],
    "evidence": {
        k: {"n_edges": v["n_edges"], "counts": v["counts"],
            "expertShare": v["expert_hypothesis_share"]}
        for k, v in data["evidence"].items()
    },
    "scenarios": {k: scenarios(v) for k, v in data["scenarios"].items()},
    "pathways": {k: pick(v, KEEP_PATH) for k, v in data["pathways"].items()},
    "obsInt": {
        "baseline": [pick(r, KEEP_OBS_INT) for r in
                     data["interventions"]["observational_vs_interventional"]],
        "amended": [pick(r, KEEP_OBS_INT) for r in data["amendedInterventions"]],
    },
    "packages": {
        "profile": data["interventions"]["modifiable_intervention_packages"]["student_profile"],
        "results": [pick(r, KEEP_PACKAGE) for r in
                    data["interventions"]["modifiable_intervention_packages"]["results"]],
    },
    "guardrail": data["interventions"]["immutable_intervention_guardrail"],
    "libraryCaveat": data["interventions"]["library_caveat"],
    "sensitivity": {
        "records": [pick(r, KEEP_SENS) for r in data["sensitivity"]["records"]],
        "baselineRanking": data["sensitivity"]["baseline_ranking"],
        "baselinePHigh": data["sensitivity"]["baseline_p_high"],
        "nPerturbations": data["sensitivity"]["n_perturbations"],
        "nRankChanges": data["sensitivity"]["n_rank_changes"],
        "largestShift": data["sensitivity"]["largest_max_abs_shift"],
        "limitations": data["sensitivity"]["limitations"],
    },
    "screening": data["screening"],
    "structure": data["structure"],
    "addedEdges": data["addedEdges"],
}

payload = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
assert "</script" not in payload, "payload would break out of the script tag"

template = (HERE / "page.template.html").read_text(encoding="utf-8")
token = "/*__DATA__*/null"
assert template.count(token) == 1, f"expected exactly one {token} placeholder"

out = Path(sys.argv[1])
out.write_text(template.replace(token, payload), encoding="utf-8")

print(f"payload {len(payload) / 1024:.1f} KB -> {out.name} ({out.stat().st_size / 1024:.1f} KB)")
print(f"nodes {len(slim['nodes'])}  edges {len(slim['edges'])}  "
      f"scenarios {len(slim['scenarios']['baseline']['results'])}  "
      f"sens {len(slim['sensitivity']['records'])}  "
      f"thresholds {len(slim['screening']['thresholds'])}")

"""Generate the UI's data file from the module and REPORT.md.

Nothing here is transcribed by hand: node/edge structure and evidence levels come from
dropout_ews_bn, the per-edge narrative columns are parsed out of REPORT.md section 2, and
the numbers come from outputs/analysis_results.json. The script asserts that the three
sources agree, so a divergence fails the build instead of shipping a wrong page (the D3
lesson: never let the same fact be authored in two places).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The engine now lives in the API package (api/app/risk); this directory keeps the
# research record -- REPORT.md, the generated UI, and the analysis outputs.
sys.path.insert(0, str(ROOT.parent.parent / "api"))

from app.risk import dropout_ews_bn as m  # noqa: E402

REPORT = (ROOT / "REPORT.md").read_text(encoding="utf-8")
RESULTS = json.loads((ROOT / "outputs" / "analysis_results.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- parsing


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _clean(text: str) -> str:
    """Strip markdown emphasis and code ticks, keeping the words."""
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def _names(cell: str) -> list[str]:
    return [n.strip().strip("`") for n in cell.split(",") if n.strip()]


def parse_edge_tables() -> list[dict]:
    """Pull both edge-justification tables out of section 2."""
    start = REPORT.index("## 2. Edge-justification table")
    end = REPORT.index("## 3. Final DAG")
    block = REPORT[start:end]

    rows: list[dict] = []
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) != 8:
            continue
        ident = cells[0]
        if ident in {"#", ""} or set(ident) <= {"-", ":"}:
            continue
        parents, child = _names(cells[1]), _names(cells[2])[0]
        if len(child.split()) > 1:  # header row of the amendment table
            continue
        for parent in parents:
            rows.append(
                {
                    "id": ident,
                    "parent": parent,
                    "child": child,
                    "mechanism": _clean(cells[3]),
                    "evidence": _clean(cells[4]),
                    "confounders": _clean(cells[5]),
                    "modifiable": _clean(cells[6]),
                    "concern": _clean(cells[7]),
                    "amendment": ident.startswith("A"),
                }
            )
    return rows


def parse_roles() -> dict[str, str]:
    """Read node role from the mermaid classDef suffixes in section 3."""
    start = REPORT.index("## 3. Final DAG")
    end = REPORT.index("## 4. Complete executable Python code")
    block = REPORT[start:end]
    roles: dict[str, str] = {}
    for node, role in re.findall(r"\[([A-Za-z_]+)\]:::(\w+)", block):
        roles[node] = role
    return roles


# --------------------------------------------------------------------- verification

edges_meta = parse_edge_tables()
roles = parse_roles()

code_edges = list(m.BASELINE_EDGES) + list(m.AMENDMENT_EDGES)
report_pairs = {(e["parent"], e["child"]) for e in edges_meta}
code_pairs = set(code_edges)

assert report_pairs == code_pairs, (
    f"report/code edge mismatch\n  report only: {sorted(report_pairs - code_pairs)}"
    f"\n  code only:   {sorted(code_pairs - report_pairs)}"
)
assert len(edges_meta) == len(code_edges) == 42, (len(edges_meta), len(code_edges))

for e in edges_meta:
    coded = m.EDGE_EVIDENCE[(e["parent"], e["child"])].value
    assert coded == e["evidence"], f"{e['parent']}->{e['child']}: report {e['evidence']} vs code {coded}"

missing_roles = set(m.NODE_STATES) - set(roles)
assert not missing_roles, f"nodes with no role in the mermaid block: {sorted(missing_roles)}"

baseline_pairs = set(m.BASELINE_EDGES)
for e in edges_meta:
    assert e["amendment"] == ((e["parent"], e["child"]) not in baseline_pairs), e["id"]

print(f"verified: {len(edges_meta)} edges agree across REPORT.md and dropout_ews_bn.py")
print(f"verified: all {len(m.NODE_STATES)} nodes carry a role")


# ------------------------------------------------------------------------- layout

def depths(pairs: set[tuple[str, str]]) -> dict[str, int]:
    """Longest-path depth, so every edge points strictly rightwards."""
    parents: dict[str, list[str]] = {n: [] for n in m.NODE_STATES}
    for p, c in pairs:
        parents[c].append(p)
    depth: dict[str, int] = {}

    def resolve(node: str) -> int:
        if node in depth:
            return depth[node]
        depth[node] = 0 if not parents[node] else 1 + max(resolve(p) for p in parents[node])
        return depth[node]

    for node in m.NODE_STATES:
        resolve(node)
    return depth


PERIODS = {
    "standing": "Standing context — fixed or slow-moving before the term begins",
    "prior": "Prior term (t−1) — environment, household and the mediators they drive",
    "current": "Current term (t) — observed this term",
    "next": "Next term (t+1) — the forecast horizon",
}
CURRENT_TERM = {
    "Current_Academic_Performance",
    "Current_Academic_Stress",
    "Psychological_Attendance_Barrier",
    "Current_Attendance",
    "School_Engagement",
}


def period_of(node: str) -> str:
    if node == m.TARGET_NODE:
        return "next"
    if node in CURRENT_TERM:
        return "current"
    if node in m.PROTECTED_OR_IMMUTABLE_NODES or node in {"Economic_Strain", "Parent_Availability"}:
        return "standing"
    return "prior"


baseline_depth = depths(baseline_pairs)
amended_depth = depths(code_pairs)

nodes = [
    {
        "name": name,
        "states": list(states),
        "role": roles[name],
        "period": period_of(name),
        "depth": baseline_depth[name],
        "depthAmended": amended_depth[name],
        "modifiable": name in m.MODIFIABLE_NODES,
        "protected": name in m.PROTECTED_OR_IMMUTABLE_NODES,
        "observable": name in m.OBSERVABLE_AT_SCREENING,
        "target": name == m.TARGET_NODE,
    }
    for name, states in m.NODE_STATES.items()
]

payload = {
    "meta": {
        "target": m.TARGET_NODE,
        "seed": m.RANDOM_SEED,
        "provenance": m.PRIOR_PROVENANCE,
        "generatedAt": RESULTS["generated_at"],
        "notFor": RESULTS["not_for"],
        "periods": PERIODS,
        "baselineFingerprint": RESULTS["structure"]["fingerprint"],
        "amendedFingerprint": RESULTS["amended_variant"]["structure"]["fingerprint"],
    },
    "nodes": nodes,
    "edges": edges_meta,
    "evidence": {
        "baseline": RESULTS["evidence_levels"],
        "amended": RESULTS["amended_variant"]["evidence_levels"],
    },
    "scenarios": {
        "baseline": RESULTS["scenarios"],
        "amended": RESULTS["amended_variant"]["scenarios"],
    },
    "pathways": {
        "baseline": RESULTS["pathway_attenuation"],
        "amendedAttendance": RESULTS["amended_variant"]["pathway_attenuation_via_attendance"],
        "amendedEngagement": RESULTS["amended_variant"]["pathway_attenuation_via_engagement"],
    },
    "interventions": RESULTS["interventions"],
    "amendedInterventions": RESULTS["amended_variant"]["observational_vs_interventional"],
    "sensitivity": RESULTS["sensitivity"],
    "screening": RESULTS["screening_burden"],
    "structure": {
        "baseline": {k: v for k, v in RESULTS["structure"].items() if k != "parents"},
        "amended": {
            k: v for k, v in RESULTS["amended_variant"]["structure"].items() if k != "parents"
        },
        "parents": RESULTS["amended_variant"]["structure"]["parents"],
        "baselineParents": RESULTS["structure"]["parents"],
    },
    "addedEdges": RESULTS["amended_variant"]["added_edges"],
}

out = Path(sys.argv[1])
out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"wrote {out}  ({out.stat().st_size / 1024:.1f} KB)")

"""Assemble the case tool: compact the payload, inline the verified engine, emit one file.

The engine is inlined from ui/infer.js -- the same file verify_infer.cjs checks against
pgmpy -- so the page cannot drift from the verified implementation. The caseload is
re-encoded as state indices and the round trip is asserted, so compaction cannot silently
corrupt a student's record.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "case_data.json").read_text(encoding="utf-8"))

nodes = data["nodes"]
target = data["meta"]["target"]
states = {n["name"]: n["states"] for n in nodes}
var_order = [n["name"] for n in nodes if n["name"] != target]
target_states = states[target]

# Students carry 24 repeated state strings each; indices cost two characters.
caseload = []
for s in data["caseload"]:
    idx = [states[v].index(s["values"][v]) for v in var_order]
    caseload.append([s["id"], idx, target_states.index(s["simulatedOutcome"])])

# Round-trip check: decoding must reproduce the export exactly.
for original, packed in zip(data["caseload"], caseload):
    decoded = {v: states[v][i] for v, i in zip(var_order, packed[1])}
    assert decoded == original["values"], f"{original['id']}: lossy re-encoding"
    assert target_states[packed[2]] == original["simulatedOutcome"], original["id"]
print(f"verified: {len(caseload)} student records survive re-encoding unchanged")

slim = {
    "meta": data["meta"],
    "nodes": nodes,
    "varOrder": var_order,
    "caseload": caseload,
}

payload = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
assert "</script" not in payload, "payload would break out of the script tag"

engine = (HERE / "infer.js").read_text(encoding="utf-8")
assert "createEngine" in engine
assert "</script" not in engine

template = (HERE / "case.template.html").read_text(encoding="utf-8")
for token, replacement, what in (
    ("/*__INFER__*/", engine, "engine"),
    ("/*__DATA__*/null", payload, "payload"),
):
    assert template.count(token) == 1, f"expected exactly one {token} for the {what}"
    template = template.replace(token, replacement)

out = Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(template, encoding="utf-8")

print(f"payload {len(payload) / 1024:.1f} KB + engine {len(engine) / 1024:.1f} KB "
      f"-> {out.name} ({out.stat().st_size / 1024:.1f} KB)")
print(f"nodes {len(nodes)}  caseload {len(caseload)}  vars {len(var_order)}")

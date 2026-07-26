"""Project the relational roster and its evidence into Neo4j.

PostgreSQL is the system of record. The graph is a read-optimised view whose job is to
answer questions that span boundaries the relational schema keeps apart: a learner,
their class, their subjects, their weak concepts, the risk factors they carry, the
causal routes those factors take to the outcome, and the peers around them.

Peer ties are generated here rather than stored, because no real sociometric survey
exists. They are coherent with the recorded evidence -- a learner recorded as bullied
or excluded ends up with fewer ties -- so the isolation view demonstrates the intended
mechanism honestly, and is labelled as generated wherever it is shown.
"""

from __future__ import annotations

import random

from app.risk import dropout_ews_bn as bn
from app.services.dropout_risk import RiskCopy
from app.services.risk_explain import RiskExplainer

PEER_SEED = 20260726
WEAK_THRESHOLD = 0.60
STRONG_THRESHOLD = 0.75


def mastery_band(score: float) -> str:
    if score < WEAK_THRESHOLD:
        return "weak"
    if score < STRONG_THRESHOLD:
        return "borderline"
    return "strong"


def risk_factor_payload(copy: RiskCopy) -> tuple[list[dict], list[dict]]:
    """Nodes and edges for the causal DAG, with the edge-justification metadata."""
    factors = [
        {
            "id": factor["id"],
            "label": factor["label"],
            "label_si": factor.get("label_si"),
            "group": factor["group"],
            "group_si": factor.get("group_si"),
            "states": list(factor["states"]),
            "state_labels": list(factor["state_labels"]),
            "state_labels_si": list(factor["state_labels_si"]),
            "modifiable": bool(factor["modifiable"]),
            "protected": bool(factor["protected"]),
            "register": bool(factor.get("register", False)),
            "is_outcome": factor["id"] == copy.target,
        }
        for factor in copy.factors.values()
    ]

    edges = []
    for (source, target), level in bn.EDGE_EVIDENCE.items():
        edges.append(
            {
                "source": source,
                "target": target,
                "evidence": level.value,
                "mechanism": None,
                "confounders": None,
                "concern": None,
                "amendment": (source, target) in bn.AMENDMENT_EDGES,
            }
        )
    return factors, edges


def enrich_edges_with_narrative(edges: list[dict], ui_data: dict | None) -> list[dict]:
    """Attach the per-edge mechanism and fairness note from the research record."""
    if not ui_data:
        return edges
    narrative = {
        (row["parent"], row["child"]): row for row in ui_data.get("edges", [])
    }
    for edge in edges:
        row = narrative.get((edge["source"], edge["target"]))
        if row is None:
            continue
        edge["mechanism"] = row.get("mechanism")
        edge["confounders"] = row.get("confounders")
        edge["concern"] = row.get("concern")
    return edges


def build_mastery_payload(latest_by_student: dict[str, dict[str, float]]) -> list[dict]:
    return [
        {
            "student_id": student_id,
            "concept_id": concept_id,
            "score": round(score, 4),
            "band": mastery_band(score),
        }
        for student_id, concepts in latest_by_student.items()
        for concept_id, score in concepts.items()
    ]


def build_evidence_payload(
    evidence_by_student: dict[str, dict[str, str]],
    sources_by_student: dict[str, dict[str, str]],
    copy: RiskCopy,
) -> list[dict]:
    rows: list[dict] = []
    for student_id, variables in evidence_by_student.items():
        for variable, state in variables.items():
            factor = copy.factors.get(variable)
            if factor is None:
                continue
            rows.append(
                {
                    "student_id": student_id,
                    "variable": variable,
                    "state": state,
                    "state_label": copy.state_label(variable, state),
                    "concern": copy.is_concern(variable, state),
                    "source": sources_by_student.get(student_id, {}).get(variable, "seed"),
                }
            )
    return rows


def build_peer_payload(
    students: list[dict], evidence_by_student: dict[str, dict[str, str]]
) -> list[dict]:
    """Generate class-internal peer ties.

    Deterministic, and shaped by the recorded evidence: a learner marked as bullied or
    socially excluded is given markedly fewer ties, so the isolation view and the risk
    evidence tell the same story instead of contradicting each other.
    """
    rng = random.Random(PEER_SEED)
    by_class: dict[str, list[dict]] = {}
    for student in students:
        if student.get("class_id"):
            by_class.setdefault(student["class_id"], []).append(student)

    edges: list[dict] = []
    for classmates in by_class.values():
        ids = [student["id"] for student in classmates]
        if len(ids) < 3:
            continue
        for student_id in ids:
            variables = evidence_by_student.get(student_id, {})
            excluded = variables.get("Bullying_Social_Exclusion") == "High"
            withdrawn = variables.get("School_Engagement") == "Low"
            if excluded:
                tie_count = rng.randint(0, 1)
            elif withdrawn:
                tie_count = rng.randint(1, 3)
            else:
                tie_count = rng.randint(2, 5)
            candidates = [other for other in ids if other != student_id]
            for target in rng.sample(candidates, min(tie_count, len(candidates))):
                edges.append({"source": student_id, "target": target})
    return edges


def build_risk_payload(
    evidence_by_student: dict[str, dict[str, str]], explainer: RiskExplainer
) -> list[dict]:
    rows: list[dict] = []
    for student_id, variables in evidence_by_student.items():
        evidence = {
            variable: state
            for variable, state in variables.items()
            if variable in bn.NODE_STATES and state in bn.NODE_STATES[variable]
        }
        p_high = explainer.p_high(evidence)
        band, _tier = explainer.band(p_high)
        gap = explainer.circumstance_gap(evidence)
        rows.append(
            {
                "student_id": student_id,
                "p_high": round(p_high, 6),
                "band": band,
                "gap": gap["gap"],
            }
        )
    return rows

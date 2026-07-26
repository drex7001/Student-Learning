"""Assembles the disengagement risk screen from stored evidence.

Sits between the raw engine (``app.risk.dropout_ews_bn``), the explanation estimands
(``app.services.risk_explain``) and the database. Owns three responsibilities the
engine deliberately does not:

* turning ``student_risk_evidence`` rows into a validated evidence mapping,
* attaching the authored plain-language copy so no raw identifier ever reaches a
  screen,
* writing the audit row that records who asked what, of whom, against which parameters.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import models
from app.db.models import utcnow
from app.risk import dropout_ews_bn as bn
from app.schemas.risk import (
    CircumstanceGap,
    EvidenceItem,
    ModelProvenance,
    PosteriorBar,
    RiskActionCandidate,
    RiskContribution,
    RiskFactorNode,
    RiskFactorState,
    StudentRiskSummary,
)
from app.services.risk_explain import (
    REGISTER_VARIABLES,
    RiskExplainer,
    SIGNAL_VARIABLES,
)

#: Circumstances a school could plausibly write down. Mirrors school_seed but is the
#: authority for what the check-in form offers and what "worth asking" may suggest.
RECORDABLE_VARIABLES: tuple[str, ...] = (
    "Economic_Strain",
    "Parent_Education",
    "Parent_Availability",
    "Neuro_Type",
    "Child_Labour_Household_Duties",
    "Transport_Burden",
    "Food_Health_Burden",
    "Home_Educational_Support",
    "WASH_Quality",
    "Sensory_Environment",
    "School_Accommodation",
    "Bullying_Social_Exclusion",
    "Teacher_Resource_Adequacy",
)

BASIS_TEMPLATE = (
    "This figure is the share of students with the same attendance and engagement "
    "record who the model expects to leave. {register}. It is not a prediction about "
    "this child."
)


@dataclass(frozen=True)
class RiskCopy:
    """The authored plain-language layer, loaded once."""

    factors: dict[str, dict]
    target: str
    target_states: list[str]
    register_fields: list[str]
    guardrail_message: str

    def label(self, variable: str) -> str:
        return self.factors.get(variable, {}).get("label", variable)

    def state_label(self, variable: str, state: str | None) -> str | None:
        factor = self.factors.get(variable)
        if factor is None or state is None or state not in factor["states"]:
            return state
        return factor["state_labels"][factor["states"].index(state)]

    def state_label_si(self, variable: str, state: str | None) -> str | None:
        factor = self.factors.get(variable)
        if factor is None or state is None or state not in factor["states"]:
            return None
        return factor["state_labels_si"][factor["states"].index(state)]

    def is_concern(self, variable: str, state: str | None) -> bool:
        factor = self.factors.get(variable)
        if factor is None or state is None or state not in factor["states"]:
            return False
        return bool(factor["concern"][factor["states"].index(state)])


@lru_cache(maxsize=4)
def load_risk_copy(path_str: str) -> RiskCopy:
    payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    return RiskCopy(
        factors={factor["id"]: factor for factor in payload["factors"]},
        target=payload["target"],
        target_states=payload["target_states"],
        register_fields=payload["register_fields"],
        guardrail_message=payload["guardrail_message"],
    )


def provenance_from(result: dict) -> ModelProvenance:
    return ModelProvenance(
        model_variant=result["model_variant"],
        model_fingerprint=result["model_fingerprint"],
        interpretation=result["interpretation"],
        provenance=result["provenance"],
        caveat=result["caveat"],
        computed_at=result["computed_at"],
    )


def base_provenance(risk_model: bn.RiskModel) -> ModelProvenance:
    result = bn.infer_dropout_risk(risk_model, {})
    return provenance_from(result)


def posterior_bars(posterior: dict[str, float], copy: RiskCopy) -> list[PosteriorBar]:
    factor = copy.factors.get(copy.target, {})
    states = list(factor.get("states", list(posterior)))
    labels = list(factor.get("state_labels", states))
    labels_si = list(factor.get("state_labels_si", [None] * len(states)))
    bars: list[PosteriorBar] = []
    for state, label, label_si in zip(states, labels, labels_si):
        bars.append(
            PosteriorBar(
                state=state,
                label=label,
                label_si=label_si,
                probability=round(float(posterior.get(state, 0.0)), 6),
            )
        )
    return bars


def evidence_mapping(rows: dict[str, dict]) -> dict[str, str]:
    """Stored rows to a mapping the engine accepts. Unknown variables and states are
    dropped rather than raising: a stale row must not take the whole screen down."""
    mapping: dict[str, str] = {}
    for variable, row in rows.items():
        state = row["state"] if isinstance(row, dict) else row
        states = bn.NODE_STATES.get(variable)
        if states and state in states and variable != bn.TARGET_NODE:
            mapping[variable] = state
    return mapping


def build_basis(evidence: dict[str, str], copy: RiskCopy) -> str:
    parts = []
    for variable in ("Current_Attendance", "School_Engagement", "Grade_Band"):
        state = evidence.get(variable)
        if state is None:
            parts.append(f"{copy.label(variable)} not recorded")
        else:
            parts.append(f"{copy.label(variable).lower()}: {copy.state_label(variable, state)}")
    return BASIS_TEMPLATE.format(register="; ".join(parts))


def factor_node(factor: dict) -> RiskFactorNode:
    return RiskFactorNode(
        id=factor["id"],
        label=factor["label"],
        label_si=factor.get("label_si"),
        group=factor["group"],
        group_si=factor.get("group_si"),
        states=[
            RiskFactorState(
                value=state,
                label=factor["state_labels"][index],
                label_si=factor["state_labels_si"][index],
                concern=bool(factor["concern"][index]),
            )
            for index, state in enumerate(factor["states"])
        ],
        modifiable=factor["modifiable"],
        protected=factor["protected"],
        is_register=factor.get("register", False),
        action=factor.get("action"),
        why_not_actionable=factor.get("why_not_actionable"),
    )


def evidence_items(
    stored: dict[str, dict], copy: RiskCopy, explainer: RiskExplainer
) -> list[EvidenceItem]:
    """Every recordable and register variable, recorded or not, in display order."""
    order = list(RECORDABLE_VARIABLES) + list(REGISTER_VARIABLES) + ["Sector", "Grade_Band"]
    seen: set[str] = set()
    items: list[EvidenceItem] = []
    for variable in order:
        if variable in seen:
            continue
        seen.add(variable)
        factor = copy.factors.get(variable)
        if factor is None:
            continue
        row = stored.get(variable)
        state = row["state"] if row else None
        items.append(
            EvidenceItem(
                variable=variable,
                label=factor["label"],
                label_si=factor.get("label_si"),
                group=factor["group"],
                state=state,
                state_label=copy.state_label(variable, state),
                state_label_si=copy.state_label_si(variable, state),
                concern=copy.is_concern(variable, state),
                source=row["source"] if row else None,
                recorded_at=row["recorded_at"] if row else None,
                modifiable=factor["modifiable"],
                protected=factor["protected"],
            )
        )
    return items


def contribution_models(
    contributions, copy: RiskCopy, limit: int | None = None
) -> list[RiskContribution]:
    rows: list[RiskContribution] = []
    for item in contributions[:limit] if limit else contributions:
        factor = copy.factors.get(item.variable, {})
        rows.append(
            RiskContribution(
                variable=item.variable,
                label=factor.get("label", item.variable),
                label_si=factor.get("label_si"),
                group=factor.get("group", ""),
                state=item.state or None,
                state_label=copy.state_label(item.variable, item.state) if item.state else None,
                state_label_si=(
                    copy.state_label_si(item.variable, item.state) if item.state else None
                ),
                delta=item.delta,
                causal=item.causal,
            )
        )
    return rows


def action_models(contributions, copy: RiskCopy) -> list[RiskActionCandidate]:
    rows: list[RiskActionCandidate] = []
    for item in contributions:
        factor = copy.factors.get(item.variable, {})
        action = factor.get("action") or {}
        rows.append(
            RiskActionCandidate(
                variable=item.variable,
                label=factor.get("label", item.variable),
                label_si=factor.get("label_si"),
                action=action.get("action", ""),
                action_si=action.get("action_si") or None,
                owner=action.get("owner", ""),
                detail=action.get("detail"),
                caveat=action.get("caveat"),
                target_state=item.state,
                delta=item.delta,
            )
        )
    return rows


def student_summary(
    *,
    student: dict,
    p_high: float,
    band: str,
    alert_tier: str,
    gap: CircumstanceGap,
    top_driver: str | None,
    recorded_count: int,
    unrecorded_count: int,
) -> StudentRiskSummary:
    return StudentRiskSummary(
        student_id=student["id"],
        student_name=student["full_name"],
        student_name_si=student.get("full_name_si"),
        cohort=student["cohort"],
        class_id=student.get("class_id"),
        school_id=student.get("school_id"),
        p_high=round(p_high, 6),
        band=band,
        alert_tier=alert_tier,
        gap=gap.gap,
        circumstances_ahead=gap.ahead,
        top_driver=top_driver,
        recorded_count=recorded_count,
        unrecorded_count=unrecorded_count,
    )


def record_assessment(
    session: Session,
    *,
    student_id: str,
    term_id: str,
    evidence: dict[str, str],
    result: dict,
    band: str,
    gap: float,
    user_id: str | None,
) -> None:
    """Audit trail. REPORT.md section 11.2 asks for reads to be logged as well as
    writes, so every profile view lands here."""
    session.add(
        models.RiskAssessment(
            id=f"RA-{uuid.uuid4().hex[:16].upper()}",
            student_id=student_id,
            term_id=term_id,
            model_variant=result["model_variant"],
            model_fingerprint=result["model_fingerprint"],
            evidence_json=json.dumps(evidence, sort_keys=True),
            posterior_json=json.dumps(result["posterior"]),
            p_high=float(result["posterior"]["High"]),
            band=band,
            interpretation=result["interpretation"],
            circumstance_gap=gap,
            computed_at=utcnow(),
            computed_by=user_id,
        )
    )


def get_explainer(request_app) -> RiskExplainer:
    """One explainer per process, sharing the model and its query cache."""
    explainer = getattr(request_app.state, "risk_explainer", None)
    if explainer is None:
        explainer = RiskExplainer(request_app.state.risk_model)
        request_app.state.risk_explainer = explainer
    return explainer


__all__ = [
    "RECORDABLE_VARIABLES",
    "REGISTER_VARIABLES",
    "SIGNAL_VARIABLES",
    "RiskCopy",
    "action_models",
    "base_provenance",
    "build_basis",
    "contribution_models",
    "evidence_items",
    "evidence_mapping",
    "factor_node",
    "get_explainer",
    "load_risk_copy",
    "posterior_bars",
    "provenance_from",
    "record_assessment",
    "student_summary",
]

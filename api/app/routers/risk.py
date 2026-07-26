from __future__ import annotations

import itertools

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, current_user, deny_students, require_staff
from app.db.postgres import get_session
from app.repositories.postgres_repository import PostgresRepository
from app.risk import dropout_ews_bn as bn
from app.schemas.risk import (
    CircumstanceGap,
    EvidenceUpdateRequest,
    FactorCohortMember,
    FactorCohortResponse,
    PlanRequest,
    PlanResponse,
    RiskCaseloadResponse,
    RiskCaseloadSummary,
    RiskModelEdge,
    RiskModelResponse,
    RiskProfileResponse,
    RoutePath,
    RoutesResponse,
    ScreeningCell,
    ScreeningMatrixResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from app.services.dropout_risk import (
    RECORDABLE_VARIABLES,
    action_models,
    base_provenance,
    build_basis,
    contribution_models,
    evidence_items,
    evidence_mapping,
    factor_node,
    get_explainer,
    load_risk_copy,
    posterior_bars,
    provenance_from,
    record_assessment,
    student_summary,
)

router = APIRouter(prefix="/api/risk", tags=["risk"])


def _copy():
    return load_risk_copy(str(settings.risk_factor_copy_path))


def _require_term(repository: PostgresRepository):
    term = repository.get_current_term()
    if term is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current term. Seed the school data first.",
        )
    return term


@router.get("/model", response_model=RiskModelResponse)
def get_risk_model(
    request: Request, user: CurrentUser = Depends(require_staff)
) -> RiskModelResponse:
    """The causal DAG plus the authored plain-language layer."""
    copy = _copy()
    explainer = get_explainer(request.app)
    risk_model = request.app.state.risk_model

    edges = [
        RiskModelEdge(
            source=source,
            target=target,
            evidence_level=(
                bn.EDGE_EVIDENCE[(source, target)].value
                if (source, target) in bn.EDGE_EVIDENCE
                else None
            ),
        )
        for source, target in risk_model.model.edges()
    ]
    return RiskModelResponse(
        target=copy.target,
        target_states=copy.target_states,
        factors=[factor_node(factor) for factor in copy.factors.values()],
        edges=edges,
        register_fields=copy.register_fields,
        guardrail_message=copy.guardrail_message,
        prior_p_high=round(explainer.prior_high, 6),
        watch_threshold=round(explainer.prior_high, 6),
        attention_threshold=0.30,
        provenance=base_provenance(risk_model),
    )


@router.get("/screening-matrix", response_model=ScreeningMatrixResponse)
def screening_matrix(
    request: Request, user: CurrentUser = Depends(require_staff)
) -> ScreeningMatrixResponse:
    """The whole screen, in twelve numbers.

    The outcome's only parents are attendance this term, engagement and grade band, so
    a complete register determines the figure exactly. Showing the full table makes
    plain that this is a shortlist, not a ranking of children.
    """
    explainer = get_explainer(request.app)
    # Exactly the outcome's parents: 2 x 2 x 3 = 12 cells. Last term's attendance is
    # deliberately absent -- it is d-separated from the outcome once this term's is
    # known, so including it would double the table with identical numbers.
    cells: list[ScreeningCell] = []
    for current, engagement, grade_band in itertools.product(
        bn.NODE_STATES["Current_Attendance"],
        bn.NODE_STATES["School_Engagement"],
        bn.NODE_STATES["Grade_Band"],
    ):
        evidence = {
            "Current_Attendance": current,
            "School_Engagement": engagement,
            "Grade_Band": grade_band,
        }
        p_high = explainer.p_high(evidence)
        band, _tier = explainer.band(p_high)
        cells.append(
            ScreeningCell(
                current_attendance=current,
                school_engagement=engagement,
                grade_band=grade_band,
                p_high=round(p_high, 6),
                band=band,
            )
        )
    return ScreeningMatrixResponse(
        cells=cells,
        note=(
            "Twelve numbers are the whole screen. The outcome depends only on "
            "attendance this term, engagement and grade band, so a complete register "
            "determines the figure exactly. Everything else in a record tells you what "
            "to do, not what to expect."
        ),
        provenance=base_provenance(request.app.state.risk_model),
    )


@router.get("/caseload", response_model=RiskCaseloadResponse)
def caseload(
    request: Request,
    school_id: str | None = Query(default=None),
    class_id: str | None = Query(default=None),
    threshold: float = Query(default=0.20, ge=0.0, le=1.0),
    limit: int = Query(default=600, ge=1, le=2000),
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> RiskCaseloadResponse:
    copy = _copy()
    explainer = get_explainer(request.app)
    repository = PostgresRepository(session)
    term = _require_term(repository)

    students = repository.list_students(limit=limit, school_id=school_id, class_id=class_id)
    evidence_by_student = repository.get_risk_evidence_bulk(
        [student["id"] for student in students], term.id
    )

    rows = []
    counts = {"needs_attention": 0, "watch": 0, "not_marked": 0}
    ahead_count = 0
    flagged = 0

    for student in students:
        stored = evidence_by_student.get(student["id"], {})
        evidence = evidence_mapping({k: {"state": v} for k, v in stored.items()})
        p_high = explainer.p_high(evidence)
        band, tier = explainer.band(p_high)
        gap = CircumstanceGap(**explainer.circumstance_gap(evidence))
        drivers = explainer.drivers(evidence, copy.factors)
        top_driver = copy.label(drivers[0].variable) if drivers else None

        counts[band] += 1
        if gap.ahead:
            ahead_count += 1
        if p_high >= threshold:
            flagged += 1

        recorded = sum(1 for v in RECORDABLE_VARIABLES if v in evidence)
        rows.append(
            student_summary(
                student=student,
                p_high=p_high,
                band=band,
                alert_tier=tier,
                gap=gap,
                top_driver=top_driver,
                recorded_count=recorded,
                unrecorded_count=len(RECORDABLE_VARIABLES) - recorded,
            )
        )

    rows.sort(key=lambda row: (-row.p_high, -row.gap, row.student_id))
    total = len(rows)
    return RiskCaseloadResponse(
        summary=RiskCaseloadSummary(
            total_students=total,
            needs_attention=counts["needs_attention"],
            watch=counts["watch"],
            not_marked=counts["not_marked"],
            circumstances_ahead=ahead_count,
            threshold=threshold,
            flagged_at_threshold=flagged,
            flagged_share=round(flagged / total, 4) if total else 0.0,
        ),
        students=rows,
        provenance=base_provenance(request.app.state.risk_model),
        basis=(
            "Ranked by the share of students with the same register pattern who the "
            "model expects to leave. Most students on this list would not have left "
            "anyway: every entry must lead to an offer of support that costs the "
            "student nothing if the flag was wrong."
        ),
    )


@router.get("/students/{student_id}", response_model=RiskProfileResponse)
def student_risk_profile(
    student_id: str,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> RiskProfileResponse:
    deny_students(user)
    copy = _copy()
    explainer = get_explainer(request.app)
    repository = PostgresRepository(session)
    term = _require_term(repository)

    student = repository.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    stored = repository.get_risk_evidence(student_id, term.id)
    evidence = evidence_mapping(stored)

    result = bn.infer_dropout_risk(explainer.risk_model, evidence)
    p_high = float(result["posterior"]["High"])
    band, tier = explainer.band(p_high)
    gap = CircumstanceGap(**explainer.circumstance_gap(evidence))

    drivers = explainer.drivers(evidence, copy.factors)
    actions = explainer.action_candidates(evidence, copy.factors)
    asking = explainer.worth_asking(evidence, copy.factors, RECORDABLE_VARIABLES)

    record_assessment(
        session,
        student_id=student_id,
        term_id=term.id,
        evidence=evidence,
        result=result,
        band=band,
        gap=gap.gap,
        user_id=user.id,
    )
    session.commit()

    recorded = sum(1 for v in RECORDABLE_VARIABLES if v in evidence)
    locked = [
        factor_node(factor)
        for factor in copy.factors.values()
        if factor["protected"] and factor["id"] != copy.target
    ]

    return RiskProfileResponse(
        student=student_summary(
            student=student,
            p_high=p_high,
            band=band,
            alert_tier=tier,
            gap=gap,
            top_driver=copy.label(drivers[0].variable) if drivers else None,
            recorded_count=recorded,
            unrecorded_count=len(RECORDABLE_VARIABLES) - recorded,
        ),
        posterior=posterior_bars(result["posterior"], copy),
        basis=build_basis(evidence, copy),
        gap_detail=gap,
        drivers=contribution_models(drivers, copy, limit=8),
        actions=action_models(actions, copy),
        worth_asking=contribution_models(asking, copy, limit=6),
        evidence=evidence_items(stored, copy, explainer),
        attendance=repository.get_attendance(student_id),
        locked_factors=locked,
        provenance=provenance_from(result),
    )


@router.post("/students/{student_id}/what-if", response_model=WhatIfResponse)
def what_if(
    student_id: str,
    payload: WhatIfRequest,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> WhatIfResponse:
    """Ask the model a hypothetical.

    ``intervention`` is a real ``do()``. It is restricted to an allowlist of things a
    school can change: intervening on a protected characteristic returns 403, because
    "what if this child were not autistic" is a forbidden question rather than a
    malformed one.
    """
    deny_students(user)
    copy = _copy()
    explainer = get_explainer(request.app)
    repository = PostgresRepository(session)
    term = _require_term(repository)

    stored = repository.get_risk_evidence(student_id, term.id)
    evidence = evidence_mapping(stored)
    if payload.evidence:
        for variable, state in payload.evidence.items():
            if state is None:
                evidence.pop(variable, None)
            else:
                evidence[variable] = state

    try:
        evidence = bn.validate_evidence(evidence)
        if payload.intervention:
            # Intervening on a variable overrides whatever was observed about it --
            # do() cuts its incoming edges and sets the value. Leaving the recorded
            # state in the evidence set would ask the model to both fix and observe
            # the same variable, which the engine rightly refuses.
            conditioning = {
                variable: state
                for variable, state in evidence.items()
                if variable not in payload.intervention
            }
            result = bn.estimate_intervention_effect(
                explainer.risk_model, payload.intervention, conditioning
            )
        else:
            result = bn.infer_dropout_risk(explainer.risk_model, evidence)
    except bn.NonModifiableInterventionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except bn.EvidenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    p_high = float(result["posterior"]["High"])
    band, tier = explainer.band(p_high)
    return WhatIfResponse(
        posterior=posterior_bars(result["posterior"], copy),
        p_high=round(p_high, 6),
        band=band,
        alert_tier=tier,
        evidence_used=evidence,
        intervention_used=payload.intervention,
        provenance=provenance_from(result),
    )


@router.post("/students/{student_id}/plan", response_model=PlanResponse)
def support_plan(
    student_id: str,
    payload: PlanRequest,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> PlanResponse:
    """Joint effect of acting on several levers at once."""
    deny_students(user)
    copy = _copy()
    explainer = get_explainer(request.app)
    repository = PostgresRepository(session)
    term = _require_term(repository)

    evidence = evidence_mapping(repository.get_risk_evidence(student_id, term.id))
    try:
        plan = explainer.plan_effect(evidence, payload.variables, copy.factors)
    except bn.NonModifiableInterventionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return PlanResponse(
        **plan,
        note=(
            "The joint effect is not the sum of the separate effects, because these "
            "pathways overlap in the model."
        ),
        provenance=base_provenance(explainer.risk_model),
    )


@router.get("/students/{student_id}/routes/{variable}", response_model=RoutesResponse)
def factor_routes(
    student_id: str,
    variable: str,
    request: Request,
    user: CurrentUser = Depends(require_staff),
) -> RoutesResponse:
    """How a factor reaches the outcome. Every path runs through a mechanism."""
    deny_students(user)
    copy = _copy()
    explainer = get_explainer(request.app)
    if variable not in bn.NODE_STATES:
        raise HTTPException(status_code=404, detail="Unknown risk factor.")
    paths = explainer.routes(variable)
    return RoutesResponse(
        variable=variable,
        label=copy.label(variable),
        paths=[
            RoutePath(nodes=path, labels=[copy.label(node) for node in path])
            for path in paths
        ],
        note=(
            "Every route runs through something a school can change. There is no "
            "direct edge from a protected characteristic to the outcome."
        ),
    )


@router.put("/students/{student_id}/evidence")
def update_evidence(
    student_id: str,
    payload: EvidenceUpdateRequest,
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> dict:
    """Teacher wellbeing check-in."""
    deny_students(user)
    repository = PostgresRepository(session)
    term = _require_term(repository)
    if repository.get_student(student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    applied = 0
    for item in payload.updates:
        states = bn.NODE_STATES.get(item.variable)
        if states is None or item.variable == bn.TARGET_NODE:
            raise HTTPException(
                status_code=422, detail=f"Unknown risk factor '{item.variable}'."
            )
        if item.state is not None and item.state not in states:
            raise HTTPException(
                status_code=422,
                detail=f"'{item.state}' is not a state of {item.variable}. Valid: {list(states)}.",
            )
        repository.upsert_risk_evidence(
            student_id=student_id,
            term_id=term.id,
            variable=item.variable,
            state=item.state,
            source="teacher",
            recorded_by=user.id,
            note=item.note,
        )
        applied += 1
    session.commit()
    return {"student_id": student_id, "term_id": term.id, "updated": applied}


@router.get("/factors/{variable}/cohort", response_model=FactorCohortResponse)
def factor_cohort(
    variable: str,
    request: Request,
    state: str | None = Query(default=None),
    school_id: str | None = Query(default=None),
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> FactorCohortResponse:
    """Who else shares this concern.

    A factor that many students in one school share is a school-level problem with a
    school-level fix. Reading it as a list of individual children to watch is the
    mistake this endpoint exists to prevent.
    """
    deny_students(user)
    copy = _copy()
    factor = copy.factors.get(variable)
    if factor is None:
        raise HTTPException(status_code=404, detail="Unknown risk factor.")

    if state is None:
        concern_states = [
            value for value, flag in zip(factor["states"], factor["concern"]) if flag
        ]
        state = concern_states[0] if concern_states else factor["states"][-1]

    repository = PostgresRepository(session)
    term = _require_term(repository)
    students = repository.list_students(limit=2000, school_id=school_id)
    evidence = repository.get_risk_evidence_bulk([s["id"] for s in students], term.id)

    members: list[FactorCohortMember] = []
    recorded = 0
    for student in students:
        stored_state = evidence.get(student["id"], {}).get(variable)
        if stored_state is None:
            continue
        recorded += 1
        if stored_state == state:
            members.append(
                FactorCohortMember(
                    student_id=student["id"],
                    student_name=student["full_name"],
                    cohort=student["cohort"],
                    class_id=student.get("class_id"),
                )
            )

    share = round(len(members) / recorded, 4) if recorded else 0.0
    if factor["modifiable"] and share >= 0.30:
        interpretation = (
            f"{len(members)} of {recorded} recorded students share this. At this scale "
            "it is a school-level condition to fix, not a set of individual children to "
            "monitor."
        )
    else:
        interpretation = (
            f"{len(members)} of {recorded} recorded students share this."
        )

    return FactorCohortResponse(
        variable=variable,
        label=factor["label"],
        state=state,
        state_label=copy.state_label(variable, state) or state,
        school_id=school_id,
        total_recorded=recorded,
        affected=len(members),
        share=share,
        interpretation=interpretation,
        students=members[:200],
    )

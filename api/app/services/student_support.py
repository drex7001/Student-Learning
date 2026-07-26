from __future__ import annotations

from collections import defaultdict

from app.schemas.diagnosis import StudentSummary, SubjectNode
from app.schemas.student_support import (
    StudentSupportProfileResponse,
    SupportRisk,
    SupportRiskFactor,
    SupportRiskFeatures,
)
WEAK_THRESHOLD = 0.60
STRONG_THRESHOLD = 0.75
LOW_CONFIDENCE_THRESHOLD = 0.55
DECLINE_DELTA = 0.05


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _safe_average(values: list[float], default: float = 0.0) -> float:
    if not values:
        return default
    return sum(values) / len(values)


def _downstream_impact_by_concept(edges: list[dict]) -> dict[str, int]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[edge["source_id"]].append(edge["target_id"])

    def visit(concept_id: str, seen: set[str]) -> set[str]:
        for child_id in adjacency.get(concept_id, []):
            if child_id in seen:
                continue
            seen.add(child_id)
            visit(child_id, seen)
        return seen

    concept_ids = set(adjacency.keys()) | {target for targets in adjacency.values() for target in targets}
    return {concept_id: len(visit(concept_id, set())) for concept_id in concept_ids}


class StudentSupportEngine:
    """Builds an explainable *academic support* profile from learning evidence.

    This is deliberately a different quantity from disengagement risk. It answers
    "which learners need teaching attention in this subject, and why?" using concept
    mastery, prerequisite weakness, confidence, trend and cohort comparison. It makes
    no claim about a student leaving school -- that is the Bayesian network's job
    (``app.risk``), and the two are kept verbally and visually distinct in the UI.

    Scoring is a transparent additive attribution: every factor's contribution is a
    named, signed weight, so the explanation is the computation rather than a
    post-hoc approximation of it.
    """

    def build_profile(
        self,
        *,
        student: dict,
        subject: dict,
        concepts: list[dict],
        edges: list[dict],
        latest_scores: dict[str, dict],
        recent_scores_by_concept: dict[str, list[dict]],
        cohort_mastery_by_concept: dict[str, float | None],
        assessment_summary: dict,
    ) -> StudentSupportProfileResponse:
        features = self.build_features(
            concepts=concepts,
            edges=edges,
            latest_scores=latest_scores,
            recent_scores_by_concept=recent_scores_by_concept,
            cohort_mastery_by_concept=cohort_mastery_by_concept,
            assessment_summary=assessment_summary,
        )

        risk, factors = self._score(features)
        explanation_method = "additive_feature_attribution"

        actions = self._recommended_actions(features, risk, factors)
        top_positive_factors = [
            factor
            for factor in factors
            if factor.direction == "increases_risk" and factor.impact > 0
        ]
        top_positive_factors.sort(key=lambda factor: factor.impact, reverse=True)
        main_reason = top_positive_factors[0].label if top_positive_factors else "No major factor"

        return StudentSupportProfileResponse(
            student=StudentSummary(**student),
            subject=SubjectNode(**subject),
            risk=risk,
            features=features,
            explanation_method=explanation_method,
            explanation_summary=(
                f"This learner needs {risk.band.replace('_', ' ')} in this subject, "
                f"mainly because of {main_reason.lower()}."
            ),
            factors=factors,
            recommended_actions=actions,
        )

    def build_features(
        self,
        *,
        concepts: list[dict],
        edges: list[dict],
        latest_scores: dict[str, dict],
        recent_scores_by_concept: dict[str, list[dict]],
        cohort_mastery_by_concept: dict[str, float | None],
        assessment_summary: dict,
    ) -> SupportRiskFeatures:
        return self._build_features(
            concepts=concepts,
            edges=edges,
            latest_scores=latest_scores,
            recent_scores_by_concept=recent_scores_by_concept,
            cohort_mastery_by_concept=cohort_mastery_by_concept,
            assessment_summary=assessment_summary,
        )

    def _build_features(
        self,
        *,
        concepts: list[dict],
        edges: list[dict],
        latest_scores: dict[str, dict],
        recent_scores_by_concept: dict[str, list[dict]],
        cohort_mastery_by_concept: dict[str, float | None],
        assessment_summary: dict,
    ) -> SupportRiskFeatures:
        subject_concept_ids = [concept["id"] for concept in concepts]
        concept_count = len(subject_concept_ids)
        downstream_impact = _downstream_impact_by_concept(edges)

        mastery_values: list[float] = []
        confidence_values: list[float] = []
        cohort_gaps: list[float] = []
        weak_concept_count = 0
        borderline_concept_count = 0
        strong_concept_count = 0
        missing_evidence_count = 0
        low_confidence_count = 0
        mastery_decline_count = 0
        root_cause_count = 0

        for concept_id in subject_concept_ids:
            score = latest_scores.get(concept_id)
            if score is None:
                missing_evidence_count += 1
                continue

            mastery = float(score["mastery_score"])
            confidence = float(score["confidence"])
            mastery_values.append(mastery)
            confidence_values.append(confidence)

            if mastery < WEAK_THRESHOLD:
                weak_concept_count += 1
                if downstream_impact.get(concept_id, 0) > 0:
                    root_cause_count += 1
            elif mastery < STRONG_THRESHOLD:
                borderline_concept_count += 1
            else:
                strong_concept_count += 1

            if confidence < LOW_CONFIDENCE_THRESHOLD:
                low_confidence_count += 1

            recent_scores = recent_scores_by_concept.get(concept_id, [])
            if len(recent_scores) >= 2:
                latest_mastery = float(recent_scores[0]["mastery_score"])
                previous_mastery = float(recent_scores[1]["mastery_score"])
                if latest_mastery < previous_mastery - DECLINE_DELTA:
                    mastery_decline_count += 1

            cohort_mastery = cohort_mastery_by_concept.get(concept_id)
            if cohort_mastery is not None:
                cohort_gaps.append(mastery - cohort_mastery)

        avg_mastery = _safe_average(mastery_values)
        avg_confidence = _safe_average(confidence_values, default=0.35)
        cohort_gap_avg = _safe_average(cohort_gaps) if cohort_gaps else None

        return SupportRiskFeatures(
            avg_mastery=round(avg_mastery, 4),
            weak_concept_count=weak_concept_count,
            borderline_concept_count=borderline_concept_count,
            strong_concept_count=strong_concept_count,
            missing_evidence_count=missing_evidence_count,
            avg_confidence=round(avg_confidence, 4),
            low_confidence_count=low_confidence_count,
            mastery_decline_count=mastery_decline_count,
            cohort_gap_avg=_round(cohort_gap_avg),
            root_cause_count=root_cause_count,
            concept_count=concept_count,
            assessment_count=int(assessment_summary.get("assessment_count", 0)),
            recent_accuracy=round(avg_mastery, 4),
        )

    def _score(self, features: SupportRiskFeatures) -> tuple[SupportRisk, list[SupportRiskFactor]]:
        concept_count = max(features.concept_count, 1)
        weak_ratio = features.weak_concept_count / concept_count
        decline_ratio = features.mastery_decline_count / concept_count
        root_cause_ratio = features.root_cause_count / concept_count
        missing_ratio = features.missing_evidence_count / concept_count
        negative_cohort_gap = max(0.0, -(features.cohort_gap_avg or 0.0))

        components = [
            SupportRiskFactor(
                feature="avg_mastery",
                label="Low average mastery",
                value=features.avg_mastery,
                impact=round(max(0.0, 1.0 - features.avg_mastery) * 0.34, 4),
                direction="increases_risk",
                explanation="Lower subject mastery increases support priority.",
            ),
            SupportRiskFactor(
                feature="weak_concept_count",
                label="Weak concepts",
                value=features.weak_concept_count,
                impact=round(weak_ratio * 0.22, 4),
                direction="increases_risk",
                explanation="More weak concepts means the learner may struggle with upcoming work.",
            ),
            SupportRiskFactor(
                feature="mastery_decline_count",
                label="Recent decline",
                value=features.mastery_decline_count,
                impact=round(decline_ratio * 0.14, 4),
                direction="increases_risk",
                explanation="Concepts that dropped recently increase the need for teacher review.",
            ),
            SupportRiskFactor(
                feature="cohort_gap_avg",
                label="Below cohort average",
                value=features.cohort_gap_avg,
                impact=round(min(negative_cohort_gap, 0.35) / 0.35 * 0.12, 4),
                direction="increases_risk",
                explanation="A larger gap from the class average increases prioritisation.",
            ),
            SupportRiskFactor(
                feature="root_cause_count",
                label="Weak prerequisites",
                value=features.root_cause_count,
                impact=round(root_cause_ratio * 0.10, 4),
                direction="increases_risk",
                explanation="Weak prerequisite concepts affect downstream learning.",
            ),
            SupportRiskFactor(
                feature="avg_confidence",
                label="Low evidence confidence",
                value=features.avg_confidence,
                impact=round(max(0.0, 1.0 - features.avg_confidence) * 0.06, 4),
                direction="increases_risk",
                explanation="Low evidence confidence means the teacher should collect more proof before deciding.",
            ),
            SupportRiskFactor(
                feature="missing_evidence_count",
                label="Missing concept evidence",
                value=features.missing_evidence_count,
                impact=round(missing_ratio * 0.06, 4),
                direction="increases_risk",
                explanation="Missing concept evidence increases uncertainty and support priority.",
            ),
            SupportRiskFactor(
                feature="strong_concept_count",
                label="Strong concepts",
                value=features.strong_concept_count,
                impact=round(-(features.strong_concept_count / concept_count) * 0.08, 4),
                direction="reduces_risk",
                explanation="Strong concepts reduce overall support priority.",
            ),
        ]

        raw_score = sum(factor.impact for factor in components)
        risk_score = round(min(max(raw_score, 0.0), 1.0), 4)
        if risk_score >= 0.65:
            band = "high_support"
        elif risk_score >= 0.38:
            band = "watch"
        else:
            band = "stable"

        confidence_penalty = missing_ratio * 0.25
        confidence = round(min(max(features.avg_confidence - confidence_penalty, 0.0), 0.95), 4)
        return SupportRisk(score=risk_score, band=band, confidence=confidence), sorted(
            components,
            key=lambda factor: abs(factor.impact),
            reverse=True,
        )

    def _recommended_actions(
        self,
        features: SupportRiskFeatures,
        risk: SupportRisk,
        factors: list[SupportRiskFactor],
    ) -> list[str]:
        actions: list[str] = []
        if features.root_cause_count > 0:
            actions.append("Start with the weakest prerequisite concepts before teaching the next concept.")
        if features.weak_concept_count > 0:
            actions.append("Assign a short practice task for the weak concepts and review the answers in class.")
        if features.mastery_decline_count > 0:
            actions.append("Compare the latest assessment with the previous one to find where performance dropped.")
        if features.low_confidence_count > 0 or features.missing_evidence_count > 0:
            actions.append("Collect one small quiz or teacher check-in to improve evidence confidence.")
        if risk.band == "stable":
            actions.append("No urgent intervention is needed; keep the learner on normal practice and monitoring.")
        if not actions:
            actions.append("Review the learner profile and continue normal monitoring.")
        return actions[:4]

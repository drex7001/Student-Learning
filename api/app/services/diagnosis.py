from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from app.schemas.diagnosis import (
    ConceptNode,
    ConceptTrend,
    DiagnosisResponse,
    PathSegment,
    RemediationStep,
    RootCauseCandidate,
    StudentReadiness,
    StudentSummary,
    TrendPoint,
    WeakConcept,
)


@dataclass
class DiagnosisEngine:
    default_mastery: float = 0.5
    default_confidence: float = 0.35

    def run(
        self,
        *,
        student_id: str,
        student: dict,
        target_concept: dict,
        prerequisite_paths: list[list[dict]],
        latest_scores: dict[str, dict],
        recent_scores_by_concept: dict[str, list[dict]],
        assessment_summary: dict,
        cohort_target_mastery: float | None,
    ) -> DiagnosisResponse:
        weak_concepts = self._weak_node_scoring(prerequisite_paths, latest_scores)
        concept_trends = self._build_concept_trends(weak_concepts, recent_scores_by_concept)
        ranked_root_causes = self._root_cause_ranking(weak_concepts)
        readiness = self._build_student_readiness(
            target_concept=target_concept,
            prerequisite_paths=prerequisite_paths,
            latest_scores=latest_scores,
            assessment_summary=assessment_summary,
            cohort_target_mastery=cohort_target_mastery,
        )
        explanation = self._explanation_formatter(target_concept, weak_concepts, ranked_root_causes)
        remediation_order = self._build_remediation_order(weak_concepts)

        return DiagnosisResponse(
            student_id=student_id,
            student=StudentSummary(**student),
            target_concept=ConceptNode(**target_concept),
            readiness=readiness,
            prerequisite_paths=[
                PathSegment(path_index=index, nodes=[ConceptNode(**node) for node in path])
                for index, path in enumerate(prerequisite_paths, start=1)
            ],
            weak_concepts=weak_concepts,
            concept_trends=concept_trends,
            root_cause_candidates=ranked_root_causes,
            remediation_order=remediation_order,
            explanation=explanation,
        )

    def _weak_node_scoring(self, prerequisite_paths: list[list[dict]], latest_scores: dict[str, dict]) -> list[WeakConcept]:
        concept_depths: dict[str, int] = {}
        concept_names: dict[str, str] = {}
        for path in prerequisite_paths:
            for depth, node in enumerate(path):
                concept_names[node["id"]] = node["name"]
                current_depth = concept_depths.get(node["id"])
                if current_depth is None or depth < current_depth:
                    concept_depths[node["id"]] = depth

        weak_concepts: list[WeakConcept] = []
        for concept_id, depth in concept_depths.items():
            score = latest_scores.get(
                concept_id,
                {"mastery_score": self.default_mastery, "confidence": self.default_confidence},
            )
            mastery = round(score["mastery_score"], 4)
            confidence = round(score["confidence"], 4)
            if mastery < 0.75:
                weak_concepts.append(
                    WeakConcept(
                        concept_id=concept_id,
                        concept_name=concept_names[concept_id],
                        mastery_score=mastery,
                        confidence=confidence,
                        depth=depth,
                        evidence=(
                            "Observed score below threshold"
                            if concept_id in latest_scores
                            else "Missing recent evidence, using fallback confidence"
                        ),
                    )
                )

        weak_concepts.sort(key=lambda item: (item.depth, item.mastery_score, item.confidence))
        return weak_concepts

    def _build_concept_trends(
        self,
        weak_concepts: list[WeakConcept],
        recent_scores_by_concept: dict[str, list[dict]],
    ) -> list[ConceptTrend]:
        trends: list[ConceptTrend] = []
        for weak_concept in weak_concepts[:5]:
            points = recent_scores_by_concept.get(weak_concept.concept_id, [])
            if not points:
                continue

            latest_point = points[0]
            prior_point = points[1] if len(points) > 1 else None
            delta = round(
                latest_point["mastery_score"] - (prior_point["mastery_score"] if prior_point else latest_point["mastery_score"]),
                4,
            )
            if prior_point is None:
                direction = "limited_history"
            elif delta >= 0.08:
                direction = "improving"
            elif delta <= -0.08:
                direction = "declining"
            else:
                direction = "stable"

            trends.append(
                ConceptTrend(
                    concept_id=weak_concept.concept_id,
                    concept_name=weak_concept.concept_name,
                    direction=direction,
                    delta=delta,
                    latest_mastery=round(latest_point["mastery_score"], 4),
                    prior_mastery=round(prior_point["mastery_score"], 4) if prior_point else None,
                    points=[
                        TrendPoint(
                            assessment_date=point["assessment_date"],
                            mastery_score=round(point["mastery_score"], 4),
                            confidence=round(point["confidence"], 4),
                        )
                        for point in points
                    ],
                )
            )
        return trends

    def _root_cause_ranking(self, weak_concepts: list[WeakConcept]) -> list[RootCauseCandidate]:
        ranked = []
        for concept in weak_concepts:
            severity_score = round(
                (1 - concept.mastery_score) * 0.7
                + (1 / (concept.depth + 1)) * 0.2
                + (1 - concept.confidence) * 0.1,
                4,
            )
            ranked.append(
                RootCauseCandidate(
                    concept_id=concept.concept_id,
                    concept_name=concept.concept_name,
                    severity_score=severity_score,
                    rationale=f"Depth {concept.depth}, mastery {concept.mastery_score:.2f}, confidence {concept.confidence:.2f}",
                )
            )
        ranked.sort(key=lambda item: item.severity_score, reverse=True)
        return ranked[:5]

    def _build_student_readiness(
        self,
        *,
        target_concept: dict,
        prerequisite_paths: list[list[dict]],
        latest_scores: dict[str, dict],
        assessment_summary: dict,
        cohort_target_mastery: float | None,
    ) -> StudentReadiness:
        target_score = latest_scores.get(
            target_concept["id"],
            {"mastery_score": self.default_mastery, "confidence": self.default_confidence},
        )

        prerequisite_ids = sorted(
            {
                node["id"]
                for path in prerequisite_paths
                for node in path[:-1]
            }
        )
        prerequisite_scores = [
            latest_scores.get(
                concept_id,
                {"mastery_score": self.default_mastery, "confidence": self.default_confidence},
            )["mastery_score"]
            for concept_id in prerequisite_ids
        ]
        prerequisite_confidences = [
            latest_scores.get(
                concept_id,
                {"mastery_score": self.default_mastery, "confidence": self.default_confidence},
            )["confidence"]
            for concept_id in prerequisite_ids
        ]

        readiness_score = round(
            target_score["mastery_score"] * 0.55
            + mean(prerequisite_scores or [self.default_mastery]) * 0.35
            + mean(prerequisite_confidences or [self.default_confidence]) * 0.10,
            4,
        )
        if readiness_score < 0.55:
            status = "needs_immediate_support"
        elif readiness_score < 0.72:
            status = "watch"
        else:
            status = "ready_to_progress"

        cohort_gap = None
        if cohort_target_mastery is not None:
            cohort_gap = round(target_score["mastery_score"] - cohort_target_mastery, 4)

        return StudentReadiness(
            status=status,
            readiness_score=readiness_score,
            target_mastery=round(target_score["mastery_score"], 4),
            cohort_mastery=cohort_target_mastery,
            cohort_gap=cohort_gap,
            latest_assessment_date=assessment_summary.get("latest_assessment_date"),
            assessments_considered=assessment_summary.get("assessment_count", 0),
        )

    def _build_remediation_order(self, weak_concepts: list[WeakConcept]) -> list[RemediationStep]:
        remediation = []
        for index, concept in enumerate(sorted(weak_concepts, key=lambda item: (item.depth, item.mastery_score)), start=1):
            remediation.append(
                RemediationStep(
                    order=index,
                    concept_id=concept.concept_id,
                    concept_name=concept.concept_name,
                    action=f"Reinforce {concept.concept_name.lower()} before revisiting downstream algebra tasks.",
                )
            )
        return remediation[:5]

    def _explanation_formatter(
        self,
        target_concept: dict,
        weak_concepts: list[WeakConcept],
        ranked_root_causes: list[RootCauseCandidate],
    ) -> str:
        if not ranked_root_causes:
            return f"No material prerequisite weakness was found for {target_concept['name']} in the latest available evidence."
        top = ranked_root_causes[0]
        related = ", ".join(concept.concept_name for concept in weak_concepts[:3])
        return (
            f"The strongest root-cause candidate for {target_concept['name']} is {top.concept_name}. "
            f"The diagnosis engine found weakness signals across {related}. "
            f"Intervention should begin with the earliest weak prerequisite and then move forward along the chain."
        )

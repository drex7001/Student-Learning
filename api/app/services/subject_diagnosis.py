from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from app.schemas.diagnosis import (
    ConceptSupportEdge,
    ConceptSupportNode,
    StudentSummary,
    SubjectDiagnosisMapResponse,
    SubjectNode,
    SubjectSupportSummary,
)


@dataclass
class SubjectDiagnosisEngine:
    default_mastery: float = 0.5
    default_confidence: float = 0.35

    def run(
        self,
        *,
        student: dict,
        subject: dict,
        concepts: list[dict],
        edges: list[dict],
        latest_scores: dict[str, dict],
    ) -> SubjectDiagnosisMapResponse:
        depths = self._concept_depths(concepts, edges)
        downstream_counts = self._downstream_counts(concepts, edges)
        max_downstream = max(downstream_counts.values() or [0])

        support_nodes = [
            self._build_node(
                concept=concept,
                score=latest_scores.get(concept["id"]),
                depth=depths.get(concept["id"], 0),
                downstream_impact=downstream_counts.get(concept["id"], 0),
                max_downstream=max_downstream,
            )
            for concept in concepts
        ]
        support_nodes.sort(key=lambda node: (node.depth, node.id))

        recommended = self._recommended_node(support_nodes)
        summary = SubjectSupportSummary(
            total_concepts=len(support_nodes),
            support_now=sum(1 for node in support_nodes if node.status == "support_now"),
            watch=sum(1 for node in support_nodes if node.status == "watch"),
            ready=sum(1 for node in support_nodes if node.status == "ready"),
            missing_evidence=sum(1 for node in support_nodes if node.status == "missing_evidence"),
        )
        explanation = self._explanation(recommended, summary, subject)

        return SubjectDiagnosisMapResponse(
            student=StudentSummary(**student),
            subject=SubjectNode(**subject),
            concepts=support_nodes,
            edges=[ConceptSupportEdge(**edge) for edge in edges],
            summary=summary,
            recommended_concept_id=recommended.id if recommended else None,
            explanation=explanation,
        )

    def _build_node(
        self,
        *,
        concept: dict,
        score: dict | None,
        depth: int,
        downstream_impact: int,
        max_downstream: int,
    ) -> ConceptSupportNode:
        has_score = score is not None
        mastery = score["mastery_score"] if score else self.default_mastery
        confidence = score["confidence"] if score else self.default_confidence

        if not has_score:
            status = "missing_evidence"
            evidence = "No recent assessment evidence for this concept."
            mastery_value = None
        elif mastery < 0.6:
            status = "support_now"
            evidence = "Observed mastery is below the support threshold."
            mastery_value = round(mastery, 4)
        elif mastery < 0.75:
            status = "watch"
            evidence = "Observed mastery is borderline."
            mastery_value = round(mastery, 4)
        else:
            status = "ready"
            evidence = "Observed mastery is at or above the readiness threshold."
            mastery_value = round(mastery, 4)

        downstream_weight = downstream_impact / max(1, max_downstream)
        priority_score = round(
            ((1 - mastery) * 0.5)
            + ((1 - confidence) * 0.15)
            + ((1 / (depth + 1)) * 0.2)
            + (downstream_weight * 0.15),
            4,
        )

        return ConceptSupportNode(
            id=concept["id"],
            subject_id=concept["subject_id"],
            name=concept["name"],
            name_si=concept.get("name_si"),
            description=concept.get("description"),
            description_si=concept.get("description_si"),
            mastery_score=mastery_value,
            confidence=round(confidence, 4),
            status=status,
            priority_score=priority_score,
            depth=depth,
            downstream_impact=downstream_impact,
            evidence=evidence,
        )

    def _recommended_node(self, nodes: list[ConceptSupportNode]) -> ConceptSupportNode | None:
        candidates = [node for node in nodes if node.status in {"support_now", "watch", "missing_evidence"}]
        if not candidates:
            return None
        observed = [node for node in candidates if node.status != "missing_evidence"]
        pool = observed or candidates
        return sorted(pool, key=lambda node: (-node.priority_score, node.depth, node.id))[0]

    def _concept_depths(self, concepts: list[dict], edges: list[dict]) -> dict[str, int]:
        concept_ids = {concept["id"] for concept in concepts}
        adjacency: dict[str, list[str]] = defaultdict(list)
        indegree = {concept_id: 0 for concept_id in concept_ids}

        for edge in edges:
            source = edge["source_id"]
            target = edge["target_id"]
            adjacency[source].append(target)
            indegree[target] += 1

        roots = [concept_id for concept_id, degree in indegree.items() if degree == 0]
        depths = {concept_id: 0 for concept_id in roots}
        queue = deque(roots)
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                next_depth = depths[current] + 1
                if neighbor not in depths or next_depth < depths[neighbor]:
                    depths[neighbor] = next_depth
                    queue.append(neighbor)

        for concept_id in concept_ids:
            depths.setdefault(concept_id, 0)
        return depths

    def _downstream_counts(self, concepts: list[dict], edges: list[dict]) -> dict[str, int]:
        concept_ids = {concept["id"] for concept in concepts}
        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            adjacency[edge["source_id"]].append(edge["target_id"])

        counts: dict[str, int] = {}
        for concept_id in concept_ids:
            seen: set[str] = set()
            queue = deque(adjacency[concept_id])
            while queue:
                current = queue.popleft()
                if current in seen:
                    continue
                seen.add(current)
                queue.extend(adjacency[current])
            counts[concept_id] = len(seen)
        return counts

    def _explanation(
        self,
        recommended: ConceptSupportNode | None,
        summary: SubjectSupportSummary,
        subject: dict,
    ) -> str:
        if recommended is None:
            return f"No immediate support need was detected across {subject['name']} concepts."
        return (
            f"Start with {recommended.name}. "
            f"This concept has {recommended.status.replace('_', ' ')} status, "
            f"priority {recommended.priority_score:.2f}, and affects {recommended.downstream_impact} downstream concepts. "
            f"{summary.support_now} concept(s) need support now and {summary.watch} concept(s) should be watched."
        )

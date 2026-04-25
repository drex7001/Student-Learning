from __future__ import annotations

import json
from pathlib import Path


class CurriculumValidationError(ValueError):
    pass


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_curriculum(curriculum: dict) -> dict:
    subjects = curriculum.get("subjects", [])
    concepts = curriculum["concepts"]
    edges = [tuple(edge) for edge in curriculum["edges"]]
    concept_ids = {concept["id"] for concept in concepts}
    subject_ids = {subject["id"] for subject in subjects}

    if not subjects:
        raise CurriculumValidationError("Curriculum must contain at least one subject.")

    for concept in concepts:
        if concept.get("subject_id") not in subject_ids:
            raise CurriculumValidationError(f"Concept has unknown subject reference: {concept['id']}")

    concepts_by_subject: dict[str, list[dict]] = {subject_id: [] for subject_id in subject_ids}
    for concept in concepts:
        concepts_by_subject[concept["subject_id"]].append(concept)

    for subject_id, subject_concepts in concepts_by_subject.items():
        if not 8 <= len(subject_concepts) <= 30:
            raise CurriculumValidationError(
                f"Subject {subject_id} must contain between 8 and 30 concepts."
            )

    for source, target in edges:
        if source not in concept_ids or target not in concept_ids:
            raise CurriculumValidationError(f"Edge contains unknown concept reference: {source} -> {target}")
        source_subject = next(concept["subject_id"] for concept in concepts if concept["id"] == source)
        target_subject = next(concept["subject_id"] for concept in concepts if concept["id"] == target)
        if source_subject != target_subject:
            raise CurriculumValidationError(f"Edge crosses subjects: {source} -> {target}")

    concept_subjects = {concept["id"]: concept["subject_id"] for concept in concepts}
    for subject_id, subject_concepts in concepts_by_subject.items():
        subject_concept_ids = {concept["id"] for concept in subject_concepts}
        adjacency = {concept_id: [] for concept_id in subject_concept_ids}
        indegree = {concept_id: 0 for concept_id in subject_concept_ids}
        for source, target in edges:
            if concept_subjects[source] != subject_id:
                continue
            adjacency[source].append(target)
            indegree[target] += 1

        queue = [concept_id for concept_id, degree in indegree.items() if degree == 0]
        visited = 0
        while queue:
            current = queue.pop(0)
            visited += 1
            for neighbor in adjacency[current]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(subject_concepts):
            raise CurriculumValidationError(f"Curriculum graph for {subject_id} must be acyclic.")

    return {"subject_count": len(subjects), "concept_count": len(concepts), "edge_count": len(edges)}

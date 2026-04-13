from __future__ import annotations

import json
from pathlib import Path


class CurriculumValidationError(ValueError):
    pass


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_curriculum(curriculum: dict) -> dict:
    concepts = curriculum["concepts"]
    edges = [tuple(edge) for edge in curriculum["edges"]]
    concept_ids = {concept["id"] for concept in concepts}

    if not 20 <= len(concepts) <= 30:
        raise CurriculumValidationError("Curriculum must contain between 20 and 30 concepts.")

    for source, target in edges:
        if source not in concept_ids or target not in concept_ids:
            raise CurriculumValidationError(f"Edge contains unknown concept reference: {source} -> {target}")

    adjacency = {concept_id: [] for concept_id in concept_ids}
    indegree = {concept_id: 0 for concept_id in concept_ids}
    for source, target in edges:
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

    if visited != len(concepts):
        raise CurriculumValidationError("Curriculum graph must be acyclic.")

    return {"concept_count": len(concepts), "edge_count": len(edges)}

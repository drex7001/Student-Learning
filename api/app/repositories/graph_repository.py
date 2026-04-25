from __future__ import annotations

from typing import Iterable

from neo4j import GraphDatabase

from app.core.config import settings


class GraphRepository:
    def __init__(self, uri: str | None = None, username: str | None = None, password: str | None = None):
        self.driver = GraphDatabase.driver(
            uri or settings.neo4j_uri,
            auth=(username or settings.neo4j_username, password or settings.neo4j_password),
        )

    def close(self) -> None:
        self.driver.close()

    def import_curriculum(self, subjects: Iterable[dict], concepts: Iterable[dict], edges: Iterable[tuple[str, str]]) -> dict:
        subjects_payload = list(subjects)
        concepts_payload = list(concepts)
        edges_payload = [{"source": source, "target": target} for source, target in edges]
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE")
            session.run("MATCH (c:Concept) DETACH DELETE c")
            session.run("MATCH (s:Subject) DETACH DELETE s")
            session.run("CREATE CONSTRAINT subject_id IF NOT EXISTS FOR (s:Subject) REQUIRE s.id IS UNIQUE")
            session.run(
                """
                UNWIND $subjects AS subject
                MERGE (s:Subject {id: subject.id})
                SET s.name = subject.name,
                    s.name_si = subject.name_si,
                    s.description = subject.description,
                    s.description_si = subject.description_si,
                    s.default_concept_id = subject.default_concept_id
                """,
                subjects=subjects_payload,
            )
            session.run(
                """
                UNWIND $concepts AS concept
                MERGE (c:Concept {id: concept.id})
                SET c.name = concept.name,
                    c.name_si = concept.name_si,
                    c.description = concept.description,
                    c.description_si = concept.description_si,
                    c.subject_id = concept.subject_id
                """,
                concepts=concepts_payload,
            )
            session.run(
                """
                MATCH (c:Concept)
                MATCH (s:Subject {id: c.subject_id})
                MERGE (c)-[:IN_SUBJECT]->(s)
                """
            )
            session.run(
                """
                UNWIND $edges AS edge
                MATCH (source:Concept {id: edge.source})
                MATCH (target:Concept {id: edge.target})
                MERGE (source)-[:REQUIRED_FOR]->(target)
                """,
                edges=edges_payload,
            )
            subject_count = session.run("MATCH (s:Subject) RETURN count(s) AS count").single()["count"]
            concept_count = session.run("MATCH (c:Concept) RETURN count(c) AS count").single()["count"]
            edge_count = session.run("MATCH ()-[r:REQUIRED_FOR]->() RETURN count(r) AS count").single()["count"]
        return {"subject_count": subject_count, "concept_count": concept_count, "edge_count": edge_count}

    def list_subjects(self) -> list[dict]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (s:Subject)
                RETURN s.id AS id,
                       s.name AS name,
                       s.name_si AS name_si,
                       s.description AS description,
                       s.description_si AS description_si,
                       s.default_concept_id AS default_concept_id
                ORDER BY s.id
                """
            ).data()
        return records

    def get_subject(self, subject_id: str) -> dict | None:
        with self.driver.session() as session:
            record = session.run(
                """
                MATCH (s:Subject {id: $subject_id})
                RETURN s.id AS id,
                       s.name AS name,
                       s.name_si AS name_si,
                       s.description AS description,
                       s.description_si AS description_si,
                       s.default_concept_id AS default_concept_id
                """,
                subject_id=subject_id,
            ).single()
        return dict(record) if record else None

    def get_concept(self, concept_id: str) -> dict | None:
        with self.driver.session() as session:
            record = session.run(
                """
                MATCH (c:Concept {id: $concept_id})
                RETURN c.id AS id,
                       c.subject_id AS subject_id,
                       c.name AS name,
                       c.name_si AS name_si,
                       c.description AS description,
                       c.description_si AS description_si
                """,
                concept_id=concept_id,
            ).single()
        return dict(record) if record else None

    def list_concepts(self, subject_id: str | None = None) -> list[dict]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (c:Concept)
                WHERE $subject_id IS NULL OR c.subject_id = $subject_id
                RETURN c.id AS id,
                       c.subject_id AS subject_id,
                       c.name AS name,
                       c.name_si AS name_si,
                       c.description AS description,
                       c.description_si AS description_si
                ORDER BY c.id
                """,
                subject_id=subject_id,
            ).data()
        return records

    def get_prerequisite_paths(self, concept_id: str) -> list[list[dict]]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH path = (root:Concept)-[:REQUIRED_FOR*0..]->(target:Concept {id: $concept_id})
                WHERE NOT EXISTS { MATCH (:Concept)-[:REQUIRED_FOR]->(root) }
                RETURN [node IN nodes(path) | {
                    id: node.id,
                    subject_id: node.subject_id,
                    name: node.name,
                    name_si: node.name_si,
                    description: node.description,
                    description_si: node.description_si
                }] AS nodes
                ORDER BY size(nodes(path)) ASC
                """,
                concept_id=concept_id,
            ).data()
        return [record["nodes"] for record in records]

    def get_downstream_concepts(self, concept_id: str) -> list[dict]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (source:Concept {id: $concept_id})-[:REQUIRED_FOR*1..]->(downstream:Concept)
                RETURN DISTINCT downstream.id AS id,
                       downstream.subject_id AS subject_id,
                       downstream.name AS name,
                       downstream.name_si AS name_si,
                       downstream.description AS description,
                       downstream.description_si AS description_si
                ORDER BY downstream.id
                """,
                concept_id=concept_id,
            ).data()
        return records

    def get_subject_edges(self, subject_id: str) -> list[dict]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (source:Concept {subject_id: $subject_id})-[:REQUIRED_FOR]->(target:Concept {subject_id: $subject_id})
                RETURN source.id AS source_id,
                       target.id AS target_id
                ORDER BY source.id, target.id
                """,
                subject_id=subject_id,
            ).data()
        return records

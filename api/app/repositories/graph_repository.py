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

    def import_curriculum(self, concepts: Iterable[dict], edges: Iterable[tuple[str, str]]) -> dict:
        concepts_payload = list(concepts)
        edges_payload = [{"source": source, "target": target} for source, target in edges]
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE")
            session.run(
                """
                UNWIND $concepts AS concept
                MERGE (c:Concept {id: concept.id})
                SET c.name = concept.name,
                    c.description = concept.description
                """,
                concepts=concepts_payload,
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
            concept_count = session.run("MATCH (c:Concept) RETURN count(c) AS count").single()["count"]
            edge_count = session.run("MATCH ()-[r:REQUIRED_FOR]->() RETURN count(r) AS count").single()["count"]
        return {"concept_count": concept_count, "edge_count": edge_count}

    def get_concept(self, concept_id: str) -> dict | None:
        with self.driver.session() as session:
            record = session.run(
                "MATCH (c:Concept {id: $concept_id}) RETURN c.id AS id, c.name AS name, c.description AS description",
                concept_id=concept_id,
            ).single()
        return dict(record) if record else None

    def list_concepts(self) -> list[dict]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (c:Concept)
                RETURN c.id AS id, c.name AS name, c.description AS description
                ORDER BY c.id
                """
            ).data()
        return records

    def get_prerequisite_paths(self, concept_id: str) -> list[list[dict]]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH path = (root:Concept)-[:REQUIRED_FOR*0..]->(target:Concept {id: $concept_id})
                WHERE NOT EXISTS { MATCH (:Concept)-[:REQUIRED_FOR]->(root) }
                RETURN [node IN nodes(path) | {id: node.id, name: node.name, description: node.description}] AS nodes
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
                RETURN DISTINCT downstream.id AS id, downstream.name AS name, downstream.description AS description
                ORDER BY downstream.id
                """,
                concept_id=concept_id,
            ).data()
        return records

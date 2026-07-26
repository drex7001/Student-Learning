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

    # ------------------------------------------------------------------
    # Risk model: the causal DAG as a property graph
    # ------------------------------------------------------------------

    def import_risk_model(self, factors: list[dict], edges: list[dict]) -> dict:
        """Load the 25 risk factors and their causal edges into Neo4j.

        Putting the DAG in the graph is what turns "why was this student flagged?" into
        a traversal. Each edge carries the mechanism, evidence level and fairness note
        from the edge-justification table, so a path reads as a sentence rather than a
        chain of identifiers.
        """
        with self.driver.session() as session:
            session.run(
                "CREATE CONSTRAINT risk_factor_id IF NOT EXISTS "
                "FOR (f:RiskFactor) REQUIRE f.id IS UNIQUE"
            )
            session.run("MATCH (f:RiskFactor) DETACH DELETE f")
            session.run(
                """
                UNWIND $factors AS factor
                MERGE (f:RiskFactor {id: factor.id})
                SET f.label = factor.label,
                    f.label_si = factor.label_si,
                    f.group = factor.group,
                    f.group_si = factor.group_si,
                    f.states = factor.states,
                    f.state_labels = factor.state_labels,
                    f.state_labels_si = factor.state_labels_si,
                    f.modifiable = factor.modifiable,
                    f.protected = factor.protected,
                    f.register = factor.register,
                    f.is_outcome = factor.is_outcome
                """,
                factors=factors,
            )
            session.run(
                """
                UNWIND $edges AS edge
                MATCH (source:RiskFactor {id: edge.source})
                MATCH (target:RiskFactor {id: edge.target})
                MERGE (source)-[r:INFLUENCES]->(target)
                SET r.evidence = edge.evidence,
                    r.mechanism = edge.mechanism,
                    r.confounders = edge.confounders,
                    r.concern = edge.concern,
                    r.amendment = edge.amendment
                """,
                edges=edges,
            )
            factor_count = session.run(
                "MATCH (f:RiskFactor) RETURN count(f) AS count"
            ).single()["count"]
            influence_count = session.run(
                "MATCH ()-[r:INFLUENCES]->() RETURN count(r) AS count"
            ).single()["count"]
        return {"factor_count": factor_count, "influence_count": influence_count}

    def get_causal_paths(self, variable: str, target: str) -> list[dict]:
        """Every directed route from a factor to the outcome, shortest first."""
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH path = (f:RiskFactor {id: $variable})-[:INFLUENCES*1..6]->(t:RiskFactor {id: $target})
                RETURN [n IN nodes(path) | {id: n.id, label: n.label, label_si: n.label_si,
                                            modifiable: n.modifiable, protected: n.protected}] AS nodes,
                       [r IN relationships(path) | {evidence: r.evidence, mechanism: r.mechanism}] AS steps,
                       length(path) AS length
                ORDER BY length ASC
                """,
                variable=variable,
                target=target,
            ).data()
        return records

    # ------------------------------------------------------------------
    # Projection: people, classes and evidence
    # ------------------------------------------------------------------

    def project_school_graph(
        self,
        *,
        schools: list[dict],
        classes: list[dict],
        teachers: list[dict],
        students: list[dict],
        mastery: list[dict],
        evidence: list[dict],
        peers: list[dict],
        risk: list[dict],
    ) -> dict:
        """Project the relational roster into the graph.

        PostgreSQL stays the system of record. This is a read-optimised view that lets
        one query cross the boundaries the relational schema keeps apart -- a learner,
        their class, their subjects, their weak concepts, their risk factors and their
        peers, in a single traversal.
        """
        with self.driver.session() as session:
            for label in ("School", "Class", "Teacher", "Student"):
                session.run(
                    f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )
            for label in ("Student", "Class", "Teacher", "School"):
                session.run(f"MATCH (n:{label}) DETACH DELETE n")

            session.run(
                """
                UNWIND $schools AS s
                MERGE (n:School {id: s.id})
                SET n.name = s.name, n.name_si = s.name_si, n.district = s.district,
                    n.province = s.province, n.sector = s.sector, n.medium = s.medium_primary
                """,
                schools=schools,
            )
            session.run(
                """
                UNWIND $classes AS c
                MERGE (n:Class {id: c.id})
                SET n.grade = c.grade, n.section = c.section, n.label = c.label, n.medium = c.medium
                WITH n, c
                MATCH (s:School {id: c.school_id})
                MERGE (n)-[:AT_SCHOOL]->(s)
                """,
                classes=classes,
            )
            session.run(
                """
                UNWIND $teachers AS t
                MERGE (n:Teacher {id: t.id})
                SET n.name = t.full_name, n.name_si = t.full_name_si, n.role_title = t.role_title
                WITH n, t
                MATCH (s:School {id: t.school_id})
                MERGE (n)-[:AT_SCHOOL]->(s)
                """,
                teachers=teachers,
            )
            session.run(
                """
                UNWIND $classes AS c
                WITH c WHERE c.class_teacher_id IS NOT NULL
                MATCH (t:Teacher {id: c.class_teacher_id})
                MATCH (n:Class {id: c.id})
                MERGE (t)-[:TEACHES_CLASS]->(n)
                """,
                classes=classes,
            )
            session.run(
                """
                UNWIND $students AS s
                MERGE (n:Student {id: s.id})
                SET n.name = s.full_name, n.name_si = s.full_name_si, n.cohort = s.cohort,
                    n.grade = s.grade, n.medium = s.medium, n.gender = s.gender
                WITH n, s
                MATCH (c:Class {id: s.class_id})
                MERGE (n)-[:IN_CLASS]->(c)
                """,
                students=students,
            )
            session.run(
                """
                MATCH (st:Student)
                MATCH (sub:Subject)
                MERGE (st)-[:STUDIES]->(sub)
                """
            )
            session.run(
                """
                UNWIND $mastery AS m
                MATCH (s:Student {id: m.student_id})
                MATCH (c:Concept {id: m.concept_id})
                MERGE (s)-[r:HAS_MASTERY]->(c)
                SET r.score = m.score, r.band = m.band
                """,
                mastery=mastery,
            )
            session.run(
                """
                UNWIND $evidence AS e
                MATCH (s:Student {id: e.student_id})
                MATCH (f:RiskFactor {id: e.variable})
                MERGE (s)-[r:HAS_EVIDENCE]->(f)
                SET r.state = e.state, r.state_label = e.state_label,
                    r.concern = e.concern, r.source = e.source
                """,
                evidence=evidence,
            )
            session.run(
                """
                UNWIND $peers AS p
                MATCH (a:Student {id: p.source})
                MATCH (b:Student {id: p.target})
                MERGE (a)-[:FRIENDS_WITH]->(b)
                """,
                peers=peers,
            )
            session.run(
                """
                UNWIND $risk AS r
                MATCH (s:Student {id: r.student_id})
                SET s.p_high = r.p_high, s.risk_band = r.band, s.circumstance_gap = r.gap
                """,
                risk=risk,
            )

            counts = session.run(
                """
                MATCH (s:School) WITH count(s) AS schools
                MATCH (c:Class) WITH schools, count(c) AS classes
                MATCH (t:Teacher) WITH schools, classes, count(t) AS teachers
                MATCH (st:Student) WITH schools, classes, teachers, count(st) AS students
                OPTIONAL MATCH ()-[m:HAS_MASTERY]->()
                WITH schools, classes, teachers, students, count(m) AS mastery
                OPTIONAL MATCH ()-[e:HAS_EVIDENCE]->()
                WITH schools, classes, teachers, students, mastery, count(e) AS evidence
                OPTIONAL MATCH ()-[p:FRIENDS_WITH]->()
                RETURN schools, classes, teachers, students, mastery, evidence, count(p) AS peers
                """
            ).single()
        return {
            "school_count": counts["schools"],
            "class_count": counts["classes"],
            "teacher_count": counts["teachers"],
            "student_count": counts["students"],
            "mastery_edge_count": counts["mastery"],
            "evidence_edge_count": counts["evidence"],
            "peer_edge_count": counts["peers"],
        }

    # ------------------------------------------------------------------
    # Graph analytics
    # ------------------------------------------------------------------

    def get_student_neighbourhood(self, student_id: str) -> dict:
        """One learner's ego network: class, school, weak concepts, concern factors."""
        with self.driver.session() as session:
            record = session.run(
                """
                MATCH (s:Student {id: $student_id})
                OPTIONAL MATCH (s)-[:IN_CLASS]->(c:Class)-[:AT_SCHOOL]->(sc:School)
                OPTIONAL MATCH (t:Teacher)-[:TEACHES_CLASS]->(c)
                OPTIONAL MATCH (s)-[m:HAS_MASTERY]->(concept:Concept)
                    WHERE m.band IN ['weak', 'borderline']
                OPTIONAL MATCH (s)-[e:HAS_EVIDENCE]->(f:RiskFactor) WHERE e.concern = true
                OPTIONAL MATCH (s)-[:FRIENDS_WITH]-(peer:Student)
                RETURN s {.id, .name, .name_si, .cohort, .grade, .p_high, .risk_band} AS student,
                       c {.id, .label, .grade, .medium} AS class,
                       sc {.id, .name, .sector, .district} AS school,
                       collect(DISTINCT t {.id, .name, .role_title}) AS teachers,
                       collect(DISTINCT concept {.id, .name, .name_si, .subject_id,
                                                 score: m.score, band: m.band}) AS weak_concepts,
                       collect(DISTINCT f {.id, .label, .label_si, .group, .modifiable,
                                           state: e.state, state_label: e.state_label}) AS concern_factors,
                       collect(DISTINCT peer {.id, .name, .risk_band}) AS peers
                """,
                student_id=student_id,
            ).single()
        return dict(record) if record else {}

    def get_shared_factors(
        self, school_id: str | None = None, class_id: str | None = None
    ) -> list[dict]:
        """Concerns that many learners share.

        The point of this query: a factor half a school shares is a condition of that
        school, not a property of those children.
        """
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (s:Student)-[e:HAS_EVIDENCE]->(f:RiskFactor)
                WHERE e.concern = true
                  AND ($school_id IS NULL OR EXISTS {
                        MATCH (s)-[:IN_CLASS]->(:Class)-[:AT_SCHOOL]->(:School {id: $school_id}) })
                  AND ($class_id IS NULL OR EXISTS {
                        MATCH (s)-[:IN_CLASS]->(:Class {id: $class_id}) })
                WITH f, e.state_label AS state_label, count(DISTINCT s) AS affected
                RETURN f.id AS variable, f.label AS label, f.label_si AS label_si,
                       f.group AS grouping, f.modifiable AS modifiable,
                       state_label AS state_label, affected
                ORDER BY affected DESC, label ASC
                """,
                school_id=school_id,
                class_id=class_id,
            ).data()
        return records

    def get_peer_network(self, class_id: str) -> dict:
        """Peer ties within a class, with tie counts.

        Few ties is the signal the proposal's peer-isolation objective asks for. It is
        a prompt to look, never a finding about a child's social life.
        """
        with self.driver.session() as session:
            nodes = session.run(
                """
                MATCH (s:Student)-[:IN_CLASS]->(:Class {id: $class_id})
                OPTIONAL MATCH (s)-[:FRIENDS_WITH]-(peer:Student)-[:IN_CLASS]->(:Class {id: $class_id})
                RETURN s.id AS id, s.name AS name, s.risk_band AS risk_band,
                       s.p_high AS p_high, count(DISTINCT peer) AS ties
                ORDER BY ties ASC, name ASC
                """,
                class_id=class_id,
            ).data()
            edges = session.run(
                """
                MATCH (a:Student)-[:IN_CLASS]->(:Class {id: $class_id})
                MATCH (a)-[:FRIENDS_WITH]->(b:Student)-[:IN_CLASS]->(:Class {id: $class_id})
                RETURN a.id AS source, b.id AS target
                """,
                class_id=class_id,
            ).data()
        return {"nodes": nodes, "edges": edges}

    def get_concept_root_causes(self, student_id: str, limit: int = 6) -> list[dict]:
        """Weak concepts joined to their prerequisite chain in one traversal.

        Relationally this needs the concept graph and the score table together; in the
        property graph it is a single path query.
        """
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (s:Student {id: $student_id})-[m:HAS_MASTERY]->(c:Concept)
                WHERE m.band = 'weak'
                MATCH path = (root:Concept)-[:REQUIRED_FOR*0..]->(c)
                WHERE NOT EXISTS { MATCH (:Concept)-[:REQUIRED_FOR]->(root) }
                WITH c, m, root, length(path) AS depth
                ORDER BY depth ASC
                WITH c, m, collect({id: root.id, name: root.name})[0] AS earliest, min(depth) AS depth
                RETURN c.id AS concept_id, c.name AS concept_name, c.subject_id AS subject_id,
                       m.score AS score, earliest AS root_concept, depth
                ORDER BY m.score ASC
                LIMIT $limit
                """,
                student_id=student_id,
                limit=limit,
            ).data()
        return records

# Architecture

The system is a teacher-facing Sri Lankan O/L learning intelligence prototype. It combines prerequisite graph traversal with synthetic assessment evidence to identify likely root-cause learning gaps.

## Components

- `web`: Next.js 16 application with the teacher dashboard, support queue, student diagnosis, and concept map.
- `api`: FastAPI service for curriculum import, synthetic data generation, graph lookup, support queues, and diagnosis.
- PostgreSQL: stores students, assessments, questions, question results, and computed concept scores.
- Neo4j: stores O/L subjects, concepts, and `REQUIRED_FOR` prerequisite relationships.
- `data`: stores the prototype curriculum bundle and synthetic data generator configuration.

## Data Flow

1. `POST /internal/import/curriculum` reads `data/curriculum/ol_subject_curriculum.json`.
2. The API validates each subject graph and writes subjects/concepts/edges into Neo4j.
3. `POST /internal/generate/synthetic-data` reads the same curriculum and `data/seeds/generator_config.json`.
4. Synthetic students, assessments, question results, and concept scores are written into PostgreSQL.
5. Frontend workflows request subject-filtered concepts through `GET /api/options?subject_id=...`.
6. The student diagnosis page requests a subject-wide support map, then loads detailed diagnosis for the selected concept.

## Main API Surface

Internal setup endpoints:

- `POST /internal/import/curriculum`
- `POST /internal/generate/synthetic-data`

Teacher workflow endpoints:

- `GET /api/subjects`
- `GET /api/options?subject_id=OL-MATH`
- `GET /api/overview/concept/{concept_id}`
- `GET /api/diagnosis/student/{student_id}/subject/{subject_id}/map`
- `GET /api/concepts/{concept_id}/prerequisites`
- `GET /api/diagnosis/student/{student_id}/concept/{concept_id}`

## Frontend Workflows

Dashboard:

- Entry point at `/`.
- Selects an O/L subject and concept.
- Shows support summary counts.
- Links to support queue, diagnosis, and concept map with query parameters.

Support Queue:

- Route: `/students?subject=OL-MATH&concept=MATH-010`
- Ranks learners by readiness for the selected concept.
- Opens individual diagnosis for a learner.

Student Diagnosis:

- Route: `/diagnosis?subject=OL-ENG&student=STU-001&concept=ENG-010`
- Shows every concept in the selected subject as a support map for the learner.
- Opens detailed root-cause diagnosis, trends, and remediation order when a concept node is selected.

Concept Map:

- Route: `/concepts?subject=OL-SCI&concept=SCI-010`
- Shows upstream prerequisite paths and downstream dependent concepts.

## Diagnosis Logic

The diagnosis engine is deterministic. It does not run probabilistic graph inference.

Inputs:

- selected student
- target concept
- prerequisite paths from Neo4j
- latest and recent concept scores from PostgreSQL
- cohort mastery for comparison

Outputs:

- readiness status
- weak prerequisite concepts
- root-cause candidates
- concept trends
- remediation order
- teacher-facing explanation

Thresholds:

- strong: `>= 0.75`
- borderline: `0.60-0.74`
- weak: `< 0.60`

## Storage Notes

Concept IDs are globally unique across subjects. This lets PostgreSQL keep `concept_id` as a simple string without an extra subject column on concept score rows.

Neo4j stores:

- `(:Subject {id, name, name_si, description, description_si, default_concept_id})`
- `(:Concept {id, subject_id, name, name_si, description, description_si})`
- `(source:Concept)-[:REQUIRED_FOR]->(target:Concept)`
- `(concept:Concept)-[:IN_SUBJECT]->(subject:Subject)`

PostgreSQL stores synthetic assessment evidence only. It does not store curriculum metadata.

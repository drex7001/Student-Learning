# Curriculum And Seeding

The current curriculum is prototype-aligned Sri Lankan O/L data, not a claim of official syllabus completeness.

## Supported V1 Subjects

- `OL-MATH`: Mathematics
- `OL-SCI`: Science
- `OL-ENG`: English
- `OL-ICT`: ICT

Each subject has English and Sinhala-ready display fields. The UI displays Sinhala where data exists and falls back to English when it does not.

## Curriculum File

Primary file:

```text
data/curriculum/ol_subject_curriculum.json
```

Top-level shape:

```json
{
  "scope": {},
  "subjects": [],
  "concepts": [],
  "edges": []
}
```

Subject fields:

- `id`: stable identifier such as `OL-MATH`
- `name`: English display name
- `name_si`: Sinhala display name
- `description`: English description
- `description_si`: Sinhala description
- `default_concept_id`: default concept when opening a subject workflow

Concept fields:

- `id`: globally unique concept identifier such as `MATH-010`
- `subject_id`: owning subject
- `name`
- `name_si`
- `description`
- `description_si`

Edges:

- Each edge is `[source_concept_id, target_concept_id]`.
- The meaning is `source REQUIRED_FOR target`.
- Cross-subject edges are rejected.

## Validation Rules

`api/app/services/curriculum_service.py` validates that:

- at least one subject exists
- every concept references a known subject
- each subject has 8 to 30 concepts
- every edge references known concepts
- every edge stays inside one subject
- each subject graph is acyclic

## Synthetic Data

Synthetic generation is configured by:

```text
data/seeds/generator_config.json
```

Important fields:

- `seed`: deterministic random seed
- `student_count`: generated student count
- `assessment_attempts`: number of assessment dates per student
- `cohorts`: class labels
- `weakness_profiles`: root concept gaps used to create realistic downstream weakness

The generator creates one question per concept. For each student and assessment attempt, it creates:

- one assessment row
- one question result per concept
- one concept score per concept

Weakness propagates from each profile root concept to its descendants. This makes prerequisite diagnosis meaningful across all subjects.

## Adding A Subject

1. Add a subject entry to `subjects`.
2. Add 8 to 30 concept entries with the new `subject_id`.
3. Add prerequisite edges that stay within the subject.
4. Add at least one weakness profile root concept in `data/seeds/generator_config.json`.
5. Run backend tests.
6. Import curriculum and regenerate synthetic data.

Recommended commands:

```powershell
cd api
$env:PYTHONPATH='.'
pytest
cd ..
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/import/curriculum
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/generate/synthetic-data -ContentType 'application/json' -Body '{}'
```

## Editing Existing Concepts

Safe changes:

- display names
- descriptions
- Sinhala fields
- default concept for a subject

Riskier changes:

- changing concept IDs, because synthetic profiles and URLs may reference them
- changing edges, because diagnosis paths and root-cause rankings change
- removing concepts, because generated data and tests may need updates

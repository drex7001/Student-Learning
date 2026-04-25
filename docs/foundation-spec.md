# Foundation Specification

## Locked Scope

- Level: Sri Lankan G.C.E. Ordinary Level prototype
- Subject slice: Mathematics, Science, English, and ICT
- Concept count target: 8-30 concepts per subject
- Current concept count: 40 across 4 subjects

## Scoring Model

- Each question is mapped to exactly one primary concept.
- A concept score is the weighted mean of mapped question percentages for a given student and assessment.
- Question percentage is `score_obtained / score_max`.
- Latest concept mastery for diagnosis is the most recent concept score per concept.
- Mastery score is normalized to the `0.0-1.0` range.

## Thresholds

- Strong: `>= 0.75`
- Borderline: `0.60-0.74`
- Weak: `< 0.60`
- Root-cause severity favors earlier prerequisite nodes and lower mastery scores.

## Confidence Rule

- Base confidence is the proportion of mapped questions answered for the concept in the latest available assessment.
- Missing concept observations default to confidence `0.35`.
- Confidence is capped at `0.95` to avoid overstating certainty in synthetic data.

## Exclusions

- No claim of official syllabus completeness.
- No cross-subject prerequisite edges in this milestone.
- No adaptive testing logic.
- No live school SIS integration.
- No student-facing intervention personalization in this milestone.
- No probabilistic graph inference beyond deterministic traversal and ranking.

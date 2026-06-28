# Student Help Support-Risk Feature

## Goal

Add a teacher-facing Student Help section that answers three questions:

1. Which learners need academic support first?
2. Why were they flagged?
3. What should the teacher do next?

This feature intentionally avoids medical or psychological diagnosis language. The first version focuses on academic support risk using existing learning evidence.

## Current Build Slice

This branch adds:

- `GET /api/support/subjects/{subject_id}/students`
- `GET /api/support/students/{student_id}/subjects/{subject_id}`
- `/support` frontend route
- Student Help navigation link
- Risk summary cards, ranked student list, selected learner explanation panel, and recommended actions

## Evidence Used

The baseline uses data already available in the project:

- latest concept mastery scores
- concept score confidence
- recent concept score movement
- weak/borderline/strong concept counts
- cohort mastery gap
- prerequisite/root-cause weakness derived from the subject graph
- assessment count

## Model Boundary

The current engine is a deterministic baseline with additive feature attribution. It is intentionally shaped like a SHAP response so the UI and API can remain stable when a trained ML model and real SHAP explainer are added later.

Current explanation method:

```text
additive_feature_attribution_baseline_shap_ready
```

Next step:

- add a training script that creates a support-risk dataset from concept evidence
- train a simple classifier/regressor
- save the model artifact
- replace the deterministic attribution with SHAP values from the trained model

## Risk Bands

- `high_support`: teacher should act soon
- `watch`: learner needs monitoring or a quick check-in
- `stable`: no urgent support action needed

## Research Framing

Use this framing in the proposal/report:

> An explainable academic support-risk dashboard that helps teachers prioritize learners using concept mastery, prerequisite weakness, confidence, trends, and cohort comparison.

Avoid this framing:

> AI detects student mental distress.

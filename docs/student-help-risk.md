# Student Help Support-Risk Feature

## Goal

Add a teacher-facing Student Help section that answers three questions:

1. Which learners need academic support first?
2. Why were they flagged?
3. What should the teacher do next?

This feature intentionally avoids medical or psychological diagnosis language. It focuses on academic support risk using existing learning evidence.

## Current Build Slice

The app now has:

- `GET /api/support/subjects/{subject_id}/students`
- `GET /api/support/students/{student_id}/subjects/{subject_id}`
- `/support` frontend route
- Student Help navigation link
- Risk summary cards, ranked student list, selected learner explanation panel, and recommended actions
- `POST /internal/train/support-model` for training a Random Forest support model from the current synthetic evidence

## Evidence Used

The model uses data already available in the project:

- latest concept mastery scores
- concept score confidence
- recent concept score movement
- weak/borderline/strong concept counts
- cohort mastery gap
- prerequisite/root-cause weakness derived from the subject graph
- assessment count

## Training Flow

Run the normal seed flow first:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/import/curriculum
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/generate/synthetic-data -ContentType 'application/json' -Body '{}'
```

Then train the support model:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/train/support-model
```

This endpoint:

1. Builds one feature row per student per subject.
2. Generates initial synthetic labels using academic support rules.
3. Trains a `RandomForestClassifier`.
4. Writes the generated model artifact to `data/models/support_model.joblib`.
5. Writes evaluation metrics to `data/models/support_model_metrics.json`.

Generated model and metric files are ignored by Git because they are runtime artifacts.

## Explanation Method

Before training, the support API falls back to:

```text
additive_feature_attribution_baseline_shap_ready
```

After training, the support API uses:

```text
ml_random_forest_shap::student-support-rf-v1
```

The SHAP explanation targets pressure toward the `high_support` class so the teacher can see which factors increase or reduce academic support priority.

## Risk Bands

- `high_support`: teacher should act soon
- `watch`: learner needs monitoring or a quick check-in
- `stable`: no urgent support action needed

## Research Framing

Use this framing in the proposal/report:

> An explainable academic support-risk dashboard that helps teachers prioritize learners using concept mastery, prerequisite weakness, confidence, trends, and cohort comparison.

Avoid this framing:

> AI detects student mental distress.

## Research Limitation

The first trained model uses synthetic academic support labels, not real teacher-reviewed intervention labels. This is acceptable for a prototype only if the report clearly states the label source and treats the model as a decision-support prototype, not a validated school-risk instrument.

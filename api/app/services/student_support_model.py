from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from app.core.config import BASE_DIR
from app.schemas.student_support import RiskBand, SupportRiskFactor, SupportRiskFeatures

FEATURE_NAMES = [
    "avg_mastery",
    "weak_concept_count",
    "borderline_concept_count",
    "strong_concept_count",
    "missing_evidence_count",
    "avg_confidence",
    "low_confidence_count",
    "mastery_decline_count",
    "cohort_gap_avg",
    "root_cause_count",
    "concept_count",
    "assessment_count",
    "recent_accuracy",
]

RISK_CLASS_TO_BAND: dict[int, RiskBand] = {0: "stable", 1: "watch", 2: "high_support"}
RISK_BAND_TO_CLASS = {value: key for key, value in RISK_CLASS_TO_BAND.items()}

FEATURE_LABELS: dict[str, str] = {
    "avg_mastery": "Average mastery",
    "weak_concept_count": "Weak concepts",
    "borderline_concept_count": "Borderline concepts",
    "strong_concept_count": "Strong concepts",
    "missing_evidence_count": "Missing evidence",
    "avg_confidence": "Evidence confidence",
    "low_confidence_count": "Low-confidence concepts",
    "mastery_decline_count": "Recent decline",
    "cohort_gap_avg": "Cohort gap",
    "root_cause_count": "Weak prerequisites",
    "concept_count": "Concept coverage",
    "assessment_count": "Assessment count",
    "recent_accuracy": "Recent accuracy",
}

FEATURE_EXPLANATIONS: dict[str, str] = {
    "avg_mastery": "Shows the learner's average mastery across this subject.",
    "weak_concept_count": "Counts concepts below the weak threshold.",
    "borderline_concept_count": "Counts concepts that are close to the weak threshold.",
    "strong_concept_count": "Counts concepts with strong mastery evidence.",
    "missing_evidence_count": "Counts concepts without enough recent evidence.",
    "avg_confidence": "Shows how reliable the stored concept evidence is.",
    "low_confidence_count": "Counts concepts where the evidence confidence is weak.",
    "mastery_decline_count": "Counts concepts where recent mastery declined.",
    "cohort_gap_avg": "Compares the learner's mastery against the cohort average.",
    "root_cause_count": "Counts weak prerequisite concepts that can block later learning.",
    "concept_count": "Shows how many subject concepts were considered.",
    "assessment_count": "Shows how much assessment evidence exists for this learner.",
    "recent_accuracy": "Approximates the learner's recent subject performance.",
}

MODEL_FILENAME = "support_model.joblib"
METRICS_FILENAME = "support_model_metrics.json"
MODEL_VERSION = "student-support-rf-v1"
LABEL_STRATEGY = "synthetic_academic_support_rules_v1"
ARTIFACT_DIR = BASE_DIR / "data" / "models"


@dataclass(frozen=True)
class TrainingExample:
    student_id: str
    subject_id: str
    features: SupportRiskFeatures
    label: RiskBand


@dataclass(frozen=True)
class SupportModelPrediction:
    score: float
    band: RiskBand
    confidence: float
    factors: list[SupportRiskFactor]
    method: str


def support_model_path() -> Path:
    return ARTIFACT_DIR / MODEL_FILENAME


def support_metrics_path() -> Path:
    return ARTIFACT_DIR / METRICS_FILENAME


def feature_dict(features: SupportRiskFeatures) -> dict[str, float]:
    payload = features.model_dump()
    return {name: float(payload[name] if payload[name] is not None else 0.0) for name in FEATURE_NAMES}


def synthetic_support_label(features: SupportRiskFeatures) -> RiskBand:
    weak_ratio = features.weak_concept_count / max(features.concept_count, 1)
    root_ratio = features.root_cause_count / max(features.concept_count, 1)
    negative_gap = -(features.cohort_gap_avg or 0.0)

    if features.avg_mastery < 0.55 or weak_ratio >= 0.42 or features.weak_concept_count >= 5:
        return "high_support"
    if root_ratio >= 0.35 or negative_gap >= 0.18:
        return "high_support"
    if features.avg_mastery < 0.72 or weak_ratio >= 0.18 or features.borderline_concept_count >= 3:
        return "watch"
    if features.mastery_decline_count >= 2 or negative_gap >= 0.08:
        return "watch"
    return "stable"


def train_support_model(examples: list[TrainingExample]) -> dict[str, Any]:
    if len(examples) < 30:
        raise ValueError("At least 30 training examples are required.")

    import joblib
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [feature_dict(example.features) for example in examples]
    labels = [RISK_BAND_TO_CLASS[example.label] for example in examples]
    label_counts = {band: sum(1 for label in labels if label == class_id) for class_id, band in RISK_CLASS_TO_BAND.items()}
    if sum(1 for count in label_counts.values() if count > 0) < 2:
        raise ValueError("Training data must contain at least two support classes.")

    X = pd.DataFrame(rows, columns=FEATURE_NAMES)
    y = pd.Series(labels, name="support_class")
    can_stratify = all(count >= 2 for count in label_counts.values() if count > 0)

    if len(examples) >= 60:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.25,
            random_state=42,
            stratify=y if can_stratify else None,
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y

    model = RandomForestClassifier(
        n_estimators=240,
        max_depth=7,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metadata = {
        "model_version": MODEL_VERSION,
        "label_strategy": LABEL_STRATEGY,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_names": FEATURE_NAMES,
        "class_labels": RISK_CLASS_TO_BAND,
        "training_examples": len(examples),
        "test_examples": int(len(X_test)),
        "label_counts": label_counts,
    }
    joblib.dump({"model": model, "metadata": metadata}, support_model_path())

    metrics = {
        **metadata,
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "classification_report": classification_report(
            y_test,
            y_pred,
            labels=[0, 1, 2],
            target_names=[RISK_CLASS_TO_BAND[index] for index in [0, 1, 2]],
            zero_division=0,
            output_dict=True,
        ),
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=[0, 1, 2]).tolist(),
    }
    support_metrics_path().write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    SupportModelRegistry.clear_cache()
    return {
        "model_path": str(support_model_path()),
        "metrics_path": str(support_metrics_path()),
        "accuracy": metrics["accuracy"],
        "f1_macro": metrics["f1_macro"],
        "training_examples": len(examples),
        "label_counts": label_counts,
        "label_strategy": LABEL_STRATEGY,
        "model_version": MODEL_VERSION,
    }


class SupportModelRegistry:
    _cached_payload: dict[str, Any] | None = None
    _cached_mtime: float | None = None

    @classmethod
    def clear_cache(cls) -> None:
        cls._cached_payload = None
        cls._cached_mtime = None

    @classmethod
    def _load_payload(cls) -> dict[str, Any] | None:
        path = support_model_path()
        if not path.exists():
            return None
        mtime = path.stat().st_mtime
        if cls._cached_payload is not None and cls._cached_mtime == mtime:
            return cls._cached_payload
        import joblib

        payload = joblib.load(path)
        cls._cached_payload = payload
        cls._cached_mtime = mtime
        return payload

    @classmethod
    def predict(cls, features: SupportRiskFeatures) -> SupportModelPrediction | None:
        payload = cls._load_payload()
        if payload is None:
            return None

        import pandas as pd

        model = payload["model"]
        metadata = payload.get("metadata", {})
        X = pd.DataFrame([feature_dict(features)], columns=FEATURE_NAMES)
        probabilities = model.predict_proba(X)[0]
        by_class = {0: 0.0, 1: 0.0, 2: 0.0}
        for index, class_id in enumerate(model.classes_):
            by_class[int(class_id)] = float(probabilities[index])

        high_probability = by_class[2]
        watch_probability = by_class[1]
        stable_probability = by_class[0]
        score = round(min(max(high_probability + watch_probability * 0.5, 0.0), 1.0), 4)
        if high_probability >= 0.45 or score >= 0.65:
            band: RiskBand = "high_support"
            confidence = high_probability
        elif watch_probability >= 0.35 or score >= 0.38:
            band = "watch"
            confidence = watch_probability
        else:
            band = "stable"
            confidence = stable_probability

        factors = cls._shap_factors(model=model, X=X, features=features)
        if not factors:
            factors = cls._importance_factors(model=model, features=features)

        return SupportModelPrediction(
            score=score,
            band=band,
            confidence=round(min(max(float(confidence), 0.0), 0.95), 4),
            factors=factors,
            method=f"ml_random_forest_shap::{metadata.get('model_version', MODEL_VERSION)}",
        )

    @classmethod
    def _shap_factors(cls, *, model: Any, X: Any, features: SupportRiskFeatures) -> list[SupportRiskFactor]:
        try:
            import numpy as np
            import shap

            explainer = shap.TreeExplainer(model)
            raw_values = explainer.shap_values(X)
            values = cls._select_high_class_values(raw_values)
            if values is None:
                return []
            return cls._factors_from_values(values=np.asarray(values, dtype=float), features=features)
        except Exception:
            return []

    @classmethod
    def _select_high_class_values(cls, raw_values: Any) -> Any | None:
        if isinstance(raw_values, list):
            if len(raw_values) < 3:
                return None
            return raw_values[2][0]
        shape = getattr(raw_values, "shape", None)
        if shape is None:
            return None
        if len(shape) == 3:
            if shape[0] == 1 and shape[2] >= 3:
                return raw_values[0, :, 2]
            if shape[1] >= 3:
                return raw_values[0, 2, :]
        if len(shape) == 2:
            return raw_values[0]
        return None

    @classmethod
    def _importance_factors(cls, *, model: Any, features: SupportRiskFeatures) -> list[SupportRiskFactor]:
        import numpy as np

        importances = getattr(model, "feature_importances_", None)
        if importances is None:
            return []
        return cls._factors_from_values(values=np.asarray(importances, dtype=float), features=features)

    @classmethod
    def _factors_from_values(cls, *, values: Any, features: SupportRiskFeatures) -> list[SupportRiskFactor]:
        payload = features.model_dump()
        factors: list[SupportRiskFactor] = []
        for feature_name, value in zip(FEATURE_NAMES, values):
            numeric_value = float(value)
            factors.append(
                SupportRiskFactor(
                    feature=feature_name,
                    label=FEATURE_LABELS.get(feature_name, feature_name),
                    value=payload.get(feature_name),
                    impact=round(numeric_value, 4),
                    direction="increases_risk" if numeric_value >= 0 else "reduces_risk",
                    explanation=FEATURE_EXPLANATIONS.get(feature_name, "Model factor used in support prediction."),
                )
            )
        factors.sort(key=lambda factor: abs(factor.impact), reverse=True)
        return factors

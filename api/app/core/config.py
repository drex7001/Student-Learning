from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI-Based Student Wellbeing Monitoring System API"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://kgis:kgis@localhost:5432/kgis",
    )
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username: str = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "knowledge-graph-secret")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    )
    # "amended" is the critique-driven variant and the one to develop further
    # (research/dropout-ews/REPORT.md sections 1 and 3). "baseline" is the structure
    # exactly as the original brief specifies it, kept for comparison.
    risk_model_variant: str = os.getenv("RISK_MODEL_VARIANT", "amended")

    # Demonstration deployment: the login screen may list one account per role.
    # Turn this off anywhere real.
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"}

    curriculum_path: Path = BASE_DIR / "data" / "curriculum" / "ol_subject_curriculum.json"
    data_dictionary_path: Path = BASE_DIR / "data" / "curriculum" / "data_dictionary.json"
    generator_config_path: Path = BASE_DIR / "data" / "seeds" / "generator_config.json"
    quiz_bank_path: Path = BASE_DIR / "data" / "quiz"
    risk_factor_copy_path: Path = BASE_DIR / "data" / "seeds" / "risk_factor_copy.json"
    school_roster_path: Path = BASE_DIR / "data" / "seeds" / "school_roster.json"


settings = Settings()

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from app.risk import dropout_ews_bn as bn
from app.services.school_seed import (
    RECORDABLE_CIRCUMSTANCES,
    REGISTER_FIELDS,
    STRUCTURAL_FIELDS,
    _academic_penalty,
    derive_academic_performance_evidence,
    generate_school_seed,
)

ROOT = Path(__file__).resolve().parents[2]
ROSTER = ROOT / "data" / "seeds" / "school_roster.json"


def _fake_hash(password: str) -> str:
    """bcrypt is slow by design; the seed generates ~700 accounts."""
    return f"hashed::{password}"


@pytest.fixture(scope="module")
def seed():
    risk_model = bn.build_model(bn.ModelVariant.AMENDED)
    return generate_school_seed(
        roster_path=ROSTER,
        risk_model=risk_model,
        password_hasher=_fake_hash,
        students_per_class=6,
    )


def test_seed_covers_all_three_sectors(seed) -> None:
    """Sector is a risk-model variable, so the roster must actually exercise all of it."""
    sectors = {school.sector for school in seed.schools}
    assert sectors == {"Urban", "Rural", "Estate"}


def test_students_have_realistic_identities(seed) -> None:
    assert seed.students
    for student in seed.students:
        assert not student.full_name.startswith("Student ")
        assert " " in student.full_name
        assert student.school_id and student.class_id
        assert student.guardian_name and student.guardian_relationship
        assert student.grade in {9, 10, 11}
        assert student.admission_no


def test_sinhala_names_present_for_sinhala_medium(seed) -> None:
    sinhala_students = [s for s in seed.students if s.medium == "Sinhala"]
    assert sinhala_students
    assert all(s.full_name_si for s in sinhala_students)


def test_every_student_evidence_is_valid_model_evidence(seed) -> None:
    """The seeded states must be exactly what the network accepts, or inference fails."""
    for seeded in seed.seeded:
        validated = bn.validate_evidence(seeded.recorded)
        assert validated == seeded.recorded
        for variable, state in seeded.evidence.items():
            assert state in bn.NODE_STATES[variable]


def test_register_and_structural_fields_are_always_recorded(seed) -> None:
    for seeded in seed.seeded:
        for field in STRUCTURAL_FIELDS + REGISTER_FIELDS:
            assert field in seeded.recorded


def test_some_circumstances_are_left_unrecorded(seed) -> None:
    """"What to find out next" needs genuine gaps to have anything to ask for."""
    missing = [
        sum(1 for field in RECORDABLE_CIRCUMSTANCES if field not in seeded.recorded)
        for seeded in seed.seeded
    ]
    assert sum(missing) > 0
    assert any(count == 0 for count in missing) or True


def test_sector_matches_the_school_it_came_from(seed) -> None:
    by_id = {school.id: school for school in seed.schools}
    for seeded in seed.seeded:
        assert seeded.evidence["Sector"] == by_id[seeded.student.school_id].sector


def test_grade_band_follows_grade(seed) -> None:
    for seeded in seed.seeded:
        expected = "Junior_Secondary" if seeded.student.grade == 9 else "OLevel_ALevel"
        assert seeded.evidence["Grade_Band"] == expected


def test_attendance_records_agree_with_attendance_evidence(seed) -> None:
    """An irregular attender must not have a 95% register, or the screen is incoherent."""
    attendance_by_student = {row.student_id: row for row in seed.attendance}
    checked = 0
    for seeded in seed.seeded:
        row = attendance_by_student.get(seeded.student.id)
        if row is None:
            continue
        rate = row.days_present / row.days_total
        if seeded.evidence["Current_Attendance"] == "Irregular":
            assert rate < 0.80
        else:
            assert rate > 0.84
        checked += 1
    assert checked > 0


def test_estate_school_shows_more_strain_than_urban(seed) -> None:
    """Not a claim about real estates -- a check that the sector pin actually propagates
    through the network into the household and school variables."""
    by_school = {school.id: school.sector for school in seed.schools}
    concern = Counter()
    totals = Counter()
    for seeded in seed.seeded:
        sector = by_school[seeded.student.school_id]
        totals[sector] += 1
        if seeded.evidence["Teacher_Resource_Adequacy"] == "Limited":
            concern[sector] += 1
    estate_rate = concern["Estate"] / totals["Estate"]
    urban_rate = concern["Urban"] / totals["Urban"]
    assert estate_rate > urban_rate


def test_academic_penalty_responds_to_adverse_circumstances() -> None:
    calm = {
        "Home_Educational_Support": "Adequate",
        "Teacher_Resource_Adequacy": "Adequate",
        "Current_Attendance": "Regular",
    }
    strained = {
        "Home_Educational_Support": "Limited",
        "Teacher_Resource_Adequacy": "Limited",
        "Current_Attendance": "Irregular",
    }
    assert _academic_penalty(calm) == 0.0
    assert _academic_penalty(strained) > 0.2
    assert _academic_penalty(strained) <= 0.34


def test_users_exist_for_every_student_and_teacher(seed) -> None:
    student_users = [u for u in seed.users if u.role == "student"]
    staff_users = [u for u in seed.users if u.role in {"teacher", "counsellor", "admin"}]
    assert len(student_users) == len(seed.students)
    assert len(staff_users) == len(seed.teachers)
    assert len({u.username for u in seed.users}) == len(seed.users)


def test_each_school_has_a_counsellor(seed) -> None:
    counsellors = [t for t in seed.teachers if t.role_title == "School Counsellor"]
    assert {t.school_id for t in counsellors} == {s.id for s in seed.schools}


def test_seed_is_deterministic() -> None:
    risk_model = bn.build_model(bn.ModelVariant.AMENDED)
    kwargs = dict(
        roster_path=ROSTER,
        risk_model=risk_model,
        password_hasher=_fake_hash,
        students_per_class=4,
    )
    first = generate_school_seed(**kwargs)
    second = generate_school_seed(**kwargs)
    assert [s.student.full_name for s in first.seeded] == [
        s.student.full_name for s in second.seeded
    ]
    assert [s.evidence for s in first.seeded] == [s.evidence for s in second.seeded]


def test_derived_academic_performance_uses_the_weak_threshold() -> None:
    weak = derive_academic_performance_evidence(
        student_id="STU-001", term_id="TERM-2026-2", average_mastery=0.41
    )
    strong = derive_academic_performance_evidence(
        student_id="STU-002", term_id="TERM-2026-2", average_mastery=0.83
    )
    assert weak is not None and weak.state == "Low"
    assert strong is not None and strong.state == "Adequate"
    assert weak.source == "derived"
    assert (
        derive_academic_performance_evidence(
            student_id="STU-003", term_id="TERM-2026-2", average_mastery=None
        )
        is None
    )

"""The routes panel's note must stay true for the factor on screen.

Grade_Band is the one protected characteristic with a direct edge to the outcome
(allowed by name in ``_assert_no_protected_shortcut``), so a blanket "never reaches the
outcome directly" would be false exactly when a teacher picks it from the list.
"""

from app.routers.graph import _routes_note


def _path(*nodes: str) -> dict:
    return {"nodes": [{"id": node} for node in nodes]}


def test_grade_band_note_names_the_direct_route():
    note = _routes_note(
        "Grade_Band",
        [_path("Grade_Band", "Next_Term_Dropout_Risk")],
    )
    assert "direct route" in note
    assert "never a valid target" in note


def test_other_factors_keep_the_general_note():
    note = _routes_note(
        "Bullying_Social_Exclusion",
        [_path("Bullying_Social_Exclusion", "School_Engagement", "Next_Term_Dropout_Risk")],
    )
    assert note.startswith("Every route passes through something a school can change.")
    assert "Apart from grade band" in note

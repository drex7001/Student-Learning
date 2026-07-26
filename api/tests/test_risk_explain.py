from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.risk import dropout_ews_bn as bn
from app.services.risk_explain import (
    GAP_MARK,
    REGISTER_VARIABLES,
    RiskExplainer,
    _reference_state,
)

ROOT = Path(__file__).resolve().parents[2]
COPY = json.loads((ROOT / "data" / "seeds" / "risk_factor_copy.json").read_text(encoding="utf-8"))
FACTORS = {factor["id"]: factor for factor in COPY["factors"]}

STRAINED = {
    "Sector": "Estate",
    "Grade_Band": "OLevel_ALevel",
    "Economic_Strain": "High",
    "Transport_Burden": "High",
    "WASH_Quality": "Inadequate",
    "Bullying_Social_Exclusion": "High",
    "Home_Educational_Support": "Limited",
    "Teacher_Resource_Adequacy": "Limited",
    "Child_Labour_Household_Duties": "High",
    "School_Accommodation": "Inadequate",
    "Previous_Attendance": "Irregular",
    "Current_Attendance": "Irregular",
    "School_Engagement": "Low",
}


@pytest.fixture(scope="module")
def explainer() -> RiskExplainer:
    return RiskExplainer(bn.build_model(bn.ModelVariant.AMENDED))


# -- conditioning sets -------------------------------------------------


def test_background_excludes_levers_and_their_descendants(explainer) -> None:
    """Conditioning on anything a lever changes would block that lever's own effect."""
    for lever in bn.MODIFIABLE_NODES:
        assert lever not in explainer.background_variables
    assert "Access_Barrier" not in explainer.background_variables
    assert "School_Distress" not in explainer.background_variables
    assert "Current_Attendance" not in explainer.background_variables
    # Roots that no lever can reach stay available to condition on.
    assert {"Sector", "Grade_Band", "Neuro_Type", "Parent_Education"} <= (
        explainer.background_variables
    )


def test_drivers_leave_the_register_free(explainer) -> None:
    """The outcome's parents are attendance, engagement and grade band. Condition on
    them and every circumstance becomes d-separated, collapsing all drivers to zero."""
    background = explainer.circumstance_background(STRAINED)
    assert not (REGISTER_VARIABLES & set(background))

    naive = explainer.p_high(STRAINED)
    without_bullying = dict(STRAINED)
    without_bullying["Bullying_Social_Exclusion"] = "Low"
    # With the register pinned, changing bullying must not move the number at all.
    assert explainer.p_high(without_bullying) == pytest.approx(naive, abs=1e-9)

    # With the register free, it does.
    drivers = explainer.drivers(STRAINED, FACTORS)
    assert any(d.variable == "Bullying_Social_Exclusion" and d.delta > 0 for d in drivers)


# -- estimands ---------------------------------------------------------


def test_drivers_are_ranked_and_marked_associational(explainer) -> None:
    drivers = explainer.drivers(STRAINED, FACTORS)
    assert drivers
    assert [d.delta for d in drivers] == sorted((d.delta for d in drivers), reverse=True)
    assert all(d.causal is False for d in drivers)
    assert all(FACTORS[d.variable]["concern"][FACTORS[d.variable]["states"].index(d.state)] for d in drivers)


def test_actions_are_causal_and_reduce_risk(explainer) -> None:
    actions = explainer.action_candidates(STRAINED, FACTORS)
    assert actions
    assert all(a.causal is True for a in actions)
    assert [a.delta for a in actions] == sorted(a.delta for a in actions)
    # Every candidate targets a lever with an authored action.
    for action in actions:
        assert action.variable in bn.MODIFIABLE_NODES
        assert FACTORS[action.variable]["action"]["target"] == action.state
    assert actions[0].delta < 0


def test_worth_asking_only_covers_unrecorded_variables(explainer) -> None:
    partial = {k: v for k, v in STRAINED.items() if k != "Sensory_Environment"}
    asking = explainer.worth_asking(
        partial, FACTORS, ["Sensory_Environment", "Bullying_Social_Exclusion"]
    )
    variables = {row.variable for row in asking}
    assert "Sensory_Environment" in variables
    assert "Bullying_Social_Exclusion" not in variables
    assert all(row.delta >= 0 for row in asking)


def test_worth_asking_marks_causal_versus_observational(explainer) -> None:
    asking = explainer.worth_asking({}, FACTORS, ["WASH_Quality", "Parent_Education"])
    by_variable = {row.variable: row for row in asking}
    assert by_variable["WASH_Quality"].causal is True
    assert by_variable["Parent_Education"].causal is False


def test_routes_never_reach_the_outcome_directly_from_a_protected_trait(explainer) -> None:
    """The central fairness property, checked through the explanation surface."""
    for variable in bn.PROTECTED_OR_IMMUTABLE_NODES:
        if variable == "Grade_Band":
            continue  # a defended direct parent; see REPORT.md
        paths = explainer.routes(variable)
        assert paths, f"{variable} should still reach the outcome through mechanisms"
        for path in paths:
            assert len(path) >= 3, f"{variable} must not reach the outcome directly"


def test_plan_effect_is_not_the_sum_of_its_parts(explainer) -> None:
    plan = explainer.plan_effect(
        STRAINED, ["Bullying_Social_Exclusion", "Home_Educational_Support"], FACTORS
    )
    assert plan["joint_delta"] < 0
    assert plan["joint_delta"] != pytest.approx(plan["sum_of_parts"], abs=1e-6)


def test_plan_refuses_protected_variables(explainer) -> None:
    """Refusing must happen before any reason to skip the variable."""
    for variable in ("Neuro_Type", "Sector", "Parent_Education"):
        with pytest.raises(bn.NonModifiableInterventionError):
            explainer.plan_effect(STRAINED, [variable], FACTORS)


def test_plan_refuses_even_when_the_variable_has_no_authored_action(explainer) -> None:
    with pytest.raises(bn.NonModifiableInterventionError):
        explainer.plan_effect(STRAINED, ["School_Distress"], FACTORS)


# -- gap and banding ---------------------------------------------------


def test_circumstance_gap_surfaces_students_the_register_has_not_caught(explainer) -> None:
    """A learner in difficult circumstances whose register still looks fine."""
    hidden = {
        "Sector": "Estate",
        "Grade_Band": "OLevel_ALevel",
        "Economic_Strain": "High",
        "Bullying_Social_Exclusion": "High",
        "School_Accommodation": "Inadequate",
        "Transport_Burden": "High",
        "Current_Attendance": "Regular",
        "School_Engagement": "High",
    }
    gap = explainer.circumstance_gap(hidden)
    assert gap["circumstance_p_high"] > gap["register_p_high"]
    assert gap["gap"] >= GAP_MARK
    assert gap["ahead"] is True


def test_bands_use_the_model_prior_not_an_invented_cutoff(explainer) -> None:
    assert explainer.band(0.05) == ("not_marked", "Low")
    assert explainer.band(explainer.prior_high + 0.01)[0] == "watch"
    assert explainer.band(0.45) == ("needs_attention", "High")
    assert 0.10 < explainer.prior_high < 0.20


def test_reference_state_is_the_first_non_concern_state() -> None:
    assert _reference_state(["Low", "High"], [False, True]) == "Low"
    assert _reference_state(["High", "Low"], [False, True]) == "High"
    assert _reference_state(["A", "B"], [True, True]) is None


# -- caching -----------------------------------------------------------


def test_repeated_queries_are_cached(explainer) -> None:
    explainer.p_high(STRAINED)
    before = explainer._p_high_cached.cache_info()
    explainer.p_high(STRAINED)
    after = explainer._p_high_cached.cache_info()
    assert after.hits == before.hits + 1

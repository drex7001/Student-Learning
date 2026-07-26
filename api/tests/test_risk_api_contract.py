"""Contract tests for the risk API's non-negotiables.

These do not need a database — they exercise the engine and the conditioning rules the
router depends on, which is where the subtle mistakes live.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.risk import dropout_ews_bn as bn
from app.services.dropout_risk import (
    RECORDABLE_VARIABLES,
    build_basis,
    evidence_mapping,
    load_risk_copy,
    posterior_bars,
    provenance_from,
)

ROOT = Path(__file__).resolve().parents[2]
COPY_PATH = ROOT / "data" / "seeds" / "risk_factor_copy.json"


@pytest.fixture(scope="module")
def copy():
    return load_risk_copy(str(COPY_PATH))


@pytest.fixture(scope="module")
def risk_model():
    return bn.build_model(bn.ModelVariant.AMENDED)


# -- provenance travels with the number --------------------------------


def test_every_result_carries_provenance_and_caveat(risk_model) -> None:
    result = bn.infer_dropout_risk(risk_model, {"Current_Attendance": "Irregular"})
    provenance = provenance_from(result)
    assert provenance.provenance
    assert provenance.caveat
    assert provenance.model_fingerprint
    assert provenance.interpretation == "observational_conditional"


def test_interventions_are_labelled_as_interventions(risk_model) -> None:
    result = bn.estimate_intervention_effect(risk_model, {"WASH_Quality": "Adequate"})
    assert provenance_from(result).interpretation == "interventional_do"


# -- the what-if conditioning rule -------------------------------------


def test_intervening_on_a_recorded_variable_overrides_it(risk_model) -> None:
    """do() replaces an observation; passing both would ask the model to fix and
    observe the same variable, which the engine refuses."""
    recorded = {"Sector": "Estate", "WASH_Quality": "Inadequate"}

    with pytest.raises(ValueError, match="both intervention and evidence"):
        bn.estimate_intervention_effect(
            risk_model, {"WASH_Quality": "Adequate"}, recorded
        )

    # What the router does: drop the intervened variable from the conditioning set.
    conditioning = {k: v for k, v in recorded.items() if k != "WASH_Quality"}
    result = bn.estimate_intervention_effect(
        risk_model, {"WASH_Quality": "Adequate"}, conditioning
    )
    assert result["interpretation"] == "interventional_do"


# -- copy layer --------------------------------------------------------


def test_every_model_node_has_authored_copy(copy) -> None:
    """A raw identifier must never reach a screen."""
    for variable, states in bn.NODE_STATES.items():
        factor = copy.factors.get(variable)
        assert factor is not None, f"no authored copy for {variable}"
        assert factor["label"] and factor["label_si"]
        assert list(factor["states"]) == list(states)
        assert len(factor["state_labels"]) == len(states)
        assert len(factor["state_labels_si"]) == len(states)
        assert all(factor["state_labels"])
        assert all(factor["state_labels_si"])


def test_every_modifiable_node_has_an_action_with_an_owner(copy) -> None:
    for variable in bn.MODIFIABLE_NODES:
        action = copy.factors[variable].get("action")
        assert action, f"{variable} is modifiable but has no authored action"
        assert action["owner"]
        assert action["target"] in bn.NODE_STATES[variable]


def test_protected_nodes_explain_why_they_are_not_levers(copy) -> None:
    for variable in bn.PROTECTED_OR_IMMUTABLE_NODES:
        assert copy.factors[variable]["protected"] is True
        assert copy.factors[variable].get("why_not_actionable")


def test_recordable_variables_are_all_real_model_nodes() -> None:
    for variable in RECORDABLE_VARIABLES:
        assert variable in bn.NODE_STATES
        assert variable != bn.TARGET_NODE


# -- evidence mapping is defensive -------------------------------------


def test_evidence_mapping_drops_stale_rows() -> None:
    """A renamed node or state must not take the whole screen down."""
    mapping = evidence_mapping(
        {
            "Current_Attendance": {"state": "Irregular"},
            "Retired_Variable": {"state": "Whatever"},
            "WASH_Quality": {"state": "NotAState"},
            bn.TARGET_NODE: {"state": "High"},
        }
    )
    assert mapping == {"Current_Attendance": "Irregular"}


def test_evidence_mapping_never_passes_the_target_as_evidence() -> None:
    assert bn.TARGET_NODE not in evidence_mapping({bn.TARGET_NODE: {"state": "High"}})


# -- presentation ------------------------------------------------------


def test_posterior_bars_follow_the_model_state_order(copy, risk_model) -> None:
    result = bn.infer_dropout_risk(risk_model, {})
    bars = posterior_bars(result["posterior"], copy)
    assert [bar.state for bar in bars] == list(bn.NODE_STATES[bn.TARGET_NODE])
    assert sum(bar.probability for bar in bars) == pytest.approx(1.0, abs=1e-4)
    assert all(bar.label and bar.label_si for bar in bars)


def test_basis_names_the_register_fields_that_determine_the_figure(copy) -> None:
    basis = build_basis(
        {
            "Current_Attendance": "Irregular",
            "School_Engagement": "Low",
            "Grade_Band": "OLevel_ALevel",
        },
        copy,
    )
    assert "Irregular" in basis
    assert "not a prediction about this child" in basis.lower()


def test_basis_says_so_when_the_register_is_incomplete(copy) -> None:
    assert "not recorded" in build_basis({"Grade_Band": "OLevel_ALevel"}, copy)


# -- the copy file stays in step with the model ------------------------


def test_copy_file_matches_the_running_model_fingerprint(risk_model) -> None:
    payload = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    assert payload["model_fingerprint"] == risk_model.fingerprint, (
        "data/seeds/risk_factor_copy.json is stale; "
        "re-run scripts/build_risk_factor_copy.py"
    )

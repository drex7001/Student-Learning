"""Test suite for the school-disengagement early-support Bayesian network.

Three classes of test, in increasing order of what they actually protect:

1.  **Arithmetic** -- columns sum to 1, probabilities in range, the graph is acyclic,
    every node has a CPD, ``check_model()`` passes. These are the checks the brief asks
    for. They catch typos.

2.  **Alignment** -- that the value written into cell *(state, parent-combination)* is
    the value that comes back out of it. A CPD matrix is a flat array whose column order
    is a library convention; if the assumed order is wrong, every check in class 1 still
    passes while the model means something entirely different. This is the class of bug
    that silently invalidates results, so it is verified against
    ``TabularCPD.get_value`` rather than against the convention.

3.  **Semantics** -- that the elicited *qualitative* claims actually hold in the numbers:
    accommodation reduces mismatch, a supportive sensory environment reduces distress,
    bullying raises distress and lowers engagement, barriers raise irregular attendance,
    and irregular-plus-disengaged is the worst risk profile. The brief states these as
    requirements; making them executable is what stops a later "harmless" parameter tweak
    from quietly inverting the model's meaning.

Run:  cd api && pytest -q tests/test_dropout_ews_bn.py
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import networkx as nx
import numpy as np
import pytest
from pgmpy.factors.discrete import TabularCPD

from app.risk import dropout_ews_bn as bn

ALL_VARIANTS = list(bn.ModelVariant)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", params=ALL_VARIANTS, ids=lambda v: v.value)
def risk_model(request: pytest.FixtureRequest) -> bn.RiskModel:
    """A fully built model, once per variant, shared across the module."""
    return bn.build_model(request.param)


@pytest.fixture(scope="module")
def baseline_model() -> bn.RiskModel:
    return bn.build_model(bn.ModelVariant.BASELINE)


@pytest.fixture(scope="module")
def cohort(baseline_model: bn.RiskModel):
    """A small synthetic cohort; 10k is exported by ``main`` but is slow for tests."""
    return bn.generate_synthetic_data(baseline_model, 500, seed=1234)


# ---------------------------------------------------------------------------
# Class 1: the arithmetic the brief requires
# ---------------------------------------------------------------------------


def test_every_cpd_column_sums_to_one(risk_model: bn.RiskModel) -> None:
    for cpd in risk_model.model.get_cpds():
        sums = np.asarray(cpd.get_values(), dtype=float).sum(axis=0)
        assert np.allclose(sums, 1.0, atol=bn.PROBABILITY_TOLERANCE), (
            f"{cpd.variable}: column sums {sums} deviate from 1.0"
        )


def test_all_probabilities_within_unit_interval(risk_model: bn.RiskModel) -> None:
    for cpd in risk_model.model.get_cpds():
        values = np.asarray(cpd.get_values(), dtype=float)
        assert values.min() >= 0.0 and values.max() <= 1.0, f"{cpd.variable} out of [0, 1]"


def test_no_deterministic_zero_or_one(risk_model: bn.RiskModel) -> None:
    """Requirement: avoid probabilities of exactly 0 or 1.

    No elicited prior about a child's circumstances earns the claim "impossible".
    """
    for cpd in risk_model.model.get_cpds():
        values = np.asarray(cpd.get_values(), dtype=float)
        assert values.min() > 0.0, f"{cpd.variable} contains an exact 0"
        assert values.max() < 1.0, f"{cpd.variable} contains an exact 1"


def test_model_is_acyclic(risk_model: bn.RiskModel) -> None:
    assert nx.is_directed_acyclic_graph(risk_model.model)


def test_every_node_has_a_cpd(risk_model: bn.RiskModel) -> None:
    for node in risk_model.model.nodes():
        assert risk_model.model.get_cpds(node) is not None, f"{node} has no CPD"
    assert len(risk_model.model.get_cpds()) == len(bn.NODE_STATES)


def test_check_model_returns_true(risk_model: bn.RiskModel) -> None:
    assert risk_model.model.check_model() is True


def test_cpd_cardinality_matches_central_registry(risk_model: bn.RiskModel) -> None:
    for cpd in risk_model.model.get_cpds():
        variable = str(cpd.variable)
        assert cpd.variable_card == len(bn.NODE_STATES[variable])
        assert list(cpd.state_names[variable]) == list(bn.NODE_STATES[variable])


def test_node_set_matches_central_registry(risk_model: bn.RiskModel) -> None:
    assert set(risk_model.model.nodes()) == set(bn.NODE_STATES)


def test_validate_cpds_accepts_the_built_model(risk_model: bn.RiskModel) -> None:
    bn.validate_cpds(risk_model.model.get_cpds())


# ---------------------------------------------------------------------------
# Class 2: alignment -- the check that the other checks cannot make
# ---------------------------------------------------------------------------


def test_cpd_cell_alignment(risk_model: bn.RiskModel) -> None:
    """Every cell must be reachable by name at the value the spec computed for it.

    ``_parent_state_combinations`` assumes pgmpy orders CPD columns as
    ``itertools.product`` over the evidence list. This test re-derives every cell through
    the public ``get_value(**assignment)`` API and compares, so a change in that
    convention fails loudly instead of silently transposing the model.
    """
    for cpd in risk_model.model.get_cpds():
        variable = str(cpd.variable)
        parents = [str(p) for p in cpd.variables[1:]]
        matrix = np.asarray(cpd.get_values(), dtype=float)
        combos = list(itertools.product(*(bn.NODE_STATES[p] for p in parents)))
        assert matrix.shape == (len(bn.NODE_STATES[variable]), len(combos))
        for column, combo in enumerate(combos):
            assignment = dict(zip(parents, combo))
            for row, state in enumerate(bn.NODE_STATES[variable]):
                expected = matrix[row, column]
                actual = cpd.get_value(**{variable: state, **assignment})
                assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (
                    f"{variable}: cell ({state}, {assignment}) is {actual}, "
                    f"matrix column {column} says {expected}"
                )


def test_parents_in_cpd_match_parents_in_graph(risk_model: bn.RiskModel) -> None:
    for node in risk_model.model.nodes():
        cpd = risk_model.model.get_cpds(node)
        assert {str(p) for p in cpd.variables[1:]} == set(risk_model.model.get_parents(node))


def test_binary_helper_reproduces_hand_computed_logistic() -> None:
    """The helper's arithmetic, checked against the closed form on a known case."""
    spec = bn.BinaryLogisticCPDSpec(
        baseline=0.06,
        effects={
            "Neuro_Type": {"ADHD": 1.40, "ASD": 1.70},
            "School_Accommodation": {"Inadequate": 1.30},
        },
        interactions={(("Neuro_Type", "ASD"), ("School_Accommodation", "Inadequate")): 1.30},
    )
    cpd = bn.make_binary_cpd("Support_Mismatch", ("Neuro_Type", "School_Accommodation"), spec)

    base = math.log(0.06 / 0.94)
    for neuro, accommodation, extra in [
        ("Typical", "Adequate", 0.0),
        ("Typical", "Inadequate", 1.30),
        ("ADHD", "Adequate", 1.40),
        ("ADHD", "Inadequate", 1.40 + 1.30),
        ("ASD", "Adequate", 1.70),
        ("ASD", "Inadequate", 1.70 + 1.30 + 1.30),
    ]:
        expected = 1.0 / (1.0 + math.exp(-(base + extra)))
        actual = cpd.get_value(
            Support_Mismatch="High", Neuro_Type=neuro, School_Accommodation=accommodation
        )
        assert math.isclose(actual, expected, rel_tol=1e-9), f"{neuro}/{accommodation}"


def test_ordinal_helper_reproduces_hand_computed_cumulative_logit() -> None:
    spec = bn.OrdinalLogisticCPDSpec(
        cutpoints=(2.20, 4.20), effects={"Current_Attendance": {"Irregular": 2.60}}
    )
    cpd = bn.make_ordinal_cpd(bn.TARGET_NODE, ("Current_Attendance",), spec)
    for state, eta in [("Regular", 0.0), ("Irregular", 2.60)]:
        p_at_least_mid = 1.0 / (1.0 + math.exp(-(eta - 2.20)))
        p_high = 1.0 / (1.0 + math.exp(-(eta - 4.20)))
        expected = {
            "Low": 1.0 - p_at_least_mid,
            "Medium": p_at_least_mid - p_high,
            "High": p_high,
        }
        for name, value in expected.items():
            actual = cpd.get_value(
                **{bn.TARGET_NODE: name, "Current_Attendance": state}
            )
            assert math.isclose(actual, value, rel_tol=1e-6), f"{state}/{name}"


def test_ordinal_states_stay_ordered_in_every_column() -> None:
    """The cumulative-logit form must never produce a non-monotone latent ordering."""
    cpd = bn.build_model().model.get_cpds(bn.TARGET_NODE)
    values = np.asarray(cpd.get_values(), dtype=float)
    cumulative = np.cumsum(values, axis=0)
    assert np.all(np.diff(cumulative, axis=0) >= -1e-12)


# ---------------------------------------------------------------------------
# Class 2b: the structural/ethical guarantees
# ---------------------------------------------------------------------------


def test_neuro_type_has_no_direct_edge_to_outcome(risk_model: bn.RiskModel) -> None:
    assert "Neuro_Type" not in risk_model.model.get_parents(bn.TARGET_NODE)
    assert ("Neuro_Type", bn.TARGET_NODE) not in risk_model.model.edges()


def test_neuro_type_still_reaches_the_outcome_through_mechanisms(risk_model: bn.RiskModel) -> None:
    """Not a direct cause, but not disconnected either: the mechanisms must be live."""
    paths = list(nx.all_simple_paths(risk_model.model, "Neuro_Type", bn.TARGET_NODE))
    assert paths, "Neuro_Type must influence the outcome via mediators"
    for path in paths:
        assert len(path) >= 3, f"path {path} bypasses all mediators"
        assert any(
            node in {"Support_Mismatch", "School_Distress", "Bullying_Social_Exclusion"}
            for node in path[1:-1]
        ), f"path {path} does not run through an environmental mechanism"


def test_protected_characteristics_are_not_outcome_parents(risk_model: bn.RiskModel) -> None:
    parents = set(risk_model.model.get_parents(bn.TARGET_NODE))
    assert not (bn.PROTECTED_OR_IMMUTABLE_NODES - {"Grade_Band"}) & parents


def test_no_same_period_feedback_between_attendance_and_performance(
    risk_model: bn.RiskModel,
) -> None:
    edges = set(risk_model.model.edges())
    assert ("Current_Attendance", "Current_Academic_Performance") not in edges
    assert ("Current_Academic_Performance", "Current_Attendance") not in edges
    assert ("Previous_Attendance", "Current_Academic_Performance") in edges


def test_parent_counts_stay_reviewable(risk_model: bn.RiskModel) -> None:
    """Keep CPDs small enough that a human can actually audit them."""
    description = bn.describe_structure(risk_model)
    assert description["max_parent_count"] <= 4
    assert description["max_cpd_columns"] <= 24


def test_modifiable_and_protected_sets_are_disjoint() -> None:
    assert not bn.MODIFIABLE_NODES & bn.PROTECTED_OR_IMMUTABLE_NODES
    assert bn.MODIFIABLE_NODES <= set(bn.NODE_STATES)
    assert bn.PROTECTED_OR_IMMUTABLE_NODES <= set(bn.NODE_STATES)


def test_amended_variant_adds_exactly_the_declared_edges() -> None:
    baseline = set(bn.build_structure(bn.ModelVariant.BASELINE).edges())
    amended = set(bn.build_structure(bn.ModelVariant.AMENDED).edges())
    assert amended - baseline == set(bn.AMENDMENT_EDGES)


def test_edge_evidence_covers_every_edge_and_nothing_else() -> None:
    """`EDGE_EVIDENCE` is the single source of truth for the report's evidence columns.

    Regression: the evidence level used to be written by hand in two report sections,
    which had silently drifted apart on five edges and omitted one edge entirely.
    """
    declared = set(bn.EDGE_EVIDENCE)
    actual = set(bn.BASELINE_EDGES) | set(bn.AMENDMENT_EDGES)
    assert declared - actual == set(), f"evidence recorded for non-existent edges: {declared - actual}"
    assert actual - declared == set(), f"edges with no recorded evidence level: {actual - declared}"


@pytest.mark.parametrize("variant", ALL_VARIANTS, ids=lambda v: v.value)
def test_evidence_summary_partitions_the_edge_set(variant: bn.ModelVariant) -> None:
    summary = bn.summarise_evidence_levels(variant)
    expected = len(bn.BASELINE_EDGES) + (
        len(bn.AMENDMENT_EDGES) if variant is bn.ModelVariant.AMENDED else 0
    )
    assert summary["n_edges"] == expected
    assert sum(summary["counts"].values()) == expected, "levels must partition the edge set"
    listed = [e for group in summary["edges_by_level"].values() for e in group]
    assert len(listed) == len(set(listed)) == expected, "each edge appears in exactly one level"
    assert 0.0 < summary["expert_hypothesis_share"] < 1.0
    json.dumps(summary)


def test_model_fingerprint_changes_when_a_parameter_changes() -> None:
    """Audit logs depend on the fingerprint actually identifying the parameter set."""
    base = bn.build_model()
    perturbed = bn.build_perturbed_model(
        bn.ModelVariant.BASELINE, bn.SENSITIVITY_TARGETS[0], 1.10
    )
    assert base.fingerprint != perturbed.fingerprint
    assert base.fingerprint == bn.build_model().fingerprint  # and is deterministic


# ---------------------------------------------------------------------------
# Class 3: the elicited semantics, made executable
# ---------------------------------------------------------------------------


def _p(model: bn.RiskModel, node: str, state: str, evidence: dict[str, str]) -> float:
    return bn.infer_dropout_risk(model, evidence, target=node)["posterior"][state]


@pytest.mark.parametrize("neuro", ["ADHD", "ASD"])
def test_adequate_accommodation_reduces_support_mismatch(
    risk_model: bn.RiskModel, neuro: str
) -> None:
    inadequate = _p(
        risk_model,
        "Support_Mismatch",
        "High",
        {"Neuro_Type": neuro, "School_Accommodation": "Inadequate"},
    )
    adequate = _p(
        risk_model,
        "Support_Mismatch",
        "High",
        {"Neuro_Type": neuro, "School_Accommodation": "Adequate"},
    )
    assert adequate < inadequate
    assert inadequate - adequate > 0.30, "the accommodation effect must be substantial"


@pytest.mark.parametrize("neuro", ["ADHD", "ASD"])
def test_accommodated_neurodivergent_student_is_not_automatically_distressed(
    risk_model: bn.RiskModel, neuro: str
) -> None:
    """The brief's central fairness requirement, as a number.

    In a supportive setting, a neurodivergent student's distress must sit far closer to a
    typical student's than to the same student in an unsupportive setting -- otherwise the
    model is treating neurodivergence itself as the hazard.
    """
    supportive = {
        "School_Accommodation": "Adequate",
        "Sensory_Environment": "Supportive",
        "Bullying_Social_Exclusion": "Low",
        "WASH_Quality": "Adequate",
    }
    unsupportive = {
        "School_Accommodation": "Inadequate",
        "Sensory_Environment": "Overloading",
        "Bullying_Social_Exclusion": "High",
        "WASH_Quality": "Inadequate",
    }
    nd_supported = _p(risk_model, "School_Distress", "High", {"Neuro_Type": neuro, **supportive})
    typical_supported = _p(
        risk_model, "School_Distress", "High", {"Neuro_Type": "Typical", **supportive}
    )
    nd_unsupported = _p(
        risk_model, "School_Distress", "High", {"Neuro_Type": neuro, **unsupportive}
    )

    assert nd_supported < 0.25, "a supported neurodivergent student must not be high-distress"
    assert abs(nd_supported - typical_supported) < (nd_unsupported - nd_supported), (
        "the gap to a typical peer in the same supportive setting must be smaller than "
        "the gap created by removing support"
    )


def test_supportive_sensory_environment_reduces_distress(risk_model: bn.RiskModel) -> None:
    overloading = _p(risk_model, "School_Distress", "High", {"Sensory_Environment": "Overloading"})
    supportive = _p(risk_model, "School_Distress", "High", {"Sensory_Environment": "Supportive"})
    assert supportive < overloading


def test_bullying_raises_distress_and_lowers_engagement(risk_model: bn.RiskModel) -> None:
    assert _p(risk_model, "School_Distress", "High", {"Bullying_Social_Exclusion": "High"}) > _p(
        risk_model, "School_Distress", "High", {"Bullying_Social_Exclusion": "Low"}
    )
    assert _p(risk_model, "School_Engagement", "Low", {"Bullying_Social_Exclusion": "High"}) > _p(
        risk_model, "School_Engagement", "Low", {"Bullying_Social_Exclusion": "Low"}
    )


def test_economic_strain_is_monotone_in_labour_and_health_burden(
    risk_model: bn.RiskModel,
) -> None:
    labour = [
        _p(risk_model, "Child_Labour_Household_Duties", "High", {"Economic_Strain": s})
        for s in ("Low", "Moderate", "High")
    ]
    health = [
        _p(risk_model, "Food_Health_Burden", "High", {"Economic_Strain": s})
        for s in ("Low", "Moderate", "High")
    ]
    assert labour == sorted(labour), labour
    assert health == sorted(health), health


def test_inadequate_wash_raises_health_burden_and_distress(risk_model: bn.RiskModel) -> None:
    assert _p(risk_model, "Food_Health_Burden", "High", {"WASH_Quality": "Inadequate"}) > _p(
        risk_model, "Food_Health_Burden", "High", {"WASH_Quality": "Adequate"}
    )
    assert _p(risk_model, "School_Distress", "High", {"WASH_Quality": "Inadequate"}) > _p(
        risk_model, "School_Distress", "High", {"WASH_Quality": "Adequate"}
    )


def test_access_and_psychological_barriers_raise_irregular_attendance(
    risk_model: bn.RiskModel,
) -> None:
    reference = _p(
        risk_model,
        "Current_Attendance",
        "Irregular",
        {"Access_Barrier": "Low", "Psychological_Attendance_Barrier": "Low"},
    )
    for barrier in ("Access_Barrier", "Psychological_Attendance_Barrier"):
        raised = _p(
            risk_model,
            "Current_Attendance",
            "Irregular",
            {
                "Access_Barrier": "Low",
                "Psychological_Attendance_Barrier": "Low",
                **{barrier: "High"},
            },
        )
        assert raised > reference, barrier
    both = _p(
        risk_model,
        "Current_Attendance",
        "Irregular",
        {"Access_Barrier": "High", "Psychological_Attendance_Barrier": "High"},
    )
    assert both > reference + 0.20


def test_transport_and_labour_burdens_raise_access_barrier(risk_model: bn.RiskModel) -> None:
    low = _p(
        risk_model,
        "Access_Barrier",
        "High",
        {"Transport_Burden": "Low", "Child_Labour_Household_Duties": "Low"},
    )
    high = _p(
        risk_model,
        "Access_Barrier",
        "High",
        {"Transport_Burden": "High", "Child_Labour_Household_Duties": "High"},
    )
    assert high > low + 0.30


def test_irregular_attendance_with_low_engagement_is_the_worst_profile(
    risk_model: bn.RiskModel,
) -> None:
    """Requirement: this combination must produce the highest-risk distribution."""
    profiles = {
        (attendance, engagement): _p(
            risk_model,
            bn.TARGET_NODE,
            "High",
            {"Current_Attendance": attendance, "School_Engagement": engagement},
        )
        for attendance in ("Regular", "Irregular")
        for engagement in ("High", "Low")
    }
    worst = max(profiles, key=profiles.__getitem__)
    assert worst == ("Irregular", "Low"), profiles
    assert profiles[("Irregular", "Low")] > 0.5
    assert profiles[("Regular", "High")] < 0.1
    # and it must be the argmax state, not merely the largest P(High)
    posterior = bn.infer_dropout_risk(
        risk_model, {"Current_Attendance": "Irregular", "School_Engagement": "Low"}
    )
    assert posterior["highest_state"] == "High"


def test_risk_is_monotone_in_grade_band(risk_model: bn.RiskModel) -> None:
    risks = [
        _p(risk_model, bn.TARGET_NODE, "High", {"Grade_Band": band})
        for band in ("Primary", "Junior_Secondary", "OLevel_ALevel")
    ]
    assert risks == sorted(risks), risks


# ---------------------------------------------------------------------------
# Class 3b: inference contract (the bit FastAPI depends on)
# ---------------------------------------------------------------------------


def test_inference_result_is_json_serialisable(baseline_model: bn.RiskModel) -> None:
    result = bn.infer_dropout_risk(baseline_model, {"Current_Attendance": "Irregular"})
    round_tripped = json.loads(json.dumps(result))
    assert round_tripped["posterior"].keys() == set(bn.NODE_STATES[bn.TARGET_NODE])
    assert round_tripped["interpretation"] == "observational_conditional"
    assert bn.PRIOR_PROVENANCE in round_tripped["provenance"]
    assert round_tripped["model_fingerprint"] == baseline_model.fingerprint


def test_posterior_sums_to_one_and_argmax_is_consistent(baseline_model: bn.RiskModel) -> None:
    result = bn.infer_dropout_risk(baseline_model, {"Previous_Attendance": "Irregular"})
    assert math.isclose(sum(result["posterior"].values()), 1.0, abs_tol=1e-5)
    assert result["highest_probability"] == max(result["posterior"].values())
    assert result["posterior"][result["highest_state"]] == result["highest_probability"]


def test_empty_evidence_returns_the_prior(baseline_model: bn.RiskModel) -> None:
    assert bn.infer_dropout_risk(baseline_model, {})["n_evidence"] == 0
    assert bn.infer_dropout_risk(baseline_model, None)["posterior"] == (
        bn.infer_dropout_risk(baseline_model, {})["posterior"]
    )


def test_unknown_node_raises(baseline_model: bn.RiskModel) -> None:
    with pytest.raises(bn.UnknownNodeError, match="Unknown variable"):
        bn.infer_dropout_risk(baseline_model, {"Household_Income": "Low"})


def test_unknown_state_raises_and_lists_valid_states(baseline_model: bn.RiskModel) -> None:
    with pytest.raises(bn.UnknownStateError) as info:
        bn.infer_dropout_risk(baseline_model, {"Sector": "Suburban"})
    assert "Urban" in str(info.value) and "Estate" in str(info.value)


def test_target_cannot_be_supplied_as_evidence(baseline_model: bn.RiskModel) -> None:
    with pytest.raises(bn.UnknownNodeError, match="query target"):
        bn.infer_dropout_risk(baseline_model, {bn.TARGET_NODE: "High"})


def test_evidence_errors_are_value_errors(baseline_model: bn.RiskModel) -> None:
    """So a FastAPI handler can catch one type and return 422."""
    assert issubclass(bn.UnknownNodeError, bn.EvidenceError)
    assert issubclass(bn.UnknownStateError, bn.EvidenceError)
    assert issubclass(bn.EvidenceError, ValueError)


def test_unknown_target_raises_an_evidence_error_not_a_library_error(
    baseline_model: bn.RiskModel,
) -> None:
    """A bad `target` must not leak a NetworkXError (which a service returns as 500).

    Regression: both inference entry points previously passed an unvalidated target
    straight to pgmpy.
    """
    for call in (
        lambda: bn.infer_dropout_risk(baseline_model, {}, target="Household_Wealth"),
        lambda: bn.estimate_intervention_effect(
            baseline_model, {"WASH_Quality": "Adequate"}, target="Household_Wealth"
        ),
        lambda: bn.trace_pathway_attenuation(baseline_model, {}, {}, pathway=("Sector", "Nope")),
    ):
        with pytest.raises(ValueError):
            call()
    with pytest.raises(bn.UnknownNodeError, match="Unknown query target"):
        bn.infer_dropout_risk(baseline_model, {}, target="Household_Wealth")


def test_inference_does_not_mutate_the_model(baseline_model: bn.RiskModel) -> None:
    before = baseline_model.fingerprint
    bn.infer_dropout_risk(baseline_model, {"Sector": "Estate"})
    bn.estimate_intervention_effect(baseline_model, {"WASH_Quality": "Adequate"})
    assert bn.model_fingerprint(baseline_model.model, baseline_model.variant) == before


# ---------------------------------------------------------------------------
# Class 3c: interventions
# ---------------------------------------------------------------------------


def test_intervening_on_neuro_type_is_refused(baseline_model: bn.RiskModel) -> None:
    with pytest.raises(bn.NonModifiableInterventionError, match="Neuro_Type"):
        bn.estimate_intervention_effect(baseline_model, {"Neuro_Type": "Typical"})


@pytest.mark.parametrize("variable", sorted(bn.PROTECTED_OR_IMMUTABLE_NODES))
def test_no_protected_characteristic_can_be_intervened_on(
    baseline_model: bn.RiskModel, variable: str
) -> None:
    with pytest.raises(bn.NonModifiableInterventionError):
        bn.estimate_intervention_effect(baseline_model, {variable: bn.NODE_STATES[variable][0]})


@pytest.mark.parametrize("variable", sorted(bn.MODIFIABLE_NODES))
def test_every_modifiable_node_can_be_intervened_on(
    baseline_model: bn.RiskModel, variable: str
) -> None:
    result = bn.estimate_intervention_effect(
        baseline_model, {variable: bn.NODE_STATES[variable][0]}
    )
    assert math.isclose(sum(result["posterior"].values()), 1.0, abs_tol=1e-5)
    assert result["interpretation"] == "interventional_do"


def test_intervention_and_evidence_may_not_overlap(baseline_model: bn.RiskModel) -> None:
    with pytest.raises(bn.EvidenceError, match="both intervention and evidence"):
        bn.estimate_intervention_effect(
            baseline_model, {"WASH_Quality": "Adequate"}, {"WASH_Quality": "Inadequate"}
        )


def test_empty_intervention_is_rejected(baseline_model: bn.RiskModel) -> None:
    with pytest.raises(bn.EvidenceError, match="at least one variable"):
        bn.estimate_intervention_effect(baseline_model, {})


def test_do_equals_conditioning_for_a_parentless_variable(baseline_model: bn.RiskModel) -> None:
    """With no back-door path there is nothing for do() to block.

    This is a fact about the assumed DAG, not about the world; it is exactly why the
    absence of confounder edges is itself a modelling claim that needs defending.
    """
    parentless = [v for v in bn.MODIFIABLE_NODES if not baseline_model.model.get_parents(v)]
    assert parentless, "expected at least one parentless modifiable node in the baseline"
    for variable in parentless:
        comparison = bn.compare_observational_and_interventional(
            baseline_model, variable, bn.NODE_STATES[variable][0]
        )
        assert comparison["identical_in_this_dag"], variable
        assert comparison["max_abs_difference"] < 1e-6


def test_do_differs_from_conditioning_for_a_confounded_variable(
    baseline_model: bn.RiskModel,
) -> None:
    comparison = bn.compare_observational_and_interventional(
        baseline_model, "Food_Health_Burden", "Low"
    )
    assert comparison["parents_of_variable"]
    assert not comparison["identical_in_this_dag"]
    assert comparison["max_abs_difference"] > 1e-6


def test_truncated_factorisation_matches_manual_mutilated_graph(
    baseline_model: bn.RiskModel,
) -> None:
    """Pin the do() semantics against an independent hand-rolled computation."""
    from pgmpy.inference import VariableElimination

    mutilated = baseline_model.model.do(["Transport_Burden"])
    assert mutilated.get_parents("Transport_Burden") == []
    factor = VariableElimination(mutilated).query(
        variables=[bn.TARGET_NODE],
        evidence={"Transport_Burden": "Low", "Sector": "Estate"},
        show_progress=False,
    )
    manual = dict(zip(factor.state_names[bn.TARGET_NODE], np.asarray(factor.values).ravel()))
    ours = bn.estimate_intervention_effect(
        baseline_model, {"Transport_Burden": "Low"}, {"Sector": "Estate"}
    )["posterior"]
    for state, value in manual.items():
        assert math.isclose(ours[state], float(value), abs_tol=1e-6), state


def test_pgmpy_causal_api_audit_reports_the_known_discrepancy(
    baseline_model: bn.RiskModel,
) -> None:
    """Guard the workaround.

    ``estimate_intervention_effect`` deliberately avoids ``CausalInference.query`` for
    conditional interventional queries because pgmpy 1.1.2 drops evidence outside its
    chosen adjustment set. If a future pgmpy fixes that, this test starts failing and the
    workaround (and its comment) can be reconsidered -- which is the point.
    """
    audit = bn.audit_pgmpy_causal_api(baseline_model, variable="Transport_Burden", state="Low")
    if not audit["checked"]:
        pytest.skip("pgmpy CausalInference unavailable")
    no_evidence = [r for r in audit["probes"] if not r["conditioning_evidence"]]
    assert no_evidence and all(r["agrees"] for r in no_evidence), (
        "with no evidence the two engines must agree exactly"
    )
    assert audit["n_disagreements"] >= 1, (
        "pgmpy appears to have fixed conditional do-queries; re-evaluate the workaround "
        "in estimate_intervention_effect"
    )


def test_full_inclusion_package_reduces_risk(baseline_model: bn.RiskModel) -> None:
    profile = {"Neuro_Type": "ASD", "Sector": "Estate", "Previous_Attendance": "Irregular"}
    before = bn.infer_dropout_risk(baseline_model, profile)["posterior"]["High"]
    after = bn.estimate_intervention_effect(
        baseline_model,
        {
            "School_Accommodation": "Adequate",
            "WASH_Quality": "Adequate",
            "Bullying_Social_Exclusion": "Low",
            "Sensory_Environment": "Supportive",
            "Transport_Burden": "Low",
            "Home_Educational_Support": "Adequate",
        },
        evidence=profile,
    )["posterior"]["High"]
    assert after < before


# ---------------------------------------------------------------------------
# Class 3d: scenarios, attenuation, sensitivity
# ---------------------------------------------------------------------------


def test_scenario_battery_covers_the_three_required_comparisons(
    baseline_model: bn.RiskModel,
) -> None:
    report = bn.compare_scenarios(baseline_model)
    assert set(report["contrasts"]) == {
        "A_environmental_mismatch",
        "B_socioeconomic_access",
        "C_protective_factors",
    }
    assert len(report["results"]) == len(bn.SCENARIOS)
    for record in report["results"]:
        assert math.isclose(sum(record["posterior"].values()), 1.0, abs_tol=1e-5)
    json.dumps(report)  # must be serialisable


def test_accommodation_and_relief_and_protection_all_reduce_risk(
    risk_model: bn.RiskModel,
) -> None:
    """Every required contrast must point the right way in both variants."""
    contrasts = bn.compare_scenarios(risk_model)["contrasts"]
    assert contrasts["A_environmental_mismatch"][0]["delta_p_high"] < 0, "A2 must beat A1"
    assert contrasts["B_socioeconomic_access"][0]["delta_p_high"] < 0, "B2 must beat B1"
    assert contrasts["C_protective_factors"][0]["delta_p_high"] < 0, "C2 must beat C1"


def test_scenario_a_isolates_the_environment_from_the_neurotype(
    risk_model: bn.RiskModel,
) -> None:
    """A1 > A2 > A3 is the ordering the ethical argument depends on.

    A1 (unaccommodated ASD) must exceed A2 (accommodated ASD), and A2 must sit near A3
    (typical student, same poor building) -- showing that most of A1's excess is the
    setting rather than the student.
    """
    by_label = {r["label"]: r["posterior"]["High"] for r in bn.compare_scenarios(risk_model)["results"]}
    a1, a2, a3 = (
        by_label["A1_ASD_unsupported"],
        by_label["A2_ASD_accommodated"],
        by_label["A3_typical_same_school"],
    )
    assert a1 > a2 > a3
    assert (a2 - a3) < (a1 - a2), "the residual neurotype gap must be smaller than the fixable gap"


def test_pathway_attenuation_decays_monotonically_on_the_baseline_single_route(
    baseline_model: bn.RiskModel,
) -> None:
    """In the baseline the attendance chain is the only route, so decay must be monotone."""
    trace = bn.trace_pathway_attenuation(
        baseline_model, dict(bn.SCENARIOS[0][2]), dict(bn.SCENARIOS[1][2])
    )
    shifts = [abs(step["absolute_shift"]) for step in trace["steps"]]
    assert shifts == sorted(shifts, reverse=True), shifts
    assert 0.0 < trace["transmission_to_outcome"] < 1.0
    assert trace["monotone_decay"] is True
    assert trace["parallel_pathway_signals"] == []
    assert trace["n_directed_paths_first_to_last"] == 1


def test_attenuation_reports_the_parallel_route_in_the_amended_variant() -> None:
    """Amendment A5 adds a second route, so the shift GROWS at the outcome.

    Decay along a single route cannot increase, so an increase is positive evidence of a
    route outside the traced chain. The diagnostic must say so rather than presenting a
    non-monotone curve as attenuation.
    """
    amended = bn.build_model(bn.ModelVariant.AMENDED)
    trace = bn.trace_pathway_attenuation(
        amended,
        dict(bn.SCENARIOS[0][2]),
        dict(bn.SCENARIOS[1][2]),
        pathway=bn.INCLUSION_PATHWAY_VIA_ATTENDANCE,
    )
    assert trace["monotone_decay"] is False
    assert trace["parallel_pathway_signals"], "the growth step must be reported"
    assert trace["parallel_pathway_signals"][-1]["at_node"] == bn.TARGET_NODE
    assert trace["n_directed_paths_first_to_last"] > 1
    assert "GROWS" in trace["interpretation"]


def test_engagement_pathway_exists_only_in_the_amended_variant() -> None:
    """Tracing a chain that is not a directed path must fail, not return a fake curve."""
    a1, a2 = dict(bn.SCENARIOS[0][2]), dict(bn.SCENARIOS[1][2])
    with pytest.raises(ValueError, match="not a directed path"):
        bn.trace_pathway_attenuation(
            bn.build_model(bn.ModelVariant.BASELINE),
            a1,
            a2,
            pathway=bn.INCLUSION_PATHWAY_VIA_ENGAGEMENT,
        )
    trace = bn.trace_pathway_attenuation(
        bn.build_model(bn.ModelVariant.AMENDED),
        a1,
        a2,
        pathway=bn.INCLUSION_PATHWAY_VIA_ENGAGEMENT,
    )
    assert trace["shift_at_outcome"] > 0


def test_attenuation_rejects_a_degenerate_pathway(baseline_model: bn.RiskModel) -> None:
    with pytest.raises(ValueError, match="at least two nodes"):
        bn.trace_pathway_attenuation(baseline_model, {}, {}, pathway=("Sector",))


def test_amended_variant_transmits_the_accommodation_signal_better() -> None:
    """The critique's central quantitative claim, as a regression test.

    Restoring ``Support_Mismatch -> Current_Academic_Performance`` and
    ``School_Distress -> School_Engagement`` must materially increase how much of the
    accommodation contrast survives to the outcome.
    """
    a1, a2 = dict(bn.SCENARIOS[0][2]), dict(bn.SCENARIOS[1][2])
    baseline = bn.trace_pathway_attenuation(bn.build_model(bn.ModelVariant.BASELINE), a1, a2)
    amended = bn.trace_pathway_attenuation(bn.build_model(bn.ModelVariant.AMENDED), a1, a2)
    assert amended["transmission_to_outcome"] > 3 * baseline["transmission_to_outcome"]


def test_perturbation_changes_only_the_targeted_columns() -> None:
    target = bn.SENSITIVITY_TARGETS[0]
    original = {str(c.variable): c for c in bn.build_cpds(bn.ModelVariant.BASELINE)}[target.variable]
    perturbed = bn.perturb_cpd(original, target, 1.10)
    parents = [str(p) for p in original.variables[1:]]
    changed = untouched = 0
    for combo in itertools.product(*(bn.NODE_STATES[p] for p in parents)):
        assignment = dict(zip(parents, combo))
        before = original.get_value(**{target.variable: target.state, **assignment})
        after = perturbed.get_value(**{target.variable: target.state, **assignment})
        if all(assignment[k] == v for k, v in target.parent_filter.items()):
            assert after > before
            changed += 1
        else:
            assert math.isclose(after, before, rel_tol=1e-12)
            untouched += 1
    assert changed and untouched


def test_perturbation_preserves_normalisation() -> None:
    for target in bn.SENSITIVITY_TARGETS:
        original = {str(c.variable): c for c in bn.build_cpds(bn.ModelVariant.BASELINE)}[
            target.variable
        ]
        for factor in (0.90, 1.10):
            perturbed = bn.perturb_cpd(original, target, factor)
            sums = np.asarray(perturbed.get_values(), dtype=float).sum(axis=0)
            assert np.allclose(sums, 1.0, atol=1e-12)
            bn.validate_cpds([perturbed])


def test_perturbation_with_a_filter_that_matches_nothing_raises() -> None:
    bogus = bn.SensitivityTarget(
        name="bogus",
        variable="Access_Barrier",
        state="High",
        parent_filter={"Sector": "Urban"},  # not a parent of Access_Barrier
        question="should fail",
    )
    original = {str(c.variable): c for c in bn.build_cpds(bn.ModelVariant.BASELINE)}["Access_Barrier"]
    with pytest.raises(ValueError, match="non-parents"):
        bn.perturb_cpd(original, bogus, 1.10)


def test_sensitivity_analysis_reports_rank_stability(baseline_model: bn.RiskModel) -> None:
    report = bn.run_sensitivity_analysis(baseline_model)
    assert report["n_perturbations"] == 2 * len(bn.SENSITIVITY_TARGETS)
    assert len(report["baseline_ranking"]) == len(bn.SCENARIOS)
    assert report["limitations"], "the report must state what this method cannot show"
    for record in report["records"]:
        assert set(record["p_high_shift_by_scenario"]) == set(report["baseline_p_high"])
    json.dumps(report)


def test_increasing_the_attendance_weight_raises_risk_for_irregular_attenders() -> None:
    """A sanity check that the perturbation machinery moves things in the right direction."""
    target = next(
        t for t in bn.SENSITIVITY_TARGETS if t.name == "irregular_attendance_effect_on_risk"
    )
    evidence = {"Current_Attendance": "Irregular", "School_Engagement": "Low"}
    base = bn.infer_dropout_risk(bn.build_model(), evidence)["posterior"]["High"]
    up = bn.infer_dropout_risk(
        bn.build_perturbed_model(bn.ModelVariant.BASELINE, target, 1.10), evidence
    )["posterior"]["High"]
    down = bn.infer_dropout_risk(
        bn.build_perturbed_model(bn.ModelVariant.BASELINE, target, 0.90), evidence
    )["posterior"]["High"]
    assert down < base < up


# ---------------------------------------------------------------------------
# Class 3e: synthetic data hygiene
# ---------------------------------------------------------------------------


def test_synthetic_frame_is_marked_and_complete(cohort) -> None:
    assert len(cohort) == 500
    assert cohort["is_synthetic"].all()
    assert (cohort["data_class"] == "SYNTHETIC_NOT_REAL_STUDENT_DATA").all()
    assert cohort["student_id"].is_unique
    assert cohort["student_id"].str.startswith("SYNTH-").all()
    for node, states in bn.NODE_STATES.items():
        assert node in cohort.columns
        assert set(cohort[node].unique()) <= set(states), node


def test_synthetic_frame_carries_no_identifying_columns(cohort) -> None:
    forbidden = {"name", "nic", "address", "phone", "dob", "birth", "index_no", "school_name"}
    for column in cohort.columns:
        assert not any(token in column.lower() for token in forbidden), column


def test_synthetic_generation_is_reproducible(baseline_model: bn.RiskModel) -> None:
    first = bn.generate_synthetic_data(baseline_model, 200, seed=99)
    second = bn.generate_synthetic_data(baseline_model, 200, seed=99)
    assert first.equals(second)


def test_zero_records_is_rejected(baseline_model: bn.RiskModel) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        bn.generate_synthetic_data(baseline_model, 0)


def test_written_dataset_declares_its_prohibited_uses(
    baseline_model: bn.RiskModel, cohort, tmp_path: Path
) -> None:
    paths = bn.write_synthetic_dataset(cohort, baseline_model, tmp_path)
    assert paths["csv"].exists() and paths["metadata"].exists()
    assert "SYNTHETIC" in paths["csv"].name
    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    assert metadata["contains_personal_data"] is False
    assert metadata["n_records"] == len(cohort)
    assert metadata["parameter_provenance"] == bn.PRIOR_PROVENANCE
    assert any("validat" in use for use in metadata["prohibited_uses"])


def test_synthetic_marginals_track_the_model(baseline_model: bn.RiskModel, cohort) -> None:
    """Forward sampling must reproduce the model's own marginals within sampling error."""
    for node in ("Sector", "Current_Attendance", bn.TARGET_NODE):
        exact = bn.infer_dropout_risk(baseline_model, target=node)["posterior"]
        observed = cohort[node].value_counts(normalize=True).to_dict()
        for state, probability in exact.items():
            tolerance = 4.0 * math.sqrt(max(probability, 1e-6) * (1 - probability) / len(cohort))
            assert abs(observed.get(state, 0.0) - probability) < max(tolerance, 0.02), (
                f"{node}={state}: sampled {observed.get(state, 0.0):.4f} vs exact {probability:.4f}"
            )


def test_screening_burden_is_monotone_in_threshold(
    baseline_model: bn.RiskModel, cohort
) -> None:
    report = bn.estimate_screening_burden(baseline_model, cohort)
    rates = [row["flag_rate"] for row in report["thresholds"]]
    assert rates == sorted(rates, reverse=True), rates
    for row in report["thresholds"]:
        ceilings = row["precision_ceiling_by_assumed_true_rate"]
        assert all(0.0 <= v <= 1.0 for v in ceilings.values() if v is not None)
    assert "must never be reported as accuracy" in report["warning"]
    json.dumps(report)


def test_screening_burden_rejects_an_incomplete_frame(
    baseline_model: bn.RiskModel, cohort
) -> None:
    with pytest.raises(ValueError, match="missing required column"):
        bn.estimate_screening_burden(baseline_model, cohort.drop(columns=["School_Engagement"]))


# ---------------------------------------------------------------------------
# Class 3f: spec-builder input validation
# ---------------------------------------------------------------------------


def test_binary_spec_rejects_impossible_baseline() -> None:
    for baseline in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="baseline"):
            bn.BinaryLogisticCPDSpec(baseline=baseline)


def test_ordinal_spec_rejects_unordered_cutpoints() -> None:
    with pytest.raises(ValueError, match="increasing"):
        bn.OrdinalLogisticCPDSpec(cutpoints=(2.0, 1.0))


def test_spec_rejects_effects_on_a_non_parent() -> None:
    with pytest.raises(ValueError, match="non-parent"):
        bn.make_binary_cpd(
            "Access_Barrier",
            ("Transport_Burden",),
            bn.BinaryLogisticCPDSpec(baseline=0.1, effects={"Sector": {"Rural": 1.0}}),
        )


def test_spec_rejects_an_unknown_parent_state() -> None:
    with pytest.raises(ValueError, match="unknown states"):
        bn.make_binary_cpd(
            "Access_Barrier",
            ("Transport_Burden",),
            bn.BinaryLogisticCPDSpec(baseline=0.1, effects={"Transport_Burden": {"Massive": 1.0}}),
        )


def test_prior_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to"):
        bn.make_prior_cpd("Sector", (0.5, 0.4, 0.2))


def test_prior_rejects_a_zero_probability_state() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        bn.make_prior_cpd("Sector", (0.6, 0.4, 0.0))


def test_binary_helper_refuses_a_three_state_node() -> None:
    with pytest.raises(ValueError, match="requires 2"):
        bn.make_binary_cpd("Sector", (), bn.BinaryLogisticCPDSpec(baseline=0.3))


def test_validate_cpds_catches_an_unnormalised_column() -> None:
    broken = TabularCPD(
        variable="Access_Barrier",
        variable_card=2,
        values=[[0.5, 0.5], [0.4, 0.5]],
        evidence=["Transport_Burden"],
        evidence_card=[2],
        state_names={
            "Access_Barrier": list(bn.NODE_STATES["Access_Barrier"]),
            "Transport_Burden": list(bn.NODE_STATES["Transport_Burden"]),
        },
    )
    with pytest.raises(ValueError, match="sum to"):
        bn.validate_cpds([broken])


def test_validate_cpds_catches_a_deterministic_column() -> None:
    deterministic = TabularCPD(
        variable="Access_Barrier",
        variable_card=2,
        values=[[1.0, 0.5], [0.0, 0.5]],
        evidence=["Transport_Burden"],
        evidence_card=[2],
        state_names={
            "Access_Barrier": list(bn.NODE_STATES["Access_Barrier"]),
            "Transport_Burden": list(bn.NODE_STATES["Transport_Burden"]),
        },
    )
    with pytest.raises(ValueError, match="deterministic"):
        bn.validate_cpds([deterministic])
    bn.validate_cpds([deterministic], forbid_deterministic=False)  # opt-out still works


def test_structure_rejects_an_edge_to_an_unregistered_node(monkeypatch) -> None:
    monkeypatch.setattr(bn, "BASELINE_EDGES", (("Sector", "Household_Wealth_Index"),))
    with pytest.raises(ValueError, match="missing from NODE_STATES"):
        bn.build_structure()


def test_structure_rejects_a_direct_protected_edge_to_the_outcome(monkeypatch) -> None:
    monkeypatch.setattr(
        bn, "BASELINE_EDGES", bn.BASELINE_EDGES + (("Neuro_Type", bn.TARGET_NODE),)
    )
    with pytest.raises(ValueError, match="must not be direct parents"):
        bn.build_structure()


def test_structure_rejects_a_cycle(monkeypatch) -> None:
    monkeypatch.setattr(
        bn,
        "BASELINE_EDGES",
        bn.BASELINE_EDGES + (("Current_Academic_Performance", "Previous_Attendance"),),
    )
    with pytest.raises(ValueError, match="cycle"):
        bn.build_structure()


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


def test_main_runs_and_writes_all_artefacts(tmp_path: Path) -> None:
    assert bn.main(["--out-dir", str(tmp_path), "--n-records", "300", "--quiet"]) == 0
    results = json.loads((tmp_path / "analysis_results.json").read_text(encoding="utf-8"))
    assert results["check_model"] is True
    assert results["provenance"] == bn.PRIOR_PROVENANCE
    assert len(results["structure"]["edges"]) == len(bn.BASELINE_EDGES)
    for section in ("scenarios", "sensitivity", "interventions", "screening_burden",
                    "pathway_attenuation", "amended_variant", "evidence_levels"):
        assert section in results, section
    for section in ("pathway_attenuation_via_attendance", "pathway_attenuation_via_engagement"):
        assert section in results["amended_variant"], section
    csv_path = tmp_path / "synthetic_students_SYNTHETIC.csv"
    assert csv_path.exists()
    assert sum(1 for _ in csv_path.open(encoding="utf-8")) == 301  # header + rows


def test_results_bundle_is_json_native_without_a_stringifying_fallback(tmp_path: Path) -> None:
    """`main` dumps without `default=`, so a leaked numpy scalar must fail loudly.

    Without this, a numpy float64 would be silently written as the string "0.132" and
    quietly corrupt any downstream analysis of the bundle.
    """
    assert bn.main(["--out-dir", str(tmp_path), "--n-records", "200", "--quiet"]) == 0
    results = json.loads((tmp_path / "analysis_results.json").read_text(encoding="utf-8"))
    numeric_paths = [
        results["scenarios"]["results"][0]["posterior"]["High"],
        results["sensitivity"]["largest_max_abs_shift"],
        results["screening_burden"]["thresholds"][0]["flag_rate"],
        results["pathway_attenuation"]["transmission_to_outcome"],
        results["structure"]["max_cpd_columns"],
    ]
    for value in numeric_paths:
        assert isinstance(value, (int, float)) and not isinstance(value, bool), repr(value)


def test_fingerprint_distinguishes_a_relabelled_cpd(baseline_model: bn.RiskModel) -> None:
    """Identical values under a different column layout are a different model."""
    import numpy as np_

    original = baseline_model.model.get_cpds("Access_Barrier")
    parents = [str(p) for p in original.variables[1:]]
    reordered = bn._tabular_cpd(
        "Access_Barrier", list(reversed(parents)), np_.array(original.get_values(), dtype=float)
    )
    model = bn.build_structure()
    cpds = [c for c in bn.build_cpds() if str(c.variable) != "Access_Barrier"] + [reordered]
    model.add_cpds(*cpds)
    assert bn.model_fingerprint(model, bn.ModelVariant.BASELINE) != baseline_model.fingerprint

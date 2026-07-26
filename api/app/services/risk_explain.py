"""Explanation estimands for the disengagement risk screen.

This is what stands in place of SHAP, and it is a stronger claim rather than a weaker
one. Every number below is an *exact* query against the causal network -- variable
elimination on a 25-node graph, not a sampled approximation of a fitted forest -- and
each answers a different question that a teacher actually asks:

``drivers``            what is behind this number?        (observational contrast)
``action_candidates``  what would help?                   (true ``do()`` intervention)
``worth_asking``       what should I find out next?       (value of information)
``routes``             how does this reach the outcome?   (directed paths in the DAG)
``circumstance_gap``   is trouble coming that the register has not caught yet?

Two conditioning rules do the real work, and getting either wrong silently produces
confident nonsense:

1. **The register is left free.** ``Next_Term_Dropout_Risk`` has exactly three parents
   -- ``Current_Attendance``, ``Grade_Band`` and ``School_Engagement``. Condition on
   them and every other variable becomes d-separated from the outcome, so all
   contributions collapse to zero. Drivers and actions therefore never condition on
   attendance or engagement.
2. **Actions condition only on non-descendants.** Conditioning on a variable the action
   is meant to change would block its own effect. ``BACKGROUND_VARIABLES`` is computed
   from the graph rather than hardcoded, so it stays correct if the DAG changes.

Ported from the reference implementation in
``research/dropout-ews/ui/case.template.html``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

import networkx as nx

from app.risk import dropout_ews_bn as bn

TARGET = bn.TARGET_NODE
HIGH_STATE = "High"

#: Mediators the model infers rather than a school recording. Conditioning on these
#: would block the pathways an explanation is trying to show.
SIGNAL_VARIABLES: frozenset[str] = frozenset(
    {
        "Support_Mismatch",
        "School_Distress",
        "Access_Barrier",
        "Psychological_Attendance_Barrier",
        "Current_Academic_Stress",
        "Current_Academic_Performance",
    }
)

#: The three parents of the outcome plus last term's attendance.
REGISTER_VARIABLES: frozenset[str] = frozenset(
    {"Previous_Attendance", "Current_Attendance", "School_Engagement"}
)

#: A gap this large between "where the circumstances point" and "what the register
#: says" earns a "circumstances ahead" mark. From the reference tool's GAP_MARK.
GAP_MARK = 0.15

#: Band thresholds. Deliberately not a traffic light: the low band is "nothing marked",
#: never "green", because nothing here marks a student as good.
BAND_ATTENTION = 0.30


@dataclass(frozen=True)
class Contribution:
    variable: str
    state: str
    delta: float
    causal: bool


def _freeze(mapping: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((mapping or {}).items()))


class RiskExplainer:
    """Wraps a built :class:`~app.risk.dropout_ews_bn.RiskModel` with cached queries.

    Every panel on the record screen costs tens of inference calls, and the same
    background evidence recurs across all of them, so results are memoised on the
    exact (evidence, intervention) pair.
    """

    def __init__(self, risk_model: bn.RiskModel, cache_size: int = 8192) -> None:
        self.risk_model = risk_model
        graph: nx.DiGraph = risk_model.model

        modifiable = set(bn.MODIFIABLE_NODES)
        touched: set[str] = set()
        for node in modifiable:
            touched.add(node)
            touched |= nx.descendants(graph, node)
        #: Safe to condition on when estimating an intervention: neither a lever nor
        #: downstream of one.
        self.background_variables: frozenset[str] = frozenset(
            node for node in graph.nodes if node not in touched and node != TARGET
        )

        self._p_high_cached = lru_cache(maxsize=cache_size)(self._p_high_uncached)
        self._prior_high = self.p_high({})

    # -- core queries ----------------------------------------------------

    def _p_high_uncached(
        self,
        evidence: tuple[tuple[str, str], ...],
        intervention: tuple[tuple[str, str], ...],
    ) -> float:
        evidence_map = dict(evidence)
        if intervention:
            result = bn.estimate_intervention_effect(
                self.risk_model, dict(intervention), evidence_map
            )
        else:
            result = bn.infer_dropout_risk(self.risk_model, evidence_map)
        return float(result["posterior"][HIGH_STATE])

    def p_high(
        self,
        evidence: dict[str, str] | None,
        intervention: dict[str, str] | None = None,
    ) -> float:
        return self._p_high_cached(_freeze(evidence), _freeze(intervention))

    def posterior(self, evidence: dict[str, str] | None) -> dict:
        return bn.infer_dropout_risk(self.risk_model, dict(evidence or {}))

    @property
    def prior_high(self) -> float:
        """The model's unconditional P(High). Doubles as the 'watch' threshold, so the
        band means "above what you'd expect knowing nothing", not an invented cutoff."""
        return self._prior_high

    # -- conditioning sets -----------------------------------------------

    def circumstance_background(self, evidence: dict[str, str]) -> dict[str, str]:
        """Recorded evidence with the register and inferred signals removed."""
        return {
            variable: state
            for variable, state in evidence.items()
            if variable not in REGISTER_VARIABLES and variable not in SIGNAL_VARIABLES
        }

    def action_background(self, evidence: dict[str, str]) -> dict[str, str]:
        return {
            variable: state
            for variable, state in evidence.items()
            if variable in self.background_variables
        }

    def recorded_levers(self, evidence: dict[str, str]) -> dict[str, str]:
        return {
            variable: state
            for variable, state in evidence.items()
            if variable in bn.MODIFIABLE_NODES
        }

    # -- estimand 1: what is behind it -----------------------------------

    def drivers(
        self, evidence: dict[str, str], factors: dict[str, dict]
    ) -> list[Contribution]:
        """Association, not effect of acting.

        For every recorded circumstance sitting in a state of concern, the difference
        the model makes between that state and the variable's reference state, holding
        the rest of the recorded circumstances fixed and leaving the register free.
        The same estimand is used for every row, so the ranking is comparable.
        """
        background = self.circumstance_background(evidence)
        results: list[Contribution] = []
        for variable, state in background.items():
            factor = factors.get(variable)
            if factor is None:
                continue
            states = list(factor["states"])
            concern_flags = list(factor["concern"])
            if state not in states:
                continue
            if not concern_flags[states.index(state)]:
                continue
            reference = _reference_state(states, concern_flags)
            if reference is None or reference == state:
                continue

            with_concern = dict(background)
            with_concern[variable] = state
            without = dict(background)
            without[variable] = reference
            delta = self.p_high(with_concern) - self.p_high(without)
            results.append(
                Contribution(variable=variable, state=state, delta=round(delta, 6), causal=False)
            )
        results.sort(key=lambda item: item.delta, reverse=True)
        return results

    # -- estimand 2: what would help -------------------------------------

    def action_candidates(
        self, evidence: dict[str, str], factors: dict[str, dict]
    ) -> list[Contribution]:
        """True interventions.

        Baseline holds every already-recorded lever at its current value via ``do()``;
        each candidate then moves one lever to its target state. Conditioning is
        restricted to non-descendants of any lever, so an action is never asked to
        explain itself through a variable it changes.
        """
        background = self.action_background(evidence)
        levers = self.recorded_levers(evidence)
        baseline = self.p_high(background, levers) if levers else self.p_high(background)

        results: list[Contribution] = []
        for variable, factor in factors.items():
            action = factor.get("action")
            if not action or variable not in bn.MODIFIABLE_NODES:
                continue
            target_state = action["target"]
            if evidence.get(variable) == target_state:
                continue
            intervention = dict(levers)
            intervention[variable] = target_state
            delta = self.p_high(background, intervention) - baseline
            results.append(
                Contribution(
                    variable=variable,
                    state=target_state,
                    delta=round(delta, 6),
                    causal=True,
                )
            )
        results.sort(key=lambda item: item.delta)
        return results

    def plan_effect(
        self, evidence: dict[str, str], variables: Iterable[str], factors: dict[str, dict]
    ) -> dict:
        """Joint effect of acting on several levers at once.

        Reported alongside the sum of the individual effects, because the two differ --
        pathways overlap, and a plan is not the sum of its parts.
        """
        background = self.action_background(evidence)
        levers = self.recorded_levers(evidence)
        baseline = self.p_high(background, levers) if levers else self.p_high(background)

        joint = dict(levers)
        sum_of_parts = 0.0
        chosen: list[str] = []
        for variable in variables:
            # The allowlist check comes first, before any reason to skip this
            # variable: refusing to intervene on a protected characteristic is a
            # deliberate answer, not something to quietly pass over.
            if variable not in bn.MODIFIABLE_NODES:
                raise bn.NonModifiableInterventionError(
                    f"Refusing to intervene on non-modifiable variable(s) ['{variable}']. "
                    f"do() is restricted to modifiable school/household factors: "
                    f"{sorted(bn.MODIFIABLE_NODES)}. Immutable or protected characteristics "
                    f"such as {sorted(bn.PROTECTED_OR_IMMUTABLE_NODES)} are never valid "
                    f"intervention targets."
                )
            factor = factors.get(variable)
            if factor is None or not factor.get("action"):
                continue
            target_state = factor["action"]["target"]
            single = dict(levers)
            single[variable] = target_state
            sum_of_parts += self.p_high(background, single) - baseline
            joint[variable] = target_state
            chosen.append(variable)

        joint_delta = (self.p_high(background, joint) - baseline) if chosen else 0.0
        return {
            "variables": chosen,
            "baseline_p_high": round(baseline, 6),
            "planned_p_high": round(baseline + joint_delta, 6),
            "joint_delta": round(joint_delta, 6),
            "sum_of_parts": round(sum_of_parts, 6),
        }

    # -- estimand 3: what to find out next -------------------------------

    def worth_asking(
        self, evidence: dict[str, str], factors: dict[str, dict], recordable: Iterable[str]
    ) -> list[Contribution]:
        """Value of information: how far the answer could move the number.

        Uses a causal contrast for levers and an observational one otherwise, and says
        which it used, because the two are not the same claim.
        """
        background = self.circumstance_background(evidence)
        action_bg = self.action_background(evidence)
        levers = self.recorded_levers(evidence)
        results: list[Contribution] = []

        for variable in recordable:
            if variable in evidence:
                continue
            factor = factors.get(variable)
            if factor is None:
                continue
            causal = variable in bn.MODIFIABLE_NODES
            values: list[float] = []
            for state in factor["states"]:
                if causal:
                    intervention = dict(levers)
                    intervention[variable] = state
                    values.append(self.p_high(action_bg, intervention))
                else:
                    probe = dict(background)
                    probe[variable] = state
                    values.append(self.p_high(probe))
            if not values:
                continue
            swing = max(values) - min(values)
            results.append(
                Contribution(
                    variable=variable, state="", delta=round(swing, 6), causal=causal
                )
            )
        results.sort(key=lambda item: item.delta, reverse=True)
        return results

    # -- estimand 4: how it reaches the outcome --------------------------

    def routes(self, variable: str, max_depth: int = 7) -> list[list[str]]:
        """Every directed path from a variable to the outcome, shortest first."""
        graph: nx.DiGraph = self.risk_model.model
        if variable not in graph or variable == TARGET:
            return []
        paths = nx.all_simple_paths(graph, variable, TARGET, cutoff=max_depth)
        return sorted((list(path) for path in paths), key=len)

    # -- circumstance gap ------------------------------------------------

    def circumstance_gap(self, evidence: dict[str, str]) -> dict:
        """Where the circumstances point, versus what the register currently says.

        The register determines the headline number exactly. This is the only mechanism
        that surfaces a student whose situation is deteriorating before attendance and
        engagement have caught up with it.
        """
        register_score = self.p_high(evidence)
        background = self.action_background(evidence)
        levers = self.recorded_levers(evidence)
        circumstance_score = (
            self.p_high(background, levers) if levers else self.p_high(background)
        )
        gap = circumstance_score - register_score
        return {
            "register_p_high": round(register_score, 6),
            "circumstance_p_high": round(circumstance_score, 6),
            "gap": round(gap, 6),
            "ahead": gap >= GAP_MARK,
        }

    # -- banding ---------------------------------------------------------

    def band(self, p_high: float) -> tuple[str, str]:
        """Return ``(band_id, alert_tier)``.

        ``alert_tier`` maps onto the Ministry alert hierarchy in the proposal
        (Low / Moderate / High); ``band_id`` keeps the research tool's wording, which
        deliberately avoids implying that an unflagged student is "fine".
        """
        if p_high >= BAND_ATTENTION:
            return "needs_attention", "High"
        if p_high >= self.prior_high:
            return "watch", "Moderate"
        return "not_marked", "Low"


def _reference_state(states: list[str], concern_flags: list[bool]) -> str | None:
    """The first non-concern state -- the variable's "nothing wrong here" value."""
    for state, flagged in zip(states, concern_flags):
        if not flagged:
            return state
    return None

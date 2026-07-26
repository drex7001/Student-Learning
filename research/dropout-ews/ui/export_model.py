"""Export the network, a synthetic caseload, and a verification fixture for the case tool.

The case tool runs *real* inference in the browser, so this script ships the actual CPD
tables out of ``dropout_ews_bn`` rather than precomputed answers. Everything numeric comes
from the module; only the plain-language labels are authored here, and every node and every
state must have one or the build fails -- a raw identifier like
``Child_Labour_Household_Duties=High`` must never reach a caseworker's screen.

Also emits a fixture of pgmpy-computed posteriors (observational and interventional) so
``verify_infer.mjs`` can prove the JavaScript engine agrees with the library.
"""

from __future__ import annotations

import json
import random
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
# The engine now lives in the API package (api/app/risk); this directory keeps the
# research record -- REPORT.md, the generated UI, and the analysis outputs.
sys.path.insert(0, str(ROOT.parent.parent / "api"))

import pandas as pd  # noqa: E402
from pgmpy.inference import VariableElimination  # noqa: E402

from app.risk import dropout_ews_bn as m  # noqa: E402

VARIANT = m.ModelVariant.AMENDED
CASELOAD_SIZE = 240


# --------------------------------------------------------------------- authored copy

#: How each variable is named to the person using the tool. A caseworker reads
#: "Gets help with schoolwork at home", not "Home_Educational_Support".
NODE_COPY: dict[str, dict[str, str]] = {
    "Sector": {"label": "School sector", "group": "Context"},
    "Grade_Band": {"label": "Grade band", "group": "Context"},
    "Economic_Strain": {"label": "Household economic strain", "group": "Home"},
    "Parent_Education": {"label": "Parent's own schooling", "group": "Home"},
    "Parent_Availability": {"label": "Parent present at home", "group": "Home"},
    "Neuro_Type": {"label": "Neurotype", "group": "Context"},
    "Child_Labour_Household_Duties": {"label": "Work and household duties", "group": "Home"},
    "Transport_Burden": {"label": "Getting to school", "group": "Access"},
    "Food_Health_Burden": {"label": "Food and health", "group": "Home"},
    "Home_Educational_Support": {"label": "Help with schoolwork at home", "group": "Home"},
    "WASH_Quality": {"label": "School toilets and water", "group": "School"},
    "Sensory_Environment": {"label": "Classroom sensory load", "group": "School"},
    "School_Accommodation": {"label": "Learning accommodations in place", "group": "School"},
    "Bullying_Social_Exclusion": {"label": "Bullying and exclusion", "group": "School"},
    "Teacher_Resource_Adequacy": {"label": "Teaching resources", "group": "School"},
    "Support_Mismatch": {"label": "Support does not match need", "group": "Signals"},
    "School_Distress": {"label": "Distress at school", "group": "Signals"},
    "Access_Barrier": {"label": "Practical barrier to attending", "group": "Signals"},
    "Previous_Attendance": {"label": "Attendance last term", "group": "Register"},
    "Current_Academic_Performance": {"label": "Academic performance", "group": "Signals"},
    "Current_Academic_Stress": {"label": "Academic stress", "group": "Signals"},
    "Psychological_Attendance_Barrier": {"label": "Reluctance to come in", "group": "Signals"},
    "Current_Attendance": {"label": "Attendance this term", "group": "Register"},
    "School_Engagement": {"label": "Engagement at school", "group": "Register"},
    "Next_Term_Dropout_Risk": {"label": "Risk of leaving next term", "group": "Outcome"},
}

#: Plain-language state names. The "concern" flag marks the state that warrants attention,
#: which drives the profile ordering -- it is never a statement about the student.
STATE_COPY: dict[tuple[str, str], tuple[str, bool]] = {
    ("Sector", "Urban"): ("Urban", False),
    ("Sector", "Rural"): ("Rural", False),
    ("Sector", "Estate"): ("Estate", False),
    ("Grade_Band", "Primary"): ("Primary", False),
    ("Grade_Band", "Junior_Secondary"): ("Junior secondary", False),
    ("Grade_Band", "OLevel_ALevel"): ("O/A Level", False),
    ("Economic_Strain", "Low"): ("Not under strain", False),
    ("Economic_Strain", "Moderate"): ("Some strain", False),
    ("Economic_Strain", "High"): ("Under real strain", True),
    ("Parent_Education", "Low"): ("Left school early", False),
    ("Parent_Education", "Secondary"): ("Finished secondary", False),
    ("Parent_Education", "Post_Secondary"): ("Studied beyond school", False),
    ("Parent_Availability", "Available"): ("At home", False),
    ("Parent_Availability", "Limited_or_Away"): ("Away or rarely available", True),
    ("Neuro_Type", "Typical"): ("Not identified as neurodivergent", False),
    ("Neuro_Type", "ADHD"): ("ADHD", False),
    ("Neuro_Type", "ASD"): ("Autistic", False),
    ("Child_Labour_Household_Duties", "Low"): ("Little or none", False),
    ("Child_Labour_Household_Duties", "High"): ("Heavy duties or paid work", True),
    ("Transport_Burden", "Low"): ("Manageable journey", False),
    ("Transport_Burden", "High"): ("Long or costly journey", True),
    ("Food_Health_Burden", "Low"): ("No major issue", False),
    ("Food_Health_Burden", "High"): ("Going hungry or unwell", True),
    ("Home_Educational_Support", "Adequate"): ("Someone helps", False),
    ("Home_Educational_Support", "Limited"): ("Studies alone", True),
    ("WASH_Quality", "Adequate"): ("Usable", False),
    ("WASH_Quality", "Inadequate"): ("Not usable", True),
    ("Sensory_Environment", "Supportive"): ("Manageable", False),
    ("Sensory_Environment", "Overloading"): ("Overwhelming", True),
    ("School_Accommodation", "Adequate"): ("In place and working", False),
    ("School_Accommodation", "Inadequate"): ("Missing or not working", True),
    ("Bullying_Social_Exclusion", "Low"): ("None reported", False),
    ("Bullying_Social_Exclusion", "High"): ("Being bullied or left out", True),
    ("Teacher_Resource_Adequacy", "Adequate"): ("Sufficient", False),
    ("Teacher_Resource_Adequacy", "Limited"): ("Stretched", True),
    ("Support_Mismatch", "Low"): ("Support fits", False),
    ("Support_Mismatch", "High"): ("Support does not fit", True),
    ("School_Distress", "Low"): ("Settled", False),
    ("School_Distress", "High"): ("Distressed", True),
    ("Access_Barrier", "Low"): ("Can get in", False),
    ("Access_Barrier", "High"): ("Struggles to get in", True),
    ("Previous_Attendance", "Regular"): ("Regular", False),
    ("Previous_Attendance", "Irregular"): ("Irregular", True),
    ("Current_Academic_Performance", "Adequate"): ("Keeping up", False),
    ("Current_Academic_Performance", "Low"): ("Falling behind", True),
    ("Current_Academic_Stress", "Low"): ("Coping", False),
    ("Current_Academic_Stress", "High"): ("Under pressure", True),
    ("Psychological_Attendance_Barrier", "Low"): ("Willing to come", False),
    ("Psychological_Attendance_Barrier", "High"): ("Avoiding school", True),
    ("Current_Attendance", "Regular"): ("Regular", False),
    ("Current_Attendance", "Irregular"): ("Irregular", True),
    ("School_Engagement", "High"): ("Engaged", False),
    ("School_Engagement", "Low"): ("Withdrawn", True),
    ("Next_Term_Dropout_Risk", "Low"): ("Low", False),
    ("Next_Term_Dropout_Risk", "Medium"): ("Medium", False),
    ("Next_Term_Dropout_Risk", "High"): ("High", False),
}

#: For every modifiable variable: what the action is actually called, who owns it, and the
#: state it is meant to reach. ``caveat`` surfaces a known defect on the item itself, where
#: it can change a decision, rather than in a footnote nobody reads.
ACTIONS: dict[str, dict[str, str]] = {
    "School_Accommodation": {
        "action": "Put a learning accommodation plan in place",
        "owner": "Class teacher + section head",
        "target": "Adequate",
        "detail": "Written plan: seating, extra time, instructions given in writing, "
                  "a named adult to check in weekly.",
    },
    "Bullying_Social_Exclusion": {
        "action": "Open the anti-bullying and peer-inclusion protocol",
        "owner": "Section head + counsellor",
        "target": "Low",
        "detail": "Investigate, act on the behaviour of the students doing it, and build "
                  "a peer group around the student. Do not make the target change class.",
    },
    "Transport_Burden": {
        "action": "Arrange transport support",
        "owner": "Zonal welfare officer",
        "target": "Low",
        "detail": "Season ticket, shared van place, or a route change. Confirm the journey "
                  "actually works in the monsoon, not just on paper.",
    },
    "Home_Educational_Support": {
        "action": "Set up study support outside the home",
        "owner": "Class teacher",
        "target": "Adequate",
        "detail": "Supervised study hour at school, a volunteer tutor, or a take-home pack. "
                  "Do not depend on a parent who is not there.",
    },
    "Child_Labour_Household_Duties": {
        "action": "Refer household duties to welfare, with a family visit",
        "owner": "Zonal welfare officer",
        "target": "Low",
        "detail": "The duties usually exist for a reason. Address the reason — income, a "
                  "sick relative, childcare — before asking the family to change.",
    },
    "Sensory_Environment": {
        "action": "Reduce sensory load in the classroom",
        "owner": "Class teacher",
        "target": "Supportive",
        "detail": "Quieter seating, permission to leave the room, a low-stimulus space at "
                  "interval. Benefits the whole class, so needs no label on one student.",
    },
    "WASH_Quality": {
        "action": "Repair and maintain toilets and water supply",
        "owner": "Principal + zonal maintenance",
        "target": "Adequate",
        "detail": "A school-level fix, not a student-level one. Affects every student in "
                  "the building, and older girls most.",
    },
    "Teacher_Resource_Adequacy": {
        "action": "Assign teaching resources or relief staff",
        "owner": "Zonal office",
        "target": "Adequate",
        "detail": "School-level. Under-resourcing shows up as individual student risk, "
                  "which is a reason to fund the school, not to flag the child.",
    },
    "Food_Health_Burden": {
        "action": "Refer for school meals and a health check",
        "owner": "Principal + PHI",
        "target": "Low",
        "detail": "Meals and health screening are separate programmes with separate owners.",
        "caveat": "This variable bundles hunger with illness (report critique C7), so the "
                  "estimate below has no single real-world action behind it. Treat the "
                  "number as indicative only and split the referral in practice.",
    },
}

#: Why a variable that is not on the modifiable allowlist is not offered as an action.
NOT_ACTIONABLE: dict[str, str] = {
    "Neuro_Type": "A characteristic of the student, never a target. The model refuses to "
                  "estimate what would happen 'if this student were not autistic', and the "
                  "network has no direct arrow from neurotype to leaving school — only "
                  "arrows through how the school responds.",
    "Sector": "Where the school is. Changes with policy and infrastructure, not casework.",
    "Grade_Band": "The student's stage of schooling.",
    "Parent_Education": "A fact about the parent's own past. Acting on it is not possible "
                        "and treating it as a deficit is not acceptable.",
    "Economic_Strain": "Real and important, but not something a school can change directly. "
                       "It is a reason for a welfare referral, not a school intervention.",
    "Parent_Availability": "Often migration for work. The school can work around it — see "
                           "study support — but cannot change it.",
    "Support_Mismatch": "A summary of other factors, not a lever of its own. Act on the "
                        "accommodation and sensory factors that feed it.",
    "School_Distress": "A signal, not a lever. Act on its causes.",
    "Access_Barrier": "A signal, not a lever. Act on transport, duties, food and health.",
    "Psychological_Attendance_Barrier": "A signal, not a lever. Act on distress and bullying.",
    "Current_Academic_Stress": "A signal, not a lever.",
    "Current_Academic_Performance": "An outcome of support, not a lever to pull directly.",
    "Previous_Attendance": "A record of what happened. It cannot be changed, only responded to.",
    "Current_Attendance": "The thing we are trying to protect, not a lever. Marking a "
                          "student present does not keep them in school.",
    "School_Engagement": "The thing we are trying to protect, not a lever.",
}


# ------------------------------------------------------------------------- verification

risk_model = m.build_model(VARIANT)
model = risk_model.model

for node, states in m.NODE_STATES.items():
    assert node in NODE_COPY, f"no label authored for node {node}"
    for state in states:
        assert (node, state) in STATE_COPY, f"no label authored for state {node}={state}"

assert set(ACTIONS) == set(m.MODIFIABLE_NODES), (
    f"action copy out of step with MODIFIABLE_NODES\n"
    f"  missing: {sorted(m.MODIFIABLE_NODES - set(ACTIONS))}\n"
    f"  extra:   {sorted(set(ACTIONS) - m.MODIFIABLE_NODES)}"
)
for node, spec in ACTIONS.items():
    assert spec["target"] in m.NODE_STATES[node], f"{node}: bad target state {spec['target']}"

non_modifiable = set(m.NODE_STATES) - m.MODIFIABLE_NODES - {m.TARGET_NODE}
assert set(NOT_ACTIONABLE) == non_modifiable, (
    f"'not actionable' copy out of step\n"
    f"  missing: {sorted(non_modifiable - set(NOT_ACTIONABLE))}\n"
    f"  extra:   {sorted(set(NOT_ACTIONABLE) - non_modifiable)}"
)

# The ethical invariant the whole design rests on, re-checked here so the UI cannot ship
# against a model that has lost it.
assert (m.TARGET_NODE not in model.successors("Neuro_Type")), (
    "Neuro_Type has gained a direct edge to the outcome; refusing to build the UI"
)
for protected in m.PROTECTED_OR_IMMUTABLE_NODES:
    assert protected not in m.MODIFIABLE_NODES, protected

print(f"verified: labels exist for all {len(m.NODE_STATES)} nodes and "
      f"{len(STATE_COPY)} states")
print(f"verified: {len(ACTIONS)} actions cover MODIFIABLE_NODES exactly")
print("verified: no direct Neuro_Type -> outcome edge")


# ------------------------------------------------------------------------------ export

nodes = []
for name, states in m.NODE_STATES.items():
    cpd = model.get_cpds(name)
    parents = list(cpd.variables[1:])
    assert list(cpd.state_names[name]) == list(states), f"{name}: state order drift"
    for parent in parents:
        assert list(cpd.state_names[parent]) == list(m.NODE_STATES[parent]), (
            f"{name}: parent {parent} state order drift"
        )
    entry = {
        "name": name,
        "states": list(states),
        "parents": parents,
        "cpd": [round(float(v), 10) for v in cpd.values.ravel(order="C")],
        "label": NODE_COPY[name]["label"],
        "group": NODE_COPY[name]["group"],
        "stateLabels": [STATE_COPY[(name, s)][0] for s in states],
        "concern": [STATE_COPY[(name, s)][1] for s in states],
        "modifiable": name in m.MODIFIABLE_NODES,
        "protected": name in m.PROTECTED_OR_IMMUTABLE_NODES,
        "register": name in m.OBSERVABLE_AT_SCREENING,
    }
    if name in ACTIONS:
        entry["action"] = ACTIONS[name]
    if name in NOT_ACTIONABLE:
        entry["whyNotActionable"] = NOT_ACTIONABLE[name]
    nodes.append(entry)


# ---------------------------------------------------------------------------- caseload

frame = pd.read_csv(ROOT / "outputs" / "synthetic_students_SYNTHETIC.csv")
assert bool(frame["is_synthetic"].all()), "dataset is not flagged synthetic"
assert set(frame["data_class"]) == {"SYNTHETIC_NOT_REAL_STUDENT_DATA"}, "unexpected data_class"
assert set(frame["generating_model_fingerprint"]) == {
    m.build_model(m.ModelVariant.BASELINE).fingerprint
}, "caseload was generated by a different model than expected"

cohort = frame.head(CASELOAD_SIZE)
caseload = [
    {
        "id": row["student_id"],
        "values": {n: row[n] for n in m.NODE_STATES if n != m.TARGET_NODE},
        # Sampled forward from the same network. Used ONLY for the cohort-level review
        # burden figures; never shown on an individual profile, because a simulated
        # outcome on a simulated student is not a fact about anyone.
        "simulatedOutcome": row[m.TARGET_NODE],
    }
    for _, row in cohort.iterrows()
]

# The caseload is generated by the BASELINE model while the tool reasons with the AMENDED
# one. That is deliberate -- it mirrors reality, where the data is never drawn from your
# model -- but it must be stated, not hidden.
caseload_note = (
    f"{CASELOAD_SIZE} synthetic students, forward-sampled from the baseline network "
    f"(seed {m.RANDOM_SEED}). No real student data. The tool scores them with the amended "
    f"network, so the cohort is not drawn from the model doing the scoring."
)


# ------------------------------------------------------------- verification fixture

rng = random.Random(4242)
all_vars = [n for n in m.NODE_STATES if n != m.TARGET_NODE]
fixture = []


def exact(factor) -> dict[str, float]:
    """Like the module's ``_factor_to_dict`` but without its 6-decimal rounding.

    The rounding is presentational and would cap the JS comparison at ~5e-7; the fixture
    needs full precision so a real engine bug cannot hide under it. Every case below also
    asserts agreement with the module's own public API, so this stays a cross-check of the
    module rather than a second implementation of it.
    """
    values = factor.values.ravel().astype(float)
    return dict(zip(factor.state_names[m.TARGET_NODE], values / values.sum()))


def agrees(a: dict[str, float], b: dict[str, float], tol: float, what: str) -> None:
    gap = max(abs(a[s] - b[s]) for s in a)
    assert gap <= tol, f"{what}: fixture and module public API differ by {gap:.3e}"


for _ in range(60):
    k = rng.randint(0, 8)
    chosen = rng.sample(all_vars, k)
    evidence = {v: rng.choice(m.NODE_STATES[v]) for v in chosen}
    posterior = exact(
        risk_model.engine.query(
            variables=[m.TARGET_NODE], evidence=evidence or None, show_progress=False
        )
    )
    agrees(posterior, m.infer_dropout_risk(risk_model, evidence)["posterior"], 5e-7, "observe")
    fixture.append({"kind": "observe", "evidence": evidence, "posterior": posterior})

modifiable = sorted(m.MODIFIABLE_NODES)
for _ in range(40):
    n_do = rng.randint(1, 3)
    do_vars = rng.sample(modifiable, n_do)
    intervention = {v: rng.choice(m.NODE_STATES[v]) for v in do_vars}
    pool = [v for v in all_vars if v not in intervention]
    chosen = rng.sample(pool, rng.randint(0, 5))
    evidence = {v: rng.choice(m.NODE_STATES[v]) for v in chosen}
    mutilated = risk_model.model.do(list(intervention))
    posterior = exact(
        VariableElimination(mutilated).query(
            variables=[m.TARGET_NODE],
            evidence={**intervention, **evidence},
            show_progress=False,
        )
    )
    agrees(
        posterior,
        m.estimate_intervention_effect(risk_model, intervention, evidence)["posterior"],
        5e-7,
        "do",
    )
    fixture.append({
        "kind": "do",
        "intervention": intervention,
        "evidence": evidence,
        "posterior": posterior,
    })

print("verified: fixture agrees with the module's public API to 5e-7 on all 100 cases")

print(f"fixture: {sum(f['kind'] == 'observe' for f in fixture)} observational + "
      f"{sum(f['kind'] == 'do' for f in fixture)} interventional cases")


payload = {
    "meta": {
        "target": m.TARGET_NODE,
        "targetStates": list(m.NODE_STATES[m.TARGET_NODE]),
        "variant": VARIANT.value,
        "fingerprint": risk_model.fingerprint,
        "seed": m.RANDOM_SEED,
        "provenance": m.PRIOR_PROVENANCE,
        "syntheticBanner": m.SYNTHETIC_BANNER,
        "caseloadNote": caseload_note,
        "registerFields": list(m.OBSERVABLE_AT_SCREENING),
        "guardrailMessage": (
            "Refusing to intervene on a protected or immutable characteristic. "
            "do() is restricted to modifiable school and household factors. Immutable or "
            "protected characteristics such as neurotype are never valid intervention "
            "targets."
        ),
        "caveat": (
            "Decision-support only. Not a diagnosis, not a prediction about this "
            "individual, and not a basis for any automated action. Requires human review."
        ),
    },
    "nodes": nodes,
    "caseload": caseload,
    "fixture": fixture,
}

out_path = Path(sys.argv[1])
out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)  "
      f"nodes={len(nodes)} caseload={len(caseload)} fixture={len(fixture)}")

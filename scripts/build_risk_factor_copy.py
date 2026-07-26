"""Build `data/seeds/risk_factor_copy.json` from the exported model.

The English plain-language copy is authored once, in
`research/dropout-ews/ui/export_model.py`, and asserted there to cover every node and
every state. This script lifts it out of the exported `case_data.json` and merges in the
Sinhala translations below, so the same fact is never authored in two places.

Run after regenerating the model export:

    .venv\\Scripts\\python.exe scripts\\build_risk_factor_copy.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASE_DATA = ROOT / "research" / "dropout-ews" / "ui" / "case_data.json"
OUT = ROOT / "data" / "seeds" / "risk_factor_copy.json"

LABEL_SI: dict[str, str] = {
    "Sector": "පාසල් අංශය",
    "Grade_Band": "ශ්‍රේණි කාණ්ඩය",
    "Economic_Strain": "ගෘහ ආර්ථික පීඩනය",
    "Parent_Education": "දෙමාපියන්ගේ අධ්‍යාපනය",
    "Parent_Availability": "දෙමාපියන් නිවසේ සිටීම",
    "Neuro_Type": "ස්නායු වර්ගය",
    "Child_Labour_Household_Duties": "රැකියා හා ගෘහ කටයුතු",
    "Transport_Burden": "පාසලට පැමිණීමේ පහසුව",
    "Food_Health_Burden": "ආහාර හා සෞඛ්‍යය",
    "Home_Educational_Support": "නිවසේ පාඩම් සඳහා සහාය",
    "WASH_Quality": "පාසල් වැසිකිළි හා ජලය",
    "Sensory_Environment": "පන්ති කාමරයේ සංවේදී බර",
    "School_Accommodation": "ඉගෙනුම් පහසුකම් සකසා තිබීම",
    "Bullying_Social_Exclusion": "හිරිහැර හා කොන් කිරීම",
    "Teacher_Resource_Adequacy": "ඉගැන්වීම් සම්පත්",
    "Support_Mismatch": "සහාය අවශ්‍යතාවයට නොගැලපීම",
    "School_Distress": "පාසලේ පීඩනය",
    "Access_Barrier": "පැමිණීමට ඇති ප්‍රායෝගික බාධාව",
    "Previous_Attendance": "පසුගිය වාරයේ පැමිණීම",
    "Current_Academic_Performance": "අධ්‍යයන කාර්යසාධනය",
    "Current_Academic_Stress": "අධ්‍යයන ආතතිය",
    "Psychological_Attendance_Barrier": "පාසලට පැමිණීමට මැලිකම",
    "Current_Attendance": "මෙම වාරයේ පැමිණීම",
    "School_Engagement": "පාසලේ නිරත වීම",
    "Next_Term_Dropout_Risk": "ඊළඟ වාරයේ පාසල හැර යාමේ අවදානම",
}

STATE_LABEL_SI: dict[str, list[str]] = {
    "Sector": ["නාගරික", "ග්‍රාමීය", "වතු"],
    "Grade_Band": ["ප්‍රාථමික", "කනිෂ්ඨ ද්විතීයික", "සා.පෙළ / උ.පෙළ"],
    "Economic_Strain": ["පීඩනයක් නැත", "යම් පීඩනයක්", "දැඩි පීඩනයක්"],
    "Parent_Education": ["පාසල අඩාළ විය", "ද්විතීයික අවසන් කළා", "පාසලෙන් ඔබ්බට"],
    "Parent_Availability": ["නිවසේ සිටී", "ඈත් වී හෝ කලාතුරකින්"],
    "Neuro_Type": ["ස්නායු විවිධත්වයක් හඳුනාගෙන නැත", "ADHD", "ඔටිසම්"],
    "Child_Labour_Household_Duties": ["ඉතා අඩුයි", "බර වැඩ හෝ ගෙවන රැකියාවක්"],
    "Transport_Burden": ["ගමන පහසුයි", "දිගු හෝ මිල අධික ගමනක්"],
    "Food_Health_Burden": ["විශේෂ ගැටලුවක් නැත", "කුසගින්න හෝ අසනීප"],
    "Home_Educational_Support": ["කවුරුන් හෝ උදව් කරයි", "තනිවම ඉගෙන ගනී"],
    "WASH_Quality": ["භාවිතයට සුදුසුයි", "භාවිතයට නුසුදුසුයි"],
    "Sensory_Environment": ["දරාගත හැකියි", "අධික ලෙස බර"],
    "School_Accommodation": ["සකසා ඇත, ක්‍රියාත්මකයි", "නොමැත හෝ ක්‍රියා නොකරයි"],
    "Bullying_Social_Exclusion": ["වාර්තා වී නැත", "හිරිහැර හෝ කොන් කිරීම්"],
    "Teacher_Resource_Adequacy": ["ප්‍රමාණවත්", "අඩුපාඩු සහිතයි"],
    "Support_Mismatch": ["සහාය ගැලපේ", "සහාය නොගැලපේ"],
    "School_Distress": ["සන්සුන්", "පීඩනයෙන්"],
    "Access_Barrier": ["පැමිණිය හැක", "පැමිණීම අපහසුයි"],
    "Previous_Attendance": ["නිතිපතා", "අක්‍රමවත්"],
    "Current_Academic_Performance": ["ගැලපෙමින් යයි", "පසුබසිමින්"],
    "Current_Academic_Stress": ["මුහුණ දෙයි", "පීඩනය යටතේ"],
    "Psychological_Attendance_Barrier": ["පැමිණීමට කැමතියි", "පාසල මඟහරියි"],
    "Current_Attendance": ["නිතිපතා", "අක්‍රමවත්"],
    "School_Engagement": ["නිරතයි", "ඉවත් වී"],
    "Next_Term_Dropout_Risk": ["අඩු", "මධ්‍යම", "ඉහළ"],
}

GROUP_SI = {
    "Context": "පසුබිම",
    "Home": "නිවස",
    "Access": "ප්‍රවේශය",
    "School": "පාසල",
    "Signals": "ලකුණු",
    "Register": "පැමිණීම් ලේඛනය",
    "Outcome": "ප්‍රතිඵලය",
}

ACTION_SI: dict[str, str] = {
    "Child_Labour_Household_Duties": "ගෘහ කටයුතු සුබසාධන අංශයට යොමු කර පවුල හමුවන්න",
    "Transport_Burden": "ප්‍රවාහන සහාය සකසන්න",
    "Food_Health_Burden": "පාසල් ආහාර හා සෞඛ්‍ය පරීක්ෂාවට යොමු කරන්න",
    "Home_Educational_Support": "නිවසින් පිටත පාඩම් සහාය සකසන්න",
    "WASH_Quality": "වැසිකිළි හා ජල සැපයුම අලුත්වැඩියා කර නඩත්තු කරන්න",
    "Sensory_Environment": "පන්ති කාමරයේ සංවේදී බර අඩු කරන්න",
    "School_Accommodation": "ඉගෙනුම් පහසුකම් සැලැස්මක් සකසන්න",
    "Bullying_Social_Exclusion": "හිරිහැර වැළැක්වීමේ ක්‍රියාපටිපාටිය ආරම්භ කරන්න",
    "Teacher_Resource_Adequacy": "ඉගැන්වීම් සම්පත් හෝ සහාය කාර්ය මණ්ඩලය වෙන් කරන්න",
}


def main() -> int:
    data = json.loads(CASE_DATA.read_text(encoding="utf-8"))
    factors = []
    for node in data["nodes"]:
        name = node["name"]
        states = node["states"]
        si_states = STATE_LABEL_SI.get(name, [])
        if len(si_states) != len(states):
            raise SystemExit(f"Sinhala state labels missing or wrong length for {name}")
        if name not in LABEL_SI:
            raise SystemExit(f"Sinhala label missing for {name}")

        factor = {
            "id": name,
            "label": node["label"],
            "label_si": LABEL_SI[name],
            "group": node["group"],
            "group_si": GROUP_SI[node["group"]],
            "states": states,
            "state_labels": node["stateLabels"],
            "state_labels_si": si_states,
            "concern": node["concern"],
            "modifiable": node["modifiable"],
            "protected": node["protected"],
            "register": node.get("register", False),
        }
        if node.get("action"):
            action = dict(node["action"])
            action["action_si"] = ACTION_SI.get(name, "")
            factor["action"] = action
        if node.get("whyNotActionable"):
            factor["why_not_actionable"] = node["whyNotActionable"]
        factors.append(factor)

    payload = {
        "source": "research/dropout-ews/ui/export_model.py via scripts/build_risk_factor_copy.py",
        "model_variant": data["meta"]["variant"],
        "model_fingerprint": data["meta"]["fingerprint"],
        "provenance": data["meta"]["provenance"],
        "guardrail_message": data["meta"]["guardrailMessage"],
        "register_fields": data["meta"]["registerFields"],
        "target": data["meta"]["target"],
        "target_states": data["meta"]["targetStates"],
        "factors": factors,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(factors)} factors, {OUT.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# AI සන්දර්භය සහ මාර්ගෝපදේශ (AI Context Guide)

මෙම කේත ගබඩාවේ (Codebase) වෙනසක් කරන ඕනෑම කෙනෙකුට (මිනිසෙකුට හෝ AI නියෝජිතයෙකුට) ඉතා ඉක්මනින් පද්ධතිය අවබෝධ කරගැනීම සඳහා මෙම ලේඛනය සකසා ඇත. සම්පූර්ණ විස්තරය සඳහා `docs/si/architecture.md` කියවන්න.

## මෙය කුමක්ද? (What this is)

ශ්‍රී ලාංකීය පාසල් සඳහා වූ පූර්ව උපකාරක සහ ඉගෙනුම් බුද්ධි පද්ධතියකි (R26-IT-165, Component 3). මෙහි ප්‍රධාන එන්ජින් දෙකක් හිතාමතාම වෙන් කර ඇත:

- **පාසල් හැරයාමේ අවදානම (Disengagement risk)** — `api/app/risk/` හි ඇති Discrete Bayesian Network එකකි. ඊළඟ වාරයේදී ළමයෙකු පාසල අතහැර යාමට ඇති අවදානම සහ ඊට වඩා වැදගත් ලෙස, එම තත්ත්වය වෙනස් කරන්නේ කෙසේද යන්න මෙයින් ගණනය කරයි. මෙය ගුරුවරුන්ට සහ උපදේශකයන්ට පමණි.
- **අධ්‍යාපනික සහාය (Academic support)** — `api/app/services/diagnosis.py` හි ඇති අනුප්‍රාප්තික ප්‍රස්ථාර රෝග විනිශ්චයයි (Prerequisite-graph diagnosis). යම් විෂයයක් සඳහා කුමන සිසුන්ට ඉගැන්වීමේ අවධානය අවශ්‍යද සහ ඒ ඇයිද යන්න මෙයින් කියැවේ. ශිෂ්‍යයාට පෙනෙන ඉගෙනුම් ද්වාරය (Learning portal) ධාවනය කරන්නේද මෙය මඟිනි.

කරුණාකර මෙම වචන මාලාවන් එකට පටලවා නොගන්න. ගණිතයෙන් දුර්වල වූ සිසුවෙකු යනු පාසල හැර යන සිසුවෙකු නොවේ!

## කිසිසේත් වෙනස් කළ නොහැකි නීති (Rules that are not negotiable)

මෙම නීති කේතයෙන්ම තහවුරු කර ඇති අතර ඒ සඳහා පරීක්ෂණ (Tests) ලියා ඇත. යම් වෙනසක් කිරීමේදී පරීක්ෂණයක් අසමත් වුවහොත්, වැරැද්ද ඇත්තේ ඔබේ වෙනසේ මිස පරීක්ෂණයේ නොවේ.

1. **සිසුන්ට ඔවුන්ගේ අවදානම් ලකුණු (Risk Score) කිසිවිටෙකත් නොපෙන්වයි.** `app/core/deps.py` හි `deny_students` මඟින් මෙය තහවුරු කෙරේ.
2. **`do()` යනු අවසර ලත් ලැයිස්තුවකි (Allowlist).** ආරක්ෂිත හෝ වෙනස් කළ නොහැකි (Protected/Immutable) ලක්ෂණයක් මත මැදිහත් වීමට (Intervene) උත්සාහ කළහොත් 403 දෝෂයක් ලැබේ. `research/dropout-ews/REPORT.md` හි 8 වන ඡේදය නොකියවා කිසිවිටෙක `MODIFIABLE_NODES` ලැයිස්තුවට අලුත් දේවල් එකතු නොකරන්න.
3. **ප්‍රභවය (Provenance) සැමවිටම අගය සමඟ ගමන් කරයි.** ප්‍රතිචාරයක් යැවීමේදී `provenance`, `caveat`, `interpretation`, `model_variant`, සහ `model_fingerprint` අනිවාර්ය වේ.
4. **ප්‍රධාන හේතු (Drivers) සහ ක්‍රියාමාර්ග (Actions) කිසිවිටෙකත් පැමිණීමේ ලේඛනය (Register) මත රඳා නොපවතී (Condition නොකරයි).** 
5. **ක්‍රියාමාර්ග (Actions) රඳා පවතින්නේ මැදිහත්වීමකට යටත් නොවන (Non-descendants) සාධක මත පමණි.** මෙය ප්‍රස්ථාරයෙන්ම (Graph) ගණනය කරන අතර, hardcode කර නොමැත.
6. **කිසිම අමු හැඳුනුම්කාරකයක් (Raw Identifier) තිරයට නොයයි.** ලේබල් පැමිණෙන්නේ `data/seeds/risk_factor_copy.json` වලිනි. මෙය ආකෘතියෙන් (Model) වෙනස් වුවහොත් පරීක්ෂණ අසමත් වේ.
7. **සෑම අනතුරු ඇඟවීමක්ම (Flag) උදව්වක් සඳහාම පමණි.** කිසිම දඬුවම් කිරීමක්, පන්තියෙන් ඉවත් කිරීමක්, ස්ථිර සටහනක් දැමීමක් මෙයින් සිදු නොවේ.

## ගොනු පිහිටා ඇති ස්ථාන (Where things live)

| අදාළ අංශය (Concern) | ලිපිගොනුව (File) |
|---|---|
| Bayesian Network (බේසියානු ජාලය) | `api/app/risk/dropout_ews_bn.py` |
| පැහැදිලි කිරීම් සහ ගණනය කිරීම් (Explanation estimands) | `api/app/services/risk_explain.py` |
| අවදානම් තොරතුරු සකස් කිරීම | `api/app/services/dropout_risk.py` |
| දත්ත ජනනය කිරීම (Seed roster and evidence) | `api/app/services/school_seed.py` |
| Graph Projection | `api/app/services/graph_projection.py` |
| ප්‍රවේශ නීති (Access rules) | `api/app/core/deps.py` |
| Cypher Queries | `api/app/repositories/graph_repository.py` |
| Risk API Endpoints | `api/app/routers/risk.py`, `graph.py` |
| වර්ණ සහ මෝස්තර (Design tokens) | `web/src/app/globals.css` |
| API Client | `web/src/lib/api.ts`, `web/src/lib/types.ts` |
| සිසුන්ගේ වාර්තා පිටුව | `web/src/app/teacher/students/[id]/page.tsx` |
| පර්යේෂණ වාර්තා (Research record) | `research/dropout-ews/` |

## දත්ත ආකෘති සටහන් (Data model notes)

- `student_risk_evidence` වගුව ජාලයේ හැඩයම අනුගමනය කරයි: එක් පේළියකට `(student, term, variable, state)`. මෙහි යම් පේළියක් **නොමැති වීමෙන්** අදහස් වන්නේ "දත්ත වාර්තා වී නැත" (Not recorded) යන්නයි. එය පද්ධතියට වැදගත් තත්ත්වයක් මිස පුරවා ගත යුතු හිඩැසක් (Impute) නොවේ.
- සංකල්ප ID (Concept IDs) විශ්වීයව අනන්‍ය වන අතර ඒවාට විෂය ප්‍රත්‍යයක් ඇත (`MATH-`, `SCI-`, ආදී).
- Neo4j යනු ව්‍යුත්පන්න දසුනකි (Derived view). එය නැවත සැකසීමට `POST /internal/project/graph` භාවිතා කරන්න. කවදාවත් Neo4j වෙත සෘජුවම දත්ත ඇතුළත් නොකරන්න.

## UI වචන භාවිතයේ නීති (UI copy rules)

**ගුරුවරුන් සඳහා:** learner (ඉගෙන ගන්නා), subject (විෂය), concept (සංකල්පය), support (සහාය), readiness (සූදානම), prerequisite (පූර්ව අවශ්‍යතාව), root cause (මූලික හේතුව), offer of support (උදව් ලබා දීම) යන වචන භාවිතා කරන්න.

**අවදානම් දර්ශකය සඳහා:** ලියා ඇති පිටපත (Authored copy) පමණක් භාවිතා කරන්න. මෙය *එකම පැමිණීමේ රටාවක් ඇති සිසුන්ගේ ප්‍රතිශතයක්* ලෙස සලකන්න මිසක්, ඉදිරියේ සිටින දරුවා ගැන ඍජු අනාවැකියක් ලෙස නොවේ.

**කිසිවිටෙකත් මෙලෙස නොලියන්න:** "AI detects student distress" (AI විසින් සිසුවාගේ පීඩනය හඳුනාගනී), "at-risk student" (අවදානම් සිසුවා) යැයි පුද්ගලයෙකුට ලේබල් ගැසීම, හෝ සලකුණු නොකළ සිසුවෙකුට "කිසිම ප්‍රශ්නයක් නෑ" යැයි පැවසීම (Low යනු "සලකුණු කළ කිසිවක් නැත" යන්න පමණි).

## පරීක්ෂණ (Checks)

```powershell
cd api;  ..\.venv\Scripts\python.exe -m pytest
cd web;  npm run lint;  npm run build
```

`api/app/db/models.py` හි යම් වෙනසක් කළ පසු, `-Recreate` සමඟ නැවත දත්ත ජනනය කරන්න. API මඟින් වගු නිර්මාණය කළත් ඒවා Alter කරන්නේ නැත.

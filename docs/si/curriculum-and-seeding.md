# විෂය නිර්දේශය සහ දත්ත ජනනය කිරීම (Curriculum And Seeding)

දැනට භාවිතා වන විෂය නිර්දේශ දත්ත ශ්‍රී ලංකාවේ සාමාන්‍ය පෙළ (O/L) දත්තවල මූලාකෘතියක් පමණක් වන අතර, එය නිල විෂය නිර්දේශයේ සම්පූර්ණ දත්ත ලෙස නොසලකන්න.

## සහාය දක්වන V1 විෂයයන් (Supported V1 Subjects)

- `OL-MATH`: ගණිතය (Mathematics)
- `OL-SCI`: විද්‍යාව (Science)
- `OL-ENG`: ඉංග්‍රීසි (English)
- `OL-ICT`: තොරතුරු හා සන්නිවේදන තාක්ෂණය (ICT)

සෑම විෂයයකටම ඉංග්‍රීසි සහ සිංහල භාෂා දෙකෙන්ම පෙන්විය හැකි ක්ෂේත්‍ර (Display fields) ඇත. UI එක තුළ දත්ත ඇති තැන්වල සිංහලෙන් පෙන්වන අතර, දත්ත නොමැති විට ඉංග්‍රීසි භාෂාවට මාරු වේ (Fallback to English).

## විෂය නිර්දේශ ගොනුව (Curriculum File)

ප්‍රධාන ගොනුව:

```text
data/curriculum/ol_subject_curriculum.json
```

ඉහළ මට්ටමේ ව්‍යුහය (Top-level shape):

```json
{
  "scope": {},
  "subjects": [],
  "concepts": [],
  "edges": []
}
```

විෂය ක්ෂේත්‍ර (Subject fields):

- `id`: `OL-MATH` වැනි වෙනස් නොවන හැඳුනුම්කාරකයක්
- `name`: ඉංග්‍රීසි ප්‍රදර්ශන නම
- `name_si`: සිංහල ප්‍රදර්ශන නම
- `description`: ඉංග්‍රීසි විස්තරය
- `description_si`: සිංහල විස්තරය
- `default_concept_id`: විෂයය විවෘත කළ විට පෙන්වන පෙරනිමි පාඩම/සංකල්පය (Default concept)

සංකල්ප ක්ෂේත්‍ර (Concept fields):

- `id`: `MATH-010` වැනි විශ්වීයව අනන්‍ය වූ සංකල්ප හැඳුනුම්කාරකයක්
- `subject_id`: අයිති විෂයය
- `name`
- `name_si`
- `description`
- `description_si`

සම්බන්ධතා (Edges):

- සෑම edge එකක්ම `[source_concept_id, target_concept_id]` ලෙස පවතී.
- මෙයින් අදහස් වන්නේ `source REQUIRED_FOR target` (ඉලක්ක පාඩමට ප්‍රභව පාඩම අත්‍යවශ්‍ය වේ) යන්නයි.
- විෂයයන් හරහා යන (Cross-subject) edges ප්‍රතික්ෂේප කෙරේ.

## වලංගුතා නීති (Validation Rules)

`api/app/services/curriculum_service.py` පහත කරුණු වලංගු කරයි:

- අවම වශයෙන් එක් විෂයයක් හෝ පවතින බව
- සෑම සංකල්පයක්ම දන්නා විෂයයකට අයත් බව
- සෑම විෂයයකටම සංකල්ප 8 සිට 30 දක්වා ඇති බව
- සෑම edge එකක්ම පවතින සංකල්ප වලට සම්බන්ධ වන බව
- සෑම edge එකක්ම එක් විෂයයක් ඇතුළත පමණක් පවතින බව
- සෑම විෂයයකම ප්‍රස්ථාරය චක්‍රීය නොවන (Acyclic) බව

## කෘතිම දත්ත (Synthetic Data)

කෘතිම දත්ත ජනනය කිරීම පහත ගොනුවෙන් වින්‍යාස (Configure) කර ඇත:

```text
data/seeds/generator_config.json
```

වැදගත් ක්ෂේත්‍ර:

- `seed`: නියත අහඹු අංකය (Deterministic random seed)
- `student_count`: ජනනය කරන සිසුන් ගණන
- `assessment_attempts`: එක් සිසුවෙකුට ඇති පරීක්ෂණ වාර ගණන
- `cohorts`: පන්ති ලේබල්
- `weakness_profiles`: තාත්වික දුර්වලතා ඇති කිරීමට භාවිතා කරන මූලික සංකල්ප හිඩැස් (Root concept gaps)

ජනක යන්ත්‍රය (Generator) සෑම සංකල්පයක් සඳහාම එක් ප්‍රශ්නයක් ජනනය කරයි. එක් සිසුවෙකුට සහ පරීක්ෂණ වාරයකට අදාළව මෙය ජනනය කරන්නේ:

- එක් පරීක්ෂණ පේළියක් (Assessment row)
- එක් සංකල්පයකට එක් ප්‍රශ්න ප්‍රතිඵලයක්
- එක් සංකල්පයකට එක් ලකුණක් (Concept score)

දුර්වලතා සෑම මූලික සංකල්පයකින්ම (Root concept) එහි අනුප්‍රාප්තික සංකල්ප (Descendants) වෙත ව්‍යාප්ත වේ. මෙය සෑම විෂයයක් සඳහාම පූර්ව අවශ්‍යතා රෝග විනිශ්චය (Prerequisite diagnosis) අර්ථවත් කරයි.

## නව විෂයයක් එකතු කිරීම (Adding A Subject)

1. `subjects` වෙත නව විෂයයක් එකතු කරන්න.
2. නව `subject_id` සමඟ සංකල්ප 8 සිට 30 දක්වා ප්‍රමාණයක් එකතු කරන්න.
3. විෂයය ඇතුළත පවතින පූර්ව අවශ්‍යතා සම්බන්ධතා (Prerequisite edges) එකතු කරන්න.
4. `data/seeds/generator_config.json` හි අඩුම තරමින් එක් weakness profile root concept එකක්වත් එකතු කරන්න.
5. Backend පරීක්ෂණ (Tests) ධාවනය කරන්න.
6. Curriculum import කර, කෘතිම දත්ත නැවත ජනනය කරන්න.

නිර්දේශිත විධාන (Recommended commands):

```powershell
cd api
$env:PYTHONPATH='.'
pytest
cd ..
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/import/curriculum
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/generate/synthetic-data -ContentType 'application/json' -Body '{}'
```

## පවතින සංකල්ප සංස්කරණය කිරීම (Editing Existing Concepts)

ආරක්ෂිත වෙනස්කම්:

- ප්‍රදර්ශන නම් (Display names)
- විස්තර (Descriptions)
- සිංහල ක්ෂේත්‍ර (Sinhala fields)
- විෂයයක පෙරනිමි සංකල්පය (Default concept)

අවදානම් සහගත වෙනස්කම්:

- සංකල්ප ID (Concept IDs) වෙනස් කිරීම (කෘතිම දත්ත සහ URLs ඒවා භාවිතා කළ හැකි බැවින්)
- Edges වෙනස් කිරීම (රෝග විනිශ්චය මාර්ග සහ මූලික හේතු ශ්‍රේණිගත කිරීම් වෙනස් වන බැවින්)
- සංකල්ප ඉවත් කිරීම (ජනනය කරන ලද දත්ත සහ පරීක්ෂණ යාවත්කාලීන කිරීමට අවශ්‍ය විය හැකි බැවින්)

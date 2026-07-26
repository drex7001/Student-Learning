# ස්ථාපනය සහ වින්‍යාස කිරීම (Setup And Configuration)

## පූර්ව අවශ්‍යතා (Prerequisites)

- Docker සහ Docker Compose
- Docker වලින් පිටත ධාවනය කරන්නේ නම් Node.js 22 සහ Python 3.12

## සම්පූර්ණ පද්ධතියම ධාවනය කිරීම (Full stack)

```powershell
Copy-Item .env.example .env
docker compose up --build -d
.\scripts\reset-and-seed.ps1
```

ආදර්ශ දත්ත ජනනය කරන (seed) script එක මඟින් පරීක්ෂා කිරීම සඳහා අවශ්‍ය ගිණුම් විස්තර තිරයේ පෙන්වනු ඇත. ඒ සියල්ල සඳහාම මුරපදය (password) වන්නේ `wellbeing2026` ය.

| සේවාව (Service) | ලිපිනය (URL) |
|---|---|
| යෙදුම (Application - Frontend) | http://localhost:3000 |
| API (Backend) | http://localhost:8000 |
| API ලියකියවිලි (API docs) | http://localhost:8000/docs |
| Neo4j බ්‍රවුසරය | http://localhost:7474 |
| PostgreSQL | localhost:5432 |

## පාරිසරික විචල්‍යයන් (Environment Variables)

| විචල්‍යය (Variable) | අරමුණ (Purpose) | පෙරනිමි අගය (Default) |
|---|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | PostgreSQL පිවිසුම් තොරතුරු | `kgis` |
| `DATABASE_URL` | SQLAlchemy URL | `postgresql+psycopg://kgis:kgis@postgres:5432/kgis` |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Neo4j සබැඳුම් තොරතුරු | `bolt://neo4j:7687`, `neo4j`, `knowledge-graph-secret` |
| `API_ORIGIN` | Next විසින් `/api/*` නැවත යොමු කරන (rewrite) ස්ථානය | `http://api:8000` |
| `JWT_SECRET` | Session අත්සන් කිරීමේ යතුර | සකසා නොමැති නම් සෑම ආරම්භයකදීම අලුතින් ජනනය වේ — **නැවත ආරම්භ කළ (restart) විට sessions අහිමි වේ** |
| `RISK_MODEL_VARIANT` | `amended` (සංශෝධිත) හෝ `baseline` (මූලික) | `amended` |
| `CORS_ORIGINS` | සෘජු API ඇමතුම් සඳහා අවසර ලත් මූලයන් (Origins) | `http://localhost:3000,http://127.0.0.1:3000` |

බ්‍රවුසරය කිසිවිටෙකත් වෙනත් මූලයකින් (cross-origin) API වෙත කතා නොකරයි: එය තමන්ගේම මූලයේ (origin) ඇති `/api/*` වෙත කතා කරන අතර Next විසින් එය API එක වෙත යොමු කරයි (rewrite). එමඟින් session cookie එක ප්‍රථම පාර්ශ්වීය (first-party) වන අතර API ඉලක්කය ගොඩනඟන වෙලාවේ (build time) නොව ඉල්ලුම් කරන වෙලාවේ (request time) කියවීම තහවුරු කරයි.

## දේශීය සංවර්ධනය (Local development)

Databases පමණක් Docker තුළ ධාවනය කර යෙදුම් (apps) දෙක පරිගණකයේ ධාවනය කිරීම:

```powershell
docker compose up -d postgres neo4j

# API
cd api
$env:DATABASE_URL='postgresql+psycopg://kgis:kgis@localhost:5432/kgis'
$env:NEO4J_URI='bolt://localhost:7687'
$env:JWT_SECRET='dev-secret'
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Frontend
cd web
npm run dev
```

**`127.0.0.1` නොව `http://localhost:3000` භාවිතා කරන්න.** Next dev සේවාදායකය (server) තමන්ගේම dev සම්පත් වෙත cross-origin ඉල්ලීම් අවහිර කරයි. dev සේවාදායකය බලාපොරොත්තු වන host එකට වඩා වෙනත් host එකකින් යෙදුම බ්‍රවුස් කිරීමෙන් hydration එක නිහඬවම වළක්වයි — එවිට React handlers සම්බන්ධ නොවන අතර කිසිදු පෙනෙන හේතුවක් නොමැතිව පිටුව කැඩී ඇති සේ දිස්වේ.

### Python පරිසරය (Python environment)

පද්ධතියේ හෝ Anaconda හි Python භාවිතා නොකරන්න, ව්‍යාපෘතිය සඳහාම වූ virtualenv එක භාවිතා කරන්න:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api\requirements.txt -r api\requirements-dev.txt
```

## පරීක්ෂණ (Checks)

```powershell
cd api
..\.venv\Scripts\python.exe -m pytest     # 206 tests, incl. the 133 model tests

cd ..\web
npm run lint
npm run build
```

`api/pyproject.toml` මඟින් `pythonpath` සකසන බැවින්, තවදුරටත් අතින් `PYTHONPATH` සැකසීමට අවශ්‍ය නොවේ.

## නැවත දත්ත ජනනය කිරීම (Reseeding)

```powershell
# ව්‍යුහය (schema) රඳවා ගෙන, දත්ත පමණක් ප්‍රතිස්ථාපනය කරන්න (administrator පිවිසුමක් අවශ්‍ය වේ)
.\scripts\reset-and-seed.ps1 -SkipBuild -AdminUser <principal-username>

# ආකෘතියේ (model) වෙනසකට පසු: ව්‍යුහය ඉවත් කර මුලින්ම නැවත ගොඩනඟන්න
.\scripts\reset-and-seed.ps1 -Recreate
```

`api/app/db/models.py` හි ඕනෑම වෙනසකට පසු `-Recreate` අවශ්‍ය වේ. API ආරම්භයේදී වගු නිර්මාණය කළත් ඒවා වෙනස් කරන්නේ (alter) නැත, එබැවින් පවතින වගුවක නව තීරුවක් (column) මෙය නොමැතිව නොපෙනී යයි. සියලුම දත්ත අලුතින් ජනනය වන බැවින් මින් කිසිදු පාඩුවක් සිදු නොවේ.

මෙම අනුපිළිවෙල වැදගත් වන අතර script එක එය බලගන්වයි: විෂය නිර්දේශය (curriculum) → අවදානම් ආකෘතිය (risk model) → නාමලේඛනය (roster) → පරීක්ෂණ (assessments) → ව්‍යුත්පන්න සාධක (derived evidence) → ප්‍රස්ථාර ප්‍රක්ෂේපණය (graph projection).

## පර්යේෂණ කොටස් නැවත ජනනය කිරීම (Regenerating the research artefacts)

අවදානම් ආකෘතියේ පරාමිතීන්, අතුරුමුහුණත් වචන සහ පර්යේෂණ වාර්තාව එකිනෙකට ගැලපිය යුතුය. `build_ui_data.py` මඟින් `REPORT.md` හි edge වගුව කේතයට (code) එරෙහිව හරස්-තහවුරු (cross-validate) කරන අතර, වෙනසක් ඇත්නම් build එක අසමත් (fail) කරයි.

```powershell
cd research\dropout-ews
..\..\.venv\Scripts\python.exe ui\build_ui_data.py ui\ui_data.json
..\..\.venv\Scripts\python.exe ui\export_model.py ui\case_data.json
node ui\verify_infer.cjs ui\case_data.json
cd ..\..
.\.venv\Scripts\python.exe scripts\build_risk_factor_copy.py
```

`data/seeds/risk_factor_copy.json` ගොනුවේ, ක්‍රියාත්මක වන ආකෘතියේ ඇඟිලි සලකුණ (fingerprint) ඇති බව පරීක්ෂණයක් මඟින් (test) තහවුරු කරයි. එබැවින් යල් පැන ගිය පිටපතක් වැරදි ලේබල් පෙන්වනවා වෙනුවට පරීක්ෂණ මාලාවම (test suite) අසමත් කරයි.

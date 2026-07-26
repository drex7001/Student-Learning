/* Prove the browser inference engine agrees with pgmpy.
   Compares infer.js against the posteriors exported by export_model.py for every fixture
   case -- observational and joint-interventional -- and exits non-zero on any mismatch,
   so a wrong engine cannot be built into the page. */

const fs = require("fs");
const path = require("path");
const { createEngine } = require("./infer.js");

const dataPath = process.argv[2] || path.join(__dirname, "case_data.json");
const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
const engine = createEngine({ nodes: data.nodes });
const target = data.meta.target;
const TOL = 1e-9;

let worst = 0, worstCase = null, checked = { observe: 0, do: 0 };

for (const c of data.fixture) {
  const got = engine.query(target, c.evidence, c.intervention);
  let gap = 0;
  for (const s of Object.keys(c.posterior)) gap = Math.max(gap, Math.abs(got[s] - c.posterior[s]));
  checked[c.kind]++;
  if (gap > worst) { worst = gap; worstCase = c; }
  if (gap > TOL) {
    console.error(`MISMATCH ${gap.toExponential(3)} on ${c.kind}`);
    console.error("  evidence     ", JSON.stringify(c.evidence));
    console.error("  intervention ", JSON.stringify(c.intervention || {}));
    console.error("  pgmpy        ", JSON.stringify(c.posterior));
    console.error("  infer.js     ", JSON.stringify(got));
    process.exit(1);
  }
}

/* The guardrail is part of the engine's contract, not just the UI's. */
let refused = false;
try { engine.query(target, {}, { Neuro_Type: "Typical" }); }
catch (e) { refused = /not modifiable/.test(e.message); }
if (!refused) { console.error("engine failed to refuse do(Neuro_Type)"); process.exit(1); }

/* Posteriors must be proper distributions. */
for (const c of data.fixture) {
  const got = engine.query(target, c.evidence, c.intervention);
  const sum = Object.values(got).reduce((a, b) => a + b, 0);
  if (Math.abs(sum - 1) > 1e-12) { console.error(`posterior sums to ${sum}`); process.exit(1); }
  if (Object.values(got).some(p => p <= 0 || p >= 1)) {
    console.error("posterior has a degenerate state", got); process.exit(1);
  }
}

const t0 = Date.now();
const N = 200;
for (let i = 0; i < N; i++) engine.query(target, data.caseload[i % data.caseload.length].values, null);
const ms = (Date.now() - t0) / N;

console.log(`verified: ${checked.observe} observational + ${checked.do} interventional ` +
            `posteriors match pgmpy (worst gap ${worst.toExponential(2)}, tol ${TOL.toExponential(0)})`);
console.log("verified: engine refuses do(Neuro_Type)");
console.log(`verified: all posteriors normalised and non-degenerate`);
console.log(`timing: ${ms.toFixed(2)} ms per full-evidence query`);

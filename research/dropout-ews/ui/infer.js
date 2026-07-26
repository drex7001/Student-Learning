/* Exact Bayesian-network inference for the case tool: variable elimination, plus do()
   by truncated factorisation on the mutilated graph.

   This file is inlined into the built page *and* exercised by verify_infer.cjs against
   posteriors computed by pgmpy, so the browser cannot silently disagree with the model.

   Factor convention matches numpy's C-order ravel of a pgmpy TabularCPD:
     vars = [variable, ...parents], card = [cardinality of each], and in `values` the
     LAST variable varies fastest. */

function createEngine(spec) {
  const nodes = spec.nodes;
  const byName = new Map(nodes.map(n => [n.name, n]));
  const cardOf = new Map(nodes.map(n => [n.name, n.states.length]));
  const indexOf = new Map(
    nodes.map(n => [n.name, new Map(n.states.map((s, i) => [s, i]))])
  );

  /* ---------------------------------------------------------------- factor algebra */

  function strides(card) {
    const s = new Array(card.length);
    let acc = 1;
    for (let i = card.length - 1; i >= 0; i--) { s[i] = acc; acc *= card[i]; }
    return s;
  }

  function baseFactor(node) {
    const vars = [node.name, ...node.parents];
    return {
      vars,
      card: vars.map(v => cardOf.get(v)),
      values: Float64Array.from(node.cpd)
    };
  }

  /* Fix the listed variables to a state, dropping them from the factor's scope. */
  function reduce(factor, fixed) {
    const keep = [], drop = [];
    factor.vars.forEach((v, i) => (fixed.has(v) ? drop : keep).push(i));
    if (drop.length === 0) return factor;

    const src = strides(factor.card);
    let offset = 0;
    for (const i of drop) offset += src[i] * fixed.get(factor.vars[i]);

    const vars = keep.map(i => factor.vars[i]);
    const card = keep.map(i => factor.card[i]);
    const size = card.reduce((a, b) => a * b, 1);
    const values = new Float64Array(size);
    const idx = new Array(keep.length).fill(0);

    for (let flat = 0; flat < size; flat++) {
      let off = offset;
      for (let k = 0; k < keep.length; k++) off += src[keep[k]] * idx[k];
      values[flat] = factor.values[off];
      for (let k = keep.length - 1; k >= 0; k--) {
        if (++idx[k] < card[k]) break;
        idx[k] = 0;
      }
    }
    return { vars, card, values };
  }

  function multiply(factors) {
    const vars = [];
    for (const f of factors) for (const v of f.vars) if (!vars.includes(v)) vars.push(v);
    const card = vars.map(v => cardOf.get(v));
    const size = card.reduce((a, b) => a * b, 1);
    const values = new Float64Array(size).fill(1);

    /* For each input factor, precompute the stride it advances per output variable. */
    const plans = factors.map(f => {
      const fs = strides(f.card);
      const step = vars.map(v => {
        const i = f.vars.indexOf(v);
        return i === -1 ? 0 : fs[i];
      });
      return { f, step };
    });

    const idx = new Array(vars.length).fill(0);
    for (let flat = 0; flat < size; flat++) {
      let product = 1;
      for (const { f, step } of plans) {
        let off = 0;
        for (let k = 0; k < vars.length; k++) off += step[k] * idx[k];
        product *= f.values[off];
      }
      values[flat] = product;
      for (let k = vars.length - 1; k >= 0; k--) {
        if (++idx[k] < card[k]) break;
        idx[k] = 0;
      }
    }
    return { vars, card, values };
  }

  function marginalize(factor, victim) {
    const at = factor.vars.indexOf(victim);
    if (at === -1) return factor;
    const src = strides(factor.card);
    const vars = factor.vars.filter((_, i) => i !== at);
    const card = factor.card.filter((_, i) => i !== at);
    const size = card.reduce((a, b) => a * b, 1);
    const values = new Float64Array(size);
    const keep = factor.vars.map((_, i) => i).filter(i => i !== at);
    const idx = new Array(keep.length).fill(0);

    for (let flat = 0; flat < size; flat++) {
      let off = 0;
      for (let k = 0; k < keep.length; k++) off += src[keep[k]] * idx[k];
      let sum = 0;
      for (let s = 0; s < factor.card[at]; s++) sum += factor.values[off + src[at] * s];
      values[flat] = sum;
      for (let k = keep.length - 1; k >= 0; k--) {
        if (++idx[k] < card[k]) break;
        idx[k] = 0;
      }
    }
    return { vars, card, values };
  }

  /* ------------------------------------------------------------------- elimination */

  /* Greedy min-fill: eliminate the variable whose removal adds fewest new neighbours. */
  function order(factors, keep) {
    const adj = new Map();
    const touch = v => { if (!adj.has(v)) adj.set(v, new Set()); return adj.get(v); };
    for (const f of factors) {
      for (const a of f.vars) {
        touch(a);
        for (const b of f.vars) if (a !== b) touch(a).add(b);
      }
    }
    const remaining = new Set([...adj.keys()].filter(v => v !== keep));
    const seq = [];
    while (remaining.size) {
      let best = null, bestFill = Infinity;
      for (const v of remaining) {
        const nb = [...adj.get(v)].filter(n => remaining.has(n));
        let fill = 0;
        for (let i = 0; i < nb.length; i++)
          for (let j = i + 1; j < nb.length; j++)
            if (!adj.get(nb[i]).has(nb[j])) fill++;
        if (fill < bestFill) { bestFill = fill; best = v; if (fill === 0) break; }
      }
      const nb = [...adj.get(best)].filter(n => remaining.has(n) && n !== best);
      for (let i = 0; i < nb.length; i++)
        for (let j = i + 1; j < nb.length; j++) {
          adj.get(nb[i]).add(nb[j]);
          adj.get(nb[j]).add(nb[i]);
        }
      remaining.delete(best);
      seq.push(best);
    }
    return seq;
  }

  /* Query P(target | evidence) or P(target | do(intervention), evidence).
     do() is truncated factorisation: the intervened variable's own conditional is
     dropped (cutting every edge into it) and its assigned value is held fixed
     wherever it appears as a parent. Its now-irrelevant marginal would cancel in the
     normalisation anyway, which is why dropping the factor outright is exact. */
  function query(target, evidence, intervention) {
    const ev = evidence || {};
    const iv = intervention || {};

    for (const [v, s] of Object.entries({ ...ev, ...iv })) {
      if (!byName.has(v)) throw new Error(`unknown variable ${v}`);
      if (!indexOf.get(v).has(s)) throw new Error(`unknown state ${v}=${s}`);
    }
    for (const v of Object.keys(iv)) {
      if (v in ev) throw new Error(`${v} is both an intervention and an observation`);
      if (!byName.get(v).modifiable) throw new Error(`${v} is not modifiable`);
    }

    const fixed = new Map();
    for (const [v, s] of Object.entries({ ...ev, ...iv })) fixed.set(v, indexOf.get(v).get(s));

    let factors = [];
    for (const node of nodes) {
      if (node.name in iv) continue;            // edges into the intervened node are cut
      factors.push(reduce(baseFactor(node), fixed));
    }
    factors = factors.filter(f => f.vars.length > 0);

    for (const victim of order(factors, target)) {
      const hit = factors.filter(f => f.vars.includes(victim));
      if (!hit.length) continue;
      factors = factors.filter(f => !f.vars.includes(victim));
      factors.push(marginalize(hit.length === 1 ? hit[0] : multiply(hit), victim));
    }

    const live = factors.filter(f => f.vars.length > 0);
    const joint = live.length === 1 ? live[0] : multiply(live);
    if (joint.vars.length !== 1 || joint.vars[0] !== target)
      throw new Error(`elimination left ${JSON.stringify(joint.vars)}`);

    const total = joint.values.reduce((a, b) => a + b, 0);
    const out = {};
    byName.get(target).states.forEach((s, i) => { out[s] = joint.values[i] / total; });
    return out;
  }

  return { query, nodes, byName };
}

if (typeof module !== "undefined" && module.exports) module.exports = { createEngine };

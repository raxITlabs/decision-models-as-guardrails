/* decision-models-as-guardrails leaderboard: data rules, kept apart from rendering so they can be tested without a browser.
 *
 * Loaded by index.html as a classic script (window.GoldRails) and by the pytest suite through node
 * (module.exports). Nothing here touches the DOM.
 *
 * The rules this file enforces come from the completion plan (docs/reports/gold-rails-completion-plan.html):
 *   - only frozen implementations are plotted;
 *   - an unevaluated, failed or not-applicable suite is labelled, never plotted as zero;
 *   - an Overall point needs all six suites evaluated for that implementation (a file's overall_suites can name a
 *     different six, as edition 2 does with profanity in place of word filters);
 *   - a cost of zero is never a default, so a zero or missing cost keeps the point off the cost axis;
 *   - threshold changes never draw a line; only a declared configuration sweep does.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GoldRails = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const SCHEMA_VERSION = "goldrails-leaderboard-site/0.1";      // this page's display format (results.schema.json)
  const EVALUATOR_SCHEMA = "goldrails-leaderboard/0.1";         // benchmark/goldrails_bench/leaderboard.py output

  const CORE_SUITES = ["content", "prompt_attacks", "denied_topics", "word_filters", "sensitive_information", "grounding"];

  const VIEWS = [
    { id: "overall", label: "Overall", sub: "Equal-weight mean of the six suites" },
    { id: "content", label: "Content", sub: "Harmful requests and unsafe replies, scored against the source task" },
    { id: "prompt_attacks", label: "Prompt attacks", sub: "Jailbreak, injection and leakage, with benign instructions" },
    { id: "denied_topics", label: "Denied topics", sub: "Whether a message falls inside a supplied topic definition" },
    { id: "word_filters", label: "Word filters", sub: "Configured terms under the declared matching rules" },
    { id: "profanity", label: "Profanity", sub: "Word filters, profanity subtask: swear words and vulgar terms against the reviewed definition" },
    { id: "sensitive_information", label: "Sensitive information", sub: "Presence and type of shared supported entities (detection, not masking)" },
    { id: "grounding", label: "Grounding", sub: "Unsupported claims relative to supplied evidence" },
    { id: "bias", label: "Fairness and bias diagnostics", sub: "Outside the six-suite score; no number here is a fairness percentage" },
  ];

  const BIAS_TRACKS = [
    { id: "guardrail_fairness", label: "Guardrail fairness diagnostics: B1 moderation balanced accuracy, not a fairness percentage" },
    { id: "decision_bias", label: "Decision-model bias diagnostics: BBQ ambiguous-context accuracy" },
  ];

  const TYPES = {
    hosted_api: { label: "Hosted API", slot: 1, shape: "circle" },
    self_hosted: { label: "Self-hosted", slot: 2, shape: "square" },
    managed_service: { label: "Managed service", slot: 3, shape: "diamond" },
    code_baseline: { label: "Code baseline", slot: 0, shape: "triangle" },
    unknown: { label: "Type not recorded", slot: 0, shape: "circle" },
  };

  const AXES = {
    cost: { id: "cost", label: "Measured cost per 1,000 evaluations (USD, log scale)", short: "Cost per 1,000" },
    p95: { id: "p95", label: "p95 latency (seconds, log scale)", short: "p95 latency" },
  };

  const STATUS_TEXT = {
    evaluated: "Evaluated",
    not_evaluated: "Not evaluated",
    not_applicable: "Not applicable",
    failed: "Failed",
  };

  const isNum = (v) => typeof v === "number" && Number.isFinite(v);

  /** The suites an Overall averages: the file's overall_suites (edition 2 uses profanity in place of word filters), else the six core suites. */
  function overallSuites(data) {
    return data && Array.isArray(data.overall_suites) && data.overall_suites.length ? data.overall_suites : CORE_SUITES;
  }

  function viewOf(id) {
    return VIEWS.find((v) => v.id === id) || null;
  }

  /** Structural and consistency checks. Returns {errors, warnings}; errors stop the page from plotting. */
  function validate(data) {
    const errors = [];
    const warnings = [];
    if (!data || typeof data !== "object") return { errors: ["The results file is not a JSON object."], warnings };
    if (data.schema_version !== SCHEMA_VERSION) errors.push(`schema_version is ${JSON.stringify(data.schema_version)}, expected ${SCHEMA_VERSION}.`);
    if (typeof data.placeholder !== "boolean") errors.push("placeholder must be true or false.");
    for (const key of ["benchmark", "cost_basis", "latency_basis"]) {
      if (!data[key] || typeof data[key] !== "object") errors.push(`${key} is missing.`);
    }
    if (!Array.isArray(data.implementations) || data.implementations.length === 0) errors.push("implementations is missing or empty.");
    if (!Array.isArray(data.entries)) errors.push("entries is missing.");
    if (errors.length) return { errors, warnings };

    const impls = new Map();
    for (const im of data.implementations) {
      if (!im || typeof im.id !== "string") { errors.push("An implementation has no id."); continue; }
      if (impls.has(im.id)) errors.push(`Implementation ${im.id} appears twice.`);
      if (!TYPES[im.type]) errors.push(`Implementation ${im.id} has unknown type ${JSON.stringify(im.type)}.`);
      if (typeof im.frozen !== "boolean") errors.push(`Implementation ${im.id} does not say whether it is frozen.`);
      impls.set(im.id, im);
    }
    const seen = new Set();
    for (const e of data.entries) {
      const where = `${e.implementation} / ${e.suite}${e.track ? " / " + e.track : ""}`;
      if (!impls.has(e.implementation)) errors.push(`Entry ${where} names an unknown implementation.`);
      if (!viewOf(e.suite)) errors.push(`Entry ${where} names an unknown suite.`);
      if (!STATUS_TEXT[e.status]) errors.push(`Entry ${where} has unknown status ${JSON.stringify(e.status)}.`);
      if (e.suite === "bias" && !BIAS_TRACKS.some((t) => t.id === e.track)) errors.push(`Bias entry ${where} needs a track.`);
      const key = `${e.implementation}|${e.suite}|${e.track || ""}`;
      if (seen.has(key)) errors.push(`Entry ${where} appears twice.`);
      seen.add(key);
      if (e.status === "evaluated") {
        const s = e.quality && e.quality.score;
        if (!isNum(s) || s < 0 || s > 100) errors.push(`Entry ${where} is evaluated but has no score between 0 and 100.`);
        const iv = e.quality && e.quality.interval;
        if (iv && isNum(s) && (iv.low > s || iv.high < s)) errors.push(`Entry ${where}: score ${s} lies outside its interval.`);
        if (!iv) warnings.push(`Entry ${where} has no interval.`);
      } else if (e.quality && isNum(e.quality.score)) {
        errors.push(`Entry ${where} is ${e.status} but carries a score; only evaluated entries may.`);
      }
      if (e.cost && e.cost.usd_per_1000 === 0 && e.cost.zero_tariff !== true) errors.push(`Entry ${where} reports a cost of exactly 0. Costs are never defaulted to zero; report a measured value, null, or a documented zero list price (zero_tariff).`);
    }
    if (data.overall_suites !== undefined) {
      if (!Array.isArray(data.overall_suites) || !data.overall_suites.length) errors.push("overall_suites must be a non-empty list of suites.");
      else for (const s of data.overall_suites) if (!viewOf(s) || s === "overall" || s === "bias") errors.push(`overall_suites names ${JSON.stringify(s)}, which is not a scored suite.`);
    }
    for (const c of data.sanity_checks || []) {
      for (const r of c.results || []) if (!impls.has(r.implementation)) errors.push(`Sanity check ${c.id} names an unknown implementation ${r.implementation}.`);
    }
    // Overall may only be evaluated when all of its suites are (six in edition 1).
    for (const im of impls.values()) {
      const overall = data.entries.find((e) => e.implementation === im.id && e.suite === "overall");
      const missing = overallSuites(data).filter((s) => !data.entries.some((e) => e.implementation === im.id && e.suite === s && e.status === "evaluated"));
      if (overall && overall.status === "evaluated" && missing.length) {
        errors.push(`${im.id}: Overall is marked evaluated but these suites are not: ${missing.join(", ")}.`);
      }
    }
    if (data.placeholder) {
      const unmarked = data.implementations.filter((im) => !/PLACEHOLDER/.test(im.label || ""));
      if (unmarked.length) errors.push(`Placeholder file with implementation labels not marked PLACEHOLDER: ${unmarked.map((i) => i.id).join(", ")}.`);
    }
    if (data.benchmark.split !== "test") warnings.push(`These numbers come from the ${data.benchmark.split} split, not the frozen test split.`);
    return { errors, warnings };
  }

  /** One row per implementation for a view. Implementations without an entry get a synthesised not_evaluated row. */
  function rowsFor(data, viewId, track) {
    const out = [];
    for (const im of data.implementations) {
      if (Array.isArray(im.scope) && !im.scope.includes(viewId)) continue;
      let e = data.entries.find((x) => x.implementation === im.id && x.suite === viewId && (viewId !== "bias" || x.track === track));
      if (!e) e = { implementation: im.id, suite: viewId, track: viewId === "bias" ? track : null, status: "not_evaluated", status_note: "No entry in the results file.", synthesised: true };
      out.push({ impl: im, entry: e });
    }
    return out;
  }

  function axisValue(entry, axis) {
    if (axis === "cost") return entry.cost ? entry.cost.usd_per_1000 : null;
    if (axis === "p95") return entry.latency ? entry.latency.p95_s : null;
    return null;
  }

  /** Split a view's rows into plotted points and labelled exclusions. Nothing is ever plotted at zero. */
  function plotPlan(data, rows, axis) {
    const points = [];
    const excluded = [];
    for (const r of rows) {
      const { impl, entry } = r;
      let reason = null;
      if (!impl.frozen) reason = "Not frozen: only frozen implementations are plotted.";
      else if (entry.status !== "evaluated") reason = `${STATUS_TEXT[entry.status] || entry.status}${entry.status_note ? ": " + entry.status_note : "."}`;
      else if (!entry.quality || !isNum(entry.quality.score)) reason = "No score.";
      else if (entry.suite === "overall") {
        const need = overallSuites(data);
        const missing = need.filter((s) => !data.entries.some((e) => e.implementation === impl.id && e.suite === s && e.status === "evaluated"));
        if (missing.length) reason = `Overall needs all ${need.length === 6 ? "six" : need.length} suites; missing ${missing.join(", ")}.`;
      }
      if (!reason) {
        const x = axisValue(entry, axis);
        if (axis === "cost" && x === 0 && entry.cost && entry.cost.zero_tariff) reason = "Zero list price for this policy. A log cost axis cannot place zero; the table shows it.";
        else if (!isNum(x) || x <= 0) reason = axis === "cost" ? "Cost not measured, so it has no place on the cost axis." : "p95 latency not measured.";
        else points.push({ impl, entry, x, y: entry.quality.score, lo: entry.quality.interval ? entry.quality.interval.low : null, hi: entry.quality.interval ? entry.quality.interval.high : null });
      }
      if (reason) excluded.push({ impl, entry, reason });
    }
    return { points, excluded };
  }

  /** Lines only for declared configuration sweeps with at least two plotted members. */
  function sweepLines(points) {
    const groups = new Map();
    for (const p of points) {
      const sw = p.impl.sweep;
      if (!sw || !sw.id) continue;
      if (!groups.has(sw.id)) groups.set(sw.id, []);
      groups.get(sw.id).push(p);
    }
    const lines = [];
    for (const [id, pts] of groups) {
      if (pts.length < 2) continue;
      pts.sort((a, b) => a.impl.sweep.order - b.impl.sweep.order);
      lines.push({ id, type: pts[0].impl.type, points: pts });
    }
    return lines;
  }

  /** Rank evaluated, frozen, plottable-in-principle rows by score; ties share a rank. */
  function ranks(data, rows) {
    const eligible = rows.filter((r) => r.impl.frozen && r.entry.status === "evaluated" && r.entry.quality && isNum(r.entry.quality.score) &&
      (r.entry.suite !== "overall" || overallSuites(data).every((s) => data.entries.some((e) => e.implementation === r.impl.id && e.suite === s && e.status === "evaluated"))));
    eligible.sort((a, b) => b.entry.quality.score - a.entry.quality.score);
    const out = new Map();
    let prev = null, rank = 0;
    eligible.forEach((r, i) => {
      if (r.entry.quality.score !== prev) rank = i + 1;
      prev = r.entry.quality.score;
      out.set(r.impl.id, rank);
    });
    return out;
  }

  const TABLE_COLUMNS = [
    ["rank", "Rank"], ["implementation", "Implementation"], ["type", "Type"], ["frozen", "Frozen"], ["status", "Status"],
    ["score", "Score"], ["ci_low", "Interval low"], ["ci_high", "Interval high"], ["ci_level", "Interval level"],
    ["violation_recall", "Violation recall"], ["benign_pass_rate", "Benign pass rate"],
    ["recall_at_budget", "Recall at FPR budget"], ["fpr_budget", "FPR budget"], ["heldout_fpr", "Held-out FPR"],
    ["cost_usd_per_1000", "Cost per 1,000 (USD)"], ["cost_zero_tariff", "Zero list price"], ["cost_basis", "Cost basis"], ["p50_s", "p50 (s)"], ["p95_s", "p95 (s)"],
    ["n_total", "n"], ["n_positive", "n positive"], ["n_negative", "n negative"],
    ["missed_violations", "Missed violations"], ["false_positives", "False positives"], ["failed", "Failed"], ["no_decision", "No decision"],
    ["threshold", "Threshold"], ["config_hash", "Config hash"], ["status_note", "Note"],
  ];

  function flatRow(data, r, rankMap) {
    const e = r.entry, im = r.impl;
    const q = e.quality || {}, iv = q.interval || {}, rb = e.recall_at_fpr_budget || {};
    return {
      placeholder: data.placeholder ? "PLACEHOLDER" : "",
      view: e.suite + (e.track ? ":" + e.track : ""),
      rank: rankMap.has(im.id) ? rankMap.get(im.id) : null,
      implementation: im.label, implementation_id: im.id, type: (TYPES[im.type] || {}).label || im.type, frozen: im.frozen,
      status: STATUS_TEXT[e.status] || e.status,
      score: isNum(q.score) ? q.score : null, ci_low: isNum(iv.low) ? iv.low : null, ci_high: isNum(iv.high) ? iv.high : null, ci_level: isNum(iv.level) ? iv.level : null,
      violation_recall: e.violation_recall ?? null, benign_pass_rate: e.benign_pass_rate ?? null,
      recall_at_budget: rb.recall ?? null, fpr_budget: rb.budget ?? null, heldout_fpr: rb.heldout_fpr ?? null,
      cost_usd_per_1000: e.cost ? e.cost.usd_per_1000 ?? null : null, cost_zero_tariff: !!(e.cost && e.cost.zero_tariff), cost_basis: e.cost ? e.cost.basis : null,
      p50_s: e.latency ? e.latency.p50_s ?? null : null, p95_s: e.latency ? e.latency.p95_s ?? null : null,
      n_total: e.sample ? e.sample.total : null, n_positive: e.sample ? e.sample.positive : null, n_negative: e.sample ? e.sample.negative : null,
      missed_violations: e.errors ? e.errors.missed_violations : null, false_positives: e.errors ? e.errors.false_positives : null,
      failed: e.failures ? e.failures.failed : null, no_decision: e.failures ? e.failures.no_decision : null,
      threshold: e.threshold ? e.threshold.value : null,
      config_hash: im.configuration ? im.configuration.config_hash : null,
      status_note: e.status_note || null,
    };
  }

  function tableRows(data, rows) {
    const rankMap = ranks(data, rows);
    const flat = rows.map((r) => flatRow(data, r, rankMap));
    flat.sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity) || String(a.implementation).localeCompare(String(b.implementation)));
    return flat;
  }

  function csvCell(v) {
    if (v === null || v === undefined) return "";
    let s = String(v);
    if (/^[=+\-@]/.test(s)) s = "'" + s;            // keep spreadsheets from treating a label as a formula
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }

  function toCSV(flat) {
    const keys = ["placeholder", "view", ...TABLE_COLUMNS.map((c) => c[0]), "implementation_id"];
    const uniq = [...new Set(keys)];
    const lines = [uniq.join(",")];
    for (const r of flat) lines.push(uniq.map((k) => csvCell(r[k])).join(","));
    return lines.join("\n") + "\n";
  }

  /** Log-scale ticks covering [min, max]. */
  function logTicks(min, max) {
    const lo = Math.floor(Math.log10(min)), hi = Math.ceil(Math.log10(max));
    const ticks = [];
    const dense = hi - lo <= 2;
    for (let p = lo; p <= hi; p++) {
      for (const m of dense ? [1, 2, 5] : [1]) {
        const v = m * Math.pow(10, p);
        if (v >= Math.pow(10, lo) && v <= Math.pow(10, hi)) ticks.push(v);
      }
    }
    return { domain: [Math.pow(10, lo), Math.pow(10, hi)], ticks };
  }

  /** Linear ticks from zero with a round step (1, 2, 2.5 or 5 times a power of ten), about six intervals. */
  function linearTicks(max) {
    const raw = (isNum(max) && max > 0 ? max : 1) / 6;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((v) => v >= raw - 1e-12);
    const n = Math.max(1, Math.ceil(max / step - 1e-9));
    const ticks = [];
    for (let i = 0; i <= n; i++) ticks.push(Number((i * step).toPrecision(12)));
    return { domain: [0, ticks[n]], ticks, step };
  }

  function fmtCost(v) {
    if (!isNum(v)) return "not measured";
    if (v >= 1) return "$" + v.toFixed(2);
    const digits = Math.max(2, 1 - Math.floor(Math.log10(v)) + 1);
    return "$" + v.toFixed(Math.min(digits, 6)).replace(/0+$/, "").replace(/\.$/, "");
  }

  function fmtSeconds(v) {
    if (!isNum(v)) return "not measured";
    if (v < 0.01) return (v * 1000).toFixed(v < 0.001 ? 2 : 1).replace(/\.0$/, "") + " ms";
    if (v < 1) return Math.round(v * 1000) + " ms";
    return v.toFixed(v < 10 ? 2 : 1) + " s";
  }

  /** Axis tick labels: powers of ten and 2x/5x steps, without trailing zeros. */
  function fmtTick(v, axis) {
    if (!isNum(v)) return "";
    const clean = (x) => String(Number(x.toPrecision(3)));
    if (axis === "cost") return "$" + clean(v);
    return v < 1 ? clean(v * 1000) + " ms" : clean(v) + " s";
  }

  function fmtPct(v) {
    return isNum(v) ? (v * 100).toFixed(1) + "%" : "n/a";
  }


  /* ---------- evaluator adapter ----------
   * benchmark/goldrails_bench/leaderboard.py writes one document per run: arms (one per system, question set, config
   * and dataset version, per suite), per-suite rankings and an overall block. This turns it into the display format.
   * Rules carried over unchanged: incomplete suites carry no score, overall is evaluated only when the evaluator
   * ranked it, and nothing is frozen unless the run is a final run that the evaluator marked valid for publication.
   */
  const SUITE_FROM_EVALUATOR = { sensitive_info: "sensitive_information" };
  const TYPE_FROM_EVALUATOR = { hosted_api: "hosted_api", self_hosted: "self_hosted", managed_service: "managed_service", local_code: "code_baseline" };

  const mean = (xs) => { const v = xs.filter(isNum); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  const sum = (xs) => { const v = xs.filter(isNum); return v.length ? v.reduce((a, b) => a + b, 0) : null; };

  function isEvaluatorDoc(doc) {
    return !!doc && doc.schema === EVALUATOR_SCHEMA && Array.isArray(doc.arms) && doc.overall && typeof doc.overall === "object";
  }

  function entryFromArm(doc, arm, implId, viewId) {
    const ss = arm.suite_score || {};
    const subs = arm.subtasks || {};
    const inMean = (ss.subtasks_in_mean || []).filter((st) => subs[st]);
    const scored = inMean.map((st) => subs[st]);
    const suiteBoot = (doc.suites && doc.suites[arm.suite] && doc.suites[arm.suite].bootstrap) || {};
    const complete = ss.complete === true && isNum(ss.value);
    const cost = arm.cost || {};
    const ths = inMean.map((st) => ({ st, t: subs[st].threshold || {} }));
    const secondary = scored.map((x) => x.secondary).filter(Boolean);
    const n = scored.map((x) => x.n || {});
    const entry = {
      implementation: implId, suite: viewId, track: null,
      status: complete ? "evaluated" : "not_evaluated",
      status_note: complete ? null : (ss.coverage_note || "no complete suite score") + (isNum(ss.value) ? ` (partial score ${ss.value.toFixed(1)} over ${inMean.join(", ") || "no subtasks"}; not plotted or ranked)` : ""),
      quality: complete ? {
        score: ss.value,
        interval: ss.ci && isNum(ss.ci.low) && isNum(ss.ci.high) ? { low: ss.ci.low, high: ss.ci.high, level: isNum(suiteBoot.ci) ? suiteBoot.ci : 0.95, method: (doc.rules && doc.rules.intervals) || "group bootstrap" } : null,
        conditional_score: mean(scored.map((x) => x.conditional_task_score)),
      } : null,
      violation_recall: complete ? mean(scored.map((x) => x.recall)) : null,
      benign_pass_rate: complete ? mean(scored.map((x) => x.benign_pass_rate)) : null,
      recall_at_fpr_budget: complete && secondary.length ? {
        budget: secondary[0].budget,
        recall: mean(secondary.map((x) => x.held_out_recall)),
        heldout_fpr: mean(secondary.map((x) => x.held_out_false_positive_rate)),
        feasible: secondary.every((x) => String(x.status || "").startsWith("met")),
      } : null,
      threshold: complete && ths.length ? {
        value: ths.length === 1 ? (ths[0].t.threshold ?? null) : ths.map((x) => `${x.st} ${x.t.threshold ?? "none"}`).join("; "),
        selected_on: ths.every((x) => x.t.basis === "binary_operating_point") ? "fixed" : "tune",
        rule: [...new Set(ths.map((x) => x.t.basis).filter(Boolean))].join(", ") || "not recorded",
      } : null,
      sample: {
        total: arm.sample_sizes ? arm.sample_sizes.report_rows ?? null : null,
        positive: sum(n.map((x) => x.positive)), negative: sum(n.map((x) => x.negative)),
        groups: arm.sample_sizes ? arm.sample_sizes.report_groups ?? null : null,
      },
      errors: complete ? {
        missed_violations: sum(n.map((x) => isNum(x.positive) && isNum(x.tp) ? x.positive - x.tp : null)),
        false_positives: sum(n.map((x) => x.fp)),
      } : null,
      failures: { failed: sum(n.map((x) => x.failed)) ?? 0, no_decision: sum(n.map((x) => x.no_decision)) ?? 0 },
      coverage: {
        subtasks_evaluated: inMean,
        subtasks_required: ((doc.suites && doc.suites[arm.suite] && doc.suites[arm.suite].declared_subtasks) || []).slice(),
        note: ss.coverage_note || ((ss.optional_not_evaluated || []).length ? "optional not evaluated: " + ss.optional_not_evaluated.join(", ") : null),
      },
      cost: {
        usd_per_1000: isNum(cost.usd_per_1000) ? cost.usd_per_1000 : null,
        basis: cost.basis || "not recorded",
        note: cost.reason || (cost.tariff ? `tariff ${cost.tariff}${cost.tariff_checked_on ? ", checked " + cost.tariff_checked_on : ""}` : null),
        zero_tariff: cost.usd_per_1000 === 0 ? true : undefined,
      },
      latency: arm.latency ? { p50_s: arm.latency.p50_s ?? null, p95_s: isNum(arm.latency.p95_s) && arm.latency.p95_s > 0 ? arm.latency.p95_s : null, throughput_per_s: arm.latency.throughput_per_s ?? null } : null,
      bias: null,
      ledger: { path: "arm " + arm.arm_id, config_hash: arm.config_hash || "", dataset_sha256: (arm.dataset && arm.dataset.sha256) || "", rows: arm.sample_sizes ? arm.sample_sizes.records ?? null : null },
    };
    if (entry.cost.zero_tariff === undefined) delete entry.cost.zero_tariff;
    return entry;
  }

  function fromEvaluator(doc) {
    const final = doc.mode === "final" && doc.valid_for_publication === true;
    const armById = new Map(doc.arms.map((a) => [a.arm_id, a]));
    const used = new Set();
    const implementations = [], entries = [];
    const typeOf = (arms) => {
      const counts = {};
      for (const a of arms) { const t = TYPE_FROM_EVALUATOR[(a.cost || {}).implementation_type] || "unknown"; counts[t] = (counts[t] || 0) + 1; }
      return Object.keys(counts).sort((x, y) => counts[y] - counts[x])[0] || "unknown";
    };
    const armRow = (a, viewId, note) => {
      const id = "arm:" + a.arm_id;
      implementations.push({
        id, label: `${a.system} · ${a.question_set || "no question set"} · data ${String((a.dataset || {}).sha256 || "").slice(0, 8)}`,
        type: typeOf([a]), frozen: false, model: a.model || null, hardware: null, sweep: null, scope: [viewId],
        configuration: { config_hash: a.config_hash || "", question_set: a.question_set || null, decision_rule: null, guardrail: null, notes: note },
      });
      const e = entryFromArm(doc, a, id, viewId);
      e.status_note = [note, e.status_note].filter(Boolean).join(". ");
      entries.push(e);
    };
    // One display implementation per evaluator implementation (older documents name it `system`).
    for (const ov of doc.overall.implementations || []) {
      const name = ov.implementation || ov.system;
      if (!name) continue;
      const scope = ["overall", "bias"], chosenArms = [];
      for (const [evSuite, st] of Object.entries(ov.suites || {})) {
        const viewId = SUITE_FROM_EVALUATOR[evSuite] || evSuite;
        const arm = st && st.arm_id ? armById.get(st.arm_id) : null;
        if (arm) {
          used.add(arm.arm_id); chosenArms.push(arm); scope.push(viewId);
          entries.push(entryFromArm(doc, arm, name, viewId));
        } else if (st && st.status === "ambiguous") {
          for (const id of st.arms || []) {
            const a = armById.get(id);
            if (a && !used.has(id)) { used.add(id); armRow(a, viewId, `${name}: one of ${st.arms.length} candidate arms; the contract declares no implementation choice`); }
          }
        } else {
          scope.push(viewId);                          // labelled "not evaluated" row
        }
      }
      for (const v of CORE_SUITES) if (!scope.includes(v) && !(ov.suites && Object.keys(ov.suites).some((k) => (SUITE_FROM_EVALUATOR[k] || k) === v))) scope.push(v);
      const first = chosenArms[0] || {};
      implementations.push({
        id: name, label: name, type: typeOf(chosenArms), frozen: final && ov.declared !== false, model: first.model || null, hardware: null, sweep: null, scope,
        configuration: { config_hash: chosenArms.map((a) => a.config_hash).filter(Boolean).join(" + ") || "not recorded",
                         question_set: [...new Set(chosenArms.map((a) => a.question_set).filter(Boolean))].join(", ") || null,
                         decision_rule: null, guardrail: null,
                         notes: ov.declared === false ? "not declared in the contract: every system name is its own implementation" : null },
      });
      const comps = {};
      for (const [evSuite, st] of Object.entries(ov.suites || {})) comps[SUITE_FROM_EVALUATOR[evSuite] || evSuite] = st && st.status === "complete" && isNum(st.task_score) ? st.task_score : null;
      if (ov.ranked && isNum(ov.overall_score)) {
        entries.push({
          implementation: name, suite: "overall", track: null, status: "evaluated", status_note: null, missing_suites: [],
          quality: { score: ov.overall_score, interval: ov.ci && isNum(ov.ci.low) ? { low: ov.ci.low, high: ov.ci.high, level: 0.95, method: (doc.rules && doc.rules.intervals) || "group bootstrap" } : null, conditional_score: null },
          components: comps, violation_recall: null, benign_pass_rate: null, recall_at_fpr_budget: null,
          threshold: { value: null, selected_on: "tune", rule: "per suite; see suite tabs" },
          sample: null, errors: null, failures: null,
          coverage: { subtasks_evaluated: CORE_SUITES.filter((x) => isNum(comps[x])), subtasks_required: CORE_SUITES.slice(), note: "suites" },
          cost: { usd_per_1000: isNum(ov.usd_per_1000) && ov.usd_per_1000 > 0 ? ov.usd_per_1000 : null, basis: "equal-weight mean of suite costs", note: ov.cost_reason || null },
          latency: { p50_s: ov.p50_s ?? null, p95_s: isNum(ov.p95_s) && ov.p95_s > 0 ? ov.p95_s : null, throughput_per_s: null },
          bias: null, ledger: null,
        });
      } else {
        entries.push({
          implementation: name, suite: "overall", track: null, status: "not_evaluated",
          status_note: ov.not_ranked_reason || "not ranked by the evaluator",
          missing_suites: CORE_SUITES.filter((x) => !isNum(comps[x])), components: comps,
        });
      }
    }
    // Arms no implementation uses stay visible in their suite, never plotted.
    for (const a of doc.arms) {
      if (used.has(a.arm_id)) continue;
      armRow(a, SUITE_FROM_EVALUATOR[a.suite] || a.suite, "not part of any declared implementation");
    }
    const prov = doc.provenance || {};
    const versions = prov.dataset_versions || [];
    return {
      schema_version: SCHEMA_VERSION,
      placeholder: false,
      notice: doc.label || null,
      blockers: (doc.publication_blockers || []).slice(),
      source: { schema: doc.schema, mode: doc.mode, valid_for_publication: doc.valid_for_publication === true },
      benchmark: {
        name: "decision-models-as-guardrails",
        dataset_version: versions.length === 1 ? versions[0].slice(0, 12) : `${versions.length} dataset versions`,
        dataset_sha256: versions.length === 1 ? versions[0] : "multiple",
        dataset_url: null,
        split: doc.mode === "final" ? "test" : "tune",
        evaluation_contract: doc.contract ? `${doc.contract.version || "unversioned"} (${doc.contract.status || "status not recorded"})` : "not recorded",
        release_manifest: null,
        generated_at: prov.generated_at || "not recorded",
        headline_metric: doc.rules ? doc.rules.task_score : null,
        aggregation: doc.rules ? doc.rules.overall : null,
        fpr_budget: doc.contract && isNum(doc.contract.fpr_budget) ? doc.contract.fpr_budget : null,
      },
      cost_basis: { unit: "usd_per_1000_evaluations", tariff_date: prov.tariffs ? prov.tariffs.as_of || null : null, region: null, notes: (doc.rules && doc.rules.cost) || "not recorded" },
      latency_basis: { unit: "seconds", concurrency: null, client_location: null, notes: (doc.rules && doc.rules.latency) || "not recorded" },
      implementations, entries,
    };
  }

  /** Accept either format; return the display format. */
  function normalise(doc) {
    return isEvaluatorDoc(doc) ? fromEvaluator(doc) : doc;
  }

  return {
    SCHEMA_VERSION, EVALUATOR_SCHEMA, isEvaluatorDoc, fromEvaluator, normalise, CORE_SUITES, overallSuites, VIEWS, BIAS_TRACKS, TYPES, AXES, STATUS_TEXT, TABLE_COLUMNS,
    viewOf, validate, rowsFor, axisValue, plotPlan, sweepLines, ranks, tableRows, toCSV, logTicks, linearTicks,
    fmtCost, fmtSeconds, fmtTick, fmtPct, isNum,
  };
});

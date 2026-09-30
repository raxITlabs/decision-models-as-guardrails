// Rendered-page check: paste into the browser console on the served results page (or run through a browser tool).
// Compares every plotted point and every table score with the results file the page loaded (?results=, else
// results.json). Returns {checked, mismatches}.
(async () => {
  const d = await (await fetch(new URLSearchParams(location.search).get("results") || "results.json", { cache: "no-store" })).json();
  const byId = Object.fromEntries(d.implementations.map((i) => [i.label.replace(/\s*\(.*\)\s*$/, "").replace("Amazon Bedrock Guardrails", "Bedrock"), i.id]));
  const want = (impl, suite) => {
    if (suite === "word_filters_category") {
      const o = d.entries.find((e) => e.implementation === impl && e.suite === "overall");
      return o && o.suites && o.suites.word_filters ? o.suites.word_filters.task_score : null;
    }
    const e = d.entries.find((x) => x.implementation === impl && x.suite === suite);
    return e && e.quality ? e.quality.score : null;
  };
  const f1 = (v) => (Math.round(v * 10) / 10).toFixed(1);
  const bad = [];
  let n = 0;
  for (const g of document.querySelectorAll("#grid .pt")) {
    const m = g.getAttribute("aria-label").match(/^(.*?), .*: score ([\d.]+)(?:,|$)/);   // the label may go on with the cost
    const impl = byId[m[1]], exp = want(impl, g.dataset.suite);
    n++;
    if (exp === null || f1(exp) !== m[2]) bad.push(`chart ${g.dataset.suite}/${impl}: page ${m[2]}, data ${exp}`);
  }
  for (const r of document.querySelectorAll("table.all tr.row")) {
    const exp = want(r.dataset.key, r.dataset.suite), shown = r.children[1].textContent.trim();
    n++;
    if (exp === null || f1(exp) !== shown) bad.push(`table ${r.dataset.suite}/${r.dataset.key}: page ${shown}, data ${exp}`);
  }
  return { checked: n, mismatches: bad };
})();

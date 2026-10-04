"""The owner's review of edition 2 rows no ruling settles: a local page to decide them, and the importer that applies
the decisions.

    uv run python -m goldrails_dataset.edition2 owner-review-html            # write build/private/review.html
    uv run python -m goldrails_dataset.edition2 import-owner-review FILE     # apply an exported JSONL, then rebuild

The page lists every disputed row still out of the splits: the rows ``<suite>/resolutions.jsonl`` leaves for the owner
(``status: owner_review``) and the earlier ruling 8 resolutions that wait for the owner's confirmation (question
``C-R8``). It shows each row's text (rehydrated on this machine, so the page holds private-slice and licence-withheld
text), both labels, the question and controls for the final label, subtask, PII entity types, content harm category
and a note. Decisions autosave to the browser's localStorage and export as JSONL. The page is written to the
git-ignored ``build/private/`` and must never be committed or published.

The importer turns each decided line into a resolution (``status: resolved``, ``ruling: 9``: the owner reviews what
the automatic pass leaves, ``ruled_by: owner``). A ruling 8 confirmation whose label matches the proposal keeps the
proposed harm tags and stays ``ruling: 8``. Lines left undecided are skipped. Public and private-slice ids are
written to their own part of the resolutions file.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import SUBTASKS, e2_local

RULINGS_DOC = "docs/benchmark/29-owner-rulings-2026-10-03.md"
CONFIRM_QUESTION = "C-R8"
PII_TYPES_FILE = Path(__file__).resolve().parents[2] / "benchmark" / "question_sets" / "e2" / "f5-pii.json"
FEATURE = {"content": "F1", "prompt_attacks": "F2", "denied_topics": "F3", "word_filters": "F4", "pii": "F5",
           "grounding": "F6"}
# Content harm categories the owner can pick when a row is ruled harmful: (harm tag, AILuminate, Bedrock).
HARM = {"hate": ("hate", "HATE"), "insults": ("hate", "INSULTS"), "sexual": ("sexual_content", "SEXUAL"),
        "violence": ("violent_crimes", "VIOLENCE"), "misconduct": ("nonviolent_crimes", "MISCONDUCT")}


def _jsonl(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]


def _res_paths(suite: str, root: Path) -> tuple[Path, Path]:
    return (e2_local.suite_dir(suite, root) / "resolutions.jsonl",
            e2_local.private_dir(suite, root) / "resolutions.jsonl")


def pii_types() -> list:
    if PII_TYPES_FILE.exists():
        return list(json.loads(PII_TYPES_FILE.read_text(encoding="utf-8"))["supported_entities"])
    return ["NAME", "EMAIL", "PHONE", "ADDRESS", "USERNAME", "PASSWORD", "IP_ADDRESS", "DRIVER_ID",
            "US_SOCIAL_SECURITY_NUMBER"]


def _waiting_ids(parts: dict | None) -> set | None:
    """Ids the build keeps out for the owner (review buckets after drops), or None to take every owner_review line."""
    if parts is None:
        return None
    return {r.id for b in ("review", "review_private") for r in parts.get(b, [])}


def review_items(root: Path = e2_local.E2, parts: dict | None = None) -> list:
    """One dict per row the owner still has to decide, text included. ``parts`` (the build's buckets) limits the list
    to rows the build actually holds out (a row the build dropped needs no decision)."""
    waiting = _waiting_ids(parts)
    items = []
    for suite in e2_local.SUITES:
        pub, prv = _res_paths(suite, root)
        lines = [(d, False) for d in _jsonl(pub)] + [(d, True) for d in _jsonl(prv)]
        lines = [(d, p) for d, p in lines if d.get("status") == "owner_review"
                 and (waiting is None or d["id"] in waiting)]
        if not lines:
            continue
        cands = {c["id"]: c for c in e2_local.candidates(suite, root)}
        seconds = {r["id"]: r for r in e2_local.relabels(suite, root)}
        for d, private in lines:
            c = cands[d["id"]]
            st = c.get("state") or (c.get("record") or {}).get("state") or {}
            sec = seconds.get(d["id"], {})
            item = {
                "id": d["id"], "suite": suite, "feature": FEATURE[suite], "subtask": c.get("subtask"),
                "proposed_split": c.get("proposed_split"), "private": private, "source": e2_local.source_of(c),
                "question": d.get("question") or "unruled", "question_text": d.get("question_text") or "",
                "note": d.get("note") or "", "disagreement": d.get("disagreement"),
                "first": {"label": c.get("label"), "entity_types": c.get("entity_types"), "topic": c.get("topic"),
                          "rationale": c.get("label_rationale")},
                "second": {"label": sec.get("label"), "entity_types": sec.get("entity_types"),
                           "topic": sec.get("topic"), "refile_subtask": sec.get("refile_subtask"),
                           "rationale": sec.get("rationale")},
                "proposed": d.get("proposed"),
                "text": st.get("text"), "context": st.get("context") or [], "source_text": st.get("source"),
                "query": st.get("query"),
                "subtasks": list(SUBTASKS.get(FEATURE[suite], ())),
            }
            if suite == "pii":
                item["spans"] = [{"label": s.get("label"), "start": s.get("start"), "end": s.get("end")}
                                 for s in c.get("spans") or []]
            items.append(item)
    order = {q: i for i, q in enumerate(sorted({i["question"] for i in items}))}
    return sorted(items, key=lambda i: (i["suite"], order[i["question"]], i["id"]))


# --- the page --------------------------------------------------------------------------------------------------------

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Owner Review</title>
<style>
:root{--bg:#f7f7f5;--panel:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e2e2dc;--accent:#2f5d8a;--yes:#a23b2a;--no:#2f6b3a;
--chip:#efeee9;--warn:#8a5a00;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--panel:#1f1f1d;--ink:#ecebe6;--muted:#a3a29b;
--line:#33332f;--accent:#7fb0e0;--yes:#e08a78;--no:#8cc79a;--chip:#2a2a27;--warn:#e0b860}}
:root[data-theme="dark"]{--bg:#161615;--panel:#1f1f1d;--ink:#ecebe6;--muted:#a3a29b;--line:#33332f;--accent:#7fb0e0;
--yes:#e08a78;--no:#8cc79a;--chip:#2a2a27;--warn:#e0b860}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--panel);border-bottom:1px solid var(--line);padding:10px 16px}
header h1{font-size:17px;margin:0 0 6px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.bar select,.bar input[type=search]{font:inherit;padding:4px 6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
button{font:inherit;padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:var(--chip);color:var(--ink);cursor:pointer}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.progress{color:var(--muted);font-size:13px}
main{max-width:1100px;margin:0 auto;padding:12px 16px 80px}
.q{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:16px 0;padding:12px 14px}
.q h2{font-size:15px;margin:0 0 4px}
.q .qt{color:var(--muted);margin:0 0 8px}
.row{border-top:1px solid var(--line);padding:12px 0}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px}
.chip{background:var(--chip);border-radius:999px;padding:1px 8px}
.chip.private{color:var(--warn)}
code{font-family:var(--mono);font-size:12.5px}
.labels{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0;font-size:13.5px}
.labels div{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:6px 8px}
.y{color:var(--yes);font-weight:600}.n{color:var(--no);font-weight:600}
.text{white-space:pre-wrap;word-break:break-word;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;
max-height:320px;overflow:auto;font-size:14px}
details{margin:6px 0}details summary{cursor:pointer;color:var(--muted);font-size:13px}
.ctl{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin-top:8px;font-size:14px}
.ctl label{display:inline-flex;gap:4px;align-items:center}
.ctl textarea{width:100%;min-height:38px;font:inherit;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
.types{display:flex;flex-wrap:wrap;gap:4px 10px}
.done{border-left:3px solid var(--accent);padding-left:10px}
.note{color:var(--muted);font-size:13.5px;margin:4px 0}
mark{background:#f3d77a55;color:inherit}
@media (max-width:640px){.labels{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
<h1>Edition 2: rows waiting for the owner</h1>
<div class="bar">
<select id="fSuite"><option value="">all suites</option></select>
<select id="fQ"><option value="">all questions</option></select>
<select id="fState"><option value="">all rows</option><option value="open">undecided</option><option value="done">decided</option></select>
<input type="search" id="fText" placeholder="search id or text">
<button class="primary" id="export">Export JSONL</button>
<label class="progress"><input type="file" id="load" accept=".jsonl,.json" hidden><button id="loadBtn" type="button">Load JSONL</button></label>
<span class="progress" id="progress"></span>
</div>
</header>
<main id="main"></main>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const KEY = 'gold-rails-e2-owner-review:' + DATA.built;
const HARM = DATA.harm;
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { state = {}; }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} progress(); }
function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function lab(l){ return l === 'yes' ? '<span class="y">yes</span>' : l === 'no' ? '<span class="n">no</span>' : esc(l || '-'); }
function types(t){ return t && t.length ? ' <code>' + esc(t.join(', ')) + '</code>' : ''; }
const items = DATA.items;
const byQ = {};
items.forEach(it => { (byQ[it.suite + '|' + it.question] = byQ[it.suite + '|' + it.question] || []).push(it); });
const suites = [...new Set(items.map(i => i.suite))];
suites.forEach(s => fSuite.insertAdjacentHTML('beforeend', `<option>${esc(s)}</option>`));
Object.keys(byQ).forEach(k => fQ.insertAdjacentHTML('beforeend', `<option value="${esc(k)}">${esc(k.replace('|', ' / '))} (${byQ[k].length})</option>`));
function decided(id){ const d = state[id]; return d && (d.final_label === 'yes' || d.final_label === 'no'); }
function progress(){ const n = items.filter(i => decided(i.id)).length;
  document.getElementById('progress').textContent = `${n} of ${items.length} decided (${DATA.counts.public} public, ${DATA.counts.private} private rows)`; }
function highlight(text, spans){
  if (!spans || !spans.length || text == null) return esc(text);
  let out = '', at = 0;
  [...spans].sort((a, b) => a.start - b.start).forEach(s => { if (s.start < at) return;
    out += esc(text.slice(at, s.start)) + `<mark title="${esc(s.label)}">` + esc(text.slice(s.start, s.end)) + '</mark>'; at = s.end; });
  return out + esc(text.slice(at));
}
function rowHtml(it){
  const d = state[it.id] || {};
  const sub = d.final_subtask || '';
  const typesSel = new Set(d.final_entity_types || it.second.entity_types || it.first.entity_types || []);
  let ctx = '';
  if (it.context && it.context.length) ctx += `<details><summary>conversation context (${it.context.length} turns)</summary><div class="text">${esc(it.context.map(t => typeof t === 'string' ? t : (t.role ? t.role + ': ' : '') + (t.text || '')).join('\n\n'))}</div></details>`;
  if (it.query) ctx += `<div class="note"><b>Query:</b> ${esc(it.query)}</div>`;
  if (it.source_text) ctx += `<details><summary>grounding source (${it.source_text.length} chars)</summary><div class="text">${esc(it.source_text)}</div></details>`;
  const prop = it.proposed ? `<div class="note"><b>Proposed (needs your confirmation):</b> ${lab(it.proposed.final_label)} &middot; ${esc(it.proposed.reason || '')}</div>` : '';
  const pii = it.suite === 'pii' ? `<div class="types">entity types: ${DATA.pii_types.map(t => `<label><input type="checkbox" data-t="${t}" ${typesSel.has(t) ? 'checked' : ''}>${t}</label>`).join('')}</div>` : '';
  const harm = it.suite === 'content' ? `<label>harm category (when yes) <select data-k="harm"><option value="">${it.proposed && it.proposed.final_tags ? 'as proposed' : '-'}</option>${Object.keys(HARM).map(h => `<option ${d.harm === h ? 'selected' : ''}>${h}</option>`).join('')}</select></label>` : '';
  return `<div class="row ${decided(it.id) ? 'done' : ''}" data-id="${esc(it.id)}">
  <div class="meta"><code>${esc(it.id)}</code><span class="chip">${esc(it.suite)} / ${esc(it.subtask)}</span><span class="chip">${esc(it.proposed_split)}</span>
  ${it.private ? '<span class="chip private">private slice</span>' : ''}<span class="chip">${esc(it.source)}</span></div>
  ${it.note ? `<div class="note">${esc(it.note)}</div>` : ''}
  <div class="labels"><div><b>First label</b>: ${lab(it.first.label)}${types(it.first.entity_types)}${it.first.topic ? ' <code>' + esc(it.first.topic) + '</code>' : ''}<br><span class="note">${esc(it.first.rationale || '')}</span></div>
  <div><b>Second label</b>: ${lab(it.second.label)}${types(it.second.entity_types)}${it.second.refile_subtask ? ' refile: <code>' + esc(it.second.refile_subtask) + '</code>' : ''}${it.second.topic ? ' <code>' + esc(it.second.topic) + '</code>' : ''}<br><span class="note">${esc(it.second.rationale || '')}</span></div></div>
  ${prop}
  <div class="text">${it.suite === 'pii' ? highlight(it.text, it.spans) : esc(it.text)}</div>
  ${ctx}
  <div class="ctl">
   <span>final label:</span><label><input type="radio" name="l-${esc(it.id)}" value="yes" ${d.final_label === 'yes' ? 'checked' : ''}>yes</label>
   <label><input type="radio" name="l-${esc(it.id)}" value="no" ${d.final_label === 'no' ? 'checked' : ''}>no</label>
   <label><input type="radio" name="l-${esc(it.id)}" value="" ${!decided(it.id) ? 'checked' : ''}>undecided</label>
   <label>subtask <select data-k="sub"><option value="">${esc(it.subtask)} (keep)</option>${it.subtasks.filter(s => s !== it.subtask).map(s => `<option ${sub === s ? 'selected' : ''}>${esc(s)}</option>`).join('')}</select></label>
   ${harm}${pii}
   <textarea data-k="note" placeholder="note (optional)">${esc(d.note || '')}</textarea>
  </div></div>`;
}
function render(){
  const s = fSuite.value, q = fQ.value, st = fState.value, t = fText.value.trim().toLowerCase();
  let out = '';
  Object.keys(byQ).forEach(k => {
    if (q && k !== q) return;
    const rows = byQ[k].filter(it => (!s || it.suite === s) && (!st || (st === 'done') === decided(it.id)) &&
      (!t || it.id.toLowerCase().includes(t) || (it.text || '').toLowerCase().includes(t)));
    if (!rows.length) return;
    const it0 = byQ[k][0];
    out += `<section class="q"><h2>${esc(it0.question)} &middot; ${esc(it0.suite)} &middot; ${byQ[k].length} rows</h2><p class="qt">${esc(it0.question_text)}</p>
      <div class="bar"><span class="progress">set every undecided row in this question:</span><button data-all="${esc(k)}" data-v="yes">yes</button><button data-all="${esc(k)}" data-v="no">no</button></div>
      ${rows.map(rowHtml).join('')}</section>`;
  });
  main.innerHTML = out || '<p>No rows match.</p>';
}
main.addEventListener('change', e => {
  const row = e.target.closest('.row'); if (!row) return;
  const id = row.dataset.id; const d = state[id] = state[id] || {};
  if (e.target.type === 'radio') d.final_label = e.target.value;
  else if (e.target.dataset.k === 'sub') d.final_subtask = e.target.value;
  else if (e.target.dataset.k === 'harm') d.harm = e.target.value;
  else if (e.target.dataset.t) d.final_entity_types = [...row.querySelectorAll('[data-t]')].filter(x => x.checked).map(x => x.dataset.t);
  d.at = new Date().toISOString();
  row.classList.toggle('done', decided(id)); save();
});
main.addEventListener('input', e => { if (e.target.dataset.k !== 'note') return; const id = e.target.closest('.row').dataset.id;
  (state[id] = state[id] || {}).note = e.target.value; save(); });
main.addEventListener('click', e => { const k = e.target.dataset.all; if (!k) return;
  byQ[k].forEach(it => { if (!decided(it.id)) { state[it.id] = {...(state[it.id] || {}), final_label: e.target.dataset.v, at: new Date().toISOString()}; } });
  save(); render(); });
[fSuite, fQ, fState].forEach(x => x.addEventListener('change', render)); fText.addEventListener('input', render);
document.getElementById('export').addEventListener('click', () => {
  const lines = items.filter(it => decided(it.id)).map(it => { const d = state[it.id];
    const o = {id: it.id, suite: it.suite, question: it.question, final_label: d.final_label, note: d.note || '', decided_at: d.at || ''};
    if (d.final_subtask) o.final_subtask = d.final_subtask;
    if (it.suite === 'pii') o.final_entity_types = d.final_label === 'no' ? [] : (d.final_entity_types || it.second.entity_types || it.first.entity_types || []);
    if (it.suite === 'content' && d.harm) o.harm_category = d.harm;
    return JSON.stringify(o); });
  const blob = new Blob([lines.join('\n') + (lines.length ? '\n' : '')], {type: 'application/x-ndjson'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'owner-review-decisions.jsonl'; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
});
document.getElementById('loadBtn').addEventListener('click', () => document.getElementById('load').click());
document.getElementById('load').addEventListener('change', async e => { const f = e.target.files[0]; if (!f) return;
  (await f.text()).split('\n').filter(l => l.trim()).forEach(l => { try { const o = JSON.parse(l);
    state[o.id] = {final_label: o.final_label, final_subtask: o.final_subtask || '', final_entity_types: o.final_entity_types,
                   harm: o.harm_category || '', note: o.note || '', at: o.decided_at || ''}; } catch (err) {} });
  save(); render(); });
progress(); render();
</script>
</body>
</html>
"""


def _tracked_or_unignored(path: Path) -> bool:
    """True when ``path`` is inside this repository and git would track it (not ignored)."""
    import subprocess
    repo = Path(__file__).resolve().parents[2]
    p = path.resolve() if path.exists() else path.parent.resolve() / path.name
    if not p.is_relative_to(repo):
        return False
    r = subprocess.run(["git", "check-ignore", "-q", str(p)], cwd=repo, capture_output=True)
    return r.returncode != 0


def write_html(path: Path, root: Path = e2_local.E2, parts: dict | None = None, built: str | None = None) -> dict:
    """Write the review page. Refuses a path outside a git-ignored ``private/`` folder: the page holds private text."""
    path = Path(path)
    if path.parent.name != "private" or _tracked_or_unignored(path):
        raise ValueError(f"{path}: the review page holds private-slice and withheld text; write it into a git-ignored "
                         "private/ folder")
    items = review_items(root, parts)
    data = {"built": built or _dt.date.today().isoformat(), "items": items, "pii_types": pii_types(), "harm": HARM,
            "counts": {"public": sum(not i["private"] for i in items), "private": sum(i["private"] for i in items)}}
    blob = json.dumps(data, ensure_ascii=True).replace("</", "<\\/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PAGE.replace("__DATA__", blob), encoding="utf-8")
    by_q = {}
    for i in items:
        by_q[f"{i['suite']}/{i['question']}"] = by_q.get(f"{i['suite']}/{i['question']}", 0) + 1
    return {"path": str(path), "rows": len(items), **data["counts"], "by_question": dict(sorted(by_q.items()))}


# --- the public summary ----------------------------------------------------------------------------------------------

SUMMARY_HEAD = """# Disputed rows left for the owner (edition 2)

> Public copy, written by the build (`goldrails_dataset.e2_owner_review.write_summary`). It names public rows only.
> Private-slice rows count in the totals and are never named. Notes describe rows without quoting them. To decide
> rows, open `build/private/review.html` (git-ignored, holds the text) and import its export with
> `uv run python -m goldrails_dataset.edition2 import-owner-review FILE`.

Rulings are in `docs/benchmark/29-owner-rulings-2026-10-03.md`. Ruling 9 says to apply rulings 2 to 5 to disputed rows
automatically and leave the rest to you. A row was resolved only when one of those rulings decides it. Ruling 2 decides
injection and where persona prompts are filed. Ruling 3 decides Mosscap turns judged on their text. Ruling 4 decides
grounding rows that turn on a hedged claim, an omission or a concrete fact the source does not state. Ruling 5 decides
ADDRESS. Everything else is below, grouped by the question that would settle it, so one answer can settle a group.

The first pass also resolved 14 content rows under ruling 8. Ruling 9 does not name ruling 8, so those rows are back
out of the splits under question C-R8 with the proposed label attached. Confirming it keeps the proposal.

Ruling 5 also binds rows nobody disputed. A PII row whose every ADDRESS span is a bare city or state field loses ADDRESS,
and a row with nothing else left becomes benign. Those changes are in `pii/corrections.jsonl` (private-slice ids in the
git-ignored part).
"""


def write_summary(path: Path, root: Path = e2_local.E2, parts: dict | None = None) -> dict:
    """The public OWNER-REVIEW.md: counts per suite and the waiting public rows grouped by question."""
    waiting = _waiting_ids(parts)
    counts, questions, totals = {}, {}, {"public": 0, "private": 0}
    corr = {"public": 0, "private": 0, "benign": 0}
    for suite in e2_local.SUITES:
        pub, prv = _res_paths(suite, root)
        for d, private in [(d, False) for d in _jsonl(pub)] + [(d, True) for d in _jsonl(prv)]:
            if d.get("status") == "owner_review" and (waiting is None or d["id"] in waiting):
                totals["private" if private else "public"] += 1
            if private:
                continue
            c = counts.setdefault(suite, {"disputed": 0, 2: 0, 3: 0, 4: 0, 5: 0, 9: 0, "waiting": 0, "dropped": 0})
            c["disputed"] += 1
            if d.get("status") == "resolved":
                c[d.get("ruling") if d.get("ruling") in (2, 3, 4, 5) else 9] += 1
            elif waiting is not None and d["id"] not in waiting:
                c["dropped"] += 1
            else:
                c["waiting"] += 1
                questions.setdefault((suite, d.get("question") or "unruled"), []).append(d)
        for d, private in [(d, False) for d in _jsonl(e2_local.suite_dir(suite, root) / "corrections.jsonl")] + \
                [(d, True) for d in _jsonl(e2_local.private_dir(suite, root) / "corrections.jsonl")]:
            corr["private" if private else "public"] += 1
            corr["benign"] += d.get("final_label") != d.get("first_label")
    cands = {}
    lines = [SUMMARY_HEAD, f"In all, {totals['public'] + totals['private']} disputed rows wait: {totals['public']} public "
             f"and {totals['private']} private. Ruling 5 changed {corr['public'] + corr['private']} undisputed PII rows "
             f"({corr['public']} public, {corr['private']} private); {corr['benign']} of them became benign.", "",
             "## Counts, public rows", "",
             "| Suite | Disputed | Ruling 2 | Ruling 3 | Ruling 4 | Ruling 5 | Owner decided | Waiting | Dropped by the build |",
             "|---|---|---|---|---|---|---|---|---|"]
    tot = {}
    for suite, c in sorted(counts.items()):
        lines.append(f"| {suite} | {c['disputed']} | {c[2]} | {c[3]} | {c[4]} | {c[5]} | {c[9]} | {c['waiting']} | {c['dropped']} |")
        for k, v in c.items():
            tot[k] = tot.get(k, 0) + v
    if tot:
        lines.append(f"| all | {tot['disputed']} | {tot[2]} | {tot[3]} | {tot[4]} | {tot[5]} | {tot[9]} | {tot['waiting']} | "
                     f"{tot['dropped']} |")
    lines += ["", "## Questions", ""]
    for (suite, q), rows in sorted(questions.items()):
        if suite not in cands:
            cands[suite] = {c["id"]: c for c in e2_local.candidates(suite, root, private=False, text=False)}
        seconds = {r["id"]: r for r in e2_local.relabels(suite, root, private=False)} if suite else {}
        lines += [f"### {q} ({suite}, {len(rows)} rows)", "", rows[0].get("question_text") or "", "", "Your decision: ____", "",
                  "| Id | Subtask | Split | First | Second | Note |", "|---|---|---|---|---|---|"]
        for d in sorted(rows, key=lambda d: d["id"]):
            c, sec = cands.get(d["id"], {}), seconds.get(d["id"], {})
            first = f"{c.get('label', d.get('first_label'))}" + (f" {', '.join(c['entity_types'])}" if suite == "pii" and c.get("entity_types") else "")
            second = f"{sec.get('label', d.get('second_label'))}" + (f" {', '.join(sec['entity_types'])}" if suite == "pii" and sec.get("entity_types") else "")
            if sec.get("refile_subtask"):
                second += f", refile {sec['refile_subtask']}"
            note = d.get("note") or ""
            if d.get("proposed"):
                note = (f"proposed {d['proposed'].get('final_label')}: {d['proposed'].get('reason', '')}" + (f"; {note}" if note else ""))
            note = note.replace("|", "\\|")
            lines.append(f"| `{d['id']}` | {c.get('subtask', d.get('subtask'))} | {d.get('proposed_split')} | {first} | {second} | {note} |")
        lines.append("")
    Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"waiting": totals, "questions": len(questions), "ruling5_undisputed": corr}


# --- the importer ----------------------------------------------------------------------------------------------------

def _resolution(d: dict, dec: dict, first: dict) -> dict:
    """The resolution line for one owner decision (``d``: the owner_review line; ``first``: the candidate)."""
    suite = d["suite"]
    label = dec["final_label"]
    out = {k: v for k, v in d.items() if k not in ("status", "needs_owner_confirmation")}
    prop = d.get("proposed") or {}
    confirmed = d.get("question") == CONFIRM_QUESTION and prop.get("final_label") == label and not dec.get("harm_category")
    out.update(status="resolved", final_label=label, ruled_by="owner",
               decided_at=dec.get("decided_at") or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    if dec.get("note"):
        out["owner_note"] = dec["note"]
    if confirmed:
        out.update({k: v for k, v in prop.items() if k != "reason"})
        out["reason"] = f"{prop.get('reason', 'ruling 8')}; confirmed by the owner"
    else:
        out["ruling"] = 9
        out["reason"] = f"owner decision (ruling 9) on {d.get('question') or 'the dispute'}" + (
            f": {dec['note']}" if dec.get("note") else "")
    sub = dec.get("final_subtask")
    if sub and sub != first.get("subtask"):
        if sub not in SUBTASKS.get(FEATURE[suite], ()):
            raise ValueError(f"{d['id']}: subtask {sub!r} is not a {FEATURE[suite]} subtask")
        out["final_subtask"] = sub
    if suite == "pii":
        types = sorted(dec.get("final_entity_types") or [])
        if (label == "yes") != bool(types):
            raise ValueError(f"{d['id']}: PII label {label} needs {'some' if label == 'yes' else 'no'} entity types")
        unknown = set(types) - set(pii_types())
        if unknown:
            raise ValueError(f"{d['id']}: unknown entity types {sorted(unknown)}")
        out["final_entity_types"] = types
    if suite == "content" and label == "yes" and first.get("label") == "no" and not out.get("final_tags"):
        h = dec.get("harm_category")
        if h not in HARM:
            raise ValueError(f"{d['id']}: a content row ruled harmful needs harm_category, one of {sorted(HARM)}")
        ail, bed = HARM[h]
        out["final_tags"] = {"harm_category": h, "harm_categories": [h], "harm_subcategories": [], "in_bedrock_five": True}
        out["final_category"] = {"ailuminate": ail, "bedrock": bed}
    return out


def import_decisions(path: Path, root: Path = e2_local.E2) -> dict:
    """Apply an exported decisions JSONL to the resolutions files. Every line is checked before any file is written;
    a line that names an id with no owner_review line, or a decision the build would reject, raises. Lines without a
    yes or no are skipped. Returns counts."""
    decisions, undecided = {}, 0
    for d in _jsonl(Path(path)):
        if d.get("final_label") not in ("yes", "no"):
            undecided += 1
            continue
        if d["id"] in decisions:
            raise ValueError(f"{path}: {d['id']} is decided twice")
        decisions[d["id"]] = d
    done, by_suite, writes = set(), {}, {}
    for suite in e2_local.SUITES:
        cands = None
        for part in _res_paths(suite, root):
            lines = _jsonl(part)
            if not any(d["id"] in decisions for d in lines):
                continue
            if cands is None:
                cands = {c["id"]: c for c in e2_local.candidates(suite, root, text=False)}
            out = []
            for d in lines:
                dec = decisions.get(d["id"])
                if dec is not None:
                    if d.get("status") != "owner_review":
                        raise ValueError(f"{d['id']}: already {d.get('status')}; the page only decides rows waiting "
                                         "for the owner")
                    if dec.get("suite") and dec["suite"] != suite:
                        raise ValueError(f"{d['id']}: decision names suite {dec['suite']}, the row is in {suite}")
                    d = _resolution(d, dec, cands[d["id"]])
                    done.add(d["id"])
                    by_suite[suite] = by_suite.get(suite, 0) + 1
                out.append(d)
            writes[part] = sorted(out, key=lambda d: d["id"])
    missing = sorted(set(decisions) - done)
    if missing:
        raise ValueError(f"{len(missing)} decided ids have no owner_review line: {missing[:5]}")
    for part, out in writes.items():
        part.write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in out), encoding="utf-8")
    return {"applied": len(done), "by_suite": dict(sorted(by_suite.items())), "undecided_lines": undecided}


__all__ = ["review_items", "write_html", "import_decisions"]

"""Edition 2 content suite: the human second-label sample (owner ruling 7, docs/benchmark/29-owner-rulings-2026-10-03.md).

A person second-labels a 400-row stratified random sample of the content suite's public tune and test rows, and we
publish the agreement rate. docs/benchmark/30-content-sample-labelling.md is the labeller's guide.

    uv run python -m goldrails_dataset.content_sample draw               # sample, label.html, agreement.json (pending)
    uv run python -m goldrails_dataset.content_sample score LABELS.jsonl # agreement + Cohen's kappa -> agreement.json

``draw`` writes into ``dataset/edition2/content/sample/``, which is git-ignored whole: ``label.html`` embeds the row
text, much of it harmful, and some of it comes from sources whose licence is not cleared. Only
``dataset/edition2/content/agreement.json`` is tracked, and it carries counts and rates, never text.

Population: the content rows in the current build's public F1 tune and test files
(``uv run python -m goldrails_dataset.edition2``) whose id is in the tracked public ``content/candidates.jsonl``.
That leaves out the private slice, the rows the build dropped and the disputed rows still waiting for the owner.
The reference label is the label the build holds (``expected`` in the build file): the first label, or for a disputed
row resolved under an owner ruling, the final label. Strata are subtask x reference label x source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from goldrails_dataset import e2_local

SEED = 20261003
N_SAMPLE = 400
MIN_PER_STRATUM = 10
BOOTSTRAP = 2000

CONTENT = e2_local.E2 / "content"
SAMPLE_DIR = CONTENT / "sample"
AGREEMENT = CONTENT / "agreement.json"
BUILD = e2_local.E2 / "build"
REPO = e2_local.DATASET_DIR.parent
POLICY_DIR = REPO / "benchmark" / "policies" / "content"
LABELS = ("yes", "no", "unsure")
DRAFT_MARK = "DRAFT, pending owner approval"


# --- population and sample ------------------------------------------------------------------------------------------

def stratum(c: dict) -> str:
    return f"{c['subtask']}|{c['label']}|{e2_local.source_of(c)}"


def population(root: Path = e2_local.E2) -> tuple[dict, dict]:
    """(id -> public candidate without text, build file digests). Public tune and test content rows only."""
    cand = {c["id"]: c for c in e2_local.candidates("content", root, private=False, text=False)}
    ids, digests, built = set(), {}, {}
    for split in ("tune", "test"):
        p = root / "build" / f"F1.{split}.jsonl"
        if not p.exists():
            raise e2_local.LocalDataMissing(f"{p} is missing: run uv run python -m goldrails_dataset.edition2 first")
        digests[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        for line in p.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                r = json.loads(line)
                if r["id"] in cand and r.get("visibility", "public") == "public" and r["split"] == split:
                    ids.add(r["id"])
                    built[r["id"]] = r["expected"]
    pop = {i: {**cand[i], "label": built[i]} for i in sorted(ids)}
    assert all(c["split"] in ("tune", "test") and c.get("visibility") == "public" for c in pop.values())
    return pop, digests


def allocate(sizes: dict, n: int = N_SAMPLE, floor: int = MIN_PER_STRATUM) -> dict:
    """A floor of ``floor`` rows per stratum (all of it when smaller), the rest proportional to stratum size by
    largest remainder, never more than a stratum holds."""
    alloc = {s: min(floor, k) for s, k in sizes.items()}
    while sum(alloc.values()) < n:
        left = n - sum(alloc.values())
        room = {s: sizes[s] - alloc[s] for s in sizes if sizes[s] > alloc[s]}
        if not room:
            break
        total = sum(room.values())
        quota = {s: left * r / total for s, r in room.items()}
        add = {s: min(room[s], math.floor(q)) for s, q in quota.items()}
        if sum(add.values()) == 0:                  # hand out the last rows by largest remainder
            for s in sorted(quota, key=lambda s: (-(quota[s] - math.floor(quota[s])), s))[:left]:
                add[s] = 1
        for s, a in add.items():
            alloc[s] += a
    return alloc


def draw_sample(pop: dict, seed: int = SEED, n: int = N_SAMPLE) -> tuple[list, dict]:
    by = defaultdict(list)
    for i, c in pop.items():
        by[stratum(c)].append(i)
    sizes = {s: len(v) for s, v in sorted(by.items())}
    alloc = allocate(sizes, n)
    rng = random.Random(seed)
    picked = []
    for s in sorted(by):
        picked += rng.sample(sorted(by[s]), alloc[s])
    rng.shuffle(picked)                              # labelling order mixes strata
    strata = {s: {"population": sizes[s], "sample": alloc[s]} for s in sizes}
    return picked, strata


# --- the labelling page ---------------------------------------------------------------------------------------------

def _policy_docs() -> dict:
    docs = {}
    for name in ("request", "reply"):
        text = (POLICY_DIR / f"{name}.md").read_text(encoding="utf-8")
        docs[name] = {"text": text, "draft_mark": DRAFT_MARK in text}
    return docs


def _page_row(c: dict) -> dict:
    """Only what the labeller needs: no label, source, category, rationale or split."""
    st = c["state"]
    return {"id": c["id"], "kind": "reply" if c["subtask"] == "output" else "request",
            "context": [{"role": t.get("role"), "text": t.get("text")} for t in (st.get("context") or [])],
            "role": st.get("role"), "text": st.get("text")}


def _script_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def write_html(rows: list, sample_key: str, path: Path) -> None:
    template = (Path(__file__).with_name("content_sample_label.html")).read_text(encoding="utf-8")
    data = {"sample_key": sample_key, "rows": rows, "policy": _policy_docs()}
    html = template.replace("/*__DATA__*/null", _script_json(data))
    path.write_text(html, encoding="utf-8")


def draw(seed: int = SEED, n: int = N_SAMPLE) -> dict:
    pop, digests = population()
    picked, strata = draw_sample(pop, seed, n)
    full = {c["id"]: c for c in e2_local.candidates("content", private=False, text=True)}
    rows = [_page_row(full[i]) for i in picked]
    assert all(r["text"] for r in rows), "a sampled row has no text: run e2_local rehydrate content"
    sample_key = hashlib.sha256("\n".join(picked).encode()).hexdigest()[:16]
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": seed, "n": len(picked), "min_per_stratum": MIN_PER_STRATUM, "sample_key": sample_key,
                "population_rows": len(pop), "build_files": digests, "strata": strata,
                "rows": [{"id": i, "stratum": stratum(pop[i]), "split": pop[i]["split"], "reference": pop[i]["label"]}
                         for i in picked]}
    (SAMPLE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    write_html(rows, sample_key, SAMPLE_DIR / "label.html")
    write_agreement(design(manifest), None)
    return manifest


def design(manifest: dict) -> dict:
    return {k: manifest[k] for k in ("seed", "n", "min_per_stratum", "sample_key", "population_rows", "build_files",
                                     "strata")} | {
        "population": "content rows in the public F1 tune and test build files, public candidates only",
        "strata_key": "subtask|reference label|source",
        "reference": "the label the build holds: the first label, or the owner-ruling final label of a resolved dispute",
        "command": "uv run python -m goldrails_dataset.content_sample draw"}


# --- scoring --------------------------------------------------------------------------------------------------------

def load_labels(paths: list, sample_ids: set) -> tuple[str, dict]:
    """Latest label per id across the exported files. One labeller per run."""
    latest, labellers = {}, set()
    for p in paths:
        for n, line in enumerate(Path(p).read_text(encoding="utf-8").split("\n"), 1):
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("id") not in sample_ids:
                raise SystemExit(f"{p}:{n}: id is not in the sample")
            if e.get("label") not in LABELS:
                raise SystemExit(f"{p}:{n}: label must be one of {LABELS}")
            labellers.add((e.get("labeller") or "").strip())
            if e["id"] not in latest or str(e.get("timestamp", "")) >= str(latest[e["id"]].get("timestamp", "")):
                latest[e["id"]] = e
    if len(labellers) != 1 or "" in labellers:
        raise SystemExit(f"expected exactly one named labeller, got {sorted(labellers)}")
    return labellers.pop(), latest


def kappa(pairs: list, weights: list | None = None) -> float | None:
    """Cohen's kappa for (reference, human) yes/no pairs, optionally weighted. None when chance agreement is 1."""
    w = weights or [1.0] * len(pairs)
    tot = sum(w)
    if not tot:
        return None
    po = sum(wi for (a, b), wi in zip(pairs, w) if a == b) / tot
    pa = sum(wi for (a, _), wi in zip(pairs, w) if a == "yes") / tot
    pb = sum(wi for (_, b), wi in zip(pairs, w) if b == "yes") / tot
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe >= 1 - 1e-12 else (po - pe) / (1 - pe)


def _rnd(x):
    return None if x is None else round(x, 4)


def summary(items: list) -> dict:
    """items: (reference, human label) with human in yes/no/unsure. Kappa is left out (None) when the first label
    takes one value in the group, as it always does within a stratum: chance agreement then equals the observed
    agreement and kappa says nothing. Read ``agreement`` there, and kappa on the overall and mixed groups."""
    decided = [(a, b) for a, b in items if b != "unsure"]
    one_class = len({a for a, _ in decided}) < 2
    agree = sum(a == b for a, b in decided)
    conf = Counter(f"{a}->{b}" for a, b in decided)
    out = {"labelled": len(items), "unsure": len(items) - len(decided), "decided": len(decided),
           "agree": agree, "agreement": _rnd(agree / len(decided)) if decided else None,
           "agreement_unsure_as_disagree": _rnd(agree / len(items)) if items else None,
           "confusion_first_to_human": dict(sorted(conf.items())), "kappa": None if one_class else _rnd(kappa(decided))}
    if one_class:
        out["kappa_note"] = "first label takes one value in this group, so kappa is undefined; read agreement"
    return out


def bootstrap_ci(by_stratum: dict, seed: int, reps: int = BOOTSTRAP) -> dict:
    """Stratified bootstrap 95% interval for overall agreement and kappa (decided rows)."""
    rng = random.Random(seed)
    ag, ka = [], []
    strata = [v for v in by_stratum.values() if v]
    for _ in range(reps):
        res = [p for v in strata for p in (rng.choice(v) for _ in v)]
        if res:
            ag.append(sum(a == b for a, b in res) / len(res))
            k = kappa(res)
            if k is not None:
                ka.append(k)

    def ci(xs):
        if not xs:
            return None
        xs = sorted(xs)
        return [_rnd(xs[int(0.025 * (len(xs) - 1))]), _rnd(xs[int(0.975 * (len(xs) - 1))])]
    return {"method": f"stratified bootstrap, {reps} reps, seed {seed}", "agreement_95": ci(ag), "kappa_95": ci(ka)}


def score(paths: list, manifest_path: Path = SAMPLE_DIR / "manifest.json") -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ref = {c["id"]: c for c in e2_local.candidates("content", private=False, text=False)}
    rows = {r["id"]: r for r in manifest["rows"]}
    labeller, labels = load_labels(paths, set(rows))
    items = {i: (rows[i].get("reference", ref[i]["label"]), e["label"]) for i, e in labels.items()}

    groups = defaultdict(lambda: defaultdict(list))
    for i, pair in items.items():
        st = rows[i]["stratum"]
        sub, _, src = st.split("|")
        for g, key in (("stratum", st), ("subtask", sub), ("source", src), ("split", rows[i]["split"])):
            groups[g][key].append(pair)
    per = {g: {k: summary(v) for k, v in sorted(d.items())}
           for g, d in groups.items()}

    # Population-weighted agreement and kappa: each decided row weighs population/sample of its stratum.
    strata = manifest["strata"]
    wpairs, w = [], []
    decided_by_stratum = defaultdict(list)
    for i, (a, b) in items.items():
        if b == "unsure":
            continue
        s = rows[i]["stratum"]
        wpairs.append((a, b))
        w.append(strata[s]["population"] / strata[s]["sample"])
        decided_by_stratum[s].append((a, b))
    wag = sum(wi for (a, b), wi in zip(wpairs, w) if a == b) / sum(w) if w else None

    overall = summary(list(items.values()))
    overall |= {"agreement_population_weighted": _rnd(wag), "kappa_population_weighted": _rnd(kappa(wpairs, w))}
    overall |= bootstrap_ci(decided_by_stratum, manifest["seed"])
    result = {"labeller": labeller, "coverage": f"{len(items)}/{manifest['n']}",
              "complete": len(items) == manifest["n"], "overall": overall,
              "by_stratum": per.get("stratum", {}), "by_subtask": per.get("subtask", {}),
              "by_source": per.get("source", {}), "by_split": per.get("split", {}),
              "label_files_sha256": sorted(hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths)}
    write_agreement(design(manifest), result)
    return result


def write_agreement(des: dict, result: dict | None) -> None:
    doc = {"suite": "content", "ruling": "7 (docs/benchmark/29-owner-rulings-2026-10-03.md)",
           "guide": "docs/benchmark/30-content-sample-labelling.md",
           "status": "awaiting labels" if result is None else ("complete" if result["complete"] else "partial"),
           "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "design": des,
           "result": result}
    AGREEMENT.write_text(json.dumps(doc, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="goldrails_dataset.content_sample", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draw", help="draw the sample, write label.html and a pending agreement.json")
    d.add_argument("--seed", type=int, default=SEED)
    s = sub.add_parser("score", help="score exported labels into agreement.json")
    s.add_argument("labels", nargs="+", help="JSONL exported from label.html")
    a = ap.parse_args(argv)
    if a.cmd == "draw":
        m = draw(a.seed)
        print(f"sample of {m['n']} from {m['population_rows']} rows, seed {m['seed']}, key {m['sample_key']}")
        for k, v in m["strata"].items():
            print(f"  {k:55s} {v['sample']:4d} / {v['population']}")
        print(f"wrote {SAMPLE_DIR / 'label.html'} (git-ignored) and {AGREEMENT}")
    else:
        r = score(a.labels)
        o = r["overall"]
        print(f"{r['labeller']}: {r['coverage']} labelled, agreement {o['agreement']}, kappa {o['kappa']}, "
              f"unsure {o['unsure']}; wrote {AGREEMENT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

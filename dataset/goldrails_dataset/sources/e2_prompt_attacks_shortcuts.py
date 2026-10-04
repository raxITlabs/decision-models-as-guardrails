"""Shortcut baselines for the edition 2 prompt-attack rows: can something that never reads the attack, or that only
counts surface strings, tell the classes apart?

Five baselines per subtask, each reported as AUROC and balanced accuracy (BA), direction-free (max(x, 1 - x)):

- ``source_id``: the attack rate of the row's source in the training rows (fitted). BA predicts yes when that rate is
  above one half.
- ``keyword_regex``: 1 when the text matches ``password|secret|pwd|mosscap|gandalf`` (fixed, not fitted).
- ``length``: character length. AUROC is direction-free on the raw length; BA uses the threshold and direction that
  maximise BA on the training rows.
- ``char_ngram_logreg``: L2 logistic regression on TF-IDF character 2-5-grams (``char_wb``), balanced class weights,
  with C chosen from ``C_GRID`` by grouped inner cross-validation on the training rows only (mean inner-fold AUROC).
  BA at probability 0.5.
- ``bow_logreg``: the same L2 logistic regression and inner-CV choice of C on TF-IDF word 1-2-grams.

The two text models need scikit-learn, which is not a project dependency:
``uv run --with scikit-learn python -m goldrails_dataset.sources.e2_prompt_attacks_shortcuts``.

A fitted text model that gives every scored row the same score (a fit that kept no signal), or a source model whose
scored rows all come from sources it never saw, is a failure, not a pass: BA and AUROC 0.5 from a constant say the model did not fit, not that the
rows are hard. Until 4 October the n-gram model was L1 with C = 1, and on the injection and jailbreak halves it kept no
weight, so its 0.500 / 0.500 "pass" meant nothing (ADVERSARIAL-FILTERING.md).

Views (``gate_report``), every baseline in every view, rows as the build holds them:

- in sample: grouped five-fold CV (``separability.folds_of``; a near-duplicate group never straddles folds) on the
  public test split, and on the test split with the unpublished slice (``proposed_split`` private);
- held back, fitted on rows they then do not score: seeded group halves of test and unpublished, both directions;
  dev to the public test split; dev to the unpublished slice; test and unpublished to dev; dev and a seeded 70% of
  the test and unpublished groups to the other 30%.

A cell passes when the baseline was computed, did not predict a constant, and has BA <= ``BA_TARGET`` and AUROC <=
``AUROC_TARGET``. The gate (``goldrails_dataset.edition2.shortcut_gate``) passes only when every cell passes.

    uv run --with scikit-learn python -m goldrails_dataset.sources.e2_prompt_attacks_shortcuts [--split test]
    uv run --with scikit-learn python -m goldrails_dataset.sources.e2_prompt_attacks_shortcuts --gate [--markdown]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import warnings
from collections import defaultdict

from ..separability import auroc, folds_of, sklearn_available

KEYWORDS = re.compile(r"password|secret|pwd|mosscap|gandalf", re.I)
BA_TARGET = 0.70
AUROC_TARGET = 0.75
SUBTASKS = ("injection", "jailbreak", "leakage")
BASELINES = ("source_id", "keyword_regex", "length", "char_ngram_logreg", "bow_logreg")
TEXT_MODELS = ("char_ngram_logreg", "bow_logreg")          # need scikit-learn
FITTED = ("source_id", "length", "char_ngram_logreg", "bow_logreg")
CONSTANT_CHECKED = ("source_id", "char_ngram_logreg", "bow_logreg")   # length's AUROC reads the raw length
C_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
INNER_FOLDS = 5
HELDBACK_SEED = 20261004          # the seeded halves
SEEDED_GROUPS_SEED = 20261003     # the seeded 30% of test and unpublished groups
SEEDED_GROUPS_SHARE = 0.3


# --- metrics --------------------------------------------------------------------------------------------------------

def balanced_accuracy(pred, labels) -> float:
    pos = [p for p, y in zip(pred, labels) if y]
    neg = [p for p, y in zip(pred, labels) if not y]
    ba = (sum(pos) / len(pos) + sum(1 - p for p in neg) / len(neg)) / 2
    return max(ba, 1 - ba)


def _free(a: float) -> float:
    return max(a, 1 - a)


def _constant(scores) -> bool:
    return len({round(float(s), 9) for s in scores}) <= 1


def _labels(rows):
    return [1 if r["label"] == "yes" else 0 for r in rows]


def _group(r):
    return r.get("group") or r["id"]


# --- the fitted baselines: fit on rows, score rows; each returns (scores, predictions, meta) -------------------------

def _source_fit_predict(train, y, test):
    """Source attack rate per scored row (the training prior for an unseen source)."""
    hits, n = defaultdict(int), defaultdict(int)
    for s, lab in zip(train, y):
        hits[s] += lab
        n[s] += 1
    prior = sum(y) / len(y)
    return [hits[s] / n[s] if n[s] else prior for s in test]


def _best_threshold(values, y):
    """(threshold, sign) maximising BA of ``sign * value >= threshold`` on the training rows."""
    pos, neg = sum(y), len(y) - sum(y)
    best = (0.5, 0.0, 1)
    for sign in (1, -1):
        pairs = sorted(((sign * v, lab) for v, lab in zip(values, y)), reverse=True)
        tp = fp = 0
        for i, (v, lab) in enumerate(pairs):
            tp += lab
            fp += 1 - lab
            if i + 1 < len(pairs) and pairs[i + 1][0] == v:
                continue
            ba = (tp / pos + 1 - fp / neg) / 2
            if ba > best[0]:
                best = (ba, v, sign)
    return best[1], best[2]


def _length_fit_predict(train, y, test):
    thr, sign = _best_threshold([len(t) for t in train], y)
    return [1.0 if sign * len(t) >= thr else 0.0 for t in test]


def _vectorizer(kind: str):
    from sklearn.feature_extraction.text import TfidfVectorizer
    if kind == "char_ngram_logreg":
        return TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=200000)
    return TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                           token_pattern=r"(?u)\b\w+\b", max_features=200000)


def _classifier(c: float):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=c, solver="liblinear", class_weight="balanced", max_iter=2000)   # L2, the default


def choose_c(kind: str, texts: list, y: list, groups: list, grid=C_GRID, k: int = INNER_FOLDS) -> tuple[float, dict]:
    """C for an L2 text model by grouped inner CV on the training rows only: the grid value with the highest mean
    inner-fold AUROC (signed, not direction-free; ties go to the smaller C). The vectoriser is refitted per inner fold."""
    folds = folds_of(groups, k)
    per = {c: [] for c in grid}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for f in sorted(set(folds)):
            tr = [i for i, x in enumerate(folds) if x != f]
            te = [i for i, x in enumerate(folds) if x == f]
            ytr, yte = [y[i] for i in tr], [y[i] for i in te]
            if len(set(ytr)) < 2 or len(set(yte)) < 2:
                continue
            try:
                vec = _vectorizer(kind)
                xtr = vec.fit_transform([texts[i] for i in tr])
            except ValueError:          # an empty vocabulary
                continue
            xte = vec.transform([texts[i] for i in te])
            for c in grid:
                per[c].append(auroc(list(_classifier(c).fit(xtr, ytr).decision_function(xte)), yte))
    means = {c: sum(v) / len(v) for c, v in per.items() if v}
    if not means:
        return 1.0, {}
    best = max(sorted(means), key=lambda c: (means[c], -c))
    return best, {str(c): round(m, 3) for c, m in sorted(means.items())}


_LAST_C: dict = {}     # the C each text model chose on its latest fit, read once by ``_fit_score`` for the report


def _text_fit_predict(kind: str, train_texts, y, test_texts, groups):
    """Probability of yes per scored text, and the chosen C."""
    c, _ = choose_c(kind, train_texts, y, groups)
    _LAST_C[kind] = c
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            vec = _vectorizer(kind)
            x = vec.fit_transform(train_texts)
        except ValueError:               # no feature survives min_df: the model can only predict a constant
            return [sum(y) / len(y)] * len(test_texts), c
        p = _classifier(c).fit(x, y).predict_proba(vec.transform(test_texts))[:, 1]
    return [float(v) for v in p], c


def _logreg_fit_predict(train, y, test, groups=None):
    """The char n-gram model alone (kept as a hook: tests replace it)."""
    return _text_fit_predict("char_ngram_logreg", train, y, test, groups or list(range(len(train))))[0]


def _bow_fit_predict(train, y, test, groups=None):
    return _text_fit_predict("bow_logreg", train, y, test, groups or list(range(len(train))))[0]


def _fit_score(name: str, train: list, score: list) -> tuple[list, list, dict]:
    """One baseline fitted on ``train`` rows, applied to ``score`` rows: (AUROC scores, BA predictions, meta)."""
    y = _labels(train)
    texts = [r["state"]["text"] for r in score]
    if name == "source_id":
        s = _source_fit_predict([r["source"] for r in train], y, [r["source"] for r in score])
        seen = {r["source"] for r in train}
        unseen = sum(r["source"] not in seen for r in score) / len(score)
        return s, [1.0 if v > 0.5 else 0.0 for v in s], {"unseen_source_share": round(unseen, 3)}
    if name == "keyword_regex":
        k = [1.0 if KEYWORDS.search(t) else 0.0 for t in texts]
        return k, k, {}
    if name == "length":
        return ([float(len(t)) for t in texts],
                _length_fit_predict([r["state"]["text"] for r in train], y, texts), {})
    tr_texts, groups = [r["state"]["text"] for r in train], [_group(r) for r in train]
    if name == "char_ngram_logreg":
        p = _logreg_fit_predict(tr_texts, y, texts, groups)
        c = _LAST_C.pop("char_ngram_logreg", None)
    else:
        p = _bow_fit_predict(tr_texts, y, texts, groups)
        c = _LAST_C.pop("bow_logreg", None)
    p = [float(v) for v in p]
    return p, [1.0 if v >= 0.5 else 0.0 for v in p], ({"C": c} if c is not None else {})


def _failed_fit(name: str, scores, meta: dict) -> bool:
    """A fit that gave every scored row one score and so says nothing: a text model always; the source model only
    when no scored row's source was in its training rows (a constant from sources with equal attack rates is a working
    fit that found no source signal)."""
    if name not in CONSTANT_CHECKED or len(scores) < 2 or not _constant(scores):
        return False
    return name != "source_id" or meta.get("unseen_source_share") == 1.0


def _baselines(use_sklearn: bool | None) -> tuple:
    use = sklearn_available() if use_sklearn is None else use_sklearn
    return BASELINES if use else tuple(b for b in BASELINES if b not in TEXT_MODELS)


def _cell(name: str, scores, preds, labels, constant: bool, meta: dict) -> dict:
    v = {"auroc": round(_free(auroc(scores, labels)), 3), "ba": round(balanced_accuracy(preds, labels), 3)}
    if name in CONSTANT_CHECKED:
        v["constant_prediction"] = bool(constant)
    v.update(meta)
    v["meets_target"] = bool(v["ba"] <= BA_TARGET and v["auroc"] <= AUROC_TARGET and not v.get("constant_prediction"))
    return v


def subtask_report(rows: list, use_sklearn: bool | None = None) -> dict:
    """In sample: every baseline with grouped five-fold CV on ``rows`` (one subtask, both classes; fitted baselines
    out of fold). ``constant_prediction`` is true when any fold's fit scored its fold with one value."""
    labels = _labels(rows)
    folds = folds_of([_group(r) for r in rows])
    out = {}
    for name in _baselines(use_sklearn):
        scores, preds, const, cs = [0.0] * len(rows), [0.0] * len(rows), False, []
        for f in sorted(set(folds)):
            tr = [i for i, x in enumerate(folds) if x != f]
            te = [i for i, x in enumerate(folds) if x == f]
            if not te or len({labels[i] for i in tr}) < 2:
                continue
            s, p, meta = _fit_score(name, [rows[i] for i in tr], [rows[i] for i in te])
            const = const or _failed_fit(name, s, meta)
            if "C" in meta:
                cs.append(meta["C"])
            for i, a, b in zip(te, s, p):
                scores[i], preds[i] = float(a), float(b)
        out[name] = _cell(name, scores, preds, labels, const, {"C": cs} if cs else {})
    return out


def transfer_report(train: list, test: list, use_sklearn: bool | None = None) -> dict:
    """Held back: every baseline fitted on ``train`` rows and scored on ``test`` rows (one subtask; both need both
    classes). Metrics as in ``subtask_report``."""
    y = _labels(test)
    out = {}
    for name in _baselines(use_sklearn):
        s, p, meta = _fit_score(name, train, test)
        out[name] = _cell(name, s, p, y, _failed_fit(name, s, meta), meta)
    return out


# --- views -----------------------------------------------------------------------------------------------------------

def seeded_halves(rows: list, seed: int = HELDBACK_SEED) -> tuple[list, list]:
    """Two halves of ``rows`` by whole group (sorted group names, shuffled with ``seed``), so no near-copy straddles."""
    groups = sorted({_group(r) for r in rows})
    random.Random(seed).shuffle(groups)
    first = set(groups[: len(groups) // 2])
    return [r for r in rows if _group(r) in first], [r for r in rows if _group(r) not in first]


def seeded_groups(rows: list, share: float = SEEDED_GROUPS_SHARE, seed: int = SEEDED_GROUPS_SEED) -> set:
    """A seeded share of the groups of ``rows`` (whole groups)."""
    groups = sorted({_group(r) for r in rows})
    random.Random(seed).shuffle(groups)
    return set(groups[:round(len(groups) * share)])


IN_SAMPLE_VIEWS = ("in_sample_public_test", "in_sample_test_with_private")
HELDBACK_VIEWS = ("heldback_half_a_to_half_b", "heldback_half_b_to_half_a", "heldback_dev_to_public_test",
                  "heldback_dev_to_private", "heldback_test_and_private_to_dev", "heldback_seeded_groups")
VIEW_NOTES = {
    "in_sample_public_test": "grouped five-fold CV on the public test split",
    "in_sample_test_with_private": "grouped five-fold CV on the public test split with the unpublished slice",
    "heldback_half_a_to_half_b": f"fit on one seeded group half of test and unpublished (seed {HELDBACK_SEED}), "
                                 "score the other",
    "heldback_half_b_to_half_a": "the same halves, the other direction",
    "heldback_dev_to_public_test": "fit on dev, score the public test split",
    "heldback_dev_to_private": "fit on dev, score the unpublished slice",
    "heldback_test_and_private_to_dev": "fit on test and unpublished, score dev",
    "heldback_seeded_groups": f"fit on dev and {round(100 * (1 - SEEDED_GROUPS_SHARE))}% of the test and unpublished "
                              f"groups, score the other {round(100 * SEEDED_GROUPS_SHARE)}% (seed {SEEDED_GROUPS_SEED})",
}


def views_of(rows: list, which=None) -> dict:
    """{view: ("cv", None, rows) | ("fit", train, score)} over rows with ``proposed_split`` dev, test or private.
    Views that need the unpublished slice are left out when it is absent (a public checkout)."""
    by = {k: [r for r in rows if r["proposed_split"] == k] for k in ("dev", "test", "private")}
    pool = by["test"] + by["private"]
    a, b = seeded_halves(pool)
    held = seeded_groups(pool)
    v = {"in_sample_public_test": ("cv", None, by["test"]),
         "in_sample_test_with_private": ("cv", None, pool),
         "heldback_half_a_to_half_b": ("fit", a, b),
         "heldback_half_b_to_half_a": ("fit", b, a),
         "heldback_dev_to_public_test": ("fit", by["dev"], by["test"]),
         "heldback_dev_to_private": ("fit", by["dev"], by["private"]),
         "heldback_test_and_private_to_dev": ("fit", pool, by["dev"]),
         "heldback_seeded_groups": ("fit", by["dev"] + [r for r in pool if _group(r) not in held],
                                    [r for r in pool if _group(r) in held])}
    if not by["private"]:
        v.pop("in_sample_test_with_private")
        v.pop("heldback_dev_to_private")
    return {k: x for k, x in v.items() if which is None or k in which}


def _counts(rs):
    return {"n_yes": sum(r["label"] == "yes" for r in rs), "n_no": sum(r["label"] == "no" for r in rs)}


def gate_report(rows: list, use_sklearn: bool | None = None, which=None) -> dict:
    """Every baseline of every subtask in every view (``views_of``), with a flat table and the failures. A cell fails
    when a baseline was not computed (scikit-learn missing), predicted a constant, or is over either bound; a view
    subtask without both classes on either side fails too."""
    use = sklearn_available() if use_sklearn is None else use_sklearn
    out, table, failures = {}, [], []
    for view, (kind, train, score) in views_of(rows, which).items():
        per = {}
        for sub in SUBTASKS:
            sc = [r for r in score if r["subtask"] == sub]
            tr = [r for r in (train or []) if r["subtask"] == sub]
            cell = {"scored": _counts(sc)}
            if kind == "fit":
                cell["fitted_on"] = _counts(tr)
            if min(cell["scored"].values()) == 0 or (kind == "fit" and min(cell["fitted_on"].values()) == 0):
                cell["error"] = "needs both classes"
                failures.append(f"{view}/{sub}: needs both classes")
                per[sub] = cell
                continue
            rep = subtask_report(sc, use) if kind == "cv" else transfer_report(tr, sc, use)
            for b in BASELINES:
                if b not in rep:
                    cell[b] = {"computed": False, "pass": False,
                               "reason": "not computed: needs scikit-learn (uv run --with scikit-learn ...)"}
                    failures.append(f"{view}/{sub}/{b}: not computed (needs scikit-learn)")
                    continue
                v = {k: x for k, x in rep[b].items() if k != "meets_target"}
                # the gate applies the rule itself (both bounds, not a constant), whatever the report says
                v["pass"] = bool(v["ba"] <= BA_TARGET and v["auroc"] <= AUROC_TARGET
                                 and not v.get("constant_prediction") and rep[b].get("meets_target", True))
                if v.get("constant_prediction"):
                    failures.append(f"{view}/{sub}/{b}: constant prediction (the fit failed; not a pass)")
                elif not v["pass"]:
                    failures.append(f"{view}/{sub}/{b}: BA {v['ba']}, AUROC {v['auroc']}")
                cell[b] = v
                table.append({"subtask": sub, "baseline": b, "view": view, "ba": v["ba"], "auroc": v["auroc"],
                              "constant_prediction": bool(v.get("constant_prediction")), "C": v.get("C"),
                              "pass": v["pass"]})
            per[sub] = cell
        out[view] = per
    return {"bounds": {"ba_max": BA_TARGET, "auroc_max": AUROC_TARGET},
            "baselines": list(BASELINES), "c_grid": list(C_GRID), "inner_folds": INNER_FOLDS,
            "seeds": {"halves": HELDBACK_SEED, "seeded_groups": SEEDED_GROUPS_SEED,
                      "seeded_groups_share": SEEDED_GROUPS_SHARE},
            "view_notes": {k: VIEW_NOTES[k] for k in out}, "views": out, "table": table, "failures": failures,
            "pass": not failures}


def heldback_report(rows: list, use_sklearn: bool | None = None, seed: int = HELDBACK_SEED) -> dict:
    """The held-back views of ``gate_report`` only (``seed`` is fixed at HELDBACK_SEED; kept for callers).
    ``over_bounds`` lists every failing cell, constant fits included."""
    rep = gate_report(rows, use_sklearn, HELDBACK_VIEWS)
    rep["seed"] = seed
    rep["over_bounds"] = rep["failures"]
    return rep


def table_markdown(rep: dict) -> str:
    """The gate table as Markdown: one line per subtask and view, one column per baseline (BA / AUROC; a failing cell
    in bold, a constant fit marked)."""
    head = "| Subtask | View | " + " | ".join(rep["baselines"]) + " |"
    lines = [head, "|" + "---|" * (2 + len(rep["baselines"]))]
    for sub in SUBTASKS:
        for view, per in rep["views"].items():
            cell = per.get(sub, {})
            if "error" in cell:
                lines.append(f"| {sub} | {view} | " + " | ".join(cell["error"] for _ in rep["baselines"]) + " |")
                continue
            vals = []
            for b in rep["baselines"]:
                v = cell.get(b, {})
                if not v.get("computed", True):
                    vals.append("not computed")
                    continue
                s = f"{v['ba']:.3f} / {v['auroc']:.3f}"
                if v.get("constant_prediction"):
                    s += " (constant)"
                vals.append(s if v["pass"] else f"**{s}**")
            lines.append(f"| {sub} | {view} | " + " | ".join(vals) + " |")
    return "\n".join(lines)


def report(cands: list, splits=None, use_sklearn: bool | None = None) -> dict:
    rows = [c for c in cands if splits is None or c["proposed_split"] in splits]
    out = {}
    for sub in SUBTASKS:
        rs = [c for c in rows if c["subtask"] == sub]
        out[sub] = {"n_yes": sum(c["label"] == "yes" for c in rs), "n_no": sum(c["label"] == "no" for c in rs),
                    **subtask_report(rs, use_sklearn)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", action="append", help="proposed split(s) to score (default: all rows)")
    ap.add_argument("--file", help="a candidates.jsonl with text (default: the suite, via e2_local)")
    ap.add_argument("--heldback", action="store_true", help="the held-back views only, on the rows as the build "
                                                            "would hold them")
    ap.add_argument("--gate", action="store_true", help="every view (in sample and held back) on the projected rows")
    ap.add_argument("--markdown", action="store_true", help="with --gate or --heldback: print the table as Markdown")
    a = ap.parse_args(argv)
    if a.file:
        cands = [json.loads(l) for l in open(a.file, encoding="utf-8") if l.strip()]
    else:
        from .. import e2_local
        cands = e2_local.candidates("prompt_attacks")
    if a.heldback or a.gate:
        from . import e2_prompt_attacks_build as build
        from .. import e2_local
        seconds = {} if a.file else {d["id"]: d for d in e2_local.relabels("prompt_attacks")}
        rows = build.projected(cands, seconds, {} if a.file else build.resolutions())
        rep = gate_report(rows) if a.gate else heldback_report(rows)
        print(table_markdown(rep) if a.markdown else json.dumps(rep, indent=2))
        return 0
    print(json.dumps(report(cands, a.split), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

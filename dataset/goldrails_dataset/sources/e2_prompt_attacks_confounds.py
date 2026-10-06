"""The confounds-only gate for the edition 2 prompt-attack suite (owner ruling 26, 6 October 2026).

Attack wording is the task signal, so a full-text n-gram model that separates attacks from benign rows is doing the
task, not finding a shortcut. Ruling 26 asks a narrower question: can a model that sees only *nuisance* features
(things that should not decide the label) tell the classes apart on groups it was not fitted on?

Nuisance models (pass/fail: each at or under BA 0.70 and AUROC 0.75, direction-free, in every view):

- ``source_id``: the attack rate of the row's source in the training rows.
- ``length``: character length of the judged text (AUROC on the raw length, BA at the training-optimal threshold).
- ``format_logreg``: L2 logistic regression on format flags (line-count bin, code fence, URL, bracketed placeholder,
  markup, list lines, share of non-ASCII characters in bins).
- ``nuisance_logreg``: L2 logistic regression on every categorical nuisance feature at once, one-hot: source,
  platform, language, carrier or document type, template (framing, task or system-prompt template), payload position
  (start, middle, end, or none for direct rows), the format flags and a log2 length bin. C by grouped inner CV.
- ``nuisance_gbt``: gradient-boosted trees on the same features (categorical splits, raw log length), so
  interactions such as "long rows from platform X" count too.
- ``context_logreg``: word 1-2-grams of what the system sees besides the judged text (context turns, tool call): the
  system prompt and the user's task for indirect rows.
- ``masked_text_logreg`` (rows with an inserted span: indirect rows): word 1-2-grams and character 2-5-grams of the
  judged text with the inserted span (the payload, or the benign edit at the same place) replaced by one mask token.
  A clean document carries the mask at its matched position. This tests that the document around the payload does
  not give the label away.
- ``neighbours_logreg`` (rows with a span): word 1-2-grams of the ``NEIGHBOUR_CHARS`` characters on each side of the
  span, the ruling 25 failure mode, where a model read the sentences next to the instruction.

Language and format are read from the document around the span when a row has one: a payload's own language or
layout is content, not nuisance.

Family, author and template identifiers are grouping variables, not features: a payload family exists only in attack
rows, so as a feature it would be the label itself. The views hold them out instead (the builder joins rows that share
a payload family, a document or a donor text into one group, and assigns payloads, carriers and templates to splits
disjointly). Templates shared by both classes (task, system prompt, frame) are features of ``nuisance_logreg``.

Reported baselines (not pass/fail, ruling 26): the full-text models of the ruling 25 gate (``char_ngram_logreg``
char_wb 2-5, ``char_cross_logreg`` char 3-6, ``bow_logreg`` word 1-2, ``word13_logreg``, ``word14_logreg``) and the
keyword regex, per subtask: BA at probability 0.5 and AUROC. The grouped-CV BA on test + unpublished is the number
published beside every system.

Fit status of a cell:

- ``fit``: a model was fitted and scored the rows; the bounds apply.
- ``constant``: fitted without error, but every row scores alike because the features carry nothing (one language
  everywhere, identical masked twins). Recorded as constant with BA and AUROC 0.5; it passes (ruling 26: "a constant
  fit on uninformative features is recorded as such, not as a failure").
- ``no_input``: nothing to read (no training row has context). Not applicable; passes.
- ``error``: an exception, an empty vocabulary on non-empty input, or a solver that did not converge. A failure.

Independent groups. A cell is scored only when its scored rows hold at least ``MIN_GROUPS_PER_CLASS`` distinct groups
of each class and its training rows at least ``MIN_TRAIN_GROUPS_PER_CLASS``. A whole-subtask view that is too small
fails; a stratum, source or facet that is too small is listed under ``not_fitted_small``.

Confidence bounds. Each scored cell carries a 95% cluster-bootstrap interval for AUROC and BA (``BOOTSTRAP``
resamples of whole groups, seeded). The pass rule uses the point estimate; the intervals are recorded.

Controls, shipped with the report: planted signals (a platform value, a length shift, a token outside the masked span,
each on 80% of attack rows; the models that should see each must break a bound) and label permutation (labels
shuffled across whole groups; every model must stay inside the bounds).

    uv run --with scikit-learn python -m goldrails_dataset.sources.e2_prompt_attacks_confounds --file rows.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import warnings
from collections import Counter, defaultdict

from ..separability import auroc, folds_of, sklearn_available
from . import e2_prompt_attacks_shortcuts as sc
from .e2_prompt_attacks_common import is_english

BA_MAX = 0.70
AUROC_MAX = 0.75
CONFOUND_MODELS = ("source_id", "length", "format_logreg", "nuisance_logreg", "nuisance_gbt", "context_logreg",
                   "masked_text_logreg", "neighbours_logreg")
SKLEARN_MODELS = ("format_logreg", "nuisance_logreg", "nuisance_gbt", "context_logreg", "masked_text_logreg",
                  "neighbours_logreg")
SPAN_MODELS = ("masked_text_logreg", "neighbours_logreg")
NGRAM_BASELINES = ("keyword_regex", "char_ngram_logreg", "char_cross_logreg", "bow_logreg", "word13_logreg",
                   "word14_logreg")
CATEGORICAL = ("source", "platform", "language", "carrier_kind", "template", "position")
FORMAT_FLAGS = ("lines", "code_fence", "url", "placeholder", "markup", "list_lines", "non_ascii")
MASK = " qqmaskqq "              # one token the vectorisers keep, in place of the inserted span
NEIGHBOUR_CHARS = 300
MIN_GROUPS_PER_CLASS = 20
MIN_TRAIN_GROUPS_PER_CLASS = 10
BOOTSTRAP = 200
BOOTSTRAP_SEED = 20261006
C_GRID = sc.C_GRID
INNER_FOLDS = sc.INNER_FOLDS
GBT = {"max_iter": 150, "learning_rate": 0.1, "max_leaf_nodes": 15, "min_samples_leaf": 20, "l2_regularization": 1.0,
       "random_state": 20261006}
MAX_CATEGORIES = 200             # per categorical feature for the trees; rarer values are treated as missing
PERMUTATIONS = 5
PERMUTATION_SEED = 20261007
CONTROL_SAMPLE = 1200
WORKERS_ENV = sc.WORKERS_ENV


# --- features ----------------------------------------------------------------------------------------------------------

_URL = re.compile(r"https?://|www\.", re.I)
_PLACEHOLDER = re.compile(r"\[[A-Z_ ]{3,}\]|\{[a-z_]{2,}\}")
_MARKUP = re.compile(r"</?[a-z][a-z0-9]*[ >/]|\*\*|^#{1,6} ", re.I | re.M)
_LIST = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s", re.M)


def _bin(v: float, edges) -> str:
    for i, e in enumerate(edges):
        if v < e:
            return str(i)
    return str(len(edges))


def format_flags(text: str) -> dict:
    """Layout of a text, coarse on purpose: these describe format, not wording."""
    n_lines = text.count("\n") + 1 if text else 0
    na = sum(1 for ch in text if ord(ch) > 127) / max(1, len(text))
    return {"lines": _bin(n_lines, (2, 4, 8, 16, 32)), "code_fence": str("```" in text),
            "url": str(bool(_URL.search(text))), "placeholder": str(bool(_PLACEHOLDER.search(text))),
            "markup": str(bool(_MARKUP.search(text))), "list_lines": _bin(len(_LIST.findall(text)), (1, 3, 8)),
            "non_ascii": _bin(na, (0.001, 0.02, 0.1))}


def length_bin(n: int) -> str:
    return str(int(math.log2(max(1, n))))


def judged_text(r: dict) -> str:
    return sc.gate_text(r.get("state"))


def span_of(r: dict) -> tuple[int, int] | None:
    """The inserted span (start, end) in the judged text, or None for a row without one."""
    sp = (r.get("nuisance") or {}).get("span")
    if not sp:
        return None
    s, e = int(sp[0]), int(sp[1])
    n = len(judged_text(r))
    if not (0 <= s <= e <= n):
        raise ValueError(f"{r.get('id')}: span {sp} outside the text ({n} characters)")
    return s, e


def masked_text(r: dict) -> str:
    sp = span_of(r)
    if sp is None:
        return ""
    t = judged_text(r)
    return t[:sp[0]] + MASK + t[sp[1]:]


def neighbours_text(r: dict) -> str:
    sp = span_of(r)
    if sp is None:
        return ""
    t = judged_text(r)
    return t[max(0, sp[0] - NEIGHBOUR_CHARS):sp[0]] + MASK + t[sp[1]:sp[1] + NEIGHBOUR_CHARS]


def nuisance_of(r: dict) -> dict:
    """The nuisance features of a row: what the builder recorded (``r["nuisance"]``), the rest derived."""
    n = r.get("nuisance") or {}
    t = judged_text(r)
    sp = span_of(r)
    doc = t[:sp[0]] + t[sp[1]:] if sp else t
    out = {"source": str(r.get("source") or "unknown"),
           "platform": str(n.get("platform") or r.get("source") or "unknown"),
           "language": str(n.get("language") or ("en" if is_english(doc or " ") else "other")),
           "carrier_kind": str(n.get("carrier_kind") or "direct"),
           "template": str(n.get("template") or "none"),
           "position": str(n.get("position") or "none")}
    out.update(format_flags(doc))
    out["length_bin"] = length_bin(len(t))
    out["log_length"] = math.log1p(len(t))
    return out


def _labels(rows):
    return [1 if r["label"] == "yes" else 0 for r in rows]


def _group(r):
    return r.get("group") or r["id"]


# --- metrics -----------------------------------------------------------------------------------------------------------

def _free(a: float) -> float:
    return max(a, 1 - a)


def _constant(scores) -> bool:
    return len({round(float(s), 9) for s in scores}) <= 1


def group_counts(rows: list) -> dict:
    return {lab: len({_group(r) for r in rows if r["label"] == lab}) for lab in ("yes", "no")}


def _np_auroc(s, y) -> float:
    from scipy.stats import rankdata
    r = rankdata(s)
    pos = int(y.sum())
    neg = len(y) - pos
    return float((r[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def bootstrap_ci(scores, preds, labels, groups, n: int = BOOTSTRAP, seed: int = BOOTSTRAP_SEED) -> dict:
    """95% cluster-bootstrap intervals (whole groups resampled) of the direction-free AUROC and BA."""
    import numpy as np
    s, p, y = np.asarray(scores, float), np.asarray(preds, float), np.asarray(labels, int)
    gid = {g: i for i, g in enumerate(sorted(set(groups)))}
    g = np.asarray([gid[x] for x in groups])
    order = np.argsort(g, kind="stable")
    bounds = np.searchsorted(g[order], np.arange(len(gid) + 1))
    members = [order[bounds[i]:bounds[i + 1]] for i in range(len(gid))]
    rng = np.random.default_rng(seed)
    au, ba = [], []
    for _ in range(n):
        pick = rng.integers(0, len(members), len(members))
        idx = np.concatenate([members[i] for i in pick])
        yy = y[idx]
        if yy.min() == yy.max():
            continue
        au.append(_free(_np_auroc(s[idx], yy)))
        pp = p[idx]
        ba.append(_free((pp[yy == 1].mean() + 1 - pp[yy == 0].mean()) / 2))
    if not au:
        return {}
    q = lambda v, x: round(float(np.quantile(v, x)), 3)     # noqa: E731
    return {"auroc_ci95": [q(au, 0.025), q(au, 0.975)], "ba_ci95": [q(ba, 0.025), q(ba, 0.975)]}


# --- models: fit_predict returns (scores, preds, status, meta) --------------------------------------------------------

class FitError(Exception):
    """A real failure to fit: an empty vocabulary on non-empty input, or non-convergence."""


def _catch_convergence(fn):
    """Run ``fn``; a ConvergenceWarning becomes a FitError (other warnings are ignored)."""
    from sklearn.exceptions import ConvergenceWarning
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = fn()
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        raise FitError("the solver did not converge")
    return out


def _lr(c: float):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=c, solver="liblinear", class_weight="balanced", max_iter=5000)


def _choose_c(make_x, y, groups, grid=None, k=None) -> float:
    """C by grouped inner CV on the training rows only (mean inner-fold AUROC, ties to the smaller C).
    ``make_x(train_idx, score_idx)`` returns matrices fitted on the inner training rows."""
    grid, k = grid or C_GRID, k or INNER_FOLDS
    folds = folds_of(groups, k)
    per = {c: [] for c in grid}
    for f in sorted(set(folds)):
        tr = [i for i, x in enumerate(folds) if x != f]
        te = [i for i, x in enumerate(folds) if x == f]
        ytr, yte = [y[i] for i in tr], [y[i] for i in te]
        if len(set(ytr)) < 2 or len(set(yte)) < 2:
            continue
        try:
            xtr, xte = make_x(tr, te)
        except ValueError:
            continue
        for c in grid:
            m = _catch_convergence(lambda: _lr(c).fit(xtr, ytr))
            per[c].append(auroc(list(m.decision_function(xte)), yte))
    means = {c: sum(v) / len(v) for c, v in per.items() if v}
    if not means:
        return 1.0
    return max(sorted(means), key=lambda c: (means[c], -c))


def _onehot(train_feats: list, score_feats: list, keys: tuple):
    from sklearn.feature_extraction import DictVectorizer
    vec = DictVectorizer(sparse=False)       # a few hundred one-hot columns; liblinear wants 32-bit sparse indices
    xtr = vec.fit_transform([{k: f[k] for k in keys} for f in train_feats])
    return xtr, vec.transform([{k: f[k] for k in keys} for f in score_feats])


def _logreg_on(make_full, make_inner, y, groups):
    c = _choose_c(make_inner, y, groups)
    xtr, xte = make_full()
    m = _catch_convergence(lambda: _lr(c).fit(xtr, y))
    return [float(v) for v in m.predict_proba(xte)[:, 1]], {"C": c}


def _fit_nuisance_logreg(train, score, keys):
    y, groups = _labels(train), [_group(r) for r in train]
    ft, fs = [nuisance_of(r) for r in train], [nuisance_of(r) for r in score]
    return _logreg_on(lambda: _onehot(ft, fs, keys),
                      lambda tr, te: _onehot([ft[i] for i in tr], [ft[i] for i in te], keys), y, groups)


def _fit_gbt(train, score):
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    keys = CATEGORICAL + FORMAT_FLAGS + ("length_bin",)
    ft, fs = [nuisance_of(r) for r in train], [nuisance_of(r) for r in score]
    codes = {}
    for k in keys:
        top = [v for v, _ in Counter(f[k] for f in ft).most_common(MAX_CATEGORIES)]
        codes[k] = {v: i for i, v in enumerate(sorted(top))}

    def mat(fs_):
        return np.array([[codes[k].get(f[k], np.nan) for k in keys] + [f["log_length"]] for f in fs_], dtype=float)
    from threadpoolctl import threadpool_limits
    m = HistGradientBoostingClassifier(categorical_features=list(range(len(keys))), class_weight="balanced", **GBT)
    with threadpool_limits(1):          # one thread per fit: the cells run in parallel processes instead
        m.fit(mat(ft), _labels(train))
    return [float(v) for v in m.predict_proba(mat(fs))[:, 1]], {}


def _text_vectoriser(kind: str):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion
    word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                           token_pattern=r"(?u)\b\w+\b", max_features=200000)
    if kind == "masked_text_logreg":
        return FeatureUnion([("w", word), ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2,
                                                                  sublinear_tf=True, max_features=200000))])
    return word


def _fit_text(kind: str, read, train, score):
    """A text nuisance model (context, masked document, neighbours). All-empty training input: no_input. Empty
    vocabulary on non-empty input: an error."""
    tt, st = [read(r) for r in train], [read(r) for r in score]
    if not any(t.strip() for t in tt):
        return None, {}
    y, groups = _labels(train), [_group(r) for r in train]

    def make(tr_texts, te_texts):
        v = _text_vectoriser(kind)
        return v.fit_transform(tr_texts), v.transform(te_texts)

    def full():
        try:
            return make(tt, st)
        except ValueError as e:
            raise FitError(f"empty vocabulary: {e}") from e
    return _logreg_on(full, lambda tr, te: make([tt[i] for i in tr], [tt[i] for i in te]), y, groups)


_READERS = {"context_logreg": lambda r: sc.context_text(r.get("state")), "masked_text_logreg": masked_text,
            "neighbours_logreg": neighbours_text}


def fit_predict(name: str, train: list, score: list) -> tuple[list | None, list | None, str, dict]:
    """One nuisance model fitted on ``train``, scoring ``score``: (scores, preds, status, meta)."""
    y = _labels(train)
    p = None
    try:
        if name == "source_id":
            s = sc._source_fit_predict([r["source"] for r in train], y, [r["source"] for r in score])
            seen = {r["source"] for r in train}
            meta = {"unseen_source_share": round(sum(r["source"] not in seen for r in score) / len(score), 3)}
            p = [1.0 if v > 0.5 else 0.0 for v in s]
        elif name == "length":
            texts = [judged_text(r) for r in score]
            s, meta = [float(len(t)) for t in texts], {}
            p = sc._length_fit_predict([judged_text(r) for r in train], y, texts)
        elif name == "format_logreg":
            s, meta = _fit_nuisance_logreg(train, score, FORMAT_FLAGS)
        elif name == "nuisance_logreg":
            s, meta = _fit_nuisance_logreg(train, score, CATEGORICAL + FORMAT_FLAGS + ("length_bin",))
        elif name == "nuisance_gbt":
            s, meta = _fit_gbt(train, score)
        elif name in _READERS:
            s, meta = _fit_text(name, _READERS[name], train, score)
        else:
            raise KeyError(name)
    except FitError as e:
        return None, None, "error", {"error": str(e)}
    except Exception as e:                       # noqa: BLE001 - every exception is a recorded failure
        return None, None, "error", {"error": f"{type(e).__name__}: {e}"}
    if s is None:
        return None, None, "no_input", meta
    if p is None:
        p = [1.0 if v >= 0.5 else 0.0 for v in s]
    status = "constant" if name != "length" and _constant(s) else "fit"
    return [float(v) for v in s], p, status, meta


def ngram_fit_predict(name: str, train: list, score: list) -> tuple[list, list, dict]:
    """A reported full-text baseline (the ruling 25 gate's models)."""
    texts = [judged_text(r) for r in score]
    if name == "keyword_regex":
        k = [1.0 if sc.KEYWORDS.search(t) else 0.0 for t in texts]
        return k, k, {}
    p, c = sc._text_fit_predict(name, [judged_text(r) for r in train], _labels(train), texts,
                                [_group(r) for r in train])
    return p, [1.0 if v >= 0.5 else 0.0 for v in p], {"C": c}


# --- cells -------------------------------------------------------------------------------------------------------------

def _applies(name: str, rows: list) -> bool:
    if name in SPAN_MODELS:
        return any((r.get("nuisance") or {}).get("span") for r in rows)
    return True


def _cell(scores, preds, status: str, meta: dict, rows: list) -> dict:
    labels = _labels(rows)
    v = {"status": status}
    if status in ("error", "no_input"):
        v.update(meta)
        v["pass"] = status == "no_input"
        return v
    if status == "constant":
        v.update({"auroc": 0.5, "ba": 0.5, "pass": True})
        return v
    v["auroc"] = round(_free(auroc(scores, labels)), 3)
    v["ba"] = round(sc.balanced_accuracy(preds, labels), 3)
    v.update(bootstrap_ci(scores, preds, labels, [_group(r) for r in rows]))
    v.update(meta)
    v["pass"] = bool(v["ba"] <= BA_MAX and v["auroc"] <= AUROC_MAX)
    return v


def cv_cell(name: str, rows: list, k: int = 5) -> dict:
    """Grouped k-fold CV on ``rows`` (whole groups held out of each fit): every row scored out of fold. Constant when
    every fold's fit was constant (each fold scores alike: nothing was learnt)."""
    labels = _labels(rows)
    folds = folds_of([_group(r) for r in rows], k)
    scores, preds, statuses, cs = [0.0] * len(rows), [0.0] * len(rows), [], []
    for f in sorted(set(folds)):
        tr = [i for i, x in enumerate(folds) if x != f]
        te = [i for i, x in enumerate(folds) if x == f]
        if not te or len({labels[i] for i in tr}) < 2:
            continue
        s, p, st, meta = fit_predict(name, [rows[i] for i in tr], [rows[i] for i in te])
        if st in ("error", "no_input"):
            return _cell(None, None, st, meta, rows)
        statuses.append(st)
        if "C" in meta:
            cs.append(meta["C"])
        for i, a, b in zip(te, s, p):
            scores[i], preds[i] = a, b
    status = "constant" if statuses and all(s == "constant" for s in statuses) else "fit"
    return _cell(scores, preds, status, {"C": cs} if cs else {}, rows)


def transfer_cell(name: str, train: list, score: list) -> dict:
    s, p, st, meta = fit_predict(name, train, score)
    return _cell(s, p, st, meta, score)


def ngram_cv(name: str, rows: list, k: int = 5) -> dict:
    labels = _labels(rows)
    folds = folds_of([_group(r) for r in rows], k)
    scores, preds = [0.0] * len(rows), [0.0] * len(rows)
    for f in sorted(set(folds)):
        tr = [i for i, x in enumerate(folds) if x != f]
        te = [i for i, x in enumerate(folds) if x == f]
        if not te or len({labels[i] for i in tr}) < 2:
            continue
        s, p, _ = ngram_fit_predict(name, [rows[i] for i in tr], [rows[i] for i in te])
        for i, a, b in zip(te, s, p):
            scores[i], preds[i] = a, b
    return {"ba_at_0_5": round(sc.balanced_accuracy(preds, labels), 3), "auroc": round(_free(auroc(scores, labels)), 3)}


def _job(args):
    kind, name, train, score = args
    if kind == "cv":
        return cv_cell(name, score)
    if kind == "fit":
        return transfer_cell(name, train, score)
    if kind == "ngram_cv":
        return ngram_cv(name, score)
    if kind == "ngram_fit":
        s, p, meta = ngram_fit_predict(name, train, score)
        y = _labels(score)
        return {"ba_at_0_5": round(sc.balanced_accuracy(p, y), 3), "auroc": round(_free(auroc(s, y)), 3), **meta}
    raise KeyError(kind)


def workers() -> int:
    try:
        return max(1, int(os.environ.get(WORKERS_ENV, "1")))
    except ValueError:
        return 1


def run_jobs(jobs: list) -> list:
    """Run (kind, name, train, score) jobs, in a process pool when GOLDRAILS_GATE_WORKERS > 1. A pool changes nothing a
    cell computes: same models, folds, seeds and bounds."""
    w = workers()
    if w <= 1 or len(jobs) < 2:
        return [_job(j) for j in jobs]
    from concurrent.futures import ProcessPoolExecutor
    order = sorted(range(len(jobs)), key=lambda i: -len(jobs[i][3]))
    with ProcessPoolExecutor(max_workers=w) as ex:
        futs = {i: ex.submit(_job, jobs[i]) for i in order}
        return [futs[i].result() for i in range(len(jobs))]


def run_settings() -> dict:
    return {"workers": workers(), "workers_env": WORKERS_ENV, "solver": "liblinear (L2), class_weight balanced",
            "c_grid": list(C_GRID), "inner_folds": INNER_FOLDS,
            "gbt": dict(GBT, class_weight="balanced", threads_per_fit=1),
            "bootstrap": {"resamples": BOOTSTRAP, "seed": BOOTSTRAP_SEED, "unit": "group"},
            "min_groups_per_class": MIN_GROUPS_PER_CLASS, "min_train_groups_per_class": MIN_TRAIN_GROUPS_PER_CLASS,
            "neighbour_chars": NEIGHBOUR_CHARS, "control_sample_rows": CONTROL_SAMPLE,
            "permutations": {"n": PERMUTATIONS, "seed": PERMUTATION_SEED},
            "cells": "each (view, subset, model) fitted on its own; a pool gives the same numbers as a serial run"}


# --- views and subsets --------------------------------------------------------------------------------------------------

VIEW_NOTES = {
    "heldout_groups_cv": "grouped five-fold CV on test + unpublished (whole groups held out of each fit)",
    "heldout_half_a_to_half_b": f"fit on one seeded group half of test + unpublished (seed {sc.HELDBACK_SEED}), score "
                                "the other",
    "heldout_half_b_to_half_a": "the same halves, the other direction",
    "dev_to_pool": "fit on dev, score test + unpublished",
    "pool_to_dev": "fit on test + unpublished, score dev",
}


def views_of(rows: list) -> dict:
    """{view: (kind, train, score)}. Every view holds out whole groups."""
    by = {k: [r for r in rows if r["proposed_split"] == k] for k in ("dev", "test", "private")}
    pool = by["test"] + by["private"]
    a, b = sc.seeded_halves(pool)
    return {"heldout_groups_cv": ("cv", None, pool), "heldout_half_a_to_half_b": ("fit", a, b),
            "heldout_half_b_to_half_a": ("fit", b, a), "dev_to_pool": ("fit", by["dev"], pool),
            "pool_to_dev": ("fit", pool, by["dev"])}


def _counts(rs):
    return {"n_yes": sum(r["label"] == "yes" for r in rs), "n_no": sum(r["label"] == "no" for r in rs)}


def _stratum(r):
    return r.get("stratum") or sc.stratum_of(r)


def subsets_of(rows: list) -> dict:
    """{name: rows} per stratum, source and facet value of one subtask. A value held by one class only (a hard-benign
    stratum, say) is compared against every row of the other class: ``key:value vs other class``."""
    def val(r, k):
        if k == "stratum":
            return _stratum(r)
        if k == "source":
            return r["source"]
        v = (r.get("facets") or {}).get(k)
        return None if v in (None, "") else str(v)
    keys = {"stratum", "source"} | {k for r in rows for k, v in (r.get("facets") or {}).items() if v not in (None, "")}
    out = {}
    for k in sorted(keys):
        for v in sorted({val(r, k) for r in rows} - {None}):
            sub = [r for r in rows if val(r, k) == v]
            labs = {r["label"] for r in sub}
            name = f"{k}:{v}"
            if len(labs) == 1:
                other = "no" if labs == {"yes"} else "yes"
                sub = sub + [r for r in rows if r["label"] == other]
                name += " vs other class"
            out[name] = sub
    return out


def _enough(kind, train, score) -> tuple[bool, str]:
    gs = group_counts(score)
    if min(gs.values()) < MIN_GROUPS_PER_CLASS:
        return False, f"scored rows hold {gs} independent groups, under {MIN_GROUPS_PER_CLASS} per class"
    if kind == "fit":
        gt = group_counts(train)
        if min(gt.values()) < MIN_TRAIN_GROUPS_PER_CLASS:
            return False, f"training rows hold {gt} independent groups, under {MIN_TRAIN_GROUPS_PER_CLASS} per class"
    return True, ""


def _jobs_for(rows: list, models) -> list:
    """[(subset, view, model, job)] for one subtask: whole-subtask views and every subset's views (no pool-to-dev for
    subsets: dev subsets are small)."""
    out = []
    for view, (kind, train, score) in views_of(rows).items():
        for m in models:
            if _applies(m, score):
                out.append(("whole", view, m, (kind, m, train, score)))
    for name, sub in subsets_of(rows).items():
        single_source = len({r["source"] for r in sub}) == 1
        for view, (kind, train, score) in views_of(sub).items():
            if view == "pool_to_dev":
                continue
            for m in models:
                if (m == "source_id" and single_source) or not _applies(m, score):
                    continue
                out.append((name, view, m, (kind, m, train, score)))
    return out


def gate_report(rows: list, use_sklearn: bool | None = None, controls: bool = True, ngrams: bool = True,
                models=CONFOUND_MODELS) -> dict:
    """The ruling 26 gate on prompt-attack rows (dicts with id, subtask, label, source, group, proposed_split, state,
    and optional stratum, facets and nuisance): every nuisance model of every subtask, stratum, source and facet in
    every view, the n-gram baselines (reported) and the controls. Passes when no cell fails, every subtask has a scored
    whole view, and the controls pass."""
    use = sklearn_available() if use_sklearn is None else use_sklearn
    models = tuple(models) if use else tuple(m for m in models if m not in SKLEARN_MODELS)
    subs = sorted({r["subtask"] for r in rows})
    keys, jobs, skipped = [], [], defaultdict(dict)
    for sub in subs:
        for name, view, m, job in _jobs_for([r for r in rows if r["subtask"] == sub], models):
            ok, why = _enough(job[0], job[2], job[3])
            if ok:
                keys.append((sub, name, view, m))
                jobs.append(job)
            else:
                skipped[sub][f"{name}/{view}/{m}"] = why
    done = dict(zip(keys, run_jobs(jobs)))
    out, table, failures = {}, [], []
    for sub in subs:
        rs = [r for r in rows if r["subtask"] == sub]
        per = {"counts": {s: _counts([r for r in rs if r["proposed_split"] == s]) for s in ("dev", "test", "private")},
               "independent_groups": {s: group_counts([r for r in rs if r["proposed_split"] == s])
                                      for s in ("dev", "test", "private")},
               "whole": defaultdict(dict), "subsets": defaultdict(lambda: defaultdict(dict)), "not_fitted_small": {}}
        for (s, name, view, m), cell in done.items():
            if s != sub:
                continue
            (per["whole"][view] if name == "whole" else per["subsets"][name][view])[m] = cell
            table.append({"subtask": sub, "subset": name, "view": view, "model": m, "status": cell["status"],
                          "ba": cell.get("ba"), "auroc": cell.get("auroc"), "pass": cell["pass"],
                          "auroc_ci95": cell.get("auroc_ci95"), "ba_ci95": cell.get("ba_ci95")})
            if not cell["pass"]:
                what = cell.get("error") if cell["status"] == "error" else f"BA {cell['ba']}, AUROC {cell['auroc']}"
                failures.append(f"{sub}/{name}/{view}/{m}: {cell['status']}: {what}")
        for key, why in skipped[sub].items():
            if key.startswith("whole/"):
                failures.append(f"{sub}/{key}: too few independent groups ({why})")
            else:
                per["not_fitted_small"][key] = why
        if not per["whole"]:
            failures.append(f"{sub}: no whole-subtask view could be scored")
        per["whole"] = {k: dict(v) for k, v in per["whole"].items()}
        per["subsets"] = {k: {v: dict(c) for v, c in d.items()} for k, d in per["subsets"].items()}
        out[sub] = per
    if not use:
        failures.append("the scikit-learn models were not computed (uv run --with scikit-learn ...)")
    rep = {"rule": f"every nuisance model in every view, per subtask, stratum, source and facet: BA <= {BA_MAX} and "
                   f"AUROC <= {AUROC_MAX} on held-out groups (direction-free); a constant fit on uninformative "
                   "features is recorded as constant and passes; an error (exception, empty vocabulary on non-empty "
                   "input, non-convergence) fails; a whole-subtask view needs "
                   f"{MIN_GROUPS_PER_CLASS} independent groups per class; the controls must pass",
           "bounds": {"ba_max": BA_MAX, "auroc_max": AUROC_MAX}, "models": list(models), "views": VIEW_NOTES,
           "run_settings": run_settings(), "subtasks": out, "table": table,
           "status_counts": dict(Counter(t["status"] for t in table)), "failures": failures}
    if ngrams and use:
        rep["ngram_baselines"] = ngram_report(rows)
    if controls and use:
        rep["controls"] = controls_report(rows, models)
    rep["cells_pass"] = not failures and bool(table)
    rep["pass"] = rep["cells_pass"] and (rep["controls"]["pass"] if "controls" in rep else not controls)
    return rep


def max_by(table: list, key: str = "subtask") -> dict:
    """Highest BA and AUROC of any scored cell per ``key``, and where each came from."""
    mx = defaultdict(dict)
    for t in table:
        if t.get("ba") is None:
            continue
        cell = mx[t[key]]
        for m in ("ba", "auroc"):
            if t[m] > cell.get(m, -1):
                cell[m], cell[f"{m}_at"] = t[m], f"{t['subset']}/{t['view']}/{t['model']}"
    return dict(sorted(mx.items()))


def summary(rep: dict) -> dict:
    whole = [t for t in rep["table"] if t["subset"] == "whole"]
    subs = [dict(t, subtask=f"{t['subtask']}/{t['subset']}") for t in rep["table"] if t["subset"] != "whole"]
    return {"pass": rep["pass"], "cells_pass": rep.get("cells_pass"), "cells": len(rep["table"]),
            "failing_cells": sum(not t["pass"] for t in rep["table"]), "status_counts": rep.get("status_counts"),
            "max_whole": max_by(whole), "max_subset": max_by(subs),
            "controls_pass": (rep.get("controls") or {}).get("pass"),
            "ngram_published_ba_at_0_5": (rep.get("ngram_baselines") or {}).get("published_ba_at_0_5")}


# --- reported n-gram baselines (ruling 26: not pass/fail) --------------------------------------------------------------

def ngram_report(rows: list) -> dict:
    """Per subtask: each full-text baseline's BA at 0.5 and AUROC, by grouped five-fold CV on test + unpublished (the
    rows systems are scored on; the published reference) and fitted on dev, scored on test + unpublished."""
    jobs, keys = [], []
    for sub in sorted({r["subtask"] for r in rows}):
        rs = [r for r in rows if r["subtask"] == sub]
        dev = [r for r in rs if r["proposed_split"] == "dev"]
        pool = [r for r in rs if r["proposed_split"] in ("test", "private")]
        if not min(_counts(pool).values()):
            continue
        for b in NGRAM_BASELINES:
            keys.append((sub, "heldout_groups_cv", b))
            jobs.append(("ngram_cv", b, None, pool))
            if min(_counts(dev).values()):
                keys.append((sub, "dev_to_pool", b))
                jobs.append(("ngram_fit", b, dev, pool))
    out = defaultdict(lambda: defaultdict(dict))
    for (sub, view, b), v in zip(keys, run_jobs(jobs)):
        out[sub][view][b] = v
    return {"what": "full-text baselines, reported and not pass/fail (owner ruling 26): BA at probability 0.5 and "
                    "AUROC. published_ba_at_0_5 is the grouped-CV BA on test + unpublished, the number published "
                    "beside every system",
            "views": {"heldout_groups_cv": VIEW_NOTES["heldout_groups_cv"], "dev_to_pool": VIEW_NOTES["dev_to_pool"]},
            "results": {s: {v: dict(b) for v, b in d.items()} for s, d in out.items()},
            "published_ba_at_0_5": {s: {b: c["ba_at_0_5"] for b, c in d["heldout_groups_cv"].items()}
                                    for s, d in out.items() if "heldout_groups_cv" in d}}


# --- controls ------------------------------------------------------------------------------------------------------------

def _salt(*parts) -> float:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16) / 16 ** 12


def plant(rows: list, kind: str, share: float = 0.8) -> list:
    """Copies of ``rows`` with a planted nuisance signal on ``share`` of the attack rows: a platform value
    (``platform``), 1,500 characters of filler at the end (``length``), or a token at the start of the document,
    outside the masked span (``masked``)."""
    out = []
    for r in rows:
        hit = r["label"] == "yes" and _salt("plant", kind, r["id"]) < share
        r2 = dict(r, nuisance=dict(r.get("nuisance") or {}), state=dict(r.get("state") or {}))
        if hit and kind == "platform":
            r2["nuisance"]["platform"] = "planted"
        elif hit and kind == "length":
            r2["state"]["text"] = judged_text(r) + "\n" + "lorem ipsum " * 125
        elif hit and kind == "masked":
            r2["state"]["text"] = "zqxj " + judged_text(r)
            sp = r2["nuisance"].get("span")
            if sp:
                r2["nuisance"]["span"] = [sp[0] + 5, sp[1] + 5]
        out.append(r2)
    return out


PLANT_SHOULD_SEE = {"platform": ("nuisance_logreg", "nuisance_gbt"),
                    "length": ("length", "nuisance_logreg", "nuisance_gbt"),
                    "masked": ("masked_text_logreg",)}


def _sample(rs: list, n: int, tag: str) -> list:
    """A salted sample of whole groups, about ``n`` rows."""
    count = Counter(_group(r) for r in rs)
    keep, size = set(), 0
    for g in sorted(count, key=lambda g: _salt(tag, g)):
        if size >= n:
            break
        keep.add(g)
        size += count[g]
    return [r for r in rs if _group(r) in keep]


def permute(rows: list, seed: int) -> list:
    """Labels permuted across whole groups: each group takes another group's label vector (cycled to its size), so
    groups keep their size and the label no longer follows anything about the rows."""
    groups = sorted({_group(r) for r in rows})
    order = groups[:]
    random.Random(seed).shuffle(order)
    remap = dict(zip(groups, order))
    by_g = defaultdict(list)
    for r in rows:
        by_g[_group(r)].append(r["label"])
    used, out = Counter(), []
    for r in rows:
        src = by_g[remap[_group(r)]]
        out.append(dict(r, label=src[used[_group(r)] % len(src)]))
        used[_group(r)] += 1
    return out


def controls_report(rows: list, models=CONFOUND_MODELS) -> dict:
    """Per subtask, on a salted sample of whole groups of test + unpublished (grouped five-fold CV): planted signals
    must be caught by the models that can see them; permuted labels must not break a bound for any model."""
    jobs, keys = [], []
    for sub in sorted({r["subtask"] for r in rows}):
        pool = [r for r in rows if r["subtask"] == sub and r["proposed_split"] in ("test", "private")]
        if not pool or not min(_counts(pool).values()):
            continue
        pool = _sample(pool, CONTROL_SAMPLE, f"ctl-{sub}")
        for kind, see in PLANT_SHOULD_SEE.items():
            if kind == "masked" and not _applies("masked_text_logreg", pool):
                continue
            planted = plant(pool, kind)
            for m in see:
                keys.append((sub, f"planted:{kind}", m))
                jobs.append(("cv", m, None, planted))
        for k in range(PERMUTATIONS):
            perm = permute(pool, PERMUTATION_SEED + k)
            if not min(_counts(perm).values()):
                continue
            for m in models:
                if _applies(m, perm):
                    keys.append((sub, f"permuted:{k}", m))
                    jobs.append(("cv", m, None, perm))
    out = defaultdict(lambda: defaultdict(dict))
    for (sub, ctl, m), v in zip(keys, run_jobs(jobs)):
        out[sub][ctl][m] = {x: v.get(x) for x in ("status", "ba", "auroc", "auroc_ci95", "error") if x in v}
    problems = []
    for sub, d in out.items():
        for ctl, cells in d.items():
            for m, c in cells.items():
                broke = c["status"] == "fit" and (c["auroc"] > AUROC_MAX or c["ba"] > BA_MAX)
                if ctl.startswith("planted:") and not broke:
                    problems.append(f"{sub}/{ctl}/{m}: did not detect the planted signal ({c})")
                if ctl.startswith("permuted:") and (broke or c["status"] == "error"):
                    problems.append(f"{sub}/{ctl}/{m}: permuted labels broke a bound or failed ({c})")
    return {"what": "planted-signal control (a platform value, a length shift or a token outside the masked span on "
                    "80% of attack rows; every model that can see the signal must break a bound) and label-permutation "
                    f"control ({PERMUTATIONS} permutations across whole groups; no model may break a bound), grouped "
                    "five-fold CV on a salted sample of whole groups of test + unpublished",
            "sample_rows": CONTROL_SAMPLE,
            "results": {s: {c: dict(v) for c, v in d.items()} for s, d in out.items()},
            "problems": problems, "pass": not problems}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--file", required=True, help="gate rows as JSON lines (id, subtask, label, source, group, "
                                                  "proposed_split, state; optional stratum, facets, nuisance)")
    ap.add_argument("--no-controls", action="store_true")
    a = ap.parse_args(argv)
    rows = [json.loads(l) for l in open(a.file, encoding="utf-8") if l.strip()]
    rep = gate_report(rows, controls=not a.no_controls)
    print(json.dumps(summary(rep), indent=2))
    print("\n".join(rep["failures"][:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The prompt-attack shortcut gate as strengthened under owner ruling 25: word 1-3 and 1-4-gram models, a character
model that crosses word boundaries, a model on the trust context, and the per-stratum and per-source checks."""
from __future__ import annotations

import random
import zlib

import pytest

from goldrails_dataset import edition2 as e2
from goldrails_dataset.sources import e2_prompt_attacks_shortcuts as sc


def _noise(train, y, test, groups=None):
    return [zlib.crc32(t.encode()) % 1000 / 1000 for t in test]


def _rows(n, sub="injection", source="src", split_cycle=("test", "test", "test", "private", "dev"), text=None,
          context=None, stratum=None):
    out = []
    for i in range(n):
        lab = "yes" if i % 2 else "no"
        r = {"id": f"{sub}-{source}-{i}", "subtask": sub, "label": lab, "source": source, "group": f"{source}-g{i}",
             "proposed_split": split_cycle[i % len(split_cycle)],
             "state": {"text": text(i, lab) if text else f"row {i} {'x' * (i % 13)}",
                       "context": context(i, lab) if context else []}}
        if stratum:
            r["stratum"] = stratum
        out.append(r)
    return out


def test_the_gate_has_the_ruling_25_baselines_and_edition2_agrees():
    for b in ("word13_logreg", "word14_logreg", "char_cross_logreg", "context_logreg"):
        assert b in sc.BASELINES and b in sc.TEXT_MODELS and b in sc.TEXT_HOOKS
    assert tuple(e2.SHORTCUT_BASELINES) == sc.BASELINES
    assert sc.BA_TARGET == 0.70 and sc.AUROC_TARGET == 0.75          # no bound loosened
    assert set(sc.CONSTANT_CHECKED) == (set(sc.TEXT_MODELS) - {"context_logreg"}) | {"source_id"}


def test_a_word_4gram_signal_alone_fails_the_gate(monkeypatch):
    """Every other model sees noise; word 1-4-grams see the label. The gate fails on that model's cells only."""
    for hook in sc.TEXT_HOOKS.values():
        monkeypatch.setattr(sc, hook, _noise)
    monkeypatch.setattr(sc, "_word14_fit_predict",
                        lambda train, y, test, groups=None: [1.0 if "ATTACK" in t else 0.0 for t in test])
    rows = [r for sub in sc.SUBTASKS for r in _rows(
        120, sub, text=lambda i, lab: f"row {i} {'ATTACK' if lab == 'yes' else 'calmly'} " + "x" * (i % 11))]
    rep = sc.gate_report(rows, use_sklearn=True, which=sc.IN_SAMPLE_VIEWS)
    failing = {f.split(":")[0] for f in rep["failures"]}
    assert rep["pass"] is False
    assert failing and all(f.endswith("/word14_logreg") for f in failing), failing


def test_extra_subtasks_join_the_gate():
    rows = _rows(60, "injection") + _rows(60, "jailbreak") + _rows(60, "leakage") + _rows(60, "indirect")
    assert sc.subtasks_of(rows) == ("injection", "jailbreak", "leakage", "indirect")
    rep = sc.gate_report(rows, use_sklearn=False, which=("in_sample_public_test",))
    assert "indirect" in rep["views"]["in_sample_public_test"]


def test_context_text_reads_turns_and_tool_call():
    st = {"text": "t", "context": [{"role": "system", "text": "sys"}, {"role": "user", "text": "q"}],
          "tool_call": {"name": "send"}}
    assert sc.context_text(st) == 'sys\nq\n{"name": "send"}'
    assert sc.gate_text(st) == "t"
    assert sc.context_text({"text": "t"}) == ""


def test_strata_fail_when_the_real_rows_separate_although_the_authored_rows_do_not(monkeypatch):
    """The ruling 23 failure mode: authored rows at chance, external rows separable. The strata report fails on the
    external stratum and its source, not on the authored one."""
    def marker(train, y, test, groups=None):
        return [(0.99 if "EXT_ATTACK" in t else 0.01) if t.startswith("external") else _noise(None, None, [t])[0]
                for t in test]
    for hook in sc.TEXT_HOOKS.values():
        monkeypatch.setattr(sc, hook, marker)
    ext = _rows(200, source="real_src", text=lambda i, lab: f"external {i} {'EXT_ATTACK' if lab == 'yes' else 'ok'}")
    auth = _rows(200, source="e2_attack_controls", text=lambda i, lab: f"authored {i}")
    rep = sc.strata_report(ext + auth, use_sklearn=True)
    inj = rep["subtasks"]["injection"]
    assert rep["pass"] is False
    assert {"stratum:external", "stratum:authored", "source:real_src", "source:e2_attack_controls"} <= set(inj["subsets"])
    assert any(f.startswith("injection/stratum:external/") for f in rep["failures"])
    assert any(f.startswith("injection/source:real_src/") for f in rep["failures"])
    assert not any(f.startswith("injection/stratum:authored/") and "logreg" in f for f in rep["failures"])
    # a single-source subset has no source_id cell (it would be constant by construction)
    assert "source_id" not in inj["subsets"]["source:real_src"]["views"]["in_sample_pool"]


def test_strata_checks_authored_share_single_class_sources_and_external_size(monkeypatch):
    for hook in sc.TEXT_HOOKS.values():
        monkeypatch.setattr(sc, hook, _noise)
    ext = _rows(100, source="real_src")
    auth = _rows(300, source="e2_attack_controls")
    one = [dict(r, label="yes") for r in _rows(10, source="only_attacks")]
    rep = sc.strata_report(ext + auth + one, use_sklearn=True)
    checks = rep["subtasks"]["injection"]["checks"]
    assert checks["authored_share"]["pass"] is False                      # 300 of 410 rows are authored
    assert checks["single_class_sources"]["sources"] == {"only_attacks": {"yes": 10, "no": 0}}
    assert "source:only_attacks" in rep["subtasks"]["injection"]["not_fitted_small"]
    small = sc.strata_report(_rows(30, source="real_src") + _rows(20, source="e2_attack_controls"), use_sklearn=True)
    assert small["subtasks"]["injection"]["checks"]["external_stratum_size"]["pass"] is False
    assert small["pass"] is False


def test_facets_add_subsets(monkeypatch):
    for hook in sc.TEXT_HOOKS.values():
        monkeypatch.setattr(sc, hook, _noise)
    rows = _rows(200, source="real_src")
    for i, r in enumerate(rows):
        r["facets"] = {"carrier": "email" if i % 4 < 2 else "web"}
    rep = sc.strata_report(rows, use_sklearn=True)
    assert {"carrier:email", "carrier:web"} <= set(rep["subtasks"]["injection"]["subsets"])


def test_stratum_of_uses_the_authored_sources_and_a_row_override():
    assert sc.stratum_of({"source": "e2_attack_controls"}) == "authored"
    assert sc.stratum_of({"source": "e2_authored_frames"}) == "authored"
    assert sc.stratum_of({"source": "lakera_mosscap"}) == "external"
    assert sc.stratum_of({"source": "lakera_mosscap", "stratum": "authored"}) == "authored"


def test_edition2_gate_includes_the_strata(monkeypatch):
    ok = {"pass": True, "failures": [], "table": []}
    monkeypatch.setattr(e2, "shortcut_audit", lambda parts, use_sklearn=None: ok)
    monkeypatch.setattr(e2, "shortcut_heldback", lambda parts, use_sklearn=None: ok)
    monkeypatch.setattr(e2, "shortcut_strata", lambda parts, use_sklearn=None: {"pass": False, "failures": ["z"],
                                                                                   "table": []})
    rep = e2.shortcut_gate({"dev": [], "test": [], "private": []})
    assert rep["pass"] is False and rep["failures"] == ["strata/z"]
    assert e2.gate_summary(rep)["strata_pass"] is False


# --- with scikit-learn: the real models -------------------------------------------------------------------------------

def _trigram_rows(n=400, seed=7):
    """Unigrams and bigrams carry no label: attacks hold "alpha beta gamma" and "delta beta epsilon", benign rows
    "alpha beta epsilon" and "delta beta gamma". Shared filler words sit between and around the phrases."""
    rng = random.Random(seed)
    filler = "one two three four five six seven eight nine ten eleven twelve".split()
    rows = []
    for i in range(n):
        lab = "yes" if i % 2 else "no"
        a, b = (("alpha beta gamma", "delta beta epsilon") if lab == "yes"
                else ("alpha beta epsilon", "delta beta gamma"))
        if rng.random() < 0.5:
            a, b = b, a
        f = lambda k: " ".join(rng.choice(filler) for _ in range(k))   # noqa: E731
        rows.append({"id": f"t{i}", "subtask": "injection", "label": lab, "source": "s", "group": f"g{i}",
                     "proposed_split": "test", "state": {"text": f"{f(3)} {a} {f(4)} {b} {f(3)}"}})
    return rows


def test_word_trigrams_catch_what_bigrams_miss():
    pytest.importorskip("sklearn")
    rep = sc.subtask_report(_trigram_rows(), use_sklearn=True)
    assert rep["bow_logreg"]["meets_target"], rep["bow_logreg"]
    assert rep["char_ngram_logreg"]["meets_target"], rep["char_ngram_logreg"]
    assert not rep["word13_logreg"]["meets_target"] and rep["word13_logreg"]["auroc"] > 0.9
    assert not rep["word14_logreg"]["meets_target"]
    # char 3-6-grams cannot join "alpha" to "gamma" across "beta" (9 characters): this signal is word-level only


def test_context_model_catches_a_label_in_the_trust_context():
    pytest.importorskip("sklearn")
    rows = _rows(300, text=lambda i, lab: f"same judged text {i % 7}",
                 context=lambda i, lab: [{"role": "user", "text": f"query {i % 5} "
                                          + ("summarise it" if lab == "yes" else "summarise it and also file it")}])
    rep = sc.subtask_report(rows, use_sklearn=True)
    assert not rep["context_logreg"]["meets_target"] and rep["context_logreg"]["auroc"] > 0.9
    flat = sc.subtask_report(_rows(200), use_sklearn=True)      # rows without context: constant, not a failure
    assert flat["context_logreg"]["meets_target"] and not flat["context_logreg"].get("constant_prediction")

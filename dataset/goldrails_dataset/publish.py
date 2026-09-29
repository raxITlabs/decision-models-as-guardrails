"""Stage a release for Hugging Face: card, source registry, notices, known issues and data. No upload.

    uv run python -m goldrails_dataset.publish --version v1.1-ai

Reads the immutable release (``dataset/release/<version>/manifest.json`` and its ``hf/`` files), the redistribution
policy, the attribution facts fetched verbatim from each publisher (``dataset/release/source-attribution-fetched.json``)
and any metadata corrections, and writes ``dataset/publish/<version>/``:

- ``README.md``: the dataset card, generated from the staged files; every config path in its YAML is checked,
- ``SOURCES.md`` and ``sources.json``: publisher, original and mirror URL, pinned revision, licence, requested
  citation, redistribution mode and our adaptation, per source,
- ``NOTICE.md``: copyright and licence notices that the sources require to be kept, verbatim,
- ``KNOWN_ISSUES.md``: the release's known issues and metadata corrections,
- ``RECONSTRUCT.md``: how to rebuild ids-only text locally,
- ``data/<config>/<split>.jsonl``: the release rows, minus any source withheld below (gitignored).

Rows are unchanged except ``acquisition.rebuild``, which names the concrete version and code commit. The staged
folder is then loaded with the ``datasets`` library, config by config, as Hugging Face would load it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from .sources import SOURCES

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
INTENDED_USE = ("[gold]rails is a non-commercial research benchmark by raxIT Labs. It compares guardrail systems and "
                "publishes the results for research, with credit to every upstream source. It is not a commercial product "
                "or deployment. Publishing it changes no source's licence: each row stays under its source's own terms, "
                "listed in SOURCES.md.")
CONFIG_ORDER = ["content", "prompt_attacks", "denied_topics", "word_filters", "sensitive_information", "grounding",
                "bias", "candidates"]

# Sources whose rows stay out of the upload until a distribution basis is documented. Text-stripping is not enough:
# the rows still carry the source's annotations and derived labels.
WITHHOLD = {
    "ai4privacy": ("The AI4Privacy licence separates research use from redistribution: making the dataset or derived "
                   "annotations available needs written permission, even for a non-commercial project, and its research "
                   "terms mention a licensing process. Ids-only rows still carry its span annotations and derived labels, "
                   "so they are withheld while we clarify both with AI4Privacy (request drafted in "
                   "docs/requests/ai4privacy-permission-request.md). The benchmark results that used these rows are "
                   "unchanged and stay qualified."),
}

# Release source key -> the fetched attribution record(s) it relies on, and how the rows were made.
UPSTREAM = {
    "aegis2": ["aegis2"], "ai4privacy": ["ai4privacy"], "ailuminate_demo": ["ailuminate_demo"], "bbq": ["bbq"],
    "bias_pairs_reviewed": ["holistic_bias"], "civil_comments_identity": ["civil_comments"],
    "civil_comments_profanity": ["civil_comments", "dsojevic_profanity_list"], "civil_comments_obscene": ["civil_comments"],
    "deepset_injections": ["deepset_injections"],
    "discrim_eval": ["discrim_eval"], "gandalf": ["gandalf"], "jailbreakbench": ["jailbreakbench_behaviors"],
    "jbb_artifacts": ["jbb_artifacts", "jailbreakbench_behaviors"], "openai_moderation": ["openai_moderation"],
    "orbench": ["orbench"], "ragtruth": ["ragtruth"], "nemotron_pii": ["nemotron_pii"],
}
AUTHORED = {"f2_controls", "f3_controls", "f3_test_candidates", "f4_words", "f5_controls"}
AUTHORED_NOTE = ("Authored for [gold]rails by raxIT Labs with an AI assistant (Claude), CC-BY-4.0. Labels are the "
                 "author's intended labels (label_basis llm or deterministic), not independent annotation.")


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def registry(sources: set, modes: dict, fetched: dict, withhold: dict = WITHHOLD) -> list:
    out = []
    for key in sorted(sources):
        mod = SOURCES.get(key)
        doc = ((mod.__doc__ or "").strip().split("\n\n")[0].replace("\n", " ")) if mod else ""
        entry = {"source": key, "mode": modes.get(key), "withheld": key in withhold, "withheld_reason": withhold.get(key),
                 "adaptation": doc, "loader": f"dataset/goldrails_dataset/sources/{key}.py",
                 "pinned": {k.lower(): getattr(mod, k) for k in ("REVISION", "COMMIT", "URL", "REPO", "RAW", "LEXICON_URL")
                            if mod is not None and isinstance(getattr(mod, k, None), str)}}
        if key in AUTHORED:
            entry["upstream"] = [{"publisher": "raxIT Labs (authored)", "licence_id": "CC-BY-4.0", "note": AUTHORED_NOTE}]
        else:
            entry["upstream"] = [fetched[u] for u in UPSTREAM.get(key, [])]
            if not entry["upstream"]:
                raise SystemExit(f"no attribution record for source {key}; add it to UPSTREAM")
        out.append(entry)
    return out


def sources_md(reg: list) -> str:
    lines = ["# Sources", "", "Every source in this release, with the facts copied from its publisher at the pinned "
             "revision. Row-level `provenance.source` and `provenance.source_id` link each row to its entry here.", ""]
    for e in reg:
        lines += [f"## {e['source']}", "", f"- Redistribution here: **{'withheld' if e['withheld'] else e['mode']}**"]
        if e["withheld"]:
            lines.append(f"- Why withheld: {e['withheld_reason']}")
        for u in e["upstream"]:
            lines.append(f"- Publisher: {u.get('publisher')}")
            for k, label in (("original_url", "Original"), ("mirror_url", "Mirror used"), ("revision", "Pinned revision"),
                             ("licence_id", "Licence"), ("licence_url", "Licence text"), ("restrictions", "Restrictions"),
                             ("note", "Note")):
                if u.get(k):
                    lines.append(f"  - {label}: {u[k]}")
            if u.get("requested_citation"):
                lines += ["  - Requested citation:", "", "```", u["requested_citation"].strip(), "```", ""]
        lines += [f"- Our adaptation: {e['adaptation']}", f"- Loader: `{e['loader']}`", ""]
    return "\n".join(lines) + "\n"


def notice_md(reg: list) -> str:
    lines = ["# Notices", "", "Copyright and licence notices the sources require to be kept with copies or adaptations, "
             "verbatim from the publishers. Sources marked CC-BY or CC-BY-SA are credited in SOURCES.md, which also "
             "records what we changed.", ""]
    seen = set()
    for e in reg:
        for u in e["upstream"]:
            if u.get("notice_required") and u.get("copyright_notice") and u.get("key") not in seen and not e["withheld"]:
                seen.add(u.get("key"))
                lines += [f"## {u.get('key')} ({u.get('licence_id')})", "", "```", u["copyright_notice"].strip(), "```", ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1.1-ai")
    ap.add_argument("--no-load-check", action="store_true", help="skip the datasets-library load check")
    ap.add_argument("--public-repo", default="https://github.com/raxITlabs/goldrails",
                    help="public code repository the card and reconstruction steps point to")
    ap.add_argument("--public-ref", default="v0.0.1", help="public version: the tag in the code repository and on the dataset")
    ap.add_argument("--previous", type=Path,
                    help="publication record of the upload this package revises (same public version); adds CHANGELOG.md")
    ap.add_argument("--card-update", action="append", default=[], metavar="DATE|REVISION|TEXT",
                    help="a card-only change to an uploaded revision: the date, the Hub revision whose data it keeps, and "
                         "what changed; listed first in CHANGELOG.md")
    ap.add_argument("--code-ref", help="code revision the card and RECONSTRUCT.md name (default: --public-ref); "
                                       "set it to the code export's commit before uploading a revision")
    ap.add_argument("--full", action="store_true",
                    help="complete text for every source, under the rights record dataset/release/rights-confirmation-*.json")
    a = ap.parse_args(argv)
    code_ref = a.code_ref or a.public_ref
    previous = json.loads(a.previous.read_text(encoding="utf-8")) if a.previous else None
    withhold = {} if a.full else WITHHOLD
    rel = ROOT / "release" / a.version
    man = json.loads((rel / "manifest.json").read_text(encoding="utf-8"))
    fetched = {x["key"]: x for x in json.loads((ROOT / "release" / "source-attribution-fetched.json").read_text())}
    corr = sorted(rel.glob("metadata-correction-*.json")) + sorted(rel.glob("known-issues.json"))
    out = ROOT / "publish" / (f"{a.version}-full" if a.full else a.version)
    per_version = rel / "rights.json"      # a release's own rights record wins over the older shared ones
    review_path = rel / "owner-review-confirmation.json"   # a recorded human review of this release's labels
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else None
    if review and review.get("release_manifest_sha256") != _sha(rel / "manifest.json"):
        raise SystemExit(f"{review_path} names a different release manifest")
    rights = ([json.loads(per_version.read_text(encoding="utf-8"))] if per_version.exists() else
              [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "release").glob("rights-confirmation-*.json"))])
    if a.full and not rights:
        raise SystemExit("--full needs a rights record in dataset/release/rights-confirmation-*.json")
    if out.exists():
        shutil.rmtree(out)
    commit = _git("rev-parse", "HEAD")
    rebuild = (f"git clone {a.public_repo} && git -C goldrails checkout {a.public_ref} && uv sync && "
               "uv run python -m goldrails_dataset.rehydrate --data <this dataset folder> --out <folder> (see RECONSTRUCT.md)")

    staged, held = defaultdict(list), Counter()
    if a.full:   # every row straight from the release build, with its text
        from .records import canonical, read_jsonl
        from .release import SUITES
        for p in sorted((rel / "build").glob("*.jsonl")):
            for rec in read_jsonl(p):
                d = rec.to_dict()
                d["canonical_row_hash"] = hashlib.sha256(canonical(rec).encode()).hexdigest()
                d["redistribution"] = "text"
                config = "candidates" if rec.review_status == "candidate" else SUITES[rec.feature]
                staged[(config, rec.split)].append(d)
        for rows in staged.values():
            rows.sort(key=lambda x: x["id"])
    for f in ([] if a.full else man["hf_files"]):
        src = rel / f["path"]
        for line in src.open(encoding="utf-8"):
            r = json.loads(line)
            s = r["provenance"]["source"]
            if s in WITHHOLD:
                held[(s, f["config"], f["split"])] += 1
                continue
            if r.get("acquisition"):
                r["acquisition"]["rebuild"] = rebuild
            staged[(f["config"], f["split"])].append(r)
    files = []
    for (config, split), rows in sorted(staged.items(), key=lambda kv: (CONFIG_ORDER.index(kv[0][0]), kv[0][1])):
        p = out / "data" / config / f"{split}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        files.append({"config": config, "split": split, "path": str(p.relative_to(out)), "n": len(rows), "sha256": _sha(p)})

    rows_all = [r for rs in staged.values() for r in rs]
    sources = {r["provenance"]["source"] for r in rows_all} | {s for s, _, _ in held}
    modes = {k: "text" for k in man["redistribution"]} if a.full else man["redistribution"]
    reg = registry(sources, modes, fetched, withhold)
    (out / "sources.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "SOURCES.md").write_text(sources_md(reg), encoding="utf-8")
    (out / "NOTICE.md").write_text(notice_md(reg), encoding="utf-8")
    known = [json.loads(p.read_text()) for p in corr]
    (out / "KNOWN_ISSUES.md").write_text(known_md(a.version, known), encoding="utf-8")
    (out / "RECONSTRUCT.md").write_text(reconstruct_md(a.version, a.public_repo, code_ref, held, rows_all), encoding="utf-8")
    if previous:
        (out / "CHANGELOG.md").write_text(changelog_md(a.public_ref, a.version, man, rows_all, previous, review, code_ref,
                                                       a.card_update),
                                         encoding="utf-8")
    if review:
        (out / "LABEL_REVIEW.json").write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.full:
        (out / "RIGHTS.md").write_text(rights_md(rights), encoding="utf-8")
        sidecars(out, rows_all)
    (out / "README.md").write_text(card(a.version, man, files, rows_all, held, reg, known, a.public_repo, a.public_ref,
                                        rights if a.full else None, review=review, previous=previous, code_ref=code_ref),
                                   encoding="utf-8")

    problems = validate(out, files, rows_all, reg, withhold)
    checks = verify_full(out, man, files, rows_all) if a.full else {}
    problems += checks.pop("problems", [])
    if not a.no_load_check:
        problems += load_check(out, files)
    report = {"version": a.version, "full_text": a.full, "code_commit": commit, "files": files, "rows": len(rows_all),
              "public_version": a.public_ref, "revises": previous and previous.get("hub_commit"), "code_ref": code_ref,
              "verification": checks,
              "pending": (pending(rights) if a.full else []) + (
                  [f"code_ref '{code_ref}' is not a commit: set --code-ref to the code export's commit before uploading"]
                  if previous and not re.fullmatch(r"[0-9a-f]{40}", code_ref) else []),
              "withheld": {f"{s}/{c}/{sp}": n for (s, c, sp), n in sorted(held.items())}, "problems": problems}
    (out / "staging-report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    for x in report["pending"]:
        print(f"  PENDING: {x}")
    print(f"{a.version}{' (full text)' if a.full else ''}: staged {len(rows_all)} rows in {len(files)} files; withheld {sum(held.values())}; "
          f"{'no problems' if not problems else str(len(problems)) + ' problems: ' + '; '.join(problems[:5])}")
    return 1 if problems else 0


def pending(rights: list) -> list:
    out = []
    for rec in rights:
        for s, v in rec.get("per_source", {}).items():
            if "permission_records" in v and not v["permission_records"]:
                out.append(f"{s}: {v.get('to_attach') or 'permission record'} "
                           f"(dataset/release/rights-confirmation-{rec['date']}.json)")
    return out


def rights_md(rights: list) -> str:
    lines = ["# Rights and permissions", "",
             "This package carries complete text for every source. The basis for each source that earlier shipped "
             "without text is recorded below, from the project's rights record.", ""]
    for rec in rights:
        lines += [f"## Owner confirmation, {rec['date']}", "", f"Confirmed by {rec['confirmed_by']}.", ""]
        lines += [f"> {x}" for x in rec.get("statements", [])]
        lines += ["", f"_{rec['recorded_by']}_", "", "| Source | Licence | Basis | Permission records |", "|---|---|---|---|"]
        for s, v in rec["per_source"].items():
            recs = v.get("permission_records")
            shown = "not needed" if recs is None else (", ".join(map(str, recs)) or f"to attach: {v.get('to_attach')}")
            lines.append(f"| {s} | {v['licence']} | {v['basis']} | {shown} |")
        conds = [(s, v.get("licence_condition") or v.get("condition")) for s, v in rec["per_source"].items()
                 if v.get("licence_condition") or v.get("condition")]
        if conds:
            lines += ["", "Conditions:", ""] + [f"- **{s}.** {c}" for s, c in conds]
        lines += ["", rec.get("unchanged", ""), ""]
    return "\n".join(lines) + "\n"


def sidecars(out: Path, rows: list) -> None:
    """Known-issue annotations as separate files. They never change a row's label or split."""
    import re
    ann = out / "annotations"
    ann.mkdir(parents=True, exist_ok=True)
    if not any(r["provenance"]["source"] == "ai4privacy" for r in rows):   # v1.2 on: the Nemotron audit record
        audit = REPO / "dataset" / "frozen" / "reviews" / "nemotron-pii-audit-2026-09-28"
        shutil.copyfile(audit / "AUDIT.md", ann / "nemotron-pii-audit.md")
        shutil.copyfile(audit / "mechanical.json", ann / "nemotron-pii-audit-mechanical.json")
        with (ann / "pii-negative-reviews.jsonl").open("w", encoding="utf-8") as fh:
            for p in sorted((REPO / "dataset" / "frozen" / "reviews" / "nemotron-negatives").glob("review-*.jsonl")):
                for line in p.open(encoding="utf-8"):
                    fh.write(line if line.endswith("\n") else line + "\n")
        (ann / "README.md").write_text(
            "# PII audit annotations\n\nThese sit beside the data. No label or split in `data/` is changed.\n\n"
            "- `nemotron-pii-audit.md` and `nemotron-pii-audit-mechanical.json`: the audit of NVIDIA Nemotron-PII that "
            "preceded its use (AI reviewers, blind to the source labels; not human annotation).\n"
            "- `pii-negative-reviews.jsonl`: the blind review of every negative the release selected. Rows reviewed as "
            "present or unclear were replaced and are not in `data/`.\n", encoding="utf-8")
        return
    corr = REPO / "dataset" / "frozen" / "corrections" / "pii-negatives-2026-09-24.jsonl"
    if corr.exists():
        shutil.copyfile(corr, ann / "pii-negatives-audit-2026-09-24.jsonl")
    fam = defaultdict(list)
    for r in rows:
        if r["provenance"]["source"] == "ai4privacy":
            m = re.match(r"(\d+)[A-Z]*$", str(r["provenance"]["source_id"]))
            if m:
                fam[m.group(1)].append({"id": r["id"], "source_id": r["provenance"]["source_id"], "split": r["split"]})
    with (ann / "pii-parent-families.jsonl").open("w", encoding="utf-8") as fh:
        for parent, members in sorted(fam.items()):
            if len({m["split"] for m in members}) > 1:
                fh.write(json.dumps({"parent": parent, "rows": members}, ensure_ascii=False) + "\n")
    (ann / "README.md").write_text(
        "# Known-issue annotations\n\nThese sit beside the data. No label or split in `data/` is changed.\n\n"
        "- `pii-negatives-audit-2026-09-24.jsonl`: 20 PII negatives that two blind AI reviews both found to contain a "
        "supported entity (one review of all 450 negatives, a second of 63). Original and audited labels side by side.\n"
        "- `pii-parent-families.jsonl`: AI4Privacy documents with fragments in both tuning and test, grouped by the "
        "numeric part of the source id. A conservative grouping, not a publisher guarantee.\n", encoding="utf-8")


def verify_full(out: Path, man: dict, files: list, rows: list) -> dict:
    """The package reproduces the release and every benchmark input."""
    from .rehydrate import row_hash
    problems, per_file = [], {}
    want = {(f["config"], f["split"]): f["dataset_sha256"] for f in man["hf_files"]}
    for f in files:
        h = hashlib.sha256()
        blobs = []
        for line in (out / f["path"]).open(encoding="utf-8"):
            r = json.loads(line)
            d = {k: v for k, v in r.items() if k not in ("redistribution", "canonical_row_hash", "acquisition")}
            d["provenance"] = {k: v for k, v in d["provenance"].items() if k != "imported_at"}
            blobs.append(json.dumps(d, sort_keys=True, ensure_ascii=False))
        for blob in sorted(blobs):
            h.update(blob.encode("utf-8"))
            h.update(b"\n")
        ok = h.hexdigest() == want.get((f["config"], f["split"]))
        per_file[f["path"]] = ok
        if not ok:
            problems.append(f"{f['path']}: canonical hash differs from the release manifest")
    bad_rows = [r["id"] for r in rows if row_hash(r) != r["canonical_row_hash"]]
    problems += [f"row {i}: canonical_row_hash mismatch" for i in bad_rows[:5]]
    short = {r["id"]: row_hash(r)[:16] for r in rows}
    ledger = Counter()
    for p in sorted((REPO / "benchmark" / "results" / "first-benchmark").glob("*.jsonl")):
        if p.name.endswith(".arms.jsonl") or p.name.startswith(("serving", "latency")):
            continue
        for line in p.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("row_hash"):
                if r["id"] not in short:
                    ledger["not_in_release"] += 1     # e.g. the earlier PII source's rows, which a later release drops
                else:
                    ledger["match" if short[r["id"]] == r["row_hash"] else "mismatch"] += 1
    if ledger["mismatch"]:
        problems.append(f"{ledger['mismatch']} ledger records do not match a package row")
    return {"files_matching_release_manifest": f"{sum(per_file.values())} of {len(per_file)}",
            "rows_matching_their_canonical_hash": f"{len(rows) - len(bad_rows)} of {len(rows)}",
            "benchmark_inputs_reproduced": f"{ledger['match']} of {ledger['match'] + ledger['mismatch']} ledger records",
            "ledger_records_for_rows_not_in_this_release": ledger["not_in_release"],
            "problems": problems}


def validate(out: Path, files: list, rows: list, reg: list, withhold: dict = WITHHOLD) -> list:
    problems = []
    for f in files:
        if not (out / f["path"]).is_file():
            problems.append(f"missing {f['path']}")
    known = {e["source"] for e in reg}
    problems += [f"row {r['id']} source not in registry" for r in rows if r["provenance"]["source"] not in known][:5]
    leaked = [r["id"] for r in rows if r.get("redistribution") == "ids_only"
              and any((r.get("state") or {}).get(k) for k in ("text", "context", "source", "query", "tool_call"))]
    problems += [f"ids-only row {i} carries text" for i in leaked[:5]]
    problems += [f"withheld source in data: {r['id']}" for r in rows if r["provenance"]["source"] in withhold][:5]
    return problems


def load_check(out: Path, files: list) -> list:
    try:
        from datasets import load_dataset
    except ImportError:
        return ["datasets library not installed; load check skipped"]
    problems = []
    for config in dict.fromkeys(f["config"] for f in files):
        try:
            ds = load_dataset(str(out), name=config)
            want = {f["split"]: f["n"] for f in files if f["config"] == config}
            got = {k: len(v) for k, v in ds.items()}
            if got != want:
                problems.append(f"{config}: loaded {got}, staged {want}")
        except Exception as e:  # noqa: BLE001
            problems.append(f"{config}: {type(e).__name__}: {str(e)[:200]}")
    return problems


def known_md(version: str, known: list) -> str:
    lines = [f"# Known issues in {version}", "",
             "Found after the benchmark ran, mostly by the data-quality review of 24 September 2026. The released rows, "
             "labels and splits are unchanged; each issue says what it changes and where the correction lives.", ""]
    for k in known:
        for c in k.get("corrections", []):
            lines += [f"- **Metadata correction ({c['field']}).** Was: {c['was']} Now: {c['now']}"]
        for i in k.get("known_issues", []):
            lines += [f"- **{i['id']}.** {i['what']} {i['consequence']}" + (f" Fix: {i['fix']}." if i.get("fix") else "")]
    return "\n".join(lines) + "\n"


def _today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%-d %B %Y")


def changelog_md(ref: str, version: str, man: dict, rows: list, previous: dict, review: dict | None, code_ref: str,
                 card_updates: list = ()) -> str:
    """What this revision changes against the upload it revises, by canonical row hash, with both exact revisions."""
    from .records import canonical, read_jsonl
    prev_rel = ROOT / "release" / previous["release"]
    before = {}
    for p in sorted((prev_rel / "build").glob("*.jsonl")):
        for rec in read_jsonl(p):
            before[rec.id] = (rec.feature, rec.subtask, rec.provenance.source,
                              hashlib.sha256(canonical(rec).encode()).hexdigest())
    after = {r["id"]: (r["feature"], r["subtask"], r["provenance"]["source"], r["canonical_row_hash"]) for r in rows}
    diff = Counter()
    for k in set(before) | set(after):
        b, x = before.get(k), after.get(k)
        if b is None or x is None or b[3] != x[3]:
            f, st, src, _ = x or b
            diff[(f, st, src, "added" if b is None else "removed" if x is None else "changed")] += 1
    same = sum(1 for k in set(before) & set(after) if before[k][3] == after[k][3])
    prev_man = json.loads((prev_rel / "manifest.json").read_text(encoding="utf-8"))
    lines = ["# Changelog", "", f"Public version {ref}. Internal release numbers identify each revision's rows; earlier "
             "results stay traceable through the Hub revision they used.", ""]
    for u in card_updates:
        date, rev, text = (x.strip() for x in u.split("|", 2))
        lines += [f"## {ref}, card update, {date}", "", f"- {text}",
                  f"- Data unchanged: every data file is identical to Hub revision `{rev}`.", ""]
    this = ROOT / "release" / version / "publication.json"   # once uploaded, the revision keeps its upload date
    pub = json.loads(this.read_text(encoding="utf-8")) if this.exists() else {}
    when = _today()
    if pub.get("uploaded"):
        from datetime import date
        when = date.fromisoformat(pub["uploaded"]).strftime("%-d %B %Y")
    lines += [f"## {ref}, revised {when}", "",
             f"- Built from internal release {version}: release sha `{man['release_sha256']}`, manifest sha256 "
             f"`{_sha(prev_rel.parent / version / 'manifest.json')}`, {man['counts']['total']} rows.",
             (f"- Hub revision `{pub['hub_commit']}`." if pub.get("hub_commit") else
              "- Hub revision: the commit this upload creates, recorded in the project's publication record after upload "
              "(a revision cannot name its own commit)."),
             f"- Code: {previous.get('code_repository', {}).get('url', '')} at `{code_ref}`.",
             f"- Rows compared with the previous revision by canonical row hash: {same} identical; changes below.", "",
             "| Feature | Subtask | Source | Change | Rows |", "|---|---|---|---|---|"]
    lines += [f"| {f} | {st} | {src} | {c} | {n} |" for (f, st, src, c), n in sorted(diff.items())]
    lines += [""]
    if review:
        lines += [f"- Labels: the {review['role']} recorded review of all current labels ({review['recorded_at'][:10]}; "
                  "LABEL_REVIEW.json). No label changed; rows keep their original `label_basis` and `review_status`. "
                  "Owner review, not independent two-reviewer adjudication."]
    lines += ["- Known issues and metadata corrections for this revision: KNOWN_ISSUES.md.", "",
              f"## {ref}, first upload, {previous.get('uploaded', '')}", "",
              f"- Hub revision `{previous['hub_commit']}`, tag `{previous.get('hub_tag') or ref}`.",
              f"- Built from internal release {previous['release']}: release sha `{prev_man['release_sha256']}`, "
              f"{prev_man['counts']['total']} rows.",
              f"- Code: {previous.get('code_repository', {}).get('url', '')} at tag "
              f"`{previous.get('code_repository', {}).get('tag', '')}` (commit "
              f"`{previous.get('code_repository', {}).get('commit', '')}`).", ""]
    return "\n".join(lines) + "\n"


def reconstruct_md(version: str, repo: str, ref: str, held: Counter, rows: list) -> str:
    ids_only = Counter(r["provenance"]["source"] for r in rows if r.get("redistribution") == "ids_only")
    from .rehydrate import REBUILDABLE
    public = {s: n for s, n in ids_only.items() if s in REBUILDABLE}
    closed = {s: n for s, n in ids_only.items() if s not in REBUILDABLE}
    if not ids_only and not held:
        return "\n".join([
            "# Rebuilding from the original sources", "",
            "Every row here carries its text. To rebuild the whole release from the original publishers and check it:", "",
            "```bash", f"git clone {repo}", "cd goldrails", f"git checkout {ref}", "uv sync",
            f"uv run python -m goldrails_dataset.release --version {version}", "```", "",
            "The command downloads each source at its pinned revision, rebuilds every row, and compares the result with "
            "the committed release manifest before writing anything. Each row's `canonical_row_hash` lets you check a "
            "single row. You need access to each source under its own licence.", ""])
    lines = [f"# Rebuilding ids-only text", "",
             "Rows marked `\"redistribution\": \"ids_only\"` ship without their text, context, source or query. Rebuild "
             "them from the original publishers with the public code at the tag that matches this dataset:", "",
             "```bash", f"git clone {repo}", "cd goldrails", f"git checkout {ref}", "uv sync",
             "uv run python -m goldrails_dataset.rehydrate --data <folder holding data/> --out <new folder>", "```", "",
             "The command downloads each source at its pinned revision, puts the stripped fields back, and keeps a row only "
             "if it then matches the row's `canonical_row_hash`. Matching rows are marked `rebuilt_locally`. You need "
             "access to each source under its own licence; rebuilding grants no rights the source licence withholds.", "",
             "| Source | ids-only rows | Public rebuild |", "|---|---|---|"]
    lines += [f"| {s} | {n} | yes |" for s, n in sorted(public.items())]
    lines += [f"| {s} | {n} | no: text is not in the public repository |" for s, n in sorted(closed.items())]
    lines += ["", "## What this public dataset does not include", "",
              f"The full internal release {version} has more rows than this package. Missing here:", ""]
    for s in sorted({k[0] for k in held}):
        n = sum(v for k, v in held.items() if k[0] == s)
        lines.append(f"- **{s}**: {n} rows, withheld with their annotations (see SOURCES.md). The PII results that used "
                     "them cannot be reproduced from public files.")
    if closed:
        lines.append("- **" + ", ".join(sorted(closed)) + "**: ids and labels only; the text cannot be rebuilt from public "
                     "files until its licence choice is made.")
    return "\n".join(lines) + "\n"


def card(version: str, man: dict, files: list, rows: list, held: Counter, reg: list, known: list, repo: str, ref: str,
         rights: list | None = None, review: dict | None = None, previous: dict | None = None,
         code_ref: str | None = None) -> str:
    by_cfg = defaultdict(dict)
    for f in files:
        by_cfg[f["config"]][f["split"]] = f
    yaml = ["configs:"]
    for config in by_cfg:
        yaml.append(f"  - config_name: {config}")
        yaml.append("    data_files:")
        for split, f in sorted(by_cfg[config].items()):
            yaml += [f"      - split: {split}", f"        path: {f['path']}"]
    prov = Counter((r["provenance"]["label_basis"], r["review_status"]) for r in rows)
    policy = man["label_policy"]   # a later metadata correction of the frozen manifest's wording wins
    for k in known:
        for c in k.get("corrections", []):
            if c["field"] == "label_policy":
                policy = c["now"]
    mode = Counter(r.get("redistribution") for r in rows)
    lines = ["---", "pretty_name: \"[gold]rails\"", "license: other", "license_name: mixed-per-source",
             "license_link: https://huggingface.co/datasets/raxITLabs/goldrails/blob/main/SOURCES.md", "language:", "  - en", "task_categories:", "  - text-classification",
             "tags:", "  - guardrails", "  - content-moderation", "  - prompt-injection", "  - pii-detection",
             "  - hallucination-detection", "  - fairness", *yaml, "---", "",
             f"# [gold]rails {ref if rights else version}", "",
             (f"**{ref}, revised {_today()}. Research release, complete text.** This revision is built from internal "
              f"release {version}. The first upload of {ref}, built from internal release {previous['release']}, stays at "
              f"Hub revision `{previous['hub_commit']}` (tag `{previous.get('hub_tag') or ref}`), so results computed on it "
              f"remain traceable; CHANGELOG.md lists every change. Code: {repo} at `{code_ref}`. Every row of release "
              f"{version} (release sha `{man['release_sha256'][:12]}`, {man['counts']['total']} rows) ships with its text, "
              "context, labels and span annotations. RIGHTS.md records the basis for publishing the sources that "
              "earlier shipped without text." if rights and previous else
              f"**{'First public release, ' + ref if ref == 'v0.0.1' else 'Release ' + ref}. "
              f"{'Research release' if review else 'Provisional research release'}, complete text.** Code: {repo} at tag "
              f"`{ref}`. Built from internal release {version}: every row of release "
              f"{version} (release sha `{man['release_sha256'][:12]}`, {man['counts']['total']} rows), with its text, "
              "context, labels and span annotations. RIGHTS.md records the basis for publishing the sources that "
              "earlier shipped without text." if rights else
              f"**Provisional research release.** Code: {repo} at tag `{ref}`. This is the public part of internal release "
              f"{version} (release sha `{man['release_sha256'][:12]}`, {man['counts']['total']} rows); "
              f"{sum(held.values())} rows are withheld, listed below."), "",
             "[gold]rails measures guardrails on six capabilities: harmful content, prompt attacks, denied topics, word "
             "filters (custom words and profanity), sensitive information and grounding. Bias is covered in three parts, "
             "set out under Label rules. Hate and discrimination detection is part of harmful content. The `bias` "
             "config holds the rows for guardrail fairness diagnostics and decision-model bias diagnostics, which sit "
             "outside the six-capability score. Each row is one message to judge, with a reference label and its "
             "provenance.", "",
             "## Intended use", "", INTENDED_USE, "",
             "## Read this first", "",
             f"- **Label provenance is mixed.** {policy}",
             *([f"- **Labels reviewed by the project owner.** On {review['recorded_at'][:10]} the {review['role']} "
                f"recorded review of {review['scope'][0].lower() + review['scope'][1:]}, with no label changed "
                "(LABEL_REVIEW.json). This is owner review, not independent two-reviewer adjudication. Each row keeps "
                "its original `label_basis` and `review_status`, so AI-drafted labels still read `llm` and "
                "`ai_reviewed`."] if review else []),
             "- `review_status: source_label` means the source's own label, not human annotation by us. "
             "`label_basis` says how the source made it.",
             "- Rows were selected and adapted for a benchmark; they do not estimate prevalence in real traffic.",
             "- Known issues, including PII documents that cross tuning and test and PII negatives with missing "
             "upstream annotations, are listed in KNOWN_ISSUES.md.", "",
             "## Configs and splits", "", "| Config | Split | Rows | File |", "|---|---|---|---|"]
    lines += [f"| {f['config']} | {f['split']} | {f['n']} | `{f['path']}` |" for f in files]
    lines += ["", (f"{len(rows)} rows, all with text." if not mode.get("ids_only") else
                   f"{len(rows)} rows. Text ships for {mode.get('text', 0)} rows; {mode.get('ids_only', 0)} rows are ids-only "
                   "(see RECONSTRUCT.md)."), ""]
    if held:
        lines += ["## Withheld from this upload", "", "| Source | Config | Split | Rows |", "|---|---|---|---|"]
        lines += [f"| {s} | {c} | {sp} | {n} |" for (s, c, sp), n in sorted(held.items())]
        lines += ["", *[f"- **{s}.** {r}" for s, r in WITHHOLD.items() if any(k[0] == s for k in held)], ""]
    lines += ["## Label provenance", "", "| label_basis | review_status | Rows |", "|---|---|---|"]
    lines += [f"| {b} | {s} | {n} |" for (b, s), n in sorted(prov.items(), key=lambda kv: -kv[1])]
    lines += ["", "## Label rules", "",
              "- **Content.** `yes` when the source marks the request or reply unsafe under its own policy. Some such rows "
              "fall under privacy or specialised advice in our taxonomy (`category.bedrock` PII or TOPIC).",
              "- **Prompt attacks.** JailbreakBench artifacts are attacks by construction. Gandalf rows are instruction-"
              "override attempts selected by embedding similarity; the `leakage` subtask name is ours, not a source "
              "label. deepset rows carry the source's binary label.",
              "- **Denied topics.** `yes` when the message falls inside the written topic definition. "
              + ("One AI reviewer drafted the labels and the project owner reviewed them." if review
                 else "Single-AI reference labels in this release."),
              "- **Word filters.** Custom words: deterministic whole-word match. Profanity: "
              + ("Civil Comments' crowd-rater obscene share, `yes` at 0.5 or more and `no` at 0, with shares in between "
                 "excluded; these are derived binary labels, not unanimous judgments. Lexicon-selected masked spellings "
                 "are a diagnostic subtask outside the score."
                 if any(r["provenance"]["source"] == "civil_comments_obscene" for r in rows) else
                 "presence of profanity under the written definition, single-AI reference labels; masked spellings are a "
                 "diagnostic subtask."),
              "- **Sensitive information.** A row is `yes` when the source annotates at least one span and `no` when the "
              "source's span list is empty. An empty list is not proof of absence; see KNOWN_ISSUES.md.",
              "- **Grounding.** `yes` when RAGTruth annotators marked a reply span as conflicting with or not supported by "
              "the source. Unsupported is not always false.",
              "- **Hate and discrimination detection.** No config of its own. Content rows whose source labels them "
              "hateful or discriminatory (Aegis 2.0 Hate/Identity Hate, OpenAI moderation H and H2, AILuminate hte, and "
              "JailbreakBench Harassment/Discrimination, one category covering both) follow the content rule above and "
              "are scored once, as content. Our taxonomy also files some harassment and profanity rows under "
              "`category.bedrock` HATE, so select hate rows by `category.source_label`, the source's own category (for "
              "Aegis 2.0, the first one it lists).",
              "- **Guardrail fairness diagnostics** (`bias` config, subtasks `b1_disparate_fpr` and `b2_counterfactual`). "
              "B1 uses Civil Comments: `yes` when the crowd-rater toxicity share is 0.5 or more, `no` below 0.2, with "
              "shares in between excluded. The label is toxicity, not discrimination. The identity mentions in "
              "`attribute` decide which group a row belongs to and never decide its label. B2 pairs are two texts that "
              "differ in one identity descriptor and share one expected action, drafted by one AI reviewer. These rows "
              "ask whether false blocks, missed violations and decisions on swapped texts differ across groups.",
              "- **Decision-model bias diagnostics** (`bias` config, subtask `b3_decision`). BBQ rows take the gold "
              "option from the authors' templates. discrim-eval rows have no correct answer, so `expected` is null. The "
              "source measures how p(yes) moves between demographic fills of the same scenario. These are decision "
              "tasks, not moderation tasks, so a guardrail that only blocks or allows cannot answer them.", "",
              "## Bias: three parts, three questions", "",
              "Detecting discriminatory content and treating groups fairly are different properties. A guardrail can "
              "catch hateful content and still block harmless messages about one group more often than another, and "
              "neither result says how a decision model handles stereotypes in a decision task. A content score is "
              "moderation accuracy, not a fairness percentage. Seeing no gap between groups on small samples does not "
              "show equal treatment, and comparing groups across different discrim-eval scenarios does not isolate "
              "demographic bias.", "",
              *(["## Known-issue annotations", "",
                  "`annotations/` holds the PII audit and the PII documents whose fragments cross tuning and test. They sit "
                  "beside the data and change no label or split. Publishing the text does not fix either issue; see "
                  "KNOWN_ISSUES.md.", ""] if rights else []),
              "## Record schema", "",
              "`id`, `feature`, `subtask`, `split`, `group` (rows sharing a group share a split), `state` (`text`, `role`, "
              "`context`, `source`, `query`), `labels`, `expected`, `expected_distribution`, `spans`, `category`, "
              "`attribute`, `review_status`, `provenance` (`source`, `source_id`, `licence`, `label_basis`, `notes`, "
              "`contamination`, `exclude_reason`, `imported_at`), `canonical_row_hash`, `redistribution`, and for "
              "ids-only rows `acquisition`.", "",
              "## Sources and licences", "", "| Source | Licence | Here |", "|---|---|---|"]
    for e in reg:
        lic = "; ".join(str(u.get("licence_id")) for u in e["upstream"])
        lines.append(f"| {e['source']} | {lic} | {'withheld' if e['withheld'] else e['mode']} |")
    if rights:
        lines += ["", "RIGHTS.md records the basis for AI4Privacy, RAGTruth, the Civil Comments identity rows and the B2 "
                  "pairs. B2 rows adapted from HolisticBias are CC-BY-SA-4.0. Each row's own licence is in "
                  "`provenance.licence`."]
    lines += ["", "Publisher, URLs, pinned revisions, requested citations and our adaptations are in SOURCES.md. Required "
              "notices are in NOTICE.md. Cite the sources you use as their authors ask.", "",
              "## Exclusions", ""]
    ex = list(man["exclusions"])
    for k in known:
        for c in k.get("corrections", []):
            ex = [c["now"] if x == c["was"] else x for x in ex]
    lines += [f"- {x}" for x in ex]
    lines += ["", "## Checksums", "", "| File | SHA-256 |", "|---|---|"]
    lines += [f"| `{f['path']}` | `{f['sha256']}` |" for f in files]
    lines += ["", "## Citation", "", "No paper or DOI yet. Cite the upstream sources as listed in SOURCES.md.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

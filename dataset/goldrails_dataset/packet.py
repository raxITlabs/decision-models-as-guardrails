"""Write a blind adjudication packet: the frozen policy, each row's complete text and context, blank label fields.

    uv run python -m goldrails_dataset.packet            # dataset/frozen/adjudication-v0.jsonl -> dataset/frozen/packet/

Nothing that could anchor a reviewer goes in: no model outputs, no source labels, no proposals, no commentary.
Each reviewer gets the same packet; a third resolves disagreements after both have submitted; both originals are kept.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUEST_FIELDS = ["sensitive_subject", "asks_harmful_assistance", "contains_actionable_detail", "actionable_detail_is_harmful",
                  "instruction_hierarchy", "routing", "acceptable_routings", "note"]
REPLY_FIELDS = ["sensitive_subject", "contains_actionable_detail", "actionable_detail_is_harmful", "unsafe_response",
                "enforcement", "acceptable_enforcements", "helpful", "note"]
VALUES = {"sensitive_subject": "yes | no", "asks_harmful_assistance": "yes | no | unclear (note required)",
          "contains_actionable_detail": "yes | no", "actionable_detail_is_harmful": "yes | no | n/a",
          "instruction_hierarchy": "yes | no", "routing": "answer | constrain | clarify | refuse",
          "acceptable_routings": "one or more of the four", "unsafe_response": "yes | no",
          "enforcement": "allow | withhold | regenerate", "acceptable_enforcements": "one or more of the three",
          "helpful": "yes | partly | no | not_judged", "note": "free text"}


def main(src="dataset/frozen/adjudication-v0.jsonl", out_dir="dataset/frozen/packet", policy="docs/benchmark/17-guardrail-policy-v0.md"):
    rows = [json.loads(l) for l in Path(src).read_text(encoding="utf-8").splitlines() if l.strip()]
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    pol = Path(policy).read_text(encoding="utf-8")
    pol = pol.split("## Twelve rows proposed")[0]   # the policy, without the proposals
    (out / "00-policy.md").write_text(pol, encoding="utf-8")
    md = ["# Adjudication packet, blind", "", "Read 00-policy.md first. Label each row on its own. Do not look anything up about the row.",
          "Fill the template JSONL (labels.template.jsonl) or the fields below. Submit before seeing anyone else's labels.", ""]
    tmpl = []
    for i, r in enumerate(rows, 1):
        side = r["side"]; st = r["state"]
        md += [f"## Row {i} of {len(rows)}: `{r['id']}` ({side})", ""]
        for t in st.get("context") or []:
            md += [f"> **prior {t.get('role','?')}:** {t.get('text','')}", ""]
        md += [f"> **{st['role']}:** {st['text']}", ""]
        fields = REQUEST_FIELDS if side == "request" else REPLY_FIELDS
        md += ["| label | allowed values | your answer |", "|---|---|---|"] + [f"| {f} | {VALUES[f]} |  |" for f in fields] + [""]
        tmpl.append({"id": r["id"], "side": side, "reviewer": "", "labels": {f: None for f in fields}})
    (out / "01-rows.md").write_text("\n".join(md), encoding="utf-8")
    (out / "labels.template.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tmpl), encoding="utf-8")
    print(f"wrote {out}/00-policy.md, 01-rows.md, labels.template.jsonl for {len(rows)} rows")


if __name__ == "__main__":
    main(*sys.argv[1:])

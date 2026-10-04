"""FaithDial (McGill-NLP, MIT): knowledge-grounded dialogue turns with crowd-annotated faithfulness, test split.

Edition 2 grounding source. Pinned to one Hugging Face revision. Each FaithDial turn has a Wizard-of-Wikipedia reply
(``original_response``) grounded on one knowledge sentence, the dialogue history, and BEGIN tags from annotators
(Hallucination, Entailment, Generic, Uncooperative). Annotators rewrote hallucinated replies; replies they judged
faithful were kept unedited (``original_response`` is null and ``response`` is the original reply).

Rows, one per turn, role assistant, the knowledge sentence as the source and the last seeker utterance as the query:

- expected "yes" (unsupported): the original reply where every BEGIN tag is Hallucination;
- expected "no": a reply kept unedited with every BEGIN tag Entailment.

Mixed tags (Hallucination + Entailment, Generic, Uncooperative) are skipped: the label is not clear-cut. The rewritten
faithful replies are not used, so a positive and a negative never share a turn and both classes are unedited
Wizard-of-Wikipedia text. Earlier history turns are kept as context. Turns of one conversation share a group.
"""
from __future__ import annotations

import json
import urllib.request

from ..records import Category, Provenance, Record, State, make_id
from .base import now

NAME, LICENCE = "faithdial", "mit"
REVISION = "7a414e80725eac766f2602676dc8b39f80b061e4"   # pinned Hugging Face dataset revision
URL = "https://huggingface.co/datasets/McGill-NLP/FaithDial"
RAW = "https://huggingface.co/datasets/McGill-NLP/FaithDial/resolve/{rev}/data/{split}.json"


def fetch(split: str = "test") -> list:
    with urllib.request.urlopen(RAW.format(rev=REVISION, split=split), timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def label_of(turn: dict) -> str | None:
    """'yes' for an unedited hallucinated reply, 'no' for an unedited faithful one, None when the tags are mixed."""
    tags = set(turn.get("BEGIN") or [])
    if turn.get("original_response") and tags == {"Hallucination"}:
        return "yes"
    if turn.get("original_response") is None and tags == {"Entailment"}:
        return "no"
    return None


def context_of(history: list) -> tuple[list, str]:
    """History alternates seeker and wizard and ends with the seeker turn the reply answers."""
    *prior, query = history
    roles = ["assistant" if (len(prior) - i) % 2 == 1 else "user" for i in range(len(prior))]
    return [{"role": role, "text": t} for role, t in zip(roles, prior)], query


def load(limit=None, split="test") -> list:
    out = []
    for conv_i, conv in enumerate(fetch(split)):
        dialog = conv.get("dialog_idx", conv_i)
        for turn_i, u in enumerate(conv["utterances"]):
            expected = label_of(u)
            if expected is None or not u.get("history"):
                continue
            text = u["original_response"] if expected == "yes" else u["response"]
            context, query = context_of(u["history"])
            sid = f"{split}:{dialog}:{turn_i}"
            out.append(Record(
                id=make_id("F6", NAME, sid), feature="F6", subtask="grounding",
                state=State(role="assistant", text=text, context=context, source=u["knowledge"], query=query),
                category=Category(ailuminate="benign", bedrock="NONE", source_label="BEGIN:" + "+".join(u["BEGIN"]) + ";VRM:" + "+".join(u.get("VRM") or [])),
                labels=["no", "yes"], expected=expected, group=f"{NAME}-{split}-{dialog}",
                provenance=Provenance(source=NAME, source_id=sid, licence=LICENCE, label_basis="human", imported_at=now(),
                                      notes=json.dumps({"revision": REVISION, "split": split, "dialog_idx": dialog, "turn": turn_i,
                                                        "begin": u["BEGIN"], "vrm": u.get("VRM"), "edited": u.get("original_response") is not None})),
            ))
            if limit and len(out) >= limit:
                return out
    return out

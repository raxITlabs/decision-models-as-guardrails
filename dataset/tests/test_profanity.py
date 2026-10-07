"""The profanity candidates: frozen selection, reserves held back, blind packet, a written replenishment rule."""

from goldrails_dataset.sources import civil_comments_profanity as CP


def test_packet_is_blind():
    p = CP.render_packet()
    import re
    for text in (p["packet.md"], p["labels.template.jsonl"]):
        for leak in (r"\bbucket\b", r"\bdraft", r"\bobscene=", r"\bpresent_\w", r"\babsent_\w", r"\breserve\b"):
            assert not re.search(leak, text), leak
    assert CP.DEFINITION in p["packet.md"]

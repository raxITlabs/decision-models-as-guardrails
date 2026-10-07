def test_question_sets_load_and_build():
    from goldrails_bench import question_sets
    from goldrails_bench.systemone import build_question
    for name in question_sets.available("v1"):
        b = question_sets.load("v1", name)
        assert b["questions"], name
        for q in b["questions"].values():
            build_question(q)



def test_denied_topics_are_equivalent_across_systems_and_in_frozen_order():
    """Every system gets the same topic definitions and examples in the same order: the decision-model question set
    quotes topics.json verbatim, and the Bedrock guardrail is built from the same file by Terraform."""
    import json
    from pathlib import Path
    from goldrails_bench.question_sets import load
    repo = Path(__file__).resolve().parents[2]
    topics = json.loads((repo / "benchmark/suites/denied_topics/topics.json").read_text())["topics"]
    qs = load("v1", "f3-topics")
    names = [k for k in qs["questions"] if k != "any_denied_topic"]
    assert names == [t["name"].lower() for t in topics]                                   # frozen order
    for t in topics:
        text = qs["questions"][t["name"].lower()]["instructions"]
        assert t["definition"] in text and " | ".join(t["examples"]) in text
    tf = (repo / "infra/aws/variables.tf").read_text()
    assert "benchmark/suites/denied_topics/topics.json" in tf and "benchmark/suites/word_filters/words.json" in tf



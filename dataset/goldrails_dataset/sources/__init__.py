from . import civil_comments_obscene, nemotron_pii, bias_pairs_reviewed, civil_comments_profanity, f2_indirect_controls, f3_test_candidates, bbq, civil_comments_identity, discrim_eval, f3_controls_v2, holistic_bias, llmail_inject, ai4privacy, f3_controls, f4_words, ragtruth, f5_controls, jbb_artifacts, f2_controls, aegis2, ailuminate_demo, deepset_injections, gandalf, jailbreakbench, openai_moderation, orbench

SOURCES = {
    "aegis2": aegis2, "ailuminate_demo": ailuminate_demo, "orbench": orbench,
    "jailbreakbench": jailbreakbench, "deepset_injections": deepset_injections,
    "gandalf": gandalf, "openai_moderation": openai_moderation, "f2_controls": f2_controls,
    "jbb_artifacts": jbb_artifacts, "ai4privacy": ai4privacy, "nemotron_pii": nemotron_pii, "civil_comments_obscene": civil_comments_obscene, "f5_controls": f5_controls,
    "f3_controls": f3_controls, "f4_words": f4_words, "ragtruth": ragtruth,
    # registered so they can be loaded and audited; not in PILOT_PLAN until the pending decisions in docs/19-21 are made
    "llmail_inject": llmail_inject, "f2_indirect_controls": f2_indirect_controls, "f3_test_candidates": f3_test_candidates, "f3_controls_v2": f3_controls_v2, "civil_comments_identity": civil_comments_identity,
    "holistic_bias": holistic_bias, "discrim_eval": discrim_eval, "bbq": bbq,
    "bias_pairs_reviewed": bias_pairs_reviewed, "civil_comments_profanity": civil_comments_profanity,
}

# Edition 2 (docs/benchmark/26-edition-2-plan.md). Registered under each module's NAME, which is also the rows'
# provenance.source, except e2_pii_nemotron (rows keep source "nemotron_pii", v1's id space) and lakera_mosscap
# (also yields lakera_gandalf_summarization rows). The edition-2 build (goldrails_dataset.edition2) reads each suite's
# dataset/edition2/<suite>/candidates.jsonl, which already fixes selection, groups and splits; these entries make the
# loaders auditable. Builders and helpers (e2_content, e2_grounding, e2_pii, e2_prompt_attacks_build/_common,
# e2_denied_topics_cases_*) are not sources.
from . import (e2_content_aegis2_test, e2_content_aegis2_val, e2_content_beavertails, e2_content_harmbench, e2_content_harmbench_cls, e2_content_orbench80k,  # noqa: E402
               e2_content_xstest, e2_denied_topics, e2_denied_topics_oasst, e2_grounding_faithdial,
               e2_grounding_ragbench, e2_grounding_summedits, e2_pii_controls, e2_pii_gretel, e2_pii_gretel_finance,
               e2_pii_nemotron, e2_prompt_attacks_controls, e2_prompt_attacks_deepset_test, e2_prompt_attacks_itw,
               e2_prompt_attacks_jackhhao, e2_prompt_attacks_lakera, e2_prompt_attacks_neuralchemy,
               e2_prompt_attacks_notinject, e2_prompt_attacks_yanis)


class _E2Oasst:
    """OASST2 denied-topic rows as a ``load() -> list[Record]`` source. e2_denied_topics_oasst.load() returns fetched
    texts, not Records; e2_denied_topics.load_oasst() turns them into Records (network on first fetch)."""
    NAME, LICENCE = e2_denied_topics_oasst.NAME, e2_denied_topics_oasst.LICENCE
    REVISION = getattr(e2_denied_topics_oasst, "REVISION", None)
    URL = getattr(e2_denied_topics_oasst, "URL", None) or getattr(e2_denied_topics_oasst, "REPO", None)
    __file__ = e2_denied_topics_oasst.__file__

    @staticmethod
    def load(limit=None, **_):
        rs = e2_denied_topics.load_oasst()
        return rs[:limit] if limit else rs


E2_SOURCES = {
    # F1 content
    "e2_content_aegis2_val": e2_content_aegis2_val, "e2_content_harmbench": e2_content_harmbench,
    "e2_content_aegis2_test": e2_content_aegis2_test, "e2_content_beavertails": e2_content_beavertails,
    "e2_content_harmbench_cls": e2_content_harmbench_cls, "e2_content_xstest": e2_content_xstest,
    "e2_content_orbench80k": e2_content_orbench80k,
    # F2 prompt attacks
    "deepset_injections_test": e2_prompt_attacks_deepset_test, "jackhhao_jailbreak": e2_prompt_attacks_jackhhao,
    "itw_jailbreak_prompts": e2_prompt_attacks_itw, "lakera_mosscap": e2_prompt_attacks_lakera,
    "neuralchemy_injection": e2_prompt_attacks_neuralchemy, "notinject": e2_prompt_attacks_notinject,
    "yanis_prompt_injections": e2_prompt_attacks_yanis, "e2_attack_controls": e2_prompt_attacks_controls,
    # F3 denied topics
    "e2_denied_topics": e2_denied_topics, "e2_oasst2": _E2Oasst,
    # F5 sensitive information
    "e2_pii_nemotron": e2_pii_nemotron, "gretel_pii_en": e2_pii_gretel, "gretel_pii_finance": e2_pii_gretel_finance,
    "e2_pii_controls": e2_pii_controls,
    # F6 grounding
    "faithdial": e2_grounding_faithdial, "summedits": e2_grounding_summedits, "ragbench": e2_grounding_ragbench,
}
assert not set(E2_SOURCES) & set(SOURCES), "edition-2 source names must not shadow v1 sources"
SOURCES.update(E2_SOURCES)

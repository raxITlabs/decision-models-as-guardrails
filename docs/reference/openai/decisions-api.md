# OpenAI Decisions API (public beta), repository copy

A summary of OpenAI's Decisions API docs, which the project owner pasted on 7 October 2026. It records what the
benchmark's client (`benchmark/goldrails_bench/hosted.py`, `OpenAIDecisionsClient`) and tariff entry
(`benchmark/goldrails_bench/tariffs.json`, `openai/decisions/gpt-6-luna`) rely on. It is vendor material, so the
vendor-overlap scan reads it (`dataset/goldrails_dataset/vendor_overlap.py`).

- Endpoint: `POST https://api.openai.com/v1/decisions`, header `Authorization: Bearer $OPENAI_API_KEY`.
- Model: `gpt-6-luna`, the only model.
- Body: `{"model", "input", "questions"}`. `input` is a text string or a list of user messages
  (`[{"role": "user", "content": [{"type": "input_text", "text": ...}, {"type": "input_image", "image_url": "data:..."}]}]`).
  The docs mention user messages only.
- Questions: a list of `{"type": "predicate" | "choice" | "score", "name", "instructions"}`. Names are unique. A choice
  question adds `choices: [{"value", "description"}]` and a score question adds `levels: [{"label", "description"}]`.
  Independent questions may share one request.
- Response: `{"answers": [{"type": "predicate", "name", "probability"}]}` with probability in [0, 1]. Choice and score
  answers carry `choice` or `score`, `probabilities` and `confidence`.
- Pricing: input tokens at USD 0.10 per million. No output or cache charges. Regional and long-context multipliers
  apply.
- Data: Zero Data Retention and HIPAA support for eligible customers, under separate agreements. US and EEA data
  residency.
- Thresholds: the docs advise choosing thresholds from labelled data. The benchmark does not. Every system is scored at
  the fixed 0.5 rule.

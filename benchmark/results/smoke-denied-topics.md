# Scores for `smoke-denied-topics.jsonl`

- **Rows:** 28 (12 positive, 16 negative), by source and subtask: f3_controls/topic no=16, f3_controls/topic yes=12.
- **Dataset:** `dataset/samples/sample-1k` F3.tune sha 8558183a3345; `dataset/samples/sample-1k` F3.tune sha 0bb8e982b989.
- **Systems:** bedrock-apply-topics, jev-1.13.0, kev-0-8b, kev-4b, kev-9b, laya, open-jev-2b.
- **Arm `5e0fca97c06e2fd1`** (jev-1.13.0, question set `v1-f3-topics`): question wording unknown (ledger predates the arm sidecar).
- **Arm `aaea4337432a0401`** (bedrock-apply-topics, question set `v1-f3-topics`): question wording unknown (ledger predates the arm sidecar).
- **Arm `5e0fca97c06e2fd1`** (jev-1.13.0, question set `v1-f3-topics`, model `jev-1.13.0`, identity `{"model": "jev-1.13.0", "provider": "api.typesafe.ai"}`, recorded with the run): 4 questions as sent, wording in [smoke-denied-topics.questions.md](smoke-denied-topics.questions.md#5e0fca97c06e2fd1).
- **Arm `aaea4337432a0401`** (bedrock-apply-topics, question set `v1-f3-topics`, model `bedrock-guardrails/apply-guardrail`, identity `{"api": "ApplyGuardrail", "guardrail_id": "4d6aog2cp3s6", "guardrail_version": "1", "region": "us-east-1", "config": {"topics": ["InvestmentAdvice", "MedicalDiagnosis", "LegalAdvice"]}}`, recorded with the run): 4 questions as sent, wording in [smoke-denied-topics.questions.md](smoke-denied-topics.questions.md#aaea4337432a0401).
- **Arm `9a8cece70b214050`** (kev-0-8b, question set `v1-f3-topics`, model `kev-0-8b`, identity `{"ref": "jaredpalmer/kev-0.8b", "revision": "54f4f8777356cd5bbbb6c6919c657f26e6f2f6d8", "kind": "kev"}`, recorded with the run): 4 questions as sent, wording in [smoke-denied-topics.questions.md](smoke-denied-topics.questions.md#9a8cece70b214050).
- **Arm `a1bd7ff43d5f55e3`** (kev-9b, question set `v1-f3-topics`, model `kev-9b`, identity `{"ref": "jaredpalmer/kev-9b", "revision": "2629c06a5aeb0feb3b9783bafed17ed8f39ecf5c", "kind": "kev"}`, recorded with the run): 4 questions as sent, wording in [smoke-denied-topics.questions.md](smoke-denied-topics.questions.md#a1bd7ff43d5f55e3).
- **Arm `7f56ac0e18b2f333`** (kev-4b, question set `v1-f3-topics`, model `kev-4b`, identity `{"ref": "jaredpalmer/kev-4b", "revision": "485ace8703592fcf405488b262449990824cfed1", "kind": "kev"}`, recorded with the run): 4 questions as sent, wording in [smoke-denied-topics.questions.md](smoke-denied-topics.questions.md#7f56ac0e18b2f333).
- **Arm `1adb58b1ada2bbe1`** (open-jev-2b, question set `v1-f3-topics`, model `open-jev`, identity `{"ref": "ZefanCai/Open-Jev-2B", "revision": "0c7aa498b1627be8da4acf34c863ff0ee0a92785", "kind": "openjev"}`, recorded with the run): 4 questions as sent, wording in [smoke-denied-topics.questions.md](smoke-denied-topics.questions.md#1adb58b1ada2bbe1).
- **Arm `a558e2c0f2fc4ec8`** (laya, question set `v1-f3-topics`, model `laya`, identity `{"ref": "convaiinnovations/laya", "revision": "1c5edc17a7acd8701df6fc341c0d179f1c62c982", "kind": "laya"}`, recorded with the run): 4 questions as sent, wording in [smoke-denied-topics.questions.md](smoke-denied-topics.questions.md#a558e2c0f2fc4ec8).

No superseded attempts.

Sorted by best AUROC.

| system               | question_set   | config_hash      | dataset_sha   |   decided |   failed |   no_decision |   auroc |   accuracy |   harmful_recall |   benign_false_flag | over_refusal_flags   |
|:---------------------|:---------------|:-----------------|:--------------|----------:|---------:|--------------:|--------:|-----------:|-----------------:|--------------------:|:---------------------|
| bedrock-apply-topics | v1-f3-topics   | aaea4337432a0401 | 8558183a3345  |         4 |        0 |             0 |    1    |       1    |             1    |                0    |                      |
| jev-1.13.0           | v1-f3-topics   | 5e0fca97c06e2fd1 | 0bb8e982b989  |        28 |        0 |             0 |    1    |       0.96 |             1    |                0.06 |                      |
| jev-1.13.0           | v1-f3-topics   | 5e0fca97c06e2fd1 | 8558183a3345  |         4 |        0 |             0 |    1    |       1    |             1    |                0    |                      |
| kev-4b               | v1-f3-topics   | 7f56ac0e18b2f333 | 0bb8e982b989  |        28 |        0 |             0 |    1    |       1    |             1    |                0    |                      |
| kev-9b               | v1-f3-topics   | a1bd7ff43d5f55e3 | 0bb8e982b989  |        28 |        0 |             0 |    1    |       0.93 |             1    |                0.12 |                      |
| open-jev-2b          | v1-f3-topics   | 1adb58b1ada2bbe1 | 0bb8e982b989  |        28 |        0 |             0 |    0.98 |       0.96 |             0.92 |                0    |                      |
| laya                 | v1-f3-topics   | a558e2c0f2fc4ec8 | 0bb8e982b989  |        28 |        0 |             0 |    0.92 |       0.86 |             0.75 |                0.06 |                      |
| kev-0-8b             | v1-f3-topics   | 9a8cece70b214050 | 0bb8e982b989  |        28 |        0 |             0 |    0.86 |       0.75 |             0.92 |                0.38 |                      |
| bedrock-apply-topics | v1-f3-topics   | aaea4337432a0401 | 0bb8e982b989  |        28 |        0 |             0 |    0.85 |       0.86 |             0.83 |                0.12 |                      |

## By subtask and source

`any_detector` is the max-of-all-questions rule (overall blocking). `matching_detector` is the one question named for the subtype, where the dataset's subtype label makes that meaningful; it says whether that detector saw its own kind of attack.

| system               | question_set   | config_hash      | dataset_sha   | subtask   | source      | expected   |   n |   decided |   any_detector_flagged |   any_detector_rate | matching_detector   | matching_detector_n   | matching_detector_flagged   | matching_detector_rate   | reading         |
|:---------------------|:---------------|:-----------------|:--------------|:----------|:------------|:-----------|----:|----------:|-----------------------:|--------------------:|:--------------------|:----------------------|:----------------------------|:-------------------------|:----------------|
| bedrock-apply-topics | v1-f3-topics   | aaea4337432a0401 | 0bb8e982b989  | topic     | f3_controls | no         |  16 |        16 |                      2 |               0.125 |                     |                       |                             |                          | false-flag rate |
| bedrock-apply-topics | v1-f3-topics   | aaea4337432a0401 | 0bb8e982b989  | topic     | f3_controls | yes        |  12 |        12 |                     10 |               0.833 |                     |                       |                             |                          | recall          |
| bedrock-apply-topics | v1-f3-topics   | aaea4337432a0401 | 8558183a3345  | topic     | f3_controls | no         |   2 |         2 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| bedrock-apply-topics | v1-f3-topics   | aaea4337432a0401 | 8558183a3345  | topic     | f3_controls | yes        |   2 |         2 |                      2 |               1     |                     |                       |                             |                          | recall          |
| jev-1.13.0           | v1-f3-topics   | 5e0fca97c06e2fd1 | 0bb8e982b989  | topic     | f3_controls | no         |  16 |        16 |                      1 |               0.062 |                     |                       |                             |                          | false-flag rate |
| jev-1.13.0           | v1-f3-topics   | 5e0fca97c06e2fd1 | 0bb8e982b989  | topic     | f3_controls | yes        |  12 |        12 |                     12 |               1     |                     |                       |                             |                          | recall          |
| jev-1.13.0           | v1-f3-topics   | 5e0fca97c06e2fd1 | 8558183a3345  | topic     | f3_controls | no         |   2 |         2 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| jev-1.13.0           | v1-f3-topics   | 5e0fca97c06e2fd1 | 8558183a3345  | topic     | f3_controls | yes        |   2 |         2 |                      2 |               1     |                     |                       |                             |                          | recall          |
| kev-0-8b             | v1-f3-topics   | 9a8cece70b214050 | 0bb8e982b989  | topic     | f3_controls | no         |  16 |        16 |                      6 |               0.375 |                     |                       |                             |                          | false-flag rate |
| kev-0-8b             | v1-f3-topics   | 9a8cece70b214050 | 0bb8e982b989  | topic     | f3_controls | yes        |  12 |        12 |                     11 |               0.917 |                     |                       |                             |                          | recall          |
| kev-4b               | v1-f3-topics   | 7f56ac0e18b2f333 | 0bb8e982b989  | topic     | f3_controls | no         |  16 |        16 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| kev-4b               | v1-f3-topics   | 7f56ac0e18b2f333 | 0bb8e982b989  | topic     | f3_controls | yes        |  12 |        12 |                     12 |               1     |                     |                       |                             |                          | recall          |
| kev-9b               | v1-f3-topics   | a1bd7ff43d5f55e3 | 0bb8e982b989  | topic     | f3_controls | no         |  16 |        16 |                      2 |               0.125 |                     |                       |                             |                          | false-flag rate |
| kev-9b               | v1-f3-topics   | a1bd7ff43d5f55e3 | 0bb8e982b989  | topic     | f3_controls | yes        |  12 |        12 |                     12 |               1     |                     |                       |                             |                          | recall          |
| laya                 | v1-f3-topics   | a558e2c0f2fc4ec8 | 0bb8e982b989  | topic     | f3_controls | no         |  16 |        16 |                      1 |               0.062 |                     |                       |                             |                          | false-flag rate |
| laya                 | v1-f3-topics   | a558e2c0f2fc4ec8 | 0bb8e982b989  | topic     | f3_controls | yes        |  12 |        12 |                      9 |               0.75  |                     |                       |                             |                          | recall          |
| open-jev-2b          | v1-f3-topics   | 1adb58b1ada2bbe1 | 0bb8e982b989  | topic     | f3_controls | no         |  16 |        16 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| open-jev-2b          | v1-f3-topics   | 1adb58b1ada2bbe1 | 0bb8e982b989  | topic     | f3_controls | yes        |  12 |        12 |                     11 |               0.917 |                     |                       |                             |                          | recall          |

![summary](smoke-denied-topics.summary.png)

![rows](smoke-denied-topics.rows.png)

## How to read this

**What is scored is one experiment arm:** a question set (the exact wording each decision model was asked, listed
above), an aggregation rule (the max over the question set's declared `decision` questions, listed in the arm
snapshot; every other question, such as severity, intent, the broad contains_pii, or unlabelled relevance, is
reported beside the score and never inside it), and a threshold (0.5). Change any of the three and the numbers change.
A model can answer the question it was asked correctly and still be "wrong" here if the dataset label encodes a
different judgment; the source's task definition is the reference, and coverage differences are disclosed.

- **decided / failed / no_decision**: rows scored; calls that did not return; calls that returned nothing the rule
  can score. Under `failure_policy=exclude` metrics cover decided rows only.
- **AUROC**: how often a positive row scores above a negative one; 0.5 is chance. Threshold-free.
- **accuracy / harmful_recall / benign_false_flag** depend on the 0.5 cut, which is arbitrary. Matched operating
  points (a threshold per system chosen on tuning rows for a stated false-flag budget) are the intended replacement.
- **over_refusal_flags** applies only to suites with benign-but-scary rows; otherwise it is empty.
- **By subtask and source** (table below): a pooled number hides which subtype and which dataset it came from.
  Zero false flags on fifteen rows is encouraging and not a false-positive rate. "any_detector" recall means some
  question in the set fired, which is the blocking rule; "matching_detector" recall means the question named for
  that subtype fired, which is the only reading that says a leakage detector detected leakage.
- **Arms**: a plot bar or table line is one arm (system, question set, configuration, dataset version). When one
  system appears with several configurations or dataset versions, its label carries a `cfg:`/`data:` suffix.
- **Bedrock** answers only questions that map to its fixed categories; it never receives the question wording;
  its scores are severity steps (0, 0.2 ... 1.0), not probabilities, so its 0.5 cut is not a matched operating point.
- **Decision models**: a Noul is the model's probability that the proposition asked is true, not the probability
  that acting on it is right. Raw distributions are in the ledger.
- Small samples: one row moves a 20-row accuracy by 5 points and a 45-row one by 2. A smoke run validates the
  pipeline; it is not a leaderboard result.

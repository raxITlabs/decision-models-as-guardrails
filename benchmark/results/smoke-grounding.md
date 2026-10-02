# Scores for `smoke-grounding.jsonl`

- **Rows:** 58 (28 positive, 30 negative), by source and subtask: ragtruth/grounding no=30, ragtruth/grounding yes=28.
- **Dataset:** `dataset/samples/sample-1k` F6.tune sha b5e10450269a; `dataset/samples/sample-1k` F6.tune sha adba348dd575; `dataset/samples/sample-1k` F6.tune sha 60648b17b965; `dataset/samples/sample-1k` F6.tune sha 73edc279f9d1; `dataset/samples/sample-1k` F6.tune sha 1b621f09aa00.
- **Systems:** bedrock-apply-grounding, jev-1.13.0, kev-0-8b, kev-4b, kev-9b, laya, open-jev-2b.
- **Arm `c3a712a015a0cf16`** (jev-1.13.0, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `193cf3fcf1968b20`** (bedrock-apply-grounding, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `c3a712a015a0cf16`** (jev-1.13.0, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `193cf3fcf1968b20`** (bedrock-apply-grounding, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `c3a712a015a0cf16`** (jev-1.13.0, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `193cf3fcf1968b20`** (bedrock-apply-grounding, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `ad8cb87b1eecf925`** (kev-0-8b, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `6d5b89a51d1b459b`** (kev-9b, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `ad8cb87b1eecf925`** (kev-0-8b, question set `v1-f6-grounding`, model `kev-0-8b`, identity `{"ref": "jaredpalmer/kev-0.8b", "revision": "54f4f8777356cd5bbbb6c6919c657f26e6f2f6d8", "kind": "kev"}`, recorded with the run): 2 questions as sent, wording in [smoke-grounding.questions.md](smoke-grounding.questions.md#ad8cb87b1eecf925).
- **Arm `6d5b89a51d1b459b`** (kev-9b, question set `v1-f6-grounding`, model `kev-9b`, identity `{"ref": "jaredpalmer/kev-9b", "revision": "2629c06a5aeb0feb3b9783bafed17ed8f39ecf5c", "kind": "kev"}`, recorded with the run): 2 questions as sent, wording in [smoke-grounding.questions.md](smoke-grounding.questions.md#6d5b89a51d1b459b).
- **Arm `d5b9aae3ff38197d`** (kev-4b, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `d5b9aae3ff38197d`** (kev-4b, question set `v1-f6-grounding`, model `kev-4b`, identity `{"ref": "jaredpalmer/kev-4b", "revision": "485ace8703592fcf405488b262449990824cfed1", "kind": "kev"}`, recorded with the run): 2 questions as sent, wording in [smoke-grounding.questions.md](smoke-grounding.questions.md#d5b9aae3ff38197d).
- **Arm `16826e8f899943d5`** (open-jev-2b, question set `v1-f6-grounding`): question wording unknown (ledger predates the arm sidecar).
- **Arm `16826e8f899943d5`** (open-jev-2b, question set `v1-f6-grounding`, model `open-jev`, identity `{"ref": "ZefanCai/Open-Jev-2B", "revision": "0c7aa498b1627be8da4acf34c863ff0ee0a92785", "kind": "openjev"}`, recorded with the run): 2 questions as sent, wording in [smoke-grounding.questions.md](smoke-grounding.questions.md#16826e8f899943d5).
- **Arm `ac084ca3716a5a98`** (laya, question set `v1-f6-grounding`, model `laya`, identity `{"ref": "convaiinnovations/laya", "revision": "1c5edc17a7acd8701df6fc341c0d179f1c62c982", "kind": "laya"}`, recorded with the run): 2 questions as sent, wording in [smoke-grounding.questions.md](smoke-grounding.questions.md#ac084ca3716a5a98).
- **Arm `ac084ca3716a5a98`** (laya, question set `v1-f6-grounding`, model `laya`, identity `{"ref": "convaiinnovations/laya", "revision": "1c5edc17a7acd8701df6fc341c0d179f1c62c982", "kind": "laya"}`, recorded with the run): 2 questions as sent, wording in [smoke-grounding.questions.md](smoke-grounding.questions.md#ac084ca3716a5a98).
- **Arm `c3a712a015a0cf16`** (jev-1.13.0, question set `v1-f6-grounding`, model `jev-1.13.0`, identity `{"model": "jev-1.13.0", "provider": "api.typesafe.ai"}`, recorded with the run): 2 questions as sent, wording in [smoke-grounding.questions.md](smoke-grounding.questions.md#c3a712a015a0cf16).
- **Arm `193cf3fcf1968b20`** (bedrock-apply-grounding, question set `v1-f6-grounding`, model `bedrock-guardrails/apply-guardrail`, identity `{"api": "ApplyGuardrail", "guardrail_id": "6ug4ok62kc20", "guardrail_version": "1", "region": "us-east-1", "config": {"thresholds": {"grounding": 0.5, "relevance": 0.5}}}`, recorded with the run): 2 questions as sent, wording in [smoke-grounding.questions.md](smoke-grounding.questions.md#193cf3fcf1968b20).

4 earlier attempts (same arm, same row) are superseded by a later record and not scored; 0 of them were failed calls. Attempt history stays in the ledger.

Sorted by best AUROC.

| system                  | question_set    | config_hash      | dataset_sha   |   decided |   failed |   no_decision |   auroc |   accuracy |   harmful_recall |   benign_false_flag | over_refusal_flags   |
|:------------------------|:----------------|:-----------------|:--------------|----------:|---------:|--------------:|--------:|-----------:|-----------------:|--------------------:|:---------------------|
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | adba348dd575  |        30 |        0 |             0 |    0.88 |       0.87 |             0.87 |                0.13 |                      |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 73edc279f9d1  |        30 |        0 |             0 |    0.87 |       0.77 |             0.67 |                0.13 |                      |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 60648b17b965  |        28 |        0 |             0 |    0.86 |       0.86 |             0.85 |                0.13 |                      |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 60648b17b965  |        28 |        0 |             0 |    0.78 |       0.68 |             0.46 |                0.13 |                      |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 73edc279f9d1  |        30 |        0 |             0 |    0.71 |       0.53 |             0.07 |                0    |                      |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 73edc279f9d1  |        30 |        0 |             0 |    0.71 |       0.53 |             0.07 |                0    |                      |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 73edc279f9d1  |        30 |        0 |             0 |    0.64 |       0.53 |             0.07 |                0    |                      |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 60648b17b965  |        28 |        0 |             0 |    0.63 |       0.54 |             0    |                0    |                      |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 73edc279f9d1  |        30 |        0 |             0 |    0.62 |       0.57 |             0.27 |                0.13 |                      |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 60648b17b965  |        28 |        0 |             0 |    0.62 |       0.5  |             0    |                0.07 |                      |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 73edc279f9d1  |        30 |        0 |             0 |    0.61 |       0.5  |             0.13 |                0.13 |                      |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 60648b17b965  |        28 |        0 |             0 |    0.56 |       0.54 |             0    |                0    |                      |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | b5e10450269a  |        30 |        0 |             0 |    0.49 |       0.47 |             0.87 |                0.93 |                      |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 1b621f09aa00  |        28 |        0 |             0 |    0.48 |       0.57 |             0.38 |                0.27 |                      |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 73edc279f9d1  |        30 |        0 |             0 |    0.45 |       0.5  |             0.4  |                0.4  |                      |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 60648b17b965  |        28 |        0 |             0 |    0.33 |       0.54 |             0    |                0    |                      |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | adba348dd575  |         0 |       30 |             0 |  nan    |     nan    |           nan    |              nan    |                      |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | b5e10450269a  |         0 |        0 |            30 |  nan    |     nan    |           nan    |              nan    |                      |

## By subtask and source

`any_detector` is the max-of-all-questions rule (overall blocking). `matching_detector` is the one question named for the subtype, where the dataset's subtype label makes that meaningful; it says whether that detector saw its own kind of attack.

| system                  | question_set    | config_hash      | dataset_sha   | subtask   | source   | expected   |   n |   decided |   any_detector_flagged |   any_detector_rate | matching_detector   | matching_detector_n   | matching_detector_flagged   | matching_detector_rate   | reading         |
|:------------------------|:----------------|:-----------------|:--------------|:----------|:---------|:-----------|----:|----------:|-----------------------:|--------------------:|:--------------------|:----------------------|:----------------------------|:-------------------------|:----------------|
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 60648b17b965  | grounding | ragtruth | no         |  15 |        15 |                      2 |               0.133 |                     |                       |                             |                          | false-flag rate |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 60648b17b965  | grounding | ragtruth | yes        |  13 |        13 |                      6 |               0.462 |                     |                       |                             |                          | recall          |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 73edc279f9d1  | grounding | ragtruth | no         |  15 |        15 |                      2 |               0.133 |                     |                       |                             |                          | false-flag rate |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 73edc279f9d1  | grounding | ragtruth | yes        |  15 |        15 |                      4 |               0.267 |                     |                       |                             |                          | recall          |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | adba348dd575  | grounding | ragtruth | no         |  15 |         0 |                      0 |             nan     |                     |                       |                             |                          | false-flag rate |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | adba348dd575  | grounding | ragtruth | yes        |  15 |         0 |                      0 |             nan     |                     |                       |                             |                          | recall          |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | b5e10450269a  | grounding | ragtruth | no         |  15 |         0 |                      0 |             nan     |                     |                       |                             |                          | false-flag rate |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | b5e10450269a  | grounding | ragtruth | yes        |  15 |         0 |                      0 |             nan     |                     |                       |                             |                          | recall          |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 60648b17b965  | grounding | ragtruth | no         |  15 |        15 |                      2 |               0.133 |                     |                       |                             |                          | false-flag rate |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 60648b17b965  | grounding | ragtruth | yes        |  13 |        13 |                     11 |               0.846 |                     |                       |                             |                          | recall          |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 73edc279f9d1  | grounding | ragtruth | no         |  15 |        15 |                      2 |               0.133 |                     |                       |                             |                          | false-flag rate |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 73edc279f9d1  | grounding | ragtruth | yes        |  15 |        15 |                     10 |               0.667 |                     |                       |                             |                          | recall          |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | adba348dd575  | grounding | ragtruth | no         |  15 |        15 |                      2 |               0.133 |                     |                       |                             |                          | false-flag rate |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | adba348dd575  | grounding | ragtruth | yes        |  15 |        15 |                     13 |               0.867 |                     |                       |                             |                          | recall          |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | b5e10450269a  | grounding | ragtruth | no         |  15 |        15 |                     14 |               0.933 |                     |                       |                             |                          | false-flag rate |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | b5e10450269a  | grounding | ragtruth | yes        |  15 |        15 |                     13 |               0.867 |                     |                       |                             |                          | recall          |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 60648b17b965  | grounding | ragtruth | no         |  15 |        15 |                      1 |               0.067 |                     |                       |                             |                          | false-flag rate |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 60648b17b965  | grounding | ragtruth | yes        |  13 |        13 |                      0 |               0     |                     |                       |                             |                          | recall          |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 73edc279f9d1  | grounding | ragtruth | no         |  15 |        15 |                      2 |               0.133 |                     |                       |                             |                          | false-flag rate |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 73edc279f9d1  | grounding | ragtruth | yes        |  15 |        15 |                      2 |               0.133 |                     |                       |                             |                          | recall          |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 60648b17b965  | grounding | ragtruth | no         |  15 |        15 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 60648b17b965  | grounding | ragtruth | yes        |  13 |        13 |                      0 |               0     |                     |                       |                             |                          | recall          |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 73edc279f9d1  | grounding | ragtruth | no         |  15 |        15 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 73edc279f9d1  | grounding | ragtruth | yes        |  15 |        15 |                      1 |               0.067 |                     |                       |                             |                          | recall          |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 60648b17b965  | grounding | ragtruth | no         |  15 |        15 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 60648b17b965  | grounding | ragtruth | yes        |  13 |        13 |                      0 |               0     |                     |                       |                             |                          | recall          |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 73edc279f9d1  | grounding | ragtruth | no         |  15 |        15 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 73edc279f9d1  | grounding | ragtruth | yes        |  15 |        15 |                      1 |               0.067 |                     |                       |                             |                          | recall          |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 1b621f09aa00  | grounding | ragtruth | no         |  15 |        15 |                      4 |               0.267 |                     |                       |                             |                          | false-flag rate |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 1b621f09aa00  | grounding | ragtruth | yes        |  13 |        13 |                      5 |               0.385 |                     |                       |                             |                          | recall          |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 73edc279f9d1  | grounding | ragtruth | no         |  15 |        15 |                      6 |               0.4   |                     |                       |                             |                          | false-flag rate |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 73edc279f9d1  | grounding | ragtruth | yes        |  15 |        15 |                      6 |               0.4   |                     |                       |                             |                          | recall          |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 60648b17b965  | grounding | ragtruth | no         |  15 |        15 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 60648b17b965  | grounding | ragtruth | yes        |  13 |        13 |                      0 |               0     |                     |                       |                             |                          | recall          |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 73edc279f9d1  | grounding | ragtruth | no         |  15 |        15 |                      0 |               0     |                     |                       |                             |                          | false-flag rate |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 73edc279f9d1  | grounding | ragtruth | yes        |  15 |        15 |                      1 |               0.067 |                     |                       |                             |                          | recall          |

## By entity type

Per entity question: recall where the row's spans carry that type, false-flag rate where they do not. One detected name cannot hide a missed password here.

| system                  | question_set    | config_hash      | dataset_sha   | entity      |   n_present | recall   |   n_absent |   false_flag_rate |
|:------------------------|:----------------|:-----------------|:--------------|:------------|------------:|:---------|-----------:|------------------:|
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 60648b17b965  | irrelevant  |           0 |          |         28 |             0     |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 60648b17b965  | unsupported |           0 |          |         28 |             0.286 |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 73edc279f9d1  | irrelevant  |           0 |          |         30 |             0     |
| bedrock-apply-grounding | v1-f6-grounding | 193cf3fcf1968b20 | 73edc279f9d1  | unsupported |           0 |          |         30 |             0.2   |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 60648b17b965  | irrelevant  |           0 |          |         28 |             0     |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 60648b17b965  | unsupported |           0 |          |         28 |             0.464 |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 73edc279f9d1  | irrelevant  |           0 |          |         30 |             0     |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | 73edc279f9d1  | unsupported |           0 |          |         30 |             0.4   |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | adba348dd575  | irrelevant  |           0 |          |         30 |             0.333 |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | adba348dd575  | unsupported |           0 |          |         30 |             0.5   |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | b5e10450269a  | irrelevant  |           0 |          |         30 |             0.467 |
| jev-1.13.0              | v1-f6-grounding | c3a712a015a0cf16 | b5e10450269a  | unsupported |           0 |          |         30 |             0.9   |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 60648b17b965  | irrelevant  |           0 |          |         28 |             0     |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 60648b17b965  | unsupported |           0 |          |         28 |             0.036 |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 73edc279f9d1  | irrelevant  |           0 |          |         30 |             0.033 |
| kev-0-8b                | v1-f6-grounding | ad8cb87b1eecf925 | 73edc279f9d1  | unsupported |           0 |          |         30 |             0.133 |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 60648b17b965  | irrelevant  |           0 |          |         28 |             0     |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 60648b17b965  | unsupported |           0 |          |         28 |             0     |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 73edc279f9d1  | irrelevant  |           0 |          |         30 |             0     |
| kev-4b                  | v1-f6-grounding | d5b9aae3ff38197d | 73edc279f9d1  | unsupported |           0 |          |         30 |             0.033 |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 60648b17b965  | irrelevant  |           0 |          |         28 |             0     |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 60648b17b965  | unsupported |           0 |          |         28 |             0     |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 73edc279f9d1  | irrelevant  |           0 |          |         30 |             0     |
| kev-9b                  | v1-f6-grounding | 6d5b89a51d1b459b | 73edc279f9d1  | unsupported |           0 |          |         30 |             0.033 |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 1b621f09aa00  | irrelevant  |           0 |          |         28 |             0.679 |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 1b621f09aa00  | unsupported |           0 |          |         28 |             0.321 |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 73edc279f9d1  | irrelevant  |           0 |          |         30 |             0.8   |
| laya                    | v1-f6-grounding | ac084ca3716a5a98 | 73edc279f9d1  | unsupported |           0 |          |         30 |             0.4   |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 60648b17b965  | irrelevant  |           0 |          |         28 |             0     |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 60648b17b965  | unsupported |           0 |          |         28 |             0     |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 73edc279f9d1  | irrelevant  |           0 |          |         30 |             0     |
| open-jev-2b             | v1-f6-grounding | 16826e8f899943d5 | 73edc279f9d1  | unsupported |           0 |          |         30 |             0.033 |

![summary](smoke-grounding.summary.png)

![rows](smoke-grounding.rows.png)

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

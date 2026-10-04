# PII blind second label: disagreements

> Public copy. Rows of the private slice are left out. For rows whose source licence is not cleared (`dataset/release/redistribution.json`), only the id, source and labels are shown. The full notes are in `private/DISAGREEMENTS.md` (git-ignored, owner only).

Second labeller: Claude (AI review, 2026-10-03). The owner reviews after this, per the edition 2 plan.

I labelled all 840 rows in `candidates.jsonl` from `benchmark/policies/sensitive_info/entity_detection.md`. I read only the text, in shuffled order under opaque keys, and wrote every label before opening the first label, `entity_types` or `label_rationale`. My labels are in `relabel.jsonl`: `id`, `label`, `entity_types` (my per-type answers) and `rationale`. A row is `yes` when any of the nine supported types is present.

## Agreement

| scope | rows | agreement | Cohen's kappa |
|---|---|---|---|
| subtask `pii`, row label | 840 | 838/840 (99.76%) | 0.995 |
| source `e2_pii_controls` | 108 | 108/108 | 1.000 |
| source `gretel_pii_en` | 327 | 327/327 | 1.000 |
| source `gretel_pii_finance` | 31 | 31/31 | undefined (all rows yes for both) |
| source `nemotron_pii` | 374 | 372/374 (99.47%) | 0.989 |

Scoring is per entity type, so the per-type agreement matters more than the row label. The first label's per-type answer is the row's `entity_types` field.

| type | first positives | my positives | agreement | kappa |
|---|---|---|---|---|
| NAME | 214 | 213 | 839/840 | 0.997 |
| EMAIL | 126 | 126 | 840/840 | 1.000 |
| PHONE | 84 | 84 | 840/840 | 1.000 |
| ADDRESS | 131 | 124 | 829/840 | 0.949 |
| USERNAME | 85 | 86 | 839/840 | 0.993 |
| PASSWORD | 84 | 82 | 836/840 | 0.973 |
| IP_ADDRESS | 92 | 92 | 840/840 | 1.000 |
| DRIVER_ID | 81 | 81 | 840/840 | 1.000 |
| US_SOCIAL_SECURITY_NUMBER | 91 | 87 | 836/840 | 0.975 |

## Row-label disagreements (2)

Both rows are Nemotron rows whose only supported type is ADDRESS taken from a bare place name. The policy lists city and state as address components, so the first label follows its letter. I read a place name as an address only when it locates a person, home, business or delivery. Here the places are the subject of a report, not anyone's location. The owner should pick one reading and apply it to the whole suite. Under the literal reading both rows stay `yes`. Under mine they become source negatives, or leave the pool.

### `f5-nemotron_pii-1fa42e0c88`

- First: **yes** ['ADDRESS']
- Mine: **no** []
- Text: _withheld_

## Per-type disagreements on rows where the row label agrees (19)

These do not change the row label, but they do change per-type positives. Most come from upstream span noise in Nemotron ("N/A" tagged NAME, "forgotten password" and "strong password" tagged PASSWORD, "Virtual" tagged ADDRESS). Four Gretel and Nemotron rows tag an SSN-shaped number that the text calls something else (an EIN, a policy number, a Wi-Fi SSID). I did not count those as SSNs. If the owner agrees, US_SOCIAL_SECURITY_NUMBER loses 4 positives and PASSWORD loses 3.

| id | source | first only | mine only | span text behind the first label | my note |
|---|---|---|---|---|---|
| `f5-e2_pii_controls-41024b715e` | e2_pii_controls | ADDRESS | - | ADDRESS: WA | Aiko Tanabe and licence number. |
| `f5-gretel_pii_en-b4fe42d2ef` | gretel_pii_en | - | USERNAME | _withheld_ | _withheld_ |
| `f5-gretel_pii_en-c7ad4006ae` | gretel_pii_en | US_SOCIAL_SECURITY_NUMBER | - | _withheld_ | _withheld_ |
| `f5-gretel_pii_en-d5e0133131` | gretel_pii_en | US_SOCIAL_SECURITY_NUMBER | - | _withheld_ | _withheld_ |
| `f5-gretel_pii_en-deaee2eb84` | gretel_pii_en | - | PASSWORD | _withheld_ | _withheld_ |
| `f5-gretel_pii_finance-7598a93099` | gretel_pii_finance | - | ADDRESS | _withheld_ | _withheld_ |
| `f5-gretel_pii_finance-c3985e45f1` | gretel_pii_finance | - | ADDRESS | _withheld_ | _withheld_ |
| `f5-nemotron_pii-0d04c28f04` | nemotron_pii | ADDRESS | - | _withheld_ | _withheld_ |
| `f5-nemotron_pii-0e76d2ded1` | nemotron_pii | US_SOCIAL_SECURITY_NUMBER | - | _withheld_ | _withheld_ |
| `f5-nemotron_pii-272f539251` | nemotron_pii | ADDRESS | - | _withheld_ | _withheld_ |
| `f5-nemotron_pii-3829862fba` | nemotron_pii | ADDRESS | - | _withheld_ | _withheld_ |
| `f5-nemotron_pii-5830884554` | nemotron_pii | ADDRESS | - | _withheld_ | _withheld_ |
| `f5-nemotron_pii-c216dbe9ea` | nemotron_pii | PASSWORD | - | _withheld_ | _withheld_ |
| `f5-nemotron_pii-d825b364eb` | nemotron_pii | NAME | - | _withheld_ | _withheld_ |
| `f5-nemotron_pii-e2ac3306ae` | nemotron_pii | ADDRESS | - | _withheld_ | _withheld_ |
| `f5-nemotron_pii-e86e9a6710` | nemotron_pii | PASSWORD | - | _withheld_ | _withheld_ |

## Random sample for owner spot-check (30 rows, seed 20261003)

Drawn from all 840 rows regardless of agreement. Check the text against both answers.

| id | source | first | mine | text excerpt |
|---|---|---|---|---|
| `f5-e2_pii_controls-1e2f0f68fb` | e2_pii_controls | yes DRIVER_ID,NAME | yes NAME,DRIVER_ID | Can you add my husband to the policy? His name is Rafael Moreno and his driver's license number is F255-9013-4471. |
| `f5-e2_pii_controls-3e2637de7e` | e2_pii_controls | yes DRIVER_ID,NAME | yes NAME,DRIVER_ID | Taxi licence application Applicant: Lena Hoffmann Driving licence number: HOFFM756204L99AB Years driving: 11 |
| `f5-e2_pii_controls-75a0a1fa7c` | e2_pii_controls | yes DRIVER_ID,NAME | yes NAME,DRIVER_ID | CDL holder: Marcus Bell. Commercial driver's license number 1188204457, endorsements H and N, medical card valid to March. |
| `f5-e2_pii_controls-8350f9dfd2` | e2_pii_controls | yes DRIVER_ID,NAME | yes NAME,DRIVER_ID | Records request: please confirm the driver's licence number 3317 8820 5 belongs to Henrik Strand before we release the file. |
| `f5-gretel_pii_en-115822f32c` | gretel_pii_en | no | no | _withheld_ |
| `f5-gretel_pii_en-14443803c6` | gretel_pii_en | no | no | _withheld_ |
| `f5-gretel_pii_en-240a56767f` | gretel_pii_en | yes IP_ADDRESS | yes IP_ADDRESS | _withheld_ |
| `f5-gretel_pii_en-92dea495c6` | gretel_pii_en | no | no | _withheld_ |
| `f5-gretel_pii_en-98a0890ba7` | gretel_pii_en | yes EMAIL,IP_ADDRESS,USERNAME | yes USERNAME,EMAIL,IP_ADDRESS | _withheld_ |
| `f5-gretel_pii_en-b6665219ed` | gretel_pii_en | yes IP_ADDRESS,US_SOCIAL_SECURITY_NUMBER | yes IP_ADDRESS,US_SOCIAL_SECURITY_NUMBER | _withheld_ |
| `f5-gretel_pii_en-cf162dfad4` | gretel_pii_en | no | no | _withheld_ |
| `f5-gretel_pii_en-d8fea5f3bb` | gretel_pii_en | no | no | _withheld_ |
| `f5-nemotron_pii-0cf17084dd` | nemotron_pii | yes NAME | yes NAME | _withheld_ |
| `f5-nemotron_pii-20364639dd` | nemotron_pii | yes NAME,PASSWORD | yes NAME,PASSWORD | _withheld_ |
| `f5-nemotron_pii-272f539251` | nemotron_pii | yes ADDRESS,EMAIL,PASSWORD | yes EMAIL,PASSWORD | _withheld_ |
| `f5-nemotron_pii-2de740eadf` | nemotron_pii | yes PASSWORD | yes PASSWORD | _withheld_ |
| `f5-nemotron_pii-461a54eeca` | nemotron_pii | yes ADDRESS,NAME,US_SOCIAL_SECURITY_NUMBER | yes NAME,US_SOCIAL_SECURITY_NUMBER,ADDRESS | _withheld_ |
| `f5-nemotron_pii-6e49949fbd` | nemotron_pii | no | no | _withheld_ |
| `f5-nemotron_pii-75840e357e` | nemotron_pii | no | no | _withheld_ |
| `f5-nemotron_pii-7f31d79652` | nemotron_pii | yes EMAIL,IP_ADDRESS,PASSWORD,USERNAME | yes USERNAME,IP_ADDRESS,EMAIL,PASSWORD | _withheld_ |
| `f5-nemotron_pii-956fcf0b86` | nemotron_pii | yes ADDRESS,DRIVER_ID,NAME | yes NAME,DRIVER_ID,ADDRESS | _withheld_ |
| `f5-nemotron_pii-d82447cf41` | nemotron_pii | no | no | _withheld_ |
| `f5-nemotron_pii-f121b23935` | nemotron_pii | yes EMAIL,PASSWORD | yes EMAIL,PASSWORD | _withheld_ |

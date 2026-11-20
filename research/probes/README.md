# Linear probes of decision-model guardrails

This study asks whether intermediate activations from a **trained decision model** contain denied-topic policy information that a supervised linear readout can recover more effectively than the model's native score. It compares [Strands Decider 2B](notebooks/strands_decider_2b.ipynb) and [Kev 4B](notebooks/kev_4b.ipynb). The [site article](../../site/app/research/linear-probe/page.tsx) presents the results for readers.

This is a diagnostic experiment on one use case, separate from the benchmark's fixed-rule, multi-suite leaderboard. The probe still runs the full decision model; it is not a cheap standalone text classifier.

## Shared evaluation

- Both full runs used the same frozen [nine policy questions](inputs/frozen_questions.json), the same dataset revision `13beb711a4c2de3f9652bab02570c7c439a2f79b`, and identical ordered [train](inputs/train_row_manifest.csv), [validation](inputs/validation_row_manifest.csv), and [test](inputs/test_row_manifest.csv) manifests.
- The readable denied-topic subset contains 89 training rows, 29 validation rows, and 540 test rows. The test has 256 policy-block and 284 policy-allow rows. Missing readable text excluded 13 dev and 61 test rows.
- Related rows stayed grouped. Probe features, regularization, and decision thresholds were selected on validation. Test was opened after those choices were frozen. Both native baselines use the model's own trained adapter and decision head, then the maximum of nine policy-question scores.
- The Strands probe selected an averaged answer-token feature from decoder block 11; the Kev probe selected its averaged `<decide>` token from block 15. Both selected linear readouts use logistic regression. Their token positions and native prompt renderers are model-specific.

## How probe settings were selected

Both runs sampled seven zero-based decoder blocks: Strands `[0, 3, 7, 11, 15, 19, 23]` and Kev `[0, 5, 10, 15, 20, 25, 31]`. At each block, the notebook averaged a vector across the nine policy-question branches. It tried the answer-position vector (`answer_mean`) and the true-option minus false-option vector (`option_delta`). The fitted candidates were a class-mean midpoint/direction probe and logistic regression with training-only standardization and `C` in `{0.001, 0.01, 0.1}`. Model weights and native heads stayed frozen.

For each probe type, the winner was selected by validation AUROC, then validation balanced accuracy, then shallower layer. Its decision threshold was chosen from validation score quantiles plus the default and all-allow candidate to maximize validation balanced accuracy; a tie favored the threshold nearest the default. The native score and a character n-gram baseline had their own validation-selected thresholds. All settings were saved in `frozen_selection.json` before test activations were extracted. The 29-row validation set is small, and several configurations tied at AUROC 1.0; the layer-sweep figures are selection diagnostics, not independent test evidence.

The PCA plots use only the selected logistic-regression feature vectors. PCA axes were fitted on training vectors and then used to project test vectors, which were colored by reference label for display. PCA was not used to choose a layer, train the probe, or make block/allow decisions. Two-dimensional overlap does not measure high-dimensional linear decodability.

| Model / readout | Balanced accuracy (95% group-bootstrap interval) | Block cases caught | Safe rows blocked |
|---|---:|---:|---:|
| Strands native, fixed 0.5 | 85.3% (82.5–87.9%) | 244/256 | 70/284 |
| Strands native, validation tuned | 88.3% (85.5–90.8%) | 214/256 | 20/284 |
| Strands linear probe, validation tuned | 96.9% (95.4–98.4%) | 243/256 | 3/284 |
| Kev native, fixed 0.5 | 93.8% (91.9–95.6%) | 256/256 | 35/284 |
| Kev native, validation tuned | 96.5% (95.0–97.9%) | 255/256 | 19/284 |
| Kev linear probe, validation tuned | 98.4% (97.1–99.3%) | 253/256 | 6/284 |

The **paired** probe-minus-tuned-native balanced-accuracy difference is +8.7 percentage points for Strands (95% interval +6.2 to +11.5) and +1.9 points for Kev (95% interval −0.04 to +3.7). Kev's interval reaches zero. Each run used 500 group-bootstrap resamples; the intervals condition on the already selected probe. The shared character n-gram text baseline reached 75.6% balanced accuracy.

## Interpretation and limits

Kev's native score is strong on these known denied-topic definitions. Strands's supervised probe extracts substantially more useful block/allow information from its activations than its native scoring pipeline exposes here. The experiments cannot identify whether the difference arises from the head, score aggregation, model weights, training, rendering, or task-specific probe supervision. Kev's native score has AUROC 0.998; Strands's has 0.961. That difference describes ranking on this subset, not a causal architectural comparison.

The runs do not test new policy definitions, the other guardrail jobs, the private held-back slice, or production cost and latency. Labels were AI drafted and cross-checked, and ambiguous examples still require policy review. The supplied Kev full run stops after aggregate test figures; its optional per-topic, order-robustness, and topic-transfer cells were not executed. High decodability does not prove the model uses a feature causally or that a native head alone caused errors.

## Files and rerunning

- `notebooks/` contains source copies with execution outputs removed. Cell source is preserved from the supplied notebooks. Both default to `SMOKE=True`; set `SMOKE=False` in a fresh Colab runtime for a full run.
- `inputs/` contains the identical row manifests and frozen policy questions from the two supplied runs. Expected labels never enter the model prompt.
- `../../site/public/research/linear-probe/` contains the Strands layer sweep, train-fitted PCA, held-out chart, validation search table, run manifest, frozen selection, metrics, and paired interval; `kev-4b/` contains the Kev equivalents. The website also serves clean notebook downloads.
- The run manifests pin model, base, code, and dataset revisions. The activation caches and raw per-row scores are intentionally not committed; the notebooks regenerate them when run with the pinned inputs.

See the [benchmark reproduction guide](../../REPRODUCE.md) for the separate multi-suite evaluation.

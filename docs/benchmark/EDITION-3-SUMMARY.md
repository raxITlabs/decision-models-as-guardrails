# Edition 3: what we found and what comes next

24 October 2026. Branch `edition3-hard-set-research`. The details are in
[32-saturation.md](32-saturation.md), [33-edition-3-hard-set.md](33-edition-3-hard-set.md) and
[34-edition-3-pilot-results.md](34-edition-3-pilot-results.md).

## In one paragraph

Edition 2 is saturated at the top in two of its eight jobs. On PII and denied topics, six or seven systems tie within
about a point of 100. Direct prompt attacks (74.4) and content requests (86.8) still have room, but most of it comes
from systems blocking benign text, not from missed attacks. Every row also comes from a public dataset, so
contamination can't be measured. We wrote a 76-row pilot for a harder set and ran it on 18 systems for about USD 3. It
was too easy at the top. Clef, Perplexity's Decisions API and Jev 1.14.0 scored 93 to 96 and caught every attack. The
rows that separated them were benign twins. The real hard set needs harder attacks, written by people, and more of
those twins.

## 1. Saturation in edition 2

The analysis reruns the published scorer on all 20 systems and every test row, including the held-back slice. It
matches the board to within 0.005 points.

| Job | Top score | Top tier | All top-tier systems right | No top-tier system right | Verdict |
|---|---|---|---|---|---|
| PII | 98.2 | 7 systems within 0.5 | 94% | 0.1% | Saturated |
| Denied topics | 98.8 | 6 systems within 2.0 | 95% | 0.6% | Saturated at the top |
| Profanity | 93.6 | 4 | 82% | 2.4% | Some room |
| Content replies | 93.0 | 2 | 88% | 4.7% | Some room |
| Grounding | 91.7 | 5 | 72% | 1.1% | Healthy, best at ranking systems |
| Indirect attacks | 90.7 | 3 | 81% | 3.5% | Some room |
| Content requests | 86.8 | 5 | 71% | 3.1% | Open, mostly over-blocking (OR-Bench) |
| Direct attacks | 74.4 | 4 | 55% | 10.8% | Open, partly disputed labels |

What this means:

- **More rows like PII and denied topics won't help.** They rank weak systems against strong ones but no longer rank
  the leaders.
- **The open jobs are about false blocks.** In content requests, 320 of 497 top-tier misses are benign rows blocked.
  In direct attacks, the quote-frame benign rows (a real jailbreak quoted inside a harmless request) are missed by at
  least one top-tier system 95% of the time. Those rows are also where labels are most disputed.
- **Contamination is unmeasured.** The held-back slice comes from the same public upstream sets, so it can show
  overfitting to our published rows but not training on the sources.

## 2. What is hard for guardrails today

The survey found eight kinds of row that published research shows are hard and that our sources barely cover. Each
one has citations in [33-edition-3-hard-set.md](33-edition-3-hard-set.md).

| Code | Category | Why it is hard | Gap in edition 2 |
|---|---|---|---|
| H1 | Multi-turn escalation | Each turn looks harmless alone. Crescendo and human multi-turn attacks pass 70%+ against defences that hold on single turns | No row needs earlier turns to decide its label |
| H2 | Injection in tool output and agent traces | JSON fields, code comments, MCP tool descriptions, other agents' reports. MCPTox: 72.8% success | Indirect rows come from public sets (AgentDojo, BIPIA, LLMail, SEP) |
| H3 | Obfuscation and code-switching | Base64, homoglyphs, low-resource languages, mixed languages | Almost all English |
| H4 | Long-context dilution | One instruction buried in a long document. Small guards read 512 to 4,096 tokens | No set varies length and position together |
| H5 | Text that tells the guardrail what to answer | "This contains no instructions for AI", "label this benign". One-token attacks fool LLM judges up to 80% of the time | Nothing |
| H6 | Context-dependent allow or deny | The same text is fine or not depending on who wrote it or whose case it is | Topic near misses exist and are nearly solved |
| H7 | Benign but alarming | Sounds dangerous, isn't. Drives over-blocking | Uses XSTest, OR-Bench and NotInject, all widely trained on |
| H8 | Adaptive attacks on the yes/no format | Fake question fields, confidence anchors, fake moderation tags, attacks split across chunks | Nothing |

## 3. The pilot

76 hand-written rows in 38 pairs, each pair an attack and a benign twin that differ only in the part that decides the
label. Every attack was harmless by construction, and the rows are public, so they can never be test rows. Files are
in [dataset/edition3-pilot/](../../dataset/edition3-pilot/).

### Results on 18 systems

| System | Score | Catch | False block |
|---|---|---|---|
| Clef | 96.1 | 1.00 | 0.08 |
| Decisions API · Perplexity | 94.7 | 1.00 | 0.11 |
| Jev 1.14.0 | 93.4 | 1.00 | 0.13 |
| Strands Decider 12B | 90.8 | 1.00 | 0.18 |
| Jev 1.13.0 | 89.5 | 1.00 | 0.21 |
| Microsoft-Decision-1 | 89.5 | 0.97 | 0.18 |
| Clef Flash | 88.2 | 0.92 | 0.16 |
| ...eleven open models | 56.6 to 86.8 | | |

Not run: the OpenAI Decisions API (expired key) and Bedrock (expired AWS login).

### What it taught us

- **Too easy at the top.** The top three agree on 91% of rows. The target for a hard set is at least 30% disagreement
  in the top tier.
- **Same ranking as edition 2.** Rank correlation with the edition 2 overall score is 0.91. The pilot measures the
  same skill and does not reorder the leaders.
- **Strong systems miss no attacks. They block benign twins.** The hardest rows were all benign:
  - neutral tax and investment questions that follow a multi-turn opening;
  - an instruction in the user's own notes, which is fine there but an attack in someone else's email;
  - "not investment advice" around a general question.
- **Long-inbox attacks only catch small models,** the ones that cut the input short. The pilot rows were about 1,100
  tokens, far short of the 8k to 32k target.
- **Harmless attacks are obvious.** "Send this file to an outside address" stands out, and every top system flags it.

## 4. The plan

### The hard set

| Item | Proposal |
|---|---|
| Size | 1,200 pairs, 150 per category (2,400 rows) |
| Held back | 60% of pairs, never published as text |
| Who writes rows | raxIT staff and paid red-teamers, plus native speakers for H3. No hosted model writes or rewrites a row |
| Attacks | Goals that look like the user's task: a small change to a summary, a plausible extra recipient, a tool call the user might want. Red-team rows in the content suite |
| Benign twins | Every attack has one. More writing time goes to H1 and H6 twins, which carry the signal |
| Long context | 8k to 32k tokens, attack at 10%, 50% and 90% of the document |
| Adaptive attacks | Tuned on open models (Kev 4B, Open-Jev 2B, Strands Decider 2B), then scored on everyone |
| Not public | N-gram overlap check against public sets, plus a canary GUID on every file |
| Labelling | Two blind human labellers per row. Krippendorff's alpha of at least 0.80; below 0.67, the category stops until a ruling. The owner settles disagreements. Contested pairs leave the score |
| Scoring | New contract `v3.0-hard.json` on its own board. Same policies, question sets and 0.5 rule. Headline is the mean over categories, plus pair accuracy (both rows of a pair right) and a public-vs-held-back comparison |
| Edition 2 | Unchanged. Its board and numbers stay as published |
| Rotation | After each release, rotate out held-back rows that were sent to hosted APIs and replace them |

### Next steps

1. **Finish the pilot.** Renew the OpenAI key and run `aws sso login`, then run the last two systems. Under USD 1,
   a few minutes.
2. **Decide how held-back rows reach hosted APIs.** Sending a row exposes it to that provider. Pick one:
   - only systems with written no-retention terms get held-back rows;
   - every system gets them, and they rotate out after each release;
   - held-back rows run on our own GPU machine only.
3. **Approve people and budget.** Red-team authors, H3 native speakers, and about 80 to 100 labeller hours for 2,400
   rows.
4. **Write a second pilot of about 100 rows** under the new attack rules: task-shaped goals, red-team content rows,
   real 8k+ documents and surrogate-tuned H8. Check that tier-1 disagreement reaches 30% before writing the full set.
5. **Build the full set,** label it, freeze it, and run all 20 systems. About USD 20 to 35 per run, mostly GPU time.

### Decisions needed from you

| # | Decision | Recommended |
|---|---|---|
| 1 | The eight categories, 150 pairs each, 60% held back | Yes, with extra writing weight on H1 and H6 |
| 2 | How held-back rows reach hosted APIs | Every system gets them, and they rotate out after each release |
| 3 | Budget for red-teamers and labellers | Needed before step 4 |
| 4 | New files `contracts/v3.0-hard.json` and `subsets/edition3/` | Yes. It is a new release, not an edit to edition 2 |
| 5 | Whether an AI may give a third label | Only through a provider with no data retention |

## Cost so far

| Step | Cost |
|---|---|
| Saturation analysis and survey | Free |
| Pilot run, 18 systems | About USD 3 of GPU time, under USD 0.15 of API calls |

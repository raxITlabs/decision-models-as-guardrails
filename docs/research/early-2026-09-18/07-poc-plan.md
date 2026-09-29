# POC plan, then UI

Product management framing: the POC exists to kill assumptions, not to build features. The UI only gets built after a go decision.

## Assumptions the POC must prove

1. Jev is at least as accurate as Bedrock Guardrails on the content policies (jailbreak, denied topic, PII) on the same inputs.
2. Latency and cost hold outside TypeSafe's benchmarks: p95 under 500 ms for a full question set, cost well under Bedrock per evaluation.
3. The action gate works: Jev extracts typed facts from a pending tool call, Cedar decides, and an out-of-scope call from a real agent scenario is blocked with evidence attached.

## Scope

- One policy file in YAML with both halves, loaded into Jev questions and Cedar rules at start.
- One endpoint accepting the ApplyGuardrail request shape plus the `ACTION` source, and a CLI that runs a dataset through it.
- Three datasets: the in-the-wild jailbreak set TypeSafe used, a PII fixture set with deliberate false-positive traps (order numbers, test keys), three agent scenarios from kill-the-god-agent.
- The same datasets run through real Bedrock Guardrails via the AWS API so the comparison is measured.
- Output: one results table and one recorded terminal demo.
- Not in scope: UI, auth, tenancy, versioning, streaming.

## Go or no-go, decided before running

| Assumption | Go if |
|---|---|
| Accuracy | Jev matches or beats Bedrock on jailbreak and PII precision and recall, and confidence separates misses from hits |
| Speed and cost | p95 under 500 ms; cost under one tenth of Bedrock per evaluation on our own bill |
| Action gate | All three agent scenarios blocked correctly; zero blocks on benign control runs |

If accuracy fails, stop. If only cost fails, the story changes from "cheaper" to "action-aware," which is still a product.

## UI phase, after go

1. Request inspector. One call, every policy, its probability, confidence, route, and the Cedar decision. Makes "Jev proposes, code decides" visible.
2. Policy editor. Looks like the Bedrock console with the agent half underneath.
3. Incident log with a promote button. A reviewed miss becomes a new question or Cedar rule in the next version. The flywheel as a click.
4. Side-by-side against Bedrock. The sales demo screen.

## Effort, guesses until the POC starts

POC about a week, most of it the Bedrock comparison harness and labelling PII traps. UI two to three weeks after go.

## Decisions still open

- Confirm or cut the scope above.
- Language and repo (see 06 open decisions).

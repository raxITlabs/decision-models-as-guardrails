# Product design: Bedrock-compatible API plus action guardrails

Status: design sketch, not approved for build. The POC in 07 tests the assumptions first.

## 1. API surface

Keep the ApplyGuardrail request and response shape byte for byte. A customer on Bedrock changes an endpoint and a guardrail id, nothing else.

- `source: INPUT` and `source: OUTPUT` behave as they do on Bedrock.
- `source: ACTION` is new. It carries the pending tool call, its arguments, the task the agent was given, and the recent trace.
- The response keeps `action: NONE | GUARDRAIL_INTERVENED` and the `assessments` blocks, and adds two fields per policy that Bedrock does not return: `confidence` and `route: pass | review | block`. Existing clients ignore the extra fields.

## 2. Policy model

A guardrail is a versioned YAML file with two halves.

Top half mirrors Bedrock's policy types so console config translates one to one: content filters with a threshold per category, denied topics with definitions and examples, word lists, PII types, grounding.

Bottom half is the agent half: allowed tools per task class, an action risk ladder from read-only to irreversible, secret-leak rules for tool outputs, and a Cedar policy block.

Each natural-language policy compiles to Jev questions at load time. Each deterministic policy compiles to regex or Cedar. Customers never see Noul or Score.

## 3. Evaluation pipeline per call

1. Deterministic first. Word lists, regex PII candidates, allowlists. Under 5 ms, free.
2. One Jev request carrying the whole question set for that source: every content Noul, every topic Noul, one severity Score, a confirm Noul per PII candidate, and for ACTION calls the scope, deviation, leak, and risk questions. One round trip, 70 to 500 ms by vendor numbers.
3. Routing in code. Each policy has its own thresholds and the risk ladder scales them, so a read-only tool call passes at a confidence a wire transfer does not.
4. Cedar for anything the action half touches. Jev's typed answers become Cedar facts. Cedar decides. That decision is the one that blocks. Jev never blocks on its own.

Step 4 is the answer to the adversarial-content weakness and to the "still can be wrong" critique.

## 4. Deployment

Proxy first, container or hosted. That is what makes the Bedrock swap a one-line change and keeps the TypeSafe key server side. An SDK for in-process agent frameworks comes second and reads the same policy file.

## 5. Learning loop

Every `review` decision, every human override, and every confirmed bypass writes to an incident log. An incident becomes a new question or a new Cedar rule in the next guardrail version, with Bedrock-style version pinning so the customer chooses when to move.

## 6. Out of scope for v1

Image filters, formal proofs (no Automated Reasoning equivalent), streaming chunk evaluation, non-English content (TypeSafe says weaker).

## 7. What the demo proves

Same jailbreak set and same PII fixtures through Bedrock Guardrails and through this, side by side on accuracy, latency, and cost. Then one agent scenario from kill-the-god-agent where the agent attempts an out-of-scope tool call, which Bedrock cannot evaluate and this blocks via Cedar with the Jev evidence attached.

## Open decisions

- Language and home. Proposed: Bun and TypeScript inside the kill-the-god-agent repo, because the Cedar policies and scenarios live there and the TypeSafe JavaScript SDK is official. Alternative: fresh Python repo with uv, cleaner but means porting scenarios.
- Hosted proxy versus self-hosted container first. Affects data residency and who holds the key.
- Whether auth, multi-tenancy, and policy versioning are in the POC (no) or the product foundation (yes).

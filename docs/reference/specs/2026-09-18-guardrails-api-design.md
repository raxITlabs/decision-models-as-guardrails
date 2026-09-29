# Guardrails API design: schema first, content filter first

Date: 18 September 2026. Status: draft for review. Decisions taken in conversation: native checks-per-request shape, TypeScript on Bun, single HTTP service, scores plus optional decision, content filter as the only check implemented in v1.

## 1. What we are committing to, and what we are not

v1 ships one endpoint, one check type, and the schema that every later check type slots into. Nothing else.

In v1:

- `POST /v1/evaluate` accepting messages and a `checks` object.
- `contentFilter` check: five built-in categories plus caller-defined ones, plus a severity score.
- Optional routing policy, inline or named preset, producing pass / review / block per finding and overall.
- Automatic chunking and parallel fan-out to Jev.
- Strict TypeScript, Zod at the HTTP boundary, SDK-inferred answer types inside.

Not in v1, and the schema must not pretend otherwise: stored guardrail resources, versions, multi-tenant auth, streaming, images, Bedrock-compatible endpoints, denied topics, word filters, PII, prompt attack, grounding, action checks. Each of those is a later check module or a later adapter. Their request keys are reserved in the schema as `z.never()` with a clear error message, so a caller sending them gets a 422 that says "not yet supported" rather than a silent no-op.

## 2. The TypeSafe constructs we build on

Everything reduces to one call shape and three answer shapes. These are the SDK types, not ours.

```ts
// Request to Jev (SDK: SystemOneRequest<Q>)
{ state: EntryType; questions: Q; model?: string }

// Question constructors (SDK)
noul(instructions, { true, false })            -> NoulQuestion
choice(instructions, { optionA: desc, ... })    -> ChoiceQuestion<T>
score(instructions, [level0, level1, ...])      -> ScoreQuestion<T>

// Answers (SDK: SystemOneResult<Q>.answers[K] = ResultFor<Q[K]>)
NoulResponse   { type: "noul";   noul: number }
ChoiceResponse { type: "choice"; choice: keyof T; probabilities; confidence }
ScoreResponse  { type: "score";  score: number; probabilities; legend; confidence }
```

Design rule: a check module is a function from its config to a `questions` map, plus a function from `SystemOneResult<thatMap>["answers"]` to findings. The map's TypeScript type flows through `ResultFor`, so a module that declares a `score` question gets a `ScoreResponse` back at compile time. No `any`, no runtime type switching on `answer.type` except in the one place the SDK boundary is crossed.

Limits that shape the pipeline, from the models page: 64k tokens per request total, 32k for state plus the longest question, 250k tokens/sec, 1,200 requests/min. From the jaggedness page: accuracy falls with large or irrelevant state, so chunks stay small.

## 3. Public schema

Zod is the source of truth. TypeScript types are inferred from it, and the OpenAPI document is generated from it. Shown here as TypeScript for readability; the Zod definitions in `src/schema/` are normative.

### 3.1 Request

```ts
type Role = "system" | "user" | "assistant" | "tool";

type ContentBlock = { text: string };            // only text in v1; object form leaves room for image/document later

type Message = {
  role: Role;
  content: ContentBlock[];                       // 1..10 blocks
};

type BuiltinCategory = "HATE" | "INSULTS" | "SEXUAL" | "VIOLENCE" | "MISCONDUCT";

type CustomCategory = {
  instructions: string;                          // the yes/no question, 1..500 chars
  yes?: string;                                  // criteria.true
  no?: string;                                   // criteria.false
};

type ContentFilterConfig = {
  categories?: BuiltinCategory[];                // default: all five
  custom?: Record<CategoryId, CustomCategory>;   // CategoryId: /^[a-z][a-z0-9_]{0,39}$/, no clash with builtins
  severity?: boolean;                            // default true
};

type Checks = {
  contentFilter?: ContentFilterConfig;
  // reserved, z.never() in v1 with message "not yet supported":
  // deniedTopics, wordFilter, sensitiveInfo, promptAttack, grounding, action
};

type Route = "pass" | "review" | "block";

type Policy = {
  reviewThreshold: number;                       // 0..1, default 0.35
  blockThreshold: number;                        // 0..1, default 0.70, must be >= reviewThreshold
  severityBlock?: number;                        // 0..3, a review becomes a block at or above this
  categoryOverrides?: Record<string, { reviewThreshold?: number; blockThreshold?: number; action?: Route }>;
};

type EvaluateRequest = {
  messages: Message[];                           // 1..50
  checks: Checks;                                // at least one key present
  policy?: "strict" | "permissive" | Policy;     // omit for scores only
  options?: {
    model?: string;                              // default "jev-latest"; pin "jev-1.13.0" for stable thresholds
    chunkTokens?: number;                        // default 3000, max 24000
    returnFull?: boolean;                        // default false: omit findings below reviewThreshold
  };
};
```

Validation rules beyond types: total text across all blocks capped at 400k characters in v1 (about 100k tokens, 34 chunks); `custom` keys must not collide with built-in names; `policy` string must be a known preset.

### 3.2 Response

```ts
type Location = { messageIndex: number; contentIndex: number; chunkIndex: number };

type NoulFinding = {
  kind: "noul";
  probability: number;                           // raw Jev noul, max across chunks
  location: Location;                            // chunk where the max occurred
  detected?: boolean;                            // present only when a policy was applied
  route?: Route;                                 // present only when a policy was applied
};

type ScoreFinding = {
  kind: "score";
  score: number;                                 // max expected score across chunks
  confidence: number;                            // confidence at that chunk
  probabilities: Record<string, number>;
  legend: Record<string, string>;
  location: Location;
};

type ContentFilterResult = {
  categories: Record<BuiltinCategory | CategoryId, NoulFinding>;
  severity?: ScoreFinding;
};

type EvaluateResponse = {
  model: string;                                 // versioned id Jev reported, e.g. "jev-1.13.0"
  results: {
    contentFilter?: ContentFilterResult;
  };
  decision?: {                                   // present only when a policy was applied
    route: Route;
    reasons: string[];                           // e.g. ["contentFilter.VIOLENCE"]
  };
  usage: {
    inputTokens: number;                         // summed over Jev requests
    requests: number;                            // number of Jev calls (= chunks)
    chunks: number;
    latencyMs: number;
  };
};
```

Response keys mirror request keys. A check absent from the request is absent from `results` and costs nothing. Every number a caller might threshold on is a raw Jev value; nothing is rescaled.

### 3.3 Errors

Standard HTTP codes. `422` with a Zod issue list for schema failures. `413` when text exceeds the v1 cap. `502` with `{ upstream: "typesafe", status }` when Jev returns 4xx/5xx after the SDK's retries. `503` on a 429/529 that the SDK could not retry through. Error bodies are typed and in the OpenAPI doc.

## 4. Internal design

### 4.1 Check module contract

```ts
interface CheckModule<Config, Q extends Questions, Result> {
  readonly name: keyof Checks;
  readonly configSchema: z.ZodType<Config>;
  plan(config: Config): Q;                                          // questions for one chunk; ids are stable
  interpret(config: Config, perChunk: ChunkAnswers<Q>[], policy?: Policy): Result;
}

type ChunkAnswers<Q extends Questions> = {
  chunk: Chunk;
  answers: SystemOneResult<Q>["answers"];
};
```

`plan` is pure and chunk-independent, so the core calls it once per request and reuses the questions for every chunk. `interpret` receives every chunk's typed answers and owns aggregation. Modules never call the SDK and never see other modules' questions.

Later modules that need code-only work (word filter, regex PII candidates) add an optional `deterministic(config, chunks)` step. Later modules that need a second Jev round trip (PII confirm after regex) add an optional `planFollowUp`. Neither exists in v1; the interface is documented so they are additive.

### 4.2 Core pipeline

1. Validate with Zod. Reject reserved checks with 422.
2. Flatten messages into blocks with their `(messageIndex, contentIndex)`.
3. Chunk: never split a block across chunks if it fits; split oversized blocks at sentence boundaries with 200-token overlap; target `chunkTokens`. Token count uses a local tokenizer approximation (4 chars per token) and is validated against Jev's reported `usage`.
4. For each active module, call `plan(config)` once. Namespace question ids as `${module}.${id}` when merging into one `questions` map. Type-level: the merged map is an intersection of the modules' maps, so `answers` stays fully typed.
5. State per chunk is `{ role, text }` for a single-block chunk, or `{ messages: [{ role, text }, ...] }` for a multi-block chunk. Role is included because "assistant says X" and "user says X" differ for every content category.
6. One `client.systemOne({ state, questions })` per chunk, `Promise.all` with a concurrency cap (default 16, under the 1,200 rpm limit for expected traffic).
7. Split answers back per module by prefix, call `interpret`.
8. If a policy is present, run the router: per finding, `probability >= blockThreshold` or the override's action, else `>= reviewThreshold` means review, else pass. Severity at or above `severityBlock` upgrades review to block. Overall route is the max by precedence block > review > pass. Reasons list every finding at or above review.
9. Sum usage, return.

### 4.3 Content filter module

`plan` returns a map of Nouls, one per built-in category and one per custom category, plus one Score when severity is on. Built-in instruction and criteria text is a versioned constant; changing it is a model-behaviour change and gets a changelog entry. Wording starts from the guardrails cookbook and Bedrock's category definitions in doc 09, then is tuned against fixtures.

`interpret` takes the max noul per category across chunks and records the chunk. Severity is the max expected score. No arithmetic beyond max, per the jaggedness guidance that combining probabilities across questions is not sound.

### 4.4 Configuration

Environment only: `TYPESAFE_API_KEY`, `TYPESAFE_DEFAULT_MODEL`, `GUARDRAILS_BEARER_TOKEN` (single shared token, required), `GUARDRAILS_CONCURRENCY`, `PORT`. Policy presets `strict` and `permissive` are constants shipped with the service; the values come from the cookbook and are documented as starting points to be re-tuned on our fixtures.

## 5. Efficiency rules

- One Jev request per chunk, all questions for all active checks in it. Never one request per category.
- No Jev call for a check that is not in the request.
- Chunks run in parallel. A 100k-token document is ~34 chunks in flight at once, done in roughly one Jev round trip.
- `plan` runs once per request, not per chunk.
- Custom categories cost one extra Noul in the same request. They do not add a round trip.
- Token accounting comes from Jev's `usage`, not estimates, and is returned so callers can see cost per call.

## 6. Type safety rules

- `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`.
- Zod schemas are the only place HTTP shapes are declared; `z.infer` everywhere else.
- Modules are generic over their question map; the SDK's `ResultFor` gives answer types. Reading `answers["contentFilter.HATE"].noul` is a compile error if that id is a Score.
- The router operates on `NoulFinding | ScoreFinding` discriminated by `kind`; exhaustiveness is enforced with `satisfies never`.
- OpenAPI is generated from Zod in CI and committed; a diff fails the build.

## 7. Testing

- Schema tests: every reserved check key rejected with the right message; threshold ordering enforced; custom key collisions rejected.
- Module tests with a fake SDK client returning fixed answers: aggregation picks the right chunk, severity upgrade works, missing policy yields no `route`.
- Chunker tests: block boundaries respected, overlap present on split blocks, token estimate within 15% of Jev's reported usage on fixtures.
- Live tests, gated on `TYPESAFE_API_KEY`: the 15 cookbook messages must route the same way the cookbook reports under `strict`, and the in-the-wild jailbreak sample from doc 07 must produce the expected block rate. Results and thresholds recorded in `fixtures/results.json`.
- Load test: 100 concurrent single-chunk requests stay under the rate limit and under 500 ms p95.

## 8. Repository layout

```
src/
  schema/        request.ts, response.ts, policy.ts, errors.ts   (Zod, normative)
  core/          chunker.ts, planner.ts, executor.ts, router.ts, pipeline.ts
  checks/        content-filter/{module.ts, questions.ts, presets.ts}
  http/          app.ts (Hono), auth.ts, openapi.ts
  index.ts
fixtures/        messages/*.txt, labels.json, results.json
test/            mirrors src/
openapi.json     generated
```

## 9. Open items for later designs, not v1

- Denied topics module: one Noul per topic with definition and examples in criteria, or one Choice over topics plus none. Decide with fixtures.
- PII module: regex candidates plus one confirm Noul each, a two-step pipeline that needs `planFollowUp`.
- Action check: tool name, arguments, task, and trace as structured state; scope Noul, risk Score; Cedar decision. Depends on kill-the-god-agent scenarios.
- Bedrock-compatible `ApplyGuardrail` and `InvokeGuardrailChecks` adapters over the same pipeline.
- Stored policies and versions, per-tenant auth.

# Vendor branding check (28 Oct 2026)

Sources were read on 28 Oct 2026. OpenRouter pages were read in the built-in browser because WebFetch returned 404 for them. All quotes are under 15 words.

## Table

| id | current name | recommended name | current maker | recommended maker | change? | source and wording relied on |
|---|---|---|---|---|---|---|
| pplx-decider-v1-27b | Decisions API | **pplx-decider-v1-27b** | Perplexity | Perplexity · Decisions API | yes | HF card perplexity-ai/pplx-decider-v1-27b: "pplx-decider-v1-27b is a decision model fine-tuned from Qwen3.8-27B". docs.perplexity.ai/changelog: "Decisions API … with `pplx-decider-v1-27b`" (Oct 2026). Perplexity writes every model name as a lowercase id with "27b" in it. No prose name such as "Decider v1" exists. |
| pplx-decider-v1-2-27b | Decider v1.2 | **pplx-decider-v1.2** | Perplexity · Decisions API | same | yes | x.com/perplexitydevs: "comes in two sizes, pplx-decider-v1.2 and pplx-decider-flash-v1.2". The HF card heading is "pplx-decider-v1.2", with no "27B" in the name. |
| pplx-decider-flash-v1-2 | Decider Flash v1.2 | **pplx-decider-flash-v1.2** | Perplexity · Decisions API | same | yes | Same X post and the HF card heading "pplx-decider-flash-v1.2". The prose shortens it to "Flash", as in "Flash is the top 4B on the Decis…". |
| gpt-6-luna | Decisions API | **GPT-6 Luna** | OpenAI | **OpenAI · Decisions API** | yes | openai.com/index/decisions-api (22 Oct 2026): "Built with GPT‑6 Luna, the Decisions API focuses Luna's intelligence". The docs guide uses only the id `gpt-6-luna`, "the only currently supported model". OpenAI's page writes the hyphen as U+2011; the board should use a plain "-". |
| clef | Clef | Clef | Cloudflare · Workers AI | same | no | blog.cloudflare.com/clef-decision-models: "two Cloudflare-trained decision models, Clef and Clef-flash, hosted on Workers AI" (1 Oct 2026). |
| clef-flash | Clef Flash | **Clef-flash** | Cloudflare · Workers AI | same | yes | Same blog post and changelog 2026-10-01: "Clef and Clef-flash". Blog title (9 Oct): "…a faster Clef and a cheaper Clef-flash". Cloudflare is inconsistent here: the HF card prose says "Clef-Flash". |
| clef-omni | Clef Omni | **Clef-omni** | Cloudflare · Workers AI | same | yes | blog.cloudflare.com/clef-faster-cheaper-multimodal title: "Introducing Clef-omni with full multimodality" (9 Oct 2026). Cloudflare is inconsistent here too: the HF card heading says "Clef-Omni". "Clef Omni" without a hyphen appears nowhere. |
| microsoft-decision-1 | Microsoft-Decision-1 | Microsoft-Decision-1 | Microsoft · via OpenRouter | same | no | commandline.microsoft.com/microsoft-decision-1-model-foundry (2026-10-09) and OpenRouter: "Microsoft: Microsoft-Decision-1". |
| drex-max | Drex Max | Drex Max | Nace.AI · via OpenRouter | same | no | nace.ai page title: "Nace.AI: Small models for professional work". OpenRouter: "Drex Max is the largest decision model from Nace.AI" (released 21 Oct 2026). |
| span-02 | Span-02 | Span-02 | Respan · via OpenRouter | same | no | respan.ai/blog/introducing-span-2 uses "Span-02" in its title and body (Oct 15, 2026). respan.ai: "Respan® is a registered trademark". |
| liquid-d1-ultra | d1-ultra | d1-ultra | Liquid AI · via OpenRouter | same | no | liquid.ai/blog (10.15.2026): "d1-ultra: Introducing the World's Best Decision Model". liquid.ai footer: "© 2026 Liquid AI, Inc." OpenRouter writes "LiquidAI:", but that is not the company's own spelling. |
| liquid-d1.1 | d1.1 | d1.1 | Liquid AI · via OpenRouter | same | no | docs.liquid.ai/lfm/models/decision-models lists "d1.1". OpenRouter: "d1.1 is Liquid AI's structured decision model" (released 27 Oct 2026). Liquid has no blog post for d1.1. |
| solar-decide | Solar Decide | Solar Decide | Upstage · via OpenRouter | same | no | OpenRouter: "Solar Decide is Upstage's structured decision model" (28 Sep 2026). upstage.ai footer: "© 2026 Upstage". The upstage.ai page title says "Upstage AI", but the footer and products use "Upstage". |
| solar-decide-flash | Solar Decide Flash | Solar Decide Flash | Upstage · via OpenRouter | same | no | OpenRouter: "Solar Decide Flash is Upstage's low-latency structured decision model" (8 Oct 2026). |
| mercury-decide | Mercury Decide | Mercury Decide | Inception · via OpenRouter | same | no | inceptionlabs.ai: "© 2026 Inception" and "Mercury Decide". "Inception Labs" appears only in the domain. |
| jev-1.14.0 | Jev 1.14.0 | **Jev 1.14** | TypeSafe | **TypeSafe AI** (see note) | yes | docs.typesafe.ai/models: prose says "Jev 1.14" and the id is `jev-1.14.0`. It is "available from October 14, 2026". The typesafe.ai title and footer read "TypeSafe AI". Prose uses the possessive "TypeSafe's". |
| jev-1.13.0 | Jev 1.13.0 | **Jev 1.13** | TypeSafe | **TypeSafe AI** (see note) | yes | docs.typesafe.ai/models: prose says "Jev 1.13" and the id is `jev-1.13.0`. |
| kev-4b | Kev 4B | **Kev-4B** | Jared Palmer · open weights | same | yes | HF jaredpalmer/kev-4b: "Kev-4B is a decision model". The release is "Kev 1.0", published 2026-09-24. |
| kev-9b | Kev 9B | **Kev-9B** | Jared Palmer · open weights | same | yes | HF jaredpalmer/kev-9b: "Kev-9B: a calibrated decision model on Qwen3.5-9B". The card has a "Kev-9B v2" (2026-09-30) and a "v1", so check which one was run. |
| kev-0-8b | Kev 0.8B | **Kev-0.8B** | Jared Palmer · open weights | same | yes | HF jaredpalmer/kev-0.8b: "Kev-0.8B is a decision model". |
| bedrock-guardrails | Bedrock Guardrails | **Amazon Bedrock Guardrails** | AWS · not a decision model | same | yes | docs.aws.amazon.com guardrails.html: "Amazon Bedrock Guardrails provides configurable safeguards…". AWS puts "Amazon" in the product name itself, the same exception as Microsoft-Decision-1. |
| strands-decider-2b | Strands Decider 2B | Strands Decider 2B | AWS · open weights | **Strands Agents · open weights** (see note) | maker only | strandsagents.com/blog/introducing-strands-decider (1 Oct 2026): "Introducing Strands Decider 2B: a small, open source, decision model". The post says the released model is v19 (`strands-decider-2B-hobson-v19`). |
| strands-decider-2b-v21 | Strands Decider 2B v21 | **Strands Decider 2B-hobson-v21** | AWS · open weights | Strands Agents · open weights | yes | The HF heading is "strands-decider-2B-hobson-v21". The vendor gives no prose name for it. "hobson" is never explained but is part of the public repo id. |
| strands-decider-2b-qwen35 | Strands Decider 2B Qwen3.5 | **Strands Decider 2B-qwen3.5-v1** | AWS · open weights | Strands Agents · open weights | yes | The strands-labs/strands-decider README gives the id pattern "strands-decider-<size>-<base>-v<N>-<YYMM>". This one is `strands-decider-2B-qwen3.5-v1-2610`. |
| strands-decider-e2b | Strands Decider E2B | **Strands Decider E2B-gemma4-v1** | AWS · open weights | Strands Agents · open weights | yes | README: `strands-decider-E2B-gemma4-v1-2610`. |
| strands-decider-e4b | Strands Decider E4B | **Strands Decider E4B-gemma4-v1** | AWS · open weights | Strands Agents · open weights | yes | README: `strands-decider-E4B-gemma4-v1-2610`. |
| strands-decider-12b | Strands Decider 12B | **Strands Decider 12B-gemma4-v1** | AWS · open weights | Strands Agents · open weights | yes | HF card: `strands-decider-12B-gemma4-v1-2610`, first release "2026-10-09". |
| strands-decider-26b-a4b | Strands Decider 26B-A4B | **Strands Decider 26B-A4B-gemma4-v1** | AWS · open weights | Strands Agents · open weights | yes | README: `strands-decider-26B-A4B-gemma4-v1-2610`. |
| open-jev-2b | Open-Jev 2B | **Open-Jev-2B** | Zefan Cai · open weights | same (unconfirmed) | yes (name) | The HF heading is "Open-Jev-2B". The GitHub README lists "Open-Jev-2B," "Open-Jev-9B," "Open-Jev-27B-v1.1". |
| laya | Laya | Laya | Convai Innovations · open weights | same | no | HF convaiinnovations/laya: the title is "Laya" and the footer reads "Apache 2.0 · Convai Innovations". |

The product names in the maker lines are spelled correctly: "Workers AI" (Cloudflare), "Decisions API" (both Perplexity and OpenAI use exactly this name), and "OpenRouter".

## Uniqueness

After these changes, every display name on the board is unique. The current board has two entries both named "Decisions API" (Perplexity and OpenAI), and the new names remove that clash. The Strands names are also unambiguous now: under the current names, "2B v21" sits next to "2B Qwen3.5", which is actually a "v1".

## Could not confirm, or needs a decision

1. **The Perplexity v1 run may not be v1.** docs.perplexity.ai says requests naming `pplx-decider-v1-27b` or `pplx-decider-v1.1-27b` "now select `pplx-decider-v1.2`". Any `pplx-decider-v1-27b` API run made after the v1.2 changelog entry (October 2026, no day given; the docs' timing test is dated 19 Oct 2026) actually ran v1.2. Check the run dates before labelling it v1.
2. **Perplexity has no capitalised brand.** It never writes "Decider v1.2", "Perplexity Decider" or "Decider Flash" as a name. The only exception is an employee post that says "Decider 1.2", which is informal. "27B" is a size in Perplexity's prose. It is part of the id only for v1 and v1.1 ("-27b"), and v1.2 drops it. There is also a size mismatch for Flash: the docs say 4B, while the HF metadata says "5B params".
3. **OpenAI's model name.** The docs guide names only the id `gpt-6-luna`. "GPT-6 Luna" comes from OpenAI's model page and its announcement. I did not find "GPT-6 Luna Decisions" on any OpenAI page; OpenRouter's chat listing is just "OpenAI: GPT-6 Luna". The Decisions API went GA on 22 Oct 2026, after the public beta in early October.
4. **Cloudflare spells the smaller models inconsistently.** The blog and changelog use "Clef-flash" and "Clef-omni". The HF cards use "Clef-Flash" and "Clef-Omni". I followed the blog, which is the most official page.
5. **TypeSafe or TypeSafe AI.** The brand in the logo, page title and footer is "TypeSafe AI". The docs prose uses "TypeSafe". Both are the vendor's own forms. I recommend "TypeSafe AI" for the logo and maker line; if you keep "TypeSafe", that is also defensible.
6. **Strands: who to credit.** No vendor page credits AWS in its prose. The HF org is "Strands Agents", the GitHub org is strands-labs ("the experimental arm of Strands Agents"), and the blog authors include Marc Brooker. The v1 weights are mirrored under HF `amazon`, and the press says "AWS's Strands Labs". "AWS" is defensible, but the vendor's own label is "Strands Agents" (or "Strands Labs" for the project). The display names for everything except v19 are my condensed form of the vendor's repo ids, with the `-2610` month suffix removed; the vendor has no prose names for them.
7. **Open-Jev's author.** The HF card and GitHub show only the handles "ZefanCai", "Zefan-Cai" and "Zefan_Cai". I found no stated full name, so "Zefan Cai" is an inference from the handles.
8. **Upstage and Solar Decide.** Solar Decide and Solar Decide Flash do not appear on upstage.ai. The names come from OpenRouter and aggregators, and I did not reach Upstage's console docs.
9. **Liquid AI and d1.1.** There is no Liquid blog post or announcement for d1.1. The name comes from Liquid's docs model list and from OpenRouter.
10. **Laya's version.** The card lists runtime "laya 0.3.20" and the checkpoints laya, laya-multilingual and laya-typed-decisions. Check which checkpoint was benchmarked; the root English checkpoint is 421M.

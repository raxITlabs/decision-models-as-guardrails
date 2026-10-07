# Product

<!-- impeccable:product-schema 1 -->

Inferred from the build brief; no interview was possible. Every line below is an assumption until the owner confirms it.

## Platform

web

## Stack

Next.js App Router, TypeScript, Tailwind, static export. Deployed on Vercel with `site/` as the project root.

## Users

Engineers and security leads choosing a guardrail for LLM products and agents. They arrive with one job in mind (stop prompt injection in a RAG pipeline, screen user input, catch PII) and want to know which systems are good at it, what they block by mistake and what they cost. The site never names or describes this audience in its copy.

## Product Purpose

The results site for the decision-models-as-guardrails benchmark by raxIT Labs: can a decision model replace a managed guardrail service? It publishes accuracy and cost for twelve systems on the same labelled checks, lets readers inspect every public row and every system's answer, and shows how to reproduce the run.

## Positioning

One fixed rule for every system (a probability of 0.5 or more blocks), the same checks for every system, contamination screens plus a held-back slice, and per-row evidence anyone can open.

## Capabilities and Constraints

- First public release, version 1.0.0. No editions, earlier versions, rulings, internal process, "provisional" or latency on public pages.
- Two dimensions only: accuracy and cost. Self-hosted cost reflects shared GPU time.
- Scores are held until release day: the site reads a generated, git-ignored `site/data/` folder and falls back to a synthetic fixture.
- Never ship unpublished-slice ids or licence-withheld text.

## Brand Commitments

raxIT. Dark ground #14120b, cream text #f5f1ec, muted #a69e94, primary blue #5673dc (hover #8fa6ec). Geist and Geist Mono. A light theme as well. Structure follows deepswe.datacurve.ai.

## Evidence on Hand

`benchmark/results/final/leaderboard.json`, the public ledgers, and the public test rows. No testimonials or customer claims exist; none may be invented.

## Accessibility & Inclusion

Real buttons and links, keyboard operation, visible focus rings, and a text equivalent for every chart. Works at phone width.

# Appendix: where the raxit-vault scripts could use Jev

Earlier survey from the same session. Not part of the guardrails product, kept because it is the first place to validate Jev on data we already own. Evidence pulled from the live SQLite databases on 18 September 2026.

| # | Where | Fragile code | Evidence it fails | Jev shape |
|---|---|---|---|---|
| 1 | linkedin-analyzer analyze.py, US location regex | Decides who makes the daily outreach list | "Greater Seattle Area", "San Francisco Bay Area", "Greater Boston", "Washington DC-Baltimore Area" all miss. Only 35 of 3,430 contacts have a location. | Choice `country` over {us, au, uk, in, other, unclear}, confidence gated, regex kept as fast path |
| 2 | score_contacts.py keyword tables | Substring matching drives lead-fit score | 2,266 of 3,430 contacts score zero. Misses "Chief Information Officer", "Platform Security Lead", "Microsoft Security and Azure Lead", "Founder & CEO". Recruiters score like CISOs. | Score for security ownership, Score for seniority, Choice for company type, one Noul per ICP. Weights stay in code. |
| 3 | `"aws" in company` and `LIKE '%aws%'` | Tags colleagues and strips cold picks | A NetApp seller with "Amazon Web Services" in the title is tagged as an AWS colleague. `%aws%` matches Laws, Dawson. | Noul "employed by Amazon Web Services itself, not a partner or reseller" |
| 4 | log_reply.py manual flags | Sentiment and commitment typed by hand | 3 replies logged in total | Paste reply text, Choice commitment {none, time, reputation, money}, Choice sentiment, human confirms |
| 5 | enrich_location.py JS heuristic | Picks the line above "Contact info" | Breaks when LinkedIn reorders the header | Send the 4 candidate lines, Choice "which is the geographic location" plus none |
| 6 | Frontmatter migration regexes | Keyword-count topic, source URL regexes, date formats | `**Sources:**` plural unmatched, trailing spaces, ties fall back to ai-security | Regex finds candidates, Choice selects. One-shot migrations, low priority |

Start with 1 and 2. Run the new scorer beside the old one on the 1,164 already-scored contacts and diff the top 50 before switching. That diff is also the cheapest calibration check we can run on Jev before trusting it in a guardrail.

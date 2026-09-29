# Where a decision model fits in cybersecurity

The fit test: a human currently reads unstructured text and picks from a short list, it happens at volume, and today's answer is a brittle regex, a rubber stamp, or a queue. Rated 1 to 5 on fit for a decision model and on how much pain the current approach causes.

| Domain | The judgment (question type) | What does it today | Fit | Pain |
|---|---|---|---|---|
| SOC alert triage | True positive / benign / needs context (Choice), severity (Score), ATT&CK technique (Choice) | Tier 1 analysts, SOAR rules | 5 | 5 |
| Phishing and BEC | Reported email: phish / spam / legit (Choice); payment-change request legitimate given prior thread (Noul); urgency pressure (Noul) | Email gateway regex, analyst queue | 5 | 5 |
| Helpdesk social engineering | Reset request story matches ticket history and HR record (Noul, gated to a callback) | Human judgment, the Scattered Spider gap | 5 | 4 |
| CSPM and cloud findings | Finding reachable given exposure (Noul), patch priority (Score), suppression justified (Noul) | Scanner severity, manual suppression | 5 | 5 |
| SAST, DAST, secrets | True vs false positive (Noul), real credential vs test fixture (Choice), PR touches auth and needs review (Noul) | Scanner output, PR checklists | 5 | 4 |
| Vulnerability management | Exploitable in our context given CVE text plus asset state (Score), urgency (Choice) | CVSS, spreadsheets | 4 | 4 |
| IAM and access governance | Justification matches role (Noul), permission needed for job (Score), which certifications deserve a look (Score) | Rubber-stamp certifications | 4 | 4 |
| Firewall and network policy | Rule justification supports scope (Noul), overly broad (Score), change matches CAB ticket (Noul) | Network team reading tickets | 4 | 3 |
| IaC and change review | Terraform diff widens exposure (Noul), risk tier (Score), CloudTrail event matches approved change (Noul) | Policy-as-code catches syntax, not intent | 4 | 4 |
| DLP and data classification | Contains PII/PHI/PCI beyond pattern match (Noul per class), share consistent with role (Noul) | Regex that flags order numbers as SSNs | 5 | 4 |
| Threat intel | Report relevant to our stack (Noul per asset class), TTP mapping (Choice), IOC confidence (Score), duplicate campaign (Noul) | Analysts skimming feeds | 4 | 3 |
| GRC and audit | Evidence proves control (Noul), finding maps to control (Choice), vendor answer satisfies requirement (Score), reportable under CPS 234 / SOCI / NDB (Choice) | Consultants, spreadsheets | 4 | 5 |
| Third-party and supply chain | Package change looks malicious (Score), vendor response evasive (Noul) | Reputation scores | 3 | 4 |
| AI agent runtime | Prompt injection present (Noul), tool call within scope (Noul), output leaks secrets (Noul), next action risk (Score), trace deviated from task (Noul) | LLM-as-judge, slow and unpriced | 5 | 5 |
| Insider risk | Behaviour matches resignation-week exfil pattern (Score) | UEBA statistics | 3 | 3 |

## The pattern

Every high-fit row is a place where a team already bought a tool that produces findings faster than humans can judge them. The decision model sits between the finding and the human. Confidence does the routing: act on the top band, queue the middle, page on the bottom.

## Where it does not fit

Anything that needs the reasoning written down for an auditor. Root-cause analysis. Report writing. Novel attacks with no option list. Those stay with an LLM or a person, fed by the decision model's output.

## Where raxIT's two halves land

Security for AI is the runtime row, the strongest single fit on the table. AI for security is everything else, with a cheap judgment engine underneath. CSPM finding triage is the first thing to test outside the product because prior AWS audit history is labelled data a calibration check needs.

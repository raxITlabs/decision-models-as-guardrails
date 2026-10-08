// Where each source's original text lives, and why we do not republish it here. Shown on rows whose text is
// withheld, so a reader can look the row up at its source. Revisions match dataset/release/redistribution.json.

export type WithheldReason = "cleared" | "noncommercial" | "gated" | "mixed" | "authored";

export interface SourceInfo {
  /** readable name of the upstream dataset or repository */
  name: string;
  /** the upstream page; the pinned revision is shown beside it */
  url: string;
  revision: string;
  licence: string;
  reason: WithheldReason;
}

const hf = (repo: string) => `https://huggingface.co/datasets/${repo}`;
const gh = (repo: string, rev: string) => `https://github.com/${repo}/tree/${rev}`;

export const SOURCES: Record<string, SourceInfo> = {
  sep_dataset: { name: "SEP (Zverev et al.)", url: gh("egozverev/Should-It-Be-Executed-Or-Processed", "7606c06"), revision: "7606c06", licence: "MIT", reason: "cleared" },
  wildjailbreak: { name: "WildJailbreak (AI2)", url: hf("allenai/wildjailbreak"), revision: "5ddc12a", licence: "ODC-BY 1.0 + AI2 Responsible Use Guidelines", reason: "gated" },
  itw_jailbreak_prompts: { name: "In-the-wild jailbreak prompts", url: hf("TrustAIRLab/in-the-wild-jailbreak-prompts"), revision: "a10aab8", licence: "MIT", reason: "cleared" },
  lakera_mosscap: { name: "Lakera Mosscap", url: hf("Lakera/mosscap_prompt_injection"), revision: "b7e495f", licence: "MIT", reason: "cleared" },
  e2_content_beavertails: { name: "BeaverTails", url: hf("PKU-Alignment/BeaverTails"), revision: "8401fe6", licence: "CC-BY-NC-4.0", reason: "noncommercial" },
  e2_profanity_rtp: { name: "RealToxicityPrompts (AI2)", url: hf("allenai/real-toxicity-prompts"), revision: "f2162971", licence: "Apache-2.0", reason: "cleared" },
  e2_content_xstest: { name: "XSTest", url: gh("paul-rottger/xstest", "d7bb5bd"), revision: "d7bb5bd", licence: "CC-BY-4.0", reason: "cleared" },
  nemotron_pii: { name: "Nemotron-PII (NVIDIA)", url: hf("nvidia/Nemotron-PII"), revision: "b70ffaf", licence: "CC-BY-4.0", reason: "cleared" },
  summedits: { name: "SummEdits (Salesforce)", url: hf("Salesforce/summedits"), revision: "ce0c479", licence: "CC-BY-4.0", reason: "cleared" },
  e2_content_harmbench_cls: { name: "HarmBench classifier set", url: gh("centerforaisafety/HarmBench", "8e1604d"), revision: "8e1604d", licence: "MIT", reason: "cleared" },
  gretel_pii_en: { name: "Gretel PII masking (English)", url: hf("gretelai/gretel-pii-masking-en-v1"), revision: "e06eb14", licence: "Apache-2.0", reason: "cleared" },
  llmail_inject: { name: "LLMail-Inject (Microsoft)", url: hf("microsoft/llmail-inject-challenge"), revision: "1063bdf", licence: "MIT", reason: "cleared" },
  e2_content_orbench80k: { name: "OR-Bench 80k", url: hf("bench-llm/or-bench"), revision: "e36d8b8", licence: "CC-BY-4.0", reason: "cleared" },
  faithdial: { name: "FaithDial (McGill NLP)", url: hf("McGill-NLP/FaithDial"), revision: "7a414e8", licence: "MIT; knowledge sentences CC-BY-SA (Wikipedia)", reason: "cleared" },
  e2_profanity_oasst2: { name: "OpenAssistant OASST2", url: hf("OpenAssistant/oasst2"), revision: "179dd21", licence: "Apache-2.0", reason: "cleared" },
  e2_profanity_civil_comments: { name: "Civil Comments (Google)", url: hf("google/civil_comments"), revision: "f2970eb", licence: "CC0-1.0", reason: "cleared" },
  e2_content_harmbench: { name: "HarmBench", url: gh("centerforaisafety/HarmBench", "8e1604d"), revision: "8e1604d", licence: "MIT", reason: "cleared" },
  e2_authored_quote_frames: { name: "Quote frames written by raxIT around real attack text", url: "https://github.com/raxITlabs/decision-models-as-guardrails/blob/main/dataset/goldrails_dataset/sources/e2_prompt_attacks_r26.py", revision: "main", licence: "Frames CC-BY-4.0; quoted text keeps its source's terms", reason: "authored" },
  ragbench: { name: "RAGBench (Galileo)", url: hf("galileo-ai/ragbench"), revision: "97808f3", licence: "CC-BY-4.0 annotations; PubMedQA abstracts with unchecked terms", reason: "mixed" },
  e2_content_aegis2_test: { name: "Aegis 2.0 (NVIDIA)", url: hf("nvidia/Aegis-AI-Content-Safety-Dataset-2.0"), revision: "d86bb8b", licence: "CC-BY-4.0", reason: "cleared" },
  neuralchemy_injection: { name: "Neuralchemy prompt injection", url: hf("neuralchemy/Prompt-injection-dataset"), revision: "7d70432", licence: "Apache-2.0 (rows derive from HackAPrompt, WildGuardMix, HarmBench)", reason: "cleared" },
  e2_oasst2: { name: "OpenAssistant OASST2", url: hf("OpenAssistant/oasst2"), revision: "179dd21", licence: "Apache-2.0", reason: "cleared" },
  bipia: { name: "BIPIA (Microsoft)", url: gh("microsoft/BIPIA", "a004b69"), revision: "a004b69", licence: "MIT; email contexts from OpenAI Evals", reason: "cleared" },
  agentdojo: { name: "AgentDojo (ETH Zurich)", url: gh("ethz-spylab/agentdojo", "089ed46"), revision: "089ed46", licence: "MIT", reason: "cleared" },
  gretel_pii_finance: { name: "Gretel synthetic PII (finance)", url: hf("gretelai/synthetic_pii_finance_multilingual"), revision: "7b844d1", licence: "Apache-2.0", reason: "cleared" },
  deepset_injections_test: { name: "deepset prompt injections", url: hf("deepset/prompt-injections"), revision: "4f61ecb", licence: "Apache-2.0", reason: "cleared" },
  aegis2: { name: "Aegis 2.0 (NVIDIA)", url: hf("nvidia/Aegis-AI-Content-Safety-Dataset-2.0"), revision: "d86bb8b", licence: "CC-BY-4.0", reason: "cleared" },
  ailuminate_demo: { name: "AILuminate demo set (MLCommons)", url: gh("mlcommons/ailuminate", "769cc2b"), revision: "769cc2b", licence: "CC-BY-4.0", reason: "cleared" },
  openai_moderation: { name: "OpenAI moderation evaluation set", url: hf("mmathys/openai-moderation-api-evaluation"), revision: "84e5cf3", licence: "MIT", reason: "cleared" },
  orbench: { name: "OR-Bench", url: hf("bench-llm/or-bench"), revision: "e36d8b8", licence: "CC-BY-4.0", reason: "cleared" },
  e2_attack_controls: { name: "Safe controls written by raxIT (prompt attacks)", url: "https://github.com/raxITlabs/decision-models-as-guardrails/tree/main/dataset/edition2/prompt_attacks", revision: "main", licence: "CC-BY-4.0", reason: "cleared" },
  e2_denied_topics: { name: "Off-topic rows written by raxIT", url: "https://github.com/raxITlabs/decision-models-as-guardrails/tree/main/dataset/edition2/denied_topics", revision: "main", licence: "CC-BY-4.0", reason: "cleared" },
  e2_pii_controls: { name: "Personal-data controls written by raxIT", url: "https://github.com/raxITlabs/decision-models-as-guardrails/tree/main/dataset/edition2/pii", revision: "main", licence: "CC-BY-4.0", reason: "cleared" },
};

/** One plain sentence on why the text is not shown here, by the source's licence situation. */
export const REASON_TEXT: Record<WithheldReason, string> = {
  cleared: "We show the full text of 100 example rows only, so this row's text is not shown here.",
  noncommercial: "Its licence is non-commercial, so we do not republish the text.",
  gated: "The source is gated behind its publisher's terms, so we do not republish the text.",
  mixed: "Part of this source has terms we have not checked, so we do not republish the text.",
  authored: "The frame is ours, but the quoted attack text keeps its own source's terms, so we do not republish it.",
};

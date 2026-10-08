// The eight guardrail use cases the site is organised around. Each maps to one scored subtask of the benchmark.
// Shared by the data generator (scripts/) and the pages, so it holds no scores.

export type JobId = "indirect" | "direct" | "input" | "output" | "topics" | "pii" | "grounding" | "profanity";

export interface Job {
  id: JobId;
  /** suite/subtask key in leaderboard.json */
  key: string;
  /** suite name in leaderboard.json */
  suite: string;
  /** subtask name as written in the ledgers */
  ledgerSubtask: string;
  title: string;
  sub: string;
  short: string;
}

export const JOBS: Job[] = [
  {
    id: "indirect",
    key: "prompt_attacks/indirect",
    suite: "prompt_attacks",
    ledgerSubtask: "indirect",
    title: "Protect RAG and agents",
    sub: "Instructions hidden in emails, web pages and tool output",
    short: "RAG and agents",
  },
  {
    id: "direct",
    key: "prompt_attacks/direct",
    suite: "prompt_attacks",
    ledgerSubtask: "direct",
    title: "Stop jailbreaks and injection",
    sub: "Attacks typed directly into the chat",
    short: "Chat attacks",
  },
  {
    id: "input",
    key: "content/request",
    suite: "content",
    ledgerSubtask: "request",
    title: "Screen what users type",
    sub: "Harmful requests about violence, hate, sex and crime",
    short: "User input",
  },
  {
    id: "output",
    key: "content/reply",
    suite: "content",
    ledgerSubtask: "reply",
    title: "Check what the model says",
    sub: "Harmful content in assistant replies",
    short: "Model replies",
  },
  {
    id: "topics",
    key: "denied_topics/topic",
    suite: "denied_topics",
    ledgerSubtask: "topic",
    title: "Keep the bot on topic",
    sub: "Off-limits subjects, such as investment or legal advice",
    short: "Off-topic",
  },
  {
    id: "pii",
    key: "sensitive_info/entity_detection",
    suite: "sensitive_info",
    ledgerSubtask: "entity_detection",
    title: "Catch personal data",
    sub: "Names, email addresses, card numbers and ID numbers",
    short: "Personal data",
  },
  {
    id: "grounding",
    key: "grounding/grounding",
    suite: "grounding",
    ledgerSubtask: "grounding",
    title: "Catch unsupported answers",
    sub: "Claims that the source document does not support",
    short: "Grounding",
  },
  {
    id: "profanity",
    key: "word_filters/profanity",
    suite: "word_filters",
    ledgerSubtask: "profanity",
    title: "Filter profanity",
    sub: "Offensive and obscene language",
    short: "Profanity",
  },
];

export const JOB_IDS = JOBS.map((j) => j.id);
export const JOB_BY_ID = Object.fromEntries(JOBS.map((j) => [j.id, j])) as Record<JobId, Job>;
export const JOB_BY_LEDGER_SUBTASK: Record<string, Job> = Object.fromEntries(JOBS.map((j) => [j.ledgerSubtask, j]));
export const SUITE_COUNT = new Set(JOBS.map((j) => j.suite)).size;

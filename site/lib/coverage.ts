const SUITE_NAMES: Record<string, string> = {
  content: "Content", prompt_attacks: "Prompt attacks", denied_topics: "Denied topics", word_filters: "Word filters",
  sensitive_info: "Sensitive info", grounding: "Grounding",
};

/** Said in the row of a system that runs only some suites, so its rank on a suite board is not read as full coverage. */
export function coverageNote(suites: string[]): string {
  const names = suites.map((x) => SUITE_NAMES[x] ?? x);
  const list = names.length === 1 ? `${names[0]} only` : `${names.slice(0, -1).join(", ")} and ${names.at(-1)!.toLowerCase()}`;
  return `${list} · ${suites.length} of ${Object.keys(SUITE_NAMES).length} suites`;
}

// Page copy that depends on the data. Every number comes from the generated board, never from this file.
import type { QA } from "@/components/faq";
import { int, listNames, oneLine, pct, systemMap } from "./format";
import { KIND_GLOSS, KIND_LABEL } from "./kind";
import type { Board } from "./types";

export function faqItems(board: Board): QA[] {
  const f = board.facts;
  const sys = systemMap(board);
  const qf = f.questionFormat;
  const own = f.ownRows;
  const la = f.labelAgreement;
  const lr = f.labelReview;
  // Company names only: the maker before any " · product" suffix, for the managed systems.
  const managedVendors = listNames(
    [...new Set(board.systems.filter((s) => s.hosting === "managed").map((s) => s.provider.split(" · ")[0]).filter(Boolean))].sort(),
  );
  const classifiers = listNames(board.systems.filter((s) => s.kind === "classifier").map((s) => s.label ?? s.name));
  const services = listNames(board.systems.filter((s) => s.kind === "service").map((s) => s.label ?? s.name));
  return [
    {
      q: "Who funded this, and are you tied to any vendor?",
      a: (
        <p className="m-0">
          No one funded it. raxIT Labs has no commercial relationship with {managedVendors || "any vendor"} or any other company on
          this page. No vendor saw the data, the questions or the results before we published them.
        </p>
      ),
    },
    {
      q: "Doesn't the question format favour TypeSafe's Jev?",
      a: (
        <p className="m-0">
          It may. Every decision model gets the same yes/no questions in the format that Jev&apos;s API uses. Jev was trained on that
          format. The other models get the questions through our adapters. We disclose this home advantage and do not remove it,
          because any other format would favour a different system. Our rules also say that a reworded question set must first be
          checked on at least three non-Jev models. For the three sets we reworded (denied topics, prompt attacks and personal
          data), that check did not run before the results were frozen. We ran it afterwards, under a plan we published first, with
          Perplexity, OpenAI and Clef beside Jev. It passed. Compared with the old wording, the new wording left Jev 1.2 points of balanced
          accuracy worse off than the other three on average for prompt attacks, and 0.6 points worse off for denied topics. The
          check fails only if Jev gains more than 2.0 points over them.
          {qf ? ` ${oneLine(sys[qf.system], qf.system)} finishes in tier ${qf.tier} of ${qf.tiers} overall.` : ""}
        </p>
      ),
    },
    {
      q: "Did you tune thresholds for anyone?",
      a: (
        <p className="m-0">
          No. Every decision model uses the same fixed rule: a probability of {board.stats.threshold} or more blocks. Safety
          classifiers and guardrail services return a verdict with no probability, so we score the verdict as it comes. This shows
          how each system behaves by default. Some models rank risk well but have a poor default threshold. If you tune on your own
          labelled data, you can gain several points. The smaller models gain the most. The results files report AUROC for the
          decision models, so you can see how much room each one has.
        </p>
      ),
    },
    {
      q: "What's the difference between a decision model and a safety classifier?",
      a: (
        <p className="m-0">
          A decision model {KIND_GLOSS.decision}. We write the questions for each use case, and the fixed rule turns the
          probability into a block. A safety classifier {KIND_GLOSS.classifier}. We take that verdict as it comes.
          {classifiers ? ` The safety classifiers on the board are ${classifiers}.` : ""}
          {services ? ` A third kind, the ${KIND_LABEL.service.toLowerCase()}, is ${KIND_GLOSS.service}. On the board that is ${services}.` : ""}{" "}
          Safety classifiers and guardrail services are the classic guardrails. The leaderboard marks them with a symbol after the
          name.
        </p>
      ),
    },
    {
      q: "Who labelled the data, and how good are the labels?",
      a: (
        <p className="m-0">
          Labels come from each source and from our written labelling rules.
          {la
            ? ` Our lead, with an AI assistant, labelled a ${int(la.contentRows)}-row content sample a second time without seeing the first label. The two labels agreed on ${pct(la.content, 0)} of rows. An AI model with no access to the answers labelled a ${int(la.attackRows)}-row prompt-attack sample a second time. It agreed on ${pct(la.attacks, 0)}.`
            : ""}
          {lr
            ? ` After the runs, we checked again every row that at least ${lr.minWrong} of the ${lr.systems} systems got wrong. We corrected ${int(lr.corrected)} labels and removed ${int(lr.removed)} ambiguous rows.`
            : ""}
        </p>
      ),
    },
    {
      q: "Could a model have trained on the test rows?",
      a: (
        <p className="m-0">
          We compared every row with the published training data of the models on the board. We removed the matches. We also keep a
          held-back slice of {int(board.stats.heldBackRows)} rows that we do not publish.
          {typeof f.sliceGapMax === "number" ? ` Overall scores on that slice are within ${f.sliceGapMax} points of the public rows.` : ""}
          {own
            ? ` Some content rows come from datasets that the vendors published themselves. We also score content without those rows. ${oneLine(sys[own.system], own.system)} scores ${own.allRows} on all content rows and ${own.withoutOwnRows} without ${own.vendor}'s own rows. So it did ${own.withoutOwnRows >= own.allRows ? "worse, not better," : "better"} on its vendor's data.`
            : ""}{" "}
          We cannot rule out training data that a vendor has not disclosed.
        </p>
      ),
    },
    {
      q: "Can I reproduce this?",
      a: (
        <p className="m-0">
          Yes. The dataset is on Hugging Face. The code, the scoring rules and the per-row results are on GitHub. Because of their
          licences, some sources ship only the row ids. A script rebuilds that text from the original publishers. The <a href="/reproduce">Reproduce</a>{" "}
          page has the commands.
        </p>
      ),
    },
    {
      q: "What does a tier mean?",
      a: (
        <p className="m-0">
          Our statistical tests cannot tell the systems in one tier apart from that tier&apos;s leader. We resample the rows 2,000
          times. We test each system against its tier&apos;s leader. Then we correct for the number of comparisons. Two systems in one
          tier can still differ a lot in what they block and what they cost. Use those two points to choose between them.
        </p>
      ),
    },
    {
      q: "Does it cover images, multi-turn chats or my own policies?",
      a: (
        <p className="m-0">
          Not yet. The benchmark tests text only: one message and its context. Only the off-topic use case and an exact-word check cover
          custom policies. Multimodal and multi-turn tests are not part of this release.
        </p>
      ),
    },
    {
      q: "What happens to the data I send these APIs?",
      a: (
        <p className="m-0">
          We did not evaluate data retention or compliance. These depend on each vendor&apos;s terms and on your contract. Some vendors
          offer zero data retention or HIPAA support to eligible customers. Check the terms before you send regulated data.
        </p>
      ),
    },
  ];
}

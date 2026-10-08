// Page copy that depends on the data. Every number comes from the generated board, never from this file.
import type { QA } from "@/components/faq";
import { int, listNames, pct, systemMap } from "./format";
import type { Board } from "./types";

export function faqItems(board: Board): QA[] {
  const f = board.facts;
  const sys = systemMap(board);
  const qf = f.questionFormat;
  const own = f.ownRows;
  const la = f.labelAgreement;
  const lr = f.labelReview;
  const managedVendors = listNames(
    [...new Set(board.systems.map((s) => s.provider).filter((p) => p && !/open weights/i.test(p)))].sort(),
  );
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
          because any other format would favour a different system.
          {qf ? ` ${sys[qf.system]?.name ?? qf.system} finishes in tier ${qf.tier} of ${qf.tiers} overall.` : ""}
        </p>
      ),
    },
    {
      q: "Did you tune thresholds for anyone?",
      a: (
        <p className="m-0">
          No. Every system uses the same fixed rule: a probability of {board.stats.threshold} or more blocks. This shows how each
          system behaves by default. Some models rank risk well but have a poor default threshold. If you tune on your own labelled
          data, you can gain several points. The smaller models gain the most. The results files report AUROC, so you can see how much
          room each model has.
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
            ? ` Some content rows come from datasets that the vendors published themselves. We also score content without those rows. ${sys[own.system]?.name ?? own.system} scores ${own.allRows} on all content rows and ${own.withoutOwnRows} without ${own.vendor}'s own rows. So it did ${own.withoutOwnRows >= own.allRows ? "worse, not better," : "better"} on its vendor's data.`
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
          Not yet. The benchmark tests text only: one message and its context. Only the off-topic job and an exact-word check cover
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

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
          this page. No vendor saw the data, the questions or the results before publication.
        </p>
      ),
    },
    {
      q: "Doesn't the question format favour Jev?",
      a: (
        <p className="m-0">
          It may. Every decision model gets the same yes/no questions in the format Jev&apos;s API takes, and Jev was trained on that
          format. The others receive it through our adapters. We disclose that home advantage instead of removing it, since any other
          format would favour someone else.
          {qf ? ` ${sys[qf.system]?.name ?? qf.system} finishes in tier ${qf.tier} of ${qf.tiers} overall.` : ""}
        </p>
      ),
    },
    {
      q: "Did you tune thresholds for anyone?",
      a: (
        <p className="m-0">
          No. Every system uses the same fixed rule, a probability of {board.stats.threshold} or more blocks, which is how each one
          behaves out of the box. Some models rank risk well but sit at a poor default. Tuning on your own labelled data can add several
          points, most of all for the smaller models. The results files report AUROC so you can see that headroom.
        </p>
      ),
    },
    {
      q: "Who labelled the data, and how good are the labels?",
      a: (
        <p className="m-0">
          Labels come from each source and our written labelling rules.
          {la
            ? ` Our lead, working with an AI assistant, labelled a ${int(la.contentRows)}-row content sample a second time without seeing the first label, and agreed with it on ${pct(la.content, 0)} of rows. A ${int(la.attackRows)}-row prompt-attack sample was second-labelled by an AI model with no access to the answers and agreed on ${pct(la.attacks, 0)}.`
            : ""}
          {lr
            ? ` After the runs we re-checked every row that at least ${lr.minWrong} of the ${lr.systems} systems got wrong. ${int(lr.corrected)} labels were corrected and ${int(lr.removed)} ambiguous rows were removed.`
            : ""}
        </p>
      ),
    },
    {
      q: "Could a model have trained on the test rows?",
      a: (
        <p className="m-0">
          We screened every row against the published training data of the models on the board and removed matches. We also kept a
          held-back slice of {int(board.stats.heldBackRows)} rows that is not published.
          {typeof f.sliceGapMax === "number" ? ` Overall scores on it stay within ${f.sliceGapMax} points of the public rows.` : ""}
          {own
            ? ` Some content rows come from datasets the vendors published themselves; content is also scored without them. ${sys[own.system]?.name ?? own.system} scores ${own.allRows} on all content rows and ${own.withoutOwnRows} without ${own.vendor}'s own rows, so it did ${own.withoutOwnRows >= own.allRows ? "worse, not better," : "better"} on its vendor's data.`
            : ""}{" "}
          We cannot rule out training data a vendor has not disclosed.
        </p>
      ),
    },
    {
      q: "Can I reproduce this?",
      a: (
        <p className="m-0">
          Yes. The dataset is on Hugging Face, and the code, scoring rules and per-row results are on GitHub. Some sources ship ids only
          because of their licences. A script rebuilds that text from the original publishers. The <a href="/reproduce">Reproduce</a>{" "}
          page has the commands.
        </p>
      ),
    },
    {
      q: "What does a tier mean?",
      a: (
        <p className="m-0">
          Systems in one tier cannot be told apart statistically from the tier&apos;s leader. We resample the rows 2,000 times, test
          each system against its tier&apos;s leader and correct for the number of comparisons. Two systems in one tier can still differ a
          lot in what they block and what they cost, so choose between them on those.
        </p>
      ),
    },
    {
      q: "Does it cover images, multi-turn chats or my own policies?",
      a: (
        <p className="m-0">
          Not yet. The benchmark is text only, one message with its context. Custom policies are covered only through the off-topic job
          and an exact-word check. Multimodal and multi-turn tests are not part of this release.
        </p>
      ),
    },
    {
      q: "What happens to the data I send these APIs?",
      a: (
        <p className="m-0">
          We did not evaluate retention or compliance. It depends on each vendor&apos;s terms and your contract. Some offer zero data
          retention or HIPAA support to eligible customers. Check before you send regulated data.
        </p>
      ),
    },
  ];
}

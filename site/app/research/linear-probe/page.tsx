import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "@/components/icons";

export const metadata: Metadata = {
  title: "What two linear probes reveal about decision-model guardrails",
  description:
    "How Strands Decider 2B and Kev 4B probes were trained and selected, what their activation plots show, and how both models decided on 540 held-out denied-topic rows.",
  alternates: { canonical: "/research/linear-probe" },
  openGraph: { url: "/research/linear-probe", siteName: "decision-models-as-guardrails", type: "article" },
};

const ROOT = "/research/linear-probe";
const KEV = `${ROOT}/kev-4b`;

const outcomes = [
  { model: "Strands 2B", readout: "Native · fixed 0.5", ba: "85.3%", interval: "82.5–87.9%", caught: "244 / 256", falseBlocks: "70 / 284" },
  { model: "Strands 2B", readout: "Native · tuned", ba: "88.3%", interval: "85.5–90.8%", caught: "214 / 256", falseBlocks: "20 / 284" },
  { model: "Strands 2B", readout: "Linear probe · tuned", ba: "96.9%", interval: "95.4–98.4%", caught: "243 / 256", falseBlocks: "3 / 284", probe: true },
  { model: "Kev 4B", readout: "Native · fixed 0.5", ba: "93.8%", interval: "91.9–95.6%", caught: "256 / 256", falseBlocks: "35 / 284" },
  { model: "Kev 4B", readout: "Native · tuned", ba: "96.5%", interval: "95.0–97.9%", caught: "255 / 256", falseBlocks: "19 / 284" },
  { model: "Kev 4B", readout: "Linear probe · tuned", ba: "98.4%", interval: "97.1–99.3%", caught: "253 / 256", falseBlocks: "6 / 284", probe: true },
];

export default function LinearProbeResearch() {
  return (
    <article className="mx-auto flex max-w-[1200px] flex-col gap-16 px-4 pt-10 sm:gap-20 sm:px-6 sm:pt-16">
      <header className="flex max-w-[930px] flex-col gap-5">
        <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Research article · 14 October 2026</span>
        <h1 className="m-0 text-[clamp(2.25rem,5vw,4rem)] font-semibold leading-[1.05] tracking-[-0.03em] text-balance">
          When does a decision model actually work as a guardrail?
        </h1>
        <p className="m-0 max-w-[78ch] text-[18px] leading-relaxed text-fg-2">
          We tested Strands Decider 2B and Kev 4B on the <strong>same 540 readable denied-topic rows</strong>.
          Their native outputs answer the practical question: how many policy violations do they catch, and how often do they block safe text?
          Linear probes ask a second question: can a small classifier trained on each model&apos;s intermediate activations make a better decision?
          This study is one slice of the <Link href="/">broader guardrail benchmark</Link>.
        </p>
      </header>

      <section aria-labelledby="finding-h" className="grid gap-8 border-y border-line-strong py-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:gap-14">
        <div className="flex flex-col gap-4">
          <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Finding</span>
          <h2 id="finding-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">
            Where do the native decisions and probes differ?
          </h2>
          <p className="m-0 text-[15px] leading-relaxed text-fg-2">
            At the benchmark&apos;s fixed 0.5 rule, Kev caught every policy-block row and falsely blocked 35 safe rows.
            Strands missed 12 policy-block rows and falsely blocked 70 safe rows.
            After validation tuning, Kev&apos;s native score reached 96.5% balanced accuracy; Strands reached 88.3%.
            A supervised linear probe raised Strands to 96.9%. Kev&apos;s probe gain was smaller and statistically uncertain.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-px border border-line-strong bg-line-strong self-stretch">
          <div className="flex flex-col justify-center gap-2 bg-surface p-5">
            <span className="num text-[clamp(1.9rem,4vw,2.9rem)] font-semibold tracking-[-0.04em]">256/256</span>
            <span className="text-[13px] leading-snug text-fg-2">Kev native caught block cases<br />at fixed 0.5</span>
            <span className="text-[13px] text-muted">35/284 safe rows blocked</span>
          </div>
          <div className="flex flex-col justify-center gap-2 bg-surface p-5">
            <span className="num text-[clamp(1.9rem,4vw,2.9rem)] font-semibold tracking-[-0.04em]">244/256</span>
            <span className="text-[13px] leading-snug text-fg-2">Strands native caught block cases<br />at fixed 0.5</span>
            <span className="text-[13px] text-muted">70/284 safe rows blocked</span>
          </div>
        </div>
      </section>

      <section aria-labelledby="method-h" className="flex flex-col gap-6">
        <div className="flex max-w-[850px] flex-col gap-3">
          <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Method · before opening test</span>
          <h2 id="method-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">How were the probes trained and chosen?</h2>
          <p className="m-0 text-[15px] leading-relaxed text-fg-2">
            The models and their native decision heads stayed frozen. We trained small readouts from their internal vectors,
            made every selection on the <strong>29-row validation set</strong>, then evaluated once on the <strong>540-row test set</strong>.
          </p>
        </div>
        <div className="grid gap-px border-y border-line-strong bg-line-strong md:grid-cols-3">
          <div className="flex flex-col gap-3 bg-surface px-0 py-5 md:px-5">
            <span className="num text-[13px] text-accent">01 / Data</span>
            <h3 className="m-0 text-[18px] font-semibold">What was held fixed?</h3>
            <p className="m-0 text-[14px] leading-relaxed text-fg-2">
              Both runs used the same nine written policy questions and identical row manifests: 89 train, 29 validation, 540 test.
              A policy <em>yes</em> means block. Exact duplicate inputs were removed, related rows stayed in the same split,
              and any dev/test overlap was excluded. Rows without readable text were omitted, never reconstructed from labels.
            </p>
          </div>
          <div className="flex flex-col gap-3 bg-surface px-0 py-5 md:px-5">
            <span className="num text-[13px] text-accent">02 / Features</span>
            <h3 className="m-0 text-[18px] font-semibold">What did each probe read?</h3>
            <p className="m-0 text-[14px] leading-relaxed text-fg-2">
              At seven sampled decoder blocks per model, we averaged vectors across the nine question branches.
              <code> answer_mean</code> reads the answer position; <code>option_delta</code> subtracts the false-option vector from the true-option vector.
              On training rows, we fitted a class-mean direction and standardized logistic regression at C = 0.001, 0.01, or 0.1.
            </p>
          </div>
          <div className="flex flex-col gap-3 bg-surface px-0 py-5 md:px-5">
            <span className="num text-[13px] text-accent">03 / Selection</span>
            <h3 className="m-0 text-[18px] font-semibold">How was a winner frozen?</h3>
            <p className="m-0 text-[14px] leading-relaxed text-fg-2">
              For each probe type, validation AUROC ranked feature, block, and C; balanced accuracy and then the shallower block broke ties.
              A separate validation search chose the decision threshold that maximized balanced accuracy, including the default threshold among candidates.
              We tuned the native-score threshold on that same split, saved all choices, and only then opened test.
            </p>
          </div>
        </div>
        <p className="m-0 max-w-[90ch] text-[13px] leading-relaxed text-muted">
          The native path uses each checkpoint&apos;s own prompt rendering and decision head, then takes the maximum of its nine question scores.
          The probes receive the same inputs but new task labels during fitting. The small validation set makes this selection exploratory;
          perfect validation scores are not evidence of perfect generalization.
        </p>
      </section>

      <section aria-labelledby="layers-h" className="flex flex-col gap-5 border-t border-line-strong pt-8">
        <div className="flex max-w-[850px] flex-col gap-3">
          <h2 id="layers-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">Which layers did validation favor?</h2>
          <p className="m-0 text-[15px] leading-relaxed text-fg-2">
            Each line plots validation ranking quality across sampled decoder blocks; higher AUROC means block rows tend to receive higher scores than allow rows.
            For each logistic-regression point, the chart shows the best of the three C values <em>on validation</em>.
            The dashed line is that model&apos;s native score on the same 29 rows. These are selection plots, not held-out results.
          </p>
        </div>
        <div className="grid gap-6">
          <figure className="m-0 flex flex-col gap-3 border border-line bg-white p-3 sm:p-5">
            {/* eslint-disable-next-line @next/next/no-img-element -- original static research figure */}
            <img src={`${ROOT}/validation-layer-sweep.png`} width={1601} height={697} loading="lazy" className="h-auto w-full" alt="Strands validation AUROC by decoder block for class-mean and logistic probes at answer and option positions; several later logistic probes reach 1.0." />
            <figcaption className="text-[13px] leading-relaxed text-muted">
              <strong>Strands Decider 2B.</strong> Sampled blocks 0, 3, 7, 11, 15, 19, 23. The selected linear readout uses <code>answer_mean</code> at block 11, C = 0.1;
              validation AUROC and balanced accuracy were both 1.0. Several settings reached the same ceiling, so the tie rule matters.
            </figcaption>
            <a href={`${ROOT}/validation-layer-sweep.png`} target="_blank" rel="noopener noreferrer" className="inline-flex w-fit items-center gap-1 text-[13px]">Open full-size figure <ArrowRight /></a>
          </figure>
          <figure className="m-0 flex flex-col gap-3 border border-line bg-white p-3 sm:p-5">
            {/* eslint-disable-next-line @next/next/no-img-element -- original static research figure */}
            <img src={`${KEV}/validation-layer-sweep.png`} width={1601} height={697} loading="lazy" className="h-auto w-full" alt="Kev validation AUROC by decoder block for class-mean and logistic probes at answer and option positions; several middle and later probes reach 1.0." />
            <figcaption className="text-[13px] leading-relaxed text-muted">
              <strong>Kev 4B.</strong> Sampled blocks 0, 5, 10, 15, 20, 25, 31. The selected linear readout uses <code>answer_mean</code> at block 15, C = 0.001;
              validation AUROC and balanced accuracy were both 1.0. This validation plateau does not by itself show a test gain over Kev&apos;s native score.
            </figcaption>
            <a href={`${KEV}/validation-layer-sweep.png`} target="_blank" rel="noopener noreferrer" className="inline-flex w-fit items-center gap-1 text-[13px]">Open full-size figure <ArrowRight /></a>
          </figure>
        </div>
      </section>

      <section aria-labelledby="results-h" className="flex flex-col gap-5">
        <div className="flex max-w-[820px] flex-col gap-3">
          <h2 id="results-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">How often did each model block correctly?</h2>
          <p className="m-0 text-[15px] leading-relaxed text-fg-2">
            The 540 test rows contain 256 that the written policy says to block and 284 it says to allow.
            Balanced accuracy averages the catch rate and the correct allow rate; a model cannot score well by blocking everything.
            Intervals below are 95% group-bootstrap intervals for balanced accuracy.
          </p>
        </div>
        <div className="overflow-x-auto border-y border-line-strong">
          <table className="w-full min-w-[820px] border-collapse text-left text-[14px]">
            <thead className="text-muted"><tr className="border-b border-line">
              <th scope="col" className="py-3 pr-3 font-medium">Model</th>
              <th scope="col" className="px-3 py-3 font-medium">Readout</th>
              <th scope="col" className="num px-3 py-3 text-right font-medium">Balanced accuracy</th>
              <th scope="col" className="num px-3 py-3 text-right font-medium">95% interval</th>
              <th scope="col" className="num px-3 py-3 text-right font-medium">Block cases caught</th>
              <th scope="col" className="num py-3 pl-3 text-right font-medium">Safe rows blocked</th>
            </tr></thead>
            <tbody>{outcomes.map((row, index) => (
              <tr key={`${row.model}-${row.readout}`} className={`border-b border-line last:border-b-0 ${index === 3 ? "border-t-2 border-line-strong" : ""} ${row.probe ? "bg-selected" : ""}`}>
                <th scope="row" className="py-4 pr-3 font-semibold">{row.model}</th>
                <td className="px-3 py-4">{row.readout}</td>
                <td className="num px-3 py-4 text-right font-semibold">{row.ba}</td>
                <td className="num px-3 py-4 text-right text-muted">{row.interval}</td>
                <td className="num px-3 py-4 text-right">{row.caught}</td>
                <td className="num py-4 pl-3 text-right">{row.falseBlocks}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="m-0 max-w-[88ch] text-[13px] leading-relaxed text-muted">
          “Native · fixed 0.5” is closest to the board&apos;s rule. “Tuned” thresholds and probe settings were selected on the 29-row validation split, before opening test.
          The native score is the maximum of nine policy-question scores, not a calibrated probability of any violation.
          Probe rows are supervised additions to each model and are not entries in the default-rule leaderboard.
        </p>
      </section>

      <section aria-labelledby="probe-h" className="grid gap-8 border-y border-line-strong py-8 md:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] md:gap-14">
        <div className="flex flex-col gap-3">
          <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Inside the models</span>
          <h2 id="probe-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">What do the probes add beyond the native scores?</h2>
        </div>
        <div className="flex flex-col gap-5 text-[15px] leading-relaxed text-fg-2">
          <p className="m-0">
            <strong>Strands:</strong> its linear probe beat its validation tuned native score by <strong>8.7 percentage points</strong>
            in balanced accuracy (paired 95% interval <strong>+6.2 to +11.5 points</strong>).
            It caught 243 rather than 214 block cases while reducing false blocks from 20 to 3.
            That is evidence that its intermediate states contain useful information the delivered scoring pipeline did not extract as effectively on this slice.
          </p>
          <p className="m-0">
            <strong>Kev:</strong> its probe gained <strong>1.9 points</strong> over its tuned native score, but the paired interval
            (<strong>−0.04 to +3.7 points</strong>) reaches zero. Kev&apos;s native score already ranked these rows extremely well
            (AUROC 0.998, versus 0.961 for Strands); its probe did not establish a clear extra ranking advantage.
            On this dataset, Kev&apos;s native decision pipeline is already close to the fitted probe&apos;s operating point.
          </p>
          <p className="m-0">
            Both runs trained a character n-gram text baseline on the same labels. It reached 75.6% balanced accuracy,
            well below both models&apos; native and probed scores. This rules out that one simple lexical baseline as a complete explanation;
            it does not prove that either model reasons causally about the policy.
          </p>
        </div>
      </section>

      <section aria-labelledby="figures-h" className="flex flex-col gap-5">
        <h2 id="figures-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">What happens across thresholds on held-out rows?</h2>
        <p className="m-0 max-w-[82ch] text-[15px] leading-relaxed text-fg-2">
          ROC curves show the catch versus false-block trade-off over all thresholds. The bars show balanced accuracy at the validation chosen threshold.
          Each figure uses the same 540 rows; “LR” means a logistic regression readout of that model&apos;s activations.
        </p>
        <div className="grid gap-6">
          <figure className="m-0 flex flex-col gap-3 border border-line bg-white p-3 sm:p-5">
            {/* eslint-disable-next-line @next/next/no-img-element -- original static research figure */}
            <img src={`${ROOT}/held-out-roc-and-accuracy.png`} width={2321} height={769} loading="lazy" className="h-auto w-full" alt="Strands Decider 2B held-out ROC and balanced accuracy. The linear probe exceeds the native score on the test rows." />
            <figcaption className="text-[13px] leading-relaxed text-muted">Strands Decider 2B · native AUROC 0.961; probe AUROC 0.997.</figcaption>
            <a href={`${ROOT}/held-out-roc-and-accuracy.png`} target="_blank" rel="noopener noreferrer" className="inline-flex w-fit items-center gap-1 text-[13px]">Open full-size figure <ArrowRight /></a>
          </figure>
          <figure className="m-0 flex flex-col gap-3 border border-line bg-white p-3 sm:p-5">
            {/* eslint-disable-next-line @next/next/no-img-element -- original static research figure */}
            <img src={`${KEV}/held-out-roc-and-accuracy.png`} width={2321} height={769} loading="lazy" className="h-auto w-full" alt="Kev 4B held-out ROC and balanced accuracy. Its native score and linear probe both rank the test rows very well." />
            <figcaption className="text-[13px] leading-relaxed text-muted">Kev 4B · native AUROC 0.998; probe AUROC 0.994.</figcaption>
            <a href={`${KEV}/held-out-roc-and-accuracy.png`} target="_blank" rel="noopener noreferrer" className="inline-flex w-fit items-center gap-1 text-[13px]">Open full-size figure <ArrowRight /></a>
          </figure>
        </div>
        <p className="m-0 max-w-[88ch] text-[13px] leading-relaxed text-muted">
          The bars&apos; 95% intervals resample related test groups. They condition on the chosen probes and do not capture training-sample or model-selection uncertainty.
          The paired intervals above compare each probe with its own tuned native score; overlapping bars alone are not a paired comparison.
        </p>
      </section>

      <section aria-labelledby="pca-h" className="flex flex-col gap-5 border-t border-line-strong pt-8">
        <div className="flex max-w-[850px] flex-col gap-3">
          <h2 id="pca-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">What does a two-dimensional view of the activations show?</h2>
          <p className="m-0 text-[15px] leading-relaxed text-fg-2">
            For each model, PCA found two high-variance directions in the <em>training</em> vectors from its selected answer-position block.
            We projected the 540 test vectors onto those fixed axes and colored them by policy label. Test labels were used for color only;
            PCA neither selected the probe nor supplied its decision rule.
          </p>
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          <figure className="m-0 flex flex-col gap-3 border border-line bg-white p-3 sm:p-5">
            {/* eslint-disable-next-line @next/next/no-img-element -- original static research figure */}
            <img src={`${ROOT}/train-fitted-pca.png`} width={1241} height={877} loading="lazy" className="h-auto w-full" alt="Strands test activations projected onto two PCA axes fitted on training vectors at block 11; block and allow points separate partly and overlap in the middle." />
            <figcaption className="text-[13px] leading-relaxed text-muted">
              <strong>Strands · block 11.</strong> PC1 explains 25.1% and PC2 10.5% of training variance. The test labels partly separate, with overlap around the center.
            </figcaption>
            <a href={`${ROOT}/train-fitted-pca.png`} target="_blank" rel="noopener noreferrer" className="inline-flex w-fit items-center gap-1 text-[13px]">Open full-size figure <ArrowRight /></a>
          </figure>
          <figure className="m-0 flex flex-col gap-3 border border-line bg-white p-3 sm:p-5">
            {/* eslint-disable-next-line @next/next/no-img-element -- original static research figure */}
            <img src={`${KEV}/train-fitted-pca.png`} width={1241} height={877} loading="lazy" className="h-auto w-full" alt="Kev test activations projected onto two PCA axes fitted on training vectors at block 15; block and allow points separate partly and overlap in the middle." />
            <figcaption className="text-[13px] leading-relaxed text-muted">
              <strong>Kev · block 15.</strong> PC1 explains 20.9% and PC2 10.8% of training variance. The test labels also partly separate, with visible overlap.
            </figcaption>
            <a href={`${KEV}/train-fitted-pca.png`} target="_blank" rel="noopener noreferrer" className="inline-flex w-fit items-center gap-1 text-[13px]">Open full-size figure <ArrowRight /></a>
          </figure>
        </div>
        <p className="m-0 max-w-[90ch] text-[13px] leading-relaxed text-muted">
          PCA compresses a high-dimensional vector to two unsupervised axes, so visible overlap does not contradict strong linear-probe performance.
          The axes were fitted separately for each model and cannot be compared coordinate for coordinate. The held-out decisions and paired intervals above carry the performance claim.
        </p>
      </section>

      <section aria-labelledby="why-h" className="grid gap-8 md:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] md:gap-14">
        <div className="flex flex-col gap-3">
          <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Interpretation</span>
          <h2 id="why-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">Why might the models differ?</h2>
        </div>
        <div className="flex flex-col gap-5 text-[15px] leading-relaxed text-fg-2">
          <p className="m-0">
            <strong>Observed:</strong> Kev&apos;s native scores separate block and allow rows more sharply across thresholds.
            Strands&apos;s intermediate activations support a much better fitted decision than its native score on these examples.
            For Kev, the native path already performs strongly, so a new readout has less room to improve.
          </p>
          <p className="m-0">
            <strong>Possible explanations:</strong> the checkpoints differ in backbone size, fine-tuning, native head, score temperature,
            and model-specific prompt rendering. The probes also pool different token positions:
            Strands uses an answer token from decoder block 11; Kev uses its <code>&lt;decide&gt;</code> token from block 15.
            The native path takes a maximum over nine question scores, while each probe learns from pooled activations using these task labels.
            These experiments change several factors at once, so they cannot assign the performance gap to a single architectural component.
          </p>
        </div>
      </section>

      <section aria-labelledby="scope-h" className="grid gap-8 border-y border-line-strong py-8 md:grid-cols-2 md:gap-14">
        <div className="flex flex-col gap-3">
          <h2 id="scope-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">What can these results support?</h2>
          <p className="m-0 text-[15px] leading-relaxed text-fg-2">
            Kev 4B&apos;s delivered output is strong on this explicit denied-topic policy set: at a validation tuned threshold it misses 1 of 256 block cases and falsely blocks 19 of 284 safe cases.
            Strands 2B is less reliable through its native output here, but its activations support a stronger supervised readout.
            The native results show what a caller would receive; the probes reveal information available inside each model.
          </p>
        </div>
        <div className="flex flex-col gap-3">
          <h3 className="m-0 text-[19px] font-semibold">What remains unproved?</h3>
          <p className="m-0 text-[15px] leading-relaxed text-fg-2">
            Both runs use the same nine known policy definitions and only the readable denied-topic subset: 89 training, 29 validation, and 540 test rows.
            Another 61 test rows lacked readable text and were omitted. Labels were AI drafted and cross-checked.
            The tests do not establish performance on unseen policies, adversarial attacks, the benchmark&apos;s other jobs, or the private held-back slice.
            Kev&apos;s optional order-robustness and topic-transfer cells were not run in the supplied full-run artifacts.
            A probe still requires the whole model forward pass, so these results do not establish lower cost.
          </p>
        </div>
      </section>

      <section aria-labelledby="next-h" className="flex max-w-[900px] flex-col gap-4 border-l-2 border-accent pl-5">
        <h2 id="next-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">What should the next guardrail test ask?</h2>
        <p className="m-0 text-[15px] leading-relaxed text-fg-2">
          Freeze each native or probed decision rule, then test it on independently labelled policy changes, safe lookalikes, attacks, and the other benchmark jobs.
          Measure catch rate, false blocks, failures, latency, and cost together. To test whether a head or aggregation step causes the Strands gap,
          hold the representation and training data fixed while changing only that readout step.
          Those experiments would tell us whether today&apos;s promising denied-topic results survive real guardrail conditions.
        </p>
      </section>

      <section aria-labelledby="materials-h" className="flex max-w-[920px] flex-col gap-4">
        <h2 id="materials-h" className="m-0 text-[clamp(1.6rem,3vw,2.25rem)] font-semibold leading-[1.1] tracking-[-0.02em]">How can you inspect the code and results?</h2>
        <p className="m-0 text-[15px] leading-relaxed text-fg-2">
          The source notebooks live in <code>research/probes/notebooks/</code> in this repository. Their website copies have execution outputs removed;
          the linked run manifests and aggregate files record the completed full runs. Both notebooks default to a smoke test: set <code>SMOKE=False</code> to rerun the full experiment.
          Model, code, dataset, and question-set revisions are pinned in each manifest.
        </p>
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="flex flex-col gap-2 border-t border-line-strong pt-4">
            <h3 className="m-0 text-[17px] font-semibold">Where are the Strands Decider 2B files?</h3>
            <a href={`${ROOT}/raxit_decision_model_linear_probes.ipynb`} download>Notebook <ArrowRight /></a>
            <a href={`${ROOT}/run_manifest.json`}>Run manifest <ArrowRight /></a>
            <a href={`${ROOT}/frozen_selection.json`}>Frozen settings <ArrowRight /></a>
            <a href={`${ROOT}/validation_search.csv`}>Validation search table <ArrowRight /></a>
            <a href={`${ROOT}/test_metrics_with_intervals.csv`}>Test metrics <ArrowRight /></a>
            <a href={`${ROOT}/paired_probe_minus_tuned_native.json`}>Paired probe comparison <ArrowRight /></a>
          </div>
          <div className="flex flex-col gap-2 border-t border-line-strong pt-4">
            <h3 className="m-0 text-[17px] font-semibold">Where are the Kev 4B files?</h3>
            <a href={`${ROOT}/kev4b_linear_probes.ipynb`} download>Notebook <ArrowRight /></a>
            <a href={`${KEV}/run_manifest.json`}>Run manifest <ArrowRight /></a>
            <a href={`${KEV}/frozen_selection.json`}>Frozen settings <ArrowRight /></a>
            <a href={`${KEV}/validation_search.csv`}>Validation search table <ArrowRight /></a>
            <a href={`${KEV}/test_metrics_with_intervals.csv`}>Test metrics <ArrowRight /></a>
            <a href={`${KEV}/paired_probe_minus_tuned_native.json`}>Paired probe comparison <ArrowRight /></a>
          </div>
        </div>
        <Link href="/reproduce" className="inline-flex min-h-11 w-fit items-center gap-1.5 text-[14px]">Read the benchmark method <ArrowRight /></Link>
      </section>
    </article>
  );
}

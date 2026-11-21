import type { Metadata } from "next";
import Link from "next/link";
import { pageOpenGraph, pageTwitter } from "@/lib/og";
import { AccuracyChart, GainChart, MistakesChart } from "./charts";
import { STUDY } from "./data";
import { LayerSweepChart } from "./layer-sweep";
import { ProbeMap } from "./probe-map";
import { StudySetup } from "./study-diagrams";
import { AuthorLink } from "@/components/author-link";

const path = "/research/linear-probe";
export const metadata: Metadata = {
  title: "Linear probes on Strands and Kev",
  description:
    "A linear probe reading Strands Decider 2B's internal signals caught 29 more violations and blocked 17 fewer safe requests than the model's own score, on 540 held-out requests. Kev 4B's gain was small and uncertain.",
  alternates: { canonical: path },
  openGraph: { ...pageOpenGraph(path), type: "article" },
  twitter: pageTwitter(),
};

const systems = [
  { name: "Strands Decider 2B", dir: path, notebook: "raxit_decision_model_linear_probes.ipynb" },
  { name: "Kev 4B", dir: path + "/kev-4b", notebook: "kev4b_linear_probes.ipynb" },
];
const files = [
  ["Validation by layer", "validation-layer-sweep.png"],
  ["Activation map (PCA)", "train-fitted-pca.png"],
  ["Test ROC and accuracy", "held-out-roc-and-accuracy.png"],
  ["Test metrics", "test_metrics_with_intervals.csv"],
  ["Paired comparison", "paired_probe_minus_tuned_native.json"],
  ["Validation search", "validation_search.csv"],
  ["Selected settings", "frozen_selection.json"],
  ["Run manifest", "run_manifest.json"],
];

const h2 = "text-[clamp(1.45rem,3vw,2rem)] font-semibold leading-tight tracking-[-0.035em] text-balance";
// One centred reading column for text; figures break out to a wider centred measure.
const col = "mx-auto w-full max-w-[44rem]";
const wide = "mx-auto w-full max-w-[66rem]";
const prose = col + " space-y-4 text-[17px] leading-[1.7] text-fg-2";
const pct = (v: number) => (v * 100).toFixed(1) + "%";
const pts = (v: number) => (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(1);
const S = STUDY.strands;
const K = STUDY.kev;

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-8">
      <h2 id={id} className={col + " border-t border-line-strong pt-8 " + h2}>{title}</h2>
      {children}
    </section>
  );
}

export default function LinearProbeResearch() {
  return (
    <article className="mx-auto flex max-w-[1200px] flex-col gap-12 px-4 pt-6 pb-8 sm:gap-16 sm:px-6 sm:pt-14">
      <header className="flex flex-col gap-10">
        <div className={col + " text-center"}>
          <Link href="/research" className="inline-flex min-h-10 items-center text-sm">← Research</Link>
          <p className="mt-4 mb-2 text-sm text-muted">
            14 October 2026 · Study by{" "}
            <AuthorLink name="Aditya Shrivastava" href="https://www.linkedin.com/in/aditya-shrivastava-1966b0265" />, AI safety researcher
          </p>
          <h1 className="text-balance text-[clamp(2rem,5vw,3.2rem)] font-semibold leading-[1.05] tracking-[-0.035em]">
            Linear probes on Strands and Kev
          </h1>
          <p className="mx-auto mt-4 max-w-[60ch] text-[18px] leading-relaxed text-fg-2">
            Does a guardrail model know more than its answer says? Aditya froze two of them, read the signals inside, and
            trained a small classifier on those signals with 89 examples. On Strands it fixed most of the model’s mistakes.
            On Kev, which was already close to perfect, it changed little.
          </p>
        </div>

        <dl className={wide + " grid border-y text-center border-line-strong sm:grid-cols-3 sm:divide-x sm:divide-line-strong"}>
          <div className="py-4 sm:px-6">
            <dt className="text-sm text-muted">Strands Decider 2B, balanced accuracy</dt>
            <dd className="m-0 mt-1">
              <span className="num text-[28px] font-semibold tracking-tight">
                {pct(S.arms.tuned.ba)} <span className="text-muted">→</span>{" "}
                <span className="text-accent">{pct(S.arms.probe.ba)}</span>
              </span>
              <span className="num block text-sm text-fg-2">
                {pts(S.gain.probe.diff)} points, 95% interval {pts(S.gain.probe.low)} to {pts(S.gain.probe.high)}
              </span>
            </dd>
          </div>
          <div className="border-t border-line py-4 sm:border-t-0 sm:px-6">
            <dt className="text-sm text-muted">Kev 4B, balanced accuracy</dt>
            <dd className="m-0 mt-1">
              <span className="num text-[28px] font-semibold tracking-tight">
                {pct(K.arms.tuned.ba)} <span className="text-muted">→</span> {pct(K.arms.probe.ba)}
              </span>
              <span className="num block text-sm text-fg-2">{pts(K.gain.probe.diff)} points, interval includes zero</span>
            </dd>
          </div>
          <div className="border-t border-line py-4 sm:border-t-0 sm:px-6">
            <dt className="text-sm text-muted">Held-out test set</dt>
            <dd className="m-0 mt-1">
              <span className="num text-[28px] font-semibold tracking-tight">540 requests</span>
              <span className="block text-sm text-fg-2">8 denied topics, unseen in training and tuning</span>
            </dd>
          </div>
        </dl>
      </header>

      <Section id="takeaway" title="What this means if you run an open model">
        <div className={prose}>
          <p>
            You can get a better decision out of an open guardrail model without retraining it. Keep the model frozen, label
            about 120 requests for your own policy (89 to train the probe, 29 to pick the layer and cutoff), and let a linear
            probe read one of the model’s middle layers. On Strands that cut missed violations from 42 to 13 and wrongly
            blocked requests from 20 to 3. Kev was already close to perfect, and the probe made little difference there.
          </p>
          <p>
            The probe is a weighted sum over one layer’s numbers, which is cheap next to running the model itself. It needs
            the model’s weights, so it won’t work on a hosted API, and it only knows the policy it was trained on.
          </p>
        </div>
      </Section>

      <Section id="what" title="Reading the model instead of its answer">
        <div className={prose}>
          <p>
            A guardrail model reads a request and gives a score: how likely it is that the request breaks the policy. On
            the way to that score, every layer of the model turns the request into a long list of numbers. A{" "}
            <strong className="font-semibold text-fg">linear probe</strong> takes the list from one layer, gives each number
            a weight, adds them up, and blocks the request if the total passes a cutoff. The model never changes. Only the
            weights are learned.
          </p>
          <p>
            Guillaume Alain and Yoshua Bengio, who introduced probes in 2016, compared them to thermometers placed at
            different points of a machine that keeps running as usual. (<a href="https://arxiv.org/abs/1610.01644">Their
            paper</a>.) Inside one layer, each request becomes a point in a space with thousands of directions. A linear
            probe is a single straight cut through that space. Requests on one side get blocked.
          </p>
        </div>
        <div className={wide}><ProbeMap /></div>
        <div className={prose}>
          <p>
            In the first layer, violations and their look-alikes sit mixed together, and no straight cut separates them.
            Deeper in, they drift apart, and by the middle of the model a probe sorts every validation request correctly.
            Aditya took the earliest layer that did: 11 for Strands, 15 for Kev. Fig 2 shows every probe type at every
            sampled layer. Later layers tie with the chosen one, so validation alone can’t pick a winner. That is what the
            test set is for.
          </p>
        </div>
        <div className={wide}><LayerSweepChart /></div>
      </Section>

      <Section id="setup" title="One request, two ways to score it">
        <div className={prose}>
          <p>
            Take a service that blocks investment advice. Someone asks, <em>“Which stock should I buy?”</em> The right
            answer is block. Both scorers see the same request inside the same frozen model, and each gets its own cutoff.
          </p>
        </div>
        <div className={wide}><StudySetup /></div>
        <div className={prose}>
          <p>
            Each of the eight denied topics, such as investment advice, medical diagnosis and academic dishonesty, has 32
            requests to block and 32 look-alikes to allow in the test set. Another 28 requests touch none of the topics.
            Both cutoffs were fixed on the 29 validation requests before the test set was scored.
          </p>
        </div>
      </Section>

      <Section id="results" title="Strands made fewer mistakes of both kinds">
        <div className={wide}><MistakesChart /></div>
        <div className={prose}>
          <p>
            Strands’s own score missed 42 of 256 violations. The probe missed 13. It also blocked 3 safe requests, where the
            built-in score blocked 20. Improving on both sides at once is the important part. A new cutoff only trades one
            mistake for the other. The probe found a cleaner signal.
          </p>
          <p>
            Kev’s own score already caught 255 of 256 violations. Its probe blocked 13 fewer safe requests and missed two
            more violations. Whether that trade is worth it depends on which mistake costs you more.
          </p>
        </div>
      </Section>

      <Section id="checks" title="Is the gain real?">
        <div className={prose}>
          <p>
            Two controls rule out the easy explanations. If the probe only picked up the wording of the requests, a
            classifier that reads the words alone should do as well. It reaches {pct(S.arms.text.ba)}. If the probe were
            memorising noise, training it on shuffled labels should still work. It falls to {pct(S.arms.shuffled.ba)},
            below chance.
          </p>
        </div>
        <div className={wide}><AccuracyChart /></div>
        <div className={wide}><GainChart /></div>
        <div className={prose}>
          <p>
            Every test request was scored by both rules, so the comparison is paired. For Strands the gain is{" "}
            {pts(S.gain.probe.diff)} points, and the whole interval sits above zero. For Kev it is {pts(K.gain.probe.diff)}{" "}
            points, with an interval that touches zero. A simpler mass-mean probe, which compares the average signal of
            block and allow examples, did not clearly beat either model’s own score.
          </p>
        </div>
      </Section>

      <Section id="limits" title="What this does not show">
        <div className={prose}>
          <p>
            All 540 test requests come from the benchmark’s AI-assisted authored set. The other 61 test requests, written by
            real OpenAssistant users, had no readable text in this release and were left out. The result holds for
            authored requests. How a probe does on real traffic is still open.
          </p>
          <p>
            The policy questions stayed the same from training to test, so a probe trained on these eight topics says
            nothing about a new policy. The score also doesn’t explain why Strands’s answer lost information its middle
            layers still held.
          </p>
          <p>
            A probe needs the model’s weights. It works for open models you run yourself, like these two, and can’t be
            added to a hosted API. The <Link href="/">leaderboard</Link> scores every system at a fixed 0.5 cutoff and
            doesn’t include probes.
          </p>
        </div>
      </Section>

      <Section id="runs" title="Check the work">
        <div className={prose}>
          <p>
            Each notebook ran on one T4 GPU and starts in a short smoke mode. Every number on this page comes from the
            files below.
          </p>
        </div>
        <div className={col + " grid gap-x-10 gap-y-6 sm:grid-cols-2"}>
          {systems.map((system) => (
            <div key={system.name} className="border-t border-line py-4">
              <h3 className="mb-2 text-lg font-semibold">{system.name}</h3>
              <a href={path + "/" + system.notebook} download className="inline-flex min-h-11 items-center font-medium">
                Download notebook ↓<span className="sr-only"> for {system.name}</span>
              </a>
              <ul className="mt-2 divide-y divide-line border-y border-line">
                {files.map(([label, file]) => (
                  <li key={file}>
                    <a href={system.dir + "/" + file} className="flex min-h-11 items-center justify-between gap-4 py-2 text-sm">
                      <span>
                        {label}
                        <span className="sr-only"> for {system.name}</span>
                      </span>
                      <span className="num text-xs text-muted">{file.split(".").pop()?.toUpperCase()}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>
    </article>
  );
}

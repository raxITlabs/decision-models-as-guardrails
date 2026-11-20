import type { Metadata } from "next";
import Link from "next/link";
import { pageOpenGraph, pageTwitter } from "@/lib/og";

const path = "/research/linear-probe";
export const metadata: Metadata = {
  title: "Linear probes on Strands and Kev",
  description: "A linear probe caught 29 more violations in Strands. On the same prompts, Kev caught fewer violations but blocked fewer safe requests.",
  alternates: { canonical: path },
  openGraph: { ...pageOpenGraph(path), type: "article" },
  twitter: pageTwitter(),
};

// Counts from the published test metrics, on 256 block rows and 284 allow rows.
const systems = [
  { name: "Strands Decider 2B", dir: path, notebook: "raxit_decision_model_linear_probes.ipynb",
    builtIn: { missed: 42, falseBlocks: 20 }, probe: { missed: 13, falseBlocks: 3 } },
  { name: "Kev 4B", dir: path + "/kev-4b", notebook: "kev4b_linear_probes.ipynb",
    builtIn: { missed: 1, falseBlocks: 19 }, probe: { missed: 3, falseBlocks: 6 } },
];
const files = [
  ["Validation by layer", "validation-layer-sweep.png"], ["Activation map (PCA)", "train-fitted-pca.png"],
  ["Test ROC and accuracy", "held-out-roc-and-accuracy.png"], ["Test metrics", "test_metrics_with_intervals.csv"],
  ["Paired comparison", "paired_probe_minus_tuned_native.json"], ["Validation search", "validation_search.csv"],
  ["Selected settings", "frozen_selection.json"], ["Run manifest", "run_manifest.json"],
];
const heading = "text-[clamp(1.45rem,3vw,2rem)] font-semibold tracking-[-0.035em] leading-tight";
const copy = "max-w-[68ch] text-[16px] leading-relaxed text-fg-2";

function ErrorChart({ metric, title, denominator }: {
  metric: "missed" | "falseBlocks"; title: string; denominator: string;
}) {
  return (
    <figure className="m-0 min-w-0 py-6 sm:px-7">
      <figcaption className="mb-5">
        <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
        <p className="text-sm text-muted">{denominator}</p>
      </figcaption>
      {systems.map(system => {
        const native = system.builtIn[metric];
        const probe = system.probe[metric];
        const change = probe - native;
        return (
          <div key={system.name} className="mb-5">
            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3">
              <h4 className="text-sm font-semibold">{system.name}</h4>
              <span className={`num text-xs ${change > 0 ? "text-warn" : "text-good"}`}>
                {Math.abs(change)} {change > 0 ? "more" : "fewer"} with probe
              </span>
            </div>
            <dl className="m-0">
              {([["Built-in score", native], ["Linear probe", probe]] as const).map(([label, value]) => (
                <div key={label} className="grid grid-cols-[6rem_1fr_2ch] items-center gap-3 py-1 text-[13px]">
                  <dt>{label}</dt>
                  <dd className="col-span-2 grid grid-cols-subgrid items-center">
                    <span aria-hidden="true" className="block h-3 border-l border-line-strong bg-raised">
                      <span className={label === "Linear probe" ? "block h-full bg-fg" : "block h-full bg-muted"} style={{ width: (value / 50 * 100) + "%" }} />
                    </span>
                    <span className="num text-right">{value}<span className="sr-only"> {title.toLowerCase()} for {system.name}</span></span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        );
      })}
      <div aria-hidden="true" className="grid grid-cols-[6rem_1fr_2ch] items-baseline gap-3 text-xs text-muted">
        <span>Rows</span>
        <div className="num flex justify-between border-t border-line-strong pt-1"><span>0</span><span>25</span><span>50</span></div>
      </div>
    </figure>
  );
}

export default function LinearProbeResearch() {
  return (
    <article className="mx-auto flex max-w-[1200px] flex-col gap-9 px-4 pt-6 sm:gap-12 sm:px-6 sm:pt-16">
      <header className="max-w-[840px]">
        <Link href="/research" className="text-sm">← Research</Link>
        <p className="mt-4 mb-2 text-sm text-muted">14 October 2026 · Community study by Aditya Shrivastava</p>
        <h1 className="text-balance text-[clamp(2rem,5vw,3rem)] leading-[1.05] font-semibold tracking-[-0.03em]">Linear probes on Strands and Kev</h1>
        <p className="mt-3 max-w-[68ch] text-[17px] leading-relaxed text-fg-2">
          A linear probe reads signals inside a model to decide which prompts to block. On 540 denied-topic prompts it caught 29 more violations than Strands’s own score and blocked 17 fewer safe prompts. Kev’s own score already caught 255 of 256 violations.
        </p>
      </header>

      <section aria-labelledby="errors">
        <h2 id="errors" className={heading}>Where each guardrail made mistakes</h2>
        <p className="mt-2 mb-5 text-sm text-muted">The study tuned both cutoffs on 29 labelled prompts. The <Link href="/">leaderboard</Link> uses a fixed cutoff of 0.5.</p>
        <div className="grid border-y border-line-strong bg-surface px-3 sm:grid-cols-2 sm:divide-x sm:divide-line-strong sm:px-0">
          <ErrorChart metric="missed" title="Violations missed" denominator="Of 256 prompts the policy says to block" />
          <ErrorChart metric="falseBlocks" title="Safe prompts blocked" denominator="Of 284 prompts the policy allows" />
        </div>
        <p className={copy + " mt-4"}>For Kev, the probe let 13 more safe prompts through and missed two more violations. Its overall gain is uncertain.</p>
      </section>

      <section className="grid gap-4 border-t border-line-strong pt-6 md:grid-cols-[1fr_2fr] md:gap-12">
        <h2 className={heading}>How a linear probe works</h2>
        <div className={copy + " space-y-4"}>
          <p>As a model reads a prompt, each layer produces a list of numbers. A linear probe gives each number a weight, adds up the weighted values and uses a cutoff to decide whether to block. The model itself stays frozen.</p>
          <p>The study fitted those weights on 89 labelled prompts. On 29 more, it chose which layer to read and where to set the cutoff. Strands’s selected layer was block 11 and Kev’s was block 15, counting from zero. Both used the signals at the answer position, averaged across nine policy questions.</p>
          <p>For comparison, each model also answered those nine questions with its built-in score. The highest answer determined whether to block. Both rules were fixed before the 540 test prompts were scored.</p>
        </div>
      </section>

      <section className="grid gap-4 border-t border-line-strong pt-6 md:grid-cols-[1fr_2fr] md:gap-12">
        <h2 className={heading}>How much did the score change?</h2>
        <div className={copy + " space-y-4"}>
          <p>Balanced accuracy gives equal weight to catching violations and allowing safe prompts. Strands went from <strong className="num">88.3%</strong> with its tuned built-in score to <strong className="num">96.9%</strong> with the probe. The estimated gain was 8.7 percentage points, with a 95% interval of 6.2 to 11.5 points.</p>
          <p>Kev went from <strong className="num">96.5%</strong> to <strong className="num">98.4%</strong>. Its interval ran from −0.04 to +3.7 points, which includes zero. Both intervals come from resampling groups of related test prompts 500 times.</p>
          <p>At the leaderboard’s fixed 0.5 cutoff, Strands missed 12 violations and blocked 70 safe prompts. Kev missed none and blocked 35 safe prompts. The <Link href="/">leaderboard</Link> uses that fixed rule across several tasks.</p>
        </div>
      </section>

      <section className="grid gap-4 border-t border-line-strong pt-6 md:grid-cols-[1fr_2fr] md:gap-12">
        <h2 className={heading}>Which prompts did this cover?</h2>
        <div className={copy + " space-y-4"}>
          <p>All 540 test prompts came from the benchmark’s AI-assisted authored set. The other 61 test prompts came from real OpenAssistant users and lacked readable text in this release. The experiment therefore leaves performance on real-user prompts open.</p>
          <p>The same policy questions were used throughout. A probe can pick up patterns in how the examples were written. Its score alone cannot tell us why Strands’s built-in decisions differed, or how either model would handle a new policy.</p>
        </div>
      </section>

      <section className="border-t border-line-strong pt-6">
        <h2 className={heading}>Inspect the runs</h2>
        <p className={copy + " mt-3"}>Each notebook includes the training code and policy-question setup. The original figures show how the layers scored on validation, how the test scores changed across cutoffs, and how the activations looked in two dimensions.</p>
        <div className="mt-5 grid gap-6 sm:grid-cols-2">
          {systems.map(system => <div key={system.name} className="border-t border-line py-4">
            <h3 className="mb-2 text-lg font-semibold">{system.name}</h3>
            <a href={path + "/" + system.notebook} download className="inline-flex min-h-11 items-center font-medium">Download notebook ↓<span className="sr-only"> for {system.name}</span></a>
            <ul className="mt-2 divide-y divide-line border-y border-line">
              {files.map(([label, file]) => (
                <li key={file}>
                  <a href={system.dir + "/" + file} className="flex min-h-11 items-center justify-between gap-4 py-2 text-sm">
                    <span>{label}<span className="sr-only"> for {system.name}</span></span>
                    <span className="num text-xs text-muted">{file.split(".").pop()?.toUpperCase()}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>)}
        </div>
      </section>
    </article>
  );
}

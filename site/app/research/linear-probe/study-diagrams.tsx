// Fig 3: how the study was run. Left, where each score reads the model. Right, where the 658 requests went.

const DEPTH = 24; // Strands Decider 2B
const TAP = 11; // the layer the Strands probe reads

const SPLITS = [
  { key: "train", count: 89, title: "Train", text: "The probe learns its weights", fill: "var(--fg)" },
  { key: "choose", count: 29, title: "Choose", text: "Pick the layer and both cutoffs", fill: "var(--accent)" },
  { key: "test", count: 540, title: "Test", text: "Both rules fixed; count mistakes", fill: "none" },
] as const;
const COLS = 47; // 47 × 14 = 658, one dot per request
const ROWS = 14;

function Track() {
  // A score from 0 to 1 with a cutoff; the block side is tinted. Schematic: no values are implied.
  return (
    <div className="mt-2 flex items-center gap-2 text-[11px] text-muted">
      <span>allow</span>
      <div className="relative h-2 flex-1 rounded-full bg-line">
        <div className="absolute inset-y-0 right-0 left-[62%] rounded-r-full bg-accent/15" />
        <div className="absolute -top-1 left-[62%] h-4 w-px bg-fg" />
      </div>
      <span className="font-medium text-fg">block</span>
    </div>
  );
}

function ScorePaths() {
  return (
    <div className="flex min-w-0 flex-col">
      <p className="m-0 mb-1 text-sm font-semibold text-fg">One request, two readings</p>
      <p className="m-0 mb-4 text-xs text-muted">
        Same request, same frozen model, read in two different places.
      </p>

      <p className="m-0 mb-2 text-[11px] text-muted">
        Strands Decider 2B, frozen · {DEPTH} layers · <span className="inline-block size-2 rounded-[1px] bg-fg align-baseline" aria-hidden="true" /> last layer ·{" "}
        <span className="inline-block size-2 rounded-[1px] bg-accent align-baseline" aria-hidden="true" /> layer {TAP}
      </p>
      <div className="flex items-center gap-2">
        <span className="shrink-0 rounded-[3px] border border-line-strong px-2 py-1 text-xs text-fg-2">Request</span>
        <div className="relative flex-1">
          <div className="flex h-10 items-end gap-[2px]" aria-hidden="true">
            {Array.from({ length: DEPTH }, (_, i) => (
              <div
                key={i}
                className={"flex-1 rounded-[1px] " + (i === TAP ? "h-10 bg-accent" : i === DEPTH - 1 ? "h-10 bg-fg" : "h-7 bg-line-strong")}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-[3px] border border-line bg-bg/40 p-3">
          <p className="m-0 flex items-center gap-1.5 text-sm font-semibold text-fg">
            <span className="inline-block size-2 rounded-[1px] bg-fg" aria-hidden="true" />
            Built-in score
          </p>
          <p className="m-0 mt-1 text-xs leading-relaxed text-fg-2">
            Reads the model’s answer at the last layer: it asks nine policy questions and keeps the highest score.
          </p>
          <Track />
        </div>
        <div className="rounded-[3px] border border-accent/40 bg-selected/60 p-3">
          <p className="m-0 flex items-center gap-1.5 text-sm font-semibold text-fg">
            <span className="inline-block size-2 rounded-[1px] bg-accent" aria-hidden="true" />
            Linear probe
          </p>
          <p className="m-0 mt-1 text-xs leading-relaxed text-fg-2">
            Reads layer {TAP} directly: multiplies each signal by a learned weight and adds them up.
          </p>
          <Track />
        </div>
      </div>
      <p className="m-0 mt-3 text-xs text-muted">Each path gets its own cutoff, chosen on validation. At or above it means block.</p>
    </div>
  );
}

function StudySplit() {
  let n = 0;
  const dots = SPLITS.flatMap((s) => Array.from({ length: s.count }, () => ({ s, i: n++ })));
  return (
    <div className="flex min-w-0 flex-col">
      <p className="m-0 mb-1 text-sm font-semibold text-fg">Where the 658 requests went</p>
      <p className="m-0 mb-4 text-xs text-muted">One dot per request. Related requests stayed in the same split.</p>
      <svg viewBox={`0 0 ${COLS * 8} ${ROWS * 8}`} className="block h-auto w-full" role="img" aria-label="658 requests: 89 train, 29 choose, 540 test.">
        {dots.map(({ s, i }) => {
          const cx = (i % COLS) * 8 + 4;
          const cy = Math.floor(i / COLS) * 8 + 4;
          return s.fill === "none" ? (
            <circle key={i} cx={cx} cy={cy} r={2.4} fill="none" stroke="var(--muted)" strokeWidth={1} />
          ) : (
            <circle key={i} cx={cx} cy={cy} r={2.8} fill={s.fill} />
          );
        })}
      </svg>
      <ol className="m-0 mt-4 grid list-none grid-cols-3 gap-3 p-0">
        {SPLITS.map((s) => (
          <li key={s.key} className="border-t border-line-strong pt-2">
            <p className="m-0 flex items-center gap-1.5 text-sm font-semibold text-fg">
              <svg width="10" height="10" aria-hidden="true">
                {s.fill === "none" ? (
                  <circle cx="5" cy="5" r="3.6" fill="none" stroke="var(--muted)" strokeWidth="1.2" />
                ) : (
                  <circle cx="5" cy="5" r="4" fill={s.fill} />
                )}
              </svg>
              {s.title} <span className="num font-normal text-fg-2">{s.count}</span>
            </p>
            <p className="m-0 mt-1 text-xs leading-snug text-fg-2">{s.text}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function StudySetup() {
  return (
    <figure className="m-0">
      <div className="rounded-[4px] border border-line-strong bg-surface px-4 pt-3 pb-5 sm:px-5">
        <div className="mb-4 flex justify-between gap-4 text-xs text-muted">
          <span className="num">Fig 3</span>
          <span className="text-right">How the study was run</span>
        </div>
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:gap-10">
          <ScorePaths />
          <StudySplit />
        </div>
      </div>
      <figcaption className="mx-auto mt-3 max-w-[44rem] text-sm leading-relaxed text-muted">
        Shown for Strands; Kev is set up the same way, with 32 layers and the probe on layer 15. The score tracks are
        schematic. The split counts come from the run manifests.
      </figcaption>
    </figure>
  );
}

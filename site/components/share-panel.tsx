"use client";

import { forwardRef, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { SHARE_SIZES, SHARE_SIZE_IDS, type ShareSize, type ShareView, isShareView, shareDownloadName, shareLink, shareSrc } from "../lib/share";
import { Segmented } from "./segmented";

/** The use case named by ``?case=`` in a query string, if it is one the board has. */
export function caseFromSearch(search: string): ShareView | null {
  const v = new URLSearchParams(search).get("case");
  return isShareView(v) ? v : null;
}

/** The name a downloaded image is saved under: decision-models-as-guardrails-overall-landscape-2026-10-20.png */
export const downloadName = (view: ShareView, size: ShareSize, date: string) => shareDownloadName(view, size, date);

const noSubscribe = () => () => {};

/** The ``?case=`` view the page was opened with. null on the server and during hydration, so the HTML matches. */
export function useCaseParam(): ShareView | null {
  return useSyncExternalStore(
    noSubscribe,
    () => caseFromSearch(window.location.search),
    () => null,
  );
}

const useCanCopyImage = () =>
  useSyncExternalStore(
    noSubscribe,
    () => typeof ClipboardItem !== "undefined" && !!navigator.clipboard?.write,
    () => false,
  );

/** The quiet word that opens the panel, in the style of the "N more" toggle beside it. */
export const ShareTrigger = forwardRef<HTMLButtonElement, { open: boolean; controls: string; onToggle: () => void }>(
  function ShareTrigger({ open, controls, onToggle }, ref) {
    return (
      <button
        ref={ref}
        type="button"
        aria-expanded={open}
        aria-controls={controls}
        onClick={onToggle}
        className="group ml-auto inline-flex min-h-11 items-center gap-1.5 text-[14px] text-muted transition-colors hover:text-fg motion-reduce:transition-none"
      >
        <svg viewBox="0 0 16 16" aria-hidden="true" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 10V2.5M5 5.5l3-3 3 3M3.5 8.5v4a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1v-4" />
        </svg>
        <span className="underline decoration-line-strong underline-offset-[3px] group-hover:decoration-fg">Share</span>
      </button>
    );
  },
);

const action =
  "inline-flex min-h-11 items-center text-[14px] text-fg underline decoration-line-strong underline-offset-[3px] transition-colors hover:decoration-fg motion-reduce:transition-none";

/** The share image for the current view: a preview, three sizes, and download, copy and share actions. Inline under
 *  the use-case row, on the paper, divided by a hairline. Escape closes it. */
export function SharePanel({
  id,
  view,
  viewLabel,
  altFor,
  date,
  onClose,
}: {
  id: string;
  view: ShareView;
  viewLabel: string;
  /** the image's text equivalent for a size */
  altFor: (size: ShareSize) => string;
  /** the release date, for the download's file name */
  date: string;
  onClose: () => void;
}) {
  const [size, setSize] = useState<ShareSize>("landscape");
  const [note, setNote] = useState("");
  const [file, setFile] = useState<{ src: string; file: File } | null>(null);
  const canCopy = useCanCopyImage();
  const root = useRef<HTMLDivElement>(null);
  const src = shareSrc(view, size);
  // Downloads, copies and shares use the 2x file: feeds show it sharp on high-density screens.
  const hi = shareSrc(view, size, 2);
  const dims = SHARE_SIZES[size];
  const name = downloadName(view, size, date);

  // Fetch the PNG ahead of a click, so the system share sheet opens inside the click's user activation.
  useEffect(() => {
    if (typeof navigator.canShare !== "function") return;
    let live = true;
    fetch(hi)
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(String(r.status)))))
      .then((b) => {
        const f = new File([b], name, { type: "image/png" });
        if (live && navigator.canShare?.({ files: [f] })) setFile({ src, file: f });
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [src, hi, name]);
  const shareable = file?.src === src ? file.file : null;

  useEffect(() => {
    root.current?.focus({ preventScroll: true });
  }, []);

  const copyImage = async () => {
    try {
      // A promise inside the item keeps Safari's user activation while the PNG loads.
      const blob = fetch(hi).then((r) => (r.ok ? r.blob() : Promise.reject(new Error(String(r.status)))));
      await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
      setNote("Image copied");
    } catch {
      setNote("Could not copy the image. Use Download PNG instead.");
    }
  };
  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareLink(view));
      setNote("Link copied");
    } catch {
      setNote(`Could not copy the link. It is ${shareLink(view)}`);
    }
  };
  const copyAlt = async () => {
    try {
      await navigator.clipboard.writeText(altFor(size));
      setNote("Alt text copied. Paste it into the image description when you post.");
    } catch {
      setNote("Could not copy the alt text.");
    }
  };
  const share = async () => {
    if (!shareable) return;
    try {
      await navigator.share({ files: [shareable], title: `${viewLabel} · raxIT guardrail benchmark`, url: shareLink(view) });
    } catch (e) {
      if ((e as Error)?.name !== "AbortError") setNote("Could not open sharing. Use Download PNG instead.");
    }
  };

  return (
    <div
      id={id}
      ref={root}
      tabIndex={-1}
      role="region"
      aria-label="Share image"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          onClose();
        }
      }}
      className="-mt-6 grid min-w-0 gap-x-10 gap-y-5 border-b border-line-strong py-6 outline-none md:grid-cols-[minmax(0,1fr)_17rem]"
    >
      <div className="min-w-0">
        {/* eslint-disable-next-line @next/next/no-img-element -- a static PNG at its own size; the download is this file */}
        <img
          key={src}
          src={src}
          width={dims.width}
          height={dims.height}
          alt={altFor(size)}
          className={`block h-auto w-full border border-line bg-surface ${size === "landscape" ? "" : "max-w-[440px]"}`}
        />
      </div>
      <div className="flex min-w-0 flex-col gap-4">
        <p className="m-0 text-[14px] leading-relaxed text-muted">
          The top systems and their 95% intervals, as an image for a post or a slide.
        </p>
        <div className="flex flex-col gap-1">
          <Segmented
            label="Image size"
            value={size}
            onChange={(s) => {
              setSize(s);
              setNote("");
            }}
            options={SHARE_SIZE_IDS.map((s) => ({ value: s, label: SHARE_SIZES[s].label }))}
          />
          <p className="m-0 text-[13px] text-muted">
            <span className="font-mono">
              {dims.width} × {dims.height}
            </span>{" "}
            · {dims.hint.split(" · ").slice(1).join(" · ")}
          </p>
        </div>
        <div className="flex flex-wrap gap-x-5 border-t border-line pt-2">
          <a href={hi} download={name} className={action}>
            Download PNG
          </a>
          {canCopy && (
            <button type="button" onClick={copyImage} className={action}>
              Copy image
            </button>
          )}
          <button type="button" onClick={copyLink} className={action}>
            Copy link
          </button>
          <button type="button" onClick={copyAlt} className={action}>
            Copy alt text
          </button>
          {shareable && (
            <button type="button" onClick={share} className={action}>
              Share…
            </button>
          )}
        </div>
        <p aria-live="polite" className="m-0 min-h-5 break-words text-[13px] text-muted">
          {note}
        </p>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { External } from "./icons";

export const CONTACT_URL = "https://raxitlabs.com/contact-us";

/** A link that opens raxIT Labs' contact page in a pop-up over this page. Without JavaScript it is a plain link to
 *  that page. The page loads only when the pop-up opens. The dialog is portalled to <body>, so the link can sit inside
 *  a paragraph without nesting a dialog in it. */
export function ContactLink({
  children,
  className,
  onOpen,
  onClose,
}: {
  children: React.ReactNode;
  className?: string;
  onOpen?: () => void;
  onClose?: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- portal target exists only on the client
  useEffect(() => setMounted(true), []);
  return (
    <>
      <a
        href={CONTACT_URL}
        onClick={(e) => {
          if (e.metaKey || e.ctrlKey || e.shiftKey) return;
          e.preventDefault();
          setOpen(true);
          dialog.current?.showModal();
          onOpen?.();
        }}
        className={className}
      >
        {children}
      </a>
      {mounted &&
        createPortal(
      <dialog
        ref={dialog}
        aria-label="Contact raxIT Labs"
        onClose={() => {
          setOpen(false);
          onClose?.();
        }}
        onClick={(e) => {
          if (e.target === dialog.current) dialog.current?.close();
        }}
        className="contact-dialog m-auto h-[min(860px,calc(100dvh-32px))] w-[min(960px,calc(100vw-32px))] max-w-none overflow-hidden border border-line-strong bg-bg p-0 text-fg backdrop:bg-[rgb(var(--smoky)/0.55)] max-sm:h-dvh max-sm:max-h-none max-sm:w-screen max-sm:border-0"
      >
        <div className="flex h-full flex-col">
          <div className="flex min-h-14 items-center justify-between gap-4 border-b border-line px-4 sm:px-5">
            <span className="text-[15px] font-medium">Contact raxIT Labs</span>
            <span className="flex items-center gap-5 text-[14px]">
              <a href={CONTACT_URL} target="_blank" rel="noopener" className="inline-flex min-h-11 items-center gap-1">
                Open in a new tab <External className="size-3" />
              </a>
              <button
                type="button"
                autoFocus
                onClick={() => dialog.current?.close()}
                className="inline-flex min-h-11 items-center font-medium text-fg underline decoration-line-strong underline-offset-4 hover:decoration-fg"
              >
                Close
              </button>
            </span>
          </div>
          {open && <iframe src={CONTACT_URL} title="raxIT Labs contact form" className="min-h-0 w-full flex-1 border-0 bg-bg" />}
        </div>
      </dialog>,
          document.body,
        )}
    </>
  );
}

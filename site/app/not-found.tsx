import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Page not found", robots: { index: false } };

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-[820px] flex-col gap-4 px-4 pt-20 sm:px-6">
      <h1 className="m-0 text-[32px] font-semibold tracking-[-0.02em]">Page not found</h1>
      <p className="m-0 text-[16px] text-fg-2">
        No page or public row has that address. We never list rows from the held-back slice.
      </p>
      <p className="m-0 flex gap-4 text-[15px]">
        <Link href="/" prefetch={false} className="inline-flex min-h-11 items-center">Results</Link>
        <Link href="/data" className="inline-flex min-h-11 items-center">Browse the data</Link>
      </p>
    </div>
  );
}

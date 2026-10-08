"use client";

import { useEffect } from "react";

/** Opens the <details> inside the element with this id when the page is opened at, or moves to, its #hash. */
export function HashOpen({ id }: { id: string }) {
  useEffect(() => {
    const open = () => {
      if (window.location.hash !== `#${id}`) return;
      const d = document.getElementById(id)?.querySelector("details");
      if (d && !d.open) d.open = true;
    };
    open();
    window.addEventListener("hashchange", open);
    return () => window.removeEventListener("hashchange", open);
  }, [id]);
  return null;
}

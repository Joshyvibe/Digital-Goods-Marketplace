"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-lg flex-1 flex-col items-start justify-center gap-4 px-4">
      <p className="text-sm font-semibold tracking-[0.2em] text-muted uppercase">Error</p>
      <h1 className="text-4xl font-black tracking-tight uppercase">Something went wrong</h1>
      <p className="text-muted">
        That wasn&rsquo;t supposed to happen. You can try again, or head back to the shop.
      </p>
      <div className="mt-2 flex gap-3">
        <button
          onClick={reset}
          className="rounded-full bg-ink px-6 py-3 font-semibold text-paper transition hover:bg-ink/85"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded-full border border-line px-6 py-3 font-semibold transition hover:border-ink"
        >
          Back to shop
        </Link>
      </div>
    </main>
  );
}

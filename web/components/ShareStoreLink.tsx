"use client";

import { useState } from "react";

export function ShareStoreLink({ slug }: { slug: string }) {
  const [copied, setCopied] = useState(false);
  const url = typeof window !== "undefined" ? `${window.location.origin}/store/${slug}` : `/store/${slug}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard permission denied or unavailable — the URL is still shown as plain
      // text below, so the vendor can just select and copy it manually.
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-muted">Your public store link</span>
      <div className="flex items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded-lg border border-line bg-paper-muted px-3 py-1.5 text-sm">
          {url}
        </code>
        <button
          onClick={handleCopy}
          className="shrink-0 rounded-full border border-line px-3 py-1.5 text-xs font-semibold transition hover:border-ink"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
    </div>
  );
}

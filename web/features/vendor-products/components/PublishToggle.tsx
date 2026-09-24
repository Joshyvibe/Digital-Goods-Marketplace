"use client";

import { Archive, CheckCircle2, Circle, Loader2 } from "lucide-react";
import { useState } from "react";
import { FormError } from "@/components/ui/FormError";
import { ApiError } from "@/types/api";
import { updateProduct } from "../api";
import type { VendorProduct } from "../types";

const STATUS_STYLES: Record<VendorProduct["status"], string> = {
  draft: "bg-paper-muted text-ink/70",
  published: "bg-accent text-accent-ink",
  archived: "bg-ink/10 text-ink/50",
};

const STATUS_ICONS: Record<VendorProduct["status"], typeof CheckCircle2> = {
  draft: Circle,
  published: CheckCircle2,
  archived: Archive,
};

export function PublishToggle({
  product,
  onSaved,
}: {
  product: VendorProduct;
  onSaved: (product: VendorProduct) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const setStatus = async (status: VendorProduct["status"]) => {
    setError(null);
    setIsSaving(true);
    try {
      const updated = await updateProduct(product.id, { status });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update status.");
    } finally {
      setIsSaving(false);
    }
  };

  const StatusIcon = STATUS_ICONS[product.status];

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <span
          className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[product.status]}`}
        >
          {isSaving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2.2} />
          ) : (
            <StatusIcon className="h-3.5 w-3.5" strokeWidth={2.2} />
          )}
          {product.status}
        </span>
        {product.status !== "published" && (
          <button
            onClick={() => setStatus("published")}
            disabled={isSaving}
            className="text-sm font-semibold underline underline-offset-2 disabled:opacity-50"
          >
            Publish
          </button>
        )}
        {product.status === "published" && (
          <button
            onClick={() => setStatus("archived")}
            disabled={isSaving}
            className="text-sm font-semibold underline underline-offset-2 disabled:opacity-50"
          >
            Archive
          </button>
        )}
      </div>
      <FormError message={error} />
    </div>
  );
}

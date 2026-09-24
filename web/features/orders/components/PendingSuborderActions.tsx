"use client";

import { Loader2, RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { FormError } from "@/components/ui/FormError";
import { startPendingCheckout } from "@/features/checkout/pendingCheckout";
import { ApiError } from "@/types/api";
import { cancelPendingSuborder, retrySuborderCheckout } from "../api";

interface PendingSuborderActionsProps {
  orderId: number;
  suborderId: number;
  onCancelled: () => void;
}

export function PendingSuborderActions({ orderId, suborderId, onCancelled }: PendingSuborderActionsProps) {
  const [isRetrying, setIsRetrying] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRetry = async () => {
    setError(null);
    setIsRetrying(true);
    try {
      const { checkout_urls } = await retrySuborderCheckout(orderId, suborderId);
      startPendingCheckout(orderId, checkout_urls);
      window.location.href = checkout_urls[0];
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not restart checkout.");
      setIsRetrying(false);
    }
  };

  const handleCancel = async () => {
    setError(null);
    setIsCancelling(true);
    try {
      await cancelPendingSuborder(orderId, suborderId);
      onCancelled();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not cancel this item.");
      setIsCancelling(false);
    }
  };

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-line pt-3">
      <div className="flex gap-2">
        <button
          onClick={handleRetry}
          disabled={isRetrying || isCancelling}
          className="flex items-center gap-1.5 rounded-full bg-ink px-4 py-1.5 text-xs font-semibold text-paper transition hover:bg-ink/85 disabled:opacity-50"
        >
          {isRetrying ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2.5} />
          ) : (
            <RotateCcw className="h-3.5 w-3.5" strokeWidth={2.2} />
          )}
          {isRetrying ? "Redirecting…" : "Retry payment"}
        </button>
        <button
          onClick={handleCancel}
          disabled={isRetrying || isCancelling}
          className="flex items-center gap-1.5 rounded-full border border-line px-4 py-1.5 text-xs font-semibold transition hover:border-red-300 hover:text-red-600 disabled:opacity-50"
        >
          {isCancelling ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2.5} />
          ) : (
            <Trash2 className="h-3.5 w-3.5" strokeWidth={1.8} />
          )}
          {isCancelling ? "Cancelling…" : "Cancel"}
        </button>
      </div>
      <FormError message={error} />
    </div>
  );
}

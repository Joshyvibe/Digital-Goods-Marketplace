"use client";

import { AlertTriangle, CheckCircle2, Loader2, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { motion } from "motion/react";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { ApiError } from "@/types/api";

export function DeleteAccountSection({ isVendor }: { isVendor: boolean }) {
  const { deleteAccount } = useAuth();
  const [isConfirming, setIsConfirming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<"deleted" | "deactivated" | null>(null);

  if (outcome) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="rounded-2xl border border-line bg-paper-muted p-6"
      >
        <p className="flex items-center gap-2 font-semibold">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" strokeWidth={2} />
          Your account has been removed.
        </p>
        <p className="mt-1 text-sm text-muted">
          {outcome === "deleted"
            ? "Nothing was left behind — the account is fully deleted."
            : "You've been signed out and your email removed. Your past orders" +
              (isVendor ? " and sales" : "") +
              " are kept on record so other people's purchases and downloads stay intact."}
        </p>
        <Link
          href="/"
          className="mt-4 inline-block rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper"
        >
          Back to shop
        </Link>
      </motion.div>
    );
  }

  if (!isConfirming) {
    return (
      <button
        onClick={() => setIsConfirming(true)}
        className="flex items-center gap-1.5 self-start text-sm font-semibold text-red-600 hover:underline"
      >
        <Trash2 className="h-4 w-4" strokeWidth={1.8} />
        Delete account
      </button>
    );
  }

  const handleConfirm = async () => {
    setError(null);
    setIsDeleting(true);
    try {
      const result = await deleteAccount();
      setOutcome(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete your account.");
      setIsDeleting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-red-200 bg-red-50 p-5"
    >
      <p className="flex items-center gap-2 font-semibold text-red-800">
        <AlertTriangle className="h-4 w-4" strokeWidth={2.2} />
        Delete your account?
      </p>
      <p className="mt-1 text-sm text-red-700">
        This can&rsquo;t be undone. If you have no past orders{isVendor ? " or sales" : ""}, your
        account is removed entirely. Otherwise it&rsquo;s deactivated and your email erased, but
        order records are kept so other people&rsquo;s purchases stay valid.
      </p>
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      <div className="mt-4 flex gap-3">
        <button
          onClick={handleConfirm}
          disabled={isDeleting}
          className="flex items-center gap-2 rounded-full bg-red-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
        >
          {isDeleting && <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />}
          {isDeleting ? "Deleting…" : "Yes, delete my account"}
        </button>
        <button
          onClick={() => setIsConfirming(false)}
          disabled={isDeleting}
          className="rounded-full border border-line px-5 py-2 text-sm font-semibold transition hover:border-ink"
        >
          Cancel
        </button>
      </div>
    </motion.div>
  );
}

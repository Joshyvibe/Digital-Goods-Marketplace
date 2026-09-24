"use client";

import { useState } from "react";
import { updateStoreName } from "@/features/vendor-onboarding/api";
import type { VendorProfile } from "@/features/vendor-onboarding/types";
import { ApiError } from "@/types/api";

export function StoreNameEditor({
  vendor,
  onSaved,
}: {
  vendor: VendorProfile;
  onSaved: (vendor: VendorProfile) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(vendor.store_name);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  if (!isEditing) {
    return (
      <div className="flex items-center gap-2">
        <p className="font-semibold">{vendor.store_name}</p>
        <button
          onClick={() => {
            setName(vendor.store_name);
            setError(null);
            setIsEditing(true);
          }}
          className="text-xs font-semibold text-muted underline underline-offset-2 hover:text-ink"
        >
          Rename
        </button>
      </div>
    );
  }

  const handleSave = async () => {
    setError(null);
    setIsSaving(true);
    try {
      const updated = await updateStoreName(name);
      onSaved(updated);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not rename your store.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded-lg border border-line px-3 py-1.5 text-sm outline-none focus:border-ink focus:ring-2 focus:ring-accent/40"
        />
        <button
          onClick={handleSave}
          disabled={isSaving || !name.trim()}
          className="rounded-full bg-ink px-3 py-1.5 text-xs font-semibold text-paper disabled:opacity-50"
        >
          {isSaving ? "Saving…" : "Save"}
        </button>
        <button
          onClick={() => setIsEditing(false)}
          disabled={isSaving}
          className="text-xs font-semibold text-muted hover:text-ink"
        >
          Cancel
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

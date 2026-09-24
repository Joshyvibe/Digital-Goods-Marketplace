"use client";

import { ImageIcon, ImageUp, Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { FormError } from "@/components/ui/FormError";
import { uploadCoverImage } from "../api";
import type { VendorProduct } from "../types";

export function CoverImageUploader({
  product,
  onSaved,
}: {
  product: VendorProduct;
  onSaved: (product: VendorProduct) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setError(null);
    setIsUploading(true);
    try {
      const updated = await uploadCoverImage(product.id, file);
      onSaved(updated);
    } catch {
      setError("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-4">
      <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-xl border border-line bg-paper-muted">
        {product.cover_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element -- private, presigned R2 URL; next/image's remote-host allowlist doesn't fit a per-object signed URL
          <img src={product.cover_image_url} alt="" className="h-full w-full object-cover" />
        ) : (
          <ImageIcon className="h-6 w-6 text-muted" strokeWidth={1.5} />
        )}
      </div>
      <div className="flex flex-col gap-2">
        <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
          className="flex items-center gap-2 self-start rounded-full border border-line px-5 py-2 text-sm font-semibold transition hover:border-ink disabled:opacity-50"
        >
          {isUploading ? (
            <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.2} />
          ) : (
            <ImageUp className="h-4 w-4" strokeWidth={2} />
          )}
          {isUploading ? "Uploading…" : "Upload cover image"}
        </button>
        <FormError message={error} />
      </div>
    </div>
  );
}

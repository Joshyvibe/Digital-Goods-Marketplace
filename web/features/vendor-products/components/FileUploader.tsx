"use client";

import { File as FileIcon, Loader2, Trash2, Upload } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { FormError } from "@/components/ui/FormError";
import { deleteFile, uploadProductFile } from "../api";
import type { ProductFile, VendorProduct } from "../types";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileUploader({
  product,
  onChange,
}: {
  product: VendorProduct;
  onChange: (files: ProductFile[]) => void;
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
      const newFile = await uploadProductFile(product.id, file);
      onChange([...product.files, newFile]);
    } catch {
      setError("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (fileId: number) => {
    setError(null);
    try {
      await deleteFile(product.id, fileId);
      onChange(product.files.filter((f) => f.id !== fileId));
    } catch {
      setError("Could not remove that file.");
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {product.files.length > 0 && (
        <ul className="flex flex-col gap-2">
          <AnimatePresence initial={false}>
            {product.files.map((file) => (
              <motion.li
                key={file.id}
                layout
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center justify-between rounded-xl border border-line px-4 py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <FileIcon className="h-4 w-4 shrink-0 text-muted" strokeWidth={1.8} />
                  <div>
                    <p className="text-sm font-medium">{file.original_filename}</p>
                    <p className="text-xs text-muted">{formatBytes(file.byte_size)}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(file.id)}
                  className="flex items-center gap-1 text-sm text-red-600 hover:underline"
                >
                  <Trash2 className="h-3.5 w-3.5" strokeWidth={1.8} />
                  Remove
                </button>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}

      <FormError message={error} />

      <input ref={inputRef} type="file" className="hidden" onChange={handleFileChange} />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="flex items-center gap-2 self-start rounded-full border border-line px-5 py-2 text-sm font-semibold transition hover:border-ink disabled:opacity-50"
      >
        {isUploading ? (
          <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.2} />
        ) : (
          <Upload className="h-4 w-4" strokeWidth={2} />
        )}
        {isUploading ? "Uploading…" : "Upload a file"}
      </button>
    </div>
  );
}

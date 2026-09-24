"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { FormError } from "@/components/ui/FormError";
import { ApiError } from "@/types/api";
import { createProduct, updateProduct } from "../api";
import type { ProductCategory, VendorProduct } from "../types";

const CATEGORIES: { value: ProductCategory; label: string }[] = [
  { value: "template", label: "Template" },
  { value: "preset", label: "Preset" },
  { value: "ebook", label: "Ebook" },
  { value: "license", label: "License" },
  { value: "stock", label: "Stock Asset" },
];

interface ProductFormProps {
  product?: VendorProduct;
  /** Edit mode only — lets the parent update its own state instead of relying on the
   * child to trigger a refetch it has no way to observe. */
  onSaved?: (product: VendorProduct) => void;
}

export function ProductForm({ product, onSaved }: ProductFormProps) {
  const router = useRouter();
  const [title, setTitle] = useState(product?.title ?? "");
  const [description, setDescription] = useState(product?.description ?? "");
  const [category, setCategory] = useState<ProductCategory>(product?.category ?? "template");
  const [price, setPrice] = useState(product ? (product.price_cents / 100).toFixed(2) : "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const priceCents = Math.round(parseFloat(price || "0") * 100);

    try {
      if (product) {
        const updated = await updateProduct(product.id, {
          title,
          description,
          category,
          price_cents: priceCents,
        });
        onSaved?.(updated);
      } else {
        const created = await createProduct({ title, description, category, price_cents: priceCents });
        router.push(`/vendor/products/${created.id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-ink/80">Title</span>
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="rounded-xl border border-line px-4 py-2.5 outline-none transition focus:border-ink focus:ring-2 focus:ring-accent/40"
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-ink/80">Description</span>
        <textarea
          required
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="rounded-xl border border-line px-4 py-2.5 outline-none transition focus:border-ink focus:ring-2 focus:ring-accent/40"
        />
      </label>
      <div className="grid grid-cols-2 gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-ink/80">Category</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as ProductCategory)}
            className="rounded-xl border border-line px-4 py-2.5 outline-none transition focus:border-ink focus:ring-2 focus:ring-accent/40"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-ink/80">Price (USD)</span>
          <input
            required
            type="number"
            min="0"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="rounded-xl border border-line px-4 py-2.5 outline-none transition focus:border-ink focus:ring-2 focus:ring-accent/40"
          />
        </label>
      </div>
      <FormError message={error} />
      <button
        type="submit"
        disabled={isSubmitting}
        className="flex items-center gap-2 self-start rounded-full bg-ink px-6 py-2.5 font-semibold text-paper transition hover:bg-ink/85 disabled:opacity-50"
      >
        {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />}
        {isSubmitting ? "Saving…" : product ? "Save changes" : "Create product"}
      </button>
    </form>
  );
}

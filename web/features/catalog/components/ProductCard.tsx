import { BookOpen, Image as ImageIcon, KeyRound, LayoutTemplate, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import type { Product } from "../types";

const CATEGORY_GRADIENTS: Record<string, string> = {
  template: "from-[#d4ff4f] to-[#a6d92a]",
  preset: "from-[#ffd4e5] to-[#ff9fc2]",
  ebook: "from-[#c9e4ff] to-[#8fc2ff]",
  license: "from-[#e5d4ff] to-[#c29fff]",
  stock: "from-[#ffe8c9] to-[#ffc27a]",
};

const CATEGORY_ICONS = {
  template: LayoutTemplate,
  preset: SlidersHorizontal,
  ebook: BookOpen,
  license: KeyRound,
  stock: ImageIcon,
} as const;

const CATEGORY_LABELS: Record<string, string> = {
  template: "Template",
  preset: "Preset",
  ebook: "Ebook",
  license: "License",
  stock: "Stock Asset",
};

function formatPrice(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(
    cents / 100
  );
}

export function ProductCard({ product }: { product: Product }) {
  const gradient = CATEGORY_GRADIENTS[product.category] ?? "from-paper-muted to-line";
  const CategoryIcon =
    CATEGORY_ICONS[product.category as keyof typeof CATEGORY_ICONS] ?? LayoutTemplate;

  return (
    <Link
      href={`/products/${product.slug}`}
      className="group flex flex-col overflow-hidden rounded-2xl border border-line bg-paper transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-ink/5"
    >
      <div
        className={`relative flex aspect-square items-center justify-center overflow-hidden bg-gradient-to-br ${gradient}`}
      >
        {product.cover_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element -- private, presigned R2 URL; next/image's remote-host allowlist doesn't fit a per-object signed URL
          <img
            src={product.cover_image_url}
            alt=""
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <CategoryIcon
            className="h-16 w-16 text-ink/15 transition-transform duration-500 group-hover:scale-110"
            strokeWidth={1.5}
          />
        )}
        <span className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-paper/90 px-3 py-1 text-xs font-semibold text-ink backdrop-blur-sm">
          <CategoryIcon className="h-3.5 w-3.5" strokeWidth={2.2} />
          {CATEGORY_LABELS[product.category] ?? product.category}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-1 p-4">
        <p className="text-xs font-medium text-muted">{product.vendor_store_name}</p>
        <h3 className="font-semibold text-ink transition group-hover:underline">{product.title}</h3>
        <div className="mt-auto flex items-center justify-between pt-2">
          <span className="font-bold text-ink">{formatPrice(product.price_cents, product.currency)}</span>
          <span className="flex items-center gap-1 text-sm text-muted transition group-hover:translate-x-0.5 group-hover:text-ink">
            View <span aria-hidden>→</span>
          </span>
        </div>
      </div>
    </Link>
  );
}

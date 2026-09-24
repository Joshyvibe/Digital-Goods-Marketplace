import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BookOpen, Image as ImageIcon, KeyRound, LayoutTemplate, SlidersHorizontal } from "lucide-react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { getProduct } from "@/features/catalog/api";
import { AddToCartButton } from "@/features/cart/components/AddToCartButton";
import { ApiError } from "@/types/api";

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

function formatPrice(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(
    cents / 100
  );
}

async function loadProduct(slug: string) {
  return getProduct(slug).catch((err) => {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  });
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const product = await loadProduct(slug);
  return { title: product ? `${product.title} — Marketplace` : "Product not found" };
}

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const product = await loadProduct(slug);

  if (!product) notFound();

  const gradient = CATEGORY_GRADIENTS[product.category] ?? "from-paper-muted to-line";
  const CategoryIcon =
    CATEGORY_ICONS[product.category as keyof typeof CATEGORY_ICONS] ?? LayoutTemplate;

  return (
    <>
      <SiteHeader />
      <main className="mx-auto grid w-full max-w-5xl flex-1 animate-[fadeIn_0.4s_ease-out] gap-12 px-4 py-16 sm:grid-cols-2">
        <div
          className={`flex aspect-square items-center justify-center overflow-hidden rounded-3xl bg-gradient-to-br ${gradient}`}
        >
          {product.cover_image_url ? (
            // eslint-disable-next-line @next/next/no-img-element -- private, presigned R2 URL; next/image's remote-host allowlist doesn't fit a per-object signed URL
            <img src={product.cover_image_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <CategoryIcon className="h-24 w-24 text-ink/15" strokeWidth={1.25} />
          )}
        </div>

        <div className="flex flex-col gap-6">
          <div>
            <Link
              href={`/store/${product.vendor_slug}`}
              className="text-sm font-medium text-muted hover:text-ink hover:underline"
            >
              {product.vendor_store_name}
            </Link>
            <h1 className="mt-1 text-3xl font-black tracking-tight">{product.title}</h1>
          </div>
          <p className="text-2xl font-bold text-ink">
            {formatPrice(product.price_cents, product.currency)}
          </p>
          <p className="text-ink/80">{product.description}</p>
          <AddToCartButton productId={product.id} />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}

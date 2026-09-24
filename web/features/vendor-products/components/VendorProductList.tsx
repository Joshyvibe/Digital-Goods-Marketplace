import { Archive, CheckCircle2, Circle, PackagePlus, PackageSearch } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
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

const container = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } };

function formatPrice(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(
    cents / 100
  );
}

export function VendorProductList({ products }: { products: VendorProduct[] }) {
  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line p-12 text-center">
        <PackageSearch className="h-8 w-8 text-muted" strokeWidth={1.5} />
        <p className="text-muted">No products yet.</p>
        <Link
          href="/vendor/products/new"
          className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper transition hover:bg-ink/85"
        >
          <PackagePlus className="h-4 w-4" strokeWidth={2.2} />
          Create your first product
        </Link>
      </div>
    );
  }

  return (
    <motion.ul variants={container} initial="hidden" animate="show" className="flex flex-col gap-3">
      {products.map((product) => {
        const StatusIcon = STATUS_ICONS[product.status];
        return (
          <motion.li key={product.id} variants={item}>
            <Link
              href={`/vendor/products/${product.id}`}
              className="flex items-center justify-between rounded-2xl border border-line px-5 py-4 transition hover:border-ink hover:shadow-sm"
            >
              <div>
                <p className="font-semibold">{product.title}</p>
                <p className="text-sm text-muted">
                  {formatPrice(product.price_cents, product.currency)} · {product.files.length} file
                  {product.files.length === 1 ? "" : "s"}
                </p>
              </div>
              <span
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[product.status]}`}
              >
                <StatusIcon className="h-3.5 w-3.5" strokeWidth={2.2} />
                {product.status}
              </span>
            </Link>
          </motion.li>
        );
      })}
    </motion.ul>
  );
}

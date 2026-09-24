"use client";

import {
  CheckCircle2,
  Clock,
  Coins,
  PackageSearch,
  Receipt,
  RotateCcw,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { VendorOnlyNotice } from "@/components/ui/VendorOnlyNotice";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import type { SuborderStatus } from "@/features/orders/types";
import { getVendorSales } from "../api";
import type { VendorSalesResponse } from "../types";

function formatPrice(cents: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "usd" }).format(cents / 100);
}

const STATUS_STYLES: Record<SuborderStatus, string> = {
  pending: "bg-paper-muted text-ink/70",
  paid: "bg-accent text-accent-ink",
  failed: "bg-red-100 text-red-700",
  refunded: "bg-ink/10 text-ink/50",
};

const STATUS_ICONS: Record<SuborderStatus, typeof CheckCircle2> = {
  pending: Clock,
  paid: CheckCircle2,
  failed: XCircle,
  refunded: RotateCcw,
};

const container = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } };

export function VendorSalesPageContent() {
  const { user, isLoading: authLoading } = useAuth();
  const [data, setData] = useState<VendorSalesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user || !user.is_vendor) return;
    getVendorSales()
      .then(setData)
      .catch(() => setError("Could not load your sales."));
  }, [authLoading, user]);

  if (authLoading) return <Spinner label="Loading your sales…" />;
  if (!user?.is_vendor) return <VendorOnlyNotice />;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <Spinner label="Loading your sales…" />;

  const { summary, sales } = data;

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="flex items-center gap-3 rounded-2xl border border-line p-5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/60">
            <Coins className="h-5 w-5 text-ink" strokeWidth={2} />
          </span>
          <div>
            <p className="text-sm text-muted">Total earned</p>
            <p className="text-xl font-bold">{formatPrice(summary.total_earned_cents)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-2xl border border-line p-5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-paper-muted">
            <TrendingUp className="h-5 w-5 text-ink" strokeWidth={2} />
          </span>
          <div>
            <p className="text-sm text-muted">Completed sales</p>
            <p className="text-xl font-bold">{summary.total_sales}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-2xl border border-line p-5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-paper-muted">
            <Clock className="h-5 w-5 text-ink" strokeWidth={2} />
          </span>
          <div>
            <p className="text-sm text-muted">Pending checkouts</p>
            <p className="text-xl font-bold">{summary.pending_count}</p>
          </div>
        </div>
      </div>

      {sales.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line p-12 text-center">
          <PackageSearch className="h-8 w-8 text-muted" strokeWidth={1.5} />
          <p className="text-muted">No sales yet — share your store link to get your first one.</p>
        </div>
      ) : (
        <motion.ul variants={container} initial="hidden" animate="show" className="flex flex-col gap-3">
          {sales.map((sale) => {
            const StatusIcon = STATUS_ICONS[sale.status];
            return (
              <motion.li key={sale.id} variants={item} className="rounded-2xl border border-line p-5">
                <div className="flex items-center justify-between">
                  <p className="flex items-center gap-2 font-semibold">
                    <Receipt className="h-4 w-4 text-muted" strokeWidth={2} />
                    Order #{sale.order_id}
                  </p>
                  <span
                    className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[sale.status]}`}
                  >
                    <StatusIcon className="h-3.5 w-3.5" strokeWidth={2.2} />
                    {sale.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-muted">{sale.buyer_email}</p>
                <ul className="mt-3 flex flex-col gap-1 text-sm text-ink/80">
                  {sale.line_items.map((li) => (
                    <li key={li.id} className="flex justify-between">
                      <span>{li.product_title_snapshot}</span>
                      <span>{formatPrice(li.unit_price_cents)}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 flex items-center justify-between border-t border-line pt-3 text-sm">
                  <span className="text-muted">
                    Subtotal {formatPrice(sale.subtotal_cents)} &minus; fee {formatPrice(sale.platform_fee_cents)}
                  </span>
                  <span className="font-semibold">
                    {sale.status === "paid"
                      ? `You earned ${formatPrice(sale.net_cents)}`
                      : sale.status === "pending"
                        ? "Checkout not completed"
                        : `Not paid out — ${sale.status}`}
                  </span>
                </div>
              </motion.li>
            );
          })}
        </motion.ul>
      )}
    </div>
  );
}

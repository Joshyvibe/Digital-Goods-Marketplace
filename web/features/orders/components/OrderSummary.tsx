import { CheckCircle2, Clock, RotateCcw, Store, XCircle } from "lucide-react";
import type { Order, SuborderStatus } from "../types";
import { DownloadList } from "./DownloadList";
import { PendingSuborderActions } from "./PendingSuborderActions";

function formatPrice(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(
    cents / 100
  );
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

interface OrderSummaryProps {
  order: Order;
  /** Shows Retry/Cancel on a pending suborder. Off by default — the immediate post-checkout
   * return page can show a "pending" status that's just the webhook still catching up on a
   * real payment, and offering to cancel it there would be actively dangerous. Only the
   * standalone order pages, visited well after that race has settled, opt in. */
  interactive?: boolean;
  onOrderChanged?: () => void;
}

export function OrderSummary({ order, interactive = false, onOrderChanged }: OrderSummaryProps) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted">Order #{order.id}</p>
          <p className="text-2xl font-bold">{formatPrice(order.total_cents, order.currency)}</p>
        </div>
        <span className="rounded-full bg-paper-muted px-3 py-1 text-xs font-semibold text-ink/70">
          {order.status.replace("_", " ")}
        </span>
      </div>

      <div className="flex flex-col gap-4">
        {order.suborders.map((suborder) => {
          const StatusIcon = STATUS_ICONS[suborder.status];
          return (
            <div key={suborder.id} className="rounded-2xl border border-line p-5">
              <div className="mb-3 flex items-center justify-between">
                <p className="flex items-center gap-2 font-semibold">
                  <Store className="h-4 w-4 text-muted" strokeWidth={2} />
                  {suborder.vendor_store_name}
                </p>
                <span
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[suborder.status]}`}
                >
                  <StatusIcon className="h-3.5 w-3.5" strokeWidth={2.2} />
                  {suborder.status}
                </span>
              </div>
              <ul className="flex flex-col gap-1 text-sm text-ink/80">
                {suborder.line_items.map((item) => (
                  <li key={item.id} className="flex justify-between">
                    <span>{item.product_title_snapshot}</span>
                    <span>{formatPrice(item.unit_price_cents, order.currency)}</span>
                  </li>
                ))}
              </ul>
              {interactive && suborder.status === "pending" && (
                <PendingSuborderActions
                  orderId={order.id}
                  suborderId={suborder.id}
                  onCancelled={() => onOrderChanged?.()}
                />
              )}
            </div>
          );
        })}
      </div>

      {(order.status === "paid" || order.status === "partially_paid") && (
        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold tracking-wide text-muted uppercase">Your downloads</h2>
          <DownloadList orderId={order.id} />
        </div>
      )}
    </div>
  );
}

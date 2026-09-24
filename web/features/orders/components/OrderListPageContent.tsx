"use client";

import { PackageSearch, Receipt } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import type { Paginated } from "@/types/api";
import type { Order } from "../types";

function formatPrice(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(
    cents / 100
  );
}

function itemsSummary(order: Order) {
  const titles = order.suborders.flatMap((suborder) =>
    suborder.line_items.map((item) => item.product_title_snapshot)
  );
  return titles.join(", ");
}

export function OrderListPageContent() {
  const { user, isLoading: authLoading } = useAuth();
  const [orders, setOrders] = useState<Order[] | null>(null);

  useEffect(() => {
    if (authLoading || !user) return;
    apiFetch<Paginated<Order>>("/api/orders/").then((data) => setOrders(data.results));
  }, [authLoading, user]);

  if (authLoading) return <Spinner />;

  if (!user) {
    return (
      <p className="text-muted">
        <Link href="/login" className="font-semibold text-ink underline underline-offset-2">
          Sign in
        </Link>{" "}
        to see your orders.
      </p>
    );
  }

  if (!orders) return <Spinner label="Loading your orders…" />;

  if (orders.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line p-12 text-center">
        <PackageSearch className="h-8 w-8 text-muted" strokeWidth={1.5} />
        <p className="text-muted">No orders yet.</p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {orders.map((order) => (
        <li key={order.id}>
          <Link
            href={`/orders/${order.id}`}
            className="flex items-center justify-between rounded-2xl border border-line px-5 py-4 transition hover:border-ink hover:shadow-sm"
          >
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-paper-muted">
                <Receipt className="h-4 w-4 text-muted" strokeWidth={2} />
              </span>
              <div>
                <p className="font-semibold">{itemsSummary(order) || `Order #${order.id}`}</p>
                <p className="text-sm text-muted">
                  Order #{order.id} · {new Date(order.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="font-semibold">{formatPrice(order.total_cents, order.currency)}</p>
              <p className="text-sm text-muted">{order.status.replace("_", " ")}</p>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

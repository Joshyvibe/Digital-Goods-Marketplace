"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useCart } from "@/features/cart/hooks/CartContext";
import { getOrder } from "@/features/orders/api";
import { OrderSummary } from "@/features/orders/components/OrderSummary";
import type { Order } from "@/features/orders/types";
import { advancePendingCheckout } from "../pendingCheckout";

export function CheckoutReturnFlow() {
  const router = useRouter();
  const { refresh: refreshCart } = useCart();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasAdvanced = useRef(false);

  useEffect(() => {
    if (hasAdvanced.current) return;
    hasAdvanced.current = true;

    // Routed through a microtask so every setState call below happens in a callback, not
    // synchronously in the effect body itself (react-hooks/set-state-in-effect).
    Promise.resolve().then(() => {
      const pending = advancePendingCheckout();
      if (!pending) {
        setError("No checkout in progress.");
        return;
      }

      if (pending.nextUrl) {
        window.location.href = pending.nextUrl;
        return;
      }

      // Sequence complete — every suborder's Checkout Session has been visited. Webhook
      // processing may still be catching up, so this fetch reflects whatever's landed so
      // far; the orders page can be revisited later for the settled state.
      refreshCart();
      getOrder(pending.orderId)
        .then(setOrder)
        .catch(() => setError("Could not load your order."));
    });
  }, [refreshCart]);

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-red-600">{error}</p>
        <button
          onClick={() => router.push("/cart")}
          className="self-start rounded-full bg-ink px-6 py-2.5 font-semibold text-paper"
        >
          Back to cart
        </button>
      </div>
    );
  }

  if (!order) {
    return <p className="text-muted">Finishing up…</p>;
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-black tracking-tight uppercase">Thanks for your order</h1>
        <p className="mt-2 text-muted">
          A confirmation is on its way. Downloads will be available on your order page once
          payment is confirmed.
        </p>
      </div>
      <OrderSummary order={order} />
    </div>
  );
}

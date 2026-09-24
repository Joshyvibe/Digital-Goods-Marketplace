"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { getOrder } from "../api";
import type { Order } from "../types";
import { OrderSummary } from "./OrderSummary";

export function OrderDetailPageContent({ orderId }: { orderId: number }) {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    // A cancel can delete the order entirely (it was the only pending suborder), so a
    // refetch here can legitimately 404 — that means "gone", not "failed to load".
    getOrder(orderId)
      .then(setOrder)
      .catch(() => router.push("/orders"));
  }, [orderId, router]);

  useEffect(() => {
    if (authLoading || !user) return;
    getOrder(orderId)
      .then(setOrder)
      .catch(() => setError("Could not load this order."));
  }, [authLoading, user, orderId]);

  if (authLoading || (!order && !error)) {
    return <Spinner label="Loading order…" />;
  }

  if (error || !order) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  return <OrderSummary order={order} interactive onOrderChanged={refresh} />;
}

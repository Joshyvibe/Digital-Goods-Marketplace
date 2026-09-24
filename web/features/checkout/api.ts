import { apiFetch } from "@/lib/apiClient";

export interface CheckoutResponse {
  order_id: number;
  checkout_urls: string[];
}

export async function startCheckout(): Promise<CheckoutResponse> {
  return apiFetch("/api/orders/checkout/", { body: {} });
}

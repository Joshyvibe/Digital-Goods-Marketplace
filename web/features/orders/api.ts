import { apiFetch } from "@/lib/apiClient";
import type { DownloadItem, Order } from "./types";

export async function getOrder(id: number): Promise<Order> {
  return apiFetch(`/api/orders/${id}/`);
}

export async function getOrderDownloads(id: number): Promise<DownloadItem[]> {
  return apiFetch(`/api/orders/${id}/downloads/`);
}

export async function retrySuborderCheckout(
  orderId: number,
  suborderId: number
): Promise<{ checkout_urls: string[] }> {
  return apiFetch(`/api/orders/${orderId}/suborders/${suborderId}/retry/`, { body: {} });
}

export async function cancelPendingSuborder(orderId: number, suborderId: number): Promise<void> {
  await apiFetch(`/api/orders/${orderId}/suborders/${suborderId}/`, { method: "DELETE" });
}

import { apiFetch } from "@/lib/apiClient";
import type { VendorSalesResponse } from "./types";

export async function getVendorSales(): Promise<VendorSalesResponse> {
  return apiFetch("/api/vendors/sales/");
}

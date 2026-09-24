import type { OrderLineItem, SuborderStatus } from "@/features/orders/types";

export interface VendorSale {
  id: number;
  order_id: number;
  buyer_email: string;
  status: SuborderStatus;
  subtotal_cents: number;
  platform_fee_cents: number;
  net_cents: number;
  created_at: string;
  paid_at: string | null;
  line_items: OrderLineItem[];
}

export interface VendorSalesSummary {
  total_earned_cents: number;
  total_sales: number;
  pending_count: number;
}

export interface VendorSalesResponse {
  summary: VendorSalesSummary;
  sales: VendorSale[];
}

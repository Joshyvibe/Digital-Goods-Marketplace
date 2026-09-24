export type OrderStatus = "pending" | "paid" | "partially_paid" | "failed" | "refunded";
export type SuborderStatus = "pending" | "paid" | "failed" | "refunded";

export interface OrderLineItem {
  id: number;
  product_title_snapshot: string;
  unit_price_cents: number;
}

export interface VendorSuborder {
  id: number;
  vendor_store_name: string;
  subtotal_cents: number;
  status: SuborderStatus;
  paid_at: string | null;
  line_items: OrderLineItem[];
}

export interface Order {
  id: number;
  status: OrderStatus;
  total_cents: number;
  currency: string;
  created_at: string;
  suborders: VendorSuborder[];
}

export interface DownloadFile {
  filename: string;
  download_url: string;
}

export interface DownloadItem {
  product_title: string;
  status: SuborderStatus;
  files: DownloadFile[];
}

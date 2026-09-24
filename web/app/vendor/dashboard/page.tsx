import { redirect } from "next/navigation";

// Superseded by /account (store status) + /vendor/products (management) — kept as a
// redirect so an old bookmark or typed URL doesn't land on a dead page.
export default function VendorDashboardPage() {
  redirect("/vendor/products");
}

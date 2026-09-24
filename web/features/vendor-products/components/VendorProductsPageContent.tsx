"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ShareStoreLink } from "@/components/ShareStoreLink";
import { Spinner } from "@/components/ui/Spinner";
import { VendorOnlyNotice } from "@/components/ui/VendorOnlyNotice";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { getOnboardingStatus } from "@/features/vendor-onboarding/api";
import type { VendorProfile } from "@/features/vendor-onboarding/types";
import { listMyProducts } from "../api";
import type { VendorProduct } from "../types";
import { VendorProductList } from "./VendorProductList";

export function VendorProductsPageContent() {
  const { user, isLoading: authLoading } = useAuth();
  const [products, setProducts] = useState<VendorProduct[] | null>(null);
  const [vendor, setVendor] = useState<VendorProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user || !user.is_vendor) return;
    listMyProducts()
      .then((data) => setProducts(data.results))
      .catch(() => setError("Could not load your products."));
    getOnboardingStatus()
      .then(setVendor)
      .catch(() => {});
  }, [authLoading, user]);

  if (authLoading) {
    return <Spinner label="Loading your products…" />;
  }

  if (!user?.is_vendor) {
    return <VendorOnlyNotice />;
  }

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  if (!products) {
    return <Spinner label="Loading your products…" />;
  }

  return (
    <div className="flex flex-col gap-6">
      {vendor && (
        <div className="rounded-2xl border border-line p-4">
          <ShareStoreLink slug={vendor.slug} />
        </div>
      )}
      <div className="flex items-center justify-between">
        <p className="text-muted">{products.length} products</p>
        <Link
          href="/vendor/products/new"
          className="flex items-center gap-1.5 rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper transition hover:bg-ink/85"
        >
          <Plus className="h-4 w-4" strokeWidth={2.2} />
          New product
        </Link>
      </div>
      <VendorProductList products={products} />
    </div>
  );
}

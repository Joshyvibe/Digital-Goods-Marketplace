"use client";

import { ImageIcon, ListChecks, Package } from "lucide-react";
import { useEffect, useState } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { VendorOnlyNotice } from "@/components/ui/VendorOnlyNotice";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { getMyProduct } from "../api";
import type { ProductFile, VendorProduct } from "../types";
import { CoverImageUploader } from "./CoverImageUploader";
import { FileUploader } from "./FileUploader";
import { ProductForm } from "./ProductForm";
import { PublishToggle } from "./PublishToggle";

export function ProductEditPageContent({ productId }: { productId: number }) {
  const { user, isLoading: authLoading } = useAuth();
  const [product, setProduct] = useState<VendorProduct | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user || !user.is_vendor) return;
    getMyProduct(productId)
      .then(setProduct)
      .catch(() => setError("Could not load this product."));
  }, [authLoading, user, productId]);

  if (authLoading) {
    return <Spinner label="Loading product…" />;
  }

  if (!user?.is_vendor) {
    return <VendorOnlyNotice />;
  }

  if (error || !product) {
    return error ? <p className="text-sm text-red-600">{error}</p> : <Spinner label="Loading product…" />;
  }

  const handleFilesChange = (files: ProductFile[]) => setProduct({ ...product, files });

  return (
    <div className="flex flex-col gap-10">
      <PublishToggle product={product} onSaved={setProduct} />

      <section className="flex flex-col gap-3">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold tracking-wide text-muted uppercase">
          <ImageIcon className="h-3.5 w-3.5" strokeWidth={2.2} />
          Cover image
        </h2>
        <CoverImageUploader product={product} onSaved={setProduct} />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold tracking-wide text-muted uppercase">
          <Package className="h-3.5 w-3.5" strokeWidth={2.2} />
          Files
        </h2>
        <FileUploader product={product} onChange={handleFilesChange} />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold tracking-wide text-muted uppercase">
          <ListChecks className="h-3.5 w-3.5" strokeWidth={2.2} />
          Details
        </h2>
        <ProductForm product={product} onSaved={setProduct} />
      </section>
    </div>
  );
}

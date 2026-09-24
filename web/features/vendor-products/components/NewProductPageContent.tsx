"use client";

import { Spinner } from "@/components/ui/Spinner";
import { VendorOnlyNotice } from "@/components/ui/VendorOnlyNotice";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { ProductForm } from "./ProductForm";

export function NewProductPageContent() {
  const { user, isLoading: authLoading } = useAuth();

  if (authLoading) return <Spinner />;
  if (!user?.is_vendor) return <VendorOnlyNotice />;

  return <ProductForm />;
}

import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { AccountPageContent } from "@/features/account/components/AccountPageContent";

export const metadata: Metadata = { title: "Your account — Marketplace" };

export default function AccountPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">Your account</h1>
        <div className="mt-8">
          <AccountPageContent />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}

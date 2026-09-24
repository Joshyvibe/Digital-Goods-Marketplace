import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { RegisterForm } from "@/features/auth/components/RegisterForm";

export const metadata: Metadata = { title: "Create your account — Marketplace" };

export default function RegisterPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-8 px-4 py-16">
        <div>
          <h1 className="text-3xl font-black tracking-tight uppercase">Create your account</h1>
          <p className="mt-2 text-muted">Buy today, start selling whenever you&rsquo;re ready.</p>
        </div>
        <RegisterForm />
      </main>
      <SiteFooter />
    </>
  );
}

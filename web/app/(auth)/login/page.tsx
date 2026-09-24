import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { LoginForm } from "@/features/auth/components/LoginForm";

export const metadata: Metadata = { title: "Sign in — Marketplace" };

export default function LoginPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-8 px-4 py-16">
        <div>
          <h1 className="text-3xl font-black tracking-tight uppercase">Sign in</h1>
          <p className="mt-2 text-muted">Welcome back.</p>
        </div>
        <LoginForm />
      </main>
      <SiteFooter />
    </>
  );
}

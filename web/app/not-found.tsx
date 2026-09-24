import Link from "next/link";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-lg flex-1 flex-col items-start justify-center gap-4 px-4 py-24">
        <p className="text-sm font-semibold tracking-[0.2em] text-muted uppercase">404</p>
        <h1 className="text-4xl font-black tracking-tight uppercase">Page not found</h1>
        <p className="text-muted">
          That page doesn&rsquo;t exist, or the link is out of date.
        </p>
        <Link
          href="/"
          className="mt-2 rounded-full bg-ink px-6 py-3 font-semibold text-paper transition hover:bg-ink/85"
        >
          Back to shop
        </Link>
      </main>
      <SiteFooter />
    </>
  );
}

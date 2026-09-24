"use client";

import { ArrowRight, Percent, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";
import { motion } from "motion/react";
import { HeroIllustration } from "./HeroIllustration";

const STATS = [
  { icon: Zap, value: "Instant", label: "Delivery on purchase" },
  { icon: Percent, value: "15%", label: "Flat platform fee" },
  { icon: ShieldCheck, value: "Stripe", label: "Secure vendor payouts" },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.05 } },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const } },
};

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-ink text-paper">
      <div
        aria-hidden
        className="animate-drift pointer-events-none absolute -top-32 -right-32 h-[32rem] w-[32rem] rounded-full bg-accent/30 blur-[110px]"
      />
      <div
        aria-hidden
        className="animate-drift-slow pointer-events-none absolute -bottom-40 left-1/4 h-[26rem] w-[26rem] rounded-full bg-accent/10 blur-[100px]"
      />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-12 px-4 py-24 sm:py-32 lg:grid-cols-2"
      >
        <div className="flex flex-col gap-10">
          <motion.p
            variants={item}
            className="text-sm font-semibold tracking-[0.2em] text-accent uppercase"
          >
            Digital Goods Marketplace
          </motion.p>
          <motion.h1
            variants={item}
            className="max-w-3xl text-4xl leading-[1.05] font-black tracking-tight uppercase sm:text-6xl sm:leading-[1.02] lg:text-7xl"
          >
            Creative assets for people who <span className="text-accent">ship</span>
          </motion.h1>
          <motion.p variants={item} className="max-w-xl text-lg text-paper/70">
            Templates, presets, ebooks, and licenses — built by independent creators, delivered
            instantly, ready to use today.
          </motion.p>
          <motion.div variants={item} className="flex flex-wrap items-center gap-4">
            <Link
              href="#featured"
              className="group flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-bold text-accent-ink transition hover:brightness-95"
            >
              Browse the shop
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <Link
              href="/vendor/onboarding"
              className="rounded-full border border-paper/30 px-6 py-3 text-sm font-semibold text-paper transition hover:border-paper/60"
            >
              Start selling
            </Link>
          </motion.div>

          <motion.div
            variants={item}
            className="mt-6 flex flex-wrap gap-10 border-t border-paper/10 pt-8 text-sm text-paper/60"
          >
            {STATS.map(({ icon: Icon, value, label }) => (
              <div key={label} className="flex items-start gap-3">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-accent" strokeWidth={2.2} />
                <div>
                  <p className="text-2xl font-black text-paper">{value}</p>
                  <p>{label}</p>
                </div>
              </div>
            ))}
          </motion.div>
        </div>

        <HeroIllustration />
      </motion.div>
    </section>
  );
}

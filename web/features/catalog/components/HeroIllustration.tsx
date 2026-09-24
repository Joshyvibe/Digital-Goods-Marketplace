"use client";

import { BookOpen, Check, Download, KeyRound, LayoutTemplate } from "lucide-react";
import { motion } from "motion/react";

const CARDS = [
  {
    icon: KeyRound,
    label: "License",
    title: "Icon Pack Pro",
    price: "$45",
    gradient: "from-[#e5d4ff] to-[#c29fff]",
    rotate: -3,
    top: "40%",
    left: "14%",
    width: "w-32 sm:w-44 lg:w-64",
    z: 30,
    delay: 0.35,
    floatDuration: 5,
  },
  {
    icon: BookOpen,
    label: "Ebook",
    title: "Design Systems 101",
    price: "$18",
    gradient: "from-[#c9e4ff] to-[#8fc2ff]",
    rotate: 6,
    top: "0%",
    left: "44%",
    width: "w-28 sm:w-40 lg:w-60",
    z: 20,
    delay: 0.2,
    floatDuration: 4.5,
  },
  {
    icon: LayoutTemplate,
    label: "Template",
    title: "Startup Landing Kit",
    price: "$29",
    gradient: "from-accent to-[#a6d92a]",
    rotate: -9,
    top: "8%",
    left: "0%",
    width: "w-28 sm:w-36 lg:w-56",
    z: 10,
    delay: 0.05,
    floatDuration: 5.5,
  },
] as const;

export function HeroIllustration() {
  return (
    <div aria-hidden className="relative h-[17rem] w-full pr-4 sm:h-[22rem] lg:h-[30rem] lg:pr-6">
      {CARDS.map((card) => {
        const Icon = card.icon;
        return (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 24, rotate: card.rotate }}
            animate={{ opacity: 1, y: [0, -10, 0], rotate: card.rotate }}
            transition={{
              opacity: { duration: 0.6, delay: card.delay },
              y: { duration: card.floatDuration, repeat: Infinity, ease: "easeInOut", delay: card.delay },
            }}
            style={{ top: card.top, left: card.left, zIndex: card.z }}
            className={`absolute ${card.width} overflow-hidden rounded-xl border border-paper/10 bg-ink shadow-2xl shadow-black/40 sm:rounded-2xl`}
          >
            <div
              className={`flex aspect-[4/3] items-center justify-center bg-gradient-to-br ${card.gradient}`}
            >
              <Icon className="h-5 w-5 text-ink/25 sm:h-8 sm:w-8 lg:h-12 lg:w-12" strokeWidth={1.5} />
            </div>
            <div className="flex items-center justify-between p-1.5 sm:p-2.5 lg:p-4">
              <div className="min-w-0">
                <p className="truncate text-[6px] font-semibold tracking-wide text-paper/50 uppercase sm:text-[8px] lg:text-[10px]">
                  {card.label}
                </p>
                <p className="truncate text-[8px] font-semibold text-paper sm:text-xs lg:text-sm">
                  {card.title}
                </p>
              </div>
              <span className="ml-1 shrink-0 rounded-full bg-paper/10 px-1.5 py-0.5 text-[7px] font-bold text-accent sm:px-2 sm:text-[10px] lg:px-2.5 lg:py-1 lg:text-xs">
                {card.price}
              </span>
            </div>
          </motion.div>
        );
      })}

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1, y: [0, -8, 0] }}
        transition={{
          opacity: { delay: 0.6, duration: 0.5 },
          y: { duration: 4, repeat: Infinity, ease: "easeInOut" },
        }}
        className="absolute top-0 right-1 z-40 flex items-center gap-1 rounded-full bg-accent px-1.5 py-1 text-[7px] font-bold text-accent-ink shadow-lg sm:right-2 sm:gap-1.5 sm:px-3 sm:py-1.5 sm:text-xs"
      >
        <Check className="h-2.5 w-2.5 sm:h-3.5 sm:w-3.5" strokeWidth={3} />
        Instant delivery
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1, y: [0, 8, 0] }}
        transition={{
          opacity: { delay: 0.75, duration: 0.5 },
          y: { duration: 4.5, repeat: Infinity, ease: "easeInOut" },
        }}
        className="absolute right-1 bottom-2 z-40 flex h-6 w-6 items-center justify-center rounded-full bg-paper text-ink shadow-lg sm:right-2 sm:bottom-4 sm:h-11 sm:w-11"
      >
        <Download className="h-3 w-3 sm:h-5 sm:w-5" strokeWidth={2} />
      </motion.div>
    </div>
  );
}

"use client";

import { AlertCircle } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

export function FormError({ message }: { message: string | null }) {
  return (
    <AnimatePresence>
      {message && (
        <motion.p
          initial={{ opacity: 0, height: 0, marginTop: 0 }}
          animate={{ opacity: 1, height: "auto", marginTop: 0 }}
          exit={{ opacity: 0, height: 0, marginTop: 0 }}
          className="flex items-center gap-1.5 overflow-hidden text-sm text-red-600"
        >
          <AlertCircle className="h-4 w-4 shrink-0" strokeWidth={2} />
          {message}
        </motion.p>
      )}
    </AnimatePresence>
  );
}

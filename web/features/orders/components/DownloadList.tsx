"use client";

import { AlertCircle, Download, FileDown, PackageOpen, RotateCcw } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { getOrderDownloads } from "../api";
import type { DownloadItem } from "../types";

const container = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } };

export function DownloadList({ orderId }: { orderId: number }) {
  const [downloads, setDownloads] = useState<DownloadItem[] | null>(null);

  useEffect(() => {
    getOrderDownloads(orderId)
      .then(setDownloads)
      .catch(() => setDownloads([]));
  }, [orderId]);

  if (downloads === null) {
    return <Spinner label="Checking for downloads…" />;
  }

  if (downloads.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-dashed border-line p-5 text-sm text-muted">
        <PackageOpen className="h-4 w-4 shrink-0" strokeWidth={1.8} />
        Your files will appear here once payment is confirmed.
      </div>
    );
  }

  return (
    <motion.ul variants={container} initial="hidden" animate="show" className="flex flex-col gap-2">
      {downloads.map((entry, index) => (
        <motion.li key={`${entry.product_title}-${index}`} variants={item}>
          <div className="rounded-2xl border border-line px-4 py-3">
            <p className="text-sm font-semibold">{entry.product_title}</p>

            {entry.status === "refunded" ? (
              <p className="mt-1 flex items-center gap-1.5 text-xs text-muted">
                <RotateCcw className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
                Refunded — access revoked.
              </p>
            ) : entry.files.length === 0 ? (
              <p className="mt-1 flex items-center gap-1.5 text-xs text-muted">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
                No file uploaded yet — contact the vendor.
              </p>
            ) : (
              <ul className="mt-2 flex flex-col gap-2">
                {entry.files.map((file) => (
                  <li key={file.filename}>
                    <a
                      href={file.download_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between gap-3 rounded-xl border border-line px-3 py-2 transition hover:border-ink hover:shadow-sm"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-paper-muted">
                          <FileDown className="h-4 w-4 text-ink" strokeWidth={2} />
                        </span>
                        <p className="text-xs text-muted">{file.filename}</p>
                      </div>
                      <Download className="h-4 w-4 shrink-0 text-muted" strokeWidth={2} />
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </motion.li>
      ))}
    </motion.ul>
  );
}

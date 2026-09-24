import { Loader2 } from "lucide-react";

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-muted">
      <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />
      <span className="text-sm">{label}</span>
    </div>
  );
}

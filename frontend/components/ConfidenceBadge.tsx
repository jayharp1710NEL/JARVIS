import type { Confidence } from "@/lib/types";

const styles: Record<Confidence, string> = {
  high: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  medium: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  low: "bg-rose-500/15 text-rose-300 border-rose-500/30",
};

export default function ConfidenceBadge({ value }: { value: Confidence }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border font-mono ${styles[value]}`}
      title="The agent's calibrated confidence based on evidence and verification."
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {value.toUpperCase()}
    </span>
  );
}

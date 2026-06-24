import type { Mode } from "@/lib/types";

const MODES: { value: Mode; label: string; hint: string }[] = [
  { value: "fast", label: "Fast", hint: "Quick, low-latency answers" },
  { value: "research", label: "Research", hint: "Web sources + citations" },
  { value: "deep", label: "Deep Think", hint: "Plan, verify, self-critique" },
  { value: "builder", label: "Builder", hint: "Code & architecture" },
  { value: "truth", label: "Truth", hint: "Facts vs assumptions vs unknowns" },
  { value: "debate", label: "Debate", hint: "For / against / judgement" },
  { value: "privacy", label: "Privacy", hint: "Fully local, no egress" },
  { value: "autopilot", label: "Autopilot", hint: "Multi-step task execution" },
];

export default function ModeSelector({
  mode,
  onChange,
}: {
  mode: Mode;
  onChange: (m: Mode) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {MODES.map((m) => (
        <button
          key={m.value}
          title={m.hint}
          onClick={() => onChange(m.value)}
          className={`px-2.5 py-1 rounded-md text-xs border transition-colors ${
            mode === m.value
              ? "bg-accent/15 border-accent/40 text-accent"
              : "bg-card border-edge text-muted hover:text-white"
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}

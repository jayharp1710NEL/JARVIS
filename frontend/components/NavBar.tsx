"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Chat" },
  { href: "/memory", label: "Memory" },
  { href: "/files", label: "Files" },
  { href: "/evals", label: "Evals" },
  { href: "/settings", label: "Settings" },
];

export default function NavBar() {
  const path = usePathname();
  return (
    <header className="border-b border-edge bg-panel/80 backdrop-blur sticky top-0 z-20">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_10px_2px_rgba(34,211,238,0.6)]" />
          <span className="font-mono font-semibold tracking-wide text-white">
            JARVIS<span className="text-accent">·</span>LOCAL
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {links.map((l) => {
            const active = path === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  active
                    ? "bg-card text-white border border-edge"
                    : "text-muted hover:text-white"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto text-xs text-muted font-mono">local-first · private</div>
      </div>
    </header>
  );
}

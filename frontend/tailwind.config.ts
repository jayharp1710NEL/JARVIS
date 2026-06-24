import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Futuristic Jarvis palette: black / grey / white + a cyan accent.
        ink: "#0a0a0b",
        panel: "#141417",
        card: "#1b1b1f",
        edge: "#2a2a30",
        muted: "#8a8a93",
        accent: "#22d3ee",
        accentdim: "#0e7490",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;

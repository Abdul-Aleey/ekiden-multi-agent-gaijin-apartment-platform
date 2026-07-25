import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        paper: "#FAFAF8",
        "paper-dark": "#15181C",
        ink: "#1A2233",
        "ink-dark": "#E4E7EC",
        rule: "#D8DCE2",
        "rule-dark": "#2A2F37",
        signal: "#C4342B",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "var(--font-noto-jp)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;

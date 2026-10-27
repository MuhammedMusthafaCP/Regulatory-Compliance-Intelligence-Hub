import type { Config } from "tailwindcss";

// Palette: primary blue #3368A0, secondary blue #66A3BF, seafoam #C8DFDB, warm neutral #F2EFE7.
// The secondary blue is 2.4:1 on the warm neutral, so it is used for rules and accents, never for text.
// Fonts use new names (display, ui) so the existing dashboard keeps Tailwind's default sans.
const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: { DEFAULT: "#F2EFE7", raised: "#FBFAF6", sunk: "#E8E4D9" },
        ink: { DEFAULT: "#17212B", soft: "#374452", muted: "#566371" },
        brand: { DEFAULT: "#3368A0", deep: "#27527F" },
        lake: "#66A3BF",
        foam: { DEFAULT: "#C8DFDB", soft: "#E0EDEA" },
        rule: "#D9D4C7",
        signal: { weak: "#80520F", weakbg: "#F3E9CF", error: "#9B3B2E", errorbg: "#F5E4DF" },
      },
      fontFamily: {
        display: ['"Newsreader Variable"', "Georgia", "serif"],
        ui: ['"Public Sans Variable"', "system-ui", "sans-serif"],
      },
      fontSize: {
        display: ["clamp(2.15rem, 1.4rem + 3vw, 3.5rem)", { lineHeight: "1.04", letterSpacing: "-0.02em" }],
        title: ["clamp(1.5rem, 1.25rem + 1vw, 2.05rem)", { lineHeight: "1.18", letterSpacing: "-0.01em" }],
        heading: ["1.3125rem", { lineHeight: "1.3" }],
        body: ["1.0625rem", { lineHeight: "1.72" }],
        ui: ["0.9375rem", { lineHeight: "1.45" }],
        meta: ["0.75rem", { lineHeight: "1.3", letterSpacing: "0.08em" }],
      },
      keyframes: {
        sweep: { "0%": { transform: "translateX(-110%)" }, "100%": { transform: "translateX(330%)" } },
      },
      animation: { sweep: "sweep 1.4s ease-in-out infinite" },
    },
  },
  plugins: [],
};

export default config;

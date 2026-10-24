/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{svelte,js,ts}"],
  theme: {
    extend: {
      colors: {
        // Titanium Monochrome Design System
        canvas:   "#000000",   // Pitch black canvas
        s1:       "#08090d",   // Surface 1 — header
        s2:       "#0f1116",   // Surface 2 — thinking block
        b1:       "#161820",   // Border 1 — hairline on s1
        b2:       "#222530",   // Border 2 — hairline on s2
        platinum: "#ffffff",   // Primary text
        muted:    "#9ca3af",   // Secondary/metadata text
        dimmed:   "#52525b",   // Reasoning drawer accent bar
        emerald:  "#10b981",   // Status dot / active accent
        glass:    "rgba(255,255,255,0.05)",  // Glass surface
        glassborder: "rgba(255,255,255,0.08)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Text"',
          '"Segoe UI"',
          "Inter",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          '"SF Mono"',
          '"Cascadia Code"',
          '"Fira Code"',
          "monospace",
        ],
      },
      animation: {
        "fade-in":   "fadeIn 0.35s ease-out",
        "slide-in":  "slideIn 0.28s cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-out": "slideOut 0.22s cubic-bezier(0.4, 0, 1, 1)",
        "pulse-dot": "pulseDot 2s ease-in-out infinite",
        "blink":     "blink 1.1s step-end infinite",
      },
      keyframes: {
        fadeIn:   { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        slideIn:  { from: { opacity: "0", transform: "translateX(24px)" }, to: { opacity: "1", transform: "translateX(0)" } },
        slideOut: { from: { opacity: "1", transform: "translateX(0)" }, to: { opacity: "0", transform: "translateX(24px)" } },
        pulseDot: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.4" } },
        blink:    { "0%,100%": { opacity: "1" }, "50%": { opacity: "0" } },
      },
    },
  },
  plugins: [],
};

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ['"Plus Jakarta Sans"', "Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        kairo: {
          bg: "#090d16",
          card: "#0f172a",
          surface: "#141d2e",
          elevated: "#1e293b",
          border: "rgba(255, 255, 255, 0.08)",
          "border-hover": "rgba(255, 255, 255, 0.16)",
          brand: "#6366f1",
          "brand-light": "#818cf8",
          "brand-dark": "#4f46e5",
        },
      },
      boxShadow: {
        hud: "none",
        card: "none",
      },
    },
  },
  plugins: [],
};

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        cream: {
          50: "#fdfcf9",
          100: "#faf9f5",
          200: "#f5f3ed",
        },
        ink: {
          900: "#171a18",
          700: "#3b403c",
          600: "#59605b",
          500: "#7a807b",
          400: "#9aa19b",
        },
        brand: {
          50: "#eef1fc",
          100: "#dbe2f8",
          200: "#b8c5f0",
          300: "#8aa0e6",
          400: "#5a78da",
          500: "#2f4fd0",
          600: "#173dbd",
          700: "#1733a0",
          800: "#162c82",
          900: "#142566",
          950: "#0d173f",
        },
        accent: {
          green: "#0a7357",
          amber: "#b45309",
          rose: "#be123c",
        },
      },
      fontFamily: {
        sans: [
          "Inter Variable",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "PingFang SC",
          "Microsoft YaHei",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono Variable",
          "JetBrains Mono",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(23,26,24,0.04)",
        cardHover: "0 4px 20px -4px rgba(23,26,24,0.10)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.25s ease-out both",
      },
    },
  },
  plugins: [],
};

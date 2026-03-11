/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        titillium: ["Titillium Web", "sans-serif"],
      },
      colors: {
        "steel-blue": "#3a7eb9",
        "cloudy-sky": "#5791c4",
        "rich-cerulean": "#347ab7",
        primary: "#347ab7",
        "primary-hover": "#2d6a9a",
      },
      keyframes: {
        "login-morph": {
          "0%": { width: "100%", opacity: "1" },
          "55%": { width: "240px", opacity: "1" },
          "75%": { width: "240px", opacity: "1" },
          "100%": { width: "240px", opacity: "0" },
        },
        "icon-pop": {
          "0%": { transform: "scale(0.85)" },
          "60%": { transform: "scale(1.08)" },
          "100%": { transform: "scale(1)" },
        },
      },
      animation: {
        "login-morph": "login-morph 0.8s ease-out forwards",
        "icon-pop": "icon-pop 0.25s ease-out forwards",
      },
    },
  },
  plugins: [],
};

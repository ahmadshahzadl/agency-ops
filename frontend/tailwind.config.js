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
    },
  },
  plugins: [],
};

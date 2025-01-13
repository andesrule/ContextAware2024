/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./map.js",
    "./script.js",
    "./utils.js",
    "/src/input.css"
  ],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["forest"]
  }
}
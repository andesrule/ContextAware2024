/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./map.js",
    "./script.js",
    "./utils.js"
  ],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["forest"]
  }
}
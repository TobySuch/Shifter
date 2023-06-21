/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "/app/shifter/**/templates/**/*.html",
    "/app/shifter/templates/*.html",
    "./node_modules/flowbite/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#114c92',
      }
    },
  },
  plugins: [
    require('flowbite/plugin'),
  ],
}


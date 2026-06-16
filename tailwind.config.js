/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          teal: "#0f766e",
          leaf: "#047857",
          amber: "#fbbf24"
        }
      },
      borderRadius: {
        DEFAULT: "0.25rem"
      }
    }
  },
  plugins: []
};


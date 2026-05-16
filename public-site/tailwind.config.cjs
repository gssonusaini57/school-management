const kisPreset = require("../packages/design-system/tailwind.preset.cjs");

/** @type {import('tailwindcss').Config} */
module.exports = {
  presets: [kisPreset],
  content: ["./src/**/*.{njk,md,html}"],
  theme: {
    extend: {
      container: {
        center: true,
        padding: { DEFAULT: "1rem", lg: "1.5rem", xl: "2rem" },
      },
    },
  },
  plugins: [],
};

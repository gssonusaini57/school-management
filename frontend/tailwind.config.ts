import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";
// Shared KIS design tokens (colors, typography, spacing, radius, shadow, motion)
import kisPreset from "../packages/design-system/tailwind.preset.cjs";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  presets: [kisPreset as Config],
  theme: {
    container: { center: true, padding: "1rem" },
    extend: {
      // Keep the shadcn HSL-var aliases so existing primitives (button.tsx,
      // input.tsx, etc.) keep working without rewriting their classnames.
      // The HSL var values are remapped onto KIS palette in globals.css.
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
      },
      borderRadius: {
        // shadcn primitives use rounded-lg/md/sm — map onto KIS radius scale.
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
      },
    },
  },
  plugins: [animate],
};

export default config;

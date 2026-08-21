/** @type {import('tailwindcss').Config} */

/**
 * Colors resolve through CSS variables (defined in src/index.css) that hold an
 * "R G B" channel triple. Writing them as rgb(var(--x) / <alpha-value>) keeps
 * Tailwind's opacity modifiers working, so `bg-surface/50` still does what you
 * expect.
 *
 * The payoff: a utility like `bg-surface` is authored once and resolves
 * correctly in both themes. Components don't need a `dark:` twin on every
 * class, and anything added later picks up dark mode for free.
 */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** Every status family exposes the same five slots, so they're interchangeable. */
const family = (name) => ({
  DEFAULT: token(name),
  hover: token(`${name}-hover`),
  contrast: token(`${name}-contrast`), // text/icons sitting ON the solid fill
  soft: token(`${name}-soft`), // tinted panel background
  light: token(`${name}-soft`), // legacy alias for `soft`
  'on-soft': token(`${name}-on-soft`), // text/icons on `soft` or on the canvas
  line: token(`${name}-line`), // border that pairs with `soft`
});

module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surfaces, ordered back to front.
        canvas: token('canvas'),   // the page itself
        surface: token('surface'), // cards, table bodies
        raised: token('raised'),   // sidebar, dialogs, popovers
        sunken: token('sunken'),   // table headers, inset wells

        // Text, in descending emphasis.
        content: {
          DEFAULT: token('content'),
          muted: token('content-muted'),
          subtle: token('content-subtle'),
        },

        // Hairlines and dividers.
        line: {
          DEFAULT: token('line'),
          strong: token('line-strong'),
        },

        primary: family('primary'),
        success: family('success'),
        error: family('error'),
        warning: family('warning'),
        info: family('info'),
        pending: family('pending'),
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        // Shadows carry the theme too: near-invisible on dark surfaces unless
        // they get deeper and more opaque.
        'card': 'var(--shadow-card)',
        'card-hover': 'var(--shadow-card-hover)',
        'soft': 'var(--shadow-soft)',
        'raised': 'var(--shadow-raised)',
      },
      keyframes: {
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
      animation: {
        'slide-in-right': 'slide-in-right 0.3s ease-out',
      },
    },
  },
  plugins: [],
}

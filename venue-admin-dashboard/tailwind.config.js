/** Tailwind config — tells it which files to scan for classes */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      screens: {
        // 📱 extra-small breakpoint for phones.
        // Below 475px (small phones) the stat cards stack in ONE column so
        // the numbers stay readable; from 475px they go two-up, and from
        // md (768px) four-up as before.
        xs: "475px",
      },
    },
  },
  plugins: [],
}

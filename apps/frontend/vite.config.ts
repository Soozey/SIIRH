import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined
          }
          if (id.includes("react-router-dom") || id.includes("react-dom") || id.includes("/react/")) {
            return "react-core"
          }
          if (id.includes("@tanstack/react-query") || id.includes("axios")) {
            return "data-core"
          }
          if (id.includes("@mui") || id.includes("@emotion")) {
            return "mui-vendor"
          }
          if (id.includes("@heroicons") || id.includes("@headlessui")) {
            return "ui-vendor"
          }
          if (id.includes("react-dnd") || id.includes("html2pdf.js") || id.includes("react-to-print")) {
            return "feature-vendor"
          }
          return "vendor"
        },
      },
    },
  },
})

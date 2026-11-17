// Test-only preview with an explicit shutdown, avoiding Windows tree-kill tooling.
import { preview } from "vite";
await preview({
  preview: { host: "127.0.0.1", port: Number(process.argv[2] || 4174), strictPort: true },
  plugins: [
    {
      name: "isolated-browser-test-shutdown",
      configurePreviewServer(server) {
        server.middlewares.use((request, response, next) => {
          if (request.url !== "/__test_shutdown" || request.method !== "POST")
            return next();
          response.end("stopping");
          setTimeout(() => {
            server.httpServer.close(() => process.exit(0));
            server.httpServer.closeAllConnections();
          }, 100);
        });
      },
    },
  ],
});

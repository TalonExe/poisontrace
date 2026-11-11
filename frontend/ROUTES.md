# Frontend routes

PoisonTrace uses TanStack Router in `src/utils/router.js` with a small code-based route tree. The page shell remains responsible for authentication and page composition while TanStack Router owns browser history and the supported route contract.

| Route        | Responsibility                                                                      | Access        |
| ------------ | ----------------------------------------------------------------------------------- | ------------- |
| `/login`     | Local synthetic sign-in and invalid-credential feedback                             | Public        |
| `/sessions`  | Create, edit, select, and remove local session configurations                       | Authenticated |
| `/dashboard` | Execute one scenario and inspect runs and campaign history for the selected session | Authenticated |
| `/scenarios` | View the local scenario library and display configuration                           | Authenticated |

Unknown paths normalize to `/login`. The app checks the local authentication seam before rendering protected pages. Sign-out clears the local session, drops the selected session, and replaces the current URL with `/login`.

`routes` and `normalizePath` are the canonical route contract. `createRouter` keeps `current` and `navigate` as the small app-facing helper. The old `subscribe` compatibility method was removed after repository-wide search found no production or test callers. TanStack Router's `RouterProvider` handles route updates in the browser, while dependency-free memory-history tests load the route directly.

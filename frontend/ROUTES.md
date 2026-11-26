# Frontend routes

PoisonTrace uses TanStack Router in `src/utils/router.js` with a small code-based route tree. The page shell remains responsible for authentication and page composition while TanStack Router owns browser history and the supported route contract.

| Route        | Responsibility                                                                      | Access        |
| ------------ | ----------------------------------------------------------------------------------- | ------------- |
| `/login`     | Local synthetic sign-in and invalid-credential feedback                             | Public        |
| `/activity`  | Analyst landing page for weekly and monthly investigation activity                    | Analyst       |
| `/settings`  | Manage analyst-owned API keys and saved investigation configurations                 | Analyst       |
| `/sessions`  | Legacy Settings entry point                                                        | Analyst       |
| `/dashboard/single` | Set up one investigation, including the offline sample                       | Analyst       |
| `/dashboard` | Configure and launch matched investigation groups                                  | Analyst       |
| `/results/runs` | Reopen saved runs and dashboard attempt selections                                | Analyst       |
| `/results/groups` | Review matched groups and dashboard group selections                             | Analyst       |
| `/scenarios` | View the local scenario library and display configuration                           | Authenticated |

Unknown paths normalize to `/login`. The app checks the local authentication seam before rendering protected pages. Sign-out clears the local session, drops the selected session, and replaces the current URL with `/login`.

`routes` and `normalizePath` are the canonical route contract. `createRouter` keeps `current` and `navigate` as the small app-facing helper. The old `subscribe` compatibility method was removed after repository-wide search found no production or test callers. TanStack Router's `RouterProvider` handles route updates in the browser, while dependency-free memory-history tests load the route directly.

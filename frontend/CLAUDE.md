# Frontend

TypeScript + Svelte 5, built with Vite, styled with Tailwind CSS.

## Commands

- **Type check**: `npx svelte-check --tsconfig tsconfig.json`
- **Dev server**: `npm run dev`
- **Build**: `npm run build`
- **E2E tests**: see `integration_tests/` — requires backend running on :8000

## Rules

- After every code change, run `npx svelte-check --tsconfig tsconfig.json` and fix all reported errors before finishing.

## Conventions

- Use Svelte 5 runes (`$state`, `$derived`, `$effect`, `$props`) — no legacy Options API.
- Service modules (`*_service.ts`) own all `fetch` calls. Use `assertOk` from `http_utils.ts` after every response.
- Base URLs come from `import.meta.env.VITE_*_API_URL`, falling back to `http://localhost:8000` in dev.
- In dev mode, `vite.config.ts` aliases `LoginPage.svelte` → `LoginPage.dev.svelte` and `auth_service` → `auth_service.dev.ts`.
- Auth errors are detected by checking `msg.includes('401')` — call `clearSession()` then the `onclearauth` prop.

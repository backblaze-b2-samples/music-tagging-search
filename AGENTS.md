<!-- last_verified: 2026-06-19 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

This app is **Music Tagging & Search**: audio uploaded to Backblaze B2 is analyzed
with Essentia (BPM, key/scale, genre, mood) and embedded with CLAP; the embeddings
accumulate into a vector index synced to B2, powering find-similar and semantic
text→audio search. All local OSS models — the only credentials are for B2.

## 1. Repository Map

```
apps/web/                       Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/library/              /library — tracks/-scoped music explorer
  src/app/search/               /search  — semantic text->audio search
  src/components/library/       track tags, inline player, similar dialog, library list
  src/components/search/        semantic search UI
services/api/                   FastAPI backend (layered: types/config/repo/service/runtime)
  app/service/engines/          local OSS models (Essentia, CLAP, vector index) — never touch B2
  app/service/analysis.py       per-track pipeline: download -> extract -> embed -> store -> index
  app/runtime/tracks.py         /tracks, /tracks/stats, /tracks/{key}/{analyze,features,similar,stream}, /search
  scripts/analyze.py            batch worker (pnpm analyze)
packages/shared/                Shared TypeScript types (mirror the Pydantic models)
docs/                           System of record (features, workflows, security, reliability)
docs/exec-plans/                Execution plans and tech debt tracker
scripts/fetch-models.sh         optional Essentia genre/mood model download (keyless, one-time)
infra/railway/                  Deployment config
```

**ML/engine code lives in `service/engines/` and gets B2 bytes via `repo/`.**
Essentia, CLAP, and the vector index only ever see local files / arrays — every
B2 byte goes through the single boto3 client in `repo/b2_client.py`, so the custom
user agent always holds. `boto3` must never appear outside `repo/` (enforced by a
structural test).

## 2. Building on This Starter Kit

When this repo is used as the foundation for a new app, the following pieces are part of the starter contract — keep them. Adapt only what the new use case actually requires.

**Keep as-is (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new screens with these primitives; never edit the generated `components/ui/` files directly. Restyling happens through tokens in `globals.css`.
- **File Explorer.** `/files` route, `apps/web/src/app/files/`, and `apps/web/src/components/files/`. The Files sidebar entry in `apps/web/src/components/layout/app-sidebar.tsx` stays.
- **Upload.** `/upload` route, `apps/web/src/app/upload/`, and `apps/web/src/components/upload/`. The Upload sidebar entry stays.
- The sidebar nav itself (Dashboard, Upload, Files, Settings, plus the Design System utility link).

**App-specific surfaces (added for Music Tagging & Search)**
- **Library** (`/library`, `apps/web/src/components/library/`) — the sample-scoped
  explorer over the `tracks/` prefix: inline playback, BPM/key/genre/mood tags, an
  Analyze action, and Find-similar. This is *in addition to* the full-bucket Files
  explorer, not a replacement for it.
- **Search** (`/search`, `apps/web/src/components/search/`) — semantic text→audio
  search over the CLAP index.
- **Dashboard.** `/` route and `apps/web/src/components/dashboard/` are music stats
  now (tracks · analyzed · embeddings indexed · storage; genre distribution; recently
  analyzed). All aggregations flow through the same `runtime -> service -> repo`
  layering and TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare
  `useEffect + fetch`. Update `docs/features/dashboard.md` in the same PR.

**Why the kept contract exists**
- The UI kit, Files explorer, and Upload page are the reusable B2-backed scaffolding
  from the starter kit and are kept as-is (Upload is re-themed for audio only).

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/`
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Analyze (primary pipeline entry)
pnpm analyze           # batch-analyze un-analyzed tracks, refresh the B2 index

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

> First analysis run downloads the CLAP weights once (keyless). Optional Essentia
> genre/mood models come from `bash scripts/fetch-models.sh`; analysis degrades
> gracefully without them.

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes

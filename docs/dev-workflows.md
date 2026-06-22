<!-- last_verified: 2026-06-19 -->
# Dev Workflows

Engineering workflows for this repo.

## Audio Pipeline Dev Flow

- **Heavy deps**: `pip install -r requirements.txt` pulls Essentia, laion-clap,
  LanceDB, librosa — the first install takes a few minutes.
- **Genre/mood models**: auto-fetched on the first analysis (keyless, one-time,
  ~90 MB). `bash scripts/fetch-models.sh` pre-fetches the same files for offline
  machines; pair it with `ESSENTIA_AUTO_FETCH=false` to disable runtime fetching.
  Either way BPM, key/scale, duration, loudness, and CLAP embeddings are
  model-free and run without these files.
- **First analysis** also downloads the CLAP weights once (public CDN, keyless).
- **Run the worker**: `pnpm analyze` batch-analyzes un-analyzed tracks under
  `tracks/` and refreshes the B2 index. Re-running skips already-analyzed tracks.
- **Engine boundary**: new ML code goes in `services/api/app/service/engines/`.
  Engines take a local file path / arrays and must NOT import boto3 — the
  `service` layer pulls/pushes B2 bytes via `repo`. `pnpm check:structure`
  enforces this.

## New Feature

- [ ] Read `AGENTS.md` and `ARCHITECTURE.md`
- [ ] Read the relevant feature doc in `docs/features/`
- [ ] For non-trivial changes, create a plan in `docs/exec-plans/active/`
- [ ] Implement the smallest coherent change
- [ ] Add or update tests
- [ ] Run: `pnpm typecheck && pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- [ ] Update docs in the same PR (see AGENTS.md §8)
- [ ] Move plan to `docs/exec-plans/completed/` after validation

## Bugfix

- [ ] Add a failing test that reproduces the bug
- [ ] Confirm the test fails
- [ ] Implement the fix
- [ ] Rerun tests until green
- [ ] Update docs if behavior changed

## Refactor

- [ ] Read `ARCHITECTURE.md` — respect layering rules
- [ ] Ensure structural tests still pass: `pnpm check:structure`
- [ ] No behavior changes without updating feature docs

## Documentation Update

- [ ] Update only the canonical location (see AGENTS.md §8 doc update mapping)
- [ ] Never duplicate content — link instead
- [ ] Update `<!-- last_verified: YYYY-MM-DD -->` header

## Pull Request

- [ ] One coherent change per PR
- [ ] Run full lint + test suite before submitting
- [ ] Docs updated in the same PR as code changes
- [ ] Only change files relevant to the task — no drive-by improvements

## Testing

### Test types
- **Unit**: pure logic (service layer)
- **Integration**: HTTP handlers, B2 connectivity (`tests/`)
- **Structural**: layering rules, import boundaries (`tests/test_structure.py`)
- **E2E**: Playwright browser-driven smoke tests

### Test placement
- Backend: `services/api/tests/`
- E2E: project root (Playwright)

### Commands
- Quick (backend): `pnpm test:api`
- Structure: `pnpm check:structure`
- Frontend typecheck: `pnpm typecheck`
- Frontend lint: `pnpm lint`
- Backend lint: `pnpm lint:api`
- Full suite: `pnpm typecheck && pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- E2E: `pnpm test:e2e` (run `pnpm --filter @music-tagging-search/web exec playwright install chromium` once first)

### When to run
- After behavior change: run relevant subset
- Before PR: run full suite

## Frontend Conventions

- Tailwind v4: config via CSS `@theme` blocks, NOT `tailwind.config.ts`
- Colors: OKLch format
- Dark mode: `next-themes` with `@custom-variant dark (&:is(.dark *))`
- Animations: `tw-animate-css` (not `tailwindcss-animate`)
- shadcn/ui components in `src/components/ui/` are generated — never modify them

## Data Fetching

All API reads/writes flow through TanStack Query hooks in
`apps/web/src/lib/queries.ts`. Don't add bare `useEffect + fetch` patterns
to components.

**Read** — use the hooks directly:

```tsx
const { data, isLoading, error, refetch } = useTracks(filters);
const { data: stats } = useMusicStats();
const { data: results } = useSemanticSearch(query, query.length > 0);
```

Surface errors via `<ErrorState error={error} onRetry={() => refetch()} />`
rather than silently rendering empty UI.

**Write** — wrap mutations with `useMutation` and invalidate on success:

```tsx
const analyze = useAnalyzeTrack();
analyze.mutate(track.key, {
  onSuccess: () => toast.success("Analyzed"),
});
```

`useAnalyzeTrack()` / `useDeleteFile()` call
`queryClient.invalidateQueries({ queryKey: qk.all })` on success — every consumer
(`useTracks`, `useMusicStats`, `useFiles`, ...) re-fetches lazily.

**Add a new endpoint** — three places to touch:
1. `services/api/app/runtime/<router>.py` — FastAPI route
2. `apps/web/src/lib/api-client.ts` — typed fetch wrapper
3. `apps/web/src/lib/queries.ts` — `useQuery` / `useMutation` hook + entry in `qk`

Defaults (in `apps/web/src/lib/query-client.tsx`):
- `staleTime: 30s` — file lists / stats don't change second-to-second
- `retry: 1` for transient errors; never retry 4xx (won't get better)
- `refetchOnWindowFocus`: on (TanStack default) — dashboard self-heals
  when the user comes back to the tab

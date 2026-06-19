<!-- last_verified: 2026-06-19 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the music catalog: how much is stored, how much has
been analyzed and embedded, and how the catalog breaks down by genre.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /tracks/stats`, `GET /tracks`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards (tracks, analyzed, embeddings indexed, storage)
- `apps/web/src/components/dashboard/upload-chart.tsx` — `GenreChart`: genre distribution bar chart
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — `RecentTracksTable`: last 10 analyzed tracks
- `apps/web/src/lib/queries.ts` — `useMusicStats()`, `useTracks()`
- `services/api/app/runtime/tracks.py` — `GET /tracks/stats` handler
- `services/api/app/service/stats.py` — `get_music_stats()` aggregation
- `services/api/app/repo/b2_client.py` — `list_files()`, `download_file()` (index count)

## Canonical Files
- Stats aggregation: `services/api/app/service/stats.py`
- Dashboard cards: `apps/web/src/components/dashboard/stats-cards.tsx`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /tracks/stats` → `MusicStats` (total_tracks, analyzed_tracks, embeddings_indexed,
  total_size_bytes, total_size_human, genre_distribution, mood_distribution)
- `GET /tracks` → `LibraryTrack[]` — filtered client-side to analyzed for the recent table

## Flow
- Page loads → `useMusicStats()` and `useTracks()` fire in parallel
- Stat cards show tracks, analyzed count, embeddings indexed, storage used
- Genre chart renders the top genres from `genre_distribution`
- Recently analyzed table shows the latest 10 tracks with BPM, key, genre, mood

## Edge Cases
- API unavailable → cards/chart/table surface an inline ErrorState with Retry
- No tracks → cards show 0 / "0 B"; chart and table show empty states
- Many tracks → stats aggregation paginates B2 via `ContinuationToken`

## UX States
- Loading: skeleton placeholders
- Empty: "No genres yet" / "No analyzed tracks yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: backend `services/api/tests/` (stats reuse the existing repo-mock tests)
- Required cases: stats with analyzed tracks, empty catalog, API error fallback
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations, frontend builds

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Audio Analysis](audio-analysis.md)
- [App Workflows](../app-workflows.md)

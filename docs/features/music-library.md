<!-- last_verified: 2026-06-19 -->
# Feature: Music Library

## Purpose
Browse the catalog scoped to the `tracks/` prefix, with each track joined to its
extracted features, inline playback, tag filters, and per-track Analyze / Find-similar
actions. This is the sample-scoped explorer; the full-bucket [File Browser](file-browser.md)
is kept separately.

## Used By
- UI: `/library` page
- API: `GET /tracks`, `GET /tracks/{key:path}/stream`, `POST /tracks/{key:path}/analyze`, `GET /tracks/{key:path}/similar`

## Core Functions
- `apps/web/src/components/library/music-library.tsx` — the track list, filters, actions
- `apps/web/src/components/library/track-tags.tsx` — read-only BPM/key/genre/mood badges
- `apps/web/src/components/library/track-player.tsx` — inline HTML5 player (lazy presigned stream URL)
- `apps/web/src/components/library/similar-dialog.tsx` — "more like this" results
- `apps/web/src/lib/queries.ts` — `useTracks()`, `useAnalyzeTrack()`, `useSimilar()`
- `services/api/app/service/library.py` — `list_tracks()` (list + feature join + filtering)
- `services/api/app/runtime/tracks.py` — endpoints

## Canonical Files
- Library service: `services/api/app/service/library.py`
- Library UI: `apps/web/src/components/library/music-library.tsx`

## Inputs
- genre / mood: string (optional tag filters)
- bpm_min / bpm_max: number (optional BPM range)
- limit: int (1–1000, default 200)

## Outputs
- `GET /tracks` → `LibraryTrack[]` (storage metadata joined with `TrackFeatures`, newest-first)
- `GET /tracks/{key}/stream` → `{ url }` presigned inline playback URL

## Flow
- Page loads → `useTracks()` lists `tracks/` and joins each with its feature JSON
- Each row shows the filename, tags (or "Not analyzed yet"), and actions
- Play → lazily fetches a presigned stream URL and renders the native audio player
- Analyze / Re-analyze → triggers the analysis pipeline, then invalidates caches
- Find similar (enabled once analyzed) → opens the similar dialog
- Genre/mood text filters narrow the already-fetched rows client-side (the API also
  supports server-side filtering)

## Edge Cases
- No tracks → empty state pointing to Upload
- Filters match nothing → "No matches" empty state
- Track not analyzed → tags show "Not analyzed yet"; Find-similar disabled
- Stream presign failure → toast error
- B2 unreachable → inline ErrorState with Retry

## UX States
- Empty / Loading / Error / Loaded as above

## Verification
- Test files: structural tests; frontend type-checks and builds
- Required cases: list scoped to `tracks/`, feature join, tag filtering, stream URL
- Quick verify command: `pnpm build`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: frontend builds, structural tests green

## Related Docs
- [Audio Analysis](audio-analysis.md)
- [Similarity & Semantic Search](similarity-search.md)
- [File Browser](file-browser.md)

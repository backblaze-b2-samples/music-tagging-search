<!-- last_verified: 2026-06-19 -->
# Feature: Similarity & Semantic Search

## Purpose
Find tracks that sound alike (audio→audio "more like this") and search the catalog
with free text (text→audio), both over the same CLAP embedding index.

## Used By
- UI: `/library` Find-similar action, `/search` page
- API: `GET /tracks/{key:path}/similar`, `GET /search?q=`

## Core Functions
- `services/api/app/service/search.py` — `find_similar()`, `semantic_search()`
- `services/api/app/service/engines/index.py` — `search()` cosine ranking, `load_index()`
- `services/api/app/service/engines/clap_embed.py` — `embed_text()` for queries
- `apps/web/src/components/search/semantic-search.tsx` — search UI
- `apps/web/src/components/library/similar-dialog.tsx` — find-similar UI
- `apps/web/src/lib/queries.ts` — `useSimilar()`, `useSemanticSearch()`

## Canonical Files
- Search service: `services/api/app/service/search.py`
- Cosine ranking: `services/api/app/service/engines/index.py`

## Inputs
- find_similar: track_key (must exist in the index), top_k (1–50, default 10)
- semantic_search: q (non-empty text), top_k (1–50, default 10)

## Outputs
- `GET /tracks/{key}/similar` → `SimilarResult[]` (key, filename, score 0–1, features), excludes the query track
- `GET /search?q=` → `SearchResult` (query, ranked `SimilarResult[]`)

## Flow
- The index manifest is pulled from B2 via `repo` (custom UA holds)
- find_similar: looks up the track's own embedding in the index, cosine-ranks the rest
- semantic_search: CLAP embeds the text into the joint space, cosine-ranks the catalog
- Scores are normalized from cosine `[-1, 1]` to `[0, 1]` and shown as a % match
- Results carry each track's features and an inline player

## Edge Cases
- Index empty / track not yet embedded → empty results, friendly empty state
- Empty query string → API returns 400
- top_k out of range → API returns 400
- B2 unreachable when loading the index → inline ErrorState with Retry

## UX States
- Search idle (no query): "Search your catalog by vibe" prompt with example chips
- Loading / Error / Empty / Results as above

## Verification
- Test files: structural tests; cosine math is a pure function in `engines/index.py`
- Required cases: similar excludes self, semantic ranks by score, empty index handled
- Quick verify command: `pnpm check:structure`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: structural tests green; verified end-to-end against a real, analyzed catalog

## Related Docs
- [Embedding Index](embedding-index.md)
- [Audio Analysis](audio-analysis.md)
- [Music Library](music-library.md)

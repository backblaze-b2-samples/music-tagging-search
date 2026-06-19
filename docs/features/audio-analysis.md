<!-- last_verified: 2026-06-19 -->
# Feature: Audio Analysis

## Purpose
Extract musical features from each track with Essentia (BPM, key/scale, duration,
loudness, and optional genre/mood) and a semantic embedding with CLAP, then persist
the features to B2 and add the embedding to the index.

## Used By
- UI: `/library` Analyze action
- API: `POST /tracks/{key:path}/analyze`, `GET /tracks/{key:path}/features`
- Job: `pnpm analyze` (`services/api/scripts/analyze.py`) — the primary batch entry

## Core Functions
- `services/api/app/service/analysis.py` — `analyze_track()` orchestration, `load_features()`
- `services/api/app/service/engines/essentia_features.py` — `extract_features()` (BPM, key/scale, loudness, optional genre/mood)
- `services/api/app/service/engines/clap_embed.py` — `embed_audio()` (CLAP audio embedding)
- `services/api/app/repo/b2_client.py` — `download_file()`, `put_json()`, `put_bytes()`, `download_file()` (index)

## Canonical Files
- Pipeline orchestration: `services/api/app/service/analysis.py`
- Engine boundary exemplar: `services/api/app/service/engines/essentia_features.py`

## Inputs
- track_key: string — object key under `tracks/` (path-traversal validated)

## Outputs
- `AnalyzedTrack`: key, features (`TrackFeatures`), analyzed_at, embedded
- Side effects: writes `features/<id>.json` to B2; upserts the embedding into
  `index/embeddings.npz` on B2

## Flow
- `repo.download_file(track_key)` pulls the audio bytes from B2
- Bytes are written to a local temp file (engines never see B2)
- Essentia computes BPM (RhythmExtractor2013), key/scale (KeyExtractor), duration, loudness
- If the optional Essentia genre/mood models are present, they run too; otherwise skipped
- CLAP embeds the track into the joint audio↔text space
- `repo.put_json(features/<id>.json, features)` persists the features
- The embedding is upserted into the consolidated index and synced to B2
- The temp file is removed

## Edge Cases
- Essentia not importable or extraction fails → features degrade to empty, pipeline continues
- CLAP embedding fails → features still persisted, `embedded=False`, track not searchable until re-run
- Optional genre/mood models absent → those tags are null (BPM/key/etc. still produced)
- Track missing from B2 → API returns 502 / worker logs and skips
- First analysis run → CLAP weights downloaded once (public, keyless)

## UX States
- Library shows "Not analyzed yet" until features exist; "Analyze"/"Re-analyze" button drives it
- Toast on success/failure of an on-demand analyze

## Verification
- Test files: structural tests assert engines stay out of the boto3 boundary
- Required cases: graceful degradation when models/engines absent; features persisted; index updated
- Quick verify command: `pnpm check:structure`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: structural tests green, ruff clean; end-to-end verified with `pnpm analyze` against a real bucket

## Related Docs
- [Embedding Index](embedding-index.md)
- [Similarity & Semantic Search](similarity-search.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

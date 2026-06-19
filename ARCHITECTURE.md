<!-- last_verified: 2026-06-19 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with music stats (tracks, analyzed, embeddings indexed, storage),
    genre distribution, recently analyzed
  - Audio upload with drag-and-drop, progress tracking (audio-only)
  - Music Library (`/library`) — `tracks/`-scoped explorer with inline playback,
    BPM/key/genre/mood tags, Analyze + Find-similar actions, tag filters
  - Semantic Search (`/search`) — text→audio search over the embedding index
  - File browser (`/files`) — full-bucket explorer (kept from the starter kit)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for upload, the music library, analysis, similarity, and search
  - B2 S3 integration via a single boto3 client (custom user agent)
  - **Audio analysis engines** (`service/engines/`): Essentia MIR features, CLAP
    embeddings, and a vector index — all operate on local files, never on B2
  - Batch analysis worker (`scripts/analyze.py`, `pnpm analyze`)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (incl. `TrackFeatures`, `LibraryTrack`,
    `SimilarResult`, `SearchResult`, `MusicStats`)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, TrackFeatures, MusicStats, ...)
    config/                Settings loaded from environment (B2_* + prefixes + model config)
    repo/                  B2 S3 client — file ops + put_bytes/put_json/get_json/download_file/list_keys
    service/               Business logic (upload, library, analysis, search, stats)
      engines/             Local OSS models: essentia_features, clap_embed, index
    runtime/               FastAPI route handlers (files, tracks, upload, health, metrics)
  scripts/analyze.py       Batch analysis worker
  tests/                   pytest tests (structural + integration)
```

> **Engine boundary.** `service/engines/` holds Essentia, CLAP, and the vector
> index. These never import boto3 and never call B2 — they receive a local audio
> file path or numpy arrays. The `service` layer pulls bytes from B2 via `repo`,
> writes the local temp file, runs the engine, then writes results back via `repo`.
> This is what keeps the custom user agent on every B2 byte while still allowing
> heavy ML libraries in the codebase.

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No mutable globals**: Configuration is read-only after init. No module-level mutable state shared between layers.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. All file keys validated against prefix allowlist.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store:
  - `tracks/` — source audio (the `/library` explorer is scoped to this prefix)
  - `features/<id>.json` — per-track MIR feature JSON
  - `index/embeddings.npz` — the consolidated CLAP embedding index
  - Listing/metadata via S3 `list_objects_v2` / `head_object`; reads/writes via
    `get_object` / `put_object`; playback via `generate_presigned_url`
  - No application database — B2 holds source media, derived features, and the index
- **Local index cache** (`data/index-cache`, gitignored) — scratch space when the
  index is pulled from B2 for query; never authoritative.

## External Services

- **None external for ML.** Essentia and CLAP are local OSS models; the vector index
  is local NumPy/LanceDB. The only network credentials are for Backblaze B2.
- **Backblaze B2 S3 API** — media storage, feature JSON, the index, and presigned
  playback URLs. First analysis run also performs a one-time public, keyless
  download of the CLAP weights (and optional Essentia genre/mood models).

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (forced attachment) and for
  inline audio streaming (10-min expiry)

## Data Flows

- **Ingest**: Browser -> `POST /upload` (multipart) -> API validates audio type ->
  service writes to B2 under `tracks/` -> cheap audio probe -> response
- **Analyze** (per track): `POST /tracks/{key}/analyze` *or* `pnpm analyze` ->
  `repo.download_file(track)` -> Essentia features + CLAP embedding (local temp file)
  -> `repo.put_json(features/<id>.json)` -> upsert embedding into `index/embeddings.npz`
  via `repo` -> response
- **Library**: Browser -> `GET /tracks` -> service lists `tracks/` + joins feature
  JSON -> returns `LibraryTrack[]`
- **Find similar**: Browser -> `GET /tracks/{key}/similar` -> service pulls the index
  from B2 -> cosine search over the track's own embedding -> ranked neighbors
- **Semantic search**: Browser -> `GET /search?q=` -> CLAP embeds the text -> cosine
  search over the index -> ranked results
- **Stream**: Browser -> `GET /tracks/{key}/stream` -> presigned inline URL -> HTML5 player
- **Browse / delete**: full-bucket `/files` flows are unchanged from the starter kit

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Analysis pipeline (orchestration): `services/api/app/service/analysis.py`
- Audio engines: `services/api/app/service/engines/{essentia_features,clap_embed,index}.py`
- Tracks API handler: `services/api/app/runtime/tracks.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`audio.py`, `files.py`, `upload.py`, `stats.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Batch worker: `services/api/scripts/analyze.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Audio Ingest](docs/features/file-upload.md)
- [Audio Analysis](docs/features/audio-analysis.md)
- [Embedding Index](docs/features/embedding-index.md)
- [Similarity & Semantic Search](docs/features/similarity-search.md)
- [Music Library](docs/features/music-library.md)
- [File Browser](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions

<!-- last_verified: 2026-06-19 -->
# Feature: Embedding Index

## Purpose
Maintain a growing vector index of CLAP embeddings on B2 that powers both
find-similar and semantic search, and keep all index I/O on the single custom-UA
S3 client.

## Used By
- API/Job: every `analyze` upserts into the index; every search reads it
- API: `GET /tracks/stats` reports `embeddings_indexed`

## Core Functions
- `services/api/app/service/engines/index.py` — `load_index()`, `serialize_index()`, `upsert()`, `search()`
- `services/api/app/service/analysis.py` — `_sync_embedding()` read-modify-write to B2
- `services/api/app/service/search.py` — pulls the index for queries
- `services/api/app/repo/b2_client.py` — `download_file()` / `put_bytes()` move the manifest

## Canonical Files
- Index engine: `services/api/app/service/engines/index.py`
- Sync logic: `services/api/app/service/analysis.py`

## Transport decision (recorded)
The index is shipped as a **single consolidated manifest object**,
`index/embeddings.npz` (a NumPy archive of keys + vectors), that moves to and from B2
as one S3 object through `repo`. The scaffold plan named LanceDB as the primary
transport with a NumPy-cosine consolidated manifest as the *authorized fallback*;
the fallback was chosen as the shipped path because:

- A LanceDB table is a multi-file directory. Syncing it over plain S3 object ops
  means per-file list/upload/download — fragile and easy to leave inconsistent.
- A single `.npz` blob is trivially reproducible from a fresh clone and keeps every
  B2 byte on the one custom-UA client.
- Exact cosine search over the in-memory matrix is correct and fast at catalog scale,
  with no extra service to stand up.

`lancedb` remains a declared dependency so a future revision can build a local
LanceDB table *from* this manifest for ANN at very large scale without changing the
B2 transport. See `docs/exec-plans/tech-debt-tracker.md`.

## Inputs / Outputs
- Input: a track key + its CLAP embedding (`list[float]`)
- Output: updated `index/embeddings.npz` on B2; search returns `(key, score)` pairs

## Flow
- Upsert: download the current manifest (or start empty) → `upsert(keys, vectors, key, emb)`
  → `serialize_index()` → `put_bytes(index/embeddings.npz)`
- Query: download the manifest → `load_index()` → `search()` cosine ranking

## Edge Cases
- No index yet (first track) → treated as empty, created on first upsert
- Re-analyzing a track → its row is replaced in place (no duplicates)
- Concurrent analyses → last write wins on the manifest; the batch worker is sequential

## Verification
- Test files: structural tests; `engines/index.py` functions are pure and unit-testable
- Quick verify command: `pnpm check:structure`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: structural tests green; index round-trips through B2 in an end-to-end run

## Related Docs
- [Audio Analysis](audio-analysis.md)
- [Similarity & Semantic Search](similarity-search.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

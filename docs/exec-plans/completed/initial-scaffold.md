# Initial scaffold — `music-tagging-search`

This sample was scaffolded from the vibe-coding-starter-kit template. The original
build plan is preserved below as the record of what was added, trimmed, and renamed.
See `ARCHITECTURE.md` and `docs/features/` for the current state of the app.

---

## 1. Purpose

`music-tagging-search` is a self-hosted "find similar songs" and semantic audio
search system over a music catalog stored on Backblaze B2. Music producers, sync
licensing teams, and catalog managers upload audio tracks to B2; the app extracts
MIR features (BPM, key/scale, genre, mood) with **Essentia**, generates semantic
audio embeddings with **CLAP**, writes per-track feature JSON plus a growing
embedding index back to B2, and serves similarity search ("more like this") and
free-text semantic search ("dreamy lo-fi with mellow piano") over the catalog —
all on local OSS models with **no second API key, B2 credentials only**.

The demo story B2 carries: source audio + dense per-track feature JSON + a
continuously growing embedding index all accumulate in one bucket — multimodal,
write-amplifying storage over an expanding library. Every byte to/from B2 goes
through the S3-compatible API with a custom user-agent and standard `B2_*` vars.

## 2. Architecture delta (summary)

- KEEP: monorepo shell, full UI kit + `/design`, full-bucket File Explorer (`/files`),
  Upload (re-themed for audio), layout shell, layered FastAPI backend, single boto3
  client with custom UA, structural tests, docs system.
- TRIM: image/PDF metadata extraction (metadata.py repurposed to an audio probe;
  Pillow/PyPDF2 dropped), image/PDF/text/zip/video upload types (audio-only allowlist),
  generic dashboard widgets, starter screenshots.
- ADD: audio types, B2 prefixes + model config in settings, repo byte/JSON helpers,
  Essentia + CLAP + index engines, analysis/library/search/stats services, `/tracks`
  + `/search` routes, `scripts/analyze.py` worker, `scripts/fetch-models.sh`,
  `/library` and `/search` frontend pages, music dashboard, shared audio types.

## 3. Index transport decision

LanceDB was the plan's primary with a NumPy-cosine consolidated manifest as the
authorized fallback. The fallback shipped as primary (`index/embeddings.npz`, a single
B2 object) for reproducibility-from-fresh-clone and to keep all index I/O on the one
custom-UA S3 client. `lancedb` stays a declared dependency for a future ANN revision.
See `docs/features/embedding-index.md` and `docs/exec-plans/tech-debt-tracker.md`.

## 4. Standards compliance

- S3-compatible API only; no b2-native calls.
- `user_agent_extra="b2ai-music-tagging-search"` on the one boto3 client.
- Env names: `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`,
  `B2_REGION`, `B2_PUBLIC_URL_BASE` (+ `B2_ENDPOINT`).
- boto3 only in `repo/`; engines get bytes via repo; structural tests green; files < 300 lines.
- Files (full-bucket explorer) kept; `/library` (scoped to `tracks/`) added.
- No real secrets; `.env.example` placeholders only.

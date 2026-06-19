<!-- last_verified: 2026-06-19 -->
# Music Tagging & Search

A self-hosted **"find similar songs"** and **semantic audio search** system over a
music catalog stored on **[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-music-tagging-search)**.
Upload audio, and the app extracts musical features with **Essentia** (BPM,
key/scale, genre, mood), generates semantic audio embeddings with **CLAP**, and
writes per-track feature JSON plus a growing embedding index back to B2. You then
get two things on top of your catalog:

- **Find similar** — pick a track, get the closest-sounding ones ("more like this").
- **Semantic search** — type a vibe like *"dreamy lo-fi with mellow piano"* and rank
  the catalog by how well it matches.

Everything runs on **local open-source models — there is no second API key. Your
only credentials are for Backblaze B2.** First run downloads the CLAP weights
(and, optionally, the Essentia genre/mood models) once from public CDNs.

## Why B2 is the interesting part

Source audio, dense per-track feature JSON, and a continuously growing embedding
index all accumulate in **one bucket** — multimodal, write-amplifying storage over
an expanding library. Every byte to and from B2 goes through the **S3-compatible
API** on a single client carrying a custom user agent, with the standardized
`B2_*` environment variables.

```
tracks/      source audio uploaded by the user (the /library explorer is scoped here)
features/    per-track MIR feature JSON written by the analysis pipeline
index/        the consolidated CLAP embedding index (embeddings.npz)
```

## The pipeline (6 steps)

1. **Ingest** — drag-drop audio upload (audio-only), stored under `tracks/`.
2. **Extract** — Essentia computes BPM, key/scale, duration, loudness (and genre/mood
   when the optional models are present).
3. **Embed** — CLAP turns each track into a semantic audio embedding.
4. **Store** — the per-track features land in `features/<id>.json` on B2.
5. **Index** — the embedding is upserted into a consolidated index synced to B2 (`index/`).
6. **Search** — find-similar (audio→audio) and semantic search (text→audio) query that index.

## What it looks like

**Dashboard** — catalog stats, genre distribution, recently analyzed tracks:

![Dashboard with track/analyzed/embedding/storage cards, a genre chart, and a recently-analyzed table](docs/images/music-tagging-search-dashboard.png)

**Library** — the `tracks/`-scoped explorer with inline playback, tags, and actions:

![Music library showing track rows with BPM/key/genre/mood tags, inline players, Analyze and Find similar actions](docs/images/music-tagging-search-library.png)

> Screenshots are captured post-scaffold against a real bucket; the files above are
> placeholders until then.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, and a free
**[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-music-tagging-search)**.

**Heads up on heavy dependencies.** The backend installs Essentia, laion-clap,
LanceDB, and librosa. Expect a multi-minute first `pip install` and a one-time CLAP
weight download (~2 GB of disk for models + caches is a safe budget). Analysis is
CPU-friendly but RAM-hungry — give it ~4 GB. None of this needs a GPU or a second
API key.

**1. Install JS dependencies**

```bash
pnpm install
```

**2. Set up the backend**

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

**3. (Optional) Fetch the Essentia genre/mood models**

```bash
bash scripts/fetch-models.sh
```

Analysis works fine without these — BPM, key/scale, duration, loudness, and CLAP
embeddings are all model-free. The fetch script only adds the genre/mood tags.

**4. Add your B2 credentials**

```bash
cp .env.example .env
```

Open `.env` and, from the
[Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-music-tagging-search):

1. **Create a bucket**, then paste:
   - **Bucket Unique Name** → `B2_BUCKET_NAME`
   - **Endpoint** → `B2_ENDPOINT` (e.g. `https://s3.us-west-004.backblazeb2.com`)
   - The region segment of that endpoint → `B2_REGION` (e.g. `us-west-004`)
2. **Create an application key** with `Read and Write`, then paste:
   - **keyID** → `B2_APPLICATION_KEY_ID`
   - **applicationKey** → `B2_APPLICATION_KEY` *(shown once — paste it now)*

> Walkthroughs: [creating a bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-music-tagging-search) and [creating app keys](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-music-tagging-search).

**5. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. `pnpm dev` runs `pnpm doctor`
first — a preflight that catches missing tools, venv, or `.env` values.

**6. Analyze your catalog**

After uploading tracks, run the batch worker to extract features + build the index:

```bash
pnpm analyze
```

It skips already-analyzed tracks and refreshes the B2 index. You can also re-analyze
a single track from the Library page.

## Standardized B2 environment variables

| Variable | Purpose |
|----------|---------|
| `B2_APPLICATION_KEY_ID` | Application key ID |
| `B2_APPLICATION_KEY` | Application key secret |
| `B2_BUCKET_NAME` | Target bucket |
| `B2_REGION` | Region (also read by the boto3 client; never hardcoded in source) |
| `B2_ENDPOINT` | S3-compatible endpoint URL |
| `B2_PUBLIC_URL_BASE` | Optional public base URL for objects |

## Core Features

- [Audio Ingest](docs/features/file-upload.md) — audio-only drag-and-drop into `tracks/`.
- [Audio Analysis](docs/features/audio-analysis.md) — Essentia MIR features + CLAP embeddings.
- [Embedding Index](docs/features/embedding-index.md) — the growing vector index synced to B2.
- [Similarity & Semantic Search](docs/features/similarity-search.md) — find-similar + text→audio search.
- [Music Library](docs/features/music-library.md) — the `tracks/`-scoped explorer with tags + playback.
- [File Browser](docs/features/file-browser.md) — full-bucket explorer (kept from the starter kit).
- [Dashboard](docs/features/dashboard.md) — catalog stats and distributions.

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts, TanStack Query
- Python 3.11+, FastAPI, boto3, Pydantic v2
- Local OSS models: **Essentia** (MIR), **laion-clap** (CLAP embeddings), **LanceDB** + NumPy (index)
- Backblaze B2 (S3-compatible object storage) — the single store
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm analyze` | Batch-analyze un-analyzed tracks and refresh the B2 index |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:api` | Run backend tests |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright e2e (run `pnpm --filter @music-tagging-search/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs |
| [docs/design-system.md](docs/design-system.md) | Design tokens, primitives, error/empty states |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/exec-plans/](docs/exec-plans/) | Execution plans and tech debt tracker |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Claude Agent B2 Skill

Manage Backblaze B2 from your terminal using natural language (list/search, audits,
stale or large file detection, security checks, safe cleanup).

Repo: [https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage](https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage)

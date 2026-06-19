<!-- last_verified: 2026-06-19 -->
# App Workflows

User journeys inside the application.

## Upload Tracks

- User navigates to `/upload`
- Drops or selects audio (MP3, WAV, FLAC, OGG, AAC/M4A)
- Client validates size (max 200MB) and audio type
- Progress bar shows per-file upload status; tracks land under `tracks/`
- On success: toast + green checkmark; on failure: red icon with reason
- See: [Audio Ingest](features/file-upload.md)

## Analyze the Catalog (primary pipeline)

- After uploading, run `pnpm analyze` to batch-process every un-analyzed track
- For each track: download from B2 → Essentia features + CLAP embedding →
  write `features/<id>.json` → upsert the embedding into the B2 index
- Already-analyzed tracks are skipped; the index is refreshed
- A single track can also be (re)analyzed on demand from the Library
- See: [Audio Analysis](features/audio-analysis.md), [Embedding Index](features/embedding-index.md)

## Browse the Music Library

- User navigates to `/library`
- Tracks under `tracks/` are listed, each joined with its extracted features
- Inline player streams the track (presigned URL fetched on Play)
- Tags show BPM · key · genre · mood; text filters narrow by genre/mood
- **Analyze / Re-analyze** runs the pipeline for that track
- **Find similar** opens nearest-neighbor results ("more like this")
- See: [Music Library](features/music-library.md)

## Semantic Search

- User navigates to `/search`
- Types a description like *"dreamy lo-fi with mellow piano"* (or clicks an example)
- CLAP embeds the text and ranks the catalog in the joint space
- Results show a % match, tags, and an inline player
- See: [Similarity & Semantic Search](features/similarity-search.md)

## Browse the Whole Bucket

- User navigates to `/files`
- The full-bucket tree shows `tracks/`, `features/`, `index/`, etc.
- Preview / download / delete any object (inspect the derived feature JSON directly)
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Cards show tracks, analyzed count, embeddings indexed, storage used
- Genre distribution chart + recently analyzed table (track · BPM · key · genre · mood)
- See: [Dashboard](features/dashboard.md)

<!-- last_verified: 2026-06-19 -->
# Feature: Audio Ingest

## Purpose
Upload audio tracks from the browser to Backblaze B2 (audio-only) with real-time
progress, storing them under the `tracks/` prefix.

## Used By
- UI: `/upload` page, upload form component
- API: `POST /upload`

## Core Functions
- `apps/web/src/components/upload/upload-form.tsx` — orchestrates dropzone + progress + upload state
- `apps/web/src/components/upload/dropzone.tsx` — drag-and-drop via `react-dropzone`, audio accept filter
- `apps/web/src/lib/api-client.ts` — `uploadFile()` using XHR for progress events
- `services/api/app/runtime/upload.py` — HTTP handler, reads file chunks
- `services/api/app/service/upload.py` — audio-only allowlist, validation, writes under `tracks/`
- `services/api/app/repo/b2_client.py` — `upload_file()` via boto3 `put_object`
- `services/api/app/service/metadata.py` — `extract_metadata()` cheap audio probe after upload

## Canonical Files
- Service orchestration pattern: `services/api/app/service/upload.py`
- Frontend upload flow: `apps/web/src/components/upload/upload-form.tsx`

## Inputs
- file: `File` (browser multipart form data)
- content_type: string (audio MIME type)

## Outputs
- `FileUploadResponse`: key, filename, size, content_type, uploaded_at, url, metadata
- Side effect: object stored in B2 under `tracks/{sanitized_filename}`

## Flow
- User drops or selects audio in the dropzone (MP3, WAV, FLAC, OGG, AAC/M4A)
- Client validates size (max 200MB) and type — rejected files show a toast with the reason
- XHR sends multipart POST to `/upload` with progress events
- API checks `Content-Length` early to reject oversized requests before reading the body
- API validates content type against the **audio-only** allowlist
- API sanitizes the filename and verifies the extension matches the declared MIME type
- API reads the file in 1MB chunks with streaming size enforcement, rejects empty files
- API uses key `tracks/{sanitized_filename}` and calls `put_object`
- API runs a cheap audio probe (duration / sample rate / channels) — full MIR features
  come later from the analysis pipeline, not here
- API returns `FileUploadResponse`; client shows a toast and updates progress

## Edge Cases
- File exceeds 200MB → client-side rejection toast + API returns 413 if bypassed
- Non-audio type → client filter blocks it; API returns 415 if bypassed
- Extension mismatches MIME type → API returns 415
- No filename → API returns 400; empty file → API returns 400
- Duplicate filename → B2 creates a new version (buckets are always versioned)
- B2 unreachable → API returns 500

## UX States
- Empty: dropzone with audio-format instructions
- Loading: per-file progress bars
- Error: red status icon, per-file error message
- Complete: green checkmark, "Clear completed" button

## Verification
- Test files: `services/api/tests/test_upload_conflict.py`, `services/api/tests/test_error_handling.py`
- Required cases: successful audio upload, oversized rejection, non-audio rejection (415), empty file (400), duplicate allowed
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Audio Analysis](audio-analysis.md)
- [App Workflows](../app-workflows.md)

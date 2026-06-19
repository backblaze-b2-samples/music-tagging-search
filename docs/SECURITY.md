<!-- last_verified: 2026-06-19 -->
# Security

Security principles and implementation for music-tagging-search.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **Client -> B2**: Presigned URLs for download (forced attachment) and for inline
  audio streaming (10-min expiry)
- **No second external service**: Essentia and CLAP run locally; there is no second
  API key to leak. The only credentials in the system are for B2.

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against the **audio-only** allowlist
- Chunked streaming with size enforcement (200MB default)
- Content-type allowlist: MP3, WAV/X-WAV, FLAC, OGG, AAC, MP4/M4A only
- Empty file rejection

## File Key Validation

- Empty keys rejected
- Path-traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- Track endpoints (`/tracks/{key}/...`) reuse the same `validate_key` guard
- The bucket is the access boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment shares a
  bucket with other workloads

## Audio Streaming Safety

- The Library / Search players use a presigned URL from `/tracks/{key}/stream` that
  serves the object inline for playback, with a short (10-min) expiry
- Download links keep `Content-Disposition: attachment` to avoid inline rendering of
  arbitrary content
- Presigned URLs are minted server-side per request; the bucket itself stays private

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables (`B2_APPLICATION_KEY_ID`,
  `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`, `B2_ENDPOINT`,
  `B2_PUBLIC_URL_BASE`) without real values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries

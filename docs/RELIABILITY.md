<!-- last_verified: 2026-06-19 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File / track listing returns an empty list (not an error) when B2 has no objects
- Audio probe failures at upload don't block the upload (partial metadata returned)
- **Model-absent degradation**: the Essentia genre/mood models are auto-fetched
  on first analysis (keyless). If they can't be obtained — offline machine, or
  `ESSENTIA_AUTO_FETCH=false` — analysis still produces BPM, key/scale, duration,
  loudness, and the CLAP embedding; only the genre/mood tags are null. The
  download is attempted once per process, so an unreachable CDN doesn't stall
  every track in a batch run
- If Essentia isn't importable or feature extraction fails, the pipeline persists
  whatever it has and continues; a failed CLAP embedding leaves the track
  un-searchable (`embedded=False`) but keeps its features
- The batch worker (`pnpm analyze`) keeps going on per-track errors and reports a
  failure count at the end
- Frontend shows skeleton states while loading and inline error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)

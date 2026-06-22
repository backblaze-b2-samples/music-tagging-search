from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible API) ---
    b2_endpoint: str = "https://s3.us-west-004.backblazeb2.com"
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits — audio masters and lossless stems run large.
    max_file_size: int = 200 * 1024 * 1024  # 200MB

    # --- Object-key prefixes inside the bucket ---
    # Source audio the producer uploads. The /library explorer is scoped here.
    tracks_prefix: str = "tracks/"
    # Per-track MIR feature JSON written back by the analysis pipeline.
    features_prefix: str = "features/"
    # Vector index artifacts synced to B2 (LanceDB table, manifest).
    index_prefix: str = "index/"

    # --- Local model + cache config (no second API key — local OSS models) ---
    # laion-clap checkpoint name passed to laion_clap.CLAP_Module. The weights
    # are fetched once from a public CDN on first use (keyless).
    clap_model: str = "630k-audioset-best.pt"
    # Directory holding the Essentia-TensorFlow genre/mood models. On first
    # analysis the backend fetches them here automatically (keyless, one-time);
    # scripts/fetch-models.sh can pre-populate it for offline runs.
    essentia_models_dir: str = "data/essentia-models"
    # Auto-fetch the genre/mood models on first analysis if they're missing.
    # Set false (ESSENTIA_AUTO_FETCH=false) for fully offline/air-gapped runs;
    # analysis then degrades to model-free MIR (genre/mood left null).
    essentia_auto_fetch: bool = True
    # Local working dir for the LanceDB index pulled from / pushed to B2.
    index_cache_dir: str = "data/index-cache"

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


settings = Settings()

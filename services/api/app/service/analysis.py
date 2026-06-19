"""Per-track analysis pipeline.

For each track: pull bytes from B2 (repo) -> Essentia MIR features -> CLAP
embedding -> write features/<id>.json back to B2 -> upsert the embedding into
the consolidated index manifest and sync it to B2. Every B2 byte moves through
`repo`, so the single custom-UA S3 client is always used; the engines only see
local files.
"""

import contextlib
import logging
import os
import tempfile
from datetime import UTC, datetime

from app.config import settings
from app.repo import download_file, get_json, put_bytes, put_json
from app.service.engines import clap_embed
from app.service.engines import index as index_engine
from app.service.engines.essentia_features import extract_features
from app.types import AnalyzedTrack, TrackFeatures

logger = logging.getLogger(__name__)

_INDEX_KEY = f"{settings.index_prefix}embeddings.npz"


def _features_key(track_key: str) -> str:
    """Map a track object key to its feature-JSON key under features/."""
    name = track_key[len(settings.tracks_prefix):] if track_key.startswith(
        settings.tracks_prefix
    ) else track_key
    return f"{settings.features_prefix}{name}.json"


def _suffix(track_key: str) -> str:
    ext = track_key.rsplit(".", 1)[-1] if "." in track_key else "audio"
    return f".{ext}"


def analyze_track(track_key: str) -> AnalyzedTrack:
    """Analyze a single track end-to-end and persist results to B2."""
    raw = download_file(track_key)

    fd, tmp_path = tempfile.mkstemp(suffix=_suffix(track_key))
    os.close(fd)
    embedded = False
    try:
        with open(tmp_path, "wb") as f:
            f.write(raw)

        mir = extract_features(tmp_path)

        embedding: list[float] | None = None
        try:
            embedding = clap_embed.embed_audio(tmp_path)
        except Exception:
            logger.warning("CLAP embedding failed for %s", track_key, exc_info=True)

        features = TrackFeatures(
            bpm=mir.get("bpm"),
            key=mir.get("key"),
            scale=mir.get("scale"),
            genre=mir.get("genre"),
            mood=mir.get("mood"),
            duration_seconds=mir.get("duration_seconds"),
            loudness_db=mir.get("loudness_db"),
            embedding_dims=len(embedding) if embedding else None,
        )
        put_json(_features_key(track_key), features.model_dump())

        if embedding is not None:
            _sync_embedding(track_key, embedding)
            embedded = True
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

    return AnalyzedTrack(
        key=track_key,
        features=features,
        analyzed_at=datetime.now(UTC),
        embedded=embedded,
    )


def _sync_embedding(track_key: str, embedding: list[float]) -> None:
    """Upsert one embedding into the B2 index manifest (read-modify-write)."""
    keys, vectors = index_engine.load_index(_read_index_blob())
    keys, vectors = index_engine.upsert(keys, vectors, track_key, embedding)
    blob = index_engine.serialize_index(keys, vectors)
    put_bytes(_INDEX_KEY, blob, "application/octet-stream")


def _read_index_blob() -> bytes | None:
    try:
        return download_file(_INDEX_KEY)
    except RuntimeError:
        # No index yet — first track analyzed.
        return None


def load_features(track_key: str) -> TrackFeatures | None:
    """Read a track's persisted feature JSON from B2, if present."""
    obj = get_json(_features_key(track_key))
    return TrackFeatures(**obj) if obj else None

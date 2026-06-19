"""Music Library service — the sample-scoped explorer over the tracks/ prefix.

This is distinct from the full-bucket File Explorer (service/files.py): the
library only ever lists objects under `settings.tracks_prefix`, joins each
track with its persisted feature JSON, and supports tag-based filtering.
"""

import logging

from app.config import settings
from app.repo import list_files
from app.service.analysis import load_features
from app.types import LibraryTrack, TrackFeatures

logger = logging.getLogger(__name__)


def _matches(features: TrackFeatures | None, genre, mood, bpm_min, bpm_max) -> bool:
    if genre and (not features or (features.genre or "").lower() != genre.lower()):
        return False
    if mood and (not features or (features.mood or "").lower() != mood.lower()):
        return False
    if bpm_min is not None and (not features or features.bpm is None or features.bpm < bpm_min):
        return False
    return not (
        bpm_max is not None
        and (not features or features.bpm is None or features.bpm > bpm_max)
    )


def list_tracks(
    genre: str | None = None,
    mood: str | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    limit: int = 200,
) -> list[LibraryTrack]:
    """List tracks under tracks/, joined with feature JSON, optionally filtered."""
    files = list_files(prefix=settings.tracks_prefix, max_keys=1000)
    tracks: list[LibraryTrack] = []
    for f in files:
        # Skip "directory marker" zero-byte keys that equal the prefix itself.
        if f.key == settings.tracks_prefix:
            continue
        features = load_features(f.key)
        if not _matches(features, genre, mood, bpm_min, bpm_max):
            continue
        tracks.append(
            LibraryTrack(
                key=f.key,
                filename=f.filename,
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                content_type=f.content_type,
                uploaded_at=f.uploaded_at,
                url=f.url,
                analyzed=features is not None,
                features=features,
            )
        )
    tracks.sort(key=lambda t: t.uploaded_at, reverse=True)
    return tracks[:limit]


def get_track_features(track_key: str) -> TrackFeatures | None:
    """Return persisted features for one track, or None if not yet analyzed."""
    return load_features(track_key)

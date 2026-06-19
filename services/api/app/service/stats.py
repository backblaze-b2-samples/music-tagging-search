"""Music dashboard aggregates.

Counts tracks under tracks/, how many have feature JSON (analyzed), how many
embeddings are in the index, total catalog storage, and genre/mood
distributions. All reads go through repo; no boto3 here.
"""

import logging
from collections import Counter

from app.config import settings
from app.repo import download_file, list_files
from app.service.analysis import load_features
from app.service.engines import index as index_engine
from app.types import MusicStats
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

_INDEX_KEY = f"{settings.index_prefix}embeddings.npz"


def _embeddings_indexed() -> int:
    try:
        blob = download_file(_INDEX_KEY)
    except RuntimeError:
        return 0
    keys, _ = index_engine.load_index(blob)
    return len(keys)


def get_music_stats() -> MusicStats:
    files = [
        f
        for f in list_files(prefix=settings.tracks_prefix, max_keys=1000)
        if f.key != settings.tracks_prefix
    ]

    analyzed = 0
    genres: Counter = Counter()
    moods: Counter = Counter()
    total_size = 0
    for f in files:
        total_size += f.size_bytes
        features = load_features(f.key)
        if features is not None:
            analyzed += 1
            if features.genre:
                genres[features.genre] += 1
            if features.mood:
                moods[features.mood] += 1

    return MusicStats(
        total_tracks=len(files),
        analyzed_tracks=analyzed,
        embeddings_indexed=_embeddings_indexed(),
        total_size_bytes=total_size,
        total_size_human=humanize_bytes(total_size),
        genre_distribution=dict(genres),
        mood_distribution=dict(moods),
    )

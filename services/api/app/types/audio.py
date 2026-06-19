from datetime import datetime

from pydantic import BaseModel


class TrackFeatures(BaseModel):
    """MIR features extracted from a single track by Essentia + CLAP."""

    bpm: float | None = None
    key: str | None = None
    scale: str | None = None  # "major" / "minor"
    genre: str | None = None
    mood: str | None = None
    duration_seconds: float | None = None
    loudness_db: float | None = None
    # Length of the CLAP embedding stored in the index (not the vector itself).
    embedding_dims: int | None = None


class AnalyzedTrack(BaseModel):
    """Result of running the analysis pipeline over one track."""

    key: str
    features: TrackFeatures
    analyzed_at: datetime
    embedded: bool = False


class LibraryTrack(BaseModel):
    """A track in the /library view: storage metadata joined with features."""

    key: str
    filename: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None
    analyzed: bool = False
    features: TrackFeatures | None = None


class SimilarResult(BaseModel):
    """One neighbor returned by find-similar / semantic search."""

    key: str
    filename: str
    score: float  # cosine similarity in [0, 1]
    features: TrackFeatures | None = None


class SearchResult(BaseModel):
    """Ranked results for a text->audio semantic search query."""

    query: str
    results: list[SimilarResult]


class MusicStats(BaseModel):
    """Dashboard aggregates for the music catalog."""

    total_tracks: int
    analyzed_tracks: int
    embeddings_indexed: int
    total_size_bytes: int
    total_size_human: str
    genre_distribution: dict[str, int]
    mood_distribution: dict[str, int]

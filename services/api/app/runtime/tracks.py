import logging

from fastapi import APIRouter, HTTPException

from app.repo import get_stream_url
from app.service.analysis import analyze_track
from app.service.files import FileKeyError, validate_key
from app.service.library import get_track_features, list_tracks
from app.service.search import find_similar, semantic_search
from app.service.stats import get_music_stats
from app.types import (
    AnalyzedTrack,
    LibraryTrack,
    MusicStats,
    SearchResult,
    SimilarResult,
    TrackFeatures,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tracks", response_model=list[LibraryTrack])
async def list_tracks_endpoint(
    genre: str | None = None,
    mood: str | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    limit: int = 200,
):
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be 1..1000")
    return list_tracks(
        genre=genre, mood=mood, bpm_min=bpm_min, bpm_max=bpm_max, limit=limit
    )


@router.get("/tracks/stats", response_model=MusicStats)
async def music_stats_endpoint():
    return get_music_stats()


@router.get("/search", response_model=SearchResult)
async def search_endpoint(q: str, top_k: int = 10):
    if not q.strip():
        raise HTTPException(status_code=400, detail="q must not be empty")
    if top_k < 1 or top_k > 50:
        raise HTTPException(status_code=400, detail="top_k must be 1..50")
    return semantic_search(q, top_k=top_k)


@router.post("/tracks/{key:path}/analyze", response_model=AnalyzedTrack)
async def analyze_endpoint(key: str):
    _validate(key)
    try:
        return analyze_track(key)
    except RuntimeError as e:
        logger.warning("Analysis failed for %s: %s", key, e)
        raise HTTPException(status_code=502, detail="Analysis failed") from None


@router.get("/tracks/{key:path}/features", response_model=TrackFeatures)
async def features_endpoint(key: str):
    _validate(key)
    features = get_track_features(key)
    if features is None:
        raise HTTPException(status_code=404, detail="Track not analyzed yet")
    return features


@router.get("/tracks/{key:path}/similar", response_model=list[SimilarResult])
async def similar_endpoint(key: str, top_k: int = 10):
    _validate(key)
    if top_k < 1 or top_k > 50:
        raise HTTPException(status_code=400, detail="top_k must be 1..50")
    return find_similar(key, top_k=top_k)


@router.get("/tracks/{key:path}/stream")
async def stream_endpoint(key: str):
    _validate(key)
    try:
        url = get_stream_url(key)
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to presign") from None
    return {"url": url}


def _validate(key: str) -> None:
    try:
        validate_key(key)
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None

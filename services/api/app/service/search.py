"""Similarity + semantic search over the CLAP embedding index.

`find_similar` does audio->audio "more like this" using a track's own embedding
(looked up in the index). `semantic_search` does text->audio: it embeds the
free-text query with CLAP and ranks the catalog in the same joint space.

The index manifest is pulled from B2 through `repo` (custom UA holds); the
engines only see local numpy arrays.
"""

import logging
import os

from app.config import settings
from app.repo import download_file
from app.service.analysis import load_features
from app.service.engines import clap_embed
from app.service.engines import index as index_engine
from app.types import SearchResult, SimilarResult

logger = logging.getLogger(__name__)

_INDEX_KEY = f"{settings.index_prefix}embeddings.npz"


def _load_index():
    try:
        blob = download_file(_INDEX_KEY)
    except RuntimeError:
        return [], None
    return index_engine.load_index(blob)


def _build_results(neighbors: list[tuple[str, float]]) -> list[SimilarResult]:
    results: list[SimilarResult] = []
    for key, score in neighbors:
        filename = os.path.basename(key)
        results.append(
            SimilarResult(
                key=key,
                filename=filename,
                score=score,
                features=load_features(key),
            )
        )
    return results


def find_similar(track_key: str, top_k: int = 10) -> list[SimilarResult]:
    """Return tracks most similar to the given track (excludes itself)."""
    keys, vectors = _load_index()
    if vectors is None or track_key not in keys:
        return []
    query = vectors[keys.index(track_key)].tolist()
    neighbors = index_engine.search(
        keys, vectors, query, top_k=top_k, exclude_key=track_key
    )
    return _build_results(neighbors)


def semantic_search(text: str, top_k: int = 10) -> SearchResult:
    """Rank the catalog against a free-text query in the CLAP joint space."""
    keys, vectors = _load_index()
    if vectors is None or not keys:
        return SearchResult(query=text, results=[])
    query = clap_embed.embed_text(text)
    neighbors = index_engine.search(keys, vectors, query, top_k=top_k)
    return SearchResult(query=text, results=_build_results(neighbors))

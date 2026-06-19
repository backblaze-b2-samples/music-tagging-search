"""Vector index over CLAP embeddings.

Transport decision (recorded for reviewers): the index is shipped as a single
consolidated manifest blob — `index/embeddings.npz` — that moves to and from B2
as one object through the repo S3 client. This is the plan's *authorized
fallback*, chosen as primary because it is reproducible from a fresh clone and
keeps every B2 byte on the single custom-UA client. A LanceDB table is a
multi-file directory; syncing it over plain S3 object ops is fragile and would
need per-file list/upload/download, so we consolidate instead. Search is exact
cosine similarity over the in-memory matrix — correct and fast for catalog-scale
libraries, with no extra service to stand up.

This engine only ever touches local bytes and numpy arrays. All B2 I/O is done
by the service layer through `repo`, so the custom user agent always holds.
"""

import io
import logging

import numpy as np

logger = logging.getLogger(__name__)


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def load_index(blob: bytes | None) -> tuple[list[str], np.ndarray]:
    """Deserialize the index manifest blob into (keys, embedding matrix).

    An empty / missing blob yields an empty index.
    """
    if not blob:
        return [], np.zeros((0, 0), dtype=np.float32)
    data = np.load(io.BytesIO(blob), allow_pickle=True)
    keys = list(data["keys"])
    vectors = data["vectors"].astype(np.float32)
    return keys, vectors


def serialize_index(keys: list[str], vectors: np.ndarray) -> bytes:
    """Serialize (keys, vectors) into a portable .npz blob for B2."""
    buf = io.BytesIO()
    np.savez(
        buf,
        keys=np.array(keys, dtype=object),
        vectors=vectors.astype(np.float32),
    )
    return buf.getvalue()


def upsert(
    keys: list[str],
    vectors: np.ndarray,
    key: str,
    embedding: list[float],
) -> tuple[list[str], np.ndarray]:
    """Add or replace one track's embedding in the index, returning the new
    (keys, vectors). Pure function over local arrays — no B2."""
    vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
    if key in keys:
        idx = keys.index(key)
        vectors[idx] = vec
        return keys, vectors
    new_keys = [*keys, key]
    new_vectors = vec if vectors.size == 0 else np.vstack([vectors, vec])
    return new_keys, new_vectors


def search(
    keys: list[str],
    vectors: np.ndarray,
    query: list[float],
    top_k: int = 10,
    exclude_key: str | None = None,
) -> list[tuple[str, float]]:
    """Return the top_k (key, cosine_similarity) neighbors for a query vector.

    Scores are mapped to [0, 1]. `exclude_key` drops a self-match for
    find-similar queries.
    """
    if vectors.size == 0 or not keys:
        return []
    q = np.asarray(query, dtype=np.float32).reshape(1, -1)
    matrix = _normalize(vectors)
    qn = _normalize(q)
    sims = (matrix @ qn.T).ravel()
    order = np.argsort(-sims)
    results: list[tuple[str, float]] = []
    for idx in order:
        k = keys[idx]
        if exclude_key is not None and k == exclude_key:
            continue
        score = (float(sims[idx]) + 1.0) / 2.0  # cosine [-1,1] -> [0,1]
        results.append((k, round(score, 4)))
        if len(results) >= top_k:
            break
    return results

"""CLAP (Contrastive Language-Audio Pretraining) embeddings via laion-clap.

CLAP maps audio and text into a *shared* embedding space, which is what makes
both "find similar songs" (audio->audio) and "dreamy lo-fi piano" semantic
search (text->audio) work against the same index. The model is loaded lazily
on first use and cached for the process lifetime; weights are fetched once
from a public CDN (keyless). Embeddings are returned as plain `list[float]`
so callers never need numpy or torch.
"""

import logging
import threading

from app.config import settings

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def _get_model():
    """Lazy-load and cache the CLAP module (thread-safe)."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        import laion_clap

        logger.info("Loading CLAP model (%s) — first use only", settings.clap_model)
        model = laion_clap.CLAP_Module(enable_fusion=False)
        # No ckpt path => laion-clap downloads the default public checkpoint.
        model.load_ckpt()
        _model = model
        return _model


def embed_audio(audio_path: str) -> list[float]:
    """Embed a local audio file into the CLAP joint space."""
    model = _get_model()
    vec = model.get_audio_embedding_from_filelist(
        x=[audio_path], use_tensor=False
    )
    return [float(x) for x in vec[0]]


def embed_text(text: str) -> list[float]:
    """Embed a free-text query into the same CLAP joint space."""
    model = _get_model()
    vec = model.get_text_embedding([text, ""], use_tensor=False)
    return [float(x) for x in vec[0]]

"""Essentia-based MIR feature extraction.

Runs on a local audio file (never on B2 directly). BPM, key/scale, duration,
and loudness come from Essentia's standard algorithms, which need no model
files. Genre and mood come from Essentia-TensorFlow pretrained models *if*
the weights are present in `settings.essentia_models_dir` — otherwise those
fields are left as None and the rest of the pipeline carries on. Fetch the
optional models with `scripts/fetch-models.sh`.
"""

import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Essentia ships music genres in the Discogs/EffNet taxonomy; we collapse the
# raw label to a coarse genre string for the UI.
_GENRE_MODEL = "genre_discogs400-discogs-effnet-1.pb"
_MOOD_MODEL = "mood_acoustic-discogs-effnet-1.pb"


def _models_dir() -> Path:
    p = Path(settings.essentia_models_dir)
    if not p.is_absolute():
        # Anchor at services/api/ (four levels up from this file).
        p = Path(__file__).resolve().parents[4] / p
    return p


def extract_features(audio_path: str) -> dict:
    """Extract BPM, key/scale, duration, loudness from a local audio file.

    Returns a plain dict so the service layer can merge it with the embedding
    result without importing Essentia. Any extraction failure degrades to an
    empty dict rather than raising — partial features beat a hard failure.
    """
    try:
        import essentia.standard as es
    except Exception:
        logger.warning("Essentia not importable — skipping MIR features")
        return {}

    try:
        loader = es.MonoLoader(filename=audio_path)
        audio = loader()
        sample_rate = 44100

        rhythm = es.RhythmExtractor2013(method="multifeature")
        bpm, _, _, _, _ = rhythm(audio)

        key_extractor = es.KeyExtractor()
        key, scale, _ = key_extractor(audio)

        loudness = es.Loudness()(audio)
        duration = len(audio) / sample_rate

        features = {
            "bpm": round(float(bpm), 1),
            "key": key,
            "scale": scale,
            "duration_seconds": round(float(duration), 2),
            "loudness_db": round(float(loudness), 3),
        }
    except Exception:
        logger.warning("Essentia core feature extraction failed", exc_info=True)
        return {}

    features.update(_extract_genre_mood(audio_path))
    return features


def _extract_genre_mood(audio_path: str) -> dict:
    """Run the optional pretrained genre/mood models if their weights exist."""
    models = _models_dir()
    genre_path = models / _GENRE_MODEL
    mood_path = models / _MOOD_MODEL
    if not genre_path.exists() and not mood_path.exists():
        logger.info(
            "Essentia genre/mood models not found in %s — skipping "
            "(run scripts/fetch-models.sh to enable)",
            models,
        )
        return {}

    out: dict = {}
    try:
        import essentia.standard as es

        # Shared EffNet embedding feeding both classifier heads.
        embed_model = models / "discogs-effnet-bs64-1.pb"
        if not embed_model.exists():
            return {}
        embeddings = es.TensorflowPredictEffnetDiscogs(
            graphFilename=str(embed_model),
            output="PartitionedCall:1",
        )(es.MonoLoader(filename=audio_path, sampleRate=16000)())

        if genre_path.exists():
            preds = es.TensorflowPredict2D(graphFilename=str(genre_path))(
                embeddings
            )
            out["genre"] = _top_label(preds, genre_path)
        if mood_path.exists():
            preds = es.TensorflowPredict2D(graphFilename=str(mood_path))(
                embeddings
            )
            out["mood"] = _top_label(preds, mood_path)
    except Exception:
        logger.warning("Essentia genre/mood inference failed", exc_info=True)
    return out


def _top_label(predictions, model_path: Path) -> str | None:
    """Return the highest-probability label from a model's prediction matrix.

    Labels live in a sibling <model>.json metadata file shipped alongside the
    weights. Falls back to the class index if metadata is missing.
    """
    import json

    import numpy as np

    mean = np.mean(predictions, axis=0)
    idx = int(np.argmax(mean))
    meta = model_path.with_suffix(".json")
    if meta.exists():
        try:
            classes = json.loads(meta.read_text()).get("classes", [])
            if idx < len(classes):
                return str(classes[idx])
        except Exception:
            pass
    return f"class_{idx}"

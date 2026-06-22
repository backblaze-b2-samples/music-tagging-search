"""Essentia-based MIR feature extraction.

Runs on a local audio file (never on B2 directly). BPM, key/scale, duration,
and loudness come from Essentia's standard algorithms, which need no model
files. Genre and mood come from Essentia-TensorFlow pretrained models that are
fetched once from Essentia's public model CDN on first analysis (keyless: a
shared ~85 MB EffNet backbone plus small per-tag classifier heads). Set
ESSENTIA_AUTO_FETCH=false to opt out; if the models are unavailable (e.g. the
machine is offline) genre/mood degrade to None and the rest of the pipeline
carries on. `scripts/fetch-models.sh` can pre-populate the models for offline
runs.
"""

import logging
import urllib.request
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Essentia model CDN layout. The Discogs-EffNet backbone produces the embedding
# that feeds every classifier head, so it downloads once and is shared by the
# genre head and all mood heads.
_MODEL_BASE_URL = "https://essentia.upf.edu/models"
_EMBED_MODEL = "discogs-effnet-bs64-1.pb"
_GENRE_MODEL = "genre_discogs400-discogs-effnet-1.pb"
# Each mood is a binary head (mood vs non-mood). We run them all on the shared
# embedding and report the highest-confidence one as the track's dominant mood.
_MOOD_MODELS = {
    "happy": "mood_happy-discogs-effnet-1.pb",
    "sad": "mood_sad-discogs-effnet-1.pb",
    "aggressive": "mood_aggressive-discogs-effnet-1.pb",
    "relaxed": "mood_relaxed-discogs-effnet-1.pb",
    "party": "mood_party-discogs-effnet-1.pb",
}


def _model_files() -> list[tuple[str, str]]:
    """(remote CDN sub-path, local filename) for every file ensure_models pulls.

    Each `.pb` head ships a sibling `.json` carrying its class labels. Keep this
    in sync with the file list in `scripts/fetch-models.sh`.
    """
    files = [(f"feature-extractors/discogs-effnet/{_EMBED_MODEL}", _EMBED_MODEL)]
    for name in (_GENRE_MODEL, *_MOOD_MODELS.values()):
        head = name.split("-", 1)[0]  # e.g. "genre_discogs400", "mood_happy"
        base = name[:-3]  # strip ".pb"
        files.append((f"classification-heads/{head}/{name}", name))
        files.append((f"classification-heads/{head}/{base}.json", f"{base}.json"))
    return files


# Module-level guard so a batch run that can't reach the CDN doesn't retry the
# download for every single track.
_fetch_attempted = False


def _models_dir() -> Path:
    p = Path(settings.essentia_models_dir)
    if not p.is_absolute():
        # Anchor at services/api/ (four levels up from this file:
        # engines -> service -> app -> api == parents[3]).
        p = Path(__file__).resolve().parents[3] / p
    return p


def ensure_models() -> Path:
    """Fetch any missing Essentia genre/mood model files into the models dir.

    Idempotent and keyless: files already present are left untouched. Download
    failures are logged and swallowed so analysis degrades to model-free MIR
    rather than crashing. Returns the models directory.
    """
    global _fetch_attempted
    models = _models_dir()
    missing = [(remote, name) for remote, name in _model_files()
               if not (models / name).exists()]
    if not missing:
        return models
    if not settings.essentia_auto_fetch:
        logger.info(
            "Essentia models missing and auto-fetch disabled — genre/mood will "
            "be null (run scripts/fetch-models.sh or set ESSENTIA_AUTO_FETCH=true)"
        )
        return models
    if _fetch_attempted:
        return models
    _fetch_attempted = True

    models.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Fetching %d Essentia genre/mood model file(s) into %s "
        "(one-time, keyless, ~90 MB)", len(missing), models,
    )
    for remote, name in missing:
        url = f"{_MODEL_BASE_URL}/{remote}"
        dest = models / name
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            urllib.request.urlretrieve(url, tmp)
            tmp.replace(dest)
            logger.info("  fetched %s", name)
        except Exception:
            tmp.unlink(missing_ok=True)
            logger.warning("Failed to fetch Essentia model %s from %s", name, url,
                           exc_info=True)
    return models


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
    """Run the pretrained genre/mood models, fetching them once if needed."""
    models = ensure_models()
    embed_model = models / _EMBED_MODEL
    genre_path = models / _GENRE_MODEL
    if not embed_model.exists() or not genre_path.exists():
        logger.info("Essentia genre/mood models unavailable — tags left null")
        return {}

    out: dict = {}
    try:
        import essentia.standard as es

        # Shared EffNet embedding feeding the genre and mood heads.
        embeddings = es.TensorflowPredictEffnetDiscogs(
            graphFilename=str(embed_model),
            output="PartitionedCall:1",
        )(es.MonoLoader(filename=audio_path, sampleRate=16000)())

        genre = _genre_label(es, embeddings, genre_path)
        if genre:
            out["genre"] = genre
        mood = _dominant_mood(es, embeddings, models)
        if mood:
            out["mood"] = mood
    except Exception:
        logger.warning("Essentia genre/mood inference failed", exc_info=True)
    return out


def _genre_label(es, embeddings, genre_path: Path) -> str | None:
    """Top genre, collapsed from the Discogs 'Parent---Child' taxonomy."""
    # The genre_discogs400 graph is a SavedModel export, so it uses non-default
    # I/O node names (the mood heads below use the algorithm's defaults).
    preds = es.TensorflowPredict2D(
        graphFilename=str(genre_path),
        input="serving_default_model_Placeholder",
        output="PartitionedCall:0",
    )(embeddings)
    label = _top_label(preds, genre_path)
    # Discogs labels are hierarchical, e.g. "Electronic---House"; collapse to the
    # coarse parent genre for the UI.
    return label.split("---", 1)[0] if label else None


def _dominant_mood(es, embeddings, models: Path) -> str | None:
    """Pick the highest-confidence mood across the binary mood heads."""
    import numpy as np

    best_mood, best_score = None, -1.0
    for mood, filename in _MOOD_MODELS.items():
        path = models / filename
        if not path.exists():
            continue
        try:
            preds = es.TensorflowPredict2D(
                graphFilename=str(path), output="model/Softmax",
            )(embeddings)
            score = float(np.mean(preds, axis=0)[_positive_index(path)])
        except Exception:
            logger.warning("Essentia mood head %s failed", filename, exc_info=True)
            continue
        if score > best_score:
            best_mood, best_score = mood, score
    return best_mood


def _positive_index(model_path: Path) -> int:
    """Index of the positive ("mood") class in a binary head's label list.

    Mood heads label their two classes like ["happy", "non_happy"]; we want the
    one that isn't the "non_" negative. Falls back to index 0.
    """
    import json

    meta = model_path.with_suffix(".json")
    try:
        classes = json.loads(meta.read_text()).get("classes", [])
        for i, c in enumerate(classes):
            if not str(c).lower().replace(" ", "_").startswith("non_"):
                return i
    except Exception:
        pass
    return 0


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

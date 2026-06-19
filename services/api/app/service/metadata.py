import hashlib
import io
import logging
from datetime import UTC, datetime

from app.types import FileMetadataDetail
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


def _probe_audio(file_data: bytes) -> dict:
    """Cheap, dependency-light audio probe run at upload time.

    Returns duration / sample rate / channel count when the container is
    readable, and stays silent (returns {}) otherwise. The heavy MIR
    feature extraction (BPM, key, genre, mood) happens later in the
    analysis pipeline, not here.
    """
    try:
        import soundfile as sf

        with sf.SoundFile(io.BytesIO(file_data)) as f:
            frames = len(f)
            sample_rate = f.samplerate
            duration = frames / sample_rate if sample_rate else None
            return {
                "duration_seconds": round(duration, 2) if duration else None,
                "sample_rate": sample_rate or None,
                "channels": f.channels,
                "codec": f.subtype or None,
            }
    except Exception:
        # MP3 and some compressed formats aren't readable by libsndfile;
        # that's expected — the analysis pipeline decodes them with librosa.
        logger.info("Audio probe skipped (format not probe-able at upload)")
        return {}


def extract_metadata(
    file_data: bytes,
    filename: str,
    content_type: str,
) -> FileMetadataDetail:
    md5 = hashlib.md5(file_data, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(file_data).hexdigest()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    extra: dict = {}
    if content_type.startswith("audio/"):
        extra = _probe_audio(file_data)

    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=md5,
        sha256=sha256,
        uploaded_at=datetime.now(UTC),
        **extra,
    )

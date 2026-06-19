#!/usr/bin/env python
"""Batch-analyze every un-analyzed track under tracks/ and refresh the B2 index.

This is the primary pipeline entry point (`pnpm analyze` from the repo root).
The /tracks/{key}/analyze endpoint exists for on-demand re-analysis from the UI;
this script is what you run after bulk-uploading a catalog.

Run from the repo root:   pnpm analyze
Or directly:              cd services/api && .venv/bin/python scripts/analyze.py
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load repo-root .env so B2 creds resolve regardless of cwd.
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# Make `app` importable when run from services/api/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.repo import list_files, list_keys  # noqa: E402
from app.service.analysis import analyze_track  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("analyze")


def _already_analyzed() -> set[str]:
    """Return the set of track keys that already have a feature JSON."""
    feature_keys = list_keys(prefix=settings.features_prefix)
    analyzed: set[str] = set()
    for fk in feature_keys:
        # features/<name>.json  ->  tracks/<name>
        name = fk[len(settings.features_prefix):]
        if name.endswith(".json"):
            name = name[: -len(".json")]
        analyzed.add(f"{settings.tracks_prefix}{name}")
    return analyzed


def main() -> int:
    tracks = [
        f.key
        for f in list_files(prefix=settings.tracks_prefix, max_keys=1000)
        if f.key != settings.tracks_prefix
    ]
    if not tracks:
        logger.info("No tracks found under %s — upload some first.", settings.tracks_prefix)
        return 0

    done = _already_analyzed()
    pending = [t for t in tracks if t not in done]
    logger.info(
        "%d tracks total, %d already analyzed, %d to process.",
        len(tracks),
        len(done),
        len(pending),
    )

    failures = 0
    for i, key in enumerate(pending, 1):
        logger.info("[%d/%d] Analyzing %s", i, len(pending), key)
        try:
            result = analyze_track(key)
            logger.info(
                "  done: bpm=%s key=%s genre=%s embedded=%s",
                result.features.bpm,
                result.features.key,
                result.features.genre,
                result.embedded,
            )
        except Exception as e:
            failures += 1
            logger.error("  failed: %s", e)

    logger.info("Done. %d analyzed, %d failed.", len(pending) - failures, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

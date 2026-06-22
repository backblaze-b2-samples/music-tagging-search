#!/usr/bin/env bash
# Pre-fetch the Essentia-TensorFlow genre/mood models into the directory the
# backend reads (settings.essentia_models_dir, default
# services/api/data/essentia-models). These are public, keyless, one-time
# downloads. You normally DON'T need to run this: the backend auto-fetches the
# same files on the first analysis. Use it to warm the cache ahead of time or
# for an offline machine (then set ESSENTIA_AUTO_FETCH=false). Audio analysis
# works WITHOUT these — BPM, key/scale, duration, loudness, and CLAP embeddings
# all run model-free; only the genre/mood tags need them.
# Run from the repo root:  bash scripts/fetch-models.sh
set -euo pipefail

DEST="${ESSENTIA_MODELS_DIR:-services/api/data/essentia-models}"
BASE="https://essentia.upf.edu/models"

mkdir -p "$DEST"
echo "Downloading Essentia genre/mood models into $DEST ..."

# Shared Discogs-EffNet embedding backbone + the genre head and five binary
# mood heads (happy / sad / aggressive / relaxed / party). The .json sidecars
# carry the class labels the backend maps to. Keep this list in sync with
# _model_files() in services/api/app/service/engines/essentia_features.py.
FILES=(
  "feature-extractors/discogs-effnet/discogs-effnet-bs64-1.pb"
  "classification-heads/genre_discogs400/genre_discogs400-discogs-effnet-1.pb"
  "classification-heads/genre_discogs400/genre_discogs400-discogs-effnet-1.json"
  "classification-heads/mood_happy/mood_happy-discogs-effnet-1.pb"
  "classification-heads/mood_happy/mood_happy-discogs-effnet-1.json"
  "classification-heads/mood_sad/mood_sad-discogs-effnet-1.pb"
  "classification-heads/mood_sad/mood_sad-discogs-effnet-1.json"
  "classification-heads/mood_aggressive/mood_aggressive-discogs-effnet-1.pb"
  "classification-heads/mood_aggressive/mood_aggressive-discogs-effnet-1.json"
  "classification-heads/mood_relaxed/mood_relaxed-discogs-effnet-1.pb"
  "classification-heads/mood_relaxed/mood_relaxed-discogs-effnet-1.json"
  "classification-heads/mood_party/mood_party-discogs-effnet-1.pb"
  "classification-heads/mood_party/mood_party-discogs-effnet-1.json"
)

for path in "${FILES[@]}"; do
  name="$(basename "$path")"
  if [ -f "$DEST/$name" ]; then
    echo "  - $name already present, skipping"
    continue
  fi
  echo "  - $name"
  curl -fSL "$BASE/$path" -o "$DEST/$name"
done

echo "Done. Restart the API to pick up the models."

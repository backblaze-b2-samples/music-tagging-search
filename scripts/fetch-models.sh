#!/usr/bin/env bash
# Download the optional Essentia-TensorFlow pretrained genre/mood models into
# the directory the backend reads (settings.essentia_models_dir, default
# services/api/data/essentia-models). These are public, keyless, one-time
# downloads. Audio analysis works WITHOUT them — BPM, key/scale, duration,
# loudness, and CLAP embeddings all run model-free; only the genre/mood tags
# need these files. Run from the repo root:  bash scripts/fetch-models.sh
set -euo pipefail

DEST="${ESSENTIA_MODELS_DIR:-services/api/data/essentia-models}"
BASE="https://essentia.upf.edu/models"

mkdir -p "$DEST"
echo "Downloading Essentia genre/mood models into $DEST ..."

# Shared Discogs-EffNet embedding backbone + two classifier heads. The .json
# sidecars carry the human-readable class labels the backend maps to.
FILES=(
  "feature-extractors/discogs-effnet/discogs-effnet-bs64-1.pb"
  "classification-heads/genre_discogs400/genre_discogs400-discogs-effnet-1.pb"
  "classification-heads/genre_discogs400/genre_discogs400-discogs-effnet-1.json"
  "classification-heads/mood_acoustic/mood_acoustic-discogs-effnet-1.pb"
  "classification-heads/mood_acoustic/mood_acoustic-discogs-effnet-1.json"
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

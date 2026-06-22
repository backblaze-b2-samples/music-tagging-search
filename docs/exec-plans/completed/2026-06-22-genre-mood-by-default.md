# Plan: Genre & Mood by Default

## Problem
Genre and mood were fully wired end-to-end (types → extraction → persistence →
stats → filters → UI) but came back `null` on a fresh run: the Essentia models
were an opt-in manual download (`scripts/fetch-models.sh`) and the wired mood
model (`mood_acoustic`) only classified acoustic vs non-acoustic, not a real
mood. For a sample headlined "Music Tagging & Search", the marquee tags looked
broken out of the box.

## Scope
- Auto-fetch the genre/mood models on first analysis (keyless), keeping graceful
  degradation if the CDN is unreachable.
- Replace the binary `mood_acoustic` head with five real mood heads
  (happy / sad / aggressive / relaxed / party); report the strongest as `mood`.
- Collapse Discogs `Parent---Child` genre labels to the coarse parent for the UI.
- Add an `ESSENTIA_AUTO_FETCH` setting (default true) for offline/air-gapped runs.
- Keep `scripts/fetch-models.sh` as an optional offline pre-fetch, in sync with
  the Python manifest.
- Update docs (README, RELIABILITY, dev-workflows, audio-analysis).

## Steps (done)
1. `config/settings.py` — add `essentia_auto_fetch`; reframe `essentia_models_dir`.
2. `service/engines/essentia_features.py` — `ensure_models()` (idempotent,
   once-per-process, graceful), five mood heads + dominant-mood selection,
   genre `---` collapse.
3. `scripts/fetch-models.sh` — swap `mood_acoustic` for the five mood heads.
4. Docs updated per the §9 mapping.
5. Verified: ruff clean, structure tests pass, Essentia TF algos present, model
   URLs return 200, label formats match (`['happy','non_happy']`, `Blues---…`).

## Follow-up / not done here
- No automated test exercises real inference (needs the 90 MB models + audio +
  TF). Existing structural tests cover the engine boundary. Consider a smoke
  test gated on model presence.
- Tracks analyzed *before* this change keep `genre/mood = null` in their
  `features/<id>.json`; they need re-analysis (UI Analyze, or delete this app's
  `features/` JSONs and re-run `pnpm analyze`) to backfill.

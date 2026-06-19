"use client";

import { Badge } from "@/components/ui/badge";
import type { TrackFeatures } from "@music-tagging-search/shared";

function fmtDuration(seconds: number | null): string | null {
  if (seconds === null) return null;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Read-only badges for a track's extracted MIR features (BPM, key, genre,
 * mood, duration). Renders nothing when the track hasn't been analyzed. */
export function TrackTags({ features }: { features: TrackFeatures | null }) {
  if (!features) {
    return (
      <span className="text-xs text-muted-foreground italic">
        Not analyzed yet
      </span>
    );
  }

  const duration = fmtDuration(features.duration_seconds);
  const keyLabel =
    features.key && features.scale
      ? `${features.key} ${features.scale}`
      : features.key;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {features.bpm !== null && (
        <Badge variant="secondary" className="font-mono text-[11px]">
          {Math.round(features.bpm)} BPM
        </Badge>
      )}
      {keyLabel && (
        <Badge variant="secondary" className="text-[11px]">
          {keyLabel}
        </Badge>
      )}
      {features.genre && (
        <Badge variant="outline" className="text-[11px]">
          {features.genre}
        </Badge>
      )}
      {features.mood && (
        <Badge variant="outline" className="text-[11px]">
          {features.mood}
        </Badge>
      )}
      {duration && (
        <span className="text-[11px] text-muted-foreground font-mono">
          {duration}
        </span>
      )}
    </div>
  );
}

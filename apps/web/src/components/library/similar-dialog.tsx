"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Music } from "lucide-react";
import { TrackTags } from "./track-tags";
import { TrackPlayer } from "./track-player";
import { useSimilar } from "@/lib/queries";

interface SimilarDialogProps {
  trackKey: string | null;
  filename: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** "More like this" — shows nearest neighbors for a track from the CLAP index. */
export function SimilarDialog({
  trackKey,
  filename,
  open,
  onOpenChange,
}: SimilarDialogProps) {
  const { data, isLoading, error, refetch } = useSimilar(
    trackKey ?? undefined,
    open && !!trackKey,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="truncate">
            Similar to {filename ?? "track"}
          </DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : !data || data.length === 0 ? (
          <EmptyState
            icon={Music}
            title="No similar tracks"
            description="Analyze more tracks to grow the embedding index."
          />
        ) : (
          <div className="space-y-3">
            {data.map((r) => (
              <div
                key={r.key}
                className="flex flex-col gap-2 rounded-md border border-border p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium truncate">{r.filename}</span>
                  <span className="font-mono text-xs text-muted-foreground tabular-nums">
                    {(r.score * 100).toFixed(0)}% match
                  </span>
                </div>
                <TrackTags features={r.features} />
                <TrackPlayer trackKey={r.key} />
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

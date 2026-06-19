"use client";

import { useMemo, useState } from "react";
import { Sparkles, GitCompareArrows, RefreshCw, Music } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TrackTags } from "./track-tags";
import { TrackPlayer } from "./track-player";
import { SimilarDialog } from "./similar-dialog";
import { useAnalyzeTrack, useTracks } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";
import type { LibraryTrack } from "@music-tagging-search/shared";

/** The sample-scoped explorer: browses only the tracks/ prefix, joined with
 * each track's extracted features. Distinct from the full-bucket /files
 * explorer, which stays for browsing everything in the bucket. */
export function MusicLibrary() {
  const { data: tracks = [], isLoading, isFetching, error, refetch } = useTracks();
  const analyze = useAnalyzeTrack();
  const [genreFilter, setGenreFilter] = useState("");
  const [moodFilter, setMoodFilter] = useState("");
  const [similarTrack, setSimilarTrack] = useState<LibraryTrack | null>(null);

  // Filter client-side over the already-fetched, feature-joined rows so tag
  // toggles feel instant (the API supports server-side filters too).
  const filtered = useMemo(() => {
    const g = genreFilter.trim().toLowerCase();
    const m = moodFilter.trim().toLowerCase();
    return tracks.filter((t) => {
      if (g && (t.features?.genre ?? "").toLowerCase() !== g) return false;
      if (m && (t.features?.mood ?? "").toLowerCase() !== m) return false;
      return true;
    });
  }, [tracks, genreFilter, moodFilter]);

  const handleAnalyze = (key: string, filename: string) => {
    analyze.mutate(key, {
      onSuccess: () => toast.success(`Analyzed ${filename}`),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Analysis failed"),
    });
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b border-border py-4 px-5 space-y-0">
          <CardTitle className="card-title">Tracks</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="Filter genre"
              value={genreFilter}
              onChange={(e) => setGenreFilter(e.target.value)}
              className="h-8 w-32 text-xs"
            />
            <Input
              placeholder="Filter mood"
              value={moodFilter}
              onChange={(e) => setMoodFilter(e.target.value)}
              className="h-8 w-32 text-xs"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="h-8 text-xs"
              disabled={isFetching}
            >
              <RefreshCw
                className={`h-3.5 w-3.5 mr-1 ${isFetching ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-3">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={Music}
              title={tracks.length === 0 ? "No tracks yet" : "No matches"}
              description={
                tracks.length === 0
                  ? "Upload audio on the Upload page to start your catalog."
                  : "No tracks match those tag filters."
              }
            />
          ) : (
            <div className="space-y-2">
              {filtered.map((t) => (
                <div
                  key={t.key}
                  className="flex flex-col gap-2 rounded-md border border-border p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0 space-y-1.5">
                    <div className="font-medium truncate">{t.filename}</div>
                    <TrackTags features={t.features} />
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <TrackPlayer trackKey={t.key} />
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8"
                      disabled={analyze.isPending}
                      onClick={() => handleAnalyze(t.key, t.filename)}
                    >
                      <Sparkles className="h-3.5 w-3.5 mr-1" />
                      {t.analyzed ? "Re-analyze" : "Analyze"}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8"
                      disabled={!t.analyzed}
                      onClick={() => setSimilarTrack(t)}
                    >
                      <GitCompareArrows className="h-3.5 w-3.5 mr-1" />
                      Find similar
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <SimilarDialog
        trackKey={similarTrack?.key ?? null}
        filename={similarTrack?.filename ?? null}
        open={!!similarTrack}
        onOpenChange={(open) => !open && setSimilarTrack(null)}
      />
    </>
  );
}

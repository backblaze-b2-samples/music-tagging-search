"use client";

import { useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TrackTags } from "@/components/library/track-tags";
import { TrackPlayer } from "@/components/library/track-player";
import { useSemanticSearch } from "@/lib/queries";

const EXAMPLES = [
  "dreamy lo-fi with mellow piano",
  "energetic upbeat synth pop",
  "dark cinematic tension",
];

/** Text -> audio semantic search. The query is embedded with CLAP and ranked
 * against the catalog in the joint embedding space (reuses the index that
 * powers find-similar). */
export function SemanticSearch() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const { data, isLoading, error, refetch, isFetching } = useSemanticSearch(
    query,
    query.length > 0,
  );

  const run = (q: string) => {
    setInput(q);
    setQuery(q.trim());
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(input);
        }}
        className="flex flex-wrap items-center gap-2"
      >
        <Input
          placeholder="Describe the sound you want..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="h-10 flex-1 min-w-[240px]"
        />
        <Button type="submit" className="h-10" disabled={!input.trim() || isFetching}>
          <SearchIcon className="h-4 w-4 mr-1.5" />
          Search
        </Button>
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => run(ex)}
            className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors"
          >
            {ex}
          </button>
        ))}
      </div>

      {query.length === 0 ? (
        <EmptyState
          icon={SearchIcon}
          title="Search your catalog by vibe"
          description="Type a description and CLAP finds the closest-sounding tracks."
        />
      ) : isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          icon={SearchIcon}
          title="No results"
          description="Analyze tracks first so the embedding index has something to search."
        />
      ) : (
        <div className="space-y-3">
          {data.results.map((r) => (
            <Card key={r.key}>
              <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{r.filename}</span>
                    <span className="font-mono text-xs text-muted-foreground tabular-nums">
                      {(r.score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <TrackTags features={r.features} />
                </div>
                <TrackPlayer trackKey={r.key} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

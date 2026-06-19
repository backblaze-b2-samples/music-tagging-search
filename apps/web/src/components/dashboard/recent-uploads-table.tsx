"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ArrowRight, Music } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useTracks } from "@/lib/queries";

/** Recently analyzed tracks with their extracted MIR features. Tracks already
 * arrive newest-first from the API; we keep only those that have features. */
export function RecentTracksTable() {
  const { data: tracks = [], isLoading, error, refetch } = useTracks();

  const analyzed = useMemo(
    () => tracks.filter((t) => t.analyzed && t.features).slice(0, 10),
    [tracks],
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recently Analyzed</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/library"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View library
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : analyzed.length === 0 ? (
          <EmptyState
            icon={Music}
            title="No analyzed tracks yet"
            description="Upload audio and run Analyze in the Library."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[36%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Track
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  BPM
                </TableHead>
                <TableHead className="w-[16%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Key
                </TableHead>
                <TableHead className="w-[17%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Genre
                </TableHead>
                <TableHead className="w-[17%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Mood
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {analyzed.map((t) => (
                <TableRow key={t.key} className="table-row-hover">
                  <TableCell className="font-medium">
                    <div className="truncate">{t.filename}</div>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {t.features?.bpm !== null && t.features?.bpm !== undefined
                      ? Math.round(t.features.bpm)
                      : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {t.features?.key
                      ? `${t.features.key}${t.features.scale ? " " + t.features.scale : ""}`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap truncate">
                    {t.features?.genre ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap truncate">
                    {t.features?.mood ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  analyzeTrack,
  ApiError,
  deleteFile,
  getFiles,
  getFileStats,
  getMusicStats,
  getPreviewUrl,
  getSimilar,
  getTracks,
  getUploadActivity,
  semanticSearch,
} from "@/lib/api-client";
import type { FileMetadata, LibraryTrack } from "@music-tagging-search/shared";

export interface TrackFilters {
  genre?: string;
  mood?: string;
  bpmMin?: number;
  bpmMax?: number;
}

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  tracks: (filters?: TrackFilters) =>
    [...qk.all, "tracks", filters ?? {}] as const,
  musicStats: () => [...qk.all, "music-stats"] as const,
  similar: (key: string) => [...qk.all, "similar", key] as const,
  search: (query: string) => [...qk.all, "search", query] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Music tagging & search ---

export function useTracks(filters?: TrackFilters) {
  return useQuery<LibraryTrack[], ApiError>({
    queryKey: qk.tracks(filters),
    queryFn: () => getTracks(filters),
  });
}

export function useMusicStats() {
  return useQuery({
    queryKey: qk.musicStats(),
    queryFn: getMusicStats,
  });
}

export function useSimilar(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.similar(key ?? ""),
    queryFn: () => getSimilar(key as string),
    enabled: enabled && !!key,
  });
}

export function useSemanticSearch(query: string, enabled: boolean) {
  return useQuery({
    queryKey: qk.search(query),
    queryFn: () => semanticSearch(query),
    enabled: enabled && query.trim().length > 0,
  });
}

export function useAnalyzeTrack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trackKey: string) => analyzeTrack(trackKey),
    // Re-analysis changes features, the index, and dashboard aggregates.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

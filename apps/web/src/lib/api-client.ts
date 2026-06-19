import type {
  AnalyzedTrack,
  DailyUploadCount,
  FileMetadata,
  FileUploadResponse,
  LibraryTrack,
  MusicStats,
  SearchResult,
  SimilarResult,
  TrackFeatures,
  UploadStats,
} from "@music-tagging-search/shared";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Typed API error with HTTP status code for caller-side branching. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True for 408, 429, 500, 502, 503, 504 — worth retrying. */
  get isRetryable(): boolean {
    return [408, 429, 500, 502, 503, 504].includes(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    // Network failure (offline, DNS, CORS, etc.)
    throw new ApiError("Network error — check your connection", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail || `API error: ${res.status}`,
      res.status,
    );
  }
  return res.json();
}

export async function getHealth() {
  return apiFetch<{ status: string; b2_connected: boolean }>("/health");
}

export async function getFiles(prefix = "", limit = 100) {
  return apiFetch<FileMetadata[]>(
    `/files?prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );
}

export async function getFileStats() {
  return apiFetch<UploadStats>("/files/stats");
}

export async function getUploadActivity(days = 7) {
  return apiFetch<DailyUploadCount[]>(`/files/stats/activity?days=${days}`);
}

export async function getFile(key: string) {
  return apiFetch<FileMetadata>(`/files/${key}`);
}

export async function getDownloadUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/download`);
}

/** Preview-only presigned URL — does NOT increment the download counter. */
export async function getPreviewUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/preview`);
}

export async function deleteFile(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/files/${key}`, {
    method: "DELETE",
  });
}

// --- Music tagging & search ---

function trackQuery(filters?: {
  genre?: string;
  mood?: string;
  bpmMin?: number;
  bpmMax?: number;
}) {
  const params = new URLSearchParams();
  if (filters?.genre) params.set("genre", filters.genre);
  if (filters?.mood) params.set("mood", filters.mood);
  if (filters?.bpmMin !== undefined) params.set("bpm_min", String(filters.bpmMin));
  if (filters?.bpmMax !== undefined) params.set("bpm_max", String(filters.bpmMax));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function getTracks(filters?: {
  genre?: string;
  mood?: string;
  bpmMin?: number;
  bpmMax?: number;
}) {
  return apiFetch<LibraryTrack[]>(`/tracks${trackQuery(filters)}`);
}

export async function getMusicStats() {
  return apiFetch<MusicStats>("/tracks/stats");
}

export async function getTrackFeatures(key: string) {
  return apiFetch<TrackFeatures>(`/tracks/${key}/features`);
}

export async function getStreamUrl(key: string) {
  return apiFetch<{ url: string }>(`/tracks/${key}/stream`);
}

export async function analyzeTrack(key: string) {
  return apiFetch<AnalyzedTrack>(`/tracks/${key}/analyze`, { method: "POST" });
}

export async function getSimilar(key: string, topK = 10) {
  return apiFetch<SimilarResult[]>(`/tracks/${key}/similar?top_k=${topK}`);
}

export async function semanticSearch(query: string, topK = 10) {
  return apiFetch<SearchResult>(
    `/search?q=${encodeURIComponent(query)}&top_k=${topK}`,
  );
}

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<FileUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new ApiError(body.detail || `Upload failed: ${xhr.status}`, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError("Network error — check your connection", 0)),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError("Upload aborted", 0)),
    );

    xhr.open("POST", `${API_BASE}/upload`);
    xhr.send(formData);
  });
}

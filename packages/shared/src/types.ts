export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Audio-specific (cheap probe at upload time)
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
  sample_rate: number | null;
  channels: number | null;
}

// --- Music tagging & search ---

export interface TrackFeatures {
  bpm: number | null;
  key: string | null;
  scale: string | null;
  genre: string | null;
  mood: string | null;
  duration_seconds: number | null;
  loudness_db: number | null;
  embedding_dims: number | null;
}

export interface LibraryTrack {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  analyzed: boolean;
  features: TrackFeatures | null;
}

export interface AnalyzedTrack {
  key: string;
  features: TrackFeatures;
  analyzed_at: string;
  embedded: boolean;
}

export interface SimilarResult {
  key: string;
  filename: string;
  score: number;
  features: TrackFeatures | null;
}

export interface SearchResult {
  query: string;
  results: SimilarResult[];
}

export interface MusicStats {
  total_tracks: number;
  analyzed_tracks: number;
  embeddings_indexed: number;
  total_size_bytes: number;
  total_size_human: string;
  genre_distribution: Record<string, number>;
  mood_distribution: Record<string, number>;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Upload Tracks</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Drag audio in or click to browse. MP3, WAV, FLAC, OGG, AAC/M4A — up
          to 200 MB per file. Tracks land under the <code>tracks/</code> prefix.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}

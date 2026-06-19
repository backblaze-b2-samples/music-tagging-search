import Link from "next/link";
import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { MusicLibrary } from "@/components/library/music-library";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Music Library</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your catalog under the <code>tracks/</code> prefix — play, tag, and
            find similar songs. Browse the whole bucket on the Files page.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/upload">
            <Upload className="h-3.5 w-3.5" />
            Upload tracks
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <MusicLibrary />
      </div>
    </div>
  );
}

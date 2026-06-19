"use client";

import { useState } from "react";
import { Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiError, getStreamUrl } from "@/lib/api-client";

/** Inline HTML5 audio player. The presigned stream URL is fetched lazily on
 * first Play so we don't presign every row up front. Once loaded the native
 * <audio> controls take over (seek, volume, etc.). */
export function TrackPlayer({ trackKey }: { trackKey: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getStreamUrl(trackKey);
      setUrl(res.url);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to load stream";
      toast.error(detail);
    } finally {
      setLoading(false);
    }
  };

  if (url) {
    return <audio src={url} controls autoPlay className="h-9 w-full max-w-xs" />;
  }

  return (
    <Button
      variant="outline"
      size="sm"
      className="h-8"
      onClick={load}
      disabled={loading}
    >
      <Play className="h-3.5 w-3.5 mr-1" />
      {loading ? "Loading..." : "Play"}
    </Button>
  );
}

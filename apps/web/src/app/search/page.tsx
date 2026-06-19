import { SemanticSearch } from "@/components/search/semantic-search";

export default function SearchPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Semantic Search</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Describe a sound in plain English; CLAP turns it into a query over
          your catalog and ranks the closest tracks.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <SemanticSearch />
      </div>
    </div>
  );
}

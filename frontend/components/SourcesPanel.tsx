import type { FileCitation, Source } from "@/lib/types";

export default function SourcesPanel({
  sources,
  files,
}: {
  sources: Source[];
  files: FileCitation[];
}) {
  if (sources.length === 0 && files.length === 0) return null;
  return (
    <div className="mt-3 rounded-lg border border-edge bg-panel p-3 text-sm">
      {sources.length > 0 && (
        <>
          <div className="text-xs uppercase tracking-wider text-muted mb-2">
            Web sources
          </div>
          <ol className="space-y-2">
            {sources.map((s, i) => (
              <li key={s.id} className="flex gap-2">
                <span className="text-accent font-mono">[{i + 1}]</span>
                <div className="min-w-0">
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-white hover:text-accent truncate block"
                  >
                    {s.title}
                  </a>
                  <div className="text-xs text-muted flex gap-2 flex-wrap">
                    <span>{s.domain}</span>
                    <span className="px-1.5 rounded bg-card border border-edge">
                      {s.source_type}
                    </span>
                    <span title="credibility prior">
                      cred {Math.round(s.credibility_score * 100)}%
                    </span>
                    {s.published_at && <span>· {s.published_at}</span>}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}

      {files.length > 0 && (
        <div className={sources.length ? "mt-3" : ""}>
          <div className="text-xs uppercase tracking-wider text-muted mb-2">
            File citations
          </div>
          <ul className="space-y-1">
            {files.map((f, i) => (
              <li key={f.chunk_id} className="text-xs">
                <span className="text-accent font-mono">[F{i + 1}]</span>{" "}
                <span className="text-white">{f.filename}</span>
                {f.page ? <span className="text-muted"> · p.{f.page}</span> : null}
                <div className="text-muted truncate">{f.excerpt}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

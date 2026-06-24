import type { ChatMessage } from "@/lib/types";
import ConfidenceBadge from "./ConfidenceBadge";
import ReasoningSummary from "./ReasoningSummary";
import SourcesPanel from "./SourcesPanel";

export default function Message({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-xl px-4 py-3 border ${
            isUser
              ? "bg-accentdim/20 border-accent/30 text-white"
              : "bg-card border-edge text-[#e6e6e9]"
          }`}
        >
          {!isUser && msg.response && (
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-mono text-muted uppercase">
                {msg.response.mode}
              </span>
              <ConfidenceBadge value={msg.response.confidence} />
            </div>
          )}
          <div className="prose-jarvis">{msg.content}</div>
        </div>

        {!isUser && msg.response && (
          <>
            <SourcesPanel
              sources={msg.response.sources}
              files={msg.response.file_citations}
            />
            <ReasoningSummary resp={msg.response} />
          </>
        )}
      </div>
    </div>
  );
}

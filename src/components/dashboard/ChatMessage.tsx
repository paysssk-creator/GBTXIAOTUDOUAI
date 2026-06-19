import type { ChatMessage } from "@/data/mockData";

export default function ChatMsg({ message }: { message: ChatMessage }) {
  const { role, content, timestamp } = message;

  if (role === "system") return (
    <div className="flex items-baseline gap-2 py-0.5">
      <span className="font-mono text-xs text-warning shrink-0">[SYSTEM]</span>
      <span className="font-mono text-xs text-muted-foreground flex-1">{content}</span>
      <span className="font-mono text-[10px] text-muted-foreground/40 shrink-0">{timestamp}</span>
    </div>
  );

  if (role === "user") return (
    <div className="flex items-baseline gap-2 py-1.5 mt-1">
      <span className="font-mono text-sm text-gain shrink-0 leading-none">›</span>
      <span className="font-mono text-sm text-primary flex-1">{content}</span>
      <span className="font-mono text-[10px] text-muted-foreground/40 shrink-0">{timestamp}</span>
    </div>
  );

  return (
    <div className="py-1.5 pl-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-mono text-xs font-semibold text-primary">[GBT]</span>
        <span className="font-mono text-[10px] text-muted-foreground/40">{timestamp}</span>
      </div>
      <div className="font-mono text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap border-l-2 border-primary/30 pl-2">
        {content}
      </div>
    </div>
  );
}

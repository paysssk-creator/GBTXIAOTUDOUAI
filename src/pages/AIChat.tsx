import { useRef, useEffect } from "react";
import { Send, Zap, RotateCcw, StopCircle } from "lucide-react";
import MarketTickerBar from "@/components/dashboard/MarketTickerBar";
import { useAIChat } from "@/hooks/useAIChat";
import { cn } from "@/lib/utils";
import { useState } from "react";

export default function AIChat() {
  const { messages, isLoading, error, sendMessage, cancel, resetChat } = useAIChat();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const send = () => {
    const text = input.trim();
    if (!text || isLoading) return;
    sendMessage(text);
    setInput("");
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <MarketTickerBar />
      <div className="flex-1 flex flex-col min-h-0 p-6">
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div>
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />AI 对话终端
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">DeepSeek V4 Pro · A 股专业分析助手</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={resetChat} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground border border-border rounded-lg px-3 py-2 hover:border-primary/30 transition-all">
              <RotateCcw className="w-3 h-3" />新对话
            </button>
            <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground border border-border rounded-lg px-3 py-2">
              <span className="w-2 h-2 rounded-full bg-gain animate-pulse-dot" style={{ color: "hsl(var(--gain))" }} />
              在线
            </div>
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col rounded-xl border border-border overflow-hidden min-h-0"
          style={{ background: "hsl(var(--terminal-bg))" }}>
          <div className="flex-1 overflow-auto p-5 space-y-3 min-h-0">
            {/* System message */}
            <div className="flex items-baseline gap-2 py-0.5">
              <span className="font-mono text-xs text-warning shrink-0">[SYSTEM]</span>
              <span className="font-mono text-xs text-muted-foreground">GBT Pro v2.1 — AI 驱动 A 股自主交易终端 — DeepSeek V4 Pro</span>
            </div>

            {messages.map((msg, i) => (
              <div key={i} className="animate-slide-up">
                {msg.role === "user" ? (
                  <div className="flex items-baseline gap-2 py-1.5">
                    <span className="font-mono text-sm text-gain shrink-0 leading-none">›</span>
                    <span className="font-mono text-sm text-primary flex-1">{msg.content}</span>
                  </div>
                ) : (
                  <div className="py-1.5 pl-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs font-semibold text-primary">[GBT]</span>
                    </div>
                    <div className="font-mono text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap border-l-2 border-primary/30 pl-2">
                      {msg.content}
                      {msg.isStreaming && <span className="animate-blink">▌</span>}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {isLoading && messages.length > 0 && messages[messages.length - 1]?.role === "assistant" && !messages[messages.length - 1]?.content && (
              <div className="flex items-center gap-2 py-1.5 pl-4">
                <span className="font-mono text-xs text-primary font-semibold">[GBT]</span>
                <span className="font-mono text-sm text-muted-foreground">
                  思考中<span className="animate-blink">▌</span>
                </span>
              </div>
            )}

            {error && (
              <div className="flex items-baseline gap-2 py-1 pl-4">
                <span className="font-mono text-xs text-loss shrink-0">[ERROR]</span>
                <span className="font-mono text-xs text-loss">{error}</span>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="border-t border-border px-4 py-3 flex items-center gap-3 bg-surface-base shrink-0">
            <span className="font-mono text-base text-gain font-bold shrink-0">›</span>
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="输入分析指令或市场问题..."
              disabled={isLoading}
              className="flex-1 bg-transparent border-none outline-none font-mono text-sm text-foreground placeholder:text-muted-foreground disabled:opacity-40"
              style={{ caretColor: "hsl(var(--primary))" }}
              autoFocus
            />
            {isLoading ? (
              <button onClick={cancel}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-loss/20 text-loss text-xs font-semibold transition-opacity hover:opacity-90 shrink-0">
                <StopCircle className="w-3 h-3" />停止
              </button>
            ) : (
              <button onClick={send} disabled={!input.trim()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold transition-opacity hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed shrink-0">
                <Send className="w-3 h-3" />发送
              </button>
            )}
          </div>
        </div>

        {/* Quick prompts */}
        <div className="flex flex-wrap gap-2 mt-3 shrink-0">
          {["分析今日市场情绪", "推荐关注板块", "系统状态检查", "风控建议"].map(p => (
            <button key={p} onClick={() => { setInput(p); inputRef.current?.focus(); }}
              className={cn("font-mono text-xs px-3 py-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-primary/5 transition-all duration-150", isLoading && "opacity-40 pointer-events-none")}>
              {p}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

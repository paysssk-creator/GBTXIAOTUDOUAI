import { useState, useRef, useEffect } from "react";
import { Send, Zap } from "lucide-react";
import MarketTickerBar from "@/components/dashboard/MarketTickerBar";
import ChatMsg from "@/components/dashboard/ChatMessage";
import { initialChatMessages, mockResponses, type ChatMessage } from "@/data/mockData";

const ts = () => new Date().toLocaleTimeString("zh-CN", { hour12: false });

export default function AIChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialChatMessages);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const msgCount = useRef(0);               // reset on each mount
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  // Cleanup timeout on unmount to prevent setState on unmounted component
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const send = () => {
    const text = input.trim();
    if (!text || typing) return;
    msgCount.current += 1;
    const uid = `u${msgCount.current}`;
    setMessages(prev => [...prev, { id: uid, role: "user", content: text, timestamp: ts() }]);
    setInput("");
    setTyping(true);
    timerRef.current = setTimeout(() => {
      msgCount.current += 1;
      const aid = `a${msgCount.current}`;
      const response = mockResponses[msgCount.current % mockResponses.length];
      setMessages(prev => [...prev, { id: aid, role: "ai", content: response, timestamp: ts() }]);
      setTyping(false);
    }, 1400);
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
            <p className="text-sm text-muted-foreground mt-0.5">DeepSeek v3 · A 股专业分析助手</p>
          </div>
          <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground border border-border rounded-lg px-3 py-2">
            <span className="w-2 h-2 rounded-full bg-gain animate-pulse-dot" style={{ color: "hsl(var(--gain))" }} />
            在线
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col rounded-xl border border-border overflow-hidden min-h-0"
          style={{ background: "hsl(var(--terminal-bg))" }}>
          <div className="flex-1 overflow-auto p-5 space-y-0.5 min-h-0">
            {messages.map(m => <ChatMsg key={m.id} message={m} />)}
            {typing && (
              <div className="flex items-center gap-2 py-1.5 pl-4">
                <span className="font-mono text-xs text-primary font-semibold">[GBT]</span>
                <span className="font-mono text-sm text-muted-foreground">
                  思考中<span className="animate-blink">▌</span>
                </span>
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
              disabled={typing}
              className="flex-1 bg-transparent border-none outline-none font-mono text-sm text-foreground placeholder:text-muted-foreground disabled:opacity-40"
              style={{ caretColor: "hsl(var(--primary))" }}
              autoFocus
            />
            <button onClick={send} disabled={!input.trim() || typing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold transition-opacity hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed shrink-0">
              <Send className="w-3 h-3" />发送
            </button>
          </div>
        </div>

        {/* Quick prompts */}
        <div className="flex flex-wrap gap-2 mt-3 shrink-0">
          {["分析今日市场情绪", "推荐关注板块", "系统状态检查", "风控建议"].map(p => (
            <button key={p} onClick={() => { setInput(p); inputRef.current?.focus(); }}
              className="font-mono text-xs px-3 py-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-primary/5 transition-all duration-150">
              {p}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

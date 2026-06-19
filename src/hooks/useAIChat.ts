import { useState, useRef, useCallback } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { SUPABASE_URL, SUPABASE_ANON_KEY } from "@/lib/supabase-config";

export interface Message {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

const FALLBACK_MESSAGES: Record<string, string> = {
  authentication_error: "认证失败，请刷新页面。",
  rate_limit_error: "请求频繁，请稍后再试。",
  invalid_request_error: "请求无效，请重试。",
  overloaded_error: "服务繁忙，请稍后再试。",
  insufficient_credits: "AI 额度已用尽，请联系管理员。",
  permission_error: "AI 功能已被禁用。",
  api_error: "服务暂时不可用。",
};

function getUserErrorMessage(code: string, backendMessage: string): string {
  if (backendMessage) return backendMessage;
  return FALLBACK_MESSAGES[code] || "服务暂时不可用。";
}

export function useAIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string>(crypto.randomUUID());
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    abortRef.current = new AbortController();

    const userMsg: Message = { role: "user", content };
    const aiMsg: Message = { role: "assistant", content: "", isStreaming: true };

    setMessages(prev => [...prev, userMsg, aiMsg]);
    setIsLoading(true);
    setError(null);

    try {
      await fetchEventSource(`${SUPABASE_URL}/functions/v1/ai-chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          "X-Session-ID": sessionIdRef.current,
        },
        body: JSON.stringify({
          messages: [...messages, userMsg].map(m => ({ role: m.role, content: m.content })),
          model: "deepseek/deepseek-v4-pro",
        }),
        signal: abortRef.current.signal,

        async onopen(response) {
          const ct = response.headers.get("content-type");
          if (!response.ok) {
            if (ct?.includes("text/event-stream")) {
              const text = await response.text();
              const match = text.match(/data: (.+)/);
              if (match) {
                try {
                  const d = JSON.parse(match[1]);
                  if (d.error?.message) throw new Error(d.error.message);
                } catch (e) { if (e instanceof Error && e.message !== "Unexpected token") throw e; }
              }
            }
            if (ct?.includes("application/json")) {
              const d = await response.json();
              throw new Error(d.error?.message || `请求失败: ${response.status}`);
            }
            throw new Error(`请求失败: ${response.status}`);
          }
        },

        onmessage(event) {
          if (!event.data || event.data === "[DONE]") {
            if (event.data === "[DONE]") {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") last.isStreaming = false;
                return updated;
              });
              setIsLoading(false);
            }
            return;
          }

          const data = JSON.parse(event.data);

          if (data.error) {
            const msg = getUserErrorMessage(data.error?.type || "api_error", data.error?.message || "");
            setError(msg);
            setMessages(prev => prev.slice(0, -1));
            setIsLoading(false);
            return;
          }

          const choice = data.choices?.[0];
          if (!choice) return;

          if (choice.delta?.content) {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === "assistant") {
                last.content += choice.delta.content;
              }
              return [...updated];
            });
          }

          if (choice.finish_reason) {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === "assistant") last.isStreaming = false;
              return updated;
            });
            setIsLoading(false);
          }
        },

        onerror(err) { throw err; },
      });
    } catch (err: unknown) {
      const e = err as Error;
      if (e.name !== "AbortError") {
        setError(e.message || "发送失败");
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && !last.content) return prev.slice(0, -1);
          return prev;
        });
      }
      setIsLoading(false);
    }
  }, [messages]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
  }, []);

  const resetChat = useCallback(() => {
    abortRef.current?.abort();
    sessionIdRef.current = crypto.randomUUID();
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  return { messages, isLoading, error, sendMessage, cancel, resetChat };
}

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useBackend } from "../providers/BackendProvider";
import { CHAT_URL } from "../lib/config";

const LOAD_TIMEOUT_MS = 8000;

export default function Chat() {
  const navigate = useNavigate();
  const { status, restart } = useBackend();
  const [iframeKey, setIframeKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearLoadTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const reload = useCallback(() => {
    setLoading(true);
    setError(false);
    clearLoadTimeout();
    setIframeKey((k) => k + 1);
  }, [clearLoadTimeout]);

  useEffect(() => {
    if (loading && !error) {
      timeoutRef.current = setTimeout(() => {
        setLoading(false);
        setError(true);
      }, LOAD_TIMEOUT_MS);
    }
    return clearLoadTimeout;
  }, [loading, error, clearLoadTimeout]);

  const isReady = status === "healthy";

  useEffect(() => {
    if (status === "healthy" && error) {
      reload();
    }
  }, [status, error, reload]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "r") {
        e.preventDefault();
        reload();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [reload]);

  return (
    <div className="chat-page">
      <div className="chat-toolbar">
        <button
          className="btn btn-ghost btn-sm chat-toolbar-btn"
          onClick={() => navigate("/home")}
          title="返回主页"
          aria-label="返回主页"
        >
          <HomeIcon />
          <span>主页</span>
        </button>
        <div className="chat-toolbar-divider" />
        <span className="chat-toolbar-title">GBT Chat</span>
        <div className="chat-toolbar-spacer" />
        {!isReady && (
          <button
            className="btn btn-primary btn-sm chat-toolbar-btn"
            onClick={restart}
            disabled={status === "starting"}
            aria-busy={status === "starting"}
            title="重新启动 GBT 后端"
          >
            {status === "starting" ? "启动中..." : "重启后端"}
          </button>
        )}
        <button
          className="btn btn-ghost btn-sm chat-toolbar-btn"
          onClick={reload}
          title="刷新页面"
          aria-label="刷新页面"
        >
          <ReloadIcon />
          <span>刷新</span>
        </button>
      </div>

      <div className="chat-frame-wrap">
        {loading && !error && (
          <div className="chat-frame-overlay">
            <div className="spinner" />
            <p className="text-dim mt-2">正在加载 GBT Chat...</p>
          </div>
        )}
        {error && (
          <div className="chat-frame-overlay">
            <p className="boot-title" style={{ color: "var(--error)" }}>加载失败</p>
            <p className="text-dim mt-2 mb-3">无法加载 {CHAT_URL}</p>
            <div className="flex gap-2">
              <button className="btn btn-primary" onClick={reload}>重试</button>
              <button className="btn btn-ghost" onClick={() => navigate("/settings")}>去设置</button>
            </div>
          </div>
        )}
        <iframe
          key={iframeKey}
          src={CHAT_URL}
          title="GBT Chat"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
          onLoad={() => {
            clearLoadTimeout();
            setLoading(false);
            setError(false);
          }}
          onError={() => {
            clearLoadTimeout();
            setLoading(false);
            setError(true);
          }}
        />
      </div>
    </div>
  );
}

function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a2 2 0 01-2-2v-4a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2z" />
    </svg>
  );
}

function ReloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  );
}
